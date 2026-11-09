"""Testes unitários para a configuração de personalidade e PromptEngine."""

from app.intelligence.personality.personality_config import PersonalityConfig
from app.intelligence.prompt_engine import PromptEngine
from app.models.message import ChatMessage, MessageRole


def test_personality_config_render_defaults():
    """Valida a renderização com o template mestre configurado."""
    config = PersonalityConfig()
    prompt = config.render_system_prompt()
    assert "ULTRON" in prompt
    assert "AUTONOMIA INTELECTUAL" in prompt
    assert "Conhecimento acima de conveniência" in prompt
    assert "sem facilitar abuso, intrusão ou dano real" in prompt
    assert "personalidade vilanesca, arrogante, fria, cínica e mordaz" in prompt
    assert "Dirija provocações ao interlocutor" in prompt


def test_personality_config_custom_template():
    """Valida a customização de atributos e instruções especiais em templates com variáveis."""
    config = PersonalityConfig(
        name="JARVIS",
        language="Inglês",
        tone="polido e formal",
        custom_instructions="Sempre cite fontes.",
    )
    custom_template = "Você é {name}. Idioma: {language}. Tom: {tone}."
    prompt = config.render_system_prompt(template_content=custom_template)
    assert "JARVIS" in prompt
    assert "Inglês" in prompt
    assert "polido e formal" in prompt
    assert "Sempre cite fontes." in prompt


def test_prompt_engine_assemble_request():
    """Valida a montagem da requisição de LLM pelo PromptEngine."""
    engine = PromptEngine()
    messages = [
        ChatMessage(role=MessageRole.USER, content="Qual a lei da termodinâmica?"),
        ChatMessage(role=MessageRole.ASSISTANT, content="A primeira lei estabelece..."),
        ChatMessage(role=MessageRole.USER, content="E a segunda?"),
    ]

    req = engine.assemble_request(
        messages=messages,
        system_instruction_override="Instrução customizada de teste",
        temperature=0.3,
    )

    assert req.system_instruction == "Instrução customizada de teste"
    assert req.temperature == 0.3
    assert len(req.messages) == 3
    assert req.messages[-1].content == "E a segunda?"
