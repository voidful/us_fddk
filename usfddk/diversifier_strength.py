from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from usfddk.data import panel_fingerprint
from usfddk.engine import run_backtest
from usfddk.hierarchical_defense import _halves, _rolling_comparison, _slice_result
from usfddk.metrics import newey_west_mean_test
from usfddk.models import BacktestResult, MarketPanel
from usfddk.strategies import (
    buy_and_hold_targets,
    diversifier_relative_strength_targets,
    fixed_weight_targets,
)
from usfddk.validation import deflated_sharpe_ratio, probabilistic_sharpe_ratio

V20_PROTOCOL_SHA256 = "a6fdca00b3a4d69cf42cd507f1a3fbd278275bb490ddb9ea7b980e3dc4e0f81c"
V20_GLOBAL_SEARCH_TRIALS = 6_122
V20_EXTERNAL_PANEL_SHA256 = "e30b403220d7863243a60cc9e672d3310a1f2658c7cbdd0ef70c8cdc2ddfe0d7"
V20_EXTERNAL_ARCHIVE_SHA256 = "197ed7ff65045114220e1ec8a60b854f74233206b84a2e88655a6116e31e732e"
V20_SOURCE_IDENTITIES = {
    "capital": {
        "panel_sha256": "4c948bf6e98055823bb4b722809040eaeeb4cb0cf3606417ad6a2a5dcdaec0c4",
        "archive_sha256": "b582a9fddf22d728227d2d64e63a85f5c8dc57012e71cf96375f34b371105bad",
    },
    "main": {
        "panel_sha256": "6a7ca6b83b1570007424daa46b0ff4e8fb4a655d39298a0f4f6d74c3b7ea3a66",
        "archive_sha256": "d480fb82e712f06aabe0a98461e222344656b87022b8bda2cd7ccaa4c29ae88b",
    },
    "v18": {
        "panel_sha256": "dd920b902fcc0054c411d78a5255b9b2cbc699fbfda2d17a5d04aa38a249ef2c",
        "archive_sha256": "19347d5c1152a95248fecfd5feec098bd9176ddae311d62f9209e75aa82fd9e5",
    },
    "external": {
        "panel_sha256": V20_EXTERNAL_PANEL_SHA256,
        "archive_sha256": V20_EXTERNAL_ARCHIVE_SHA256,
    },
}
V20_EXTERNAL_TICKERS = ("EWJ", "EWZ", "EZJ", "FXI", "GLD", "IEF", "SHY", "UBR", "XPP")
V20_DIVERSIFIERS = ("IEF", "GLD", "SHY")

V20_DESIGN_DATASETS: dict[str, dict[str, Any]] = {
    "sp500": {
        "label": "S&P 500",
        "core": "SPY",
        "leveraged": "SSO",
        "start": "2006-07-31",
        "end": "2026-07-31",
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
        "halves": (
            ("first", "2008-07-31", "2017-07-31"),
            ("second", "2017-08-01", "2026-07-31"),
        ),
    },
    "russell2000": {
        "label": "Russell 2000",
        "core": "IWM",
        "leveraged": "UWM",
        "start": "2008-07-31",
        "end": "2026-07-31",
        "halves": (
            ("first", "2008-07-31", "2017-07-31"),
            ("second", "2017-08-01", "2026-07-31"),
        ),
    },
    "smallcap600": {
        "label": "S&P SmallCap 600",
        "core": "IJR",
        "leveraged": "SAA",
        "start": "2008-07-31",
        "end": "2026-07-31",
        "halves": (
            ("first", "2008-07-31", "2017-07-31"),
            ("second", "2017-08-01", "2026-07-31"),
        ),
    },
    "developed_ex_us": {
        "label": "美國以外已開發市場",
        "core": "EFA",
        "leveraged": "EFO",
        "start": "2010-07-30",
        "end": "2026-07-31",
        "halves": (
            ("first", "2010-07-30", "2018-07-30"),
            ("second", "2018-07-31", "2026-07-31"),
        ),
    },
    "emerging_markets": {
        "label": "新興市場",
        "core": "EEM",
        "leveraged": "EET",
        "start": "2010-07-30",
        "end": "2026-07-31",
        "halves": (
            ("first", "2010-07-30", "2018-07-30"),
            ("second", "2018-07-31", "2026-07-31"),
        ),
    },
}
V20_EXTERNAL_DATASETS: dict[str, dict[str, Any]] = {
    "japan": {"label": "日本", "core": "EWJ", "leveraged": "EZJ"},
    "china_large_cap": {
        "label": "中國大型股",
        "core": "FXI",
        "leveraged": "XPP",
    },
    "brazil": {"label": "巴西", "core": "EWZ", "leveraged": "UBR"},
}
V20_EXTERNAL_START = "2016-09-01"
V20_EXTERNAL_END = "2026-07-31"
V20_EXTERNAL_HALVES = (
    ("first", "2016-09-01", "2021-08-31"),
    ("second", "2021-09-01", "2026-07-31"),
)


def build_v20_us_design_panel(capital_panel: MarketPanel, main_panel: MarketPanel) -> MarketPanel:
    """Join the frozen v17 equity/IEF paths with the already-seen GLD path."""
    equity_columns = [
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
    ]
    if not set(equity_columns).issubset(capital_panel.close.columns):
        raise ValueError("v20 美國設計面板缺少 v17 欄位")
    if "GLD" not in main_panel.close.columns:
        raise ValueError("v20 美國設計面板缺少 GLD")
    common = capital_panel.close.index.intersection(main_panel.close.index).sort_values()

    def joined(field: str) -> pd.DataFrame:
        return pd.concat(
            [
                capital_panel.field_map()[field].loc[common, equity_columns],
                main_panel.field_map()[field].loc[common, ["GLD"]],
            ],
            axis=1,
        )

    return MarketPanel(
        open=joined("Open"),
        high=joined("High"),
        low=joined("Low"),
        close=joined("Close"),
        volume=joined("Volume"),
        metadata={
            "derived_from_frozen_seen_snapshots": True,
            "join": "common sessions only; no fill or interpolation",
            "strategy_version": "v20",
        },
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
        "active_probabilistic_sharpe": probabilistic_sharpe_ratio(active, benchmark_sharpe=0.0),
        "active_global_deflated_sharpe": deflated_sharpe_ratio(
            active, trials=V20_GLOBAL_SEARCH_TRIALS
        ),
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
        "cagr_beats_fixed_v18_10bp": False,
        "sharpe_beats_fixed_v18": False,
        "drawdown_not_worse_than_fixed_v18": False,
        "calmar_beats_fixed_v18": False,
        "50bps_cagr_beats_fixed_v18_10bp": False,
        "cagr_beats_unlevered_same_policy_10bp": False,
        "50bps_cagr_beats_unlevered_same_policy_10bp": False,
    }


def _economic_gates(data: dict[str, Any]) -> dict[str, bool]:
    strategy = data["strategy_metrics"]
    core = data["benchmark_metrics"]["core"]
    fixed = data["benchmark_metrics"]["fixed_v18"]
    unlevered = data["benchmark_metrics"]["unlevered_same_policy"]
    rolling = data["rolling_five_year_vs_core"]["summary"]
    stress = data["cost_50bps"]
    return {
        "cagr_beats_core_25bp": bool(strategy["cagr"] > core["cagr"] + 0.0025),
        "sharpe_beats_core": bool(strategy["sharpe"] > core["sharpe"]),
        "drawdown_not_worse_than_core": bool(strategy["max_drawdown"] >= core["max_drawdown"]),
        "calmar_beats_core": bool(strategy["calmar"] > core["calmar"]),
        "50bps_cagr_beats_core_10bp": bool(stress["vs_core_cagr_difference"] > 0.001),
        "both_halves_cagr_beat_core_10bp": bool(
            all(half["cagr_difference"] > 0.001 for half in data["fixed_halves_vs_core"].values())
        ),
        "rolling_wins_60pct_and_positive_median": bool(
            rolling.get("cagr_win_fraction", 0.0) >= 0.60
            and rolling.get("median_cagr_difference", 0.0) > 0.0
        ),
        "cagr_beats_fixed_v18_10bp": bool(strategy["cagr"] > fixed["cagr"] + 0.001),
        "sharpe_beats_fixed_v18": bool(strategy["sharpe"] > fixed["sharpe"]),
        "drawdown_not_worse_than_fixed_v18": bool(
            strategy["max_drawdown"] >= fixed["max_drawdown"]
        ),
        "calmar_beats_fixed_v18": bool(strategy["calmar"] > fixed["calmar"]),
        "50bps_cagr_beats_fixed_v18_10bp": bool(stress["vs_fixed_v18_cagr_difference"] > 0.001),
        "cagr_beats_unlevered_same_policy_10bp": bool(strategy["cagr"] > unlevered["cagr"] + 0.001),
        "50bps_cagr_beats_unlevered_same_policy_10bp": bool(
            stress["vs_unlevered_same_policy_cagr_difference"] > 0.001
        ),
    }


def _signal_execution_integrity(
    panel: MarketPanel,
    targets: pd.DataFrame,
    *,
    end: str,
    required_assets: list[str],
) -> dict[str, Any]:
    through_end = panel.close.loc[: pd.Timestamp(end)]
    completed_month_ends = set(
        through_end.groupby(through_end.index.to_period("M")).apply(lambda frame: frame.index[-1])
    )
    clock_ok = all(day in completed_month_ends for day in targets.index)
    missing_execution_days: list[str] = []
    pending_after_cutoff: list[str] = []
    for signal_day in targets.index:
        position = panel.close.index.get_loc(signal_day)
        if not isinstance(position, int):
            missing_execution_days.append(pd.Timestamp(signal_day).strftime("%Y-%m-%d"))
            continue
        if position + 1 >= len(panel.close.index):
            pending_after_cutoff.append(pd.Timestamp(signal_day).strftime("%Y-%m-%d"))
            continue
        execution_day = panel.close.index[position + 1]
        if not all(
            frame.loc[execution_day, required_assets].notna().all()
            for frame in panel.field_map().values()
        ):
            missing_execution_days.append(pd.Timestamp(execution_day).strftime("%Y-%m-%d"))
    return {
        "completed_month_end_clock": bool(clock_ok),
        "formal_signal_count": int(len(targets)),
        "execution_days_with_missing_ohlcv": missing_execution_days,
        "signals_pending_execution_after_data_cutoff": pending_after_cutoff,
        "all_signal_execution_days_complete": not missing_execution_days,
    }


def _dataset_results(
    panel: MarketPanel,
    *,
    label: str,
    core: str,
    leveraged: str,
    start: str,
    end: str,
    halves: tuple[tuple[str, str, str], ...],
    equity_prestart_requirement: int,
    primary_cost_bps: float,
    stress_cost_bps: float,
) -> tuple[dict[str, Any], dict[str, pd.Series]]:
    required_assets = [core, leveraged, *V20_DIVERSIFIERS]
    missing = set(required_assets) - set(panel.close.columns)
    if missing:
        return {
            "label": label,
            "status": "missing_assets",
            "data_gate_passed": False,
            "failure": "缺少行情：" + ", ".join(sorted(missing)),
            "economic_gates": _failed_economic_gates(),
        }, {}

    before_start = panel.close.index < pd.Timestamp(start)
    warmup = {
        ticker: int(panel.close.loc[before_start, ticker].notna().sum())
        for ticker in required_assets
    }
    base: dict[str, Any] = {
        "label": label,
        "assets": {
            "core": core,
            "leveraged": leveraged,
            "diversifier_candidates": list(V20_DIVERSIFIERS),
        },
        "formal_period": {"start": start, "end": end},
        "prestart_sessions": warmup,
        "required_prestart_sessions": {
            core: equity_prestart_requirement,
            leveraged: equity_prestart_requirement,
            **{ticker: 252 for ticker in V20_DIVERSIFIERS},
        },
    }
    requirements = base["required_prestart_sessions"]
    if any(warmup[ticker] < required for ticker, required in requirements.items()):
        return {
            **base,
            "status": "insufficient_warmup",
            "data_gate_passed": False,
            "failure": "；".join(
                f"{ticker} 正式期前有效日 {warmup[ticker]}/{required}"
                for ticker, required in requirements.items()
                if warmup[ticker] < required
            ),
            "economic_gates": _failed_economic_gates(),
        }, {}

    strategy_targets = diversifier_relative_strength_targets(
        panel.close,
        equity=leveraged,
        equity_weight=0.50,
        selected_count=2,
        selected_weight=0.25,
    )
    unlevered_targets = diversifier_relative_strength_targets(
        panel.close,
        equity=core,
        equity_weight=2 / 3,
        selected_count=2,
        selected_weight=1 / 6,
    )
    strategy_signals = strategy_targets.dropna(how="all")
    if strategy_signals.empty:
        return {
            **base,
            "status": "no_completed_month_signal",
            "data_gate_passed": False,
            "failure": "找不到完成 12–1 月暖機的已完成月末",
            "economic_gates": _failed_economic_gates(),
        }, {}

    initial_signal = pd.Timestamp(strategy_signals.index[0])
    initial_position = panel.close.index.get_loc(initial_signal)
    if not isinstance(initial_position, int) or initial_position + 1 >= len(panel.close.index):
        raise ValueError(f"{label} 初始訊號沒有下一個可執行交易日")
    run_start = pd.Timestamp(panel.close.index[initial_position + 1])
    signal_text = initial_signal.strftime("%Y-%m-%d")
    targets = {
        "strategy": strategy_targets,
        "fixed_v18": fixed_weight_targets(panel.close, {leveraged: 0.50, "IEF": 0.25, "GLD": 0.25}),
        "unlevered_same_policy": unlevered_targets,
        "core": buy_and_hold_targets(panel.close, core, signal_on=signal_text),
        "leveraged_buy_hold": buy_and_hold_targets(panel.close, leveraged, signal_on=signal_text),
    }

    def run(target: pd.DataFrame, name: str, cost: float) -> BacktestResult:
        full = run_backtest(
            panel,
            target,
            name=f"{label} {name}",
            cost_bps=cost,
            start=run_start,
        )
        return _slice_result(full, start, end)

    results = {key: run(target, key, primary_cost_bps) for key, target in targets.items()}
    stress = {
        key: run(targets[key], f"{key} 50bps", stress_cost_bps)
        for key in ("strategy", "core", "fixed_v18", "unlevered_same_policy")
    }
    comparison_keys = ("core", "fixed_v18", "unlevered_same_policy", "leveraged_buy_hold")
    active: dict[str, pd.Series] = {}
    comparisons: dict[str, Any] = {}
    for benchmark in comparison_keys:
        active[benchmark], comparisons[benchmark] = _active_statistics(
            results["strategy"], results[benchmark]
        )

    formal_targets = strategy_signals.loc[start:end]
    signal_integrity = _signal_execution_integrity(
        panel,
        formal_targets,
        end=end,
        required_assets=required_assets,
    )
    target_sums = formal_targets.sum(axis=1)
    target_notional = 2.0 * formal_targets[leveraged] + formal_targets[list(V20_DIVERSIFIERS)].sum(
        axis=1
    )
    selected_counts = (formal_targets[list(V20_DIVERSIFIERS)] > 0.0).sum(axis=1)
    diversifier_values = formal_targets[list(V20_DIVERSIFIERS)].to_numpy(dtype=float)
    selected_values = diversifier_values[diversifier_values > 0.0]
    realized = results["strategy"].weights
    weight_integrity = {
        **signal_integrity,
        "target_weight_sum_min": float(target_sums.min()),
        "target_weight_sum_max": float(target_sums.max()),
        "selected_diversifier_count_min": int(selected_counts.min()),
        "selected_diversifier_count_max": int(selected_counts.max()),
        "selected_diversifier_weight_min": float(selected_values.min()),
        "selected_diversifier_weight_max": float(selected_values.max()),
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
        and (selected_counts == 2).all()
        and np.isclose(selected_values, 0.25, atol=1e-8).all()
        and np.isclose(target_notional, 1.50, atol=1e-8).all()
        and weight_integrity["realized_fully_invested_fraction"] >= 0.99
        and weight_integrity["realized_minimum_asset_weight"] >= -1e-12
        and weight_integrity["realized_maximum_asset_weight"] <= 1.0 + 1e-8
    )

    latest = formal_targets.iloc[-1]
    selected_latest = [ticker for ticker in V20_DIVERSIFIERS if float(latest[ticker]) > 0.0]
    result: dict[str, Any] = {
        **base,
        "status": "completed",
        "data_gate_passed": bool(weight_integrity["passed"]),
        "period": {
            "start": start,
            "end": end,
            "sessions": int(len(results["strategy"].equity)),
            "initial_signal": signal_text,
            "initial_execution": run_start.strftime("%Y-%m-%d"),
        },
        "strategy_metrics": results["strategy"].metrics,
        "benchmark_metrics": {key: results[key].metrics for key in comparison_keys},
        "comparisons": comparisons,
        "cost_50bps": {
            "strategy_metrics": stress["strategy"].metrics,
            "core_metrics": stress["core"].metrics,
            "fixed_v18_metrics": stress["fixed_v18"].metrics,
            "unlevered_same_policy_metrics": stress["unlevered_same_policy"].metrics,
            "vs_core_cagr_difference": (
                stress["strategy"].metrics["cagr"] - stress["core"].metrics["cagr"]
            ),
            "vs_fixed_v18_cagr_difference": (
                stress["strategy"].metrics["cagr"] - stress["fixed_v18"].metrics["cagr"]
            ),
            "vs_unlevered_same_policy_cagr_difference": (
                stress["strategy"].metrics["cagr"] - stress["unlevered_same_policy"].metrics["cagr"]
            ),
        },
        "fixed_halves_vs_core": _halves(results["strategy"], results["core"], halves),
        "rolling_five_year_vs_core": _rolling_comparison(
            results["strategy"], results["core"], window=1_260
        ),
        "weight_integrity": weight_integrity,
        "signals": {
            "completed_month_end_targets_in_formal_period": int(len(formal_targets)),
            "completed_rebalances_in_formal_period": int(
                results["strategy"].diagnostics["rebalance_count"]
            ),
            "latest_completed_month_end": pd.Timestamp(formal_targets.index[-1]).strftime(
                "%Y-%m-%d"
            ),
            "latest_selected_diversifiers": selected_latest,
            "latest_target": {
                ticker: float(value) for ticker, value in latest.items() if value > 0.0
            },
            "approximate_equity_notional": 1.00,
            "diversifier_notional": 0.50,
            "total_notional": 1.50,
        },
    }
    result["economic_gates"] = _economic_gates(result)
    return result, active


def _verify_receipts(
    *,
    capital_panel: MarketPanel,
    main_panel: MarketPanel,
    v18_panel: MarketPanel,
    external_panel: MarketPanel,
    source_receipts: dict[str, dict[str, Any]],
    protocol_receipt: dict[str, Any],
    data_receipt: dict[str, Any],
    product_mapping_receipt: dict[str, Any],
    protocol_sha256: str,
) -> dict[str, Any]:
    if protocol_sha256 != V20_PROTOCOL_SHA256:
        raise ValueError("v20 協議雜湊與凍結版本不同")
    if protocol_receipt.get("protocol_sha256") != V20_PROTOCOL_SHA256:
        raise ValueError("v20 協議凍結收據雜湊不符")
    if (
        protocol_receipt.get("status")
        != "frozen_before_first_strategy_calculation_or_external_download"
    ):
        raise ValueError("v20 收據未證明先凍結再計算與下載")
    if (
        product_mapping_receipt.get("status")
        != "all_three_pairs_definition_compatible_for_formal_period"
    ):
        raise ValueError("v20 官方產品配對門檻未通過")
    if data_receipt.get("pre_registration_order_proved") is not True:
        raise ValueError("v20 資料收據未證明預先登錄順序")
    frozen_mtime = int(protocol_receipt.get("protocol_mtime_epoch", 0))
    snapshot_mtime = int(data_receipt.get("download", {}).get("snapshot_mtime_epoch", 0))
    if not 0 < frozen_mtime < snapshot_mtime:
        raise ValueError("v20 協議時間未嚴格早於外部快照")

    panels = {
        "capital": capital_panel,
        "main": main_panel,
        "v18": v18_panel,
        "external": external_panel,
    }
    checked: dict[str, Any] = {}
    for key, panel in panels.items():
        identity = V20_SOURCE_IDENTITIES[key]
        receipt = source_receipts.get(key, {})
        actual_panel = panel_fingerprint(panel)
        if actual_panel != identity["panel_sha256"]:
            raise ValueError(f"v20 {key} 面板雜湊不符")
        if receipt.get("panel_sha256") != identity["panel_sha256"]:
            raise ValueError(f"v20 {key} 面板收據雜湊不符")
        if receipt.get("archive_sha256") != identity["archive_sha256"]:
            raise ValueError(f"v20 {key} ZIP 收據雜湊不符")
        checked[key] = {
            "panel_sha256": actual_panel,
            "archive_sha256": receipt["archive_sha256"],
            "rows": int(len(panel.close)),
            "start": panel.start.strftime("%Y-%m-%d"),
            "end": panel.end.strftime("%Y-%m-%d"),
            "tickers": sorted(panel.tickers),
        }

    actual_tickers = tuple(sorted(external_panel.tickers))
    if actual_tickers != tuple(sorted(V20_EXTERNAL_TICKERS)):
        raise ValueError("v20 外部代號集合與凍結契約不同")
    external_data = data_receipt.get("snapshot", {})
    if external_data.get("panel_sha256") != V20_EXTERNAL_PANEL_SHA256:
        raise ValueError("v20 資料收據 panel 雜湊不符")
    if external_data.get("archive_sha256") != V20_EXTERNAL_ARCHIVE_SHA256:
        raise ValueError("v20 資料收據 archive 雜湊不符")
    if external_data.get("contract_ok") is not True:
        raise ValueError("v20 外部資料契約未通過")
    if external_panel.start.strftime("%Y-%m-%d") != "2006-08-03":
        raise ValueError("v20 外部面板起日不符")
    if external_panel.end.strftime("%Y-%m-%d") != V20_EXTERNAL_END:
        raise ValueError("v20 外部面板截止日不符")
    if len(external_panel.close) < 5_000:
        raise ValueError("v20 外部面板少於 5,000 列")
    return {
        "protocol_sha256": protocol_sha256,
        "protocol_mtime_epoch": frozen_mtime,
        "external_snapshot_mtime_epoch": snapshot_mtime,
        "sources": checked,
        "protocol_frozen_before_external_download_and_first_calculation": True,
        "product_mapping_gate_passed": True,
        "external_snapshot_contract_passed": True,
    }


def evaluate_diversifier_strength_research(
    capital_panel: MarketPanel,
    main_panel: MarketPanel,
    v18_panel: MarketPanel,
    external_panel: MarketPanel,
    *,
    source_receipts: dict[str, dict[str, Any]],
    protocol_receipt: dict[str, Any],
    data_receipt: dict[str, Any],
    product_mapping_receipt: dict[str, Any],
    protocol_sha256: str,
    primary_cost_bps: float = 10.0,
    stress_cost_bps: float = 50.0,
) -> dict[str, Any]:
    """Evaluate the frozen v20 rule on eight seen and three new ETF paths."""
    integrity = _verify_receipts(
        capital_panel=capital_panel,
        main_panel=main_panel,
        v18_panel=v18_panel,
        external_panel=external_panel,
        source_receipts=source_receipts,
        protocol_receipt=protocol_receipt,
        data_receipt=data_receipt,
        product_mapping_receipt=product_mapping_receipt,
        protocol_sha256=protocol_sha256,
    )
    us_design = build_v20_us_design_panel(capital_panel, main_panel)
    datasets: dict[str, Any] = {}
    active_external: dict[str, dict[str, pd.Series]] = {
        "core": {},
        "fixed_v18": {},
        "unlevered_same_policy": {},
    }

    for key, spec in V20_DESIGN_DATASETS.items():
        panel = v18_panel if key in {"developed_ex_us", "emerging_markets"} else us_design
        data, _ = _dataset_results(
            panel,
            label=spec["label"],
            core=spec["core"],
            leveraged=spec["leveraged"],
            start=spec["start"],
            end=spec["end"],
            halves=spec["halves"],
            equity_prestart_requirement=1,
            primary_cost_bps=primary_cost_bps,
            stress_cost_bps=stress_cost_bps,
        )
        datasets[key] = {**data, "evidence_role": "seen_design_diagnostic"}

    for key, spec in V20_EXTERNAL_DATASETS.items():
        data, active = _dataset_results(
            external_panel,
            label=spec["label"],
            core=spec["core"],
            leveraged=spec["leveraged"],
            start=V20_EXTERNAL_START,
            end=V20_EXTERNAL_END,
            halves=V20_EXTERNAL_HALVES,
            equity_prestart_requirement=252,
            primary_cost_bps=primary_cost_bps,
            stress_cost_bps=stress_cost_bps,
        )
        datasets[key] = {**data, "evidence_role": "new_external_daily_path"}
        for benchmark in active_external:
            if benchmark in active:
                active_external[benchmark][key] = active[benchmark]

    economic_gates = {
        f"{dataset_key}_{gate_name}": bool(passed)
        for dataset_key, data in datasets.items()
        for gate_name, passed in data["economic_gates"].items()
    }
    design_keys = tuple(V20_DESIGN_DATASETS)
    external_keys = tuple(V20_EXTERNAL_DATASETS)
    design_gates = {
        key: value
        for key, value in economic_gates.items()
        if any(key.startswith(f"{dataset}_") for dataset in design_keys)
    }
    external_gates = {
        key: value
        for key, value in economic_gates.items()
        if any(key.startswith(f"{dataset}_") for dataset in external_keys)
    }
    data_gates = {
        "frozen_source_hashes_preregistration_and_external_contract_pass": True,
        "official_product_mapping_pass": True,
        **{
            f"{key}_warmup_signal_execution_selection_and_weights_pass": bool(
                data["data_gate_passed"]
            )
            for key, data in datasets.items()
        },
    }
    paper_eligible = all(economic_gates.values()) and all(data_gates.values())

    statistical_gates: dict[str, bool] = {}
    statistical_details: dict[str, Any] = {}
    for key in external_keys:
        data = datasets[key]
        statistical_details[key] = {}
        for benchmark in active_external:
            if data["status"] != "completed":
                statistical_gates[f"{key}_vs_{benchmark}_newey_west_t_1_96"] = False
                statistical_gates[f"{key}_vs_{benchmark}_psr_95pct"] = False
                statistical_gates[f"{key}_vs_{benchmark}_global_dsr_95pct"] = False
                continue
            comparison = data["comparisons"][benchmark]
            nw = comparison["active_return_newey_west"]
            psr = comparison["active_probabilistic_sharpe"]
            dsr = comparison["active_global_deflated_sharpe"]
            statistical_gates[f"{key}_vs_{benchmark}_newey_west_t_1_96"] = bool(
                nw["t_stat"] >= 1.96
            )
            statistical_gates[f"{key}_vs_{benchmark}_psr_95pct"] = bool(psr["probability"] >= 0.95)
            statistical_gates[f"{key}_vs_{benchmark}_global_dsr_95pct"] = bool(
                dsr["probability"] >= 0.95
            )
            statistical_details[key][benchmark] = {
                "newey_west": nw,
                "probabilistic_sharpe": psr,
                "global_deflated_sharpe": dsr,
            }

    pooled: dict[str, Any] = {"gate_eligible": False}
    for benchmark, series in active_external.items():
        if len(series) == len(V20_EXTERNAL_DATASETS):
            pooled_active = pd.concat(series, axis=1, join="inner").mean(axis=1)
            pooled[f"equal_weight_active_vs_{benchmark}"] = {
                "observations": int(len(pooled_active)),
                "newey_west": newey_west_mean_test(pooled_active, max_lag=9),
                "probabilistic_sharpe": probabilistic_sharpe_ratio(
                    pooled_active, benchmark_sharpe=0.0
                ),
                "global_deflated_sharpe": deflated_sharpe_ratio(
                    pooled_active, trials=V20_GLOBAL_SEARCH_TRIALS
                ),
            }
    pooled["reason"] = "事前指定為診斷；不能覆蓋任何單一市場失敗"

    statistically_confirmed = paper_eligible and all(statistical_gates.values())
    return {
        "schema_version": 1,
        "strategy_name": "v20 固定股票曝險＋分散器 12–1 相對強弱",
        "status": (
            "historically_confirmed_pending_live"
            if statistically_confirmed
            else "paper_entry_passed_statistical_pending"
            if paper_eligible
            else "diversifier_rotation_validation_failed"
        ),
        "paper_eligible": paper_eligible,
        "statistically_confirmed": statistically_confirmed,
        "historically_confirmed": statistically_confirmed,
        "promotion_ready": False,
        "reference_trade_candidate": False,
        "promotion_effect": "create_isolated_paper_only" if paper_eligible else "none",
        "evidence_boundary": {
            "seen_design_markets": 8,
            "us_large_cap_design_years": 20,
            "external_markets": 3,
            "external_years": 10,
            "external_daily_paths_downloaded_after_v20_freeze": True,
            "official_summary_performance_seen_before_v20_freeze": True,
            "classification": "semi_independent_external_daily_path_validation_not_fully_blind",
            "cannot_claim_fully_independent_confirmation": True,
            "v19_failed_before_any_return_calculation": True,
        },
        "protocol": {
            "path": "docs/V20_DIVERSIFIER_RELATIVE_STRENGTH_PROTOCOL.md",
            "sha256": protocol_sha256,
            "global_search_trials": V20_GLOBAL_SEARCH_TRIALS,
            "rule_unchanged_from_v19": True,
            "literature_sources": [
                "https://www.aqr.com/Insights/Research/Journal-Article/Time-Series-Momentum",
                "https://papers.ssrn.com/sol3/papers.cfm?abstract_id=962461",
                "https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2607730",
            ],
        },
        "parameters": {
            "physical_weights": {
                "actual_daily_2x_equity_etf": 0.50,
                "two_selected_diversifiers_each": 0.25,
            },
            "diversifier_candidates": list(V20_DIVERSIFIERS),
            "momentum": "Close[t-21] / Close[t-252] - 1",
            "selected_count": 2,
            "tie_break": "ticker lexicographic",
            "approximate_total_notional": 1.50,
            "primary_cost_bps": primary_cost_bps,
            "stress_cost_bps": stress_cost_bps,
            "paper_candidate_if_all_entry_gates_pass": {
                "equity": {"ticker": "SSO", "weight": 0.50},
                "diversifiers": {
                    "candidates": list(V20_DIVERSIFIERS),
                    "slots": 2,
                    "weight_each": 0.25,
                },
            },
        },
        "integrity": integrity,
        "protocol_receipt": protocol_receipt,
        "data_receipt": data_receipt,
        "product_mapping_receipt": product_mapping_receipt,
        "datasets": datasets,
        "design_economic_passed_gate_count": int(sum(design_gates.values())),
        "design_economic_required_gate_count": len(design_gates),
        "external_economic_passed_gate_count": int(sum(external_gates.values())),
        "external_economic_required_gate_count": len(external_gates),
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
        "pooled_external_diagnostic": pooled,
        "forward_requirements_if_history_passes": {
            "minimum_new_sessions": 252,
            "minimum_completed_rebalances": 6,
            "after_cost_return_positive": True,
            "must_beat_same_start": [
                "SPY",
                "v18 fixed 50% SSO / 25% IEF / 25% GLD",
                "unlevered same-policy comparator",
            ],
            "max_drawdown_not_worse_than_all_three_benchmarks": True,
            "active_newey_west_t_at_least": 1.96,
            "active_psr_probability_at_least": 0.95,
            "historical_trades_may_be_backfilled": False,
        },
        "risk_disclosure": {
            "daily_objective": "2x ETFs seek daily benchmark multiples, not fixed long-horizon multiples.",
            "momentum_reversal": "The 12-1 ranking can rotate late and lose during sharp reversals.",
            "fixed_equity_risk": "Approximate equity notional stays near 100% and has no crash exit.",
            "external_market_risk": "Regional funds add currency, time-zone, fair-value, regulatory, and liquidity risks.",
        },
        "interpretation": {
            "paper_decision": (
                "All frozen design, external, and integrity gates passed; isolated Paper may start."
                if paper_eligible
                else "At least one frozen design, external, or integrity gate failed; do not create v20 Paper."
            ),
            "reference_decision": "Not reference-ready; at least 252 new Paper sessions and six completed rebalances are still required even after a historical pass.",
        },
    }
