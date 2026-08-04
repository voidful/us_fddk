from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import pytest

from scripts.build_short_term_reversal_volatility_attribution_report import _canonicalize_floats
from usfddk.reversal_volatility_attribution import (
    FROZEN_CONTRACT,
    PROTOCOL_PATH,
    PROTOCOL_SHA256,
    _event_feature_hash,
    run_contract_attacks,
    run_reversal_volatility_attribution,
    validate_reversal_volatility_contract,
)

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "artifacts/short_term_reversal_volatility_attribution_validation.json"
SITE_DATA = ROOT / "site/data/short-term-reversal-volatility-attribution.json"


@pytest.fixture(scope="module")
def result() -> dict:
    return run_reversal_volatility_attribution(ROOT)


def test_protocol_was_frozen_before_attribution_results() -> None:
    assert hashlib.sha256((ROOT / PROTOCOL_PATH).read_bytes()).hexdigest() == PROTOCOL_SHA256
    validate_reversal_volatility_contract(FROZEN_CONTRACT)


def test_replays_all_same_seen_events_without_claiming_independence(result: dict) -> None:
    assert result["input"]["events"] == 905
    assert result["input"]["first_signal_date"] == "2006-08-04"
    assert result["input"]["last_signal_date"] == "2026-07-02"
    assert len(result["event_rows"]) == 905
    assert result["protocol"]["calculated_after_protocol_commit"] is True
    assert result["protocol"]["independent_first_unseen_evidence"] is False
    assert result["protocol"]["same_seen_905_event_family"] is True
    assert result["input"]["round27_bucket_assignment_sha256"] == (
        "0f1512ccc893f554028b77de85af146e53333e1badd528fb00089878d49e8ffd"
    )


def test_feature_regressions_and_attribution_identities_are_exact(result: dict) -> None:
    integrity = result["attribution_integrity"]
    assert integrity["feature_receipt_sha256"] == (
        "417e67b07bed7676c5cbbcf03d16ec78951d79f874cbfdd6beedd814212fe048"
    )
    assert integrity["maximum_raw_round27_residual"] <= 1e-12
    assert integrity["maximum_identity_residual"] <= 1e-12
    assert integrity["maximum_residual_mean"] <= 1e-12
    assert integrity["maximum_condition_number"] == pytest.approx(14.0)
    assert integrity["minimum_design_rank"] == 3

    first = result["event_rows"][0]
    assert first["qqq_trailing_20d"] == pytest.approx(-0.019633167228)
    assert first["universes"]["eligible"]["feature_receipt_sha256"] == (
        "fe0f04864fd8fa7ad09e0b84f1d39669b482f747cc06a8d219c3e1365bfe73ed"
    )
    for event in result["event_rows"]:
        for universe in event["universes"].values():
            assert universe["regression"]["rank"] == 3
            assert abs(universe["regression"]["residual_mean"]) <= 1e-12
            attribution = universe["bottom_middle_attribution"]
            assert attribution["raw"] == pytest.approx(
                attribution["predicted_total"] + attribution["residual"], abs=1e-12
            )
            assert attribution["predicted_total"] == pytest.approx(
                attribution["prior_5d_contribution"] + attribution["volatility_20d_contribution"],
                abs=1e-12,
            )


def test_eight_hypothesis_family_preserves_raw_and_residual_failures(result: dict) -> None:
    rows = {row["id"]: row for row in result["family"]["comparisons"]}
    assert result["family"]["size"] == len(rows) == 8
    assert rows["eligible_raw_top_middle"]["mean"] == pytest.approx(0.005163622595)
    assert rows["eligible_raw_top_middle"]["newey_west"]["t_stat"] == pytest.approx(2.56517594566)
    assert rows["eligible_raw_top_middle"]["bootstrap_max_t_p"] == pytest.approx(0.110594470276)
    assert rows["complete_raw_top_middle"]["newey_west"]["t_stat"] == pytest.approx(2.304227464867)
    assert rows["eligible_residual_top_middle"]["mean"] == pytest.approx(0.002158657793)
    assert rows["eligible_residual_top_middle"]["newey_west"]["t_stat"] == pytest.approx(
        1.616989081984
    )
    assert rows["complete_residual_top_middle"]["newey_west"]["t_stat"] == pytest.approx(
        1.098092016483
    )
    assert rows["complete_residual_top_middle"]["fixed_halves"]["second"]["mean"] == pytest.approx(
        -0.000678733773
    )
    assert rows["eligible_residual_bottom_middle"]["mean"] == pytest.approx(0.001642554039)
    assert rows["complete_residual_bottom_middle"]["mean"] == pytest.approx(0.000530441136)


def test_controls_explain_most_top_middle_but_not_all_bottom_rebound(result: dict) -> None:
    eligible = result["attribution_summary"]["eligible"]
    complete = result["attribution_summary"]["complete"]
    assert eligible["aggregate_top_middle_retention_fraction"] == pytest.approx(0.418051039423)
    assert complete["aggregate_top_middle_retention_fraction"] == pytest.approx(0.349390675464)
    assert eligible["predicted_bottom_middle"]["mean"] == pytest.approx(-0.000187686893)
    assert complete["predicted_bottom_middle"]["mean"] == pytest.approx(0.00095575566)
    assert eligible["prior5_rank_gap_bottom_middle"]["mean"] == pytest.approx(-0.113034048131)
    assert complete["volatility_rank_gap_bottom_middle"]["mean"] == pytest.approx(0.11350713628)
    assert eligible["beta_prior5"]["newey_west"]["t_stat"] == pytest.approx(-1.412835887437)
    assert complete["beta_volatility"]["newey_west"]["t_stat"] == pytest.approx(2.805551316461)


def test_known_at_market_and_tail_stresses_reject_promotion(result: dict) -> None:
    regimes = result["primary_stresses"]["qqq_trailing_20d_known_at_signal"]
    assert regimes["eligible"]["qqq_trailing_nonnegative"]["events"] == 677
    assert regimes["eligible"]["qqq_trailing_nonnegative"]["newey_west"]["t_stat"] == pytest.approx(
        2.146312239808
    )
    assert regimes["eligible"]["qqq_trailing_negative"]["events"] == 228
    assert regimes["eligible"]["qqq_trailing_negative"]["mean"] == pytest.approx(-0.000376958483)
    assert regimes["complete"]["qqq_trailing_negative"]["mean"] == pytest.approx(-0.001380303965)

    tails = result["primary_stresses"]["remove_largest_raw_bottom_middle"]
    assert tails["eligible"]["events"] == tails["complete"]["events"] == 859
    assert tails["eligible"]["newey_west"]["t_stat"] == pytest.approx(1.95058210917)
    assert tails["complete"]["newey_west"]["t_stat"] == pytest.approx(1.009225082337)


def test_fourteen_gates_keep_short_paper_all_cash(result: dict) -> None:
    assert result["gate_summary"] == {"passed": 6, "total": 14, "all_passed": False}
    assert {row["id"] for row in result["gates"] if not row["passed"]} == {
        "eligible_residual_top_middle",
        "complete_residual_top_middle",
        "eligible_raw_bottom_middle",
        "complete_raw_bottom_middle",
        "eligible_residual_bottom_middle",
        "complete_residual_bottom_middle",
        "retention_and_adjusted_family",
        "known_at_regime_and_tail",
    }
    decision = result["decision"]
    assert decision["can_promote_from_this_round"] is False
    assert decision["new_strategy_created"] is False
    assert decision["formal_strategy_runs"] == 0
    assert decision["paper_status"] == "all_cash_not_started"
    assert decision["paper_positions"] == 0
    assert decision["real_money_action_usd"] == 0


def test_controls_and_single_field_attacks_are_complete(result: dict) -> None:
    assert result["control_summary"] == {"passed": 23, "total": 23, "all_passed": True}
    assert result["attack_summary"] == {"rejected": 23, "total": 23, "all_rejected": True}
    attacks = run_contract_attacks()
    assert len(attacks) == 23
    assert all(row["rejected"] for row in attacks)
    assert attacks[-4]["expected_error_code"] == "reversal_volatility_bootstrap_contract_mismatch"
    assert attacks[-1]["expected_error_code"] == "reversal_volatility_decision_boundary_breached"


def test_generated_receipts_are_identical_and_platform_stable(result: dict) -> None:
    assert ARTIFACT.read_bytes() == SITE_DATA.read_bytes()
    assert re.search(rb": -0\.0(?:[,}\n])", ARTIFACT.read_bytes()) is None
    assert _canonicalize_floats(-5e-13) == 0.0
    stored = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    assert stored["research_round"] == result["research_round"] == 28
    assert stored["gate_summary"] == result["gate_summary"]
    assert stored["decision"]["formal_global_search_trials_unchanged"] == 6208
    assert stored["attribution_integrity"]["feature_receipt_decimal_places"] == 8
    first = [{"ticker": "A", "predicted": 0.1234567890123, "residual": -0.0}]
    second = [{"ticker": "A", "predicted": 0.1234567890124, "residual": 0.0}]
    assert _event_feature_hash(first) == _event_feature_hash(second)
