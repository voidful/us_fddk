from __future__ import annotations

import hashlib
import json
import shutil
import tempfile
from pathlib import Path
from typing import Any

import pandas as pd

from .formal_backtest_readiness import (
    FORMAL_BASELINES,
    FORMAL_COSTS_BPS,
    FORMAL_GLOBAL_SEARCH_TRIALS,
    FORMAL_READINESS_VERSION,
    FORMAL_RF_ECONOMIC_DEFINITION,
    FORMAL_RF_SERIES,
    FORMAL_RF_UNIT,
    _policy_payload,
    _protocol_integrity,
    _validate_decision_boundary,
    _validate_policy,
    audit_formal_backtest_readiness,
)
from .local_quarantine_intake import run_local_quarantine_intake
from .local_quarantine_intake_validation import (
    CONTROL_REQUIREMENTS,
    _write_control_set,
)

EXPECTED_TRUE_READINESS = {"passed": 1, "total": 20, "all_passed": False}
EXPECTED_TRUE_LOCAL_INTAKE = {
    "passed": 1,
    "total": 16,
    "all_passed": False,
    "only_passed_gate": "01_preregistration_integrity",
}


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


def _owner_only(path: Path) -> None:
    for item in path.rglob("*"):
        item.chmod(0o700 if item.is_dir() else 0o600)
    path.chmod(0o700)


def _write_risk_free_control(package: Path, destination: Path) -> Path:
    destination.mkdir(parents=True)
    execution_manifest = json.loads(
        (package / "execution/execution_manifest.json").read_text(encoding="utf-8")
    )
    calendar = pd.read_csv(
        package / "ledger/trading_calendar.csv",
        dtype=str,
        keep_default_na=False,
        na_filter=False,
    )
    sessions = pd.to_datetime(calendar["session"], format="%Y-%m-%d", errors="raise")
    start = pd.Timestamp(execution_manifest["study_start"])
    end = pd.Timestamp(execution_manifest["study_end"])
    selected = sessions[(sessions >= start) & (sessions <= end)]
    frame = pd.DataFrame(
        {
            "session": selected.dt.strftime("%Y-%m-%d"),
            "risk_free_return": [0.0001] * len(selected),
            "unit": [FORMAL_RF_UNIT] * len(selected),
            "source_series": [FORMAL_RF_SERIES] * len(selected),
            "source_record_id": [
                f"synthetic-rf-{session.strftime('%Y%m%d')}" for session in selected
            ],
        }
    )
    csv_path = destination / "risk_free_daily.csv"
    frame.to_csv(csv_path, index=False, lineterminator="\n")
    manifest = {
        "schema_version": 1,
        "status": "synthetic_risk_free_control",
        "source_name": "authorized-synthetic-control-only",
        "source_url": (
            "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/"
            "data_library/f-f_factors.html"
        ),
        "source_vintage": "synthetic-round18-shape-control-no-provider-rows",
        "downloaded_at": "2026-08-04T00:30:00Z",
        "first_imported_at": "2026-08-04T00:31:00Z",
        "study_start": execution_manifest["study_start"],
        "study_end": execution_manifest["study_end"],
        "calendar": "XNYS",
        "economic_definition": FORMAL_RF_ECONOMIC_DEFINITION,
        "unit": FORMAL_RF_UNIT,
        "license_attestation": {
            "authorized_for_local_research": True,
            "raw_redistribution_allowed": False,
            "attested_at": "2026-08-04T00:29:00Z",
            "reference": "synthetic-control-no-provider-rows",
        },
        "files": {
            "risk_free_daily.csv": {
                "sha256": _sha256_file(csv_path),
                "rows": len(frame),
            }
        },
    }
    _write_json(destination / "risk_free_manifest.json", manifest)
    _owner_only(destination)
    return destination


def _rehash_risk_free(bundle: Path) -> None:
    manifest_path = bundle / "risk_free_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    csv_path = bundle / "risk_free_daily.csv"
    frame = pd.read_csv(
        csv_path,
        dtype=str,
        keep_default_na=False,
        na_filter=False,
    )
    manifest["files"]["risk_free_daily.csv"] = {
        "sha256": _sha256_file(csv_path),
        "rows": len(frame),
    }
    _write_json(manifest_path, manifest)
    _owner_only(bundle)


def _error_code(exc: BaseException) -> str | None:
    return getattr(exc, "code", None)


def _run_attack(
    attack_id: str,
    *,
    root: Path,
    base_package: Path,
    base_risk_free: Path,
    parent: Path,
) -> str | None:
    if attack_id in {"14", "15", "16", "18"}:
        try:
            if attack_id == "14":
                policy = _policy_payload()
                policy["statistics"] = {
                    **policy["statistics"],
                    "global_search_trials": FORMAL_GLOBAL_SEARCH_TRIALS - 1,
                }
                _validate_policy(policy)
            elif attack_id == "15":
                policy = _policy_payload()
                policy["baselines"] = [*FORMAL_BASELINES[:-1], "ambiguous_drift"]
                _validate_policy(policy)
            elif attack_id == "16":
                policy = _policy_payload()
                policy["execution"] = {
                    **policy["execution"],
                    "costs_bps": [*FORMAL_COSTS_BPS[:-1], 40],
                }
                _validate_policy(policy)
            else:
                _validate_decision_boundary(
                    source_mode="synthetic_control",
                    formal_authorized=True,
                    paper_authorized=False,
                    real_money_action_usd=0,
                )
        except Exception as exc:  # noqa: BLE001 - stable semantic code harness.
            return _error_code(exc)
        return None

    parent.mkdir(parents=True)
    package = parent / "package"
    risk_free = parent / "risk-free"
    output = parent / "formal-output"
    shutil.copytree(base_package, package)
    shutil.copytree(base_risk_free, risk_free)
    _owner_only(package)
    _owner_only(risk_free)
    source_mode = "synthetic_control"
    expected_run_id: str | None = None
    package_arg: str | Path = package
    risk_free_arg: str | Path = risk_free

    if attack_id == "01":
        risk_free_arg = Path(risk_free.name)
    elif attack_id == "02":
        (risk_free / "risk_free_daily.csv").chmod(0o644)
    elif attack_id == "03":
        source_mode = "provider"
    elif attack_id == "04":
        receipt_path = package / "intake_receipt.json"
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        receipt["strategy_run_count"] = 1
        _write_json(receipt_path, receipt)
        _owner_only(package)
    elif attack_id == "05":
        manifest_path = package / "execution/execution_manifest.json"
        manifest_path.write_text(
            manifest_path.read_text(encoding="utf-8") + " ", encoding="utf-8"
        )
        _owner_only(package)
    elif attack_id == "06":
        extra = risk_free / "extra.csv"
        extra.write_text("not,allowed\n", encoding="utf-8")
        extra.chmod(0o600)
    elif attack_id == "07":
        csv_path = risk_free / "risk_free_daily.csv"
        csv_path.write_text(csv_path.read_text(encoding="utf-8") + "\n", encoding="utf-8")
        _owner_only(risk_free)
    elif attack_id in {"08", "09", "10", "11", "12"}:
        csv_path = risk_free / "risk_free_daily.csv"
        frame = pd.read_csv(
            csv_path,
            dtype=str,
            keep_default_na=False,
            na_filter=False,
        )
        if attack_id == "08":
            frame = frame.iloc[1:].copy()
        elif attack_id == "09":
            extra = frame.iloc[-1].copy()
            extra["session"] = "2026-08-01"
            extra["source_record_id"] = "synthetic-rf-extra-non-session"
            frame = pd.concat([frame, extra.to_frame().T], ignore_index=True)
        elif attack_id == "10":
            frame.loc[:, "unit"] = "percent_daily_return"
        elif attack_id == "11":
            frame.loc[0, "risk_free_return"] = "0.02"
        else:
            frame.loc[1, "source_record_id"] = frame.loc[0, "source_record_id"]
        frame.to_csv(csv_path, index=False, lineterminator="\n")
        _rehash_risk_free(risk_free)
    elif attack_id == "13":
        expected_run_id = "0" * 64
    elif attack_id == "17":
        output.mkdir()

    try:
        audit_formal_backtest_readiness(
            package_arg,
            risk_free_arg,
            output,
            root=root,
            source_mode=source_mode,
            requirements=CONTROL_REQUIREMENTS,
            expected_run_id=expected_run_id,
        )
    except Exception as exc:  # noqa: BLE001 - stable semantic code harness.
        return _error_code(exc)
    return None


def run_formal_backtest_readiness_validation(root: str | Path) -> dict[str, Any]:
    root_path = Path(root).resolve()
    protocol = _protocol_integrity(root_path)
    with tempfile.TemporaryDirectory(prefix="usfddk-round18-formal-") as temporary:
        temp_root = Path(temporary)
        control_paths = _write_control_set(temp_root / "source")
        run_local_quarantine_intake(
            control_paths["response"],
            control_paths["ciz"],
            control_paths["overlay"],
            control_paths["output"],
            root=root_path,
            source_mode="synthetic_control",
            requirements=CONTROL_REQUIREMENTS,
        )
        risk_free = _write_risk_free_control(
            control_paths["output"], temp_root / "risk-free-control"
        )
        control = audit_formal_backtest_readiness(
            control_paths["output"],
            risk_free,
            temp_root / "formal-output-control",
            root=root_path,
            source_mode="synthetic_control",
            requirements=CONTROL_REQUIREMENTS,
        )
        attack_specs = [
            ("01", "相對路徑", "formal_path_boundary_invalid"),
            ("02", "非 owner-only 輸入", "formal_private_input_invalid"),
            ("03", "synthetic 冒充 provider／缺少 release firewall", "formal_release_firewall_required"),
            ("04", "Round 17 receipt 已跑一次", "formal_prior_run_detected"),
            ("05", "上游 manifest 漂移", "formal_input_binding_mismatch"),
            ("06", "RF 多一個檔案", "risk_free_file_set_mismatch"),
            ("07", "RF CSV 收據不符", "risk_free_receipt_invalid"),
            ("08", "RF 缺一個 session", "risk_free_session_mismatch"),
            ("09", "RF 多一個非交易日", "risk_free_session_mismatch"),
            ("10", "RF 單位改為 percent", "risk_free_unit_invalid"),
            ("11", "RF 日回報量級 2%", "risk_free_value_invalid"),
            ("12", "RF source record 重複", "risk_free_provenance_invalid"),
            ("13", "run ID 未綁定輸入", "formal_run_id_mismatch"),
            ("14", "DSR trials 改為 6,207", "formal_statistics_policy_mismatch"),
            ("15", "漂移 baseline 改名／改義", "formal_baseline_policy_mismatch"),
            ("16", "成本由 50 改 40 bps", "formal_execution_policy_mismatch"),
            ("17", "輸出目錄已存在", "formal_run_already_exists"),
            ("18", "合成控制升級正式授權", "formal_decision_boundary_violation"),
        ]
        attacks = []
        for attack_id, label, expected in attack_specs:
            observed = _run_attack(
                attack_id,
                root=root_path,
                base_package=control_paths["output"],
                base_risk_free=risk_free,
                parent=temp_root / f"attack-{attack_id}",
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

    readiness = json.loads(
        (root_path / "artifacts/short_term_point_in_time_readiness.json").read_text(
            encoding="utf-8"
        )
    )
    local_intake = json.loads(
        (
            root_path
            / "artifacts/short_term_local_quarantine_intake_validation.json"
        ).read_text(encoding="utf-8")
    )
    if readiness["gate_summary"] != EXPECTED_TRUE_READINESS:
        raise ValueError("真實 point-in-time readiness 已漂移；不得沿用 Round 18 結論")
    if local_intake["actual_local_intake"] != EXPECTED_TRUE_LOCAL_INTAKE:
        raise ValueError("真實 local intake 狀態已漂移；不得沿用 Round 18 結論")
    rejected = sum(int(row["rejected"]) for row in attacks)
    controls_ok = control["gate_summary"] == {
        "passed": 18,
        "total": 18,
        "all_passed": True,
    }
    attacks_ok = rejected == len(attacks) == 18
    return {
        "schema_version": 1,
        "research_round": 18,
        "readiness_version": FORMAL_READINESS_VERSION,
        "status": (
            "formal_preregistration_and_synthetic_readiness_controls_passed_inputs_missing"
            if controls_ok and attacks_ok
            else "formal_readiness_control_incomplete_or_failed"
        ),
        "evidence_as_of": "2026-08-04",
        "protocol_integrity": protocol,
        "gap_closed": {
            "risk_free_proxy": (
                "新增同步 US 1M T-bill 日回報；禁止用 0 或 SHY 代替超額統計。"
            ),
            "drift_baseline": (
                "固定為首個正式訊號 Top-10 只買一次後漂移，不再混用今日完整股池。"
            ),
            "global_search_trials": FORMAL_GLOBAL_SEARCH_TRIALS,
            "pbo_paths": 4,
            "formal_strategy_results_generated": False,
        },
        "synthetic_control": {
            "gate_summary": control["gate_summary"],
            "gates": control["gates"],
            "risk_free_sessions": control["risk_free"]["sessions"],
            "policy": control["policy"],
            "run_id_bound": len(control["run_id"]) == 64,
            "formal_stock_backtest_authorized": control[
                "formal_stock_backtest_authorized"
            ],
            "contains_provider_rows": False,
        },
        "attacks": attacks,
        "attack_summary": {
            "rejected": rejected,
            "total": len(attacks),
            "all_rejected": attacks_ok,
        },
        "actual_formal_readiness": {
            "passed": 1,
            "total": 18,
            "all_passed": False,
            "only_passed_gate": "01_preregistration_integrity",
        },
        "actual_point_in_time_readiness": readiness["gate_summary"],
        "actual_local_intake": local_intake["actual_local_intake"],
        "authorized_provider_package_received": False,
        "risk_free_provider_input_received": False,
        "provider_readiness_run_count": 0,
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
            "取得合法 provider package 與同日 US 1M T-bill RF 包後，先通過 18/18，"
            "再以 immutable run ID 只跑一次凍結正式回測。"
        ),
        "disclaimer": (
            "合成 18/18 只證明事前規則、RF、baseline、統計及決策邊界會關門；"
            "正式策略結果仍為 0，不代表盈利或 Paper 通過。"
        ),
    }
