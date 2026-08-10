from __future__ import annotations

import copy
import hashlib
import io
import json
import zipfile
from dataclasses import replace
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

import usfddk.form4_historical_feasibility as history
from usfddk.form4_historical_feasibility import (
    AccessionPurchase,
    Form4HistoricalFeasibilityError,
    ParsedQuarter,
    _load_historical_protocol,
    _privacy_scan,
    build_historical_clusters,
    parse_quarter_archive,
)

ROOT = Path(__file__).resolve().parents[1]

_PHYSICAL_TEXT = {
    "SUBMISSION.tsv": "ACCESSION_NUMBER|FILING_DATE|PERIOD_OF_REPORT|DATE_OF_ORIG_SUB|NO_SECURITIES_OWNED|NOT_SUBJECT_SEC16|FORM3_HOLDINGS_REPORTED|FORM4_TRANS_REPORTED|DOCUMENT_TYPE|ISSUERCIK|ISSUERNAME|ISSUERTRADINGSYMBOL|REMARKS|AFF10B5ONE",
    "REPORTINGOWNER.tsv": "ACCESSION_NUMBER|RPTOWNERCIK|RPTOWNERNAME|RPTOWNER_RELATIONSHIP|RPTOWNER_TITLE|RPTOWNER_TXT|RPTOWNER_STREET1|RPTOWNER_STREET2|RPTOWNER_CITY|RPTOWNER_STATE|RPTOWNER_ZIPCODE|RPTOWNER_STATE_DESC|FILE_NUMBER",
    "NONDERIV_TRANS.tsv": "ACCESSION_NUMBER|NONDERIV_TRANS_SK|SECURITY_TITLE|SECURITY_TITLE_FN|TRANS_DATE|TRANS_DATE_FN|DEEMED_EXECUTION_DATE|DEEMED_EXECUTION_DATE_FN|TRANS_FORM_TYPE|TRANS_CODE|EQUITY_SWAP_INVOLVED|EQUITY_SWAP_TRANS_CD_FN|TRANS_TIMELINESS|TRANS_TIMELINESS_FN|TRANS_SHARES|TRANS_SHARES_FN|TRANS_PRICEPERSHARE|TRANS_PRICEPERSHARE_FN|TRANS_ACQUIRED_DISP_CD|TRANS_ACQUIRED_DISP_CD_FN|SHRS_OWND_FOLWNG_TRANS|SHRS_OWND_FOLWNG_TRANS_FN|VALU_OWND_FOLWNG_TRANS|VALU_OWND_FOLWNG_TRANS_FN|DIRECT_INDIRECT_OWNERSHIP|DIRECT_INDIRECT_OWNERSHIP_FN|NATURE_OF_OWNERSHIP|NATURE_OF_OWNERSHIP_FN",
    "NONDERIV_HOLDING.tsv": "ACCESSION_NUMBER|NONDERIV_HOLDING_SK|SECURITY_TITLE|SECURITY_TITLE_FN|TRANS_FORM_TYPE|TRANS_FORM_TYPE_FN|SHRS_OWND_FOLWNG_TRANS|SHRS_OWND_FOLWNG_TRANS_FN|VALU_OWND_FOLWNG_TRANS|VALU_OWND_FOLWNG_TRANS_FN|DIRECT_INDIRECT_OWNERSHIP|DIRECT_INDIRECT_OWNERSHIP_FN|NATURE_OF_OWNERSHIP|NATURE_OF_OWNERSHIP_FN",
    "DERIV_TRANS.tsv": "ACCESSION_NUMBER|DERIV_TRANS_SK|SECURITY_TITLE|SECURITY_TITLE_FN|CONV_EXERCISE_PRICE|CONV_EXERCISE_PRICE_FN|TRANS_DATE|TRANS_DATE_FN|DEEMED_EXECUTION_DATE|DEEMED_EXECUTION_DATE_FN|TRANS_FORM_TYPE|TRANS_CODE|EQUITY_SWAP_INVOLVED|EQUITY_SWAP_TRANS_CD_FN|TRANS_TIMELINESS|TRANS_TIMELINESS_FN|TRANS_SHARES|TRANS_SHARES_FN|TRANS_TOTAL_VALUE|TRANS_TOTAL_VALUE_FN|TRANS_PRICEPERSHARE|TRANS_PRICEPERSHARE_FN|TRANS_ACQUIRED_DISP_CD|TRANS_ACQUIRED_DISP_CD_FN|EXCERCISE_DATE|EXCERCISE_DATE_FN|EXPIRATION_DATE|EXPIRATION_DATE_FN|UNDLYNG_SEC_TITLE|UNDLYNG_SEC_TITLE_FN|UNDLYNG_SEC_SHARES|UNDLYNG_SEC_SHARES_FN|UNDLYNG_SEC_VALUE|UNDLYNG_SEC_VALUE_FN|SHRS_OWND_FOLWNG_TRANS|SHRS_OWND_FOLWNG_TRANS_FN|VALU_OWND_FOLWNG_TRANS|VALU_OWND_FOLWNG_TRANS_FN|DIRECT_INDIRECT_OWNERSHIP|DIRECT_INDIRECT_OWNERSHIP_FN|NATURE_OF_OWNERSHIP|NATURE_OF_OWNERSHIP_FN",
    "DERIV_HOLDING.tsv": "ACCESSION_NUMBER|DERIV_HOLDING_SK|SECURITY_TITLE|SECURITY_TITLE_FN|CONV_EXERCISE_PRICE|CONV_EXERCISE_PRICE_FN|TRANS_FORM_TYPE|TRANS_FORM_TYPE_FN|EXERCISE_DATE|EXERCISE_DATE_FN|EXPIRATION_DATE|EXPIRATION_DATE_FN|UNDLYNG_SEC_TITLE|UNDLYNG_SEC_TITLE_FN|UNDLYNG_SEC_SHARES|UNDLYNG_SEC_SHARES_FN|UNDLYNG_SEC_VALUE|UNDLYNG_SEC_VALUE_FN|SHRS_OWND_FOLWNG_TRANS|SHRS_OWND_FOLWNG_TRANS_FN|VALU_OWND_FOLWNG_TRANS|VALU_OWND_FOLWNG_TRANS_FN|DIRECT_INDIRECT_OWNERSHIP|DIRECT_INDIRECT_OWNERSHIP_FN|NATURE_OF_OWNERSHIP|NATURE_OF_OWNERSHIP_FN",
    "FOOTNOTES.tsv": "ACCESSION_NUMBER|FOOTNOTE_ID|FOOTNOTE_TXT",
    "OWNER_SIGNATURE.tsv": "ACCESSION_NUMBER|OWNERSIGNATURENAME|OWNERSIGNATUREDATE",
}
PHYSICAL = {key: tuple(value.split("|")) for key, value in _PHYSICAL_TEXT.items()}


def _metadata_header(role: str, quarter: str) -> tuple[str, ...]:
    values = list(PHYSICAL[role])
    if role == "SUBMISSION.tsv":
        if quarter != "2026Q2":
            values.remove("AFF10B5ONE")
        index = values.index("REMARKS")
        values[index:index] = [
            "CONTACT_NAME",
            "CONTACT_PHONE_NUMBER",
            "CONTACT_EMAIL_ADDRESS",
            "NOTIFICATION_EMAIL_ADDRESS",
        ]
    elif role in {"NONDERIV_TRANS.tsv", "DERIV_TRANS.tsv"}:
        values[11 if role == "NONDERIV_TRANS.tsv" else 13] = (
            "EQUITY_SWAP_INVOLVED_FN"
        )
    return tuple(values)


def _physical_header(role: str, quarter: str) -> tuple[str, ...]:
    if role == "SUBMISSION.tsv" and quarter != "2026Q2":
        return tuple(item for item in PHYSICAL[role] if item != "AFF10B5ONE")
    return PHYSICAL[role]


def _row(header: tuple[str, ...], **values: str) -> str:
    return "\t".join(values.get(name, "") for name in header)


def _archive(
    *,
    quarter: str = "2026Q2",
    submissions: list[dict[str, str]] | None = None,
    owners: list[dict[str, str]] | None = None,
    transactions: list[dict[str, str]] | None = None,
    mutate_submission_header: bool = False,
    unsafe_member: bool = False,
) -> bytes:
    metadata = {
        "tables": [
            {
                "url": role,
                "tableSchema": {
                    "columns": [
                        {"name": name} for name in _metadata_header(role, quarter)
                    ]
                },
            }
            for role in PHYSICAL
        ]
    }
    rows_by_role = {
        "SUBMISSION.tsv": submissions or [],
        "REPORTINGOWNER.tsv": owners or [],
        "NONDERIV_TRANS.tsv": transactions or [],
    }
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("FORM_345_metadata.json", json.dumps(metadata))
        archive.writestr("FORM_345_readme.htm", "<p>synthetic fixture</p>")
        for role in PHYSICAL:
            header = _physical_header(role, quarter)
            if role == "SUBMISSION.tsv" and mutate_submission_header:
                header = tuple(item for item in header if item != "REMARKS")
            lines = ["\t".join(header)]
            lines.extend(_row(header, **row) for row in rows_by_role.get(role, []))
            archive.writestr(role, "\n".join(lines) + "\n")
        if unsafe_member:
            archive.writestr("../escape.txt", "forbidden")
    return buffer.getvalue()


def _accept_fixture(monkeypatch: pytest.MonkeyPatch, body: bytes) -> None:
    protocol = _load_historical_protocol(ROOT)
    source = next(
        item
        for item in protocol["fixed_offline_sources"]
        if item["quarter"] == "2026Q2"
    )
    source = {
        **source,
        "bytes": len(body),
        "sha256": hashlib.sha256(body).hexdigest(),
    }
    fixture_protocol = copy.deepcopy(protocol)
    fixture_protocol["fixed_offline_sources"] = [
        source if item["quarter"] == "2026Q2" else item
        for item in fixture_protocol["fixed_offline_sources"]
    ]
    monkeypatch.setattr(history, "_load_historical_protocol", lambda _: fixture_protocol)


def _base_rows() -> tuple[
    list[dict[str, str]], list[dict[str, str]], list[dict[str, str]]
]:
    first = "0000000001-26-000001"
    second = "0000000002-26-000002"
    submissions = [
        {
            "ACCESSION_NUMBER": first,
            "FILING_DATE": "20-APR-2026",
            "DOCUMENT_TYPE": "4",
            "ISSUERCIK": "100",
        },
        {
            "ACCESSION_NUMBER": second,
            "FILING_DATE": "21-APR-2026",
            "DOCUMENT_TYPE": "4",
            "ISSUERCIK": "100",
        },
    ]
    owners = [
        {
            "ACCESSION_NUMBER": first,
            "RPTOWNERCIK": "201",
            "RPTOWNER_RELATIONSHIP": "Director,Officer",
        },
        {
            "ACCESSION_NUMBER": first,
            "RPTOWNERCIK": "202",
            "RPTOWNER_RELATIONSHIP": "Director",
        },
        {
            "ACCESSION_NUMBER": second,
            "RPTOWNERCIK": "203",
            "RPTOWNER_RELATIONSHIP": "Officer",
        },
    ]
    transactions = [
        {
            "ACCESSION_NUMBER": first,
            "NONDERIV_TRANS_SK": "1",
            "TRANS_FORM_TYPE": "4",
            "TRANS_CODE": "P",
            "EQUITY_SWAP_INVOLVED": "0",
            "TRANS_SHARES": "3000",
            "TRANS_PRICEPERSHARE": "10",
            "TRANS_ACQUIRED_DISP_CD": "A",
        },
        {
            "ACCESSION_NUMBER": first,
            "NONDERIV_TRANS_SK": "2",
            "TRANS_FORM_TYPE": "4",
            "TRANS_CODE": "P",
            "EQUITY_SWAP_INVOLVED": "false",
            "TRANS_SHARES": "3000",
            "TRANS_PRICEPERSHARE": "10",
            "TRANS_ACQUIRED_DISP_CD": "A",
        },
        {
            "ACCESSION_NUMBER": second,
            "NONDERIV_TRANS_SK": "3",
            "TRANS_FORM_TYPE": "4",
            "TRANS_CODE": "P",
            "EQUITY_SWAP_INVOLVED": "0",
            "TRANS_SHARES": "5000",
            "TRANS_PRICEPERSHARE": "10",
            "TRANS_ACQUIRED_DISP_CD": "A",
        },
    ]
    return submissions, owners, transactions


def _parse_fixture(
    monkeypatch: pytest.MonkeyPatch,
    *,
    submissions: list[dict[str, str]] | None = None,
    owners: list[dict[str, str]] | None = None,
    transactions: list[dict[str, str]] | None = None,
    **archive_options: bool,
) -> ParsedQuarter:
    base_submissions, base_owners, base_transactions = _base_rows()
    body = _archive(
        submissions=base_submissions if submissions is None else submissions,
        owners=base_owners if owners is None else owners,
        transactions=base_transactions if transactions is None else transactions,
        **archive_options,
    )
    _accept_fixture(monkeypatch, body)
    return parse_quarter_archive(
        body,
        quarter="2026Q2",
        repository_root=ROOT,
        filename="2026q2_form345.zip",
    )


def _error_code(action: object) -> str:
    with pytest.raises(Form4HistoricalFeasibilityError) as caught:
        action()  # type: ignore[operator]
    return caught.value.code


def test_protocol_and_committed_validation_receipt_are_self_bound() -> None:
    receipt = _load_historical_protocol(ROOT)
    assert receipt["receipt_sha256"] == history.EXPECTED_PROTOCOL_RECEIPT_SHA256
    validation_path = (
        ROOT / "artifacts/short_term_form4_historical_feasibility_validation.json"
    )
    validation = json.loads(validation_path.read_text(encoding="utf-8"))
    claimed = validation.pop("receipt_sha256")
    assert history._canonical_sha256(validation) == claimed
    assert validation["aggregate_event_gate"] == {
        "minimum_primary_clusters": 30,
        "observed_primary_clusters": 805,
        "parameters_reselected_after_result": False,
        "passed": True,
    }
    assert validation["state_boundary"]["performance_present"] is False
    assert validation["state_boundary"]["paper_authorized"] is False
    assert validation["state_boundary"]["real_money_action_usd"] == 0
    _privacy_scan(validation)


def test_valid_fixture_does_not_multiply_notional_by_joint_owner_count(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    parsed = _parse_fixture(monkeypatch)
    assert parsed.eligible_transaction_rows == 3
    assert len(parsed.purchase_accessions) == 2
    first, second = parsed.purchase_accessions
    assert first.reported_purchase_dollars == Decimal("60000")
    assert len(first.owner_ciks) == 2
    assert second.reported_purchase_dollars == Decimal("50000")
    audit = build_historical_clusters(parsed)
    assert audit.raw_gate_crossings == 1
    assert len(audit.primary_clusters) == 1
    cluster = audit.primary_clusters[0]
    assert cluster.reported_purchase_dollars == Decimal("110000")
    assert len(cluster.member_accessions) == 2
    assert len(cluster.owner_ciks) == 3


def test_amendment_swap_unknown_substring_role_and_nonfinite_values_are_excluded(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    submissions, owners, transactions = _base_rows()
    reasons = (
        ("0000000010-26-000010", "4/A", "Director", "P", "0", "100", "10"),
        ("0000000011-26-000011", "4", "Director", "P", "", "100", "10"),
        (
            "0000000012-26-000012",
            "4",
            "TenPercentOwnerOther",
            "P",
            "0",
            "100",
            "10",
        ),
        ("0000000013-26-000013", "4", "Director", "P", "0", "100", "NaN"),
        ("0000000014-26-000014", "4", "Director", "S", "0", "100", "10"),
        ("0000000015-26-000015", "4", "Director", "P", "0", "0", "10"),
    )
    for serial, (accession, form, role, code, swap, shares, price) in enumerate(
        reasons, start=10
    ):
        submissions.append(
            {
                "ACCESSION_NUMBER": accession,
                "FILING_DATE": "20-APR-2026",
                "DOCUMENT_TYPE": form,
                "ISSUERCIK": str(1000 + serial),
            }
        )
        owners.append(
            {
                "ACCESSION_NUMBER": accession,
                "RPTOWNERCIK": str(2000 + serial),
                "RPTOWNER_RELATIONSHIP": role,
            }
        )
        transactions.append(
            {
                "ACCESSION_NUMBER": accession,
                "NONDERIV_TRANS_SK": str(100 + serial),
                "TRANS_FORM_TYPE": "4",
                "TRANS_CODE": code,
                "EQUITY_SWAP_INVOLVED": swap,
                "TRANS_SHARES": shares,
                "TRANS_PRICEPERSHARE": price,
                "TRANS_ACQUIRED_DISP_CD": "A",
            }
        )
    parsed = _parse_fixture(
        monkeypatch,
        submissions=submissions,
        owners=owners,
        transactions=transactions,
    )
    assert parsed.transaction_exclusion_counts == {
        "non_primary_form4_submission": 1,
        "not_purchase_code": 1,
        "price_not_positive_finite": 1,
        "relationship_not_eligible": 1,
        "shares_not_positive_finite": 1,
        "swap_not_proven_false": 1,
    }
    assert len(parsed.purchase_accessions) == 2


def test_duplicate_transaction_owner_and_unknown_accession_fail_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    submissions, owners, transactions = _base_rows()
    transactions.append(dict(transactions[0]))
    assert _error_code(
        lambda: _parse_fixture(
            monkeypatch,
            submissions=submissions,
            owners=owners,
            transactions=transactions,
        )
    ) == "form4_history_key_duplicate"

    monkeypatch.undo()
    submissions, owners, transactions = _base_rows()
    owners.append(dict(owners[0]))
    assert _error_code(
        lambda: _parse_fixture(
            monkeypatch,
            submissions=submissions,
            owners=owners,
            transactions=transactions,
        )
    ) == "form4_history_key_duplicate"

    monkeypatch.undo()
    submissions, owners, transactions = _base_rows()
    transactions[0]["ACCESSION_NUMBER"] = "0000000099-26-000099"
    assert _error_code(
        lambda: _parse_fixture(
            monkeypatch,
            submissions=submissions,
            owners=owners,
            transactions=transactions,
        )
    ) == "form4_history_schema_invalid"


def test_zip_traversal_header_drift_and_source_hash_are_rejected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert _error_code(
        lambda: _parse_fixture(monkeypatch, unsafe_member=True)
    ) == "form4_history_zip_invalid"
    monkeypatch.undo()
    assert _error_code(
        lambda: _parse_fixture(monkeypatch, mutate_submission_header=True)
    ) == "form4_history_schema_invalid"
    monkeypatch.undo()
    assert _error_code(
        lambda: parse_quarter_archive(
            b"not-the-frozen-archive",
            quarter="2026Q2",
            repository_root=ROOT,
            filename="2026q2_form345.zip",
        )
    ) == "form4_history_source_mismatch"


def _purchase(
    serial: int,
    when: date,
    owner: int,
    notional: str,
    *,
    issuer: str = "100",
) -> AccessionPurchase:
    return AccessionPurchase(
        accession=f"{serial:010d}-26-{serial:06d}",
        issuer_cik=issuer,
        filing_date=when,
        owner_ciks=(str(owner),),
        reported_purchase_dollars=Decimal(notional),
        eligible_transaction_rows=1,
    )


def test_left_boundary_cooldown_and_same_day_order_are_deterministic() -> None:
    purchases = (
        _purchase(1, date(2026, 4, 1), 1, "60000"),
        _purchase(2, date(2026, 4, 1), 2, "50000"),
        _purchase(3, date(2026, 4, 10), 3, "60000"),
        _purchase(4, date(2026, 4, 20), 4, "50000"),
        _purchase(5, date(2026, 4, 22), 5, "10000"),
        _purchase(6, date(2026, 4, 30), 6, "60000"),
        _purchase(7, date(2026, 5, 12), 7, "50000"),
        _purchase(8, date(2026, 5, 13), 8, "10000"),
        _purchase(9, date(2026, 5, 13), 9, "9999"),
    )
    parsed = ParsedQuarter(
        quarter="2026Q2",
        filename="fixture.zip",
        body_sha256="0" * 64,
        byte_count=1,
        row_counts={},
        submission_type_counts={},
        form4_submission_count=9,
        amendment_submission_count=0,
        transaction_exclusion_counts={},
        eligible_transaction_rows=9,
        purchase_accessions=purchases,
    )
    first = build_historical_clusters(parsed)
    second = build_historical_clusters(
        replace(parsed, purchase_accessions=tuple(reversed(purchases)))
    )
    assert first == second
    assert first.raw_gate_crossings == 3
    assert len(first.left_boundary_clusters) == 1
    assert len(first.primary_clusters) == 2
    assert [cluster.decision_date for cluster in first.primary_clusters] == [
        date(2026, 4, 22),
        date(2026, 5, 13),
    ]
    assert first.accessions_below_minimum == 1
    assert first.cooldown_suppressed_filing_dates == 4


def test_distinct_owner_accession_and_twenty_day_window_gates_are_exact() -> None:
    def parsed(*purchases: AccessionPurchase) -> ParsedQuarter:
        return ParsedQuarter(
            quarter="2026Q2",
            filename="fixture.zip",
            body_sha256="0" * 64,
            byte_count=1,
            row_counts={},
            submission_type_counts={},
            form4_submission_count=len(purchases),
            amendment_submission_count=0,
            transaction_exclusion_counts={},
            eligible_transaction_rows=len(purchases),
            purchase_accessions=tuple(purchases),
        )

    same_owner = build_historical_clusters(
        parsed(
            _purchase(10, date(2026, 4, 20), 1, "60000"),
            _purchase(11, date(2026, 4, 21), 1, "60000"),
        )
    )
    assert same_owner.raw_gate_crossings == 0

    joint_single_accession = build_historical_clusters(
        parsed(
            replace(
                _purchase(12, date(2026, 4, 20), 1, "120000"),
                owner_ciks=("1", "2"),
            )
        )
    )
    assert joint_single_accession.raw_gate_crossings == 0

    inclusive_boundary = build_historical_clusters(
        parsed(
            _purchase(13, date(2026, 4, 20), 1, "60000"),
            _purchase(14, date(2026, 5, 9), 2, "50000"),
        )
    )
    assert len(inclusive_boundary.primary_clusters) == 1

    outside_boundary = build_historical_clusters(
        parsed(
            _purchase(15, date(2026, 4, 20), 1, "60000"),
            _purchase(16, date(2026, 5, 10), 2, "50000"),
        )
    )
    assert outside_boundary.raw_gate_crossings == 0


def test_privacy_scan_rejects_identifier_keys_and_accession_like_values() -> None:
    assert _error_code(lambda: _privacy_scan({"ticker": "SYN"})) == (
        "form4_history_privacy_boundary"
    )
    assert _error_code(
        lambda: _privacy_scan({"safe": "0000000001-26-000001"})
    ) == "form4_history_privacy_boundary"
    _privacy_scan(
        {
            "quarter": "2026Q2",
            "primary_cluster_count": 10,
            "reported_notional": {"100k_to_250k": 10},
        }
    )
