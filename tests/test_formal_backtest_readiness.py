import json
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.build_short_term_formal_backtest_readiness_report import _site_summary
from usfddk.formal_backtest_readiness import (
    FORMAL_BASELINES,
    FORMAL_GLOBAL_SEARCH_TRIALS,
    FORMAL_PBO_PATHS,
    FORMAL_PREREGISTRATION_PROTOCOL_SHA256,
    FORMAL_READINESS_VERSION,
    FormalBacktestReadinessError,
    audit_formal_backtest_readiness,
)
from usfddk.formal_backtest_readiness_validation import (
    run_formal_backtest_readiness_validation,
)

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def result() -> dict:
    return run_formal_backtest_readiness_validation(ROOT)


def test_round18_controls_and_attacks_are_exact(result: dict) -> None:
    assert result["status"] == (
        "formal_preregistration_and_synthetic_readiness_controls_passed_inputs_missing"
    )
    assert result["readiness_version"] == FORMAL_READINESS_VERSION
    assert result["synthetic_control"]["gate_summary"] == {
        "passed": 18,
        "total": 18,
        "all_passed": True,
    }
    assert result["attack_summary"] == {
        "rejected": 18,
        "total": 18,
        "all_rejected": True,
    }
    assert [row["id"] for row in result["synthetic_control"]["gates"]] == [
        f"{index:02d}" for index in range(1, 19)
    ]
    assert all(
        row["rejected"]
        and row["observed_error_code"] == row["expected_error_code"]
        for row in result["attacks"]
    )


def test_formal_policy_is_frozen_before_results(result: dict) -> None:
    policy = result["synthetic_control"]["policy"]
    assert policy["baselines"] == list(FORMAL_BASELINES)
    assert policy["baselines"][-1] == "first_top10_equal_then_drift"
    assert policy["statistics"]["global_search_trials"] == FORMAL_GLOBAL_SEARCH_TRIALS
    assert policy["statistics"]["pbo_paths"] == list(FORMAL_PBO_PATHS)
    assert policy["execution"]["costs_bps"] == [10, 25, 50]
    assert policy["execution"]["starting_capital_usd"] == 1_000
    assert policy["execution"]["cash_return_policy"] == (
        "zero_percent_uninvested_cash"
    )
    assert result["protocol_integrity"]["passed"] is True
    assert len(result["protocol_integrity"]["hash_checks"]) == 13
    assert all(result["protocol_integrity"]["hash_checks"].values())
    assert FORMAL_PREREGISTRATION_PROTOCOL_SHA256 == (
        "4534130e245c97b6718e21a658708bd763c7046317a2b355c09b2589a8a3e083"
    )


def test_synthetic_control_never_promotes_formal_or_paper(result: dict) -> None:
    control = result["synthetic_control"]
    assert control["formal_stock_backtest_authorized"] is False
    assert control["contains_provider_rows"] is False
    assert control["run_id_bound"] is True
    assert result["formal_stock_backtest_input_ready"] is False
    assert result["formal_stock_backtest_completed"] is False
    assert result["strategy_run_count"] == 0
    assert result["paper"] == {
        "authorized": False,
        "state": "all_cash",
        "backfilled_trades": 0,
        "positions": [],
    }
    assert result["real_money_action_usd"] == 0


def test_production_entrypoint_rejects_relative_paths_before_reading() -> None:
    with pytest.raises(FormalBacktestReadinessError) as error:
        audit_formal_backtest_readiness(
            "package",
            "/private/does-not-matter-risk-free",
            "/private/does-not-matter-output",
            root=ROOT,
            source_mode="provider",
        )
    assert error.value.code == "formal_path_boundary_invalid"


def test_provider_mode_requires_release_firewall_before_formal_readiness(
    tmp_path: Path,
) -> None:
    package = tmp_path / "package"
    risk_free = tmp_path / "risk-free"
    output = tmp_path / "output"
    package.mkdir()
    risk_free.mkdir()
    with pytest.raises(FormalBacktestReadinessError) as error:
        audit_formal_backtest_readiness(
            package,
            risk_free,
            output,
            root=ROOT,
            source_mode="provider",
        )
    assert error.value.code == "formal_provider_mode_required"
    assert "release firewall" in error.value.detail


def test_cli_is_provider_only_and_does_not_offer_strategy_switches() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/validate_short_term_formal_backtest_readiness.py"),
            "--help",
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    assert "--package" in completed.stdout
    assert "--risk-free-bundle" in completed.stdout
    assert "--release-firewall" in completed.stdout
    assert "--output" in completed.stdout
    assert "--mode" not in completed.stdout
    assert "--trials" not in completed.stdout
    assert "--cost" not in completed.stdout


def test_actual_state_remains_unpromoted(result: dict) -> None:
    assert result["actual_formal_readiness"] == {
        "passed": 1,
        "total": 18,
        "all_passed": False,
        "only_passed_gate": "01_preregistration_integrity",
    }
    assert result["actual_point_in_time_readiness"] == {
        "passed": 1,
        "total": 20,
        "all_passed": False,
    }
    assert result["actual_local_intake"]["passed"] == 1
    assert result["authorized_provider_package_received"] is False
    assert result["risk_free_provider_input_received"] is False
    assert result["provider_readiness_run_count"] == 0


def test_committed_machine_and_site_receipts_match_round18(result: dict) -> None:
    machine = json.loads(
        (
            ROOT / "artifacts/short_term_formal_backtest_readiness_validation.json"
        ).read_text(encoding="utf-8")
    )
    site = json.loads(
        (
            ROOT / "site/data/short-term-formal-backtest-readiness.json"
        ).read_text(encoding="utf-8")
    )
    assert machine == result
    assert site == _site_summary(result)
