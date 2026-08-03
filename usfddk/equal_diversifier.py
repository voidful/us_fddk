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

V18_PROTOCOL_SHA256 = "5d88a1a11746f87ceee17fcf805bb570ae5992fa220e72b3711477984e2bd263"
V18_GLOBAL_SEARCH_TRIALS = 6_121
V18_VALIDATION_PANEL_SHA256 = (
    "dd920b902fcc0054c411d78a5255b9b2cbc699fbfda2d17a5d04aa38a249ef2c"
)
V18_VALIDATION_ARCHIVE_SHA256 = (
    "19347d5c1152a95248fecfd5feec098bd9176ddae311d62f9209e75aa82fd9e5"
)
V18_VALIDATION_START = "2008-06-02"
V18_VALIDATION_END = "2026-07-31"
V18_FORMAL_START = "2010-07-30"
V18_FORMAL_END = "2026-07-31"
V18_VALIDATION_TICKERS = ("EEM", "EET", "EFA", "EFO", "GLD", "IEF", "SHY")
V18_DATASETS: dict[str, dict[str, str]] = {
    "developed_ex_us": {
        "label": "美國以外已開發市場",
        "core": "EFA",
        "leveraged": "EFO",
    },
    "emerging_markets": {
        "label": "新興市場",
        "core": "EEM",
        "leveraged": "EET",
    },
}
V18_HALVES = (
    ("first", "2010-07-30", "2018-07-30"),
    ("second", "2018-07-31", "2026-07-31"),
)


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
            active, trials=V18_GLOBAL_SEARCH_TRIALS
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
            clean, trials=V18_GLOBAL_SEARCH_TRIALS
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
    if protocol_sha256 != V18_PROTOCOL_SHA256:
        raise ValueError("v18 協議雜湊與外部日線下載前凍結版本不同")
    if protocol_receipt.get("protocol_sha256") != V18_PROTOCOL_SHA256:
        raise ValueError("v18 協議凍結收據雜湊不符")
    if (
        protocol_receipt.get("status")
        != "frozen_before_first_external_daily_download_or_calculation"
    ):
        raise ValueError("v18 協議收據未證明先凍結再下載日線")
    if data_receipt.get("pre_registration_order_proved") is not True:
        raise ValueError("v18 資料收據未證明預先登錄順序")

    frozen_mtime = int(protocol_receipt.get("protocol_mtime_epoch", 0))
    snapshot_mtime = int(data_receipt.get("download", {}).get("snapshot_mtime_epoch", 0))
    if frozen_mtime <= 0 or snapshot_mtime <= frozen_mtime:
        raise ValueError("v18 協議檔時間未早於首次外部日線快照")

    frozen_snapshot = data_receipt.get("snapshot") or {}
    for receipt in (frozen_snapshot, validation_receipt):
        if receipt.get("panel_sha256") != V18_VALIDATION_PANEL_SHA256:
            raise ValueError("v18 驗證面板雜湊不符")
        if receipt.get("archive_sha256") != V18_VALIDATION_ARCHIVE_SHA256:
            raise ValueError("v18 驗證 ZIP 雜湊不符")
    if frozen_snapshot.get("contract_ok") is not True:
        raise ValueError("v18 資料收據的快照契約未通過")
    if (validation_receipt.get("contract") or {}).get("ok") is not True:
        raise ValueError("v18 驗證快照契約未通過")

    actual_tickers = tuple(sorted(panel.close.columns))
    if actual_tickers != V18_VALIDATION_TICKERS:
        raise ValueError("v18 ETF 代號與下載前協議不同")
    if panel.start.strftime("%Y-%m-%d") != V18_VALIDATION_START:
        raise ValueError("v18 驗證資料起點與凍結協議不同")
    if panel.end.strftime("%Y-%m-%d") != V18_VALIDATION_END:
        raise ValueError("v18 驗證資料終點與凍結協議不同")
    if len(panel.close) < 4_500:
        raise ValueError("v18 驗證面板少於凍結的 4,500 列")
    return {
        "protocol_sha256": protocol_sha256,
        "panel_sha256": V18_VALIDATION_PANEL_SHA256,
        "archive_sha256": V18_VALIDATION_ARCHIVE_SHA256,
        "tickers": list(actual_tickers),
        "start": panel.start.strftime("%Y-%m-%d"),
        "end": panel.end.strftime("%Y-%m-%d"),
        "rows": int(len(panel.close)),
        "snapshot_contract_ok": True,
        "protocol_frozen_before_first_external_daily_download": True,
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
        "cagr_beats_unlevered_same_assets_10bp": False,
        "50bps_cagr_beats_unlevered_same_assets_10bp": False,
    }


def _economic_gates(data: dict[str, Any]) -> dict[str, bool]:
    strategy = data["strategy_metrics"]
    core = data["benchmark_metrics"]["core"]
    unlevered = data["benchmark_metrics"]["unlevered_same_assets"]
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
        "cagr_beats_unlevered_same_assets_10bp": bool(
            strategy["cagr"] > unlevered["cagr"] + 0.001
        ),
        "50bps_cagr_beats_unlevered_same_assets_10bp": bool(
            data["cost_50bps"]["vs_unlevered_same_assets_cagr_difference"] > 0.001
        ),
    }


def _signal_execution_integrity(
    panel: MarketPanel,
    formal_targets: pd.DataFrame,
    required_assets: list[str],
) -> dict[str, Any]:
    completed_month_ends = set(
        panel.close.loc[: pd.Timestamp(V18_FORMAL_END)]
        .groupby(panel.close.loc[: pd.Timestamp(V18_FORMAL_END)].index.to_period("M"))
        .apply(lambda frame: frame.index[-1])
    )
    clock_ok = all(day in completed_month_ends for day in formal_targets.index)
    missing_execution_days: list[str] = []
    pending_after_cutoff_signals: list[str] = []
    for signal_day in formal_targets.index:
        position = panel.close.index.get_loc(signal_day)
        if not isinstance(position, int):
            missing_execution_days.append(pd.Timestamp(signal_day).strftime("%Y-%m-%d"))
            continue
        if position + 1 >= len(panel.close.index):
            # A completed month-end at the frozen data cutoff is a valid current
            # target, but its next-session execution is future data, not a missing bar.
            pending_after_cutoff_signals.append(
                pd.Timestamp(signal_day).strftime("%Y-%m-%d")
            )
            continue
        execution_day = panel.close.index[position + 1]
        if not all(
            frame.loc[execution_day, required_assets].notna().all()
            for frame in panel.field_map().values()
        ):
            missing_execution_days.append(pd.Timestamp(execution_day).strftime("%Y-%m-%d"))
    return {
        "completed_month_end_clock": bool(clock_ok),
        "formal_signal_count": int(len(formal_targets)),
        "execution_days_with_missing_ohlcv": missing_execution_days,
        "signals_pending_execution_after_data_cutoff": pending_after_cutoff_signals,
        "all_signal_execution_days_complete": not missing_execution_days,
    }


def _dataset_results(
    panel: MarketPanel,
    *,
    label: str,
    core: str,
    leveraged: str,
    primary_cost_bps: float,
    stress_cost_bps: float,
) -> tuple[dict[str, Any], dict[str, pd.Series]]:
    required_assets = [core, leveraged, "IEF", "GLD", "SHY"]
    before_start = panel.close.index < pd.Timestamp(V18_FORMAL_START)
    warmup = {
        ticker: int(panel.close.loc[before_start, ticker].notna().sum())
        for ticker in required_assets
    }
    requirements = {ticker: 252 for ticker in required_assets}
    base: dict[str, Any] = {
        "label": label,
        "assets": {
            "core": core,
            "leveraged": leveraged,
            "duration_defensive": "IEF",
            "inflation_diversifier": "GLD",
            "short_duration_control": "SHY",
        },
        "formal_period": {"start": V18_FORMAL_START, "end": V18_FORMAL_END},
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

    targets = {
        "strategy": fixed_weight_targets(
            panel.close, {leveraged: 0.50, "IEF": 0.25, "GLD": 0.25}
        ),
        "unlevered_same_assets": fixed_weight_targets(
            panel.close, {core: 2 / 3, "IEF": 1 / 6, "GLD": 1 / 6}
        ),
        "leveraged_50_50_ief": fixed_weight_targets(
            panel.close, {leveraged: 0.50, "IEF": 0.50}
        ),
        "leveraged_50_50_gld": fixed_weight_targets(
            panel.close, {leveraged: 0.50, "GLD": 0.50}
        ),
        "leveraged_50_50_shy": fixed_weight_targets(
            panel.close, {leveraged: 0.50, "SHY": 0.50}
        ),
    }
    strategy_signals = targets["strategy"].dropna(how="all")
    if strategy_signals.empty:
        return {
            **base,
            "status": "no_completed_month_signal",
            "data_gate_passed": False,
            "failure": "找不到全部策略資產皆完整的已完成月末",
            "economic_gates": _failed_economic_gates(),
        }, {}

    initial_signal = pd.Timestamp(strategy_signals.index[0])
    position = panel.close.index.get_loc(initial_signal)
    if not isinstance(position, int) or position + 1 >= len(panel.close.index):
        raise ValueError(f"{label} 初始訊號沒有下一個可執行交易日")
    run_start = pd.Timestamp(panel.close.index[position + 1])
    signal_text = initial_signal.strftime("%Y-%m-%d")
    targets["core"] = buy_and_hold_targets(panel.close, core, signal_on=signal_text)
    targets["leveraged_buy_hold"] = buy_and_hold_targets(
        panel.close, leveraged, signal_on=signal_text
    )

    formal_targets = strategy_signals.loc[V18_FORMAL_START:V18_FORMAL_END]
    signal_integrity = _signal_execution_integrity(
        panel, formal_targets, required_assets
    )

    def run(target: pd.DataFrame, name: str, cost: float) -> BacktestResult:
        full = run_backtest(
            panel,
            target,
            name=f"{label} {name}",
            cost_bps=cost,
            start=run_start,
        )
        return _slice_result(full, V18_FORMAL_START, V18_FORMAL_END)

    results = {
        key: run(target, key, primary_cost_bps) for key, target in targets.items()
    }
    stress = {
        key: run(targets[key], f"{key} 50bps", stress_cost_bps)
        for key in ("strategy", "core", "unlevered_same_assets")
    }
    comparison_keys = (
        "core",
        "unlevered_same_assets",
        "leveraged_50_50_ief",
        "leveraged_50_50_gld",
        "leveraged_50_50_shy",
        "leveraged_buy_hold",
    )
    active: dict[str, pd.Series] = {}
    comparisons: dict[str, Any] = {}
    for benchmark in comparison_keys:
        active[benchmark], comparisons[benchmark] = _active_statistics(
            results["strategy"], results[benchmark]
        )

    target_sums = formal_targets.sum(axis=1)
    target_notional = (
        2.0 * formal_targets[leveraged]
        + formal_targets["IEF"]
        + formal_targets["GLD"]
    )
    realized = results["strategy"].weights
    weight_integrity = {
        **signal_integrity,
        "target_weight_sum_min": float(target_sums.min()),
        "target_weight_sum_max": float(target_sums.max()),
        "target_total_notional_min": float(target_notional.min()),
        "target_total_notional_max": float(target_notional.max()),
        "realized_fully_invested_fraction": float(
            np.isclose(realized.sum(axis=1), 1.0, atol=1e-8).mean()
        ),
        "realized_minimum_asset_weight": float(realized.min().min()),
        "realized_maximum_asset_weight": float(realized.max().max()),
        "portfolio_borrowing_or_shorting": False,
    }
    weight_integrity["passed"] = bool(
        len(formal_targets) > 0
        and weight_integrity["completed_month_end_clock"]
        and weight_integrity["all_signal_execution_days_complete"]
        and np.isclose(target_sums, 1.0, atol=1e-8).all()
        and np.isclose(target_notional, 1.50, atol=1e-8).all()
        and weight_integrity["realized_fully_invested_fraction"] >= 0.99
        and weight_integrity["realized_minimum_asset_weight"] >= -1e-12
        and weight_integrity["realized_maximum_asset_weight"] <= 1.0 + 1e-8
    )

    result: dict[str, Any] = {
        **base,
        "status": "completed",
        "data_gate_passed": bool(weight_integrity["passed"]),
        "period": {
            "start": V18_FORMAL_START,
            "end": V18_FORMAL_END,
            "sessions": int(len(results["strategy"].equity)),
            "years": 16,
            "initial_signal": signal_text,
            "initial_execution": run_start.strftime("%Y-%m-%d"),
        },
        "strategy_metrics": results["strategy"].metrics,
        "benchmark_metrics": {
            key: results[key].metrics for key in comparison_keys
        },
        "comparisons": comparisons,
        "cost_50bps": {
            "strategy_metrics": stress["strategy"].metrics,
            "core_metrics": stress["core"].metrics,
            "unlevered_same_assets_metrics": stress["unlevered_same_assets"].metrics,
            "vs_core_cagr_difference": (
                stress["strategy"].metrics["cagr"] - stress["core"].metrics["cagr"]
            ),
            "vs_unlevered_same_assets_cagr_difference": (
                stress["strategy"].metrics["cagr"]
                - stress["unlevered_same_assets"].metrics["cagr"]
            ),
        },
        "fixed_halves_vs_core": _halves(
            results["strategy"], results["core"], V18_HALVES
        ),
        "rolling_five_year_vs_core": _rolling_comparison(
            results["strategy"], results["core"]
        ),
        "diagnostic_halves": {
            key: _halves(results["strategy"], results[key], V18_HALVES)
            for key in ("unlevered_same_assets", "leveraged_50_50_ief", "leveraged_50_50_gld")
        },
        "diagnostic_rolling_five_year": {
            key: _rolling_comparison(results["strategy"], results[key])
            for key in ("unlevered_same_assets", "leveraged_50_50_ief", "leveraged_50_50_gld")
        },
        "weight_integrity": weight_integrity,
        "signals": {
            "completed_month_end_targets_in_formal_period": int(len(formal_targets)),
            "completed_rebalances_in_formal_period": int(
                results["strategy"].diagnostics["rebalance_count"]
            ),
            "latest_completed_month_end": pd.Timestamp(formal_targets.index[-1]).strftime(
                "%Y-%m-%d"
            ),
            "latest_target": {leveraged: 0.50, "IEF": 0.25, "GLD": 0.25},
            "approximate_equity_notional": 1.00,
            "treasury_notional": 0.25,
            "gold_notional": 0.25,
            "total_notional": 1.50,
        },
    }
    result["economic_gates"] = _economic_gates(result)
    return result, active


def evaluate_equal_diversifier_research(
    validation_panel: MarketPanel,
    *,
    validation_receipt: dict[str, Any],
    protocol_receipt: dict[str, Any],
    data_receipt: dict[str, Any],
    protocol_sha256: str,
    primary_cost_bps: float = 10.0,
    stress_cost_bps: float = 50.0,
) -> dict[str, Any]:
    """Evaluate the frozen v18 equal Treasury/gold capital-efficient structure."""
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
        "unlevered_same_assets": {},
    }
    for key, spec in V18_DATASETS.items():
        data, active_series = _dataset_results(
            validation_panel,
            label=spec["label"],
            core=spec["core"],
            leveraged=spec["leveraged"],
            primary_cost_bps=primary_cost_bps,
            stress_cost_bps=stress_cost_bps,
        )
        datasets[key] = data
        for benchmark in active:
            if benchmark in active_series:
                active[benchmark][key] = active_series[benchmark]

    economic_gates = {
        f"{dataset_key}_{gate_name}": bool(passed)
        for dataset_key, data in datasets.items()
        for gate_name, passed in data["economic_gates"].items()
    }
    data_gates = {
        "snapshot_contract_hashes_and_preregistration_pass": True,
        **{
            f"{key}_warmup_signal_execution_and_weights_pass": bool(
                data["data_gate_passed"]
            )
            for key, data in datasets.items()
        },
    }
    paper_eligible = all(economic_gates.values()) and all(data_gates.values())

    statistical_gates: dict[str, bool] = {}
    statistical_details: dict[str, Any] = {}
    for key, data in datasets.items():
        statistical_details[key] = {}
        if data["status"] != "completed":
            for benchmark in active:
                statistical_gates[f"{key}_vs_{benchmark}_newey_west_t_1_96"] = False
                statistical_gates[f"{key}_vs_{benchmark}_psr_95pct"] = False
                statistical_gates[f"{key}_vs_{benchmark}_global_dsr_95pct"] = False
            statistical_details[key] = {"status": "not_evaluable_due_to_data_gate"}
            continue
        for benchmark in active:
            comparison = data["comparisons"][benchmark]
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
    if all(len(series) == len(V18_DATASETS) for series in active.values()):
        pooled = {
            f"equal_weight_active_vs_{benchmark}": _series_statistics(
                pd.concat(series, axis=1, join="inner").mean(axis=1)
            )
            for benchmark, series in active.items()
        }
        pooled.update(
            {
                "gate_eligible": False,
                "reason": "事前指定為診斷；不能覆蓋任何單一海外市場失敗",
            }
        )

    statistically_confirmed = paper_eligible and all(statistical_gates.values())
    return {
        "schema_version": 1,
        "strategy_name": "v18 等權股／債／金資本效率",
        "status": (
            "historically_confirmed_pending_live"
            if statistically_confirmed
            else "paper_entry_passed_statistical_pending"
            if paper_eligible
            else "equal_diversifier_external_validation_failed"
        ),
        "paper_eligible": paper_eligible,
        "statistically_confirmed": statistically_confirmed,
        "historically_confirmed": statistically_confirmed,
        "promotion_ready": False,
        "reference_trade_candidate": False,
        "promotion_effect": "create_isolated_paper_only" if paper_eligible else "none",
        "evidence_boundary": {
            "us_design_markets_previously_observed": True,
            "us_large_cap_design_years": 20,
            "external_daily_path_downloaded_after_freeze": True,
            "external_years": 16,
            "official_summary_performance_seen_before_freeze": True,
            "classification": "semi_independent_external_validation_not_fully_blind",
            "cannot_claim_fully_independent_confirmation": True,
        },
        "protocol": {
            "path": "docs/V18_EQUAL_DIVERSIFIER_CAPITAL_EFFICIENCY_PROTOCOL.md",
            "sha256": protocol_sha256,
            "frozen_before_first_external_daily_download": True,
            "global_search_trials": V18_GLOBAL_SEARCH_TRIALS,
            "literature_sources": [
                "https://www.proshares.com/our-etfs/leveraged-and-inverse/efo",
                "https://www.proshares.com/our-etfs/leveraged-and-inverse/eet",
                "https://www.wisdomtree.com/us/insights/blog/boosting-portfolio-efficiency-via-our-90-60-approach",
                "https://www.wisdomtree.com/us/products/capital-efficient/gde",
            ],
        },
        "parameters": {
            "physical_weights": {
                "actual_daily_2x_equity_etf": 0.50,
                "IEF": 0.25,
                "GLD": 0.25,
            },
            "approximate_notional": {
                "equity": 1.00,
                "treasury": 0.25,
                "gold": 0.25,
                "total": 1.50,
            },
            "monthly_rebalance": True,
            "execution": "completed month-end target; next-session adjusted open",
            "primary_cost_bps": primary_cost_bps,
            "stress_cost_bps": stress_cost_bps,
            "market_timing": False,
            "portfolio_borrowing": False,
            "shorting": False,
            "leveraged_product_daily_reset": True,
            "paper_candidate_if_external_gates_pass": {
                "SSO": 0.50,
                "IEF": 0.25,
                "GLD": 0.25,
            },
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
                "SPY",
                "unlevered same-assets stock/IEF/GLD",
                "50% 2x equity ETF / 50% SHY",
            ],
            "max_drawdown_not_worse_than_all_three_benchmarks": True,
            "active_newey_west_t_at_least": 1.96,
            "active_psr_probability_at_least": 0.95,
            "historical_trades_may_be_backfilled": False,
        },
        "risk_disclosure": {
            "daily_objective": (
                "EFO and EET seek 2x daily benchmark returns, not a fixed long-horizon multiple."
            ),
            "diversifier_risk": (
                "IEF and GLD can both lose value and may fail to diversify equities."
            ),
            "loss_risk": (
                "Physical weights sum to 100%, but approximate total notional is 150% and losses can be rapid and large."
            ),
        },
        "interpretation": {
            "paper_decision": (
                "All frozen external economic and integrity gates passed; only isolated Paper may start."
                if paper_eligible
                else "At least one frozen external economic or integrity gate failed; do not create v18 Paper."
            ),
            "reference_decision": (
                "Not reference-ready; historical statistics and at least 252 new Paper sessions must pass before readiness may expose an allocation."
            ),
        },
    }
