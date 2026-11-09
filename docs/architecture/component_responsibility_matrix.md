# Matriz de Responsabilidade dos Componentes — ULTRON

| Camada | Componente / Arquivo | Responsabilidades Primárias | O que NÃO deve fazer |
|---|---|---|---|
| **API** | `app/api/routes/chat.py` | Receber requisição HTTP POST `/api/v1/chat`, delegar ao `Orchestrator`, retornar `ChatResponse`. | Não chama SDK de LLM diretamente; não executa queries de banco; não formata prompts. |
| **API** | `app/api/routes/health.py` | Receber requisição GET `/api/v1/health`, checar status do app e conectividade do banco/provedor. | Não altera estados do sistema; não manipula conversas. |
| **API** | `app/api/dependencies.py` | Prover injeção de dependências do FastAPI (sessão de banco, instâncias de serviços). | Não instancia regras de negócio ad-hoc. |
| **Core** | `app/core/orchestrator.py` | Coordenar o fluxo ponta a ponta: salvar input, recuperar contexto, compor prompt, chamar LLM, salvar output. | Não faz chamadas HTTP diretas; não implementa detalhes de drivers SQL ou SDKs específicos de LLM. |
| **Core** | `app/core/chat_service.py` | Gerenciar o ciclo de vida de conversas (criar, buscar, listar, recuperar histórico). | Não interage com provedores de IA; não formata system prompts. |
| **Core** | `app/core/context_manager.py` | Filtrar histórico de mensagens por limites de contagem e estimativa de tokens. | Não persiste dados; não decide qual provedor chamar. |
| **Intelligence** | `app/intelligence/providers/base.py` | Declarar interface abstrata `LLMProvider`, tipos de request/response e exceções normalizadas. | Não contém implementações concretas de fornecedores específicos. |
| **Intelligence** | `app/intelligence/providers/gemini.py` | Implementar `LLMProvider` para a API do Google Gemini usando o SDK oficial `google-genai`. | Não interage com o banco de dados; não formata templates de personalidade da aplicação. |
| **Intelligence** | `app/intelligence/providers/mock.py` | Provedor simulado previsível e rápido para testes automatizados e ambiente offline. | Não faz requisições de rede. |
| **Intelligence** | `app/intelligence/providers/registry.py` | Registrar, instanciar e fornecer provedores de LLM baseado em configuração (`ProviderRegistry`). | Não implementa a lógica de geração dos modelos. |
| **Intelligence** | `app/intelligence/prompt_engine.py` | Construir mensagens de sistema, aplicar diretrizes de personalidade e preparar payload de mensagens. | Não chama a API do LLM. |
| **Intelligence** | `app/intelligence/personality/` | Armazenar o prompt mestre e parâmetros de tom/estilo de resposta. | Não deve ter lógica executável acoplada. |
| **Database** | `app/database/connection.py` | Criar a engine SQLAlchemy assíncrona, scoped sessionmaker e inicializar schema. | Não define schemas de DTO de API. |
| **Database** | `app/database/models.py` | Declarar modelos relacionais SQLAlchemy (`ConversationModel`, `MessageModel`). | Não define validações HTTP de Pydantic. |
| **Database** | `app/database/repositories/` | Executar consultas e persistências no banco via queries assíncronas. | Não orquestra chamadas ao LLM nem monta respostas HTTP. |
| **Models** | `app/models/message.py` | Esquemas Pydantic para mensagens (UserMessage, AssistantMessage, MessageRole). | Não faz chamadas I/O nem queries. |
| **Models** | `app/models/conversation.py`| Esquemas Pydantic para conversas (ConversationCreate, ConversationResponse). | Não contém código de banco de dados. |
| **Config** | `app/config.py` | Carregar variáveis de ambiente com validação via `pydantic-settings`. | Não deve ter credenciais hardcoded. |
