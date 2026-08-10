"""Pre-registered baseline target schedules for the short-term v1 study.

Baseline construction is kept separate from valuation.  Each returned frame
contains only point-in-time target rows; callers must pass it through the same
``build_next_open_schedule`` and raw-accounting layer as the candidate.  No
baseline result is published by this module.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

FORMAL_BASELINE_SCHEDULE_VERSION = "round20-formal-baseline-schedule-v1"
FORMAL_BASELINE_KEYS = (
    "QQQ_buy_hold",
    "SPY_buy_hold",
    "pit_eligible_equal_weight_monthly",
    "first_top10_equal_then_drift",
)
_TOLERANCE = 1e-10


class FormalBaselineScheduleError(ValueError):
    """Fail-closed baseline schedule error with a stable code."""

    def __init__(self, code: str, detail: str):
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}")


def _fail(code: str, detail: str) -> None:
    raise FormalBaselineScheduleError(code, detail)


def _validate_candidate_targets(targets: pd.DataFrame) -> pd.DatetimeIndex:
    if not isinstance(targets, pd.DataFrame) or targets.empty:
        _fail("baseline_target_missing", "candidate targets 不可為空")
    if not isinstance(targets.index, pd.DatetimeIndex):
        _fail("baseline_target_index_invalid", "target index 必須是 DatetimeIndex")
    index = pd.DatetimeIndex(targets.index)
    if index.hasnans or index.has_duplicates or not index.is_monotonic_increasing:
        _fail("baseline_target_index_invalid", "signal 日期必須唯一遞增")
    values = targets.apply(pd.to_numeric, errors="coerce")
    if values.isna().any().any() or not np.isfinite(values.to_numpy(dtype=float)).all():
        _fail("baseline_target_invalid", "candidate target 含非有限數字")
    if (values < -_TOLERANCE).any().any():
        _fail("baseline_target_invalid", "candidate target 含負權重")
    if not np.allclose(values.sum(axis=1), 1.0, atol=_TOLERANCE, rtol=0.0):
        _fail("baseline_target_invalid", "candidate target 權重未逐期等於 100%")
    return index


def _one_asset_buy_hold(index: pd.DatetimeIndex, asset_id: str) -> pd.DataFrame:
    asset = str(asset_id).strip()
    if not asset:
        _fail("baseline_asset_invalid", "buy-and-hold asset 不可空白")
    # A single first-signal row means one D+1 entry, followed by no further
    # target changes.  The account layer holds the asset between sessions.
    return pd.DataFrame({asset: [1.0]}, index=pd.DatetimeIndex([index[0]]))


def _eligible_equal_weight(
    targets: pd.DataFrame,
    audit: pd.DataFrame,
) -> pd.DataFrame:
    required = {"signal_session", "security_id"}
    if not isinstance(audit, pd.DataFrame) or not required <= set(audit.columns):
        _fail("baseline_audit_schema_invalid", "signal audit 缺少 eligibility 欄位")
    result = pd.DataFrame(0.0, index=targets.index, columns=targets.columns)
    for signal in targets.index:
        rows = audit.loc[audit["signal_session"].eq(str(signal.date()))]
        symbols = sorted(set(rows["security_id"].astype(str)))
        # The frozen policy gives each qualifying name one tenth while the
        # remaining Top-10 slots use the same QQQ fallback.  If more than ten
        # names qualify, the baseline is equal weight across the entire pool.
        if not symbols:
            result.loc[signal, "QQQ"] = 1.0
            continue
        slots = max(10, len(symbols))
        weight = 1.0 / float(slots)
        for symbol in symbols:
            if symbol not in result.columns:
                result[symbol] = 0.0
            result.loc[signal, symbol] = weight
        if len(symbols) < 10:
            if "QQQ" not in result.columns:
                result["QQQ"] = 0.0
            result.loc[signal, "QQQ"] = (10 - len(symbols)) * weight
    return result


def _first_top10_drift(targets: pd.DataFrame) -> pd.DataFrame:
    positive = targets.iloc[0].loc[targets.iloc[0] > _TOLERANCE]
    if positive.empty:
        _fail("baseline_target_invalid", "首個 Top-10 target 沒有持倉")
    # Only one target row is intentional.  Filling later rows would turn a
    # no-rebalance drift control into a monthly strategy by accident.
    return pd.DataFrame(
        {str(symbol): [float(weight)] for symbol, weight in positive.items()},
        index=pd.DatetimeIndex([targets.index[0]]),
    )


def _validate_result(name: str, frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty or not isinstance(frame.index, pd.DatetimeIndex):
        _fail("baseline_target_invalid", f"{name} 沒有有效 target row")
    values = frame.apply(pd.to_numeric, errors="coerce")
    if values.isna().any().any() or not np.isfinite(values.to_numpy(dtype=float)).all():
        _fail("baseline_target_invalid", f"{name} 含非有限權重")
    if (values < -_TOLERANCE).any().any() or not np.allclose(
        values.sum(axis=1), 1.0, atol=_TOLERANCE, rtol=0.0
    ):
        _fail("baseline_target_invalid", f"{name} 權重未逐期等於 100%")
    return values.loc[:, [column for column in values if (values[column] > _TOLERANCE).any()]]


@dataclass(frozen=True)
class FormalBaselineTargetSet:
    """The four frozen baseline target frames, before D+1 scheduling."""

    version: str
    targets: dict[str, pd.DataFrame]
    semantics: dict[str, str]


def build_formal_baseline_targets(
    candidate_targets: pd.DataFrame,
    signal_audit: pd.DataFrame,
    *,
    qqq_asset_id: str = "QQQ",
    spy_asset_id: str = "SPY",
) -> FormalBaselineTargetSet:
    """Build all four pre-registered baselines from the same signal dates.

    The stock-pool baseline uses only rows present in the signal audit at that
    signal date.  The drift baseline has exactly one row; this shape is a
    guard against accidentally rebalancing it every month.
    """

    index = _validate_candidate_targets(candidate_targets)
    if str(qqq_asset_id).strip() == str(spy_asset_id).strip():
        _fail("baseline_asset_invalid", "QQQ 與 SPY asset ID 不可相同")
    frames = {
        "QQQ_buy_hold": _one_asset_buy_hold(index, qqq_asset_id),
        "SPY_buy_hold": _one_asset_buy_hold(index, spy_asset_id),
        "pit_eligible_equal_weight_monthly": _eligible_equal_weight(
            candidate_targets, signal_audit
        ),
        "first_top10_equal_then_drift": _first_top10_drift(candidate_targets),
    }
    frames = {name: _validate_result(name, frame) for name, frame in frames.items()}
    return FormalBaselineTargetSet(
        version=FORMAL_BASELINE_SCHEDULE_VERSION,
        targets=frames,
        semantics={
            "QQQ_buy_hold": "首個正式訊號後下一開市買入 QQQ，之後不再換倉",
            "SPY_buy_hold": "首個正式訊號後下一開市買入 SPY，之後不再換倉",
            "pit_eligible_equal_weight_monthly": "同一訊號日合資格逐期股票池等權；不足十槽以 QQQ 補位",
            "first_top10_equal_then_drift": "只在首個正式訊號等權買入候選 target，之後公司行動外不再換倉",
        },
    )


def baseline_target_summary(targets: FormalBaselineTargetSet) -> list[dict[str, Any]]:
    """Return a small internal summary without metrics or promotion fields."""

    if tuple(targets.targets) != FORMAL_BASELINE_KEYS:
        _fail("baseline_target_schema_invalid", "baseline key 次序漂移")
    return [
        {
            "key": key,
            "signal_rows": len(targets.targets[key]),
            "first_signal": str(targets.targets[key].index[0].date()),
            "assets_seen": sorted(map(str, targets.targets[key].columns)),
            "semantics": targets.semantics[key],
        }
        for key in FORMAL_BASELINE_KEYS
    ]
