from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from usfddk.engine import run_backtest
from usfddk.metrics import compute_metrics, newey_west_mean_test
from usfddk.models import BacktestResult, MarketPanel
from usfddk.relative_growth import (
    V7_GSPC_ARCHIVE_SHA256,
    V7_GSPC_PANEL_SHA256,
    V7_MAIN_ARCHIVE_SHA256,
    V7_MAIN_PANEL_SHA256,
    V7_NDX_ARCHIVE_SHA256,
    V7_NDX_PANEL_SHA256,
    V7_PROXY_END,
    _validate_snapshot,
    build_v7_proxy_panel,
)
from usfddk.strategies import (
    always_invested_relative_growth_targets,
    buy_and_hold_targets,
    fixed_weight_targets,
)
from usfddk.validation import deflated_sharpe_ratio, probabilistic_sharpe_ratio

V8_PROTOCOL_SHA256 = "2d21d2b81ad9285839a7036085231b6c670bbf63559179a144d6e6a8ddc9769c"
V8_GLOBAL_SEARCH_TRIALS = 6_105
V8_MAIN_START = "2006-07-31"
V8_MAIN_END = "2026-07-31"
V8_PROXY_START = "1989-01-03"
V8_PROXY_END = V7_PROXY_END


def _slice_metrics(result: BacktestResult, start: str, end: str) -> dict[str, float]:
    dates = result.equity.loc[start:end].index
    return compute_metrics(
        result.equity.loc[dates], result.returns.loc[dates], result.turnover.loc[dates]
    )


def _comparison(strategy: BacktestResult, benchmark: BacktestResult) -> dict[str, Any]:
    aligned = pd.concat(
        [strategy.returns.rename("strategy"), benchmark.returns.rename("benchmark")], axis=1
    ).dropna()
    active = aligned["strategy"] - aligned["benchmark"]
    return {
        "cagr_difference": strategy.metrics["cagr"] - benchmark.metrics["cagr"],
        "sharpe_difference": strategy.metrics["sharpe"] - benchmark.metrics["sharpe"],
        "drawdown_difference": (
            strategy.metrics["max_drawdown"] - benchmark.metrics["max_drawdown"]
        ),
        "calmar_difference": strategy.metrics["calmar"] - benchmark.metrics["calmar"],
        "active_return_newey_west": newey_west_mean_test(active, max_lag=9),
        "active_probabilistic_sharpe": probabilistic_sharpe_ratio(
            active, benchmark_sharpe=0.0
        ),
        "active_global_deflated_sharpe": deflated_sharpe_ratio(
            active, trials=V8_GLOBAL_SEARCH_TRIALS
        ),
    }


def _rolling_comparison(
    strategy: BacktestResult, benchmark: BacktestResult, *, window: int = 1_260
) -> dict[str, Any]:
    common = strategy.equity.index.intersection(benchmark.equity.index)
    periods = pd.Series(common.to_period("M"), index=common)
    endpoints = common[periods.ne(periods.shift(-1)).to_numpy()]
    rows: list[dict[str, float | str]] = []
    for end in endpoints:
        position = common.get_loc(end)
        if not isinstance(position, int) or position < window:
            continue
        dates = common[position - window : position + 1]
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
                "cagr_difference": (
                    strategy_metrics["cagr"] - benchmark_metrics["cagr"]
                ),
            }
        )
    if not rows:
        return {"window_sessions": window, "series": [], "summary": {}}
    differences = pd.Series([float(row["cagr_difference"]) for row in rows])
    return {
        "window_sessions": window,
        "series": rows,
        "summary": {
            "windows": int(len(rows)),
            "minimum_cagr_edge": 0.001,
            "cagr_win_fraction": float((differences > 0.001).mean()),
            "median_cagr_difference": float(differences.median()),
            "worst_cagr_difference": float(differences.min()),
            "latest_cagr_difference": float(differences.iloc[-1]),
        },
    }


def _halves(
    strategy: BacktestResult,
    benchmark: BacktestResult,
    periods: tuple[tuple[str, str, str], ...],
) -> dict[str, Any]:
    rows: dict[str, Any] = {}
    for label, start, end in periods:
        strategy_metrics = _slice_metrics(strategy, start, end)
        benchmark_metrics = _slice_metrics(benchmark, start, end)
        rows[label] = {
            "start": start,
            "end": end,
            "strategy_metrics": strategy_metrics,
            "benchmark_metrics": benchmark_metrics,
            "cagr_difference": (
                strategy_metrics["cagr"] - benchmark_metrics["cagr"]
            ),
        }
    return rows


def _first_entry_signal(target: pd.DataFrame, panel: MarketPanel, start: str) -> str:
    start_stamp = pd.Timestamp(start)
    for signal in target.dropna(how="all").index:
        position = panel.close.index.get_loc(signal)
        if isinstance(position, int) and position + 1 < len(panel.close.index):
            if panel.close.index[position + 1] >= start_stamp:
                return pd.Timestamp(signal).strftime("%Y-%m-%d")
    raise ValueError("v8 找不到正式期第一個可執行訊號")


def _dataset_results(
    panel: MarketPanel,
    *,
    core: str,
    growth: str,
    start: str,
    end: str,
    half_periods: tuple[tuple[str, str, str], ...],
    label: str,
    primary_cost_bps: float,
    stress_cost_bps: float,
) -> tuple[BacktestResult, pd.DataFrame, dict[str, Any]]:
    target = always_invested_relative_growth_targets(
        panel.close, core=core, growth=growth
    )
    entry_signal = _first_entry_signal(target, panel, start)
    market_target = buy_and_hold_targets(panel.close, core, signal_on=entry_signal)
    opportunity_target = buy_and_hold_targets(panel.close, growth, signal_on=entry_signal)
    static_target = fixed_weight_targets(
        panel.close, {core: 0.50, growth: 0.50}, signal_on=entry_signal
    )

    def run(signals: pd.DataFrame, name: str, cost: float) -> BacktestResult:
        return run_backtest(
            panel, signals, name=f"{label}{name}", cost_bps=cost, start=start
        )

    strategy = run(target, "永遠持股相對成長", primary_cost_bps)
    market = run(market_target, "市場", primary_cost_bps)
    opportunity = run(opportunity_target, "成長機會成本", primary_cost_bps)
    static = run(static_target, "固定 50/50", primary_cost_bps)
    strategy_50 = run(target, "永遠持股相對成長 50bps", stress_cost_bps)
    market_50 = run(market_target, "市場 50bps", stress_cost_bps)
    comparison = _comparison(strategy, market)
    rolling = _rolling_comparison(strategy, market)
    half_rows = _halves(strategy, market, half_periods)
    signals = target.dropna(how="all")
    risk_on = signals[growth] > 0.0
    return strategy, target, {
        "period": {
            "start": start,
            "end": end,
            "sessions": int(len(strategy.equity)),
            "entry_signal": entry_signal,
        },
        "strategy_metrics": strategy.metrics,
        "benchmark_metrics": {
            "market": market.metrics,
            "opportunity": opportunity.metrics,
            "fixed_50_50": static.metrics,
        },
        "comparison": comparison,
        "cost_50bps": {
            "strategy_metrics": strategy_50.metrics,
            "market_metrics": market_50.metrics,
            "cagr_difference": (
                strategy_50.metrics["cagr"] - market_50.metrics["cagr"]
            ),
        },
        "fixed_halves": half_rows,
        "rolling_five_year": rolling,
        "signals": {
            "completed_month_ends": int(len(signals)),
            "growth_tilt_count": int(risk_on.sum()),
            "all_spy_count": int((~risk_on).sum()),
            "growth_tilt_fraction": float(risk_on.mean()),
        },
        "current_target": {
            str(ticker): float(weight)
            for ticker, weight in strategy.current_target.items()
            if weight > 0.0
        },
    }


def evaluate_always_invested_research(
    main_panel: MarketPanel,
    ndx_panel: MarketPanel,
    gspc_panel: MarketPanel,
    *,
    main_receipt: dict[str, Any],
    ndx_receipt: dict[str, Any],
    gspc_receipt: dict[str, Any],
    protocol_sha256: str,
    primary_cost_bps: float = 10.0,
    stress_cost_bps: float = 50.0,
) -> tuple[BacktestResult, pd.DataFrame, dict[str, Any]]:
    """Evaluate the frozen v8 policy without tuning after the result."""
    if protocol_sha256 != V8_PROTOCOL_SHA256:
        raise ValueError("v8 協議雜湊與第一次計算前凍結版本不同")
    _validate_snapshot(
        main_panel,
        main_receipt,
        label="v8 主樣本",
        required_tickers=("SPY", "QQQ"),
        expected_panel_sha256=V7_MAIN_PANEL_SHA256,
        expected_archive_sha256=V7_MAIN_ARCHIVE_SHA256,
        expected_start="2004-01-02",
        expected_end=V8_MAIN_END,
        exact_tickers=False,
    )
    _validate_snapshot(
        ndx_panel,
        ndx_receipt,
        label="v8 Nasdaq-100 代理",
        required_tickers=("^NDX",),
        expected_panel_sha256=V7_NDX_PANEL_SHA256,
        expected_archive_sha256=V7_NDX_ARCHIVE_SHA256,
        expected_start="1985-10-01",
        expected_end=V8_PROXY_END,
        exact_tickers=True,
    )
    _validate_snapshot(
        gspc_panel,
        gspc_receipt,
        label="v8 S&P 500 代理",
        required_tickers=("^GSPC",),
        expected_panel_sha256=V7_GSPC_PANEL_SHA256,
        expected_archive_sha256=V7_GSPC_ARCHIVE_SHA256,
        expected_start="1987-01-02",
        expected_end=V8_PROXY_END,
        exact_tickers=True,
    )
    main_warmup = main_panel.close.loc[
        main_panel.close.index < pd.Timestamp(V8_MAIN_START), ["SPY", "QQQ"]
    ].notna().all(axis=1)
    if int(main_warmup.sum()) < 252:
        raise ValueError("v8 主樣本暖機不足 252 個共同有效交易日")

    strategy, target, main = _dataset_results(
        main_panel,
        core="SPY",
        growth="QQQ",
        start=V8_MAIN_START,
        end=V8_MAIN_END,
        half_periods=(
            ("first", "2006-07-31", "2016-07-29"),
            ("second", "2016-08-01", "2026-07-31"),
        ),
        label="v8 ETF ",
        primary_cost_bps=primary_cost_bps,
        stress_cost_bps=stress_cost_bps,
    )
    proxy_panel = build_v7_proxy_panel(ndx_panel, gspc_panel)
    proxy_warmup = proxy_panel.close.loc[
        proxy_panel.close.index < pd.Timestamp(V8_PROXY_START), ["^GSPC", "^NDX"]
    ].notna().all(axis=1)
    if int(proxy_warmup.sum()) < 252:
        raise ValueError("v8 舊代理暖機不足 252 個共同有效交易日")
    _, _, proxy = _dataset_results(
        proxy_panel,
        core="^GSPC",
        growth="^NDX",
        start=V8_PROXY_START,
        end=V8_PROXY_END,
        half_periods=(
            ("first", "1989-01-03", "1997-09-30"),
            ("second", "1997-10-01", "2006-07-28"),
        ),
        label="v8 舊代理 ",
        primary_cost_bps=primary_cost_bps,
        stress_cost_bps=stress_cost_bps,
    )

    main_strategy = main["strategy_metrics"]
    main_market = main["benchmark_metrics"]["market"]
    proxy_strategy = proxy["strategy_metrics"]
    proxy_market = proxy["benchmark_metrics"]["market"]
    weight_sums = strategy.weights.sum(axis=1)
    gates = {
        "01_main_cagr_beats_spy_10bp": bool(
            main_strategy["cagr"] > main_market["cagr"] + 0.001
        ),
        "02_main_sharpe_beats_spy": bool(
            main_strategy["sharpe"] > main_market["sharpe"]
        ),
        "03_main_drawdown_not_worse_than_spy_5pp": bool(
            main_strategy["max_drawdown"] >= main_market["max_drawdown"] - 0.05
        ),
        "04_main_calmar_beats_spy": bool(
            main_strategy["calmar"] > main_market["calmar"]
        ),
        "05_main_50bps_cagr_beats_spy_10bp": bool(
            main["cost_50bps"]["cagr_difference"] > 0.001
        ),
        "06_main_both_halves_cagr_beat_spy_10bp": all(
            half["cagr_difference"] > 0.001
            for half in main["fixed_halves"].values()
        ),
        "07_main_rolling_wins_60pct_and_positive_median": bool(
            main["rolling_five_year"]["summary"].get("cagr_win_fraction", 0.0)
            >= 0.60
            and main["rolling_five_year"]["summary"].get(
                "median_cagr_difference", -1.0
            )
            > 0.0
        ),
        "08_main_newey_west_t_at_least_1_96": bool(
            main["comparison"]["active_return_newey_west"]["t_stat"] >= 1.96
        ),
        "09_main_psr_probability_95pct": bool(
            main["comparison"]["active_probabilistic_sharpe"]["probability"]
            >= 0.95
        ),
        "10_main_weights_fully_invested_95pct_no_leverage_or_short": bool(
            np.isclose(weight_sums, 1.0, atol=1e-8).mean() >= 0.95
            and float(weight_sums.max()) <= 1.0 + 1e-8
            and float(strategy.weights.min().min()) >= -1e-12
        ),
        "11_proxy_cagr_beats_gspc_10bp": bool(
            proxy_strategy["cagr"] > proxy_market["cagr"] + 0.001
        ),
        "12_proxy_sharpe_beats_gspc": bool(
            proxy_strategy["sharpe"] > proxy_market["sharpe"]
        ),
        "13_proxy_drawdown_not_worse_than_gspc_5pp": bool(
            proxy_strategy["max_drawdown"] >= proxy_market["max_drawdown"] - 0.05
        ),
        "14_proxy_calmar_beats_gspc": bool(
            proxy_strategy["calmar"] > proxy_market["calmar"]
        ),
        "15_proxy_50bps_cagr_beats_gspc_10bp": bool(
            proxy["cost_50bps"]["cagr_difference"] > 0.001
        ),
        "16_proxy_both_halves_cagr_beat_gspc_10bp": all(
            half["cagr_difference"] > 0.001
            for half in proxy["fixed_halves"].values()
        ),
        "17_proxy_rolling_wins_60pct_and_positive_median": bool(
            proxy["rolling_five_year"]["summary"].get("cagr_win_fraction", 0.0)
            >= 0.60
            and proxy["rolling_five_year"]["summary"].get(
                "median_cagr_difference", -1.0
            )
            > 0.0
        ),
        "18_proxy_newey_west_t_at_least_1_96": bool(
            proxy["comparison"]["active_return_newey_west"]["t_stat"] >= 1.96
        ),
        "19_proxy_psr_probability_95pct": bool(
            proxy["comparison"]["active_probabilistic_sharpe"]["probability"]
            >= 0.95
        ),
        "20_proxy_data_translation_and_warmup_integrity": True,
    }
    paper_entry_numbers = {1, 2, 3, 4, 5, 6, 7, 10, 11, 12, 13, 14, 15, 16, 17, 20}
    paper_entry_gates = {
        key: passed
        for key, passed in gates.items()
        if int(key[:2]) in paper_entry_numbers
    }
    paper_eligible = all(paper_entry_gates.values())
    historically_confirmed = all(gates.values())
    dsr_sensitivity = {
        "main": main["comparison"]["active_global_deflated_sharpe"],
        "proxy": proxy["comparison"]["active_global_deflated_sharpe"],
    }
    dsr_sensitivity_passed = all(
        float(item["probability"]) >= 0.95 for item in dsr_sensitivity.values()
    )
    audit: dict[str, Any] = {
        "schema_version": 1,
        "strategy_name": "v8 永遠持股相對成長傾斜",
        "status": (
            "historically_confirmed_pending_live"
            if historically_confirmed
            else "paper_entry_passed_statistical_pending"
            if paper_eligible
            else "historical_economic_failed"
        ),
        "paper_eligible": paper_eligible,
        "historically_confirmed": historically_confirmed,
        "promotion_ready": False,
        "reference_trade_candidate": False,
        "promotion_effect": "create_isolated_paper_only" if paper_eligible else "none",
        "protocol": {
            "path": "docs/V8_ALWAYS_INVESTED_PROTOCOL.md",
            "sha256": protocol_sha256,
            "frozen_before_first_v8_calculation": True,
            "data_independent": False,
            "derived_after_v7": True,
            "global_search_trials": V8_GLOBAL_SEARCH_TRIALS,
        },
        "parameters": {
            "permanent_spy_weight": 0.50,
            "conditional_growth_weight": 0.50,
            "risk_off_destination": "SPY",
            "momentum": "close(t-21) / close(t-252) - 1",
            "growth_trend_sma_sessions": 200,
            "equity_exposure": 1.0,
            "primary_cost_bps": primary_cost_bps,
            "stress_cost_bps": stress_cost_bps,
            "leverage": False,
            "parameter_search": False,
        },
        "data_receipts": {
            "main": main_receipt,
            "ndx": ndx_receipt,
            "gspc": gspc_receipt,
            "main_warmup_common_sessions": int(main_warmup.sum()),
            "proxy_warmup_common_sessions": int(proxy_warmup.sum()),
            "proxy_translation": "QQQ->^NDX; SPY->^GSPC; common sessions only",
        },
        "main": main,
        "proxy": proxy,
        "weight_integrity": {
            "fully_invested_fraction": float(
                np.isclose(weight_sums, 1.0, atol=1e-8).mean()
            ),
            "maximum_weight_sum": float(weight_sums.max()),
            "minimum_weight": float(strategy.weights.min().min()),
        },
        "gates": gates,
        "passed_gate_count": int(sum(gates.values())),
        "required_gate_count": 20,
        "paper_entry_gates": paper_entry_gates,
        "paper_entry_passed_gate_count": int(sum(paper_entry_gates.values())),
        "paper_entry_required_gate_count": len(paper_entry_gates),
        "statistical_gates": {
            key: value
            for key, value in gates.items()
            if int(key[:2]) in {8, 9, 18, 19}
        },
        "global_dsr_promotion_sensitivity": {
            "passed": dsr_sensitivity_passed,
            **dsr_sensitivity,
        },
        "forward_requirements": {
            "minimum_new_sessions": 252,
            "minimum_completed_rebalances": 6,
            "after_cost_return_positive": True,
            "must_beat": "same-start SPY",
            "max_drawdown_not_worse_than_spy": True,
            "active_newey_west_t_at_least": 1.96,
            "active_psr_probability_at_least": 0.95,
            "historical_trades_may_be_backfilled": False,
        },
        "interpretation": {
            "policy": "Always 100% equities; tilt half from SPY to QQQ only in relative strength.",
            "paper_decision": (
                "Economic and temporal entry gates passed; only isolated forward Paper may begin."
                if paper_eligible
                else "At least one economic or temporal entry gate failed; do not create Paper."
            ),
            "reference_decision": (
                "Not reference-ready: historical statistics, global selection sensitivity, and "
                "new forward evidence are separate required layers."
            ),
        },
    }
    return strategy, target, audit
