from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.build_short_term_market_stress_laggard_external import build_payload

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = (
    ROOT
    / "artifacts/snapshot_short_term_sector_vanguard_20040923_20260731_7a13b864.zip"
)
DATA_RECEIPT = ROOT / "artifacts/short_term_sector_etf_data_receipt.json"
RESULT = ROOT / "artifacts/short_term_market_stress_laggard_external.json"
REPORT = ROOT / "docs/SHORT_TERM_MARKET_STRESS_LAGGARD_EXTERNAL_REPORT.md"
PUBLIC_DECISION = ROOT / "site/data/public-decision.json"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def result() -> dict:
    return _load(RESULT)


def test_external_result_is_reproducible_and_fails_closed(result: dict) -> None:
    assert build_payload(SNAPSHOT, DATA_RECEIPT) == result
    assert result["status"] == "external_market_stress_laggard_validation_failed"
    assert result["source"]["formal_period"] == {
        "start": "2006-08-01",
        "end": "2026-07-31",
    }
    assert result["source"]["point_in_time_stock_membership"] is False
    assert result["source"]["delisted_returns_complete"] is False
    assert result["source"]["corporate_actions_complete"] is False
    assert result["source"]["data_checks"] == {
        "contract_ok": True,
        "first_joint_download_only": True,
        "formal_period_all_ohlcv_complete": True,
        "formal_period_has_at_least_5000_sessions": True,
        "latest_all_positive_volume": True,
        "maximum_adjusted_daily_move_not_above_65pct": True,
        "snapshot_created_after_freeze": True,
    }
    assert result["schedule"]["complete_events_by_horizon"] == {
        "5": 18,
        "10": 18,
        "20": 18,
    }
    assert result["decision"]["gate_summary"] == {
        "passed": 1,
        "total": 6,
        "all_passed": False,
    }


def test_external_result_keeps_fixed_costs_baselines_and_gates(result: dict) -> None:
    assert result["protocol"]["cost_scenarios_bps"] == [10.0, 20.0, 50.0]
    assert result["decision"]["best_variant_selection_allowed"] is False
    primary = result["horizons"]["20"]["20"]
    assert primary["events"] == 18
    assert primary["net_return_summary"]["candidate_top5_mean"] == pytest.approx(
        0.08790600876144125
    )
    assert primary["net_return_summary"]["eligible_equal_mean"] == pytest.approx(
        0.08557964610167938
    )
    comparison = primary["comparisons"]["eligible_equal"]
    assert comparison["mean_difference"] > 0.0
    assert comparison["newey_west"]["t_stat"] < 1.96
    assert comparison["win_fraction"] < 0.50
    assert (
        primary["moving_block_bootstrap_mean_difference_vs_eligible_equal"]["low"]
        < 0.0
    )
    assert primary["fixed_halves_vs_eligible_equal"]["first"]["events"] == 0
    assert result["decision"]["gates"] == {
        "at_least_30_complete_events": False,
        "mean_difference_positive": True,
        "newey_west_t_at_least_1_96": False,
        "bootstrap_95pct_low_positive": False,
        "paired_win_fraction_above_50pct": False,
        "both_fixed_halves_positive": False,
    }
    for horizon in ("5", "10", "20"):
        for cost in ("10", "20", "50"):
            summary = result["horizons"][horizon][cost]
            assert summary["events"] == 18
            assert set(summary["net_return_summary"]) >= {
                "candidate_top5_mean",
                "eligible_equal_mean",
                "all_sector_equal_mean",
                "SPY_mean",
                "QQQ_mean",
                "VTI_mean",
            }


def test_failed_external_result_stays_internal_and_public_page_holds_cash(
    result: dict,
) -> None:
    assert result["paper_authorized"] is False
    assert result["public_strategy_allowed"] is False
    assert result["real_money_action_usd"] == 0
    report = REPORT.read_text(encoding="utf-8")
    assert "結果只留在研究 log" in report
    assert "paper_authorized=false" in report
    public = _load(PUBLIC_DECISION)
    public_text = json.dumps(public, ensure_ascii=False)
    assert public["surface"] == "hold-cash"
    assert public["today_action"] == "今天不下單"
    assert public["strategies"] == []
    assert "short_term_market_stress_laggard_external" not in public_text
    assert "不構成投資建議" in public_text
