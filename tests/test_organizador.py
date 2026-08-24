from pathlib import Path

import organizador


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