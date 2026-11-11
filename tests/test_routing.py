"""Testes da Fase 3 — Model Router.

Cobrem, com provedores REAIS do contrato `LLMProvider` (stubs determinísticos,
sem rede):

1. inferência determinística de tipo de tarefa;
2. catálogo/capacidades e ranking da política;
3. retry com backoff e classificação de erros;
4. métricas, cooldown e sanitização de segredos;
5. seleção/fallback/timeout entre DOIS provedores distintos;
6. isolamento de falhas, provedor/modelo explícitos e `mock`;
7. streaming com failover apenas antes do primeiro chunk;
8. configuração por env sem credenciais;
9. integração real pelo `OrchestratorBridge` (histórico único).
"""

from __future__ import annotations

import asyncio
import json
import time

import pytest

import ultron_2_0  # noqa: F401 — resolve lain/ e Mark-LVI-main/ no sys.path
from app.intelligence.providers.base import (
    ProviderAuthenticationError,
    ProviderConnectionError,
    ProviderTimeoutError,
    ProviderUnavailableError,
)
from app.intelligence.providers.registry import ProviderRegistry
from app.models.message import ChatMessage, LLMRequest, MessageRole
from tests.fakes import ScriptedProvider, StubProvider
from ultron_2_0.orchestrator_bridge import OrchestratorBridge
from ultron_2_0.routing import (
    AUTO_MODEL,
    MetricsRegistry,
    ModelCapabilities,
    ModelCatalog,
    ModelRouter,
    ModelSelectionPolicy,
    RetryPolicy,
    RouterConfig,
    TaskType,
    infer_task_type,
    sanitize_error,
)


# -- helpers -----------------------------------------------------------------
def _request(text: str = "oi", model: str | None = None) -> LLMRequest:
    return LLMRequest(
        messages=[ChatMessage(role=MessageRole.USER, content=text)],
        model=model,
    )


def _registry(default: str, *providers: StubProvider) -> ProviderRegistry:
    registry = ProviderRegistry(default_provider_id=default)
    for provider in providers:
        registry.register_provider(provider)
    return registry


def _fast_config(**overrides) -> RouterConfig:
    values = {
        "fallback_enabled": True,
        "max_attempts": 1,
        "base_backoff_seconds": 0.0,
        "max_backoff_seconds": 0.0,
        "timeout_seconds": 5.0,
        "cooldown_seconds": 0.0,
    }
    values.update(overrides)
    return RouterConfig(**values)


def _router(
    default: str = "alpha",
    *providers: StubProvider,
    config: RouterConfig | None = None,
) -> ModelRouter:
    return ModelRouter(
        _registry(default, *providers),
        config=config or _fast_config(fallback_enabled=False),
    )


def _two_providers(*, alpha_fails: bool = True) -> tuple[StubProvider, StubProvider]:
    alpha = StubProvider(
        "alpha",
        error=ProviderUnavailableError("alpha fora do ar", provider="alpha"),
        fail_times=999 if alpha_fails else 0,
        responses=["resposta do alpha"],
    )
    beta = StubProvider("beta", responses=["resposta do beta"])
    return alpha, beta


# -- 1. inferência de tarefa -------------------------------------------------
@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("bom dia, tudo bem?", TaskType.CHAT),
        ("implemente uma função python que ordena a lista", TaskType.CODE),
        ("explique os trade-offs de arquitetura desse desenho", TaskType.REASONING),
        ("resuma este texto para mim", TaskType.CHEAP),
        ("x" * 5_000, TaskType.LONG_CONTEXT),
    ],
)
def test_infer_task_type_e_deterministica(text, expected):
    assert infer_task_type(text) is expected
    assert infer_task_type(text) is expected  # sem estado, mesmo resultado


def test_infer_task_type_aceita_override_explicito():
    assert infer_task_type("oi", task="code") is TaskType.CODE
    with pytest.raises(ValueError):
        infer_task_type("oi", task="inexistente")


def test_task_type_prioriza_contexto_longo_sobre_codigo():
    text = "implemente uma função python\n" + ("linha de contexto\n" * 400)
    assert infer_task_type(text) is TaskType.LONG_CONTEXT


# -- 2. catálogo e política --------------------------------------------------
def test_capacidades_pontuam_por_tarefa():
    gemini = ModelCapabilities.for_provider("gemini", "gemini-x")
    mock = ModelCapabilities.for_provider("mock", "mock-x")
    assert gemini.score(TaskType.CODE) > mock.score(TaskType.CODE)
    assert gemini.score(TaskType.REASONING) > mock.score(TaskType.REASONING)
    assert mock.score(TaskType.CHEAP) > gemini.score(TaskType.CHEAP)


def test_politica_ordena_e_exclui_provedores():
    catalog = ModelCatalog()
    catalog.register_provider("mock", "mock-model")
    catalog.register_provider("gemini", "gemini-model")
    policy = ModelSelectionPolicy(default_bonus=0.0)

    code = policy.rank(catalog, TaskType.CODE, ["mock", "gemini"])
    assert [c.provider_id for c in code] == ["gemini", "mock"]

    without = policy.rank(
        catalog, TaskType.CODE, ["mock", "gemini"], exclude=("gemini",)
    )
    assert [c.provider_id for c in without] == ["mock"]


def test_politica_da_bonus_ao_provedor_preferido():
    catalog = ModelCatalog()
    catalog.register_provider("alpha", "m")
    catalog.register_provider("beta", "m")
    policy = ModelSelectionPolicy(default_bonus=0.1)
    ranked = policy.rank(
        catalog, TaskType.CHAT, ["alpha", "beta"], preferred="beta"
    )
    assert ranked[0].provider_id == "beta"
    assert ranked[0].score > ranked[1].score


def test_catalogo_respeita_override_de_modelo_por_tarefa():
    alpha = StubProvider("alpha", model="stub-model")
    router = _router(
        "alpha",
        alpha,
        config=_fast_config(
            fallback_enabled=False,
            model_overrides={"alpha": {"code": "alpha-code"}},
        ),
    )
    selection = router.select(TaskType.CODE)
    assert selection[0].provider_id == "alpha"
    assert selection[0].model == "alpha-code"

    asyncio.run(router.dispatch(_request("implemente uma função python")))
    assert alpha.calls[-1].model == "alpha-code"


# -- 3. retry ----------------------------------------------------------------
def test_retry_policy_backoff_exponencial_limitado():
    policy = RetryPolicy(max_attempts=5, base_delay_seconds=0.1, max_delay_seconds=0.5)
    assert [policy.delay_for(i) for i in range(4)] == [0.1, 0.2, 0.4, 0.5]


def test_retry_policy_classifica_erros():
    policy = RetryPolicy()
    assert policy.should_retry(ProviderUnavailableError("x", provider="p"))
    assert policy.should_retry(ProviderConnectionError("x", provider="p"))
    assert policy.should_retry(ProviderTimeoutError("x", provider="p"))
    assert not policy.should_retry(
        ProviderAuthenticationError("x", provider="p")
    )
    assert policy.should_retry(RuntimeError("desconhecido"))


def test_retry_policy_rejeita_parametros_invalidos():
    with pytest.raises(ValueError):
        RetryPolicy(max_attempts=0)
    with pytest.raises(ValueError):
        RetryPolicy(base_delay_seconds=-1)


def test_retry_repete_transitorio_antes_de_responder():
    alpha = StubProvider(
        "alpha",
        error=ProviderUnavailableError("spike", provider="alpha"),
        fail_times=1,
        responses=["alpha recuperado"],
    )
    beta = StubProvider("beta")
    router = _router(
        "alpha",
        alpha,
        beta,
        config=_fast_config(fallback_enabled=True, max_attempts=2),
    )

    response = asyncio.run(router.dispatch(_request()))

    assert response.provider == "alpha"
    assert alpha.attempts == 2
    assert beta.attempts == 0
    assert router.metrics.entry("alpha").retries == 1


def test_erro_de_autenticacao_nao_e_repetido_mas_permite_fallback():
    alpha = StubProvider(
        "alpha",
        error=ProviderAuthenticationError("sem chave", provider="alpha"),
        fail_times=999,
    )
    beta = StubProvider("beta")
    router = _router(
        "alpha",
        alpha,
        beta,
        config=_fast_config(fallback_enabled=True, max_attempts=3),
    )

    response = asyncio.run(router.dispatch(_request()))

    assert response.provider == "beta"
    assert alpha.attempts == 1  # não insistiu
    assert router.metrics.entry("alpha").retries == 0


# -- 4. métricas e segredos --------------------------------------------------
def test_metricas_registram_cooldown_e_sanitizam_segredo():
    metrics = MetricsRegistry()
    leaker = RuntimeError(
        "falhou com GEMINI_API_KEY=AIzaSyABCDEFGHIJKLMNOPQRSTUV123456"
    )
    metrics.record_failure("alpha", leaker, cooldown_seconds=30)

    entry = metrics.entry("alpha").public()
    assert entry["failures"] == 1
    assert entry["available"] is False
    assert entry["cooldown_remaining_seconds"] > 0
    assert "AIza" not in (entry["last_error"] or "")
    assert "[redacted]" in (entry["last_error"] or "")
    assert metrics.available("alpha", now=time.monotonic() + 31) is True


def test_sanitize_error_remove_padroes_conhecidos():
    assert "sk-" not in sanitize_error("token sk-abcdefghijklmno")
    assert sanitize_error(None) is None
    assert len(sanitize_error("x" * 1_000)) == 300


def test_status_do_roteador_nao_expoe_segredo():
    alpha = StubProvider(
        "alpha",
        error=ProviderUnavailableError(
            "falha com chave AIzaSyABCDEFGHIJKLMNOPQRSTUV123456",
            provider="alpha",
        ),
        fail_times=999,
    )
    router = _router("alpha", alpha, config=_fast_config(fallback_enabled=False))
    with pytest.raises(ProviderUnavailableError):
        asyncio.run(router.dispatch(_request()))

    payload = json.dumps(router.status(), ensure_ascii=False)
    assert "AIza" not in payload
    assert router.status()["metrics"]["alpha"]["failures"] == 1


# -- 5. seleção, fallback e timeout -----------------------------------------
def test_provedor_padrao_continua_sendo_o_primario():
    alpha, beta = _two_providers(alpha_fails=False)
    router = _router("alpha", alpha, beta, config=_fast_config(fallback_enabled=False))

    response = asyncio.run(router.dispatch(_request()))

    assert response.provider == "alpha"
    assert beta.attempts == 0


def test_fallback_troca_de_provedor_apos_falha():
    alpha, beta = _two_providers(alpha_fails=True)
    router = _router("alpha", alpha, beta, config=_fast_config(fallback_enabled=True))

    response = asyncio.run(router.dispatch(_request()))

    assert response.provider == "beta"
    assert response.content == "resposta do beta"
    assert router.metrics.entry("alpha").failures == 1
    assert router.metrics.entry("beta").successes == 1
    decision = router.status()["recent_decisions"][-1]
    assert decision["chosen"] == "beta"
    assert decision["fallback_used"] is True


def test_fallback_desligado_propaga_o_erro_original():
    alpha, beta = _two_providers(alpha_fails=True)
    router = _router("alpha", alpha, beta, config=_fast_config(fallback_enabled=False))

    with pytest.raises(ProviderUnavailableError):
        asyncio.run(router.dispatch(_request()))
    assert beta.attempts == 0


def test_timeout_isola_o_provedor_e_permite_fallback():
    alpha = StubProvider("alpha", delay_seconds=0.5)
    beta = StubProvider("beta")
    router = _router(
        "alpha",
        alpha,
        beta,
        config=_fast_config(
            fallback_enabled=True, timeout_seconds=0.02, cooldown_seconds=30
        ),
    )

    response = asyncio.run(router.dispatch(_request()))

    assert response.provider == "beta"
    metrics = router.metrics.entry("alpha").public()
    assert metrics["last_error_type"] == "ProviderTimeoutError"
    assert metrics["available"] is False


def test_provedor_em_cooldown_e_pulado_no_fallback():
    alpha = StubProvider("alpha")
    beta = StubProvider("beta")
    router = _router(
        "alpha",
        alpha,
        beta,
        config=_fast_config(fallback_enabled=True, cooldown_seconds=60),
    )
    router.metrics.record_failure(
        "beta", RuntimeError("beta caiu"), cooldown_seconds=60
    )

    response = asyncio.run(router.dispatch(_request()))
    assert response.provider == "alpha"
    # beta em cooldown foi ignorado: não houve tentativa.
    assert beta.attempts == 0


def test_mock_nunca_e_fallback_automatico_por_padrao():
    alpha = StubProvider(
        "alpha",
        error=ProviderUnavailableError("caiu", provider="alpha"),
        fail_times=999,
    )
    mock = StubProvider("mock")
    router = _router(
        "alpha", alpha, mock, config=_fast_config(fallback_enabled=True)
    )
    with pytest.raises(ProviderUnavailableError):
        asyncio.run(router.dispatch(_request()))
    assert mock.attempts == 0

    permitido = _router(
        "alpha",
        StubProvider(
            "alpha",
            error=ProviderUnavailableError("caiu", provider="alpha"),
            fail_times=999,
        ),
        StubProvider("mock"),
        config=_fast_config(fallback_enabled=True, allow_mock_fallback=True),
    )
    response = asyncio.run(permitido.dispatch(_request()))
    assert response.provider == "mock"


def test_provedor_explicito_desliga_fallback():
    """Escolher um provedor NÃO-padrão fixa aquele provedor (sem fallback).

    Selecionar o próprio padrão é o caminho de roteamento normal; por isso o
    teste usa `beta` (padrão saudável) e pede `alpha` (que falha) de propósito.
    """
    alpha, beta = _two_providers(alpha_fails=True)
    router = _router("beta", alpha, beta, config=_fast_config(fallback_enabled=True))
    provider = router.get_provider("alpha")
    assert provider.provider_id == "alpha"

    with pytest.raises(ProviderUnavailableError):
        asyncio.run(provider.generate_response(_request()))
    assert beta.attempts == 0


def test_modelo_explicito_e_respeitado_e_desliga_fallback():
    alpha, beta = _two_providers(alpha_fails=False)
    router = _router("alpha", alpha, beta, config=_fast_config(fallback_enabled=True))

    response = asyncio.run(router.dispatch(_request(model="meu-modelo")))

    assert response.provider == "alpha"
    assert alpha.calls[-1].model == "meu-modelo"
    assert beta.attempts == 0


def test_identidade_do_routing_provider_vem_do_registry():
    alpha, beta = _two_providers(alpha_fails=False)
    router = _router("alpha", alpha, beta, config=_fast_config())
    primary = router.get_provider()
    assert primary.provider_id == "alpha"
    assert primary.default_model == "stub-model"
    assert router.get_provider("beta").provider_id == "beta"
    assert router.list_providers() == ["alpha", "beta"]


# -- 7. streaming ------------------------------------------------------------
def test_stream_faz_failover_antes_do_primeiro_chunk():
    alpha = StubProvider(
        "alpha",
        error=ProviderUnavailableError("caiu", provider="alpha"),
        fail_times=999,
    )
    beta = StubProvider("beta", stream_chunks=["beta ", "ok"])
    router = _router("alpha", alpha, beta, config=_fast_config(fallback_enabled=True))

    async def consume():
        return [chunk async for chunk in router.iter_stream(_request())]

    assert asyncio.run(consume()) == ["beta ", "ok"]
    assert router.metrics.entry("beta").successes == 1


def test_stream_nao_faz_failover_depois_do_primeiro_chunk():
    alpha = StubProvider(
        "alpha", stream_chunks=["parcial", "final"], stream_error_after=1
    )
    beta = StubProvider("beta", stream_chunks=["beta"])
    router = _router("alpha", alpha, beta, config=_fast_config(fallback_enabled=True))

    async def consume():
        chunks = []
        with pytest.raises(RuntimeError):
            async for chunk in router.iter_stream(_request()):
                chunks.append(chunk)
        return chunks

    assert asyncio.run(consume()) == ["parcial"]
    assert beta.attempts == 0


def test_generate_response_streaming_devolve_identidade_real():
    alpha = StubProvider(
        "alpha",
        error=ProviderUnavailableError("caiu", provider="alpha"),
        fail_times=999,
    )
    beta = StubProvider("beta", stream_chunks=["beta ", "ok"])
    router = _router("alpha", alpha, beta, config=_fast_config(fallback_enabled=True))
    chunks: list[str] = []

    response = asyncio.run(
        router.get_provider().generate_response_streaming(_request(), chunks.append)
    )

    assert chunks == ["beta ", "ok"]
    assert response.content == "beta ok"
    assert response.provider == "beta"


# -- 8. modo auto (seleção por tipo de tarefa) ------------------------------
def test_default_model_retorna_auto_sem_provedor_explicito() -> None:
    alpha = StubProvider("alpha", model="stub-model")
    beta = StubProvider("beta", model="stub-model")
    router = _router(
        "alpha",
        alpha,
        beta,
        config=_fast_config(mode="auto", fallback_enabled=False),
    )
    provider = router.get_provider()
    assert provider.default_model == AUTO_MODEL
    # Provedor explícito continua com modelo real.
    assert router.get_provider("beta").default_model == "stub-model"


def test_auto_escolhe_provedor_por_tarefa() -> None:
    # alpha é bom em código (tags "code"), beta é barato/rápido (latência "fast").
    alpha = StubProvider("alpha", model="alpha-model")
    beta = StubProvider("beta", model="beta-model")
    router = _router(
        "alpha",
        alpha,
        beta,
        config=_fast_config(mode="auto", fallback_enabled=False),
    )

    # Força perfis distintos via catálogo: alpha com tag "code", beta sem.
    router.catalog.register_provider("alpha", "alpha-model")
    router.catalog.register_provider("beta", "beta-model")

    # Tarefa de código → alpha (bônus de tag "code" + qualidade similar).
    response = asyncio.run(router.dispatch(_request("implemente uma função python")))
    assert response.provider == "alpha"

    # Tarefa de chat → alpha (padrão, bônus do provedor preferido).
    response = asyncio.run(router.dispatch(_request("bom dia")))
    assert response.provider == "alpha"


def test_auto_respeita_provedor_e_modelo_explicitos() -> None:
    alpha = StubProvider("alpha", model="alpha-model")
    beta = StubProvider("beta", model="beta-model")
    router = _router(
        "alpha",
        alpha,
        beta,
        config=_fast_config(mode="auto", fallback_enabled=False),
    )

    # Provedor explícito desliga a seleção automática.
    provider = router.get_provider("beta")
    assert provider.provider_id == "beta"

    # Modelo explícito (não "auto") é respeitado.
    response = asyncio.run(router.dispatch(_request(model="modelo-fixo")))
    assert response.provider == "alpha"
    assert alpha.calls[-1].model == "modelo-fixo"


def test_auto_rejeita_modos_invalidos() -> None:
    with pytest.raises(ValueError):
        RouterConfig(mode="invalido")  # type: ignore[arg-type]


def test_config_por_env_define_modos() -> None:
    env = {"ULTRON_ROUTER_MODE": "auto"}
    config = RouterConfig.from_env(env)
    assert config.mode == "auto"

    env = {"ULTRON_ROUTER_MODE": "primary"}
    config = RouterConfig.from_env(env)
    assert config.mode == "primary"

    env = {"ULTRON_ROUTER_MODE": ""}
    config = RouterConfig.from_env(env)
    assert config.mode == "primary"


# -- 9. configuração ---------------------------------------------------------
def test_config_por_env_e_sem_segredos():
    env = {
        "ULTRON_ROUTER_ENABLED": "0",
        "ULTRON_ROUTER_FALLBACK": "true",
        "ULTRON_ROUTER_TIMEOUT": "12.5",
        "ULTRON_ROUTER_MAX_ATTEMPTS": "4",
        "ULTRON_ROUTER_BACKOFF": "0.1",
        "ULTRON_ROUTER_MAX_BACKOFF": "2",
        "ULTRON_ROUTER_COOLDOWN": "7",
        "ULTRON_ROUTER_ALLOW_MOCK_FALLBACK": "yes",
        "ULTRON_ROUTER_PROVIDERS": "alpha, beta",
        "ULTRON_ROUTER_MODELS": '{"alpha": {"code": "alpha-code"}}',
        "GEMINI_API_KEY": "AIzaSySegredoQueNaoPodeVazar123456",
    }
    config = RouterConfig.from_env(env)

    assert config.enabled is False
    assert config.fallback_enabled is True
    assert config.timeout_seconds == 12.5
    assert config.max_attempts == 4
    assert config.max_backoff_seconds == 2.0
    assert config.cooldown_seconds == 7.0
    assert config.allow_mock_fallback is True
    assert config.providers == ("alpha", "beta")
    assert config.model_overrides == {"alpha": {"code": "alpha-code"}}

    payload = json.dumps(config.to_public_dict(), ensure_ascii=False)
    assert "AIza" not in payload
    assert "GEMINI_API_KEY" not in payload


def test_config_por_env_tolera_valores_invalidos():
    config = RouterConfig.from_env(
        {
            "ULTRON_ROUTER_TIMEOUT": "abc",
            "ULTRON_ROUTER_MAX_ATTEMPTS": "x",
            "ULTRON_ROUTER_MODELS": "não-é-json",
        }
    )
    assert config.timeout_seconds == 45.0
    assert config.max_attempts == 2
    assert config.model_overrides == {}


def test_config_rejeita_parametros_invalidos():
    with pytest.raises(ValueError):
        RouterConfig(timeout_seconds=0)
    with pytest.raises(ValueError):
        RouterConfig(max_attempts=0)
    with pytest.raises(ValueError):
        RouterConfig(cooldown_seconds=-1)


# -- 10. integração real pelo bridge -----------------------------------------
def test_bridge_roteia_para_fallback_e_persiste_o_provedor_real():
    with OrchestratorBridge(
        database_url="sqlite+aiosqlite:///:memory:",
        default_provider="alpha",
        enable_tools=False,
        router_config=RouterConfig(
            fallback_enabled=True,
            max_attempts=1,
            base_backoff_seconds=0.0,
            max_backoff_seconds=0.0,
            cooldown_seconds=0.0,
            timeout_seconds=5.0,
            providers=("alpha", "beta"),
        ),
    ) as bridge:
        bridge.runtime.register_provider(
            StubProvider(
                "alpha",
                error=ProviderUnavailableError("alpha caiu", provider="alpha"),
                fail_times=999,
            )
        )
        bridge.runtime.register_provider(StubProvider("beta", responses=["olá do beta"]))

        response = bridge.process_text("oi")

        assert response.provider == "beta"
        assert response.content == "olá do beta"
        assistant = [m for m in bridge.history() if m["role"] == "assistant"][-1]
        assert assistant["provider"] == "beta"

        status = bridge.status()
        assert status["router"]["enabled"] is True
        assert status["router"]["config"]["fallback_enabled"] is True
        assert status["router"]["recent_decisions"][-1]["chosen"] == "beta"
        assert "AIza" not in json.dumps(status, ensure_ascii=False)


def test_bridge_sem_config_mantem_comportamento_anterior():
    with OrchestratorBridge(
        database_url="sqlite+aiosqlite:///:memory:",
        default_provider="mock",
        enable_tools=False,
    ) as bridge:
        bridge.runtime.register_provider(ScriptedProvider(["resposta normal"]))

        response = bridge.process_text("oi")

        assert response.content == "resposta normal"
        assert response.provider == "mock"
        status = bridge.status()
        assert status["router"]["enabled"] is True
        assert status["router"]["config"]["fallback_enabled"] is False
