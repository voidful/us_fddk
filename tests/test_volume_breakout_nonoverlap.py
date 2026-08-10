from __future__ import annotations

import hashlib
import json
from pathlib import Path

from usfddk.global_trial_ledger_round61_extension import audit_round61_extension
from usfddk.short_term_volume_breakout_nonoverlap import (
    EXPECTED_PROTOCOL_RECEIPT_SHA256,
    EXPECTED_PROTOCOL_SHA256,
    PROTOCOL_PATH,
    PROTOCOL_RECEIPT_PATH,
    VALIDATION_PATH,
    _canonical_sha256,
    _load_protocol,
)

ROOT = Path(__file__).resolve().parents[1]


def test_round61_protocol_is_frozen_and_self_bound() -> None:
    assert hashlib.sha256((ROOT / PROTOCOL_PATH).read_bytes()).hexdigest() == EXPECTED_PROTOCOL_SHA256
    receipt = json.loads((ROOT / PROTOCOL_RECEIPT_PATH).read_text(encoding="utf-8"))
    claimed = receipt["receipt_sha256"]
    unsigned = dict(receipt)
    unsigned.pop("receipt_sha256")
    assert claimed == EXPECTED_PROTOCOL_RECEIPT_SHA256
    assert _canonical_sha256(unsigned) == claimed
    loaded = _load_protocol(ROOT)
    assert loaded["status"] == "posthoc_volume_breakout_nonoverlap_capital_diagnostic_only"
    assert loaded["research_role"] == "capital_accounting_diagnostic"
    assert loaded["independent_first_seen_evidence"] is False
    assert loaded["strategy_rule_changed"] is False
    assert loaded["starting_capital_usd"] == 1000.0
    assert loaded["holding_sessions"] == 20
    assert loaded["paper_authorized"] is False
    assert loaded["real_money_authorized"] is False
    assert loaded["today_action"] == "今天不下單"


def test_round61_capital_curve_is_a_negative_trade_blind_diagnostic() -> None:
    validation = json.loads((ROOT / VALIDATION_PATH).read_text(encoding="utf-8"))
    claimed = validation["receipt_sha256"]
    unsigned = dict(validation)
    unsigned.pop("receipt_sha256")
    assert _canonical_sha256(unsigned) == claimed
    assert validation["status"] == "volume_breakout_nonoverlap_capital_negative_survivorship_biased"
    assert validation["capital_policy"] == {
        "accepted_events": 146,
        "candidate_events": 403,
        "holding_sessions": 20,
        "ignored_overlapping_events": 257,
        "overlap_policy": "ignore_signals_until_exit_then_resume",
        "starting_capital_usd": 1000.0,
    }
    assert validation["gate_summary"]["passed"] == 5
    assert validation["gate_summary"]["required"] == 7
    selected = validation["scheduled_baselines"]["selected"]
    assert selected["cagr"] == 0.15071915465773844
    assert selected["max_drawdown"] == -0.5498993556165696
    assert selected["utilization_fraction"] == 0.6094215861657722
    assert validation["passive_baselines"]["QQQ"]["cagr"] > selected["cagr"]
    assert validation["passive_baselines"]["QQQ"]["max_drawdown"] > selected["max_drawdown"]
    assert validation["state_boundary"] == {
        "performance_present": False,
        "strategy_run_count": 0,
        "paper_authorized": False,
        "real_money_authorized": False,
        "real_money_action_usd": 0,
        "today_action": "今天不下單",
    }
    assert validation["multiplicity"]["current_lower_bound"] == 6313

    forbidden = {"accession", "cik", "issuer", "name", "owner", "symbol", "ticker"}

    def keys(value: object) -> set[str]:
        if isinstance(value, dict):
            return {str(key) for key in value} | {
                nested for item in value.values() for nested in keys(item)
            }
        if isinstance(value, list):
            return {nested for item in value for nested in keys(item)}
        return set()

    assert forbidden.isdisjoint(keys(validation))


def test_round61_trial_ledger_extension_is_append_only() -> None:
    result = audit_round61_extension(root=ROOT)
    assert result["passed"] is True
    assert result["current_lower_bound"] == 6313
    assert result["increment"] == 1
    assert result["source_binding_count"] == 4
    assert result["paper"]["authorized"] is False
    assert result["paper"]["state"] == "all_cash"
    assert result["real_money_action_usd"] == 0
