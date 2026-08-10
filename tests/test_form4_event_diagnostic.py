from __future__ import annotations

import hashlib
import json
from pathlib import Path

from usfddk.global_trial_ledger_round53_extension import audit_round53_extension
from usfddk.short_term_form4_event_diagnostic import (
    EXPECTED_PROTOCOL_RECEIPT_SHA256,
    EXPECTED_PROTOCOL_SHA256,
    PROTOCOL_PATH,
    PROTOCOL_RECEIPT_PATH,
    VALIDATION_PATH,
    _canonical_sha256,
    _event_mapping,
    _load_protocol,
)

ROOT = Path(__file__).resolve().parents[1]


def test_round53_protocol_is_frozen_and_self_bound() -> None:
    assert hashlib.sha256((ROOT / PROTOCOL_PATH).read_bytes()).hexdigest() == EXPECTED_PROTOCOL_SHA256
    receipt = json.loads((ROOT / PROTOCOL_RECEIPT_PATH).read_text(encoding="utf-8"))
    claimed = receipt["receipt_sha256"]
    unsigned = dict(receipt)
    unsigned.pop("receipt_sha256")
    assert claimed == EXPECTED_PROTOCOL_RECEIPT_SHA256
    assert _canonical_sha256(unsigned) == claimed
    assert _load_protocol(ROOT)["status"] == "preregistered_form4_event_diagnostic_only"
    assert receipt["event_contract"]["exit_horizons_sessions"] == [5, 10, 20]
    assert receipt["paper_authorized"] is False
    assert receipt["real_money_authorized"] is False
    assert receipt["today_action"] == "今天不下單"


def test_mapping_prefers_as_filed_and_rejects_ambiguous_current_cik() -> None:
    watchlist = {"AAA", "BBB"}
    mapping = {"0000000001": frozenset({"AAA"}), "0000000002": frozenset({"AAA", "BBB"})}
    filed, mode = _event_mapping(
        {"issuer_symbol": "BBB", "issuer_cik": "0000000001"},
        watchlist_symbols=watchlist,
        cik_to_symbols=mapping,
    )
    assert (filed, mode) == ("BBB", "as_filed_symbol_exact")
    filed, mode = _event_mapping(
        {"issuer_symbol": None, "issuer_cik": "0000000002"},
        watchlist_symbols=watchlist,
        cik_to_symbols=mapping,
    )
    assert (filed, mode) == (None, "ambiguous_current_cik")


def test_round53_validation_is_negative_and_trade_blind() -> None:
    validation = json.loads((ROOT / VALIDATION_PATH).read_text(encoding="utf-8"))
    claimed = validation["receipt_sha256"]
    unsigned = dict(validation)
    unsigned.pop("receipt_sha256")
    assert _canonical_sha256(unsigned) == claimed
    assert validation["status"] == "form4_event_diagnostic_negative_survivorship_biased"
    assert validation["event_definition"]["cluster_event_count"] == 45
    assert validation["complete_event_counts"] == {"5": 45, "10": 45, "20": 45}
    assert validation["gate_summary"]["passed"] == 1
    assert validation["gate_summary"]["required"] == 6
    primary = validation["horizons"]["10"]
    assert primary["mean_difference_vs_eligible_pool"] < 0
    assert primary["newey_west_vs_eligible_pool"]["t_stat"] < 1.96
    assert primary["moving_block_bootstrap_vs_eligible_pool"]["low"] < 0
    assert primary["win_fraction_vs_eligible_pool"] < 0.50
    assert validation["state_boundary"] == {
        "performance_present": False,
        "strategy_run_count": 0,
        "paper_authorized": False,
        "real_money_authorized": False,
        "real_money_action_usd": 0,
        "today_action": "今天不下單",
    }
    assert validation["multiplicity"]["current_lower_bound"] == 6293
    forbidden = {
        "accession",
        "accession_number",
        "cik",
        "filing_date",
        "issuer",
        "issuer_cik",
        "notional",
        "owner",
        "owner_cik",
        "owner_name",
        "symbol",
        "ticker",
    }

    def keys(value: object) -> set[str]:
        if isinstance(value, dict):
            return {str(key) for key in value} | {
                nested
                for item in value.values()
                for nested in keys(item)
            }
        if isinstance(value, list):
            return {nested for item in value for nested in keys(item)}
        return set()

    assert forbidden.isdisjoint(keys(validation))


def test_round53_trial_ledger_extension_is_append_only() -> None:
    result = audit_round53_extension(root=ROOT)
    assert result["passed"] is True
    assert result["current_lower_bound"] == 6293
    assert result["increment"] == 3
    assert result["source_binding_count"] == 4
    assert result["paper"]["authorized"] is False
    assert result["real_money_action_usd"] == 0
