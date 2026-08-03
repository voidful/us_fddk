from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from usfddk.engine import run_backtest
from usfddk.hierarchical_defense import _halves, _rolling_comparison, _slice_result
from usfddk.metrics import newey_west_mean_test
from usfddk.models import BacktestResult, MarketPanel
from usfddk.strategies import (
    buy_and_hold_targets,
    fixed_weight_weekly_targets,
    trend_volatility_brake_targets,
)
from usfddk.validation import deflated_sharpe_ratio, probabilistic_sharpe_ratio

V16_PROTOCOL_SHA256 = "cde8c76f0fff818b2253b9d8d65d5c3b55ab11eefacd2e34ab04d95c41c4479e"
V16_GLOBAL_SEARCH_TRIALS = 6_113
V16_VALIDATION_PANEL_SHA256 = (
    "777302d40ff29bc0c0ca53634511500102b4354e566f503575df101781fd507f"
)
V16_VALIDATION_ARCHIVE_SHA256 = (
    "d17378519ae947c78d76cd6a960bf5b99863a671c2d4ce688ec6a69673f1162f"
)
V16_VALIDATION_START = "2008-07-31"
V16_VALIDATION_END = "2026-07-31"
V16_VALIDATION_TICKERS = ("IJH", "IJR", "IWM", "MVV", "SAA", "SHY", "UWM")
V16_DATASETS = {
    "midcap400": {
        "label": "S&P MidCap 400",
        "core": "IJH",
        "leveraged": "MVV",
        "defensive": "SHY",
    },
    "russell2000": {
        "label": "Russell 2000",
        "core": "IWM",
        "leveraged": "UWM",
        "defensive": "SHY",
    },
    "smallcap600": {
        "label": "S&P SmallCap 600",
        "core": "IJR",
        "leveraged": "SAA",
        "defensive": "SHY",
    },
}


def _active_statistics(
    strategy: BacktestResult, benchmark: BacktestResult
) -> tuple[pd.Series, dict[str, Any]]:
    aligned = pd.concat(
        [strategy.returns.rename("strategy"), benchmark.returns.rename("benchmark")],
        axis=1,
    ).dropna()
    active = (aligned["strategy"] - aligned["benchmark"]).rename("active")
    return active, {
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
        "active_global_deflated_sharpe": deflated_sharpe_ratio(
            active, trials=V16_GLOBAL_SEARCH_TRIALS
        ),
    }


def _series_statistics(active: pd.Series) -> dict[str, Any]:
    clean = active.dropna()
    return {
        "observations": int(len(clean)),
        "active_return_newey_west": newey_west_mean_test(clean, max_lag=9),
        "active_probabilistic_sharpe": probabilistic_sharpe_ratio(
            clean, benchmark_sharpe=0.0
        ),
        "active_global_deflated_sharpe": deflated_sharpe_ratio(
            clean, trials=V16_GLOBAL_SEARCH_TRIALS
        ),
    }


def _snapshot_integrity(
    panel: MarketPanel,
    validation_receipt: dict[str, Any],
    protocol_receipt: dict[str, Any],
    data_receipt: dict[str, Any],
    *,
    protocol_sha256: str,
) -> dict[str, Any]:
    if protocol_sha256 != V16_PROTOCOL_SHA256:
        raise ValueError("v16 協議雜湊與首次中小型 2 倍 ETF 下載前凍結版本不同")
    if protocol_receipt.get("protocol_sha256") != V16_PROTOCOL_SHA256:
        raise ValueError("v16 協議凍結收據雜湊不符")
    if protocol_receipt.get("status") != "frozen_before_first_download_or_calculation":
        raise ValueError("v16 協議收據未證明先凍結再下載")
    if data_receipt.get("pre_registration_order_proved") is not True:
        raise ValueError("v16 資料收據未證明預先登錄順序")

    protocol_mtime = int(protocol_receipt.get("protocol_mtime_epoch", 0))
    snapshot_mtime = int(
        data_receipt.get("download", {}).get("snapshot_mtime_epoch", 0)
    )
    if not 0 < protocol_mtime < snapshot_mtime:
        raise ValueError("v16 協議檔時間未早於首次下載快照")

    receipt_snapshot = data_receipt.get("snapshot") or {}
    for receipt in (receipt_snapshot, validation_receipt):
        if receipt.get("panel_sha256") != V16_VALIDATION_PANEL_SHA256:
            raise ValueError("v16 驗證面板雜湊不符")
        if receipt.get("archive_sha256") != V16_VALIDATION_ARCHIVE_SHA256:
            raise ValueError("v16 驗證 ZIP 雜湊不符")
    if receipt_snapshot.get("contract_ok") is not True:
        raise ValueError("v16 資料收據的快照契約未通過")
    if (validation_receipt.get("contract") or {}).get("ok") is not True:
        raise ValueError("v16 驗證快照契約未通過")

    tickers = tuple(sorted(panel.close.columns))
    if tickers != V16_VALIDATION_TICKERS:
        raise ValueError("v16 ETF 代號與下載前協議不同")
    if panel.start.strftime("%Y-%m-%d") != "2005-01-03":
        raise ValueError("v16 驗證資料起點與凍結協議不同")
    if panel.end.strftime("%Y-%m-%d") != V16_VALIDATION_END:
        raise ValueError("v16 驗證資料終點與凍結協議不同")
    return {
        "protocol_sha256": protocol_sha256,
        "panel_sha256": V16_VALIDATION_PANEL_SHA256,
        "archive_sha256": V16_VALIDATION_ARCHIVE_SHA256,
        "tickers": list(tickers),
        "start": panel.start.strftime("%Y-%m-%d"),
        "end": panel.end.strftime("%Y-%m-%d"),
        "rows": int(len(panel.close)),
        "snapshot_contract_ok": True,
        "protocol_frozen_before_first_download": True,
        "protocol_mtime_epoch": protocol_mtime,
        "snapshot_mtime_epoch": snapshot_mtime,
    }


def _failed_economic_gates() -> dict[str, bool]:
    return {
        "cagr_beats_core_25bp": False,
        "sharpe_beats_core": False,
        "drawdown_not_worse_than_core": False,
        "calmar_beats_core": False,
        "50bps_cagr_beats_core_10bp": False,
        "both_halves_cagr_beat_core_10bp": False,
        "rolling_wins_60pct_and_positive_median_vs_core": False,
        "cagr_beats_unlevered_trend_25bp": False,
        "sharpe_beats_unlevered_trend": False,
        "calmar_beats_unlevered_trend": False,
        "50bps_cagr_beats_unlevered_trend_10bp": False,
        "both_halves_cagr_beat_unlevered_trend_10bp": False,
        "sharpe_beats_fixed_150": False,
        "calmar_beats_fixed_150": False,
        "drawdown_improves_fixed_150_10pp": False,
        "50bps_cagr_shortfall_vs_fixed_within_100bp": False,
    }


def _economic_gates(data: dict[str, Any]) -> dict[str, bool]:
    strategy = data["strategy_metrics"]
    core = data["benchmark_metrics"]["core"]
    trend = data["benchmark_metrics"]["unlevered_trend"]
    fixed = data["benchmark_metrics"]["fixed_150"]
    rolling = data["rolling_five_year_vs_core"]["summary"]
    return {
        "cagr_beats_core_25bp": bool(strategy["cagr"] > core["cagr"] + 0.0025),
        "sharpe_beats_core": bool(strategy["sharpe"] > core["sharpe"]),
        "drawdown_not_worse_than_core": bool(
            strategy["max_drawdown"] >= core["max_drawdown"]
        ),
        "calmar_beats_core": bool(strategy["calmar"] > core["calmar"]),
        "50bps_cagr_beats_core_10bp": bool(
            data["cost_50bps"]["vs_core_cagr_difference"] > 0.001
        ),
        "both_halves_cagr_beat_core_10bp": bool(
            all(
                half["cagr_difference"] > 0.001
                for half in data["fixed_halves_vs_core"].values()
            )
        ),
        "rolling_wins_60pct_and_positive_median_vs_core": bool(
            rolling.get("cagr_win_fraction", 0.0) >= 0.60
            and rolling.get("median_cagr_difference", -1.0) > 0.0
        ),
        "cagr_beats_unlevered_trend_25bp": bool(
            strategy["cagr"] > trend["cagr"] + 0.0025
        ),
        "sharpe_beats_unlevered_trend": bool(strategy["sharpe"] > trend["sharpe"]),
        "calmar_beats_unlevered_trend": bool(strategy["calmar"] > trend["calmar"]),
        "50bps_cagr_beats_unlevered_trend_10bp": bool(
            data["cost_50bps"]["vs_unlevered_trend_cagr_difference"] > 0.001
        ),
        "both_halves_cagr_beat_unlevered_trend_10bp": bool(
            all(
                half["cagr_difference"] > 0.001
                for half in data["fixed_halves_vs_unlevered_trend"].values()
            )
        ),
        "sharpe_beats_fixed_150": bool(strategy["sharpe"] > fixed["sharpe"]),
        "calmar_beats_fixed_150": bool(strategy["calmar"] > fixed["calmar"]),
        "drawdown_improves_fixed_150_10pp": bool(
            strategy["max_drawdown"] >= fixed["max_drawdown"] + 0.10
        ),
        "50bps_cagr_shortfall_vs_fixed_within_100bp": bool(
            data["cost_50bps"]["vs_fixed_150_cagr_difference"] >= -0.01
        ),
    }


def _dataset_results(
    panel: MarketPanel,
    *,
    label: str,
    core: str,
    leveraged: str,
    defensive: str,
    start: str,
    end: str,
    primary_cost_bps: float,
    stress_cost_bps: float,
) -> tuple[dict[str, Any], dict[str, pd.Series]]:
    before_start = panel.close.index < pd.Timestamp(start)
    warmup = {
        ticker: int(panel.close.loc[before_start, ticker].notna().sum())
        for ticker in (core, leveraged, defensive)
    }
    base: dict[str, Any] = {
        "label": label,
        "assets": {"core": core, "leveraged": leveraged, "defensive": defensive},
        "formal_period": {"start": start, "end": end},
        "prestart_sessions": warmup,
        "required_prestart_sessions_each": 252,
    }
    if any(value < 252 for value in warmup.values()):
        return {
            **base,
            "status": "insufficient_warmup",
            "data_gate_passed": False,
            "failure": "；".join(
                f"{ticker} 正式期前有效日 {value}/252"
                for ticker, value in warmup.items()
            ),
            "economic_gates": _failed_economic_gates(),
        }, {}

    targets = trend_volatility_brake_targets(
        panel.close,
        core=core,
        leveraged=leveraged,
        defensive=defensive,
        initial_signal_before=start,
    )
    unlevered_target = trend_volatility_brake_targets(
        panel.close,
        core=core,
        leveraged=leveraged,
        defensive=defensive,
        initial_signal_before=start,
        maximum_equity_notional=1.0,
    )
    signals = targets.dropna(how="all")
    if signals.empty:
        return {
            **base,
            "status": "no_weekly_signal",
            "data_gate_passed": False,
            "failure": "正式期以前沒有已完成週末訊號",
            "economic_gates": _failed_economic_gates(),
        }, {}

    initial_signal = pd.Timestamp(signals.index[0])
    position = panel.close.index.get_loc(initial_signal)
    if not isinstance(position, int) or position + 1 >= len(panel.close.index):
        raise ValueError(f"{label} 初始訊號沒有下一個可執行交易日")
    run_start = pd.Timestamp(panel.close.index[position + 1])
    first_execution_complete = all(
        frame.loc[run_start, [core, leveraged, defensive]].notna().all()
        for frame in panel.field_map().values()
    )
    if not first_execution_complete:
        return {
            **base,
            "status": "first_execution_missing_ohlcv",
            "data_gate_passed": False,
            "failure": f"第一個執行日 {run_start:%Y-%m-%d} 缺少完整 OHLCV",
            "economic_gates": _failed_economic_gates(),
        }, {}

    signal_text = initial_signal.strftime("%Y-%m-%d")
    core_target = buy_and_hold_targets(panel.close, core, signal_on=signal_text)
    leveraged_target = buy_and_hold_targets(panel.close, leveraged, signal_on=signal_text)
    fixed_target = fixed_weight_weekly_targets(
        panel.close, {core: 0.50, leveraged: 0.50}, signal_on=signal_text
    )

    def run(target: pd.DataFrame, name: str, cost: float) -> BacktestResult:
        full = run_backtest(
            panel,
            target,
            name=f"{label} {name}",
            cost_bps=cost,
            start=run_start,
        )
        return _slice_result(full, start, end)

    strategy = run(targets, "v16 趨勢與波動煞車", primary_cost_bps)
    core_result = run(core_target, f"{core} 買進持有", primary_cost_bps)
    leveraged_result = run(
        leveraged_target, f"{leveraged} 買進持有", primary_cost_bps
    )
    trend_result = run(unlevered_target, "不加槓桿同趨勢", primary_cost_bps)
    fixed_result = run(fixed_target, "固定 150% 曝險", primary_cost_bps)
    strategy_50 = run(targets, "v16 50bps", stress_cost_bps)
    core_50 = run(core_target, f"{core} 50bps", stress_cost_bps)
    trend_50 = run(unlevered_target, "不加槓桿同趨勢 50bps", stress_cost_bps)
    fixed_50 = run(fixed_target, "固定 150% 50bps", stress_cost_bps)

    active_core, core_comparison = _active_statistics(strategy, core_result)
    active_trend, trend_comparison = _active_statistics(strategy, trend_result)
    active_fixed, fixed_comparison = _active_statistics(strategy, fixed_result)
    periods = (
        ("first", "2008-07-31", "2017-07-28"),
        ("second", "2017-07-31", "2026-07-31"),
    )
    target_rows = targets.dropna(how="all")
    target_sums = target_rows.sum(axis=1)
    target_notional = target_rows[core] + 2.0 * target_rows[leveraged]
    realized_weights = strategy.weights
    weight_integrity = {
        "target_rows": int(len(target_rows)),
        "target_weight_sum_min": float(target_sums.min()),
        "target_weight_sum_max": float(target_sums.max()),
        "target_equity_notional_min": float(target_notional.min()),
        "target_equity_notional_max": float(target_notional.max()),
        "risk_on_average_equity_notional": float(
            target_notional[target_rows[defensive] < 0.5].mean()
        ),
        "realized_fully_invested_fraction": float(
            np.isclose(realized_weights.sum(axis=1), 1.0, atol=1e-8).mean()
        ),
        "realized_minimum_asset_weight": float(realized_weights.min().min()),
        "realized_maximum_asset_weight": float(realized_weights.max().max()),
        "maximum_allowed_equity_notional": 1.50,
        "portfolio_borrowing_or_shorting": False,
    }
    weight_integrity["passed"] = bool(
        np.isclose(target_sums, 1.0, atol=1e-8).all()
        and target_notional.min() >= -1e-12
        and target_notional.max() <= 1.50 + 1e-8
        and weight_integrity["realized_fully_invested_fraction"] >= 0.99
        and weight_integrity["realized_minimum_asset_weight"] >= -1e-12
        and weight_integrity["realized_maximum_asset_weight"] <= 1.0 + 1e-8
    )

    formal_targets = target_rows.loc[pd.Timestamp(start) : pd.Timestamp(end)]
    risk_off = formal_targets[defensive] > 0.5
    result: dict[str, Any] = {
        **base,
        "status": "completed",
        "data_gate_passed": bool(weight_integrity["passed"]),
        "period": {
            "start": start,
            "end": end,
            "sessions": int(len(strategy.equity)),
            "initial_signal": signal_text,
            "initial_execution": run_start.strftime("%Y-%m-%d"),
        },
        "strategy_metrics": strategy.metrics,
        "benchmark_metrics": {
            "core": core_result.metrics,
            "unlevered_trend": trend_result.metrics,
            "fixed_150": fixed_result.metrics,
            "leveraged_buy_and_hold_diagnostic": leveraged_result.metrics,
        },
        "comparison_vs_core": core_comparison,
        "comparison_vs_unlevered_trend": trend_comparison,
        "comparison_vs_fixed_150": fixed_comparison,
        "cost_50bps": {
            "strategy_metrics": strategy_50.metrics,
            "core_metrics": core_50.metrics,
            "unlevered_trend_metrics": trend_50.metrics,
            "fixed_150_metrics": fixed_50.metrics,
            "vs_core_cagr_difference": (
                strategy_50.metrics["cagr"] - core_50.metrics["cagr"]
            ),
            "vs_unlevered_trend_cagr_difference": (
                strategy_50.metrics["cagr"] - trend_50.metrics["cagr"]
            ),
            "vs_fixed_150_cagr_difference": (
                strategy_50.metrics["cagr"] - fixed_50.metrics["cagr"]
            ),
        },
        "fixed_halves_vs_core": _halves(strategy, core_result, periods),
        "fixed_halves_vs_unlevered_trend": _halves(
            strategy, trend_result, periods
        ),
        "rolling_five_year_vs_core": _rolling_comparison(strategy, core_result),
        "rolling_five_year_vs_unlevered_trend": _rolling_comparison(
            strategy, trend_result
        ),
        "weight_integrity": weight_integrity,
        "signals": {
            "completed_weekly_signals_in_formal_period": int(len(formal_targets)),
            "risk_on_weeks": int((~risk_off).sum()),
            "risk_off_weeks": int(risk_off.sum()),
            "completed_rebalances_in_formal_period": int(
                strategy.diagnostics["rebalance_count"]
            ),
            "latest_policy": (
                "risk_off_shy" if bool(risk_off.iloc[-1]) else "risk_on_scaled_equity"
            ),
            "latest_completed_week_end": pd.Timestamp(formal_targets.index[-1]).strftime(
                "%Y-%m-%d"
            ),
            "latest_target_equity_notional": float(target_notional.loc[formal_targets.index[-1]]),
        },
    }
    result["economic_gates"] = _economic_gates(result)
    return result, {
        "vs_core": active_core,
        "vs_unlevered_trend": active_trend,
        "vs_fixed_150": active_fixed,
    }


def evaluate_trend_volatility_brake_research(
    validation_panel: MarketPanel,
    *,
    validation_receipt: dict[str, Any],
    protocol_receipt: dict[str, Any],
    data_receipt: dict[str, Any],
    protocol_sha256: str,
    primary_cost_bps: float = 10.0,
    stress_cost_bps: float = 50.0,
) -> dict[str, Any]:
    """Evaluate v16 only after the rule and actual mid/small-cap ETFs were frozen."""
    snapshot = _snapshot_integrity(
        validation_panel,
        validation_receipt,
        protocol_receipt,
        data_receipt,
        protocol_sha256=protocol_sha256,
    )
    datasets: dict[str, Any] = {}
    active: dict[str, dict[str, pd.Series]] = {
        "core": {},
        "unlevered_trend": {},
        "fixed_150": {},
    }
    for key, spec in V16_DATASETS.items():
        data, active_series = _dataset_results(
            validation_panel,
            label=str(spec["label"]),
            core=str(spec["core"]),
            leveraged=str(spec["leveraged"]),
            defensive=str(spec["defensive"]),
            start=V16_VALIDATION_START,
            end=V16_VALIDATION_END,
            primary_cost_bps=primary_cost_bps,
            stress_cost_bps=stress_cost_bps,
        )
        datasets[key] = data
        if active_series:
            active["core"][key] = active_series["vs_core"]
            active["unlevered_trend"][key] = active_series["vs_unlevered_trend"]
            active["fixed_150"][key] = active_series["vs_fixed_150"]

    economic_gates = {
        f"{dataset_key}_{gate_name}": bool(passed)
        for dataset_key, data in datasets.items()
        for gate_name, passed in data["economic_gates"].items()
    }
    data_gates = {
        "snapshot_contract_hashes_and_preregistration_pass": True,
        **{
            f"{key}_warmup_execution_weekly_clock_and_weights_pass": bool(
                data["data_gate_passed"]
            )
            for key, data in datasets.items()
        },
    }
    paper_eligible = all(economic_gates.values()) and all(data_gates.values())

    statistical_gates: dict[str, bool] = {}
    statistical_details: dict[str, Any] = {}
    comparison_keys = {
        "core": "comparison_vs_core",
        "unlevered_trend": "comparison_vs_unlevered_trend",
        "fixed_150": "comparison_vs_fixed_150",
    }
    for key, data in datasets.items():
        if data["status"] != "completed":
            for benchmark in comparison_keys:
                statistical_gates[f"{key}_vs_{benchmark}_newey_west_t_1_96"] = False
                statistical_gates[f"{key}_vs_{benchmark}_psr_95pct"] = False
                statistical_gates[f"{key}_vs_{benchmark}_global_dsr_95pct"] = False
            statistical_details[key] = {"status": "not_evaluable_due_to_data_gate"}
            continue
        statistical_details[key] = {}
        for benchmark, comparison_key in comparison_keys.items():
            comparison = data[comparison_key]
            nw = comparison["active_return_newey_west"]
            psr = comparison["active_probabilistic_sharpe"]
            dsr = comparison["active_global_deflated_sharpe"]
            statistical_gates[f"{key}_vs_{benchmark}_newey_west_t_1_96"] = bool(
                nw["t_stat"] >= 1.96
            )
            statistical_gates[f"{key}_vs_{benchmark}_psr_95pct"] = bool(
                psr["probability"] >= 0.95
            )
            statistical_gates[f"{key}_vs_{benchmark}_global_dsr_95pct"] = bool(
                dsr["probability"] >= 0.95
            )
            statistical_details[key][benchmark] = {
                "newey_west": nw,
                "probabilistic_sharpe": psr,
                "global_deflated_sharpe": dsr,
            }

    pooled: dict[str, Any] = {}
    if all(len(series) == len(V16_DATASETS) for series in active.values()):
        pooled = {
            f"equal_weight_active_vs_{benchmark}": _series_statistics(
                pd.concat(series, axis=1, join="inner").mean(axis=1)
            )
            for benchmark, series in active.items()
        }
        pooled.update(
            {
                "gate_eligible": False,
                "reason": "預先指定為診斷；不能覆蓋任何單一市場失敗",
            }
        )

    statistically_confirmed = paper_eligible and all(statistical_gates.values())
    return {
        "schema_version": 1,
        "strategy_name": "v16 週度趨勢與波動煞車",
        "status": (
            "historically_confirmed_pending_live"
            if statistically_confirmed
            else "paper_entry_passed_statistical_pending"
            if paper_eligible
            else "new_mid_small_cap_leveraged_etf_validation_failed"
        ),
        "paper_eligible": paper_eligible,
        "statistically_confirmed": statistically_confirmed,
        "historically_confirmed": statistically_confirmed,
        "promotion_ready": False,
        "reference_trade_candidate": False,
        "promotion_effect": "create_isolated_paper_only" if paper_eligible else "none",
        "evidence_boundary": {
            "v14_v15_samples": "problem formulation only",
            "v16_actual_2x_mid_small_cap_paths": "first-seen after protocol freeze",
            "independent_confirmation_years": 18,
            "cannot_claim_independent_twenty_year_v16": True,
        },
        "protocol": {
            "path": "docs/V16_TREND_VOLATILITY_BRAKE_PROTOCOL.md",
            "sha256": protocol_sha256,
            "frozen_before_new_validation_download": True,
            "global_search_trials": V16_GLOBAL_SEARCH_TRIALS,
            "literature_sources": [
                "https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2741701",
                "https://www.nber.org/papers/w22208",
            ],
        },
        "parameters": {
            "trend_sma_sessions": 200,
            "realized_volatility_sessions": 21,
            "target_annualized_volatility": 0.18,
            "minimum_risk_on_equity_notional": 1.00,
            "maximum_risk_on_equity_notional": 1.50,
            "risk_off": {"SHY": 1.00},
            "completed_weekly_rebalance": True,
            "execution": "completed trading-week close signal; next-session adjusted open",
            "primary_cost_bps": primary_cost_bps,
            "stress_cost_bps": stress_cost_bps,
            "portfolio_borrowing": False,
            "shorting": False,
            "leveraged_product_daily_reset": True,
        },
        "snapshot": snapshot,
        "protocol_receipt": protocol_receipt,
        "data_receipt": data_receipt,
        "datasets": datasets,
        "economic_gates": economic_gates,
        "economic_passed_gate_count": int(sum(economic_gates.values())),
        "economic_required_gate_count": len(economic_gates),
        "data_gates": data_gates,
        "data_passed_gate_count": int(sum(data_gates.values())),
        "data_required_gate_count": len(data_gates),
        "paper_entry_passed_gate_count": int(
            sum(economic_gates.values()) + sum(data_gates.values())
        ),
        "paper_entry_required_gate_count": len(economic_gates) + len(data_gates),
        "statistical_gates": statistical_gates,
        "statistical_passed_gate_count": int(sum(statistical_gates.values())),
        "statistical_required_gate_count": len(statistical_gates),
        "statistical_details": statistical_details,
        "pooled_diagnostic": pooled,
        "forward_requirements_if_history_passes": {
            "minimum_new_sessions": 252,
            "minimum_completed_rebalances": 26,
            "after_cost_return_positive": True,
            "must_beat_same_start": [
                "one-times core ETF",
                "unlevered trend control",
                "fixed 150% control",
            ],
            "max_drawdown_not_worse_than_all_benchmarks": True,
            "active_newey_west_t_at_least": 1.96,
            "active_psr_probability_at_least": 0.95,
            "historical_trades_may_be_backfilled": False,
        },
        "risk_disclosure": {
            "daily_objective": (
                "MVV, UWM and SAA seek 2x daily benchmark returns, not a fixed "
                "long-horizon multiple."
            ),
            "compounding": (
                "Daily reset, volatility, expenses and compounding can materially alter "
                "long-horizon outcomes."
            ),
            "loss_risk": (
                "Risk-on exposure can reach about 150% in more volatile mid- and small-cap "
                "markets, while the trend brake can also whipsaw."
            ),
        },
        "interpretation": {
            "paper_decision": (
                "All frozen economic and integrity gates passed; only isolated Paper may start."
                if paper_eligible
                else "At least one frozen economic or integrity gate failed; do not create v16 Paper."
            ),
            "reference_decision": (
                "Not reference-ready; full historical statistics and at least 252 new Paper "
                "sessions must pass before readiness may expose an allocation."
            ),
        },
    }
