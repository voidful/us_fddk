from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from pathlib import Path

import pytest

from scripts.build_short_term_correlation_crowding_report import (
    _canonicalize_floats,
)
from usfddk.correlation_crowding import (
    FROZEN_CONTRACT,
    PROTOCOL_SHA256,
    REPAIR_PROTOCOL_SHA256,
    CorrelationCrowdingError,
    run_attack_harness,
    run_correlation_crowding,
    validate_crowding_contract,
)

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def result() -> dict:
    return run_correlation_crowding(ROOT)


def test_parent_and_repair_protocol_hashes_are_frozen() -> None:
    parent = ROOT / "docs/SHORT_TERM_CORRELATION_CROWDING_PROTOCOL.md"
    repair = ROOT / "docs/SHORT_TERM_CORRELATION_CROWDING_SCHEMA_REPAIR_PROTOCOL.md"
    assert hashlib.sha256(parent.read_bytes()).hexdigest() == PROTOCOL_SHA256
    assert hashlib.sha256(repair.read_bytes()).hexdigest() == REPAIR_PROTOCOL_SHA256


def test_parent_failure_and_non_independent_repair_are_disclosed(result: dict) -> None:
    protocol = result["protocol"]
    assert protocol["initial_parent_protocol_run"] == {
        "status": "failed_closed_before_output",
        "error_code": "crowding_baseline_fairness_breached",
    }
    assert protocol["schema_repair"]["independent_first_unseen_evidence"] is False
    assert protocol["schema_repair"]["calculated_after_repair_commit"] is True


def test_contract_mutations_fail_closed() -> None:
    attacks = run_attack_harness()
    assert len(attacks) == 19
    assert all(row["rejected"] for row in attacks)


def test_repair_contract_violation_has_stable_code() -> None:
    with pytest.raises(CorrelationCrowdingError) as exc_info:
        validate_crowding_contract(
            replace(FROZEN_CONTRACT, matched_cash_on_insufficient_breadth=False)
        )
    assert exc_info.value.code == "crowding_repair_protocol_mismatch"


def test_existing_events_are_reconstructed_exactly(result: dict) -> None:
    assert result["research_round"] == 25
    assert result["input"]["current_cohort_count"] == 25
    assert result["input"]["events"] == 905
    assert result["input"]["first_signal_date"] == "2006-08-04"
    assert result["input"]["last_signal_date"] == "2026-07-02"
    assert result["reconstruction"]["maximum_return_residual"] <= 1e-12
    assert result["reconstruction"]["maximum_contribution_identity_residual"] <= 1e-12


def test_crowding_and_current_identifier_scope_are_explicit(result: dict) -> None:
    assert result["input"]["survivorship_bias_warning"] is True
    assert result["input"]["identifier_scope"] == ("2026_current_symbols_not_permanent_ids")
    crowding = result["original_crowding"]
    assert crowding["nominal_stocks"] == 7
    assert crowding["pairs_per_event"] == 21
    assert crowding["effective_bets"]["median"] <= 7
    assert all(
        row["investment_role"] == "ex_post_attribution_not_a_buy_list"
        for row in result["current_symbol_contributors"]
    )


def test_matched_cash_stresses_keep_candidate_and_baseline_exposure_equal(
    result: dict,
) -> None:
    family = {row["id"]: row for row in result["family"]["comparisons"]}
    for row_id in ("remove_top1_contributor", "remove_top3_contributors"):
        exposure = family[row_id]["matched_cash_exposure"]
        assert exposure["matched_cash"] is True
        assert 0 < exposure["minimum_equity_exposure"] <= 1
        assert exposure["mean_equity_exposure"] <= 1
    assert all(
        row["matched_cash_exposure"]["matched_cash"] is True
        for row in result["leave_one_symbol_out"]["rows_sorted_weakest_first"]
    )


def test_family_correction_and_decision_boundary(result: dict) -> None:
    assert result["family"]["size"] == 4
    assert len(result["family"]["comparisons"]) == 4
    assert result["family"]["bootstrap"]["paths"] == 20_000
    assert result["family"]["bootstrap"]["common_indices"] is True
    assert result["gate_summary"]["total"] == 12
    assert result["gate_summary"]["passed"] == sum(row["passed"] for row in result["gates"])
    assert result["control_summary"] == {
        "passed": 19,
        "total": 19,
        "all_passed": True,
    }
    assert result["attack_summary"] == {
        "rejected": 19,
        "total": 19,
        "all_rejected": True,
    }
    decision = result["decision"]
    assert decision["new_strategy_created"] is False
    assert decision["formal_strategy_runs"] == 0
    assert decision["paper_status"] == "all_cash_not_started"
    assert decision["real_money_action_usd"] == 0
    assert decision["can_promote_from_this_round"] is False


def test_committed_receipts_match_recalculation() -> None:
    artifact = ROOT / "artifacts/short_term_correlation_crowding_validation.json"
    site = ROOT / "site/data/short-term-correlation-crowding.json"
    if not artifact.exists() or not site.exists():
        pytest.skip("generated receipts are created by the report builder")
    generated = _canonicalize_floats(run_correlation_crowding(ROOT))
    generated["receipt_float_decimal_places"] = 12
    saved = json.loads(artifact.read_text(encoding="utf-8"))
    assert saved == generated
    assert site.read_bytes() == artifact.read_bytes()


def test_receipt_float_canonicalization_is_platform_stable() -> None:
    left = {"value": 2.2050905311151254, "nested": [0.1 + 0.2]}
    right = {"value": 2.2050905311151251, "nested": [0.3]}
    assert _canonicalize_floats(left) == _canonicalize_floats(right)
