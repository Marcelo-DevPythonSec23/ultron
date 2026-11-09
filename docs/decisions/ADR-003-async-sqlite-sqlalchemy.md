# ADR-003: Persistência Assíncrona com SQLite e SQLAlchemy 2.0

## Status
Aceito

## Contexto
O MVP do ULTRON precisa armazenar conversas e mensagens localmente de forma simples e sem exigir instalação de servidores de banco pesados no ambiente de desenvolvimento do usuário. Ao mesmo tempo, o sistema deve ser preparado para futura migração para PostgreSQL sem reescrita de código de negócio.

## Decisão
Utilizar o **SQLAlchemy 2.0** no modo puramente assíncrono (`async_sessionmaker`, `AsyncEngine`) acoplado ao driver `aiosqlite` para SQLite.
Isolar todas as consultas atrás do padrão **Repository**:
- `ConversationRepository`
- `MessageRepository`

## Consequências
### Positivas:
- Arquivo de banco local zero-configuration (`ultron.db`) para o MVP.
- Operações de I/O não bloqueiam o event loop do FastAPI.
- A migração futura para PostgreSQL requer unicamente a alteração da string de conexão `DATABASE_URL` (ex: `postgresql+asyncpg://...`) e migrações Alembic.

### Negativas / Mitigações:
- SQLite possui concorrência de escrita limitada em ambientes multi-processo. Mitigado habilitando o modo WAL (`journal_mode = WAL`) na inicialização da conexão.
