"""Internal performance and baseline comparison for the frozen raw ledger.

The functions here consume ``RawAccountingResult`` objects only.  They compute
descriptive metrics and same-session active-return diagnostics; they do not
decide whether a strategy is profitable, authorize Paper, or write public site
data.  Formal promotion gates remain in the pre-registration auditor.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from typing import Any

import numpy as np
import pandas as pd

from .formal_baseline_schedule import FORMAL_BASELINE_KEYS
from .formal_raw_accounting import RawAccountingResult
from .metrics import max_drawdown, newey_west_mean_test
from .validation import deflated_sharpe_ratio, probabilistic_sharpe_ratio

FORMAL_PERFORMANCE_VERSION = "round21-formal-performance-v1"
TRADING_DAYS_PER_YEAR = 252
_TOLERANCE = 1e-12


class FormalPerformanceError(ValueError):
    """Fail-closed performance input error with a stable code."""

    def __init__(self, code: str, detail: str):
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}")


def _fail(code: str, detail: str) -> None:
    raise FormalPerformanceError(code, detail)


def _curve(account: RawAccountingResult | pd.DataFrame) -> pd.DataFrame:
    frame = account.equity_curve.copy() if isinstance(account, RawAccountingResult) else account.copy()
    required = {"session", "equity"}
    missing = sorted(required - set(frame.columns))
    if missing:
        _fail("performance_curve_schema_invalid", f"equity curve 缺欄位：{missing}")
    dates = pd.to_datetime(frame["session"], format="%Y-%m-%d", errors="coerce")
    equity = pd.to_numeric(frame["equity"], errors="coerce")
    if dates.isna().any() or dates.duplicated().any() or not dates.is_monotonic_increasing:
        _fail("performance_curve_schema_invalid", "session 必須唯一遞增")
    if equity.isna().any() or not np.isfinite(equity).all() or (equity <= 0).any():
        _fail("performance_curve_schema_invalid", "equity 必須為正有限數")
    frame["__session"] = pd.DatetimeIndex(dates).normalize()
    frame["__equity"] = equity.astype(float)
    return frame


def _returns(frame: pd.DataFrame) -> pd.Series:
    return frame.set_index("__session")["__equity"].pct_change(fill_method=None).fillna(0.0)


def _risk_free_series(
    risk_free: pd.Series | pd.DataFrame | None,
    dates: pd.DatetimeIndex,
) -> pd.Series:
    if risk_free is None:
        return pd.Series(0.0, index=dates, dtype=float)
    if isinstance(risk_free, pd.DataFrame):
        if not {"session", "risk_free_return"} <= set(risk_free.columns):
            _fail("performance_risk_free_schema_invalid", "RF 缺 session／risk_free_return")
        parsed = pd.to_datetime(risk_free["session"], format="%Y-%m-%d", errors="coerce")
        values = pd.to_numeric(risk_free["risk_free_return"], errors="coerce")
        if parsed.isna().any() or parsed.duplicated().any():
            _fail("performance_risk_free_schema_invalid", "RF session 無效或重複")
        series = pd.Series(values.to_numpy(dtype=float), index=pd.DatetimeIndex(parsed).normalize())
    elif isinstance(risk_free, pd.Series):
        parsed = pd.to_datetime(risk_free.index, errors="coerce")
        if pd.isna(parsed).any() or parsed.has_duplicates:
            _fail("performance_risk_free_schema_invalid", "RF index 無效或重複")
        series = pd.Series(risk_free.to_numpy(dtype=float), index=pd.DatetimeIndex(parsed).normalize())
    else:
        _fail("performance_risk_free_schema_invalid", "RF 必須是 Series／DataFrame")
    if series.isna().any() or not np.isfinite(series.to_numpy(dtype=float)).all():
        _fail("performance_risk_free_schema_invalid", "RF 含非有限數字")
    if (series <= -1.0).any() or series.abs().gt(0.01).any():
        _fail("performance_risk_free_value_invalid", "RF 日回報量級無效")
    if set(series.index) != set(dates):
        _fail("performance_risk_free_session_mismatch", "RF sessions 必須與帳本一對一")
    return series.reindex(dates).astype(float)


def _years(dates: pd.DatetimeIndex) -> float:
    elapsed = (dates[-1] - dates[0]).days / 365.2425
    if elapsed <= 0.0:
        _fail("performance_period_invalid", "研究期必須跨越至少兩個日期")
    return float(elapsed)


def _turnover_series(
    account: RawAccountingResult | pd.DataFrame,
    frame: pd.DataFrame,
) -> pd.Series:
    index = pd.DatetimeIndex(frame["__session"])
    notional = pd.Series(0.0, index=index)
    if not isinstance(account, RawAccountingResult) or account.trades.empty:
        return notional
    trades = account.trades.copy()
    if not {"session", "gross_notional"} <= set(trades.columns):
        _fail("performance_trade_schema_invalid", "trades 缺 session／gross_notional")
    trade_dates = pd.to_datetime(trades["session"], format="%Y-%m-%d", errors="coerce")
    amounts = pd.to_numeric(trades["gross_notional"], errors="coerce").abs()
    if trade_dates.isna().any() or amounts.isna().any() or not np.isfinite(amounts).all():
        _fail("performance_trade_schema_invalid", "trades 日期或成交金額無效")
    if not set(pd.DatetimeIndex(trade_dates).normalize()).issubset(set(index)):
        _fail("performance_trade_schema_invalid", "trades session 不在 equity curve")
    for date, amount in zip(pd.DatetimeIndex(trade_dates).normalize(), amounts, strict=True):
        notional.loc[date] += float(amount)
    previous_equity = frame.set_index("__session")["__equity"].shift(1)
    previous_equity.iloc[0] = frame.iloc[0]["__equity"]
    return notional.div(previous_equity)


def _downside_deviation(excess: pd.Series) -> float:
    negative = np.minimum(excess.to_numpy(dtype=float), 0.0)
    return float(np.sqrt(np.mean(negative**2)) * math.sqrt(TRADING_DAYS_PER_YEAR))


def compute_formal_metrics(
    account: RawAccountingResult | pd.DataFrame,
    *,
    risk_free: pd.Series | pd.DataFrame | None = None,
) -> dict[str, float | int | str]:
    """Compute fixed descriptive metrics for one raw-account path."""

    frame = _curve(account)
    dates = pd.DatetimeIndex(frame["__session"])
    years = _years(dates)
    equity = frame.set_index("__session")["__equity"]
    returns = _returns(frame)
    rf = _risk_free_series(risk_free, dates)
    excess = returns - rf
    std = float(returns.std(ddof=1)) if len(returns) > 1 else 0.0
    excess_std = float(excess.std(ddof=1)) if len(excess) > 1 else 0.0
    downside = _downside_deviation(excess)
    total_return = float(equity.iloc[-1] / equity.iloc[0] - 1.0)
    cagr = float((equity.iloc[-1] / equity.iloc[0]) ** (1.0 / years) - 1.0)
    drawdown = max_drawdown(equity)
    turnover = _turnover_series(account, frame)
    total_costs = float(
        pd.to_numeric(account.trades["cost"], errors="coerce").sum()
        if isinstance(account, RawAccountingResult) and not account.trades.empty
        else 0.0
    )
    if not math.isfinite(total_costs) or total_costs < 0.0:
        _fail("performance_trade_schema_invalid", "交易成本必須為非負有限數")
    return {
        "version": FORMAL_PERFORMANCE_VERSION,
        "sessions": int(len(equity)),
        "years": years,
        "total_return": total_return,
        "cagr": cagr,
        "volatility": std * math.sqrt(TRADING_DAYS_PER_YEAR),
        "excess_sharpe": (float(excess.mean()) / excess_std * math.sqrt(TRADING_DAYS_PER_YEAR))
        if excess_std > 0.0
        else 0.0,
        "excess_sortino": float(excess.mean()) / downside * math.sqrt(TRADING_DAYS_PER_YEAR)
        if downside > 0.0
        else 0.0,
        "max_drawdown": float(drawdown),
        "calmar": float(cagr / abs(drawdown)) if drawdown < 0.0 else 0.0,
        "annual_turnover": float(turnover.sum() / years),
        "total_costs": total_costs,
        "transactions": int(len(account.trades)) if isinstance(account, RawAccountingResult) else 0,
        "terminal_usd": float(equity.iloc[-1]),
        "average_exposure": float(
            frame["positions_value"].div(frame["equity"]).mean()
        )
        if {"positions_value", "equity"} <= set(frame.columns)
        else 0.0,
        "maximum_exposure": float(
            frame["positions_value"].div(frame["equity"]).max()
        )
        if {"positions_value", "equity"} <= set(frame.columns)
        else 0.0,
    }


def compare_account_to_baseline(
    candidate: RawAccountingResult | pd.DataFrame,
    baseline: RawAccountingResult | pd.DataFrame,
    *,
    baseline_key: str,
    risk_free: pd.Series | pd.DataFrame | None = None,
    global_trials: int,
) -> dict[str, Any]:
    """Compare two paths on their exact common session path."""

    candidate_frame = _curve(candidate).set_index("__session")
    baseline_frame = _curve(baseline).set_index("__session")
    aligned = pd.concat(
        [candidate_frame["__equity"].rename("candidate"), baseline_frame["__equity"].rename("baseline")],
        axis=1,
        join="inner",
    ).dropna()
    if len(aligned) < 3 or not aligned.index.is_monotonic_increasing:
        _fail("performance_baseline_session_mismatch", f"{baseline_key} 共同 session 不足")
    candidate_returns = aligned["candidate"].pct_change(fill_method=None).fillna(0.0)
    baseline_returns = aligned["baseline"].pct_change(fill_method=None).fillna(0.0)
    active = candidate_returns - baseline_returns
    nw = newey_west_mean_test(active)
    psr = probabilistic_sharpe_ratio(active, benchmark_sharpe=0.0)
    dsr = deflated_sharpe_ratio(active, trials=global_trials)
    candidate_metrics = compute_formal_metrics(candidate, risk_free=risk_free)
    baseline_metrics = compute_formal_metrics(baseline, risk_free=risk_free)
    return {
        "baseline_key": baseline_key,
        "observations": int(len(active)),
        "cagr_difference": float(candidate_metrics["cagr"] - baseline_metrics["cagr"]),
        "max_drawdown_difference": float(
            candidate_metrics["max_drawdown"] - baseline_metrics["max_drawdown"]
        ),
        "positive_active_fraction": float((active > 0.0).mean()),
        "active_return_newey_west": nw,
        "active_psr": psr,
        "active_dsr": dsr,
        "risk_free_series_supplied": risk_free is not None,
    }


def compare_formal_paths(
    paths: Mapping[str, RawAccountingResult | pd.DataFrame],
    *,
    candidate_key: str,
    baseline_keys: tuple[str, ...],
    risk_free: pd.Series | pd.DataFrame | None = None,
    global_trials: int,
) -> dict[str, Any]:
    """Return internal metrics and all pre-registered baseline comparisons."""

    if candidate_key not in paths:
        _fail("performance_candidate_missing", f"缺 candidate path：{candidate_key}")
    if global_trials < 1:
        _fail("performance_statistics_policy_invalid", "global trials 必須為正")
    if tuple(baseline_keys) != FORMAL_BASELINE_KEYS:
        _fail(
            "performance_baseline_policy_invalid",
            "正式比較必須按凍結次序包含四個 baseline",
        )
    missing = [key for key in baseline_keys if key not in paths]
    if missing:
        _fail("performance_baseline_missing", f"缺 baseline path：{missing}")
    metrics = {
        key: compute_formal_metrics(value, risk_free=risk_free)
        for key, value in paths.items()
    }
    comparisons = {
        key: compare_account_to_baseline(
            paths[candidate_key],
            paths[key],
            baseline_key=key,
            risk_free=risk_free,
            global_trials=global_trials,
        )
        for key in baseline_keys
    }
    return {
        "version": FORMAL_PERFORMANCE_VERSION,
        "candidate_key": candidate_key,
        "global_trials": int(global_trials),
        "metrics": metrics,
        "comparisons": comparisons,
        "paper_authorized": False,
        "real_money_action_usd": 0,
    }
