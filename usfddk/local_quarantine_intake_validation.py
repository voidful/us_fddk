from __future__ import annotations

import copy
import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any

import pandas as pd

from .authorized_data_handoff import _envelope, _synthetic_response
from .ciz_execution_extension_validation import (
    CONTROL_REQUIREMENTS,
    _write_ciz_control,
    _write_overlay_control,
)
from .local_quarantine_intake import (
    INTAKE_VERSION,
    _protocol_integrity,
    audit_local_quarantine_package,
    run_local_quarantine_intake,
)

EXPECTED_TRUE_READINESS = {"passed": 1, "total": 20, "all_passed": False}
EXPECTED_TRUE_DOCUMENT = {
    "passed": 1,
    "total": 12,
    "all_passed": False,
    "only_passed_gate": "01_preregistration_integrity",
}
CONTROL_PROVIDER = "authorized-synthetic-control-only"
CONTROL_PRODUCT = "round17-local-intake-shape-control-no-provider-rows"


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _control_response() -> dict[str, Any]:
    response = _synthetic_response()
    response["provider"] = CONTROL_PROVIDER
    response["provider_product"] = CONTROL_PRODUCT
    response["responded_at"] = "2026-08-03T20:10:00Z"
    response["license_attestation"]["attested_at"] = "2026-08-03T20:00:00Z"
    return response


def _align_manifest(path: Path) -> dict[str, Any]:
    manifest = json.loads(path.read_text(encoding="utf-8"))
    manifest["provider"] = CONTROL_PROVIDER
    manifest["provider_product"] = CONTROL_PRODUCT
    _write_json(path, manifest)
    return manifest


def _write_control_set(parent: Path) -> dict[str, Path]:
    parent.mkdir(parents=True, exist_ok=True)
    response_path = parent / "synthetic-response-envelope.json"
    _write_json(response_path, _envelope(_control_response()))
    ciz = _write_ciz_control(parent)
    overlay = _write_overlay_control(parent)
    _align_manifest(ciz / "ciz_manifest.json")
    _align_manifest(overlay / "execution_overlay_manifest.json")
    return {
        "response": response_path,
        "ciz": ciz,
        "overlay": overlay,
        "output": parent / "synthetic-derived-local-package",
    }


def _rehash_ciz_file(ciz: Path, name: str) -> None:
    manifest_path = ciz / "ciz_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    frame = pd.read_csv(ciz / name, dtype=str, keep_default_na=False, na_filter=False)
    manifest["files"][name] = {
        "sha256": _sha256_file(ciz / name),
        "rows": len(frame),
    }
    _write_json(manifest_path, manifest)


def _rehash_overlay(overlay: Path) -> None:
    manifest_path = overlay / "execution_overlay_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    frame = pd.read_csv(
        overlay / "benchmark_daily.csv",
        dtype=str,
        keep_default_na=False,
        na_filter=False,
    )
    manifest["files"]["benchmark_daily.csv"] = {
        "sha256": _sha256_file(overlay / "benchmark_daily.csv"),
        "rows": len(frame),
    }
    _write_json(manifest_path, manifest)


def _rewrite_response(path: Path, mutate: Any) -> None:
    envelope = json.loads(path.read_text(encoding="utf-8"))
    response = copy.deepcopy(envelope["response"])
    mutate(response)
    _write_json(path, _envelope(response))


def _error_code(exc: BaseException) -> str | None:
    return getattr(exc, "code", None)


def _run_attack(attack_id: str, root: Path, parent: Path) -> str | None:
    paths = _write_control_set(parent)
    response = paths["response"]
    ciz = paths["ciz"]
    overlay = paths["overlay"]
    output = paths["output"]
    source_mode = "synthetic_control"

    if attack_id == "01":
        response = Path(response.name)
    elif attack_id == "02":
        response = root / "schemas/short_term_authorized_data_response.schema.json"
    elif attack_id == "03":
        os.symlink(ciz / "stk_delists.csv", ciz / "linked-delists.csv")
    elif attack_id == "04":
        output.mkdir()
    elif attack_id == "05":
        envelope = json.loads(response.read_text(encoding="utf-8"))
        envelope["response"]["provider"] = "changed-without-receipt"
        _write_json(response, envelope)
    elif attack_id == "06":
        source_mode = "provider"
    elif attack_id == "07":
        _rewrite_response(
            response,
            lambda value: value.__setitem__("provider", "different-provider"),
        )
    elif attack_id == "08":
        _rewrite_response(
            response,
            lambda value: value.__setitem__("provider_product", "different-product"),
        )
    elif attack_id == "09":
        manifest_path = overlay / "execution_overlay_manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["provider"] = "different-overlay-provider"
        _write_json(manifest_path, manifest)
    elif attack_id == "10":
        manifest_path = overlay / "execution_overlay_manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["license_attestation"]["authorized_for_local_research"] = False
        _write_json(manifest_path, manifest)
    elif attack_id == "11":
        def late_document(value: dict[str, Any]) -> None:
            value["responded_at"] = "2026-08-03T23:00:00Z"

        _rewrite_response(response, late_document)
    elif attack_id == "12":
        path = ciz / "stk_delists.csv"
        path.write_text(path.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    elif attack_id == "13":
        name = "membership_announcements.csv"
        path = ciz / name
        frame = pd.read_csv(path, dtype=str, keep_default_na=False, na_filter=False)
        frame.loc[0, "AnnouncedAt"] = "2026-07-01T12:00:00Z"
        frame.to_csv(path, index=False, lineterminator="\n")
        _rehash_ciz_file(ciz, name)
    elif attack_id == "14":
        path = overlay / "benchmark_daily.csv"
        frame = pd.read_csv(path, dtype=str, keep_default_na=False, na_filter=False)
        first_qqq = frame.loc[frame["asset_id"] == "QQQ"].index[0]
        frame = frame.drop(index=first_qqq)
        frame.to_csv(path, index=False, lineterminator="\n")
        _rehash_overlay(overlay)

    try:
        run_local_quarantine_intake(
            response,
            ciz,
            overlay,
            output,
            root=root,
            source_mode=source_mode,
            requirements=CONTROL_REQUIREMENTS,
        )
        if attack_id == "15":
            manifest_path = output / "execution/execution_manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["status"] = "synthetic_execution_extension_built"
            _write_json(manifest_path, manifest)
            audit_local_quarantine_package(
                output,
                root=root,
                source_mode="synthetic_control",
                requirements=CONTROL_REQUIREMENTS,
            )
        elif attack_id == "16":
            (output / "ledger/manifest.json").chmod(0o644)
            audit_local_quarantine_package(
                output,
                root=root,
                source_mode="synthetic_control",
                requirements=CONTROL_REQUIREMENTS,
            )
    except Exception as exc:  # noqa: BLE001 - the harness records stable upstream codes.
        return _error_code(exc)
    return None


def run_local_quarantine_intake_validation(root: str | Path) -> dict[str, Any]:
    root_path = Path(root).resolve()
    protocol = _protocol_integrity(root_path)
    with tempfile.TemporaryDirectory(prefix="usfddk-round17-intake-") as temporary:
        temp_root = Path(temporary)
        control_paths = _write_control_set(temp_root / "control")
        control_receipt = run_local_quarantine_intake(
            control_paths["response"],
            control_paths["ciz"],
            control_paths["overlay"],
            control_paths["output"],
            root=root_path,
            source_mode="synthetic_control",
            requirements=CONTROL_REQUIREMENTS,
        )
        control_audit = audit_local_quarantine_package(
            control_paths["output"],
            root=root_path,
            source_mode="synthetic_control",
            requirements=CONTROL_REQUIREMENTS,
        )
        attack_specs = [
            ("01", "response 使用相對路徑", "intake_path_not_absolute"),
            ("02", "輸入位於 repository 內", "intake_path_inside_repository"),
            ("03", "CIZ 樹加入 symlink", "intake_symlink_or_special_file"),
            ("04", "輸出目錄已存在", "intake_output_exists"),
            ("05", "response hash 不符", "response_receipt_mismatch"),
            ("06", "provider mode 使用 synthetic response", "intake_source_mode_mismatch"),
            ("07", "response 與 CIZ provider 不同", "intake_provider_binding_mismatch"),
            ("08", "response 與 CIZ product 不同", "intake_product_binding_mismatch"),
            ("09", "overlay provider 不同", "intake_overlay_binding_mismatch"),
            ("10", "overlay 本地研究授權 false", "intake_license_binding_invalid"),
            ("11", "文件時間遲於 export", "intake_timestamp_order_invalid"),
            ("12", "CIZ CSV 改動但收據不改", "source_receipt_invalid"),
            ("13", "成分公布時間晚於生效", "membership_effective_date_substitution"),
            ("14", "QQQ 缺一個必要 session", "benchmark_session_missing"),
            ("15", "輸出改成舊 synthetic status", "intake_source_mode_mismatch"),
            ("16", "輸出檔案變成 world-readable", "intake_private_permissions_invalid"),
        ]
        attacks = []
        for attack_id, label, expected in attack_specs:
            observed = _run_attack(
                attack_id,
                root_path,
                temp_root / f"attack-{attack_id}",
            )
            attacks.append(
                {
                    "id": attack_id,
                    "label": label,
                    "expected_error_code": expected,
                    "observed_error_code": observed,
                    "rejected": observed == expected,
                }
            )

    rejected = sum(int(item["rejected"]) for item in attacks)
    readiness = json.loads(
        (root_path / "artifacts/short_term_point_in_time_readiness.json").read_text(
            encoding="utf-8"
        )
    )
    handoff = json.loads(
        (root_path / "artifacts/short_term_authorized_data_handoff.json").read_text(
            encoding="utf-8"
        )
    )
    if readiness["gate_summary"] != EXPECTED_TRUE_READINESS:
        raise ValueError("真實 point-in-time readiness 已漂移；不得沿用 Round 17 結論")
    if handoff["actual_document_handoff"] != EXPECTED_TRUE_DOCUMENT:
        raise ValueError("真實文件交接狀態已漂移；不得沿用 Round 17 結論")
    control_ok = bool(
        control_receipt["gate_summary"]
        == {"passed": 16, "total": 16, "all_passed": True}
        and control_audit["gate_summary"]
        == {"passed": 16, "total": 16, "all_passed": True}
        and control_receipt["source_mode"] == "synthetic_control"
        and control_receipt["formal_stock_backtest_input_ready"] is False
    )
    attacks_ok = rejected == len(attacks) == 16
    return {
        "schema_version": 1,
        "research_round": 17,
        "intake_version": INTAKE_VERSION,
        "status": (
            "synthetic_local_intake_passed_provider_inputs_still_missing"
            if control_ok and attacks_ok
            else "local_intake_control_incomplete_or_failed"
        ),
        "evidence_as_of": "2026-08-04",
        "protocol_integrity": protocol,
        "gap_closed": {
            "finding": "Round 15 manifest status 只接受 synthetic，不能標示真實 provider mode。",
            "old_status": "synthetic_execution_extension_built",
            "new_synthetic_status": "synthetic_local_quarantine_extension_built",
            "new_provider_status": "authorized_provider_local_quarantine_extension_built",
            "round15_files_modified": False,
        },
        "synthetic_control": {
            "gate_summary": control_audit["gate_summary"],
            "gates": control_audit["gates"],
            "point_in_time_gate_summary": control_audit[
                "point_in_time_gate_summary"
            ],
            "extension_gate_summary": control_audit["extension_gate_summary"],
            "counts": control_audit["counts"],
            "private_permissions": control_audit["private_permissions"],
            "formal_stock_backtest_input_ready": control_receipt[
                "formal_stock_backtest_input_ready"
            ],
            "contains_provider_rows": False,
        },
        "attacks": attacks,
        "attack_summary": {
            "rejected": rejected,
            "total": len(attacks),
            "all_rejected": attacks_ok,
        },
        "actual_local_intake": {
            "passed": 1,
            "total": 16,
            "all_passed": False,
            "only_passed_gate": "01_preregistration_integrity",
        },
        "actual_document_handoff": handoff["actual_document_handoff"],
        "actual_point_in_time_readiness": readiness["gate_summary"],
        "explicit_external_paths_provided": False,
        "provider_mode_run_count": 0,
        "authorized_provider_response_received": False,
        "authorized_provider_sample_received": False,
        "formal_stock_backtest_input_ready": False,
        "formal_stock_backtest_completed": False,
        "strategy_rule_changed": False,
        "paper": {
            "authorized": False,
            "state": "all_cash",
            "backfilled_trades": 0,
            "positions": [],
        },
        "real_money_action_usd": 0,
        "next_action": (
            "使用者明確提供 repository 外四個絕對路徑後，才以 provider mode 運行；"
            "16/16 只准進入一次固定正式回測，不會自動建立 Paper。"
        ),
        "disclaimer": (
            "合成 16/16 只證明本地隔離匯入器及 provider-mode 標示會關門；"
            "不證明供應商、數據、策略、Paper 或盈利通過。"
        ),
    }
