#!/usr/bin/env python3
"""Núcleo de organização de arquivos e geração opcional de resumos."""

import argparse
import csv
import os
import random
import shutil
import sys
import threading
import time
from collections import Counter
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Protocol, TypedDict
from html.parser import HTMLParser

from dotenv import load_dotenv
from groq import APIConnectionError, APIStatusError, Groq, RateLimitError
from pypdf import PdfReader
from rich.console import Console
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TaskProgressColumn, TextColumn
from rich.table import Table

MODELO_PADRAO = "qwen/qwen3.6-27b"
URL_CHAVES_GROQ = "https://console.groq.com/keys"
ARQUIVOS_INTERNOS = {".env", ".gitignore", "contexto.txt", "organizador.py", "app.py"}

CATEGORIAS = {
    "pdfs": [".pdf"],
    "imagens": [".jpg", ".jpeg", ".png", ".bmp", ".webp", ".gif"],
    "documentos": [".doc", ".docx", ".odt", ".txt", ".rtf"],
    "planilhas": [".xls", ".xlsx", ".csv", ".ods"],
    "compactados": [".zip", ".rar", ".7z", ".tar", ".gz"],
}


class Estatisticas(TypedDict):
    """Resumo dos resultados de uma operação."""

    movidos: int
    resumos_sucesso: int
    resumos_falha: int
    por_categoria: dict[str, int]
    destino: str


class Logger(Protocol):
    """Contrato de saída usado pelo núcleo, pela CLI e pela GUI."""

    def info(self, mensagem: str) -> None:
        """Registra uma mensagem informativa."""

    def warning(self, mensagem: str) -> None:
        """Registra um alerta."""

    def error(self, mensagem: str) -> None:
        """Registra um erro."""


class RichLogger:
    """Implementa o logger do núcleo usando o Rich."""

    def __init__(self, console: Console | None = None) -> None:
        self.console = console or Console()

    def info(self, mensagem: str) -> None:
        self.console.print(mensagem)

    def warning(self, mensagem: str) -> None:
        self.console.print(f"[yellow]{mensagem}[/yellow]")

    def error(self, mensagem: str) -> None:
        self.console.print(f"[red]{mensagem}[/red]")


class OperacaoCancelada(Exception):
    """Sinaliza o cancelamento solicitado pela interface."""


def cancelar_futuros(futuros: list[Any]) -> None:
    """Solicita cancelamento de todos os futures ainda pendentes."""
    for futuro in futuros:
        futuro.cancel()


class _ExtratorHTML(HTMLParser):
    """Coleta texto visível de um documento HTML."""

    def __init__(self) -> None:
        super().__init__()
        self.textos: list[str] = []

    def handle_data(self, data: str) -> None:
        if data.strip():
            self.textos.append(data.strip())


def caminho_base() -> Path:
    """Retorna a pasta do script ou do executável empacotado."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def caminhos_env() -> tuple[Path, Path]:
    """Retorna os caminhos principal e alternativo para configuração da API."""
    principal = caminho_base() / ".env"
    alternativo = Path.home() / ".config" / "organizador-ia" / ".env"
    return principal, alternativo


def caminho_env_gravavel() -> Path:
    """Retorna o caminho de configuração com permissão de escrita disponível."""
    principal, alternativo = caminhos_env()
    try:
        principal.parent.mkdir(parents=True, exist_ok=True)
        if not principal.exists():
            principal.touch()
        if os.access(principal, os.W_OK):
            return principal
    except OSError:
        pass
    alternativo.parent.mkdir(parents=True, exist_ok=True)
    return alternativo


def carregar_ambiente() -> Path | None:
    """Carrega o primeiro `.env` disponível e retorna seu caminho."""
    for caminho in caminhos_env():
        if caminho.is_file():
            load_dotenv(dotenv_path=caminho)
            return caminho
    return None


def obter_categoria(extensao: str) -> str:
    """Retorna a categoria associada a uma extensão."""
    extensao = extensao.lower()
    return next((categoria for categoria, extensoes in CATEGORIAS.items() if extensao in extensoes), "outros")


def extrair_texto_pdf(caminho: Path, logger: Logger | None = None) -> str:
    """Extrai o texto disponível em todas as páginas de um PDF."""
    try:
        reader = PdfReader(str(caminho))
        texto = "\n".join(pagina.extract_text() or "" for pagina in reader.pages).strip()
        if len(texto) < 20 and caminho.stat().st_size > 50 * 1024:
            (logger or RichLogger()).warning(
                f"O arquivo {caminho.name} pode ser uma imagem ou PDF escaneado "
                "(sem texto extraível). OCR indisponível."
            )
        return texto
    except Exception as erro:
        (logger or RichLogger()).warning(f"Não foi possível ler o PDF {caminho.name}: {erro}")
        return ""


def extrair_texto_txt(caminho: Path, logger: Logger | None = None) -> str:
    """Lê um TXT tentando UTF-8, ISO-8859-1 e Latin-1."""
    for encoding in ("utf-8", "iso-8859-1", "latin-1"):
        try:
            return caminho.read_text(encoding=encoding).strip()
        except UnicodeDecodeError:
            continue
        except OSError as erro:
            (logger or RichLogger()).warning(f"Não foi possível ler o TXT {caminho.name}: {erro}")
            return ""
    return ""


def extrair_texto_docx(caminho: Path, logger: Logger | None = None) -> str:
    """Extrai o texto dos parágrafos de um DOCX."""
    try:
        from docx import Document

        documento = Document(str(caminho))
        return "\n".join(paragrafo.text for paragrafo in documento.paragraphs).strip()
    except Exception as erro:
        (logger or RichLogger()).warning(f"Não foi possível ler o DOCX {caminho.name}: {erro}")
        return ""


def extrair_texto_pptx(caminho: Path, logger: Logger | None = None) -> str:
    """Extrai textos de caixas e tabelas de uma apresentação PPTX."""
    try:
        from pptx import Presentation

        apresentacao = Presentation(str(caminho))
        textos: list[str] = []
        for slide in apresentacao.slides:
            for forma in slide.shapes:
                if hasattr(forma, "text") and forma.text.strip():
                    textos.append(forma.text.strip())
        return "\n".join(textos)
    except ImportError:
        (logger or RichLogger()).warning("python-pptx não está instalado; PPTX ignorado.")
    except Exception as erro:
        (logger or RichLogger()).warning(f"Não foi possível ler o PPTX {caminho.name}: {erro}")
    return ""


def extrair_texto_html(caminho: Path, logger: Logger | None = None) -> str:
    """Extrai texto simples de um arquivo HTML."""
    try:
        parser = _ExtratorHTML()
        parser.feed(caminho.read_text(encoding="utf-8", errors="replace"))
        return " ".join(parser.textos)
    except OSError as erro:
        (logger or RichLogger()).warning(f"Não foi possível ler o HTML {caminho.name}: {erro}")
        return ""


def extrair_texto_csv(caminho: Path, logger: Logger | None = None) -> str:
    """Extrai e concatena as células de um arquivo CSV."""
    try:
        with caminho.open(newline="", encoding="utf-8", errors="replace") as arquivo:
            return "\n".join(" | ".join(celula.strip() for celula in linha) for linha in csv.reader(arquivo)).strip()
    except OSError as erro:
        (logger or RichLogger()).warning(f"Não foi possível ler o CSV {caminho.name}: {erro}")
        return ""


def extrair_texto(caminho: Path, logger: Logger | None = None) -> str:
    """Seleciona o extrator compatível com a extensão."""
    extratores: dict[str, Callable[[Path, Logger | None], str]] = {
        ".pdf": extrair_texto_pdf,
        ".txt": extrair_texto_txt,
        ".docx": extrair_texto_docx,
        ".pptx": extrair_texto_pptx,
        ".html": extrair_texto_html,
        ".csv": extrair_texto_csv,
    }
    extrator = extratores.get(caminho.suffix.lower())
    return extrator(caminho, logger) if extrator else ""


def gerar_resumo(texto: str, nome_arquivo: str, model: str = MODELO_PADRAO,
                 client: Any | None = None, logger: Logger | None = None) -> str:
    """Gera um resumo em português usando a API da Groq."""
    if not texto or len(texto) < 50:
        return "Texto muito curto ou vazio para gerar resumo."
    carregar_ambiente()
    if client is None:
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            return "IA desativada: GROQ_API_KEY não configurada."
        client = Groq(api_key=api_key)
    prompt = f"Faça um resumo em português do texto abaixo em no máximo 5 linhas.\nSeja claro e objetivo.\n\nTexto:\n{texto[:6000]}"
    for tentativa in range(3):
        try:
            resposta = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "Você cria resumos curtos e claros em português."},
                    {"role": "user", "content": prompt},
                ], temperature=0.3, max_tokens=300,
            )
            return (resposta.choices[0].message.content or "").strip()
        except RateLimitError:
            if tentativa < 2:
                time.sleep((2 ** tentativa) + random.uniform(0.1, 0.5))
        except (APIConnectionError, APIStatusError) as erro:
            status = getattr(erro, "status_code", None)
            if status in {400, 401, 403, 404}:
                (logger or RichLogger()).error(f"Falha permanente da API ao resumir {nome_arquivo}: {erro}")
                return "Erro permanente da API ao gerar o resumo."
            if tentativa < 2:
                time.sleep((2 ** tentativa) + random.uniform(0.1, 0.5))
            else:
                (logger or RichLogger()).warning(f"Falha da API ao resumir {nome_arquivo}: {erro}")
        except Exception as erro:
            (logger or RichLogger()).warning(f"Erro ao gerar resumo de {nome_arquivo}: {erro}")
            break
    return "Erro ao gerar resumo com a IA."


def proximo_destino(destino: Path) -> Path:
    """Retorna um destino livre, adicionando sufixo numérico se necessário."""
    if not destino.exists():
        return destino
    contador = 1
    while (candidato := destino.with_name(f"{destino.stem}_{contador}{destino.suffix}")).exists():
        contador += 1
    return candidato


def salvar_resumo(pasta_resumos: Path, nome_arquivo: str, resumo: str) -> None:
    """Salva um resumo Markdown sem sobrescrever outro existente."""
    destino = proximo_destino(pasta_resumos / f"resumo_{Path(nome_arquivo).stem}.md")
    destino.write_text(f"# Resumo de {nome_arquivo}\n\n{resumo}\n", encoding="utf-8")


def organizar_pasta(caminho_pasta: str, dry_run: bool = False, no_ai: bool = False,
                   model: str = MODELO_PADRAO, max_files: int | None = None,
                   logger: Logger | None = None, progresso: Callable[[float], None] | None = None,
                   cancel_event: threading.Event | None = None,
                   estatisticas: Callable[[Estatisticas], None] | None = None) -> Estatisticas:
    """Organiza uma pasta e gera resumos opcionalmente."""
    logger = logger or RichLogger()
    pasta = Path(caminho_pasta).expanduser().resolve()
    if not pasta.is_dir():
        raise ValueError(f"A pasta '{pasta}' não existe ou não é um diretório.")
    arquivos = sorted((item for item in pasta.iterdir() if item.is_file() and item.name not in ARQUIVOS_INTERNOS), key=lambda item: item.name.lower())
    if max_files is not None:
        arquivos = arquivos[:max_files]
    if not arquivos:
        logger.warning("Nenhum arquivo encontrado para organizar.")
        resultado: Estatisticas = {"movidos": 0, "resumos_sucesso": 0, "resumos_falha": 0, "por_categoria": {}, "destino": str(pasta)}
        if estatisticas:
            estatisticas(resultado)
        return resultado
    pasta_resumos = pasta / "resumos"
    if not dry_run:
        pasta_resumos.mkdir(exist_ok=True)
    planos: list[tuple[Path, str, Path, str]] = []
    usados: set[Path] = set()
    for indice, arquivo in enumerate(arquivos, 1):
        if cancel_event and cancel_event.is_set():
            raise OperacaoCancelada
        categoria = obter_categoria(arquivo.suffix)
        destino = proximo_destino(pasta / categoria / arquivo.name)
        while destino in usados:
            destino = proximo_destino(destino)
        usados.add(destino)
        texto = extrair_texto(arquivo, logger) if arquivo.suffix.lower() in {".pdf", ".txt", ".docx"} else ""
        planos.append((arquivo, categoria, destino, texto))
        if progresso:
            progresso(indice / (len(arquivos) * 2))
    movidos = 0
    for arquivo, categoria, destino, _ in planos:
        if cancel_event and cancel_event.is_set():
            raise OperacaoCancelada
        if dry_run:
            logger.info(f"SIMULAÇÃO {arquivo.name} -> {categoria}/{destino.name}")
        elif arquivo.parent != destino.parent or arquivo.name != destino.name:
            try:
                destino.parent.mkdir(exist_ok=True)
                shutil.move(str(arquivo), str(destino))
                movidos += 1
                logger.info(f"Movido: {arquivo.name} -> {categoria}/{destino.name}")
            except OSError as erro:
                logger.error(f"Falha ao mover {arquivo.name}: {erro}")
    resumos: set[str] = set()
    resumos_falha = 0
    tarefas_ia = [(arquivo, texto) for arquivo, _, _, texto in planos if texto and not no_ai]
    if tarefas_ia and dry_run:
        for arquivo, _ in tarefas_ia:
            logger.info(f"SIMULAÇÃO gerar resumo para {arquivo.name}")
        if progresso:
            progresso(0.5)
    elif tarefas_ia:
        carregar_ambiente()
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            logger.warning("GROQ_API_KEY não configurada; resumos de IA ignorados.")
            if progresso:
                progresso(0.5)
        else:
            client = Groq(api_key=api_key)
            executor = ThreadPoolExecutor(max_workers=min(8, len(tarefas_ia)))
            try:
                futuros = {executor.submit(gerar_resumo, texto, arquivo.name, model, client, logger): arquivo for arquivo, texto in tarefas_ia}
                for indice, futuro in enumerate(as_completed(futuros), 1):
                    if cancel_event and cancel_event.is_set():
                        cancelar_futuros(list(futuros))
                        raise OperacaoCancelada
                    arquivo = futuros[futuro]
                    resumo = futuro.result()
                    salvar_resumo(pasta_resumos, arquivo.name, resumo)
                    resumos.add(arquivo.name)
                    if resumo.startswith("Erro"):
                        resumos_falha += 1
                    if progresso:
                        progresso(indice / (len(tarefas_ia) * 2))
            finally:
                executor.shutdown(wait=False, cancel_futures=True)
    elif progresso:
        progresso(0.5)
    contagem = Counter(categoria for _, categoria, _, _ in planos)
    logger.info(f"Concluído: {movidos} arquivo(s) movido(s); {len(resumos)} resumo(s) criado(s).")
    for categoria in sorted(contagem):
        logger.info(f"{categoria}: {contagem[categoria]} arquivo(s), {sum(1 for arquivo, cat, _, _ in planos if cat == categoria and arquivo.name in resumos)} resumo(s)")
    resultado = {
        "movidos": movidos,
        "resumos_sucesso": len(resumos) - resumos_falha,
        "resumos_falha": resumos_falha,
        "por_categoria": dict(contagem),
        "destino": str(pasta),
    }
    if estatisticas:
        estatisticas(resultado)
    return resultado


def construir_parser() -> argparse.ArgumentParser:
    """Cria o parser da interface de linha de comando."""
    parser = argparse.ArgumentParser(description="Organiza arquivos e cria resumos com a Groq.")
    parser.add_argument("caminho", help="Pasta que será organizada")
    parser.add_argument("-d", "--dry-run", action="store_true", help="Simula a operação sem alterar arquivos")
    parser.add_argument("--no-ai", action="store_true", help="Desativa a geração de resumos com IA")
    parser.add_argument("--model", default=MODELO_PADRAO, help="Modelo da Groq usado nos resumos")
    parser.add_argument("--max-files", type=int, help="Limita a quantidade de arquivos processados")
    return parser


def main() -> int:
    """Executa a interface de linha de comando."""
    args = construir_parser().parse_args()
    if args.max_files is not None and args.max_files < 1:
        raise SystemExit("--max-files deve ser maior que zero")
    try:
        organizar_pasta(args.caminho, args.dry_run, args.no_ai, args.model, args.max_files)
    except ValueError as erro:
        RichLogger().error(str(erro))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
