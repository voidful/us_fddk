from __future__ import annotations

import hashlib
import json
import os
import stat
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

from .authorized_data_handoff import (
    AuthorizedDataHandoffError,
    validate_authorized_data_response,
)
from .ciz_execution_extension import (
    EXECUTION_EXTENSION_PROTOCOL_SHA256,
    EXECUTION_EXTENSION_VERSION,
    FROZEN_DIVIDEND_POLICY,
    FROZEN_EXECUTION_CLOCK,
    FROZEN_PRICE_BASIS,
    FROZEN_PRIMARY_COST_BPS,
    FROZEN_QQQ_FALLBACK,
    FROZEN_SIGNAL_POLICY,
    FROZEN_STRESS_COST_BPS,
    STRATEGY_PROTOCOL_SHA256,
    _audit_entitlements,
    _audit_removal_rows,
    _audit_signal_rows,
    _calendar_and_signals,
    _load_execution_layer,
    _read_ledger,
    _validate_benchmarks,
    audit_point_in_time_bundle,
    transform_crsp_ciz_execution_bundle,
)
from .point_in_time_ledger import PointInTimeRequirements

INTAKE_VERSION = "round17-local-quarantine-intake-v1"
INTAKE_PROTOCOL_SHA256 = (
    "1167310d566c0208befc09f24d6391fe4dc3efd606a09f8b16e983c2abdf79a8"
)
INTAKE_RECEIPT_PATH = (
    "artifacts/short_term_local_quarantine_intake_protocol_receipt.json"
)
SOURCE_MODES = {"provider", "synthetic_control"}
MODE_STATUS = {
    "provider": "authorized_provider_local_quarantine_extension_built",
    "synthetic_control": "synthetic_local_quarantine_extension_built",
}
RESPONSE_STATUS = {
    "provider": "provider_document_response",
    "synthetic_control": "synthetic_document_response_control",
}
OWNER_DIRECTORY_MODE = 0o700
OWNER_FILE_MODE = 0o600
INTAKE_RECEIPT_KEYS = {
    "schema_version",
    "intake_version",
    "status",
    "source_mode",
    "provider",
    "provider_product",
    "generated_at",
    "response_sha256",
    "manifest_receipts",
    "source_as_of_date",
    "study_start",
    "study_end",
    "gate_summary",
    "point_in_time_gate_summary",
    "extension_gate_summary",
    "counts",
    "private_permissions",
    "contains_absolute_paths",
    "credentials_included",
    "provider_rows_published",
    "formal_stock_backtest_input_ready",
    "formal_stock_backtest_completed",
    "strategy_rule_changed",
    "strategy_run_count",
    "paper",
    "real_money_action_usd",
}
MANIFEST_RECEIPT_KEYS = {
    "ciz_manifest.json",
    "execution_overlay_manifest.json",
    "ledger/manifest.json",
    "execution/execution_manifest.json",
}


class LocalQuarantineIntakeError(ValueError):
    """Fail-closed local intake error with a stable semantic code."""

    def __init__(self, code: str, detail: str):
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}")


def _fail(code: str, detail: str) -> None:
    raise LocalQuarantineIntakeError(code, detail)


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
            allow_nan=False,
        )
        + "\n",
        encoding="utf-8",
    )


def _read_json(path: Path, code: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        _fail(code, f"{path.name}: {type(exc).__name__}")
    if not isinstance(payload, dict):
        _fail(code, f"{path.name} 必須是 JSON object")
    return payload


def _timestamp(value: object, field: str) -> datetime:
    raw = str(value)
    if not raw.endswith("Z") and not (
        len(raw) >= 6 and raw[-6] in {"+", "-"} and raw[-3] == ":"
    ):
        _fail("intake_timestamp_order_invalid", f"{field} 缺 UTC offset")
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        _fail("intake_timestamp_order_invalid", f"{field} 無效")
    if parsed.tzinfo is None:
        _fail("intake_timestamp_order_invalid", f"{field} 沒有 timezone")
    return parsed


def _protocol_integrity(root: Path) -> dict[str, Any]:
    receipt_path = root / INTAKE_RECEIPT_PATH
    try:
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        tracked = [
            value
            for value in receipt.values()
            if isinstance(value, dict) and set(value) == {"path", "sha256"}
        ]
        hash_checks = {
            item["path"]: _sha256_file(root / item["path"]) == item["sha256"]
            for item in tracked
        }
        passed = bool(
            receipt["status"]
            == "frozen_with_error_code_erratum_before_implementation"
            and receipt["protocol"]["sha256"] == INTAKE_PROTOCOL_SHA256
            and receipt["erratum_scope"]
            == "existing_error_code_names_only_attacks_12_to_14"
            and receipt["frozen_prerequisite_hash_count"] == 16
            and receipt["frozen_control_gate_count"] == 16
            and receipt["frozen_attack_count"] == 16
            and receipt["provider_mode_bridge_implemented_at_freeze"] is False
            and receipt["local_intake_cli_implemented_at_freeze"] is False
            and receipt["authorized_provider_response_present_at_freeze"] is False
            and receipt["authorized_provider_sample_present_at_freeze"] is False
            and receipt["strategy_rule_changed"] is False
            and receipt["real_money_action_usd"] == 0
            and len(tracked) == 17
            and all(hash_checks.values())
        )
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError):
        receipt = {}
        hash_checks = {}
        passed = False
    if not passed:
        _fail("intake_protocol_integrity_failed", "Round 17 協議或前置雜湊不完整")
    return {
        "passed": True,
        "frozen_at": receipt["frozen_at"],
        "erratum_at": receipt["erratum_at"],
        "git_head_at_freeze": receipt["git_head_at_freeze"],
        "hash_checks": hash_checks,
    }


def _inside(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def _reject_links_and_special(root: Path) -> None:
    if root.is_symlink():
        _fail("intake_symlink_or_special_file", f"{root.name} 是 symlink")
    for directory, directories, files in os.walk(root, followlinks=False):
        base = Path(directory)
        for name in [*directories, *files]:
            item = base / name
            mode = item.lstat().st_mode
            if stat.S_ISLNK(mode) or not (stat.S_ISDIR(mode) or stat.S_ISREG(mode)):
                _fail(
                    "intake_symlink_or_special_file",
                    f"{item.name} 是連結或特殊檔案",
                )


def _resolve_input(path: str | Path, *, root: Path, kind: str) -> Path:
    candidate = Path(path)
    if not candidate.is_absolute():
        _fail("intake_path_not_absolute", f"{kind} 必須使用絕對路徑")
    if candidate.is_symlink():
        _fail("intake_symlink_or_special_file", f"{kind} 不可是 symlink")
    try:
        resolved = candidate.resolve(strict=True)
    except OSError:
        _fail("intake_path_missing", f"{kind} 不存在")
    if _inside(resolved, root.resolve()):
        _fail("intake_path_inside_repository", f"{kind} 位於 repository 內")
    return resolved


def _resolve_output(path: str | Path, *, root: Path) -> Path:
    candidate = Path(path)
    if not candidate.is_absolute():
        _fail("intake_path_not_absolute", "輸出必須使用絕對路徑")
    if candidate.exists() or candidate.is_symlink():
        _fail("intake_output_exists", "輸出位置已存在或是 symlink")
    try:
        parent = candidate.parent.resolve(strict=True)
    except OSError:
        _fail("intake_path_missing", "輸出父目錄不存在")
    resolved = parent / candidate.name
    if _inside(resolved, root.resolve()):
        _fail("intake_path_inside_repository", "輸出位於 repository 內")
    return resolved


def _preflight_paths(
    response_path: str | Path,
    ciz_bundle: str | Path,
    execution_overlay: str | Path,
    output_bundle: str | Path,
    *,
    root: Path,
) -> tuple[Path, Path, Path, Path]:
    response = _resolve_input(response_path, root=root, kind="response")
    ciz = _resolve_input(ciz_bundle, root=root, kind="CIZ bundle")
    overlay = _resolve_input(execution_overlay, root=root, kind="execution overlay")
    output = _resolve_output(output_bundle, root=root)
    if not response.is_file() or not ciz.is_dir() or not overlay.is_dir():
        _fail("intake_path_missing", "response 必須是檔案；兩個輸入包必須是目錄")
    _reject_links_and_special(ciz)
    _reject_links_and_special(overlay)
    return response, ciz, overlay, output


def _license_ok(value: object) -> bool:
    return bool(
        isinstance(value, dict)
        and value.get("authorized_for_local_research") is True
        and isinstance(value.get("raw_redistribution_allowed"), bool)
        and str(value.get("reference", "")).strip()
        and str(value.get("attested_at", "")).strip()
    )


def _validate_identity_and_time(
    response: dict[str, Any],
    ciz_manifest: dict[str, Any],
    overlay_manifest: dict[str, Any],
) -> None:
    provider = str(response.get("provider", "")).strip()
    product = str(response.get("provider_product", "")).strip()
    if provider != str(ciz_manifest.get("provider", "")).strip():
        _fail("intake_provider_binding_mismatch", "response 與 CIZ provider 不同")
    if product != str(ciz_manifest.get("provider_product", "")).strip():
        _fail("intake_product_binding_mismatch", "response 與 CIZ product 不同")
    if (
        provider != str(overlay_manifest.get("provider", "")).strip()
        or product != str(overlay_manifest.get("provider_product", "")).strip()
    ):
        _fail("intake_overlay_binding_mismatch", "overlay provider／product 未綁定")

    licenses = (
        response.get("license_attestation"),
        ciz_manifest.get("license_attestation"),
        overlay_manifest.get("license_attestation"),
    )
    if not all(_license_ok(value) for value in licenses):
        _fail("intake_license_binding_invalid", "三層本地研究授權未完整綁定")

    response_time = _timestamp(response["responded_at"], "response responded_at")
    response_license = _timestamp(
        response["license_attestation"]["attested_at"],
        "response license attested_at",
    )
    ciz_license = _timestamp(
        ciz_manifest["license_attestation"]["attested_at"],
        "CIZ license attested_at",
    )
    ciz_export = _timestamp(ciz_manifest["exported_at"], "CIZ exported_at")
    ciz_import = _timestamp(ciz_manifest["first_imported_at"], "CIZ first_imported_at")
    overlay_license = _timestamp(
        overlay_manifest["license_attestation"]["attested_at"],
        "overlay license attested_at",
    )
    overlay_export = _timestamp(
        overlay_manifest["exported_at"], "overlay exported_at"
    )
    overlay_import = _timestamp(
        overlay_manifest["first_imported_at"], "overlay first_imported_at"
    )
    if not (
        response_time <= ciz_export
        and response_time <= overlay_export
        and response_license <= ciz_export
        and response_license <= overlay_export
        and ciz_license <= ciz_export <= ciz_import
        and overlay_license <= overlay_export <= overlay_import
    ):
        _fail("intake_timestamp_order_invalid", "文件／授權／匯出／首次匯入次序不符")


def _validate_document(
    envelope: dict[str, Any],
    *,
    root: Path,
    source_mode: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    if source_mode not in SOURCE_MODES:
        _fail("intake_source_mode_mismatch", "source mode 不受支持")
    response = envelope.get("response")
    if not isinstance(response, dict):
        _fail("response_schema_mismatch", "response envelope 缺 object")
    if response.get("status") != RESPONSE_STATUS[source_mode]:
        _fail("intake_source_mode_mismatch", "文件 status 與 source mode 不同")
    try:
        validation = validate_authorized_data_response(
            envelope,
            root=root,
            allow_synthetic_control=source_mode == "synthetic_control",
        )
    except AuthorizedDataHandoffError as exc:
        if exc.code in {"license_attestation_invalid", "license_timestamp_invalid"}:
            _fail("intake_license_binding_invalid", exc.detail)
        raise
    return response, validation


def _assert_authorized_manifest_policies(
    manifest: dict[str, Any],
    ledger: Path,
    *,
    source_mode: str,
) -> None:
    if manifest["base_ledger_manifest_sha256"] != _sha256_file(
        ledger / "manifest.json"
    ):
        _fail("base_ledger_binding_mismatch", "base ledger manifest SHA-256 不符")
    if (
        manifest["schema_version"] != 1
        or manifest["status"] != MODE_STATUS[source_mode]
        or manifest["transform_version"] != EXECUTION_EXTENSION_VERSION
        or manifest["protocol_sha256"] != EXECUTION_EXTENSION_PROTOCOL_SHA256
    ):
        _fail("intake_source_mode_mismatch", "provider-mode manifest 狀態或版本不符")
    if manifest["price_basis"] != FROZEN_PRICE_BASIS:
        _fail("benchmark_price_policy_invalid", "基準價格政策漂移")
    if manifest["signal_policy"] != FROZEN_SIGNAL_POLICY:
        _fail("signal_calendar_invalid", "月末訊號政策漂移")
    if manifest["execution_clock"] != FROZEN_EXECUTION_CLOCK:
        _fail("execution_clock_violation", "D+1 open 時鐘漂移")
    if manifest["dividend_cash_policy"] != FROZEN_DIVIDEND_POLICY:
        _fail("dividend_entitlement_mismatch", "派息現金政策漂移")
    if manifest["qqq_fallback_asset_id"] != FROZEN_QQQ_FALLBACK:
        _fail("qqq_fallback_binding_invalid", "補位不是同一 QQQ 序列")
    if (
        manifest["primary_cost_bps"] != FROZEN_PRIMARY_COST_BPS
        or manifest["stress_cost_bps"] != FROZEN_STRESS_COST_BPS
        or manifest["strategy_protocol_sha256"] != STRATEGY_PROTOCOL_SHA256
    ):
        _fail("strategy_cost_policy_mismatch", "策略成本或雜湊漂移")


def _permissions_ok(package: Path) -> bool:
    for item in [package, *package.rglob("*")]:
        mode = stat.S_IMODE(item.stat().st_mode)
        if item.is_dir() and mode != OWNER_DIRECTORY_MODE:
            return False
        if item.is_file() and mode != OWNER_FILE_MODE:
            return False
    return True


def _apply_private_permissions(package: Path) -> None:
    for item in sorted(
        (entry for entry in package.rglob("*") if entry.is_file()),
        key=lambda entry: len(entry.parts),
        reverse=True,
    ):
        item.chmod(OWNER_FILE_MODE)
    for item in sorted(
        (entry for entry in package.rglob("*") if entry.is_dir()),
        key=lambda entry: len(entry.parts),
        reverse=True,
    ):
        item.chmod(OWNER_DIRECTORY_MODE)
    package.chmod(OWNER_DIRECTORY_MODE)


def _validate_intake_receipt(
    package: Path,
    *,
    source_mode: str,
    counts: dict[str, int],
    ledger_manifest: dict[str, Any],
    execution_manifest: dict[str, Any],
) -> None:
    receipt_path = package / "intake_receipt.json"
    receipt = _read_json(receipt_path, "intake_receipt_invalid")
    if set(receipt) != INTAKE_RECEIPT_KEYS:
        _fail("intake_receipt_invalid", "intake receipt keys 不符")
    manifest_receipts = receipt["manifest_receipts"]
    if (
        not isinstance(manifest_receipts, dict)
        or set(manifest_receipts) != MANIFEST_RECEIPT_KEYS
        or any(
            not isinstance(value, str)
            or len(value) != 64
            or any(character not in "0123456789abcdef" for character in value)
            for value in manifest_receipts.values()
        )
    ):
        _fail("intake_receipt_invalid", "manifest receipt 集合或 SHA-256 無效")
    response_sha256 = receipt["response_sha256"]
    if (
        not isinstance(response_sha256, str)
        or len(response_sha256) != 64
        or any(character not in "0123456789abcdef" for character in response_sha256)
    ):
        _fail("intake_receipt_invalid", "response SHA-256 無效")
    if (
        manifest_receipts["ledger/manifest.json"]
        != _sha256_file(package / "ledger/manifest.json")
        or manifest_receipts["execution/execution_manifest.json"]
        != _sha256_file(package / "execution/execution_manifest.json")
        or manifest_receipts["execution_overlay_manifest.json"]
        != execution_manifest["source_overlay_manifest_sha256"]
    ):
        _fail("intake_receipt_invalid", "輸出 manifest 與 intake receipt 不對數")
    expected_gate = {"passed": 16, "total": 16, "all_passed": True}
    expected_point_in_time = {"passed": 20, "total": 20, "all_passed": True}
    if (
        receipt["schema_version"] != 1
        or receipt["intake_version"] != INTAKE_VERSION
        or receipt["status"] != f"{source_mode}_local_quarantine_intake_passed"
        or receipt["source_mode"] != source_mode
        or receipt["provider"] != ledger_manifest["provider"]
        or receipt["provider_product"] != ledger_manifest["provider_product"]
        or receipt["source_as_of_date"] != ledger_manifest["as_of_date"]
        or receipt["generated_at"] != execution_manifest["generated_at"]
        or receipt["study_start"] != execution_manifest["study_start"]
        or receipt["study_end"] != execution_manifest["study_end"]
        or receipt["gate_summary"] != expected_gate
        or receipt["point_in_time_gate_summary"] != expected_point_in_time
        or receipt["extension_gate_summary"] != expected_gate
        or receipt["counts"] != counts
        or receipt["private_permissions"] is not True
        or receipt["contains_absolute_paths"] is not False
        or receipt["credentials_included"] is not False
        or receipt["provider_rows_published"] is not False
        or receipt["formal_stock_backtest_input_ready"] is not (
            source_mode == "provider"
        )
        or receipt["formal_stock_backtest_completed"] is not False
        or receipt["strategy_rule_changed"] is not False
        or receipt["strategy_run_count"] != 0
        or receipt["paper"]
        != {
            "authorized": False,
            "state": "all_cash",
            "backfilled_trades": 0,
            "positions": [],
        }
        or receipt["real_money_action_usd"] != 0
    ):
        _fail("intake_receipt_invalid", "intake receipt 狀態或決策邊界不符")


def audit_local_quarantine_package(
    package: str | Path,
    *,
    root: str | Path,
    source_mode: str,
    requirements: PointInTimeRequirements | None = None,
    require_receipt: bool = True,
) -> dict[str, Any]:
    """Audit a derived local package without returning or publishing raw rows."""

    if source_mode not in SOURCE_MODES:
        _fail("intake_source_mode_mismatch", "source mode 不受支持")
    root_path = Path(root)
    package_path = Path(package)
    protocol = _protocol_integrity(root_path)
    if not package_path.is_dir():
        _fail("intake_path_missing", "本地輸出 package 不存在")
    manifest, frames = _load_execution_layer(package_path)
    ledger = package_path / "ledger"
    _assert_authorized_manifest_policies(
        manifest,
        ledger,
        source_mode=source_mode,
    )
    ledger_audit = audit_point_in_time_bundle(
        ledger,
        root=root_path,
        requirements=requirements or PointInTimeRequirements(),
    )
    if not ledger_audit["gate_summary"]["all_passed"]:
        _fail("base_ledger_binding_mismatch", "base ledger 未通過 20 道閘門")
    ledger_manifest, tables = _read_ledger(ledger)
    sessions, signals = _calendar_and_signals(
        tables["trading_calendar.csv"],
        manifest["study_start"],
        manifest["study_end"],
    )
    _audit_entitlements(
        tables["corporate_actions.csv"], frames["cash_entitlements.csv"]
    )
    _audit_signal_rows(
        tables["membership_history.csv"],
        tables["daily_prices.csv"],
        signals,
        frames["signal_eligibility.csv"],
    )
    _audit_removal_rows(
        tables["security_outcomes.csv"],
        tables["daily_prices.csv"],
        sessions,
        signals,
        frames["removal_execution_windows.csv"],
    )
    _validate_benchmarks(
        frames["benchmark_daily.csv"],
        sessions,
        signals,
        manifest["study_start"],
        manifest["study_end"],
    )
    counts = {
        "signals": len(signals),
        "cash_entitlements": len(frames["cash_entitlements.csv"]),
        "signal_eligibility_rows": len(frames["signal_eligibility.csv"]),
        "removal_execution_windows": len(frames["removal_execution_windows.csv"]),
        "benchmark_rows": len(frames["benchmark_daily.csv"]),
    }
    if require_receipt:
        _validate_intake_receipt(
            package_path,
            source_mode=source_mode,
            counts=counts,
            ledger_manifest=ledger_manifest,
            execution_manifest=manifest,
        )
    if not _permissions_ok(package_path):
        _fail(
            "intake_private_permissions_invalid",
            "輸出目錄或檔案不是 owner-only",
        )

    gate_rows = [
        ("01", "事前凍結完整性", "Round 17 協議及十六份前置雜湊完整"),
        ("02", "模式明確", f"source_mode={source_mode}；status 一致"),
        ("03", "絕對外部路徑", "輸入及輸出均在 repository 外"),
        ("04", "無連結或特殊檔", "輸入樹只含正常檔案及目錄"),
        ("05", "新輸出及原子寫入", "新 staging 完成後才 rename"),
        ("06", "文件 envelope 對數", "Round 16 request、schema 及 response hash 通過"),
        ("07", "正式／合成隔離", "provider 與 synthetic status 不可互換"),
        ("08", "供應商及產品綁定", "response、CIZ 及 overlay 身份一致"),
        ("09", "授權邊界綁定", "三層本地研究授權及 reference 完整"),
        ("10", "時間次序", "文件／授權 ≤ export ≤ first import"),
        ("11", "CIZ 精確輸入", "十份輸入、欄位、列數及 SHA-256 對數"),
        ("12", "Base ledger 20/20", "原 point-in-time auditor 全數通過"),
        ("13", "Provider-mode 語義", "新 manifest 沒有沿用 synthetic 冒充"),
        ("14", "公平 execution overlay", "QQQ／SPY 同步 raw 行情及來源 ID"),
        ("15", "Execution extension 16/16", "派息、歷史、移除、D+1 及成本通過"),
        ("16", "隔離及決策邊界", "owner-only；不運行策略、Paper 或實金"),
    ]
    return {
        "status": f"{source_mode}_local_quarantine_intake_passed",
        "gate_summary": {"passed": 16, "total": 16, "all_passed": True},
        "gates": [
            {"id": gate_id, "label": label, "passed": True, "detail": detail}
            for gate_id, label, detail in gate_rows
        ],
        "protocol_integrity": protocol,
        "point_in_time_gate_summary": ledger_audit["gate_summary"],
        "extension_gate_summary": {
            "passed": 16,
            "total": 16,
            "all_passed": True,
        },
        "counts": counts,
        "private_permissions": True,
        "provider_rows_published": False,
        "strategy_run_count": 0,
        "paper_authorized": False,
        "real_money_action_usd": 0,
    }


def _sanitized_receipt(
    *,
    source_mode: str,
    response: dict[str, Any],
    envelope: dict[str, Any],
    ciz_manifest: dict[str, Any],
    overlay_manifest: dict[str, Any],
    package: Path,
    audit: dict[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "intake_version": INTAKE_VERSION,
        "status": audit["status"],
        "source_mode": source_mode,
        "provider": response["provider"],
        "provider_product": response["provider_product"],
        "generated_at": overlay_manifest["first_imported_at"],
        "response_sha256": envelope["response_sha256"],
        "manifest_receipts": {
            "ciz_manifest.json": _sha256_file(package.parent / "ciz-manifest-source"),
            "execution_overlay_manifest.json": _sha256_file(
                package.parent / "overlay-manifest-source"
            ),
            "ledger/manifest.json": _sha256_file(package / "ledger/manifest.json"),
            "execution/execution_manifest.json": _sha256_file(
                package / "execution/execution_manifest.json"
            ),
        },
        "source_as_of_date": ciz_manifest["as_of_date"],
        "study_start": overlay_manifest["study_start"],
        "study_end": overlay_manifest["study_end"],
        "gate_summary": audit["gate_summary"],
        "point_in_time_gate_summary": audit["point_in_time_gate_summary"],
        "extension_gate_summary": audit["extension_gate_summary"],
        "counts": audit["counts"],
        "private_permissions": True,
        "contains_absolute_paths": False,
        "credentials_included": False,
        "provider_rows_published": False,
        "formal_stock_backtest_input_ready": source_mode == "provider",
        "formal_stock_backtest_completed": False,
        "strategy_rule_changed": False,
        "strategy_run_count": 0,
        "paper": {
            "authorized": False,
            "state": "all_cash",
            "backfilled_trades": 0,
            "positions": [],
        },
        "real_money_action_usd": 0,
    }


def run_local_quarantine_intake(
    response_path: str | Path,
    ciz_bundle: str | Path,
    execution_overlay: str | Path,
    output_bundle: str | Path,
    *,
    root: str | Path,
    source_mode: str = "provider",
    requirements: PointInTimeRequirements | None = None,
) -> dict[str, Any]:
    """Validate, transform and retain one explicit external package atomically."""

    root_path = Path(root).resolve()
    _protocol_integrity(root_path)
    response_file, ciz, overlay, destination = _preflight_paths(
        response_path,
        ciz_bundle,
        execution_overlay,
        output_bundle,
        root=root_path,
    )
    envelope = _read_json(response_file, "response_schema_mismatch")
    response, _ = _validate_document(
        envelope,
        root=root_path,
        source_mode=source_mode,
    )
    ciz_manifest_path = ciz / "ciz_manifest.json"
    overlay_manifest_path = overlay / "execution_overlay_manifest.json"
    ciz_manifest = _read_json(ciz_manifest_path, "invalid_source_manifest")
    overlay_manifest = _read_json(
        overlay_manifest_path, "execution_source_manifest_invalid"
    )
    _validate_identity_and_time(response, ciz_manifest, overlay_manifest)

    with tempfile.TemporaryDirectory(
        prefix=f".{destination.name}-", dir=destination.parent
    ) as temporary:
        temporary_root = Path(temporary)
        staging = temporary_root / destination.name
        # These two private copies are only used to calculate a sanitized receipt and
        # are removed with the staging parent; no absolute source path is serialized.
        ciz_manifest_copy = temporary_root / "ciz-manifest-source"
        overlay_manifest_copy = temporary_root / "overlay-manifest-source"
        ciz_manifest_copy.write_bytes(ciz_manifest_path.read_bytes())
        overlay_manifest_copy.write_bytes(overlay_manifest_path.read_bytes())
        transform_crsp_ciz_execution_bundle(
            ciz,
            overlay,
            staging,
            root=root_path,
        )
        execution_manifest_path = staging / "execution/execution_manifest.json"
        execution_manifest = _read_json(
            execution_manifest_path, "execution_source_manifest_invalid"
        )
        execution_manifest["status"] = MODE_STATUS[source_mode]
        _write_json(execution_manifest_path, execution_manifest)
        _apply_private_permissions(staging)
        audit = audit_local_quarantine_package(
            staging,
            root=root_path,
            source_mode=source_mode,
            requirements=requirements,
            require_receipt=False,
        )
        receipt = _sanitized_receipt(
            source_mode=source_mode,
            response=response,
            envelope=envelope,
            ciz_manifest=ciz_manifest,
            overlay_manifest=overlay_manifest,
            package=staging,
            audit=audit,
        )
        _write_json(staging / "intake_receipt.json", receipt)
        _apply_private_permissions(staging)
        audit_local_quarantine_package(
            staging,
            root=root_path,
            source_mode=source_mode,
            requirements=requirements,
            require_receipt=True,
        )
        staging.rename(destination)
    return receipt
