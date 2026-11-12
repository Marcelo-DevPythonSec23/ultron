# ULTRON 2.0 — INVESTIGAÇÃO E CORREÇÃO DEFINITIVA DO BACKEND DA INTERFACE

## CONTEXTO

Esta é a terceira tentativa de corrigir a comunicação entre a interface desktop e o backend.

A interface visual já está implementada e funcionando. NÃO reconstrua a interface, NÃO redesenhe os componentes e NÃO comece outra implementação.

O problema atual está na comunicação entre a interface, o orquestrador e o provider de IA.

A captura de tela comprova que o sistema continua apresentando:

`Jarvis [mock] (mock-model-v1): [Resposta Simulada ULTRON]`

Também existe o registro:

`Dashboard not running - remote unavailable`

Quero uma investigação técnica da execução REAL, não apenas uma revisão dos arquivos.

## FASE 1 — REPRODUZIR E RASTREAR

Execute a aplicação desktop e rastreie uma mensagem desde o momento em que o usuário pressiona Enter ou clica no botão de envio.

Identifique:

1. Qual função recebe a mensagem.
2. Qual callback da interface é executado.
3. Qual adaptador recebe a mensagem.
4. Se `OrchestratorBridge.process_text` é chamado.
5. Qual instância do Orchestrator está sendo utilizada.
6. Qual ModelRouter está sendo utilizado.
7. Qual provider é selecionado.
8. Qual modelo efetivamente recebe a requisição.
9. Qual resposta retorna ao backend.
10. Qual componente apresenta essa resposta na interface.

Registre os arquivos, funções e classes envolvidos em cada etapa.

Não presuma que a arquitetura documentada corresponde à execução atual. Verifique o código realmente executado.

## FASE 2 — LOCALIZAR A ORIGEM DO MOCK

Procure especificamente:

- `mock-model-v1`
- `MockProvider`
- `MockLLMProvider`
- `mock`
- `Resposta Simulada ULTRON`
- `Jarvis [mock]`
- `provider_id`
- `default_provider`
- `ModelRouter`
- `ProviderRegistry`

Descubra exatamente quem está selecionando o mock.

Investigue:

- Configuração padrão.
- Variáveis de ambiente.
- Bootstrap.
- Registro de providers.
- Injeção de dependências.
- Inicialização da interface.
- Fallback automático.
- Adaptadores.
- Configuração do ambiente de desenvolvimento.

Não remova o mock dos testes. Ele pode continuar existindo para testes e demonstrações explícitas.

O que precisa desaparecer é sua utilização involuntária na execução normal.

## FASE 3 — INTEGRAR NVIDIA DE VERDADE

Verifique se existe implementação real do provider NVIDIA.

Se não existir, implemente-a seguindo o contrato `LLMProvider` utilizado pelo núcleo Lain.

Configuração:

- Provider: NVIDIA
- Base URL: `https://integrate.api.nvidia.com/v1`
- Credencial: `NVIDIA_API_KEY`
- Modelo: identificador NVIDIA válido e configurável.

Não invente modelos.

Utilize a compatibilidade OpenAI quando suportada pelo endpoint e pelo modelo selecionado.

Não altere o núcleo original `lain/`.

Implemente a integração exclusivamente na camada do ULTRON 2.0, respeitando o contrato existente.

Verifique se o registro de providers do núcleo permite registrar o provider NVIDIA sem alterar arquivos originais.

Se não permitir, apresente a limitação técnica e implemente um adaptador compatível dentro do ULTRON 2.0.

## FASE 4 — CORRIGIR A INICIALIZAÇÃO

O provider NVIDIA deve ser selecionado como padrão na execução normal.

O comportamento esperado é:

`Desktop UI → Bridge → Orchestrator → NVIDIA Provider → API NVIDIA → Response → Desktop UI`

Se a credencial estiver ausente, informe o problema.

Se a API retornar erro, informe o problema.

Se houver HTTP 429, respeite o limite e o Retry-After.

NUNCA apresente uma resposta simulada como resposta real.

NUNCA declare o ULTRON conectado apenas porque a janela abriu.

## FASE 5 — DIAGNÓSTICO DE STATUS

Implemente ou corrija um diagnóstico de conexão que diferencie:

- Interface inicializada.
- Backend inicializado.
- Orquestrador inicializado.
- Provider configurado.
- Provider autenticado.
- API acessível.
- Última requisição bem-sucedida.

Não confunda `ULTRON ONLINE` com conexão comprovada à API.

O indicador de provider deve exibir o provider e o modelo realmente selecionados.

O indicador ONLINE só pode representar conexão com a API quando houver evidência de uma verificação bem-sucedida.

## FASE 6 — INVESTIGAR DASHBOARD

Investigue:

`Dashboard not running - remote unavailable`

Descubra:

- Quem gera essa mensagem.
- Qual endereço está sendo consultado.
- Se o dashboard é um serviço obrigatório.
- Se existe uma URL antiga ou incorreta.
- Se a interface está tentando conectar a uma instância remota desnecessária.
- Se o backend local já está disponível.

Não tente corrigir esse erro por tentativa e erro. Determine se ele está relacionado à comunicação com o backend principal.

## FASE 7 — TESTE REAL DE PONTA A PONTA

Depois das correções:

1. Inicialize a interface.
2. Confirme a inicialização do backend.
3. Confirme a seleção do provider NVIDIA.
4. Envie uma mensagem pela interface.
5. Verifique que `process_text` foi chamado.
6. Verifique que a requisição chegou à NVIDIA.
7. Verifique que a resposta retornou.
8. Verifique que a interface apresentou a resposta real.
9. Verifique que o histórico foi persistido.
10. Desconecte temporariamente a API e confirme que a interface apresenta erro, sem gerar uma resposta fictícia.

Faça uma chamada real somente se a credencial estiver configurada.

Não exponha credenciais em logs ou relatórios.

## FASE 8 — REGRAS DE EXECUÇÃO

- Não reconstruir a interface.
- Não substituir componentes visuais.
- Não criar outro orquestrador.
- Não criar outro histórico.
- Não criar outro banco.
- Não modificar `lain/`.
- Não modificar `Mark-LVI-main/`.
- Não apagar funcionalidades existentes.
- Não repetir comandos que já falharam sem analisar a causa.
- Não realizar requisições repetidas durante HTTP 429.
- Não instalar dependências desnecessárias.
- Não considerar testes com fake providers como comprovação de integração real.

Antes de modificar qualquer arquivo, apresente a causa identificada.

Depois, implemente a correção.

## FASE 9 — RELATÓRIO

Atualize:

`docs/qa/BACKEND_CONNECTION_ROOT_CAUSE.md`

Inclua:

- Causa raiz.
- Caminho real da mensagem.
- Local onde o mock era selecionado.
- Implementação NVIDIA.
- Arquivos modificados.
- Resultado dos testes.
- Evidência da chamada real.
- Problemas restantes.

## CRITÉRIO FINAL

A tarefa não está concluída até que eu possa abrir o ULTRON, enviar uma mensagem pela interface e receber uma resposta produzida pelo modelo NVIDIA através do backend real.

Não quero uma simulação, um protótipo ou uma demonstração.

Quero o sistema conectado.