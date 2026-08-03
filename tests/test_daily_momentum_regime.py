from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from scripts.build_short_term_daily_momentum_regime_report import _site_summary
from usfddk.daily_momentum_regime import (
    PRIOR_COLUMNS,
    build_daily_momentum_regime_research,
    build_exposure_signals,
    load_frozen_daily_momentum_data,
)

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def result() -> dict[str, object]:
    return build_daily_momentum_regime_research(ROOT)


def test_frozen_receipts_preserve_the_original_failure_and_repair_boundary() -> None:
    data = load_frozen_daily_momentum_data(ROOT)
    original = data["original_receipt"]
    repair = data["repair_receipt"]

    assert original["passed_check_count"] == 4
    assert original["required_check_count"] == 9
    assert original["numeric_return_rows_parsed"] is False
    assert original["strategy_calculation_started"] is False
    assert repair["schema_seen_before_repair_freeze"] is True
    assert repair["independent_first_seen_evidence"] is False
    assert repair["candidate_or_gate_changed"] is False


def test_repaired_daily_file_has_the_exact_frozen_schema() -> None:
    data = load_frozen_daily_momentum_data(ROOT)
    prior = data["prior"]
    meta = data["prior_meta"]

    assert list(prior.columns) == PRIOR_COLUMNS
    assert meta["marker"] == "Average Value Weighted Returns -- Daily"
    assert meta["first_date"] == "1926-11-03"
    assert meta["last_date"] == "2026-05-29"
    assert meta["raw_missing_codes"] == 0
    assert prior.index.is_monotonic_increasing
    assert not prior.index.has_duplicates
    assert np.isfinite(prior.to_numpy()).all()


def test_exposure_signal_is_lagged_and_cannot_see_same_day_return() -> None:
    index = pd.bdate_range("2020-01-01", periods=120)
    base = np.linspace(-0.002, 0.003, len(index))
    prior = pd.DataFrame(
        {column: base + rank * 0.00005 for rank, column in enumerate(PRIOR_COLUMNS)},
        index=index,
    )
    market = pd.Series(np.linspace(-0.001, 0.002, len(index)), index=index)
    changed_prior = prior.copy()
    changed_market = market.copy()
    mutation_date = index[85]
    changed_prior.loc[mutation_date, :] = -0.80
    changed_market.loc[mutation_date] = -0.80

    original = build_exposure_signals(prior, market)
    changed = build_exposure_signals(changed_prior, changed_market)

    pd.testing.assert_frame_equal(
        original.loc[:mutation_date],
        changed.loc[:mutation_date],
    )
    assert not original.loc[mutation_date:].equals(changed.loc[mutation_date:])


def test_round_ten_result_is_frozen_negative_evidence(result: dict[str, object]) -> None:
    assert result["status"] == "daily_momentum_regime_schema_repair_diagnostic_failed"
    assert result["passed_gate_count"] == 27
    assert result["required_gate_count"] == 48
    assert sum(result["data_gates"].values()) == 10
    assert sum(result["early_gates"].values()) == 10
    assert sum(result["recent_gates"].values()) == 5
    assert sum(result["mechanism_gates"].values()) == 2
    assert result["paper_eligible"] is False
    assert result["trade_ready"] is False
    assert result["paper_state_created"] is False
    assert result["paper_position_count"] == 0
    assert result["real_money_action_usd"] == 0
    assert result["point_in_time_stock_ledger_readiness"] == "1/20"


def test_recent_candidate_loses_to_fixed_baselines_and_both_halves(
    result: dict[str, object],
) -> None:
    recent = result["recent_20y"]
    candidate = recent["candidate_metrics"]
    baselines = recent["baseline_metrics"]

    assert candidate["cagr"] == pytest.approx(0.005799881392)
    assert candidate["excess_sharpe"] == pytest.approx(0.018920562636)
    assert baselines["qqq"]["cagr"] == pytest.approx(0.168052574403)
    assert baselines["raw_hi_prior"]["cagr"] == pytest.approx(0.082531243621)
    assert baselines["matched_market_exposure"]["cagr"] == pytest.approx(0.043438669633)
    assert candidate["cagr"] < baselines["qqq"]["cagr"]
    assert candidate["cagr"] < baselines["raw_hi_prior"]["cagr"]
    assert all(row["cagr_difference"] < 0 for row in recent["fixed_halves"].values())
    assert recent["rolling_three_year"]["cagr_win_fraction"] < 0.05


def test_exposure_is_discrete_unlevered_and_cost_grid_is_monotonic(
    result: dict[str, object],
) -> None:
    recent = result["recent_20y"]
    fractions = recent["exposure_diagnostics"]["state_fraction"]
    assert set(fractions) == {"0.0", "0.5", "1.0"}
    assert sum(fractions.values()) == pytest.approx(1.0)
    assert 0.0 <= recent["candidate_metrics"]["minimum_exposure"]
    assert recent["candidate_metrics"]["maximum_exposure"] <= 1.0

    grid = {
        (row["annual_drag"], row["overlay_cost_bps"]): row["metrics"]["cagr"]
        for row in recent["cost_and_drag_grid"]
    }
    for drag in (0.02, 0.05, 0.10):
        assert grid[(drag, 10.0)] > grid[(drag, 25.0)] > grid[(drag, 50.0)]
    for cost in (10.0, 25.0, 50.0):
        assert grid[(0.02, cost)] > grid[(0.05, cost)] > grid[(0.10, cost)]


def test_published_summary_matches_the_frozen_full_result(result: dict[str, object]) -> None:
    published = json.loads(
        (ROOT / "site/data/short-term-daily-momentum-regime.json").read_text(
            encoding="utf-8"
        )
    )
    assert published == _site_summary(result)
    assert published["headline"] == "每日環境共振近期失效：27/48，不建立 Paper"
    assert published["recent"]["candidate"]["hypothetical_1000_usd_end"] == pytest.approx(
        1122.359367232924
    )
