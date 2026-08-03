from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pandas as pd

FIELDS = ("Open", "High", "Low", "Close", "Volume")


@dataclass(frozen=True)
class MarketPanel:
    """Adjusted OHLCV matrices sharing the same date index and ticker columns."""

    open: pd.DataFrame
    high: pd.DataFrame
    low: pd.DataFrame
    close: pd.DataFrame
    volume: pd.DataFrame
    metadata: dict[str, Any] = field(default_factory=dict)

    def field_map(self) -> dict[str, pd.DataFrame]:
        return {
            "Open": self.open,
            "High": self.high,
            "Low": self.low,
            "Close": self.close,
            "Volume": self.volume,
        }

    @property
    def tickers(self) -> list[str]:
        return [str(x) for x in self.close.columns]

    @property
    def start(self) -> pd.Timestamp:
        return pd.Timestamp(self.close.index.min())

    @property
    def end(self) -> pd.Timestamp:
        return pd.Timestamp(self.close.index.max())


@dataclass(frozen=True)
class ContractResult:
    ok: bool
    errors: tuple[str, ...]
    warnings: tuple[str, ...]
    stats: dict[str, Any]

    def require(self) -> None:
        if not self.ok:
            raise ValueError("資料契約未通過：" + "；".join(self.errors))


@dataclass(frozen=True)
class BacktestResult:
    name: str
    equity: pd.Series
    returns: pd.Series
    weights: pd.DataFrame
    turnover: pd.Series
    costs: pd.Series
    metrics: dict[str, float]
    current_target: pd.Series
    diagnostics: dict[str, Any] = field(default_factory=dict)
