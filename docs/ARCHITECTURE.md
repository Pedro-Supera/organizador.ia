# Arquitetura e fluxo de trabalho

## Responsabilidades

- `organizador.py`: domínio, classificação, extração, anonimização, cache, IA, CLI e relatórios.
- `app.py`: GUI CustomTkinter e adaptação dos eventos do domínio para a interface.
- `mcp_organizador.py`: ferramentas MCP para contexto, artefatos e coordenação entre agentes.
- `tests/test_organizador.py`: regressão do domínio e contratos públicos.
- `construir_executavel.py`, `OrganizadorInteligente.spec` e `installer.iss`: empacotamento e instalação.
- `WORKFLOW_MCP.md`: protocolo de hand-off entre agentes.

## Organização de pastas

O projeto mantém uma estrutura plana de propósito. O núcleo ainda cabe em um módulo, e extrair `organizador/` ou vários frames de `gui/` agora aumentaria imports e risco de PyInstaller sem reduzir complexidade real.

```text
.
├── app.py
├── organizador.py
├── mcp_organizador.py
├── tests/
├── docs/
├── build/                  # gerado, ignorado pelo Git
├── dist/                   # gerado, ignorado pelo Git
└── .mcp_workspace/         # mailbox local, ignorado pelo Git
```

## Ciclo cooperativo

1. O Copilot transforma a solicitação atual em um hand-off usando `solicitar_revisao`.
2. O Cline lê mensagens destinadas a `cline`, revisa ou implementa apenas o escopo recebido e executa os comandos de validação.
3. O Cline publica uma resposta para `copilot` com achados, testes e riscos.
4. O Copilot lê a resposta, corrige ou integra o trabalho, executa a validação final e só então cria commit/push.

O MCP coordena mensagens, mas não executa agentes automaticamente. O cliente Cline precisa estar ativo e consultar o mailbox; quando isso não ocorrer, o hand-off permanece pendente e nenhuma publicação deve ser presumida.

## Guardrails

- Não incluir `.env`, tokens ou chaves no mailbox, commits ou relatórios.
- Não fazer `git push --force`.
- Não publicar sem `pytest tests/test_organizador.py -q`, `git diff --check` e revisão do estado remoto.
- Não modificar comportamento de negócio durante refatorações de GUI sem teste correspondente.