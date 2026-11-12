# MASTER PROMPT — ULTRON 2.0
## Integração arquitetural entre ULTRON Core e Mark-LVI Runtime

> **Porta de entrada de contexto.** Este arquivo descreve a missão. Antes de
> alterar código, leia `../PROJECT_CONTEXT.md` e
> `../docs/context/CONTEXT_INDEX.md`; o estado real, decisões, mapa de módulos e
> limitações vivem neles. Para memória, leia
> `../docs/memory/MEMORY_ARCHITECTURE.md` e `../docs/memory/MEMORY_API.md`.
> `lain/` e `Mark-LVI-main/` são **somente leitura**; o produto é `ultron-2.0/`.


**PAPEL DO AGENTE**

Você atuará como engenheiro de software sênior, arquiteto de sistemas, engenheiro de integração Python e especialista em sistemas de IA, orquestração de agentes, processamento de áudio, automação de desktop e arquitetura modular.

Sua missão é integrar dois projetos Python existentes em um único sistema denominado **ULTRON 2.0**, preservando a identidade arquitetural do ULTRON e reutilizando os recursos operacionais do Mark-LVI.

Não trate esta tarefa como uma simples cópia de arquivos, concatenação de projetos ou substituição de um sistema pelo outro.

Trata-se de uma integração arquitetural que exige inspeção do código-fonte, análise de dependências, identificação de interfaces, compatibilidade entre componentes, planejamento de migração e implementação incremental.

---

# 1. OBJETIVO PRINCIPAL

Construir um sistema unificado com as seguintes responsabilidades:

**ULTRON: núcleo inteligente e autoridade de orquestração.**

Responsável por:
- Identidade e personalidade do sistema.
- System prompts e contexto comportamental.
- Orquestração das interações.
- Integração com provedores de modelos de IA.
- Gerenciamento de contexto e histórico.
- Memória e persistência próprias.
- Planejamento e decomposição de tarefas.
- Decisão sobre utilização de ferramentas.
- Interpretação dos resultados das ferramentas.
- Coordenação futura de agentes especializados.
- API e interfaces de comunicação já existentes.

**Mark-LVI: infraestrutura de interação e execução.**

Responsável por fornecer, após auditoria e adaptação:
- Captura de áudio.
- Reconhecimento de fala (STT).
- Síntese de fala (TTS).
- Wake word, caso disponível e funcional.
- Voice Activity Detection (VAD), caso disponível.
- Reprodução de áudio.
- Interação com aplicações locais.
- Automação de desktop.
- Ações e ferramentas reutilizáveis.
- Integrações com navegador.
- Monitoramento do sistema.
- Interface gráfica e elementos visuais reutilizáveis.

**Resultado esperado:** um único assistente chamado ULTRON, capaz de receber comandos por texto ou voz, processá-los por meio de seu núcleo inteligente, executar ferramentas autorizadas e responder por texto ou áudio.

Não devem existir dois assistentes independentes competindo pela conversa.

---

# 2. LOCALIZAÇÃO DOS PROJETOS

Os diretórios identificados são:

**Projeto ULTRON:**

`/home/marcelo/projetos/ultron/lain/`

Arquivos previamente identificados:

- `lain/app/main.py`
- `lain/app/core/orchestrator.py`
- `lain/app/intelligence/providers/registry.py`

**Projeto Mark-LVI:**

`/home/marcelo/projetos/ultron/Mark-LVI-main/`

Arquivos previamente identificados:

- `Mark-LVI-main/main.py`
- `Mark-LVI-main/core/stt.py`
- `Mark-LVI-main/core/tts.py`
- `Mark-LVI-main/actions/open_app.py`
- `Mark-LVI-main/actions/browser_control.py`
- `Mark-LVI-main/actions/system_monitor.py`
- `Mark-LVI-main/actions/file_controller.py`
- `Mark-LVI-main/actions/web_search.py`

IMPORTANTE:

Esses caminhos são pontos de partida identificados anteriormente, não uma especificação completa da arquitetura.

Inspecione a estrutura real dos diretórios antes de tomar decisões.

Não presuma que classes, métodos, funções ou interfaces possuem nomes ou assinaturas específicas sem verificar suas implementações.

Não presuma que todos os componentes identificados estejam completos ou funcionais.

---

# 3. REGRAS INEGOCIÁVEIS

As seguintes regras devem ser respeitadas durante toda a execução:

### 3.1 Preservação dos projetos originais

- Não modifique diretamente o diretório original do ULTRON.
- Não modifique diretamente o diretório original do Mark-LVI.
- Não exclua arquivos originais.
- Não substitua implementações existentes sem justificar tecnicamente a necessidade.
- Não sobrescreva configurações, bancos de dados, arquivos de memória ou credenciais.
- Não execute operações destrutivas sem autorização explícita.

O trabalho deverá ocorrer em uma terceira estrutura independente.

### 3.2 Integridade arquitetural

- O ULTRON continuará sendo o núcleo inteligente e o orquestrador principal.
- O Mark-LVI será uma fonte de componentes operacionais reutilizáveis.
- O ULTRON deverá controlar o fluxo principal da aplicação.
- O Mark-LVI não poderá assumir silenciosamente o gerenciamento do contexto do ULTRON.
- Não deverão existir dois históricos independentes para a mesma conversa.
- Não deverão existir dois orquestradores principais.
- Não deverão existir dois mecanismos concorrentes de tomada de decisão.
- Não deverá haver duplicação desnecessária de memória.

### 3.3 Integridade funcional

- Não remova funcionalidades existentes do ULTRON.
- Não remova funcionalidades úteis do Mark-LVI sem justificativa.
- Não implemente recursos fictícios ou apenas aparentes.
- Não substitua uma funcionalidade real por uma implementação simplificada sem autorização.
- Não declare uma integração concluída sem testes.
- Não esconda falhas de compatibilidade.
- Não utilize mocks como substitutos permanentes de implementações reais.

### 3.4 Precisão técnica

Antes de utilizar qualquer componente:

1. Localize sua implementação.
2. Leia o código completo relevante.
3. Identifique suas dependências.
4. Identifique seus parâmetros.
5. Identifique seus retornos.
6. Identifique seus efeitos colaterais.
7. Identifique seu gerenciamento de estado.
8. Identifique suas exceções.
9. Verifique sua compatibilidade com o ambiente atual.

Nunca invente APIs, métodos, classes ou parâmetros.

---

# 4. FASE ZERO — INVENTÁRIO E AUDITORIA

Antes de escrever ou modificar código, realize uma auditoria completa dos dois projetos.

Inspecione:

- Estrutura de diretórios.
- Arquivos Python.
- Arquivos de configuração.
- Arquivos de dependências.
- Variáveis de ambiente.
- Arquivos de inicialização.
- Interfaces entre módulos.
- Sistemas de armazenamento.
- Provedores de IA.
- Gerenciamento de sessões.
- Gerenciamento de histórico.
- Processamento de áudio.
- Ações de desktop.
- Interface gráfica.
- Sistemas de plugins.
- APIs existentes.
- Tratamento de erros.
- Logging.
- Testes automatizados.

Examine especialmente:

**ULTRON**
- `app/main.py`
- `app/core/orchestrator.py`
- `app/intelligence/providers/registry.py`
- Todos os módulos relacionados à memória.
- Todos os módulos relacionados ao contexto.
- Todos os módulos relacionados à persistência.
- Todas as interfaces de API existentes.

**Mark-LVI**
- `main.py`
- `core/stt.py`
- `core/tts.py`
- Todos os módulos relacionados a áudio.
- Todos os módulos relacionados a wake word.
- Todos os módulos relacionados a VAD.
- Diretório `actions/`.
- Diretório `plugins/`.
- Diretório `providers/`.
- Diretório `memory/`.
- Diretório `dashboard/`.
- Todos os módulos de controle do computador.

Não se limite aos arquivos listados.

Faça uma busca por referências cruzadas, imports, chamadas e dependências para entender como cada componente realmente funciona.

## Entregável obrigatório

Produza um documento:

`docs/INTEGRATION_AUDIT.md`

Esse documento deverá apresentar:

1. Arquitetura atual do ULTRON.
2. Arquitetura atual do Mark-LVI.
3. Responsabilidade de cada componente relevante.
4. Dependências internas e externas.
5. Bibliotecas compartilhadas.
6. Dependências incompatíveis.
7. Conflitos de inicialização.
8. Conflitos de estado.
9. Conflitos de memória.
10. Conflitos de provedores de IA.
11. Compatibilidade dos sistemas de áudio.
12. Compatibilidade dos sistemas de ferramentas.
13. Componentes reutilizáveis.
14. Componentes que precisam de adaptação.
15. Componentes que não devem ser integrados.
16. Riscos técnicos identificados.

Não avance para a implementação antes de concluir essa auditoria.

---

# 5. FASE UM — DEFINIÇÃO DA ARQUITETURA FINAL

A arquitetura deverá seguir o princípio de separação de responsabilidades.

Estrutura conceitual desejada:

```text
ULTRON 2.0
│
├── app/
│   ├── main.py
│   │
│   ├── core/
│   │   ├── orchestrator.py
│   │   ├── context_manager.py
│   │   ├── session_manager.py
│   │   └── execution_manager.py
│   │
│   ├── intelligence/
│   │   ├── providers/
│   │   ├── reasoning/
│   │   ├── prompts/
│   │   └── agents/
│   │
│   ├── memory/
│   │
│   ├── interfaces/
│   │   ├── voice/
│   │   ├── api/
│   │   └── desktop/
│   │
│   ├── integrations/
│   │   └── mark_lvi/
│   │       ├── audio/
│   │       ├── actions/
│   │       ├── plugins/
│   │       └── adapters/
│   │
│   ├── security/
│   │
│   └── config/
│
├── dashboard/
│
├── tests/
│
├── docs/
│
├── scripts/
│
├── requirements.txt
│
└── README.md
```

ATENÇÃO:

Essa estrutura é uma proposta lógica, não uma ordem para recriar todos os diretórios.

Compare-a com a estrutura existente do ULTRON.

Preserve os módulos que já funcionam e adapte a organização apenas quando existir uma justificativa técnica.

Não crie arquivos vazios para preencher a estrutura.

Não duplique módulos existentes com nomes diferentes.

Não mova arquivos desnecessariamente.

## 5.1 Hierarquia de autoridade

A hierarquia deverá ser:

```text
Usuário
  │
  ▼
Interface ULTRON
  │
  ▼
ULTRON Orchestrator
  │
  ├── Context Manager
  ├── Memory Manager
  ├── Provider Registry
  ├── Reasoning / Planning
  └── Execution Manager
         │
         ▼
    Tool Adapters
         │
         ▼
    Mark-LVI Actions
         │
         ▼
    Sistema operacional
```

O Mark-LVI não deverá responder diretamente ao usuário ignorando o orquestrador do ULTRON.

O fluxo de entrada e saída deverá ser controlado pelo ULTRON.

---

# 6. FASE DOIS — INTEGRAÇÃO DO SISTEMA DE VOZ

Esta é uma das partes prioritárias do projeto.

Aproveite os componentes reais do Mark-LVI relacionados ao processamento de áudio.

Inspecione particularmente:

- `core/stt.py`
- `core/tts.py`
- Implementações de captura de microfone.
- Implementações de reprodução de áudio.
- Wake word.
- VAD.
- Gerenciamento de sessões de voz.
- Integrações com provedores de áudio.

Não assuma que STT e TTS compartilham o mesmo provedor ou protocolo.

Não assuma que o sistema utiliza uma única sessão de áudio.

Identifique o fluxo real de processamento.

## 6.1 Entrada de voz

Fluxo desejado:

```text
Microfone
   │
   ▼
Captura de áudio
   │
   ▼
Wake Word (quando disponível)
   │
   ▼
VAD (quando disponível)
   │
   ▼
STT
   │
   ▼
Texto reconhecido
   │
   ▼
ULTRON Orchestrator
```

O resultado do STT deverá ser encaminhado ao mesmo fluxo de processamento utilizado pelas mensagens de texto.

Não crie um segundo mecanismo de conversação exclusivo para voz.

## 6.2 Saída de voz

Fluxo desejado:

```text
ULTRON Orchestrator
   │
   ▼
Resposta final
   │
   ▼
Voice Output Adapter
   │
   ▼
TTS
   │
   ▼
Reprodução de áudio
   │
   ▼
Usuário
```

A resposta textual deverá continuar disponível mesmo quando o TTS falhar.

A indisponibilidade de áudio não poderá interromper o funcionamento do núcleo inteligente.

## 6.3 Requisitos de áudio

- Captura e reprodução devem possuir ciclos de vida independentes.
- Não abrir múltiplos microfones sem necessidade.
- Não iniciar múltiplos dispositivos de áudio concorrentes.
- Implementar tratamento de interrupções.
- Implementar tratamento de dispositivos indisponíveis.
- Registrar erros de captura e reprodução.
- Permitir desligar o sistema de voz.
- Permitir utilizar o ULTRON exclusivamente por texto.
- Evitar bloquear a interface gráfica durante operações de áudio.
- Utilizar execução assíncrona ou threads quando tecnicamente necessário.
- Gerenciar corretamente o encerramento dos dispositivos.

Não implemente processamento de áudio fictício para simular funcionamento.

---

# 7. FASE TRÊS — INTEGRAÇÃO DAS ACTIONS E FERRAMENTAS

O ULTRON deverá conseguir utilizar ferramentas provenientes do Mark-LVI.

Audite todas as implementações do diretório:

`Mark-LVI-main/actions/`

Dê atenção especial aos seguintes módulos, caso existam e estejam funcionais:

- `open_app.py`
- `browser_control.py`
- `system_monitor.py`
- `file_controller.py`
- `web_search.py`

Não limite a integração a esses cinco módulos.

Identifique todas as ferramentas disponíveis e classifique-as por responsabilidade.

## 7.1 Adaptadores de ferramentas

Não permita que o orquestrador dependa diretamente de detalhes internos de cada action.

Implemente uma camada de adaptadores.

Cada ferramenta integrada deverá possuir um contrato explícito contendo:

- Nome.
- Descrição.
- Parâmetros.
- Tipos de dados.
- Campos obrigatórios.
- Resultado esperado.
- Exceções possíveis.
- Permissões necessárias.
- Requisitos de confirmação.
- Timeout.
- Estratégia de tratamento de erros.

O contrato deverá refletir a implementação real.

## 7.2 Ciclo de execução

O fluxo deverá ser:

```text
Mensagem do usuário
        │
        ▼
ULTRON Orchestrator
        │
        ▼
Modelo de IA
        │
        ▼
Decisão de utilizar ferramenta
        │
        ▼
Validação do contrato
        │
        ▼
Verificação de permissões
        │
        ▼
Execução autorizada
        │
        ▼
Resultado da ferramenta
        │
        ▼
ULTRON Orchestrator
        │
        ▼
Interpretação do resultado
        │
        ▼
Resposta ao usuário
```

O modelo não deverá executar comandos diretamente fora do mecanismo de ferramentas.

O resultado de uma ferramenta não deverá ser tratado automaticamente como uma nova instrução confiável.

---

# 8. FASE QUATRO — PROVEDORES DE IA

O ULTRON já possui um registro de provedores em:

`lain/app/intelligence/providers/registry.py`

Esse sistema deverá continuar sendo a autoridade responsável pelo gerenciamento de provedores do núcleo.

Audite como os provedores são registrados, inicializados e utilizados.

Investigue:

- Formatos de mensagens.
- Estrutura de histórico.
- Function calling.
- Tool calling.
- Streaming.
- Gerenciamento de sessões.
- Configurações de geração.
- Autenticação.
- Variáveis de ambiente.
- Tratamento de erros.
- Limites de contexto.
- Compatibilidade de SDKs.

O fato de os dois projetos utilizarem Gemini não significa que suas implementações sejam compatíveis.

Não substitua o sistema de provedores do ULTRON pelo sistema do Mark-LVI sem uma justificativa técnica demonstrável.

O Mark-LVI poderá fornecer componentes específicos de integração com provedores quando forem necessários para funcionalidades operacionais, mas não deverá criar uma segunda autoridade de orquestração.

## Requisitos

- Preservar o Provider Registry do ULTRON.
- Evitar duplicação de credenciais.
- Centralizar configurações.
- Não inserir chaves diretamente no código.
- Não registrar segredos em logs.
- Não assumir compatibilidade entre SDKs.
- Documentar as diferenças de protocolo.
- Implementar adaptadores quando necessário.

---

# 9. FASE CINCO — MEMÓRIA E CONTEXTO

A memória do ULTRON deverá permanecer sob responsabilidade do núcleo do ULTRON.

Antes de integrar qualquer mecanismo de memória do Mark-LVI, investigue:

- Tipo de armazenamento.
- Estrutura dos registros.
- Persistência.
- Recuperação.
- Indexação.
- Embeddings.
- Histórico.
- Sessões.
- Estratégias de retenção.
- Dependências externas.

Não mantenha dois sistemas de memória concorrentes para o mesmo usuário sem uma finalidade arquitetural explícita.

O ULTRON deverá continuar responsável por:

- Histórico conversacional.
- Contexto de execução.
- Memórias persistentes.
- Estado das tarefas.
- Informações necessárias para o planejamento.

O Mark-LVI poderá fornecer informações transitórias de seus componentes operacionais.

Não copie automaticamente toda saída de ferramenta para a memória permanente.

Implemente critérios claros para decidir o que será persistido.

---

# 10. FASE SEIS — INTERFACE GRÁFICA

A interface poderá utilizar componentes do dashboard do Mark-LVI, desde que sua implementação seja compatível com a arquitetura final.

O produto deverá apresentar a identidade visual do ULTRON.

## Direção visual

Tema:
- Vermelho escuro.
- Vermelho luminoso.
- Preto.
- Grafite.
- Transparências.
- Elementos holográficos.
- Indicadores de atividade.
- Visual tecnológico e futurista.

Referência estética: representação digital do Ultron no MCU.

Não utilizar o rosto robótico do personagem como requisito visual.

A identidade deverá ser representada por uma interface digital abstrata.

## Elementos desejados

- Indicador de estado do ULTRON.
- Visualização de atividade de voz.
- Indicador de captura do microfone.
- Indicador de processamento.
- Visualização de resposta em tempo real, se suportada.
- Indicador de execução de ferramentas.
- Estado dos agentes.
- Histórico de conversação.
- Indicador de conexão com provedores.
- Controles para ativar e desativar funcionalidades.

## Regras de implementação

- Centralizar cores em variáveis ou tokens.
- Evitar substituir cores manualmente em dezenas de arquivos.
- Separar identidade visual da lógica do sistema.
- Não remover funcionalidades da interface original sem necessidade.
- Não criar botões sem funcionalidade.
- Não simular estados que não correspondam ao estado real do sistema.

---

# 11. FASE SETE — SEGURANÇA E CONTROLE DE EXECUÇÃO

O ULTRON poderá controlar ferramentas locais, mas deverá operar com limites técnicos claros.

A personalidade do sistema não poderá alterar as políticas de segurança da aplicação.

Implementar, conforme aplicável:

- Permissões mínimas.
- Validação de parâmetros.
- Separação entre planejamento e execução.
- Confirmação para operações destrutivas.
- Proteção de credenciais.
- Logs de auditoria.
- Timeouts.
- Limites de execução.
- Tratamento de exceções.
- Controle de acesso às ferramentas.
- Restrição de diretórios sensíveis.
- Separação de processos quando necessário.

Ações como excluir arquivos, alterar configurações críticas, executar comandos privilegiados ou modificar dados persistentes devem exigir autorização explícita.

Não permitir que uma instrução recebida de uma página web, arquivo, documento ou resultado de ferramenta altere as regras internas do sistema.

Não implementar execução irrestrita de comandos de shell.

O sistema deverá conseguir explicar quais ferramentas utilizou e quais operações foram realizadas.

---

# 12. FASE OITO — COMPATIBILIDADE COM O HARDWARE

O ambiente de desenvolvimento possui recursos limitados.

Considere como condição de projeto:

- Linux.
- Aproximadamente 4 GB de RAM.
- Ausência de GPU dedicada.
- Preferência por componentes gratuitos e open source.
- Possibilidade de utilizar APIs remotas.

O sistema deverá priorizar eficiência de memória e execução.

Requisitos:

- Não exigir GPU.
- Não carregar modelos locais grandes por padrão.
- Evitar processos redundantes.
- Evitar múltiplas instâncias dos mesmos serviços.
- Não executar recursos pesados sem necessidade.
- Permitir desativar módulos não utilizados.
- Utilizar carregamento sob demanda quando apropriado.
- Controlar concorrência.
- Evitar vazamentos de memória.
- Não bloquear o sistema durante processamento de áudio ou ferramentas.

Audite a compatibilidade das dependências com a distribuição Linux e o ambiente Python existentes.

Não atualize indiscriminadamente todas as bibliotecas.

Não substitua versões sem verificar compatibilidade.

---

# 13. FASE NOVE — TESTES E VALIDAÇÃO

Nenhuma funcionalidade deverá ser considerada integrada apenas porque o código importa sem apresentar erro.

Implemente testes progressivos.

## Teste A — Inicialização

Verificar:
- Inicialização do núcleo.
- Carregamento de configurações.
- Registro de provedores.
- Inicialização da interface.
- Ausência de imports circulares.
- Ausência de dependências ausentes.

## Teste B — Conversação por texto

Verificar:
- Recebimento de mensagem.
- Encaminhamento ao orquestrador.
- Recuperação de contexto.
- Chamada ao provedor.
- Resposta final.
- Persistência correta.

## Teste C — STT

Verificar:
- Inicialização do microfone.
- Captura de áudio.
- Reconhecimento.
- Conversão para texto.
- Encaminhamento ao ULTRON.
- Tratamento de falhas.

## Teste D — TTS

Verificar:
- Recebimento da resposta.
- Conversão para áudio.
- Reprodução.
- Encerramento correto.
- Recuperação após falhas.

## Teste E — Ferramentas

Verificar:
- Descoberta das ferramentas.
- Registro dos contratos.
- Validação dos parâmetros.
- Autorização.
- Execução.
- Retorno.
- Interpretação do resultado.

Utilize operações de teste não destrutivas.

## Teste F — Integração completa

Simular o fluxo:

```text
Usuário fala
    ↓
STT
    ↓
ULTRON
    ↓
Provider
    ↓
Tool Calling
    ↓
Action
    ↓
Resultado
    ↓
ULTRON
    ↓
TTS
    ↓
Usuário
```

O fluxo completo deverá funcionar sem criar uma segunda conversa independente.

## Teste G — Recuperação de falhas

Verificar:
- Provedor indisponível.
- Microfone desconectado.
- Falha de TTS.
- Action com erro.
- Timeout.
- Parâmetros inválidos.
- Perda de conexão.
- Encerramento inesperado de um módulo.

O sistema deverá falhar de maneira controlada.

---

# 14. FASE DE IMPLEMENTAÇÃO

Depois de concluir a auditoria e definir a arquitetura, implemente a integração em etapas pequenas.

Ordem recomendada:

1. Preparar o terceiro repositório.
2. Preservar os projetos originais.
3. Documentar a arquitetura final.
4. Criar adaptadores.
5. Integrar STT.
6. Integrar TTS.
7. Integrar o ciclo de voz.
8. Integrar actions.
9. Integrar o controle de execução.
10. Validar provedores.
11. Validar memória e contexto.
12. Integrar a interface.
13. Implementar testes.
14. Documentar o resultado.

Após cada etapa:

- Execute os testes relevantes.
- Verifique imports.
- Verifique logs.
- Verifique dependências.
- Verifique regressões.
- Registre os arquivos alterados.
- Documente problemas encontrados.

Não acumule dezenas de alterações antes de testar.

Não declare uma etapa concluída sem evidências.

---

# 15. DOCUMENTAÇÃO OBRIGATÓRIA

Produza e mantenha:

`docs/INTEGRATION_AUDIT.md`

Auditoria dos projetos.

`docs/ARCHITECTURE.md`

Arquitetura final e responsabilidades.

`docs/INTEGRATION_MAP.md`

Mapeamento dos módulos originais e seus destinos.

`docs/VOICE_PIPELINE.md`

Fluxo de captura, STT, processamento, TTS e reprodução.

`docs/TOOLS.md`

Contratos e documentação das ferramentas.

`docs/SECURITY.md`

Modelo de permissões, execução e auditoria.

`docs/TESTING.md`

Testes, resultados e limitações.

`README.md`

Instalação, configuração, inicialização e funcionalidades reais do ULTRON 2.0.

Não documente funcionalidades que ainda não existem como se estivessem concluídas.

---

# 16. CONTROLE DE ALTERAÇÕES

Utilize Git para manter rastreabilidade.

Antes da implementação:

- Verifique o estado dos repositórios.
- Identifique arquivos não rastreados.
- Não descarte alterações preexistentes.
- Crie uma branch de trabalho no terceiro repositório.
- Registre um ponto de restauração.

Durante a implementação:

- Trabalhe por etapas.
- Utilize commits pequenos e descritivos.
- Não utilize `git reset --hard`.
- Não utilize `git clean -fd`.
- Não execute `git push --force`.
- Não sobrescreva históricos.
- Não altere os repositórios originais.

Se houver conflitos, interrompa a etapa, documente o problema e resolva preservando as implementações existentes.

---

# 17. CRITÉRIOS DE ACEITAÇÃO

A integração só poderá ser considerada concluída quando:

1. O ULTRON iniciar utilizando a nova infraestrutura.
2. O núcleo original do ULTRON continuar funcional.
3. A comunicação por texto continuar funcionando.
4. O STT estiver integrado e testado.
5. O TTS estiver integrado e testado.
6. O fluxo de voz utilizar o mesmo orquestrador do texto.
7. As ferramentas selecionadas do Mark-LVI estiverem acessíveis por adaptadores.
8. O controle de execução estiver funcionando.
9. A memória principal continuar sob responsabilidade do ULTRON.
10. Os provedores continuarem funcionando.
11. A interface estiver integrada.
12. Os testes relevantes estiverem passando.
13. Os projetos originais permanecerem intactos.
14. A documentação refletir o comportamento real.
15. Os limites de segurança estiverem implementados.

Se algum requisito não puder ser concluído, identifique-o como pendente, explique a causa e apresente evidências.

Não declare sucesso parcial como sucesso total.

---

# 18. INSTRUÇÕES DE EXECUÇÃO PARA O AGENTE

Siga rigorosamente esta sequência:

**PRIMEIRO: AUDITAR.**

Não altere arquivos durante o inventário inicial.

**SEGUNDO: DOCUMENTAR.**

Crie o relatório técnico e o mapa de integração.

**TERCEIRO: PLANEJAR.**

Defina os módulos que serão reutilizados, adaptados, substituídos ou descartados.

**QUARTO: VALIDAR A ARQUITETURA.**

Verifique se o projeto resultante preserva o ULTRON como núcleo inteligente e o Mark-LVI como infraestrutura operacional.

**QUINTO: IMPLEMENTAR.**

Execute a integração em etapas pequenas, verificáveis e reversíveis.

**SEXTO: TESTAR.**

Teste individualmente e em conjunto todos os componentes integrados.

**SÉTIMO: DOCUMENTAR O RESULTADO.**

Atualize toda a documentação e apresente um relatório final.

## REGRAS FINAIS

- Não invente informações.
- Não presuma compatibilidade.
- Não ignore dependências.
- Não reescreva componentes funcionais sem necessidade.
- Não crie implementações duplicadas.
- Não altere o núcleo do ULTRON para acomodar limitações desnecessárias do Mark-LVI.
- Não permita que o Mark-LVI substitua o orquestrador do ULTRON.
- Não sacrifique funcionalidades existentes para simplificar a integração.
- Não esconda problemas.
- Não execute ações destrutivas sem autorização.
- Não considere código escrito como código validado.

**A prioridade é construir um sistema unificado, modular, funcional, eficiente e sustentável, não apenas produzir uma demonstração visual.**

O resultado deverá ser um único sistema: ULTRON 2.0.

**Um núcleo inteligente próprio, uma infraestrutura operacional reutilizada e uma arquitetura na qual cada componente possui uma responsabilidade inequívoca.**
