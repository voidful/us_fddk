from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from usfddk.engine import run_backtest
from usfddk.hierarchical_defense import _halves, _rolling_comparison, _slice_result
from usfddk.metrics import newey_west_mean_test
from usfddk.models import BacktestResult, MarketPanel
from usfddk.strategies import buy_and_hold_targets, fixed_weight_targets
from usfddk.validation import deflated_sharpe_ratio, probabilistic_sharpe_ratio

V17_PROTOCOL_SHA256 = "b2f83e64b744d6d57a3aa0454943a094b987b767ee505695c63cd75c6c357a5c"
V17_GLOBAL_SEARCH_TRIALS = 6_114
V17_VALIDATION_PANEL_SHA256 = (
    "4c948bf6e98055823bb4b722809040eaeeb4cb0cf3606417ad6a2a5dcdaec0c4"
)
V17_VALIDATION_ARCHIVE_SHA256 = (
    "b582a9fddf22d728227d2d64e63a85f5c8dc57012e71cf96375f34b371105bad"
)
V17_VALIDATION_START = "2004-01-02"
V17_VALIDATION_END = "2026-07-31"
V17_VALIDATION_TICKERS = (
    "DDM",
    "DIA",
    "IEF",
    "IJH",
    "IJR",
    "IWM",
    "MVV",
    "QLD",
    "QQQ",
    "SAA",
    "SHY",
    "SPY",
    "SSO",
    "UWM",
)
V17_DATASETS: dict[str, dict[str, Any]] = {
    "sp500": {
        "label": "S&P 500",
        "core": "SPY",
        "leveraged": "SSO",
        "start": "2006-07-31",
        "end": "2026-07-31",
        "required_leveraged_warmup": 20,
        "halves": (
            ("first", "2006-07-31", "2016-07-29"),
            ("second", "2016-08-01", "2026-07-31"),
        ),
    },
    "nasdaq100": {
        "label": "Nasdaq-100",
        "core": "QQQ",
        "leveraged": "QLD",
        "start": "2006-07-31",
        "end": "2026-07-31",
        "required_leveraged_warmup": 20,
        "halves": (
            ("first", "2006-07-31", "2016-07-29"),
            ("second", "2016-08-01", "2026-07-31"),
        ),
    },
    "dow30": {
        "label": "Dow 30",
        "core": "DIA",
        "leveraged": "DDM",
        "start": "2006-07-31",
        "end": "2026-07-31",
        "required_leveraged_warmup": 20,
        "halves": (
            ("first", "2006-07-31", "2016-07-29"),
            ("second", "2016-08-01", "2026-07-31"),
        ),
    },
    "midcap400": {
        "label": "S&P MidCap 400",
        "core": "IJH",
        "leveraged": "MVV",
        "start": "2008-07-31",
        "end": "2026-07-31",
        "required_leveraged_warmup": 252,
        "halves": (
            ("first", "2008-07-31", "2017-07-28"),
            ("second", "2017-07-31", "2026-07-31"),
        ),
    },
    "russell2000": {
        "label": "Russell 2000",
        "core": "IWM",
        "leveraged": "UWM",
        "start": "2008-07-31",
        "end": "2026-07-31",
        "required_leveraged_warmup": 252,
        "halves": (
            ("first", "2008-07-31", "2017-07-28"),
            ("second", "2017-07-31", "2026-07-31"),
        ),
    },
    "smallcap600": {
        "label": "S&P SmallCap 600",
        "core": "IJR",
        "leveraged": "SAA",
        "start": "2008-07-31",
        "end": "2026-07-31",
        "required_leveraged_warmup": 252,
        "halves": (
            ("first", "2008-07-31", "2017-07-28"),
            ("second", "2017-07-31", "2026-07-31"),
        ),
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
            active, trials=V17_GLOBAL_SEARCH_TRIALS
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
            clean, trials=V17_GLOBAL_SEARCH_TRIALS
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
    if protocol_sha256 != V17_PROTOCOL_SHA256:
        raise ValueError("v17 協議雜湊與組合計算前凍結版本不同")
    if protocol_receipt.get("protocol_sha256") != V17_PROTOCOL_SHA256:
        raise ValueError("v17 協議凍結收據雜湊不符")
    if (
        protocol_receipt.get("status")
        != "frozen_before_first_combination_download_or_calculation"
    ):
        raise ValueError("v17 協議收據未證明先凍結再計算")
    if data_receipt.get("pre_registration_order_proved") is not True:
        raise ValueError("v17 資料收據未證明預先登錄順序")

    frozen_mtime = int(protocol_receipt.get("protocol_mtime_epoch", 0))
    snapshot_mtime = int(data_receipt.get("download", {}).get("snapshot_mtime_epoch", 0))
    if frozen_mtime <= 0 or snapshot_mtime <= frozen_mtime:
        raise ValueError("v17 協議檔時間未早於首次合併快照")

    frozen_snapshot = data_receipt.get("snapshot") or {}
    for receipt in (frozen_snapshot, validation_receipt):
        if receipt.get("panel_sha256") != V17_VALIDATION_PANEL_SHA256:
            raise ValueError("v17 驗證面板雜湊不符")
        if receipt.get("archive_sha256") != V17_VALIDATION_ARCHIVE_SHA256:
            raise ValueError("v17 驗證 ZIP 雜湊不符")
    if frozen_snapshot.get("contract_ok") is not True:
        raise ValueError("v17 資料收據的快照契約未通過")
    if (validation_receipt.get("contract") or {}).get("ok") is not True:
        raise ValueError("v17 驗證快照契約未通過")

    actual_tickers = tuple(sorted(panel.close.columns))
    if actual_tickers != V17_VALIDATION_TICKERS:
        raise ValueError("v17 ETF 代號與下載前協議不同")
    if panel.start.strftime("%Y-%m-%d") != V17_VALIDATION_START:
        raise ValueError("v17 驗證資料起點與凍結協議不同")
    if panel.end.strftime("%Y-%m-%d") != V17_VALIDATION_END:
        raise ValueError("v17 驗證資料終點與凍結協議不同")
    return {
        "protocol_sha256": protocol_sha256,
        "panel_sha256": V17_VALIDATION_PANEL_SHA256,
        "archive_sha256": V17_VALIDATION_ARCHIVE_SHA256,
        "tickers": list(actual_tickers),
        "start": panel.start.strftime("%Y-%m-%d"),
        "end": panel.end.strftime("%Y-%m-%d"),
        "rows": int(len(panel.close)),
        "snapshot_contract_ok": True,
        "protocol_frozen_before_first_combination": True,
        "protocol_mtime_epoch": frozen_mtime,
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
        "rolling_wins_60pct_and_positive_median": False,
        "sharpe_beats_unlevered_75_25": False,
        "calmar_beats_unlevered_75_25": False,
        "50bps_cagr_beats_unlevered_75_25_10bp": False,
        "cagr_beats_60_40_shy_10bp": False,
        "sharpe_beats_60_40_shy": False,
        "drawdown_not_worse_than_60_40_shy": False,
        "calmar_beats_60_40_shy": False,
    }


def _economic_gates(data: dict[str, Any]) -> dict[str, bool]:
    strategy = data["strategy_metrics"]
    core = data["benchmark_metrics"]["core"]
    unlevered = data["benchmark_metrics"]["unlevered_75_25"]
    shy = data["benchmark_metrics"]["leveraged_60_40_shy"]
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
        "rolling_wins_60pct_and_positive_median": bool(
            rolling.get("cagr_win_fraction", 0.0) >= 0.60
            and rolling.get("median_cagr_difference", 0.0) > 0.0
        ),
        "sharpe_beats_unlevered_75_25": bool(
            strategy["sharpe"] > unlevered["sharpe"]
        ),
        "calmar_beats_unlevered_75_25": bool(
            strategy["calmar"] > unlevered["calmar"]
        ),
        "50bps_cagr_beats_unlevered_75_25_10bp": bool(
            data["cost_50bps"]["vs_unlevered_75_25_cagr_difference"] > 0.001
        ),
        "cagr_beats_60_40_shy_10bp": bool(strategy["cagr"] > shy["cagr"] + 0.001),
        "sharpe_beats_60_40_shy": bool(strategy["sharpe"] > shy["sharpe"]),
        "drawdown_not_worse_than_60_40_shy": bool(
            strategy["max_drawdown"] >= shy["max_drawdown"]
        ),
        "calmar_beats_60_40_shy": bool(strategy["calmar"] > shy["calmar"]),
    }


def _dataset_results(
    panel: MarketPanel,
    *,
    label: str,
    core: str,
    leveraged: str,
    start: str,
    end: str,
    required_leveraged_warmup: int,
    half_periods: tuple[tuple[str, str, str], ...],
    primary_cost_bps: float,
    stress_cost_bps: float,
) -> tuple[dict[str, Any], dict[str, pd.Series]]:
    before_start = panel.close.index < pd.Timestamp(start)
    warmup = {
        ticker: int(panel.close.loc[before_start, ticker].notna().sum())
        for ticker in (core, leveraged, "IEF", "SHY")
    }
    requirements = {
        core: 252,
        leveraged: required_leveraged_warmup,
        "IEF": 252,
        "SHY": 252,
    }
    base: dict[str, Any] = {
        "label": label,
        "assets": {
            "core": core,
            "leveraged": leveraged,
            "duration_defensive": "IEF",
            "short_duration_control": "SHY",
        },
        "formal_period": {"start": start, "end": end},
        "prestart_sessions": warmup,
        "required_prestart_sessions": requirements,
    }
    if any(warmup[ticker] < required for ticker, required in requirements.items()):
        return {
            **base,
            "status": "insufficient_warmup",
            "data_gate_passed": False,
            "failure": "；".join(
                f"{ticker} 正式期前有效日 {warmup[ticker]}/{required}"
                for ticker, required in requirements.items()
            ),
            "economic_gates": _failed_economic_gates(),
        }, {}

    strategy_targets = fixed_weight_targets(
        panel.close, {leveraged: 0.60, "IEF": 0.40}
    )
    strategy_signals = strategy_targets.dropna(how="all")
    if strategy_signals.empty:
        return {
            **base,
            "status": "no_completed_month_signal",
            "data_gate_passed": False,
            "failure": "找不到實際 2 倍 ETF 與 IEF 皆完整的已完成月末",
            "economic_gates": _failed_economic_gates(),
        }, {}

    initial_signal = pd.Timestamp(strategy_signals.index[0])
    position = panel.close.index.get_loc(initial_signal)
    if not isinstance(position, int) or position + 1 >= len(panel.close.index):
        raise ValueError(f"{label} 初始訊號沒有下一個可執行交易日")
    run_start = pd.Timestamp(panel.close.index[position + 1])
    first_execution_complete = all(
        frame.loc[run_start, [core, leveraged, "IEF", "SHY"]].notna().all()
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
    leveraged_target = buy_and_hold_targets(
        panel.close, leveraged, signal_on=signal_text
    )
    unlevered_target = fixed_weight_targets(
        panel.close, {core: 0.75, "IEF": 0.25}, signal_on=signal_text
    )
    shy_control_target = fixed_weight_targets(
        panel.close, {leveraged: 0.60, "SHY": 0.40}, signal_on=signal_text
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

    strategy = run(strategy_targets, "v17 60% 2x 股票／40% IEF", primary_cost_bps)
    core_result = run(core_target, f"{core} 買進持有", primary_cost_bps)
    unlevered_result = run(
        unlevered_target, "未槓桿 75% 股票／25% IEF", primary_cost_bps
    )
    shy_result = run(
        shy_control_target, "60% 2x 股票／40% SHY", primary_cost_bps
    )
    leveraged_result = run(
        leveraged_target, f"{leveraged} 買進持有診斷", primary_cost_bps
    )
    strategy_50 = run(strategy_targets, "v17 50bps", stress_cost_bps)
    core_50 = run(core_target, f"{core} 50bps", stress_cost_bps)
    unlevered_50 = run(
        unlevered_target, "未槓桿 75/25 50bps", stress_cost_bps
    )
    shy_50 = run(shy_control_target, "60/40 SHY 50bps", stress_cost_bps)

    active_core, core_comparison = _active_statistics(strategy, core_result)
    active_unlevered, unlevered_comparison = _active_statistics(
        strategy, unlevered_result
    )
    active_shy, shy_comparison = _active_statistics(strategy, shy_result)

    target_rows = strategy_targets.dropna(how="all")
    formal_targets = target_rows.loc[pd.Timestamp(start) : pd.Timestamp(end)]
    target_sums = formal_targets.sum(axis=1)
    target_notional = 2.0 * formal_targets[leveraged] + formal_targets["IEF"]
    completed_month_ends = set(
        panel.close.loc[: pd.Timestamp(end)]
        .groupby(panel.close.loc[: pd.Timestamp(end)].index.to_period("M"))
        .apply(lambda frame: frame.index[-1])
    )
    monthly_clock_ok = all(day in completed_month_ends for day in formal_targets.index)
    realized_weights = strategy.weights
    weight_integrity = {
        "target_rows_in_formal_period": int(len(formal_targets)),
        "target_weight_sum_min": float(target_sums.min()),
        "target_weight_sum_max": float(target_sums.max()),
        "target_total_notional_min": float(target_notional.min()),
        "target_total_notional_max": float(target_notional.max()),
        "realized_fully_invested_fraction": float(
            np.isclose(realized_weights.sum(axis=1), 1.0, atol=1e-8).mean()
        ),
        "realized_minimum_asset_weight": float(realized_weights.min().min()),
        "realized_maximum_asset_weight": float(realized_weights.max().max()),
        "completed_month_end_clock": bool(monthly_clock_ok),
        "portfolio_borrowing_or_shorting": False,
    }
    weight_integrity["passed"] = bool(
        len(formal_targets) > 0
        and monthly_clock_ok
        and np.isclose(target_sums, 1.0, atol=1e-8).all()
        and np.isclose(target_notional, 1.60, atol=1e-8).all()
        and weight_integrity["realized_fully_invested_fraction"] >= 0.99
        and weight_integrity["realized_minimum_asset_weight"] >= -1e-12
        and weight_integrity["realized_maximum_asset_weight"] <= 1.0 + 1e-8
    )

    result: dict[str, Any] = {
        **base,
        "status": "completed",
        "data_gate_passed": bool(weight_integrity["passed"]),
        "period": {
            "start": start,
            "end": end,
            "sessions": int(len(strategy.equity)),
            "years": 20 if start == "2006-07-31" else 18,
            "initial_signal": signal_text,
            "initial_execution": run_start.strftime("%Y-%m-%d"),
        },
        "strategy_metrics": strategy.metrics,
        "benchmark_metrics": {
            "core": core_result.metrics,
            "unlevered_75_25": unlevered_result.metrics,
            "leveraged_60_40_shy": shy_result.metrics,
            "leveraged_buy_and_hold_diagnostic": leveraged_result.metrics,
        },
        "comparison_vs_core": core_comparison,
        "comparison_vs_unlevered_75_25": unlevered_comparison,
        "comparison_vs_leveraged_60_40_shy": shy_comparison,
        "cost_50bps": {
            "strategy_metrics": strategy_50.metrics,
            "core_metrics": core_50.metrics,
            "unlevered_75_25_metrics": unlevered_50.metrics,
            "leveraged_60_40_shy_metrics": shy_50.metrics,
            "vs_core_cagr_difference": (
                strategy_50.metrics["cagr"] - core_50.metrics["cagr"]
            ),
            "vs_unlevered_75_25_cagr_difference": (
                strategy_50.metrics["cagr"] - unlevered_50.metrics["cagr"]
            ),
            "vs_leveraged_60_40_shy_cagr_difference": (
                strategy_50.metrics["cagr"] - shy_50.metrics["cagr"]
            ),
        },
        "fixed_halves_vs_core": _halves(strategy, core_result, half_periods),
        "rolling_five_year_vs_core": _rolling_comparison(strategy, core_result),
        "weight_integrity": weight_integrity,
        "signals": {
            "completed_month_end_targets_in_formal_period": int(len(formal_targets)),
            "completed_rebalances_in_formal_period": int(
                strategy.diagnostics["rebalance_count"]
            ),
            "latest_completed_month_end": pd.Timestamp(formal_targets.index[-1]).strftime(
                "%Y-%m-%d"
            ),
            "latest_target": {leveraged: 0.60, "IEF": 0.40},
            "approximate_equity_notional": 1.20,
            "treasury_notional": 0.40,
            "total_notional": 1.60,
        },
    }
    result["economic_gates"] = _economic_gates(result)
    return result, {
        "core": active_core,
        "unlevered_75_25": active_unlevered,
        "leveraged_60_40_shy": active_shy,
    }


def evaluate_capital_efficient_research(
    validation_panel: MarketPanel,
    *,
    validation_receipt: dict[str, Any],
    protocol_receipt: dict[str, Any],
    data_receipt: dict[str, Any],
    protocol_sha256: str,
    primary_cost_bps: float = 10.0,
    stress_cost_bps: float = 50.0,
) -> dict[str, Any]:
    """Evaluate the frozen v17 stock/Treasury structure across six actual ETFs."""
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
        "unlevered_75_25": {},
        "leveraged_60_40_shy": {},
    }
    for key, spec in V17_DATASETS.items():
        data, active_series = _dataset_results(
            validation_panel,
            label=str(spec["label"]),
            core=str(spec["core"]),
            leveraged=str(spec["leveraged"]),
            start=str(spec["start"]),
            end=str(spec["end"]),
            required_leveraged_warmup=int(spec["required_leveraged_warmup"]),
            half_periods=spec["halves"],
            primary_cost_bps=primary_cost_bps,
            stress_cost_bps=stress_cost_bps,
        )
        datasets[key] = data
        for benchmark, series in active_series.items():
            active[benchmark][key] = series

    economic_gates = {
        f"{dataset_key}_{gate_name}": bool(passed)
        for dataset_key, data in datasets.items()
        for gate_name, passed in data["economic_gates"].items()
    }
    data_gates = {
        "snapshot_contract_hashes_and_preregistration_pass": True,
        **{
            f"{key}_warmup_execution_monthly_clock_and_weights_pass": bool(
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
        "unlevered_75_25": "comparison_vs_unlevered_75_25",
        "leveraged_60_40_shy": "comparison_vs_leveraged_60_40_shy",
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
    if all(len(series) == len(V17_DATASETS) for series in active.values()):
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
        "strategy_name": "v17 資本效率股票／公債組合",
        "status": (
            "historically_confirmed_pending_live"
            if statistically_confirmed
            else "paper_entry_passed_statistical_pending"
            if paper_eligible
            else "capital_efficient_equity_bond_validation_failed"
        ),
        "paper_eligible": paper_eligible,
        "statistically_confirmed": statistically_confirmed,
        "historically_confirmed": statistically_confirmed,
        "promotion_ready": False,
        "reference_trade_candidate": False,
        "promotion_effect": "create_isolated_paper_only" if paper_eligible else "none",
        "evidence_boundary": {
            "component_paths_previously_observed": True,
            "combination_rule_preregistered_before_first_v17_calculation": True,
            "large_cap_years": 20,
            "mid_small_cap_years": 18,
            "cannot_claim_fully_independent_confirmation": True,
        },
        "protocol": {
            "path": "docs/V17_CAPITAL_EFFICIENT_EQUITY_BOND_PROTOCOL.md",
            "sha256": protocol_sha256,
            "frozen_before_first_combination_download": True,
            "global_search_trials": V17_GLOBAL_SEARCH_TRIALS,
            "literature_sources": [
                "https://www.wisdomtree.com/us/products/capital-efficient/ntsx",
                "https://www.wisdomtree.com/us/insights/blog/boosting-portfolio-efficiency-via-our-90-60-approach",
            ],
        },
        "parameters": {
            "physical_weights": {"actual_daily_2x_equity_etf": 0.60, "IEF": 0.40},
            "approximate_notional": {"equity": 1.20, "treasury": 0.40, "total": 1.60},
            "monthly_rebalance": True,
            "execution": "completed month-end target; next-session adjusted open",
            "primary_cost_bps": primary_cost_bps,
            "stress_cost_bps": stress_cost_bps,
            "market_timing": False,
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
            "minimum_completed_rebalances": 6,
            "after_cost_return_positive": True,
            "must_beat_same_start": [
                "one-times core ETF",
                "unlevered 75/25 stock/IEF",
                "60% 2x equity ETF / 40% SHY",
            ],
            "max_drawdown_not_worse_than_all_three_benchmarks": True,
            "active_newey_west_t_at_least": 1.96,
            "active_psr_probability_at_least": 0.95,
            "historical_trades_may_be_backfilled": False,
        },
        "risk_disclosure": {
            "daily_objective": (
                "The six leveraged ETFs seek 2x daily benchmark returns, not a fixed "
                "long-horizon multiple."
            ),
            "duration_risk": (
                "IEF has material interest-rate risk; stocks and Treasuries can fall together."
            ),
            "loss_risk": (
                "Physical weights sum to 100%, but approximate total notional is 160% and "
                "losses can be rapid and large."
            ),
        },
        "interpretation": {
            "paper_decision": (
                "All frozen economic and integrity gates passed; only isolated Paper may start."
                if paper_eligible
                else "At least one frozen economic or integrity gate failed; do not create v17 Paper."
            ),
            "reference_decision": (
                "Not reference-ready; full historical statistics and at least 252 new Paper "
                "sessions must pass before readiness may expose an allocation."
            ),
        },
    }
