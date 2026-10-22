from __future__ import annotations

import base64
import copy
import hashlib
import json
import os
import plistlib
import socket
import stat
import subprocess
import threading
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

import pytest

import usfddk.form4_monitor_start as monitor

ROOT = Path(__file__).resolve().parents[1]
AUTHORIZATION_RECEIPT = ROOT / monitor.START_AUTHORIZATION_PATH
WORKFLOW = ROOT / monitor.ROUND45_WORKFLOW_PATH


def _error_code(action: Callable[[], object]) -> str:
    with pytest.raises(monitor.Form4MonitorStartError) as caught:
        action()
    return caught.value.code


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _authorization_receipt(bindings: dict[str, dict[str, str]]) -> dict[str, object]:
    receipt: dict[str, object] = {
        "schema_version": monitor.AUTHORIZATION_SCHEMA,
        "research_round": 45,
        "authorization_id": monitor.AUTHORIZATION_ID,
        "phase": "monitor_start_authorization",
        "status": "frozen_remote_exact_head_required",
        "frozen_at": monitor.AUTHORIZATION_FROZEN_AT,
        "parent_commit": monitor.ROUND44_COMMIT,
        "bindings": bindings,
        "tool_contract": copy.deepcopy(monitor.TOOL_CONTRACT),
        "remote_contract": copy.deepcopy(monitor.REMOTE_CONTRACT),
        "tsa_contract": copy.deepcopy(monitor.TSA_CONTRACT),
        "private_contract": copy.deepcopy(monitor.PRIVATE_CONTRACT),
        "state_boundary": copy.deepcopy(monitor.STATE_BOUNDARY),
        "permission": copy.deepcopy(monitor.PERMISSION),
        "today_action": "今天不下單",
        "receipt_sha256": "",
    }
    receipt["receipt_sha256"] = monitor.canonical_sha256(
        receipt,
        omit="receipt_sha256",
    )
    return receipt


def _authorization_fixture(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[Path, Path, dict[str, object], dict[str, Path]]:
    repository = tmp_path / "repository"
    repository.mkdir()
    bound_paths = {
        "implementation": repository / "implementation.py",
        "protocol": repository / "protocol.md",
    }
    bound_paths["implementation"].write_bytes(b"frozen implementation\n")
    bound_paths["protocol"].write_bytes(b"frozen protocol\n")
    binding_paths = {
        name: path.relative_to(repository).as_posix()
        for name, path in bound_paths.items()
    }
    monkeypatch.setattr(monitor, "BINDING_PATHS", binding_paths)
    monkeypatch.setattr(monitor, "BINDING_KEYS", frozenset(binding_paths))
    monkeypatch.setattr(monitor, "START_AUTHORIZATION_PATH", "authorization.json")
    monkeypatch.setattr(
        monitor,
        "_head_blob_bytes",
        lambda root, relative, **_kwargs: (root / relative).read_bytes(),
    )
    monkeypatch.setattr(monitor, "_validate_repository_identity", lambda _root: None)
    monkeypatch.setattr(
        monitor,
        "validate_predata_authorization",
        lambda *_args, **_kwargs: {"status": "validated"},
    )
    monkeypatch.setattr(
        monitor,
        "_run_process",
        lambda args, **_kwargs: subprocess.CompletedProcess(args, 0, b"", b""),
    )
    bindings = {
        name: {
            "path": relative,
            "sha256": _sha256_bytes(bound_paths[name].read_bytes()),
        }
        for name, relative in binding_paths.items()
    }
    receipt = _authorization_receipt(bindings)
    authorization_path = repository / "authorization.json"
    authorization_path.write_text(json.dumps(receipt), encoding="utf-8")
    return repository, authorization_path, receipt, bound_paths


def _volume_fixture(private_root: Path) -> dict[str, object]:
    metadata = private_root.stat()
    volume_uuid = "00000000-0000-0000-0000-000000000045"
    return {
        "schema_version": "us_fddk.short_term_form4_volume_attestation.v1",
        "canonical_private_root": str(private_root),
        "private_root_path_sha256": _sha256_bytes(str(private_root).encode()),
        "device": "/dev/test-round45",
        "device_identifier": "test-round45",
        "mount_point": str(private_root.parent),
        "volume_uuid": volume_uuid,
        "volume_uuid_sha256": _sha256_bytes(volume_uuid.encode()),
        "st_dev": metadata.st_dev,
        "st_ino": metadata.st_ino,
        "owner_uid": metadata.st_uid,
        "mode": "0700",
        "filevault": True,
        "encryption": True,
        "encryption_this_volume_proper": True,
        "locked": False,
        "writable": True,
        "diskutil_plist_sha256": "1" * 64,
        "fdesetup_status_sha256": "2" * 64,
        "attestation_sha256": "",
    }


def _remote_proof_fixture() -> dict[str, object]:
    head = "b" * 40

    def side(
        *,
        side_head: str,
        branch: str,
        workflow_name: str,
        workflow_path: str,
        job_name: str,
        pull_number: int,
        pull_id: int,
        run_id: int,
        job_id: int,
    ) -> dict[str, object]:
        job_url = f"https://github.com/{monitor.REPOSITORY}/actions/runs/{run_id}/job/{job_id}"
        check_url = f"https://api.github.com/repos/{monitor.REPOSITORY}/check-runs/{job_id}"
        return {
            "run": {
                "run_id": run_id,
                "run_attempt": 1,
                "workflow_name": workflow_name,
                "workflow_path": workflow_path,
                "event": "pull_request",
                "head_sha": side_head,
                "head_branch": branch,
                "status": "completed",
                "conclusion": "success",
                "created_at": "2026-08-10T05:00:00Z",
                "completed_at": "2026-08-10T05:01:00Z",
                "pull_request_number": pull_number,
                "pull_request_id": pull_id,
            },
            "job": {
                "job_id": job_id,
                "run_id": run_id,
                "run_attempt": 1,
                "workflow_name": workflow_name,
                "job_name": job_name,
                "head_sha": side_head,
                "status": "completed",
                "conclusion": "success",
                "started_at": "2026-08-10T05:00:10Z",
                "completed_at": "2026-08-10T05:01:00Z",
                "html_url": job_url,
                "check_run_url": check_url,
            },
            "check": {
                "check_id": job_id,
                "check_name": job_name,
                "head_sha": side_head,
                "check_app_id": monitor.GITHUB_ACTIONS_APP_ID,
                "check_app_slug": monitor.GITHUB_ACTIONS_APP_SLUG,
                "check_app_owner": monitor.GITHUB_ACTIONS_APP_OWNER,
                "status": "completed",
                "conclusion": "success",
                "started_at": "2026-08-10T05:00:10Z",
                "completed_at": "2026-08-10T05:01:00Z",
                "details_url": job_url,
            },
        }

    proof: dict[str, object] = {
        "schema_version": "us_fddk.short_term_form4_remote_gate_proof.v1",
        "repository": monitor.REPOSITORY,
        "repository_id": monitor.REPOSITORY_ID,
        "branch": monitor.BRANCH,
        "authorization_commit": head,
        "pull_request_number": 45,
        "pull_request_id": 4500,
        "pull_request_draft": True,
        "refs": {
            "current": {
                "ref": f"refs/heads/{monitor.BRANCH}",
                "object_type": "commit",
                "sha": head,
            },
            "parent": {
                "ref": f"refs/heads/{monitor.PARENT_BRANCH}",
                "object_type": "commit",
                "sha": monitor.ROUND44_COMMIT,
            },
        },
        "parent": side(
            side_head=monitor.ROUND44_COMMIT,
            branch=monitor.PARENT_BRANCH,
            workflow_name=monitor.ROUND44_WORKFLOW_NAME,
            workflow_path=monitor.ROUND44_WORKFLOW_PATH,
            job_name=monitor.ROUND44_JOB_NAME,
            pull_number=monitor.ROUND44_PR_NUMBER,
            pull_id=monitor.ROUND44_PR_ID,
            run_id=monitor.ROUND44_RUN_ID,
            job_id=monitor.ROUND44_JOB_ID,
        ),
        "current": side(
            side_head=head,
            branch=monitor.BRANCH,
            workflow_name=monitor.ROUND45_WORKFLOW_NAME,
            workflow_path=monitor.ROUND45_WORKFLOW_PATH,
            job_name=monitor.ROUND45_JOB_NAME,
            pull_number=45,
            pull_id=4500,
            run_id=450,
            job_id=451,
        ),
        "raw_response_sha256": {
            "current_ref_first": "1" * 64,
            "parent_ref": "2" * 64,
            "current_prs": "3" * 64,
            "current_run_pages": ["4" * 64],
            "current_run": "a" * 64,
            "current_jobs": "5" * 64,
            "current_checks": "6" * 64,
            "parent_run": "7" * 64,
            "parent_jobs": "8" * 64,
            "parent_checks": "9" * 64,
            "current_ref_last": "1" * 64,
        },
        "proof_sha256": "",
    }
    proof["proof_sha256"] = monitor.canonical_sha256(proof, omit="proof_sha256")
    return proof


def _install_start_fixtures(
    monkeypatch: pytest.MonkeyPatch,
    private_root: Path,
) -> tuple[dict[str, str], dict[str, object]]:
    authorization = {"receipt_sha256": "3" * 64}
    remote_proof: dict[str, object] = {
        "schema_version": "us_fddk.short_term_form4_remote_gate_proof.v1",
        "authorization_commit": "a" * 40,
        "current": {"check": {"completed_at": "2026-08-10T06:00:00Z"}},
        "proof_sha256": "4" * 64,
    }
    monkeypatch.setattr(monitor, "START_AUTHORIZATION_PATH", "authorization.json")
    monkeypatch.setattr(
        monitor,
        "PRIVATE_PARENT_PATH_SHA256",
        _sha256_bytes(str(private_root.parent).encode()),
    )
    monkeypatch.setattr(
        monitor,
        "PRIVATE_ROOT_PATH_SHA256",
        _sha256_bytes(str(private_root).encode()),
    )
    monkeypatch.setattr(
        monitor,
        "validate_monitor_start_authorization",
        lambda *_args, **_kwargs: authorization,
    )
    monkeypatch.setattr(
        monitor,
        "collect_remote_gate_proof",
        lambda *_args, **_kwargs: copy.deepcopy(remote_proof),
    )
    monkeypatch.setattr(monitor, "_validate_stored_remote_proof", lambda *_args: None)
    monkeypatch.setattr(monitor, "_validate_tool_contract", lambda: None)
    monkeypatch.setattr(monitor, "_validate_private_location", lambda *_args: None)
    monkeypatch.setattr(monitor, "_validate_tsa_assets", lambda *_args: None)
    monkeypatch.setattr(monitor, "_assert_no_acl_or_xattr", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(monitor, "_volume_attestation", _volume_fixture)
    monkeypatch.setattr(
        monitor,
        "_generate_anchor_query",
        lambda *_args: b"round45-fixed-query",
    )
    return authorization, remote_proof


def _start_paths(tmp_path: Path) -> tuple[Path, Path, Path]:
    repository = tmp_path / "repository"
    repository.mkdir()
    authorization_path = repository / "authorization.json"
    authorization_path.write_bytes(b"synthetic round45 authorization\n")
    private_parent = tmp_path / "private-parent"
    private_parent.mkdir(mode=0o700)
    private_parent.chmod(0o700)
    return repository, authorization_path, private_parent / "runtime"


def test_authorization_is_exact_typed_hash_bound_and_ancestral(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository, path, receipt, bound_paths = _authorization_fixture(
        tmp_path,
        monkeypatch,
    )
    assert monitor.validate_monitor_start_authorization(
        path,
        repository_root=repository,
    ) == receipt

    bool_as_int = copy.deepcopy(receipt)
    bool_as_int["research_round"] = True
    bool_as_int["receipt_sha256"] = monitor.canonical_sha256(
        bool_as_int,
        omit="receipt_sha256",
    )
    path.write_text(json.dumps(bool_as_int), encoding="utf-8")
    assert _error_code(
        lambda: monitor.validate_monitor_start_authorization(
            path,
            repository_root=repository,
        )
    ) == monitor.STABLE_CODES["authorization"]

    not_finite = copy.deepcopy(receipt)
    not_finite["research_round"] = float("nan")
    path.write_text(json.dumps(not_finite, allow_nan=True), encoding="utf-8")
    assert _error_code(
        lambda: monitor.validate_monitor_start_authorization(
            path,
            repository_root=repository,
        )
    ) == monitor.STABLE_CODES["authorization"]

    extra = copy.deepcopy(receipt)
    extra["unexpected"] = None
    extra["receipt_sha256"] = monitor.canonical_sha256(extra, omit="receipt_sha256")
    path.write_text(json.dumps(extra), encoding="utf-8")
    assert _error_code(
        lambda: monitor.validate_monitor_start_authorization(
            path,
            repository_root=repository,
        )
    ) == monitor.STABLE_CODES["authorization"]

    swapped = copy.deepcopy(receipt)
    bindings = swapped["bindings"]
    assert isinstance(bindings, dict)
    left = bindings["implementation"]
    right = bindings["protocol"]
    assert isinstance(left, dict) and isinstance(right, dict)
    left["path"], right["path"] = right["path"], left["path"]
    left["sha256"], right["sha256"] = right["sha256"], left["sha256"]
    swapped["receipt_sha256"] = monitor.canonical_sha256(
        swapped,
        omit="receipt_sha256",
    )
    path.write_text(json.dumps(swapped), encoding="utf-8")
    assert _error_code(
        lambda: monitor.validate_monitor_start_authorization(
            path,
            repository_root=repository,
        )
    ) == monitor.STABLE_CODES["authorization"]

    outside = tmp_path / "outside-authorization.json"
    outside.write_text(json.dumps(receipt), encoding="utf-8")
    assert _error_code(
        lambda: monitor.validate_monitor_start_authorization(
            outside,
            repository_root=repository,
        )
    ) == monitor.STABLE_CODES["authorization"]

    bound_paths["implementation"].write_bytes(b"drifted after authorization\n")
    path.write_text(json.dumps(receipt), encoding="utf-8")
    assert _error_code(
        lambda: monitor.validate_monitor_start_authorization(
            path,
            repository_root=repository,
        )
    ) == monitor.STABLE_CODES["authorization"]


def test_authorization_rejects_duplicate_nan_extra_and_binding_identity_drift(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository, path, receipt, _ = _authorization_fixture(tmp_path, monkeypatch)

    path.write_text('{"schema_version": 1, "schema_version": 2}', encoding="utf-8")
    assert _error_code(
        lambda: monitor.validate_monitor_start_authorization(
            path,
            repository_root=repository,
        )
    ) == monitor.STABLE_CODES["authorization"]

    mutations: list[dict[str, object]] = []

    missing_key = copy.deepcopy(receipt)
    del missing_key["today_action"]
    mutations.append(missing_key)

    missing_binding = copy.deepcopy(receipt)
    missing_bindings = missing_binding["bindings"]
    assert isinstance(missing_bindings, dict)
    del missing_bindings["protocol"]
    mutations.append(missing_binding)

    absolute_binding = copy.deepcopy(receipt)
    absolute_bindings = absolute_binding["bindings"]
    assert isinstance(absolute_bindings, dict)
    absolute_implementation = absolute_bindings["implementation"]
    assert isinstance(absolute_implementation, dict)
    absolute_implementation["path"] = "/tmp/implementation.py"
    mutations.append(absolute_binding)

    traversal_binding = copy.deepcopy(receipt)
    traversal_bindings = traversal_binding["bindings"]
    assert isinstance(traversal_bindings, dict)
    traversal_protocol = traversal_bindings["protocol"]
    assert isinstance(traversal_protocol, dict)
    traversal_protocol["path"] = "../protocol.md"
    mutations.append(traversal_binding)

    for mutated in mutations:
        mutated["receipt_sha256"] = monitor.canonical_sha256(
            mutated,
            omit="receipt_sha256",
        )
        path.write_text(json.dumps(mutated), encoding="utf-8")
        assert _error_code(
            lambda: monitor.validate_monitor_start_authorization(
                path,
                repository_root=repository,
            )
        ) == monitor.STABLE_CODES["authorization"]


def test_committed_authorization_is_current_head_bound_and_locally_replayable() -> None:
    receipt = json.loads(AUTHORIZATION_RECEIPT.read_text(encoding="utf-8"))
    assert monitor.validate_monitor_start_authorization(
        AUTHORIZATION_RECEIPT,
        repository_root=ROOT,
    ) == receipt
    assert receipt["receipt_sha256"] == monitor.canonical_sha256(
        receipt,
        omit="receipt_sha256",
    )
    assert set(receipt["bindings"]) == monitor.BINDING_KEYS


def test_workflow_is_exact_head_read_only_and_cannot_collect_or_deploy() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")
    exact_head = "${{ github.event.pull_request.head.sha }}"
    assert f"ref: {exact_head}" in workflow
    assert f"EXPECTED_HEAD_SHA: {exact_head}" in workflow
    assert "if: github.event.pull_request.head.repo.full_name == github.repository" in workflow
    assert "permissions:\n  contents: read\n" in workflow
    assert "persist-credentials: false" in workflow
    assert "workflow_dispatch:" not in workflow
    assert "schedule:" not in workflow
    assert "sec.gov" not in workflow
    for forbidden in (
        "deploy-pages",
        "pages: write",
        "id-token: write",
        "secrets.",
        "curl ",
        "wget ",
    ):
        assert forbidden not in workflow


def test_stored_remote_proof_rejects_head_app_time_id_and_ref_mutations() -> None:
    valid = _remote_proof_fixture()
    monitor._validate_stored_remote_proof(valid)

    mutations: list[tuple[tuple[str, ...], object]] = [
        (("repository_id",), True),
        (("pull_request_number",), 46),
        (("pull_request_draft",), False),
        (("current", "run", "head_sha"), "c" * 40),
        (("current", "run", "workflow_name"), "Pages build and deployment"),
        (("current", "run", "workflow_path"), ".github/workflows/pages.yml"),
        (("current", "run", "event"), "schedule"),
        (("current", "run", "status"), "in_progress"),
        (("current", "run", "conclusion"), "failure"),
        (("current", "job", "job_name"), "Daily refresh"),
        (("current", "check", "check_name"), "Pages build and deployment"),
        (("current", "check", "check_app_id"), 1),
        (("current", "check", "completed_at"), "2026-08-10T05:02:00Z"),
        (("current", "job", "run_attempt"), 2),
        (("refs", "current", "sha"), "c" * 40),
        (("raw_response_sha256", "current_ref_last"), "f" * 64),
        (("raw_response_sha256", "current_run_pages"), []),
        (("raw_response_sha256", "current_run_pages"), ["not-a-hash"]),
    ]
    for path, replacement in mutations:
        mutated = copy.deepcopy(valid)
        target: dict[str, object] = mutated
        for key in path[:-1]:
            child = target[key]
            assert isinstance(child, dict)
            target = child
        target[path[-1]] = replacement
        mutated["proof_sha256"] = monitor.canonical_sha256(
            mutated,
            omit="proof_sha256",
        )
        assert _error_code(lambda value=mutated: monitor._validate_stored_remote_proof(value)) == (
            monitor.STABLE_CODES["remote_gate"]
        )


def test_live_check_details_url_must_be_exact_job_url() -> None:
    proof = _remote_proof_fixture()
    current = proof["current"]
    assert isinstance(current, dict)
    normalized_job = current["job"]
    normalized_check = current["check"]
    assert isinstance(normalized_job, dict) and isinstance(normalized_check, dict)
    job = {
        "id": normalized_job["job_id"],
        "run_id": normalized_job["run_id"],
        "run_attempt": normalized_job["run_attempt"],
        "workflow_name": normalized_job["workflow_name"],
        "name": normalized_job["job_name"],
        "head_sha": normalized_job["head_sha"],
        "status": normalized_job["status"],
        "conclusion": normalized_job["conclusion"],
        "started_at": normalized_job["started_at"],
        "completed_at": normalized_job["completed_at"],
        "html_url": normalized_job["html_url"],
        "check_run_url": normalized_job["check_run_url"],
    }
    check = {
        "id": normalized_check["check_id"],
        "name": normalized_check["check_name"],
        "head_sha": normalized_check["head_sha"],
        "status": normalized_check["status"],
        "conclusion": normalized_check["conclusion"],
        "started_at": normalized_check["started_at"],
        "completed_at": normalized_check["completed_at"],
        "details_url": normalized_check["details_url"],
        "app": {
            "id": normalized_check["check_app_id"],
            "slug": normalized_check["check_app_slug"],
            "owner": {"login": normalized_check["check_app_owner"]},
        },
    }
    result = monitor._validate_job_and_check(
        jobs_payload={"jobs": [job]},
        checks_payload={"check_runs": [check]},
        run_id=job["run_id"],  # type: ignore[arg-type]
        run_attempt=job["run_attempt"],  # type: ignore[arg-type]
        head=str(job["head_sha"]),
        workflow_name=str(job["workflow_name"]),
        job_name=str(job["name"]),
        expected_job_id=None,
    )
    assert result["check"]["details_url"] == job["html_url"]

    check["details_url"] = f"https://evil.invalid/prefix{job['html_url']}"
    assert _error_code(
        lambda: monitor._validate_job_and_check(
            jobs_payload={"jobs": [job]},
            checks_payload={"check_runs": [check]},
            run_id=job["run_id"],  # type: ignore[arg-type]
            run_attempt=job["run_attempt"],  # type: ignore[arg-type]
            head=str(job["head_sha"]),
            workflow_name=str(job["workflow_name"]),
            job_name=str(job["name"]),
            expected_job_id=None,
        )
    ) == monitor.STABLE_CODES["remote_gate"]


def test_current_workflow_run_universe_paginates_without_metadata_filters(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    other_head = "c" * 40
    first_page = [
        {"id": run_id, "run_attempt": 1, "head_sha": other_head}
        for run_id in range(1, 101)
    ]
    exact_head_run = {"id": 451, "run_attempt": 2, "head_sha": "b" * 40}
    responses = iter(
        (
            ({"total_count": 101, "workflow_runs": first_page}, "1" * 64),
            ({"total_count": 101, "workflow_runs": [exact_head_run]}, "2" * 64),
        )
    )
    endpoints: list[str] = []

    def api(endpoint: str, **_kwargs: object) -> tuple[object, str]:
        endpoints.append(endpoint)
        return next(responses)

    monkeypatch.setattr(monitor, "_gh_api", api)
    runs, hashes = monitor._collect_current_workflow_run_universe(tmp_path)
    base = (
        f"repos/{monitor.REPOSITORY}/actions/workflows/"
        f"{Path(monitor.ROUND45_WORKFLOW_PATH).name}/runs"
    )
    assert endpoints == [
        f"{base}?per_page=100&page=1",
        f"{base}?per_page=100&page=2",
    ]
    assert runs == [*first_page, exact_head_run]
    assert hashes == ["1" * 64, "2" * 64]
    for endpoint in endpoints:
        for forbidden in (
            "branch=",
            "event=",
            "status=",
            "conclusion=",
            "name=",
            "path=",
        ):
            assert forbidden not in endpoint


def test_current_workflow_run_universe_fails_closed_on_page_drift(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    invalid_sequences: tuple[tuple[dict[str, object], ...], ...] = (
        ({"total_count": True, "workflow_runs": []},),
        ({"total_count": -1, "workflow_runs": []},),
        ({"total_count": 1, "workflow_runs": [None]},),
        ({"total_count": 101, "workflow_runs": [{}] * 101},),
        ({"total_count": 1, "workflow_runs": []},),
        ({"total_count": 0, "workflow_runs": [{}]},),
        (
            {"total_count": 101, "workflow_runs": [{}] * 100},
            {"total_count": 102, "workflow_runs": [{}]},
        ),
    )

    def api_for(
        payloads: tuple[dict[str, object], ...],
    ) -> Callable[..., tuple[object, str]]:
        responses = iter(payloads)

        def api(_endpoint: str, **_kwargs: object) -> tuple[object, str]:
            return next(responses), "1" * 64

        return api

    for payloads in invalid_sequences:
        monkeypatch.setattr(monitor, "_gh_api", api_for(payloads))
        assert _error_code(
            lambda: monitor._collect_current_workflow_run_universe(tmp_path)
        ) == monitor.STABLE_CODES["remote_gate"]


@pytest.mark.parametrize(
    ("malformed_field", "malformed_value"),
    (
        ("id", True),
        ("id", "450"),
        ("id", None),
        ("id", 0),
        ("id", -1),
        ("run_attempt", True),
        ("run_attempt", "1"),
        ("run_attempt", None),
        ("run_attempt", 0),
        ("run_attempt", -1),
    ),
)
def test_live_remote_run_candidates_fail_closed_on_malformed_ids(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    malformed_field: str,
    malformed_value: object,
) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    head = "b" * 40
    monkeypatch.setattr(monitor, "_validate_tool_contract", lambda: None)
    monkeypatch.setattr(monitor, "_validate_repository_identity", lambda _root: None)
    monkeypatch.setattr(
        monitor,
        "_remote_ref",
        lambda _root, branch, sha: (
            {"ref": f"refs/heads/{branch}", "object_type": "commit", "sha": sha},
            "1" * 64,
        ),
    )

    def git_output(args: list[str], **_kwargs: object) -> bytes:
        if args[1:3] == ["status", "--porcelain=v1"]:
            return b""
        if args[1:] == ["remote", "get-url", "origin"]:
            return f"{monitor.REMOTE_URL}\n".encode()
        if args[1:] == ["rev-parse", "HEAD"]:
            return f"{head}\n".encode()
        if args[1:] == ["branch", "--show-current"]:
            return f"{monitor.BRANCH}\n".encode()
        raise AssertionError(args)

    monkeypatch.setattr(monitor, "_run_ok", git_output)
    pull = {
        "number": 45,
        "id": 4500,
        "draft": True,
        "head": {
            "sha": head,
            "ref": monitor.BRANCH,
            "repo": {"full_name": monitor.REPOSITORY, "id": monitor.REPOSITORY_ID},
        },
        "base": {
            "sha": monitor.ROUND44_COMMIT,
            "ref": monitor.PARENT_BRANCH,
            "repo": {"full_name": monitor.REPOSITORY, "id": monitor.REPOSITORY_ID},
        },
    }
    run = {
        "id": 450,
        "run_attempt": 1,
        "head_sha": head,
        "name": monitor.ROUND45_WORKFLOW_NAME,
        "path": monitor.ROUND45_WORKFLOW_PATH,
        "event": "pull_request",
        "status": "completed",
        "conclusion": "success",
    }
    run[malformed_field] = malformed_value
    api_responses = iter(([pull], {"total_count": 1, "workflow_runs": [run]}))
    monkeypatch.setattr(
        monitor,
        "_gh_api",
        lambda *_args, **_kwargs: (next(api_responses), "2" * 64),
    )
    assert _error_code(lambda: monitor.collect_remote_gate_proof(repository)) == (
        monitor.STABLE_CODES["remote_gate"]
    )


@pytest.mark.parametrize(
    ("drifted_field", "drifted_value"),
    (
        ("event", "schedule"),
        ("status", "in_progress"),
        ("path", ".github/workflows/pages.yml"),
        ("conclusion", "failure"),
        ("name", "Pages build and deployment"),
        ("head_branch", "main"),
    ),
)
def test_remote_gate_rejects_newer_wrong_metadata_instead_of_old_success(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    drifted_field: str,
    drifted_value: str,
) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    head = "b" * 40
    monkeypatch.setattr(monitor, "_validate_tool_contract", lambda: None)
    monkeypatch.setattr(monitor, "_validate_repository_identity", lambda _root: None)
    monkeypatch.setattr(
        monitor,
        "_remote_ref",
        lambda _root, branch, sha: (
            {"ref": f"refs/heads/{branch}", "object_type": "commit", "sha": sha},
            "1" * 64,
        ),
    )

    def git_output(args: list[str], **_kwargs: object) -> bytes:
        if args[1:3] == ["status", "--porcelain=v1"]:
            return b""
        if args[1:] == ["remote", "get-url", "origin"]:
            return f"{monitor.REMOTE_URL}\n".encode()
        if args[1:] == ["rev-parse", "HEAD"]:
            return f"{head}\n".encode()
        if args[1:] == ["branch", "--show-current"]:
            return f"{monitor.BRANCH}\n".encode()
        raise AssertionError(args)

    monkeypatch.setattr(monitor, "_run_ok", git_output)
    pull = {
        "number": 45,
        "id": 4500,
        "draft": True,
        "head": {
            "sha": head,
            "ref": monitor.BRANCH,
            "repo": {"full_name": monitor.REPOSITORY, "id": monitor.REPOSITORY_ID},
        },
        "base": {
            "sha": monitor.ROUND44_COMMIT,
            "ref": monitor.PARENT_BRANCH,
            "repo": {"full_name": monitor.REPOSITORY, "id": monitor.REPOSITORY_ID},
        },
    }

    def run(run_id: int, conclusion: str) -> dict[str, object]:
        return {
            "id": run_id,
            "run_attempt": 1,
            "head_sha": head,
            "head_branch": monitor.BRANCH,
            "name": monitor.ROUND45_WORKFLOW_NAME,
            "path": monitor.ROUND45_WORKFLOW_PATH,
            "event": "pull_request",
            "status": "completed",
            "conclusion": conclusion,
        }

    old_success = run(450, "success")
    newest_failure = run(451, "success")
    newest_failure[drifted_field] = drifted_value
    responses = iter(
        (
            [pull],
            {
                "total_count": 2,
                "workflow_runs": [old_success, newest_failure],
            },
            newest_failure,
        )
    )
    endpoints: list[str] = []

    def api(endpoint: str, **_kwargs: object) -> tuple[object, str]:
        endpoints.append(endpoint)
        return next(responses), "2" * 64

    monkeypatch.setattr(monitor, "_gh_api", api)
    assert _error_code(lambda: monitor.collect_remote_gate_proof(repository)) == (
        monitor.STABLE_CODES["remote_gate"]
    )
    expected_runs_endpoint = (
        f"repos/{monitor.REPOSITORY}/actions/workflows/"
        f"{Path(monitor.ROUND45_WORKFLOW_PATH).name}/runs?per_page=100&page=1"
    )
    assert endpoints[1] == expected_runs_endpoint
    for forbidden in (
        "branch=",
        "event=",
        "status=",
        "conclusion=",
        "name=",
        "path=",
    ):
        assert forbidden not in endpoints[1]
    assert endpoints[2] == f"repos/{monitor.REPOSITORY}/actions/runs/451"


@pytest.mark.parametrize("status_output", (b" M tracked.py\n", b"?? untracked.py\n"))
def test_remote_gate_stops_on_dirty_or_untracked_worktree_before_github(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    status_output: bytes,
) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    monkeypatch.setattr(monitor, "_validate_tool_contract", lambda: None)
    monkeypatch.setattr(monitor, "_validate_repository_identity", lambda _root: None)
    commands: list[list[str]] = []

    def run_ok(args: list[str], **_kwargs: object) -> bytes:
        commands.append(args)
        if args[1:3] == ["status", "--porcelain=v1"]:
            return status_output
        raise AssertionError("worktree gate must run before all other commands")

    monkeypatch.setattr(monitor, "_run_ok", run_ok)
    monkeypatch.setattr(
        monitor,
        "_gh_api",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("GitHub API must not run for a dirty worktree")
        ),
    )
    assert _error_code(lambda: monitor.collect_remote_gate_proof(repository)) == (
        monitor.STABLE_CODES["authorization"]
    )
    assert len(commands) == 1


def test_saved_tsq_parser_binds_policy_certreq_nonce_and_exact_intent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    digest = "ab" * 32

    def line(offset: int, octets: list[str]) -> str:
        rendered = " ".join(octets[:8]) + "-" + " ".join(octets[8:])
        return f"    {offset:04x} - {rendered}   ................"

    octets = [digest[index : index + 2] for index in range(0, len(digest), 2)]
    text = "\n".join(
        [
            "Version: 1",
            "Hash Algorithm: sha256",
            "Message data:",
            line(0, octets[:16]),
            line(16, octets[16:]),
            f"Policy OID: {monitor.TSA_POLICY_OID}",
            "Nonce: 0x1234567890ABCDEF",
            "Certificate required: yes",
            "Extensions:",
            "",
        ]
    ).encode()
    monkeypatch.setattr(monitor, "_run_ok", lambda *_args, **_kwargs: text)
    monkeypatch.setattr(
        monitor,
        "_query_nonce_from_der",
        lambda _query: int("1234567890ABCDEF", 16),
    )
    assert monitor._validate_anchor_query(
        b"\x30\x00",
        expected_imprint_sha256=digest,
    ).startswith("Version: 1")
    assert _error_code(
        lambda: monitor._validate_anchor_query(
            b"\x30\x00",
            expected_imprint_sha256="cd" * 32,
        )
    ) == monitor.STABLE_CODES["external_anchor"]


def test_accuracy_parser_is_fail_closed_and_uses_an_upper_bound() -> None:
    assert _error_code(lambda: monitor._parse_accuracy("Accuracy: unspecified\n")) == (
        monitor.STABLE_CODES["external_anchor"]
    )
    delta, exact = monitor._parse_accuracy(
        "Accuracy: 0x01 seconds, 0x1F4 millis, 0x64 micros\n"
    )
    assert delta.total_seconds() == pytest.approx(1.5001)
    assert exact == {
        "accuracy_unspecified": False,
        "seconds": 1,
        "millis": 500,
        "micros": 100,
    }
    assert _error_code(lambda: monitor._parse_accuracy("Accuracy: maybe\n")) == (
        monitor.STABLE_CODES["external_anchor"]
    )
    assert _error_code(lambda: monitor._parse_accuracy("Status: Granted.\n")) == (
        monitor.STABLE_CODES["external_anchor"]
    )


def test_anchor_verifier_rejects_policy_signer_signature_and_time_drift(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    query = tmp_path / "anchor_request.tsq"
    response = tmp_path / "anchor_response.tsr"
    digest = "a" * 64
    octets = [digest[index : index + 2] for index in range(0, len(digest), 2)]

    def message_line(offset: int, values: list[str]) -> str:
        rendered = " ".join(values[:8]) + "-" + " ".join(values[8:])
        return f"    {offset:04x} - {rendered}   ................"

    message_lines = "\n".join(
        (message_line(0, octets[:16]), message_line(16, octets[16:]))
    )
    query.write_bytes(b"\x30\x00")
    response.write_bytes(b"\x30\x07\x30\x03\x02\x01\x00\x30\x00")
    query.chmod(0o600)
    response.chmod(0o600)
    responder_pem = (ROOT / monitor.RESPONDER_CERT_PATH).read_bytes()
    state = {
        "query_text": (
            "Version: 1\n"
            "Hash Algorithm: sha256\n"
            "Message data:\n"
            f"{message_lines}\n"
            f"Policy OID: {monitor.TSA_POLICY_OID}\n"
            "Nonce: 0x1234567890ABCDEF\n"
            "Certificate required: yes\n"
            "Extensions:\n"
        ).encode(),
        "token_text": (
            "Version: 1\n"
            f"Policy OID: {monitor.TSA_POLICY_OID}\n"
            "Hash Algorithm: sha256\n"
            "Message data:\n"
            f"{message_lines}\n"
            "Serial number: 0x45\n"
            "Time stamp: Aug 10 06:00:02 2026 GMT\n"
            "Accuracy: 1 seconds\n"
            "Ordering: no\n"
            "Nonce: 0x1234567890ABCDEF\n"
            "TSA: unspecified\n"
            "Extensions:\n"
        ).encode(),
        "cms": (
            "signerInfos:\n"
            " d.issuerAndSerialNumber:\n"
            f" serialNumber: {monitor.TSA_RESPONDER_SERIAL}\n"
        ).encode(),
        "verify": True,
    }

    def fake_run_ok(args: list[str], **_kwargs: object) -> bytes:
        if args[1:3] == ["ts", "-query"]:
            return state["query_text"]  # type: ignore[return-value]
        if args[1:3] == ["ts", "-reply"] and "-token_out" in args:
            return b"\x30\x00"
        if args[1:3] == ["ts", "-reply"] and "-token_in" in args:
            assert args[args.index("-in") + 1] == "/dev/stdin"
            return state["token_text"]  # type: ignore[return-value]
        if args[1:3] == ["ts", "-verify"]:
            if not state["verify"]:
                raise monitor.Form4MonitorStartError(
                    monitor.STABLE_CODES["external_anchor"],
                    "synthetic signature failure",
                )
            return b"Verification: OK\n"
        if args[1] == "cms":
            return state["cms"]  # type: ignore[return-value]
        if args[1] == "pkcs7":
            return responder_pem
        raise AssertionError(args)

    monkeypatch.setattr(monitor, "_owner_file_metadata", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        monitor,
        "_query_nonce_from_der",
        lambda _query: int("1234567890ABCDEF", 16),
    )
    monkeypatch.setattr(monitor, "_run_ok", fake_run_ok)

    def verify(*, earliest: str = "2026-08-10T06:00:00Z") -> dict[str, object]:
        return monitor._verify_anchor(
            query_path=query,
            response_path=response,
            repository_root=ROOT,
            earliest_time=earliest,
            expected_intent_sha256=digest,
        )

    anchor = verify()
    assert anchor["signature_verified"] is True
    assert anchor["monitor_started_at"] == "2026-08-10T06:00:03Z"

    response.write_bytes(b"\x30\x07\x30\x03\x02\x01\x01\x30\x00")
    assert _error_code(verify) == monitor.STABLE_CODES["external_anchor"]
    response.write_bytes(
        b"\x30\x0f\x30\x0b\x02\x01\x00\x30\x06\x0c\x04evil\x30\x00"
    )
    assert _error_code(verify) == monitor.STABLE_CODES["external_anchor"]
    response.write_bytes(b"\x30\x07\x30\x03\x02\x01\x00\x30\x00")

    valid_text = state["token_text"]
    state["token_text"] = bytes(valid_text).replace(
        monitor.TSA_POLICY_OID.encode(), b"1.2.3.4"
    )
    assert _error_code(verify) == monitor.STABLE_CODES["external_anchor"]

    state["token_text"] = valid_text
    valid_cms = state["cms"]
    state["cms"] = bytes(valid_cms).replace(
        monitor.TSA_RESPONDER_SERIAL.encode(), b"01"
    )
    assert _error_code(verify) == monitor.STABLE_CODES["external_anchor"]

    state["cms"] = valid_cms
    state["verify"] = False
    assert _error_code(verify) == monitor.STABLE_CODES["external_anchor"]

    state["verify"] = True
    assert _error_code(lambda: verify(earliest="2026-08-10T06:00:02Z")) == (
        monitor.STABLE_CODES["external_anchor"]
    )


@pytest.mark.skipif(
    not Path(monitor.TOOL_CONTRACT["openssl"]["path"]).is_file(),
    reason="pinned local OpenSSL is unavailable",
)
def test_pinned_openssl_token_reply_reads_actual_stdin_not_dash() -> None:
    completed = monitor._run_process(
        [
            monitor.TOOL_CONTRACT["openssl"]["path"],
            "ts",
            "-reply",
            "-token_in",
            "-in",
            "/dev/stdin",
            "-text",
        ],
        input_bytes=b"\x30\x00",
        code=monitor.STABLE_CODES["external_anchor"],
    )
    assert completed.returncode != 0
    assert b"calling fopen(-, rb)" not in completed.stderr
    assert b"calling fopen(/dev/stdin, rb)" not in completed.stderr

    verify_source = (ROOT / "usfddk/form4_monitor_start.py").read_text(encoding="utf-8")
    verify_body = verify_source.split("def _verify_anchor(", 1)[1].split(
        "def _create_response_file(", 1
    )[0]
    assert '"-no-CApath"' not in verify_body
    assert '"-no-CAstore"' not in verify_body


@pytest.mark.skipif(
    not Path(monitor.TOOL_CONTRACT["openssl"]["path"]).is_file(),
    reason="pinned local OpenSSL is unavailable",
)
def test_pinned_openssl_verifies_bound_offline_signed_timestamp_fixture(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = ROOT / "tests/fixtures/form4_round45_offline_tsa"
    query_path = tmp_path / "query.tsq"
    response_path = tmp_path / "response.tsr"
    query_path.write_bytes(
        base64.b64decode((fixture / "query.tsq.b64").read_text().strip(), validate=True)
    )
    response_path.write_bytes(
        base64.b64decode(
            (fixture / "response.tsr.b64").read_text().strip(),
            validate=True,
        )
    )
    query_path.chmod(0o600)
    response_path.chmod(0o600)
    certificate = (fixture / "tsa.crt").resolve()
    certificate_fingerprint = monitor._certificate_fingerprint(certificate)
    assert certificate_fingerprint == (
        "2dfbda521492fe8aa6f6614885802a9a1c3e755bc566e7d5e253463bacf7e0c6"
    )
    monkeypatch.setattr(monitor, "ROOT_CERT_PATH", str(certificate))
    monkeypatch.setattr(monitor, "INTERMEDIATE_CERT_PATH", str(certificate))
    monkeypatch.setattr(
        monitor,
        "TSA_RESPONDER_SERIAL",
        "6f25c2edd68127aa13c8ba2b7bd3b5b26604b471",
    )
    monkeypatch.setattr(monitor, "TSA_RESPONDER_FINGERPRINT", certificate_fingerprint)
    monkeypatch.setattr(monitor, "TSA_INTERMEDIATE_FINGERPRINT", certificate_fingerprint)
    monkeypatch.setattr(monitor, "TSA_ROOT_FINGERPRINT", certificate_fingerprint)
    monkeypatch.setattr(monitor, "_assert_no_acl_or_xattr", lambda *_args, **_kwargs: None)

    anchor = monitor._verify_anchor(
        query_path=query_path,
        response_path=response_path,
        repository_root=Path("/"),
        earliest_time="2026-08-10T07:19:33Z",
        expected_intent_sha256="a" * 64,
    )
    assert anchor["signature_verified"] is True
    assert anchor["signed_gen_time"] == "2026-08-10T07:19:35Z"
    assert anchor["monitor_started_at"] == "2026-08-10T07:19:36.500100Z"
    assert anchor["revocation_checked"] is False
    assert anchor["long_term_validation"] is False


def test_monitor_and_dedicated_account_are_strict_zero_state() -> None:
    authorization_commit = "a" * 40
    account = monitor._account_zero_state(authorization_commit)
    assert account["proof_scope"] == "round45_form4_runtime_namespace_only"
    assert account["other_user_accounts_in_scope"] is False
    assert account["external_broker_account_zero_proven"] is False
    assert account["paper"] == {
        "authorized": False,
        "funding_usd": 0,
        "cash_usd": 0,
        "nav_points": 0,
        "positions": [],
        "open_orders": [],
        "trades": [],
        "backfilled_trades": 0,
    }
    assert account["broker"] == {
        "binding_state": "unbound",
        "account_identifier_count": 0,
        "credential_handle_count": 0,
        "transport_count": 0,
    }
    assert account["real_ledger"] == {
        "positions": [],
        "orders": [],
        "fills": [],
        "transfers": [],
        "entry_count": 0,
        "real_money_action_usd": 0,
    }
    assert account["receipt_sha256"] == monitor.canonical_sha256(
        account,
        omit="receipt_sha256",
    )
    monitor._assert_private_zero_state(account)

    nonzero = copy.deepcopy(account)
    paper = nonzero["paper"]
    assert isinstance(paper, dict)
    paper["cash_usd"] = 1
    nonzero["receipt_sha256"] = monitor.canonical_sha256(
        nonzero,
        omit="receipt_sha256",
    )
    assert _error_code(lambda: monitor._assert_private_zero_state(nonzero)) == (
        monitor.STABLE_CODES["non_engineering"]
    )

    bool_as_zero = copy.deepcopy(account)
    bool_paper = bool_as_zero["paper"]
    assert isinstance(bool_paper, dict)
    bool_paper["cash_usd"] = False
    bool_as_zero["receipt_sha256"] = monitor.canonical_sha256(
        bool_as_zero,
        omit="receipt_sha256",
    )
    assert _error_code(lambda: monitor._assert_private_zero_state(bool_as_zero)) == (
        monitor.STABLE_CODES["non_engineering"]
    )

    state = monitor._monitor_state(authorization_commit)
    assert state["status"] == "monitor_started_collection_locked"
    assert state["state_boundary"] == monitor.STATE_BOUNDARY
    assert state["permission"] == monitor.PERMISSION
    assert state["today_action"] == "今天不下單"
    assert all(
        state["permission"][key] is False  # type: ignore[index]
        for key in (
            "sec_network_collection",
            "prospective_collector_implemented",
            "sec_collection_capability_issued",
            "candidate_selection",
            "candidate_allocation",
            "strategy_run",
            "performance_readout",
            "paper",
            "real_money",
            "congress_collection",
        )
    )


def test_sec_capability_is_locked_before_any_socket() -> None:
    with patch.object(socket, "create_connection") as create_connection:
        assert _error_code(monitor.assert_sec_collection_locked) == monitor.STABLE_CODES[
            "live_network"
        ]
        create_connection.assert_not_called()


def test_monitor_start_source_has_no_sec_transport_or_selection_path() -> None:
    source = (ROOT / "usfddk/form4_monitor_start.py").read_text(encoding="utf-8")
    for forbidden in (
        "www.sec.gov",
        "sec.gov/Archives",
        "requests.get",
        "requests.post",
        "urllib.request",
        "httpx.",
        "yfinance",
        "candidate_ticker",
        "portfolio_weight",
        "form4_admission_collection",
        "form4_multipath_reconciliation",
        "form4_forward_admission_contract",
        "Form4Admission",
    ):
        assert forbidden not in source
    assert monitor.PERMISSION["sec_network_collection"] is False
    assert monitor.PERMISSION["candidate_selection"] is False
    assert monitor.PERMISSION["strategy_run"] is False
    assert monitor.PERMISSION["paper"] is False
    assert monitor.STATE_BOUNDARY["sec_request_count"] == 0


def test_audit_chain_rejects_truncation_reorder_duplicate_and_bool_count() -> None:
    authorization_commit = "a" * 40
    anchor = {
        "response_sha256": "b" * 64,
        "signed_gen_time": "2026-08-10T06:00:01Z",
        "monitor_started_at": "2026-08-10T06:00:02Z",
    }
    records = monitor._expected_audit_records(
        authorization_commit,
        query_sha256="c" * 64,
        anchor=anchor,
    )
    valid = b"".join(monitor._jsonl_line(record) for record in records)
    parsed, head = monitor._parse_chain_bytes(valid, expected_kind="audit")
    assert parsed == records
    assert head == records[-1]["entry_sha256"]

    reordered = b"".join(
        monitor._jsonl_line(records[index])
        for index in (0, 2, 1)
    )
    duplicate_ordinal = copy.deepcopy(records)
    duplicate_ordinal[2]["ordinal"] = 1
    duplicate_ordinal[2]["entry_sha256"] = monitor.canonical_sha256(
        duplicate_ordinal[2],
        omit="entry_sha256",
    )
    bool_count = copy.deepcopy(records)
    bool_count[1]["event_count"] = True
    bool_count[1]["entry_sha256"] = monitor.canonical_sha256(
        bool_count[1],
        omit="entry_sha256",
    )
    invalid_values = (
        valid[:-1],
        reordered,
        b"".join(monitor._jsonl_line(record) for record in duplicate_ordinal),
        b"".join(monitor._jsonl_line(record) for record in bool_count),
    )
    for raw in invalid_values:
        assert _error_code(
            lambda value=raw: monitor._parse_chain_bytes(
                value,
                expected_kind="audit",
            )
        ) == monitor.STABLE_CODES["attempt_ledger"]


def test_dirfd_writer_is_owner_only_create_once_and_path_anchored(tmp_path: Path) -> None:
    parent = tmp_path / "owner-only"
    parent.mkdir(mode=0o700)
    parent.chmod(0o700)
    parent_fd = monitor._open_directory_fd(parent)
    try:
        monitor._validate_directory_fd(parent_fd)
        assert monitor._mkdir_at(parent_fd, "namespace") is True
        assert monitor._mkdir_at(parent_fd, "namespace") is False
        namespace = parent / "namespace"
        assert stat.S_IMODE(namespace.stat().st_mode) == 0o700
    finally:
        os.close(parent_fd)

    namespace_fd = monitor._open_directory_fd(namespace)
    moved = parent / "namespace-moved"
    replacement = parent / "namespace"
    namespace.rename(moved)
    replacement.mkdir(mode=0o700)
    replacement.chmod(0o700)
    try:
        payload = b"create once through the opened directory\n"
        digest = monitor._write_create_at(namespace_fd, "receipt.json", payload)
        created = moved / "receipt.json"
        assert created.read_bytes() == payload
        assert digest == _sha256_bytes(payload)
        assert stat.S_IMODE(created.stat().st_mode) == 0o600
        assert created.stat().st_uid == os.getuid()
        assert created.stat().st_nlink == 1
        assert not (replacement / "receipt.json").exists()
        assert _error_code(
            lambda: monitor._write_create_at(namespace_fd, "receipt.json", b"replace")
        ) == monitor.STABLE_CODES["start_receipt"]
        assert _error_code(
            lambda: monitor._write_create_at(namespace_fd, "../escape", b"escape")
        ) == monitor.STABLE_CODES["private_boundary"]
    finally:
        os.close(namespace_fd)

    hardlink = moved / "receipt-hardlink.json"
    os.link(moved / "receipt.json", hardlink)
    assert _error_code(
        lambda: monitor._owner_file_metadata(
            moved / "receipt.json",
            code=monitor.STABLE_CODES["private_boundary"],
        )
    ) == monitor.STABLE_CODES["private_boundary"]


def test_private_metadata_rejects_symlinks_and_wrong_uid(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target_directory = tmp_path / "target-directory"
    target_directory.mkdir(mode=0o700)
    target_directory.chmod(0o700)
    directory_link = tmp_path / "directory-link"
    directory_link.symlink_to(target_directory, target_is_directory=True)
    assert _error_code(
        lambda: monitor._owner_directory_metadata(
            directory_link,
            code=monitor.STABLE_CODES["private_boundary"],
        )
    ) == monitor.STABLE_CODES["private_boundary"]

    target_file = tmp_path / "target-file"
    target_file.write_bytes(b"owner-only\n")
    target_file.chmod(0o600)
    file_link = tmp_path / "file-link"
    file_link.symlink_to(target_file)
    assert _error_code(
        lambda: monitor._owner_file_metadata(
            file_link,
            code=monitor.STABLE_CODES["private_boundary"],
        )
    ) == monitor.STABLE_CODES["private_boundary"]

    metadata = target_file.lstat()
    wrong_uid = os.stat_result(
        (
            metadata.st_mode,
            metadata.st_ino,
            metadata.st_dev,
            metadata.st_nlink,
            metadata.st_uid + 1,
            metadata.st_gid,
            metadata.st_size,
            metadata.st_atime,
            metadata.st_mtime,
            metadata.st_ctime,
        )
    )
    monkeypatch.setattr(Path, "lstat", lambda _path: wrong_uid)
    assert _error_code(
        lambda: monitor._owner_file_metadata(
            target_file,
            code=monitor.STABLE_CODES["private_boundary"],
        )
    ) == monitor.STABLE_CODES["private_boundary"]


def test_existing_lock_with_wrong_mode_is_rejected_without_repair(tmp_path: Path) -> None:
    root = tmp_path / "runtime"
    root.mkdir(mode=0o700)
    root.chmod(0o700)
    lock = root / ".monitor-start.lock"
    lock.write_bytes(b"")
    lock.chmod(0o644)
    root_fd = monitor._open_directory_fd(root)
    try:
        assert _error_code(lambda: monitor._open_lock(root_fd)) == (
            monitor.STABLE_CODES["private_boundary"]
        )
    finally:
        os.close(root_fd)
    assert stat.S_IMODE(lock.stat().st_mode) == 0o644


def test_git_and_gh_subprocesses_drop_redirect_and_transport_overrides(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    def fake_run(args: list[str], **kwargs: object) -> subprocess.CompletedProcess[bytes]:
        captured["args"] = args
        captured["env"] = kwargs.get("env")
        return subprocess.CompletedProcess(args, 0, b"", b"")

    monkeypatch.setenv("GIT_DIR", "/tmp/untrusted-git-dir")
    monkeypatch.setenv("GIT_WORK_TREE", "/tmp/untrusted-work-tree")
    monkeypatch.setenv("HTTPS_PROXY", "http://untrusted-proxy.invalid")
    monkeypatch.setenv("SSL_CERT_FILE", "/tmp/untrusted-ca.pem")
    monkeypatch.setenv("GH_CONFIG_DIR", "/tmp/untrusted-gh-config")
    monkeypatch.setattr(subprocess, "run", fake_run)
    monitor._run_process(
        [monitor.TOOL_CONTRACT["git"]["path"], "status"],
        cwd=ROOT,
        code=monitor.STABLE_CODES["authorization"],
    )
    environment = captured["env"]
    assert isinstance(environment, dict)
    assert "GIT_DIR" not in environment
    assert "GIT_WORK_TREE" not in environment
    assert environment["GIT_CONFIG_GLOBAL"] == "/dev/null"
    assert environment["GIT_CONFIG_NOSYSTEM"] == "1"
    assert environment["GIT_TERMINAL_PROMPT"] == "0"

    monitor._run_process(
        [monitor.TOOL_CONTRACT["gh"]["path"], "api", "user"],
        cwd=ROOT,
        code=monitor.STABLE_CODES["remote_gate"],
    )
    gh_environment = captured["env"]
    assert isinstance(gh_environment, dict)
    assert set(gh_environment).issubset(
        {"GH_PAGER", "GH_TOKEN", "GITHUB_TOKEN", "HOME", "LANG", "LC_ALL"}
    )
    assert gh_environment["HOME"] == str(Path.home())
    assert "HTTPS_PROXY" not in gh_environment
    assert "SSL_CERT_FILE" not in gh_environment
    assert "GH_CONFIG_DIR" not in gh_environment


def test_private_location_rejects_relative_repository_and_non_owner_mode(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = tmp_path / "repository"
    repository.mkdir(mode=0o700)
    repository.chmod(0o700)
    outside_parent = tmp_path / "outside"
    outside_parent.mkdir(mode=0o700)
    outside_parent.chmod(0o700)
    monkeypatch.setattr(
        monitor,
        "PRIVATE_PARENT_PATH_SHA256",
        _sha256_bytes(str(outside_parent).encode()),
    )
    monkeypatch.setattr(
        monitor,
        "PRIVATE_ROOT_PATH_SHA256",
        _sha256_bytes(str(outside_parent / "runtime").encode()),
    )
    # This test isolates canonical-location and POSIX owner-mode checks. The
    # separate metadata tests below exercise the pinned macOS ACL/xattr tools,
    # which are deliberately unavailable on the Linux Actions runner.
    monkeypatch.setattr(monitor, "_assert_no_acl_or_xattr", lambda *_args, **_kwargs: None)

    monitor._validate_private_location(outside_parent / "runtime", repository)
    assert _error_code(
        lambda: monitor._validate_private_location(
            outside_parent / "alternate-runtime",
            repository,
        )
    ) == monitor.STABLE_CODES["private_boundary"]
    assert _error_code(
        lambda: monitor._validate_private_location(Path("relative/runtime"), repository)
    ) == monitor.STABLE_CODES["private_boundary"]
    assert _error_code(
        lambda: monitor._validate_private_location(repository / "runtime", repository)
    ) == monitor.STABLE_CODES["private_boundary"]

    outside_parent.chmod(0o755)
    assert _error_code(
        lambda: monitor._validate_private_location(outside_parent / "runtime", repository)
    ) == monitor.STABLE_CODES["private_boundary"]


def test_private_metadata_rejects_acl_and_extended_attributes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    private = tmp_path / "private"
    private.mkdir(mode=0o700)
    private.chmod(0o700)

    def acl_listing(args: list[str], **_kwargs: object) -> bytes:
        if args[0] == monitor.TOOL_CONTRACT["xattr"]["path"]:
            return b""
        if args[0] == monitor.TOOL_CONTRACT["ls"]["path"]:
            return b"drwx------+ 2 owner group 64 Aug 10 00:00 private\n"
        raise AssertionError(args)

    monkeypatch.setattr(monitor, "_run_ok", acl_listing)
    assert _error_code(
        lambda: monitor._owner_directory_metadata(
            private,
            code=monitor.STABLE_CODES["private_boundary"],
        )
    ) == monitor.STABLE_CODES["private_boundary"]

    def xattr_listing(args: list[str], **_kwargs: object) -> bytes:
        if args[0] == monitor.TOOL_CONTRACT["xattr"]["path"]:
            return b"com.example.untrusted\n"
        raise AssertionError(args)

    monkeypatch.setattr(monitor, "_run_ok", xattr_listing)
    assert _error_code(
        lambda: monitor._owner_directory_metadata(
            private,
            code=monitor.STABLE_CODES["private_boundary"],
        )
    ) == monitor.STABLE_CODES["private_boundary"]


def test_private_metadata_fails_closed_when_pinned_xattr_tool_is_unavailable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    private = tmp_path / "private"
    private.mkdir(mode=0o700)
    private.chmod(0o700)
    monkeypatch.setitem(
        monitor.TOOL_CONTRACT["xattr"],
        "path",
        str(tmp_path / "missing-pinned-xattr"),
    )

    assert _error_code(
        lambda: monitor._owner_directory_metadata(
            private,
            code=monitor.STABLE_CODES["private_boundary"],
        )
    ) == monitor.STABLE_CODES["private_boundary"]


def test_volume_receipt_rejects_encryption_identity_and_type_mutations(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    private_root = tmp_path / "runtime"
    private_root.mkdir(mode=0o700)
    private_root.chmod(0o700)
    payload = _volume_fixture(private_root)
    payload["attestation_sha256"] = monitor.canonical_sha256(
        payload,
        omit="attestation_sha256",
    )
    monkeypatch.setattr(
        monitor,
        "PRIVATE_ROOT_PATH_SHA256",
        _sha256_bytes(str(private_root).encode()),
    )
    monkeypatch.setattr(
        monitor,
        "_volume_attestation",
        lambda _path: copy.deepcopy(payload),
    )
    monitor._validate_volume_receipt(payload, private_root=private_root)

    for key, replacement in (
        ("filevault", False),
        ("encryption", False),
        ("encryption_this_volume_proper", False),
        ("locked", True),
        ("writable", 1),
        ("st_ino", True),
        ("volume_uuid", "not-a-uuid"),
    ):
        mutated = copy.deepcopy(payload)
        mutated[key] = replacement
        mutated["attestation_sha256"] = monitor.canonical_sha256(
            mutated,
            omit="attestation_sha256",
        )
        assert _error_code(
            lambda value=mutated: monitor._validate_volume_receipt(
                value,
                private_root=private_root,
            )
        ) == monitor.STABLE_CODES["private_boundary"]


def test_raw_volume_attestation_binds_df_plist_and_filevault_identity(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    private_root = tmp_path / "runtime"
    private_root.mkdir(mode=0o700)
    private_root.chmod(0o700)
    device = "/dev/test-round45"
    mount_point = str(private_root.parent)
    df_raw = (
        "Filesystem 512-blocks Used Available Capacity Mounted on\n"
        f"{device} 1000 100 900 10% {mount_point}\n"
    ).encode()
    base_info: dict[str, object] = {
        "FileVault": True,
        "Encryption": True,
        "EncryptionThisVolumeProper": True,
        "Writable": True,
        "WritableVolume": True,
        "Internal": True,
        "SolidState": True,
        "Locked": False,
        "VolumeUUID": "00000000-0000-0000-0000-000000000045",
        "DeviceIdentifier": "test-round45",
        "DeviceNode": device,
        "MountPoint": mount_point,
    }
    active_info = copy.deepcopy(base_info)

    def run_ok(args: list[str], **_kwargs: object) -> bytes:
        if args[:2] == [monitor.TOOL_CONTRACT["df"]["path"], "-P"]:
            return df_raw
        if args[:3] == [
            monitor.TOOL_CONTRACT["diskutil"]["path"],
            "info",
            "-plist",
        ]:
            return plistlib.dumps(active_info)
        if args == [monitor.TOOL_CONTRACT["fdesetup"]["path"], "status"]:
            return b"FileVault is On.\n"
        raise AssertionError(args)

    monkeypatch.setattr(monitor, "_run_ok", run_ok)
    valid = monitor._volume_attestation(private_root)
    assert valid["device"] == device
    assert valid["device_identifier"] == "test-round45"
    assert valid["mount_point"] == mount_point
    assert valid["filevault"] is True

    for key, replacement in (
        ("DeviceNode", "/dev/drifted"),
        ("DeviceIdentifier", "drifted"),
        ("MountPoint", "/drifted"),
        ("FileVault", False),
        ("Encryption", False),
        ("EncryptionThisVolumeProper", False),
        ("Locked", True),
    ):
        active_info = copy.deepcopy(base_info)
        active_info[key] = replacement
        assert _error_code(lambda: monitor._volume_attestation(private_root)) == (
            monitor.STABLE_CODES["private_boundary"]
        )



def test_tsa_transport_is_one_attempt_without_retry_redirect_proxy_or_fallback(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[list[str], dict[str, object]]] = []

    def fake_run_ok(args: list[str], **kwargs: object) -> bytes:
        calls.append((args, kwargs))
        return b"200\napplication/timestamp-reply; charset=binary\n2\n0\n"

    monkeypatch.setattr(monitor, "_run_ok", fake_run_ok)
    monkeypatch.setenv("HTTP_PROXY", "http://must-not-leak.invalid")
    monkeypatch.setenv("https_proxy", "http://must-not-leak.invalid")
    response_path = tmp_path / "response.tsr"
    response_fd = os.open(response_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        receipt = monitor._post_anchor_once(b"\x30\x00", response_fd)
    finally:
        os.close(response_fd)

    assert receipt == {
        "http_status": 200,
        "content_type": "application/timestamp-reply",
        "response_bytes": 2,
        "redirect_count": 0,
        "request_count": 1,
        "retry_count": 0,
        "proxy_used": False,
    }
    assert len(calls) == 1
    args, kwargs = calls[0]
    assert args.count(monitor.TSA_URL) == 1
    assert args[1] == "--disable"
    assert args[args.index("--retry") + 1] == "0"
    assert args[args.index("--max-redirs") + 1] == "0"
    assert args[args.index("--noproxy") + 1] == "*"
    assert "--location" not in args
    assert kwargs["pass_fds"] == (response_fd,)
    environment = kwargs["env"]
    assert environment == {"LANG": "C", "LC_ALL": "C"}


def test_tsa_failure_is_durable_and_reentry_cannot_attempt_again(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository, authorization_path, private_root = _start_paths(tmp_path)
    _, remote_proof = _install_start_fixtures(monkeypatch, private_root)
    attempts = 0
    remote_calls = 0

    def collect_once(*_args: object, **_kwargs: object) -> dict[str, object]:
        nonlocal remote_calls
        remote_calls += 1
        return copy.deepcopy(remote_proof)

    monkeypatch.setattr(monitor, "collect_remote_gate_proof", collect_once)

    def fail_after_socket_ledger(query: bytes, response_fd: int) -> dict[str, object]:
        nonlocal attempts
        attempts += 1
        assert query == b"round45-fixed-query"
        assert response_fd >= 0
        audit_path = (
            private_root
            / monitor.AUTHORIZATION_ID
            / monitor.LEDGER_FILENAMES["audit"]
        )
        records, _ = monitor._parse_chain(audit_path, expected_kind="audit")
        assert [record["event"] for record in records] == [
            "genesis",
            "tsa_request_started",
        ]
        raise monitor.Form4MonitorStartError(
            monitor.STABLE_CODES["external_anchor"],
            "synthetic one-attempt failure",
        )

    monkeypatch.setattr(monitor, "_post_anchor_once", fail_after_socket_ledger)
    def launch() -> dict[str, object]:
        return monitor.start_form4_monitor(
            repository_root=repository,
            authorization_path=authorization_path,
            private_root=private_root,
        )

    assert _error_code(launch) == monitor.STABLE_CODES["external_anchor"]
    assert attempts == 1
    assert remote_calls == 1

    namespace = private_root / monitor.AUTHORIZATION_ID
    response = namespace / "anchor_response.tsr"
    assert response.is_file()
    assert response.stat().st_size == 0
    assert stat.S_IMODE(response.stat().st_mode) == 0o600
    assert not (namespace / "monitor_start_receipt.json").exists()
    assert not (namespace / "monitor_state.json").exists()

    assert _error_code(launch) == monitor.STABLE_CODES["start_receipt"]
    assert attempts == 1
    assert remote_calls == 1


@pytest.mark.parametrize(
    "partial_name",
    (None, *sorted(monitor.NAMESPACE_FILES)),
)
def test_any_final_less_namespace_stops_before_remote_or_tsa(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    partial_name: str | None,
) -> None:
    repository, authorization_path, private_root = _start_paths(tmp_path)
    _install_start_fixtures(monkeypatch, private_root)
    private_root.mkdir(mode=0o700)
    private_root.chmod(0o700)
    namespace = private_root / monitor.AUTHORIZATION_ID
    namespace.mkdir(mode=0o700)
    namespace.chmod(0o700)
    if partial_name is not None:
        artifact = namespace / partial_name
        if partial_name == "objects":
            artifact.mkdir(mode=0o700)
            artifact.chmod(0o700)
        else:
            artifact.write_bytes(b"partial\n")
            artifact.chmod(0o600)
    remote_calls = 0
    tsa_calls = 0

    def forbidden_remote(*_args: object, **_kwargs: object) -> dict[str, object]:
        nonlocal remote_calls
        remote_calls += 1
        raise AssertionError("remote proof must not run for partial state")

    def forbidden_tsa(*_args: object, **_kwargs: object) -> dict[str, object]:
        nonlocal tsa_calls
        tsa_calls += 1
        raise AssertionError("TSA must not run for partial state")

    monkeypatch.setattr(monitor, "collect_remote_gate_proof", forbidden_remote)
    monkeypatch.setattr(monitor, "_post_anchor_once", forbidden_tsa)
    assert _error_code(
        lambda: monitor.start_form4_monitor(
            repository_root=repository,
            authorization_path=authorization_path,
            private_root=private_root,
        )
    ) == monitor.STABLE_CODES["start_receipt"]
    assert remote_calls == 0
    assert tsa_calls == 0

def test_complete_start_is_byte_idempotent_and_uses_one_tsa_response(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository, authorization_path, private_root = _start_paths(tmp_path)
    _, remote_proof = _install_start_fixtures(monkeypatch, private_root)
    response = b"\x30\x00"
    attempts = 0
    remote_calls = 0

    def collect_once(*_args: object, **_kwargs: object) -> dict[str, object]:
        nonlocal remote_calls
        remote_calls += 1
        return copy.deepcopy(remote_proof)

    monkeypatch.setattr(monitor, "collect_remote_gate_proof", collect_once)
    anchor = {
        "endpoint": monitor.TSA_URL,
        "policy_oid": monitor.TSA_POLICY_OID,
        "response_bytes": len(response),
        "response_sha256": _sha256_bytes(response),
        "signed_gen_time": "2026-08-10T06:00:01Z",
        "monitor_started_at": "2026-08-10T06:00:01Z",
    }

    def post_once(query: bytes, response_fd: int) -> dict[str, object]:
        nonlocal attempts
        attempts += 1
        assert query == b"round45-fixed-query"
        assert os.write(response_fd, response) == len(response)
        return {
            "http_status": 200,
            "content_type": "application/timestamp-reply",
            "response_bytes": len(response),
            "redirect_count": 0,
            "request_count": 1,
            "retry_count": 0,
            "proxy_used": False,
        }

    monkeypatch.setattr(monitor, "_post_anchor_once", post_once)
    monkeypatch.setattr(
        monitor,
        "_verify_anchor",
        lambda **_kwargs: copy.deepcopy(anchor),
    )
    def launch() -> dict[str, object]:
        return monitor.start_form4_monitor(
            repository_root=repository,
            authorization_path=authorization_path,
            private_root=private_root,
        )

    first = launch()
    assert first["status"] == "monitor_started_collection_locked"
    assert first["state_boundary"] == monitor.STATE_BOUNDARY
    assert first["permission"] == monitor.PERMISSION
    assert first["today_action"] == "今天不下單"
    assert attempts == 1
    assert remote_calls == 1

    namespace = private_root / monitor.AUTHORIZATION_ID
    before = {
        path.relative_to(namespace).as_posix(): (path.read_bytes(), path.stat().st_mtime_ns)
        for path in namespace.iterdir()
        if path.is_file()
    }
    second = launch()
    after = {
        path.relative_to(namespace).as_posix(): (path.read_bytes(), path.stat().st_mtime_ns)
        for path in namespace.iterdir()
        if path.is_file()
    }
    assert second == first
    assert after == before
    assert attempts == 1
    assert remote_calls == 1
    assert {path.name for path in namespace.iterdir()} == set(monitor.NAMESPACE_FILES)

    authorization_path.write_bytes(b"synthetic round45 authorization with byte drift\n")
    assert _error_code(launch) == monitor.STABLE_CODES["start_receipt"]
    assert attempts == 1
    assert remote_calls == 1


def test_concurrent_callers_create_one_start_and_one_tsa_response(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository, authorization_path, private_root = _start_paths(tmp_path)
    _, remote_proof = _install_start_fixtures(monkeypatch, private_root)
    response = b"\x30\x00"
    counter_lock = threading.Lock()
    second_lock_entry = threading.Event()
    attempts = 0
    remote_calls = 0
    lock_entries = 0

    original_open_lock = monitor._open_lock

    def observed_open_lock(root_fd: int) -> int:
        nonlocal lock_entries
        with counter_lock:
            lock_entries += 1
            if lock_entries == 2:
                second_lock_entry.set()
        return original_open_lock(root_fd)

    def collect_once(*_args: object, **_kwargs: object) -> dict[str, object]:
        nonlocal remote_calls
        with counter_lock:
            remote_calls += 1
        return copy.deepcopy(remote_proof)

    def post_once(_query: bytes, response_fd: int) -> dict[str, object]:
        nonlocal attempts
        with counter_lock:
            attempts += 1
        assert second_lock_entry.wait(timeout=5)
        assert os.write(response_fd, response) == len(response)
        return {
            "http_status": 200,
            "content_type": "application/timestamp-reply",
            "response_bytes": len(response),
            "redirect_count": 0,
            "request_count": 1,
            "retry_count": 0,
            "proxy_used": False,
        }

    anchor = {
        "endpoint": monitor.TSA_URL,
        "policy_oid": monitor.TSA_POLICY_OID,
        "response_bytes": len(response),
        "response_sha256": _sha256_bytes(response),
        "signed_gen_time": "2026-08-10T06:00:01Z",
        "monitor_started_at": "2026-08-10T06:00:01Z",
    }
    monkeypatch.setattr(monitor, "_open_lock", observed_open_lock)
    monkeypatch.setattr(monitor, "collect_remote_gate_proof", collect_once)
    monkeypatch.setattr(monitor, "_post_anchor_once", post_once)
    monkeypatch.setattr(monitor, "_verify_anchor", lambda **_kwargs: copy.deepcopy(anchor))

    def launch() -> dict[str, object]:
        return monitor.start_form4_monitor(
            repository_root=repository,
            authorization_path=authorization_path,
            private_root=private_root,
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(launch) for _ in range(2)]
        receipts = [future.result(timeout=10) for future in futures]

    assert receipts[0] == receipts[1]
    assert attempts == 1
    assert remote_calls == 1
    assert lock_entries == 2
