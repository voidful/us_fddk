from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _load() -> dict:
    return json.loads(
        (ROOT / "artifacts/short_term_us_volume_breakout_20y_diagnostic.json").read_text(
            encoding="utf-8"
        )
    )


def test_volume_breakout_20y_fails_closed_on_sparse_event_count() -> None:
    payload = _load()
    assert payload["status"] == "post_hoc_us_volume_breakout_20y_diagnostic"
    assert payload["source"]["archive_sha256"] == (
        "d480fb82e712f06aabe0a98461e222344656b87022b8bda2cd7ccaa4c29ae88b"
    )
    assert payload["source"]["panel_sha256"] == (
        "6a7ca6b83b1570007424daa46b0ff4e8fb4a655d39298a0f4f6d74c3b7ea3a66"
    )
    assert payload["schedule"]["candidate_events"] == 1
    assert payload["schedule"]["accepted_events"] == 1
    assert payload["schedule"]["accepted_signals"] == 10
    assert payload["decision"]["gate_summary"] == {
        "all_passed": False,
        "passed": 3,
        "total": 6,
    }
    assert payload["decision"]["gates"]["minimum_30_accepted_events"] is False
    assert payload["decision"]["paper_authorized"] is False
    assert payload["decision"]["public_strategy_allowed"] is False
    assert payload["decision"]["real_money_action_usd"] == 0
    assert payload["cost_scenarios"]["10"]["all_period"]["portfolio"]["cagr"] == pytest.approx(
        1.9950146120
    )


def test_volume_breakout_report_explains_sparse_result_and_public_boundary() -> None:
    report = (ROOT / "docs/SHORT_TERM_US_VOLUME_BREAKOUT_20Y_REPORT.md").read_text(
        encoding="utf-8"
    )
    assert "成交量突破" in report
    assert "候選事件 1 宗" in report
    assert "3/6" in report
    assert "Paper=false" in report
    assert "今天不下單" in report
    assert "{payload" not in report
