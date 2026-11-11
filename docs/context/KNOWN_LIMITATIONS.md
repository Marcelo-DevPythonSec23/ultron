# KNOWN_LIMITATIONS — limitações conhecidas

**Regra:** limitação não é desculpa; é estado documentado. Tudo aqui tem causa
técnica identificada. Não prometa o que está nesta lista.

## 1. Voz

| Limitação | Causa | Mitigação/estado |
|---|---|---|
| Sem wake word | não implementada no 2.0 | iniciar voz explicitamente (`--voice`) |
| Sem VAD | idem | turnos por transcrição final do Live |
| Sem barge-in | idem | — |
| STT Live exige rede e chave | Gemini Live é remoto | erro controlado; `--audio` em lote |
| Dependência de `parec/arecord` e `aplay/paplay` | áudio do SO | `--list-devices`; erro explícito |
| Qualidade/latência dependem do provedor | rede/quota | configurável por modelo |

## 2. Ferramentas e ações

| Limitação | Causa | Estado |
|---|---|---|
| Só 4 actions operacionais + 3 de memória | subset curado por risco | `docs/INTEGRATION_MAP.md` |
| `file_controller`, `computer_settings`, `game_updater` etc. desconectadas | `shell=True`, pyautogui sem failsafe, credenciais | `BLOCKED` |
| `forget` sempre recusado | não há UI de confirmação | seguro por desenho |
| `open_app` depende de apps instalados | ambiente | erro controlado |
| `web_search` depende de rede/DDG | externo | timeout e dado não confiável |
| Sem shell/eval/exec genérico | proibido | permanente |

## 3. Memória

| Limitação | Causa | Estado |
|---|---|---|
| Nada é memorizado automaticamente | política explícita | por desenho |
| Busca lexical (sem embeddings) | dependência opcional evitada | ver `docs/memory/` |
| Sem knowledge graph | sem necessidade demonstrada | `PLANNED` |
| Sem UI de edição de memória | HUD atual só lê estado | `PLANNED` |
| Consolidação/versão em evolução | implementação incremental | ver `MEMORY_AUDIT.md` |

## 4. Contexto e sessões

| Limitação | Causa | Estado |
|---|---|---|
| Uma sessão de interface corrente por bridge | simplicidade | `new_conversation` |
| Sem multiusuário/autenticação | uso pessoal local | `PLANNED` |
| Contexto limitado por tokens do lain | `MAX_CONTEXT_TOKENS` | configurável |

## 5. Infraestrutura

| Limitação | Causa | Estado |
|---|---|---|
| `Mark-LVI-main` sem git | projeto original | não versionado |
| `lain/.env.example` modificado preexistente | usuário | não tocar |
| `google-genai` 3.x incompatível com runtime Mark-LVI | pin `<3` | runtime não executado |
| Sem GPU/modelo local | hardware ~4 GB | APIs remotas |
| HUD local sem TLS/auth | uso local | não expor à rede |

## 6. Testes

| Limitação | Causa |
|---|---|
| Sem teste ao vivo automatizado de STT/TTS | rede, quota, microfone |
| Sem benchmark de latência/tokens | não implementado |
| Sem avaliação de qualidade do recall | metodologia não definida |
| `lain` tem 64 testes; 2.0 tem 88 | linha de base atual |

## 7. Segurança (riscos pendentes)

1. Resultado de ferramenta é tratado como dado, mas o modelo ainda pode ser
   induzido por conteúdo externo — mitigação é prompt + validação, não completa.
2. Cancelar `asyncio.wait_for` **não interrompe** uma thread já em execução; o
   gateway usa timeout de espera, não de thread.
3. `forget` sem UI de confirmação é recusado (seguro), mas não há exclusão
   interativa.
4. Segredos: `GEMINI_API_KEY` em `lain/.env`; nunca duplicar.
5. HUD sem autenticação: bind `127.0.0.1` reduz superfície.

Detalhes e controles em `docs/SECURITY.md`.
