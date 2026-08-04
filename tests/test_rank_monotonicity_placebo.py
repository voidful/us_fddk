from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import pytest

from scripts.build_short_term_rank_monotonicity_placebo_report import _canonicalize_floats
from usfddk.rank_monotonicity_placebo import (
    FROZEN_CONTRACT,
    PROTOCOL_PATH,
    PROTOCOL_SHA256,
    run_contract_attacks,
    run_rank_monotonicity_placebo,
    validate_rank_monotonicity_contract,
)

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "artifacts/short_term_rank_monotonicity_placebo_validation.json"
SITE_DATA = ROOT / "site/data/short-term-rank-monotonicity-placebo.json"


@pytest.fixture(scope="module")
def result() -> dict:
    return run_rank_monotonicity_placebo(ROOT)


def test_protocol_was_frozen_before_outcome_calculation() -> None:
    assert hashlib.sha256((ROOT / PROTOCOL_PATH).read_bytes()).hexdigest() == PROTOCOL_SHA256
    validate_rank_monotonicity_contract(FROZEN_CONTRACT)


def test_all_905_events_are_reconstructed_without_coverage_repair(result: dict) -> None:
    assert result["input"]["events"] == 905
    assert result["input"]["first_signal_date"] == "2006-08-04"
    assert result["input"]["last_signal_date"] == "2026-07-02"
    assert result["input"]["eligible_count"] == {"minimum": 7, "median": 17.0, "maximum": 25}
    assert result["reconstruction"]["maximum_return_residual"] <= 1e-12
    assert result["reconstruction"]["maximum_contribution_identity_residual"] <= 1e-12
    assert len(result["event_rows"]) == 905


def test_bucket_partitions_are_exact_and_replay_stable(result: dict) -> None:
    assert (
        result["bucket_assignment_sha256"]
        == "0f1512ccc893f554028b77de85af146e53333e1badd528fb00089878d49e8ffd"
    )
    for event in result["event_rows"]:
        for universe_id, universe in event["universes"].items():
            ranked = universe["ranked"]
            buckets = universe["buckets"]
            flattened = buckets["top"] + buckets["middle"] + buckets["bottom"]
            assert flattened == ranked
            assert len(flattened) == len(set(flattened)) == universe["count"]
            sizes = [len(buckets[bucket]) for bucket in ("top", "middle", "bottom")]
            assert max(sizes) - min(sizes) <= 1
            if universe_id == "complete":
                assert sizes == [9, 8, 8]


def test_eight_hypothesis_family_keeps_unfavourable_ranks(result: dict) -> None:
    rows = {row["id"]: row for row in result["family"]["comparisons"]}
    assert result["family"]["size"] == len(rows) == 8
    assert rows["eligible_top_middle"]["mean"] == pytest.approx(0.005163622595)
    assert rows["eligible_top_middle"]["newey_west"]["t_stat"] == pytest.approx(2.56517594566)
    assert rows["eligible_top_middle"]["bootstrap_max_t_p"] == pytest.approx(0.080945952702)
    assert rows["eligible_middle_bottom"]["mean"] == pytest.approx(-0.001454867146)
    assert rows["eligible_top_bottom"]["newey_west"]["t_stat"] == pytest.approx(1.460622557646)
    assert rows["complete_top_middle"]["newey_west"]["t_stat"] == pytest.approx(2.304227464867)
    assert rows["complete_middle_bottom"]["mean"] == pytest.approx(-0.001486196795)
    assert rows["complete_top_bottom"]["newey_west"]["t_stat"] == pytest.approx(1.092435423081)
    assert rows["eligible_rank_ic"]["newey_west"]["t_stat"] == pytest.approx(1.011501617227)
    assert rows["complete_rank_ic"]["newey_west"]["t_stat"] == pytest.approx(1.459753185889)


def test_twenty_placebos_do_not_validate_both_universes(result: dict) -> None:
    eligible = result["placebo"]["eligible"]
    complete = result["placebo"]["complete"]
    assert [row["id"] for row in eligible["rows"]] == [f"P{i:02d}" for i in range(1, 21)]
    assert [row["id"] for row in complete["rows"]] == [f"P{i:02d}" for i in range(1, 21)]
    assert eligible["maximum_placebo_mean_id"] == eligible["maximum_placebo_t_id"] == "P06"
    assert eligible["maximum_placebo_t"] == pytest.approx(1.071389201028)
    assert eligible["mean_dominates"] is eligible["t_dominates"] is True
    assert complete["maximum_placebo_mean_id"] == complete["maximum_placebo_t_id"] == "P14"
    assert complete["maximum_placebo_t"] == pytest.approx(1.21716640169)
    assert complete["mean_dominates"] is True
    assert complete["t_dominates"] is False


def test_market_and_tail_stresses_reject_promotion(result: dict) -> None:
    regimes = result["primary_stresses"]["qqq_forward_regimes_ex_post_not_a_signal"]
    assert regimes["eligible"]["qqq_nonnegative"]["events"] == 610
    assert regimes["eligible"]["qqq_nonnegative"]["newey_west"]["t_stat"] == pytest.approx(
        2.860169866136
    )
    assert regimes["eligible"]["qqq_negative"]["events"] == 295
    assert regimes["eligible"]["qqq_negative"]["mean"] == pytest.approx(-0.006466335852)
    assert regimes["complete"]["qqq_negative"]["mean"] == pytest.approx(-0.001831648769)

    tails = result["primary_stresses"]["remove_largest_absolute_spreads"]
    assert tails["eligible"]["events"] == tails["complete"]["events"] == 859
    assert tails["eligible"]["newey_west"]["t_stat"] == pytest.approx(1.459935088081)
    assert tails["complete"]["newey_west"]["t_stat"] == pytest.approx(1.929761917859)


def test_fourteen_gates_keep_paper_all_cash(result: dict) -> None:
    assert result["gate_summary"] == {"passed": 5, "total": 14, "all_passed": False}
    assert {row["id"] for row in result["gates"] if not row["passed"]} == {
        "eligible_middle_bottom",
        "eligible_top_bottom",
        "complete_middle_bottom",
        "complete_top_bottom",
        "rank_ic_both_universes",
        "adjusted_family_correction",
        "placebo_dominance_both_universes",
        "qqq_up_down_both_universes",
        "remove_top_spreads_both_universes",
    }
    decision = result["decision"]
    assert decision["new_strategy_created"] is False
    assert decision["can_promote_from_this_round"] is False
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
    assert attacks[-4]["expected_error_code"] == "rank_monotonicity_placebo_contract_mismatch"
    assert attacks[-1]["expected_error_code"] == "rank_monotonicity_decision_boundary_breached"


def test_generated_receipts_are_identical_and_platform_stable(result: dict) -> None:
    assert ARTIFACT.read_bytes() == SITE_DATA.read_bytes()
    assert re.search(rb": -0\.0(?:[,}\n])", ARTIFACT.read_bytes()) is None
    assert _canonicalize_floats(-5e-13) == 0.0
    stored = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    assert stored["research_round"] == result["research_round"] == 27
    assert stored["gate_summary"] == result["gate_summary"]
    assert stored["decision"]["formal_global_search_trials_unchanged"] == 6208
