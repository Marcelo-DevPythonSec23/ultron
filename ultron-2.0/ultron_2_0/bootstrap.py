"""Bootstrap de caminhos e configuração do ULTRON 2.0.

Resolve, por caminho ABSOLUTO, as três raízes envolvidas na integração:

    PROJECT_ROOT  (…)            /home/marcelo/projetos/ultron
    LAIN_ROOT     (…/lain)       núcleo ULTRON — NUNCA é modificado
    MARKLVI_ROOT  (…/Mark-LVI-main)  runtime Mark-LVI — NUNCA é modificado

Duas correções da auditoria vivem aqui (docs/INTEGRATION_AUDIT.md):

1. O `Settings` do lain carrega `.env` relativo ao CWD (`lain/app/config.py:51`),
   o que quebrava o health_check fora de `lain/`. Aqui o `.env` é resolvido por
   caminho absoluto — o ULTRON 2.0 funciona a partir de qualquer diretório.

2. O banco padrão do lain (`sqlite+aiosqlite:///./ultron.db`) também é relativo ao
   CWD e apontaria para o banco REAL do usuário se executado de dentro de
   `lain/`. O ULTRON 2.0 usa por padrão um banco PRÓPRIO, isolado, em
   `ultron-2.0/data/ultron2.db`. `lain/ultron.db` nunca é tocado.

Nada aqui escreve nos repositórios originais; apenas os adiciona ao `sys.path`
para importar (não copiar) seus módulos.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Camada padrão do ultron-2.0: ultron_2_0/ -> ultron-2.0/ -> ultron (raiz do projeto)
_THIS_FILE = Path(__file__).resolve()
ULTRON2_ROOT = _THIS_FILE.parents[1]
DEFAULT_PROJECT_ROOT = _THIS_FILE.parents[2]


def resolve_project_root(project_root: str | Path | None = None) -> Path:
    """Raiz do projeto ultron (contém lain/ e Mark-LVI-main/)."""
    if project_root is not None:
        root = Path(project_root).resolve()
    else:
        env_root = os.environ.get("ULTRON2_PROJECT_ROOT")
        root = Path(env_root).resolve() if env_root else DEFAULT_PROJECT_ROOT
    return root


def resolve_roots(
    project_root: str | Path | None = None,
) -> tuple[Path, Path, Path]:
    """Retorna (PROJECT_ROOT, LAIN_ROOT, MARKLVI_ROOT) validados."""
    root = resolve_project_root(project_root)
    lain = root / "lain"
    marklvi = root / "Mark-LVI-main"
    if not lain.is_dir():
        raise RuntimeError(
            f"Núcleo ULTRON não encontrado em '{lain}'. "
            "Passe project_root= apontando para a raiz que contém lain/."
        )
    if not marklvi.is_dir():
        raise RuntimeError(
            f"Runtime Mark-LVI não encontrado em '{marklvi}'. "
            "Passe project_root= apontando para a raiz que contém Mark-LVI-main/."
        )
    return root, lain, marklvi


def ensure_sys_paths(project_root: str | Path | None = None) -> tuple[Path, Path, Path]:
    """Adiciona lain/ e Mark-LVI-main/ ao sys.path (idempotente).

    Os nomes de pacote de nível superior dos dois projetos não colidem:
    lain expõe `app`, Mark-LVI expõe `core`/`actions`/`providers`/`memory`.
    """
    root, lain, marklvi = resolve_roots(project_root)
    for p in (str(lain), str(marklvi)):
        if p not in sys.path:
            sys.path.insert(0, p)
    return root, lain, marklvi


def load_env(env_file: str | Path | None = None) -> Path | None:
    """Carrega o `.env` do ULTRON 2.0 no ambiente do processo.

    O arquivo fica em `ultron-2.0/.env` (gitignored) e é opcional: se não
    existir, nada acontece. Variáveis já exportadas no shell têm precedência
    (`override=False`) e a função é idempotente — pode ser chamada por
    qualquer entrypoint sem duplicar efeitos.

    Retorna o caminho carregado ou `None` quando não há `.env` (ou quando
    `python-dotenv` não está instalado).
    """
    path = Path(env_file).resolve() if env_file else ULTRON2_ROOT / ".env"
    if not path.is_file():
        return None
    try:
        from dotenv import load_dotenv
    except ImportError:  # dependência opcional em runtime mínimo
        return None
    load_dotenv(dotenv_path=path, override=False)
    return path


def default_database_url(ultron2_root: Path | None = None) -> str:
    """URL do banco ISOLADO do ULTRON 2.0 (nunca o lain/ultron.db)."""
    root = (ultron2_root or ULTRON2_ROOT).resolve()
    data_dir = root / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    return f"sqlite+aiosqlite:///{data_dir / 'ultron2.db'}"


def build_settings(
    lain_root: str | Path,
    database_url: str | None = None,
) -> "Settings":  # noqa: F821 — tipo resolvido após ensure_sys_paths
    """Constrói o `Settings` do núcleo ULTRON de forma CWD-independente.

    - `.env` do lain resolvido por caminho absoluto (carrega a GEMINI_API_KEY
      real sem duplicá-la em nenhum outro lugar);
    - `DATABASE_URL` forçado para o banco isolado do ULTRON 2.0, a menos que o
      chamador forneça outro (ex.: `:memory:` em testes).

    Argumentos de inicialização têm precedência sobre variáveis de ambiente e
    sobre o `.env` no pydantic-settings — por isso o override do banco é garantido.
    """
    from app.config import Settings  # requer lain/ no sys.path (ensure_sys_paths)

    env_file = Path(lain_root) / ".env"
    return Settings(
        _env_file=str(env_file) if env_file.exists() else None,
        DATABASE_URL=database_url or default_database_url(),
    )
