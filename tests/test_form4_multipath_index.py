from __future__ import annotations

from collections.abc import Callable

import pytest

from usfddk.form4_multipath_index import (
    FORM4_MULTIPATH_ERROR_CODES,
    Form4MultipathIndexError,
    parse_form_index_equivalence_class,
    resolve_form_index_carrier,
)

ACCESSION = "0000123456-26-000001"
FILING_DATE = "2026-06-30"


def _line(
    cik: str,
    *,
    form: str = "4",
    filing_date: str = "20260630",
    path_cik: str | None = None,
    basename: str | None = None,
) -> str:
    path = f"edgar/data/{path_cik or cik}/{basename or f'{ACCESSION}.txt'}"
    return f"{form:<12}{'Synthetic issuer':<67}{cik:>10} {filing_date} {path}\n"


def _body(*lines: str) -> bytes:
    return ("Form Type   Company Name" + "\n" + "".join(lines)).encode("latin-1")


def _code(action: Callable[[], object]) -> str:
    with pytest.raises(Form4MultipathIndexError) as caught:
        action()
    return caught.value.code


def _parse(body: bytes) -> dict[str, object]:
    return parse_form_index_equivalence_class(
        body,
        accession=ACCESSION,
        form="4",
        filing_date=FILING_DATE,
    )


def test_one_to_ten_distinct_paths_form_a_sorted_equivalence_class() -> None:
    lines = [_line(str(cik)) for cik in (42, 7, 100, 2)]
    expected = _parse(_body(*lines))
    reordered = _parse(_body(*reversed(lines)))

    assert reordered == expected
    assert expected["member_count"] == 4
    assert expected["members"] == [
        {"cik": "2", "path": f"edgar/data/2/{ACCESSION}.txt"},
        {"cik": "7", "path": f"edgar/data/7/{ACCESSION}.txt"},
        {"cik": "42", "path": f"edgar/data/42/{ACCESSION}.txt"},
        {"cik": "100", "path": f"edgar/data/100/{ACCESSION}.txt"},
    ]
    assert expected["canonical"] == expected["members"][0]


def test_unrelated_accessions_do_not_enter_the_equivalence_class() -> None:
    unrelated = _line("999").replace(ACCESSION, "0000123456-26-000002")
    result = _parse(_body(unrelated, _line("15")))
    assert result["member_count"] == 1
    assert result["canonical"] == {
        "cik": "15",
        "path": f"edgar/data/15/{ACCESSION}.txt",
    }


@pytest.mark.parametrize(
    ("mutation", "expected_code"),
    [
        (_body(), "form4_multipath_accession_missing"),
        (_body(_line("1"), _line("1")), "form4_multipath_exact_duplicate"),
        (
            _body(*(_line(str(cik)) for cik in range(1, 12))),
            "form4_multipath_equivalence_class_too_large",
        ),
        (_body(_line("1"), _line("2", form="4/A")), "form4_multipath_mixed_form"),
        (
            _body(_line("1"), _line("2", filing_date="20260701")),
            "form4_multipath_mixed_filing_date",
        ),
        (
            _body(_line("1", path_cik="2")),
            "form4_multipath_path_cik_drift",
        ),
        (
            _body(_line("1", basename=f"{ACCESSION}.txt.backup")),
            "form4_multipath_basename_drift",
        ),
    ],
)
def test_required_mutations_are_rejected_with_stable_codes(
    mutation: bytes,
    expected_code: str,
) -> None:
    assert expected_code in FORM4_MULTIPATH_ERROR_CODES
    assert _code(lambda: _parse(mutation)) == expected_code


def test_uniform_wrong_form_and_date_are_not_accepted_as_bulk_evidence() -> None:
    assert _code(lambda: _parse(_body(_line("1", form="4/A")))) == (
        "form4_multipath_form_mismatch"
    )
    assert _code(lambda: _parse(_body(_line("1", filing_date="20260701")))) == (
        "form4_multipath_filing_date_mismatch"
    )


def test_error_precedence_is_line_order_invariant() -> None:
    lines = [_line("3"), _line("3"), _line("2", form="4/A")]
    first = _code(lambda: _parse(_body(*lines)))
    second = _code(lambda: _parse(_body(*reversed(lines))))
    assert first == second == "form4_multipath_exact_duplicate"


def test_carrier_accepts_d0_xor_d1_and_preserves_bulk_row_date() -> None:
    unrelated = _body(_line("8").replace(ACCESSION, "0000123456-26-000002"))
    d0 = resolve_form_index_carrier(
        accession=ACCESSION,
        form="4",
        bulk_filing_date=FILING_DATE,
        d0_body=_body(_line("7"), _line("2")),
        d1_body=unrelated,
        d1_date="2026-07-01",
    )
    d1 = resolve_form_index_carrier(
        accession=ACCESSION,
        form="4",
        bulk_filing_date=FILING_DATE,
        d0_body=unrelated,
        d1_body=_body(_line("9")),
        d1_date="2026-07-03",
    )

    assert d0["carrier"] == "d0"
    assert d0["carrier_date"] == FILING_DATE
    assert d1["carrier"] == "d1"
    assert d1["carrier_date"] == "2026-07-03"
    assert d1["filing_date"] == FILING_DATE
    assert d1["equivalence_class"]["filing_date"] == FILING_DATE


@pytest.mark.parametrize(
    ("d0_body", "d1_body"),
    [
        (_body(), _body()),
        (_body(_line("1")), _body(_line("2"))),
    ],
)
def test_carrier_rejects_neither_or_both_exact_accession_matches(
    d0_body: bytes,
    d1_body: bytes,
) -> None:
    assert _code(
        lambda: resolve_form_index_carrier(
            accession=ACCESSION,
            form="4",
            bulk_filing_date=FILING_DATE,
            d0_body=d0_body,
            d1_body=d1_body,
            d1_date="2026-07-01",
        )
    ) == "form4_multipath_carrier_xor_invalid"


def test_d1_is_limited_to_four_calendar_days_after_d0() -> None:
    assert _code(
        lambda: resolve_form_index_carrier(
            accession=ACCESSION,
            form="4",
            bulk_filing_date=FILING_DATE,
            d0_body=_body(),
            d1_body=_body(_line("1")),
            d1_date="2026-07-05",
        )
    ) == "form4_multipath_d1_date_window_invalid"


def test_d1_row_cannot_replace_bulk_filing_date_with_carrier_date() -> None:
    assert _code(
        lambda: resolve_form_index_carrier(
            accession=ACCESSION,
            form="4",
            bulk_filing_date=FILING_DATE,
            d0_body=_body(),
            d1_body=_body(_line("1", filing_date="20260703")),
            d1_date="2026-07-03",
        )
    ) == "form4_multipath_filing_date_mismatch"


def test_d1_body_and_date_must_be_supplied_together() -> None:
    assert _code(
        lambda: resolve_form_index_carrier(
            accession=ACCESSION,
            form="4",
            bulk_filing_date=FILING_DATE,
            d0_body=_body(_line("1")),
            d1_body=_body(),
        )
    ) == "form4_multipath_carrier_shape_invalid"
