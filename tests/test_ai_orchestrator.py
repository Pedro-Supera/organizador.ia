from pathlib import Path

import ai_orchestrator as team


def test_task_handoff_and_status(tmp_path: Path) -> None:
    team.set_availability(tmp_path, "cline", "available", "sessão ativa")
    task = team.create_task(tmp_path, "Revisar testes", priority=1)
    claimed = team.claim_next_task(tmp_path, "cline")

    assert claimed is not None
    assert claimed["id"] == task["id"]

    finished = team.complete_task(tmp_path, task["id"], "cline", "Testes revisados.")
    assert finished["status"] == "done"
    assert "Nenhuma." in team.render_status(tmp_path)


def test_limited_agent_cannot_claim_task(tmp_path: Path) -> None:
    team.set_availability(tmp_path, "codex", "limited", "limite diário atingido")
    team.create_task(tmp_path, "Documentar fluxo")

    try:
        team.claim_next_task(tmp_path, "codex")
    except RuntimeError as error:
        assert "limited" in str(error)
    else:
        raise AssertionError("Codex limitado não deveria assumir tarefa.")


def test_decisions_are_auditable(tmp_path: Path) -> None:
    team.record_decision(tmp_path, "copilot", "Adicionar teste de regressão", "Evita retorno do bug.")
    assert "Adicionar teste de regressão" in team.render_status(tmp_path)
