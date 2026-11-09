# ADR-001: Adoção de Arquitetura Modular em Camadas

## Status
Aceito

## Contexto
O ULTRON precisa operar como uma plataforma conversacional extensível, permitindo a substituição de provedores de IA, persistência de dados, evolução de regras de personalidade e futuros agentes autônomos sem comprometer a estabilidade do código. Sistemas monolíticos fortemente acoplados a um único fornecedor de LLM falham ao tentar suportar múltiplos provedores e ambientes de teste locais.

## Decisão
Adotamos uma arquitetura modular inspirada em Clean Architecture e Ports and Adapters, segregando o sistema em 5 camadas explícitas:
1. `app.api`: adaptadores primários de entrada HTTP REST.
2. `app.core`: regras de aplicação e orquestração do fluxo de mensagens.
3. `app.intelligence`: contratos de IA (`LLMProvider`), adaptadores para provedores e mecanismo de prompts.
4. `app.database`: infraestrutura de persistência relacional com Repositories.
5. `app.models`: entidades e DTOs de dados imutáveis/validados.

## Consequências
### Positivas:
- Módulos desacoplados e testáveis isoladamente sem I/O real.
- Flexibilidade total para plugar novos provedores (OpenAI, Groq, Mistral, Ollama) sem tocar na camada de API ou Core.
- Baixo acoplamento entre regras de negócio e detalhes de bibliotecas externas.

### Negativas / Mitigações:
- Maior número inicial de arquivos e interfaces estruturadas em comparação a um script direto. Mitigado por uma estrutura de pastas intuitiva e padrões bem documentados.
