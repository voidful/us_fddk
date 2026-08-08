from __future__ import annotations

from copy import deepcopy

import pytest

from usfddk.restatement_firewall import (
    PROTOCOL_SHA256,
    RestatementFirewallError,
    frozen_decision_summary,
    protocol_integrity,
    synthetic_as_known_envelope,
    validate_envelope,
    validate_result,
)


def _expect(envelope: dict, code: str) -> None:
    with pytest.raises(RestatementFirewallError) as exc_info:
        validate_envelope(envelope, root=".")
    assert exc_info.value.code == code


def test_round34_protocol_and_valid_as_known_fixture_pass() -> None:
    assert protocol_integrity(".")["passed"] is True
    summary = validate_envelope(synthetic_as_known_envelope(), root=".")
    assert summary["as_known_integrity_passed"] is True
    assert summary["selected_release_ids"] == ["R-20260701-v1"]
    assert summary["future_selected_release_ids"] == []
    assert summary["strategy_input_allowed"] is False
    assert summary["paper_state"] == "all_cash"


def test_future_restatement_and_future_release_are_rejected() -> None:
    base = synthetic_as_known_envelope()
    restatement = deepcopy(base)
    restatement["selected_release_ids"] = ["R-20260701-v2"]
    restatement["rows"] = [
        {
            **row,
            "release_id": "R-20260701-v2",
            "source_record_id": f"{row['source_record_id']}-v2",
        }
        for row in base["rows"]
    ]
    _expect(restatement, "restatement_substitution")

    future = deepcopy(base)
    future["release_ledger"].append(
        {
            "provider": "synthetic-provider",
            "source_id": "CRSP_STK_DLY",
            "release_id": "R-20260720-v1",
            "available_at": "2026-07-20T12:00:00Z",
            "data_cutoff": "2026-07-20",
            "is_restatement": False,
            "supersedes_release_id": None,
            "content_sha256": "a" * 64,
            "row_count": 1,
        }
    )
    future["release_receipts"]["R-20260720-v1"] = {
        "content_sha256": "a" * 64,
        "row_count": 1,
    }
    future["selected_release_ids"] = ["R-20260720-v1"]
    future["rows"] = [
        {
            "source_id": "CRSP_STK_DLY",
            "release_id": "R-20260720-v1",
            "source_record_id": "future-row",
            "observation_date": "2026-07-20",
            "effective_at": "2026-07-20T20:00:00Z",
        }
    ]
    _expect(future, "future_release_leakage")


@pytest.mark.parametrize(
    ("mutation", "code"),
    [
        ("duplicate", "release_id_duplicate"),
        ("schema", "release_schema_mismatch"),
        ("chain", "supersedes_chain_invalid"),
        ("receipt", "release_receipt_mismatch"),
    ],
)
def test_release_ledger_attacks_fail_closed(mutation: str, code: str) -> None:
    envelope = deepcopy(synthetic_as_known_envelope())
    if mutation == "duplicate":
        envelope["release_ledger"].append(deepcopy(envelope["release_ledger"][0]))
    elif mutation == "schema":
        envelope["rows"][0].pop("effective_at")
    elif mutation == "chain":
        envelope["release_ledger"][1]["supersedes_release_id"] = "R-20260701-v2"
    elif mutation == "receipt":
        envelope["release_receipts"]["R-20260701-v1"]["row_count"] = 99
    _expect(envelope, code)


def test_final_revised_isolated_from_strategy_and_decision_boundary() -> None:
    envelope = deepcopy(synthetic_as_known_envelope())
    envelope["mode"] = "final_revised"
    envelope["selected_release_ids"] = ["R-20260701-v2"]
    envelope["rows"] = [
        {
            **row,
            "release_id": "R-20260701-v2",
            "source_record_id": f"{row['source_record_id']}-v2",
        }
        for row in synthetic_as_known_envelope()["rows"]
    ]
    summary = validate_envelope(envelope, root=".")
    assert summary["strategy_input_allowed"] is False
    result = {
        "research_round": 34,
        "protocol_sha256": PROTOCOL_SHA256,
        **summary,
        **frozen_decision_summary(),
    }
    result["strategy_input_allowed"] = True
    with pytest.raises(RestatementFirewallError) as exc_info:
        validate_result(result, root=".")
    assert exc_info.value.code == "final_revised_strategy_substitution"

    result = {
        "research_round": 34,
        "protocol_sha256": PROTOCOL_SHA256,
        **validate_envelope(synthetic_as_known_envelope(), root="."),
        **frozen_decision_summary(),
    }
    result["paper_state"] = "positions"
    with pytest.raises(RestatementFirewallError) as exc_info:
        validate_result(result, root=".")
    assert exc_info.value.code == "release_decision_boundary_violation"
