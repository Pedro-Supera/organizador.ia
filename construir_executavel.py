import subprocess
import sys
import os
import customtkinter

def build(platform_target=None):
    """Compila o executavel para a plataforma alvo.

    Args:
        platform_target: 'windows', 'linux', 'mac' ou None (plataforma atual).
    """
    ctk_path = os.path.dirname(customtkinter.__file__)

    entry_point = "app.py"
    exe_name = "OrganizadorInteligente"

    # O separador do --add-data e diferente entre Windows (;) e Linux/Mac (:)
    sep = ";" if os.name == "nt" else ":"

    # Adiciona extensao .exe quando compilar no Windows
    target = platform_target or ("windows" if os.name == "nt" else "linux")
    if target == "windows":
        exe_name = "OrganizadorInteligente.exe"
        sep = ";"

    cmd = [
        "pyinstaller",
        "--noconsole",
        "--onefile",
        f"--name={exe_name}",
        f"--add-data={ctk_path}{sep}customtkinter",
        entry_point
    ]

    print(f"[INFO] Compilando para plataforma: {target}")
    print(f"[INFO] Comando: {' '.join(cmd)}")

    try:
        subprocess.run(cmd, check=True)
        print(f"[OK] Executavel criado com sucesso: dist/{exe_name}")
    except subprocess.CalledProcessError as e:
        print(f"[ERRO] Falha ao criar o executavel: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Erro inesperado: {e}")
        sys.exit(1)

if __name__ == "__main__":
    # Suporta argumento opcional: --windows, --linux, --mac
    target = None
    if len(sys.argv) > 1:
        arg = sys.argv[1].lower().lstrip("-")
        if arg in ("windows", "win"):
            target = "windows"
        elif arg in ("linux",):
            target = "linux"
        elif arg in ("mac", "osx", "darwin"):
            target = "mac"
    build(target)

