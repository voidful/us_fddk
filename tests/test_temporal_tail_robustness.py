from __future__ import annotations

import hashlib
from dataclasses import replace
from pathlib import Path

import pytest

from scripts.build_short_term_temporal_tail_robustness_report import (
    _canonicalize_floats,
)
from usfddk.temporal_tail_robustness import (
    FROZEN_CONTRACT,
    PROTOCOL_SHA256,
    TemporalTailRobustnessError,
    run_attack_harness,
    run_temporal_tail_robustness,
    validate_robustness_contract,
)

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def result() -> dict:
    return run_temporal_tail_robustness(ROOT)


def test_protocol_hash_is_frozen() -> None:
    path = ROOT / "docs/SHORT_TERM_TEMPORAL_TAIL_ROBUSTNESS_PROTOCOL.md"
    assert hashlib.sha256(path.read_bytes()).hexdigest() == PROTOCOL_SHA256


def test_contract_mutations_fail_closed() -> None:
    attacks = run_attack_harness()
    assert len(attacks) == 15
    assert all(row["rejected"] for row in attacks)


def test_direct_contract_violation_has_stable_code() -> None:
    with pytest.raises(TemporalTailRobustnessError) as exc_info:
        validate_robustness_contract(
            replace(FROZEN_CONTRACT, paper_authorized=True)
        )
    assert exc_info.value.code == "robustness_decision_boundary_breached"


def test_frozen_input_and_observed_pairing(result: dict) -> None:
    assert result["research_round"] == 23
    assert result["input"]["events"] == 905
    assert result["input"]["first_signal_date"] == "2006-08-04"
    assert result["input"]["last_signal_date"] == "2026-07-02"
    assert result["input"]["holding_period_sessions"] == 20
    assert result["observed"]["mean_active_difference"] == pytest.approx(
        result["observed"]["mean_selected_return"]
        - result["observed"]["mean_eligible_equal_return"]
    )


def test_fixed_time_and_tail_frontiers(result: dict) -> None:
    assert [row["lag"] for row in result["hac_frontier"]] == [4, 13, 26, 52]
    assert [row["year"] for row in result["calendar_years"]] == list(
        range(2006, 2027)
    )
    assert len(result["epochs"]) == 5
    assert len(result["leave_one_year_out"]) == 21
    assert [row["removed_count"] for row in result["best_year_removals"]] == [
        1,
        3,
    ]
    assert [row["removed_count"] for row in result["tail_event_removals"]] == [
        10,
        46,
    ]


def test_bootstrap_is_deterministic(result: dict) -> None:
    again = run_temporal_tail_robustness(ROOT)
    assert result["moving_block_bootstrap"] == again["moving_block_bootstrap"]
    assert result["moving_block_bootstrap"]["paths"] == 5_000
    assert result["moving_block_bootstrap"]["block_length_events"] == 52


def test_controls_gates_and_decision_boundary(result: dict) -> None:
    assert result["control_summary"] == {
        "passed": 15,
        "total": 15,
        "all_passed": True,
    }
    assert result["attack_summary"] == {
        "rejected": 15,
        "total": 15,
        "all_rejected": True,
    }
    assert result["gate_summary"]["total"] == 8
    assert result["gate_summary"]["passed"] == sum(
        row["passed"] for row in result["gates"]
    )
    assert result["decision"]["formal_readiness"] == "1/18"
    assert result["decision"]["formal_strategy_runs"] == 0
    assert result["decision"]["paper_status"] == "all_cash_not_started"
    assert result["decision"]["real_money_action_usd"] == 0
    assert result["decision"]["can_promote_from_this_round"] is False


def test_receipt_float_canonicalization_is_platform_stable() -> None:
    left = {"value": 1.4909766094180172, "nested": [0.1 + 0.2]}
    right = {"value": 1.4909766094180177, "nested": [0.3]}
    assert _canonicalize_floats(left) == _canonicalize_floats(right)
