from __future__ import annotations

import numpy as np
import pandas as pd

from usfddk.metrics import compute_metrics
from usfddk.models import BacktestResult, MarketPanel


def execute_rebalance(
    shares: pd.Series,
    cash: float,
    open_prices: pd.Series,
    target: pd.Series,
    *,
    cost_bps: float,
) -> tuple[pd.Series, float, float, float, pd.Series]:
    """Rebalance at an opening auction and return shares, cash, turnover, cost, trades.

    The same primitive is shared by the historical engine and the persistent paper
    account so the two paths cannot quietly use different cost or sizing math.
    """
    symbols = list(dict.fromkeys([*shares.index, *target.index]))
    shares = shares.reindex(symbols, fill_value=0.0).astype(float)
    prices = open_prices.reindex(symbols).astype(float)
    target = target.reindex(symbols, fill_value=0.0).fillna(0.0).clip(lower=0.0)
    if float(target.sum()) > 1.0000001:
        raise ValueError("目標權重加總 > 1")
    held = shares != 0
    if bool(prices[held].isna().any()):
        raise ValueError("既有持倉缺少開盤價")
    tradable = target > 0
    if bool(prices[tradable].isna().any()):
        raise ValueError("目標持倉缺少開盤價")

    current_dollars = shares * prices.fillna(0.0)
    pretrade = float(cash + current_dollars.sum())
    if not np.isfinite(pretrade) or pretrade <= 0:
        raise ValueError(f"交易前權益無效：{pretrade}")
    rate = float(cost_bps) / 10_000.0
    investable = pretrade
    for _ in range(8):
        desired = target * investable
        traded = desired - current_dollars
        estimated_cost = rate * float(traded.abs().sum())
        new_investable = pretrade - estimated_cost
        if abs(new_investable - investable) < 1e-10:
            break
        investable = new_investable
    desired = target * investable
    traded = desired - current_dollars
    cost = rate * float(traded.abs().sum())
    turnover = float(traded.abs().sum() / pretrade)
    new_shares = desired.div(prices).replace([np.inf, -np.inf], 0.0).fillna(0.0)
    new_cash = pretrade - float(desired.sum()) - cost
    return new_shares, new_cash, turnover, cost, traded


def run_backtest(
    panel: MarketPanel,
    target_signals: pd.DataFrame,
    *,
    name: str,
    cost_bps: float = 10.0,
    start: str | pd.Timestamp | None = None,
) -> BacktestResult:
    """Execute close-t signals at open t+1, with drift and two-sided turnover costs."""
    tickers = [x for x in target_signals.columns if x in panel.close.columns]
    if not tickers:
        raise ValueError("目標權重與行情沒有共同代號")
    index = panel.close.index
    signals = target_signals.reindex(index=index, columns=tickers)
    execution = signals.shift(1)
    open_px = panel.open[tickers]
    close_px = panel.close[tickers]
    if start is not None:
        start_stamp = pd.Timestamp(start)
        index = index[index >= start_stamp]
    if len(index) < 2:
        raise ValueError("回測期間不足")

    open_px = open_px.loc[index]
    close_px = close_px.loc[index]
    execution = execution.loc[index]
    trade_positions = np.flatnonzero(execution.notna().any(axis=1).to_numpy())
    shares = pd.Series(0.0, index=tickers)
    cash = 1.0
    equity = pd.Series(index=index, dtype=float, name=name)
    turnover_series = pd.Series(0.0, index=index, name="turnover")
    cost_series = pd.Series(0.0, index=index, name="cost")
    weights = pd.DataFrame(0.0, index=index, columns=tickers)

    def value_interval(left: int, right: int) -> None:
        if right <= left:
            return
        held = shares != 0.0
        if bool(held.any()):
            held_columns = held.to_numpy()
            missing = open_px.iloc[left:right, held_columns].isna() | close_px.iloc[
                left:right, held_columns
            ].isna()
            if bool(missing.any(axis=None)):
                offset = int(np.flatnonzero(missing.any(axis=1).to_numpy())[0])
                row = left + offset
                missing_names = list(missing.columns[missing.iloc[offset].to_numpy()])
                raise ValueError(f"持倉遇到缺價 {index[row].date()}: {missing_names}")
        values = close_px.iloc[left:right].fillna(0.0).mul(shares, axis=1)
        interval_equity = values.sum(axis=1) + cash
        invalid = ~np.isfinite(interval_equity) | (interval_equity <= 0.0)
        if bool(invalid.any()):
            bad_day = interval_equity.index[np.flatnonzero(invalid.to_numpy())[0]]
            raise RuntimeError(f"{bad_day.date()} 權益無效：{interval_equity.loc[bad_day]}")
        equity.iloc[left:right] = interval_equity
        weights.iloc[left:right] = values.div(interval_equity, axis=0)

    cursor = 0
    for raw_position in trade_positions:
        position = int(raw_position)
        value_interval(cursor, position)
        day = index[position]
        day_open = open_px.loc[day]
        day_close = close_px.loc[day]
        held = shares != 0.0
        if bool((held & day_open.isna()).any()) or bool((held & day_close.isna()).any()):
            missing = list(day_open.index[held & (day_open.isna() | day_close.isna())])
            raise ValueError(f"持倉遇到缺價 {day.date()}: {missing}")
        try:
            shares, cash, turnover, cost, _ = execute_rebalance(
                shares,
                cash,
                day_open,
                execution.loc[day],
                cost_bps=cost_bps,
            )
        except ValueError as exc:
            raise ValueError(f"{day.date()} {exc}") from exc
        turnover_series.loc[day] = turnover
        cost_series.loc[day] = cost
        cursor = position
    value_interval(cursor, len(index))

    returns = equity.pct_change(fill_method=None).fillna(0.0).rename(name)
    metrics = compute_metrics(equity, returns, turnover_series)
    signal_rows = signals.dropna(how="all")
    current_target = (
        signal_rows.iloc[-1].fillna(0.0) if len(signal_rows) else pd.Series(0.0, index=tickers)
    )
    diagnostics = {
        "cost_bps": float(cost_bps),
        "rebalance_count": int((turnover_series > 0).sum()),
        "total_cost_fraction_initial": float(cost_series.sum()),
        "execution_clock": "signal at close t; rebalance at adjusted open t+1",
        "engine": "sparse_interval_vectorized_shared_execution_primitive",
    }
    return BacktestResult(
        name=name,
        equity=equity,
        returns=returns,
        weights=weights,
        turnover=turnover_series,
        costs=cost_series,
        metrics=metrics,
        current_target=current_target.sort_values(ascending=False),
        diagnostics=diagnostics,
    )
