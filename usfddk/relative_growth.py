from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from usfddk.data import panel_fingerprint
from usfddk.engine import run_backtest
from usfddk.metrics import compute_metrics, newey_west_mean_test
from usfddk.models import BacktestResult, MarketPanel
from usfddk.strategies import (
    buy_and_hold_targets,
    fixed_weight_targets,
    relative_growth_matched_targets,
    relative_growth_satellite_targets,
)
from usfddk.validation import deflated_sharpe_ratio, probabilistic_sharpe_ratio

V7_PROTOCOL_SHA256 = "2836a94c10973a498b59f33d1812984f5a32b5f1682b63add31e40a293d8ccac"
V7_GLOBAL_SEARCH_TRIALS = 6_104
V7_MAIN_PANEL_SHA256 = "6a7ca6b83b1570007424daa46b0ff4e8fb4a655d39298a0f4f6d74c3b7ea3a66"
V7_MAIN_ARCHIVE_SHA256 = "d480fb82e712f06aabe0a98461e222344656b87022b8bda2cd7ccaa4c29ae88b"
V7_NDX_PANEL_SHA256 = "4814654a4abb4ea5ef0eb52763e233e13bc7088d51ca506eb94c7e335f5f4faa"
V7_NDX_ARCHIVE_SHA256 = "ede88d5906411182e454d2e43442e7b5af61c392eab75e4235d5f22d3112f78d"
V7_GSPC_PANEL_SHA256 = "fbe6b7403574d3296f371ed77c9831cca605b45a5dc5d2a0becfc02ec22f9e2f"
V7_GSPC_ARCHIVE_SHA256 = "2406c622d7b4c85666512ef84b3853b8729c5fe6b4e50256270f60a6273ecacd"
V7_MAIN_START = "2006-07-31"
V7_MAIN_END = "2026-07-31"
V7_PROXY_START = "1989-01-03"
V7_PROXY_END = "2006-07-28"


def _validate_snapshot(
    panel: MarketPanel,
    receipt: dict[str, Any],
    *,
    label: str,
    required_tickers: tuple[str, ...],
    expected_panel_sha256: str,
    expected_archive_sha256: str,
    expected_start: str,
    expected_end: str,
    exact_tickers: bool,
) -> None:
    tickers = set(panel.tickers)
    required = set(required_tickers)
    if not required.issubset(tickers) or (exact_tickers and tickers != required):
        raise ValueError(f"{label}代號與 v7 凍結協議不同")
    if panel.start != pd.Timestamp(expected_start) or panel.end != pd.Timestamp(expected_end):
        raise ValueError(f"{label}期間與 v7 凍結協議不同")
    actual = panel_fingerprint(panel)
    if actual != expected_panel_sha256:
        raise ValueError(f"{label}面板不是 v7 協議指定內容")
    if receipt.get("panel_sha256") != expected_panel_sha256:
        raise ValueError(f"{label}收據面板雜湊與 v7 協議不同")
    if receipt.get("archive_sha256") != expected_archive_sha256:
        raise ValueError(f"{label}封存檔雜湊與 v7 協議不同")


def build_v7_proxy_panel(ndx: MarketPanel, gspc: MarketPanel) -> MarketPanel:
    """Join the two frozen price-index snapshots and add zero-return cash."""
    common = ndx.close.index.intersection(gspc.close.index)
    if not len(common) or common[0] != pd.Timestamp("1987-01-02"):
        raise ValueError("v7 舊代理共同交易日起點與凍結協議不同")
    if common[-1] != pd.Timestamp(V7_PROXY_END):
        raise ValueError("v7 舊代理共同交易日終點與凍結協議不同")
    frames: dict[str, pd.DataFrame] = {}
    for field in ("Open", "High", "Low", "Close", "Volume"):
        left = ndx.field_map()[field].loc[common, ["^NDX"]]
        right = gspc.field_map()[field].loc[common, ["^GSPC"]]
        frame = pd.concat([right, left], axis=1)
        frame["CASH"] = 0.0 if field == "Volume" else 1.0
        if frame[["^GSPC", "^NDX"]].isna().any().any():
            raise ValueError(f"v7 舊代理共同交易日仍含缺值：{field}")
        frames[field] = frame
    return MarketPanel(
        open=frames["Open"],
        high=frames["High"],
        low=frames["Low"],
        close=frames["Close"],
        volume=frames["Volume"],
        metadata={
            "derived_from": [ndx.metadata.get("snapshot"), gspc.metadata.get("snapshot")],
            "translation": "QQQ->^NDX; SPY->^GSPC; SHY->constant CASH",
            "cash_proxy": "constant 1.0; zero return; no interest",
        },
    )


def _slice_metrics(
    result: BacktestResult, start: str, end: str
) -> dict[str, float]:
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
        "drawdown_improvement": (
            strategy.metrics["max_drawdown"] - benchmark.metrics["max_drawdown"]
        ),
        "calmar_difference": strategy.metrics["calmar"] - benchmark.metrics["calmar"],
        "active_return_newey_west": newey_west_mean_test(active, max_lag=9),
        "active_probabilistic_sharpe": probabilistic_sharpe_ratio(
            active, benchmark_sharpe=0.0
        ),
        "active_global_deflated_sharpe_disclosure": deflated_sharpe_ratio(
            active, trials=V7_GLOBAL_SEARCH_TRIALS
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
    market: BacktestResult,
    matched: BacktestResult,
    periods: tuple[tuple[str, str, str], ...],
) -> dict[str, Any]:
    rows: dict[str, Any] = {}
    for label, start, end in periods:
        strategy_metrics = _slice_metrics(strategy, start, end)
        market_metrics = _slice_metrics(market, start, end)
        matched_metrics = _slice_metrics(matched, start, end)
        rows[label] = {
            "start": start,
            "end": end,
            "strategy_metrics": strategy_metrics,
            "market_metrics": market_metrics,
            "matched_metrics": matched_metrics,
            "cagr_difference_vs_market": (
                strategy_metrics["cagr"] - market_metrics["cagr"]
            ),
            "cagr_difference_vs_matched": (
                strategy_metrics["cagr"] - matched_metrics["cagr"]
            ),
        }
    return rows


def _first_entry_signal(target: pd.DataFrame, panel: MarketPanel, start: str) -> str:
    signals = target.dropna(how="all").index
    start_stamp = pd.Timestamp(start)
    for signal in signals:
        position = panel.close.index.get_loc(signal)
        if isinstance(position, int) and position + 1 < len(panel.close.index):
            if panel.close.index[position + 1] >= start_stamp:
                return pd.Timestamp(signal).strftime("%Y-%m-%d")
    raise ValueError("v7 找不到正式期第一個可執行訊號")


def _dataset_results(
    panel: MarketPanel,
    *,
    core: str,
    growth: str,
    defensive: str,
    start: str,
    end: str,
    half_periods: tuple[tuple[str, str, str], ...],
    label: str,
    primary_cost_bps: float,
    stress_cost_bps: float,
) -> tuple[BacktestResult, pd.DataFrame, dict[str, Any]]:
    target = relative_growth_satellite_targets(
        panel.close, core=core, growth=growth, defensive=defensive
    )
    matched_target = relative_growth_matched_targets(
        target, core=core, growth=growth, defensive=defensive
    )
    entry_signal = _first_entry_signal(target, panel, start)
    market_target = buy_and_hold_targets(panel.close, core, signal_on=entry_signal)
    opportunity_target = buy_and_hold_targets(panel.close, growth, signal_on=entry_signal)
    passive_target = fixed_weight_targets(
        panel.close, {core: 0.50, growth: 0.50}, signal_on=entry_signal
    )

    def run(signals: pd.DataFrame, name: str, cost: float) -> BacktestResult:
        return run_backtest(
            panel, signals, name=f"{label}{name}", cost_bps=cost, start=start
        )

    strategy = run(target, "相對成長衛星", primary_cost_bps)
    market = run(market_target, "市場", primary_cost_bps)
    matched = run(matched_target, "matched", primary_cost_bps)
    opportunity = run(opportunity_target, "成長機會成本", primary_cost_bps)
    passive = run(passive_target, "固定 50/50", primary_cost_bps)
    strategy_50 = run(target, "相對成長衛星 50bps", stress_cost_bps)
    market_50 = run(market_target, "市場 50bps", stress_cost_bps)
    matched_50 = run(matched_target, "matched 50bps", stress_cost_bps)

    versus_market = _comparison(strategy, market)
    versus_matched = _comparison(strategy, matched)
    rolling_market = _rolling_comparison(strategy, market)
    rolling_matched = _rolling_comparison(strategy, matched)
    half_rows = _halves(strategy, market, matched, half_periods)
    signal_rows = target.dropna(how="all")
    risk_on = signal_rows[growth] > 0.0
    data = {
        "period": {
            "start": start,
            "end": end,
            "sessions": int(len(strategy.equity)),
            "entry_signal": entry_signal,
        },
        "strategy_metrics": strategy.metrics,
        "benchmark_metrics": {
            "market": market.metrics,
            "matched": matched.metrics,
            "opportunity": opportunity.metrics,
            "fixed_50_50": passive.metrics,
        },
        "comparisons": {"market": versus_market, "matched": versus_matched},
        "cost_50bps": {
            "strategy_metrics": strategy_50.metrics,
            "market_metrics": market_50.metrics,
            "matched_metrics": matched_50.metrics,
            "cagr_difference_vs_market": (
                strategy_50.metrics["cagr"] - market_50.metrics["cagr"]
            ),
            "cagr_difference_vs_matched": (
                strategy_50.metrics["cagr"] - matched_50.metrics["cagr"]
            ),
        },
        "fixed_halves": half_rows,
        "rolling_five_year": {
            "market": rolling_market,
            "matched": rolling_matched,
        },
        "signals": {
            "completed_month_ends": int(len(signal_rows)),
            "risk_on_count": int(risk_on.sum()),
            "risk_off_count": int((~risk_on).sum()),
            "risk_on_fraction": float(risk_on.mean()),
        },
        "current_target": {
            str(ticker): float(weight)
            for ticker, weight in strategy.current_target.items()
            if weight > 0.0
        },
    }
    return strategy, target, data


def _point_gates(data: dict[str, Any], prefix: str) -> dict[str, bool]:
    strategy = data["strategy_metrics"]
    market = data["benchmark_metrics"]["market"]
    matched = data["benchmark_metrics"]["matched"]
    comparisons = data["comparisons"]
    stress = data["cost_50bps"]
    rolling_market = data["rolling_five_year"]["market"]["summary"]
    rolling_matched = data["rolling_five_year"]["matched"]["summary"]
    halves = data["fixed_halves"].values()
    return {
        f"{prefix}_cagr_beats_market_and_matched_10bp": bool(
            strategy["cagr"] > market["cagr"] + 0.001
            and strategy["cagr"] > matched["cagr"] + 0.001
        ),
        f"{prefix}_sharpe_beats_market_and_matched": bool(
            strategy["sharpe"] > market["sharpe"]
            and strategy["sharpe"] > matched["sharpe"]
        ),
        f"{prefix}_drawdown_improves_market_5pp_and_not_worse_matched": bool(
            strategy["max_drawdown"] >= market["max_drawdown"] + 0.05
            and strategy["max_drawdown"] >= matched["max_drawdown"]
        ),
        f"{prefix}_calmar_beats_market_and_matched": bool(
            strategy["calmar"] > market["calmar"]
            and strategy["calmar"] > matched["calmar"]
        ),
        f"{prefix}_50bps_cagr_beats_both_10bp": bool(
            stress["cagr_difference_vs_market"] > 0.001
            and stress["cagr_difference_vs_matched"] > 0.001
        ),
        f"{prefix}_both_halves_cagr_beat_both_10bp": all(
            half["cagr_difference_vs_market"] > 0.001
            and half["cagr_difference_vs_matched"] > 0.001
            for half in halves
        ),
        f"{prefix}_rolling_wins_60pct_and_positive_medians": bool(
            rolling_market.get("cagr_win_fraction", 0.0) >= 0.60
            and rolling_matched.get("cagr_win_fraction", 0.0) >= 0.60
            and rolling_market.get("median_cagr_difference", -1.0) > 0.0
            and rolling_matched.get("median_cagr_difference", -1.0) > 0.0
        ),
        f"{prefix}_newey_west_t_at_least_1_96_vs_both": bool(
            comparisons["market"]["active_return_newey_west"]["t_stat"] >= 1.96
            and comparisons["matched"]["active_return_newey_west"]["t_stat"] >= 1.96
        ),
        f"{prefix}_psr_probability_95pct_vs_both": bool(
            comparisons["market"]["active_probabilistic_sharpe"]["probability"] >= 0.95
            and comparisons["matched"]["active_probabilistic_sharpe"]["probability"] >= 0.95
        ),
    }


def evaluate_relative_growth_research(
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
    """Evaluate the frozen v7 rule once, without parameter search or rescue."""
    if protocol_sha256 != V7_PROTOCOL_SHA256:
        raise ValueError("v7 協議雜湊與第一次計算前凍結版本不同")
    _validate_snapshot(
        main_panel,
        main_receipt,
        label="v7 主樣本",
        required_tickers=("SPY", "QQQ", "SHY"),
        expected_panel_sha256=V7_MAIN_PANEL_SHA256,
        expected_archive_sha256=V7_MAIN_ARCHIVE_SHA256,
        expected_start="2004-01-02",
        expected_end=V7_MAIN_END,
        exact_tickers=False,
    )
    _validate_snapshot(
        ndx_panel,
        ndx_receipt,
        label="v7 Nasdaq-100 代理",
        required_tickers=("^NDX",),
        expected_panel_sha256=V7_NDX_PANEL_SHA256,
        expected_archive_sha256=V7_NDX_ARCHIVE_SHA256,
        expected_start="1985-10-01",
        expected_end=V7_PROXY_END,
        exact_tickers=True,
    )
    _validate_snapshot(
        gspc_panel,
        gspc_receipt,
        label="v7 S&P 500 代理",
        required_tickers=("^GSPC",),
        expected_panel_sha256=V7_GSPC_PANEL_SHA256,
        expected_archive_sha256=V7_GSPC_ARCHIVE_SHA256,
        expected_start="1987-01-02",
        expected_end=V7_PROXY_END,
        exact_tickers=True,
    )

    strategy, target, main = _dataset_results(
        main_panel,
        core="SPY",
        growth="QQQ",
        defensive="SHY",
        start=V7_MAIN_START,
        end=V7_MAIN_END,
        half_periods=(
            ("first", "2006-07-31", "2016-07-29"),
            ("second", "2016-08-01", "2026-07-31"),
        ),
        label="v7 ETF ",
        primary_cost_bps=primary_cost_bps,
        stress_cost_bps=stress_cost_bps,
    )
    proxy_panel = build_v7_proxy_panel(ndx_panel, gspc_panel)
    _, _, proxy = _dataset_results(
        proxy_panel,
        core="^GSPC",
        growth="^NDX",
        defensive="CASH",
        start=V7_PROXY_START,
        end=V7_PROXY_END,
        half_periods=(
            ("first", "1989-01-03", "1997-09-30"),
            ("second", "1997-10-01", "2006-07-28"),
        ),
        label="v7 舊代理 ",
        primary_cost_bps=primary_cost_bps,
        stress_cost_bps=stress_cost_bps,
    )

    main_gates = _point_gates(main, "main")
    weight_sums = strategy.weights.sum(axis=1)
    main_gates["main_weights_fully_invested_95pct_no_leverage_or_short"] = bool(
        np.isclose(weight_sums, 1.0, atol=1e-8).mean() >= 0.95
        and float(weight_sums.max()) <= 1.0 + 1e-8
        and float(strategy.weights.min().min()) >= -1e-12
    )
    main_order = [
        "main_cagr_beats_market_and_matched_10bp",
        "main_sharpe_beats_market_and_matched",
        "main_drawdown_improves_market_5pp_and_not_worse_matched",
        "main_calmar_beats_market_and_matched",
        "main_50bps_cagr_beats_both_10bp",
        "main_both_halves_cagr_beat_both_10bp",
        "main_rolling_wins_60pct_and_positive_medians",
        "main_newey_west_t_at_least_1_96_vs_both",
        "main_psr_probability_95pct_vs_both",
        "main_weights_fully_invested_95pct_no_leverage_or_short",
    ]
    proxy_gates = _point_gates(proxy, "proxy")
    proxy_order = [
        "proxy_cagr_beats_market_and_matched_10bp",
        "proxy_sharpe_beats_market_and_matched",
        "proxy_drawdown_improves_market_5pp_and_not_worse_matched",
        "proxy_calmar_beats_market_and_matched",
        "proxy_50bps_cagr_beats_both_10bp",
        "proxy_both_halves_cagr_beat_both_10bp",
        "proxy_rolling_wins_60pct_and_positive_medians",
        "proxy_newey_west_t_at_least_1_96_vs_both",
        "proxy_psr_probability_95pct_vs_both",
    ]
    gates = {
        f"{number:02d}_{key}": bool((main_gates | proxy_gates)[key])
        for number, key in enumerate([*main_order, *proxy_order], start=1)
    }
    passed = sum(gates.values())
    historical_passed = passed == 19
    audit: dict[str, Any] = {
        "schema_version": 1,
        "strategy_name": "v7 相對強弱成長衛星",
        "status": "historical_passed_pending_live" if historical_passed else "historical_failed",
        "historical_gate_passed": historical_passed,
        "paper_eligible": historical_passed,
        "reference_trade_candidate": False,
        "promotion_effect": "create_isolated_paper_only" if historical_passed else "none",
        "protocol": {
            "path": "docs/V7_RELATIVE_GROWTH_PROTOCOL.md",
            "sha256": protocol_sha256,
            "frozen_before_first_v7_calculation": True,
            "data_independent": False,
            "global_search_trials_disclosure": V7_GLOBAL_SEARCH_TRIALS,
        },
        "parameters": {
            "permanent_core_weight": 0.50,
            "growth_or_defensive_slot_weight": 0.50,
            "momentum": "close(t-21) / close(t-252) - 1",
            "growth_trend_sma_sessions": 200,
            "rebalance": "completed month-end close; next adjusted open",
            "primary_cost_bps": primary_cost_bps,
            "stress_cost_bps": stress_cost_bps,
            "leverage": False,
            "parameter_search": False,
        },
        "data_receipts": {
            "main": main_receipt,
            "ndx": ndx_receipt,
            "gspc": gspc_receipt,
            "proxy_translation": "QQQ->^NDX; SPY->^GSPC; SHY->CASH at zero return",
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
        "passed_gate_count": int(passed),
        "required_gate_count": 19,
        "forward_requirements_if_historical_passes": {
            "new_sessions": 252,
            "completed_rebalances": 6,
            "after_cost_return_positive": True,
            "must_beat": ["SPY", "synchronous_matched_control"],
            "drawdown_not_worse_than_both": True,
            "historical_trades_may_be_backfilled": False,
        },
        "interpretation": {
            "policy_question": (
                "Whether a permanent broad-market core plus a monthly relative-growth switch "
                "is a useful exposure policy."
            ),
            "alpha_question": (
                "Whether choosing QQQ instead of SPY during risk-on months adds repeatable net "
                "return beyond the same monthly equity exposure."
            ),
            "decision": (
                "Historical gates passed; only an isolated forward paper account may begin."
                if historical_passed
                else "At least one frozen gate failed; retain as research and do not open Paper."
            ),
        },
    }
    return strategy, target, audit
