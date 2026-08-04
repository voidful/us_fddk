from __future__ import annotations

import hashlib
from dataclasses import replace
from pathlib import Path

import pytest

from scripts.build_short_term_baseline_multiplicity_report import (
    _canonicalize_floats,
)
from usfddk.baseline_multiplicity import (
    FROZEN_CONTRACT,
    PROTOCOL_SHA256,
    BaselineMultiplicityError,
    run_attack_harness,
    run_baseline_multiplicity,
    validate_multiplicity_contract,
)

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def result() -> dict:
    return run_baseline_multiplicity(ROOT)


def test_protocol_hash_is_frozen() -> None:
    path = ROOT / "docs/SHORT_TERM_BASELINE_MULTIPLICITY_PROTOCOL.md"
    assert hashlib.sha256(path.read_bytes()).hexdigest() == PROTOCOL_SHA256


def test_contract_mutations_fail_closed() -> None:
    attacks = run_attack_harness()
    assert len(attacks) == 16
    assert all(row["rejected"] for row in attacks)


def test_direct_contract_violation_has_stable_code() -> None:
    with pytest.raises(BaselineMultiplicityError) as exc_info:
        validate_multiplicity_contract(
            replace(FROZEN_CONTRACT, global_search_trials=9)
        )
    assert exc_info.value.code == "multiplicity_global_trials_not_frozen"


def test_common_sample_and_family_are_frozen(result: dict) -> None:
    assert result["research_round"] == 24
    assert result["input"]["common_events"] == 905
    assert result["input"]["first_signal_date"] == "2006-08-04"
    assert result["input"]["last_signal_date"] == "2026-07-02"
    assert result["input"]["horizons"] == [5, 10, 20]
    assert result["input"]["embedded_round_trip_cost_bps"] == 20
    assert len(result["comparisons"]) == 9
    assert result["global_search_trials"] == 6_208


def test_primary_attribution_is_exact(result: dict) -> None:
    attribution = result["primary_attribution"]
    assert attribution["max_abs_identity_residual"] <= 1e-12
    assert attribution["combined_effect"]["mean_difference"] == pytest.approx(
        attribution["ranking_effect"]["mean_difference"]
        + attribution["eligibility_effect"]["mean_difference"]
    )


def test_bootstrap_is_common_and_deterministic(result: dict) -> None:
    bootstrap = result["common_bootstrap"]
    assert bootstrap["paths"] == 20_000
    assert bootstrap["block_length_events"] == 52
    assert bootstrap["common_indices"] is True
    assert bootstrap["centered_under_null"] is True
    again = run_baseline_multiplicity(ROOT)
    assert bootstrap == again["common_bootstrap"]


def test_controls_gates_and_decision_boundary(result: dict) -> None:
    assert result["control_summary"] == {
        "passed": 16,
        "total": 16,
        "all_passed": True,
    }
    assert result["attack_summary"] == {
        "rejected": 16,
        "total": 16,
        "all_rejected": True,
    }
    assert result["gate_summary"]["total"] == 9
    assert result["gate_summary"]["passed"] == sum(
        row["passed"] for row in result["gates"]
    )
    assert result["decision"]["formal_readiness"] == "1/18"
    assert result["decision"]["formal_strategy_runs"] == 0
    assert result["decision"]["paper_status"] == "all_cash_not_started"
    assert result["decision"]["real_money_action_usd"] == 0
    assert result["decision"]["can_promote_from_this_round"] is False


def test_receipt_float_canonicalization_is_platform_stable() -> None:
    left = {"value": 1.6880813581069898, "nested": [0.1 + 0.2]}
    right = {"value": 1.6880813581069893, "nested": [0.3]}
    assert _canonicalize_floats(left) == _canonicalize_floats(right)
