"""Fail-closed SEC XBRL quarterly earnings-event parser.

The parser turns already downloaded Company Facts JSON into a deterministic
research event stream.  It deliberately stops before any promotion decision:
facts are filtered by filing date, current-period rows are selected without
looking at prices, and a missing or ambiguous observation is skipped and
reported to the caller.
"""

from __future__ import annotations

import bisect
import json
import math
from collections import defaultdict
from collections.abc import Iterable
from datetime import date
from pathlib import Path
from typing import Any

SEC_XBRL_SCHEMA_VERSION = 1
FACTS_CUTOFF = date(2026, 6, 30)
EVENT_START = date(2023, 1, 1)
EVENT_END = FACTS_CUTOFF
ALLOWED_FORMS = ("10-Q",)
ALLOWED_FISCAL_PERIODS = ("Q1", "Q2", "Q3")
MIN_DURATION_DAYS = 70
MAX_DURATION_DAYS = 120
EPS_TAG = "EarningsPerShareDiluted"
REVENUE_TAGS = (
    "Revenues",
    "RevenueFromContractWithCustomerExcludingAssessedTax",
)


def _parse_date(value: Any) -> date | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return date.fromisoformat(text)
    except ValueError:
        return None


def _finite(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return number if math.isfinite(number) else None


def load_company_facts(path: str | Path) -> dict[str, Any]:
    """Load one SEC Company Facts JSON object and reject malformed inputs."""

    source = Path(path)
    payload = json.loads(source.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or not isinstance(payload.get("facts"), dict):
        raise ValueError(f"SEC Company Facts 必須是含 facts 物件的 JSON：{source}")
    if not str(payload.get("cik", "")).strip():
        raise ValueError(f"SEC Company Facts 缺少 cik：{source}")
    return payload


def _fact_rows(
    payload: dict[str, Any],
    *,
    tag: str,
    unit: str,
    cutoff: date,
) -> list[dict[str, Any]]:
    us_gaap = payload.get("facts", {}).get("us-gaap", {})
    fact = us_gaap.get(tag)
    units = fact.get("units") if isinstance(fact, dict) else None
    raw_rows = units.get(unit) if isinstance(units, dict) else None
    if not isinstance(raw_rows, list):
        return []
    rows: list[dict[str, Any]] = []
    for raw in raw_rows:
        if not isinstance(raw, dict):
            continue
        form = str(raw.get("form", "")).strip()
        fp = str(raw.get("fp", "")).strip().upper()
        accession = str(raw.get("accn", "")).strip()
        start = _parse_date(raw.get("start"))
        end = _parse_date(raw.get("end"))
        filed = _parse_date(raw.get("filed"))
        value = _finite(raw.get("val"))
        if (
            form not in ALLOWED_FORMS
            or fp not in ALLOWED_FISCAL_PERIODS
            or not accession
            or start is None
            or end is None
            or filed is None
            or value is None
            or filed > cutoff
        ):
            continue
        duration = (end - start).days + 1
        if not MIN_DURATION_DAYS <= duration <= MAX_DURATION_DAYS:
            continue
        rows.append(
            {
                "tag": tag,
                "unit": unit,
                "accn": accession,
                "fy": int(raw["fy"]) if str(raw.get("fy", "")).strip().isdigit() else None,
                "fp": fp,
                "start": start,
                "end": end,
                "filed": filed,
                "value": value,
                "form": form,
            }
        )
    return [row for row in rows if row["fy"] is not None]


def _select_latest_end(
    rows: Iterable[dict[str, Any]],
) -> dict[tuple[str, int, str], dict[str, Any]]:
    """Select the current-quarter observation inside each accession."""

    grouped: dict[tuple[str, int, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[(row["accn"], row["fy"], row["fp"])].append(row)
    selected: dict[tuple[str, int, str], dict[str, Any]] = {}
    for key, values in grouped.items():
        # A 10-Q can contain cumulative and current-quarter comparative rows.
        # The latest end and latest start is the current quarter; the final
        # value tie-break makes duplicate frame/non-frame rows deterministic.
        selected[key] = max(
            values,
            key=lambda row: (
                row["end"],
                row["start"],
                row["filed"],
                row["value"],
            ),
        )
    return selected


def _period_records(
    payload: dict[str, Any], cutoff: date
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    eps_rows = _fact_rows(payload, tag=EPS_TAG, unit="USD/shares", cutoff=cutoff)
    revenue_rows = [
        row
        for tag, unit in ((REVENUE_TAGS[0], "USD"), (REVENUE_TAGS[1], "USD"))
        for row in _fact_rows(payload, tag=tag, unit=unit, cutoff=cutoff)
    ]
    eps_selected = _select_latest_end(eps_rows)
    revenue_by_tag = {
        tag: _select_latest_end([row for row in revenue_rows if row["tag"] == tag])
        for tag in REVENUE_TAGS
    }
    # Revenue tag priority is per accession-period, never based on its value.
    revenue_selected: dict[tuple[str, int, str], dict[str, Any]] = {}
    for key in set().union(*(mapping.keys() for mapping in revenue_by_tag.values())):
        for tag in REVENUE_TAGS:
            row = revenue_by_tag[tag].get(key)
            if row is not None:
                revenue_selected[key] = row
                break
    records: list[dict[str, Any]] = []
    for key in sorted(set(eps_selected) | set(revenue_selected)):
        eps = eps_selected.get(key)
        revenue = revenue_selected.get(key)
        if eps is None or revenue is None:
            continue
        # Both facts must describe the same accession-period; otherwise the
        # event is not an observable XBRL pair.
        if (eps["end"], eps["start"]) != (revenue["end"], revenue["start"]):
            continue
        records.append(
            {
                "accn": key[0],
                "fy": key[1],
                "fp": key[2],
                "filed": eps["filed"],
                "eps": eps["value"],
                "revenue": revenue["value"],
                "revenue_tag": revenue["tag"],
                "start": eps["start"],
                "end": eps["end"],
            }
        )
    stats = {
        "eps_rows": len(eps_rows),
        "revenue_rows": len(revenue_rows),
        "eps_accession_periods": len(eps_selected),
        "revenue_accession_periods": len(revenue_selected),
        "paired_accession_periods": len(records),
        "unpaired_accession_periods": len(set(eps_selected) | set(revenue_selected)) - len(records),
    }
    return records, stats


def build_positive_growth_events(
    symbol: str,
    payload: dict[str, Any],
    sessions: Iterable[date],
    *,
    event_start: date = EVENT_START,
    event_end: date = EVENT_END,
    cutoff: date = FACTS_CUTOFF,
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    """Build positive EPS-and-revenue year-over-year filing events."""

    if event_start < date(1900, 1, 1) or event_start > event_end:
        raise ValueError("event date window 不合法")
    if event_end > cutoff:
        raise ValueError("event_end 不可晚於 facts cutoff")
    ordered_sessions = sorted(set(sessions))
    records, stats = _period_records(payload, cutoff)
    by_period: dict[tuple[int, str], list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        by_period[(record["fy"], record["fp"])].append(record)
    events: list[dict[str, Any]] = []
    counts = {
        **stats,
        "current_periods": 0,
        "missing_prior": 0,
        "non_positive": 0,
        "not_both_growth": 0,
        "before_event_start": 0,
        "missing_price_session": 0,
        "event_count": 0,
    }
    for (fy, fp), candidates in sorted(by_period.items()):
        # First original filing is the only current-period signal.  A later
        # filing can still serve as a prior comparator only if it was public by
        # the current filing date.
        current = min(candidates, key=lambda row: (row["filed"], row["accn"]))
        counts["current_periods"] += 1
        prior_candidates = [
            row for row in by_period.get((fy - 1, fp), []) if row["filed"] <= current["filed"]
        ]
        if not prior_candidates:
            counts["missing_prior"] += 1
            continue
        prior = max(prior_candidates, key=lambda row: (row["filed"], row["accn"]))
        if (
            current["eps"] <= 0.0
            or prior["eps"] <= 0.0
            or current["revenue"] <= 0.0
            or prior["revenue"] <= 0.0
        ):
            counts["non_positive"] += 1
            continue
        if current["eps"] <= prior["eps"] or current["revenue"] <= prior["revenue"]:
            counts["not_both_growth"] += 1
            continue
        filing_date = current["filed"]
        if not event_start <= filing_date <= event_end:
            if filing_date < event_start:
                counts["before_event_start"] += 1
            continue
        session_index = bisect.bisect_right(ordered_sessions, filing_date)
        if session_index >= len(ordered_sessions):
            counts["missing_price_session"] += 1
            continue
        available_session = ordered_sessions[session_index]
        event = {
            "ticker": str(symbol).strip().upper(),
            "filing_date": filing_date.isoformat(),
            "available_session": available_session.isoformat(),
            "signal_quarter": f"FY{fy}{fp}",
            "score": 0.0,
            "accession_number": current["accn"],
            "eps_current": current["eps"],
            "eps_prior": prior["eps"],
            "revenue_current": current["revenue"],
            "revenue_prior": prior["revenue"],
            "eps_growth": current["eps"] / prior["eps"] - 1.0,
            "revenue_growth": current["revenue"] / prior["revenue"] - 1.0,
            "revenue_tag": current["revenue_tag"],
        }
        events.append(event)
    counts["event_count"] = len(events)
    return events, counts
