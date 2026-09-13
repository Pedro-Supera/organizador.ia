# Contribuindo

## Ambiente

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pytest tests/ -q
```

## Antes de abrir uma PR

- Explique o problema e a solução.
- Mantenha mudanças pequenas quando possível.
- Adicione ou atualize testes para comportamento novo.
- Não inclua chaves de API, dados pessoais ou arquivos reais de usuários.
- Verifique que `pytest tests/ -q` passa.
- Se alterar o fluxo de arquivos, teste também `--dry-run`.

## Áreas sensíveis

Mudanças em anonimização, chamadas à IA, movimentação de arquivos, cache ou ferramentas MCP devem ser acompanhadas de testes e de uma explicação do impacto de segurança/privacidade.

## Pull request

Inclua no mínimo:

- problema resolvido;
- comportamento novo ou alterado;
- testes executados;
- possíveis impactos de compatibilidade.
