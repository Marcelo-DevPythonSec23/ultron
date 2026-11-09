# Fluxo de Dados do Sistema — ULTRON

Este documento descreve a sequência de eventos durante uma solicitação conversacional típica enviada à API do ULTRON.

## 1. Diagrama de Sequência de Chat

```mermaid
sequenceDiagram
    autonumber
    actor Cliente as Usuário / Cliente HTTP
    participant API as API Router (/api/v1/chat)
    participant Orch as Orchestrator
    participant ChatSvc as ChatService / Repository
    participant CtxMgr as ContextManager
    participant PromptEng as PromptEngine
    participant Registry as ProviderRegistry
    participant Provider as LLMProvider (Gemini / Mock)
    participant DB as SQLite DB (Async)

    Cliente->>API: POST /api/v1/chat { conversation_id, content }
    API->>Orch: handle_message(conversation_id, content, config_override)
    
    Orch->>ChatSvc: get_or_create_conversation(conversation_id)
    ChatSvc->>DB: SELECT / INSERT conversation
    DB-->>ChatSvc: ConversationEntity
    ChatSvc-->>Orch: ConversationEntity
    
    Orch->>ChatSvc: record_message(conversation_id, role="user", content)
    ChatSvc->>DB: INSERT message (user)
    DB-->>ChatSvc: MessageEntity
    ChatSvc-->>Orch: MessageEntity
    
    Orch->>ChatSvc: get_recent_messages(conversation_id, limit=MAX_HISTORY)
    ChatSvc->>DB: SELECT messages ORDER BY created_at ASC
    DB-->>ChatSvc: list[MessageEntity]
    ChatSvc-->>Orch: list[MessageEntity]
    
    Orch->>CtxMgr: build_context(messages, max_tokens)
    CtxMgr-->>Orch: filtered_context_messages
    
    Orch->>PromptEng: assemble_prompt(filtered_context_messages, personality)
    PromptEng-->>Orch: prompt_payload (system_instruction + formatted_history)
    
    Orch->>Registry: get_provider(provider_name)
    Registry-->>Orch: ProviderInstance (GeminiProvider)
    
    Orch->>Provider: generate_response(prompt_payload)
    Provider-->>Orch: LLMResponse (content, usage_metadata)
    
    Orch->>ChatSvc: record_message(conversation_id, role="assistant", content, metadata)
    ChatSvc->>DB: INSERT message (assistant)
    DB-->>ChatSvc: MessageEntity
    ChatSvc-->>Orch: MessageEntity
    
    Orch-->>API: ChatResponse (conversation_id, message_id, content, model, tokens)
    API-->>Cliente: 200 OK { response JSON }
```

## 2. Tratamento de Exceções e Resiliência no Fluxo

1. **Falha de Validação na Entrada:** Se o corpo da requisição tiver campos inválidos ou vazios, o FastAPI intercepta imediatamente no middleware Pydantic e devolve `422 Unprocessable Entity`.
2. **Falha de Conexão com o Provedor LLM:** Se a API externa do Gemini retornar erro de autenticação, cota excedida ou timeout, o `GeminiProvider` normaliza o erro em exceções de domínio (`ProviderAuthenticationError`, `ProviderRateLimitError`, `ProviderUnavailableError`). O `Orchestrator` ou middleware de exceção converte em HTTP 502/503/504 com payload padronizado, sem vazar tokens nem stack traces sensíveis.
3. **Falha no Banco de Dados:** Se a transação do banco falhar, a sessão assíncrona executa rollback explícito e a requisição retorna HTTP 500 com log estruturado de erro.
