# Organizador Inteligente

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-passing-brightgreen.svg)](tests/test_organizador.py)
[![Build: PyInstaller](https://img.shields.io/badge/build-PyInstaller-orange.svg)](construir_executavel.py)
[![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)](https://github.com/Pedro-Supera/organizador.ia)

**Organize arquivos automaticamente com IA, cache local e proteção de dados sensíveis.**

Aplicação em Python que classifica arquivos por categoria, extrai texto de formatos comuns e gera resumos em português via API Groq. Prioriza privacidade (anonimização de PII antes de qualquer chamada à IA) e eficiência (cache local por SHA-256).

**Repositório:** [github.com/Pedro-Supera/organizador.ia](https://github.com/Pedro-Supera/organizador.ia)

---

## Recursos

- Organização automática por categoria (PDFs, imagens, documentos, planilhas, compactados e outros)
- Resumos em português com Groq (streaming, retries e backoff)
- Anonimização de CPF, CNPJ, RG, e-mail, telefone, cartão, tokens e datas antes do envio à IA
- Cache local inteligente (`SHA-256 + modelo`) para evitar chamadas repetidas
- Relatório consolidado em Markdown e resumos individuais
- Interface gráfica com CustomTkinter e CLI completa
- Executável independente via PyInstaller (~38 MB no Linux)
- Instalador Windows (Inno Setup) e scripts de build multiplataforma
- Servidor MCP para integração com agentes (Cline e similares)
- Suite de testes automatizados com pytest

### Tecnologias

| Tecnologia | Uso |
|---|---|
| Python 3.11+ | Linguagem principal |
| CustomTkinter | Interface gráfica |
| Groq API | Resumos com IA |
| pypdf, python-docx, python-pptx | Extração de texto |
| Rich | Logs no terminal |
| PyInstaller | Empacotamento |
| pytest | Testes |
| MCP 2.x | Ferramentas para agentes |

---

## Início rápido

### 1. Clonar e instalar

```bash
git clone https://github.com/Pedro-Supera/organizador.ia.git
cd organizador.ia

python3 -m venv venv
source venv/bin/activate          # Linux/macOS
# venv\Scripts\activate           # Windows

pip install -r requirements.txt
```

### 2. Configurar a chave Groq (opcional, só se quiser resumos com IA)

1. Crie uma chave em [console.groq.com/keys](https://console.groq.com/keys)
2. Crie um arquivo `.env` na raiz do projeto:

```env
GROQ_API_KEY=sua_chave_aqui
```

Sem a chave, a organização de arquivos continua funcionando; apenas os resumos com IA ficam desativados.

### 3. Executar

```bash
# Interface gráfica
python app.py

# Linha de comando
python organizador.py ~/Downloads

# Simulação (não move arquivos)
python organizador.py ~/Downloads --dry-run

# Sem IA
python organizador.py ~/Downloads --no-ai

# Limitar quantidade de arquivos
python organizador.py ~/Downloads --max-files 20

# Modelo específico
python organizador.py ~/Downloads --model "qwen/qwen3.6-27b"
```

### Resultado típico

```text
~/Downloads/
├── documentos/
├── pdfs/
├── imagens/
├── planilhas/
├── compactados/
├── outros/
├── resumos/                      # resumos em Markdown
└── 00_RELATORIO_ORGANIZACAO.md   # relatório consolidado
```

---

## Executável (sem instalar Python)

### Linux

```bash
source venv/bin/activate
python construir_executavel.py --linux
./dist/OrganizadorInteligente
```

### Windows

Veja o guia completo em [`COMPILAR_WINDOWS.md`](COMPILAR_WINDOWS.md).

Resumo:

```powershell
# PowerShell (preferencialmente como Administrador)
.\build_windows.ps1
```

Ou:

```bat
python construir_executavel.py --windows
```

O instalador Inno Setup (`installer.iss`) pode ser gerado automaticamente se o `ISCC.exe` estiver disponível.

### macOS

```bash
source venv/bin/activate
python construir_executavel.py --mac
```

> O PyInstaller gera binário nativo da plataforma em que o build roda. Não use flags de outra SO na mesma máquina.

---

## Testes

```bash
source venv/bin/activate
pytest tests/test_organizador.py -v
```

Cobertura principal:

- classificação por extensão e destinos seguros
- extração de PDF, TXT, DOCX, PPTX, HTML e CSV
- anonimização de dados sensíveis
- cache local (SHA-256 + modelo)
- streaming e retry da IA
- dry-run, cancelamento e limite de arquivos
- relatórios Markdown
- compatibilidade com PyInstaller (`sys._MEIPASS`)

Validação recente da release v1.0.0: suite de regressão passando.

---

## Segurança e privacidade

Antes de qualquer envio à API, o texto passa por anonimização local:

| Dado | Marcador |
|------|----------|
| CPF | `[CPF_PROTEGIDO]` |
| CNPJ | `[CNPJ_PROTEGIDO]` |
| RG | `[RG_PROTEGIDO]` |
| E-mail | `[EMAIL_PROTEGIDO]` |
| Telefone | `[TELEFONE_PROTEGIDO]` |
| Cartão | `[CARTAO_PROTEGIDO]` |
| Tokens/senhas | `[SEGREDO_PROTEGIDO]` |
| Datas | `[DATA_PROTEGIDA]` |

Outras práticas:

- chave da API só via `.env` / ambiente (nunca hardcoded)
- permissões restritas ao gravar a chave
- cache e relatórios ficam na pasta processada
- arquivos internos do projeto são ignorados na organização

---

## Estrutura do projeto

```text
organizador.ia/
├── app.py                    # Interface gráfica (CustomTkinter)
├── organizador.py            # Núcleo: organização, IA, cache, relatórios
├── mcp_organizador.py        # Servidor MCP (contexto e distribuição)
├── construir_executavel.py   # Build PyInstaller multiplataforma
├── build_windows.ps1         # Automação de build no Windows
├── installer.iss             # Instalador Inno Setup (Windows)
├── COMPILAR_WINDOWS.md       # Guia de compilação Windows
├── contexto.txt              # Documentação operativa interna
├── requirements.txt
├── README.md
├── LICENSE
├── .gitignore
├── .github/workflows/        # CI de build
└── tests/
    └── test_organizador.py
```

---

## Integração MCP (agentes)

O arquivo `mcp_organizador.py` expõe um servidor MCP local (stdio) com ferramentas como:

- `ler_contexto`
- `atualizar_contexto`
- `listar_arquivos_dist`

Útil para agentes (ex.: Cline) trabalharem no workspace sem embutir credenciais na configuração.

---

## CLI — opções

| Opção | Descrição |
|-------|-----------|
| `caminho` | Pasta a organizar |
| `-d`, `--dry-run` | Simula sem mover arquivos nem gravar resumos |
| `--no-ai` | Desativa geração de resumos |
| `--model` | Modelo Groq (padrão: `qwen/qwen3.6-27b`) |
| `--max-files` | Limita quantos arquivos processar |

---

## Contribuindo

1. Faça um fork (se o repositório estiver público) ou clone
2. Crie uma branch: `git checkout -b feature/minha-melhoria`
3. Rode os testes antes do commit
4. Abra um Pull Request com descrição clara

Padrões:

- type hints (Python 3.11+)
- PEP 8
- testes para comportamento novo
- zero secrets no código

---

## Licença

Distribuído sob a licença [MIT](LICENSE).

---

## Changelog

### v1.0.0 (2026-09-04)

- Organização automática por categoria
- Resumos com Groq (streaming + retry)
- Anonimização de PII
- Cache local por conteúdo e modelo
- GUI (CustomTkinter) e CLI
- Empacotamento PyInstaller (Linux validado)
- Scripts e instalador Windows (Inno Setup)
- Servidor MCP para agentes
- Suite de testes de regressão

---

Desenvolvido por [Pedro-Supera](https://github.com/Pedro-Supera) · Python 3.11+
