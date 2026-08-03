from __future__ import annotations

import numpy as np
import pandas as pd

from usfddk.metrics import newey_west_mean_test
from usfddk.validation import (
    block_bootstrap_cagr,
    deflated_sharpe_ratio,
    probabilistic_sharpe_ratio,
    probability_of_backtest_overfitting,
)


def test_newey_west_detects_large_positive_mean():
    values = pd.Series(np.full(600, 0.001), index=pd.bdate_range("2020-01-01", periods=600))
    result = newey_west_mean_test(values)
    assert result["annualized"] > 0.2
    assert result["t_stat"] > 1.96


def test_bootstrap_is_seeded():
    rng = np.random.default_rng(3)
    returns = pd.Series(rng.normal(0.0003, 0.01, 800))
    first = block_bootstrap_cagr(returns, samples=100, seed=9)
    second = block_bootstrap_cagr(returns, samples=100, seed=9)
    assert first == second


def test_probabilistic_and_deflated_sharpe_penalize_thresholds_and_trials():
    rng = np.random.default_rng(11)
    returns = pd.Series(rng.normal(0.0007, 0.01, 5_000))
    psr_zero = probabilistic_sharpe_ratio(returns, benchmark_sharpe=0.0)
    psr_one = probabilistic_sharpe_ratio(returns, benchmark_sharpe=1.0)
    dsr = deflated_sharpe_ratio(returns, trials=6_000)
    assert psr_zero["probability"] > psr_one["probability"]
    assert dsr["expected_max_sharpe"] > 0
    assert dsr["probability"] < psr_zero["probability"]


def test_pbo_flags_inverse_train_test_winners():
    rng = np.random.default_rng(5)
    block = 60
    columns = {}
    for idx in range(4):
        values = []
        for segment in range(10):
            favored = idx == segment % 4
            mean = 0.0015 if favored else -0.0002
            values.extend(rng.normal(mean, 0.004, block))
        columns[f"c{idx}"] = values
    result = probability_of_backtest_overfitting(pd.DataFrame(columns), slices=10)
    assert result["combinations"] == 252
    assert 0.0 <= result["pbo"] <= 1.0
