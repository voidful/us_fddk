from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

PROTOCOL_PATH = ROOT / "docs/SHORT_TERM_DISCLOSURE_KNOWN_AT_PROTOCOL.md"
SCHEMA_PATH = ROOT / "schemas/short_term_disclosure_point_in_time_manifest.schema.json"
RECEIPT_PATH = ROOT / "artifacts/short_term_disclosure_known_at_protocol_receipt.json"

SOURCE_TYPES = [
    "congress_house_ptr",
    "congress_senate_ptr",
    "sec_form_4",
    "sec_schedule_13d",
    "sec_schedule_13g",
    "sec_form_13f",
]

TIMESTAMP_FIELDS = [
    "event_at",
    "filed_at",
    "accepted_at",
    "public_at",
    "first_observed_at",
    "known_at",
    "decision_at",
    "trade_at",
]

PASSED_GATE_IDS = [
    "01_protocol_schema_receipt_integrity",
    "02_official_source_semantics_pinned",
]

BLOCKED_GATE_IDS = [
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
]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _const_array(schema: dict) -> list[str]:
    assert schema["type"] == "array"
    assert schema["items"] is False
    return [item["const"] for item in schema["prefixItems"]]


def test_protocol_and_schema_are_bound_to_the_frozen_receipt() -> None:
    receipt = _load(RECEIPT_PATH)

    assert receipt["schema_version"] == 1
    assert receipt["protocol_phase"] == 1
    assert receipt["status"] == (
        "frozen_after_official_documentation_review_before_any_disclosure_data_fetch_or_"
        "strategy_design"
    )
    assert receipt["protocol"] == {
        "path": "docs/SHORT_TERM_DISCLOSURE_KNOWN_AT_PROTOCOL.md",
        "sha256": _sha256(PROTOCOL_PATH),
    }
    assert receipt["manifest_schema"] == {
        "path": "schemas/short_term_disclosure_point_in_time_manifest.schema.json",
        "sha256": _sha256(SCHEMA_PATH),
    }
    for parent_key in (
        "parent_point_in_time_contract",
        "parent_point_in_time_receipt",
        "parent_restatement_firewall_protocol",
        "parent_restatement_firewall_receipt",
    ):
        parent = receipt[parent_key]
        assert _sha256(ROOT / parent["path"]) == parent["sha256"]


def test_manifest_schema_is_closed_phase_one_readiness_only() -> None:
    schema = _load(SCHEMA_PATH)

    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["additionalProperties"] is False
    assert schema["properties"]["schema_version"]["const"] == 1
    assert schema["properties"]["contract_id"]["const"] == (
        "us_fddk.short_term_disclosure_known_at.v1"
    )
    assert schema["properties"]["phase"]["const"] == "known_at_readiness_only"

    def assert_named_objects_are_closed(node: object) -> None:
        if isinstance(node, dict):
            if node.get("type") == "object":
                assert node.get("additionalProperties") is False
            for value in node.values():
                assert_named_objects_are_closed(value)
        elif isinstance(node, list):
            for value in node:
                assert_named_objects_are_closed(value)

    assert_named_objects_are_closed(schema)

    boundary = schema["properties"]["readiness_boundary"]["properties"]
    assert boundary["strategy_defined"]["const"] is False
    assert boundary["strategy_run_count"]["const"] == 0
    assert boundary["formal_backtest_authorized"]["const"] is False
    assert boundary["paper_authorized"]["const"] is False
    assert boundary["paper_state"]["const"] == "all_cash"
    assert boundary["paper_positions"]["maxItems"] == 0
    assert boundary["backfilled_trades"]["const"] == 0
    assert boundary["real_money_action_usd"]["const"] == 0
    assert boundary["today_action"]["const"] == "today_no_trade"


def test_schema_freezes_exact_sources_files_and_timestamp_semantics() -> None:
    schema = _load(SCHEMA_PATH)
    properties = schema["properties"]

    source_receipts = properties["source_receipts"]
    assert source_receipts["required"] == SOURCE_TYPES
    assert list(source_receipts["properties"]) == SOURCE_TYPES
    for source_type in SOURCE_TYPES:
        refinement = source_receipts["properties"][source_type]["allOf"][1]["properties"]
        assert refinement["source_type"]["const"] == source_type
        assert refinement["official_entry_url"]["const"].startswith("https://")

    record_contract = properties["normalized_record_contract"]["properties"]
    assert _const_array(record_contract["source_type_values"]) == SOURCE_TYPES
    required_fields = _const_array(record_contract["required_fields"])
    assert required_fields[-9:] == [
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

    timestamp_contract = properties["timestamp_contract"]["properties"]
    assert _const_array(timestamp_contract["required_timestamp_fields"]) == TIMESTAMP_FIELDS
    assert timestamp_contract["known_at_rule"]["const"] == (
        "official_public_timestamp_else_independent_archived_first_seen_else_local_first_"
        "observed"
    )
    assert timestamp_contract["decision_at_rule"]["const"] == (
        "first_official_xnys_close_strictly_after_known_at"
    )
    assert timestamp_contract["trade_at_rule"]["const"] == (
        "next_official_xnys_open_after_decision_at"
    )

    files = properties["files"]
    assert files["required"] == [
        "disclosure_events.jsonl",
        "source_versions.jsonl",
        "identifier_history.csv",
        "trading_calendar.csv",
        "sanitized_summary.json",
    ]
    assert list(files["properties"]) == files["required"]


def test_legal_privacy_coverage_and_sec_access_gates_fail_closed() -> None:
    schema = _load(SCHEMA_PATH)
    receipt = _load(RECEIPT_PATH)

    legal_schema = schema["properties"]["legal_use"]["properties"]
    assert legal_schema["commercial_use_review_status"]["const"] == "approved_for_exact_use"
    assert legal_schema["congress_use_review_status"]["const"] == "approved_for_exact_use"
    assert legal_schema["source_terms_reviewed"]["const"] is True

    sec_schema = schema["properties"]["sec_access"]["properties"]
    assert sec_schema["user_agent_contact_declared"]["const"] is True
    assert sec_schema["sec_policy_ceiling_requests_per_second"]["const"] == 10
    assert sec_schema["configured_requests_per_second"]["maximum"] == 10
    assert sec_schema["global_across_processes_and_machines"]["const"] is True

    coverage_schema = schema["properties"]["coverage"]["properties"]
    assert coverage_schema["complete_period_claimed"]["const"] is False
    assert coverage_schema["twenty_year_coverage_claimed"]["const"] is False
    assert coverage_schema["twenty_year_coverage_validated"]["const"] is False

    privacy_schema = schema["properties"]["privacy_contract"]["properties"]
    assert privacy_schema["raw_data_allowed_in_git_ci_site"]["const"] is False
    assert privacy_schema["actor_salt_allowed_in_git"]["const"] is False
    assert privacy_schema["minimum_distinct_actor_count_for_public_aggregate"]["const"] == 10
    forbidden = _const_array(privacy_schema["public_forbidden_fields"])
    for sensitive in (
        "person_name",
        "street_address",
        "family_member_name",
        "actor_token",
        "ticker",
        "cik",
        "accession_number",
        "source_document_url",
        "raw_document_body",
    ):
        assert sensitive in forbidden

    access = receipt["legal_and_access_state_at_freeze"]
    assert access["congress_exact_use_written_legal_clearance_received"] is False
    assert access["congress_commercial_use_cleared"] is False
    assert access["authorized_collection_allowed"] is False
    privacy = receipt["privacy_state_at_freeze"]
    assert privacy["raw_disclosure_records_fetched"] is False
    assert privacy["raw_disclosure_records_stored"] is False
    assert privacy["personal_data_fetched"] is False
    assert privacy["personal_data_stored"] is False
    assert privacy["normalized_disclosure_rows"] == 0
    assert receipt["coverage_state_at_freeze"]["twenty_year_coverage_claimed"] is False
    assert receipt["coverage_state_at_freeze"]["twenty_year_coverage_validated"] is False


def test_receipt_has_exact_twenty_gate_readiness_and_no_trade_boundary() -> None:
    receipt = _load(RECEIPT_PATH)
    readiness = receipt["actual_disclosure_readiness"]

    assert readiness == {
        "passed": 2,
        "total": 20,
        "all_passed": False,
        "passed_gate_ids": PASSED_GATE_IDS,
        "blocked_gate_ids": BLOCKED_GATE_IDS,
    }
    assert len(PASSED_GATE_IDS) + len(BLOCKED_GATE_IDS) == 20

    boundary = receipt["decision_boundary"]
    assert boundary == {
        "readiness_only": True,
        "strategy_defined": False,
        "strategy_rule_changed": False,
        "strategy_run_count": 0,
        "formal_backtest_authorized": False,
        "formal_backtest_completed": False,
        "paper_authorized": False,
        "paper_state": "all_cash",
        "paper_positions": [],
        "paper_backfilled_trades": 0,
        "orders_created": 0,
        "real_money_action_usd": 0,
        "today_action": "today_no_trade",
    }


def test_protocol_is_explicit_about_source_lag_revisions_and_non_strategy_boundary() -> None:
    protocol = PROTOCOL_PATH.read_text(encoding="utf-8")

    for source_type in SOURCE_TYPES:
        assert f"`{source_type}`" in protocol
    for timestamp in TIMESTAMP_FIELDS:
        assert f"`{timestamp}`" in protocol
    for phrase in (
        "5 U.S.C. § 13107",
        "10 requests/second",
        "嚴格晚於",
        "append-only",
        "twenty_year_coverage_claimed=false",
        "2/20",
        "短線 Paper 維持全現金",
        "實金動作為 **US$0**",
        "今天不下單",
    ):
        assert phrase in protocol

    official_urls = {row["url"] for row in _load(RECEIPT_PATH)["official_sources"]}
    assert "https://disclosures-clerk.house.gov/FinancialDisclosure" in official_urls
    assert "https://efdsearch.senate.gov/search/home/" in official_urls
    assert "https://www.sec.gov/files/form4.pdf" in official_urls
    assert "https://www.sec.gov/files/form13f.pdf" in official_urls
    assert "https://www.sec.gov/about/developer-resources" in official_urls
    assert all(url.startswith("https://") for url in official_urls)
