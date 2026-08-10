from __future__ import annotations

import hashlib
import json
from datetime import date
from pathlib import Path

import pytest

import usfddk.form4_current_cohort_coverage as coverage
from usfddk.form4_historical_feasibility import (
    ClusterAudit,
    HistoricalCluster,
    ParsedQuarter,
)
from usfddk.universe import load_stock_watchlist

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = ROOT / "artifacts/snapshot_20260731_6a7ca6b8.zip"


def _write_mapping(path: Path, *, count: int = 30) -> None:
    payload = {
        str(index): {"ticker": record.symbol, "cik_str": 1000000 + index}
        for index, record in enumerate(load_stock_watchlist(), start=1)
    }
    if count < len(payload):
        payload = dict(list(payload.items())[:count])
    path.write_text(json.dumps(payload), encoding="utf-8")


def _fake_parsed(quarter: str) -> ParsedQuarter:
    return ParsedQuarter(
        quarter=quarter,
        filename=f"{quarter.lower()}_form345.zip",
        body_sha256="a" * 64,
        byte_count=1,
        row_counts={"submission": 1, "reporting_owner": 1, "nonderivative_transaction": 1},
        submission_type_counts={"4": 1},
        form4_submission_count=1,
        amendment_submission_count=0,
        transaction_exclusion_counts={},
        eligible_transaction_rows=1,
        purchase_accessions=(),
    )


def _fake_cluster(issuer_cik: str, day: date) -> HistoricalCluster:
    return HistoricalCluster(
        issuer_cik=issuer_cik,
        decision_date=day,
        member_accessions=("hidden", "hidden2"),
        owner_ciks=("hidden-owner-a", "hidden-owner-b"),
        reported_purchase_dollars=100000,
        left_boundary_excluded=False,
    )


def test_protocol_receipt_is_self_bound() -> None:
    receipt = json.loads(
        (ROOT / coverage.PROTOCOL_RECEIPT_PATH).read_text(encoding="utf-8")
    )
    claimed = receipt.pop("receipt_sha256")
    canonical = json.dumps(
        receipt, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode()
    assert claimed == coverage.EXPECTED_PROTOCOL_RECEIPT_SHA256
    assert hashlib.sha256(canonical).hexdigest() == claimed
    assert coverage._sha256_file(ROOT / coverage.PROTOCOL_PATH) == coverage.EXPECTED_PROTOCOL_SHA256


def test_current_cohort_audit_stays_aggregate_and_fails_insufficient_coverage(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    mapping_path = tmp_path / "company_tickers.json"
    _write_mapping(mapping_path)
    monkeypatch.setattr(coverage, "SEC_MAPPING_BYTES", mapping_path.stat().st_size)
    monkeypatch.setattr(coverage, "SEC_MAPPING_SHA256", coverage._sha256_file(mapping_path))
    monkeypatch.setattr(coverage, "_load_protocol", lambda repository_root: {})

    archive_paths: dict[str, Path] = {}
    for quarter in coverage.FIXED_QUARTERS:
        archive = tmp_path / f"{quarter.lower()}_form345.zip"
        archive.write_bytes(b"fixture")
        archive_paths[quarter] = archive

    first_cik = "0001000001"

    def fake_parse(body: bytes, *, quarter: str, repository_root: Path, filename: str):
        assert body == b"fixture"
        return _fake_parsed(quarter)

    def fake_build(parsed: ParsedQuarter) -> ClusterAudit:
        clusters = {
            "2006Q1": (_fake_cluster(first_cik, date(2006, 1, 27)),),
            "2016Q3": (),
            "2026Q2": (),
        }[parsed.quarter]
        return ClusterAudit(
            primary_clusters=clusters,
            left_boundary_clusters=(),
            raw_gate_crossings=len(clusters),
            accessions_below_minimum=0,
            cooldown_suppressed_filing_dates=0,
        )

    monkeypatch.setattr(coverage, "parse_quarter_archive", fake_parse)
    monkeypatch.setattr(coverage, "build_historical_clusters", fake_build)
    result = coverage.audit_current_cohort_coverage(
        repository_root=ROOT,
        snapshot_path=SNAPSHOT,
        sec_mapping_path=mapping_path,
        archive_paths=archive_paths,
    )

    assert result["status"] == "current_cohort_coverage_failed_no_formal_backtest"
    assert result["coverage_gate"]["observed_mapped_primary_clusters"] == 1
    assert result["coverage_gate"]["observed_mapped_issuers"] == 1
    assert result["state_boundary"]["performance_present"] is False
    assert result["state_boundary"]["paper_authorized"] is False
    assert result["state_boundary"]["today_action"] == "今天不下單"
    rendered = json.dumps(result, ensure_ascii=False)
    assert "issuer_cik" not in rendered
    assert "hidden-owner" not in rendered
    assert "hidden" not in rendered


def test_mapping_must_remain_outside_repository(tmp_path: Path) -> None:
    inside = ROOT / "company_tickers.test.json"
    inside.write_text("{}", encoding="utf-8")
    try:
        with pytest.raises(coverage.Form4CurrentCohortCoverageError) as error:
            coverage.audit_current_cohort_coverage(
                repository_root=ROOT,
                snapshot_path=SNAPSHOT,
                sec_mapping_path=inside,
                archive_paths={quarter: tmp_path / "missing" for quarter in coverage.FIXED_QUARTERS},
            )
        assert error.value.code == "form4_current_cohort_source_boundary"
    finally:
        inside.unlink()


def test_mapping_rejects_duplicate_ticker(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    mapping = tmp_path / "company_tickers.json"
    mapping.write_text(
        json.dumps(
            {
                "0": {"ticker": "AAA", "cik_str": 1},
                "1": {"ticker": "AAA", "cik_str": 2},
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(coverage, "SEC_MAPPING_BYTES", mapping.stat().st_size)
    monkeypatch.setattr(coverage, "SEC_MAPPING_SHA256", coverage._sha256_file(mapping))
    with pytest.raises(coverage.Form4CurrentCohortCoverageError) as error:
        coverage._load_sec_mapping(mapping)
    assert error.value.code == "form4_current_cohort_mapping_invalid"
