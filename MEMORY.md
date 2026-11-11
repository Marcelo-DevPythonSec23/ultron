# MEGA PROMPT — MEMORY ENGINEERING DO ULTRON 2.0
## Sistema de memória persistente, contextual, episódica e semântica

Você é responsável por projetar, implementar e integrar o sistema de memória do ULTRON 2.0.

O objetivo é construir uma infraestrutura de memória capaz de armazenar, organizar, recuperar, atualizar e utilizar informações relevantes durante diferentes sessões e tarefas.

O ULTRON não deve depender exclusivamente do histórico da conversa atual para manter continuidade.

Ele deve conseguir preservar conhecimento útil, recuperar experiências anteriores, reconhecer informações relacionadas e utilizar o contexto recuperado durante o processamento de novas solicitações.

**IMPORTANTE: memória não é sinônimo de histórico de conversas.**

O sistema precisa distinguir mensagens, eventos, fatos, preferências, conhecimentos, experiências e informações operacionais.

Não implemente uma arquitetura artificial sem antes investigar o sistema de memória que já existe.

---

# 1. FASE ZERO — AUDITORIA DA MEMÓRIA EXISTENTE

Antes de escrever código, investigue os sistemas de memória existentes em:

- `lain/`
- `Mark-LVI-main/`
- `ultron-2.0/`

Investigue:

- Classes de memória.
- Armazenamento persistente.
- Histórico de conversas.
- Recuperação de informações.
- Embeddings.
- Bancos de dados.
- Sistemas de busca.
- Context windows.
- Gerenciamento de sessões.
- Funções de escrita e leitura.
- Exclusão de informações.
- Integrações com provedores.
- Testes.
- Documentação.

Verifique especialmente as ferramentas existentes:

- `remember`
- `recall`
- `forget`

Não presuma que essas ferramentas implementam um sistema completo de memória.

Determine o que cada uma realmente faz.

Identifique:

1. O que já funciona.
2. O que está parcialmente implementado.
3. O que está duplicado.
4. O que precisa ser preservado.
5. O que precisa ser integrado.
6. O que apresenta limitações.
7. O que ainda não existe.

Crie:

`docs/memory/MEMORY_AUDIT.md`

Não modifique os repositórios originais.

---

# 2. ARQUITETURA GERAL

O sistema de memória deve funcionar como um subsistema do ULTRON Core.

O núcleo continua responsável pela orquestração.

A memória fornece informações relevantes ao núcleo, mas não toma decisões de forma independente.

Fluxo conceitual:

```text
                 ULTRON CORE
                      |
                      v
              Context Manager
                      |
                      v
               Memory Engine
                      |
          +-----------+-----------+
          |           |           |
          v           v           v
       Memory      Memory      Memory
       Storage     Retrieval   Manager
          |           |           |
          +-----------+-----------+
                      |
                      v
             Context Assembly
                      |
                      v
               ULTRON Core
```

O sistema deve possuir interfaces explícitas para leitura, escrita, atualização, recuperação e exclusão de memória.

Não crie um segundo núcleo cognitivo.

---

# 3. TIPOS DE MEMÓRIA

Implemente uma arquitetura modular que diferencie os seguintes tipos de memória.

## 3.1 Working Memory — Memória de trabalho

Responsável por manter informações necessárias à execução da tarefa atual.

Exemplos:

- Objetivo da tarefa.
- Informações fornecidas na conversa atual.
- Etapas já executadas.
- Resultados intermediários.
- Decisões temporárias.
- Estado de execução de agentes.

Características:

- Alta frequência de leitura e escrita.
- Escopo limitado à tarefa ou sessão.
- Atualização constante.
- Expiração configurável.
- Não deve ser confundida automaticamente com memória persistente.

## 3.2 Episodic Memory — Memória episódica

Armazena eventos e experiências relevantes.

Exemplos:

- Uma tarefa executada anteriormente.
- Uma decisão tomada durante um projeto.
- Uma falha encontrada.
- Uma solução que funcionou.
- Uma interação importante.
- O resultado de determinado workflow.

Cada episódio deve possuir:

- Identificador.
- Data e horário.
- Origem.
- Descrição.
- Contexto.
- Atores envolvidos, quando aplicável.
- Ações realizadas.
- Resultado.
- Referências relacionadas.
- Grau de confiabilidade.
- Política de retenção.

Não transforme automaticamente todas as mensagens em episódios persistentes.

## 3.3 Semantic Memory — Memória semântica

Armazena conhecimentos e informações estruturadas.

Exemplos:

- Fatos conhecidos.
- Conceitos.
- Relações entre entidades.
- Informações técnicas.
- Preferências confirmadas.
- Conhecimento consolidado a partir de experiências.

O sistema deve permitir relacionar informações sem depender exclusivamente da busca textual.

Investigue a viabilidade de armazenar relações entre entidades e fatos.

Não implemente um knowledge graph completo sem demonstrar necessidade técnica.

## 3.4 Procedural Memory — Memória procedural

Armazena procedimentos e conhecimentos sobre como realizar determinadas tarefas.

Exemplos:

- Como executar determinado workflow.
- Como configurar um componente.
- Como iniciar um serviço.
- Como utilizar uma ferramenta.
- Procedimentos técnicos validados.

Procedimentos devem possuir:

- Objetivo.
- Pré-condições.
- Etapas.
- Dependências.
- Resultado esperado.
- Estado de validação.
- Versão.
- Histórico de alterações.

Uma instrução encontrada em uma página externa não deve ser promovida automaticamente a procedimento confiável.

## 3.5 User Memory — Memória sobre usuários

Quando o ULTRON operar com diferentes usuários, deve existir uma separação explícita entre informações de cada identidade.

Exemplos:

- Preferências.
- Configurações.
- Contexto de utilização.
- Informações fornecidas voluntariamente.
- Preferências de interação.

Essas informações não devem ser compartilhadas entre usuários.

O sistema deve respeitar consentimento, privacidade, controle de acesso e políticas de retenção.

Não armazene senhas, tokens, chaves privadas ou credenciais como memória pessoal.

Informações pessoais sensíveis devem receber proteção reforçada e não devem ser armazenadas automaticamente.

---

# 4. MEMORY ENGINE — NÚCLEO DE GERENCIAMENTO

Implemente um componente central responsável por coordenar as operações de memória.

Interface conceitual:

```python
class MemoryEngine:

    async def store(self, memory):
        ...

    async def retrieve(self, query, context=None):
        ...

    async def update(self, memory_id, changes):
        ...

    async def delete(self, memory_id):
        ...

    async def search(self, query, filters=None):
        ...

    async def consolidate(self, scope=None):
        ...

    async def get_context(self, query, budget=None):
        ...
```

Essa interface é uma referência conceitual.

Adapte-a às convenções reais do projeto.

Não implemente métodos vazios ou operações fictícias.

Cada operação deve possuir validação, tratamento de erros e comportamento documentado.

O Memory Engine deve controlar:

- Persistência.
- Recuperação.
- Atualização.
- Consolidação.
- Deduplicação.
- Expiração.
- Versionamento.
- Permissões.
- Integridade.
- Auditoria.

---

# 5. MEMORY STORAGE — ARMAZENAMENTO

Investigue as tecnologias já utilizadas.

Preserve o armazenamento existente quando for tecnicamente adequado.

Avalie separadamente:

- Banco relacional para informações estruturadas.
- Armazenamento documental para registros flexíveis.
- Índice vetorial para busca semântica.
- Armazenamento de arquivos para conteúdo externo.
- Cache para memória de trabalho.

Não adicione cinco bancos de dados só porque a arquitetura permite.

Escolha a menor quantidade de componentes capaz de atender aos requisitos.

Cada registro deve possuir identificação, origem, escopo e metadados.

Considere:

- SQLite ou PostgreSQL para persistência estruturada.
- Busca textual para correspondências exatas.
- Embeddings para similaridade semântica, quando disponíveis.
- Índices relacionais para filtros e recuperação.

A arquitetura deve funcionar mesmo quando um provedor externo de embeddings estiver indisponível.

Não faça da memória vetorial uma dependência obrigatória para todas as operações.

---

# 6. MEMORY RETRIEVAL — RECUPERAÇÃO INTELIGENTE

Uma memória só é útil se puder ser recuperada corretamente.

Implemente recuperação contextual.

O sistema deve considerar:

1. Correspondência textual.
2. Similaridade semântica.
3. Relevância para a tarefa.
4. Recência.
5. Confiabilidade.
6. Escopo.
7. Relações com outras memórias.
8. Estado de validade.

O mecanismo deve evitar recuperar informações apenas porque possuem palavras semelhantes.

Exemplo:

Se o usuário mencionar um projeto anteriormente discutido, o sistema deve tentar localizar informações relacionadas àquele projeto, em vez de recuperar qualquer registro que contenha a mesma palavra.

Implemente uma estratégia híbrida quando viável:

```text
Consulta
   |
   v
Normalização
   |
   v
Busca textual
   |
   v
Busca semântica
   |
   v
Filtros de escopo e permissão
   |
   v
Ranking de relevância
   |
   v
Deduplicação
   |
   v
Contexto recuperado
```

A recuperação deve possuir limite de resultados e orçamento de contexto.

Não envie todo o banco de memória ao modelo.

---

# 7. MEMORY CONSOLIDATION — CONSOLIDAÇÃO

Implemente um mecanismo de consolidação.

Seu objetivo é identificar informações relacionadas e organizar o conhecimento armazenado.

Exemplos:

- Vários episódios relacionados ao mesmo projeto.
- Informações repetidas.
- Preferências recorrentes.
- Procedimentos que foram validados várias vezes.
- Conhecimentos derivados de experiências anteriores.

A consolidação pode:

- Agrupar registros relacionados.
- Identificar duplicatas.
- Criar resumos.
- Sugerir novas relações.
- Identificar informações potencialmente desatualizadas.

Entretanto:

**Consolidação não significa reescrever ou apagar automaticamente a memória original.**

Preserve referências aos registros de origem.

Quando houver informações conflitantes, não escolha arbitrariamente uma delas.

Registre a divergência e considere:

- Data.
- Origem.
- Confiabilidade.
- Contexto.
- Confirmação do usuário.

Informações inferidas devem continuar identificadas como inferências.

---

# 8. MEMORY DECAY E RETENÇÃO

Nem todas as informações possuem o mesmo valor permanente.

Implemente políticas de retenção configuráveis.

Considere:

- Memórias temporárias.
- Memórias de sessão.
- Memórias episódicas.
- Memórias persistentes.
- Procedimentos validados.
- Informações desatualizadas.

O sistema pode utilizar recência e frequência como fatores de relevância.

Entretanto, não implemente esquecimento baseado exclusivamente em tempo.

Uma decisão arquitetural importante pode continuar relevante anos depois.

A expiração deve respeitar o tipo de memória e sua política de retenção.

Não apague silenciosamente informações importantes.

---

# 9. MEMORY VERSIONING E CONFLITOS

Implemente controle de versões para informações atualizáveis.

Exemplo:

Uma configuração anteriormente registrada pode ser substituída por uma nova.

O sistema deve preservar:

- Valor anterior.
- Valor atual.
- Data da alteração.
- Origem da alteração.
- Motivo, quando disponível.

Não sobrescreva fatos conflitantes sem registrar a mudança.

Diferencie:

- Informação corrigida.
- Informação atualizada.
- Informação contraditória.
- Informação temporária.
- Informação não confirmada.

---

# 10. INTEGRAÇÃO COM O ULTRON CORE

A memória deve ser integrada ao fluxo central do ULTRON.

Fluxo de referência:

```text
Entrada do usuário
       |
       v
ULTRON Core
       |
       v
Context Manager
       |
       v
Memory Retrieval
       |
       v
Context Assembly
       |
       v
LLM Provider
       |
       v
Orchestrator
       |
       v
Resposta ou execução de ferramenta
       |
       v
Memory Evaluation
       |
       v
Persistência, se aplicável
```

O sistema deve conseguir:

- Consultar memória antes de responder.
- Utilizar informações relevantes.
- Registrar resultados importantes.
- Atualizar informações quando necessário.
- Evitar registros redundantes.
- Preservar o isolamento das sessões.

A memória não deve ser chamada indiscriminadamente para todas as operações.

Implemente políticas de recuperação conforme o tipo de tarefa.

---

# 11. INTEGRAÇÃO COM AGENTES

O ULTRON poderá utilizar múltiplos agentes especializados.

A memória deve suportar diferentes escopos:

- Memória global do sistema.
- Memória do usuário.
- Memória de projeto.
- Memória de sessão.
- Memória de tarefa.
- Memória de agente.

Cada agente deve acessar somente os escopos autorizados.

Exemplo:

Um agente responsável por voz pode consultar configurações e procedimentos do pipeline de áudio.

Um agente responsável por segurança pode consultar auditorias e decisões de segurança.

Um agente não deve ter permissão para modificar indiscriminadamente a memória global.

Estabeleça políticas de leitura, escrita e exclusão.

Agentes devem identificar a origem das informações que utilizam.

Resultados de agentes externos não devem ser considerados automaticamente verdadeiros.

---

# 12. MEMORY SECURITY

Segurança deve ser aplicada na implementação.

Considere:

- Isolamento por usuário.
- Controle de acesso por escopo.
- Proteção de dados pessoais.
- Sanitização de entradas.
- Proteção contra prompt injection.
- Integridade dos registros.
- Auditoria.
- Controle de exclusão.
- Proteção de credenciais.
- Backup e recuperação.

Memórias podem conter texto proveniente de páginas web, arquivos, ferramentas ou agentes externos.

Esses conteúdos devem ser tratados como dados não confiáveis.

Uma memória recuperada não deve adquirir autoridade de instrução do sistema simplesmente por estar armazenada no banco.

Nunca permita que uma memória altere silenciosamente políticas de segurança, permissões ou instruções centrais.

Não armazene segredos operacionais em texto simples.

Implemente políticas explícitas para dados sensíveis.

---

# 13. MEMORY TOOLS

Investigue as ferramentas existentes:

- `remember`
- `recall`
- `forget`

Preserve suas funcionalidades quando forem adequadas.

Amplie os contratos quando necessário.

## remember

Responsável por solicitar o armazenamento de uma informação.

Deve identificar:

- Conteúdo.
- Tipo de memória.
- Escopo.
- Origem.
- Metadados.
- Política de retenção.

Não permita gravação arbitrária sem validação.

## recall

Responsável por recuperar informações.

Deve permitir:

- Busca textual.
- Busca semântica, quando disponível.
- Filtros por escopo.
- Recuperação por identificador.
- Limitação de resultados.

## forget

Responsável por excluir informações.

Deve possuir:

- Identificação inequívoca do registro.
- Verificação de autorização.
- Confirmação para exclusões relevantes.
- Auditoria da operação.
- Tratamento de referências e índices derivados.

A exclusão deve respeitar a política de retenção e os requisitos de privacidade.

Não declare uma informação excluída se cópias ou índices derivados ainda permanecerem acessíveis.

---

# 14. CONTEXT BUDGET

O sistema deve controlar a quantidade de memória enviada ao modelo.

Não recupere centenas de registros sem necessidade.

Implemente:

- Limite de resultados.
- Ranking.
- Priorização.
- Resumos.
- Deduplicação.
- Orçamento configurável de tokens.
- Seleção contextual.

O objetivo é maximizar a relevância das informações recuperadas, não a quantidade.

Quando possível, preserve referências aos registros originais para permitir rastreabilidade.

---

# 15. OBSERVABILIDADE

Implemente registros técnicos que permitam entender o comportamento da memória.

Registre:

- Operação realizada.
- Tipo de memória.
- Escopo.
- Tempo de recuperação.
- Quantidade de registros encontrados.
- Quantidade de registros utilizados.
- Falhas.
- Operações de atualização.
- Operações de exclusão.

Não registre conteúdo sensível integralmente nos logs.

Crie métricas que permitam avaliar:

- Latência de recuperação.
- Taxa de recuperação sem resultados.
- Duplicação.
- Falhas de persistência.
- Memórias não utilizadas.
- Qualidade da recuperação.

Não invente métricas de precisão sem implementar uma metodologia de avaliação.

---

# 16. TESTES

Crie testes para:

1. Persistência.
2. Recuperação textual.
3. Recuperação semântica.
4. Isolamento de usuários.
5. Isolamento de sessões.
6. Memória episódica.
7. Memória semântica.
8. Memória procedural.
9. Atualização.
10. Exclusão.
11. Deduplicação.
12. Consolidação.
13. Conflitos.
14. Expiração.
15. Falhas de armazenamento.
16. Falhas de embeddings.
17. Controle de permissões.
18. Integração com o ULTRON Core.
19. Integração com agentes.
20. Limites de contexto.

Utilize mocks para testes unitários quando necessário.

Entretanto, diferencie testes simulados de testes que validam integrações reais.

Não remova testes existentes para fazer a suíte passar.

Preserve a linha de base de regressão e documente alterações no número de testes.

---

# 17. DOCUMENTAÇÃO

Crie ou atualize, conforme a estrutura existente:

```text
docs/memory/
├── MEMORY_AUDIT.md
├── MEMORY_ARCHITECTURE.md
├── MEMORY_TYPES.md
├── MEMORY_STORAGE.md
├── MEMORY_RETRIEVAL.md
├── MEMORY_SECURITY.md
├── MEMORY_LIFECYCLE.md
├── MEMORY_API.md
└── MEMORY_TESTING.md
```

Documente a implementação real.

Não documente funcionalidades apenas planejadas como se estivessem prontas.

Atualize também:

- PROJECT_CONTEXT.md.
- CONTEXT_INDEX.md.
- MODULE_MAP.md.
- DEVELOPMENT_STATE.md.
- ARCHITECTURE.md.

---

# 18. IMPLEMENTAÇÃO PROGRESSIVA

Trabalhe nas seguintes etapas:

1. Auditoria da memória existente.
2. Definição dos requisitos reais.
3. Desenho da arquitetura.
4. Definição dos contratos.
5. Organização do armazenamento.
6. Implementação do Memory Engine.
7. Implementação da recuperação.
8. Integração com o ULTRON Core.
9. Integração com os agentes.
10. Segurança e permissões.
11. Consolidação e ciclo de vida.
12. Testes.
13. Documentação.
14. Validação final.

Não tente implementar todos os recursos simultaneamente.

Priorize uma memória persistente funcional, confiável e integrada antes de adicionar mecanismos avançados.

---

# 19. CRITÉRIOS DE CONCLUSÃO

O sistema só deve ser considerado funcional quando:

- As informações persistirem entre sessões.
- O ULTRON conseguir recuperar informações relevantes.
- O sistema diferenciar os tipos de memória.
- Existir isolamento de escopos.
- A memória puder ser atualizada.
- A exclusão funcionar corretamente.
- A recuperação respeitar permissões.
- O sistema não depender obrigatoriamente de um único provedor.
- Os agentes utilizarem a memória por interfaces controladas.
- A memória não substituir o orquestrador.
- O contexto enviado aos modelos respeitar limites configuráveis.
- Os testes validarem os comportamentos implementados.

---

# 20. RELATÓRIO FINAL

Ao concluir, apresente:

1. Arquitetura implementada.
2. Componentes reutilizados.
3. Componentes novos.
4. Tecnologias de armazenamento.
5. Tipos de memória disponíveis.
6. Estratégia de recuperação.
7. Estratégia de consolidação.
8. Políticas de retenção.
9. Segurança e permissões.
10. Integração com o núcleo.
11. Integração com agentes.
12. Testes executados.
13. Limitações conhecidas.
14. Próximas melhorias.

Classifique cada recurso como:

- IMPLEMENTED
- PARTIAL
- PLANNED
- BLOCKED
- UNKNOWN

Não declare funcionalidades concluídas sem evidências.

---

# OBJETIVO FINAL

Quero que o ULTRON consiga preservar continuidade entre sessões, tarefas e agentes.

Ele deve ser capaz de recuperar experiências, reconhecer informações relevantes, manter conhecimentos estruturados e utilizar procedimentos anteriormente validados.

A memória deve ser persistente, organizada, rastreável, segura e independente de um único modelo de IA.

**O ULTRON não deve simplesmente lembrar tudo. Deve saber o que vale a pena lembrar, por que aquilo foi armazenado, quando deve recuperar a informação e quando ela deixou de ser válida.**

Comece pela auditoria do sistema existente. Não substitua funcionalidades funcionais sem justificativa técnica. Implemente progressivamente e valide cada etapa.