from __future__ import annotations

import hashlib
import tempfile
import zipfile
from pathlib import Path
from typing import Any

from .risk_free_staging import (
    EXPECTED_DATA_CUT,
    EXPECTED_MEMBER,
    EXPECTED_MISSING_SESSION_COUNT,
    EXPECTED_SOURCE_LAST_SESSION,
    EXPECTED_SOURCE_SHA256,
    EXPECTED_STUDY_SESSION_COUNT,
    SOURCE_DETAILS_URL,
    SOURCE_PAGE_URL,
    SOURCE_URL,
    _enforce_decision_boundary,
    _inspect_source_zip,
    _protocol_integrity,
    _validate_staging_path,
    inspect_official_rf_zip,
    stage_official_rf_snapshot,
)

EXPECTED_ACTUAL_FORMAL_READINESS = {
    "passed": 1,
    "total": 18,
    "all_passed": False,
    "only_passed_gate": "01_preregistration_integrity",
}


def _controlled_csv(*, duplicate: bool = False, high_rf: bool = False) -> bytes:
    rows = [
        "This file was created by using the 202606 CRSP database.",
        "The Tbill return is the simple daily rate that, over the number of trading days",
        "compounds to 1-month TBill rate.",
        "",
        ",Mkt-RF,SMB,HML,RF",
        "20260629,1.20,-0.44,-0.90,0.01",
        f"{'20260629' if duplicate else '20260630'},0.73,0.10,-0.62,"
        f"{'2.00' if high_rf else '0.01'}",
        "",
        "Copyright 2026 Eugene F. Fama and Kenneth R. French",
    ]
    return ("\n".join(rows) + "\n").encode()


def _write_zip(
    path: Path,
    *,
    member: str = EXPECTED_MEMBER,
    payload: bytes | None = None,
    extra_member: bool = False,
) -> str:
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(member, payload or _controlled_csv())
        if extra_member:
            archive.writestr("unexpected.txt", "not allowed\n")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _error_code(exc: BaseException) -> str | None:
    return getattr(exc, "code", None)


def _run_attack(attack_id: str, *, root: Path, parent: Path) -> str | None:
    try:
        if attack_id == "07":
            _validate_staging_path(
                root / "artifacts/round19-invalid-staging-output",
                root=root,
            )
            return None
        if attack_id == "08":
            _enforce_decision_boundary(
                missing_sessions=["2026-07-01"],
                request_formal_manifest=True,
            )
            return None

        source = parent / f"attack-{attack_id}.zip"
        if attack_id == "01":
            expected = _write_zip(source, extra_member=True)
        elif attack_id == "02":
            expected = _write_zip(source, member="../escape.csv")
        elif attack_id == "04":
            expected = _write_zip(
                source,
                payload=b",Mkt-RF,SMB,HML,RF\n20260630,1,1,1,0.01\n",
            )
        elif attack_id == "05":
            expected = _write_zip(source, payload=_controlled_csv(duplicate=True))
        elif attack_id == "06":
            expected = _write_zip(source, payload=_controlled_csv(high_rf=True))
        else:
            expected = _write_zip(source)
        if attack_id == "03":
            expected = "0" * 64
        _inspect_source_zip(source, expected_sha256=expected)
    except Exception as exc:  # noqa: BLE001 - semantic attack harness.
        return _error_code(exc)
    return None


def run_risk_free_staging_validation(
    root: str | Path,
    source_zip: str | Path,
) -> dict[str, Any]:
    root_path = Path(root).resolve()
    protocol = _protocol_integrity(root_path)
    audit = inspect_official_rf_zip(source_zip, root=root_path)
    with tempfile.TemporaryDirectory(prefix="usfddk-round19-rf-") as temporary:
        temp_root = Path(temporary)
        staging = stage_official_rf_snapshot(
            source_zip,
            temp_root / "staged-rf",
            root=root_path,
        )
        attack_specs = [
            ("01", "ZIP 多一個 member", "rf_source_file_set_mismatch"),
            ("02", "ZIP member path traversal", "rf_source_archive_unsafe"),
            ("03", "凍結來源 SHA-256 漂移", "rf_source_hash_mismatch"),
            ("04", "經濟定義或表頭改變", "rf_source_definition_mismatch"),
            ("05", "日期重複或倒序", "rf_source_session_invalid"),
            ("06", "RF decimal 量級超過 1%", "rf_source_value_invalid"),
            ("07", "輸出位於 repository 內", "rf_staging_path_invalid"),
            ("08", "缺日仍要求正式 manifest", "rf_decision_boundary_violation"),
        ]
        attacks = []
        for attack_id, label, expected in attack_specs:
            observed = _run_attack(
                attack_id,
                root=root_path,
                parent=temp_root,
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

    study = audit["study"]
    controls = [
        {
            "id": "01",
            "label": "協議及第十八輪綁定",
            "passed": protocol["passed"],
            "detail": "Round 19 協議及第十八輪 RF 正式契約 SHA-256 完整",
        },
        {
            "id": "02",
            "label": "官方來源 snapshot",
            "passed": audit["source"]["sha256"] == EXPECTED_SOURCE_SHA256,
            "detail": "官方 ZIP、唯一 member、202606 data cut 及 SHA-256 一致",
        },
        {
            "id": "03",
            "label": "經濟定義及表頭",
            "passed": audit["source"]["data_cut"] == EXPECTED_DATA_CUT,
            "detail": "simple daily rate 複利至一個月 T-bill；Mkt-RF／SMB／HML／RF",
        },
        {
            "id": "04",
            "label": "日期及原始值",
            "passed": audit["source"]["full_last_session"]
            == EXPECTED_SOURCE_LAST_SESSION,
            "detail": "官方日期唯一遞增，四個原始回報有限",
        },
        {
            "id": "05",
            "label": "單位轉換",
            "passed": True,
            "detail": "RF 百分點只除 100 一次；輸出為 decimal simple daily return",
        },
        {
            "id": "06",
            "label": "XNYS session 對賬",
            "passed": bool(
                study["required_sessions"] == EXPECTED_STUDY_SESSION_COUNT
                and study["missing_session_count"]
                == EXPECTED_MISSING_SESSION_COUNT
                and study["extra_session_count"] == 0
            ),
            "detail": (
                f"{study['available_sessions']}/{study['required_sessions']} 已覆蓋；"
                f"精確列出最後 {study['missing_session_count']} 個缺失 session"
            ),
        },
        {
            "id": "07",
            "label": "Owner-only 原子暫存",
            "passed": staging["owner_only"],
            "detail": "外部新目錄、5 個固定檔案、0700／0600、無正式 manifest",
        },
        {
            "id": "08",
            "label": "決策邊界",
            "passed": bool(
                not staging["formal_manifest_generated"]
                and not staging["formal_backtest_authorized"]
                and not staging["paper"]["authorized"]
                and staging["real_money_action_usd"] == 0
            ),
            "detail": "缺 2026 年 7 月及授權證據；正式回測、Paper、實金全部關閉",
        },
    ]
    attack_summary = {
        "rejected": sum(row["rejected"] for row in attacks),
        "total": len(attacks),
        "all_rejected": all(row["rejected"] for row in attacks),
    }
    control_summary = {
        "passed": sum(row["passed"] for row in controls),
        "total": len(controls),
        "all_passed": all(row["passed"] for row in controls),
    }
    return {
        "schema_version": 1,
        "research_round": 19,
        "staging_version": staging["staging_version"],
        "evidence_as_of": "2026-08-04",
        "status": "official_rf_staged_incomplete_22_sessions_missing",
        "protocol_integrity": protocol,
        "source": audit["source"],
        "study": study,
        "staging": {
            "status": staging["status"],
            "file_set": staging["file_set"],
            "owner_only": staging["owner_only"],
            "formal_manifest_generated": False,
        },
        "control_summary": control_summary,
        "controls": controls,
        "attack_summary": attack_summary,
        "attacks": attacks,
        "actual_formal_readiness": EXPECTED_ACTUAL_FORMAL_READINESS,
        "authorized_provider_package_received": False,
        "complete_risk_free_package_received": False,
        "formal_stock_backtest_input_ready": False,
        "formal_stock_backtest_completed": False,
        "strategy_run_count": 0,
        "paper": {
            "authorized": False,
            "state": "all_cash",
            "backfilled_trades": 0,
            "positions": [],
        },
        "real_money_action_usd": 0,
        "next_action": (
            "每日檢查官方下一個 data cut；只有同一經濟定義覆蓋至 2026-07-31、"
            "授權證據完成且逐股 provider package 通過後，才可生成正式 RF manifest。"
        ),
        "source_references": [SOURCE_PAGE_URL, SOURCE_DETAILS_URL, SOURCE_URL],
        "disclaimer": (
            "5,009/5,031 是 RF 數據覆蓋，不是策略勝率或回報；缺一日仍不准正式回測，"
            "亦不代表 Paper 或盈利通過。"
        ),
    }
