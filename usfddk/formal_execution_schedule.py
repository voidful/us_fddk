"""D+1 execution schedule for the frozen monthly signal layer.

This module is intentionally separate from account valuation.  It turns each
month-end target row into exactly one next-XNYS-open instruction and rejects
backfilled, duplicate, or end-of-calendar signals before any cash accounting
can run.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd


class FormalExecutionScheduleError(ValueError):
    """Fail-closed schedule error with a stable code."""

    def __init__(self, code: str, detail: str):
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}")


def _fail(code: str, detail: str) -> None:
    raise FormalExecutionScheduleError(code, detail)


@dataclass(frozen=True)
class ExecutionInstruction:
    signal_session: pd.Timestamp
    execution_session: pd.Timestamp
    targets: dict[str, float]


def _sessions(values: Iterable[object]) -> pd.DatetimeIndex:
    parsed = pd.to_datetime(list(values), format="%Y-%m-%d", errors="coerce")
    index = pd.DatetimeIndex(parsed)
    if len(index) == 0 or index.hasnans or index.has_duplicates or not index.is_monotonic_increasing:
        _fail("execution_calendar_invalid", "XNYS sessions 必須唯一、完整及遞增")
    return index


def build_next_open_schedule(
    sessions: Iterable[object],
    targets: pd.DataFrame,
) -> tuple[ExecutionInstruction, ...]:
    """Convert target rows to one irreversible next-open instruction each."""

    calendar = _sessions(sessions)
    if targets.empty:
        _fail("execution_target_missing", "沒有月末 target row")
    if not isinstance(targets.index, pd.DatetimeIndex):
        _fail("execution_target_index_invalid", "target index 必須是 DatetimeIndex")
    signals = pd.DatetimeIndex(targets.index)
    if signals.hasnans or signals.has_duplicates or not signals.is_monotonic_increasing:
        _fail("execution_target_index_invalid", "target signal 日期必須唯一遞增")
    if any(signal not in calendar for signal in signals):
        _fail("execution_target_calendar_mismatch", "target signal 不在 XNYS sessions")

    instructions: list[ExecutionInstruction] = []
    used_executions: set[pd.Timestamp] = set()
    for signal, row in targets.iterrows():
        later = calendar[calendar > signal]
        if len(later) == 0:
            _fail("execution_clock_violation", f"{signal.date()} 沒有下一個 XNYS open")
        execution = pd.Timestamp(later[0])
        if execution in used_executions:
            _fail("execution_schedule_duplicate", f"{execution.date()} 有多個訊號")
        values = pd.to_numeric(row, errors="coerce")
        if values.isna().any() or not np.isfinite(values.to_numpy(dtype=float)).all():
            _fail("execution_target_invalid", f"{signal.date()} target 含非有限數字")
        if (values < 0).any() or not np.isclose(float(values.sum()), 1.0, atol=1e-10):
            _fail("execution_target_invalid", f"{signal.date()} target 權重未精確等於 100%")
        targets_dict = {
            str(symbol): float(weight)
            for symbol, weight in values.items()
            if float(weight) > 0.0
        }
        if not targets_dict:
            _fail("execution_target_invalid", f"{signal.date()} target 沒有持倉")
        instructions.append(
            ExecutionInstruction(
                signal_session=pd.Timestamp(signal),
                execution_session=execution,
                targets=targets_dict,
            )
        )
        used_executions.add(execution)
    return tuple(instructions)


def execution_schedule_frame(
    instructions: Iterable[ExecutionInstruction],
) -> pd.DataFrame:
    """Create an internal audit frame without changing target semantics."""

    rows: list[dict[str, Any]] = []
    for instruction in instructions:
        rows.append(
            {
                "signal_session": str(instruction.signal_session.date()),
                "execution_session": str(instruction.execution_session.date()),
                "target_weights": dict(instruction.targets),
            }
        )
    return pd.DataFrame(rows, columns=("signal_session", "execution_session", "target_weights"))
