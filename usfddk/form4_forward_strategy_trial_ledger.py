from __future__ import annotations

import hashlib
import json
import re
import stat
from copy import deepcopy
from pathlib import Path
from typing import Any, NoReturn

from usfddk.global_trial_ledger import audit_global_trial_ledger

BASE_LEDGER_PATH = "artifacts/short_term_global_trial_ledger.json"
ROUND46_PROTOCOL_PATH = "docs/SHORT_TERM_FORM4_FORWARD_STRATEGY_EVIDENCE_PROTOCOL.md"
ROUND46_EXTENSION_PATH = (
    "artifacts/short_term_global_trial_ledger_extension_round46.json"
)
BASE_LEDGER_SHA256 = "0240f3c36edca35a86c077a94116067a7d1560e4329968df33abbdcaffbb4b49"
BASE_CHAIN_HEAD_SHA256 = (
    "c0e754cee5603c5eb9d2d142db1af6ec21b465d3492097b02112b94a18574085"
)
ROUND46_PROTOCOL_SHA256 = "a72bbfc56071aa16831bc90a64e3063fdcb1ecea40624b697be6e11d18b7e32c"
ROUND46_EXTENSION_FILE_SHA256 = (
    "90c99afe3184ef7654fe7e013bc6030901e19fe70af1720825f5c13e2fda1b00"
)
BASE_LOWER_BOUND = 6_287
ROUND46_INCREMENT = 8
COMBINED_LOWER_BOUND = 6_295
ROUND46_SEQUENCE = 12
ROUND46_FAMILY_ID = "round46_form4_forward_eight_comparisons"

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_TOP_KEYS = {
    "schema_version",
    "status",
    "count_semantics",
    "exact_global_count_claimed",
    "predecessor",
    "entry",
    "combined_tip_sha256",
    "paper",
    "real_money_action_usd",
    "extension_sha256",
}
_PREDECESSOR_KEYS = {
    "path",
    "sha256",
    "schema_version",
    "entry_count",
    "current_lower_bound",
    "chain_head_sha256",
}
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
_BINDING_KEYS = {"label", "path", "sha256"}
_PAPER_ZERO = {
    "authorized": False,
    "state": "all_cash",
    "backfilled_trades": 0,
    "positions": [],
}


class Round46TrialLedgerError(ValueError):
    """Fail-closed versioned trial-ledger extension error."""

    def __init__(self, code: str, detail: str):
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}")


def _fail(detail: str) -> NoReturn:
    raise Round46TrialLedgerError("round46_trial_extension_invalid", detail)


def _canonical_sha256(value: dict[str, Any]) -> str:
    try:
        rendered = json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError):
        _fail("canonical JSON is invalid")
    return hashlib.sha256(rendered).hexdigest()


def _file_sha256(path: Path) -> str:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        _fail("bound file is missing")


def _exact_relative(root: Path, value: object) -> Path:
    if not isinstance(value, str) or not value:
        _fail("binding path is invalid")
    relative = Path(value)
    if relative.is_absolute() or ".." in relative.parts:
        _fail("binding path escaped repository")
    unresolved = root / relative
    try:
        metadata = unresolved.lstat()
    except OSError:
        _fail("binding is missing")
    resolved = unresolved.resolve()
    if root != resolved and root not in resolved.parents:
        _fail("binding path escaped repository")
    if not stat.S_ISREG(metadata.st_mode) or unresolved.is_symlink():
        _fail("binding is not one regular file")
    return resolved


def audit_round46_trial_extension_payload(
    payload: dict[str, Any],
    *,
    root: str | Path,
) -> dict[str, Any]:
    root_path = Path(root).resolve()
    if set(payload) != _TOP_KEYS:
        _fail("top-level schema drifted")
    if (
        payload.get("schema_version")
        != "us_fddk.global_trial_ledger_extension.round46.v1"
        or payload.get("status") != "append_only_successor_preregistered_unrun"
        or payload.get("count_semantics")
        != "conservative_minimum_hypothesis_path_lower_bound_not_exact_global_count"
        or payload.get("exact_global_count_claimed") is not False
    ):
        _fail("extension semantics drifted")

    base_audit = audit_global_trial_ledger(root=root_path)
    predecessor = payload.get("predecessor")
    if not isinstance(predecessor, dict) or set(predecessor) != _PREDECESSOR_KEYS:
        _fail("predecessor schema drifted")
    predecessor_path = _exact_relative(root_path, predecessor.get("path"))
    if (
        predecessor.get("path") != BASE_LEDGER_PATH
        or predecessor.get("sha256") != BASE_LEDGER_SHA256
        or _file_sha256(predecessor_path) != BASE_LEDGER_SHA256
        or predecessor.get("schema_version") != 1
        or type(predecessor.get("entry_count")) is not int
        or predecessor.get("entry_count") != 12
        or type(predecessor.get("current_lower_bound")) is not int
        or predecessor.get("current_lower_bound") != BASE_LOWER_BOUND
        or predecessor.get("chain_head_sha256") != BASE_CHAIN_HEAD_SHA256
        or base_audit.get("current_lower_bound") != BASE_LOWER_BOUND
        or base_audit.get("chain_head_sha256") != BASE_CHAIN_HEAD_SHA256
    ):
        _fail("predecessor identity drifted")

    entry = payload.get("entry")
    if not isinstance(entry, dict) or set(entry) != _ENTRY_KEYS:
        _fail("successor entry schema drifted")
    if (
        type(entry.get("sequence")) is not int
        or entry.get("sequence") != ROUND46_SEQUENCE
        or entry.get("family_id") != ROUND46_FAMILY_ID
        or entry.get("result_state") != "preregistered_unrun"
        or entry.get("publication_state") != "tracked_preregistered"
        or entry.get("seen_result") is not False
        or type(entry.get("previous_lower_bound")) is not int
        or entry.get("previous_lower_bound") != BASE_LOWER_BOUND
        or type(entry.get("minimum_increment")) is not int
        or entry.get("minimum_increment") != ROUND46_INCREMENT
        or type(entry.get("current_lower_bound")) is not int
        or entry.get("current_lower_bound") != COMBINED_LOWER_BOUND
        or entry.get("current_lower_bound")
        != entry.get("previous_lower_bound") + entry.get("minimum_increment")
        or entry.get("exact_increment_claimed") is not True
        or entry.get("previous_entry_sha256") != BASE_CHAIN_HEAD_SHA256
    ):
        _fail("successor state or arithmetic drifted")

    bindings = entry.get("source_bindings")
    if not isinstance(bindings, list) or len(bindings) != 1:
        _fail("successor source bindings drifted")
    binding = bindings[0]
    if not isinstance(binding, dict) or set(binding) != _BINDING_KEYS:
        _fail("successor source binding schema drifted")
    protocol_path = _exact_relative(root_path, binding.get("path"))
    if (
        binding.get("label") != "round46_protocol"
        or binding.get("path") != ROUND46_PROTOCOL_PATH
        or binding.get("sha256") != ROUND46_PROTOCOL_SHA256
        or _file_sha256(protocol_path) != ROUND46_PROTOCOL_SHA256
    ):
        _fail("Round46 protocol binding drifted")

    entry_core = deepcopy(entry)
    claimed_entry_sha = entry_core.pop("entry_sha256")
    if (
        not isinstance(claimed_entry_sha, str)
        or _SHA256.fullmatch(claimed_entry_sha) is None
        or _canonical_sha256(entry_core) != claimed_entry_sha
        or payload.get("combined_tip_sha256") != claimed_entry_sha
    ):
        _fail("successor chain tip drifted")

    extension_core = deepcopy(payload)
    claimed_extension_sha = extension_core.pop("extension_sha256")
    if (
        not isinstance(claimed_extension_sha, str)
        or _SHA256.fullmatch(claimed_extension_sha) is None
        or _canonical_sha256(extension_core) != claimed_extension_sha
        or payload.get("paper") != _PAPER_ZERO
        or type(payload.get("real_money_action_usd")) is not int
        or payload.get("real_money_action_usd") != 0
    ):
        _fail("extension hash or decision boundary drifted")

    return {
        "passed": True,
        "base_lower_bound": BASE_LOWER_BOUND,
        "round46_increment": ROUND46_INCREMENT,
        "combined_lower_bound": COMBINED_LOWER_BOUND,
        "combined_tip_sha256": claimed_entry_sha,
        "seen_result": False,
        "paper": deepcopy(_PAPER_ZERO),
        "real_money_action_usd": 0,
    }


def audit_round46_trial_extension(*, root: str | Path) -> dict[str, Any]:
    root_path = Path(root).resolve()
    extension_path = _exact_relative(root_path, ROUND46_EXTENSION_PATH)
    try:
        raw = extension_path.read_bytes()
        payload = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        _fail("extension JSON is invalid")
    if (
        not isinstance(payload, dict)
        or hashlib.sha256(raw).hexdigest() != ROUND46_EXTENSION_FILE_SHA256
    ):
        _fail("extension file identity drifted")
    return audit_round46_trial_extension_payload(payload, root=root_path)
