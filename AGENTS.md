# ULTRON 2.1 — DIRETRIZES MESTRAS DE ENGENHARIA

**Projeto:** ULTRON  
**Versão:** 2.1  
**Etapa de desenvolvimento:** Pós-integração / Arquitetura Multiagente  
**Linguagem principal:** Python 3.12  
**Ambiente:** Linux  
**Diretório principal:** `ultron-2.0/`

---

# 1. OBJETIVO DO PROJETO

Dar continuidade ao desenvolvimento do ULTRON após a conclusão bem-sucedida do plano original de integração, composto pelas Etapas 0–10.

O objetivo é evoluir o ULTRON de um assistente de IA com memória persistente, ferramentas, voz e HUD para um sistema inteligente modular, extensível e multiagente.

O sistema deverá adquirir progressivamente capacidade para:

- Coordenar múltiplos provedores de IA.
- Delegar tarefas a agentes externos de programação.
- Gerenciar agentes especializados.
- Planejar e executar fluxos de trabalho complexos.
- Avaliar e validar resultados produzidos por agentes.
- Manter memória contextual persistente.
- Interagir com sistemas externos por interfaces controladas.
- Recuperar-se de falhas.
- Operar autonomamente dentro de permissões explicitamente definidas.

O ULTRON deve continuar sendo a autoridade central de conversação, memória e orquestração.

Não reconstruir infraestruturas já implementadas sem justificativa técnica comprovada.

# 2. ARQUITETURA ATUAL

Os componentes abaixo já foram implementados e devem ser tratados como infraestrutura existente.

## 2.1 Núcleo

- Orchestrator original do Lain reutilizado sem modificações.
- OrchestratorBridge.
- CoreRuntime.
- Histórico conversacional único.
- Banco SQLite isolado em `ultron-2.0/data/ultron2.db`.
- ProviderRegistry.
- ToolCallingProvider.
- ToolGateway.

## 2.2 Engenharia de Memória

- MemoryEngine.
- MemoryInjectionProvider.
- Integração com FactMemory.
- Memória persistente.
- Cinco tipos de memória:
  - working
  - episodic
  - semantic
  - procedural
  - user
- Isolamento por escopos.
- Níveis de confiança.
- Etiquetas (tags).
- Retenção e TTL.
- Deduplicação.
- Histórico de versões.
- Exclusão autorizada.
- Consolidação somente leitura.
- Recuperação lexical.
- Injeção contextual com orçamento de caracteres.
- Auditoria de memória.

Armazenamento canônico:

- `data/memory.json`
- `data/memory_records.json`
- `data/memory_history.json`

## 2.3 Interfaces

- CLI.
- HUD Web.
- VoicePipeline.
- STT Gemini Live.
- TTS Gemini.
- SystemSpeaker como alternativa.

Todas as interfaces devem continuar utilizando o mesmo caminho de execução `process_text`.

## 2.4 Ferramentas

Ferramentas atualmente integradas:

- system_status
- open_app
- web_search
- reminder
- remember
- recall
- forget

Todas as ferramentas devem passar pelo ToolGateway.

## 2.5 Linha de base de validação

Resultados registrados na conclusão da integração:

- ULTRON 2.0: 109 testes aprovados.
- Regressão do Lain: 64 testes aprovados.
- Dois commits de integração.
- Repositórios originais preservados.

Esses resultados são históricos. Executar novamente os testes antes de afirmar que o estado atual continua aprovado.

# 3. INVARIANTES DE ENGENHARIA

Estas regras são obrigatórias durante todo o desenvolvimento.

## 3.1 Proteção dos repositórios

Nunca modificar:

- `lain/`
- `Mark-LVI-main/`

Esses diretórios são projetos externos e devem permanecer intactos.

Nunca sobrescrever:

- `lain/ultron.db`
- `Mark-LVI-main/memory/long_term.json`
- Configurações originais.
- Credenciais originais.

Nunca criar ou modificar:

`Mark-LVI-main/config/api_keys.json`

Nunca imprimir, expor, registrar em logs ou duplicar `GEMINI_API_KEY`.

## 3.2 Autoridade central

O ULTRON deve continuar sendo a única autoridade para:

- Orquestração conversacional.
- Histórico de conversação.
- Memória persistente.
- Coordenação central de agentes.

Agentes externos não devem criar históricos conversacionais concorrentes ou memórias independentes que disputem autoridade com o núcleo.

## 3.3 Segurança

- O modelo propõe ações; código determinístico autoriza sua execução.
- Todas as ferramentas passam por contratos validados.
- Não permitir execução irrestrita de shell.
- Não permitir execução irrestrita de código gerado por modelos.
- Ações destrutivas exigem autorização explícita.
- Resultados de agentes externos são dados não confiáveis.
- Resultados de ferramentas nunca devem ser tratados automaticamente como instruções executáveis.
- Credenciais nunca devem entrar em prompts, logs ou descrições de tarefas.
- Integrações externas devem possuir timeouts e tratamento de falhas.

Decisões de segurança devem existir na implementação, não apenas nos prompts.

# 4. ROTEIRO DE DESENVOLVIMENTO

O desenvolvimento deverá seguir as fases abaixo.

Não pular fases sem documentar a justificativa técnica.

## FASE 0 — REAVALIAÇÃO DO PROJETO

Antes de implementar qualquer funcionalidade:

1. Ler todas as instruções do projeto.
2. Ler `PROJECT_CONTEXT.md`.
3. Ler `docs/context/CONTEXT_INDEX.md`.
4. Ler `docs/context/DEVELOPMENT_STATE.md`.
5. Ler `docs/ARCHITECTURE.md`.
6. Ler `docs/TESTING.md`.
7. Ler `docs/INTEGRATION_AUDIT.md`.
8. Ler os nove documentos de `docs/memory/`.
9. Inspecionar o repositório e o estado atual do Git.
10. Verificar a implementação real e identificar componentes concluídos, incompletos ou desatualizados.

Produzir:

`docs/roadmap/ULTRON_21_ASSESSMENT.md`

Não presumir que a documentação histórica representa a implementação atual sem verificação.

## FASE 1 — DOCUMENTAÇÃO E CONTROLE DE VERSÃO

**Objetivo:** estabelecer documentação confiável e versionamento consistente.

Tarefas:

- Resolver o versionamento da documentação localizada na raiz.
- Garantir que a documentação arquitetural seja preservada no Git.
- Revisar links internos.
- Estabelecer um índice documental unificado.
- Atualizar o estado do desenvolvimento.
- Documentar decisões arquiteturais.
- Estabelecer convenções de versionamento.

Critérios de conclusão:

- Nenhuma documentação importante deve permanecer fora do controle de versão sem justificativa.
- Todas as referências internas devem ser válidas.
- A documentação deve representar a implementação real.
- Registros históricos devem ser preservados.

## FASE 2 — SISTEMA DE AUTORIZAÇÃO INTERATIVA

**Objetivo:** implementar autorização interativa real para operações sensíveis.

Componentes:

- AuthorizationManager.
- PendingAction.
- ApprovalToken.
- Controle de expiração.
- Proteção contra reutilização de tokens.
- Confirmação pela CLI.
- Confirmação pelo HUD.
- Integração com auditoria.

Requisitos:

- Vincular a autorização à ferramenta e aos argumentos exatos.
- Utilizar tokens temporários e de uso único.
- Rejeitar tokens expirados ou reutilizados.
- Rejeitar argumentos modificados.
- Separar autorização de execução.
- Nunca permitir que o modelo aprove suas próprias operações.

Não implementar autorização por voz sem mecanismo confiável de autenticação.

Critérios de conclusão:

- Autorização funcional pela CLI e HUD.
- Operações destrutivas sem possibilidade de contornar a autorização.
- Testes de replay, expiração e concorrência.
- Compatibilidade preservada com os contratos existentes do ToolGateway.

## FASE 3 — MODEL ROUTER

**Objetivo:** permitir que o ULTRON selecione e coordene diferentes provedores de modelos de IA.

Componentes previstos:

- ModelRouter.
- ProviderAdapter.
- ModelRegistry.
- ModelCapabilities.
- ModelSelectionPolicy.
- FallbackManager.
- RetryManager.
- Métricas de provedores.

Requisitos:

- Suportar múltiplos provedores.
- Permitir configuração independente por provedor.
- Identificar capacidades e limitações de cada modelo.
- Selecionar modelos conforme o tipo de tarefa.
- Permitir fallback em caso de indisponibilidade.
- Implementar timeout e retry com backoff.
- Preservar o ProviderRegistry existente.
- Não acoplar o núcleo a um único fornecedor.
- Não expor credenciais durante o roteamento.

O ModelRouter deve ser uma camada de seleção e encaminhamento, não um segundo orquestrador conversacional.

Critérios de conclusão:

- Pelo menos dois provedores integrados e efetivamente testados.
- Seleção de modelo validada.
- Fallback testado.
- Falhas de provedores isoladas.
- Configurações e credenciais protegidas.

## FASE 4 — SISTEMA MULTIAGENTE

**Objetivo:** permitir que o ULTRON coordene agentes especializados e delegue tarefas.

Arquitetura prevista:

- AgentOrchestrator.
- AgentRegistry.
- AgentExecutor.
- AgentTask.
- TaskQueue.
- AgentCommunication.
- ResultManager.
- AgentValidator.
- ExecutionMonitor.

Agentes iniciais sugeridos:

1. Developer Agent: implementação e manutenção de código.
2. Research Agent: pesquisa técnica e documentação.
3. Security Agent: auditoria e análise de segurança.
4. QA Agent: testes e validação.
5. Database Agent: arquitetura e gerenciamento de dados.
6. Architecture Agent: revisão de arquitetura e decisões técnicas.

Requisitos:

- Agentes possuem responsabilidades delimitadas.
- Cada agente recebe contexto específico para sua tarefa.
- A comunicação utiliza contratos estruturados.
- Resultados são enviados ao ULTRON para avaliação.
- Agentes não podem modificar diretamente a memória canônica sem autorização.
- Alterações de código devem possuir isolamento e rastreabilidade.
- Tarefas concorrentes devem evitar conflitos de arquivos.
- Resultados devem possuir identificação de origem.
- Falhas de agentes devem ser detectadas e registradas.

A primeira implementação deverá utilizar agentes externos existentes sempre que tecnicamente viável.

Não criar modelos próprios para funcionalidades já oferecidas por ferramentas existentes.

Critérios de conclusão:

- Registro e descoberta de agentes.
- Delegação funcional.
- Execução de tarefas.
- Retorno estruturado de resultados.
- Validação dos resultados.
- Tratamento de falhas.
- Testes de concorrência e isolamento.

## FASE 5 — INTEGRAÇÃO COM AGENTES CLI E MCP

**Objetivo:** conectar o ULTRON a ferramentas e agentes externos.

Integrações prioritárias:

- OpenCode.
- Claude Code.
- Outros agentes CLI compatíveis.
- Servidores MCP.

Requisitos:

- Inspecionar as interfaces reais de cada ferramenta.
- Não inventar comandos, APIs ou contratos.
- Utilizar adaptadores independentes.
- Isolar processos externos.
- Aplicar limites de execução.
- Registrar tarefas e resultados.
- Controlar permissões por integração.
- Permitir desativar individualmente cada integração.

O ULTRON deverá conseguir encaminhar tarefas especializadas a agentes externos e receber seus resultados sem perder o controle central do fluxo de execução.

Critérios de conclusão:

- Pelo menos uma integração CLI funcional.
- Pelo menos uma integração MCP funcional.
- Comunicação validada.
- Tratamento de timeout e falhas.
- Permissões verificadas.

## FASE 6 — EVOLUÇÃO DA MEMÓRIA

**Objetivo:** expandir a capacidade de recuperação e relacionamento de informações.

Funcionalidades previstas:

- Embeddings opcionais.
- Busca semântica.
- Recuperação híbrida.
- Relações entre memórias.
- Memória episódica aprimorada.
- Métricas de qualidade da recuperação.
- Criptografia em repouso.
- Backup e restauração.

Requisitos:

- Preservar o MemoryEngine.
- Manter compatibilidade com os tipos e escopos existentes.
- Não tornar embeddings uma dependência obrigatória.
- Não permitir que consolidação altere silenciosamente fatos.
- Preservar histórico e rastreabilidade.
- Manter exclusão autorizada.
- Garantir isolamento entre escopos.

Critérios de conclusão:

- Recuperação semântica testada.
- Recuperação lexical preservada.
- Backup e restauração validados.
- Criptografia testada.
- Compatibilidade com memória existente.

## FASE 7 — AUTONOMIA OPERACIONAL

**Objetivo:** permitir que o ULTRON planeje e execute fluxos de trabalho complexos.

Componentes previstos:

- Planner.
- TaskDecomposer.
- WorkflowEngine.
- ExecutionMonitor.
- Scheduler.
- RecoveryManager.
- StateTracker.

Capacidades:

- Receber objetivos complexos.
- Decompor objetivos em tarefas.
- Identificar dependências.
- Distribuir tarefas entre agentes.
- Acompanhar execução.
- Avaliar resultados intermediários.
- Replanejar após falhas.
- Retomar trabalhos interrompidos.
- Produzir relatórios de execução.

Requisitos:

- Separar planejamento de execução.
- Aplicar limites de recursos e tempo.
- Exigir autorização para ações sensíveis.
- Registrar decisões e resultados.
- Evitar loops de execução.
- Implementar limites de tentativas.
- Preservar possibilidade de interrupção humana.

Critérios de conclusão:

- Workflows executáveis.
- Persistência de estado.
- Recuperação após falhas.
- Monitoramento de tarefas.
- Aprovação humana para operações sensíveis.

## FASE 8 — VALIDAÇÃO E ESTABILIZAÇÃO

**Objetivo:** validar a arquitetura completa e preparar uma versão estável.

Executar:

- Testes unitários.
- Testes de integração.
- Testes de regressão.
- Testes de concorrência.
- Testes de segurança.
- Testes de falhas de provedores.
- Testes de agentes externos.
- Testes de recuperação.
- Testes de integridade da memória.
- Testes de compatibilidade das interfaces.

Documentar:

- Arquitetura final.
- Componentes implementados.
- Dependências.
- Limitações.
- Resultados de testes.
- Riscos identificados.
- Decisões arquiteturais.
- Próximas etapas.

Produzir:

`docs/roadmap/ULTRON_21_FINAL_REPORT.md`

Não declarar uma fase concluída sem evidências verificáveis.

# 5. PADRÃO DE ENGENHARIA MULTIAGENTE

Todos os agentes devem respeitar os seguintes princípios:

1. Especialização: cada agente possui uma responsabilidade definida.
2. Isolamento: cada tarefa recebe apenas o contexto necessário.
3. Rastreabilidade: toda tarefa possui identificação e estado.
4. Comunicação estruturada: resultados seguem contratos definidos.
5. Validação: nenhum resultado é considerado correto apenas porque foi produzido por uma IA.
6. Segurança: agentes não possuem permissões ilimitadas.
7. Recuperação: falhas não devem comprometer o núcleo.
8. Supervisão: o ULTRON mantém autoridade sobre a coordenação.

Os agentes não devem compartilhar indiscriminadamente seus contextos.

A memória central permanece sob responsabilidade do ULTRON.

# 6. PADRÃO DE DESENVOLVIMENTO

Antes de implementar:

- Inspecionar os arquivos envolvidos.
- Identificar dependências.
- Ler os contratos existentes.
- Verificar os testes relacionados.
- Identificar possíveis conflitos.

Durante a implementação:

- Preservar compatibilidade.
- Evitar duplicação de responsabilidades.
- Criar componentes modulares.
- Aplicar tipagem quando apropriado.
- Tratar exceções explicitamente.
- Registrar operações relevantes.
- Criar testes para novas funcionalidades.

Depois da implementação:

- Executar testes.
- Revisar alterações.
- Verificar regressões.
- Atualizar documentação.
- Registrar limitações.
- Apresentar evidências.

Não realizar commits sem validar o estado do Git e apresentar os resultados.

# 7. GERENCIAMENTO DE TAREFAS

Toda tarefa de engenharia deve possuir:

- Identificador.
- Objetivo.
- Descrição.
- Agente responsável.
- Dependências.
- Arquivos envolvidos.
- Permissões.
- Estado de execução.
- Resultado.
- Evidências de validação.

Estados permitidos:

- pending
- assigned
- running
- blocked
- review
- completed
- failed
- cancelled

O AgentOrchestrator deve controlar o ciclo de vida das tarefas.

Não considerar uma tarefa concluída apenas porque um agente informou que terminou.

# 8. GERENCIAMENTO DE CONTEXTO

Toda implementação deve consultar a documentação existente antes de tomar decisões arquiteturais.

Fontes prioritárias:

- `PROJECT_CONTEXT.md`
- `docs/context/CONTEXT_INDEX.md`
- `docs/context/DEVELOPMENT_STATE.md`
- `docs/ARCHITECTURE.md`
- `docs/TESTING.md`
- `docs/memory/`

O contexto fornecido aos agentes deve ser específico para suas responsabilidades.

Evitar enviar todo o histórico conversacional para todos os agentes.

Os agentes devem receber informações relevantes, atualizadas e verificáveis.

# 9. OBSERVABILIDADE

A arquitetura deverá registrar:

- Identificador da tarefa.
- Agente responsável.
- Provedor utilizado.
- Tempo de execução.
- Estado da tarefa.
- Falhas.
- Tentativas.
- Resultado da validação.
- Consumo de recursos quando disponível.

Não registrar credenciais, conteúdo sensível ou dados privados desnecessários.

# 10. CRITÉRIOS GERAIS DE CONCLUSÃO

Uma funcionalidade somente poderá ser declarada concluída quando:

1. A implementação existir.
2. Os contratos estiverem definidos.
3. Os testes relevantes forem executados.
4. Os resultados forem registrados.
5. As regressões forem verificadas.
6. A documentação estiver atualizada.
7. As limitações forem identificadas.
8. Os riscos de segurança forem avaliados.

Se algum requisito não puder ser validado, declarar explicitamente como incompleto.

# 11. RELATÓRIO OBRIGATÓRIO

Ao finalizar cada fase, produzir um relatório contendo:

A. Objetivo da fase.

B. Auditoria da implementação anterior.

C. Arquitetura implementada.

D. Arquivos criados, modificados e removidos.

E. Dependências adicionadas.

F. Testes executados e resultados.

G. Verificações de segurança.

H. Limitações e funcionalidades pendentes.

I. Próximas etapas recomendadas.

J. Estado do Git e commits, quando existentes.

# 12. FILOSOFIA DE DESENVOLVIMENTO

O ULTRON deve ser desenvolvido como um sistema modular, verificável e extensível.

Prioridades:

1. Integridade arquitetural.
2. Segurança.
3. Confiabilidade.
4. Modularidade.
5. Observabilidade.
6. Eficiência.
7. Autonomia progressiva.

Não confundir autonomia com ausência de controle.

Não confundir quantidade de agentes com inteligência.

Não confundir código gerado com código validado.

Não introduzir complexidade sem benefício arquitetural demonstrável.

**Diretriz central: o ULTRON deve coordenar inteligência, ferramentas e agentes externos sem perder sua própria integridade arquitetural.**

---

**ESTADO INICIAL DESTE CICLO**

- Integração original: Etapas 0–10 concluídas conforme relatório anterior.
- Próximo ciclo: Fase 0 — Reavaliação do projeto.
- Primeira prioridade: Fase 1 — Documentação e controle de versão.
- Próxima grande expansão: Model Router e Sistema Multiagente.

Este documento estabelece o roteiro de desenvolvimento, não declara nenhuma das novas fases concluída antecipadamente.