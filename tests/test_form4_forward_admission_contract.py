from __future__ import annotations

import copy
import hashlib
import json
import socket
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

import pytest

from usfddk.form4_forward_admission_contract import (
    FORM4_FORWARD_ADMISSION_ERROR_CODES,
    Form4ForwardAdmissionContractError,
    evaluate_readout_gate,
    form4_forward_receipt_sha256,
    validate_form4_forward_admission_receipt,
    validate_form4_forward_public_progress,
)
from usfddk.form4_multipath_reconciliation_v2 import reconcile_form_index_pair

ADMISSION_SCHEMA = "us_fddk.short_term_form4_forward_admission.v1_1"
PUBLIC_SCHEMA = "us_fddk.short_term_form4_forward_public_progress.v1_1"
KNOWN_AT_BASIS = "prospective_local_full_body_first_observed"
CONTENT_BASIS = "local_full_body_completion_after_start"
RECONCILIATION_STATUS = "d0_d1_reconciled"
PUBLIC_STATUS = "prospective_admission_progress_no_performance"

ACCESSION = "0000123456-26-000001"
ROOT = Path(__file__).resolve().parents[1]
BODY = (
    b"<SEC-DOCUMENT>\n<SEC-HEADER>\n"
    b"<ACCESSION-NUMBER>0000123456-26-000001\n"
    b"<CONFORMED-SUBMISSION-TYPE>4\n"
    b"<CENTRAL-INDEX-KEY>0000123456\n</SEC-HEADER>\n"
    b"<DOCUMENT>\n<TYPE>4\n<TEXT>\n<XML>\n<ownershipDocument>\n"
    b"<documentType>4</documentType>\n"
    b"<issuer><issuerCik>0000999999</issuerCik></issuer>\n"
    b"<reportingOwner><reportingOwnerId>"
    b"<rptOwnerCik>0000123456</rptOwnerCik>"
    b"</reportingOwnerId></reportingOwner>\n"
    b"</ownershipDocument>\n</XML>\n</TEXT>\n"
    b"</DOCUMENT>\n</SEC-DOCUMENT>\n"
)
BODY_SHA256 = hashlib.sha256(BODY).hexdigest()
FIRST_OBSERVED = "2026-08-10T02:25:02Z"

PARENT_CONTRACT: dict[str, object] = {
    "historical_v1_protocol_sha256": (
        "845b13b1c01a0edef887ac490764ef8359cb382184430f483ab7093ca2b013eb"
    ),
    "historical_v1_receipt_file_sha256": (
        "f4c413217145fc2fff422a8291957565e690a1f4a734dab1b75482a9e1be4e85"
    ),
    "historical_v1_commit": "0e326d75e87d0ca8ee3e2260ad3c4a3c4f6c1a02",
    "disclosure_protocol_sha256": (
        "ffe2d6df0fce9a305a5a361bc4ce0d377cc9d9afb20246f212031ce57a3949b7"
    ),
    "disclosure_receipt_file_sha256": (
        "87f4c322333c8bdf8be12ee9682d49ea22ecce8c6569139a192cebd4892374e7"
    ),
    "disclosure_amendment_sha256": (
        "cd2422c3f74aa79ab062aaf02fbdce7c20ba9d0455b4f7219c3954521614ac76"
    ),
    "disclosure_amendment_receipt_file_sha256": (
        "09cc69ec9f4bcf896f7b527f7b14b51b36e4d634d7f6fd5d3e0905e7d78de7aa"
    ),
    "round41_amendment_sha256": (
        "0ba74da7e77119679f1ae178a2dcabe57e96267d6c6564ed3741bcf11739a3dd"
    ),
    "round41_amendment_receipt_file_sha256": (
        "90440b0ae74dbbe91c45ab885f9ad5e1e1457392b4eaff9265c5f7588bdc883c"
    ),
    "round41_protocol_sha256": (
        "c0b8370f5139d7076d9b4bc52fd8514c3b57a4bb4917b9890720d15d78d8c28e"
    ),
    "round41_receipt_file_sha256": (
        "077b877f7b04acf5aa9fcbcb2efcd4e99bc894f6a85846a616f549745126b383"
    ),
    "round42_feasibility_protocol_sha256": (
        "ddce1e7152a3d23f39dae4f8d7bb812166941952d7611523ca5796f11b4b1186"
    ),
    "round42_feasibility_protocol_receipt_file_sha256": (
        "75f81c0149abc003fa0438e9498f0884a0e7020b31c07bbeaef122cc15f912db"
    ),
    "round42_schema_amendment_sha256": (
        "2d5f2e27a28151a032ebd440271d2bb325d210df8628de1baea00677ab926b2c"
    ),
    "round42_schema_amendment_receipt_file_sha256": (
        "c8811f20a4a5369a442f297bb34870baf62bf76aa74538ef9ea68f4d98f83558"
    ),
    "round42_collection_authorization_sha256": (
        "b3ac9dc96cc3aa54281d88bbe387649be76f936270b94beae1735a628c5353a7"
    ),
    "round42_collection_authorization_receipt_file_sha256": (
        "28d2a4eca39205c16a58845f5d817d6e6b5a2f964242704c53941c858b089789"
    ),
    "round42_validation_file_sha256": (
        "44fc7bcf41b336406633338e306458184b999ff90cff86cac80238ecffc38ddf"
    ),
    "round42_report_sha256": (
        "307d8f2bb8b01a300194a9cbc1770f008c78b9a856f36f3391f176a001d3fab3"
    ),
    "round42_admission_passed": 2,
    "round42_admission_total": 16,
    "historical_gate_07_passed": False,
    "historical_gate_08_passed": False,
    "prospective_evidence_can_promote_historical_admission": False,
    "global_trial_ledger_protocol_sha256": (
        "8c9fb4d515741283143192612d8017a86333086ed641ea0e45c2eb5c492c4451"
    ),
    "global_trial_ledger_file_sha256": (
        "0240f3c36edca35a86c077a94116067a7d1560e4329968df33abbdcaffbb4b49"
    ),
    "global_trial_chain_head_sha256": (
        "c0e754cee5603c5eb9d2d142db1af6ec21b465d3492097b02112b94a18574085"
    ),
    "global_trial_lower_bound": 6287,
    "round43_trial_increment": 0,
    "round43_amendment_sha256": (
        "2a642f22ca113286241062343ecfc788eaee82ca7bb394790ff4ab8ede7eb0e3"
    ),
}


def _canonical_hash(value: Mapping[str, Any]) -> str:
    rendered = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(rendered).hexdigest()


def _seal(payload: dict[str, Any]) -> dict[str, Any]:
    core = {key: value for key, value in payload.items() if key != "receipt_sha256"}
    payload["receipt_sha256"] = _canonical_hash(core)
    return payload


def _zero_state() -> dict[str, object]:
    return {
        "candidate_selection_count": 0,
        "candidate_allocation_count": 0,
        "strategy_run_count": 0,
        "performance_result_present": False,
        "paper_authorized": False,
        "paper_state": "all_cash",
        "paper_positions": [],
        "paper_backfilled_trades": 0,
        "real_money_action_usd": 0,
    }


def _index_line(accession: str = ACCESSION) -> bytes:
    path = f"edgar/data/123456/{accession}.txt"
    return f"{'4':<12}{'Synthetic issuer':<67}{'123456':>10} 20260630 {path}\n".encode(
        "latin-1"
    )


def _reconciliation_inputs() -> dict[str, object]:
    unrelated = "0000123456-26-000002"
    return {
        "accession": ACCESSION,
        "form": "4",
        "bulk_filing_date": "2026-06-30",
        "d0_body": b"Form Type   Company Name\n" + _index_line(),
        "d1_body": b"Form Type   Company Name\n" + _index_line(unrelated),
        "published_form_index_dates": ["2026-06-30", "2026-07-01"],
    }


def _reconciliation_hash(inputs: Mapping[str, Any]) -> str:
    result = reconcile_form_index_pair(**dict(inputs))
    return _canonical_hash(result)


def _registry(first_observed: str = FIRST_OBSERVED) -> dict[str, str]:
    return {BODY_SHA256: first_observed}


def _admission(*, pre_start: bool = True) -> dict[str, Any]:
    filing_at = "2026-08-09T22:00:00Z" if pre_start else "2026-08-10T02:30:01Z"
    event_at = "2026-08-08T22:00:00Z" if pre_start else "2026-08-10T02:30:00Z"
    inputs = _reconciliation_inputs()
    return _seal(
        {
            "schema_version": ADMISSION_SCHEMA,
            "evidence_mode": "synthetic_fixture_only",
            "admission_authorized": False,
            "source_scope": ["sec_form_4"],
            "source_type": "sec_form_4",
            "form_type": "4",
            "parent_contract": copy.deepcopy(PARENT_CONTRACT),
            "monitor_started_at": "2026-08-10T02:21:51Z",
            "start_receipt_sha256": "a" * 64,
            "content_observation": {
                "request_started_at": "2026-08-10T02:25:00Z",
                "content_full_body_first_observed_at": FIRST_OBSERVED,
                "first_observed_basis": CONTENT_BASIS,
                "full_body_complete": True,
                "read_to_eof": True,
                "hash_verified": True,
                "byte_count": len(BODY),
                "body_sha256": BODY_SHA256,
                "immutable_object_sha256": BODY_SHA256,
                "first_observation_registry_sha256": _canonical_hash(_registry()),
            },
            "source_times": {"filing_at": filing_at, "event_at": event_at},
            "temporal_classification": {
                "pre_start_event_date": pre_start,
                "pre_start_filing_date": pre_start,
                "historical_event_used_for_backfill": False,
                "historical_filing_used_for_backfill": False,
            },
            "reconciliation": {
                "status": RECONCILIATION_STATUS,
                "observed_at": "2026-08-11T03:00:00Z",
                "d0_d1_complete": True,
                "content_body_sha256": BODY_SHA256,
                "reconciliation_result_sha256": _reconciliation_hash(inputs),
            },
            "data_known_at": FIRST_OBSERVED,
            "data_known_at_basis": KNOWN_AT_BASIS,
            "state_boundary": _zero_state(),
            "receipt_sha256": "",
        }
    )


def _public() -> dict[str, Any]:
    return _seal(
        {
            "schema_version": PUBLIC_SCHEMA,
            "evidence_mode": "synthetic_fixture_only",
            "status": PUBLIC_STATUS,
            "source_scope": ["sec_form_4"],
            "as_of": "2026-08-11T03:00:00Z",
            "start_receipt_sha256": "a" * 64,
            "progress": {
                "published_form_index_dates_observed": 2,
                "content_observations": 2,
                "reconciled_observations": 1,
                "pre_start_observations": 1,
                "admission_failures": 0,
            },
            "state_boundary": _zero_state(),
            "receipt_sha256": "",
        }
    )


def _validate(payload: Mapping[str, Any], **overrides: Any) -> dict[str, Any]:
    registry = overrides.pop("first_observation_registry", _registry())
    trusted = overrides.pop(
        "trusted_first_observation_registry_sha256", _canonical_hash(registry)
    )
    inputs = overrides.pop("reconciliation_inputs", _reconciliation_inputs())
    assert not overrides
    return validate_form4_forward_admission_receipt(
        payload,
        content_body=BODY,
        first_observation_registry=registry,
        trusted_first_observation_registry_sha256=trusted,
        reconciliation_inputs=inputs,
        parent_root=ROOT,
    )


def _error_code(call: Callable[[], object]) -> str:
    with pytest.raises(Form4ForwardAdmissionContractError) as error:
        call()
    assert error.value.code in FORM4_FORWARD_ADMISSION_ERROR_CODES
    return error.value.code


def test_valid_receipt_binds_exact_scope_parent_zero_state_and_content_known_at() -> None:
    receipt = _admission(pre_start=True)
    assert _validate(receipt) == receipt
    assert receipt["evidence_mode"] == "synthetic_fixture_only"
    assert receipt["admission_authorized"] is False
    assert receipt["source_scope"] == ["sec_form_4"]
    assert receipt["source_type"] == "sec_form_4"
    assert receipt["form_type"] == "4"
    assert receipt["parent_contract"] == PARENT_CONTRACT
    assert receipt["state_boundary"] == _zero_state()
    assert receipt["data_known_at_basis"] == KNOWN_AT_BASIS
    assert receipt["data_known_at"] == FIRST_OBSERVED
    assert receipt["data_known_at"] != receipt["reconciliation"]["observed_at"]
    assert receipt["receipt_sha256"] == form4_forward_receipt_sha256(receipt)


def test_v1_1_cannot_be_relabelled_as_real_admission() -> None:
    receipt = _admission()
    receipt["evidence_mode"] = "authorized_real_evidence"
    receipt["admission_authorized"] = True
    _seal(receipt)
    assert _error_code(lambda: _validate(receipt)) == (
        "form4_forward_admission_schema_invalid"
    )


def test_parent_hash_labels_are_verified_against_actual_repository_bytes(
    tmp_path: Path,
) -> None:
    receipt = _admission()
    assert _error_code(
        lambda: validate_form4_forward_admission_receipt(
            receipt,
            content_body=BODY,
            first_observation_registry=_registry(),
            trusted_first_observation_registry_sha256=_canonical_hash(_registry()),
            reconciliation_inputs=_reconciliation_inputs(),
            parent_root=tmp_path,
        )
    ) == "form4_forward_admission_schema_invalid"


def test_old_event_and_filing_dates_stay_in_cohort_without_backfill() -> None:
    receipt = _admission(pre_start=True)
    assert _validate(receipt)["temporal_classification"] == {
        "pre_start_event_date": True,
        "pre_start_filing_date": True,
        "historical_event_used_for_backfill": False,
        "historical_filing_used_for_backfill": False,
    }
    post_start = _admission(pre_start=False)
    assert _validate(post_start)["temporal_classification"] == {
        "pre_start_event_date": False,
        "pre_start_filing_date": False,
        "historical_event_used_for_backfill": False,
        "historical_filing_used_for_backfill": False,
    }


@pytest.mark.parametrize(
    ("mutate", "expected"),
    [
        (
            lambda row: row.update(source_scope=["sec_form_4", "sec_form_4_a"]),
            "form4_forward_admission_source_scope_invalid",
        ),
        (
            lambda row: row.update(source_type="sec_form_4_a"),
            "form4_forward_admission_source_scope_invalid",
        ),
        (
            lambda row: row.update(form_type="3"),
            "form4_forward_admission_source_scope_invalid",
        ),
        (
            lambda row: row.update(form_type=[]),
            "form4_forward_admission_source_scope_invalid",
        ),
        (
            lambda row: row["parent_contract"].update(round42_admission_passed=16),
            "form4_forward_admission_schema_invalid",
        ),
        (
            lambda row: row["parent_contract"].update(historical_gate_07_passed=0),
            "form4_forward_admission_schema_invalid",
        ),
        (
            lambda row: row["parent_contract"].update(round42_admission_passed=2.0),
            "form4_forward_admission_schema_invalid",
        ),
        (
            lambda row: row["parent_contract"].update(round43_trial_increment=False),
            "form4_forward_admission_schema_invalid",
        ),
        (
            lambda row: row["content_observation"].pop(
                "content_full_body_first_observed_at"
            ),
            "form4_forward_known_at_invented",
        ),
        (
            lambda row: row["content_observation"].update(
                content_full_body_first_observed_at="2026-08-10T02:21:51Z"
            ),
            "form4_forward_known_at_invented",
        ),
        (
            lambda row: row["content_observation"].update(read_to_eof=False),
            "form4_forward_admission_content_invalid",
        ),
        (
            lambda row: row["content_observation"].update(hash_verified=False),
            "form4_forward_admission_content_invalid",
        ),
        (
            lambda row: row["content_observation"].update(byte_count=len(BODY) + 1),
            "form4_forward_admission_content_invalid",
        ),
        (
            lambda row: row["content_observation"].update(immutable_object_sha256="b" * 64),
            "form4_forward_admission_content_invalid",
        ),
        (
            lambda row: row["reconciliation"].update(observed_at="2026-08-10T02:25:01Z"),
            "form4_forward_admission_reconciliation_invalid",
        ),
        (
            lambda row: row.update(data_known_at=row["reconciliation"]["observed_at"]),
            "form4_forward_known_at_invented",
        ),
        (
            lambda row: row["temporal_classification"].update(
                historical_event_used_for_backfill=True
            ),
            "form4_forward_admission_pre_start_invalid",
        ),
        (
            lambda row: row["state_boundary"].update(candidate_selection_count=1),
            "form4_forward_non_engineering_action_forbidden",
        ),
        (
            lambda row: row["state_boundary"].update(candidate_allocation_count=1),
            "form4_forward_non_engineering_action_forbidden",
        ),
        (
            lambda row: row["state_boundary"].update(performance_result_present=True),
            "form4_forward_non_engineering_action_forbidden",
        ),
        (
            lambda row: row["state_boundary"].update(paper_state="invested"),
            "form4_forward_non_engineering_action_forbidden",
        ),
        (
            lambda row: row["state_boundary"].update(real_money_action_usd=1),
            "form4_forward_non_engineering_action_forbidden",
        ),
    ],
)
def test_semantic_mutations_use_v1_1_canonical_codes(
    mutate: Callable[[dict[str, Any]], object], expected: str
) -> None:
    payload = _admission()
    mutate(payload)
    _seal(payload)
    assert _error_code(lambda: _validate(payload)) == expected


@pytest.mark.parametrize(
    "key",
    [
        "congress_ptr",
        "house_member",
        "senate_trade",
        "lawmaker_name",
        "senator_score",
        "p_t_r",
        "c-o-n-g-r-e-s-s",
        "houseMember",
    ],
)
def test_congress_like_keys_are_rejected_at_any_depth_even_when_null(key: str) -> None:
    payload = _admission()
    payload["content_observation"]["nested"] = [{key: None}]
    _seal(payload)
    assert _error_code(lambda: _validate(payload)) == "form4_forward_congress_field_injection"


@pytest.mark.parametrize("value", ["congress_house_ptr", "congress_senate_ptr", "p_t_r"])
def test_congress_source_values_fail_before_scope_or_network(value: str) -> None:
    payload = _admission()
    payload["source_type"] = value
    _seal(payload)
    assert _error_code(lambda: _validate(payload)) == "form4_forward_congress_field_injection"


@pytest.mark.parametrize(
    "key",
    [
        "strategy_run_count",
        "paper_state",
        "real_money_action_usd",
        "latest_order",
        "shadow_portfolio",
        "dry_run",
        "entry",
        "exit",
        "portfolio",
        "entry_signal",
        "exit_signal",
    ],
)
def test_nonengineering_aliases_fail_with_the_single_canonical_code(key: str) -> None:
    payload = _admission()
    payload[key] = 0
    _seal(payload)
    assert _error_code(lambda: _validate(payload)) == (
        "form4_forward_non_engineering_action_forbidden"
    )


def test_validation_has_no_network_path(monkeypatch: pytest.MonkeyPatch) -> None:
    attempts: list[object] = []

    def forbidden_network(*args: object, **kwargs: object) -> None:
        attempts.append((args, kwargs))
        raise AssertionError("network must not be called")

    monkeypatch.setattr(socket, "create_connection", forbidden_network)
    assert _validate(_admission())
    assert attempts == []


def test_registry_anchor_rejects_replay_that_moves_first_seen_earlier() -> None:
    payload = _admission()
    trusted_hash = _canonical_hash(_registry())
    forged_registry = _registry("2026-08-10T02:24:00Z")
    payload["content_observation"][
        "content_full_body_first_observed_at"
    ] = "2026-08-10T02:24:00Z"
    payload["content_observation"]["request_started_at"] = "2026-08-10T02:23:00Z"
    payload["content_observation"]["first_observation_registry_sha256"] = _canonical_hash(
        forged_registry
    )
    payload["data_known_at"] = "2026-08-10T02:24:00Z"
    _seal(payload)
    assert _error_code(
        lambda: _validate(
            payload,
            first_observation_registry=forged_registry,
            trusted_first_observation_registry_sha256=trusted_hash,
        )
    ) == "form4_forward_known_at_invented"


def test_reconciliation_is_replayed_and_cannot_overwrite_data_known_at() -> None:
    payload = _admission()
    changed_inputs = _reconciliation_inputs()
    changed_inputs["d1_body"] = changed_inputs["d0_body"]
    assert _error_code(
        lambda: _validate(payload, reconciliation_inputs=changed_inputs)
    ) == "form4_forward_cross_day_missing_or_ambiguous"
    assert payload["data_known_at"] == FIRST_OBSERVED

    tampered = _admission()
    tampered["reconciliation"]["reconciliation_result_sha256"] = "b" * 64
    _seal(tampered)
    assert _error_code(lambda: _validate(tampered)) == (
        "form4_forward_admission_reconciliation_invalid"
    )


def test_submission_accession_is_cryptographically_bound_to_reconciliation() -> None:
    other_accession = "0000123456-26-000099"
    inputs = _reconciliation_inputs()
    inputs["accession"] = other_accession
    inputs["d0_body"] = b"Form Type   Company Name\n" + _index_line(other_accession)
    receipt = _admission()
    receipt["reconciliation"]["reconciliation_result_sha256"] = _reconciliation_hash(inputs)
    _seal(receipt)
    assert _error_code(lambda: _validate(receipt, reconciliation_inputs=inputs)) == (
        "form4_forward_admission_content_invalid"
    )


def test_arbitrary_or_ptr_body_cannot_be_admitted_as_form4() -> None:
    payload = _admission()
    arbitrary = (
        b"<SEC-DOCUMENT>\n<DOCUMENT>\n<TYPE>4\n"
        b"<html>Congress House Periodic Transaction Report</html>\n"
        b"</DOCUMENT>\n</SEC-DOCUMENT>\n"
    )
    payload["content_observation"].update(
        byte_count=len(arbitrary),
        body_sha256=hashlib.sha256(arbitrary).hexdigest(),
        immutable_object_sha256=hashlib.sha256(arbitrary).hexdigest(),
    )
    registry = {hashlib.sha256(arbitrary).hexdigest(): FIRST_OBSERVED}
    payload["content_observation"]["first_observation_registry_sha256"] = _canonical_hash(registry)
    payload["reconciliation"]["content_body_sha256"] = hashlib.sha256(arbitrary).hexdigest()
    _seal(payload)
    with pytest.raises(Form4ForwardAdmissionContractError) as error:
        validate_form4_forward_admission_receipt(
            payload,
            content_body=arbitrary,
            first_observation_registry=registry,
            trusted_first_observation_registry_sha256=_canonical_hash(registry),
            reconciliation_inputs=_reconciliation_inputs(),
            parent_root=ROOT,
        )
    assert error.value.code == "form4_forward_admission_content_invalid"


def test_public_progress_is_aggregate_only_and_zero_state() -> None:
    payload = _public()
    assert validate_form4_forward_public_progress(payload) == payload

    inconsistent = copy.deepcopy(payload)
    inconsistent["progress"]["reconciled_observations"] = 3
    _seal(inconsistent)
    assert _error_code(lambda: validate_form4_forward_public_progress(inconsistent)) == (
        "form4_forward_public_schema_invalid"
    )

    nonzero = copy.deepcopy(payload)
    nonzero["state_boundary"]["paper_positions"] = [{"ticker": "FAKE"}]
    _seal(nonzero)
    assert _error_code(lambda: validate_form4_forward_public_progress(nonzero)) == (
        "form4_forward_non_engineering_action_forbidden"
    )


@pytest.mark.parametrize(
    ("key", "expected"),
    [
        ("issuer_cik", "form4_forward_public_identifier_forbidden"),
        ("ticker_symbol", "form4_forward_public_identifier_forbidden"),
        ("accession_number", "form4_forward_public_identifier_forbidden"),
        ("candidate_return", "form4_forward_non_engineering_action_forbidden"),
        ("nav", "form4_forward_non_engineering_action_forbidden"),
        ("sharpe_ratio", "form4_forward_non_engineering_action_forbidden"),
    ],
)
def test_receipt_and_public_progress_reject_identifier_or_performance_keys(
    key: str, expected: str
) -> None:
    admission = _admission()
    admission["content_observation"][key] = 0
    _seal(admission)
    assert _error_code(lambda: _validate(admission)) == expected

    public = _public()
    public["progress"][key] = 0
    _seal(public)
    assert _error_code(lambda: validate_form4_forward_public_progress(public)) == expected


@pytest.mark.parametrize(
    "key",
    [
        "prospective_sessions",
        "fixed_session",
        "minimum_candidate_allocations",
        "minimum_distinct_issuers",
        "readout_eligibility_receipt",
    ],
)
def test_504_100_50_and_readout_progress_fields_are_never_executable(key: str) -> None:
    public = _public()
    public["progress"][key] = 504
    _seal(public)
    assert _error_code(lambda: validate_form4_forward_public_progress(public)) == (
        "form4_forward_non_engineering_action_forbidden"
    )


def test_effective_v1_1_readout_entry_point_always_rejects() -> None:
    assert _error_code(
        lambda: evaluate_readout_gate(
            prospective_sessions=504,
            candidate_allocations=100,
            distinct_issuers_allocated=50,
        )
    ) == "form4_forward_non_engineering_action_forbidden"


def test_exact_schema_rejects_unknown_non_sensitive_keys_and_boolean_counts() -> None:
    admission = _admission()
    admission["unexpected"] = False
    _seal(admission)
    assert _error_code(lambda: _validate(admission)) == (
        "form4_forward_admission_schema_invalid"
    )

    public = _public()
    public["progress"]["content_observations"] = True
    _seal(public)
    assert _error_code(lambda: validate_form4_forward_public_progress(public)) == (
        "form4_forward_public_schema_invalid"
    )
