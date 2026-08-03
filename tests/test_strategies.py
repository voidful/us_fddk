from __future__ import annotations

import numpy as np
import pandas as pd

from usfddk.strategies import (
    _month_end_signal_mask,
    always_invested_relative_growth_targets,
    balanced_trend_satellite_targets,
    confirmed_relative_growth_matched_targets,
    confirmed_relative_growth_states,
    confirmed_relative_growth_targets,
    dual_momentum_targets,
    fixed_weight_targets,
    growth_guard_targets,
    hierarchical_relative_growth_states,
    hierarchical_relative_growth_targets,
    low_turnover_relative_growth_states,
    low_turnover_relative_growth_targets,
    momentum_tilt_targets,
    relative_growth_matched_targets,
    relative_growth_satellite_targets,
    style_rotation_targets,
    three_clock_ensemble_targets,
    trend_confirmed_volatility_guard_targets,
    volatility_guard_targets,
)
from usfddk.universe import ETF_TREND_UNIVERSE


def test_dual_momentum_weights_are_bounded(synthetic_panel):
    targets = dual_momentum_targets(synthetic_panel.close)
    active = targets.dropna(how="all")
    assert len(active) > 8
    assert np.allclose(active.sum(axis=1), 1.0)
    assert (active >= 0).all().all()
    assert (active <= 1.0 + 1e-12).all().all()


def test_momentum_tilt_preserves_broad_pool(synthetic_panel):
    tickers = list(ETF_TREND_UNIVERSE)
    targets = momentum_tilt_targets(synthetic_panel.close, tickers, max_weight=0.2)
    active = targets.dropna(how="all")
    seasoned = active[active.sum(axis=1) > 0]
    assert len(seasoned)
    assert np.allclose(seasoned.sum(axis=1), 1.0)
    assert (seasoned > 0).sum(axis=1).min() == len(tickers)
    assert seasoned.max().max() <= 0.2 + 1e-9


def test_balanced_trend_satellite_is_fully_invested_and_has_fixed_qqq_floor(synthetic_panel):
    targets = balanced_trend_satellite_targets(synthetic_panel.close)
    active = targets.dropna(how="all")
    assert len(active) > 8
    assert np.allclose(active.sum(axis=1), 1.0)
    assert (active >= 0).all().all()
    assert (active["QQQ"] >= 0.25 - 1e-12).all()
    assert (active["SHY"] <= 0.75 + 1e-12).all()


def test_growth_guard_has_declared_growth_floor_and_full_investment(synthetic_panel):
    targets = growth_guard_targets(synthetic_panel.close)
    active = targets.dropna(how="all")
    assert np.allclose(active.sum(axis=1), 1.0)
    assert (active["QQQ"] >= 0.80 - 1e-12).all()
    assert (active >= 0).all().all()


def test_volatility_guard_is_unlevered_and_moves_to_defensive_asset(synthetic_panel):
    targets = volatility_guard_targets(synthetic_panel.close)
    active = targets.dropna(how="all")
    assert len(active) > 0
    assert np.allclose(active.sum(axis=1), 1.0)
    assert bool(active["QQQ"].between(0.0, 1.0).all())
    assert bool(active["SHY"].between(0.0, 1.0).all())
    assert bool((active["SHY"] > 0).any())


def test_trend_confirmed_guard_is_bounded_and_reconstructs_regime_state():
    index = pd.bdate_range("2022-01-03", "2024-12-31")
    # A long decline followed by a recovery creates two confirmed regime changes.
    first_returns = np.where(np.arange(len(index) // 2) % 2 == 0, -0.025, 0.01)
    first = 100.0 * np.cumprod(1.0 + first_returns)
    second_returns = np.where(
        np.arange(len(index) - len(first)) % 2 == 0, 0.003, 0.005
    )
    second = first[-1] * np.cumprod(1.0 + second_returns)
    qqq = np.concatenate([first, second])
    close = pd.DataFrame({"QQQ": qqq, "SHY": 100.0}, index=index)

    targets = trend_confirmed_volatility_guard_targets(
        close,
        momentum_window=63,
        volatility_window=21,
        confirmation_months=2,
    )
    active = targets.dropna(how="all")
    rerun = trend_confirmed_volatility_guard_targets(
        close,
        momentum_window=63,
        volatility_window=21,
        confirmation_months=2,
    ).dropna(how="all")

    assert active.equals(rerun)
    assert np.allclose(active.sum(axis=1), 1.0)
    assert bool(active["QQQ"].between(0.0, 1.0).all())
    assert bool((active["SHY"] > 0.0).any())
    assert active.iloc[-1]["QQQ"] == 1.0


def test_fixed_weight_benchmark_rebalances_only_at_completed_month_end(synthetic_panel):
    targets = fixed_weight_targets(synthetic_panel.close, {"QQQ": 0.9, "SHY": 0.1})
    active = targets.dropna(how="all")
    assert len(active) > 8
    assert np.allclose(active["QQQ"], 0.9)
    assert np.allclose(active["SHY"], 0.1)
    assert np.allclose(active.sum(axis=1), 1.0)


def test_incomplete_final_month_is_not_a_signal():
    index = pd.bdate_range("2024-01-02", "2024-02-15")
    mask = _month_end_signal_mask(index)
    assert bool(mask.loc[pd.Timestamp("2024-01-31")])
    assert not bool(mask.iloc[-1])


def test_relative_growth_satellite_and_matched_control_have_exact_exposure():
    index = pd.bdate_range("2020-01-02", "2022-12-30")
    steps = np.arange(len(index), dtype=float)
    close = pd.DataFrame(
        {
            "SPY": 100.0 * np.exp(0.0003 * steps),
            "QQQ": 100.0 * np.exp(0.0007 * steps),
            "SHY": 100.0,
        },
        index=index,
    )
    target = relative_growth_satellite_targets(close).dropna(how="all")
    matched = relative_growth_matched_targets(
        relative_growth_satellite_targets(close)
    ).dropna(how="all")

    assert len(target) > 10
    assert np.allclose(target.sum(axis=1), 1.0)
    assert (target >= 0.0).all().all()
    assert np.allclose(target["SPY"], 0.50)
    assert np.allclose(target["QQQ"], 0.50)
    assert np.allclose(target["SHY"], 0.0)
    assert np.allclose(matched["SPY"], 1.0)
    assert np.allclose(matched[["QQQ", "SHY"]], 0.0)


def test_relative_growth_missing_or_tied_signal_fails_defensively():
    index = pd.bdate_range("2020-01-02", "2022-12-30")
    steps = np.arange(len(index), dtype=float)
    same = 100.0 * np.exp(0.0003 * steps)
    close = pd.DataFrame({"SPY": same, "QQQ": same, "SHY": 100.0}, index=index)
    target = relative_growth_satellite_targets(close).dropna(how="all")

    assert len(target) > 10
    assert np.allclose(target["SPY"], 0.50)
    assert np.allclose(target["QQQ"], 0.0)
    assert np.allclose(target["SHY"], 0.50)


def test_always_invested_relative_growth_keeps_exact_full_equity_exposure():
    index = pd.bdate_range("2020-01-02", "2022-12-30")
    steps = np.arange(len(index), dtype=float)
    close = pd.DataFrame(
        {
            "SPY": 100.0 * np.exp(0.0003 * steps),
            "QQQ": 100.0 * np.exp(0.0007 * steps),
        },
        index=index,
    )
    active = always_invested_relative_growth_targets(close).dropna(how="all")

    assert len(active) > 10
    assert np.allclose(active.sum(axis=1), 1.0)
    assert (active >= 0.0).all().all()
    assert np.allclose(active["SPY"], 0.50)
    assert np.allclose(active["QQQ"], 0.50)


def test_always_invested_relative_growth_sends_tied_signal_to_spy():
    index = pd.bdate_range("2020-01-02", "2022-12-30")
    steps = np.arange(len(index), dtype=float)
    same = 100.0 * np.exp(0.0003 * steps)
    close = pd.DataFrame({"SPY": same, "QQQ": same}, index=index)
    active = always_invested_relative_growth_targets(close).dropna(how="all")

    assert len(active) > 10
    assert np.allclose(active["SPY"], 1.0)
    assert np.allclose(active["QQQ"], 0.0)


def test_low_turnover_relative_growth_emits_only_initial_and_state_changes():
    index = pd.bdate_range("2020-01-02", "2022-12-30")
    steps = np.arange(len(index), dtype=float)
    qqq_returns = np.where((steps // 90) % 2 == 0, 0.004, -0.003)
    close = pd.DataFrame(
        {
            "SPY": 100.0 * np.exp(0.0003 * steps),
            "QQQ": 100.0 * np.exp(np.cumsum(qqq_returns)),
        },
        index=index,
    )
    start = pd.Timestamp("2021-01-04")
    states = low_turnover_relative_growth_states(
        close, long_lookback=63, skip_recent=5, trend_window=40
    )
    target = low_turnover_relative_growth_targets(
        close,
        initial_signal_before=start,
        long_lookback=63,
        skip_recent=5,
        trend_window=40,
    ).dropna(how="all")

    initial_day = states.index[states.index < start][-1]
    relevant_states = states.loc[initial_day:]
    expected_days = relevant_states.index[
        relevant_states.ne(relevant_states.shift(1)).to_numpy()
    ]
    observed_states = target["QQQ"] > 0.0

    assert target.index.equals(expected_days)
    assert len(target) < len(relevant_states)
    assert np.allclose(target.sum(axis=1), 1.0)
    assert set(target["SPY"].unique()) <= {0.60, 1.0}
    assert set(target["QQQ"].unique()) <= {0.0, 0.40}
    assert bool(observed_states.ne(observed_states.shift(1)).all())


def test_low_turnover_tied_growth_stays_in_core_without_monthly_rebalancing():
    index = pd.bdate_range("2020-01-02", "2022-12-30")
    steps = np.arange(len(index), dtype=float)
    same = 100.0 * np.exp(0.0003 * steps)
    close = pd.DataFrame({"SPY": same, "QQQ": same}, index=index)
    target = low_turnover_relative_growth_targets(
        close, initial_signal_before="2021-01-04"
    ).dropna(how="all")

    assert len(target) == 1
    assert np.isclose(target.iloc[0]["SPY"], 1.0)
    assert np.isclose(target.iloc[0]["QQQ"], 0.0)


def test_hierarchical_tied_growth_falls_through_to_core():
    index = pd.bdate_range("2020-01-02", "2022-12-30")
    steps = np.arange(len(index), dtype=float)
    same = 100.0 * np.exp(0.0003 * steps)
    close = pd.DataFrame(
        {"SPY": same, "QQQ": same, "SHY": np.full(len(index), 100.0)},
        index=index,
    )

    states = hierarchical_relative_growth_states(close)
    targets = hierarchical_relative_growth_targets(
        close, initial_signal_before="2021-01-04"
    ).dropna(how="all")

    assert set(states.loc[states.index >= index[199]].dropna().unique()) == {"core"}
    assert len(targets) == 1
    assert np.isclose(targets.iloc[0]["SPY"], 1.0)
    assert np.isclose(targets.iloc[0][["QQQ", "SHY"]].sum(), 0.0)


def test_hierarchical_uses_defense_when_core_is_below_trend():
    index = pd.bdate_range("2020-01-02", "2022-12-30")
    steps = np.arange(len(index), dtype=float)
    close = pd.DataFrame(
        {
            "SPY": 100.0 * np.exp(-0.0008 * steps),
            "QQQ": 100.0 * np.exp(-0.0012 * steps),
            "SHY": np.full(len(index), 100.0),
        },
        index=index,
    )
    targets = hierarchical_relative_growth_targets(
        close, initial_signal_before="2021-01-04"
    ).dropna(how="all")

    assert len(targets) == 1
    assert np.isclose(targets.iloc[0]["SPY"], 0.60)
    assert np.isclose(targets.iloc[0]["SHY"], 0.40)
    assert np.isclose(targets.iloc[0]["QQQ"], 0.0)


def test_hierarchical_emits_only_three_state_changes():
    index = pd.bdate_range("2020-01-02", "2023-12-29")
    steps = np.arange(len(index), dtype=float)
    qqq_return = np.where((steps // 100) % 3 == 0, 0.004, -0.002)
    spy_return = np.where((steps // 160) % 2 == 0, 0.0005, -0.001)
    close = pd.DataFrame(
        {
            "SPY": 100.0 * np.exp(np.cumsum(spy_return)),
            "QQQ": 100.0 * np.exp(np.cumsum(qqq_return)),
            "SHY": np.full(len(index), 100.0),
        },
        index=index,
    )
    start = pd.Timestamp("2021-01-04")
    states = hierarchical_relative_growth_states(
        close, long_lookback=63, skip_recent=5, trend_window=40
    )
    target = hierarchical_relative_growth_targets(
        close,
        initial_signal_before=start,
        long_lookback=63,
        skip_recent=5,
        trend_window=40,
    ).dropna(how="all")
    initial_day = states.index[states.index < start][-1]
    relevant = states.loc[initial_day:]
    expected_days = relevant.index[
        relevant.ne(relevant.shift(1)).fillna(True).to_numpy(dtype=bool)
    ]

    assert target.index.equals(expected_days)
    assert np.allclose(target.sum(axis=1), 1.0)
    assert (target >= 0.0).all().all()
    assert set(relevant.unique()) == {"growth", "core", "defense"}


def test_confirmed_relative_growth_waits_for_confirmation_and_matches_exposure():
    index = pd.bdate_range("2020-01-02", "2023-12-29")
    steps = np.arange(len(index), dtype=float)
    growth_returns = np.where((steps // 85) % 2 == 0, 0.004, -0.003)
    core_returns = np.where((steps // 170) % 2 == 0, 0.0004, -0.0012)
    close = pd.DataFrame(
        {
            "SPY": 100.0 * np.exp(np.cumsum(core_returns)),
            "QQQ": 100.0 * np.exp(np.cumsum(growth_returns)),
            "SHY": 100.0 * np.exp(0.00005 * steps),
        },
        index=index,
    )
    states = confirmed_relative_growth_states(
        close,
        confirmation_months=2,
        long_lookback=63,
        skip_recent=5,
        trend_window=40,
    )
    start = pd.Timestamp("2021-01-04")
    target = confirmed_relative_growth_targets(
        close,
        initial_signal_before=start,
        confirmation_months=2,
        long_lookback=63,
        skip_recent=5,
        trend_window=40,
    ).dropna(how="all")
    matched = confirmed_relative_growth_matched_targets(
        close,
        initial_signal_before=start,
        confirmation_months=2,
        long_lookback=63,
        skip_recent=5,
        trend_window=40,
    ).dropna(how="all")

    initial_day = states.index[states.index < start][-1]
    relevant = states.loc[initial_day:]
    expected_days = relevant.index[
        relevant.ne(relevant.shift(1)).fillna(True).to_numpy(dtype=bool)
    ]

    assert target.index.equals(expected_days)
    assert matched.index.equals(expected_days)
    assert np.allclose(target.sum(axis=1), 1.0)
    assert np.allclose(matched.sum(axis=1), 1.0)
    assert (target >= 0.0).all().all()
    assert (matched >= 0.0).all().all()
    assert np.allclose(matched["QQQ"], 0.0)
    growth_days = relevant.loc[target.index] == "growth"
    defense_days = relevant.loc[target.index] == "defense"
    assert bool(growth_days.any())
    assert bool(defense_days.any())
    assert np.allclose(target.loc[growth_days, ["SPY", "QQQ"]], [0.40, 0.60])
    assert np.allclose(target.loc[defense_days, ["SPY", "SHY"]], [0.70, 0.30])
    assert np.allclose(matched.loc[growth_days, "SPY"], 1.0)
    assert np.allclose(
        matched.loc[defense_days, ["SPY", "SHY"]], [0.70, 0.30]
    )


def test_style_rotation_keeps_empty_slot_in_defensive_asset():
    index = pd.bdate_range("2020-01-02", "2021-04-30")
    steps = np.arange(len(index), dtype=float)
    close = pd.DataFrame(
        {
            "IWF": 100.0 * np.exp(0.0010 * steps),
            "IWD": 100.0 * np.exp(-0.0004 * steps),
            "IJR": 100.0 * np.exp(-0.0008 * steps),
            "SHY": 100.0,
        },
        index=index,
    )

    active = style_rotation_targets(close).dropna(how="all")
    latest = active.iloc[-1]

    assert np.isclose(latest["IWF"], 0.5)
    assert np.isclose(latest["SHY"], 0.5)
    assert np.isclose(latest[["IWD", "IJR"]].sum(), 0.0)
    assert np.isclose(latest.sum(), 1.0)


def test_style_rotation_uses_two_equal_slots_without_leverage():
    index = pd.bdate_range("2020-01-02", "2021-04-30")
    steps = np.arange(len(index), dtype=float)
    close = pd.DataFrame(
        {
            "IWF": 100.0 * np.exp(0.0010 * steps),
            "IWD": 100.0 * np.exp(0.0007 * steps),
            "IJR": 100.0 * np.exp(-0.0008 * steps),
            "SHY": 100.0,
        },
        index=index,
    )

    active = style_rotation_targets(close).dropna(how="all")
    latest = active.iloc[-1]

    assert np.isclose(latest["IWF"], 0.5)
    assert np.isclose(latest["IWD"], 0.5)
    assert np.isclose(latest[["IJR", "SHY"]].sum(), 0.0)
    assert np.isclose(latest.sum(), 1.0)


def test_three_clock_ensemble_is_exact_equal_sleeve_average(synthetic_panel):
    volatility = volatility_guard_targets(synthetic_panel.close)
    trend = trend_confirmed_volatility_guard_targets(synthetic_panel.close)
    ensemble = three_clock_ensemble_targets(synthetic_panel.close)
    active = ensemble.dropna(how="all")

    expected_qqq = (
        1.0 + volatility.loc[active.index, "QQQ"] + trend.loc[active.index, "QQQ"]
    ) / 3.0

    assert np.allclose(active["QQQ"], expected_qqq)
    assert np.allclose(active.sum(axis=1), 1.0)
    assert bool(active["QQQ"].between(1.0 / 3.0, 1.0).all())
    assert bool(active["SHY"].between(0.0, 2.0 / 3.0).all())
