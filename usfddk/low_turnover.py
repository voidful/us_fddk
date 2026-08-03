from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from usfddk.data import fetch_yfinance, panel_fingerprint, save_snapshot
from usfddk.engine import run_backtest
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
    low_turnover_relative_growth_states,
    low_turnover_relative_growth_targets,
)
from usfddk.validation import deflated_sharpe_ratio, probabilistic_sharpe_ratio

V9_PROTOCOL_SHA256 = "3c147b87cf59c73c4a00ceb934763a9a7d75ffc25eb62cde3a1727c735954d8c"
V9_DATA_CONTRACT_SHA256 = "b4250178d43a9d8eb75d1e03e5d44f4303d5a3e677ef1c88d3010d2e6782b00b"
V9_EXTERNAL_FETCH_START = "1971-02-05"
V9_EXTERNAL_END = "1988-12-30"
V9_EXTERNAL_START = "1973-01-03"
V9_MAIN_START = "2006-07-31"
V9_MAIN_END = "2026-07-31"
V9_PROXY_START = "1989-01-03"
V9_PROXY_END = "2006-07-28"
V9_GLOBAL_SEARCH_TRIALS = 6_106
V9_IXIC_PANEL_SHA256 = "76bc29b61c480e8c44032e4aeaea801e9ea97a1aebceb758bda84df8a8b7d2c9"
V9_IXIC_ARCHIVE_SHA256 = "b845aecd3175584f8dc40e0db8e93ec9427e2a9f491f0824ec7264f6cda9eb22"
V9_EXTERNAL_GSPC_PANEL_SHA256 = (
    "414d787995baeceb921bb088d5b54d08612e8b60d7a8443785c9603335ffc5ca"
)
V9_EXTERNAL_GSPC_ARCHIVE_SHA256 = (
    "b5bcc28cf4fdddc83e60bf08601c83cd67eff44132c92a4980d6d37a20a2d471"
)
V9_EXTERNAL_COMMON_PANEL_SHA256 = (
    "557deb72e586194965d3a9624ee9769ef383ee7fa5d55295e5beeaaeff0561b0"
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


def validate_v9_external_index(
    panel: MarketPanel,
    *,
    ticker: str,
    protocol_sha256: str,
    minimum_rows: int = 4_300,
) -> ContractResult:
    """Apply the external-index contract frozen before the first download."""
    errors: list[str] = []
    warnings: list[str] = []
    stats: dict[str, Any] = {}
    close = panel.close
    fields = panel.field_map()

    if list(close.columns) != [ticker]:
        errors.append(f"欄位必須只有 {ticker}")
    if not close.index.is_monotonic_increasing or close.index.has_duplicates:
        errors.append("日期索引不是嚴格遞增且唯一")
    if close.empty:
        errors.append("Close 面板為空")
        return ContractResult(False, tuple(errors), tuple(warnings), stats)

    stats.update(
        {
            "ticker": ticker,
            "rows": int(len(close)),
            "start": panel.start.strftime("%Y-%m-%d"),
            "end": panel.end.strftime("%Y-%m-%d"),
        }
    )
    if panel.start.strftime("%Y-%m-%d") != V9_EXTERNAL_FETCH_START:
        errors.append(f"第一筆不是 {V9_EXTERNAL_FETCH_START}")
    if panel.end.strftime("%Y-%m-%d") != V9_EXTERNAL_END:
        errors.append(f"最後一筆不是 {V9_EXTERNAL_END}")
    if len(close) < minimum_rows:
        errors.append(f"資料列數 {len(close)} < {minimum_rows}")

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
        frame = fields[field]
        values = frame.to_numpy(dtype=float)
        if not bool(np.isfinite(values).all() and (values > 0.0).all()):
            errors.append(f"{field} 含非有限值、零或負數")
    volume = panel.volume.to_numpy(dtype=float)
    if not bool(np.isfinite(volume).all() and (volume >= 0.0).all()):
        errors.append("Volume 含非有限值或負數")

    o = panel.open[ticker]
    h = panel.high[ticker]
    low = panel.low[ticker]
    c = panel.close[ticker]
    ohlc_violations = int(((h < o) | (h < c) | (low > o) | (low > c)).sum())
    stats["ohlc_violations"] = ohlc_violations
    if ohlc_violations:
        errors.append(f"OHLC 關係違反 {ohlc_violations} 筆")

    max_absolute_close_return = float(c.pct_change(fill_method=None).abs().max())
    stats["max_absolute_close_return"] = max_absolute_close_return
    if max_absolute_close_return > 0.35:
        errors.append(f"單日 Close 絕對報酬 {max_absolute_close_return:.2%} > 35%")

    metadata = panel.metadata
    if metadata.get("provider") != "Yahoo Finance via yfinance":
        errors.append("provider metadata 不符")
    if not metadata.get("adjustment"):
        errors.append("缺少還原方法 metadata")
    if metadata.get("research_protocol_sha256") != protocol_sha256:
        errors.append("研究協議 SHA-256 metadata 不符")
    return ContractResult(not errors, tuple(errors), tuple(warnings), stats)


def build_v9_external_common_panel(
    ixic_panel: MarketPanel, gspc_panel: MarketPanel
) -> MarketPanel:
    """Join the two frozen external snapshots on common sessions only."""
    common = ixic_panel.close.index.intersection(gspc_panel.close.index).sort_values()

    def joined(field: str) -> pd.DataFrame:
        ixic = ixic_panel.field_map()[field].loc[common, ["^IXIC"]]
        gspc = gspc_panel.field_map()[field].loc[common, ["^GSPC"]]
        return pd.concat([gspc, ixic], axis=1)

    return MarketPanel(
        open=joined("Open"),
        high=joined("High"),
        low=joined("Low"),
        close=joined("Close"),
        volume=joined("Volume"),
        metadata={
            "derived_from_frozen_snapshots": True,
            "join": "common sessions only; no filling or interpolation",
            "research_protocol_sha256": V9_PROTOCOL_SHA256,
        },
    )


def validate_v9_external_common(panel: MarketPanel) -> ContractResult:
    errors: list[str] = []
    stats: dict[str, Any] = {
        "rows": int(len(panel.close)),
        "start": panel.start.strftime("%Y-%m-%d"),
        "end": panel.end.strftime("%Y-%m-%d"),
    }
    if list(panel.close.columns) != ["^GSPC", "^IXIC"]:
        errors.append("共同面板欄位或順序不符")
    if panel.start.strftime("%Y-%m-%d") != V9_EXTERNAL_FETCH_START:
        errors.append(f"共同面板第一筆不是 {V9_EXTERNAL_FETCH_START}")
    if panel.end.strftime("%Y-%m-%d") != V9_EXTERNAL_END:
        errors.append(f"共同面板最後一筆不是 {V9_EXTERNAL_END}")
    if len(panel.close) < 4_300:
        errors.append(f"共同面板資料列數 {len(panel.close)} < 4300")

    missing = {
        field: int(frame.isna().sum().sum()) for field, frame in panel.field_map().items()
    }
    stats["missing_by_field"] = missing
    if any(missing.values()):
        errors.append("共同面板 OHLCV 含缺值")
    warmup = panel.close.loc[panel.close.index < pd.Timestamp(V9_EXTERNAL_START)]
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


def fetch_and_freeze_v9_external(
    output_dir: str | Path,
    *,
    protocol_sha256: str,
    data_contract_sha256: str,
) -> tuple[dict[str, Any], bool]:
    """Fetch once under the frozen contract and persist content-addressed snapshots."""
    if protocol_sha256 != V9_PROTOCOL_SHA256:
        raise ValueError("v9 協議雜湊與下載前凍結版本不同")
    if data_contract_sha256 != V9_DATA_CONTRACT_SHA256:
        raise ValueError("v9 外部資料契約雜湊與下載前凍結版本不同")

    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    existing = sorted(destination.glob("snapshot_v9_*_19710205_19881230_*.zip"))
    if existing:
        raise ValueError(
            "v9 外部快照已凍結，拒絕重新下載或覆寫；請直接執行 v9-low-turnover"
        )
    panels: dict[str, MarketPanel] = {}
    receipts: dict[str, Any] = {}
    for role, ticker in (("growth", "^IXIC"), ("core", "^GSPC")):
        fetched = fetch_yfinance(
            [ticker], V9_EXTERNAL_FETCH_START, V9_EXTERNAL_END, threads=False
        )
        panel = _with_metadata(
            fetched,
            {
                "research_protocol_sha256": protocol_sha256,
                "external_data_contract_sha256": data_contract_sha256,
                "requested_start": V9_EXTERNAL_FETCH_START,
                "requested_end": V9_EXTERNAL_END,
                "role": role,
            },
        )
        contract = validate_v9_external_index(
            panel, ticker=ticker, protocol_sha256=protocol_sha256
        )
        fingerprint = panel_fingerprint(panel)
        safe_ticker = ticker.lstrip("^").lower()
        path = destination / (
            f"snapshot_v9_{safe_ticker}_19710205_19881230_{fingerprint[:8]}.zip"
        )
        manifest = save_snapshot(panel, path, contract=contract)
        panels[role] = panel
        receipts[role] = {
            "path": str(path),
            "ticker": ticker,
            "panel_sha256": manifest["panel_sha256"],
            "archive_sha256": manifest["archive_sha256"],
            "rows": manifest["rows"],
            "start": manifest["start"],
            "end": manifest["end"],
            "created_at": manifest["created_at"],
            "provider_metadata": manifest["provider_metadata"],
            "contract": manifest["contract"],
        }

    common = build_v9_external_common_panel(panels["growth"], panels["core"])
    common_contract = validate_v9_external_common(common)
    receipt = {
        "schema_version": 1,
        "protocol": {
            "path": "docs/V9_LOW_TURNOVER_EXTERNAL_PROTOCOL.md",
            "sha256": protocol_sha256,
        },
        "external_data_contract": {
            "path": "docs/V9_EXTERNAL_DATA_CONTRACT.md",
            "sha256": data_contract_sha256,
        },
        "snapshots": receipts,
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
    all_ok = all(
        bool(item["contract"] and item["contract"]["ok"])
        for item in receipts.values()
    ) and common_contract.ok
    return receipt, bool(all_ok)


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
        "drawdown_difference": (
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
            active, trials=V9_GLOBAL_SEARCH_TRIALS
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
    start: str,
    end: str,
    half_periods: tuple[tuple[str, str, str], ...],
    label: str,
    primary_cost_bps: float,
    stress_cost_bps: float,
) -> tuple[BacktestResult, pd.DataFrame, dict[str, Any]]:
    target = low_turnover_relative_growth_targets(
        panel.close,
        core=core,
        growth=growth,
        core_weight_when_risk_on=0.60,
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

    strategy = run(target, "低換手相對成長", primary_cost_bps)
    market = run(market_target, "市場", primary_cost_bps)
    opportunity = run(opportunity_target, "成長機會成本", primary_cost_bps)
    static = run(static_target, "一次性 60/40", primary_cost_bps)
    strategy_50 = run(target, "低換手相對成長 50bps", stress_cost_bps)
    market_50 = run(market_target, "市場 50bps", stress_cost_bps)
    comparison = _comparison(strategy, market)
    rolling = _rolling_comparison(strategy, market)
    half_rows = _halves(strategy, market, half_periods)
    states = low_turnover_relative_growth_states(
        panel.close, core=core, growth=growth
    )
    formal_states = states.loc[pd.Timestamp(start) : pd.Timestamp(end)]
    formal_signals = signals.loc[pd.Timestamp(start) : pd.Timestamp(end)]
    latest_state = bool(states.iloc[-1])
    final_weights = strategy.weights.iloc[-1]
    last_signal = pd.Timestamp(signals.index[-1])
    pending_after_snapshot = bool(last_signal >= panel.end)
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
            "state_change_signals_in_formal_period": int(len(formal_signals)),
            "completed_executions_in_formal_period": int(
                strategy.diagnostics["rebalance_count"]
            ),
            "latest_completed_month_end": pd.Timestamp(states.index[-1]).strftime(
                "%Y-%m-%d"
            ),
            "latest_risk_on": latest_state,
            "latest_state_change_signal": last_signal.strftime("%Y-%m-%d"),
            "pending_execution_after_snapshot": pending_after_snapshot,
        },
        "current_policy_allocation": {
            core: 0.60 if latest_state else 1.0,
            growth: 0.40 if latest_state else 0.0,
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


def evaluate_low_turnover_research(
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
    external_data_receipt: dict[str, Any],
    protocol_sha256: str,
    data_contract_sha256: str,
    primary_cost_bps: float = 10.0,
    stress_cost_bps: float = 50.0,
) -> tuple[BacktestResult, pd.DataFrame, dict[str, Any]]:
    """Evaluate the frozen v9 policy across all three preregistered periods."""
    if protocol_sha256 != V9_PROTOCOL_SHA256:
        raise ValueError("v9 協議雜湊與第一次計算前凍結版本不同")
    if data_contract_sha256 != V9_DATA_CONTRACT_SHA256:
        raise ValueError("v9 外部資料契約雜湊與首次下載前凍結版本不同")

    _validate_snapshot(
        main_panel,
        main_receipt,
        label="v9 主樣本",
        required_tickers=("SPY", "QQQ"),
        expected_panel_sha256=V7_MAIN_PANEL_SHA256,
        expected_archive_sha256=V7_MAIN_ARCHIVE_SHA256,
        expected_start="2004-01-02",
        expected_end=V9_MAIN_END,
        exact_tickers=False,
    )
    _validate_snapshot(
        ndx_panel,
        ndx_receipt,
        label="v9 Nasdaq-100 代理",
        required_tickers=("^NDX",),
        expected_panel_sha256=V7_NDX_PANEL_SHA256,
        expected_archive_sha256=V7_NDX_ARCHIVE_SHA256,
        expected_start="1985-10-01",
        expected_end=V9_PROXY_END,
        exact_tickers=True,
    )
    _validate_snapshot(
        old_gspc_panel,
        old_gspc_receipt,
        label="v9 舊 S&P 500 代理",
        required_tickers=("^GSPC",),
        expected_panel_sha256=V7_GSPC_PANEL_SHA256,
        expected_archive_sha256=V7_GSPC_ARCHIVE_SHA256,
        expected_start="1987-01-02",
        expected_end=V9_PROXY_END,
        exact_tickers=True,
    )
    _validate_snapshot(
        ixic_panel,
        ixic_receipt,
        label="v9 Nasdaq Composite 外部樣本",
        required_tickers=("^IXIC",),
        expected_panel_sha256=V9_IXIC_PANEL_SHA256,
        expected_archive_sha256=V9_IXIC_ARCHIVE_SHA256,
        expected_start=V9_EXTERNAL_FETCH_START,
        expected_end=V9_EXTERNAL_END,
        exact_tickers=True,
    )
    _validate_snapshot(
        external_gspc_panel,
        external_gspc_receipt,
        label="v9 外部 S&P 500 樣本",
        required_tickers=("^GSPC",),
        expected_panel_sha256=V9_EXTERNAL_GSPC_PANEL_SHA256,
        expected_archive_sha256=V9_EXTERNAL_GSPC_ARCHIVE_SHA256,
        expected_start=V9_EXTERNAL_FETCH_START,
        expected_end=V9_EXTERNAL_END,
        exact_tickers=True,
    )
    ixic_contract = validate_v9_external_index(
        ixic_panel, ticker="^IXIC", protocol_sha256=protocol_sha256
    )
    gspc_contract = validate_v9_external_index(
        external_gspc_panel, ticker="^GSPC", protocol_sha256=protocol_sha256
    )
    ixic_contract.require()
    gspc_contract.require()

    external_panel = build_v9_external_common_panel(
        ixic_panel, external_gspc_panel
    )
    external_common_contract = validate_v9_external_common(external_panel)
    external_common_contract.require()
    if panel_fingerprint(external_panel) != V9_EXTERNAL_COMMON_PANEL_SHA256:
        raise ValueError("v9 外部共同面板不是首次下載後凍結內容")
    if external_data_receipt.get("protocol", {}).get("sha256") != protocol_sha256:
        raise ValueError("v9 外部資料收據的協議雜湊不符")
    if (
        external_data_receipt.get("external_data_contract", {}).get("sha256")
        != data_contract_sha256
    ):
        raise ValueError("v9 外部資料收據的資料契約雜湊不符")
    if (
        external_data_receipt.get("derived_common_panel", {}).get("panel_sha256")
        != V9_EXTERNAL_COMMON_PANEL_SHA256
    ):
        raise ValueError("v9 外部資料收據的共同面板雜湊不符")

    main_warmup = int(
        main_panel.close.loc[
            main_panel.close.index < pd.Timestamp(V9_MAIN_START), ["SPY", "QQQ"]
        ]
        .notna()
        .all(axis=1)
        .sum()
    )
    if main_warmup < 252:
        raise ValueError("v9 主樣本暖機不足 252 個共同有效交易日")
    old_proxy_panel = build_v7_proxy_panel(ndx_panel, old_gspc_panel)
    old_warmup = int(
        old_proxy_panel.close.loc[
            old_proxy_panel.close.index < pd.Timestamp(V9_PROXY_START),
            ["^GSPC", "^NDX"],
        ]
        .notna()
        .all(axis=1)
        .sum()
    )
    if old_warmup < 252:
        raise ValueError("v9 舊代理暖機不足 252 個共同有效交易日")
    external_warmup = int(external_common_contract.stats["warmup_common_sessions"])

    main_result, target, main = _dataset_results(
        main_panel,
        core="SPY",
        growth="QQQ",
        start=V9_MAIN_START,
        end=V9_MAIN_END,
        half_periods=(
            ("first", "2006-07-31", "2016-07-29"),
            ("second", "2016-08-01", "2026-07-31"),
        ),
        label="v9 ETF ",
        primary_cost_bps=primary_cost_bps,
        stress_cost_bps=stress_cost_bps,
    )
    old_result, _, old_proxy = _dataset_results(
        old_proxy_panel,
        core="^GSPC",
        growth="^NDX",
        start=V9_PROXY_START,
        end=V9_PROXY_END,
        half_periods=(
            ("first", "1989-01-03", "1997-09-30"),
            ("second", "1997-10-01", "2006-07-28"),
        ),
        label="v9 舊代理 ",
        primary_cost_bps=primary_cost_bps,
        stress_cost_bps=stress_cost_bps,
    )
    external_result, _, external = _dataset_results(
        external_panel,
        core="^GSPC",
        growth="^IXIC",
        start=V9_EXTERNAL_START,
        end=V9_EXTERNAL_END,
        half_periods=(
            ("first", "1973-01-03", "1980-12-31"),
            ("second", "1981-01-02", "1988-12-30"),
        ),
        label="v9 全新外部 ",
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
    gates["23_all_data_translation_warmup_contracts_and_hashes_pass"] = True
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
        "strategy_name": "v9 低換手相對成長傾斜",
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
            "path": "docs/V9_LOW_TURNOVER_EXTERNAL_PROTOCOL.md",
            "sha256": protocol_sha256,
            "external_data_contract_sha256": data_contract_sha256,
            "frozen_before_first_v9_calculation": True,
            "external_sample_frozen_before_first_download": True,
            "data_independent": False,
            "derived_after_v8": True,
            "global_search_trials": V9_GLOBAL_SEARCH_TRIALS,
        },
        "parameters": {
            "core_weight_when_risk_on": 0.60,
            "conditional_growth_weight": 0.40,
            "risk_off_destination": "core market",
            "momentum": "close(t-21) / close(t-252) - 1",
            "growth_trend_sma_sessions": 200,
            "trade_trigger": "initial allocation, then Boolean regime changes only",
            "between_changes": "hold shares and allow weights to drift",
            "equity_exposure": 1.0,
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
            "external_data_receipt": external_data_receipt,
            "main_warmup_common_sessions": main_warmup,
            "old_proxy_warmup_common_sessions": old_warmup,
            "external_warmup_common_sessions": external_warmup,
            "old_proxy_translation": "QQQ->^NDX; SPY->^GSPC; common sessions only",
            "external_translation": "QQQ mechanism->^IXIC; SPY->^GSPC; common sessions only",
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
            "minimum_completed_regime_change_executions": 6,
            "after_cost_return_positive": True,
            "must_beat": "same-start SPY",
            "max_drawdown_not_worse_than_spy": True,
            "active_newey_west_t_at_least": 1.96,
            "active_psr_probability_at_least": 0.95,
            "historical_trades_may_be_backfilled": False,
        },
        "interpretation": {
            "policy": (
                "Always 100% equities; use 60% core and 40% growth only when relative "
                "strength and trend agree; trade only on regime changes."
            ),
            "external_limit": (
                "Nasdaq Composite is a broader price-index mechanism test, not historical "
                "QQQ or a dividend-inclusive tradable return."
            ),
            "paper_decision": (
                "All 23 economic, temporal, exposure, and data gates passed; only isolated "
                "forward Paper may begin."
                if paper_eligible
                else "At least one of the 23 Paper-entry gates failed; do not create Paper."
            ),
            "reference_decision": (
                "Not reference-ready: historical statistics, global selection sensitivity, "
                "and 252 new sessions plus 6 completed regime changes remain separate gates."
            ),
        },
    }
    return main_result, target, audit
