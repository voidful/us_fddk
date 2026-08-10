from __future__ import annotations

import hashlib
import json
from pathlib import Path

from usfddk.global_trial_ledger_round57_extension import audit_round57_extension
from usfddk.short_term_market_stress_laggard_reversal import (
    EXPECTED_PROTOCOL_RECEIPT_SHA256,
    EXPECTED_PROTOCOL_SHA256,
    PROTOCOL_PATH,
    PROTOCOL_RECEIPT_PATH,
    VALIDATION_PATH,
    _canonical_sha256,
    _load_protocol,
)

ROOT = Path(__file__).resolve().parents[1]


def test_round57_protocol_is_frozen_and_self_bound() -> None:
    assert hashlib.sha256((ROOT / PROTOCOL_PATH).read_bytes()).hexdigest() == EXPECTED_PROTOCOL_SHA256
    receipt = json.loads((ROOT / PROTOCOL_RECEIPT_PATH).read_text(encoding="utf-8"))
    claimed = receipt["receipt_sha256"]
    unsigned = dict(receipt)
    unsigned.pop("receipt_sha256")
    assert claimed == EXPECTED_PROTOCOL_RECEIPT_SHA256
    assert _canonical_sha256(unsigned) == claimed
    assert _load_protocol(ROOT)["status"] == (
        "preregistered_market_stress_laggard_reversal_diagnostic_only"
    )
    assert receipt["horizons"] == [5, 10, 20]
    assert receipt["primary_horizon_sessions"] == 20
    assert receipt["signal"]["market_shock_asset"] == "SPY"
    assert receipt["paper_authorized"] is False
    assert receipt["real_money_authorized"] is False
    assert receipt["today_action"] == "今天不下單"


def test_round57_validation_is_positive_diagnostic_but_trade_blind() -> None:
    validation = json.loads((ROOT / VALIDATION_PATH).read_text(encoding="utf-8"))
    claimed = validation["receipt_sha256"]
    unsigned = dict(validation)
    unsigned.pop("receipt_sha256")
    assert _canonical_sha256(unsigned) == claimed
    assert validation["status"] == (
        "market_stress_laggard_reversal_diagnostic_positive_survivorship_biased"
    )
    assert validation["complete_event_counts"] == {"5": 204, "10": 204, "20": 204}
    assert validation["gate_summary"]["passed"] == 6
    assert validation["gate_summary"]["required"] == 6
    primary = validation["horizons"]["20"]
    assert primary["mean_difference_vs_eligible_pool"] > 0
    assert primary["newey_west_vs_eligible_pool"]["t_stat"] >= 1.96
    assert primary["moving_block_bootstrap_vs_eligible_pool"]["low"] > 0
    assert primary["win_fraction_vs_eligible_pool"] > 0.50
    assert primary["fixed_halves_vs_eligible_pool"]["first"]["mean_difference"] > 0
    assert primary["fixed_halves_vs_eligible_pool"]["second"]["mean_difference"] > 0
    assert validation["state_boundary"] == {
        "performance_present": False,
        "strategy_run_count": 0,
        "paper_authorized": False,
        "real_money_authorized": False,
        "real_money_action_usd": 0,
        "today_action": "今天不下單",
    }
    assert validation["multiplicity"]["current_lower_bound"] == 6305

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


def test_round57_trial_ledger_extension_is_append_only() -> None:
    result = audit_round57_extension(root=ROOT)
    assert result["passed"] is True
    assert result["current_lower_bound"] == 6305
    assert result["increment"] == 3
    assert result["source_binding_count"] == 4
    assert result["paper"]["authorized"] is False
    assert result["real_money_action_usd"] == 0
