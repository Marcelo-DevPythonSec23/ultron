from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ultron_2_0.voice_runner import VoiceRunner


if __name__ == "__main__":
    runner = VoiceRunner(ROOT.parent)
    print(runner.run_text("qual é o status do sistema?"))
    print(runner.run_text("abrir firefox"))
