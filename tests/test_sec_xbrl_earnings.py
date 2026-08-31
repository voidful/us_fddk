from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest

from usfddk.sec_xbrl_earnings import build_positive_growth_events, load_company_facts


def _fact(
    *,
    start: str,
    end: str,
    value: float,
    accn: str,
    fy: int,
    fp: str,
    filed: str,
    form: str = "10-Q",
) -> dict:
    return {
        "start": start,
        "end": end,
        "val": value,
        "accn": accn,
        "fy": fy,
        "fp": fp,
        "form": form,
        "filed": filed,
    }


def _payload(*, revenue_tag: str = "RevenueFromContractWithCustomerExcludingAssessedTax") -> dict:
    eps = [
        _fact(
            start="2023-01-01",
            end="2023-03-31",
            value=1.0,
            accn="0000000001-23-000001",
            fy=2023,
            fp="Q1",
            filed="2023-05-01",
        ),
        # The cumulative/comparative row must not displace the latest current
        # quarter row selected from the same accession.
        _fact(
            start="2023-01-01",
            end="2024-03-31",
            value=2.0,
            accn="0000000001-24-000001",
            fy=2024,
            fp="Q1",
            filed="2024-05-01",
        ),
        _fact(
            start="2024-01-01",
            end="2024-03-31",
            value=2.0,
            accn="0000000001-24-000001",
            fy=2024,
            fp="Q1",
            filed="2024-05-01",
        ),
        # A later duplicate filing has a different value and must not become
        # the signal because the original accession is frozen first.
        _fact(
            start="2024-01-01",
            end="2024-03-31",
            value=9.0,
            accn="0000000001-24-000002",
            fy=2024,
            fp="Q1",
            filed="2024-05-10",
        ),
        _fact(
            start="2024-01-01",
            end="2024-03-31",
            value=99.0,
            accn="0000000001-24-000003",
            fy=2024,
            fp="Q1",
            filed="2024-07-01",
            form="10-Q/A",
        ),
    ]
    revenue = [
        _fact(
            start="2023-01-01",
            end="2023-03-31",
            value=100.0,
            accn="0000000001-23-000001",
            fy=2023,
            fp="Q1",
            filed="2023-05-01",
        ),
        _fact(
            start="2024-01-01",
            end="2024-03-31",
            value=200.0,
            accn="0000000001-24-000001",
            fy=2024,
            fp="Q1",
            filed="2024-05-01",
        ),
        _fact(
            start="2024-01-01",
            end="2024-03-31",
            value=900.0,
            accn="0000000001-24-000002",
            fy=2024,
            fp="Q1",
            filed="2024-05-10",
        ),
    ]
    return {
        "cik": "0000000001",
        "entityName": "Synthetic Corp",
        "facts": {
            "us-gaap": {
                "EarningsPerShareDiluted": {"units": {"USD/shares": eps}},
                revenue_tag: {"units": {"USD": revenue}},
            }
        },
    }


def test_xbrl_parser_uses_original_filing_and_next_session() -> None:
    events, counts = build_positive_growth_events(
        "TEST",
        _payload(),
        [date(2024, 5, 1), date(2024, 5, 2), date(2024, 5, 3)],
    )
    assert len(events) == 1
    event = events[0]
    assert event["available_session"] == "2024-05-02"
    assert event["accession_number"] == "0000000001-24-000001"
    assert event["eps_current"] == 2.0
    assert event["revenue_current"] == 200.0
    assert event["signal_quarter"] == "FY2024Q1"
    assert counts["event_count"] == 1
    assert counts["not_both_growth"] == 0


def test_xbrl_parser_accepts_revenue_fallback_and_rejects_after_cutoff() -> None:
    payload = _payload(revenue_tag="RevenueFromContractWithCustomerExcludingAssessedTax")
    events, _ = build_positive_growth_events(
        "TEST",
        payload,
        [date(2024, 5, 2)],
        cutoff=date(2024, 6, 30),
        event_end=date(2024, 6, 30),
    )
    assert events[0]["revenue_tag"] == "RevenueFromContractWithCustomerExcludingAssessedTax"


def test_load_company_facts_rejects_non_object(tmp_path: Path) -> None:
    source = tmp_path / "facts.json"
    source.write_text(json.dumps([]), encoding="utf-8")
    with pytest.raises(ValueError, match="facts"):
        load_company_facts(source)


def test_committed_diagnostic_is_research_only() -> None:
    path = Path(__file__).parents[1] / "artifacts/short_term_sec_xbrl_earnings_diagnostic.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["status"] == "post_hoc_sec_xbrl_earnings_event_diagnostic"
    assert payload["event_filter"]["raw_event_count"] == 139
    assert payload["cost_scenarios"]["10"]["all_period"]["accepted_count"] == 138
    assert payload["cost_scenarios"]["10"]["all_period"]["simulation"]["portfolio"]["cagr"] == pytest.approx(0.1340333269)
    assert payload["cost_scenarios"]["10"]["all_period"]["simulation"]["QQQ"]["cagr"] == pytest.approx(0.2907234523)
    assert payload["decision"]["paper_authorized"] is False
    assert payload["decision"]["public_strategy_allowed"] is False
