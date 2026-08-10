from __future__ import annotations

import csv
import hashlib
import io
import json
import math
import re
import zipfile
from collections import Counter
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import unquote, urlparse
from xml.etree import ElementTree

from .sec_edgar_client import SecEdgarClient, SecEdgarClientError

SCHEMA_VERSION = "us_fddk.short_term_form4_admission_feasibility.v1_1"
PROTOCOL_PATH = Path("docs/SHORT_TERM_FORM4_ADMISSION_FEASIBILITY_PROTOCOL.md")
PROTOCOL_RECEIPT_PATH = Path(
    "artifacts/short_term_form4_admission_feasibility_protocol_receipt.json"
)
EXPECTED_PROTOCOL_SHA256 = "ddce1e7152a3d23f39dae4f8d7bb812166941952d7611523ca5796f11b4b1186"
EXPECTED_PROTOCOL_RECEIPT_SHA256 = (
    "75f81c0149abc003fa0438e9498f0884a0e7020b31c07bbeaef122cc15f912db"
)
SCHEMA_AMENDMENT_PATH = Path(
    "docs/SHORT_TERM_FORM4_ADMISSION_FEASIBILITY_SCHEMA_AMENDMENT_V1_1.md"
)
SCHEMA_AMENDMENT_RECEIPT_PATH = Path(
    "artifacts/short_term_form4_admission_feasibility_schema_amendment_v1_1_receipt.json"
)
EXPECTED_SCHEMA_AMENDMENT_SHA256 = (
    "2d5f2e27a28151a032ebd440271d2bb325d210df8628de1baea00677ab926b2c"
)
EXPECTED_SCHEMA_AMENDMENT_RECEIPT_SHA256 = (
    "c8811f20a4a5369a442f297bb34870baf62bf76aa74538ef9ea68f4d98f83558"
)
SCHEMA_AMENDMENT_FROZEN_AT = "2026-08-09T23:39:35Z"
FIXED_QUARTERS = ("2006Q1", "2016Q3", "2026Q2")
ALLOWED_DOCUMENT_TYPES = frozenset({"4", "4/A"})
REQUIRED_TABLES: dict[str, tuple[str, ...]] = {
    "SUBMISSION.tsv": (
        "ACCESSION_NUMBER",
        "FILING_DATE",
        "DATE_OF_ORIG_SUB",
        "DOCUMENT_TYPE",
        "ISSUERCIK",
    ),
    "REPORTINGOWNER.tsv": (
        "ACCESSION_NUMBER",
        "RPTOWNERCIK",
        "RPTOWNERNAME",
    ),
    "NONDERIV_TRANS.tsv": (
        "ACCESSION_NUMBER",
        "NONDERIV_TRANS_SK",
        "TRANS_FORM_TYPE",
        "TRANS_CODE",
        "TRANS_ACQUIRED_DISP_CD",
    ),
    "NONDERIV_HOLDING.tsv": ("ACCESSION_NUMBER", "NONDERIV_HOLDING_SK"),
    "DERIV_TRANS.tsv": (
        "ACCESSION_NUMBER",
        "DERIV_TRANS_SK",
        "TRANS_FORM_TYPE",
        "TRANS_CODE",
        "TRANS_ACQUIRED_DISP_CD",
    ),
    "DERIV_HOLDING.tsv": ("ACCESSION_NUMBER", "DERIV_HOLDING_SK"),
    "FOOTNOTES.tsv": ("ACCESSION_NUMBER", "FOOTNOTE_ID", "FOOTNOTE_TXT"),
    "OWNER_SIGNATURE.tsv": (
        "ACCESSION_NUMBER",
        "OWNERSIGNATURENAME",
        "OWNERSIGNATUREDATE",
    ),
}

FIXED_ATTACK_CODES = (
    "form4_feasibility_quarter_set_mismatch",
    "form4_feasibility_zip_member_mismatch",
    "form4_feasibility_header_mismatch",
    "form4_feasibility_form_type_invalid",
    "form4_feasibility_accession_invalid",
    "form4_feasibility_accession_duplicate",
    "form4_feasibility_filing_date_invalid",
    "form4_feasibility_sample_too_small",
    "form4_feasibility_amendment_sample_missing",
    "form4_feasibility_sample_not_deterministic",
    "form4_feasibility_daily_index_missing_or_ambiguous",
    "form4_feasibility_complete_submission_mismatch",
    "form4_feasibility_content_hash_mismatch",
    "form4_feasibility_historical_time_invented",
    "form4_feasibility_amendment_target_unresolved",
    "form4_feasibility_private_boundary_breached",
    "form4_feasibility_result_boundary_breached",
    "form4_feasibility_parent_hash_mismatch",
    "form4_feasibility_global_trial_drift",
)

SCHEMA_ATTACK_CODES = (
    "form4_feasibility_contact_omission_mismatch",
    "form4_feasibility_swap_footnote_alias_mismatch",
    "form4_feasibility_physical_header_profile_mismatch",
    "form4_feasibility_unexpected_metadata_physical_drift",
)
ALL_ATTACK_CODES = FIXED_ATTACK_CODES + SCHEMA_ATTACK_CODES

SAFE_STATE_CLAIMS: dict[str, Any] = {
    "authorized_real_form4_rows": 0,
    "candidate_selection_count": 0,
    "strategy_run_count": 0,
    "performance_present": False,
    "historical_public_time_claimed": False,
    "clock_mapping_executed": False,
    "private_identifier_output_requested": False,
    "form4_specific_admission_passed": 0,
    "form4_specific_admission_total": 16,
    "paper_authorized": False,
    "paper_state": "all_cash",
    "backfilled_trades": 0,
    "positions": [],
    "real_money_action_usd": 0,
}

FORM4_ADMISSION_GATES = (
    ("01", "versioned_parent_lineage_verified"),
    ("02", "sec_exact_use_terms_verified"),
    ("03", "encrypted_private_quarantine_verified"),
    ("04", "source_scope_exact"),
    ("05", "filing_denominator_complete"),
    ("06", "as_filed_content_complete"),
    ("07", "fixed_period_coverage_verified"),
    ("08", "known_at_evidence_complete"),
    ("09", "known_at_clock_verified"),
    ("10", "version_amendment_chain_verified"),
    ("11", "form4_semantics_verified"),
    ("12", "economic_event_dedupe_verified"),
    ("13", "pit_security_universe_verified"),
    ("14", "pit_market_execution_verified"),
    ("15", "independent_mutation_attacks_passed"),
    ("16", "authorized_real_sample_independently_replayed"),
)

_ACCESSION = re.compile(r"^\d{10}-\d{2}-\d{6}$")
_CIK = re.compile(r"^\d{1,10}$")
_FILING_DATE = re.compile(
    r"^(?P<day>\d{2})-(?P<month>JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)-(?P<year>\d{4})$"
)
_DAILY_INDEX_URL = re.compile(
    r"^/Archives/edgar/daily-index/(?P<year>20\d{2})/QTR(?P<quarter>[1-4])/form\.(?P<date>20\d{6})\.idx$"
)
_COMPLETE_URL = re.compile(
    r"^/Archives/edgar/data/(?P<cik>\d{1,10})/(?P<directory>\d{18})/(?P<accession>\d{10}-\d{2}-\d{6})\.txt$"
)
_INDEX_ROW_SUFFIX = re.compile(
    r"(?P<cik>\d{1,10})\s+(?P<date>20\d{6})\s+"
    r"(?P<path>edgar/data/(?P<path_cik>\d{1,10})/"
    r"(?P<accession>\d{10}-\d{2}-\d{6})\.txt)\s*$"
)


class Form4AdmissionFeasibilityError(RuntimeError):
    """Fail-closed Round 42 feasibility error with a frozen semantic code."""

    def __init__(self, code: str, detail: str):
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}")


def _fail(code: str, detail: str) -> None:
    raise Form4AdmissionFeasibilityError(code, detail)


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical_sha256(value: object) -> str:
    rendered = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return _sha256_bytes(rendered)


def _load_json(path: Path, *, code: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        _fail(code, type(exc).__name__)
    if not isinstance(payload, dict):
        _fail(code, "expected a JSON object")
    return payload


def _bound_file(root: Path, binding: Mapping[str, Any], *, code: str) -> Path:
    path_value = binding.get("path")
    digest = binding.get("sha256")
    if not isinstance(path_value, str) or not isinstance(digest, str):
        _fail(code, "binding is incomplete")
    path = root / path_value
    if not path.is_file() or _sha256_file(path) != digest:
        _fail(code, f"bound file drifted: {path_value}")
    return path


def _load_protocol_binding(repository_root: Path) -> dict[str, Any]:
    root = repository_root.resolve()
    protocol = root / PROTOCOL_PATH
    receipt_path = root / PROTOCOL_RECEIPT_PATH
    if (
        not protocol.is_file()
        or _sha256_file(protocol) != EXPECTED_PROTOCOL_SHA256
        or not receipt_path.is_file()
        or _sha256_file(receipt_path) != EXPECTED_PROTOCOL_RECEIPT_SHA256
    ):
        _fail("form4_feasibility_parent_hash_mismatch", "Round 42 freeze bytes drifted")
    receipt = _load_json(
        receipt_path, code="form4_feasibility_parent_hash_mismatch"
    )
    if (
        receipt.get("protocol", {}).get("sha256") != EXPECTED_PROTOCOL_SHA256
        or tuple(receipt.get("fixed_quarters", ())) != FIXED_QUARTERS
        or receipt.get("quarterly_zip_contract", {}).get("required_tables")
        != {key: list(value) for key, value in REQUIRED_TABLES.items()}
        or tuple(receipt.get("fixed_attack_codes", ())) != FIXED_ATTACK_CODES
    ):
        _fail("form4_feasibility_parent_hash_mismatch", "Round 42 contract drifted")
    amendment_path = root / SCHEMA_AMENDMENT_PATH
    amendment_receipt_path = root / SCHEMA_AMENDMENT_RECEIPT_PATH
    if (
        not amendment_path.is_file()
        or _sha256_file(amendment_path) != EXPECTED_SCHEMA_AMENDMENT_SHA256
        or not amendment_receipt_path.is_file()
        or _sha256_file(amendment_receipt_path)
        != EXPECTED_SCHEMA_AMENDMENT_RECEIPT_SHA256
    ):
        _fail(
            "form4_feasibility_parent_hash_mismatch",
            "Round 42 v1.1 schema freeze bytes drifted",
        )
    amendment_receipt = _load_json(
        amendment_receipt_path,
        code="form4_feasibility_parent_hash_mismatch",
    )
    if (
        amendment_receipt.get("amendment", {}).get("sha256")
        != EXPECTED_SCHEMA_AMENDMENT_SHA256
        or amendment_receipt.get("parent_v1_0_protocol", {}).get("sha256")
        != EXPECTED_PROTOCOL_SHA256
        or amendment_receipt.get("parent_v1_0_receipt", {}).get("sha256")
        != EXPECTED_PROTOCOL_RECEIPT_SHA256
        or amendment_receipt.get("frozen_at") != SCHEMA_AMENDMENT_FROZEN_AT
        or tuple(amendment_receipt.get("fixed_quarters", ())) != FIXED_QUARTERS
        or tuple(amendment_receipt.get("new_stable_error_codes", ()))
        != SCHEMA_ATTACK_CODES
    ):
        _fail(
            "form4_feasibility_parent_hash_mismatch",
            "Round 42 v1.1 schema contract drifted",
        )
    for key in (
        "parent_form4_v1_1_protocol",
        "parent_form4_v1_1_receipt",
        "global_trial_ledger_protocol",
    ):
        _bound_file(
            root,
            receipt.get(key, {}),
            code="form4_feasibility_parent_hash_mismatch",
        )
    sec_client = receipt.get("sec_client", {})
    for key in ("implementation", "isolated_tests"):
        _bound_file(
            root,
            sec_client.get(key, {}),
            code="form4_feasibility_parent_hash_mismatch",
        )
    ledger_binding = receipt.get("global_trial_ledger", {})
    ledger_path = _bound_file(
        root,
        ledger_binding,
        code="form4_feasibility_global_trial_drift",
    )
    ledger = _load_json(ledger_path, code="form4_feasibility_global_trial_drift")
    if (
        ledger_binding.get("current_lower_bound") != 6287
        or ledger.get("current_lower_bound") != 6287
        or len(ledger.get("entries", ())) != ledger_binding.get("entry_count")
        or ledger.get("chain_head_sha256") != ledger_binding.get("chain_head_sha256")
        or receipt.get("global_trial_state")
        != {
            "lower_bound_before": 6287,
            "round42_increment": 0,
            "lower_bound_after": 6287,
            "ledger_append_authorized": False,
        }
    ):
        _fail("form4_feasibility_global_trial_drift", "global trial state drifted")
    return {
        "receipt": receipt,
        "amendment_receipt": amendment_receipt,
        "protocol_sha256": EXPECTED_SCHEMA_AMENDMENT_SHA256,
        "protocol_receipt_sha256": EXPECTED_SCHEMA_AMENDMENT_RECEIPT_SHA256,
        "frozen_at": SCHEMA_AMENDMENT_FROZEN_AT,
    }


def _validate_state_claims(claims: Mapping[str, Any] | None) -> dict[str, Any]:
    candidate = dict(SAFE_STATE_CLAIMS if claims is None else claims)
    if set(candidate) != set(SAFE_STATE_CLAIMS):
        _fail("form4_feasibility_result_boundary_breached", "state claim schema drifted")
    if candidate.get("historical_public_time_claimed") is not False:
        _fail(
            "form4_feasibility_historical_time_invented",
            "engineering first-observed time cannot become historical public time",
        )
    if candidate.get("private_identifier_output_requested") is not False:
        _fail(
            "form4_feasibility_private_boundary_breached",
            "public receipt cannot expose identifiers",
        )
    if candidate != SAFE_STATE_CLAIMS:
        _fail(
            "form4_feasibility_result_boundary_breached",
            "feasibility cannot authorize selection, results, Paper, or real money",
        )
    return candidate


def _quarter_parts(value: str) -> tuple[int, int]:
    match = re.fullmatch(r"(?P<year>20\d{2})Q(?P<quarter>[1-4])", value)
    if match is None:
        _fail("form4_feasibility_quarter_set_mismatch", "quarter ID is invalid")
    return int(match.group("year")), int(match.group("quarter"))


def _normalize_sec_date(value: object, *, quarter_id: str | None = None) -> str:
    if not isinstance(value, str) or _FILING_DATE.fullmatch(value) is None:
        _fail("form4_feasibility_filing_date_invalid", "SEC date is not DD-MON-YYYY")
    try:
        parsed = datetime.strptime(value, "%d-%b-%Y").date()
    except ValueError:
        _fail("form4_feasibility_filing_date_invalid", "SEC date is not a real date")
    if parsed.strftime("%d-%b-%Y").upper() != value:
        _fail("form4_feasibility_filing_date_invalid", "SEC date is not canonical")
    if quarter_id is not None:
        year, quarter = _quarter_parts(quarter_id)
        actual_quarter = (parsed.month - 1) // 3 + 1
        if parsed.year != year or actual_quarter != quarter:
            _fail("form4_feasibility_filing_date_invalid", "SEC date is outside its quarter")
    return parsed.isoformat()


def _normalize_xml_date(value: str) -> str:
    try:
        parsed = datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        _fail(
            "form4_feasibility_complete_submission_mismatch",
            "ownership XML transaction date is invalid",
        )
    if parsed.isoformat() != value:
        _fail(
            "form4_feasibility_complete_submission_mismatch",
            "ownership XML transaction date is not canonical",
        )
    return value


def _pure_member_name(value: object) -> str:
    if not isinstance(value, str) or not value:
        _fail("form4_feasibility_zip_member_mismatch", "metadata table URL is missing")
    if (
        unquote(value) != value
        or "/" in value
        or "\\" in value
        or PurePosixPath(value).name != value
        or value in {".", ".."}
    ):
        _fail("form4_feasibility_zip_member_mismatch", "table URL is not a pure basename")
    return value


def _metadata_contract(payload: object) -> dict[str, tuple[str, ...]] | None:
    if not isinstance(payload, dict) or not isinstance(payload.get("tables"), list):
        return None
    result: dict[str, tuple[str, ...]] = {}
    try:
        for table in payload["tables"]:
            if not isinstance(table, dict):
                return None
            name = _pure_member_name(table.get("url"))
            columns = table.get("tableSchema", {}).get("columns")
            if not isinstance(columns, list) or not columns:
                return None
            names = tuple(column.get("name") for column in columns if isinstance(column, dict))
            if len(names) != len(columns) or any(not isinstance(item, str) for item in names):
                return None
            if len(set(names)) != len(names) or name in result:
                _fail("form4_feasibility_zip_member_mismatch", "metadata role is duplicated")
            result[name] = names  # type: ignore[assignment]
    except (AttributeError, TypeError):
        return None
    return result


def _physical_header_projection(
    metadata_header: tuple[str, ...],
    *,
    table_name: str,
    quarter_id: str,
    amendment_receipt: Mapping[str, Any],
    allow_variable_submission_profile: bool = False,
) -> tuple[str, ...]:
    policy = amendment_receipt.get("metadata_to_physical_policy", {})
    projected = list(metadata_header)
    if table_name == "SUBMISSION.tsv":
        contract = policy.get("submission_contact_omission", {})
        contacts = contract.get("metadata_only_columns")
        left = contract.get("metadata_left_anchor")
        right = contract.get("metadata_right_anchor")
        if not isinstance(contacts, list) or not all(
            isinstance(item, str) for item in contacts
        ):
            _fail(
                "form4_feasibility_parent_hash_mismatch",
                "v1.1 contact omission policy is invalid",
            )
        try:
            left_index = projected.index(str(left))
            right_index = projected.index(str(right))
        except ValueError:
            _fail(
                "form4_feasibility_contact_omission_mismatch",
                "submission contact anchors are missing",
            )
        if (
            right_index <= left_index
            or projected[left_index + 1 : right_index] != contacts
            or any(projected.count(item) != 1 for item in contacts)
        ):
            _fail(
                "form4_feasibility_contact_omission_mismatch",
                "submission contact columns are not the one frozen contiguous omission",
            )
        del projected[left_index + 1 : right_index]
        expected_columns = 14 if quarter_id == "2026Q2" else 13
        expected_metadata_columns = expected_columns + len(contacts)
        if (
            not allow_variable_submission_profile
            and (
                len(metadata_header) != expected_metadata_columns
                or len(projected) != expected_columns
            )
        ):
            _fail(
                "form4_feasibility_contact_omission_mismatch",
                "submission column count differs from its fixed quarter profile",
            )
        aff_present = "AFF10B5ONE" in projected
        if not allow_variable_submission_profile and aff_present != (quarter_id == "2026Q2"):
            _fail(
                "form4_feasibility_contact_omission_mismatch",
                "AFF10B5ONE quarter profile drifted",
            )
    elif table_name in {"NONDERIV_TRANS.tsv", "DERIV_TRANS.tsv"}:
        aliases = policy.get("swap_footnote_aliases", ())
        alias = next(
            (
                item
                for item in aliases
                if isinstance(item, Mapping) and item.get("role") == table_name
            ),
            None,
        )
        if alias is None:
            _fail(
                "form4_feasibility_parent_hash_mismatch",
                "v1.1 swap footnote policy is missing",
            )
        index = int(alias.get("one_based_position", 0)) - 1
        metadata_name = alias.get("metadata_name")
        physical_name = alias.get("physical_name")
        if (
            index < 0
            or len(projected) != alias.get("metadata_columns")
            or index >= len(projected)
            or projected[index] != metadata_name
            or projected.count(str(metadata_name)) != 1
        ):
            _fail(
                "form4_feasibility_swap_footnote_alias_mismatch",
                f"{table_name} swap footnote metadata alias drifted",
            )
        projected[index] = str(physical_name)
        if len(projected) != alias.get("physical_columns"):
            _fail(
                "form4_feasibility_swap_footnote_alias_mismatch",
                f"{table_name} swap footnote physical width drifted",
            )
    else:
        exact_roles = policy.get("exact_match_roles", {})
        if exact_roles.get(table_name) != len(projected):
            _fail(
                "form4_feasibility_unexpected_metadata_physical_drift",
                f"{table_name} metadata width drifted",
            )
    if any(anchor not in projected for anchor in REQUIRED_TABLES[table_name]):
        _fail("form4_feasibility_header_mismatch", f"{table_name} anchor missing")
    return tuple(projected)


def _validate_physical_header_profile(
    header: tuple[str, ...],
    *,
    table_name: str,
    quarter_id: str,
    amendment_receipt: Mapping[str, Any],
) -> None:
    profiles = amendment_receipt.get("physical_header_profiles", {})
    profile_key = (
        f"SUBMISSION.tsv@{quarter_id}" if table_name == "SUBMISSION.tsv" else table_name
    )
    profile = profiles.get(profile_key)
    if not isinstance(profile, Mapping):
        _fail(
            "form4_feasibility_parent_hash_mismatch",
            f"physical header profile is missing for {profile_key}",
        )
    rendered = "\t".join(header).encode("utf-8")
    if len(header) != profile.get("columns") or _sha256_bytes(rendered) != profile.get(
        "sha256"
    ):
        _fail(
            "form4_feasibility_physical_header_profile_mismatch",
            f"{profile_key} does not match the frozen physical profile",
        )


def _read_tsv(
    raw: bytes,
    *,
    table_name: str,
    expected_header: tuple[str, ...],
    quarter_id: str,
    amendment_receipt: Mapping[str, Any],
    keep_accessions: set[str] | None = None,
    known_accessions: set[str] | None = None,
    validate_physical_profile: bool = True,
) -> list[dict[str, str]]:
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        _fail("form4_feasibility_header_mismatch", f"{table_name} is not UTF-8")
    reader = csv.DictReader(io.StringIO(text, newline=""), delimiter="\t")
    header = tuple(reader.fieldnames or ())
    if header != expected_header or len(set(header)) != len(header):
        _fail(
            "form4_feasibility_unexpected_metadata_physical_drift",
            f"{table_name} differs from the sole v1.1 metadata projection",
        )
    if validate_physical_profile:
        _validate_physical_header_profile(
            header,
            table_name=table_name,
            quarter_id=quarter_id,
            amendment_receipt=amendment_receipt,
        )
    if any(anchor not in header for anchor in REQUIRED_TABLES[table_name]):
        _fail("form4_feasibility_header_mismatch", f"{table_name} anchor missing")
    rows: list[dict[str, str]] = []
    try:
        for row in reader:
            if None in row or any(value is None for value in row.values()):
                _fail("form4_feasibility_header_mismatch", f"{table_name} row width drifted")
            item = {str(key): str(value) for key, value in row.items()}
            accession = item.get("ACCESSION_NUMBER", "")
            if known_accessions is not None and accession and accession not in known_accessions:
                _fail(
                    "form4_feasibility_accession_invalid",
                    f"{table_name} references an unknown accession",
                )
            if keep_accessions is None or accession in keep_accessions:
                rows.append(item)
    except csv.Error:
        _fail("form4_feasibility_header_mismatch", f"{table_name} is not valid TSV")
    return rows


def _stored_bytes(
    client: SecEdgarClient,
    receipt: Mapping[str, Any],
    *,
    expected_kind: str,
    code: str,
) -> bytes:
    if receipt.get("source_kind") != expected_kind:
        _fail(code, f"expected stored {expected_kind} receipt")
    if (
        receipt.get("known_at") is not None
        or receipt.get("public_at") is not None
        or receipt.get("observation_mode")
        != "engineering_fetch_not_contemporaneous_evidence"
    ):
        _fail(
            "form4_feasibility_historical_time_invented",
            "stored engineering receipt contains a historical-time claim",
        )
    try:
        body = client.object_bytes(receipt)
    except SecEdgarClientError as exc:
        if exc.code in {"sec_cached_object_invalid", "sec_cached_receipt_invalid"}:
            _fail("form4_feasibility_content_hash_mismatch", exc.code)
        _fail(code, exc.code)
    if receipt.get("body_sha256") != _sha256_bytes(body) or receipt.get("byte_count") != len(body):
        _fail("form4_feasibility_content_hash_mismatch", "stored body receipt drifted")
    return body


def _parse_quarter_zip(
    client: SecEdgarClient,
    quarter_id: str,
    receipt: Mapping[str, Any],
    *,
    required_headers: Mapping[str, Sequence[str]],
    amendment_receipt: Mapping[str, Any],
) -> dict[str, Any]:
    body = _stored_bytes(
        client,
        receipt,
        expected_kind="insider_transactions_quarter_zip",
        code="form4_feasibility_zip_member_mismatch",
    )
    url_path = urlparse(str(receipt.get("requested_url", ""))).path.lower()
    if not url_path.endswith(f"/{quarter_id.lower()}_form345.zip"):
        _fail("form4_feasibility_quarter_set_mismatch", "quarter receipt URL drifted")
    try:
        archive = zipfile.ZipFile(io.BytesIO(body))
    except zipfile.BadZipFile:
        _fail("form4_feasibility_zip_member_mismatch", "quarter object is not a ZIP")
    with archive:
        infos = [item for item in archive.infolist() if not item.is_dir()]
        names = [item.filename for item in infos]
        if len(names) != len(set(names)) or any(
            PurePosixPath(name).is_absolute()
            or ".." in PurePosixPath(name).parts
            or "\\" in name
            or unquote(name) != name
            for name in names
        ):
            _fail("form4_feasibility_zip_member_mismatch", "ZIP member is unsafe or duplicated")
        total_size = sum(item.file_size for item in infos)
        compressed_size = sum(item.compress_size for item in infos)
        if (
            total_size <= 0
            or total_size > 1_000_000_000
            or compressed_size <= 0
            or total_size / compressed_size > 200
            or any(item.file_size > 500_000_000 for item in infos)
        ):
            _fail("form4_feasibility_zip_member_mismatch", "ZIP expansion limit exceeded")
        try:
            corrupt = archive.testzip()
        except (OSError, RuntimeError, zipfile.BadZipFile):
            _fail("form4_feasibility_zip_member_mismatch", "ZIP CRC replay failed")
        if corrupt is not None:
            _fail("form4_feasibility_zip_member_mismatch", "ZIP member CRC is invalid")
        metadata_candidates: list[tuple[str, dict[str, tuple[str, ...]]]] = []
        for info in infos:
            if info.file_size > 2_000_000:
                continue
            try:
                payload = json.loads(archive.read(info).decode("utf-8-sig"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                continue
            contract = _metadata_contract(payload)
            if contract is not None:
                metadata_candidates.append((info.filename, contract))
        if len(metadata_candidates) != 1:
            _fail(
                "form4_feasibility_zip_member_mismatch",
                "ZIP must contain exactly one W3C Table Group metadata object",
            )
        _, metadata = metadata_candidates[0]
        if set(metadata) != set(required_headers):
            _fail("form4_feasibility_zip_member_mismatch", "metadata table roles drifted")
        physical_headers: dict[str, tuple[str, ...]] = {}
        for table_name, anchors in required_headers.items():
            if names.count(table_name) != 1:
                _fail("form4_feasibility_zip_member_mismatch", f"{table_name} missing")
            metadata_header = metadata[table_name]
            if any(anchor not in metadata_header for anchor in anchors):
                _fail("form4_feasibility_header_mismatch", f"{table_name} anchor missing")
            physical_headers[table_name] = _physical_header_projection(
                metadata_header,
                table_name=table_name,
                quarter_id=quarter_id,
                amendment_receipt=amendment_receipt,
            )
        submissions = _read_tsv(
            archive.read("SUBMISSION.tsv"),
            table_name="SUBMISSION.tsv",
            expected_header=physical_headers["SUBMISSION.tsv"],
            quarter_id=quarter_id,
            amendment_receipt=amendment_receipt,
        )
        form4_rows: list[dict[str, str]] = []
        seen: set[str] = set()
        for row in submissions:
            raw_form = row["DOCUMENT_TYPE"]
            if raw_form.casefold() in {"4", "4/a"} and raw_form not in ALLOWED_DOCUMENT_TYPES:
                _fail("form4_feasibility_form_type_invalid", "Form 4 type is not exact")
            if raw_form not in ALLOWED_DOCUMENT_TYPES:
                continue
            accession = row["ACCESSION_NUMBER"]
            if _ACCESSION.fullmatch(accession) is None:
                _fail("form4_feasibility_accession_invalid", "SUBMISSION accession is invalid")
            if accession in seen:
                _fail("form4_feasibility_accession_duplicate", "SUBMISSION accession is duplicated")
            seen.add(accession)
            if _CIK.fullmatch(row["ISSUERCIK"]) is None:
                _fail("form4_feasibility_complete_submission_mismatch", "issuer CIK is invalid")
            item = dict(row)
            item["normalized_FILING_DATE"] = _normalize_sec_date(
                row["FILING_DATE"], quarter_id=quarter_id
            )
            form4_rows.append(item)
        if len(form4_rows) < 3:
            _fail("form4_feasibility_sample_too_small", f"{quarter_id} has fewer than 3 filings")
        form4_rows.sort(
            key=lambda row: (row["normalized_FILING_DATE"], row["ACCESSION_NUMBER"])
        )
        n = len(form4_rows)
        base = (("first", 0), ("median", (n - 1) // 2), ("last", n - 1))
        samples: list[dict[str, str]] = []
        selected: set[str] = set()
        for label, index in base:
            row = dict(form4_rows[index])
            row["sample_role"] = label
            samples.append(row)
            selected.add(row["ACCESSION_NUMBER"])
        if len(selected) != 3:
            _fail("form4_feasibility_sample_too_small", "base sample accessions are not distinct")
        amendments = [row for row in form4_rows if row["DOCUMENT_TYPE"] == "4/A"]
        if not amendments:
            _fail("form4_feasibility_amendment_sample_missing", f"{quarter_id} has no 4/A")
        extra = next(
            (row for row in amendments if row["ACCESSION_NUMBER"] not in selected),
            None,
        )
        if extra is not None:
            item = dict(extra)
            item["sample_role"] = "amendment"
            samples.append(item)
            selected.add(item["ACCESSION_NUMBER"])
            amendment_state = "amendment_added"
        else:
            amendment_state = "amendment_covered_by_base"
        if not 3 <= len(samples) <= 4 or not any(
            row["DOCUMENT_TYPE"] == "4/A" for row in samples
        ):
            _fail("form4_feasibility_sample_not_deterministic", "amendment selection drifted")
        all_submission_accessions = {
            row["ACCESSION_NUMBER"]
            for row in submissions
            if _ACCESSION.fullmatch(row.get("ACCESSION_NUMBER", ""))
        }
        tables: dict[str, list[dict[str, str]]] = {"SUBMISSION.tsv": submissions}
        for table_name in required_headers:
            if table_name == "SUBMISSION.tsv":
                continue
            tables[table_name] = _read_tsv(
                archive.read(table_name),
                table_name=table_name,
                expected_header=physical_headers[table_name],
                quarter_id=quarter_id,
                amendment_receipt=amendment_receipt,
                keep_accessions=selected,
                known_accessions=all_submission_accessions,
            )
    return {
        "quarter_id": quarter_id,
        "tables": tables,
        "form4_rows": form4_rows,
        "samples": samples,
        "amendment_state": amendment_state,
        "receipt_sha256": receipt.get("receipt_sha256"),
        "body_sha256": receipt.get("body_sha256"),
    }


def _parse_utc(value: object, *, code: str) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        _fail(code, "timestamp is not canonical UTC")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        _fail(code, "timestamp is invalid")
    if parsed.utcoffset() is None or parsed.astimezone(UTC).isoformat().replace("+00:00", "Z") != value:
        _fail(code, "timestamp is not canonical UTC")
    return parsed.astimezone(UTC)


def _normalize_cik(value: object) -> str:
    text = str(value).strip()
    if _CIK.fullmatch(text) is None:
        _fail("form4_feasibility_complete_submission_mismatch", "CIK is invalid")
    return str(int(text))


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _first_text(node: ElementTree.Element, name: str) -> str | None:
    for item in node.iter():
        if _local_name(item.tag) == name and item.text is not None:
            value = item.text.strip()
            if value:
                return value
    return None


def _child(node: ElementTree.Element, name: str) -> ElementTree.Element | None:
    return next((item for item in node.iter() if _local_name(item.tag) == name), None)


def _transaction_value(node: ElementTree.Element, name: str) -> str:
    container = _child(node, name)
    if container is None:
        return ""
    value = _first_text(container, "value")
    return value or ""


def _number(value: str) -> str:
    if not value:
        return ""
    try:
        parsed = Decimal(value.replace(",", ""))
    except InvalidOperation:
        _fail("form4_feasibility_complete_submission_mismatch", "numeric transaction value invalid")
    if not parsed.is_finite():
        _fail("form4_feasibility_complete_submission_mismatch", "numeric transaction value invalid")
    return format(parsed.normalize(), "f")


def _bulk_transaction(row: Mapping[str, str]) -> tuple[str, ...]:
    transaction_date = row.get("TRANS_DATE", "").strip()
    return (
        row.get("TRANS_FORM_TYPE", "").strip(),
        row.get("TRANS_CODE", "").strip(),
        row.get("TRANS_ACQUIRED_DISP_CD", "").strip(),
        row.get("SECURITY_TITLE", "").strip(),
        _normalize_sec_date(transaction_date),
        row.get("EQUITY_SWAP_INVOLVED", "").strip(),
        _number(row.get("TRANS_SHARES", "").strip()),
        _number(row.get("TRANS_PRICEPERSHARE", "").strip()),
        row.get("DIRECT_INDIRECT_OWNERSHIP", "").strip(),
    )


def _raw_transaction(node: ElementTree.Element) -> tuple[str, ...]:
    transaction_date = _transaction_value(node, "transactionDate")
    return (
        _first_text(node, "transactionFormType") or "",
        _first_text(node, "transactionCode") or "",
        _transaction_value(node, "transactionAcquiredDisposedCode"),
        _transaction_value(node, "securityTitle"),
        _normalize_xml_date(transaction_date),
        _first_text(node, "equitySwapInvolved") or "",
        _number(_transaction_value(node, "transactionShares")),
        _number(_transaction_value(node, "transactionPricePerShare")),
        _transaction_value(node, "directOrIndirectOwnership"),
    )


def _extract_tag(text: str, tag: str) -> str | None:
    match = re.search(rf"<{re.escape(tag)}>\s*([^<\r\n]+)", text, flags=re.IGNORECASE)
    return match.group(1).strip() if match is not None else None


def _extract_header_label(text: str, label: str) -> str | None:
    match = re.search(
        rf"^\s*{re.escape(label)}\s*:\s*([^\r\n]+?)\s*$",
        text,
        flags=re.IGNORECASE | re.MULTILINE,
    )
    return match.group(1).strip() if match is not None else None


def _parse_complete_submission(raw: bytes) -> dict[str, Any]:
    text = raw.decode("latin-1")
    if re.search(r"<!\s*(?:DOCTYPE|ENTITY)\b", text, flags=re.IGNORECASE):
        _fail(
            "form4_feasibility_complete_submission_mismatch",
            "complete submission contains a forbidden DTD or entity declaration",
        )
    if re.search(r"<SEC-DOCUMENT(?:\s|>)", text, flags=re.IGNORECASE) is None:
        _fail(
            "form4_feasibility_complete_submission_mismatch",
            "complete submission outer SGML is missing",
        )
    accession = _extract_tag(text, "ACCESSION-NUMBER") or _extract_header_label(
        text, "ACCESSION NUMBER"
    )
    form = _extract_tag(text, "CONFORMED-SUBMISSION-TYPE") or _extract_header_label(
        text, "CONFORMED SUBMISSION TYPE"
    )
    documents = re.findall(
        r"<DOCUMENT>\s*(.*?)\s*</DOCUMENT>",
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if accession is None or form is None or not documents:
        _fail("form4_feasibility_complete_submission_mismatch", "complete submission shape invalid")
    primary_documents: list[str] = []
    for document in documents:
        document_type = _extract_tag(document, "TYPE")
        if document_type in ALLOWED_DOCUMENT_TYPES:
            primary_documents.append(document)
    if form not in ALLOWED_DOCUMENT_TYPES or len(primary_documents) != 1:
        _fail(
            "form4_feasibility_complete_submission_mismatch",
            "complete submission must contain one Form 4/4-A primary document",
        )
    primary = primary_documents[0]
    if _extract_tag(primary, "TYPE") != form:
        _fail(
            "form4_feasibility_complete_submission_mismatch",
            "primary document type differs from submission header",
        )
    ownership_documents = re.findall(
        r"<ownershipDocument(?:\s[^>]*)?>.*?</ownershipDocument>",
        primary,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if len(ownership_documents) != 1:
        _fail(
            "form4_feasibility_complete_submission_mismatch",
            "primary document must contain one ownership XML document",
        )
    try:
        root = ElementTree.fromstring(ownership_documents[0])
    except ElementTree.ParseError:
        _fail("form4_feasibility_complete_submission_mismatch", "ownership XML invalid")
    xml_form = _first_text(root, "documentType")
    issuer = _child(root, "issuer")
    issuer_cik = _first_text(issuer, "issuerCik") if issuer is not None else None
    if xml_form is None or issuer_cik is None:
        _fail("form4_feasibility_complete_submission_mismatch", "ownership XML identity missing")
    transactions = {
        "NONDERIV_TRANS.tsv": [
            _raw_transaction(item)
            for item in root.iter()
            if _local_name(item.tag) == "nonDerivativeTransaction"
        ],
        "DERIV_TRANS.tsv": [
            _raw_transaction(item)
            for item in root.iter()
            if _local_name(item.tag) == "derivativeTransaction"
        ],
    }
    explicit_targets = {
        value
        for value in (
            _first_text(root, "amendsAccessionNumber"),
            _extract_tag(text, "AMENDS-ACCESSION-NUMBER"),
        )
        if isinstance(value, str) and _ACCESSION.fullmatch(value)
    }
    return {
        "accession": accession,
        "header_form": form,
        "xml_form": xml_form,
        "issuer_cik": issuer_cik,
        "transactions": transactions,
        "explicit_amendment_targets": explicit_targets,
    }


def _daily_index_row(
    body: bytes,
    *,
    accession: str,
    form: str,
    filing_date: str,
) -> dict[str, str]:
    matches: list[dict[str, str]] = []
    for line in body.decode("latin-1").splitlines():
        if len(line) < 12:
            continue
        parsed_form = line[:12].strip()
        match = _INDEX_ROW_SUFFIX.search(line[12:])
        if match is None or match.group("accession") != accession:
            continue
        item = match.groupdict()
        item["form"] = parsed_form
        matches.append(item)
    if len(matches) != 1:
        _fail(
            "form4_feasibility_daily_index_missing_or_ambiguous",
            "daily index exact accession path is absent or ambiguous",
        )
    row = matches[0]
    if (
        row["form"] != form
        or datetime.strptime(row["date"], "%Y%m%d").date().isoformat() != filing_date
        or _normalize_cik(row["cik"]) != _normalize_cik(row["path_cik"])
        or row["path"]
        != f"edgar/data/{_normalize_cik(row['cik'])}/{accession}.txt"
    ):
        _fail("form4_feasibility_daily_index_missing_or_ambiguous", "daily index row drifted")
    return row


def _validate_filing_evidence(
    client: SecEdgarClient,
    sample: Mapping[str, str],
    evidence: Mapping[str, Any],
    *,
    quarter: Mapping[str, Any],
    all_submissions: Mapping[str, Mapping[str, str]],
) -> dict[str, Any]:
    if set(evidence) != {
        "daily_index_receipt",
        "complete_submission_receipt",
    }:
        _fail("form4_feasibility_sample_not_deterministic", "filing evidence schema drifted")
    daily_receipt = evidence["daily_index_receipt"]
    complete_receipt = evidence["complete_submission_receipt"]
    if not isinstance(daily_receipt, Mapping) or not isinstance(complete_receipt, Mapping):
        _fail("form4_feasibility_sample_not_deterministic", "filing receipts missing")
    daily_body = _stored_bytes(
        client,
        daily_receipt,
        expected_kind="edgar_daily_form_index",
        code="form4_feasibility_daily_index_missing_or_ambiguous",
    )
    daily_match = _DAILY_INDEX_URL.fullmatch(urlparse(str(daily_receipt.get("requested_url", ""))).path)
    filing_date = sample["normalized_FILING_DATE"]
    if daily_match is None or datetime.strptime(daily_match.group("date"), "%Y%m%d").date().isoformat() != filing_date:
        _fail("form4_feasibility_daily_index_missing_or_ambiguous", "daily index date drifted")
    daily_row = _daily_index_row(
        daily_body,
        accession=sample["ACCESSION_NUMBER"],
        form=sample["DOCUMENT_TYPE"],
        filing_date=filing_date,
    )
    complete_body = _stored_bytes(
        client,
        complete_receipt,
        expected_kind="edgar_complete_submission",
        code="form4_feasibility_complete_submission_mismatch",
    )
    complete_match = _COMPLETE_URL.fullmatch(
        urlparse(str(complete_receipt.get("requested_url", ""))).path
    )
    expected_directory = sample["ACCESSION_NUMBER"].replace("-", "")
    if (
        complete_match is None
        or complete_match.group("accession") != sample["ACCESSION_NUMBER"]
        or complete_match.group("directory") != expected_directory
        or _normalize_cik(complete_match.group("cik"))
        != _normalize_cik(daily_row["cik"])
    ):
        _fail("form4_feasibility_complete_submission_mismatch", "complete archive path drifted")
    daily_observed = _parse_utc(
        daily_receipt.get("first_observed_at"),
        code="form4_feasibility_historical_time_invented",
    )
    complete_started = _parse_utc(
        complete_receipt.get("request_started_at"),
        code="form4_feasibility_historical_time_invented",
    )
    if complete_started < daily_observed:
        _fail(
            "form4_feasibility_historical_time_invented",
            "complete submission was observed before its daily-index evidence",
        )
    parsed = _parse_complete_submission(complete_body)
    if parsed["accession"] != sample["ACCESSION_NUMBER"]:
        _fail("form4_feasibility_complete_submission_mismatch", "raw accession drifted")
    if parsed["header_form"] not in ALLOWED_DOCUMENT_TYPES or parsed["xml_form"] not in ALLOWED_DOCUMENT_TYPES:
        _fail("form4_feasibility_form_type_invalid", "raw filing is not Form 4/4-A")
    if parsed["header_form"] != sample["DOCUMENT_TYPE"] or parsed["xml_form"] != sample["DOCUMENT_TYPE"]:
        _fail("form4_feasibility_complete_submission_mismatch", "raw form type drifted")
    if _normalize_cik(parsed["issuer_cik"]) != _normalize_cik(sample["ISSUERCIK"]):
        _fail("form4_feasibility_complete_submission_mismatch", "raw issuer drifted")
    bulk_by_role = {
        role: [
            _bulk_transaction(row)
            for row in quarter["tables"][role]
            if row["ACCESSION_NUMBER"] == sample["ACCESSION_NUMBER"]
        ]
        for role in ("NONDERIV_TRANS.tsv", "DERIV_TRANS.tsv")
    }
    if any(
        Counter(parsed["transactions"][role]) != Counter(bulk_by_role[role])
        for role in bulk_by_role
    ):
        _fail("form4_feasibility_complete_submission_mismatch", "bulk/raw transaction drifted")
    bulk_transactions = [
        row for role in ("NONDERIV_TRANS.tsv", "DERIV_TRANS.tsv") for row in bulk_by_role[role]
    ]
    semantics = Counter((row[1], row[2]) for row in bulk_transactions)
    for transaction in bulk_transactions:
        if transaction[1:3] == ("P", "A"):
            if transaction[5].strip().casefold() not in {"0", "false"}:
                _fail("form4_feasibility_complete_submission_mismatch", "P/A is an equity swap")
            try:
                shares = Decimal(transaction[6])
                price = Decimal(transaction[7])
            except InvalidOperation:
                _fail("form4_feasibility_complete_submission_mismatch", "P/A amount invalid")
            if not shares.is_finite() or not price.is_finite() or shares <= 0 or price <= 0:
                _fail("form4_feasibility_complete_submission_mismatch", "P/A amount invalid")
    target: str | None = None
    if sample["DOCUMENT_TYPE"] == "4/A":
        targets = parsed["explicit_amendment_targets"]
        if len(targets) != 1:
            _fail(
                "form4_feasibility_amendment_target_unresolved",
                "4/A lacks one explicit as-filed original accession",
            )
        target = next(iter(targets))
        original = all_submissions.get(target)
        if original is None or original.get("DOCUMENT_TYPE") != "4":
            _fail(
                "form4_feasibility_amendment_target_unresolved",
                "explicit amendment target is not a replayable original Form 4",
            )
        original_date = original.get("normalized_FILING_DATE")
        if original_date is None or original_date > filing_date:
            _fail("form4_feasibility_amendment_target_unresolved", "amendment target is later")
        date_of_orig = sample.get("DATE_OF_ORIG_SUB", "")
        if not date_of_orig:
            _fail("form4_feasibility_amendment_target_unresolved", "DATE_OF_ORIG_SUB missing")
        target_quarter = next(
            (item for item in FIXED_QUARTERS if item[:4] == original_date[:4] and ((int(original_date[5:7]) - 1) // 3 + 1) == int(item[-1])),
            None,
        )
        if target_quarter is None:
            _fail(
                "form4_feasibility_amendment_target_unresolved",
                "original-date quarter is outside the frozen replay set",
            )
        normalized_anchor = _normalize_sec_date(date_of_orig, quarter_id=target_quarter)
        if normalized_anchor != original_date:
            _fail("form4_feasibility_amendment_target_unresolved", "original-date anchor drifted")
    elif parsed["explicit_amendment_targets"]:
        _fail("form4_feasibility_amendment_target_unresolved", "original Form 4 claims amendment target")
    return {
        "quarter": quarter["quarter_id"],
        "sample_role": sample["sample_role"],
        "document_type": sample["DOCUMENT_TYPE"],
        "accession_commitment": _sha256_bytes(sample["ACCESSION_NUMBER"].encode("ascii")),
        "daily_index_sha256": daily_receipt.get("body_sha256"),
        "complete_submission_sha256": complete_receipt.get("body_sha256"),
        "semantics": {f"{code}/{ad}": count for (code, ad), count in sorted(semantics.items())},
        "amendment_target_commitment": (
            _sha256_bytes(target.encode("ascii")) if target is not None else None
        ),
    }


def _admission_controls(*, real_sample_replayed: bool = False) -> dict[str, Any]:
    reasons = {
        "01": "frozen_parent_lineage_hashes_verified",
        "04": "source_scope_sec_form_4_and_exact_form_types_verified",
        "02": "project_wide_exact_use_and_complete_attempt_ledger_not_established",
        "03": "independent_encrypted_quarantine_evidence_not_established",
        "05": "full_filing_denominator_not_replayed",
        "06": "full_denominator_as_filed_content_not_replayed",
        "07": "fixed_2005q4_through_2026q2_coverage_not_replayed",
        "08": "external_historical_known_at_evidence_absent",
        "09": "decision_and_trade_clock_mapping_not_executed",
        "10": "full_denominator_version_chain_not_replayed",
        "11": "full_denominator_semantics_not_replayed",
        "12": "economic_event_deduplication_not_replayed",
        "13": "pit_security_universe_not_replayed",
        "14": "pit_market_execution_inputs_not_replayed",
        "15": "local_fixture_attacks_are_not_full_independent_admission_attacks",
        "16": (
            "authorized_real_sample_independently_replayed"
            if real_sample_replayed
            else "real_sample_not_authorized_or_replayed"
        ),
    }
    gates = [
        {
            "id": gate_id,
            "name": name,
            "passed": gate_id in {"01", "04"}
            or (gate_id == "16" and real_sample_replayed),
            "reason": reasons[gate_id],
        }
        for gate_id, name in FORM4_ADMISSION_GATES
    ]
    return {
        "passed": 3 if real_sample_replayed else 2,
        "total": 16,
        "all_passed": False,
        "gates": gates,
        "candidate_selection_authorized": False,
        "strategy_run_authorized": False,
    }


def build_form4_feasibility_failure_receipt(
    error: Form4AdmissionFeasibilityError,
    *,
    sample_count: int = 0,
    evidence_mode: str = "none_after_failure",
    private_manifest_sha256: str | None = None,
) -> dict[str, Any]:
    """Build an identifier-free public stop receipt from a fail-closed error."""

    if isinstance(sample_count, bool) or not isinstance(sample_count, int) or not 0 <= sample_count <= 12:
        _fail("form4_feasibility_result_boundary_breached", "failure sample count is invalid")
    if evidence_mode not in {"none_after_failure", "authorized_real_sample"}:
        _fail("form4_feasibility_result_boundary_breached", "failure evidence mode is invalid")
    if private_manifest_sha256 is not None and re.fullmatch(
        r"[0-9a-f]{64}", private_manifest_sha256
    ) is None:
        _fail("form4_feasibility_result_boundary_breached", "private manifest hash is invalid")
    code = (
        error.code
        if error.code in ALL_ATTACK_CODES
        else "form4_feasibility_result_boundary_breached"
    )
    controls = _admission_controls()
    return {
        "schema_version": SCHEMA_VERSION,
        "protocol_sha256": EXPECTED_SCHEMA_AMENDMENT_SHA256,
        "protocol_receipt_sha256": EXPECTED_SCHEMA_AMENDMENT_RECEIPT_SHA256,
        "frozen_at": SCHEMA_AMENDMENT_FROZEN_AT,
        "status": "stopped_no_admission_claim",
        "fixed_quarters": list(FIXED_QUARTERS),
        "sample_count": sample_count,
        "admission_controls": controls,
        "attack_results": {"error_code": code, "identifier_detail_included": False},
        "stop_reasons": [code],
        "state_boundary": {
            "evidence_mode": evidence_mode,
            "authorized_real_form4_rows": 0,
            "form4_specific_admission": {
                "passed": controls["passed"],
                "total": controls["total"],
                "all_passed": controls["all_passed"],
            },
            "candidate_selection_count": 0,
            "strategy_run_count": 0,
            "performance_present": False,
            "paper": {
                "authorized": False,
                "state": "all_cash",
                "backfilled_trades": 0,
                "positions": [],
            },
            "real_money_action_usd": 0,
            "today_action": "今天不下單",
        },
        "private_manifest_sha256": private_manifest_sha256,
    }


def audit_form4_admission_feasibility(
    client: SecEdgarClient,
    *,
    repository_root: str | Path,
    quarter_receipts: Mapping[str, Mapping[str, Any]],
    filing_evidence: Mapping[str, Mapping[str, Any]],
    evidence_mode: str,
    real_sample_authorized: bool = False,
    private_manifest_sha256: str | None = None,
    state_claims: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Replay a sealed Form 4 feasibility sample without authorizing a strategy.

    All market identifiers remain inside the in-memory private manifest commitment.
    The function never performs a fetch: every byte must already be bound by a stored
    :class:`SecEdgarClient` receipt.
    """

    binding = _load_protocol_binding(Path(repository_root))
    _validate_state_claims(state_claims)
    if evidence_mode not in {"synthetic_fixture", "authorized_real_sample"}:
        _fail(
            "form4_feasibility_private_boundary_breached",
            "evidence mode is outside the frozen feasibility boundary",
        )
    is_real_sample = evidence_mode == "authorized_real_sample"
    if is_real_sample != real_sample_authorized:
        _fail(
            "form4_feasibility_private_boundary_breached",
            "real-sample replay requires a separately validated authorization",
        )
    if is_real_sample:
        if private_manifest_sha256 is None or re.fullmatch(
            r"[0-9a-f]{64}", private_manifest_sha256
        ) is None:
            _fail(
                "form4_feasibility_private_boundary_breached",
                "real-sample replay must bind one private manifest",
            )
    elif private_manifest_sha256 is not None:
        _fail(
            "form4_feasibility_private_boundary_breached",
            "synthetic replay cannot claim a stored private manifest",
        )
    if set(quarter_receipts) != set(FIXED_QUARTERS):
        _fail("form4_feasibility_quarter_set_mismatch", "fixed quarter set drifted")
    required_headers = binding["receipt"]["quarterly_zip_contract"]["required_tables"]
    quarters = {
        quarter_id: _parse_quarter_zip(
            client,
            quarter_id,
            quarter_receipts[quarter_id],
            required_headers=required_headers,
            amendment_receipt=binding["amendment_receipt"],
        )
        for quarter_id in FIXED_QUARTERS
    }
    samples = [row for quarter in quarters.values() for row in quarter["samples"]]
    accessions = [row["ACCESSION_NUMBER"] for row in samples]
    if not 9 <= len(samples) <= 12 or len(set(accessions)) != len(accessions):
        _fail("form4_feasibility_sample_not_deterministic", "sample count or identity drifted")
    if set(filing_evidence) != set(accessions):
        _fail("form4_feasibility_sample_not_deterministic", "filing evidence set drifted")
    all_submissions = {
        row["ACCESSION_NUMBER"]: row
        for quarter in quarters.values()
        for row in quarter["form4_rows"]
    }
    private_samples = [
        _validate_filing_evidence(
            client,
            sample,
            filing_evidence[sample["ACCESSION_NUMBER"]],
            quarter=quarters[next(
                quarter_id
                for quarter_id, quarter in quarters.items()
                if sample in quarter["samples"]
            )],
            all_submissions=all_submissions,
        )
        for sample in samples
    ]
    private_manifest = {
        "schema_version": 1,
        "evidence_mode": evidence_mode,
        "quarters": [
            {
                "quarter": quarter_id,
                "quarter_receipt_sha256": quarters[quarter_id]["receipt_sha256"],
                "quarter_body_sha256": quarters[quarter_id]["body_sha256"],
                "amendment_state": quarters[quarter_id]["amendment_state"],
            }
            for quarter_id in FIXED_QUARTERS
        ],
        "samples": private_samples,
    }
    real_sample_replayed = is_real_sample
    controls = _admission_controls(real_sample_replayed=real_sample_replayed)
    state_boundary = {
        "evidence_mode": evidence_mode,
        "authorized_real_form4_rows": 0,
        "form4_specific_admission": {
            "passed": controls["passed"],
            "total": controls["total"],
            "all_passed": controls["all_passed"],
        },
        "candidate_selection_count": 0,
        "strategy_run_count": 0,
        "performance_present": False,
        "paper": {
            "authorized": False,
            "state": "all_cash",
            "backfilled_trades": 0,
            "positions": [],
        },
        "real_money_action_usd": 0,
        "today_action": "今天不下單",
    }
    result = {
        "schema_version": SCHEMA_VERSION,
        "protocol_sha256": binding["protocol_sha256"],
        "protocol_receipt_sha256": binding["protocol_receipt_sha256"],
        "frozen_at": binding["frozen_at"],
        "status": (
            "authorized_real_sample_replayed_form4_admission_3_of_16"
            if is_real_sample
            else "synthetic_fixture_feasibility_replayed_form4_admission_2_of_16"
        ),
        "fixed_quarters": list(FIXED_QUARTERS),
        "sample_count": len(samples),
        "admission_controls": controls,
        "attack_results": {
            "runtime_mutations_executed": False,
            "fixed_codes": list(ALL_ATTACK_CODES),
            "covered_by_fake_fixture_tests": True,
        },
        "stop_reasons": ["form4_admission_below_16_of_16"],
        "state_boundary": state_boundary,
        "private_manifest_sha256": (
            private_manifest_sha256
            if is_real_sample
            else _canonical_sha256(private_manifest)
        ),
    }
    expected_keys = set(
        binding["receipt"]["future_public_validation"]["exact_top_level_keys"]
    )
    if set(result) != expected_keys:
        _fail("form4_feasibility_result_boundary_breached", "public receipt schema drifted")
    if not math.isfinite(float(result["sample_count"])):
        _fail("form4_feasibility_result_boundary_breached", "sample count invalid")
    return result
