"""Post-hoc forward diagnostic for the SEC insider research-only feed.

This module deliberately stops at an event study.  It does not create a
portfolio, infer a point-in-time universe, or authorize Paper.  Prices are
loaded from an explicit long CSV so the input snapshot and its hash remain
visible in the receipt.
"""

from __future__ import annotations

import math
from collections.abc import Iterable
from datetime import date
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

FORWARD_DIAGNOSTIC_SCHEMA_VERSION = 1
FORWARD_HORIZONS = (5, 10, 20)
FORWARD_PRIMARY_HORIZON = 20
FORWARD_ROUND_TRIP_COST_BPS = 20.0
FORWARD_BOOTSTRAP_SAMPLES = 2_000
FORWARD_BOOTSTRAP_BLOCK = 8
FORWARD_BOOTSTRAP_SEED = 20260811
PRICE_COLUMNS = ("symbol", "date", "adj_open", "adj_close")


def load_long_total_return_prices(path: str | Path) -> pd.DataFrame:
    """Load and validate a long-format adjusted OHLC price snapshot.

    Required columns are ``symbol``, ``date``, ``adj_open`` and ``adj_close``.
    Missing values are retained as unavailable observations and never filled.
    """

    frame = pd.read_csv(path, dtype={"symbol": str, "date": str})
    missing = set(PRICE_COLUMNS) - set(frame.columns)
    if missing:
        raise ValueError(f"price snapshot 欄位不完整：{sorted(missing)}")
    frame = frame.loc[:, list(PRICE_COLUMNS)].copy()
    frame["symbol"] = frame["symbol"].str.strip().str.upper()
    frame["date"] = pd.to_datetime(frame["date"], errors="coerce").dt.date
    for column in ("adj_open", "adj_close"):
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    if frame["symbol"].eq("").any() or frame["date"].isna().any():
        raise ValueError("price snapshot 有空白 symbol 或無效日期")
    if frame.duplicated(["symbol", "date"]).any():
        raise ValueError("price snapshot 有重複 symbol/date，拒絕猜測")
    invalid = (
        ~np.isfinite(frame["adj_open"])
        | ~np.isfinite(frame["adj_close"])
        | (frame["adj_open"] <= 0.0)
        | (frame["adj_close"] <= 0.0)
    )
    if invalid.any():
        raise ValueError("price snapshot 有非有限或非正 adjusted 價格")
    return frame.sort_values(["symbol", "date"]).reset_index(drop=True)


def _price_lookup(
    prices: pd.DataFrame,
) -> dict[str, tuple[dict[date, int], np.ndarray, np.ndarray]]:
    lookup: dict[str, tuple[dict[date, int], np.ndarray, np.ndarray]] = {}
    for symbol, rows in prices.groupby("symbol", sort=False):
        rows = rows.sort_values("date").reset_index(drop=True)
        dates = rows["date"].tolist()
        lookup[str(symbol)] = (
            {day: index for index, day in enumerate(dates)},
            rows["adj_open"].to_numpy(dtype=float),
            rows["adj_close"].to_numpy(dtype=float),
        )
    return lookup


def _forward_return(
    prices: dict[str, tuple[dict[date, int], np.ndarray, np.ndarray]],
    *,
    symbol: str,
    entry_date: date,
    horizon: int,
    cost: float,
) -> float | None:
    entry_positions = prices.get(symbol)
    if entry_positions is None:
        return None
    date_positions, adj_open, adj_close = entry_positions
    entry_position = date_positions.get(entry_date)
    if entry_position is None:
        return None
    exit_position = entry_position + horizon - 1
    if exit_position >= len(adj_close):
        return None
    entry = float(adj_open[entry_position])
    exit = float(adj_close[exit_position])
    return exit / entry - 1.0 - cost


def _bootstrap(values: Iterable[float]) -> dict[str, float | None]:
    array = np.asarray(list(values), dtype=float)
    array = array[np.isfinite(array)]
    if len(array) < FORWARD_BOOTSTRAP_BLOCK * 2:
        return {
            "low": None,
            "median": None,
            "high": None,
            "p_mean_le_zero": None,
        }
    rng = np.random.default_rng(FORWARD_BOOTSTRAP_SEED)
    starts_count = len(array) - FORWARD_BOOTSTRAP_BLOCK + 1
    blocks = int(math.ceil(len(array) / FORWARD_BOOTSTRAP_BLOCK))
    means = np.empty(FORWARD_BOOTSTRAP_SAMPLES, dtype=float)
    for sample in range(FORWARD_BOOTSTRAP_SAMPLES):
        starts = rng.integers(0, starts_count, size=blocks)
        resampled = np.concatenate(
            [array[start : start + FORWARD_BOOTSTRAP_BLOCK] for start in starts]
        )[: len(array)]
        means[sample] = float(resampled.mean())
    low, median, high = np.quantile(means, [0.025, 0.5, 0.975])
    return {
        "low": float(low),
        "median": float(median),
        "high": float(high),
        "p_mean_le_zero": float((means <= 0.0).mean()),
    }


def compute_forward_event_diagnostic(
    candidates: list[dict[str, Any]],
    prices: pd.DataFrame,
    *,
    as_of: date,
    horizons: tuple[int, ...] = FORWARD_HORIZONS,
    baseline_symbol: str = "QQQ",
    round_trip_cost_bps: float = FORWARD_ROUND_TRIP_COST_BPS,
) -> dict[str, Any]:
    """Compare candidate event windows with same-clock QQQ windows.

    Each row is an event observation, not a portfolio holding.  Repeated
    issuer signals remain separate and overlapping observations are reported;
    no capital allocation or de-duplication is invented after seeing returns.
    """

    if tuple(horizons) != FORWARD_HORIZONS:
        raise ValueError("forward diagnostic horizons are frozen at 5/10/20 sessions")
    if round_trip_cost_bps != FORWARD_ROUND_TRIP_COST_BPS:
        raise ValueError("forward diagnostic cost is frozen at 20 bps round trip")
    price_lookup = _price_lookup(prices)
    if baseline_symbol not in price_lookup:
        raise ValueError(f"price snapshot 缺少 baseline：{baseline_symbol}")
    cost = round_trip_cost_bps / 10_000.0
    normalized: list[dict[str, Any]] = []
    for candidate in candidates:
        available = date.fromisoformat(str(candidate["available_session"]))
        if available > as_of:
            continue
        normalized.append(
            {
                "ticker": str(candidate["ticker"]).upper(),
                "available_session": available,
            }
        )

    output: dict[str, Any] = {
        "candidate_rows": len(normalized),
        "candidate_issuers": len({row["ticker"] for row in normalized}),
        "baseline_symbol": baseline_symbol,
        "round_trip_cost_bps": round_trip_cost_bps,
        "horizons": {},
    }
    for horizon in horizons:
        observations: list[tuple[float, float, float]] = []
        missing_candidate = 0
        missing_baseline = 0
        for row in normalized:
            candidate_return = _forward_return(
                price_lookup,
                symbol=row["ticker"],
                entry_date=row["available_session"],
                horizon=horizon,
                cost=cost,
            )
            baseline_return = _forward_return(
                price_lookup,
                symbol=baseline_symbol,
                entry_date=row["available_session"],
                horizon=horizon,
                cost=cost,
            )
            if candidate_return is None:
                missing_candidate += 1
                continue
            if baseline_return is None:
                missing_baseline += 1
                continue
            observations.append(
                (candidate_return, baseline_return, candidate_return - baseline_return)
            )
        candidate_values = np.asarray([row[0] for row in observations], dtype=float)
        baseline_values = np.asarray([row[1] for row in observations], dtype=float)
        excess_values = np.asarray([row[2] for row in observations], dtype=float)
        if len(observations):
            summary: dict[str, Any] = {
                "complete_rows": len(observations),
                "missing_candidate_rows": missing_candidate,
                "missing_baseline_rows": missing_baseline,
                "candidate_mean_net_return": float(candidate_values.mean()),
                "candidate_median_net_return": float(np.median(candidate_values)),
                "baseline_mean_net_return": float(baseline_values.mean()),
                "baseline_median_net_return": float(np.median(baseline_values)),
                "mean_excess_vs_baseline": float(excess_values.mean()),
                "median_excess_vs_baseline": float(np.median(excess_values)),
                "win_fraction_vs_baseline": float((excess_values > 0.0).mean()),
                "moving_block_bootstrap_excess": _bootstrap(excess_values),
            }
        else:
            summary = {
                "complete_rows": 0,
                "missing_candidate_rows": missing_candidate,
                "missing_baseline_rows": missing_baseline,
                "candidate_mean_net_return": None,
                "candidate_median_net_return": None,
                "baseline_mean_net_return": None,
                "baseline_median_net_return": None,
                "mean_excess_vs_baseline": None,
                "median_excess_vs_baseline": None,
                "win_fraction_vs_baseline": None,
                "moving_block_bootstrap_excess": _bootstrap([]),
            }
        output["horizons"][str(horizon)] = summary
    return output
