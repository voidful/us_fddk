from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from usfddk.french_prior_return_research import (
    DECILE_COLUMNS,
    FORMAL_END,
    FORMAL_START,
    TABLE_MARKERS,
    apply_buy_and_hold_entry_cost,
    apply_full_reconstitution_cost,
    build_french_prior_return_schema_repair_research,
    load_frozen_prior_return_data,
    parse_exact_monthly_table,
)

ROOT = Path(__file__).resolve().parents[1]


def test_exact_schema_repair_parser_accepts_only_frozen_observed_marker() -> None:
    data = load_frozen_prior_return_data(ROOT)
    assert list(data["short_value"].columns) == DECILE_COLUMNS
    assert data["markers"]["short_value"] == TABLE_MARKERS["short_value"]

    archive = ROOT / "artifacts/french_10_prior_1_0_monthly_20b186f6.zip"
    import zipfile

    with zipfile.ZipFile(archive) as bundle:
        text = bundle.read("10_Portfolios_Prior_1_0.csv").decode("latin-1")
    with pytest.raises(ValueError, match="精確月表 marker"):
        parse_exact_monthly_table(text, "Average Value Weighted Returns -- Monthly")


def test_frozen_formal_monthly_data_are_complete_and_contiguous() -> None:
    data = load_frozen_prior_return_data(ROOT)
    expected = pd.period_range(FORMAL_START, FORMAL_END, freq="M")
    assert data["common_index"].equals(expected)
    assert len(expected) == 761
    assert all(
        not data[key].isna().any().any()
        for key in ("short_value", "short_equal", "long_value", "long_equal", "factors")
    )


def test_frozen_cost_formula_charges_one_side_then_two_sides() -> None:
    index = pd.period_range("2020-01", periods=3, freq="M")
    gross = pd.Series([0.10, -0.05, 0.02], index=index)
    recurring = apply_full_reconstitution_cost(gross, 10.0)
    market = apply_buy_and_hold_entry_cost(gross, 10.0)
    assert recurring.returns.iloc[0] == pytest.approx((1 - 0.001) * 1.10 - 1)
    assert recurring.returns.iloc[1] == pytest.approx((1 - 0.001) ** 2 * 0.95 - 1)
    assert recurring.turnover.tolist() == [1.0, 2.0, 2.0]
    assert market.returns.iloc[0] == pytest.approx((1 - 0.001) * 1.10 - 1)
    assert market.returns.iloc[1] == pytest.approx(-0.05)
    assert market.turnover.tolist() == [1.0, 0.0, 0.0]


def test_schema_informed_result_never_promotes_to_paper_or_independent_evidence() -> None:
    result = build_french_prior_return_schema_repair_research(ROOT)
    assert result["schema_repair_engineering_passed"] is True
    assert result["independent_first_seen_evidence"] is False
    assert result["paper_eligible"] is False
    assert result["paper_state_created"] is False
    assert result["trade_ready"] is False
    assert result["real_money_action_usd"] == 0
    assert result["required_gate_count"] == 38
    assert result["passed_gate_count"] == (
        sum(result["data_gates"].values())
        + result["primary_external_period"]["passed_gate_count"]
        + result["recent_confirmation_period"]["passed_gate_count"]
    )
