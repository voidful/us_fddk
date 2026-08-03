from __future__ import annotations

import io
import zipfile
from pathlib import Path

import pandas as pd
import pytest

from usfddk.french_size_prior import (
    EQUAL_WEIGHTED_MONTHLY_MARKER,
    SIZE_PRIOR_COLUMNS,
    VALUE_WEIGHTED_MONTHLY_MARKER,
    extract_single_csv,
    parse_size_prior_monthly_table,
)
from usfddk.french_size_prior_research import (
    FORMAL_END,
    FORMAL_START,
    build_french_size_prior_research,
    load_frozen_size_prior_data,
)

ROOT = Path(__file__).resolve().parents[1]


def _synthetic_text(marker: str = VALUE_WEIGHTED_MONTHLY_MARKER) -> str:
    header = "," + ",".join(SIZE_PRIOR_COLUMNS)
    row = "196301," + ",".join(["1.00"] * 25)
    return f"metadata\n{marker}\n{header}\n{row}\n\nAnnual Returns\n"


def test_size_prior_parser_accepts_only_frozen_25_cell_grid() -> None:
    parsed = parse_size_prior_monthly_table(_synthetic_text(), VALUE_WEIGHTED_MONTHLY_MARKER)
    assert list(parsed.frame.columns) == SIZE_PRIOR_COLUMNS
    assert parsed.frame.iloc[0, -1] == pytest.approx(0.01)
    assert parsed.raw_missing_codes == 0


def test_size_prior_parser_rejects_marker_or_header_drift() -> None:
    with pytest.raises(ValueError, match="marker"):
        parse_size_prior_monthly_table(_synthetic_text(), EQUAL_WEIGHTED_MONTHLY_MARKER)
    malformed = _synthetic_text().replace("BIG HiPRIOR", "BIG Winner")
    with pytest.raises(ValueError, match="欄名或次序"):
        parse_size_prior_monthly_table(malformed, VALUE_WEIGHTED_MONTHLY_MARKER)


def test_size_prior_zip_requires_the_exact_single_member() -> None:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as bundle:
        bundle.writestr("25_Portfolios_ME_Prior_1_0.csv", _synthetic_text())
    assert "196301" in extract_single_csv(buffer.getvalue(), "25_Portfolios_ME_Prior_1_0.csv")
    with pytest.raises(ValueError, match="ZIP member"):
        extract_single_csv(buffer.getvalue(), "wrong.csv")


def test_frozen_size_prior_snapshot_is_complete_and_first_seen() -> None:
    data = load_frozen_size_prior_data(ROOT)
    assert data["common_index"].equals(pd.period_range(FORMAL_START, FORMAL_END, freq="M"))
    assert data["size_value"].shape == (761, 25)
    assert data["protocol_receipt"]["new_archive_numeric_rows_seen"] is False
    assert data["data_receipt"]["strategy_calculation_started"] is False


def test_size_prior_result_is_frozen_negative_and_never_tradeable() -> None:
    result = build_french_size_prior_research(ROOT)
    assert result["data_contract_passed"] is True
    assert result["economic_validation_passed"] is False
    assert result["independent_first_seen_evidence"] is True
    assert result["gate_breakdown"] == {"data": "10/10", "primary": "1/17", "recent": "3/17"}
    assert result["passed_gate_count"] == 14
    assert result["required_gate_count"] == 44
    assert result["paper_eligible"] is False
    assert result["paper_state_created"] is False
    assert result["trade_ready"] is False
    assert result["real_money_action_usd"] == 0


def test_size_prior_key_baselines_and_cost_result_are_reproducible() -> None:
    result = build_french_size_prior_research(ROOT)
    primary = result["primary_external_period"]
    recent = result["recent_confirmation_period"]
    assert primary["candidate_metrics"]["cagr"] == pytest.approx(0.04605303970189567)
    assert primary["baseline_metrics"]["market"]["cagr"] == pytest.approx(0.10823714197896361)
    assert recent["candidate_metrics"]["cagr"] == pytest.approx(0.0971321570649546)
    assert recent["baseline_metrics"]["QQQ"]["cagr"] == pytest.approx(0.16181452008211372)
    assert recent["candidate_50bps_metrics"]["cagr"] == pytest.approx(-0.003582916359736621)
