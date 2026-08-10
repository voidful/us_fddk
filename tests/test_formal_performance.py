from __future__ import annotations

import pandas as pd
import pytest

from usfddk.formal_baseline_schedule import FORMAL_BASELINE_KEYS
from usfddk.formal_performance import (
    FormalPerformanceError,
    compare_account_to_baseline,
    compare_formal_paths,
    compute_formal_metrics,
)
from usfddk.formal_raw_accounting import RawAccountingResult

DATES = ["2026-01-02", "2026-01-05", "2026-01-06", "2026-01-07", "2026-01-08"]


def _account(values: list[float], *, trades: list[dict[str, object]] | None = None) -> RawAccountingResult:
    curve = pd.DataFrame(
        {
            "session": DATES[: len(values)],
            "cash": [0.0] * len(values),
            "receivables": [0.0] * len(values),
            "positions_value": values,
            "equity": values,
            "holdings": [{}] * len(values),
            "pending_entitlements": [[]] * len(values),
            "execution_session": [False] * len(values),
        }
    )
    trade_frame = pd.DataFrame(
        trades or [],
        columns=(
            "session",
            "security_id",
            "shares",
            "open_raw",
            "gross_notional",
            "cost",
            "side",
        ),
    )
    return RawAccountingResult(
        policy={"paper_authorized": False, "real_money_action_usd": 0},
        equity_curve=curve,
        trades=trade_frame,
        action_audit=pd.DataFrame(),
    )


def test_formal_metrics_report_return_risk_drawdown_and_costs() -> None:
    account = _account(
        [1000.0, 1010.0, 1005.0, 1020.0],
        trades=[
            {
                "session": "2026-01-02",
                "security_id": "A",
                "shares": 10.0,
                "open_raw": 100.0,
                "gross_notional": 1000.0,
                "cost": 1.0,
                "side": "buy",
            }
        ],
    )
    rf = pd.DataFrame(
        {"session": DATES[:4], "risk_free_return": [0.0001] * 4}
    )
    metrics = compute_formal_metrics(account, risk_free=rf)

    assert metrics["sessions"] == 4
    assert metrics["total_return"] == pytest.approx(0.02)
    assert metrics["max_drawdown"] == pytest.approx(1005.0 / 1010.0 - 1.0)
    assert metrics["total_costs"] == pytest.approx(1.0)
    assert metrics["transactions"] == 1
    assert metrics["average_exposure"] == pytest.approx(1.0)


def test_comparison_uses_same_sessions_and_selection_adjusted_active_diagnostics() -> None:
    candidate = _account([1000.0, 1010.0, 1020.0, 1030.0])
    baseline = _account([1000.0, 1005.0, 1010.0, 1015.0])
    comparison = compare_account_to_baseline(
        candidate,
        baseline,
        baseline_key="QQQ_buy_hold",
        global_trials=6287,
    )

    assert comparison["baseline_key"] == "QQQ_buy_hold"
    assert comparison["observations"] == 4
    assert comparison["cagr_difference"] > 0.0
    assert comparison["positive_active_fraction"] > 0.0
    assert comparison["active_return_newey_west"]["lag"] >= 0.0
    assert comparison["active_dsr"]["trials"] == 6287.0

    paths = {
        "candidate": candidate,
        "QQQ_buy_hold": baseline,
        "SPY_buy_hold": baseline,
        "pit_eligible_equal_weight_monthly": baseline,
        "first_top10_equal_then_drift": baseline,
    }
    bundle = compare_formal_paths(
        paths,
        candidate_key="candidate",
        baseline_keys=FORMAL_BASELINE_KEYS,
        global_trials=6287,
    )
    assert bundle["paper_authorized"] is False
    assert bundle["real_money_action_usd"] == 0


def test_performance_rejects_risk_free_session_drift_and_missing_baseline() -> None:
    account = _account([1000.0, 1010.0, 1005.0])
    bad_rf = pd.DataFrame(
        {
            "session": ["2026-01-02", "2026-01-05", "2026-01-09"],
            "risk_free_return": [0.0, 0.0, 0.0],
        }
    )
    with pytest.raises(FormalPerformanceError) as rf_error:
        compute_formal_metrics(account, risk_free=bad_rf)
    assert rf_error.value.code == "performance_risk_free_session_mismatch"

    with pytest.raises(FormalPerformanceError) as baseline_error:
        compare_formal_paths(
            {"candidate": account},
            candidate_key="candidate",
            baseline_keys=FORMAL_BASELINE_KEYS,
            global_trials=6287,
        )
    assert baseline_error.value.code == "performance_baseline_missing"
