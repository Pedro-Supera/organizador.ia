import subprocess
import sys
import os
import customtkinter

def build():
    ctk_path = os.path.dirname(customtkinter.__file__)

    entry_point = "app.py"
    exe_name = "OrganizadorInteligente"

    cmd = [
        "pyinstaller",
        "--noconsole",
        "--onefile",
        f"--name={exe_name}",
        f"--add-data={ctk_path};customtkinter",
        entry_point
    ]

    try:
        subprocess.run(cmd, check=True)
        print("[OK] Executavel criado com sucesso!")
    except subprocess.CalledProcessError as e:
        print(f"[ERRO] Falha ao criar o executavel: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Erro inesperado: {e}")
        sys.exit(1)

if __name__ == "__main__":
    build()

