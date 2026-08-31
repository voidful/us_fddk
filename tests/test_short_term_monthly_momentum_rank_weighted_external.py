from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load() -> dict:
    return json.loads(
        (
            ROOT / "artifacts/short_term_monthly_momentum_rank_weighted_external.json"
        ).read_text(encoding="utf-8")
    )


def test_external_rank_weighted_validation_is_frozen_and_fail_closed() -> None:
    payload = _load()
    assert payload["status"] == "external_rank_weighted_momentum_validation_failed"
    assert payload["schedule"]["signals"] == 240
    assert payload["protocol"]["rank_weights"] == [0.5, 0.3, 0.2]
    assert payload["source"]["data_checks"] == {
        "contract_ok": True,
        "snapshot_created_after_freeze": True,
        "formal_period_all_ohlcv_complete": True,
        "formal_period_has_at_least_5000_sessions": True,
        "latest_all_positive_volume": True,
        "maximum_adjusted_daily_move_not_above_65pct": True,
        "first_joint_download_only": True,
    }
    assert payload["decision"]["gate_summary"] == {
        "passed": 1,
        "total": 10,
        "all_passed": False,
    }


def test_external_rank_weighted_result_keeps_fair_costs_baselines_and_boundaries() -> None:
    payload = _load()
    assert set(payload["cost_scenarios"]) == {"10", "25", "50"}
    for scenario in payload["cost_scenarios"].values():
        assert set(scenario["baselines"]) >= {
            "QQQ",
            "SPY",
            "VTI",
            "sector_monthly_equal",
            "sector_start_equal_then_drift",
            "matched_control",
        }
    assert payload["decision"]["formal_backtest_completed"] is False
    assert payload["decision"]["paper_authorized"] is False
    assert payload["decision"]["public_strategy_allowed"] is False
    assert payload["decision"]["real_money_action_usd"] == 0


def test_external_report_is_conclusion_first_and_not_a_public_action() -> None:
    report = (
        ROOT / "docs/SHORT_TERM_MONTHLY_MOMENTUM_RANK_WEIGHTED_EXTERNAL_REPORT.md"
    ).read_text(encoding="utf-8")
    assert "未能重現" in report
    assert "QQQ" in report
    assert "Paper" in report
    assert "今天不下單" in report
