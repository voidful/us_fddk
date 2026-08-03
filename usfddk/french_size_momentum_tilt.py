from __future__ import annotations

from collections.abc import Mapping

import numpy as np
import pandas as pd

from usfddk.french_size_prior import SIZE_PRIOR_COLUMNS

ARCHIVE_URL = (
    "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/"
    "25_Portfolios_ME_Prior_12_2_CSV.zip"
)
EXPECTED_MEMBER = "25_Portfolios_ME_Prior_12_2.csv"
FORMAL_START = pd.Period("1963-01", freq="M")
FORMAL_END = pd.Period("2026-05", freq="M")


def size_prior_coordinates() -> list[tuple[int, int]]:
    """Return the frozen column coordinates in official size-major order."""
    return [(size_rank, prior_rank) for size_rank in range(1, 6) for prior_rank in range(1, 6)]


def frozen_cell_weights(kind: str) -> pd.Series:
    """Build one of the preregistered 25-cell weighting schemes."""
    coordinates = size_prior_coordinates()
    if kind == "equal":
        values = [1 / 25] * 25
    elif kind == "linear":
        values = [prior_rank / 75 for _, prior_rank in coordinates]
    elif kind == "squared":
        values = [prior_rank**2 / 275 for _, prior_rank in coordinates]
    elif kind == "top2":
        values = [0.1 if prior_rank >= 4 else 0.0 for _, prior_rank in coordinates]
    elif kind == "top1":
        values = [0.2 if prior_rank == 5 else 0.0 for _, prior_rank in coordinates]
    else:
        raise ValueError(f"未知 25-cell 權重：{kind}")
    weights = pd.Series(values, index=SIZE_PRIOR_COLUMNS, dtype=float, name=kind)
    if not np.isclose(float(weights.sum()), 1.0, atol=1e-12):
        raise AssertionError(f"{kind} 權重不等於 1")
    return weights


def aggregate_cells(frame: pd.DataFrame, kind: str) -> pd.Series:
    """Aggregate official cell returns without shifting their month labels."""
    if list(frame.columns) != SIZE_PRIOR_COLUMNS:
        raise ValueError("25-cell 欄名或次序不符凍結映射")
    if frame.isna().any().any():
        raise ValueError("25-cell 回報含缺值，不准補值後計算")
    result = frame.mul(frozen_cell_weights(kind), axis=1).sum(axis=1)
    result.name = kind
    return result


def validate_frozen_weight_contract() -> Mapping[str, bool]:
    """Expose machine-readable invariants for the data receipt and tests."""
    linear = frozen_cell_weights("linear")
    checks = {
        "all_25_linear_weights_are_positive": bool((linear > 0).all()),
        "five_size_rows_have_equal_total_weight": all(
            np.isclose(float(linear.iloc[offset : offset + 5].sum()), 0.2, atol=1e-12)
            for offset in range(0, 25, 5)
        ),
        "linear_prior_weights_are_monotonic_within_each_size": all(
            linear.iloc[offset : offset + 5].is_monotonic_increasing
            for offset in range(0, 25, 5)
        ),
        "all_preregistered_weights_sum_to_one": all(
            np.isclose(float(frozen_cell_weights(kind).sum()), 1.0, atol=1e-12)
            for kind in ("equal", "linear", "squared", "top2", "top1")
        ),
    }
    return checks
