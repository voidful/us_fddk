from __future__ import annotations

import json
from pathlib import Path

from scripts.build_short_term_provider_gap_closure_report import _site_summary
from scripts.probe_short_term_provider_gap_sources import (
    PROBE_IDENTITIES,
    inspect_current_sources,
)
from usfddk.provider_gap_closure import (
    CANDIDATE_ROUTE_IDS,
    CAPABILITY_IDS,
    PRIMARY_SOURCES,
    PROTOCOL_SHA256,
    frozen_gap_closure_record,
    validate_provider_gap_closure,
)
from usfddk.provider_gap_closure_validation import (
    run_provider_gap_closure_validation,
)

ROOT = Path(__file__).resolve().parents[1]


def test_round21_protocol_receipt_and_parent_hashes_are_intact() -> None:
    receipt = json.loads(
        (ROOT / "artifacts/short_term_provider_gap_closure_protocol_receipt.json").read_text(
            encoding="utf-8"
        )
    )
    validation = validate_provider_gap_closure(frozen_gap_closure_record(), root=ROOT)

    assert receipt["protocol"]["sha256"] == PROTOCOL_SHA256
    assert receipt["new_candidate_provider_evidence_inspected_at_freeze"] is False
    assert receipt["gap_closure_implementation_present_at_freeze"] is False
    assert receipt["strategy_run_count"] == 0
    assert receipt["paper_state"] == "all_cash"
    assert validation["passed"] is True
    assert validation["protocol_integrity"]["passed"] is True


def test_five_routes_use_the_same_fourteen_capabilities() -> None:
    result = run_provider_gap_closure_validation(ROOT)

    assert [row["id"] for row in result["routes"]] == CANDIDATE_ROUTE_IDS
    assert result["required_capability_ids"] == CAPABILITY_IDS
    assert len(result["routes"]) == 5
    assert len(CAPABILITY_IDS) == 14
    for route in result["routes"]:
        assert list(route["capabilities"]) == CAPABILITY_IDS
        assert sum(route["status_counts"].values()) == 14
        assert route["qualified"] is False


def test_public_evidence_scores_are_conservative_and_reproducible() -> None:
    result = run_provider_gap_closure_validation(ROOT)
    rows = {row["id"]: row for row in result["route_summary"]}

    assert result["best_documented_route"] == {
        "id": "crsp_spdj_composite",
        "name": "CRSP Stock CIZ＋S&P DJI 事件＋CRSP Treasury",
        "explicit_count": 5,
        "partial_count": 5,
        "hard_gap_count": 9,
    }
    assert rows["crsp_spdj_composite"]["status_counts"] == {
        "explicit_primary_documentation": 5,
        "partial_primary_documentation": 5,
        "contradicted_by_primary_documentation": 1,
        "unresolved_primary_documentation": 3,
        "validated_authorized_sample": 0,
        "qualified_provider_package": 0,
    }
    spgmi = next(row for row in result["routes"] if row["id"] == "sp_global_market_intelligence")
    assert spgmi["capabilities"]["point_in_time_sp500_membership"]["status"] == (
        "contradicted_by_primary_documentation"
    )
    assert result["qualified_route_count"] == 0


def test_all_fifteen_controls_and_attacks_hit_exact_codes() -> None:
    result = run_provider_gap_closure_validation(ROOT)

    assert result["control_summary"] == {
        "passed": 15,
        "total": 15,
        "all_passed": True,
    }
    assert result["attack_summary"] == {
        "rejected": 15,
        "total": 15,
        "all_rejected": True,
    }
    assert all(
        row["observed_error_code"] == row["expected_error_code"] for row in result["attacks"]
    )


def test_formal_paper_and_real_money_boundaries_remain_closed() -> None:
    result = run_provider_gap_closure_validation(ROOT)

    assert result["actual_formal_readiness"] == {
        "passed": 1,
        "total": 18,
        "all_passed": False,
        "only_passed_gate": "01_preregistration_integrity",
    }
    assert result["authorized_provider_package_received"] is False
    assert result["complete_risk_free_package_received"] is False
    assert result["formal_stock_backtest_input_ready"] is False
    assert result["formal_stock_backtest_completed"] is False
    assert result["strategy_run_count"] == 0
    assert result["paper"] == {
        "authorized": False,
        "state": "all_cash",
        "backfilled_trades": 0,
        "positions": [],
    }
    assert result["real_money_action_usd"] == 0


def test_live_source_probe_matches_identities_but_never_qualifies() -> None:
    artifact = json.loads(
        (ROOT / "artifacts/short_term_provider_gap_source_probe.json").read_text(encoding="utf-8")
    )
    site_data = json.loads(
        (ROOT / "site/data/short-term-provider-gap-source-probe.json").read_text(encoding="utf-8")
    )

    assert artifact == site_data
    assert artifact["all_match_frozen_identities"] is True
    assert artifact["source_identity_count"] == 5
    assert artifact["new_source_qualified"] is False
    assert artifact["provider_package_qualified"] is False
    assert artifact["formal_backtest_authorized"] is False
    assert artifact["paper_authorized"] is False
    assert artifact["paper_state"] == "all_cash"
    assert artifact["real_money_action_usd"] == 0


def test_changed_source_identity_requires_review_and_opens_no_gate() -> None:
    downloaded = {
        source_id: (
            PRIMARY_SOURCES[source_id]["url"],
            probe["marker"],
        )
        for source_id, probe in PROBE_IDENTITIES.items()
    }
    downloaded["factset_benchmarks"] = (
        "https://example.com/not-factset",
        PROBE_IDENTITIES["factset_benchmarks"]["marker"],
    )
    result = inspect_current_sources(downloaded)

    assert result["status"] == "manual_review_required"
    assert result["all_match_frozen_identities"] is False
    assert result["new_source_qualified"] is False
    assert result["provider_package_qualified"] is False
    assert result["formal_backtest_authorized"] is False
    assert result["paper_authorized"] is False
    assert result["real_money_action_usd"] == 0


def test_published_outputs_match_reproducible_builder() -> None:
    result = run_provider_gap_closure_validation(ROOT)
    artifact = json.loads(
        (ROOT / "artifacts/short_term_provider_gap_closure_validation.json").read_text(
            encoding="utf-8"
        )
    )
    site_data = json.loads(
        (ROOT / "site/data/short-term-provider-gap-closure.json").read_text(encoding="utf-8")
    )

    assert artifact == result
    assert site_data == _site_summary(result)


def test_report_is_conclusion_first_detailed_and_non_promotional() -> None:
    report = (ROOT / "docs/SHORT_TERM_PROVIDER_GAP_CLOSURE_REPORT.md").read_text(encoding="utf-8")

    assert "**五條固定路徑沒有一條合格。**" in report
    assert "**5/14 明確" in report
    assert "十五項單一\n替代攻擊 **15/15 全部拒收**" in report
    assert "真實正式就緒仍為\n**1/18**" in report
    assert "正式策略運行 **0 次**" in report
    assert "短線 Paper **全現金**" in report
    assert "實金動作 **US$0**" in report
    assert "Point In Time: No" in report
    assert "盈利保證" in report
