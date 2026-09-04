# Workflow de cooperação via MCP

Este protocolo permite cooperação indireta entre o Cline e outros agentes no mesmo workspace. Não existe conversa direta entre os modelos: as mensagens são persistidas pelo servidor MCP em `.mcp_workspace/messages.json`.

## Agentes

Use identificadores estáveis:

- `cline`: implementação, exploração local e revisão inicial;
- `copilot`: segunda revisão, integração e validação;
- `todos`: avisos destinados a todos os agentes.

## Ciclo de trabalho

1. O agente que identifica uma tarefa publica uma mensagem com `publicar_mensagem`.
2. O agente destinatário consulta `ler_mensagens` usando seu identificador.
3. O destinatário executa a parte solicitada no workspace e publica um resumo para o remetente.
4. O destinatário marca a mensagem original como lida com `marcar_mensagem_lida`.
5. Antes de commit ou push, o agente deve executar testes, verificar `git diff` e avisar sobre conflitos ou mudanças remotas.

Para o fluxo padrão Copilot -> Cline, prefira `solicitar_revisao(escopo, arquivos, criterios, comandos)`. Essa ferramenta monta o hand-off no formato esperado e deixa a mensagem pendente para o cliente Cline.

## Formato recomendado

Assunto: `[handoff] escopo curto`

Conteúdo:

```text
Objetivo:
Arquivos permitidos:
Critérios de aceite:
Comandos de validação:
Resultado esperado:
```

Não inclua chaves, tokens ou conteúdo de `.env`. O mailbox é um canal de coordenação local, não um mecanismo de autenticação ou autorização.

O disparo automático do Cline depende do cliente Cline estar ativo e consultar o mailbox. O MCP não consegue iniciar ou conversar diretamente com outro modelo.

## Worker responsivo

Para monitorar continuamente as mensagens destinadas ao Cline:

```bash
source venv/bin/activate
python mcp_responder.py --agent cline
```

Esse modo imprime cada hand-off e não o marca como lido. Para entregar a mensagem a um adaptador local que converse com um cliente, use `--handler`:

```bash
python mcp_responder.py --agent cline --handler "python meu_adaptador_cline.py"
```

O adaptador recebe uma mensagem JSON pela entrada padrão. O worker só marca a mensagem como lida quando o comando termina com código `0`; falhas permanecem pendentes para retry. O worker não inicia o modelo Cline diretamente e não deve receber segredos na linha de comando.

## Exemplo

```text
publicar_mensagem(
  remetente="cline",
  destinatario="copilot",
  assunto="[handoff] revisar progresso da GUI",
  conteudo="Revise app.py e execute pytest; não faça push sem relatar conflitos."
)
```