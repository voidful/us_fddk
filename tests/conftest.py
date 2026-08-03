from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from usfddk.models import MarketPanel


@pytest.fixture
def synthetic_panel() -> MarketPanel:
    index = pd.bdate_range("2022-01-03", periods=420)
    tickers = ["SPY", "QQQ", "IWM", "EFA", "EEM", "VNQ", "TLT", "IEF", "GLD", "DBC", "SHY", "^VIX"]
    rng = np.random.default_rng(7)
    prices = {}
    for idx, ticker in enumerate(tickers):
        drift = 0.00015 + idx * 0.000015
        if ticker == "SHY":
            drift = 0.00008
        if ticker == "^VIX":
            drift = 0.0
        returns = drift + rng.normal(0, 0.006 if ticker != "^VIX" else 0.025, len(index))
        base = 20.0 if ticker == "^VIX" else 100.0
        prices[ticker] = base * np.exp(np.cumsum(returns))
    close = pd.DataFrame(prices, index=index)
    open_ = close * (1 + rng.normal(0, 0.001, close.shape))
    high = np.maximum(open_, close) * 1.004
    low = np.minimum(open_, close) * 0.996
    volume = pd.DataFrame(1_000_000.0, index=index, columns=tickers)
    return MarketPanel(open_, high, low, close, volume, {"provider": "synthetic"})
