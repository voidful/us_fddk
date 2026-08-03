from __future__ import annotations

import itertools
import math
from statistics import NormalDist

import numpy as np
import pandas as pd

from usfddk.metrics import compute_metrics, newey_west_mean_test
from usfddk.models import BacktestResult


def probabilistic_sharpe_ratio(
    returns: pd.Series,
    *,
    benchmark_sharpe: float = 0.0,
    periods_per_year: int = 252,
) -> dict[str, float]:
    """Probability that the population Sharpe exceeds an annualized hurdle.

    This is the Bailey and Lopez de Prado finite-sample adjustment for skewness
    and kurtosis. It does not correct for trying many strategies; use
    ``deflated_sharpe_ratio`` for that selection penalty.
    """
    values = returns.dropna().astype(float)
    n = len(values)
    std = float(values.std(ddof=1))
    if n < 3 or std <= 0:
        return {
            "observed_sharpe": 0.0,
            "benchmark_sharpe": float(benchmark_sharpe),
            "sharpe_standard_error": float("nan"),
            "probability": float("nan"),
            "observations": float(n),
        }
    daily_sharpe = float(values.mean() / std)
    skew = float(values.skew())
    pearson_kurtosis = float(values.kurt()) + 3.0
    variance_term = max(
        1.0
        - skew * daily_sharpe
        + ((pearson_kurtosis - 1.0) / 4.0) * daily_sharpe**2,
        1e-12,
    )
    daily_se = math.sqrt(variance_term / (n - 1))
    annualizer = math.sqrt(float(periods_per_year))
    observed = daily_sharpe * annualizer
    annual_se = daily_se * annualizer
    z = (observed - float(benchmark_sharpe)) / annual_se
    return {
        "observed_sharpe": float(observed),
        "benchmark_sharpe": float(benchmark_sharpe),
        "sharpe_standard_error": float(annual_se),
        "skew": skew,
        "pearson_kurtosis": pearson_kurtosis,
        "z_score": float(z),
        "probability": float(NormalDist().cdf(z)),
        "observations": float(n),
    }


def deflated_sharpe_ratio(
    returns: pd.Series,
    *,
    trials: int,
    periods_per_year: int = 252,
) -> dict[str, float]:
    """Selection-adjusted Sharpe evidence using a conservative trial count."""
    if trials < 1:
        raise ValueError("trials 必須至少為 1")
    base = probabilistic_sharpe_ratio(returns, periods_per_year=periods_per_year)
    sharpe_se = float(base["sharpe_standard_error"])
    if not np.isfinite(sharpe_se):
        return {**base, "trials": float(trials), "expected_max_sharpe": float("nan")}
    if trials == 1:
        expected_max = 0.0
    else:
        normal = NormalDist()
        euler_gamma = 0.5772156649015329
        upper_one = normal.inv_cdf(1.0 - 1.0 / trials)
        upper_e = normal.inv_cdf(1.0 - 1.0 / (trials * math.e))
        expected_max = sharpe_se * ((1.0 - euler_gamma) * upper_one + euler_gamma * upper_e)
    z = (float(base["observed_sharpe"]) - expected_max) / sharpe_se
    return {
        **base,
        "trials": float(trials),
        "expected_max_sharpe": float(expected_max),
        "z_score": float(z),
        "probability": float(NormalDist().cdf(z)),
    }


def probability_of_backtest_overfitting(
    candidate_returns: pd.DataFrame,
    *,
    slices: int = 10,
) -> dict[str, object]:
    """CSCV estimate of how often the in-sample winner ranks below median OOS."""
    frame = candidate_returns.dropna(how="any")
    if slices < 4 or slices % 2:
        raise ValueError("slices 必須是至少 4 的偶數")
    if len(frame) < slices * 20 or frame.shape[1] < 2:
        return {"pbo": float("nan"), "combinations": 0, "logits": []}
    blocks = [np.asarray(x, dtype=int) for x in np.array_split(np.arange(len(frame)), slices)]
    logits: list[float] = []
    oos_sharpes: list[float] = []
    selections: dict[str, int] = {str(column): 0 for column in frame.columns}
    for train_blocks in itertools.combinations(range(slices), slices // 2):
        train_set = set(train_blocks)
        train_idx = np.concatenate([blocks[idx] for idx in train_blocks])
        test_idx = np.concatenate([blocks[idx] for idx in range(slices) if idx not in train_set])
        train = frame.iloc[train_idx]
        test = frame.iloc[test_idx]
        train_std = train.std(ddof=1).replace(0.0, np.nan)
        train_sharpe = train.mean().div(train_std) * math.sqrt(252.0)
        if train_sharpe.dropna().empty:
            continue
        selected_key = train_sharpe.idxmax()
        selected = str(selected_key)
        selections[selected] += 1
        test_std = test.std(ddof=1).replace(0.0, np.nan)
        test_sharpe = test.mean().div(test_std) * math.sqrt(252.0)
        selected_oos = float(test_sharpe[selected_key])
        ranks = test_sharpe.rank(method="average", ascending=True)
        percentile = (float(ranks[selected_key]) - 0.5) / len(test_sharpe)
        percentile = min(max(percentile, 1e-12), 1.0 - 1e-12)
        logits.append(float(math.log(percentile / (1.0 - percentile))))
        oos_sharpes.append(selected_oos)
    return {
        "pbo": float(np.mean(np.asarray(logits) <= 0.0)) if logits else float("nan"),
        "combinations": len(logits),
        "median_selected_oos_sharpe": float(np.median(oos_sharpes))
        if oos_sharpes
        else float("nan"),
        "logits": logits,
        "selections": selections,
    }


def compare_to_benchmark(strategy: BacktestResult, benchmark: BacktestResult) -> dict[str, float]:
    aligned = pd.concat(
        [strategy.returns.rename("strategy"), benchmark.returns.rename("benchmark")], axis=1
    ).dropna()
    active = aligned["strategy"] - aligned["benchmark"]
    test = newey_west_mean_test(active)
    strategy_years = strategy.metrics.get("cagr", 0.0)
    benchmark_years = benchmark.metrics.get("cagr", 0.0)
    return {
        "cagr_difference": float(strategy_years - benchmark_years),
        "sharpe_difference": float(
            strategy.metrics.get("sharpe", 0.0) - benchmark.metrics.get("sharpe", 0.0)
        ),
        "active_return_nw": test["annualized"],
        "active_return_t": test["t_stat"],
        "observations": float(len(aligned)),
    }


def block_bootstrap_cagr(
    returns: pd.Series,
    *,
    samples: int = 1_000,
    block_size: int = 21,
    seed: int = 20260801,
) -> dict[str, float]:
    values = returns.dropna().to_numpy(dtype=float)
    n = len(values)
    if n < block_size * 2 or samples <= 0:
        return {
            "low": float("nan"),
            "median": float("nan"),
            "high": float("nan"),
            "p_below_zero": float("nan"),
        }
    rng = np.random.default_rng(seed)
    out = np.empty(samples, dtype=float)
    blocks_needed = int(np.ceil(n / block_size))
    for i in range(samples):
        starts = rng.integers(0, n, size=blocks_needed)
        sample = np.concatenate([values[(start + np.arange(block_size)) % n] for start in starts])[
            :n
        ]
        gross = float(np.prod(1.0 + sample))
        out[i] = gross ** (252.0 / n) - 1.0
    low, median, high = np.quantile(out, [0.025, 0.5, 0.975])
    return {
        "low": float(low),
        "median": float(median),
        "high": float(high),
        "p_below_zero": float((out < 0).mean()),
    }


def subperiod_metrics(
    result: BacktestResult, splits: list[tuple[str, str, str]]
) -> dict[str, dict[str, float]]:
    output: dict[str, dict[str, float]] = {}
    for label, start, end in splits:
        equity = result.equity.loc[start:end]
        returns = result.returns.loc[start:end]
        turnover = result.turnover.loc[start:end]
        output[label] = compute_metrics(equity, returns, turnover)
    return output


def stress_period_metrics(
    results: list[BacktestResult],
    periods: list[tuple[str, str, str]],
) -> dict[str, dict[str, dict[str, float | str]]]:
    """Measure realized return and drawdown inside predeclared market stress windows."""
    output: dict[str, dict[str, dict[str, float | str]]] = {}
    for label, start, end in periods:
        rows: dict[str, dict[str, float | str]] = {}
        for result in results:
            equity = result.equity.loc[start:end].dropna()
            if len(equity) < 2:
                continue
            rows[result.name] = {
                "start": pd.Timestamp(equity.index[0]).strftime("%Y-%m-%d"),
                "end": pd.Timestamp(equity.index[-1]).strftime("%Y-%m-%d"),
                "return": float(equity.iloc[-1] / equity.iloc[0] - 1.0),
                "max_drawdown": float((equity / equity.cummax() - 1.0).min()),
                "worst_day": float(result.returns.loc[equity.index].min()),
            }
        output[label] = rows
    return output


def rolling_metrics(
    result: BacktestResult,
    *,
    window: int = 756,
) -> dict[str, object]:
    """Return month-end samples of rolling three-year risk and return metrics."""
    equity = result.equity.dropna()
    if len(equity) <= window:
        return {"window_sessions": window, "series": [], "summary": {}}
    periods = pd.Series(equity.index.to_period("M"), index=equity.index)
    month_end = periods.ne(periods.shift(-1)).fillna(True)
    endpoints = equity.index[month_end.to_numpy()]
    rows: list[dict[str, float | str]] = []
    for end in endpoints:
        position = equity.index.get_loc(end)
        if not isinstance(position, int) or position < window:
            continue
        window_equity = equity.iloc[position - window : position + 1]
        window_returns = result.returns.reindex(window_equity.index).fillna(0.0)
        window_turnover = result.turnover.reindex(window_equity.index).fillna(0.0)
        metrics = compute_metrics(window_equity, window_returns, window_turnover)
        rows.append(
            {
                "end": pd.Timestamp(end).strftime("%Y-%m-%d"),
                "cagr": float(metrics["cagr"]),
                "sharpe": float(metrics["sharpe"]),
                "max_drawdown": float(metrics["max_drawdown"]),
            }
        )
    if not rows:
        return {"window_sessions": window, "series": [], "summary": {}}
    frame = pd.DataFrame(rows)
    summary = {
        "latest_cagr": float(frame.iloc[-1]["cagr"]),
        "latest_sharpe": float(frame.iloc[-1]["sharpe"]),
        "latest_max_drawdown": float(frame.iloc[-1]["max_drawdown"]),
        "worst_cagr": float(frame["cagr"].min()),
        "median_cagr": float(frame["cagr"].median()),
        "worst_max_drawdown": float(frame["max_drawdown"].min()),
        "positive_cagr_fraction": float((frame["cagr"] > 0).mean()),
    }
    return {"window_sessions": window, "series": rows, "summary": summary}
