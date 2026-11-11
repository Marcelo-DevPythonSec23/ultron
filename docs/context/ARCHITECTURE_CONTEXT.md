# ARCHITECTURE_CONTEXT — resumo e apontadores

> Documento de **contexto**, não substitui `docs/ARCHITECTURE.md` (fonte
> detalhada). Aqui estão o fluxo, a hierarquia de autoridade e as regras que um
> agente precisa respeitar antes de mexer no sistema.

## 1. Hierarquia de autoridade (fato de código)

```text
Usuário
  │
  ▼
Interface (CLI · voz · HUD)
  │
  ▼
OrchestratorBridge          ← só estado de interface (conversation_id)
  │
  ▼
Orchestrator do lain        ← ÚNICO ciclo de conversa/contexto/persistência
  ├── ChatService (SQLite do 2.0)
  ├── ContextManager + PromptEngine
  └── ProviderRegistry
        └── ToolCallingProvider
              └── ToolGateway
                    └── actions do Mark-LVI
```

Nada abaixo do `Orchestrator` decide conversa. O Mark-LVI **não** responde ao
usuário diretamente.

## 2. Fluxo de um turno de texto

```text
process_text(msg)
  → runtime.chat_sync(msg)                 [loop dedicado]
    → Orchestrator.process_chat(ChatRequest)
      1. provider/modelo
      2. get_or_create_conversation
      3. registra mensagem do usuário
      4. carrega histórico recente
      5. ContextManager.build_context
      6. PromptEngine.assemble_request
      7. provider.generate_response
           └─ ToolCallingProvider: detecta JSON de tool, chama ToolGateway,
              devolve [TOOL_RESULT...] e repete (até 4 rodadas)
      8. registra resposta do assistente
      9. retorna ChatResponse
```

## 3. Fluxo de voz

`Microfone → Gemini Live (só transcrição) → VoicePipeline.handle_transcript →
OrchestratorBridge.process_text → (mesmo fluxo acima) → TTS → alto-falante`.
Detalhes e falhas em `docs/VOICE_PIPELINE.md`.

## 4. Regras arquiteturais invioláveis

1. **Um orquestrador.** Não criar segundo ciclo de decisão/histórico.
2. **Uma memória sob o ULTRON.** Não duplicar `FactMemory`/long_term.
3. **Ferramentas só pelo gateway.** Modelo propõe; gateway valida e executa.
4. **Resultado externo é dado, não instrução.**
5. **Providers atrás do `ProviderRegistry`.** Não acoplar o núcleo a um SDK.
6. **Sem shell/eval/exec genérico** como ferramenta.
7. **Originais intactos:** `lain/` e `Mark-LVI-main/` nunca são editados.

## 5. Onde implementar cada tipo de mudança

| Mudança | Onde |
|---|---|
| Nova ferramenta segura | `ultron_2_0/marklvi_actions.py` ou módulo próprio + `ToolContract` no gateway |
| Novo provider | `provider` que implemente `LLMProvider` + registro no `ProviderRegistry` |
| Nova interface | novo adaptador que chame `OrchestratorBridge.process_text` |
| Memória | `ultron_2_0/memory_tools.py` (nunca duplicar o manager) |
| Áudio/voz | `ultron_2_0/voice/` |
| HUD | `ultron_2_0/web/` |
| Config/caminhos | `ultron_2_0/bootstrap.py` |
| Decisão arquitetural | `docs/context/TECHNICAL_DECISIONS.md` |

## 6. Dependências proibidas (ciclos)

- `core` **não** importa `web` nem `voice`.
- `voice` e `web` importam `orchestrator_bridge`, nunca o contrário.
- `memory_tools` não importa `web`/`voice`.
- `tool_gateway` não importa providers.

Ver `DEPENDENCY_MAP.md`.
