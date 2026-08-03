from __future__ import annotations

import math

import numpy as np
import pandas as pd

TRADING_DAYS = 252


def max_drawdown(equity: pd.Series) -> float:
    clean = equity.dropna()
    if clean.empty:
        return 0.0
    return float((clean / clean.cummax() - 1.0).min())


def compute_metrics(
    equity: pd.Series,
    returns: pd.Series,
    turnover: pd.Series,
    *,
    periods_per_year: int = TRADING_DAYS,
) -> dict[str, float]:
    eq = equity.dropna()
    ret = returns.dropna()
    if len(eq) < 2:
        return {
            k: 0.0
            for k in (
                "total_return",
                "cagr",
                "volatility",
                "sharpe",
                "sortino",
                "max_drawdown",
                "calmar",
                "turnover",
            )
        }
    years = max((eq.index[-1] - eq.index[0]).days / 365.2425, 1 / 365.2425)
    total = float(eq.iloc[-1] / eq.iloc[0] - 1.0)
    cagr = float((eq.iloc[-1] / eq.iloc[0]) ** (1.0 / years) - 1.0)
    std = float(ret.std(ddof=1))
    vol = std * math.sqrt(periods_per_year)
    sharpe = float(ret.mean() / std * math.sqrt(periods_per_year)) if std > 0 else 0.0
    downside = ret[ret < 0]
    downside_std = float(downside.std(ddof=1))
    sortino = (
        float(ret.mean() / downside_std * math.sqrt(periods_per_year))
        if downside_std > 0
        else 0.0
    )
    mdd = max_drawdown(eq)
    calmar = cagr / abs(mdd) if mdd < 0 else 0.0
    annual_turnover = float(turnover.sum() / years)
    return {
        "total_return": total,
        "cagr": cagr,
        "volatility": vol,
        "sharpe": sharpe,
        "sortino": sortino,
        "max_drawdown": mdd,
        "calmar": calmar,
        "turnover": annual_turnover,
    }


def newey_west_mean_test(
    series: pd.Series,
    max_lag: int | None = None,
    *,
    periods_per_year: int = TRADING_DAYS,
) -> dict[str, float]:
    values = series.dropna().to_numpy(dtype=float)
    n = len(values)
    if n < 3:
        return {"mean_daily": 0.0, "annualized": 0.0, "t_stat": 0.0, "lag": 0.0}
    centered = values - values.mean()
    if max_lag is None:
        max_lag = int(math.floor(4 * (n / 100) ** (2 / 9)))
    gamma0 = float(np.dot(centered, centered) / n)
    long_run = gamma0
    for lag in range(1, min(max_lag, n - 1) + 1):
        gamma = float(np.dot(centered[lag:], centered[:-lag]) / n)
        weight = 1.0 - lag / (max_lag + 1)
        long_run += 2.0 * weight * gamma
    se_mean = math.sqrt(max(long_run, 0.0) / n)
    mean = float(values.mean())
    t_stat = mean / se_mean if se_mean > 0 else 0.0
    return {
        "mean_daily": mean,
        "annualized": mean * periods_per_year,
        "t_stat": float(t_stat),
        "lag": float(max_lag),
    }


def annual_returns(returns: pd.Series) -> pd.Series:
    clean = returns.dropna()
    return clean.groupby(clean.index.year).apply(lambda x: float((1.0 + x).prod() - 1.0))
