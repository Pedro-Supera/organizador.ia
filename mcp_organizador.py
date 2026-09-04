import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from mcp.server.mcpserver import MCPServer

mcp = MCPServer("OrganizadorInteligenteTools")

BASE_DIR = Path(__file__).parent.resolve()
WORKSPACE_DIR = BASE_DIR / ".mcp_workspace"
MAILBOX_PATH = WORKSPACE_DIR / "messages.json"


def _ler_mensagens() -> list[dict[str, object]]:
    if not MAILBOX_PATH.exists():
        return []
    try:
        dados = json.loads(MAILBOX_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    return dados if isinstance(dados, list) else []


def _salvar_mensagens(mensagens: list[dict[str, object]]) -> None:
    WORKSPACE_DIR.mkdir(parents=True, exist_ok=True)
    fd, caminho_temporario = tempfile.mkstemp(dir=WORKSPACE_DIR, prefix="messages-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as arquivo:
            json.dump(mensagens, arquivo, ensure_ascii=False, indent=2)
            arquivo.write("\n")
        os.replace(caminho_temporario, MAILBOX_PATH)
    finally:
        if os.path.exists(caminho_temporario):
            os.unlink(caminho_temporario)

@mcp.tool()
def ler_contexto() -> str:
    caminho = BASE_DIR / "contexto.txt"
    if caminho.exists():
        return caminho.read_text(encoding="utf-8")
    return "Arquivo contexto.txt não encontrado."

@mcp.tool()
def atualizar_contexto(novo_conteudo: str) -> str:
    caminho = BASE_DIR / "contexto.txt"
    caminho.write_text(novo_conteudo, encoding="utf-8")
    return "contexto.txt atualizado com sucesso!"

@mcp.tool()
def listar_arquivos_dist() -> str:
    pasta_dist = BASE_DIR / "dist"
    if not pasta_dist.exists():
        return "A pasta dist/ ainda não foi criada."
    
    arquivos = [f.name for f in pasta_dist.iterdir() if f.is_file()]
    if not arquivos:
        return "A pasta dist/ está vazia."
    
    return f"Arquivos encontrados em dist/: {', '.join(arquivos)}"


@mcp.tool()
def publicar_mensagem(remetente: str, destinatario: str, assunto: str, conteudo: str) -> str:
    """Publica uma mensagem persistente para outro agente do workspace."""
    mensagem = {
        "id": uuid4().hex,
        "remetente": remetente,
        "destinatario": destinatario,
        "assunto": assunto,
        "conteudo": conteudo,
        "criado_em": datetime.now(timezone.utc).isoformat(),
        "lida": False,
    }
    mensagens = _ler_mensagens()
    mensagens.append(mensagem)
    _salvar_mensagens(mensagens)
    return f"Mensagem publicada com id {mensagem['id']}."


@mcp.tool()
def ler_mensagens(destinatario: str, apenas_nao_lidas: bool = True) -> str:
    """Lê mensagens destinadas ao agente informado."""
    mensagens = [
        mensagem
        for mensagem in _ler_mensagens()
        if mensagem.get("destinatario") in {destinatario, "todos"}
        and (not apenas_nao_lidas or not mensagem.get("lida", False))
    ]
    return json.dumps(mensagens, ensure_ascii=False, indent=2)


@mcp.tool()
def marcar_mensagem_lida(mensagem_id: str) -> str:
    """Marca uma mensagem do mailbox como lida."""
    mensagens = _ler_mensagens()
    for mensagem in mensagens:
        if mensagem.get("id") == mensagem_id:
            mensagem["lida"] = True
            _salvar_mensagens(mensagens)
            return f"Mensagem {mensagem_id} marcada como lida."
    return f"Mensagem {mensagem_id} não encontrada."

if __name__ == "__main__":
    mcp.run()
