# Diagrama de Dependências entre Módulos — ULTRON

Este documento formaliza as regras de dependência estrita entre os módulos do sistema, garantindo a preservação da regra de dependência da Clean Architecture: dependências apontam para dentro (em direção ao domínio e abstrações).

```mermaid
graph TD
    classDef api fill:#4a90e2,stroke:#1a5276,color:#fff;
    classDef core fill:#27ae60,stroke:#196f3d,color:#fff;
    classDef intel fill:#8e44ad,stroke:#5b2c6f,color:#fff;
    classDef db fill:#e67e22,stroke:#935116,color:#fff;
    classDef models fill:#f39c12,stroke:#b9770e,color:#fff;
    classDef config fill:#7f8c8d,stroke:#34495e,color:#fff;

    API[app.api]::api
    Core[app.core]::core
    Intelligence[app.intelligence]::intel
    Database[app.database]::db
    Models[app.models]::models
    Config[app.config]::config

    API --> Core
    API --> Models
    API --> Config

    Core --> Models
    Core --> Config
    Core --> Intelligence
    Core --> Database

    Intelligence --> Models
    Intelligence --> Config

    Database --> Models
    Database --> Config
```

## Regras de Dependência Mandatórias
1. **`app.models`** é um módulo folha de domínio de dados (estruturas Pydantic/dataclasses puras). Não importa nada de `app.api`, `app.core`, `app.database` ou `app.intelligence`.
2. **`app.intelligence.providers.base`** depende exclusivamente de `app.models` e tipos padrão do Python.
3. **`app.database`** não importa módulos da camada `app.api` nem `app.intelligence`.
4. **`app.intelligence`** não importa módulos de banco de dados (`app.database`). A camada de persistência desconhece o provedor de IA e vice-versa.
5. **`app.api`** orquestra dependências através de injeção (`FastAPI.Depends`), nunca instanciando clientes de rede brutos dentro dos manipuladores de rota.
