from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .restatement_firewall import (
    PROTOCOL_PATH as RESTATEMENT_PROTOCOL_PATH,
)
from .restatement_firewall import (
    PROTOCOL_SHA256 as RESTATEMENT_PROTOCOL_SHA256,
)
from .restatement_firewall import (
    validate_envelope,
)

RESEARCH_ROUND = 35
PROTOCOL_PATH = "docs/SHORT_TERM_FORMAL_RELEASE_INTEGRATION_PROTOCOL.md"
PROTOCOL_RECEIPT_PATH = "artifacts/short_term_formal_release_integration_protocol_receipt.json"
PROTOCOL_SHA256 = (
    "f02529ec9e09c4cdc3942769d1a8df11cab052654c62afb2e9f65f611000e1ed"
)
PROTOCOL_RECEIPT_SHA256 = (
    "0a43039e569a4561f89887c761c457d0d202d950bb4cda070210bb24460f78fd"
)
FORMAL_RECEIPT_NAME = "release_firewall.json"
ENVELOPE_NAME = "release_envelope.json"
REQUIRED_RECEIPT_FIELDS = {
    "schema_version",
    "source_mode",
    "mode",
    "as_known_integrity_passed",
    "provider_package_qualified",
    "formal_backtest_authorized",
    "package_binding_sha256",
    "release_ledger_sha256",
    "release_receipt_chain_passed",
    "source_record_count",
    "paper_authorized",
    "paper_state",
    "real_money_action_usd",
}


class FormalReleaseIntegrationError(ValueError):
    """Fail-closed error with a stable formal-readiness code."""

    def __init__(self, code: str, detail: str):
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}")


def _fail(code: str, detail: str) -> None:
    raise FormalReleaseIntegrationError(code, detail)


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _canonical_sha256(payload: Any) -> str:
    return hashlib.sha256(
        (
            json.dumps(
                payload,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            )
        ).encode("utf-8")
    ).hexdigest()


def _read_json(path: Path, code: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        _fail(code, f"{path.name}: {type(exc).__name__}")
    if not isinstance(payload, dict):
        _fail(code, f"{path.name} 必須是 JSON object")
    return payload


def _protocol_integrity(root: str | Path) -> dict[str, Any]:
    root_path = Path(root).resolve()
    try:
        receipt_path = root_path / PROTOCOL_RECEIPT_PATH
        receipt = _read_json(receipt_path, "formal_release_protocol_mismatch")
        checks = {
            PROTOCOL_PATH: _sha256_file(root_path / PROTOCOL_PATH) == PROTOCOL_SHA256,
            PROTOCOL_RECEIPT_PATH: _sha256_file(receipt_path)
            == PROTOCOL_RECEIPT_SHA256,
            receipt["parent_restatement_protocol"]["path"]: _sha256_file(
                root_path / receipt["parent_restatement_protocol"]["path"]
            )
            == receipt["parent_restatement_protocol"]["sha256"],
            receipt["parent_restatement_receipt"]["path"]: _sha256_file(
                root_path / receipt["parent_restatement_receipt"]["path"]
            )
            == receipt["parent_restatement_receipt"]["sha256"],
            receipt["parent_formal_preregistration_protocol"]["path"]: _sha256_file(
                root_path / receipt["parent_formal_preregistration_protocol"]["path"]
            )
            == receipt["parent_formal_preregistration_protocol"]["sha256"],
            receipt["parent_formal_preregistration_receipt"]["path"]: _sha256_file(
                root_path / receipt["parent_formal_preregistration_receipt"]["path"]
            )
            == receipt["parent_formal_preregistration_receipt"]["sha256"],
        }
        passed = bool(
            receipt.get("schema_version") == 1
            and receipt.get("research_round") == RESEARCH_ROUND
            and receipt.get("status")
            == "frozen_before_formal_provider_release_receipt"
            and receipt.get("protocol")
            == {"path": PROTOCOL_PATH, "sha256": PROTOCOL_SHA256}
            and receipt.get("reference_commits")
            == {
                "tst_wocker": "3372aa088328700feafeeb07c72ab832ea2d3ecb",
                "tw_block_warrant": "37463c54796ba36f4aac262519ea7fc2ef797de6",
                "tst_wocker_filter_lab": "06c87b7a1735877c9ccbab3a339c1742814a5058",
            }
            and receipt.get("provider_release_receipt_present_at_freeze") is False
            and receipt.get("formal_provider_run_present_at_freeze") is False
            and receipt.get("formal_backtest_authorized") is False
            and receipt.get("strategy_run_count") == 0
            and receipt.get("paper_authorized") is False
            and receipt.get("paper_state") == "all_cash"
            and receipt.get("real_money_action_usd") == 0
            and receipt.get("frozen_control_count") == 8
            and receipt.get("frozen_attack_count") == 8
            and all(checks.values())
        )
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        _fail("formal_release_protocol_mismatch", str(exc))
    if not passed:
        _fail("formal_release_protocol_mismatch", "Round35 protocol or parent hash mismatch")
    return {
        "passed": True,
        "frozen_at": receipt["frozen_at"],
        "git_head_at_freeze": receipt["git_head_at_freeze"],
        "hash_checks": checks,
        "restatement_protocol": {
            "path": RESTATEMENT_PROTOCOL_PATH,
            "sha256": RESTATEMENT_PROTOCOL_SHA256,
        },
    }


def protocol_integrity(root: str | Path) -> dict[str, Any]:
    return _protocol_integrity(root)


def package_binding_sha256(package: str | Path) -> str:
    package_path = Path(package)
    receipt = package_path / "intake_receipt.json"
    execution = package_path / "execution/execution_manifest.json"
    if not receipt.is_file() or not execution.is_file():
        _fail("formal_release_package_binding_mismatch", "package binding files missing")
    payload = {
        "intake_receipt_sha256": _sha256_file(receipt),
        "execution_manifest_sha256": _sha256_file(execution),
    }
    return _canonical_sha256(payload)


def audit_release_firewall(
    release_directory: str | Path,
    package: str | Path,
    *,
    root: str | Path,
) -> dict[str, Any]:
    """Validate provider release receipt and its as-known envelope binding."""

    protocol = protocol_integrity(root)
    directory = Path(release_directory)
    if not directory.is_dir():
        _fail("formal_release_firewall_required", "release firewall directory missing")
    actual_names = {item.name for item in directory.iterdir() if item.is_file()}
    if actual_names != {FORMAL_RECEIPT_NAME, ENVELOPE_NAME}:
        _fail("formal_release_receipt_schema_invalid", "release directory file set is not exact")
    receipt = _read_json(directory / FORMAL_RECEIPT_NAME, "formal_release_receipt_schema_invalid")
    envelope = _read_json(directory / ENVELOPE_NAME, "formal_release_receipt_schema_invalid")
    if set(receipt) != REQUIRED_RECEIPT_FIELDS:
        _fail("formal_release_receipt_schema_invalid", "release receipt fields are not exact")
    if receipt["schema_version"] != 1 or receipt["source_mode"] != "provider":
        _fail("formal_release_mode_invalid", "release receipt is not provider mode")
    if receipt["mode"] != "as_known":
        _fail("formal_release_mode_invalid", "formal entrypoint only accepts as_known")
    if receipt["as_known_integrity_passed"] is not True:
        _fail("formal_release_as_known_invalid", "as-known release check did not pass")
    if receipt["release_receipt_chain_passed"] is not True:
        _fail("formal_release_chain_invalid", "release receipt chain did not pass")
    if not isinstance(receipt["source_record_count"], int) or receipt["source_record_count"] <= 0:
        _fail("formal_release_chain_invalid", "release row receipt count is empty")
    envelope_summary = validate_envelope(envelope, root=root)
    if envelope_summary["mode"] != "as_known" or not envelope_summary["as_known_integrity_passed"]:
        _fail("formal_release_as_known_invalid", "envelope is not a valid as-known selection")
    if envelope_summary["future_selected_release_ids"]:
        _fail("formal_release_chain_invalid", "future release is selected")
    providers = {
        str(record.get("provider", ""))
        for record in envelope.get("release_ledger", [])
        if isinstance(record, dict)
    }
    if any(provider.casefold().startswith("synthetic") for provider in providers):
        _fail("formal_release_synthetic_substitution", "synthetic provider cannot enter provider mode")
    if receipt["release_ledger_sha256"] != _canonical_sha256(envelope):
        _fail("formal_release_chain_invalid", "release envelope SHA-256 does not match receipt")
    if receipt["source_record_count"] != len(envelope.get("rows", [])):
        _fail("formal_release_chain_invalid", "release row count does not match envelope")
    if receipt["package_binding_sha256"] != package_binding_sha256(package):
        _fail("formal_release_package_binding_mismatch", "release receipt is bound to another package")
    if receipt["provider_package_qualified"] is not True or receipt["formal_backtest_authorized"] is not True:
        _fail("formal_release_chain_invalid", "provider release receipt has not qualified the package")
    if receipt["paper_authorized"] is not False or receipt["paper_state"] != "all_cash" or receipt["real_money_action_usd"] != 0:
        _fail("formal_release_decision_boundary_violation", "release receipt tries to authorize Paper or real money")
    return {
        "protocol_integrity": protocol,
        "status": "provider_release_firewall_passed",
        "mode": receipt["mode"],
        "as_known_integrity_passed": True,
        "provider_package_qualified": True,
        "formal_backtest_authorized": True,
        "package_binding_verified": True,
        "release_ledger_sha256": receipt["release_ledger_sha256"],
        "source_record_count": receipt["source_record_count"],
        "paper_authorized": False,
        "paper_state": "all_cash",
        "real_money_action_usd": 0,
    }
