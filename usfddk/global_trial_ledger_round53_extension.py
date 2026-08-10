from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from pathlib import Path
from typing import Any

EXTENSION_PATH = Path("artifacts/short_term_global_trial_ledger_round53_extension.json")
PROTOCOL_PATH = Path("docs/SHORT_TERM_FORM4_EVENT_DIAGNOSTIC_PROTOCOL.md")
EXPECTED_PROTOCOL_SHA256 = (
    "692d0d32036ae2f5a42fdae54bf3f825df0c761cdadb29bc6133bebaeb235b74"
)
PREDECESSOR_PATH = Path("artifacts/short_term_global_trial_ledger_round51_extension.json")
PREDECESSOR_SHA256 = (
    "f6563a533f017e573a0f9b05fe0f73edfc8ac173f67918ab307a1c12c8bb1522"
)
PREDECESSOR_LOWER_BOUND = 6290
PREDECESSOR_CHAIN_HEAD = (
    "c2a7fe646af27bdff1e281e777f3d1ac779c29c3b8aca081ed13af9deb739a21"
)
INCREMENT = 3
CURRENT_LOWER_BOUND = 6293
SEQUENCE = 13
FAMILY_ID = "round53_form4_event_three_horizons"
EXPECTED_ENTRY_SHA256 = (
    "9d1e252e549673f141fba8629d0768460914ff43b1ae35d7d1f366e4f66fa136"
)
EXPECTED_RECEIPT_SHA256 = (
    "3c026ac851c61a9cfdcea06bafec26f3a2fc44c492fc48d85aa9780ed25b156c"
)


class GlobalTrialLedgerRound53Error(ValueError):
    def __init__(self, code: str, detail: str):
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}")


def _fail(code: str, detail: str) -> None:
    raise GlobalTrialLedgerRound53Error(code, detail)


def _sha256_file(path: Path) -> str:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError as exc:
        _fail("trial_ledger_round53_source_missing", f"{path}: {type(exc).__name__}")


def _canonical_sha256(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


def _check_bindings(root: Path, bindings: object) -> int:
    if not isinstance(bindings, list) or len(bindings) != 4:
        _fail("trial_ledger_round53_binding_mismatch", "binding count drifted")
    labels: set[str] = set()
    for binding in bindings:
        if not isinstance(binding, dict) or set(binding) != {"label", "path", "sha256"}:
            _fail("trial_ledger_round53_binding_mismatch", "binding fields drifted")
        label = binding["label"]
        path_value = binding["path"]
        claimed = binding["sha256"]
        if not isinstance(label, str) or label in labels or not isinstance(path_value, str):
            _fail("trial_ledger_round53_binding_mismatch", "binding value invalid")
        path = Path(path_value)
        if path.is_absolute() or ".." in path.parts or len(claimed) != 64:
            _fail("trial_ledger_round53_binding_mismatch", "binding path or hash invalid")
        labels.add(label)
        if _sha256_file((root / path).resolve()) != claimed:
            _fail("trial_ledger_round53_binding_mismatch", f"source hash drifted: {path_value}")
    return len(bindings)


def audit_round53_extension(*, root: str | Path) -> dict[str, Any]:
    root_path = Path(root).resolve()
    predecessor = root_path / PREDECESSOR_PATH
    if _sha256_file(predecessor) != PREDECESSOR_SHA256:
        _fail("trial_ledger_round53_predecessor_mismatch", "Round51 extension drifted")
    if _sha256_file(root_path / PROTOCOL_PATH) != EXPECTED_PROTOCOL_SHA256:
        _fail("trial_ledger_round53_protocol_mismatch", "protocol bytes drifted")
    try:
        extension = json.loads((root_path / EXTENSION_PATH).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        _fail("trial_ledger_round53_schema_mismatch", type(exc).__name__)
    if not isinstance(extension, dict):
        _fail("trial_ledger_round53_schema_mismatch", "extension is not an object")
    entry = extension.get("entry")
    if not isinstance(entry, dict):
        _fail("trial_ledger_round53_schema_mismatch", "entry is missing")
    claimed_entry = entry.get("entry_sha256")
    unsigned_entry = deepcopy(entry)
    unsigned_entry.pop("entry_sha256", None)
    if claimed_entry != EXPECTED_ENTRY_SHA256 or _canonical_sha256(unsigned_entry) != claimed_entry:
        _fail("trial_ledger_round53_chain_mismatch", "entry hash drifted")
    if (
        entry.get("sequence") != SEQUENCE
        or entry.get("family_id") != FAMILY_ID
        or entry.get("result_state") != "result_seen"
        or entry.get("publication_state") != "tracked"
        or entry.get("seen_result") is not True
        or entry.get("previous_lower_bound") != PREDECESSOR_LOWER_BOUND
        or entry.get("minimum_increment") != INCREMENT
        or entry.get("current_lower_bound") != CURRENT_LOWER_BOUND
        or entry.get("exact_increment_claimed") is not False
        or entry.get("previous_entry_sha256") != PREDECESSOR_CHAIN_HEAD
    ):
        _fail("trial_ledger_round53_arithmetic_mismatch", "entry arithmetic drifted")
    source_count = _check_bindings(root_path, entry.get("source_bindings"))
    if (
        extension.get("current_lower_bound") != CURRENT_LOWER_BOUND
        or extension.get("chain_head_sha256") != claimed_entry
        or extension.get("paper") != {
            "authorized": False,
            "state": "all_cash",
            "backfilled_trades": 0,
            "positions": [],
        }
        or extension.get("real_money_action_usd") != 0
    ):
        _fail("trial_ledger_round53_boundary_violation", "extension tip drifted")
    claimed_receipt = extension.get("receipt_sha256")
    unsigned_extension = deepcopy(extension)
    unsigned_extension.pop("receipt_sha256", None)
    if claimed_receipt != EXPECTED_RECEIPT_SHA256 or _canonical_sha256(unsigned_extension) != claimed_receipt:
        _fail("trial_ledger_round53_chain_mismatch", "receipt hash drifted")
    return {
        "passed": True,
        "current_lower_bound": CURRENT_LOWER_BOUND,
        "increment": INCREMENT,
        "source_binding_count": source_count,
        "paper": deepcopy(extension["paper"]),
        "real_money_action_usd": 0,
        "receipt_sha256": claimed_receipt,
    }
