from __future__ import annotations

from pathlib import Path

from usfddk.french_prior_return_contract import audit_frozen_prior_return_archives

ROOT = Path(__file__).resolve().parents[1]


def test_first_download_fails_closed_before_numeric_strategy_calculation() -> None:
    result = audit_frozen_prior_return_archives(ROOT)

    assert result["passed_check_count"] == 6
    assert result["required_check_count"] == 8
    assert result["checks"]["short_term_exact_value_weighted_monthly_marker"] is False
    assert result["checks"]["long_term_exact_value_weighted_monthly_marker"] is False
    assert result["numeric_return_rows_parsed"] is False
    assert result["strategy_calculation_started"] is False
    assert result["redownload_permitted"] is False


def test_failed_contract_cannot_create_paper_or_real_money_action() -> None:
    result = audit_frozen_prior_return_archives(ROOT)

    assert result["status"].endswith("failed_before_strategy_calculation")
    assert result["decision_boundary"] == {
        "academic_result_available": False,
        "paper_eligible": False,
        "paper_state_created": False,
        "trade_ready": False,
        "real_money_action_usd": 0,
    }
