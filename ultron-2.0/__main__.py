"""`python -m ultron_2_0` (a partir de ultron-2.0/) — CLI de texto do ULTRON 2.0."""

from ultron_2_0 import bootstrap

# Carrega ultron-2.0/.env (opcional) antes de qualquer import que leia
# os.environ (NVIDIA_API_KEY, GEMINI_API_KEY, configuração do router).
bootstrap.load_env()

from ultron_2_0.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
