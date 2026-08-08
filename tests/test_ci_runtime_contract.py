from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = (
    ROOT / ".github/workflows/pages.yml",
    ROOT / ".github/workflows/daily-paper-update.yml",
)


@pytest.mark.parametrize("workflow", WORKFLOWS, ids=lambda path: path.name)
def test_project_commands_use_the_locked_python_runtime(workflow: Path) -> None:
    """Keep CI reproducible: no workflow step may fall back to runner Python."""

    text = workflow.read_text(encoding="utf-8")
    assert "uv sync --locked --extra dev" in text
    assert "./.venv/bin/python" in text

    bare_project_commands = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        if re.search(r"(?:^|[\s|!])python(?:\s|$)", line) and "./.venv/bin/python" not in line:
            bare_project_commands.append(f"{workflow.name}:{line_number}: {line.strip()}")
    assert not bare_project_commands, "\n".join(bare_project_commands)


@pytest.mark.parametrize("workflow", WORKFLOWS, ids=lambda path: path.name)
def test_research_workflow_keeps_the_frozen_output_diff_guard(workflow: Path) -> None:
    text = workflow.read_text(encoding="utf-8")
    assert "git diff --exit-code" in text
    assert "artifacts/short_term_formal_backtest_readiness_validation.json" in text


def test_live_refresh_skips_rebuild_when_no_session_is_added() -> None:
    text = (ROOT / "scripts/refresh_live_reference.sh").read_text(encoding="utf-8")
    assert 'update_status_path="$project_dir/artifacts/v25_live_update_status.json"' in text
    assert 'case "$data_advanced" in' in text
    assert 'true)' in text and '"$python_bin" -m usfddk build "$@"' in text
    assert "skipping full build to preserve website/report idempotence" in text
    assert "Invalid v25 LIVE data_advanced value" in text
