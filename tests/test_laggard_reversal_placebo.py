from __future__ import annotations

import hashlib
import json
from pathlib import Path

from usfddk.global_trial_ledger_round58_extension import audit_round58_extension
from usfddk.short_term_laggard_reversal_placebo import (
    EXPECTED_PROTOCOL_RECEIPT_SHA256,
    EXPECTED_PROTOCOL_SHA256,
    PROTOCOL_PATH,
    PROTOCOL_RECEIPT_PATH,
    VALIDATION_PATH,
    _canonical_sha256,
    _load_protocol,
)

ROOT = Path(__file__).resolve().parents[1]


def test_round58_placebo_protocol_is_frozen_and_self_bound() -> None:
    assert hashlib.sha256((ROOT / PROTOCOL_PATH).read_bytes()).hexdigest() == EXPECTED_PROTOCOL_SHA256
    receipt = json.loads((ROOT / PROTOCOL_RECEIPT_PATH).read_text(encoding="utf-8"))
    claimed = receipt["receipt_sha256"]
    unsigned = dict(receipt)
    unsigned.pop("receipt_sha256")
    assert claimed == EXPECTED_PROTOCOL_RECEIPT_SHA256
    assert _canonical_sha256(unsigned) == claimed
    loaded = _load_protocol(ROOT)
    assert loaded["status"] == "preregistered_laggard_reversal_placebo_diagnostic_only"
    assert loaded["research_role"] == "placebo_robustness_diagnostic"
    assert loaded["independent_first_seen_evidence"] is False
    assert loaded["strategy_rule_changed"] is False
    assert loaded["placebo_control"]["market_return_threshold"] == 0.015
    assert loaded["paper_authorized"] is False
    assert loaded["real_money_authorized"] is False
    assert loaded["today_action"] == "今天不下單"


def test_round58_placebo_is_negative_control_and_trade_blind() -> None:
    validation = json.loads((ROOT / VALIDATION_PATH).read_text(encoding="utf-8"))
    claimed = validation["receipt_sha256"]
    unsigned = dict(validation)
    unsigned.pop("receipt_sha256")
    assert _canonical_sha256(unsigned) == claimed
    assert validation["status"] == "laggard_reversal_placebo_negative_survivorship_biased_control"
    assert validation["research_role"] == "placebo_robustness_diagnostic"
    assert validation["complete_event_counts"] == {"5": 54, "10": 54, "20": 54}
    assert validation["gate_summary"]["passed"] == 5
    assert validation["gate_summary"]["required"] == 6
    primary = validation["horizons"]["20"]
    assert primary["mean_difference_vs_eligible_pool"] > 0
    assert primary["newey_west_vs_eligible_pool"]["t_stat"] < 1.96
    assert primary["moving_block_bootstrap_vs_eligible_pool"]["low"] > 0
    assert primary["win_fraction_vs_eligible_pool"] > 0.50
    assert validation["state_boundary"] == {
        "performance_present": False,
        "strategy_run_count": 0,
        "paper_authorized": False,
        "real_money_authorized": False,
        "real_money_action_usd": 0,
        "today_action": "今天不下單",
    }
    assert validation["multiplicity"]["current_lower_bound"] == 6308
    assert validation["independent_first_seen_evidence"] is False
    assert validation["strategy_rule_changed"] is False

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


def test_round58_trial_ledger_extension_is_append_only() -> None:
    result = audit_round58_extension(root=ROOT)
    assert result["passed"] is True
    assert result["current_lower_bound"] == 6308
    assert result["increment"] == 3
    assert result["source_binding_count"] == 4
    assert result["paper"]["authorized"] is False
    assert result["real_money_action_usd"] == 0
