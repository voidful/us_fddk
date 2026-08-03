from __future__ import annotations

import csv
import hashlib
import io
import math
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from usfddk.metrics import newey_west_mean_test
from usfddk.short_term_high_return import _moving_block_bootstrap_mean
from usfddk.validation import (
    deflated_sharpe_ratio,
    probabilistic_sharpe_ratio,
    probability_of_backtest_overfitting,
)

SCHEMA_VERSION = 1
PROTOCOL_SHA256 = "71c32560fd4234504cf1005686824278173f6034f7cf1a7f9179b8c587613db3"
MAPPING_SHA256 = "ae02ad3e9fa201e036b33319c7398a804e99567b2fc60ef263240f4cf8f1d0df"
PROTOCOL_COMMIT = "2ca60d4187e874b4a208029d8f18a08c21a2227a"
SNAPSHOT_COMMIT = "ddb1c178a9317687cc78f7a5f20cbf25d7f60891"
INDUSTRY_SHA256 = "7140a2dbbae2b9fa871ac99c223c4310efd2aa526bb9fa6170b118dbd1d61848"
FACTORS_SHA256 = "af8aec07d55c98caa15045a77b87455be68cb8847b2ee5bd03bf5c2c8a3f96e2"
MOMENTUM_SHA256 = "f4237e2e36dffa13fd7823f55376316a94b5ac663af951dd9eaca8ed2c678bcf"
FORMAL_START = pd.Timestamp("1963-01-02")
FORMAL_END = pd.Timestamp("2026-05-29")
PRIMARY_END = pd.Timestamp("2005-12-31")
RECENT_START = pd.Timestamp("2006-01-01")
PRIMARY_TOP_K = 3
TOP_K_NEIGHBORS = (2, 3, 5)
PRIMARY_COST_BPS = 10.0
STRESS_COST_BPS = (25.0, 50.0)
GLOBAL_SEARCH_TRIALS = 6_144
LOOKBACK_START = 126
SKIP_SESSIONS = 20


@dataclass(frozen=True)
class ReturnPath:
    returns: pd.Series
    turnover: pd.Series


def _sha256(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _extract_csv(path: str | Path) -> str:
    with zipfile.ZipFile(path) as bundle:
        members = [
            name
            for name in bundle.namelist()
            if not name.endswith("/") and name.lower().endswith(".csv")
        ]
        if len(members) != 1:
            raise ValueError(f"French ZIP CSV member 數量錯誤：{members}")
        raw = bundle.read(members[0])
    for encoding in ("utf-8-sig", "latin-1"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise ValueError("French CSV 編碼無法辨識")


def _parse_daily_table(
    text: str,
    *,
    expected_columns: int | None = None,
    required: set[str] | None = None,
    marker: str | None = None,
) -> pd.DataFrame:
    rows = list(csv.reader(io.StringIO(text)))
    start = 0
    if marker is not None:
        marker_rows = [
            index
            for index, row in enumerate(rows)
            if marker in " ".join(cell.strip() for cell in row)
        ]
        if not marker_rows:
            raise ValueError(f"找不到 French 表格標記：{marker}")
        start = marker_rows[0] + 1
    header_index: int | None = None
    for index in range(start, len(rows)):
        names = [cell.strip() for cell in rows[index][1:] if cell.strip()]
        if expected_columns is not None and len(names) == expected_columns:
            header_index = index
            break
        if required is not None and required.issubset(set(names)):
            header_index = index
            break
    if header_index is None:
        raise ValueError("找不到 French 日資料欄名")
    columns = [cell.strip() for cell in rows[header_index][1:] if cell.strip()]
    if expected_columns is not None and len(columns) != expected_columns:
        raise ValueError("French 行業欄數不符")

    dates: list[pd.Timestamp] = []
    values: list[list[float]] = []
    started = False
    for row in rows[header_index + 1 :]:
        first = row[0].strip() if row else ""
        if len(first) != 8 or not first.isdigit():
            if started:
                break
            continue
        started = True
        parsed: list[float] = []
        for cell in row[1 : len(columns) + 1]:
            value = float(cell.strip())
            parsed.append(np.nan if value in (-99.99, -999.0) else value / 100.0)
        if len(parsed) != len(columns):
            raise ValueError(f"French {first} 欄數不符")
        dates.append(pd.to_datetime(first, format="%Y%m%d"))
        values.append(parsed)
    frame = pd.DataFrame(values, index=pd.DatetimeIndex(dates), columns=columns)
    if frame.index.has_duplicates or not frame.index.is_monotonic_increasing:
        raise ValueError("French 日期重複或未嚴格遞增")
    return frame


def load_frozen_french_daily(
    industry_path: str | Path,
    factors_path: str | Path,
    momentum_path: str | Path,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    if _sha256(industry_path) != INDUSTRY_SHA256:
        raise ValueError("French 30 行業 ZIP 雜湊不符")
    if _sha256(factors_path) != FACTORS_SHA256:
        raise ValueError("French 日因素 ZIP 雜湊不符")
    if _sha256(momentum_path) != MOMENTUM_SHA256:
        raise ValueError("French 日 Mom ZIP 雜湊不符")
    industry = _parse_daily_table(
        _extract_csv(industry_path),
        expected_columns=30,
        marker="Average Value Weighted Returns -- Daily",
    )
    factors = _parse_daily_table(
        _extract_csv(factors_path),
        required={"Mkt-RF", "SMB", "HML", "RF"},
    )
    momentum = _parse_daily_table(_extract_csv(momentum_path), required={"Mom"})
    index = industry.index.intersection(factors.index).intersection(momentum.index)
    industry = industry.reindex(index).loc[:FORMAL_END]
    factors = pd.concat([factors, momentum[["Mom"]]], axis=1).reindex(index)
    factors = factors.loc[:FORMAL_END]
    formal_industry = industry.loc[FORMAL_START:FORMAL_END]
    formal_factors = factors.loc[FORMAL_START:FORMAL_END]
    if industry.shape[1] != 30 or formal_industry.isna().any().any():
        raise ValueError("French 30 正式期不完整")
    if formal_factors[["Mkt-RF", "SMB", "HML", "RF", "Mom"]].isna().any().any():
        raise ValueError("French 因素正式期不完整")
    if formal_industry.index[0] != FORMAL_START or formal_industry.index[-1] != FORMAL_END:
        raise ValueError("French 30 正式日期與凍結收據不符")
    return industry, factors


def _completed_period_dates(index: pd.DatetimeIndex, frequency: str) -> pd.DatetimeIndex:
    if frequency == "monthly":
        periods = pd.Series(index.to_period("M"), index=index)
    elif frequency == "weekly":
        periods = pd.Series(index.to_period("W-FRI"), index=index)
    else:
        raise ValueError("frequency 必須為 monthly 或 weekly")
    return index[periods.ne(periods.shift(-1)).fillna(True).to_numpy()]


def industry_momentum_targets(
    returns: pd.DataFrame,
    *,
    top_k: int,
    signal_start: pd.Timestamp = FORMAL_START,
) -> tuple[pd.DataFrame, dict[str, list[str]]]:
    if top_k not in TOP_K_NEIGHBORS:
        raise ValueError("Top-K 不在凍結鄰域")
    targets = pd.DataFrame(np.nan, index=returns.index, columns=returns.columns)
    selections: dict[str, list[str]] = {}
    for day in _completed_period_dates(returns.index, "monthly"):
        if day < signal_start:
            continue
        position = returns.index.get_loc(day)
        if not isinstance(position, int) or position < LOOKBACK_START:
            continue
        window = returns.iloc[position - LOOKBACK_START : position - SKIP_SESSIONS]
        if len(window) != LOOKBACK_START - SKIP_SESSIONS or window.isna().any().any():
            continue
        score = (1.0 + window).prod(axis=0) - 1.0
        selected = sorted(
            list(returns.columns),
            key=lambda name: (-float(score[name]), str(name)),
        )[:top_k]
        row = pd.Series(0.0, index=returns.columns)
        row.loc[selected] = 1.0 / top_k
        targets.loc[day] = row
        selections[day.date().isoformat()] = selected
    if not selections:
        raise ValueError("French 30 沒有可用月度訊號")
    return targets, selections


def equal_monthly_targets(
    returns: pd.DataFrame,
    *,
    signal_start: pd.Timestamp = FORMAL_START,
) -> pd.DataFrame:
    targets = pd.DataFrame(np.nan, index=returns.index, columns=returns.columns)
    signal_dates = _completed_period_dates(returns.index, "monthly")
    targets.loc[signal_dates[signal_dates >= signal_start]] = 1.0 / returns.shape[1]
    return targets


def _simulate(
    returns: pd.DataFrame,
    targets: pd.DataFrame,
    *,
    cost_bps: float,
) -> ReturnPath:
    targets = targets.reindex(index=returns.index, columns=returns.columns)
    weights = pd.Series(0.0, index=returns.columns)
    path_returns = pd.Series(0.0, index=returns.index, name="return")
    turnover = pd.Series(0.0, index=returns.index, name="turnover")
    rate = float(cost_bps) / 10_000.0
    for position, day in enumerate(returns.index):
        cost_fraction = 0.0
        if position > 0:
            signal = targets.iloc[position - 1]
            if signal.notna().any():
                target = signal.fillna(0.0)
                if not math.isclose(float(target.sum()), 1.0, rel_tol=0.0, abs_tol=1e-9):
                    raise ValueError(f"{day.date()} 目標權重不等於 1")
                traded = float((target - weights).abs().sum())
                turnover.iloc[position] = traded
                cost_fraction = rate * traded
                weights = target
        asset_return = returns.iloc[position]
        gross_return = float((weights * asset_return).sum())
        net_return = (1.0 - cost_fraction) * (1.0 + gross_return) - 1.0
        path_returns.iloc[position] = net_return
        denominator = 1.0 + gross_return
        if denominator <= 0.0:
            raise ValueError(f"{day.date()} 組合回報低於 -100%")
        if float(weights.sum()) > 0.0:
            weights = weights.mul(1.0 + asset_return).div(denominator)
    return ReturnPath(returns=path_returns, turnover=turnover)


def _slice_path(path: ReturnPath, start: pd.Timestamp, end: pd.Timestamp) -> ReturnPath:
    returns = path.returns.loc[start:end].copy()
    turnover = path.turnover.reindex(returns.index).fillna(0.0)
    return ReturnPath(returns=returns, turnover=turnover)


def _metrics(path: ReturnPath, risk_free: pd.Series) -> dict[str, float]:
    aligned = pd.concat(
        [path.returns.rename("return"), risk_free.rename("rf")],
        axis=1,
        join="inner",
    ).dropna()
    values = aligned["return"]
    n = len(values)
    if n < 2:
        raise ValueError("回報期不足")
    wealth = (1.0 + values).cumprod()
    wealth_with_anchor = pd.concat(
        [pd.Series([1.0], index=[values.index[0] - pd.Timedelta(days=1)]), wealth]
    )
    total = float(wealth.iloc[-1] - 1.0)
    cagr = float(wealth.iloc[-1] ** (252.0 / n) - 1.0)
    volatility = float(values.std(ddof=1) * np.sqrt(252.0))
    excess = aligned["return"] - aligned["rf"]
    excess_std = float(excess.std(ddof=1))
    excess_sharpe = (
        float(excess.mean() / excess_std * np.sqrt(252.0)) if excess_std > 0.0 else 0.0
    )
    downside = values[values < 0.0]
    downside_std = float(downside.std(ddof=1))
    sortino = (
        float(values.mean() / downside_std * np.sqrt(252.0)) if downside_std > 0.0 else 0.0
    )
    drawdown = wealth_with_anchor / wealth_with_anchor.cummax() - 1.0
    max_drawdown = float(drawdown.min())
    years = n / 252.0
    return {
        "total_return": total,
        "cagr": cagr,
        "volatility": volatility,
        "excess_sharpe": excess_sharpe,
        "sortino": sortino,
        "max_drawdown": max_drawdown,
        "calmar": cagr / abs(max_drawdown) if max_drawdown < 0.0 else 0.0,
        "annual_turnover": float(path.turnover.reindex(values.index).sum() / years),
        "sessions": float(n),
        "hypothetical_1000_usd_end": float(1_000.0 * wealth.iloc[-1]),
    }


def _active_comparison(candidate: ReturnPath, benchmark: ReturnPath) -> dict[str, Any]:
    aligned = pd.concat(
        [candidate.returns.rename("candidate"), benchmark.returns.rename("benchmark")],
        axis=1,
        join="inner",
    ).dropna()
    active = aligned["candidate"] - aligned["benchmark"]
    return {
        "mean_daily": float(active.mean()),
        "annualized_arithmetic": float(active.mean() * 252.0),
        "newey_west": newey_west_mean_test(active, max_lag=9),
        "active_probabilistic_sharpe": probabilistic_sharpe_ratio(active),
        "active_global_deflated_sharpe": deflated_sharpe_ratio(
            active,
            trials=GLOBAL_SEARCH_TRIALS,
        ),
    }


def _rolling_comparison(
    candidate: ReturnPath,
    benchmark: ReturnPath,
    *,
    window: int = 1_260,
) -> dict[str, Any]:
    aligned = pd.concat(
        [candidate.returns.rename("candidate"), benchmark.returns.rename("benchmark")],
        axis=1,
        join="inner",
    ).dropna()
    endpoints = _completed_period_dates(aligned.index, "monthly")
    rows: list[dict[str, Any]] = []
    for end in endpoints:
        position = aligned.index.get_loc(end)
        if not isinstance(position, int) or position + 1 < window:
            continue
        sample = aligned.iloc[position - window + 1 : position + 1]
        candidate_cagr = float((1.0 + sample["candidate"]).prod() ** (252.0 / window) - 1.0)
        benchmark_cagr = float((1.0 + sample["benchmark"]).prod() ** (252.0 / window) - 1.0)
        rows.append(
            {
                "end": end.date().isoformat(),
                "candidate_cagr": candidate_cagr,
                "benchmark_cagr": benchmark_cagr,
                "cagr_difference": candidate_cagr - benchmark_cagr,
            }
        )
    differences = pd.Series([row["cagr_difference"] for row in rows], dtype=float)
    return {
        "window_sessions": window,
        "observations": int(len(rows)),
        "cagr_win_fraction": float((differences > 0.0).mean()) if len(rows) else 0.0,
        "median_cagr_difference": float(differences.median()) if len(rows) else 0.0,
        "worst_cagr_difference": float(differences.min()) if len(rows) else 0.0,
        "latest_cagr_difference": float(differences.iloc[-1]) if len(rows) else 0.0,
        "series": rows,
    }


def _period_event_diagnostic(
    industry: pd.DataFrame,
    market: pd.Series,
    *,
    start: pd.Timestamp,
    end: pd.Timestamp,
    first_half_end: pd.Timestamp,
    second_half_start: pd.Timestamp,
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for signal_date in _completed_period_dates(industry.index, "weekly"):
        if signal_date < start or signal_date > end:
            continue
        position = industry.index.get_loc(signal_date)
        if not isinstance(position, int) or position < LOOKBACK_START:
            continue
        entry = position + 1
        exit_position = entry + 19
        if exit_position >= len(industry):
            continue
        window = industry.iloc[position - LOOKBACK_START : position - SKIP_SESSIONS]
        score = (1.0 + window).prod(axis=0) - 1.0
        selected = sorted(
            list(industry.columns),
            key=lambda name: (-float(score[name]), str(name)),
        )[:PRIMARY_TOP_K]
        holding = industry.iloc[entry : exit_position + 1]
        selected_return = float((1.0 + holding[selected]).prod(axis=0).mean() - 1.0 - 0.002)
        equal_return = float((1.0 + holding).prod(axis=0).mean() - 1.0 - 0.002)
        market_return = float((1.0 + market.iloc[entry : exit_position + 1]).prod() - 1.0 - 0.002)
        rows.append(
            {
                "signal_date": signal_date,
                "selected_return": selected_return,
                "industry_equal_return": equal_return,
                "market_return": market_return,
            }
        )
    events = pd.DataFrame(rows)
    if events.empty:
        raise ValueError("French 30 固定 20 日事件為空")
    difference = events["selected_return"] - events["industry_equal_return"]
    halves = {
        "first": events.loc[
            events["signal_date"] <= first_half_end,
            "selected_return",
        ].reset_index(drop=True)
        - events.loc[
            events["signal_date"] <= first_half_end,
            "industry_equal_return",
        ].reset_index(drop=True),
        "second": events.loc[
            events["signal_date"] >= second_half_start,
            "selected_return",
        ].reset_index(drop=True)
        - events.loc[
            events["signal_date"] >= second_half_start,
            "industry_equal_return",
        ].reset_index(drop=True),
    }
    nw = newey_west_mean_test(difference, max_lag=4, periods_per_year=52)
    bootstrap = _moving_block_bootstrap_mean(
        difference,
        samples=2_000,
        block_size=8,
        seed=20_260_803,
    )
    gates = {
        "mean_difference_positive": float(difference.mean()) > 0.0,
        "newey_west_t_at_least_1_96": nw["t_stat"] >= 1.96,
        "bootstrap_95pct_low_positive": bootstrap["low"] > 0.0,
        "both_fixed_halves_positive": all(float(value.mean()) > 0.0 for value in halves.values()),
        "paired_win_fraction_above_50pct": float((difference > 0.0).mean()) > 0.50,
    }
    return {
        "events": int(len(events)),
        "first_signal": events.iloc[0]["signal_date"].date().isoformat(),
        "last_signal": events.iloc[-1]["signal_date"].date().isoformat(),
        "selected_mean_return": float(events["selected_return"].mean()),
        "industry_equal_mean_return": float(events["industry_equal_return"].mean()),
        "market_mean_return": float(events["market_return"].mean()),
        "mean_difference_vs_industry_equal": float(difference.mean()),
        "median_difference_vs_industry_equal": float(difference.median()),
        "paired_win_fraction": float((difference > 0.0).mean()),
        "newey_west": nw,
        "moving_block_bootstrap": bootstrap,
        "fixed_halves": {
            key: {
                "events": int(len(value)),
                "mean_difference": float(value.mean()),
                "win_fraction": float((value > 0.0).mean()),
            }
            for key, value in halves.items()
        },
        "gates": gates,
        "passed_gate_count": int(sum(bool(value) for value in gates.values())),
        "required_gate_count": 5,
        "all_gates_pass": all(gates.values()),
    }


def _factor_regression(candidate: ReturnPath, factors: pd.DataFrame) -> dict[str, float]:
    aligned = pd.concat(
        [candidate.returns.rename("candidate"), factors],
        axis=1,
        join="inner",
    ).dropna()
    y = (aligned["candidate"] - aligned["RF"]).to_numpy(dtype=float)
    names = ["Mkt-RF", "SMB", "HML", "Mom"]
    x = np.column_stack([np.ones(len(aligned)), aligned[names].to_numpy(dtype=float)])
    coefficients, _, _, _ = np.linalg.lstsq(x, y, rcond=None)
    fitted = x @ coefficients
    residual = y - fitted
    total_sum = float(np.sum((y - y.mean()) ** 2))
    residual_sum = float(np.sum(residual**2))
    return {
        "annualized_alpha": float(coefficients[0] * 252.0),
        "market_beta": float(coefficients[1]),
        "smb_beta": float(coefficients[2]),
        "hml_beta": float(coefficients[3]),
        "mom_beta": float(coefficients[4]),
        "r_squared": float(1.0 - residual_sum / total_sum) if total_sum > 0.0 else 0.0,
        "excess_return_correlation_with_mom": float(
            np.corrcoef(y, aligned["Mom"].to_numpy(dtype=float))[0, 1]
        ),
    }


def _stress_summary(
    paths: dict[str, ReturnPath],
    periods: dict[str, tuple[str, str]],
) -> dict[str, Any]:
    output: dict[str, Any] = {}
    for label, (start, end) in periods.items():
        rows: dict[str, Any] = {}
        for name, path in paths.items():
            returns = path.returns.loc[start:end]
            if len(returns) < 2:
                continue
            wealth = (1.0 + returns).cumprod()
            anchor = pd.concat(
                [pd.Series([1.0], index=[returns.index[0] - pd.Timedelta(days=1)]), wealth]
            )
            rows[name] = {
                "return": float(wealth.iloc[-1] - 1.0),
                "max_drawdown": float((anchor / anchor.cummax() - 1.0).min()),
                "worst_day": float(returns.min()),
            }
        output[label] = rows
    return output


def _build_period(
    *,
    name: str,
    start: pd.Timestamp,
    end: pd.Timestamp,
    candidate_by_cost: dict[str, ReturnPath],
    market: ReturnPath,
    monthly_equal: ReturnPath,
    drift: ReturnPath,
    risk_free: pd.Series,
    event: dict[str, Any],
    split_ranges: list[tuple[str, pd.Timestamp, pd.Timestamp]],
    pbo: dict[str, Any],
) -> dict[str, Any]:
    candidate = _slice_path(candidate_by_cost["10"], start, end)
    candidate_50 = _slice_path(candidate_by_cost["50"], start, end)
    baselines = {
        "market": _slice_path(market, start, end),
        "industry_monthly_equal": _slice_path(monthly_equal, start, end),
        "industry_start_equal_then_drift": _slice_path(drift, start, end),
    }
    candidate_metrics = _metrics(candidate, risk_free)
    baseline_metrics = {key: _metrics(value, risk_free) for key, value in baselines.items()}
    candidate_50_metrics = _metrics(candidate_50, risk_free)
    comparisons = {key: _active_comparison(candidate, value) for key, value in baselines.items()}
    rolling_market = _rolling_comparison(candidate, baselines["market"])
    rolling_equal = _rolling_comparison(candidate, baselines["industry_monthly_equal"])
    split_results: dict[str, Any] = {}
    for label, split_start, split_end in split_ranges:
        split_candidate = _metrics(_slice_path(candidate, split_start, split_end), risk_free)
        split_market = _metrics(_slice_path(baselines["market"], split_start, split_end), risk_free)
        split_equal = _metrics(
            _slice_path(baselines["industry_monthly_equal"], split_start, split_end),
            risk_free,
        )
        split_results[label] = {
            "candidate_cagr": split_candidate["cagr"],
            "market_cagr": split_market["cagr"],
            "industry_monthly_equal_cagr": split_equal["cagr"],
            "edge_vs_market": split_candidate["cagr"] - split_market["cagr"],
            "edge_vs_industry_monthly_equal": (
                split_candidate["cagr"] - split_equal["cagr"]
            ),
        }

    baseline_values = list(baseline_metrics.values())
    gates = {
        "cagr_beats_all_three_baselines_by_2pp": all(
            candidate_metrics["cagr"] >= value["cagr"] + 0.02 for value in baseline_values
        ),
        "excess_sharpe_beats_all_three_baselines": all(
            candidate_metrics["excess_sharpe"] > value["excess_sharpe"]
            for value in baseline_values
        ),
        "max_drawdown_not_over_5pp_deeper_than_deepest_baseline": candidate_metrics[
            "max_drawdown"
        ]
        >= min(value["max_drawdown"] for value in baseline_values) - 0.05,
        "cost_50bps_cagr_beats_all_three_baselines_by_50bp": all(
            candidate_50_metrics["cagr"] >= value["cagr"] + 0.005
            for value in baseline_values
        ),
        "both_fixed_halves_beat_market_and_equal_by_50bp": all(
            value["edge_vs_market"] >= 0.005
            and value["edge_vs_industry_monthly_equal"] >= 0.005
            for value in split_results.values()
        ),
        "rolling_five_year_vs_market_60pct_and_positive_median": rolling_market[
            "cagr_win_fraction"
        ]
        >= 0.60
        and rolling_market["median_cagr_difference"] > 0.0,
        "rolling_five_year_vs_equal_60pct_and_positive_median": rolling_equal[
            "cagr_win_fraction"
        ]
        >= 0.60
        and rolling_equal["median_cagr_difference"] > 0.0,
        "active_newey_west_t_vs_market_at_least_1_96": comparisons["market"][
            "newey_west"
        ]["t_stat"]
        >= 1.96,
        "active_newey_west_t_vs_equal_at_least_1_96": comparisons[
            "industry_monthly_equal"
        ]["newey_west"]["t_stat"]
        >= 1.96,
        "active_psr_vs_market_and_equal_at_least_95pct": all(
            comparisons[key]["active_probabilistic_sharpe"]["probability"] >= 0.95
            for key in ("market", "industry_monthly_equal")
        ),
        "active_global_dsr_vs_market_and_equal_at_least_95pct": all(
            comparisons[key]["active_global_deflated_sharpe"]["probability"] >= 0.95
            for key in ("market", "industry_monthly_equal")
        ),
        "top_k_pbo_not_above_20pct": bool(np.isfinite(pbo["pbo"]) and pbo["pbo"] <= 0.20),
        "fixed_20_day_event_all_five_gates_pass": event["all_gates_pass"] is True,
    }
    return {
        "name": name,
        "start": candidate.returns.index[0].date().isoformat(),
        "end": candidate.returns.index[-1].date().isoformat(),
        "candidate_metrics": candidate_metrics,
        "candidate_50bps_metrics": candidate_50_metrics,
        "baseline_metrics": baseline_metrics,
        "comparisons": comparisons,
        "fixed_splits": split_results,
        "rolling_five_year_vs_market": rolling_market,
        "rolling_five_year_vs_industry_monthly_equal": rolling_equal,
        "fixed_20_day_event": event,
        "gates": gates,
        "passed_gate_count": int(sum(bool(value) for value in gates.values())),
        "required_gate_count": 13,
        "all_gates_pass": all(gates.values()),
    }


def build_french_30_industry_research(
    *,
    industry_path: str | Path,
    factors_path: str | Path,
    momentum_path: str | Path,
    data_receipt: dict[str, Any],
) -> dict[str, Any]:
    if data_receipt.get("status") != "french_30_industry_daily_first_download_contract_passed":
        raise ValueError("French 30 首次數據契約未通過")
    if data_receipt.get("calculation_started") is not False:
        raise ValueError("French 30 數據收據不是計算前狀態")
    if not all(data_receipt.get("checks", {}).values()):
        raise ValueError("French 30 數據檢查未全部通過")
    industry, factors = load_frozen_french_daily(industry_path, factors_path, momentum_path)
    market_returns = (factors["Mkt-RF"] + factors["RF"]).rename("market")

    targets_by_k: dict[int, pd.DataFrame] = {}
    selections_by_k: dict[int, dict[str, list[str]]] = {}
    paths_by_k: dict[int, ReturnPath] = {}
    for top_k in TOP_K_NEIGHBORS:
        targets, selections = industry_momentum_targets(industry, top_k=top_k)
        targets_by_k[top_k] = targets
        selections_by_k[top_k] = selections
        paths_by_k[top_k] = _simulate(industry, targets, cost_bps=PRIMARY_COST_BPS)
    candidate_by_cost = {
        str(int(cost)): _simulate(
            industry,
            targets_by_k[PRIMARY_TOP_K],
            cost_bps=cost,
        )
        for cost in (PRIMARY_COST_BPS, *STRESS_COST_BPS)
    }
    monthly_equal = _simulate(
        industry,
        equal_monthly_targets(industry),
        cost_bps=PRIMARY_COST_BPS,
    )
    market_frame = market_returns.to_frame()
    market_targets = pd.DataFrame(np.nan, index=industry.index, columns=["market"])
    first_candidate_signal = pd.Timestamp(next(iter(selections_by_k[PRIMARY_TOP_K])))
    market_targets.loc[first_candidate_signal, "market"] = 1.0
    market = _simulate(market_frame, market_targets, cost_bps=PRIMARY_COST_BPS)

    drift_targets_primary = pd.DataFrame(np.nan, index=industry.index, columns=industry.columns)
    drift_targets_primary.loc[first_candidate_signal] = 1.0 / industry.shape[1]
    drift_primary = _simulate(industry, drift_targets_primary, cost_bps=PRIMARY_COST_BPS)
    recent_pre_signal = industry.index[industry.index < RECENT_START][-1]
    drift_targets_recent = pd.DataFrame(np.nan, index=industry.index, columns=industry.columns)
    drift_targets_recent.loc[recent_pre_signal] = 1.0 / industry.shape[1]
    drift_recent = _simulate(industry, drift_targets_recent, cost_bps=PRIMARY_COST_BPS)

    evaluation_start = industry.index[industry.index.get_loc(first_candidate_signal) + 1]
    primary_end = industry.index[industry.index <= PRIMARY_END][-1]
    recent_start = industry.index[industry.index >= RECENT_START][0]
    primary_event = _period_event_diagnostic(
        industry,
        market_returns,
        start=FORMAL_START,
        end=primary_end,
        first_half_end=pd.Timestamp("1984-12-31"),
        second_half_start=pd.Timestamp("1985-01-01"),
    )
    recent_event = _period_event_diagnostic(
        industry,
        market_returns,
        start=recent_start,
        end=FORMAL_END,
        first_half_end=pd.Timestamp("2015-12-31"),
        second_half_start=pd.Timestamp("2016-01-01"),
    )

    pbo_primary = probability_of_backtest_overfitting(
        pd.concat(
            {
                f"top_{top_k}": _slice_path(path, evaluation_start, primary_end).returns
                for top_k, path in paths_by_k.items()
            },
            axis=1,
        ),
        slices=10,
    )
    pbo_recent = probability_of_backtest_overfitting(
        pd.concat(
            {
                f"top_{top_k}": _slice_path(path, recent_start, FORMAL_END).returns
                for top_k, path in paths_by_k.items()
            },
            axis=1,
        ),
        slices=10,
    )

    primary = _build_period(
        name="主要外部期",
        start=evaluation_start,
        end=primary_end,
        candidate_by_cost=candidate_by_cost,
        market=market,
        monthly_equal=monthly_equal,
        drift=drift_primary,
        risk_free=factors["RF"],
        event=primary_event,
        split_ranges=[
            ("start_to_1984", evaluation_start, pd.Timestamp("1984-12-31")),
            ("1985_to_2005", pd.Timestamp("1985-01-01"), primary_end),
        ],
        pbo=pbo_primary,
    )
    recent = _build_period(
        name="近期確認期",
        start=recent_start,
        end=FORMAL_END,
        candidate_by_cost=candidate_by_cost,
        market=market,
        monthly_equal=monthly_equal,
        drift=drift_recent,
        risk_free=factors["RF"],
        event=recent_event,
        split_ranges=[
            ("2006_to_2015", recent_start, pd.Timestamp("2015-12-31")),
            ("2016_to_end", pd.Timestamp("2016-01-01"), FORMAL_END),
        ],
        pbo=pbo_recent,
    )

    data_gates = {
        "protocol_and_mapping_frozen_before_download": data_receipt["protocol"]["sha256"]
        == PROTOCOL_SHA256
        and data_receipt["mapping"]["sha256"] == MAPPING_SHA256,
        "all_three_archive_hashes_match": data_receipt["archives"]["industry_30"]["sha256"]
        == INDUSTRY_SHA256
        and data_receipt["archives"]["ff_factors"]["sha256"] == FACTORS_SHA256
        and data_receipt["archives"]["momentum"]["sha256"] == MOMENTUM_SHA256,
        "raw_common_dates_pass": data_receipt["checks"][
            "raw_common_start_no_later_than_1927_01_31"
        ]
        and data_receipt["checks"]["raw_common_end_is_in_2026_05_release"],
        "industry_columns_exactly_30": industry.shape[1] == 30,
        "formal_start_and_complete_period_pass": data_receipt["common_period"]["formal_start"]
        == FORMAL_START.date().isoformat()
        and data_receipt["checks"]["formal_period_all_three_files_complete"],
        "missing_codes_audited_without_imputation": data_receipt["checks"][
            "missing_codes_audited_without_imputation"
        ],
        "signal_t_applied_to_return_t_plus_1": data_receipt["checks"][
            "signal_t_return_t_plus_1_rule_frozen"
        ],
    }
    all_gate_pass = (
        all(data_gates.values())
        and primary["all_gates_pass"] is True
        and recent["all_gates_pass"] is True
    )
    passed_gate_count = (
        int(sum(bool(value) for value in data_gates.values()))
        + int(primary["passed_gate_count"])
        + int(recent["passed_gate_count"])
    )
    candidate_full = _slice_path(candidate_by_cost["10"], evaluation_start, FORMAL_END)
    full_metrics = _metrics(candidate_full, factors["RF"])
    top_k_metrics = {
        str(top_k): _metrics(
            _slice_path(path, evaluation_start, FORMAL_END),
            factors["RF"],
        )
        for top_k, path in paths_by_k.items()
    }
    latest_signal = max(selections_by_k[PRIMARY_TOP_K])

    return {
        "schema_version": SCHEMA_VERSION,
        "status": (
            "academic_industry_mechanism_passed_but_not_tradeable"
            if all_gate_pass
            else "academic_industry_mechanism_failed"
        ),
        "academic_mechanism_passed": all_gate_pass,
        "paper_eligible": False,
        "paper_state_created": False,
        "trade_ready": False,
        "real_money_action_usd": 0,
        "research_role": "first_seen_french_30_industry_daily_external_validation",
        "protocol": {
            "sha256": PROTOCOL_SHA256,
            "mapping_sha256": MAPPING_SHA256,
            "protocol_commit": PROTOCOL_COMMIT,
            "snapshot_commit": SNAPSHOT_COMMIT,
            "global_search_trials": GLOBAL_SEARCH_TRIALS,
        },
        "snapshot": {
            "industry_sha256": INDUSTRY_SHA256,
            "factors_sha256": FACTORS_SHA256,
            "momentum_sha256": MOMENTUM_SHA256,
            "formal_start": FORMAL_START.date().isoformat(),
            "formal_end": FORMAL_END.date().isoformat(),
            "formal_sessions": int(len(industry.loc[FORMAL_START:FORMAL_END])),
            "industry_columns": list(industry.columns),
            "survivorship_reduced_not_raw_point_in_time_stock_ledger": True,
        },
        "frozen_candidate": {
            "label": "French 30 行業 6–1 動量月度 Top-3",
            "signal": "t-126 至 t-21 複利；跳過最近 20 日",
            "cost_sensitivity_full_history": {
                f"{cost}_bps": _metrics(
                    _slice_path(path, evaluation_start, FORMAL_END),
                    factors["RF"],
                )
                for cost, path in candidate_by_cost.items()
            },
            "full_history_metrics": full_metrics,
            "latest_academic_signal_date": latest_signal,
            "latest_selected_industries_not_trade_instruction": selections_by_k[PRIMARY_TOP_K][
                latest_signal
            ],
        },
        "primary_external_period": primary,
        "recent_confirmation_period": recent,
        "top_k_sensitivity_full_history": top_k_metrics,
        "pbo": {"primary": pbo_primary, "recent": pbo_recent},
        "factor_regression_full_history": _factor_regression(candidate_full, factors),
        "stress_periods": _stress_summary(
            {
                "candidate": candidate_full,
                "market": _slice_path(market, evaluation_start, FORMAL_END),
                "industry_monthly_equal": _slice_path(
                    monthly_equal,
                    evaluation_start,
                    FORMAL_END,
                ),
            },
            {
                "1973_1974": ("1973-01-01", "1974-12-31"),
                "1987_crash": ("1987-01-01", "1987-12-31"),
                "dotcom": ("2000-01-01", "2002-12-31"),
                "gfc": ("2008-01-01", "2009-12-31"),
                "covid_2020": ("2020-01-01", "2020-12-31"),
                "rate_shock_2022": ("2022-01-01", "2022-12-31"),
            },
        ),
        "data_gates": data_gates,
        "passed_gate_count": passed_gate_count,
        "required_gate_count": 33,
        "gate_breakdown": {
            "data": f"{sum(data_gates.values())}/7",
            "primary": f"{primary['passed_gate_count']}/13",
            "recent": f"{recent['passed_gate_count']}/13",
        },
        "decision": (
            "完整保留正負結果；French 行業組合不可直接交易。即使 33/33，仍須等待合格"
            "逐股 point-in-time 成分及退市資料另行通過，才可由全現金建立前瞻 Paper。"
        ),
    }
