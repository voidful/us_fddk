from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from pathlib import Path
from typing import Any

from .global_trial_ledger import audit_global_trial_ledger

EXTENSION_PATH = Path("artifacts/short_term_global_trial_ledger_round51_extension.json")
EXTENSION_PROTOCOL_PATH = Path(
    "docs/SHORT_TERM_GLOBAL_TRIAL_LEDGER_AMENDMENT_V1_1.md"
)
EXPECTED_EXTENSION_SCHEMA = "usfddk.short_term_global_trial_ledger.v1.1"
EXPECTED_EXTENSION_STATUS = "append_only_global_trial_lower_bound_extension"
EXPECTED_FAMILY_ID = "round51_current_cohort_breakout_three_horizons"
EXPECTED_BASE_LOWER_BOUND = 6_287
EXPECTED_INCREMENT = 3
EXPECTED_CURRENT_LOWER_BOUND = 6_290
EXPECTED_SEQUENCE = 12
EXPECTED_BASE_LEDGER_SHA256 = (
    "0240f3c36edca35a86c077a94116067a7d1560e4329968df33abbdcaffbb4b49"
)
EXPECTED_BASE_PROTOCOL_SHA256 = (
    "8c9fb4d515741283143192612d8017a86333086ed641ea0e45c2eb5c492c4451"
)
EXPECTED_BASE_CHAIN_HEAD = (
    "c0e754cee5603c5eb9d2d142db1af6ec21b465d3492097b02112b94a18574085"
)
EXPECTED_EXTENSION_PROTOCOL_SHA256 = (
    "99f67e0cc6670c64eda1643d9d1dc34cf79e2c4dcdb7fb23eb8526fc0bb6237d"
)
EXPECTED_ENTRY_SHA256 = (
    "c2a7fe646af27bdff1e281e777f3d1ac779c29c3b8aca081ed13af9deb739a21"
)
EXPECTED_RECEIPT_SHA256 = (
    "ea2fc3f1750e371872b5592aa8eb4cfc2deb739fd27b973d9bc8c70277801bc9"
)
_SHA256_LENGTH = 64
_ENTRY_KEYS = {
    "sequence",
    "family_id",
    "result_state",
    "publication_state",
    "seen_result",
    "previous_lower_bound",
    "minimum_increment",
    "current_lower_bound",
    "exact_increment_claimed",
    "source_bindings",
    "previous_entry_sha256",
    "entry_sha256",
}


class GlobalTrialLedgerExtensionError(ValueError):
    """Fail-closed Round51 global trial ledger extension error."""

    def __init__(self, code: str, detail: str):
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}")


def _fail(code: str, detail: str) -> None:
    raise GlobalTrialLedgerExtensionError(code, detail)


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_file(path: Path) -> str:
    try:
        return _sha256_bytes(path.read_bytes())
    except OSError as exc:
        _fail("trial_ledger_extension_source_missing", f"{path}: {type(exc).__name__}")


def _canonical_sha256(value: object) -> str:
    return _sha256_bytes(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    )


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        _fail("trial_ledger_extension_schema_mismatch", type(exc).__name__)
    if not isinstance(value, dict):
        _fail("trial_ledger_extension_schema_mismatch", "payload is not an object")
    return value


def _check_source_bindings(root: Path, bindings: object) -> int:
    if not isinstance(bindings, list) or len(bindings) != 4:
        _fail("trial_ledger_extension_source_binding_mismatch", "source binding count drifted")
    labels: set[str] = set()
    for binding in bindings:
        if not isinstance(binding, dict) or set(binding) != {"label", "path", "sha256"}:
            _fail("trial_ledger_extension_source_binding_mismatch", "binding fields drifted")
        label = binding["label"]
        path_value = binding["path"]
        claimed = binding["sha256"]
        if (
            not isinstance(label, str)
            or label in labels
            or not isinstance(path_value, str)
            or not path_value
            or not isinstance(claimed, str)
            or len(claimed) != _SHA256_LENGTH
        ):
            _fail("trial_ledger_extension_source_binding_mismatch", "binding value invalid")
        labels.add(label)
        path = Path(path_value)
        if path.is_absolute() or ".." in path.parts:
            _fail("trial_ledger_extension_source_binding_mismatch", "source escaped repository")
        resolved = (root / path).resolve()
        if root not in resolved.parents and resolved != root:
            _fail("trial_ledger_extension_source_binding_mismatch", "source escaped repository")
        if _sha256_file(resolved) != claimed:
            _fail(
                "trial_ledger_extension_source_binding_mismatch",
                f"source hash drifted: {path_value}",
            )
    return len(bindings)


def audit_round51_extension(*, root: str | Path) -> dict[str, Any]:
    root_path = Path(root).resolve()
    base = audit_global_trial_ledger(root=root_path)
    base_ledger_path = root_path / "artifacts/short_term_global_trial_ledger.json"
    extension_path = root_path / EXTENSION_PATH
    extension = _read_json(extension_path)
    if set(extension) != {
        "base_ledger",
        "chain_head_sha256",
        "current_lower_bound",
        "entry",
        "extension_protocol_path",
        "extension_protocol_sha256",
        "paper",
        "real_money_action_usd",
        "receipt_sha256",
        "schema_version",
        "status",
    }:
        _fail("trial_ledger_extension_schema_mismatch", "top-level fields drifted")
    if extension["schema_version"] != EXPECTED_EXTENSION_SCHEMA or extension["status"] != EXPECTED_EXTENSION_STATUS:
        _fail("trial_ledger_extension_schema_mismatch", "schema or status drifted")
    base_info = extension["base_ledger"]
    if not isinstance(base_info, dict) or set(base_info) != {
        "path",
        "sha256",
        "protocol_path",
        "protocol_sha256",
        "current_lower_bound",
        "chain_head_sha256",
    }:
        _fail("trial_ledger_extension_schema_mismatch", "base binding fields drifted")
    if (
        base_info["path"] != "artifacts/short_term_global_trial_ledger.json"
        or base_info["sha256"] != EXPECTED_BASE_LEDGER_SHA256
        or _sha256_file(base_ledger_path) != EXPECTED_BASE_LEDGER_SHA256
        or base_info["protocol_path"] != "docs/SHORT_TERM_GLOBAL_TRIAL_LEDGER_PROTOCOL.md"
        or base_info["protocol_sha256"] != EXPECTED_BASE_PROTOCOL_SHA256
        or base_info["current_lower_bound"] != EXPECTED_BASE_LOWER_BOUND
        or base_info["chain_head_sha256"] != EXPECTED_BASE_CHAIN_HEAD
        or base["current_lower_bound"] != EXPECTED_BASE_LOWER_BOUND
        or base["chain_head_sha256"] != EXPECTED_BASE_CHAIN_HEAD
    ):
        _fail("trial_ledger_extension_predecessor_mismatch", "v1.0 predecessor binding drifted")
    protocol_path_value = extension["extension_protocol_path"]
    if protocol_path_value != str(EXTENSION_PROTOCOL_PATH):
        _fail("trial_ledger_extension_protocol_mismatch", "amendment path drifted")
    if extension["extension_protocol_sha256"] != EXPECTED_EXTENSION_PROTOCOL_SHA256:
        _fail("trial_ledger_extension_protocol_mismatch", "amendment hash drifted")
    if _sha256_file(root_path / EXTENSION_PROTOCOL_PATH) != EXPECTED_EXTENSION_PROTOCOL_SHA256:
        _fail("trial_ledger_extension_protocol_mismatch", "amendment bytes drifted")

    entry = extension["entry"]
    if not isinstance(entry, dict) or set(entry) != _ENTRY_KEYS:
        _fail("trial_ledger_extension_schema_mismatch", "entry fields drifted")
    claimed_entry_hash = entry["entry_sha256"]
    unsigned_entry = deepcopy(entry)
    unsigned_entry.pop("entry_sha256")
    if claimed_entry_hash != EXPECTED_ENTRY_SHA256 or _canonical_sha256(unsigned_entry) != claimed_entry_hash:
        _fail("trial_ledger_extension_chain_mismatch", "entry hash drifted")
    if (
        entry["sequence"] != EXPECTED_SEQUENCE
        or entry["family_id"] != EXPECTED_FAMILY_ID
        or entry["result_state"] != "result_seen"
        or entry["publication_state"] != "tracked"
        or entry["seen_result"] is not True
        or entry["previous_lower_bound"] != EXPECTED_BASE_LOWER_BOUND
        or entry["minimum_increment"] != EXPECTED_INCREMENT
        or entry["current_lower_bound"] != EXPECTED_CURRENT_LOWER_BOUND
        or entry["exact_increment_claimed"] is not False
        or entry["previous_entry_sha256"] != EXPECTED_BASE_CHAIN_HEAD
    ):
        _fail("trial_ledger_extension_arithmetic_mismatch", "Round51 entry arithmetic drifted")
    source_count = _check_source_bindings(root_path, entry["source_bindings"])
    if extension["current_lower_bound"] != EXPECTED_CURRENT_LOWER_BOUND or extension["chain_head_sha256"] != claimed_entry_hash:
        _fail("trial_ledger_extension_arithmetic_mismatch", "extension tip drifted")
    if extension["paper"] != {
        "authorized": False,
        "state": "all_cash",
        "backfilled_trades": 0,
        "positions": [],
    } or extension["real_money_action_usd"] != 0:
        _fail("trial_ledger_extension_decision_boundary_violation", "extension authorized trading")
    claimed_receipt_hash = extension["receipt_sha256"]
    unsigned_extension = deepcopy(extension)
    unsigned_extension.pop("receipt_sha256")
    if claimed_receipt_hash != EXPECTED_RECEIPT_SHA256 or _canonical_sha256(unsigned_extension) != claimed_receipt_hash:
        _fail("trial_ledger_extension_chain_mismatch", "extension self-hash drifted")
    return {
        "passed": True,
        "base_ledger_sha256": base["ledger_sha256"],
        "base_lower_bound": EXPECTED_BASE_LOWER_BOUND,
        "family_id": EXPECTED_FAMILY_ID,
        "increment": EXPECTED_INCREMENT,
        "current_lower_bound": EXPECTED_CURRENT_LOWER_BOUND,
        "source_binding_count": source_count,
        "paper": deepcopy(extension["paper"]),
        "real_money_action_usd": 0,
        "extension_path": str(EXTENSION_PATH),
        "extension_receipt_sha256": claimed_receipt_hash,
    }
