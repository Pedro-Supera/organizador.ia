# Segurança e privacidade

## Escopo

O projeto processa arquivos locais e pode enviar texto para um provedor externo de IA quando a funcionalidade de resumos está habilitada.

## Boas práticas

- Nunca versione `GROQ_API_KEY` ou outras credenciais.
- Não abra issues públicas contendo documentos reais, PII, tokens ou segredos.
- Revise arquivos sensíveis antes de enviá-los a serviços externos.
- A anonimização baseada em padrões reduz exposição, mas não garante remoção de todos os dados pessoais.

## Reportando vulnerabilidades

Não publique credenciais, dados pessoais ou detalhes exploráveis em uma issue pública. Para problemas de segurança, use um canal privado disponível no perfil do mantenedor e forneça passos mínimos para reprodução.

## Áreas críticas

Mudanças envolvendo movimentação de arquivos, anonimização, chamadas à IA, cache ou MCP devem ser avaliadas quanto a privacidade, integridade dos arquivos e exposição de dados.
