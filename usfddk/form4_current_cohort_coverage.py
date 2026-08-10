from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from .data import load_snapshot, panel_fingerprint
from .form4_historical_feasibility import (
    FIXED_QUARTERS,
    _fixed_source,
    _load_historical_protocol,
    build_historical_clusters,
    parse_quarter_archive,
)
from .universe import load_stock_watchlist

SCHEMA_VERSION = "usfddk.short_term_form4_current_cohort_coverage.v1"
PROTOCOL_PATH = Path("docs/SHORT_TERM_FORM4_CURRENT_COHORT_COVERAGE_PROTOCOL.md")
PROTOCOL_RECEIPT_PATH = Path(
    "artifacts/short_term_form4_current_cohort_coverage_protocol_receipt.json"
)
VALIDATION_PATH = Path(
    "artifacts/short_term_form4_current_cohort_coverage_validation.json"
)
EXPECTED_PROTOCOL_SHA256 = "f58cea61d46bb67b4eefcdc6012107fe89851841a21ac502e783170c9c7c2c03"
EXPECTED_PROTOCOL_RECEIPT_SHA256 = "d0fa259feaf82cb3e53b39fdbe0e528f04f9c89ebed1c98d0eb5346041407b58"
SEC_MAPPING_URL = "https://www.sec.gov/files/company_tickers.json"
SEC_MAPPING_BYTES = 795627
SEC_MAPPING_SHA256 = "6dd9c4363c5a95d43f4d8e8f8279f9ae6538d10d295bbdeebe5a433ec954bf6d"
SNAPSHOT_FILENAME = "snapshot_20260731_6a7ca6b8.zip"
SNAPSHOT_ARCHIVE_BYTES = 5821773
SNAPSHOT_ARCHIVE_SHA256 = "d480fb82e712f06aabe0a98461e222344656b87022b8bda2cd7ccaa4c29ae88b"
SNAPSHOT_PANEL_SHA256 = "6a7ca6b83b1570007424daa46b0ff4e8fb4a655d39298a0f4f6d74c3b7ea3a66"
WATCHLIST_PATH = Path("usfddk/resources/us_large_cap_watchlist_v1.csv")
WATCHLIST_SHA256 = "b6002e4e151bd298884f8cdd6272b5cbfde8aedca47cb58b92830d4d92028014"
WATCHLIST_COUNT = 30
MIN_MAPPED_PRIMARY_CLUSTERS = 30
MIN_MAPPED_ISSUERS = 10
RECENT_QUARTERS = ("2016Q3", "2026Q2")

_CIK = re.compile(r"^\d{10}$")


class Form4CurrentCohortCoverageError(RuntimeError):
    """Fail-closed current-cohort coverage diagnostic error."""

    def __init__(self, code: str, detail: str):
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}")


def _fail(code: str, detail: str) -> None:
    raise Form4CurrentCohortCoverageError(code, detail)


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_file(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _canonical_sha256(value: object) -> str:
    rendered = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return _sha256_bytes(rendered)


def _load_protocol(repository_root: Path) -> dict[str, Any]:
    root = repository_root.resolve()
    protocol_path = root / PROTOCOL_PATH
    receipt_path = root / PROTOCOL_RECEIPT_PATH
    if not protocol_path.is_file() or not receipt_path.is_file():
        _fail("form4_current_cohort_protocol_drift", "protocol or receipt is missing")
    if _sha256_file(protocol_path) != EXPECTED_PROTOCOL_SHA256:
        _fail("form4_current_cohort_protocol_drift", "protocol bytes drifted")
    try:
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        _fail("form4_current_cohort_protocol_drift", type(exc).__name__)
    if not isinstance(receipt, dict):
        _fail("form4_current_cohort_protocol_drift", "receipt is not an object")
    canonical = dict(receipt)
    claimed = canonical.pop("receipt_sha256", None)
    if claimed != EXPECTED_PROTOCOL_RECEIPT_SHA256 or _canonical_sha256(canonical) != claimed:
        _fail("form4_current_cohort_protocol_drift", "receipt self-hash drifted")
    expected = {
        "schema_version": 1,
        "status": "post_readout_current_cohort_coverage_diagnostic",
        "snapshot_filename": SNAPSHOT_FILENAME,
        "snapshot_archive_sha256": SNAPSHOT_ARCHIVE_SHA256,
        "snapshot_panel_sha256": SNAPSHOT_PANEL_SHA256,
        "watchlist_sha256": WATCHLIST_SHA256,
        "watchlist_count": WATCHLIST_COUNT,
        "sec_mapping_url": SEC_MAPPING_URL,
        "sec_mapping_sha256": SEC_MAPPING_SHA256,
        "sec_mapping_bytes": SEC_MAPPING_BYTES,
        "fixed_quarters": list(FIXED_QUARTERS),
        "recent_quarters": list(RECENT_QUARTERS),
        "minimum_mapped_primary_clusters": MIN_MAPPED_PRIMARY_CLUSTERS,
        "minimum_mapped_issuers": MIN_MAPPED_ISSUERS,
        "performance_authorized": False,
        "paper_authorized": False,
        "real_money_authorized": False,
    }
    if receipt.get("schema_version") != 1 or any(
        receipt.get(key) != value for key, value in expected.items()
    ):
        _fail("form4_current_cohort_protocol_drift", "fixed contract drifted")
    return receipt


def _load_sec_mapping(path: Path) -> tuple[dict[str, str], int]:
    if not path.is_file() or path.is_symlink():
        _fail("form4_current_cohort_source_mismatch", "SEC mapping is not a regular file")
    body = path.read_bytes()
    if len(body) != SEC_MAPPING_BYTES or _sha256_bytes(body) != SEC_MAPPING_SHA256:
        _fail("form4_current_cohort_source_mismatch", "SEC mapping bytes drifted")
    try:
        payload = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        _fail("form4_current_cohort_mapping_invalid", type(exc).__name__)
    if not isinstance(payload, dict) or not payload:
        _fail("form4_current_cohort_mapping_invalid", "SEC mapping is not an object")
    mapping: dict[str, str] = {}
    for item in payload.values():
        if not isinstance(item, Mapping):
            _fail("form4_current_cohort_mapping_invalid", "mapping row is not an object")
        ticker = item.get("ticker")
        cik_value = item.get("cik_str")
        if not isinstance(ticker, str) or not ticker.strip() or ticker != ticker.upper():
            _fail("form4_current_cohort_mapping_invalid", "ticker is not canonical")
        if isinstance(cik_value, bool) or not isinstance(cik_value, int) or cik_value <= 0:
            _fail("form4_current_cohort_mapping_invalid", "CIK is not a positive integer")
        cik = f"{cik_value:010d}"
        if _CIK.fullmatch(cik) is None or ticker in mapping:
            _fail("form4_current_cohort_mapping_invalid", "ticker or CIK is duplicated/invalid")
        mapping[ticker] = cik
    return mapping, len(payload)


def _privacy_scan(value: object, *, path: str = "root") -> None:
    forbidden = {
        "accession",
        "accession_number",
        "cik",
        "issuer_cik",
        "issuer_token",
        "owner_cik",
        "ticker",
        "symbol",
        "security_token",
    }
    if isinstance(value, Mapping):
        for key, item in value.items():
            key_text = str(key).casefold()
            if key_text in forbidden:
                _fail("form4_current_cohort_privacy_boundary", f"forbidden key at {path}")
            _privacy_scan(item, path=f"{path}.{key_text}")
    elif isinstance(value, Sequence) and not isinstance(value, str | bytes):
        for index, item in enumerate(value):
            _privacy_scan(item, path=f"{path}[{index}]")


def audit_current_cohort_coverage(
    *,
    repository_root: Path,
    snapshot_path: Path,
    sec_mapping_path: Path,
    archive_paths: Mapping[str, Path],
) -> dict[str, Any]:
    """Audit event coverage for the frozen current watchlist, without returns."""

    _load_protocol(repository_root)
    root = repository_root.resolve()
    snapshot = snapshot_path.resolve()
    if snapshot.name != SNAPSHOT_FILENAME or not snapshot.is_file() or snapshot.is_symlink():
        _fail("form4_current_cohort_source_mismatch", "snapshot path is not fixed")
    if snapshot.stat().st_size != SNAPSHOT_ARCHIVE_BYTES or _sha256_file(snapshot) != SNAPSHOT_ARCHIVE_SHA256:
        _fail("form4_current_cohort_source_mismatch", "snapshot archive bytes drifted")
    panel, manifest = load_snapshot(snapshot)
    if panel_fingerprint(panel) != SNAPSHOT_PANEL_SHA256 or manifest.get("panel_sha256") != SNAPSHOT_PANEL_SHA256:
        _fail("form4_current_cohort_source_mismatch", "snapshot panel fingerprint drifted")
    if manifest.get("provider_metadata", {}).get("adjustment") != (
        "adjusted_ohlc = raw_ohlc * (adj_close / raw_close)"
    ):
        _fail("form4_current_cohort_execution_boundary", "raw OHLCV contract is absent")

    watchlist_file = root / WATCHLIST_PATH
    if not watchlist_file.is_file() or _sha256_file(watchlist_file) != WATCHLIST_SHA256:
        _fail("form4_current_cohort_source_mismatch", "watchlist bytes drifted")
    watchlist = load_stock_watchlist()
    symbols = [record.symbol for record in watchlist]
    if len(symbols) != WATCHLIST_COUNT or len(set(symbols)) != WATCHLIST_COUNT:
        _fail("form4_current_cohort_watchlist_invalid", "watchlist count or uniqueness drifted")
    if any(symbol not in panel.close.columns for symbol in symbols):
        _fail("form4_current_cohort_watchlist_invalid", "watchlist ticker is absent from snapshot")

    mapping_source = sec_mapping_path.resolve()
    try:
        mapping_source.relative_to(root)
    except ValueError:
        pass
    else:
        _fail("form4_current_cohort_source_boundary", "SEC mapping must remain outside repository")
    mapping, mapping_record_count = _load_sec_mapping(mapping_source)
    mapped_symbols = {symbol for symbol in symbols if symbol in mapping}
    mapped_ciks = {mapping[symbol] for symbol in mapped_symbols}

    if set(archive_paths) != set(FIXED_QUARTERS):
        _fail("form4_current_cohort_source_mismatch", "quarter set drifted")
    quarter_results: list[dict[str, Any]] = []
    mapped_primary_total = 0
    mapped_left_boundary_total = 0
    mapped_issuer_ciks: set[str] = set()
    recent_mapped_primary_quarters: list[str] = []
    for quarter in FIXED_QUARTERS:
        path = Path(archive_paths[quarter]).resolve()
        source = _fixed_source(_load_historical_protocol(root), quarter)
        parsed = parse_quarter_archive(
            path.read_bytes(),
            quarter=quarter,
            repository_root=root,
            filename=path.name,
        )
        audit = build_historical_clusters(parsed)
        primary = [cluster for cluster in audit.primary_clusters if cluster.issuer_cik in mapped_ciks]
        left_boundary = [
            cluster for cluster in audit.left_boundary_clusters if cluster.issuer_cik in mapped_ciks
        ]
        mapped_primary_total += len(primary)
        mapped_left_boundary_total += len(left_boundary)
        mapped_issuer_ciks.update(cluster.issuer_cik for cluster in primary)
        if quarter in RECENT_QUARTERS and primary:
            recent_mapped_primary_quarters.append(quarter)
        quarter_results.append(
            {
                "quarter": quarter,
                "source_filename": source["filename"],
                "source_bytes": parsed.byte_count,
                "source_sha256": parsed.body_sha256,
                "form4_submission_count": parsed.form4_submission_count,
                "eligible_purchase_accession_count": len(parsed.purchase_accessions),
                "primary_cluster_count_all_issuers": len(audit.primary_clusters),
                "left_boundary_count_all_issuers": len(audit.left_boundary_clusters),
                "mapped_primary_cluster_count": len(primary),
                "mapped_left_boundary_count": len(left_boundary),
                "mapped_issuer_count": len({cluster.issuer_cik for cluster in primary}),
            }
        )

    gates = {
        "watchlist_columns_complete": len(symbols) == WATCHLIST_COUNT,
        "mapped_primary_clusters_at_least_30": mapped_primary_total >= MIN_MAPPED_PRIMARY_CLUSTERS,
        "mapped_issuers_at_least_10": len(mapped_issuer_ciks) >= MIN_MAPPED_ISSUERS,
        "both_recent_quarters_have_mapped_primary_cluster": set(RECENT_QUARTERS)
        <= set(recent_mapped_primary_quarters),
        "sec_mapping_schema_and_hash_valid": True,
    }
    coverage_passed = all(gates.values())
    result: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "research_round": 50,
        "status": (
            "current_cohort_coverage_sufficient_but_not_formal"
            if coverage_passed
            else "current_cohort_coverage_failed_no_formal_backtest"
        ),
        "diagnostic_scope": "current_watchlist_survivorship_biased_coverage_only",
        "snapshot": {
            "filename": SNAPSHOT_FILENAME,
            "archive_bytes": SNAPSHOT_ARCHIVE_BYTES,
            "archive_sha256": SNAPSHOT_ARCHIVE_SHA256,
            "panel_sha256": SNAPSHOT_PANEL_SHA256,
            "rows": int(manifest.get("rows", 0)),
            "start": str(manifest.get("start")),
            "end": str(manifest.get("end")),
            "stock_watchlist_count": WATCHLIST_COUNT,
            "stock_watchlist_mapped_count": len(mapped_symbols),
            "adjusted_ohlcv_only": True,
        },
        "sec_mapping": {
            "source_url": SEC_MAPPING_URL,
            "bytes": SEC_MAPPING_BYTES,
            "sha256": SEC_MAPPING_SHA256,
            "record_count": mapping_record_count,
            "watchlist_mapped_count": len(mapped_symbols),
        },
        "fixed_quarters": list(FIXED_QUARTERS),
        "quarter_results": quarter_results,
        "coverage_gate": {
            "minimum_mapped_primary_clusters": MIN_MAPPED_PRIMARY_CLUSTERS,
            "observed_mapped_primary_clusters": mapped_primary_total,
            "minimum_mapped_issuers": MIN_MAPPED_ISSUERS,
            "observed_mapped_issuers": len(mapped_issuer_ciks),
            "recent_quarters_required": list(RECENT_QUARTERS),
            "recent_quarters_observed": len(recent_mapped_primary_quarters),
            "gates": gates,
            "passed": coverage_passed,
        },
        "aggregate_counts": {
            "mapped_left_boundary_clusters": mapped_left_boundary_total,
            "mapped_symbols_missing_current_cik": WATCHLIST_COUNT - len(mapped_symbols),
        },
        "limitations": [
            "current_sec_cik_mapping_is_not_historical_ticker_or_known_at_mapping",
            "watchlist_is_current_survivor_cohort_not_point_in_time_membership",
            "snapshot_contains_adjusted_ohlcv_not_raw_execution_prices",
            "no_delisting_or_corporate_action_outcome_ledger",
            "no_market_returns_or_benchmark_readout",
            "coverage_diagnostic_does_not_modify_round46_or_round49",
        ],
        "state_boundary": {
            "strategy_run_count": 0,
            "performance_present": False,
            "candidate_selection_count": 0,
            "paper_authorized": False,
            "paper_positions": 0,
            "real_money_action_usd": 0,
            "website_publication_authorized": False,
            "today_action": "今天不下單",
        },
    }
    _privacy_scan(result)
    result["receipt_sha256"] = _canonical_sha256(result)
    return result


def write_validation_receipt(receipt: Mapping[str, Any], *, repository_root: Path) -> None:
    root = repository_root.resolve()
    output = (root / VALIDATION_PATH).resolve()
    if output.parent != (root / "artifacts").resolve() or output.name != VALIDATION_PATH.name:
        _fail("form4_current_cohort_result_boundary", "output path is not fixed")
    _privacy_scan(receipt)
    output.write_text(
        json.dumps(dict(receipt), ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )


__all__ = [
    "EXPECTED_PROTOCOL_RECEIPT_SHA256",
    "EXPECTED_PROTOCOL_SHA256",
    "Form4CurrentCohortCoverageError",
    "audit_current_cohort_coverage",
    "write_validation_receipt",
]
