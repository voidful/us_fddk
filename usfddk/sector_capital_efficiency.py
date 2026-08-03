from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from usfddk.engine import execute_rebalance
from usfddk.hierarchical_defense import _halves, _rolling_comparison, _slice_result
from usfddk.metrics import compute_metrics, newey_west_mean_test
from usfddk.models import BacktestResult, MarketPanel
from usfddk.strategies import buy_and_hold_targets, fixed_weight_targets
from usfddk.validation import deflated_sharpe_ratio, probabilistic_sharpe_ratio

V22_PROTOCOL_SHA256 = "e9e9f43b30833c8131889b1967b0f47c3106f34611ef37e89a9cc62df2c72254"
V22_PRODUCT_MAPPING_SHA256 = (
    "0535884a7454ef5bf508f3d29f705accceff5a33ddae2f535c2f6c53c3ce1650"
)
V22_DESIGN_SOURCE_SHA256 = (
    "3265b48d7b8cae3f595843ed9a8c2c7732e35110c8b30cdeb8671254e2aeea26"
)
V22_PANEL_SHA256 = "52450c125c53919133457fcf57c90f3d13b2ec96e42ff06a571aab2da010f749"
V22_ARCHIVE_SHA256 = "95cad4d09a5c38a2008be25189b164002c23cb40d26e88e6d7f8d6ba9440dfd7"
V22_GLOBAL_SEARCH_TRIALS = 6_124
V22_SNAPSHOT_START = "2003-01-02"
V22_SNAPSHOT_END = "2019-06-21"
V22_FORMAL_START = "2007-07-31"
V22_FORMAL_END = "2019-06-21"
V22_HALVES = (
    ("first", "2007-07-31", "2013-07-30"),
    ("second", "2013-07-31", "2019-06-21"),
)
V22_TICKERS = (
    "DIG",
    "GLD",
    "IDU",
    "IEF",
    "IYC",
    "IYE",
    "IYF",
    "IYH",
    "IYJ",
    "IYK",
    "IYM",
    "IYW",
    "ROM",
    "RXL",
    "SHY",
    "UCC",
    "UGE",
    "UPW",
    "UXI",
    "UYG",
    "UYM",
)
V22_DATASETS: dict[str, dict[str, str]] = {
    "materials": {"label": "基礎材料", "core": "IYM", "leveraged": "UYM"},
    "consumer_staples": {"label": "民生消費", "core": "IYK", "leveraged": "UGE"},
    "consumer_discretionary": {
        "label": "非必需消費",
        "core": "IYC",
        "leveraged": "UCC",
    },
    "financials": {"label": "金融", "core": "IYF", "leveraged": "UYG"},
    "health_care": {"label": "醫療", "core": "IYH", "leveraged": "RXL"},
    "industrials": {"label": "工業", "core": "IYJ", "leveraged": "UXI"},
    "energy": {"label": "能源", "core": "IYE", "leveraged": "DIG"},
    "technology": {"label": "科技", "core": "IYW", "leveraged": "ROM"},
    "utilities": {"label": "公用事業", "core": "IDU", "leveraged": "UPW"},
}


def _active_statistics(strategy: BacktestResult, benchmark: BacktestResult) -> dict[str, Any]:
    aligned = pd.concat(
        [strategy.returns.rename("strategy"), benchmark.returns.rename("benchmark")],
        axis=1,
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
        "active_global_deflated_sharpe": deflated_sharpe_ratio(
            active, trials=V22_GLOBAL_SEARCH_TRIALS
        ),
    }


def _snapshot_integrity(
    panel: MarketPanel,
    validation_receipt: dict[str, Any],
    protocol_receipt: dict[str, Any],
    product_mapping_receipt: dict[str, Any],
    data_receipt: dict[str, Any],
    design_source_receipt: dict[str, Any],
    *,
    protocol_sha256: str,
    product_mapping_sha256: str,
    design_source_sha256: str,
) -> dict[str, Any]:
    if protocol_sha256 != V22_PROTOCOL_SHA256:
        raise ValueError("v22 協議雜湊與首次產業日線下載前凍結版本不同")
    if product_mapping_sha256 != V22_PRODUCT_MAPPING_SHA256:
        raise ValueError("v22 產品映射雜湊與首次產業日線下載前凍結版本不同")
    if design_source_sha256 != V22_DESIGN_SOURCE_SHA256:
        raise ValueError("v22 引用的 v18 美國設計紀錄已改變")
    if protocol_receipt.get("protocol_sha256") != V22_PROTOCOL_SHA256:
        raise ValueError("v22 協議凍結收據雜湊不符")
    if protocol_receipt.get("product_mapping_sha256") != V22_PRODUCT_MAPPING_SHA256:
        raise ValueError("v22 協議收據的產品映射雜湊不符")
    if (
        protocol_receipt.get("status")
        != "frozen_before_first_external_daily_download_or_v22_calculation"
    ):
        raise ValueError("v22 協議收據未證明先凍結再下載與計算")
    if product_mapping_receipt.get("status") != "all_nine_pairs_definition_aligned_for_frozen_period":
        raise ValueError("v22 九組產品映射未全部通過")
    if product_mapping_receipt.get("mapping_sha256") != V22_PRODUCT_MAPPING_SHA256:
        raise ValueError("v22 產品映射收據雜湊不符")
    if data_receipt.get("pre_registration_order_proved") is not True:
        raise ValueError("v22 資料收據未證明預先登錄順序")
    if design_source_receipt.get("source_sha256") != V22_DESIGN_SOURCE_SHA256:
        raise ValueError("v22 設計來源收據雜湊不符")
    if design_source_receipt.get("source_preceded_v22_freeze") is not True:
        raise ValueError("v18 美國設計紀錄未證明早於 v22 凍結")

    frozen_mtime = int(protocol_receipt.get("protocol_mtime_epoch", 0))
    snapshot_mtime = int(data_receipt.get("download", {}).get("snapshot_mtime_epoch", 0))
    if frozen_mtime <= 0 or snapshot_mtime <= frozen_mtime:
        raise ValueError("v22 協議檔時間未早於首次外部日線快照")

    frozen_snapshot = data_receipt.get("validated_snapshot") or {}
    for receipt in (frozen_snapshot, validation_receipt):
        if receipt.get("panel_sha256") != V22_PANEL_SHA256:
            raise ValueError("v22 驗證面板雜湊不符")
        if receipt.get("archive_sha256") != V22_ARCHIVE_SHA256:
            raise ValueError("v22 驗證 ZIP 雜湊不符")
    if frozen_snapshot.get("contract_ok") is not True:
        raise ValueError("v22 資料收據的快照契約未通過")
    if (validation_receipt.get("contract") or {}).get("ok") is not True:
        raise ValueError("v22 驗證快照 manifest 契約未通過")
    jump = data_receipt.get("jump_audit") or {}
    if jump.get("audit_passed") is not True or jump.get("redownload_performed") is not False:
        raise ValueError("v22 DIG 極端行情人工稽核或單次下載約束未通過")

    actual_tickers = tuple(sorted(panel.close.columns))
    if actual_tickers != V22_TICKERS:
        raise ValueError("v22 ETF 代號與下載前協議不同")
    if panel.start.strftime("%Y-%m-%d") != V22_SNAPSHOT_START:
        raise ValueError("v22 驗證資料起點與凍結協議不同")
    if panel.end.strftime("%Y-%m-%d") != V22_SNAPSHOT_END:
        raise ValueError("v22 驗證資料終點與凍結協議不同")
    if len(panel.close) < 4_100:
        raise ValueError("v22 驗證面板少於凍結的 4,100 列")
    return {
        "protocol_sha256": protocol_sha256,
        "product_mapping_sha256": product_mapping_sha256,
        "design_source_sha256": design_source_sha256,
        "panel_sha256": V22_PANEL_SHA256,
        "archive_sha256": V22_ARCHIVE_SHA256,
        "tickers": list(actual_tickers),
        "start": panel.start.strftime("%Y-%m-%d"),
        "end": panel.end.strftime("%Y-%m-%d"),
        "rows": int(len(panel.close)),
        "snapshot_contract_ok": True,
        "official_jump_audit_passed": True,
        "protocol_frozen_before_first_external_daily_download": True,
        "protocol_mtime_epoch": frozen_mtime,
        "snapshot_mtime_epoch": snapshot_mtime,
    }


def _signal_execution_integrity(
    panel: MarketPanel, formal_targets: pd.DataFrame, required_assets: list[str]
) -> dict[str, Any]:
    completed = set(
        panel.close.loc[: pd.Timestamp(V22_FORMAL_END)]
        .groupby(panel.close.loc[: pd.Timestamp(V22_FORMAL_END)].index.to_period("M"))
        .apply(lambda frame: frame.index[-1])
    )
    missing: list[str] = []
    pending: list[str] = []
    for signal_day in formal_targets.index:
        position = panel.close.index.get_loc(signal_day)
        if not isinstance(position, int):
            missing.append(pd.Timestamp(signal_day).strftime("%Y-%m-%d"))
            continue
        if position + 1 >= len(panel.close.index):
            pending.append(pd.Timestamp(signal_day).strftime("%Y-%m-%d"))
            continue
        execution_day = panel.close.index[position + 1]
        if not all(
            frame.loc[execution_day, required_assets].notna().all()
            for frame in panel.field_map().values()
        ):
            missing.append(pd.Timestamp(execution_day).strftime("%Y-%m-%d"))
    return {
        "completed_month_end_clock": all(day in completed for day in formal_targets.index),
        "formal_signal_count": int(len(formal_targets)),
        "execution_days_with_missing_ohlcv": missing,
        "signals_pending_execution_after_data_cutoff": pending,
        "all_signal_execution_days_complete": not missing,
    }


def _economic_gates(data: dict[str, Any]) -> dict[str, bool]:
    strategy = data["strategy_metrics"]
    core = data["benchmark_metrics"]["core"]
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
    }


def _run_sparse_backtest(
    panel: MarketPanel,
    target_signals: pd.DataFrame,
    *,
    name: str,
    cost_bps: float,
    start: pd.Timestamp,
) -> BacktestResult:
    """Run sparse monthly targets with the shared execution primitive.

    Holdings are constant between trade dates, so valuing each interval as a
    matrix operation is algebraically identical to the daily engine while
    avoiding a Python loop over every session for every frozen comparison.
    """
    tickers = [ticker for ticker in target_signals.columns if ticker in panel.close]
    if not tickers:
        raise ValueError("目標權重與行情沒有共同代號")
    full_index = panel.close.index
    signals = target_signals.reindex(index=full_index, columns=tickers)
    execution = signals.shift(1)
    index = full_index[full_index >= pd.Timestamp(start)]
    if len(index) < 2:
        raise ValueError("回測期間不足")

    open_px = panel.open.loc[index, tickers]
    close_px = panel.close.loc[index, tickers]
    execution = execution.loc[index]
    trade_positions = np.flatnonzero(execution.notna().any(axis=1).to_numpy())
    shares = pd.Series(0.0, index=tickers)
    cash = 1.0
    equity = pd.Series(index=index, dtype=float, name=name)
    turnover = pd.Series(0.0, index=index, name="turnover")
    costs = pd.Series(0.0, index=index, name="cost")
    weights = pd.DataFrame(0.0, index=index, columns=tickers)

    def value_interval(left: int, right: int) -> None:
        if right <= left:
            return
        held = shares != 0.0
        if bool(held.any()):
            missing = open_px.iloc[left:right, held.to_numpy()].isna() | close_px.iloc[
                left:right, held.to_numpy()
            ].isna()
            if bool(missing.any(axis=None)):
                row = int(np.flatnonzero(missing.any(axis=1).to_numpy())[0]) + left
                missing_names = list(missing.columns[missing.iloc[row - left].to_numpy()])
                raise ValueError(f"持倉遇到缺價 {index[row].date()}: {missing_names}")
        values = close_px.iloc[left:right].fillna(0.0).mul(shares, axis=1)
        interval_equity = values.sum(axis=1) + cash
        if bool((~np.isfinite(interval_equity) | (interval_equity <= 0.0)).any()):
            bad_day = interval_equity.index[
                np.flatnonzero((~np.isfinite(interval_equity) | (interval_equity <= 0.0)).to_numpy())[0]
            ]
            raise RuntimeError(f"{bad_day.date()} 權益無效：{interval_equity.loc[bad_day]}")
        equity.iloc[left:right] = interval_equity
        weights.iloc[left:right] = values.div(interval_equity, axis=0)

    cursor = 0
    for position in trade_positions:
        value_interval(cursor, int(position))
        day = index[int(position)]
        try:
            shares, cash, day_turnover, day_cost, _ = execute_rebalance(
                shares,
                cash,
                open_px.loc[day],
                execution.loc[day],
                cost_bps=cost_bps,
            )
        except ValueError as exc:
            raise ValueError(f"{day.date()} {exc}") from exc
        turnover.loc[day] = day_turnover
        costs.loc[day] = day_cost
        cursor = int(position)
    value_interval(cursor, len(index))

    returns = equity.pct_change(fill_method=None).fillna(0.0).rename(name)
    signal_rows = signals.dropna(how="all")
    current_target = (
        signal_rows.iloc[-1].fillna(0.0)
        if len(signal_rows)
        else pd.Series(0.0, index=tickers)
    )
    diagnostics = {
        "cost_bps": float(cost_bps),
        "rebalance_count": int((turnover > 0).sum()),
        "total_cost_fraction_initial": float(costs.sum()),
        "execution_clock": "signal at close t; rebalance at adjusted open t+1",
        "engine": "sparse_interval_vectorized_shared_execution_primitive",
    }
    return BacktestResult(
        name=name,
        equity=equity,
        returns=returns,
        weights=weights,
        turnover=turnover,
        costs=costs,
        metrics=compute_metrics(equity, returns, turnover),
        current_target=current_target.sort_values(ascending=False),
        diagnostics=diagnostics,
    )


def _dataset_results(
    panel: MarketPanel,
    *,
    label: str,
    core: str,
    leveraged: str,
    primary_cost_bps: float,
    stress_cost_bps: float,
) -> tuple[dict[str, Any], dict[str, BacktestResult]]:
    required_assets = [core, leveraged, "IEF", "GLD", "SHY"]
    before_start = panel.close.index < pd.Timestamp(V22_FORMAL_START)
    warmup = {
        ticker: int(panel.close.loc[before_start, ticker].notna().sum())
        for ticker in required_assets
    }
    requirements = {core: 100, leveraged: 100, "IEF": 500, "GLD": 500, "SHY": 500}
    base: dict[str, Any] = {
        "label": label,
        "assets": {
            "core": core,
            "leveraged": leveraged,
            "duration_defensive": "IEF",
            "inflation_diversifier": "GLD",
            "short_duration_control": "SHY",
        },
        "formal_period": {"start": V22_FORMAL_START, "end": V22_FORMAL_END},
        "prestart_sessions": warmup,
        "required_prestart_sessions": requirements,
    }
    if any(warmup[ticker] < required for ticker, required in requirements.items()):
        return {
            **base,
            "status": "insufficient_prestart_history",
            "data_gate_passed": False,
            "economic_gates": {name: False for name in (
                "cagr_beats_core_25bp", "sharpe_beats_core",
                "drawdown_not_worse_than_core", "calmar_beats_core",
                "50bps_cagr_beats_core_10bp", "both_halves_cagr_beat_core_10bp",
                "rolling_wins_60pct_and_positive_median",
            )},
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
    }
    strategy_signals = targets["strategy"].dropna(how="all")
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
    formal_targets = strategy_signals.loc[V22_FORMAL_START:V22_FORMAL_END]
    signal_integrity = _signal_execution_integrity(panel, formal_targets, required_assets)

    def run(target: pd.DataFrame, name: str, cost: float) -> BacktestResult:
        full = _run_sparse_backtest(
            panel,
            target,
            name=f"{label} {name}",
            cost_bps=cost,
            start=run_start,
        )
        return _slice_result(full, V22_FORMAL_START, V22_FORMAL_END)

    results = {key: run(target, key, primary_cost_bps) for key, target in targets.items()}
    results["strategy_stress"] = run(targets["strategy"], "strategy 50bps", stress_cost_bps)
    results["core_stress"] = run(targets["core"], "core 50bps", stress_cost_bps)
    results["unlevered_stress"] = run(
        targets["unlevered_same_assets"], "unlevered 50bps", stress_cost_bps
    )

    comparison_keys = (
        "core",
        "unlevered_same_assets",
        "leveraged_50_50_ief",
        "leveraged_50_50_gld",
        "leveraged_buy_hold",
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

    data: dict[str, Any] = {
        **base,
        "status": "completed",
        "data_gate_passed": bool(weight_integrity["passed"]),
        "period": {
            "start": V22_FORMAL_START,
            "end": V22_FORMAL_END,
            "sessions": int(len(results["strategy"].equity)),
            "years": round(
                (pd.Timestamp(V22_FORMAL_END) - pd.Timestamp(V22_FORMAL_START)).days
                / 365.2425,
                2,
            ),
            "initial_signal": signal_text,
            "initial_execution": run_start.strftime("%Y-%m-%d"),
        },
        "strategy_metrics": results["strategy"].metrics,
        "benchmark_metrics": {key: results[key].metrics for key in comparison_keys},
        "comparisons": {
            key: _active_statistics(results["strategy"], results[key])
            for key in comparison_keys
        },
        "cost_50bps": {
            "strategy_metrics": results["strategy_stress"].metrics,
            "core_metrics": results["core_stress"].metrics,
            "unlevered_same_assets_metrics": results["unlevered_stress"].metrics,
            "vs_core_cagr_difference": (
                results["strategy_stress"].metrics["cagr"]
                - results["core_stress"].metrics["cagr"]
            ),
            "vs_unlevered_same_assets_cagr_difference": (
                results["strategy_stress"].metrics["cagr"]
                - results["unlevered_stress"].metrics["cagr"]
            ),
        },
        "fixed_halves_vs_core": _halves(
            results["strategy"], results["core"], V22_HALVES
        ),
        "rolling_five_year_vs_core": _rolling_comparison(
            results["strategy"], results["core"]
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
            "historical_target": {leveraged: 0.50, "IEF": 0.25, "GLD": 0.25},
            "not_a_current_trade_signal": True,
        },
    }
    data["economic_gates"] = _economic_gates(data)
    return data, results


def _pooled_result(results: dict[str, BacktestResult], name: str) -> BacktestResult:
    common = pd.concat(
        {key: result.returns for key, result in results.items()}, axis=1, join="inner"
    ).index
    returns = pd.concat(
        {key: result.returns.loc[common] for key, result in results.items()}, axis=1
    ).mean(axis=1)
    turnover = pd.concat(
        {key: result.turnover.loc[common] for key, result in results.items()}, axis=1
    ).mean(axis=1)
    costs = pd.concat(
        {key: result.costs.loc[common] for key, result in results.items()}, axis=1
    ).mean(axis=1)
    equity = (1.0 + returns.fillna(0.0)).cumprod()
    equity = (equity / float(equity.iloc[0])).rename(name)
    returns = equity.pct_change(fill_method=None).fillna(0.0).rename(name)
    return BacktestResult(
        name=name,
        equity=equity,
        returns=returns,
        weights=pd.DataFrame(index=common),
        turnover=turnover,
        costs=costs,
        metrics=compute_metrics(equity, returns, turnover),
        current_target=pd.Series(dtype=float),
        diagnostics={"equal_weight_dataset_count": len(results)},
    )


def evaluate_sector_capital_efficiency_research(
    panel: MarketPanel,
    *,
    validation_receipt: dict[str, Any],
    protocol_receipt: dict[str, Any],
    product_mapping_receipt: dict[str, Any],
    data_receipt: dict[str, Any],
    design_source_receipt: dict[str, Any],
    protocol_sha256: str,
    product_mapping_sha256: str,
    design_source_sha256: str,
    primary_cost_bps: float = 10.0,
    stress_cost_bps: float = 50.0,
) -> dict[str, Any]:
    """Evaluate the frozen v22 U.S.-sector capital-efficiency hypothesis."""
    snapshot = _snapshot_integrity(
        panel,
        validation_receipt,
        protocol_receipt,
        product_mapping_receipt,
        data_receipt,
        design_source_receipt,
        protocol_sha256=protocol_sha256,
        product_mapping_sha256=product_mapping_sha256,
        design_source_sha256=design_source_sha256,
    )
    datasets: dict[str, Any] = {}
    raw_results: dict[str, dict[str, BacktestResult]] = {}
    for key, spec in V22_DATASETS.items():
        data, results = _dataset_results(
            panel,
            label=spec["label"],
            core=spec["core"],
            leveraged=spec["leveraged"],
            primary_cost_bps=primary_cost_bps,
            stress_cost_bps=stress_cost_bps,
        )
        datasets[key] = data
        raw_results[key] = results

    individual_gates = {
        f"{dataset_key}_{gate_name}": bool(passed)
        for dataset_key, data in datasets.items()
        for gate_name, passed in data["economic_gates"].items()
    }
    gate_names = tuple(next(iter(datasets.values()))["economic_gates"])
    pass_by_gate = {
        name: int(sum(data["economic_gates"][name] for data in datasets.values()))
        for name in gate_names
    }
    pass_by_dataset = {
        key: int(sum(data["economic_gates"].values())) for key, data in datasets.items()
    }
    cagr_shortfalls = {
        key: data["strategy_metrics"]["cagr"] - data["benchmark_metrics"]["core"]["cagr"]
        for key, data in datasets.items()
    }
    drawdown_differences = {
        key: data["strategy_metrics"]["max_drawdown"]
        - data["benchmark_metrics"]["core"]["max_drawdown"]
        for key, data in datasets.items()
    }
    consistency_gates = {
        "each_gate_passes_in_at_least_6_of_9_sectors": all(
            count >= 6 for count in pass_by_gate.values()
        ),
        "at_least_6_of_9_sectors_pass_at_least_5_of_7_gates": sum(
            count >= 5 for count in pass_by_dataset.values()
        )
        >= 6,
        "individual_gate_total_at_least_45_of_63": sum(individual_gates.values()) >= 45,
        "no_sector_cagr_lags_core_more_than_2pp": min(cagr_shortfalls.values()) >= -0.02,
        "no_sector_drawdown_deeper_than_core_by_more_than_10pp": min(
            drawdown_differences.values()
        )
        >= -0.10,
    }

    pooled_results: dict[str, BacktestResult] = {}
    for result_key in (
        "strategy",
        "core",
        "unlevered_same_assets",
        "strategy_stress",
        "core_stress",
        "unlevered_stress",
    ):
        pooled_results[result_key] = _pooled_result(
            {key: results[result_key] for key, results in raw_results.items()},
            f"九產業等權 {result_key}",
        )
    pooled_strategy = pooled_results["strategy"]
    pooled_core = pooled_results["core"]
    pooled_unlevered = pooled_results["unlevered_same_assets"]
    pooled_rolling = _rolling_comparison(pooled_strategy, pooled_core)
    pooled_halves = _halves(pooled_strategy, pooled_core, V22_HALVES)
    pooled_gates = {
        "cagr_beats_core_25bp": pooled_strategy.metrics["cagr"]
        > pooled_core.metrics["cagr"] + 0.0025,
        "sharpe_beats_core": pooled_strategy.metrics["sharpe"]
        > pooled_core.metrics["sharpe"],
        "drawdown_not_worse_than_core": pooled_strategy.metrics["max_drawdown"]
        >= pooled_core.metrics["max_drawdown"],
        "calmar_beats_core": pooled_strategy.metrics["calmar"]
        > pooled_core.metrics["calmar"],
        "50bps_cagr_beats_core_10bp": pooled_results["strategy_stress"].metrics["cagr"]
        > pooled_results["core_stress"].metrics["cagr"] + 0.001,
        "both_halves_cagr_beat_core_10bp": all(
            half["cagr_difference"] > 0.001 for half in pooled_halves.values()
        ),
        "rolling_wins_60pct_and_positive_median": (
            pooled_rolling["summary"].get("cagr_win_fraction", 0.0) >= 0.60
            and pooled_rolling["summary"].get("median_cagr_difference", 0.0) > 0.0
        ),
        "cagr_beats_unlevered_same_assets_10bp": pooled_strategy.metrics["cagr"]
        > pooled_unlevered.metrics["cagr"] + 0.001,
        "50bps_cagr_beats_unlevered_same_assets_10bp": pooled_results[
            "strategy_stress"
        ].metrics["cagr"]
        > pooled_results["unlevered_stress"].metrics["cagr"] + 0.001,
    }
    pooled_active = pooled_strategy.returns - pooled_core.returns
    statistical_details = {
        "newey_west": newey_west_mean_test(pooled_active, max_lag=9),
        "probabilistic_sharpe": probabilistic_sharpe_ratio(
            pooled_active, benchmark_sharpe=0.0
        ),
        "global_deflated_sharpe": deflated_sharpe_ratio(
            pooled_active, trials=V22_GLOBAL_SEARCH_TRIALS
        ),
    }
    statistical_gates = {
        "pooled_active_newey_west_t_1_96": statistical_details["newey_west"]["t_stat"]
        >= 1.96,
        "pooled_active_psr_95pct": statistical_details["probabilistic_sharpe"][
            "probability"
        ]
        >= 0.95,
        "pooled_active_global_dsr_95pct": statistical_details[
            "global_deflated_sharpe"
        ]["probability"]
        >= 0.95,
    }
    design_gate = bool(
        design_source_receipt.get("design_passed_gate_count") == 24
        and design_source_receipt.get("design_required_gate_count") == 24
    )
    economic_gates = {
        "preexisting_six_us_broad_markets_pass_24_of_24": design_gate,
        **consistency_gates,
        **{f"pooled_{name}": bool(value) for name, value in pooled_gates.items()},
    }
    data_gates = {
        "snapshot_hash_contract_preregistration_and_jump_audit_pass": True,
        "all_nine_product_mappings_pass": bool(
            product_mapping_receipt.get("passed_pair_count") == 9
        ),
        **{
            f"{key}_prestart_execution_and_weights_pass": bool(data["data_gate_passed"])
            for key, data in datasets.items()
        },
    }
    paper_eligible = all(economic_gates.values()) and all(data_gates.values())
    statistically_confirmed = paper_eligible and all(statistical_gates.values())
    return {
        "schema_version": 1,
        "strategy_name": "v22 美國產業股債金資本效率",
        "status": (
            "historically_confirmed_pending_forward_paper"
            if statistically_confirmed
            else "paper_entry_passed_statistical_pending"
            if paper_eligible
            else "us_sector_capital_efficiency_validation_failed"
        ),
        "paper_eligible": paper_eligible,
        "statistically_confirmed": statistically_confirmed,
        "historically_confirmed": statistically_confirmed,
        "trade_ready": False,
        "configuration_visible": False,
        "reference_trade_candidate": False,
        "promotion_ready": False,
        "promotion_effect": "create_isolated_candidate_paper_only" if paper_eligible else "none",
        "evidence_boundary": {
            "rule_previously_selected_from_us_design_data": True,
            "scope_narrowed_after_v18_overseas_failure": True,
            "external_daily_paths_seen_before_freeze": False,
            "official_summary_performance_partly_seen_before_freeze": True,
            "external_us_sector_count": 9,
            "external_years": round(
                (pd.Timestamp(V22_FORMAL_END) - pd.Timestamp(V22_FORMAL_START)).days
                / 365.2425,
                2,
            ),
            "classification": "semi_independent_external_daily_path_validation_not_fully_blind",
            "cannot_claim_global_generalization": True,
        },
        "protocol": {
            "path": "docs/V22_US_SECTOR_CAPITAL_EFFICIENCY_PROTOCOL.md",
            "sha256": protocol_sha256,
            "product_mapping_path": "docs/V22_PRODUCT_MAPPING.md",
            "product_mapping_sha256": product_mapping_sha256,
            "global_search_trials": V22_GLOBAL_SEARCH_TRIALS,
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
            "primary_cost_bps": primary_cost_bps,
            "stress_cost_bps": stress_cost_bps,
            "paper_candidate_if_all_entry_gates_pass": {
                "SSO": 0.50,
                "IEF": 0.25,
                "GLD": 0.25,
            },
        },
        "snapshot": snapshot,
        "protocol_receipt": protocol_receipt,
        "product_mapping_receipt": product_mapping_receipt,
        "data_receipt": data_receipt,
        "design_source_receipt": design_source_receipt,
        "datasets": datasets,
        "individual_economic_gates": individual_gates,
        "individual_passed_gate_count": int(sum(individual_gates.values())),
        "individual_required_gate_count": len(individual_gates),
        "individual_pass_count_by_gate": pass_by_gate,
        "individual_pass_count_by_dataset": pass_by_dataset,
        "individual_cagr_difference": cagr_shortfalls,
        "individual_drawdown_difference": drawdown_differences,
        "consistency_gates": consistency_gates,
        "pooled": {
            "strategy_metrics": pooled_strategy.metrics,
            "core_metrics": pooled_core.metrics,
            "unlevered_same_assets_metrics": pooled_unlevered.metrics,
            "cost_50bps": {
                "strategy_metrics": pooled_results["strategy_stress"].metrics,
                "core_metrics": pooled_results["core_stress"].metrics,
                "unlevered_same_assets_metrics": pooled_results[
                    "unlevered_stress"
                ].metrics,
            },
            "fixed_halves_vs_core": pooled_halves,
            "rolling_five_year_vs_core": pooled_rolling,
            "economic_gates": pooled_gates,
        },
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
        "forward_requirements_if_history_passes": {
            "minimum_new_sessions": 252,
            "minimum_completed_rebalances": 6,
            "after_cost_return_positive": True,
            "must_beat_same_start": [
                "SPY",
                "two-thirds SPY plus one-sixth IEF plus one-sixth GLD",
            ],
            "max_drawdown_not_worse_than_both_benchmarks": True,
            "active_newey_west_t_at_least": 1.96,
            "active_psr_probability_at_least": 0.95,
            "historical_trades_may_be_backfilled": False,
        },
        "interpretation": {
            "paper_decision": (
                "All frozen economic, data, and governance entry gates passed; only an isolated candidate Paper may start."
                if paper_eligible
                else "At least one frozen economic, data, or governance entry gate failed; do not create v22 Paper."
            ),
            "reference_decision": "Never reference-ready from historical data alone; forward Paper and readiness gates remain mandatory.",
        },
    }
