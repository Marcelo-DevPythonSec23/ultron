from __future__ import annotations

from .voice_runner import VoiceRunner


def demo() -> None:
    runner = VoiceRunner()
    print("Bridge status:")
    print(runner.bridge.status())

    print("\nText command demo:")
    print(runner.run_text("qual é o status do sistema?"))

    print("\nVoice command demo:")
    print(runner.run_text("abrir firefox"))


if __name__ == "__main__":
    demo()
