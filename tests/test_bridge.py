from ultron_2_0.orchestrator_bridge import OrchestratorBridge
from ultron_2_0.voice_runner import VoiceRunner


def test_bridge_status_has_expected_keys():
    bridge = OrchestratorBridge(project_root="/home/marcelo/projetos/ultron")
    status = bridge.status()

    assert "core_ready" in status
    assert "voice_runtime" in status
    assert "tools" in status
    assert isinstance(status["tools"], list)


def test_tool_registry_contains_expected_tools():
    runner = VoiceRunner(project_root="/home/marcelo/projetos/ultron")
    names = {tool.name for tool in runner.bridge.tool_registry.list_contracts()}

    assert {"open_app", "system_status", "web_search"}.issubset(names)


def test_voice_runner_extractors():
    assert VoiceRunner._extract_open_app_name("abrir firefox") == "firefox"
    assert VoiceRunner._extract_search_query("pesquisar inteligência artificial") == "inteligência artificial"
    assert VoiceRunner._extract_open_app_name("open VS Code") == "VS Code"
