from __future__ import annotations

import hashlib
import io
import re
import zipfile
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from usfddk.data import panel_fingerprint
from usfddk.engine import run_backtest
from usfddk.metrics import compute_metrics, newey_west_mean_test
from usfddk.models import BacktestResult, MarketPanel
from usfddk.strategies import (
    buy_and_hold_targets,
    fixed_weight_targets,
    industry_momentum_core_tilt_targets,
    industry_selection_matched_targets,
)
from usfddk.validation import deflated_sharpe_ratio

V6_PROTOCOL_SHA256 = "bec68668983bfc3a778843337b7441df256fd805a75df758c60adceeb3a4072f"
V6_GLOBAL_SEARCH_TRIALS = 6_103
V6_MAIN_START = "2006-07-31"
V6_MAIN_END = "2026-07-31"
V6_EARLY_END = "2006-06-30"
V6_INDUSTRIES = ("XLB", "XLE", "XLF", "XLI", "XLK", "XLP", "XLU", "XLV", "XLY")
V6_TICKERS = ("SPY", *V6_INDUSTRIES, "SHY")
V6_ETF_PANEL_SHA256 = "9238e84a2fe5932676b48697e243a44427dc5bfd3ebd9c531388489168898a54"
V6_ETF_ARCHIVE_SHA256 = "95dd00595dc3e003bc40ad1c0f60d2f02fdba7120719416a2fe85f0bc03f7bde"
V6_FRENCH_INDUSTRY_SHA256 = "245ac83a105217b859502b636abe2006f5757ac2fda21e615eba761242be5e91"
V6_FRENCH_FACTORS_SHA256 = "80b88699a18ac408e2456d25b1004e340f3f7f8d41d5b476a0285bc53c6f0436"
FRENCH_INDUSTRIES = (
    "NoDur",
    "Durbl",
    "Manuf",
    "Enrgy",
    "HiTec",
    "Telcm",
    "Shops",
    "Hlth",
    "Utils",
    "Other",
)


def _sha256(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _read_single_zip_member(path: str | Path, expected_name: str) -> str:
    with zipfile.ZipFile(path) as archive:
        if archive.namelist() != [expected_name]:
            raise ValueError(f"French ZIP 成員不符：{archive.namelist()}")
        return archive.read(expected_name).decode("utf-8-sig")


def _parse_monthly_block(
    text: str,
    *,
    columns: tuple[str, ...],
    marker: str | None = None,
) -> pd.DataFrame:
    lines = text.splitlines()
    start = 0
    if marker is not None:
        matches = [idx for idx, line in enumerate(lines) if marker in line]
        if len(matches) != 1:
            raise ValueError(f"French 月資料標記數量不符：{marker}")
        start = matches[0] + 1
    header_index = next(
        (
            idx
            for idx in range(start, len(lines))
            if lines[idx].lstrip().startswith(",")
            and all(column in lines[idx] for column in columns)
        ),
        None,
    )
    if header_index is None:
        raise ValueError("找不到 French 月資料欄名")
    rows: list[str] = []
    for line in lines[header_index + 1 :]:
        if re.match(r"^\s*\d{6}\s*,", line):
            rows.append(line)
        elif rows:
            break
    if not rows:
        raise ValueError("French 月資料表為空")
    frame = pd.read_csv(io.StringIO("Date" + lines[header_index] + "\n" + "\n".join(rows)))
    frame.columns = [str(column).strip() for column in frame.columns]
    if tuple(frame.columns) != ("Date", *columns):
        raise ValueError(f"French 月資料欄位不符：{list(frame.columns)}")
    dates = frame.pop("Date").astype(str).str.strip()
    if not bool(dates.str.fullmatch(r"\d{6}").all()):
        raise ValueError("French 月資料日期格式不符")
    numeric = frame.apply(pd.to_numeric, errors="raise")
    if bool(((numeric <= -99.0) | (numeric == -999.0)).any().any()):
        raise ValueError("French 月資料含缺值代碼，拒絕補值")
    periods = pd.PeriodIndex(dates, freq="M")
    numeric.index = periods.to_timestamp("M")
    if numeric.index.has_duplicates or not numeric.index.is_monotonic_increasing:
        raise ValueError("French 月資料日期不是嚴格遞增且唯一")
    return numeric.astype(float).div(100.0)


def load_french_industry_proxy(
    industry_zip: str | Path,
    factors_zip: str | Path,
    *,
    start: str = "1927-01",
    end: str = "2005-12",
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    """Load and validate the frozen official monthly French proxy tables."""
    industry_hash = _sha256(industry_zip)
    factor_hash = _sha256(factors_zip)
    if industry_hash != V6_FRENCH_INDUSTRY_SHA256:
        raise ValueError("French 10 Industry 原始 ZIP 雜湊與 v6 凍結收據不同")
    if factor_hash != V6_FRENCH_FACTORS_SHA256:
        raise ValueError("French Factors 原始 ZIP 雜湊與 v6 凍結收據不同")
    industry_text = _read_single_zip_member(industry_zip, "10_Industry_Portfolios.csv")
    factor_text = _read_single_zip_member(factors_zip, "F-F_Research_Data_Factors.csv")
    industries = _parse_monthly_block(
        industry_text,
        columns=FRENCH_INDUSTRIES,
        marker="Average Value Weighted Returns -- Monthly",
    )
    factors = _parse_monthly_block(factor_text, columns=("Mkt-RF", "SMB", "HML", "RF"))
    start_stamp = pd.Period(start, freq="M").to_timestamp("M")
    end_stamp = pd.Period(end, freq="M").to_timestamp("M")
    industries = industries.loc[start_stamp:end_stamp]
    factors = factors.loc[start_stamp:end_stamp, ["Mkt-RF", "RF"]]
    expected = pd.period_range(start, end, freq="M").to_timestamp("M")
    if not industries.index.equals(expected) or not factors.index.equals(expected):
        raise ValueError("French 1927-01–2005-12 月份不連續或不完整")
    if industries.isna().any().any() or factors.isna().any().any():
        raise ValueError("French 代理資料含空值")
    receipt = {
        "source_database": "202605 CRSP database",
        "period": {"start": start, "end": end, "months": int(len(expected))},
        "industry": {
            "path": str(Path(industry_zip)),
            "sha256": industry_hash,
            "table": "Average Value Weighted Returns -- Monthly",
            "columns": list(FRENCH_INDUSTRIES),
        },
        "factors": {
            "path": str(Path(factors_zip)),
            "sha256": factor_hash,
            "columns": ["Mkt-RF", "RF"],
        },
        "missing_value_policy": "reject -99.99, -999, NaN; no fill",
    }
    return industries, factors, receipt


def monthly_industry_core_tilt_targets(
    industry_returns: pd.DataFrame, rf_returns: pd.Series
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Translate the frozen daily rule to the preregistered monthly proxy."""
    if tuple(industry_returns.columns) != FRENCH_INDUSTRIES:
        raise ValueError("French 產業欄位或順序與 v6 協議不同")
    if not industry_returns.index.equals(rf_returns.index):
        raise ValueError("French 產業與 RF 月份不一致")
    total_index = (1.0 + industry_returns).cumprod()
    scores = (1.0 + industry_returns.shift(1)).rolling(11, min_periods=11).apply(
        np.prod, raw=True
    ).sub(1.0)
    rf_score = (1.0 + rf_returns.shift(1)).rolling(11, min_periods=11).apply(
        np.prod, raw=True
    ).sub(1.0)
    trend = total_index > total_index.rolling(10, min_periods=10).mean()
    columns = ["MKT", *FRENCH_INDUSTRIES, "RF"]
    target = pd.DataFrame(np.nan, index=industry_returns.index, columns=columns)
    matched = pd.DataFrame(np.nan, index=industry_returns.index, columns=columns)
    for month in industry_returns.index:
        month_scores = scores.loc[month]
        hurdle = float(rf_score.loc[month])
        if month_scores.isna().any() or not np.isfinite(hurdle):
            continue
        eligible = [
            name
            for name in FRENCH_INDUSTRIES
            if bool(trend.loc[month, name]) and float(month_scores[name]) > hurdle
        ]
        selected = sorted(
            eligible, key=lambda name: (-float(month_scores[name]), name)
        )[:3]
        row = pd.Series(0.0, index=columns)
        row["MKT"] = 0.50
        row.loc[selected] = 1.0 / 6.0
        row["RF"] = 0.50 - len(selected) / 6.0
        target.loc[month] = row

        control = pd.Series(0.0, index=columns)
        control["MKT"] = 0.50
        if selected:
            control.loc[list(FRENCH_INDUSTRIES)] = (len(selected) / 6.0) / len(
                FRENCH_INDUSTRIES
            )
        control["RF"] = 0.50 - len(selected) / 6.0
        matched.loc[month] = control
    return target, matched


def run_monthly_backtest(
    asset_returns: pd.DataFrame,
    target_signals: pd.DataFrame,
    *,
    name: str,
    cost_bps: float,
    first_realized_month: pd.Timestamp | None = None,
) -> BacktestResult:
    """Apply month-t signals to month-t+1 returns with drift-aware turnover."""
    columns = list(target_signals.columns)
    returns = asset_returns.reindex(columns=columns)
    if not returns.index.equals(target_signals.index) or returns.isna().any().any():
        raise ValueError("月頻報酬與目標資料不完整或月份不一致")
    realized = target_signals.shift(1)
    valid = realized.notna().any(axis=1)
    if not bool(valid.any()):
        raise ValueError("月頻策略沒有可執行訊號")
    first = pd.Timestamp(realized.index[valid][0])
    if first_realized_month is not None:
        first = max(first, pd.Timestamp(first_realized_month))
    months = realized.index[realized.index >= first]
    base_position = returns.index.get_loc(months[0]) - 1
    if base_position < 0:
        raise ValueError("月頻策略缺少起始基準月")
    base_month = pd.Timestamp(returns.index[base_position])

    equity = 1.0
    weights = pd.Series(0.0, index=columns)
    equity_values: dict[pd.Timestamp, float] = {base_month: equity}
    return_values: dict[pd.Timestamp, float] = {base_month: 0.0}
    turnover_values: dict[pd.Timestamp, float] = {base_month: 0.0}
    cost_values: dict[pd.Timestamp, float] = {base_month: 0.0}
    weight_values: dict[pd.Timestamp, pd.Series] = {base_month: weights.copy()}
    rate = float(cost_bps) / 10_000.0
    for month in months:
        target = realized.loc[month]
        turnover = 0.0
        cost = 0.0
        equity_before = equity
        if target.notna().any():
            target = target.fillna(0.0)
            if bool((target < -1e-12).any()) or not np.isclose(target.sum(), 1.0, atol=1e-10):
                raise ValueError("月頻目標含負權重或加總不等於 1")
            turnover = float((target - weights).abs().sum())
            cost = equity * rate * turnover
            equity -= cost
            weights = target
        month_returns = returns.loc[month]
        gross_return = float((weights * month_returns).sum())
        equity *= 1.0 + gross_return
        if not np.isfinite(equity) or equity <= 0:
            raise ValueError(f"月頻權益無效：{month.date()}")
        denominator = 1.0 + gross_return
        weights = weights.mul(1.0 + month_returns).div(denominator)
        equity_values[pd.Timestamp(month)] = equity
        return_values[pd.Timestamp(month)] = equity / equity_before - 1.0
        turnover_values[pd.Timestamp(month)] = turnover
        cost_values[pd.Timestamp(month)] = cost
        weight_values[pd.Timestamp(month)] = weights.copy()

    equity_series = pd.Series(equity_values, name=name, dtype=float)
    return_series = pd.Series(return_values, name=name, dtype=float)
    turnover_series = pd.Series(turnover_values, name="turnover", dtype=float)
    cost_series = pd.Series(cost_values, name="cost", dtype=float)
    weight_frame = pd.DataFrame.from_dict(weight_values, orient="index").fillna(0.0)
    signal_rows = target_signals.dropna(how="all")
    return BacktestResult(
        name=name,
        equity=equity_series,
        returns=return_series,
        weights=weight_frame,
        turnover=turnover_series,
        costs=cost_series,
        metrics=compute_metrics(
            equity_series, return_series, turnover_series, periods_per_year=12
        ),
        current_target=signal_rows.iloc[-1].fillna(0.0).sort_values(ascending=False),
        diagnostics={
            "cost_bps": float(cost_bps),
            "rebalance_count": int((turnover_series > 0.0).sum()),
            "execution_clock": "month t signal; month t+1 return",
            "periods_per_year": 12,
        },
    )


def _slice_panel(panel: MarketPanel, end: str) -> MarketPanel:
    fields = {key.lower(): value.loc[:end] for key, value in panel.field_map().items()}
    return MarketPanel(metadata=panel.metadata, **fields)


def _slice_metrics(
    result: BacktestResult, start: str, end: str, *, periods_per_year: int = 252
) -> dict[str, float]:
    index = result.equity.loc[start:end].index
    return compute_metrics(
        result.equity.loc[index],
        result.returns.loc[index],
        result.turnover.loc[index],
        periods_per_year=periods_per_year,
    )


def _comparison(
    strategy: BacktestResult,
    benchmark: BacktestResult,
    *,
    nw_lag: int,
    periods_per_year: int,
) -> dict[str, Any]:
    aligned = pd.concat(
        [strategy.returns.rename("strategy"), benchmark.returns.rename("benchmark")], axis=1
    ).dropna()
    active = aligned["strategy"] - aligned["benchmark"]
    return {
        "cagr_difference": strategy.metrics["cagr"] - benchmark.metrics["cagr"],
        "sharpe_difference": strategy.metrics["sharpe"] - benchmark.metrics["sharpe"],
        "drawdown_improvement": (
            strategy.metrics["max_drawdown"] - benchmark.metrics["max_drawdown"]
        ),
        "active_return_newey_west": newey_west_mean_test(
            active, max_lag=nw_lag, periods_per_year=periods_per_year
        ),
        "active_deflated_sharpe": deflated_sharpe_ratio(
            active, trials=V6_GLOBAL_SEARCH_TRIALS, periods_per_year=periods_per_year
        ),
    }


def _rolling_comparison(
    strategy: BacktestResult,
    benchmark: BacktestResult,
    *,
    window: int,
    periods_per_year: int,
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    common = strategy.equity.index.intersection(benchmark.equity.index)
    periods = pd.Series(common.to_period("M"), index=common)
    endpoints = common[periods.ne(periods.shift(-1)).to_numpy()]
    positions = [common.get_loc(end) for end in endpoints]
    for position in positions:
        if not isinstance(position, int) or position < window:
            continue
        dates = common[position - window : position + 1]
        strategy_metrics = compute_metrics(
            strategy.equity.loc[dates],
            strategy.returns.loc[dates],
            strategy.turnover.loc[dates],
            periods_per_year=periods_per_year,
        )
        benchmark_metrics = compute_metrics(
            benchmark.equity.loc[dates],
            benchmark.returns.loc[dates],
            benchmark.turnover.loc[dates],
            periods_per_year=periods_per_year,
        )
        rows.append(
            {
                "end": pd.Timestamp(dates[-1]).strftime("%Y-%m-%d"),
                "cagr_difference": strategy_metrics["cagr"] - benchmark_metrics["cagr"],
            }
        )
    if not rows:
        return {"window": window, "series": [], "summary": {}}
    differences = pd.Series([float(row["cagr_difference"]) for row in rows])
    return {
        "window": window,
        "series": rows,
        "summary": {
            "windows": len(rows),
            "minimum_cagr_edge": 0.001,
            "cagr_win_fraction": float((differences > 0.001).mean()),
            "median_cagr_difference": float(differences.median()),
            "worst_cagr_difference": float(differences.min()),
            "latest_cagr_difference": float(differences.iloc[-1]),
        },
    }


def _period_comparison(
    strategy: BacktestResult,
    spy: BacktestResult,
    matched: BacktestResult,
    start: str,
    end: str,
    *,
    periods_per_year: int,
) -> dict[str, Any]:
    strategy_metrics = _slice_metrics(
        strategy, start, end, periods_per_year=periods_per_year
    )
    spy_metrics = _slice_metrics(spy, start, end, periods_per_year=periods_per_year)
    matched_metrics = _slice_metrics(
        matched, start, end, periods_per_year=periods_per_year
    )
    return {
        "start": start,
        "end": end,
        "strategy_metrics": strategy_metrics,
        "market_metrics": spy_metrics,
        "matched_metrics": matched_metrics,
        "cagr_difference_vs_market": strategy_metrics["cagr"] - spy_metrics["cagr"],
        "cagr_difference_vs_matched": strategy_metrics["cagr"] - matched_metrics["cagr"],
    }


def evaluate_industry_tilt_research(
    panel: MarketPanel,
    industries: pd.DataFrame,
    factors: pd.DataFrame,
    *,
    etf_receipt: dict[str, Any],
    french_receipt: dict[str, Any],
    protocol_sha256: str,
    primary_cost_bps: float = 10.0,
    stress_cost_bps: float = 50.0,
) -> tuple[BacktestResult, pd.DataFrame, dict[str, Any]]:
    """Evaluate all 22 preregistered v6 gates without parameter search."""
    if protocol_sha256 != V6_PROTOCOL_SHA256:
        raise ValueError("v6 協議雜湊與資料下載前凍結版本不同")
    if panel_fingerprint(panel) != V6_ETF_PANEL_SHA256:
        raise ValueError("v6 ETF 面板內容與凍結收據不同")
    if etf_receipt.get("archive_sha256") != V6_ETF_ARCHIVE_SHA256:
        raise ValueError("v6 ETF 封存檔雜湊與凍結收據不同")
    if etf_receipt.get("panel_sha256") != V6_ETF_PANEL_SHA256:
        raise ValueError("v6 ETF manifest 面板雜湊與凍結收據不同")
    if etf_receipt.get("provider_metadata", {}).get("protocol_sha256") != protocol_sha256:
        raise ValueError("v6 ETF 快照未綁定凍結協議")
    if not etf_receipt.get("contract", {}).get("ok", False):
        raise ValueError("v6 ETF 快照資料合約未通過")
    if french_receipt.get("industry", {}).get("sha256") != V6_FRENCH_INDUSTRY_SHA256:
        raise ValueError("v6 French 產業收據雜湊不同")
    if french_receipt.get("factors", {}).get("sha256") != V6_FRENCH_FACTORS_SHA256:
        raise ValueError("v6 French 因子收據雜湊不同")
    if tuple(sorted(panel.tickers)) != tuple(sorted(V6_TICKERS)):
        raise ValueError("v6 ETF 代號與凍結協議不同")
    if panel.start.strftime("%Y-%m-%d") != "1998-12-01" or panel.end.strftime(
        "%Y-%m-%d"
    ) != V6_MAIN_END:
        raise ValueError("v6 ETF 快照期間與凍結協議不同")

    target = industry_momentum_core_tilt_targets(panel.close, industries=V6_INDUSTRIES)
    matched_target = industry_selection_matched_targets(target, industries=V6_INDUSTRIES)
    passive_weights = {"SPY": 0.50, **{ticker: 0.50 / 9.0 for ticker in V6_INDUSTRIES}}
    passive_target = fixed_weight_targets(panel.close, passive_weights)
    spy_target = buy_and_hold_targets(panel.close, "SPY", signal_on=V6_MAIN_START)

    strategy = run_backtest(
        panel, target, name="v6 產業動能核心傾斜", cost_bps=primary_cost_bps, start=V6_MAIN_START
    )
    spy = run_backtest(
        panel, spy_target, name="SPY 買進持有", cost_bps=primary_cost_bps, start=V6_MAIN_START
    )
    matched = run_backtest(
        panel,
        matched_target,
        name="同月權益曝險 matched control",
        cost_bps=primary_cost_bps,
        start=V6_MAIN_START,
    )
    passive = run_backtest(
        panel,
        passive_target,
        name="固定 50% SPY／50% 產業等權",
        cost_bps=primary_cost_bps,
        start=V6_MAIN_START,
    )
    strategy_50 = run_backtest(
        panel, target, name="v6 50bps", cost_bps=stress_cost_bps, start=V6_MAIN_START
    )
    spy_50 = run_backtest(
        panel, spy_target, name="SPY 50bps", cost_bps=stress_cost_bps, start=V6_MAIN_START
    )
    matched_50 = run_backtest(
        panel,
        matched_target,
        name="matched 50bps",
        cost_bps=stress_cost_bps,
        start=V6_MAIN_START,
    )
    main_vs_spy = _comparison(strategy, spy, nw_lag=9, periods_per_year=252)
    main_vs_matched = _comparison(strategy, matched, nw_lag=9, periods_per_year=252)
    main_halves = {
        "first": _period_comparison(
            strategy, spy, matched, "2006-07-31", "2016-07-29", periods_per_year=252
        ),
        "second": _period_comparison(
            strategy, spy, matched, "2016-08-01", "2026-07-31", periods_per_year=252
        ),
    }
    main_rolling_spy = _rolling_comparison(
        strategy, spy, window=1260, periods_per_year=252
    )
    main_rolling_matched = _rolling_comparison(
        strategy, matched, window=1260, periods_per_year=252
    )
    weight_sums = strategy.weights.sum(axis=1)
    weight_integrity = {
        "fully_invested_fraction": float(np.isclose(weight_sums, 1.0, atol=1e-8).mean()),
        "maximum_weight_sum": float(weight_sums.max()),
        "minimum_weight": float(strategy.weights.min().min()),
    }

    early_panel = _slice_panel(panel, V6_EARLY_END)
    early_target = target.loc[:V6_EARLY_END]
    early_matched_target = matched_target.loc[:V6_EARLY_END]
    first_signal = pd.Timestamp(early_target.dropna(how="all").index[0]).strftime("%Y-%m-%d")
    early_spy_target = buy_and_hold_targets(early_panel.close, "SPY", signal_on=first_signal)
    early_strategy = run_backtest(
        early_panel,
        early_target,
        name="v6 早期 ETF",
        cost_bps=primary_cost_bps,
        start=first_signal,
    )
    early_spy = run_backtest(
        early_panel,
        early_spy_target,
        name="早期 SPY",
        cost_bps=primary_cost_bps,
        start=first_signal,
    )
    early_matched = run_backtest(
        early_panel,
        early_matched_target,
        name="早期 matched",
        cost_bps=primary_cost_bps,
        start=first_signal,
    )
    early_strategy_50 = run_backtest(
        early_panel, early_target, name="早期 v6 50bps", cost_bps=stress_cost_bps, start=first_signal
    )
    early_spy_50 = run_backtest(
        early_panel,
        early_spy_target,
        name="早期 SPY 50bps",
        cost_bps=stress_cost_bps,
        start=first_signal,
    )
    early_matched_50 = run_backtest(
        early_panel,
        early_matched_target,
        name="早期 matched 50bps",
        cost_bps=stress_cost_bps,
        start=first_signal,
    )

    monthly_target, monthly_matched_target = monthly_industry_core_tilt_targets(
        industries, factors["RF"]
    )
    monthly_assets = pd.DataFrame(index=industries.index)
    monthly_assets["MKT"] = factors["Mkt-RF"] + factors["RF"]
    monthly_assets[list(FRENCH_INDUSTRIES)] = industries
    monthly_assets["RF"] = factors["RF"]
    first_proxy_realized = pd.Timestamp(monthly_target.shift(1).dropna(how="all").index[0])
    market_signals = pd.DataFrame(0.0, index=industries.index, columns=monthly_target.columns)
    market_signals["MKT"] = 1.0
    proxy_strategy = run_monthly_backtest(
        monthly_assets,
        monthly_target,
        name="v6 1927–2005 產業代理",
        cost_bps=primary_cost_bps,
        first_realized_month=first_proxy_realized,
    )
    proxy_market = run_monthly_backtest(
        monthly_assets,
        market_signals,
        name="French 市場",
        cost_bps=primary_cost_bps,
        first_realized_month=first_proxy_realized,
    )
    proxy_matched = run_monthly_backtest(
        monthly_assets,
        monthly_matched_target,
        name="French matched",
        cost_bps=primary_cost_bps,
        first_realized_month=first_proxy_realized,
    )
    proxy_strategy_50 = run_monthly_backtest(
        monthly_assets,
        monthly_target,
        name="French v6 50bps",
        cost_bps=stress_cost_bps,
        first_realized_month=first_proxy_realized,
    )
    proxy_market_50 = run_monthly_backtest(
        monthly_assets,
        market_signals,
        name="French market 50bps",
        cost_bps=stress_cost_bps,
        first_realized_month=first_proxy_realized,
    )
    proxy_matched_50 = run_monthly_backtest(
        monthly_assets,
        monthly_matched_target,
        name="French matched 50bps",
        cost_bps=stress_cost_bps,
        first_realized_month=first_proxy_realized,
    )
    proxy_vs_market = _comparison(
        proxy_strategy, proxy_market, nw_lag=6, periods_per_year=12
    )
    proxy_vs_matched = _comparison(
        proxy_strategy, proxy_matched, nw_lag=6, periods_per_year=12
    )
    proxy_halves = {
        "first": _period_comparison(
            proxy_strategy,
            proxy_market,
            proxy_matched,
            "1927-01-01",
            "1966-06-30",
            periods_per_year=12,
        ),
        "second": _period_comparison(
            proxy_strategy,
            proxy_market,
            proxy_matched,
            "1966-07-01",
            "2005-12-31",
            periods_per_year=12,
        ),
    }
    proxy_rolling_market = _rolling_comparison(
        proxy_strategy, proxy_market, window=240, periods_per_year=12
    )
    proxy_rolling_matched = _rolling_comparison(
        proxy_strategy, proxy_matched, window=240, periods_per_year=12
    )
    decades: dict[str, Any] = {}
    for year in range(1930, 2000, 10):
        item = _period_comparison(
            proxy_strategy,
            proxy_market,
            proxy_matched,
            f"{year}-01-01",
            f"{year + 9}-12-31",
            periods_per_year=12,
        )
        item["beats_both"] = bool(
            item["cagr_difference_vs_market"] > 0.001
            and item["cagr_difference_vs_matched"] > 0.001
        )
        decades[f"{year}s"] = item
    decade_wins = sum(bool(item["beats_both"]) for item in decades.values())

    gates = {
        "01_main_cagr_beats_spy_and_matched_10bp": bool(
            strategy.metrics["cagr"] > spy.metrics["cagr"] + 0.001
            and strategy.metrics["cagr"] > matched.metrics["cagr"] + 0.001
        ),
        "02_main_sharpe_beats_spy_and_matched": bool(
            strategy.metrics["sharpe"] > spy.metrics["sharpe"]
            and strategy.metrics["sharpe"] > matched.metrics["sharpe"]
        ),
        "03_main_drawdown_improves_spy_5pp_and_not_worse_matched": bool(
            strategy.metrics["max_drawdown"] >= spy.metrics["max_drawdown"] + 0.05
            and strategy.metrics["max_drawdown"] >= matched.metrics["max_drawdown"]
        ),
        "04_main_50bps_cagr_beats_both_10bp": bool(
            strategy_50.metrics["cagr"] > spy_50.metrics["cagr"] + 0.001
            and strategy_50.metrics["cagr"] > matched_50.metrics["cagr"] + 0.001
        ),
        "05_main_both_halves_cagr_beat_both_10bp": all(
            item["cagr_difference_vs_market"] > 0.001
            and item["cagr_difference_vs_matched"] > 0.001
            for item in main_halves.values()
        ),
        "06_main_rolling_wins_60pct_and_positive_medians": bool(
            main_rolling_spy["summary"].get("cagr_win_fraction", 0.0) >= 0.60
            and main_rolling_matched["summary"].get("cagr_win_fraction", 0.0) >= 0.60
            and main_rolling_spy["summary"].get("median_cagr_difference", -1.0) > 0.0
            and main_rolling_matched["summary"].get("median_cagr_difference", -1.0) > 0.0
        ),
        "07_main_newey_west_t_at_least_1_96_vs_both": bool(
            main_vs_spy["active_return_newey_west"]["t_stat"] >= 1.96
            and main_vs_matched["active_return_newey_west"]["t_stat"] >= 1.96
        ),
        "08_main_dsr_probability_95pct_vs_both": bool(
            main_vs_spy["active_deflated_sharpe"]["probability"] >= 0.95
            and main_vs_matched["active_deflated_sharpe"]["probability"] >= 0.95
        ),
        "09_main_weights_fully_invested_95pct_no_leverage_or_short": bool(
            weight_integrity["fully_invested_fraction"] >= 0.95
            and weight_integrity["maximum_weight_sum"] <= 1.0 + 1e-8
            and weight_integrity["minimum_weight"] >= -1e-12
        ),
        "10_early_cagr_beats_spy_and_matched_10bp": bool(
            early_strategy.metrics["cagr"] > early_spy.metrics["cagr"] + 0.001
            and early_strategy.metrics["cagr"] > early_matched.metrics["cagr"] + 0.001
        ),
        "11_early_sharpe_beats_spy_and_matched": bool(
            early_strategy.metrics["sharpe"] > early_spy.metrics["sharpe"]
            and early_strategy.metrics["sharpe"] > early_matched.metrics["sharpe"]
        ),
        "12_early_drawdown_improves_spy_5pp_and_not_worse_matched": bool(
            early_strategy.metrics["max_drawdown"] >= early_spy.metrics["max_drawdown"] + 0.05
            and early_strategy.metrics["max_drawdown"] >= early_matched.metrics["max_drawdown"]
        ),
        "13_early_50bps_cagr_beats_both_10bp": bool(
            early_strategy_50.metrics["cagr"] > early_spy_50.metrics["cagr"] + 0.001
            and early_strategy_50.metrics["cagr"] > early_matched_50.metrics["cagr"] + 0.001
        ),
        "14_proxy_cagr_beats_market_and_matched_10bp": bool(
            proxy_strategy.metrics["cagr"] > proxy_market.metrics["cagr"] + 0.001
            and proxy_strategy.metrics["cagr"] > proxy_matched.metrics["cagr"] + 0.001
        ),
        "15_proxy_sharpe_beats_market_and_matched": bool(
            proxy_strategy.metrics["sharpe"] > proxy_market.metrics["sharpe"]
            and proxy_strategy.metrics["sharpe"] > proxy_matched.metrics["sharpe"]
        ),
        "16_proxy_drawdown_improves_market_5pp_and_not_worse_matched": bool(
            proxy_strategy.metrics["max_drawdown"] >= proxy_market.metrics["max_drawdown"] + 0.05
            and proxy_strategy.metrics["max_drawdown"] >= proxy_matched.metrics["max_drawdown"]
        ),
        "17_proxy_50bps_cagr_beats_both_10bp": bool(
            proxy_strategy_50.metrics["cagr"] > proxy_market_50.metrics["cagr"] + 0.001
            and proxy_strategy_50.metrics["cagr"] > proxy_matched_50.metrics["cagr"] + 0.001
        ),
        "18_proxy_both_halves_cagr_beat_both_10bp": all(
            item["cagr_difference_vs_market"] > 0.001
            and item["cagr_difference_vs_matched"] > 0.001
            for item in proxy_halves.values()
        ),
        "19_proxy_rolling_wins_60pct_and_positive_medians": bool(
            proxy_rolling_market["summary"].get("cagr_win_fraction", 0.0) >= 0.60
            and proxy_rolling_matched["summary"].get("cagr_win_fraction", 0.0) >= 0.60
            and proxy_rolling_market["summary"].get("median_cagr_difference", -1.0) > 0.0
            and proxy_rolling_matched["summary"].get("median_cagr_difference", -1.0) > 0.0
        ),
        "20_proxy_newey_west_t_at_least_1_96_vs_both": bool(
            proxy_vs_market["active_return_newey_west"]["t_stat"] >= 1.96
            and proxy_vs_matched["active_return_newey_west"]["t_stat"] >= 1.96
        ),
        "21_proxy_dsr_probability_95pct_vs_both": bool(
            proxy_vs_market["active_deflated_sharpe"]["probability"] >= 0.95
            and proxy_vs_matched["active_deflated_sharpe"]["probability"] >= 0.95
        ),
        "22_proxy_at_least_5_of_7_decades_beat_both": decade_wins >= 5,
    }
    passed = all(gates.values())
    audit = {
        "schema_version": 1,
        "strategy_name": "v6 產業動能核心傾斜",
        "status": "historical_passed" if passed else "historical_failed",
        "historical_gate_passed": passed,
        "paper_eligible": passed,
        "reference_trade_candidate": False,
        "promotion_effect": "create_isolated_paper_only" if passed else "none",
        "protocol": {
            "path": "docs/V6_INDUSTRY_TILT_PROTOCOL.md",
            "sha256": protocol_sha256,
            "frozen_before_new_data_download_and_first_calculation": True,
            "global_search_trials": V6_GLOBAL_SEARCH_TRIALS,
        },
        "data_receipts": {"etf": etf_receipt, "french": french_receipt},
        "parameters": {
            "core_weight": 0.50,
            "satellite_slots": 3,
            "slot_weight": 1.0 / 6.0,
            "momentum": "t-252 to t-21; proxy compounded t-11 to t-1",
            "trend": "200 sessions; proxy 10 months",
            "primary_cost_bps": primary_cost_bps,
            "stress_cost_bps": stress_cost_bps,
            "leverage": False,
        },
        "main": {
            "period": {"start": V6_MAIN_START, "end": V6_MAIN_END},
            "strategy_metrics": strategy.metrics,
            "benchmark_metrics": {
                "spy": spy.metrics,
                "matched": matched.metrics,
                "passive_50_50": passive.metrics,
            },
            "comparisons": {"spy": main_vs_spy, "matched": main_vs_matched},
            "cost_50bps": {
                "strategy_metrics": strategy_50.metrics,
                "spy_metrics": spy_50.metrics,
                "matched_metrics": matched_50.metrics,
            },
            "fixed_halves": main_halves,
            "rolling_five_year": {
                "spy": main_rolling_spy,
                "matched": main_rolling_matched,
            },
            "weight_integrity": weight_integrity,
            "current_target": {
                str(key): float(value)
                for key, value in strategy.current_target.items()
                if float(value) > 0.0
            },
        },
        "early_etf": {
            "period": {"start": first_signal, "end": V6_EARLY_END},
            "strategy_metrics": early_strategy.metrics,
            "benchmark_metrics": {"spy": early_spy.metrics, "matched": early_matched.metrics},
            "cost_50bps": {
                "strategy_metrics": early_strategy_50.metrics,
                "spy_metrics": early_spy_50.metrics,
                "matched_metrics": early_matched_50.metrics,
            },
        },
        "proxy": {
            "period": {
                "source_start": "1927-01",
                "first_realized": first_proxy_realized.strftime("%Y-%m"),
                "end": "2005-12",
            },
            "strategy_metrics": proxy_strategy.metrics,
            "benchmark_metrics": {
                "market": proxy_market.metrics,
                "matched": proxy_matched.metrics,
            },
            "comparisons": {"market": proxy_vs_market, "matched": proxy_vs_matched},
            "cost_50bps": {
                "strategy_metrics": proxy_strategy_50.metrics,
                "market_metrics": proxy_market_50.metrics,
                "matched_metrics": proxy_matched_50.metrics,
            },
            "fixed_halves": proxy_halves,
            "rolling_twenty_year": {
                "market": proxy_rolling_market,
                "matched": proxy_rolling_matched,
            },
            "decades": decades,
            "decade_wins": decade_wins,
        },
        "gates": gates,
        "passed_gate_count": sum(bool(value) for value in gates.values()),
        "required_gate_count": 22,
        "forward_requirements_if_historical_passes": {
            "sessions": 252,
            "completed_rebalances": 6,
            "same_start_cost_and_selection_matched_control": True,
            "replay_counts": False,
        },
        "interpretation": (
            "The rule and all gates were frozen before the ETF and official French files "
            "were downloaded. A failure is retained without parameter rescue; a pass can "
            "only open an isolated forward paper account, never immediate reference trading."
        ),
    }
    return strategy, target, audit
