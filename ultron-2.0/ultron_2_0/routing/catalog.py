"""Catálogo de modelos conhecidos e capacidades por provedor.

O catálogo é derivado dos provedores REALMENTE registrados no
`ProviderRegistry` do lain (autoridade de registro preservada). Cada provedor
entra com o seu `default_model`; modelos adicionais só existem se configurados
explicitamente em `RouterConfig.model_overrides` — nada de inventar nomes de
modelo.

`ModelCatalog` é consultado pela política de seleção e pelo roteador para
decidir qual modelo usar em cada tarefa. Ele não chama rede nem SDK.
"""

from __future__ import annotations

from .capabilities import ModelCapabilities, TaskType, profile_for


class ModelCatalog:
    """Registro ordenado de `ModelCapabilities` por provedor."""

    def __init__(self) -> None:
        # dict preserva a ordem de registro: empates no ranking ficam estáveis.
        self._models: dict[str, dict[str, ModelCapabilities]] = {}
        # Overrides explícitos por tarefa: (provider_id, task) -> model.
        self._task_models: dict[tuple[str, str], str] = {}

    # -- registro -------------------------------------------------------------
    def register(self, capabilities: ModelCapabilities) -> None:
        """Registra/substitui um modelo (mesmo provedor + mesmo nome)."""
        provider = self._models.setdefault(capabilities.provider_id, {})
        provider[capabilities.model] = capabilities

    def register_provider(
        self,
        provider_id: str,
        default_model: str,
        *,
        extra_models: list[str] | None = None,
        task_models: dict[str, str] | None = None,
        supports_tools: bool = True,
        supports_streaming: bool = True,
    ) -> None:
        """Registra o modelo padrão do provedor, overrides e modelos extras."""
        models = [default_model, *(extra_models or [])]
        seen: set[str] = set()
        for model in models:
            if not model or model in seen:
                continue
            seen.add(model)
            self.register(
                ModelCapabilities.for_provider(
                    provider_id,
                    model,
                    supports_tools=supports_tools,
                    supports_streaming=supports_streaming,
                )
            )
        for task, model in (task_models or {}).items():
            if model in seen:
                self._task_models[(provider_id, str(task))] = model

    def forget(self, provider_id: str) -> None:
        """Remove um provedor do catálogo (usado quando ele é substituído)."""
        self._models.pop(provider_id, None)

    # -- consulta -------------------------------------------------------------
    def for_provider(self, provider_id: str) -> list[ModelCapabilities]:
        return list(self._models.get(provider_id, {}).values())

    def get(self, provider_id: str, model: str | None = None) -> ModelCapabilities | None:
        models = self._models.get(provider_id)
        if not models:
            return None
        if model is None:
            return next(iter(models.values()))
        return models.get(model)

    def best(
        self, provider_id: str, task: TaskType
    ) -> ModelCapabilities | None:
        """Modelo do provedor com maior aderência à tarefa (empate: o 1º).

        Um override explícito de tarefa (`task_models`) sempre vence: ele é
        uma decisão operacional, não um palpite de score.
        """
        override = self._task_models.get((provider_id, task.value))
        if override is not None:
            caps = self._models.get(provider_id, {}).get(override)
            if caps is not None:
                return caps
        models = self.for_provider(provider_id)
        if not models:
            return None
        return max(models, key=lambda caps: caps.score(task))

    def best_model(self, provider_id: str, task: TaskType) -> str | None:
        caps = self.best(provider_id, task)
        return caps.model if caps is not None else None

    def providers(self) -> list[str]:
        return list(self._models.keys())

    def public(self) -> dict[str, list[dict]]:
        """Versão serializável do catálogo (sem credenciais)."""
        return {
            provider_id: [caps.public() for caps in models.values()]
            for provider_id, models in self._models.items()
        }


def build_catalog(
    registered: list[tuple[str, str]],
    *,
    model_overrides: dict[str, dict[str, str]] | None = None,
    supports_tools: dict[str, bool] | None = None,
    supports_streaming: dict[str, bool] | None = None,
) -> ModelCatalog:
    """Catálogo a partir de `(provider_id, default_model)` já registrados.

    `model_overrides` mapeia provedor → {task: modelo} e apenas ACRESCENTA
    modelos ao catálogo; o `default_model` do provedor nunca é sobrescrito.
    """
    overrides = model_overrides or {}
    tools = supports_tools or {}
    streaming = supports_streaming or {}
    catalog = ModelCatalog()
    for provider_id, default_model in registered:
        catalog.register_provider(
            provider_id,
            default_model,
            extra_models=sorted(set(overrides.get(provider_id, {}).values())),
            task_models=dict(overrides.get(provider_id, {})),
            supports_tools=tools.get(provider_id, True),
            supports_streaming=streaming.get(provider_id, True),
        )
        # Perfil conhecido do provedor, caso o chamador queira inspecionar.
        profile_for(provider_id)
    return catalog
