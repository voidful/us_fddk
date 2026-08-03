import json
import tempfile
from pathlib import Path

import pandas as pd

from scripts.build_short_term_crsp_ciz_mapping_report import _site_summary
from usfddk.crsp_ciz_adapter import transform_crsp_ciz_bundle
from usfddk.crsp_ciz_mapping_validation import (
    CONTROL_REQUIREMENTS,
    _mutate_table,
    _write_control_bundle,
    run_crsp_ciz_mapping_validation,
)
from usfddk.point_in_time_ledger import audit_point_in_time_bundle

ROOT = Path(__file__).resolve().parents[1]


def test_synthetic_ciz_control_maps_and_passes_all_twenty_ledger_gates() -> None:
    result = run_crsp_ciz_mapping_validation(ROOT)

    assert result["protocol_integrity"]["passed"] is True
    assert result["control"] == {
        "synthetic_only": True,
        "contains_provider_rows": False,
        "mapping_completed": True,
        "ledger_gate_summary": {
            "passed": 20,
            "total": 20,
            "all_passed": True,
        },
        "paper_authorized": False,
    }


def test_all_twelve_frozen_mapping_attacks_fail_with_designated_codes() -> None:
    result = run_crsp_ciz_mapping_validation(ROOT)

    assert result["attack_summary"] == {
        "rejected": 12,
        "total": 12,
        "all_rejected": True,
    }
    assert all(
        attack["rejected"]
        and attack["observed_error_code"] == attack["expected_error_code"]
        for attack in result["attacks"]
    )


def test_mapping_never_promotes_true_readiness_backtest_or_paper() -> None:
    result = run_crsp_ciz_mapping_validation(ROOT)

    assert result["status"] == "ciz_mapping_bridge_passed_provider_data_still_blocked"
    assert result["actual_point_in_time_readiness"] == {
        "passed": 1,
        "total": 20,
        "all_passed": False,
    }
    assert result["authorized_provider_sample_received"] is False
    assert result["wrds_catalog_queried"] is False
    assert result["provider_qualified"] is False
    assert result["formal_stock_backtest_authorized"] is False
    assert result["formal_stock_backtest_completed"] is False
    assert result["paper"] == {
        "authorized": False,
        "state": "all_cash",
        "backfilled_trades": 0,
        "positions": [],
    }
    assert result["real_money_action_usd"] == 0


def test_delisting_storage_row_is_not_exported_as_a_trade_or_exit_date() -> None:
    with tempfile.TemporaryDirectory(prefix="usfddk-ciz-test-") as temporary:
        temp = Path(temporary)
        source = _write_control_bundle(temp / "source")
        output = temp / "ledger"
        mapping = transform_crsp_ciz_bundle(source, output, root=ROOT)

        prices = pd.read_csv(output / "daily_prices.csv", dtype=str, keep_default_na=False)
        outcomes = pd.read_csv(
            output / "security_outcomes.csv", dtype=str, keep_default_na=False
        )
        exited_prices = prices[prices["security_id"] == "CRSP-PERMNO-10001"]
        exited_outcome = outcomes[
            outcomes["security_id"] == "CRSP-PERMNO-10001"
        ].iloc[0]

        assert list(exited_prices["session"]) == ["2026-07-29", "2026-07-30"]
        assert exited_outcome["last_trade_date"] == "2026-07-30"
        assert exited_outcome["exit_effective_date"] == "2026-07-31"
        assert mapping["delisting_storage_dates_used_as_exit_dates"] is False
        assert mapping["missing_delisting_returns_imputed"] is False


def test_missing_delret_can_only_pass_with_traceable_cash_terms() -> None:
    with tempfile.TemporaryDirectory(prefix="usfddk-ciz-cash-exit-") as temporary:
        temp = Path(temporary)
        source = _write_control_bundle(temp / "source")

        def clear_delret(frame: pd.DataFrame) -> None:
            frame.loc[0, "DelRet"] = ""
            frame.loc[0, "DelRetMissType"] = "MP"

        def add_cash_terms(frame: pd.DataFrame) -> None:
            frame.loc[0, "OutcomeType"] = "acquired_cash"
            frame.loc[0, "CashConsideration"] = "50"

        def normalize_cash_action(frame: pd.DataFrame) -> None:
            frame.loc[0, "EventType"] = "merger_cash"
            frame.loc[0, "CashAmount"] = "50"

        def mark_storage_return_missing(frame: pd.DataFrame) -> None:
            row = (frame["PERMNO"] == "10001") & (frame["DlyCalDt"] == "2026-07-31")
            frame.loc[row, "DlyRet"] = ""
            frame.loc[row, "DlyRetMissFlg"] = "MP"

        _mutate_table(source, "stk_delists.csv", clear_delret)
        _mutate_table(source, "exit_terms.csv", add_cash_terms)
        _mutate_table(source, "corporate_action_overlay.csv", normalize_cash_action)
        _mutate_table(source, "stk_dly_security_data.csv", mark_storage_return_missing)

        output = temp / "ledger"
        transform_crsp_ciz_bundle(source, output, root=ROOT)
        audit = audit_point_in_time_bundle(
            output, root=ROOT, requirements=CONTROL_REQUIREMENTS
        )
        outcome = pd.read_csv(
            output / "security_outcomes.csv", dtype=str, keep_default_na=False
        ).query("security_id == 'CRSP-PERMNO-10001'").iloc[0]

        assert audit["gate_summary"] == {
            "passed": 20,
            "total": 20,
            "all_passed": True,
        }
        assert outcome["delisting_return"] == ""
        assert outcome["cash_consideration"] == "50.0"


def test_committed_machine_and_site_receipts_match_round_thirteen() -> None:
    result = run_crsp_ciz_mapping_validation(ROOT)
    machine = json.loads(
        (ROOT / "artifacts/short_term_crsp_ciz_mapping_validation.json").read_text(
            encoding="utf-8"
        )
    )
    site = json.loads(
        (ROOT / "site/data/short-term-crsp-ciz-mapping.json").read_text(
            encoding="utf-8"
        )
    )

    assert machine == result
    assert site == _site_summary(result)
