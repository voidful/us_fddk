from __future__ import annotations

import numpy as np
import pandas as pd

from usfddk.universe import DEFENSIVE_ASSET, ETF_TREND_UNIVERSE, StockRecord


def _month_end_signal_mask(index: pd.DatetimeIndex) -> pd.Series:
    periods = pd.Series(index.to_period("M"), index=index)
    mask = periods.ne(periods.shift(-1)).fillna(True)
    if len(index):
        # The final row of an in-progress month is not a month-end signal. This matters
        # for forward paper trading, where a mid-month snapshot must not rebalance early.
        last = pd.Timestamp(index[-1]).normalize()
        try:
            import exchange_calendars as xcals

            calendar = xcals.get_calendar("XNYS")
            session = calendar.date_to_session(last, direction="previous")
            next_session = calendar.next_session(session)
            mask.iloc[-1] = pd.Timestamp(next_session).month != last.month
        except Exception:
            mask.iloc[-1] = (last + pd.offsets.BDay()).month != last.month
    return mask


def _week_end_signal_mask(index: pd.DatetimeIndex) -> pd.Series:
    periods = pd.Series(index.to_period("W-FRI"), index=index)
    mask = periods.ne(periods.shift(-1)).fillna(True)
    if len(index):
        last = pd.Timestamp(index[-1]).normalize()
        try:
            import exchange_calendars as xcals

            calendar = xcals.get_calendar("XNYS")
            session = calendar.date_to_session(last, direction="previous")
            next_session = pd.Timestamp(calendar.next_session(session)).tz_localize(None)
            mask.iloc[-1] = next_session.to_period("W-FRI") != last.to_period("W-FRI")
        except Exception:
            next_day = last + pd.offsets.BDay()
            mask.iloc[-1] = next_day.to_period("W-FRI") != last.to_period("W-FRI")
    return mask


def buy_and_hold_targets(
    close: pd.DataFrame, ticker: str, *, signal_on: str | None = None
) -> pd.DataFrame:
    if ticker not in close.columns:
        raise ValueError(f"缺少 benchmark {ticker}")
    targets = pd.DataFrame(np.nan, index=close.index, columns=[ticker])
    available = close[ticker].dropna().index
    if signal_on is not None:
        available = available[available >= pd.Timestamp(signal_on)]
    if len(available):
        targets.loc[available[0], ticker] = 1.0
    return targets


def fixed_weight_targets(
    close: pd.DataFrame,
    weights: dict[str, float],
    *,
    signal_on: str | None = None,
) -> pd.DataFrame:
    """Rebalance a transparent passive allocation at each completed month end."""
    if not weights:
        raise ValueError("固定配置至少需要一個標的")
    normalized = {str(ticker): float(weight) for ticker, weight in weights.items()}
    missing = set(normalized) - set(close.columns)
    if missing:
        raise ValueError("固定配置缺少行情：" + ", ".join(sorted(missing)))
    if any(not np.isfinite(weight) or weight < 0 for weight in normalized.values()):
        raise ValueError("固定配置權重必須是非負有限值")
    if not np.isclose(sum(normalized.values()), 1.0, atol=1e-10):
        raise ValueError("固定配置權重加總必須等於 1")

    targets = pd.DataFrame(np.nan, index=close.index, columns=list(normalized))
    mask = _month_end_signal_mask(close.index)
    if signal_on is not None:
        mask &= close.index >= pd.Timestamp(signal_on)
    for day in close.index[mask]:
        if close.loc[day, list(normalized)].notna().all():
            targets.loc[day] = pd.Series(normalized)
    return targets


def diversifier_relative_strength_targets(
    close: pd.DataFrame,
    *,
    equity: str,
    equity_weight: float,
    diversifiers: tuple[str, ...] = ("IEF", "GLD", "SHY"),
    selected_count: int = 2,
    selected_weight: float = 0.25,
    long_lookback: int = 252,
    skip_recent: int = 21,
    signal_on: str | None = None,
) -> pd.DataFrame:
    """Monthly 12-1 relative-strength selection for the frozen v19/v20 rule.

    Every valid completed month end keeps the equity sleeve and assigns equal,
    fixed slots to the strongest diversifiers. Missing lookback data fails closed
    for the whole month; ties are resolved by ticker so results are deterministic.
    """
    if not diversifiers or len(set(diversifiers)) != len(diversifiers):
        raise ValueError("分散器代號不可空白或重複")
    if selected_count < 1 or selected_count > len(diversifiers):
        raise ValueError("分散器選取數量超出候選池")
    if long_lookback <= skip_recent or skip_recent < 0:
        raise ValueError("分散器動能回顧窗必須大於跳過區間")
    if equity_weight < 0.0 or selected_weight <= 0.0:
        raise ValueError("策略權重必須是非負值")
    if not np.isclose(equity_weight + selected_count * selected_weight, 1.0, atol=1e-10):
        raise ValueError("股票與分散器權重加總必須等於 1")

    columns = [equity, *diversifiers]
    missing = set(columns) - set(close.columns)
    if missing:
        raise ValueError("缺少分散器輪替行情：" + ", ".join(sorted(missing)))

    targets = pd.DataFrame(np.nan, index=close.index, columns=columns)
    scores = (
        close[list(diversifiers)]
        .shift(skip_recent)
        .div(close[list(diversifiers)].shift(long_lookback))
        .sub(1.0)
    )
    month_end = _month_end_signal_mask(close.index)
    if signal_on is not None:
        month_end &= close.index >= pd.Timestamp(signal_on)

    for day in close.index[month_end]:
        row_scores = scores.loc[day].replace([np.inf, -np.inf], np.nan)
        if row_scores.isna().any() or pd.isna(close.loc[day, equity]):
            continue
        selected = sorted(
            diversifiers,
            key=lambda ticker: (-float(row_scores[ticker]), ticker),
        )[:selected_count]
        row = pd.Series(0.0, index=columns)
        row.loc[equity] = equity_weight
        row.loc[selected] = selected_weight
        targets.loc[day] = row
    return targets


def fixed_weight_weekly_targets(
    close: pd.DataFrame,
    weights: dict[str, float],
    *,
    signal_on: str | None = None,
) -> pd.DataFrame:
    """Rebalance a transparent passive allocation after each completed trading week."""
    if not weights:
        raise ValueError("固定週配置至少需要一個標的")
    normalized = {str(ticker): float(weight) for ticker, weight in weights.items()}
    missing = set(normalized) - set(close.columns)
    if missing:
        raise ValueError("固定週配置缺少行情：" + ", ".join(sorted(missing)))
    if any(not np.isfinite(weight) or weight < 0 for weight in normalized.values()):
        raise ValueError("固定週配置權重必須是非負有限值")
    if not np.isclose(sum(normalized.values()), 1.0, atol=1e-10):
        raise ValueError("固定週配置權重加總必須等於 1")

    targets = pd.DataFrame(np.nan, index=close.index, columns=list(normalized))
    mask = _week_end_signal_mask(close.index)
    if signal_on is not None:
        mask &= close.index >= pd.Timestamp(signal_on)
    for day in close.index[mask]:
        if close.loc[day, list(normalized)].notna().all():
            targets.loc[day] = pd.Series(normalized)
    return targets


def industry_momentum_core_tilt_targets(
    close: pd.DataFrame,
    *,
    industries: tuple[str, ...] = (
        "XLB",
        "XLE",
        "XLF",
        "XLI",
        "XLK",
        "XLP",
        "XLU",
        "XLV",
        "XLY",
    ),
    core: str = "SPY",
    defensive: str = "SHY",
    slots: int = 3,
    long_lookback: int = 252,
    skip_recent: int = 21,
    trend_window: int = 200,
) -> pd.DataFrame:
    """Frozen v6 core-plus-industry momentum allocation.

    Half of the portfolio remains in the broad-market core.  Three fixed
    one-sixth slots select industries by 12-1 momentum when they also beat the
    defensive asset and their 200-session average.  Empty slots stay defensive.
    """
    if len(set(industries)) != len(industries) or not industries:
        raise ValueError("產業代號不可空白或重複")
    if slots < 1 or slots > len(industries):
        raise ValueError("產業槽位數必須介於 1 與產業數之間")
    if long_lookback <= skip_recent or skip_recent < 0:
        raise ValueError("產業動能回顧窗必須大於跳過區間")
    required = {*industries, core, defensive}
    missing = required - set(close.columns)
    if missing:
        raise ValueError("缺少產業策略行情：" + ", ".join(sorted(missing)))

    columns = [core, *industries, defensive]
    targets = pd.DataFrame(np.nan, index=close.index, columns=columns)
    momentum = close[columns].shift(skip_recent).div(close[columns].shift(long_lookback)).sub(1.0)
    trend = (
        close[list(industries)]
        > close[list(industries)].rolling(trend_window, min_periods=trend_window).mean()
    )
    month_end = _month_end_signal_mask(close.index)
    slot_weight = 1.0 / 6.0

    for day in close.index[month_end]:
        defensive_score = float(momentum.loc[day, defensive])
        scores = momentum.loc[day, list(industries)].replace([np.inf, -np.inf], np.nan)
        if not np.isfinite(defensive_score) or scores.isna().any():
            continue
        eligible = [
            ticker
            for ticker in industries
            if bool(trend.loc[day, ticker]) and float(scores[ticker]) > defensive_score
        ]
        selected = sorted(eligible, key=lambda ticker: (-float(scores[ticker]), ticker))[:slots]
        row = pd.Series(0.0, index=columns)
        row.loc[core] = 0.50
        row.loc[selected] = slot_weight
        row.loc[defensive] = 0.50 - slot_weight * len(selected)
        targets.loc[day] = row
    return targets


def industry_selection_matched_targets(
    strategy_targets: pd.DataFrame,
    *,
    industries: tuple[str, ...] = (
        "XLB",
        "XLE",
        "XLF",
        "XLI",
        "XLK",
        "XLP",
        "XLU",
        "XLV",
        "XLY",
    ),
    core: str = "SPY",
    defensive: str = "SHY",
) -> pd.DataFrame:
    """Match v6's monthly total equity exposure without copying its selection."""
    required = {*industries, core, defensive}
    missing = required - set(strategy_targets.columns)
    if missing:
        raise ValueError("產業對照缺少目標欄位：" + ", ".join(sorted(missing)))
    matched = pd.DataFrame(
        np.nan, index=strategy_targets.index, columns=[core, *industries, defensive]
    )
    for day, source in strategy_targets.dropna(how="all").iterrows():
        selected = int((source.loc[list(industries)] > 0.0).sum())
        row = pd.Series(0.0, index=matched.columns)
        row.loc[core] = 0.50
        if selected:
            row.loc[list(industries)] = (selected / 6.0) / len(industries)
        row.loc[defensive] = 0.50 - selected / 6.0
        matched.loc[day] = row
    return matched


def relative_growth_satellite_targets(
    close: pd.DataFrame,
    *,
    core: str = "SPY",
    growth: str = "QQQ",
    defensive: str = "SHY",
    long_lookback: int = 252,
    skip_recent: int = 21,
    trend_window: int = 200,
) -> pd.DataFrame:
    """Frozen v7 permanent-core relative-growth satellite allocation.

    At each completed month end, half remains in the broad-market core. The
    other half holds growth only when its 12-1 momentum is strictly above the
    core and growth is strictly above its 200-session simple moving average.
    Missing or tied observations fail defensively.
    """
    if long_lookback <= skip_recent or skip_recent < 0:
        raise ValueError("相對成長動能回顧窗必須大於跳過區間")
    if trend_window < 2:
        raise ValueError("相對成長趨勢窗至少需要 2 個交易日")
    required = {core, growth, defensive}
    missing = required - set(close.columns)
    if missing:
        raise ValueError("缺少相對成長策略行情：" + ", ".join(sorted(missing)))

    columns = [core, growth, defensive]
    targets = pd.DataFrame(np.nan, index=close.index, columns=columns)
    momentum = (
        close[[core, growth]]
        .shift(skip_recent)
        .div(close[[core, growth]].shift(long_lookback))
        .sub(1.0)
    )
    growth_trend = (
        close[growth] > close[growth].rolling(trend_window, min_periods=trend_window).mean()
    )
    month_end = _month_end_signal_mask(close.index)

    for day in close.index[month_end]:
        scores = momentum.loc[day].replace([np.inf, -np.inf], np.nan)
        if scores.isna().any() or pd.isna(growth_trend.loc[day]):
            continue
        risk_on = bool(float(scores[growth]) > float(scores[core]) and bool(growth_trend.loc[day]))
        row = pd.Series(0.0, index=columns)
        row.loc[core] = 0.50
        row.loc[growth if risk_on else defensive] = 0.50
        targets.loc[day] = row
    return targets


def relative_growth_matched_targets(
    strategy_targets: pd.DataFrame,
    *,
    core: str = "SPY",
    growth: str = "QQQ",
    defensive: str = "SHY",
) -> pd.DataFrame:
    """Match v7's monthly total equity exposure without selecting growth."""
    required = {core, growth, defensive}
    missing = required - set(strategy_targets.columns)
    if missing:
        raise ValueError("相對成長對照缺少目標欄位：" + ", ".join(sorted(missing)))
    matched = pd.DataFrame(np.nan, index=strategy_targets.index, columns=[core, growth, defensive])
    for day, source in strategy_targets.dropna(how="all").iterrows():
        row = pd.Series(0.0, index=matched.columns)
        row.loc[core] = 1.0 if float(source.loc[growth]) > 0.0 else 0.50
        row.loc[defensive] = 0.0 if float(source.loc[growth]) > 0.0 else 0.50
        matched.loc[day] = row
    return matched


def always_invested_relative_growth_targets(
    close: pd.DataFrame,
    *,
    core: str = "SPY",
    growth: str = "QQQ",
    long_lookback: int = 252,
    skip_recent: int = 21,
    trend_window: int = 200,
) -> pd.DataFrame:
    """Frozen v8 all-equity relative-growth tilt.

    Half is permanently invested in the core. The second half tilts to growth
    only when growth has stronger 12-1 momentum and remains above its long-term
    trend; otherwise it also remains in the core. This keeps the strategy and
    SPY benchmark at the same 100% equity exposure.
    """
    if long_lookback <= skip_recent or skip_recent < 0:
        raise ValueError("永遠持股動能回顧窗必須大於跳過區間")
    if trend_window < 2:
        raise ValueError("永遠持股趨勢窗至少需要 2 個交易日")
    required = {core, growth}
    missing = required - set(close.columns)
    if missing:
        raise ValueError("缺少永遠持股策略行情：" + ", ".join(sorted(missing)))

    columns = [core, growth]
    targets = pd.DataFrame(np.nan, index=close.index, columns=columns)
    momentum = close[columns].shift(skip_recent).div(close[columns].shift(long_lookback)).sub(1.0)
    growth_trend = (
        close[growth] > close[growth].rolling(trend_window, min_periods=trend_window).mean()
    )
    month_end = _month_end_signal_mask(close.index)

    for day in close.index[month_end]:
        scores = momentum.loc[day].replace([np.inf, -np.inf], np.nan)
        if scores.isna().any() or pd.isna(growth_trend.loc[day]):
            continue
        risk_on = bool(float(scores[growth]) > float(scores[core]) and bool(growth_trend.loc[day]))
        row = pd.Series(0.0, index=columns)
        row.loc[core] = 0.50 if risk_on else 1.0
        row.loc[growth] = 0.50 if risk_on else 0.0
        targets.loc[day] = row
    return targets


def low_turnover_relative_growth_states(
    close: pd.DataFrame,
    *,
    core: str = "SPY",
    growth: str = "QQQ",
    long_lookback: int = 252,
    skip_recent: int = 21,
    trend_window: int = 200,
) -> pd.Series:
    """Return the frozen v9 risk state at each valid completed month end."""
    if long_lookback <= skip_recent or skip_recent < 0:
        raise ValueError("低換手動能回顧窗必須大於跳過區間")
    if trend_window < 2:
        raise ValueError("低換手趨勢窗至少需要 2 個交易日")
    required = {core, growth}
    missing = required - set(close.columns)
    if missing:
        raise ValueError("缺少低換手策略行情：" + ", ".join(sorted(missing)))

    columns = [core, growth]
    momentum = close[columns].shift(skip_recent).div(close[columns].shift(long_lookback)).sub(1.0)
    growth_sma = close[growth].rolling(trend_window, min_periods=trend_window).mean()
    month_end = _month_end_signal_mask(close.index)
    states: dict[pd.Timestamp, bool] = {}
    for day in close.index[month_end]:
        scores = momentum.loc[day].replace([np.inf, -np.inf], np.nan)
        trend_value = growth_sma.loc[day]
        current_growth = close.loc[day, growth]
        if scores.isna().any() or pd.isna(trend_value) or pd.isna(current_growth):
            continue
        states[pd.Timestamp(day)] = bool(
            float(scores[growth]) > float(scores[core])
            and float(current_growth) > float(trend_value)
        )
    return pd.Series(states, dtype=bool, name="risk_on")


def low_turnover_relative_growth_targets(
    close: pd.DataFrame,
    *,
    core: str = "SPY",
    growth: str = "QQQ",
    core_weight_when_risk_on: float = 0.60,
    initial_signal_before: str | pd.Timestamp | None = None,
    long_lookback: int = 252,
    skip_recent: int = 21,
    trend_window: int = 200,
) -> pd.DataFrame:
    """Frozen v9 allocation, emitting orders only when the monthly state changes.

    ``initial_signal_before`` selects the last valid completed month end strictly
    before a formal evaluation start. That row is always emitted so the backtest
    and a newly opened Paper account have an explicit initial allocation.
    """
    if not 0.0 < core_weight_when_risk_on < 1.0:
        raise ValueError("風險開啟核心權重必須介於 0 與 1 之間")
    states = low_turnover_relative_growth_states(
        close,
        core=core,
        growth=growth,
        long_lookback=long_lookback,
        skip_recent=skip_recent,
        trend_window=trend_window,
    )
    targets = pd.DataFrame(np.nan, index=close.index, columns=[core, growth])
    if states.empty:
        return targets

    if initial_signal_before is None:
        initial_day = pd.Timestamp(states.index[0])
    else:
        eligible = states.index[states.index < pd.Timestamp(initial_signal_before)]
        if not len(eligible):
            raise ValueError("正式期以前沒有有效的完整月末初始訊號")
        initial_day = pd.Timestamp(eligible[-1])

    growth_weight = 1.0 - float(core_weight_when_risk_on)
    prior_state: bool | None = None
    for day, risk_on_value in states.loc[initial_day:].items():
        risk_on = bool(risk_on_value)
        if prior_state is not None and risk_on == prior_state:
            continue
        row = pd.Series(0.0, index=targets.columns)
        row.loc[core] = core_weight_when_risk_on if risk_on else 1.0
        row.loc[growth] = growth_weight if risk_on else 0.0
        targets.loc[day] = row
        prior_state = risk_on
    return targets


def hierarchical_relative_growth_states(
    close: pd.DataFrame,
    *,
    core: str = "SPY",
    growth: str = "QQQ",
    long_lookback: int = 252,
    skip_recent: int = 21,
    trend_window: int = 200,
) -> pd.Series:
    """Return the frozen v10-v12 growth/core/defense state at month ends."""
    if long_lookback <= skip_recent or skip_recent < 0:
        raise ValueError("階層式動能回顧窗必須大於跳過區間")
    if trend_window < 2:
        raise ValueError("階層式趨勢窗至少需要 2 個交易日")
    required = {core, growth}
    missing = required - set(close.columns)
    if missing:
        raise ValueError("缺少階層式策略行情：" + ", ".join(sorted(missing)))

    momentum = (
        close[[core, growth]]
        .shift(skip_recent)
        .div(close[[core, growth]].shift(long_lookback))
        .sub(1.0)
    )
    moving_average = close[[core, growth]].rolling(trend_window, min_periods=trend_window).mean()
    month_end = _month_end_signal_mask(close.index)
    states: dict[pd.Timestamp, str] = {}
    for day in close.index[month_end]:
        scores = momentum.loc[day].replace([np.inf, -np.inf], np.nan)
        current = close.loc[day, [core, growth]].replace([np.inf, -np.inf], np.nan)
        averages = moving_average.loc[day].replace([np.inf, -np.inf], np.nan)
        growth_is_on = bool(
            scores.notna().all()
            and current[[growth]].notna().all()
            and averages[[growth]].notna().all()
            and float(scores[growth]) > float(scores[core])
            and float(current[growth]) > float(averages[growth])
        )
        if growth_is_on:
            state = "growth"
        else:
            core_is_on = bool(
                current[[core]].notna().all()
                and averages[[core]].notna().all()
                and float(current[core]) > float(averages[core])
            )
            state = "core" if core_is_on else "defense"
        states[pd.Timestamp(day)] = state
    return pd.Series(states, dtype="string", name="state")


def hierarchical_relative_growth_targets(
    close: pd.DataFrame,
    *,
    core: str = "SPY",
    growth: str = "QQQ",
    defensive: str = "SHY",
    permanent_core_weight: float = 0.60,
    initial_signal_before: str | pd.Timestamp | None = None,
    long_lookback: int = 252,
    skip_recent: int = 21,
    trend_window: int = 200,
) -> pd.DataFrame:
    """Emit an initial target and then only frozen v12 three-state changes."""
    if not 0.0 < permanent_core_weight < 1.0:
        raise ValueError("永久核心權重必須介於 0 與 1 之間")
    required = {core, growth, defensive}
    missing = required - set(close.columns)
    if missing:
        raise ValueError("缺少階層式策略行情：" + ", ".join(sorted(missing)))
    states = hierarchical_relative_growth_states(
        close,
        core=core,
        growth=growth,
        long_lookback=long_lookback,
        skip_recent=skip_recent,
        trend_window=trend_window,
    )
    columns = list(dict.fromkeys([core, growth, defensive]))
    targets = pd.DataFrame(np.nan, index=close.index, columns=columns)
    if states.empty:
        return targets

    if initial_signal_before is None:
        initial_day = pd.Timestamp(states.index[0])
    else:
        eligible = states.index[states.index < pd.Timestamp(initial_signal_before)]
        if not len(eligible):
            raise ValueError("正式期以前沒有階層式策略的完整月末初始訊號")
        initial_day = pd.Timestamp(eligible[-1])

    satellite_weight = 1.0 - float(permanent_core_weight)
    prior_state: str | None = None
    for day, state_value in states.loc[initial_day:].items():
        state = str(state_value)
        if prior_state is not None and state == prior_state:
            continue
        row = pd.Series(0.0, index=columns)
        row.loc[core] = permanent_core_weight
        if state == "growth":
            row.loc[growth] += satellite_weight
        elif state == "core":
            row.loc[core] += satellite_weight
        elif state == "defense":
            row.loc[defensive] += satellite_weight
        else:
            raise ValueError(f"未知階層式狀態：{state}")
        targets.loc[day] = row
        prior_state = state
    return targets


def confirmed_relative_growth_states(
    close: pd.DataFrame,
    *,
    core: str = "SPY",
    growth: str = "QQQ",
    confirmation_months: int = 2,
    long_lookback: int = 252,
    skip_recent: int = 21,
    trend_window: int = 200,
) -> pd.Series:
    """Return the frozen v13 growth/core/defense state at completed month ends.

    The relative-growth boolean must agree for ``confirmation_months`` consecutive
    completed month ends before it can change.  Once growth is off, the core's own
    long trend decides between the fully invested core state and partial defense.
    No state is emitted before the first confirmation, so an evaluation cannot
    silently treat one unconfirmed observation as a valid initial allocation.
    """
    if confirmation_months < 1:
        raise ValueError("相對成長確認月至少需要一個月")
    required = {core, growth}
    missing = required - set(close.columns)
    if missing:
        raise ValueError("缺少兩月確認相對成長行情：" + ", ".join(sorted(missing)))

    raw = low_turnover_relative_growth_states(
        close,
        core=core,
        growth=growth,
        long_lookback=long_lookback,
        skip_recent=skip_recent,
        trend_window=trend_window,
    )
    core_average = close[core].rolling(trend_window, min_periods=trend_window).mean()
    prior_raw: bool | None = None
    run_length = 0
    confirmed_growth: bool | None = None
    states: dict[pd.Timestamp, str] = {}
    for day, raw_value in raw.items():
        value = bool(raw_value)
        run_length = run_length + 1 if prior_raw is not None and value == prior_raw else 1
        prior_raw = value
        if run_length >= confirmation_months:
            confirmed_growth = value
        if confirmed_growth is None:
            continue

        current_core = close.loc[day, core]
        average_core = core_average.loc[day]
        if confirmed_growth:
            state = "growth"
        elif (
            np.isfinite(current_core)
            and np.isfinite(average_core)
            and float(current_core) > float(average_core)
        ):
            state = "core"
        else:
            state = "defense"
        states[pd.Timestamp(day)] = state
    return pd.Series(states, dtype="string", name="state")


def _confirmed_relative_growth_targets(
    close: pd.DataFrame,
    *,
    core: str,
    growth: str,
    defensive: str,
    initial_signal_before: str | pd.Timestamp | None,
    growth_core_weight: float,
    defense_core_weight: float,
    matched: bool,
    confirmation_months: int,
    long_lookback: int,
    skip_recent: int,
    trend_window: int,
) -> pd.DataFrame:
    if not 0.0 < growth_core_weight < 1.0:
        raise ValueError("成長態核心權重必須介於 0 與 1 之間")
    if not 0.0 < defense_core_weight < 1.0:
        raise ValueError("防守態核心權重必須介於 0 與 1 之間")
    required = {core, growth, defensive}
    missing = required - set(close.columns)
    if missing:
        raise ValueError("缺少兩月確認相對成長行情：" + ", ".join(sorted(missing)))

    states = confirmed_relative_growth_states(
        close,
        core=core,
        growth=growth,
        confirmation_months=confirmation_months,
        long_lookback=long_lookback,
        skip_recent=skip_recent,
        trend_window=trend_window,
    )
    columns = list(dict.fromkeys([core, growth, defensive]))
    targets = pd.DataFrame(np.nan, index=close.index, columns=columns)
    if states.empty:
        return targets

    if initial_signal_before is None:
        initial_day = pd.Timestamp(states.index[0])
    else:
        eligible = states.index[states.index < pd.Timestamp(initial_signal_before)]
        if not len(eligible):
            raise ValueError("正式期以前沒有已確認的完整月末初始訊號")
        initial_day = pd.Timestamp(eligible[-1])

    prior_state: str | None = None
    for day, state_value in states.loc[initial_day:].items():
        state = str(state_value)
        if prior_state is not None and state == prior_state:
            continue
        row = pd.Series(0.0, index=columns)
        if state == "growth":
            row.loc[core] = 1.0 if matched else growth_core_weight
            row.loc[growth] = 0.0 if matched else 1.0 - growth_core_weight
        elif state == "core":
            row.loc[core] = 1.0
        elif state == "defense":
            row.loc[core] = defense_core_weight
            row.loc[defensive] = 1.0 - defense_core_weight
        else:
            raise ValueError(f"未知兩月確認相對成長狀態：{state}")
        targets.loc[day] = row
        prior_state = state
    return targets


def confirmed_relative_growth_targets(
    close: pd.DataFrame,
    *,
    core: str = "SPY",
    growth: str = "QQQ",
    defensive: str = "SHY",
    initial_signal_before: str | pd.Timestamp | None = None,
    growth_core_weight: float = 0.40,
    defense_core_weight: float = 0.70,
    confirmation_months: int = 2,
    long_lookback: int = 252,
    skip_recent: int = 21,
    trend_window: int = 200,
) -> pd.DataFrame:
    """Emit the frozen v13 allocation only at initial entry and state changes."""
    return _confirmed_relative_growth_targets(
        close,
        core=core,
        growth=growth,
        defensive=defensive,
        initial_signal_before=initial_signal_before,
        growth_core_weight=growth_core_weight,
        defense_core_weight=defense_core_weight,
        matched=False,
        confirmation_months=confirmation_months,
        long_lookback=long_lookback,
        skip_recent=skip_recent,
        trend_window=trend_window,
    )


def confirmed_relative_growth_matched_targets(
    close: pd.DataFrame,
    *,
    core: str = "SPY",
    growth: str = "QQQ",
    defensive: str = "SHY",
    initial_signal_before: str | pd.Timestamp | None = None,
    growth_core_weight: float = 0.40,
    defense_core_weight: float = 0.70,
    confirmation_months: int = 2,
    long_lookback: int = 252,
    skip_recent: int = 21,
    trend_window: int = 200,
) -> pd.DataFrame:
    """Match v13's de-risking dates while replacing its growth sleeve with core."""
    return _confirmed_relative_growth_targets(
        close,
        core=core,
        growth=growth,
        defensive=defensive,
        initial_signal_before=initial_signal_before,
        growth_core_weight=growth_core_weight,
        defense_core_weight=defense_core_weight,
        matched=True,
        confirmation_months=confirmation_months,
        long_lookback=long_lookback,
        skip_recent=skip_recent,
        trend_window=trend_window,
    )


def confirmed_market_trend_states(
    close: pd.DataFrame,
    *,
    core: str = "SPY",
    confirmation_months: int = 2,
    trend_window: int = 200,
) -> pd.Series:
    """Return the frozen v14 risk state at completed month ends.

    The broad one-times ETF forms the signal.  A raw state must agree for two
    completed months before the confirmed state may change.  No state is emitted
    before the first full confirmation, so the first allocation cannot use one
    unconfirmed observation.
    """
    if core not in close.columns:
        raise ValueError(f"缺少小幅槓桿趨勢核心行情：{core}")
    if confirmation_months < 1:
        raise ValueError("小幅槓桿趨勢確認月至少需要一個月")
    if trend_window < 2:
        raise ValueError("小幅槓桿趨勢均線至少需要兩個交易日")

    average = close[core].rolling(trend_window, min_periods=trend_window).mean()
    month_end = _month_end_signal_mask(close.index)
    raw: dict[pd.Timestamp, bool] = {}
    for day in close.index[month_end]:
        current = close.loc[day, core]
        mean = average.loc[day]
        if not np.isfinite(current) or not np.isfinite(mean):
            continue
        raw[pd.Timestamp(day)] = bool(float(current) > float(mean))

    prior_raw: bool | None = None
    run_length = 0
    confirmed: bool | None = None
    states: dict[pd.Timestamp, str] = {}
    for day, value in raw.items():
        run_length = run_length + 1 if prior_raw is not None and value == prior_raw else 1
        prior_raw = value
        if run_length >= confirmation_months:
            confirmed = value
        if confirmed is not None:
            states[day] = "risk_on" if confirmed else "risk_off"
    return pd.Series(states, dtype="string", name="state")


def modest_leverage_trend_targets(
    close: pd.DataFrame,
    *,
    core: str = "SPY",
    leveraged: str = "SSO",
    defensive: str = "SHY",
    initial_signal_before: str | pd.Timestamp | None = None,
    leveraged_weight: float = 0.60,
    confirmation_months: int = 2,
    trend_window: int = 200,
) -> pd.DataFrame:
    """Emit the pre-registered v14 monthly 60/40 or all-defensive targets."""
    if not 0.0 < leveraged_weight < 1.0:
        raise ValueError("小幅槓桿 ETF 權重必須介於 0 與 1 之間")
    required = {core, leveraged, defensive}
    missing = required - set(close.columns)
    if missing:
        raise ValueError("缺少小幅槓桿趨勢行情：" + ", ".join(sorted(missing)))

    states = confirmed_market_trend_states(
        close,
        core=core,
        confirmation_months=confirmation_months,
        trend_window=trend_window,
    )
    columns = list(dict.fromkeys([leveraged, defensive]))
    targets = pd.DataFrame(np.nan, index=close.index, columns=columns)
    if states.empty:
        return targets

    if initial_signal_before is None:
        initial_day = pd.Timestamp(states.index[0])
    else:
        eligible = states.index[states.index < pd.Timestamp(initial_signal_before)]
        if not len(eligible):
            raise ValueError("正式期以前沒有已確認的小幅槓桿趨勢訊號")
        initial_day = pd.Timestamp(eligible[-1])

    for day, state_value in states.loc[initial_day:].items():
        row = pd.Series(0.0, index=columns)
        if str(state_value) == "risk_on":
            row.loc[leveraged] = leveraged_weight
            row.loc[defensive] = 1.0 - leveraged_weight
        elif str(state_value) == "risk_off":
            row.loc[defensive] = 1.0
        else:
            raise ValueError(f"未知小幅槓桿趨勢狀態：{state_value}")
        targets.loc[day] = row
    return targets


def modest_leverage_overlay_targets(
    close: pd.DataFrame,
    *,
    core: str = "SPY",
    leveraged: str = "UPRO",
    initial_signal_before: str | pd.Timestamp | None = None,
    leveraged_weight: float = 0.10,
    confirmation_months: int = 2,
    trend_window: int = 200,
) -> pd.DataFrame:
    """Emit the pre-registered v15 120%/100% equity overlay targets monthly."""
    if not 0.0 < leveraged_weight < 1.0:
        raise ValueError("小幅槓桿疊加 ETF 權重必須介於 0 與 1 之間")
    required = {core, leveraged}
    missing = required - set(close.columns)
    if missing:
        raise ValueError("缺少小幅槓桿疊加行情：" + ", ".join(sorted(missing)))

    states = confirmed_market_trend_states(
        close,
        core=core,
        confirmation_months=confirmation_months,
        trend_window=trend_window,
    )
    columns = list(dict.fromkeys([core, leveraged]))
    targets = pd.DataFrame(np.nan, index=close.index, columns=columns)
    if states.empty:
        return targets

    if initial_signal_before is None:
        initial_day = pd.Timestamp(states.index[0])
    else:
        eligible = states.index[states.index < pd.Timestamp(initial_signal_before)]
        if not len(eligible):
            raise ValueError("正式期以前沒有已確認的小幅槓桿疊加訊號")
        initial_day = pd.Timestamp(eligible[-1])

    for day, state_value in states.loc[initial_day:].items():
        row = pd.Series(0.0, index=columns)
        if str(state_value) == "risk_on":
            row.loc[core] = 1.0 - leveraged_weight
            row.loc[leveraged] = leveraged_weight
        elif str(state_value) == "risk_off":
            row.loc[core] = 1.0
        else:
            raise ValueError(f"未知小幅槓桿疊加狀態：{state_value}")
        targets.loc[day] = row
    return targets


def hybrid_leverage_core_targets(
    close: pd.DataFrame,
    *,
    core: str = "SPY",
    leveraged: str = "SSO",
    defensive: str = "SHY",
    daily_target_multiplier: int = 2,
    initial_signal_before: str | pd.Timestamp | None = None,
    permanent_core_weight: float = 0.60,
    risk_on_equity_notional: float = 1.20,
    confirmation_months: int = 2,
    trend_window: int = 200,
) -> pd.DataFrame:
    """Emit the frozen v21 monthly 120%/60% equity-notional targets.

    Sixty percent of the physical portfolio remains in the one-times core.  A
    confirmed risk-on state adds 60 percentage points of equity notional through
    the actual daily-target leveraged ETF; the remaining physical weight stays in
    SHY.  A risk-off state holds the permanent core and SHY only.
    """
    if daily_target_multiplier not in {2, 3}:
        raise ValueError("v21 只允許協議凍結的每日 2 倍或 3 倍實作")
    if not 0.0 < permanent_core_weight < 1.0:
        raise ValueError("v21 常駐核心權重必須介於 0 與 1 之間")
    if risk_on_equity_notional <= permanent_core_weight:
        raise ValueError("v21 風險開啟股票名目曝險必須高於常駐核心")

    leveraged_weight = (
        risk_on_equity_notional - permanent_core_weight
    ) / daily_target_multiplier
    risk_on_defensive_weight = 1.0 - permanent_core_weight - leveraged_weight
    risk_off_defensive_weight = 1.0 - permanent_core_weight
    if min(leveraged_weight, risk_on_defensive_weight, risk_off_defensive_weight) < 0.0:
        raise ValueError("v21 凍結曝險無法形成不借款的物理權重")

    required = {core, leveraged, defensive}
    missing = required - set(close.columns)
    if missing:
        raise ValueError("缺少 v21 常駐核心行情：" + ", ".join(sorted(missing)))

    states = confirmed_market_trend_states(
        close,
        core=core,
        confirmation_months=confirmation_months,
        trend_window=trend_window,
    )
    columns = list(dict.fromkeys([core, leveraged, defensive]))
    targets = pd.DataFrame(np.nan, index=close.index, columns=columns)
    if states.empty:
        return targets

    if initial_signal_before is None:
        initial_day = pd.Timestamp(states.index[0])
    else:
        eligible = states.index[states.index < pd.Timestamp(initial_signal_before)]
        if not len(eligible):
            raise ValueError("正式期以前沒有已確認的 v21 常駐核心訊號")
        initial_day = pd.Timestamp(eligible[-1])

    for day, state_value in states.loc[initial_day:].items():
        row = pd.Series(0.0, index=columns)
        row.loc[core] = permanent_core_weight
        if str(state_value) == "risk_on":
            row.loc[leveraged] = leveraged_weight
            row.loc[defensive] = risk_on_defensive_weight
        elif str(state_value) == "risk_off":
            row.loc[defensive] = risk_off_defensive_weight
        else:
            raise ValueError(f"未知 v21 常駐核心狀態：{state_value}")
        targets.loc[day] = row
    return targets


def trend_volatility_brake_targets(
    close: pd.DataFrame,
    *,
    core: str = "IJH",
    leveraged: str = "MVV",
    defensive: str = "SHY",
    initial_signal_before: str | pd.Timestamp | None = None,
    trend_window: int = 200,
    volatility_window: int = 21,
    target_volatility: float = 0.18,
    maximum_equity_notional: float = 1.50,
) -> pd.DataFrame:
    """Emit v16 weekly trend/volatility targets using an actual daily 2x ETF."""
    required = {core, leveraged, defensive}
    missing = required - set(close.columns)
    if missing:
        raise ValueError("缺少趨勢與波動煞車行情：" + ", ".join(sorted(missing)))
    if trend_window < 2 or volatility_window < 2:
        raise ValueError("趨勢與波動視窗都至少需要兩個交易日")
    if not np.isfinite(target_volatility) or target_volatility <= 0.0:
        raise ValueError("目標波動必須為正的有限值")
    if not 1.0 <= maximum_equity_notional <= 2.0:
        raise ValueError("2 倍 ETF 組合的最高名目曝險必須介於 1 與 2")

    average = close[core].rolling(trend_window, min_periods=trend_window).mean()
    realized = close[core].pct_change(fill_method=None).rolling(
        volatility_window, min_periods=volatility_window
    ).std(ddof=1) * np.sqrt(252.0)
    mask = _week_end_signal_mask(close.index)
    signal_days = close.index[mask]
    if initial_signal_before is None:
        initial_day = pd.Timestamp(signal_days[0]) if len(signal_days) else None
    else:
        eligible = signal_days[signal_days < pd.Timestamp(initial_signal_before)]
        if not len(eligible):
            raise ValueError("正式期以前沒有已完成週末的趨勢與波動煞車訊號")
        initial_day = pd.Timestamp(eligible[-1])

    columns = list(dict.fromkeys([core, leveraged, defensive]))
    targets = pd.DataFrame(np.nan, index=close.index, columns=columns)
    if initial_day is None:
        return targets
    for day in signal_days[signal_days >= initial_day]:
        row = pd.Series(0.0, index=columns)
        current = close.loc[day, core]
        trend = average.loc[day]
        volatility = realized.loc[day]
        risk_on = bool(
            np.isfinite(current)
            and np.isfinite(trend)
            and np.isfinite(volatility)
            and float(current) > float(trend)
            and float(volatility) > 0.0
        )
        if risk_on:
            equity_notional = float(
                np.clip(
                    target_volatility / float(volatility),
                    1.0,
                    maximum_equity_notional,
                )
            )
            row.loc[leveraged] = equity_notional - 1.0
            row.loc[core] = 2.0 - equity_notional
        else:
            row.loc[defensive] = 1.0
        targets.loc[day] = row
    return targets


def _cap_and_normalize(weights: pd.Series, cap: float, total: float = 1.0) -> pd.Series:
    result = weights.clip(lower=0.0).fillna(0.0)
    if result.sum() <= 0 or total <= 0:
        return result * 0.0
    result = result / result.sum() * total
    for _ in range(20):
        over = result > cap + 1e-12
        if not bool(over.any()):
            break
        excess = float((result[over] - cap).sum())
        result[over] = cap
        under = ~over & (result > 0)
        if not bool(under.any()):
            break
        result[under] += excess * result[under] / result[under].sum()
    return result


def equal_weight_targets(
    close: pd.DataFrame,
    tickers: list[str] | tuple[str, ...],
    *,
    min_history: int = 252,
) -> pd.DataFrame:
    symbols = [x for x in tickers if x in close.columns]
    targets = pd.DataFrame(np.nan, index=close.index, columns=symbols)
    month_end = _month_end_signal_mask(close.index)
    history = close.notna().rolling(min_history, min_periods=min_history).sum()
    for day in close.index[month_end]:
        eligible = (history.loc[day, symbols] >= min_history) & close.loc[day, symbols].notna()
        row = pd.Series(0.0, index=symbols)
        if bool(eligible.any()):
            row.loc[eligible] = 1.0 / int(eligible.sum())
        targets.loc[day] = row
    return targets


def dual_momentum_targets(
    close: pd.DataFrame,
    *,
    assets: tuple[str, ...] = ETF_TREND_UNIVERSE,
    defensive: str = DEFENSIVE_ASSET,
    top_k: int = 4,
    long_lookback: int = 252,
    skip_recent: int = 21,
    trend_window: int = 200,
) -> pd.DataFrame:
    """Monthly diversified dual momentum with an explicit defensive fallback.

    Relative signal: total return from t-252 to t-21.
    Absolute signal: asset above its 200-session moving average and outperforming SHY.
    """
    symbols = [x for x in (*assets, defensive) if x in close.columns]
    risky = [x for x in assets if x in symbols]
    if defensive not in symbols:
        raise ValueError(f"缺少防守資產 {defensive}")
    targets = pd.DataFrame(np.nan, index=close.index, columns=symbols)
    momentum = close.shift(skip_recent).div(close.shift(long_lookback)).sub(1.0)
    trend = close > close.rolling(trend_window, min_periods=trend_window).mean()
    month_end = _month_end_signal_mask(close.index)

    for day in close.index[month_end]:
        scores = momentum.loc[day, risky].dropna().sort_values(ascending=False)
        defensive_score = float(momentum.loc[day, defensive])
        if not np.isfinite(defensive_score):
            defensive_score = 0.0
        eligible = [
            ticker
            for ticker in scores.index
            if bool(trend.loc[day, ticker]) and float(scores[ticker]) > defensive_score
        ][:top_k]
        row = pd.Series(0.0, index=symbols)
        slot = 1.0 / top_k
        if eligible:
            # Inverse-vol within each equal slot is intentionally avoided: it adds a second
            # estimated parameter surface and can turn a simple signal test into an optimizer.
            row.loc[eligible] = slot
        row.loc[defensive] = 1.0 - row.sum()
        targets.loc[day] = row
    return targets


def style_rotation_targets(
    close: pd.DataFrame,
    *,
    assets: tuple[str, ...] = ("IWF", "IWD", "IJR"),
    defensive: str = DEFENSIVE_ASSET,
    long_lookback: int = 252,
    skip_recent: int = 21,
    slots: int = 2,
) -> pd.DataFrame:
    """Allocate fixed slots to positive 12-1 month equity-style momentum.

    Each selected style receives exactly ``1 / slots``.  Empty slots stay in the
    defensive asset, so one eligible style does not quietly become a 100% position.
    The signal is formed only on completed month ends and is executed by the shared
    engine at the next session's open.
    """
    if defensive not in close.columns:
        raise ValueError(f"缺少防守資產 {defensive}")
    missing = set(assets) - set(close.columns)
    if missing:
        raise ValueError("缺少風格資產：" + ", ".join(sorted(missing)))
    if len(set(assets)) != len(assets):
        raise ValueError("風格資產不可重複")
    if long_lookback <= skip_recent or skip_recent < 0:
        raise ValueError("風格動量回顧窗必須大於跳過區間")
    if slots < 1 or slots > len(assets):
        raise ValueError("風格輪動槽位數必須介於 1 與資產數之間")

    columns = [*assets, defensive]
    targets = pd.DataFrame(np.nan, index=close.index, columns=columns)
    momentum = (
        close[list(assets)]
        .shift(skip_recent)
        .div(close[list(assets)].shift(long_lookback))
        .sub(1.0)
    )
    month_end = _month_end_signal_mask(close.index)
    slot_weight = 1.0 / slots
    for day in close.index[month_end]:
        scores = momentum.loc[day].replace([np.inf, -np.inf], np.nan).dropna()
        if len(scores) != len(assets):
            continue
        selected = list(scores[scores > 0.0].sort_values(ascending=False).index[:slots])
        row = pd.Series(0.0, index=columns)
        row.loc[selected] = slot_weight
        row.loc[defensive] = 1.0 - slot_weight * len(selected)
        targets.loc[day] = row
    return targets


def balanced_trend_satellite_targets(
    close: pd.DataFrame,
    *,
    assets: tuple[str, ...] = ETF_TREND_UNIVERSE,
    defensive: str = DEFENSIVE_ASSET,
    satellite: str = "QQQ",
    core_share: float = 0.75,
    core_risk_budget: float = 0.50,
    top_k: int = 10,
    trend_window: int = 200,
    vol_window: int = 63,
    max_active_weight: float = 0.35,
) -> pd.DataFrame:
    """Monthly diversified trend core plus a permanent growth satellite.

    The core ranks 3/6/12-month total returns, requires positive momentum and a
    price above its 200-session average, and inverse-volatility weights eligible
    ETFs. Market breadth graduates the active sleeve instead of making an all-or-
    nothing regime call. The rest of the core is SHY; a fixed QQQ satellite keeps
    some equity participation when the defensive core scales down.

    Signals use close-t data only. The engine executes them at open t+1.
    """
    if not 0.0 <= core_share <= 1.0:
        raise ValueError("core_share 必須介於 0 與 1")
    if not 0.0 <= core_risk_budget <= 1.0:
        raise ValueError("core_risk_budget 必須介於 0 與 1")
    if top_k <= 0:
        raise ValueError("top_k 必須大於零")
    if not 0.0 < max_active_weight <= 1.0:
        raise ValueError("max_active_weight 必須介於 0 與 1")

    symbols = [x for x in dict.fromkeys((*assets, defensive, satellite)) if x in close.columns]
    risky = [x for x in assets if x in symbols]
    if defensive not in symbols:
        raise ValueError(f"缺少防守資產 {defensive}")
    if satellite not in symbols:
        raise ValueError(f"缺少衛星資產 {satellite}")
    targets = pd.DataFrame(np.nan, index=close.index, columns=symbols)
    momentum = sum(close.div(close.shift(window)).sub(1.0) for window in (63, 126, 252)) / 3
    trend = close > close.rolling(trend_window, min_periods=trend_window).mean()
    volatility = (
        close.pct_change(fill_method=None).rolling(vol_window, min_periods=vol_window).std()
    )
    month_end = _month_end_signal_mask(close.index)

    for day in close.index[month_end]:
        row = pd.Series(0.0, index=symbols)
        core = pd.Series(0.0, index=symbols)
        breadth = float(trend.loc[day, risky].mean()) if risky else 0.0
        if breadth >= 0.60:
            breadth_scale = 1.0
        elif breadth >= 0.40:
            breadth_scale = 0.70
        elif breadth >= 0.20:
            breadth_scale = 0.30
        else:
            breadth_scale = 0.0

        scores = momentum.loc[day, risky]
        eligible = scores[(scores > 0) & trend.loc[day, risky]].dropna()
        eligible = eligible.sort_values(ascending=False).head(top_k).index
        inverse_vol = 1.0 / volatility.loc[day, eligible].replace(0.0, np.nan)
        inverse_vol = inverse_vol.replace([np.inf, -np.inf], np.nan).dropna()
        active_total = core_risk_budget * breadth_scale
        if len(inverse_vol) and active_total > 0:
            active_weights = _cap_and_normalize(inverse_vol, cap=max_active_weight)
            core.loc[active_weights.index] = active_weights * active_total
        core.loc[defensive] += 1.0 - float(core.sum())

        row += core * core_share
        row.loc[satellite] += 1.0 - core_share
        targets.loc[day] = row
    return targets


def growth_guard_targets(
    close: pd.DataFrame,
    *,
    core_share: float = 0.20,
) -> pd.DataFrame:
    """Growth-led reference strategy with a capped defensive trend core.

    Eighty percent is a permanent QQQ satellite at the frozen setting.
    The remaining core uses the same multi-asset trend, breadth, inverse-volatility,
    and SHY fallback rules as :func:`balanced_trend_satellite_targets`.
    """
    return balanced_trend_satellite_targets(close, core_share=core_share)


def volatility_guard_targets(
    close: pd.DataFrame,
    *,
    growth: str = "QQQ",
    defensive: str = DEFENSIVE_ASSET,
    target_volatility: float = 0.18,
    volatility_window: int = 21,
) -> pd.DataFrame:
    """Monthly unlevered volatility-managed QQQ allocation with a SHY reserve.

    Exposure equals target annualized volatility divided by trailing realized
    volatility, clipped to [0, 1]. The unused weight is held in SHY. Signals only
    use observations through close t and execute through the shared t+1 engine.
    """
    if growth not in close.columns:
        raise ValueError(f"缺少成長資產 {growth}")
    if defensive not in close.columns:
        raise ValueError(f"缺少防守資產 {defensive}")
    if target_volatility <= 0:
        raise ValueError("目標波動必須大於零")
    if volatility_window < 2:
        raise ValueError("波動估計窗至少需要兩個交易日")

    targets = pd.DataFrame(np.nan, index=close.index, columns=[growth, defensive])
    realized = close[growth].pct_change(fill_method=None).rolling(
        volatility_window, min_periods=volatility_window
    ).std() * np.sqrt(252.0)
    exposure = target_volatility / realized.replace(0.0, np.nan)
    exposure = exposure.replace([np.inf, -np.inf], np.nan).clip(lower=0.0, upper=1.0)
    month_end = _month_end_signal_mask(close.index)
    for day in close.index[month_end]:
        growth_weight = float(exposure.loc[day]) if np.isfinite(exposure.loc[day]) else 0.0
        targets.loc[day, growth] = growth_weight
        targets.loc[day, defensive] = 1.0 - growth_weight
    return targets


def trend_confirmed_volatility_guard_targets(
    close: pd.DataFrame,
    *,
    growth: str = "QQQ",
    defensive: str = DEFENSIVE_ASSET,
    target_volatility: float = 0.18,
    volatility_window: int = 21,
    momentum_window: int = 252,
    confirmation_months: int = 2,
) -> pd.DataFrame:
    """Keep full growth exposure unless a confirmed long-term downtrend raises risk.

    A completed month-end is classified as positive when the growth asset's trailing
    ``momentum_window`` total return is above zero.  The regime changes only after
    ``confirmation_months`` consecutive observations agree.  In the positive regime
    the strategy holds 100% growth; in the defensive regime it reuses the unlevered
    volatility target and holds the remainder in ``defensive``.

    The state is reconstructed from the complete signal history on every call, so a
    paper account does not depend on hidden process memory.  All inputs stop at close t
    and the shared engine executes the target at open t+1.
    """
    if growth not in close.columns:
        raise ValueError(f"缺少成長資產 {growth}")
    if defensive not in close.columns:
        raise ValueError(f"缺少防守資產 {defensive}")
    if target_volatility <= 0:
        raise ValueError("目標波動必須大於零")
    if volatility_window < 2:
        raise ValueError("波動估計窗至少需要兩個交易日")
    if momentum_window < 2:
        raise ValueError("趨勢估計窗至少需要兩個交易日")
    if confirmation_months < 1:
        raise ValueError("趨勢確認月至少需要一個月")

    targets = pd.DataFrame(np.nan, index=close.index, columns=[growth, defensive])
    growth_returns = close[growth].pct_change(fill_method=None)
    realized = growth_returns.rolling(
        volatility_window, min_periods=volatility_window
    ).std() * np.sqrt(252.0)
    defensive_exposure = target_volatility / realized.replace(0.0, np.nan)
    defensive_exposure = defensive_exposure.replace([np.inf, -np.inf], np.nan).clip(
        lower=0.0, upper=1.0
    )
    momentum = close[growth].div(close[growth].shift(momentum_window)).sub(1.0)
    month_end = _month_end_signal_mask(close.index)

    recent_signs: list[bool] = []
    growth_regime = True
    for day in close.index[month_end]:
        if not np.isfinite(momentum.loc[day]) or not np.isfinite(defensive_exposure.loc[day]):
            continue
        recent_signs.append(bool(momentum.loc[day] > 0.0))
        window = recent_signs[-confirmation_months:]
        if len(window) == confirmation_months and all(window):
            growth_regime = True
        elif len(window) == confirmation_months and not any(window):
            growth_regime = False

        growth_weight = 1.0 if growth_regime else float(defensive_exposure.loc[day])
        targets.loc[day, growth] = growth_weight
        targets.loc[day, defensive] = 1.0 - growth_weight
    return targets


def three_clock_ensemble_targets(
    close: pd.DataFrame,
    *,
    growth: str = "QQQ",
    defensive: str = DEFENSIVE_ASSET,
    target_volatility: float = 0.18,
    volatility_window: int = 21,
    momentum_window: int = 252,
    confirmation_months: int = 2,
) -> pd.DataFrame:
    """Equal-sleeve blend of static, volatility, and confirmed-trend clocks.

    The three sleeves each control exactly one third of the portfolio.  Combining
    their target weights, rather than blending their input signals, preserves each
    clock as an independent decision rule and avoids fitting ensemble weights.
    """
    if growth not in close.columns:
        raise ValueError(f"缺少成長資產 {growth}")
    if defensive not in close.columns:
        raise ValueError(f"缺少防守資產 {defensive}")
    volatility = volatility_guard_targets(
        close,
        growth=growth,
        defensive=defensive,
        target_volatility=target_volatility,
        volatility_window=volatility_window,
    )
    trend = trend_confirmed_volatility_guard_targets(
        close,
        growth=growth,
        defensive=defensive,
        target_volatility=target_volatility,
        volatility_window=volatility_window,
        momentum_window=momentum_window,
        confirmation_months=confirmation_months,
    )
    targets = pd.DataFrame(np.nan, index=close.index, columns=[growth, defensive], dtype=float)
    common = volatility.notna().all(axis=1) & trend.notna().all(axis=1)
    targets.loc[common, growth] = (
        1.0 + volatility.loc[common, growth] + trend.loc[common, growth]
    ) / 3.0
    targets.loc[common, defensive] = 1.0 - targets.loc[common, growth]
    return targets


def momentum_tilt_targets(
    close: pd.DataFrame,
    tickers: list[str] | tuple[str, ...],
    *,
    tilt_strength: float = 1.0,
    long_lookback: int = 252,
    skip_recent: int = 21,
    vol_window: int = 63,
    trend_window: int = 200,
    max_weight: float = 0.10,
) -> pd.DataFrame:
    """Broad long-only pool with monotone momentum/risk tilts, rebalanced monthly."""
    symbols = [x for x in tickers if x in close.columns]
    targets = pd.DataFrame(np.nan, index=close.index, columns=symbols)
    momentum = close.shift(skip_recent).div(close.shift(long_lookback)).sub(1.0)
    volatility = close.pct_change(fill_method=None).rolling(vol_window).std() * np.sqrt(252)
    trend = close > close.rolling(trend_window, min_periods=trend_window).mean()
    month_end = _month_end_signal_mask(close.index)

    for day in close.index[month_end]:
        valid = momentum.loc[day, symbols].notna() & volatility.loc[day, symbols].notna()
        row = pd.Series(0.0, index=symbols)
        if int(valid.sum()) < 5:
            targets.loc[day] = row
            continue
        mom_rank = momentum.loc[day, valid.index[valid]].rank(pct=True)
        low_vol_rank = (-volatility.loc[day, valid.index[valid]]).rank(pct=True)
        score = 0.8 * mom_rank + 0.2 * low_vol_rank
        # A non-zero floor preserves diversification; the signal changes active weights,
        # rather than turning a broad pool into seven concentrated bets.
        raw = 0.35 + tilt_strength * score.pow(2)
        raw *= trend.loc[day, raw.index].map({True: 1.0, False: 0.60}).astype(float)
        row.loc[raw.index] = _cap_and_normalize(raw, cap=max_weight)
        targets.loc[day] = row
    return targets


def stock_screen(
    close: pd.DataFrame,
    volume: pd.DataFrame,
    records: list[StockRecord],
) -> pd.DataFrame:
    """Latest point-in-time ranking. This function does not claim historical membership."""
    symbols = [r.symbol for r in records if r.symbol in close.columns]
    if not symbols:
        return pd.DataFrame()
    mom_12_1 = close.shift(21).div(close.shift(252)).sub(1.0).iloc[-1][symbols]
    mom_6_1 = close.shift(21).div(close.shift(126)).sub(1.0).iloc[-1][symbols]
    vol = close.pct_change(fill_method=None).rolling(63).std().iloc[-1][symbols] * np.sqrt(252)
    trend_200 = close.iloc[-1][symbols].div(close.rolling(200).mean().iloc[-1][symbols]).sub(1.0)
    dollar_volume = (close * volume).rolling(20).mean().iloc[-1][symbols]

    frame = pd.DataFrame(
        {
            "mom_12_1": mom_12_1,
            "mom_6_1": mom_6_1,
            "trend_200": trend_200,
            "ann_vol": vol,
            "dollar_volume_20d": dollar_volume,
        }
    ).dropna()
    if frame.empty:
        return frame
    frame["score"] = (
        0.45 * frame["mom_12_1"].rank(pct=True)
        + 0.25 * frame["mom_6_1"].rank(pct=True)
        + 0.20 * frame["trend_200"].rank(pct=True)
        + 0.10 * (-frame["ann_vol"]).rank(pct=True)
    )
    lookup = {r.symbol: r for r in records}
    frame["name"] = [lookup[x].name for x in frame.index]
    frame["sector"] = [lookup[x].sector for x in frame.index]
    frame["universe_as_of"] = [lookup[x].as_of for x in frame.index]
    frame["rank"] = frame["score"].rank(method="first", ascending=False).astype(int)
    return frame.sort_values("rank")
