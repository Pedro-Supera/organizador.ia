# Script PowerShell para build automatico no Windows
# Uso: .\build_windows.ps1

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Build do Organizador Inteligente (Windows)" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# Verifica Python
try {
    $pythonVersion = python --version
    Write-Host "[OK] Python encontrado: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "[ERRO] Python nao encontrado. Instale Python 3.11+ primeiro." -ForegroundColor Red
    exit 1
}

# Cria/ativa venv
if (-not (Test-Path "venv")) {
    Write-Host "[INFO] Criando ambiente virtual..." -ForegroundColor Yellow
    python -m venv venv
}

Write-Host "[INFO] Ativando ambiente virtual..." -ForegroundColor Yellow
& "venv\Scripts\Activate.ps1"

# Instala dependencias
Write-Host "[INFO] Instalando dependencias..." -ForegroundColor Yellow
pip install --upgrade pip | Out-Null
pip install -r requirements.txt
pip install pyinstaller

# Limpa builds anteriores
if (Test-Path "build") { Remove-Item -Recurse -Force "build" }
if (Test-Path "dist") { Remove-Item -Recurse -Force "dist" }
if (Test-Path "OrganizadorInteligente.spec") { Remove-Item "OrganizadorInteligente.spec" }

# Compila
Write-Host "[INFO] Compilando executavel..." -ForegroundColor Yellow
python construir_executavel.py --windows

# Resultado
$exe = "dist\OrganizadorInteligente.exe"
if (Test-Path $exe) {
    $size = [math]::Round((Get-Item $exe).Length / 1MB, 2)
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "[OK] Build concluido com sucesso!" -ForegroundColor Green
    Write-Host "[OK] Arquivo: $exe" -ForegroundColor Green
    Write-Host "[OK] Tamanho: $size MB" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
} else {
    Write-Host "[ERRO] Executavel nao foi gerado." -ForegroundColor Red
    exit 1
}
