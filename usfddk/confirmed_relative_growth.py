from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from usfddk.engine import run_backtest
from usfddk.hierarchical_defense import (
    _halves,
    _one_time_weights,
    _rolling_comparison,
    _slice_result,
)
from usfddk.metrics import newey_west_mean_test
from usfddk.models import BacktestResult, MarketPanel
from usfddk.strategies import (
    buy_and_hold_targets,
    confirmed_relative_growth_matched_targets,
    confirmed_relative_growth_states,
    confirmed_relative_growth_targets,
)
from usfddk.validation import deflated_sharpe_ratio, probabilistic_sharpe_ratio

V13_PROTOCOL_SHA256 = (
    "177e727f3a2c59ef9f5eb7b83b67b67468a8740bbeff0f22a9921fdbb034e0f1"
)
V13_GLOBAL_SEARCH_TRIALS = 6_110
V13_VALIDATION_PANEL_SHA256 = (
    "1301e2e1b484dec6022653b7d2caa040ba60af7bc676ba521ee7ba8a0fc5b6fa"
)
V13_VALIDATION_ARCHIVE_SHA256 = (
    "e16c3f4d0bc992fea5e7b416465ac1c0b1273380ab2b8dd9b92ea46ef313acf1"
)
V13_VALIDATION_START = "2006-07-31"
V13_VALIDATION_END = "2026-07-31"
V13_VALIDATION_TICKERS = ("EFA", "EFG", "IWB", "IWF", "IWM", "IWO", "SHY")
V13_DATASETS = {
    "russell_1000": {
        "label": "Russell 1000 大中型股",
        "core": "IWB",
        "growth": "IWF",
        "defensive": "SHY",
    },
    "russell_2000": {
        "label": "Russell 2000 小型股",
        "core": "IWM",
        "growth": "IWO",
        "defensive": "SHY",
    },
    "eafe": {
        "label": "EAFE 美國以外已開發市場",
        "core": "EFA",
        "growth": "EFG",
        "defensive": "SHY",
    },
}


def _comparison(strategy: BacktestResult, benchmark: BacktestResult) -> dict[str, Any]:
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
            active, trials=V13_GLOBAL_SEARCH_TRIALS
        ),
    }


def _snapshot_integrity(
    panel: MarketPanel,
    receipt: dict[str, Any],
    *,
    protocol_sha256: str,
) -> dict[str, Any]:
    if protocol_sha256 != V13_PROTOCOL_SHA256:
        raise ValueError("v13 協議雜湊與新資料下載前凍結版本不同")
    if receipt.get("panel_sha256") != V13_VALIDATION_PANEL_SHA256:
        raise ValueError("v13 新驗證面板雜湊與凍結收據不同")
    if receipt.get("archive_sha256") != V13_VALIDATION_ARCHIVE_SHA256:
        raise ValueError("v13 新驗證 ZIP 雜湊與凍結收據不同")
    actual_tickers = tuple(sorted(panel.close.columns))
    if actual_tickers != V13_VALIDATION_TICKERS:
        raise ValueError("v13 新驗證 ETF 代號與下載前協議不同")
    if panel.start.strftime("%Y-%m-%d") != "2004-01-02":
        raise ValueError("v13 新驗證資料起點與凍結收據不同")
    if panel.end.strftime("%Y-%m-%d") != V13_VALIDATION_END:
        raise ValueError("v13 新驗證資料終點與凍結收據不同")
    contract = receipt.get("contract") or {}
    if contract.get("ok") is not True:
        raise ValueError("v13 新驗證快照的資料契約未通過")
    return {
        "protocol_sha256": protocol_sha256,
        "panel_sha256": V13_VALIDATION_PANEL_SHA256,
        "archive_sha256": V13_VALIDATION_ARCHIVE_SHA256,
        "tickers": list(actual_tickers),
        "start": panel.start.strftime("%Y-%m-%d"),
        "end": panel.end.strftime("%Y-%m-%d"),
        "rows": int(len(panel.close)),
        "snapshot_contract_ok": True,
    }


def _run_targets(
    panel: MarketPanel,
    targets: pd.DataFrame,
    *,
    name: str,
    cost_bps: float,
    run_start: pd.Timestamp,
    formal_start: str,
    formal_end: str,
) -> BacktestResult:
    full = run_backtest(
        panel,
        targets,
        name=name,
        cost_bps=cost_bps,
        start=run_start,
    )
    return _slice_result(full, formal_start, formal_end)


def _economic_gates(data: dict[str, Any]) -> dict[str, bool]:
    strategy = data["strategy_metrics"]
    market = data["benchmark_metrics"]["market"]
    matched = data["benchmark_metrics"]["matched"]
    rolling = data["rolling_five_year"]["summary"]
    return {
        "cagr_beats_market_10bp": bool(strategy["cagr"] > market["cagr"] + 0.001),
        "sharpe_beats_market": bool(strategy["sharpe"] > market["sharpe"]),
        "drawdown_not_worse_than_market_5pp": bool(
            strategy["max_drawdown"] >= market["max_drawdown"] - 0.05
        ),
        "calmar_beats_market": bool(strategy["calmar"] > market["calmar"]),
        "50bps_cagr_beats_market_10bp": bool(
            data["cost_50bps"]["cagr_difference"] > 0.001
        ),
        "both_halves_cagr_beat_market_10bp": bool(
            all(
                half["cagr_difference"] > 0.001
                for half in data["fixed_halves"].values()
            )
        ),
        "rolling_wins_60pct_and_positive_median": bool(
            rolling.get("cagr_win_fraction", 0.0) >= 0.60
            and rolling.get("median_cagr_difference", -1.0) > 0.0
        ),
        "cagr_beats_matched_10bp": bool(strategy["cagr"] > matched["cagr"] + 0.001),
        "sharpe_beats_matched": bool(strategy["sharpe"] > matched["sharpe"]),
        "drawdown_not_worse_than_matched_5pp": bool(
            strategy["max_drawdown"] >= matched["max_drawdown"] - 0.05
        ),
    }


def _diagnostic_after_first_valid_signal(
    panel: MarketPanel,
    *,
    core: str,
    growth: str,
    defensive: str,
    end: str,
    cost_bps: float,
) -> dict[str, Any] | None:
    targets = confirmed_relative_growth_targets(
        panel.close,
        core=core,
        growth=growth,
        defensive=defensive,
    )
    signals = targets.dropna(how="all")
    if signals.empty:
        return None
    signal = pd.Timestamp(signals.index[0])
    position = panel.close.index.get_loc(signal)
    if not isinstance(position, int) or position + 1 >= len(panel.close.index):
        return None
    execution = pd.Timestamp(panel.close.index[position + 1])
    start = execution.strftime("%Y-%m-%d")
    strategy = run_backtest(
        panel,
        targets,
        name="v13 暖機不足診斷",
        cost_bps=cost_bps,
        start=execution,
    )
    market = run_backtest(
        panel,
        buy_and_hold_targets(panel.close, core, signal_on=signal.strftime("%Y-%m-%d")),
        name=f"{core} 同起點診斷",
        cost_bps=cost_bps,
        start=execution,
    )
    strategy = _slice_result(strategy, start, end)
    market = _slice_result(market, start, end)
    return {
        "gate_eligible": False,
        "reason": "正式固定起點前暖機不足；此段只作診斷，不計入門檻",
        "start": start,
        "end": end,
        "strategy_metrics": strategy.metrics,
        "market_metrics": market.metrics,
        "comparison": _comparison(strategy, market),
    }


def _dataset_results(
    panel: MarketPanel,
    *,
    label: str,
    core: str,
    growth: str,
    defensive: str,
    start: str,
    end: str,
    primary_cost_bps: float,
    stress_cost_bps: float,
) -> dict[str, Any]:
    required = [core, growth, defensive]
    common = panel.close[required].notna().all(axis=1)
    warmup_sessions = int(common.loc[common.index < pd.Timestamp(start)].sum())
    first_common = common.index[common]
    data = {
        "label": label,
        "assets": {"core": core, "growth": growth, "defensive": defensive},
        "formal_period": {"start": start, "end": end},
        "warmup_common_sessions": warmup_sessions,
        "required_warmup_sessions": 252,
        "first_common_session": (
            pd.Timestamp(first_common[0]).strftime("%Y-%m-%d") if len(first_common) else None
        ),
    }
    if warmup_sessions < 252:
        return {
            **data,
            "status": "insufficient_warmup",
            "data_gate_passed": False,
            "failure": (
                f"固定起點前只有 {warmup_sessions} 個共同有效交易日，少於 252；"
                "依協議不延後起點或替換 ETF"
            ),
            "diagnostic": _diagnostic_after_first_valid_signal(
                panel,
                core=core,
                growth=growth,
                defensive=defensive,
                end=end,
                cost_bps=primary_cost_bps,
            ),
            "economic_gates": {
                name: False
                for name in (
                    "cagr_beats_market_10bp",
                    "sharpe_beats_market",
                    "drawdown_not_worse_than_market_5pp",
                    "calmar_beats_market",
                    "50bps_cagr_beats_market_10bp",
                    "both_halves_cagr_beat_market_10bp",
                    "rolling_wins_60pct_and_positive_median",
                    "cagr_beats_matched_10bp",
                    "sharpe_beats_matched",
                    "drawdown_not_worse_than_matched_5pp",
                )
            },
        }

    target = confirmed_relative_growth_targets(
        panel.close,
        core=core,
        growth=growth,
        defensive=defensive,
        initial_signal_before=start,
    )
    matched_target = confirmed_relative_growth_matched_targets(
        panel.close,
        core=core,
        growth=growth,
        defensive=defensive,
        initial_signal_before=start,
    )
    signals = target.dropna(how="all")
    initial_signal = pd.Timestamp(signals.index[0])
    position = panel.close.index.get_loc(initial_signal)
    if not isinstance(position, int) or position + 1 >= len(panel.close.index):
        raise ValueError(f"{label} 初始訊號沒有下一個可執行交易日")
    run_start = pd.Timestamp(panel.close.index[position + 1])
    signal_text = initial_signal.strftime("%Y-%m-%d")

    market_target = buy_and_hold_targets(panel.close, core, signal_on=signal_text)
    opportunity_target = buy_and_hold_targets(panel.close, growth, signal_on=signal_text)
    static_target = _one_time_weights(
        panel.close, {core: 0.40, growth: 0.60}, signal_text
    )

    def run(targets_to_run: pd.DataFrame, name: str, cost: float) -> BacktestResult:
        return _run_targets(
            panel,
            targets_to_run,
            name=f"{label} {name}",
            cost_bps=cost,
            run_start=run_start,
            formal_start=start,
            formal_end=end,
        )

    strategy = run(target, "v13", primary_cost_bps)
    market = run(market_target, core, primary_cost_bps)
    opportunity = run(opportunity_target, growth, primary_cost_bps)
    static = run(static_target, "一次性 40/60", primary_cost_bps)
    matched = run(matched_target, "同狀態曝險對照", primary_cost_bps)
    strategy_50 = run(target, "v13 50bps", stress_cost_bps)
    market_50 = run(market_target, f"{core} 50bps", stress_cost_bps)
    comparison = _comparison(strategy, market)
    matched_comparison = _comparison(strategy, matched)
    periods = (
        ("first", "2006-07-31", "2016-07-29"),
        ("second", "2016-08-01", "2026-07-31"),
    )
    fixed_halves = _halves(strategy, market, periods)
    rolling = _rolling_comparison(strategy, market)
    weights = strategy.weights
    matched_weights = matched.weights
    weight_integrity = {
        "strategy_fully_invested_fraction": float(
            np.isclose(weights.sum(axis=1), 1.0, atol=1e-8).mean()
        ),
        "matched_fully_invested_fraction": float(
            np.isclose(matched_weights.sum(axis=1), 1.0, atol=1e-8).mean()
        ),
        "maximum_weight_sum": float(
            max(weights.sum(axis=1).max(), matched_weights.sum(axis=1).max())
        ),
        "minimum_weight": float(
            min(weights.min().min(), matched_weights.min().min())
        ),
    }
    weight_integrity["passed"] = bool(
        weight_integrity["strategy_fully_invested_fraction"] >= 0.95
        and weight_integrity["matched_fully_invested_fraction"] >= 0.95
        and weight_integrity["maximum_weight_sum"] <= 1.0 + 1e-8
        and weight_integrity["minimum_weight"] >= -1e-12
    )
    states = confirmed_relative_growth_states(panel.close, core=core, growth=growth)
    formal_states = states.loc[pd.Timestamp(start) : pd.Timestamp(end)]
    formal_signals = signals.loc[pd.Timestamp(start) : pd.Timestamp(end)]
    result = {
        **data,
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
            "market": market.metrics,
            "growth_opportunity": opportunity.metrics,
            "one_time_40_60": static.metrics,
            "matched": matched.metrics,
        },
        "comparison": comparison,
        "matched_comparison": matched_comparison,
        "cost_50bps": {
            "strategy_metrics": strategy_50.metrics,
            "market_metrics": market_50.metrics,
            "cagr_difference": strategy_50.metrics["cagr"] - market_50.metrics["cagr"],
        },
        "fixed_halves": fixed_halves,
        "rolling_five_year": rolling,
        "weight_integrity": weight_integrity,
        "signals": {
            "completed_month_ends_in_formal_period": int(len(formal_states)),
            "state_month_counts": {
                state: int((formal_states == state).sum())
                for state in ("growth", "core", "defense")
            },
            "state_change_signals_in_formal_period": int(len(formal_signals)),
            "completed_executions_in_formal_period": int(
                strategy.diagnostics["rebalance_count"]
            ),
            "latest_state": str(states.iloc[-1]),
            "latest_completed_month_end": pd.Timestamp(states.index[-1]).strftime(
                "%Y-%m-%d"
            ),
        },
    }
    result["economic_gates"] = _economic_gates(result)
    return result


def evaluate_confirmed_relative_growth_research(
    validation_panel: MarketPanel,
    *,
    validation_receipt: dict[str, Any],
    protocol_sha256: str,
    primary_cost_bps: float = 10.0,
    stress_cost_bps: float = 50.0,
) -> dict[str, Any]:
    """Evaluate v13 only after its rule and three unseen ETF pairs were frozen."""
    snapshot = _snapshot_integrity(
        validation_panel,
        validation_receipt,
        protocol_sha256=protocol_sha256,
    )
    datasets: dict[str, Any] = {}
    for key, spec in V13_DATASETS.items():
        datasets[key] = _dataset_results(
            validation_panel,
            label=str(spec["label"]),
            core=str(spec["core"]),
            growth=str(spec["growth"]),
            defensive=str(spec["defensive"]),
            start=V13_VALIDATION_START,
            end=V13_VALIDATION_END,
            primary_cost_bps=primary_cost_bps,
            stress_cost_bps=stress_cost_bps,
        )

    economic_gates: dict[str, bool] = {}
    for dataset_key, data in datasets.items():
        for gate_name, passed in data["economic_gates"].items():
            economic_gates[f"{dataset_key}_{gate_name}"] = bool(passed)
    data_gates = {
        "snapshot_contract_and_frozen_hashes_pass": True,
        **{
            f"{key}_warmup_execution_and_weights_pass": bool(data["data_gate_passed"])
            for key, data in datasets.items()
        },
    }
    paper_eligible = all(economic_gates.values()) and all(data_gates.values())

    statistical_gates: dict[str, bool] = {}
    dsr_rows: dict[str, Any] = {}
    for key, data in datasets.items():
        if data["status"] != "completed":
            statistical_gates[f"{key}_newey_west_t_at_least_1_96"] = False
            statistical_gates[f"{key}_psr_probability_95pct"] = False
            statistical_gates[f"{key}_global_dsr_probability_95pct"] = False
            dsr_rows[key] = {"status": "not_evaluable_due_to_data_gate"}
            continue
        comparison = data["comparison"]
        dsr = comparison["active_global_deflated_sharpe"]
        statistical_gates[f"{key}_newey_west_t_at_least_1_96"] = bool(
            comparison["active_return_newey_west"]["t_stat"] >= 1.96
        )
        statistical_gates[f"{key}_psr_probability_95pct"] = bool(
            comparison["active_probabilistic_sharpe"]["probability"] >= 0.95
        )
        statistical_gates[f"{key}_global_dsr_probability_95pct"] = bool(
            dsr["probability"] >= 0.95
        )
        dsr_rows[key] = dsr
    historically_confirmed = paper_eligible and all(statistical_gates.values())

    return {
        "schema_version": 1,
        "strategy_name": "v13 兩月確認相對成長三態",
        "status": (
            "historically_confirmed_pending_live"
            if historically_confirmed
            else "paper_entry_passed_statistical_pending"
            if paper_eligible
            else "new_etf_validation_failed"
        ),
        "paper_eligible": paper_eligible,
        "historically_confirmed": historically_confirmed,
        "promotion_ready": False,
        "reference_trade_candidate": False,
        "promotion_effect": "create_isolated_paper_only" if paper_eligible else "none",
        "protocol": {
            "path": "docs/V13_CONFIRMED_RELATIVE_GROWTH_PROTOCOL.md",
            "sha256": protocol_sha256,
            "frozen_before_new_validation_download": True,
            "rule_data_independent": False,
            "new_etf_validation_data_independent": True,
            "global_search_trials": V13_GLOBAL_SEARCH_TRIALS,
        },
        "parameters": {
            "long_lookback_sessions": 252,
            "skip_recent_sessions": 21,
            "growth_and_core_trend_sma_sessions": 200,
            "confirmation_months": 2,
            "growth_state": {"core": 0.40, "growth": 0.60},
            "core_state": {"core": 1.00},
            "defense_state": {"core": 0.70, "defensive": 0.30},
            "trade_trigger": "initial confirmed allocation, then state changes only",
            "execution": "completed month-end close signal; next-session adjusted open",
            "primary_cost_bps": primary_cost_bps,
            "stress_cost_bps": stress_cost_bps,
            "leverage": False,
            "shorting": False,
        },
        "snapshot": snapshot,
        "data_receipt": validation_receipt,
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
        "global_dsr_promotion_sensitivity": {
            "passed": all(
                value
                for key, value in statistical_gates.items()
                if key.endswith("global_dsr_probability_95pct")
            ),
            **dsr_rows,
        },
        "forward_requirements_if_history_passes": {
            "minimum_new_sessions": 252,
            "minimum_completed_state_change_executions": 6,
            "after_cost_return_positive": True,
            "must_beat_same_start": ["core market", "growth asset", "matched control"],
            "max_drawdown_not_worse_than_all_benchmarks": True,
            "active_newey_west_t_at_least": 1.96,
            "active_psr_probability_at_least": 0.95,
            "historical_trades_may_be_backfilled": False,
        },
        "interpretation": {
            "new_data_result": (
                "The newly frozen ETF pairs rejected the candidate: Russell 1000 and "
                "Russell 2000 failed return consistency gates, and EAFE lacked the "
                "predeclared 252-session warmup at the fixed start."
            ),
            "paper_decision": (
                "All new-data economic and integrity gates passed; only isolated Paper may start."
                if paper_eligible
                else "At least one frozen new-data gate failed; do not create v13 Paper."
            ),
            "reference_decision": (
                "Not reference-ready; the new ETF validation directly contradicts robust "
                "cross-universe outperformance."
            ),
        },
    }

