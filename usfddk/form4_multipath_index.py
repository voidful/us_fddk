from __future__ import annotations

import re
from collections import Counter
from datetime import date
from pathlib import PurePosixPath
from typing import Any

FORM4_MULTIPATH_ERROR_CODES = (
    "form4_multipath_accession_invalid",
    "form4_multipath_expected_form_invalid",
    "form4_multipath_bulk_filing_date_invalid",
    "form4_multipath_index_row_invalid",
    "form4_multipath_path_cik_drift",
    "form4_multipath_basename_drift",
    "form4_multipath_accession_missing",
    "form4_multipath_exact_duplicate",
    "form4_multipath_equivalence_class_too_large",
    "form4_multipath_mixed_form",
    "form4_multipath_form_mismatch",
    "form4_multipath_mixed_filing_date",
    "form4_multipath_filing_date_mismatch",
    "form4_multipath_carrier_shape_invalid",
    "form4_multipath_carrier_xor_invalid",
    "form4_multipath_d1_date_window_invalid",
)

_ACCESSION = re.compile(r"^\d{10}-\d{2}-\d{6}$")
_CIK = re.compile(r"^\d{1,10}$")
_INDEX_ROW_SUFFIX = re.compile(
    r"(?P<cik>\d{1,10})\s+(?P<date>\d{8})\s+(?P<path>\S+)\s*$"
)
_ALLOWED_FORMS = frozenset({"4", "4/A"})
_MAX_EQUIVALENT_PATHS = 10

IndexBody = bytes | str


class Form4MultipathIndexError(RuntimeError):
    """Fail-closed offline Form 4 index error with a stable semantic code."""

    def __init__(self, code: str, detail: str):
        if code not in FORM4_MULTIPATH_ERROR_CODES:
            raise ValueError("unknown Form 4 multipath error code")
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}")


def _fail(code: str, detail: str) -> None:
    raise Form4MultipathIndexError(code, detail)


def _parse_accession(value: object) -> str:
    if not isinstance(value, str) or _ACCESSION.fullmatch(value) is None:
        _fail("form4_multipath_accession_invalid", "accession must use SEC canonical form")
    return value


def _parse_expected_form(value: object) -> str:
    if not isinstance(value, str) or value not in _ALLOWED_FORMS:
        _fail("form4_multipath_expected_form_invalid", "expected form must be 4 or 4/A")
    return value


def _parse_iso_date(value: object, *, code: str) -> date:
    if isinstance(value, date):
        return value
    if not isinstance(value, str):
        _fail(code, "date must be ISO YYYY-MM-DD")
    try:
        parsed = date.fromisoformat(value)
    except ValueError:
        _fail(code, "date must be ISO YYYY-MM-DD")
    if parsed.isoformat() != value:
        _fail(code, "date must be canonical ISO YYYY-MM-DD")
    return parsed


def _decode_body(body: object) -> str:
    if isinstance(body, bytes):
        return body.decode("latin-1")
    if isinstance(body, str):
        return body
    _fail("form4_multipath_index_row_invalid", "form.idx body must be bytes or text")


def _normalize_cik(value: str) -> str:
    if _CIK.fullmatch(value) is None:
        _fail("form4_multipath_index_row_invalid", "index CIK is invalid")
    return str(int(value))


def _row_date(value: str) -> str | None:
    try:
        parsed = date(int(value[:4]), int(value[4:6]), int(value[6:8]))
    except (ValueError, TypeError):
        return None
    canonical = parsed.strftime("%Y%m%d")
    return parsed.isoformat() if canonical == value else None


def _scan_exact_accession(
    body: IndexBody,
    *,
    accession: str,
) -> tuple[list[dict[str, str]], set[str]]:
    """Scan only rows whose final path token refers to the exact accession.

    Violations are accumulated and resolved by a fixed priority in the caller so
    changing physical line order cannot change the selected error code.
    """

    rows: list[dict[str, str]] = []
    violations: set[str] = set()
    expected_basename = f"{accession}.txt"

    for line in _decode_body(body).splitlines():
        fields = line.rsplit(maxsplit=1)
        if not fields or accession not in fields[-1]:
            continue
        if len(line) < 12:
            violations.add("form4_multipath_index_row_invalid")
            continue
        match = _INDEX_ROW_SUFFIX.search(line[12:])
        if match is None:
            violations.add("form4_multipath_index_row_invalid")
            continue

        item = match.groupdict()
        path = item["path"]
        path_parts = PurePosixPath(path).parts
        if PurePosixPath(path).name != expected_basename:
            violations.add("form4_multipath_basename_drift")
            continue
        if (
            len(path_parts) != 4
            or path_parts[:2] != ("edgar", "data")
            or _CIK.fullmatch(path_parts[2]) is None
        ):
            violations.add("form4_multipath_path_cik_drift")
            continue

        cik = _normalize_cik(item["cik"])
        path_cik = _normalize_cik(path_parts[2])
        if cik != path_cik:
            violations.add("form4_multipath_path_cik_drift")
            continue
        filing_date = _row_date(item["date"])
        if filing_date is None:
            violations.add("form4_multipath_index_row_invalid")
            continue

        rows.append(
            {
                "cik": cik,
                "path": path,
                "form": line[:12].strip(),
                "filing_date": filing_date,
            }
        )
    return rows, violations


def _build_equivalence_class(
    body: IndexBody,
    *,
    accession: str,
    form: str,
    filing_date: str,
    allow_missing: bool,
) -> dict[str, Any] | None:
    rows, violations = _scan_exact_accession(body, accession=accession)

    # This fixed precedence is part of the line-order-invariance contract.
    for code in (
        "form4_multipath_index_row_invalid",
        "form4_multipath_path_cik_drift",
        "form4_multipath_basename_drift",
    ):
        if code in violations:
            _fail(code, "exact-accession form.idx row is structurally invalid")

    if not rows:
        if allow_missing:
            return None
        _fail("form4_multipath_accession_missing", "exact accession is absent from form.idx")

    identities = [(row["cik"], row["path"]) for row in rows]
    if any(count > 1 for count in Counter(identities).values()):
        _fail(
            "form4_multipath_exact_duplicate",
            "exact (CIK, path) identity is duplicated",
        )
    if len(identities) > _MAX_EQUIVALENT_PATHS:
        _fail(
            "form4_multipath_equivalence_class_too_large",
            "exact accession has more than ten distinct paths",
        )

    observed_forms = {row["form"] for row in rows}
    if len(observed_forms) != 1:
        _fail("form4_multipath_mixed_form", "equivalence class mixes form values")
    if observed_forms != {form}:
        _fail("form4_multipath_form_mismatch", "index form differs from bulk row")

    observed_dates = {row["filing_date"] for row in rows}
    if len(observed_dates) != 1:
        _fail(
            "form4_multipath_mixed_filing_date",
            "equivalence class mixes filing dates",
        )
    if observed_dates != {filing_date}:
        _fail(
            "form4_multipath_filing_date_mismatch",
            "index filing date differs from bulk filing_date",
        )

    members = sorted(
        ({"cik": cik, "path": path} for cik, path in identities),
        key=lambda row: (row["cik"].zfill(10), row["path"]),
    )
    return {
        "accession": accession,
        "form": form,
        "filing_date": filing_date,
        "member_count": len(members),
        "members": members,
        "canonical": dict(members[0]),
    }


def parse_form_index_equivalence_class(
    body: IndexBody,
    *,
    accession: str,
    form: str,
    filing_date: str | date,
) -> dict[str, Any]:
    """Parse one SEC form.idx body into a deterministic 1..10 path class."""

    parsed_accession = _parse_accession(accession)
    parsed_form = _parse_expected_form(form)
    parsed_filing_date = _parse_iso_date(
        filing_date,
        code="form4_multipath_bulk_filing_date_invalid",
    ).isoformat()
    result = _build_equivalence_class(
        body,
        accession=parsed_accession,
        form=parsed_form,
        filing_date=parsed_filing_date,
        allow_missing=False,
    )
    assert result is not None
    return result


def resolve_form_index_carrier(
    *,
    accession: str,
    form: str,
    bulk_filing_date: str | date,
    d0_body: IndexBody | None,
    d1_body: IndexBody | None = None,
    d1_date: str | date | None = None,
) -> dict[str, Any]:
    """Resolve an exact accession carried by d0 xor a delayed d1 form.idx.

    The row embedded in either carrier must retain the bulk filing date.  A d1
    carrier is admissible only one to four calendar days after d0.
    """

    parsed_accession = _parse_accession(accession)
    parsed_form = _parse_expected_form(form)
    d0_date = _parse_iso_date(
        bulk_filing_date,
        code="form4_multipath_bulk_filing_date_invalid",
    )

    if (d1_body is None) != (d1_date is None):
        _fail(
            "form4_multipath_carrier_shape_invalid",
            "d1 body and d1 date must be supplied together",
        )
    parsed_d1_date: date | None = None
    if d1_date is not None:
        parsed_d1_date = _parse_iso_date(
            d1_date,
            code="form4_multipath_d1_date_window_invalid",
        )
        if not 1 <= (parsed_d1_date - d0_date).days <= 4:
            _fail(
                "form4_multipath_d1_date_window_invalid",
                "d1 must be one to four calendar days after d0",
            )

    expected_date = d0_date.isoformat()
    d0_class = (
        None
        if d0_body is None
        else _build_equivalence_class(
            d0_body,
            accession=parsed_accession,
            form=parsed_form,
            filing_date=expected_date,
            allow_missing=True,
        )
    )
    d1_class = (
        None
        if d1_body is None
        else _build_equivalence_class(
            d1_body,
            accession=parsed_accession,
            form=parsed_form,
            filing_date=expected_date,
            allow_missing=True,
        )
    )

    if (d0_class is None) == (d1_class is None):
        _fail(
            "form4_multipath_carrier_xor_invalid",
            "exact accession must occur in d0 xor d1",
        )

    carrier = "d0" if d0_class is not None else "d1"
    equivalence_class = d0_class if d0_class is not None else d1_class
    assert equivalence_class is not None
    carrier_date = d0_date if carrier == "d0" else parsed_d1_date
    assert carrier_date is not None
    return {
        "carrier": carrier,
        "carrier_date": carrier_date.isoformat(),
        "bulk_filing_date": expected_date,
        "filing_date": equivalence_class["filing_date"],
        "equivalence_class": equivalence_class,
    }


__all__ = [
    "FORM4_MULTIPATH_ERROR_CODES",
    "Form4MultipathIndexError",
    "parse_form_index_equivalence_class",
    "resolve_form_index_carrier",
]
