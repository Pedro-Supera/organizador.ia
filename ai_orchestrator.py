"""Estado compartilhado para colaboração entre Codex, Cline e Copilot.

Este módulo não chama nem armazena credenciais das plataformas. Ele mantém um
registro local, auditável e portátil para que outro agente possa continuar uma
tarefa quando um limite de uso for alcançado.
"""

from __future__ import annotations

import json
import os
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal
from uuid import uuid4

Agent = Literal["codex", "cline", "copilot"]
Availability = Literal["available", "limited", "unavailable", "unknown"]

AGENTS: tuple[Agent, ...] = ("codex", "cline", "copilot")
AVAILABILITY: tuple[Availability, ...] = ("available", "limited", "unavailable", "unknown")
STATE_FILE = ".ai-team-state.json"


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _default_state() -> dict[str, Any]:
    now = _now()
    return {
        "schema_version": 1,
        "agents": {
            agent: {"availability": "unknown", "note": "", "updated_at": now}
            for agent in AGENTS
        },
        "tasks": [],
        "decisions": [],
        "updated_at": now,
    }


def _state_path(project_dir: str | Path) -> Path:
    return Path(project_dir).expanduser().resolve() / STATE_FILE


def _validate_agent(agent: str) -> Agent:
    if agent not in AGENTS:
        raise ValueError(f"Agente inválido: {agent}. Use: {', '.join(AGENTS)}.")
    return agent  # type: ignore[return-value]


def load_state(project_dir: str | Path) -> dict[str, Any]:
    """Lê o estado local; arquivos ausentes ou inválidos começam vazios."""
    path = _state_path(project_dir)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict) and data.get("schema_version") == 1:
            default = _default_state()
            default.update(data)
            default["agents"] = {**default["agents"], **data.get("agents", {})}
            return default
    except (OSError, json.JSONDecodeError, TypeError):
        pass
    return _default_state()


def save_state(project_dir: str | Path, state: dict[str, Any]) -> Path:
    """Grava o estado atomicamente e restringe permissões em sistemas POSIX."""
    path = _state_path(project_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    state["updated_at"] = _now()
    descriptor, temporary = tempfile.mkstemp(prefix=".ai-team-", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as output:
            json.dump(state, output, ensure_ascii=False, indent=2, sort_keys=True)
            output.write("\n")
        os.replace(temporary, path)
        if os.name != "nt":
            os.chmod(path, 0o600)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    return path


def set_availability(project_dir: str | Path, agent: str, availability: str, note: str = "") -> dict[str, Any]:
    """Registra disponibilidade declarada, sem tentar ler créditos privados."""
    valid_agent = _validate_agent(agent)
    if availability not in AVAILABILITY:
        raise ValueError(f"Disponibilidade inválida: {availability}. Use: {', '.join(AVAILABILITY)}.")
    state = load_state(project_dir)
    state["agents"][valid_agent] = {
        "availability": availability,
        "note": note.strip()[:500],
        "updated_at": _now(),
    }
    save_state(project_dir, state)
    return state["agents"][valid_agent]


def create_task(
    project_dir: str | Path,
    title: str,
    description: str = "",
    preferred_agent: str | None = None,
    priority: int = 2,
) -> dict[str, Any]:
    """Adiciona uma tarefa a uma fila compartilhada."""
    if not title.strip():
        raise ValueError("O título da tarefa é obrigatório.")
    if preferred_agent is not None:
        _validate_agent(preferred_agent)
    if priority not in {1, 2, 3}:
        raise ValueError("A prioridade deve ser 1 (alta), 2 (normal) ou 3 (baixa).")
    state = load_state(project_dir)
    task = {
        "id": uuid4().hex[:12],
        "title": title.strip()[:200],
        "description": description.strip()[:2000],
        "preferred_agent": preferred_agent,
        "priority": priority,
        "status": "open",
        "claimed_by": None,
        "created_at": _now(),
        "updated_at": _now(),
    }
    state["tasks"].append(task)
    save_state(project_dir, state)
    return task


def claim_next_task(project_dir: str | Path, agent: str) -> dict[str, Any] | None:
    """Entrega a tarefa aberta mais prioritária para um agente disponível."""
    valid_agent = _validate_agent(agent)
    state = load_state(project_dir)
    availability = state["agents"][valid_agent].get("availability", "unknown")
    if availability in {"limited", "unavailable"}:
        raise RuntimeError(f"{valid_agent} está marcado como {availability}; atualize o estado antes de assumir tarefas.")
    candidates = [
        task for task in state["tasks"]
        if task.get("status") == "open"
        and task.get("preferred_agent") in {None, valid_agent}
    ]
    if not candidates:
        return None
    task = sorted(candidates, key=lambda item: (item["priority"], item["created_at"]))[0]
    task.update({"status": "in_progress", "claimed_by": valid_agent, "updated_at": _now()})
    save_state(project_dir, state)
    return task


def complete_task(project_dir: str | Path, task_id: str, agent: str, outcome: str) -> dict[str, Any]:
    """Fecha uma tarefa e preserva o resultado para o próximo agente."""
    valid_agent = _validate_agent(agent)
    state = load_state(project_dir)
    for task in state["tasks"]:
        if task.get("id") == task_id:
            if task.get("claimed_by") not in {None, valid_agent}:
                raise RuntimeError("A tarefa foi assumida por outro agente.")
            task.update({
                "status": "done",
                "claimed_by": valid_agent,
                "outcome": outcome.strip()[:4000],
                "updated_at": _now(),
            })
            save_state(project_dir, state)
            return task
    raise ValueError(f"Tarefa não encontrada: {task_id}")


def record_decision(project_dir: str | Path, agent: str, summary: str, rationale: str = "") -> dict[str, Any]:
    """Registra uma decisão técnica curta e auditável."""
    valid_agent = _validate_agent(agent)
    if not summary.strip():
        raise ValueError("O resumo da decisão é obrigatório.")
    state = load_state(project_dir)
    decision = {
        "id": uuid4().hex[:12],
        "agent": valid_agent,
        "summary": summary.strip()[:1000],
        "rationale": rationale.strip()[:2000],
        "created_at": _now(),
    }
    state["decisions"].append(decision)
    state["decisions"] = state["decisions"][-100:]
    save_state(project_dir, state)
    return decision


def render_status(project_dir: str | Path) -> str:
    """Produz um resumo legível para chat, contexto e auditoria."""
    state = load_state(project_dir)
    lines = ["# Estado da equipe de IAs", "", "## Disponibilidade"]
    for agent in AGENTS:
        item = state["agents"][agent]
        suffix = f" — {item.get('note')}" if item.get("note") else ""
        lines.append(f"- {agent}: **{item.get('availability', 'unknown')}**{suffix}")
    open_tasks = [task for task in state["tasks"] if task.get("status") != "done"]
    lines.extend(["", "## Tarefas abertas"])
    if open_tasks:
        for task in sorted(open_tasks, key=lambda item: (item["priority"], item["created_at"])):
            owner = task.get("claimed_by") or "não assumida"
            lines.append(f"- P{task['priority']} · {task['id']} · {task['title']} ({owner})")
    else:
        lines.append("- Nenhuma.")
    lines.extend(["", "## Últimas decisões"])
    for decision in state["decisions"][-5:]:
        lines.append(f"- [{decision['agent']}] {decision['summary']}")
    if not state["decisions"]:
        lines.append("- Nenhuma.")
    return "\n".join(lines) + "\n"
