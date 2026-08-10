from __future__ import annotations

import pandas as pd
import pytest

from usfddk.formal_baseline_schedule import (
    FORMAL_BASELINE_KEYS,
    FormalBaselineScheduleError,
    baseline_target_summary,
    build_formal_baseline_targets,
)
from usfddk.formal_execution_schedule import build_next_open_schedule


def _candidate() -> tuple[pd.DataFrame, pd.DataFrame]:
    signals = pd.DatetimeIndex(["2026-01-30", "2026-02-27"])
    targets = pd.DataFrame(
        {
            "SEC-A": [0.10, 0.10],
            "SEC-B": [0.10, 0.0],
            "SEC-C": [0.0, 0.10],
            "QQQ": [0.80, 0.80],
        },
        index=signals,
    )
    audit = pd.DataFrame(
        [
            {"signal_session": "2026-01-30", "security_id": "SEC-A"},
            {"signal_session": "2026-01-30", "security_id": "SEC-B"},
            {"signal_session": "2026-02-27", "security_id": "SEC-A"},
            {"signal_session": "2026-02-27", "security_id": "SEC-C"},
        ]
    )
    return targets, audit


def test_four_baselines_share_the_same_first_signal_and_have_frozen_shapes() -> None:
    targets, audit = _candidate()
    result = build_formal_baseline_targets(targets, audit)

    assert tuple(result.targets) == FORMAL_BASELINE_KEYS
    assert len(result.targets["QQQ_buy_hold"]) == 1
    assert len(result.targets["SPY_buy_hold"]) == 1
    assert len(result.targets["pit_eligible_equal_weight_monthly"]) == 2
    assert len(result.targets["first_top10_equal_then_drift"]) == 1
    assert result.targets["QQQ_buy_hold"].iloc[0]["QQQ"] == pytest.approx(1.0)
    assert result.targets["SPY_buy_hold"].iloc[0]["SPY"] == pytest.approx(1.0)
    assert result.targets["pit_eligible_equal_weight_monthly"].iloc[0]["SEC-A"] == pytest.approx(0.1)
    assert result.targets["pit_eligible_equal_weight_monthly"].iloc[0]["SEC-B"] == pytest.approx(0.1)
    assert result.targets["pit_eligible_equal_weight_monthly"].iloc[0]["QQQ"] == pytest.approx(0.8)
    assert result.targets["first_top10_equal_then_drift"].iloc[0]["SEC-B"] == pytest.approx(0.1)
    assert baseline_target_summary(result)[-1]["signal_rows"] == 1


def test_baseline_frames_can_use_the_same_next_open_schedule_without_backfill() -> None:
    targets, audit = _candidate()
    result = build_formal_baseline_targets(targets, audit)
    sessions = pd.DatetimeIndex(
        ["2026-01-30", "2026-02-02", "2026-02-27", "2026-03-02"]
    )

    monthly = build_next_open_schedule(
        sessions, result.targets["pit_eligible_equal_weight_monthly"]
    )
    drift = build_next_open_schedule(
        sessions, result.targets["first_top10_equal_then_drift"]
    )
    assert len(monthly) == 2
    assert len(drift) == 1
    assert monthly[0].execution_session == pd.Timestamp("2026-02-02")
    assert drift[0].execution_session == pd.Timestamp("2026-02-02")


def test_baseline_builder_rejects_candidate_weight_drift_and_asset_collision() -> None:
    targets, audit = _candidate()
    targets.iloc[0, 0] = 0.2
    with pytest.raises(FormalBaselineScheduleError) as weight_error:
        build_formal_baseline_targets(targets, audit)
    assert weight_error.value.code == "baseline_target_invalid"

    targets, audit = _candidate()
    with pytest.raises(FormalBaselineScheduleError) as asset_error:
        build_formal_baseline_targets(targets, audit, qqq_asset_id="SPY", spy_asset_id="SPY")
    assert asset_error.value.code == "baseline_asset_invalid"
