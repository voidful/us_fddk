from __future__ import annotations

import csv
import hashlib
import json
from copy import deepcopy
from pathlib import Path

import exchange_calendars as xcals
import pytest

from usfddk.disclosure_known_at import (
    ACTOR_ROLES,
    CALENDAR_COLUMNS,
    GENESIS_SHA256,
    IDENTIFIER_COLUMNS,
    KNOWN_AT_BASES,
    REQUIRED_FILES,
    SOURCE_TYPES,
    TIMESTAMP_FIELDS,
    audit_disclosure_known_at_bundle,
)

ROOT = Path(__file__).resolve().parents[1]
SHA = "a" * 64


def _canonical_sha(value: dict) -> str:
    payload = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode()
    return hashlib.sha256(payload).hexdigest()


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text(
        "".join(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n" for row in rows),
        encoding="utf-8",
    )


def _write_csv(path: Path, columns: tuple[str, ...], rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _source_receipt(source: str, index: int) -> dict:
    official = {
        "congress_house_ptr": "https://disclosures-clerk.house.gov/FinancialDisclosure",
        "congress_senate_ptr": "https://efdsearch.senate.gov/search/home/",
        "sec_form_4": "https://www.sec.gov/search-filings",
        "sec_schedule_13d": "https://www.sec.gov/search-filings",
        "sec_schedule_13g": "https://www.sec.gov/search-filings",
        "sec_form_13f": "https://www.sec.gov/search-filings",
    }[source]
    return {
        "source_type": source,
        "official_entry_url": official,
        "request_url": f"{official}?receipt={index}",
        "collected_at": "2026-07-30T20:15:00Z",
        "first_observed_at": "2026-07-30T20:20:00Z",
        "http_status": 200,
        "content_type": "application/json",
        "content_sha256": hashlib.sha256(f"content-{source}".encode()).hexdigest(),
        "byte_count": 100 + index,
        "record_count": 1,
        "request_receipt_sha256": hashlib.sha256(f"request-{source}".encode()).hexdigest(),
        "terms_snapshot_sha256": hashlib.sha256(f"terms-{source}".encode()).hexdigest(),
        "legal_use_approved": True,
        "raw_payload_location": "private_quarantine_not_git_ci_site",
    }


def _source_spec(source: str) -> tuple[str, str, str, float | None, float | None, str, str]:
    specs = {
        "congress_house_ptr": (
            "PTR",
            "P",
            "purchase_range",
            1_001,
            15_000,
            "self",
            "timestamp",
        ),
        "congress_senate_ptr": (
            "PTR",
            "S",
            "sale_range",
            15_001,
            50_000,
            "joint",
            "timestamp",
        ),
        "sec_form_4": (
            "FORM4",
            "P",
            "open_or_private_purchase",
            12_500,
            12_500,
            "direct",
            "timestamp",
        ),
        "sec_schedule_13d": (
            "SC_13D",
            "OWNERSHIP",
            "beneficial_ownership_control_intent_snapshot",
            None,
            None,
            "control_intent",
            "timestamp",
        ),
        "sec_schedule_13g": (
            "SC_13G",
            "OWNERSHIP",
            "beneficial_ownership_reporting_snapshot",
            None,
            None,
            "passive_investor",
            "timestamp",
        ),
        "sec_form_13f": (
            "13F_HR",
            "HOLDING",
            "quarter_end_institutional_holding_snapshot",
            100_000,
            100_000,
            "institutional_manager",
            "quarter_end",
        ),
    }
    return specs[source]


def _build_rows() -> tuple[list[dict], list[dict], list[dict]]:
    versions: list[dict] = []
    events: list[dict] = []
    identifiers: list[dict] = []
    previous = GENESIS_SHA256
    for index, source in enumerate(SOURCE_TYPES, start=1):
        document_type, code, semantics, low, high, ownership, precision = _source_spec(source)
        version_id = f"version-{index}"
        document_id = f"document-{index}"
        accession = f"00000000{index:02d}-26-{index:06d}" if source.startswith("sec_") else None
        accepted = None if source.startswith("congress_") else "2026-07-30T20:00:00Z"
        version = {
            "source_type": source,
            "source_document_id": document_id,
            "source_version_id": version_id,
            "supersedes_version_id": None,
            "document_type": document_type,
            "accession_number": accession,
            "request_receipt_sha256": hashlib.sha256(f"request-{source}".encode()).hexdigest(),
            "content_sha256": hashlib.sha256(f"document-{source}".encode()).hexdigest(),
            "record_count": 1,
            "filed_at": "2026-07-30T19:50:00Z",
            "accepted_at": accepted,
            "public_at": "2026-07-30T20:10:00Z",
            "public_at_evidence_type": "official_timestamp",
            "public_at_evidence_sha256": hashlib.sha256(f"public-{source}".encode()).hexdigest(),
            "independent_archived_first_seen_at": None,
            "independent_archived_evidence_sha256": None,
            "first_observed_at": "2026-07-30T20:20:00Z",
            "known_at": "2026-07-30T20:10:00Z",
            "known_at_basis": "official_public_timestamp",
            "previous_chain_sha256": previous,
            "chain_sha256": "",
        }
        version["chain_sha256"] = _canonical_sha(
            {key: value for key, value in version.items() if key != "chain_sha256"}
        )
        previous = version["chain_sha256"]
        versions.append(version)
        role = sorted(ACTOR_ROLES[source])[0]
        event_at = None if source == "sec_form_13f" else "2026-07-29T15:00:00Z"
        event = {
            "source_type": source,
            "source_event_id": f"event-{index}",
            "source_document_id": document_id,
            "source_version_id": version_id,
            "supersedes_version_id": None,
            "security_id": f"security-{index}",
            "security_link_id": f"link-{index}",
            "actor_token": f"act_{index:016x}",
            "actor_role": role,
            "actor_eligibility": {
                "actor_type": {
                    "congress_house_ptr": "us_legislator",
                    "congress_senate_ptr": "us_legislator",
                    "sec_form_4": "sec_reporting_insider",
                    "sec_schedule_13d": "beneficial_owner",
                    "sec_schedule_13g": "beneficial_owner",
                    "sec_form_13f": "institutional_manager",
                }[source],
                "eligible_from": "2020-01-01T00:00:00Z",
                "eligible_to": None,
                "known_at": "2026-01-01T00:00:00Z",
                "source_record_id": f"actor-record-{index}",
            },
            "economic_semantics": semantics,
            "transaction_code": code,
            "ownership_nature": ownership,
            "acquired_disposed_code": (
                "A" if source == "sec_form_4" else None
            ),
            "filing_category": {
                "congress_house_ptr": "periodic_transaction_report",
                "congress_senate_ptr": "periodic_transaction_report",
                "sec_form_4": "section_16_transaction",
                "sec_schedule_13d": "control_intent",
                "sec_schedule_13g": "passive_investor",
                "sec_form_13f": "quarter_end_holdings",
            }[source],
            "value_min_usd": low,
            "value_max_usd": high,
            "event_precision": precision,
            "reported_event_date": None,
            "reported_period_end": "2026-06-30" if source == "sec_form_13f" else None,
            "event_at": event_at,
            "filed_at": version["filed_at"],
            "accepted_at": accepted,
            "public_at": version["public_at"],
            "first_observed_at": version["first_observed_at"],
            "known_at": version["known_at"],
            "known_at_basis": version["known_at_basis"],
            "decision_at": "2026-07-31T20:00:00Z",
            "trade_at": "2026-08-03T13:30:00Z",
            "null_reasons": {
                "event_at": "source_reports_quarter_end_only" if event_at is None else None,
                "filed_at": None,
                "accepted_at": (
                    "official_source_does_not_publish_acceptance_timestamp"
                    if accepted is None
                    else None
                ),
                "public_at": None,
            },
        }
        events.append(event)
        identifiers.append(
            {
                "security_link_id": f"link-{index}",
                "source_type": source,
                "source_security_id": f"source-security-{index}",
                "security_id": f"security-{index}",
                "company_id": f"company-{index}",
                "ticker": f"T{index}",
                "exchange": "XNYS",
                "share_class": "common",
                "cusip": f"0000000{index}",
                "cik": f"{index:010d}",
                "effective_from": "2020-01-01T00:00:00Z",
                "effective_to": "",
                "known_at": "2026-01-01T00:00:00Z",
                "source_record_id": f"security-record-{index}",
            }
        )
    return versions, events, identifiers


def _calendar_rows() -> list[dict]:
    calendar = xcals.get_calendar("XNYS")
    schedule = calendar.schedule.loc["2026-07-29":"2026-08-04"]
    return [
        {
            "session": str(session.date()),
            "open_at": row["open"].isoformat().replace("+00:00", "Z"),
            "close_at": row["close"].isoformat().replace("+00:00", "Z"),
        }
        for session, row in schedule.iterrows()
    ]


def _summary(bundle_id: str) -> dict:
    source_audits = [
        {
            "source_type": source,
            "observed_start": None,
            "observed_end": None,
            "expected_documents": None,
            "observed_documents": None,
            "missing_documents": None,
            "late_filings": None,
            "amendments": None,
            "confidential_treatment_items": None,
            "event_lag_count": None,
            "lag_unresolved_count": None,
            "distinct_actor_count": None,
            "public_statistics_suppressed": True,
        }
        for source in SOURCE_TYPES
    ]
    return {
        "schema_version": 1,
        "bundle_id": bundle_id,
        "generated_at": "2026-08-05T12:00:00Z",
        "source_audits": source_audits,
        "privacy_audit": {
            "forbidden_key_scan_passed": True,
            "site_bundle_scan_passed": True,
            "source_map_scan_passed": True,
            "manual_reviewed_at": "2026-08-05T11:00:00Z",
            "manual_reviewer_receipt_sha256": hashlib.sha256(b"privacy-review").hexdigest(),
            "minimum_actor_threshold": 10,
            "raw_rows_in_summary": 0,
            "selected_tickers": [],
            "actor_names": [],
        },
        "independent_attacks": {
            "rejected": 8,
            "total": 8,
            "all_rejected": True,
            "exact_error_codes": [
                "timestamp_contract_invalid",
                "event_schema_mismatch",
                "revision_chain_invalid",
                "security_mapping_backfill",
                "event_duplicate",
                "unsupported_transaction_code",
                "xnys_decision_trade_clock_invalid",
                "edgar_accession_duplicate",
            ],
            "independent_reviewer_receipt_sha256": hashlib.sha256(b"attack-review").hexdigest(),
        },
        "authorized_real_sample": {
            "accepted": True,
            "synthetic": False,
            "row_count": 6,
            "reviewed_at": "2026-08-05T11:30:00Z",
            "reviewer_receipt_sha256": hashlib.sha256(b"sample-review").hexdigest(),
        },
    }


def _manifest(bundle_id: str, chain_head: str) -> dict:
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
    return {
        "schema_version": 1,
        "contract_id": "us_fddk.short_term_disclosure_known_at.v1",
        "phase": "known_at_readiness_only",
        "bundle_id": bundle_id,
        "generated_at": "2026-08-05T12:00:00Z",
        "legal_use": {
            "exact_use_description": "local non-commercial readiness validation only",
            "commercial_use_review_status": "approved_for_exact_use",
            "congress_use_review_status": "approved_for_exact_use",
            "source_terms_reviewed": True,
            "reviewed_at": "2026-08-01T00:00:00Z",
            "expires_at": "2027-08-01T00:00:00Z",
            "authority_reference": "external-test-authority-receipt",
            "evidence_sha256": hashlib.sha256(b"legal").hexdigest(),
        },
        "sec_access": {
            "user_agent_contact_declared": True,
            "sec_policy_ceiling_requests_per_second": 10,
            "configured_requests_per_second": 5,
            "global_across_processes_and_machines": True,
            "cache_enabled": True,
            "retry_after_and_429_backoff": True,
            "stop_on_403_or_robots_terms_change": True,
        },
        "coverage": {
            "claim": "observed_records_only_no_complete_period_claim",
            "complete_period_claimed": False,
            "twenty_year_coverage_claimed": False,
            "twenty_year_coverage_validated": False,
            "observed_start": "2026-06-30",
            "observed_end": "2026-07-30",
        },
        "source_receipts": {
            source: _source_receipt(source, index)
            for index, source in enumerate(SOURCE_TYPES, start=1)
        },
        "normalized_record_contract": {
            "format": "utf8_jsonl_one_object_per_line",
            "source_type_values": list(SOURCE_TYPES),
            "required_fields": required_fields,
            "unknown_value_policy": "explicit_null_with_source_reason_no_imputation",
        },
        "timestamp_contract": {
            "timezone": "UTC",
            "calendar": "XNYS",
            "required_timestamp_fields": list(TIMESTAMP_FIELDS),
            "known_at_basis_values": list(KNOWN_AT_BASES),
            "known_at_rule": "official_public_timestamp_else_independent_archived_first_seen_else_local_first_observed",
            "decision_at_rule": "first_official_xnys_close_strictly_after_known_at",
            "trade_at_rule": "next_official_xnys_open_after_decision_at",
        },
        "revision_contract": {
            "append_only": True,
            "original_versions_preserved": True,
            "hash_algorithm": "sha256",
            "canonicalization": "utf8_json_sorted_keys_compact_separators_no_nan",
            "genesis_previous_sha256": GENESIS_SHA256,
            "chain_head_sha256": chain_head,
            "revision_count": 0,
            "final_revised_strategy_substitution_allowed": False,
        },
        "privacy_contract": {
            "raw_payload_location": "encrypted_private_quarantine_not_git_ci_site",
            "raw_data_allowed_in_git_ci_site": False,
            "internal_actor_key": "salted_nonreversible_actor_token",
            "actor_salt_allowed_in_git": False,
            "minimum_distinct_actor_count_for_public_aggregate": 10,
            "public_output": "source_family_readiness_lag_missingness_revision_and_compliance_aggregates_only",
            "public_forbidden_fields": forbidden,
        },
        "files": {},
        "readiness_boundary": {
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
        },
    }


def _refresh_files(bundle: Path) -> None:
    manifest_path = bundle / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    counts = {
        "disclosure_events.jsonl": len(
            (bundle / "disclosure_events.jsonl").read_text(encoding="utf-8").splitlines()
        ),
        "source_versions.jsonl": len(
            (bundle / "source_versions.jsonl").read_text(encoding="utf-8").splitlines()
        ),
        "identifier_history.csv": sum(
            1 for _ in (bundle / "identifier_history.csv").open(encoding="utf-8")
        )
        - 1,
        "trading_calendar.csv": sum(
            1 for _ in (bundle / "trading_calendar.csv").open(encoding="utf-8")
        )
        - 1,
        "sanitized_summary.json": 1,
    }
    manifest["files"] = {
        name: {
            "sha256": hashlib.sha256((bundle / name).read_bytes()).hexdigest(),
            "rows": counts[name],
            "bytes": len((bundle / name).read_bytes()),
        }
        for name in REQUIRED_FILES
    }
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


def _write_bundle(tmp_path: Path) -> Path:
    bundle = tmp_path / "authorized-real-disclosure-fixture"
    bundle.mkdir()
    versions, events, identifiers = _build_rows()
    _write_jsonl(bundle / "source_versions.jsonl", versions)
    _write_jsonl(bundle / "disclosure_events.jsonl", events)
    _write_csv(bundle / "identifier_history.csv", IDENTIFIER_COLUMNS, identifiers)
    _write_csv(bundle / "trading_calendar.csv", CALENDAR_COLUMNS, _calendar_rows())
    summary = _summary("authorized-real-fixture-v1")
    (bundle / "sanitized_summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )
    manifest = _manifest("authorized-real-fixture-v1", versions[-1]["chain_sha256"])
    (bundle / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    _refresh_files(bundle)
    return bundle


def _jsonl_rows(bundle: Path, name: str) -> list[dict]:
    return [json.loads(line) for line in (bundle / name).read_text(encoding="utf-8").splitlines()]


def _rewrite_jsonl(bundle: Path, name: str, rows: list[dict]) -> None:
    _write_jsonl(bundle / name, rows)
    _refresh_files(bundle)


def _rechain(bundle: Path, rows: list[dict]) -> None:
    previous = GENESIS_SHA256
    for row in rows:
        row["previous_chain_sha256"] = previous
        row["chain_sha256"] = _canonical_sha(
            {key: value for key, value in row.items() if key != "chain_sha256"}
        )
        previous = row["chain_sha256"]
    _write_jsonl(bundle / "source_versions.jsonl", rows)
    manifest_path = bundle / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["revision_contract"]["chain_head_sha256"] = previous
    manifest["revision_contract"]["revision_count"] = sum(
        row["supersedes_version_id"] is not None for row in rows
    )
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    _refresh_files(bundle)


def _audit(bundle: Path) -> dict:
    return audit_disclosure_known_at_bundle(bundle.resolve(), root=ROOT)


def test_absent_bundle_is_sanitized_and_exactly_two_of_twenty() -> None:
    result = audit_disclosure_known_at_bundle(None, root=ROOT)

    assert result["readiness"] == {"passed": 2, "total": 20, "all_passed": False}
    assert result["selection"] == {
        "dynamic_selection_enabled": False,
        "selected_tickers": [],
    }
    assert result["paper"]["status"] == "all_cash_not_started"
    assert result["paper"]["positions"] == 0
    assert result["real_money_usd"] == 0
    rendered = json.dumps(result)
    assert "actor_token" not in rendered
    assert "/Users/" not in rendered
    assert "/tmp/" not in rendered


def test_self_attested_external_fixture_never_becomes_ready_or_promotes(tmp_path: Path) -> None:
    result = _audit(_write_bundle(tmp_path))

    assert result["readiness"] == {"passed": 3, "total": 20, "all_passed": False}
    assert [key for key, gate in result["gates"].items() if gate["passed"]] == [
        "01_protocol_schema_receipt_integrity",
        "02_official_source_semantics_pinned",
        "07_closed_manifest_admitted",
    ]
    assert result["gates"]["03_congress_exact_use_legal_clearance"]["failure_code"] == (
        "independent_legal_clearance_receipt_missing"
    )
    assert result["gates"]["13_append_only_revision_chain_verified"]["failure_code"] == (
        "external_prior_chain_anchor_missing"
    )
    assert result["gates"]["20_authorized_real_sample_accepted"]["failure_code"] == (
        "authorized_real_sample_external_receipt_missing"
    )
    assert result["decision"] == {
        "can_promote": False,
        "dynamic_selection_enabled": False,
        "strategy_defined": False,
        "formal_backtest_authorized": False,
        "strategy_runs": 0,
        "today_action": "today_no_trade",
    }
    assert result["selection"]["selected_tickers"] == []
    assert result["paper"]["status"] == "all_cash_not_started"
    assert result["real_money_usd"] == 0
    public_receipt = json.dumps(result, sort_keys=True)
    for private_value in ("T1", "00000001", "document-1", "event-1", "act_0000000000000001"):
        assert private_value not in public_receipt
    assert result["sources"]["document_type_counts"] == {}
    assert result["sources"]["event_type_counts"] == {}


@pytest.mark.parametrize(
    ("attack", "expected_code"),
    [
        ("lookahead", "timestamp_contract_invalid"),
        ("date_only", "timestamp_contract_invalid"),
        ("final_revision", "revision_chain_invalid"),
        ("mapping_backfill", "security_mapping_backfill"),
        ("duplicate", "event_duplicate"),
        ("unsupported_code", "unsupported_transaction_code"),
        ("private_field", "event_schema_mismatch"),
        ("calendar_plus_one", "xnys_decision_trade_clock_invalid"),
        ("duplicate_accession", "edgar_accession_duplicate"),
    ],
)
def test_single_error_attacks_fail_closed(
    tmp_path: Path, attack: str, expected_code: str
) -> None:
    bundle = _write_bundle(tmp_path)
    events = _jsonl_rows(bundle, "disclosure_events.jsonl")
    versions = _jsonl_rows(bundle, "source_versions.jsonl")
    if attack == "lookahead":
        versions[0]["public_at"] = "2026-07-30T20:30:00Z"
        _rechain(bundle, versions)
    elif attack == "date_only":
        events[0]["known_at"] = "2026-07-30"
        _rewrite_jsonl(bundle, "disclosure_events.jsonl", events)
    elif attack == "final_revision":
        versions[2]["document_type"] = "FORM4_A"
        versions[2]["supersedes_version_id"] = "missing-original-version"
        events[2]["supersedes_version_id"] = "missing-original-version"
        _rewrite_jsonl(bundle, "disclosure_events.jsonl", events)
        _rechain(bundle, versions)
    elif attack == "mapping_backfill":
        path = bundle / "identifier_history.csv"
        with path.open(newline="", encoding="utf-8") as handle:
            identifiers = list(csv.DictReader(handle))
        identifiers[0]["known_at"] = "2026-07-30T20:11:00Z"
        _write_csv(path, IDENTIFIER_COLUMNS, identifiers)
        _refresh_files(bundle)
    elif attack == "duplicate":
        events.append(deepcopy(events[0]))
        versions[0]["record_count"] = 2
        manifest_path = bundle / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["source_receipts"][SOURCE_TYPES[0]]["record_count"] = 2
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        _write_jsonl(bundle / "disclosure_events.jsonl", events)
        _rechain(bundle, versions)
    elif attack == "unsupported_code":
        events[2]["transaction_code"] = "Z"
        _rewrite_jsonl(bundle, "disclosure_events.jsonl", events)
    elif attack == "private_field":
        events[0]["person_name"] = "must never enter normalized rows"
        _rewrite_jsonl(bundle, "disclosure_events.jsonl", events)
    elif attack == "calendar_plus_one":
        events[0]["trade_at"] = "2026-07-31T13:30:00Z"
        _rewrite_jsonl(bundle, "disclosure_events.jsonl", events)
    elif attack == "duplicate_accession":
        versions[3]["accession_number"] = versions[2]["accession_number"]
        _rechain(bundle, versions)
    result = _audit(bundle)

    assert result["readiness"]["all_passed"] is False
    assert result["bundle"]["failure_code"] == expected_code
    assert result["selection"]["selected_tickers"] == []
    assert result["paper"]["positions"] == 0
    assert result["real_money_usd"] == 0


def test_repository_internal_or_relative_raw_bundle_is_rejected(tmp_path: Path) -> None:
    external = _write_bundle(tmp_path)
    relative = audit_disclosure_known_at_bundle(external.name, root=ROOT)
    assert relative["bundle"]["failure_code"] == "bundle_path_not_absolute"

    internal = audit_disclosure_known_at_bundle(ROOT, root=ROOT)
    assert internal["bundle"]["failure_code"] == "bundle_inside_repository"


@pytest.mark.parametrize(
    ("attack", "expected_code"),
    [
        ("first_observed_backfill", "first_observed_receipt_mismatch"),
        ("known_priority", "known_at_priority_violation"),
        ("archive_without_evidence", "archived_first_seen_evidence_missing"),
        ("request_host", "source_request_receipt_invalid"),
        ("cusip_ambiguity", "security_identifier_ambiguity"),
        ("precision_conflict", "event_precision_timestamp_conflict"),
        ("suppressed_cell", "suppressed_cell_disclosed"),
        ("form4_indicator", "form4_acquired_disposed_missing"),
        ("ptr_band", "ptr_amount_band_invalid"),
        ("schedule_category", "schedule_13_filer_category_missing"),
        ("form13f_period", "form13f_holding_semantics_incomplete"),
    ],
)
def test_evidence_semantics_and_privacy_attacks_fail_closed(
    tmp_path: Path, attack: str, expected_code: str
) -> None:
    bundle = _write_bundle(tmp_path)
    events = _jsonl_rows(bundle, "disclosure_events.jsonl")
    versions = _jsonl_rows(bundle, "source_versions.jsonl")
    if attack == "first_observed_backfill":
        versions[0]["first_observed_at"] = "2026-07-30T20:19:00Z"
        events[0]["first_observed_at"] = "2026-07-30T20:19:00Z"
        _rewrite_jsonl(bundle, "disclosure_events.jsonl", events)
        _rechain(bundle, versions)
    elif attack == "known_priority":
        versions[0]["known_at_basis"] = "local_first_observed_fallback"
        versions[0]["known_at"] = versions[0]["first_observed_at"]
        events[0]["known_at_basis"] = versions[0]["known_at_basis"]
        events[0]["known_at"] = versions[0]["known_at"]
        _rewrite_jsonl(bundle, "disclosure_events.jsonl", events)
        _rechain(bundle, versions)
    elif attack == "archive_without_evidence":
        versions[0]["public_at"] = None
        versions[0]["public_at_evidence_type"] = None
        versions[0]["public_at_evidence_sha256"] = None
        versions[0]["independent_archived_first_seen_at"] = "2026-07-30T20:05:00Z"
        versions[0]["known_at"] = "2026-07-30T20:05:00Z"
        versions[0]["known_at_basis"] = "independent_archived_first_seen"
        events[0]["public_at"] = None
        events[0]["null_reasons"]["public_at"] = "official_public_timestamp_unavailable"
        events[0]["known_at"] = versions[0]["known_at"]
        events[0]["known_at_basis"] = versions[0]["known_at_basis"]
        _rewrite_jsonl(bundle, "disclosure_events.jsonl", events)
        _rechain(bundle, versions)
    elif attack == "request_host":
        manifest_path = bundle / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["source_receipts"]["sec_form_4"]["request_url"] = (
            "https://example.invalid/fake-edgar"
        )
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    elif attack == "cusip_ambiguity":
        path = bundle / "identifier_history.csv"
        with path.open(newline="", encoding="utf-8") as handle:
            identifiers = list(csv.DictReader(handle))
        duplicate = deepcopy(identifiers[0])
        duplicate.update(
            {
                "security_link_id": "ambiguous-link",
                "source_security_id": "different-source-security",
                "security_id": "different-permanent-security",
                "ticker": "DIFF",
                "source_record_id": "different-security-record",
            }
        )
        identifiers.append(duplicate)
        _write_csv(path, IDENTIFIER_COLUMNS, identifiers)
        _refresh_files(bundle)
    elif attack == "precision_conflict":
        events[5]["event_at"] = "2026-06-30T20:00:00Z"
        events[5]["null_reasons"]["event_at"] = None
        _rewrite_jsonl(bundle, "disclosure_events.jsonl", events)
    elif attack == "suppressed_cell":
        path = bundle / "sanitized_summary.json"
        summary = json.loads(path.read_text(encoding="utf-8"))
        summary["source_audits"][0]["observed_start"] = "2026-07-29"
        path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
        _refresh_files(bundle)
    elif attack == "form4_indicator":
        events[2]["acquired_disposed_code"] = "D"
        _rewrite_jsonl(bundle, "disclosure_events.jsonl", events)
    elif attack == "ptr_band":
        events[0]["value_min_usd"] = 2_000
        events[0]["value_max_usd"] = 3_000
        _rewrite_jsonl(bundle, "disclosure_events.jsonl", events)
    elif attack == "schedule_category":
        events[4]["filing_category"] = "generic_owner"
        _rewrite_jsonl(bundle, "disclosure_events.jsonl", events)
    elif attack == "form13f_period":
        events[5]["reported_period_end"] = "2026-06-29"
        _rewrite_jsonl(bundle, "disclosure_events.jsonl", events)
    result = _audit(bundle)

    assert result["readiness"]["all_passed"] is False
    assert result["bundle"]["failure_code"] == expected_code
    assert result["decision"]["dynamic_selection_enabled"] is False
    assert result["paper"]["positions"] == 0
    assert result["real_money_usd"] == 0


def test_missing_and_empty_bundle_paths_fail_closed(tmp_path: Path) -> None:
    missing = audit_disclosure_known_at_bundle(
        (tmp_path / "missing").resolve(), root=ROOT
    )
    assert missing["bundle"]["failure_code"] == "bundle_missing"

    empty = tmp_path / "empty"
    empty.mkdir()
    result = audit_disclosure_known_at_bundle(empty.resolve(), root=ROOT)
    assert result["bundle"]["failure_code"] == "manifest_schema_mismatch"
    assert result["readiness"]["all_passed"] is False
