from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
V1_PROTOCOL = ROOT / "docs/SHORT_TERM_FORM4_ADMISSION_FEASIBILITY_PROTOCOL.md"
V1_RECEIPT = ROOT / "artifacts/short_term_form4_admission_feasibility_protocol_receipt.json"
AMENDMENT = ROOT / "docs/SHORT_TERM_FORM4_ADMISSION_FEASIBILITY_SCHEMA_AMENDMENT_V1_1.md"
RECEIPT = (
    ROOT
    / "artifacts/short_term_form4_admission_feasibility_schema_amendment_v1_1_receipt.json"
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    assert parsed.tzinfo is not None
    return parsed.astimezone(UTC)


def _receipt() -> dict[str, Any]:
    return json.loads(RECEIPT.read_text(encoding="utf-8"))


def _expected_physical(
    role: str, metadata_columns: list[str], policy: dict[str, Any]
) -> list[str]:
    output = list(metadata_columns)
    contact = policy["submission_contact_omission"]
    if role == contact["role"]:
        expected = [
            contact["metadata_left_anchor"],
            *contact["metadata_only_columns"],
            contact["metadata_right_anchor"],
        ]
        starts = [
            index
            for index in range(len(output) - len(expected) + 1)
            if output[index : index + len(expected)] == expected
        ]
        if starts != [starts[0]] if starts else True:
            raise ValueError("form4_feasibility_contact_omission_mismatch")
        start = starts[0]
        output = output[: start + 1] + output[start + len(expected) - 1 :]

    aliases = [item for item in policy["swap_footnote_aliases"] if item["role"] == role]
    for alias in aliases:
        position = alias["one_based_position"] - 1
        if output[position] != alias["metadata_name"]:
            raise ValueError("form4_feasibility_swap_footnote_alias_mismatch")
        output[position] = alias["physical_name"]
    return output


def test_v1_1_receipt_is_append_only_and_binds_parent_commit_and_bytes() -> None:
    receipt = _receipt()
    assert receipt["status"] == (
        "v1_1_schema_amendment_frozen_after_complete_eight_table_diff_before_"
        "root_real_fetch_selection_or_performance"
    )
    for key in ("amendment", "parent_v1_0_protocol", "parent_v1_0_receipt"):
        binding = receipt[key]
        assert _sha256(ROOT / binding["path"]) == binding["sha256"]
    assert _sha256(V1_PROTOCOL) == (
        "ddce1e7152a3d23f39dae4f8d7bb812166941952d7611523ca5796f11b4b1186"
    )
    assert _sha256(V1_RECEIPT) == (
        "75f81c0149abc003fa0438e9498f0884a0e7020b31c07bbeaef122cc15f912db"
    )

    git_binding = receipt["parent_freeze_git"]
    commit = subprocess.run(
        ["git", "rev-parse", git_binding["short_commit"]],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    assert commit == git_binding["commit"]
    subject = subprocess.run(
        ["git", "show", "-s", "--format=%s", commit],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    assert subject == git_binding["subject"]
    remote_contains_parent = subprocess.run(
        [
            "git",
            "merge-base",
            "--is-ancestor",
            commit,
            git_binding["remote_ref"],
        ],
        cwd=ROOT,
        check=False,
    )
    assert remote_contains_parent.returncode == 0
    assert git_binding["remote_tip_verified_before_freeze"] is True
    assert _utc(git_binding["committed_at"]) < _utc(receipt["frozen_at"])


def test_v1_1_allows_only_frozen_contact_omission_and_swap_aliases() -> None:
    policy = _receipt()["metadata_to_physical_policy"]
    assert policy["policy_kind"] == (
        "closed_exact_transform_not_subset_alias_or_fuzzy_matching"
    )
    assert policy["any_other_difference_allowed"] is False
    submission_metadata = [
        "ACCESSION_NUMBER",
        "ISSUERCIK",
        "ISSUERNAME",
        "ISSUERTRADINGSYMBOL",
        "CONTACT_NAME",
        "CONTACT_PHONE_NUMBER",
        "CONTACT_EMAIL_ADDRESS",
        "NOTIFICATION_EMAIL_ADDRESS",
        "REMARKS",
        "AFF10B5ONE",
    ]
    assert _expected_physical("SUBMISSION.tsv", submission_metadata, policy) == [
        "ACCESSION_NUMBER",
        "ISSUERCIK",
        "ISSUERNAME",
        "ISSUERTRADINGSYMBOL",
        "REMARKS",
        "AFF10B5ONE",
    ]

    nonderiv = [f"FIELD_{index}" for index in range(1, 29)]
    nonderiv[11] = "EQUITY_SWAP_INVOLVED_FN"
    transformed = _expected_physical("NONDERIV_TRANS.tsv", nonderiv, policy)
    assert transformed[11] == "EQUITY_SWAP_TRANS_CD_FN"
    assert transformed[:11] == nonderiv[:11]
    assert transformed[12:] == nonderiv[12:]

    deriv = [f"FIELD_{index}" for index in range(1, 43)]
    deriv[13] = "EQUITY_SWAP_INVOLVED_FN"
    transformed = _expected_physical("DERIV_TRANS.tsv", deriv, policy)
    assert transformed[13] == "EQUITY_SWAP_TRANS_CD_FN"
    assert transformed[:13] == deriv[:13]
    assert transformed[14:] == deriv[14:]

    exact = ["ACCESSION_NUMBER", "RPTOWNERCIK", "RPTOWNERNAME"]
    assert _expected_physical("REPORTINGOWNER.tsv", exact, policy) == exact


@pytest.mark.parametrize(
    "metadata_columns",
    [
        ["ISSUERTRADINGSYMBOL", "CONTACT_NAME", "REMARKS"],
        [
            "ISSUERTRADINGSYMBOL",
            "CONTACT_PHONE_NUMBER",
            "CONTACT_NAME",
            "CONTACT_EMAIL_ADDRESS",
            "NOTIFICATION_EMAIL_ADDRESS",
            "REMARKS",
        ],
        [
            "ISSUERTRADINGSYMBOL",
            "CONTACT_NAME",
            "CONTACT_PHONE_NUMBER",
            "CONTACT_EMAIL_ADDRESS",
            "NOTIFICATION_EMAIL_ADDRESS",
            "EXTRA_METADATA_ONLY",
            "REMARKS",
        ],
    ],
)
def test_v1_1_rejects_contact_subset_reorder_or_extra(
    metadata_columns: list[str],
) -> None:
    with pytest.raises(ValueError, match="form4_feasibility_contact_omission_mismatch"):
        _expected_physical(
            "SUBMISSION.tsv", metadata_columns, _receipt()["metadata_to_physical_policy"]
        )


def test_v1_1_profiles_attacks_and_zero_result_boundary_are_frozen() -> None:
    receipt = _receipt()
    profiles = receipt["physical_header_profiles"]
    assert profiles.pop("hash_basis") == (
        "physical_header_utf8_no_bom_no_line_terminator_sha256"
    )
    assert len(profiles) == 10
    for profile in profiles.values():
        assert profile["columns"] > 0
        assert len(profile["sha256"]) == 64
        int(profile["sha256"], 16)

    assert receipt["new_stable_error_codes"] == [
        "form4_feasibility_contact_omission_mismatch",
        "form4_feasibility_swap_footnote_alias_mismatch",
        "form4_feasibility_physical_header_profile_mismatch",
        "form4_feasibility_unexpected_metadata_physical_drift",
    ]
    assert receipt["global_trial_state"] == {
        "lower_bound_before": 6_287,
        "round42_schema_amendment_increment": 0,
        "lower_bound_after": 6_287,
        "ledger_append_authorized": False,
    }
    assert receipt["state_at_freeze"] == {
        "form4_specific_admission_passed": 0,
        "form4_specific_admission_total": 16,
        "root_sec_real_fetch_count": 0,
        "authorized_real_form4_rows": 0,
        "root_real_sample_selection_count": 0,
        "candidate_selection_count": 0,
        "strategy_run_count": 0,
        "performance_result_present": False,
        "paper_authorized": False,
        "real_money_authorized": False,
        "real_money_action_usd": 0,
    }
    assert receipt["permission"]["root_sec_real_fetch"] is False
    assert receipt["permission"]["real_sample_selection"] is False
    assert receipt["permission"]["candidate_selection"] is False
    assert receipt["permission"]["backtest"] is False
    assert receipt["permission"]["paper"] is False
    assert receipt["permission"]["real_money"] is False
    assert receipt["paper"] == {
        "authorized": False,
        "state": "all_cash",
        "backfilled_trades": 0,
        "positions": [],
    }
    assert receipt["today_action"] == "今天不下單"
