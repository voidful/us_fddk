import json
import os
import subprocess
import textwrap
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_PATH = ROOT / ".github" / "workflows" / "daily-paper-update.yml"


def test_daily_update_dispatches_pages_only_after_a_successful_push() -> None:
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")

    assert "  actions: write" in workflow
    assert "        id: commit_update" in workflow
    assert 'echo "pushed=false" >> "$GITHUB_OUTPUT"' in workflow
    assert 'echo "pushed=true" >> "$GITHUB_OUTPUT"' in workflow
    assert "if: steps.commit_update.outputs.pushed == 'true'" in workflow
    assert "run: gh workflow run pages.yml --ref main" in workflow


def test_audited_observation_is_archived_before_later_validation_can_fail() -> None:
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")
    audit = workflow.index("      - name: Audit website and append the evidence chain\n")
    archive = workflow.index("      - name: Preserve audited LIVE observation\n")
    research = workflow.index("      - name: Verify research code\n")
    commit = workflow.index("      - name: Commit genuinely advanced market or source evidence\n")
    assert audit < archive < research < commit
    step = workflow[archive:research]
    assert "uses: actions/upload-artifact@" in step
    assert "github.run_id" in step and "github.run_attempt" in step
    assert "if: steps.live_update.outputs.data_advanced == 'true'" in step
    assert "if-no-files-found: error" in step
    assert "continue-on-error" not in step
    for path in (
        "artifacts/snapshot_v25_live_*.zip",
        "artifacts/paper_v25_state.json",
        "artifacts/paper_v25_spy_state.json",
        "artifacts/paper_v25_matched_state.json",
        "artifacts/v25_live_update_status.json",
        "artifacts/v25_live_evidence_ledger.jsonl",
        "site/data/trading-data.json",
    ):
        assert path in step


@pytest.mark.parametrize("data_advanced", [True, False, None, "true", 1])
def test_archive_condition_uses_the_actual_update_result(tmp_path, data_advanced) -> None:
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")
    step = workflow.split("      - name: Fetch the latest completed U.S. session\n", 1)[1]
    script = textwrap.dedent(step.split("        run: |\n", 1)[1].split("      - name:", 1)[0])
    fake_python = tmp_path / ".venv/bin/python"
    fake_python.parent.mkdir(parents=True)
    fake_python.write_text("#!/bin/sh\nexit 0\n")
    fake_python.chmod(0o755)
    artifacts = tmp_path / "artifacts"
    artifacts.mkdir()
    (artifacts / "v25_live_update_status.json").write_text(json.dumps({"data_advanced": data_advanced}))
    output = tmp_path / "output"
    result = subprocess.run(
        ["bash", "-e", "-o", "pipefail", "-c", script],
        cwd=tmp_path,
        env={**os.environ, "RUNNER_TEMP": str(tmp_path), "GITHUB_OUTPUT": str(output)},
        capture_output=True,
        text=True,
        check=False,
    )
    if isinstance(data_advanced, bool):
        assert result.returncode == 0, result.stderr
        assert output.read_text().splitlines() == [
            "outcome=updated_or_idempotent",
            f"data_advanced={str(data_advanced).lower()}",
        ]
    else:
        assert result.returncode == 1
        assert not output.exists() or not output.read_text()


def test_daily_update_exits_with_the_actual_continuity_failure(tmp_path) -> None:
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")
    step = workflow.split("      - name: Fetch the latest completed U.S. session\n", 1)[1]
    script = textwrap.dedent(step.split("        run: |\n", 1)[1].split("      - name:", 1)[0])
    fake_python = tmp_path / ".venv/bin/python"
    fake_python.parent.mkdir(parents=True)
    fake_python.write_text("#!/bin/sh\necho 'v25_live_continuity_gap: offline fixture'\nexit 2\n")
    fake_python.chmod(0o755)
    summary = tmp_path / "summary"
    output = tmp_path / "output"
    result = subprocess.run(
        ["bash", "-e", "-o", "pipefail", "-c", script],
        cwd=tmp_path,
        env={**os.environ, "RUNNER_TEMP": str(tmp_path), "GITHUB_OUTPUT": str(output),
             "GITHUB_STEP_SUMMARY": str(summary)},
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 2
    assert "v25_live_continuity_gap" in result.stdout
    assert "Manual continuity review is required" in summary.read_text()
    assert output.read_text().strip() == "outcome=continuity_blocked"
