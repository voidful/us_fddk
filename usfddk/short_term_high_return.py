from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from usfddk.data import panel_fingerprint
from usfddk.engine import run_backtest
from usfddk.metrics import compute_metrics, newey_west_mean_test
from usfddk.models import BacktestResult, MarketPanel
from usfddk.strategies import buy_and_hold_targets, fixed_weight_targets
from usfddk.universe import StockRecord
from usfddk.validation import (
    deflated_sharpe_ratio,
    probabilistic_sharpe_ratio,
    probability_of_backtest_overfitting,
)

SHORT_TERM_SCHEMA_VERSION = 1
SHORT_TERM_START = "2006-08-01"
SHORT_TERM_END = "2026-07-31"
SHORT_TERM_PRIMARY_COST_BPS = 10.0
SHORT_TERM_STRESS_COST_BPS = (25.0, 50.0)
SHORT_TERM_GLOBAL_SEARCH_TRIALS = 6_137
SHORT_TERM_STOCK_PANEL_SHA256 = (
    "6a7ca6b83b1570007424daa46b0ff4e8fb4a655d39298a0f4f6d74c3b7ea3a66"
)


def _sha256_file(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _completed_period_mask(index: pd.DatetimeIndex, frequency: str) -> pd.Series:
    if frequency == "monthly":
        periods = pd.Series(index.to_period("M"), index=index)
    elif frequency == "weekly":
        periods = pd.Series(index.to_period("W-FRI"), index=index)
    else:
        raise ValueError("frequency 必須是 monthly 或 weekly")
    mask = periods.ne(periods.shift(-1)).fillna(True)
    if len(index):
        last = pd.Timestamp(index[-1]).normalize()
        try:
            import exchange_calendars as xcals

            calendar = xcals.get_calendar("XNYS")
            session = calendar.date_to_session(last, direction="previous")
            next_session = pd.Timestamp(calendar.next_session(session)).tz_localize(None)
            if frequency == "monthly":
                mask.iloc[-1] = next_session.to_period("M") != last.to_period("M")
            else:
                mask.iloc[-1] = next_session.to_period("W-FRI") != last.to_period("W-FRI")
        except Exception:
            next_day = last + pd.offsets.BDay()
            if frequency == "monthly":
                mask.iloc[-1] = next_day.to_period("M") != last.to_period("M")
            else:
                mask.iloc[-1] = next_day.to_period("W-FRI") != last.to_period("W-FRI")
    return mask


def current_cohort_composite_targets(
    panel: MarketPanel,
    records: list[StockRecord],
) -> pd.DataFrame:
    """Frozen v1 stock-ranking rule, usable only as a biased current-cohort sandbox."""
    symbols = [record.symbol for record in records if record.symbol in panel.close.columns]
    if not symbols:
        raise ValueError("現時大型股名單與行情沒有共同代號")
    close = panel.close[symbols]
    volume = panel.volume[symbols]
    sector = {record.symbol: record.sector for record in records}
    momentum_12_1 = close.shift(21).div(close.shift(252)).sub(1.0)
    momentum_6_1 = close.shift(21).div(close.shift(126)).sub(1.0)
    trend_200 = close.div(close.rolling(200, min_periods=200).mean()).sub(1.0)
    volatility_63 = close.pct_change(fill_method=None).rolling(63).std(ddof=1) * np.sqrt(252)
    median_dollar_volume = (close * volume).rolling(20).median()
    targets = pd.DataFrame(np.nan, index=close.index, columns=symbols)

    for day in close.index[_completed_period_mask(close.index, "monthly")]:
        valid = (
            momentum_12_1.loc[day].notna()
            & momentum_6_1.loc[day].notna()
            & trend_200.loc[day].notna()
            & volatility_63.loc[day].notna()
            & (close.loc[day] > 5.0)
            & (median_dollar_volume.loc[day] >= 20_000_000.0)
        )
        eligible = list(valid.index[valid])
        if len(eligible) < 5:
            continue
        score = (
            0.45 * momentum_12_1.loc[day, eligible].rank(pct=True)
            + 0.25 * momentum_6_1.loc[day, eligible].rank(pct=True)
            + 0.20 * trend_200.loc[day, eligible].rank(pct=True)
            + 0.10 * (-volatility_63.loc[day, eligible]).rank(pct=True)
        )
        selected: list[str] = []
        sector_counts: dict[str, int] = {}
        for ticker in sorted(eligible, key=lambda item: (-float(score[item]), item)):
            ticker_sector = sector[ticker]
            if sector_counts.get(ticker_sector, 0) >= 3:
                continue
            selected.append(ticker)
            sector_counts[ticker_sector] = sector_counts.get(ticker_sector, 0) + 1
            if len(selected) == 10:
                break
        row = pd.Series(0.0, index=symbols)
        row.loc[selected] = 1.0 / len(selected)
        targets.loc[day] = row
    return targets


def taiwan_v85_translation_targets(
    panel: MarketPanel,
    records: list[StockRecord],
    *,
    market_regime: bool,
    correlation_filter: bool,
) -> pd.DataFrame:
    """Literal weekly 20-day-momentum/60-day-trend translation for ablation only.

    It deliberately does not copy leverage, tiered sizing, take-profit or stop-loss
    settings. Those choices are not supported by point-in-time U.S. constituent data.
    """
    symbols = [record.symbol for record in records if record.symbol in panel.close.columns]
    close = panel.close[symbols]
    volume = panel.volume[symbols]
    sector = {record.symbol: record.sector for record in records}
    momentum_20 = close.pct_change(20, fill_method=None)
    trend_60 = close > close.rolling(60, min_periods=60).mean()
    median_dollar_volume = (close * volume).rolling(20).median()
    spy_trend = panel.close["SPY"] > panel.close["SPY"].rolling(60, min_periods=60).mean()
    columns = [*symbols, "SHY"]
    targets = pd.DataFrame(np.nan, index=close.index, columns=columns)

    for day in close.index[_completed_period_mask(close.index, "weekly")]:
        valid = (
            momentum_20.loc[day].notna()
            & trend_60.loc[day]
            & (close.loc[day] > 5.0)
            & (median_dollar_volume.loc[day] >= 20_000_000.0)
        )
        eligible = list(valid.index[valid])
        if market_regime and not bool(spy_trend.loc[day]):
            eligible = []
        selected: list[str] = []
        sector_counts: dict[str, int] = {}
        for ticker in sorted(
            eligible, key=lambda item: (-float(momentum_20.loc[day, item]), item)
        ):
            ticker_sector = sector[ticker]
            if sector_counts.get(ticker_sector, 0) >= 2:
                continue
            if correlation_filter and selected:
                recent = close.loc[:day, [*selected, ticker]].tail(61).pct_change(fill_method=None)
                correlations = recent.corr().loc[ticker, selected]
                if int((correlations > 0.70).sum()) >= 2:
                    continue
            selected.append(ticker)
            sector_counts[ticker_sector] = sector_counts.get(ticker_sector, 0) + 1
            if len(selected) == 7:
                break
        row = pd.Series(0.0, index=columns)
        if selected:
            row.loc[selected] = 1.0 / len(selected)
        else:
            row.loc["SHY"] = 1.0
        targets.loc[day] = row
    return targets


def _clean_metrics(result: BacktestResult) -> dict[str, float]:
    return {key: float(value) for key, value in result.metrics.items()}


def _excess_sharpe(returns: pd.Series, risk_free: pd.Series) -> float:
    aligned = pd.concat(
        [returns.rename("asset"), risk_free.rename("risk_free")], axis=1, join="inner"
    ).dropna()
    excess = aligned["asset"] - aligned["risk_free"]
    standard_deviation = float(excess.std(ddof=1))
    if standard_deviation <= 0:
        return 0.0
    return float(excess.mean() / standard_deviation * np.sqrt(252.0))


def _period_metrics(result: BacktestResult, start: str, end: str) -> dict[str, float]:
    equity = result.equity.loc[start:end]
    returns = result.returns.loc[start:end]
    turnover = result.turnover.loc[start:end]
    return {key: float(value) for key, value in compute_metrics(equity, returns, turnover).items()}


def _fixed_halves(candidate: BacktestResult, benchmark: BacktestResult) -> dict[str, Any]:
    halves = {
        "first": ("2006-08-01", "2016-07-29"),
        "second": ("2016-08-01", "2026-07-31"),
    }
    output: dict[str, Any] = {}
    for label, (start, end) in halves.items():
        strategy_metrics = _period_metrics(candidate, start, end)
        benchmark_metrics = _period_metrics(benchmark, start, end)
        output[label] = {
            "start": start,
            "end": end,
            "strategy_metrics": strategy_metrics,
            "benchmark_metrics": benchmark_metrics,
            "cagr_difference": strategy_metrics["cagr"] - benchmark_metrics["cagr"],
        }
    return output


def _rolling_comparison(
    candidate: BacktestResult,
    benchmark: BacktestResult,
    *,
    window: int,
) -> dict[str, Any]:
    aligned = pd.concat(
        [candidate.equity.rename("candidate"), benchmark.equity.rename("benchmark")], axis=1
    ).dropna()
    periods = pd.Series(aligned.index.to_period("M"), index=aligned.index)
    endpoints = aligned.index[periods.ne(periods.shift(-1)).fillna(True).to_numpy()]
    rows: list[dict[str, float | str]] = []
    for end in endpoints:
        position = aligned.index.get_loc(end)
        if not isinstance(position, int) or position < window:
            continue
        sample = aligned.iloc[position - window : position + 1]
        years = (sample.index[-1] - sample.index[0]).days / 365.2425
        candidate_cagr = float((sample["candidate"].iloc[-1] / sample["candidate"].iloc[0]) ** (1 / years) - 1)
        benchmark_cagr = float((sample["benchmark"].iloc[-1] / sample["benchmark"].iloc[0]) ** (1 / years) - 1)
        rows.append(
            {
                "end": pd.Timestamp(end).strftime("%Y-%m-%d"),
                "candidate_cagr": candidate_cagr,
                "benchmark_cagr": benchmark_cagr,
                "cagr_difference": candidate_cagr - benchmark_cagr,
            }
        )
    differences = pd.Series([float(row["cagr_difference"]) for row in rows], dtype=float)
    return {
        "window_sessions": window,
        "windows": int(len(rows)),
        "cagr_win_fraction": float((differences > 0).mean()) if len(differences) else 0.0,
        "median_cagr_difference": float(differences.median()) if len(differences) else 0.0,
        "worst_cagr_difference": float(differences.min()) if len(differences) else 0.0,
        "best_cagr_difference": float(differences.max()) if len(differences) else 0.0,
        "series": rows,
    }


def _stress_periods(results: dict[str, BacktestResult]) -> dict[str, Any]:
    periods = {
        "global_financial_crisis": ("2007-10-09", "2009-03-09"),
        "covid_crash": ("2020-02-19", "2020-03-23"),
        "rate_hike_2022": ("2022-01-03", "2022-12-30"),
    }
    output: dict[str, Any] = {}
    for label, (start, end) in periods.items():
        rows: dict[str, Any] = {}
        for key, result in results.items():
            equity = result.equity.loc[start:end].dropna()
            if len(equity) < 2:
                continue
            rows[key] = {
                "return": float(equity.iloc[-1] / equity.iloc[0] - 1.0),
                "max_drawdown": float((equity / equity.cummax() - 1.0).min()),
                "worst_day": float(result.returns.reindex(equity.index).min()),
            }
        output[label] = {"start": start, "end": end, "results": rows}
    return output


def _comparison(
    candidate: BacktestResult,
    benchmark: BacktestResult,
    risk_free: pd.Series,
) -> dict[str, Any]:
    aligned = pd.concat(
        [candidate.returns.rename("candidate"), benchmark.returns.rename("benchmark")], axis=1
    ).dropna()
    active = aligned["candidate"] - aligned["benchmark"]
    return {
        "cagr_difference": candidate.metrics["cagr"] - benchmark.metrics["cagr"],
        "sharpe_difference": candidate.metrics["sharpe"] - benchmark.metrics["sharpe"],
        "drawdown_difference": candidate.metrics["max_drawdown"]
        - benchmark.metrics["max_drawdown"],
        "candidate_excess_sharpe_vs_shy": _excess_sharpe(candidate.returns.iloc[1:], risk_free),
        "benchmark_excess_sharpe_vs_shy": _excess_sharpe(benchmark.returns.iloc[1:], risk_free),
        "active_newey_west": newey_west_mean_test(active),
        "active_probabilistic_sharpe": probabilistic_sharpe_ratio(active),
        "active_global_deflated_sharpe": deflated_sharpe_ratio(
            active, trials=SHORT_TERM_GLOBAL_SEARCH_TRIALS
        ),
    }


def build_short_term_high_return_research(
    panel: MarketPanel,
    records: list[StockRecord],
    *,
    snapshot_path: str | Path,
) -> dict[str, Any]:
    """Build the auditable v1 sandbox without granting Paper eligibility."""
    if panel_fingerprint(panel) != SHORT_TERM_STOCK_PANEL_SHA256:
        raise ValueError("短線研究快照指紋與凍結值不符")
    if panel.end.strftime("%Y-%m-%d") != SHORT_TERM_END:
        raise ValueError("短線研究快照終點與凍結值不符")
    symbols = [record.symbol for record in records if record.symbol in panel.close.columns]
    complete_symbols = [
        ticker
        for ticker in symbols
        if panel.close.loc[:SHORT_TERM_START, ticker].notna().any()
        and bool(panel.close.loc[SHORT_TERM_START:SHORT_TERM_END, ticker].notna().all())
    ]
    if len(complete_symbols) < 20:
        raise ValueError("完整現時大型股對照不足 20 隻")

    candidate_targets = current_cohort_composite_targets(panel, records)
    candidate = run_backtest(
        panel,
        candidate_targets,
        name="現時大型股綜合動量輪選（有偏差）",
        cost_bps=SHORT_TERM_PRIMARY_COST_BPS,
        start=SHORT_TERM_START,
    )
    candidate_costs = {
        str(int(cost)): run_backtest(
            panel,
            candidate_targets,
            name=f"現時大型股綜合動量輪選 {int(cost)}bps",
            cost_bps=cost,
            start=SHORT_TERM_START,
        )
        for cost in SHORT_TERM_STRESS_COST_BPS
    }
    qqq = run_backtest(
        panel,
        buy_and_hold_targets(panel.close, "QQQ", signal_on=SHORT_TERM_START),
        name="QQQ 買入持有",
        cost_bps=SHORT_TERM_PRIMARY_COST_BPS,
        start=SHORT_TERM_START,
    )
    spy = run_backtest(
        panel,
        buy_and_hold_targets(panel.close, "SPY", signal_on=SHORT_TERM_START),
        name="SPY 買入持有",
        cost_bps=SHORT_TERM_PRIMARY_COST_BPS,
        start=SHORT_TERM_START,
    )
    equal_weights = {ticker: 1.0 / len(complete_symbols) for ticker in complete_symbols}
    cohort_monthly = run_backtest(
        panel,
        fixed_weight_targets(panel.close, equal_weights, signal_on=SHORT_TERM_START),
        name="現時完整大型股池等權月度再平衡（有偏差）",
        cost_bps=SHORT_TERM_PRIMARY_COST_BPS,
        start=SHORT_TERM_START,
    )
    drift_targets = pd.DataFrame(
        np.nan, index=panel.close.index, columns=complete_symbols, dtype=float
    )
    first_session = panel.close.index[panel.close.index >= pd.Timestamp(SHORT_TERM_START)][0]
    drift_targets.loc[first_session] = pd.Series(equal_weights)
    cohort_drift = run_backtest(
        panel,
        drift_targets,
        name="現時完整大型股池起點等權後漂移（有偏差）",
        cost_bps=SHORT_TERM_PRIMARY_COST_BPS,
        start=SHORT_TERM_START,
    )

    translations: dict[str, BacktestResult] = {}
    for key, market_regime, correlation_filter in (
        ("tw_v85_weekly", False, False),
        ("tw_v85_weekly_spy_regime", True, False),
        ("tw_v85_weekly_spy_regime_corr", True, True),
    ):
        targets = taiwan_v85_translation_targets(
            panel,
            records,
            market_regime=market_regime,
            correlation_filter=correlation_filter,
        )
        translations[key] = run_backtest(
            panel,
            targets,
            name=key,
            cost_bps=SHORT_TERM_PRIMARY_COST_BPS,
            start=SHORT_TERM_START,
        )

    pbo_frame = pd.concat(
        {
            "frozen_composite": candidate.returns,
            **{key: result.returns for key, result in translations.items()},
        },
        axis=1,
    )
    pbo = probability_of_backtest_overfitting(pbo_frame, slices=10)
    risk_free = panel.close["SHY"].pct_change(fill_method=None).reindex(candidate.returns.index)
    qqq_comparison = _comparison(candidate, qqq, risk_free)
    halves = _fixed_halves(candidate, qqq)
    rolling_three = _rolling_comparison(candidate, qqq, window=756)
    rolling_five = _rolling_comparison(candidate, qqq, window=1_260)
    fifty_bps_difference = (
        candidate_costs["50"].metrics["cagr"] - qqq.metrics["cagr"]
    )

    data_gates = {
        "frozen_snapshot_hash_pass": True,
        "twenty_year_window_pass": True,
        "next_open_execution_pass": candidate.diagnostics["execution_clock"]
        == "signal at close t; rebalance at adjusted open t+1",
        "point_in_time_membership_pass": False,
        "delisted_and_acquired_returns_pass": False,
        "historical_sector_classification_pass": False,
        "explicit_corporate_action_ledger_pass": False,
    }
    economic_gates = {
        "primary_cagr_beats_qqq_by_2pp": qqq_comparison["cagr_difference"] >= 0.02,
        "excess_sharpe_beats_qqq": qqq_comparison["candidate_excess_sharpe_vs_shy"]
        > qqq_comparison["benchmark_excess_sharpe_vs_shy"],
        "max_drawdown_not_more_than_5pp_deeper": candidate.metrics["max_drawdown"]
        >= qqq.metrics["max_drawdown"] - 0.05,
        "cost_50bps_beats_qqq_by_50bp": fifty_bps_difference >= 0.005,
        "both_fixed_halves_beat_qqq_by_50bp": all(
            value["cagr_difference"] >= 0.005 for value in halves.values()
        ),
        "rolling_three_year_win_fraction_at_least_60pct": rolling_three[
            "cagr_win_fraction"
        ]
        >= 0.60,
        "rolling_three_year_median_edge_positive": rolling_three[
            "median_cagr_difference"
        ]
        > 0.0,
        "beats_current_cohort_monthly_equal_weight": candidate.metrics["cagr"]
        > cohort_monthly.metrics["cagr"],
        "beats_current_cohort_drift": candidate.metrics["cagr"]
        > cohort_drift.metrics["cagr"],
        "active_newey_west_t_at_least_1_96": qqq_comparison["active_newey_west"][
            "t_stat"
        ]
        >= 1.96,
        "active_psr_at_least_95pct": qqq_comparison["active_probabilistic_sharpe"][
            "probability"
        ]
        >= 0.95,
        "active_global_dsr_at_least_95pct": qqq_comparison[
            "active_global_deflated_sharpe"
        ]["probability"]
        >= 0.95,
        "pbo_not_above_20pct": bool(np.isfinite(pbo["pbo"]) and pbo["pbo"] <= 0.20),
    }
    all_gates = {**data_gates, **economic_gates}

    return {
        "schema_version": SHORT_TERM_SCHEMA_VERSION,
        "status": "research_blocked_by_point_in_time_data_and_baselines",
        "paper_eligible": False,
        "trade_ready": False,
        "real_money_action_usd": 0,
        "reader_capital_example_usd": 1_000,
        "research_role": "biased_sandbox_and_negative_translation_ablation",
        "period": {
            "start": SHORT_TERM_START,
            "end": SHORT_TERM_END,
            "sessions": int(len(candidate.equity)),
            "years": float(
                (candidate.equity.index[-1] - candidate.equity.index[0]).days / 365.2425
            ),
        },
        "snapshot": {
            "path": Path(snapshot_path).name,
            "archive_sha256": _sha256_file(snapshot_path),
            "panel_sha256": panel_fingerprint(panel),
            "universe_as_of": sorted({record.as_of for record in records}),
            "current_watchlist_count": len(symbols),
            "complete_current_cohort_count": len(complete_symbols),
            "survivorship_bias_warning": True,
        },
        "frozen_candidate": {
            "label": "現時大型股綜合動量輪選",
            "valid_for_investment_decision": False,
            "invalid_reason": "2026-07-30 現時名單倒推歷史，缺逐期成分股及退市回報",
            "metrics": _clean_metrics(candidate),
            "current_target_not_actionable": {
                key: float(value)
                for key, value in candidate.current_target.items()
                if value > 0
            },
            "cost_sensitivity": {
                "10_bps": _clean_metrics(candidate),
                **{
                    f"{key}_bps": _clean_metrics(value)
                    for key, value in candidate_costs.items()
                },
            },
        },
        "baselines": {
            "QQQ": _clean_metrics(qqq),
            "SPY": _clean_metrics(spy),
            "current_cohort_monthly_equal_weight": _clean_metrics(cohort_monthly),
            "current_cohort_start_equal_then_drift": _clean_metrics(cohort_drift),
        },
        "comparison_vs_qqq": qqq_comparison,
        "fixed_halves_vs_qqq": halves,
        "rolling_three_year_vs_qqq": rolling_three,
        "rolling_five_year_vs_qqq": rolling_five,
        "stress_periods": _stress_periods(
            {
                "frozen_candidate": candidate,
                "QQQ": qqq,
                "cohort_drift": cohort_drift,
            }
        ),
        "taiwan_reference_translation_ablation": {
            "description": "20日動量、60日趨勢、每週 Top-7；逐層加入 SPY regime 及相關性濾網",
            "all_use_current_2026_cohort_and_are_not_investable": True,
            "results": {
                key: _clean_metrics(result) for key, result in translations.items()
            },
            "finding": "三個直譯版本均未勝 QQQ 或現時股池漂移基準；不移植加碼與止蝕參數",
        },
        "pbo_across_four_current_cohort_variants": pbo,
        "data_gates": data_gates,
        "economic_and_statistical_gates": economic_gates,
        "passed_gate_count": int(sum(bool(value) for value in all_gates.values())),
        "required_gate_count": len(all_gates),
        "global_search_trials": SHORT_TERM_GLOBAL_SEARCH_TRIALS,
        "paper_state_created": False,
        "decision": (
            "研究繼續，但不開 Paper。現時名單沙盒的表面 CAGR 勝 QQQ，卻輸同一現時股池起點等權後漂移，"
            "而且逐期成分、退市及公司行動證據未齊；台股 20 日動量直譯亦未通過美股基準。"
        ),
    }
