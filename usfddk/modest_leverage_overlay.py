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
    confirmed_market_trend_states,
    fixed_weight_targets,
    modest_leverage_overlay_targets,
)
from usfddk.validation import deflated_sharpe_ratio, probabilistic_sharpe_ratio

V15_PROTOCOL_SHA256 = "e5254470ce00a0bf0941fd6ca15a5400323bdf837034968f41046fabcb9ef2a6"
V15_GLOBAL_SEARCH_TRIALS = 6_112
V15_VALIDATION_PANEL_SHA256 = (
    "57527472113333ac0fa67c900983b063652be6c112aeed477fd0b99f7fe86e6f"
)
V15_VALIDATION_ARCHIVE_SHA256 = (
    "9a61c9311e1981c95ec1f5d156915487d0c48ba6aae81ca4c1fcb5598ad017e2"
)
V15_VALIDATION_START = "2011-07-29"
V15_VALIDATION_END = "2026-07-31"
V15_VALIDATION_TICKERS = ("DIA", "QQQ", "SPY", "TQQQ", "UDOW", "UPRO")
V15_DATASETS = {
    "sp500": {"label": "S&P 500", "core": "SPY", "leveraged": "UPRO"},
    "nasdaq100": {"label": "Nasdaq-100", "core": "QQQ", "leveraged": "TQQQ"},
    "dow30": {"label": "Dow 30", "core": "DIA", "leveraged": "UDOW"},
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
            active, trials=V15_GLOBAL_SEARCH_TRIALS
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
            clean, trials=V15_GLOBAL_SEARCH_TRIALS
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
    if protocol_sha256 != V15_PROTOCOL_SHA256:
        raise ValueError("v15 協議雜湊與首次 3 倍 ETF 下載前凍結版本不同")
    if protocol_receipt.get("protocol_sha256") != V15_PROTOCOL_SHA256:
        raise ValueError("v15 協議凍結收據雜湊不符")
    if protocol_receipt.get("status") != "frozen_before_first_download_or_calculation":
        raise ValueError("v15 協議收據未證明先凍結再下載")
    if data_receipt.get("pre_registration_order_proved") is not True:
        raise ValueError("v15 資料收據未證明預先登錄順序")

    protocol_mtime = int(protocol_receipt.get("protocol_mtime_epoch", 0))
    first_snapshot_mtime = int(
        data_receipt.get("download", {}).get("first_snapshot_mtime_epoch", 0)
    )
    validated_snapshot_mtime = int(
        data_receipt.get("download", {}).get("validated_snapshot_mtime_epoch", 0)
    )
    if not 0 < protocol_mtime < first_snapshot_mtime <= validated_snapshot_mtime:
        raise ValueError("v15 協議檔時間未早於首次下載與契約快照")

    receipt_snapshot = data_receipt.get("snapshot") or {}
    for receipt in (receipt_snapshot, validation_receipt):
        if receipt.get("panel_sha256") != V15_VALIDATION_PANEL_SHA256:
            raise ValueError("v15 驗證面板雜湊不符")
        if receipt.get("archive_sha256") != V15_VALIDATION_ARCHIVE_SHA256:
            raise ValueError("v15 驗證 ZIP 雜湊不符")
    if receipt_snapshot.get("contract_ok") is not True:
        raise ValueError("v15 資料收據的有效快照未通過契約")
    if (validation_receipt.get("contract") or {}).get("ok") is not True:
        raise ValueError("v15 驗證快照契約未通過")

    tickers = tuple(sorted(panel.close.columns))
    if tickers != V15_VALIDATION_TICKERS:
        raise ValueError("v15 ETF 代號與下載前協議不同")
    if panel.start.strftime("%Y-%m-%d") != "2008-01-02":
        raise ValueError("v15 驗證資料起點與凍結協議不同")
    if panel.end.strftime("%Y-%m-%d") != V15_VALIDATION_END:
        raise ValueError("v15 驗證資料終點與凍結協議不同")
    return {
        "protocol_sha256": protocol_sha256,
        "panel_sha256": V15_VALIDATION_PANEL_SHA256,
        "archive_sha256": V15_VALIDATION_ARCHIVE_SHA256,
        "tickers": list(tickers),
        "start": panel.start.strftime("%Y-%m-%d"),
        "end": panel.end.strftime("%Y-%m-%d"),
        "rows": int(len(panel.close)),
        "snapshot_contract_ok": True,
        "protocol_frozen_before_first_download": True,
        "protocol_mtime_epoch": protocol_mtime,
        "first_snapshot_mtime_epoch": first_snapshot_mtime,
        "validated_snapshot_mtime_epoch": validated_snapshot_mtime,
        "first_contract_attempt_retained": bool(
            data_receipt.get("first_contract_attempt")
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
        "sharpe_beats_fixed_90_10": False,
        "calmar_beats_fixed_90_10": False,
        "drawdown_improves_fixed_90_10_5pp": False,
        "cagr_shortfall_vs_fixed_within_50bp": False,
        "50bps_cagr_shortfall_vs_fixed_within_50bp": False,
    }


def _economic_gates(data: dict[str, Any]) -> dict[str, bool]:
    strategy = data["strategy_metrics"]
    core = data["benchmark_metrics"]["core"]
    fixed = data["benchmark_metrics"]["fixed_90_10"]
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
            and rolling.get("median_cagr_difference", -1.0) > 0.0
        ),
        "sharpe_beats_fixed_90_10": bool(strategy["sharpe"] > fixed["sharpe"]),
        "calmar_beats_fixed_90_10": bool(strategy["calmar"] > fixed["calmar"]),
        "drawdown_improves_fixed_90_10_5pp": bool(
            strategy["max_drawdown"] >= fixed["max_drawdown"] + 0.05
        ),
        "cagr_shortfall_vs_fixed_within_50bp": bool(
            strategy["cagr"] >= fixed["cagr"] - 0.005
        ),
        "50bps_cagr_shortfall_vs_fixed_within_50bp": bool(
            data["cost_50bps"]["vs_fixed_90_10_cagr_difference"] >= -0.005
        ),
    }


def _dataset_results(
    panel: MarketPanel,
    *,
    label: str,
    core: str,
    leveraged: str,
    start: str,
    end: str,
    primary_cost_bps: float,
    stress_cost_bps: float,
) -> tuple[dict[str, Any], dict[str, pd.Series]]:
    before_start = panel.close.index < pd.Timestamp(start)
    core_warmup = int(panel.close.loc[before_start, core].notna().sum())
    leveraged_warmup = int(panel.close.loc[before_start, leveraged].notna().sum())
    base: dict[str, Any] = {
        "label": label,
        "assets": {"core": core, "leveraged": leveraged},
        "formal_period": {"start": start, "end": end},
        "core_prestart_sessions": core_warmup,
        "leveraged_prestart_sessions": leveraged_warmup,
        "required_prestart_sessions_each": 252,
    }
    if core_warmup < 252 or leveraged_warmup < 252:
        return {
            **base,
            "status": "insufficient_warmup",
            "data_gate_passed": False,
            "failure": (
                f"核心正式期前有效日 {core_warmup}/252；"
                f"3 倍 ETF 正式期前有效日 {leveraged_warmup}/252"
            ),
            "economic_gates": _failed_economic_gates(),
        }, {}

    targets = modest_leverage_overlay_targets(
        panel.close,
        core=core,
        leveraged=leveraged,
        initial_signal_before=start,
    )
    signals = targets.dropna(how="all")
    if signals.empty:
        return {
            **base,
            "status": "no_confirmed_signal",
            "data_gate_passed": False,
            "failure": "正式期以前沒有兩月確認訊號",
            "economic_gates": _failed_economic_gates(),
        }, {}

    initial_signal = pd.Timestamp(signals.index[0])
    position = panel.close.index.get_loc(initial_signal)
    if not isinstance(position, int) or position + 1 >= len(panel.close.index):
        raise ValueError(f"{label} 初始訊號沒有下一個可執行交易日")
    run_start = pd.Timestamp(panel.close.index[position + 1])
    first_execution_complete = all(
        frame.loc[run_start, [core, leveraged]].notna().all()
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
    fixed_target = fixed_weight_targets(
        panel.close, {core: 0.90, leveraged: 0.10}, signal_on=signal_text
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

    strategy = run(targets, "v15 小幅槓桿疊加", primary_cost_bps)
    core_result = run(core_target, f"{core} 買進持有", primary_cost_bps)
    leveraged_result = run(
        leveraged_target, f"{leveraged} 買進持有", primary_cost_bps
    )
    fixed_result = run(fixed_target, "固定 90/10", primary_cost_bps)
    strategy_50 = run(targets, "v15 50bps", stress_cost_bps)
    core_50 = run(core_target, f"{core} 50bps", stress_cost_bps)
    fixed_50 = run(fixed_target, "固定 90/10 50bps", stress_cost_bps)

    active_core, core_comparison = _active_statistics(strategy, core_result)
    active_fixed, fixed_comparison = _active_statistics(strategy, fixed_result)
    periods = (
        ("first", "2011-07-29", "2019-01-30"),
        ("second", "2019-01-31", "2026-07-31"),
    )
    target_rows = targets.dropna(how="all")
    target_sums = target_rows.sum(axis=1)
    realized_weights = strategy.weights
    weight_integrity = {
        "target_rows": int(len(target_rows)),
        "target_weight_sum_min": float(target_sums.min()),
        "target_weight_sum_max": float(target_sums.max()),
        "realized_fully_invested_fraction": float(
            np.isclose(realized_weights.sum(axis=1), 1.0, atol=1e-8).mean()
        ),
        "realized_minimum_asset_weight": float(realized_weights.min().min()),
        "realized_maximum_asset_weight": float(realized_weights.max().max()),
        "risk_on_internal_equity_notional": 1.20,
        "risk_off_internal_equity_notional": 1.00,
        "portfolio_borrowing_or_shorting": False,
    }
    weight_integrity["passed"] = bool(
        np.isclose(target_sums, 1.0, atol=1e-8).all()
        and weight_integrity["realized_fully_invested_fraction"] >= 0.99
        and weight_integrity["realized_minimum_asset_weight"] >= -1e-12
        and weight_integrity["realized_maximum_asset_weight"] <= 1.0 + 1e-8
    )

    states = confirmed_market_trend_states(panel.close, core=core)
    formal_states = states.loc[pd.Timestamp(start) : pd.Timestamp(end)]
    formal_signals = signals.loc[pd.Timestamp(start) : pd.Timestamp(end)]
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
            "leveraged_buy_and_hold_diagnostic": leveraged_result.metrics,
            "fixed_90_10": fixed_result.metrics,
        },
        "comparison_vs_core": core_comparison,
        "comparison_vs_fixed_90_10": fixed_comparison,
        "cost_50bps": {
            "strategy_metrics": strategy_50.metrics,
            "core_metrics": core_50.metrics,
            "fixed_90_10_metrics": fixed_50.metrics,
            "vs_core_cagr_difference": (
                strategy_50.metrics["cagr"] - core_50.metrics["cagr"]
            ),
            "vs_fixed_90_10_cagr_difference": (
                strategy_50.metrics["cagr"] - fixed_50.metrics["cagr"]
            ),
        },
        "fixed_halves_vs_core": _halves(strategy, core_result, periods),
        "rolling_five_year_vs_core": _rolling_comparison(strategy, core_result),
        "weight_integrity": weight_integrity,
        "signals": {
            "completed_month_ends_in_formal_period": int(len(formal_states)),
            "state_month_counts": {
                state: int((formal_states == state).sum())
                for state in ("risk_on", "risk_off")
            },
            "monthly_target_signals_in_formal_period": int(len(formal_signals)),
            "completed_rebalances_in_formal_period": int(
                strategy.diagnostics["rebalance_count"]
            ),
            "latest_state": str(states.iloc[-1]),
            "latest_completed_month_end": pd.Timestamp(states.index[-1]).strftime(
                "%Y-%m-%d"
            ),
        },
    }
    result["economic_gates"] = _economic_gates(result)
    return result, {"vs_core": active_core, "vs_fixed_90_10": active_fixed}


def evaluate_modest_leverage_overlay_research(
    validation_panel: MarketPanel,
    *,
    validation_receipt: dict[str, Any],
    protocol_receipt: dict[str, Any],
    data_receipt: dict[str, Any],
    protocol_sha256: str,
    primary_cost_bps: float = 10.0,
    stress_cost_bps: float = 50.0,
) -> dict[str, Any]:
    """Evaluate v15 only after its rules and actual 3x ETF sample were frozen."""
    snapshot = _snapshot_integrity(
        validation_panel,
        validation_receipt,
        protocol_receipt,
        data_receipt,
        protocol_sha256=protocol_sha256,
    )
    datasets: dict[str, Any] = {}
    active_core: dict[str, pd.Series] = {}
    active_fixed: dict[str, pd.Series] = {}
    for key, spec in V15_DATASETS.items():
        data, active = _dataset_results(
            validation_panel,
            label=str(spec["label"]),
            core=str(spec["core"]),
            leveraged=str(spec["leveraged"]),
            start=V15_VALIDATION_START,
            end=V15_VALIDATION_END,
            primary_cost_bps=primary_cost_bps,
            stress_cost_bps=stress_cost_bps,
        )
        datasets[key] = data
        if active:
            active_core[key] = active["vs_core"]
            active_fixed[key] = active["vs_fixed_90_10"]

    economic_gates = {
        f"{dataset_key}_{gate_name}": bool(passed)
        for dataset_key, data in datasets.items()
        for gate_name, passed in data["economic_gates"].items()
    }
    data_gates = {
        "snapshot_contract_hashes_and_preregistration_pass": True,
        **{
            f"{key}_warmup_execution_and_weights_pass": bool(data["data_gate_passed"])
            for key, data in datasets.items()
        },
    }
    paper_eligible = all(economic_gates.values()) and all(data_gates.values())

    statistical_gates: dict[str, bool] = {}
    statistical_details: dict[str, Any] = {}
    for key, data in datasets.items():
        if data["status"] != "completed":
            for benchmark in ("core", "fixed_90_10"):
                statistical_gates[f"{key}_vs_{benchmark}_newey_west_t_1_96"] = False
                statistical_gates[f"{key}_vs_{benchmark}_psr_95pct"] = False
                statistical_gates[f"{key}_vs_{benchmark}_global_dsr_95pct"] = False
            statistical_details[key] = {"status": "not_evaluable_due_to_data_gate"}
            continue
        comparisons = {
            "core": data["comparison_vs_core"],
            "fixed_90_10": data["comparison_vs_fixed_90_10"],
        }
        statistical_details[key] = {}
        for benchmark, comparison in comparisons.items():
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
    if len(active_core) == len(V15_DATASETS):
        pooled_core = pd.concat(active_core, axis=1, join="inner").mean(axis=1)
        pooled_fixed = pd.concat(active_fixed, axis=1, join="inner").mean(axis=1)
        pooled = {
            "equal_weight_active_vs_core": _series_statistics(pooled_core),
            "equal_weight_active_vs_fixed_90_10": _series_statistics(pooled_fixed),
            "gate_eligible": False,
            "reason": "預先指定為診斷；不能覆蓋任何單一市場失敗",
        }

    statistically_confirmed = paper_eligible and all(statistical_gates.values())
    return {
        "schema_version": 1,
        "strategy_name": "v15 小幅槓桿疊加兩月確認趨勢",
        "status": (
            "historically_confirmed_pending_live"
            if statistically_confirmed
            else "paper_entry_passed_statistical_pending"
            if paper_eligible
            else "new_3x_etf_validation_failed"
        ),
        "paper_eligible": paper_eligible,
        "statistically_confirmed": statistically_confirmed,
        "historically_confirmed": statistically_confirmed,
        "promotion_ready": False,
        "reference_trade_candidate": False,
        "promotion_effect": "create_isolated_paper_only" if paper_eligible else "none",
        "evidence_boundary": {
            "v14_twenty_year_2x_sample": "design exploration only",
            "v15_actual_3x_sample": "first-seen product paths after protocol freeze",
            "independent_confirmation_years": 15,
            "cannot_claim_independent_twenty_year_v15": True,
        },
        "protocol": {
            "path": "docs/V15_MODEST_LEVERAGE_OVERLAY_PROTOCOL.md",
            "sha256": protocol_sha256,
            "frozen_before_new_validation_download": True,
            "global_search_trials": V15_GLOBAL_SEARCH_TRIALS,
        },
        "parameters": {
            "trend_sma_sessions": 200,
            "confirmation_months": 2,
            "risk_on": {"core": 0.90, "daily_3x_etf": 0.10},
            "risk_off": {"core": 1.00},
            "risk_on_approximate_equity_notional": 1.20,
            "risk_off_approximate_equity_notional": 1.00,
            "monthly_rebalance": True,
            "execution": "completed month-end close signal; next-session adjusted open",
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
            "minimum_completed_rebalances": 6,
            "after_cost_return_positive": True,
            "must_beat_same_start": ["one-times core ETF", "fixed 90/10 control"],
            "max_drawdown_not_worse_than_both_benchmarks": True,
            "active_newey_west_t_at_least": 1.96,
            "active_psr_probability_at_least": 0.95,
            "historical_trades_may_be_backfilled": False,
        },
        "risk_disclosure": {
            "daily_objective": (
                "UPRO, TQQQ and UDOW seek 3x daily benchmark returns, not a fixed "
                "long-horizon multiple."
            ),
            "compounding": (
                "Daily reset, volatility, expenses and compounding can materially alter "
                "long-horizon outcomes."
            ),
            "loss_risk": (
                "A 10% sleeve in a daily 3x ETF raises risk-on nominal equity exposure "
                "to about 120% and can lose more than the one-times ETF."
            ),
        },
        "interpretation": {
            "paper_decision": (
                "All frozen economic and integrity gates passed; only isolated Paper may start."
                if paper_eligible
                else "At least one frozen economic or integrity gate failed; do not create v15 Paper."
            ),
            "reference_decision": (
                "Not reference-ready; full historical statistics and at least 252 new Paper "
                "sessions must pass before readiness may expose an allocation."
            ),
        },
    }
