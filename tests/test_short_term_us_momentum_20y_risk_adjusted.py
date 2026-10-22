from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _load() -> dict:
    return json.loads(
        (
            ROOT / "artifacts/short_term_us_momentum_20y_risk_adjusted_diagnostic.json"
        ).read_text(encoding="utf-8")
    )


def test_risk_adjusted_momentum_is_single_fixed_internal_diagnostic() -> None:
    payload = _load()
    assert payload["status"] == "post_hoc_us_momentum_20y_risk_adjusted_diagnostic"
    assert payload["source"]["archive_sha256"] == (
        "d480fb82e712f06aabe0a98461e222344656b87022b8bda2cd7ccaa4c29ae88b"
    )
    assert payload["source"]["panel_sha256"] == (
        "6a7ca6b83b1570007424daa46b0ff4e8fb4a655d39298a0f4f6d74c3b7ea3a66"
    )
    assert payload["protocol"]["risk_adjusted_formula"] == (
        "3 * percentile(momentum20 / (ATR20 / close)) + percentile(trend60)"
    )
    assert payload["parent_reference"]["accepted_count"] == 1531
    assert payload["parent_reference"]["parent_schedule_candidate_count"] == 1531
    assert payload["parent_reference"]["risk_adjusted_schedule_candidate_count"] == 1531
    assert payload["parent_reference"]["schedule_pair_overlap_count"] == 1316
    assert payload["parent_reference"]["schedule_pairs_only_parent"] == 215
    assert payload["parent_reference"]["schedule_pairs_only_risk_adjusted"] == 215
    assert payload["regime_schedule"]["accepted_count"] == 1531
    assert payload["decision"]["paper_authorized"] is False
    assert payload["decision"]["public_strategy_allowed"] is False
    assert payload["decision"]["real_money_action_usd"] == 0


def test_risk_adjusted_costs_halves_and_baselines_are_reproducible() -> None:
    payload = _load()
    assert payload["cost_scenarios"]["10"]["all_period"]["portfolio"]["cagr"] == pytest.approx(
        0.1733361487
    )
    assert payload["cost_scenarios"]["25"]["all_period"]["portfolio"]["cagr"] == pytest.approx(
        0.1434189139
    )
    assert payload["cost_scenarios"]["50"]["all_period"]["portfolio"]["cagr"] == pytest.approx(
        0.0951273210
    )
    assert payload["decision"]["gate_summary"] == {
        "all_passed": False,
        "passed": 3,
        "total": 6,
    }
    assert payload["decision"]["gates"]["cagr_beats_qqq_at_25bps"] is False
    assert payload["decision"]["gates"]["both_fixed_halves_beat_qqq_at_50bps"] is False
    for cost in ("10", "25", "50"):
        scenario = payload["cost_scenarios"][cost]
        assert set(scenario["fixed_halves"]) == {
            "2004-01-01_2014-12-31",
            "2015-01-01_2026-06-30",
        }
        assert scenario["all_period"]["baselines"].keys() >= {"QQQ", "SPY", "IWM"}
        assert payload["control_cost_scenarios"][cost]["all_period"]["signal_count"] >= 1531


def test_risk_adjusted_report_stays_internal_and_fail_closed() -> None:
    report = (
        ROOT / "docs/SHORT_TERM_US_MOMENTUM_20Y_RISK_ADJUSTED_REPORT.md"
    ).read_text(encoding="utf-8")
    assert "風險調整動量" in report
    assert "QQQ CAGR" in report
    assert "SPY CAGR" in report
    assert "IWM CAGR" in report
    assert "3/6" in report
    assert "Paper=false" in report
    assert "今天不下單" in report
    assert "{payload" not in report
