# Orquestrador de IAs

Este projeto usa um MCP local para que Codex, Cline e Copilot trabalhem sobre
o mesmo contexto, sem compartilhar credenciais, contas ou limites de uso.

## Limite técnico importante

Nenhum agente deve tentar medir ou burlar créditos de outra plataforma. Os
limites de Codex, Cline e Copilot pertencem às suas contas e não são uma API
confiável deste projeto. Quando um limite for atingido, registre manualmente o
estado como `limited` ou `unavailable`; o próximo agente disponível assume
a tarefa.

## Fluxo de trabalho

1. Abra uma tarefa com `criar_tarefa_ia`.
2. Marque o agente atual com `definir_disponibilidade_ia`.
3. O agente chama `assumir_proxima_tarefa_ia`.
4. Antes de alterar código, ele lê `ler_contexto`, executa testes e registra
   decisões relevantes com `registrar_decisao_ia`.
5. Ao terminar, ele usa `concluir_tarefa_ia`. O status é gravado em
   `.ai-team-state.json` e sincronizado no final de `contexto.txt`.

## Papéis sugeridos

- **Codex:** arquitetura, revisão profunda, testes e documentação.
- **Cline:** execução contínua no IDE, pequenas correções e acompanhamento da
  fila MCP.
- **Copilot:** sugestões no editor, autocompletar e revisão pontual.

Todos podem trocar de papel. A regra é registrar a decisão e o resultado para
que o próximo agente continue sem repetir trabalho.

## Configuração

O Cline deve iniciar `mcp_organizador.py` por stdio com o Python do ambiente
virtual do projeto. No Codex, adicione o mesmo comando como servidor MCP local.
O Copilot pode não oferecer consumo MCP em todas as edições; nesse caso, ele
continua pelo workspace compartilhado, `contexto.txt` e
`.ai-team-state.json`.

Nunca coloque tokens, chaves de API, logs com segredos ou arquivos `.env` no
estado da equipe.
