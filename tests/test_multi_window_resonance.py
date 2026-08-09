from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from usfddk.multi_window_resonance import (
    BOOTSTRAP_PATHS,
    BOOTSTRAP_SEED,
    FAMILY_BASELINE_IDS,
    FROZEN_CONTRACT,
    PATH_IDS,
    PROTOCOL_PATH,
    PROTOCOL_SHA256,
    run_contract_attacks,
    run_multi_window_resonance,
    validate_multi_window_resonance_contract,
)

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def result() -> dict:
    return run_multi_window_resonance(ROOT)


def test_protocol_was_frozen_before_the_first_round38_calculation() -> None:
    assert hashlib.sha256((ROOT / PROTOCOL_PATH).read_bytes()).hexdigest() == PROTOCOL_SHA256
    assert FROZEN_CONTRACT.protocol_commit == "9d937340356c7352f67f61a484827a65506c216b"
    validate_multi_window_resonance_contract(FROZEN_CONTRACT)


def test_four_window_rank_sum_and_partial_allocation_are_exact(result: dict) -> None:
    assert result["input"]["events"] == 905
    assert result["reconstruction"]["slot_event_counts"] == [181] * 5
    assert result["method"]["resonance_windows"] == [5, 10, 15, 20]
    assert result["method"]["resonance_minimum_windows"] == 3
    assert result["method"]["stock_subslots"] == 7
    distribution = result["selection_distribution"]
    assert sum(row["events"] for row in distribution["candidate_count_histogram"]) == 905
    assert 0 <= distribution["minimum_candidates"] <= distribution["maximum_candidates"] <= 7
    assert distribution["maximum_allocation_residual"] <= 1e-12
    receipts = result["selection_receipts"]
    assert len(receipts) == 905
    for row in receipts:
        assert row["stock_target_fraction"] == pytest.approx(row["candidate_count"] / 7)
        assert row["qqq_target_fraction"] == pytest.approx(1 - row["candidate_count"] / 7)
        assert row["candidate_count"] == len(row["selected"])
        assert all(item["resonance_count"] >= 3 for item in row["selected_details"])


def test_nine_paths_preserve_daily_identity_and_parent_identity(result: dict) -> None:
    assert tuple(result["paths"]) == PATH_IDS
    integrity = result["calendar_integrity"]
    assert integrity["sessions"] == 5028
    assert integrity["maximum_daily_identity_residual"] <= 1e-12
    assert integrity["maximum_driver_identity_residual"] <= 1e-12
    assert integrity["maximum_cost_identity_residual"] <= 1e-12
    assert integrity["maximum_original_top7_parent_residual"] <= 1e-12
    assert (
        integrity["maximum_original_top7_parent_stress_normalized_metric_residual"]
        <= 1e-12
    )
    assert integrity["maximum_qqq_placebo_residual"] <= 1e-12
    assert (
        integrity["qqq_placebo_identity_method"]
        == "independent_analytical_qqq_price_and_partial_cost_reconstruction"
    )
    assert integrity["post_entry_maximum_cash_value"] <= 1e-12
    assert integrity["maximum_exposure"] <= 1.0 + 1e-12


def test_eight_hypothesis_family_is_frozen(result: dict) -> None:
    family = result["family"]
    assert family["size"] == 8
    assert tuple(row["baseline_id"] for row in family["comparisons"]) == FAMILY_BASELINE_IDS
    assert family["global_search_trials"] == 6_229
    assert family["common_bootstrap"]["paths"] == BOOTSTRAP_PATHS == 20_000
    assert family["common_bootstrap"]["seed"] == BOOTSTRAP_SEED == 38_202_608
    assert all(row["newey_west"]["lag"] == 20 for row in family["comparisons"])


def test_first_calculation_preserves_the_negative_incremental_result(result: dict) -> None:
    candidate = result["paths"]["resonance3_qqq_overlay"]
    qqq = result["paths"]["qqq_buy_hold"]
    matched20 = result["paths"]["matched_20d_qqq_overlay"]
    original = result["paths"]["original_top7_qqq_overlay"]
    assert candidate["terminal_usd"] == pytest.approx(22654.014551220454)
    assert candidate["cagr"] == pytest.approx(0.16894206936845046)
    assert qqq["cagr"] == pytest.approx(0.1666901406073944)
    assert matched20["cagr"] == pytest.approx(0.17843979091457207)
    assert original["cagr"] == pytest.approx(0.17939661229189485)
    qqq_test = next(
        row for row in result["family"]["comparisons"] if row["baseline_id"] == "qqq_buy_hold"
    )
    assert qqq_test["newey_west"]["t_stat"] == pytest.approx(0.1866489767553852)
    assert qqq_test["holm_adjusted_p"] == pytest.approx(0.8519358635731196)
    assert qqq_test["bootstrap_max_t_p"] == pytest.approx(1.0)
    assert result["gate_summary"] == {"passed": 11, "total": 20, "all_passed": False}
    assert {row["id"] for row in result["gates"] if not row["passed"]} == {
        "candidate_sharpe_vs_qqq",
        "candidate_cagr_vs_original",
        "candidate_cagr_vs_matched20",
        "statistical_vs_qqq",
        "statistical_vs_matched",
        "fixed_halves",
        "best_three_years_removed",
        "crisis_and_regimes",
        "global_cost_and_tail",
    }


def test_all_preregistered_stresses_are_present(result: dict) -> None:
    stresses = result["stresses"]
    assert len(stresses["best_three_years_removed"]["removed_years"]) == 3
    assert set(stresses["crisis_years"]) == {"2008", "2020", "2022"}
    assert set(stresses["known_at_qqq_regimes"]) == {"nonnegative", "negative"}
    assert set(stresses["costs"]) == {"50", "100"}
    assert stresses["favorable_46_events_removed"]["removed_event_count"] == 46
    assert len(stresses["favorable_46_events_removed"]["paths"]) == 6


def test_twenty_gates_never_authorize_paper_or_real_money(result: dict) -> None:
    assert result["gate_summary"]["total"] == 20
    assert result["decision"]["can_promote_from_this_round"] is False
    assert result["decision"]["new_strategy_created"] is False
    assert result["decision"]["formal_strategy_runs"] == 0
    assert result["decision"]["paper_status"] == "all_cash_not_started"
    assert result["decision"]["paper_positions"] == 0
    assert result["decision"]["real_money_action_usd"] == 0


def test_at_least_34_controls_and_single_field_attacks_pass(result: dict) -> None:
    assert result["control_summary"]["total"] >= 34
    assert result["control_summary"]["all_passed"] is True
    assert result["attack_summary"]["total"] >= 34
    assert result["attack_summary"]["all_rejected"] is True
    attacks = run_contract_attacks()
    assert all(row["rejected"] for row in attacks)
