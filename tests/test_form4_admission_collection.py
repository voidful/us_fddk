from __future__ import annotations

import copy
import hashlib
import json
import stat
import subprocess
from pathlib import Path

import pytest

from usfddk.form4_admission_collection import (
    AUTHORIZATION_SCHEMA,
    COLLECTION_BINDING_KEYS,
    Form4CollectionError,
    _canonical_hash,
    _sanitize_public_receipt,
    _write_private_json_create,
    validate_collection_authorization,
)
from usfddk.form4_admission_feasibility import (
    Form4AdmissionFeasibilityError,
    build_form4_feasibility_failure_receipt,
)


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _authorization_repo(tmp_path: Path) -> tuple[Path, Path, dict[str, object]]:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "config", "user.name", "Form4 Test")
    _git(repo, "config", "user.email", "form4-test@example.com")
    bound = repo / "bound.txt"
    bound.write_text("frozen\n", encoding="utf-8")
    _git(repo, "add", "bound.txt")
    _git(repo, "commit", "-m", "freeze code")
    parent = _git(repo, "rev-parse", "HEAD")
    digest = hashlib.sha256(bound.read_bytes()).hexdigest()
    authorization: dict[str, object] = {
        "schema_version": AUTHORIZATION_SCHEMA,
        "research_round": 42,
        "status": "authorized_once_before_sec_fetch",
        "frozen_at": "2026-08-10T00:00:00Z",
        "authorization_id": "round42-form4-admission-test-seal",
        "user_scope": "fixed official SEC admission-feasibility sample only",
        "parent_code_commit": parent,
        "remote_ref": "origin/codex/round42-form4-admission",
        "bindings": {
            key: {"path": "bound.txt", "sha256": digest}
            for key in COLLECTION_BINDING_KEYS
        },
        "fixed_collection": {
            "fixed_quarters": ["2006Q1", "2016Q3", "2026Q2"],
            "catalog_requests": 1,
            "quarter_zip_requests": 3,
            "daily_index_requests_max": 12,
            "complete_submission_requests_max": 12,
            "total_requests_max": 28,
            "automatic_retries": 0,
            "resampling_allowed": False,
            "next_day_index_fallback_allowed": False,
        },
        "privacy": {
            "quarantine_repository_external": True,
            "filevault_required": True,
            "directory_mode": "0700",
            "file_mode": "0600",
            "public_identifiers_allowed": False,
        },
        "state_boundary": {
            "candidate_selection_count": 0,
            "strategy_run_count": 0,
            "performance_result_present": False,
            "paper_authorized": False,
            "real_money_action_usd": 0,
        },
        "receipt_sha256": "",
    }
    authorization["receipt_sha256"] = _canonical_hash(
        authorization,
        omit="receipt_sha256",
    )
    path = repo / "authorization.json"
    path.write_text(json.dumps(authorization), encoding="utf-8")
    return repo, path, authorization


def _error_code(callable_: object) -> str:
    with pytest.raises(Form4CollectionError) as error:
        callable_()  # type: ignore[operator]
    return error.value.code


def test_collection_authorization_is_exact_hash_bound_and_ancestral(tmp_path: Path) -> None:
    repo, path, authorization = _authorization_repo(tmp_path)
    assert validate_collection_authorization(path, repository_root=repo) == authorization

    drifted = copy.deepcopy(authorization)
    drifted["fixed_collection"]["total_requests_max"] = 29  # type: ignore[index]
    drifted["receipt_sha256"] = _canonical_hash(drifted, omit="receipt_sha256")
    path.write_text(json.dumps(drifted), encoding="utf-8")
    assert _error_code(
        lambda: validate_collection_authorization(path, repository_root=repo)
    ) == "form4_collection_authorization_invalid"


def test_private_writer_is_owner_only_create_once_and_hashes_exact_bytes(
    tmp_path: Path,
) -> None:
    private = tmp_path / "private"
    private.mkdir(mode=0o700)
    private.chmod(0o700)
    path = private / "manifest.json"
    digest = _write_private_json_create(path, {"status": "sealed", "rows": 0})
    assert len(digest) == 64
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert hashlib.sha256(path.read_bytes()).hexdigest() == digest
    assert _error_code(
        lambda: _write_private_json_create(path, {"status": "replacement"})
    ) == "form4_collection_append_only_collision"


def test_public_sanitizer_accepts_redacted_gate_receipt_and_rejects_identifiers() -> None:
    receipt = build_form4_feasibility_failure_receipt(
        Form4AdmissionFeasibilityError(
            "form4_feasibility_amendment_target_unresolved",
            "private detail must never survive",
        ),
        sample_count=11,
        evidence_mode="authorized_real_sample",
        private_manifest_sha256="a" * 64,
    )
    _sanitize_public_receipt(receipt)

    leaked_key = copy.deepcopy(receipt)
    leaked_key["issuer_cik"] = "123456"
    assert _error_code(lambda: _sanitize_public_receipt(leaked_key)) == (
        "form4_collection_public_boundary_breached"
    )
    leaked_value = copy.deepcopy(receipt)
    leaked_value["stop_reasons"] = ["0000123456-26-000001"]
    assert _error_code(lambda: _sanitize_public_receipt(leaked_value)) == (
        "form4_collection_public_boundary_breached"
    )
