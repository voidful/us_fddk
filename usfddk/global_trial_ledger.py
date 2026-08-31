from __future__ import annotations

import hashlib
import json
import re
from copy import deepcopy
from pathlib import Path
from typing import Any

GLOBAL_TRIAL_LEDGER_PATH = "artifacts/short_term_global_trial_ledger.json"
GLOBAL_TRIAL_LEDGER_PROTOCOL_PATH = "docs/SHORT_TERM_GLOBAL_TRIAL_LEDGER_PROTOCOL.md"
GLOBAL_TRIAL_LEDGER_PROTOCOL_SHA256 = (
    "8c9fb4d515741283143192612d8017a86333086ed641ea0e45c2eb5c492c4451"
)
GLOBAL_TRIAL_ORIGINAL_PREREGISTRATION = 6_208
GLOBAL_TRIAL_CURRENT_LOWER_BOUND = 6_287
GLOBAL_TRIAL_EXPECTED_CHAIN_HEAD = (
    "c0e754cee5603c5eb9d2d142db1af6ec21b465d3492097b02112b94a18574085"
)
GLOBAL_TRIAL_EXPECTED_FAMILIES = (
    ("round18_formal_preregistration_anchor", 0, 6_208, 6_208),
    ("round24_baseline_multiplicity_nine_hypotheses", 6_208, 9, 6_217),
    ("round25_correlation_crowding_four_hypotheses", 6_217, 4, 6_221),
    ("round26_common_risk_residual_ten_hypotheses", 6_221, 10, 6_231),
    ("round27_rank_placebo_eight_hypotheses", 6_231, 8, 6_239),
    ("round28_reversal_volatility_eight_hypotheses", 6_239, 8, 6_247),
    ("round29_calendar_capital_six_comparisons", 6_247, 6, 6_253),
    ("round30_qqq_overlay_seven_comparisons", 6_253, 7, 6_260),
    ("round38_resonance_eight_comparisons", 6_260, 8, 6_268),
    ("round39_pullback_eight_comparisons", 6_268, 8, 6_276),
    ("local_retained_cross_asset_topk_minimum", 6_276, 3, 6_279),
    (
        "round41_form4_cluster_eight_reserved_comparisons",
        6_279,
        8,
        6_287,
    ),
)

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_GENESIS = "0" * 64
_TOP_KEYS = {
    "schema_version",
    "status",
    "count_semantics",
    "exact_global_count_claimed",
    "original_preregistration_trials",
    "current_lower_bound",
    "entries",
    "chain_head_sha256",
    "paper",
    "real_money_action_usd",
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
_PAPER = {
    "authorized": False,
    "state": "all_cash",
    "backfilled_trades": 0,
    "positions": [],
}


class GlobalTrialLedgerError(ValueError):
    """Fail-closed global multiplicity ledger error with a stable code."""

    def __init__(self, code: str, detail: str):
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}")


def _fail(code: str, detail: str) -> None:
    raise GlobalTrialLedgerError(code, detail)


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _canonical_sha256(value: dict[str, Any]) -> str:
    rendered = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(rendered).hexdigest()


def _read_payload(path: Path) -> tuple[dict[str, Any], str]:
    try:
        raw = path.read_bytes()
        value = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        _fail("trial_ledger_schema_mismatch", type(exc).__name__)
    if not isinstance(value, dict):
        _fail("trial_ledger_schema_mismatch", "ledger must be a JSON object")
    return value, hashlib.sha256(raw).hexdigest()


def _relative_source(root: Path, value: str) -> Path:
    relative = Path(value)
    if relative.is_absolute() or ".." in relative.parts:
        _fail(
            "trial_ledger_source_binding_mismatch",
            "tracked source path must remain repository-relative",
        )
    resolved = (root / relative).resolve()
    if root != resolved and root not in resolved.parents:
        _fail(
            "trial_ledger_source_binding_mismatch",
            "tracked source escaped repository root",
        )
    return resolved


def _validate_source_bindings(
    root: Path,
    entry: dict[str, Any],
) -> tuple[int, int]:
    bindings = entry.get("source_bindings")
    if not isinstance(bindings, list) or not bindings:
        _fail(
            "trial_ledger_source_binding_mismatch",
            "each entry needs at least one source binding",
        )
    tracked = 0
    opaque = 0
    labels: set[str] = set()
    for binding in bindings:
        if not isinstance(binding, dict) or set(binding) != _BINDING_KEYS:
            _fail(
                "trial_ledger_source_binding_mismatch",
                "source binding fields are not exact",
            )
        label = binding.get("label")
        digest = binding.get("sha256")
        if (
            not isinstance(label, str)
            or not label
            or label in labels
            or not isinstance(digest, str)
            or _SHA256.fullmatch(digest) is None
        ):
            _fail(
                "trial_ledger_source_binding_mismatch",
                "source label or SHA-256 is invalid",
            )
        labels.add(label)
        path_value = binding.get("path")
        if path_value is None:
            if entry.get("publication_state") != "local_retained_unpublished":
                _fail(
                    "trial_ledger_source_binding_mismatch",
                    "only the local-retained family may use opaque bindings",
                )
            opaque += 1
            continue
        if not isinstance(path_value, str) or not path_value:
            _fail(
                "trial_ledger_source_binding_mismatch",
                "tracked source path is invalid",
            )
        source_path = _relative_source(root, path_value)
        try:
            actual = _sha256_file(source_path)
        except OSError:
            _fail(
                "trial_ledger_source_binding_mismatch",
                f"tracked source is missing: {path_value}",
            )
        if actual != digest:
            _fail(
                "trial_ledger_source_binding_mismatch",
                f"tracked source hash drifted: {path_value}",
            )
        tracked += 1
    return tracked, opaque


def audit_global_trial_ledger_payload(
    payload: dict[str, Any],
    *,
    root: str | Path,
) -> dict[str, Any]:
    root_path = Path(root).resolve()
    if set(payload) != _TOP_KEYS:
        _fail("trial_ledger_schema_mismatch", "top-level fields are not exact")
    if (
        payload.get("schema_version") != 1
        or payload.get("status")
        != "append_only_global_trial_lower_bound_corrected_before_round41_result"
        or payload.get("count_semantics")
        != "conservative_minimum_hypothesis_path_lower_bound_not_exact_global_count"
        or payload.get("exact_global_count_claimed") is not False
    ):
        _fail(
            "trial_ledger_schema_mismatch",
            "lower-bound semantics or status drifted",
        )
    try:
        protocol_hash = _sha256_file(root_path / GLOBAL_TRIAL_LEDGER_PROTOCOL_PATH)
    except OSError:
        _fail("trial_ledger_protocol_mismatch", "ledger protocol is missing")
    if protocol_hash != GLOBAL_TRIAL_LEDGER_PROTOCOL_SHA256:
        _fail("trial_ledger_protocol_mismatch", "ledger protocol hash drifted")

    entries = payload.get("entries")
    if not isinstance(entries, list) or len(entries) != len(GLOBAL_TRIAL_EXPECTED_FAMILIES):
        _fail("trial_ledger_sequence_mismatch", "entry count is not frozen")
    family_ids: set[str] = set()
    prior_hash = _GENESIS
    prior_lower_bound = 0
    tracked_sources = 0
    opaque_sources = 0
    for sequence, (entry, expected) in enumerate(
        zip(entries, GLOBAL_TRIAL_EXPECTED_FAMILIES, strict=True)
    ):
        if not isinstance(entry, dict) or set(entry) != _ENTRY_KEYS:
            _fail(
                "trial_ledger_schema_mismatch",
                f"entry {sequence} fields are not exact",
            )
        family_id, expected_previous, expected_increment, expected_current = expected
        if entry.get("sequence") != sequence:
            _fail("trial_ledger_sequence_mismatch", "sequence is not contiguous")
        if entry.get("family_id") in family_ids:
            _fail("trial_ledger_duplicate_family", "family ID was reused")
        family_ids.add(entry.get("family_id"))
        if entry.get("family_id") != family_id:
            _fail("trial_ledger_sequence_mismatch", "frozen family order drifted")
        if entry.get("previous_lower_bound") != prior_lower_bound:
            _fail(
                "trial_ledger_lower_bound_regression",
                "entry does not continue the prior lower bound",
            )
        if (
            entry.get("previous_lower_bound") != expected_previous
            or entry.get("minimum_increment") != expected_increment
            or entry.get("current_lower_bound") != expected_current
        ):
            _fail(
                "trial_ledger_arithmetic_mismatch",
                "frozen lower-bound increment drifted",
            )
        increment = entry.get("minimum_increment")
        if not isinstance(increment, int) or isinstance(increment, bool) or increment < 0:
            _fail("trial_ledger_arithmetic_mismatch", "increment must be non-negative")
        if entry.get("current_lower_bound") != prior_lower_bound + increment:
            _fail("trial_ledger_arithmetic_mismatch", "lower-bound sum is invalid")
        if entry.get("previous_entry_sha256") != prior_hash:
            _fail("trial_ledger_chain_mismatch", "previous entry hash is invalid")
        canonical = deepcopy(entry)
        claimed_hash = canonical.pop("entry_sha256")
        if not isinstance(claimed_hash, str) or _canonical_sha256(canonical) != claimed_hash:
            _fail("trial_ledger_chain_mismatch", "entry hash is invalid")
        if sequence in set(range(1, 11)) and entry.get("seen_result") is not True:
            _fail(
                "trial_ledger_seen_result_regression",
                "an inspected result was changed back to unseen",
            )
        if sequence == 10 and entry.get("exact_increment_claimed") is not False:
            _fail(
                "trial_ledger_schema_mismatch",
                "local-retained family may only claim a lower bound",
            )
        if sequence == 11 and (
            entry.get("result_state") != "preregistered_unrun"
            or entry.get("seen_result") is not False
            or entry.get("publication_state") != "tracked_preregistered"
        ):
            _fail(
                "trial_ledger_seen_result_regression",
                "Round 41 preregistration state drifted",
            )
        checked, opaque = _validate_source_bindings(root_path, entry)
        tracked_sources += checked
        opaque_sources += opaque
        prior_hash = claimed_hash
        prior_lower_bound = entry["current_lower_bound"]

    if (
        payload.get("original_preregistration_trials") != GLOBAL_TRIAL_ORIGINAL_PREREGISTRATION
        or entries[0]["current_lower_bound"] != GLOBAL_TRIAL_ORIGINAL_PREREGISTRATION
    ):
        _fail(
            "trial_ledger_arithmetic_mismatch",
            "historical 6,208 anchor drifted",
        )
    if (
        payload.get("current_lower_bound") != GLOBAL_TRIAL_CURRENT_LOWER_BOUND
        or prior_lower_bound != GLOBAL_TRIAL_CURRENT_LOWER_BOUND
        or payload.get("chain_head_sha256") != GLOBAL_TRIAL_EXPECTED_CHAIN_HEAD
        or prior_hash != GLOBAL_TRIAL_EXPECTED_CHAIN_HEAD
    ):
        _fail("trial_ledger_tip_mismatch", "frozen ledger tip drifted")
    if payload.get("paper") != _PAPER or payload.get("real_money_action_usd") != 0:
        _fail(
            "trial_ledger_decision_boundary_violation",
            "trial governance cannot authorize Paper or real money",
        )
    return {
        "passed": True,
        "count_semantics": payload["count_semantics"],
        "exact_global_count_claimed": False,
        "original_preregistration_trials": GLOBAL_TRIAL_ORIGINAL_PREREGISTRATION,
        "current_lower_bound": GLOBAL_TRIAL_CURRENT_LOWER_BOUND,
        "entry_count": len(entries),
        "seen_result_family_count": sum(bool(entry["seen_result"]) for entry in entries),
        "reserved_unrun_family_count": sum(
            entry["result_state"] == "preregistered_unrun" for entry in entries
        ),
        "tracked_source_hashes_verified": tracked_sources,
        "opaque_local_source_hashes_retained": opaque_sources,
        "chain_head_sha256": prior_hash,
        "paper": deepcopy(_PAPER),
        "real_money_action_usd": 0,
    }


def audit_global_trial_ledger(*, root: str | Path) -> dict[str, Any]:
    root_path = Path(root).resolve()
    ledger_path = root_path / GLOBAL_TRIAL_LEDGER_PATH
    payload, ledger_sha256 = _read_payload(ledger_path)
    result = audit_global_trial_ledger_payload(payload, root=root_path)
    result["ledger_path"] = GLOBAL_TRIAL_LEDGER_PATH
    result["ledger_sha256"] = ledger_sha256
    result["protocol_path"] = GLOBAL_TRIAL_LEDGER_PROTOCOL_PATH
    result["protocol_sha256"] = GLOBAL_TRIAL_LEDGER_PROTOCOL_SHA256
    return result
