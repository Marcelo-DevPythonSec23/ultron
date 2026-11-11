# CONTEXT_INDEX — mapa do conhecimento

Ponto de entrada da documentação do ULTRON 2.0. Carregue apenas o que a tarefa
exige (ver §5 de `CONTEXT.md`).

## Nível 1 — contexto essencial (sempre)

| Caminho | Assunto | Descrição | Autoridade | Atualização | Relacionados |
|---|---|---|---|---|---|
| `AGENTS.md` (raiz) | Requisitos | Mega prompt da integração | **máxima** | estável | `ultron-2.0/AGENTS.md` |
| `PROJECT_CONTEXT.md` | Visão global | Identidade, origem, arquitetura, estado, restrições | **máxima** | 2026-11-10 | `docs/context/*` |
| `docs/context/CONTEXT_INDEX.md` | Índice | Este mapa | **máxima** | 2026-11-10 | todos |
| `ultron-2.0/README.md` | Uso | Instalação, comandos, funcionalidades reais | alta | 2026-11-10 | `docs/TESTING.md` |

## Nível 2 — contexto arquitetural

| Caminho | Assunto | Descrição | Autoridade | Atualização | Relacionados |
|---|---|---|---|---|---|
| `docs/context/ARCHITECTURE_CONTEXT.md` | Arquitetura | Resumo + apontadores para a arquitetura real | alta | 2026-11-10 | `docs/ARCHITECTURE.md` |
| `docs/ARCHITECTURE.md` | Arquitetura | Fonte detalhada implementada | **máxima** | 2026-11-10 | `INTEGRATION_MAP.md` |
| `docs/context/MODULE_MAP.md` | Módulos | Onde fica cada responsabilidade | alta | 2026-11-10 | `DEPENDENCY_MAP.md` |
| `docs/context/DEPENDENCY_MAP.md` | Dependências | Quem importa quem, regras | alta | 2026-11-10 | `MODULE_MAP.md` |
| `docs/context/TECHNICAL_DECISIONS.md` | ADRs | Decisões e consequências | **máxima** para decisões | 2026-11-10 | `INTEGRATION_AUDIT.md` |
| `docs/INTEGRATION_AUDIT.md` | Auditoria | Evidência original e riscos | **máxima** | 2026-11-10 | todos |
| `docs/context/DEVELOPMENT_STATE.md` | Estado | O que está implementado/parcial/pendente | alta | 2026-11-10 | `TESTING.md` |

## Nível 3 — contexto especializado

| Caminho | Assunto | Quando consultar |
|---|---|---|
| `docs/VOICE_PIPELINE.md` | Voz | STT, TTS, áudio, microfone, falhas |
| `docs/context/agents/VOICE_AGENT.md` | Voz (papel) | Antes de alterar áudio |
| `docs/TOOLS.md` | Ferramentas | Contratos, gateway, tool calling |
| `docs/context/agents/INTEGRATION_AGENT.md` | Integração | Ações Mark-LVI, adaptadores |
| `docs/SECURITY.md` | Segurança | Permissões, validação, confirmação |
| `docs/context/agents/SECURITY_AGENT.md` | Segurança (papel) | Antes de expor execução |
| `docs/TESTING.md` | Testes | Antes/depois de qualquer mudança |
| `docs/context/agents/QA_AGENT.md` | QA (papel) | Validação e regressão |
| `docs/context/agents/ARCHITECT_AGENT.md` | Arquitetura (papel) | Mudanças estruturais |
| `docs/context/agents/BACKEND_AGENT.md` | Núcleo/backend | Orquestrador, providers, banco |
| `docs/context/KNOWN_LIMITATIONS.md` | Limitações | Antes de prometer funcionalidade |
| `docs/context/GLOSSARY.md` | Glossário | Termos ambíguos |
| `docs/memory/*` | Memória | Persistência, tipos, recuperação, segurança, ciclo de vida, API e testes |
| `docs/memory/MEMORY_ARCHITECTURE.md` | Memória (arquitetura) | Antes de alterar o motor de memória |
| `docs/memory/MEMORY_API.md` | Memória (contratos) | Antes de usar/estender `MemoryEngine` |
| `docs/INTEGRATION_MAP.md` | Mapa de origem | O que veio de onde |

## Nível 4 — histórico

| Caminho | Estado | Uso |
|---|---|---|
| `docs/archive/INTEGRATION_AUDIT.draft-v1.md` | substituído | referência histórica apenas |
| `lain/docs/**` | histórico do núcleo | decisões originais; checar contra código |
| `Mark-LVI-main/readme.md` | manual original | comportamento do runtime original |
| `Mark-LVI-main/AGENTS.md` | regras originais | restrições de threads/TOOL |

## Regras de carregamento

1. Sempre: `AGENTS.md` → `PROJECT_CONTEXT.md` → este índice.
2. Tarefa de arquitetura: nível 2 inteiro.
3. Tarefa de voz/tools/segurança/testes: só o documento especializado + agente.
4. Histórico apenas sob demanda; nunca carregar tudo.
5. Se um documento contradizer o código, **registre** e siga o código até
   decisão explícita (ver `CONTEXT_AUDIT.md` §5).

## Documentos que NÃO existem (não inventar)

- `ultron-2.0/docs/` — a documentação vive na raiz `docs/`.
- Não há ADRs do 2.0 fora de `TECHNICAL_DECISIONS.md`.
- `docs/memory/` existe e está indexado acima; não criar documentos além dos 9
  listados sem implementação correspondente.
