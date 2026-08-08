from __future__ import annotations

import json
from pathlib import Path

import pytest

from usfddk.formal_release_integration import (
    ENVELOPE_NAME,
    FORMAL_RECEIPT_NAME,
    FormalReleaseIntegrationError,
    _canonical_sha256,
    audit_release_firewall,
    package_binding_sha256,
    protocol_integrity,
)
from usfddk.restatement_firewall import synthetic_as_known_envelope


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def _package(tmp_path: Path) -> Path:
    package = tmp_path / "package"
    (package / "execution").mkdir(parents=True)
    (package / "intake_receipt.json").write_text('{"source_mode":"provider"}\n', encoding="utf-8")
    (package / "execution/execution_manifest.json").write_text(
        '{"study_start":"2006-08-01","study_end":"2026-07-31"}\n',
        encoding="utf-8",
    )
    return package


def _release(tmp_path: Path, package: Path) -> Path:
    directory = tmp_path / "release"
    directory.mkdir()
    envelope = synthetic_as_known_envelope()
    for record in envelope["release_ledger"]:
        record["provider"] = "CRSP-WRDS-authorized"
    _write_json(directory / ENVELOPE_NAME, envelope)
    receipt = {
        "schema_version": 1,
        "source_mode": "provider",
        "mode": "as_known",
        "as_known_integrity_passed": True,
        "provider_package_qualified": True,
        "formal_backtest_authorized": True,
        "package_binding_sha256": package_binding_sha256(package),
        "release_ledger_sha256": _canonical_sha256(envelope),
        "release_receipt_chain_passed": True,
        "source_record_count": len(envelope["rows"]),
        "paper_authorized": False,
        "paper_state": "all_cash",
        "real_money_action_usd": 0,
    }
    _write_json(directory / FORMAL_RECEIPT_NAME, receipt)
    return directory


def test_protocol_and_authorized_binding_pass(tmp_path: Path) -> None:
    assert protocol_integrity(".")["passed"] is True
    package = _package(tmp_path)
    release = _release(tmp_path, package)
    result = audit_release_firewall(release, package, root=".")
    assert result["status"] == "provider_release_firewall_passed"
    assert result["formal_backtest_authorized"] is True
    assert result["package_binding_verified"] is True
    assert result["paper_state"] == "all_cash"


def test_missing_release_receipt_is_required(tmp_path: Path) -> None:
    with pytest.raises(FormalReleaseIntegrationError) as exc_info:
        audit_release_firewall(tmp_path / "missing", _package(tmp_path), root=".")
    assert exc_info.value.code == "formal_release_firewall_required"


@pytest.mark.parametrize(
    ("mutation", "code"),
    [
        ("package", "formal_release_package_binding_mismatch"),
        ("mode", "formal_release_mode_invalid"),
        ("synthetic", "formal_release_synthetic_substitution"),
        ("decision", "formal_release_decision_boundary_violation"),
    ],
)
def test_provider_receipt_attacks_fail_closed(
    tmp_path: Path, mutation: str, code: str
) -> None:
    package = _package(tmp_path)
    release = _release(tmp_path, package)
    receipt_path = release / FORMAL_RECEIPT_NAME
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    envelope_path = release / ENVELOPE_NAME
    envelope = json.loads(envelope_path.read_text(encoding="utf-8"))
    if mutation == "package":
        receipt["package_binding_sha256"] = "0" * 64
    elif mutation == "mode":
        receipt["mode"] = "final_revised"
    elif mutation == "synthetic":
        envelope["release_ledger"][0]["provider"] = "synthetic-provider"
        envelope["release_ledger"][1]["provider"] = "synthetic-provider"
        _write_json(envelope_path, envelope)
        receipt["release_ledger_sha256"] = _canonical_sha256(envelope)
    else:
        receipt["paper_state"] = "positions"
    _write_json(receipt_path, receipt)
    with pytest.raises(FormalReleaseIntegrationError) as exc_info:
        audit_release_firewall(release, package, root=".")
    assert exc_info.value.code == code
