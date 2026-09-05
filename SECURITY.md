# Segurança

## Escopo

O Organizador.IA pode ler arquivos escolhidos pelo usuário e, quando a IA está habilitada, enviar texto extraído e anonimizado para a API da Groq.

A proteção de dados é uma prioridade do projeto, mas a anonimização é baseada em padrões e **não garante a remoção de todos os dados sensíveis**. Antes de usar a IA com documentos reais, revise o conteúdo e considere `--no-ai` quando o arquivo for confidencial.

## Boas práticas para usuários

- Nunca coloque `GROQ_API_KEY` no código-fonte, README, issues ou commits.
- Mantenha o `.env` fora do Git; ele já é ignorado pelo `.gitignore`.
- Use `--dry-run` antes de organizar uma pasta importante.
- Faça backup de arquivos importantes antes de executar a organização.
- Evite usar a função de resumos com documentos que não possam ser enviados a um serviço externo.

## Relato de vulnerabilidades

Se você encontrar uma vulnerabilidade de segurança, **não publique credenciais, dados pessoais ou detalhes exploráveis em uma issue pública**.

Prefira entrar em contato diretamente com o mantenedor pelo perfil do GitHub do projeto e forneça:

1. descrição do problema;
2. versão/commit afetado;
3. passos mínimos para reproduzir;
4. impacto esperado;
5. uma sugestão de correção, se tiver.

O objetivo é corrigir problemas de segurança antes que detalhes sensíveis sejam divulgados publicamente.

## Segredos

Se uma chave da Groq for exposta, considere-a comprometida: revogue/rotacione a chave imediatamente e só depois investigue o histórico do repositório.

## Status

Este documento descreve as práticas de segurança atuais e será atualizado conforme o projeto evoluir.
