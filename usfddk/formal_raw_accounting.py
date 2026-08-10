"""Raw-price portfolio accounting for the frozen short-term signal bridge.

This module is deliberately an internal accounting layer.  It consumes the
point-in-time target schedule and raw-price/action tables, then produces an
auditable daily ledger.  It does not write a Paper account, calculate a
promoted strategy result, or feed the public decision contract.

The important boundary is that valuation uses raw open/raw close plus the
explicit action ledger.  ``total_return_factor`` may be present in the input
for signal construction, but it is never used to value an account.  That
prevents a dividend, split, or delisting return from being counted twice.
"""

from __future__ import annotations

import math
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from .ciz_execution_accounting import (
    apply_split_once,
    credit_dividend_cash,
    settle_cash_exit,
    settle_delisting_return,
    settle_stock_exit,
)
from .formal_execution_schedule import ExecutionInstruction

FORMAL_RAW_ACCOUNTING_VERSION = "round19-formal-raw-accounting-v1"
FORMAL_COST_BPS = (10, 25, 50)
FORMAL_INITIAL_CASH_USD = 1_000.0
VALUATION_POLICY = "raw_close_plus_explicit_action_ledger"
TARGET_NOTIONAL_POLICY = "available_cash_plus_open_positions_excludes_receivables"
_TOLERANCE = 1e-9

_PRICE_COLUMNS = {
    "security_id",
    "session",
    "open_raw",
    "close_raw",
    "source_status",
}
_ACTION_COLUMNS = {
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
}
_ENTITLEMENT_COLUMNS = {
    "event_id",
    "security_id",
    "announced_at",
    "ex_date",
    "pay_date",
    "cash_available_date",
    "cash_per_share",
    "source_record_id",
}
_OUTCOME_COLUMNS = {
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
}
_EXIT_EVENT_TYPES = {"merger_cash", "merger_stock", "bankruptcy", "delisting"}
_ACTION_ORDER = {
    # A split/spinoff is applied before a same-day open rebalance.  A dividend
    # entitlement is created before a possible exit; its payment remains a
    # later, explicit cash event.
    "dividend": 0,
    "split": 1,
    "spinoff": 2,
    "merger_cash": 3,
    "merger_stock": 3,
    "bankruptcy": 3,
    "delisting": 3,
}


class FormalRawAccountingError(ValueError):
    """Fail-closed raw account error with a stable semantic code."""

    def __init__(self, code: str, detail: str):
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}")


def _fail(code: str, detail: str) -> None:
    raise FormalRawAccountingError(code, detail)


def _date(value: object, field: str) -> pd.Timestamp:
    parsed = pd.to_datetime(str(value), format="%Y-%m-%d", errors="coerce")
    if pd.isna(parsed):
        _fail("accounting_date_invalid", f"{field} 不是 YYYY-MM-DD")
    return pd.Timestamp(parsed).normalize()


def _optional_date(value: object, field: str) -> pd.Timestamp | None:
    raw = str(value).strip()
    return None if not raw else _date(raw, field)


def _number(value: object, field: str, *, allow_blank: bool = False) -> float | None:
    raw = str(value).strip()
    if allow_blank and not raw:
        return None
    try:
        parsed = float(raw)
    except (TypeError, ValueError):
        _fail("accounting_number_invalid", f"{field} 不是數值")
    if not math.isfinite(parsed):
        _fail("accounting_number_invalid", f"{field} 不是有限數值")
    return parsed


def _sessions(values: Iterable[object]) -> pd.DatetimeIndex:
    parsed = pd.to_datetime(list(values), format="%Y-%m-%d", errors="coerce")
    result = pd.DatetimeIndex(parsed).normalize()
    if (
        len(result) == 0
        or result.hasnans
        or result.has_duplicates
        or not result.is_monotonic_increasing
    ):
        _fail("accounting_calendar_invalid", "sessions 必須非空、唯一及嚴格遞增")
    return result


def _frame_or_empty(frame: pd.DataFrame | None, columns: set[str], label: str) -> pd.DataFrame:
    if frame is None:
        return pd.DataFrame(columns=sorted(columns))
    if not isinstance(frame, pd.DataFrame):
        _fail("accounting_schema_invalid", f"{label} 必須是 DataFrame")
    missing = sorted(columns - set(frame.columns))
    if missing:
        _fail("accounting_schema_invalid", f"{label} 缺欄位：{missing}")
    return frame.copy()


def _prepare_prices(
    prices: pd.DataFrame,
    sessions: pd.DatetimeIndex,
) -> tuple[pd.DataFrame, dict[tuple[pd.Timestamp, str], dict[str, float]]]:
    frame = _frame_or_empty(prices, _PRICE_COLUMNS, "daily_prices")
    if frame.empty:
        _fail("accounting_price_missing", "daily_prices 不可為空")
    frame["__session"] = pd.to_datetime(
        frame["session"], format="%Y-%m-%d", errors="coerce"
    )
    if frame["__session"].isna().any():
        _fail("accounting_price_schema_invalid", "daily_prices session 無效")
    if frame[["security_id", "__session"]].duplicated().any():
        _fail("accounting_price_schema_invalid", "同一證券／session 有重複價格")
    if not frame["source_status"].eq("observed").all():
        _fail("accounting_price_schema_invalid", "估值只接受 observed raw price")
    for column in ("open_raw", "close_raw"):
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
        if frame[column].isna().any() or not np.isfinite(frame[column]).all():
            _fail("accounting_price_schema_invalid", f"{column} 含非有限價格")
        if (frame[column] <= 0).any():
            _fail("accounting_price_schema_invalid", f"{column} 必須為正")
    if not set(frame["__session"]).issubset(set(sessions)):
        _fail("accounting_calendar_invalid", "價格含不在 sessions 的日期")
    lookup: dict[tuple[pd.Timestamp, str], dict[str, float]] = {}
    for _, row in frame.iterrows():
        lookup[(pd.Timestamp(row["__session"]), str(row["security_id"]))] = {
            "open_raw": float(row["open_raw"]),
            "close_raw": float(row["close_raw"]),
        }
    return frame, lookup


def _prepare_actions(
    actions: pd.DataFrame | None,
    sessions: pd.DatetimeIndex,
) -> tuple[pd.DataFrame, dict[pd.Timestamp, list[dict[str, Any]]]]:
    frame = _frame_or_empty(actions, _ACTION_COLUMNS, "corporate_actions")
    if frame.empty:
        return frame, {}
    if frame["event_id"].eq("").any() or not frame["event_id"].is_unique:
        _fail("accounting_action_schema_invalid", "event_id 必須非空及唯一")
    if frame["source_record_id"].eq("").any():
        _fail("accounting_action_schema_invalid", "action source_record_id 不可空白")
    rows: list[dict[str, Any]] = []
    for row in frame.to_dict(orient="records"):
        event_type = str(row["event_type"])
        if event_type not in _ACTION_ORDER:
            _fail("accounting_action_schema_invalid", f"不支援 action type：{event_type}")
        ex_date = _optional_date(row["ex_date"], "action ex_date")
        effective_date = _date(row["effective_date"], "action effective_date")
        if ex_date is None:
            ex_date = effective_date
        if ex_date not in sessions or effective_date not in sessions:
            _fail("accounting_calendar_invalid", "action 日期不在 sessions")
        cash_amount = _number(row["cash_amount"], "action cash_amount")
        share_ratio = _number(row["share_ratio"], "action share_ratio")
        successor = str(row["successor_security_id"]).strip()
        if event_type in {"split", "spinoff", "merger_stock"} and (
            share_ratio is None or share_ratio <= 0
        ):
            _fail("accounting_action_terms_invalid", f"{row['event_id']} 缺正 share_ratio")
        if event_type == "dividend" and (cash_amount is None or cash_amount <= 0):
            _fail("accounting_action_terms_invalid", f"{row['event_id']} 缺正 cash_amount")
        if event_type == "spinoff" and not successor:
            _fail("accounting_action_terms_invalid", f"{row['event_id']} 缺 successor")
        if event_type == "merger_stock" and not successor:
            _fail("accounting_action_terms_invalid", f"{row['event_id']} 缺 successor")
        rows.append(
            {
                **row,
                "__ex_date": ex_date,
                "__effective_date": effective_date,
                "__cash_amount": cash_amount,
                "__share_ratio": share_ratio,
                "__successor": successor,
            }
        )
    normalised = pd.DataFrame(rows)
    by_date: dict[pd.Timestamp, list[dict[str, Any]]] = {}
    for row in rows:
        by_date.setdefault(row["__ex_date"], []).append(row)
        if row["__effective_date"] != row["__ex_date"]:
            by_date.setdefault(row["__effective_date"], []).append(row)
    for day in by_date:
        by_date[day] = sorted(
            by_date[day],
            key=lambda item: (
                _ACTION_ORDER[str(item["event_type"])],
                str(item["event_id"]),
            ),
        )
    return normalised, by_date


def _prepare_entitlements(
    entitlements: pd.DataFrame | None,
    sessions: pd.DatetimeIndex,
) -> tuple[pd.DataFrame, dict[str, dict[str, Any]]]:
    frame = _frame_or_empty(entitlements, _ENTITLEMENT_COLUMNS, "cash_entitlements")
    if frame.empty:
        return frame, {}
    if frame["event_id"].eq("").any() or not frame["event_id"].is_unique:
        _fail("accounting_entitlement_schema_invalid", "entitlement event_id 必須唯一")
    rows: dict[str, dict[str, Any]] = {}
    for raw in frame.to_dict(orient="records"):
        ex_date = _date(raw["ex_date"], "entitlement ex_date")
        pay_date = _date(raw["pay_date"], "entitlement pay_date")
        available = _date(raw["cash_available_date"], "cash_available_date")
        if pay_date < ex_date or available != pay_date:
            _fail("accounting_entitlement_terms_invalid", f"{raw['event_id']} pay-date policy invalid")
        if pay_date not in sessions or ex_date not in sessions:
            _fail("accounting_calendar_invalid", "entitlement 日期不在 sessions")
        cash = _number(raw["cash_per_share"], "cash_per_share")
        if cash is None or cash <= 0:
            _fail("accounting_entitlement_terms_invalid", f"{raw['event_id']} 缺正 cash_per_share")
        rows[str(raw["event_id"])] = {
            **raw,
            "__ex_date": ex_date,
            "__pay_date": pay_date,
            "__cash_per_share": cash,
        }
    return frame, rows


def _prepare_outcomes(
    outcomes: pd.DataFrame | None,
    sessions: pd.DatetimeIndex,
) -> dict[tuple[str, pd.Timestamp], dict[str, Any]]:
    frame = _frame_or_empty(outcomes, _OUTCOME_COLUMNS, "security_outcomes")
    if frame.empty:
        return {}
    result: dict[tuple[str, pd.Timestamp], dict[str, Any]] = {}
    for raw in frame.to_dict(orient="records"):
        security_id = str(raw["security_id"])
        effective = _date(raw["exit_effective_date"], "exit_effective_date")
        if effective not in sessions:
            _fail("accounting_calendar_invalid", "outcome 日期不在 sessions")
        key = (security_id, effective)
        if key in result:
            _fail("accounting_outcome_schema_invalid", f"outcome 重複：{key}")
        outcome_type = str(raw["outcome_type"])
        if outcome_type not in {"acquired_cash", "acquired_stock", "bankrupt", "delisted"}:
            _fail("accounting_outcome_schema_invalid", f"不支援 outcome：{outcome_type}")
        last_trade = _date(raw["last_trade_date"], "last_trade_date")
        if last_trade > effective:
            _fail("accounting_outcome_schema_invalid", f"{key} last_trade_date 晚於 exit")
        result[key] = {
            **raw,
            "__security_id": security_id,
            "__effective": effective,
            "__last_trade": last_trade,
            "__delisting_return": _number(
                raw["delisting_return"], "delisting_return", allow_blank=True
            ),
            "__cash_consideration": _number(
                raw["cash_consideration"], "cash_consideration", allow_blank=True
            ),
            "__successor": str(raw["successor_security_id"]).strip(),
        }
    return result


def _validate_dividend_bindings(
    actions: pd.DataFrame,
    entitlements: dict[str, dict[str, Any]],
) -> None:
    dividend_ids = set(actions.loc[actions["event_type"].eq("dividend"), "event_id"])
    if dividend_ids != set(entitlements):
        _fail("accounting_entitlement_mismatch", "dividend action 與 entitlement 未一對一")
    for row in actions.loc[actions["event_type"].eq("dividend")].to_dict(orient="records"):
        entitlement = entitlements[str(row["event_id"])]
        action_ex_date = _date(row["ex_date"], "action ex_date")
        entitlement_ex_date = _date(entitlement["ex_date"], "entitlement ex_date")
        if (
            str(row["security_id"]) != str(entitlement["security_id"])
            or action_ex_date != entitlement_ex_date
            or not math.isclose(
                float(row["cash_amount"]), float(entitlement["__cash_per_share"]), rel_tol=0.0, abs_tol=_TOLERANCE
            )
        ):
            _fail("accounting_entitlement_mismatch", f"{row['event_id']} action／entitlement 對數失敗")


@dataclass(frozen=True)
class RawAccountingResult:
    """Internal result; callers must not treat it as a Paper or recommendation."""

    policy: dict[str, Any]
    equity_curve: pd.DataFrame
    trades: pd.DataFrame
    action_audit: pd.DataFrame

    @property
    def terminal_equity(self) -> float:
        if self.equity_curve.empty:
            return 0.0
        return float(self.equity_curve.iloc[-1]["equity"])


def _price(
    lookup: dict[tuple[pd.Timestamp, str], dict[str, float]],
    day: pd.Timestamp,
    security_id: str,
    field: str,
) -> float:
    row = lookup.get((day, security_id))
    if row is None:
        _fail("accounting_price_missing", f"{security_id} 缺 {day.date()} {field}")
    return float(row[field])


def _mark(
    lookup: dict[tuple[pd.Timestamp, str], dict[str, float]],
    day: pd.Timestamp,
    holdings: dict[str, float],
) -> float:
    value = 0.0
    for security_id, shares in holdings.items():
        if shares < -_TOLERANCE:
            _fail("accounting_position_invalid", f"{security_id} 股數為負")
        if shares > _TOLERANCE:
            value += shares * _price(lookup, day, security_id, "close_raw")
    return float(value)


def _trade(
    *,
    day: pd.Timestamp,
    security_id: str,
    shares: float,
    open_price: float,
    cost_rate: float,
    cash: float,
    holdings: dict[str, float],
    trades: list[dict[str, Any]],
) -> float:
    if abs(shares) <= _TOLERANCE:
        return cash
    gross = float(shares * open_price)
    cost = abs(gross) * cost_rate
    if shares > 0:
        total = gross + cost
        if cash + _TOLERANCE < total:
            _fail("accounting_cash_unavailable", f"{day.date()} {security_id} 買入現金不足")
        cash -= total
    else:
        cash += -gross - cost
    holdings[security_id] = holdings.get(security_id, 0.0) + float(shares)
    if abs(holdings[security_id]) <= _TOLERANCE:
        holdings.pop(security_id, None)
    if holdings.get(security_id, 0.0) < -_TOLERANCE:
        _fail("accounting_position_invalid", f"{security_id} 沽出後股數為負")
    trades.append(
        {
            "session": str(day.date()),
            "security_id": security_id,
            "shares": float(shares),
            "open_raw": float(open_price),
            "gross_notional": gross,
            "cost": cost,
            "side": "buy" if shares > 0 else "sell",
        }
    )
    return float(cash)


def _rebalance(
    *,
    day: pd.Timestamp,
    targets: dict[str, float],
    lookup: dict[tuple[pd.Timestamp, str], dict[str, float]],
    holdings: dict[str, float],
    cash: float,
    cost_rate: float,
    trades: list[dict[str, Any]],
) -> float:
    if not targets or any(weight < -_TOLERANCE for weight in targets.values()):
        _fail("accounting_target_invalid", f"{day.date()} target 權重無效")
    if not math.isclose(sum(targets.values()), 1.0, rel_tol=0.0, abs_tol=1e-8):
        _fail("accounting_target_invalid", f"{day.date()} target 權重不是 100%")
    # Receivables are an asset in equity but are not cash available for an open
    # order.  The target notional therefore uses only cash plus open-position
    # value.  This is conservative and prevents implicit borrowing before pay-date.
    available_equity = float(cash)
    current_open: dict[str, float] = {}
    for security_id, shares in list(holdings.items()):
        current_open[security_id] = _price(lookup, day, security_id, "open_raw")
        available_equity += shares * current_open[security_id]
    if not math.isfinite(available_equity) or available_equity <= 0.0:
        _fail("accounting_equity_invalid", f"{day.date()} 可交易權益無效")

    # Reserve the maximum primary cost before sizing the target.  Otherwise a
    # first 100% buy would require borrowing the fee on top of the US$1,000
    # starting cash, which violates the no-leverage contract.
    target_investable = available_equity / (1.0 + cost_rate)
    desired: dict[str, float] = {}
    for security_id, weight in targets.items():
        if weight <= _TOLERANCE:
            continue
        open_price = _price(lookup, day, security_id, "open_raw")
        desired[security_id] = target_investable * float(weight) / open_price

    all_symbols = sorted(set(holdings) | set(desired))
    deltas = {
        security_id: desired.get(security_id, 0.0) - holdings.get(security_id, 0.0)
        for security_id in all_symbols
    }
    # Sell first, then buy, so a cash-funded rebalance never relies on order
    # column order or accidental temporary leverage.
    for security_id in all_symbols:
        delta = deltas[security_id]
        if delta < -_TOLERANCE:
            cash = _trade(
                day=day,
                security_id=security_id,
                shares=delta,
                open_price=current_open.get(
                    security_id, _price(lookup, day, security_id, "open_raw")
                ),
                cost_rate=cost_rate,
                cash=cash,
                holdings=holdings,
                trades=trades,
            )
    buy_deltas = {
        security_id: deltas[security_id]
        for security_id in all_symbols
        if deltas[security_id] > _TOLERANCE
    }
    buy_notional = sum(
        delta * _price(lookup, day, security_id, "open_raw")
        for security_id, delta in buy_deltas.items()
    )
    buy_total = buy_notional * (1.0 + cost_rate)
    buy_scale = 1.0
    if buy_total > cash + _TOLERANCE:
        if cash <= _TOLERANCE or buy_total <= 0.0:
            _fail("accounting_cash_unavailable", f"{day.date()} 買入現金不足")
        # Selling incurs a cost before the new target is bought.  Scale the
        # positive deltas together instead of silently borrowing that cost.
        buy_scale = cash / buy_total
    for security_id in all_symbols:
        delta = buy_deltas.get(security_id, 0.0) * buy_scale
        if delta > _TOLERANCE:
            cash = _trade(
                day=day,
                security_id=security_id,
                shares=delta,
                open_price=_price(lookup, day, security_id, "open_raw"),
                cost_rate=cost_rate,
                cash=cash,
                holdings=holdings,
                trades=trades,
            )
    return float(cash)


def _settle_exit(
    *,
    day: pd.Timestamp,
    action: dict[str, Any],
    outcome: dict[tuple[str, pd.Timestamp], dict[str, Any]],
    lookup: dict[tuple[pd.Timestamp, str], dict[str, float]],
    holdings: dict[str, float],
    cash: float,
    action_audit: list[dict[str, Any]],
) -> float:
    security_id = str(action["security_id"])
    shares = float(holdings.get(security_id, 0.0))
    if shares <= _TOLERANCE:
        return cash
    terms = outcome.get((security_id, day))
    if terms is None:
        _fail("accounting_exit_terms_missing", f"{security_id} {day.date()} 缺 exit terms")
    last_trade = terms["__last_trade"]
    last_close = _price(lookup, last_trade, security_id, "close_raw")
    last_value = shares * last_close
    delisting_return = terms["__delisting_return"]
    cash_consideration = terms["__cash_consideration"]
    successor = str(terms["__successor"])
    routes = int(delisting_return is not None) + int(cash_consideration is not None) + int(bool(successor))
    # A stock-acquisition successor is only a valid route for acquired_stock;
    # the outcome row and action type must agree rather than silently choosing
    # whichever term happens to be present.
    if routes != 1:
        _fail("accounting_exit_economics_ambiguous", f"{security_id} {day.date()} exit route 不唯一")
    if delisting_return is not None:
        terminal = settle_delisting_return(
            last_value,
            delisting_return,
            apply_storage_return=False,
            apply_outcome_return=True,
        )
        cash += terminal
        route = "delisting_return"
        successor_shares = 0.0
    elif cash_consideration is not None:
        terminal = settle_cash_exit(
            last_value=last_value,
            shares=shares,
            delisting_return=None,
            cash_consideration=cash_consideration,
            apply_return=False,
            apply_cash=True,
        )
        cash += terminal
        route = "cash_consideration"
        successor_shares = 0.0
    else:
        if str(terms["outcome_type"]) != "acquired_stock" or action["event_type"] != "merger_stock":
            _fail("accounting_exit_economics_ambiguous", f"{security_id} stock route type 不符")
        action_successor = str(action.get("__successor", "")).strip()
        if action_successor != successor:
            _fail("accounting_exit_economics_ambiguous", f"{security_id} successor 對數失敗")
        successor_id, successor_shares = settle_stock_exit(
            shares,
            successor,
            _number(action.get("__share_ratio", ""), "exit share_ratio", allow_blank=True),
        )
        holdings[successor_id] = holdings.get(successor_id, 0.0) + successor_shares
        terminal = successor_shares
        route = "stock_consideration"
    holdings.pop(security_id, None)
    action_audit.append(
        {
            "session": str(day.date()),
            "event_id": str(action["event_id"]),
            "security_id": security_id,
            "event_type": str(action["event_type"]),
            "route": route,
            "shares_before": shares,
            "last_trade_close": last_close,
            "terminal_cash": float(terminal) if route != "stock_consideration" else 0.0,
            "successor_shares": float(successor_shares),
        }
    )
    return float(cash)


def run_raw_accounting(
    *,
    sessions: Iterable[object],
    prices: pd.DataFrame,
    instructions: Iterable[ExecutionInstruction],
    corporate_actions: pd.DataFrame | None = None,
    cash_entitlements: pd.DataFrame | None = None,
    security_outcomes: pd.DataFrame | None = None,
    initial_cash: float = FORMAL_INITIAL_CASH_USD,
    cost_bps: int = 10,
) -> RawAccountingResult:
    """Replay one target schedule using raw prices and explicit action terms.

    This is an internal, one-pass ledger.  It intentionally raises on missing
    prices, ambiguous exits, early dividend cash, and unsupported adjusted-price
    shortcuts.  It never writes or mutates the repository's Paper state.
    """

    if cost_bps not in FORMAL_COST_BPS:
        _fail("accounting_cost_policy_invalid", f"只接受凍結成本 {FORMAL_COST_BPS} bps")
    if not math.isfinite(initial_cash) or initial_cash <= 0:
        _fail("accounting_initial_cash_invalid", "initial cash 必須為正有限數")
    calendar = _sessions(sessions)
    price_frame, lookup = _prepare_prices(prices, calendar)
    actions, actions_by_day = _prepare_actions(corporate_actions, calendar)
    _, entitlement_map = _prepare_entitlements(cash_entitlements, calendar)
    outcomes = _prepare_outcomes(security_outcomes, calendar)
    _validate_dividend_bindings(actions, entitlement_map)

    instruction_rows = list(instructions)
    if not instruction_rows:
        _fail("accounting_schedule_missing", "沒有正式 execution instruction")
    schedule: dict[pd.Timestamp, ExecutionInstruction] = {}
    for instruction in instruction_rows:
        if instruction.execution_session not in calendar:
            _fail("accounting_calendar_invalid", "execution session 不在 calendar")
        if instruction.execution_session in schedule:
            _fail("accounting_schedule_duplicate", "同日有多個 execution instruction")
        schedule[instruction.execution_session] = instruction

    cash = float(initial_cash)
    holdings: dict[str, float] = {}
    receivables: dict[str, float] = {}
    settled_actions: set[str] = set()
    trades: list[dict[str, Any]] = []
    action_audit: list[dict[str, Any]] = []
    curve_rows: list[dict[str, Any]] = []
    cost_rate = float(cost_bps) / 10_000.0

    for day in calendar:
        # Action rows can be indexed by ex-date and effective date.  Apply each
        # event only once even when the two dates are equal.
        for action in actions_by_day.get(day, []):
            event_id = str(action["event_id"])
            if event_id in settled_actions:
                continue
            event_type = str(action["event_type"])
            ex_date = action["__ex_date"]
            effective_date = action["__effective_date"]
            security_id = str(action["security_id"])
            if event_type == "dividend" and ex_date == day:
                shares = float(holdings.get(security_id, 0.0))
                if shares > _TOLERANCE:
                    entitlement = entitlement_map.get(event_id)
                    if entitlement is None:
                        _fail("accounting_entitlement_mismatch", f"{event_id} 缺 entitlement")
                    receivables[event_id] = credit_dividend_cash(
                        shares=shares,
                        cash_per_share=float(entitlement["__cash_per_share"]),
                        ex_date=str(entitlement["ex_date"]),
                        pay_date=str(entitlement["pay_date"]),
                        credit_date=str(entitlement["cash_available_date"]),
                    )
                    action_audit.append(
                        {
                            "session": str(day.date()),
                            "event_id": event_id,
                            "security_id": security_id,
                            "event_type": "dividend",
                            "route": "receivable",
                            "shares_before": shares,
                            "receivable": receivables[event_id],
                        }
                    )
            elif event_type == "split" and ex_date == day:
                shares = float(holdings.get(security_id, 0.0))
                if shares > _TOLERANCE:
                    previous_sessions = calendar[calendar < day]
                    if len(previous_sessions) == 0:
                        _fail("accounting_action_terms_invalid", f"{event_id} split 缺前一交易日")
                    pre_price = _price(lookup, previous_sessions[-1], security_id, "close_raw")
                    post_price = _price(lookup, day, security_id, "close_raw")
                    result = apply_split_once(
                        shares=shares,
                        pre_split_price=pre_price,
                        share_ratio=float(action["__share_ratio"]),
                        post_split_price=post_price,
                        apply_ratio_to_shares=True,
                        apply_ratio_as_return=False,
                    )
                    holdings[security_id] = result["after_shares"]
                    action_audit.append(
                        {
                            "session": str(day.date()),
                            "event_id": event_id,
                            "security_id": security_id,
                            "event_type": "split",
                            "route": "share_adjustment",
                            "shares_before": shares,
                            "shares_after": result["after_shares"],
                        }
                    )
            elif event_type == "spinoff" and ex_date == day:
                shares = float(holdings.get(security_id, 0.0))
                if shares > _TOLERANCE:
                    successor = str(action["__successor"])
                    ratio = float(action["__share_ratio"])
                    successor_price = _price(lookup, day, successor, "close_raw")
                    successor_shares = shares * ratio
                    holdings[successor] = holdings.get(successor, 0.0) + successor_shares
                    action_audit.append(
                        {
                            "session": str(day.date()),
                            "event_id": event_id,
                            "security_id": security_id,
                            "event_type": "spinoff",
                            "route": "successor_shares",
                            "shares_before": shares,
                            "successor_security_id": successor,
                            "successor_shares": successor_shares,
                            "successor_close": successor_price,
                        }
                    )
            elif event_type in _EXIT_EVENT_TYPES and effective_date == day:
                cash = _settle_exit(
                    day=day,
                    action=action,
                    outcome=outcomes,
                    lookup=lookup,
                    holdings=holdings,
                    cash=cash,
                    action_audit=action_audit,
                )
            # Events that are not relevant to a currently empty position still
            # become settled, so a later accidental position cannot backdate it.
            if event_type == "dividend" and ex_date == day:
                settled_actions.add(event_id)
            elif event_type in {"split", "spinoff"} and ex_date == day:
                settled_actions.add(event_id)
            elif event_type in _EXIT_EVENT_TYPES and effective_date == day:
                settled_actions.add(event_id)

        # Payments are released only on the exact pay-date, after ex-date
        # entitlement creation.  Unheld dividends never create a receivable.
        for event_id, entitlement in entitlement_map.items():
            if entitlement["__pay_date"] != day or event_id not in receivables:
                continue
            cash += float(receivables.pop(event_id))
            action_audit.append(
                {
                    "session": str(day.date()),
                    "event_id": event_id,
                    "security_id": str(entitlement["security_id"]),
                    "event_type": "dividend",
                    "route": "cash_payment",
                }
            )

        instruction = schedule.get(day)
        if instruction is not None:
            cash = _rebalance(
                day=day,
                targets=instruction.targets,
                lookup=lookup,
                holdings=holdings,
                cash=cash,
                cost_rate=cost_rate,
                trades=trades,
            )

        position_value = _mark(lookup, day, holdings)
        receivable_value = float(sum(receivables.values()))
        equity = float(cash + position_value + receivable_value)
        if not math.isfinite(equity) or equity <= 0.0:
            _fail("accounting_equity_invalid", f"{day.date()} 收市權益無效")
        curve_rows.append(
            {
                "session": str(day.date()),
                "cash": float(cash),
                "receivables": receivable_value,
                "positions_value": position_value,
                "equity": equity,
                "holdings": dict(sorted(holdings.items())),
                "pending_entitlements": sorted(receivables),
                "execution_session": instruction is not None,
            }
        )

    curve = pd.DataFrame(curve_rows)
    trade_frame = pd.DataFrame(
        trades,
        columns=(
            "session",
            "security_id",
            "shares",
            "open_raw",
            "gross_notional",
            "cost",
            "side",
        ),
    )
    action_frame = pd.DataFrame(action_audit)
    # Recompute the valuation identity from the public rows rather than trusting
    # an intermediate accumulator.  This catches accidental double counting of
    # cash, raw prices, or action proceeds.
    identity = curve["cash"] + curve["receivables"] + curve["positions_value"]
    if not np.allclose(identity.to_numpy(dtype=float), curve["equity"].to_numpy(dtype=float), atol=_TOLERANCE, rtol=0.0):
        _fail("accounting_valuation_identity_failed", "每日 cash／應收／持股 identity 不對數")
    return RawAccountingResult(
        policy={
            "version": FORMAL_RAW_ACCOUNTING_VERSION,
            "valuation": VALUATION_POLICY,
            "target_notional": TARGET_NOTIONAL_POLICY,
            "terminal_receivables_included": True,
            "cost_bps": cost_bps,
            "initial_cash_usd": float(initial_cash),
            "paper_authorized": False,
            "real_money_action_usd": 0,
        },
        equity_curve=curve,
        trades=trade_frame,
        action_audit=action_frame,
    )
