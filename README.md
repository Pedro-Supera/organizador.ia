# Organizador Inteligente

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-passing-brightgreen.svg)](tests/test_organizador.py)
[![Build: PyInstaller](https://img.shields.io/badge/build-PyInstaller-orange.svg)](construir_executavel.py)
[![Version](https://img.shields.io/badge/version-1.1.0-blue.svg)](https://github.com/Pedro-Supera/organizador.ia)

**Organize arquivos automaticamente com IA, cache local e proteção de dados sensíveis.**

Aplicação em Python que classifica arquivos por categoria, extrai texto de formatos comuns e gera resumos em português via API Groq. Prioriza privacidade (anonimização de PII antes de qualquer chamada à IA) e eficiência (cache local por SHA-256).

**Repositório:** [github.com/Pedro-Supera/organizador.ia](https://github.com/Pedro-Supera/organizador.ia)

---

## Recursos

- Organização automática por categoria (PDFs, imagens, documentos, planilhas, compactados e outros)
- **3 modos na GUI:** uma pasta, várias pastas ou **arquivos principais** (Desktop, Downloads, Documentos, Imagens…)
- Resumo antes de executar + progresso X/Y
- Resumos em português com Groq (streaming, retries e backoff)
- Anonimização de CPF, CNPJ, RG, e-mail, telefone, cartão, tokens e datas antes do envio à IA
- Cache local inteligente (`SHA-256 + modelo`) para evitar chamadas repetidas
- Relatório consolidado em Markdown e resumos individuais
- Interface gráfica com CustomTkinter e CLI completa
- Executável via PyInstaller (Linux local; Windows via GitHub Actions)
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

## Arquitetura

O projeto separa a interface da lógica principal para que a mesma funcionalidade possa ser usada pela GUI e pela CLI.

```text
                    ┌──────────────────────┐
                    │      app.py (GUI)    │
                    │     CustomTkinter    │
                    └──────────┬───────────┘
                               │
                               ▼
┌──────────────┐      ┌──────────────────────┐      ┌─────────────────┐
│ CLI          │─────▶│    organizador.py    │─────▶│ Groq API / IA   │
│ organizador  │      │ núcleo da aplicação  │      │ (opcional)      │
└──────────────┘      └──────────┬───────────┘      └─────────────────┘
                                  │
                 ┌────────────────┼────────────────┐
                 ▼                ▼                ▼
          Classificação     Extração de texto   Cache local
                 │                │              SHA-256
                 └────────────────┼────────────────┘
                                  ▼
                         Organização / Relatórios

                 mcp_organizador.py
                         │
                         ▼
                  Integração MCP
```

### Fluxo principal

1. O usuário escolhe uma pasta pela GUI ou informa um caminho pela CLI.
2. O núcleo encontra os arquivos elegíveis e classifica cada um por categoria.
3. O texto é extraído quando o formato é suportado.
4. Se a IA estiver habilitada, os dados identificáveis são anonimizados localmente antes da chamada externa.
5. O cache baseado em SHA-256 + modelo evita gerar novamente resumos já processados.
6. Os arquivos são organizados e os resultados são registrados em relatórios.

A arquitetura atual é intencionalmente simples: `organizador.py` concentra o núcleo, `app.py` cuida da GUI e `mcp_organizador.py` expõe a integração MCP. Refatorações maiores só devem acontecer quando trouxerem ganho real de manutenção, testes ou segurança.

---

## Como a IA é usada

A IA é **opcional** e serve para gerar resumos curtos em português a partir do texto extraído dos documentos.

```text
Arquivo → extração local → anonimização local → Groq API → resumo → cache local
```

O aplicativo não precisa de IA para organizar os arquivos. Com `--no-ai`, a organização funciona sem chamadas ao provedor externo.

Para reduzir chamadas repetidas, o projeto mantém um cache local associado ao conteúdo do arquivo por SHA-256 e ao modelo utilizado. A integração também possui streaming e tentativas com backoff para lidar com falhas transitórias.

**Importante:** anonimização baseada em padrões não garante que todos os dados sensíveis sejam removidos. Documentos confidenciais devem ser revisados e, quando necessário, processados com a IA desativada.

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

### 2. Configurar a chave Groq (opcional)

1. Crie uma chave em [console.groq.com/keys](https://console.groq.com/keys)
2. Crie um arquivo `.env` na raiz:

```env
GROQ_API_KEY=sua_chave_aqui
```

Sem a chave, a organização continua funcionando; só os resumos com IA ficam desativados.

### 3. Executar

```bash
# Interface gráfica (recomendado)
python app.py

# Linha de comando
python organizador.py ~/Downloads
python organizador.py ~/Downloads --dry-run
python organizador.py ~/Downloads --no-ai
python organizador.py ~/Downloads --max-files 20
```

Na GUI você pode escolher:

| Modo | Uso |
|------|-----|
| **Uma pasta** | Seleciona uma pasta só |
| **Várias pastas** | Monta uma lista e organiza tudo de uma vez |
| **Principais** | Desktop, Downloads, Documents, Pictures (e similares se existirem) |

> O modo **Principais** usa só pastas do usuário (`Path.home()`). **Não** varre o disco inteiro nem pastas de sistema.

### Resultado típico

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

---

## Executável (sem instalar Python)

### Linux (na sua máquina)

```bash
source venv/bin/activate
python construir_executavel.py --linux
./dist/OrganizadorInteligente
```

### Windows (GitHub Actions — recomendado)

1. Aba **Actions** → workflow **Gerar Executavel Windows**
2. **Run workflow** (branch `main`)
3. Baixe o artifact **OrganizadorInteligente-Windows**
4. Extraia e use o `OrganizadorInteligente.exe`

Também é possível compilar em um PC Windows:

```bat
python construir_executavel.py --windows
```

Guia extra: [`COMPILAR_WINDOWS.md`](COMPILAR_WINDOWS.md).

> PyInstaller gera binário da plataforma em que roda. Não há cross-compile Linux → Windows no script local.

---

## Testes e CI

Execute localmente:

```bash
source venv/bin/activate
pytest tests/ -q
```

A suíte cobre classificação, extração, PII, cache, IA, dry-run, cancelamento, pastas principais, mailbox MCP e PyInstaller.

O GitHub Actions executa os testes automaticamente em `push` para `main` e em Pull Requests para `main`. O workflow usa permissões mínimas de leitura do conteúdo do repositório.

---

## Segurança e privacidade

Antes de enviar texto à API, o app anonimiza localmente:

| Dado | Marcador |
|------|----------|
| CPF / CNPJ / RG | `[CPF_PROTEGIDO]` etc. |
| E-mail / telefone | `[EMAIL_PROTEGIDO]` / `[TELEFONE_PROTEGIDO]` |
| Cartão / tokens | `[CARTAO_PROTEGIDO]` / `[SEGREDO_PROTEGIDO]` |
| Datas | `[DATA_PROTEGIDA]` |

- Chave Groq só em `.env` (no `.gitignore`)
- Não varre raiz do disco no modo Principais
- Não apaga arquivos: apenas organiza (move) com dry-run disponível
- A IA é opcional; `--no-ai` impede o uso do provedor externo
- A anonimização é uma camada de proteção, não uma garantia absoluta de remoção de PII

Consulte a [política de segurança](SECURITY.md) para boas práticas e relato responsável de vulnerabilidades.

---

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
├── SECURITY.md
├── .github/workflows/build.yml
├── .github/workflows/tests.yml
└── tests/
```

---

## CLI

| Opção | Descrição |
|-------|-----------|
| `caminho` | Pasta a organizar |
| `-d`, `--dry-run` | Simula sem mover |
| `--no-ai` | Sem resumos |
| `--model` | Modelo Groq |
| `--max-files` | Limite de arquivos |

---

## Roadmap

- [x] Organização por categorias
- [x] GUI e CLI
- [x] Resumos opcionais com IA
- [x] Anonimização de dados sensíveis
- [x] Cache local por SHA-256
- [x] Testes automatizados
- [x] CI com GitHub Actions
- [x] Build Windows via GitHub Actions
- [x] Integração MCP
- [ ] Release oficial com executável Windows
- [ ] Melhorar cobertura de testes de segurança
- [ ] Testar distribuição em mais versões do Windows
- [ ] Melhorar observabilidade e diagnósticos de falhas

---

## Contribuindo

1. Fork / clone
2. Branch: `git checkout -b feature/minha-melhoria`
3. `pytest tests/ -q`
4. Pull Request

---

## Licença

[MIT](LICENSE)

---

## Changelog

### v1.1.0

- GUI: modos Uma pasta / Várias / Principais
- Progresso e resumo pré-execução
- Melhorias visuais e feedback de estado
- Helper `resolver_pastas_principais` + testes
- MCP mailbox (dedup, ordenação, validação) + testes

### v1.0.0

- Organização por categoria, Groq, PII, cache, GUI/CLI, PyInstaller, MCP base

---

Desenvolvido por [Pedro-Supera](https://github.com/Pedro-Supera) · Python 3.11+
