from pathlib import Path

import organizador


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


def test_extrair_texto_txt_latin1(tmp_path):
    caminho = tmp_path / "latin.txt"
    caminho.write_bytes("Ação e informação".encode("latin-1"))

    assert organizador.extrair_texto_txt(caminho) == "Ação e informação"


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