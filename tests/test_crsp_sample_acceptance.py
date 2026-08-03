import json
from pathlib import Path

from scripts.build_short_term_crsp_sample_acceptance_report import _site_summary
from usfddk.crsp_sample_acceptance import run_crsp_sample_acceptance_rehearsal

ROOT = Path(__file__).resolve().parents[1]


def test_control_passes_but_all_twelve_frozen_attacks_are_rejected() -> None:
    result = run_crsp_sample_acceptance_rehearsal(ROOT)

    assert result["protocol_integrity"]["passed"] is True
    assert result["control"]["gate_summary"] == {
        "passed": 20,
        "total": 20,
        "all_passed": True,
    }
    assert result["attack_summary"] == {
        "rejected": 12,
        "total": 12,
        "all_rejected": True,
    }
    assert all(attack["rejected"] for attack in result["attacks"])


def test_harness_result_cannot_promote_provider_backtest_or_paper() -> None:
    result = run_crsp_sample_acceptance_rehearsal(ROOT)

    assert result["status"] == "acceptance_harness_passed_provider_data_still_blocked"
    assert result["actual_point_in_time_readiness"] == {
        "passed": 1,
        "total": 20,
        "all_passed": False,
    }
    assert result["actual_provider_bundle_present"] is False
    assert result["wrds_catalog_queried"] is False
    assert result["authorized_provider_sample_received"] is False
    assert result["provider_qualified"] is False
    assert result["formal_stock_backtest_authorized"] is False
    assert result["formal_stock_backtest_completed"] is False
    assert result["strategy_rule_changed"] is False
    assert result["paper"] == {
        "authorized": False,
        "state": "all_cash",
        "backfilled_trades": 0,
        "positions": [],
    }
    assert result["real_money_action_usd"] == 0


def test_sample_request_keeps_full_twenty_year_contract_and_exit_edge_cases() -> None:
    request = run_crsp_sample_acceptance_rehearsal(ROOT)["sample_request"]

    assert request["formal_coverage_unchanged"] == {
        "start": "2006-08-01",
        "end": "2026-07-31",
        "minimum_member_price_coverage": 0.995,
        "required_daily_member_range": [495, 510],
        "all_twenty_gates_required": True,
    }
    assert "有效退市回報" in request["required_edge_cases"]
    assert "缺失退市回報" in request["required_edge_cases"]
    assert "換股收購" in request["required_edge_cases"]
    assert "歷史分類變更" in request["required_edge_cases"]


def test_committed_machine_and_site_receipts_match_the_frozen_rehearsal() -> None:
    result = run_crsp_sample_acceptance_rehearsal(ROOT)
    machine_receipt = json.loads(
        (ROOT / "artifacts/short_term_crsp_sample_acceptance.json").read_text(
            encoding="utf-8"
        )
    )
    site_receipt = json.loads(
        (ROOT / "site/data/short-term-crsp-sample-acceptance.json").read_text(
            encoding="utf-8"
        )
    )

    assert machine_receipt == result
    assert site_receipt == _site_summary(result)
