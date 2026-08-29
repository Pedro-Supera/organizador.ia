#!/usr/bin/env python3
"""Núcleo de organização de arquivos e geração opcional de resumos."""

import argparse
import csv
import hashlib
import json
import os
import random
import re
import shutil
import sys
import threading
import time
from collections import Counter
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Protocol, TypedDict

from dotenv import load_dotenv, set_key
from groq import APIConnectionError, APIStatusError, Groq, RateLimitError
from pypdf import PdfReader
from rich.console import Console
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TaskProgressColumn, TextColumn
from rich.table import Table

MODELO_PADRAO = "qwen/qwen3.6-27b"
MAX_TEXTO_LEITURA = 50_000
URL_CHAVES_GROQ = "https://console.groq.com/keys"
ARQUIVOS_INTERNOS = {".env", ".gitignore", "contexto.txt", "organizador.py", "app.py"}

CATEGORIAS = {
    "pdfs": [".pdf"],
    "imagens": [".jpg", ".jpeg", ".png", ".bmp", ".webp", ".gif"],
    "documentos": [".doc", ".docx", ".odt", ".txt", ".rtf", ".pptx", ".html"],
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
    cache_hits: int
    cache_misses: int
    taxa_hits: float
    taxa_misses: float
    caracteres_salvos: int
    tokens_salvos: int
    tempo_estimado_segundos: float


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
    # Trata PyInstaller com _MEIPASS para localizar recursos
    if getattr(sys, "_MEIPASS", None):
        return Path(sys._MEIPASS)
    # Trata outros tipos de empacotamento (frozen)
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    # Execução normal como script
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


def calcular_sha256(caminho_arquivo: Path, chunk_size: int = 65536) -> str:
    """Calcula o hash SHA-256 de um arquivo em blocos."""
    hash_arquivo = hashlib.sha256()
    with caminho_arquivo.open("rb") as arquivo:
        for bloco in iter(lambda: arquivo.read(chunk_size), b""):
            hash_arquivo.update(bloco)
    return hash_arquivo.hexdigest()


def obter_caminho_cache(base_dir: str | Path | None = None) -> Path:
    """Retorna o caminho do cache local de resumos para a pasta de trabalho."""
    base = Path(base_dir).expanduser().resolve() if base_dir is not None else caminho_base()
    caminho_local = base / ".cache_resumos.json"
    try:
        if os.access(caminho_local.parent, os.W_OK):
            return caminho_local
    except OSError:
        pass

    caminho_home = Path.home() / ".cache_resumos.json"
    try:
        if os.access(Path.home(), os.W_OK):
            return caminho_home
    except OSError:
        pass
    return caminho_local


def carregar_cache(caminho_cache: Path) -> dict:
    """Lê o arquivo JSON do cache, retornando dicionário vazio em caso de falha."""
    try:
        if not caminho_cache.exists():
            return {}
        with caminho_cache.open("r", encoding="utf-8") as arquivo:
            dados = json.load(arquivo)
        if isinstance(dados, dict):
            return dados
    except (json.JSONDecodeError, OSError, TypeError, ValueError):
        return {}
    return {}


def salvar_cache(cache: dict, caminho_cache: Path) -> None:
    """Persiste o cache em JSON com tratamento de erro de I/O."""
    try:
        caminho_cache.parent.mkdir(parents=True, exist_ok=True)
        with caminho_cache.open("w", encoding="utf-8") as arquivo:
            json.dump(cache, arquivo, ensure_ascii=False, indent=2, sort_keys=True)
            arquivo.write("\n")
    except OSError:
        pass


def carregar_ambiente() -> Path | None:
    """Carrega o primeiro `.env` disponível e retorna seu caminho."""
    for caminho in caminhos_env():
        if caminho.is_file():
            load_dotenv(dotenv_path=caminho)
            return caminho
    return None


def sanitizar_nome_caminho(nome: str) -> str:
    """Remove componentes que poderiam escapar do diretório de destino."""
    return nome.replace("/", "_").replace("\\", "_").replace("\0", "_").replace("..", "__").strip()


def salvar_chave_api(chave: str) -> bool:
    """Salva a chave da Groq com permissões restritas no arquivo `.env`."""
    if not chave:
        return True
    try:
        caminho_env = caminho_env_gravavel()
        set_key(str(caminho_env), "GROQ_API_KEY", chave)
        if os.name != "nt":
            os.chmod(caminho_env, 0o600)
        os.environ["GROQ_API_KEY"] = chave
        return True
    except (OSError, PermissionError) as erro:
        RichLogger().error(f"Falha ao salvar chave da API: {erro}")
        return False


def listar_arquivos_elegiveis(caminho_pasta: str | Path, max_files: int | None = None) -> list[Path]:
    """Lista arquivos elegíveis, ordenados e opcionalmente limitados."""
    pasta = Path(caminho_pasta).expanduser().resolve()
    if not pasta.is_dir():
        raise ValueError(f"A pasta '{pasta}' não existe ou não é um diretório.")
    arquivos = sorted(
        (item for item in pasta.iterdir() if item.is_file() and item.name not in ARQUIVOS_INTERNOS),
        key=lambda item: item.name.lower(),
    )
    if isinstance(max_files, int) and max_files > 0:
        arquivos = arquivos[:max_files]
    return arquivos


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
    return (extrator(caminho, logger) if extrator else "")[:MAX_TEXTO_LEITURA]


def anonimizar_texto_sensivel(texto: str) -> str:
    """Substitui padrões sensíveis por marcadores protegidos."""
    if not texto:
        return ""

    texto = re.sub(r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b", "[CPF_PROTEGIDO]", texto)
    texto = re.sub(r"\b\d{11}\b", "[CPF_PROTEGIDO]", texto)
    texto = re.sub(r"\b\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}\b", "[CNPJ_PROTEGIDO]", texto)
    texto = re.sub(r"\b\d{14}\b", "[CNPJ_PROTEGIDO]", texto)
    texto = re.sub(r"\b\d{1,2}\.\d{3}\.\d{3}-[0-9Xx]\b", "[RG_PROTEGIDO]", texto)
    texto = re.sub(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b", "[EMAIL_PROTEGIDO]", texto)
    texto = re.sub(r"\b(?:api[_-]?key|token|secret|password|passwd|senha|chave)[\s:=]+[A-Za-z0-9._~:/+=-]{6,}\b", "[SEGREDO_PROTEGIDO]", texto, flags=re.IGNORECASE)
    texto = re.sub(r"\b(?:\d{4}[ -]?){3}\d{4}\b", "[CARTAO_PROTEGIDO]", texto)
    texto = re.sub(r"(?:(?:\+?55\s*)?(?:\(?\d{2}\)?\s*[-.]?)?\d{4,5}\s*[-.]?\d{4})\b", "[TELEFONE_PROTEGIDO]", texto)
    texto = re.sub(r"\b(?:0?[1-9]|[12][0-9]|3[01])[-/](?:0?[1-9]|1[0-2])[-/](?:19|20)\d{2}\b", "[DATA_PROTEGIDA]", texto)
    return texto


def gerar_resumo(texto: str, nome_arquivo: str = "arquivo", model: str = MODELO_PADRAO,
                 client: Any | None = None, logger: Logger | None = None,
                 api_key: str | None = None, stream: bool = True) -> str | None:
    """Gera um resumo em português usando a API da Groq, com suporte a streaming opcional."""
    if not texto or (len(texto) < 50 and api_key is None):
        return "Texto muito curto ou vazio para gerar resumo."
    carregar_ambiente()
    if client is None:
        chave = api_key or os.getenv("GROQ_API_KEY")
        if not chave:
            return "IA desativada: GROQ_API_KEY não configurada."
        client = Groq(api_key=chave)
    prompt = f"Faça um resumo em português do texto abaixo em no máximo 5 linhas.\nSeja claro e objetivo.\n\nTexto:\n{texto[:6000]}"
    logger = logger or RichLogger()
    for tentativa in range(3):
        parcial = ""
        try:
            resposta = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "Você cria resumos curtos e claros em português."},
                    {"role": "user", "content": prompt},
                ], temperature=0.3, max_tokens=300, stream=stream,
            )
            if stream and not hasattr(resposta, "choices") and hasattr(resposta, "__iter__"):
                for chunk in resposta:
                    if chunk is None:
                        continue
                    choices = getattr(chunk, "choices", [])
                    if not choices:
                        continue
                    for item in choices:
                        delta = getattr(item, "delta", None)
                        conteudo = getattr(delta, "content", None) if delta is not None else None
                        if conteudo:
                            if isinstance(conteudo, str):
                                pedaco = conteudo
                            else:
                                pedaco = "".join(str(part) for part in conteudo if part)
                            if pedaco:
                                parcial += pedaco
                                logger.info(f"[stream] {pedaco}")
                return parcial.strip() or "Resumo vazio durante streaming."
            if hasattr(resposta, "choices") and getattr(resposta, "choices", None):
                conteudo = getattr(resposta.choices[0].message, "content", None)
                return (conteudo or "").strip()
            return parcial.strip() or "Resumo vazio durante streaming."
        except RateLimitError:
            if tentativa < 2:
                _aguardar_retry(tentativa)
        except (APIConnectionError, APIStatusError) as erro:
            status = getattr(erro, "status_code", None)
            if status in {400, 401, 403, 404}:
                logger.error(f"Falha permanente da API ao resumir {nome_arquivo}: {erro}")
                return "Erro permanente da API ao gerar o resumo."
            if status is None or status >= 500:
                if tentativa < 2:
                    _aguardar_retry(tentativa)
                    continue
            if tentativa < 2:
                _aguardar_retry(tentativa)
            else:
                logger.warning(f"Falha da API ao resumir {nome_arquivo}: {erro}")
        except Exception as erro:
            logger.warning(f"Erro ao gerar resumo de {nome_arquivo}: {erro}")
            if tentativa < 2:
                _aguardar_retry(tentativa)
            else:
                return None
    return "Erro ao gerar resumo com a IA."


def _aguardar_retry(tentativa: int) -> None:
    """Aguarda com backoff exponencial e jitter antes de repetir uma chamada."""
    time.sleep((2 ** tentativa) + random.uniform(0.1, 0.5))


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
    nome_seguro = sanitizar_nome_caminho(Path(nome_arquivo).stem)
    destino = proximo_destino(pasta_resumos / f"resumo_{nome_seguro}.md")
    destino.write_text(f"# Resumo de {nome_arquivo}\n\n{resumo}\n", encoding="utf-8")


def gerar_relatorio_geral_markdown(estatisticas: dict[str, Any] | None, caminho_pasta: str | Path) -> Path:
    """Cria um relatório consolidado em Markdown para a operação completa."""
    pasta = Path(caminho_pasta).expanduser().resolve()
    pasta.mkdir(parents=True, exist_ok=True)
    dados = estatisticas or {}
    total_processados = dados.get("movidos", 0) + max(0, dados.get("cache_hits", 0) + dados.get("cache_misses", 0))
    taxa_hits = dados.get("taxa_hits", 0.0)
    taxa_misses = dados.get("taxa_misses", 0.0)
    relatorio = pasta / "00_RELATORIO_ORGANIZACAO.md"
    conteudo = f"""# Relatório de Organização

- Pasta: `{pasta}`
- Arquivos movidos: {dados.get('movidos', 0)}
- Resumos com sucesso: {dados.get('resumos_sucesso', 0)}
- Resumos com falha: {dados.get('resumos_falha', 0)}
- Cache hits: {dados.get('cache_hits', 0)}
- Cache misses: {dados.get('cache_misses', 0)}
- Taxa de acerto: {taxa_hits:.2f}%
- Taxa de miss: {taxa_misses:.2f}%
- Caracteres salvos: {dados.get('caracteres_salvos', 0)}
- Tokens estimados salvos: {dados.get('tokens_salvos', 0)}
- Tempo estimado economizado: {dados.get('tempo_estimado_segundos', 0.0):.2f}s
- Arquivos processados estimados: {total_processados}

## Resumo executivo
A operação foi concluída com {dados.get('movidos', 0)} movimentação(ões) de arquivos e {dados.get('resumos_sucesso', 0)} resumo(s) gerado(s) com sucesso.

## Categorias
"""
    por_categoria = dados.get("por_categoria", {})
    if por_categoria:
        for categoria, quantidade in sorted(por_categoria.items()):
            conteudo += f"- {categoria}: {quantidade}\n"
    else:
        conteudo += "- Nenhuma categoria processada.\n"
    relatorio.write_text(conteudo, encoding="utf-8")
    return relatorio


def organizar_pasta(caminho_pasta: str, dry_run: bool = False, no_ai: bool = False,
                   model: str = MODELO_PADRAO, max_files: int | None = None,
                   logger: Logger | None = None, progresso: Callable[[float], None] | None = None,
                   cancel_event: threading.Event | None = None,
                   estatisticas: Callable[[Estatisticas], None] | None = None) -> Estatisticas:
    """Organiza uma pasta e gera resumos opcionalmente."""
    logger = logger or RichLogger()
    pasta = Path(caminho_pasta).expanduser().resolve()
    arquivos = listar_arquivos_elegiveis(pasta, max_files)
    if not arquivos:
        logger.warning("Nenhum arquivo encontrado para organizar.")
        resultado: Estatisticas = {
            "movidos": 0,
            "resumos_sucesso": 0,
            "resumos_falha": 0,
            "por_categoria": {},
            "destino": str(pasta),
            "cache_hits": 0,
            "cache_misses": 0,
            "taxa_hits": 0.0,
            "taxa_misses": 0.0,
            "caracteres_salvos": 0,
            "tokens_salvos": 0,
            "tempo_estimado_segundos": 0.0,
        }
        if estatisticas:
            estatisticas(resultado)
        return resultado
    pasta_resumos = pasta / "resumos"
    if not dry_run:
        pasta_resumos.mkdir(exist_ok=True)
    planos: list[tuple[Path, str, Path, str, str]] = []
    usados: set[Path] = set()
    for indice, arquivo in enumerate(arquivos, 1):
        if cancel_event and cancel_event.is_set():
            raise OperacaoCancelada
        categoria = obter_categoria(arquivo.suffix)
        categoria_segura = sanitizar_nome_caminho(categoria)
        nome_seguro = sanitizar_nome_caminho(arquivo.name)
        destino = proximo_destino(pasta / categoria_segura / nome_seguro)
        while destino in usados:
            destino = proximo_destino(destino)
        usados.add(destino)
        extensoes_texto = {".pdf", ".txt", ".docx", ".pptx", ".html", ".csv"}
        texto = extrair_texto(arquivo, logger) if arquivo.suffix.lower() in extensoes_texto else ""
        sha256 = calcular_sha256(arquivo) if texto else ""
        planos.append((arquivo, categoria, destino, texto, sha256))
        if progresso:
            progresso(indice / (len(arquivos) * 2))
    movidos = 0
    for arquivo, categoria, destino, _, _ in planos:
        if cancel_event and cancel_event.is_set():
            raise OperacaoCancelada
        if dry_run:
            logger.info(f"[SIMULAÇÃO] Moveria {arquivo} -> {destino}")
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
    cache_hits = 0
    cache_misses = 0
    caracteres_salvos = 0
    caminho_cache = obter_caminho_cache(pasta)
    cache = carregar_cache(caminho_cache)
    tarefas_ia: list[tuple[Path, str, str]] = []
    chaves_em_execucao: set[str] = set()
    for arquivo, _, _, texto, sha256 in planos:
        if not texto or no_ai:
            continue
        texto_sanitizado = anonimizar_texto_sensivel(texto)
        chave_cache = f"{sha256}_{model}"
        if chave_cache in cache and isinstance(cache[chave_cache], str):
            resumo = cache[chave_cache]
            salvar_resumo(pasta_resumos, arquivo.name, resumo)
            resumos.add(arquivo.name)
            cache_hits += 1
            caracteres_salvos += len(texto_sanitizado)
            continue
        if chave_cache in chaves_em_execucao:
            continue
        chaves_em_execucao.add(chave_cache)
        cache_misses += 1
        tarefas_ia.append((arquivo, texto_sanitizado, chave_cache))
    if tarefas_ia and dry_run:
        for arquivo, _, _ in tarefas_ia:
            nome_seguro = sanitizar_nome_caminho(Path(arquivo.name).stem)
            resumo_path = proximo_destino(pasta_resumos / f"resumo_{nome_seguro}.md")
            logger.info(f"[SIMULAÇÃO] Criaria resumo em {resumo_path}")
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
                futuros = {
                    executor.submit(gerar_resumo, texto, arquivo.name, model, client, logger, api_key): (arquivo, chave_cache)
                    for arquivo, texto, chave_cache in tarefas_ia
                }
                for indice, futuro in enumerate(as_completed(futuros), 1):
                    if cancel_event and cancel_event.is_set():
                        cancelar_futuros(list(futuros))
                        raise OperacaoCancelada
                    arquivo, chave_cache = futuros[futuro]
                    resumo = futuro.result()
                    if resumo is not None:
                        cache[chave_cache] = resumo
                        salvar_cache(cache, caminho_cache)
                        salvar_resumo(pasta_resumos, arquivo.name, resumo)
                        resumos.add(arquivo.name)
                    if resumo is None or resumo.startswith("Erro"):
                        resumos_falha += 1
                    if progresso:
                        progresso(indice / (len(tarefas_ia) * 2))
            finally:
                executor.shutdown(wait=False, cancel_futures=True)
    elif progresso:
        progresso(0.5)
    contagem = Counter(categoria for _, categoria, _, _, _ in planos)
    logger.info(f"Concluído: {movidos} arquivo(s) movido(s); {len(resumos)} resumo(s) criado(s).")
    for categoria in sorted(contagem):
        logger.info(f"{categoria}: {contagem[categoria]} arquivo(s), {sum(1 for arquivo, cat, _, _, _ in planos if cat == categoria and arquivo.name in resumos)} resumo(s)")
    taxa_hits = (cache_hits / (cache_hits + cache_misses) * 100) if (cache_hits + cache_misses) else 0.0
    taxa_misses = 100.0 - taxa_hits
    tokens_salvos = max(0, caracteres_salvos // 4)
    tempo_estimado_segundos = round((cache_hits * 0.35) + (caracteres_salvos / 5000), 2)
    resultado = {
        "movidos": movidos,
        "resumos_sucesso": len(resumos) - resumos_falha,
        "resumos_falha": resumos_falha,
        "por_categoria": dict(contagem),
        "destino": str(pasta),
        "cache_hits": cache_hits,
        "cache_misses": cache_misses,
        "taxa_hits": taxa_hits,
        "taxa_misses": taxa_misses,
        "caracteres_salvos": caracteres_salvos,
        "tokens_salvos": tokens_salvos,
        "tempo_estimado_segundos": tempo_estimado_segundos,
    }
    if not dry_run:
        gerar_relatorio_geral_markdown(resultado, pasta)
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
