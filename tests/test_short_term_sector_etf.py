from __future__ import annotations

import json
from pathlib import Path

import pytest

from usfddk.data import load_snapshot
from usfddk.short_term_sector_etf import (
    SECTOR_ARCHIVE_SHA256,
    SECTOR_MAPPING_SHA256,
    SECTOR_PANEL_SHA256,
    SECTOR_PROTOCOL_SHA256,
    build_short_term_sector_etf_research,
)

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = (
    ROOT
    / "artifacts/snapshot_short_term_sector_vanguard_20040923_20260731_7a13b864.zip"
)
DATA_RECEIPT = ROOT / "artifacts/short_term_sector_etf_data_receipt.json"
RESULT = ROOT / "artifacts/short_term_sector_etf_validation.json"
SITE_RESULT = ROOT / "site/data/short-term-sector-etf.json"


@pytest.fixture(scope="module")
def calculated() -> dict:
    panel, _ = load_snapshot(SNAPSHOT)
    receipt = json.loads(DATA_RECEIPT.read_text(encoding="utf-8"))
    return build_short_term_sector_etf_research(
        panel,
        snapshot_path=SNAPSHOT,
        data_receipt=receipt,
    )


def test_frozen_external_result_is_reproducible(calculated: dict) -> None:
    saved = json.loads(RESULT.read_text(encoding="utf-8"))
    assert calculated == saved

    site = json.loads(SITE_RESULT.read_text(encoding="utf-8"))
    expected_site = json.loads(json.dumps(saved))
    expected_site["fixed_20_day_signal_external_diagnostic"].pop("event_series")
    assert site == expected_site


def test_snapshot_and_protocol_provenance_are_preserved(calculated: dict) -> None:
    assert calculated["protocol"]["sha256"] == SECTOR_PROTOCOL_SHA256
    assert calculated["protocol"]["mapping_sha256"] == SECTOR_MAPPING_SHA256
    assert calculated["snapshot"]["panel_sha256"] == SECTOR_PANEL_SHA256
    assert calculated["snapshot"]["archive_sha256"] == SECTOR_ARCHIVE_SHA256
    assert calculated["snapshot"]["first_joint_vanguard_sector_download"] is True
    assert not any(calculated["snapshot"]["formal_ohlcv_missing_cells"].values())
    assert all(calculated["data_gates"].values())


def test_negative_external_result_cannot_create_paper(calculated: dict) -> None:
    assert calculated["status"] == "external_sector_product_validation_failed"
    assert calculated["external_product_validation_passed"] is False
    assert calculated["paper_eligible"] is False
    assert calculated["paper_state_created"] is False
    assert calculated["trade_ready"] is False
    assert calculated["real_money_action_usd"] == 0
    assert calculated["passed_gate_count"] == 7
    assert calculated["required_gate_count"] == 21


def test_candidate_loses_to_hard_baselines_and_cost_stress(calculated: dict) -> None:
    candidate = calculated["frozen_candidate"]
    baselines = calculated["baselines"]
    assert candidate["metrics"]["cagr"] == pytest.approx(0.052810313182776625)
    assert baselines["QQQ"]["cagr"] == pytest.approx(0.1673054181509217)
    assert baselines["matched_equity_exposure_equal_sector"]["cagr"] > candidate[
        "metrics"
    ]["cagr"]
    assert baselines["sector_monthly_equal"]["cagr"] > candidate["metrics"]["cagr"]
    assert baselines["sector_start_equal_then_drift"]["cagr"] > candidate[
        "metrics"
    ]["cagr"]
    assert candidate["cost_sensitivity"]["50_bps"]["cagr"] < 0
    assert calculated["rolling_three_year_vs_qqq"]["cagr_win_fraction"] < 0.01
    assert calculated["rolling_five_year_vs_qqq"]["cagr_win_fraction"] == 0


def test_signal_layer_fails_all_preregistered_gates(calculated: dict) -> None:
    signal = calculated["fixed_20_day_signal_external_diagnostic"]
    comparison = signal["comparisons"]["eligible_equal"]
    assert signal["events"] == 874
    assert comparison["mean_difference"] < 0
    assert comparison["newey_west"]["t_stat"] < 0
    assert signal["passed_gate_count"] == 0
    assert signal["required_gate_count"] == 5
    assert not any(signal["gates"].values())
    assert calculated["pbo_across_top_k_2_3_4"]["pbo"] > 0.20


def test_best_sector_is_ex_post_diagnostic_only(calculated: dict) -> None:
    best = calculated["best_individual_sector_ex_post_not_a_candidate"]
    assert best["ticker"] == "VGT"
    assert best["metrics"]["cagr"] > calculated["baselines"]["QQQ"]["cagr"]
    assert "current_target" not in calculated
