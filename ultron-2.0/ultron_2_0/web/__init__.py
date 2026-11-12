"""HUD web do ULTRON 2.0 (Etapa 5).

A interface é uma PONTA de entrada como a CLI e a voz: ela não conversa, não
guarda histórico paralelo e não decide nada. Todo turno passa pelo MESMO
`OrchestratorBridge.process_text` e todo estado exibido vem do núcleo real.

Por que HUD web (decisão nº 6 da auditoria, resolvida na implementação): o
ambiente tem ~4 GB de RAM e nenhuma GPU; FastAPI/uvicorn já são a base do
próprio lain, então a interface não adiciona uma stack nova nem processos
extras. O servidor escuta 127.0.0.1 por padrão.

Uso (a partir de `ultron-2.0/`):

    python -m ultron_2_0.web
    python -m ultron_2_0.web --port 8765 --provider mock \\
        --database sqlite+aiosqlite:///:memory:
"""

from __future__ import annotations

from .app import create_app

__all__ = ["create_app"]
