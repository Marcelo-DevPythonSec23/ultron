# Escopo do Produto Mínimo Viável (MVP) — ULTRON

## 1. O que ESTÁ no Escopo do MVP
- [x] Arquitetura modular em camadas (API, Core, Intelligence, Database, Models).
- [x] Configuração centralizada por variáveis de ambiente (`.env`) validada com Pydantic Settings.
- [x] Endpoint de Health Check (`GET /api/v1/health`) com verificação de status e dependências.
- [x] Interface abstrata de provedor de LLM (`LLMProvider`) com suporte a execução assíncrona.
- [x] Implementação concreta de integração com a API Google Gemini via SDK oficial `google-genai`.
- [x] Implementação de provedor `MockProvider` para execução de testes locais rápidos sem consumo de cota ou conexão de rede.
- [x] Registro centralizado de provedores (`ProviderRegistry`).
- [x] Mecanismo de Prompts e Personalidade configurável (`PromptEngine`) com suporte a templates externos e overrides por requisição.
- [x] Gerenciador de Contexto (`ContextManager`) com truncagem por quantidade de mensagens e limitação de tokens.
- [x] Orquestrador ponta a ponta (`Orchestrator`) conectando persistência, montagem de contexto, inteligência e resposta.
- [x] Persistência relacional assíncrona com SQLite (`aiosqlite`) e SQLAlchemy 2.0.
- [x] Endpoints REST:
  - `POST /api/v1/chat`: envio e processamento de mensagens.
  - `GET /api/v1/conversations`: listagem paginada de conversas.
  - `GET /api/v1/conversations/{id}/messages`: recuperação de histórico completo.
- [x] Cobertura abrangente de testes unitários e de integração com `pytest` e `pytest-asyncio`.
- [x] Higienização de logs para proteção de dados sensíveis e chaves de API.

## 2. O que NÃO ESTÁ no Escopo do MVP (Iterações Futuras)
- Execução de ferramentas externas pelo modelo (Function Calling / Tool Execution com privilégios de sistema).
- Autenticação e autorização multi-tenant com JWT / OAuth2 (focado inicialmente em uso pessoal local).
- Interface gráfica web (Frontend React/Vue) — o MVP provê API REST e documentação Swagger UI.
- Banco de dados vetorial para Retrieval-Augmented Generation (RAG) avançado ou memória semântica de longo prazo.
- Suporte a streaming de tokens via Server-Sent Events (SSE) ou WebSockets (planejado para v0.2.0).
