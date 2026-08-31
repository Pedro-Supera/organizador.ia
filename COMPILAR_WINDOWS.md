# Compilação para Windows

## Requisitos
1. **Windows 10/11** (64-bit)
2. **Python 3.11+** instalado e no PATH
3. **Git** (opcional, para clonar o repositório)

## Passo a Passo

### 1. Preparar ambiente
```cmd
# Clonar ou copiar o projeto para Windows
git clone https://github.com/Pedro-Supera/organizador.ia.git
cd organizador.ia

# Criar e ativar ambiente virtual
python -m venv venv
venv\Scripts\activate

# Instalar dependências
pip install -r requirements.txt
pip install pyinstaller
```

### 2. Compilar o executável
```cmd
python construir_executavel.py --windows
```

O executável será gerado em `dist\OrganizadorInteligente.exe`.

### 3. Testar
```cmd
dist\OrganizadorInteligente.exe
```

## Observações Importantes

- **Tamanho esperado**: ~38-45 MB
- **Tempo de build**: ~2-5 minutos
- **Compatibilidade**: Windows 10/11 64-bit
- **O AppUserModelID** é aplicado automaticamente em Windows, garantindo o ícone correto na barra de tarefas.
- **Distribuição**: basta distribuir o arquivo `OrganizadorInteligente.exe` único.

## Alternativa: Build Automatizado
Se preferir automatizar, use o script PowerShell `build_windows.ps1` (incluído no projeto).
