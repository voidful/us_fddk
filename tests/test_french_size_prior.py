from __future__ import annotations

import io
import zipfile

import pytest

from usfddk.french_size_prior import (
    EQUAL_WEIGHTED_MONTHLY_MARKER,
    SIZE_PRIOR_COLUMNS,
    VALUE_WEIGHTED_MONTHLY_MARKER,
    extract_single_csv,
    parse_size_prior_monthly_table,
)


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
