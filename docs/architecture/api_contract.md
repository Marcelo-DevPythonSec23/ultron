# Contrato de API HTTP REST — ULTRON v1

Prefixo Base: `/api/v1`

---

## 1. Endpoints

### 1.1 Health Check
- **Rota:** `GET /api/v1/health`
- **Descrição:** Verifica a integridade da aplicação, conectividade com o banco de dados e status do registro de provedores.
- **Resposta Sucesso (200 OK):**
```json
{
  "status": "healthy",
  "app_name": "ULTRON",
  "version": "0.1.0",
  "environment": "development",
  "database": "connected",
  "active_provider": "gemini",
  "available_providers": ["gemini", "mock"],
  "timestamp": "2026-11-09T03:00:00Z"
}
```

---

### 1.2 Envio de Mensagem de Chat
- **Rota:** `POST /api/v1/chat`
- **Descrição:** Envia uma mensagem para o ULTRON. Se `conversation_id` for omitido ou nulo, uma nova conversa é criada automaticamente.
- **Corpo da Requisição (Request Body):**
```json
{
  "conversation_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "message": "Explique a diferença entre acoplamento fraco e coesão forte.",
  "provider": "gemini",
  "model": "gemini-2.5-flash",
  "temperature": 0.7,
  "system_instruction_override": null
}
```
*Campos:*
- `conversation_id` (string UUID, opcional): Identificador da conversa existente.
- `message` (string, obrigatório, 1 a 32.000 caracteres): Mensagem do usuário.
- `provider` (string, opcional): Sobrescreve o provedor padrão para esta chamada.
- `model` (string, opcional): Sobrescreve o modelo padrão para esta chamada.
- `temperature` (float, opcional, 0.0 a 2.0): Parâmetro de aleatoriedade/criatividade.
- `system_instruction_override` (string, opcional): Sobrescreve a personalidade base para esta conversa.

- **Resposta Sucesso (200 OK):**
```json
{
  "conversation_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "message_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
  "role": "assistant",
  "content": "Acoplamento fraco refere-se ao grau de interdependência...",
  "provider": "gemini",
  "model": "gemini-2.5-flash",
  "usage": {
    "prompt_tokens": 128,
    "completion_tokens": 256,
    "total_tokens": 384
  },
  "created_at": "2026-11-09T03:00:02Z"
}
```

---

### 1.3 Listagem de Conversas
- **Rota:** `GET /api/v1/conversations`
- **Descrição:** Lista as conversas mais recentes com paginação.
- **Query Params:** `limit` (default: 20, max: 100), `offset` (default: 0).
- **Resposta Sucesso (200 OK):**
```json
{
  "total": 1,
  "items": [
    {
      "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
      "title": "Explique a diferença entre acoplamento...",
      "created_at": "2026-11-09T03:00:00Z",
      "updated_at": "2026-11-09T03:00:02Z",
      "message_count": 2
    }
  ]
}
```

---

### 1.4 Histórico de Mensagens de uma Conversa
- **Rota:** `GET /api/v1/conversations/{conversation_id}/messages`
- **Descrição:** Recupera todas as mensagens de uma conversa em ordem cronológica.
- **Resposta Sucesso (200 OK):**
```json
{
  "conversation_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "messages": [
    {
      "id": "1b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6a",
      "role": "user",
      "content": "Explique a diferença...",
      "created_at": "2026-11-09T03:00:00Z"
    },
    {
      "id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
      "role": "assistant",
      "content": "Acoplamento fraco refere-se...",
      "created_at": "2026-11-09T03:00:02Z"
    }
  ]
}
```

---

## 2. Respostas de Erro Padronizadas

Todas as falhas retornam payload estruturado:
```json
{
  "error": {
    "code": "PROVIDER_ERROR",
    "message": "Erro na comunicação com o modelo de inteligência.",
    "details": null,
    "timestamp": "2026-11-09T03:00:05Z"
  }
}
```
Códigos de erro padronizados:
- `VALIDATION_ERROR` (HTTP 422)
- `NOT_FOUND` (HTTP 404)
- `AUTHENTICATION_ERROR` (HTTP 401)
- `RATE_LIMIT_EXCEEDED` (HTTP 429)
- `PROVIDER_ERROR` (HTTP 502)
- `INTERNAL_SERVER_ERROR` (HTTP 500)
