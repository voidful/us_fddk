from __future__ import annotations

import json
from pathlib import Path


def test_saved_trend_receipt_preserves_failure_boundary() -> None:
    receipt = json.loads(
        (
            Path(__file__).resolve().parents[1]
            / "artifacts/short_term_sec_insider_trend_diagnostic.json"
        ).read_text(encoding="utf-8")
    )
    assert receipt["status"] == "post_hoc_fixed_event_portfolio_trend_diagnostic"
    assert receipt["signal_filter"]["candidate_count"] == 5798
    assert receipt["signal_filter"]["accepted_count"] == 142
    assert receipt["signal_filter"]["skipped"]["below_trend_threshold"] == 2750
    assert receipt["signal_filter"]["skipped"]["insufficient_trend_history"] == 1576
    assert receipt["decision"]["paper_authorized"] is False
    assert receipt["decision"]["public_strategy_allowed"] is False
    assert set(receipt["cost_scenarios"]) == {"10", "25", "50"}
    assert set(receipt["cost_scenarios"]["10"]["all_period"]["baselines"]) == {
        "QQQ",
        "SPY",
        "IWM",
    }
    assert (
        receipt["cost_scenarios"]["10"]["fixed_halves"]["2024Q1_2025Q1"]["portfolio"]["cagr"]
        < receipt["cost_scenarios"]["10"]["fixed_halves"]["2024Q1_2025Q1"]["QQQ"]["cagr"]
    )
    assert (
        receipt["cost_scenarios"]["50"]["all_period"]["portfolio"]["cagr"]
        < receipt["cost_scenarios"]["50"]["all_period"]["QQQ"]["cagr"]
    )
