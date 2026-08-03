from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from usfddk.data import panel_fingerprint
from usfddk.managed_futures_capital_efficiency import (
    _halves,
    _month_end_prices,
    _return_frame_from_prices,
    _rolling_comparison,
    _run_monthly_portfolio,
)
from usfddk.metrics import newey_west_mean_test
from usfddk.models import BacktestResult, MarketPanel
from usfddk.paper import paper_metrics
from usfddk.validation import deflated_sharpe_ratio, probabilistic_sharpe_ratio

V25_PROTOCOL_SHA256 = "e4cc652e7f9d7c296282aa71459abfbe58e8b945f7cafa8830a332812dd5c2db"
V25_PRODUCT_MAPPING_SHA256 = "6d82088fdbfb848329805a053071460cd8ca37a1954754ef5390485043ec37a9"
V25_GLOBAL_SEARCH_TRIALS = 6_132
V25_START = "2006-07-31"
V25_END = "2026-07-31"
V25_FORWARD_PROMOTION_PROTOCOL = {
    "schema_version": 2,
    "frozen_at_utc": "2026-08-03T00:00:24Z",
    "frozen_before_first_forward_fill": True,
    "minimum_new_sessions": 252,
    "minimum_completed_monthly_rebalances_excluding_initial_allocation": 6,
    "minimum_annualized_edge": 0.001,
    "require_positive_edge_in_both_fixed_halves": True,
    "minimum_active_newey_west_t": 1.96,
    "require_drawdown_not_worse_than_both_benchmarks": True,
    "benchmarks": ["SPY", "matched_80_VUG_20_SHY"],
}
V25_FORWARD_PROMOTION_PROTOCOL_SHA256 = hashlib.sha256(
    json.dumps(
        V25_FORWARD_PROMOTION_PROTOCOL,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
).hexdigest()
V25_PANEL_HASHES = {
    "vanguard": "6cf44e6347cdd2910605e0c31e9e72bd76544c4cf2cd8923bce7a0847c1755fe",
    "ishares": "88dc9a2762afb078de78f23035dbcdb5ed10c5059c1c51b724c058f79290e273",
    "state_street": "7a32250e94884ed9a169d70b65603dd16a57d99463700065970ec5b9a0460a70",
}
V25_ARCHIVE_HASHES = {
    "vanguard": "8fe11b82ea21bf0f6ebcaef86a46e58b62182a593adba287d675443ac68d2334",
    "ishares": "c6fe0295b2ec0ca54d5efffda1d2b5dd6e926faa06602ab869001c56598e4780",
    "state_street": "1a10bdca951b3b1f5c11cc010351bef06b4abb7f8afe7493753e4d767395b298",
}
V25_PATHS = {
    "vanguard": {"growth": "VUG", "gold": "GLD"},
    "ishares": {"growth": "IWF", "gold": "IAU"},
    "state_street": {"growth": "SPYG", "gold": "GLD"},
}


def v25_paper_fill_counts(state: dict[str, Any]) -> dict[str, int]:
    """Separate the initial allocation from later completed monthly rebalances."""
    try:
        started_at = pd.Timestamp(state["started_at"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("v25 Paper 缺少有效起點") from exc
    filled_orders = [
        item for item in state.get("order_history", []) if str(item.get("status")) == "filled"
    ]
    initial_allocations = 0
    completed_rebalances = 0
    for item in filled_orders:
        try:
            signal_date = pd.Timestamp(item["signal_date"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("v25 Paper 已成交委託缺少有效訊號日") from exc
        if signal_date <= started_at:
            initial_allocations += 1
        else:
            completed_rebalances += 1
    return {
        "filled_orders": len(filled_orders),
        "initial_allocations": initial_allocations,
        "completed_rebalances": completed_rebalances,
    }


def _v25_paper_order_path(state: dict[str, Any], label: str) -> tuple[Any, ...]:
    history: list[tuple[str, str, str, str]] = []
    previous_signal: pd.Timestamp | None = None
    previous_fill: pd.Timestamp | None = None
    for item in state.get("order_history", []):
        try:
            signal = pd.Timestamp(item["signal_date"])
            execute_after = pd.Timestamp(item["execute_after"])
            filled_at = pd.Timestamp(item["filled_at"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"v25 {label} 已成交委託日期無效") from exc
        if str(item.get("status")) != "filled":
            raise ValueError(f"v25 {label} 歷史委託含非成交狀態")
        if signal > execute_after or filled_at <= execute_after:
            raise ValueError(f"v25 {label} 已成交委託時序無效")
        if previous_signal is not None and signal <= previous_signal:
            raise ValueError(f"v25 {label} 歷史訊號日未嚴格遞增")
        if previous_fill is not None and filled_at <= previous_fill:
            raise ValueError(f"v25 {label} 歷史成交日未嚴格遞增")
        history.append(
            (
                signal.strftime("%Y-%m-%d"),
                execute_after.strftime("%Y-%m-%d"),
                filled_at.strftime("%Y-%m-%d"),
                "filled",
            )
        )
        previous_signal = signal
        previous_fill = filled_at
    pending = state.get("pending_order")
    pending_signature: tuple[str, str, str] | None = None
    if pending is not None:
        try:
            signal = pd.Timestamp(pending["signal_date"])
            execute_after = pd.Timestamp(pending["execute_after"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"v25 {label} 待成交委託日期無效") from exc
        if str(pending.get("status")) != "pending" or signal > execute_after:
            raise ValueError(f"v25 {label} 待成交委託時序無效")
        if previous_signal is not None and signal <= previous_signal:
            raise ValueError(f"v25 {label} 待成交訊號未晚於歷史訊號")
        pending_signature = (
            signal.strftime("%Y-%m-%d"),
            execute_after.strftime("%Y-%m-%d"),
            "pending",
        )
    return tuple(history), pending_signature


def _validated_paper_equity(state: dict[str, Any], label: str) -> pd.Series:
    rows = state.get("equity_curve", [])
    if not isinstance(rows, list) or not rows:
        raise ValueError(f"v25 {label} 缺少權益序列")
    try:
        dates = pd.to_datetime([row["date"] for row in rows])
        values = pd.Series(
            [float(row["equity"]) for row in rows],
            index=pd.DatetimeIndex(dates),
            dtype=float,
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError(f"v25 {label} 權益序列格式無效") from exc
    if (
        values.index.has_duplicates
        or not values.index.is_monotonic_increasing
        or not bool(np.isfinite(values.to_numpy()).all())
        or bool((values <= 0).any())
    ):
        raise ValueError(f"v25 {label} 權益序列日期或數值無效")
    if values.index[0] != pd.Timestamp(state.get("started_at")):
        raise ValueError(f"v25 {label} 權益起點與帳戶起點不同")
    if values.index[-1] != pd.Timestamp(state.get("as_of")):
        raise ValueError(f"v25 {label} 權益終點與帳戶進度不同")
    return values


def _annualized_equity_return(equity: pd.Series, start: int, end: int) -> float:
    sessions = end - start
    if sessions <= 0:
        return 0.0
    gross = float(equity.iloc[end] / equity.iloc[start])
    return float(gross ** (252.0 / sessions) - 1.0)


def _forward_benchmark_diagnostics(
    candidate: pd.Series,
    benchmark: pd.Series,
) -> dict[str, Any]:
    aligned = pd.concat(
        [candidate.rename("candidate"), benchmark.rename("benchmark")],
        axis=1,
        join="inner",
    ).dropna()
    sessions = max(len(candidate) - 1, 0)
    complete_alignment = bool(len(aligned) == len(candidate) == len(benchmark))
    if not complete_alignment or sessions == 0:
        return {
            "annualized_return_difference": 0.0,
            "persistence_available": False,
            "first_half_annualized_difference": None,
            "second_half_annualized_difference": None,
            "active_newey_west": newey_west_mean_test(
                pd.Series(dtype=float), max_lag=5, periods_per_year=252
            ),
        }
    candidate_aligned = aligned["candidate"]
    benchmark_aligned = aligned["benchmark"]
    annualized_difference = _annualized_equity_return(
        candidate_aligned, 0, sessions
    ) - _annualized_equity_return(benchmark_aligned, 0, sessions)
    midpoint = sessions // 2
    persistence_available = sessions >= 252 and midpoint > 0 and midpoint < sessions
    first_half = None
    second_half = None
    if persistence_available:
        first_half = _annualized_equity_return(
            candidate_aligned, 0, midpoint
        ) - _annualized_equity_return(benchmark_aligned, 0, midpoint)
        second_half = _annualized_equity_return(
            candidate_aligned, midpoint, sessions
        ) - _annualized_equity_return(benchmark_aligned, midpoint, sessions)
    active = (
        candidate_aligned.pct_change(fill_method=None)
        - benchmark_aligned.pct_change(fill_method=None)
    ).iloc[1:]
    return {
        "annualized_return_difference": float(annualized_difference),
        "persistence_available": persistence_available,
        "first_half_annualized_difference": (float(first_half) if first_half is not None else None),
        "second_half_annualized_difference": (
            float(second_half) if second_half is not None else None
        ),
        "active_newey_west": newey_west_mean_test(active, max_lag=5, periods_per_year=252),
    }


def v25_forward_paper_evidence(
    candidate_state: dict[str, Any],
    spy_state: dict[str, Any],
    matched_state: dict[str, Any],
) -> dict[str, Any]:
    """Evaluate the preregistered forward gate without treating queued orders as fills."""
    states = {
        "candidate": candidate_state,
        "SPY": spy_state,
        "matched_80_VUG_20_SHY": matched_state,
    }
    metrics = {key: paper_metrics(state) for key, state in states.items()}
    starts = {str(state.get("started_at")) for state in states.values()}
    as_of_dates = {str(state.get("as_of")) for state in states.values()}
    snapshots = {str(state.get("snapshot_sha256")) for state in states.values()}
    costs = {float(state.get("cost_bps", float("nan"))) for state in states.values()}
    initial_cash = {float(state.get("initial_cash", float("nan"))) for state in states.values()}
    session_paths = {
        tuple(str(row.get("date")) for row in state.get("equity_curve", []))
        for state in states.values()
    }
    execution_clocks = {str(state.get("execution_clock", "")) for state in states.values()}
    order_paths = {_v25_paper_order_path(state, label) for label, state in states.items()}
    account_fill_counts = {label: v25_paper_fill_counts(state) for label, state in states.items()}
    fill_count_signatures = {
        tuple(row[key] for key in sorted(row)) for row in account_fill_counts.values()
    }
    live_modes = all(state.get("mode") == "live" for state in states.values())
    candidate_sessions = max(len(candidate_state.get("equity_curve", [])) - 1, 0)
    fill_counts = account_fill_counts["candidate"]
    filled_rebalances = fill_counts["completed_rebalances"]
    equity = {label: _validated_paper_equity(state, label) for label, state in states.items()}
    forward_diagnostics = {
        "SPY": _forward_benchmark_diagnostics(equity["candidate"], equity["SPY"]),
        "matched_80_VUG_20_SHY": _forward_benchmark_diagnostics(
            equity["candidate"], equity["matched_80_VUG_20_SHY"]
        ),
    }
    minimum_sessions = int(V25_FORWARD_PROMOTION_PROTOCOL["minimum_new_sessions"])
    minimum_rebalances = int(
        V25_FORWARD_PROMOTION_PROTOCOL[
            "minimum_completed_monthly_rebalances_excluding_initial_allocation"
        ]
    )
    minimum_edge = float(V25_FORWARD_PROMOTION_PROTOCOL["minimum_annualized_edge"])
    minimum_t = float(V25_FORWARD_PROMOTION_PROTOCOL["minimum_active_newey_west_t"])
    sample_ready = bool(
        candidate_sessions >= minimum_sessions and filled_rebalances >= minimum_rebalances
    )
    integrity_violations = sum(
        len(state.get("integrity_violations", [])) for state in states.values()
    )
    candidate_metrics = metrics["candidate"]
    spy_metrics = metrics["SPY"]
    matched_metrics = metrics["matched_80_VUG_20_SHY"]
    gates = {
        "all_accounts_live_and_same_start": bool(live_modes and len(starts) == 1),
        "all_accounts_same_as_of": bool(len(as_of_dates) == 1),
        "all_accounts_same_snapshot": bool(len(snapshots) == 1 and "" not in snapshots),
        "all_accounts_same_cost_and_cash": bool(len(costs) == 1 and len(initial_cash) == 1),
        "all_accounts_same_session_path": bool(len(session_paths) == 1),
        "all_accounts_same_execution_clock": bool(
            len(execution_clocks) == 1 and "" not in execution_clocks
        ),
        "all_accounts_same_order_path": bool(len(order_paths) == 1),
        "all_accounts_same_fill_counts": bool(len(fill_count_signatures) == 1),
        "at_least_252_new_sessions": bool(candidate_sessions >= minimum_sessions),
        "at_least_6_filled_rebalances": bool(filled_rebalances >= minimum_rebalances),
        "zero_integrity_violations": bool(integrity_violations == 0),
        "all_accounts_exactly_one_initial_allocation": bool(
            sample_ready
            and all(row["initial_allocations"] == 1 for row in account_fill_counts.values())
        ),
        "candidate_return_above_SPY": bool(
            sample_ready and candidate_metrics["return"] > spy_metrics["return"]
        ),
        "candidate_return_above_matched": bool(
            sample_ready and candidate_metrics["return"] > matched_metrics["return"]
        ),
        "candidate_drawdown_not_worse_than_SPY": bool(
            sample_ready and candidate_metrics["max_drawdown"] >= spy_metrics["max_drawdown"]
        ),
        "candidate_drawdown_not_worse_than_matched": bool(
            sample_ready and candidate_metrics["max_drawdown"] >= matched_metrics["max_drawdown"]
        ),
        "candidate_annualized_edge_at_least_10bp_vs_SPY": bool(
            sample_ready
            and forward_diagnostics["SPY"]["annualized_return_difference"] >= minimum_edge
        ),
        "candidate_annualized_edge_at_least_10bp_vs_matched": bool(
            sample_ready
            and forward_diagnostics["matched_80_VUG_20_SHY"]["annualized_return_difference"]
            >= minimum_edge
        ),
        "candidate_outperforms_SPY_in_both_halves": bool(
            sample_ready
            and forward_diagnostics["SPY"]["persistence_available"]
            and forward_diagnostics["SPY"]["first_half_annualized_difference"] >= minimum_edge
            and forward_diagnostics["SPY"]["second_half_annualized_difference"] >= minimum_edge
        ),
        "candidate_outperforms_matched_in_both_halves": bool(
            sample_ready
            and forward_diagnostics["matched_80_VUG_20_SHY"]["persistence_available"]
            and forward_diagnostics["matched_80_VUG_20_SHY"]["first_half_annualized_difference"]
            >= minimum_edge
            and forward_diagnostics["matched_80_VUG_20_SHY"]["second_half_annualized_difference"]
            >= minimum_edge
        ),
        "candidate_active_newey_west_t_at_least_1_96_vs_SPY": bool(
            sample_ready and forward_diagnostics["SPY"]["active_newey_west"]["t_stat"] >= minimum_t
        ),
        "candidate_active_newey_west_t_at_least_1_96_vs_matched": bool(
            sample_ready
            and forward_diagnostics["matched_80_VUG_20_SHY"]["active_newey_west"]["t_stat"]
            >= minimum_t
        ),
    }
    return {
        "promotion_protocol": V25_FORWARD_PROMOTION_PROTOCOL,
        "promotion_protocol_sha256": V25_FORWARD_PROMOTION_PROTOCOL_SHA256,
        "as_of": str(candidate_state.get("as_of")),
        "started_at": str(candidate_state.get("started_at")),
        "forward_sessions": candidate_sessions,
        "minimum_sessions": minimum_sessions,
        "remaining_sessions": max(minimum_sessions - candidate_sessions, 0),
        "filled_orders_including_initial_allocation": int(fill_counts["filled_orders"]),
        "initial_allocations": int(fill_counts["initial_allocations"]),
        "account_fill_counts": account_fill_counts,
        "filled_rebalances": int(filled_rebalances),
        "minimum_filled_rebalances": minimum_rebalances,
        "remaining_filled_rebalances": max(minimum_rebalances - int(filled_rebalances), 0),
        "integrity_violations": int(integrity_violations),
        "candidate": {
            "equity": float(candidate_metrics["equity"]),
            "return": float(candidate_metrics["return"]),
            "max_drawdown": float(candidate_metrics["max_drawdown"]),
        },
        "SPY": {
            "equity": float(spy_metrics["equity"]),
            "return": float(spy_metrics["return"]),
            "max_drawdown": float(spy_metrics["max_drawdown"]),
        },
        "matched_80_VUG_20_SHY": {
            "equity": float(matched_metrics["equity"]),
            "return": float(matched_metrics["return"]),
            "max_drawdown": float(matched_metrics["max_drawdown"]),
        },
        "return_difference_vs_SPY": float(candidate_metrics["return"] - spy_metrics["return"]),
        "return_difference_vs_matched": float(
            candidate_metrics["return"] - matched_metrics["return"]
        ),
        "forward_diagnostics": forward_diagnostics,
        "gates": gates,
        "live_confirmed": bool(all(gates.values())),
    }


def _sha256(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _comparison_v25(strategy: BacktestResult, benchmark: BacktestResult) -> dict[str, Any]:
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
        "active_return_newey_west": newey_west_mean_test(active, max_lag=6, periods_per_year=12),
        "active_probabilistic_sharpe": probabilistic_sharpe_ratio(
            active, benchmark_sharpe=0.0, periods_per_year=12
        ),
        "active_global_deflated_sharpe": deflated_sharpe_ratio(
            active, trials=V25_GLOBAL_SEARCH_TRIALS, periods_per_year=12
        ),
    }


def _underwater_diagnostics(equity: pd.Series) -> dict[str, Any]:
    """Describe drawdown depth and time below the prior high in monthly observations."""
    values = equity.astype(float)
    if values.empty or values.isna().any() or bool((values <= 0).any()):
        raise ValueError("v25 underwater 診斷需要完整正值權益序列")
    running_high = values.cummax()
    drawdown = values / running_high - 1.0
    underwater = drawdown < -1e-12
    episodes: list[dict[str, Any]] = []
    start_position: int | None = None
    peak_position: int | None = None
    for position, is_underwater in enumerate(underwater.tolist()):
        if is_underwater and start_position is None:
            start_position = position
            peak_position = max(position - 1, 0)
        recovery = start_position is not None and not is_underwater
        final_open_episode = start_position is not None and position == len(values) - 1
        if not recovery and not final_open_episode:
            continue
        end_position = position - 1 if recovery else position
        segment = drawdown.iloc[start_position : end_position + 1]
        trough_date = segment.idxmin()
        episodes.append(
            {
                "peak": values.index[peak_position].strftime("%Y-%m-%d"),
                "underwater_start": values.index[start_position].strftime("%Y-%m-%d"),
                "trough": trough_date.strftime("%Y-%m-%d"),
                "recovery": (values.index[position].strftime("%Y-%m-%d") if recovery else None),
                "underwater_months": int(end_position - start_position + 1),
                "drawdown": float(segment.min()),
                "recovered": bool(recovery),
            }
        )
        start_position = None
        peak_position = None
    if not episodes:
        empty_episode = {
            "peak": values.index[0].strftime("%Y-%m-%d"),
            "underwater_start": None,
            "trough": values.index[0].strftime("%Y-%m-%d"),
            "recovery": values.index[0].strftime("%Y-%m-%d"),
            "underwater_months": 0,
            "drawdown": 0.0,
            "recovered": True,
        }
        return {
            "max_underwater_months": 0,
            "current_drawdown": 0.0,
            "deepest_episode": empty_episode,
            "longest_episode": empty_episode,
            "episode_count": 0,
        }
    return {
        "max_underwater_months": int(max(item["underwater_months"] for item in episodes)),
        "current_drawdown": float(drawdown.iloc[-1]),
        "deepest_episode": min(episodes, key=lambda item: item["drawdown"]),
        "longest_episode": max(
            episodes,
            key=lambda item: (item["underwater_months"], -item["drawdown"]),
        ),
        "episode_count": len(episodes),
    }


def _relative_underwater_diagnostics(
    strategy: BacktestResult, benchmark: BacktestResult
) -> dict[str, Any]:
    aligned = pd.concat(
        [strategy.equity.rename("strategy"), benchmark.equity.rename("benchmark")],
        axis=1,
    ).dropna()
    if not aligned.index.equals(strategy.equity.index) or not aligned.index.equals(
        benchmark.equity.index
    ):
        raise ValueError("v25 相對財富診斷月份未對齊")
    relative_wealth = aligned["strategy"] / aligned["benchmark"]
    relative_wealth = relative_wealth / float(relative_wealth.iloc[0])
    return _underwater_diagnostics(relative_wealth)


def _rolling_window_risk(strategy: BacktestResult, benchmark: BacktestResult) -> dict[str, Any]:
    rolling = _rolling_comparison(strategy, benchmark)
    series = rolling["series"]
    if not series:
        raise ValueError("v25 五年滾動診斷沒有可用視窗")
    worst = min(series, key=lambda item: item["cagr_difference"])
    latest = series[-1]
    return {
        "window_months": int(rolling["window_months"]),
        "windows": int(rolling["summary"]["windows"]),
        "winning_window_fraction": float(rolling["summary"]["cagr_win_fraction"]),
        "worst_window": {
            "start": worst["start"],
            "end": worst["end"],
            "cagr_difference": float(worst["cagr_difference"]),
        },
        "latest_window": {
            "start": latest["start"],
            "end": latest["end"],
            "cagr_difference": float(latest["cagr_difference"]),
        },
    }


def _paired_moving_block_bootstrap(
    strategy: BacktestResult,
    benchmark: BacktestResult,
    *,
    block_months: int,
    trials: int,
    seed: int,
) -> dict[str, Any]:
    """Resample paired monthly returns in circular blocks; diagnostic only."""
    if block_months <= 0 or trials <= 0:
        raise ValueError("v25 區塊重抽樣參數必須大於零")
    aligned = pd.concat(
        [strategy.returns.rename("strategy"), benchmark.returns.rename("benchmark")],
        axis=1,
    ).dropna()
    if not aligned.index.equals(strategy.returns.index) or not aligned.index.equals(
        benchmark.returns.index
    ):
        raise ValueError("v25 區塊重抽樣月份未對齊")
    monthly = aligned.iloc[1:].to_numpy(dtype=float)
    months = len(monthly)
    if months < block_months:
        raise ValueError("v25 區塊重抽樣區塊長於樣本")
    blocks = int(np.ceil(months / block_months))
    rng = np.random.default_rng(seed)
    starts = rng.integers(0, months, size=(trials, blocks))
    offsets = np.arange(block_months)
    indices = (starts[:, :, None] + offsets[None, None, :]) % months
    indices = indices.reshape(trials, -1)[:, :months]
    sampled = monthly[indices]
    wealth = np.cumprod(1.0 + sampled, axis=1)
    start = np.ones((trials, 1, 2), dtype=float)
    wealth_with_start = np.concatenate([start, wealth], axis=1)
    running_high = np.maximum.accumulate(wealth_with_start, axis=1)
    drawdown = np.min(wealth_with_start / running_high - 1.0, axis=1)
    cagr = wealth[:, -1, :] ** (12.0 / months) - 1.0
    cagr_difference = cagr[:, 0] - cagr[:, 1]
    drawdown_not_worse = drawdown[:, 0] >= drawdown[:, 1]
    cagr_above = cagr_difference > 0.0
    percentiles = np.quantile(cagr_difference, [0.05, 0.50, 0.95])
    return {
        "block_months": int(block_months),
        "trials": int(trials),
        "seed": int(seed),
        "probability_cagr_above": float(np.mean(cagr_above)),
        "probability_cagr_edge_at_least_10bp": float(np.mean(cagr_difference >= 0.001)),
        "probability_drawdown_not_worse": float(np.mean(drawdown_not_worse)),
        "probability_cagr_above_and_drawdown_not_worse": float(
            np.mean(cagr_above & drawdown_not_worse)
        ),
        "cagr_difference_percentiles": {
            "p05": float(percentiles[0]),
            "p50": float(percentiles[1]),
            "p95": float(percentiles[2]),
        },
    }


def _post_entry_diagnostics(
    candidate: BacktestResult,
    *,
    spy: BacktestResult,
    growth: BacktestResult,
    matched: BacktestResult,
    include_bootstrap: bool = False,
) -> dict[str, Any]:
    """Additional transparency only; these fields cannot change frozen gates."""
    benchmarks = {"SPY": spy, "growth": growth, "matched": matched}
    diagnostics = {
        "used_for_frozen_entry_gate": False,
        "portfolio_underwater": _underwater_diagnostics(candidate.equity),
        "relative_wealth_underwater": {
            label: _relative_underwater_diagnostics(candidate, benchmark)
            for label, benchmark in benchmarks.items()
        },
        "rolling_five_year_entry_timing_risk": {
            label: _rolling_window_risk(candidate, benchmark)
            for label, benchmark in benchmarks.items()
        },
    }
    if include_bootstrap:
        diagnostics["paired_moving_block_bootstrap"] = {
            "used_for_frozen_entry_gate": False,
            "method": "paired circular moving-block bootstrap of monthly returns",
            "trials_per_block_length": 10_000,
            "block_months": [6, 12, 24],
            "selection_bias_or_future_proof": False,
            "benchmarks": {
                label: {
                    str(block): _paired_moving_block_bootstrap(
                        candidate,
                        benchmark,
                        block_months=block,
                        trials=10_000,
                        seed=25_000 + offset * 100 + block,
                    )
                    for block in (6, 12, 24)
                }
                for offset, (label, benchmark) in enumerate(benchmarks.items())
            },
        }
    return diagnostics


def _evaluate_path(
    panel: MarketPanel,
    *,
    growth: str,
    gold: str,
    primary_cost_bps: float,
    stress_cost_bps: float,
) -> tuple[dict[str, Any], dict[str, BacktestResult]]:
    tickers = ["SPY", "SHY", growth, gold]
    prices = _month_end_prices(panel, tickers, start=V25_START, end=V25_END)
    returns = _return_frame_from_prices(prices)
    candidate = _run_monthly_portfolio(
        returns,
        {growth: 0.8, gold: 0.2},
        name=f"80% {growth} / 20% {gold}",
        start_equity_date=V25_START,
        cost_bps=primary_cost_bps,
        rebalance_monthly=True,
    )
    candidate_stress = _run_monthly_portfolio(
        returns,
        {growth: 0.8, gold: 0.2},
        name=f"80% {growth} / 20% {gold} stress",
        start_equity_date=V25_START,
        cost_bps=stress_cost_bps,
        rebalance_monthly=True,
    )
    spy = _run_monthly_portfolio(
        returns,
        {"SPY": 1.0},
        name="SPY",
        start_equity_date=V25_START,
        cost_bps=primary_cost_bps,
        rebalance_monthly=False,
    )
    spy_stress = _run_monthly_portfolio(
        returns,
        {"SPY": 1.0},
        name="SPY stress",
        start_equity_date=V25_START,
        cost_bps=stress_cost_bps,
        rebalance_monthly=False,
    )
    growth_only = _run_monthly_portfolio(
        returns,
        {growth: 1.0},
        name=growth,
        start_equity_date=V25_START,
        cost_bps=primary_cost_bps,
        rebalance_monthly=False,
    )
    matched = _run_monthly_portfolio(
        returns,
        {growth: 0.8, "SHY": 0.2},
        name=f"80% {growth} / 20% SHY",
        start_equity_date=V25_START,
        cost_bps=primary_cost_bps,
        rebalance_monthly=True,
    )
    drift = _run_monthly_portfolio(
        returns,
        {growth: 0.8, gold: 0.2},
        name=f"80% {growth} / 20% {gold} start then drift",
        start_equity_date=V25_START,
        cost_bps=primary_cost_bps,
        rebalance_monthly=False,
    )
    results = {
        "candidate": candidate,
        "candidate_stress": candidate_stress,
        "spy": spy,
        "spy_stress": spy_stress,
        "growth": growth_only,
        "matched": matched,
        "drift": drift,
    }
    data = {
        "period": {
            "start_equity_date": V25_START,
            "first_return_month_end": returns.index[0].strftime("%Y-%m-%d"),
            "end": returns.index[-1].strftime("%Y-%m-%d"),
            "months": int(len(returns)),
        },
        "implementation": {
            "growth": growth,
            "gold": gold,
            "weights": {growth: 0.8, gold: 0.2},
        },
        "strategy_metrics": candidate.metrics,
        "benchmark_metrics": {
            "SPY": spy.metrics,
            "growth": growth_only.metrics,
            "matched_80_growth_20_SHY": matched.metrics,
            "start_then_drift_80_20": drift.metrics,
        },
        "comparisons": {
            "SPY": _comparison_v25(candidate, spy),
            "growth": _comparison_v25(candidate, growth_only),
            "matched_80_growth_20_SHY": _comparison_v25(candidate, matched),
            "start_then_drift_80_20": _comparison_v25(candidate, drift),
        },
        "cost_50bps": {
            "strategy_metrics": candidate_stress.metrics,
            "spy_metrics": spy_stress.metrics,
            "cagr_difference": (candidate_stress.metrics["cagr"] - spy_stress.metrics["cagr"]),
        },
        "fixed_halves_vs_SPY": _halves(candidate, spy),
        "fixed_halves_vs_growth": _halves(candidate, growth_only),
        "fixed_halves_vs_matched": _halves(candidate, matched),
        "rolling_five_year_vs_SPY": _rolling_comparison(candidate, spy),
        "rolling_five_year_vs_growth": _rolling_comparison(candidate, growth_only),
        "rolling_five_year_vs_matched": _rolling_comparison(candidate, matched),
        "post_entry_diagnostics_not_used_for_frozen_gate": _post_entry_diagnostics(
            candidate,
            spy=spy,
            growth=growth_only,
            matched=matched,
        ),
        "turnover_definition": "sum absolute target-minus-drift weights; initial 100pct",
    }
    return data, results


def _path_gates(data: dict[str, Any]) -> dict[str, bool]:
    strategy = data["strategy_metrics"]
    spy = data["benchmark_metrics"]["SPY"]
    growth = data["benchmark_metrics"]["growth"]
    matched = data["benchmark_metrics"]["matched_80_growth_20_SHY"]
    halves = data["fixed_halves_vs_SPY"]
    rolling = data["rolling_five_year_vs_SPY"]["summary"]
    return {
        "exact_240_months_and_data_contract_pass": bool(data["period"]["months"] == 240),
        "cagr_beats_SPY_25bp": bool(strategy["cagr"] >= spy["cagr"] + 0.0025),
        "sharpe_beats_SPY": bool(strategy["sharpe"] > spy["sharpe"]),
        "drawdown_not_worse_than_SPY": bool(strategy["max_drawdown"] >= spy["max_drawdown"]),
        "calmar_beats_SPY": bool(strategy["calmar"] > spy["calmar"]),
        "50bps_cagr_beats_SPY_10bp": bool(data["cost_50bps"]["cagr_difference"] >= 0.001),
        "both_fixed_decades_cagr_beat_SPY_10bp": bool(
            all(item["cagr_difference"] >= 0.001 for item in halves.values())
        ),
        "rolling_5y_wins_60pct_and_median_10bp": bool(
            rolling["cagr_win_fraction"] >= 0.60 and rolling["median_cagr_difference"] >= 0.001
        ),
        "cagr_beats_matched_10bp": bool(strategy["cagr"] >= matched["cagr"] + 0.001),
        "sharpe_beats_matched": bool(strategy["sharpe"] > matched["sharpe"]),
        "drawdown_not_worse_than_matched": bool(
            strategy["max_drawdown"] >= matched["max_drawdown"]
        ),
        "growth_tradeoff_pass": bool(
            strategy["sharpe"] > growth["sharpe"]
            and strategy["max_drawdown"] >= growth["max_drawdown"] + 0.05
            and strategy["cagr"] >= growth["cagr"] - 0.01
        ),
    }


def _pooled_result(
    results: dict[str, dict[str, BacktestResult]],
    key: str,
    *,
    name: str,
) -> BacktestResult:
    monthly = pd.concat(
        {label: path_results[key].returns.iloc[1:] for label, path_results in results.items()},
        axis=1,
    )
    if monthly.isna().any(axis=None):
        raise ValueError(f"v25 {name} 三路徑月份未對齊")
    return _run_monthly_portfolio(
        monthly,
        {column: 1.0 / len(monthly.columns) for column in monthly.columns},
        name=name,
        start_equity_date=V25_START,
        cost_bps=0.0,
        rebalance_monthly=True,
    )


def _receipt_integrity(
    panels: dict[str, MarketPanel],
    manifests: dict[str, dict[str, Any]],
    *,
    protocol_receipt: dict[str, Any],
    data_receipt: dict[str, Any],
    protocol_sha256: str,
    product_mapping_sha256: str,
) -> dict[str, bool]:
    if protocol_sha256 != V25_PROTOCOL_SHA256:
        raise ValueError("v25 協議雜湊不符")
    if product_mapping_sha256 != V25_PRODUCT_MAPPING_SHA256:
        raise ValueError("v25 產品映射雜湊不符")
    if protocol_receipt.get("protocol_sha256") != V25_PROTOCOL_SHA256:
        raise ValueError("v25 協議收據不符")
    if (
        protocol_receipt.get("status")
        != "frozen_before_first_v25_joint_daily_download_or_portfolio_calculation"
    ):
        raise ValueError("v25 收據未證明先凍結")
    if data_receipt.get("pre_registration_order_proved") is not True:
        raise ValueError("v25 資料收據未證明先凍結")
    frozen = max(
        int(protocol_receipt["protocol_mtime_epoch"]),
        int(protocol_receipt["product_mapping_mtime_epoch"]),
    )
    gates = {
        "frozen_protocol_and_mapping_hashes_pass": True,
        "protocol_and_mapping_precede_all_first_downloads": True,
    }
    for label in V25_PATHS:
        panel = panels[label]
        manifest = manifests[label]
        receipt = data_receipt["snapshots"][label]
        if panel_fingerprint(panel) != V25_PANEL_HASHES[label]:
            raise ValueError(f"v25 {label} 面板內容雜湊不符")
        if manifest.get("panel_sha256") != V25_PANEL_HASHES[label]:
            raise ValueError(f"v25 {label} manifest 面板雜湊不符")
        if manifest.get("archive_sha256") != V25_ARCHIVE_HASHES[label]:
            raise ValueError(f"v25 {label} ZIP 雜湊不符")
        if receipt.get("archive_sha256") != V25_ARCHIVE_HASHES[label]:
            raise ValueError(f"v25 {label} 資料收據 ZIP 雜湊不符")
        if int(receipt["snapshot_mtime_epoch"]) <= frozen:
            raise ValueError(f"v25 {label} 快照沒有晚於凍結")
        if (manifest.get("contract") or {}).get("ok") is not True:
            raise ValueError(f"v25 {label} 資料契約未通過")
        gates[f"{label}_snapshot_hash_and_contract_pass"] = True
    split = data_receipt.get("vug_split_adjustment_audit", {})
    if split.get("passed") is not True:
        raise ValueError("v25 VUG 拆股調整稽核未通過")
    gates["vug_6_for_1_split_adjustment_pass"] = True
    return gates


def evaluate_growth_gold_diversification(
    panels: dict[str, MarketPanel],
    *,
    manifests: dict[str, dict[str, Any]],
    protocol_receipt: dict[str, Any],
    data_receipt: dict[str, Any],
    protocol_sha256: str,
    product_mapping_sha256: str,
    primary_cost_bps: float = 10.0,
    stress_cost_bps: float = 50.0,
) -> dict[str, Any]:
    if set(panels) != set(V25_PATHS) or set(manifests) != set(V25_PATHS):
        raise ValueError("v25 必須同時提供三條凍結產品路徑")
    data_gates = _receipt_integrity(
        panels,
        manifests,
        protocol_receipt=protocol_receipt,
        data_receipt=data_receipt,
        protocol_sha256=protocol_sha256,
        product_mapping_sha256=product_mapping_sha256,
    )
    path_data: dict[str, dict[str, Any]] = {}
    path_results: dict[str, dict[str, BacktestResult]] = {}
    for label, mapping in V25_PATHS.items():
        data, results = _evaluate_path(
            panels[label],
            growth=mapping["growth"],
            gold=mapping["gold"],
            primary_cost_bps=primary_cost_bps,
            stress_cost_bps=stress_cost_bps,
        )
        gates = _path_gates(data)
        path_data[label] = {
            **data,
            "entry_gates": gates,
            "passed_gate_count": int(sum(gates.values())),
            "required_gate_count": len(gates),
            "required_pass_count": 10,
        }
        path_results[label] = results

    candidate = _pooled_result(path_results, "candidate", name="v25 pooled candidate")
    candidate_stress = _pooled_result(
        path_results, "candidate_stress", name="v25 pooled candidate 50bps"
    )
    spy = _pooled_result(path_results, "spy", name="v25 pooled SPY")
    spy_stress = _pooled_result(path_results, "spy_stress", name="v25 pooled SPY 50bps")
    growth = _pooled_result(path_results, "growth", name="v25 pooled growth")
    matched = _pooled_result(path_results, "matched", name="v25 pooled matched")
    pooled_halves = _halves(candidate, spy)
    pooled_rolling = _rolling_comparison(candidate, spy)["summary"]
    pooled_gates = {
        "cagr_beats_SPY_25bp": bool(candidate.metrics["cagr"] >= spy.metrics["cagr"] + 0.0025),
        "sharpe_beats_SPY": bool(candidate.metrics["sharpe"] > spy.metrics["sharpe"]),
        "drawdown_not_worse_than_SPY": bool(
            candidate.metrics["max_drawdown"] >= spy.metrics["max_drawdown"]
        ),
        "calmar_beats_SPY": bool(candidate.metrics["calmar"] > spy.metrics["calmar"]),
        "50bps_cagr_beats_SPY_10bp": bool(
            candidate_stress.metrics["cagr"] >= spy_stress.metrics["cagr"] + 0.001
        ),
        "both_fixed_decades_cagr_beat_SPY_10bp": bool(
            all(item["cagr_difference"] >= 0.001 for item in pooled_halves.values())
        ),
        "rolling_5y_wins_60pct_and_median_10bp": bool(
            pooled_rolling["cagr_win_fraction"] >= 0.60
            and pooled_rolling["median_cagr_difference"] >= 0.001
        ),
        "cagr_beats_matched_10bp": bool(
            candidate.metrics["cagr"] >= matched.metrics["cagr"] + 0.001
        ),
        "sharpe_beats_matched": bool(candidate.metrics["sharpe"] > matched.metrics["sharpe"]),
        "drawdown_not_worse_than_matched": bool(
            candidate.metrics["max_drawdown"] >= matched.metrics["max_drawdown"]
        ),
    }
    data_gates.update(
        {
            "all_paths_exact_240_months": bool(
                all(data["period"]["months"] == 240 for data in path_data.values())
            ),
            "all_paths_same_formal_month_range": bool(
                len(
                    {
                        (
                            data["period"]["first_return_month_end"],
                            data["period"]["end"],
                        )
                        for data in path_data.values()
                    }
                )
                == 1
            ),
        }
    )
    pooled_passed = int(sum(pooled_gates.values()))
    data_passed = int(sum(data_gates.values()))
    each_path_passes = all(
        data["passed_gate_count"] >= data["required_pass_count"] for data in path_data.values()
    )
    paper_eligible = bool(
        each_path_passes and pooled_passed == len(pooled_gates) and data_passed == len(data_gates)
    )
    pooled_comparison = _comparison_v25(candidate, spy)
    growth_comparison = _comparison_v25(candidate, growth)
    matched_comparison = _comparison_v25(candidate, matched)
    return {
        "schema_version": 1,
        "status": (
            "growth_gold_diversification_passed_for_isolated_paper"
            if paper_eligible
            else "growth_gold_diversification_validation_failed"
        ),
        "paper_eligible": paper_eligible,
        "trade_ready": False,
        "reference_trade_candidate": paper_eligible,
        "global_search_trials": V25_GLOBAL_SEARCH_TRIALS,
        "protocol": {
            "sha256": V25_PROTOCOL_SHA256,
            "product_mapping_sha256": V25_PRODUCT_MAPPING_SHA256,
        },
        "candidate": {
            "paper_implementation": {"VUG": 0.8, "GLD": 0.2},
            "rebalance": "monthly",
            "timing_or_exit_overlay": False,
            "signal_display_allowed": paper_eligible,
        },
        "paths": path_data,
        "pooled": {
            "period": {
                "start_equity_date": V25_START,
                "first_return_month_end": candidate.equity.index[1].strftime("%Y-%m-%d"),
                "end": candidate.equity.index[-1].strftime("%Y-%m-%d"),
                "months": int(len(candidate.equity) - 1),
            },
            "strategy_metrics": candidate.metrics,
            "spy_metrics": spy.metrics,
            "growth_metrics": growth.metrics,
            "matched_metrics": matched.metrics,
            "comparison_vs_SPY": pooled_comparison,
            "comparison_vs_growth": growth_comparison,
            "comparison_vs_matched": matched_comparison,
            "cost_50bps_cagr_difference_vs_SPY": (
                candidate_stress.metrics["cagr"] - spy_stress.metrics["cagr"]
            ),
            "fixed_halves_vs_SPY": pooled_halves,
            "fixed_halves_vs_growth": _halves(candidate, growth),
            "rolling_five_year_vs_SPY": _rolling_comparison(candidate, spy),
            "rolling_five_year_vs_growth": _rolling_comparison(candidate, growth),
            "rolling_five_year_vs_matched": _rolling_comparison(candidate, matched),
            "post_entry_diagnostics_not_used_for_frozen_gate": _post_entry_diagnostics(
                candidate,
                spy=spy,
                growth=growth,
                matched=matched,
                include_bootstrap=True,
            ),
            "entry_gates": pooled_gates,
            "passed_gate_count": pooled_passed,
            "required_gate_count": len(pooled_gates),
        },
        "data_gates": data_gates,
        "data_passed_gate_count": data_passed,
        "data_required_gate_count": len(data_gates),
        "path_pass_rule": "each_at_least_10_of_12",
        "all_paths_passed": each_path_passes,
        "pooled_passed_gate_count": pooled_passed,
        "pooled_required_gate_count": len(pooled_gates),
        "paper_entry_passed_gate_count": (
            sum(
                min(data["passed_gate_count"], data["required_pass_count"])
                for data in path_data.values()
            )
            + pooled_passed
            + data_passed
        ),
        "paper_entry_required_gate_count": (3 * 10 + len(pooled_gates) + len(data_gates)),
        "paper_state_created": False,
        "evidence_boundary": {
            "classification": "theory_fixed_product_definition_sensitivity_with_seen_summaries_but_post_freeze_joint_paths",
            "official_summary_performance_seen_before_freeze": True,
            "iwf_product_definition_seen_in_prior_research": True,
            "joint_paths_computed_after_freeze": True,
            "three_growth_indexes_are_not_interchangeable": True,
            "gold_is_not_cash_or_principal_protection": True,
        },
    }
