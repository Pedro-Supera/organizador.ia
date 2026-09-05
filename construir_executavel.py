import os
import subprocess
import sys
from pathlib import Path

import customtkinter


def build(platform_target=None):
    """Compila o executável para a plataforma alvo usando a plataforma atual."""
    host_platform = {"nt": "windows", "darwin": "mac"}.get(os.name, "linux")
    target = platform_target or host_platform
    if target != host_platform:
        raise RuntimeError(
            f"PyInstaller nao faz cross-compilacao: alvo {target} em host {host_platform}."
        )

    ctk_path = Path(customtkinter.__file__).resolve().parent
    entry_point = Path("app.py")
    exe_name = "OrganizadorInteligente"
    sep = ";" if os.name == "nt" else ":"

    if not entry_point.is_file():
        raise FileNotFoundError(f"Arquivo de entrada nao encontrado: {entry_point}")

    cmd = [
        "pyinstaller",
        "--noconsole",
        "--onefile",
        "--clean",
        "--noconfirm",
        f"--name={exe_name}",
        f"--add-data={ctk_path}{sep}customtkinter",
        str(entry_point),
    ]

    print(f"[INFO] Compilando para plataforma: {target}")
    print(f"[INFO] Comando: {' '.join(cmd)}")

    try:
        subprocess.run(cmd, check=True)
        saida = Path("dist") / (f"{exe_name}.exe" if target == "windows" else exe_name)
        if not saida.is_file():
            raise RuntimeError(f"O build terminou, mas o executavel nao foi encontrado: {saida}")
        print(f"[OK] Executavel criado com sucesso: {saida}")
    except subprocess.CalledProcessError as e:
        print(f"[ERRO] Falha ao criar o executavel: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"[ERRO] Erro inesperado: {e}")
        sys.exit(1)


if __name__ == "__main__":
    target = None
    if len(sys.argv) > 1:
        arg = sys.argv[1].lower().lstrip("-")
        if arg in ("windows", "win"):
            target = "windows"
        elif arg == "linux":
            target = "linux"
        elif arg in ("mac", "osx", "darwin"):
            target = "mac"
    build(target)
