from __future__ import annotations

import csv
import hashlib
import io
import json
import re
import zipfile
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from decimal import Decimal
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import unquote

from .form4_admission_feasibility import (
    REQUIRED_TABLES as ROUND42_REQUIRED_TABLES,
)
from .form4_admission_feasibility import (
    _metadata_contract,
)
from .form4_historical_feasibility import (
    _CIK,
    ALLOWED_DOCUMENT_TYPES,
    FALSE_SWAP_VALUES,
    _eligible_relationship,
    _load_protocol_binding,
    _parse_sec_date,
    _positive_decimal,
)
from .universe import load_stock_watchlist

SCHEMA_VERSION = "usfddk.short_term_form4_full_coverage.v1"
PROTOCOL_PATH = Path("docs/SHORT_TERM_FORM4_FULL_COVERAGE_PROTOCOL.md")
PROTOCOL_RECEIPT_PATH = Path(
    "artifacts/short_term_form4_full_coverage_protocol_receipt.json"
)
MANIFEST_PATH = Path("artifacts/short_term_form4_full_coverage_source_manifest.json")
VALIDATION_PATH = Path("artifacts/short_term_form4_full_coverage_validation.json")
EXPECTED_PROTOCOL_SHA256 = (
    "faefdba7bd890e9d47be115f09e8aee7d9b6a956e28a8a44ce7be415d6ea5fd7"
)
EXPECTED_PROTOCOL_RECEIPT_SHA256 = (
    "32eabfd42688eac10a73447ca53e7e886710cf9757e90fea49be9955926ff553"
)
SEC_URL_TEMPLATE = (
    "https://www.sec.gov/files/structureddata/data/insider-transactions-data-sets/"
    "{yyyy}q{q}_form345.zip"
)
QUARTERS = tuple(
    f"{year}Q{quarter}"
    for year in range(2006, 2027)
    for quarter in range(1, 5)
    if not (year == 2026 and quarter > 2)
)
QUARTER_FILENAMES = {quarter: f"{quarter.lower()}_form345.zip" for quarter in QUARTERS}
WATCHLIST_PATH = Path("usfddk/resources/us_large_cap_watchlist_v1.csv")
WATCHLIST_SHA256 = (
    "b6002e4e151bd298884f8cdd6272b5cbfde8aedca47cb58b92830d4d92028014"
)
WATCHLIST_COUNT = 30
SEC_MAPPING_URL = "https://www.sec.gov/files/company_tickers.json"
SEC_MAPPING_BYTES = 795627
SEC_MAPPING_SHA256 = (
    "6dd9c4363c5a95d43f4d8e8f8279f9ae6538d10d295bbdeebe5a433ec954bf6d"
)
ANCHOR_HASHES = {
    "2006Q1": (17306804, "62becdadbe5eaff68f03edefe2ba2357c8bb498a1f825b697003e087cf98e6ce"),
    "2016Q3": (8704557, "5a25d3c6cb874875904b2be0059bb4784e4da28b315af30b15568fd250bd0dde"),
    "2026Q2": (11498860, "11f1b2bbbdcbe6347a34437c02d04202fda0eca1dbb023726e4b56504b802e27"),
}
GLOBAL_TRIAL_LOWER_BOUND = 6290
_CLEAN_SYMBOL = re.compile(r"^[A-Z0-9-]+$")


class Form4FullCoverageError(RuntimeError):
    """Fail-closed full-quarter Form 4 coverage error."""

    def __init__(self, code: str, detail: str):
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}")


def _fail(code: str, detail: str) -> None:
    raise Form4FullCoverageError(code, detail)


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_file(path: Path) -> str:
    try:
        return _sha256_bytes(path.read_bytes())
    except OSError as exc:
        _fail("form4_full_coverage_source_missing", f"{path}: {type(exc).__name__}")


def _canonical_sha256(value: object) -> str:
    return _sha256_bytes(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    )


def quarter_list() -> tuple[str, ...]:
    return QUARTERS


def _load_protocol(root: Path) -> dict[str, Any]:
    protocol = root / PROTOCOL_PATH
    receipt_path = root / PROTOCOL_RECEIPT_PATH
    if _sha256_file(protocol) != EXPECTED_PROTOCOL_SHA256:
        _fail("form4_full_coverage_protocol_drift", "protocol bytes drifted")
    try:
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        _fail("form4_full_coverage_protocol_drift", type(exc).__name__)
    if not isinstance(receipt, dict):
        _fail("form4_full_coverage_protocol_drift", "protocol receipt is not an object")
    claimed = receipt.get("receipt_sha256")
    unsigned = dict(receipt)
    unsigned.pop("receipt_sha256", None)
    if claimed != EXPECTED_PROTOCOL_RECEIPT_SHA256 or _canonical_sha256(unsigned) != claimed:
        _fail("form4_full_coverage_protocol_drift", "protocol receipt hash drifted")
    expected = {
        "schema_version": 1,
        "status": "preregistered_full_quarter_form4_coverage_only",
        "research_round": 52,
        "quarter_count": len(QUARTERS),
        "quarter_start": QUARTERS[0],
        "quarter_end": QUARTERS[-1],
        "url_template": SEC_URL_TEMPLATE,
        "watchlist_count": WATCHLIST_COUNT,
        "watchlist_sha256": WATCHLIST_SHA256,
        "mapping_modes": ["current_cik_exact", "as_filed_trading_symbol_exact"],
        "current_global_trial_lower_bound": GLOBAL_TRIAL_LOWER_BOUND,
        "performance_authorized": False,
        "paper_authorized": False,
        "real_money_authorized": False,
        "today_action": "今天不下單",
    }
    if any(receipt.get(key) != value for key, value in expected.items()):
        _fail("form4_full_coverage_protocol_drift", "fixed protocol field drifted")
    return receipt


def _normalize_symbol(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    cleaned = value.strip().upper().replace(".", "-").replace("/", "-")
    if cleaned in {"", "N/A", "NONE", "NA"} or _CLEAN_SYMBOL.fullmatch(cleaned) is None:
        return None
    return cleaned


def _load_sec_mapping(path: Path) -> dict[str, frozenset[str]]:
    if not path.is_file() or path.is_symlink():
        _fail("form4_full_coverage_mapping_invalid", "mapping is not a regular file")
    body = path.read_bytes()
    if len(body) != SEC_MAPPING_BYTES or _sha256_bytes(body) != SEC_MAPPING_SHA256:
        _fail("form4_full_coverage_mapping_invalid", "SEC mapping bytes drifted")
    try:
        payload = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        _fail("form4_full_coverage_mapping_invalid", type(exc).__name__)
    if not isinstance(payload, dict) or not payload:
        _fail("form4_full_coverage_mapping_invalid", "mapping is not an object")
    by_cik: dict[str, set[str]] = defaultdict(set)
    seen_symbols: set[str] = set()
    for item in payload.values():
        if not isinstance(item, Mapping):
            _fail("form4_full_coverage_mapping_invalid", "mapping row is not an object")
        ticker = _normalize_symbol(item.get("ticker"))
        cik_value = item.get("cik_str")
        if isinstance(cik_value, bool) or not isinstance(cik_value, int) or cik_value <= 0:
            _fail("form4_full_coverage_mapping_invalid", "mapping row is invalid")
        cik = f"{cik_value:010d}"
        if _CIK.fullmatch(cik) is None or (ticker is not None and ticker in seen_symbols):
            _fail("form4_full_coverage_mapping_invalid", "CIK or ticker is invalid/duplicated")
        if ticker is not None:
            by_cik[cik].add(ticker)
            seen_symbols.add(ticker)
        else:
            by_cik.setdefault(cik, set())
    return {cik: frozenset(symbols) for cik, symbols in by_cik.items()}


def _load_manifest(root: Path, manifest_path: Path) -> dict[str, Any]:
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        _fail("form4_full_coverage_manifest_invalid", type(exc).__name__)
    if not isinstance(manifest, dict):
        _fail("form4_full_coverage_manifest_invalid", "manifest is not an object")
    claimed = manifest.get("manifest_sha256")
    unsigned = dict(manifest)
    unsigned.pop("manifest_sha256", None)
    if not isinstance(claimed, str) or _canonical_sha256(unsigned) != claimed:
        _fail("form4_full_coverage_manifest_invalid", "manifest self-hash drifted")
    if manifest.get("schema_version") != 1 or manifest.get("status") != "fetched_without_row_readout":
        _fail("form4_full_coverage_manifest_invalid", "manifest status drifted")
    if manifest.get("protocol_sha256") != EXPECTED_PROTOCOL_SHA256:
        _fail("form4_full_coverage_manifest_invalid", "manifest protocol binding drifted")
    rows = manifest.get("quarters")
    if not isinstance(rows, list) or [row.get("quarter") for row in rows] != list(QUARTERS):
        _fail("form4_full_coverage_manifest_invalid", "manifest quarter order drifted")
    if len(rows) != len(QUARTERS):
        _fail("form4_full_coverage_manifest_invalid", "manifest quarter count drifted")
    for row, quarter in zip(rows, QUARTERS, strict=True):
        if not isinstance(row, dict) or set(row) != {"quarter", "filename", "url", "bytes", "sha256"}:
            _fail("form4_full_coverage_manifest_invalid", "manifest row fields drifted")
        year, number = quarter[:4], quarter[-1]
        expected_url = SEC_URL_TEMPLATE.format(yyyy=year, q=number)
        if row["quarter"] != quarter or row["filename"] != QUARTER_FILENAMES[quarter] or row["url"] != expected_url:
            _fail("form4_full_coverage_manifest_invalid", "manifest source URL drifted")
        if not isinstance(row["bytes"], int) or row["bytes"] <= 0 or not isinstance(row["sha256"], str) or len(row["sha256"]) != 64:
            _fail("form4_full_coverage_manifest_invalid", "manifest source hash is invalid")
    return manifest


def _validate_sources(*, staging_dir: Path, manifest: dict[str, Any]) -> None:
    rows = manifest["quarters"]
    for row in rows:
        path = staging_dir / row["filename"]
        if not path.is_file() or path.is_symlink():
            _fail("form4_full_coverage_source_missing", f"missing {row['quarter']}")
        if path.stat().st_size != row["bytes"] or _sha256_file(path) != row["sha256"]:
            _fail("form4_full_coverage_source_hash_drift", f"hash drifted {row['quarter']}")
    for quarter, (expected_bytes, expected_sha) in ANCHOR_HASHES.items():
        row = next(item for item in rows if item["quarter"] == quarter)
        if row["bytes"] != expected_bytes or row["sha256"] != expected_sha:
            _fail("form4_full_coverage_anchor_drift", f"anchor drifted {quarter}")


def _project_full_coverage_header(
    metadata_header: tuple[str, ...],
    *,
    table_name: str,
    amendment_receipt: Mapping[str, Any],
) -> tuple[str, ...]:
    """Project SEC metadata headers without using the fixed-quarter profiles."""

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
            _fail("form4_full_coverage_schema_invalid", "submission omission policy is invalid")
        try:
            left_index = projected.index(str(left))
            right_index = projected.index(str(right))
        except ValueError:
            _fail("form4_full_coverage_schema_invalid", "submission anchors are missing")
        if (
            right_index <= left_index
            or projected[left_index + 1 : right_index] != contacts
            or any(projected.count(item) != 1 for item in contacts)
        ):
            _fail("form4_full_coverage_schema_invalid", "submission omission is not contiguous")
        del projected[left_index + 1 : right_index]
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
            _fail("form4_full_coverage_schema_invalid", f"{table_name} alias is missing")
        try:
            index = int(alias.get("one_based_position", 0)) - 1
        except (TypeError, ValueError):
            _fail("form4_full_coverage_schema_invalid", f"{table_name} alias position is invalid")
        metadata_name = alias.get("metadata_name")
        physical_name = alias.get("physical_name")
        if (
            index < 0
            or len(projected) != alias.get("metadata_columns")
            or index >= len(projected)
            or projected[index] != metadata_name
            or projected.count(str(metadata_name)) != 1
        ):
            _fail("form4_full_coverage_schema_invalid", f"{table_name} alias metadata drifted")
        projected[index] = str(physical_name)
        if len(projected) != alias.get("physical_columns"):
            _fail("form4_full_coverage_schema_invalid", f"{table_name} alias width drifted")
    else:
        exact_roles = policy.get("exact_match_roles", {})
        if exact_roles.get(table_name) != len(projected):
            _fail("form4_full_coverage_schema_invalid", f"{table_name} metadata width drifted")
    if any(anchor not in projected for anchor in ROUND42_REQUIRED_TABLES[table_name]):
        _fail("form4_full_coverage_schema_invalid", f"{table_name} required anchor is missing")
    return tuple(projected)


def _read_full_coverage_rows(
    raw: bytes,
    *,
    table_name: str,
    expected_header: tuple[str, ...],
    known_accessions: set[str] | None = None,
) -> list[dict[str, str]]:
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        _fail("form4_full_coverage_schema_invalid", f"{table_name} is not UTF-8")
    reader = csv.DictReader(io.StringIO(text, newline=""), delimiter="\t")
    header = tuple(reader.fieldnames or ())
    if header != expected_header or len(set(header)) != len(header):
        _fail("form4_full_coverage_schema_invalid", f"{table_name} physical header drifted")
    rows: list[dict[str, str]] = []
    try:
        for row in reader:
            if None in row or any(value is None for value in row.values()):
                _fail("form4_full_coverage_schema_invalid", f"{table_name} row width drifted")
            item = {str(key): str(value) for key, value in row.items()}
            accession = item.get("ACCESSION_NUMBER", "")
            if known_accessions is not None and accession and accession not in known_accessions:
                _fail("form4_full_coverage_reference_invalid", f"{table_name} accession reference drifted")
            rows.append(item)
    except csv.Error:
        _fail("form4_full_coverage_schema_invalid", f"{table_name} is not valid TSV")
    return rows


def _safe_full_coverage_zip(
    body: bytes,
    *,
    quarter: str,
    amendment_receipt: Mapping[str, Any],
) -> tuple[list[dict[str, str]], list[dict[str, str]], list[dict[str, str]]]:
    """Validate and read one full-coverage ZIP with quarter-variable headers."""

    try:
        archive = zipfile.ZipFile(io.BytesIO(body))
    except zipfile.BadZipFile:
        _fail("form4_full_coverage_zip_invalid", "source is not a ZIP")
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
            _fail("form4_full_coverage_zip_invalid", "ZIP member is unsafe or duplicated")
        total_size = sum(info.file_size for info in infos)
        compressed_size = sum(info.compress_size for info in infos)
        if (
            total_size <= 0
            or total_size > 1_000_000_000
            or compressed_size <= 0
            or total_size / compressed_size > 200
            or any(info.file_size > 500_000_000 for info in infos)
        ):
            _fail("form4_full_coverage_zip_invalid", "ZIP expansion limit exceeded")
        try:
            corrupt = archive.testzip()
        except (OSError, RuntimeError, zipfile.BadZipFile):
            _fail("form4_full_coverage_zip_invalid", "ZIP CRC replay failed")
        if corrupt is not None:
            _fail("form4_full_coverage_zip_invalid", "ZIP member CRC is invalid")
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
            _fail("form4_full_coverage_schema_invalid", "exactly one metadata object is required")
        metadata = metadata_candidates[0]
        if set(metadata) != set(ROUND42_REQUIRED_TABLES):
            _fail("form4_full_coverage_schema_invalid", "metadata table roles drifted")
        physical_headers: dict[str, tuple[str, ...]] = {}
        for table_name in ROUND42_REQUIRED_TABLES:
            if names.count(table_name) != 1:
                _fail("form4_full_coverage_schema_invalid", f"{table_name} is missing")
            physical_headers[table_name] = _project_full_coverage_header(
                metadata[table_name],
                table_name=table_name,
                amendment_receipt=amendment_receipt,
            )
            try:
                raw_header = tuple(
                    archive.read(table_name).decode("utf-8-sig").splitlines()[0].split("\t")
                )
            except (IndexError, UnicodeDecodeError):
                _fail("form4_full_coverage_schema_invalid", f"{table_name} has no header")
            if raw_header != physical_headers[table_name]:
                _fail("form4_full_coverage_schema_invalid", f"{table_name} physical header drifted")
        submissions = _read_full_coverage_rows(
            archive.read("SUBMISSION.tsv"),
            table_name="SUBMISSION.tsv",
            expected_header=physical_headers["SUBMISSION.tsv"],
        )
        known_accessions = {row.get("ACCESSION_NUMBER", "") for row in submissions}
        owners = _read_full_coverage_rows(
            archive.read("REPORTINGOWNER.tsv"),
            table_name="REPORTINGOWNER.tsv",
            expected_header=physical_headers["REPORTINGOWNER.tsv"],
            known_accessions=known_accessions,
        )
        transactions = _read_full_coverage_rows(
            archive.read("NONDERIV_TRANS.tsv"),
            table_name="NONDERIV_TRANS.tsv",
            expected_header=physical_headers["NONDERIV_TRANS.tsv"],
            known_accessions=known_accessions,
        )
    return submissions, owners, transactions


def _parse_purchase_aggregates(
    body: bytes,
    *,
    quarter: str,
    amendment_receipt: Mapping[str, Any],
) -> dict[str, Any]:
    submissions, owners, transactions = _safe_full_coverage_zip(
        body,
        quarter=quarter,
        amendment_receipt=amendment_receipt,
    )
    by_accession: dict[str, dict[str, Any]] = {}
    submission_types: Counter[str] = Counter()
    for row in submissions:
        accession = row.get("ACCESSION_NUMBER", "")
        document_type = row.get("DOCUMENT_TYPE", "")
        issuer_cik = row.get("ISSUERCIK", "")
        if accession in by_accession or not _CIK.fullmatch(issuer_cik):
            _fail("form4_full_coverage_row_invalid", "submission key or CIK invalid")
        if document_type not in ALLOWED_DOCUMENT_TYPES:
            _fail("form4_full_coverage_row_invalid", "document type invalid")
        by_accession[accession] = {
            "document_type": document_type,
            "issuer_cik": f"{int(issuer_cik):010d}",
            "issuer_symbol": _normalize_symbol(row.get("ISSUERTRADINGSYMBOL")),
            "filing_date": _parse_sec_date(row.get("FILING_DATE"), quarter=quarter),
        }
        submission_types[document_type] += 1
    eligible_owners: dict[str, set[str]] = defaultdict(set)
    for row in owners:
        accession = row.get("ACCESSION_NUMBER", "")
        owner_cik = row.get("RPTOWNERCIK", "")
        if accession not in by_accession or not _CIK.fullmatch(owner_cik):
            _fail("form4_full_coverage_reference_invalid", "owner reference invalid")
        if _eligible_relationship(row.get("RPTOWNER_RELATIONSHIP", "")):
            eligible_owners[accession].add(f"{int(owner_cik):010d}")
    exclusion_counts: Counter[str] = Counter()
    notional_by_accession: dict[str, Decimal] = defaultdict(Decimal)
    eligible_rows = 0
    for row in transactions:
        accession = row.get("ACCESSION_NUMBER", "")
        if accession not in by_accession:
            _fail("form4_full_coverage_reference_invalid", "transaction reference invalid")
        submission = by_accession[accession]
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
        price = _positive_decimal(row.get("TRANS_PRICEPERSHARE"))
        if shares is None or price is None:
            exclusion_counts["shares_or_price_not_positive_finite"] += 1
            continue
        if not eligible_owners.get(accession):
            exclusion_counts["relationship_not_eligible"] += 1
            continue
        notional_by_accession[accession] += shares * price
        eligible_rows += 1
    purchases = [
        {
            "issuer_cik": by_accession[accession]["issuer_cik"],
            "issuer_symbol": by_accession[accession]["issuer_symbol"],
            "filing_date": by_accession[accession]["filing_date"].isoformat(),
            "notional": notional,
        }
        for accession, notional in notional_by_accession.items()
    ]
    return {
        "form4_submission_count": submission_types["4"],
        "amendment_submission_count": submission_types["4/A"],
        "submission_count": len(submissions),
        "eligible_transaction_rows": eligible_rows,
        "eligible_purchase_accession_count": len(purchases),
        "transaction_exclusion_counts": dict(sorted(exclusion_counts.items())),
        "purchases": purchases,
    }


def _aggregate_mapping(
    purchases: Sequence[Mapping[str, Any]],
    *,
    cik_to_symbols: Mapping[str, frozenset[str]],
    watchlist_symbols: set[str],
) -> dict[str, int]:
    cik_mapped = [
        item
        for item in purchases
        if cik_to_symbols.get(item["issuer_cik"], frozenset()) & watchlist_symbols
    ]
    symbol_mapped = [item for item in purchases if item.get("issuer_symbol") in watchlist_symbols]
    union = {id(item): item for item in [*cik_mapped, *symbol_mapped]}
    return {
        "current_cik_exact_purchase_accession_count": len(cik_mapped),
        "current_cik_exact_issuer_count": len({item["issuer_cik"] for item in cik_mapped}),
        "as_filed_symbol_exact_purchase_accession_count": len(symbol_mapped),
        "as_filed_symbol_exact_issuer_count": len({item.get("issuer_symbol") for item in symbol_mapped}),
        "union_mapped_purchase_accession_count": len(union),
        "union_mapped_issuer_count": len(
            {item["issuer_cik"] for item in union.values()}
        ),
    }


def _privacy_scan(value: object, *, path: str = "root") -> None:
    forbidden = {
        "accession",
        "cik",
        "issuer_cik",
        "issuer_name",
        "owner",
        "owner_cik",
        "owner_name",
        "symbol",
        "ticker",
    }
    if isinstance(value, Mapping):
        for key, item in value.items():
            if str(key).casefold() in forbidden:
                _fail("form4_full_coverage_privacy_boundary", f"forbidden key at {path}")
            _privacy_scan(item, path=f"{path}.{key}")
    elif isinstance(value, Sequence) and not isinstance(value, str | bytes):
        for index, item in enumerate(value):
            _privacy_scan(item, path=f"{path}[{index}]")


def audit_full_coverage(
    *,
    repository_root: Path,
    staging_dir: Path,
    manifest_path: Path,
    sec_mapping_path: Path,
) -> dict[str, Any]:
    root = repository_root.resolve()
    _load_protocol(root)
    manifest = _load_manifest(root, manifest_path.resolve())
    _validate_sources(staging_dir=staging_dir.resolve(), manifest=manifest)
    watchlist_file = root / WATCHLIST_PATH
    if _sha256_file(watchlist_file) != WATCHLIST_SHA256:
        _fail("form4_full_coverage_source_mismatch", "watchlist hash drifted")
    watchlist = load_stock_watchlist()
    watchlist_symbols = {_normalize_symbol(record.symbol) for record in watchlist}
    if len(watchlist) != WATCHLIST_COUNT or None in watchlist_symbols or len(watchlist_symbols) != WATCHLIST_COUNT:
        _fail("form4_full_coverage_universe_invalid", "watchlist count or symbols invalid")
    mapping_path = sec_mapping_path.resolve()
    try:
        mapping_path.relative_to(root)
    except ValueError:
        pass
    else:
        _fail("form4_full_coverage_mapping_boundary", "SEC mapping must remain outside repository")
    cik_to_symbol = _load_sec_mapping(mapping_path)
    try:
        round42_binding = _load_protocol_binding(root)
    except Exception as exc:
        _fail("form4_full_coverage_protocol_drift", type(exc).__name__)
    quarter_results: list[dict[str, Any]] = []
    totals = Counter()
    for row in manifest["quarters"]:
        quarter = row["quarter"]
        path = staging_dir.resolve() / row["filename"]
        parsed = _parse_purchase_aggregates(
            path.read_bytes(),
            quarter=quarter,
            amendment_receipt=round42_binding["amendment_receipt"],
        )
        mapping = _aggregate_mapping(
            parsed["purchases"],
            cik_to_symbols=cik_to_symbol,
            watchlist_symbols=watchlist_symbols,
        )
        for key, value in parsed.items():
            if key.endswith("count") or key == "eligible_transaction_rows":
                totals[key] += int(value)
        quarter_results.append(
            {
                "quarter": quarter,
                "source_bytes": row["bytes"],
                "source_sha256": row["sha256"],
                "submission_count": parsed["submission_count"],
                "form4_submission_count": parsed["form4_submission_count"],
                "amendment_submission_count": parsed["amendment_submission_count"],
                "eligible_transaction_rows": parsed["eligible_transaction_rows"],
                "eligible_purchase_accession_count": parsed["eligible_purchase_accession_count"],
                "transaction_exclusion_counts": parsed["transaction_exclusion_counts"],
                "mapping": mapping,
            }
        )
    result: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "research_round": 52,
        "status": "full_quarter_coverage_ready_for_separate_preregistration",
        "validation_scope": "82_quarter_form4_coverage_only_no_market_returns",
        "source_manifest": {
            "path": str(manifest_path),
            "manifest_sha256": manifest["manifest_sha256"],
            "quarter_count": len(manifest["quarters"]),
            "all_bytes_and_hashes_verified": True,
            "anchors_verified": True,
        },
        "watchlist": {
            "count": WATCHLIST_COUNT,
            "sha256": WATCHLIST_SHA256,
            "current_cohort_only": True,
        },
        "sec_mapping": {
            "source_url": SEC_MAPPING_URL,
            "bytes": SEC_MAPPING_BYTES,
            "sha256": SEC_MAPPING_SHA256,
            "mapping_is_current_only": True,
        },
        "quarter_results": quarter_results,
        "aggregate_counts": {
            "form4_submission_count": totals["form4_submission_count"],
            "eligible_transaction_rows": totals["eligible_transaction_rows"],
            "eligible_purchase_accession_count": totals["eligible_purchase_accession_count"],
            "current_cik_exact_purchase_accession_count": sum(
                row["mapping"]["current_cik_exact_purchase_accession_count"]
                for row in quarter_results
            ),
            "as_filed_symbol_exact_purchase_accession_count": sum(
                row["mapping"]["as_filed_symbol_exact_purchase_accession_count"]
                for row in quarter_results
            ),
            "union_mapped_purchase_accession_count": sum(
                row["mapping"]["union_mapped_purchase_accession_count"]
                for row in quarter_results
            ),
        },
        "state_boundary": {
            "performance_present": False,
            "strategy_run_count": 0,
            "paper_authorized": False,
            "real_money_action_usd": 0,
            "today_action": "今天不下單",
        },
        "limitations": [
            "current_watchlist_is_not_point_in_time_membership",
            "current_cik_mapping_is_not_historical_security_master",
            "as_filed_symbol_match_is_not_known_at_mapping",
            "form4_filing_date_is_not_intraday_public_timestamp",
            "coverage_only_does_not_compute_market_returns_or_strategy_metrics",
            "raw_form4_row_identifiers_are_discarded_after_aggregate_processing",
        ],
    }
    _privacy_scan(result)
    result["receipt_sha256"] = _canonical_sha256(result)
    return result


def write_validation_receipt(result: dict[str, Any], *, repository_root: Path) -> Path:
    path = repository_root / VALIDATION_PATH
    path.write_text(
        json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    return path
