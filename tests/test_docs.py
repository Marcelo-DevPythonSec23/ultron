"""Validação do sistema de contexto/memória (CONTEXT.md §13, MEMORY.md §17).

Os documentos vivem na **raiz do projeto** (`PROJECT_CONTEXT.md`,
`docs/context/`, `docs/memory/`), fora do repositório `ultron-2.0`. Se essa
árvore não estiver presente (checkout isolado do 2.0), os testes são pulados com
motivo explícito — não fingem validar o que não existe.

O que é validado:

1. os documentos obrigatórios existem;
2. o índice (`CONTEXT_INDEX.md`) não cita caminhos fantasmas;
3. links markdown internos de `PROJECT_CONTEXT.md` e `docs/memory/*.md` resolvem;
4. o `AGENTS.md` do produto aponta para o contexto global e a memória.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = REPO_ROOT.parent
DOCS = PROJECT_ROOT / "docs"
MEMORY = DOCS / "memory"
CONTEXT_INDEX = DOCS / "context" / "CONTEXT_INDEX.md"

pytestmark = pytest.mark.skipif(
    not DOCS.is_dir(),
    reason="docs/ da raiz ausente (checkout isolado do ultron-2.0)",
)

REQUIRED_ROOT_DOCS = (
    "AGENTS.md",
    "CONTEXT.md",
    "MEMORY.md",
    "PROJECT_CONTEXT.md",
    "ultron-2.0/README.md",
)

REQUIRED_CONTEXT_DOCS = (
    "docs/context/CONTEXT_INDEX.md",
    "docs/context/CONTEXT_AUDIT.md",
    "docs/context/ARCHITECTURE_CONTEXT.md",
    "docs/context/DEVELOPMENT_STATE.md",
    "docs/context/TECHNICAL_DECISIONS.md",
    "docs/context/MODULE_MAP.md",
    "docs/context/DEPENDENCY_MAP.md",
    "docs/context/KNOWN_LIMITATIONS.md",
    "docs/context/GLOSSARY.md",
)

REQUIRED_MEMORY_DOCS = (
    "MEMORY_AUDIT.md",
    "MEMORY_ARCHITECTURE.md",
    "MEMORY_TYPES.md",
    "MEMORY_STORAGE.md",
    "MEMORY_RETRIEVAL.md",
    "MEMORY_SECURITY.md",
    "MEMORY_LIFECYCLE.md",
    "MEMORY_API.md",
    "MEMORY_TESTING.md",
)

REQUIRED_SPECIALIZED_DOCS = (
    "docs/ARCHITECTURE.md",
    "docs/INTEGRATION_AUDIT.md",
    "docs/INTEGRATION_MAP.md",
    "docs/SECURITY.md",
    "docs/TOOLS.md",
    "docs/VOICE_PIPELINE.md",
    "docs/TESTING.md",
)

_LINK_RE = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
_PATH_TOKEN_RE = re.compile(r"`([^`\s]+)`")


def _path_exists(relative: str) -> bool:
    """Resolve um caminho do índice; globs checam o diretório pai."""
    if "*" in relative:
        parent = relative.split("*", 1)[0].rstrip("/")
        return (PROJECT_ROOT / parent).is_dir()
    return (PROJECT_ROOT / relative).exists()


def test_documentos_obrigatorios_existem():
    missing = [
        path
        for path in (*REQUIRED_ROOT_DOCS, *REQUIRED_CONTEXT_DOCS, *REQUIRED_SPECIALIZED_DOCS)
        if not (PROJECT_ROOT / path).exists()
    ]
    missing += [f"docs/memory/{name}" for name in REQUIRED_MEMORY_DOCS if not (MEMORY / name).exists()]
    assert not missing, f"documentos obrigatórios ausentes: {missing}"


def test_indice_nao_cita_documentos_fantasmas():
    text = CONTEXT_INDEX.read_text(encoding="utf-8")
    # A seção final lista caminhos que NÃO devem existir; não entra na checagem.
    text = text.split("## Documentos que NÃO existem", 1)[0]

    checked = 0
    missing: list[str] = []
    for token in _PATH_TOKEN_RE.findall(text):
        if "/" not in token:
            continue  # nomes soltos em colunas "Relacionados" não são caminhos
        if token.startswith(("http://", "https://")):
            continue
        token = token.rstrip(".,;:")
        checked += 1
        if not _path_exists(token):
            missing.append(token)

    assert checked >= 20, f"índice parece vazio/incompleto ({checked} caminhos)"
    assert not missing, f"índice cita caminhos inexistentes: {sorted(set(missing))}"


def test_links_internos_resolvem():
    files = [PROJECT_ROOT / "PROJECT_CONTEXT.md", *sorted(MEMORY.glob("*.md"))]
    broken: list[str] = []
    for file in files:
        text = file.read_text(encoding="utf-8")
        for target in _LINK_RE.findall(text):
            target = target.strip()
            if target.startswith(("http://", "https://", "mailto:", "#")):
                continue
            target = target.split("#", 1)[0]
            if not target:
                continue
            resolved = (file.parent / target).resolve()
            if not resolved.exists():
                broken.append(f"{file.relative_to(PROJECT_ROOT)} -> {target}")
    assert not broken, f"links internos quebrados: {broken}"


def test_agents_aponta_para_contexto_e_memoria():
    agents = (REPO_ROOT / "AGENTS.md").read_text(encoding="utf-8")
    for expected in (
        "../PROJECT_CONTEXT.md",
        "../docs/context/CONTEXT_INDEX.md",
        "../docs/memory/MEMORY_ARCHITECTURE.md",
        "../docs/memory/MEMORY_API.md",
    ):
        assert expected in agents, f"AGENTS.md não aponta para {expected}"
