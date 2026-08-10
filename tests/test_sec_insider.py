from __future__ import annotations

import zipfile
from datetime import date
from io import BytesIO

import pandas as pd
import pytest

from usfddk.sec_insider import (
    MIN_CLUSTER_NOTIONAL_USD,
    build_insider_receipt,
    parse_insider_purchases,
    rank_insider_clusters,
)


def _write_zip(path) -> None:
    tables = {
        "SUBMISSION.tsv": pd.DataFrame(
            [
                {
                    "ACCESSION_NUMBER": "0000000001-26-000001",
                    "FILING_DATE": "01-JUN-2026",
                    "PERIOD_OF_REPORT": "29-MAY-2026",
                    "DOCUMENT_TYPE": "4",
                    "ISSUERCIK": "0000000002",
                    "ISSUERNAME": "Example Corp",
                    "ISSUERTRADINGSYMBOL": "EXMP",
                    "AFF10B5ONE": "0",
                },
                {
                    "ACCESSION_NUMBER": "0000000003-26-000001",
                    "FILING_DATE": "01-JUN-2026",
                    "PERIOD_OF_REPORT": "29-MAY-2026",
                    "DOCUMENT_TYPE": "4",
                    "ISSUERCIK": "0000000004",
                    "ISSUERNAME": "Plan Corp",
                    "ISSUERTRADINGSYMBOL": "PLAN",
                    "AFF10B5ONE": "1",
                },
            ]
        ),
        "REPORTINGOWNER.tsv": pd.DataFrame(
            [
                {
                    "ACCESSION_NUMBER": "0000000001-26-000001",
                    "RPTOWNERCIK": "0000000011",
                    "RPTOWNERNAME": "Founder A",
                    "RPTOWNER_RELATIONSHIP": "Officer",
                    "RPTOWNER_TITLE": "Chief Executive Officer",
                },
                {
                    "ACCESSION_NUMBER": "0000000001-26-000001",
                    "RPTOWNERCIK": "0000000012",
                    "RPTOWNERNAME": "Director B",
                    "RPTOWNER_RELATIONSHIP": "Director",
                    "RPTOWNER_TITLE": "",
                },
                {
                    "ACCESSION_NUMBER": "0000000003-26-000001",
                    "RPTOWNERCIK": "0000000013",
                    "RPTOWNERNAME": "Plan Insider",
                    "RPTOWNER_RELATIONSHIP": "Officer",
                    "RPTOWNER_TITLE": "CFO",
                },
            ]
        ),
        "NONDERIV_TRANS.tsv": pd.DataFrame(
            [
                {
                    "ACCESSION_NUMBER": "0000000001-26-000001",
                    "NONDERIV_TRANS_SK": "1",
                    "TRANS_DATE": "29-MAY-2026",
                    "TRANS_FORM_TYPE": "4",
                    "TRANS_CODE": "P",
                    "TRANS_SHARES": "1000",
                    "TRANS_PRICEPERSHARE": "150",
                    "TRANS_ACQUIRED_DISP_CD": "A",
                    "DIRECT_INDIRECT_OWNERSHIP": "D",
                },
                {
                    "ACCESSION_NUMBER": "0000000001-26-000001",
                    "NONDERIV_TRANS_SK": "2",
                    "TRANS_DATE": "29-MAY-2026",
                    "TRANS_FORM_TYPE": "4",
                    "TRANS_CODE": "S",
                    "TRANS_SHARES": "900",
                    "TRANS_PRICEPERSHARE": "150",
                    "TRANS_ACQUIRED_DISP_CD": "D",
                    "DIRECT_INDIRECT_OWNERSHIP": "D",
                },
                {
                    "ACCESSION_NUMBER": "0000000003-26-000001",
                    "NONDERIV_TRANS_SK": "3",
                    "TRANS_DATE": "29-MAY-2026",
                    "TRANS_FORM_TYPE": "4",
                    "TRANS_CODE": "P",
                    "TRANS_SHARES": "5000",
                    "TRANS_PRICEPERSHARE": "100",
                    "TRANS_ACQUIRED_DISP_CD": "A",
                    "DIRECT_INDIRECT_OWNERSHIP": "D",
                },
            ]
        ),
    }
    with zipfile.ZipFile(path, "w") as archive:
        for name, frame in tables.items():
            buffer = BytesIO()
            frame.to_csv(buffer, sep="\t", index=False)
            archive.writestr(name, buffer.getvalue())


def test_parser_keeps_as_filed_open_market_purchases_only(tmp_path) -> None:
    package = tmp_path / "insider.zip"
    _write_zip(package)

    events = parse_insider_purchases(package)

    assert len(events) == 2
    assert {event.owner_name for event in events} == {"Founder A", "Director B"}
    assert all(event.issuer_ticker == "EXMP" for event in events)
    assert all(event.notional_usd == 150_000 for event in events)


def test_parser_rejects_packages_without_10b5_one_field(tmp_path) -> None:
    package = tmp_path / "insider.zip"
    _write_zip(package)
    rewritten = tmp_path / "without-aff.zip"
    with zipfile.ZipFile(package) as source, zipfile.ZipFile(rewritten, "w") as target:
        for info in source.infolist():
            payload = source.read(info.filename)
            if info.filename == "SUBMISSION.tsv":
                frame = pd.read_csv(BytesIO(payload), sep="\t", dtype=str)
                payload = frame.drop(columns=["AFF10B5ONE"]).to_csv(sep="\t", index=False).encode()
            target.writestr(info.filename, payload)

    with pytest.raises(ValueError, match="SUBMISSION 欄位不完整"):
        parse_insider_purchases(rewritten)


def test_signal_uses_next_session_and_never_looks_past_as_of(tmp_path) -> None:
    package = tmp_path / "insider.zip"
    _write_zip(package)
    events = parse_insider_purchases(package)

    assert rank_insider_clusters(events, as_of=date(2026, 6, 1)) == []
    candidates = rank_insider_clusters(
        events,
        as_of=date(2026, 6, 2),
        universe_symbols={"EXMP"},
    )

    assert len(candidates) == 1
    candidate = candidates[0]
    assert candidate["ticker"] == "EXMP"
    assert candidate["available_session"] == "2026-06-02"
    assert candidate["distinct_owner_count"] == 2
    assert candidate["notional_usd"] >= MIN_CLUSTER_NOTIONAL_USD
    assert candidate["research_only"] is True

    assert rank_insider_clusters(
        events,
        as_of=date(2026, 6, 2),
        universe_symbols={"PLAN"},
    ) == []


def test_signal_window_is_frozen_and_receipt_is_not_a_trade(tmp_path) -> None:
    package = tmp_path / "insider.zip"
    _write_zip(package)
    events = parse_insider_purchases(package)

    with pytest.raises(ValueError, match="frozen at 20"):
        rank_insider_clusters(events, as_of=date(2026, 6, 2), window_sessions=10)

    receipt = build_insider_receipt(
        package,
        as_of=date(2026, 6, 2),
        source_url="https://example.invalid/2026q2_form345.zip",
    )
    assert receipt["decision"]["strategy_status"] == "research_candidate_only"
    assert receipt["source"]["url"].endswith("2026q2_form345.zip")
    assert receipt["decision"]["formal_backtest_completed"] is False
    assert receipt["decision"]["paper_authorized"] is False
    assert receipt["decision"]["real_money_action_usd"] == 0
