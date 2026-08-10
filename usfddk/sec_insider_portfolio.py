"""Implementability check for a fixed SEC-insider event portfolio."""

from __future__ import annotations

import math
from collections import defaultdict
from datetime import date
from typing import Any

import pandas as pd

PORTFOLIO_SCHEMA_VERSION = 1
PORTFOLIO_HOLDING_SESSIONS = 20
PORTFOLIO_ONE_WAY_COST_BPS = 10.0
PORTFOLIO_ROUND_TRIP_COST_BPS = 20.0
PORTFOLIO_COST_SCENARIOS = (10.0, 25.0, 50.0)
PORTFOLIO_BASELINE_SYMBOLS = ("QQQ", "SPY", "IWM")


def _price_maps(
    prices: pd.DataFrame,
) -> tuple[
    list[date],
    dict[date, int],
    dict[str, dict[date, tuple[float, float]]],
]:
    qqq = prices[prices["symbol"].eq("QQQ")].sort_values("date")
    sessions = qqq["date"].tolist()
    session_positions = {day: index for index, day in enumerate(sessions)}
    by_symbol: dict[str, dict[date, tuple[float, float]]] = defaultdict(dict)
    for row in prices.itertuples(index=False):
        by_symbol[str(row.symbol)][row.date] = (
            float(row.adj_open),
            float(row.adj_close),
        )
    return sessions, session_positions, dict(by_symbol)


def prepare_portfolio_signals(
    candidates: list[dict[str, Any]],
    prices: pd.DataFrame,
    *,
    holding_sessions: int = PORTFOLIO_HOLDING_SESSIONS,
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    """Apply fixed price-completeness and first-signal-wins rules."""

    if holding_sessions != PORTFOLIO_HOLDING_SESSIONS:
        raise ValueError("portfolio holding period is frozen at 20 sessions")
    sessions, positions, by_symbol = _price_maps(prices)
    accepted: list[dict[str, Any]] = []
    skipped = {
        "missing_session": 0,
        "missing_price_window": 0,
        "overlapping_issuer_signal": 0,
    }
    active_until: dict[str, date] = {}
    ordered = sorted(
        candidates,
        key=lambda row: (
            str(row["available_session"]),
            -float(row.get("score", 0.0)),
            str(row["ticker"]),
        ),
    )
    for candidate in ordered:
        ticker = str(candidate["ticker"]).upper()
        entry = date.fromisoformat(str(candidate["available_session"]))
        entry_position = positions.get(entry)
        if entry_position is None:
            skipped["missing_session"] += 1
            continue
        exit_position = entry_position + holding_sessions - 1
        if exit_position >= len(sessions):
            skipped["missing_price_window"] += 1
            continue
        exit_date = sessions[exit_position]
        if ticker in active_until and entry <= active_until[ticker]:
            skipped["overlapping_issuer_signal"] += 1
            continue
        symbol_prices = by_symbol.get(ticker, {})
        window = sessions[entry_position : exit_position + 1]
        if any(day not in symbol_prices for day in window):
            skipped["missing_price_window"] += 1
            continue
        active_until[ticker] = exit_date
        accepted.append(
            {
                "ticker": ticker,
                "entry_date": entry,
                "exit_date": exit_date,
                "signal_quarter": candidate.get("signal_quarter"),
                "score": float(candidate.get("score", 0.0)),
            }
        )
    skipped["accepted"] = len(accepted)
    return accepted, skipped


def _metrics(equity: pd.Series, daily_returns: pd.Series, days: int) -> dict[str, float]:
    if equity.empty:
        return {
            "total_return": 0.0,
            "cagr": 0.0,
            "sharpe": 0.0,
            "max_drawdown": 0.0,
        }
    running_max = equity.cummax()
    drawdown = equity.div(running_max).sub(1.0)
    volatility = float(daily_returns.std(ddof=1)) if len(daily_returns) > 1 else 0.0
    sharpe = (
        float(daily_returns.mean()) / volatility * math.sqrt(252.0)
        if volatility > 0.0
        else 0.0
    )
    ending = float(equity.iloc[-1])
    cagr = ending ** (365.25 / max(days, 1)) - 1.0 if ending > 0.0 else -1.0
    return {
        "total_return": ending - 1.0,
        "cagr": float(cagr),
        "sharpe": sharpe,
        "max_drawdown": float(drawdown.min()),
    }


def _buy_hold_baseline(
    prices: pd.DataFrame,
    *,
    symbol: str,
    start: date,
    end: date,
    one_way_cost: float,
) -> tuple[dict[str, float], pd.Series]:
    rows = prices[prices["symbol"].eq(symbol)].sort_values("date")
    rows = rows[(rows["date"] >= start) & (rows["date"] <= end)].reset_index(drop=True)
    if rows.empty:
        return _metrics(pd.Series(dtype=float), pd.Series(dtype=float), 1), pd.Series(dtype=float)
    returns = [float(rows.loc[0, "adj_close"] / rows.loc[0, "adj_open"] - 1.0)]
    if len(rows) > 1:
        returns.extend(
            (rows["adj_close"].iloc[1:].to_numpy() / rows["adj_close"].iloc[:-1].to_numpy())
            - 1.0
        )
    equity_values = []
    equity = 1.0 - one_way_cost
    for value in returns:
        equity *= 1.0 + float(value)
        equity_values.append(equity)
    equity *= 1.0 - one_way_cost
    equity_values[-1] = equity
    series = pd.Series(equity_values, index=rows["date"].tolist())
    net_returns = series.pct_change().fillna(series.iloc[0] - 1.0)
    days = max((end - start).days, 1)
    return _metrics(series, net_returns, days), net_returns


def simulate_event_portfolio(
    signals: list[dict[str, Any]],
    prices: pd.DataFrame,
    *,
    one_way_cost_bps: float = PORTFOLIO_ONE_WAY_COST_BPS,
    baseline_symbols: tuple[str, ...] = ("QQQ",),
) -> dict[str, Any]:
    """Simulate all eligible signals with equal active-position weights."""

    if one_way_cost_bps not in PORTFOLIO_COST_SCENARIOS:
        raise ValueError("portfolio transaction cost must be one of frozen 10/25/50 bps scenarios")
    if not signals:
        return {
            "signal_count": 0,
            "period": None,
            "portfolio": _metrics(pd.Series(dtype=float), pd.Series(dtype=float), 1),
            "QQQ": _metrics(pd.Series(dtype=float), pd.Series(dtype=float), 1),
            "baselines": {
                symbol: _metrics(pd.Series(dtype=float), pd.Series(dtype=float), 1)
                for symbol in baseline_symbols
            },
            "comparison": {"cagr_difference": 0.0, "total_return_difference": 0.0},
            "average_active_positions": 0.0,
            "annualized_turnover": 0.0,
            "terminal_liquidation_cost": 0.0,
        }
    one_way_cost = one_way_cost_bps / 10_000.0
    sessions, positions, by_symbol = _price_maps(prices)
    start = min(signal["entry_date"] for signal in signals)
    end = max(signal["exit_date"] for signal in signals)
    session_slice = [day for day in sessions if start <= day <= end]
    signals_by_day: dict[date, list[dict[str, Any]]] = defaultdict(list)
    for signal in signals:
        signals_by_day[signal["entry_date"]].append(signal)
    active: dict[str, dict[str, Any]] = {}
    previous_weights: dict[str, float] = {}
    equity = 1.0
    equity_values: list[float] = []
    daily_returns: list[float] = []
    turnover_total = 0.0
    active_total = 0
    for day in session_slice:
        for ticker in list(active):
            if day > active[ticker]["exit_date"]:
                del active[ticker]
        for signal in signals_by_day.get(day, []):
            active[signal["ticker"]] = signal
        weight = 1.0 / len(active) if active else 0.0
        target_weights = {ticker: weight for ticker in active}
        turnover = sum(
            abs(target_weights.get(ticker, 0.0) - previous_weights.get(ticker, 0.0))
            for ticker in set(target_weights) | set(previous_weights)
        )
        turnover_total += turnover
        gross_return = 0.0
        for ticker, signal in active.items():
            ticker_prices = by_symbol[ticker]
            if day == signal["entry_date"]:
                open_price, close_price = ticker_prices[day]
                position_return = close_price / open_price - 1.0
            else:
                previous_position = positions[day] - 1
                previous_day = sessions[previous_position]
                _, close_price = ticker_prices[day]
                previous_close = ticker_prices[previous_day][1]
                position_return = close_price / previous_close - 1.0
            gross_return += target_weights[ticker] * position_return
        equity *= (1.0 - turnover * one_way_cost) * (1.0 + gross_return)
        equity_values.append(equity)
        daily_returns.append(equity_values[-1] / equity_values[-2] - 1.0 if len(equity_values) > 1 else equity - 1.0)
        active_total += len(active)
        previous_weights = target_weights
    terminal_liquidation_cost = sum(previous_weights.values()) * one_way_cost
    equity *= 1.0 - terminal_liquidation_cost
    equity_values[-1] = equity
    equity_series = pd.Series(equity_values, index=session_slice)
    return_values = equity_series.pct_change().fillna(equity_series.iloc[0] - 1.0)
    portfolio_metrics = _metrics(equity_series, return_values, max((end - start).days, 1))
    baselines: dict[str, dict[str, float]] = {}
    for symbol in baseline_symbols:
        if symbol not in by_symbol:
            raise ValueError(f"price snapshot 缺少 baseline：{symbol}")
        baselines[symbol], _ = _buy_hold_baseline(
            prices,
            symbol=symbol,
            start=start,
            end=end,
            one_way_cost=one_way_cost,
        )
    qqq_metrics = baselines["QQQ"]
    return {
        "signal_count": len(signals),
        "period": {"start": start.isoformat(), "end": end.isoformat()},
        "portfolio": portfolio_metrics,
        "QQQ": qqq_metrics,
        "baselines": baselines,
        "comparison": {
            "cagr_difference": portfolio_metrics["cagr"] - qqq_metrics["cagr"],
            "total_return_difference": portfolio_metrics["total_return"]
            - qqq_metrics["total_return"],
        },
        "average_active_positions": active_total / max(len(session_slice), 1),
        "annualized_turnover": turnover_total / max(len(session_slice), 1) * 252.0,
        "terminal_liquidation_cost": terminal_liquidation_cost,
    }
