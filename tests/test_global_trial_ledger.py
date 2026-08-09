import hashlib
import json
from copy import deepcopy
from pathlib import Path

import pytest

from usfddk.formal_backtest_readiness import (
    FORMAL_GLOBAL_SEARCH_TRIALS,
    FORMAL_PREREGISTRATION_GLOBAL_SEARCH_TRIALS,
    _policy_payload,
    _protocol_integrity,
)
from usfddk.global_trial_ledger import (
    GLOBAL_TRIAL_CURRENT_LOWER_BOUND,
    GLOBAL_TRIAL_EXPECTED_CHAIN_HEAD,
    GLOBAL_TRIAL_LEDGER_PATH,
    GlobalTrialLedgerError,
    audit_global_trial_ledger,
    audit_global_trial_ledger_payload,
)

ROOT = Path(__file__).resolve().parents[1]
LEDGER_PATH = ROOT / GLOBAL_TRIAL_LEDGER_PATH


def _payload() -> dict:
    return json.loads(LEDGER_PATH.read_text(encoding="utf-8"))


def _rehash(payload: dict) -> None:
    previous = "0" * 64
    for entry in payload["entries"]:
        entry["previous_entry_sha256"] = previous
        canonical = deepcopy(entry)
        canonical.pop("entry_sha256", None)
        rendered = json.dumps(
            canonical,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
        entry["entry_sha256"] = hashlib.sha256(rendered).hexdigest()
        previous = entry["entry_sha256"]
    payload["chain_head_sha256"] = previous


def _assert_error(payload: dict, code: str) -> None:
    with pytest.raises(GlobalTrialLedgerError) as error:
        audit_global_trial_ledger_payload(payload, root=ROOT)
    assert error.value.code == code


def test_global_trial_ledger_is_append_only_lower_bound() -> None:
    result = audit_global_trial_ledger(root=ROOT)
    assert result["passed"] is True
    assert result["original_preregistration_trials"] == 6_208
    assert result["current_lower_bound"] == 6_287
    assert result["exact_global_count_claimed"] is False
    assert result["entry_count"] == 12
    assert result["seen_result_family_count"] == 10
    assert result["reserved_unrun_family_count"] == 1
    assert result["tracked_source_hashes_verified"] == 21
    assert result["opaque_local_source_hashes_retained"] == 4
    assert result["chain_head_sha256"] == GLOBAL_TRIAL_EXPECTED_CHAIN_HEAD
    assert result["paper"]["state"] == "all_cash"
    assert result["real_money_action_usd"] == 0


def test_global_trial_audit_hashes_the_same_ledger_bytes_it_parses(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_read_bytes = Path.read_bytes
    ledger_reads = 0

    def counted_read_bytes(path: Path) -> bytes:
        nonlocal ledger_reads
        if path.resolve() == LEDGER_PATH.resolve():
            ledger_reads += 1
        return original_read_bytes(path)

    monkeypatch.setattr(Path, "read_bytes", counted_read_bytes)
    result = audit_global_trial_ledger(root=ROOT)
    assert result["passed"] is True
    assert ledger_reads == 1


def test_formal_preregistration_history_is_preserved_but_policy_is_current() -> None:
    integrity = _protocol_integrity(ROOT)
    assert FORMAL_PREREGISTRATION_GLOBAL_SEARCH_TRIALS == 6_208
    assert FORMAL_GLOBAL_SEARCH_TRIALS == GLOBAL_TRIAL_CURRENT_LOWER_BOUND == 6_287
    assert integrity["original_preregistered_global_search_trials"] == 6_208
    assert integrity["global_trial_ledger"]["current_lower_bound"] == 6_287
    assert _policy_payload()["statistics"]["global_search_trials"] == 6_287


def test_ledger_rejects_deleted_or_duplicate_families() -> None:
    deleted = _payload()
    del deleted["entries"][3]
    _assert_error(deleted, "trial_ledger_sequence_mismatch")

    duplicate = _payload()
    duplicate["entries"][2]["family_id"] = duplicate["entries"][1]["family_id"]
    _assert_error(duplicate, "trial_ledger_duplicate_family")


def test_ledger_rejects_lower_bound_reduction_and_bad_arithmetic() -> None:
    reduced = _payload()
    reduced["entries"][4]["previous_lower_bound"] = 6_228
    _assert_error(reduced, "trial_ledger_lower_bound_regression")

    bad_sum = _payload()
    bad_sum["entries"][4]["minimum_increment"] = 7
    _assert_error(bad_sum, "trial_ledger_arithmetic_mismatch")


def test_ledger_rejects_seen_result_regression_and_false_exactness() -> None:
    unseen = _payload()
    unseen["entries"][10]["seen_result"] = False
    _rehash(unseen)
    _assert_error(unseen, "trial_ledger_seen_result_regression")

    exact = _payload()
    exact["entries"][10]["exact_increment_claimed"] = True
    _rehash(exact)
    _assert_error(exact, "trial_ledger_schema_mismatch")


def test_ledger_rejects_source_hash_chain_tip_and_decision_mutations() -> None:
    source = _payload()
    source["entries"][2]["source_bindings"][0]["sha256"] = "1" * 64
    _rehash(source)
    _assert_error(source, "trial_ledger_source_binding_mismatch")

    chain = _payload()
    chain["entries"][3]["entry_sha256"] = "2" * 64
    _assert_error(chain, "trial_ledger_chain_mismatch")

    tip = _payload()
    tip["chain_head_sha256"] = "3" * 64
    _assert_error(tip, "trial_ledger_tip_mismatch")

    promoted = _payload()
    promoted["paper"]["authorized"] = True
    _assert_error(promoted, "trial_ledger_decision_boundary_violation")
