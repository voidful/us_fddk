from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import pytest

from usfddk.sec_insider_portfolio import (
    load_long_liquidity,
    prepare_portfolio_signals,
    simulate_event_portfolio,
)


def _prices() -> pd.DataFrame:
    days = [date(2026, 6, 1) + timedelta(days=offset) for offset in range(180)]
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


def test_liquidity_filter_uses_only_prior_sessions(tmp_path) -> None:
    prices = _prices()
    rows = []
    for symbol in ("AAA", "BBB"):
        for day in sorted(prices[prices["symbol"].eq(symbol)]["date"].unique()):
            entry_day = day == date(2026, 6, 29)
            rows.append(
                {
                    "symbol": symbol,
                    "date": day,
                    # The entry-day quote is deliberately untradeable.  It must
                    # not leak into the pre-entry history calculation.
                    "close": 1.0 if entry_day else 10.0,
                    "dollar_volume": 1_000_000.0 if entry_day else 25_000_000.0,
                }
            )
    path = tmp_path / "liquidity.csv"
    pd.DataFrame(rows).to_csv(path, index=False)
    liquidity = load_long_liquidity(path)
    candidates = [
        {"ticker": "AAA", "available_session": "2026-06-29", "score": 1.0},
    ]
    signals, skipped = prepare_portfolio_signals(
        candidates,
        prices,
        liquidity=liquidity,
        min_price_usd=5.0,
        min_median_dollar_volume_usd=20_000_000.0,
    )
    assert len(signals) == 1
    assert skipped["below_liquidity_threshold"] == 0


def test_trend_filter_uses_only_prior_sessions(tmp_path) -> None:
    prices = _prices()
    entry_day = date(2026, 8, 31)
    prices.loc[
        prices["symbol"].eq("AAA") & prices["date"].eq(entry_day), "adj_close"
    ] = 1.0
    rows = []
    for symbol in ("AAA",):
        for day in sorted(prices[prices["symbol"].eq(symbol)]["date"].unique()):
            is_entry = day == entry_day
            rows.append(
                {
                    "symbol": symbol,
                    "date": day,
                    # A bad entry-day print must not leak into the gate.
                    "close": 1.0 if is_entry else 10.0,
                    "dollar_volume": 1_000_000.0 if is_entry else 25_000_000.0,
                }
            )
    path = tmp_path / "liquidity.csv"
    pd.DataFrame(rows).to_csv(path, index=False)
    liquidity = load_long_liquidity(path)
    signals, skipped = prepare_portfolio_signals(
        [{"ticker": "AAA", "available_session": entry_day.isoformat(), "score": 1.0}],
        prices,
        liquidity=liquidity,
        min_price_usd=5.0,
        min_median_dollar_volume_usd=20_000_000.0,
        trend_filter=True,
    )
    assert len(signals) == 1
    assert skipped["below_trend_threshold"] == 0


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
    assert receipt["signal_filter"]["liquidity_filtered_accepted_count"] == 642
    assert receipt["signal_filter"]["liquidity_filtered_skipped"]["below_liquidity_threshold"] == 3400
    assert all_period["portfolio"]["cagr"] > all_period["QQQ"]["cagr"]
    assert set(all_period["baselines"]) == {"QQQ", "SPY", "IWM"}
    assert all_period["annualized_turnover"] > 30.0
    assert (
        receipt["cost_scenarios"]["50"]["all_period"]["portfolio"]["cagr"]
        < receipt["cost_scenarios"]["50"]["all_period"]["QQQ"]["cagr"]
    )
    filtered = receipt["liquidity_filtered_cost_scenarios"]["10"]["all_period"]
    assert filtered["portfolio"]["cagr"] < filtered["QQQ"]["cagr"]
    assert receipt["decision"]["public_strategy_allowed"] is False
