"""Testes para o mailbox MCP: validação, deduplicação e concorrência."""
from __future__ import annotations

import json
import sys
import threading
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import mcp_organizador as mcp


def _setup_tmp(monkeypatch, tmp_path):
    """Redireciona BASE_DIR, WORKSPACE_DIR e MAILBOX_PATH para tmp_path."""
    ws = tmp_path / ".mcp_workspace"
    monkeypatch.setattr(mcp, "BASE_DIR", tmp_path)
    monkeypatch.setattr(mcp, "WORKSPACE_DIR", ws)
    monkeypatch.setattr(mcp, "MAILBOX_PATH", ws / "messages.json")


def test_campos_obrigatorios_presentes(monkeypatch, tmp_path):
    """Mensagens publicadas têm todos os campos obrigatórios."""
    _setup_tmp(monkeypatch, tmp_path)
    mcp.publicar_mensagem("a", "b", "c", "d")
    mensagens = json.loads(mcp.ler_mensagens("b"))
    assert len(mensagens) == 1
    assert mcp._CAMPOS_MENSAGEM <= set(mensagens[0].keys())
    assert mensagens[0]["lida"] is False


def test_deduplicacao_por_id(monkeypatch, tmp_path):
    """Remove duplicatas preservando ordem."""
    _setup_tmp(monkeypatch, tmp_path)
    mcp.publicar_mensagem("a", "b", "s1", "x")
    mcp.publicar_mensagem("a", "b", "s2", "y")
    mcp.publicar_mensagem("a", "b", "s3", "z")
    msgs = mcp._ler_mensagens()
    msgs.append(dict(msgs[0]))
    mcp._salvar_mensagens(msgs)
    assert len(mcp._ler_mensagens()) == 3


def test_ignora_registros_invalidos(monkeypatch, tmp_path):
    """Registros sem campos obrigatórios são descartados."""
    _setup_tmp(monkeypatch, tmp_path)
    tmp_path.joinpath(".mcp_workspace").mkdir()
    mcp.MAILBOX_PATH.write_text(json.dumps([
        {"id": "abc", "remetente": "a", "destinatario": "cline",
         "assunto": "ok", "conteudo": "t", "criado_em": "2026-01-01T00:00:00+00:00", "lida": False},
        {"id": "x", "remetente": "a"},  # faltam campos
        {"foo": "bar"},  # sem id
    ]), encoding="utf-8")
    msgs = mcp._ler_mensagens()
    assert len(msgs) == 1
    assert msgs[0]["id"] == "abc"


def test_leitura_filtra_por_destinatario(monkeypatch, tmp_path):
    _setup_tmp(monkeypatch, tmp_path)
    mcp.publicar_mensagem("a", "cline", "1", "x")
    mcp.publicar_mensagem("a", "copilot", "2", "y")
    mcp.publicar_mensagem("a", "todos", "3", "z")
    assert len(json.loads(mcp.ler_mensagens("cline"))) == 2
    assert len(json.loads(mcp.ler_mensagens("copilot"))) == 2


def test_apenas_nao_lidas(monkeypatch, tmp_path):
    _setup_tmp(monkeypatch, tmp_path)
    mcp.publicar_mensagem("a", "cline", "s1", "x")
    mcp.publicar_mensagem("a", "cline", "s2", "y")
    msgs = json.loads(mcp.ler_mensagens("cline", apenas_nao_lidas=True))
    assert len(msgs) == 2
    mcp.marcar_mensagem_lida(msgs[1]["id"])
    msgs2 = json.loads(mcp.ler_mensagens("cline", apenas_nao_lidas=True))
    assert len(msgs2) == 1


def test_marcar_como_lida_idempotente(monkeypatch, tmp_path):
    _setup_tmp(monkeypatch, tmp_path)
    mcp.publicar_mensagem("a", "cline", "s", "x")
    msg_id = json.loads(mcp.ler_mensagens("cline"))[0]["id"]
    r1 = mcp.marcar_mensagem_lida(msg_id)
    r2 = mcp.marcar_mensagem_lida(msg_id)
    assert "lida" in r1.lower()
    assert "lida" in r2.lower()
    r3 = mcp.marcar_mensagem_lida("id-inexistente")
    assert "não encontrada" in r3.lower() or "removida" in r3.lower()


def test_thread_safety_escrita_concorrente(monkeypatch, tmp_path):
    """Múltiplas threads publicando não devem corromper o mailbox."""
    _setup_tmp(monkeypatch, tmp_path)
    def pub(i):
        mcp.publicar_mensagem(f"r{i}", "todos", f"s{i}", f"c{i}")
    threads = [threading.Thread(target=pub, args=(i,)) for i in range(10)]
    for t in threads: t.start()
    for t in threads: t.join()
    assert len(mcp._ler_mensagens()) == 10


def test_ordenacao_mais_recente_primeiro(monkeypatch, tmp_path):
    _setup_tmp(monkeypatch, tmp_path)
    mcp.publicar_mensagem("a", "cline", "antiga", "x")
    mcp.publicar_mensagem("a", "cline", "nova", "y")
    msgs = json.loads(mcp.ler_mensagens("cline"))
    assert msgs[0]["assunto"] == "nova"
    assert msgs[1]["assunto"] == "antiga"


def test_solicitar_revisao_cria_handoff_valido(monkeypatch, tmp_path):
    _setup_tmp(monkeypatch, tmp_path)
    mcp.solicitar_revisao("X", "a.py", "Y", "pytest")
    msgs = json.loads(mcp.ler_mensagens("cline"))
    assert len(msgs) == 1
    c = msgs[0]["conteudo"]
    assert "Objetivo:" in c
    assert "Arquivos permitidos:" in c
    assert "Critérios de aceite:" in c
    assert "Comandos de validação:" in c
    assert msgs[0]["remetente"] == "copilot"


def test_mailbox_vazio_ou_ausente(monkeypatch, tmp_path):
    _setup_tmp(monkeypatch, tmp_path)
    assert mcp._ler_mensagens() == []
    mcp.MAILBOX_PATH.parent.mkdir(parents=True, exist_ok=True)
    mcp.MAILBOX_PATH.write_text("[]", encoding="utf-8")
    assert mcp._ler_mensagens() == []


def test_arquivo_corrompido_recupera(monkeypatch, tmp_path):
    """JSON inválido retorna lista vazia sem explodir."""
    _setup_tmp(monkeypatch, tmp_path)
    mcp.MAILBOX_PATH.parent.mkdir(parents=True, exist_ok=True)
    mcp.MAILBOX_PATH.write_text("{invalid json", encoding="utf-8")
    assert mcp._ler_mensagens() == []
