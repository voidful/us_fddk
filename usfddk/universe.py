from __future__ import annotations

import csv
from dataclasses import dataclass
from importlib.resources import files

ETF_TREND_UNIVERSE = (
    "SPY",  # US large cap
    "QQQ",  # US growth / Nasdaq-100
    "IWM",  # US small cap
    "EFA",  # developed ex-US
    "EEM",  # emerging markets
    "VNQ",  # US REITs
    "TLT",  # long Treasuries
    "IEF",  # intermediate Treasuries
    "GLD",  # gold
    "DBC",  # broad commodities
)

# SHY launched early enough to support a complete 20-year study. BIL only begins
# in 2007 and would silently shorten the requested research window.
DEFENSIVE_ASSET = "SHY"
MARKET_CONTEXT = ("SPY", "^VIX")


@dataclass(frozen=True)
class StockRecord:
    symbol: str
    name: str
    sector: str
    source_weight_pct: float
    as_of: str


def load_stock_watchlist() -> list[StockRecord]:
    """Current large-cap watchlist. It is never treated as point-in-time history."""
    path = files("usfddk").joinpath("resources/us_large_cap_watchlist_v1.csv")
    with path.open("r", encoding="utf-8", newline="") as handle:
        rows = csv.DictReader(handle)
        return [
            StockRecord(
                symbol=row["symbol"],
                name=row["name"],
                sector=row["sector"],
                source_weight_pct=float(row["source_weight_pct"]),
                as_of=row["as_of"],
            )
            for row in rows
        ]


def all_default_tickers() -> list[str]:
    stocks = [x.symbol for x in load_stock_watchlist()]
    return sorted(set(ETF_TREND_UNIVERSE) | {DEFENSIVE_ASSET, *MARKET_CONTEXT, *stocks})
