from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from collections.abc import Iterable
from datetime import date, datetime
from typing import Any
from urllib.parse import unquote

FORM4_FORWARD_RECONCILIATION_ERROR_CODES = (
    "form4_forward_congress_field_injection",
    "form4_forward_denominator_incomplete",
    "form4_forward_d1_window_invalid",
    "form4_forward_cross_day_missing_or_ambiguous",
    "form4_forward_project_path_cap_exceeded",
    "form4_forward_multipath_duplicate_row",
    "form4_forward_multipath_identity_mismatch",
    "form4_forward_canonical_path_drift",
)

_ACCESSION = re.compile(r"^\d{10}-\d{2}-\d{6}$")
_CIK = re.compile(r"^\d{1,10}$")
_ROW_SUFFIX = re.compile(
    r"(?P<cik>\d{1,10})\s+(?P<date>\d{8})\s+(?P<path>\S+)\s*$"
)
_ALLOWED_FORMS = frozenset({"4", "4/A"})
_PROJECT_PATH_CAP = 10

IndexBody = bytes | str


class Form4MultipathReconciliationError(RuntimeError):
    """Fail-closed offline reconciliation error with a frozen forward code."""

    def __init__(self, code: str, detail: str):
        if code not in FORM4_FORWARD_RECONCILIATION_ERROR_CODES:
            raise ValueError("unknown Form 4 forward reconciliation error code")
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}")


def _fail(code: str, detail: str) -> None:
    raise Form4MultipathReconciliationError(code, detail)


def _is_congress_value(value: object) -> bool:
    if not isinstance(value, str):
        return False
    separated = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", value)
    folded = re.sub(r"[^a-z0-9]+", "_", separated.casefold()).strip("_")
    tokens = set(folded.split("_")) if folded else set()
    compact = folded.replace("_", "")
    return (
        any(
            marker in compact
            for marker in (
                "congress",
                "lawmaker",
                "legislator",
                "senator",
                "politician",
                "capitoltrade",
            )
        )
        or bool(tokens & {"ptr", "house", "senate", "representative"})
        or compact in {"ptr", "house", "senate", "representative"}
    )


def _canonical_date(value: object, *, code: str) -> date:
    # datetime is a date subclass but is not a valid date-only contract value.
    if type(value) is date:
        return value
    if not isinstance(value, str):
        _fail(code, "date must be canonical ISO YYYY-MM-DD")
    try:
        parsed = date.fromisoformat(value)
    except ValueError:
        _fail(code, "date must be canonical ISO YYYY-MM-DD")
    if value != parsed.isoformat():
        _fail(code, "date must be canonical ISO YYYY-MM-DD")
    return parsed


def _validate_identity_inputs(accession: object, form: object) -> tuple[str, str]:
    if _is_congress_value(form):
        _fail(
            "form4_forward_congress_field_injection",
            "Congress/PTR form values are outside the exact SEC Form 4 scope",
        )
    if not isinstance(accession, str) or _ACCESSION.fullmatch(accession) is None:
        _fail("form4_forward_multipath_identity_mismatch", "accession is not canonical")
    if not isinstance(form, str) or form not in _ALLOWED_FORMS:
        _fail("form4_forward_multipath_identity_mismatch", "form must be 4 or 4/A")
    return accession, form


def _required_body(value: object, *, label: str) -> tuple[str, bytes]:
    if isinstance(value, bytes):
        raw = value
        text = raw.decode("latin-1")
    elif isinstance(value, str):
        text = value
        try:
            raw = text.encode("latin-1")
        except UnicodeEncodeError:
            _fail(
                "form4_forward_denominator_incomplete",
                f"{label} body is not byte-preserving Latin-1 text",
            )
    else:
        _fail("form4_forward_denominator_incomplete", f"{label} body is missing")
    if not text.strip():
        _fail("form4_forward_denominator_incomplete", f"{label} body is empty")
    return text, raw


def _published_dates(
    values: object,
    *,
    d0: date,
) -> tuple[tuple[date, ...], date]:
    if isinstance(values, (str, bytes)) or not isinstance(values, Iterable):
        _fail(
            "form4_forward_d1_window_invalid",
            "published_form_index_dates must be a complete date collection",
        )
    parsed = [
        _canonical_date(item, code="form4_forward_d1_window_invalid") for item in values
    ]
    if not parsed or len(parsed) != len(set(parsed)) or d0 not in parsed:
        _fail(
            "form4_forward_d1_window_invalid",
            "published index dates must be non-empty, unique, and include d0",
        )
    ordered = tuple(sorted(parsed))
    later = [item for item in ordered if item > d0]
    if not later:
        _fail(
            "form4_forward_d1_window_invalid",
            "published index dates have no first date strictly after d0",
        )
    d1 = later[0]
    if not 1 <= (d1 - d0).days <= 4:
        _fail(
            "form4_forward_d1_window_invalid",
            "first published index after d0 exceeds the four-day project window",
        )
    return ordered, d1


def _row_date(value: str) -> str | None:
    try:
        parsed = datetime.strptime(value, "%Y%m%d").date()
    except ValueError:
        return None
    return parsed.isoformat() if parsed.strftime("%Y%m%d") == value else None


def _looks_like_target_path(path: str, accession: str) -> bool:
    decoded = unquote(path)
    compact = accession.replace("-", "")
    return accession in path or accession in decoded or compact in path or compact in decoded


def _scan(
    text: str,
    *,
    accession: str,
) -> tuple[list[dict[str, str]], set[str]]:
    rows: list[dict[str, str]] = []
    violations: set[str] = set()

    for raw_line in text.splitlines():
        fields = raw_line.rsplit(maxsplit=1)
        if not fields or not _looks_like_target_path(fields[-1], accession):
            continue
        leading = raw_line.split(maxsplit=1)
        if leading and _is_congress_value(leading[0]):
            violations.add("form4_forward_congress_field_injection")
            continue
        if len(raw_line) < 12:
            violations.add("form4_forward_multipath_identity_mismatch")
            continue
        match = _ROW_SUFFIX.search(raw_line[12:])
        if match is None:
            violations.add("form4_forward_multipath_identity_mismatch")
            continue

        item = match.groupdict()
        raw_form = raw_line[:12].strip()
        if _is_congress_value(raw_form):
            violations.add("form4_forward_congress_field_injection")
            continue
        cik_raw = item["cik"]
        normalized_cik = str(int(cik_raw))
        expected_path = f"edgar/data/{normalized_cik}/{accession}.txt"
        if item["path"] != expected_path:
            violations.add("form4_forward_multipath_identity_mismatch")
            continue
        filing_date = _row_date(item["date"])
        if filing_date is None:
            violations.add("form4_forward_multipath_identity_mismatch")
            continue

        rows.append(
            {
                "cik": normalized_cik,
                "path": item["path"],
                "form": raw_form,
                "filing_date": filing_date,
                "raw_row": raw_line,
            }
        )
    return rows, violations


def _equivalence_class(
    rows: list[dict[str, str]],
    violations: set[str],
    *,
    accession: str,
    form: str,
    filing_date: str,
) -> dict[str, Any] | None:
    if violations:
        if "form4_forward_congress_field_injection" in violations:
            _fail(
                "form4_forward_congress_field_injection",
                "Congress/PTR row was injected into an SEC Form 4 equivalence class",
            )
        _fail(
            "form4_forward_multipath_identity_mismatch",
            "an exact-accession row violates the raw identity contract",
        )
    if not rows:
        return None

    raw_counts = Counter(row["raw_row"] for row in rows)
    if any(count > 1 for count in raw_counts.values()):
        _fail(
            "form4_forward_multipath_duplicate_row",
            "an exact raw form.idx row is duplicated",
        )
    identities = [(row["cik"], row["path"]) for row in rows]
    if len(identities) != len(set(identities)):
        _fail(
            "form4_forward_multipath_identity_mismatch",
            "distinct raw rows collapse to the same normalized identity",
        )
    if not 1 <= len(identities) <= _PROJECT_PATH_CAP:
        _fail(
            "form4_forward_project_path_cap_exceeded",
            "equivalence class exceeds the project cap of ten paths",
        )
    if {row["form"] for row in rows} != {form}:
        _fail(
            "form4_forward_multipath_identity_mismatch",
            "equivalence class has mixed or unexpected form values",
        )
    if {row["filing_date"] for row in rows} != {filing_date}:
        _fail(
            "form4_forward_multipath_identity_mismatch",
            "equivalence class has mixed or unexpected Date Filed values",
        )

    members = sorted(
        ({"cik": cik, "path": path} for cik, path in identities),
        key=lambda row: (row["cik"].zfill(10), row["path"].encode("ascii")),
    )
    return {
        "accession": accession,
        "form": form,
        "filing_date": filing_date,
        "path_count": len(members),
        "project_path_cap": _PROJECT_PATH_CAP,
        "members": members,
        "canonical": dict(members[0]),
    }


def reconcile_form_index_pair(
    *,
    accession: str,
    form: str,
    bulk_filing_date: str | date,
    d0_body: IndexBody,
    d1_body: IndexBody,
    published_form_index_dates: Iterable[str | date],
) -> dict[str, Any]:
    """Reconcile a required d0/d1 pair without network access.

    d1 is derived solely from the complete supplied set of published Form-index
    dates.  The accession must occur in exactly one of the two required bodies.
    """

    parsed_accession, parsed_form = _validate_identity_inputs(accession, form)
    d0 = _canonical_date(
        bulk_filing_date,
        code="form4_forward_multipath_identity_mismatch",
    )
    d0_text, d0_raw = _required_body(d0_body, label="d0")
    d1_text, d1_raw = _required_body(d1_body, label="d1")
    published_dates, d1 = _published_dates(published_form_index_dates, d0=d0)

    d0_rows, d0_violations = _scan(d0_text, accession=parsed_accession)
    d1_rows, d1_violations = _scan(d1_text, accession=parsed_accession)
    expected_filing_date = d0.isoformat()
    d0_class = _equivalence_class(
        d0_rows,
        d0_violations,
        accession=parsed_accession,
        form=parsed_form,
        filing_date=expected_filing_date,
    )
    d1_class = _equivalence_class(
        d1_rows,
        d1_violations,
        accession=parsed_accession,
        form=parsed_form,
        filing_date=expected_filing_date,
    )
    if (d0_class is None) == (d1_class is None):
        _fail(
            "form4_forward_cross_day_missing_or_ambiguous",
            "accession must occur in d0 xor the first published d1",
        )

    carrier = "d0" if d0_class is not None else "d1"
    selected = d0_class if d0_class is not None else d1_class
    assert selected is not None
    published_date_strings = [item.isoformat() for item in published_dates]
    manifest_bytes = json.dumps(
        published_date_strings,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("ascii")
    return {
        "accession": parsed_accession,
        "form": parsed_form,
        "bulk_filing_date": expected_filing_date,
        "d0_date": expected_filing_date,
        "d1_date": d1.isoformat(),
        "published_form_index_dates": published_date_strings,
        "input_seal": {
            "d0_body_sha256": hashlib.sha256(d0_raw).hexdigest(),
            "d1_body_sha256": hashlib.sha256(d1_raw).hexdigest(),
            "published_form_index_dates_sha256": hashlib.sha256(manifest_bytes).hexdigest(),
        },
        "carrier": carrier,
        "carrier_date": expected_filing_date if carrier == "d0" else d1.isoformat(),
        "equivalence_class": selected,
    }


__all__ = [
    "FORM4_FORWARD_RECONCILIATION_ERROR_CODES",
    "Form4MultipathReconciliationError",
    "reconcile_form_index_pair",
]
