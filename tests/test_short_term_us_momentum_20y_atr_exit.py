from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _load() -> dict:
    return json.loads(
        (ROOT / "artifacts/short_term_us_momentum_20y_atr_exit_diagnostic.json").read_text(
            encoding="utf-8"
        )
    )


def test_atr_exit_extension_keeps_parent_schedule_and_fails_cost_gates() -> None:
    payload = _load()
    assert payload["status"] == "post_hoc_us_momentum_20y_atr_exit_diagnostic"
    assert payload["parent"]["time_exit_accepted_count"] == 1531
    assert payload["schedule"]["accepted_count"] == 1531
    assert payload["protocol"]["stop_atr_multiplier"] == 3.0
    assert payload["protocol"]["target_atr_multiplier"] == 4.0
    assert payload["cost_scenarios"]["10"]["all_period"]["exit_counts"] == {
        "stop": 412,
        "target": 389,
        "time": 730,
    }
    assert payload["cost_scenarios"]["10"]["all_period"]["portfolio"]["cagr"] == pytest.approx(
        0.0925286414
    )
    assert payload["cost_scenarios"]["25"]["all_period"]["portfolio"]["cagr"] == pytest.approx(
        0.0406052256
    )
    assert payload["cost_scenarios"]["50"]["all_period"]["portfolio"]["cagr"] == pytest.approx(
        -0.0406769518
    )
    assert payload["decision"]["gate_summary"] == {
        "all_passed": False,
        "passed": 2,
        "total": 6,
    }
    assert payload["decision"]["gates"]["cagr_beats_qqq_at_10bps"] is False
    assert payload["decision"]["paper_authorized"] is False
    assert payload["decision"]["public_strategy_allowed"] is False
    assert payload["decision"]["real_money_action_usd"] == 0


def test_atr_exit_report_keeps_halves_and_all_baselines_internal() -> None:
    payload = _load()
    for cost in ("10", "25", "50"):
        scenario = payload["cost_scenarios"][cost]
        assert set(scenario["fixed_halves"]) == {
            "2004-01-01_2014-12-31",
            "2015-01-01_2026-06-30",
        }
        assert scenario["all_period"]["baselines"].keys() >= {"QQQ", "SPY", "IWM"}
    report = (ROOT / "docs/SHORT_TERM_US_MOMENTUM_20Y_ATR_EXIT_REPORT.md").read_text(
        encoding="utf-8"
    )
    assert "止蝕 3×ATR" in report
    assert "策略最大跌幅" in report
    assert "QQQ CAGR" in report
    assert "SPY CAGR" in report
    assert "IWM CAGR" in report
    assert "2/6" in report
    assert "Paper=false" in report
    assert "今天不下單" in report
    assert "{payload" not in report
