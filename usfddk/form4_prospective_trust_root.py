from __future__ import annotations

import hashlib
import json
import re
import subprocess
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

PRE_DATA_SCHEMA = "us_fddk.short_term_form4_prospective_predata.v1"
PRE_DATA_STATUS = (
    "protocol_frozen_sec_collection_unauthorized_exact_head_remote_gate_required"
)
PRE_DATA_FROZEN_AT = "2026-08-10T05:14:47Z"
ROUND43_PARENT_COMMIT = "d42b444651a3ccde0f26882c803b58f0daf386a2"
ROUND43_PARENT_REMOTE_REF = "origin/codex/round43-form4-multipath"

PRE_DATA_BINDING_PATHS = {
    "actor_dynamic_selection_design": (
        "docs/SHORT_TERM_ACTOR_DISCLOSURE_DYNAMIC_SELECTION_DESIGN.md"
    ),
    "ci_runtime_tests": "tests/test_ci_runtime_contract.py",
    "dependency_lock": "uv.lock",
    "disclosure_known_at_protocol_v1": (
        "docs/SHORT_TERM_DISCLOSURE_KNOWN_AT_PROTOCOL.md"
    ),
    "disclosure_known_at_protocol_v1_receipt": (
        "artifacts/short_term_disclosure_known_at_protocol_receipt.json"
    ),
    "disclosure_known_at_protocol_v1_1": (
        "docs/SHORT_TERM_DISCLOSURE_KNOWN_AT_PROTOCOL_AMENDMENT_V1_1.md"
    ),
    "disclosure_known_at_protocol_v1_1_receipt": (
        "artifacts/short_term_disclosure_known_at_protocol_amendment_v1_1_receipt.json"
    ),
    "form4_cluster_protocol_v1": "docs/SHORT_TERM_FORM4_CLUSTER_PROTOCOL.md",
    "form4_cluster_protocol_v1_receipt": (
        "artifacts/short_term_form4_cluster_protocol_receipt.json"
    ),
    "form4_cluster_protocol_v1_1": (
        "docs/SHORT_TERM_FORM4_CLUSTER_PROTOCOL_AMENDMENT_V1_1.md"
    ),
    "form4_cluster_protocol_v1_1_receipt": (
        "artifacts/short_term_form4_cluster_protocol_amendment_v1_1_receipt.json"
    ),
    "global_trial_ledger": "artifacts/short_term_global_trial_ledger.json",
    "global_trial_ledger_protocol": "docs/SHORT_TERM_GLOBAL_TRIAL_LEDGER_PROTOCOL.md",
    "legacy_form4_contract_workflow": ".github/workflows/form4-contract-ci.yml",
    "legacy_sec_engineering_client": "usfddk/sec_edgar_client.py",
    "predata_protocol": "docs/SHORT_TERM_FORM4_PROSPECTIVE_TRUST_ROOT_PROTOCOL.md",
    "predata_tests": "tests/test_form4_prospective_trust_root.py",
    "predata_verifier": "usfddk/form4_prospective_trust_root.py",
    "project_metadata": "pyproject.toml",
    "round42_collection_authorization": (
        "docs/SHORT_TERM_FORM4_ADMISSION_COLLECTION_AUTHORIZATION.md"
    ),
    "round42_collection_authorization_receipt": (
        "artifacts/short_term_form4_admission_collection_authorization_receipt.json"
    ),
    "round42_feasibility_protocol": (
        "docs/SHORT_TERM_FORM4_ADMISSION_FEASIBILITY_PROTOCOL.md"
    ),
    "round42_feasibility_protocol_receipt": (
        "artifacts/short_term_form4_admission_feasibility_protocol_receipt.json"
    ),
    "round42_schema_amendment_v1_1": (
        "docs/SHORT_TERM_FORM4_ADMISSION_FEASIBILITY_SCHEMA_AMENDMENT_V1_1.md"
    ),
    "round42_schema_amendment_v1_1_receipt": (
        "artifacts/short_term_form4_admission_feasibility_schema_amendment_v1_1_receipt.json"
    ),
    "round42_stop_validation": (
        "artifacts/short_term_form4_admission_feasibility_validation.json"
    ),
    "round43_multipath_amendment_v1_1": (
        "docs/SHORT_TERM_FORM4_MULTIPATH_FORWARD_PROTOCOL_AMENDMENT_V1_1.md"
    ),
    "round43_multipath_amendment_v1_1_receipt": (
        "artifacts/short_term_form4_multipath_forward_protocol_amendment_v1_1_receipt.json"
    ),
    "round43_multipath_protocol_v1": (
        "docs/SHORT_TERM_FORM4_MULTIPATH_FORWARD_PROTOCOL.md"
    ),
    "round43_multipath_protocol_v1_receipt": (
        "artifacts/short_term_form4_multipath_forward_protocol_receipt.json"
    ),
    "round44_predata_workflow": ".github/workflows/form4-round44-predata-ci.yml",
    "sec_client_tests": "tests/test_sec_edgar_client.py",
}
PRE_DATA_BINDING_KEYS = frozenset(PRE_DATA_BINDING_PATHS)

PRE_DATA_RECEIPT_KEYS = frozenset(
    {
        "schema_version",
        "research_round",
        "phase",
        "status",
        "frozen_at",
        "parent_code_commit",
        "parent_remote_ref",
        "bindings",
        "official_source_contract",
        "lineage_state",
        "remote_gate",
        "monitor_start_boundary",
        "request_policy",
        "evidence_boundary",
        "state_boundary",
        "permission",
        "stable_codes",
        "today_action",
        "receipt_sha256",
    }
)

OFFICIAL_SOURCE_CONTRACT = {
    "accessing_edgar_data_url": (
        "https://www.sec.gov/search-filings/edgar-search-assistance/"
        "accessing-edgar-data"
    ),
    "developer_resources_url": "https://www.sec.gov/about/developer-resources",
    "technical_specifications_url": (
        "https://www.sec.gov/submit-filings/technical-specifications"
    ),
    "ownership_xml_version": "5.5",
    "ownership_xml_effective_date": "2026-03-18",
    "allowed_hosts_after_future_authorization": ["www.sec.gov"],
    "daily_index_directory_template": (
        "https://www.sec.gov/Archives/edgar/daily-index/{year}/QTR{quarter}/"
    ),
    "complete_submission_path_template": (
        "/Archives/edgar/data/{archive_cik}/{accession_no_dashes}/"
        "{accession_with_dashes}.txt"
    ),
    "sec_policy_requests_per_second_ceiling": 10,
    "sec_public_first_available_timestamp_exists": False,
    "sec_public_content_signature_exists": False,
    "acceptance_time_is_known_at": False,
    "filing_date_is_known_at": False,
    "index_filename_date_is_known_at": False,
    "http_headers_are_known_at": False,
}

LINEAGE_STATE = {
    "round41_historical_admission_required": 16,
    "round42_observed_admission_passed": 2,
    "round42_observed_admission_total": 16,
    "round42_status": "stopped_no_admission_claim",
    "round42_restart_or_reuse_allowed": False,
    "round43_evidence_mode": "synthetic_fixture_only",
    "round43_real_evidence_admission_authorized": False,
    "round43_performance_readout_authorized": False,
    "global_trial_lower_bound": 6287,
    "round44_trial_increment": 0,
}

REMOTE_GATE = {
    "authorization_commit_self_embedded": False,
    "authorization_commit_must_be_derived_from_repository_head": True,
    "same_repository_remote_head_must_equal_authorization_commit": True,
    "pull_request_checkout_must_use_exact_head_sha": True,
    "accepted_events_after_exact_checkout": ["pull_request"],
    "same_repository_pull_request_required": True,
    "launch_remote_branch_current_head_recheck_required": True,
    "required_workflow_name": "Form 4 Round44 pre-data CI",
    "required_workflow_path": ".github/workflows/form4-round44-predata-ci.yml",
    "required_job_name": "predata",
    "required_conclusion": "success",
    "required_runner": "ubuntu-24.04",
    "required_python_version": "3.12.12",
    "checkout_action_commit": "3d3c42e5aac5ba805825da76410c181273ba90b1",
    "setup_python_action_commit": "5fda3b95a4ea91299a34e894583c3862153e4b97",
    "setup_uv_action_commit": "c771a70e6277c0a99b617c7a806ffedaca235ff9",
    "github_actions_app_proof_required": True,
    "pages_or_daily_workflow_can_authorize": False,
    "ci_sec_collection_authorized": False,
    "current_exact_suite_sec_request_count": 0,
    "remote_gate_passed_in_this_receipt": False,
}

MONITOR_START_BOUNDARY = {
    "repository_external_owner_only_start_receipt_required": True,
    "create_once_no_overwrite_required": True,
    "external_time_anchor_required": True,
    "empty_attempt_chain_genesis_required": True,
    "actual_account_and_ledger_zero_state_required": True,
    "monitor_start_receipt_created": False,
    "sec_collection_capability_issued": False,
    "sec_collection_enabled": False,
}

REQUEST_POLICY = {
    "predata_sec_request_limit": 0,
    "future_project_requests_per_second_max": 1,
    "future_automatic_retries": 0,
    "future_single_designated_collector_required": True,
    "future_initial_http_status_required": 200,
    "future_full_body_eof_required": True,
    "future_raw_entity_body_sha256_required": True,
    "future_attempt_ledger_append_only_required": True,
    "future_response_receipt_append_only_required": True,
    "future_redirect_chain_receipt_required": True,
    "future_403_or_429_stops_all_sec_access": True,
    "future_fallback_path_allowed": False,
    "future_saved_request_reuse_allowed": False,
}

EVIDENCE_BOUNDARY = {
    "known_at_basis_after_future_start": (
        "max(local_full_body_completed_at, independent_anchor_received_at)"
    ),
    "complete_submission_is_primary_content": True,
    "daily_index_is_discovery_and_reconciliation_only": True,
    "d0_or_d1_can_rewrite_known_at": False,
    "historical_backfill_allowed": False,
    "local_sha256_alone_is_external_trust_root": False,
    "sec_http_200_alone_is_external_trust_root": False,
    "etag_or_last_modified_is_external_trust_root": False,
    "legacy_sec_client_is_round44_production_transport": False,
    "legacy_sec_client_receipt_is_round44_admission": False,
    "prospective_collector_implemented": False,
    "real_evidence_admission_authorized": False,
    "prospective_real_row_admitted": False,
}

STATE_BOUNDARY = {
    "new_sec_request_count": 0,
    "real_identifier_count": 0,
    "real_filing_count": 0,
    "candidate_selection_count": 0,
    "candidate_allocation_count": 0,
    "strategy_run_count": 0,
    "performance_result_present": False,
    "paper_authorized": False,
    "paper_state": "all_cash",
    "paper_positions": [],
    "paper_backfilled_trades": 0,
    "real_money_action_usd": 0,
    "congress_request_count": 0,
    "congress_row_count": 0,
    "congress_field_count": 0,
}

PERMISSION = {
    "predata_protocol_freeze": True,
    "remote_gate_evaluation": True,
    "monitor_start_creation": False,
    "sec_network_collection": False,
    "historical_collection": False,
    "candidate_selection": False,
    "candidate_allocation": False,
    "performance_readout": False,
    "paper": False,
    "real_money": False,
    "congress_collection": False,
}

STABLE_CODES = {
    "authorization": "form4_round44_authorization_invalid",
    "remote_gate": "form4_round44_remote_gate_invalid",
    "start_receipt": "form4_round44_start_receipt_invalid",
    "private_boundary": "form4_round44_private_boundary_invalid",
    "request_plan": "form4_round44_request_plan_drifted",
    "already_started": "form4_round44_already_started",
    "attempt_ledger": "form4_round44_attempt_ledger_invalid",
    "external_anchor": "form4_round44_external_anchor_invalid",
    "response_incomplete": "form4_round44_response_incomplete",
    "cold_replay": "form4_round44_cold_replay_required",
    "public_boundary": "form4_round44_public_boundary_breached",
    "live_network": "sec_live_network_authorization_missing",
    "congress": "form4_forward_congress_field_injection",
    "non_engineering": "form4_forward_non_engineering_action_forbidden",
}

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_ACCESSION = re.compile(r"(?<!\d)\d{10}-\d{2}-\d{6}(?!\d)")
_REAL_IDENTIFIER_KEYS = frozenset(
    {"accession", "cik", "issuer", "owner", "person", "ticker", "symbol", "raw_path"}
)


class Form4ProspectiveTrustRootError(RuntimeError):
    """Fail-closed Round44 pre-data protocol error with one stable code."""

    def __init__(self, code: str, detail: str):
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}")


def _fail(detail: str) -> None:
    raise Form4ProspectiveTrustRootError(
        STABLE_CODES["authorization"],
        detail,
    )


def canonical_sha256(payload: Mapping[str, Any], *, omit: str | None = None) -> str:
    core = {key: value for key, value in payload.items() if key != omit}
    try:
        rendered = json.dumps(
            core,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        _fail(f"receipt is not canonical JSON: {type(exc).__name__}")
    return hashlib.sha256(rendered).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            while chunk := handle.read(1024 * 1024):
                digest.update(chunk)
    except OSError as exc:
        _fail(f"bound file cannot be read: {type(exc).__name__}")
    return digest.hexdigest()


def _canonical_utc(value: object) -> bool:
    if not isinstance(value, str) or not value.endswith("Z"):
        return False
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    if parsed.utcoffset() is None:
        return False
    return parsed.astimezone(UTC).isoformat().replace("+00:00", "Z") == value


def _typed_equal(actual: object, expected: object) -> bool:
    if type(actual) is not type(expected):
        return False
    if isinstance(expected, dict):
        actual_mapping = actual
        return set(actual_mapping) == set(expected) and all(  # type: ignore[arg-type]
            _typed_equal(actual_mapping[key], value)  # type: ignore[index]
            for key, value in expected.items()
        )
    if isinstance(expected, list):
        actual_list = actual
        return len(actual_list) == len(expected) and all(  # type: ignore[arg-type]
            _typed_equal(left, right)
            for left, right in zip(actual_list, expected, strict=True)  # type: ignore[arg-type]
        )
    return actual == expected


def _assert_identifier_free(value: object, *, path: str = "receipt") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if not isinstance(key, str):
                _fail(f"{path} contains a non-string key")
            if key.casefold() in _REAL_IDENTIFIER_KEYS:
                _fail(f"{path} contains a real-identifier field")
            _assert_identifier_free(child, path=f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _assert_identifier_free(child, path=f"{path}[{index}]")
    elif isinstance(value, str) and _ACCESSION.search(value):
        _fail(f"{path} contains an accession-like value")


def _reject_duplicate_json_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            _fail(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _load_exact_json(text: str) -> object:
    try:
        return json.loads(text, object_pairs_hook=_reject_duplicate_json_keys)
    except json.JSONDecodeError as exc:
        _fail(f"pre-data receipt is not valid JSON: {type(exc).__name__}")


def _validate_static_content(receipt: Mapping[str, Any]) -> None:
    if set(receipt) != PRE_DATA_RECEIPT_KEYS:
        _fail("pre-data receipt schema is not exact")
    if (
        receipt.get("schema_version") != PRE_DATA_SCHEMA
        or type(receipt.get("research_round")) is not int
        or receipt.get("research_round") != 44
        or receipt.get("phase") != "predata_protocol_freeze"
        or receipt.get("status") != PRE_DATA_STATUS
        or receipt.get("frozen_at") != PRE_DATA_FROZEN_AT
        or not _canonical_utc(receipt.get("frozen_at"))
        or receipt.get("parent_code_commit") != ROUND43_PARENT_COMMIT
        or receipt.get("parent_remote_ref") != ROUND43_PARENT_REMOTE_REF
        or not _typed_equal(
            receipt.get("official_source_contract"), OFFICIAL_SOURCE_CONTRACT
        )
        or not _typed_equal(receipt.get("lineage_state"), LINEAGE_STATE)
        or not _typed_equal(receipt.get("remote_gate"), REMOTE_GATE)
        or not _typed_equal(
            receipt.get("monitor_start_boundary"), MONITOR_START_BOUNDARY
        )
        or not _typed_equal(receipt.get("request_policy"), REQUEST_POLICY)
        or not _typed_equal(receipt.get("evidence_boundary"), EVIDENCE_BOUNDARY)
        or not _typed_equal(receipt.get("state_boundary"), STATE_BOUNDARY)
        or not _typed_equal(receipt.get("permission"), PERMISSION)
        or not _typed_equal(receipt.get("stable_codes"), STABLE_CODES)
        or receipt.get("today_action") != "今天不下單"
        or receipt.get("receipt_sha256")
        != canonical_sha256(receipt, omit="receipt_sha256")
    ):
        _fail("pre-data receipt content drifted")
    _assert_identifier_free(dict(receipt))


def _validate_bindings(receipt: Mapping[str, Any], root: Path) -> None:
    bindings = receipt.get("bindings")
    if not isinstance(bindings, dict) or set(bindings) != PRE_DATA_BINDING_KEYS:
        _fail("pre-data receipt bindings are incomplete")
    for name, binding in bindings.items():
        if not isinstance(binding, dict) or set(binding) != {"path", "sha256"}:
            _fail(f"binding {name} schema drifted")
        relative = binding.get("path")
        expected = binding.get("sha256")
        if (
            not isinstance(relative, str)
            or relative != PRE_DATA_BINDING_PATHS[name]
            or not isinstance(expected, str)
            or _SHA256.fullmatch(expected) is None
        ):
            _fail(f"binding {name} identity is invalid")
        candidate = (root / relative).resolve()
        try:
            candidate.relative_to(root)
        except ValueError:
            _fail(f"binding {name} escaped the repository")
        if not candidate.is_file() or _sha256_file(candidate) != expected:
            _fail(f"binding {name} bytes drifted")


def validate_predata_authorization(
    receipt_path: str | Path,
    *,
    repository_root: str | Path,
) -> dict[str, Any]:
    """Validate the committed phase-A receipt without authorizing any network call."""

    root = Path(repository_root).resolve()
    path = Path(receipt_path).resolve()
    try:
        path.relative_to(root)
    except ValueError:
        _fail("pre-data receipt must be inside the repository")
    try:
        receipt = _load_exact_json(path.read_text(encoding="utf-8"))
    except OSError as exc:
        _fail(f"pre-data receipt cannot be loaded: {type(exc).__name__}")
    if not isinstance(receipt, dict):
        _fail("pre-data receipt root must be an object")
    _validate_static_content(receipt)
    _validate_bindings(receipt, root)

    ancestry = subprocess.run(
        ["git", "merge-base", "--is-ancestor", ROUND43_PARENT_COMMIT, "HEAD"],
        cwd=root,
        capture_output=True,
        check=False,
    )
    if ancestry.returncode != 0:
        _fail("Round43 parent commit is not an ancestor of HEAD")

    return receipt


def assert_predata_network_locked() -> None:
    """Permanent phase-A guard: this module cannot mint a live SEC capability."""

    raise Form4ProspectiveTrustRootError(
        STABLE_CODES["live_network"],
        "Round44 phase A has no monitor-start receipt or live SEC capability",
    )
