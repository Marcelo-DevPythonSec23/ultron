# ULTRON 2.0 — INTERFACE ENGINEERING SPECIFICATION
## Transplante integral da interface e das capacidades visuais do Mark LVI

**CLASSIFICAÇÃO:** Especificação principal de implementação  
**PROJETO:** ULTRON 2.0  
**REFERÊNCIA VISUAL E FUNCIONAL:** Mark LVI (FatihMakes)  
**NÚCLEO COGNITIVO:** Lain Orchestrator  
**LINGUAGEM PRINCIPAL:** Python  
**OBJETIVO:** Construir a interface desktop definitiva do ULTRON 2.0, reproduzindo fielmente a interface e os recursos do Mark LVI.

---

# 1. MISSÃO PRINCIPAL

Sua missão é desenvolver a interface desktop definitiva do ULTRON 2.0, utilizando o projeto Mark LVI como referência direta de implementação.

O objetivo NÃO é criar uma interface inspirada no Mark LVI.

O objetivo NÃO é criar uma versão simplificada.

O objetivo NÃO é criar um dashboard genérico de inteligência artificial.

O objetivo é REPRODUZIR, REUTILIZAR E INTEGRAR O MÁXIMO POSSÍVEL DA INTERFACE ORIGINAL DO MARK LVI, incluindo:

- Identidade visual.
- Organização dos componentes.
- Layout.
- Animações.
- Transições.
- Avatar.
- Visualização de voz.
- Indicadores de estado.
- Menus.
- Painéis.
- Configurações.
- Personalização.
- Controles.
- Interações.
- Funcionalidades visuais e operacionais.

A interface final deverá funcionar como o corpo operacional do ULTRON.

O ULTRON será a inteligência central. O Mark LVI fornecerá a experiência visual e os subsistemas de interação que serão incorporados e adaptados.

A interface deverá ser um software desktop completo, não uma página web apresentada como aplicação principal.

# 2. CONTEXTO ARQUITETURAL DO ULTRON

Antes de implementar qualquer coisa, compreenda a arquitetura existente.

O ULTRON 2.0 possui uma arquitetura própria e já funcional.

Componentes documentados:

- Lain Orchestrator.
- OrchestratorBridge.
- UltronCoreRuntime.
- ToolCallingProvider.
- ToolGateway.
- ToolContract.
- ToolResult.
- Memory Tools.
- Voice Pipeline.
- Gemini Live STT.
- Gemini TTS.
- SystemSpeaker.
- Provider Registry.
- Banco de dados isolado.
- Histórico conversacional.
- HUD web local existente.

O Lain é o núcleo conversacional central e deve permanecer como a única autoridade de processamento das conversas.

O fluxo principal de mensagens é:

```text
Interface Desktop
       |
       v
Application Controller
       |
       v
OrchestratorBridge
       |
       v
Lain Orchestrator
       |
       +---- Memory
       |
       +---- Provider Registry
       |
       +---- ToolCallingProvider
                    |
                    v
                ToolGateway
                    |
                    v
                  Actions
```

O fluxo de voz existente é:

```text
Microphone
    |
    v
Gemini Live STT
    |
    v
VoicePipeline
    |
    v
OrchestratorBridge
    |
    v
Lain Orchestrator
    |
    v
Response Text
    |
    v
TTS
    |
    v
Audio Output
```

A nova interface deverá integrar-se a esses fluxos.

## 2.1 Regra arquitetural absoluta

NÃO criar um segundo cérebro.

NÃO criar outro Orchestrator.

NÃO criar outro sistema independente de histórico conversacional.

NÃO duplicar a memória central.

NÃO implementar um mecanismo paralelo de decisão por regex ou regras improvisadas.

NÃO permitir que a interface execute ferramentas diretamente, contornando o ToolGateway.

NÃO substituir funcionalidades existentes por simulações.

A interface deve consumir os serviços existentes e apresentar seus estados e resultados reais.

# 3. INSPEÇÃO OBRIGATÓRIA DO MARK LVI

Antes de começar a implementação, faça uma análise completa do código-fonte original.

Não trabalhe apenas com screenshots, descrições ou documentação superficial.

Investigue o projeto real.

Identifique:

1. Framework gráfico utilizado.
2. Ponto de entrada da interface.
3. Organização das janelas.
4. Componentes visuais.
5. Componentes reutilizáveis.
6. Sistema de animações.
7. Sistema de partículas.
8. Avatar e renderização.
9. Sincronização de áudio e animação.
10. Menus e navegação.
11. Configurações.
12. Personalização visual.
13. Sistema de voz.
14. Seleção de dispositivos.
15. Sistema de sessões.
16. Histórico.
17. Memória.
18. Gerenciamento de providers.
19. Skills e plugins.
20. Eventos internos.
21. Comunicação entre frontend e backend.
22. Dependências externas.
23. Recursos gráficos.
24. Arquivos de configuração.
25. Licença e condições de reutilização.

Produza um inventário técnico antes de iniciar a implementação.

Para cada funcionalidade, classifique:

- Reutilizável diretamente.
- Reutilizável com adaptação.
- Necessita reimplementação.
- Já existente no ULTRON.
- Não disponível no código original.
- Bloqueada por dependência ou incompatibilidade.

Não declare que uma funcionalidade foi integrada sem verificar sua implementação real.

# 4. FIDELIDADE VISUAL ABSOLUTA

A interface do Mark LVI será a referência visual principal.

Preserve o máximo possível:

- Dimensões e proporções.
- Distribuição dos painéis.
- Espaçamento.
- Tipografia.
- Hierarquia visual.
- Paleta de cores.
- Transparências.
- Bordas.
- Efeitos luminosos.
- Elementos holográficos.
- Indicadores.
- Animações.
- Transições.
- Ícones.
- Comportamento dos menus.
- Organização dos controles.

Não substitua componentes originais por versões genéricas sem necessidade técnica comprovada.

Não remova animações porque são difíceis de implementar.

Não simplifique o avatar.

Não substitua elementos gráficos por emojis.

Não transforme a interface em um dashboard administrativo convencional.

Não invente uma identidade visual alternativa.

O resultado deverá ser visualmente reconhecível como a interface do Mark LVI.

Quando houver incompatibilidade técnica, documente o motivo e procure a adaptação mais fiel possível.

# 5. ARQUITETURA DESKTOP

A interface principal deverá funcionar como aplicação desktop.

Investigue a compatibilidade do projeto original com o ambiente do ULTRON.

Avalie prioritariamente:

- PySide6.
- Qt Widgets.
- Qt Quick.
- QML.

Se o Mark LVI utilizar outro framework, avalie primeiro a possibilidade de preservar sua implementação original.

Não escolha uma tecnologia apenas por preferência pessoal.

A escolha deverá considerar:

- Compatibilidade com o código existente.
- Fidelidade visual.
- Performance.
- Renderização.
- Animações.
- Integração com Python.
- Consumo de memória.
- Facilidade de manutenção.
- Compatibilidade com Linux.

O HUD web atual não deverá ser considerado a interface principal definitiva.

Ele poderá permanecer como ferramenta auxiliar de desenvolvimento e diagnóstico, desde que não interfira no novo aplicativo.

Não introduza Electron, Chromium ou servidores HTTP desnecessários sem justificativa técnica.

# 6. SISTEMA DE INICIALIZAÇÃO

Reproduza a experiência de inicialização do Mark LVI.

A inicialização deverá possuir:

- Animação de abertura.
- Transições visuais.
- Carregamento dos componentes.
- Inicialização do avatar.
- Verificação dos subsistemas.
- Verificação dos providers.
- Verificação do sistema de áudio.
- Comunicação com o núcleo ULTRON.
- Indicadores de disponibilidade.
- Tratamento de falhas.

A interface deverá distinguir:

```text
STARTING
INITIALIZING
CONNECTING_CORE
CHECKING_AUDIO
CHECKING_PROVIDERS
READY
DEGRADED
ERROR
```

Não apresentar o ULTRON como pronto enquanto o núcleo não estiver efetivamente disponível.

Se algum subsistema falhar, apresentar seu estado real sem impedir desnecessariamente o funcionamento dos demais.

# 7. SISTEMA VISUAL E AVATAR

Reproduza o sistema visual original do Mark LVI.

Inclua, conforme disponível no código original:

- Avatar central.
- Visualização holográfica.
- Partículas.
- Ondas.
- Elementos luminosos.
- Efeitos de movimento.
- Animações de estado.
- Expressões faciais.
- Lip-sync.
- Efeitos durante a fala.
- Efeitos durante a escuta.
- Efeitos durante o processamento.

As animações devem estar vinculadas aos eventos reais do ULTRON.

Implemente uma máquina de estados visual centralizada:

```text
IDLE
LISTENING
PROCESSING
PLANNING
EXECUTING
SPEAKING
WAITING_CONFIRMATION
INTERRUPTED
ERROR
OFFLINE
```

Cada estado deverá possuir uma representação visual própria.

Exemplos:

- IDLE: animação de repouso.
- LISTENING: indicação de captura de áudio.
- PROCESSING: animação de processamento.
- EXECUTING: representação de execução de ferramentas.
- SPEAKING: animação sincronizada com a reprodução.
- WAITING_CONFIRMATION: indicação de autorização pendente.
- ERROR: apresentação de falha.
- OFFLINE: indicação de indisponibilidade do núcleo.

Não criar animações que indiquem processamento inexistente.

O estado visual deve refletir os eventos verdadeiros do backend.

# 8. SISTEMA DE VOZ

Integrar a interface ao Voice Pipeline existente.

Funcionalidades desejadas:

- Push-to-talk.
- Controle de microfone.
- Indicador de captura.
- Indicador de transcrição.
- Reprodução de áudio.
- Controle de volume.
- Seleção de dispositivos.
- Interrupção da reprodução.
- Indicador de voz ativa.
- Histórico de transcrições.
- Configuração de idioma.
- Configuração de STT.
- Configuração de TTS.
- Wake word, caso implementada.
- VAD, caso implementado.
- Barge-in, caso implementado.
- Echo guard, caso implementado.

A interface deverá oferecer controles para as funcionalidades que realmente existirem.

Não apresentar wake word, VAD ou barge-in como recursos disponíveis antes de sua integração e validação.

A voz deverá utilizar o mesmo OrchestratorBridge da comunicação textual.

# 9. CHAT E COMMUNICATIONS

Implementar o sistema de conversação integrado.

A interface deverá oferecer:

- Campo de entrada.
- Envio de mensagens.
- Histórico de conversas.
- Exibição de respostas.
- Diferenciação visual entre usuário e assistente.
- Indicador de processamento.
- Exibição de erros.
- Suporte a respostas faladas.
- Opção de reproduzir respostas.
- Opção de interromper a fala.
- Identificação de mensagens associadas a ferramentas.
- Exibição de resultados relevantes.

Toda mensagem deverá utilizar o fluxo central do ULTRON.

A interface não deverá manter uma conversa independente.

O histórico deverá respeitar o mecanismo de persistência já existente.

# 10. PAINEL SYSTEMS

Reproduzir o painel de monitoramento do Mark LVI.

Integrar os dados reais disponíveis.

Possíveis indicadores:

- CPU.
- RAM.
- GPU.
- Temperatura.
- Processos.
- Uptime.
- Recursos do sistema.
- Estado dos serviços.
- Estado do núcleo.
- Estado dos providers.
- Estado do áudio.

Não inventar métricas.

Quando um sensor ou dispositivo não estiver disponível, apresentar indisponibilidade em vez de valores fictícios.

Atualizações deverão ocorrer de maneira assíncrona, sem bloquear a interface.

# 11. PAINEL TASKS

Implementar o painel de tarefas.

Ele deverá apresentar as operações realmente existentes no ULTRON.

Exemplos:

- Ferramentas em execução.
- Ferramentas concluídas.
- Ferramentas com falha.
- Operações pendentes.
- Ações aguardando confirmação.
- Estado das tarefas.
- Tempo de execução.
- Resultado resumido.

Respeitar os estados reais do ToolResult:

```text
done
unverified
failed
started
```

Nunca apresentar uma ferramenta como concluída apenas porque sua execução começou.

# 12. PERSONALIZAÇÃO COMPLETA

Reproduzir as opções de personalização existentes no Mark LVI.

Investigue e implemente, conforme disponíveis:

- Alteração do nome do assistente.
- Alteração de cores.
- Temas.
- Aparência.
- Configuração de avatar.
- Configuração de animações.
- Configuração de transparência.
- Configuração de menus.
- Preferências visuais.
- Configuração de áudio.
- Configuração de dispositivos.
- Configuração de idioma.
- Preferências de inicialização.
- Atalhos.
- Configurações de comportamento visual.

As configurações deverão ser persistentes.

Não armazenar preferências temporárias apenas em variáveis de execução.

Criar uma estrutura de configuração organizada, validada e versionada.

Alterar a identidade visual não poderá modificar a personalidade ou o comportamento do núcleo cognitivo.

# 13. ENGINE E PROVIDER MANAGER

A interface deverá permitir visualizar e gerenciar os providers disponíveis.

O sistema deverá respeitar o Provider Registry existente.

Investigue a possibilidade de integrar:

- Gemini.
- OpenAI.
- OpenRouter.
- Groq.
- DeepSeek.
- Mistral.
- xAI.
- Ollama.
- LM Studio.
- llama.cpp.
- vLLM.
- Outros providers compatíveis.

Não declarar suporte apenas porque um provider aparece em uma lista.

Cada integração deverá possuir implementação real e compatibilidade com o contrato LLMProvider.

A interface deverá permitir, conforme suportado:

- Seleção de provider.
- Seleção de modelo.
- Visualização do provider ativo.
- Configuração de endpoints.
- Configuração de credenciais.
- Teste de conexão.
- Exibição de erros.
- Configuração de fallback.
- Configuração de modelos locais.

Segredos deverão ser protegidos e nunca exibidos em logs.

# 14. MEMORY MANAGER

Integrar o painel de memória à memória central do ULTRON.

A interface deverá permitir:

- Visualizar memórias.
- Pesquisar memórias.
- Consultar categorias.
- Criar memórias explicitamente.
- Editar memórias, se suportado.
- Excluir memórias com confirmação.
- Consultar informações armazenadas.
- Visualizar operações recentes.

Não criar um segundo banco de memória independente.

Respeitar os contratos remember, recall e forget.

Toda operação destrutiva deverá passar pelo mecanismo de confirmação do sistema.

# 15. SKILLS E PLUGINS

Investigar e integrar o sistema de skills e plugins do Mark LVI.

O objetivo é oferecer gerenciamento visual das capacidades disponíveis.

Recursos desejados:

- Listagem.
- Descoberta.
- Informações.
- Ativação.
- Desativação.
- Configuração.
- Dependências.
- Estado.
- Logs.
- Permissões.
- Erros de carregamento.

Skills não poderão ignorar o ToolGateway quando executarem operações protegidas.

Nenhuma extensão deverá obter autoridade irrestrita sobre o sistema apenas por estar instalada.

# 16. DESKTOP CONTROL

Integrar as funcionalidades de controle do desktop que forem compatíveis com o modelo de segurança do ULTRON.

Investigar:

- Abrir aplicações.
- Fechar aplicações.
- Trazer janelas para primeiro plano.
- Consultar aplicações abertas.
- Interação com janelas.
- Controle de dispositivos.
- Automação autorizada.
- Gerenciamento de processos.

A implementação deverá respeitar:

- Allowlist.
- Permissões.
- Timeouts.
- Confirmações.
- Auditoria.
- Validação de parâmetros.
- Isolamento de execução.

Não conectar indiscriminadamente todas as actions do Mark LVI.

Actions que executam código, comandos arbitrários ou operações destrutivas deverão passar por revisão de segurança.

# 17. EVENT SYSTEM E INTEGRAÇÃO

Criar uma camada de comunicação organizada entre interface e backend.

A interface deverá receber eventos estruturados.

Exemplo conceitual:

```json
{
  "event": "assistant.state_changed",
  "state": "LISTENING",
  "timestamp": "..."
}
```

Eventos possíveis:

```text
assistant.initialized
assistant.state_changed
assistant.listening
assistant.processing
assistant.executing_tool
assistant.tool_completed
assistant.tool_failed
assistant.confirmation_required
assistant.speaking
assistant.interrupted
assistant.error

voice.transcription
voice.playback_started
voice.playback_finished
voice.device_changed

memory.updated
provider.changed
provider.failed

task.started
task.completed
task.failed

system.metrics_updated
session.updated
```

Os eventos são uma proposta de contrato, não uma afirmação de que todos já existem.

Mapeie os eventos aos serviços reais.

A comunicação deverá ser assíncrona.

Não bloquear a thread gráfica durante processamento de IA, operações de rede, áudio ou ferramentas.

# 18. API E ADAPTER

Avaliar se a arquitetura atual exige uma API interna ou se a comunicação direta por interfaces Python é suficiente.

Não criar uma API apenas por conveniência.

Caso seja necessária, avaliar:

- REST para comandos e configurações.
- WebSocket para eventos.
- Interfaces Python para serviços internos.
- Contratos tipados.
- Validação.
- Tratamento de erros.
- Controle de ciclo de vida.

Criar um adapter entre os componentes reutilizados do Mark LVI e os serviços centrais do ULTRON quando necessário.

Não importar o ciclo de sessão completo do Mark LVI.

Não executar seu Orchestrator original.

Não duplicar seu histórico.

Não permitir duas autoridades de LLM.

# 19. SEGURANÇA

A interface deverá respeitar integralmente o modelo de segurança existente.

Princípios obrigatórios:

1. O modelo propõe ferramentas.
2. O ToolGateway decide se executa.
3. A interface solicita ações através das interfaces autorizadas.
4. Ações destrutivas exigem confirmação explícita.
5. Resultados externos são dados não confiáveis.
6. Credenciais não aparecem em logs.
7. Parâmetros são validados.
8. Operações possuem timeout.
9. Falhas são registradas.
10. Não existe execução irrestrita de código produzido pelo modelo.

A interface deverá oferecer um mecanismo real de confirmação.

A confirmação precisa estar vinculada à operação específica, apresentar os detalhes da ação e permitir aceitar ou recusar.

Não criar botões decorativos de confirmação.

Não remover proteções existentes para facilitar a integração.

# 20. EXPERIÊNCIA DE USO

A interface deverá funcionar como uma central de interação completa.

O usuário deverá conseguir:

- Abrir o ULTRON.
- Visualizar sua inicialização.
- Conversar por texto.
- Conversar por voz.
- Ouvir respostas.
- Interromper a fala.
- Acompanhar o estado do assistente.
- Visualizar ferramentas.
- Acompanhar tarefas.
- Consultar memória.
- Gerenciar providers.
- Configurar voz.
- Personalizar a aparência.
- Gerenciar plugins.
- Consultar métricas.
- Autorizar operações.
- Consultar histórico.

A experiência deverá ser fluida, responsiva e consistente.

Não exigir terminal para operações normais que tenham controles previstos na interface.

O terminal poderá continuar disponível para diagnóstico e administração avançada.

# 21. PERFORMANCE E RECURSOS

O ULTRON deverá funcionar em hardware limitado.

O ambiente de desenvolvimento possui restrições severas de memória e processamento.

Portanto:

- Evitar renderização desnecessária.
- Evitar loops de atualização excessivamente frequentes.
- Evitar carregar recursos gráficos gigantes sem necessidade.
- Otimizar animações.
- Utilizar carregamento sob demanda.
- Liberar recursos de áudio.
- Encerrar subprocessos corretamente.
- Evitar vazamentos de memória.
- Separar tarefas pesadas da thread gráfica.
- Evitar múltiplas instâncias do mesmo serviço.

A interface deverá degradar graciosamente em hardware limitado.

Não sacrificar a fidelidade visual sem antes avaliar técnicas de otimização.

# 22. TESTES OBRIGATÓRIOS

A implementação deverá possuir testes próprios.

Cobrir:

## Inicialização
- Abertura da aplicação.
- Inicialização do núcleo.
- Falha de provider.
- Falha de áudio.
- Recuperação.

## Interface
- Abertura de janelas.
- Navegação.
- Menus.
- Configurações.
- Persistência visual.
- Mudança de tema.

## Comunicação
- Mensagem enviada ao OrchestratorBridge.
- Resposta recebida.
- Histórico.
- Eventos.
- Falhas de comunicação.

## Voz
- Captura.
- Transcrição.
- Reprodução.
- Interrupção.
- Seleção de dispositivos.

## Ferramentas
- Exibição de tarefas.
- Estados reais.
- Falhas.
- Confirmação.
- Recusa de operações.

## Memória
- Consulta.
- Pesquisa.
- Criação.
- Exclusão com confirmação.

## Performance
- Tempo de inicialização.
- Uso de memória.
- Responsividade.
- Atualização dos indicadores.
- Estabilidade prolongada.

Os testes devem distinguir:

- Testes unitários.
- Testes de integração.
- Testes de interface.
- Testes de hardware.
- Testes reais de providers.

Não utilizar mocks para afirmar que uma integração externa foi validada em ambiente real.

# 23. ESTRATÉGIA DE IMPLEMENTAÇÃO

Trabalhe em etapas.

Não tente modificar toda a aplicação em uma única operação.

## ETAPA 1 — AUDITORIA

- Inspecionar o Mark LVI.
- Inspecionar o ULTRON 2.0.
- Mapear dependências.
- Mapear componentes visuais.
- Mapear funcionalidades.
- Identificar incompatibilidades.
- Avaliar licenças.
- Produzir inventário.

Entregável: `INTERFACE_AUDIT.md`.

## ETAPA 2 — ARQUITETURA

- Definir framework.
- Definir estrutura de diretórios.
- Definir contratos.
- Definir eventos.
- Definir comunicação com o backend.
- Definir gerenciamento de ciclo de vida.

Entregável: `INTERFACE_ARCHITECTURE.md`.

## ETAPA 3 — TRANSPLANTE VISUAL

- Reutilizar componentes originais.
- Reproduzir layout.
- Reproduzir animações.
- Reproduzir avatar.
- Reproduzir menus.
- Reproduzir painéis.
- Reproduzir transições.

Não conectar funcionalidades fictícias nesta etapa.

## ETAPA 4 — INTEGRAÇÃO COM O CORE

- Conectar OrchestratorBridge.
- Conectar memória.
- Conectar providers.
- Conectar ToolGateway.
- Conectar histórico.
- Conectar estados.
- Conectar eventos.

## ETAPA 5 — VOZ

- Conectar STT.
- Conectar TTS.
- Conectar dispositivos.
- Conectar controles.
- Implementar recursos adicionais que forem suportados.

## ETAPA 6 — FUNCIONALIDADES OPERACIONAIS

- Tasks.
- Skills.
- Plugins.
- Desktop Control.
- Configurações.
- Personalização.
- Confirmações.

## ETAPA 7 — VALIDAÇÃO

- Testes.
- Correções.
- Performance.
- Verificação visual.
- Verificação de integração.
- Documentação final.

Cada etapa deverá terminar com evidências de implementação e testes.

Não declarar uma etapa concluída enquanto houver funcionalidades obrigatórias daquela etapa sem implementação ou justificativa documentada.

# 24. ESTRUTURA DE CÓDIGO

A estrutura final deverá manter separação de responsabilidades.

A estrutura exata deverá ser definida após auditoria, mas considere uma organização semelhante a:

```text
ultron-2.0/
│
├── ultron_2_0/
│   ├── core/
│   ├── voice/
│   ├── memory/
│   ├── tools/
│   ├── providers/
│   │
│   ├── interface/
│   │   ├── application/
│   │   ├── windows/
│   │   ├── components/
│   │   ├── panels/
│   │   ├── avatar/
│   │   ├── animations/
│   │   ├── themes/
│   │   ├── controllers/
│   │   ├── adapters/
│   │   ├── events/
│   │   └── assets/
│   │
│   └── runtime/
│
├── tests/
│   ├── interface/
│   ├── integration/
│   └── performance/
│
└── docs/
    ├── INTERFACE_AUDIT.md
    ├── INTERFACE_ARCHITECTURE.md
    ├── INTERFACE_INTEGRATION.md
    └── INTERFACE_TESTING.md
```

Não reorganize módulos existentes sem necessidade.

Não duplique código que já possui uma implementação funcional.

# 25. REGRAS DE PRESERVAÇÃO

Os seguintes componentes são críticos:

- `lain/`
- `Mark-LVI-main/`
- `ultron-2.0/`

Não modificar os projetos originais Lain e Mark LVI de maneira destrutiva.

Preservar os bancos originais.

Preservar os arquivos de memória originais.

Preservar credenciais.

Não sobrescrever configurações existentes.

Qualquer adaptação deverá ser realizada na camada do ULTRON 2.0, salvo autorização explícita.

Não apagar implementações anteriores sem demonstrar que são obsoletas e sem preservar uma forma segura de recuperação.

# 26. REGRAS DE TRABALHO DO AGENTE

Você está trabalhando em um projeto existente.

Portanto:

- Primeiro inspecione.
- Depois compreenda.
- Em seguida planeje.
- Só então implemente.
- Teste cada alteração.
- Documente decisões.
- Preserve funcionalidades anteriores.

Não invente arquivos ou APIs.

Não suponha que uma dependência está instalada.

Não suponha que uma funcionalidade está implementada.

Não use placeholders como substitutos de funcionalidades concluídas.

Não esconda erros.

Não silencie exceções sem justificativa.

Não transforme testes de integração em testes puramente simulados.

Não faça refatorações fora do escopo.

Não altere o núcleo cognitivo para resolver problemas puramente visuais.

Se uma funcionalidade não puder ser implementada, explique:

1. O motivo.
2. A dependência ausente.
3. A incompatibilidade.
4. O impacto.
5. A solução recomendada.

Se encontrar uma decisão arquitetural que precise mudar, apresente a justificativa antes de alterar componentes centrais.

# 27. CRITÉRIOS DE ACEITAÇÃO FINAL

O trabalho somente poderá ser considerado concluído quando:

- A aplicação desktop iniciar corretamente.
- A interface reproduzir fielmente o Mark LVI.
- As animações originais estiverem integradas.
- O avatar refletir estados reais.
- O chat utilizar o OrchestratorBridge.
- A voz utilizar o Voice Pipeline.
- O histórico utilizar a persistência central.
- A memória utilizar o sistema central.
- Os providers forem integrados.
- As ferramentas forem controladas pelo ToolGateway.
- Os painéis exibirem dados reais.
- As configurações forem persistentes.
- Os menus funcionarem.
- A personalização funcionar.
- As confirmações forem reais.
- O tratamento de erros funcionar.
- Os testes passarem.
- A documentação refletir o estado real da implementação.

Não confundir fidelidade visual com conclusão funcional.

Não confundir presença de componentes com integração.

Não confundir testes simulados com validação real.

# 28. RESULTADO FINAL ESPERADO

O resultado deverá ser o ULTRON 2.0 com:

**A inteligência do ULTRON e o corpo operacional do Mark LVI.**

Uma única inteligência central.

Uma única memória central.

Um único histórico conversacional.

Um único mecanismo de decisão.

Uma interface desktop completa.

Uma experiência visual fiel ao Mark LVI.

Uma arquitetura modular, testável, segura e extensível.

O usuário deverá poder conversar com o ULTRON por texto e voz, visualizar suas atividades, acompanhar suas ferramentas, personalizar sua aparência e controlar as funcionalidades disponíveis através de uma única aplicação desktop.

A interface não é um acessório.

A interface é a principal superfície de interação com o ULTRON.

**PRIORIDADE ABSOLUTA: fidelidade à implementação original do Mark LVI, integração real com o ULTRON e preservação da arquitetura existente.**

Não construa algo parecido quando for possível reutilizar o original.

Não simplifique aquilo que foi solicitado para ser reproduzido integralmente.

Não sacrifique a arquitetura para conseguir uma demonstração visual.

Construa o corpo definitivo do ULTRON.