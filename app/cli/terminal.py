"""Renderização da interface interativa do ULTRON no terminal."""

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from enum import Enum

from rich import box
from rich.console import Console, Group
from rich.live import Live
from rich.markdown import Markdown
from rich.panel import Panel
from rich.spinner import Spinner
from rich.text import Text

from app.cli.error_handling import ErrorPresentation


class ProcessingState(str, Enum):
    """Estados observáveis da interação no terminal."""

    IDLE = "IDLE"
    RECEIVING = "RECEIVING"
    ANALYZING = "ANALYZING"
    PROCESSING = "PROCESSING"
    GENERATING = "GENERATING"
    COMPLETED = "COMPLETED"
    ERROR = "ERROR"


class TerminalRenderer:
    """Apresenta mensagens, estados e respostas formatadas no terminal."""

    def __init__(self, console: Console | None = None) -> None:
        self.console = console or Console()
        self.state = ProcessingState.IDLE

    def begin_initialization(self) -> None:
        self.console.print()
        self.console.print(
            Panel(
                Text("ULTRON SYSTEM INITIALIZATION", style="bold bright_red"),
                border_style="bright_red",
                box=box.ASCII,
                padding=(0, 1),
            )
        )

    @contextmanager
    def initialization_status(self, component: str) -> Iterator[None]:
        message = Text(f"INITIALIZING {component}...", style="bright_red")
        with self.console.status(
            message,
            spinner="line",
            spinner_style="bright_red",
        ):
            yield

    def initialization_step(self, component: str, status: str) -> None:
        line = Text("> ")
        line.append(f"{component:<28}", style="bright_black")
        line.append(f"[{status}]", style="bold bright_red")
        self.console.print(line)

    def show_header(
        self,
        version: str,
        provider: str,
        model: str,
    ) -> None:
        title = Text("ULTRON", style="bold bright_red")
        title.append(" // INTELLIGENCE INTERFACE", style="bright_black")
        details = Text(f"VERSION: {version}   SYSTEM: READY\n", style="bright_white")
        details.append(f"PROVIDER: {provider}   MODEL: {model}", style="bright_black")
        self.console.print(
            Panel(
                Text.assemble(title, "\n", details),
                border_style="bright_red",
                box=box.ASCII,
                padding=(0, 1),
            )
        )
        self.console.print("Enter a message, or 'sair' to exit.", style="bright_black")
        self.console.print()

    def prompt(self) -> str:
        self.state = ProcessingState.IDLE
        return self.console.input("[bold bright_white]YOU[/] > ").strip()

    def show_user_message(self, content: str) -> None:
        self.state = ProcessingState.RECEIVING
        self.console.print(Text("YOU", style="bold bright_white"))
        self.console.print(content, style="white", soft_wrap=True)
        self.console.rule(characters="-", style="bright_black")

    @contextmanager
    def response_stream(self) -> Iterator[Callable[[str], None]]:
        """Show processing until actual output arrives, then render it progressively."""
        self.state = ProcessingState.PROCESSING
        chunks: list[str] = []
        live = Live(
            Spinner(
                "line",
                Text("ULTRON // PROCESSING REQUEST", style="bright_red"),
            ),
            console=self.console,
            refresh_per_second=12,
            transient=True,
        )

        with live:
            def receive_chunk(chunk: str) -> None:
                if not chunk:
                    return
                if not chunks:
                    live.transient = False
                self.state = ProcessingState.GENERATING
                chunks.append(chunk)
                live.update(
                    Group(
                        Text("ULTRON // INTELLIGENCE CORE", style="bold bright_red"),
                        Markdown("".join(chunks)),
                    ),
                    refresh=False,
                )

            yield receive_chunk

    def show_assistant_message(self, content: str) -> None:
        streamed = self.state == ProcessingState.GENERATING
        self.state = ProcessingState.COMPLETED
        self.console.print()
        if not streamed:
            self.console.print(
                Text("ULTRON // INTELLIGENCE CORE", style="bold bright_red")
            )
            self.console.print(Markdown(content), soft_wrap=True)
        self.console.rule(characters="-", style="bright_black")
        self.console.print()

    def show_error(
        self,
        error: ErrorPresentation,
        *,
        debug: bool = False,
        log_file: str = "logs/errors.log",
    ) -> None:
        self.state = ProcessingState.ERROR
        heading = Text(f"[!] {error.category.value}", style="bold bright_red")
        body = Text(error.message, style="white")
        body.append(f"\n\nPROVIDER : {error.provider}", style="bright_black")
        if error.http_status is not None:
            body.append(f"\nCODE     : HTTP {error.http_status}", style="bright_black")
        body.append(f"\nSTATUS   : {error.status}", style="bright_black")
        if error.retry_message:
            body.append(f"\n\n{error.retry_message}", style="yellow")
        if debug:
            body.append(f"\n\nSOURCE   : {error.source}", style="bright_black")
            body.append(f"\nCATEGORY : {error.category.value}", style="bright_black")
            if error.request_id:
                body.append(f"\nREQUEST  : {error.request_id}", style="bright_black")
            body.append(f"\nLOG      : {log_file}", style="bright_black")
            if error.details:
                body.append(f"\nDETAILS  : {error.details}", style="bright_black")
        self.console.print(
            Panel(
                Text.assemble(heading, "\n\n", body),
                title=Text(f"ULTRON // {error.title}", style="bold bright_red"),
                border_style="red",
                box=box.ASCII,
                padding=(0, 1),
            )
        )

    def show_shutdown(self, message: str = "Session terminated.") -> None:
        self.console.print(Text(f"\nULTRON // {message}\n", style="bright_black"))
