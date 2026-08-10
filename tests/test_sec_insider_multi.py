from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest

from usfddk.sec_insider import InsiderPurchase
from usfddk.sec_insider_multi import (
    EXPECTED_QUARTERS,
    build_quarter_candidates,
    deduplicate_events,
)


def _event(accession: str, filing: date, owner: str) -> InsiderPurchase:
    return InsiderPurchase(
        accession_number=accession,
        filing_date=filing,
        transaction_date=filing,
        issuer_cik="1",
        issuer_name="Example Corp",
        issuer_ticker="EXMP",
        owner_cik=owner,
        owner_name=owner,
        owner_relationship="Officer",
        owner_title="CFO",
        transaction_sk=accession,
        shares=2_000.0,
        price_per_share=150.0,
        direct_indirect="D",
        ten_b5_one=False,
        source_url="https://www.sec.gov/",
    )


def test_deduplication_keeps_exact_rows_and_rejects_conflicts() -> None:
    event = _event("a", date(2024, 3, 1), "owner-a")
    assert deduplicate_events([event, event]) == [event]
    conflict = _event("a", date(2024, 3, 2), "owner-a")
    with pytest.raises(ValueError, match="conflicting"):
        deduplicate_events([event, conflict])


def test_quarter_candidates_can_use_cross_quarter_window() -> None:
    rows = [
        ("2024Q1", date(2024, 3, 31), [_event("a", date(2024, 3, 29), "owner-a")]),
        ("2024Q2", date(2024, 6, 30), [_event("b", date(2024, 4, 1), "owner-b")]),
    ]
    # Fill the required labels with empty quarters after the focused fixture.
    rows.extend(
        (label, end, [])
        for label, end in EXPECTED_QUARTERS[2:]
    )
    candidates = build_quarter_candidates(rows)
    assert candidates["2024Q1"] == []
    assert len(candidates["2024Q2"]) == 1
    assert candidates["2024Q2"][0]["signal_quarter"] == "2024Q2"


def test_expected_quarter_contract_is_fixed() -> None:
    assert EXPECTED_QUARTERS[0] == ("2024Q1", date(2024, 3, 31))
    assert EXPECTED_QUARTERS[-1] == ("2026Q2", date(2026, 6, 30))


def test_saved_multi_quarter_receipt_keeps_mixed_halves_and_no_paper() -> None:
    receipt = json.loads(
        (
            Path(__file__).resolve().parents[1]
            / "artifacts/short_term_sec_insider_multi_quarter_diagnostic.json"
        ).read_text(encoding="utf-8")
    )
    all_period = receipt["diagnostic"]["all_period"]
    early = receipt["diagnostic"]["fixed_halves"]["2024Q1_2025Q1"]
    late = receipt["diagnostic"]["fixed_halves"]["2025Q2_2026Q2"]
    assert receipt["status"] == "post_hoc_multi_quarter_forward_diagnostic"
    assert receipt["decision"]["paper_authorized"] is False
    assert receipt["diagnostic"]["candidate_count"] == 5798
    assert all_period["horizons"]["20"]["complete_rows"] == 4915
    assert early["horizons"]["20"]["mean_excess_vs_baseline"] < 0.0
    assert late["horizons"]["20"]["mean_excess_vs_baseline"] > 0.0
    assert receipt["price_source"]["missing_candidate_symbol_count"] == 137
