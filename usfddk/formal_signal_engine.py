"""Point-in-time signal generation for the frozen short-term v1 strategy.

This module deliberately stops at target weights.  It is the bridge between a
validated provider ledger and the later, one-shot accounting runner; it does
not create a Paper account, publish symbols, or calculate performance.  The
implementation is intentionally independent of the current-cohort sandbox in
``short_term_high_return`` so that today's constituents cannot silently become
historical inputs.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

FORMAL_SIGNAL_ENGINE_VERSION = "round18-formal-signal-engine-v1"
FORMAL_SIGNAL_POLICY = "last_official_session_each_complete_month"
FORMAL_STRATEGY_PROTOCOL_SHA256 = (
    "589a799b18412e1fdad569c48e94313689c57b75eae84972a5c20baaa6ede139"
)
FORMAL_SIGNAL_COLUMNS = (
    "signal_session",
    "security_id",
    "company_id",
    "sector_code",
    "momentum_12_1",
    "momentum_6_1",
    "trend_200",
    "volatility_63",
    "median_dollar_volume_20",
    "composite_score",
    "selected",
    "fallback_qqq",
)


class FormalSignalEngineError(ValueError):
    """Stable fail-closed error for point-in-time signal generation."""

    def __init__(self, code: str, detail: str):
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}")


def _fail(code: str, detail: str) -> None:
    raise FormalSignalEngineError(code, detail)


def _date(value: object, field: str) -> pd.Timestamp:
    parsed = pd.to_datetime(str(value), format="%Y-%m-%d", errors="coerce")
    if pd.isna(parsed):
        _fail("signal_date_invalid", f"{field} 不是 YYYY-MM-DD")
    return pd.Timestamp(parsed).normalize()


def _known_at(value: object, field: str) -> pd.Timestamp:
    raw = str(value).strip()
    if not raw:
        _fail("point_in_time_timestamp_missing", f"{field} 缺少 known-at 時間")
    parsed = pd.to_datetime(raw, errors="coerce", utc=True)
    if pd.isna(parsed):
        _fail("point_in_time_timestamp_invalid", f"{field} known-at 時間無效")
    return pd.Timestamp(parsed)


def _end_date(value: object) -> pd.Timestamp | None:
    raw = str(value).strip()
    return None if not raw else _date(raw, "effective_to")


def _active_rows(
    frame: pd.DataFrame,
    *,
    security_id: str,
    signal: pd.Timestamp,
    signal_close_at: pd.Timestamp,
    start_column: str = "effective_from",
    end_column: str = "effective_to",
    known_column: str | None = None,
) -> pd.DataFrame:
    rows: list[int] = []
    for index, row in frame.loc[frame["security_id"].eq(security_id)].iterrows():
        start = _date(row[start_column], start_column)
        end = _end_date(row[end_column])
        if not (start <= signal and (end is None or signal < end)):
            continue
        if known_column is not None and _known_at(row[known_column], known_column) > signal_close_at:
            continue
        rows.append(index)
    return frame.loc[rows]


def _require_exactly_one(frame: pd.DataFrame, code: str, detail: str) -> pd.Series:
    if len(frame) != 1:
        _fail(code, detail)
    return frame.iloc[0]


def _validate_price_frame(prices: pd.DataFrame) -> pd.DataFrame:
    required = {
        "security_id",
        "session",
        "open_raw",
        "high_raw",
        "low_raw",
        "close_raw",
        "volume",
        "total_return_factor",
        "source_status",
    }
    # The provider contract may carry additional columns, but all required
    # columns must be present.  Keeping this check explicit avoids a silent
    # adjusted-price fallback.
    missing = sorted(required - set(prices.columns))
    if missing:
        _fail("signal_price_schema_invalid", f"daily_prices 缺欄位：{missing}")
    frame = prices.copy()
    frame["__session"] = pd.to_datetime(frame["session"], format="%Y-%m-%d", errors="coerce")
    if frame["__session"].isna().any():
        _fail("signal_price_schema_invalid", "daily_prices 有無效 session")
    numeric_columns = (
        "open_raw",
        "high_raw",
        "low_raw",
        "close_raw",
        "volume",
        "total_return_factor",
    )
    for column in numeric_columns:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    if frame[["security_id", "__session"]].duplicated().any():
        _fail("signal_price_schema_invalid", "同一證券／交易日有重複價格")
    if not frame["__session"].is_monotonic_increasing:
        frame = frame.sort_values(["__session", "security_id"])
    return frame.reset_index(drop=True)


def _month_end_sessions(sessions: pd.DatetimeIndex) -> pd.DatetimeIndex:
    if len(sessions) == 0 or sessions.hasnans or sessions.has_duplicates:
        _fail("signal_calendar_invalid", "交易日曆為空、重複或含缺失")
    ordered = pd.DatetimeIndex(sessions).sort_values()
    periods = ordered.to_period("M")
    return pd.DatetimeIndex(
        [ordered[index] for index in range(len(ordered)) if index == len(ordered) - 1 or periods[index] != periods[index + 1]]
    )


@dataclass(frozen=True)
class SignalInputs:
    """Validated provider tables needed by the signal layer."""

    security_master: pd.DataFrame
    membership_history: pd.DataFrame
    daily_prices: pd.DataFrame
    classification_history: pd.DataFrame
    trading_calendar: pd.DataFrame


def load_signal_inputs_from_ledger(package: str | Path) -> SignalInputs:
    """Load only the provider ledger tables needed by the signal layer.

    The caller must run the repository's point-in-time and execution-extension
    auditors before treating the package as formal input.  This loader performs
    no promotion and never reads the current watchlist or a ticker snapshot.
    """

    root = Path(package)
    ledger = root / "ledger" if (root / "ledger").is_dir() else root
    files = {
        "security_master": "security_master.csv",
        "membership_history": "membership_history.csv",
        "daily_prices": "daily_prices.csv",
        "classification_history": "classification_history.csv",
        "trading_calendar": "trading_calendar.csv",
    }
    frames: dict[str, pd.DataFrame] = {}
    for key, filename in files.items():
        path = ledger / filename
        try:
            frames[key] = pd.read_csv(
                path,
                dtype=str,
                keep_default_na=False,
                na_filter=False,
            )
        except (OSError, pd.errors.ParserError) as exc:
            _fail("signal_input_read_failed", f"{filename}: {type(exc).__name__}")
    return SignalInputs(**frames)


def _prepare_inputs(inputs: SignalInputs) -> tuple[SignalInputs, pd.DatetimeIndex]:
    required_master = {"security_id", "company_id", "security_type", "share_class", "currency"}
    if not required_master <= set(inputs.security_master.columns):
        _fail("signal_security_master_invalid", "security_master 缺少固定身份欄位")
    required_membership = {
        "index_id",
        "security_id",
        "effective_from",
        "effective_to",
        "announced_at",
        "source_record_id",
    }
    if not required_membership <= set(inputs.membership_history.columns):
        _fail("signal_membership_schema_invalid", "membership_history 缺少公布時間欄位")
    required_classification = {
        "security_id",
        "scheme",
        "sector_code",
        "effective_from",
        "effective_to",
        "known_at",
        "source_record_id",
    }
    if not required_classification <= set(inputs.classification_history.columns):
        _fail("signal_classification_schema_invalid", "classification_history 缺少 known-at 欄位")
    if not {"session", "exchange", "close_at"} <= set(inputs.trading_calendar.columns):
        _fail("signal_calendar_invalid", "trading_calendar 缺少 XNYS close_at 欄位")

    prices = _validate_price_frame(inputs.daily_prices)
    calendar = inputs.trading_calendar.copy()
    sessions = pd.to_datetime(calendar["session"], format="%Y-%m-%d", errors="coerce")
    if sessions.isna().any() or not sessions.is_monotonic_increasing or sessions.duplicated().any():
        _fail("signal_calendar_invalid", "trading_calendar 必須按日期唯一遞增")
    if not calendar["exchange"].eq("XNYS").all():
        _fail("signal_calendar_invalid", "signal calendar 只接受 XNYS")
    close_at = pd.to_datetime(calendar["close_at"], errors="coerce", utc=True)
    if close_at.isna().any():
        _fail("signal_calendar_invalid", "trading_calendar close_at 缺少明確 UTC offset")
    master = inputs.security_master.copy()
    if master["security_id"].duplicated().any() or master["company_id"].eq("").any():
        _fail("signal_security_master_invalid", "security master 證券 ID／公司 ID 無法唯一對數")
    if not master["security_type"].eq("common_stock").all() or not master["currency"].eq("USD").all():
        _fail("signal_security_master_invalid", "策略只接受 USD common_stock")
    return SignalInputs(
        security_master=master,
        membership_history=inputs.membership_history.copy(),
        daily_prices=prices,
        classification_history=inputs.classification_history.copy(),
        trading_calendar=calendar.copy(),
    ), pd.DatetimeIndex(sessions)


def _price_history(
    prices: pd.DataFrame,
    security_id: str,
    signal: pd.Timestamp,
) -> pd.DataFrame:
    rows = prices.loc[(prices["security_id"] == security_id) & (prices["__session"] <= signal)].copy()
    rows = rows.sort_values("__session")
    if rows.empty:
        _fail("signal_price_history_missing", f"{security_id} 在 {signal.date()} 沒有價格")
    if rows["source_status"].eq("observed").sum() != len(rows):
        _fail("signal_price_history_missing", f"{security_id} 在訊號日前含非 observed 價格")
    if rows[["close_raw", "volume", "total_return_factor"]].isna().any().any():
        _fail("signal_price_history_missing", f"{security_id} 價格／成交量／總回報因子缺失")
    if (rows[["close_raw", "total_return_factor"]] <= 0).any().any() or (rows["volume"] < 0).any():
        _fail("signal_price_history_invalid", f"{security_id} 價格／總回報因子量級無效")
    return rows


def _feature_row(
    history: pd.DataFrame,
    *,
    signal: pd.Timestamp,
    security_id: str,
    company_id: str,
    sector_code: str,
) -> dict[str, Any] | None:
    if history["__session"].iloc[-1] != signal:
        _fail("signal_price_history_missing", f"{security_id} 缺少訊號日收市資料")
    if len(history) < 252:
        _fail("signal_history_window_missing", f"{security_id} 少於 252 個訊號前交易日")
    if len(history) < 253:
        _fail("signal_history_window_missing", f"{security_id} 無法建立 t-252／t-21 窗口")
    position = len(history) - 1
    if position < 252 or position < 21 or position < 126 or position < 199 or position < 62:
        return None
    wealth = history["total_return_factor"].cumprod()
    mom_12_1 = float(wealth.iloc[position - 21] / wealth.iloc[position - 252] - 1.0)
    mom_6_1 = float(wealth.iloc[position - 21] / wealth.iloc[position - 126] - 1.0)
    trend_window = wealth.iloc[position - 199 : position + 1]
    trend = float(wealth.iloc[position] / trend_window.mean() - 1.0)
    daily_returns = history["total_return_factor"].iloc[position - 62 : position + 1] - 1.0
    volatility = float(daily_returns.std(ddof=1) * math.sqrt(252.0))
    dollar_volume = history["close_raw"].iloc[position - 19 : position + 1] * history["volume"].iloc[position - 19 : position + 1]
    median_dollar_volume = float(dollar_volume.median())
    if float(history["close_raw"].iloc[position]) <= 5.0 or median_dollar_volume < 20_000_000.0:
        return None
    if not all(math.isfinite(value) for value in (mom_12_1, mom_6_1, trend, volatility, median_dollar_volume)):
        _fail("signal_feature_invalid", f"{security_id} 在 {signal.date()} 特徵非有限")
    return {
        "signal_session": str(signal.date()),
        "security_id": security_id,
        "company_id": company_id,
        "sector_code": sector_code,
        "momentum_12_1": mom_12_1,
        "momentum_6_1": mom_6_1,
        "trend_200": trend,
        "volatility_63": volatility,
        "median_dollar_volume_20": median_dollar_volume,
    }


def _percentile(series: pd.Series) -> pd.Series:
    if series.empty:
        return series
    return series.rank(method="average", pct=True)


def _eligible_rows(
    inputs: SignalInputs,
    signal: pd.Timestamp,
    signal_close_at: pd.Timestamp,
) -> pd.DataFrame:
    membership = inputs.membership_history
    master = inputs.security_master.set_index("security_id", drop=False)
    classifications = inputs.classification_history
    prices = inputs.daily_prices
    candidates: list[dict[str, Any]] = []
    active = membership.loc[membership["index_id"].eq("SP500")]
    for security_id in sorted(active["security_id"].unique()):
        member_rows = _active_rows(
            active,
            security_id=security_id,
            signal=signal,
            signal_close_at=signal_close_at,
            known_column="announced_at",
        )
        if member_rows.empty:
            continue
        if security_id not in master.index:
            _fail("signal_security_master_invalid", f"{security_id} 不在 security master")
        master_row = master.loc[security_id]
        class_rows = classifications.loc[classifications["scheme"].eq("GICS")]
        class_rows = _active_rows(
            class_rows,
            security_id=security_id,
            signal=signal,
            signal_close_at=signal_close_at,
            known_column="known_at",
        )
        classification = _require_exactly_one(
            class_rows,
            "signal_classification_ambiguous",
            f"{security_id} 在 {signal.date()} 沒有唯一 point-in-time GICS sector",
        )
        sector_code = str(classification["sector_code"]).strip()
        if not sector_code:
            _fail("signal_classification_ambiguous", f"{security_id} 缺 sector_code")
        feature = _feature_row(
            _price_history(prices, security_id, signal),
            signal=signal,
            security_id=security_id,
            company_id=str(master_row["company_id"]),
            sector_code=sector_code,
        )
        if feature is not None:
            candidates.append(feature)
    if not candidates:
        return pd.DataFrame(columns=FORMAL_SIGNAL_COLUMNS)
    frame = pd.DataFrame(candidates)
    # Deduplicate share classes using the signal-date 20-session median dollar
    # volume, then permanent security ID.  This is done before ranking.
    frame = frame.sort_values(
        ["company_id", "median_dollar_volume_20", "security_id"],
        ascending=[True, False, True],
    ).drop_duplicates("company_id", keep="first")
    for column in ("momentum_12_1", "momentum_6_1", "trend_200", "volatility_63"):
        frame[f"rank_{column}"] = _percentile(
            -frame[column] if column == "volatility_63" else frame[column]
        )
    frame["composite_score"] = (
        0.45 * frame["rank_momentum_12_1"]
        + 0.25 * frame["rank_momentum_6_1"]
        + 0.20 * frame["rank_trend_200"]
        + 0.10 * frame["rank_volatility_63"]
    )
    return frame


def build_monthly_target_weights(
    inputs: SignalInputs,
    *,
    start: str = "2006-08-01",
    end: str = "2026-07-31",
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Build frozen monthly targets and an internal feature/selection audit.

    The returned target table has permanent ``security_id`` columns plus ``QQQ``
    fallback.  Every row is a month-end close decision and every trade therefore
    belongs to the next XNYS session.  No result or account state is written.
    """

    prepared, sessions = _prepare_inputs(inputs)
    start_date = _date(start, "study_start")
    end_date = _date(end, "study_end")
    study_sessions = sessions[(sessions >= start_date) & (sessions <= end_date)]
    signals = _month_end_sessions(study_sessions)
    symbols = sorted(set(prepared.security_master["security_id"]) | {"QQQ"})
    targets = pd.DataFrame(0.0, index=signals, columns=symbols)
    audit_rows: list[dict[str, Any]] = []
    for signal in signals:
        close_rows = prepared.trading_calendar.loc[
            pd.to_datetime(prepared.trading_calendar["session"], format="%Y-%m-%d") == signal
        ]
        close_row = _require_exactly_one(
            close_rows,
            "signal_calendar_invalid",
            f"{signal.date()} 沒有唯一 XNYS close_at",
        )
        signal_close_at = _known_at(close_row["close_at"], "close_at")
        eligible = _eligible_rows(prepared, signal, signal_close_at)
        if eligible.empty:
            targets.loc[signal, "QQQ"] = 1.0
            continue
        eligible["selected"] = False
        eligible["fallback_qqq"] = False
        sector_counts: dict[str, int] = {}
        selected_indices: list[int] = []
        ordered = eligible.sort_values(
            ["composite_score", "security_id"], ascending=[False, True]
        )
        for row_index, row in ordered.iterrows():
            sector = str(row["sector_code"])
            if sector_counts.get(sector, 0) >= 3:
                continue
            selected_indices.append(row_index)
            sector_counts[sector] = sector_counts.get(sector, 0) + 1
            if len(selected_indices) == 10:
                break
        eligible.loc[selected_indices, "selected"] = True
        missing_slots = 10 - len(selected_indices)
        if missing_slots:
            targets.loc[signal, "QQQ"] = missing_slots / 10.0
            eligible["fallback_qqq"] = True
        for row_index in selected_indices:
            targets.loc[signal, eligible.loc[row_index, "security_id"]] = 0.10
        for row in eligible.itertuples(index=False):
            audit_rows.append({column: getattr(row, column) for column in FORMAL_SIGNAL_COLUMNS})
    if not np.isclose(targets.sum(axis=1), 1.0).all():
        _fail("signal_target_weight_invalid", "每個月末目標權重未精確等於 100%")
    audit = pd.DataFrame(audit_rows, columns=FORMAL_SIGNAL_COLUMNS)
    return targets, audit


def build_baseline_target_weights(
    targets: pd.DataFrame,
    audit: pd.DataFrame,
) -> dict[str, pd.DataFrame]:
    """Build the two stock-pool controls from the same signal audit.

    QQQ/SPY buy-and-hold are account-level baselines and are intentionally not
    represented here.  This function only builds the two strategy-family
    controls that share the point-in-time stock pool.
    """

    if targets.empty:
        _fail("signal_target_weight_invalid", "沒有月末訊號可建立 baseline")
    eligible = pd.DataFrame(0.0, index=targets.index, columns=targets.columns)
    for signal in targets.index:
        rows = audit.loc[audit["signal_session"].eq(str(signal.date()))]
        if rows.empty:
            eligible.loc[signal, "QQQ"] = 1.0
            continue
        securities = list(rows["security_id"].astype(str))
        weight = 1.0 / (len(securities) + (1 if len(securities) < 10 else 0) * (10 - len(securities)))
        # The formal protocol's eligible-pool baseline is equal weight across
        # all qualifying securities; any missing Top-10 slots are QQQ fallback.
        for security_id in securities:
            eligible.loc[signal, security_id] = weight
        if len(securities) < 10:
            eligible.loc[signal, "QQQ"] = weight * (10 - len(securities))
    first = targets.iloc[0].copy() * 0.0
    first.loc[targets.iloc[0] > 0] = targets.iloc[0].loc[targets.iloc[0] > 0]
    drift = pd.DataFrame(np.nan, index=targets.index, columns=targets.columns)
    drift.iloc[0] = first
    return {
        "pit_eligible_equal_weight_monthly": eligible,
        "first_top10_equal_then_drift": drift,
    }
