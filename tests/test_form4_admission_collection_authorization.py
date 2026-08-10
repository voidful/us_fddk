from __future__ import annotations

import copy
import hashlib
import json
import re
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from usfddk.form4_admission_collection import (
    AUTHORIZATION_KEYS,
    COLLECTION_BINDING_KEYS,
    Form4CollectionError,
    _canonical_hash,
    validate_collection_authorization,
)

ROOT = Path(__file__).resolve().parents[1]
DOCUMENT = ROOT / "docs/SHORT_TERM_FORM4_ADMISSION_COLLECTION_AUTHORIZATION.md"
RECEIPT = (
    ROOT / "artifacts/short_term_form4_admission_collection_authorization_receipt.json"
)
PARENT_COMMIT = "0145969e19f2524d3eddc77702865425767aefac"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    assert parsed.tzinfo is not None
    return parsed.astimezone(UTC)


def _receipt() -> dict[str, Any]:
    return json.loads(RECEIPT.read_text(encoding="utf-8"))


def _error_code(action: object) -> str:
    with pytest.raises(Form4CollectionError) as caught:
        action()  # type: ignore[operator]
    return caught.value.code


def test_authorization_receipt_exactly_matches_runtime_schema_and_canonical_hash() -> None:
    receipt = _receipt()
    assert set(receipt) == AUTHORIZATION_KEYS
    assert set(receipt["bindings"]) == COLLECTION_BINDING_KEYS
    assert receipt["schema_version"] == (
        "us_fddk.short_term_form4_collection_authorization.v1"
    )
    assert receipt["status"] == "authorized_once_before_sec_fetch"
    assert receipt["authorization_id"] == "round42-form4-admission-one-shot-v1"
    assert receipt["receipt_sha256"] == _canonical_hash(receipt, omit="receipt_sha256")
    assert validate_collection_authorization(RECEIPT, repository_root=ROOT) == receipt


def test_authorization_binds_remote_parent_and_all_execution_bytes() -> None:
    receipt = _receipt()
    assert receipt["parent_code_commit"] == PARENT_COMMIT
    assert receipt["remote_ref"] == "origin/codex/round42-form4-admission"
    for binding in receipt["bindings"].values():
        assert set(binding) == {"path", "sha256"}
        assert _sha256(ROOT / binding["path"]) == binding["sha256"]

    parent_timestamp = subprocess.run(
        ["git", "show", "-s", "--format=%cI", PARENT_COMMIT],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    assert _utc(parent_timestamp) < _utc(receipt["frozen_at"])
    remote_contains_parent = subprocess.run(
        [
            "git",
            "merge-base",
            "--is-ancestor",
            PARENT_COMMIT,
            receipt["remote_ref"],
        ],
        cwd=ROOT,
        check=False,
    )
    assert remote_contains_parent.returncode == 0

    text = DOCUMENT.read_text(encoding="utf-8")
    frozen = re.search(r"^FrozenAt：`([^`]+)`$", text, flags=re.MULTILINE)
    assert frozen is not None
    assert frozen.group(1) == receipt["frozen_at"]
    assert PARENT_COMMIT in text


def test_authorization_is_one_shot_fixed_bounded_private_and_result_blind() -> None:
    receipt = _receipt()
    assert receipt["fixed_collection"] == {
        "fixed_quarters": ["2006Q1", "2016Q3", "2026Q2"],
        "catalog_requests": 1,
        "quarter_zip_requests": 3,
        "daily_index_requests_max": 12,
        "complete_submission_requests_max": 12,
        "total_requests_max": 28,
        "automatic_retries": 0,
        "resampling_allowed": False,
        "next_day_index_fallback_allowed": False,
    }
    assert receipt["privacy"] == {
        "quarantine_repository_external": True,
        "filevault_required": True,
        "directory_mode": "0700",
        "file_mode": "0600",
        "public_identifiers_allowed": False,
    }
    assert receipt["state_boundary"] == {
        "candidate_selection_count": 0,
        "strategy_run_count": 0,
        "performance_result_present": False,
        "paper_authorized": False,
        "real_money_action_usd": 0,
    }

    text = DOCUMENT.read_text(encoding="utf-8")
    for frozen_term in (
        "first／lower-median／last",
        "9–12",
        "同日 index",
        "automatic retry 精確為 0",
        "selection_plan.json",
        "private_manifest.json",
        "private_collection_complete_cold_replay_required",
        "網路 opener 強制失敗",
        "今天不下單",
    ):
        assert frozen_term in text


def test_authorization_freezes_below_16_stop_and_collector_failures() -> None:
    document = DOCUMENT.read_text(encoding="utf-8")
    verifier_source = (
        ROOT / "usfddk/form4_admission_feasibility.py"
    ).read_text(encoding="utf-8")
    collector_source = (
        ROOT / "usfddk/form4_admission_collection.py"
    ).read_text(encoding="utf-8")
    assert "form4_admission_below_16_of_16" in document
    assert '"form4_admission_below_16_of_16"' in verifier_source

    collector_failures = {
        "form4_collection_authorization_invalid",
        "form4_collection_private_boundary_invalid",
        "form4_collection_filevault_not_verified",
        "form4_collection_already_started",
        "form4_collection_append_only_collision",
        "form4_collection_attempt_ledger_invalid",
        "form4_collection_request_plan_drifted",
        "form4_collection_selection_plan_invalid",
        "form4_collection_request_limit_exceeded",
        "form4_collection_private_manifest_invalid",
        "form4_collection_replay_network_forbidden",
        "form4_collection_public_boundary_breached",
    }
    for code in collector_failures:
        assert f"`{code}`" in document
        assert f'"{code}"' in collector_source


def test_authorization_drift_fails_even_with_recomputed_receipt_hash(tmp_path: Path) -> None:
    drifted = copy.deepcopy(_receipt())
    drifted["fixed_collection"]["total_requests_max"] = 29
    drifted["receipt_sha256"] = _canonical_hash(drifted, omit="receipt_sha256")
    path = ROOT / "artifacts" / f".authorization-drift-{tmp_path.name}.json"
    path.write_text(json.dumps(drifted), encoding="utf-8")
    try:
        assert _error_code(
            lambda: validate_collection_authorization(path, repository_root=ROOT)
        ) == "form4_collection_authorization_invalid"
    finally:
        path.unlink()
