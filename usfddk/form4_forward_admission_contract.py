from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from usfddk.form4_multipath_reconciliation_v2 import (
    FORM4_FORWARD_RECONCILIATION_ERROR_CODES,
    Form4MultipathReconciliationError,
    reconcile_form_index_pair,
)

FORWARD_ADMISSION_SCHEMA = "us_fddk.short_term_form4_forward_admission.v1_1"
FORWARD_PUBLIC_PROGRESS_SCHEMA = (
    "us_fddk.short_term_form4_forward_public_progress.v1_1"
)
FORWARD_SOURCE_SCOPE = ["sec_form_4"]
FORWARD_SOURCE_TYPE = "sec_form_4"
FORWARD_FORM_TYPES = frozenset({"4", "4/A"})
FORWARD_EVIDENCE_MODE = "synthetic_fixture_only"
FORWARD_ADMISSION_AUTHORIZED = False
FORWARD_KNOWN_AT_BASIS = "prospective_local_full_body_first_observed"
FORWARD_CONTENT_OBSERVATION_BASIS = "local_full_body_completion_after_start"
FORWARD_RECONCILIATION_STATUS = "d0_d1_reconciled"
FORWARD_PUBLIC_PROGRESS_STATUS = "prospective_admission_progress_no_performance"
FORWARD_PARENT_CONTRACT: dict[str, object] = {
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
FORWARD_PARENT_PATHS = {
    "historical_v1_protocol_sha256": "docs/SHORT_TERM_FORM4_MULTIPATH_FORWARD_PROTOCOL.md",
    "historical_v1_receipt_file_sha256": (
        "artifacts/short_term_form4_multipath_forward_protocol_receipt.json"
    ),
    "disclosure_protocol_sha256": "docs/SHORT_TERM_DISCLOSURE_KNOWN_AT_PROTOCOL.md",
    "disclosure_receipt_file_sha256": (
        "artifacts/short_term_disclosure_known_at_protocol_receipt.json"
    ),
    "disclosure_amendment_sha256": (
        "docs/SHORT_TERM_DISCLOSURE_KNOWN_AT_PROTOCOL_AMENDMENT_V1_1.md"
    ),
    "disclosure_amendment_receipt_file_sha256": (
        "artifacts/short_term_disclosure_known_at_protocol_amendment_v1_1_receipt.json"
    ),
    "round41_protocol_sha256": "docs/SHORT_TERM_FORM4_CLUSTER_PROTOCOL.md",
    "round41_receipt_file_sha256": "artifacts/short_term_form4_cluster_protocol_receipt.json",
    "round41_amendment_sha256": "docs/SHORT_TERM_FORM4_CLUSTER_PROTOCOL_AMENDMENT_V1_1.md",
    "round41_amendment_receipt_file_sha256": (
        "artifacts/short_term_form4_cluster_protocol_amendment_v1_1_receipt.json"
    ),
    "round42_feasibility_protocol_sha256": (
        "docs/SHORT_TERM_FORM4_ADMISSION_FEASIBILITY_PROTOCOL.md"
    ),
    "round42_feasibility_protocol_receipt_file_sha256": (
        "artifacts/short_term_form4_admission_feasibility_protocol_receipt.json"
    ),
    "round42_schema_amendment_sha256": (
        "docs/SHORT_TERM_FORM4_ADMISSION_FEASIBILITY_SCHEMA_AMENDMENT_V1_1.md"
    ),
    "round42_schema_amendment_receipt_file_sha256": (
        "artifacts/short_term_form4_admission_feasibility_schema_amendment_v1_1_receipt.json"
    ),
    "round42_collection_authorization_sha256": (
        "docs/SHORT_TERM_FORM4_ADMISSION_COLLECTION_AUTHORIZATION.md"
    ),
    "round42_collection_authorization_receipt_file_sha256": (
        "artifacts/short_term_form4_admission_collection_authorization_receipt.json"
    ),
    "round42_validation_file_sha256": (
        "artifacts/short_term_form4_admission_feasibility_validation.json"
    ),
    "round42_report_sha256": "docs/SHORT_TERM_FORM4_ADMISSION_FEASIBILITY_REPORT.md",
    "global_trial_ledger_protocol_sha256": "docs/SHORT_TERM_GLOBAL_TRIAL_LEDGER_PROTOCOL.md",
    "global_trial_ledger_file_sha256": "artifacts/short_term_global_trial_ledger.json",
    "round43_amendment_sha256": (
        "docs/SHORT_TERM_FORM4_MULTIPATH_FORWARD_PROTOCOL_AMENDMENT_V1_1.md"
    ),
}

FORM4_FORWARD_ADMISSION_ERROR_CODES = (
    "form4_forward_admission_schema_invalid",
    "form4_forward_admission_source_scope_invalid",
    "form4_forward_congress_field_injection",
    "form4_forward_admission_timestamp_invalid",
    "form4_forward_admission_content_invalid",
    "form4_forward_admission_reconciliation_invalid",
    "form4_forward_known_at_invented",
    "form4_forward_admission_pre_start_invalid",
    "form4_forward_non_engineering_action_forbidden",
    "form4_forward_admission_receipt_hash_invalid",
    "form4_forward_public_schema_invalid",
    "form4_forward_public_identifier_forbidden",
    *FORM4_FORWARD_RECONCILIATION_ERROR_CODES,
)

_ADMISSION_KEYS = frozenset(
    {
        "schema_version",
        "evidence_mode",
        "admission_authorized",
        "source_scope",
        "source_type",
        "form_type",
        "parent_contract",
        "monitor_started_at",
        "start_receipt_sha256",
        "content_observation",
        "source_times",
        "temporal_classification",
        "reconciliation",
        "data_known_at",
        "data_known_at_basis",
        "state_boundary",
        "receipt_sha256",
    }
)
_CONTENT_KEYS = frozenset(
    {
        "request_started_at",
        "content_full_body_first_observed_at",
        "first_observed_basis",
        "full_body_complete",
        "read_to_eof",
        "hash_verified",
        "byte_count",
        "body_sha256",
        "immutable_object_sha256",
        "first_observation_registry_sha256",
    }
)
_SOURCE_TIME_KEYS = frozenset({"filing_at", "event_at"})
_TEMPORAL_KEYS = frozenset(
    {
        "pre_start_event_date",
        "pre_start_filing_date",
        "historical_event_used_for_backfill",
        "historical_filing_used_for_backfill",
    }
)
_RECONCILIATION_KEYS = frozenset(
    {
        "status",
        "observed_at",
        "d0_d1_complete",
        "content_body_sha256",
        "reconciliation_result_sha256",
    }
)
_STATE_BOUNDARY_KEYS = frozenset(
    {
        "candidate_selection_count",
        "candidate_allocation_count",
        "strategy_run_count",
        "performance_result_present",
        "paper_authorized",
        "paper_state",
        "paper_positions",
        "paper_backfilled_trades",
        "real_money_action_usd",
    }
)
_PUBLIC_KEYS = frozenset(
    {
        "schema_version",
        "evidence_mode",
        "status",
        "source_scope",
        "as_of",
        "start_receipt_sha256",
        "progress",
        "state_boundary",
        "receipt_sha256",
    }
)
_PUBLIC_PROGRESS_KEYS = frozenset(
    {
        "published_form_index_dates_observed",
        "content_observations",
        "reconciled_observations",
        "pre_start_observations",
        "admission_failures",
    }
)

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_CONGRESS_SUBSTRINGS = (
    "congress",
    "lawmaker",
    "legislator",
    "senator",
    "politician",
    "capitol_trade",
)
_CONGRESS_TOKENS = frozenset({"ptr", "house", "senate", "representative"})
_PUBLIC_IDENTIFIER_SUBSTRINGS = (
    "accession",
    "cik",
    "issuer",
    "ticker",
    "symbol",
    "actor",
    "person",
    "owner",
    "security",
    "company",
    "document",
    "raw_text",
    "raw_path",
    "file_path",
    "source_url",
)
_PUBLIC_PERFORMANCE_SUBSTRINGS = (
    "return",
    "performance",
    "pnl",
    "nav",
    "sharpe",
    "sortino",
    "drawdown",
    "cagr",
    "win_rate",
    "alpha",
    "profit",
    "loss",
    "benchmark",
    "allocation",
    "holding",
    "position",
    "trade",
    "weight",
    "price",
)
_ALLOWED_ZERO_BOUNDARY_PATHS = frozenset(
    ("state_boundary", key) for key in _STATE_BOUNDARY_KEYS
)
_NON_ENGINEERING_KEY_SUBSTRINGS = (
    "candidate_selection",
    "candidate_allocation",
    "strategy",
    "performance",
    "distinct_issuers_allocated",
    "performance_engine",
    "readout",
    "paper",
    "real_money",
    "order",
    "position",
    "holding",
    "allocation",
    "trade",
    "shadow",
    "dry_run",
    "portfolio",
    "entry",
    "exit",
)
_OBSOLETE_PROGRESS_KEYS = frozenset(
    {
        "fixed_session",
        "prospective_sessions",
        "minimum_candidate_allocations",
        "minimum_distinct_issuers",
        "candidate_allocations",
        "distinct_issuers_allocated",
        "readout_eligibility_receipt",
    }
)


class Form4ForwardAdmissionContractError(RuntimeError):
    """Fail-closed offline Round 43 admission error with a stable code."""

    def __init__(self, code: str, detail: str):
        if code not in FORM4_FORWARD_ADMISSION_ERROR_CODES:
            raise ValueError("unknown Form 4 forward-admission error code")
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}")


def _fail(code: str, detail: str) -> None:
    raise Form4ForwardAdmissionContractError(code, detail)


def _canonical_hash(payload: Mapping[str, Any], *, omit: str | None = None) -> str:
    value = {key: item for key, item in payload.items() if key != omit}
    try:
        rendered = json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError):
        _fail("form4_forward_admission_schema_invalid", "receipt is not canonical JSON")
    return hashlib.sha256(rendered).hexdigest()


def form4_forward_receipt_sha256(payload: Mapping[str, Any]) -> str:
    """Return the canonical whole-receipt hash, excluding its hash field."""

    return _canonical_hash(payload, omit="receipt_sha256")


def _exact_mapping(
    value: object,
    keys: frozenset[str],
    *,
    code: str,
    label: str,
) -> dict[str, Any]:
    if not isinstance(value, Mapping) or set(value) != keys:
        _fail(code, f"{label} schema is not exact")
    if not all(isinstance(key, str) for key in value):
        _fail(code, f"{label} keys must be strings")
    return dict(value)


def _same_typed_value(actual: object, expected: object) -> bool:
    if type(actual) is not type(expected):
        return False
    if isinstance(expected, Mapping):
        return (
            isinstance(actual, Mapping)
            and set(actual) == set(expected)
            and all(_same_typed_value(actual[key], expected[key]) for key in expected)
        )
    if isinstance(expected, list):
        return isinstance(actual, list) and len(actual) == len(expected) and all(
            _same_typed_value(left, right) for left, right in zip(actual, expected, strict=True)
        )
    return actual == expected


def _normalized_key(value: str) -> tuple[str, set[str]]:
    separated = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", value)
    folded = re.sub(r"[^a-z0-9]+", "_", separated.casefold()).strip("_")
    return folded, set(folded.split("_")) if folded else set()


def _walk_keys(value: object, path: tuple[str, ...] = ()) -> list[tuple[tuple[str, ...], str]]:
    found: list[tuple[tuple[str, ...], str]] = []
    if isinstance(value, Mapping):
        for key, item in value.items():
            if not isinstance(key, str):
                _fail("form4_forward_admission_schema_invalid", "all keys must be strings")
            child = (*path, key)
            found.append((child, key))
            found.extend(_walk_keys(item, child))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            found.extend(_walk_keys(item, (*path, str(index))))
    return found


def _reject_congress_keys(payload: object) -> None:
    for _, key in _walk_keys(payload):
        folded, tokens = _normalized_key(key)
        compact = folded.replace("_", "")
        if any(marker.replace("_", "") in compact for marker in _CONGRESS_SUBSTRINGS) or bool(
            tokens & _CONGRESS_TOKENS
        ) or compact in _CONGRESS_TOKENS:
            _fail(
                "form4_forward_congress_field_injection",
                "Congress-like keys are outside the exact SEC Form 4 scope",
            )
    for value in _walk_string_values(payload):
        folded, tokens = _normalized_key(value)
        compact = folded.replace("_", "")
        if any(marker.replace("_", "") in compact for marker in _CONGRESS_SUBSTRINGS) or bool(
            tokens & _CONGRESS_TOKENS
        ) or compact in _CONGRESS_TOKENS:
            _fail(
                "form4_forward_congress_field_injection",
                "Congress-like source values are outside the exact SEC Form 4 scope",
            )


def _walk_string_values(value: object) -> list[str]:
    found: list[str] = []
    if isinstance(value, Mapping):
        for item in value.values():
            found.extend(_walk_string_values(item))
    elif isinstance(value, list):
        for item in value:
            found.extend(_walk_string_values(item))
    elif isinstance(value, str):
        found.append(value)
    return found


def _reject_non_engineering_keys(payload: object) -> None:
    for path, key in _walk_keys(payload):
        if path[:2] == ("state_boundary", "paper_positions") and len(path) > 2:
            _fail(
                "form4_forward_non_engineering_action_forbidden",
                "Round43 Paper positions must remain an empty list",
            )
        if path in _ALLOWED_ZERO_BOUNDARY_PATHS:
            continue
        folded, _ = _normalized_key(key)
        compact = folded.replace("_", "")
        if folded in _OBSOLETE_PROGRESS_KEYS or any(
            marker.replace("_", "") in compact
            for marker in (*_NON_ENGINEERING_KEY_SUBSTRINGS, *_PUBLIC_PERFORMANCE_SUBSTRINGS)
        ):
            _fail(
                "form4_forward_non_engineering_action_forbidden",
                "candidate, allocation, performance or readout counters are forbidden",
            )


def _reject_public_leak_keys(payload: object) -> None:
    for path, key in _walk_keys(payload):
        if path in _ALLOWED_ZERO_BOUNDARY_PATHS:
            continue
        folded, _ = _normalized_key(key)
        if any(marker in folded for marker in _PUBLIC_IDENTIFIER_SUBSTRINGS):
            _fail(
                "form4_forward_public_identifier_forbidden",
                "identifier-like keys are forbidden from receipts and public progress",
            )
def _canonical_utc(value: object) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        _fail("form4_forward_admission_timestamp_invalid", "timestamp must be canonical UTC")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        _fail("form4_forward_admission_timestamp_invalid", "timestamp is not ISO-8601")
    if parsed.tzinfo is None:
        _fail("form4_forward_admission_timestamp_invalid", "timestamp has no UTC offset")
    normalized = parsed.astimezone(UTC).replace(microsecond=0)
    canonical = normalized.isoformat().replace("+00:00", "Z")
    if parsed.microsecond != 0 or value != canonical:
        _fail(
            "form4_forward_admission_timestamp_invalid",
            "timestamp must be whole-second UTC with a Z suffix",
        )
    return normalized


def _canonical_known_at(value: object) -> datetime:
    try:
        return _canonical_utc(value)
    except Form4ForwardAdmissionContractError:
        _fail(
            "form4_forward_known_at_invented",
            "content full-body first-observed time is missing or non-canonical",
        )


def _sha256(value: object, *, code: str, label: str) -> str:
    if not isinstance(value, str) or _SHA256.fullmatch(value) is None:
        _fail(code, f"{label} must be a lowercase SHA-256")
    return value


def _validate_source_scope(value: object) -> None:
    if type(value) is not list or value != FORWARD_SOURCE_SCOPE:
        _fail(
            "form4_forward_admission_source_scope_invalid",
            "source_scope must be exactly ['sec_form_4']",
        )


def _validate_form_source(*, source_type: object, form_type: object) -> None:
    if (
        type(source_type) is not str
        or source_type != FORWARD_SOURCE_TYPE
        or type(form_type) is not str
        or form_type not in FORWARD_FORM_TYPES
    ):
        _fail(
            "form4_forward_admission_source_scope_invalid",
            "each observation must be one SEC Form 4 or 4/A source",
        )


def _validate_parent_contract(value: object, *, parent_root: Path) -> None:
    if not isinstance(value, Mapping) or not _same_typed_value(value, FORWARD_PARENT_CONTRACT):
        _fail(
            "form4_forward_admission_schema_invalid",
            "the complete frozen parent contract must match exactly",
        )
    for key, relative_path in FORWARD_PARENT_PATHS.items():
        path = parent_root / relative_path
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != value[key]:
            _fail(
                "form4_forward_admission_schema_invalid",
                f"frozen parent byte binding drifted: {relative_path}",
            )


def _validate_first_observation_registry(
    value: object,
    *,
    expected_registry_sha256: object,
    trusted_registry_sha256: object,
    body_sha256: str,
    first_observed_at: str,
) -> None:
    if not isinstance(value, Mapping) or not value:
        _fail(
            "form4_forward_known_at_invented",
            "the create-once first-observation registry is missing",
        )
    registry: dict[str, str] = {}
    for key, item in value.items():
        if not isinstance(key, str) or _SHA256.fullmatch(key) is None:
            _fail(
                "form4_forward_known_at_invented",
                "the first-observation registry has an invalid content hash",
            )
        if not isinstance(item, str):
            _fail(
                "form4_forward_known_at_invented",
                "the first-observation registry has an invalid timestamp",
            )
        try:
            _canonical_utc(item)
        except Form4ForwardAdmissionContractError:
            _fail(
                "form4_forward_known_at_invented",
                "the first-observation registry has a non-canonical timestamp",
            )
        registry[key] = item
    expected_hash = _sha256(
        expected_registry_sha256,
        code="form4_forward_known_at_invented",
        label="first-observation registry hash",
    )
    trusted_hash = _sha256(
        trusted_registry_sha256,
        code="form4_forward_known_at_invented",
        label="trusted owner-only first-observation registry hash",
    )
    if (
        _canonical_hash(registry) != expected_hash
        or trusted_hash != expected_hash
        or registry.get(body_sha256) != first_observed_at
    ):
        _fail(
            "form4_forward_known_at_invented",
            "content first-observed does not match the sealed create-once registry",
        )


def _single_match(pattern: bytes, content_body: bytes, *, label: str) -> str:
    matches = re.findall(pattern, content_body, flags=re.IGNORECASE | re.MULTILINE)
    if len(matches) != 1:
        _fail(
            "form4_forward_admission_content_invalid",
            f"complete submission must contain one canonical {label}",
        )
    value = matches[0]
    if isinstance(value, tuple):
        value = value[0]
    return value.decode("ascii")


def _validate_submission_identity(
    content_body: bytes,
    *,
    form_type: str,
    reconciliation_result: Mapping[str, Any],
) -> None:
    if (
        not content_body.startswith(b"<SEC-DOCUMENT>")
        or b"<SEC-HEADER>" not in content_body
        or not content_body.rstrip().endswith(b"</SEC-DOCUMENT>")
        or b"<XML>" not in content_body
        or b"<ownershipDocument>" not in content_body
        or b"</ownershipDocument>" not in content_body
    ):
        _fail(
            "form4_forward_admission_content_invalid",
            "body is not one complete SEC ownership submission envelope",
        )
    accession = _single_match(
        rb"^<ACCESSION-NUMBER>\s*(\d{10}-\d{2}-\d{6})\s*$",
        content_body,
        label="accession number",
    )
    conformed_form = _single_match(
        rb"^<CONFORMED-SUBMISSION-TYPE>\s*(4(?:/A)?)\s*$",
        content_body,
        label="conformed submission type",
    )
    header_cik = str(
        int(
            _single_match(
                rb"^<CENTRAL-INDEX-KEY>\s*(\d{1,10})\s*$",
                content_body,
                label="header CIK",
            )
        )
    )
    document_type = _single_match(
        rb"<documentType>\s*(4(?:/A)?)\s*</documentType>",
        content_body,
        label="Ownership XML document type",
    )
    _single_match(
        rb"<issuerCik>\s*(\d{1,10})\s*</issuerCik>",
        content_body,
        label="Ownership XML issuer CIK",
    )
    owner_ciks = {
        str(int(value.decode("ascii")))
        for value in re.findall(
            rb"<rptOwnerCik>\s*(\d{1,10})\s*</rptOwnerCik>",
            content_body,
            flags=re.IGNORECASE,
        )
    }
    equivalence = reconciliation_result.get("equivalence_class")
    if not isinstance(equivalence, Mapping):
        _fail(
            "form4_forward_admission_reconciliation_invalid",
            "reconciliation result has no equivalence class",
        )
    members = equivalence.get("members")
    if not isinstance(members, list) or not members:
        _fail(
            "form4_forward_admission_reconciliation_invalid",
            "reconciliation result has no path members",
        )
    member_ciks = {
        member.get("cik") for member in members if isinstance(member, Mapping)
    }
    if (
        accession != reconciliation_result.get("accession")
        or conformed_form != form_type
        or document_type != form_type
        or reconciliation_result.get("form") != form_type
        or not owner_ciks
        or header_cik not in owner_ciks
        or member_ciks != owner_ciks
    ):
        _fail(
            "form4_forward_admission_content_invalid",
            "submission identity does not match Form type, owners and index equivalence class",
        )


def _validate_state_boundary(value: object) -> dict[str, Any]:
    boundary = _exact_mapping(
        value,
        _STATE_BOUNDARY_KEYS,
        code="form4_forward_non_engineering_action_forbidden",
        label="state_boundary",
    )
    integer_zero = (
        "candidate_selection_count",
        "candidate_allocation_count",
        "strategy_run_count",
        "paper_backfilled_trades",
        "real_money_action_usd",
    )
    boolean_false = (
        "performance_result_present",
        "paper_authorized",
    )
    if (
        any(type(boundary[key]) is not int or boundary[key] != 0 for key in integer_zero)
        or any(
            type(boundary[key]) is not bool or boundary[key] is not False
            for key in boolean_false
        )
        or boundary["paper_state"] != "all_cash"
        or type(boundary["paper_positions"]) is not list
        or boundary["paper_positions"] != []
    ):
        _fail(
            "form4_forward_non_engineering_action_forbidden",
            "candidate, strategy, performance, Paper and real-money state must remain exact zero",
        )
    return boundary


def validate_form4_forward_admission_receipt(
    payload: Mapping[str, Any],
    *,
    content_body: bytes,
    first_observation_registry: Mapping[str, str],
    trusted_first_observation_registry_sha256: str,
    reconciliation_inputs: Mapping[str, Any],
    parent_root: str | Path,
) -> dict[str, Any]:
    """Validate a non-authorizing, result-blind structural fixture receipt.

    ``content_body`` must be the exact complete response bytes held in the private
    owner-only store.  This v1.1 implementation is synthetic-only, is offline,
    never writes or fetches data, and cannot admit real evidence.
    """

    _reject_congress_keys(payload)
    _reject_non_engineering_keys(payload)
    content_candidate = payload.get("content_observation")
    if (
        not isinstance(content_candidate, Mapping)
        or not isinstance(
            content_candidate.get("content_full_body_first_observed_at"), str
        )
        or not isinstance(payload.get("data_known_at"), str)
        or not isinstance(payload.get("data_known_at_basis"), str)
    ):
        _fail(
            "form4_forward_known_at_invented",
            "full-body first-observed known-at fields are missing",
        )
    _reject_public_leak_keys(payload)
    receipt = _exact_mapping(
        payload,
        _ADMISSION_KEYS,
        code="form4_forward_admission_schema_invalid",
        label="admission receipt",
    )
    if receipt["schema_version"] != FORWARD_ADMISSION_SCHEMA:
        _fail("form4_forward_admission_schema_invalid", "admission schema version drifted")
    if (
        receipt["evidence_mode"] != FORWARD_EVIDENCE_MODE
        or receipt["admission_authorized"] is not FORWARD_ADMISSION_AUTHORIZED
    ):
        _fail(
            "form4_forward_admission_schema_invalid",
            "v1.1 accepts structural synthetic fixtures but authorizes no real evidence",
        )
    _validate_source_scope(receipt["source_scope"])
    _validate_form_source(
        source_type=receipt["source_type"],
        form_type=receipt["form_type"],
    )
    _validate_parent_contract(receipt["parent_contract"], parent_root=Path(parent_root))
    monitor_started = _canonical_utc(receipt["monitor_started_at"])
    _sha256(
        receipt["start_receipt_sha256"],
        code="form4_forward_admission_schema_invalid",
        label="start receipt hash",
    )

    content = _exact_mapping(
        receipt["content_observation"],
        _CONTENT_KEYS,
        code="form4_forward_admission_content_invalid",
        label="content_observation",
    )
    request_started = _canonical_utc(content["request_started_at"])
    first_observed = _canonical_known_at(
        content["content_full_body_first_observed_at"]
    )
    if request_started < monitor_started or first_observed <= monitor_started:
        _fail(
            "form4_forward_known_at_invented",
            "full-body first-observed must be strictly later than the create-once monitor start",
        )
    if first_observed < request_started:
        _fail(
            "form4_forward_admission_content_invalid",
            "full-body observation precedes request start",
        )
    if (
        content["first_observed_basis"] != FORWARD_CONTENT_OBSERVATION_BASIS
        or type(content["full_body_complete"]) is not bool
        or content["full_body_complete"] is not True
        or type(content["read_to_eof"]) is not bool
        or content["read_to_eof"] is not True
        or type(content["hash_verified"]) is not bool
        or content["hash_verified"] is not True
        or type(content["byte_count"]) is not int
        or content["byte_count"] <= 0
        or not isinstance(content_body, bytes)
        or len(content_body) != content["byte_count"]
    ):
        _fail(
            "form4_forward_admission_content_invalid",
            "content is not one completed, positive-length response body",
        )
    body_sha256 = _sha256(
        content["body_sha256"],
        code="form4_forward_admission_content_invalid",
        label="content body hash",
    )
    immutable_object_sha256 = _sha256(
        content["immutable_object_sha256"],
        code="form4_forward_admission_content_invalid",
        label="immutable content object hash",
    )
    if (
        hashlib.sha256(content_body).hexdigest() != body_sha256
        or immutable_object_sha256 != body_sha256
    ):
        _fail("form4_forward_admission_content_invalid", "content body hash drifted")
    _validate_first_observation_registry(
        first_observation_registry,
        expected_registry_sha256=content["first_observation_registry_sha256"],
        trusted_registry_sha256=trusted_first_observation_registry_sha256,
        body_sha256=body_sha256,
        first_observed_at=content["content_full_body_first_observed_at"],
    )

    source_times = _exact_mapping(
        receipt["source_times"],
        _SOURCE_TIME_KEYS,
        code="form4_forward_admission_pre_start_invalid",
        label="source_times",
    )
    filing_at = _canonical_utc(source_times["filing_at"])
    event_at = _canonical_utc(source_times["event_at"])
    temporal = _exact_mapping(
        receipt["temporal_classification"],
        _TEMPORAL_KEYS,
        code="form4_forward_admission_pre_start_invalid",
        label="temporal_classification",
    )
    expected_filing_pre_start = filing_at < monitor_started
    expected_event_pre_start = event_at < monitor_started
    if (
        type(temporal["pre_start_filing_date"]) is not bool
        or temporal["pre_start_filing_date"] is not expected_filing_pre_start
        or type(temporal["pre_start_event_date"]) is not bool
        or temporal["pre_start_event_date"] is not expected_event_pre_start
        or type(temporal["historical_event_used_for_backfill"]) is not bool
        or temporal["historical_event_used_for_backfill"] is not False
        or type(temporal["historical_filing_used_for_backfill"]) is not bool
        or temporal["historical_filing_used_for_backfill"] is not False
    ):
        _fail(
            "form4_forward_admission_pre_start_invalid",
            "filing/event pre-start classification or no-backfill boundary drifted",
        )

    reconciliation = _exact_mapping(
        receipt["reconciliation"],
        _RECONCILIATION_KEYS,
        code="form4_forward_admission_reconciliation_invalid",
        label="reconciliation",
    )
    reconciliation_observed = _canonical_utc(reconciliation["observed_at"])
    if reconciliation_observed < first_observed:
        _fail(
            "form4_forward_admission_reconciliation_invalid",
            "d0/d1 reconciliation cannot precede content observation",
        )
    if (
        reconciliation["status"] != FORWARD_RECONCILIATION_STATUS
        or type(reconciliation["d0_d1_complete"]) is not bool
        or reconciliation["d0_d1_complete"] is not True
        or reconciliation["content_body_sha256"] != body_sha256
    ):
        _fail(
            "form4_forward_admission_reconciliation_invalid",
            "reconciliation does not bind the completed content body",
        )
    if not isinstance(reconciliation_inputs, Mapping):
        _fail(
            "form4_forward_admission_reconciliation_invalid",
            "reconciliation inputs are missing",
        )
    try:
        reconciliation_result = reconcile_form_index_pair(**dict(reconciliation_inputs))
    except Form4MultipathReconciliationError as error:
        _fail(error.code, error.detail)
    except TypeError:
        _fail(
            "form4_forward_admission_reconciliation_invalid",
            "reconciliation inputs do not match the closed verifier interface",
        )
    _validate_submission_identity(
        content_body,
        form_type=receipt["form_type"],
        reconciliation_result=reconciliation_result,
    )
    supplied_reconciliation_hash = _sha256(
        reconciliation["reconciliation_result_sha256"],
        code="form4_forward_admission_reconciliation_invalid",
        label="reconciliation result hash",
    )
    if _canonical_hash(reconciliation_result) != supplied_reconciliation_hash:
        _fail(
            "form4_forward_admission_reconciliation_invalid",
            "reconciliation receipt does not match a fresh offline d0/d1 replay",
        )

    if (
        receipt["data_known_at_basis"] != FORWARD_KNOWN_AT_BASIS
        or receipt["data_known_at"]
        != content["content_full_body_first_observed_at"]
    ):
        _fail(
            "form4_forward_known_at_invented",
            "known_at must remain the completed-content first-observed time",
        )
    _canonical_known_at(receipt["data_known_at"])
    _validate_state_boundary(receipt["state_boundary"])
    supplied_hash = _sha256(
        receipt["receipt_sha256"],
        code="form4_forward_admission_receipt_hash_invalid",
        label="admission receipt hash",
    )
    if supplied_hash != form4_forward_receipt_sha256(receipt):
        _fail(
            "form4_forward_admission_receipt_hash_invalid",
            "admission receipt hash drifted",
        )
    return deepcopy(receipt)


def _nonnegative_integer(value: object, *, label: str) -> int:
    if type(value) is not int or value < 0:
        _fail("form4_forward_public_schema_invalid", f"{label} must be a non-negative integer")
    return value


def validate_form4_forward_public_progress(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Validate aggregate-only public progress without identifiers or performance."""

    _reject_congress_keys(payload)
    _reject_non_engineering_keys(payload)
    _reject_public_leak_keys(payload)
    receipt = _exact_mapping(
        payload,
        _PUBLIC_KEYS,
        code="form4_forward_public_schema_invalid",
        label="public progress",
    )
    if (
        receipt["schema_version"] != FORWARD_PUBLIC_PROGRESS_SCHEMA
        or receipt["evidence_mode"] != FORWARD_EVIDENCE_MODE
        or receipt["status"] != FORWARD_PUBLIC_PROGRESS_STATUS
    ):
        _fail("form4_forward_public_schema_invalid", "public schema or status drifted")
    _validate_source_scope(receipt["source_scope"])
    _canonical_utc(receipt["as_of"])
    _sha256(
        receipt["start_receipt_sha256"],
        code="form4_forward_public_schema_invalid",
        label="start receipt hash",
    )
    progress = _exact_mapping(
        receipt["progress"],
        _PUBLIC_PROGRESS_KEYS,
        code="form4_forward_public_schema_invalid",
        label="progress",
    )
    published_dates = _nonnegative_integer(
        progress["published_form_index_dates_observed"],
        label="published Form index dates observed",
    )
    content = _nonnegative_integer(progress["content_observations"], label="content observations")
    reconciled = _nonnegative_integer(
        progress["reconciled_observations"], label="reconciled observations"
    )
    pre_start = _nonnegative_integer(
        progress["pre_start_observations"], label="pre-start observations"
    )
    _nonnegative_integer(progress["admission_failures"], label="admission failures")
    if reconciled > content or pre_start > content or (published_dates == 0 and content > 0):
        _fail("form4_forward_public_schema_invalid", "public aggregate counts are inconsistent")
    _validate_state_boundary(receipt["state_boundary"])
    supplied_hash = _sha256(
        receipt["receipt_sha256"],
        code="form4_forward_admission_receipt_hash_invalid",
        label="public progress receipt hash",
    )
    if supplied_hash != form4_forward_receipt_sha256(receipt):
        _fail(
            "form4_forward_admission_receipt_hash_invalid",
            "public progress receipt hash drifted",
        )
    return deepcopy(receipt)


def evaluate_readout_gate(**_: object) -> dict[str, Any]:
    """Reject the superseded v1.0 504/100/50 performance entry point."""

    _fail(
        "form4_forward_non_engineering_action_forbidden",
        "Round43 v1.1 is permanently data-engineering-only and has no readout gate",
    )


__all__ = [
    "FORM4_FORWARD_ADMISSION_ERROR_CODES",
    "FORWARD_ADMISSION_SCHEMA",
    "FORWARD_ADMISSION_AUTHORIZED",
    "FORWARD_CONTENT_OBSERVATION_BASIS",
    "FORWARD_KNOWN_AT_BASIS",
    "FORWARD_PUBLIC_PROGRESS_SCHEMA",
    "FORWARD_PUBLIC_PROGRESS_STATUS",
    "FORWARD_RECONCILIATION_STATUS",
    "FORWARD_SOURCE_SCOPE",
    "FORWARD_SOURCE_TYPE",
    "FORWARD_FORM_TYPES",
    "FORWARD_EVIDENCE_MODE",
    "FORWARD_PARENT_CONTRACT",
    "FORWARD_PARENT_PATHS",
    "Form4ForwardAdmissionContractError",
    "form4_forward_receipt_sha256",
    "evaluate_readout_gate",
    "validate_form4_forward_admission_receipt",
    "validate_form4_forward_public_progress",
]
