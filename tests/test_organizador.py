import os
import threading
from pathlib import Path
import warnings

import app
import organizador
import pytest
from unittest.mock import patch, MagicMock


class LoggerDeTeste:
    def __init__(self):
        self.mensagens = []

    def info(self, mensagem):
        self.mensagens.append(("info", mensagem))

    def warning(self, mensagem):
        self.mensagens.append(("warning", mensagem))

    def error(self, mensagem):
        self.mensagens.append(("error", mensagem))


def test_obter_categoria_case_insensitive():
    assert organizador.obter_categoria(".DOCX") == "documentos"
    assert organizador.obter_categoria(".desconhecido") == "outros"


def test_sanitizar_nome_caminho_remove_path_traversal():
    assert organizador.sanitizar_nome_caminho("../../subpasta") == "______subpasta"
    assert organizador.sanitizar_nome_caminho("pasta/teste") == "pasta_teste"


def test_listar_arquivos_elegiveis(tmp_path):
    (tmp_path / "zeta.txt").touch()
    (tmp_path / "Alfa.txt").touch()
    (tmp_path / ".env").touch()
    (tmp_path / "organizador.py").touch()
    (tmp_path / ".oculta").mkdir()

    arquivos = organizador.listar_arquivos_elegiveis(tmp_path)
    limitados = organizador.listar_arquivos_elegiveis(tmp_path, max_files=1)

    assert [arquivo.name for arquivo in arquivos] == ["Alfa.txt", "zeta.txt"]
    assert [arquivo.name for arquivo in limitados] == ["Alfa.txt"]


def test_salvar_chave_api_permissoes(tmp_path, monkeypatch):
    caminho_env = tmp_path / ".env"
    monkeypatch.setattr(organizador, "caminho_env_gravavel", lambda: caminho_env)

    assert organizador.salvar_chave_api("chave-de-teste") is True
    assert os.environ["GROQ_API_KEY"] == "chave-de-teste"
    if os.name != "nt":
        assert os.stat(caminho_env).st_mode & 0o777 == 0o600


def test_extrair_texto_txt_latin1(tmp_path):
    caminho = tmp_path / "latin.txt"
    caminho.write_bytes("Ação e informação".encode("latin-1"))

    assert organizador.extrair_texto_txt(caminho) == "Ação e informação"


def test_extrair_texto_limita_tamanho_maximo(tmp_path):
    caminho = tmp_path / "grande.txt"
    caminho.write_text("x" * 60_000, encoding="utf-8")

    texto = organizador.extrair_texto(caminho)

    assert len(texto) == organizador.MAX_TEXTO_LEITURA == 50_000


@patch("organizador.Groq")
def test_gerar_resumo_sucesso(mock_groq):
    mock_groq.return_value.chat.completions.create.return_value.choices[0].message.content = "Resumo simulado com sucesso"

    resultado = organizador.gerar_resumo("Texto de teste", api_key="chave_fake")

    assert resultado == "Resumo simulado com sucesso"


@patch("organizador.Groq")
@patch("time.sleep")
def test_gerar_resumo_falha_persistente_com_retry(mock_sleep, mock_groq):
    mock_groq.return_value.chat.completions.create.side_effect = RuntimeError("falha temporaria")

    resultado = organizador.gerar_resumo("Texto de teste", api_key="chave_fake")

    assert resultado is None
    assert mock_sleep.called


def test_extrair_texto_docx(tmp_path):
    from docx import Document

    caminho = tmp_path / "nota.docx"
    documento = Document()
    documento.add_paragraph("Conteúdo do documento")
    documento.save(caminho)

    assert organizador.extrair_texto_docx(caminho) == "Conteúdo do documento"


def test_dry_run_ignora_arquivos_internos_e_nao_cria_pastas(tmp_path):
    (tmp_path / ".env").write_text("GROQ_API_KEY=segredo", encoding="utf-8")
    (tmp_path / "app.py").write_text("arquivo interno", encoding="utf-8")
    (tmp_path / "relatorio.txt").write_text("relatório", encoding="utf-8")

    organizador.organizar_pasta(tmp_path, dry_run=True, no_ai=True)

    assert not (tmp_path / "documentos").exists()
    assert (tmp_path / "relatorio.txt").exists()


def test_organizar_pasta_dry_run_nao_move_arquivos(tmp_path):
    arquivo = tmp_path / "relatorio.txt"
    arquivo.write_text("relatorio", encoding="utf-8")

    organizador.organizar_pasta(tmp_path, dry_run=True, no_ai=True)

    assert arquivo.exists()
    assert not (tmp_path / "documentos" / arquivo.name).exists()


def test_destino_incremental(tmp_path):
    destino = tmp_path / "arquivo.pdf"
    destino.touch()
    (tmp_path / "arquivo_1.pdf").touch()

    assert organizador.proximo_destino(destino).name == "arquivo_2.pdf"


def test_max_files_limita_processamento(tmp_path):
    for nome in ("a.txt", "b.txt", "c.txt"):
        (tmp_path / nome).write_text("conteúdo", encoding="utf-8")

    organizador.organizar_pasta(tmp_path, dry_run=False, no_ai=True, max_files=2)

    assert len(list((tmp_path / "documentos").iterdir())) == 2
    assert (tmp_path / "c.txt").exists()


def test_logger_injetado_recebe_relatorio(tmp_path):
    logger = LoggerDeTeste()
    (tmp_path / "nota.txt").write_text("conteúdo", encoding="utf-8")

    organizador.organizar_pasta(tmp_path, no_ai=True, logger=logger)

    assert any("Concluído" in mensagem for _, mensagem in logger.mensagens)


def test_falha_de_io_ao_mover_e_registrada(tmp_path, monkeypatch):
    logger = LoggerDeTeste()
    arquivo = tmp_path / "nota.txt"
    arquivo.write_text("conteúdo", encoding="utf-8")

    def mover_com_falha(*args):
        raise OSError("disco somente leitura")

    monkeypatch.setattr(organizador.shutil, "move", mover_com_falha)
    organizador.organizar_pasta(tmp_path, no_ai=True, logger=logger)

    assert any("somente leitura" in mensagem for nivel, mensagem in logger.mensagens if nivel == "error")


def test_cancelar_futuros_solicita_cancelamento():
    class Futuro:
        def __init__(self):
            self.cancelado = False

        def cancel(self):
            self.cancelado = True

    futuros = [Futuro(), Futuro()]
    organizador.cancelar_futuros(futuros)

    assert all(futuro.cancelado for futuro in futuros)


def test_cancelamento_interrompe_resumos_e_lanca_excecao(tmp_path, monkeypatch):
    cancel_event = threading.Event()
    for nome in ("a.txt", "b.txt"):
        (tmp_path / nome).write_text("texto suficiente para gerar um resumo com a IA. " * 2, encoding="utf-8")

    def gerar_resumo_cancelando(*args, **kwargs):
        cancel_event.set()
        return "resumo"

    monkeypatch.setenv("GROQ_API_KEY", "chave-de-teste")
    monkeypatch.setattr(organizador, "Groq", lambda **kwargs: object())
    monkeypatch.setattr(organizador, "gerar_resumo", gerar_resumo_cancelando)

    with pytest.raises(organizador.OperacaoCancelada):
        organizador.organizar_pasta(tmp_path, model="modelo-teste", cancel_event=cancel_event)


def test_pdf_escaneado_gera_alerta(tmp_path, monkeypatch):
    class Pagina:
        def extract_text(self):
            return ""

    class Leitor:
        pages = [Pagina()]

    logger = LoggerDeTeste()
    caminho = tmp_path / "scan.pdf"
    caminho.write_bytes(b"0" * (51 * 1024))
    monkeypatch.setattr(organizador, "PdfReader", lambda _: Leitor())

    assert organizador.extrair_texto_pdf(caminho, logger) == ""
    assert any("escaneado" in mensagem for _, mensagem in logger.mensagens)


def test_novas_extensoes_de_texto(tmp_path):
    html = tmp_path / "pagina.html"
    csv = tmp_path / "dados.csv"
    html.write_text("<h1>Título</h1><p>Conteúdo</p>", encoding="utf-8")
    csv.write_text("nome,valor\nproduto,10", encoding="utf-8")

    assert organizador.extrair_texto(html) == "Título Conteúdo"
    assert organizador.extrair_texto(csv) == "nome | valor\nproduto | 10"
    assert organizador.obter_categoria(".html") == "documentos"
    assert organizador.obter_categoria(".pptx") == "documentos"


def test_fluxo_retorna_estatisticas_e_processa_csv(tmp_path):
    csv = tmp_path / "dados.csv"
    csv.write_text("nome,valor\nproduto,10", encoding="utf-8")
    recebidos = []

    resultado = organizador.organizar_pasta(
        tmp_path,
        no_ai=True,
        estatisticas=recebidos.append,
    )

    assert resultado["movidos"] == 1
    assert resultado["por_categoria"] == {"planilhas": 1}
    assert recebidos == [resultado]
    assert (tmp_path / "planilhas" / "dados.csv").exists()


def test_sanitizacao_de_max_files():
    assert app.validar_max_files(" 12 ") == 12
    assert app.validar_max_files(" ") is None
    for valor in ("0", "-1", "abc"):
        try:
            app.validar_max_files(valor)
        except ValueError:
            pass
        else:
            raise AssertionError("Valor inválido foi aceito")


def test_log_pode_ser_limpo_e_exportado(tmp_path, monkeypatch):
    janela = app.ctk.CTk()
    try:
        log = app.ConsoleLogFrame(janela)
        log.adicionar("[12:00:00] INFO: teste")
        log.limpar()
        assert log.caixa.get("1.0", "end-1c") == ""
        destino = tmp_path / "log.txt"
        monkeypatch.setattr(app.filedialog, "asksaveasfilename", lambda **_: str(destino))
        log.adicionar("linha exportada")
        log.exportar()
        assert destino.read_text(encoding="utf-8").strip() == "linha exportada"
    finally:
        janela.destroy()


def test_importacoes_nao_geram_deprecation_warning():
    with warnings.catch_warnings(record=True) as capturados:
        warnings.simplefilter("always", DeprecationWarning)
        __import__("organizador")
        __import__("app")
    assert not [warning for warning in capturados if issubclass(warning.category, DeprecationWarning)]