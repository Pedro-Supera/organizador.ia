# Organizador Inteligente

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Tests: 31/31](https://img.shields.io/badge/tests-31%2F31-brightgreen.svg)](tests/test_organizador.py)
[![Build: PyInstaller](https://img.shields.io/badge/build-PyInstaller-orange.svg)](construir_executavel.py)

**Organize seus arquivos automaticamente com IA e proteção de dados sensíveis.**

Organizador Inteligente é uma aplicação que classifica arquivos por categoria, extrai conteúdo textual e gera resumos em português usando a API Groq. O projeto prioriza segurança (anonimização de PII, permissões restritas) e eficiência (cache local com SHA-256).

## ✨ Recursos Principais

- 🗂️ **Organização automática** de arquivos por categoria (PDFs, imagens, documentos, planilhas, compactados)
- 🤖 **Geração de resumos com IA** em português usando Groq
- 🔒 **Proteção de dados sensíveis** com anonimização de CPF, CNPJ, email, cartão, etc.
- ⚡ **Cache inteligente local** baseado em SHA-256 para evitar chamadas duplicadas à API
- 📊 **Relatórios em Markdown** com estatísticas e métricas operacionais
- 🎨 **Interface gráfica** intuitiva com CustomTkinter
- 📦 **Executável independente** empacotado com PyInstaller (sem dependência de Python)
- ✅ **Testes automatizados** com 31 testes de regressão e cobertura completa
- ⚙️ **CLI e GUI** para flexibilidade de uso

### Tecnologias

| Tecnologia | Versão | Propósito |
|---|---|---|
| **Python** | 3.11+ | Linguagem principal |
| **CustomTkinter** | Última | Interface gráfica moderna |
| **Groq API** | v1 | Geração de resumos com IA |
| **PyInstaller** | 6.22+ | Empacotamento de executável |
| **Pytest** | 9.1+ | Testes automatizados |
| **Rich** | Última | Formatação de console |

## 🚀 Instalação e Uso via Executável

### Windows, macOS ou Linux (sem Python)

**Opção 1: Baixar executável pré-compilado**
1. Acesse a seção [Releases](../../releases) do repositório
2. Faça download do `OrganizadorInteligente` para seu sistema operacional
3. Execute diretamente:
   ```bash
   # Linux/macOS
   ./OrganizadorInteligente
   
   # Windows
   OrganizadorInteligente.exe
   ```

**Opção 2: Compilar localmente**
```bash
# Clone o repositório
git clone https://github.com/seu-usuario/organizador-ia.git
cd organizador-ia

# Ative o ambiente virtual
python -m venv venv
source venv/bin/activate  # ou venv\Scripts\activate no Windows

# Instale dependências
pip install -r requirements.txt

# Execute o build
python construir_executavel.py

# Use o executável gerado
./dist/OrganizadorInteligente
```

### Interface Gráfica

1. **Selecione a pasta** que deseja organizar
2. **Configure a chave Groq** (obtém em https://console.groq.com/keys)
3. **Escolha o modelo** de IA (padrão: `qwen/qwen3.6-27b`)
4. **Ative/desative** geração de resumos
5. **Clique em "Iniciar"** para organizar

### Linha de Comando

```bash
# Organizar pasta com resumos
./OrganizadorInteligente ~/Downloads

# Simular operação sem mover arquivos
./OrganizadorInteligente ~/Downloads --dry-run

# Desativar geração de resumos
./OrganizadorInteligente ~/Downloads --no-ai

# Limitar quantidade de arquivos
./OrganizadorInteligente ~/Downloads --max-files 10

# Especificar modelo de IA
./OrganizadorInteligente ~/Downloads --model "mixtral-8x7b-32768"
```

### Resultado da Execução

Após a organização, a pasta conterá:
```
~/Downloads/
├── documentos/          # .doc, .docx, .txt, .rtf, .pptx, .html
├── pdfs/                # .pdf
├── imagens/             # .jpg, .png, .webp, .gif, .bmp
├── planilhas/           # .xls, .xlsx, .csv
├── compactados/         # .zip, .rar, .7z, .tar, .gz
├── outros/              # Extensões não categorizadas
├── resumos/             # Arquivos Markdown com resumos gerados
└── 00_RELATORIO_ORGANIZACAO.md  # Relatório consolidado
```

## 🛠️ Desenvolvimento e Compilação

### Requisitos

- Python 3.11+
- pip (gerenciador de pacotes)
- Virtual environment
- Git

### Instalação do Ambiente

```bash
# Clone o repositório
git clone https://github.com/seu-usuario/organizador-ia.git
cd organizador-ia

# Crie e ative o virtual environment
python -m venv venv
source venv/bin/activate  # Linux/macOS
# ou
venv\Scripts\activate  # Windows

# Instale as dependências
pip install -r requirements.txt
```

### Execução da Aplicação

```bash
# Interface gráfica
python app.py

# CLI
python organizador.py ~/Downloads
```

### Testes Automatizados

```bash
# Executar todos os testes
pytest tests/test_organizador.py -v

# Teste específico de PyInstaller
pytest tests/test_organizador.py::test_caminho_base_suporta_pyinstaller -v

# Modo verbose com cobertura
pytest tests/test_organizador.py -q
```

**Status atual:** ✅ 31/31 testes passando

### Compilação para Executável

```bash
# Ativar ambiente virtual
source venv/bin/activate

# Executar build
python construir_executavel.py

# Resultado em
./dist/OrganizadorInteligente
```

O script `construir_executavel.py`:
- Localiza `customtkinter` no venv ativo
- Monta comando PyInstaller com flags apropriadas
- Cria executável único (`--onefile`)
- Oculta console (`--noconsole`)
- Mapeia bibliotecas graficamente dependentes

**Tempo de compilação:** ~2-3 minutos em máquina típica

## 🔒 Segurança e Privacidade

### Anonimização de Dados Sensíveis

Antes de enviar texto para a IA, a aplicação mascara automaticamente:
- **CPF:** `123.456.789-00` → `[CPF_PROTEGIDO]`
- **CNPJ:** `12.345.678/0001-99` → `[CNPJ_PROTEGIDO]`
- **RG:** `12.345.678-X` → `[RG_PROTEGIDO]`
- **Email:** `user@example.com` → `[EMAIL_PROTEGIDO]`
- **Telefone:** `(11) 99999-1234` → `[TELEFONE_PROTEGIDO]`
- **Cartão:** `4111 1111 1111 1111` → `[CARTAO_PROTEGIDO]`
- **Segredos/Tokens:** Chaves API, senhas → `[SEGREDO_PROTEGIDO]`
- **Data:** `12/03/1998` → `[DATA_PROTEGIDA]`

### Proteção de Chave da API

- Chave da Groq é armazenada **localmente** com permissões restritas (`0o600`)
- **Nunca é hardcoded** no código
- Carregada dinamicamente de `.env` ou `~/.config/organizador-ia/.env`
- Validada antes de cada chamada à API

### Cache Local

- Resumos são cacheados **localmente** com SHA-256 do conteúdo
- Evita reprocessamento desnecessário e economia de tokens
- Chave de cache: `{sha256}_{modelo}`

## 📊 Performance e Eficiência

### Cache Inteligente

```
Cache Hits:  X/Y (XX%)
Cache Misses: Y/X (XX%)
Caracteres salvos: Z
Tokens salvos: W
Tempo economizado: ~0.35s por hit
```

### Limitações Intencionais

- Máximo 50.000 caracteres por arquivo processado
- Streaming de resposta para feedback em tempo real
- Retry com backoff exponencial em falhas da API
- Timeout e tratamento de rate limit da Groq

## 📁 Estrutura do Projeto

```
organizador-ia/
├── app.py                          # Interface gráfica (CustomTkinter)
├── organizador.py                  # Núcleo de lógica e organização
├── construir_executavel.py         # Script de automação PyInstaller
├── contexto.txt                    # Documentação operativa
├── requirements.txt                # Dependências Python
├── .gitignore                      # Arquivos a ignorar no Git
├── README.md                       # Este arquivo
├── tests/
│   └── test_organizador.py        # Suite de testes (31 testes)
├── dist/                          # (Gerado) Executável compilado
├── build/                         # (Gerado) Artefatos intermediários
└── OrganizadorInteligente.spec    # (Gerado) Configuração PyInstaller
```

## 🧪 Testes e Validação

### Cobertura de Testes

- ✅ Organização e classificação de arquivos
- ✅ Extração de texto (PDF, TXT, DOCX, PPTX, HTML, CSV)
- ✅ Anonimização de PII
- ✅ Cache local com SHA-256
- ✅ Geração de resumo com streaming
- ✅ Retry em falhas temporárias
- ✅ Cancelamento de operação
- ✅ Relatórios em Markdown
- ✅ PyInstaller com `sys._MEIPASS`
- ✅ Compatibilidade geral

### Comando para Testar

```bash
# Todos os testes
pytest tests/test_organizador.py -q

# Com verbose
pytest tests/test_organizador.py -v

# Teste específico
pytest tests/test_organizador.py::test_organizador -v

# Com cobertura (se coverage instalado)
pytest --cov=organizador tests/test_organizador.py
```

**Resultado:** ✅ 31/31 PASSED (1.15s)

## 🤝 Contribuindo

1. Fork o repositório
2. Crie uma branch para sua feature (`git checkout -b feature/MinhaFeature`)
3. Commit suas mudanças (`git commit -am 'Adiciona MinhaFeature'`)
4. Push para a branch (`git push origin feature/MinhaFeature`)
5. Abra um Pull Request

### Padrões de Código

- Usar type hints (Python 3.11+)
- Seguir PEP 8
- Adicionar testes para novas funcionalidades
- Documentar funções com docstrings
- Não hardcoding de secrets

## 📝 Licença

Este projeto está licenciado sob a [MIT License](LICENSE).

## 🙋 Suporte

- 📧 Email: seu-email@example.com
- 🐛 Issues: [Abrir uma issue](../../issues)
- 💬 Discussions: [Abrir discussão](../../discussions)

## 📌 Changelog

### v1.0.0 (2026-08-29)
- ✅ Lançamento inicial
- ✅ Organização automática de arquivos
- ✅ Geração de resumos com Groq
- ✅ Proteção de PII com anonimização
- ✅ Cache local inteligente
- ✅ Interface gráfica com CustomTkinter
- ✅ Executável empacotado com PyInstaller
- ✅ 31 testes de cobertura completa

---

**Desenvolvido com ❤️ em Python 3.11+**
