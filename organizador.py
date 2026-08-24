#!/usr/bin/env python3
"""Organiza arquivos e cria resumos opcionais com a API da Groq."""

import argparse
import os
import shutil
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from dotenv import load_dotenv
from groq import APIConnectionError, APIStatusError, Groq, RateLimitError
from pypdf import PdfReader
from rich.console import Console
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TaskProgressColumn, TextColumn
from rich.table import Table

console = Console()
ARQUIVOS_INTERNOS = {".env", ".gitignore", "contexto.txt", "organizador.py", "app.py"}
CAMINHO_ENV = Path(__file__).with_name(".env")


class OperacaoCancelada(Exception):
    """Sinaliza o cancelamento solicitado pela interface gráfica."""

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
        return "\n".join(pagina.extract_text() or "" for pagina in reader.pages).strip()
    except Exception as erro:
        console.print(f"[yellow]Não foi possível ler o PDF {caminho.name}: {erro}[/yellow]")
        return ""


def extrair_texto_txt(caminho: Path) -> str:
    for encoding in ("utf-8", "iso-8859-1", "latin-1"):
        try:
            return caminho.read_text(encoding=encoding).strip()
        except UnicodeDecodeError:
            continue
        except OSError as erro:
            console.print(f"[yellow]Não foi possível ler o TXT {caminho.name}: {erro}[/yellow]")
            return ""
    return ""


def extrair_texto_docx(caminho: Path) -> str:
    try:
        from docx import Document

        documento = Document(str(caminho))
        return "\n".join(paragrafo.text for paragrafo in documento.paragraphs).strip()
    except Exception as erro:
        console.print(f"[yellow]Não foi possível ler o DOCX {caminho.name}: {erro}[/yellow]")
        return ""


def extrair_texto(caminho: Path) -> str:
    extratores = {".pdf": extrair_texto_pdf, ".txt": extrair_texto_txt, ".docx": extrair_texto_docx}
    extrator = extratores.get(caminho.suffix.lower())
    return extrator(caminho) if extrator else ""


def gerar_resumo(texto: str, nome_arquivo: str, model: str = "qwen/qwen3.6-27b", client=None) -> str:
    if not texto or len(texto) < 50:
        return "Texto muito curto ou vazio para gerar resumo."

    load_dotenv(dotenv_path=CAMINHO_ENV)
    if client is None:
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            return "IA desativada: GROQ_API_KEY não configurada."
        client = Groq(api_key=api_key)

    prompt = f"""Faça um resumo em português do texto abaixo em no máximo 5 linhas.
Seja claro e objetivo.

Texto:
{texto[:6000]}
"""
    for tentativa in range(3):
        try:
            resposta = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "Você é um assistente que cria resumos curtos e claros em português."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
                max_tokens=300,
            )
            return (resposta.choices[0].message.content or "").strip()
        except RateLimitError:
            if tentativa < 2:
                time.sleep(2 ** tentativa)
        except (APIConnectionError, APIStatusError) as erro:
            status = getattr(erro, "status_code", None)
            if status in {400, 401, 403, 404}:
                console.print(f"[yellow]Falha permanente da API ao resumir {nome_arquivo}: {erro}[/yellow]")
                return "Erro permanente da API ao gerar o resumo."
            if tentativa < 2:
                time.sleep(2 ** tentativa)
            else:
                console.print(f"[yellow]Falha da API ao resumir {nome_arquivo}: {erro}[/yellow]")
        except Exception as erro:
            console.print(f"[yellow]Erro ao gerar resumo de {nome_arquivo}: {erro}[/yellow]")
            break
    return "Erro ao gerar resumo com a IA."


def proximo_destino(destino: Path) -> Path:
    if not destino.exists():
        return destino
    contador = 1
    while True:
        candidato = destino.with_name(f"{destino.stem}_{contador}{destino.suffix}")
        if not candidato.exists():
            return candidato
        contador += 1


def salvar_resumo(pasta_resumos: Path, nome_arquivo: str, resumo: str) -> None:
    destino = proximo_destino(pasta_resumos / f"resumo_{Path(nome_arquivo).stem}.md")
    destino.write_text(f"# Resumo de {nome_arquivo}\n\n{resumo}\n", encoding="utf-8")


def organizar_pasta(caminho_pasta: str, dry_run: bool = False, no_ai: bool = False,
                   model: str = "qwen/qwen3.6-27b", max_files: int | None = None,
                   progresso=None, cancel_event=None) -> None:
    pasta = Path(caminho_pasta).expanduser().resolve()
    if not pasta.is_dir():
        raise ValueError(f"A pasta '{pasta}' não existe ou não é um diretório.")

    arquivos = sorted(
        (arquivo for arquivo in pasta.iterdir() if arquivo.is_file() and arquivo.name not in ARQUIVOS_INTERNOS),
        key=lambda item: item.name.lower(),
    )
    if max_files is not None:
        arquivos = arquivos[:max_files]
    if not arquivos:
        console.print(Panel("Nenhum arquivo encontrado para organizar.", style="yellow"))
        return

    pasta_resumos = pasta / "resumos"
    if not dry_run:
        pasta_resumos.mkdir(exist_ok=True)

    planos = []
    usados = set()
    with Progress(SpinnerColumn(), TextColumn("Lendo arquivos"), BarColumn(), TaskProgressColumn()) as progress:
        tarefa = progress.add_task("leitura", total=len(arquivos))
        for arquivo in arquivos:
            if cancel_event and cancel_event.is_set():
                raise OperacaoCancelada
            categoria = obter_categoria(arquivo.suffix)
            destino = proximo_destino(pasta / categoria / arquivo.name)
            while destino in usados:
                destino = proximo_destino(destino)
            usados.add(destino)
            texto = extrair_texto(arquivo) if arquivo.suffix.lower() in {".pdf", ".txt", ".docx"} else ""
            planos.append((arquivo, categoria, destino, texto))
            progress.advance(tarefa)
            if progresso:
                progresso(1 / (len(arquivos) * 2))

    movidos = 0
    for arquivo, categoria, destino, _ in planos:
        if cancel_event and cancel_event.is_set():
            raise OperacaoCancelada
        if dry_run:
            console.print(f"[cyan]SIMULAÇÃO[/cyan] {arquivo.name} -> {categoria}/{destino.name}")
        elif arquivo.parent != destino.parent or arquivo.name != destino.name:
            try:
                destino.parent.mkdir(exist_ok=True)
                shutil.move(str(arquivo), str(destino))
                movidos += 1
            except OSError as erro:
                console.print(f"[red]Falha ao mover {arquivo.name}: {erro}[/red]")

    resumos = set()
    tarefas_ia = [(arquivo, texto) for arquivo, _, _, texto in planos if texto and not no_ai]
    if tarefas_ia and dry_run:
        for arquivo, _ in tarefas_ia:
            console.print(f"[cyan]SIMULAÇÃO[/cyan] gerar resumo para {arquivo.name}")
        if progresso:
            progresso(0.5)
    elif tarefas_ia:
        load_dotenv(dotenv_path=CAMINHO_ENV)
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            console.print(Panel("GROQ_API_KEY não configurada; resumos de IA ignorados.", title="Atenção", style="yellow"))
            if progresso:
                progresso(0.5)
        else:
            client = Groq(api_key=api_key)
            with ThreadPoolExecutor(max_workers=min(8, len(tarefas_ia))) as executor:
                futuros = {executor.submit(gerar_resumo, texto, arquivo.name, model, client): arquivo for arquivo, texto in tarefas_ia}
                with Progress(SpinnerColumn(), TextColumn("Gerando resumos"), BarColumn(), TaskProgressColumn()) as progress:
                    tarefa = progress.add_task("IA", total=len(futuros))
                    for futuro in as_completed(futuros):
                        arquivo = futuros[futuro]
                        salvar_resumo(pasta_resumos, arquivo.name, futuro.result())
                        resumos.add(arquivo.name)
                        progress.advance(tarefa)
                        if progresso:
                            progresso(1 / (len(tarefas_ia) * 2))
    elif progresso:
        progresso(0.5)

    tabela = Table(title="Relatório da organização")
    tabela.add_column("Categoria")
    tabela.add_column("Arquivos", justify="right")
    tabela.add_column("Resumos", justify="right")
    contagem = Counter(categoria for _, categoria, _, _ in planos)
    for categoria in sorted(contagem):
        quantidade_resumos = sum(1 for arquivo, cat, _, _ in planos if cat == categoria and arquivo.name in resumos)
        tabela.add_row(categoria, str(contagem[categoria]), str(quantidade_resumos))
    console.print(tabela)
    console.print(Panel(f"{movidos} arquivo(s) movido(s); {len(resumos)} resumo(s) criado(s).", title="Concluído", style="green"))


def construir_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Organiza arquivos e cria resumos com a Groq.")
    parser.add_argument("caminho", help="Pasta que será organizada")
    parser.add_argument("-d", "--dry-run", action="store_true", help="Simula a operação sem alterar arquivos")
    parser.add_argument("--no-ai", action="store_true", help="Desativa a geração de resumos com IA")
    parser.add_argument("--model", default="qwen/qwen3.6-27b", help="Modelo da Groq usado nos resumos")
    parser.add_argument("--max-files", type=int, help="Limita a quantidade de arquivos processados")
    return parser


def main() -> int:
    args = construir_parser().parse_args()
    if args.max_files is not None and args.max_files < 1:
        raise SystemExit("--max-files deve ser maior que zero")
    try:
        organizar_pasta(args.caminho, args.dry_run, args.no_ai, args.model, args.max_files)
    except ValueError as erro:
        console.print(Panel(str(erro), title="Erro", style="red"))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
