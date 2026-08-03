from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from usfddk.data import panel_fingerprint
from usfddk.engine import run_backtest
from usfddk.metrics import newey_west_mean_test
from usfddk.models import BacktestResult, MarketPanel
from usfddk.short_term_high_return import (
    _completed_period_mask,
    _fixed_halves,
    _fixed_horizon_basket_return,
    _moving_block_bootstrap_mean,
    _rolling_comparison,
    _stress_periods,
)
from usfddk.strategies import buy_and_hold_targets, fixed_weight_targets
from usfddk.validation import (
    deflated_sharpe_ratio,
    probabilistic_sharpe_ratio,
    probability_of_backtest_overfitting,
)

SECTOR_SCHEMA_VERSION = 1
SECTOR_PROTOCOL_SHA256 = (
    "3affdc24f39353a6eb606075f802ffe6252cac01be57b13b9d098114a502a80d"
)
SECTOR_MAPPING_SHA256 = (
    "c42743ed3d884c818dd3632d20db9f80d225ea1ccf361ea2a1ed1c1a76457a67"
)
SECTOR_PROTOCOL_COMMIT = "543259105c7c426aa15436b7f15a33dd2ffff620"
SECTOR_SNAPSHOT_COMMIT = "4378d24f703c6e1408af9f7b3e7dfd0fa6674a9e"
SECTOR_PANEL_SHA256 = (
    "7a13b864f5e4aeaec08c1c78e2ed3f5fd64a7586acf7818e16c0ca945870d392"
)
SECTOR_ARCHIVE_SHA256 = (
    "5f9a020e33399705ac52b9bdd2f5cda1d569909cd3577f80de4bf3f92a935105"
)
SECTOR_FORMAL_START = "2006-08-01"
SECTOR_FORMAL_END = "2026-07-31"
SECTOR_SIGNAL_START = "2006-07-31"
SECTOR_PRIMARY_TOP_K = 3
SECTOR_TOP_K_NEIGHBORS = (2, 3, 4)
SECTOR_PRIMARY_COST_BPS = 10.0
SECTOR_STRESS_COST_BPS = (25.0, 50.0)
SECTOR_GLOBAL_SEARCH_TRIALS = 6_141
SECTOR_ETFS = (
    "VAW",
    "VCR",
    "VDC",
    "VDE",
    "VFH",
    "VGT",
    "VHT",
    "VIS",
    "VOX",
    "VPU",
)
SECTOR_LABELS = {
    "VAW": "基礎材料",
    "VCR": "非必需消費",
    "VDC": "必需消費",
    "VDE": "能源",
    "VFH": "金融",
    "VGT": "資訊科技",
    "VHT": "醫療保健",
    "VIS": "工業",
    "VOX": "通訊服務",
    "VPU": "公用事業",
}
REQUIRED_TICKERS = tuple(sorted((*SECTOR_ETFS, "QQQ", "SHY", "SPY", "VTI")))


def _sha256_file(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _metrics(result: BacktestResult) -> dict[str, float]:
    return {key: float(value) for key, value in result.metrics.items()}


def sector_monthly_targets(
    panel: MarketPanel,
    *,
    top_k: int = SECTOR_PRIMARY_TOP_K,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Frozen monthly sector ranking and its exact equity-exposure control."""
    if top_k < 1 or top_k > len(SECTOR_ETFS):
        raise ValueError("行業 Top-K 超出固定投資範圍")
    close = panel.close[list(SECTOR_ETFS)]
    momentum = close.pct_change(20, fill_method=None)
    trend = close > close.rolling(60, min_periods=60).mean()
    columns = [*SECTOR_ETFS, "SHY"]
    candidate = pd.DataFrame(np.nan, index=close.index, columns=columns)
    matched = pd.DataFrame(np.nan, index=close.index, columns=columns)

    for day in close.index[_completed_period_mask(close.index, "monthly")]:
        eligible = list(
            close.columns[(momentum.loc[day].notna() & trend.loc[day]).to_numpy()]
        )
        selected = sorted(
            eligible,
            key=lambda ticker: (-float(momentum.loc[day, ticker]), ticker),
        )[:top_k]
        equity_weight = len(selected) / top_k

        row = pd.Series(0.0, index=columns)
        if selected:
            row.loc[selected] = 1.0 / top_k
        row["SHY"] = 1.0 - equity_weight
        candidate.loc[day] = row

        control = pd.Series(0.0, index=columns)
        control.loc[list(SECTOR_ETFS)] = equity_weight / len(SECTOR_ETFS)
        control["SHY"] = 1.0 - equity_weight
        matched.loc[day] = control
    return candidate, matched


def _excess_sharpe(returns: pd.Series, risk_free: pd.Series) -> float:
    aligned = pd.concat(
        [returns.rename("asset"), risk_free.rename("risk_free")],
        axis=1,
        join="inner",
    ).dropna()
    excess = aligned["asset"] - aligned["risk_free"]
    standard_deviation = float(excess.std(ddof=1))
    if standard_deviation <= 0.0:
        return 0.0
    return float(excess.mean() / standard_deviation * np.sqrt(252.0))


def _active_comparison(
    candidate: BacktestResult,
    benchmark: BacktestResult,
    risk_free: pd.Series,
) -> dict[str, Any]:
    aligned = pd.concat(
        [
            candidate.returns.rename("candidate"),
            benchmark.returns.rename("benchmark"),
        ],
        axis=1,
    ).dropna()
    active = aligned["candidate"] - aligned["benchmark"]
    return {
        "cagr_difference": float(
            candidate.metrics["cagr"] - benchmark.metrics["cagr"]
        ),
        "sharpe_difference": float(
            candidate.metrics["sharpe"] - benchmark.metrics["sharpe"]
        ),
        "drawdown_difference": float(
            candidate.metrics["max_drawdown"]
            - benchmark.metrics["max_drawdown"]
        ),
        "candidate_excess_sharpe_vs_shy": _excess_sharpe(
            candidate.returns.iloc[1:], risk_free
        ),
        "benchmark_excess_sharpe_vs_shy": _excess_sharpe(
            benchmark.returns.iloc[1:], risk_free
        ),
        "active_newey_west": newey_west_mean_test(active, max_lag=9),
        "active_probabilistic_sharpe": probabilistic_sharpe_ratio(active),
        "active_global_deflated_sharpe": deflated_sharpe_ratio(
            active,
            trials=SECTOR_GLOBAL_SEARCH_TRIALS,
        ),
    }


def _signal_layer_external_diagnostic(panel: MarketPanel) -> dict[str, Any]:
    close = panel.close[list(SECTOR_ETFS)]
    momentum = close.pct_change(20, fill_method=None)
    trend = close > close.rolling(60, min_periods=60).mean()
    weekly = _completed_period_mask(close.index, "weekly")
    signal_dates = close.index[
        weekly.to_numpy()
        & (close.index >= pd.Timestamp(SECTOR_FORMAL_START))
        & (close.index <= pd.Timestamp(SECTOR_FORMAL_END))
    ]
    cost = 20.0 / 10_000.0
    rows: list[dict[str, Any]] = []

    for signal_date in signal_dates:
        position = close.index.get_loc(signal_date)
        if not isinstance(position, int):
            continue
        entry_position = position + 1
        exit_position = entry_position + 19
        if exit_position >= len(close.index):
            continue
        eligible = list(
            close.columns[(momentum.loc[signal_date].notna() & trend.loc[signal_date]).to_numpy()]
        )
        if len(eligible) < 3:
            continue
        selected = sorted(
            eligible,
            key=lambda ticker: (-float(momentum.loc[signal_date, ticker]), ticker),
        )[:3]
        entry_date = close.index[entry_position]
        exit_date = close.index[exit_position]
        rows.append(
            {
                "signal_date": pd.Timestamp(signal_date).strftime("%Y-%m-%d"),
                "entry_date": pd.Timestamp(entry_date).strftime("%Y-%m-%d"),
                "exit_date": pd.Timestamp(exit_date).strftime("%Y-%m-%d"),
                "eligible_count": int(len(eligible)),
                "top3_return": _fixed_horizon_basket_return(
                    panel,
                    selected,
                    entry_date=entry_date,
                    exit_date=exit_date,
                    cost=cost,
                ),
                "eligible_equal_return": _fixed_horizon_basket_return(
                    panel,
                    eligible,
                    entry_date=entry_date,
                    exit_date=exit_date,
                    cost=cost,
                ),
                "all_sectors_equal_return": _fixed_horizon_basket_return(
                    panel,
                    list(SECTOR_ETFS),
                    entry_date=entry_date,
                    exit_date=exit_date,
                    cost=cost,
                ),
                "qqq_return": _fixed_horizon_basket_return(
                    panel,
                    ["QQQ"],
                    entry_date=entry_date,
                    exit_date=exit_date,
                    cost=cost,
                ),
            }
        )

    events = pd.DataFrame(rows)
    if events.empty:
        raise ValueError("外部行業 ETF 固定持有期沒有可用事件")
    selected = events["top3_return"]
    eligible = events["eligible_equal_return"]
    excess = selected - eligible
    comparisons: dict[str, Any] = {}
    for key, baseline in (
        ("eligible_equal", eligible),
        ("all_sectors_equal", events["all_sectors_equal_return"]),
        ("QQQ", events["qqq_return"]),
    ):
        difference = selected - baseline
        comparisons[key] = {
            "mean_difference": float(difference.mean()),
            "median_difference": float(difference.median()),
            "win_fraction": float((difference > 0.0).mean()),
            "newey_west": newey_west_mean_test(
                difference,
                max_lag=4,
                periods_per_year=52,
            ),
        }

    signal_dates_series = pd.to_datetime(events["signal_date"])
    halves: dict[str, Any] = {}
    for label, mask in (
        ("first", signal_dates_series <= pd.Timestamp("2016-07-29")),
        ("second", signal_dates_series >= pd.Timestamp("2016-08-01")),
    ):
        sample = excess.loc[mask.to_numpy()]
        halves[label] = {
            "events": int(len(sample)),
            "mean_difference": float(sample.mean()),
            "median_difference": float(sample.median()),
            "win_fraction": float((sample > 0.0).mean()),
        }
    bootstrap = _moving_block_bootstrap_mean(excess)
    primary = comparisons["eligible_equal"]
    gates = {
        "mean_difference_positive": primary["mean_difference"] > 0.0,
        "newey_west_t_at_least_1_96": primary["newey_west"]["t_stat"] >= 1.96,
        "bootstrap_95pct_low_positive": bootstrap["low"] > 0.0,
        "both_fixed_halves_positive": all(
            value["mean_difference"] > 0.0 for value in halves.values()
        ),
        "paired_win_fraction_above_50pct": primary["win_fraction"] > 0.50,
    }
    return {
        "valid_for_paper": False,
        "holding_sessions": 20,
        "round_trip_cost_bps": 20.0,
        "events": int(len(events)),
        "first_signal_date": str(events.iloc[0]["signal_date"]),
        "last_signal_date": str(events.iloc[-1]["signal_date"]),
        "mean_eligible_count": float(events["eligible_count"].mean()),
        "net_return_summary": {
            "top3_mean": float(selected.mean()),
            "top3_median": float(selected.median()),
            "eligible_equal_mean": float(eligible.mean()),
            "all_sectors_equal_mean": float(events["all_sectors_equal_return"].mean()),
            "QQQ_mean": float(events["qqq_return"].mean()),
        },
        "comparisons": comparisons,
        "fixed_halves_vs_eligible_equal": halves,
        "moving_block_bootstrap_mean_difference_vs_eligible_equal": bootstrap,
        "gates": gates,
        "passed_gate_count": int(sum(bool(value) for value in gates.values())),
        "required_gate_count": len(gates),
        "all_signal_gates_pass": all(gates.values()),
        "event_series": events.to_dict(orient="records"),
    }


def build_short_term_sector_etf_research(
    panel: MarketPanel,
    *,
    snapshot_path: str | Path,
    data_receipt: dict[str, Any],
) -> dict[str, Any]:
    """Calculate the frozen first-seen Vanguard sector confirmation once."""
    if panel_fingerprint(panel) != SECTOR_PANEL_SHA256:
        raise ValueError("Vanguard 行業 ETF 面板指紋與凍結收據不同")
    if _sha256_file(snapshot_path) != SECTOR_ARCHIVE_SHA256:
        raise ValueError("Vanguard 行業 ETF ZIP 雜湊與凍結收據不同")
    if tuple(sorted(panel.close.columns)) != REQUIRED_TICKERS:
        raise ValueError("Vanguard 行業 ETF 代號與凍結協議不同")
    if panel.end.strftime("%Y-%m-%d") != SECTOR_FORMAL_END:
        raise ValueError("Vanguard 行業 ETF 資料終點與凍結協議不同")
    if data_receipt.get("status") != (
        "short_term_sector_etf_first_external_download_contract_passed"
    ):
        raise ValueError("Vanguard 行業 ETF 首次數據契約未通過")
    if data_receipt.get("pre_registration_order_proved") is not True:
        raise ValueError("Vanguard 行業 ETF 數據沒有證明先凍結後下載")
    if data_receipt.get("calculation_started") is not False:
        raise ValueError("Vanguard 行業 ETF 數據收據不是計算前狀態")
    if not all(data_receipt.get("checks", {}).values()):
        raise ValueError("Vanguard 行業 ETF 數據完整性門檻未全部通過")

    target_by_k: dict[int, pd.DataFrame] = {}
    results_by_k: dict[int, BacktestResult] = {}
    matched_target: pd.DataFrame | None = None
    for top_k in SECTOR_TOP_K_NEIGHBORS:
        target, matched = sector_monthly_targets(panel, top_k=top_k)
        target_by_k[top_k] = target
        results_by_k[top_k] = run_backtest(
            panel,
            target,
            name=f"Vanguard 行業 20 日動量 Top-{top_k}",
            cost_bps=SECTOR_PRIMARY_COST_BPS,
            start=SECTOR_FORMAL_START,
        )
        if top_k == SECTOR_PRIMARY_TOP_K:
            matched_target = matched
    if matched_target is None:
        raise RuntimeError("沒有建立 Top-3 matched control")
    candidate = results_by_k[SECTOR_PRIMARY_TOP_K]
    matched = run_backtest(
        panel,
        matched_target,
        name="相同行業持倉比率等權控制",
        cost_bps=SECTOR_PRIMARY_COST_BPS,
        start=SECTOR_FORMAL_START,
    )
    cost_results = {
        str(int(cost)): run_backtest(
            panel,
            target_by_k[SECTOR_PRIMARY_TOP_K],
            name=f"Vanguard 行業 Top-3 {int(cost)}bps",
            cost_bps=cost,
            start=SECTOR_FORMAL_START,
        )
        for cost in SECTOR_STRESS_COST_BPS
    }

    buy_hold_results = {
        ticker: run_backtest(
            panel,
            buy_and_hold_targets(panel.close, ticker, signal_on=SECTOR_SIGNAL_START),
            name=f"{ticker} 買入持有",
            cost_bps=SECTOR_PRIMARY_COST_BPS,
            start=SECTOR_FORMAL_START,
        )
        for ticker in ("QQQ", "SPY", "VTI", *SECTOR_ETFS)
    }
    equal_weights = {ticker: 1.0 / len(SECTOR_ETFS) for ticker in SECTOR_ETFS}
    sector_equal_monthly = run_backtest(
        panel,
        fixed_weight_targets(
            panel.close,
            equal_weights,
            signal_on=SECTOR_SIGNAL_START,
        ),
        name="十行業月度等權",
        cost_bps=SECTOR_PRIMARY_COST_BPS,
        start=SECTOR_FORMAL_START,
    )
    drift_target = pd.DataFrame(
        np.nan,
        index=panel.close.index,
        columns=list(SECTOR_ETFS),
    )
    drift_target.loc[pd.Timestamp(SECTOR_SIGNAL_START)] = pd.Series(equal_weights)
    sector_equal_drift = run_backtest(
        panel,
        drift_target,
        name="十行業起點等權後漂移",
        cost_bps=SECTOR_PRIMARY_COST_BPS,
        start=SECTOR_FORMAL_START,
    )

    qqq = buy_hold_results["QQQ"]
    risk_free = panel.close["SHY"].pct_change(fill_method=None).reindex(candidate.returns.index)
    comparison_qqq = _active_comparison(candidate, qqq, risk_free)
    comparison_matched = _active_comparison(candidate, matched, risk_free)
    halves_qqq = _fixed_halves(candidate, qqq)
    rolling_three = _rolling_comparison(candidate, qqq, window=756)
    rolling_five = _rolling_comparison(candidate, qqq, window=1_260)
    signal = _signal_layer_external_diagnostic(panel)
    pbo = probability_of_backtest_overfitting(
        pd.concat(
            {
                f"top_{top_k}": result.returns
                for top_k, result in results_by_k.items()
            },
            axis=1,
        ),
        slices=10,
    )

    data_gates = {
        "protocol_hash_pass": data_receipt["protocol"]["sha256"]
        == SECTOR_PROTOCOL_SHA256,
        "product_mapping_hash_pass": data_receipt["product_mapping"]["sha256"]
        == SECTOR_MAPPING_SHA256,
        "first_download_after_freeze_pass": data_receipt[
            "pre_registration_order_proved"
        ]
        is True,
        "snapshot_hash_pass": data_receipt["snapshot"]["panel_sha256"]
        == SECTOR_PANEL_SHA256,
        "formal_ohlcv_complete_pass": all(
            value == 0
            for value in data_receipt["formal_period"][
                "missing_cells_by_field"
            ].values()
        ),
        "next_open_execution_pass": candidate.diagnostics["execution_clock"]
        == "signal at close t; rebalance at adjusted open t+1",
    }
    economic_gates = {
        "cagr_beats_qqq_by_2pp": comparison_qqq["cagr_difference"] >= 0.02,
        "excess_sharpe_beats_qqq": comparison_qqq[
            "candidate_excess_sharpe_vs_shy"
        ]
        > comparison_qqq["benchmark_excess_sharpe_vs_shy"],
        "max_drawdown_not_more_than_5pp_deeper_than_qqq": candidate.metrics[
            "max_drawdown"
        ]
        >= qqq.metrics["max_drawdown"] - 0.05,
        "cost_50bps_beats_qqq_by_50bp": cost_results["50"].metrics["cagr"]
        >= qqq.metrics["cagr"] + 0.005,
        "both_fixed_halves_beat_qqq_by_50bp": all(
            value["cagr_difference"] >= 0.005 for value in halves_qqq.values()
        ),
        "rolling_three_year_win_fraction_at_least_60pct": rolling_three[
            "cagr_win_fraction"
        ]
        >= 0.60,
        "rolling_three_year_median_edge_positive": rolling_three[
            "median_cagr_difference"
        ]
        > 0.0,
        "beats_matched_control_cagr": candidate.metrics["cagr"]
        > matched.metrics["cagr"],
        "beats_sector_monthly_equal_cagr": candidate.metrics["cagr"]
        > sector_equal_monthly.metrics["cagr"],
        "beats_sector_drift_cagr": candidate.metrics["cagr"]
        > sector_equal_drift.metrics["cagr"],
        "active_newey_west_t_at_least_1_96": comparison_qqq[
            "active_newey_west"
        ]["t_stat"]
        >= 1.96,
        "active_psr_at_least_95pct": comparison_qqq[
            "active_probabilistic_sharpe"
        ]["probability"]
        >= 0.95,
        "active_global_dsr_at_least_95pct": comparison_qqq[
            "active_global_deflated_sharpe"
        ]["probability"]
        >= 0.95,
        "top_k_pbo_not_above_20pct": bool(
            np.isfinite(pbo["pbo"]) and pbo["pbo"] <= 0.20
        ),
        "all_signal_layer_gates_pass": signal["all_signal_gates_pass"] is True,
    }
    all_gates = {**data_gates, **economic_gates}
    individual = {
        ticker: {
            "label": SECTOR_LABELS[ticker],
            "metrics": _metrics(buy_hold_results[ticker]),
        }
        for ticker in SECTOR_ETFS
    }
    best_ticker = max(
        SECTOR_ETFS,
        key=lambda ticker: buy_hold_results[ticker].metrics["cagr"],
    )

    return {
        "schema_version": SECTOR_SCHEMA_VERSION,
        "status": (
            "external_sector_product_validation_passed_but_stock_data_gate_still_closed"
            if all(all_gates.values())
            else "external_sector_product_validation_failed"
        ),
        "external_product_validation_passed": all(all_gates.values()),
        "paper_eligible": False,
        "trade_ready": False,
        "paper_state_created": False,
        "real_money_action_usd": 0,
        "research_role": "first_seen_external_sector_product_mechanism_validation",
        "protocol": {
            "sha256": SECTOR_PROTOCOL_SHA256,
            "mapping_sha256": SECTOR_MAPPING_SHA256,
            "protocol_commit": SECTOR_PROTOCOL_COMMIT,
            "snapshot_commit": SECTOR_SNAPSHOT_COMMIT,
        },
        "period": {
            "start": SECTOR_FORMAL_START,
            "end": SECTOR_FORMAL_END,
            "sessions": int(len(candidate.equity)),
            "years": float(
                (candidate.equity.index[-1] - candidate.equity.index[0]).days
                / 365.2425
            ),
        },
        "snapshot": {
            "path": Path(snapshot_path).name,
            "archive_sha256": SECTOR_ARCHIVE_SHA256,
            "panel_sha256": SECTOR_PANEL_SHA256,
            "first_joint_vanguard_sector_download": True,
            "formal_ohlcv_missing_cells": data_receipt["formal_period"][
                "missing_cells_by_field"
            ],
            "etf_survival_bias_reduced_not_eliminated": True,
        },
        "frozen_candidate": {
            "label": "Vanguard 十行業 20 日動量月度 Top-3",
            "metrics": _metrics(candidate),
            "cost_sensitivity": {
                "10_bps": _metrics(candidate),
                **{
                    f"{key}_bps": _metrics(value)
                    for key, value in cost_results.items()
                },
            },
        },
        "baselines": {
            "QQQ": _metrics(qqq),
            "SPY": _metrics(buy_hold_results["SPY"]),
            "VTI": _metrics(buy_hold_results["VTI"]),
            "matched_equity_exposure_equal_sector": _metrics(matched),
            "sector_monthly_equal": _metrics(sector_equal_monthly),
            "sector_start_equal_then_drift": _metrics(sector_equal_drift),
        },
        "comparison_vs_qqq": comparison_qqq,
        "comparison_vs_matched_control": comparison_matched,
        "fixed_halves_vs_qqq": halves_qqq,
        "rolling_three_year_vs_qqq": rolling_three,
        "rolling_five_year_vs_qqq": rolling_five,
        "stress_periods": _stress_periods(
            {
                "candidate": candidate,
                "QQQ": qqq,
                "matched_control": matched,
                "sector_drift": sector_equal_drift,
            }
        ),
        "top_k_sensitivity": {
            str(top_k): _metrics(result)
            for top_k, result in results_by_k.items()
        },
        "pbo_across_top_k_2_3_4": pbo,
        "fixed_20_day_signal_external_diagnostic": signal,
        "individual_sector_buy_and_hold_diagnostics": individual,
        "best_individual_sector_ex_post_not_a_candidate": {
            "ticker": best_ticker,
            "label": SECTOR_LABELS[best_ticker],
            "metrics": _metrics(buy_hold_results[best_ticker]),
        },
        "data_gates": data_gates,
        "economic_and_statistical_gates": economic_gates,
        "passed_gate_count": int(sum(bool(value) for value in all_gates.values())),
        "required_gate_count": len(all_gates),
        "global_search_trials": SECTOR_GLOBAL_SEARCH_TRIALS,
        "decision": (
            "只保留首次外部產品結果；不依結果改規則。短線 Paper 仍須等待合格 point-in-time "
            "個股成分及退市資料，而且必須由全現金開始累積前瞻成交。"
        ),
    }
