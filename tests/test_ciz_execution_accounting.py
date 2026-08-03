import json
from pathlib import Path

import pytest

from scripts.build_short_term_ciz_execution_accounting_report import _site_summary
from usfddk.ciz_execution_accounting import (
    ExecutionAccountingError,
    apply_split_once,
    credit_dividend_cash,
    require_next_open_execution,
    run_ciz_execution_accounting_validation,
    settle_cash_exit,
    settle_delisting_return,
    settle_stock_exit,
)

ROOT = Path(__file__).resolve().parents[1]


def test_round14_protocol_and_control_accounting_are_reproducible() -> None:
    result = run_ciz_execution_accounting_validation(ROOT)

    assert result["protocol_integrity"]["passed"] is True
    assert result["accounting_controls"] == {
        "delisting_last_value": 100.0,
        "delisting_return": -0.5,
        "delisting_terminal_value_once": 50.0,
        "cash_exit_shares": 2.0,
        "cash_consideration_per_share": 50.0,
        "cash_exit_terminal_value": 100.0,
        "stock_exit_old_shares": 4.0,
        "stock_exit_ratio": 0.5,
        "stock_exit_successor_shares": 2.0,
        "split_before_value": 100.0,
        "split_after_value": 100.0,
        "spinoff_successor_shares": 1.0,
    }


def test_round14_finds_exactly_four_formal_execution_input_gaps() -> None:
    result = run_ciz_execution_accounting_validation(ROOT)
    passed = {row["id"] for row in result["gates"] if row["passed"]}
    failed = {row["id"] for row in result["gates"] if not row["passed"]}

    assert result["gate_summary"] == {"passed": 8, "total": 12, "all_passed": False}
    assert passed == {"01", "02", "03", "04", "05", "06", "08", "12"}
    assert failed == {"07", "09", "10", "11"}
    assert result["unresolved_execution_inputs"] == [
        "派息權利與付款分離",
        "訊號前歷史覆蓋",
        "移除後成交覆蓋",
        "公平基準同步",
    ]


def test_all_ten_frozen_execution_attacks_fail_with_exact_codes() -> None:
    result = run_ciz_execution_accounting_validation(ROOT)

    assert result["attack_summary"] == {
        "rejected": 10,
        "total": 10,
        "all_rejected": True,
    }
    assert all(
        row["rejected"]
        and row["observed_error_code"] == row["expected_error_code"]
        for row in result["attacks"]
    )


def test_once_only_terminal_accounting_examples() -> None:
    assert settle_delisting_return(
        100.0,
        -0.5,
        apply_storage_return=False,
        apply_outcome_return=True,
    ) == 50.0
    assert settle_cash_exit(
        last_value=100.0,
        shares=2.0,
        delisting_return=None,
        cash_consideration=50.0,
        apply_return=False,
        apply_cash=True,
    ) == 100.0
    assert settle_stock_exit(4.0, "CRSP-PERMNO-10002", 0.5) == (
        "CRSP-PERMNO-10002",
        2.0,
    )
    assert apply_split_once(
        shares=1.0,
        pre_split_price=100.0,
        share_ratio=2.0,
        post_split_price=50.0,
        apply_ratio_to_shares=True,
        apply_ratio_as_return=False,
    ) == {"before_value": 100.0, "after_shares": 2.0, "after_value": 100.0}


def test_early_dividend_and_same_day_execution_fail_closed() -> None:
    with pytest.raises(ExecutionAccountingError) as dividend_error:
        credit_dividend_cash(
            shares=10.0,
            cash_per_share=0.5,
            ex_date="2026-07-30",
            pay_date="2026-08-03",
            credit_date="2026-07-30",
        )
    assert dividend_error.value.code == "dividend_cash_available_early"

    with pytest.raises(ExecutionAccountingError) as clock_error:
        require_next_open_execution(
            signal_date="2026-07-29",
            execution_date="2026-07-29",
            sessions=["2026-07-29", "2026-07-30"],
            open_price=100.0,
        )
    assert clock_error.value.code == "execution_clock_violation"


def test_round14_never_promotes_backtest_paper_or_real_money() -> None:
    result = run_ciz_execution_accounting_validation(ROOT)

    assert result["status"] == "execution_accounting_controls_passed_formal_inputs_incomplete"
    assert result["actual_point_in_time_readiness"] == {
        "passed": 1,
        "total": 20,
        "all_passed": False,
    }
    assert result["authorized_provider_sample_received"] is False
    assert result["formal_stock_backtest_authorized"] is False
    assert result["formal_stock_backtest_completed"] is False
    assert result["paper"] == {
        "authorized": False,
        "state": "all_cash",
        "backfilled_trades": 0,
        "positions": [],
    }
    assert result["real_money_action_usd"] == 0


def test_committed_machine_and_site_receipts_match_round14() -> None:
    result = run_ciz_execution_accounting_validation(ROOT)
    machine = json.loads(
        (ROOT / "artifacts/short_term_ciz_execution_accounting_validation.json").read_text(
            encoding="utf-8"
        )
    )
    site = json.loads(
        (ROOT / "site/data/short-term-ciz-execution-accounting.json").read_text(
            encoding="utf-8"
        )
    )

    assert machine == result
    assert site == _site_summary(result)
