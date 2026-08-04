from __future__ import annotations

import json
from pathlib import Path

from scripts.build_short_term_provider_convergence_report import _site_summary
from usfddk.provider_convergence import (
    DIRECT_STOCK_CAPABILITIES,
    OVERLAY_CAPABILITIES,
    PROTOCOL_SHA256,
    STOCK_GUIDE,
    TREASURY_GUIDE,
    frozen_convergence_record,
    inspect_provider_guides,
    validate_provider_convergence,
)
from usfddk.provider_convergence_validation import (
    run_provider_convergence_validation,
)

ROOT = Path(__file__).resolve().parents[1]


def test_protocol_and_frozen_record_integrity() -> None:
    receipt = json.loads(
        (
            ROOT / "artifacts/short_term_provider_convergence_protocol_receipt.json"
        ).read_text(encoding="utf-8")
    )
    validation = validate_provider_convergence(
        frozen_convergence_record(), root=ROOT
    )

    assert receipt["protocol"]["sha256"] == PROTOCOL_SHA256
    assert receipt["status"] == (
        "frozen_after_official_guide_inspection_before_convergence_implementation"
    )
    assert receipt["convergence_implementation_present_at_freeze"] is False
    assert receipt["convergence_output_present_at_freeze"] is False
    assert receipt["strategy_run_count"] == 0
    assert receipt["paper_state"] == "all_cash"
    assert validation["passed"] is True
    assert validation["protocol_integrity"]["passed"] is True


def test_capability_matrix_preserves_five_direct_and_five_overlay_inputs() -> None:
    result = run_provider_convergence_validation(ROOT)
    matrix = result["capability_matrix"]

    assert matrix["requested_input_count"] == 10
    assert matrix["direct_documented_count"] == 5
    assert matrix["overlay_required_count"] == 5
    assert matrix["direct"] == DIRECT_STOCK_CAPABILITIES
    assert matrix["overlay_required"] == OVERLAY_CAPABILITIES
    assert matrix["direct"]["stk_ind_membership.csv"] == (
        "direct_effective_interval_only"
    )
    assert matrix["overlay_required"]["membership_announcements.csv"] == (
        "evidence_overlay_required"
    )


def test_all_twelve_controls_and_attacks_hit_exact_codes() -> None:
    result = run_provider_convergence_validation(ROOT)

    assert result["control_summary"] == {
        "passed": 12,
        "total": 12,
        "all_passed": True,
    }
    assert result["attack_summary"] == {
        "rejected": 12,
        "total": 12,
        "all_rejected": True,
    }
    assert all(
        row["observed_error_code"] == row["expected_error_code"]
        for row in result["attacks"]
    )


def test_treasury_mapping_rejects_tenor_and_unit_substitution() -> None:
    treasury = run_provider_convergence_validation(ROOT)["treasury"]

    assert treasury["individual_issue_daily_unadjusted_return_field"] == "TDRETNUA"
    assert treasury["daily_rf_tenors"] == ["4_week", "13_week", "26_week"]
    assert treasury["daily_4_week_treasnox"] == 2_000_061
    assert treasury["exact_1_month_series"] == {
        "treasnox": 2_000_001,
        "frequency": "monthly",
        "unit": "continuously_compounded_yield",
    }
    assert treasury["same_provider_mapping_status"] == (
        "same_provider_mapping_candidate_not_formal_rf"
    )
    assert treasury["four_week_used_as_one_month_daily"] is False
    assert treasury["annual_yield_divided_by_252"] is False
    assert treasury["formal_rf_manifest_generated"] is False


def test_formal_paper_and_real_money_boundaries_remain_closed() -> None:
    result = run_provider_convergence_validation(ROOT)

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


def test_live_guide_probe_matches_frozen_identity_but_never_self_qualifies() -> None:
    artifact = json.loads(
        (
            ROOT / "artifacts/short_term_provider_guide_probe.json"
        ).read_text(encoding="utf-8")
    )
    site_data = json.loads(
        (
            ROOT / "site/data/short-term-provider-guide-probe.json"
        ).read_text(encoding="utf-8")
    )

    assert artifact == site_data
    assert artifact["status"] == "matches_frozen_guides"
    assert artifact["all_match_frozen_guides"] is True
    assert artifact["observations"]["stock_ciz"]["pdf_sha256"] == (
        STOCK_GUIDE["pdf_sha256"]
    )
    assert artifact["observations"]["treasury"]["pdf_sha256"] == (
        TREASURY_GUIDE["pdf_sha256"]
    )
    assert artifact["new_guide_qualified"] is False
    assert artifact["provider_package_qualified"] is False
    assert artifact["formal_rf_input_ready"] is False
    assert artifact["formal_backtest_authorized"] is False
    assert artifact["strategy_run_count"] == 0
    assert artifact["paper_authorized"] is False
    assert artifact["paper_state"] == "all_cash"
    assert artifact["real_money_action_usd"] == 0


def test_changed_guide_is_unqualified_and_cannot_open_any_gate() -> None:
    result = inspect_provider_guides(
        stock_landing_html=(
            f"{STOCK_GUIDE['title']} 2026-07-28 "
            "6a70fc12f1246457e16fbfad"
        ),
        stock_pdf_bytes=b"%PDF-1.7\n/Type/Page>>\n",
        treasury_landing_html=(
            f"{TREASURY_GUIDE['title']} 2026-06-30 "
            "6a454eb24453862570c90c07"
        ),
        treasury_pdf_bytes=b"%PDF-1.7\n/Type/Page>>\n",
    )

    assert result["status"] == "unqualified_new_guide"
    assert result["all_match_frozen_guides"] is False
    assert result["new_guide_qualified"] is False
    assert result["provider_package_qualified"] is False
    assert result["formal_backtest_authorized"] is False
    assert result["paper_authorized"] is False
    assert result["real_money_action_usd"] == 0


def test_published_outputs_match_reproducible_builder() -> None:
    result = run_provider_convergence_validation(ROOT)
    artifact = json.loads(
        (
            ROOT / "artifacts/short_term_provider_convergence_validation.json"
        ).read_text(encoding="utf-8")
    )
    site_data = json.loads(
        (
            ROOT / "site/data/short-term-provider-convergence.json"
        ).read_text(encoding="utf-8")
    )

    assert artifact == result
    assert site_data == _site_summary(result)


def test_report_is_conclusion_first_and_non_promotional() -> None:
    report = (
        ROOT / "docs/SHORT_TERM_PROVIDER_CONVERGENCE_REPORT.md"
    ).read_text(encoding="utf-8")

    assert "**5/10 份有直接資料字典能力**" in report
    assert "**5/10 份仍須供應商或獨立" in report
    assert "十二項單一\n錯誤攻擊 **12/12 全部拒收**" in report
    assert "真實正式就緒仍為 **1/18**" in report
    assert "正式策略運行 **0 次**" in report
    assert "短線 Paper 全現金" in report
    assert "實金\n動作 **US$0**" in report
    assert "不構成數據供應商背書、投資建議、回報預測或盈利保證" in report
