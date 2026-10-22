from __future__ import annotations

import base64
import fcntl
import hashlib
import json
import os
import platform
import plistlib
import pwd
import re
import stat
import subprocess
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import quote

from .form4_prospective_trust_root import validate_predata_authorization

AUTHORIZATION_SCHEMA = "us_fddk.short_term_form4_monitor_start_authorization.v1"
START_SCHEMA = "us_fddk.short_term_form4_monitor_start.v1"
AUTHORIZATION_ID = "round45-form4-monitor-start-v1"
AUTHORIZATION_FROZEN_AT = "2026-08-10T08:14:58Z"
ROUND44_COMMIT = "f599816da099dff75a8a4a60ad21d07ecacb0359"
ROUND44_RECEIPT_PATH = (
    "artifacts/short_term_form4_prospective_trust_root_protocol_receipt.json"
)
START_AUTHORIZATION_PATH = (
    "artifacts/short_term_form4_monitor_start_authorization_receipt.json"
)
REPOSITORY = "voidful/us_fddk"
REPOSITORY_ID = 1321032410
GITHUB_HOSTNAME = "github.com"
REMOTE_URL = "https://github.com/voidful/us_fddk.git"
BRANCH = "codex/round45-form4-monitor-start"
PARENT_BRANCH = "codex/round44-form4-trust-root"
ROUND44_RUN_ID = 31358886821
ROUND44_JOB_ID = 93363646562
ROUND44_PR_NUMBER = 8
ROUND44_PR_ID = 4242016813
ROUND44_PR_BASE_BRANCH = "codex/round43-form4-multipath"
ROUND44_PR_BASE_COMMIT = "d42b444651a3ccde0f26882c803b58f0daf386a2"
GITHUB_ACTIONS_APP_ID = 15368
GITHUB_ACTIONS_APP_SLUG = "github-actions"
GITHUB_ACTIONS_APP_OWNER = "github"
ROUND44_WORKFLOW_NAME = "Form 4 Round44 pre-data CI"
ROUND44_WORKFLOW_PATH = ".github/workflows/form4-round44-predata-ci.yml"
ROUND44_JOB_NAME = "predata"
ROUND45_WORKFLOW_NAME = "Form 4 Round45 monitor-start CI"
ROUND45_WORKFLOW_PATH = ".github/workflows/form4-round45-monitor-start-ci.yml"
ROUND45_JOB_NAME = "monitor-start"

TSA_URL = "http://timestamp.digicert.com"
TSA_POLICY_OID = "2.16.840.1.114412.7.1"
TSA_RESPONDER_FINGERPRINT = (
    "4aa03fa22cd75c84c55c938f828e676b9caecab33fe36d269aa334f146110a33"
)
TSA_INTERMEDIATE_FINGERPRINT = (
    "ca0b1554ecd901ea19dcad8749e9f2648c8d6dfcea1add9d2c2109415bb82ccd"
)
TSA_ROOT_FINGERPRINT = (
    "552f7bdcf1a7af9e6ce672017f4f12abf77240c78e761ac203d1d9d20ac89988"
)
TSA_RESPONDER_SERIAL = "0a80ef184b8df10582d1c476a7957468"
PRIVATE_PARENT_PATH_SHA256 = (
    "98cd2c917f668882aaca3bbab9186a804fdbf90386e232bcd0abb26755d479bf"
)
PRIVATE_ROOT_PATH_SHA256 = (
    "60ce955e35899ab1851b4c8864f06c9bbcde5952a422276b39575f1d8685aa3e"
)
ROOT_CERT_PATH = "assets/digicert_trusted_root_g4.pem"
INTERMEDIATE_CERT_PATH = (
    "assets/digicert_trusted_g4_timestamping_rsa4096_sha256_2025_ca1.pem"
)
RESPONDER_CERT_PATH = (
    "assets/digicert_sha256_rsa4096_timestamp_responder_2025_1.pem"
)

ZERO_SHA256 = "0" * 64
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
ACCESSION_RE = re.compile(r"(?<!\d)\d{10}-\d{2}-\d{6}(?!\d)")

STABLE_CODES = {
    "authorization": "form4_round44_authorization_invalid",
    "remote_gate": "form4_round44_remote_gate_invalid",
    "private_boundary": "form4_round44_private_boundary_invalid",
    "start_receipt": "form4_round44_start_receipt_invalid",
    "already_started": "form4_round44_already_started",
    "request_plan": "form4_round44_request_plan_drifted",
    "attempt_ledger": "form4_round44_attempt_ledger_invalid",
    "external_anchor": "form4_round44_external_anchor_invalid",
    "live_network": "sec_live_network_authorization_missing",
    "public_boundary": "form4_round44_public_boundary_breached",
    "congress": "form4_forward_congress_field_injection",
    "non_engineering": "form4_forward_non_engineering_action_forbidden",
}

BINDING_PATHS = {
    "actor_dynamic_selection_design": (
        "docs/SHORT_TERM_ACTOR_DISCLOSURE_DYNAMIC_SELECTION_DESIGN.md"
    ),
    "dependency_lock": "uv.lock",
    "global_trial_ledger": "artifacts/short_term_global_trial_ledger.json",
    "global_trial_ledger_protocol": "docs/SHORT_TERM_GLOBAL_TRIAL_LEDGER_PROTOCOL.md",
    "monitor_start_implementation": "usfddk/form4_monitor_start.py",
    "offline_tsa_fixture_certificate": (
        "tests/fixtures/form4_round45_offline_tsa/tsa.crt"
    ),
    "offline_tsa_fixture_query": (
        "tests/fixtures/form4_round45_offline_tsa/query.tsq.b64"
    ),
    "offline_tsa_fixture_response": (
        "tests/fixtures/form4_round45_offline_tsa/response.tsr.b64"
    ),
    "monitor_start_protocol": "docs/SHORT_TERM_FORM4_MONITOR_START_PROTOCOL.md",
    "monitor_start_tests": "tests/test_form4_monitor_start.py",
    "monitor_start_workflow": ROUND45_WORKFLOW_PATH,
    "project_metadata": "pyproject.toml",
    "round44_predata_receipt": ROUND44_RECEIPT_PATH,
    "round44_predata_protocol": (
        "docs/SHORT_TERM_FORM4_PROSPECTIVE_TRUST_ROOT_PROTOCOL.md"
    ),
    "round44_predata_verifier": "usfddk/form4_prospective_trust_root.py",
    "round44_predata_workflow": ROUND44_WORKFLOW_PATH,
    "tsa_intermediate_cert": INTERMEDIATE_CERT_PATH,
    "tsa_responder_cert": RESPONDER_CERT_PATH,
    "tsa_root_cert": ROOT_CERT_PATH,
}
BINDING_KEYS = frozenset(BINDING_PATHS)

TOOL_CONTRACT = {
    "curl": {
        "path": "/usr/bin/curl",
        "sha256": "5ab042572ea0e068644e3b8f9e8dd1ad197bfcf33d199316615b46ddc4390a41",
    },
    "df": {
        "path": "/bin/df",
        "sha256": "f57b43da7cc2f701db5ebad1b78ae9a30f10f9a102b2a83b0707031e69367e8a",
    },
    "diskutil": {
        "path": "/usr/sbin/diskutil",
        "sha256": "9e30fe2a9b00bdc054fefecfe2f0be478e6166101b106c12c4b5168a777f1f93",
    },
    "fdesetup": {
        "path": "/usr/bin/fdesetup",
        "sha256": "db78286c33a7db9eb04c9cd94e06d1c756c13cc252d865b1cd15bac471cdfae6",
    },
    "gh": {
        "path": "/opt/homebrew/bin/gh",
        "sha256": "b9c11684efeff0557ce4f7fe23fe358e0c05568b8115058ee2e17ac94bd4d886",
    },
    "git": {
        "path": "/usr/bin/git",
        "sha256": "179301dcb41ea78accc3fa0048a7e6f6710d891945a751a34addd622020c1818",
    },
    "ls": {
        "path": "/bin/ls",
        "sha256": "a97c50d34f912a5ada66959c231897ec2144e3c9cb922cd8150e4f2b0c9470e7",
    },
    "openssl": {
        "path": "/opt/homebrew/bin/openssl",
        "sha256": "bf63843e6856e1994ca71092ff3b46834236eb2144dd9b6ceb85d511128b836e",
    },
    "xattr": {
        "path": "/usr/bin/xattr",
        "sha256": "3cc7308e9dfd687b0b7f4778a6101633aa9dce5ccdd012cf17cd858848295162",
    },
}

REMOTE_CONTRACT = {
    "repository": REPOSITORY,
    "repository_id": REPOSITORY_ID,
    "github_hostname": GITHUB_HOSTNAME,
    "remote_url": REMOTE_URL,
    "branch": BRANCH,
    "parent_branch": PARENT_BRANCH,
    "parent_commit": ROUND44_COMMIT,
    "parent_run_id": ROUND44_RUN_ID,
    "parent_job_id": ROUND44_JOB_ID,
    "parent_workflow_name": ROUND44_WORKFLOW_NAME,
    "parent_workflow_path": ROUND44_WORKFLOW_PATH,
    "parent_job_name": ROUND44_JOB_NAME,
    "current_workflow_name": ROUND45_WORKFLOW_NAME,
    "current_workflow_path": ROUND45_WORKFLOW_PATH,
    "current_job_name": ROUND45_JOB_NAME,
    "current_run_candidate_universe": "pinned_workflow_endpoint_all_runs",
    "current_run_query_filters": [],
    "current_run_selection": "exact_head_then_max_run_id_attempt",
    "current_run_exact_get_before_semantic_validation": True,
    "event": "pull_request",
    "same_repository_pr_required": True,
    "draft_pr_required": True,
    "github_actions_app_id": GITHUB_ACTIONS_APP_ID,
    "github_actions_app_slug": GITHUB_ACTIONS_APP_SLUG,
    "github_actions_app_owner": GITHUB_ACTIONS_APP_OWNER,
    "completed_status": "completed",
    "success_conclusion": "success",
}

TSA_CONTRACT = {
    "endpoint": TSA_URL,
    "message_imprint_algorithm": "sha256",
    "policy_oid": TSA_POLICY_OID,
    "cert_req": True,
    "random_nonce_required": True,
    "requests_exact": 1,
    "automatic_retries": 0,
    "redirects": 0,
    "proxy_allowed": False,
    "fallback_allowed": False,
    "pki_status_allowed": [0],
    "response_content_type": "application/timestamp-reply",
    "response_bytes_max": 1_048_576,
    "responder_fingerprint_sha256": TSA_RESPONDER_FINGERPRINT,
    "intermediate_fingerprint_sha256": TSA_INTERMEDIATE_FINGERPRINT,
    "root_fingerprint_sha256": TSA_ROOT_FINGERPRINT,
    "responder_serial_hex": TSA_RESPONDER_SERIAL,
    "monitor_started_at_basis": "signed_gen_time_plus_accuracy_upper_bound",
    "accuracy_required": True,
    "revocation_checked": False,
    "long_term_validation": False,
}

PRIVATE_CONTRACT = {
    "private_parent_path_sha256": PRIVATE_PARENT_PATH_SHA256,
    "private_root_path_sha256": PRIVATE_ROOT_PATH_SHA256,
    "repository_external": True,
    "direct_parent_owner_only": True,
    "directory_mode": "0700",
    "file_mode": "0600",
    "regular_file_link_count": 1,
    "symlink_allowed": False,
    "acl_allowed": False,
    "immutable_flags_allowed": False,
    "filevault_required": True,
    "volume_encryption_required": True,
    "parent_directory_fsync_required": True,
    "partial_state_recovery_allowed": False,
    "cold_replay_after_complete_tsr_only": False,
}

STATE_BOUNDARY = {
    "sec_request_count": 0,
    "tsa_request_count_before_start": 0,
    "real_identifier_count": 0,
    "real_filing_count": 0,
    "candidate_selection_count": 0,
    "candidate_allocation_count": 0,
    "strategy_run_count": 0,
    "performance_result_present": False,
    "paper_authorized": False,
    "real_money_action_usd": 0,
    "congress_request_count": 0,
    "congress_row_count": 0,
    "congress_field_count": 0,
}

PERMISSION = {
    "monitor_start_creation": True,
    "sec_network_collection": False,
    "prospective_collector_implemented": False,
    "sec_collection_capability_issued": False,
    "candidate_selection": False,
    "candidate_allocation": False,
    "strategy_run": False,
    "performance_readout": False,
    "paper": False,
    "real_money": False,
    "congress_collection": False,
}

AUTHORIZATION_KEYS = frozenset(
    {
        "schema_version",
        "research_round",
        "authorization_id",
        "phase",
        "status",
        "frozen_at",
        "parent_commit",
        "bindings",
        "tool_contract",
        "remote_contract",
        "tsa_contract",
        "private_contract",
        "state_boundary",
        "permission",
        "today_action",
        "receipt_sha256",
    }
)

LEDGER_KINDS = (
    "sec_attempt",
    "response_receipt",
    "object",
    "official_manifest",
    "first_seen_registry",
    "audit",
)
LEDGER_FILENAMES = {kind: f"{kind}_ledger.jsonl" for kind in LEDGER_KINDS}

NAMESPACE_FILES = frozenset(
    {
        *LEDGER_FILENAMES.values(),
        "account_zero_state.json",
        "volume_attestation.json",
        "remote_gate_proof.json",
        "start_intent.json",
        "anchor_request.tsq",
        "anchor_response.tsr",
        "anchor_exchange.json",
        "monitor_state.json",
        "monitor_start_receipt.json",
        "objects",
    }
)


class Form4MonitorStartError(RuntimeError):
    def __init__(self, code: str, detail: str):
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}")


def _fail(code: str, detail: str) -> None:
    raise Form4MonitorStartError(code, detail)


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_file(
    path: Path,
    *,
    code: str = STABLE_CODES["authorization"],
) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            while chunk := handle.read(1024 * 1024):
                digest.update(chunk)
    except OSError as exc:
        _fail(code, f"file unreadable: {type(exc).__name__}")
    return digest.hexdigest()


def _canonical_bytes(payload: Mapping[str, Any], *, omit: str | None = None) -> bytes:
    core = {key: value for key, value in payload.items() if key != omit}
    try:
        return json.dumps(
            core,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        _fail(STABLE_CODES["authorization"], f"non-canonical JSON: {type(exc).__name__}")


def canonical_sha256(payload: Mapping[str, Any], *, omit: str | None = None) -> str:
    return _sha256_bytes(_canonical_bytes(payload, omit=omit))


def _pretty_json_bytes(payload: Mapping[str, Any]) -> bytes:
    try:
        return (
            json.dumps(
                payload,
                ensure_ascii=False,
                sort_keys=True,
                indent=2,
                allow_nan=False,
            )
            + "\n"
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        _fail(STABLE_CODES["start_receipt"], f"private JSON invalid: {type(exc).__name__}")


def _reject_duplicate_keys(
    pairs: list[tuple[str, Any]],
    *,
    code: str = STABLE_CODES["authorization"],
) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            _fail(code, f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _load_exact_json_bytes(value: bytes, *, code: str) -> object:
    try:
        return json.loads(
            value,
            object_pairs_hook=lambda pairs: _reject_duplicate_keys(pairs, code=code),
            parse_constant=lambda constant: _fail(code, f"JSON constant forbidden: {constant}"),
        )
    except UnicodeDecodeError as exc:
        _fail(code, f"JSON is not UTF-8: {type(exc).__name__}")
    except json.JSONDecodeError as exc:
        _fail(code, f"JSON invalid: {type(exc).__name__}")


def _typed_equal(actual: object, expected: object) -> bool:
    if type(actual) is not type(expected):
        return False
    if isinstance(expected, dict):
        actual_dict = actual
        return set(actual_dict) == set(expected) and all(  # type: ignore[arg-type]
            _typed_equal(actual_dict[key], value)  # type: ignore[index]
            for key, value in expected.items()
        )
    if isinstance(expected, list):
        actual_list = actual
        return len(actual_list) == len(expected) and all(  # type: ignore[arg-type]
            _typed_equal(left, right)
            for left, right in zip(actual_list, expected, strict=True)  # type: ignore[arg-type]
        )
    return actual == expected


def _canonical_utc(value: object) -> datetime | None:
    if not isinstance(value, str) or not value.endswith("Z"):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.utcoffset() is None:
        return None
    canonical = parsed.astimezone(UTC).isoformat().replace("+00:00", "Z")
    return parsed.astimezone(UTC) if canonical == value else None


def _head_blob_bytes(root: Path, relative: str, *, code: str) -> bytes:
    if not relative or relative.startswith("/") or ".." in Path(relative).parts:
        _fail(code, "HEAD blob path is unsafe")
    listing = _run_ok(
        [TOOL_CONTRACT["git"]["path"], "ls-tree", "HEAD", "--", relative],
        cwd=root,
        code=code,
    )
    try:
        prefix, listed_path = listing.decode("utf-8", errors="strict").rstrip("\n").split(
            "\t", 1
        )
        mode, kind, object_id = prefix.split()
    except ValueError:
        _fail(code, "HEAD blob identity is missing or ambiguous")
    if (
        mode != "100644"
        or kind != "blob"
        or COMMIT_RE.fullmatch(object_id) is None
        or listed_path != relative
    ):
        _fail(code, "HEAD entry is not one exact regular blob")
    return _run_ok(
        [TOOL_CONTRACT["git"]["path"], "cat-file", "blob", object_id],
        cwd=root,
        code=code,
    )


def _validate_bindings(receipt: Mapping[str, Any], root: Path) -> None:
    bindings = receipt.get("bindings")
    if not isinstance(bindings, dict) or set(bindings) != BINDING_KEYS:
        _fail(STABLE_CODES["authorization"], "authorization bindings are incomplete")
    for name, binding in bindings.items():
        if not isinstance(binding, dict) or set(binding) != {"path", "sha256"}:
            _fail(STABLE_CODES["authorization"], f"binding {name} schema drifted")
        relative = binding.get("path")
        digest = binding.get("sha256")
        if (
            not isinstance(relative, str)
            or relative != BINDING_PATHS[name]
            or not isinstance(digest, str)
            or SHA256_RE.fullmatch(digest) is None
        ):
            _fail(STABLE_CODES["authorization"], f"binding {name} identity drifted")
        unresolved = root / relative
        try:
            metadata = unresolved.lstat()
        except OSError as exc:
            _fail(
                STABLE_CODES["authorization"],
                f"binding {name} unavailable: {type(exc).__name__}",
            )
        candidate = unresolved.resolve()
        try:
            candidate.relative_to(root)
        except ValueError:
            _fail(STABLE_CODES["authorization"], f"binding {name} escaped repository")
        if (
            not stat.S_ISREG(metadata.st_mode)
            or unresolved.is_symlink()
            or not candidate.is_file()
            or _sha256_file(candidate) != digest
        ):
            _fail(STABLE_CODES["authorization"], f"binding {name} bytes drifted")
        head_bytes = _head_blob_bytes(
            root,
            relative,
            code=STABLE_CODES["authorization"],
        )
        if head_bytes != candidate.read_bytes() or _sha256_bytes(head_bytes) != digest:
            _fail(STABLE_CODES["authorization"], f"binding {name} HEAD blob drifted")


def validate_monitor_start_authorization(
    authorization_path: str | Path,
    *,
    repository_root: str | Path,
) -> dict[str, Any]:
    root = Path(repository_root).resolve()
    _validate_repository_identity(root)
    path = Path(authorization_path).resolve()
    expected_path = (root / START_AUTHORIZATION_PATH).resolve()
    if path != expected_path:
        _fail(STABLE_CODES["authorization"], "authorization path drifted")
    try:
        path.relative_to(root)
    except ValueError:
        _fail(STABLE_CODES["authorization"], "authorization must be inside repository")
    try:
        raw = path.read_bytes()
    except OSError as exc:
        _fail(STABLE_CODES["authorization"], f"authorization unreadable: {type(exc).__name__}")
    value = _load_exact_json_bytes(raw, code=STABLE_CODES["authorization"])
    if not isinstance(value, dict):
        _fail(STABLE_CODES["authorization"], "authorization root is not an object")
    if _head_blob_bytes(
        root,
        START_AUTHORIZATION_PATH,
        code=STABLE_CODES["authorization"],
    ) != raw:
        _fail(STABLE_CODES["authorization"], "authorization HEAD blob drifted")
    receipt = value
    if (
        set(receipt) != AUTHORIZATION_KEYS
        or receipt.get("schema_version") != AUTHORIZATION_SCHEMA
        or type(receipt.get("research_round")) is not int
        or receipt.get("research_round") != 45
        or receipt.get("authorization_id") != AUTHORIZATION_ID
        or receipt.get("phase") != "monitor_start_authorization"
        or receipt.get("status") != "frozen_remote_exact_head_required"
        or receipt.get("frozen_at") != AUTHORIZATION_FROZEN_AT
        or _canonical_utc(receipt.get("frozen_at")) is None
        or receipt.get("parent_commit") != ROUND44_COMMIT
        or not _typed_equal(receipt.get("tool_contract"), TOOL_CONTRACT)
        or not _typed_equal(receipt.get("remote_contract"), REMOTE_CONTRACT)
        or not _typed_equal(receipt.get("tsa_contract"), TSA_CONTRACT)
        or not _typed_equal(receipt.get("private_contract"), PRIVATE_CONTRACT)
        or not _typed_equal(receipt.get("state_boundary"), STATE_BOUNDARY)
        or not _typed_equal(receipt.get("permission"), PERMISSION)
        or receipt.get("today_action") != "今天不下單"
        or receipt.get("receipt_sha256")
        != canonical_sha256(receipt, omit="receipt_sha256")
    ):
        _fail(STABLE_CODES["authorization"], "authorization content drifted")
    _validate_bindings(receipt, root)
    validate_predata_authorization(root / ROUND44_RECEIPT_PATH, repository_root=root)
    ancestry = _run_process(
        [TOOL_CONTRACT["git"]["path"], "merge-base", "--is-ancestor", ROUND44_COMMIT, "HEAD"],
        cwd=root,
        code=STABLE_CODES["authorization"],
    )
    if ancestry.returncode != 0:
        _fail(STABLE_CODES["authorization"], "Round44 is not an ancestor of HEAD")
    return receipt


def _run_process(
    args: Sequence[str],
    *,
    cwd: Path | None = None,
    input_bytes: bytes | None = None,
    pass_fds: tuple[int, ...] = (),
    code: str,
    timeout: int = 30,
    env: Mapping[str, str] | None = None,
) -> subprocess.CompletedProcess[bytes]:
    effective_env = dict(env) if env is not None else None
    if args and args[0] == TOOL_CONTRACT["openssl"]["path"]:
        effective_env = {
            "LANG": "C",
            "LC_ALL": "C",
            "OPENSSL_CONF": "/dev/null",
        }
    elif args and args[0] == TOOL_CONTRACT["git"]["path"]:
        effective_env = {
            "GIT_CONFIG_GLOBAL": "/dev/null",
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_TERMINAL_PROMPT": "0",
            "LANG": "C",
            "LC_ALL": "C",
        }
    elif args and args[0] == TOOL_CONTRACT["gh"]["path"]:
        source = dict(os.environ) if effective_env is None else effective_env
        effective_env = {
            "GH_PAGER": "cat",
            "HOME": pwd.getpwuid(os.getuid()).pw_dir,
            "LANG": "C",
            "LC_ALL": "C",
        }
        for key in ("GH_TOKEN", "GITHUB_TOKEN"):
            if key in source:
                effective_env[key] = source[key]
    try:
        return subprocess.run(
            list(args),
            cwd=cwd,
            input=input_bytes,
            capture_output=True,
            check=False,
            timeout=timeout,
            pass_fds=pass_fds,
            env=effective_env,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        _fail(code, f"command failed: {type(exc).__name__}")


def _run_ok(
    args: Sequence[str],
    *,
    cwd: Path | None = None,
    input_bytes: bytes | None = None,
    pass_fds: tuple[int, ...] = (),
    code: str,
    timeout: int = 30,
    env: Mapping[str, str] | None = None,
) -> bytes:
    completed = _run_process(
        args,
        cwd=cwd,
        input_bytes=input_bytes,
        pass_fds=pass_fds,
        code=code,
        timeout=timeout,
        env=env,
    )
    if completed.returncode != 0:
        _fail(code, "fixed command returned nonzero")
    return completed.stdout


def _validate_repository_identity(root: Path) -> None:
    top = _run_ok(
        [TOOL_CONTRACT["git"]["path"], "rev-parse", "--show-toplevel"],
        cwd=root,
        code=STABLE_CODES["authorization"],
    ).decode("utf-8", errors="strict").strip()
    inside = _run_ok(
        [TOOL_CONTRACT["git"]["path"], "rev-parse", "--is-inside-work-tree"],
        cwd=root,
        code=STABLE_CODES["authorization"],
    )
    if top != str(root) or inside != b"true\n":
        _fail(STABLE_CODES["authorization"], "repository root identity drifted")


def _validate_tool_contract() -> None:
    for name, contract in TOOL_CONTRACT.items():
        path = Path(contract["path"])
        try:
            metadata = path.stat()
        except OSError as exc:
            _fail(STABLE_CODES["request_plan"], f"tool {name} unavailable: {type(exc).__name__}")
        if (
            not stat.S_ISREG(metadata.st_mode)
            or metadata.st_nlink < 1
            or not os.access(path, os.X_OK)
            or _sha256_file(path, code=STABLE_CODES["request_plan"])
            != contract["sha256"]
        ):
            _fail(STABLE_CODES["request_plan"], f"tool {name} drifted")


def _gh_api(endpoint: str, *, root: Path) -> tuple[dict[str, Any] | list[Any], str]:
    raw = _run_ok(
        [
            TOOL_CONTRACT["gh"]["path"],
            "api",
            "--hostname",
            GITHUB_HOSTNAME,
            "--method",
            "GET",
            "--header",
            "Accept: application/vnd.github+json",
            "--header",
            "X-GitHub-Api-Version: 2022-11-28",
            endpoint,
        ],
        cwd=root,
        code=STABLE_CODES["remote_gate"],
        timeout=30,
    )
    value = _load_exact_json_bytes(raw, code=STABLE_CODES["remote_gate"])
    if not isinstance(value, (dict, list)):
        _fail(STABLE_CODES["remote_gate"], "GitHub response root drifted")
    return value, _sha256_bytes(raw)


def _exact_string(value: object, expected: str, detail: str) -> str:
    if not isinstance(value, str) or value != expected:
        _fail(STABLE_CODES["remote_gate"], detail)
    return value


def _exact_int(value: object, expected: int | None, detail: str) -> int:
    if (
        type(value) is not int
        or value < 1
        or (expected is not None and value != expected)
    ):
        _fail(STABLE_CODES["remote_gate"], detail)
    return value


def _validate_run(
    run: Mapping[str, Any],
    *,
    head: str,
    branch: str,
    workflow_name: str,
    workflow_path: str,
    pull_request_number: int,
    pull_request_id: int,
    base_branch: str,
    base_sha: str,
    run_id: int | None = None,
) -> dict[str, Any]:
    actual_id = _exact_int(run.get("id"), run_id, "workflow run id drifted")
    _exact_string(run.get("name"), workflow_name, "workflow name drifted")
    _exact_string(run.get("path"), workflow_path, "workflow path drifted")
    _exact_string(run.get("event"), "pull_request", "workflow event drifted")
    _exact_string(run.get("head_sha"), head, "workflow head drifted")
    _exact_string(run.get("head_branch"), branch, "workflow branch drifted")
    _exact_string(run.get("status"), "completed", "workflow is not completed")
    _exact_string(run.get("conclusion"), "success", "workflow did not succeed")
    attempt = _exact_int(run.get("run_attempt"), None, "workflow attempt is invalid")
    if attempt < 1:
        _fail(STABLE_CODES["remote_gate"], "workflow attempt is invalid")
    created = run.get("created_at")
    updated = run.get("updated_at")
    if _canonical_utc(created) is None or _canonical_utc(updated) is None:
        _fail(STABLE_CODES["remote_gate"], "workflow timestamps drifted")
    pull_requests = run.get("pull_requests")
    if not isinstance(pull_requests, list):
        _fail(STABLE_CODES["remote_gate"], "workflow pull-request link missing")
    linked = []
    for pull in pull_requests:
        if not isinstance(pull, dict):
            continue
        pull_head = pull.get("head")
        pull_base = pull.get("base")
        head_repo = pull_head.get("repo") if isinstance(pull_head, dict) else None
        base_repo = pull_base.get("repo") if isinstance(pull_base, dict) else None
        if (
            pull.get("number") == pull_request_number
            and pull.get("id") == pull_request_id
            and isinstance(pull_head, dict)
            and pull_head.get("ref") == branch
            and pull_head.get("sha") == head
            and isinstance(head_repo, dict)
            and head_repo.get("id") == REPOSITORY_ID
            and isinstance(pull_base, dict)
            and pull_base.get("ref") == base_branch
            and pull_base.get("sha") == base_sha
            and isinstance(base_repo, dict)
            and base_repo.get("id") == REPOSITORY_ID
        ):
            linked.append(pull)
    if len(linked) != 1:
        _fail(STABLE_CODES["remote_gate"], "workflow is not linked to exact pull request")
    expected_run_url = f"https://github.com/{REPOSITORY}/actions/runs/{actual_id}"
    expected_jobs_url = f"https://api.github.com/repos/{REPOSITORY}/actions/runs/{actual_id}/jobs"
    _exact_string(run.get("html_url"), expected_run_url, "workflow URL drifted")
    _exact_string(run.get("jobs_url"), expected_jobs_url, "workflow jobs URL drifted")
    return {
        "run_id": actual_id,
        "run_attempt": attempt,
        "workflow_name": workflow_name,
        "workflow_path": workflow_path,
        "event": "pull_request",
        "head_sha": head,
        "head_branch": branch,
        "status": "completed",
        "conclusion": "success",
        "created_at": created,
        "completed_at": updated,
        "pull_request_number": pull_request_number,
        "pull_request_id": pull_request_id,
    }


def _validate_job_and_check(
    *,
    jobs_payload: Mapping[str, Any],
    checks_payload: Mapping[str, Any],
    run_id: int,
    run_attempt: int,
    head: str,
    workflow_name: str,
    job_name: str,
    expected_job_id: int | None,
) -> dict[str, Any]:
    jobs = jobs_payload.get("jobs")
    if not isinstance(jobs, list):
        _fail(STABLE_CODES["remote_gate"], "jobs response drifted")
    matches = [
        job
        for job in jobs
        if isinstance(job, dict)
        and job.get("name") == job_name
        and (expected_job_id is None or job.get("id") == expected_job_id)
    ]
    if len(matches) != 1:
        _fail(STABLE_CODES["remote_gate"], "required job is not unique")
    job = matches[0]
    job_id = _exact_int(job.get("id"), expected_job_id, "job id drifted")
    _exact_int(job.get("run_id"), run_id, "job run id drifted")
    _exact_int(job.get("run_attempt"), run_attempt, "job run attempt drifted")
    _exact_string(job.get("workflow_name"), workflow_name, "job workflow drifted")
    _exact_string(job.get("head_sha"), head, "job head drifted")
    _exact_string(job.get("status"), "completed", "job is not completed")
    _exact_string(job.get("conclusion"), "success", "job did not succeed")
    completed_at = job.get("completed_at")
    started_at = job.get("started_at")
    if _canonical_utc(completed_at) is None or _canonical_utc(started_at) is None:
        _fail(STABLE_CODES["remote_gate"], "job timestamps drifted")
    expected_job_url = f"https://github.com/{REPOSITORY}/actions/runs/{run_id}/job/{job_id}"
    expected_check_url = f"https://api.github.com/repos/{REPOSITORY}/check-runs/{job_id}"
    _exact_string(job.get("html_url"), expected_job_url, "job URL drifted")
    _exact_string(job.get("check_run_url"), expected_check_url, "job check URL drifted")

    checks = checks_payload.get("check_runs")
    if not isinstance(checks, list):
        _fail(STABLE_CODES["remote_gate"], "checks response drifted")
    check_matches = [
        check
        for check in checks
        if isinstance(check, dict)
        and check.get("id") == job_id
        and check.get("name") == job_name
    ]
    if len(check_matches) != 1:
        _fail(STABLE_CODES["remote_gate"], "required check is not unique")
    check = check_matches[0]
    _exact_string(check.get("head_sha"), head, "check head drifted")
    _exact_string(check.get("status"), "completed", "check is not completed")
    _exact_string(check.get("conclusion"), "success", "check did not succeed")
    _exact_string(check.get("started_at"), str(started_at), "check start time drifted")
    _exact_string(check.get("completed_at"), str(completed_at), "check completion time drifted")
    app = check.get("app")
    if not isinstance(app, dict):
        _fail(STABLE_CODES["remote_gate"], "check app missing")
    _exact_int(app.get("id"), GITHUB_ACTIONS_APP_ID, "check app id drifted")
    _exact_string(app.get("slug"), GITHUB_ACTIONS_APP_SLUG, "check app slug drifted")
    owner = app.get("owner")
    if not isinstance(owner, dict):
        _fail(STABLE_CODES["remote_gate"], "check app owner missing")
    _exact_string(owner.get("login"), GITHUB_ACTIONS_APP_OWNER, "check app owner drifted")
    _exact_string(
        check.get("details_url"),
        expected_job_url,
        "check does not belong to required run",
    )
    return {
        "job": {
            "job_id": job_id,
            "run_id": run_id,
            "run_attempt": run_attempt,
            "workflow_name": workflow_name,
            "job_name": job_name,
            "head_sha": head,
            "status": "completed",
            "conclusion": "success",
            "started_at": started_at,
            "completed_at": completed_at,
            "html_url": expected_job_url,
            "check_run_url": expected_check_url,
        },
        "check": {
            "check_id": job_id,
            "check_name": job_name,
            "head_sha": head,
            "check_app_id": GITHUB_ACTIONS_APP_ID,
            "check_app_slug": GITHUB_ACTIONS_APP_SLUG,
            "check_app_owner": GITHUB_ACTIONS_APP_OWNER,
            "status": "completed",
            "conclusion": "success",
            "started_at": started_at,
            "completed_at": completed_at,
            "details_url": expected_job_url,
        },
    }


def _remote_ref(root: Path, branch: str, head: str) -> tuple[dict[str, str], str]:
    value, raw_sha256 = _gh_api(
        f"repos/{REPOSITORY}/git/ref/heads/{quote(branch, safe='')}",
        root=root,
    )
    git_object = value.get("object") if isinstance(value, dict) else None
    if (
        not isinstance(value, dict)
        or value.get("ref") != f"refs/heads/{branch}"
        or not isinstance(git_object, dict)
        or git_object.get("type") != "commit"
        or git_object.get("sha") != head
        or git_object.get("url")
        != f"https://api.github.com/repos/{REPOSITORY}/git/commits/{head}"
    ):
        _fail(STABLE_CODES["remote_gate"], "remote branch head drifted")
    return {
        "ref": f"refs/heads/{branch}",
        "object_type": "commit",
        "sha": head,
    }, raw_sha256


def _collect_current_workflow_run_universe(
    root: Path,
) -> tuple[list[dict[str, Any]], list[str]]:
    workflow = Path(ROUND45_WORKFLOW_PATH).name
    collected: list[dict[str, Any]] = []
    raw_hashes: list[str] = []
    expected_total: int | None = None
    page = 1
    while True:
        value, raw_sha256 = _gh_api(
            f"repos/{REPOSITORY}/actions/workflows/{workflow}/runs"
            f"?per_page=100&page={page}",
            root=root,
        )
        raw_hashes.append(raw_sha256)
        if not isinstance(value, dict) or set(value) != {
            "total_count",
            "workflow_runs",
        }:
            _fail(STABLE_CODES["remote_gate"], "workflow runs response drifted")
        total_count = value.get("total_count")
        runs = value.get("workflow_runs")
        if (
            type(total_count) is not int
            or total_count < 0
            or not isinstance(runs, list)
            or len(runs) > 100
            or any(not isinstance(run, dict) for run in runs)
        ):
            _fail(STABLE_CODES["remote_gate"], "workflow runs page drifted")
        if expected_total is None:
            expected_total = total_count
        elif total_count != expected_total:
            _fail(STABLE_CODES["remote_gate"], "workflow run universe changed")
        if not runs and len(collected) != expected_total:
            _fail(STABLE_CODES["remote_gate"], "workflow run universe is incomplete")
        collected.extend(runs)
        if len(collected) > expected_total:
            _fail(STABLE_CODES["remote_gate"], "workflow run universe overcounted")
        if len(collected) == expected_total:
            break
        page += 1

    return collected, raw_hashes


def collect_remote_gate_proof(repository_root: str | Path) -> dict[str, Any]:
    root = Path(repository_root).resolve()
    _validate_tool_contract()
    _validate_repository_identity(root)
    status = _run_ok(
        [
            TOOL_CONTRACT["git"]["path"],
            "status",
            "--porcelain=v1",
            "--untracked-files=all",
        ],
        cwd=root,
        code=STABLE_CODES["authorization"],
    )
    if status:
        _fail(STABLE_CODES["authorization"], "launch worktree is not clean")
    origin = _run_ok(
        [TOOL_CONTRACT["git"]["path"], "remote", "get-url", "origin"],
        cwd=root,
        code=STABLE_CODES["remote_gate"],
    ).decode("utf-8", errors="strict").strip()
    if origin != REMOTE_URL:
        _fail(STABLE_CODES["remote_gate"], "origin URL drifted")
    head = _run_ok(
        [TOOL_CONTRACT["git"]["path"], "rev-parse", "HEAD"],
        cwd=root,
        code=STABLE_CODES["authorization"],
    ).decode("ascii").strip()
    if COMMIT_RE.fullmatch(head) is None:
        _fail(STABLE_CODES["authorization"], "HEAD is not a commit SHA")
    branch = _run_ok(
        [TOOL_CONTRACT["git"]["path"], "branch", "--show-current"],
        cwd=root,
        code=STABLE_CODES["authorization"],
    ).decode("utf-8").strip()
    if branch != BRANCH:
        _fail(STABLE_CODES["remote_gate"], "launch branch drifted")

    current_ref, current_ref_hash = _remote_ref(root, BRANCH, head)
    parent_ref, parent_ref_hash = _remote_ref(root, PARENT_BRANCH, ROUND44_COMMIT)
    raw_hashes: dict[str, Any] = {
        "current_ref_first": current_ref_hash,
        "parent_ref": parent_ref_hash,
    }
    encoded_branch = quote(BRANCH, safe="")
    pulls_value, raw_hashes["current_prs"] = _gh_api(
        f"repos/{REPOSITORY}/pulls?state=open&head=voidful:{encoded_branch}&per_page=100",
        root=root,
    )
    if not isinstance(pulls_value, list):
        _fail(STABLE_CODES["remote_gate"], "pull request response drifted")
    pull_matches = []
    for pull in pulls_value:
        if not isinstance(pull, dict):
            continue
        head_info = pull.get("head")
        base_info = pull.get("base")
        head_repo = head_info.get("repo") if isinstance(head_info, dict) else None
        base_repo = base_info.get("repo") if isinstance(base_info, dict) else None
        if (
            isinstance(head_info, dict)
            and isinstance(base_info, dict)
            and isinstance(head_repo, dict)
            and isinstance(base_repo, dict)
            and head_info.get("sha") == head
            and head_info.get("ref") == BRANCH
            and head_repo.get("full_name") == REPOSITORY
            and head_repo.get("id") == REPOSITORY_ID
            and base_info.get("ref") == PARENT_BRANCH
            and base_info.get("sha") == ROUND44_COMMIT
            and base_repo.get("full_name") == REPOSITORY
            and base_repo.get("id") == REPOSITORY_ID
            and pull.get("draft") is True
        ):
            pull_matches.append(pull)
    if len(pull_matches) != 1:
        _fail(STABLE_CODES["remote_gate"], "same-repository draft PR is not unique")
    pull = pull_matches[0]
    pull_number = _exact_int(pull.get("number"), None, "pull request number invalid")
    pull_id = _exact_int(pull.get("id"), None, "pull request id invalid")

    runs, raw_hashes["current_run_pages"] = _collect_current_workflow_run_universe(
        root
    )
    current_candidates = [
        run
        for run in runs
        if isinstance(run, dict)
        and run.get("head_sha") == head
    ]
    if not current_candidates:
        _fail(STABLE_CODES["remote_gate"], "current exact-head workflow success missing")
    identities: set[tuple[int, int]] = set()
    for candidate in current_candidates:
        candidate_id = candidate.get("id")
        candidate_attempt = candidate.get("run_attempt")
        if (
            type(candidate_id) is not int
            or candidate_id < 1
            or type(candidate_attempt) is not int
            or candidate_attempt < 1
            or (candidate_id, candidate_attempt) in identities
        ):
            _fail(STABLE_CODES["remote_gate"], "workflow candidate identity is invalid")
        identities.add((candidate_id, candidate_attempt))
    current_candidates.sort(
        key=lambda item: (item["id"], item["run_attempt"]),
        reverse=True,
    )
    selected_run = current_candidates[0]
    selected_run_id = selected_run["id"]
    selected_run_attempt = selected_run["run_attempt"]
    current_run_value, raw_hashes["current_run"] = _gh_api(
        f"repos/{REPOSITORY}/actions/runs/{selected_run_id}",
        root=root,
    )
    if not isinstance(current_run_value, dict):
        _fail(STABLE_CODES["remote_gate"], "current exact workflow run drifted")
    current_run = _validate_run(
        current_run_value,
        head=head,
        branch=BRANCH,
        workflow_name=ROUND45_WORKFLOW_NAME,
        workflow_path=ROUND45_WORKFLOW_PATH,
        pull_request_number=pull_number,
        pull_request_id=pull_id,
        base_branch=PARENT_BRANCH,
        base_sha=ROUND44_COMMIT,
        run_id=selected_run_id,
    )
    listed_run = _validate_run(
        selected_run,
        head=head,
        branch=BRANCH,
        workflow_name=ROUND45_WORKFLOW_NAME,
        workflow_path=ROUND45_WORKFLOW_PATH,
        pull_request_number=pull_number,
        pull_request_id=pull_id,
        base_branch=PARENT_BRANCH,
        base_sha=ROUND44_COMMIT,
        run_id=selected_run_id,
    )
    if (
        current_run["run_attempt"] != selected_run_attempt
        or not _typed_equal(current_run, listed_run)
    ):
        _fail(STABLE_CODES["remote_gate"], "listed and exact workflow run drifted")
    current_run_id = current_run["run_id"]
    current_jobs_value, raw_hashes["current_jobs"] = _gh_api(
        f"repos/{REPOSITORY}/actions/runs/{current_run_id}/jobs?filter=latest&per_page=100",
        root=root,
    )
    current_checks_value, raw_hashes["current_checks"] = _gh_api(
        f"repos/{REPOSITORY}/commits/{head}/check-runs?check_name={quote(ROUND45_JOB_NAME)}"
        "&filter=all&per_page=100",
        root=root,
    )
    if not isinstance(current_jobs_value, dict) or not isinstance(current_checks_value, dict):
        _fail(STABLE_CODES["remote_gate"], "current job/check response drifted")
    current_job = _validate_job_and_check(
        jobs_payload=current_jobs_value,
        checks_payload=current_checks_value,
        run_id=current_run_id,
        run_attempt=current_run["run_attempt"],
        head=head,
        workflow_name=ROUND45_WORKFLOW_NAME,
        job_name=ROUND45_JOB_NAME,
        expected_job_id=None,
    )

    parent_run_value, raw_hashes["parent_run"] = _gh_api(
        f"repos/{REPOSITORY}/actions/runs/{ROUND44_RUN_ID}", root=root
    )
    parent_jobs_value, raw_hashes["parent_jobs"] = _gh_api(
        f"repos/{REPOSITORY}/actions/runs/{ROUND44_RUN_ID}/jobs?filter=all&per_page=100",
        root=root,
    )
    parent_checks_value, raw_hashes["parent_checks"] = _gh_api(
        f"repos/{REPOSITORY}/commits/{ROUND44_COMMIT}/check-runs?check_name={ROUND44_JOB_NAME}"
        "&filter=all&per_page=100",
        root=root,
    )
    if not all(
        isinstance(value, dict)
        for value in (parent_run_value, parent_jobs_value, parent_checks_value)
    ):
        _fail(STABLE_CODES["remote_gate"], "parent run proof drifted")
    parent_run = _validate_run(
        parent_run_value,
        head=ROUND44_COMMIT,
        branch=PARENT_BRANCH,
        workflow_name=ROUND44_WORKFLOW_NAME,
        workflow_path=ROUND44_WORKFLOW_PATH,
        pull_request_number=ROUND44_PR_NUMBER,
        pull_request_id=ROUND44_PR_ID,
        base_branch=ROUND44_PR_BASE_BRANCH,
        base_sha=ROUND44_PR_BASE_COMMIT,
        run_id=ROUND44_RUN_ID,
    )
    parent_job = _validate_job_and_check(
        jobs_payload=parent_jobs_value,
        checks_payload=parent_checks_value,
        run_id=ROUND44_RUN_ID,
        run_attempt=parent_run["run_attempt"],
        head=ROUND44_COMMIT,
        workflow_name=ROUND44_WORKFLOW_NAME,
        job_name=ROUND44_JOB_NAME,
        expected_job_id=ROUND44_JOB_ID,
    )
    current_ref_last, raw_hashes["current_ref_last"] = _remote_ref(root, BRANCH, head)
    if (
        raw_hashes["current_ref_first"] != raw_hashes["current_ref_last"]
        or not _typed_equal(current_ref, current_ref_last)
    ):
        _fail(STABLE_CODES["remote_gate"], "remote head changed during proof")

    proof: dict[str, Any] = {
        "schema_version": "us_fddk.short_term_form4_remote_gate_proof.v1",
        "repository": REPOSITORY,
        "repository_id": REPOSITORY_ID,
        "branch": BRANCH,
        "authorization_commit": head,
        "pull_request_number": pull_number,
        "pull_request_id": pull_id,
        "pull_request_draft": True,
        "refs": {"current": current_ref, "parent": parent_ref},
        "parent": {"run": parent_run, **parent_job},
        "current": {"run": current_run, **current_job},
        "raw_response_sha256": raw_hashes,
        "proof_sha256": "",
    }
    proof["proof_sha256"] = canonical_sha256(proof, omit="proof_sha256")
    return proof


def _validate_stored_remote_side(
    value: object,
    *,
    head: str,
    branch: str,
    workflow_name: str,
    workflow_path: str,
    job_name: str,
    pull_request_number: int,
    pull_request_id: int,
    expected_run_id: int | None,
    expected_job_id: int | None,
) -> None:
    if not isinstance(value, dict) or set(value) != {"run", "job", "check"}:
        _fail(STABLE_CODES["remote_gate"], "stored remote side schema drifted")
    run = value["run"]
    job = value["job"]
    check = value["check"]
    run_keys = {
        "run_id",
        "run_attempt",
        "workflow_name",
        "workflow_path",
        "event",
        "head_sha",
        "head_branch",
        "status",
        "conclusion",
        "created_at",
        "completed_at",
        "pull_request_number",
        "pull_request_id",
    }
    job_keys = {
        "job_id",
        "run_id",
        "run_attempt",
        "workflow_name",
        "job_name",
        "head_sha",
        "status",
        "conclusion",
        "started_at",
        "completed_at",
        "html_url",
        "check_run_url",
    }
    check_keys = {
        "check_id",
        "check_name",
        "head_sha",
        "check_app_id",
        "check_app_slug",
        "check_app_owner",
        "status",
        "conclusion",
        "started_at",
        "completed_at",
        "details_url",
    }
    if (
        not isinstance(run, dict)
        or set(run) != run_keys
        or not isinstance(job, dict)
        or set(job) != job_keys
        or not isinstance(check, dict)
        or set(check) != check_keys
    ):
        _fail(STABLE_CODES["remote_gate"], "stored run/job/check schema drifted")
    run_id = run.get("run_id")
    job_id = job.get("job_id")
    run_attempt = run.get("run_attempt")
    if (
        type(run_id) is not int
        or run_id < 1
        or (expected_run_id is not None and run_id != expected_run_id)
        or type(job_id) is not int
        or job_id < 1
        or (expected_job_id is not None and job_id != expected_job_id)
        or type(run_attempt) is not int
        or run_attempt < 1
    ):
        _fail(STABLE_CODES["remote_gate"], "stored remote immutable id drifted")
    expected_run = {
        "workflow_name": workflow_name,
        "workflow_path": workflow_path,
        "event": "pull_request",
        "head_sha": head,
        "head_branch": branch,
        "status": "completed",
        "conclusion": "success",
        "pull_request_number": pull_request_number,
        "pull_request_id": pull_request_id,
    }
    if any(not _typed_equal(run.get(key), item) for key, item in expected_run.items()):
        _fail(STABLE_CODES["remote_gate"], "stored workflow identity drifted")
    expected_job_url = f"https://github.com/{REPOSITORY}/actions/runs/{run_id}/job/{job_id}"
    expected_check_url = f"https://api.github.com/repos/{REPOSITORY}/check-runs/{job_id}"
    expected_job = {
        "run_id": run_id,
        "run_attempt": run_attempt,
        "workflow_name": workflow_name,
        "job_name": job_name,
        "head_sha": head,
        "status": "completed",
        "conclusion": "success",
        "html_url": expected_job_url,
        "check_run_url": expected_check_url,
    }
    expected_check = {
        "check_id": job_id,
        "check_name": job_name,
        "head_sha": head,
        "check_app_id": GITHUB_ACTIONS_APP_ID,
        "check_app_slug": GITHUB_ACTIONS_APP_SLUG,
        "check_app_owner": GITHUB_ACTIONS_APP_OWNER,
        "status": "completed",
        "conclusion": "success",
        "details_url": expected_job_url,
    }
    if any(not _typed_equal(job.get(key), item) for key, item in expected_job.items()):
        _fail(STABLE_CODES["remote_gate"], "stored job identity drifted")
    if any(not _typed_equal(check.get(key), item) for key, item in expected_check.items()):
        _fail(STABLE_CODES["remote_gate"], "stored check identity drifted")
    for key in ("created_at", "completed_at"):
        if _canonical_utc(run.get(key)) is None:
            _fail(STABLE_CODES["remote_gate"], "stored workflow timestamp drifted")
    for key in ("started_at", "completed_at"):
        if _canonical_utc(job.get(key)) is None or job.get(key) != check.get(key):
            _fail(STABLE_CODES["remote_gate"], "stored job/check timestamp drifted")


def _validate_stored_remote_proof(value: Mapping[str, Any]) -> None:
    required = {
        "schema_version",
        "repository",
        "repository_id",
        "branch",
        "authorization_commit",
        "pull_request_number",
        "pull_request_id",
        "pull_request_draft",
        "refs",
        "parent",
        "current",
        "raw_response_sha256",
        "proof_sha256",
    }
    head = value.get("authorization_commit")
    pull_number = value.get("pull_request_number")
    pull_id = value.get("pull_request_id")
    if (
        set(value) != required
        or value.get("schema_version")
        != "us_fddk.short_term_form4_remote_gate_proof.v1"
        or value.get("repository") != REPOSITORY
        or value.get("repository_id") != REPOSITORY_ID
        or value.get("branch") != BRANCH
        or not isinstance(head, str)
        or COMMIT_RE.fullmatch(head) is None
        or type(pull_number) is not int
        or pull_number < 1
        or type(pull_id) is not int
        or pull_id < 1
        or value.get("pull_request_draft") is not True
        or value.get("proof_sha256") != canonical_sha256(value, omit="proof_sha256")
    ):
        _fail(STABLE_CODES["remote_gate"], "stored remote proof content drifted")
    raw = value.get("raw_response_sha256")
    refs = value.get("refs")
    expected_refs = {
        "current": {
            "ref": f"refs/heads/{BRANCH}",
            "object_type": "commit",
            "sha": head,
        },
        "parent": {
            "ref": f"refs/heads/{PARENT_BRANCH}",
            "object_type": "commit",
            "sha": ROUND44_COMMIT,
        },
    }
    if not _typed_equal(refs, expected_refs):
        _fail(STABLE_CODES["remote_gate"], "stored normalized refs drifted")
    raw_keys = {
        "current_ref_first",
        "parent_ref",
        "current_prs",
        "current_run_pages",
        "current_run",
        "current_jobs",
        "current_checks",
        "parent_run",
        "parent_jobs",
        "parent_checks",
        "current_ref_last",
    }
    if (
        not isinstance(raw, dict)
        or set(raw) != raw_keys
        or not isinstance(raw.get("current_run_pages"), list)
        or not raw["current_run_pages"]
        or any(
            not isinstance(item, str) or SHA256_RE.fullmatch(item) is None
            for item in raw["current_run_pages"]
        )
        or any(
            not isinstance(item, str) or SHA256_RE.fullmatch(item) is None
            for key, item in raw.items()
            if key != "current_run_pages"
        )
        or raw["current_ref_first"] != raw["current_ref_last"]
    ):
        _fail(STABLE_CODES["remote_gate"], "stored remote raw-response hashes drifted")
    _validate_stored_remote_side(
        value.get("parent"),
        head=ROUND44_COMMIT,
        branch=PARENT_BRANCH,
        workflow_name=ROUND44_WORKFLOW_NAME,
        workflow_path=ROUND44_WORKFLOW_PATH,
        job_name=ROUND44_JOB_NAME,
        pull_request_number=ROUND44_PR_NUMBER,
        pull_request_id=ROUND44_PR_ID,
        expected_run_id=ROUND44_RUN_ID,
        expected_job_id=ROUND44_JOB_ID,
    )
    _validate_stored_remote_side(
        value.get("current"),
        head=head,
        branch=BRANCH,
        workflow_name=ROUND45_WORKFLOW_NAME,
        workflow_path=ROUND45_WORKFLOW_PATH,
        job_name=ROUND45_JOB_NAME,
        pull_request_number=pull_number,
        pull_request_id=pull_id,
        expected_run_id=None,
        expected_job_id=None,
    )


def _assert_no_acl_or_xattr(path: Path, *, expected_mode_text: str, code: str) -> None:
    environment = {"LC_ALL": "C", "LANG": "C"}
    xattrs = _run_ok(
        [TOOL_CONTRACT["xattr"]["path"], str(path)],
        code=code,
        env=environment,
    )
    if xattrs:
        _fail(code, "private path has extended attributes")
    listing = _run_ok(
        [TOOL_CONTRACT["ls"]["path"], "-lde", str(path)],
        code=code,
        env=environment,
    )
    first_line = listing.decode("utf-8", errors="strict").splitlines()
    if not first_line or first_line[0].split(maxsplit=1)[0] != expected_mode_text:
        _fail(code, "private path has ACL or mode marker drift")


def _owner_directory_metadata(path: Path, *, code: str) -> os.stat_result:
    try:
        metadata = path.lstat()
    except OSError as exc:
        _fail(code, f"directory unavailable: {type(exc).__name__}")
    if (
        not stat.S_ISDIR(metadata.st_mode)
        or stat.S_IMODE(metadata.st_mode) != 0o700
        or metadata.st_uid != os.getuid()
        or path.is_symlink()
    ):
        _fail(code, "directory is not owner-only")
    flags = getattr(metadata, "st_flags", 0)
    immutable = getattr(stat, "UF_IMMUTABLE", 0) | getattr(stat, "SF_IMMUTABLE", 0)
    if flags & immutable:
        _fail(code, "directory is immutable")
    _assert_no_acl_or_xattr(path, expected_mode_text="drwx------", code=code)
    return metadata


def _owner_file_metadata(path: Path, *, code: str) -> os.stat_result:
    try:
        metadata = path.lstat()
    except OSError as exc:
        _fail(code, f"file unavailable: {type(exc).__name__}")
    if (
        not stat.S_ISREG(metadata.st_mode)
        or stat.S_IMODE(metadata.st_mode) != 0o600
        or metadata.st_uid != os.getuid()
        or metadata.st_nlink != 1
        or path.is_symlink()
    ):
        _fail(code, "file is not owner-only regular one-link data")
    flags = getattr(metadata, "st_flags", 0)
    immutable = getattr(stat, "UF_IMMUTABLE", 0) | getattr(stat, "SF_IMMUTABLE", 0)
    if flags & immutable:
        _fail(code, "file is immutable")
    _assert_no_acl_or_xattr(path, expected_mode_text="-rw-------", code=code)
    return metadata


def _validate_private_location(private_root: Path, repository_root: Path) -> None:
    if not private_root.is_absolute() or ".." in private_root.parts:
        _fail(STABLE_CODES["private_boundary"], "private root must be canonical absolute")
    if private_root.exists() and private_root.resolve() != private_root:
        _fail(STABLE_CODES["private_boundary"], "private root is not canonical")
    parent = private_root.parent
    if parent.resolve() != parent:
        _fail(STABLE_CODES["private_boundary"], "private parent is not canonical")
    _owner_directory_metadata(parent, code=STABLE_CODES["private_boundary"])
    if (
        _sha256_bytes(str(parent).encode("utf-8")) != PRIVATE_PARENT_PATH_SHA256
        or _sha256_bytes(str(private_root).encode("utf-8")) != PRIVATE_ROOT_PATH_SHA256
    ):
        _fail(STABLE_CODES["private_boundary"], "private path commitment drifted")
    try:
        private_root.resolve().relative_to(repository_root.resolve())
    except ValueError:
        pass
    else:
        _fail(STABLE_CODES["private_boundary"], "private root is inside repository")


def _volume_attestation(path: Path) -> dict[str, Any]:
    df_raw = _run_ok(
        [TOOL_CONTRACT["df"]["path"], "-P", str(path)],
        code=STABLE_CODES["private_boundary"],
    )
    lines = df_raw.decode("utf-8", errors="strict").splitlines()
    if len(lines) != 2:
        _fail(STABLE_CODES["private_boundary"], "df output drifted")
    fields = lines[1].split()
    if len(fields) != 6 or not fields[0].startswith("/dev/"):
        _fail(STABLE_CODES["private_boundary"], "backing device unresolved")
    device = fields[0]
    diskutil_raw = _run_ok(
        [TOOL_CONTRACT["diskutil"]["path"], "info", "-plist", device],
        code=STABLE_CODES["private_boundary"],
    )
    try:
        info = plistlib.loads(diskutil_raw)
    except Exception as exc:
        _fail(STABLE_CODES["private_boundary"], f"diskutil plist invalid: {type(exc).__name__}")
    required_true = (
        "FileVault",
        "Encryption",
        "EncryptionThisVolumeProper",
        "Writable",
        "WritableVolume",
        "Internal",
        "SolidState",
    )
    if not isinstance(info, dict) or any(info.get(key) is not True for key in required_true):
        _fail(STABLE_CODES["private_boundary"], "volume encryption state is not exact")
    if info.get("Locked") is not False:
        _fail(STABLE_CODES["private_boundary"], "volume is locked or lock state is unknown")
    volume_uuid = info.get("VolumeUUID")
    device_identifier = info.get("DeviceIdentifier")
    device_node = info.get("DeviceNode")
    mount_point = info.get("MountPoint")
    if (
        not all(
            isinstance(item, str) and item
            for item in (volume_uuid, device_identifier, device_node, mount_point)
        )
        or device_node != device
        or device != f"/dev/{device_identifier}"
        or mount_point != fields[5]
    ):
        _fail(STABLE_CODES["private_boundary"], "volume identity is incomplete")
    filevault_raw = _run_ok(
        [TOOL_CONTRACT["fdesetup"]["path"], "status"],
        code=STABLE_CODES["private_boundary"],
    )
    if filevault_raw != b"FileVault is On.\n":
        _fail(STABLE_CODES["private_boundary"], "FileVault status drifted")
    metadata = path.stat()
    return {
        "schema_version": "us_fddk.short_term_form4_volume_attestation.v1",
        "canonical_private_root": str(path),
        "private_root_path_sha256": _sha256_bytes(str(path).encode("utf-8")),
        "device": device,
        "device_identifier": device_identifier,
        "mount_point": mount_point,
        "volume_uuid": volume_uuid,
        "volume_uuid_sha256": _sha256_bytes(volume_uuid.encode("ascii")),
        "st_dev": metadata.st_dev,
        "st_ino": metadata.st_ino,
        "owner_uid": metadata.st_uid,
        "mode": "0700",
        "filevault": True,
        "encryption": True,
        "encryption_this_volume_proper": True,
        "locked": False,
        "writable": True,
        "diskutil_plist_sha256": _sha256_bytes(diskutil_raw),
        "fdesetup_status_sha256": _sha256_bytes(filevault_raw),
        "attestation_sha256": "",
    }


def _open_directory_fd(path: Path) -> int:
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        return os.open(path, flags)
    except OSError as exc:
        _fail(STABLE_CODES["private_boundary"], f"directory open failed: {type(exc).__name__}")


def _open_child_directory_fd(parent_fd: int, name: str) -> int:
    if not name or "/" in name or name in {".", ".."}:
        _fail(STABLE_CODES["private_boundary"], "unsafe child directory name")
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        return os.open(name, flags, dir_fd=parent_fd)
    except OSError as exc:
        _fail(STABLE_CODES["private_boundary"], f"child directory open failed: {type(exc).__name__}")


def _validate_directory_fd(descriptor: int) -> None:
    metadata = os.fstat(descriptor)
    if (
        not stat.S_ISDIR(metadata.st_mode)
        or stat.S_IMODE(metadata.st_mode) != 0o700
        or metadata.st_uid != os.getuid()
    ):
        _fail(STABLE_CODES["private_boundary"], "directory fd drifted")


def _assert_path_matches_fd(path: Path, descriptor: int, *, code: str) -> None:
    try:
        path_metadata = path.lstat()
        fd_metadata = os.fstat(descriptor)
    except OSError as exc:
        _fail(code, f"path/fd identity unavailable: {type(exc).__name__}")
    if (
        path.is_symlink()
        or path_metadata.st_dev != fd_metadata.st_dev
        or path_metadata.st_ino != fd_metadata.st_ino
        or stat.S_IFMT(path_metadata.st_mode) != stat.S_IFMT(fd_metadata.st_mode)
    ):
        _fail(code, "path no longer names opened directory")


def _mkdir_at(parent_fd: int, name: str) -> bool:
    if not name or "/" in name or name in {".", ".."}:
        _fail(STABLE_CODES["private_boundary"], "unsafe directory name")
    try:
        os.mkdir(name, mode=0o700, dir_fd=parent_fd)
    except FileExistsError:
        return False
    except OSError as exc:
        _fail(STABLE_CODES["private_boundary"], f"directory create failed: {type(exc).__name__}")
    os.fsync(parent_fd)
    return True


def _write_create_at(parent_fd: int, name: str, data: bytes, *, mode: int = 0o600) -> str:
    if not name or "/" in name or name in {".", ".."}:
        _fail(STABLE_CODES["private_boundary"], "unsafe private filename")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(name, flags, mode, dir_fd=parent_fd)
    except FileExistsError:
        _fail(STABLE_CODES["start_receipt"], "create-once private artifact exists")
    except OSError as exc:
        _fail(STABLE_CODES["private_boundary"], f"private create failed: {type(exc).__name__}")
    try:
        offset = 0
        while offset < len(data):
            written = os.write(descriptor, data[offset:])
            if written <= 0:
                _fail(STABLE_CODES["private_boundary"], "short private write")
            offset += written
        os.fchmod(descriptor, mode)
        metadata = os.fstat(descriptor)
        if (
            not stat.S_ISREG(metadata.st_mode)
            or stat.S_IMODE(metadata.st_mode) != mode
            or metadata.st_uid != os.getuid()
            or metadata.st_nlink != 1
        ):
            _fail(STABLE_CODES["private_boundary"], "private file metadata drifted")
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    os.fsync(parent_fd)
    return _sha256_bytes(data)


def _open_lock(root_fd: int) -> int:
    flags = os.O_RDWR | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    created = False
    try:
        descriptor = os.open(".monitor-start.lock", flags, 0o600, dir_fd=root_fd)
        created = True
    except FileExistsError:
        existing_flags = os.O_RDWR
        if hasattr(os, "O_NOFOLLOW"):
            existing_flags |= os.O_NOFOLLOW
        try:
            descriptor = os.open(".monitor-start.lock", existing_flags, dir_fd=root_fd)
        except OSError as exc:
            _fail(
                STABLE_CODES["private_boundary"],
                f"existing lock open failed: {type(exc).__name__}",
            )
    except OSError as exc:
        _fail(STABLE_CODES["private_boundary"], f"lock open failed: {type(exc).__name__}")
    if created:
        os.fchmod(descriptor, 0o600)
    metadata = os.fstat(descriptor)
    if (
        not stat.S_ISREG(metadata.st_mode)
        or stat.S_IMODE(metadata.st_mode) != 0o600
        or metadata.st_uid != os.getuid()
        or metadata.st_nlink != 1
    ):
        os.close(descriptor)
        _fail(STABLE_CODES["private_boundary"], "global lock metadata drifted")
    os.fsync(descriptor)
    os.fsync(root_fd)
    fcntl.flock(descriptor, fcntl.LOCK_EX)
    return descriptor


def _genesis_record(kind: str, authorization_commit: str) -> dict[str, Any]:
    record: dict[str, Any] = {
        "schema_version": "us_fddk.short_term_form4_chain_entry.v1",
        "authorization_id": AUTHORIZATION_ID,
        "authorization_commit": authorization_commit,
        "ledger_kind": kind,
        "ordinal": 0,
        "event": "genesis",
        "event_count": 0,
        "prev_sha256": ZERO_SHA256,
        "entry_sha256": "",
    }
    record["entry_sha256"] = canonical_sha256(record, omit="entry_sha256")
    return record


def _jsonl_line(payload: Mapping[str, Any]) -> bytes:
    return _canonical_bytes(payload) + b"\n"


def _parse_chain_bytes(raw: bytes, *, expected_kind: str) -> tuple[list[dict[str, Any]], str]:
    if not raw.endswith(b"\n"):
        _fail(STABLE_CODES["attempt_ledger"], "ledger has partial tail")
    lines = raw.splitlines()
    if not lines:
        _fail(STABLE_CODES["attempt_ledger"], "ledger is empty")
    records: list[dict[str, Any]] = []
    previous = ZERO_SHA256
    for index, line in enumerate(lines):
        value = _load_exact_json_bytes(line, code=STABLE_CODES["attempt_ledger"])
        if not isinstance(value, dict):
            _fail(STABLE_CODES["attempt_ledger"], "ledger entry is not an object")
        if line != _canonical_bytes(value):
            _fail(STABLE_CODES["attempt_ledger"], "ledger line is not canonical")
        if (
            value.get("schema_version") != "us_fddk.short_term_form4_chain_entry.v1"
            or value.get("authorization_id") != AUTHORIZATION_ID
            or value.get("ledger_kind") != expected_kind
            or type(value.get("ordinal")) is not int
            or value.get("ordinal") != index
            or type(value.get("event_count")) is not int
            or value.get("event_count") != index
            or value.get("prev_sha256") != previous
            or value.get("entry_sha256") != canonical_sha256(value, omit="entry_sha256")
        ):
            _fail(STABLE_CODES["attempt_ledger"], "ledger chain drifted")
        if index == 0 and (
            value.get("event") != "genesis"
            or value.get("event_count") != 0
            or value.get("prev_sha256") != ZERO_SHA256
        ):
            _fail(STABLE_CODES["attempt_ledger"], "ledger genesis drifted")
        previous = str(value["entry_sha256"])
        records.append(value)
    return records, previous


def _parse_chain(path: Path, *, expected_kind: str) -> tuple[list[dict[str, Any]], str]:
    _owner_file_metadata(path, code=STABLE_CODES["attempt_ledger"])
    try:
        raw = path.read_bytes()
    except OSError as exc:
        _fail(STABLE_CODES["attempt_ledger"], f"ledger unreadable: {type(exc).__name__}")
    return _parse_chain_bytes(raw, expected_kind=expected_kind)


def _append_chain_entry(
    path: Path,
    *,
    kind: str,
    event: str,
    fields: Mapping[str, Any],
    parent_fd: int | None = None,
) -> str:
    reserved = {
        "schema_version",
        "authorization_id",
        "authorization_commit",
        "ledger_kind",
        "ordinal",
        "event",
        "event_count",
        "prev_sha256",
        "entry_sha256",
    }
    if reserved.intersection(fields):
        _fail(STABLE_CODES["attempt_ledger"], "ledger fields override protected keys")
    opened_parent = -1
    if parent_fd is None:
        opened_parent = _open_directory_fd(path.parent)
        parent_fd = opened_parent
    flags = os.O_RDWR | os.O_APPEND
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = -1
    try:
        try:
            descriptor = os.open(path.name, flags, dir_fd=parent_fd)
        except OSError as exc:
            _fail(
                STABLE_CODES["attempt_ledger"],
                f"ledger append open failed: {type(exc).__name__}",
            )
        metadata = os.fstat(descriptor)
        if (
            not stat.S_ISREG(metadata.st_mode)
            or stat.S_IMODE(metadata.st_mode) != 0o600
            or metadata.st_uid != os.getuid()
            or metadata.st_nlink != 1
        ):
            _fail(STABLE_CODES["attempt_ledger"], "ledger append metadata drifted")
        os.lseek(descriptor, 0, os.SEEK_SET)
        chunks: list[bytes] = []
        while chunk := os.read(descriptor, 1024 * 1024):
            chunks.append(chunk)
        records, head = _parse_chain_bytes(b"".join(chunks), expected_kind=kind)
        entry: dict[str, Any] = {
            "schema_version": "us_fddk.short_term_form4_chain_entry.v1",
            "authorization_id": AUTHORIZATION_ID,
            "authorization_commit": records[0]["authorization_commit"],
            "ledger_kind": kind,
            "ordinal": len(records),
            "event": event,
            "event_count": len(records),
            "prev_sha256": head,
            **dict(fields),
            "entry_sha256": "",
        }
        entry["entry_sha256"] = canonical_sha256(entry, omit="entry_sha256")
        data = _jsonl_line(entry)
        offset = 0
        while offset < len(data):
            written = os.write(descriptor, data[offset:])
            if written <= 0:
                _fail(STABLE_CODES["attempt_ledger"], "ledger append was short")
            offset += written
        os.fsync(descriptor)
        os.fsync(parent_fd)
        return str(entry["entry_sha256"])
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        if opened_parent >= 0:
            os.close(opened_parent)


def _account_zero_state(authorization_commit: str) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "schema_version": "us_fddk.short_term_form4_account_zero_state.v1",
        "authorization_id": AUTHORIZATION_ID,
        "authorization_commit": authorization_commit,
        "proof_scope": "round45_form4_runtime_namespace_only",
        "other_user_accounts_in_scope": False,
        "external_broker_account_zero_proven": False,
        "paper": {
            "authorized": False,
            "funding_usd": 0,
            "cash_usd": 0,
            "nav_points": 0,
            "positions": [],
            "open_orders": [],
            "trades": [],
            "backfilled_trades": 0,
        },
        "broker": {
            "binding_state": "unbound",
            "account_identifier_count": 0,
            "credential_handle_count": 0,
            "transport_count": 0,
        },
        "real_ledger": {
            "positions": [],
            "orders": [],
            "fills": [],
            "transfers": [],
            "entry_count": 0,
            "real_money_action_usd": 0,
        },
        "receipt_sha256": "",
    }
    payload["receipt_sha256"] = canonical_sha256(payload, omit="receipt_sha256")
    return payload


def _monitor_state(authorization_commit: str) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "schema_version": "us_fddk.short_term_form4_monitor_state.v1",
        "authorization_id": AUTHORIZATION_ID,
        "authorization_commit": authorization_commit,
        "status": "monitor_started_collection_locked",
        "sec_collection_enabled": False,
        "sec_collection_capability_issued": False,
        "prospective_collector_implemented": False,
        "state_boundary": dict(STATE_BOUNDARY),
        "permission": dict(PERMISSION),
        "today_action": "今天不下單",
        "state_sha256": "",
    }
    payload["state_sha256"] = canonical_sha256(payload, omit="state_sha256")
    return payload


def _assert_private_zero_state(payload: Mapping[str, Any]) -> None:
    authorization_commit = payload.get("authorization_commit")
    if (
        not isinstance(authorization_commit, str)
        or COMMIT_RE.fullmatch(authorization_commit) is None
        or not _typed_equal(payload, _account_zero_state(authorization_commit))
    ):
        _fail(STABLE_CODES["non_engineering"], "dedicated account state is not exact zero")


def _validate_volume_receipt(
    payload: Mapping[str, Any],
    *,
    private_root: Path,
) -> None:
    keys = {
        "schema_version",
        "canonical_private_root",
        "private_root_path_sha256",
        "device",
        "device_identifier",
        "mount_point",
        "volume_uuid",
        "volume_uuid_sha256",
        "st_dev",
        "st_ino",
        "owner_uid",
        "mode",
        "filevault",
        "encryption",
        "encryption_this_volume_proper",
        "locked",
        "writable",
        "diskutil_plist_sha256",
        "fdesetup_status_sha256",
        "attestation_sha256",
    }
    volume_uuid = payload.get("volume_uuid")
    metadata = private_root.stat()
    if (
        set(payload) != keys
        or payload.get("schema_version")
        != "us_fddk.short_term_form4_volume_attestation.v1"
        or payload.get("canonical_private_root") != str(private_root)
        or payload.get("private_root_path_sha256") != PRIVATE_ROOT_PATH_SHA256
        or not isinstance(volume_uuid, str)
        or re.fullmatch(r"[0-9A-Fa-f]{8}(?:-[0-9A-Fa-f]{4}){3}-[0-9A-Fa-f]{12}", volume_uuid)
        is None
        or payload.get("volume_uuid_sha256")
        != _sha256_bytes(volume_uuid.encode("ascii"))
        or type(payload.get("st_dev")) is not int
        or payload.get("st_dev") != metadata.st_dev
        or type(payload.get("st_ino")) is not int
        or payload.get("st_ino") != metadata.st_ino
        or type(payload.get("owner_uid")) is not int
        or payload.get("owner_uid") != os.getuid()
        or payload.get("mode") != "0700"
        or payload.get("filevault") is not True
        or payload.get("encryption") is not True
        or payload.get("encryption_this_volume_proper") is not True
        or payload.get("locked") is not False
        or payload.get("writable") is not True
        or any(
            not isinstance(payload.get(key), str)
            or SHA256_RE.fullmatch(str(payload.get(key))) is None
            for key in ("diskutil_plist_sha256", "fdesetup_status_sha256")
        )
        or payload.get("attestation_sha256")
        != canonical_sha256(payload, omit="attestation_sha256")
    ):
        _fail(STABLE_CODES["private_boundary"], "stored volume attestation drifted")
    current = _volume_attestation(private_root)
    stable_keys = {
        "canonical_private_root",
        "private_root_path_sha256",
        "device",
        "device_identifier",
        "mount_point",
        "volume_uuid",
        "volume_uuid_sha256",
        "st_dev",
        "st_ino",
        "owner_uid",
        "mode",
        "filevault",
        "encryption",
        "encryption_this_volume_proper",
        "locked",
        "writable",
    }
    if any(not _typed_equal(payload.get(key), current.get(key)) for key in stable_keys):
        _fail(STABLE_CODES["private_boundary"], "current volume identity drifted")


def _validate_start_intent(
    payload: Mapping[str, Any],
    *,
    raw: bytes,
    authorization: Mapping[str, Any],
    authorization_file_sha256: str,
    authorization_commit: str,
    remote_proof: Mapping[str, Any],
    remote_file_sha256: str,
    volume: Mapping[str, Any],
    volume_file_sha256: str,
    account: Mapping[str, Any],
    account_file_sha256: str,
) -> None:
    keys = {
        "schema_version",
        "authorization_id",
        "authorization_commit",
        "authorization_receipt_sha256",
        "authorization_receipt_file_sha256",
        "prepared_at_untrusted_local",
        "host_identity_sha256",
        "remote_gate_proof_file_sha256",
        "remote_gate_proof_sha256",
        "volume_attestation_file_sha256",
        "volume_attestation_sha256",
        "account_zero_state_file_sha256",
        "account_zero_state_sha256",
        "genesis_file_sha256",
        "genesis_chain_heads",
        "objects_count",
        "tsa_contract",
        "state_boundary",
        "permission",
        "intent_sha256",
    }
    genesis_hashes = {
        kind: _sha256_bytes(_jsonl_line(_genesis_record(kind, authorization_commit)))
        for kind in LEDGER_KINDS
    }
    genesis_heads = {
        kind: _genesis_record(kind, authorization_commit)["entry_sha256"]
        for kind in LEDGER_KINDS
    }
    if (
        set(payload) != keys
        or payload.get("schema_version") != "us_fddk.short_term_form4_start_intent.v1"
        or payload.get("authorization_id") != AUTHORIZATION_ID
        or payload.get("authorization_commit") != authorization_commit
        or payload.get("authorization_receipt_sha256") != authorization["receipt_sha256"]
        or payload.get("authorization_receipt_file_sha256")
        != authorization_file_sha256
        or _canonical_utc(payload.get("prepared_at_untrusted_local")) is None
        or not isinstance(payload.get("host_identity_sha256"), str)
        or SHA256_RE.fullmatch(str(payload.get("host_identity_sha256"))) is None
        or payload.get("remote_gate_proof_file_sha256") != remote_file_sha256
        or payload.get("remote_gate_proof_sha256") != remote_proof["proof_sha256"]
        or payload.get("volume_attestation_file_sha256") != volume_file_sha256
        or payload.get("volume_attestation_sha256") != volume["attestation_sha256"]
        or payload.get("account_zero_state_file_sha256") != account_file_sha256
        or payload.get("account_zero_state_sha256") != account["receipt_sha256"]
        or not _typed_equal(payload.get("genesis_file_sha256"), genesis_hashes)
        or not _typed_equal(payload.get("genesis_chain_heads"), genesis_heads)
        or type(payload.get("objects_count")) is not int
        or payload.get("objects_count") != 0
        or not _typed_equal(payload.get("tsa_contract"), TSA_CONTRACT)
        or not _typed_equal(payload.get("state_boundary"), STATE_BOUNDARY)
        or not _typed_equal(payload.get("permission"), PERMISSION)
        or payload.get("intent_sha256") != canonical_sha256(payload, omit="intent_sha256")
        or raw != _pretty_json_bytes(payload)
    ):
        _fail(STABLE_CODES["start_receipt"], "anchored start intent drifted")


def _expected_audit_records(
    authorization_commit: str,
    *,
    query_sha256: str,
    anchor: Mapping[str, Any],
) -> list[dict[str, Any]]:
    genesis = _genesis_record("audit", authorization_commit)
    started: dict[str, Any] = {
        "schema_version": "us_fddk.short_term_form4_chain_entry.v1",
        "authorization_id": AUTHORIZATION_ID,
        "authorization_commit": authorization_commit,
        "ledger_kind": "audit",
        "ordinal": 1,
        "event": "tsa_request_started",
        "event_count": 1,
        "prev_sha256": genesis["entry_sha256"],
        "endpoint_sha256": _sha256_bytes(TSA_URL.encode("ascii")),
        "query_sha256": query_sha256,
        "request_ordinal": 1,
        "retry_count": 0,
        "entry_sha256": "",
    }
    started["entry_sha256"] = canonical_sha256(started, omit="entry_sha256")
    verified: dict[str, Any] = {
        "schema_version": "us_fddk.short_term_form4_chain_entry.v1",
        "authorization_id": AUTHORIZATION_ID,
        "authorization_commit": authorization_commit,
        "ledger_kind": "audit",
        "ordinal": 2,
        "event": "tsa_response_verified",
        "event_count": 2,
        "prev_sha256": started["entry_sha256"],
        "response_sha256": anchor["response_sha256"],
        "signed_gen_time": anchor["signed_gen_time"],
        "monitor_started_at": anchor["monitor_started_at"],
        "request_ordinal": 1,
        "entry_sha256": "",
    }
    verified["entry_sha256"] = canonical_sha256(verified, omit="entry_sha256")
    return [genesis, started, verified]


def _der_element_bounds(
    value: bytes,
    offset: int,
    limit: int,
) -> tuple[int, int, int] | None:
    if offset < 0 or limit > len(value) or offset + 2 > limit:
        return None
    tag = value[offset]
    if tag & 0x1F == 0x1F:
        return None
    first = value[offset + 1]
    if first < 0x80:
        content_start = offset + 2
        length = first
    else:
        count = first & 0x7F
        if count == 0 or count > 4 or offset + 2 + count > limit:
            return None
        length_bytes = value[offset + 2 : offset + 2 + count]
        if not length_bytes or length_bytes[0] == 0:
            return None
        length = int.from_bytes(length_bytes, "big")
        if length < 0x80 or count != (length.bit_length() + 7) // 8:
            return None
        content_start = offset + 2 + count
    content_end = content_start + length
    if content_end > limit:
        return None
    return tag, content_start, content_end


def _der_is_exact_sequence(value: bytes) -> bool:
    bounds = _der_element_bounds(value, 0, len(value))
    return bounds is not None and bounds[0] == 0x30 and bounds[2] == len(value)


def _validate_timestamp_response_status(value: bytes) -> None:
    outer = _der_element_bounds(value, 0, len(value))
    if outer is None or outer[0] != 0x30 or outer[2] != len(value):
        _fail(STABLE_CODES["external_anchor"], "timestamp response DER is not exact")
    status = _der_element_bounds(value, outer[1], outer[2])
    if status is None or status[0] != 0x30:
        _fail(STABLE_CODES["external_anchor"], "timestamp status structure drifted")
    status_integer = _der_element_bounds(value, status[1], status[2])
    if (
        status_integer is None
        or status_integer[0] != 0x02
        or value[status_integer[1] : status_integer[2]] != b"\x00"
        or status_integer[2] != status[2]
    ):
        _fail(STABLE_CODES["external_anchor"], "timestamp PKI status is not exact granted")
    token = _der_element_bounds(value, status[2], outer[2])
    if token is None or token[0] != 0x30 or token[2] != outer[2]:
        _fail(STABLE_CODES["external_anchor"], "timestamp token is missing or ambiguous")


def _query_nonce_from_der(value: bytes) -> int:
    outer = _der_element_bounds(value, 0, len(value))
    if outer is None or outer[0] != 0x30 or outer[2] != len(value):
        _fail(STABLE_CODES["external_anchor"], "timestamp query DER is not exact")
    offset = outer[1]
    expected_tags = (0x02, 0x30, 0x06, 0x02, 0x01)
    elements: list[tuple[int, int, int]] = []
    for expected_tag in expected_tags:
        element = _der_element_bounds(value, offset, outer[2])
        if element is None or element[0] != expected_tag:
            _fail(STABLE_CODES["external_anchor"], "timestamp query structure drifted")
        elements.append(element)
        offset = element[2]
    if offset != outer[2]:
        _fail(STABLE_CODES["external_anchor"], "timestamp query has extra fields")
    version = value[elements[0][1] : elements[0][2]]
    nonce_bytes = value[elements[3][1] : elements[3][2]]
    cert_req = value[elements[4][1] : elements[4][2]]
    if version != b"\x01" or cert_req != b"\xff":
        _fail(STABLE_CODES["external_anchor"], "timestamp query flags drifted")
    if not 1 <= len(nonce_bytes) <= 9:
        _fail(STABLE_CODES["external_anchor"], "timestamp query nonce DER drifted")
    if nonce_bytes[0] == 0:
        if len(nonce_bytes) == 1 or nonce_bytes[1] < 0x80:
            _fail(STABLE_CODES["external_anchor"], "timestamp query nonce DER drifted")
    elif nonce_bytes[0] >= 0x80:
        _fail(STABLE_CODES["external_anchor"], "timestamp query nonce DER is negative")
    nonce = int.from_bytes(nonce_bytes, "big", signed=False)
    if nonce == 0:
        _fail(STABLE_CODES["external_anchor"], "timestamp query nonce is zero")
    return nonce


def _exact_nonce(text: str) -> str:
    matches = re.findall(r"^Nonce:\s*0x([0-9A-Fa-f]+)\s*$", text, flags=re.MULTILINE)
    if len(matches) != 1 or len(matches[0]) > 34 or int(matches[0], 16) == 0:
        _fail(STABLE_CODES["external_anchor"], "timestamp nonce drifted")
    return matches[0].casefold()


def _exact_message_imprint(text: str, *, end_prefix: str) -> str:
    lines = text.splitlines()
    starts = [index for index, line in enumerate(lines) if line == "Message data:"]
    if len(starts) != 1:
        _fail(STABLE_CODES["external_anchor"], "timestamp imprint is missing")
    start = starts[0] + 1
    ends = [
        index
        for index in range(start, len(lines))
        if lines[index].startswith(end_prefix)
    ]
    if len(ends) != 1 or ends[0] == start:
        _fail(STABLE_CODES["external_anchor"], "timestamp imprint boundary drifted")
    octets: list[str] = []
    for line in lines[start : ends[0]]:
        if " - " not in line:
            _fail(STABLE_CODES["external_anchor"], "timestamp imprint format drifted")
        rendered = line.split(" - ", 1)[1].split("   ", 1)[0]
        pairs = re.findall(
            r"(?<![0-9A-Fa-f])[0-9A-Fa-f]{2}(?![0-9A-Fa-f])",
            rendered,
        )
        if not pairs:
            _fail(STABLE_CODES["external_anchor"], "timestamp imprint format drifted")
        octets.extend(pairs)
    return "".join(octets).casefold()


def _certificate_fingerprint(path: Path) -> str:
    output = _run_ok(
        [
            TOOL_CONTRACT["openssl"]["path"],
            "x509",
            "-in",
            str(path),
            "-outform",
            "DER",
        ],
        code=STABLE_CODES["request_plan"],
    )
    return _sha256_bytes(output)


def _validate_tsa_assets(root: Path) -> None:
    expected = (
        (ROOT_CERT_PATH, TSA_ROOT_FINGERPRINT),
        (INTERMEDIATE_CERT_PATH, TSA_INTERMEDIATE_FINGERPRINT),
        (RESPONDER_CERT_PATH, TSA_RESPONDER_FINGERPRINT),
    )
    for relative, fingerprint in expected:
        if _certificate_fingerprint(root / relative) != fingerprint:
            _fail(STABLE_CODES["request_plan"], "TSA certificate fingerprint drifted")
    _run_ok(
        [
            TOOL_CONTRACT["openssl"]["path"],
            "verify",
            "-no-CApath",
            "-no-CAstore",
            "-purpose",
            "timestampsign",
            "-x509_strict",
            "-verify_depth",
            "2",
            "-check_ss_sig",
            "-CAfile",
            str(root / ROOT_CERT_PATH),
            "-untrusted",
            str(root / INTERMEDIATE_CERT_PATH),
            str(root / RESPONDER_CERT_PATH),
        ],
        code=STABLE_CODES["request_plan"],
    )


def _generate_anchor_query(intent_sha256: str, root: Path) -> bytes:
    if SHA256_RE.fullmatch(intent_sha256) is None:
        _fail(STABLE_CODES["external_anchor"], "intent hash invalid")
    query = _run_ok(
        [
            TOOL_CONTRACT["openssl"]["path"],
            "ts",
            "-query",
            "-digest",
            intent_sha256,
            "-sha256",
            "-cert",
            "-tspolicy",
            TSA_POLICY_OID,
        ],
        cwd=root,
        code=STABLE_CODES["external_anchor"],
    )
    if not _der_is_exact_sequence(query):
        _fail(STABLE_CODES["external_anchor"], "timestamp query DER is not exact")
    _validate_anchor_query(query, expected_imprint_sha256=intent_sha256)
    return query


def _validate_anchor_query(query: bytes, *, expected_imprint_sha256: str) -> str:
    if SHA256_RE.fullmatch(expected_imprint_sha256) is None:
        _fail(STABLE_CODES["external_anchor"], "expected timestamp imprint is invalid")
    if not _der_is_exact_sequence(query):
        _fail(STABLE_CODES["external_anchor"], "timestamp query DER is not exact")
    text = _run_ok(
        [
            TOOL_CONTRACT["openssl"]["path"],
            "ts",
            "-query",
            "-in",
            "-",
            "-text",
        ],
        input_bytes=query,
        code=STABLE_CODES["external_anchor"],
    ).decode("utf-8", errors="strict")
    if (
        text.splitlines().count("Version: 1") != 1
        or text.splitlines().count("Hash Algorithm: sha256") != 1
        or text.splitlines().count(f"Policy OID: {TSA_POLICY_OID}") != 1
        or text.splitlines().count("Certificate required: yes") != 1
    ):
        _fail(STABLE_CODES["external_anchor"], "timestamp query contract drifted")
    if int(_exact_nonce(text), 16) != _query_nonce_from_der(query):
        _fail(STABLE_CODES["external_anchor"], "timestamp query nonce text drifted")
    actual = _exact_message_imprint(text, end_prefix="Policy OID:")
    if actual != expected_imprint_sha256:
        _fail(STABLE_CODES["external_anchor"], "timestamp query imprint drifted")
    return text


def _post_anchor_once(query: bytes, response_fd: int) -> dict[str, Any]:
    environment = {"LANG": "C", "LC_ALL": "C"}
    output = _run_ok(
        [
            TOOL_CONTRACT["curl"]["path"],
            "--disable",
            "--fail",
            "--silent",
            "--show-error",
            "--proto",
            "=http",
            "--noproxy",
            "*",
            "--retry",
            "0",
            "--max-redirs",
            "0",
            "--connect-timeout",
            "10",
            "--max-time",
            "30",
            "--max-filesize",
            str(TSA_CONTRACT["response_bytes_max"]),
            "--header",
            "Content-Type: application/timestamp-query",
            "--data-binary",
            "@-",
            "--output",
            f"/dev/fd/{response_fd}",
            "--write-out",
            "%{http_code}\n%{content_type}\n%{size_download}\n%{num_redirects}\n",
            TSA_URL,
        ],
        input_bytes=query,
        pass_fds=(response_fd,),
        code=STABLE_CODES["external_anchor"],
        timeout=35,
        env=environment,
    )
    lines = output.decode("utf-8", errors="strict").splitlines()
    if len(lines) != 4:
        _fail(STABLE_CODES["external_anchor"], "timestamp HTTP receipt drifted")
    try:
        size_download = int(float(lines[2]))
        redirects = int(lines[3])
    except ValueError:
        _fail(STABLE_CODES["external_anchor"], "timestamp HTTP counters drifted")
    if (
        lines[0] != "200"
        or lines[1].split(";", 1)[0].strip().casefold()
        != TSA_CONTRACT["response_content_type"]
        or size_download <= 0
        or size_download > TSA_CONTRACT["response_bytes_max"]
        or redirects != 0
    ):
        _fail(STABLE_CODES["external_anchor"], "timestamp HTTP response was not exact")
    return {
        "http_status": 200,
        "content_type": TSA_CONTRACT["response_content_type"],
        "response_bytes": size_download,
        "redirect_count": 0,
        "request_count": 1,
        "retry_count": 0,
        "proxy_used": False,
    }


def _parse_accuracy(text: str) -> tuple[timedelta, dict[str, Any]]:
    accuracy_lines = re.findall(r"^Accuracy:.*$", text, flags=re.MULTILINE)
    if accuracy_lines == ["Accuracy: unspecified"]:
        _fail(STABLE_CODES["external_anchor"], "timestamp accuracy is unspecified")
    if len(accuracy_lines) != 1:
        _fail(STABLE_CODES["external_anchor"], "timestamp accuracy field drifted")
    match = re.fullmatch(
        r"^Accuracy:\s*(?:(0x[0-9A-Fa-f]+|\d+) seconds)?(?:,\s*(0x[0-9A-Fa-f]+|\d+) millis)?(?:,\s*(0x[0-9A-Fa-f]+|\d+) micros)?\s*$",
        accuracy_lines[0],
    )
    if match is None:
        _fail(STABLE_CODES["external_anchor"], "timestamp accuracy format drifted")

    def parse(value: str | None) -> int:
        if value is None:
            return 0
        return int(value, 16) if value.lower().startswith("0x") else int(value)

    seconds, millis, micros = (parse(value) for value in match.groups())
    if seconds < 0 or not 0 <= millis <= 999 or not 0 <= micros <= 999:
        _fail(STABLE_CODES["external_anchor"], "timestamp accuracy drifted")
    return timedelta(seconds=seconds, milliseconds=millis, microseconds=micros), {
        "accuracy_unspecified": False,
        "seconds": seconds,
        "millis": millis,
        "micros": micros,
    }


def _format_utc(value: datetime) -> str:
    normalized = value.astimezone(UTC)
    if normalized.microsecond:
        return normalized.isoformat(timespec="microseconds").replace("+00:00", "Z")
    return normalized.isoformat(timespec="seconds").replace("+00:00", "Z")


def _verify_anchor(
    *,
    query_path: Path,
    response_path: Path,
    repository_root: Path,
    earliest_time: str,
    expected_intent_sha256: str,
) -> dict[str, Any]:
    _owner_file_metadata(query_path, code=STABLE_CODES["external_anchor"])
    _owner_file_metadata(response_path, code=STABLE_CODES["external_anchor"])
    response = response_path.read_bytes()
    query = query_path.read_bytes()
    query_text = _validate_anchor_query(
        query,
        expected_imprint_sha256=expected_intent_sha256,
    )
    _validate_timestamp_response_status(response)
    token = _run_ok(
        [
            TOOL_CONTRACT["openssl"]["path"],
            "ts",
            "-reply",
            "-in",
            str(response_path),
            "-token_out",
        ],
        code=STABLE_CODES["external_anchor"],
    )
    if not _der_is_exact_sequence(token):
        _fail(STABLE_CODES["external_anchor"], "signed timestamp token DER drifted")
    token_text = _run_ok(
        [
            TOOL_CONTRACT["openssl"]["path"],
            "ts",
            "-reply",
            "-token_in",
            "-in",
            "/dev/stdin",
            "-text",
        ],
        input_bytes=token,
        code=STABLE_CODES["external_anchor"],
    ).decode("utf-8", errors="strict")
    token_lines = token_text.splitlines()
    if (
        token_lines.count("Version: 1") != 1
        or token_lines.count(f"Policy OID: {TSA_POLICY_OID}") != 1
        or token_lines.count("Hash Algorithm: sha256") != 1
        or token_lines.count("Ordering: no") != 1
    ):
        _fail(STABLE_CODES["external_anchor"], "signed timestamp fields drifted")
    if _exact_message_imprint(token_text, end_prefix="Serial number:") != expected_intent_sha256:
        _fail(STABLE_CODES["external_anchor"], "signed timestamp imprint drifted")
    query_nonce = _exact_nonce(query_text)
    token_nonce = _exact_nonce(token_text)
    if int(query_nonce, 16) != int(token_nonce, 16):
        _fail(STABLE_CODES["external_anchor"], "signed timestamp nonce drifted")
    token_serials = re.findall(
        r"^Serial number:\s*0x([0-9A-Fa-f]+)\s*$",
        token_text,
        flags=re.MULTILINE,
    )
    if len(token_serials) != 1 or int(token_serials[0], 16) == 0:
        _fail(STABLE_CODES["external_anchor"], "signed timestamp serial drifted")
    time_matches = re.findall(
        r"^Time stamp:\s*(.+ GMT)\s*$",
        token_text,
        flags=re.MULTILINE,
    )
    if len(time_matches) != 1:
        _fail(STABLE_CODES["external_anchor"], "signed timestamp missing")
    try:
        gen_time = datetime.strptime(
            re.sub(r"\s+", " ", time_matches[0].strip()),
            "%b %d %H:%M:%S %Y GMT",
        ).replace(tzinfo=UTC)
    except ValueError:
        _fail(STABLE_CODES["external_anchor"], "signed timestamp format drifted")
    accuracy_delta, accuracy = _parse_accuracy(token_text)
    verify_time = str(int(gen_time.timestamp()))
    _run_ok(
        [
            TOOL_CONTRACT["openssl"]["path"],
            "ts",
            "-verify",
            "-queryfile",
            str(query_path),
            "-in",
            str(response_path),
            "-purpose",
            "timestampsign",
            "-x509_strict",
            "-verify_depth",
            "2",
            "-check_ss_sig",
            "-attime",
            verify_time,
            "-CAfile",
            str(repository_root / ROOT_CERT_PATH),
            "-untrusted",
            str(repository_root / INTERMEDIATE_CERT_PATH),
        ],
        code=STABLE_CODES["external_anchor"],
    )
    cms = _run_ok(
        [
            TOOL_CONTRACT["openssl"]["path"],
            "cms",
            "-cmsout",
            "-print",
            "-inform",
            "DER",
        ],
        input_bytes=token,
        code=STABLE_CODES["external_anchor"],
    ).decode("utf-8", errors="strict").casefold()
    signer_section = cms.partition("signerinfos:")[2]
    if not signer_section or signer_section.count("d.issuerandserialnumber:") != 1:
        _fail(STABLE_CODES["external_anchor"], "timestamp signer set drifted")
    if "d.subjectkeyidentifier:" in signer_section:
        _fail(STABLE_CODES["external_anchor"], "timestamp signer identifier drifted")
    serial_match = re.search(r"serialnumber:\s*(?:0x)?([0-9a-f]+)\b", signer_section)
    serial_normalized = TSA_RESPONDER_SERIAL.casefold().lstrip("0") or "0"
    if serial_match is None or (serial_match.group(1).lstrip("0") or "0") != serial_normalized:
        _fail(STABLE_CODES["external_anchor"], "timestamp signer serial drifted")
    certificates = _run_ok(
        [
            TOOL_CONTRACT["openssl"]["path"],
            "pkcs7",
            "-inform",
            "DER",
            "-in",
            "-",
            "-print_certs",
        ],
        input_bytes=token,
        code=STABLE_CODES["external_anchor"],
    )
    pem_blocks = re.findall(
        rb"-----BEGIN CERTIFICATE-----\s+([A-Za-z0-9+/=\r\n]+)-----END CERTIFICATE-----",
        certificates,
    )
    if not pem_blocks:
        _fail(STABLE_CODES["external_anchor"], "timestamp signer certificate missing")
    try:
        embedded_fingerprints = [
            _sha256_bytes(base64.b64decode(re.sub(rb"\s+", b"", block), validate=True))
            for block in pem_blocks
        ]
    except ValueError:
        _fail(STABLE_CODES["external_anchor"], "timestamp certificate encoding drifted")
    allowed_fingerprints = {
        TSA_RESPONDER_FINGERPRINT,
        TSA_INTERMEDIATE_FINGERPRINT,
        TSA_ROOT_FINGERPRINT,
    }
    if (
        len(embedded_fingerprints) != len(set(embedded_fingerprints))
        or TSA_RESPONDER_FINGERPRINT not in embedded_fingerprints
        or not set(embedded_fingerprints).issubset(allowed_fingerprints)
    ):
        _fail(STABLE_CODES["external_anchor"], "timestamp embedded certificate set drifted")
    trusted_start = gen_time + accuracy_delta
    earliest_possible = gen_time - accuracy_delta
    earliest = _canonical_utc(earliest_time)
    if earliest is None or earliest_possible < earliest:
        _fail(STABLE_CODES["external_anchor"], "timestamp predates exact-head CI")
    return {
        "endpoint": TSA_URL,
        "policy_oid": TSA_POLICY_OID,
        "message_imprint_algorithm": "sha256",
        "query_sha256": _sha256_file(
            query_path,
            code=STABLE_CODES["external_anchor"],
        ),
        "response_sha256": _sha256_file(
            response_path,
            code=STABLE_CODES["external_anchor"],
        ),
        "response_bytes": len(response),
        "pki_status": 0,
        "signature_verified": True,
        "chain_verified_at_signed_time": True,
        "revocation_checked": False,
        "long_term_validation": False,
        "responder_fingerprint_sha256": TSA_RESPONDER_FINGERPRINT,
        "intermediate_fingerprint_sha256": TSA_INTERMEDIATE_FINGERPRINT,
        "root_fingerprint_sha256": TSA_ROOT_FINGERPRINT,
        "responder_serial_hex": TSA_RESPONDER_SERIAL,
        "signed_gen_time": _format_utc(gen_time),
        "accuracy": accuracy,
        "earliest_possible_time": _format_utc(earliest_possible),
        "monitor_started_at": _format_utc(trusted_start),
    }


def _create_response_file(ns_fd: int) -> int:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open("anchor_response.tsr", flags, 0o600, dir_fd=ns_fd)
    except FileExistsError:
        _fail(STABLE_CODES["external_anchor"], "timestamp response already exists")
    except OSError as exc:
        _fail(STABLE_CODES["private_boundary"], f"response create failed: {type(exc).__name__}")
    os.fchmod(descriptor, 0o600)
    return descriptor


def _private_artifact_hashes(namespace: Path, *, exclude: set[str]) -> dict[str, str]:
    hashes: dict[str, str] = {}
    for name in sorted(NAMESPACE_FILES - {"objects"} - exclude):
        path = namespace / name
        if not path.is_file():
            _fail(STABLE_CODES["start_receipt"], f"private artifact missing: {name}")
        _owner_file_metadata(path, code=STABLE_CODES["private_boundary"])
        hashes[name] = _sha256_file(path, code=STABLE_CODES["start_receipt"])
    objects = namespace / "objects"
    _owner_directory_metadata(objects, code=STABLE_CODES["private_boundary"])
    if list(objects.iterdir()):
        _fail(STABLE_CODES["start_receipt"], "objects directory is not empty")
    return hashes


def _validate_existing_start(
    namespace: Path,
    *,
    repository_root: Path,
    authorization: Mapping[str, Any],
    namespace_fd: int,
) -> dict[str, Any]:
    _validate_directory_fd(namespace_fd)
    _assert_path_matches_fd(
        namespace,
        namespace_fd,
        code=STABLE_CODES["private_boundary"],
    )
    _owner_directory_metadata(namespace, code=STABLE_CODES["private_boundary"])
    expected_entries = set(NAMESPACE_FILES)
    actual_entries = {path.name for path in namespace.iterdir()}
    if actual_entries != expected_entries:
        _fail(STABLE_CODES["start_receipt"], "private namespace is partial or has extras")
    receipt_path = namespace / "monitor_start_receipt.json"
    _owner_file_metadata(receipt_path, code=STABLE_CODES["private_boundary"])
    receipt_raw = receipt_path.read_bytes()
    value = _load_exact_json_bytes(receipt_raw, code=STABLE_CODES["start_receipt"])
    if not isinstance(value, dict):
        _fail(STABLE_CODES["start_receipt"], "start receipt is not an object")
    receipt = value
    required = {
        "schema_version",
        "research_round",
        "authorization_id",
        "phase",
        "status",
        "authorization_commit",
        "authorization_receipt_sha256",
        "authorization_receipt_file_sha256",
        "start_intent_file_sha256",
        "monitor_started_at",
        "private_boundary",
        "remote_gate_proof_sha256",
        "account_zero_state_sha256",
        "ledger_heads",
        "tsa_anchor",
        "private_artifact_sha256",
        "state_boundary",
        "permission",
        "today_action",
        "receipt_sha256",
    }
    if (
        set(receipt) != required
        or receipt.get("schema_version") != START_SCHEMA
        or type(receipt.get("research_round")) is not int
        or receipt.get("research_round") != 45
        or receipt.get("authorization_id") != AUTHORIZATION_ID
        or receipt.get("phase") != "monitor_start"
        or receipt.get("status") != "monitor_started_collection_locked"
        or receipt.get("authorization_receipt_sha256")
        != authorization["receipt_sha256"]
        or receipt.get("authorization_receipt_file_sha256")
        != _sha256_file(repository_root / START_AUTHORIZATION_PATH)
        or not _typed_equal(receipt.get("state_boundary"), STATE_BOUNDARY)
        or not _typed_equal(receipt.get("permission"), PERMISSION)
        or receipt.get("today_action") != "今天不下單"
        or receipt.get("receipt_sha256")
        != canonical_sha256(receipt, omit="receipt_sha256")
        or receipt_raw != _pretty_json_bytes(receipt)
    ):
        _fail(STABLE_CODES["start_receipt"], "start receipt content drifted")
    artifacts = _private_artifact_hashes(namespace, exclude={"monitor_start_receipt.json"})
    if not _typed_equal(receipt.get("private_artifact_sha256"), artifacts):
        _fail(STABLE_CODES["start_receipt"], "private artifact hashes drifted")
    remote_raw = (namespace / "remote_gate_proof.json").read_bytes()
    remote_value = _load_exact_json_bytes(
        remote_raw,
        code=STABLE_CODES["remote_gate"],
    )
    account_raw = (namespace / "account_zero_state.json").read_bytes()
    account_value = _load_exact_json_bytes(
        account_raw,
        code=STABLE_CODES["non_engineering"],
    )
    if not isinstance(remote_value, dict) or not isinstance(account_value, dict):
        _fail(STABLE_CODES["start_receipt"], "private proof schema drifted")
    _validate_stored_remote_proof(remote_value)
    authorization_commit = remote_value["authorization_commit"]
    if receipt.get("authorization_commit") != authorization_commit:
        _fail(STABLE_CODES["start_receipt"], "authorization commit drifted")
    _assert_private_zero_state(account_value)
    if (
        account_value.get("authorization_commit") != authorization_commit
        or account_raw != _pretty_json_bytes(account_value)
    ):
        _fail(STABLE_CODES["non_engineering"], "account zero bytes drifted")
    if (
        receipt.get("remote_gate_proof_sha256") != remote_value.get("proof_sha256")
        or remote_raw != _pretty_json_bytes(remote_value)
    ):
        _fail(STABLE_CODES["start_receipt"], "remote proof hash drifted")
    if receipt.get("account_zero_state_sha256") != account_value.get("receipt_sha256"):
        _fail(STABLE_CODES["start_receipt"], "account zero hash drifted")
    volume_raw = (namespace / "volume_attestation.json").read_bytes()
    volume_value = _load_exact_json_bytes(
        volume_raw,
        code=STABLE_CODES["private_boundary"],
    )
    if not isinstance(volume_value, dict) or volume_raw != _pretty_json_bytes(volume_value):
        _fail(STABLE_CODES["private_boundary"], "volume attestation bytes drifted")
    _validate_volume_receipt(volume_value, private_root=namespace.parent)

    state_raw = (namespace / "monitor_state.json").read_bytes()
    state_value = _load_exact_json_bytes(state_raw, code=STABLE_CODES["non_engineering"])
    if (
        not isinstance(state_value, dict)
        or not _typed_equal(state_value, _monitor_state(authorization_commit))
        or state_raw != _pretty_json_bytes(state_value)
    ):
        _fail(STABLE_CODES["non_engineering"], "monitor locked state drifted")

    intent_raw = (namespace / "start_intent.json").read_bytes()
    intent_value = _load_exact_json_bytes(intent_raw, code=STABLE_CODES["start_receipt"])
    if not isinstance(intent_value, dict):
        _fail(STABLE_CODES["start_receipt"], "start intent schema drifted")
    _validate_start_intent(
        intent_value,
        raw=intent_raw,
        authorization=authorization,
        authorization_file_sha256=_sha256_file(repository_root / START_AUTHORIZATION_PATH),
        authorization_commit=authorization_commit,
        remote_proof=remote_value,
        remote_file_sha256=_sha256_bytes(remote_raw),
        volume=volume_value,
        volume_file_sha256=_sha256_bytes(volume_raw),
        account=account_value,
        account_file_sha256=_sha256_bytes(account_raw),
    )
    intent_file_sha256 = _sha256_bytes(intent_raw)
    if receipt.get("start_intent_file_sha256") != intent_file_sha256:
        _fail(STABLE_CODES["start_receipt"], "start intent file hash drifted")

    ledger_heads: dict[str, str] = {}
    ledger_records: dict[str, list[dict[str, Any]]] = {}
    for kind, filename in LEDGER_FILENAMES.items():
        records, head = _parse_chain(namespace / filename, expected_kind=kind)
        ledger_records[kind] = records
        ledger_heads[kind] = head
    if not _typed_equal(receipt.get("ledger_heads"), ledger_heads):
        _fail(STABLE_CODES["attempt_ledger"], "ledger heads drifted")
    current = remote_value.get("current")
    current_check = current.get("check") if isinstance(current, dict) else None
    completed_at = current_check.get("completed_at") if isinstance(current_check, dict) else None
    if not isinstance(completed_at, str):
        _fail(STABLE_CODES["remote_gate"], "remote completion proof missing")
    anchor = _verify_anchor(
        query_path=namespace / "anchor_request.tsq",
        response_path=namespace / "anchor_response.tsr",
        repository_root=repository_root,
        earliest_time=completed_at,
        expected_intent_sha256=intent_file_sha256,
    )
    if not _typed_equal(receipt.get("tsa_anchor"), anchor) or not _typed_equal(
        receipt.get("monitor_started_at"), anchor["monitor_started_at"]
    ):
        _fail(STABLE_CODES["external_anchor"], "start anchor drifted")

    query_sha256 = _sha256_file(namespace / "anchor_request.tsq")
    for kind in LEDGER_KINDS:
        expected_records = (
            _expected_audit_records(
                authorization_commit,
                query_sha256=query_sha256,
                anchor=anchor,
            )
            if kind == "audit"
            else [_genesis_record(kind, authorization_commit)]
        )
        if not _typed_equal(ledger_records[kind], expected_records):
            _fail(STABLE_CODES["attempt_ledger"], f"{kind} ledger semantics drifted")

    exchange_raw = (namespace / "anchor_exchange.json").read_bytes()
    exchange_value = _load_exact_json_bytes(
        exchange_raw,
        code=STABLE_CODES["external_anchor"],
    )
    expected_http = {
        "http_status": 200,
        "content_type": TSA_CONTRACT["response_content_type"],
        "response_bytes": anchor["response_bytes"],
        "redirect_count": 0,
        "request_count": 1,
        "retry_count": 0,
        "proxy_used": False,
    }
    if (
        not isinstance(exchange_value, dict)
        or set(exchange_value)
        != {"schema_version", "authorization_id", "http", "anchor", "exchange_sha256"}
        or exchange_value.get("schema_version")
        != "us_fddk.short_term_form4_anchor_exchange.v1"
        or exchange_value.get("authorization_id") != AUTHORIZATION_ID
        or not _typed_equal(exchange_value.get("http"), expected_http)
        or not _typed_equal(exchange_value.get("anchor"), anchor)
        or exchange_value.get("exchange_sha256")
        != canonical_sha256(exchange_value, omit="exchange_sha256")
        or exchange_raw != _pretty_json_bytes(exchange_value)
    ):
        _fail(STABLE_CODES["external_anchor"], "anchor exchange drifted")

    expected_private_boundary = {
        "private_root_path_sha256": PRIVATE_ROOT_PATH_SHA256,
        "volume_uuid_sha256": volume_value["volume_uuid_sha256"],
        "st_dev": volume_value["st_dev"],
        "st_ino": volume_value["st_ino"],
        "owner_uid": volume_value["owner_uid"],
        "directory_mode": "0700",
        "file_mode": "0600",
        "filevault": True,
        "encryption": True,
        "repository_external": True,
    }
    if not _typed_equal(receipt.get("private_boundary"), expected_private_boundary):
        _fail(STABLE_CODES["private_boundary"], "start private boundary drifted")
    _assert_path_matches_fd(
        namespace,
        namespace_fd,
        code=STABLE_CODES["private_boundary"],
    )
    return receipt


def start_form4_monitor(
    *,
    repository_root: str | Path,
    authorization_path: str | Path,
    private_root: str | Path,
) -> dict[str, Any]:
    """Create one externally timestamped monitor start; never enables SEC access."""

    root = Path(repository_root).resolve()
    private = Path(private_root)
    authorization = validate_monitor_start_authorization(
        authorization_path,
        repository_root=root,
    )
    authorization_file_sha256 = _sha256_file(root / START_AUTHORIZATION_PATH)
    _validate_tool_contract()
    _validate_private_location(private, root)
    _validate_tsa_assets(root)

    parent_fd = _open_directory_fd(private.parent)
    root_fd = -1
    try:
        _validate_directory_fd(parent_fd)
        _mkdir_at(parent_fd, private.name)
        root_fd = _open_child_directory_fd(parent_fd, private.name)
    finally:
        os.close(parent_fd)
    _owner_directory_metadata(private, code=STABLE_CODES["private_boundary"])
    volume = _volume_attestation(private)
    volume["attestation_sha256"] = canonical_sha256(volume, omit="attestation_sha256")

    lock_fd = -1
    try:
        _validate_directory_fd(root_fd)
        _assert_path_matches_fd(private, root_fd, code=STABLE_CODES["private_boundary"])
        lock_fd = _open_lock(root_fd)
        lock_path = private / ".monitor-start.lock"
        _owner_file_metadata(lock_path, code=STABLE_CODES["private_boundary"])
        _assert_path_matches_fd(
            lock_path,
            lock_fd,
            code=STABLE_CODES["private_boundary"],
        )
        _validate_volume_receipt(volume, private_root=private)
        allowed_root_entries = {".monitor-start.lock", AUTHORIZATION_ID}
        root_entries = set(os.listdir(root_fd))
        if not root_entries.issubset(allowed_root_entries):
            _fail(STABLE_CODES["already_started"], "private root contains another authorization")
        namespace = private / AUTHORIZATION_ID
        if AUTHORIZATION_ID in root_entries:
            namespace_fd = _open_child_directory_fd(root_fd, AUTHORIZATION_ID)
            try:
                _validate_directory_fd(namespace_fd)
                _assert_path_matches_fd(
                    namespace,
                    namespace_fd,
                    code=STABLE_CODES["private_boundary"],
                )
                _owner_directory_metadata(namespace, code=STABLE_CODES["private_boundary"])
                final = namespace / "monitor_start_receipt.json"
                if final.is_file():
                    return _validate_existing_start(
                        namespace,
                        repository_root=root,
                        authorization=authorization,
                        namespace_fd=namespace_fd,
                    )
            finally:
                os.close(namespace_fd)
            _fail(STABLE_CODES["start_receipt"], "partial start is permanently stopped")

        remote_proof = collect_remote_gate_proof(root)
        _validate_stored_remote_proof(remote_proof)
        authorization_commit = str(remote_proof["authorization_commit"])
        if not _mkdir_at(root_fd, AUTHORIZATION_ID):
            _fail(STABLE_CODES["already_started"], "authorization namespace raced")
        _owner_directory_metadata(namespace, code=STABLE_CODES["private_boundary"])
        namespace_fd = _open_child_directory_fd(root_fd, AUTHORIZATION_ID)
        try:
            _validate_directory_fd(namespace_fd)
            _assert_path_matches_fd(
                namespace,
                namespace_fd,
                code=STABLE_CODES["private_boundary"],
            )
            if not _mkdir_at(namespace_fd, "objects"):
                _fail(STABLE_CODES["start_receipt"], "objects directory collision")
            ledger_heads: dict[str, str] = {}
            ledger_hashes: dict[str, str] = {}
            for kind, filename in LEDGER_FILENAMES.items():
                genesis = _genesis_record(kind, authorization_commit)
                ledger_heads[kind] = str(genesis["entry_sha256"])
                ledger_hashes[kind] = _write_create_at(
                    namespace_fd,
                    filename,
                    _jsonl_line(genesis),
                )
            zero_state = _account_zero_state(authorization_commit)
            zero_sha = _write_create_at(
                namespace_fd,
                "account_zero_state.json",
                _pretty_json_bytes(zero_state),
            )
            volume_sha = _write_create_at(
                namespace_fd,
                "volume_attestation.json",
                _pretty_json_bytes(volume),
            )
            remote_sha = _write_create_at(
                namespace_fd,
                "remote_gate_proof.json",
                _pretty_json_bytes(remote_proof),
            )
            prepared_at = _format_utc(datetime.now(UTC))
            host_material = "\0".join(
                [platform.node(), str(os.getuid()), str(volume["volume_uuid"])]
            ).encode("utf-8")
            intent: dict[str, Any] = {
                "schema_version": "us_fddk.short_term_form4_start_intent.v1",
                "authorization_id": AUTHORIZATION_ID,
                "authorization_commit": authorization_commit,
                "authorization_receipt_sha256": authorization["receipt_sha256"],
                "authorization_receipt_file_sha256": authorization_file_sha256,
                "prepared_at_untrusted_local": prepared_at,
                "host_identity_sha256": _sha256_bytes(host_material),
                "remote_gate_proof_file_sha256": remote_sha,
                "remote_gate_proof_sha256": remote_proof["proof_sha256"],
                "volume_attestation_file_sha256": volume_sha,
                "volume_attestation_sha256": volume["attestation_sha256"],
                "account_zero_state_file_sha256": zero_sha,
                "account_zero_state_sha256": zero_state["receipt_sha256"],
                "genesis_file_sha256": ledger_hashes,
                "genesis_chain_heads": ledger_heads,
                "objects_count": 0,
                "tsa_contract": dict(TSA_CONTRACT),
                "state_boundary": dict(STATE_BOUNDARY),
                "permission": dict(PERMISSION),
                "intent_sha256": "",
            }
            intent["intent_sha256"] = canonical_sha256(intent, omit="intent_sha256")
            intent_bytes = _pretty_json_bytes(intent)
            _write_create_at(namespace_fd, "start_intent.json", intent_bytes)
            query = _generate_anchor_query(_sha256_bytes(intent_bytes), root)
            query_sha = _write_create_at(namespace_fd, "anchor_request.tsq", query)
            audit_path = namespace / LEDGER_FILENAMES["audit"]
            _append_chain_entry(
                audit_path,
                kind="audit",
                event="tsa_request_started",
                fields={
                    "endpoint_sha256": _sha256_bytes(TSA_URL.encode("ascii")),
                    "query_sha256": query_sha,
                    "request_ordinal": 1,
                    "retry_count": 0,
                },
                parent_fd=namespace_fd,
            )
            response_fd = _create_response_file(namespace_fd)
            response_path = namespace / "anchor_response.tsr"
            try:
                _assert_path_matches_fd(
                    namespace,
                    namespace_fd,
                    code=STABLE_CODES["private_boundary"],
                )
                _assert_path_matches_fd(
                    response_path,
                    response_fd,
                    code=STABLE_CODES["private_boundary"],
                )
                _validate_volume_receipt(volume, private_root=private)
                http_receipt = _post_anchor_once(query, response_fd)
                os.fsync(response_fd)
                _assert_path_matches_fd(
                    namespace,
                    namespace_fd,
                    code=STABLE_CODES["private_boundary"],
                )
                _assert_path_matches_fd(
                    response_path,
                    response_fd,
                    code=STABLE_CODES["private_boundary"],
                )
                response_metadata = os.fstat(response_fd)
                if (
                    not stat.S_ISREG(response_metadata.st_mode)
                    or stat.S_IMODE(response_metadata.st_mode) != 0o600
                    or response_metadata.st_uid != os.getuid()
                    or response_metadata.st_nlink != 1
                ):
                    _fail(STABLE_CODES["private_boundary"], "timestamp response metadata drifted")
            finally:
                os.close(response_fd)
            os.fsync(namespace_fd)
            if response_path.stat().st_size != http_receipt["response_bytes"]:
                _fail(STABLE_CODES["external_anchor"], "timestamp byte count drifted")
            current = remote_proof.get("current")
            current_check = current.get("check") if isinstance(current, dict) else None
            completed_at = (
                current_check.get("completed_at") if isinstance(current_check, dict) else None
            )
            if not isinstance(completed_at, str):
                _fail(STABLE_CODES["remote_gate"], "current CI completion proof missing")
            anchor = _verify_anchor(
                query_path=namespace / "anchor_request.tsq",
                response_path=response_path,
                repository_root=root,
                earliest_time=completed_at,
                expected_intent_sha256=_sha256_bytes(intent_bytes),
            )
            _append_chain_entry(
                audit_path,
                kind="audit",
                event="tsa_response_verified",
                fields={
                    "response_sha256": anchor["response_sha256"],
                    "signed_gen_time": anchor["signed_gen_time"],
                    "monitor_started_at": anchor["monitor_started_at"],
                    "request_ordinal": 1,
                },
                parent_fd=namespace_fd,
            )
            exchange: dict[str, Any] = {
                "schema_version": "us_fddk.short_term_form4_anchor_exchange.v1",
                "authorization_id": AUTHORIZATION_ID,
                "http": http_receipt,
                "anchor": anchor,
                "exchange_sha256": "",
            }
            exchange["exchange_sha256"] = canonical_sha256(
                exchange, omit="exchange_sha256"
            )
            _write_create_at(
                namespace_fd,
                "anchor_exchange.json",
                _pretty_json_bytes(exchange),
            )
            state = _monitor_state(authorization_commit)
            _write_create_at(
                namespace_fd,
                "monitor_state.json",
                _pretty_json_bytes(state),
            )
            ledger_heads = {
                kind: _parse_chain(namespace / filename, expected_kind=kind)[1]
                for kind, filename in LEDGER_FILENAMES.items()
            }
            artifact_hashes = _private_artifact_hashes(
                namespace,
                exclude={"monitor_start_receipt.json"},
            )
            start_receipt: dict[str, Any] = {
                "schema_version": START_SCHEMA,
                "research_round": 45,
                "authorization_id": AUTHORIZATION_ID,
                "phase": "monitor_start",
                "status": "monitor_started_collection_locked",
                "authorization_commit": authorization_commit,
                "authorization_receipt_sha256": authorization["receipt_sha256"],
                "authorization_receipt_file_sha256": authorization_file_sha256,
                "start_intent_file_sha256": _sha256_bytes(intent_bytes),
                "monitor_started_at": anchor["monitor_started_at"],
                "private_boundary": {
                    "private_root_path_sha256": volume["private_root_path_sha256"],
                    "volume_uuid_sha256": volume["volume_uuid_sha256"],
                    "st_dev": volume["st_dev"],
                    "st_ino": volume["st_ino"],
                    "owner_uid": volume["owner_uid"],
                    "directory_mode": "0700",
                    "file_mode": "0600",
                    "filevault": True,
                    "encryption": True,
                    "repository_external": True,
                },
                "remote_gate_proof_sha256": remote_proof["proof_sha256"],
                "account_zero_state_sha256": zero_state["receipt_sha256"],
                "ledger_heads": ledger_heads,
                "tsa_anchor": anchor,
                "private_artifact_sha256": artifact_hashes,
                "state_boundary": dict(STATE_BOUNDARY),
                "permission": dict(PERMISSION),
                "today_action": "今天不下單",
                "receipt_sha256": "",
            }
            start_receipt["receipt_sha256"] = canonical_sha256(
                start_receipt, omit="receipt_sha256"
            )
            _write_create_at(
                namespace_fd,
                "monitor_start_receipt.json",
                _pretty_json_bytes(start_receipt),
            )
            return _validate_existing_start(
                namespace,
                repository_root=root,
                authorization=authorization,
                namespace_fd=namespace_fd,
            )
        finally:
            os.close(namespace_fd)
    finally:
        if lock_fd >= 0:
            fcntl.flock(lock_fd, fcntl.LOCK_UN)
            os.close(lock_fd)
        os.close(root_fd)


def assert_sec_collection_locked() -> None:
    raise Form4MonitorStartError(
        STABLE_CODES["live_network"],
        "Round45 monitor start cannot issue SEC collection capability",
    )
