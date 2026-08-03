from pathlib import Path

import pandas as pd
import pytest

from usfddk.v11_official_data import parse_official_djia_workbook


def _daily_levels() -> pd.DataFrame:
    dates = pd.bdate_range("1971-02-05", "1988-12-30")
    return pd.DataFrame(
        {
            "Date": dates,
            "DJIA Index Level": 900.0 + pd.Series(range(len(dates))) * 0.1,
        }
    )


def test_parse_official_workbook_scans_unknown_sheet_and_header(tmp_path: Path):
    path = tmp_path / "official.xlsx"
    data = _daily_levels()
    preamble = pd.DataFrame(
        [["Official history", None], [None, None]], columns=data.columns
    )
    header = pd.DataFrame([list(data.columns)], columns=data.columns)
    body = pd.concat([preamble, header, data], ignore_index=True)
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        pd.DataFrame([["notes"]]).to_excel(
            writer, sheet_name="Read me", index=False, header=False
        )
        body.to_excel(writer, sheet_name="Unexpected name", index=False, header=False)

    series, audit = parse_official_djia_workbook(path)

    assert len(series) >= 4_300
    assert series.index[0] == pd.Timestamp("1971-02-05")
    assert series.index[-1] == pd.Timestamp("1988-12-30")
    assert audit["eligible_candidate_count"] == 1
    assert audit["selected"]["sheet"] == "Unexpected name"
    assert audit["selected"]["header_row_excel"] == 3


def test_parse_official_workbook_rejects_multiple_eligible_candidates(tmp_path: Path):
    path = tmp_path / "ambiguous.xlsx"
    data = _daily_levels()
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        data.to_excel(writer, sheet_name="A", index=False)
        data.to_excel(writer, sheet_name="B", index=False)

    with pytest.raises(ValueError, match="實際為 2 個"):
        parse_official_djia_workbook(path)


def test_parse_official_workbook_rejects_conflicting_duplicate_dates(tmp_path: Path):
    path = tmp_path / "conflict.xlsx"
    data = _daily_levels()
    duplicate = data.iloc[[100]].copy()
    duplicate["DJIA Index Level"] += 10.0
    data = pd.concat([data, duplicate], ignore_index=True)
    data.to_excel(path, index=False)

    with pytest.raises(ValueError, match="實際為 0 個"):
        parse_official_djia_workbook(path)
