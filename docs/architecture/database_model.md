# Modelo de Banco de Dados — ULTRON

O modelo de dados do ULTRON foi projetado para alta escalabilidade e simplicidade, utilizando chaves primárias UUIDv4 em formato string (compatível universalmente com SQLite e nativo em PostgreSQL).

## Diagrama Entidade-Relacionamento (ERD)

```mermaid
erDiagram
    CONVERSATION ||--o{ MESSAGE : contains

    CONVERSATION {
        string id PK "UUIDv4 string"
        string title "Título ou assunto inferido"
        string system_override "Instrução de sistema específica opcional"
        string provider "Provedor padrão da conversa (ex: gemini)"
        string model "Modelo específico usado na conversa"
        datetime created_at "Data/hora ISO 8601 UTC"
        datetime updated_at "Data/hora da última atividade"
    }

    MESSAGE {
        string id PK "UUIDv4 string"
        string conversation_id FK "Chave estrangeira referenciando CONVERSATION.id"
        string role "Papel: system | user | assistant"
        string content "Conteúdo textual da mensagem"
        string provider "Provedor que gerou a resposta (se assistant)"
        string model "Modelo que gerou a resposta"
        integer prompt_tokens "Tokens de entrada estimados/reportados"
        integer completion_tokens "Tokens gerados reportados"
        string raw_metadata "JSON serializado com metadados adicionais"
        datetime created_at "Data/hora ISO 8601 UTC"
    }
```

## Índices e Otimizações
1. `conversations.id`: Chave primária com índice B-tree único.
2. `conversations.updated_at`: Índice decrescente para recuperação rápida de conversas recentes (`ORDER BY updated_at DESC`).
3. `messages.conversation_id`: Índice para acelerar a busca de mensagens por conversa (`WHERE conversation_id = ?`).
4. `messages.created_at`: Índice composto `(conversation_id, created_at ASC)` para ordenação cronológica do histórico com mínima sobrecarga de I/O.
