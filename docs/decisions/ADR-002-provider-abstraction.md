# ADR-002: Abstração de Provedores de LLM e Normalização de Erros

## Status
Aceito

## Contexto
O ecossistema de LLMs possui APIs divergentes em formatos de payload, tratamento de contexto, nomes de parâmetros (ex: `temperature`, `max_output_tokens` vs `max_tokens`) e exceções retornadas (códigos HTTP, quotas, erros de credenciais). O ULTRON necessita suportar múltiplos provedores (inicialmente Google Gemini via `google-genai` e mocks para testes) com capacidade de expansão para OpenAI, Groq, Mistral e Ollama.

## Decisão
1. Definir uma classe abstrata `LLMProvider` (ABC) em `app/intelligence/providers/base.py` com contrato assíncrono:
   - `generate(request: LLMRequest) -> LLMResponse`
   - `health_check() -> bool`
2. Criar uma hierarquia de exceções canônicas de domínio:
   - `LLMException` (base)
   - `ProviderAuthenticationError`
   - `ProviderRateLimitError`
   - `ProviderUnavailableError`
   - `ProviderInvalidRequestError`
3. Cada adaptador de provedor (`GeminiProvider`, `MockProvider`) é responsável por interceptar exceções nativas de seu SDK e convertê-las para as exceções canônicas do ULTRON.
4. Implementar um `ProviderRegistry` para carregamento e resolução dinâmica de instâncias de provedores com base em identificador de string.

## Consequências
### Positivas:
- O orquestrador nunca lida com exceções específicas de fornecedores.
- Facilidade de mockar testes automatizados sem consumir cota real de API.
- Facilidade de alternar entre modelos e fornecedores por requisição ou configuração de ambiente.

### Negativas / Mitigações:
- Necessidade de mapear novos recursos proprietários que surjam em SDKs específicos para o modelo canônico. Mitigado permitindo passar metadados adicionais em `raw_metadata`.
