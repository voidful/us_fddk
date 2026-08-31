from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = (
    ROOT / ".github/workflows/pages.yml",
    ROOT / ".github/workflows/daily-paper-update.yml",
)
FORM4_CONTRACT_CI = ROOT / ".github/workflows/form4-contract-ci.yml"


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
def test_setup_uv_action_uses_a_resolvable_release(workflow: Path) -> None:
    text = workflow.read_text(encoding="utf-8")
    assert "astral-sh/setup-uv@v9.0.0" in text
    assert "astral-sh/setup-uv@v9\n" not in text


def test_pages_deploys_only_from_main_while_branch_builds_remain_available() -> None:
    text = (ROOT / ".github/workflows/pages.yml").read_text(encoding="utf-8")
    build_start = text.index("  build:\n")
    deploy_start = text.index("  deploy:\n")

    assert "workflow_dispatch:" in text
    assert "github.ref == 'refs/heads/main'" not in text[build_start:deploy_start]
    assert (
        "  deploy:\n"
        "    if: github.ref == 'refs/heads/main'\n"
        "    environment:\n"
    ) in text


@pytest.mark.parametrize("workflow", WORKFLOWS, ids=lambda path: path.name)
def test_research_workflow_keeps_the_frozen_output_diff_guard(workflow: Path) -> None:
    text = workflow.read_text(encoding="utf-8")
    assert "git diff --exit-code" in text
    assert "artifacts/short_term_formal_backtest_readiness_validation.json" in text


@pytest.mark.parametrize("workflow", WORKFLOWS, ids=lambda path: path.name)
def test_full_research_jobs_keep_the_verified_sixty_minute_budget(workflow: Path) -> None:
    text = workflow.read_text(encoding="utf-8")
    assert len(re.findall(r"^\s{4}timeout-minutes: 60$", text, re.MULTILINE)) == 1
    assert "timeout-minutes: 45" not in text


def test_live_refresh_skips_rebuild_when_no_session_is_added() -> None:
    text = (ROOT / "scripts/refresh_live_reference.sh").read_text(encoding="utf-8")
    assert 'update_status_path="$project_dir/artifacts/v25_live_update_status.json"' in text
    assert 'case "$data_advanced" in' in text
    assert 'true)' in text and '"$python_bin" -m usfddk build "$@"' in text
    assert "skipping full build to preserve website/report idempotence" in text
    assert "Invalid v25 LIVE data_advanced value" in text


def test_frozen_parent_receipt_is_validated_before_dependent_rebuild() -> None:
    for workflow in WORKFLOWS:
        text = workflow.read_text(encoding="utf-8")
        round39 = text.index("scripts/build_short_term_leader_pullback_rebound_report.py")
        disclosure = text.index("scripts/build_short_term_disclosure_readiness_report.py")
        round38 = text.index("scripts/build_short_term_multi_window_resonance_report.py")
        round30 = text.index("scripts/build_short_term_qqq_replacement_overlay_report.py")
        round29 = text.index("scripts/build_short_term_calendar_capital_accounting_report.py")
        round28 = text.index("scripts/build_short_term_reversal_volatility_attribution_report.py")
        assert round39 < disclosure < round38 < round30 < round29 < round28, workflow.name
        round39_test = text.index("pytest tests/test_leader_pullback_rebound.py")
        round39_report_test = text.index(
            "pytest tests/test_leader_pullback_rebound_report.py"
        )
        disclosure_protocol_test = text.index(
            "pytest tests/test_disclosure_known_at_protocol.py"
        )
        disclosure_core_test = text.index("pytest tests/test_disclosure_known_at.py")
        disclosure_report_test = text.index(
            "pytest tests/test_disclosure_readiness_report.py"
        )
        round38_test = text.index("pytest tests/test_multi_window_resonance.py")
        round38_report_test = text.index(
            "pytest tests/test_multi_window_resonance_report.py"
        )
        round30_test = text.index("pytest tests/test_qqq_replacement_overlay.py")
        round29_test = text.index("pytest tests/test_calendar_capital_accounting.py")
        round28_test = text.index("pytest tests/test_reversal_volatility_attribution.py")
        assert (
            round39_test
            < round39_report_test
            < disclosure_protocol_test
            < disclosure_core_test
            < disclosure_report_test
            < round38_test
            < round38_report_test
            < round30_test
            < round29_test
            < round28_test
        ), workflow.name
        assert "artifacts/short_term_leader_pullback_rebound_validation.json" in text
        assert "site/data/short-term-leader-pullback-rebound.json" in text
        assert "docs/SHORT_TERM_LEADER_PULLBACK_REBOUND_RESEARCH_REPORT.md" in text
        assert "artifacts/short_term_disclosure_readiness.json" in text
        assert "site/data/short-term-disclosure-readiness.json" in text
        assert "docs/SHORT_TERM_DISCLOSURE_READINESS_REPORT.md" in text
        assert "artifacts/short_term_multi_window_resonance_validation.json" in text
        assert "site/data/short-term-multi-window-resonance.json" in text
        assert "docs/SHORT_TERM_MULTI_WINDOW_RESONANCE_RESEARCH_REPORT.md" in text


@pytest.mark.parametrize("workflow", WORKFLOWS, ids=lambda path: path.name)
def test_numerical_receipt_rebuild_uses_the_frozen_execution_contract(workflow: Path) -> None:
    text = workflow.read_text(encoding="utf-8")
    expected = {
        "OPENBLAS_CORETYPE": "HASWELL",
        "OPENBLAS_NUM_THREADS": "1",
        "OMP_NUM_THREADS": "1",
        "MKL_NUM_THREADS": "1",
        "NUMEXPR_NUM_THREADS": "1",
        "PYTHONHASHSEED": "0",
    }
    for name, value in expected.items():
        assert re.search(rf"^\s+{name}: [\"']?{value}[\"']?\s*$", text, re.MULTILINE), (
            workflow.name,
            name,
        )


def test_formal_release_firewall_is_rebuilt_and_diff_guarded() -> None:
    for workflow in WORKFLOWS:
        text = workflow.read_text(encoding="utf-8")
        assert "scripts/build_short_term_restatement_firewall.py" in text
        assert "scripts/build_short_term_formal_release_integration.py" in text
        assert "tests/test_restatement_firewall.py" in text
        assert "tests/test_formal_release_integration.py" in text
        assert "site/data/short-term-restatement-firewall.json" in text
        assert "site/data/short-term-formal-release-integration.json" in text


def test_effective_form4_v1_1_supersession_suite_is_mandatory_in_both_workflows() -> None:
    required = (
        "tests/test_form4_multipath_reconciliation_v2.py",
        "tests/test_form4_forward_admission_contract.py",
        "tests/test_form4_multipath_forward_protocol_amendment_v1_1.py",
    )
    for workflow in WORKFLOWS:
        text = workflow.read_text(encoding="utf-8")
        positions = [text.index(path) for path in required]
        assert positions[0] < positions[1] < positions[2], workflow.name
        for forbidden in (
            "tests/test_form4_multipath_index.py",
            "tests/test_form4_forward_contract.py",
            "tests/test_form4_multipath_forward_protocol.py",
        ):
            assert forbidden not in text, workflow.name


def test_form4_contract_has_read_only_pull_request_ci() -> None:
    text = FORM4_CONTRACT_CI.read_text(encoding="utf-8")
    assert "  pull_request:\n" in text
    assert "    paths:\n" not in text
    assert "permissions:\n  contents: read\n" in text
    assert "write" not in text
    assert "uv sync --locked --extra dev" in text
    assert "git diff --exit-code" in text
    assert "tests/test_form4_forward_contract.py" not in text
    assert (
        "--deselect=tests/test_form4_admission_collection_authorization.py::"
        "test_authorization_drift_fails_even_with_recomputed_receipt_hash"
    ) in text
    for required in (
        "tests/test_ci_runtime_contract.py",
        "tests/test_form4_multipath_reconciliation_v2.py",
        "tests/test_form4_forward_admission_contract.py",
        "tests/test_form4_multipath_forward_protocol_amendment_v1_1.py",
    ):
        assert required in text


def test_provider_evidence_refresh_receipt_is_rebuilt_and_tested() -> None:
    for workflow in WORKFLOWS:
        text = workflow.read_text(encoding="utf-8")
        assert "scripts/build_short_term_provider_evidence_refresh_report.py" in text
        assert "tests/test_provider_evidence_refresh.py" in text
        assert "tests/test_provider_evidence_refresh_report.py" in text
        assert "artifacts/short_term_provider_evidence_refresh.json" in text
        assert "site/data/short-term-provider-evidence-refresh.json" in text
        assert "docs/SHORT_TERM_PROVIDER_EVIDENCE_REFRESH_REPORT.md" in text


def test_treasury_bridge_report_is_deterministic_and_locked() -> None:
    for workflow in WORKFLOWS:
        text = workflow.read_text(encoding="utf-8")
        assert "scripts/build_short_term_rf_treasury_bridge_report.py" in text
        assert "tests/test_risk_free_treasury_bridge.py" in text
        assert "tests/test_risk_free_treasury_bridge_report.py" in text
        assert "artifacts/short_term_rf_treasury_bridge.json" in text
        assert "site/data/short-term-rf-treasury-bridge.json" in text
        assert "docs/SHORT_TERM_RF_TREASURY_BRIDGE_REPORT.md" in text
