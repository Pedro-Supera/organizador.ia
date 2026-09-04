"""Servidor MCP local do Organizador Inteligente.

Use este servidor no Cline e no Codex para compartilhar contexto e coordenar
tarefas. O Copilot não expõe uma API de consumo MCP universal; por isso ele usa
os mesmos arquivos de estado e contexto no workspace.
"""

from pathlib import Path

from mcp.server.fastmcp import FastMCP

import ai_orchestrator

mcp = FastMCP("OrganizadorInteligenteTools")
BASE_DIR = Path(__file__).parent.resolve()
CONTEXTO = BASE_DIR / "contexto.txt"


def _sync_context() -> None:
    """Acrescenta o estado atual ao contexto sem apagar a documentação existente."""
    marker = "\n\n<!-- AI_TEAM_STATUS -->\n"
    original = CONTEXTO.read_text(encoding="utf-8") if CONTEXTO.exists() else "# Contexto do Projeto\n"
    base = original.split(marker, 1)[0].rstrip()
    CONTEXTO.write_text(base + marker + ai_orchestrator.render_status(BASE_DIR), encoding="utf-8")


@mcp.tool()
def ler_contexto() -> str:
    """Lê a documentação técnica e o estado compartilhado da equipe."""
    _sync_context()
    return CONTEXTO.read_text(encoding="utf-8")


@mcp.tool()
def atualizar_contexto(novo_conteudo: str) -> str:
    """Substitui a documentação do projeto; o status da equipe é recriado."""
    CONTEXTO.write_text(novo_conteudo.strip() + "\n", encoding="utf-8")
    _sync_context()
    return "contexto.txt atualizado com sucesso."


@mcp.tool()
def status_equipe_ia() -> str:
    """Mostra disponibilidade, tarefas abertas e decisões recentes."""
    return ai_orchestrator.render_status(BASE_DIR)


@mcp.tool()
def definir_disponibilidade_ia(agente: str, disponibilidade: str, observacao: str = "") -> str:
    """Marca codex, cline ou copilot como available, limited, unavailable ou unknown."""
    ai_orchestrator.set_availability(BASE_DIR, agente, disponibilidade, observacao)
    _sync_context()
    return f"Disponibilidade de {agente} atualizada para {disponibilidade}."


@mcp.tool()
def criar_tarefa_ia(titulo: str, descricao: str = "", agente_preferido: str = "", prioridade: int = 2) -> str:
    """Cria uma tarefa compartilhada; prioridade 1 é a mais alta."""
    task = ai_orchestrator.create_task(BASE_DIR, titulo, descricao, agente_preferido or None, prioridade)
    _sync_context()
    return f"Tarefa criada: {task['id']} — {task['title']}."


@mcp.tool()
def assumir_proxima_tarefa_ia(agente: str) -> str:
    """Permite que um agente disponível assuma a próxima tarefa compatível."""
    task = ai_orchestrator.claim_next_task(BASE_DIR, agente)
    _sync_context()
    return "Não há tarefa aberta compatível." if task is None else f"Tarefa assumida: {task['id']} — {task['title']}."


@mcp.tool()
def concluir_tarefa_ia(id_tarefa: str, agente: str, resultado: str) -> str:
    """Conclui uma tarefa e registra o resultado para o próximo agente."""
    task = ai_orchestrator.complete_task(BASE_DIR, id_tarefa, agente, resultado)
    _sync_context()
    return f"Tarefa concluída: {task['id']}."


@mcp.tool()
def registrar_decisao_ia(agente: str, resumo: str, justificativa: str = "") -> str:
    """Registra uma decisão técnica curta e auditável."""
    decision = ai_orchestrator.record_decision(BASE_DIR, agente, resumo, justificativa)
    _sync_context()
    return f"Decisão registrada: {decision['id']}."


@mcp.tool()
def listar_arquivos_dist() -> str:
    """Lista executáveis compilados, quando existirem."""
    pasta_dist = BASE_DIR / "dist"
    if not pasta_dist.exists():
        return "A pasta dist/ ainda não foi criada."
    arquivos = [file.name for file in pasta_dist.iterdir() if file.is_file()]
    return f"Arquivos encontrados em dist/: {', '.join(arquivos)}" if arquivos else "A pasta dist/ está vazia."


if __name__ == "__main__":
    mcp.run()
