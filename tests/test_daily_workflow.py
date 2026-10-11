import os
import subprocess
import textwrap
from pathlib import Path

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
