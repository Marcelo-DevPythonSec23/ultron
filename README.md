# ULTRON 2.0 Integration Layer

This is a third, independent integration layer that keeps the original projects untouched:

- `lain/` remains the ULTRON core intelligence
- `Mark-LVI-main/` remains the voice + desktop runtime
- this folder provides the bridge and adapters that unify them without modifying either original project

## Goals

- keep the ULTRON orchestrator as the single source of truth for conversation state
- reuse Mark-LVI audio stacks via a VoiceRuntime adapter
- expose Mark-LVI actions as tool contracts for the ULTRON core
- support both text-only and voice-first execution

## Structure

```text
ultron-2.0/
├── README.md
├── requirements.txt
├── pyproject.toml
├── ultron_2_0/
│   ├── __init__.py
│   ├── voice_runtime.py
│   ├── tool_contracts.py
│   ├── tool_registry.py
│   ├── orchestrator_bridge.py
│   └── main.py
└── scripts/
```

## Runtime model

The integrated flow is:

```text
Microphone -> STT -> ULTRON orchestrator -> provider -> tool adapter -> Mark-LVI action -> result -> ULTRON -> TTS -> user
```

This layer does not replace the existing code. It provides the controlled integration boundary.
