from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from usfddk.data import (
    fetch_yfinance,
    load_snapshot,
    panel_fingerprint,
    save_snapshot,
)
from usfddk.engine import run_backtest
from usfddk.low_turnover import (
    build_v9_external_common_panel,
    validate_v9_external_common,
)
from usfddk.metrics import compute_metrics, newey_west_mean_test
from usfddk.models import BacktestResult, ContractResult, MarketPanel
from usfddk.relative_growth import (
    V7_GSPC_ARCHIVE_SHA256,
    V7_GSPC_PANEL_SHA256,
    V7_MAIN_ARCHIVE_SHA256,
    V7_MAIN_PANEL_SHA256,
    V7_NDX_ARCHIVE_SHA256,
    V7_NDX_PANEL_SHA256,
    _validate_snapshot,
    build_v7_proxy_panel,
)
from usfddk.strategies import (
    buy_and_hold_targets,
    hierarchical_relative_growth_states,
    hierarchical_relative_growth_targets,
)
from usfddk.validation import deflated_sharpe_ratio, probabilistic_sharpe_ratio

V10_PROTOCOL_SHA256 = "ec23c0593820529e60087daf866adc66b64eda91922165a614ba225dadbc4484"
V10_DATA_CONTRACT_SHA256 = (
    "c81c4627b32c1c1d6172db3cac4a090aaae5f02621c2dfcffa1479b9af52ad26"
)
V10_FETCH_START = "1971-02-05"
V10_EXTERNAL_START = "1973-01-03"
V10_EXTERNAL_END = "1988-12-30"
V10_IXIC_PANEL_SHA256 = "76bc29b61c480e8c44032e4aeaea801e9ea97a1aebceb758bda84df8a8b7d2c9"
V10_IXIC_ARCHIVE_SHA256 = (
    "b845aecd3175584f8dc40e0db8e93ec9427e2a9f491f0824ec7264f6cda9eb22"
)
V12_PROTOCOL_SHA256 = "902fd24841a323c70023b240e695a9bcc0a32c4eb21cbd96b7cfdff9a9918c34"
V12_GLOBAL_SEARCH_TRIALS = 6_109
V12_MAIN_START = "2006-07-31"
V12_MAIN_END = "2026-07-31"
V12_PROXY_START = "1989-01-03"
V12_PROXY_END = "2006-07-28"
V12_EXTERNAL_START = "1973-01-03"
V12_EXTERNAL_END = "1988-12-30"
V12_IXIC_PANEL_SHA256 = V10_IXIC_PANEL_SHA256
V12_IXIC_ARCHIVE_SHA256 = V10_IXIC_ARCHIVE_SHA256
V12_GSPC_PANEL_SHA256 = "414d787995baeceb921bb088d5b54d08612e8b60d7a8443785c9603335ffc5ca"
V12_GSPC_ARCHIVE_SHA256 = (
    "b5bcc28cf4fdddc83e60bf08601c83cd67eff44132c92a4980d6d37a20a2d471"
)
V12_V10_FAILURE_RECEIPT_SHA256 = (
    "7b4a1b2d436b003d2b5d6b1d79e234a165b86d8113720530e40919d025f0c5b2"
)
V12_V11_FAILURE_RECEIPT_SHA256 = (
    "a020faffcfc2204bf046cb535e6876df05002678d5ef562898cea42ca6cbf642"
)


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _with_metadata(panel: MarketPanel, extra: dict[str, Any]) -> MarketPanel:
    return MarketPanel(
        open=panel.open,
        high=panel.high,
        low=panel.low,
        close=panel.close,
        volume=panel.volume,
        metadata={**panel.metadata, **extra},
    )


def validate_v10_dji_index(
    panel: MarketPanel, *, protocol_sha256: str
) -> ContractResult:
    """Apply the DJIA contract frozen before its first v10 download."""
    ticker = "^DJI"
    errors: list[str] = []
    stats: dict[str, Any] = {}
    close = panel.close
    fields = panel.field_map()
    if list(close.columns) != [ticker]:
        errors.append("欄位必須只有 ^DJI")
    if not close.index.is_monotonic_increasing or close.index.has_duplicates:
        errors.append("日期索引不是嚴格遞增且唯一")
    if close.empty:
        errors.append("Close 面板為空")
        return ContractResult(False, tuple(errors), (), stats)
    stats.update(
        {
            "ticker": ticker,
            "rows": int(len(close)),
            "start": panel.start.strftime("%Y-%m-%d"),
            "end": panel.end.strftime("%Y-%m-%d"),
        }
    )
    if stats["start"] != V10_FETCH_START:
        errors.append(f"第一筆不是 {V10_FETCH_START}")
    if stats["end"] != V10_EXTERNAL_END:
        errors.append(f"最後一筆不是 {V10_EXTERNAL_END}")
    if len(close) < 4_300:
        errors.append(f"資料列數 {len(close)} < 4300")

    missing_by_field: dict[str, int] = {}
    for field, frame in fields.items():
        if not frame.index.equals(close.index) or list(frame.columns) != [ticker]:
            errors.append(f"{field} 與 Close 的索引或欄位不一致")
            continue
        missing_by_field[field] = int(frame.isna().sum().sum())
        if missing_by_field[field]:
            errors.append(f"{field} 含 {missing_by_field[field]} 個缺值")
    stats["missing_by_field"] = missing_by_field
    for field in ("Open", "High", "Low", "Close"):
        values = fields[field].to_numpy(dtype=float)
        if not bool(np.isfinite(values).all() and (values > 0.0).all()):
            errors.append(f"{field} 含非有限值、零或負數")
    volume = panel.volume.to_numpy(dtype=float)
    if not bool(np.isfinite(volume).all() and (volume >= 0.0).all()):
        errors.append("Volume 含非有限值或負數")

    o = panel.open[ticker]
    h = panel.high[ticker]
    low = panel.low[ticker]
    c = panel.close[ticker]
    violations = int(((h < o) | (h < c) | (low > o) | (low > c)).sum())
    stats["ohlc_violations"] = violations
    if violations:
        errors.append(f"OHLC 關係違反 {violations} 筆")
    max_move = float(c.pct_change(fill_method=None).abs().max())
    stats["max_absolute_close_return"] = max_move
    if max_move > 0.35:
        errors.append(f"單日 Close 絕對報酬 {max_move:.2%} > 35%")

    metadata = panel.metadata
    if metadata.get("provider") != "Yahoo Finance via yfinance":
        errors.append("provider metadata 不符")
    if not metadata.get("adjustment"):
        errors.append("缺少還原方法 metadata")
    if metadata.get("research_protocol_sha256") != protocol_sha256:
        errors.append("研究協議 SHA-256 metadata 不符")
    if metadata.get("role") != "core_sensitivity":
        errors.append("資料角色 metadata 不符")
    return ContractResult(not errors, tuple(errors), (), stats)


def build_v10_dji_common_panel(
    dji_panel: MarketPanel, ixic_panel: MarketPanel
) -> MarketPanel:
    common = dji_panel.close.index.intersection(ixic_panel.close.index).sort_values()

    def joined(field: str) -> pd.DataFrame:
        dji = dji_panel.field_map()[field].loc[common, ["^DJI"]]
        ixic = ixic_panel.field_map()[field].loc[common, ["^IXIC"]]
        return pd.concat([dji, ixic], axis=1)

    return MarketPanel(
        open=joined("Open"),
        high=joined("High"),
        low=joined("Low"),
        close=joined("Close"),
        volume=joined("Volume"),
        metadata={
            "derived_from_frozen_snapshots": True,
            "join": "common sessions only; no filling or interpolation",
            "research_protocol_sha256": V10_PROTOCOL_SHA256,
        },
    )


def validate_v10_dji_common(panel: MarketPanel) -> ContractResult:
    errors: list[str] = []
    stats: dict[str, Any] = {
        "rows": int(len(panel.close)),
        "start": panel.start.strftime("%Y-%m-%d"),
        "end": panel.end.strftime("%Y-%m-%d"),
    }
    if list(panel.close.columns) != ["^DJI", "^IXIC"]:
        errors.append("共同面板欄位或順序不符")
    if stats["start"] != V10_FETCH_START:
        errors.append(f"共同面板第一筆不是 {V10_FETCH_START}")
    if stats["end"] != V10_EXTERNAL_END:
        errors.append(f"共同面板最後一筆不是 {V10_EXTERNAL_END}")
    if len(panel.close) < 4_300:
        errors.append(f"共同面板資料列數 {len(panel.close)} < 4300")
    missing = {
        field: int(frame.isna().sum().sum()) for field, frame in panel.field_map().items()
    }
    stats["missing_by_field"] = missing
    if any(missing.values()):
        errors.append("共同面板 OHLCV 含缺值")
    warmup = panel.close.loc[panel.close.index < pd.Timestamp(V10_EXTERNAL_START)]
    warmup_sessions = int(warmup.notna().all(axis=1).sum())
    stats["warmup_common_sessions"] = warmup_sessions
    if warmup_sessions < 252:
        errors.append(f"共同暖機日 {warmup_sessions} < 252")
    for boundary in (
        "1973-01-03",
        "1980-12-31",
        "1981-01-02",
        "1988-12-30",
    ):
        if pd.Timestamp(boundary) not in panel.close.index:
            errors.append(f"缺少固定邊界 {boundary}")
    return ContractResult(not errors, tuple(errors), (), stats)


def fetch_and_freeze_v10_dji(
    output_dir: str | Path,
    *,
    ixic_snapshot: str | Path,
    protocol_sha256: str,
    data_contract_sha256: str,
) -> tuple[dict[str, Any], bool]:
    """Fetch the partially new DJIA core once and preserve a content receipt."""
    if protocol_sha256 != V10_PROTOCOL_SHA256:
        raise ValueError("v10 協議雜湊與首次下載前凍結版本不同")
    if data_contract_sha256 != V10_DATA_CONTRACT_SHA256:
        raise ValueError("v10 DJIA 資料契約雜湊與首次下載前凍結版本不同")
    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    existing = sorted(destination.glob("snapshot_v10_dji_19710205_19881230_*.zip"))
    if existing:
        raise ValueError(
            "v10 DJIA 快照已凍結，拒絕重新下載或覆寫；請直接執行 v10-hierarchical"
        )

    ixic_path = Path(ixic_snapshot)
    ixic_panel, ixic_manifest = load_snapshot(ixic_path)
    if panel_fingerprint(ixic_panel) != V10_IXIC_PANEL_SHA256:
        raise ValueError("v10 指定的既有 ^IXIC panel 雜湊不符")
    if _file_sha256(ixic_path) != V10_IXIC_ARCHIVE_SHA256:
        raise ValueError("v10 指定的既有 ^IXIC archive 雜湊不符")

    fetched = fetch_yfinance(
        ["^DJI"], V10_FETCH_START, V10_EXTERNAL_END, threads=False
    )
    panel = _with_metadata(
        fetched,
        {
            "research_protocol_sha256": protocol_sha256,
            "external_data_contract_sha256": data_contract_sha256,
            "requested_start": V10_FETCH_START,
            "requested_end": V10_EXTERNAL_END,
            "role": "core_sensitivity",
        },
    )
    contract = validate_v10_dji_index(panel, protocol_sha256=protocol_sha256)
    fingerprint = panel_fingerprint(panel)
    path = destination / (
        f"snapshot_v10_dji_19710205_19881230_{fingerprint[:8]}.zip"
    )
    manifest = save_snapshot(panel, path, contract=contract)
    common = build_v10_dji_common_panel(panel, ixic_panel)
    common_contract = validate_v10_dji_common(common)
    receipt = {
        "schema_version": 1,
        "protocol": {
            "path": "docs/V10_HIERARCHICAL_DEFENSE_PROTOCOL.md",
            "sha256": protocol_sha256,
        },
        "data_contract": {
            "path": "docs/V10_DJI_DATA_CONTRACT.md",
            "sha256": data_contract_sha256,
        },
        "dji_snapshot": {
            "path": str(path),
            "ticker": "^DJI",
            "panel_sha256": manifest["panel_sha256"],
            "archive_sha256": manifest["archive_sha256"],
            "rows": manifest["rows"],
            "start": manifest["start"],
            "end": manifest["end"],
            "created_at": manifest["created_at"],
            "provider_metadata": manifest["provider_metadata"],
            "contract": manifest["contract"],
        },
        "frozen_ixic_snapshot": {
            "path": str(ixic_path),
            "panel_sha256": V10_IXIC_PANEL_SHA256,
            "archive_sha256": V10_IXIC_ARCHIVE_SHA256,
            "rows": int(ixic_manifest["rows"]),
            "start": str(ixic_manifest["start"]),
            "end": str(ixic_manifest["end"]),
        },
        "derived_common_panel": {
            "panel_sha256": panel_fingerprint(common),
            "contract": {
                "ok": common_contract.ok,
                "errors": list(common_contract.errors),
                "warnings": list(common_contract.warnings),
                "stats": common_contract.stats,
            },
        },
    }
    return receipt, bool(contract.ok and common_contract.ok)


def _add_constant_cash(panel: MarketPanel) -> MarketPanel:
    frames: dict[str, pd.DataFrame] = {}
    for field, frame in panel.field_map().items():
        copied = frame.copy()
        copied["CASH"] = 0.0 if field == "Volume" else 1.0
        frames[field] = copied
    return MarketPanel(
        open=frames["Open"],
        high=frames["High"],
        low=frames["Low"],
        close=frames["Close"],
        volume=frames["Volume"],
        metadata={
            **panel.metadata,
            "cash_proxy": "constant 1.0; zero return; no interest",
        },
    )


def _slice_result(result: BacktestResult, start: str, end: str) -> BacktestResult:
    dates = result.equity.loc[start:end].index
    if len(dates) < 2:
        raise ValueError(f"正式期 {start}–{end} 有效交易日不足")
    equity = result.equity.loc[dates].copy()
    equity = (equity / float(equity.iloc[0])).rename(result.name)
    returns = equity.pct_change(fill_method=None).fillna(0.0).rename(result.name)
    turnover = result.turnover.loc[dates].copy()
    costs = result.costs.loc[dates].copy()
    weights = result.weights.loc[dates].copy()
    diagnostics = {
        **result.diagnostics,
        "formal_start": start,
        "formal_end": end,
        "rebalance_count": int((turnover > 0.0).sum()),
        "warm_started_before_formal_period": True,
    }
    return BacktestResult(
        name=result.name,
        equity=equity,
        returns=returns,
        weights=weights,
        turnover=turnover,
        costs=costs,
        metrics=compute_metrics(equity, returns, turnover),
        current_target=result.current_target,
        diagnostics=diagnostics,
    )


def _comparison(strategy: BacktestResult, benchmark: BacktestResult) -> dict[str, Any]:
    aligned = pd.concat(
        [strategy.returns.rename("strategy"), benchmark.returns.rename("benchmark")],
        axis=1,
    ).dropna()
    active = aligned["strategy"] - aligned["benchmark"]
    return {
        "cagr_difference": strategy.metrics["cagr"] - benchmark.metrics["cagr"],
        "sharpe_difference": (
            strategy.metrics["sharpe"] - benchmark.metrics["sharpe"]
        ),
        "drawdown_improvement": (
            strategy.metrics["max_drawdown"] - benchmark.metrics["max_drawdown"]
        ),
        "calmar_difference": (
            strategy.metrics["calmar"] - benchmark.metrics["calmar"]
        ),
        "active_return_newey_west": newey_west_mean_test(active, max_lag=9),
        "active_probabilistic_sharpe": probabilistic_sharpe_ratio(
            active, benchmark_sharpe=0.0
        ),
        "active_global_deflated_sharpe": deflated_sharpe_ratio(
            active, trials=V12_GLOBAL_SEARCH_TRIALS
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
        dates = strategy.equity.loc[start:end].index
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


def _one_time_weights(
    close: pd.DataFrame, weights: dict[str, float], signal_on: str
) -> pd.DataFrame:
    targets = pd.DataFrame(np.nan, index=close.index, columns=list(weights))
    signal = pd.Timestamp(signal_on)
    if signal not in targets.index:
        raise ValueError(f"一次性配置訊號日不存在：{signal_on}")
    targets.loc[signal] = pd.Series(weights)
    return targets


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
    target = hierarchical_relative_growth_targets(
        panel.close,
        core=core,
        growth=growth,
        defensive=defensive,
        permanent_core_weight=0.60,
        initial_signal_before=start,
    )
    signals = target.dropna(how="all")
    if signals.empty:
        raise ValueError(f"{label}找不到初始或狀態切換訊號")
    entry_signal = pd.Timestamp(signals.index[0])
    entry_position = panel.close.index.get_loc(entry_signal)
    if not isinstance(entry_position, int) or entry_position + 1 >= len(panel.close.index):
        raise ValueError(f"{label}初始訊號無下一個可執行交易日")
    execution_start = panel.close.index[entry_position + 1]
    entry_signal_text = entry_signal.strftime("%Y-%m-%d")
    run_start = execution_start.strftime("%Y-%m-%d")

    market_target = buy_and_hold_targets(
        panel.close, core, signal_on=entry_signal_text
    )
    opportunity_target = buy_and_hold_targets(
        panel.close, growth, signal_on=entry_signal_text
    )
    static_target = _one_time_weights(
        panel.close, {core: 0.60, growth: 0.40}, entry_signal_text
    )

    def run(signals_to_run: pd.DataFrame, name: str, cost: float) -> BacktestResult:
        full = run_backtest(
            panel,
            signals_to_run,
            name=f"{label}{name}",
            cost_bps=cost,
            start=run_start,
        )
        return _slice_result(full, start, end)

    strategy = run(target, "階層式三態", primary_cost_bps)
    market = run(market_target, "市場", primary_cost_bps)
    opportunity = run(opportunity_target, "成長機會成本", primary_cost_bps)
    static = run(static_target, "一次性 60/40", primary_cost_bps)
    strategy_50 = run(target, "階層式三態 50bps", stress_cost_bps)
    market_50 = run(market_target, "市場 50bps", stress_cost_bps)
    comparison = _comparison(strategy, market)
    rolling = _rolling_comparison(strategy, market)
    half_rows = _halves(strategy, market, half_periods)
    states = hierarchical_relative_growth_states(
        panel.close, core=core, growth=growth
    )
    formal_states = states.loc[pd.Timestamp(start) : pd.Timestamp(end)]
    formal_signals = signals.loc[pd.Timestamp(start) : pd.Timestamp(end)]
    latest_state = str(states.iloc[-1])
    final_weights = strategy.weights.iloc[-1]
    last_signal = pd.Timestamp(signals.index[-1])
    pending_after_snapshot = bool(last_signal >= panel.end)
    state_counts = {
        state: int((formal_states == state).sum())
        for state in ("growth", "core", "defense")
    }
    policy_allocation = {core: 0.60, growth: 0.0, defensive: 0.0}
    if latest_state == "growth":
        policy_allocation[growth] += 0.40
    elif latest_state == "core":
        policy_allocation[core] += 0.40
    else:
        policy_allocation[defensive] += 0.40
    return strategy, target, {
        "period": {
            "start": start,
            "end": end,
            "sessions": int(len(strategy.equity)),
            "initial_signal": entry_signal_text,
            "initial_execution": run_start,
        },
        "strategy_metrics": strategy.metrics,
        "benchmark_metrics": {
            "market": market.metrics,
            "opportunity": opportunity.metrics,
            "one_time_60_40": static.metrics,
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
            "completed_month_ends_in_formal_period": int(len(formal_states)),
            "state_month_counts": state_counts,
            "state_change_signals_in_formal_period": int(len(formal_signals)),
            "completed_executions_in_formal_period": int(
                strategy.diagnostics["rebalance_count"]
            ),
            "latest_completed_month_end": pd.Timestamp(states.index[-1]).strftime(
                "%Y-%m-%d"
            ),
            "latest_state": latest_state,
            "latest_state_change_signal": last_signal.strftime("%Y-%m-%d"),
            "pending_execution_after_snapshot": pending_after_snapshot,
        },
        "current_policy_allocation": {
            ticker: float(weight)
            for ticker, weight in policy_allocation.items()
            if weight > 0.0
        },
        "historical_final_drifted_weights": {
            str(ticker): float(weight)
            for ticker, weight in final_weights.items()
            if float(weight) > 1e-12
        },
    }


def _economic_gates(prefix: str, data: dict[str, Any]) -> list[tuple[str, bool]]:
    strategy = data["strategy_metrics"]
    benchmark = data["benchmark_metrics"]["market"]
    rolling = data["rolling_five_year"]["summary"]
    return [
        (
            f"{prefix}_cagr_beats_market_10bp",
            bool(strategy["cagr"] > benchmark["cagr"] + 0.001),
        ),
        (
            f"{prefix}_sharpe_beats_market",
            bool(strategy["sharpe"] > benchmark["sharpe"]),
        ),
        (
            f"{prefix}_drawdown_not_worse_than_market_5pp",
            bool(strategy["max_drawdown"] >= benchmark["max_drawdown"] - 0.05),
        ),
        (
            f"{prefix}_calmar_beats_market",
            bool(strategy["calmar"] > benchmark["calmar"]),
        ),
        (
            f"{prefix}_50bps_cagr_beats_market_10bp",
            bool(data["cost_50bps"]["cagr_difference"] > 0.001),
        ),
        (
            f"{prefix}_both_halves_cagr_beat_market_10bp",
            bool(
                all(
                    half["cagr_difference"] > 0.001
                    for half in data["fixed_halves"].values()
                )
            ),
        ),
        (
            f"{prefix}_rolling_wins_60pct_and_positive_median",
            bool(
                rolling.get("cagr_win_fraction", 0.0) >= 0.60
                and rolling.get("median_cagr_difference", -1.0) > 0.0
            ),
        ),
    ]


def evaluate_v12_hierarchical_research(
    main_panel: MarketPanel,
    ndx_panel: MarketPanel,
    old_gspc_panel: MarketPanel,
    ixic_panel: MarketPanel,
    external_gspc_panel: MarketPanel,
    *,
    main_receipt: dict[str, Any],
    ndx_receipt: dict[str, Any],
    old_gspc_receipt: dict[str, Any],
    ixic_receipt: dict[str, Any],
    external_gspc_receipt: dict[str, Any],
    v10_failure_receipt: dict[str, Any],
    v11_failure_receipt: dict[str, Any],
    protocol_sha256: str,
    primary_cost_bps: float = 10.0,
    stress_cost_bps: float = 50.0,
) -> tuple[BacktestResult, pd.DataFrame, dict[str, Any]]:
    """Run the v10-v12 rule for the first time on three frozen datasets."""
    if protocol_sha256 != V12_PROTOCOL_SHA256:
        raise ValueError("v12 協議雜湊與第一次計算前凍結版本不同")

    _validate_snapshot(
        main_panel,
        main_receipt,
        label="v12 主樣本",
        required_tickers=("SPY", "QQQ", "SHY"),
        expected_panel_sha256=V7_MAIN_PANEL_SHA256,
        expected_archive_sha256=V7_MAIN_ARCHIVE_SHA256,
        expected_start="2004-01-02",
        expected_end=V12_MAIN_END,
        exact_tickers=False,
    )
    _validate_snapshot(
        ndx_panel,
        ndx_receipt,
        label="v12 Nasdaq-100 代理",
        required_tickers=("^NDX",),
        expected_panel_sha256=V7_NDX_PANEL_SHA256,
        expected_archive_sha256=V7_NDX_ARCHIVE_SHA256,
        expected_start="1985-10-01",
        expected_end=V12_PROXY_END,
        exact_tickers=True,
    )
    _validate_snapshot(
        old_gspc_panel,
        old_gspc_receipt,
        label="v12 舊 S&P 500 代理",
        required_tickers=("^GSPC",),
        expected_panel_sha256=V7_GSPC_PANEL_SHA256,
        expected_archive_sha256=V7_GSPC_ARCHIVE_SHA256,
        expected_start="1987-01-02",
        expected_end=V12_PROXY_END,
        exact_tickers=True,
    )
    _validate_snapshot(
        ixic_panel,
        ixic_receipt,
        label="v12 Nasdaq Composite 外部樣本",
        required_tickers=("^IXIC",),
        expected_panel_sha256=V12_IXIC_PANEL_SHA256,
        expected_archive_sha256=V12_IXIC_ARCHIVE_SHA256,
        expected_start=V10_FETCH_START,
        expected_end=V12_EXTERNAL_END,
        exact_tickers=True,
    )
    _validate_snapshot(
        external_gspc_panel,
        external_gspc_receipt,
        label="v12 外部 S&P 500 樣本",
        required_tickers=("^GSPC",),
        expected_panel_sha256=V12_GSPC_PANEL_SHA256,
        expected_archive_sha256=V12_GSPC_ARCHIVE_SHA256,
        expected_start=V10_FETCH_START,
        expected_end=V12_EXTERNAL_END,
        exact_tickers=True,
    )
    if (
        v10_failure_receipt.get("receipt_file", {}).get("sha256")
        != V12_V10_FAILURE_RECEIPT_SHA256
        or v10_failure_receipt.get("status") != "fetch_failed"
        or v10_failure_receipt.get("decision", {}).get("v10_calculation_started")
        is not False
    ):
        raise ValueError("v10 失敗收據不是 v12 協議指定的未計算封存內容")
    if (
        v11_failure_receipt.get("receipt_file", {}).get("sha256")
        != V12_V11_FAILURE_RECEIPT_SHA256
        or v11_failure_receipt.get("status") != "data_contract_failed"
        or v11_failure_receipt.get("result", {}).get("failure_stage")
        != "official_http_get"
        or "403" not in str(v11_failure_receipt.get("result", {}).get("error", ""))
    ):
        raise ValueError("v11 失敗收據不是 v12 協議指定的官方 403 封存內容")

    main_warmup = int(
        main_panel.close.loc[
            main_panel.close.index < pd.Timestamp(V12_MAIN_START),
            ["SPY", "QQQ", "SHY"],
        ]
        .notna()
        .all(axis=1)
        .sum()
    )
    if main_warmup < 252:
        raise ValueError("v12 主樣本暖機不足 252 個共同有效交易日")
    old_proxy_panel = build_v7_proxy_panel(ndx_panel, old_gspc_panel)
    old_warmup = int(
        old_proxy_panel.close.loc[
            old_proxy_panel.close.index < pd.Timestamp(V12_PROXY_START),
            ["^GSPC", "^NDX", "CASH"],
        ]
        .notna()
        .all(axis=1)
        .sum()
    )
    if old_warmup < 252:
        raise ValueError("v12 舊代理暖機不足 252 個共同有效交易日")
    external_without_cash = build_v9_external_common_panel(
        ixic_panel, external_gspc_panel
    )
    external_contract = validate_v9_external_common(external_without_cash)
    external_contract.require()
    external_panel = _add_constant_cash(external_without_cash)
    external_warmup = int(external_contract.stats["warmup_common_sessions"])

    main_result, target, main = _dataset_results(
        main_panel,
        core="SPY",
        growth="QQQ",
        defensive="SHY",
        start=V12_MAIN_START,
        end=V12_MAIN_END,
        half_periods=(
            ("first", "2006-07-31", "2016-07-29"),
            ("second", "2016-08-01", "2026-07-31"),
        ),
        label="v12 ETF ",
        primary_cost_bps=primary_cost_bps,
        stress_cost_bps=stress_cost_bps,
    )
    old_result, _, old_proxy = _dataset_results(
        old_proxy_panel,
        core="^GSPC",
        growth="^NDX",
        defensive="CASH",
        start=V12_PROXY_START,
        end=V12_PROXY_END,
        half_periods=(
            ("first", "1989-01-03", "1997-09-30"),
            ("second", "1997-10-01", "2006-07-28"),
        ),
        label="v12 舊代理 ",
        primary_cost_bps=primary_cost_bps,
        stress_cost_bps=stress_cost_bps,
    )
    external_result, _, external = _dataset_results(
        external_panel,
        core="^GSPC",
        growth="^IXIC",
        defensive="CASH",
        start=V12_EXTERNAL_START,
        end=V12_EXTERNAL_END,
        half_periods=(
            ("first", "1973-01-03", "1980-12-31"),
            ("second", "1981-01-02", "1988-12-30"),
        ),
        label="v12 外部 ",
        primary_cost_bps=primary_cost_bps,
        stress_cost_bps=stress_cost_bps,
    )

    economic_rows = [
        *_economic_gates("main", main),
        *_economic_gates("old_proxy", old_proxy),
        *_economic_gates("external", external),
    ]
    gates: dict[str, bool] = {
        f"{index:02d}_{name}": passed
        for index, (name, passed) in enumerate(economic_rows, start=1)
    }
    weight_sets = {
        "main": main_result.weights,
        "old_proxy": old_result.weights,
        "external": external_result.weights,
    }
    weight_checks = {
        label: {
            "fully_invested_fraction": float(
                np.isclose(weights.sum(axis=1), 1.0, atol=1e-8).mean()
            ),
            "maximum_weight_sum": float(weights.sum(axis=1).max()),
            "minimum_weight": float(weights.min().min()),
        }
        for label, weights in weight_sets.items()
    }
    gates["22_all_samples_fully_invested_95pct_no_leverage_or_short"] = bool(
        all(
            item["fully_invested_fraction"] >= 0.95
            and item["maximum_weight_sum"] <= 1.0 + 1e-8
            and item["minimum_weight"] >= -1e-12
            for item in weight_checks.values()
        )
    )
    gates["23_all_hashes_warmup_cash_execution_and_failure_receipts_pass"] = True
    for number, (label, data) in enumerate(
        (("main", main), ("old_proxy", old_proxy), ("external", external)),
        start=24,
    ):
        gates[f"{number:02d}_{label}_newey_west_t_at_least_1_96"] = bool(
            data["comparison"]["active_return_newey_west"]["t_stat"] >= 1.96
        )
    for number, (label, data) in enumerate(
        (("main", main), ("old_proxy", old_proxy), ("external", external)),
        start=27,
    ):
        gates[f"{number:02d}_{label}_psr_probability_95pct"] = bool(
            data["comparison"]["active_probabilistic_sharpe"]["probability"]
            >= 0.95
        )

    paper_entry_gates = {
        key: value for key, value in gates.items() if int(key[:2]) <= 23
    }
    statistical_gates = {
        key: value for key, value in gates.items() if int(key[:2]) >= 24
    }
    paper_eligible = all(paper_entry_gates.values())
    historically_confirmed = all(gates.values())
    dsr_sensitivity = {
        label: data["comparison"]["active_global_deflated_sharpe"]
        for label, data in (
            ("main", main),
            ("old_proxy", old_proxy),
            ("external", external),
        )
    }
    dsr_sensitivity_passed = all(
        float(item["probability"]) >= 0.95 for item in dsr_sensitivity.values()
    )
    audit: dict[str, Any] = {
        "schema_version": 1,
        "strategy_name": "v12 階層式成長／核心／防守三態",
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
            "path": "docs/V12_HIERARCHICAL_DEFENSE_THREE_SAMPLE_PROTOCOL.md",
            "sha256": protocol_sha256,
            "frozen_before_first_v12_calculation": True,
            "data_independent": False,
            "rule_previously_frozen_in_v10_and_v11_but_never_calculated": True,
            "global_search_trials": V12_GLOBAL_SEARCH_TRIALS,
        },
        "parameters": {
            "permanent_core_weight": 0.60,
            "conditional_slot_weight": 0.40,
            "states_in_order": ["growth", "core", "defense"],
            "momentum": "close(t-21) / close(t-252) - 1",
            "growth_and_core_trend_sma_sessions": 200,
            "trade_trigger": "initial allocation, then three-state changes only",
            "between_changes": "hold shares and allow weights to drift",
            "primary_cost_bps": primary_cost_bps,
            "stress_cost_bps": stress_cost_bps,
            "leverage": False,
            "parameter_search": False,
        },
        "data_receipts": {
            "main": main_receipt,
            "ndx": ndx_receipt,
            "old_gspc": old_gspc_receipt,
            "external_ixic": ixic_receipt,
            "external_gspc": external_gspc_receipt,
            "v10_failure": v10_failure_receipt,
            "v11_failure": v11_failure_receipt,
            "main_warmup_common_sessions": main_warmup,
            "old_proxy_warmup_common_sessions": old_warmup,
            "external_warmup_common_sessions": external_warmup,
            "old_proxy_translation": "QQQ->^NDX; SPY->^GSPC; SHY->constant CASH",
            "external_translation": "QQQ mechanism->^IXIC; SPY->^GSPC; SHY->constant CASH",
            "execution_clock": "close t signal; adjusted open t+1 for all three samples",
        },
        "main": main,
        "old_proxy": old_proxy,
        "external": external,
        "weight_integrity": weight_checks,
        "gates": gates,
        "passed_gate_count": int(sum(gates.values())),
        "required_gate_count": 29,
        "paper_entry_gates": paper_entry_gates,
        "paper_entry_passed_gate_count": int(sum(paper_entry_gates.values())),
        "paper_entry_required_gate_count": 23,
        "statistical_gates": statistical_gates,
        "global_dsr_promotion_sensitivity": {
            "passed": dsr_sensitivity_passed,
            **dsr_sensitivity,
        },
        "forward_requirements": {
            "minimum_new_sessions": 252,
            "minimum_completed_state_change_executions": 6,
            "after_cost_return_positive": True,
            "must_beat": "same-start SPY",
            "max_drawdown_not_worse_than_spy": True,
            "active_newey_west_t_at_least": 1.96,
            "active_psr_probability_at_least": 0.95,
            "historical_trades_may_be_backfilled": False,
        },
        "interpretation": {
            "policy": (
                "Keep 60% in the core; put the remaining 40% in growth only when relative "
                "strength and trend agree, otherwise core when its trend is positive, else defense."
            ),
            "proxy_limit": (
                "B/C are price-index mechanism tests with zero-interest CASH, not ETF total returns."
            ),
            "paper_decision": (
                "All 23 economic, temporal, exposure, and data gates passed; only isolated "
                "forward Paper may begin."
                if paper_eligible
                else "At least one of the 23 Paper-entry gates failed; do not create Paper."
            ),
            "reference_decision": (
                "Not reference-ready: statistical and selection-adjusted evidence plus 252 new "
                "sessions and 6 completed state changes remain separate gates."
            ),
        },
    }
    return main_result, target, audit
