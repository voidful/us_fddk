from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from scripts.build_short_term_common_risk_residual_report import _canonicalize_floats
from usfddk.common_risk_residual import (
    FROZEN_CONTRACT,
    PROTOCOL_PATH,
    PROTOCOL_SHA256,
    REPAIR_PROTOCOL_PATH,
    REPAIR_PROTOCOL_SHA256,
    _comparison,
    run_common_risk_residual,
    run_contract_attacks,
    validate_common_risk_contract,
)

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "artifacts/short_term_common_risk_residual_validation.json"
SITE_DATA = ROOT / "site/data/short-term-common-risk-residual.json"


@pytest.fixture(scope="module")
def result() -> dict:
    return run_common_risk_residual(ROOT)


def test_protocols_are_frozen_before_successful_output() -> None:
    assert hashlib.sha256((ROOT / PROTOCOL_PATH).read_bytes()).hexdigest() == PROTOCOL_SHA256
    assert (
        hashlib.sha256((ROOT / REPAIR_PROTOCOL_PATH).read_bytes()).hexdigest()
        == REPAIR_PROTOCOL_SHA256
    )
    validate_common_risk_contract(FROZEN_CONTRACT)


def test_reconstructs_all_events_but_uses_one_common_beta_sample(result: dict) -> None:
    assert result["input"]["events"] == 905
    assert result["input"]["first_signal_date"] == "2006-08-04"
    assert result["input"]["family_common_events"] == 866
    assert result["input"]["family_first_signal_date"] == "2007-06-01"
    assert result["input"]["coverage_excluded_events"] == 39
    assert result["input"]["coverage_missing_symbols"] == ["MA"]
    assert result["input"]["common_model_event_indices"] is True
    assert result["reconstruction"]["maximum_return_residual"] <= 1e-12
    assert result["protocol"]["initial_parent_protocol_run"] == {
        "status": "failed_closed_before_output",
        "error_code": "common_risk_beta_window_mismatch",
    }
    assert result["protocol"]["coverage_repair"]["independent_first_unseen_evidence"] is False


def test_beta_coverage_and_decomposition_are_exact(result: dict) -> None:
    coverage = result["beta_coverage"]
    assert coverage["events"] == 866
    assert coverage["beta_cells"] == coverage["expected_beta_cells"] == 86_600
    assert coverage["all_complete"] is True
    assert result["maximum_decomposition_residual"] <= 1e-12
    assert all(
        row["maximum_decomposition_residual"] <= 1e-12 for row in result["beta_gap_summaries"]
    )


def test_near_zero_signs_and_negative_zero_are_platform_stable() -> None:
    values = np.asarray([-5e-13, 5e-13, 2e-12], dtype=float)
    comparison = _comparison(
        values,
        pd.Series(pd.to_datetime(["2026-01-01", "2026-01-02", "2026-01-03"])),
        include_halves=False,
    )
    assert comparison["positive_fraction"] == pytest.approx(1 / 3)
    assert _canonicalize_floats(-5e-13) == 0.0
    assert str(_canonicalize_floats(-5e-13)) == "0.0"


def test_ten_hypothesis_family_preserves_unfavourable_baselines(result: dict) -> None:
    rows = {row["id"]: row for row in result["family"]["comparisons"]}
    assert len(rows) == result["family"]["size"] == 10
    assert set(rows) == {
        f"{model}__{baseline}"
        for model in ("RAW", "QQQ_60", "QQQ_252", "SPY_252", "COHORT_252")
        for baseline in ("eligible", "complete_cohort")
    }
    assert rows["RAW__eligible"]["mean_difference"] == pytest.approx(0.003130685887)
    assert rows["RAW__eligible"]["newey_west"]["t_stat"] == pytest.approx(2.878319, abs=1e-6)
    assert rows["RAW__complete_cohort"]["newey_west"]["t_stat"] == pytest.approx(1.781080, abs=1e-6)
    assert rows["QQQ_252__eligible"]["mean_difference"] == pytest.approx(0.002284827090)
    assert rows["QQQ_252__eligible"]["newey_west"]["t_stat"] == pytest.approx(2.445587, abs=1e-6)
    assert rows["QQQ_252__eligible"]["holm_adjusted_p"] == pytest.approx(0.130155, abs=1e-6)
    assert rows["QQQ_252__eligible"]["bootstrap_max_t_p"] == pytest.approx(0.052397, abs=1e-6)
    assert rows["QQQ_252__complete_cohort"]["newey_west"]["t_stat"] == pytest.approx(
        1.356765, abs=1e-6
    )
    assert rows["COHORT_252__eligible"]["newey_west"]["t_stat"] == pytest.approx(1.510623, abs=1e-6)
    assert rows["COHORT_252__complete_cohort"]["newey_west"]["t_stat"] == pytest.approx(
        0.658078, abs=1e-6
    )


def test_beta_gap_and_regime_stresses_fail_closed(result: dict) -> None:
    gap = next(row for row in result["beta_gap_summaries"] if row["id"] == "QQQ_252__eligible")
    assert gap["median_absolute_beta_gap"] == pytest.approx(0.108013921655)
    assert gap["p95_absolute_beta_gap"] == pytest.approx(0.403578984405)
    assert gap["beta_contribution_share_of_raw_mean"] == pytest.approx(0.270183221048)

    regimes = result["primary_stresses"]["qqq_forward_regimes_ex_post_not_a_signal"]
    assert regimes["qqq_nonnegative"]["events"] == 581
    assert regimes["qqq_nonnegative"]["newey_west"]["t_stat"] == pytest.approx(2.586328678396)
    assert regimes["qqq_negative"]["events"] == 285
    assert regimes["qqq_negative"]["newey_west"]["t_stat"] == pytest.approx(0.70239991493)

    tail = result["primary_stresses"]["remove_largest_absolute_beta_contribution"]
    assert tail["removed_events"] == 46
    assert tail["events"] == 820
    assert tail["newey_west"]["t_stat"] == pytest.approx(2.198651736891)
    assert tail["removed_absolute_beta_contribution_share"] == pytest.approx(0.272510932778)


def test_current_sector_labels_are_caution_only(result: dict) -> None:
    diagnostic = result["current_sector_label_diagnostic"]
    assert diagnostic["identifier_scope"] == "2026_current_sector_labels_not_point_in_time"
    assert diagnostic["investment_role"] == "one_way_caution_not_promotion_evidence"
    assert len(diagnostic["event_rows"]) == 866
    summary = diagnostic["summary"]
    assert summary["median_unique_current_sectors"] == 4
    assert summary["median_effective_current_sectors"] == pytest.approx(3.266666666667)
    assert summary["events_with_current_sector_majority_fraction"] == pytest.approx(0.301385681293)


def test_fourteen_gates_reject_promotion(result: dict) -> None:
    assert result["gate_summary"] == {"passed": 6, "total": 14, "all_passed": False}
    failed = {row["id"] for row in result["gates"] if not row["passed"]}
    assert failed == {
        "median_absolute_qqq_beta_gap",
        "p95_absolute_qqq_beta_gap",
        "qqq252_complete",
        "spy252_complete",
        "cohort252_eligible",
        "cohort252_complete",
        "adjusted_family_correction",
        "qqq_up_down_regimes",
    }
    decision = result["decision"]
    assert decision["can_promote_from_this_round"] is False
    assert decision["new_strategy_created"] is False
    assert decision["formal_strategy_runs"] == 0
    assert decision["paper_status"] == "all_cash_not_started"
    assert decision["paper_positions"] == 0
    assert decision["real_money_action_usd"] == 0


def test_controls_and_single_field_attacks_are_complete(result: dict) -> None:
    assert result["control_summary"] == {"passed": 21, "total": 21, "all_passed": True}
    assert result["attack_summary"] == {"rejected": 21, "total": 21, "all_rejected": True}
    attacks = run_contract_attacks()
    assert len(attacks) == 21
    assert all(row["rejected"] for row in attacks)
    assert attacks[-1]["expected_error_code"] == "common_risk_coverage_repair_mismatch"


def test_generated_receipts_are_identical_and_match_calculation(result: dict) -> None:
    assert ARTIFACT.read_bytes() == SITE_DATA.read_bytes()
    assert re.search(rb": -0\.0(?:[,}\n])", ARTIFACT.read_bytes()) is None
    stored = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    assert stored["research_round"] == result["research_round"] == 26
    assert stored["gate_summary"] == result["gate_summary"]
    assert stored["decision"]["formal_global_search_trials_unchanged"] == 6208
