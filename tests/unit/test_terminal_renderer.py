"""Testes da renderização visual da CLI."""

from io import StringIO

from rich.console import Console

from app.cli.error_handling import classify_error
from app.cli.terminal import ProcessingState, TerminalRenderer


def test_terminal_renderer_formats_messages_and_stream_state():
    output = StringIO()
    renderer = TerminalRenderer(Console(file=output, width=80, force_terminal=False))

    renderer.show_user_message("Explique o contexto.")
    assert renderer.state == ProcessingState.RECEIVING

    with renderer.response_stream() as on_chunk:
        on_chunk("# Resposta\n\nConteúdo progressivo.")
        assert renderer.state == ProcessingState.GENERATING

    renderer.show_assistant_message("# Resposta\n\nConteúdo progressivo.")
    assert renderer.state == ProcessingState.COMPLETED

    rendered = output.getvalue()
    assert "YOU" in rendered
    assert "ULTRON // INTELLIGENCE CORE" in rendered
    assert "Conteúdo progressivo." in rendered


def test_terminal_renderer_marks_errors():
    output = StringIO()
    renderer = TerminalRenderer(Console(file=output, force_terminal=False))

    renderer.show_error(classify_error(TimeoutError("technical details")))

    assert renderer.state == ProcessingState.ERROR
    assert "O provedor demorou" in output.getvalue()
