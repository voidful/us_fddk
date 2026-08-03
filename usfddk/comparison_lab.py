from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from usfddk.data import panel_fingerprint
from usfddk.managed_futures_capital_efficiency import (
    _month_end_prices,
    _return_frame_from_prices,
    _rolling_comparison,
    _run_monthly_portfolio,
)
from usfddk.metrics import newey_west_mean_test
from usfddk.models import BacktestResult, MarketPanel
from usfddk.universe import load_stock_watchlist

EXPANDED_COMPARISON_SCHEMA_VERSION = 1
EXPANDED_COMPARISON_START = "2006-07-31"
EXPANDED_COMPARISON_END = "2026-07-31"
EXPANDED_COMPARISON_COST_BPS = 10.0
EXPANDED_COMPARISON_STOCK_COUNT = 12
V25_VANGUARD_PANEL_SHA256 = (
    "6cf44e6347cdd2910605e0c31e9e72bd76544c4cf2cd8923bce7a0847c1755fe"
)
MAIN_RESEARCH_PANEL_SHA256 = (
    "6a7ca6b83b1570007424daa46b0ff4e8fb4a655d39298a0f4f6d74c3b7ea3a66"
)


_BASELINE_SPECS: tuple[dict[str, Any], ...] = (
    {
        "key": "candidate",
        "label": "最新策略實作",
        "detail": "80% VUG／20% GLD，每月重新平衡",
        "role": "candidate",
        "weights": {"VUG": 0.8, "GLD": 0.2},
        "rebalance_monthly": True,
    },
    {
        "key": "SPY",
        "label": "SPY",
        "detail": "美國大型股廣泛市場",
        "role": "market",
        "weights": {"SPY": 1.0},
        "rebalance_monthly": False,
    },
    {
        "key": "QQQ",
        "label": "QQQ",
        "detail": "Nasdaq-100 大型非金融股",
        "role": "growth_style",
        "weights": {"QQQ": 1.0},
        "rebalance_monthly": False,
    },
    {
        "key": "VUG",
        "label": "VUG",
        "detail": "美國大型成長股",
        "role": "growth_style",
        "weights": {"VUG": 1.0},
        "rebalance_monthly": False,
    },
    {
        "key": "GLD",
        "label": "GLD",
        "detail": "實物黃金價格參考",
        "role": "diversifier",
        "weights": {"GLD": 1.0},
        "rebalance_monthly": False,
    },
    {
        "key": "60_SPY_40_IEF",
        "label": "60% SPY／40% IEF",
        "detail": "傳統股債平衡配置",
        "role": "balanced_allocation",
        "weights": {"SPY": 0.6, "IEF": 0.4},
        "rebalance_monthly": True,
    },
    {
        "key": "80_SPY_20_GLD",
        "label": "80% SPY／20% GLD",
        "detail": "相同黃金比重、改用廣泛市場股票",
        "role": "equity_selection_control",
        "weights": {"SPY": 0.8, "GLD": 0.2},
        "rebalance_monthly": True,
    },
    {
        "key": "80_VUG_20_SHY",
        "label": "80% VUG／20% SHY",
        "detail": "相同股票持倉比率控制",
        "role": "exposure_control",
        "weights": {"VUG": 0.8, "SHY": 0.2},
        "rebalance_monthly": True,
    },
    {
        "key": "80_VUG_20_GLD_DRIFT",
        "label": "80% VUG／20% GLD 漂移",
        "detail": "起點買入後不再重新平衡",
        "role": "rebalance_control",
        "weights": {"VUG": 0.8, "GLD": 0.2},
        "rebalance_monthly": False,
    },
)


def _sha256_file(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _excess_sharpe(returns: pd.Series, risk_free: pd.Series) -> float:
    aligned = pd.concat(
        [returns.rename("asset"), risk_free.rename("risk_free")], axis=1, join="inner"
    ).dropna()
    excess = aligned["asset"] - aligned["risk_free"]
    standard_deviation = float(excess.std(ddof=1))
    if standard_deviation <= 0:
        return 0.0
    return float(excess.mean() / standard_deviation * np.sqrt(12.0))


def _market_relationships(returns: pd.Series, spy_returns: pd.Series) -> dict[str, float]:
    aligned = pd.concat(
        [returns.rename("asset"), spy_returns.rename("SPY")], axis=1, join="inner"
    ).dropna()
    spy_variance = float(aligned["SPY"].var(ddof=1))
    beta = (
        float(aligned[["asset", "SPY"]].cov().loc["asset", "SPY"] / spy_variance)
        if spy_variance > 0
        else 0.0
    )
    up = aligned[aligned["SPY"] > 0]
    down = aligned[aligned["SPY"] < 0]
    up_capture = float(up["asset"].mean() / up["SPY"].mean()) if not up.empty else 0.0
    down_capture = (
        float(down["asset"].mean() / down["SPY"].mean()) if not down.empty else 0.0
    )
    return {
        "beta_to_spy": beta,
        "correlation_to_spy": float(aligned["asset"].corr(aligned["SPY"])),
        "up_capture_vs_spy": up_capture,
        "down_capture_vs_spy": down_capture,
    }


def _clean_metrics(result: BacktestResult) -> dict[str, float]:
    return {
        key: float(result.metrics[key])
        for key in (
            "total_return",
            "cagr",
            "volatility",
            "sharpe",
            "sortino",
            "max_drawdown",
            "calmar",
            "turnover",
            "worst_month",
        )
    }


def _comparison_row(
    result: BacktestResult,
    *,
    candidate: BacktestResult,
    spy_returns: pd.Series,
    risk_free_returns: pd.Series,
    is_candidate: bool,
) -> dict[str, Any]:
    asset_returns = result.returns.iloc[1:]
    row: dict[str, Any] = {
        "metrics": _clean_metrics(result),
        "excess_sharpe_vs_shy": _excess_sharpe(asset_returns, risk_free_returns),
        **_market_relationships(asset_returns, spy_returns),
    }
    if is_candidate:
        row.update(
            {
                "candidate_cagr_difference": None,
                "candidate_rolling_five_year_win_fraction": None,
                "candidate_active_return_annualized": None,
                "candidate_active_newey_west_t": None,
            }
        )
        return row

    rolling = _rolling_comparison(candidate, result)["summary"]
    active = candidate.returns.iloc[1:] - result.returns.iloc[1:]
    newey_west = newey_west_mean_test(active, max_lag=6, periods_per_year=12)
    row.update(
        {
            "candidate_cagr_difference": float(
                candidate.metrics["cagr"] - result.metrics["cagr"]
            ),
            "candidate_rolling_five_year_win_fraction": float(
                rolling["cagr_win_fraction"]
            ),
            "candidate_active_return_annualized": float(newey_west["annualized"]),
            "candidate_active_newey_west_t": float(newey_west["t_stat"]),
        }
    )
    return row


def _latest_market_context(v25_panel: MarketPanel, stock_panel: MarketPanel) -> dict[str, Any]:
    v25_close = v25_panel.close.loc[:EXPANDED_COMPARISON_END, ["VUG", "GLD", "SPY"]]
    v25_returns = v25_close.pct_change(fill_method=None)
    spy = v25_close["SPY"]
    vug = v25_close["VUG"]
    gold = v25_close["GLD"]
    spy_realized_volatility = v25_returns["SPY"].rolling(21).std(ddof=1) * np.sqrt(252.0)
    current_realized_volatility = float(spy_realized_volatility.iloc[-1])
    five_year_volatility = spy_realized_volatility.dropna().tail(252 * 5)

    watchlist = load_stock_watchlist()
    stock_symbols = [record.symbol for record in watchlist]
    stock_close = stock_panel.close.loc[:EXPANDED_COMPARISON_END, stock_symbols]
    latest = stock_close.iloc[-1]
    eligible = latest.notna() & stock_close.rolling(252).count().iloc[-1].ge(252)
    latest = latest[eligible]
    ma50 = stock_close.rolling(50).mean().iloc[-1][eligible]
    ma200 = stock_close.rolling(200).mean().iloc[-1][eligible]
    high252 = stock_close.rolling(252).max().iloc[-1][eligible]

    vix = stock_panel.close.loc[:EXPANDED_COMPARISON_END, "^VIX"].dropna()
    vix_five_year = vix.tail(252 * 5)
    return {
        "as_of": EXPANDED_COMPARISON_END,
        "context_only_not_a_trading_signal": True,
        "spy_return_12m": float(spy.pct_change(252).iloc[-1]),
        "spy_distance_from_50d_average": float(spy.iloc[-1] / spy.rolling(50).mean().iloc[-1] - 1.0),
        "spy_distance_from_200d_average": float(
            spy.iloc[-1] / spy.rolling(200).mean().iloc[-1] - 1.0
        ),
        "spy_realized_volatility_21d": current_realized_volatility,
        "spy_realized_volatility_21d_five_year_percentile": float(
            (five_year_volatility <= current_realized_volatility).mean()
        ),
        "vug_return_12m": float(vug.pct_change(252).iloc[-1]),
        "vug_relative_return_vs_spy_12m": float(
            vug.pct_change(252).iloc[-1] - spy.pct_change(252).iloc[-1]
        ),
        "vug_distance_from_200d_average": float(
            vug.iloc[-1] / vug.rolling(200).mean().iloc[-1] - 1.0
        ),
        "gold_return_12m": float(gold.pct_change(252).iloc[-1]),
        "gold_distance_from_200d_average": float(
            gold.iloc[-1] / gold.rolling(200).mean().iloc[-1] - 1.0
        ),
        "vug_gold_correlation_63d": float(
            v25_returns["VUG"].tail(63).corr(v25_returns["GLD"].tail(63))
        ),
        "vug_gold_correlation_252d": float(
            v25_returns["VUG"].tail(252).corr(v25_returns["GLD"].tail(252))
        ),
        "vix_close": float(vix.iloc[-1]),
        "vix_five_year_percentile": float((vix_five_year <= vix.iloc[-1]).mean()),
        "current_watchlist_count": int(len(latest)),
        "current_watchlist_above_50d_fraction": float((latest > ma50).mean()),
        "current_watchlist_above_200d_fraction": float((latest > ma200).mean()),
        "current_watchlist_within_5pct_of_52w_high_fraction": float(
            (latest >= high252 * 0.95).mean()
        ),
        "breadth_survivorship_bias_warning": True,
    }


def build_v25_expanded_comparison(
    v25_panel: MarketPanel,
    stock_panel: MarketPanel,
    *,
    v25_snapshot_path: str | Path,
    stock_snapshot_path: str | Path,
) -> dict[str, Any]:
    """Build post-entry comparisons without modifying the frozen v25 gate."""
    v25_fingerprint = panel_fingerprint(v25_panel)
    stock_fingerprint = panel_fingerprint(stock_panel)
    if v25_fingerprint != V25_VANGUARD_PANEL_SHA256:
        raise ValueError("v25 Vanguard 比較面板雜湊不符")
    if stock_fingerprint != MAIN_RESEARCH_PANEL_SHA256:
        raise ValueError("大型股比較面板雜湊不符")

    watchlist = load_stock_watchlist()
    duplicate_share_classes = {"GOOG"}
    full_history: list[Any] = []
    for record in watchlist:
        if record.symbol in duplicate_share_classes or record.symbol not in stock_panel.close:
            continue
        series = stock_panel.close.loc[
            EXPANDED_COMPARISON_START:EXPANDED_COMPARISON_END, record.symbol
        ]
        monthly = series.groupby(series.index.to_period("M"), sort=True).tail(1)
        if len(monthly) == 241 and not monthly.isna().any():
            full_history.append(record)
    selected_stocks = sorted(
        full_history, key=lambda record: (-record.source_weight_pct, record.symbol)
    )[:EXPANDED_COMPARISON_STOCK_COUNT]
    if len(selected_stocks) != EXPANDED_COMPARISON_STOCK_COUNT:
        raise ValueError("具完整 20 年歷史的大型股不足")

    v25_month_end = _month_end_prices(
        v25_panel,
        ["VUG", "GLD", "SPY", "SHY"],
        start=EXPANDED_COMPARISON_START,
        end=EXPANDED_COMPARISON_END,
    )
    extra_tickers = ["QQQ", "IEF", *(record.symbol for record in selected_stocks)]
    extra_month_end = _month_end_prices(
        stock_panel,
        extra_tickers,
        start=EXPANDED_COMPARISON_START,
        end=EXPANDED_COMPARISON_END,
    )
    prices = pd.concat([v25_month_end, extra_month_end], axis=1)
    if prices.columns.duplicated().any() or prices.isna().any(axis=None):
        raise ValueError("擴充比較月末價格重複或缺值")
    monthly_returns = _return_frame_from_prices(prices)

    results: dict[str, BacktestResult] = {}
    for spec in _BASELINE_SPECS:
        results[spec["key"]] = _run_monthly_portfolio(
            monthly_returns,
            spec["weights"],
            name=spec["label"],
            start_equity_date=EXPANDED_COMPARISON_START,
            cost_bps=EXPANDED_COMPARISON_COST_BPS,
            rebalance_monthly=spec["rebalance_monthly"],
        )
    candidate = results["candidate"]
    spy_returns = monthly_returns["SPY"]
    risk_free_returns = monthly_returns["SHY"]
    baseline_rows = []
    for spec in _BASELINE_SPECS:
        baseline_rows.append(
            {
                key: value
                for key, value in spec.items()
                if key not in {"weights", "rebalance_monthly"}
            }
            | {
                "weights": spec["weights"],
                "rebalance_monthly": bool(spec["rebalance_monthly"]),
                **_comparison_row(
                    results[spec["key"]],
                    candidate=candidate,
                    spy_returns=spy_returns,
                    risk_free_returns=risk_free_returns,
                    is_candidate=spec["key"] == "candidate",
                ),
            }
        )

    stock_rows = []
    for record in selected_stocks:
        result = _run_monthly_portfolio(
            monthly_returns,
            {record.symbol: 1.0},
            name=record.symbol,
            start_equity_date=EXPANDED_COMPARISON_START,
            cost_bps=EXPANDED_COMPARISON_COST_BPS,
            rebalance_monthly=False,
        )
        stock_rows.append(
            {
                "symbol": record.symbol,
                "name": record.name,
                "sector": record.sector,
                "source_weight_pct": float(record.source_weight_pct),
                **_comparison_row(
                    result,
                    candidate=candidate,
                    spy_returns=spy_returns,
                    risk_free_returns=risk_free_returns,
                    is_candidate=False,
                ),
            }
        )

    return {
        "schema_version": EXPANDED_COMPARISON_SCHEMA_VERSION,
        "used_for_frozen_entry_gate": False,
        "changes_strategy_or_paper_rules": False,
        "period": {
            "start_equity_date": EXPANDED_COMPARISON_START,
            "first_return_month_end": monthly_returns.index[0].strftime("%Y-%m-%d"),
            "end": EXPANDED_COMPARISON_END,
            "months": int(len(monthly_returns)),
        },
        "methodology": {
            "return_source": "adjusted OHLCV total-return proxy from frozen Yahoo Finance snapshots",
            "cost_bps": EXPANDED_COMPARISON_COST_BPS,
            "sharpe_display": "excess monthly return over SHY, annualized",
            "rolling_window_months": 60,
            "stock_selection": (
                "current watchlist ranked by source weight; full 240-month history required; "
                "duplicate Alphabet share class removed; first 12 retained"
            ),
            "stock_selection_is_point_in_time": False,
            "stock_table_has_survivorship_bias": True,
            "fundamental_metrics_excluded_without_point_in_time_history": True,
        },
        "source_snapshots": {
            "v25_vanguard": {
                "panel_sha256": v25_fingerprint,
                "archive_sha256": _sha256_file(v25_snapshot_path),
            },
            "main_research": {
                "panel_sha256": stock_fingerprint,
                "archive_sha256": _sha256_file(stock_snapshot_path),
            },
        },
        "formal_baselines": baseline_rows,
        "individual_stock_diagnostics": {
            "watchlist_as_of": sorted({record.as_of for record in watchlist})[0],
            "watchlist_size": len(watchlist),
            "full_history_eligible_count": len(full_history),
            "displayed_count": len(stock_rows),
            "survivorship_bias_warning": True,
            "stocks": stock_rows,
        },
        "market_context": _latest_market_context(v25_panel, stock_panel),
        "official_product_sources": {
            "VUG": "https://investor.vanguard.com/investment-products/etfs/profile/vug",
            "SPY": "https://www.ssga.com/us/en/individual/etfs/state-street-spdr-sp-500-etf-trust-spy",
            "QQQ": "https://www.invesco.com/us/financial-products/etfs/product-detail?productId=QQQ&ticker=QQQ",
            "GLD": "https://www.ssga.com/us/en/individual/etfs/spdr-gold-shares-gld",
            "IEF": "https://www.ishares.com/us/products/239456/IEF",
        },
    }
