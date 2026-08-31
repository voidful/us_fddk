from __future__ import annotations

import copy
import hashlib
import io
import json
import zipfile
from pathlib import Path

import pytest

from usfddk.form4_admission_feasibility import (
    Form4AdmissionFeasibilityError,
    _admission_controls,
    _daily_index_row,
    _load_protocol_binding,
    _parse_complete_submission,
    _parse_quarter_zip,
    _physical_header_projection,
    _validate_physical_header_profile,
    build_form4_feasibility_failure_receipt,
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


def _amendment_receipt() -> dict[str, object]:
    return json.loads(
        (ROOT / "artifacts/short_term_form4_admission_feasibility_schema_amendment_v1_1_receipt.json").read_text()
    )


def _metadata(role: str, quarter: str) -> tuple[str, ...]:
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
        values[11 if role == "NONDERIV_TRANS.tsv" else 13] = "EQUITY_SWAP_INVOLVED_FN"
    return tuple(values)


def _code(action: object) -> str:
    with pytest.raises(Form4AdmissionFeasibilityError) as caught:
        action()  # type: ignore[operator]
    return caught.value.code


def test_v1_1_binding_and_all_eight_metadata_projections_are_exact() -> None:
    binding = _load_protocol_binding(ROOT)
    amendment = binding["amendment_receipt"]
    for quarter in ("2006Q1", "2016Q3", "2026Q2"):
        for role, physical_2026 in PHYSICAL.items():
            physical = physical_2026
            if role == "SUBMISSION.tsv" and quarter != "2026Q2":
                physical = tuple(item for item in physical if item != "AFF10B5ONE")
            projected = _physical_header_projection(
                _metadata(role, quarter),
                table_name=role,
                quarter_id=quarter,
                amendment_receipt=amendment,
            )
            assert projected == physical
            _validate_physical_header_profile(
                projected,
                table_name=role,
                quarter_id=quarter,
                amendment_receipt=amendment,
            )


def test_schema_projection_mutations_fail_closed() -> None:
    amendment = _amendment_receipt()
    submission = list(_metadata("SUBMISSION.tsv", "2026Q2"))
    submission.remove("CONTACT_EMAIL_ADDRESS")
    assert _code(
        lambda: _physical_header_projection(
            tuple(submission),
            table_name="SUBMISSION.tsv",
            quarter_id="2026Q2",
            amendment_receipt=amendment,
        )
    ) == "form4_feasibility_contact_omission_mismatch"
    trans = list(_metadata("NONDERIV_TRANS.tsv", "2026Q2"))
    trans[11] = "ARBITRARY_ALIAS"
    assert _code(
        lambda: _physical_header_projection(
            tuple(trans),
            table_name="NONDERIV_TRANS.tsv",
            quarter_id="2026Q2",
            amendment_receipt=amendment,
        )
    ) == "form4_feasibility_swap_footnote_alias_mismatch"
    drifted = list(PHYSICAL["FOOTNOTES.tsv"])
    drifted[-1] = "FOOTNOTE_TEXT"
    assert _code(
        lambda: _validate_physical_header_profile(
            tuple(drifted),
            table_name="FOOTNOTES.tsv",
            quarter_id="2026Q2",
            amendment_receipt=amendment,
        )
    ) == "form4_feasibility_physical_header_profile_mismatch"


def test_full_zip_parser_selects_only_frozen_rows_and_streams_other_tables() -> None:
    metadata = {
        "tables": [
            {
                "url": role,
                "tableSchema": {
                    "columns": [{"name": name} for name in _metadata(role, "2026Q2")]
                },
            }
            for role in PHYSICAL
        ]
    }
    submission_header = PHYSICAL["SUBMISSION.tsv"]
    rows: list[str] = []
    fixtures = (
        (1, "01-APR-2026", "4"),
        (2, "02-APR-2026", "4/A"),
        (3, "03-APR-2026", "4"),
        (4, "06-APR-2026", "4"),
        (5, "07-APR-2026", "4"),
    )
    for serial, filing_date, form in fixtures:
        values = {name: "" for name in submission_header}
        values.update(
            {
                "ACCESSION_NUMBER": f"{serial:010d}-26-{serial:06d}",
                "FILING_DATE": filing_date,
                "DOCUMENT_TYPE": form,
                "ISSUERCIK": str(1000 + serial),
            }
        )
        rows.append("\t".join(values[name] for name in submission_header))
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("FORM_345_METADATA.json", json.dumps(metadata))
        archive.writestr("FORM_345_README.htm", "<p>synthetic schema fixture</p>")
        for role, header in PHYSICAL.items():
            content = "\t".join(header) + "\n"
            if role == "SUBMISSION.tsv":
                content += "\n".join(rows) + "\n"
            archive.writestr(role, content)
    body = buffer.getvalue()
    receipt = {
        "source_kind": "insider_transactions_quarter_zip",
        "requested_url": "https://www.sec.gov/files/2026q2_form345.zip",
        "known_at": None,
        "public_at": None,
        "observation_mode": "engineering_fetch_not_contemporaneous_evidence",
        "body_sha256": hashlib.sha256(body).hexdigest(),
        "byte_count": len(body),
        "receipt_sha256": "a" * 64,
    }

    class FixtureClient:
        @staticmethod
        def object_bytes(receipt_value: object) -> bytes:
            assert receipt_value is receipt
            return body

    binding = _load_protocol_binding(ROOT)
    parsed = _parse_quarter_zip(
        FixtureClient(),  # type: ignore[arg-type]
        "2026Q2",
        receipt,
        required_headers=binding["receipt"]["quarterly_zip_contract"]["required_tables"],
        amendment_receipt=binding["amendment_receipt"],
    )
    assert len(parsed["form4_rows"]) == 5
    assert len(parsed["samples"]) == 4
    assert parsed["amendment_state"] == "amendment_added"
    assert all(
        not rows_value
        for role, rows_value in parsed["tables"].items()
        if role != "SUBMISSION.tsv"
    )


def test_daily_index_is_right_anchored_and_archive_cik_is_not_issuer_cik() -> None:
    accession = "0000123456-26-000001"
    archive_cik = "7654321"
    path = f"edgar/data/{archive_cik}/{accession}.txt"
    line = f"{'4':<12}{'Synthetic Issuer':<67}{archive_cik:>10} 20260630 {path}\n"
    row = _daily_index_row(
        line.encode(),
        accession=accession,
        form="4",
        filing_date="2026-06-30",
    )
    assert row["cik"] == archive_cik
    assert row["path"] == path
    assert _code(
        lambda: _daily_index_row(
            (line + line).encode(),
            accession=accession,
            form="4",
            filing_date="2026-06-30",
        )
    ) == "form4_feasibility_daily_index_missing_or_ambiguous"
    assert _code(
        lambda: _daily_index_row(
            line.replace(".txt", ".txt.backup").encode(),
            accession=accession,
            form="4",
            filing_date="2026-06-30",
        )
    ) == "form4_feasibility_daily_index_missing_or_ambiguous"


def _sgml(*, dtd: bool = False, duplicate_primary: bool = False) -> bytes:
    accession = "0000123456-26-000001"
    xml = (
        ("<!DOCTYPE ownershipDocument [<!ENTITY x 'bad'>]>" if dtd else "")
        + "<ownershipDocument><documentType>4</documentType>"
        "<issuer><issuerCik>123456</issuerCik></issuer></ownershipDocument>"
    )
    document = f"<DOCUMENT><TYPE>4<SEQUENCE>1<TEXT>{xml}</TEXT></DOCUMENT>"
    return (
        f"<SEC-DOCUMENT><ACCESSION-NUMBER>{accession}\n"
        f"<CONFORMED-SUBMISSION-TYPE>4\n{document}"
        f"{document if duplicate_primary else ''}</SEC-DOCUMENT>"
    ).encode()


def test_complete_submission_requires_one_safe_primary_document_identity() -> None:
    parsed = _parse_complete_submission(_sgml())
    assert parsed["accession"] == "0000123456-26-000001"
    assert parsed["header_form"] == parsed["xml_form"] == "4"
    assert parsed["issuer_cik"] == "123456"
    assert _code(lambda: _parse_complete_submission(_sgml(dtd=True))) == (
        "form4_feasibility_complete_submission_mismatch"
    )
    assert _code(lambda: _parse_complete_submission(_sgml(duplicate_primary=True))) == (
        "form4_feasibility_complete_submission_mismatch"
    )


def test_public_receipts_are_redacted_and_admission_stays_two_of_sixteen() -> None:
    secret = "0000123456-26-000001 Synthetic Person 123456"
    failure = build_form4_feasibility_failure_receipt(
        Form4AdmissionFeasibilityError(
            "form4_feasibility_complete_submission_mismatch", secret
        )
    )
    rendered = json.dumps(failure, sort_keys=True)
    assert secret not in rendered
    assert "0000123456-26-000001" not in rendered
    assert failure["status"] == "stopped_no_admission_claim"
    controls = _admission_controls()
    assert controls["passed"] == 2
    assert controls["total"] == 16
    assert controls["all_passed"] is False
    passed = [gate["id"] for gate in controls["gates"] if gate["passed"]]
    assert passed == ["01", "04"]
    mutated = copy.deepcopy(controls)
    assert len(mutated["gates"]) == 16

    real_controls = _admission_controls(real_sample_replayed=True)
    assert real_controls["passed"] == 3
    assert [gate["id"] for gate in real_controls["gates"] if gate["passed"]] == [
        "01",
        "04",
        "16",
    ]
    assert real_controls["candidate_selection_authorized"] is False
    assert real_controls["strategy_run_authorized"] is False
