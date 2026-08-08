from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

RESEARCH_ROUND = 34
PROTOCOL_PATH = "docs/SHORT_TERM_RESTATEMENT_FIREWALL_PROTOCOL.md"
PROTOCOL_RECEIPT_PATH = "artifacts/short_term_restatement_firewall_protocol_receipt.json"
PROTOCOL_SHA256 = (
    "d8cae6bce76300efb44c22439c46cf20f5aeda3a9d5776ad0faea318e11fef8f"
)
PROTOCOL_RECEIPT_SHA256 = (
    "65be630a5360c23b0eba18d4f5d0b62e5e7b6ad2d94b5da88294ba7ef470260d"
)
PARENT_PROVIDER_PROTOCOL_SHA256 = (
    "42c55adf76bba072b50618800890e5e34f07aae3d0b68be7ec1b46f5dcdaea9d"
)
PARENT_PROVIDER_RECEIPT_SHA256 = (
    "099c5fecc5d604582921cbc4b932c81226492b7bbff632f388f1003c8b25f961"
)
PARENT_PIT_CONTRACT_SHA256 = (
    "1e684e0ddbffbd29860a78d01c27b1e42885d53fafd8b1b95ae47b7547396b6c"
)
PARENT_PIT_RECEIPT_SHA256 = (
    "337d7116df98cfab692b125528cb986d0107145463db98c0f97c45fc0d433e48"
)

REFERENCE_COMMITS = {
    "tst_wocker": "3372aa088328700feafeeb07c72ab832ea2d3ecb",
    "tw_block_warrant": "37463c54796ba36f4aac262519ea7fc2ef797de6",
    "tst_wocker_filter_lab": "06c87b7a1735877c9ccbab3a339c1742814a5058",
}

RELEASE_FIELDS = {
    "provider",
    "source_id",
    "release_id",
    "available_at",
    "data_cutoff",
    "is_restatement",
    "supersedes_release_id",
    "content_sha256",
    "row_count",
}
ROW_FIELDS = {
    "source_id",
    "release_id",
    "source_record_id",
    "observation_date",
    "effective_at",
}
ENVELOPE_FIELDS = {
    "mode",
    "requested_as_of",
    "selected_release_ids",
    "release_ledger",
    "release_receipts",
    "rows",
}
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")
OFFSET_PATTERN = re.compile(r"(?:Z|[+-]\d{2}:\d{2})$")


class RestatementFirewallError(ValueError):
    """Fail-closed error with a stable semantic code."""

    def __init__(self, code: str, detail: str):
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}")


def _fail(code: str, detail: str) -> None:
    raise RestatementFirewallError(code, detail)


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _parse_utc(value: Any) -> datetime | None:
    if not isinstance(value, str) or not OFFSET_PATTERN.search(value):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(UTC)


def _parse_date(value: Any) -> date | None:
    if not isinstance(value, str) or DATE_PATTERN.fullmatch(value) is None:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _protocol_integrity(root: str | Path) -> dict[str, Any]:
    root_path = Path(root).resolve()
    try:
        receipt_path = root_path / PROTOCOL_RECEIPT_PATH
        receipt = _load_json(receipt_path)
        checks = {
            PROTOCOL_PATH: _sha256_file(root_path / PROTOCOL_PATH) == PROTOCOL_SHA256,
            PROTOCOL_RECEIPT_PATH: _sha256_file(receipt_path)
            == PROTOCOL_RECEIPT_SHA256,
            receipt["parent_provider_evidence_protocol"]["path"]: _sha256_file(
                root_path / receipt["parent_provider_evidence_protocol"]["path"]
            )
            == PARENT_PROVIDER_PROTOCOL_SHA256,
            receipt["parent_provider_evidence_receipt"]["path"]: _sha256_file(
                root_path / receipt["parent_provider_evidence_receipt"]["path"]
            )
            == PARENT_PROVIDER_RECEIPT_SHA256,
            receipt["parent_point_in_time_contract"]["path"]: _sha256_file(
                root_path / receipt["parent_point_in_time_contract"]["path"]
            )
            == PARENT_PIT_CONTRACT_SHA256,
            receipt["parent_point_in_time_receipt"]["path"]: _sha256_file(
                root_path / receipt["parent_point_in_time_receipt"]["path"]
            )
            == PARENT_PIT_RECEIPT_SHA256,
        }
        frozen = (
            receipt["schema_version"] == 1
            and receipt["research_round"] == RESEARCH_ROUND
            and receipt["status"] == "frozen_before_release_ledger_fixture"
            and receipt["protocol"]
            == {"path": PROTOCOL_PATH, "sha256": PROTOCOL_SHA256}
            and receipt["reference_commits"] == REFERENCE_COMMITS
            and receipt["synthetic_fixture_present_at_freeze"] is False
            and receipt["authorized_provider_package_present_at_freeze"] is False
            and receipt["formal_backtest_authorized"] is False
            and receipt["strategy_run_count"] == 0
            and receipt["paper_authorized"] is False
            and receipt["paper_state"] == "all_cash"
            and receipt["real_money_action_usd"] == 0
            and receipt["frozen_control_count"] == 9
            and receipt["frozen_attack_count"] == 9
            and all(checks.values())
        )
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        _fail("release_protocol_mismatch", f"protocol or parent receipt invalid: {exc}")
    if not frozen:
        _fail("release_protocol_mismatch", "Round34 protocol or parent hash mismatch")
    return {
        "passed": True,
        "frozen_at": receipt["frozen_at"],
        "git_head_at_freeze": receipt["git_head_at_freeze"],
        "hash_checks": checks,
    }


def protocol_integrity(root: str | Path) -> dict[str, Any]:
    return _protocol_integrity(root)


def _validate_release_records(
    records: Any,
) -> tuple[dict[str, dict[str, Any]], dict[str, datetime]]:
    if not isinstance(records, list) or not records:
        _fail("release_schema_mismatch", "release_ledger must be a non-empty list")
    by_id: dict[str, dict[str, Any]] = {}
    available: dict[str, datetime] = {}
    for record in records:
        if not isinstance(record, dict) or set(record) != RELEASE_FIELDS:
            _fail("release_schema_mismatch", "release record fields are not exact")
        release_id = record.get("release_id")
        if not isinstance(release_id, str) or not release_id:
            _fail("release_schema_mismatch", "release_id must be a non-empty string")
        if release_id in by_id:
            _fail("release_id_duplicate", f"duplicate release id: {release_id}")
        if not isinstance(record.get("provider"), str) or not record["provider"]:
            _fail("release_schema_mismatch", f"provider missing for {release_id}")
        if not isinstance(record.get("source_id"), str) or not record["source_id"]:
            _fail("release_schema_mismatch", f"source_id missing for {release_id}")
        available_at = _parse_utc(record.get("available_at"))
        cutoff = _parse_date(record.get("data_cutoff"))
        if available_at is None or cutoff is None:
            _fail("release_schema_mismatch", f"invalid timestamp/date for {release_id}")
        if not isinstance(record.get("is_restatement"), bool):
            _fail("release_schema_mismatch", f"is_restatement must be bool for {release_id}")
        supersedes = record.get("supersedes_release_id")
        if supersedes is not None and not isinstance(supersedes, str):
            _fail("release_schema_mismatch", f"invalid supersedes id for {release_id}")
        digest = record.get("content_sha256")
        row_count = record.get("row_count")
        if not isinstance(digest, str) or SHA256_PATTERN.fullmatch(digest) is None:
            _fail("release_schema_mismatch", f"invalid content SHA for {release_id}")
        if not isinstance(row_count, int) or isinstance(row_count, bool) or row_count < 0:
            _fail("release_schema_mismatch", f"invalid row count for {release_id}")
        by_id[release_id] = record
        available[release_id] = available_at
    for release_id, record in by_id.items():
        supersedes = record["supersedes_release_id"]
        if supersedes is None:
            if record["is_restatement"]:
                _fail("supersedes_chain_invalid", f"restatement {release_id} has no predecessor")
            continue
        if supersedes not in by_id:
            _fail("supersedes_chain_invalid", f"unknown predecessor {supersedes}")
        if by_id[supersedes]["source_id"] != record["source_id"]:
            _fail("supersedes_chain_invalid", f"source changed at {release_id}")
        if not record["is_restatement"]:
            _fail("supersedes_chain_invalid", f"non-restatement supersedes at {release_id}")
        if available[supersedes] >= available[release_id]:
            _fail("supersedes_chain_invalid", f"predecessor is not older at {release_id}")
    for release_id in by_id:
        seen: set[str] = set()
        current: str | None = release_id
        while current is not None:
            if current in seen:
                _fail("supersedes_chain_invalid", f"cycle at {release_id}")
            seen.add(current)
            current = by_id[current]["supersedes_release_id"]
    return by_id, available


def _validate_rows(rows: Any, releases: dict[str, dict[str, Any]]) -> dict[str, int]:
    if not isinstance(rows, list):
        _fail("release_schema_mismatch", "rows must be a list")
    counts: Counter[str] = Counter()
    seen: set[tuple[str, str]] = set()
    for row in rows:
        if not isinstance(row, dict) or set(row) != ROW_FIELDS:
            _fail("release_schema_mismatch", "row fields are not exact")
        source_id = row.get("source_id")
        release_id = row.get("release_id")
        source_record_id = row.get("source_record_id")
        if not all(isinstance(row.get(key), str) and row[key] for key in ROW_FIELDS):
            _fail("release_schema_mismatch", "row fields cannot be empty")
        if release_id not in releases:
            _fail("release_receipt_mismatch", f"row references unknown release {release_id}")
        if source_id != releases[release_id]["source_id"]:
            _fail("release_receipt_mismatch", f"row source does not match {release_id}")
        if _parse_date(row["observation_date"]) is None or _parse_utc(row["effective_at"]) is None:
            _fail("release_schema_mismatch", f"invalid row time for {source_record_id}")
        key = (source_id, source_record_id)
        if key in seen:
            _fail("release_receipt_mismatch", f"duplicate source row {key}")
        seen.add(key)
        counts[release_id] += 1
    return dict(counts)


def validate_envelope(envelope: dict[str, Any], *, root: str | Path) -> dict[str, Any]:
    """Validate an as-known release selection without importing market data."""

    protocol = protocol_integrity(root)
    if not isinstance(envelope, dict) or set(envelope) != ENVELOPE_FIELDS:
        _fail("release_schema_mismatch", "envelope fields are not exact")
    mode = envelope.get("mode")
    if mode not in {"as_known", "final_revised"}:
        _fail("release_schema_mismatch", "unsupported envelope mode")
    requested = _parse_utc(envelope.get("requested_as_of"))
    if requested is None:
        _fail("release_schema_mismatch", "requested_as_of must include UTC offset")
    releases, available = _validate_release_records(envelope.get("release_ledger"))
    receipts = envelope.get("release_receipts")
    if not isinstance(receipts, dict) or set(receipts) != set(releases):
        _fail("release_receipt_mismatch", "release receipts do not cover exact release set")
    for release_id, release in releases.items():
        receipt = receipts.get(release_id)
        if not isinstance(receipt, dict) or set(receipt) != {"content_sha256", "row_count"}:
            _fail("release_receipt_mismatch", f"receipt shape invalid for {release_id}")
        if receipt != {
            "content_sha256": release["content_sha256"],
            "row_count": release["row_count"],
        }:
            _fail("release_receipt_mismatch", f"receipt mismatch for {release_id}")
    selected = envelope.get("selected_release_ids")
    if (
        not isinstance(selected, list)
        or not selected
        or any(not isinstance(item, str) for item in selected)
        or len(set(selected)) != len(selected)
        or any(item not in releases for item in selected)
    ):
        _fail("release_schema_mismatch", "selected release ids are invalid")
    row_counts = _validate_rows(envelope.get("rows"), releases)
    for release_id in selected:
        if row_counts.get(release_id, 0) != releases[release_id]["row_count"]:
            _fail("release_receipt_mismatch", f"row count mismatch for {release_id}")
    eligible = [release_id for release_id, at in available.items() if at <= requested]
    future_selected = [release_id for release_id in selected if release_id not in eligible]
    if mode == "as_known" and future_selected:
        if any(releases[item]["is_restatement"] for item in future_selected):
            _fail(
                "restatement_substitution",
                f"future restatement selected for as-known request: {future_selected}",
            )
        _fail("future_release_leakage", f"future release selected for as-known request: {future_selected}")
    if mode == "as_known":
        for release_id in selected:
            cutoff = _parse_date(releases[release_id]["data_cutoff"])
            assert cutoff is not None
            if cutoff > requested.date():
                _fail("future_release_leakage", f"data cutoff is after request for {release_id}")
            for row in envelope["rows"]:
                if row["release_id"] == release_id and _parse_date(row["observation_date"]) > requested.date():
                    _fail("future_release_leakage", f"row observation is after request for {release_id}")
    return {
        "protocol_integrity": protocol,
        "mode": mode,
        "requested_as_of": envelope["requested_as_of"],
        "selected_release_ids": list(selected),
        "eligible_release_ids": eligible,
        "future_selected_release_ids": future_selected,
        "restatement_release_ids": [
            release_id for release_id in selected if releases[release_id]["is_restatement"]
        ],
        "row_count_by_release": row_counts,
        "row_count": len(envelope["rows"]),
        "as_known_integrity_passed": mode == "as_known",
        "strategy_input_allowed": False,
        "formal_backtest_authorized": False,
        "provider_package_qualified": False,
        "strategy_run_count": 0,
        "paper_authorized": False,
        "paper_state": "all_cash",
        "real_money_action_usd": 0,
    }


def _digest(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def synthetic_as_known_envelope() -> dict[str, Any]:
    releases = [
        {
            "provider": "synthetic-provider",
            "source_id": "CRSP_STK_DLY",
            "release_id": "R-20260701-v1",
            "available_at": "2026-07-02T12:00:00Z",
            "data_cutoff": "2026-07-01",
            "is_restatement": False,
            "supersedes_release_id": None,
            "content_sha256": _digest("release-v1"),
            "row_count": 2,
        },
        {
            "provider": "synthetic-provider",
            "source_id": "CRSP_STK_DLY",
            "release_id": "R-20260701-v2",
            "available_at": "2026-07-15T12:00:00Z",
            "data_cutoff": "2026-07-01",
            "is_restatement": True,
            "supersedes_release_id": "R-20260701-v1",
            "content_sha256": _digest("release-v2"),
            "row_count": 2,
        },
    ]
    return {
        "mode": "as_known",
        "requested_as_of": "2026-07-05T20:00:00Z",
        "selected_release_ids": ["R-20260701-v1"],
        "release_ledger": releases,
        "release_receipts": {
            release["release_id"]: {
                "content_sha256": release["content_sha256"],
                "row_count": release["row_count"],
            }
            for release in releases
        },
        "rows": [
            {
                "source_id": "CRSP_STK_DLY",
                "release_id": "R-20260701-v1",
                "source_record_id": "ROW-1",
                "observation_date": "2026-07-01",
                "effective_at": "2026-07-01T20:00:00Z",
            },
            {
                "source_id": "CRSP_STK_DLY",
                "release_id": "R-20260701-v1",
                "source_record_id": "ROW-2",
                "observation_date": "2026-07-01",
                "effective_at": "2026-07-01T20:00:00Z",
            },
        ],
    }


def frozen_decision_summary() -> dict[str, Any]:
    return {
        "provider_package_qualified": False,
        "formal_backtest_authorized": False,
        "strategy_run_count": 0,
        "paper_authorized": False,
        "paper_state": "all_cash",
        "real_money_action_usd": 0,
        "formal_readiness": {"passed": 1, "total": 18, "all_passed": False},
        "point_in_time_readiness": {"passed": 1, "total": 20, "all_passed": False},
    }


def validate_result(result: dict[str, Any], *, root: str | Path) -> dict[str, Any]:
    protocol_integrity(root)
    if result.get("research_round") != RESEARCH_ROUND:
        _fail("release_protocol_mismatch", "research round mismatch")
    if result.get("protocol_sha256") != PROTOCOL_SHA256:
        _fail("release_protocol_mismatch", "protocol SHA mismatch")
    for key, value in frozen_decision_summary().items():
        if result.get(key) != value:
            _fail("release_decision_boundary_violation", f"decision field drift: {key}")
    if result.get("mode") == "final_revised" and result.get("strategy_input_allowed") is True:
        _fail(
            "final_revised_strategy_substitution",
            "final revised release cannot become strategy input",
        )
    if result.get("mode") == "as_known" and result.get("as_known_integrity_passed") is not True:
        _fail("release_decision_boundary_violation", "as-known integrity result missing")
    return {"passed": True, "mode": result.get("mode")}
