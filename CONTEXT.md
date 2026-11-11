# MEGA PROMPT — CONTEXT ENGINEERING DO ULTRON 2.0
## Sistema centralizado de contexto, conhecimento e memória arquitetural para agentes de IA

Você é responsável por implementar um sistema de Context Engineering para o projeto ULTRON 2.0.

O objetivo é permitir que qualquer agente de IA que trabalhe no projeto consiga compreender:

- O que é o ULTRON.
- Qual é sua finalidade.
- Como sua arquitetura funciona.
- Quais são seus módulos.
- Como os componentes se comunicam.
- Quais decisões arquiteturais já foram tomadas.
- O que já foi implementado.
- O que está parcialmente implementado.
- O que ainda precisa ser desenvolvido.
- Quais limitações técnicas existem.
- Quais alterações foram realizadas anteriormente.
- Quais documentos devem ser consultados para cada tarefa.

O sistema deve reduzir a necessidade de explicar repetidamente o projeto aos agentes.

Não quero apenas um arquivo enorme com informações sobre o ULTRON.

Quero uma estrutura organizada de contexto, capaz de fornecer informações relevantes aos agentes conforme a tarefa executada.

---

# 1. PRIMEIRO: INVESTIGAÇÃO DO PROJETO

Antes de criar arquivos, investigue o repositório completo.

Examine:

- Estrutura de diretórios.
- Código-fonte.
- Documentação.
- READMEs.
- Arquivos AGENTS.md.
- Configurações.
- Testes.
- Relatórios de auditoria.
- Documentos de integração.
- Decisões arquiteturais.
- Histórico disponível de desenvolvimento.

Existe um acervo documental extenso, com aproximadamente 400 documentos e auditorias.

Esse acervo é uma fonte importante para reconstruir o contexto do projeto.

Não ignore documentos antigos simplesmente por sua data.

Verifique se ainda representam decisões válidas, se foram substituídos ou se descrevem implementações anteriores.

Não presuma que todos os documentos estão corretos.

Não invente informações ausentes.

Não transforme hipóteses em fatos.

Não altere os documentos originais durante a investigação.

## Entregável

Crie:

`docs/context/CONTEXT_AUDIT.md`

Registre:

1. O contexto atualmente disponível.
2. Documentações encontradas.
3. Informações arquiteturais identificadas.
4. Decisões confirmadas.
5. Informações contraditórias.
6. Lacunas de conhecimento.
7. Documentos obsoletos ou substituídos.
8. Fontes de informação mais confiáveis.
9. Recomendações para organização do contexto.

---

# 2. ARQUITETURA DO SISTEMA DE CONTEXTO

Implemente uma estrutura hierárquica.

A organização deve separar contexto global, contexto arquitetural, contexto dos módulos e contexto específico das tarefas.

Estrutura de referência:

```text
ultron-2.0/
│
├── AGENTS.md
│
├── PROJECT_CONTEXT.md
│
├── docs/
│   ├── context/
│   │   ├── CONTEXT_INDEX.md
│   │   ├── CONTEXT_AUDIT.md
│   │   ├── PROJECT_OVERVIEW.md
│   │   ├── ARCHITECTURE_CONTEXT.md
│   │   ├── DEVELOPMENT_STATE.md
│   │   ├── TECHNICAL_DECISIONS.md
│   │   ├── MODULE_MAP.md
│   │   ├── DEPENDENCY_MAP.md
│   │   ├── KNOWN_LIMITATIONS.md
│   │   ├── GLOSSARY.md
│   │   └── agents/
│   │       ├── ARCHITECT_AGENT.md
│   │       ├── BACKEND_AGENT.md
│   │       ├── INTEGRATION_AGENT.md
│   │       ├── VOICE_AGENT.md
│   │       ├── SECURITY_AGENT.md
│   │       └── QA_AGENT.md
│   │
│   ├── architecture/
│   ├── integrations/
│   ├── security/
│   └── testing/
│
└── ...
```

Essa estrutura é uma referência.

Adapte-a à organização real do repositório.

Não crie arquivos redundantes apenas para preencher a estrutura.

---

# 3. PROJECT_CONTEXT.md — CONTEXTO GLOBAL

Crie um documento central:

`PROJECT_CONTEXT.md`

Ele deve fornecer uma visão geral suficientemente completa para um agente compreender o projeto antes de começar a trabalhar.

Inclua:

## Identidade

- Nome: ULTRON 2.0.
- Objetivo geral do projeto.
- Problema que o sistema pretende resolver.
- Visão de longo prazo.
- Princípios fundamentais de desenvolvimento.

## Origem

Explique a relação entre:

- `lain/`
- `Mark-LVI-main/`
- `ultron-2.0/`

Considere a documentação existente para determinar quais componentes foram preservados, adaptados, reimplementados ou descartados.

Não confunda projetos de origem com o sistema final.

## Arquitetura

Descreva:

- Núcleo inteligente.
- Orquestrador.
- Provedores de IA.
- Memória.
- Ferramentas.
- Gateway.
- Voz.
- Interfaces.
- Integrações.
- Infraestrutura.

Use exclusivamente informações confirmadas pelo código e pela documentação.

## Estado atual

Explique o que está:

- Implementado.
- Parcialmente implementado.
- Planejado.
- Descontinuado.
- Bloqueado.

Não classifique funcionalidades como implementadas apenas porque existem arquivos ou classes com seus nomes.

## Restrições

Registre:

- Requisitos de hardware.
- Dependências externas.
- Limitações conhecidas.
- Restrições de segurança.
- Compatibilidade.
- Configurações relevantes.

---

# 4. CONTEXT_INDEX.md — ÍNDICE DE CONHECIMENTO

Crie:

`docs/context/CONTEXT_INDEX.md`

Esse documento será o ponto de entrada para a documentação do projeto.

Ele deve funcionar como um mapa de conhecimento.

Organize os documentos por assunto.

Exemplo:

| Assunto | Documentos | Quando consultar |
|---|---|---|
| Arquitetura | ARCHITECTURE.md | Alterações estruturais |
| Voz | VOICE_PIPELINE.md | STT, TTS e áudio |
| Ferramentas | TOOLS.md | Integração de tools |
| Segurança | SECURITY.md | Permissões e execução |
| Testes | TESTING.md | Testes e regressão |
| Integração | INTEGRATION_MAP.md | Lain e Mark-LVI |
| Contexto | PROJECT_CONTEXT.md | Compreensão geral |

Adapte a tabela aos documentos realmente encontrados.

Para cada documento, registre:

- Caminho.
- Assunto.
- Descrição.
- Autoridade documental.
- Estado de atualização.
- Documentos relacionados.

O índice não deve inventar documentos que não existem.

---

# 5. CONTEXT LOADING — CARREGAMENTO SELETIVO

O agente não deve carregar todas as documentações em todas as tarefas.

Implemente uma estratégia de carregamento progressivo.

## Nível 1 — Contexto essencial

Sempre consultar:

- AGENTS.md.
- PROJECT_CONTEXT.md.
- CONTEXT_INDEX.md.

## Nível 2 — Contexto arquitetural

Consultar quando a tarefa envolver arquitetura:

- ARCHITECTURE_CONTEXT.md.
- MODULE_MAP.md.
- DEPENDENCY_MAP.md.
- TECHNICAL_DECISIONS.md.

## Nível 3 — Contexto especializado

Carregar conforme a tarefa:

- Voz: VOICE_PIPELINE.md.
- Ferramentas: TOOLS.md.
- Segurança: SECURITY.md.
- Testes: TESTING.md.
- Integração: INTEGRATION_MAP.md.

## Nível 4 — Contexto histórico

Consultar documentos históricos, auditorias e registros anteriores quando necessário.

Não carregue o histórico inteiro automaticamente.

Priorize informações atuais e fontes diretamente relacionadas à tarefa.

---

# 6. TECHNICAL_DECISIONS.md — MEMÓRIA DE DECISÕES

Crie um registro de decisões arquiteturais.

Cada decisão deve conter:

- Identificador.
- Data.
- Título.
- Contexto.
- Problema.
- Alternativas consideradas.
- Decisão adotada.
- Justificativa.
- Consequências.
- Estado: proposta, aceita, substituída ou rejeitada.
- Fontes relacionadas.

Use uma estrutura inspirada em Architecture Decision Records (ADR).

Exemplo conceitual:

```markdown
# ADR-001 — Orquestrador central

Status: Aceita

## Contexto
Existem dois projetos de origem com responsabilidades distintas.

## Decisão
O ULTRON será responsável pela orquestração central.

## Justificativa
Evitar múltiplos núcleos conversacionais independentes.

## Consequências
Os módulos operacionais devem se comunicar com o núcleo
por interfaces explícitas.
```

Não invente decisões históricas.

Quando uma decisão for inferida, identifique-a como inferência e aguarde validação.

---

# 7. DEVELOPMENT_STATE.md — ESTADO DO DESENVOLVIMENTO

Crie um documento que represente o estado técnico atual.

Ele deve registrar:

- Módulos existentes.
- Funcionalidades implementadas.
- Funcionalidades parciais.
- Funcionalidades pendentes.
- Testes existentes.
- Problemas conhecidos.
- Dependências.
- Próximos objetivos.

Cada funcionalidade deve possuir uma classificação:

- `IMPLEMENTED`
- `PARTIAL`
- `PLANNED`
- `BLOCKED`
- `DEPRECATED`
- `UNKNOWN`

Inclua evidências sempre que possível:

- Arquivos.
- Classes.
- Funções.
- Testes.
- Documentação.

Não confunda planejamento com implementação.

---

# 8. MODULE_MAP.md — MAPA DOS MÓDULOS

Crie um mapa dos módulos reais do ULTRON.

Para cada módulo, registre:

- Nome.
- Responsabilidade.
- Diretório.
- Entrypoint.
- Dependências.
- Interfaces públicas.
- Entradas.
- Saídas.
- Estado de implementação.
- Testes associados.
- Documentação relacionada.

O objetivo é permitir que um agente localize rapidamente onde deve trabalhar.

Evite descrições genéricas como "módulo responsável por processar informações".

Explique concretamente o que o módulo faz no código existente.

---

# 9. AGENT CONTEXT — CONTEXTO ESPECIALIZADO

Crie documentos de contexto para os diferentes papéis de agentes.

Cada documento deve informar:

- Responsabilidade do agente.
- Partes do sistema relevantes.
- Documentos obrigatórios.
- Interfaces que precisa respeitar.
- Restrições.
- Testes que deve executar.
- Critérios de conclusão.
- Agentes ou módulos com os quais precisa coordenar.

Os documentos devem orientar os agentes sem criar autoridades conflitantes.

Um agente especializado não pode modificar decisões arquiteturais globais unilateralmente.

Se encontrar necessidade de mudança estrutural, deve documentar a proposta e solicitar revisão.

---

# 10. RASTREABILIDADE E CONFIABILIDADE

Toda informação importante do contexto deve possuir uma origem identificável.

Diferencie:

- Fato confirmado pelo código.
- Fato documentado.
- Decisão arquitetural aprovada.
- Hipótese.
- Inferência.
- Informação histórica.
- Informação não verificada.

Quando houver contradição:

1. Identifique as fontes.
2. Verifique a implementação atual.
3. Verifique os testes.
4. Consulte decisões registradas.
5. Registre a divergência.
6. Não resolva silenciosamente.

A documentação não deve ser tratada automaticamente como mais confiável que o código.

O código também não deve ser tratado automaticamente como prova de que uma decisão arquitetural foi intencional.

Preserve a distinção entre intenção, implementação e validação.

---

# 11. MANUTENÇÃO AUTOMÁTICA DO CONTEXTO

Estabeleça regras para manter os documentos atualizados.

Sempre que uma alteração relevante for realizada:

- Verifique se o mapa de módulos precisa mudar.
- Verifique se o estado de desenvolvimento precisa mudar.
- Verifique se alguma decisão arquitetural foi afetada.
- Atualize dependências e interfaces documentadas.
- Registre limitações novas.
- Atualize o índice se novos documentos forem criados.

Não atualize documentos sem evidência.

Não reescreva todo o contexto a cada alteração pequena.

O agente deve informar quais documentos foram atualizados e por quê.

---

# 12. INTEGRAÇÃO COM AGENTS.md

O `AGENTS.md` deve permanecer conciso.

Ele deve explicar:

1. O que é o ULTRON 2.0.
2. Onde encontrar o contexto global.
3. Onde encontrar o índice documental.
4. Como carregar documentação especializada.
5. Como verificar o estado real do código.
6. Como registrar decisões.
7. Como validar alterações.
8. Quais são as regras de segurança.
9. Quais arquivos originais não podem ser modificados.

Não coloque toda a documentação arquitetural dentro de AGENTS.md.

O objetivo é que ele funcione como uma porta de entrada para o contexto, não como uma enciclopédia.

---

# 13. VALIDAÇÃO DO SISTEMA DE CONTEXTO

Ao concluir, verifique:

- Se os caminhos documentais existem.
- Se os links internos funcionam.
- Se não há documentos duplicados desnecessariamente.
- Se o índice representa os arquivos reais.
- Se os estados de implementação possuem evidências.
- Se as decisões históricas foram preservadas.
- Se hipóteses estão identificadas.
- Se os agentes conseguem localizar informações relevantes.
- Se o AGENTS.md aponta para os documentos corretos.

Crie testes automatizados para validar caminhos e referências documentais quando isso for viável.

---

# 14. RELATÓRIO FINAL

Apresente:

1. Estrutura de contexto criada.
2. Documentos analisados.
3. Documentos consolidados.
4. Contradições encontradas.
5. Lacunas de conhecimento.
6. Fontes de verdade identificadas.
7. Regras de carregamento.
8. Integração com AGENTS.md.
9. Validações realizadas.
10. Recomendações futuras.

Não declare o Context Engineering concluído se apenas criou arquivos vazios.

O conteúdo deve refletir o projeto real.

---

# OBJETIVO FINAL

Quero que qualquer agente que entre no ULTRON 2.0 consiga compreender o projeto sem depender exclusivamente do histórico da conversa ou de explicações improvisadas.

O agente deve saber:

- O que está construindo.
- Por que está construindo.
- Onde implementar.
- Quais decisões respeitar.
- Quais documentos consultar.
- O que não deve modificar.
- Como verificar se seu trabalho está correto.

**O contexto deve sobreviver à troca de agentes, sessões, provedores e ferramentas.**

Implemente esse sistema de forma progressiva, verificável e integrada à arquitetura existente.

Comece pela auditoria do conhecimento disponível. Não crie uma nova arquitetura documental antes de entender a documentação que já existe.