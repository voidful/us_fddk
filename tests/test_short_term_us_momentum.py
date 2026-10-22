from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _load() -> dict:
    return json.loads(
        (ROOT / "artifacts/short_term_us_cross_sectional_momentum_diagnostic.json").read_text(
            encoding="utf-8"
        )
    )


def test_us_momentum_diagnostic_is_research_only_and_fails_persistence_gate() -> None:
    payload = _load()
    assert payload["status"] == "post_hoc_us_cross_sectional_momentum_diagnostic"
    assert payload["universe"]["stock_symbol_count"] == 29
    assert payload["price_source"]["sha256"] == (
        "c984f85d6e6197d46436e2c15dec5c5b3b14dc0823c4fd052fce5f75edc25a40"
    )
    assert payload["liquidity_source"]["sha256"] == (
        "be1cdd723db77cef8e38a16435b1be220ab75337ef6f196afbabc37b1a76f9cc"
    )
    assert payload["regime_schedule"]["accepted_count"] == 252
    assert payload["cost_scenarios"]["10"]["all_period"]["portfolio"]["cagr"] == pytest.approx(
        0.4802065015
    )
    assert payload["cost_scenarios"]["10"]["all_period"]["QQQ"]["cagr"] == pytest.approx(
        0.2950081467
    )
    assert payload["decision"]["gate_summary"] == {
        "all_passed": False,
        "passed": 4,
        "total": 6,
    }
    assert payload["decision"]["gates"]["both_fixed_halves_beat_qqq_at_50bps"] is False
    assert payload["decision"]["paper_authorized"] is False
    assert payload["decision"]["public_strategy_allowed"] is False
    assert payload["decision"]["real_money_action_usd"] == 0


def test_us_momentum_diagnostic_keeps_costs_halves_control_and_baselines() -> None:
    payload = _load()
    for cost in ("10", "25", "50"):
        scenario = payload["cost_scenarios"][cost]
        assert set(scenario["fixed_halves"]) == {
            "2023-01-01_2024-12-31",
            "2025-01-01_2026-06-30",
        }
        assert scenario["all_period"]["baselines"].keys() >= {"QQQ", "SPY", "IWM"}
        assert payload["control_cost_scenarios"][cost]["all_period"]["signal_count"] == 287


def test_us_momentum_report_is_internal_and_has_hk_baseline_table() -> None:
    report = (ROOT / "docs/SHORT_TERM_US_CROSS_SECTIONAL_MOMENTUM_REPORT.md").read_text(
        encoding="utf-8"
    )
    assert "策略最大跌幅" in report
    assert "QQQ CAGR" in report
    assert "SPY CAGR" in report
    assert "IWM CAGR" in report
    assert "4/6" in report
    assert "Paper=false" in report
    assert "今天不下單" in report
    assert "{payload" not in report
