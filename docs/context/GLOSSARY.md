# GLOSSARY — termos do ULTRON 2.0

| Termo | Significado no projeto |
|---|---|
| **ULTRON / lain** | Núcleo inteligente original em `lain/`: orquestrador, contexto, prompt, providers, SQLite. |
| **Mark-LVI** | Runtime operacional original em `Mark-LVI-main/`: actions, áudio, memória JSON, HUD Qt. |
| **ULTRON 2.0** | Produto em `ultron-2.0/` que integra os dois sem modificá-los. |
| **OrchestratorBridge** | Adaptador de interface; mantém o `conversation_id` da sessão e chama o núcleo. |
| **Orchestrator** | Classe do lain que executa o único ciclo de conversa. |
| **ProviderRegistry** | Autoridade de provedores do lain (`mock`, `gemini`). |
| **ToolCallingProvider** | Proxy de provider do 2.0 que adiciona tool calling por JSON. |
| **ToolGateway** | Camada que valida e executa ferramentas (allowlist, timeout, confirmação). |
| **ToolContract** | Contrato explícito de uma ferramenta (schema, permissões, timeout...). |
| **Subset curado** | Conjunto de actions do Mark-LVI aprovadas para uso (4). |
| **Working memory** | Estado efêmero da tarefa/sessão; não persistente. |
| **Memória episódica** | Eventos/sessões relevantes (ex.: `sessions` no JSON). |
| **Memória semântica** | Fatos/preferências estruturados (categorias do `memory_manager`). |
| **Memória procedural** | Procedimentos validados; `PLANNED` no 2.0. |
| **FactMemory** | Fachada do 2.0 sobre o `memory_manager` do Mark-LVI. |
| **long_term.json** | Arquivo de memória original do Mark-LVI; **nunca tocado**. |
| **ultron2.db** | Banco SQLite isolado do 2.0. |
| **STT** | Speech-to-text; no 2.0 via Gemini Live (só transcrição) ou lote. |
| **TTS** | Text-to-speech; Gemini ou voz do sistema. |
| **PCM** | Áudio linear 16-bit; taxas 16 kHz (entrada) e 24 kHz (saída Gemini). |
| **v1beta** | Versão da API Gemini que aceita `speechConfig` para TTS. |
| **HUD** | Interface web local (`web/`), tema ULTRON, sem CDN. |
| **MCP** | Model Context Protocol; integração `PLANNED`, não implementada. |
| **Model Router** | Seleção automática de provider/modelo; `PLANNED`, não existe. |
| **Dado não confiável** | Saída de ferramenta/página/arquivo: nunca vira instrução. |
| **Gate de confirmação** | Exigência de confirmação explícita para ação destrutiva. |
| **Originais** | `lain/` e `Mark-LVI-main/`; imutáveis no escopo do 2.0. |
