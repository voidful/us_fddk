from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from usfddk.data import panel_fingerprint
from usfddk.metrics import compute_metrics, newey_west_mean_test
from usfddk.models import BacktestResult, MarketPanel
from usfddk.validation import deflated_sharpe_ratio, probabilistic_sharpe_ratio

V23_PROTOCOL_SHA256 = "083583b5b9b35a3384ff72cde50e9d0aa6aa3a8986df48a88564cce0df62ae25"
V23_PRODUCT_MAPPING_SHA256 = (
    "2ed2f3d15279878f81f758ae1b565023c06b7550dffc62d86651c1f2be8f4eea"
)
V23_GLOBAL_SEARCH_TRIALS = 6_130
V23_DESIGN_PANEL_SHA256 = (
    "4c948bf6e98055823bb4b722809040eaeeb4cb0cf3606417ad6a2a5dcdaec0c4"
)
V23_DESIGN_ARCHIVE_SHA256 = (
    "b582a9fddf22d728227d2d64e63a85f5c8dc57012e71cf96375f34b371105bad"
)
V23_KMLM_PANEL_SHA256 = (
    "a7826ecd81e7ebb18ee43c41f0db5284ab68168b71bd5ffc46472196b7e3b9cb"
)
V23_KMLM_ARCHIVE_SHA256 = (
    "80fd1d5483d211958881086472bc9c039f708ee9f2b0a175aa9c15a574d2c42d"
)
V23_FMF_PANEL_SHA256 = (
    "42ecc0b81b89f15445ef3ec112b86f74a7452705a49de64d263d3c9375bd59d5"
)
V23_FMF_ARCHIVE_SHA256 = (
    "ee3178c68305badf2280d10c07f4aa4dffc4850d2bfe7ec8d584278b02277369"
)
V23_KFA_PDF_SHA256 = (
    "2843db7a80c0b25020f6a192b56f693d32766ec1cf148826529f6100e01e72bd"
)
V23_KFA_CSV_SHA256 = (
    "ae84957a0418fa42c395a0664e2aa4e8805d668e7d83e35208f3822b04b8d1c6"
)
V23_LONG_START = "2006-06-30"
V23_LONG_END = "2026-06-30"
V23_KMLM_START = "2020-12-31"
V23_KMLM_END = "2026-07-31"
V23_FMF_START = "2013-08-30"
V23_FMF_END = "2026-07-31"
V23_KFA_ANNUAL_DRAG = 0.0105


def _sha256(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _month_end_prices(
    panel: MarketPanel,
    tickers: list[str],
    *,
    start: str,
    end: str,
) -> pd.DataFrame:
    close = panel.close.loc[start:end, tickers]
    if close.empty:
        raise ValueError(f"月末價格區間為空：{start}–{end}")
    positions = close.groupby(close.index.to_period("M"), sort=True).tail(1)
    if positions.isna().any(axis=None):
        missing = positions.columns[positions.isna().any()].tolist()
        raise ValueError(f"月末價格缺值：{missing}")
    if positions.index[0].strftime("%Y-%m-%d") != start:
        raise ValueError(f"月末起點 {positions.index[0].date()} != 凍結起點 {start}")
    if positions.index[-1].strftime("%Y-%m-%d") != end:
        raise ValueError(f"月末終點 {positions.index[-1].date()} != 凍結終點 {end}")
    periods = positions.index.to_period("M")
    expected = pd.period_range(periods[0], periods[-1], freq="M")
    if not periods.equals(expected):
        missing = expected.difference(periods).astype(str).tolist()
        raise ValueError(f"月末價格月份不連續：{missing}")
    return positions.astype(float)


def _run_monthly_portfolio(
    asset_returns: pd.DataFrame,
    target_weights: dict[str, float],
    *,
    name: str,
    start_equity_date: str,
    cost_bps: float,
    rebalance_monthly: bool,
) -> BacktestResult:
    assets = list(target_weights)
    returns = asset_returns.reindex(columns=assets).astype(float)
    if returns.empty or returns.isna().any(axis=None):
        raise ValueError(f"{name} 月報酬缺值")
    target = pd.Series(target_weights, dtype=float).reindex(assets)
    if not np.isclose(float(target.sum()), 1.0, atol=1e-12):
        raise ValueError(f"{name} 目標權重合計不是 100%")
    if bool((target < 0).any()):
        raise ValueError(f"{name} 不允許負 ETF 權重")

    start_stamp = pd.Timestamp(start_equity_date)
    if not start_stamp.to_period("M") + 1 == returns.index[0].to_period("M"):
        raise ValueError(f"{name} 起始權益日與第一個報酬月不連續")
    equity_index = pd.DatetimeIndex([start_stamp, *returns.index])
    equity = pd.Series(index=equity_index, dtype=float, name=name)
    net_returns = pd.Series(0.0, index=equity_index, name=name)
    turnover = pd.Series(0.0, index=equity_index, name="turnover")
    costs = pd.Series(0.0, index=equity_index, name="cost")
    weights = pd.DataFrame(0.0, index=equity_index, columns=assets)
    equity.iloc[0] = 1.0
    current_weights = pd.Series(0.0, index=assets)
    cost_rate = float(cost_bps) / 10_000.0

    for position, (date, row) in enumerate(returns.iterrows(), start=1):
        trade = position == 1 or rebalance_monthly
        start_weights = target if trade else current_weights
        traded = float((target - current_weights).abs().sum()) if trade else 0.0
        prior_equity = float(equity.iloc[position - 1])
        cost = prior_equity * traded * cost_rate
        investable = prior_equity - cost
        gross_return = float((start_weights * row).sum())
        ending_equity = investable * (1.0 + gross_return)
        if not np.isfinite(ending_equity) or ending_equity <= 0:
            raise RuntimeError(f"{name} {date.date()} 權益無效")
        end_values = start_weights * (1.0 + row)
        denominator = float(end_values.sum())
        if denominator <= 0:
            raise RuntimeError(f"{name} {date.date()} 月末持倉價值無效")
        current_weights = end_values / denominator
        equity.iloc[position] = ending_equity
        net_returns.iloc[position] = ending_equity / prior_equity - 1.0
        turnover.iloc[position] = traded
        costs.iloc[position] = cost
        weights.iloc[position] = current_weights

    metrics = compute_metrics(equity, net_returns, turnover, periods_per_year=12)
    metrics["worst_month"] = float(net_returns.iloc[1:].min())
    return BacktestResult(
        name=name,
        equity=equity,
        returns=net_returns,
        weights=weights,
        turnover=turnover,
        costs=costs,
        metrics=metrics,
        current_target=target.sort_values(ascending=False),
        diagnostics={
            "cost_bps": float(cost_bps),
            "rebalance_count": int((turnover > 0).sum()),
            "total_cost_fraction_initial": float(costs.sum()),
            "execution_clock": "month-start fixed target; month-end total return",
            "engine": "monthly_total_return_with_drift_and_two_sided_turnover",
            "rebalance_monthly": bool(rebalance_monthly),
        },
    )


def _slice_monthly(
    result: BacktestResult, start_position: int, end_position: int
) -> BacktestResult:
    dates = result.equity.index[start_position : end_position + 1]
    if len(dates) < 2:
        raise ValueError("月度切片不足")
    equity = (result.equity.loc[dates] / float(result.equity.loc[dates].iloc[0])).rename(
        result.name
    )
    returns = equity.pct_change(fill_method=None).fillna(0.0).rename(result.name)
    turnover = result.turnover.loc[dates].copy()
    costs = result.costs.loc[dates].copy()
    weights = result.weights.loc[dates].copy()
    metrics = compute_metrics(equity, returns, turnover, periods_per_year=12)
    metrics["worst_month"] = float(returns.iloc[1:].min())
    return BacktestResult(
        name=result.name,
        equity=equity,
        returns=returns,
        weights=weights,
        turnover=turnover,
        costs=costs,
        metrics=metrics,
        current_target=result.current_target,
        diagnostics={**result.diagnostics, "monthly_slice": True},
    )


def _comparison(strategy: BacktestResult, benchmark: BacktestResult) -> dict[str, Any]:
    aligned = pd.concat(
        [strategy.returns.rename("strategy"), benchmark.returns.rename("benchmark")],
        axis=1,
    ).dropna()
    active = (aligned["strategy"] - aligned["benchmark"]).iloc[1:]
    return {
        "cagr_difference": strategy.metrics["cagr"] - benchmark.metrics["cagr"],
        "sharpe_difference": strategy.metrics["sharpe"] - benchmark.metrics["sharpe"],
        "drawdown_improvement": (
            strategy.metrics["max_drawdown"] - benchmark.metrics["max_drawdown"]
        ),
        "calmar_difference": strategy.metrics["calmar"] - benchmark.metrics["calmar"],
        "active_return_newey_west": newey_west_mean_test(
            active, max_lag=6, periods_per_year=12
        ),
        "active_probabilistic_sharpe": probabilistic_sharpe_ratio(
            active, benchmark_sharpe=0.0, periods_per_year=12
        ),
        "active_global_deflated_sharpe": deflated_sharpe_ratio(
            active, trials=V23_GLOBAL_SEARCH_TRIALS, periods_per_year=12
        ),
    }


def _halves(strategy: BacktestResult, benchmark: BacktestResult) -> dict[str, Any]:
    months = len(strategy.equity) - 1
    split = months // 2
    slices = {
        "first": (0, split),
        "second": (split, months),
    }
    output: dict[str, Any] = {}
    for key, (start, end) in slices.items():
        left = _slice_monthly(strategy, start, end)
        right = _slice_monthly(benchmark, start, end)
        output[key] = {
            "start": left.equity.index[0].strftime("%Y-%m-%d"),
            "end": left.equity.index[-1].strftime("%Y-%m-%d"),
            "months": int(len(left.equity) - 1),
            "strategy_metrics": left.metrics,
            "benchmark_metrics": right.metrics,
            "cagr_difference": left.metrics["cagr"] - right.metrics["cagr"],
        }
    return output


def _rolling_comparison(
    strategy: BacktestResult,
    benchmark: BacktestResult,
    *,
    window_months: int = 60,
) -> dict[str, Any]:
    rows: list[dict[str, float | str]] = []
    for end_position in range(window_months, len(strategy.equity)):
        start_position = end_position - window_months
        left = _slice_monthly(strategy, start_position, end_position)
        right = _slice_monthly(benchmark, start_position, end_position)
        rows.append(
            {
                "start": left.equity.index[0].strftime("%Y-%m-%d"),
                "end": left.equity.index[-1].strftime("%Y-%m-%d"),
                "cagr_difference": left.metrics["cagr"] - right.metrics["cagr"],
            }
        )
    if not rows:
        return {"window_months": window_months, "series": [], "summary": {}}
    differences = pd.Series([float(row["cagr_difference"]) for row in rows])
    return {
        "window_months": window_months,
        "series": rows,
        "summary": {
            "windows": int(len(rows)),
            "minimum_cagr_edge": 0.001,
            "cagr_win_fraction": float((differences > 0.001).mean()),
            "median_cagr_difference": float(differences.median()),
            "worst_cagr_difference": float(differences.min()),
            "best_cagr_difference": float(differences.max()),
        },
    }


def _load_kfa_monthly(
    csv_path: str | Path,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    if _sha256(csv_path) != V23_KFA_CSV_SHA256:
        raise ValueError("v23 KFA 月報酬 CSV 雜湊不符")
    frame = pd.read_csv(csv_path, dtype={"month": str, "method_regime": str})
    required = {"month", "gross_return", "published_year_return", "method_regime"}
    if set(frame.columns) != required:
        raise ValueError("v23 KFA 月報酬 CSV 欄位不符")
    if frame["month"].duplicated().any():
        raise ValueError("v23 KFA 月報酬月份重複")
    periods = pd.PeriodIndex(frame["month"], freq="M")
    if not periods.equals(pd.period_range(periods.min(), periods.max(), freq="M")):
        raise ValueError("v23 KFA 月報酬月份不連續")
    frame = frame.set_index(periods).drop(columns="month")
    formal = frame.loc["2006-07":"2026-06"].copy()
    if len(formal) != 240:
        raise ValueError(f"v23 KFA 正式月數 {len(formal)} != 240")
    if bool((formal.index < pd.Period("2005-01", freq="M")).any()):
        raise ValueError("v23 正式 KFA 月報酬誤用 2005 前舊方法")

    annual_differences: dict[str, float] = {}
    for year, group in frame.groupby(frame.index.year):
        compounded = float((1.0 + group["gross_return"]).prod() - 1.0)
        published = float(group["published_year_return"].iloc[0])
        annual_differences[str(year)] = compounded - published
    max_abs_difference = max(abs(value) for value in annual_differences.values())
    if max_abs_difference > 0.0015:
        raise ValueError("v23 KFA 月報酬複利與官方年度欄超過凍結容差")
    return frame, {
        "rows": int(len(frame)),
        "start_month": str(frame.index.min()),
        "end_month": str(frame.index.max()),
        "formal_rows": int(len(formal)),
        "maximum_absolute_annual_rounding_difference": float(max_abs_difference),
        "annual_compounding_check_passed": True,
    }


def _return_frame_from_prices(prices: pd.DataFrame) -> pd.DataFrame:
    returns = prices.pct_change(fill_method=None).iloc[1:]
    if returns.isna().any(axis=None):
        raise ValueError("實際 ETF 月報酬含缺值")
    return returns


def _evaluate_period(
    asset_returns: pd.DataFrame,
    *,
    diversifier: str,
    start_equity_date: str,
    primary_cost_bps: float,
    stress_cost_bps: float,
    include_unlevered: bool,
) -> tuple[dict[str, Any], dict[str, BacktestResult]]:
    strategy = _run_monthly_portfolio(
        asset_returns[["SSO", diversifier]],
        {"SSO": 0.5, diversifier: 0.5},
        name=f"50% SSO / 50% {diversifier}",
        start_equity_date=start_equity_date,
        cost_bps=primary_cost_bps,
        rebalance_monthly=True,
    )
    strategy_stress = _run_monthly_portfolio(
        asset_returns[["SSO", diversifier]],
        {"SSO": 0.5, diversifier: 0.5},
        name=f"50% SSO / 50% {diversifier} 50bps",
        start_equity_date=start_equity_date,
        cost_bps=stress_cost_bps,
        rebalance_monthly=True,
    )
    spy = _run_monthly_portfolio(
        asset_returns[["SPY"]],
        {"SPY": 1.0},
        name="SPY",
        start_equity_date=start_equity_date,
        cost_bps=primary_cost_bps,
        rebalance_monthly=False,
    )
    spy_stress = _run_monthly_portfolio(
        asset_returns[["SPY"]],
        {"SPY": 1.0},
        name="SPY 50bps",
        start_equity_date=start_equity_date,
        cost_bps=stress_cost_bps,
        rebalance_monthly=False,
    )
    matched = _run_monthly_portfolio(
        asset_returns[["SSO", "SHY"]],
        {"SSO": 0.5, "SHY": 0.5},
        name="50% SSO / 50% SHY",
        start_equity_date=start_equity_date,
        cost_bps=primary_cost_bps,
        rebalance_monthly=True,
    )
    results = {
        "strategy": strategy,
        "strategy_stress": strategy_stress,
        "spy": spy,
        "spy_stress": spy_stress,
        "matched": matched,
    }
    if include_unlevered:
        results["unlevered"] = _run_monthly_portfolio(
            asset_returns[["SPY", diversifier]],
            {"SPY": 2 / 3, diversifier: 1 / 3},
            name=f"2/3 SPY / 1/3 {diversifier}",
            start_equity_date=start_equity_date,
            cost_bps=primary_cost_bps,
            rebalance_monthly=True,
        )

    data: dict[str, Any] = {
        "period": {
            "start_equity_date": start_equity_date,
            "first_return_month_end": asset_returns.index[0].strftime("%Y-%m-%d"),
            "end": asset_returns.index[-1].strftime("%Y-%m-%d"),
            "months": int(len(asset_returns)),
        },
        "strategy_metrics": strategy.metrics,
        "benchmark_metrics": {
            "SPY": spy.metrics,
            "same_equity_notional_SHY_control": matched.metrics,
        },
        "comparisons": {
            "SPY": _comparison(strategy, spy),
            "same_equity_notional_SHY_control": _comparison(strategy, matched),
        },
        "cost_50bps": {
            "strategy_metrics": strategy_stress.metrics,
            "SPY_metrics": spy_stress.metrics,
            "cagr_difference": (
                strategy_stress.metrics["cagr"] - spy_stress.metrics["cagr"]
            ),
        },
        "fixed_halves_vs_SPY": _halves(strategy, spy),
        "rolling_five_year_vs_SPY": _rolling_comparison(strategy, spy),
        "turnover_definition": "sum absolute target-minus-drift weights; initial 100pct",
    }
    if "unlevered" in results:
        data["benchmark_metrics"]["unlevered_same_assets"] = results[
            "unlevered"
        ].metrics
        data["comparisons"]["unlevered_same_assets"] = _comparison(
            strategy, results["unlevered"]
        )
    return data, results


def _receipt_integrity(
    design_panel: MarketPanel,
    kmlm_panel: MarketPanel,
    fmf_panel: MarketPanel,
    *,
    design_receipt: dict[str, Any],
    kmlm_receipt: dict[str, Any],
    fmf_receipt: dict[str, Any],
    protocol_receipt: dict[str, Any],
    data_receipt: dict[str, Any],
    protocol_sha256: str,
    product_mapping_sha256: str,
    kfa_pdf_path: str | Path,
) -> dict[str, bool]:
    if protocol_sha256 != V23_PROTOCOL_SHA256:
        raise ValueError("v23 協議已與首次產品下載前凍結版本不同")
    if product_mapping_sha256 != V23_PRODUCT_MAPPING_SHA256:
        raise ValueError("v23 產品映射已與首次產品下載前凍結版本不同")
    if protocol_receipt.get("protocol_sha256") != V23_PROTOCOL_SHA256:
        raise ValueError("v23 協議收據雜湊不符")
    if protocol_receipt.get("product_mapping_sha256") != V23_PRODUCT_MAPPING_SHA256:
        raise ValueError("v23 產品映射收據雜湊不符")
    if (
        protocol_receipt.get("status")
        != "frozen_before_first_kmlm_fmf_daily_download_or_v23_portfolio_calculation"
    ):
        raise ValueError("v23 協議收據未證明先凍結再下載與計算")
    if data_receipt.get("pre_registration_order_proved") is not True:
        raise ValueError("v23 資料收據未證明預先登錄順序")
    if _sha256(kfa_pdf_path) != V23_KFA_PDF_SHA256:
        raise ValueError("v23 KFA 官方簡報雜湊不符")

    expected = (
        (
            design_panel,
            design_receipt,
            V23_DESIGN_PANEL_SHA256,
            V23_DESIGN_ARCHIVE_SHA256,
        ),
        (kmlm_panel, kmlm_receipt, V23_KMLM_PANEL_SHA256, V23_KMLM_ARCHIVE_SHA256),
        (fmf_panel, fmf_receipt, V23_FMF_PANEL_SHA256, V23_FMF_ARCHIVE_SHA256),
    )
    for panel, receipt, panel_sha, archive_sha in expected:
        if panel_fingerprint(panel) != panel_sha or receipt.get("panel_sha256") != panel_sha:
            raise ValueError("v23 快照面板雜湊不符")
        if receipt.get("archive_sha256") != archive_sha:
            raise ValueError("v23 快照 ZIP 雜湊不符")
        if (receipt.get("contract") or {}).get("ok") is not True:
            raise ValueError("v23 快照資料契約未通過")

    protocol_mtime = int(protocol_receipt.get("protocol_mtime_epoch", 0))
    mapping_mtime = int(protocol_receipt.get("product_mapping_mtime_epoch", 0))
    kmlm_mtime = int(data_receipt.get("kmlm_snapshot", {}).get("snapshot_mtime_epoch", 0))
    fmf_mtime = int(data_receipt.get("fmf_snapshot", {}).get("snapshot_mtime_epoch", 0))
    if min(protocol_mtime, mapping_mtime, kmlm_mtime, fmf_mtime) <= 0:
        raise ValueError("v23 凍結／下載時間收據不完整")
    if protocol_mtime >= min(kmlm_mtime, fmf_mtime) or mapping_mtime >= min(
        kmlm_mtime, fmf_mtime
    ):
        raise ValueError("v23 協議或映射沒有早於產品快照")
    return {
        "frozen_protocol_and_mapping_hashes_pass": True,
        "protocol_and_mapping_precede_both_product_snapshots": True,
        "official_kfa_pdf_hash_and_visual_review_pass": bool(
            data_receipt.get("kfa_index_source", {}).get("visual_review_passed")
        ),
        "design_snapshot_hash_and_contract_pass": True,
        "kmlm_snapshot_hash_and_contract_pass": True,
        "fmf_snapshot_hash_and_contract_pass": True,
    }


def evaluate_managed_futures_capital_efficiency(
    design_panel: MarketPanel,
    kmlm_panel: MarketPanel,
    fmf_panel: MarketPanel,
    *,
    design_receipt: dict[str, Any],
    kmlm_receipt: dict[str, Any],
    fmf_receipt: dict[str, Any],
    protocol_receipt: dict[str, Any],
    data_receipt: dict[str, Any],
    protocol_sha256: str,
    product_mapping_sha256: str,
    kfa_pdf_path: str | Path,
    kfa_monthly_csv_path: str | Path,
    primary_cost_bps: float = 10.0,
    stress_cost_bps: float = 50.0,
) -> dict[str, Any]:
    """Evaluate the frozen v23 S&P 500 plus managed-futures hypothesis."""
    data_gates = _receipt_integrity(
        design_panel,
        kmlm_panel,
        fmf_panel,
        design_receipt=design_receipt,
        kmlm_receipt=kmlm_receipt,
        fmf_receipt=fmf_receipt,
        protocol_receipt=protocol_receipt,
        data_receipt=data_receipt,
        protocol_sha256=protocol_sha256,
        product_mapping_sha256=product_mapping_sha256,
        kfa_pdf_path=kfa_pdf_path,
    )
    kfa, kfa_integrity = _load_kfa_monthly(kfa_monthly_csv_path)
    data_gates["kfa_240_months_and_annual_compounding_pass"] = bool(
        kfa_integrity["formal_rows"] == 240
        and kfa_integrity["annual_compounding_check_passed"]
    )

    long_prices = _month_end_prices(
        design_panel,
        ["SPY", "SSO", "SHY"],
        start=V23_LONG_START,
        end=V23_LONG_END,
    )
    long_returns = _return_frame_from_prices(long_prices)
    if len(long_returns) != 240:
        raise ValueError(f"v23 長期實際 ETF 月數 {len(long_returns)} != 240")
    formal_kfa = kfa.loc["2006-07":"2026-06", "gross_return"]
    if not long_returns.index.to_period("M").equals(formal_kfa.index):
        raise ValueError("v23 KFA 與實際 ETF 長期月份未對齊")
    monthly_drag = (1.0 - V23_KFA_ANNUAL_DRAG) ** (1.0 / 12.0)
    long_returns["KFA_MLM_NET_PROXY"] = (
        (1.0 + formal_kfa.to_numpy(dtype=float)) * monthly_drag - 1.0
    )
    long_data, _ = _evaluate_period(
        long_returns,
        diversifier="KFA_MLM_NET_PROXY",
        start_equity_date=V23_LONG_START,
        primary_cost_bps=primary_cost_bps,
        stress_cost_bps=stress_cost_bps,
        include_unlevered=True,
    )
    long_rolling = long_data["rolling_five_year_vs_SPY"]["summary"]
    long_halves = long_data["fixed_halves_vs_SPY"]
    long_strategy = long_data["strategy_metrics"]
    long_spy = long_data["benchmark_metrics"]["SPY"]
    long_matched = long_data["benchmark_metrics"]["same_equity_notional_SHY_control"]
    long_unlevered = long_data["benchmark_metrics"]["unlevered_same_assets"]
    long_gates = {
        "cagr_beats_SPY_25bp": bool(long_strategy["cagr"] >= long_spy["cagr"] + 0.0025),
        "sharpe_beats_SPY": bool(long_strategy["sharpe"] > long_spy["sharpe"]),
        "drawdown_not_worse_than_SPY": bool(
            long_strategy["max_drawdown"] >= long_spy["max_drawdown"]
        ),
        "calmar_beats_SPY": bool(long_strategy["calmar"] > long_spy["calmar"]),
        "50bps_cagr_beats_SPY_10bp": bool(
            long_data["cost_50bps"]["cagr_difference"] >= 0.001
        ),
        "both_fixed_decades_cagr_beat_SPY_10bp": bool(
            all(half["cagr_difference"] >= 0.001 for half in long_halves.values())
        ),
        "rolling_5y_wins_60pct_and_median_10bp": bool(
            long_rolling.get("cagr_win_fraction", 0.0) >= 0.60
            and long_rolling.get("median_cagr_difference", 0.0) >= 0.001
        ),
        "cagr_beats_same_notional_SHY_control_10bp": bool(
            long_strategy["cagr"] >= long_matched["cagr"] + 0.001
        ),
        "drawdown_not_worse_than_same_notional_SHY_control": bool(
            long_strategy["max_drawdown"] >= long_matched["max_drawdown"]
        ),
        "cagr_beats_unlevered_same_assets_10bp": bool(
            long_strategy["cagr"] >= long_unlevered["cagr"] + 0.001
        ),
    }

    kmlm_prices = _month_end_prices(
        kmlm_panel,
        ["SPY", "SSO", "SHY", "KMLM"],
        start=V23_KMLM_START,
        end=V23_KMLM_END,
    )
    kmlm_returns = _return_frame_from_prices(kmlm_prices)
    if len(kmlm_returns) != 67:
        raise ValueError(f"v23 KMLM 實際月數 {len(kmlm_returns)} != 67")
    kmlm_data, _ = _evaluate_period(
        kmlm_returns,
        diversifier="KMLM",
        start_equity_date=V23_KMLM_START,
        primary_cost_bps=primary_cost_bps,
        stress_cost_bps=stress_cost_bps,
        include_unlevered=False,
    )
    kfa_common = kfa.loc["2021-01":"2026-06", "gross_return"]
    kmlm_common = kmlm_returns.loc[
        kmlm_returns.index.to_period("M").isin(kfa_common.index), "KMLM"
    ]
    if len(kmlm_common) != len(kfa_common) or len(kmlm_common) != 66:
        raise ValueError("v23 KMLM／KFA 共同月份不是凍結的 66 個月")
    index_values = kfa_common.to_numpy(dtype=float)
    fund_values = kmlm_common.to_numpy(dtype=float)
    tracking_correlation = float(np.corrcoef(index_values, fund_values)[0, 1])
    years = len(index_values) / 12.0
    index_cagr = float(np.prod(1.0 + index_values) ** (1.0 / years) - 1.0)
    fund_cagr = float(np.prod(1.0 + fund_values) ** (1.0 / years) - 1.0)
    tracking_gap = index_cagr - fund_cagr
    maximum_monthly_deviation = float(np.max(np.abs(index_values - fund_values)))
    tracking = {
        "common_months": int(len(index_values)),
        "start_month": str(kfa_common.index.min()),
        "end_month": str(kfa_common.index.max()),
        "monthly_return_correlation": tracking_correlation,
        "index_cagr": index_cagr,
        "fund_cagr": fund_cagr,
        "annualized_geometric_tracking_gap": tracking_gap,
        "maximum_absolute_monthly_deviation": maximum_monthly_deviation,
    }
    kmlm_strategy = kmlm_data["strategy_metrics"]
    kmlm_spy = kmlm_data["benchmark_metrics"]["SPY"]
    kmlm_halves = kmlm_data["fixed_halves_vs_SPY"]
    kmlm_rolling = kmlm_data["rolling_five_year_vs_SPY"]["summary"]
    kmlm_bridge_gates = {
        "actual_months_ohlc_and_unique_dates_pass": bool(
            (kmlm_receipt.get("contract") or {}).get("ok")
            and len(kmlm_returns) == 67
        ),
        "index_fund_monthly_correlation_at_least_097": bool(
            tracking_correlation >= 0.97
        ),
        "tracking_gap_0_to_2pct_and_monthly_deviation_at_most_8pct": bool(
            0.0 <= tracking_gap <= 0.02 and maximum_monthly_deviation <= 0.08
        ),
        "actual_candidate_cagr_beats_SPY_10bp": bool(
            kmlm_strategy["cagr"] >= kmlm_spy["cagr"] + 0.001
        ),
        "actual_candidate_sharpe_beats_SPY": bool(
            kmlm_strategy["sharpe"] > kmlm_spy["sharpe"]
        ),
        "actual_candidate_drawdown_not_worse_than_SPY": bool(
            kmlm_strategy["max_drawdown"] >= kmlm_spy["max_drawdown"]
        ),
        "actual_candidate_calmar_beats_SPY": bool(
            kmlm_strategy["calmar"] > kmlm_spy["calmar"]
        ),
        "actual_50bps_cagr_not_below_SPY": bool(
            kmlm_data["cost_50bps"]["cagr_difference"] >= 0.0
        ),
        "actual_both_halves_cagr_not_below_SPY": bool(
            all(half["cagr_difference"] >= 0.0 for half in kmlm_halves.values())
        ),
        "actual_rolling_5y_wins_60pct_and_positive_median": bool(
            kmlm_rolling.get("cagr_win_fraction", 0.0) >= 0.60
            and kmlm_rolling.get("median_cagr_difference", 0.0) > 0.0
        ),
    }

    fmf_prices = _month_end_prices(
        fmf_panel,
        ["SPY", "SSO", "SHY", "FMF"],
        start=V23_FMF_START,
        end=V23_FMF_END,
    )
    fmf_returns = _return_frame_from_prices(fmf_prices)
    if len(fmf_returns) != 155:
        raise ValueError(f"v23 FMF 實際月數 {len(fmf_returns)} != 155")
    fmf_data, _ = _evaluate_period(
        fmf_returns,
        diversifier="FMF",
        start_equity_date=V23_FMF_START,
        primary_cost_bps=primary_cost_bps,
        stress_cost_bps=stress_cost_bps,
        include_unlevered=False,
    )
    fmf_strategy = fmf_data["strategy_metrics"]
    fmf_spy = fmf_data["benchmark_metrics"]["SPY"]
    fmf_halves = fmf_data["fixed_halves_vs_SPY"]
    fmf_rolling = fmf_data["rolling_five_year_vs_SPY"]["summary"]
    fmf_gates = {
        "cagr_beats_SPY_10bp": bool(fmf_strategy["cagr"] >= fmf_spy["cagr"] + 0.001),
        "sharpe_beats_SPY": bool(fmf_strategy["sharpe"] > fmf_spy["sharpe"]),
        "drawdown_not_worse_than_SPY": bool(
            fmf_strategy["max_drawdown"] >= fmf_spy["max_drawdown"]
        ),
        "calmar_beats_SPY": bool(fmf_strategy["calmar"] > fmf_spy["calmar"]),
        "50bps_cagr_not_below_SPY": bool(
            fmf_data["cost_50bps"]["cagr_difference"] >= 0.0
        ),
        "both_halves_cagr_not_below_SPY": bool(
            all(half["cagr_difference"] >= 0.0 for half in fmf_halves.values())
        ),
        "rolling_5y_wins_60pct_and_positive_median": bool(
            fmf_rolling.get("cagr_win_fraction", 0.0) >= 0.60
            and fmf_rolling.get("median_cagr_difference", 0.0) > 0.0
        ),
    }

    long_passed = sum(long_gates.values())
    kmlm_passed = sum(kmlm_bridge_gates.values())
    fmf_passed = sum(fmf_gates.values())
    data_passed = sum(data_gates.values())
    paper_eligible = bool(
        long_passed == len(long_gates)
        and kmlm_passed == len(kmlm_bridge_gates)
        and fmf_passed >= 5
        and data_passed == len(data_gates)
    )
    audit: dict[str, Any] = {
        "schema_version": 1,
        "status": (
            "managed_futures_capital_efficiency_passed_for_isolated_paper"
            if paper_eligible
            else "managed_futures_capital_efficiency_validation_failed"
        ),
        "paper_eligible": paper_eligible,
        "trade_ready": False,
        "reference_trade_candidate": bool(paper_eligible),
        "global_search_trials": V23_GLOBAL_SEARCH_TRIALS,
        "protocol_sha256": V23_PROTOCOL_SHA256,
        "product_mapping_sha256": V23_PRODUCT_MAPPING_SHA256,
        "protocol": {
            "sha256": V23_PROTOCOL_SHA256,
            "product_mapping_sha256": V23_PRODUCT_MAPPING_SHA256,
        },
        "candidate": {
            "physical_weights": {"SSO": 0.5, "KMLM": 0.5},
            "rebalance": "monthly",
            "approximate_equity_notional": 1.0,
            "account_borrowing": False,
            "long_history_uses_index_proxy_not_actual_KMLM": True,
            "signal_display_allowed": bool(paper_eligible),
        },
        "kfa_index_integrity": kfa_integrity,
        "long_horizon": {**long_data, "economic_gates": long_gates},
        "kmlm_actual_bridge": {
            **kmlm_data,
            "tracking": tracking,
            "entry_gates": kmlm_bridge_gates,
        },
        "fmf_cross_manager": {**fmf_data, "entry_gates": fmf_gates},
        "data_gates": data_gates,
        "long_passed_gate_count": long_passed,
        "long_required_gate_count": len(long_gates),
        "kmlm_bridge_passed_gate_count": kmlm_passed,
        "kmlm_bridge_required_gate_count": len(kmlm_bridge_gates),
        "fmf_passed_gate_count": fmf_passed,
        "fmf_required_gate_count": len(fmf_gates),
        "fmf_required_pass_count": 5,
        "data_passed_gate_count": data_passed,
        "data_required_gate_count": len(data_gates),
        "paper_entry_passed_gate_count": (
            long_passed + kmlm_passed + min(fmf_passed, 5) + data_passed
        ),
        "paper_entry_required_gate_count": (
            len(long_gates) + len(kmlm_bridge_gates) + 5 + len(data_gates)
        ),
        "paper_state_created": False,
        "paper_requirements_if_eligible": {
            "new_sessions": 252,
            "completed_monthly_rebalances": 6,
            "data_or_guard_violations": 0,
            "forward_directions_must_remain_consistent": True,
        },
        "statistical_confirmation": {
            "long_vs_SPY": long_data["comparisons"]["SPY"],
            "kmlm_actual_vs_SPY": kmlm_data["comparisons"]["SPY"],
            "fmf_actual_vs_SPY": fmf_data["comparisons"]["SPY"],
        },
        "evidence_boundary": {
            "classification": "seen_long_history_design_data_plus_post_freeze_product_paths_not_fully_blind",
            "twenty_year_claim": "actual SSO plus official gross KFA MLM index proxy net of fixed 1.05pct annual drag",
            "actual_KMLM_history_start": "2020-12-01",
            "actual_FMF_is_cross_manager_not_interchangeable": True,
            "official_summary_and_index_month_table_seen_before_freeze": True,
            "joint_portfolio_paths_computed_after_freeze": True,
        },
    }
    return audit
