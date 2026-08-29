#!/usr/bin/env python3
"""Script de automação de build para empacotar o Organizador Inteligente via PyInstaller."""

import subprocess
import sys
from pathlib import Path

import customtkinter


def obter_caminho_customtkinter() -> Path:
    """Localiza o caminho de instalação da biblioteca customtkinter."""
    caminho_modulo = Path(customtkinter.__file__).resolve()
    caminho_pasta = caminho_modulo.parent
    return caminho_pasta


def construir_comando_pyinstaller() -> list[str]:
    """Monta o comando do PyInstaller com as flags necessárias."""
    caminho_customtkinter = obter_caminho_customtkinter()
    
    # Validar que o caminho existe
    if not caminho_customtkinter.exists():
        raise FileNotFoundError(f"Pasta customtkinter não encontrada: {caminho_customtkinter}")
    
    # Mapear customtkinter para o pacote (--add-data "origem:destino")
    # No Linux/Mac: /path/to/customtkinter:customtkinter
    # No Windows: C:\path\to\customtkinter;customtkinter
    separador = ";" if sys.platform == "win32" else ":"
    add_data_flag = f"{caminho_customtkinter}{separador}customtkinter"
    
    comando = [
        "pyinstaller",
        "--noconsole",
        "--onefile",
        "--name", "OrganizadorInteligente",
        "--add-data", add_data_flag,
        "app.py",
    ]
    
    return comando


def executar_build() -> int:
    """Executa o comando PyInstaller e retorna o código de saída."""
    try:
        comando = construir_comando_pyinstaller()
        print(f"Executando: {' '.join(comando)}")
        print()
        
        resultado = subprocess.run(comando, check=True)
        print()
        print("✓ Build completado com sucesso!")
        print(f"  Executável gerado em: ./dist/OrganizadorInteligente")
        return resultado.returncode
        
    except FileNotFoundError as erro:
        print(f"Erro: {erro}")
        return 1
    except subprocess.CalledProcessError as erro:
        print(f"Erro durante build: {erro}")
        return erro.returncode
    except Exception as erro:
        print(f"Erro inesperado: {erro}")
        return 1


def main() -> int:
    """Ponto de entrada do script de build."""
    caminho_script = Path(__file__).resolve().parent
    
    # Verificar se estamos no diretório correto
    if not (caminho_script / "app.py").exists():
        print("Erro: app.py não encontrado no diretório correto.")
        print(f"Executar a partir de: {caminho_script}")
        return 1
    
    print("=" * 60)
    print("Organizador Inteligente - Build Automation")
    print("=" * 60)
    print()
    
    # Exibir informações do build
    caminho_customtkinter = obter_caminho_customtkinter()
    print(f"customtkinter localizado em: {caminho_customtkinter}")
    print(f"Ponto de entrada: app.py")
    print(f"Nome do executável: OrganizadorInteligente")
    print()
    
    # Executar o build
    return executar_build()


if __name__ == "__main__":
    raise SystemExit(main())
