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
    fixed_weight_targets,
    hybrid_leverage_core_targets,
)
from usfddk.validation import deflated_sharpe_ratio, probabilistic_sharpe_ratio

V21_PROTOCOL_SHA256 = "8c2d913ee36505e6bba54e8004e7b8a10248b6de644264ea29706112263ccfb7"
V21_PRODUCT_MAPPING_SHA256 = "d4b260caff14ca768469f5b18d65b15c571808343a43bbbc47fda629996e2201"
V21_GLOBAL_SEARCH_TRIALS = 6_123
V21_EXTERNAL_PANEL_SHA256 = "45f452a2eb8ed05c6f9f3f161fdccca3ed7e5dabedc3098d455293c6584f3ff8"
V21_EXTERNAL_ARCHIVE_SHA256 = "b6f6066bfdff0f0d8ce879620c9fc0d308c7ad8cedc30cd6e42c3f23e710af80"
V21_EXTERNAL_TICKERS = ("IJH", "IWM", "SHY", "UMDD", "URTY")

V21_SOURCE_IDENTITIES = {
    "capital": {
        "panel_sha256": "4c948bf6e98055823bb4b722809040eaeeb4cb0cf3606417ad6a2a5dcdaec0c4",
        "archive_sha256": "b582a9fddf22d728227d2d64e63a85f5c8dc57012e71cf96375f34b371105bad",
    },
    "three_x": {
        "panel_sha256": "57527472113333ac0fa67c900983b063652be6c112aeed477fd0b99f7fe86e6f",
        "archive_sha256": "9a61c9311e1981c95ec1f5d156915487d0c48ba6aae81ca4c1fcb5598ad017e2",
    },
    "external": {
        "panel_sha256": V21_EXTERNAL_PANEL_SHA256,
        "archive_sha256": V21_EXTERNAL_ARCHIVE_SHA256,
    },
}

V21_TWO_X_DATASETS: dict[str, dict[str, Any]] = {
    "sp500_2x": {"label": "S&P 500（2 倍實作）", "core": "SPY", "leveraged": "SSO"},
    "nasdaq100_2x": {
        "label": "Nasdaq-100（2 倍實作）",
        "core": "QQQ",
        "leveraged": "QLD",
    },
    "dow30_2x": {"label": "Dow 30（2 倍實作）", "core": "DIA", "leveraged": "DDM"},
}
V21_THREE_X_DESIGN_DATASETS: dict[str, dict[str, Any]] = {
    "sp500_3x": {"label": "S&P 500（3 倍實作）", "core": "SPY", "leveraged": "UPRO"},
    "nasdaq100_3x": {
        "label": "Nasdaq-100（3 倍實作）",
        "core": "QQQ",
        "leveraged": "TQQQ",
    },
    "dow30_3x": {"label": "Dow 30（3 倍實作）", "core": "DIA", "leveraged": "UDOW"},
}
V21_EXTERNAL_DATASETS: dict[str, dict[str, Any]] = {
    "midcap400_3x": {
        "label": "S&P MidCap 400（外部 3 倍）",
        "core": "IJH",
        "leveraged": "UMDD",
    },
    "russell2000_3x": {
        "label": "Russell 2000（外部 3 倍）",
        "core": "IWM",
        "leveraged": "URTY",
    },
}

V21_TWO_X_START = "2006-07-31"
V21_TWO_X_END = "2026-07-31"
V21_TWO_X_HALVES = (
    ("first", "2006-07-31", "2016-07-29"),
    ("second", "2016-08-01", "2026-07-31"),
)
V21_THREE_X_START = "2011-07-29"
V21_THREE_X_END = "2026-07-31"
V21_THREE_X_HALVES = (
    ("first", "2011-07-29", "2019-01-30"),
    ("second", "2019-01-31", "2026-07-31"),
)


def build_v21_three_x_design_panel(
    three_x_panel: MarketPanel, capital_panel: MarketPanel
) -> MarketPanel:
    """Attach the already-seen SHY path to the already-seen v15 3x panel."""
    three_x_columns = ["DIA", "QQQ", "SPY", "TQQQ", "UDOW", "UPRO"]
    if not set(three_x_columns).issubset(three_x_panel.close.columns):
        raise ValueError("v21 三倍設計面板缺少 v15 欄位")
    if "SHY" not in capital_panel.close.columns:
        raise ValueError("v21 三倍設計面板缺少 SHY")
    common = three_x_panel.close.index.intersection(capital_panel.close.index).sort_values()

    def joined(field: str) -> pd.DataFrame:
        return pd.concat(
            [
                three_x_panel.field_map()[field].loc[common, three_x_columns],
                capital_panel.field_map()[field].loc[common, ["SHY"]],
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
            "strategy_version": "v21",
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
        "active_probabilistic_sharpe": probabilistic_sharpe_ratio(
            active, benchmark_sharpe=0.0
        ),
        "active_global_deflated_sharpe": deflated_sharpe_ratio(
            active, trials=V21_GLOBAL_SEARCH_TRIALS
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
        "sharpe_beats_fixed_risk_on": False,
        "calmar_beats_fixed_risk_on": False,
        "drawdown_improves_fixed_risk_on_5pp": False,
        "cagr_lags_fixed_risk_on_no_more_than_50bp": False,
        "50bps_cagr_lags_fixed_risk_on_no_more_than_50bp": False,
        "cagr_beats_fixed_risk_off_10bp": False,
        "sharpe_beats_fixed_risk_off": False,
        "calmar_beats_fixed_risk_off": False,
        "50bps_cagr_beats_fixed_risk_off_10bp": False,
    }


def _economic_gates(data: dict[str, Any]) -> dict[str, bool]:
    strategy = data["strategy_metrics"]
    core = data["benchmark_metrics"]["core"]
    fixed_on = data["benchmark_metrics"]["fixed_risk_on"]
    fixed_off = data["benchmark_metrics"]["fixed_risk_off"]
    rolling = data["rolling_five_year_vs_core"]["summary"]
    stress = data["cost_50bps"]
    return {
        "cagr_beats_core_25bp": bool(strategy["cagr"] > core["cagr"] + 0.0025),
        "sharpe_beats_core": bool(strategy["sharpe"] > core["sharpe"]),
        "drawdown_not_worse_than_core": bool(
            strategy["max_drawdown"] >= core["max_drawdown"]
        ),
        "calmar_beats_core": bool(strategy["calmar"] > core["calmar"]),
        "50bps_cagr_beats_core_10bp": bool(stress["vs_core_cagr_difference"] > 0.001),
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
        "sharpe_beats_fixed_risk_on": bool(strategy["sharpe"] > fixed_on["sharpe"]),
        "calmar_beats_fixed_risk_on": bool(strategy["calmar"] > fixed_on["calmar"]),
        "drawdown_improves_fixed_risk_on_5pp": bool(
            strategy["max_drawdown"] >= fixed_on["max_drawdown"] + 0.05
        ),
        "cagr_lags_fixed_risk_on_no_more_than_50bp": bool(
            strategy["cagr"] >= fixed_on["cagr"] - 0.005
        ),
        "50bps_cagr_lags_fixed_risk_on_no_more_than_50bp": bool(
            stress["vs_fixed_risk_on_cagr_difference"] >= -0.005
        ),
        "cagr_beats_fixed_risk_off_10bp": bool(strategy["cagr"] > fixed_off["cagr"] + 0.001),
        "sharpe_beats_fixed_risk_off": bool(strategy["sharpe"] > fixed_off["sharpe"]),
        "calmar_beats_fixed_risk_off": bool(strategy["calmar"] > fixed_off["calmar"]),
        "50bps_cagr_beats_fixed_risk_off_10bp": bool(
            stress["vs_fixed_risk_off_cagr_difference"] > 0.001
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
        through_end.groupby(through_end.index.to_period("M")).apply(
            lambda frame: frame.index[-1]
        )
    )
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
        "completed_month_end_clock": bool(
            all(day in completed_month_ends for day in targets.index)
        ),
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
    multiplier: int,
    start: str,
    end: str,
    halves: tuple[tuple[str, str, str], ...],
    leveraged_prestart_requirement: int,
    primary_cost_bps: float,
    stress_cost_bps: float,
) -> tuple[dict[str, Any], dict[str, pd.Series]]:
    required_assets = [core, leveraged, "SHY"]
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
    requirements = {core: 252, leveraged: leveraged_prestart_requirement, "SHY": 252}
    base: dict[str, Any] = {
        "label": label,
        "assets": {
            "core": core,
            "leveraged": leveraged,
            "defensive": "SHY",
            "daily_target_multiplier": multiplier,
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
                if warmup[ticker] < required
            ),
            "economic_gates": _failed_economic_gates(),
        }, {}

    strategy_targets = hybrid_leverage_core_targets(
        panel.close,
        core=core,
        leveraged=leveraged,
        defensive="SHY",
        daily_target_multiplier=multiplier,
        initial_signal_before=start,
    )
    strategy_signals = strategy_targets.dropna(how="all")
    if strategy_signals.empty:
        return {
            **base,
            "status": "no_confirmed_month_signal",
            "data_gate_passed": False,
            "failure": "找不到正式期以前已確認的 200 日趨勢訊號",
            "economic_gates": _failed_economic_gates(),
        }, {}

    initial_signal = pd.Timestamp(strategy_signals.index[0])
    initial_position = panel.close.index.get_loc(initial_signal)
    if not isinstance(initial_position, int) or initial_position + 1 >= len(panel.close.index):
        raise ValueError(f"{label} 初始訊號沒有下一個可執行交易日")
    run_start = pd.Timestamp(panel.close.index[initial_position + 1])
    signal_text = initial_signal.strftime("%Y-%m-%d")
    leveraged_weight = 0.60 / multiplier
    fixed_on_weights = {
        core: 0.60,
        leveraged: leveraged_weight,
        "SHY": 0.40 - leveraged_weight,
    }
    fixed_off_weights = {core: 0.60, leveraged: 0.0, "SHY": 0.40}
    targets = {
        "strategy": strategy_targets,
        "core": buy_and_hold_targets(panel.close, core, signal_on=signal_text),
        "fixed_risk_on": fixed_weight_targets(
            panel.close, fixed_on_weights, signal_on=signal_text
        ),
        "fixed_risk_off": fixed_weight_targets(
            panel.close, fixed_off_weights, signal_on=signal_text
        ),
        "leveraged_buy_hold": buy_and_hold_targets(
            panel.close, leveraged, signal_on=signal_text
        ),
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
        for key in ("strategy", "core", "fixed_risk_on", "fixed_risk_off")
    }
    comparison_keys = ("core", "fixed_risk_on", "fixed_risk_off", "leveraged_buy_hold")
    active: dict[str, pd.Series] = {}
    comparisons: dict[str, Any] = {}
    for benchmark in comparison_keys:
        active[benchmark], comparisons[benchmark] = _active_statistics(
            results["strategy"], results[benchmark]
        )

    formal_targets = strategy_signals.loc[start:end]
    integrity = _signal_execution_integrity(
        panel,
        formal_targets,
        end=end,
        required_assets=required_assets,
    )
    target_sums = formal_targets.sum(axis=1)
    target_notional = formal_targets[core] + multiplier * formal_targets[leveraged]
    allowed_leveraged = np.isclose(formal_targets[leveraged], 0.0, atol=1e-8) | np.isclose(
        formal_targets[leveraged], leveraged_weight, atol=1e-8
    )
    expected_shy = np.where(
        np.isclose(formal_targets[leveraged], leveraged_weight, atol=1e-8),
        0.40 - leveraged_weight,
        0.40,
    )
    realized = results["strategy"].weights
    weight_integrity = {
        **integrity,
        "target_weight_sum_min": float(target_sums.min()),
        "target_weight_sum_max": float(target_sums.max()),
        "target_core_weight_min": float(formal_targets[core].min()),
        "target_core_weight_max": float(formal_targets[core].max()),
        "target_leveraged_weight_min": float(formal_targets[leveraged].min()),
        "target_leveraged_weight_max": float(formal_targets[leveraged].max()),
        "target_equity_notional_min": float(target_notional.min()),
        "target_equity_notional_max": float(target_notional.max()),
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
        and np.isclose(formal_targets[core], 0.60, atol=1e-8).all()
        and allowed_leveraged.all()
        and np.isclose(formal_targets["SHY"], expected_shy, atol=1e-8).all()
        and np.isclose(
            target_notional.to_numpy(dtype=float)[:, None],
            np.array([0.60, 1.20], dtype=float)[None, :],
            atol=1e-8,
        )
        .any(axis=1)
        .all()
        and weight_integrity["realized_fully_invested_fraction"] >= 0.99
        and weight_integrity["realized_minimum_asset_weight"] >= -1e-12
        and weight_integrity["realized_maximum_asset_weight"] <= 1.0 + 1e-8
    )

    latest = formal_targets.iloc[-1]
    latest_notional = float(latest[core] + multiplier * latest[leveraged])
    latest_state = "risk_on" if float(latest[leveraged]) > 0.0 else "risk_off"
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
            "fixed_risk_on_metrics": stress["fixed_risk_on"].metrics,
            "fixed_risk_off_metrics": stress["fixed_risk_off"].metrics,
            "vs_core_cagr_difference": (
                stress["strategy"].metrics["cagr"] - stress["core"].metrics["cagr"]
            ),
            "vs_fixed_risk_on_cagr_difference": (
                stress["strategy"].metrics["cagr"]
                - stress["fixed_risk_on"].metrics["cagr"]
            ),
            "vs_fixed_risk_off_cagr_difference": (
                stress["strategy"].metrics["cagr"]
                - stress["fixed_risk_off"].metrics["cagr"]
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
            "latest_state": latest_state,
            "latest_target": {
                ticker: float(value) for ticker, value in latest.items() if value > 0.0
            },
            "approximate_equity_notional": latest_notional,
        },
    }
    result["economic_gates"] = _economic_gates(result)
    return result, active


def _verify_receipts(
    *,
    capital_panel: MarketPanel,
    three_x_panel: MarketPanel,
    external_panel: MarketPanel,
    source_receipts: dict[str, dict[str, Any]],
    protocol_receipt: dict[str, Any],
    data_receipt: dict[str, Any],
    product_mapping_receipt: dict[str, Any],
    protocol_sha256: str,
    product_mapping_sha256: str,
) -> dict[str, Any]:
    if protocol_sha256 != V21_PROTOCOL_SHA256:
        raise ValueError("v21 協議雜湊與凍結版本不同")
    if product_mapping_sha256 != V21_PRODUCT_MAPPING_SHA256:
        raise ValueError("v21 產品稽核雜湊與凍結版本不同")
    if protocol_receipt.get("protocol_sha256") != V21_PROTOCOL_SHA256:
        raise ValueError("v21 協議凍結收據雜湊不符")
    if protocol_receipt.get("product_mapping_sha256") != V21_PRODUCT_MAPPING_SHA256:
        raise ValueError("v21 協議收據內產品稽核雜湊不符")
    if (
        protocol_receipt.get("status")
        != "frozen_before_first_v21_external_daily_download_or_strategy_calculation"
    ):
        raise ValueError("v21 收據未證明先凍結再下載與計算")
    if product_mapping_receipt.get("gate_passed") is not True:
        raise ValueError("v21 官方產品配對門檻未通過")
    if data_receipt.get("pre_registration_order_proved") is not True:
        raise ValueError("v21 資料收據未證明預先登錄順序")
    frozen_mtime = int(protocol_receipt.get("protocol_mtime_epoch", 0))
    mapping_mtime = int(protocol_receipt.get("product_mapping_mtime_epoch", 0))
    snapshot_mtime = int(data_receipt.get("download", {}).get("snapshot_mtime_epoch", 0))
    if not 0 < frozen_mtime < snapshot_mtime or not 0 < mapping_mtime < snapshot_mtime:
        raise ValueError("v21 協議或產品稽核時間未嚴格早於外部快照")

    panels = {
        "capital": capital_panel,
        "three_x": three_x_panel,
        "external": external_panel,
    }
    checked: dict[str, Any] = {}
    for key, panel in panels.items():
        identity = V21_SOURCE_IDENTITIES[key]
        receipt = source_receipts.get(key, {})
        actual_panel = panel_fingerprint(panel)
        if actual_panel != identity["panel_sha256"]:
            raise ValueError(f"v21 {key} 面板雜湊不符")
        if receipt.get("panel_sha256") != identity["panel_sha256"]:
            raise ValueError(f"v21 {key} 面板收據雜湊不符")
        if receipt.get("archive_sha256") != identity["archive_sha256"]:
            raise ValueError(f"v21 {key} ZIP 收據雜湊不符")
        checked[key] = {
            "panel_sha256": actual_panel,
            "archive_sha256": receipt["archive_sha256"],
            "rows": int(len(panel.close)),
            "start": panel.start.strftime("%Y-%m-%d"),
            "end": panel.end.strftime("%Y-%m-%d"),
            "tickers": sorted(panel.tickers),
        }

    if tuple(sorted(external_panel.tickers)) != tuple(sorted(V21_EXTERNAL_TICKERS)):
        raise ValueError("v21 外部代號集合與凍結契約不同")
    external_data = data_receipt.get("snapshot", {})
    if external_data.get("panel_sha256") != V21_EXTERNAL_PANEL_SHA256:
        raise ValueError("v21 資料收據 panel 雜湊不符")
    if external_data.get("archive_sha256") != V21_EXTERNAL_ARCHIVE_SHA256:
        raise ValueError("v21 資料收據 archive 雜湊不符")
    if external_data.get("contract_ok") is not True:
        raise ValueError("v21 外部資料契約未通過")
    if external_panel.start.strftime("%Y-%m-%d") != "2008-01-02":
        raise ValueError("v21 外部面板起日不符")
    if external_panel.end.strftime("%Y-%m-%d") != V21_THREE_X_END:
        raise ValueError("v21 外部面板截止日不符")
    if len(external_panel.close) < 4_650:
        raise ValueError("v21 外部面板少於 4,650 列")
    return {
        "protocol_sha256": protocol_sha256,
        "product_mapping_sha256": product_mapping_sha256,
        "protocol_mtime_epoch": frozen_mtime,
        "product_mapping_mtime_epoch": mapping_mtime,
        "external_snapshot_mtime_epoch": snapshot_mtime,
        "sources": checked,
        "protocol_and_mapping_frozen_before_external_download_and_first_calculation": True,
        "product_mapping_gate_passed": True,
        "external_snapshot_contract_passed": True,
    }


def evaluate_hybrid_leverage_core_research(
    capital_panel: MarketPanel,
    three_x_panel: MarketPanel,
    external_panel: MarketPanel,
    *,
    source_receipts: dict[str, dict[str, Any]],
    protocol_receipt: dict[str, Any],
    data_receipt: dict[str, Any],
    product_mapping_receipt: dict[str, Any],
    protocol_sha256: str,
    product_mapping_sha256: str,
    primary_cost_bps: float = 10.0,
    stress_cost_bps: float = 50.0,
) -> dict[str, Any]:
    """Evaluate the single frozen v21 rule on six seen and two external paths."""
    integrity = _verify_receipts(
        capital_panel=capital_panel,
        three_x_panel=three_x_panel,
        external_panel=external_panel,
        source_receipts=source_receipts,
        protocol_receipt=protocol_receipt,
        data_receipt=data_receipt,
        product_mapping_receipt=product_mapping_receipt,
        protocol_sha256=protocol_sha256,
        product_mapping_sha256=product_mapping_sha256,
    )
    three_x_design = build_v21_three_x_design_panel(three_x_panel, capital_panel)
    datasets: dict[str, Any] = {}
    active_external: dict[str, dict[str, pd.Series]] = {
        "core": {},
        "fixed_risk_on": {},
        "fixed_risk_off": {},
    }

    for key, spec in V21_TWO_X_DATASETS.items():
        data, _ = _dataset_results(
            capital_panel,
            label=spec["label"],
            core=spec["core"],
            leveraged=spec["leveraged"],
            multiplier=2,
            start=V21_TWO_X_START,
            end=V21_TWO_X_END,
            halves=V21_TWO_X_HALVES,
            leveraged_prestart_requirement=20,
            primary_cost_bps=primary_cost_bps,
            stress_cost_bps=stress_cost_bps,
        )
        datasets[key] = {**data, "evidence_role": "seen_20y_2x_design_diagnostic"}

    for key, spec in V21_THREE_X_DESIGN_DATASETS.items():
        data, _ = _dataset_results(
            three_x_design,
            label=spec["label"],
            core=spec["core"],
            leveraged=spec["leveraged"],
            multiplier=3,
            start=V21_THREE_X_START,
            end=V21_THREE_X_END,
            halves=V21_THREE_X_HALVES,
            leveraged_prestart_requirement=252,
            primary_cost_bps=primary_cost_bps,
            stress_cost_bps=stress_cost_bps,
        )
        datasets[key] = {**data, "evidence_role": "seen_15y_3x_implementation_sensitivity"}

    for key, spec in V21_EXTERNAL_DATASETS.items():
        data, active = _dataset_results(
            external_panel,
            label=spec["label"],
            core=spec["core"],
            leveraged=spec["leveraged"],
            multiplier=3,
            start=V21_THREE_X_START,
            end=V21_THREE_X_END,
            halves=V21_THREE_X_HALVES,
            leveraged_prestart_requirement=252,
            primary_cost_bps=primary_cost_bps,
            stress_cost_bps=stress_cost_bps,
        )
        datasets[key] = {**data, "evidence_role": "new_external_daily_path_semi_independent"}
        for benchmark in active_external:
            if benchmark in active:
                active_external[benchmark][key] = active[benchmark]

    economic_gates = {
        f"{dataset_key}_{gate_name}": bool(passed)
        for dataset_key, data in datasets.items()
        for gate_name, passed in data["economic_gates"].items()
    }
    design_keys = (*V21_TWO_X_DATASETS, *V21_THREE_X_DESIGN_DATASETS)
    external_keys = tuple(V21_EXTERNAL_DATASETS)
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
            f"{key}_warmup_signal_execution_and_weights_pass": bool(
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

    pooled: dict[str, Any] = {"gate_eligible": False}
    for benchmark, series in active_external.items():
        if len(series) == len(V21_EXTERNAL_DATASETS):
            pooled_active = pd.concat(series, axis=1, join="inner").mean(axis=1)
            pooled[f"equal_weight_active_vs_{benchmark}"] = {
                "observations": int(len(pooled_active)),
                "newey_west": newey_west_mean_test(pooled_active, max_lag=9),
                "probabilistic_sharpe": probabilistic_sharpe_ratio(
                    pooled_active, benchmark_sharpe=0.0
                ),
                "global_deflated_sharpe": deflated_sharpe_ratio(
                    pooled_active, trials=V21_GLOBAL_SEARCH_TRIALS
                ),
            }
    pooled["reason"] = "事前指定為診斷；不能覆蓋任何單一外部市場失敗"

    statistically_confirmed = paper_eligible and all(statistical_gates.values())
    status = (
        "historical_entry_passed_forward_paper_required"
        if paper_eligible
        else "hybrid_leverage_core_validation_failed"
    )
    return {
        "schema_version": 1,
        "strategy_name": "v21 常駐 60% 核心＋兩月確認受控槓桿",
        "strategy_version": "v21",
        "status": status,
        "paper_eligible": bool(paper_eligible),
        "paper_state_created": False,
        "statistically_confirmed": bool(statistically_confirmed),
        "trade_ready": False,
        "configuration_visible": False,
        "promotion_ready": False,
        "reference_trade_candidate": False,
        "promotion_effect": "create_isolated_paper_only" if paper_eligible else "none",
        "global_search_trials": V21_GLOBAL_SEARCH_TRIALS,
        "design_economic_passed_gate_count": int(sum(design_gates.values())),
        "design_economic_required_gate_count": int(len(design_gates)),
        "external_economic_passed_gate_count": int(sum(external_gates.values())),
        "external_economic_required_gate_count": int(len(external_gates)),
        "economic_passed_gate_count": int(sum(economic_gates.values())),
        "economic_required_gate_count": int(len(economic_gates)),
        "data_passed_gate_count": int(sum(data_gates.values())),
        "data_required_gate_count": int(len(data_gates)),
        "statistical_passed_gate_count": int(sum(statistical_gates.values())),
        "statistical_required_gate_count": int(len(statistical_gates)),
        "paper_entry_passed_gate_count": int(
            sum(economic_gates.values()) + sum(data_gates.values())
        ),
        "paper_entry_required_gate_count": int(len(economic_gates) + len(data_gates)),
        "protocol": {
            "path": "docs/V21_HYBRID_LEVERAGE_CORE_PROTOCOL.md",
            "sha256": protocol_sha256,
            "frozen_before_external_download": True,
        },
        "product_mapping": {
            "path": "docs/V21_PRODUCT_MAPPING.md",
            "sha256": product_mapping_sha256,
            "gate_passed": True,
        },
        "snapshot": {
            "path": data_receipt["snapshot"]["path"],
            "panel_sha256": V21_EXTERNAL_PANEL_SHA256,
            "archive_sha256": V21_EXTERNAL_ARCHIVE_SHA256,
        },
        "evidence_boundary": {
            "seen_diagnostic_datasets": list(design_keys),
            "external_daily_path_datasets": list(external_keys),
            "official_external_summary_performance_seen_before_freeze": True,
            "external_classification": "semi_independent_daily_path_validation_not_fully_blind",
            "external_20_year_claim_allowed": False,
        },
        "integrity": integrity,
        "datasets": datasets,
        "economic_gates": economic_gates,
        "data_gates": data_gates,
        "statistical_gates": statistical_gates,
        "statistical_details": statistical_details,
        "pooled_external_diagnostic": pooled,
        "paper_gate": {
            "approved": bool(paper_eligible),
            "requires_economic_gates": len(economic_gates),
            "requires_data_gates": len(data_gates),
            "statistics_required_for_historical_confirmation": True,
            "paper_strategy_if_approved": {
                "implementation": "S&P 500 actual 2x",
                "risk_on": {"SPY": 0.60, "SSO": 0.30, "SHY": 0.10},
                "risk_off": {"SPY": 0.60, "SHY": 0.40},
            },
            "state_path": "artifacts/paper_v21_state.json",
            "state_created": False,
        },
        "decision": (
            "歷史經濟與資料入口全過；只准建立隔離 Paper，尚不可參考實金交易。"
            if paper_eligible
            else "至少一項凍結經濟或資料門檻失敗；不建立 v21 Paper，不顯示可照抄配置。"
        ),
    }
