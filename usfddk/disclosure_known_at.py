from __future__ import annotations

import csv
import hashlib
import json
import re
import stat
from collections import Counter
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import exchange_calendars as xcals

SCHEMA_VERSION = 1
RESEARCH_ROUND = 40
DISCLOSURE_BUNDLE_ENV = "USFDDK_DISCLOSURE_DATA_BUNDLE"

PROTOCOL_PATH = "docs/SHORT_TERM_DISCLOSURE_KNOWN_AT_PROTOCOL.md"
MANIFEST_SCHEMA_PATH = "schemas/short_term_disclosure_point_in_time_manifest.schema.json"
PROTOCOL_RECEIPT_PATH = "artifacts/short_term_disclosure_known_at_protocol_receipt.json"
PROTOCOL_SHA256 = "ffe2d6df0fce9a305a5a361bc4ce0d377cc9d9afb20246f212031ce57a3949b7"
MANIFEST_SCHEMA_SHA256 = "e86300b2cbb3b6b5d4e6d6cfd394b3e4b5b4badb07098aa9f10e5b6835d67485"
PROTOCOL_RECEIPT_SHA256 = "87f4c322333c8bdf8be12ee9682d49ea22ecce8c6569139a192cebd4892374e7"

SOURCE_TYPES = (
    "congress_house_ptr",
    "congress_senate_ptr",
    "sec_form_4",
    "sec_schedule_13d",
    "sec_schedule_13g",
    "sec_form_13f",
)
OFFICIAL_ENTRY_URLS = {
    "congress_house_ptr": "https://disclosures-clerk.house.gov/FinancialDisclosure",
    "congress_senate_ptr": "https://efdsearch.senate.gov/search/home/",
    "sec_form_4": "https://www.sec.gov/search-filings",
    "sec_schedule_13d": "https://www.sec.gov/search-filings",
    "sec_schedule_13g": "https://www.sec.gov/search-filings",
    "sec_form_13f": "https://www.sec.gov/search-filings",
}
TIMESTAMP_FIELDS = (
    "event_at",
    "filed_at",
    "accepted_at",
    "public_at",
    "first_observed_at",
    "known_at",
    "decision_at",
    "trade_at",
)
KNOWN_AT_BASES = (
    "official_public_timestamp",
    "independent_archived_first_seen",
    "local_first_observed_fallback",
)

REQUIRED_FILES = (
    "disclosure_events.jsonl",
    "source_versions.jsonl",
    "identifier_history.csv",
    "trading_calendar.csv",
    "sanitized_summary.json",
)
GATE_KEYS = (
    "01_protocol_schema_receipt_integrity",
    "02_official_source_semantics_pinned",
    "03_congress_exact_use_legal_clearance",
    "04_source_terms_and_automation_clearance",
    "05_sec_fair_access_client_verified",
    "06_private_quarantine_verified",
    "07_closed_manifest_admitted",
    "08_source_request_receipts_complete",
    "09_stable_document_version_ids",
    "10_eight_timestamps_complete_or_reasoned",
    "11_public_at_evidence_verified",
    "12_known_at_derivation_verified",
    "13_append_only_revision_chain_verified",
    "14_point_in_time_security_mapping_verified",
    "15_source_specific_semantics_verified",
    "16_xnys_decision_entry_clock_verified",
    "17_coverage_lag_missingness_audited",
    "18_public_sanitizer_verified",
    "19_independent_synthetic_attacks_passed",
    "20_authorized_real_sample_accepted",
)
INDEPENDENT_EVIDENCE_REQUIRED = {
    "03_congress_exact_use_legal_clearance": "independent_legal_clearance_receipt_missing",
    "04_source_terms_and_automation_clearance": "independent_terms_clearance_receipts_missing",
    "05_sec_fair_access_client_verified": "independent_sec_client_runtime_receipt_missing",
    "06_private_quarantine_verified": "independent_quarantine_verification_receipt_missing",
    "08_source_request_receipts_complete": "external_source_request_receipts_missing",
    "09_stable_document_version_ids": "external_document_version_anchor_missing",
    "10_eight_timestamps_complete_or_reasoned": "timestamp_source_evidence_missing",
    "11_public_at_evidence_verified": "external_public_at_evidence_payload_missing",
    "12_known_at_derivation_verified": "independent_known_at_evidence_missing",
    "13_append_only_revision_chain_verified": "external_prior_chain_anchor_missing",
    "14_point_in_time_security_mapping_verified": "external_security_mapping_evidence_missing",
    "15_source_specific_semantics_verified": "source_semantics_evidence_incomplete",
    "16_xnys_decision_entry_clock_verified": "trusted_known_at_clock_missing",
    "17_coverage_lag_missingness_audited": "independent_coverage_denominator_missing",
    "18_public_sanitizer_verified": "independent_sanitizer_verification_receipt_missing",
    "19_independent_synthetic_attacks_passed": "independent_attack_execution_receipt_missing",
    "20_authorized_real_sample_accepted": "authorized_real_sample_external_receipt_missing",
}

MANIFEST_KEYS = {
    "schema_version",
    "contract_id",
    "phase",
    "bundle_id",
    "generated_at",
    "legal_use",
    "sec_access",
    "coverage",
    "source_receipts",
    "normalized_record_contract",
    "timestamp_contract",
    "revision_contract",
    "privacy_contract",
    "files",
    "readiness_boundary",
}
LEGAL_KEYS = {
    "exact_use_description",
    "commercial_use_review_status",
    "congress_use_review_status",
    "source_terms_reviewed",
    "reviewed_at",
    "expires_at",
    "authority_reference",
    "evidence_sha256",
}
SEC_ACCESS_KEYS = {
    "user_agent_contact_declared",
    "sec_policy_ceiling_requests_per_second",
    "configured_requests_per_second",
    "global_across_processes_and_machines",
    "cache_enabled",
    "retry_after_and_429_backoff",
    "stop_on_403_or_robots_terms_change",
}
COVERAGE_KEYS = {
    "claim",
    "complete_period_claimed",
    "twenty_year_coverage_claimed",
    "twenty_year_coverage_validated",
    "observed_start",
    "observed_end",
}
SOURCE_RECEIPT_KEYS = {
    "source_type",
    "official_entry_url",
    "request_url",
    "collected_at",
    "first_observed_at",
    "http_status",
    "content_type",
    "content_sha256",
    "byte_count",
    "record_count",
    "request_receipt_sha256",
    "terms_snapshot_sha256",
    "legal_use_approved",
    "raw_payload_location",
}
NORMALIZED_CONTRACT_KEYS = {
    "format",
    "source_type_values",
    "required_fields",
    "unknown_value_policy",
}
TIMESTAMP_CONTRACT_KEYS = {
    "timezone",
    "calendar",
    "required_timestamp_fields",
    "known_at_basis_values",
    "known_at_rule",
    "decision_at_rule",
    "trade_at_rule",
}
REVISION_CONTRACT_KEYS = {
    "append_only",
    "original_versions_preserved",
    "hash_algorithm",
    "canonicalization",
    "genesis_previous_sha256",
    "chain_head_sha256",
    "revision_count",
    "final_revised_strategy_substitution_allowed",
}
PRIVACY_CONTRACT_KEYS = {
    "raw_payload_location",
    "raw_data_allowed_in_git_ci_site",
    "internal_actor_key",
    "actor_salt_allowed_in_git",
    "minimum_distinct_actor_count_for_public_aggregate",
    "public_output",
    "public_forbidden_fields",
}
FILE_RECEIPT_KEYS = {"sha256", "rows", "bytes"}
READINESS_BOUNDARY_KEYS = {
    "manifest_format_pass_implies_data_truth",
    "strategy_defined",
    "strategy_run_count",
    "formal_backtest_authorized",
    "paper_authorized",
    "paper_state",
    "paper_positions",
    "backfilled_trades",
    "real_money_action_usd",
    "today_action",
}

SOURCE_VERSION_KEYS = {
    "source_type",
    "source_document_id",
    "source_version_id",
    "supersedes_version_id",
    "document_type",
    "accession_number",
    "request_receipt_sha256",
    "content_sha256",
    "record_count",
    "filed_at",
    "accepted_at",
    "public_at",
    "public_at_evidence_type",
    "public_at_evidence_sha256",
    "independent_archived_first_seen_at",
    "independent_archived_evidence_sha256",
    "first_observed_at",
    "known_at",
    "known_at_basis",
    "previous_chain_sha256",
    "chain_sha256",
}
EVENT_KEYS = {
    "source_type",
    "source_event_id",
    "source_document_id",
    "source_version_id",
    "supersedes_version_id",
    "security_id",
    "security_link_id",
    "actor_token",
    "actor_role",
    "actor_eligibility",
    "economic_semantics",
    "transaction_code",
    "ownership_nature",
    "acquired_disposed_code",
    "filing_category",
    "value_min_usd",
    "value_max_usd",
    "event_precision",
    "reported_event_date",
    "reported_period_end",
    "event_at",
    "filed_at",
    "accepted_at",
    "public_at",
    "first_observed_at",
    "known_at",
    "known_at_basis",
    "decision_at",
    "trade_at",
    "null_reasons",
}
ACTOR_ELIGIBILITY_KEYS = {
    "actor_type",
    "eligible_from",
    "eligible_to",
    "known_at",
    "source_record_id",
}
NULL_REASON_KEYS = {"event_at", "filed_at", "accepted_at", "public_at"}
IDENTIFIER_COLUMNS = (
    "security_link_id",
    "source_type",
    "source_security_id",
    "security_id",
    "company_id",
    "ticker",
    "exchange",
    "share_class",
    "cusip",
    "cik",
    "effective_from",
    "effective_to",
    "known_at",
    "source_record_id",
)
CALENDAR_COLUMNS = ("session", "open_at", "close_at")

SUMMARY_KEYS = {
    "schema_version",
    "bundle_id",
    "generated_at",
    "source_audits",
    "privacy_audit",
    "independent_attacks",
    "authorized_real_sample",
}
SOURCE_AUDIT_KEYS = {
    "source_type",
    "observed_start",
    "observed_end",
    "expected_documents",
    "observed_documents",
    "missing_documents",
    "late_filings",
    "amendments",
    "confidential_treatment_items",
    "event_lag_count",
    "lag_unresolved_count",
    "distinct_actor_count",
    "public_statistics_suppressed",
}
PRIVACY_AUDIT_KEYS = {
    "forbidden_key_scan_passed",
    "site_bundle_scan_passed",
    "source_map_scan_passed",
    "manual_reviewed_at",
    "manual_reviewer_receipt_sha256",
    "minimum_actor_threshold",
    "raw_rows_in_summary",
    "selected_tickers",
    "actor_names",
}
ATTACK_AUDIT_KEYS = {
    "rejected",
    "total",
    "all_rejected",
    "exact_error_codes",
    "independent_reviewer_receipt_sha256",
}
SAMPLE_AUDIT_KEYS = {
    "accepted",
    "synthetic",
    "row_count",
    "reviewed_at",
    "reviewer_receipt_sha256",
}

DOCUMENT_TYPES = {
    "congress_house_ptr": {"PTR"},
    "congress_senate_ptr": {"PTR"},
    "sec_form_4": {"FORM4", "FORM4_A"},
    "sec_schedule_13d": {"SC_13D", "SC_13D_A"},
    "sec_schedule_13g": {"SC_13G", "SC_13G_A"},
    "sec_form_13f": {"13F_HR", "13F_HR_A"},
}
AMENDMENT_BASE = {
    "FORM4_A": "FORM4",
    "SC_13D_A": "SC_13D",
    "SC_13G_A": "SC_13G",
    "13F_HR_A": "13F_HR",
}
ACTOR_TYPE_BY_SOURCE = {
    "congress_house_ptr": "us_legislator",
    "congress_senate_ptr": "us_legislator",
    "sec_form_4": "sec_reporting_insider",
    "sec_schedule_13d": "beneficial_owner",
    "sec_schedule_13g": "beneficial_owner",
    "sec_form_13f": "institutional_manager",
}
ACTOR_ROLES = {
    "congress_house_ptr": {"us_representative"},
    "congress_senate_ptr": {"us_senator"},
    "sec_form_4": {"director", "officer", "ten_percent_owner", "officer_director"},
    "sec_schedule_13d": {"beneficial_owner"},
    "sec_schedule_13g": {"beneficial_owner"},
    "sec_form_13f": {"institutional_investment_manager"},
}
FORM4_SEMANTICS = {
    "P": "open_market_purchase",
    "S": "open_market_sale",
    "A": "grant_or_other_acquisition_non_signal",
    "D": "disposition_to_issuer_or_other_non_signal",
    "F": "tax_or_exercise_price_withholding_non_signal",
    "G": "gift_non_signal",
    "M": "derivative_exercise_or_conversion_non_signal",
    "C": "derivative_conversion_non_signal",
    "X": "in_the_money_derivative_exercise_non_signal",
}
PTR_SEMANTICS = {"P": "purchase_range", "S": "sale_range", "E": "exchange_range"}
PTR_AMOUNT_BANDS = {
    (1_001.0, 15_000.0),
    (15_001.0, 50_000.0),
    (50_001.0, 100_000.0),
    (100_001.0, 250_000.0),
    (250_001.0, 500_000.0),
    (500_001.0, 1_000_000.0),
    (1_000_001.0, 5_000_000.0),
    (5_000_001.0, 25_000_000.0),
    (25_000_001.0, 50_000_000.0),
    (50_000_001.0, None),
}
SOURCE_SEMANTICS = {
    "sec_schedule_13d": ("OWNERSHIP", "beneficial_ownership_control_intent_snapshot"),
    "sec_schedule_13g": ("OWNERSHIP", "beneficial_ownership_reporting_snapshot"),
    "sec_form_13f": ("HOLDING", "quarter_end_institutional_holding_snapshot"),
}

SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
OFFSET_PATTERN = re.compile(r"(?:Z|[+-]\d{2}:\d{2})$")
DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")
ACCESSION_PATTERN = re.compile(r"^\d{10}-\d{2}-\d{6}$")
OPAQUE_ACTOR_PATTERN = re.compile(r"^act_[0-9a-f]{16,64}$")
CUSIP_PATTERN = re.compile(r"^[0-9A-Z*@#]{8,9}$")
CIK_PATTERN = re.compile(r"^\d{10}$")
GENESIS_SHA256 = "0" * 64


class DisclosureKnownAtError(ValueError):
    """Fail-closed disclosure intake error with a stable semantic code."""

    def __init__(self, code: str, detail: str):
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}")


def _fail(code: str, detail: str) -> None:
    raise DisclosureKnownAtError(code, detail)


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _timestamp(value: Any, *, field_name: str, code: str) -> datetime:
    if not isinstance(value, str) or OFFSET_PATTERN.search(value) is None:
        _fail(code, f"{field_name} must be an offset-aware timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        _fail(code, f"{field_name} is not a valid timestamp")
    if parsed.tzinfo is None:
        _fail(code, f"{field_name} has no timezone")
    return parsed.astimezone(UTC)


def _optional_timestamp(value: Any, *, field_name: str, code: str) -> datetime | None:
    if value is None:
        return None
    return _timestamp(value, field_name=field_name, code=code)


def _exact(value: Any, keys: set[str], *, label: str, code: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != keys:
        _fail(code, f"{label} fields are not exact")
    return value


def _nonempty(value: Any, *, field_name: str, code: str) -> str:
    if not isinstance(value, str) or not value.strip():
        _fail(code, f"{field_name} must be a non-empty string")
    return value


def _sha_ok(value: Any) -> bool:
    return isinstance(value, str) and SHA256_PATTERN.fullmatch(value) is not None


def _canonical_sha256(value: Mapping[str, Any]) -> str:
    rendered = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode()
    return hashlib.sha256(rendered).hexdigest()


def _jsonl(path: Path, *, code: str) -> list[dict[str, Any]]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        _fail(code, f"cannot read {path.name}: {type(exc).__name__}")
    if not lines or any(not line.strip() for line in lines):
        _fail(code, f"{path.name} is empty or contains blank rows")
    rows: list[dict[str, Any]] = []
    for line in lines:
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            _fail(code, f"{path.name} contains invalid JSON")
        if not isinstance(row, dict):
            _fail(code, f"{path.name} rows must be objects")
        rows.append(row)
    return rows


def _csv_rows(path: Path, columns: tuple[str, ...], *, code: str) -> list[dict[str, str]]:
    try:
        with path.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            if tuple(reader.fieldnames or ()) != columns:
                _fail(code, f"{path.name} columns are not exact")
            rows = list(reader)
    except OSError as exc:
        _fail(code, f"cannot read {path.name}: {type(exc).__name__}")
    if not rows or any(set(row) != set(columns) for row in rows):
        _fail(code, f"{path.name} has no valid rows")
    return rows


def _inside(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def _external_bundle(path: str | Path, *, root: Path) -> Path:
    candidate = Path(path)
    if not candidate.is_absolute():
        _fail("bundle_path_not_absolute", "raw bundle path must be absolute")
    if candidate.is_symlink():
        _fail("bundle_symlink_or_special_file", "raw bundle cannot be a symlink")
    try:
        resolved = candidate.resolve(strict=True)
    except OSError:
        _fail("bundle_missing", "configured raw bundle does not exist")
    if not resolved.is_dir():
        _fail("bundle_not_directory", "configured raw bundle is not a directory")
    if _inside(resolved, root.resolve()):
        _fail("bundle_inside_repository", "raw bundle must remain repository-external")
    for item in resolved.iterdir():
        mode = item.lstat().st_mode
        if stat.S_ISLNK(mode) or not stat.S_ISREG(mode):
            _fail("bundle_symlink_or_special_file", "bundle contains a link or special file")
    return resolved


def _protocol_integrity(root: Path) -> None:
    code = "protocol_schema_receipt_mismatch"
    try:
        receipt_path = root / PROTOCOL_RECEIPT_PATH
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        hashes_ok = (
            _sha256_file(root / PROTOCOL_PATH) == PROTOCOL_SHA256
            and _sha256_file(root / MANIFEST_SCHEMA_PATH) == MANIFEST_SCHEMA_SHA256
            and _sha256_file(receipt_path) == PROTOCOL_RECEIPT_SHA256
            and receipt["protocol"] == {"path": PROTOCOL_PATH, "sha256": PROTOCOL_SHA256}
            and receipt["manifest_schema"]
            == {"path": MANIFEST_SCHEMA_PATH, "sha256": MANIFEST_SCHEMA_SHA256}
        )
        readiness = receipt["actual_disclosure_readiness"]
        frozen = (
            receipt["schema_version"] == 1
            and receipt["protocol_phase"] == 1
            and receipt["status"]
            == "frozen_after_official_documentation_review_before_any_disclosure_data_fetch_or_strategy_design"
            and receipt["source_types"] == list(SOURCE_TYPES)
            and receipt["timestamp_fields"] == list(TIMESTAMP_FIELDS)
            and readiness["passed"] == 2
            and readiness["total"] == 20
            and readiness["all_passed"] is False
            and readiness["passed_gate_ids"] == list(GATE_KEYS[:2])
            and readiness["blocked_gate_ids"] == list(GATE_KEYS[2:])
            and hashes_ok
        )
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError):
        frozen = False
    if not frozen:
        _fail(code, "frozen protocol, schema, or receipt does not match")


def _official_semantics_pinned(root: Path) -> None:
    receipt = json.loads((root / PROTOCOL_RECEIPT_PATH).read_text(encoding="utf-8"))
    source_rows = receipt["official_sources"]
    if (
        receipt["source_types"] != list(SOURCE_TYPES)
        or len(source_rows) < len(SOURCE_TYPES)
        or any(not row.get("url", "").startswith("https://") for row in source_rows)
        or any(not row.get("semantic_role") for row in source_rows)
    ):
        _fail("official_source_semantics_mismatch", "all six source semantics are not pinned")


@dataclass
class _State:
    root: Path
    bundle: Path
    manifest: dict[str, Any] = field(default_factory=dict)
    versions: list[dict[str, Any]] = field(default_factory=list)
    events: list[dict[str, Any]] = field(default_factory=list)
    identifiers: list[dict[str, str]] = field(default_factory=list)
    calendar: list[dict[str, str]] = field(default_factory=list)
    summary: dict[str, Any] = field(default_factory=dict)
    version_times: dict[str, dict[str, datetime | None]] = field(default_factory=dict)
    event_times: dict[str, dict[str, datetime | None]] = field(default_factory=dict)
    identifier_times: dict[str, dict[str, datetime | None]] = field(default_factory=dict)
    calendar_times: list[tuple[str, datetime, datetime]] = field(default_factory=list)


def _load_manifest(state: _State) -> None:
    try:
        value = json.loads((state.bundle / "manifest.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        _fail("manifest_schema_mismatch", "manifest.json is unreadable")
    state.manifest = _exact(value, MANIFEST_KEYS, label="manifest", code="manifest_schema_mismatch")


def _validate_manifest_contract(state: _State) -> None:
    code = "manifest_schema_mismatch"
    m = state.manifest
    if (
        m["schema_version"] != 1
        or m["contract_id"] != "us_fddk.short_term_disclosure_known_at.v1"
        or m["phase"] != "known_at_readiness_only"
        or not isinstance(m["bundle_id"], str)
        or re.fullmatch(r"[a-z0-9][a-z0-9._-]{7,127}", m["bundle_id"]) is None
    ):
        _fail(code, "manifest identity fields do not match")
    generated = _timestamp(m["generated_at"], field_name="generated_at", code=code)
    legal = _exact(m["legal_use"], LEGAL_KEYS, label="legal_use", code=code)
    sec = _exact(m["sec_access"], SEC_ACCESS_KEYS, label="sec_access", code=code)
    coverage = _exact(m["coverage"], COVERAGE_KEYS, label="coverage", code=code)
    normalized = _exact(
        m["normalized_record_contract"], NORMALIZED_CONTRACT_KEYS, label="normalized contract", code=code
    )
    timestamps = _exact(
        m["timestamp_contract"], TIMESTAMP_CONTRACT_KEYS, label="timestamp contract", code=code
    )
    revision = _exact(
        m["revision_contract"], REVISION_CONTRACT_KEYS, label="revision contract", code=code
    )
    privacy = _exact(
        m["privacy_contract"], PRIVACY_CONTRACT_KEYS, label="privacy contract", code=code
    )
    boundary = _exact(
        m["readiness_boundary"], READINESS_BOUNDARY_KEYS, label="readiness boundary", code=code
    )
    reviewed = _timestamp(legal["reviewed_at"], field_name="reviewed_at", code=code)
    expires = _timestamp(legal["expires_at"], field_name="expires_at", code=code)
    if not reviewed <= generated < expires:
        _fail(code, "legal review is expired or post-dates the bundle")
    if not _sha_ok(legal["evidence_sha256"]):
        _fail(code, "legal evidence receipt is invalid")
    expected_legal = {
        "commercial_use_review_status": "approved_for_exact_use",
        "congress_use_review_status": "approved_for_exact_use",
        "source_terms_reviewed": True,
    }
    if any(legal[key] != value for key, value in expected_legal.items()):
        _fail(code, "legal-use constants do not match")
    _nonempty(legal["exact_use_description"], field_name="exact_use_description", code=code)
    _nonempty(legal["authority_reference"], field_name="authority_reference", code=code)
    if sec != {
        "user_agent_contact_declared": True,
        "sec_policy_ceiling_requests_per_second": 10,
        "configured_requests_per_second": sec["configured_requests_per_second"],
        "global_across_processes_and_machines": True,
        "cache_enabled": True,
        "retry_after_and_429_backoff": True,
        "stop_on_403_or_robots_terms_change": True,
    } or isinstance(sec["configured_requests_per_second"], bool) or not isinstance(
        sec["configured_requests_per_second"], (int, float)
    ) or not 0 < sec["configured_requests_per_second"] <= 10:
        _fail(code, "SEC access contract does not match")
    if coverage != {
        "claim": "observed_records_only_no_complete_period_claim",
        "complete_period_claimed": False,
        "twenty_year_coverage_claimed": False,
        "twenty_year_coverage_validated": False,
        "observed_start": coverage["observed_start"],
        "observed_end": coverage["observed_end"],
    }:
        _fail(code, "coverage boundary does not match")
    for name in ("observed_start", "observed_end"):
        if coverage[name] is not None and (
            not isinstance(coverage[name], str) or DATE_PATTERN.fullmatch(coverage[name]) is None
        ):
            _fail(code, f"{name} is not a date or null")
    required_fields = [
        "source_type",
        "source_document_id",
        "source_version_id",
        "supersedes_version_id",
        "security_id",
        "actor_token",
        "actor_role",
        "economic_semantics",
        "transaction_code",
        "ownership_nature",
        "value_min_usd",
        "value_max_usd",
        "event_precision",
        "event_at",
        "filed_at",
        "accepted_at",
        "public_at",
        "first_observed_at",
        "known_at",
        "known_at_basis",
        "decision_at",
        "trade_at",
    ]
    if normalized != {
        "format": "utf8_jsonl_one_object_per_line",
        "source_type_values": list(SOURCE_TYPES),
        "required_fields": required_fields,
        "unknown_value_policy": "explicit_null_with_source_reason_no_imputation",
    }:
        _fail(code, "normalized record contract does not match")
    if timestamps != {
        "timezone": "UTC",
        "calendar": "XNYS",
        "required_timestamp_fields": list(TIMESTAMP_FIELDS),
        "known_at_basis_values": list(KNOWN_AT_BASES),
        "known_at_rule": "official_public_timestamp_else_independent_archived_first_seen_else_local_first_observed",
        "decision_at_rule": "first_official_xnys_close_strictly_after_known_at",
        "trade_at_rule": "next_official_xnys_open_after_decision_at",
    }:
        _fail(code, "timestamp contract does not match")
    expected_revision = {
        "append_only": True,
        "original_versions_preserved": True,
        "hash_algorithm": "sha256",
        "canonicalization": "utf8_json_sorted_keys_compact_separators_no_nan",
        "genesis_previous_sha256": GENESIS_SHA256,
        "chain_head_sha256": revision["chain_head_sha256"],
        "revision_count": revision["revision_count"],
        "final_revised_strategy_substitution_allowed": False,
    }
    if revision != expected_revision or not _sha_ok(revision["chain_head_sha256"]) or (
        not isinstance(revision["revision_count"], int)
        or isinstance(revision["revision_count"], bool)
        or revision["revision_count"] < 0
    ):
        _fail(code, "revision contract does not match")
    forbidden = [
        "person_name",
        "street_address",
        "signature",
        "family_member_name",
        "spouse_or_dependent_label",
        "actor_token",
        "ticker",
        "cusip",
        "cik",
        "accession_number",
        "source_document_id",
        "source_document_url",
        "raw_document_body",
    ]
    if privacy != {
        "raw_payload_location": "encrypted_private_quarantine_not_git_ci_site",
        "raw_data_allowed_in_git_ci_site": False,
        "internal_actor_key": "salted_nonreversible_actor_token",
        "actor_salt_allowed_in_git": False,
        "minimum_distinct_actor_count_for_public_aggregate": 10,
        "public_output": "source_family_readiness_lag_missingness_revision_and_compliance_aggregates_only",
        "public_forbidden_fields": forbidden,
    }:
        _fail(code, "privacy contract does not match")
    if boundary != {
        "manifest_format_pass_implies_data_truth": False,
        "strategy_defined": False,
        "strategy_run_count": 0,
        "formal_backtest_authorized": False,
        "paper_authorized": False,
        "paper_state": "all_cash",
        "paper_positions": [],
        "backfilled_trades": 0,
        "real_money_action_usd": 0,
        "today_action": "today_no_trade",
    }:
        _fail(code, "readiness decision boundary does not match")
    files = m["files"]
    if not isinstance(files, dict) or set(files) != set(REQUIRED_FILES):
        _fail(code, "manifest file set is not exact")
    for receipt in files.values():
        receipt = _exact(receipt, FILE_RECEIPT_KEYS, label="file receipt", code=code)
        if (
            not _sha_ok(receipt["sha256"])
            or not isinstance(receipt["rows"], int)
            or isinstance(receipt["rows"], bool)
            or receipt["rows"] < 0
            or not isinstance(receipt["bytes"], int)
            or isinstance(receipt["bytes"], bool)
            or receipt["bytes"] < 0
        ):
            _fail(code, "manifest file receipt is invalid")


def _validate_legal_gate(state: _State) -> None:
    code = "congress_legal_clearance_invalid"
    legal = _exact(state.manifest.get("legal_use"), LEGAL_KEYS, label="legal use", code=code)
    reviewed = _timestamp(legal["reviewed_at"], field_name="reviewed_at", code=code)
    expires = _timestamp(legal["expires_at"], field_name="expires_at", code=code)
    generated = _timestamp(
        state.manifest["generated_at"], field_name="generated_at", code=code
    )
    if (
        legal["commercial_use_review_status"] != "approved_for_exact_use"
        or legal["congress_use_review_status"] != "approved_for_exact_use"
        or legal["source_terms_reviewed"] is not True
        or not reviewed <= generated < expires
        or not _sha_ok(legal["evidence_sha256"])
        or not isinstance(legal["exact_use_description"], str)
        or not legal["exact_use_description"].strip()
        or not isinstance(legal["authority_reference"], str)
        or not legal["authority_reference"].strip()
    ):
        _fail(code, "exact-use written clearance is missing, invalid, or expired")


def _validate_terms_gate(state: _State) -> None:
    code = "source_terms_clearance_invalid"
    receipts = state.manifest.get("source_receipts")
    if not isinstance(receipts, dict) or list(receipts) != list(SOURCE_TYPES):
        _fail(code, "source terms do not cover the exact six sources")
    for source_type, receipt in receipts.items():
        receipt = _exact(receipt, SOURCE_RECEIPT_KEYS, label="source receipt", code=code)
        if (
            receipt["source_type"] != source_type
            or receipt["official_entry_url"] != OFFICIAL_ENTRY_URLS[source_type]
            or receipt["legal_use_approved"] is not True
            or not _sha_ok(receipt["terms_snapshot_sha256"])
            or receipt["raw_payload_location"] != "private_quarantine_not_git_ci_site"
        ):
            _fail(code, "source terms, legal-use, or storage receipt is invalid")


def _validate_sec_gate(state: _State) -> None:
    code = "sec_fair_access_invalid"
    access = _exact(
        state.manifest.get("sec_access"), SEC_ACCESS_KEYS, label="SEC access", code=code
    )
    rate = access["configured_requests_per_second"]
    if (
        access["user_agent_contact_declared"] is not True
        or access["sec_policy_ceiling_requests_per_second"] != 10
        or isinstance(rate, bool)
        or not isinstance(rate, (int, float))
        or not 0 < rate <= 10
        or access["global_across_processes_and_machines"] is not True
        or access["cache_enabled"] is not True
        or access["retry_after_and_429_backoff"] is not True
        or access["stop_on_403_or_robots_terms_change"] is not True
    ):
        _fail(code, "SEC Fair Access controls are incomplete")


def _validate_private_gate(state: _State) -> None:
    code = "private_quarantine_invalid"
    privacy = _exact(
        state.manifest.get("privacy_contract"),
        PRIVACY_CONTRACT_KEYS,
        label="privacy contract",
        code=code,
    )
    if (
        privacy["raw_payload_location"]
        != "encrypted_private_quarantine_not_git_ci_site"
        or privacy["raw_data_allowed_in_git_ci_site"] is not False
        or privacy["internal_actor_key"] != "salted_nonreversible_actor_token"
        or privacy["actor_salt_allowed_in_git"] is not False
        or privacy["minimum_distinct_actor_count_for_public_aggregate"] != 10
    ):
        _fail(code, "private quarantine or actor-token boundary is invalid")


def _validate_exact_files(state: _State) -> None:
    code = "file_receipt_mismatch"
    if {item.name for item in state.bundle.iterdir()} != {"manifest.json", *REQUIRED_FILES}:
        _fail(code, "bundle file set is not exact")
    state.events = _jsonl(state.bundle / "disclosure_events.jsonl", code=code)
    state.versions = _jsonl(state.bundle / "source_versions.jsonl", code=code)
    state.identifiers = _csv_rows(
        state.bundle / "identifier_history.csv", IDENTIFIER_COLUMNS, code=code
    )
    state.calendar = _csv_rows(
        state.bundle / "trading_calendar.csv", CALENDAR_COLUMNS, code=code
    )
    try:
        summary = json.loads((state.bundle / "sanitized_summary.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        _fail(code, "sanitized_summary.json is unreadable")
    if not isinstance(summary, dict):
        _fail(code, "sanitized summary must be an object")
    state.summary = summary
    row_counts = {
        "disclosure_events.jsonl": len(state.events),
        "source_versions.jsonl": len(state.versions),
        "identifier_history.csv": len(state.identifiers),
        "trading_calendar.csv": len(state.calendar),
        "sanitized_summary.json": 1,
    }
    for name in REQUIRED_FILES:
        path = state.bundle / name
        if state.manifest["files"][name] != {
            "sha256": _sha256_file(path),
            "rows": row_counts[name],
            "bytes": len(path.read_bytes()),
        }:
            _fail(code, "a file receipt does not match bytes, rows, and SHA-256")


def _validate_source_receipts(state: _State) -> None:
    code = "source_request_receipt_invalid"
    receipts = state.manifest["source_receipts"]
    if not isinstance(receipts, dict) or list(receipts) != list(SOURCE_TYPES):
        _fail(code, "source receipt keys and order are not exact")
    generated = _timestamp(state.manifest["generated_at"], field_name="generated_at", code=code)
    counts = Counter(row.get("source_type") for row in state.events)
    allowed_hosts = {
        "congress_house_ptr": {"disclosures-clerk.house.gov"},
        "congress_senate_ptr": {"efdsearch.senate.gov"},
        "sec_form_4": {"www.sec.gov", "data.sec.gov"},
        "sec_schedule_13d": {"www.sec.gov", "data.sec.gov"},
        "sec_schedule_13g": {"www.sec.gov", "data.sec.gov"},
        "sec_form_13f": {"www.sec.gov", "data.sec.gov"},
    }
    for source_type, receipt in receipts.items():
        receipt = _exact(receipt, SOURCE_RECEIPT_KEYS, label="source receipt", code=code)
        if (
            receipt["source_type"] != source_type
            or receipt["official_entry_url"] != OFFICIAL_ENTRY_URLS[source_type]
            or not isinstance(receipt["request_url"], str)
            or urlparse(receipt["request_url"]).scheme != "https"
            or urlparse(receipt["request_url"]).hostname not in allowed_hosts[source_type]
            or receipt["http_status"] != 200
            or not isinstance(receipt["content_type"], str)
            or not receipt["content_type"]
            or not _sha_ok(receipt["content_sha256"])
            or not _sha_ok(receipt["request_receipt_sha256"])
            or not _sha_ok(receipt["terms_snapshot_sha256"])
            or not isinstance(receipt["byte_count"], int)
            or isinstance(receipt["byte_count"], bool)
            or receipt["byte_count"] <= 0
            or receipt["record_count"] != counts[source_type]
            or receipt["legal_use_approved"] is not True
            or receipt["raw_payload_location"] != "private_quarantine_not_git_ci_site"
        ):
            _fail(code, "source receipt content is invalid")
        collected = _timestamp(receipt["collected_at"], field_name="collected_at", code=code)
        observed = _timestamp(
            receipt["first_observed_at"], field_name="first_observed_at", code=code
        )
        if not collected <= observed <= generated:
            _fail(code, "source receipt clocks are out of order")
        bound_versions = [row for row in state.versions if row["source_type"] == source_type]
        if any(
            row["request_receipt_sha256"] != receipt["request_receipt_sha256"]
            or _timestamp(
                row["first_observed_at"], field_name="version first_observed_at", code=code
            )
            != observed
            for row in bound_versions
        ):
            _fail(
                "first_observed_receipt_mismatch",
                "document first-observed clock is not bound to its request receipt",
            )


def _validate_versions(state: _State) -> None:
    code = "document_version_invalid"
    version_ids: set[str] = set()
    document_versions: set[tuple[str, str, str]] = set()
    accessions: set[str] = set()
    content_versions: set[tuple[str, str, str]] = set()
    for row in state.versions:
        _exact(row, SOURCE_VERSION_KEYS, label="source version", code=code)
        for key in ("source_type", "source_document_id", "source_version_id", "document_type"):
            _nonempty(row[key], field_name=key, code=code)
        source_type = row["source_type"]
        if source_type not in SOURCE_TYPES or row["document_type"] not in DOCUMENT_TYPES[source_type]:
            _fail(code, "source and document type are incompatible")
        if row["source_version_id"] in version_ids:
            _fail("document_version_duplicate", "source_version_id is duplicated")
        version_ids.add(row["source_version_id"])
        key = (source_type, row["source_document_id"], row["source_version_id"])
        if key in document_versions:
            _fail("document_version_duplicate", "source document/version is duplicated")
        document_versions.add(key)
        content_key = (source_type, row["source_version_id"], row["content_sha256"])
        if content_key in content_versions:
            _fail("document_version_duplicate", "source version/content is duplicated")
        content_versions.add(content_key)
        if not _sha_ok(row["content_sha256"]) or not _sha_ok(row["request_receipt_sha256"]):
            _fail(code, "source version receipt hash is invalid")
        if row["request_receipt_sha256"] != state.manifest["source_receipts"][source_type]["request_receipt_sha256"]:
            _fail(code, "source version does not bind its request receipt")
        if (
            not isinstance(row["record_count"], int)
            or isinstance(row["record_count"], bool)
            or row["record_count"] < 0
        ):
            _fail(code, "source version record_count is invalid")
        accession = row["accession_number"]
        if source_type.startswith("sec_"):
            if not isinstance(accession, str) or ACCESSION_PATTERN.fullmatch(accession) is None:
                _fail(code, "SEC accession is invalid")
            if accession in accessions:
                _fail("edgar_accession_duplicate", "EDGAR accession is duplicated")
            accessions.add(accession)
        elif accession is not None:
            _fail(code, "Congress source cannot claim an EDGAR accession")
        if row["supersedes_version_id"] is not None and not isinstance(
            row["supersedes_version_id"], str
        ):
            _fail(code, "supersedes_version_id must be string or null")


def _validate_timestamps(state: _State) -> None:
    code = "timestamp_contract_invalid"
    for row in state.versions:
        clocks = {
            key: _optional_timestamp(row[key], field_name=key, code=code)
            for key in ("filed_at", "accepted_at", "public_at")
        }
        clocks["independent_archived_first_seen_at"] = _optional_timestamp(
            row["independent_archived_first_seen_at"],
            field_name="independent_archived_first_seen_at",
            code=code,
        )
        clocks["first_observed_at"] = _timestamp(
            row["first_observed_at"], field_name="first_observed_at", code=code
        )
        clocks["known_at"] = _timestamp(row["known_at"], field_name="known_at", code=code)
        ordered = [clocks[key] for key in ("filed_at", "accepted_at", "public_at") if clocks[key] is not None]
        if any(left > right for left, right in zip(ordered, ordered[1:], strict=False)):
            _fail(code, "filed/accepted/public clocks are out of order")
        if clocks["public_at"] is not None and clocks["public_at"] > clocks["first_observed_at"]:
            _fail(code, "public_at is after first_observed_at")
        if (
            clocks["independent_archived_first_seen_at"] is not None
            and clocks["independent_archived_first_seen_at"] > clocks["first_observed_at"]
        ):
            _fail(code, "archived first-seen is after local first observation")
        state.version_times[row["source_version_id"]] = clocks
    version_by_id = {row["source_version_id"]: row for row in state.versions}
    for row in state.events:
        _exact(row, EVENT_KEYS, label="event", code="event_schema_mismatch")
        for key in (
            "source_type",
            "source_event_id",
            "source_document_id",
            "source_version_id",
            "security_id",
            "security_link_id",
            "actor_token",
            "actor_role",
            "economic_semantics",
            "transaction_code",
            "ownership_nature",
            "event_precision",
            "first_observed_at",
            "known_at",
            "known_at_basis",
            "decision_at",
            "trade_at",
        ):
            _nonempty(row[key], field_name=key, code=code)
        if row["event_precision"] not in {"timestamp", "date", "quarter_end", "unknown"}:
            _fail(code, "event_precision is unsupported")
        reported_date = row["reported_event_date"]
        period_end = row["reported_period_end"]
        if reported_date is not None and (
            not isinstance(reported_date, str) or DATE_PATTERN.fullmatch(reported_date) is None
        ):
            _fail(code, "reported_event_date must be an ISO date or null")
        if period_end is not None and (
            not isinstance(period_end, str) or DATE_PATTERN.fullmatch(period_end) is None
        ):
            _fail(code, "reported_period_end must be an ISO date or null")
        null_reasons = _exact(row["null_reasons"], NULL_REASON_KEYS, label="null reasons", code=code)
        clocks: dict[str, datetime | None] = {}
        for key in TIMESTAMP_FIELDS:
            clocks[key] = _optional_timestamp(row[key], field_name=key, code=code)
            reason = null_reasons.get(key) if key in NULL_REASON_KEYS else None
            if key in NULL_REASON_KEYS:
                if row[key] is None and (not isinstance(reason, str) or not reason.strip()):
                    _fail(code, f"{key} null requires a source reason")
                if row[key] is not None and reason is not None:
                    _fail(code, f"{key} non-null cannot have a null reason")
        if any(clocks[key] is None for key in ("first_observed_at", "known_at", "decision_at", "trade_at")):
            _fail(code, "observed/known/decision/trade timestamps cannot be null")
        precision_shape = {
            "timestamp": (clocks["event_at"] is not None and reported_date is None and period_end is None),
            "date": (clocks["event_at"] is None and reported_date is not None and period_end is None),
            "quarter_end": (clocks["event_at"] is None and reported_date is None and period_end is not None),
            "unknown": (clocks["event_at"] is None and reported_date is None and period_end is None),
        }
        if not precision_shape[row["event_precision"]]:
            _fail(
                "event_precision_timestamp_conflict",
                "event precision conflicts with timestamp/date/period fields",
            )
        available = [clocks[key] for key in ("event_at", "filed_at", "accepted_at", "public_at") if clocks[key] is not None]
        if any(left > right for left, right in zip(available, available[1:], strict=False)):
            _fail(code, "event/filed/accepted/public ordering is invalid")
        if row["source_version_id"] not in version_by_id:
            _fail(code, "event references an unknown source version")
        version = version_by_id[row["source_version_id"]]
        if (
            row["source_type"] != version["source_type"]
            or row["source_document_id"] != version["source_document_id"]
            or row["supersedes_version_id"] != version["supersedes_version_id"]
        ):
            _fail(code, "event source/version linkage differs from its document")
        for key in ("filed_at", "accepted_at", "public_at", "first_observed_at", "known_at", "known_at_basis"):
            if row[key] != version[key]:
                _fail(code, "event substituted a document availability field")
        state.event_times[row["source_event_id"]] = clocks
    if len(state.event_times) != len(state.events):
        _fail("event_duplicate", "source_event_id is duplicated")


def _validate_public_evidence(state: _State) -> None:
    code = "public_at_evidence_invalid"
    for row in state.versions:
        public_at = state.version_times[row["source_version_id"]]["public_at"]
        evidence_type = row["public_at_evidence_type"]
        evidence_hash = row["public_at_evidence_sha256"]
        archived_at = state.version_times[row["source_version_id"]][
            "independent_archived_first_seen_at"
        ]
        archived_hash = row["independent_archived_evidence_sha256"]
        if public_at is None:
            if evidence_type is not None or evidence_hash is not None:
                _fail(code, "null public_at cannot claim public evidence")
        elif (
            evidence_type not in {"official_timestamp", "independent_archive"}
            or not _sha_ok(evidence_hash)
        ):
            _fail(code, "public_at lacks hash-bound official or independent evidence")
        if archived_at is None:
            if archived_hash is not None:
                _fail(code, "null archived first-seen cannot claim an evidence hash")
        elif not _sha_ok(archived_hash):
            _fail(
                "archived_first_seen_evidence_missing",
                "archived first-seen lacks independent evidence SHA-256",
            )


def _validate_known_at(state: _State) -> None:
    code = "known_at_derivation_invalid"
    for row in state.versions:
        times = state.version_times[row["source_version_id"]]
        basis = row["known_at_basis"]
        if basis not in KNOWN_AT_BASES:
            _fail(code, "known_at_basis is unsupported")
        official_available = (
            times["public_at"] is not None
            and row["public_at_evidence_type"] == "official_timestamp"
            and _sha_ok(row["public_at_evidence_sha256"])
        )
        archive_available = (
            times["independent_archived_first_seen_at"] is not None
            and _sha_ok(row["independent_archived_evidence_sha256"])
        )
        expected_basis = (
            "official_public_timestamp"
            if official_available
            else "independent_archived_first_seen"
            if archive_available
            else "local_first_observed_fallback"
        )
        if basis != expected_basis:
            _fail("known_at_priority_violation", "known_at did not use the highest-priority evidence")
        if basis == "official_public_timestamp":
            expected = times["public_at"]
            if expected is None or row["public_at_evidence_type"] != "official_timestamp":
                _fail(code, "official-public basis lacks official evidence")
        elif basis == "independent_archived_first_seen":
            expected = times["independent_archived_first_seen_at"]
            if expected is None or not _sha_ok(row["independent_archived_evidence_sha256"]):
                _fail(
                    "archived_first_seen_evidence_missing",
                    "archived-first-seen basis lacks hash-bound evidence",
                )
        else:
            expected = times["first_observed_at"]
        if times["known_at"] != expected:
            _fail(code, "known_at does not equal its frozen basis clock")


def _validate_revision_chain(state: _State) -> None:
    code = "revision_chain_invalid"
    by_id = {row["source_version_id"]: row for row in state.versions}
    positions = {row["source_version_id"]: index for index, row in enumerate(state.versions)}
    previous = GENESIS_SHA256
    revisions = 0
    event_versions = Counter(row["source_version_id"] for row in state.events)
    for row in state.versions:
        if row["previous_chain_sha256"] != previous or not _sha_ok(row["chain_sha256"]):
            _fail(code, "append-only chain predecessor is invalid")
        payload = {key: value for key, value in row.items() if key != "chain_sha256"}
        if row["chain_sha256"] != _canonical_sha256(payload):
            _fail(code, "append-only chain hash is invalid")
        previous = row["chain_sha256"]
        predecessor_id = row["supersedes_version_id"]
        is_amendment = row["document_type"] in AMENDMENT_BASE
        if is_amendment:
            revisions += 1
            if predecessor_id not in by_id:
                _fail(code, "amendment predecessor is missing")
            predecessor = by_id[predecessor_id]
            if positions[predecessor_id] >= positions[row["source_version_id"]]:
                _fail(
                    "revision_predecessor_order_invalid",
                    "amendment predecessor appears later in the append-only chain",
                )
            if (
                predecessor["source_type"] != row["source_type"]
                or predecessor["source_document_id"] != row["source_document_id"]
                or AMENDMENT_BASE.get(
                    predecessor["document_type"], predecessor["document_type"]
                )
                != AMENDMENT_BASE[row["document_type"]]
                or predecessor["content_sha256"] == row["content_sha256"]
                or state.version_times[predecessor_id]["known_at"]
                >= state.version_times[row["source_version_id"]]["known_at"]
            ):
                _fail(code, "amendment chain overwrites or backfills its predecessor")
        elif predecessor_id is not None:
            _fail(code, "base document cannot supersede another version")
        if event_versions[row["source_version_id"]] != row["record_count"]:
            _fail(code, "document record_count does not equal normalized events")
    for version_id in by_id:
        seen: set[str] = set()
        cursor: str | None = version_id
        while cursor is not None:
            if cursor in seen:
                _fail(code, "revision chain contains a cycle")
            seen.add(cursor)
            cursor = by_id[cursor]["supersedes_version_id"]
    contract = state.manifest["revision_contract"]
    if contract["chain_head_sha256"] != previous or contract["revision_count"] != revisions:
        _fail(code, "manifest chain head or revision count is stale")


def _validate_identifiers(state: _State) -> None:
    code = "security_mapping_invalid"
    ids: set[str] = set()
    records: set[tuple[str, str]] = set()
    grouped: dict[tuple[str, str], list[str]] = {}
    for row in state.identifiers:
        for key in (
            "security_link_id",
            "source_type",
            "source_security_id",
            "security_id",
            "company_id",
            "ticker",
            "exchange",
            "share_class",
            "cusip",
            "cik",
            "effective_from",
            "known_at",
            "source_record_id",
        ):
            _nonempty(row[key], field_name=key, code=code)
        if row["source_type"] not in SOURCE_TYPES or row["exchange"] not in {"XNYS", "XNAS"}:
            _fail(code, "identifier source is unsupported")
        if row["security_link_id"] in ids:
            _fail("security_mapping_duplicate", "security_link_id is duplicated")
        ids.add(row["security_link_id"])
        record = (row["source_type"], row["source_record_id"])
        if record in records:
            _fail("security_mapping_duplicate", "security source record is duplicated")
        records.add(record)
        if CUSIP_PATTERN.fullmatch(row["cusip"]) is None or CIK_PATTERN.fullmatch(row["cik"]) is None:
            _fail(code, "CUSIP or CIK is invalid")
        start = _timestamp(row["effective_from"], field_name="effective_from", code=code)
        end = _optional_timestamp(row["effective_to"] or None, field_name="effective_to", code=code)
        known = _timestamp(row["known_at"], field_name="known_at", code=code)
        if end is not None and start >= end:
            _fail(code, "identifier interval is empty")
        state.identifier_times[row["security_link_id"]] = {
            "start": start,
            "end": end,
            "known": known,
        }
        grouped.setdefault((row["source_type"], row["source_security_id"]), []).append(
            row["security_link_id"]
        )
    ambiguity_groups: dict[tuple[str, ...], list[str]] = dict(grouped)
    security_by_link = {
        row["security_link_id"]: row["security_id"] for row in state.identifiers
    }
    for row in state.identifiers:
        for key in (
            ("cusip", row["source_type"], row["cusip"]),
            ("ticker", row["ticker"], row["exchange"]),
        ):
            ambiguity_groups.setdefault(key, []).append(row["security_link_id"])
    for group_key, link_ids in ambiguity_groups.items():
        if len({security_by_link[link_id] for link_id in link_ids}) <= 1:
            continue
        ordered = sorted(link_ids, key=lambda item: state.identifier_times[item]["start"])
        for earlier, later in zip(ordered, ordered[1:], strict=False):
            end = state.identifier_times[earlier]["end"]
            if end is None or state.identifier_times[later]["start"] < end:
                failure = (
                    "ticker_exchange_ambiguity"
                    if group_key[0] == "ticker"
                    else "security_identifier_ambiguity"
                )
                _fail(failure, "identifier maps to overlapping permanent securities")
    identifier_by_id = {row["security_link_id"]: row for row in state.identifiers}
    for event in state.events:
        link_id = event["security_link_id"]
        if link_id not in identifier_by_id:
            _fail(code, "event references an unknown permanent security link")
        link = identifier_by_id[link_id]
        if link["source_type"] != event["source_type"] or link["security_id"] != event["security_id"]:
            _fail(code, "event and security mapping disagree")
        event_at = state.event_times[event["source_event_id"]]["event_at"]
        times = state.identifier_times[link_id]
        if event_at is not None and (
            event_at < times["start"] or (times["end"] is not None and event_at >= times["end"])
        ):
            _fail(code, "event falls outside security mapping interval")
        if times["known"] > state.event_times[event["source_event_id"]]["known_at"]:
            _fail("security_mapping_backfill", "permanent mapping was not known by event known_at")


def _number(value: Any, *, field_name: str, code: str) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        _fail(code, f"{field_name} must be numeric or null")
    parsed = float(value)
    if parsed != parsed or parsed in {float("inf"), float("-inf")}:
        _fail(code, f"{field_name} must be finite")
    return parsed


def _validate_semantics_and_actors(state: _State) -> None:
    code = "source_semantics_invalid"
    actor_records: set[str] = set()
    for row in state.events:
        source = row["source_type"]
        if source not in SOURCE_TYPES or OPAQUE_ACTOR_PATTERN.fullmatch(row["actor_token"]) is None:
            _fail(code, "source or opaque actor token is invalid")
        if row["actor_role"] not in ACTOR_ROLES[source]:
            _fail(code, "actor role is incompatible with source semantics")
        actor = _exact(
            row["actor_eligibility"],
            ACTOR_ELIGIBILITY_KEYS,
            label="actor eligibility",
            code=code,
        )
        if actor["actor_type"] != ACTOR_TYPE_BY_SOURCE[source]:
            _fail(code, "actor eligibility type is incompatible with source")
        start = _timestamp(actor["eligible_from"], field_name="eligible_from", code=code)
        end = _optional_timestamp(actor["eligible_to"], field_name="eligible_to", code=code)
        known = _timestamp(actor["known_at"], field_name="actor known_at", code=code)
        source_record = _nonempty(
            actor["source_record_id"], field_name="actor source_record_id", code=code
        )
        if source_record in actor_records:
            _fail("actor_eligibility_duplicate", "actor eligibility source record is duplicated")
        actor_records.add(source_record)
        event_at = state.event_times[row["source_event_id"]]["event_at"]
        if end is not None and start >= end:
            _fail(code, "actor eligibility interval is empty")
        if event_at is not None and (event_at < start or (end is not None and event_at >= end)):
            _fail(code, "event falls outside actor eligibility interval")
        if known > state.event_times[row["source_event_id"]]["known_at"]:
            _fail("actor_eligibility_backfill", "actor eligibility was not known by event known_at")
        low = _number(row["value_min_usd"], field_name="value_min_usd", code=code)
        high = _number(row["value_max_usd"], field_name="value_max_usd", code=code)
        open_ended_ptr = (
            source in {"congress_house_ptr", "congress_senate_ptr"}
            and low == 50_000_001.0
            and high is None
        )
        if (
            ((low is None) != (high is None) and not open_ended_ptr)
            or (low is not None and low <= 0)
            or (high is not None and low is not None and low > high)
        ):
            _fail(code, "reported value range is invalid")
        if source in {"congress_house_ptr", "congress_senate_ptr"}:
            expected = PTR_SEMANTICS.get(row["transaction_code"])
            if expected is None:
                _fail("unsupported_transaction_code", "unsupported PTR transaction code")
            if (
                row["economic_semantics"] != expected
                or low is None
                or (low, high) not in PTR_AMOUNT_BANDS
                or row["ownership_nature"] not in {
                "self",
                "joint",
                "spouse",
                "dependent",
                "unknown",
                }
                or row["acquired_disposed_code"] is not None
                or row["filing_category"] != "periodic_transaction_report"
            ):
                _fail("ptr_amount_band_invalid", "PTR range, owner, or semantics are invalid")
        elif source == "sec_form_4":
            expected = FORM4_SEMANTICS.get(row["transaction_code"])
            if expected is None:
                _fail("unsupported_transaction_code", "unsupported Form 4 transaction code")
            if row["economic_semantics"] != expected or row["ownership_nature"] not in {
                "direct",
                "indirect",
            } or row["filing_category"] != "section_16_transaction":
                _fail(code, "Form 4 code or ownership semantics are invalid")
            expected_indicator = "A" if row["transaction_code"] == "P" else "D" if row["transaction_code"] == "S" else None
            if expected_indicator is not None and row["acquired_disposed_code"] != expected_indicator:
                _fail(
                    "form4_acquired_disposed_missing",
                    "Form 4 P/S code lacks its required acquired/disposed indicator",
                )
            if expected_indicator is None and row["acquired_disposed_code"] not in {"A", "D"}:
                _fail(
                    "form4_acquired_disposed_missing",
                    "Form 4 non-P/S code must preserve its reported A/D indicator",
                )
            if row["transaction_code"] in {"P", "S"} and low is None:
                _fail(code, "open-market Form 4 row lacks reported value")
        else:
            expected_code, expected_semantics = SOURCE_SEMANTICS[source]
            if (
                row["transaction_code"] != expected_code
                or row["economic_semantics"] != expected_semantics
            ):
                _fail("unsupported_transaction_code", "snapshot source was mislabeled as a trade")
            if source in {"sec_schedule_13d", "sec_schedule_13g"} and low is not None:
                _fail(code, "13D/G ownership snapshot cannot be assigned transaction value")
            if source == "sec_schedule_13d" and (
                row["filing_category"] != "control_intent"
                or row["ownership_nature"] != "control_intent"
            ):
                _fail(
                    "schedule_13_filer_category_missing",
                    "Schedule 13D control-intent category is missing",
                )
            if source == "sec_schedule_13g" and (
                row["filing_category"]
                not in {"qualified_institutional", "passive_investor", "exempt_investor"}
                or row["ownership_nature"] != row["filing_category"]
            ):
                _fail(
                    "schedule_13_filer_category_missing",
                    "Schedule 13G filer category is missing",
                )
            if source == "sec_form_13f" and row["event_precision"] != "quarter_end":
                _fail(code, "13F must remain a quarter-end holdings snapshot")
            if source == "sec_form_13f" and (
                row["filing_category"] != "quarter_end_holdings"
                or row["ownership_nature"] != "institutional_manager"
                or low is None
                or not isinstance(row["reported_period_end"], str)
                or row["reported_period_end"][5:] not in {"03-31", "06-30", "09-30", "12-31"}
            ):
                _fail(
                    "form13f_holding_semantics_incomplete",
                    "13F holding amount or quarter-end category is incomplete",
                )


def _validate_calendar(state: _State) -> None:
    code = "xnys_decision_trade_clock_invalid"
    parsed: list[tuple[str, datetime, datetime]] = []
    for row in state.calendar:
        if DATE_PATTERN.fullmatch(row["session"]) is None:
            _fail(code, "calendar session is not an ISO date")
        open_at = _timestamp(row["open_at"], field_name="open_at", code=code)
        close_at = _timestamp(row["close_at"], field_name="close_at", code=code)
        if open_at >= close_at:
            _fail(code, "calendar open is not before close")
        parsed.append((row["session"], open_at, close_at))
    if len({row[0] for row in parsed}) != len(parsed) or parsed != sorted(parsed):
        _fail(code, "calendar has duplicate or unordered sessions")
    calendar = xcals.get_calendar("XNYS")
    expected = calendar.sessions_in_range(parsed[0][0], parsed[-1][0])
    if [row[0] for row in parsed] != [str(session.date()) for session in expected]:
        _fail(code, "calendar omits or adds an official XNYS session")
    schedule = calendar.schedule.loc[parsed[0][0] : parsed[-1][0]]
    for actual, (_, official) in zip(parsed, schedule.iterrows(), strict=True):
        if (
            actual[1] != official["open"].to_pydatetime().astimezone(UTC)
            or actual[2] != official["close"].to_pydatetime().astimezone(UTC)
        ):
            _fail(code, "calendar open/close differs from official XNYS")
    state.calendar_times = parsed
    for event in state.events:
        clocks = state.event_times[event["source_event_id"]]
        decision_index = next(
            (index for index, row in enumerate(parsed) if row[2] > clocks["known_at"]), None
        )
        if decision_index is None or decision_index + 1 >= len(parsed):
            _fail(code, "calendar does not extend through decision and next trade session")
        if (
            clocks["decision_at"] != parsed[decision_index][2]
            or clocks["trade_at"] != parsed[decision_index + 1][1]
        ):
            _fail(code, "event does not use next close then following XNYS open")


def _validate_summary_coverage(state: _State) -> None:
    code = "coverage_lag_missingness_invalid"
    summary = _exact(state.summary, SUMMARY_KEYS, label="sanitized summary", code=code)
    if (
        summary["schema_version"] != 1
        or summary["bundle_id"] != state.manifest["bundle_id"]
        or _timestamp(summary["generated_at"], field_name="summary generated_at", code=code)
        != _timestamp(state.manifest["generated_at"], field_name="generated_at", code=code)
    ):
        _fail(code, "sanitized summary identity differs from manifest")
    audits = summary["source_audits"]
    if not isinstance(audits, list) or [row.get("source_type") for row in audits] != list(SOURCE_TYPES):
        _fail(code, "source audits do not cover the exact six source types")
    version_counts = Counter(row["source_type"] for row in state.versions)
    event_counts = Counter(row["source_type"] for row in state.events)
    actor_counts = {
        source: len({row["actor_token"] for row in state.events if row["source_type"] == source})
        for source in SOURCE_TYPES
    }
    amendment_counts = Counter(
        row["source_type"] for row in state.versions if row["supersedes_version_id"] is not None
    )
    observed_windows: dict[str, tuple[str, str]] = {}
    for source in SOURCE_TYPES:
        source_events = [row for row in state.events if row["source_type"] == source]
        dates = [
            row["reported_event_date"]
            or row["reported_period_end"]
            or row["event_at"][:10]
            for row in source_events
            if row["reported_event_date"] or row["reported_period_end"] or row["event_at"]
        ]
        known_dates = [row["known_at"][:10] for row in source_events]
        if not dates or not known_dates:
            _fail("source_family_empty", "source family has no replayable observed window")
        observed_windows[source] = (min(dates), max(known_dates))
    for row in audits:
        _exact(row, SOURCE_AUDIT_KEYS, label="source audit", code=code)
        source = row["source_type"]
        suppressed = actor_counts[source] < 10
        sensitive_aggregate_keys = SOURCE_AUDIT_KEYS - {
            "source_type",
            "public_statistics_suppressed",
        }
        if suppressed:
            if row["public_statistics_suppressed"] is not True or any(
                row[key] is not None for key in sensitive_aggregate_keys
            ):
                _fail(
                    "suppressed_cell_disclosed",
                    "small-cell source audit discloses exact dates or counts",
                )
            continue
        for date_key in ("observed_start", "observed_end"):
            if not isinstance(row[date_key], str) or DATE_PATTERN.fullmatch(row[date_key]) is None:
                _fail(code, "source audit dates are invalid")
        integer_keys = SOURCE_AUDIT_KEYS - {
            "source_type",
            "observed_start",
            "observed_end",
            "public_statistics_suppressed",
        }
        if any(
            not isinstance(row[key], int) or isinstance(row[key], bool) or row[key] < 0
            for key in integer_keys
        ):
            _fail(code, "source audit counts are invalid")
        resolved_lag = sum(
            event["event_at"] is not None and event["event_precision"] == "timestamp"
            for event in state.events
            if event["source_type"] == source
        )
        if (
            row["observed_documents"] != version_counts[source]
            or row["event_lag_count"] != resolved_lag
            or row["lag_unresolved_count"] != event_counts[source] - resolved_lag
            or row["distinct_actor_count"] != actor_counts[source]
            or (row["observed_start"], row["observed_end"]) != observed_windows[source]
            or row["amendments"] != amendment_counts[source]
            or row["expected_documents"]
            != row["observed_documents"] + row["missing_documents"]
            or row["public_statistics_suppressed"] is not (actor_counts[source] < 10)
        ):
            _fail(code, "source coverage window, denominator, lag, or revisions do not reconcile")


def _validate_summary_privacy(state: _State) -> None:
    code = "public_sanitizer_invalid"
    privacy = _exact(
        state.summary["privacy_audit"], PRIVACY_AUDIT_KEYS, label="privacy audit", code=code
    )
    if (
        privacy["forbidden_key_scan_passed"] is not True
        or privacy["site_bundle_scan_passed"] is not True
        or privacy["source_map_scan_passed"] is not True
        or privacy["minimum_actor_threshold"] != 10
        or privacy["raw_rows_in_summary"] != 0
        or privacy["selected_tickers"] != []
        or privacy["actor_names"] != []
        or not _sha_ok(privacy["manual_reviewer_receipt_sha256"])
    ):
        _fail(code, "sanitizer or public suppression evidence is incomplete")
    _timestamp(privacy["manual_reviewed_at"], field_name="manual_reviewed_at", code=code)


def _validate_summary_attacks(state: _State) -> None:
    code = "independent_attacks_invalid"
    attacks = _exact(
        state.summary["independent_attacks"], ATTACK_AUDIT_KEYS, label="attack audit", code=code
    )
    required_codes = {
        "timestamp_contract_invalid",
        "event_schema_mismatch",
        "revision_chain_invalid",
        "security_mapping_backfill",
        "event_duplicate",
        "unsupported_transaction_code",
        "xnys_decision_trade_clock_invalid",
        "edgar_accession_duplicate",
    }
    if (
        not isinstance(attacks["rejected"], int)
        or isinstance(attacks["rejected"], bool)
        or attacks["rejected"] != attacks["total"]
        or attacks["total"] < len(required_codes)
        or attacks["all_rejected"] is not True
        or not isinstance(attacks["exact_error_codes"], list)
        or not required_codes <= set(attacks["exact_error_codes"])
        or not _sha_ok(attacks["independent_reviewer_receipt_sha256"])
    ):
        _fail(code, "independent mutation evidence is incomplete")


def _validate_real_sample(state: _State) -> None:
    code = "authorized_real_sample_invalid"
    sample = _exact(
        state.summary["authorized_real_sample"], SAMPLE_AUDIT_KEYS, label="sample audit", code=code
    )
    if (
        sample["accepted"] is not True
        or sample["synthetic"] is not False
        or sample["row_count"] != len(state.events)
        or not _sha_ok(sample["reviewer_receipt_sha256"])
    ):
        _fail(code, "real sample is not independently accepted")
    _timestamp(sample["reviewed_at"], field_name="sample reviewed_at", code=code)


VALIDATION_STEPS: tuple[tuple[str, Callable[[_State], None]], ...] = (
    ("03_congress_exact_use_legal_clearance", _validate_legal_gate),
    ("04_source_terms_and_automation_clearance", _validate_terms_gate),
    ("05_sec_fair_access_client_verified", _validate_sec_gate),
    ("06_private_quarantine_verified", _validate_private_gate),
    ("07_closed_manifest_admitted", _validate_manifest_contract),
    ("08_source_request_receipts_complete", _validate_exact_files),
    ("08_source_request_receipts_complete", _validate_source_receipts),
    ("09_stable_document_version_ids", _validate_versions),
    ("10_eight_timestamps_complete_or_reasoned", _validate_timestamps),
    ("11_public_at_evidence_verified", _validate_public_evidence),
    ("12_known_at_derivation_verified", _validate_known_at),
    ("13_append_only_revision_chain_verified", _validate_revision_chain),
    ("14_point_in_time_security_mapping_verified", _validate_identifiers),
    ("15_source_specific_semantics_verified", _validate_semantics_and_actors),
    ("16_xnys_decision_entry_clock_verified", _validate_calendar),
    ("17_coverage_lag_missingness_audited", _validate_summary_coverage),
    ("18_public_sanitizer_verified", _validate_summary_privacy),
    ("19_independent_synthetic_attacks_passed", _validate_summary_attacks),
    ("20_authorized_real_sample_accepted", _validate_real_sample),
)


def _gate(passed: bool, detail: str, failure_code: str | None = None) -> dict[str, Any]:
    return {"passed": passed, "detail": detail, "failure_code": failure_code}


def _frozen_gates(root: Path) -> dict[str, dict[str, Any]]:
    gates = {
        key: _gate(False, "尚未由合法真實外部數據包驗證", "not_evaluated")
        for key in GATE_KEYS
    }
    try:
        _protocol_integrity(root)
        gates[GATE_KEYS[0]] = _gate(True, "協議、schema、收據及前置雜湊一致")
        _official_semantics_pinned(root)
        gates[GATE_KEYS[1]] = _gate(True, "六類官方來源及不可推論語意已事前固定")
    except DisclosureKnownAtError as exc:
        gate = GATE_KEYS[0] if exc.code.startswith("protocol_") else GATE_KEYS[1]
        gates[gate] = _gate(False, "凍結契約完整性失敗", exc.code)
    return gates


def _result(
    gates: dict[str, dict[str, Any]],
    *,
    configured: bool,
    state: _State | None,
    failure_code: str | None,
) -> dict[str, Any]:
    passed = sum(int(row["passed"]) for row in gates.values())
    all_passed = passed == len(gates)
    versions = [] if state is None else state.versions
    events = [] if state is None else state.events
    manifest = {} if state is None else state.manifest
    source_counts = Counter(row.get("source_type") for row in versions if row.get("source_type"))
    event_counts = Counter(row.get("source_type") for row in events if row.get("source_type"))
    public_aggregates_allowed = gates["18_public_sanitizer_verified"]["passed"]
    legal = manifest.get("legal_use", {})
    return {
        "schema_version": SCHEMA_VERSION,
        "research_round": RESEARCH_ROUND,
        "phase": "phase1_disclosure_known_at_readiness",
        "status": "blocked_by_disclosure_known_at_readiness",
        "bundle": {
            "configured": configured,
            "repository_external_required": True,
            "absolute_path_published": False,
            "raw_rows_published": 0,
            "failure_code": failure_code,
        },
        "sources": {
            "official_only": gates[GATE_KEYS[1]]["passed"],
            "present": sorted(source_counts),
            "document_type_counts": (
                dict(sorted(source_counts.items())) if public_aggregates_allowed else {}
            ),
            "event_type_counts": (
                dict(sorted(event_counts.items())) if public_aggregates_allowed else {}
            ),
            "actor_names_published": 0,
        },
        "known_at": {
            "basis_order": list(KNOWN_AT_BASES),
            "documents_validated": len(versions) if gates[GATE_KEYS[12]]["passed"] else 0,
            "events_validated": len(events) if gates[GATE_KEYS[14]]["passed"] else 0,
            "historical_backfill_allowed": False,
            "final_revision_substitution_allowed": False,
        },
        "lag": {
            "definition": "known_at_minus_event_at_when_both_have_reliable_precision",
            "events_with_valid_lag": sum(
                1
                for row in events
                if row.get("event_at") is not None and row.get("event_precision") == "timestamp"
            )
            if gates[GATE_KEYS[16]]["passed"]
            else 0,
            "decision_at_rule": "first_official_xnys_close_strictly_after_known_at",
            "trade_at_rule": "next_official_xnys_open_after_decision_at",
            "events_with_valid_next_session": len(events) if gates[GATE_KEYS[15]]["passed"] else 0,
            "same_or_prior_session_execution_allowed": False,
        },
        "legal": {
            "authorized_for_local_research": bool(
                gates[GATE_KEYS[2]]["passed"] and legal.get("congress_use_review_status") == "approved_for_exact_use"
            ),
            "raw_redistribution_allowed": None,
            "official_public_sources_only": gates[GATE_KEYS[1]]["passed"],
        },
        "readiness": {"passed": passed, "total": 20, "all_passed": all_passed},
        "gates": gates,
        "controls": {
            "synthetic_raw_rows_generated": 0,
            "raw_rows_published": 0,
            "selected_tickers_published": 0,
            "actor_names_published": 0,
        },
        "attacks": {
            "runtime_mutations_executed": 0,
            "adversarial_mutations_are_test_suite_only": True,
            "independent_contract_passed": gates[GATE_KEYS[18]]["passed"],
        },
        "selection": {"dynamic_selection_enabled": False, "selected_tickers": []},
        "decision": {
            "can_promote": False,
            "dynamic_selection_enabled": False,
            "strategy_defined": False,
            "formal_backtest_authorized": False,
            "strategy_runs": 0,
            "today_action": "today_no_trade",
        },
        "paper": {
            "authorized": False,
            "status": "all_cash_not_started",
            "positions": 0,
            "backfilled_trades": 0,
        },
        "real_money_usd": 0,
        "next_action": (
            "20/20 只准另行凍結策略研究協議；本輪仍不選股、不回測、不建立訂單"
            if all_passed
            else "先取得精確用途書面准許及合法 repository-external 真實小樣本，再原樣重跑二十道門檻"
        ),
        "disclaimer": "資料入口通過不等於策略有效，不構成投資或法律建議，亦不保證盈利。",
    }


def audit_disclosure_known_at_bundle(
    bundle: str | Path | None,
    *,
    root: str | Path,
) -> dict[str, Any]:
    """Audit an external bundle and return only a sanitized fail-closed receipt."""

    root_path = Path(root).resolve()
    gates = _frozen_gates(root_path)
    if bundle is None:
        return _result(
            gates,
            configured=False,
            state=None,
            failure_code="bundle_not_configured",
        )
    try:
        bundle_path = _external_bundle(bundle, root=root_path)
    except DisclosureKnownAtError as exc:
        return _result(gates, configured=True, state=None, failure_code=exc.code)
    state = _State(root=root_path, bundle=bundle_path)
    try:
        _load_manifest(state)
    except DisclosureKnownAtError as exc:
        gates["07_closed_manifest_admitted"] = _gate(
            False, "封閉 manifest 無法讀取", exc.code
        )
        return _result(gates, configured=True, state=state, failure_code=exc.code)
    first_blocker: str | None = None
    for gate_key, validator in VALIDATION_STEPS:
        try:
            validator(state)
        except DisclosureKnownAtError as exc:
            gates[gate_key] = _gate(False, "此層失敗關閉；公開收據不披露原始列", exc.code)
            return _result(gates, configured=True, state=state, failure_code=exc.code)
        independent_code = INDEPENDENT_EVIDENCE_REQUIRED.get(gate_key)
        if independent_code is None:
            gates[gate_key] = _gate(True, "外部包的可重播內部合約驗證通過")
        else:
            gates[gate_key] = _gate(
                False,
                "包內自我聲明只通過格式檢查，不能冒充獨立外部證據",
                independent_code,
            )
            first_blocker = first_blocker or independent_code
    return _result(gates, configured=True, state=state, failure_code=first_blocker)


def validate_disclosure_known_at_bundle(
    bundle: str | Path,
    *,
    root: str | Path,
) -> dict[str, Any]:
    """Validate a bundle and raise the stable semantic failure code."""

    result = audit_disclosure_known_at_bundle(bundle, root=root)
    if not result["readiness"]["all_passed"]:
        code = result["bundle"]["failure_code"] or "disclosure_known_at_contract_failed"
        _fail(code, "disclosure known-at bundle did not pass all twenty gates")
    return result


audit_disclosure_bundle = audit_disclosure_known_at_bundle
