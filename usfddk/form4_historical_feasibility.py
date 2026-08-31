from __future__ import annotations

import hashlib
import io
import json
import re
import zipfile
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import unquote

from .form4_admission_feasibility import (
    REQUIRED_TABLES as ROUND42_REQUIRED_TABLES,
)
from .form4_admission_feasibility import (
    Form4AdmissionFeasibilityError,
    _load_protocol_binding,
    _metadata_contract,
    _physical_header_projection,
    _read_tsv,
)

SCHEMA_VERSION = "us_fddk.short_term_form4_historical_feasibility.v1"
PROTOCOL_PATH = Path("docs/SHORT_TERM_FORM4_HISTORICAL_FEASIBILITY_PROTOCOL.md")
PROTOCOL_RECEIPT_PATH = Path(
    "artifacts/short_term_form4_historical_feasibility_protocol_receipt.json"
)
EXPECTED_PROTOCOL_SHA256 = (
    "08dcc931d7a2ec4a4efef7868fcd5b770d05c8c8b3c04a4f21bda473bf6143b3"
)
EXPECTED_PROTOCOL_RECEIPT_SHA256 = (
    "257cee937e2ceb5a68b591b078be60d83468089fe92cefcab1122bfa7d450a88"
)
FIXED_QUARTERS = ("2006Q1", "2016Q3", "2026Q2")
ALLOWED_DOCUMENT_TYPES = frozenset({"3", "3/A", "4", "4/A", "5", "5/A"})
ALLOWED_RELATIONSHIP_TOKENS = frozenset(
    {"Director", "Officer", "TenPercentOwner"}
)
FALSE_SWAP_VALUES = frozenset({"0", "false"})
MIN_ACCESSION_NOTIONAL = Decimal("10000")
MIN_CLUSTER_NOTIONAL = Decimal("100000")
WINDOW_DAYS = 20
COOLDOWN_DAYS = 20
MIN_PRIMARY_CLUSTERS = 30

_ACCESSION = re.compile(r"^\d{10}-\d{2}-\d{6}$")
_CIK = re.compile(r"^\d{1,10}$")
_TRANSACTION_KEY = re.compile(r"^\d+$")
_QUARTER = re.compile(r"^(?P<year>20\d{2})Q(?P<quarter>[1-4])$")
_SEC_DATE = re.compile(
    r"^(?P<day>\d{2})-(?P<month>JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)-(?P<year>\d{4})$"
)

_FORBIDDEN_PUBLIC_KEYS = frozenset(
    {
        "accession",
        "accession_number",
        "accessions",
        "candidate",
        "candidate_list",
        "exact_filing_date",
        "exact_notional",
        "filing_date",
        "issuer_cik",
        "issuer_token",
        "owner_cik",
        "owner_name",
        "reporting_owner_cik",
        "reporting_owner_name",
        "security_token",
        "ticker",
    }
)


class Form4HistoricalFeasibilityError(RuntimeError):
    """Fail-closed historical-diagnostic error with a stable code."""

    def __init__(self, code: str, detail: str):
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}")


def _fail(code: str, detail: str) -> None:
    raise Form4HistoricalFeasibilityError(code, detail)


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


@dataclass(frozen=True, slots=True)
class AccessionPurchase:
    accession: str
    issuer_cik: str
    filing_date: date
    owner_ciks: tuple[str, ...]
    reported_purchase_dollars: Decimal
    eligible_transaction_rows: int


@dataclass(frozen=True, slots=True)
class ParsedQuarter:
    quarter: str
    filename: str
    body_sha256: str
    byte_count: int
    row_counts: Mapping[str, int]
    submission_type_counts: Mapping[str, int]
    form4_submission_count: int
    amendment_submission_count: int
    transaction_exclusion_counts: Mapping[str, int]
    eligible_transaction_rows: int
    purchase_accessions: tuple[AccessionPurchase, ...]


@dataclass(frozen=True, slots=True)
class HistoricalCluster:
    issuer_cik: str
    decision_date: date
    member_accessions: tuple[str, ...]
    owner_ciks: tuple[str, ...]
    reported_purchase_dollars: Decimal
    left_boundary_excluded: bool


@dataclass(frozen=True, slots=True)
class ClusterAudit:
    primary_clusters: tuple[HistoricalCluster, ...]
    left_boundary_clusters: tuple[HistoricalCluster, ...]
    raw_gate_crossings: int
    accessions_below_minimum: int
    cooldown_suppressed_filing_dates: int


def _load_historical_protocol(repository_root: Path) -> dict[str, Any]:
    root = repository_root.resolve()
    protocol_path = root / PROTOCOL_PATH
    receipt_path = root / PROTOCOL_RECEIPT_PATH
    if not protocol_path.is_file() or not receipt_path.is_file():
        _fail("form4_history_protocol_drift", "protocol or receipt is missing")
    if _sha256_file(protocol_path) != EXPECTED_PROTOCOL_SHA256:
        _fail("form4_history_protocol_drift", "protocol bytes drifted")
    try:
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        _fail("form4_history_protocol_drift", type(exc).__name__)
    if not isinstance(receipt, dict):
        _fail("form4_history_protocol_drift", "protocol receipt is not an object")
    claimed_sha = receipt.get("receipt_sha256")
    canonical = dict(receipt)
    canonical.pop("receipt_sha256", None)
    if (
        claimed_sha != EXPECTED_PROTOCOL_RECEIPT_SHA256
        or _canonical_sha256(canonical) != EXPECTED_PROTOCOL_RECEIPT_SHA256
        or receipt.get("status") != "frozen_before_event_count_readout"
        or receipt.get("protocol", {}).get("sha256") != EXPECTED_PROTOCOL_SHA256
        or receipt.get("trial_accounting", {}).get("combined_lower_bound_before")
        != 6295
        or receipt.get("trial_accounting", {}).get("minimum_increment_this_round")
        != 0
    ):
        _fail("form4_history_protocol_drift", "protocol receipt contract drifted")
    sources = receipt.get("fixed_offline_sources")
    if not isinstance(sources, list) or tuple(
        item.get("quarter") for item in sources if isinstance(item, dict)
    ) != FIXED_QUARTERS:
        _fail("form4_history_protocol_drift", "fixed quarter order drifted")
    event_contract = receipt.get("fixed_event_contract")
    expected_event_contract = {
        "document_type": "4",
        "transaction_form_type": "4",
        "transaction_code": "P",
        "acquired_disposed": "A",
        "equity_swap_false_values": ["0", "false"],
        "allowed_relationship_tokens": [
            "Director",
            "Officer",
            "TenPercentOwner",
        ],
        "window_calendar_days_inclusive": WINDOW_DAYS,
        "minimum_distinct_accessions": 2,
        "minimum_distinct_reporting_owner_ciks": 2,
        "minimum_purchase_dollars_per_accession": str(MIN_ACCESSION_NOTIONAL),
        "minimum_cluster_purchase_dollars": str(MIN_CLUSTER_NOTIONAL),
        "diagnostic_cooldown_calendar_days_inclusive": COOLDOWN_DAYS,
        "left_boundary_days_excluded": WINDOW_DAYS - 1,
    }
    if event_contract != expected_event_contract:
        _fail("form4_history_protocol_drift", "fixed event contract drifted")
    return receipt


def _quarter_parts(value: str) -> tuple[int, int]:
    match = _QUARTER.fullmatch(value)
    if match is None:
        _fail("form4_history_quarter_invalid", "quarter ID is invalid")
    return int(match.group("year")), int(match.group("quarter"))


def _quarter_start(value: str) -> date:
    year, quarter = _quarter_parts(value)
    return date(year, 1 + (quarter - 1) * 3, 1)


def _parse_sec_date(value: object, *, quarter: str) -> date:
    if not isinstance(value, str) or _SEC_DATE.fullmatch(value) is None:
        _fail("form4_history_row_invalid", "filing date is not canonical SEC format")
    try:
        parsed = datetime.strptime(value, "%d-%b-%Y").date()
    except ValueError:
        _fail("form4_history_row_invalid", "filing date is not a real date")
    if parsed.strftime("%d-%b-%Y").upper() != value:
        _fail("form4_history_row_invalid", "filing date canonicalization drifted")
    year, quarter_number = _quarter_parts(quarter)
    if parsed.year != year or (parsed.month - 1) // 3 + 1 != quarter_number:
        _fail("form4_history_quarter_invalid", "filing date is outside fixed quarter")
    return parsed


def _positive_decimal(value: object) -> Decimal | None:
    if not isinstance(value, str) or not value or value.strip() != value:
        return None
    try:
        parsed = Decimal(value)
    except InvalidOperation:
        return None
    if not parsed.is_finite() or parsed <= 0:
        return None
    return parsed


def _eligible_relationship(value: str) -> bool:
    tokens = tuple(item.strip() for item in value.split(","))
    return any(token in ALLOWED_RELATIONSHIP_TOKENS for token in tokens)


def _safe_zip(
    body: bytes,
    *,
    quarter: str,
    amendment_receipt: Mapping[str, Any],
) -> tuple[list[dict[str, str]], list[dict[str, str]], list[dict[str, str]]]:
    try:
        archive = zipfile.ZipFile(io.BytesIO(body))
    except zipfile.BadZipFile:
        _fail("form4_history_zip_invalid", "source is not a ZIP")
    with archive:
        infos = [info for info in archive.infolist() if not info.is_dir()]
        names = [info.filename for info in infos]
        if len(names) != len(set(names)) or any(
            PurePosixPath(name).is_absolute()
            or ".." in PurePosixPath(name).parts
            or "\\" in name
            or unquote(name) != name
            for name in names
        ):
            _fail("form4_history_zip_invalid", "ZIP member is unsafe or duplicated")
        total_size = sum(info.file_size for info in infos)
        compressed_size = sum(info.compress_size for info in infos)
        if (
            total_size <= 0
            or total_size > 1_000_000_000
            or compressed_size <= 0
            or total_size / compressed_size > 200
            or any(info.file_size > 500_000_000 for info in infos)
        ):
            _fail("form4_history_zip_invalid", "ZIP expansion limit exceeded")
        try:
            corrupt = archive.testzip()
        except (OSError, RuntimeError, zipfile.BadZipFile):
            _fail("form4_history_zip_invalid", "ZIP CRC replay failed")
        if corrupt is not None:
            _fail("form4_history_zip_invalid", "ZIP member CRC is invalid")
        metadata_candidates: list[dict[str, tuple[str, ...]]] = []
        for info in infos:
            if info.file_size > 2_000_000:
                continue
            try:
                value = json.loads(archive.read(info).decode("utf-8-sig"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                continue
            contract = _metadata_contract(value)
            if contract is not None:
                metadata_candidates.append(contract)
        if len(metadata_candidates) != 1:
            _fail(
                "form4_history_schema_invalid",
                "exactly one W3C metadata object is required",
            )
        metadata = metadata_candidates[0]
        if set(metadata) != set(ROUND42_REQUIRED_TABLES):
            _fail("form4_history_schema_invalid", "metadata table roles drifted")
        physical_headers: dict[str, tuple[str, ...]] = {}
        try:
            for table_name, anchors in ROUND42_REQUIRED_TABLES.items():
                if names.count(table_name) != 1:
                    _fail("form4_history_schema_invalid", f"{table_name} is missing")
                header = metadata[table_name]
                if any(anchor not in header for anchor in anchors):
                    _fail(
                        "form4_history_schema_invalid",
                        f"{table_name} required anchor is missing",
                    )
                physical_headers[table_name] = _physical_header_projection(
                    header,
                    table_name=table_name,
                    quarter_id=quarter,
                    amendment_receipt=amendment_receipt,
                )
            submissions = _read_tsv(
                archive.read("SUBMISSION.tsv"),
                table_name="SUBMISSION.tsv",
                expected_header=physical_headers["SUBMISSION.tsv"],
                quarter_id=quarter,
                amendment_receipt=amendment_receipt,
            )
            known_accessions = {
                row.get("ACCESSION_NUMBER", "") for row in submissions
            }
            owners = _read_tsv(
                archive.read("REPORTINGOWNER.tsv"),
                table_name="REPORTINGOWNER.tsv",
                expected_header=physical_headers["REPORTINGOWNER.tsv"],
                quarter_id=quarter,
                amendment_receipt=amendment_receipt,
                known_accessions=known_accessions,
            )
            transactions = _read_tsv(
                archive.read("NONDERIV_TRANS.tsv"),
                table_name="NONDERIV_TRANS.tsv",
                expected_header=physical_headers["NONDERIV_TRANS.tsv"],
                quarter_id=quarter,
                amendment_receipt=amendment_receipt,
                known_accessions=known_accessions,
            )
        except Form4AdmissionFeasibilityError as exc:
            _fail("form4_history_schema_invalid", exc.code)
    return submissions, owners, transactions


def _fixed_source(
    protocol_receipt: Mapping[str, Any], quarter: str
) -> Mapping[str, Any]:
    source = next(
        (
            item
            for item in protocol_receipt.get("fixed_offline_sources", ())
            if isinstance(item, Mapping) and item.get("quarter") == quarter
        ),
        None,
    )
    if source is None:
        _fail("form4_history_source_mismatch", "quarter is not fixed by protocol")
    return source


def parse_quarter_archive(
    body: bytes,
    *,
    quarter: str,
    repository_root: Path,
    filename: str | None = None,
) -> ParsedQuarter:
    """Parse one fixed SEC archive without persisting row-level identifiers."""

    protocol_receipt = _load_historical_protocol(repository_root)
    source = _fixed_source(protocol_receipt, quarter)
    expected_filename = source.get("filename")
    if filename is not None and filename != expected_filename:
        _fail("form4_history_source_mismatch", "archive filename drifted")
    if (
        len(body) != source.get("bytes")
        or _sha256_bytes(body) != source.get("sha256")
    ):
        _fail("form4_history_source_mismatch", "archive bytes drifted")
    try:
        round42_binding = _load_protocol_binding(repository_root)
    except Form4AdmissionFeasibilityError as exc:
        _fail("form4_history_protocol_drift", exc.code)
    submissions, owners, transactions = _safe_zip(
        body,
        quarter=quarter,
        amendment_receipt=round42_binding["amendment_receipt"],
    )

    submission_by_accession: dict[str, dict[str, Any]] = {}
    submission_type_counts: Counter[str] = Counter()
    for row in submissions:
        accession = row.get("ACCESSION_NUMBER", "")
        document_type = row.get("DOCUMENT_TYPE", "")
        issuer_cik = row.get("ISSUERCIK", "")
        if _ACCESSION.fullmatch(accession) is None:
            _fail("form4_history_row_invalid", "submission accession is invalid")
        if accession in submission_by_accession:
            _fail("form4_history_key_duplicate", "submission accession is duplicated")
        if document_type not in ALLOWED_DOCUMENT_TYPES:
            _fail("form4_history_row_invalid", "document type is outside Forms 3/4/5")
        if _CIK.fullmatch(issuer_cik) is None:
            _fail("form4_history_row_invalid", "issuer CIK is invalid")
        filing_date = _parse_sec_date(row.get("FILING_DATE"), quarter=quarter)
        submission_by_accession[accession] = {
            "document_type": document_type,
            "issuer_cik": issuer_cik,
            "filing_date": filing_date,
        }
        submission_type_counts[document_type] += 1

    eligible_owners: dict[str, set[str]] = defaultdict(set)
    owner_keys: set[tuple[str, str]] = set()
    for row in owners:
        accession = row.get("ACCESSION_NUMBER", "")
        owner_cik = row.get("RPTOWNERCIK", "")
        if accession not in submission_by_accession:
            _fail("form4_history_reference_invalid", "owner accession is unknown")
        if _CIK.fullmatch(owner_cik) is None:
            _fail("form4_history_row_invalid", "reporting-owner CIK is invalid")
        key = (accession, owner_cik)
        if key in owner_keys:
            _fail("form4_history_key_duplicate", "reporting-owner key is duplicated")
        owner_keys.add(key)
        if _eligible_relationship(row.get("RPTOWNER_RELATIONSHIP", "")):
            eligible_owners[accession].add(owner_cik)

    transaction_keys: set[tuple[str, str]] = set()
    exclusion_counts: Counter[str] = Counter()
    notional_by_accession: dict[str, Decimal] = defaultdict(Decimal)
    row_count_by_accession: Counter[str] = Counter()
    eligible_transaction_rows = 0
    for row in transactions:
        accession = row.get("ACCESSION_NUMBER", "")
        transaction_key = row.get("NONDERIV_TRANS_SK", "")
        if accession not in submission_by_accession:
            _fail("form4_history_reference_invalid", "transaction accession is unknown")
        if _TRANSACTION_KEY.fullmatch(transaction_key) is None:
            _fail("form4_history_row_invalid", "transaction key is invalid")
        key = (accession, transaction_key)
        if key in transaction_keys:
            _fail("form4_history_key_duplicate", "transaction key is duplicated")
        transaction_keys.add(key)
        submission = submission_by_accession[accession]
        if submission["document_type"] != "4":
            exclusion_counts["non_primary_form4_submission"] += 1
            continue
        if row.get("TRANS_FORM_TYPE") != "4":
            exclusion_counts["wrong_transaction_form"] += 1
            continue
        if row.get("TRANS_CODE") != "P":
            exclusion_counts["not_purchase_code"] += 1
            continue
        if row.get("TRANS_ACQUIRED_DISP_CD") != "A":
            exclusion_counts["not_acquired"] += 1
            continue
        if row.get("EQUITY_SWAP_INVOLVED", "").casefold() not in FALSE_SWAP_VALUES:
            exclusion_counts["swap_not_proven_false"] += 1
            continue
        shares = _positive_decimal(row.get("TRANS_SHARES"))
        if shares is None:
            exclusion_counts["shares_not_positive_finite"] += 1
            continue
        price = _positive_decimal(row.get("TRANS_PRICEPERSHARE"))
        if price is None:
            exclusion_counts["price_not_positive_finite"] += 1
            continue
        if not eligible_owners.get(accession):
            exclusion_counts["relationship_not_eligible"] += 1
            continue
        notional_by_accession[accession] += shares * price
        row_count_by_accession[accession] += 1
        eligible_transaction_rows += 1

    purchase_accessions: list[AccessionPurchase] = []
    for accession, notional in notional_by_accession.items():
        submission = submission_by_accession[accession]
        purchase_accessions.append(
            AccessionPurchase(
                accession=accession,
                issuer_cik=str(submission["issuer_cik"]),
                filing_date=submission["filing_date"],
                owner_ciks=tuple(sorted(eligible_owners[accession])),
                reported_purchase_dollars=notional,
                eligible_transaction_rows=row_count_by_accession[accession],
            )
        )
    purchase_accessions.sort(
        key=lambda item: (item.filing_date, item.accession)
    )
    return ParsedQuarter(
        quarter=quarter,
        filename=str(expected_filename),
        body_sha256=_sha256_bytes(body),
        byte_count=len(body),
        row_counts={
            "submission": len(submissions),
            "reporting_owner": len(owners),
            "nonderivative_transaction": len(transactions),
        },
        submission_type_counts=dict(sorted(submission_type_counts.items())),
        form4_submission_count=submission_type_counts["4"],
        amendment_submission_count=submission_type_counts["4/A"],
        transaction_exclusion_counts=dict(sorted(exclusion_counts.items())),
        eligible_transaction_rows=eligible_transaction_rows,
        purchase_accessions=tuple(purchase_accessions),
    )


def build_historical_clusters(parsed: ParsedQuarter) -> ClusterAudit:
    """Apply the frozen diagnostic state machine to one isolated quarter."""

    qualifying = [
        item
        for item in parsed.purchase_accessions
        if item.reported_purchase_dollars >= MIN_ACCESSION_NOTIONAL
    ]
    by_issuer: dict[str, list[AccessionPurchase]] = defaultdict(list)
    for item in qualifying:
        by_issuer[item.issuer_cik].append(item)
    valid_from = _quarter_start(parsed.quarter) + timedelta(days=WINDOW_DAYS - 1)
    primary: list[HistoricalCluster] = []
    left_boundary: list[HistoricalCluster] = []
    raw_crossings = 0
    cooldown_suppressed_dates = 0
    for issuer_cik in sorted(by_issuer):
        by_date: dict[date, list[AccessionPurchase]] = defaultdict(list)
        for item in by_issuer[issuer_cik]:
            by_date[item.filing_date].append(item)
        pending: list[AccessionPurchase] = []
        cooldown_through: date | None = None
        for filing_date in sorted(by_date):
            pending.extend(
                sorted(by_date[filing_date], key=lambda item: item.accession)
            )
            window_start = filing_date - timedelta(days=WINDOW_DAYS - 1)
            pending = [item for item in pending if item.filing_date >= window_start]
            if cooldown_through is not None and filing_date <= cooldown_through:
                cooldown_suppressed_dates += 1
                continue
            owner_ciks = tuple(
                sorted({owner for item in pending for owner in item.owner_ciks})
            )
            total_notional = sum(
                (item.reported_purchase_dollars for item in pending), Decimal(0)
            )
            if (
                len(pending) < 2
                or len(owner_ciks) < 2
                or total_notional < MIN_CLUSTER_NOTIONAL
            ):
                continue
            raw_crossings += 1
            cluster = HistoricalCluster(
                issuer_cik=issuer_cik,
                decision_date=filing_date,
                member_accessions=tuple(item.accession for item in pending),
                owner_ciks=owner_ciks,
                reported_purchase_dollars=total_notional,
                left_boundary_excluded=filing_date < valid_from,
            )
            if cluster.left_boundary_excluded:
                left_boundary.append(cluster)
            else:
                primary.append(cluster)
            pending = []
            cooldown_through = filing_date + timedelta(days=COOLDOWN_DAYS)
    primary.sort(key=lambda item: (item.decision_date, item.issuer_cik))
    left_boundary.sort(key=lambda item: (item.decision_date, item.issuer_cik))
    return ClusterAudit(
        primary_clusters=tuple(primary),
        left_boundary_clusters=tuple(left_boundary),
        raw_gate_crossings=raw_crossings,
        accessions_below_minimum=(
            len(parsed.purchase_accessions) - len(qualifying)
        ),
        cooldown_suppressed_filing_dates=cooldown_suppressed_dates,
    )


def _count_bucket(value: int) -> str:
    if value == 2:
        return "2"
    if value == 3:
        return "3"
    return "4_plus"


def _notional_bucket(value: Decimal) -> str:
    if value < Decimal("250000"):
        return "100k_to_250k"
    if value < Decimal("1000000"):
        return "250k_to_1m"
    return "1m_plus"


def _cluster_buckets(
    clusters: Sequence[HistoricalCluster],
) -> dict[str, dict[str, int]]:
    owners: Counter[str] = Counter()
    accessions: Counter[str] = Counter()
    notionals: Counter[str] = Counter()
    for cluster in clusters:
        owners[_count_bucket(len(cluster.owner_ciks))] += 1
        accessions[_count_bucket(len(cluster.member_accessions))] += 1
        notionals[_notional_bucket(cluster.reported_purchase_dollars)] += 1
    return {
        "distinct_owner_count": dict(sorted(owners.items())),
        "distinct_accession_count": dict(sorted(accessions.items())),
        "reported_notional": dict(sorted(notionals.items())),
    }


def _privacy_scan(value: object, *, path: str = "root") -> None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            key_text = str(key)
            if key_text.casefold() in _FORBIDDEN_PUBLIC_KEYS:
                _fail(
                    "form4_history_privacy_boundary",
                    f"forbidden public key at {path}.{key_text}",
                )
            _privacy_scan(item, path=f"{path}.{key_text}")
        return
    if isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            _privacy_scan(item, path=f"{path}[{index}]")
        return
    if isinstance(value, str) and _ACCESSION.fullmatch(value):
        _fail(
            "form4_history_privacy_boundary",
            f"accession-like value at {path}",
        )


def audit_historical_feasibility(
    archive_paths: Mapping[str, Path],
    *,
    repository_root: Path,
) -> dict[str, Any]:
    """Build an aggregate-only diagnostic receipt from the three fixed archives."""

    protocol_receipt = _load_historical_protocol(repository_root)
    if tuple(sorted(archive_paths)) != tuple(sorted(FIXED_QUARTERS)):
        _fail("form4_history_source_mismatch", "archive quarter set drifted")
    parsed_quarters: list[ParsedQuarter] = []
    audits: list[ClusterAudit] = []
    quarter_summaries: list[dict[str, Any]] = []
    for quarter in FIXED_QUARTERS:
        path = Path(archive_paths[quarter])
        if not path.is_file() or path.is_symlink():
            _fail("form4_history_source_mismatch", "archive path is not a regular file")
        source = _fixed_source(protocol_receipt, quarter)
        parsed = parse_quarter_archive(
            path.read_bytes(),
            quarter=quarter,
            repository_root=repository_root,
            filename=path.name,
        )
        audit = build_historical_clusters(parsed)
        parsed_quarters.append(parsed)
        audits.append(audit)
        quarter_summaries.append(
            {
                "quarter": quarter,
                "source_filename": source["filename"],
                "source_bytes": parsed.byte_count,
                "source_sha256": parsed.body_sha256,
                "row_counts": dict(parsed.row_counts),
                "submission_type_counts": dict(parsed.submission_type_counts),
                "form4_submission_count": parsed.form4_submission_count,
                "amendment_submission_count": parsed.amendment_submission_count,
                "transaction_exclusion_counts": dict(
                    parsed.transaction_exclusion_counts
                ),
                "eligible_transaction_rows": parsed.eligible_transaction_rows,
                "eligible_purchase_accession_count": len(
                    parsed.purchase_accessions
                ),
                "accessions_below_minimum": audit.accessions_below_minimum,
                "raw_gate_crossings": audit.raw_gate_crossings,
                "left_boundary_excluded": len(audit.left_boundary_clusters),
                "primary_cluster_count": len(audit.primary_clusters),
                "cooldown_suppressed_filing_date_count": (
                    audit.cooldown_suppressed_filing_dates
                ),
                "primary_cluster_buckets": _cluster_buckets(
                    audit.primary_clusters
                ),
            }
        )
    total_clusters = sum(len(audit.primary_clusters) for audit in audits)
    event_rate_passed = total_clusters >= MIN_PRIMARY_CLUSTERS
    diagnostic_status = (
        "historical_backtest_preregistration_warranted"
        if event_rate_passed
        else "insufficient_event_rate_no_historical_backtest"
    )
    result: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "research_round": 49,
        "status": diagnostic_status,
        "validation_scope": "historical_event_rate_only_no_market_returns",
        "protocol_sha256": EXPECTED_PROTOCOL_SHA256,
        "protocol_receipt_sha256": EXPECTED_PROTOCOL_RECEIPT_SHA256,
        "fixed_quarters": list(FIXED_QUARTERS),
        "quarter_results": quarter_summaries,
        "aggregate_event_gate": {
            "minimum_primary_clusters": MIN_PRIMARY_CLUSTERS,
            "observed_primary_clusters": total_clusters,
            "passed": event_rate_passed,
            "parameters_reselected_after_result": False,
        },
        "implementation_validation": {
            "required_test": "uv run pytest -q tests/test_form4_historical_feasibility.py",
            "test_execution_claimed_in_this_data_receipt": False,
            "reason": "deterministic_data_receipt_cannot_attest_external_test_process",
        },
        "privacy": {
            "identifier_detail_included": False,
            "raw_rows_persisted": False,
            "low_entropy_identifier_hashes_included": False,
        },
        "limitations": [
            "three_noncontiguous_schema_anchor_quarters_not_twenty_year_coverage",
            "quarterly_as_filed_data_not_contemporaneous_intraday_known_at",
            "reporting_owner_cik_count_not_verified_independent_capital_group",
            "no_point_in_time_security_master_delisting_or_market_execution_data",
            "no_return_baseline_cost_statistical_or_performance_readout",
            "cannot_promote_or_modify_round46_forward_only_family",
        ],
        "state_boundary": {
            "sec_requests_this_round": 0,
            "historical_replay_only": True,
            "strategy_runs": 0,
            "performance_present": False,
            "candidate_selection_count": 0,
            "promotion_authorized": False,
            "paper_authorized": False,
            "paper_positions": [],
            "backfilled_trades": 0,
            "website_publication_authorized": False,
            "real_money_action_usd": 0,
            "today_action": "今天不下單",
        },
    }
    _privacy_scan(result)
    result["receipt_sha256"] = _canonical_sha256(result)
    return result


def write_validation_receipt(
    receipt: Mapping[str, Any],
    *,
    output_path: Path,
    repository_root: Path,
) -> None:
    root = repository_root.resolve()
    expected_parent = (root / "artifacts").resolve()
    resolved = output_path.resolve()
    if resolved.parent != expected_parent or resolved.name != (
        "short_term_form4_historical_feasibility_validation.json"
    ):
        _fail("form4_history_result_boundary", "output path is not the fixed log path")
    _privacy_scan(receipt)
    rendered = json.dumps(
        dict(receipt),
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
        allow_nan=False,
    ) + "\n"
    resolved.write_text(rendered, encoding="utf-8")


__all__ = [
    "AccessionPurchase",
    "ClusterAudit",
    "FIXED_QUARTERS",
    "Form4HistoricalFeasibilityError",
    "HistoricalCluster",
    "ParsedQuarter",
    "audit_historical_feasibility",
    "build_historical_clusters",
    "parse_quarter_archive",
    "write_validation_receipt",
]
