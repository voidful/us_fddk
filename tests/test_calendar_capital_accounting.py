from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import pytest

from scripts.build_short_term_calendar_capital_accounting_report import _canonicalize_floats
from usfddk.calendar_capital_accounting import (
    ASSIGNMENT_SHA256,
    FROZEN_CONTRACT,
    PROTOCOL_PATH,
    PROTOCOL_SHA256,
    run_calendar_capital_accounting,
    run_contract_attacks,
    validate_calendar_capital_contract,
)

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "artifacts/short_term_calendar_capital_accounting_validation.json"
SITE_DATA = ROOT / "site/data/short-term-calendar-capital-accounting.json"
REPORT = ROOT / "docs/SHORT_TERM_CALENDAR_CAPITAL_ACCOUNTING_RESEARCH_REPORT.md"


@pytest.fixture(scope="module")
def result() -> dict:
    return run_calendar_capital_accounting(ROOT)


def test_protocol_was_frozen_and_pushed_before_calendar_results() -> None:
    assert hashlib.sha256((ROOT / PROTOCOL_PATH).read_bytes()).hexdigest() == PROTOCOL_SHA256
    assert FROZEN_CONTRACT.protocol_commit == "65b3789fa7698ddd06639c334339a5c604c3a745"
    validate_calendar_capital_contract(FROZEN_CONTRACT)


def test_reconstructs_the_frozen_905_events_and_five_slots(result: dict) -> None:
    assert result["input"]["events"] == 905
    assert result["input"]["first_signal_date"] == "2006-08-04"
    assert result["input"]["first_entry_date"] == "2006-08-07"
    assert result["input"]["last_signal_date"] == "2026-07-02"
    assert result["input"]["last_exit_date"] == "2026-07-31"
    reconstruction = result["reconstruction"]
    assert reconstruction["assignment_sha256"] == ASSIGNMENT_SHA256
    assert reconstruction["slot_event_counts"] == [181] * 5
    assert reconstruction["maximum_concurrent_intervals"] == 5
    assert reconstruction["maximum_event_return_residual"] <= 1e-12
    assert len(reconstruction["event_receipts"]) == 905


def test_daily_paths_preserve_cash_and_no_leverage(result: dict) -> None:
    integrity = result["calendar_integrity"]
    assert integrity["sessions"] == 5028
    assert integrity["first_date"] == "2006-08-04"
    assert integrity["last_date"] == "2026-07-31"
    assert integrity["maximum_event_terminal_residual"] <= 1e-12
    assert integrity["maximum_daily_identity_residual"] <= 1e-12
    assert integrity["minimum_cash_value"] >= -1e-12
    assert integrity["maximum_exposure"] <= 1.0 + 1e-12
    assert len(result["calendar_rows"]) == 5028
    assert result["calendar_rows"][0]["top7_cash_value"] == pytest.approx(1.0)


def test_calendar_performance_keeps_qqq_and_spy_baselines_visible(result: dict) -> None:
    paths = result["paths"]
    assert paths["top7_five_slot"]["terminal_usd"] == pytest.approx(10189.007312293306)
    assert paths["top7_five_slot"]["cagr"] == pytest.approx(0.1231381371627891)
    assert paths["top7_five_slot"]["shy_excess_sharpe"] == pytest.approx(
        0.6728648972964388
    )
    assert paths["top7_five_slot"]["max_drawdown"] == pytest.approx(-0.38740164036011837)
    assert paths["top7_five_slot"]["average_exposure"] == pytest.approx(
        0.7202744536514116
    )
    assert paths["qqq_buy_hold"]["terminal_usd"] == pytest.approx(21797.40437742496)
    assert paths["qqq_buy_hold"]["cagr"] == pytest.approx(0.1666901406073944)
    assert paths["spy_buy_hold"]["cagr"] == pytest.approx(0.11255971079953775)
    assert paths["shy_buy_hold"]["cagr"] == pytest.approx(0.019410006889724496)


def test_six_baseline_family_applies_hac_and_common_bootstrap(result: dict) -> None:
    family = result["family"]
    rows = {row["baseline_id"]: row for row in family["comparisons"]}
    assert family["size"] == len(rows) == 6
    eligible = rows["eligible_equal_five_slot"]
    assert eligible["newey_west"]["t_stat"] == pytest.approx(2.703909293011861)
    assert eligible["holm_adjusted_p"] == pytest.approx(0.03426449663111447)
    assert eligible["bootstrap_max_t_p"] == pytest.approx(0.03009849507524624)
    assert eligible["global_bonferroni_p"] == pytest.approx(1.0)
    assert rows["complete_equal_five_slot"]["newey_west"]["t_stat"] == pytest.approx(
        1.5099095253996462
    )
    assert rows["qqq_buy_hold"]["mean_daily_difference"] < 0.0
    assert rows["spy_buy_hold"]["newey_west"]["t_stat"] == pytest.approx(
        0.12856560645833842
    )
    bootstrap = family["common_bootstrap"]
    assert bootstrap["block_sessions"] == 63
    assert bootstrap["paths"] == 20_000
    assert bootstrap["seed"] == 29_202_608
    assert bootstrap["common_indices"] is True


def test_time_crisis_and_cost_stresses_reject_promotion(result: dict) -> None:
    removed = result["stresses"]["best_three_years_removed"]
    assert removed["removed_years"] == [2026, 2009, 2025]
    assert removed["remaining_sessions"] == 4381
    assert removed["newey_west"]["t_stat"] == pytest.approx(1.550746646451819)
    crisis = result["stresses"]["crisis_years"]
    assert crisis["2008"]["top7_five_slot"]["return"] == pytest.approx(
        -0.3328902170686696
    )
    assert crisis["2020"]["top7_five_slot"]["return"] == pytest.approx(
        0.07598892334070229
    )
    assert crisis["2022"]["top7_five_slot"]["return"] == pytest.approx(
        -0.25716515931831196
    )
    costs = result["stresses"]["costs"]
    assert costs["50"]["paths"]["top7_five_slot"]["cagr"] == pytest.approx(
        0.09332472652274726
    )
    assert costs["100"]["paths"]["top7_five_slot"]["cagr"] == pytest.approx(
        0.04519680631307632
    )


def test_eighteen_gates_keep_paper_and_real_money_at_zero(result: dict) -> None:
    assert result["gate_summary"] == {"passed": 13, "total": 18, "all_passed": False}
    assert {row["id"] for row in result["gates"] if not row["passed"]} == {
        "candidate_cagr_vs_qqq_buy_hold",
        "nw_vs_complete",
        "fixed_halves",
        "best_three_years_removed",
        "global_and_cost_stress",
    }
    decision = result["decision"]
    assert decision["can_promote_from_this_round"] is False
    assert decision["not_rejected_by_round29"] is False
    assert decision["new_strategy_created"] is False
    assert decision["formal_strategy_runs"] == 0
    assert decision["paper_status"] == "all_cash_not_started"
    assert decision["paper_positions"] == 0
    assert decision["real_money_action_usd"] == 0


def test_controls_and_contract_attacks_are_complete(result: dict) -> None:
    assert result["control_summary"] == {"passed": 25, "total": 25, "all_passed": True}
    assert result["attack_summary"] == {"rejected": 25, "total": 25, "all_rejected": True}
    attacks = run_contract_attacks()
    assert len(attacks) == 25
    assert all(row["rejected"] for row in attacks)
    assert attacks[-1]["expected_error_code"] == "calendar_capital_decision_boundary_breached"


def test_generated_receipts_are_canonical_and_identical(result: dict) -> None:
    expected = _canonicalize_floats({**result, "receipt_float_decimal_places": 12})
    assert json.loads(ARTIFACT.read_text(encoding="utf-8")) == expected
    assert SITE_DATA.read_bytes() == ARTIFACT.read_bytes()
    payload = ARTIFACT.read_text(encoding="utf-8")
    assert re.search(r"(?<![\d.])-0\.0(?:[,\n])", payload) is None


def test_research_report_states_limits_and_all_cash() -> None:
    report = REPORT.read_text(encoding="utf-8")
    assert "US$10,189" in report
    assert "US$21,797" in report
    assert "13/18" in report
    assert "短線 Paper 維持全現金" in report
    assert "實金動作 **US$0**" in report
    assert "不是 2026-08-04 即市行情" in report
