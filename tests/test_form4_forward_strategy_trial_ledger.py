from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import pytest

from usfddk.form4_forward_strategy_trial_ledger import (
    BASE_CHAIN_HEAD_SHA256,
    BASE_LEDGER_SHA256,
    BASE_LOWER_BOUND,
    COMBINED_LOWER_BOUND,
    ROUND46_EXTENSION_PATH,
    ROUND46_FAMILY_ID,
    ROUND46_INCREMENT,
    ROUND46_SEQUENCE,
    Round46TrialLedgerError,
    audit_round46_trial_extension,
    audit_round46_trial_extension_payload,
)

ROOT = Path(__file__).resolve().parents[1]
EXTENSION = ROOT / ROUND46_EXTENSION_PATH


def _payload() -> dict[str, object]:
    return json.loads(EXTENSION.read_text(encoding="utf-8"))


def _canonical_sha256(value: dict[str, object]) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


def _rehash(payload: dict[str, object]) -> None:
    entry = payload["entry"]
    assert isinstance(entry, dict)
    entry_core = {key: value for key, value in entry.items() if key != "entry_sha256"}
    entry["entry_sha256"] = _canonical_sha256(entry_core)
    payload["combined_tip_sha256"] = entry["entry_sha256"]
    extension_core = {
        key: value for key, value in payload.items() if key != "extension_sha256"
    }
    payload["extension_sha256"] = _canonical_sha256(extension_core)


def _error(payload: dict[str, object]) -> str:
    with pytest.raises(Round46TrialLedgerError) as caught:
        audit_round46_trial_extension_payload(payload, root=ROOT)
    return caught.value.code


def test_round46_extension_is_one_verified_successor_not_a_side_receipt() -> None:
    result = audit_round46_trial_extension(root=ROOT)
    assert result == {
        "passed": True,
        "base_lower_bound": BASE_LOWER_BOUND,
        "round46_increment": ROUND46_INCREMENT,
        "combined_lower_bound": COMBINED_LOWER_BOUND,
        "combined_tip_sha256": _payload()["combined_tip_sha256"],
        "seen_result": False,
        "paper": {
            "authorized": False,
            "state": "all_cash",
            "backfilled_trades": 0,
            "positions": [],
        },
        "real_money_action_usd": 0,
    }
    payload = _payload()
    predecessor = payload["predecessor"]
    entry = payload["entry"]
    assert isinstance(predecessor, dict)
    assert isinstance(entry, dict)
    assert predecessor["sha256"] == BASE_LEDGER_SHA256
    assert predecessor["chain_head_sha256"] == BASE_CHAIN_HEAD_SHA256
    assert entry["sequence"] == ROUND46_SEQUENCE
    assert entry["family_id"] == ROUND46_FAMILY_ID
    assert entry["previous_entry_sha256"] == BASE_CHAIN_HEAD_SHA256
    assert entry["previous_lower_bound"] == BASE_LOWER_BOUND
    assert entry["minimum_increment"] == ROUND46_INCREMENT
    assert entry["current_lower_bound"] == COMBINED_LOWER_BOUND
    assert entry["seen_result"] is False


@pytest.mark.parametrize(
    ("section", "field", "replacement"),
    (
        ("predecessor", "sha256", "1" * 64),
        ("predecessor", "chain_head_sha256", "2" * 64),
        ("predecessor", "current_lower_bound", 6_286),
        ("entry", "sequence", 11),
        ("entry", "family_id", "forked_family"),
        ("entry", "previous_entry_sha256", "3" * 64),
        ("entry", "previous_lower_bound", 6_286),
        ("entry", "minimum_increment", 7),
        ("entry", "current_lower_bound", 6_294),
        ("entry", "seen_result", True),
        ("entry", "result_state", "result_seen"),
    ),
)
def test_round46_extension_rejects_fork_reorder_regression_and_promotion(
    section: str,
    field: str,
    replacement: object,
) -> None:
    payload = _payload()
    nested = payload[section]
    assert isinstance(nested, dict)
    nested[field] = replacement
    _rehash(payload)
    assert _error(payload) == "round46_trial_extension_invalid"


def test_round46_extension_rejects_source_chain_and_decision_boundary_drift() -> None:
    source = _payload()
    entry = source["entry"]
    assert isinstance(entry, dict)
    bindings = entry["source_bindings"]
    assert isinstance(bindings, list)
    binding = bindings[0]
    assert isinstance(binding, dict)
    binding["sha256"] = "4" * 64
    _rehash(source)
    assert _error(source) == "round46_trial_extension_invalid"

    chain = _payload()
    chain["combined_tip_sha256"] = "5" * 64
    extension_core = {
        key: value for key, value in chain.items() if key != "extension_sha256"
    }
    chain["extension_sha256"] = _canonical_sha256(extension_core)
    assert _error(chain) == "round46_trial_extension_invalid"

    paper = _payload()
    paper_state = paper["paper"]
    assert isinstance(paper_state, dict)
    paper_state["authorized"] = True
    _rehash(paper)
    assert _error(paper) == "round46_trial_extension_invalid"


def test_round46_extension_rejects_schema_and_bool_as_int_even_if_rehashed() -> None:
    extra = _payload()
    extra["extra"] = False
    _rehash(extra)
    assert _error(extra) == "round46_trial_extension_invalid"

    bool_sequence = _payload()
    entry = bool_sequence["entry"]
    assert isinstance(entry, dict)
    entry["sequence"] = True
    _rehash(bool_sequence)
    assert _error(bool_sequence) == "round46_trial_extension_invalid"

    missing = _payload()
    _rehash(missing)
    missing.pop("combined_tip_sha256")
    assert _error(missing) == "round46_trial_extension_invalid"


def test_round46_extension_payload_is_deepcopy_safe() -> None:
    first = _payload()
    second = copy.deepcopy(first)
    assert audit_round46_trial_extension_payload(first, root=ROOT) == (
        audit_round46_trial_extension_payload(second, root=ROOT)
    )
