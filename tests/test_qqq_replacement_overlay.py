from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import pytest

from scripts.build_short_term_qqq_replacement_overlay_report import _canonicalize_floats
from usfddk.qqq_replacement_overlay import (
    FROZEN_CONTRACT,
    PROTOCOL_PATH,
    PROTOCOL_SHA256,
    run_contract_attacks,
    run_qqq_replacement_overlay,
    validate_qqq_replacement_overlay_contract,
)

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "artifacts/short_term_qqq_replacement_overlay_validation.json"
SITE_DATA = ROOT / "site/data/short-term-qqq-replacement-overlay.json"
REPORT = ROOT / "docs/SHORT_TERM_QQQ_REPLACEMENT_OVERLAY_RESEARCH_REPORT.md"


@pytest.fixture(scope="module")
def result() -> dict:
    return run_qqq_replacement_overlay(ROOT)


def test_protocol_was_frozen_and_pushed_before_round30_results() -> None:
    assert hashlib.sha256((ROOT / PROTOCOL_PATH).read_bytes()).hexdigest() == PROTOCOL_SHA256
    assert FROZEN_CONTRACT.protocol_commit == "bf52098e8ff5919cf5afff262e982be281fc488c"
    validate_qqq_replacement_overlay_contract(FROZEN_CONTRACT)


def test_reconstructs_parent_events_and_four_leg_overlay(result: dict) -> None:
    assert result["input"]["events"] == 905
    assert result["input"]["first_entry_date"] == "2006-08-07"
    assert result["input"]["last_exit_date"] == "2026-07-31"
    assert result["reconstruction"]["slot_event_counts"] == [181] * 5
    assert result["reconstruction"]["maximum_concurrent_intervals"] == 5
    assert result["calendar_integrity"]["candidate_total_transaction_legs"] == 3626
    assert result["method"]["normal_event_transaction_legs"] == 4
    assert result["method"]["normal_event_total_nominal_cost_bps"] == 40


def test_daily_paths_are_fully_invested_without_leverage(result: dict) -> None:
    integrity = result["calendar_integrity"]
    assert integrity["sessions"] == 5028
    assert integrity["maximum_daily_identity_residual"] <= 1e-12
    assert integrity["maximum_driver_identity_residual"] <= 1e-12
    assert integrity["maximum_qqq_placebo_residual"] <= 1e-12
    assert integrity["post_entry_maximum_cash_value"] <= 1e-12
    assert integrity["maximum_exposure"] == pytest.approx(1.0)
    assert len(result["calendar_rows"]) == 5028


def test_headline_beats_qqq_but_is_not_promoted(result: dict) -> None:
    paths = result["paths"]
    candidate = paths["top7_qqq_overlay"]
    qqq = paths["qqq_buy_hold"]
    assert candidate["terminal_usd"] == pytest.approx(27067.126762245793)
    assert candidate["cagr"] == pytest.approx(0.17939661229189552)
    assert candidate["shy_excess_sharpe"] == pytest.approx(0.7392373677417544)
    assert candidate["max_drawdown"] == pytest.approx(-0.5248145820006294)
    assert qqq["terminal_usd"] == pytest.approx(21797.40437742496)
    assert qqq["cagr"] == pytest.approx(0.1666901406073944)
    assert candidate["cagr"] > qqq["cagr"]
    assert result["decision"]["can_promote_from_this_round"] is False
    assert result["decision"]["new_strategy_created"] is False


def test_seven_baseline_family_rejects_qqq_statistical_claim(result: dict) -> None:
    family = result["family"]
    rows = {row["baseline_id"]: row for row in family["comparisons"]}
    assert family["size"] == len(rows) == 7
    qqq = rows["qqq_buy_hold"]
    assert qqq["newey_west"]["t_stat"] == pytest.approx(0.6561697482161137)
    assert qqq["holm_adjusted_p"] == pytest.approx(0.5117149110974148)
    assert qqq["bootstrap_max_t_p"] == pytest.approx(0.9368031598420079)
    assert qqq["global_bonferroni_p"] == pytest.approx(1.0)
    assert rows["eligible_qqq_overlay"]["newey_west"]["t_stat"] == pytest.approx(
        2.7726525901010115
    )
    assert rows["complete_qqq_overlay"]["newey_west"]["t_stat"] == pytest.approx(
        1.5661516818989005
    )
    assert family["common_bootstrap"]["seed"] == 30_202_608
    assert family["global_search_trials"] == 6_221


def test_time_event_tail_and_cost_stresses_reverse_headline(result: dict) -> None:
    years = result["stresses"]["best_three_years_removed"]
    assert years["removed_years"] == [2026, 2025, 2016]
    assert years["newey_west"]["t_stat"] == pytest.approx(-0.9719732893260791)
    assert years["mean_daily_difference"] < 0.0
    event_tail = result["stresses"]["favorable_46_events_removed"]
    assert event_tail["removed_event_count"] == 46
    assert event_tail["candidate_cagr_differences"]["qqq_buy_hold"] == pytest.approx(
        -0.03758739850338211
    )
    assert event_tail["candidate_cagr_differences"]["complete_qqq_overlay"] < 0.0
    costs = result["stresses"]["costs"]
    assert costs["50"]["candidate_cagr_differences"]["qqq_buy_hold"] == pytest.approx(
        -0.04984533055279394
    )
    assert costs["100"]["candidate_cagr_differences"]["qqq_buy_hold"] == pytest.approx(
        -0.14699711835533824
    )


def test_twenty_gates_keep_paper_and_real_money_at_zero(result: dict) -> None:
    assert result["gate_summary"] == {"passed": 13, "total": 20, "all_passed": False}
    assert {row["id"] for row in result["gates"] if not row["passed"]} == {
        "nw_vs_complete",
        "nw_vs_qqq",
        "holm_and_max_t_vs_qqq",
        "fixed_halves",
        "best_three_years_removed",
        "crisis_periods",
        "global_cost_and_event_tail",
    }
    decision = result["decision"]
    assert decision["not_rejected_by_round30"] is False
    assert decision["formal_strategy_runs"] == 0
    assert decision["paper_status"] == "all_cash_not_started"
    assert decision["paper_positions"] == 0
    assert decision["real_money_action_usd"] == 0


def test_controls_and_contract_attacks_are_complete(result: dict) -> None:
    assert result["control_summary"] == {"passed": 29, "total": 29, "all_passed": True}
    assert result["attack_summary"] == {"rejected": 29, "total": 29, "all_rejected": True}
    attacks = run_contract_attacks()
    assert len(attacks) == 29
    assert all(row["rejected"] for row in attacks)


def test_generated_receipts_are_canonical_and_identical(result: dict) -> None:
    expected = _canonicalize_floats({**result, "receipt_float_decimal_places": 12})
    assert json.loads(ARTIFACT.read_text(encoding="utf-8")) == expected
    assert SITE_DATA.read_bytes() == ARTIFACT.read_bytes()
    payload = ARTIFACT.read_text(encoding="utf-8")
    assert re.search(r"(?<![\d.])-0\.0(?:[,\n])", payload) is None


def test_report_states_positive_headline_and_rejection() -> None:
    report = REPORT.read_text(encoding="utf-8")
    assert "US$27,067" in report
    assert "US$21,797" in report
    assert "13/20" in report
    assert "headline 終值高於 QQQ" in report
    assert "短線 Paper 維持全現金" in report
    assert "實金動作 **US$0**" in report
