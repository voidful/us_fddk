from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from scripts.build_short_term_survivorship_contamination_report import (
    _canonicalize_floats,
)
from usfddk.survivorship_contamination import (
    CONTAMINATION_RATE_GRID,
    EXIT_RETURN_GRID,
    FROZEN_CONTRACT,
    INPUT_SHA256,
    PROTOCOL_COMMIT,
    PROTOCOL_SHA256,
    SCHEMA_REPAIR_PROTOCOL_COMMIT,
    SCHEMA_REPAIR_PROTOCOL_SHA256,
    SurvivorshipStressError,
    contamination_delta,
    run_attack_harness,
    run_survivorship_contamination_stress,
    validate_stress_contract,
)

ROOT = Path(__file__).resolve().parents[1]


def test_frozen_contract_and_protocol_identity() -> None:
    validate_stress_contract(FROZEN_CONTRACT)
    assert len(PROTOCOL_SHA256) == 64
    assert len(PROTOCOL_COMMIT) == 40
    assert len(SCHEMA_REPAIR_PROTOCOL_SHA256) == 64
    assert len(SCHEMA_REPAIR_PROTOCOL_COMMIT) == 40
    assert len(INPUT_SHA256) == 64


def test_contract_mutation_fails_with_exact_code() -> None:
    with pytest.raises(SurvivorshipStressError) as caught:
        validate_stress_contract(replace(FROZEN_CONTRACT, top_k=10))
    assert caught.value.code == "stress_top_k_not_frozen"


def test_all_twelve_attacks_are_rejected_by_exact_code() -> None:
    attacks = run_attack_harness()
    assert len(attacks) == 12
    assert all(row["rejected"] for row in attacks)
    assert all(row["expected_error_code"] == row["observed_error_code"] for row in attacks)


def test_candidate_and_eligible_baseline_receive_same_missing_stock() -> None:
    selected = np.array([0.14])
    baseline = np.array([0.10])
    eligible_count = np.array([19.0])
    selected_adjustment, baseline_adjustment, active_delta = contamination_delta(
        selected,
        baseline,
        eligible_count,
        exit_return=-0.50,
    )
    assert selected_adjustment[0] == pytest.approx((-0.50 - 0.14) / 7)
    assert baseline_adjustment[0] == pytest.approx((-0.50 - 0.10) / 20)
    assert active_delta[0] == pytest.approx(
        selected_adjustment[0] - baseline_adjustment[0]
    )


@pytest.fixture(scope="module")
def result() -> dict:
    return run_survivorship_contamination_stress(ROOT)


def test_full_frozen_grid_and_integrity_controls(result: dict) -> None:
    assert len(result["stress_grid"]) == len(EXIT_RETURN_GRID) * len(
        CONTAMINATION_RATE_GRID
    )
    assert result["input"]["event_count"] == 905
    assert result["observed_signal"]["first_signal_date"] == "2006-08-04"
    assert result["observed_signal"]["last_signal_date"] == "2026-07-02"
    assert result["control_summary"] == {
        "passed": 12,
        "total": 12,
        "all_passed": True,
    }
    assert result["attack_summary"] == {
        "rejected": 12,
        "total": 12,
        "all_rejected": True,
    }


def test_primary_cell_survives_only_the_fixed_synthetic_stress(result: dict) -> None:
    primary = result["primary_cell"]
    assert primary["exit_return"] == -0.50
    assert primary["contamination_rate"] == 0.02
    assert primary["expected"]["mean_difference"] == pytest.approx(
        0.0023607875674247335
    )
    assert primary["expected"]["newey_west"]["t_stat"] == pytest.approx(
        2.2534616266278817
    )
    assert result["primary_gate_summary"] == {
        "passed": 5,
        "total": 5,
        "all_passed": True,
    }
    assert result["status"] == "synthetic_primary_stress_survived_not_investable"


def test_severe_low_frequency_exit_stress_breaks_statistical_gate(result: dict) -> None:
    severe = {
        row["exit_return"]: row
        for row in result["stress_grid"]
        if row["contamination_rate"] == 0.02
    }
    assert severe[-0.80]["expected"]["newey_west"]["t_stat"] < 1.96
    assert severe[-1.00]["expected"]["newey_west"]["t_stat"] < 1.96
    break_even = {row["exit_return"]: row for row in result["break_even_by_exit_return"]}
    assert break_even[-0.50]["mean_zero_contamination_rate"] == pytest.approx(
        0.07698466588143499
    )
    assert break_even[-0.50]["newey_west_below_1_96_contamination_rate"] == 0.0276
    assert break_even[-1.00]["newey_west_below_1_96_contamination_rate"] == 0.014


def test_deterministic_randomness_and_decision_boundary(result: dict) -> None:
    assert (
        result["frozen_contract"]["common_random_numbers_sha256"]
        == "28950041e05ef84d70f25c79c178d24868c4823cbec4a114b5e9a5d07af35655"
    )
    assert result["formal_readiness"] == {"passed": 1, "total": 18}
    assert result["formal_stock_backtest_completed"] is False
    assert result["strategy_run_count"] == 0
    assert result["paper"] == {
        "authorized": False,
        "state": "all_cash",
        "positions": 0,
        "allocation_usd": 0,
    }
    assert result["real_money_action_usd"] == 0


def test_receipt_float_canonicalization_removes_platform_epsilon() -> None:
    left = {"t": 1.4909766094180172, "q": [0.002354270094792401]}
    right = {"t": 1.4909766094180177, "q": [0.0023542700947924004]}
    assert _canonicalize_floats(left) == _canonicalize_floats(right)
