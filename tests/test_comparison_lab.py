from __future__ import annotations

import json
from pathlib import Path

from usfddk.comparison_lab import build_v25_expanded_comparison
from usfddk.data import load_snapshot

ROOT = Path(__file__).resolve().parents[1]
V25 = ROOT / "artifacts/snapshot_v25_vanguard_20060701_20260731_6cf44e63.zip"
STOCKS = ROOT / "artifacts/snapshot_20260731_6a7ca6b8.zip"
RECEIPT = ROOT / "artifacts/v25_expanded_comparison.json"


def _build() -> dict:
    v25_panel, _ = load_snapshot(V25)
    stock_panel, _ = load_snapshot(STOCKS)
    return build_v25_expanded_comparison(
        v25_panel,
        stock_panel,
        v25_snapshot_path=V25,
        stock_snapshot_path=STOCKS,
    )


def test_expanded_comparison_is_reproducible_and_post_entry_only() -> None:
    generated = _build()
    saved = json.loads(RECEIPT.read_text(encoding="utf-8"))
    assert generated == saved
    assert generated["used_for_frozen_entry_gate"] is False
    assert generated["changes_strategy_or_paper_rules"] is False
    assert generated["period"]["months"] == 240
    assert len(generated["formal_baselines"]) == 9
    assert len(generated["individual_stock_diagnostics"]["stocks"]) == 12
    assert generated["individual_stock_diagnostics"]["survivorship_bias_warning"] is True


def test_expanded_comparison_keeps_hard_baselines_and_negative_results() -> None:
    data = json.loads(RECEIPT.read_text(encoding="utf-8"))
    rows = {row["key"]: row for row in data["formal_baselines"]}
    assert set(rows) == {
        "candidate",
        "SPY",
        "QQQ",
        "VUG",
        "GLD",
        "60_SPY_40_IEF",
        "80_SPY_20_GLD",
        "80_VUG_20_SHY",
        "80_VUG_20_GLD_DRIFT",
    }
    assert rows["candidate"]["metrics"]["cagr"] < rows["QQQ"]["metrics"]["cagr"]
    assert rows["candidate"]["metrics"]["max_drawdown"] > rows["SPY"]["metrics"]["max_drawdown"]
    assert rows["candidate"]["excess_sharpe_vs_shy"] > rows["SPY"]["excess_sharpe_vs_shy"]
    assert rows["SPY"]["candidate_active_newey_west_t"] < 1.96
    assert rows["60_SPY_40_IEF"]["candidate_cagr_difference"] > 0


def test_market_context_is_diagnostic_not_a_signal() -> None:
    context = json.loads(RECEIPT.read_text(encoding="utf-8"))["market_context"]
    assert context["as_of"] == "2026-07-31"
    assert context["context_only_not_a_trading_signal"] is True
    assert context["current_watchlist_count"] == 30
    assert 0 <= context["current_watchlist_above_200d_fraction"] <= 1
    assert -1 <= context["vug_gold_correlation_252d"] <= 1
    assert context["breadth_survivorship_bias_warning"] is True
