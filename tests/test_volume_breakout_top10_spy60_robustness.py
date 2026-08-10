from __future__ import annotations

import hashlib
import json
from pathlib import Path

from usfddk.global_trial_ledger_round64_extension import audit_round64_extension
from usfddk.short_term_volume_breakout_top10_spy60_robustness import (
    EXPECTED_PROTOCOL_RECEIPT_SHA256,
    EXPECTED_PROTOCOL_SHA256,
    PROTOCOL_PATH,
    PROTOCOL_RECEIPT_PATH,
    VALIDATION_PATH,
    _canonical_sha256,
    _load_protocol,
)

ROOT = Path(__file__).resolve().parents[1]


def test_round64_protocol_is_frozen_and_paper_blind() -> None:
    assert (
        hashlib.sha256((ROOT / PROTOCOL_PATH).read_bytes()).hexdigest()
        == EXPECTED_PROTOCOL_SHA256
    )
    receipt = json.loads((ROOT / PROTOCOL_RECEIPT_PATH).read_text(encoding="utf-8"))
    claimed = receipt["receipt_sha256"]
    unsigned = dict(receipt)
    unsigned.pop("receipt_sha256")
    assert claimed == EXPECTED_PROTOCOL_RECEIPT_SHA256
    assert _canonical_sha256(unsigned) == claimed
    loaded = _load_protocol(ROOT)
    assert loaded["status"] == "posthoc_volume_breakout_top10_spy60_robustness_diagnostic_only"
    assert loaded["research_role"] == "robustness_stress_diagnostic"
    assert loaded["independent_first_seen_evidence"] is False
    assert loaded["strategy_rule_changed"] is False
    assert loaded["costs_round_trip_bps"] == [20.0, 50.0]
    assert loaded["half_periods"]["first_half"] == {
        "start": "2006-08-01",
        "end": "2016-07-31",
    }
    assert loaded["paper_authorized"] is False
    assert loaded["real_money_authorized"] is False
    assert loaded["today_action"] == "今天不下單"


def test_round64_robustness_is_negative_and_stays_out_of_public_strategy() -> None:
    validation = json.loads((ROOT / VALIDATION_PATH).read_text(encoding="utf-8"))
    claimed = validation["receipt_sha256"]
    unsigned = dict(validation)
    unsigned.pop("receipt_sha256")
    assert _canonical_sha256(unsigned) == claimed
    assert validation["status"] == (
        "volume_breakout_top10_spy60_robustness_negative_survivorship_biased"
    )
    assert validation["strategy_rule_changed"] is False
    assert validation["fixed_schedule"] == {
        "accepted_events": 132,
        "candidate_events": 356,
        "frequency": "weekly_completed_xnys",
        "holding_sessions": 20,
        "ignored_overlapping_events": 224,
        "market_filter": "SPY_close_above_60_session_SMA",
        "overlap_policy": "ignore_signals_until_exit_then_resume",
        "selection_count": 10,
    }
    assert validation["capital_gate_summary"]["passed"] == 7
    assert validation["capital_gate_summary"]["required"] == 7
    assert validation["robustness_gate_summary"]["passed"] == 3
    assert validation["robustness_gate_summary"]["required"] == 6
    selected20 = validation["full_period"]["20_bps"]["selected"]
    selected50 = validation["full_period"]["50_bps"]["selected"]
    qqq20 = validation["full_period"]["20_bps"]["passive_QQQ"]
    qqq50 = validation["full_period"]["50_bps"]["passive_QQQ"]
    assert selected20["cagr"] == 0.17411179981597735
    assert selected50["cagr"] == 0.15101222367092415
    assert qqq20["cagr"] == 0.16702748649296195
    assert qqq50["cagr"] == 0.16685182497199036
    assert selected20["cagr"] > qqq20["cagr"]
    assert selected50["cagr"] < qqq50["cagr"]
    assert validation["state_boundary"] == {
        "performance_present": False,
        "strategy_run_count": 0,
        "paper_authorized": False,
        "real_money_authorized": False,
        "real_money_action_usd": 0,
        "today_action": "今天不下單",
    }
    assert validation["multiplicity"]["current_lower_bound"] == 6316


def test_round64_trial_ledger_extension_is_append_only() -> None:
    result = audit_round64_extension(root=ROOT)
    assert result["passed"] is True
    assert result["current_lower_bound"] == 6316
    assert result["increment"] == 1
    assert result["source_binding_count"] == 4
    assert result["paper"] == {
        "authorized": False,
        "state": "all_cash",
        "backfilled_trades": 0,
        "positions": [],
    }
    assert result["real_money_action_usd"] == 0
