from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from scripts.build_short_term_french_size_momentum_tilt_report import _canonicalize
from scripts.prepare_short_term_french_size_momentum_tilt_data import _verify_preconditions
from usfddk.french_size_momentum_tilt import (
    aggregate_cells,
    frozen_cell_weights,
    validate_frozen_weight_contract,
)
from usfddk.french_size_momentum_tilt_research import (
    build_french_size_momentum_tilt_research,
    load_frozen_size_momentum_tilt_data,
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
    frame = pd.DataFrame(
        [row], index=pd.period_range("1963-01", periods=1, freq="M"), columns=SIZE_PRIOR_COLUMNS
    )
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


def test_first_seen_archive_is_complete_and_hash_locked() -> None:
    data = load_frozen_size_momentum_tilt_data(ROOT)
    assert data["size_momentum_value"].shape == (761, 25)
    assert data["size_momentum_equal"].shape == (761, 25)
    assert data["common_index"][0] == pd.Period("1963-01", freq="M")
    assert data["common_index"][-1] == pd.Period("2026-05", freq="M")
    assert data["raw_missing_codes"] == {
        "value_weighted": 4,
        "equal_weighted": 4,
    }


def test_full_pool_tilt_preserves_negative_result_and_trade_boundary() -> None:
    result = build_french_size_momentum_tilt_research(ROOT)
    primary = result["primary_external_period"]
    recent = result["recent_confirmation_period"]

    assert result["status"] == (
        "french_size_momentum_tilt_data_passed_but_economic_validation_failed"
    )
    assert result["gate_breakdown"] == {
        "data": "10/10",
        "primary": "9/19",
        "recent": "4/19",
    }
    assert result["passed_gate_count"] == 23
    assert result["required_gate_count"] == 48
    assert result["protocol"]["candidate_family_paths"] == 30
    assert result["protocol"]["economic_design_changed_after_results"] is False
    assert len(primary["gates"]) == 19
    assert len(recent["gates"]) == 19

    assert primary["candidate_metrics"]["cagr"] == pytest.approx(0.123579465260)
    assert primary["baseline_metrics"]["top1"]["cagr"] == pytest.approx(0.168237941832)
    assert recent["candidate_metrics"]["cagr"] == pytest.approx(0.083122423298)
    assert recent["baseline_metrics"]["market"]["cagr"] == pytest.approx(0.113819285389)
    assert recent["baseline_metrics"]["QQQ"]["cagr"] == pytest.approx(0.161814519558)
    assert recent["candidate_50bps_metrics"]["cagr"] == pytest.approx(-0.016306577972)
    assert result["pbo"]["primary"]["pbo"] == pytest.approx(1 / 63)
    assert result["pbo"]["recent"]["pbo"] == pytest.approx(5 / 21)

    assert result["data_contract_passed"] is True
    assert result["economic_validation_passed"] is False
    assert result["paper_eligible"] is False
    assert result["paper_state_created"] is False
    assert result["trade_ready"] is False
    assert result["real_money_action_usd"] == 0
    assert not any(result["paper_blockers"].values())


def test_report_canonicalizer_keeps_finite_reproducible_values() -> None:
    assert _canonicalize(0.123456789012345) == 0.123456789012
    assert _canonicalize(0.0000000312078618503) == 3.120786185e-08
