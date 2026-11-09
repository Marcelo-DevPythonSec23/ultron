# ULTRON — Assistente Conversacional Modular em Python

ULTRON é um assistente conversacional arquitetado para operar com alta coesão, baixo acoplamento e extensibilidade entre múltiplos provedores de Modelos de Linguagem Grande (LLMs).

## Características
- **Arquitetura em Camadas:** Separação estrita entre API, Regras de Negócio (Core), Inteligência (LLM), Persistência e Modelos.
- **Abstração de Provedor:** Suporte nativo ao Google Gemini e provedor Mock para testes rápidos, preparado para OpenAI, Groq, Mistral e Ollama.
- **Persistência Assíncrona:** SQLite assíncrono via SQLAlchemy 2.0 e `aiosqlite`.
- **Validação com Pydantic v2:** Validação estrita de contratos de entrada e saída.

## Como Executar

### Pré-requisitos
- Python 3.12+
- `uv` ou `pip`

### Instalação
```bash
uv venv
source .venv/bin/activate
uv pip install -e ".[dev]"
```

### Configuração
Copie `.env.example` para `.env` e configure sua chave de API:
```bash
cp .env.example .env
```

### Executar a Aplicação
```bash
uvicorn app.main:app --reload --port 8000
```

### Executar Testes
```bash
pytest
```
