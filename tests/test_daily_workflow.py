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
