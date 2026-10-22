from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _load() -> dict:
    return json.loads(
        (ROOT / "artifacts/short_term_sec_xbrl_trend_diagnostic.json").read_text(
            encoding="utf-8"
        )
    )


def test_xbrl_trend_extension_is_research_only_and_fails_closed() -> None:
    payload = _load()
    assert payload["status"] == "post_hoc_sec_xbrl_earnings_trend_diagnostic"
    assert payload["parent"]["event_count"] == 139
    assert payload["signal_filter"]["candidate_count"] == 139
    assert payload["cost_scenarios"]["10"]["all_period"]["accepted_count"] == 77
    assert payload["cost_scenarios"]["10"]["all_period"]["simulation"]["portfolio"]["cagr"] == pytest.approx(0.1296624206)
    assert payload["cost_scenarios"]["10"]["all_period"]["simulation"]["QQQ"]["cagr"] == pytest.approx(0.2405725516)
    assert payload["decision"]["gate_summary"] == {"all_passed": False, "passed": 1, "total": 6}
    assert payload["decision"]["paper_authorized"] is False
    assert payload["decision"]["public_strategy_allowed"] is False
    assert payload["decision"]["real_money_action_usd"] == 0


def test_xbrl_trend_extension_records_fixed_cost_and_half_paths() -> None:
    payload = _load()
    for cost in ("10", "25", "50"):
        scenario = payload["cost_scenarios"][cost]
        assert set(scenario["fixed_halves"]) == {
            "2023-01-01_2024-12-31",
            "2025-01-01_2026-06-30",
        }
        assert scenario["all_period"]["simulation"]["baselines"].keys() >= {
            "QQQ",
            "SPY",
            "IWM",
        }


def test_xbrl_trend_report_exposes_baselines_without_public_action() -> None:
    report = (ROOT / "docs/SHORT_TERM_SEC_XBRL_TREND_REPORT.md").read_text(encoding="utf-8")
    assert "QQQ CAGR" in report
    assert "SPY CAGR" in report
    assert "IWM CAGR" in report
    assert "research_candidate_only" in report
    assert "今天不下單" in report
    assert "{payload" not in report
