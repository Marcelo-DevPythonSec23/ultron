# ULTRON 2.1 — Automatic AI Provider Failover
## Gemini API → NVIDIA NIM API

### Objetivo principal

Implementar um sistema inteligente de alternância automática entre provedores de modelos de IA no ULTRON.

O Gemini será o provedor primário e a NVIDIA NIM será o provedor secundário.

Quando o Gemini atingir seu limite de utilização, esgotar sua cota ou apresentar uma indisponibilidade recuperável, o ULTRON deverá alternar automaticamente para NVIDIA NIM, sem exigir intervenção do usuário, reinicialização do sistema ou reenvio manual da mensagem.

O usuário deverá continuar conversando normalmente com o ULTRON, independentemente de qual provedor esteja ativo.

**IMPORTANTE:** O ULTRON continua sendo o núcleo cognitivo e a autoridade central do sistema. Os providers são apenas mecanismos de inferência.

---

### 1. Auditoria da arquitetura atual

Antes de implementar qualquer alteração, examine:

- `ModelRouter`
- `ProviderRegistry`
- `LLMProvider`
- `GeminiProvider`
- `NVIDIAProvider`, caso já exista
- `AgentOrchestrator`
- `OrchestratorBridge`
- Configurações e carregamento de variáveis de ambiente
- Sistema atual de retry e backoff
- Interface desktop e HUD web

Identifique o fluxo completo:

`User → Interface → OrchestratorBridge → Orchestrator → ModelRouter → Provider → Response`

Verifique quais mecanismos já existem e reutilize-os.

Não crie implementações duplicadas.

### 2. Configuração dos providers

Configuração desejada:

```python
PROVIDER_SETTINGS = {
    "primary": "gemini",
    "fallback": "nvidia",
    "auto_failover": True,
    "auto_failback": True,
    "max_retries_per_provider": 1,
    "cooldown_seconds": 60,
}
```

As configurações devem ser integradas ao sistema existente, sem obrigatoriamente utilizar esse formato literal.

Credenciais:

- `GEMINI_API_KEY`
- `NVIDIA_API_KEY`

Regras:

- Nunca inserir credenciais diretamente no código.
- Nunca registrar chaves em logs.
- Nunca expor credenciais na interface.
- Não alterar arquivos `.env` originais.
- Não sobrescrever configurações existentes.

### 3. Detecção inteligente de falhas

Criar classificação de erros por provider.

**Erros recuperáveis:**

- HTTP 429: rate limit ou cota excedida.
- RESOURCE_EXHAUSTED: limite de utilização.
- HTTP 500: erro interno transitório.
- HTTP 502: bad gateway.
- HTTP 503: serviço indisponível.
- HTTP 504: gateway timeout.
- Timeout de conexão.
- Falhas transitórias de rede.

**Erros que não devem provocar failover indiscriminado:**

- HTTP 400: requisição inválida.
- HTTP 401: credencial inválida.
- HTTP 403: permissão negada.
- Modelo inexistente ou incompatível.
- Parâmetros inválidos.

Distinguir rate limit temporário de esgotamento de cota diária quando as informações do provider permitirem.

Respeitar `Retry-After` quando fornecido.

Não realizar tentativas infinitas.

### 4. Sistema automático de failover

Implementar o seguinte comportamento:

1. Receber a solicitação do usuário.
2. Consultar o provider primário.
3. Enviar a requisição ao Gemini.
4. Se a resposta for bem-sucedida, retornar normalmente.
5. Se ocorrer uma falha recuperável, classificar o erro.
6. Se a política permitir, ativar NVIDIA NIM.
7. Reenviar a mesma solicitação lógica ao provider secundário.
8. Receber a resposta.
9. Retornar a resposta ao mesmo fluxo de conversa.
10. Registrar a mudança de provider.

A troca deve acontecer dentro do ModelRouter, sem criar outro orquestrador.

### 5. Preservação integral do contexto

O failover não pode causar:

- Perda do histórico.
- Duplicação de mensagens.
- Criação de outra conversa.
- Reinicialização do Orchestrator.
- Alteração indevida da memória.
- Perda do system prompt.
- Repetição de ferramentas que já produziram efeitos externos.

O provider secundário deverá receber o mesmo contexto lógico, histórico, instruções e parâmetros compatíveis.

Adaptar apenas os parâmetros incompatíveis entre APIs.

**Atenção especial:** se uma requisição envolver execução de ferramentas, nunca repetir automaticamente uma ação externa sem verificar se ela já foi executada.

### 6. Circuit Breaker

Implementar controle de disponibilidade individual para cada provider.

Estados:

- `HEALTHY`: provider disponível.
- `DEGRADED`: falhas recentes ou desempenho reduzido.
- `OPEN`: provider temporariamente indisponível.
- `HALF_OPEN`: testes controlados de recuperação.

Comportamento:

- Evitar enviar requisições repetidas a providers indisponíveis.
- Aplicar cooldown.
- Permitir teste de recuperação.
- Recuperar automaticamente o provider quando estiver saudável.
- Evitar alternância constante entre Gemini e NVIDIA.

### 7. Failback automático

Quando o Gemini voltar a funcionar:

1. Detectar a recuperação por uma tentativa controlada.
2. Validar a resposta.
3. Restaurar Gemini como provider primário.
4. Manter NVIDIA como fallback.
5. Registrar a recuperação.

Não interromper conversas em andamento durante a recuperação.

### 8. Interface visual

Atualizar os indicadores de provider na interface desktop e no HUD web.

Exibir:

- Provider ativo.
- Modelo utilizado.
- Estado de disponibilidade.
- Última mudança de provider.
- Motivo do failover.

Exemplos:

```text
ULTRON STATUS

PROVIDER: GEMINI
MODEL: gemini-model
STATUS: HEALTHY
```

```text
ULTRON STATUS

PROVIDER: NVIDIA NIM
MODEL: nvidia-model
STATUS: FALLBACK ACTIVE
REASON: GEMINI QUOTA EXCEEDED
```

A interface deve refletir o estado real do ModelRouter, sem simular disponibilidade.

### 9. Integração com agentes

Verificar a integração com:

- AgentOrchestrator.
- DeveloperAgent.
- ResearchAgent.
- SecurityAgent.
- QAAgent.
- DatabaseAgent.
- ArchitectureAgent.
- OpenCodeAdapter.
- MCPAdapter.

Os agentes que utilizam o ModelRouter deverão herdar a política de failover automaticamente, respeitando configurações específicas quando existirem.

Não criar um provider paralelo para cada agente.

Não modificar o funcionamento interno do OpenCode sem necessidade.

### 10. Testes obrigatórios

Criar testes automatizados para:

1. Gemini funcionando normalmente.
2. Gemini atingindo cota e NVIDIA assumindo.
3. Gemini retornando HTTP 429.
4. Gemini retornando HTTP 503.
5. Gemini retornando HTTP 401.
6. Gemini retornando HTTP 403.
7. NVIDIA indisponível.
8. Ambos os providers indisponíveis.
9. Recuperação do Gemini.
10. Circuit breaker.
11. Cooldown.
12. Preservação do histórico.
13. Ausência de mensagens duplicadas.
14. Ausência de execução duplicada de ferramentas.
15. Integração com os agentes internos.
16. Estado correto exibido na interface.

Usar providers fake para testes automatizados.

Criar testes de integração com APIs reais somente quando as credenciais e a rede estiverem disponíveis. Nunca consumir cotas reais na suíte padrão.

### 11. Segurança

Preservar integralmente:

- ToolGateway.
- Allowlist de ferramentas.
- Validação de parâmetros.
- Timeouts.
- Autorizações.
- Confirmações de ações destrutivas.
- Auditoria.
- Isolamento dos bancos de dados.
- Separação entre os projetos originais e ULTRON 2.1.

Não adicionar execução arbitrária de shell, `eval` ou `exec`.

Não reduzir as restrições de segurança para facilitar a integração.

### 12. Documentação

Criar:

`docs/qa/AUTOMATIC_PROVIDER_FAILOVER.md`

Documentar:

- Arquitetura anterior.
- Arquitetura implementada.
- Fluxo de failover.
- Classificação de erros.
- Circuit breaker.
- Failback.
- Configuração dos providers.
- Testes executados.
- Limitações conhecidas.
- Arquivos modificados.

### 13. Critérios de conclusão

A implementação só será considerada concluída quando:

- Gemini funcionar como provider primário.
- NVIDIA funcionar como fallback.
- O failover acontecer automaticamente.
- O contexto da conversa permanecer intacto.
- Não existirem duplicações de mensagens.
- Não houver loops infinitos de retry.
- O estado dos providers for exibido corretamente.
- Os testes de regressão passarem.

### INSTRUÇÃO FINAL

Primeiro audite a arquitetura existente. Depois apresente um plano curto de implementação e execute as alterações.

Não redesenhe a arquitetura do ULTRON.

Não substitua componentes funcionais sem justificativa técnica.

Não modifique `lain/` ou `Mark-LVI-main/`.

Não invente resultados de testes.

Priorize integração limpa, confiabilidade, observabilidade e preservação do núcleo cognitivo do ULTRON.