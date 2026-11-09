# Roadmap de Desenvolvimento — ULTRON

| Fase | Título | Entregas Chave | Status |
|---|---|---|---|
| **Fase 0** | Inspeção do Repositório | Análise de ambiente, detecção do Python 3.12, configuração do `uv`, `git init`, `.gitignore`, `.env.example`. | Concluído |
| **Fase 1** | Especificação de Arquitetura | SAD, Matriz de Responsabilidades, Fluxo de Dados, Diagramas de Dependência e BD, Contrato de API, ADRs, Escopo MVP e Roadmap. | Concluído |
| **Fase 2** | Fundação do Projeto | `pyproject.toml`, gerenciador de configurações `config.py`, logging estruturado, app FastAPI, rota `/api/v1/health`, testes unitários de inicialização. | A Iniciar |
| **Fase 3** | Abstração de Provedor LLM | `LLMProvider` ABC, `GeminiProvider` com `google-genai`, `MockProvider`, `ProviderRegistry`, normalização de exceções e testes unitários com mocks. | Pendente |
| **Fase 4** | Motor Conversacional | `PersonalityConfig`, `PromptEngine`, `ContextManager`, `ChatService`, `Orchestrator` e testes de fluxo lógico. | Pendente |
| **Fase 5** | Persistência Relacional | Modelos SQLAlchemy assíncronos, repositórios de conversas e mensagens, integração no `Orchestrator` e rotas de histórico. | Pendente |
| **Fase 6** | Qualidade e Segurança | Validação rigorosa de inputs, tratamento global de exceções, mascaramento de segredos em logs, testes de integração de API. | Pendente |
| **Fase 7** | Validação Completa do MVP | Validação dos 8 critérios de aceitação do MVP, execução da suíte completa de testes e relatório final de entrega. | Pendente |
