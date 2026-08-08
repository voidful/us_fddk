from __future__ import annotations

import hashlib
import json
import math
import stat
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from .formal_release_integration import (
    FormalReleaseIntegrationError,
    audit_release_firewall,
)
from .local_quarantine_intake import (
    LocalQuarantineIntakeError,
    audit_local_quarantine_package,
)
from .point_in_time_ledger import PointInTimeRequirements

FORMAL_READINESS_VERSION = "round18-formal-backtest-readiness-v1"
FORMAL_PREREGISTRATION_PROTOCOL_SHA256 = (
    "4534130e245c97b6718e21a658708bd763c7046317a2b355c09b2589a8a3e083"
)
FORMAL_PREREGISTRATION_RECEIPT_PATH = (
    "artifacts/short_term_formal_backtest_preregistration_receipt.json"
)
FORMAL_GLOBAL_SEARCH_TRIALS = 6_208
FORMAL_PBO_SLICES = 10
FORMAL_PBO_PATHS = (
    "frozen_composite_monthly_top10",
    "tw_translation_weekly_top7",
    "tw_translation_weekly_top7_spy_regime",
    "tw_translation_weekly_top7_spy_regime_correlation",
)
FORMAL_BASELINES = (
    "QQQ_buy_hold",
    "SPY_buy_hold",
    "pit_eligible_equal_weight_monthly",
    "first_top10_equal_then_drift",
)
FORMAL_COSTS_BPS = (10, 25, 50)
FORMAL_STARTING_CAPITAL_USD = 1_000
FORMAL_EXECUTION_CLOCK = "signal_close_t_trade_raw_open_t_plus_1"
FORMAL_CASH_RETURN_POLICY = "zero_percent_uninvested_cash"
FORMAL_RF_FILES = {"risk_free_manifest.json", "risk_free_daily.csv"}
FORMAL_RF_COLUMNS = (
    "session",
    "risk_free_return",
    "unit",
    "source_series",
    "source_record_id",
)
FORMAL_RF_UNIT = "decimal_simple_daily_return"
FORMAL_RF_SERIES = "US_1M_TBILL_DAILY_RETURN"
FORMAL_RF_ECONOMIC_DEFINITION = (
    "simple_daily_return_compounding_to_the_us_one_month_treasury_bill_return"
)
FORMAL_RF_MANIFEST_KEYS = {
    "schema_version",
    "status",
    "source_name",
    "source_url",
    "source_vintage",
    "downloaded_at",
    "first_imported_at",
    "study_start",
    "study_end",
    "calendar",
    "economic_definition",
    "unit",
    "license_attestation",
    "files",
}
FORMAL_RF_LICENSE_KEYS = {
    "authorized_for_local_research",
    "raw_redistribution_allowed",
    "attested_at",
    "reference",
}
FORMAL_RF_STATUS = {
    "provider": "provider_risk_free_input",
    "synthetic_control": "synthetic_risk_free_control",
}
OWNER_DIRECTORY_MODE = 0o700
OWNER_FILE_MODE = 0o600


class FormalBacktestReadinessError(ValueError):
    """Fail-closed Round 18 readiness error with a stable semantic code."""

    def __init__(self, code: str, detail: str):
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}")


def _fail(code: str, detail: str) -> None:
    raise FormalBacktestReadinessError(code, detail)


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _read_json(path: Path, code: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        _fail(code, f"{path.name}: {type(exc).__name__}")
    if not isinstance(payload, dict):
        _fail(code, f"{path.name} 必須是 JSON object")
    return payload


def _timestamp(value: object, field: str, code: str) -> datetime:
    raw = str(value)
    if not raw.endswith("Z") and not (
        len(raw) >= 6 and raw[-6] in {"+", "-"} and raw[-3] == ":"
    ):
        _fail(code, f"{field} 缺 UTC offset")
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        _fail(code, f"{field} 無效")
    if parsed.tzinfo is None:
        _fail(code, f"{field} 缺 timezone")
    return parsed


def _protocol_integrity(root: Path) -> dict[str, Any]:
    receipt_path = root / FORMAL_PREREGISTRATION_RECEIPT_PATH
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
        frozen_at = _timestamp(
            receipt["frozen_at"],
            "Round 18 frozen_at",
            "formal_protocol_integrity_failed",
        )
        passed = bool(
            receipt["status"]
            == "frozen_before_formal_backtest_bridge_implementation_and_before_provider_result"
            and receipt["preregistered_protocol"]["sha256"]
            == FORMAL_PREREGISTRATION_PROTOCOL_SHA256
            and receipt["frozen_control_gate_count"] == 18
            and receipt["frozen_attack_count"] == 18
            and receipt["frozen_global_search_trials"]
            == FORMAL_GLOBAL_SEARCH_TRIALS
            and receipt["frozen_pbo_path_count"] == len(FORMAL_PBO_PATHS)
            and receipt["frozen_prerequisite_hash_count"] == 12
            and receipt["frozen_risk_free_output_file_count"] == 2
            and receipt["frozen_strategy_run_count"] == 0
            and receipt["formal_backtest_bridge_implemented_at_freeze"] is False
            and receipt["formal_backtest_completed_at_freeze"] is False
            and receipt["authorized_provider_package_present_at_freeze"] is False
            and receipt["paper"]
            == {
                "authorized": False,
                "state": "all_cash",
                "backfilled_trades": 0,
                "positions": [],
            }
            and receipt["real_money_action_usd"] == 0
            and len(tracked) == receipt["frozen_prerequisite_hash_count"] + 1
            and all(hash_checks.values())
        )
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError):
        passed = False
        hash_checks = {}
        frozen_at = None
    if not passed or frozen_at is None:
        _fail(
            "formal_protocol_integrity_failed",
            "Round 18 事前登記、收據或前置雜湊不完整",
        )
    return {
        "passed": True,
        "frozen_at": frozen_at.isoformat().replace("+00:00", "Z"),
        "hash_checks": hash_checks,
    }


def _external_path(
    value: str | Path,
    *,
    root: Path,
    must_exist: bool,
    expect_directory: bool,
) -> Path:
    path = Path(value)
    if not path.is_absolute():
        _fail("formal_path_boundary_invalid", "所有正式路徑必須是絕對路徑")
    try:
        resolved = path.resolve(strict=must_exist)
    except OSError as exc:
        _fail("formal_path_boundary_invalid", f"路徑無法解析：{type(exc).__name__}")
    if resolved == root or root in resolved.parents:
        _fail("formal_path_boundary_invalid", "正式輸入／輸出不可位於 repository 內")
    if must_exist:
        if expect_directory and not resolved.is_dir():
            _fail("formal_path_boundary_invalid", "正式輸入目錄不存在")
        if not expect_directory and not resolved.is_file():
            _fail("formal_path_boundary_invalid", "正式輸入檔案不存在")
    elif resolved.exists():
        _fail("formal_run_already_exists", "正式輸出目錄已存在")
    return resolved


def _private_tree_ok(path: Path) -> bool:
    items = [path, *path.rglob("*")]
    for item in items:
        if item.is_symlink():
            return False
        try:
            mode = stat.S_IMODE(item.stat(follow_symlinks=False).st_mode)
        except OSError:
            return False
        if item.is_dir():
            if mode != OWNER_DIRECTORY_MODE:
                return False
        elif item.is_file():
            if mode != OWNER_FILE_MODE:
                return False
        else:
            return False
    return True


def _validate_package_receipt(package: Path, source_mode: str) -> dict[str, Any]:
    receipt = _read_json(package / "intake_receipt.json", "formal_input_binding_mismatch")
    if receipt.get("strategy_run_count") != 0 or receipt.get(
        "formal_stock_backtest_completed"
    ) is not False:
        _fail("formal_prior_run_detected", "Round 17 receipt 已記錄正式策略執行")
    manifests = receipt.get("manifest_receipts")
    if not isinstance(manifests, dict):
        _fail("formal_input_binding_mismatch", "Round 17 manifest receipts 缺失")
    expected_paths = {
        "ledger/manifest.json",
        "execution/execution_manifest.json",
    }
    if any(
        manifests.get(relative) != _sha256_file(package / relative)
        for relative in expected_paths
    ):
        _fail("formal_input_binding_mismatch", "Round 17 衍生 manifest SHA-256 漂移")
    if source_mode == "provider":
        if (
            receipt.get("source_mode") != "provider"
            or receipt.get("status") != "provider_local_quarantine_intake_passed"
            or receipt.get("formal_stock_backtest_input_ready") is not True
        ):
            _fail("formal_provider_mode_required", "正式回測只接受 provider package")
    elif source_mode == "synthetic_control":
        if (
            receipt.get("source_mode") != "synthetic_control"
            or receipt.get("status")
            != "synthetic_control_local_quarantine_intake_passed"
            or receipt.get("formal_stock_backtest_input_ready") is not False
        ):
            _fail(
                "formal_decision_boundary_violation",
                "合成 package 決策邊界不一致",
            )
    else:
        _fail("formal_provider_mode_required", "不支援的 source mode")
    return receipt


def _read_risk_free_bundle(
    bundle: Path,
    *,
    source_mode: str,
    expected_sessions: pd.DatetimeIndex,
    study_start: str,
    study_end: str,
    frozen_at: datetime,
) -> tuple[dict[str, Any], pd.DataFrame]:
    actual_files = {item.name for item in bundle.iterdir()}
    if actual_files != FORMAL_RF_FILES:
        _fail("risk_free_file_set_mismatch", "risk-free package 檔案集合不符")
    manifest_path = bundle / "risk_free_manifest.json"
    csv_path = bundle / "risk_free_daily.csv"
    manifest = _read_json(manifest_path, "risk_free_receipt_invalid")
    if set(manifest) != FORMAL_RF_MANIFEST_KEYS:
        _fail("risk_free_receipt_invalid", "risk-free manifest keys 不符")
    try:
        frame = pd.read_csv(
            csv_path,
            dtype=str,
            keep_default_na=False,
            na_filter=False,
        )
    except (OSError, pd.errors.ParserError) as exc:
        _fail("risk_free_receipt_invalid", type(exc).__name__)
    if tuple(frame.columns) != FORMAL_RF_COLUMNS:
        _fail("risk_free_receipt_invalid", "risk-free CSV 欄位或次序不符")
    files = manifest.get("files")
    receipt = files.get("risk_free_daily.csv") if isinstance(files, dict) else None
    if (
        not isinstance(receipt, dict)
        or set(files) != {"risk_free_daily.csv"}
        or set(receipt) != {"sha256", "rows"}
        or receipt.get("sha256") != _sha256_file(csv_path)
        or receipt.get("rows") != len(frame)
    ):
        _fail("risk_free_receipt_invalid", "risk-free CSV 收據不符")

    license_data = manifest.get("license_attestation")
    if (
        not isinstance(license_data, dict)
        or set(license_data) != FORMAL_RF_LICENSE_KEYS
        or license_data.get("authorized_for_local_research") is not True
        or not isinstance(license_data.get("raw_redistribution_allowed"), bool)
        or not str(license_data.get("reference", "")).strip()
    ):
        _fail("risk_free_provenance_invalid", "risk-free 授權聲明不完整")
    attested_at = _timestamp(
        license_data.get("attested_at"),
        "RF attested_at",
        "risk_free_provenance_invalid",
    )
    downloaded_at = _timestamp(
        manifest.get("downloaded_at"),
        "RF downloaded_at",
        "risk_free_provenance_invalid",
    )
    first_imported_at = _timestamp(
        manifest.get("first_imported_at"),
        "RF first_imported_at",
        "risk_free_provenance_invalid",
    )
    if not (attested_at <= downloaded_at <= first_imported_at and first_imported_at > frozen_at):
        _fail("risk_free_provenance_invalid", "risk-free 授權／下載／首次匯入次序無效")
    if (
        manifest.get("schema_version") != 1
        or manifest.get("status") != FORMAL_RF_STATUS.get(source_mode)
        or manifest.get("study_start") != study_start
        or manifest.get("study_end") != study_end
        or manifest.get("calendar") != "XNYS"
        or manifest.get("economic_definition") != FORMAL_RF_ECONOMIC_DEFINITION
        or not str(manifest.get("source_name", "")).strip()
        or not str(manifest.get("source_url", "")).startswith("https://")
        or not str(manifest.get("source_vintage", "")).strip()
    ):
        _fail("risk_free_provenance_invalid", "risk-free 模式、來源或研究口徑不符")
    if manifest.get("unit") != FORMAL_RF_UNIT or not frame["unit"].eq(
        FORMAL_RF_UNIT
    ).all():
        _fail("risk_free_unit_invalid", "risk-free 必須是 decimal simple daily return")
    if not frame["source_series"].eq(FORMAL_RF_SERIES).all():
        _fail("risk_free_provenance_invalid", "risk-free economic series 漂移")
    if (
        frame["source_record_id"].eq("").any()
        or not frame["source_record_id"].is_unique
    ):
        _fail("risk_free_provenance_invalid", "risk-free source record 缺失或重複")

    parsed_sessions = pd.to_datetime(
        frame["session"], format="%Y-%m-%d", errors="coerce"
    )
    expected = pd.DatetimeIndex(expected_sessions).tz_localize(None).normalize()
    actual = pd.DatetimeIndex(parsed_sessions.dropna()).normalize()
    if (
        parsed_sessions.isna().any()
        or frame["session"].duplicated().any()
        or set(actual) != set(expected)
        or len(frame) != len(expected)
    ):
        _fail("risk_free_session_mismatch", "risk-free sessions 與 XNYS 研究日曆不一致")
    values = pd.to_numeric(frame["risk_free_return"], errors="coerce")
    if (
        values.isna().any()
        or not values.map(math.isfinite).all()
        or values.le(-1.0).any()
        or values.abs().gt(0.01).any()
    ):
        _fail("risk_free_value_invalid", "risk-free 日回報數值或量級無效")
    return manifest, frame.assign(
        __session=parsed_sessions,
        __risk_free_return=values.astype(float),
    ).sort_values("__session")


def _policy_payload() -> dict[str, Any]:
    return {
        "strategy": {
            "weights": {
                "momentum_12_1": 0.45,
                "momentum_6_1": 0.25,
                "trend_200": 0.20,
                "low_volatility_63": 0.10,
            },
            "top_n": 10,
            "sector_cap_count": 3,
            "minimum_raw_close_usd": 5.0,
            "minimum_median_dollar_volume_usd": 20_000_000.0,
            "minimum_history_sessions": 252,
            "company_share_class_tie_break": "highest_20d_median_dollar_volume_then_security_id",
            "rank_policy": "average_percentile_then_security_id",
            "qqq_shortfall_weight_per_missing_stock": 0.10,
        },
        "execution": {
            "clock": FORMAL_EXECUTION_CLOCK,
            "costs_bps": list(FORMAL_COSTS_BPS),
            "starting_capital_usd": FORMAL_STARTING_CAPITAL_USD,
            "fractional_shares": True,
            "cash_return_policy": FORMAL_CASH_RETURN_POLICY,
            "dividend_policy": "receivable_ex_date_cash_available_pay_date_once",
            "exit_policy": "one_economic_settlement_path_only",
        },
        "baselines": list(FORMAL_BASELINES),
        "statistics": {
            "global_search_trials": FORMAL_GLOBAL_SEARCH_TRIALS,
            "pbo_slices": FORMAL_PBO_SLICES,
            "pbo_paths": list(FORMAL_PBO_PATHS),
            "newey_west_lag": "floor_4_times_n_over_100_power_2_over_9",
            "risk_free_series": FORMAL_RF_SERIES,
        },
    }


def _validate_policy(payload: dict[str, Any]) -> None:
    expected = _policy_payload()
    if payload.get("statistics") != expected["statistics"]:
        _fail("formal_statistics_policy_mismatch", "NW／DSR／PBO 政策漂移")
    if payload.get("baselines") != expected["baselines"]:
        _fail("formal_baseline_policy_mismatch", "baseline 名稱、次序或語義漂移")
    if payload.get("execution") != expected["execution"] or payload.get(
        "strategy"
    ) != expected["strategy"]:
        _fail("formal_execution_policy_mismatch", "訊號、時鐘或成本政策漂移")


def _compute_run_id(
    *,
    package: Path,
    risk_free: Path,
    policy: dict[str, Any],
) -> tuple[str, dict[str, str]]:
    bindings = {
        "formal_protocol_sha256": FORMAL_PREREGISTRATION_PROTOCOL_SHA256,
        "intake_receipt_sha256": _sha256_file(package / "intake_receipt.json"),
        "ledger_manifest_sha256": _sha256_file(package / "ledger/manifest.json"),
        "execution_manifest_sha256": _sha256_file(
            package / "execution/execution_manifest.json"
        ),
        "risk_free_manifest_sha256": _sha256_file(
            risk_free / "risk_free_manifest.json"
        ),
        "policy_sha256": hashlib.sha256(
            json.dumps(
                policy,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=True,
            ).encode("utf-8")
        ).hexdigest(),
    }
    run_id = hashlib.sha256(
        json.dumps(
            bindings,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
    ).hexdigest()
    return run_id, bindings


def _require_run_id(actual: str, expected: str) -> None:
    if actual != expected:
        _fail("formal_run_id_mismatch", "run ID 沒有綁定完整 immutable inputs")


def _validate_decision_boundary(
    *,
    source_mode: str,
    formal_authorized: bool,
    paper_authorized: bool,
    real_money_action_usd: float,
    release_firewall_passed: bool | None = None,
) -> None:
    expected_formal = (
        source_mode == "provider"
        if release_firewall_passed is None
        else source_mode == "provider" and release_firewall_passed
    )
    if (
        formal_authorized is not expected_formal
        or paper_authorized is not False
        or real_money_action_usd != 0
    ):
        _fail(
            "formal_decision_boundary_violation",
            "合成／正式回測／Paper／實金狀態混淆",
        )


def audit_formal_backtest_readiness(
    package: str | Path,
    risk_free_bundle: str | Path,
    output_directory: str | Path,
    *,
    root: str | Path,
    source_mode: str = "provider",
    requirements: PointInTimeRequirements | None = None,
    expected_run_id: str | None = None,
    release_firewall: str | Path | None = None,
) -> dict[str, Any]:
    """Audit immutable formal inputs without running a strategy or writing output."""

    root_path = Path(root).resolve()
    protocol = _protocol_integrity(root_path)
    package_path = _external_path(
        package,
        root=root_path,
        must_exist=True,
        expect_directory=True,
    )
    risk_free_path = _external_path(
        risk_free_bundle,
        root=root_path,
        must_exist=True,
        expect_directory=True,
    )
    output_path = _external_path(
        output_directory,
        root=root_path,
        must_exist=False,
        expect_directory=True,
    )
    release_path: Path | None = None
    if source_mode == "provider":
        if release_firewall is None:
            _fail(
                "formal_release_firewall_required",
                "provider formal readiness 必須提供 release firewall receipt",
            )
        release_path = _external_path(
            release_firewall,
            root=root_path,
            must_exist=True,
            expect_directory=True,
        )
    path_set = {package_path, risk_free_path, output_path}
    if release_path is not None:
        path_set.add(release_path)
    if len(path_set) != (4 if source_mode == "provider" else 3):
        _fail("formal_path_boundary_invalid", "輸入、RF 與輸出路徑必須分開")
    if (
        not _private_tree_ok(package_path)
        or not _private_tree_ok(risk_free_path)
        or (release_path is not None and not _private_tree_ok(release_path))
    ):
        _fail("formal_private_input_invalid", "正式輸入不是 owner-only 或含連結／特殊檔")

    receipt = _validate_package_receipt(package_path, source_mode)
    release_audit: dict[str, Any] | None = None
    if release_path is not None:
        try:
            release_audit = audit_release_firewall(
                release_path,
                package_path,
                root=root_path,
            )
        except FormalReleaseIntegrationError as exc:
            _fail(exc.code, exc.detail)
    try:
        upstream_audit = audit_local_quarantine_package(
            package_path,
            root=root_path,
            source_mode=source_mode,
            requirements=requirements or PointInTimeRequirements(),
        )
    except LocalQuarantineIntakeError as exc:
        if exc.code == "intake_source_mode_mismatch":
            _fail("formal_provider_mode_required", exc.detail)
        if exc.code in {
            "intake_receipt_invalid",
            "base_ledger_binding_mismatch",
            "execution_source_manifest_invalid",
        }:
            _fail("formal_input_binding_mismatch", exc.detail)
        raise
    if upstream_audit["point_in_time_gate_summary"] != {
        "passed": 20,
        "total": 20,
        "all_passed": True,
    }:
        _fail("formal_input_binding_mismatch", "base ledger 未通過 20/20")
    if upstream_audit["extension_gate_summary"] != {
        "passed": 16,
        "total": 16,
        "all_passed": True,
    }:
        _fail("formal_input_binding_mismatch", "execution extension 未通過 16/16")

    execution_manifest = _read_json(
        package_path / "execution/execution_manifest.json",
        "formal_input_binding_mismatch",
    )
    calendar = pd.read_csv(
        package_path / "ledger/trading_calendar.csv",
        dtype=str,
        keep_default_na=False,
        na_filter=False,
    )
    sessions = pd.to_datetime(calendar["session"], format="%Y-%m-%d", errors="coerce")
    start = pd.Timestamp(execution_manifest["study_start"])
    end = pd.Timestamp(execution_manifest["study_end"])
    required_sessions = pd.DatetimeIndex(sessions[(sessions >= start) & (sessions <= end)])
    risk_manifest, risk_frame = _read_risk_free_bundle(
        risk_free_path,
        source_mode=source_mode,
        expected_sessions=required_sessions,
        study_start=execution_manifest["study_start"],
        study_end=execution_manifest["study_end"],
        frozen_at=datetime.fromisoformat(protocol["frozen_at"].replace("Z", "+00:00")),
    )

    policy = _policy_payload()
    _validate_policy(policy)
    run_id, bindings = _compute_run_id(
        package=package_path,
        risk_free=risk_free_path,
        policy=policy,
    )
    if expected_run_id is not None:
        _require_run_id(run_id, expected_run_id)
    formal_authorized = bool(
        source_mode == "provider"
        and release_audit is not None
        and release_audit["formal_backtest_authorized"] is True
    )
    _validate_decision_boundary(
        source_mode=source_mode,
        formal_authorized=formal_authorized,
        paper_authorized=False,
        real_money_action_usd=0,
        release_firewall_passed=release_audit is not None,
    )

    gate_details = [
        "Round 18 協議、收據及十二份前置雜湊完整",
        "輸入、RF、預留輸出均為 repository 外絕對路徑",
        "兩個輸入樹 owner-only 且無 symlink／特殊檔",
        f"source_mode={source_mode}；Round 17 策略執行 0 次",
        "base ledger point-in-time 20/20",
        "execution extension 16/16",
        "RF manifest、CSV、SHA-256、列數及授權完整",
        f"RF 與 {len(required_sessions)} 個 XNYS sessions 一對一",
        "RF 使用 decimal simple daily return 且量級有效",
        "run ID 綁定協議、三份上游收據、RF 及政策",
        "四因子、排名、同公司去重及三股行業 cap 固定",
        "t close／t+1 raw open；10／25／50 bps 固定",
        "派息、拆股、退市、現金及 successor 只計一次",
        "四個 baseline 名稱、次序及漂移語義固定",
        "固定兩半、滾動窗口、危機段及 US$1,000",
        "NW／PSR／6,208-trial DSR／四路十段 PBO 固定",
        "預留輸出不存在；正式執行須原子建立且只可一次",
        (
            "合成只通過形狀控制；正式／Paper／實金均未升級"
            if source_mode == "synthetic_control"
            else "只授權一次正式回測；Paper／實金仍未升級"
        ),
    ]
    return {
        "schema_version": 1,
        "research_round": 18,
        "readiness_version": FORMAL_READINESS_VERSION,
        "status": (
            "provider_formal_backtest_ready_for_one_run"
            if formal_authorized
            else "synthetic_formal_readiness_control_passed_not_authorized"
        ),
        "source_mode": source_mode,
        "release_firewall": (
            release_audit
            if release_audit is not None
            else {
                "required": False,
                "status": "not_required_synthetic_control",
                "formal_backtest_authorized": False,
            }
        ),
        "protocol_integrity": protocol,
        "gate_summary": {"passed": 18, "total": 18, "all_passed": True},
        "gates": [
            {
                "id": f"{index:02d}",
                "label": label,
                "passed": True,
                "detail": detail,
            }
            for index, (label, detail) in enumerate(
                zip(
                    (
                        "事前凍結完整性",
                        "外部絕對路徑",
                        "owner-only 輸入",
                        "provider／合成及零次執行",
                        "base ledger 20/20",
                        "execution extension 16/16",
                        "RF 收據及授權",
                        "RF 日曆同步",
                        "RF 單位及數值",
                        "immutable run ID",
                        "固定訊號規則",
                        "固定成交及成本",
                        "公司行動單次入賬",
                        "四個公平 baseline",
                        "固定時段及資金口徑",
                        "固定統計及多重測試",
                        "新輸出及一次性",
                        "決策邊界分離",
                    ),
                    gate_details,
                    strict=True,
                ),
                start=1,
            )
        ],
        "upstream": {
            "round17_status": upstream_audit["status"],
            "point_in_time_gate_summary": upstream_audit[
                "point_in_time_gate_summary"
            ],
            "extension_gate_summary": upstream_audit["extension_gate_summary"],
            "strategy_run_count": receipt["strategy_run_count"],
        },
        "risk_free": {
            "source_name": risk_manifest["source_name"],
            "source_vintage": risk_manifest["source_vintage"],
            "economic_definition": risk_manifest["economic_definition"],
            "unit": risk_manifest["unit"],
            "sessions": len(risk_frame),
            "provider_rows_published": False,
        },
        "policy": policy,
        "run_id": run_id,
        "input_bindings": bindings,
        "output_directory_created": False,
        "strategy_run_count": 0,
        "formal_stock_backtest_authorized": formal_authorized,
        "formal_stock_backtest_completed": False,
        "paper": {
            "authorized": False,
            "state": "all_cash",
            "backfilled_trades": 0,
            "positions": [],
        },
        "real_money_action_usd": 0,
    }
