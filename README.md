# Organizador Inteligente

![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)
![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)
![Tests](https://img.shields.io/badge/tests-passing-brightgreen.svg)
![Build: PyInstaller](https://img.shields.io/badge/build-PyInstaller-orange.svg)
![Version](https://img.shields.io/badge/version-1.1.0-blue.svg)

> **Organize arquivos automaticamente com IA, cache local e proteção de dados sensíveis.**

Aplicação desktop/CLI em Python que classifica arquivos por categoria, extrai texto de formatos comuns e gera resumos em português com a API Groq. O projeto combina **automação de arquivos, IA, privacidade, cache, testes, CLI, GUI, empacotamento e MCP**.

A ideia central é prática: automatizar uma tarefa real sem transformar o programa em uma caixa-preta. A organização pode ser simulada com `dry-run`, dados sensíveis são anonimizados localmente antes da chamada à IA e resultados repetidos podem ser atendidos pelo cache.

**Status:** `v1.1.0` · **Python:** `>=3.11` · **Licença:** MIT

## Como funciona

```text
Arquivos do usuário
       │
       ▼
 Classificação ───────► PDF / imagem / documento / planilha / etc.
       │
       ├──────────────► mover / organizar
       │
       ▼
 Extração de texto
       │
       ▼
 Anonimização local ──► CPF / CNPJ / RG / e-mail / telefone / etc.
       │
       ├──── cache ───► resultado já conhecido
       │
       ▼
 Groq API ────────────► resumo em português
       │
       ▼
 Relatórios Markdown
```

## Principais recursos

- Organização automática por categoria.
- **3 modos na GUI:** uma pasta, várias pastas ou pastas principais do usuário.
- Resumo pré-execução e progresso X/Y.
- Resumos em português com streaming, retries e backoff.
- Anonimização de dados potencialmente sensíveis antes da chamada à IA.
- Cache local baseado em `SHA-256 + modelo`.
- Relatório consolidado em Markdown e resumos individuais.
- GUI com CustomTkinter e CLI completa.
- Executável com PyInstaller: Linux local e Windows via GitHub Actions.
- Servidor MCP para integração com agentes compatíveis.
- Suite de testes automatizados com pytest.

## Engenharia por trás do projeto

| Área | Implementação |
|---|---|
| Linguagem | Python 3.11+ |
| GUI | CustomTkinter |
| IA | Groq API |
| Extração | pypdf, python-docx, python-pptx |
| CLI | argparse + Rich |
| Cache | SHA-256 + modelo |
| Privacidade | sanitização/anonimização local |
| Testes | pytest |
| Empacotamento | PyInstaller |
| Integração com agentes | MCP 2.x |
| CI/CD | GitHub Actions |

## Início rápido

### Instalar

```bash
git clone https://github.com/Pedro-Supera/organizador.ia.git
cd organizador.ia

python3 -m venv venv
source venv/bin/activate          # Linux/macOS
# venv\Scripts\activate           # Windows

pip install -r requirements.txt
```

### Configurar IA (opcional)

Crie `.env` na raiz:

```env
GROQ_API_KEY=sua_chave_aqui
```

Sem a chave, a organização de arquivos continua disponível; somente os recursos que dependem da IA ficam desativados.

**Nunca coloque a chave diretamente no código ou em commits.**

### Executar

```bash
# GUI
python app.py

# CLI
python organizador.py ~/Downloads
python organizador.py ~/Downloads --dry-run
python organizador.py ~/Downloads --no-ai
python organizador.py ~/Downloads --max-files 20
```

## Segurança e privacidade

A privacidade foi tratada como parte do fluxo de dados, não apenas como documentação.

Antes de enviar texto à API, o aplicativo pode substituir informações identificáveis por marcadores locais:

| Dado | Marcador |
|---|---|
| CPF / CNPJ / RG | `[CPF_PROTEGIDO]` etc. |
| E-mail | `[EMAIL_PROTEGIDO]` |
| Telefone | `[TELEFONE_PROTEGIDO]` |
| Cartão | `[CARTAO_PROTEGIDO]` |
| Tokens/segredos | `[SEGREDO_PROTEGIDO]` |
| Datas | `[DATA_PROTEGIDA]` |

Outras medidas:

- chave Groq fica em `.env` e não deve ser versionada;
- o modo **Principais** trabalha com pastas do usuário e não varre a raiz do disco;
- `--dry-run` permite conferir a operação antes de mover arquivos;
- o programa organiza/move arquivos, mas não usa exclusão destrutiva como mecanismo normal de organização.

> **Nota:** anonimização baseada em padrões não é garantia absoluta de remoção de todos os dados pessoais. Arquivos que exigem privacidade elevada devem ser revisados antes do processamento por serviços externos.

## Resultado típico

```text
~/Downloads/
├── documentos/
├── pdfs/
├── imagens/
├── planilhas/
├── compactados/
├── outros/
├── resumos/
└── 00_RELATORIO_ORGANIZACAO.md
```

## GUI

| Modo | Uso |
|---|---|
| **Uma pasta** | Seleciona uma pasta e organiza seu conteúdo |
| **Várias pastas** | Processa uma lista de pastas selecionadas |
| **Principais** | Localiza Desktop, Downloads, Documents, Pictures e equivalentes existentes |

O modo **Principais** usa `Path.home()` como referência e não significa "varrer o computador inteiro".

## Executável

### Linux

```bash
source venv/bin/activate
python construir_executavel.py --linux
./dist/OrganizadorInteligente
```

### Windows via GitHub Actions

1. Abra **Actions**.
2. Execute **Gerar Executavel Windows** manualmente.
3. Baixe o artifact **OrganizadorInteligente-Windows**.
4. Extraia e execute `OrganizadorInteligente.exe`.

Guia: [`COMPILAR_WINDOWS.md`](COMPILAR_WINDOWS.md).

> PyInstaller gera o binário para a plataforma em que o build é executado. O script local não faz cross-compile Linux → Windows.

## Testes

```bash
source venv/bin/activate
pytest tests/ -q
```

A suite cobre áreas como classificação, extração, proteção de dados, cache, IA, `dry-run`, cancelamento, pastas principais, MCP e empacotamento.

## MCP

O projeto também disponibiliza integração MCP para que clientes compatíveis possam utilizar funcionalidades do organizador de forma programática.

Documentação de uso: [`WORKFLOW_MCP.md`](WORKFLOW_MCP.md).

## Estrutura

```text
organizador.ia/
├── app.py
├── organizador.py
├── mcp_organizador.py
├── construir_executavel.py
├── build_windows.ps1
├── installer.iss
├── COMPILAR_WINDOWS.md
├── WORKFLOW_MCP.md
├── contexto.txt
├── requirements.txt
├── LICENSE
├── .github/workflows/build.yml
└── tests/
```

## CLI

| Opção | Descrição |
|---|---|
| `caminho` | Pasta a organizar |
| `-d`, `--dry-run` | Simula sem mover |
| `--no-ai` | Desativa resumos com IA |
| `--model` | Define o modelo Groq |
| `--max-files` | Limita a quantidade de arquivos |

## Roadmap

- [x] Organização por categorias
- [x] GUI + CLI
- [x] Resumos com IA
- [x] Anonimização local de PII
- [x] Cache por conteúdo/modelo
- [x] `dry-run`
- [x] PyInstaller
- [x] GitHub Actions
- [x] MCP
- [ ] Melhorar cobertura e observabilidade
- [ ] Evoluir integrações MCP com ferramentas adicionais
- [ ] Melhorar experiência de instalação/distribuição

## Contribuindo

Consulte [`CONTRIBUTING.md`](CONTRIBUTING.md).

## Licença

[MIT](LICENSE)

---

Desenvolvido por [Pedro-Supera](https://github.com/Pedro-Supera) como projeto de estudo e construção de software.
