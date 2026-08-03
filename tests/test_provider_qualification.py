from __future__ import annotations

import json
from pathlib import Path

from scripts.build_short_term_provider_qualification_report import _site_summary
from usfddk.provider_qualification import (
    DOMAIN_REPAIR_PROTOCOL_SHA256,
    EXPECTED_PROVIDER_IDS,
    GATE_KEYS,
    PROTOCOL_SHA256,
    build_provider_qualification,
)

ROOT = Path(__file__).resolve().parents[1]


def test_original_protocol_and_schema_informed_domain_repair_are_preserved() -> None:
    result = build_provider_qualification(ROOT)
    preregistration = result["preregistration"]

    assert preregistration["original_protocol_frozen_before_document_review"] is True
    assert preregistration["original_protocol_sha256"] == PROTOCOL_SHA256
    assert preregistration["original_domain_scope_failed"] is True
    assert preregistration["domain_repair_frozen_after_redirect_inspection"] is True
    assert preregistration["domain_repair_sha256"] == DOMAIN_REPAIR_PROTOCOL_SHA256
    assert preregistration["independent_first_seen_evidence"] is False
    assert preregistration["provider_set_changed"] is False
    assert preregistration["twenty_gate_mapping_changed"] is False
    assert preregistration["strategy_rule_changed"] is False


def test_all_four_frozen_provider_paths_have_exactly_twenty_gates() -> None:
    result = build_provider_qualification(ROOT)

    assert tuple(provider["id"] for provider in result["providers"]) == EXPECTED_PROVIDER_IDS
    for provider in result["providers"]:
        assert tuple(provider["gates"]) == GATE_KEYS
        assert sum(provider["status_counts"].values()) == 20
        assert provider["locally_verified"] is False
        assert provider["contract_passed"] is False
        assert provider["procurement_minimum_passed"] is False
        assert provider["formal_backtest_authorized"] is False
        assert provider["paper_authorized"] is False


def test_document_support_counts_are_fixed_and_do_not_become_contract_scores() -> None:
    result = build_provider_qualification(ROOT)
    providers = {provider["id"]: provider for provider in result["providers"]}

    assert providers["crsp_wrds"]["status_counts"] == {
        "documented": 10,
        "partial": 2,
        "not_documented": 1,
        "unresolved_login_required": 0,
        "not_applicable_until_import": 7,
    }
    assert providers["norgate_data"]["status_counts"] == {
        "documented": 6,
        "partial": 4,
        "not_documented": 3,
        "unresolved_login_required": 0,
        "not_applicable_until_import": 7,
    }
    assert providers["nasdaq_data_link_sharadar"]["status_counts"] == {
        "documented": 0,
        "partial": 1,
        "not_documented": 2,
        "unresolved_login_required": 10,
        "not_applicable_until_import": 7,
    }
    assert providers["polygon_io_stocks"]["status_counts"] == {
        "documented": 4,
        "partial": 6,
        "not_documented": 3,
        "unresolved_login_required": 0,
        "not_applicable_until_import": 7,
    }


def test_crsp_is_only_a_first_enquiry_and_norgate_fails_standalone_contract() -> None:
    result = build_provider_qualification(ROOT)
    providers = {provider["id"]: provider for provider in result["providers"]}
    crsp = providers["crsp_wrds"]
    norgate = providers["norgate_data"]

    assert result["first_enquiry"]["provider_id"] == "crsp_wrds"
    assert result["first_enquiry"]["qualified"] is False
    assert crsp["gates"]["07_membership_availability"]["status"] == "not_documented"
    assert crsp["gates"]["16_permanent_exit_economics"]["status"] == "partial"
    assert norgate["gates"]["06_identifier_history"]["status"] == "partial"
    assert norgate["gates"]["07_membership_availability"]["status"] == "not_documented"
    assert norgate["gates"]["14_corporate_actions"]["status"] == "partial"
    assert norgate["gates"]["16_permanent_exit_economics"]["status"] == (
        "not_documented"
    )


def test_real_readiness_backtest_paper_and_money_remain_closed() -> None:
    result = build_provider_qualification(ROOT)

    assert result["status"] == "no_single_provider_preflight_qualified"
    assert result["actual_point_in_time_readiness"] == {
        "passed": 1,
        "total": 20,
        "all_passed": False,
        "status": "blocked_by_point_in_time_data_contract",
    }
    assert result["formal_stock_backtest_authorized"] is False
    assert result["formal_stock_backtest_completed"] is False
    assert result["paper"] == {
        "authorized": False,
        "state": "all_cash",
        "backfilled_trades": 0,
        "positions": [],
    }
    assert result["real_money_action_usd"] == 0


def test_published_machine_outputs_match_the_reproducible_builder() -> None:
    result = build_provider_qualification(ROOT)
    validation = json.loads(
        (ROOT / "artifacts/short_term_provider_qualification.json").read_text(
            encoding="utf-8"
        )
    )
    site_data = json.loads(
        (ROOT / "site/data/short-term-provider-qualification.json").read_text(
            encoding="utf-8"
        )
    )

    assert validation == result
    assert site_data == _site_summary(result)


def test_report_states_new_negative_evidence_without_promotion() -> None:
    report = (ROOT / "docs/SHORT_TERM_PROVIDER_QUALIFICATION_REPORT.md").read_text(
        encoding="utf-8"
    )

    assert "沒有單一來源通過採購前最低條件" in report
    assert "不提供 delisting return" in report
    assert "CRSP／WRDS 是首選查詢對象，但不是已通過" in report
    assert "正式 20 年逐股回測 0 次" in report
    assert "實金動作 US$0" in report
