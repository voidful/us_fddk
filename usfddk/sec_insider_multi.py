"""Fixed multi-quarter assembly for the SEC insider event diagnostic."""

from __future__ import annotations

from datetime import date
from typing import Any

from usfddk.sec_insider import InsiderPurchase, rank_insider_clusters
from usfddk.sec_insider_forward import compute_forward_event_diagnostic

EXPECTED_QUARTERS = (
    ("2024Q1", date(2024, 3, 31)),
    ("2024Q2", date(2024, 6, 30)),
    ("2024Q3", date(2024, 9, 30)),
    ("2024Q4", date(2024, 12, 31)),
    ("2025Q1", date(2025, 3, 31)),
    ("2025Q2", date(2025, 6, 30)),
    ("2025Q3", date(2025, 9, 30)),
    ("2025Q4", date(2025, 12, 31)),
    ("2026Q1", date(2026, 3, 31)),
    ("2026Q2", date(2026, 6, 30)),
)


def deduplicate_events(events: list[InsiderPurchase]) -> list[InsiderPurchase]:
    """Reject conflicting repeated rows and retain exact duplicates once."""

    unique: dict[tuple[str, str, str], InsiderPurchase] = {}
    for event in events:
        key = (event.accession_number, event.transaction_sk, event.owner_cik)
        previous = unique.get(key)
        if previous is not None and previous != event:
            raise ValueError(f"SEC event key 出現 conflicting rows：{key}")
        unique[key] = event
    return sorted(
        unique.values(),
        key=lambda event: (
            event.filing_date,
            event.accession_number,
            event.transaction_sk,
            event.owner_cik,
        ),
    )


def build_quarter_candidates(
    quarter_events: list[tuple[str, date, list[InsiderPurchase]]],
) -> dict[str, list[dict[str, Any]]]:
    """Return only newly signalled rows for each fixed quarter.

    Clusters are ranked on cumulative known events so a 20-session window may
    cross a quarter boundary.  Only rows whose filing signal date belongs to
    the current quarter are assigned to that quarter.
    """

    all_events: list[InsiderPurchase] = []
    previous_end: date | None = None
    result: dict[str, list[dict[str, Any]]] = {}
    for label, quarter_end, events in quarter_events:
        all_events = deduplicate_events([*all_events, *events])
        candidates = rank_insider_clusters(all_events, as_of=quarter_end)
        current: list[dict[str, Any]] = []
        for candidate in candidates:
            signal_date = date.fromisoformat(candidate["signal_date"])
            if previous_end is not None and signal_date <= previous_end:
                continue
            if signal_date > quarter_end:
                continue
            current.append({**candidate, "signal_quarter": label})
        result[label] = current
        previous_end = quarter_end
    return result


def build_multi_quarter_diagnostic(
    quarter_events: list[tuple[str, date, list[InsiderPurchase]]],
    prices,
) -> dict[str, Any]:
    """Compute all-period, fixed-half and per-quarter event diagnostics."""

    labels = tuple(label for label, _, _ in quarter_events)
    expected_labels = tuple(label for label, _ in EXPECTED_QUARTERS)
    if labels != expected_labels:
        raise ValueError("multi-quarter sample 必須固定為 2024Q1 至 2026Q2")
    quarter_candidates = build_quarter_candidates(quarter_events)
    flattened = [row for label in labels for row in quarter_candidates[label]]
    ends = {label: quarter_end for label, quarter_end, _ in quarter_events}
    all_end = ends[labels[-1]]
    first_half = [row for label in labels[:5] for row in quarter_candidates[label]]
    second_half = [row for label in labels[5:] for row in quarter_candidates[label]]
    candidate_symbols = sorted({row["ticker"] for row in flattened})
    return {
        "candidate_count": len(flattened),
        "candidate_issuer_count": len({row["ticker"] for row in flattened}),
        "candidate_symbols": candidate_symbols,
        "all_period": compute_forward_event_diagnostic(
            flattened,
            prices,
            as_of=all_end,
        ),
        "fixed_halves": {
            "2024Q1_2025Q1": compute_forward_event_diagnostic(
                first_half,
                prices,
                as_of=EXPECTED_QUARTERS[4][1],
            ),
            "2025Q2_2026Q2": compute_forward_event_diagnostic(
                second_half,
                prices,
                as_of=all_end,
            ),
        },
        "by_quarter": {
            label: {
                "candidate_count": len(quarter_candidates[label]),
                "candidate_issuer_count": len(
                    {row["ticker"] for row in quarter_candidates[label]}
                ),
                "diagnostic": compute_forward_event_diagnostic(
                    quarter_candidates[label],
                    prices,
                    as_of=quarter_end,
                ),
            }
            for label, quarter_end, _ in quarter_events
        },
    }
