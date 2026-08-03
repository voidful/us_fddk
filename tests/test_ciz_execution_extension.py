import json
from pathlib import Path

import pandas as pd
import pytest

from scripts.build_short_term_ciz_execution_extension_report import _site_summary
from usfddk.ciz_execution_extension import _calendar_and_signals
from usfddk.ciz_execution_extension_validation import (
    run_ciz_execution_extension_validation,
)

ROOT = Path(__file__).resolve().parents[1]


def test_signal_calendar_does_not_treat_partial_month_as_month_end() -> None:
    calendar = pd.DataFrame(
        {
            "session": [
                "2026-07-30",
                "2026-07-31",
                "2026-08-03",
                "2026-08-31",
                "2026-09-01",
            ]
        }
    )

    _, signals = _calendar_and_signals(calendar, "2026-07-01", "2026-08-03")

    assert [str(day.date()) for day in signals] == ["2026-07-31"]


@pytest.fixture(scope="module")
def result() -> dict:
    return run_ciz_execution_extension_validation(ROOT)


def test_round15_synthetic_extension_passes_all_frozen_controls(result: dict) -> None:
    assert result["status"] == (
        "synthetic_execution_extension_passed_provider_data_still_blocked"
    )
    assert result["control"]["gate_summary"] == {
        "passed": 16,
        "total": 16,
        "all_passed": True,
    }
    assert result["control"]["base_ledger_gate_summary"] == {
        "passed": 20,
        "total": 20,
        "all_passed": True,
    }
    assert [row["id"] for row in result["control"]["gates"]] == [
        f"{index:02d}" for index in range(1, 17)
    ]


def test_round15_preserves_dividend_pay_date_and_history(result: dict) -> None:
    examples = result["control"]["control_examples"]
    assert examples["dividend"]["ex_date"] == "2026-07-30"
    assert examples["dividend"]["pay_date"] == "2026-08-03"
    assert examples["dividend"]["cash_available_date"] == "2026-08-03"
    assert float(examples["dividend"]["cash_per_share"]) == 0.5
    assert examples["minimum_return_sessions"] >= 252
    assert examples["minimum_positive_volume_sessions"] >= 20


def test_round15_preserves_removed_member_until_next_open(result: dict) -> None:
    removal = result["control"]["control_examples"]["removal"]
    assert removal["membership_effective_to"] == "2026-07-16"
    assert removal["signal_session"] == "2026-07-31"
    assert removal["execution_session"] == "2026-08-03"
    assert int(removal["required_sessions"]) == int(removal["observed_sessions"])
    assert float(removal["execution_open_raw"]) > 0


def test_round15_uses_synchronized_qqq_spy_and_frozen_costs(result: dict) -> None:
    assert result["control"]["control_examples"]["benchmark_assets"] == ["QQQ", "SPY"]
    assert result["transform_result"]["strategy_rule_changed"] is False
    assert result["transform_result"]["provider_rows_published"] is False
    assert result["transform_result"]["wrds_queried"] is False


def test_all_sixteen_frozen_attacks_fail_with_exact_codes(result: dict) -> None:
    assert result["attack_summary"] == {
        "rejected": 16,
        "total": 16,
        "all_rejected": True,
    }
    assert all(
        row["rejected"]
        and row["observed_error_code"] == row["expected_error_code"]
        for row in result["attacks"]
    )


def test_round14_evidence_remains_unchanged(result: dict) -> None:
    assert result["round14_execution_accounting"] == {
        "gates": {"passed": 8, "total": 12, "all_passed": False},
        "attacks": {"rejected": 10, "total": 10, "all_rejected": True},
    }


def test_round15_never_promotes_synthetic_rows_to_backtest_or_paper(
    result: dict,
) -> None:
    assert result["actual_point_in_time_readiness"] == {
        "passed": 1,
        "total": 20,
        "all_passed": False,
    }
    assert result["authorized_provider_sample_received"] is False
    assert result["formal_stock_backtest_authorized"] is False
    assert result["formal_stock_backtest_completed"] is False
    assert result["synthetic_rows_only"] is True
    assert result["paper"] == {
        "authorized": False,
        "state": "all_cash",
        "backfilled_trades": 0,
        "positions": [],
    }
    assert result["real_money_action_usd"] == 0


def test_committed_machine_and_site_receipts_match_round15(result: dict) -> None:
    machine = json.loads(
        (
            ROOT / "artifacts/short_term_ciz_execution_extension_validation.json"
        ).read_text(encoding="utf-8")
    )
    site = json.loads(
        (ROOT / "site/data/short-term-ciz-execution-extension.json").read_text(
            encoding="utf-8"
        )
    )

    assert machine == result
    assert site == _site_summary(result)
