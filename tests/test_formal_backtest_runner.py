from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from usfddk import formal_backtest_runner as runner
from usfddk.formal_backtest_readiness import FormalBacktestReadinessError
from usfddk.formal_backtest_readiness_validation import _write_risk_free_control
from usfddk.local_quarantine_intake import run_local_quarantine_intake
from usfddk.local_quarantine_intake_validation import CONTROL_REQUIREMENTS, _write_control_set

ROOT = Path(__file__).resolve().parents[1]


def _benchmark(*, factor: float = 1.0) -> pd.DataFrame:
    rows = []
    for asset in ("QQQ", "SPY"):
        for session, price in (("2026-01-02", 100.0), ("2026-01-05", 101.0)):
            rows.append(
                {
                    "asset_id": asset,
                    "session": session,
                    "open_raw": price,
                    "high_raw": price + 1,
                    "low_raw": price - 1,
                    "close_raw": price + 0.5,
                    "volume": "1000000",
                    "total_return_factor": str(factor),
                    "source_status": "observed",
                    "source_record_id": f"{asset}-{session}",
                }
            )
    return pd.DataFrame(rows)


def test_benchmark_factor_without_action_ledger_is_rejected() -> None:
    sessions = pd.DatetimeIndex(["2026-01-02", "2026-01-05"])
    with pytest.raises(runner.FormalBacktestRunnerError) as error:
        runner._benchmark_prices(_benchmark(factor=1.001), sessions)
    assert error.value.code == "benchmark_action_ledger_missing"


def test_combined_prices_filter_history_and_keep_observed_raw_rows() -> None:
    sessions = pd.DatetimeIndex(["2026-01-02", "2026-01-05"])
    stocks = pd.DataFrame(
        [
            {
                "security_id": "SEC-A",
                "session": "2025-12-31",
                "open_raw": "90",
                "close_raw": "91",
                "source_status": "observed",
            },
            {
                "security_id": "SEC-A",
                "session": "2026-01-02",
                "open_raw": "100",
                "close_raw": "101",
                "source_status": "observed",
            },
        ]
    )
    combined = runner._combine_prices(stocks, _benchmark(), sessions)
    assert set(combined["security_id"]) == {"SEC-A", "QQQ", "SPY"}
    assert len(combined) == 5
    assert combined["source_status"].eq("observed").all()


def test_synthetic_control_is_rejected_before_output_creation(tmp_path: Path) -> None:
    paths = _write_control_set(tmp_path / "source")
    run_local_quarantine_intake(
        paths["response"],
        paths["ciz"],
        paths["overlay"],
        paths["output"],
        root=ROOT,
        source_mode="synthetic_control",
        requirements=CONTROL_REQUIREMENTS,
    )
    risk_free = _write_risk_free_control(paths["output"], tmp_path / "risk-free")
    output = tmp_path / "formal-output"

    with pytest.raises(runner.FormalBacktestRunnerError) as error:
        runner.run_formal_backtest_once(
            paths["output"],
            risk_free,
            output,
            root=ROOT,
            source_mode="synthetic_control",
            requirements=CONTROL_REQUIREMENTS,
        )

    assert error.value.code == "formal_backtest_not_authorized"
    assert not output.exists()


def test_started_provider_run_keeps_failure_receipt_and_never_promotes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    output = tmp_path / "formal-output"
    readiness = {
        "formal_stock_backtest_authorized": True,
        "run_id": "a" * 64,
        "policy": {"statistics": {"global_search_trials": 6287}},
    }

    def fake_audit(*args, **kwargs):  # noqa: ANN001, ANN002 - test seam
        return readiness

    def fake_run(*args, **kwargs):  # noqa: ANN001, ANN002 - test seam
        raise runner.FormalBacktestRunnerError(
            "benchmark_action_ledger_missing", "synthetic failure"
        )

    monkeypatch.setattr(runner, "audit_formal_backtest_readiness", fake_audit)
    monkeypatch.setattr(runner, "_run_authorized", fake_run)

    with pytest.raises(runner.FormalBacktestRunnerError) as error:
        runner.run_formal_backtest_once(
            "/private/provider-package",
            "/private/risk-free",
            output,
            root=ROOT,
            source_mode="provider",
            release_firewall="/private/release-firewall",
        )

    assert error.value.code == "benchmark_action_ledger_missing"
    failure = json.loads((output / "run_failure.json").read_text(encoding="utf-8"))
    assert failure["status"] == "formal_backtest_failed_no_promotion"
    assert failure["paper_authorized"] is False
    assert failure["real_money_action_usd"] == 0
    assert (output.stat().st_mode & 0o777) == 0o700
    assert not (output / "run_summary.json").exists()


def test_readiness_failure_does_not_create_runner_output(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    output = tmp_path / "formal-output"

    def fake_audit(*args, **kwargs):  # noqa: ANN001, ANN002 - test seam
        raise FormalBacktestReadinessError("formal_prior_run_detected", "already used")

    monkeypatch.setattr(runner, "audit_formal_backtest_readiness", fake_audit)
    with pytest.raises(runner.FormalBacktestRunnerError) as error:
        runner.run_formal_backtest_once(
            "/private/provider-package",
            "/private/risk-free",
            output,
            root=ROOT,
        )
    assert error.value.code == "formal_prior_run_detected"
    assert not output.exists()
