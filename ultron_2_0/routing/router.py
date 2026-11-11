"""Model Router do ULTRON 2.1 (Fase 3).

O roteador é uma **camada de seleção e encaminhamento**, não um segundo
orquestrador. Ele envolve o `ProviderRegistry` do lain — que continua sendo a
autoridade de registro — e é passado ao `Orchestrator` no lugar do registry
(duck typing do contrato: `default_provider_id`, `get_provider`,
`list_providers`, `register_provider`).

Fluxo de um turno:

    Orchestrator (lain)
      -> registry.default_provider_id + get_provider(...)
         -> ModelRouter.get_provider() -> RoutingProvider
            -> ModelRouter.dispatch(request)
               -> infer_task_type(última mensagem do usuário)
               -> ModelSelectionPolicy.rank()          (dados do catálogo)
               -> FallbackManager + RetryManager        (timeout/backoff)
               -> ProviderAdapter -> provedor real

Decisões de projeto (ADR-014):

* o provedor PADRÃO continua sendo o primário; a política ordena os demais
  apenas como fallback;
* fallback entre provedores é **opt-in** — trocar silenciosamente de provedor
  muda custo/privacidade, então fica explícito na configuração;
* `mock` nunca é usado como fallback automático (é provedor de teste/offline);
* provedor/modelo escolhidos explicitamente pelo usuário são respeitados e
  desligam o fallback daquele turno;
* timeout, retry com backoff e cooldown são aplicados no código, não no
  prompt; métricas e snapshots nunca expõem credenciais.
"""

from __future__ import annotations

import json
import logging
import time
from collections import deque
from collections.abc import AsyncGenerator, Callable, Mapping
from dataclasses import dataclass, field

from app.intelligence.providers.base import LLMException, LLMProvider
from app.models.message import LLMRequest, LLMResponse, MessageRole

from .adapters import ProviderAdapter
from .capabilities import ModelCapabilities, TaskType, infer_task_type
from .catalog import ModelCatalog, build_catalog
from .fallback import FallbackManager
from .metrics import MetricsRegistry
from .policy import Candidate, ModelSelectionPolicy
from .retry import RetryManager, RetryPolicy

logger = logging.getLogger("ultron2.routing")

_TRUE_VALUES = {"1", "true", "yes", "on", "sim"}

# Sentinela de modelo no modo "auto": o modelo REAL é escolhido por tarefa e
# fica registrado na mensagem do assistente (o `ChatService` do lain grava o
# provedor/modelo da RESPOSTA, não os da conversa).
AUTO_MODEL = "auto"


# -- configuração ------------------------------------------------------------
@dataclass(frozen=True)
class RouterConfig:
    """Configuração operacional do roteador (nenhuma credencial)."""

    enabled: bool = True
    fallback_enabled: bool = False
    # "primary": o provedor padrão continua primário (fallback só em falha).
    # "auto": a política escolhe o provedor por tipo de tarefa a cada turno.
    mode: str = "primary"
    timeout_seconds: float = 45.0
    max_attempts: int = 2
    base_backoff_seconds: float = 0.25
    max_backoff_seconds: float = 4.0
    cooldown_seconds: float = 30.0
    allow_mock_fallback: bool = False
    providers: tuple[str, ...] = ()
    model_overrides: dict[str, dict[str, str]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.mode not in ("primary", "auto"):
            raise ValueError("mode deve ser 'primary' ou 'auto'")
        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds deve ser > 0")
        if self.max_attempts < 1:
            raise ValueError("max_attempts deve ser >= 1")
        if self.base_backoff_seconds < 0 or self.max_backoff_seconds < 0:
            raise ValueError("backoff não pode ser negativo")
        if self.cooldown_seconds < 0:
            raise ValueError("cooldown_seconds não pode ser negativo")

    @classmethod
    def from_env(cls, environ: Mapping[str, str] | None = None) -> "RouterConfig":
        """Lê a configuração de `ULTRON_ROUTER_*` (sem tocar em credenciais)."""
        env = environ if environ is not None else __import__("os").environ

        def _bool(name: str, default: bool) -> bool:
            raw = env.get(name)
            if raw is None:
                return default
            return raw.strip().lower() in _TRUE_VALUES

        def _float(name: str, default: float) -> float:
            raw = env.get(name)
            if raw is None or not raw.strip():
                return default
            try:
                return float(raw)
            except ValueError:
                logger.warning("valor inválido em %s; usando padrão %s", name, default)
                return default

        def _int(name: str, default: int) -> int:
            raw = env.get(name)
            if raw is None or not raw.strip():
                return default
            try:
                return int(raw)
            except ValueError:
                logger.warning("valor inválido em %s; usando padrão %s", name, default)
                return default

        providers_raw = env.get("ULTRON_ROUTER_PROVIDERS", "")
        providers = tuple(
            item.strip() for item in providers_raw.split(",") if item.strip()
        )

        overrides: dict[str, dict[str, str]] = {}
        raw_models = env.get("ULTRON_ROUTER_MODELS", "").strip()
        if raw_models:
            try:
                parsed = json.loads(raw_models)
            except ValueError:
                logger.warning("ULTRON_ROUTER_MODELS não é JSON válido; ignorado")
                parsed = {}
            if isinstance(parsed, dict):
                valid_tasks = {task.value for task in TaskType}
                for provider_id, mapping in parsed.items():
                    if not isinstance(mapping, dict):
                        continue
                    clean = {
                        str(task): str(model)
                        for task, model in mapping.items()
                        if str(task) in valid_tasks and model
                    }
                    if clean:
                        overrides[str(provider_id)] = clean

        return cls(
            enabled=_bool("ULTRON_ROUTER_ENABLED", True),
            fallback_enabled=_bool("ULTRON_ROUTER_FALLBACK", False),
            mode=env.get("ULTRON_ROUTER_MODE", "primary").strip().lower()
            or "primary",
            timeout_seconds=_float("ULTRON_ROUTER_TIMEOUT", 45.0),
            max_attempts=_int("ULTRON_ROUTER_MAX_ATTEMPTS", 2),
            base_backoff_seconds=_float("ULTRON_ROUTER_BACKOFF", 0.25),
            max_backoff_seconds=_float("ULTRON_ROUTER_MAX_BACKOFF", 4.0),
            cooldown_seconds=_float("ULTRON_ROUTER_COOLDOWN", 30.0),
            allow_mock_fallback=_bool("ULTRON_ROUTER_ALLOW_MOCK_FALLBACK", False),
            providers=providers,
            model_overrides=overrides,
        )

    def to_public_dict(self) -> dict:
        """Representação segura para logs/status (não há segredos aqui)."""
        return {
            "enabled": self.enabled,
            "fallback_enabled": self.fallback_enabled,
            "mode": self.mode,
            "timeout_seconds": self.timeout_seconds,
            "max_attempts": self.max_attempts,
            "base_backoff_seconds": self.base_backoff_seconds,
            "max_backoff_seconds": self.max_backoff_seconds,
            "cooldown_seconds": self.cooldown_seconds,
            "allow_mock_fallback": self.allow_mock_fallback,
            "providers": list(self.providers),
            "model_overrides": {
                provider: dict(mapping)
                for provider, mapping in self.model_overrides.items()
            },
        }


# -- roteador ----------------------------------------------------------------
class ModelRouter:
    """Seleção/encaminhamento sobre o `ProviderRegistry` do lain."""

    def __init__(
        self,
        registry,
        *,
        config: RouterConfig | None = None,
        catalog: ModelCatalog | None = None,
        policy: ModelSelectionPolicy | None = None,
    ) -> None:
        self._registry = registry
        self._config = config or RouterConfig.from_env()
        self._metrics = MetricsRegistry()
        self._policy = policy or ModelSelectionPolicy()
        registered = [
            (provider_id, self._provider_default_model(provider_id))
            for provider_id in registry.list_providers()
        ]
        self._catalog = catalog or build_catalog(
            registered, model_overrides=self._config.model_overrides
        )
        self._ensure_all()
        self._retry = RetryManager(
            RetryPolicy(
                max_attempts=self._config.max_attempts,
                base_delay_seconds=self._config.base_backoff_seconds,
                max_delay_seconds=self._config.max_backoff_seconds,
            ),
            metrics=self._metrics,
        )
        self._fallback = FallbackManager(
            metrics=self._metrics,
            retry=self._retry,
            timeout_seconds=self._config.timeout_seconds,
            cooldown_seconds=self._config.cooldown_seconds,
        )
        self._recent: deque[dict] = deque(maxlen=20)

    # -- contrato do ProviderRegistry (preservado) ----------------------------
    @property
    def registry(self):
        return self._registry

    @property
    def config(self) -> RouterConfig:
        return self._config

    @property
    def catalog(self) -> ModelCatalog:
        return self._catalog

    @property
    def metrics(self) -> MetricsRegistry:
        return self._metrics

    @property
    def default_provider_id(self) -> str:
        return self._registry.default_provider_id

    def list_providers(self) -> list[str]:
        return self._registry.list_providers()

    def register_provider(self, provider: LLMProvider) -> None:
        """Delega o registro ao registry do lain e atualiza o catálogo."""
        self._registry.register_provider(provider)
        self._refresh_provider(provider.provider_id, provider.default_model)
        self._metrics.reset(provider.provider_id)

    def get_provider(self, provider_id: str | None = None) -> LLMProvider:
        """Devolve o provedor de roteamento (primário ou fixado)."""
        if not self._config.enabled:
            return self._registry.get_provider(provider_id)
        if provider_id is not None and provider_id != self._registry.default_provider_id:
            return RoutingProvider(self, explicit_provider_id=provider_id)
        return RoutingProvider(self, explicit_provider_id=None)

    # -- seleção explícita (API para testes/agentes) --------------------------
    def select(
        self,
        task: TaskType | str | None = None,
        *,
        message: str = "",
        provider_ids: list[str] | None = None,
        exclude: tuple[str, ...] = (),
    ) -> list[Candidate]:
        """Ranking determinístico de provedores para uma tarefa/mensagem."""
        task_type = infer_task_type(message, task=task)
        self._ensure_all()
        ids = list(provider_ids) if provider_ids is not None else self.list_providers()
        return self._policy.rank(
            self._catalog,
            task_type,
            ids,
            exclude=tuple(exclude),
            preferred=self.default_provider_id,
        )

    # -- execução -------------------------------------------------------------
    async def dispatch(
        self, request: LLMRequest, explicit_provider_id: str | None = None
    ) -> LLMResponse:
        """Resposta não-streaming com ordem de candidatos e fallback."""
        adapters, task, explicit_model = self._plan(request, explicit_provider_id)
        response = await self._fallback.generate(adapters, request)
        self._record_decision(
            task=task,
            adapters=adapters,
            chosen=response.provider,
            fallback_used=response.provider != adapters[0].provider_id,
            explicit_model=explicit_model,
        )
        return response

    async def stream_response(
        self,
        request: LLMRequest,
        on_chunk: Callable[[str], None],
        explicit_provider_id: str | None = None,
    ) -> LLMResponse:
        """Streaming com fallback APENAS antes do primeiro chunk."""
        chosen: dict[str, str] = {}
        chunks: list[str] = []

        def _mark(provider_id: str, model: str) -> None:
            chosen["provider_id"] = provider_id
            chosen["model"] = model

        async for chunk in self.iter_stream(
            request, explicit_provider_id=explicit_provider_id, on_start=_mark
        ):
            chunks.append(chunk)
            on_chunk(chunk)

        content = "".join(chunks)
        provider_id = chosen.get("provider_id", self.default_provider_id)
        model = chosen.get("model") or request.model or self._provider_default_model(
            provider_id
        )
        response = LLMResponse(content=content, provider=provider_id, model=model)
        self._record_decision(
            task=infer_task_type(_last_user_text(request)),
            adapters=[],
            chosen=provider_id,
            fallback_used=False,
            explicit_model=None,
        )
        return response

    async def iter_stream(
        self,
        request: LLMRequest,
        explicit_provider_id: str | None = None,
        on_start: Callable[[str, str], None] | None = None,
    ) -> AsyncGenerator[str, None]:
        """Itera chunks com failover antes do primeiro chunk."""
        adapters, _task, _explicit_model = self._plan(request, explicit_provider_id)
        if not adapters:
            raise RuntimeError("nenhum provedor candidato disponível")

        last_error: BaseException | None = None
        for adapter in adapters:
            provider_id = adapter.provider_id
            self._metrics.record_call(provider_id)
            started = time.monotonic()
            try:
                generator, first_chunk = await adapter.open_stream(
                    request, timeout=self._config.timeout_seconds
                )
            except Exception as error:  # noqa: BLE001 — failover
                last_error = error
                self._metrics.record_failure(
                    provider_id, error, cooldown_seconds=self._config.cooldown_seconds
                )
                continue

            if on_start is not None:
                on_start(provider_id, adapter.model)
            try:
                if first_chunk:
                    yield first_chunk
                async for chunk in generator:
                    if chunk:
                        yield chunk
            except Exception as error:  # noqa: BLE001 — já houve saída parcial
                self._metrics.record_failure(
                    provider_id, error, cooldown_seconds=self._config.cooldown_seconds
                )
                raise
            else:
                self._metrics.record_success(
                    provider_id, time.monotonic() - started
                )
            return

        assert last_error is not None  # pragma: no cover
        raise last_error

    async def health_check(self, explicit_provider_id: str | None = None) -> bool:
        provider_id = explicit_provider_id or self.default_provider_id
        try:
            provider = self._registry.get_provider(provider_id)
        except Exception:  # noqa: BLE001 — diagnóstico
            return False
        adapter = ProviderAdapter(
            provider,
            self._capabilities_for(provider_id, provider.default_model),
        )
        return await adapter.health_check(timeout=self._config.timeout_seconds)

    # -- observabilidade ------------------------------------------------------
    def status(self) -> dict:
        """Snapshot real do roteador — sem credenciais."""
        selection = {
            task.value: [
                candidate.public()
                for candidate in self.select(task)
            ]
            for task in TaskType
        }
        return {
            "enabled": self._config.enabled,
            "default_provider": self.default_provider_id,
            "config": self._config.to_public_dict(),
            "providers": self.list_providers(),
            "catalog": self._catalog.public(),
            "selection": selection,
            "metrics": self._metrics.public(),
            "policy": self._policy.public(),
            "recent_decisions": list(self._recent),
        }

    def snapshot(self) -> dict:
        """Alias explícito para diagnóstico (usado por CLI/HUD)."""
        return self.status()

    # -- interno --------------------------------------------------------------
    def _provider_default_model(self, provider_id: str) -> str:
        try:
            return self._registry.get_provider(provider_id).default_model
        except LLMException:
            return "auto"

    def _refresh_provider(self, provider_id: str, default_model: str) -> None:
        self._catalog.forget(provider_id)
        extra = sorted(
            set(self._config.model_overrides.get(provider_id, {}).values())
        )
        self._catalog.register_provider(
            provider_id,
            default_model,
            extra_models=extra,
            task_models=dict(self._config.model_overrides.get(provider_id, {})),
        )

    def _ensure_all(self) -> None:
        for provider_id in self.list_providers():
            if not self._catalog.for_provider(provider_id):
                self._refresh_provider(
                    provider_id, self._provider_default_model(provider_id)
                )

    def _capabilities_for(self, provider_id: str, model: str) -> ModelCapabilities:
        self._ensure_all()
        caps = self._catalog.get(provider_id, model)
        if caps is None:
            caps = ModelCapabilities.for_provider(provider_id, model)
            self._catalog.register(caps)
        return caps

    def _allowed(self, provider_id: str) -> bool:
        return not self._config.providers or provider_id in self._config.providers

    def _fallback_allowed(self, provider_id: str) -> bool:
        if provider_id == "mock" and not self._config.allow_mock_fallback:
            return False
        return True

    def _plan(
        self, request: LLMRequest, explicit_provider_id: str | None
    ) -> tuple[list[ProviderAdapter], TaskType, str | None]:
        task = infer_task_type(_last_user_text(request))
        self._ensure_all()

        # Modelo pedido explicitamente (o sentinela "auto" não é um pedido).
        requested_model = (
            request.model
            if request.model and request.model != AUTO_MODEL
            else None
        )

        primary_id = explicit_provider_id or self.default_provider_id

        # Modo "auto": sem provedor/modelo explícito, a POLÍTICA escolhe o
        # provedor do turno pelo tipo de tarefa (o padrão não é privilegiado
        # de forma absoluta — apenas recebe o bônus da política).
        auto_selected = False
        if (
            explicit_provider_id is None
            and requested_model is None
            and self._config.mode == "auto"
        ):
            eligible = [
                provider_id
                for provider_id in self.list_providers()
                if self._allowed(provider_id)
            ]
            ranked = self._policy.rank(self._catalog, task, eligible)
            if ranked:
                primary_id = ranked[0].provider_id
                auto_selected = True

        if primary_id not in self.list_providers():
            # O padrão pode apontar para um provedor ainda não registrado
            # (testes/integrações registram depois). Usa o melhor disponível.
            ranked = self._policy.rank(
                self._catalog, task, self.list_providers()
            )
            if not ranked:
                raise LLMException(
                    f"nenhum provedor disponível para a tarefa '{task.value}'",
                    provider=primary_id,
                )
            primary_id = ranked[0].provider_id

        primary_default = self._provider_default_model(primary_id)
        explicit_model = (
            requested_model
            if requested_model and requested_model != primary_default
            else None
        )
        primary_model = (
            explicit_model
            or self._catalog.best_model(primary_id, task)
            or primary_default
        )
        primary_provider = self._registry.get_provider(primary_id)
        adapters = [
            ProviderAdapter(
                primary_provider,
                self._capabilities_for(primary_id, primary_model),
            )
        ]

        # Seleção explícita ou fallback desligado: um único candidato.
        if (
            explicit_provider_id is not None
            or explicit_model is not None
            or not self._config.fallback_enabled
        ):
            return adapters, task, explicit_model

        ranked = self._policy.rank(
            self._catalog,
            task,
            self.list_providers(),
            exclude=(primary_id,),
            preferred=primary_id,
        )
        for candidate in ranked:
            provider_id = candidate.provider_id
            if not self._allowed(provider_id):
                continue
            if not self._fallback_allowed(provider_id):
                continue
            if not self._metrics.available(provider_id):
                continue
            adapters.append(
                ProviderAdapter(
                    self._registry.get_provider(provider_id),
                    self._capabilities_for(provider_id, candidate.model),
                )
            )
        return adapters, task, explicit_model

    def _record_decision(
        self,
        *,
        task: TaskType,
        adapters: list[ProviderAdapter],
        chosen: str,
        fallback_used: bool,
        explicit_model: str | None,
    ) -> None:
        decision = {
            "at": round(time.time(), 3),
            "task": task.value,
            "candidates": [adapter.provider_id for adapter in adapters],
            "chosen": chosen,
            "fallback_used": fallback_used,
            "requested_model": explicit_model,
        }
        self._recent.append(decision)
        logger.info(
            "roteamento: task=%s candidatos=%s escolhido=%s fallback=%s",
            decision["task"],
            decision["candidates"],
            chosen,
            fallback_used,
        )


class RoutingProvider(LLMProvider):
    """Provedor de fachada que delega ao `ModelRouter`.

    Registrado no lugar do provedor concreto? Não: o registry continua com os
    provedores reais. Esta fachada é o que o `Orchestrator` recebe via
    `get_provider()`, preservando `provider_id`/`default_model` observáveis.
    """

    def __init__(
        self, router: ModelRouter, *, explicit_provider_id: str | None = None
    ) -> None:
        self._router = router
        self._explicit_provider_id = explicit_provider_id

    @property
    def provider_id(self) -> str:
        return self._explicit_provider_id or self._router.default_provider_id

    @property
    def default_model(self) -> str:
        # No modo "auto" sem provedor explícito, o modelo real é escolhido por
        # tarefa a cada turno; o sentinela "auto" é gravado na conversa e o
        # modelo escolhido fica registrado na resposta do assistente.
        if (
            self._router._config.mode == "auto"
            and self._explicit_provider_id is None
        ):
            return AUTO_MODEL
        return self._router._provider_default_model(self.provider_id)

    async def generate_response(self, request: LLMRequest) -> LLMResponse:
        return await self._router.dispatch(request, self._explicit_provider_id)

    async def generate_stream(
        self, request: LLMRequest
    ) -> AsyncGenerator[str, None]:
        async for chunk in self._router.iter_stream(
            request, explicit_provider_id=self._explicit_provider_id
        ):
            yield chunk

    async def generate_response_streaming(
        self, request: LLMRequest, on_chunk: Callable[[str], None]
    ) -> LLMResponse:
        return await self._router.stream_response(
            request, on_chunk, explicit_provider_id=self._explicit_provider_id
        )

    async def health_check(self) -> bool:
        return await self._router.health_check(self._explicit_provider_id)


def _last_user_text(request: LLMRequest) -> str:
    """Última mensagem real do usuário (ignora resultados de ferramenta)."""
    for message in reversed(request.messages or []):
        role = getattr(message, "role", None)
        if getattr(role, "value", role) != MessageRole.USER.value:
            continue
        content = (message.content or "").strip()
        if content.startswith("[TOOL_RESULT"):
            continue
        return content[:2_000]
    return ""
