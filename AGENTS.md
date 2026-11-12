# TAREFA: Corrigir a estrutura Git e publicar corretamente o ULTRON 2.0

Você deve atuar como um engenheiro Git experiente, responsável por corrigir a estrutura dos repositórios e preparar a publicação do projeto ULTRON no GitHub.

**Não execute um push até que todas as verificações de segurança e integridade sejam concluídas.**

## 1. Contexto da arquitetura

Repositório principal:
- Caminho: `~/projetos/ultron`
- Remote: `https://github.com/Marcelo-DevPythonSec23/ultron.git`
- Branch: `master`

Estrutura:
- `lain/`: primeira versão do ULTRON. Não deve ser publicada.
- `Mark-LVI-main/`: projeto original externo. Não deve ser publicado.
- `ultron-2.0/`: versão atual do produto. Deve ser publicada integralmente.

O diretório `ultron-2.0/` possui seu próprio repositório Git, com histórico independente.

A branch que contém a integração atual do produto é:
`integration/etapa-0-fundacao`

O objetivo é incorporar o conteúdo de `ultron-2.0/` ao repositório principal como **Git Subtree**, preservando o histórico de commits sempre que tecnicamente possível.

## 2. Estado conhecido

O repositório principal apresenta atualmente:

```text
MM .gitignore
Am lain
Am ultron-2.0

160000 ... lain
160000 ... ultron-2.0
```

Isso indica que `lain` e `ultron-2.0` foram adicionados ao índice como gitlinks, e não como diretórios normais.

O repositório interno apresenta duas modificações ainda não commitadas:

```text
M ultron_2_0/interface/ultron_adapter.py
M ultron_2_0/interface/ultron_ui.py
```

Essas modificações devem ser preservadas integralmente.

## 3. Regras obrigatórias de segurança

Antes de modificar qualquer coisa:

1. Inspecione o estado atual dos dois repositórios.
2. Confirme as branches, remotes, commits e arquivos modificados.
3. Verifique se existe backup acessível.
4. Identifique alterações staged, unstaged e arquivos untracked.
5. Verifique se existem credenciais ou arquivos sensíveis que possam ser publicados.

**PROIBIDO:**
- Executar `git reset --hard`.
- Executar `git clean -fd` ou variantes.
- Apagar os diretórios `lain/`, `Mark-LVI-main/` ou `ultron-2.0/`.
- Descartar alterações locais.
- Sobrescrever arquivos sem backup.
- Publicar `.env`, `api_keys.json`, tokens, senhas ou credenciais.
- Publicar a pasta `.venv/`.
- Transformar o projeto em submodule.
- Executar `git push --force` ou `--force-with-lease`.
- Alterar os repositórios originais `lain/` e `Mark-LVI-main/`.

Se encontrar credenciais expostas ou arquivos sensíveis rastreados pelo Git, interrompa a publicação e informe o problema.

## 4. Corrigir o repositório principal

O `.gitignore` do repositório principal deve:

- Ignorar `/lain/`.
- Ignorar `/Mark-LVI-main/`.
- NÃO ignorar `/ultron-2.0/`.
- Continuar ignorando `.venv/`, `__pycache__/`, arquivos `.pyc`, `.env`, `api_keys.json`, bancos de dados e outros artefatos locais.

Remova os gitlinks de `lain` e `ultron-2.0` somente do índice do repositório principal, sem apagar seus diretórios ou seus respectivos históricos.

Use operações equivalentes a:

```bash
git rm --cached -f -- lain ultron-2.0
```

Confirme que os diretórios continuam presentes.

## 5. Preservar as modificações do ULTRON 2.0

No repositório interno:

1. Inspecione o diff completo de `ultron_adapter.py` e `ultron_ui.py`.
2. Preserve as duas alterações.
3. Verifique se são alterações válidas e se não contêm credenciais.
4. Se estiverem prontas e seguras, crie um commit descritivo na branch `integration/etapa-0-fundacao`.
5. Não descarte nem reverta nenhuma modificação.

Se houver dúvida sobre a intenção de alguma alteração, interrompa e apresente o diff para aprovação.

## 6. Importar usando Git Subtree

Importe o repositório interno para o repositório principal no caminho:

`ultron-2.0/`

Utilize Git Subtree, mantendo o histórico da branch:

`integration/etapa-0-fundacao`

Antes da importação:

- Confirme que o prefixo `ultron-2.0/` está livre no índice principal.
- Preserve o diretório original e o `.git` interno.
- Utilize uma estratégia segura para disponibilizar o repositório interno ao comando `git subtree add`.
- Não faça uma cópia que perca o histórico.
- Não transforme o diretório em submodule.

Depois da importação, verifique se os arquivos aparecem como arquivos normais no repositório principal, e não como gitlinks de modo `160000`.

## 7. Auditoria antes da publicação

Execute as verificações:

```bash
git status --short
git ls-files --stage
git ls-files | grep -E '(^|/)(\.env|api_keys\.json|\.venv/)'
git ls-files | grep -E '(^|/)__pycache__(/|$)|\.pyc$'
```

Verifique também:

- Nenhum arquivo de `lain/` está rastreado.
- Nenhum arquivo de `Mark-LVI-main/` está rastreado.
- O conteúdo de `ultron-2.0/` está rastreado normalmente.
- Não existem gitlinks inesperados.
- Nenhuma credencial foi incluída.
- Nenhum ambiente virtual foi incluído.
- O histórico do ULTRON 2.0 foi preservado.
- Os arquivos de documentação e README do repositório principal continuam presentes.

Faça uma revisão do diff completo antes de criar o commit principal.

## 8. Commit e publicação

Somente depois de todas as verificações:

1. Apresente um resumo do que será publicado.
2. Crie um commit descritivo no repositório principal.
3. Confirme que a branch de destino é `master`.
4. Confirme que o remote `origin` aponta para o repositório correto.
5. Verifique se o histórico remoto não possui alterações que precisem ser integradas.
6. Não sobrescreva commits remotos.

**Não execute o push automaticamente.**

Pare e apresente o resultado final, incluindo:
- Estrutura Git corrigida.
- Estratégia de importação utilizada.
- Commits preservados.
- Arquivos incluídos e excluídos.
- Resultado das verificações de segurança.
- Commit criado.
- Situação da branch e do remote.

Aguarde minha autorização explícita antes de executar `git push origin master`.

## 9. Comportamento esperado

Trabalhe como um engenheiro responsável pela integridade do projeto, não como um agente que executa comandos cegamente.

Inspecione antes de agir, faça alterações pequenas e verificáveis, preserve o histórico e registre qualquer problema encontrado.

Se alguma etapa não puder ser executada com segurança, interrompa o processo e explique exatamente o motivo, sem improvisar soluções destrutivas.