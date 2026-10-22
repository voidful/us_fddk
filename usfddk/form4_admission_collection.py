from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import subprocess
from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .form4_admission_feasibility import (
    FIXED_QUARTERS,
    Form4AdmissionFeasibilityError,
    _daily_index_row,
    _load_protocol_binding,
    _parse_quarter_zip,
    audit_form4_admission_feasibility,
    build_form4_feasibility_failure_receipt,
)
from .sec_edgar_client import SecEdgarClient, SecEdgarClientError

AUTHORIZATION_SCHEMA = "us_fddk.short_term_form4_collection_authorization.v1"
PRIVATE_MANIFEST_SCHEMA = "us_fddk.short_term_form4_admission_private_manifest.v1"
SELECTION_PLAN_SCHEMA = "us_fddk.short_term_form4_selection_plan.v1"
MAX_REQUESTS = 28
MAX_DAILY_INDEX_REQUESTS = 12
MAX_COMPLETE_SUBMISSION_REQUESTS = 12
COLLECTION_BINDING_KEYS = frozenset(
    {
        "protocol_v1",
        "protocol_receipt_v1",
        "schema_amendment_v1_1",
        "schema_amendment_receipt_v1_1",
        "sec_client",
        "feasibility_verifier",
        "collection_implementation",
        "collection_runner",
        "collection_tests",
    }
)

AUTHORIZATION_KEYS = frozenset(
    {
        "schema_version",
        "research_round",
        "status",
        "frozen_at",
        "authorization_id",
        "user_scope",
        "parent_code_commit",
        "remote_ref",
        "bindings",
        "fixed_collection",
        "privacy",
        "state_boundary",
        "receipt_sha256",
    }
)
PRIVATE_MANIFEST_KEYS = frozenset(
    {
        "schema_version",
        "created_at",
        "authorization_receipt_sha256",
        "environment",
        "selection_plan_sha256",
        "quarter_receipts",
        "filing_evidence",
        "sample_count",
        "request_count",
        "attempt_ledger_sha256",
        "state_boundary",
    }
)

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_ACCESSION_ANYWHERE = re.compile(r"(?<!\d)\d{10}-\d{2}-\d{6}(?!\d)")
_EMAIL_ANYWHERE = re.compile(r"[\w.+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_FORBIDDEN_PUBLIC_KEY_PARTS = (
    "accession",
    "actor",
    "cik",
    "issuer",
    "owner",
    "person",
    "raw_text",
    "symbol",
    "ticker",
    "url",
)


class Form4CollectionError(RuntimeError):
    """Fail-closed authorized collection error with a stable private code."""

    def __init__(self, code: str, detail: str):
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}")


def _fail(code: str, detail: str) -> None:
    raise Form4CollectionError(code, detail)


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical_hash(payload: Mapping[str, Any], *, omit: str | None = None) -> str:
    value = {key: item for key, item in payload.items() if key != omit}
    rendered = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return _sha256_bytes(rendered)


def _json_bytes(payload: Mapping[str, Any]) -> bytes:
    return (
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def _validate_owner_directory(path: Path, *, code: str) -> None:
    try:
        metadata = path.lstat()
    except OSError as exc:
        _fail(code, type(exc).__name__)
    if (
        not stat.S_ISDIR(metadata.st_mode)
        or stat.S_IMODE(metadata.st_mode) != 0o700
        or metadata.st_uid != os.getuid()
        or metadata.st_nlink < 1
    ):
        _fail(code, "directory must be owner-only and non-symlink")


def _validate_owner_file(path: Path, *, code: str) -> None:
    try:
        metadata = path.lstat()
    except OSError as exc:
        _fail(code, type(exc).__name__)
    if (
        not stat.S_ISREG(metadata.st_mode)
        or stat.S_IMODE(metadata.st_mode) != 0o600
        or metadata.st_uid != os.getuid()
        or metadata.st_nlink != 1
    ):
        _fail(code, "file must be an owner-only regular file with one link")


def _write_private_json_create(path: Path, payload: Mapping[str, Any]) -> str:
    _validate_owner_directory(path.parent, code="form4_collection_private_boundary_invalid")
    rendered = _json_bytes(payload)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(path, flags, 0o600)
    except FileExistsError:
        _fail("form4_collection_append_only_collision", "private artifact already exists")
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(rendered)
            handle.flush()
            os.fsync(handle.fileno())
    except BaseException:
        try:
            path.unlink()
        except OSError:
            pass
        raise
    _validate_owner_file(path, code="form4_collection_private_boundary_invalid")
    return _sha256_bytes(rendered)


def _append_private_jsonl(path: Path, payload: Mapping[str, Any]) -> None:
    _validate_owner_directory(path.parent, code="form4_collection_private_boundary_invalid")
    flags = os.O_WRONLY | os.O_CREAT | os.O_APPEND
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(path, flags, 0o600)
    except OSError as exc:
        _fail("form4_collection_attempt_ledger_invalid", type(exc).__name__)
    try:
        metadata = os.fstat(descriptor)
        if (
            not stat.S_ISREG(metadata.st_mode)
            or stat.S_IMODE(metadata.st_mode) != 0o600
            or metadata.st_uid != os.getuid()
            or metadata.st_nlink != 1
        ):
            _fail("form4_collection_attempt_ledger_invalid", "attempt ledger is not private")
        rendered = json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8") + b"\n"
        os.write(descriptor, rendered)
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _load_json(path: Path, *, owner_only: bool, code: str) -> dict[str, Any]:
    if owner_only:
        _validate_owner_file(path, code=code)
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        _fail(code, type(exc).__name__)
    if not isinstance(value, dict):
        _fail(code, "JSON root must be an object")
    return value


def validate_collection_authorization(
    authorization_path: str | Path,
    *,
    repository_root: str | Path,
) -> dict[str, Any]:
    root = Path(repository_root).resolve()
    path = Path(authorization_path).resolve()
    try:
        path.relative_to(root)
    except ValueError:
        _fail("form4_collection_authorization_invalid", "authorization must be inside Git")
    authorization = _load_json(
        path,
        owner_only=False,
        code="form4_collection_authorization_invalid",
    )
    fixed = authorization.get("fixed_collection", {})
    boundary = authorization.get("state_boundary", {})
    privacy = authorization.get("privacy", {})
    frozen_at = authorization.get("frozen_at")
    try:
        parsed_frozen_at = datetime.fromisoformat(str(frozen_at).replace("Z", "+00:00"))
        canonical_frozen_at = parsed_frozen_at.astimezone(UTC).replace(
            microsecond=0
        ).isoformat().replace("+00:00", "Z")
    except (TypeError, ValueError):
        canonical_frozen_at = ""
    if (
        set(authorization) != AUTHORIZATION_KEYS
        or authorization.get("schema_version") != AUTHORIZATION_SCHEMA
        or authorization.get("research_round") != 42
        or authorization.get("status") != "authorized_once_before_sec_fetch"
        or not isinstance(frozen_at, str)
        or canonical_frozen_at != frozen_at
        or not isinstance(authorization.get("authorization_id"), str)
        or re.fullmatch(
            r"round42-form4-admission-[a-z0-9-]{8,48}",
            str(authorization.get("authorization_id")),
        )
        is None
        or not isinstance(authorization.get("user_scope"), str)
        or not str(authorization.get("user_scope")).strip()
        or not isinstance(authorization.get("remote_ref"), str)
        or not str(authorization.get("remote_ref")).startswith("origin/codex/")
        or authorization.get("receipt_sha256")
        != _canonical_hash(authorization, omit="receipt_sha256")
        or fixed
        != {
            "fixed_quarters": list(FIXED_QUARTERS),
            "catalog_requests": 1,
            "quarter_zip_requests": 3,
            "daily_index_requests_max": MAX_DAILY_INDEX_REQUESTS,
            "complete_submission_requests_max": MAX_COMPLETE_SUBMISSION_REQUESTS,
            "total_requests_max": MAX_REQUESTS,
            "automatic_retries": 0,
            "resampling_allowed": False,
            "next_day_index_fallback_allowed": False,
        }
        or boundary.get("candidate_selection_count") != 0
        or boundary.get("strategy_run_count") != 0
        or boundary.get("performance_result_present") is not False
        or boundary.get("paper_authorized") is not False
        or boundary.get("real_money_action_usd") != 0
        or privacy
        != {
            "quarantine_repository_external": True,
            "filevault_required": True,
            "directory_mode": "0700",
            "file_mode": "0600",
            "public_identifiers_allowed": False,
        }
    ):
        _fail("form4_collection_authorization_invalid", "authorization schema drifted")
    bindings = authorization.get("bindings")
    if not isinstance(bindings, dict) or set(bindings) != COLLECTION_BINDING_KEYS:
        _fail("form4_collection_authorization_invalid", "authorization bindings missing")
    for binding in bindings.values():
        if not isinstance(binding, dict) or set(binding) != {"path", "sha256"}:
            _fail("form4_collection_authorization_invalid", "binding schema drifted")
        relative = binding["path"]
        digest = binding["sha256"]
        if not isinstance(relative, str) or not isinstance(digest, str):
            _fail("form4_collection_authorization_invalid", "binding identity invalid")
        candidate = (root / relative).resolve()
        try:
            candidate.relative_to(root)
        except ValueError:
            _fail("form4_collection_authorization_invalid", "binding escaped repository")
        if not candidate.is_file() or _sha256_file(candidate) != digest:
            _fail("form4_collection_authorization_invalid", "bound implementation drifted")
    parent_commit = authorization.get("parent_code_commit")
    if not isinstance(parent_commit, str) or re.fullmatch(r"[0-9a-f]{40}", parent_commit) is None:
        _fail("form4_collection_authorization_invalid", "parent commit invalid")
    ancestry = subprocess.run(
        ["git", "merge-base", "--is-ancestor", parent_commit, "HEAD"],
        cwd=root,
        capture_output=True,
        check=False,
    )
    if ancestry.returncode != 0:
        _fail("form4_collection_authorization_invalid", "authorization parent is not an ancestor")
    return authorization


def _environment_attestation(quarantine: Path, repository_root: Path) -> dict[str, Any]:
    root = repository_root.resolve()
    resolved = quarantine.resolve()
    if not quarantine.is_absolute() or quarantine.is_symlink():
        _fail("form4_collection_private_boundary_invalid", "quarantine path is unsafe")
    try:
        resolved.relative_to(root)
    except ValueError:
        pass
    else:
        _fail("form4_collection_private_boundary_invalid", "quarantine is inside repository")
    _validate_owner_directory(resolved, code="form4_collection_private_boundary_invalid")
    completed = subprocess.run(
        ["fdesetup", "status"],
        capture_output=True,
        check=False,
        text=True,
        timeout=10,
    )
    output = completed.stdout.strip()
    if completed.returncode != 0 or output != "FileVault is On.":
        _fail("form4_collection_filevault_not_verified", "FileVault status is not enabled")
    return {
        "filevault_enabled": True,
        "filevault_status_sha256": _sha256_bytes((output + "\n").encode("utf-8")),
        "repository_external": True,
        "quarantine_owner_uid": os.getuid(),
        "quarantine_mode": "0700",
        "source_receipts_claim_encryption": False,
    }


def _collection_directory(client: SecEdgarClient, authorization: Mapping[str, Any]) -> Path:
    name = f"round42-{authorization['authorization_id']}"
    path = client.quarantine / name
    if not path.exists():
        path.mkdir(mode=0o700)
    _validate_owner_directory(path, code="form4_collection_private_boundary_invalid")
    return path


def _request(
    ledger: Path,
    ordinal: int,
    label: str,
    call: Callable[[], Any],
) -> Any:
    _append_private_jsonl(
        ledger,
        {"ordinal": ordinal, "phase": "started", "source_label": label},
    )
    try:
        result = call()
    except (SecEdgarClientError, Form4AdmissionFeasibilityError) as exc:
        _append_private_jsonl(
            ledger,
            {
                "ordinal": ordinal,
                "phase": "failed",
                "source_label": label,
                "error_code": exc.code,
            },
        )
        raise
    receipt = result.get("receipt") if isinstance(result, dict) and "receipt" in result else result
    receipt_hash = receipt.get("receipt_sha256") if isinstance(receipt, Mapping) else None
    _append_private_jsonl(
        ledger,
        {
            "ordinal": ordinal,
            "phase": "completed",
            "source_label": label,
            "receipt_sha256": receipt_hash,
        },
    )
    return result


def collect_authorized_form4_sample(
    *,
    repository_root: str | Path,
    quarantine: str | Path,
    authorization_path: str | Path,
    user_agent: str | None = None,
) -> Path:
    root = Path(repository_root).resolve()
    authorization = validate_collection_authorization(
        authorization_path,
        repository_root=root,
    )
    client = SecEdgarClient(
        Path(quarantine),
        repository_root=root,
        user_agent=user_agent,
    )
    environment = _environment_attestation(client.quarantine, root)
    private_dir = _collection_directory(client, authorization)
    authorization_id = str(authorization["authorization_id"])
    started = private_dir / "collection_started.json"
    ledger = private_dir / "attempt_ledger.jsonl"
    selection_path = private_dir / "selection_plan.json"
    manifest_path = private_dir / "private_manifest.json"
    if any(path.exists() for path in (started, ledger, selection_path, manifest_path)):
        _fail(
            "form4_collection_already_started",
            "one-shot authorization already has a private checkpoint",
        )
    _write_private_json_create(
        started,
        {
            "schema_version": 1,
            "authorization_id": authorization_id,
            "authorization_receipt_sha256": authorization["receipt_sha256"],
            "started_at": _utc_now(),
            "network_requests_completed": 0,
        },
    )
    request_count = 1
    catalog = _request(ledger, request_count, "catalog", client.fetch_catalog)
    quarter_receipts: dict[str, dict[str, Any]] = {}
    for quarter_id in FIXED_QUARTERS:
        year = int(quarter_id[:4])
        quarter = int(quarter_id[-1])
        request_count += 1
        result = _request(
            ledger,
            request_count,
            f"quarter_{quarter_id}",
            lambda year=year, quarter=quarter: client.fetch_quarter(year, quarter),
        )
        quarter_receipts[quarter_id] = dict(result["receipt"])
    if catalog.get("strategy_defined_or_run") is not False or request_count != 4:
        _fail("form4_collection_request_plan_drifted", "catalog or quarter request plan drifted")
    binding = _load_protocol_binding(root)
    required_headers = binding["receipt"]["quarterly_zip_contract"]["required_tables"]
    parsed_quarters = {
        quarter_id: _parse_quarter_zip(
            client,
            quarter_id,
            receipt,
            required_headers=required_headers,
            amendment_receipt=binding["amendment_receipt"],
        )
        for quarter_id, receipt in quarter_receipts.items()
    }
    samples = [
        {
            "quarter": quarter_id,
            "sample_role": sample["sample_role"],
            "accession": sample["ACCESSION_NUMBER"],
            "form": sample["DOCUMENT_TYPE"],
            "filing_date": sample["normalized_FILING_DATE"],
            "issuer_cik": sample["ISSUERCIK"],
        }
        for quarter_id in FIXED_QUARTERS
        for sample in parsed_quarters[quarter_id]["samples"]
    ]
    samples.sort(key=lambda item: (FIXED_QUARTERS.index(item["quarter"]), item["filing_date"], item["accession"]))
    if not 9 <= len(samples) <= 12:
        _fail("form4_collection_selection_plan_invalid", "sample count is outside 9..12")
    selection_plan = {
        "schema_version": SELECTION_PLAN_SCHEMA,
        "authorization_receipt_sha256": authorization["receipt_sha256"],
        "fixed_quarters": list(FIXED_QUARTERS),
        "sample_count": len(samples),
        "samples": samples,
        "candidate_selection_count": 0,
        "strategy_run_count": 0,
        "performance_result_present": False,
    }
    selection_sha256 = _write_private_json_create(selection_path, selection_plan)
    daily_receipts: dict[str, dict[str, Any]] = {}
    filing_evidence: dict[str, dict[str, Any]] = {}
    for sample in samples:
        filing_date = sample["filing_date"]
        if filing_date not in daily_receipts:
            if len(daily_receipts) >= MAX_DAILY_INDEX_REQUESTS:
                _fail("form4_collection_request_limit_exceeded", "daily index request cap reached")
            request_count += 1
            daily_receipts[filing_date] = dict(
                _request(
                    ledger,
                    request_count,
                    "daily_form_index",
                    lambda filing_date=filing_date: client.fetch_daily_form_index(filing_date),
                )
            )
        daily_receipt = daily_receipts[filing_date]
        daily_row = _daily_index_row(
            client.object_bytes(daily_receipt),
            accession=sample["accession"],
            form=sample["form"],
            filing_date=filing_date,
        )
        if len(filing_evidence) >= MAX_COMPLETE_SUBMISSION_REQUESTS:
            _fail("form4_collection_request_limit_exceeded", "submission request cap reached")
        request_count += 1
        complete = _request(
            ledger,
            request_count,
            "complete_submission",
            lambda daily_row=daily_row, sample=sample, daily_receipt=daily_receipt: (
                client.fetch_complete_submission(
                    daily_row["cik"],
                    sample["accession"],
                    daily_index_receipt=daily_receipt,
                )
            ),
        )
        filing_evidence[sample["accession"]] = {
            "daily_index_receipt": daily_receipt,
            "complete_submission_receipt": complete,
        }
    if request_count > MAX_REQUESTS or len(filing_evidence) != len(samples):
        _fail("form4_collection_request_limit_exceeded", "final request count drifted")
    manifest = {
        "schema_version": PRIVATE_MANIFEST_SCHEMA,
        "created_at": _utc_now(),
        "authorization_receipt_sha256": authorization["receipt_sha256"],
        "environment": environment,
        "selection_plan_sha256": selection_sha256,
        "quarter_receipts": quarter_receipts,
        "filing_evidence": filing_evidence,
        "sample_count": len(samples),
        "request_count": request_count,
        "attempt_ledger_sha256": _sha256_file(ledger),
        "state_boundary": {
            "authorized_real_form4_rows": 0,
            "candidate_selection_count": 0,
            "strategy_run_count": 0,
            "performance_result_present": False,
            "paper_authorized": False,
            "real_money_action_usd": 0,
        },
    }
    _write_private_json_create(manifest_path, manifest)
    return manifest_path


def _network_disabled(*args: object, **kwargs: object) -> Any:
    del args, kwargs
    _fail("form4_collection_replay_network_forbidden", "cold replay attempted network access")


def _sanitize_public_receipt(payload: Mapping[str, Any]) -> None:
    def walk(value: Any, path: tuple[str, ...] = ()) -> None:
        if isinstance(value, Mapping):
            for key, item in value.items():
                lowered = str(key).casefold()
                if lowered != "private_manifest_sha256" and any(
                    token in lowered for token in _FORBIDDEN_PUBLIC_KEY_PARTS
                ):
                    _fail("form4_collection_public_boundary_breached", "forbidden public key")
                walk(item, (*path, str(key)))
        elif isinstance(value, list):
            for item in value:
                walk(item, path)
        elif isinstance(value, str):
            if (
                _ACCESSION_ANYWHERE.search(value)
                or _EMAIL_ANYWHERE.search(value)
                or "edgar/data/" in value.casefold()
                or "https://" in value.casefold()
            ):
                _fail("form4_collection_public_boundary_breached", "identifier-like public value")

    walk(payload)


def replay_authorized_form4_sample(
    *,
    repository_root: str | Path,
    quarantine: str | Path,
    authorization_path: str | Path,
    private_manifest_path: str | Path,
    user_agent: str | None = None,
) -> dict[str, Any]:
    root = Path(repository_root).resolve()
    authorization = validate_collection_authorization(
        authorization_path,
        repository_root=root,
    )
    manifest_path = Path(private_manifest_path).resolve()
    quarantine_path = Path(quarantine).resolve()
    try:
        manifest_path.relative_to(quarantine_path)
    except ValueError:
        _fail(
            "form4_collection_private_manifest_invalid",
            "private manifest is outside the authorized quarantine",
        )
    manifest = _load_json(
        manifest_path,
        owner_only=True,
        code="form4_collection_private_manifest_invalid",
    )
    manifest_sha256 = _sha256_file(manifest_path)
    sample_count = manifest.get("sample_count")
    request_count = manifest.get("request_count")
    quarter_receipts = manifest.get("quarter_receipts")
    filing_evidence = manifest.get("filing_evidence")
    selection_hash = manifest.get("selection_plan_sha256")
    attempt_hash = manifest.get("attempt_ledger_sha256")
    selection_path = manifest_path.with_name("selection_plan.json")
    attempt_path = manifest_path.with_name("attempt_ledger.jsonl")
    if not selection_path.is_file() or not attempt_path.is_file():
        _fail("form4_collection_private_manifest_invalid", "private replay seal is missing")
    _validate_owner_file(
        selection_path,
        code="form4_collection_private_manifest_invalid",
    )
    _validate_owner_file(
        attempt_path,
        code="form4_collection_private_manifest_invalid",
    )
    if (
        set(manifest) != PRIVATE_MANIFEST_KEYS
        or manifest.get("schema_version") != PRIVATE_MANIFEST_SCHEMA
        or manifest.get("authorization_receipt_sha256") != authorization["receipt_sha256"]
        or manifest.get("state_boundary")
        != {
            "authorized_real_form4_rows": 0,
            "candidate_selection_count": 0,
            "strategy_run_count": 0,
            "performance_result_present": False,
            "paper_authorized": False,
            "real_money_action_usd": 0,
        }
        or isinstance(sample_count, bool)
        or not isinstance(sample_count, int)
        or not 9 <= sample_count <= 12
        or isinstance(request_count, bool)
        or not isinstance(request_count, int)
        or not 1 <= request_count <= MAX_REQUESTS
        or not isinstance(quarter_receipts, dict)
        or set(quarter_receipts) != set(FIXED_QUARTERS)
        or not isinstance(filing_evidence, dict)
        or len(filing_evidence) != sample_count
        or not isinstance(selection_hash, str)
        or _SHA256.fullmatch(selection_hash) is None
        or not isinstance(attempt_hash, str)
        or _SHA256.fullmatch(attempt_hash) is None
        or _sha256_file(selection_path) != selection_hash
        or _sha256_file(attempt_path) != attempt_hash
    ):
        _fail("form4_collection_private_manifest_invalid", "private manifest schema drifted")
    client = SecEdgarClient(
        quarantine_path,
        repository_root=root,
        user_agent=user_agent,
        opener=_network_disabled,
    )
    try:
        result = audit_form4_admission_feasibility(
            client,
            repository_root=root,
            quarter_receipts=manifest["quarter_receipts"],
            filing_evidence=manifest["filing_evidence"],
            evidence_mode="authorized_real_sample",
            real_sample_authorized=True,
            private_manifest_sha256=manifest_sha256,
        )
    except Form4AdmissionFeasibilityError as exc:
        result = build_form4_feasibility_failure_receipt(
            exc,
            sample_count=int(manifest["sample_count"]),
            evidence_mode="authorized_real_sample",
            private_manifest_sha256=manifest_sha256,
        )
    _sanitize_public_receipt(result)
    return result


def write_public_validation(path: str | Path, payload: Mapping[str, Any]) -> None:
    _sanitize_public_receipt(payload)
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    rendered = _json_bytes(payload)
    temporary = destination.with_name(f".{destination.name}.tmp")
    temporary.write_bytes(rendered)
    temporary.replace(destination)
