from __future__ import annotations

import numpy as np
import pandas as pd

from usfddk.engine import run_backtest
from usfddk.models import MarketPanel


def test_signal_executes_next_open_without_lookahead():
    index = pd.bdate_range("2024-01-02", periods=4)
    close = pd.DataFrame({"AAA": [100.0, 120.0, 132.0, 132.0]}, index=index)
    open_ = pd.DataFrame({"AAA": [100.0, 110.0, 120.0, 132.0]}, index=index)
    high = np.maximum(open_, close)
    low = np.minimum(open_, close)
    volume = pd.DataFrame({"AAA": 1_000.0}, index=index)
    panel = MarketPanel(open_, high, low, close, volume)
    targets = pd.DataFrame(np.nan, index=index, columns=["AAA"])
    targets.loc[index[0], "AAA"] = 1.0
    result = run_backtest(panel, targets, name="test", cost_bps=0)
    assert result.equity.loc[index[0]] == 1.0
    assert result.equity.loc[index[1]] == 120.0 / 110.0
    assert result.diagnostics["rebalance_count"] == 1


def test_cost_is_deducted_on_turnover(synthetic_panel):
    index = synthetic_panel.close.index
    targets = pd.DataFrame(np.nan, index=index, columns=["SPY"])
    targets.loc[index[0], "SPY"] = 1.0
    free = run_backtest(synthetic_panel, targets, name="free", cost_bps=0)
    costly = run_backtest(synthetic_panel, targets, name="costly", cost_bps=25)
    assert costly.equity.iloc[-1] < free.equity.iloc[-1]
    assert costly.costs.sum() > 0
