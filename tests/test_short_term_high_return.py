from __future__ import annotations

import json
from pathlib import Path

from usfddk.data import load_snapshot
from usfddk.short_term_high_return import (
    SHORT_TERM_GLOBAL_SEARCH_TRIALS,
    build_short_term_high_return_research,
)
from usfddk.universe import load_stock_watchlist

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = ROOT / "artifacts/snapshot_20260731_6a7ca6b8.zip"
RECEIPT = ROOT / "artifacts/short_term_high_return_validation.json"


def _build() -> dict:
    panel, _ = load_snapshot(SNAPSHOT)
    return build_short_term_high_return_research(
        panel,
        load_stock_watchlist(),
        snapshot_path=SNAPSHOT,
    )


def test_short_term_receipt_is_reproducible_and_never_opens_paper() -> None:
    generated = _build()
    saved = json.loads(RECEIPT.read_text(encoding="utf-8"))
    assert generated == saved
    assert generated["paper_eligible"] is False
    assert generated["trade_ready"] is False
    assert generated["paper_state_created"] is False
    assert generated["real_money_action_usd"] == 0
    assert generated["snapshot"]["survivorship_bias_warning"] is True
    assert generated["data_gates"]["point_in_time_membership_pass"] is False
    assert generated["data_gates"]["delisted_and_acquired_returns_pass"] is False


def test_short_term_keeps_the_hard_baselines_and_negative_results() -> None:
    data = json.loads(RECEIPT.read_text(encoding="utf-8"))
    candidate = data["frozen_candidate"]["metrics"]
    baselines = data["baselines"]
    assert candidate["cagr"] > baselines["QQQ"]["cagr"]
    assert candidate["cagr"] > baselines["current_cohort_monthly_equal_weight"]["cagr"]
    assert candidate["cagr"] < baselines["current_cohort_start_equal_then_drift"]["cagr"]
    assert data["comparison_vs_qqq"]["active_newey_west"]["t_stat"] < 1.96
    assert data["comparison_vs_qqq"]["active_global_deflated_sharpe"]["probability"] < 0.95
    assert data["pbo_across_four_current_cohort_variants"]["pbo"] > 0.20
    assert data["global_search_trials"] == SHORT_TERM_GLOBAL_SEARCH_TRIALS


def test_taiwan_rule_translation_is_an_ablation_not_a_promoted_strategy() -> None:
    data = json.loads(RECEIPT.read_text(encoding="utf-8"))
    translation = data["taiwan_reference_translation_ablation"]
    assert translation["all_use_current_2026_cohort_and_are_not_investable"] is True
    assert len(translation["results"]) == 3
    qqq_cagr = data["baselines"]["QQQ"]["cagr"]
    assert all(row["cagr"] < qqq_cagr for row in translation["results"].values())
    assert translation["results"]["tw_v85_weekly_spy_regime"]["max_drawdown"] > data[
        "frozen_candidate"
    ]["metrics"]["max_drawdown"]
