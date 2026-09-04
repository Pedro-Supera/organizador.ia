# Workflow de cooperação via MCP — PROTOCOLO OTIMIZADO

## Princípios fundamentais

1. **Canal indireto**: Cline e Copilot se comunicam apenas via mailbox `.mcp_workspace/messages.json`. Não há conversa direta entre modelos.
2. **Tokens-first**: Cada mensagem deve ser densa mas concisa. O Copilot tem limite de tokens; mensagens devem caber em uma resposta.
3. **Idempotência**: Marcar como lida mais de uma vez não causa efeitos colaterais.
4. **Deduplicação automática**: O servidor MCP ignora IDs duplicados na gravação.
5. **Recuperação automática**: Mailbox corrompido é reconstruído como lista vazia válida.

## Agentes

| Identificador | Papel |
|---|---|
| `cline` | Implementação, exploração local, revisão inicial |
| `copilot` | Segunda revisão, integração, validação final |
| `todos` | Broadcast — todos os agentes recebem |

## Ciclo de trabalho otimizado

```
Copilot                 Mailbox                 Cline
   |                       |                      |
   |--publicar_mensagem--->|                      |
   |   [handoff]          |                      |
   |                       |                      |
   |                  [ler_mensagens]            |
   |                       |<-----cliente MCP------|
   |                       |                      |
   |                       |         |--implementa/valida--|
   |                       |         |--pytest + git diff--|
   |                       |                      |
   |<--publicar_resposta---|                      |
   |   [resultado]         |                      |
   |                       |                      |
   |                       |<--marcar_como_lida---|
   |                       |                      |
```

### Etapas detalhadas

1. **Copilot** gera hand-off via `solicitar_revisao(escopo, arquivos, criterios, comandos)` ou `publicar_mensagem`.
2. **Cline** (via cliente MCP): `ler_mensagens(destinatario="cline")`.
3. **Cline** executa APENAS o escopo solicitado + comandos de validação.
4. **Cline** publica resposta com: `achados`, `testes`, `riscos`, `recomendacao`.
5. **Cline** marca mensagem original como lida.
6. **Copilot** integra resultado e só então cria commit/push.

## Formato da mensagem de hand-off (Copilot→Cline)

```
Objetivo: [uma frase — o que fazer]
Arquivos: [lista separada por vírgulas — escopo fechado]
Critérios: [o que define sucesso]
Validação: [comando pytest/compilação]
Restrições: [não force-push, não .env, etc.]
```

## Formato da resposta (Cline→Copilot)

```
Ação: [implementado/revisado/descartado]
Testes: [N/M passando + tempo]
Achados: [lista curta — bugs, melhorias, observações]
Riscos: [pendências conhecidas — nunca omitir]
Recomendação: [próximo passo concreto]
```

## Guardrails (obrigatórios)

- ❌ Não inclua `.env`, tokens, chaves em nenhuma mensagem.
- ❌ Não faça `git push --force`.
- ❌ Não publique resposta sem antes executar `pytest tests/ -q`.
- ❌ Não modifique comportamento de negócio sem teste correspondente.
- ❌ Não assuma que o agente remoto está ativo — mailbox pode ter mensagens pendentes.

## Validações antes de commit/push

```bash
# 1. Testes passando
source venv/bin/activate && python -m pytest tests/ -q

# 2. Compilação sem erro
python -m py_compile organizador.py app.py mcp_organizador.py

# 3. Sem conflitos remotos
git fetch origin && git status

# 4. Diff limpo
git diff --check
```

## Otimização de tokens

- **Assunto**: máx 60 caracteres (`[handoff]`, `[resultado]`, `[aviso]`).
- **Conteúdo**: máx 2000 caracteres — se exceder, divida em duas mensagens.
- **Priorize**: ação concreta > descrição > contexto.
- Use formato de tabela para listas curtas.

## Ferramentas MCP disponíveis

| Ferramenta | Descrição |
|---|---|
| `publicar_mensagem(remetente, destinatario, assunto, conteudo)` | Publica mensagem com UUID único |
| `ler_mensagens(destinatario, apenas_nao_lidas=True)` | Lê filtrado por destinatário, ordenado por mais recente |
| `marcar_mensagem_lida(mensagem_id)` | Idempotente |
| `solicitar_revisao(escopo, arquivos, criterios, comandos)` | Helper do Copilot para criar hand-offs padronizados |
| `ler_contexto()` | Lê `contexto.txt` |
| `atualizar_contexto(novo_conteudo)` | Substitui `contexto.txt` |
| `listar_arquivos_dist()` | Lista artefatos em `dist/` |
