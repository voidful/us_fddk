from __future__ import annotations

from collections.abc import Callable, Iterable
from datetime import date

import pytest

from usfddk.form4_multipath_reconciliation_v2 import (
    FORM4_FORWARD_RECONCILIATION_ERROR_CODES,
    Form4MultipathReconciliationError,
    reconcile_form_index_pair,
)

ACCESSION = "0000123456-26-000001"
D0 = "2026-06-30"
OTHER_ACCESSION = "0000123456-26-000002"


def _line(
    cik: str,
    *,
    accession: str = ACCESSION,
    form: str = "4",
    filed: str = "20260630",
    path: str | None = None,
    name: str = "Synthetic issuer",
) -> str:
    archive_path = path or f"edgar/data/{int(cik)}/{accession}.txt"
    return f"{form:<12}{name:<67}{cik:>10} {filed} {archive_path}\n"


def _body(*rows: str) -> bytes:
    return ("Form Type   Company Name\n" + "".join(rows)).encode("latin-1")


def _unrelated() -> bytes:
    return _body(_line("99", accession=OTHER_ACCESSION))


def _reconcile(
    *,
    d0_body: object = None,
    d1_body: object = None,
    dates: object = ("2026-06-30", "2026-07-01"),
) -> dict[str, object]:
    return reconcile_form_index_pair(
        accession=ACCESSION,
        form="4",
        bulk_filing_date=D0,
        d0_body=d0_body,  # type: ignore[arg-type]
        d1_body=d1_body,  # type: ignore[arg-type]
        published_form_index_dates=dates,  # type: ignore[arg-type]
    )


def _code(action: Callable[[], object]) -> str:
    with pytest.raises(Form4MultipathReconciliationError) as caught:
        action()
    assert caught.value.code in FORM4_FORWARD_RECONCILIATION_ERROR_CODES
    return caught.value.code


@pytest.mark.parametrize("form", ["4", "4/A"])
def test_only_exact_form4_values_reconcile_normally(form: str) -> None:
    result = reconcile_form_index_pair(
        accession=ACCESSION,
        form=form,
        bulk_filing_date=D0,
        d0_body=_body(_line("1", form=form)),
        d1_body=_unrelated(),
        published_form_index_dates=("2026-06-30", "2026-07-01"),
    )
    assert result["form"] == form
    assert result["equivalence_class"]["form"] == form


@pytest.mark.parametrize(
    "form",
    [
        "congress_house_ptr",
        "congress_senate_ptr",
        "PTR",
        "house",
        "senate",
        "house_member",
        "houseMember",
        "senate_trade",
        "ptr_report",
        "representative_trade",
        "capitol_trade",
        "politician",
    ],
)
def test_congress_form_arguments_have_one_canonical_stop(form: str) -> None:
    assert _code(
        lambda: reconcile_form_index_pair(
            accession=ACCESSION,
            form=form,
            bulk_filing_date=D0,
            d0_body=_body(_line("1")),
            d1_body=_unrelated(),
            published_form_index_dates=("2026-06-30", "2026-07-01"),
        )
    ) == "form4_forward_congress_field_injection"


@pytest.mark.parametrize(
    "injected_form",
    [
        "PTR",
        "house",
        "congress_senate_ptr",
        "house_member",
        "houseMember",
        "senate_trade",
        "ptr_report",
        "representative_trade",
        "capitol_trade",
        "politician",
    ],
)
def test_congress_row_in_a_form4_equivalence_class_has_canonical_stop(
    injected_form: str,
) -> None:
    rows = (_line("1"), _line("2", form=injected_form))
    assert _code(lambda: _reconcile(d0_body=_body(*rows), d1_body=_unrelated())) == (
        "form4_forward_congress_field_injection"
    )


@pytest.mark.parametrize("count", [1, 2, 10])
def test_project_cap_accepts_one_two_and_ten_paths_in_canonical_order(count: int) -> None:
    rows = [_line(str(cik)) for cik in range(count, 0, -1)]
    result = _reconcile(d0_body=_body(*rows), d1_body=_unrelated())
    equivalence = result["equivalence_class"]
    assert isinstance(equivalence, dict)
    assert equivalence["path_count"] == count
    assert equivalence["project_path_cap"] == 10
    assert equivalence["canonical"] == {
        "cik": "1",
        "path": f"edgar/data/1/{ACCESSION}.txt",
    }


def test_row_and_published_date_order_do_not_change_reconciliation() -> None:
    rows = [_line("42"), _line("2"), _line("9")]
    first = _reconcile(
        d0_body=_body(*rows),
        d1_body=_unrelated(),
        dates=("2026-07-08", "2026-07-01", "2026-06-30", "2026-06-29"),
    )
    second = _reconcile(
        d0_body=_body(*reversed(rows)),
        d1_body=_unrelated(),
        dates=("2026-06-29", "2026-06-30", "2026-07-01", "2026-07-08"),
    )
    first_input_seal = first.pop("input_seal")
    second_input_seal = second.pop("input_seal")
    assert first == second
    assert first_input_seal["d0_body_sha256"] != second_input_seal["d0_body_sha256"]
    assert first_input_seal["d1_body_sha256"] == second_input_seal["d1_body_sha256"]
    assert (
        first_input_seal["published_form_index_dates_sha256"]
        == second_input_seal["published_form_index_dates_sha256"]
    )
    assert first["d1_date"] == "2026-07-01"


def test_d1_carrier_preserves_bulk_date_filed() -> None:
    result = _reconcile(
        d0_body=_unrelated(),
        d1_body=_body(_line("7")),
        dates=(date(2026, 6, 30), date(2026, 7, 3)),
    )
    assert result["carrier"] == "d1"
    assert result["carrier_date"] == "2026-07-03"
    assert result["equivalence_class"]["filing_date"] == D0


@pytest.mark.parametrize(
    ("d0_body", "d1_body"),
    [
        (None, _body(_line("1"))),
        (_body(_line("1")), None),
        (b"", _body(_line("1"))),
        (_body(_line("1")), "   "),
    ],
)
def test_both_nonempty_index_bodies_are_required(d0_body: object, d1_body: object) -> None:
    assert _code(lambda: _reconcile(d0_body=d0_body, d1_body=d1_body)) == (
        "form4_forward_denominator_incomplete"
    )


@pytest.mark.parametrize(
    "dates",
    [
        ("2026-06-30", "2026-06-30", "2026-07-01"),
        ("2026-06-29", "2026-07-01"),
        ("2026-06-30",),
        ("2026-06-30", "2026-07-05"),
    ],
)
def test_manifest_dates_must_be_unique_include_d0_and_supply_d1_within_four_days(
    dates: Iterable[str],
) -> None:
    assert _code(
        lambda: _reconcile(d0_body=_body(_line("1")), d1_body=_unrelated(), dates=dates)
    ) == "form4_forward_d1_window_invalid"


@pytest.mark.parametrize(
    "path",
    [
        f"edgar//data/1/{ACCESSION}.txt",
        f"edgar/data/1/./{ACCESSION}.txt",
        f"edgar/data/0001/{ACCESSION}.txt",
        f"edgar/data/1/{ACCESSION}.txt?download=1",
        f"EDGAR/data/1/{ACCESSION}.txt",
        f"edgar/data/1/{ACCESSION}.TXT",
    ],
)
def test_raw_path_must_equal_the_single_canonical_archive_spelling(path: str) -> None:
    assert _code(
        lambda: _reconcile(
            d0_body=_body(_line("1", path=path)),
            d1_body=_unrelated(),
        )
    ) == "form4_forward_multipath_identity_mismatch"


@pytest.mark.parametrize(
    ("d0_body", "d1_body"),
    [
        (_unrelated(), _unrelated()),
        (_body(_line("1")), _body(_line("2"))),
    ],
)
def test_exact_accession_must_be_carried_by_d0_xor_d1(
    d0_body: bytes,
    d1_body: bytes,
) -> None:
    assert _code(lambda: _reconcile(d0_body=d0_body, d1_body=d1_body)) == (
        "form4_forward_cross_day_missing_or_ambiguous"
    )


def test_eleven_paths_exceed_the_project_cap() -> None:
    body = _body(*(_line(str(cik)) for cik in range(1, 12)))
    assert _code(lambda: _reconcile(d0_body=body, d1_body=_unrelated())) == (
        "form4_forward_project_path_cap_exceeded"
    )


def test_exact_raw_duplicate_has_its_own_stable_code() -> None:
    row = _line("1")
    assert _code(lambda: _reconcile(d0_body=_body(row, row), d1_body=_unrelated())) == (
        "form4_forward_multipath_duplicate_row"
    )


@pytest.mark.parametrize(
    "rows",
    [
        (_line("1"), _line("2", form="4/A")),
        (_line("1"), _line("2", filed="20260701")),
        (
            _line("1"),
            _line("01", name="Different raw issuer representation"),
        ),
        (
            _line("1", path=f"edgar/data/2/{ACCESSION}.txt"),
        ),
    ],
)
def test_mixed_metadata_or_collapsed_identity_is_rejected(rows: tuple[str, ...]) -> None:
    assert _code(lambda: _reconcile(d0_body=_body(*rows), d1_body=_unrelated())) == (
        "form4_forward_multipath_identity_mismatch"
    )
