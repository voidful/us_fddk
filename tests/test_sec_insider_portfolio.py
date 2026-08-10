from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import pytest

from usfddk.sec_insider_portfolio import (
    prepare_portfolio_signals,
    simulate_event_portfolio,
)


def _prices() -> pd.DataFrame:
    days = [date(2026, 6, 1) + timedelta(days=offset) for offset in range(30)]
    sessions = [day for day in days if day.weekday() < 5]
    rows = []
    for symbol, base in (("AAA", 100.0), ("BBB", 200.0), ("QQQ", 300.0)):
        for index, day in enumerate(sessions):
            rows.append(
                {
                    "symbol": symbol,
                    "date": day,
                    "adj_open": base + index,
                    "adj_close": base + index + (3.0 if symbol == "AAA" else 1.0),
                }
            )
    return pd.DataFrame(rows)


def test_prepare_uses_first_signal_and_requires_full_window() -> None:
    candidates = [
        {"ticker": "AAA", "available_session": "2026-06-01", "score": 1.0},
        {"ticker": "AAA", "available_session": "2026-06-02", "score": 2.0},
        {"ticker": "BBB", "available_session": "2026-06-01", "score": 1.0},
    ]
    signals, skipped = prepare_portfolio_signals(candidates, _prices())
    assert [row["ticker"] for row in signals] == ["AAA", "BBB"]
    assert skipped["overlapping_issuer_signal"] == 1


def test_portfolio_is_research_metric_and_beats_synthetic_baseline() -> None:
    candidates = [
        {"ticker": "AAA", "available_session": "2026-06-01", "score": 1.0},
        {"ticker": "BBB", "available_session": "2026-06-01", "score": 1.0},
    ]
    signals, _ = prepare_portfolio_signals(candidates, _prices())
    result = simulate_event_portfolio(signals, _prices())
    assert result["signal_count"] == 2
    assert result["portfolio"]["total_return"] > result["QQQ"]["total_return"]
    assert result["annualized_turnover"] > 0.0


def test_cost_rule_is_frozen() -> None:
    with pytest.raises(ValueError, match="frozen"):
        simulate_event_portfolio([], _prices(), one_way_cost_bps=30.0)


def test_saved_portfolio_receipt_is_upper_bound_only_and_not_paper() -> None:
    receipt = json.loads(
        (
            Path(__file__).resolve().parents[1]
            / "artifacts/short_term_sec_insider_portfolio_diagnostic.json"
        ).read_text(encoding="utf-8")
    )
    all_period = receipt["diagnostic"]["all_period"]
    assert receipt["status"] == "post_hoc_fixed_event_portfolio_diagnostic"
    assert receipt["decision"]["paper_authorized"] is False
    assert receipt["signal_filter"]["accepted_count"] == 2266
    assert receipt["signal_filter"]["skipped"]["missing_price_window"] == 883
    assert all_period["portfolio"]["cagr"] > all_period["QQQ"]["cagr"]
    assert set(all_period["baselines"]) == {"QQQ", "SPY", "IWM"}
    assert all_period["annualized_turnover"] > 30.0
    assert (
        receipt["cost_scenarios"]["50"]["all_period"]["portfolio"]["cagr"]
        < receipt["cost_scenarios"]["50"]["all_period"]["QQQ"]["cagr"]
    )
