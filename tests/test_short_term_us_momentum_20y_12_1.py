from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _load() -> dict:
    return json.loads(
        (ROOT / "artifacts/short_term_us_momentum_20y_12_1_diagnostic.json").read_text(
            encoding="utf-8"
        )
    )


def test_twelve_one_momentum_is_fixed_and_negative() -> None:
    payload = _load()
    assert payload["status"] == "post_hoc_us_momentum_20y_12_1_diagnostic"
    assert payload["protocol"]["lookback_sessions"] == 252
    assert payload["protocol"]["recent_skip_sessions"] == 21
    assert payload["source"]["archive_sha256"] == (
        "d480fb82e712f06aabe0a98461e222344656b87022b8bda2cd7ccaa4c29ae88b"
    )
    assert payload["source"]["panel_sha256"] == (
        "6a7ca6b83b1570007424daa46b0ff4e8fb4a655d39298a0f4f6d74c3b7ea3a66"
    )
    assert payload["schedule"]["accepted_count"] == 1190
    assert payload["decision"]["gate_summary"] == {
        "all_passed": False,
        "passed": 2,
        "total": 6,
    }
    assert payload["decision"]["gates"]["cagr_beats_qqq_at_10bps"] is False
    assert payload["decision"]["paper_authorized"] is False
    assert payload["decision"]["public_strategy_allowed"] is False
    assert payload["decision"]["real_money_action_usd"] == 0


def test_twelve_one_costs_halves_and_report_are_reproducible() -> None:
    payload = _load()
    assert payload["cost_scenarios"]["10"]["all_period"]["portfolio"]["cagr"] == pytest.approx(
        0.0904740104
    )
    assert payload["cost_scenarios"]["25"]["all_period"]["portfolio"]["cagr"] == pytest.approx(
        0.0641508709
    )
    assert payload["cost_scenarios"]["50"]["all_period"]["portfolio"]["cagr"] == pytest.approx(
        0.0215998764
    )
    report = (ROOT / "docs/SHORT_TERM_US_MOMENTUM_20Y_12_1_REPORT.md").read_text(
        encoding="utf-8"
    )
    assert "12–1 月動量" in report
    assert "9.05%" in report
    assert "2/6" in report
    assert "Paper=false" in report
    assert "今天不下單" in report
    assert "{payload" not in report
