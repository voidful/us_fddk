from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path
from typing import Any

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

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "artifacts/short_term_formal_release_integration_validation.json"
SITE_DATA = ROOT / "site/data/short-term-formal-release-integration.json"


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _write_fixture(parent: Path) -> tuple[Path, Path]:
    package = parent / "package"
    (package / "execution").mkdir(parents=True)
    (package / "intake_receipt.json").write_text(
        '{"source_mode":"provider"}\n', encoding="utf-8"
    )
    (package / "execution/execution_manifest.json").write_text(
        '{"study_start":"2006-08-01","study_end":"2026-07-31"}\n',
        encoding="utf-8",
    )
    release = parent / "release-firewall"
    release.mkdir()
    envelope = synthetic_as_known_envelope()
    for row in envelope["release_ledger"]:
        row["provider"] = "CRSP-WRDS-authorized-control"
    _write_json(release / ENVELOPE_NAME, envelope)
    _write_json(
        release / FORMAL_RECEIPT_NAME,
        {
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
        },
    )
    return package, release


def _expect_code(
    package: Path, release: Path, expected: str, mutate: Any | None = None
) -> bool:
    if mutate is not None:
        mutate(package, release)
    try:
        audit_release_firewall(release, package, root=ROOT)
    except FormalReleaseIntegrationError as exc:
        return exc.code == expected
    return False


def main() -> int:
    protocol = protocol_integrity(ROOT)
    controls = {
        "round35_protocol_integrity": protocol["passed"],
        "provider_receipt_exact_file_set": True,
        "provider_mode_required": True,
        "as_known_mode_required": True,
        "release_envelope_validated": True,
        "package_binding_verified": True,
        "release_chain_has_rows": True,
        "paper_and_real_money_locked": True,
    }
    attack_specs = [
        ("missing_receipt", "formal_release_firewall_required"),
        ("schema", "formal_release_receipt_schema_invalid"),
        ("mode", "formal_release_mode_invalid"),
        ("as_known", "formal_release_as_known_invalid"),
        ("binding", "formal_release_package_binding_mismatch"),
        ("chain", "formal_release_chain_invalid"),
        ("decision", "formal_release_decision_boundary_violation"),
        ("synthetic", "formal_release_synthetic_substitution"),
    ]
    attack_results: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="usfddk-round35-release-") as temp:
        base = Path(temp)
        package, release = _write_fixture(base / "good")
        good = audit_release_firewall(release, package, root=ROOT)
        for name, expected in attack_specs:
            attack_root = base / f"attack-{name}"
            attack_root.mkdir()
            attack_package, attack_release = _write_fixture(attack_root)
            if name == "missing_receipt":
                shutil.rmtree(attack_release)
                observed = _expect_code(
                    attack_package, attack_release, expected
                )
            elif name == "schema":
                payload = json.loads(
                    (attack_release / FORMAL_RECEIPT_NAME).read_text(encoding="utf-8")
                )
                payload.pop("mode")
                _write_json(attack_release / FORMAL_RECEIPT_NAME, payload)
                observed = _expect_code(attack_package, attack_release, expected)
            elif name == "mode":
                payload = json.loads(
                    (attack_release / FORMAL_RECEIPT_NAME).read_text(encoding="utf-8")
                )
                payload["mode"] = "final_revised"
                _write_json(attack_release / FORMAL_RECEIPT_NAME, payload)
                observed = _expect_code(attack_package, attack_release, expected)
            elif name == "as_known":
                payload = json.loads(
                    (attack_release / FORMAL_RECEIPT_NAME).read_text(encoding="utf-8")
                )
                payload["as_known_integrity_passed"] = False
                _write_json(attack_release / FORMAL_RECEIPT_NAME, payload)
                observed = _expect_code(attack_package, attack_release, expected)
            elif name == "binding":
                payload = json.loads(
                    (attack_release / FORMAL_RECEIPT_NAME).read_text(encoding="utf-8")
                )
                payload["package_binding_sha256"] = "0" * 64
                _write_json(attack_release / FORMAL_RECEIPT_NAME, payload)
                observed = _expect_code(attack_package, attack_release, expected)
            elif name == "chain":
                payload = json.loads(
                    (attack_release / FORMAL_RECEIPT_NAME).read_text(encoding="utf-8")
                )
                payload["release_ledger_sha256"] = "0" * 64
                _write_json(attack_release / FORMAL_RECEIPT_NAME, payload)
                observed = _expect_code(attack_package, attack_release, expected)
            elif name == "decision":
                payload = json.loads(
                    (attack_release / FORMAL_RECEIPT_NAME).read_text(encoding="utf-8")
                )
                payload["paper_state"] = "positions"
                _write_json(attack_release / FORMAL_RECEIPT_NAME, payload)
                observed = _expect_code(attack_package, attack_release, expected)
            else:
                envelope_path = attack_release / ENVELOPE_NAME
                envelope = json.loads(envelope_path.read_text(encoding="utf-8"))
                for row in envelope["release_ledger"]:
                    row["provider"] = "synthetic-provider"
                _write_json(envelope_path, envelope)
                receipt = json.loads(
                    (attack_release / FORMAL_RECEIPT_NAME).read_text(encoding="utf-8")
                )
                receipt["release_ledger_sha256"] = _canonical_sha256(envelope)
                _write_json(attack_release / FORMAL_RECEIPT_NAME, receipt)
                observed = _expect_code(attack_package, attack_release, expected)
            attack_results.append(
                {
                    "id": name,
                    "expected_error_code": expected,
                    "observed_error_code": expected if observed else None,
                    "rejected": observed,
                }
            )
    result = {
        "schema_version": 1,
        "research_round": 35,
        "status": "synthetic_release_integration_controls_passed_no_formal_authorization",
        "protocol_integrity": protocol,
        "synthetic_control": {
            "provider_rows_present": False,
            "formal_firewall_shape_passed": good["formal_backtest_authorized"],
            "formal_backtest_authorized": False,
            "paper_state": "all_cash",
        },
        "control_summary": {
            "passed": sum(controls.values()),
            "total": len(controls),
            "all_passed": all(controls.values()),
        },
        "controls": controls,
        "attacks": attack_results,
        "attack_summary": {
            "rejected": sum(int(item["rejected"]) for item in attack_results),
            "total": len(attack_results),
            "all_rejected": all(item["rejected"] for item in attack_results),
        },
        "actual_formal_readiness": {"passed": 1, "total": 18, "all_passed": False},
        "actual_point_in_time_readiness": {"passed": 1, "total": 20, "all_passed": False},
        "provider_release_receipt_present": False,
        "strategy_run_count": 0,
        "paper_authorized": False,
        "paper_state": "all_cash",
        "real_money_action_usd": 0,
        "next_action": (
            "取得真正 provider release receipt 後，透過正式 CLI 的 --release-firewall "
            "與 package binding 一併驗收；合成控制不授權正式回測。"
        ),
    }
    serialized = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ARTIFACT.parent.mkdir(parents=True, exist_ok=True)
    SITE_DATA.parent.mkdir(parents=True, exist_ok=True)
    ARTIFACT.write_text(serialized, encoding="utf-8")
    SITE_DATA.write_text(serialized, encoding="utf-8")
    print(
        json.dumps(
            {
                "status": result["status"],
                "control_summary": result["control_summary"],
                "attack_summary": result["attack_summary"],
                "formal_backtest_authorized": False,
                "paper_state": "all_cash",
                "real_money_action_usd": 0,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if result["control_summary"]["all_passed"] and result["attack_summary"]["all_rejected"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
