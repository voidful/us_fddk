"""Fail-closed parser and research-only signal for SEC insider transactions.

The SEC quarterly Form 3/4/5 files are an evidence stream, not a price or
point-in-time universe provider.  This module deliberately uses the filing
date (and the next XNYS session) as the earliest usable signal time.  It does
not promote a trade, create Paper state, or claim that insiders are founders
or politicians.
"""

from __future__ import annotations

import hashlib
import math
import re
import zipfile
from bisect import bisect_left, bisect_right
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import pandas as pd

SIGNAL_SCHEMA_VERSION = 1
SIGNAL_WINDOW_SESSIONS = 20
MIN_CLUSTER_OWNERS = 2
MIN_CLUSTER_NOTIONAL_USD = 250_000.0
UNIVERSE_AUDIT_SCHEMA_VERSION = 1


@dataclass(frozen=True)
class InsiderPurchase:
    accession_number: str
    filing_date: date
    transaction_date: date
    issuer_cik: str
    issuer_name: str
    issuer_ticker: str
    owner_cik: str
    owner_name: str
    owner_relationship: str
    owner_title: str
    transaction_sk: str
    shares: float
    price_per_share: float
    direct_indirect: str
    ten_b5_one: bool
    source_url: str

    @property
    def notional_usd(self) -> float:
        return self.shares * self.price_per_share


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _read_tsv(archive: zipfile.ZipFile, name: str) -> pd.DataFrame:
    try:
        with archive.open(name) as handle:
            return pd.read_csv(
                handle,
                sep="\t",
                dtype=str,
                keep_default_na=False,
                encoding="utf-8-sig",
            )
    except KeyError as exc:
        raise ValueError(f"SEC insider package 缺少必要檔案：{name}") from exc


def _date(value: Any) -> date | None:
    text = str(value).strip()
    if not text:
        return None
    parsed = pd.to_datetime(text, format="%d-%b-%Y", errors="coerce")
    if pd.isna(parsed):
        return None
    return parsed.date()


def _number(value: Any) -> float | None:
    try:
        result = float(str(value).strip())
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def _truthy(value: Any) -> bool:
    return str(value).strip().lower() in {"1", "true", "t", "yes", "y"}


def _valid_ticker(value: Any) -> str | None:
    ticker = str(value).strip().upper()
    if ticker in {"", "NONE", "N/A", "NA", "NULL", "UNKNOWN"}:
        return None
    if re.fullmatch(r"[A-Z][A-Z0-9.\-]{0,9}", ticker) is None:
        return None
    return ticker


def _source_url(accession: str) -> str:
    compact = accession.replace("-", "")
    filer_cik = str(int(compact[:10])) if compact[:10].isdigit() else compact[:10]
    return f"https://www.sec.gov/Archives/edgar/data/{filer_cik}/{compact}/"


def parse_insider_purchases(path: str | Path) -> list[InsiderPurchase]:
    """Parse only as-filed, non-derivative Form 4 open-market purchases.

    Invalid dates, numeric fields, owner identity, or issuer tickers are
    rejected rather than guessed.  Amendments remain separate filings; later
    reconciliation against the original filing is required before using this
    stream in a formal backtest.
    """

    archive_path = Path(path)
    with zipfile.ZipFile(archive_path) as archive:
        submission = _read_tsv(archive, "SUBMISSION.tsv")
        owners = _read_tsv(archive, "REPORTINGOWNER.tsv")
        transactions = _read_tsv(archive, "NONDERIV_TRANS.tsv")

    required_submission = {
        "ACCESSION_NUMBER",
        "FILING_DATE",
        "DOCUMENT_TYPE",
        "ISSUERCIK",
        "ISSUERNAME",
        "ISSUERTRADINGSYMBOL",
        "AFF10B5ONE",
    }
    required_owners = {
        "ACCESSION_NUMBER",
        "RPTOWNERCIK",
        "RPTOWNERNAME",
        "RPTOWNER_RELATIONSHIP",
    }
    required_transactions = {
        "ACCESSION_NUMBER",
        "NONDERIV_TRANS_SK",
        "TRANS_DATE",
        "TRANS_FORM_TYPE",
        "TRANS_CODE",
        "TRANS_SHARES",
        "TRANS_PRICEPERSHARE",
        "TRANS_ACQUIRED_DISP_CD",
        "DIRECT_INDIRECT_OWNERSHIP",
    }
    if not required_submission.issubset(submission.columns):
        raise ValueError("SEC insider SUBMISSION 欄位不完整")
    if not required_owners.issubset(owners.columns):
        raise ValueError("SEC insider REPORTINGOWNER 欄位不完整")
    if not required_transactions.issubset(transactions.columns):
        raise ValueError("SEC insider NONDERIV_TRANS 欄位不完整")

    submission = submission[submission["DOCUMENT_TYPE"].str.upper().isin({"4", "4/A"})].copy()
    if submission.empty:
        return []
    submission = submission.set_index("ACCESSION_NUMBER", drop=False)
    owners = owners[owners["ACCESSION_NUMBER"].isin(submission.index)].copy()
    transactions = transactions[transactions["ACCESSION_NUMBER"].isin(submission.index)].copy()
    if owners.empty or transactions.empty:
        return []

    owner_columns = [
        "ACCESSION_NUMBER",
        "RPTOWNERCIK",
        "RPTOWNERNAME",
        "RPTOWNER_RELATIONSHIP",
        "RPTOWNER_TITLE",
    ]
    owners = owners.reindex(columns=owner_columns, fill_value="")
    transaction_columns = [
        "ACCESSION_NUMBER",
        "NONDERIV_TRANS_SK",
        "TRANS_DATE",
        "TRANS_FORM_TYPE",
        "TRANS_CODE",
        "TRANS_SHARES",
        "TRANS_PRICEPERSHARE",
        "TRANS_ACQUIRED_DISP_CD",
        "DIRECT_INDIRECT_OWNERSHIP",
    ]
    transactions = transactions.reindex(columns=transaction_columns, fill_value="")
    merged = transactions.merge(owners, on="ACCESSION_NUMBER", how="inner", validate="many_to_many")

    events: list[InsiderPurchase] = []
    for row in merged.to_dict(orient="records"):
        accession = str(row["ACCESSION_NUMBER"]).strip()
        submission_row = submission.loc[accession]
        filing_date = _date(submission_row["FILING_DATE"])
        transaction_date = _date(row["TRANS_DATE"])
        shares = _number(row["TRANS_SHARES"])
        price = _number(row["TRANS_PRICEPERSHARE"])
        ticker = _valid_ticker(submission_row["ISSUERTRADINGSYMBOL"])
        owner_cik = str(row["RPTOWNERCIK"]).strip()
        if (
            filing_date is None
            or transaction_date is None
            or shares is None
            or price is None
            or shares <= 0.0
            or price <= 0.0
            or ticker is None
            or not owner_cik
            or str(row["TRANS_FORM_TYPE"]).strip() not in {"", "4"}
            or str(row["TRANS_CODE"]).strip().upper() != "P"
            or str(row["TRANS_ACQUIRED_DISP_CD"]).strip().upper() != "A"
            or _truthy(submission_row.get("AFF10B5ONE", ""))
        ):
            continue
        events.append(
            InsiderPurchase(
                accession_number=accession,
                filing_date=filing_date,
                transaction_date=transaction_date,
                issuer_cik=str(submission_row["ISSUERCIK"]).strip(),
                issuer_name=str(submission_row["ISSUERNAME"]).strip(),
                issuer_ticker=ticker,
                owner_cik=owner_cik,
                owner_name=str(row["RPTOWNERNAME"]).strip(),
                owner_relationship=str(row["RPTOWNER_RELATIONSHIP"]).strip(),
                owner_title=str(row.get("RPTOWNER_TITLE", "")).strip(),
                transaction_sk=str(row["NONDERIV_TRANS_SK"]).strip(),
                shares=shares,
                price_per_share=price,
                direct_indirect=str(row["DIRECT_INDIRECT_OWNERSHIP"]).strip(),
                ten_b5_one=False,
                source_url=_source_url(accession),
            )
        )
    return events


def _next_xnys_session(day: date) -> date:
    try:
        import exchange_calendars as xcals

        calendar = xcals.get_calendar("XNYS")
        session = calendar.date_to_session(pd.Timestamp(day), direction="next")
        if session.date() <= day:
            session = calendar.next_session(session)
        return pd.Timestamp(session).date()
    except Exception:
        candidate = day + timedelta(days=1)
        while candidate.weekday() >= 5:
            candidate += timedelta(days=1)
        return candidate


def _window_start_xnys(day: date, sessions: int) -> date:
    """Return the inclusive start date for a filing-date XNYS window."""

    if sessions <= 0:
        raise ValueError("sessions must be positive")
    try:
        import exchange_calendars as xcals

        calendar = xcals.get_calendar("XNYS")
        session = calendar.date_to_session(pd.Timestamp(day), direction="previous")
        for _ in range(sessions - 1):
            session = calendar.previous_session(session)
        return pd.Timestamp(session).date()
    except Exception:
        candidate = day
        for _ in range(sessions - 1):
            candidate -= timedelta(days=1)
            while candidate.weekday() >= 5:
                candidate -= timedelta(days=1)
        return candidate


def rank_insider_clusters(
    events: list[InsiderPurchase],
    *,
    as_of: date,
    window_sessions: int = SIGNAL_WINDOW_SESSIONS,
    universe_symbols: set[str] | None = None,
) -> list[dict[str, Any]]:
    """Return research-only cluster candidates known by ``as_of``.

    The window is measured in XNYS sessions from each event's filing date; no
    transaction whose filing is after ``as_of`` can enter the result.  The
    output is a candidate feed, not a backtest or execution instruction.
    """

    if window_sessions != SIGNAL_WINDOW_SESSIONS or window_sessions <= 0:
        raise ValueError("insider signal window is frozen at 20 XNYS sessions")
    known = [
        event
        for event in events
        if event.filing_date <= as_of
        and (universe_symbols is None or event.issuer_ticker in universe_symbols)
    ]
    known.sort(key=lambda event: (event.filing_date, event.accession_number, event.transaction_sk))
    events_by_ticker: dict[str, list[InsiderPurchase]] = {}
    dates_by_ticker: dict[str, list[date]] = {}
    for event in known:
        events_by_ticker.setdefault(event.issuer_ticker, []).append(event)
    for ticker, ticker_events in events_by_ticker.items():
        dates_by_ticker[ticker] = [event.filing_date for event in ticker_events]
    candidates: list[dict[str, Any]] = []
    for current in known:
        start = _window_start_xnys(current.filing_date, window_sessions)
        ticker_events = events_by_ticker[current.issuer_ticker]
        ticker_dates = dates_by_ticker[current.issuer_ticker]
        window = ticker_events[
            bisect_left(ticker_dates, start) : bisect_right(
                ticker_dates, current.filing_date
            )
        ]
        owner_count = len({event.owner_cik for event in window})
        notional = sum(event.notional_usd for event in window)
        if owner_count < MIN_CLUSTER_OWNERS or notional < MIN_CLUSTER_NOTIONAL_USD:
            continue
        available_session = _next_xnys_session(current.filing_date)
        if available_session > as_of:
            continue
        candidates.append(
            {
                "ticker": current.issuer_ticker,
                "issuer_name": current.issuer_name,
                "signal_date": current.filing_date.isoformat(),
                "available_session": available_session.isoformat(),
                "event_count": len(window),
                "distinct_owner_count": owner_count,
                "notional_usd": round(notional, 2),
                "score": round(math.log1p(notional) + 0.5 * owner_count, 6),
                "source_accessions": sorted({event.accession_number for event in window}),
                "research_only": True,
            }
        )
    unique: dict[tuple[str, str], dict[str, Any]] = {}
    for candidate in candidates:
        unique[(candidate["ticker"], candidate["available_session"])] = candidate
    return sorted(
        unique.values(),
        key=lambda row: (-float(row["score"]), row["ticker"], row["available_session"]),
    )


def summarize_insider_scope(
    events: list[InsiderPurchase],
    candidates: list[dict[str, Any]],
    *,
    universe_label: str,
    universe_symbols: set[str] | None = None,
) -> dict[str, Any]:
    """Summarise universe sensitivity without introducing a new signal rule.

    This is a post-hoc data-quality diagnostic.  It reports how the frozen
    cluster rule changes when the candidate universe changes; it does not
    filter, rank, or turn any row into a trading instruction.
    """

    issuer_counts = Counter(row["ticker"] for row in candidates)
    relationship_counts = Counter(
        event.owner_relationship or "(missing)" for event in events
    )
    return {
        "universe_label": universe_label,
        "universe_symbol_count": (
            len(universe_symbols) if universe_symbols is not None else None
        ),
        "event_count": len(events),
        "issuer_count": len({event.issuer_ticker for event in events}),
        "owner_count": len({event.owner_cik for event in events}),
        "owner_relationship_counts": dict(sorted(relationship_counts.items())),
        "candidate_count": len(candidates),
        "candidate_issuer_count": len(issuer_counts),
        "candidate_issuers_with_repeated_signals": sum(
            count >= 2 for count in issuer_counts.values()
        ),
        "candidate_rows_notional_at_least_usd_10m": sum(
            float(row["notional_usd"]) >= 10_000_000.0 for row in candidates
        ),
        "candidate_rows_notional_at_least_usd_100m": sum(
            float(row["notional_usd"]) >= 100_000_000.0 for row in candidates
        ),
        "candidate_rows_with_research_only_flag": sum(
            row.get("research_only") is True for row in candidates
        ),
    }


def build_insider_receipt(
    path: str | Path,
    *,
    as_of: date,
    universe_symbols: set[str] | None = None,
    universe_label: str = "all_valid_tickers",
    source_url: str | None = None,
) -> dict[str, Any]:
    events = parse_insider_purchases(path)
    candidates = rank_insider_clusters(
        events,
        as_of=as_of,
        universe_symbols=universe_symbols,
    )
    return {
        "schema_version": SIGNAL_SCHEMA_VERSION,
        "source": {
            "provider": "SEC Insider Transactions Data Sets",
            # Keep the receipt portable: absolute download paths are local
            # execution details and would make the committed evidence
            # irreproducible on another machine.
            "filename": Path(path).name,
            "sha256": sha256_file(path),
            "url": source_url,
            "as_of": as_of.isoformat(),
            "as_filed": True,
            "universe_label": universe_label,
            "universe_symbols": sorted(universe_symbols) if universe_symbols is not None else None,
        },
        "rule": {
            "transaction_code": "P",
            "acquired_disposed": "A",
            "non_derivative_only": True,
            "exclude_aff10b5one": True,
            "cluster_window_xnys_sessions": SIGNAL_WINDOW_SESSIONS,
            "minimum_distinct_owners": MIN_CLUSTER_OWNERS,
            "minimum_notional_usd": MIN_CLUSTER_NOTIONAL_USD,
            "availability": "next_XNYS_session_after_filing_date",
        },
        "event_count": len(events),
        "issuer_count": len({event.issuer_ticker for event in events}),
        "owner_count": len({event.owner_cik for event in events}),
        "candidate_count": len(candidates),
        "candidates": candidates,
        "decision": {
            "strategy_status": "research_candidate_only",
            "formal_backtest_completed": False,
            "paper_authorized": False,
            "real_money_action_usd": 0,
            "public_strategy_allowed": False,
            "reason": "SEC insider events do not replace point-in-time equity prices, delisting returns, or the frozen formal backtest package.",
        },
        "events_sample": [asdict(event) | {"filing_date": event.filing_date.isoformat(), "transaction_date": event.transaction_date.isoformat()} for event in events[:20]],
    }
