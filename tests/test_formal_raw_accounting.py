from __future__ import annotations

import pandas as pd
import pytest

from usfddk.formal_execution_schedule import ExecutionInstruction
from usfddk.formal_raw_accounting import (
    FormalRawAccountingError,
    run_raw_accounting,
)

SESSIONS = pd.DatetimeIndex(
    [
        "2026-01-02",
        "2026-01-05",
        "2026-01-06",
        "2026-01-07",
        "2026-01-08",
    ]
)


def _prices(rows: list[tuple[str, str, float, float]]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "security_id": security_id,
                "session": session,
                "open_raw": open_price,
                "close_raw": close_price,
                "source_status": "observed",
            }
            for security_id, session, open_price, close_price in rows
        ]
    )


def _actions(rows: list[dict[str, object]]) -> pd.DataFrame:
    columns = [
        "event_id",
        "security_id",
        "event_type",
        "announced_at",
        "ex_date",
        "effective_date",
        "cash_amount",
        "share_ratio",
        "successor_security_id",
        "source_record_id",
    ]
    return pd.DataFrame(rows, columns=columns)


def _outcomes(rows: list[dict[str, object]]) -> pd.DataFrame:
    columns = [
        "source_record_id",
        "security_id",
        "membership_effective_to",
        "outcome_type",
        "last_trade_date",
        "exit_effective_date",
        "delisting_return",
        "cash_consideration",
        "successor_security_id",
        "reason_code",
        "known_at",
    ]
    return pd.DataFrame(rows, columns=columns)


def _entitlements(rows: list[dict[str, object]]) -> pd.DataFrame:
    columns = [
        "event_id",
        "security_id",
        "announced_at",
        "ex_date",
        "pay_date",
        "cash_available_date",
        "cash_per_share",
        "source_record_id",
    ]
    return pd.DataFrame(rows, columns=columns)


def _instruction(day: str, **targets: float) -> ExecutionInstruction:
    return ExecutionInstruction(
        signal_session=pd.Timestamp(day) - pd.Timedelta(days=1),
        execution_session=pd.Timestamp(day),
        targets=targets,
    )


def test_raw_account_uses_open_for_fills_and_close_for_valuation() -> None:
    prices = _prices(
        [
            ("A", "2026-01-02", 100.0, 110.0),
            ("A", "2026-01-05", 120.0, 130.0),
            ("A", "2026-01-06", 125.0, 125.0),
            ("QQQ", "2026-01-02", 200.0, 200.0),
            ("QQQ", "2026-01-05", 210.0, 220.0),
            ("QQQ", "2026-01-06", 215.0, 215.0),
            ("QQQ", "2026-01-07", 215.0, 215.0),
            ("QQQ", "2026-01-08", 215.0, 215.0),
        ]
    )
    result = run_raw_accounting(
        sessions=SESSIONS,
        prices=prices,
        instructions=(_instruction("2026-01-02", A=1.0), _instruction("2026-01-05", QQQ=1.0)),
    )

    assert list(result.trades["side"]) == ["buy", "sell", "buy"]
    assert result.trades.iloc[0]["open_raw"] == 100.0
    # The first close is US$110, not the fill price.  The raw account also
    # deducts both sides' 10 bp costs rather than applying an adjusted factor.
    assert result.equity_curve.iloc[0]["positions_value"] > 1_000.0
    assert set(result.equity_curve.iloc[-1]["holdings"]) == {"QQQ"}
    assert result.policy["paper_authorized"] is False


def test_dividend_is_receivable_on_ex_date_and_cash_only_on_pay_date() -> None:
    prices = _prices(
        [
            ("A", "2026-01-02", 100.0, 100.0),
            ("A", "2026-01-05", 99.0, 99.0),
            ("A", "2026-01-06", 99.0, 99.0),
        ]
    )
    actions = _actions(
        [
            {
                "event_id": "DIV-1",
                "security_id": "A",
                "event_type": "dividend",
                "announced_at": "2025-12-01T00:00:00Z",
                "ex_date": "2026-01-05",
                "effective_date": "2026-01-05",
                "cash_amount": 1.0,
                "share_ratio": 0.0,
                "successor_security_id": "",
                "source_record_id": "DIV-1",
            }
        ]
    )
    entitlements = _entitlements(
        [
            {
                "event_id": "DIV-1",
                "security_id": "A",
                "announced_at": "2025-12-01T00:00:00Z",
                "ex_date": "2026-01-05",
                "pay_date": "2026-01-06",
                "cash_available_date": "2026-01-06",
                "cash_per_share": 1.0,
                "source_record_id": "DIV-1",
            }
        ]
    )
    result = run_raw_accounting(
        sessions=SESSIONS[:3],
        prices=prices,
        instructions=(_instruction("2026-01-02", A=1.0),),
        corporate_actions=actions,
        cash_entitlements=entitlements,
    )

    ex_row = result.equity_curve.iloc[1]
    pay_row = result.equity_curve.iloc[2]
    assert ex_row["receivables"] > 0.0
    assert ex_row["cash"] < pay_row["cash"]
    assert pay_row["receivables"] == 0.0
    assert {row["route"] for row in result.action_audit.to_dict("records")} >= {
        "receivable",
        "cash_payment",
    }


def test_split_changes_shares_once_without_using_total_return_factor() -> None:
    prices = _prices(
        [
            ("A", "2026-01-02", 100.0, 100.0),
            ("A", "2026-01-05", 50.0, 55.0),
            ("A", "2026-01-06", 60.0, 60.0),
        ]
    )
    actions = _actions(
        [
            {
                "event_id": "SPLIT-1",
                "security_id": "A",
                "event_type": "split",
                "announced_at": "2025-12-01T00:00:00Z",
                "ex_date": "2026-01-05",
                "effective_date": "2026-01-05",
                "cash_amount": 0.0,
                "share_ratio": 2.0,
                "successor_security_id": "",
                "source_record_id": "SPLIT-1",
            }
        ]
    )
    result = run_raw_accounting(
        sessions=SESSIONS[:3],
        prices=prices,
        instructions=(_instruction("2026-01-02", A=1.0),),
        corporate_actions=actions,
    )

    initial_shares = float(result.equity_curve.iloc[0]["holdings"]["A"])
    split_shares = float(result.equity_curve.iloc[1]["holdings"]["A"])
    assert split_shares == pytest.approx(initial_shares * 2.0)
    assert sum(row["route"] == "share_adjustment" for row in result.action_audit.to_dict("records")) == 1


def test_cash_exit_uses_one_economic_route_and_removes_old_security() -> None:
    prices = _prices(
        [
            ("A", "2026-01-02", 100.0, 100.0),
            ("QQQ", "2026-01-02", 200.0, 200.0),
            ("QQQ", "2026-01-05", 200.0, 200.0),
            ("QQQ", "2026-01-06", 200.0, 200.0),
        ]
    )
    actions = _actions(
        [
            {
                "event_id": "EXIT-1",
                "security_id": "A",
                "event_type": "merger_cash",
                "announced_at": "2025-12-01T00:00:00Z",
                "ex_date": "2026-01-05",
                "effective_date": "2026-01-05",
                "cash_amount": 105.0,
                "share_ratio": 0.0,
                "successor_security_id": "",
                "source_record_id": "EXIT-1",
            }
        ]
    )
    outcomes = _outcomes(
        [
            {
                "source_record_id": "EXIT-1",
                "security_id": "A",
                "membership_effective_to": "2026-01-05",
                "outcome_type": "acquired_cash",
                "last_trade_date": "2026-01-02",
                "exit_effective_date": "2026-01-05",
                "delisting_return": "",
                "cash_consideration": 105.0,
                "successor_security_id": "",
                "reason_code": "MERGER",
                "known_at": "2025-12-01T00:00:00Z",
            }
        ]
    )
    result = run_raw_accounting(
        sessions=SESSIONS[:3],
        prices=prices,
        instructions=(_instruction("2026-01-02", A=1.0),),
        corporate_actions=actions,
        security_outcomes=outcomes,
    )

    assert "A" not in result.equity_curve.iloc[1]["holdings"]
    assert result.equity_curve.iloc[1]["cash"] > 1_000.0
    assert result.action_audit.iloc[-1]["route"] == "cash_consideration"


def test_stock_exit_transfers_successor_shares_once() -> None:
    prices = _prices(
        [
            ("A", "2026-01-02", 100.0, 100.0),
            ("B", "2026-01-05", 50.0, 55.0),
            ("B", "2026-01-06", 55.0, 55.0),
        ]
    )
    actions = _actions(
        [
            {
                "event_id": "EXIT-STOCK-1",
                "security_id": "A",
                "event_type": "merger_stock",
                "announced_at": "2025-12-01T00:00:00Z",
                "ex_date": "2026-01-05",
                "effective_date": "2026-01-05",
                "cash_amount": 0.0,
                "share_ratio": 0.5,
                "successor_security_id": "B",
                "source_record_id": "EXIT-STOCK-1",
            }
        ]
    )
    outcomes = _outcomes(
        [
            {
                "source_record_id": "EXIT-STOCK-1",
                "security_id": "A",
                "membership_effective_to": "2026-01-05",
                "outcome_type": "acquired_stock",
                "last_trade_date": "2026-01-02",
                "exit_effective_date": "2026-01-05",
                "delisting_return": "",
                "cash_consideration": "",
                "successor_security_id": "B",
                "reason_code": "MERGER",
                "known_at": "2025-12-01T00:00:00Z",
            }
        ]
    )
    result = run_raw_accounting(
        sessions=SESSIONS[:3],
        prices=prices,
        instructions=(_instruction("2026-01-02", A=1.0),),
        corporate_actions=actions,
        security_outcomes=outcomes,
    )

    assert "A" not in result.equity_curve.iloc[1]["holdings"]
    assert result.equity_curve.iloc[1]["holdings"]["B"] > 0.0
    assert result.action_audit.iloc[-1]["route"] == "stock_consideration"


def test_ambiguous_exit_and_missing_price_fail_closed() -> None:
    actions = _actions(
        [
            {
                "event_id": "EXIT-AMBIG",
                "security_id": "A",
                "event_type": "merger_cash",
                "announced_at": "2025-12-01T00:00:00Z",
                "ex_date": "2026-01-05",
                "effective_date": "2026-01-05",
                "cash_amount": 105.0,
                "share_ratio": 0.0,
                "successor_security_id": "",
                "source_record_id": "EXIT-AMBIG",
            }
        ]
    )
    outcomes = _outcomes(
        [
            {
                "source_record_id": "EXIT-AMBIG",
                "security_id": "A",
                "membership_effective_to": "2026-01-05",
                "outcome_type": "acquired_cash",
                "last_trade_date": "2026-01-02",
                "exit_effective_date": "2026-01-05",
                "delisting_return": -0.1,
                "cash_consideration": 105.0,
                "successor_security_id": "",
                "reason_code": "MERGER",
                "known_at": "2025-12-01T00:00:00Z",
            }
        ]
    )
    prices = _prices([("A", "2026-01-02", 100.0, 100.0)])
    with pytest.raises(FormalRawAccountingError) as error:
        run_raw_accounting(
            sessions=SESSIONS[:2],
            prices=prices,
            instructions=(_instruction("2026-01-02", A=1.0),),
            corporate_actions=actions,
            security_outcomes=outcomes,
        )
    assert error.value.code == "accounting_exit_economics_ambiguous"


def test_early_dividend_payment_and_missing_close_fail_closed() -> None:
    actions = _actions(
        [
            {
                "event_id": "DIV-EARLY",
                "security_id": "A",
                "event_type": "dividend",
                "announced_at": "2025-12-01T00:00:00Z",
                "ex_date": "2026-01-05",
                "effective_date": "2026-01-05",
                "cash_amount": 1.0,
                "share_ratio": 0.0,
                "successor_security_id": "",
                "source_record_id": "DIV-EARLY",
            }
        ]
    )
    early = _entitlements(
        [
            {
                "event_id": "DIV-EARLY",
                "security_id": "A",
                "announced_at": "2025-12-01T00:00:00Z",
                "ex_date": "2026-01-05",
                "pay_date": "2026-01-02",
                "cash_available_date": "2026-01-02",
                "cash_per_share": 1.0,
                "source_record_id": "DIV-EARLY",
            }
        ]
    )
    with pytest.raises(FormalRawAccountingError) as dividend_error:
        run_raw_accounting(
            sessions=SESSIONS[:3],
            prices=_prices(
                [
                    ("A", "2026-01-02", 100.0, 100.0),
                    ("A", "2026-01-05", 99.0, 99.0),
                ]
            ),
            instructions=(_instruction("2026-01-02", A=1.0),),
            corporate_actions=actions,
            cash_entitlements=early,
        )
    assert dividend_error.value.code == "accounting_entitlement_terms_invalid"

    with pytest.raises(FormalRawAccountingError) as price_error:
        run_raw_accounting(
            sessions=SESSIONS[:2],
            prices=_prices([("A", "2026-01-02", 100.0, 100.0)]),
            instructions=(_instruction("2026-01-02", A=1.0),),
        )
    assert price_error.value.code == "accounting_price_missing"
