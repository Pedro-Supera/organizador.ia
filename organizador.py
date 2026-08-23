#!/usr/bin/env python3
"""
Organizador Inteligente de Arquivos + Resumo com IA (Groq)
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from groq import Groq
from pypdf import PdfReader

# Carrega a chave da API
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not GROQ_API_KEY:
    print("❌ Erro: GROQ_API_KEY não encontrada no arquivo .env")
    sys.exit(1)

client = Groq(api_key=GROQ_API_KEY)

# Extensões por categoria
CATEGORIAS = {
    "pdfs": [".pdf"],
    "imagens": [".jpg", ".jpeg", ".png", ".bmp", ".webp", ".gif"],
    "documentos": [".doc", ".docx", ".odt", ".txt", ".rtf"],
    "planilhas": [".xls", ".xlsx", ".csv", ".ods"],
    "compactados": [".zip", ".rar", ".7z", ".tar", ".gz"],
}

def obter_categoria(extensao: str) -> str:
    extensao = extensao.lower()
    for categoria, extensoes in CATEGORIAS.items():
        if extensao in extensoes:
            return categoria
    return "outros"

def extrair_texto_pdf(caminho: Path) -> str:
    try:
        reader = PdfReader(str(caminho))
        texto = ""
        for pagina in reader.pages:
            conteudo = pagina.extract_text()
            if conteudo:
                texto += conteudo + "\n"
        return texto.strip()
    except Exception as e:
        print(f"  ⚠️  Não foi possível ler o PDF {caminho.name}: {e}")
        return ""

def extrair_texto_txt(caminho: Path) -> str:
    try:
        return caminho.read_text(encoding="utf-8", errors="ignore").strip()
    except Exception as e:
        print(f"  ⚠️  Não foi possível ler o TXT {caminho.name}: {e}")
        return ""

def gerar_resumo(texto: str, nome_arquivo: str) -> str:
    if not texto or len(texto) < 50:
        return "Texto muito curto ou vazio para gerar resumo."

    # Limita o texto para não estourar o contexto
    texto_limitado = texto[:6000]

    prompt = f"""Faça um resumo em português do texto abaixo em no máximo 5 linhas.
Seja claro e objetivo.

Texto:
{texto_limitado}
"""

    try:
        resposta = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "Você é um assistente que cria resumos curtos e claros em português."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=300
        )
        return resposta.choices[0].message.content.strip()
    except Exception as e:
        print(f"  ⚠️  Erro ao gerar resumo de {nome_arquivo}: {e}")
        return "Erro ao gerar resumo com a IA."

def organizar_pasta(caminho_pasta: str):
    pasta = Path(caminho_pasta).expanduser().resolve()

    if not pasta.exists() or not pasta.is_dir():
        print(f"❌ Erro: A pasta '{pasta}' não existe ou não é um diretório.")
        sys.exit(1)

    print(f"\n📂 Organizando pasta: {pasta}\n")

    # Contadores
    movidos = 0
    resumos_gerados = 0
    pastas_criadas = set()

    # Pasta de resumos
    pasta_resumos = pasta / "resumos"
    pasta_resumos.mkdir(exist_ok=True)
    pastas_criadas.add("resumos")

    # Lista apenas arquivos (ignora pastas)
    arquivos = [f for f in pasta.iterdir() if f.is_file()]

    if not arquivos:
        print("Nenhum arquivo encontrado para organizar.")
        return

    for arquivo in arquivos:
        extensao = arquivo.suffix.lower()
        categoria = obter_categoria(extensao)
        pasta_destino = pasta / categoria

        # Cria a pasta da categoria se não existir
        if not pasta_destino.exists():
            pasta_destino.mkdir()
            pastas_criadas.add(categoria)
            print(f"📁 Pasta criada: {categoria}/")

        destino = pasta_destino / arquivo.name

        # Só move se ainda não estiver na pasta correta
        if arquivo.parent != pasta_destino:
            try:
                arquivo.rename(destino)
                print(f"✅ Movido: {arquivo.name} → {categoria}/")
                movidos += 1
            except Exception as e:
                print(f"❌ Erro ao mover {arquivo.name}: {e}")
                continue
        else:
            print(f"⏭️  Já está organizado: {arquivo.name}")

        # Gera resumo apenas para PDF e TXT
        if extensao in [".pdf", ".txt"]:
            print(f"  🧠 Gerando resumo de {arquivo.name}...")

            if extensao == ".pdf":
                texto = extrair_texto_pdf(destino)
            else:
                texto = extrair_texto_txt(destino)

            if texto:
                resumo = gerar_resumo(texto, arquivo.name)
                nome_resumo = f"resumo_{arquivo.stem}.md"
                caminho_resumo = pasta_resumos / nome_resumo

                caminho_resumo.write_text(
                    f"# Resumo de {arquivo.name}\n\n{resumo}\n",
                    encoding="utf-8"
                )
                print(f"  📝 Resumo salvo: resumos/{nome_resumo}")
                resumos_gerados += 1

    # Resumo final
    print("\n" + "="*50)
    print("📊 RESUMO FINAL")
    print("="*50)
    print(f"Arquivos movidos     : {movidos}")
    print(f"Resumos gerados      : {resumos_gerados}")
    print(f"Pastas criadas       : {', '.join(sorted(pastas_criadas)) if pastas_criadas else 'Nenhuma'}")
    print("="*50)
    print("✅ Organização concluída!\n")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python organizador.py <caminho_da_pasta>")
        print("Exemplo: python organizador.py ~/Downloads")
        sys.exit(1)

    caminho = sys.argv[1]
    organizar_pasta(caminho)
