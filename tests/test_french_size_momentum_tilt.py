from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from scripts.prepare_short_term_french_size_momentum_tilt_data import _verify_preconditions
from usfddk.french_size_momentum_tilt import (
    aggregate_cells,
    frozen_cell_weights,
    validate_frozen_weight_contract,
)
from usfddk.french_size_prior import SIZE_PRIOR_COLUMNS

ROOT = Path(__file__).resolve().parents[1]


def test_frozen_full_pool_weights_are_valid_and_monotonic() -> None:
    checks = validate_frozen_weight_contract()
    assert checks
    assert all(checks.values())
    linear = frozen_cell_weights("linear")
    assert linear.iloc[0] == pytest.approx(1 / 75)
    assert linear.iloc[4] == pytest.approx(5 / 75)


def test_concentration_ladder_uses_the_same_frozen_cell_grid() -> None:
    row = [float(prior_rank) for _size in range(5) for prior_rank in range(1, 6)]
    frame = pd.DataFrame([row], index=pd.period_range("1963-01", periods=1, freq="M"), columns=SIZE_PRIOR_COLUMNS)
    assert aggregate_cells(frame, "equal").iloc[0] == pytest.approx(3.0)
    assert aggregate_cells(frame, "linear").iloc[0] == pytest.approx(11 / 3)
    assert aggregate_cells(frame, "top2").iloc[0] == pytest.approx(4.5)
    assert aggregate_cells(frame, "top1").iloc[0] == pytest.approx(5.0)


def test_cell_aggregation_fails_closed_on_schema_or_missing_values() -> None:
    frame = pd.DataFrame([[0.0] * 25], columns=SIZE_PRIOR_COLUMNS)
    with pytest.raises(ValueError, match="欄名或次序"):
        aggregate_cells(frame.rename(columns={SIZE_PRIOR_COLUMNS[-1]: "winner"}), "linear")
    frame.iloc[0, 0] = float("nan")
    with pytest.raises(ValueError, match="缺值"):
        aggregate_cells(frame, "linear")


def test_protocol_preconditions_are_frozen_before_first_download() -> None:
    reused = _verify_preconditions(ROOT)
    assert "size_prior_1_0_negative_control" in reused
    assert "qqq_spy_snapshot" in reused
