from __future__ import annotations

import pandas as pd
import pytest

from usfddk.formal_execution_schedule import (
    FormalExecutionScheduleError,
    build_next_open_schedule,
    execution_schedule_frame,
)


def test_schedule_maps_month_end_targets_to_next_session_without_backfill() -> None:
    sessions = pd.bdate_range("2026-01-01", periods=5)
    targets = pd.DataFrame(
        {"SEC-A": [0.5, 0.0], "QQQ": [0.5, 1.0]},
        index=pd.DatetimeIndex([sessions[1], sessions[3]]),
    )
    instructions = build_next_open_schedule(sessions, targets)

    assert [(row.signal_session, row.execution_session) for row in instructions] == [
        (sessions[1], sessions[2]),
        (sessions[3], sessions[4]),
    ]
    frame = execution_schedule_frame(instructions)
    assert frame.iloc[0]["target_weights"] == {"SEC-A": 0.5, "QQQ": 0.5}


def test_schedule_rejects_last_session_and_invalid_weight() -> None:
    sessions = pd.bdate_range("2026-01-01", periods=3)
    with pytest.raises(FormalExecutionScheduleError) as last_error:
        build_next_open_schedule(
            sessions,
            pd.DataFrame({"QQQ": [1.0]}, index=pd.DatetimeIndex([sessions[-1]])),
        )
    assert last_error.value.code == "execution_clock_violation"

    with pytest.raises(FormalExecutionScheduleError) as weight_error:
        build_next_open_schedule(
            sessions,
            pd.DataFrame({"SEC-A": [0.6], "QQQ": [0.6]}, index=pd.DatetimeIndex([sessions[0]])),
        )
    assert weight_error.value.code == "execution_target_invalid"
