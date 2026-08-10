from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from pathlib import Path
from typing import Any

EXTENSION_PATH = Path("artifacts/short_term_global_trial_ledger_round57_extension.json")
PROTOCOL_PATH = Path(
    "docs/SHORT_TERM_MARKET_STRESS_LAGGARD_REVERSAL_PROTOCOL.md"
)
EXPECTED_PROTOCOL_SHA256 = (
    "783a99b8d3da32824760c5162d52e2d964874b8720d4e4c783b15d53b82b5e5d"
)
PREDECESSOR_PATH = Path("artifacts/short_term_global_trial_ledger_round56_extension.json")
PREDECESSOR_SHA256 = (
    "4caa5aa92f64786e1f79975b20e89e205289e157d1b85ffeed2ddedfaaf3c77a"
)
PREDECESSOR_LOWER_BOUND = 6302
PREDECESSOR_CHAIN_HEAD = (
    "d5af5ae92f812039d007ef69f6714a55a0b9cff5bd750e9d897f35825e5ea024"
)
INCREMENT = 3
CURRENT_LOWER_BOUND = 6305
SEQUENCE = 17
FAMILY_ID = "round57_market_stress_laggard_reversal_three_horizons"
EXPECTED_ENTRY_SHA256 = (
    "d96352cab0264815d6eff976d3d1644f307c4a5455dba360ff979d6264b0b778"
)
EXPECTED_RECEIPT_SHA256 = (
    "79a9ffc620b3b38d2dfdfdcbfd5004f31adf10391e98153a50bed0de5cde51bd"
)


class GlobalTrialLedgerRound57Error(ValueError):
    def __init__(self, code: str, detail: str):
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}")


def _fail(code: str, detail: str) -> None:
    raise GlobalTrialLedgerRound57Error(code, detail)


def _sha256_file(path: Path) -> str:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError as exc:
        _fail("trial_ledger_round57_source_missing", f"{path}: {type(exc).__name__}")


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
        _fail("trial_ledger_round57_binding_mismatch", "binding count drifted")
    labels: set[str] = set()
    for binding in bindings:
        if not isinstance(binding, dict) or set(binding) != {"label", "path", "sha256"}:
            _fail("trial_ledger_round57_binding_mismatch", "binding fields drifted")
        label = binding["label"]
        path_value = binding["path"]
        claimed = binding["sha256"]
        if (
            not isinstance(label, str)
            or label in labels
            or not isinstance(path_value, str)
            or not isinstance(claimed, str)
            or len(claimed) != 64
        ):
            _fail("trial_ledger_round57_binding_mismatch", "binding value invalid")
        path = Path(path_value)
        if path.is_absolute() or ".." in path.parts:
            _fail("trial_ledger_round57_binding_mismatch", "binding path invalid")
        labels.add(label)
        if _sha256_file((root / path).resolve()) != claimed:
            _fail("trial_ledger_round57_binding_mismatch", f"source hash drifted: {path_value}")
    return len(bindings)


def audit_round57_extension(*, root: str | Path) -> dict[str, Any]:
    root_path = Path(root).resolve()
    if _sha256_file(root_path / PREDECESSOR_PATH) != PREDECESSOR_SHA256:
        _fail("trial_ledger_round57_predecessor_mismatch", "Round56 extension drifted")
    if _sha256_file(root_path / PROTOCOL_PATH) != EXPECTED_PROTOCOL_SHA256:
        _fail("trial_ledger_round57_protocol_mismatch", "protocol bytes drifted")
    try:
        extension = json.loads((root_path / EXTENSION_PATH).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        _fail("trial_ledger_round57_schema_mismatch", type(exc).__name__)
    if not isinstance(extension, dict):
        _fail("trial_ledger_round57_schema_mismatch", "extension is not an object")
    entry = extension.get("entry")
    if not isinstance(entry, dict):
        _fail("trial_ledger_round57_schema_mismatch", "entry is missing")
    claimed_entry = entry.get("entry_sha256")
    unsigned_entry = deepcopy(entry)
    unsigned_entry.pop("entry_sha256", None)
    if claimed_entry != EXPECTED_ENTRY_SHA256 or _canonical_sha256(unsigned_entry) != claimed_entry:
        _fail("trial_ledger_round57_chain_mismatch", "entry hash drifted")
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
        _fail("trial_ledger_round57_arithmetic_mismatch", "entry arithmetic drifted")
    source_count = _check_bindings(root_path, entry.get("source_bindings"))
    if (
        extension.get("current_lower_bound") != CURRENT_LOWER_BOUND
        or extension.get("chain_head_sha256") != claimed_entry
        or extension.get("paper")
        != {
            "authorized": False,
            "state": "all_cash",
            "backfilled_trades": 0,
            "positions": [],
        }
        or extension.get("real_money_action_usd") != 0
    ):
        _fail("trial_ledger_round57_boundary_violation", "extension tip drifted")
    claimed_receipt = extension.get("receipt_sha256")
    unsigned_extension = deepcopy(extension)
    unsigned_extension.pop("receipt_sha256", None)
    if claimed_receipt != EXPECTED_RECEIPT_SHA256 or _canonical_sha256(unsigned_extension) != claimed_receipt:
        _fail("trial_ledger_round57_chain_mismatch", "receipt hash drifted")
    return {
        "passed": True,
        "current_lower_bound": CURRENT_LOWER_BOUND,
        "increment": INCREMENT,
        "source_binding_count": source_count,
        "paper": deepcopy(extension["paper"]),
        "real_money_action_usd": 0,
        "receipt_sha256": claimed_receipt,
    }
