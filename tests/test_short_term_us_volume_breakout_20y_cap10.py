from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _load() -> dict:
    return json.loads(
        (
            ROOT / "artifacts/short_term_us_volume_breakout_20y_cap10_diagnostic.json"
        ).read_text(encoding="utf-8")
    )


def test_cap10_variant_is_source_aligned_but_not_promotion_ready() -> None:
    payload = _load()
    assert payload["status"] == "post_hoc_us_volume_breakout_20y_cap10_diagnostic"
    assert payload["protocol"]["top_k_cap"] == 10
    assert payload["protocol"]["min_breakout_candidates"] == 1
    assert payload["protocol"]["min_base_eligible"] == 10
    assert payload["source"]["archive_sha256"] == (
        "d480fb82e712f06aabe0a98461e222344656b87022b8bda2cd7ccaa4c29ae88b"
    )
    assert payload["schedule"]["candidate_events"] == 376
    assert payload["schedule"]["accepted_events"] == 146
    assert payload["schedule"]["accepted_signals"] == 265
    assert payload["decision"]["gate_summary"] == {
        "all_passed": False,
        "passed": 3,
        "total": 6,
    }
    assert payload["decision"]["gates"]["cagr_beats_qqq_at_25bps"] is False
    assert payload["decision"]["paper_authorized"] is False
    assert payload["decision"]["public_strategy_allowed"] is False
    assert payload["decision"]["real_money_action_usd"] == 0


def test_cap10_costs_halves_and_report_are_reproducible() -> None:
    payload = _load()
    assert payload["cost_scenarios"]["10"]["all_period"]["portfolio"]["cagr"] == pytest.approx(
        0.1635813875
    )
    assert payload["cost_scenarios"]["25"]["all_period"]["portfolio"]["cagr"] == pytest.approx(
        0.1410095900
    )
    assert payload["cost_scenarios"]["50"]["all_period"]["portfolio"]["cagr"] == pytest.approx(
        0.1042782564
    )
    report = (
        ROOT / "docs/SHORT_TERM_US_VOLUME_BREAKOUT_20Y_CAP10_REPORT.md"
    ).read_text(encoding="utf-8")
    assert "最多 Top-10" in report
    assert "候選事件 376 宗" in report
    assert "3/6" in report
    assert "Paper=false" in report
    assert "今天不下單" in report
    assert "{payload" not in report
