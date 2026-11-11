# SECURITY — permissões, execução e auditoria

Modelo de segurança **efetivamente implementado** no ULTRON 2.0. Itens ainda não
implementados estão listados como pendência, não como concluídos.

## 1. Princípios

- A personalidade do sistema não altera políticas: segurança vive no código, não
  no prompt.
- O modelo **propõe** ferramentas; o gateway decide se executa.
- Resultado de ferramenta é **dado não confiável**, nunca instrução.
- Ações destrutivas exigem confirmação explícita, dada pela interface (CLI/HUD)
  com token de uso único; sem `AuthorizationManager` ligado, são recusadas; por
  voz, são sempre recusadas.
- Segredos nunca são logados, impressos ou duplicados.

## 2. Controle de execução de ferramentas

### 2.1 Allowlist

Só executa ferramenta com `ToolContract` registrado. Nome fora da lista devolve
`unknown tool` com a lista de disponíveis — não há execução dinâmica.

### 2.2 Validação de parâmetros

- campos obrigatórios presentes e não vazios;
- parâmetros desconhecidos rejeitados (evita injeção de opções);
- tipos conferidos, com coerção apenas trivial (`"3"`→3, `"true"`→True);
- nenhuma string vira shell: actions recebem dicionário, não linha de comando.

### 2.3 Timeout e isolamento

- cada ferramenta tem teto (`system_status` 10 s, `open_app` 20 s, `reminder`
  15 s, `web_search` 30 s, memória 5 s);
- execução em worker thread (`asyncio.to_thread`) com `asyncio.wait_for`, então
  uma action travada não bloqueia o event loop do núcleo;
- timeout, exceção e saída inválida viram `ToolResult(ok=False)`.

### 2.4 Autorização interativa (Fase 2 do ULTRON 2.1)

`ToolContract.requires_confirmation` é honrado pelo gateway através do
`AuthorizationManager` (`ultron_2_0/authorization.py`). O fluxo é separado em
três etapas e **o modelo não participa da decisão**:

```text
pedido    -> request(): PendingAction + token aleatório + fingerprint
             (ferramenta + argumentos exatos) + expiração
decisão   -> approve()/reject() vêm da interface (CLI ou HUD)
execução  -> consume(): valida token, expiração e fingerprint, marca usado
```

Propriedades verificadas em `tests/test_authorization.py` (14 testes):

| Propriedade | Mecanismo | Falha resultante |
|---|---|---|
| token de uso único | `consume` marca `consumed` sob lock | `TokenAlreadyUsed` (replay) |
| expiração | TTL por contrato (`authorization_timeout_seconds`, padrão 120 s) | `ExpiredToken` |
| vínculo ferramenta+argumentos | SHA-256 de `{tool,args}` ordenado | `ArgumentsMismatch` |
| recusa explícita | `reject()` marca `rejected` | `AuthorizationDenied` |
| sem aprovação | estado diferente de `approved` | `ActionNotApproved` |
| concorrência | `threading.Lock` + `Event` por ação | exatamente 1 consumidor vence |
| sem manager ligado | gateway recusa | `authorization: unavailable` |
| handler com defeito | exceção capturada = recusa | `authorization: denied` |

Interfaces:

- **CLI**: `_terminal_confirmation` pergunta `[s/N]` no terminal; sem TTY,
  recusa. O handler é local da CLI — nenhum outro caminho o aciona.
- **HUD**: `GET /api/approvals`, `POST /api/approvals/{id}/approve|reject`; a
  pendência fica visível enquanto o turno aguarda (o gateway espera em worker
  thread, então o event loop continua respondendo).
- **Voz**: `_deny_sensitive_action` **sempre recusa** — não há autenticação
  confiável por voz (regra do `AGENTS.md` 2.1); o usuário é orientado a
  confirmar pela CLI/HUD.

Auditoria (`ultron2.security.authorization`): pedido, aprovação, recusa,
expiração e consumo são registrados com `action_id` e ferramenta — **nunca** o
token nem o conteúdo dos argumentos.

Limites conhecidos: pendências vivem em memória (reiniciar descarta tudo, o que
é o comportamento seguro); o vetor de aprovação é a interface local, não o
modelo.

### 2.5 Auditoria

Logger `ultron2.tools.audit` registra:

```text
tool=<nome> params=<dict> timeout=<s> authorized=<bool>
tool=<nome> status=ok bytes=<n>
tool=<nome> status=timeout limit=<s>
tool=<nome> rejected=validation error=<motivo>
tool=<nome> authorization=denied type=<classe> reason=<motivo>
tool=<nome> authorization=approved action=<id>
authorization requested action=<id> tool=<nome> ttl=<s>
authorization <approved|rejected|expired|consumed> action=<id> tool=<nome>
```

Nenhum valor de credencial passa por esse caminho.

## 3. Ferramentas deliberadamente fora do allowlist

| Componente | Risco | Decisão |
|---|---|---|
| `game_updater` | desativa `pyautogui.FAILSAFE`; shutdown agendado sem gate | **desconectado** |
| `computer_settings` | `shell=True` com entrada montável | **desconectado** |
| `dev_agent`, `code_helper`, `file_processor` | execução de código | **desconectado** |
| `browser_control` | `playwright` ausente; perfis reais do navegador | **desconectado** |
| `file_controller`, `computer_control`, `desktop` | escrita/controle sem gate ativo | **desconectado** |
| demais actions fora do subset | não revisadas | **desconectado** |

Reconectar qualquer uma exige: revisão da implementação real, contrato com
permissões/timeout, gate de confirmação ligado e testes não destrutivos.

## 4. Prompt injection e resultados de terceiros

- O resultado entra no histórico como `[TOOL_RESULT tool=… ok=…]` e o prompt
  instrui explicitamente que se trata de **dados**, não de fala do usuário.
- Texto vindo de `web_search` é conteúdo de terceiros; o modelo deve relatar,
  não obedecer.
- Nenhum resultado de ferramenta altera allowlist, permissões ou políticas.

## 5. Credenciais e dados sensíveis

| Item | Política aplicada |
|---|---|
| `GEMINI_API_KEY` | lida do `.env` do `lain/` por caminho absoluto; nunca impressa/logada; não copiada |
| `Mark-LVI-main/config/api_keys.json` | **não existe e não é criado/editado** pelo 2.0 |
| `lain/ultron.db` | nunca aberto; banco do 2.0 é `data/ultron2.db` |
| `Mark-LVI-main/memory/long_term.json` | nunca lido/escrito; memória do 2.0 é `data/memory.json` |
| URLs de banco em logs/status | mascaradas (`sqlite://…/arquivo`) |
| Configurações/credenciais originais | não sobrescritas |

O HUD escuta `127.0.0.1` por padrão; expor em rede exige decisão consciente do
operador (`--host 0.0.0.0`) e não é o modo suportado.

## 6. Limites de execução e concorrência

- Banco aberto em uma única sessão de vida longa no loop dedicado; acesso de
  outro loop (uvicorn) passa por `run_coro`.
- Um turno por vez em cada interface; o gateway não executa ferramentas em
  paralelo dentro do mesmo turno.
- Sem execução irrestrita de shell, sem `eval`, sem `exec` de código de modelo.
- Importações dos projetos originais são somente leitura (`sys.path`).

## 7. Pendências de segurança (explícitas)

| Pendência | Consequência atual |
|---|---|
| Aprovação por voz | recusada por design; confirmar pela CLI/HUD |
| Persistência das pendências | em memória; reiniciar descarta (seguro) |
| Autenticação do HUD | desnecessária no bind local; necessária se exposto em rede |
| Rate limiting / orçamento de chamadas | não implementado |
| Assinatura/checagem de integridade das actions | não implementada |
| Sandbox para actions que escrevem no sistema | não implementado; por isso estão desconectadas |
| Trilha de auditoria persistente em arquivo | hoje vai para o logging padrão |

Estes itens não bloqueiam o uso local atual, mas devem ser resolvidos antes de
expor o sistema em rede ou reconectar actions de escrita/execução.
