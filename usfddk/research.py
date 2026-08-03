from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from usfddk.data import panel_fingerprint
from usfddk.engine import run_backtest
from usfddk.metrics import compute_metrics, newey_west_mean_test
from usfddk.models import BacktestResult, MarketPanel
from usfddk.strategies import (
    balanced_trend_satellite_targets,
    buy_and_hold_targets,
    fixed_weight_targets,
    growth_guard_targets,
    style_rotation_targets,
    three_clock_ensemble_targets,
    trend_confirmed_volatility_guard_targets,
    volatility_guard_targets,
)
from usfddk.validation import (
    deflated_sharpe_ratio,
    probabilistic_sharpe_ratio,
    probability_of_backtest_overfitting,
)

CANDIDATE_NAME = "平衡趨勢衛星（研究候選）"
CANDIDATE_CORE_SHARE = 0.75
CANDIDATE_FAMILY = (0.60, 0.65, 0.70, 0.75, 0.80, 0.85, 0.90)
CONSERVATIVE_SEARCH_TRIALS = 6_000
GROWTH_GUARD_NAME = "成長守門員（上線研究候選）"
GROWTH_GUARD_CORE_SHARE = 0.20
GROWTH_GUARD_FAMILY = (0.10, 0.15, 0.20, 0.25, 0.30)
VOLATILITY_GUARD_NAME = "成長守門員 v2（波動管理）"
VOLATILITY_GUARD_TARGET = 0.18
VOLATILITY_GUARD_WINDOW = 21
VOLATILITY_GUARD_TARGETS = (0.14, 0.18, 0.22)
VOLATILITY_GUARD_WINDOWS = (21, 63, 126)
PASSIVE_90_10_NAME = "被動 90% QQQ／10% SHY（月末再平衡）"
PASSIVE_90_10_WEIGHTS = {"QQQ": 0.90, "SHY": 0.10}
TREND_CONFIRMED_GUARD_NAME = "成長守門員 v3（趨勢確認波動防守）"
TREND_CONFIRMED_TARGET = 0.18
TREND_CONFIRMED_VOL_WINDOW = 21
TREND_CONFIRMED_MOMENTUM_WINDOW = 252
TREND_CONFIRMED_MONTHS = 2
TREND_CONFIRMED_FAMILY = (1, 2, 3)
MATCHED_96_4_NAME = "被動 96% QQQ／4% SHY（月末再平衡）"
MATCHED_96_4_WEIGHTS = {"QQQ": 0.96, "SHY": 0.04}
V3_GLOBAL_SEARCH_TRIALS = 6_100
V3_CROSS_MARKET_PROTOCOL_SHA256 = (
    "8de1eafd2e8cbf28ee68dfc7322187d9b6c06e3b8aefc32d76d516046ec88117"
)
V3_CROSS_MARKET_START = "1989-01-03"
V3_CROSS_MARKET_END = "2006-07-28"
V3_CROSS_MARKETS = {
    "^GSPC": {"market": "美國", "index": "S&P 500"},
    "^FTSE": {"market": "英國", "index": "FTSE 100"},
    "^GDAXI": {"market": "德國", "index": "DAX"},
    "^N225": {"market": "日本", "index": "Nikkei 225"},
    "^HSI": {"market": "香港", "index": "Hang Seng"},
}
V4_STYLE_PROTOCOL_SHA256 = (
    "9be20a10a0d27809d9e420e6bf41cc6ce04c4d46a51c5b4651c54a4b28efae48"
)
V4_GLOBAL_SEARCH_TRIALS = 6_101
V4_TRADE_START = "2006-07-31"
V4_TRADE_END = "2026-07-31"
V4_TRADE_ASSETS = ("IWF", "IWD", "IJR")
V4_TRADE_TICKERS = (*V4_TRADE_ASSETS, "SHY", "SPY", "QQQ")
V4_PROXY_START = "1996-07-31"
V4_PROXY_END = "2006-07-28"
V4_PROXY_ASSETS = ("^RLG", "^RLV", "^SP600")
V4_PROXY_TICKERS = (*V4_PROXY_ASSETS, "^GSPC")
V5_THREE_CLOCK_PROTOCOL_SHA256 = (
    "67cfc566116497d2d32df904c91ff90f554380cfcdd3e47b41a41eaab1fac90f"
)
V5_GLOBAL_SEARCH_TRIALS = 6_102
V5_MAIN_PANEL_SHA256 = (
    "6a7ca6b83b1570007424daa46b0ff4e8fb4a655d39298a0f4f6d74c3b7ea3a66"
)
V5_MAIN_ARCHIVE_SHA256 = (
    "d480fb82e712f06aabe0a98461e222344656b87022b8bda2cd7ccaa4c29ae88b"
)
V5_PROXY_PANEL_SHA256 = (
    "4814654a4abb4ea5ef0eb52763e233e13bc7088d51ca506eb94c7e335f5f4faa"
)
V5_PROXY_ARCHIVE_SHA256 = (
    "ede88d5906411182e454d2e43442e7b5af61c392eab75e4235d5f22d3112f78d"
)
V5_CROSS_HASHES = {
    "^GSPC": {
        "panel_sha256": "fbe6b7403574d3296f371ed77c9831cca605b45a5dc5d2a0becfc02ec22f9e2f",
        "archive_sha256": "2406c622d7b4c85666512ef84b3853b8729c5fe6b4e50256270f60a6273ecacd",
    },
    "^FTSE": {
        "panel_sha256": "e0e17b65bb7f80dd024752505f0a48c6cffbb0ebe6a123234e46c865ef9d56cb",
        "archive_sha256": "f206abc6b29f0c82d71e96a9b544f1b8cd60b619164906191f95afe94b0289b3",
    },
    "^GDAXI": {
        "panel_sha256": "ecf4465baa6f38d61af7579e1e59acbbda5ddaafc72a18ebe78bc7286765ad58",
        "archive_sha256": "bd0b143958a9b2db88961f90dbd09a4faff2c2a48792425329a961cc76ccd397",
    },
    "^N225": {
        "panel_sha256": "df89bb42a2f4896a03636a64a2b339fcf3e7eefd753675e4d71a7e62df652bed",
        "archive_sha256": "ef8b06b0c9b44c9503105e7c5a65d1a7669075c633d2a5bfd5029607d5aa98f0",
    },
    "^HSI": {
        "panel_sha256": "e05499d694e77223bdddf97b1d182a64de30ccf0a58e3dfa5481cc15df2b7266",
        "archive_sha256": "e994ee0c10bbf555ea6a32646c0b785fbeeedabfacfe6b9274e38e47b8236866",
    },
}


def _excess_sharpe(returns: pd.Series, risk_free_returns: pd.Series) -> float:
    excess = returns.sub(risk_free_returns, fill_value=0.0).dropna()
    std = float(excess.std(ddof=1))
    return float(excess.mean() / std * np.sqrt(252.0)) if std > 0 else 0.0


def _metrics_for_slice(result: BacktestResult, start: str, end: str) -> dict[str, float]:
    equity = result.equity.loc[start:end]
    returns = result.returns.loc[start:end]
    turnover = result.turnover.loc[start:end]
    return compute_metrics(equity, returns, turnover)


def _walk_forward(
    panel: MarketPanel,
    *,
    start: str,
    cost_bps: float,
    family_targets: dict[float, pd.DataFrame],
    family_results: dict[float, BacktestResult],
    risk_free_returns: pd.Series,
) -> tuple[BacktestResult | None, dict[str, Any]]:
    """Select a core share on expanding history, then trade the next two years."""
    start_stamp = pd.Timestamp(start)
    first_test_year = start_stamp.year + 6
    final_year = panel.end.year
    dynamic = pd.DataFrame(
        np.nan,
        index=panel.close.index,
        columns=next(iter(family_targets.values())).columns,
    )
    folds: list[dict[str, Any]] = []
    for test_year in range(first_test_year, final_year + 1, 2):
        train_end = pd.Timestamp(f"{test_year - 1}-12-31")
        test_start = pd.Timestamp(f"{test_year}-01-01")
        test_end = min(pd.Timestamp(f"{test_year + 1}-12-31"), panel.end)
        if test_start > panel.end:
            break
        ranked: list[tuple[float, dict[str, float]]] = []
        for share, result in family_results.items():
            metrics = _metrics_for_slice(
                result,
                start_stamp.strftime("%Y-%m-%d"),
                train_end.strftime("%Y-%m-%d"),
            )
            ranked.append((share, metrics))
        practical = [
            item
            for item in ranked
            if item[1]["cagr"] >= 0.08 and item[1]["max_drawdown"] >= -0.25
        ]
        pool = practical or [item for item in ranked if item[1]["max_drawdown"] >= -0.25]
        pool = pool or ranked
        selected_share, train_metrics = max(pool, key=lambda item: item[1]["sharpe"])
        source = family_targets[selected_share].dropna(how="all")
        prior = source.index[source.index < test_start]
        if len(prior):
            dynamic.loc[prior[-1]] = source.loc[prior[-1]]
        in_test = source.index[(source.index >= test_start) & (source.index <= test_end)]
        dynamic.loc[in_test] = source.loc[in_test]
        folds.append(
            {
                "train_start": start_stamp.strftime("%Y-%m-%d"),
                "train_end": train_end.strftime("%Y-%m-%d"),
                "test_start": test_start.strftime("%Y-%m-%d"),
                "test_end": test_end.strftime("%Y-%m-%d"),
                "selected_core_share": selected_share,
                "selection_rule": "max train Sharpe subject to CAGR >= 8% and MDD >= -25%; fallback MDD gate",
                "train_metrics": train_metrics,
            }
        )
    if not folds:
        return None, {"status": "insufficient_history", "folds": []}
    result = run_backtest(
        panel,
        dynamic,
        name="展開式兩年走勢外組合",
        cost_bps=cost_bps,
        start=folds[0]["test_start"],
    )
    for fold in folds:
        test_metrics = _metrics_for_slice(result, fold["test_start"], fold["test_end"])
        test_metrics["excess_sharpe_vs_shy"] = _excess_sharpe(
            result.returns.loc[fold["test_start"] : fold["test_end"]],
            risk_free_returns.loc[fold["test_start"] : fold["test_end"]],
        )
        fold["test_metrics"] = test_metrics
    overall_metrics = dict(result.metrics)
    overall_metrics["excess_sharpe_vs_shy"] = _excess_sharpe(
        result.returns, risk_free_returns.reindex(result.returns.index).fillna(0.0)
    )
    return result, {
        "status": "completed",
        "initial_train_years": 6,
        "test_years_per_fold": 2,
        "selection_family": list(CANDIDATE_FAMILY),
        "overall_metrics": overall_metrics,
        "folds": folds,
        "caveat": "Walk-forward selection is historical simulation, not live evidence.",
    }


def evaluate_candidate_research(
    panel: MarketPanel,
    *,
    start: str,
    cost_bps: float = 10.0,
) -> tuple[BacktestResult, pd.DataFrame, dict[str, Any]]:
    """Run the frozen candidate, its local family, and selection-aware diagnostics."""
    family_targets: dict[float, pd.DataFrame] = {}
    family_results: dict[float, BacktestResult] = {}
    neighborhood: list[dict[str, float]] = []
    for share in CANDIDATE_FAMILY:
        target = balanced_trend_satellite_targets(panel.close, core_share=share)
        result = run_backtest(
            panel,
            target,
            name=f"candidate-core-{share:.2f}",
            cost_bps=cost_bps,
            start=start,
        )
        family_targets[share] = target
        family_results[share] = result
        neighborhood.append({"core_share": share, **result.metrics})

    candidate_target = family_targets[CANDIDATE_CORE_SHARE]
    raw_candidate = family_results[CANDIDATE_CORE_SHARE]
    candidate = BacktestResult(
        name=CANDIDATE_NAME,
        equity=raw_candidate.equity.rename(CANDIDATE_NAME),
        returns=raw_candidate.returns.rename(CANDIDATE_NAME),
        weights=raw_candidate.weights,
        turnover=raw_candidate.turnover,
        costs=raw_candidate.costs,
        metrics=raw_candidate.metrics,
        current_target=raw_candidate.current_target,
        diagnostics=raw_candidate.diagnostics,
    )
    risk_free_returns = panel.close["SHY"].pct_change(fill_method=None).reindex(
        candidate.returns.index
    ).fillna(0.0)
    if len(risk_free_returns):
        risk_free_returns.iloc[0] = 0.0
    candidate_excess = candidate.returns - risk_free_returns
    excess_sharpe = _excess_sharpe(candidate.returns, risk_free_returns)

    cost_sensitivity: list[dict[str, float]] = []
    for cost in (5.0, 10.0, 25.0, 50.0):
        result = candidate if cost == cost_bps else run_backtest(
            panel,
            candidate_target,
            name=f"candidate-cost-{cost:g}",
            cost_bps=cost,
            start=start,
        )
        cost_sensitivity.append(
            {
                "cost_bps": cost,
                **result.metrics,
                "excess_sharpe_vs_shy": _excess_sharpe(result.returns, risk_free_returns),
            }
        )

    family_returns = pd.DataFrame(
        {f"core_{share:.2f}": result.returns for share, result in family_results.items()}
    )
    for item in neighborhood:
        share = float(item["core_share"])
        item["excess_sharpe_vs_shy"] = _excess_sharpe(
            family_results[share].returns, risk_free_returns
        )
    zero_rate_psr_one = probabilistic_sharpe_ratio(candidate.returns, benchmark_sharpe=1.0)
    zero_rate_dsr = deflated_sharpe_ratio(
        candidate.returns, trials=CONSERVATIVE_SEARCH_TRIALS
    )
    psr_one = probabilistic_sharpe_ratio(candidate_excess, benchmark_sharpe=1.0)
    dsr = deflated_sharpe_ratio(candidate_excess, trials=CONSERVATIVE_SEARCH_TRIALS)
    pbo = probability_of_backtest_overfitting(
        family_returns.sub(risk_free_returns, axis=0), slices=10
    )
    walk_result, walk_forward = _walk_forward(
        panel,
        start=start,
        cost_bps=cost_bps,
        family_targets=family_targets,
        family_results=family_results,
        risk_free_returns=risk_free_returns,
    )

    midpoint = pd.Timestamp(start) + pd.DateOffset(years=10)
    first_half = _metrics_for_slice(
        candidate,
        start,
        (midpoint - pd.Timedelta(days=1)).strftime("%Y-%m-%d"),
    )
    second_half = _metrics_for_slice(candidate, midpoint.strftime("%Y-%m-%d"), "2099-12-31")
    central = [row for row in neighborhood if 0.65 <= row["core_share"] <= 0.80]
    gates = {
        "zero_rate_sharpe_above_1": bool(candidate.metrics["sharpe"] > 1.0),
        "excess_sharpe_vs_shy_above_1": bool(excess_sharpe > 1.0),
        "cagr_at_least_8pct": bool(candidate.metrics["cagr"] >= 0.08),
        "max_drawdown_no_worse_than_25pct": bool(candidate.metrics["max_drawdown"] >= -0.25),
        "both_ten_year_sharpes_above_1": bool(
            first_half["sharpe"] > 1.0 and second_half["sharpe"] > 1.0
        ),
        "central_neighborhood_sharpes_above_1": bool(
            central and all(row["sharpe"] > 1.0 for row in central)
        ),
        "psr_population_sharpe_above_1_at_95pct": bool(psr_one["probability"] >= 0.95),
        "dsr_after_6000_trials_at_95pct": bool(dsr["probability"] >= 0.95),
        "walk_forward_excess_sharpe_above_1": bool(
            walk_result is not None
            and walk_forward["overall_metrics"]["excess_sharpe_vs_shy"] > 1.0
        ),
    }
    zero_rate_point_gate = all(
        gates[key]
        for key in (
            "zero_rate_sharpe_above_1",
            "cagr_at_least_8pct",
            "max_drawdown_no_worse_than_25pct",
            "both_ten_year_sharpes_above_1",
            "central_neighborhood_sharpes_above_1",
        )
    )
    conventional_point_gate = bool(
        zero_rate_point_gate and gates["excess_sharpe_vs_shy_above_1"]
    )
    statistically_confirmed = bool(
        conventional_point_gate
        and gates["psr_population_sharpe_above_1_at_95pct"]
        and gates["dsr_after_6000_trials_at_95pct"]
        and gates["walk_forward_excess_sharpe_above_1"]
    )
    status = (
        "statistically_confirmed"
        if statistically_confirmed
        else "zero_rate_sharpe_candidate_excess_sharpe_failed"
        if zero_rate_point_gate and not conventional_point_gate
        else "conventional_point_estimate_not_statistically_confirmed"
        if conventional_point_gate
        else "research_gate_failed"
    )
    audit: dict[str, Any] = {
        "candidate_name": CANDIDATE_NAME,
        "status": status,
        "zero_rate_point_estimate_gate_passed": zero_rate_point_gate,
        "conventional_point_estimate_gate_passed": conventional_point_gate,
        "statistically_confirmed": statistically_confirmed,
        "frozen_parameters": {
            "core_share": CANDIDATE_CORE_SHARE,
            "satellite": "QQQ",
            "satellite_share": 1.0 - CANDIDATE_CORE_SHARE,
            "momentum_windows_sessions": [63, 126, 252],
            "trend_window_sessions": 200,
            "inverse_vol_window_sessions": 63,
            "top_k": 10,
            "max_active_asset_weight": 0.35,
            "core_risk_budget": 0.50,
            "breadth_tiers": {"60pct": 1.0, "40pct": 0.70, "20pct": 0.30, "below_20pct": 0.0},
            "rebalance": "monthly close signal, next-session open execution",
        },
        "gates": gates,
        "candidate_metrics": candidate.metrics,
        "excess_return_metrics": {
            "risk_free_proxy": "SHY adjusted total return",
            "annualized_excess_mean": float(candidate_excess.mean() * 252.0),
            "excess_sharpe_vs_shy": excess_sharpe,
            "risk_free_proxy_cagr_approx": float((1.0 + risk_free_returns).prod() ** (252.0 / len(risk_free_returns)) - 1.0),
        },
        "ten_year_halves": {"first": first_half, "second": second_half},
        "zero_rate_probabilistic_sharpe_above_1": zero_rate_psr_one,
        "zero_rate_deflated_sharpe": zero_rate_dsr,
        "probabilistic_sharpe_above_1": psr_one,
        "deflated_sharpe": dsr,
        "local_family_pbo": pbo,
        "neighborhood": neighborhood,
        "cost_sensitivity": cost_sensitivity,
        "walk_forward": walk_forward,
        "search_audit": {
            "conservative_trials_used_for_dsr": CONSERVATIVE_SEARCH_TRIALS,
            "reason": "Includes completed grids and aborted/planned configurations, not only the reported winner.",
            "exploratory_family_summaries": [
                {
                    "family": "multi-horizon trend and breadth",
                    "evaluated": 144,
                    "best_sharpe": 0.9367,
                    "note": "Sharpe 未跨過 1",
                },
                {
                    "family": "volatility managed",
                    "evaluated": 80,
                    "best_sharpe": 0.9221,
                    "note": "Sharpe 未跨過 1",
                },
                {
                    "family": "shrinkage covariance",
                    "evaluated": 48,
                    "best_sharpe": 0.9887,
                    "note": "接近但未跨過 1",
                },
                {
                    "family": "RSI2 trend dip",
                    "evaluated": 18,
                    "best_sharpe": 0.7080,
                    "note": "高換手且失敗",
                },
                {
                    "family": "fixed risk budget",
                    "evaluated": 11,
                    "best_sharpe": 1.1120,
                    "note": "Sharpe 通過但 CAGR 僅 5.02%",
                },
                {
                    "family": "trend core plus trend satellite",
                    "evaluated": 9,
                    "best_sharpe": 1.0178,
                    "note": "Sharpe 通過但 CAGR 僅 7.54%",
                },
                {
                    "family": "trend core plus permanent QQQ",
                    "evaluated": 8,
                    "best_sharpe": 1.1564,
                    "note": "75% 核心零利率 Sharpe 1.071；SHY 超額 Sharpe 僅 0.799",
                    "selected_core_share": 0.75,
                },
                {
                    "family": "expanded sector/country/asset ETF trend",
                    "evaluated": 128,
                    "best_sharpe": 0.7590,
                    "note": "此欄為 SHY 超額 Sharpe；擴充至 33 檔仍失敗",
                },
                {
                    "family": "turn-of-month pilot",
                    "evaluated": 30,
                    "best_sharpe": -0.1594,
                    "note": "排程重複稽核後作廢；只計搜尋次數，不作策略證據",
                },
            ],
            "negative_results_retained": True,
            "expanded_snapshot": {
                "path": "artifacts/snapshot_research_expanded_20260731_0b89bdb2.zip",
                "panel_sha256": "0b89bdb2c2c727a5665b4c306b95330a5636827d8f7bf4afc4aa4a7d87e8ed1d",
                "archive_sha256": "16a114b9c81ed5ab2c0f9601b570d106fad41be1be011533e127211c8ad12841",
                "tickers": 33,
            },
        },
        "interpretation": (
            "The zero-hurdle backtest Sharpe exceeds one, but the conventional excess-return "
            "Sharpe uses SHY as a tradable risk-free proxy and determines goal completion."
        ),
    }
    return candidate, candidate_target, audit


def _rolling_outperformance(
    strategy: BacktestResult,
    benchmark: BacktestResult,
    *,
    window: int = 1_260,
    minimum_cagr_edge: float = 0.001,
) -> dict[str, Any]:
    equity = strategy.equity.dropna()
    periods = pd.Series(equity.index.to_period("M"), index=equity.index)
    endpoints = equity.index[periods.ne(periods.shift(-1)).to_numpy()]
    rows: list[dict[str, float | str]] = []
    for end in endpoints:
        position = equity.index.get_loc(end)
        if not isinstance(position, int) or position < window:
            continue
        dates = equity.index[position - window : position + 1]
        strategy_metrics = compute_metrics(
            strategy.equity.loc[dates],
            strategy.returns.loc[dates],
            strategy.turnover.loc[dates],
        )
        benchmark_metrics = compute_metrics(
            benchmark.equity.loc[dates],
            benchmark.returns.loc[dates],
            benchmark.turnover.loc[dates],
        )
        rows.append(
            {
                "end": pd.Timestamp(end).strftime("%Y-%m-%d"),
                "strategy_cagr": strategy_metrics["cagr"],
                "benchmark_cagr": benchmark_metrics["cagr"],
                "cagr_difference": strategy_metrics["cagr"] - benchmark_metrics["cagr"],
                "strategy_max_drawdown": strategy_metrics["max_drawdown"],
                "benchmark_max_drawdown": benchmark_metrics["max_drawdown"],
            }
        )
    if not rows:
        return {"window_sessions": window, "series": [], "summary": {}}
    frame = pd.DataFrame(rows)
    summary = {
        "windows": len(rows),
        # A positive floating-point crumb is not an economically meaningful win.  Ten
        # basis points of annualized return is the frozen minimum edge for each window.
        "minimum_cagr_edge": float(minimum_cagr_edge),
        "cagr_win_fraction": float(
            (frame["cagr_difference"] > minimum_cagr_edge).mean()
        ),
        "cagr_noninferior_fraction": float(
            (frame["cagr_difference"] >= -minimum_cagr_edge).mean()
        ),
        "median_cagr_difference": float(frame["cagr_difference"].median()),
        "worst_cagr_difference": float(frame["cagr_difference"].min()),
        "latest_cagr_difference": float(frame.iloc[-1]["cagr_difference"]),
        "shallower_drawdown_fraction": float(
            (frame["strategy_max_drawdown"] > frame["benchmark_max_drawdown"]).mean()
        ),
    }
    return {"window_sessions": window, "series": rows, "summary": summary}


def _growth_walk_forward(
    panel: MarketPanel,
    *,
    start: str,
    cost_bps: float,
    family_targets: dict[float, pd.DataFrame],
    family_results: dict[float, BacktestResult],
    benchmark: BacktestResult,
) -> dict[str, Any]:
    start_stamp = pd.Timestamp(start)
    first_test_year = start_stamp.year + 6
    dynamic = pd.DataFrame(
        np.nan,
        index=panel.close.index,
        columns=next(iter(family_targets.values())).columns,
    )
    folds: list[dict[str, Any]] = []
    for test_year in range(first_test_year, panel.end.year + 1, 2):
        train_end = pd.Timestamp(f"{test_year - 1}-12-31")
        test_start = pd.Timestamp(f"{test_year}-01-01")
        test_end = min(pd.Timestamp(f"{test_year + 1}-12-31"), panel.end)
        if test_start > panel.end:
            break
        benchmark_train = _metrics_for_slice(benchmark, start, train_end.strftime("%Y-%m-%d"))
        share = GROWTH_GUARD_CORE_SHARE
        train_metrics = _metrics_for_slice(
            family_results[share], start, train_end.strftime("%Y-%m-%d")
        )
        cagr_difference = train_metrics["cagr"] - benchmark_train["cagr"]
        drawdown_improvement = (
            train_metrics["max_drawdown"] - benchmark_train["max_drawdown"]
        )
        source = family_targets[share].dropna(how="all")
        prior = source.index[source.index < test_start]
        if len(prior):
            dynamic.loc[prior[-1]] = source.loc[prior[-1]]
        in_test = source.index[(source.index >= test_start) & (source.index <= test_end)]
        dynamic.loc[in_test] = source.loc[in_test]
        folds.append(
            {
                "train_start": start_stamp.strftime("%Y-%m-%d"),
                "train_end": train_end.strftime("%Y-%m-%d"),
                "test_start": test_start.strftime("%Y-%m-%d"),
                "test_end": test_end.strftime("%Y-%m-%d"),
                "selected_core_share": share,
                "fallback_used": False,
                "train_metrics": train_metrics,
                "train_cagr_difference_vs_spy": cagr_difference,
                "train_drawdown_improvement_vs_spy": drawdown_improvement,
            }
        )
    if not folds:
        return {"status": "insufficient_history", "folds": []}
    result = run_backtest(
        panel,
        dynamic,
        name="成長守門員展開式走勢外",
        cost_bps=cost_bps,
        start=folds[0]["test_start"],
    )
    benchmark_oos = run_backtest(
        panel,
        buy_and_hold_targets(panel.close, "SPY", signal_on=folds[0]["test_start"]),
        name="SPY 走勢外基準",
        cost_bps=cost_bps,
        start=folds[0]["test_start"],
    )
    for fold in folds:
        strategy_metrics = _metrics_for_slice(result, fold["test_start"], fold["test_end"])
        benchmark_metrics = _metrics_for_slice(
            benchmark_oos, fold["test_start"], fold["test_end"]
        )
        fold["test_metrics"] = strategy_metrics
        fold["test_spy_metrics"] = benchmark_metrics
        fold["test_cagr_difference_vs_spy"] = (
            strategy_metrics["cagr"] - benchmark_metrics["cagr"]
        )
    comparison = newey_west_mean_test(result.returns - benchmark_oos.returns)
    return {
        "status": "completed",
        "initial_train_years": 6,
        "test_years_per_fold": 2,
        "selection_rule": (
            "Keep the policy fixed at 80% QQQ growth satellite and 20% diversified trend core; "
            "do not re-optimize between folds."
        ),
        "selection_family": list(GROWTH_GUARD_FAMILY),
        "strategy_metrics": result.metrics,
        "spy_metrics": benchmark_oos.metrics,
        "cagr_difference_vs_spy": result.metrics["cagr"] - benchmark_oos.metrics["cagr"],
        "active_return_newey_west": comparison,
        "folds": folds,
        "caveat": (
            "Fixed-policy forward-period simulation beginning in 2012. The 80/20 policy was "
            "chosen after broader exploration, so this is not a pristine independent holdout."
        ),
    }


def evaluate_growth_guard_research(
    panel: MarketPanel,
    *,
    start: str,
    cost_bps: float = 10.0,
) -> tuple[BacktestResult, pd.DataFrame, dict[str, Any]]:
    """Evaluate a growth-led family against SPY without claiming live superiority."""
    spy = run_backtest(
        panel,
        buy_and_hold_targets(panel.close, "SPY", signal_on=start),
        name="SPY 買進持有",
        cost_bps=cost_bps,
        start=start,
    )
    qqq = run_backtest(
        panel,
        buy_and_hold_targets(panel.close, "QQQ", signal_on=start),
        name="QQQ 買進持有",
        cost_bps=cost_bps,
        start=start,
    )
    family_targets: dict[float, pd.DataFrame] = {}
    family_results: dict[float, BacktestResult] = {}
    family_rows: list[dict[str, float]] = []
    for share in GROWTH_GUARD_FAMILY:
        target = growth_guard_targets(panel.close, core_share=share)
        result = run_backtest(
            panel,
            target,
            name=f"growth-guard-{share:.2f}",
            cost_bps=cost_bps,
            start=start,
        )
        family_targets[share] = target
        family_results[share] = result
        family_rows.append(
            {
                "core_share": share,
                "qqq_satellite_share": 1.0 - share,
                **result.metrics,
                "cagr_difference_vs_spy": result.metrics["cagr"] - spy.metrics["cagr"],
                "drawdown_improvement_vs_spy": (
                    result.metrics["max_drawdown"] - spy.metrics["max_drawdown"]
                ),
            }
        )
    target = family_targets[GROWTH_GUARD_CORE_SHARE]
    raw = family_results[GROWTH_GUARD_CORE_SHARE]
    strategy = BacktestResult(
        name=GROWTH_GUARD_NAME,
        equity=raw.equity.rename(GROWTH_GUARD_NAME),
        returns=raw.returns.rename(GROWTH_GUARD_NAME),
        weights=raw.weights,
        turnover=raw.turnover,
        costs=raw.costs,
        metrics=raw.metrics,
        current_target=raw.current_target,
        diagnostics=raw.diagnostics,
    )
    midpoint = pd.Timestamp(start) + pd.DateOffset(years=10)
    halves: dict[str, Any] = {}
    for label, period_start, period_end in (
        ("first", start, (midpoint - pd.Timedelta(days=1)).strftime("%Y-%m-%d")),
        ("second", midpoint.strftime("%Y-%m-%d"), "2099-12-31"),
    ):
        strategy_metrics = _metrics_for_slice(strategy, period_start, period_end)
        spy_metrics = _metrics_for_slice(spy, period_start, period_end)
        halves[label] = {
            "strategy": strategy_metrics,
            "spy": spy_metrics,
            "cagr_difference_vs_spy": strategy_metrics["cagr"] - spy_metrics["cagr"],
        }
    costs: list[dict[str, float]] = []
    for cost in (5.0, 10.0, 25.0, 50.0):
        result = strategy if cost == cost_bps else run_backtest(
            panel,
            target,
            name=f"growth-guard-cost-{cost:g}",
            cost_bps=cost,
            start=start,
        )
        spy_cost = spy if cost == cost_bps else run_backtest(
            panel,
            buy_and_hold_targets(panel.close, "SPY", signal_on=start),
            name=f"spy-cost-{cost:g}",
            cost_bps=cost,
            start=start,
        )
        costs.append(
            {
                "cost_bps": cost,
                **result.metrics,
                "spy_cagr": spy_cost.metrics["cagr"],
                "cagr_difference_vs_spy": result.metrics["cagr"] - spy_cost.metrics["cagr"],
            }
        )
    active_returns = strategy.returns - spy.returns
    active_nw = newey_west_mean_test(active_returns)
    active_psr = probabilistic_sharpe_ratio(active_returns, benchmark_sharpe=0.0)
    active_dsr = deflated_sharpe_ratio(
        active_returns, trials=CONSERVATIVE_SEARCH_TRIALS + len(GROWTH_GUARD_FAMILY)
    )
    family_active = pd.DataFrame(
        {
            f"core_{share:.2f}": result.returns - spy.returns
            for share, result in family_results.items()
        }
    )
    pbo = probability_of_backtest_overfitting(family_active, slices=10)
    rolling = _rolling_outperformance(strategy, spy)
    walk_forward = _growth_walk_forward(
        panel,
        start=start,
        cost_bps=cost_bps,
        family_targets=family_targets,
        family_results=family_results,
        benchmark=spy,
    )
    stress_periods = (
        ("global_financial_crisis", "2007-10-09", "2009-03-09"),
        ("covid_crash", "2020-02-19", "2020-03-23"),
        ("2022_bear", "2022-01-03", "2022-10-12"),
    )
    stress: dict[str, Any] = {}
    for label, period_start, period_end in stress_periods:
        stress[label] = {
            "strategy": _metrics_for_slice(strategy, period_start, period_end),
            "spy": _metrics_for_slice(spy, period_start, period_end),
            "qqq": _metrics_for_slice(qqq, period_start, period_end),
        }
    historical_gates = {
        "full_cagr_at_least_spy_plus_3pp": bool(
            strategy.metrics["cagr"] >= spy.metrics["cagr"] + 0.03
        ),
        "sharpe_above_spy": bool(strategy.metrics["sharpe"] > spy.metrics["sharpe"]),
        "drawdown_improvement_at_least_10pp": bool(
            strategy.metrics["max_drawdown"] >= spy.metrics["max_drawdown"] + 0.10
        ),
        "both_ten_year_halves_beat_spy": bool(
            halves["first"]["cagr_difference_vs_spy"] > 0
            and halves["second"]["cagr_difference_vs_spy"] > 0
        ),
        "rolling_five_year_win_rate_at_least_85pct": bool(
            rolling["summary"].get("cagr_win_fraction", 0.0) >= 0.85
        ),
        "still_beats_spy_at_50bps": bool(costs[-1]["cagr_difference_vs_spy"] > 0),
        "walk_forward_beats_spy": bool(walk_forward.get("cagr_difference_vs_spy", -1.0) > 0),
    }
    historical_pass = all(historical_gates.values())
    statistical_confirmation = bool(active_nw["t_stat"] >= 1.96 and active_dsr["probability"] >= 0.95)
    audit: dict[str, Any] = {
        "strategy_name": GROWTH_GUARD_NAME,
        "status": (
            "historical_outperformance_candidate_pending_live"
            if historical_pass and not statistical_confirmation
            else "historically_and_statistically_confirmed_pending_live"
            if historical_pass
            else "historical_gate_failed"
        ),
        "historical_gate_passed": historical_pass,
        "statistically_confirmed": statistical_confirmation,
        "live_confirmed": False,
        "promotion_ready": False,
        "frozen_parameters": {
            "core_share": GROWTH_GUARD_CORE_SHARE,
            "qqq_satellite_share": 1.0 - GROWTH_GUARD_CORE_SHARE,
            "selection_rule": (
                "Policy cap: QQQ satellite is limited to 80% and 20% remains in a diversified "
                "trend core. Nearby 90/10 and 85/15 settings had higher return, so 80/20 was "
                "not chosen as the return-maximizing row."
            ),
            "execution": "month-end close signal; next-session adjusted open",
            "cost_bps": cost_bps,
        },
        "strategy_metrics": strategy.metrics,
        "spy_metrics": spy.metrics,
        "qqq_metrics": qqq.metrics,
        "cagr_difference_vs_spy": strategy.metrics["cagr"] - spy.metrics["cagr"],
        "drawdown_improvement_vs_spy": (
            strategy.metrics["max_drawdown"] - spy.metrics["max_drawdown"]
        ),
        "active_return_newey_west": active_nw,
        "active_probabilistic_sharpe": active_psr,
        "active_deflated_sharpe": active_dsr,
        "local_family_pbo": pbo,
        "historical_gates": historical_gates,
        "ten_year_halves": halves,
        "rolling_five_year": rolling,
        "cost_sensitivity": costs,
        "walk_forward": walk_forward,
        "stress_periods": stress,
        "family": family_rows,
        "current_target": {
            str(ticker): float(weight)
            for ticker, weight in strategy.current_target.items()
            if weight > 0
        },
        "plain_language": {
            "what_it_does": (
                "Uses QQQ as the growth engine and a smaller diversified trend core to reduce "
                "risk when fewer markets remain above their long-term trend."
            ),
            "what_is_proven": "Beat SPY in this frozen 20-year historical simulation after costs.",
            "what_is_not_proven": (
                "The active return is not statistically significant and the LIVE paper account "
                "has not completed a forward evaluation period."
            ),
        },
    }
    return strategy, target, audit


def evaluate_volatility_guard_research(
    panel: MarketPanel,
    *,
    start: str,
    cost_bps: float = 10.0,
) -> tuple[BacktestResult, pd.DataFrame, dict[str, Any]]:
    """Evaluate the frozen unlevered volatility-managed growth policy."""
    spy = run_backtest(
        panel,
        buy_and_hold_targets(panel.close, "SPY", signal_on=start),
        name="SPY 買進持有",
        cost_bps=cost_bps,
        start=start,
    )
    qqq = run_backtest(
        panel,
        buy_and_hold_targets(panel.close, "QQQ", signal_on=start),
        name="QQQ 買進持有",
        cost_bps=cost_bps,
        start=start,
    )
    passive_target = fixed_weight_targets(panel.close, PASSIVE_90_10_WEIGHTS)
    passive_90_10 = run_backtest(
        panel,
        passive_target,
        name=PASSIVE_90_10_NAME,
        cost_bps=cost_bps,
        start=start,
    )
    incumbent_target = growth_guard_targets(panel.close)
    incumbent = run_backtest(
        panel,
        incumbent_target,
        name=GROWTH_GUARD_NAME,
        cost_bps=cost_bps,
        start=start,
    )
    family_targets: dict[tuple[int, float], pd.DataFrame] = {}
    family_results: dict[tuple[int, float], BacktestResult] = {}
    family_rows: list[dict[str, float]] = []
    for window in VOLATILITY_GUARD_WINDOWS:
        for target_volatility in VOLATILITY_GUARD_TARGETS:
            target = volatility_guard_targets(
                panel.close,
                target_volatility=target_volatility,
                volatility_window=window,
            )
            result = run_backtest(
                panel,
                target,
                name=f"volatility-guard-{window}-{target_volatility:.2f}",
                cost_bps=cost_bps,
                start=start,
            )
            key = (window, target_volatility)
            family_targets[key] = target
            family_results[key] = result
            family_rows.append(
                {
                    "volatility_window": float(window),
                    "target_volatility": target_volatility,
                    **result.metrics,
                    "cagr_difference_vs_spy": result.metrics["cagr"] - spy.metrics["cagr"],
                    "drawdown_improvement_vs_spy": (
                        result.metrics["max_drawdown"] - spy.metrics["max_drawdown"]
                    ),
                }
            )

    selected_key = (VOLATILITY_GUARD_WINDOW, VOLATILITY_GUARD_TARGET)
    target = family_targets[selected_key]
    raw = family_results[selected_key]
    strategy = BacktestResult(
        name=VOLATILITY_GUARD_NAME,
        equity=raw.equity.rename(VOLATILITY_GUARD_NAME),
        returns=raw.returns.rename(VOLATILITY_GUARD_NAME),
        weights=raw.weights,
        turnover=raw.turnover,
        costs=raw.costs,
        metrics=raw.metrics,
        current_target=raw.current_target,
        diagnostics=raw.diagnostics,
    )
    midpoint = pd.Timestamp(start) + pd.DateOffset(years=10)
    halves: dict[str, Any] = {}
    for label, period_start, period_end in (
        ("first", start, (midpoint - pd.Timedelta(days=1)).strftime("%Y-%m-%d")),
        ("second", midpoint.strftime("%Y-%m-%d"), "2099-12-31"),
    ):
        strategy_metrics = _metrics_for_slice(strategy, period_start, period_end)
        spy_metrics = _metrics_for_slice(spy, period_start, period_end)
        passive_metrics = _metrics_for_slice(passive_90_10, period_start, period_end)
        halves[label] = {
            "strategy": strategy_metrics,
            "spy": spy_metrics,
            "passive_90_10": passive_metrics,
            "cagr_difference_vs_spy": strategy_metrics["cagr"] - spy_metrics["cagr"],
            "cagr_difference_vs_passive_90_10": (
                strategy_metrics["cagr"] - passive_metrics["cagr"]
            ),
        }

    costs: list[dict[str, float]] = []
    for cost in (5.0, 10.0, 25.0, 50.0, 100.0):
        result = strategy if cost == cost_bps else run_backtest(
            panel,
            target,
            name=f"volatility-guard-cost-{cost:g}",
            cost_bps=cost,
            start=start,
        )
        spy_cost = spy if cost == cost_bps else run_backtest(
            panel,
            buy_and_hold_targets(panel.close, "SPY", signal_on=start),
            name=f"spy-cost-{cost:g}",
            cost_bps=cost,
            start=start,
        )
        passive_cost = passive_90_10 if cost == cost_bps else run_backtest(
            panel,
            passive_target,
            name=f"passive-90-10-cost-{cost:g}",
            cost_bps=cost,
            start=start,
        )
        costs.append(
            {
                "cost_bps": cost,
                **result.metrics,
                "spy_cagr": spy_cost.metrics["cagr"],
                "cagr_difference_vs_spy": result.metrics["cagr"] - spy_cost.metrics["cagr"],
                "passive_90_10_cagr": passive_cost.metrics["cagr"],
                "cagr_difference_vs_passive_90_10": (
                    result.metrics["cagr"] - passive_cost.metrics["cagr"]
                ),
            }
        )

    active_returns = strategy.returns - spy.returns
    active_nw = newey_west_mean_test(active_returns)
    active_psr = probabilistic_sharpe_ratio(active_returns, benchmark_sharpe=0.0)
    global_trials = (
        CONSERVATIVE_SEARCH_TRIALS
        + len(GROWTH_GUARD_FAMILY)
        + len(VOLATILITY_GUARD_TARGETS) * len(VOLATILITY_GUARD_WINDOWS)
    )
    active_dsr = deflated_sharpe_ratio(active_returns, trials=global_trials)
    exposure_control_returns = strategy.returns - passive_90_10.returns
    exposure_control_nw = newey_west_mean_test(exposure_control_returns)
    exposure_control_psr = probabilistic_sharpe_ratio(
        exposure_control_returns, benchmark_sharpe=0.0
    )
    exposure_control_dsr = deflated_sharpe_ratio(
        exposure_control_returns, trials=global_trials
    )
    family_active = pd.DataFrame(
        {
            f"window_{window}_target_{target_volatility:.2f}": result.returns - spy.returns
            for (window, target_volatility), result in family_results.items()
        }
    )
    pbo = probability_of_backtest_overfitting(family_active, slices=10)
    rolling = _rolling_outperformance(strategy, spy)
    rolling_vs_passive = _rolling_outperformance(strategy, passive_90_10)

    fixed_start = "2012-01-01"
    fixed_strategy = run_backtest(
        panel,
        target,
        name="波動管理固定政策 2012 至今",
        cost_bps=cost_bps,
        start=fixed_start,
    )
    fixed_spy = run_backtest(
        panel,
        buy_and_hold_targets(panel.close, "SPY", signal_on=fixed_start),
        name="SPY 2012 至今",
        cost_bps=cost_bps,
        start=fixed_start,
    )
    fixed_policy = {
        "start": fixed_start,
        "strategy_metrics": fixed_strategy.metrics,
        "spy_metrics": fixed_spy.metrics,
        "cagr_difference_vs_spy": (
            fixed_strategy.metrics["cagr"] - fixed_spy.metrics["cagr"]
        ),
        "active_return_newey_west": newey_west_mean_test(
            fixed_strategy.returns - fixed_spy.returns
        ),
        "caveat": (
            "The policy is fixed throughout 2012 onward, but it was selected after broader "
            "research and is not a pristine independent holdout."
        ),
    }
    stress: dict[str, Any] = {}
    for label, period_start, period_end in (
        ("global_financial_crisis", "2007-10-09", "2009-03-09"),
        ("covid_crash", "2020-02-19", "2020-03-23"),
        ("2022_bear", "2022-01-03", "2022-10-12"),
    ):
        stress[label] = {
            "strategy": _metrics_for_slice(strategy, period_start, period_end),
            "spy": _metrics_for_slice(spy, period_start, period_end),
            "qqq": _metrics_for_slice(qqq, period_start, period_end),
        }
    exposure = target["QQQ"].dropna()
    exposure_stats = {
        "mean_qqq_weight": float(exposure.mean()),
        "median_qqq_weight": float(exposure.median()),
        "minimum_qqq_weight": float(exposure.min()),
        "full_qqq_fraction": float((exposure >= 1.0 - 1e-12).mean()),
    }
    exposure_control_gates = {
        "full_cagr_above_passive_90_10": bool(
            strategy.metrics["cagr"] > passive_90_10.metrics["cagr"]
        ),
        "sharpe_above_passive_90_10": bool(
            strategy.metrics["sharpe"] > passive_90_10.metrics["sharpe"]
        ),
        "drawdown_improvement_at_least_10pp_vs_passive_90_10": bool(
            strategy.metrics["max_drawdown"]
            >= passive_90_10.metrics["max_drawdown"] + 0.10
        ),
        "both_ten_year_halves_beat_passive_90_10": bool(
            halves["first"]["cagr_difference_vs_passive_90_10"] > 0
            and halves["second"]["cagr_difference_vs_passive_90_10"] > 0
        ),
        "rolling_five_year_win_rate_vs_passive_at_least_75pct": bool(
            rolling_vs_passive["summary"].get("cagr_win_fraction", 0.0) >= 0.75
        ),
        "still_beats_passive_90_10_at_25bps": bool(
            next(
                row["cagr_difference_vs_passive_90_10"]
                for row in costs
                if row["cost_bps"] == 25.0
            )
            > 0
        ),
        "positive_average_daily_active_return_vs_passive_90_10": bool(
            exposure_control_nw["annualized"] > 0
        ),
    }
    historical_gates = {
        "full_cagr_at_least_spy_plus_3pp": bool(
            strategy.metrics["cagr"] >= spy.metrics["cagr"] + 0.03
        ),
        "sharpe_above_spy": bool(strategy.metrics["sharpe"] > spy.metrics["sharpe"]),
        "drawdown_improvement_at_least_15pp": bool(
            strategy.metrics["max_drawdown"] >= spy.metrics["max_drawdown"] + 0.15
        ),
        "both_ten_year_halves_beat_spy": bool(
            halves["first"]["cagr_difference_vs_spy"] > 0
            and halves["second"]["cagr_difference_vs_spy"] > 0
        ),
        "rolling_five_year_win_rate_at_least_90pct": bool(
            rolling["summary"].get("cagr_win_fraction", 0.0) >= 0.90
        ),
        "latest_five_year_window_beats_spy": bool(
            rolling["summary"].get("latest_cagr_difference", -1.0) > 0
        ),
        "still_beats_spy_at_100bps": bool(costs[-1]["cagr_difference_vs_spy"] > 0),
        "fixed_policy_2012_beats_spy": bool(fixed_policy["cagr_difference_vs_spy"] > 0),
        "improves_incumbent_cagr_and_drawdown": bool(
            strategy.metrics["cagr"] > incumbent.metrics["cagr"]
            and strategy.metrics["max_drawdown"] > incumbent.metrics["max_drawdown"]
        ),
        "average_qqq_weight_no_more_than_90pct": bool(
            exposure_stats["mean_qqq_weight"] <= 0.90
        ),
    }
    historical_pass = all(historical_gates.values())
    exposure_control_pass = all(exposure_control_gates.values())
    statistical_confirmation = bool(
        active_nw["t_stat"] >= 1.96 and active_dsr["probability"] >= 0.95
    )
    audit: dict[str, Any] = {
        "strategy_name": VOLATILITY_GUARD_NAME,
        "strategy_version": 2,
        "status": (
            "exposure_control_failed_paper_only"
            if historical_pass and not exposure_control_pass
            else
            "historical_outperformance_candidate_pending_live"
            if historical_pass and not statistical_confirmation
            else "historically_and_statistically_confirmed_pending_live"
            if historical_pass
            else "historical_gate_failed"
        ),
        "historical_gate_passed": historical_pass,
        "exposure_control_passed": exposure_control_pass,
        "reference_trade_candidate": bool(historical_pass and exposure_control_pass),
        "statistically_confirmed": statistical_confirmation,
        "live_confirmed": False,
        "promotion_ready": False,
        "frozen_parameters": {
            "growth_asset": "QQQ",
            "defensive_asset": "SHY",
            "target_annualized_volatility": VOLATILITY_GUARD_TARGET,
            "realized_volatility_window_sessions": VOLATILITY_GUARD_WINDOW,
            "maximum_qqq_weight": 1.0,
            "leverage_allowed": False,
            "selection_rule": (
                "18% is the middle risk target in the predeclared 14/18/22% family; 22% had "
                "higher return and 14% had lower drawdown, so 18% was not an endpoint winner."
            ),
            "execution": "month-end close signal; next-session adjusted open",
            "cost_bps": cost_bps,
        },
        "strategy_metrics": strategy.metrics,
        "spy_metrics": spy.metrics,
        "qqq_metrics": qqq.metrics,
        "passive_90_10_metrics": passive_90_10.metrics,
        "incumbent_growth_guard_metrics": incumbent.metrics,
        "cagr_difference_vs_spy": strategy.metrics["cagr"] - spy.metrics["cagr"],
        "drawdown_improvement_vs_spy": (
            strategy.metrics["max_drawdown"] - spy.metrics["max_drawdown"]
        ),
        "cagr_difference_vs_passive_90_10": (
            strategy.metrics["cagr"] - passive_90_10.metrics["cagr"]
        ),
        "drawdown_improvement_vs_passive_90_10": (
            strategy.metrics["max_drawdown"] - passive_90_10.metrics["max_drawdown"]
        ),
        "improvement_vs_incumbent": {
            "cagr_difference": strategy.metrics["cagr"] - incumbent.metrics["cagr"],
            "drawdown_improvement": (
                strategy.metrics["max_drawdown"] - incumbent.metrics["max_drawdown"]
            ),
        },
        "active_return_newey_west": active_nw,
        "active_probabilistic_sharpe": active_psr,
        "active_deflated_sharpe": active_dsr,
        "exposure_control_newey_west": exposure_control_nw,
        "exposure_control_probabilistic_sharpe": exposure_control_psr,
        "exposure_control_deflated_sharpe": exposure_control_dsr,
        "local_family_pbo": pbo,
        "historical_gates": historical_gates,
        "exposure_control_gates": exposure_control_gates,
        "ten_year_halves": halves,
        "rolling_five_year": rolling,
        "rolling_five_year_vs_passive_90_10": rolling_vs_passive,
        "cost_sensitivity": costs,
        "fixed_policy_2012": fixed_policy,
        "stress_periods": stress,
        "family": family_rows,
        "exposure_statistics": exposure_stats,
        "current_target": {
            str(ticker): float(weight)
            for ticker, weight in strategy.current_target.items()
            if weight > 0
        },
        "plain_language": {
            "what_it_does": (
                "Invests more in QQQ when its recent volatility is low and automatically moves "
                "the unused weight to SHY when volatility rises; it never uses leverage."
            ),
            "what_is_proven": (
                "Beat SPY and reduced drawdown versus a passive 90/10 QQQ/SHY mix in this "
                "frozen 20-year simulation after costs."
            ),
            "what_is_not_proven": (
                "The return edge over passive 90/10 fails decade, rolling-window, cost, and "
                "average-active-return checks; the version-2 LIVE paper account also has no "
                "forward history yet."
            ),
        },
    }
    return strategy, target, audit


def _proxy_panel_with_cash(panel: MarketPanel, *, cash_ticker: str = "CASH") -> MarketPanel:
    """Add a deterministic zero-return sleeve for a pre-ETF proxy audit."""
    frames: dict[str, pd.DataFrame] = {}
    for field, frame in panel.field_map().items():
        derived = frame.copy()
        derived[cash_ticker] = 0.0 if field == "Volume" else 1.0
        frames[field] = derived
    return MarketPanel(
        open=frames["Open"],
        high=frames["High"],
        low=frames["Low"],
        close=frames["Close"],
        volume=frames["Volume"],
        metadata={
            **panel.metadata,
            "derived_cash_proxy": (
                f"{cash_ticker}=constant 1.0; zero return; used only because SHY did not "
                "exist during the pre-2006 Nasdaq-100 proxy period"
            ),
        },
    )


def evaluate_v3_cross_market_research(
    panels: dict[str, MarketPanel],
    *,
    snapshot_receipts: dict[str, dict[str, Any]],
    protocol_sha256: str,
) -> dict[str, Any]:
    """Run the frozen v3 rule on five predeclared, non-US-only price indexes.

    This is deliberately a strict evaluator rather than a search helper: markets,
    dates, parameters, costs, and gates are constants from the protocol written before
    the snapshots were downloaded.  Any mismatch fails closed instead of silently
    changing the experiment.
    """
    expected = set(V3_CROSS_MARKETS)
    if set(panels) != expected:
        missing = sorted(expected - set(panels))
        extra = sorted(set(panels) - expected)
        raise ValueError(f"跨市場面板不符；缺少 {missing}；多出 {extra}")
    if set(snapshot_receipts) != expected:
        raise ValueError("跨市場快照收據必須與五個固定市場完全一致")
    if protocol_sha256 != V3_CROSS_MARKET_PROTOCOL_SHA256:
        raise ValueError("跨市場協議雜湊與下載前凍結版本不同")

    start_stamp = pd.Timestamp(V3_CROSS_MARKET_START)
    end_stamp = pd.Timestamp(V3_CROSS_MARKET_END)
    midpoint = start_stamp + (end_stamp - start_stamp) / 2
    first_end = (midpoint - pd.Timedelta(days=1)).strftime("%Y-%m-%d")
    second_start = midpoint.strftime("%Y-%m-%d")
    markets: dict[str, Any] = {}
    active_series: dict[str, pd.Series] = {}

    for ticker, identity in V3_CROSS_MARKETS.items():
        panel = panels[ticker]
        receipt = snapshot_receipts[ticker]
        if panel.tickers != [ticker]:
            raise ValueError(f"{ticker} 快照只能包含固定指數本身")
        if panel.end != end_stamp:
            raise ValueError(
                f"{ticker} 快照截止日錯誤：{panel.end.date()}，固定為 {end_stamp.date()}"
            )
        if panel.metadata.get("protocol_sha256") != protocol_sha256:
            raise ValueError(f"{ticker} 快照未綁定下載前協議雜湊")
        if receipt.get("protocol_sha256") != protocol_sha256:
            raise ValueError(f"{ticker} 收據未綁定下載前協議雜湊")
        if receipt.get("panel_sha256") in (None, "") or receipt.get(
            "archive_sha256"
        ) in (None, ""):
            raise ValueError(f"{ticker} 收據缺少面板或封存檔雜湊")
        warmup_sessions = int((panel.close.index < start_stamp).sum())
        if warmup_sessions < TREND_CONFIRMED_MOMENTUM_WINDOW:
            raise ValueError(
                f"{ticker} 驗證前只有 {warmup_sessions} 個 session，少於固定 252 日暖機"
            )

        proxy = _proxy_panel_with_cash(panel)
        target = trend_confirmed_volatility_guard_targets(
            proxy.close,
            growth=ticker,
            defensive="CASH",
            target_volatility=TREND_CONFIRMED_TARGET,
            volatility_window=TREND_CONFIRMED_VOL_WINDOW,
            momentum_window=TREND_CONFIRMED_MOMENTUM_WINDOW,
            confirmation_months=TREND_CONFIRMED_MONTHS,
        )
        benchmark_target = buy_and_hold_targets(
            proxy.close, ticker, signal_on=V3_CROSS_MARKET_START
        )
        strategy = run_backtest(
            proxy,
            target,
            name=f"v3 {identity['index']}",
            cost_bps=10.0,
            start=V3_CROSS_MARKET_START,
        )
        benchmark = run_backtest(
            proxy,
            benchmark_target,
            name=f"{identity['index']} buy-and-hold",
            cost_bps=10.0,
            start=V3_CROSS_MARKET_START,
        )
        strategy_50 = run_backtest(
            proxy,
            target,
            name=f"v3 {identity['index']} cost 50",
            cost_bps=50.0,
            start=V3_CROSS_MARKET_START,
        )
        benchmark_50 = run_backtest(
            proxy,
            benchmark_target,
            name=f"{identity['index']} buy-and-hold cost 50",
            cost_bps=50.0,
            start=V3_CROSS_MARKET_START,
        )
        rolling = _rolling_outperformance(strategy, benchmark)
        active = strategy.returns.sub(benchmark.returns, fill_value=0.0)
        active_series[ticker] = active
        active_nw = newey_west_mean_test(active)

        halves: dict[str, Any] = {}
        for label, period_start, period_end in (
            ("first", V3_CROSS_MARKET_START, first_end),
            ("second", second_start, V3_CROSS_MARKET_END),
        ):
            strategy_metrics = _metrics_for_slice(
                strategy, period_start, period_end
            )
            benchmark_metrics = _metrics_for_slice(
                benchmark, period_start, period_end
            )
            halves[label] = {
                "start": period_start,
                "end": period_end,
                "strategy_metrics": strategy_metrics,
                "benchmark_metrics": benchmark_metrics,
                "cagr_difference": (
                    strategy_metrics["cagr"] - benchmark_metrics["cagr"]
                ),
            }

        rolling_summary = rolling["summary"]
        cagr_difference = strategy.metrics["cagr"] - benchmark.metrics["cagr"]
        drawdown_improvement = (
            strategy.metrics["max_drawdown"] - benchmark.metrics["max_drawdown"]
        )
        cost_50_difference = (
            strategy_50.metrics["cagr"] - benchmark_50.metrics["cagr"]
        )
        gates = {
            "full_cagr_above_buy_and_hold": cagr_difference > 0.0,
            "sharpe_above_buy_and_hold": (
                strategy.metrics["sharpe"] > benchmark.metrics["sharpe"]
            ),
            "drawdown_improvement_at_least_10pp": drawdown_improvement >= 0.10,
            "still_beats_buy_and_hold_at_50bps": cost_50_difference > 0.0,
            "rolling_five_year_win_rate_at_least_60pct": (
                float(rolling_summary.get("cagr_win_fraction", 0.0)) >= 0.60
            ),
            "both_fixed_halves_beat_buy_and_hold": (
                halves["first"]["cagr_difference"] > 0.0
                and halves["second"]["cagr_difference"] > 0.0
            ),
        }
        markets[ticker] = {
            **identity,
            "ticker": ticker,
            "period": {
                "start": V3_CROSS_MARKET_START,
                "end": V3_CROSS_MARKET_END,
                "sessions": int(len(strategy.equity)),
                "warmup_sessions": warmup_sessions,
            },
            "strategy_metrics": strategy.metrics,
            "benchmark_metrics": benchmark.metrics,
            "cagr_difference": cagr_difference,
            "sharpe_difference": (
                strategy.metrics["sharpe"] - benchmark.metrics["sharpe"]
            ),
            "drawdown_improvement": drawdown_improvement,
            "cost_50bps": {
                "strategy_cagr": strategy_50.metrics["cagr"],
                "benchmark_cagr": benchmark_50.metrics["cagr"],
                "cagr_difference": cost_50_difference,
            },
            "rolling_five_year": rolling,
            "active_return_newey_west": active_nw,
            "halves": halves,
            "gates": gates,
            "snapshot": receipt,
        }

    pooled_active = (
        pd.concat(active_series, axis=1, sort=True).mean(axis=1, skipna=True).dropna()
    )
    pooled_nw = newey_west_mean_test(pooled_active)
    pooled_dsr = deflated_sharpe_ratio(
        pooled_active, trials=V3_GLOBAL_SEARCH_TRIALS
    )
    counts = {
        "full_cagr": sum(
            item["gates"]["full_cagr_above_buy_and_hold"]
            for item in markets.values()
        ),
        "sharpe": sum(
            item["gates"]["sharpe_above_buy_and_hold"]
            for item in markets.values()
        ),
        "drawdown_10pp": sum(
            item["gates"]["drawdown_improvement_at_least_10pp"]
            for item in markets.values()
        ),
        "cost_50bps": sum(
            item["gates"]["still_beats_buy_and_hold_at_50bps"]
            for item in markets.values()
        ),
        "rolling_60pct": sum(
            item["gates"]["rolling_five_year_win_rate_at_least_60pct"]
            for item in markets.values()
        ),
        "both_halves": sum(
            item["gates"]["both_fixed_halves_beat_buy_and_hold"]
            for item in markets.values()
        ),
    }
    rolling_win_rates = [
        float(item["rolling_five_year"]["summary"].get("cagr_win_fraction", 0.0))
        for item in markets.values()
    ]
    aggregate_gates = {
        "at_least_four_full_cagr_wins": counts["full_cagr"] >= 4,
        "at_least_four_sharpe_wins": counts["sharpe"] >= 4,
        "at_least_four_drawdown_improvements_of_10pp": counts["drawdown_10pp"] >= 4,
        "at_least_four_cost_50bps_wins": counts["cost_50bps"] >= 4,
        "rolling_median_and_three_markets_at_least_60pct": (
            float(np.median(rolling_win_rates)) >= 0.60
            and counts["rolling_60pct"] >= 3
        ),
        "pooled_active_newey_west_t_at_least_1_96": pooled_nw["t_stat"] >= 1.96,
        "at_least_three_markets_win_both_halves": counts["both_halves"] >= 3,
    }
    passed = all(aggregate_gates.values())
    return {
        "schema_version": 1,
        "strategy_name": TREND_CONFIRMED_GUARD_NAME,
        "status": "cross_market_passed" if passed else "cross_market_failed",
        "cross_market_passed": passed,
        "promotion_effect": "none",
        "protocol": {
            "path": "docs/V3_CROSS_MARKET_PROTOCOL.md",
            "sha256": protocol_sha256,
            "frozen_before_download": True,
        },
        "period": {
            "start": V3_CROSS_MARKET_START,
            "end": V3_CROSS_MARKET_END,
            "calendar": "each market local sessions; pooled series equal-weights available markets",
            "halves_midpoint": second_start,
        },
        "parameters": {
            "momentum_window": TREND_CONFIRMED_MOMENTUM_WINDOW,
            "confirmation_months": TREND_CONFIRMED_MONTHS,
            "target_volatility": TREND_CONFIRMED_TARGET,
            "volatility_window": TREND_CONFIRMED_VOL_WINDOW,
            "primary_cost_bps": 10.0,
            "stress_cost_bps": 50.0,
            "defensive_asset": "CASH",
            "cash_return": 0.0,
            "leverage": False,
            "execution_clock": "month-end close signal; next local session adjusted open",
        },
        "markets": markets,
        "counts": counts,
        "rolling_five_year_win_rate_median": float(np.median(rolling_win_rates)),
        "pooled_active_return": {
            "observations": int(len(pooled_active)),
            "newey_west": pooled_nw,
            "deflated_sharpe": pooled_dsr,
        },
        "aggregate_gates": aggregate_gates,
        "interpretation": (
            "The frozen v3 mechanism did not generalize across the five predeclared "
            "price indexes; a failed cross-market result cannot promote the strategy "
            "or replace its proxy, statistical, and forward-paper gates."
        ),
    }


def _validate_v4_snapshot(
    panel: MarketPanel,
    *,
    receipt: dict[str, Any],
    expected_tickers: tuple[str, ...],
    expected_start: str,
    expected_end: str,
    evaluation_start: str,
    strategy_assets: tuple[str, ...],
    protocol_sha256: str,
    label: str,
) -> dict[str, int]:
    """Fail closed when a v4 input differs from the pre-data protocol."""
    if set(panel.tickers) != set(expected_tickers) or len(panel.tickers) != len(
        expected_tickers
    ):
        raise ValueError(f"{label}快照代號必須與凍結協議完全一致")
    start_stamp = pd.Timestamp(expected_start)
    end_stamp = pd.Timestamp(expected_end)
    if panel.start != start_stamp or panel.end != end_stamp:
        raise ValueError(
            f"{label}快照期間錯誤：{panel.start.date()}–{panel.end.date()}，"
            f"固定為 {start_stamp.date()}–{end_stamp.date()}"
        )
    if panel.metadata.get("protocol_sha256") != protocol_sha256:
        raise ValueError(f"{label}快照未綁定下載前協議雜湊")
    if receipt.get("protocol_sha256") != protocol_sha256:
        raise ValueError(f"{label}收據未綁定下載前協議雜湊")
    if receipt.get("start") != expected_start or receipt.get("end") != expected_end:
        raise ValueError(f"{label}收據期間與凍結協議不同")
    actual_panel_sha256 = panel_fingerprint(panel)
    if receipt.get("panel_sha256") != actual_panel_sha256:
        raise ValueError(f"{label}面板內容與收據雜湊不同")
    if receipt.get("archive_sha256") in (None, ""):
        raise ValueError(f"{label}收據缺少封存檔雜湊")

    evaluation_stamp = pd.Timestamp(evaluation_start)
    warmup: dict[str, int] = {}
    for ticker in strategy_assets:
        valid = panel.close.loc[panel.close.index < evaluation_stamp, ticker]
        warmup[ticker] = int(valid.replace([np.inf, -np.inf], np.nan).notna().sum())
    return warmup


def _fixed_period_comparison(
    strategy: BacktestResult,
    benchmarks: dict[str, BacktestResult],
    *,
    start: str,
    end: str,
    half_years: int,
) -> dict[str, Any]:
    index = strategy.equity.loc[start:end].index
    target_midpoint = pd.Timestamp(start) + pd.DateOffset(years=half_years)
    second_candidates = index[index >= target_midpoint]
    if not len(second_candidates):
        raise ValueError("固定前後半段沒有足夠歷史")
    second_start_stamp = second_candidates[0]
    first_candidates = index[index < second_start_stamp]
    if not len(first_candidates):
        raise ValueError("固定前後半段無法切分")
    first_end_stamp = first_candidates[-1]
    periods = {
        "first": (pd.Timestamp(start), first_end_stamp),
        "second": (second_start_stamp, pd.Timestamp(end)),
    }
    rows: dict[str, Any] = {}
    for label, (period_start, period_end) in periods.items():
        start_text = period_start.strftime("%Y-%m-%d")
        end_text = period_end.strftime("%Y-%m-%d")
        strategy_metrics = _metrics_for_slice(strategy, start_text, end_text)
        benchmark_rows: dict[str, Any] = {}
        for key, benchmark in benchmarks.items():
            benchmark_metrics = _metrics_for_slice(benchmark, start_text, end_text)
            benchmark_rows[key] = {
                "metrics": benchmark_metrics,
                "cagr_difference": (
                    strategy_metrics["cagr"] - benchmark_metrics["cagr"]
                ),
            }
        rows[label] = {
            "start": start_text,
            "end": end_text,
            "strategy_metrics": strategy_metrics,
            "benchmarks": benchmark_rows,
        }
    return rows


def _v4_dataset_results(
    panel: MarketPanel,
    *,
    assets: tuple[str, ...],
    defensive: str,
    market_ticker: str,
    opportunity_ticker: str | None,
    start: str,
    end: str,
    half_years: int,
    name_prefix: str,
) -> tuple[BacktestResult, pd.DataFrame, dict[str, Any]]:
    target = style_rotation_targets(
        panel.close,
        assets=assets,
        defensive=defensive,
        long_lookback=252,
        skip_recent=21,
        slots=2,
    )
    equal_weights = {ticker: 1.0 / len(assets) for ticker in assets}
    benchmark_targets = {
        "market": buy_and_hold_targets(panel.close, market_ticker, signal_on=start),
        "equal_weight": fixed_weight_targets(
            panel.close, equal_weights, signal_on=start
        ),
    }
    if opportunity_ticker is not None:
        benchmark_targets["opportunity"] = buy_and_hold_targets(
            panel.close, opportunity_ticker, signal_on=start
        )

    strategy = run_backtest(
        panel,
        target,
        name=f"{name_prefix}風格輪動",
        cost_bps=10.0,
        start=start,
    )
    strategy_50 = run_backtest(
        panel,
        target,
        name=f"{name_prefix}風格輪動（50 bps）",
        cost_bps=50.0,
        start=start,
    )
    benchmarks: dict[str, BacktestResult] = {}
    benchmarks_50: dict[str, BacktestResult] = {}
    for key, benchmark_target in benchmark_targets.items():
        benchmarks[key] = run_backtest(
            panel,
            benchmark_target,
            name=f"{name_prefix}{key}",
            cost_bps=10.0,
            start=start,
        )
        benchmarks_50[key] = run_backtest(
            panel,
            benchmark_target,
            name=f"{name_prefix}{key}（50 bps）",
            cost_bps=50.0,
            start=start,
        )

    comparisons: dict[str, Any] = {}
    rolling: dict[str, Any] = {}
    for key, benchmark in benchmarks.items():
        active = strategy.returns.sub(benchmark.returns, fill_value=0.0)
        comparisons[key] = {
            "cagr_difference": (
                strategy.metrics["cagr"] - benchmark.metrics["cagr"]
            ),
            "sharpe_difference": (
                strategy.metrics["sharpe"] - benchmark.metrics["sharpe"]
            ),
            "drawdown_improvement": (
                strategy.metrics["max_drawdown"]
                - benchmark.metrics["max_drawdown"]
            ),
            "active_return_newey_west": newey_west_mean_test(active),
            "active_deflated_sharpe": deflated_sharpe_ratio(
                active, trials=V4_GLOBAL_SEARCH_TRIALS
            ),
        }
        rolling[key] = _rolling_outperformance(
            strategy, benchmark, window=1_260, minimum_cagr_edge=0.001
        )

    cost_50 = {
        key: {
            "strategy_cagr": strategy_50.metrics["cagr"],
            "benchmark_cagr": benchmark.metrics["cagr"],
            "cagr_difference": (
                strategy_50.metrics["cagr"] - benchmark.metrics["cagr"]
            ),
        }
        for key, benchmark in benchmarks_50.items()
    }
    halves = _fixed_period_comparison(
        strategy,
        benchmarks,
        start=start,
        end=end,
        half_years=half_years,
    )
    equity_weight = strategy.weights.reindex(columns=list(assets), fill_value=0.0).sum(
        axis=1
    )
    return strategy, target, {
        "period": {
            "start": start,
            "end": end,
            "sessions": int(len(strategy.equity)),
        },
        "strategy_metrics": strategy.metrics,
        "benchmark_metrics": {
            key: result.metrics for key, result in benchmarks.items()
        },
        "comparisons": comparisons,
        "cost_50bps": cost_50,
        "rolling_five_year": rolling,
        "fixed_halves": halves,
        "exposure": {
            "mean_equity_weight": float(equity_weight.mean()),
            "minimum_equity_weight": float(equity_weight.min()),
            "maximum_equity_weight": float(equity_weight.max()),
            "fully_defensive_fraction": float((equity_weight < 1e-12).mean()),
            "half_invested_fraction": float(
                np.isclose(equity_weight, 0.5, atol=1e-10).mean()
            ),
            "fully_invested_fraction": float(
                np.isclose(equity_weight, 1.0, atol=1e-10).mean()
            ),
        },
        "current_target": {
            str(ticker): float(weight)
            for ticker, weight in strategy.current_target.items()
            if weight > 0.0
        },
    }


def evaluate_style_rotation_research(
    trade_panel: MarketPanel,
    proxy_panel: MarketPanel,
    *,
    trade_receipt: dict[str, Any],
    proxy_receipt: dict[str, Any],
    protocol_sha256: str,
) -> tuple[BacktestResult, pd.DataFrame, dict[str, Any]]:
    """Evaluate the single frozen v4 hypothesis without parameter search."""
    if protocol_sha256 != V4_STYLE_PROTOCOL_SHA256:
        raise ValueError("v4 風格輪動協議雜湊與下載前凍結版本不同")
    trade_warmup = _validate_v4_snapshot(
        trade_panel,
        receipt=trade_receipt,
        expected_tickers=V4_TRADE_TICKERS,
        expected_start="2003-07-01",
        expected_end=V4_TRADE_END,
        evaluation_start=V4_TRADE_START,
        strategy_assets=V4_TRADE_ASSETS,
        protocol_sha256=protocol_sha256,
        label="可交易樣本",
    )
    proxy_warmup = _validate_v4_snapshot(
        proxy_panel,
        receipt=proxy_receipt,
        expected_tickers=V4_PROXY_TICKERS,
        expected_start="1993-07-01",
        expected_end=V4_PROXY_END,
        evaluation_start=V4_PROXY_START,
        strategy_assets=V4_PROXY_ASSETS,
        protocol_sha256=protocol_sha256,
        label="舊代理樣本",
    )
    if any(value < 273 for value in trade_warmup.values()):
        failures = ", ".join(
            f"{ticker}={sessions}"
            for ticker, sessions in trade_warmup.items()
            if sessions < 273
        )
        raise ValueError(f"可交易樣本固定 273 日暖機不足：{failures}")
    proxy_data_gate_passed = all(value >= 273 for value in proxy_warmup.values())

    strategy, target, trade = _v4_dataset_results(
        trade_panel,
        assets=V4_TRADE_ASSETS,
        defensive="SHY",
        market_ticker="SPY",
        opportunity_ticker="QQQ",
        start=V4_TRADE_START,
        end=V4_TRADE_END,
        half_years=10,
        name_prefix="v4 可交易",
    )
    trade_market = trade["comparisons"]["market"]
    trade_equal = trade["comparisons"]["equal_weight"]
    trade_opportunity = trade["comparisons"]["opportunity"]
    trade_roll_market = trade["rolling_five_year"]["market"]["summary"]
    trade_roll_equal = trade["rolling_five_year"]["equal_weight"]["summary"]
    trade_halves_pass = all(
        half["benchmarks"][key]["cagr_difference"] > 0.0
        for half in trade["fixed_halves"].values()
        for key in ("market", "equal_weight")
    )
    trade_gates = {
        "01_trade_cagr_above_spy_and_equal_weight": (
            trade_market["cagr_difference"] > 0.0
            and trade_equal["cagr_difference"] > 0.0
        ),
        "02_trade_sharpe_above_spy_and_equal_weight": (
            trade_market["sharpe_difference"] > 0.0
            and trade_equal["sharpe_difference"] > 0.0
        ),
        "03_trade_drawdown_improves_spy_by_10pp": (
            trade_market["drawdown_improvement"] >= 0.10
        ),
        "04_trade_50bps_beats_spy_and_equal_weight": (
            trade["cost_50bps"]["market"]["cagr_difference"] > 0.0
            and trade["cost_50bps"]["equal_weight"]["cagr_difference"] > 0.0
        ),
        "05_trade_both_ten_year_halves_beat_spy_and_equal_weight": (
            trade_halves_pass
        ),
        "06_trade_rolling_five_year_wins_70pct_and_positive_median": (
            float(trade_roll_market.get("cagr_win_fraction", 0.0)) >= 0.70
            and float(trade_roll_equal.get("cagr_win_fraction", 0.0)) >= 0.70
            and float(trade_roll_market.get("median_cagr_difference", 0.0)) > 0.0
            and float(trade_roll_equal.get("median_cagr_difference", 0.0)) > 0.0
        ),
        "07_trade_newey_west_t_at_least_1_96_vs_spy_and_equal_weight": (
            trade_market["active_return_newey_west"]["t_stat"] >= 1.96
            and trade_equal["active_return_newey_west"]["t_stat"] >= 1.96
        ),
        "08_trade_qqq_opportunity_cost_and_drawdown": (
            trade_opportunity["cagr_difference"] >= -0.01
            and trade_opportunity["drawdown_improvement"] >= 0.10
        ),
    }
    if proxy_data_gate_passed:
        proxy_with_cash = _proxy_panel_with_cash(proxy_panel)
        _, _, proxy = _v4_dataset_results(
            proxy_with_cash,
            assets=V4_PROXY_ASSETS,
            defensive="CASH",
            market_ticker="^GSPC",
            opportunity_ticker=None,
            start=V4_PROXY_START,
            end=V4_PROXY_END,
            half_years=5,
            name_prefix="v4 舊代理",
        )
        proxy_market = proxy["comparisons"]["market"]
        proxy_equal = proxy["comparisons"]["equal_weight"]
        proxy_roll_market = proxy["rolling_five_year"]["market"]["summary"]
        proxy_roll_equal = proxy["rolling_five_year"]["equal_weight"]["summary"]
        proxy_halves_pass = all(
            half["benchmarks"][key]["cagr_difference"] > 0.0
            for half in proxy["fixed_halves"].values()
            for key in ("market", "equal_weight")
        )
        proxy_gates = {
            "09_proxy_cagr_above_gspc_and_equal_weight": (
                proxy_market["cagr_difference"] > 0.0
                and proxy_equal["cagr_difference"] > 0.0
            ),
            "10_proxy_sharpe_above_gspc_and_equal_weight": (
                proxy_market["sharpe_difference"] > 0.0
                and proxy_equal["sharpe_difference"] > 0.0
            ),
            "11_proxy_rolling_five_year_wins_60pct": (
                float(proxy_roll_market.get("cagr_win_fraction", 0.0)) >= 0.60
                and float(proxy_roll_equal.get("cagr_win_fraction", 0.0)) >= 0.60
            ),
            "12_proxy_both_five_year_halves_beat_gspc_and_equal_weight": (
                proxy_halves_pass
            ),
            "13_proxy_50bps_beats_gspc_and_equal_weight": (
                proxy["cost_50bps"]["market"]["cagr_difference"] > 0.0
                and proxy["cost_50bps"]["equal_weight"]["cagr_difference"] > 0.0
            ),
            "14_proxy_newey_west_t_at_least_1_96_vs_gspc_and_equal_weight": (
                proxy_market["active_return_newey_west"]["t_stat"] >= 1.96
                and proxy_equal["active_return_newey_west"]["t_stat"] >= 1.96
            ),
        }
        proxy["status"] = "evaluated"
    else:
        coverage: dict[str, Any] = {}
        for ticker in V4_PROXY_TICKERS:
            valid = proxy_panel.close[ticker].dropna()
            coverage[ticker] = {
                "valid_sessions": int(len(valid)),
                "first_valid": (
                    pd.Timestamp(valid.index[0]).strftime("%Y-%m-%d")
                    if len(valid)
                    else None
                ),
                "last_valid": (
                    pd.Timestamp(valid.index[-1]).strftime("%Y-%m-%d")
                    if len(valid)
                    else None
                ),
                "warmup_sessions_before_1996_07_31": proxy_warmup.get(ticker),
            }
        proxy = {
            "status": "data_gate_failed",
            "period": {"start": V4_PROXY_START, "end": V4_PROXY_END},
            "required_warmup_sessions": 273,
            "coverage": coverage,
            "reason": (
                "The frozen ^RLG/^RLV Yahoo series begin after the proxy evaluation "
                "start and have zero valid warmup sessions. The protocol forbids symbol "
                "substitution, so proxy performance gates are unavailable and fail closed."
            ),
        }
        proxy_gates = {
            "09_proxy_cagr_above_gspc_and_equal_weight": False,
            "10_proxy_sharpe_above_gspc_and_equal_weight": False,
            "11_proxy_rolling_five_year_wins_60pct": False,
            "12_proxy_both_five_year_halves_beat_gspc_and_equal_weight": False,
            "13_proxy_50bps_beats_gspc_and_equal_weight": False,
            "14_proxy_newey_west_t_at_least_1_96_vs_gspc_and_equal_weight": False,
        }
    gates = {**trade_gates, **proxy_gates}
    historical_passed = all(gates.values())
    audit = {
        "schema_version": 1,
        "strategy_name": "v4 股權風格輪動",
        "status": "historical_passed" if historical_passed else "historical_failed",
        "data_gate_passed": proxy_data_gate_passed,
        "historical_gate_passed": historical_passed,
        "paper_eligible": historical_passed,
        "reference_trade_candidate": False,
        "promotion_effect": "create_isolated_paper_only" if historical_passed else "none",
        "protocol": {
            "path": "docs/V4_STYLE_ROTATION_PROTOCOL.md",
            "sha256": protocol_sha256,
            "frozen_before_download": True,
            "global_search_trials": V4_GLOBAL_SEARCH_TRIALS,
        },
        "parameters": {
            "momentum": "close(t-21) / close(t-252) - 1",
            "slots": 2,
            "weight_per_slot": 0.5,
            "positive_scores_only": True,
            "primary_cost_bps": 10.0,
            "stress_cost_bps": 50.0,
            "leverage": False,
            "execution_clock": "completed month-end close signal; next session adjusted open",
        },
        "snapshots": {
            "trade": {**trade_receipt, "warmup_valid_sessions": trade_warmup},
            "proxy": {**proxy_receipt, "warmup_valid_sessions": proxy_warmup},
        },
        "trade": trade,
        "proxy": proxy,
        "gates": gates,
        "passed_gate_count": sum(gates.values()),
        "required_gate_count": len(gates),
        "forward_requirements_if_historical_passes": {
            "sessions": 252,
            "completed_rebalances": 6,
            "benchmarks": ["SPY", "QQQ", "static_style_equal_weight"],
            "same_start_and_cost": True,
        },
        "interpretation": (
            "This is a single predeclared style-momentum hypothesis tested on a tradable "
            "20-year sample and a non-overlapping older proxy sample. Failure of any gate "
            "prevents a paper account; passing history would permit only an isolated paper "
            "test, not reference trading or real-money promotion."
        ),
    }
    return strategy, target, audit


def _validate_v5_receipt(
    panel: MarketPanel,
    *,
    receipt: dict[str, Any],
    required_tickers: tuple[str, ...],
    expected_panel_sha256: str,
    expected_archive_sha256: str,
    expected_start: str | None,
    expected_end: str,
    warmup_ticker: str,
    evaluation_start: str,
    exact_tickers: bool,
    label: str,
) -> int:
    tickers = set(panel.tickers)
    required = set(required_tickers)
    if not required.issubset(tickers) or (exact_tickers and tickers != required):
        raise ValueError(f"{label}代號與 v5 凍結協議不同")
    if expected_start is not None and panel.start != pd.Timestamp(expected_start):
        raise ValueError(f"{label}起始日與 v5 凍結協議不同")
    if panel.end != pd.Timestamp(expected_end):
        raise ValueError(f"{label}截止日與 v5 凍結協議不同")
    actual_panel_sha256 = panel_fingerprint(panel)
    if actual_panel_sha256 != expected_panel_sha256:
        raise ValueError(f"{label}面板不是 v5 協議指定內容")
    if receipt.get("panel_sha256") != expected_panel_sha256:
        raise ValueError(f"{label}收據面板雜湊與 v5 協議不同")
    if receipt.get("archive_sha256") != expected_archive_sha256:
        raise ValueError(f"{label}封存檔雜湊與 v5 協議不同")
    warmup = panel.close.loc[
        panel.close.index < pd.Timestamp(evaluation_start), warmup_ticker
    ]
    warmup_sessions = int(
        warmup.replace([np.inf, -np.inf], np.nan).notna().sum()
    )
    if warmup_sessions < 252:
        raise ValueError(
            f"{label}{warmup_ticker} 只有 {warmup_sessions} 個有效暖機 session"
        )
    return warmup_sessions


def _fixed_midpoint_comparison(
    strategy: BacktestResult,
    benchmarks: dict[str, BacktestResult],
    *,
    start: str,
    end: str,
) -> dict[str, Any]:
    index = strategy.equity.loc[start:end].index
    midpoint = pd.Timestamp(start) + (
        pd.Timestamp(end) - pd.Timestamp(start)
    ) / 2
    second_candidates = index[index >= midpoint]
    if not len(second_candidates):
        raise ValueError("固定前後半期沒有足夠資料")
    second_start = second_candidates[0]
    first_end = index[index < second_start][-1]
    rows: dict[str, Any] = {}
    for label, period_start, period_end in (
        ("first", pd.Timestamp(start), first_end),
        ("second", second_start, pd.Timestamp(end)),
    ):
        start_text = period_start.strftime("%Y-%m-%d")
        end_text = period_end.strftime("%Y-%m-%d")
        strategy_metrics = _metrics_for_slice(strategy, start_text, end_text)
        rows[label] = {
            "start": start_text,
            "end": end_text,
            "strategy_metrics": strategy_metrics,
            "benchmarks": {
                key: {
                    "metrics": _metrics_for_slice(benchmark, start_text, end_text),
                    "cagr_difference": (
                        strategy_metrics["cagr"]
                        - _metrics_for_slice(benchmark, start_text, end_text)["cagr"]
                    ),
                }
                for key, benchmark in benchmarks.items()
            },
        }
    return rows


def _v5_dataset_results(
    panel: MarketPanel,
    *,
    growth: str,
    defensive: str,
    market_ticker: str,
    opportunity_ticker: str | None,
    start: str,
    end: str,
    half_years: int | None,
    name_prefix: str,
) -> tuple[
    BacktestResult,
    pd.DataFrame,
    dict[str, Any],
    dict[str, BacktestResult],
]:
    target = three_clock_ensemble_targets(
        panel.close,
        growth=growth,
        defensive=defensive,
        target_volatility=0.18,
        volatility_window=21,
        momentum_window=252,
        confirmation_months=2,
    )
    benchmark_targets = {
        "market": buy_and_hold_targets(panel.close, market_ticker, signal_on=start),
        "matched_95_5": fixed_weight_targets(
            panel.close,
            {growth: 0.95, defensive: 0.05},
            signal_on=start,
        ),
    }
    if opportunity_ticker is not None:
        benchmark_targets["opportunity"] = buy_and_hold_targets(
            panel.close, opportunity_ticker, signal_on=start
        )

    strategy = run_backtest(
        panel,
        target,
        name=f"{name_prefix}三時鐘集成",
        cost_bps=10.0,
        start=start,
    )
    strategy_50 = run_backtest(
        panel,
        target,
        name=f"{name_prefix}三時鐘集成（50 bps）",
        cost_bps=50.0,
        start=start,
    )
    benchmarks: dict[str, BacktestResult] = {}
    benchmarks_50: dict[str, BacktestResult] = {}
    for key, benchmark_target in benchmark_targets.items():
        benchmarks[key] = run_backtest(
            panel,
            benchmark_target,
            name=f"{name_prefix}{key}",
            cost_bps=10.0,
            start=start,
        )
        benchmarks_50[key] = run_backtest(
            panel,
            benchmark_target,
            name=f"{name_prefix}{key}（50 bps）",
            cost_bps=50.0,
            start=start,
        )

    comparisons: dict[str, Any] = {}
    rolling: dict[str, Any] = {}
    for key, benchmark in benchmarks.items():
        active = strategy.returns.sub(benchmark.returns, fill_value=0.0)
        comparisons[key] = {
            "cagr_difference": (
                strategy.metrics["cagr"] - benchmark.metrics["cagr"]
            ),
            "sharpe_difference": (
                strategy.metrics["sharpe"] - benchmark.metrics["sharpe"]
            ),
            "drawdown_improvement": (
                strategy.metrics["max_drawdown"]
                - benchmark.metrics["max_drawdown"]
            ),
            "active_return_newey_west": newey_west_mean_test(active),
            "active_deflated_sharpe": deflated_sharpe_ratio(
                active, trials=V5_GLOBAL_SEARCH_TRIALS
            ),
        }
        rolling[key] = _rolling_outperformance(
            strategy, benchmark, window=1_260, minimum_cagr_edge=0.001
        )
    costs = {
        key: {
            "strategy_cagr": strategy_50.metrics["cagr"],
            "benchmark_cagr": benchmark.metrics["cagr"],
            "cagr_difference": (
                strategy_50.metrics["cagr"] - benchmark.metrics["cagr"]
            ),
        }
        for key, benchmark in benchmarks_50.items()
    }
    halves = (
        _fixed_period_comparison(
            strategy, benchmarks, start=start, end=end, half_years=half_years
        )
        if half_years is not None
        else _fixed_midpoint_comparison(
            strategy, benchmarks, start=start, end=end
        )
    )
    growth_weight = strategy.weights.reindex(columns=[growth], fill_value=0.0)[
        growth
    ]
    data = {
        "period": {"start": start, "end": end, "sessions": int(len(strategy.equity))},
        "strategy_metrics": strategy.metrics,
        "benchmark_metrics": {
            key: benchmark.metrics for key, benchmark in benchmarks.items()
        },
        "comparisons": comparisons,
        "cost_50bps": costs,
        "rolling_five_year": rolling,
        "fixed_halves": halves,
        "exposure": {
            "mean_growth_weight": float(growth_weight.mean()),
            "minimum_growth_weight": float(growth_weight.min()),
            "maximum_growth_weight": float(growth_weight.max()),
            "below_50pct_fraction": float((growth_weight < 0.50).mean()),
            "above_95pct_fraction": float((growth_weight > 0.95).mean()),
        },
        "current_target": {
            str(ticker): float(weight)
            for ticker, weight in strategy.current_target.items()
            if weight > 0.0
        },
    }
    return strategy, target, data, benchmarks


def evaluate_three_clock_ensemble_research(
    main_panel: MarketPanel,
    proxy_panel: MarketPanel,
    cross_panels: dict[str, MarketPanel],
    *,
    main_receipt: dict[str, Any],
    proxy_receipt: dict[str, Any],
    cross_receipts: dict[str, dict[str, Any]],
    protocol_sha256: str,
) -> tuple[BacktestResult, pd.DataFrame, dict[str, Any]]:
    """Run the frozen v5 ensemble across recent, older, and five-market samples."""
    if protocol_sha256 != V5_THREE_CLOCK_PROTOCOL_SHA256:
        raise ValueError("v5 三時鐘協議雜湊與第一次計算前凍結版本不同")
    main_warmup = _validate_v5_receipt(
        main_panel,
        receipt=main_receipt,
        required_tickers=("QQQ", "SHY", "SPY"),
        expected_panel_sha256=V5_MAIN_PANEL_SHA256,
        expected_archive_sha256=V5_MAIN_ARCHIVE_SHA256,
        expected_start="2004-01-02",
        expected_end="2026-07-31",
        warmup_ticker="QQQ",
        evaluation_start="2006-07-31",
        exact_tickers=False,
        label="v5 主樣本",
    )
    proxy_warmup = _validate_v5_receipt(
        proxy_panel,
        receipt=proxy_receipt,
        required_tickers=("^NDX",),
        expected_panel_sha256=V5_PROXY_PANEL_SHA256,
        expected_archive_sha256=V5_PROXY_ARCHIVE_SHA256,
        expected_start="1985-10-01",
        expected_end="2006-07-28",
        warmup_ticker="^NDX",
        evaluation_start="1986-10-01",
        exact_tickers=True,
        label="v5 舊代理",
    )
    if set(cross_panels) != set(V3_CROSS_MARKETS) or set(cross_receipts) != set(
        V3_CROSS_MARKETS
    ):
        raise ValueError("v5 五市場輸入必須與凍結集合完全一致")

    strategy, target, main, _ = _v5_dataset_results(
        main_panel,
        growth="QQQ",
        defensive="SHY",
        market_ticker="SPY",
        opportunity_ticker="QQQ",
        start="2006-07-31",
        end="2026-07-31",
        half_years=10,
        name_prefix="v5 主樣本",
    )
    proxy_with_cash = _proxy_panel_with_cash(proxy_panel)
    _, _, proxy, _ = _v5_dataset_results(
        proxy_with_cash,
        growth="^NDX",
        defensive="CASH",
        market_ticker="^NDX",
        opportunity_ticker=None,
        start="1986-10-01",
        end="2006-07-28",
        half_years=10,
        name_prefix="v5 舊代理",
    )

    main_market = main["comparisons"]["market"]
    main_matched = main["comparisons"]["matched_95_5"]
    main_qqq = main["comparisons"]["opportunity"]
    main_roll_market = main["rolling_five_year"]["market"]["summary"]
    main_roll_matched = main["rolling_five_year"]["matched_95_5"]["summary"]
    main_halves_pass = all(
        half["benchmarks"][key]["cagr_difference"] > 0.0
        for half in main["fixed_halves"].values()
        for key in ("market", "matched_95_5")
    )
    proxy_market = proxy["comparisons"]["market"]
    proxy_matched = proxy["comparisons"]["matched_95_5"]
    proxy_roll_market = proxy["rolling_five_year"]["market"]["summary"]
    proxy_roll_matched = proxy["rolling_five_year"]["matched_95_5"]["summary"]
    proxy_halves_pass = all(
        half["benchmarks"][key]["cagr_difference"] > 0.0
        for half in proxy["fixed_halves"].values()
        for key in ("market", "matched_95_5")
    )

    gates: dict[str, bool] = {
        "01_main_cagr_above_spy_and_matched_95_5": (
            main_market["cagr_difference"] > 0.0
            and main_matched["cagr_difference"] > 0.0
        ),
        "02_main_sharpe_above_qqq_and_matched_95_5": (
            main_qqq["sharpe_difference"] > 0.0
            and main_matched["sharpe_difference"] > 0.0
        ),
        "03_main_drawdown_improves_qqq_10pp_and_matched_8pp": (
            main_qqq["drawdown_improvement"] >= 0.10
            and main_matched["drawdown_improvement"] >= 0.08
        ),
        "04_main_50bps_beats_spy_and_matched_95_5": (
            main["cost_50bps"]["market"]["cagr_difference"] > 0.0
            and main["cost_50bps"]["matched_95_5"]["cagr_difference"] > 0.0
        ),
        "05_main_both_ten_year_halves_beat_spy_and_matched_95_5": (
            main_halves_pass
        ),
        "06_main_rolling_wins_and_positive_medians": (
            float(main_roll_market.get("cagr_win_fraction", 0.0)) >= 0.70
            and float(main_roll_matched.get("cagr_win_fraction", 0.0)) >= 0.60
            and float(main_roll_market.get("median_cagr_difference", 0.0)) > 0.0
            and float(main_roll_matched.get("median_cagr_difference", 0.0)) > 0.0
        ),
        "07_main_newey_west_t_at_least_1_96_vs_spy_and_matched": (
            main_market["active_return_newey_west"]["t_stat"] >= 1.96
            and main_matched["active_return_newey_west"]["t_stat"] >= 1.96
        ),
        "08_main_qqq_return_and_drawdown_opportunity_cost": (
            main_qqq["cagr_difference"] >= -0.005
            and main_qqq["drawdown_improvement"] >= 0.10
        ),
        "09_main_dsr_at_least_95pct_vs_spy_and_matched": (
            main_market["active_deflated_sharpe"]["probability"] >= 0.95
            and main_matched["active_deflated_sharpe"]["probability"] >= 0.95
        ),
        "10_proxy_cagr_and_sharpe_above_ndx_and_matched": (
            proxy_market["cagr_difference"] > 0.0
            and proxy_matched["cagr_difference"] > 0.0
            and proxy_market["sharpe_difference"] > 0.0
            and proxy_matched["sharpe_difference"] > 0.0
        ),
        "11_proxy_drawdown_improves_ndx_10pp_and_matched_8pp": (
            proxy_market["drawdown_improvement"] >= 0.10
            and proxy_matched["drawdown_improvement"] >= 0.08
        ),
        "12_proxy_rolling_wins_and_positive_medians": (
            float(proxy_roll_market.get("cagr_win_fraction", 0.0)) >= 0.60
            and float(proxy_roll_matched.get("cagr_win_fraction", 0.0)) >= 0.60
            and float(proxy_roll_market.get("median_cagr_difference", 0.0)) > 0.0
            and float(proxy_roll_matched.get("median_cagr_difference", 0.0)) > 0.0
        ),
        "13_proxy_both_ten_year_halves_beat_ndx_and_matched": (
            proxy_halves_pass
        ),
        "14_proxy_50bps_beats_ndx_and_matched": (
            proxy["cost_50bps"]["market"]["cagr_difference"] > 0.0
            and proxy["cost_50bps"]["matched_95_5"]["cagr_difference"] > 0.0
        ),
        "15_proxy_newey_west_t_at_least_1_96_vs_ndx_and_matched": (
            proxy_market["active_return_newey_west"]["t_stat"] >= 1.96
            and proxy_matched["active_return_newey_west"]["t_stat"] >= 1.96
        ),
    }

    markets: dict[str, Any] = {}
    pooled_market_active: dict[str, pd.Series] = {}
    pooled_matched_active: dict[str, pd.Series] = {}
    for ticker, identity in V3_CROSS_MARKETS.items():
        source_panel = cross_panels[ticker]
        receipt = cross_receipts[ticker]
        expected_hashes = V5_CROSS_HASHES[ticker]
        warmup = _validate_v5_receipt(
            source_panel,
            receipt=receipt,
            required_tickers=(ticker,),
            expected_panel_sha256=expected_hashes["panel_sha256"],
            expected_archive_sha256=expected_hashes["archive_sha256"],
            expected_start=None,
            expected_end="2006-07-28",
            warmup_ticker=ticker,
            evaluation_start=V3_CROSS_MARKET_START,
            exact_tickers=True,
            label=f"v5 {ticker}",
        )
        cross_panel = _proxy_panel_with_cash(source_panel)
        cross_strategy, _, item, cross_benchmarks = _v5_dataset_results(
            cross_panel,
            growth=ticker,
            defensive="CASH",
            market_ticker=ticker,
            opportunity_ticker=None,
            start=V3_CROSS_MARKET_START,
            end=V3_CROSS_MARKET_END,
            half_years=None,
            name_prefix=f"v5 {ticker}",
        )
        market_comparison = item["comparisons"]["market"]
        matched_comparison = item["comparisons"]["matched_95_5"]
        rolling_market = item["rolling_five_year"]["market"]["summary"]
        rolling_matched = item["rolling_five_year"]["matched_95_5"]["summary"]
        halves_pass = all(
            half["benchmarks"][key]["cagr_difference"] > 0.0
            for half in item["fixed_halves"].values()
            for key in ("market", "matched_95_5")
        )
        market_gates = {
            "full_cagr_beats_both": (
                market_comparison["cagr_difference"] > 0.0
                and matched_comparison["cagr_difference"] > 0.0
            ),
            "sharpe_beats_both": (
                market_comparison["sharpe_difference"] > 0.0
                and matched_comparison["sharpe_difference"] > 0.0
            ),
            "drawdown_improves_buyhold_10pp": (
                market_comparison["drawdown_improvement"] >= 0.10
            ),
            "cost_50bps_beats_both": (
                item["cost_50bps"]["market"]["cagr_difference"] > 0.0
                and item["cost_50bps"]["matched_95_5"]["cagr_difference"] > 0.0
            ),
            "rolling_60pct_vs_both": (
                float(rolling_market.get("cagr_win_fraction", 0.0)) >= 0.60
                and float(rolling_matched.get("cagr_win_fraction", 0.0)) >= 0.60
            ),
            "both_halves_beat_both": halves_pass,
        }
        pooled_market_active[ticker] = cross_strategy.returns.sub(
            cross_benchmarks["market"].returns, fill_value=0.0
        )
        pooled_matched_active[ticker] = cross_strategy.returns.sub(
            cross_benchmarks["matched_95_5"].returns, fill_value=0.0
        )
        markets[ticker] = {
            **identity,
            "ticker": ticker,
            **item,
            "warmup_sessions": warmup,
            "gates": market_gates,
            "snapshot": receipt,
        }

    counts = {
        key: sum(bool(item["gates"][key]) for item in markets.values())
        for key in (
            "full_cagr_beats_both",
            "sharpe_beats_both",
            "drawdown_improves_buyhold_10pp",
            "cost_50bps_beats_both",
            "rolling_60pct_vs_both",
            "both_halves_beat_both",
        )
    }
    market_rolling_rates = [
        float(item["rolling_five_year"]["market"]["summary"]["cagr_win_fraction"])
        for item in markets.values()
    ]
    matched_rolling_rates = [
        float(
            item["rolling_five_year"]["matched_95_5"]["summary"][
                "cagr_win_fraction"
            ]
        )
        for item in markets.values()
    ]
    pooled_market = (
        pd.concat(pooled_market_active, axis=1, sort=True).mean(axis=1).dropna()
    )
    pooled_matched = (
        pd.concat(pooled_matched_active, axis=1, sort=True).mean(axis=1).dropna()
    )
    pooled = {
        "market": {
            "observations": int(len(pooled_market)),
            "newey_west": newey_west_mean_test(pooled_market),
            "deflated_sharpe": deflated_sharpe_ratio(
                pooled_market, trials=V5_GLOBAL_SEARCH_TRIALS
            ),
        },
        "matched_95_5": {
            "observations": int(len(pooled_matched)),
            "newey_west": newey_west_mean_test(pooled_matched),
            "deflated_sharpe": deflated_sharpe_ratio(
                pooled_matched, trials=V5_GLOBAL_SEARCH_TRIALS
            ),
        },
    }
    gates.update(
        {
            "16_cross_at_least_4_full_cagr_wins_vs_both": (
                counts["full_cagr_beats_both"] >= 4
            ),
            "17_cross_at_least_4_sharpe_wins_vs_both": (
                counts["sharpe_beats_both"] >= 4
            ),
            "18_cross_at_least_4_drawdown_improvements_10pp": (
                counts["drawdown_improves_buyhold_10pp"] >= 4
            ),
            "19_cross_at_least_4_cost_50bps_wins_vs_both": (
                counts["cost_50bps_beats_both"] >= 4
            ),
            "20_cross_rolling_medians_and_3_markets_at_least_60pct": (
                float(np.median(market_rolling_rates)) >= 0.60
                and float(np.median(matched_rolling_rates)) >= 0.60
                and counts["rolling_60pct_vs_both"] >= 3
            ),
            "21_cross_at_least_3_markets_win_both_halves_vs_both": (
                counts["both_halves_beat_both"] >= 3
            ),
            "22_cross_pooled_newey_west_t_at_least_1_96_vs_both": (
                pooled["market"]["newey_west"]["t_stat"] >= 1.96
                and pooled["matched_95_5"]["newey_west"]["t_stat"] >= 1.96
            ),
        }
    )
    passed = all(gates.values())
    audit = {
        "schema_version": 1,
        "strategy_name": "v5 三時鐘等權集成",
        "status": "historical_passed" if passed else "historical_failed",
        "historical_gate_passed": passed,
        "paper_eligible": passed,
        "reference_trade_candidate": False,
        "promotion_effect": "create_isolated_paper_only" if passed else "none",
        "protocol": {
            "path": "docs/V5_THREE_CLOCK_PROTOCOL.md",
            "sha256": protocol_sha256,
            "frozen_before_first_ensemble_calculation": True,
            "post_selection_existing_data": True,
            "global_search_trials": V5_GLOBAL_SEARCH_TRIALS,
        },
        "parameters": {
            "sleeves": {
                "static_buy_and_hold": 1.0 / 3.0,
                "volatility_managed": 1.0 / 3.0,
                "trend_confirmed": 1.0 / 3.0,
            },
            "target_volatility": 0.18,
            "volatility_window": 21,
            "momentum_window": 252,
            "confirmation_months": 2,
            "matched_control": "95% growth / 5% defensive",
            "primary_cost_bps": 10.0,
            "stress_cost_bps": 50.0,
            "leverage": False,
            "execution_clock": "completed month-end close; next local session adjusted open",
        },
        "snapshots": {
            "main": {**main_receipt, "warmup_sessions": main_warmup},
            "proxy": {**proxy_receipt, "warmup_sessions": proxy_warmup},
        },
        "main": main,
        "proxy": proxy,
        "cross_market": {
            "period": {"start": V3_CROSS_MARKET_START, "end": V3_CROSS_MARKET_END},
            "markets": markets,
            "counts": counts,
            "rolling_five_year_win_rate_medians": {
                "market": float(np.median(market_rolling_rates)),
                "matched_95_5": float(np.median(matched_rolling_rates)),
            },
            "pooled_active_return": pooled,
        },
        "gates": gates,
        "passed_gate_count": sum(bool(value) for value in gates.values()),
        "required_gate_count": len(gates),
        "forward_requirements_if_historical_passes": {
            "sessions": 252,
            "completed_rebalances": 6,
            "benchmarks": ["SPY", "QQQ", "matched_95_5"],
            "same_start_and_cost": True,
            "replay_counts": False,
        },
        "interpretation": (
            "The equal-sleeve ensemble is a post-selection integration of existing clocks. "
            "Only simultaneous success across all 22 recent, older, matched-exposure, "
            "cross-market, cost, rolling, and statistical gates can open an isolated paper "
            "account; historical passage alone cannot authorize reference trading."
        ),
    }
    return strategy, target, audit


def evaluate_trend_confirmed_guard_research(
    panel: MarketPanel,
    *,
    start: str,
    cost_bps: float = 10.0,
    proxy_panel: MarketPanel | None = None,
    proxy_start: str = "1986-10-01",
) -> tuple[BacktestResult, pd.DataFrame, dict[str, Any]]:
    """Evaluate v3 against QQQ, matched exposure, and an older Nasdaq-100 proxy.

    Version 3 is a post-selection candidate.  Its 12-month trend, two-month
    confirmation, 21-session volatility window, and 18% defensive target are frozen
    here before LIVE paper evidence begins.  The one- and three-month confirmation
    variants are retained as a local-neighborhood audit rather than discarded.
    """
    spy_target = buy_and_hold_targets(panel.close, "SPY", signal_on=start)
    qqq_target = buy_and_hold_targets(panel.close, "QQQ", signal_on=start)
    passive_target = fixed_weight_targets(panel.close, PASSIVE_90_10_WEIGHTS)
    matched_target = fixed_weight_targets(panel.close, MATCHED_96_4_WEIGHTS)
    spy = run_backtest(
        panel, spy_target, name="SPY 買進持有", cost_bps=cost_bps, start=start
    )
    qqq = run_backtest(
        panel, qqq_target, name="QQQ 買進持有", cost_bps=cost_bps, start=start
    )
    passive_90_10 = run_backtest(
        panel,
        passive_target,
        name=PASSIVE_90_10_NAME,
        cost_bps=cost_bps,
        start=start,
    )
    matched = run_backtest(
        panel,
        matched_target,
        name=MATCHED_96_4_NAME,
        cost_bps=cost_bps,
        start=start,
    )

    family_targets: dict[int, pd.DataFrame] = {}
    family_results: dict[int, BacktestResult] = {}
    for confirmations in TREND_CONFIRMED_FAMILY:
        family_target = trend_confirmed_volatility_guard_targets(
            panel.close,
            target_volatility=TREND_CONFIRMED_TARGET,
            volatility_window=TREND_CONFIRMED_VOL_WINDOW,
            momentum_window=TREND_CONFIRMED_MOMENTUM_WINDOW,
            confirmation_months=confirmations,
        )
        family_targets[confirmations] = family_target
        family_results[confirmations] = run_backtest(
            panel,
            family_target,
            name=f"trend-confirmed-{confirmations}",
            cost_bps=cost_bps,
            start=start,
        )

    target = family_targets[TREND_CONFIRMED_MONTHS]
    raw = family_results[TREND_CONFIRMED_MONTHS]
    strategy = BacktestResult(
        name=TREND_CONFIRMED_GUARD_NAME,
        equity=raw.equity.rename(TREND_CONFIRMED_GUARD_NAME),
        returns=raw.returns.rename(TREND_CONFIRMED_GUARD_NAME),
        weights=raw.weights,
        turnover=raw.turnover,
        costs=raw.costs,
        metrics=raw.metrics,
        current_target=raw.current_target,
        diagnostics=raw.diagnostics,
    )

    midpoint = pd.Timestamp(start) + pd.DateOffset(years=10)
    halves: dict[str, Any] = {}
    for label, period_start, period_end in (
        ("first", start, (midpoint - pd.Timedelta(days=1)).strftime("%Y-%m-%d")),
        ("second", midpoint.strftime("%Y-%m-%d"), "2099-12-31"),
    ):
        strategy_metrics = _metrics_for_slice(strategy, period_start, period_end)
        spy_metrics = _metrics_for_slice(spy, period_start, period_end)
        qqq_metrics = _metrics_for_slice(qqq, period_start, period_end)
        passive_metrics = _metrics_for_slice(passive_90_10, period_start, period_end)
        matched_metrics = _metrics_for_slice(matched, period_start, period_end)
        halves[label] = {
            "strategy": strategy_metrics,
            "spy": spy_metrics,
            "qqq": qqq_metrics,
            "passive_90_10": passive_metrics,
            "matched_96_4": matched_metrics,
            "cagr_difference_vs_spy": strategy_metrics["cagr"] - spy_metrics["cagr"],
            "cagr_difference_vs_qqq": strategy_metrics["cagr"] - qqq_metrics["cagr"],
            "cagr_difference_vs_passive_90_10": (
                strategy_metrics["cagr"] - passive_metrics["cagr"]
            ),
            "cagr_difference_vs_matched_96_4": (
                strategy_metrics["cagr"] - matched_metrics["cagr"]
            ),
        }

    costs: list[dict[str, float]] = []
    for cost in (5.0, 10.0, 25.0, 50.0, 100.0):
        result = strategy if cost == cost_bps else run_backtest(
            panel,
            target,
            name=f"trend-confirmed-cost-{cost:g}",
            cost_bps=cost,
            start=start,
        )
        qqq_cost = qqq if cost == cost_bps else run_backtest(
            panel, qqq_target, name=f"qqq-cost-{cost:g}", cost_bps=cost, start=start
        )
        matched_cost = matched if cost == cost_bps else run_backtest(
            panel,
            matched_target,
            name=f"matched-96-4-cost-{cost:g}",
            cost_bps=cost,
            start=start,
        )
        passive_cost = passive_90_10 if cost == cost_bps else run_backtest(
            panel,
            passive_target,
            name=f"passive-90-10-cost-{cost:g}",
            cost_bps=cost,
            start=start,
        )
        costs.append(
            {
                "cost_bps": cost,
                **result.metrics,
                "qqq_cagr": qqq_cost.metrics["cagr"],
                "cagr_difference_vs_qqq": result.metrics["cagr"] - qqq_cost.metrics["cagr"],
                "matched_96_4_cagr": matched_cost.metrics["cagr"],
                "cagr_difference_vs_matched_96_4": (
                    result.metrics["cagr"] - matched_cost.metrics["cagr"]
                ),
                "passive_90_10_cagr": passive_cost.metrics["cagr"],
                "cagr_difference_vs_passive_90_10": (
                    result.metrics["cagr"] - passive_cost.metrics["cagr"]
                ),
            }
        )

    active_vs_qqq = strategy.returns - qqq.returns
    active_vs_matched = strategy.returns - matched.returns
    active_nw = newey_west_mean_test(active_vs_qqq)
    matched_nw = newey_west_mean_test(active_vs_matched)
    active_psr = probabilistic_sharpe_ratio(active_vs_qqq, benchmark_sharpe=0.0)
    active_dsr = deflated_sharpe_ratio(
        active_vs_qqq, trials=V3_GLOBAL_SEARCH_TRIALS
    )
    family_active = pd.DataFrame(
        {
            f"confirmation_{confirmations}": result.returns - qqq.returns
            for confirmations, result in family_results.items()
        }
    )
    pbo = probability_of_backtest_overfitting(family_active, slices=10)
    rolling_vs_spy = _rolling_outperformance(strategy, spy)
    rolling_vs_qqq = _rolling_outperformance(strategy, qqq)
    rolling_vs_matched = _rolling_outperformance(strategy, matched)
    rolling_vs_passive = _rolling_outperformance(strategy, passive_90_10)

    family_rows: list[dict[str, Any]] = []
    for confirmations, result in family_results.items():
        result_25 = run_backtest(
            panel,
            family_targets[confirmations],
            name=f"confirmation-{confirmations}-cost-25",
            cost_bps=25.0,
            start=start,
        )
        qqq_25 = run_backtest(
            panel, qqq_target, name="qqq-family-cost-25", cost_bps=25.0, start=start
        )
        family_rows.append(
            {
                "confirmation_months": confirmations,
                **result.metrics,
                "cagr_difference_vs_qqq": result.metrics["cagr"] - qqq.metrics["cagr"],
                "drawdown_improvement_vs_qqq": (
                    result.metrics["max_drawdown"] - qqq.metrics["max_drawdown"]
                ),
                "cost_25bps_cagr_difference_vs_qqq": (
                    result_25.metrics["cagr"] - qqq_25.metrics["cagr"]
                ),
            }
        )

    proxy_validation: dict[str, Any] = {
        "status": "missing",
        "passed": False,
        "gates": {},
        "caveat": (
            "A frozen pre-2006 Nasdaq-100 proxy snapshot is required; the proxy is a price "
            "index and its derived zero-return cash sleeve is not the same instrument as QQQ/SHY."
        ),
    }
    if proxy_panel is not None:
        proxy = _proxy_panel_with_cash(proxy_panel)
        proxy_target = trend_confirmed_volatility_guard_targets(
            proxy.close,
            growth="^NDX",
            defensive="CASH",
            target_volatility=TREND_CONFIRMED_TARGET,
            volatility_window=TREND_CONFIRMED_VOL_WINDOW,
            momentum_window=TREND_CONFIRMED_MOMENTUM_WINDOW,
            confirmation_months=TREND_CONFIRMED_MONTHS,
        )
        proxy_strategy = run_backtest(
            proxy,
            proxy_target,
            name="v3 pre-2006 Nasdaq-100 proxy",
            cost_bps=cost_bps,
            start=proxy_start,
        )
        proxy_benchmark_target = buy_and_hold_targets(
            proxy.close, "^NDX", signal_on=proxy_start
        )
        proxy_benchmark = run_backtest(
            proxy,
            proxy_benchmark_target,
            name="Nasdaq-100 price index buy-and-hold",
            cost_bps=cost_bps,
            start=proxy_start,
        )
        proxy_cost_50 = run_backtest(
            proxy,
            proxy_target,
            name="v3 proxy cost 50",
            cost_bps=50.0,
            start=proxy_start,
        )
        proxy_benchmark_cost_50 = run_backtest(
            proxy,
            proxy_benchmark_target,
            name="proxy benchmark cost 50",
            cost_bps=50.0,
            start=proxy_start,
        )
        proxy_rolling = _rolling_outperformance(proxy_strategy, proxy_benchmark)
        proxy_nw = newey_west_mean_test(
            proxy_strategy.returns - proxy_benchmark.returns
        )
        proxy_midpoint = pd.Timestamp(proxy_start) + pd.DateOffset(years=10)
        proxy_first_difference = (
            _metrics_for_slice(
                proxy_strategy,
                proxy_start,
                (proxy_midpoint - pd.Timedelta(days=1)).strftime("%Y-%m-%d"),
            )["cagr"]
            - _metrics_for_slice(
                proxy_benchmark,
                proxy_start,
                (proxy_midpoint - pd.Timedelta(days=1)).strftime("%Y-%m-%d"),
            )["cagr"]
        )
        proxy_second_difference = (
            _metrics_for_slice(
                proxy_strategy, proxy_midpoint.strftime("%Y-%m-%d"), "2099-12-31"
            )["cagr"]
            - _metrics_for_slice(
                proxy_benchmark, proxy_midpoint.strftime("%Y-%m-%d"), "2099-12-31"
            )["cagr"]
        )
        proxy_gates = {
            "full_cagr_above_ndx": bool(
                proxy_strategy.metrics["cagr"] > proxy_benchmark.metrics["cagr"]
            ),
            "sharpe_above_ndx": bool(
                proxy_strategy.metrics["sharpe"] > proxy_benchmark.metrics["sharpe"]
            ),
            "drawdown_improvement_at_least_10pp": bool(
                proxy_strategy.metrics["max_drawdown"]
                >= proxy_benchmark.metrics["max_drawdown"] + 0.10
            ),
            "rolling_five_year_win_rate_at_least_60pct": bool(
                proxy_rolling["summary"].get("cagr_win_fraction", 0.0) >= 0.60
            ),
            "still_beats_ndx_at_50bps": bool(
                proxy_cost_50.metrics["cagr"] > proxy_benchmark_cost_50.metrics["cagr"]
            ),
            "positive_average_daily_active_return": bool(proxy_nw["annualized"] > 0.0),
        }
        proxy_validation = {
            "status": "completed",
            "passed": all(proxy_gates.values()),
            "period": {
                "start": proxy_start,
                "end": proxy.end.strftime("%Y-%m-%d"),
                "instrument": "^NDX Nasdaq-100 price index",
                "defensive_proxy": "derived zero-return CASH",
            },
            "strategy_metrics": proxy_strategy.metrics,
            "benchmark_metrics": proxy_benchmark.metrics,
            "cagr_difference_vs_ndx": (
                proxy_strategy.metrics["cagr"] - proxy_benchmark.metrics["cagr"]
            ),
            "drawdown_improvement_vs_ndx": (
                proxy_strategy.metrics["max_drawdown"]
                - proxy_benchmark.metrics["max_drawdown"]
            ),
            "rolling_five_year": proxy_rolling,
            "active_return_newey_west": proxy_nw,
            "ten_year_cagr_differences": {
                "first": proxy_first_difference,
                "second": proxy_second_difference,
            },
            "cost_50bps_cagr_difference_vs_ndx": (
                proxy_cost_50.metrics["cagr"]
                - proxy_benchmark_cost_50.metrics["cagr"]
            ),
            "gates": proxy_gates,
            "caveat": (
                "This is an older disjoint market proxy, not a QQQ total-return backfill. "
                "Its first ten-year half did not beat buy-and-hold and is retained as a "
                "negative subperiod result."
            ),
        }

    exposure_gates = {
        "full_cagr_above_matched_96_4": bool(
            strategy.metrics["cagr"] > matched.metrics["cagr"]
        ),
        "sharpe_above_matched_96_4": bool(
            strategy.metrics["sharpe"] > matched.metrics["sharpe"]
        ),
        "drawdown_improvement_at_least_10pp_vs_matched_96_4": bool(
            strategy.metrics["max_drawdown"] >= matched.metrics["max_drawdown"] + 0.10
        ),
        "both_ten_year_halves_beat_matched_96_4": bool(
            halves["first"]["cagr_difference_vs_matched_96_4"] > 0.0
            and halves["second"]["cagr_difference_vs_matched_96_4"] > 0.0
        ),
        "rolling_five_year_win_rate_vs_matched_at_least_75pct": bool(
            rolling_vs_matched["summary"].get("cagr_win_fraction", 0.0) >= 0.75
        ),
        "still_beats_matched_96_4_at_25bps": bool(
            next(
                row["cagr_difference_vs_matched_96_4"]
                for row in costs
                if row["cost_bps"] == 25.0
            )
            > 0.0
        ),
        "positive_average_daily_active_return_vs_matched_96_4": bool(
            matched_nw["annualized"] > 0.0
        ),
    }
    historical_gates = {
        "full_cagr_above_qqq": bool(strategy.metrics["cagr"] > qqq.metrics["cagr"]),
        "sharpe_above_qqq": bool(strategy.metrics["sharpe"] > qqq.metrics["sharpe"]),
        "drawdown_improvement_at_least_15pp_vs_qqq": bool(
            strategy.metrics["max_drawdown"] >= qqq.metrics["max_drawdown"] + 0.15
        ),
        "both_ten_year_halves_beat_qqq": bool(
            halves["first"]["cagr_difference_vs_qqq"] > 0.0
            and halves["second"]["cagr_difference_vs_qqq"] > 0.0
        ),
        "still_beats_qqq_at_25bps": bool(
            next(
                row["cagr_difference_vs_qqq"]
                for row in costs
                if row["cost_bps"] == 25.0
            )
            > 0.0
        ),
        "positive_average_daily_active_return_vs_qqq": bool(
            active_nw["annualized"] > 0.0
        ),
        "confirmation_neighborhood_all_beats_qqq": bool(
            all(row["cagr_difference_vs_qqq"] > 0.0 for row in family_rows)
        ),
        "confirmation_neighborhood_all_improves_drawdown_10pp": bool(
            all(row["drawdown_improvement_vs_qqq"] >= 0.10 for row in family_rows)
        ),
        "confirmation_neighborhood_all_beats_qqq_at_25bps": bool(
            all(row["cost_25bps_cagr_difference_vs_qqq"] > 0.0 for row in family_rows)
        ),
    }
    exposure_pass = all(exposure_gates.values())
    historical_pass = all(historical_gates.values())
    proxy_pass = bool(proxy_validation["passed"])
    statistically_confirmed = bool(
        active_nw["t_stat"] >= 1.96 and active_dsr["probability"] >= 0.95
    )
    reference_candidate = bool(historical_pass and exposure_pass and proxy_pass)

    fixed_start = "2012-01-01"
    fixed_strategy = run_backtest(
        panel, target, name="v3 fixed policy 2012-present", cost_bps=cost_bps, start=fixed_start
    )
    fixed_spy = run_backtest(
        panel,
        buy_and_hold_targets(panel.close, "SPY", signal_on=fixed_start),
        name="SPY 2012-present",
        cost_bps=cost_bps,
        start=fixed_start,
    )
    fixed_policy = {
        "start": fixed_start,
        "strategy_metrics": fixed_strategy.metrics,
        "spy_metrics": fixed_spy.metrics,
        "cagr_difference_vs_spy": fixed_strategy.metrics["cagr"] - fixed_spy.metrics["cagr"],
        "active_return_newey_west": newey_west_mean_test(
            fixed_strategy.returns - fixed_spy.returns
        ),
        "caveat": "The v3 rule was selected after broader research; this is not pristine OOS evidence.",
    }

    return strategy, target, {
        "strategy_name": TREND_CONFIRMED_GUARD_NAME,
        "strategy_version": 3,
        "status": (
            "historical_and_proxy_candidate_pending_live"
            if reference_candidate and not statistically_confirmed
            else "historically_and_statistically_confirmed_pending_live"
            if reference_candidate
            else "v3_research_gate_failed"
        ),
        "historical_gate_passed": historical_pass,
        "exposure_control_passed": exposure_pass,
        "proxy_validation_passed": proxy_pass,
        "reference_trade_candidate": reference_candidate,
        "statistically_confirmed": statistically_confirmed,
        "live_confirmed": False,
        "promotion_ready": False,
        "frozen_parameters": {
            "growth_asset": "QQQ",
            "defensive_asset": "SHY",
            "positive_regime_qqq_weight": 1.0,
            "target_annualized_volatility_in_defensive_regime": TREND_CONFIRMED_TARGET,
            "realized_volatility_window_sessions": TREND_CONFIRMED_VOL_WINDOW,
            "momentum_window_sessions": TREND_CONFIRMED_MOMENTUM_WINDOW,
            "confirmation_months": TREND_CONFIRMED_MONTHS,
            "confirmation_family_retained": list(TREND_CONFIRMED_FAMILY),
            "maximum_qqq_weight": 1.0,
            "leverage_allowed": False,
            "selection_rule": (
                "Two months is the middle of the retained 1/2/3 confirmation family. The "
                "candidate was discovered after exploratory work, so 6,100 trials are charged "
                "to DSR and the result is not described as pre-registered."
            ),
            "execution": "month-end close signal; next-session adjusted open",
            "cost_bps": cost_bps,
        },
        "strategy_metrics": strategy.metrics,
        "spy_metrics": spy.metrics,
        "qqq_metrics": qqq.metrics,
        "passive_90_10_metrics": passive_90_10.metrics,
        "matched_96_4_metrics": matched.metrics,
        "cagr_difference_vs_spy": strategy.metrics["cagr"] - spy.metrics["cagr"],
        "drawdown_improvement_vs_spy": (
            strategy.metrics["max_drawdown"] - spy.metrics["max_drawdown"]
        ),
        "cagr_difference_vs_qqq": strategy.metrics["cagr"] - qqq.metrics["cagr"],
        "drawdown_improvement_vs_qqq": (
            strategy.metrics["max_drawdown"] - qqq.metrics["max_drawdown"]
        ),
        "cagr_difference_vs_passive_90_10": (
            strategy.metrics["cagr"] - passive_90_10.metrics["cagr"]
        ),
        "drawdown_improvement_vs_passive_90_10": (
            strategy.metrics["max_drawdown"] - passive_90_10.metrics["max_drawdown"]
        ),
        "cagr_difference_vs_matched_96_4": (
            strategy.metrics["cagr"] - matched.metrics["cagr"]
        ),
        "drawdown_improvement_vs_matched_96_4": (
            strategy.metrics["max_drawdown"] - matched.metrics["max_drawdown"]
        ),
        "active_return_newey_west": active_nw,
        "active_probabilistic_sharpe": active_psr,
        "active_deflated_sharpe": active_dsr,
        "exposure_control_newey_west": matched_nw,
        "exposure_control_probabilistic_sharpe": probabilistic_sharpe_ratio(
            active_vs_matched, benchmark_sharpe=0.0
        ),
        "exposure_control_deflated_sharpe": deflated_sharpe_ratio(
            active_vs_matched, trials=V3_GLOBAL_SEARCH_TRIALS
        ),
        "local_family_pbo": pbo,
        "historical_gates": historical_gates,
        "exposure_control_gates": exposure_gates,
        "proxy_validation": proxy_validation,
        "ten_year_halves": halves,
        "rolling_five_year": rolling_vs_spy,
        "rolling_five_year_vs_qqq": rolling_vs_qqq,
        "rolling_five_year_vs_matched_96_4": rolling_vs_matched,
        "rolling_five_year_vs_passive_90_10": rolling_vs_passive,
        "cost_sensitivity": costs,
        "fixed_policy_2012": fixed_policy,
        "family": family_rows,
        "exposure_statistics": {
            "mean_qqq_weight": float(target["QQQ"].dropna().mean()),
            "median_qqq_weight": float(target["QQQ"].dropna().median()),
            "minimum_qqq_weight": float(target["QQQ"].dropna().min()),
            "full_qqq_fraction": float((target["QQQ"].dropna() >= 1.0 - 1e-12).mean()),
        },
        "current_target": {
            str(ticker): float(weight) for ticker, weight in strategy.current_target.items()
        },
        "plain_language": {
            "what_it_does": (
                "Stays fully in QQQ while the 12-month trend is confirmed positive. After two "
                "consecutive negative month-end readings, it reduces QQQ only when recent "
                "volatility is high and holds the remainder in SHY."
            ),
            "what_is_proven": (
                "Beat QQQ over the frozen 2006-2026 window after costs, improved drawdown, and "
                "also beat an older disjoint Nasdaq-100 price-index proxy over 1986-2006."
            ),
            "what_is_not_proven": (
                "The active-return t statistic and search-adjusted DSR are not significant; "
                "the older proxy's first ten-year half lost to buy-and-hold, and LIVE paper has "
                "not accumulated forward sessions."
            ),
        },
    }
