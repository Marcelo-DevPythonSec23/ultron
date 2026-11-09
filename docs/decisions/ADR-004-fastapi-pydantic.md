# ADR-004: Utilização de FastAPI e Pydantic v2

## Status
Aceito

## Contexto
O ULTRON expõe uma interface de comunicação HTTP REST e necessita de alta performance, validação robusta de esquemas de dados, tipagem estática confiável e documentação OpenAPI interativa automática.

## Decisão
Adotar **FastAPI** como framework web e **Pydantic v2** (e `pydantic-settings`) para definição de esquemas de entrada/saída e gestão de variáveis de ambiente.

## Consequências
### Positivas:
- Validação automática de payloads HTTP em tempo de execução com mensagens de erro padronizadas.
- Documentação interativa Swagger UI (`/docs`) e ReDoc (`/redoc`) prontas sem esforço adicional.
- Suporte nativo a `async/await` com Uvicorn.
- Performance de serialização rápida proporcionada pelo core em Rust do Pydantic v2.

### Negativas / Mitigações:
- Atenção ao segregar schemas de DTO de API (`app/models`) das entidades de banco de dados (`app/database/models.py`) para evitar acoplamento de modelos ORM com respostas HTTP públicas.
