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

## Exemplo

```text
publicar_mensagem(
  remetente="cline",
  destinatario="copilot",
  assunto="[handoff] revisar progresso da GUI",
  conteudo="Revise app.py e execute pytest; não faça push sem relatar conflitos."
)
```