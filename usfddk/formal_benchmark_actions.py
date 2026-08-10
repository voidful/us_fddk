"""Provider-only QQQ/SPY corporate-action bridge for the formal backtest.

The execution extension deliberately keeps benchmark prices separate from the
stock ledger.  This module is the narrow bridge that makes that separation
safe: it accepts only an owner-only, externally supplied action package whose
receipts bind it to the already audited formal run and execution manifest.
Nothing in this module derives distributions from ``total_return_factor``.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import stat
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

BENCHMARK_ACTION_BRIDGE_VERSION = "round23-formal-benchmark-action-bridge-v1"
BENCHMARK_ACTION_MANIFEST = "benchmark_action_manifest.json"
BENCHMARK_ACTION_FILES = (
    "benchmark_actions.csv",
    "benchmark_entitlements.csv",
    "benchmark_outcomes.csv",
)
BENCHMARK_ASSETS = ("QQQ", "SPY")
ACTION_COLUMNS = (
    "event_id",
    "security_id",
    "event_type",
    "announced_at",
    "ex_date",
    "effective_date",
    "cash_amount",
    "share_ratio",
    "successor_security_id",
    "source_record_id",
)
ENTITLEMENT_COLUMNS = (
    "event_id",
    "security_id",
    "announced_at",
    "ex_date",
    "pay_date",
    "cash_available_date",
    "cash_per_share",
    "source_record_id",
)
OUTCOME_COLUMNS = (
    "source_record_id",
    "security_id",
    "membership_effective_to",
    "outcome_type",
    "last_trade_date",
    "exit_effective_date",
    "delisting_return",
    "cash_consideration",
    "successor_security_id",
    "reason_code",
    "known_at",
)
MANIFEST_KEYS = {
    "schema_version",
    "status",
    "bridge_version",
    "provider",
    "provider_product",
    "license_attestation",
    "exported_at",
    "first_imported_at",
    "study_start",
    "study_end",
    "formal_run_id",
    "execution_manifest_sha256",
    "benchmark_assets",
    "files",
}
LICENSE_KEYS = {
    "authorized_for_local_research",
    "raw_redistribution_allowed",
    "attested_at",
    "reference",
}
SUPPORTED_ACTIONS = {
    "dividend",
    "split",
    "spinoff",
    "merger_cash",
    "merger_stock",
    "bankruptcy",
    "delisting",
}
EXIT_ACTIONS = {"merger_cash", "merger_stock", "bankruptcy", "delisting"}
OUTCOME_TYPES = {"acquired_cash", "acquired_stock", "bankrupt", "delisted"}
OWNER_DIRECTORY_MODE = 0o700
OWNER_FILE_MODE = 0o600
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


class BenchmarkActionBridgeError(ValueError):
    """Fail-closed bridge error with a stable semantic code."""

    def __init__(self, code: str, detail: str):
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}")


def _fail(code: str, detail: str) -> None:
    raise BenchmarkActionBridgeError(code, detail)


def _sha256_file(path: Path) -> str:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError as exc:
        _fail("benchmark_action_receipt_invalid", f"{path.name}: {type(exc).__name__}")


def _timestamp(value: object, field: str) -> datetime:
    raw = str(value).strip()
    if not raw.endswith("Z") and not (
        len(raw) >= 6 and raw[-6] in {"+", "-"} and raw[-3] == ":"
    ):
        _fail("benchmark_action_provenance_invalid", f"{field} 缺 UTC offset")
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        _fail("benchmark_action_provenance_invalid", f"{field} 無效")
    if parsed.tzinfo is None:
        _fail("benchmark_action_provenance_invalid", f"{field} 缺 timezone")
    return parsed.astimezone(UTC)


def _date(value: object, field: str, *, allow_blank: bool = False) -> pd.Timestamp | None:
    raw = str(value).strip()
    if allow_blank and not raw:
        return None
    parsed = pd.to_datetime(raw, format="%Y-%m-%d", errors="coerce")
    if pd.isna(parsed):
        _fail("benchmark_action_calendar_invalid", f"{field} 不是 YYYY-MM-DD")
    return pd.Timestamp(parsed).normalize()


def _number(value: object, field: str, *, allow_blank: bool = False) -> float | None:
    raw = str(value).strip()
    if allow_blank and not raw:
        return None
    try:
        parsed = float(raw)
    except (TypeError, ValueError):
        _fail("benchmark_action_terms_invalid", f"{field} 不是數值")
    if not math.isfinite(parsed):
        _fail("benchmark_action_terms_invalid", f"{field} 不是有限數值")
    return parsed


def _private_tree_ok(path: Path) -> bool:
    for item in (path, *path.rglob("*")):
        if item.is_symlink():
            return False
        try:
            mode = stat.S_IMODE(item.stat(follow_symlinks=False).st_mode)
        except OSError:
            return False
        if item.is_dir() and mode != OWNER_DIRECTORY_MODE:
            return False
        if item.is_file() and mode != OWNER_FILE_MODE:
            return False
        if not item.is_dir() and not item.is_file():
            return False
    return True


def _resolve_bundle(bundle: str | Path, root: Path) -> Path:
    raw = Path(bundle)
    if not raw.is_absolute():
        _fail("benchmark_action_path_boundary_invalid", "bridge 必須使用 repository 外絕對路徑")
    try:
        resolved = raw.resolve(strict=True)
    except OSError as exc:
        _fail("benchmark_action_path_boundary_invalid", f"bridge 路徑無法解析：{type(exc).__name__}")
    if resolved == root or root in resolved.parents:
        _fail("benchmark_action_path_boundary_invalid", "bridge 不可位於 repository 內")
    if not resolved.is_dir() or not _private_tree_ok(resolved):
        _fail("benchmark_action_private_input_invalid", "bridge 必須是 owner-only 且不可含 symlink")
    return resolved


def _read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        _fail("benchmark_action_manifest_invalid", f"{path.name}: {type(exc).__name__}")
    if not isinstance(payload, dict):
        _fail("benchmark_action_manifest_invalid", f"{path.name} 必須是 JSON object")
    return payload


def _read_csv(path: Path, columns: tuple[str, ...]) -> pd.DataFrame:
    try:
        frame = pd.read_csv(path, dtype=str, keep_default_na=False, na_filter=False)
    except (OSError, pd.errors.ParserError) as exc:
        _fail("benchmark_action_schema_invalid", f"{path.name}: {type(exc).__name__}")
    if set(frame.columns) != set(columns):
        _fail("benchmark_action_schema_invalid", f"{path.name} 欄位集合不符")
    return frame.loc[:, list(columns)]


def _validate_manifest(
    bundle: Path,
    *,
    execution_manifest_path: Path,
    formal_run_id: str,
    study_start: str,
    study_end: str,
) -> dict[str, Any]:
    actual = {item.name for item in bundle.iterdir()}
    expected = {BENCHMARK_ACTION_MANIFEST, *BENCHMARK_ACTION_FILES}
    if actual != expected:
        _fail("benchmark_action_file_set_mismatch", "bridge 檔案集合不符")
    manifest = _read_json(bundle / BENCHMARK_ACTION_MANIFEST)
    if set(manifest) != MANIFEST_KEYS:
        _fail("benchmark_action_manifest_invalid", "bridge manifest keys 不符")
    if (
        manifest["schema_version"] != 1
        or manifest["status"] != "provider_benchmark_action_bridge"
        or manifest["bridge_version"] != BENCHMARK_ACTION_BRIDGE_VERSION
    ):
        _fail("benchmark_action_manifest_invalid", "bridge schema／狀態／版本不符")
    for field in ("provider", "provider_product", "study_start", "study_end"):
        if not isinstance(manifest[field], str) or not manifest[field].strip():
            _fail("benchmark_action_manifest_invalid", f"{field} 不可空白")
    if manifest["study_start"] != study_start or manifest["study_end"] != study_end:
        _fail("benchmark_action_binding_mismatch", "bridge 研究期與 execution manifest 不符")
    if manifest["formal_run_id"] != formal_run_id or not SHA256_PATTERN.fullmatch(
        str(manifest["formal_run_id"])
    ):
        _fail("benchmark_action_binding_mismatch", "bridge formal run ID 不符")
    expected_execution_hash = _sha256_file(execution_manifest_path)
    if manifest["execution_manifest_sha256"] != expected_execution_hash:
        _fail("benchmark_action_binding_mismatch", "bridge execution manifest SHA-256 不符")
    if manifest["benchmark_assets"] != list(BENCHMARK_ASSETS):
        _fail("benchmark_action_manifest_invalid", "bridge 只可按固定 QQQ／SPY 順序聲明資產")
    license_attestation = manifest["license_attestation"]
    if not isinstance(license_attestation, dict) or set(license_attestation) != LICENSE_KEYS:
        _fail("benchmark_action_license_invalid", "bridge license attestation keys 不符")
    if (
        license_attestation["authorized_for_local_research"] is not True
        or not isinstance(license_attestation["raw_redistribution_allowed"], bool)
    ):
        _fail("benchmark_action_license_invalid", "provider 未授權本地研究")
    if not isinstance(license_attestation["reference"], str) or not license_attestation["reference"].strip():
        _fail("benchmark_action_license_invalid", "provider license reference 缺失")
    attested_at = _timestamp(license_attestation["attested_at"], "attested_at")
    first_imported_at = _timestamp(manifest["first_imported_at"], "first_imported_at")
    exported_at = _timestamp(manifest["exported_at"], "exported_at")
    if attested_at > first_imported_at or exported_at > first_imported_at:
        _fail("benchmark_action_provenance_invalid", "provider timestamp 順序不符")
    files = manifest["files"]
    if not isinstance(files, dict) or set(files) != set(BENCHMARK_ACTION_FILES):
        _fail("benchmark_action_receipt_invalid", "bridge file receipt 集合不符")
    for name in BENCHMARK_ACTION_FILES:
        receipt = files[name]
        if (
            not isinstance(receipt, dict)
            or set(receipt) != {"sha256", "rows"}
            or not SHA256_PATTERN.fullmatch(str(receipt["sha256"]))
            or not isinstance(receipt["rows"], int)
            or receipt["rows"] < 0
            or receipt["sha256"] != _sha256_file(bundle / name)
        ):
            _fail("benchmark_action_receipt_invalid", f"{name} receipt 不符")
    return manifest


def _validate_actions(
    actions: pd.DataFrame,
    sessions: pd.DatetimeIndex,
) -> None:
    if actions.empty:
        _fail("benchmark_action_schema_invalid", "bridge 不可沒有公司行動")
    if actions["event_id"].eq("").any() or not actions["event_id"].is_unique:
        _fail("benchmark_action_schema_invalid", "event_id 必須非空及唯一")
    if actions["source_record_id"].eq("").any() or not actions["source_record_id"].is_unique:
        _fail("benchmark_action_provenance_invalid", "action source_record_id 必須非空及唯一")
    session_set = set(sessions)
    for row in actions.to_dict(orient="records"):
        event_type = str(row["event_type"])
        security_id = str(row["security_id"])
        if security_id not in BENCHMARK_ASSETS:
            _fail("benchmark_action_schema_invalid", f"只接受 QQQ／SPY action：{security_id}")
        if event_type not in SUPPORTED_ACTIONS:
            _fail("benchmark_action_schema_invalid", f"不支援 action type：{event_type}")
        _timestamp(row["announced_at"], f"{row['event_id']} announced_at")
        ex_date = _date(row["ex_date"], f"{row['event_id']} ex_date", allow_blank=True)
        effective_date = _date(row["effective_date"], f"{row['event_id']} effective_date")
        if effective_date not in session_set or (ex_date is not None and ex_date not in session_set):
            _fail("benchmark_action_calendar_invalid", f"{row['event_id']} 日期不在 XNYS sessions")
        cash_amount = _number(row["cash_amount"], f"{row['event_id']} cash_amount")
        share_ratio = _number(row["share_ratio"], f"{row['event_id']} share_ratio")
        successor = str(row["successor_security_id"]).strip()
        if event_type == "dividend" and (ex_date is None or cash_amount is None or cash_amount <= 0):
            _fail("benchmark_action_terms_invalid", f"{row['event_id']} dividend terms 無效")
        if event_type in {"split", "spinoff", "merger_stock"} and (
            ex_date is None or share_ratio is None or share_ratio <= 0
        ):
            _fail("benchmark_action_terms_invalid", f"{row['event_id']} share terms 無效")
        if event_type in {"spinoff", "merger_stock"} and successor not in BENCHMARK_ASSETS:
            _fail("benchmark_action_terms_invalid", f"{row['event_id']} successor 不在 QQQ／SPY")
        if event_type in EXIT_ACTIONS and not str(row["effective_date"]).strip():
            _fail("benchmark_action_calendar_invalid", f"{row['event_id']} exit effective_date 缺失")


def _validate_entitlements(
    actions: pd.DataFrame,
    entitlements: pd.DataFrame,
    sessions: pd.DatetimeIndex,
) -> None:
    dividend_ids = set(actions.loc[actions["event_type"].eq("dividend"), "event_id"])
    if set(entitlements["event_id"]) != dividend_ids or entitlements["event_id"].duplicated().any():
        _fail("benchmark_action_entitlement_mismatch", "dividend action 與 entitlement 未一對一")
    if entitlements["source_record_id"].eq("").any() or not entitlements["source_record_id"].is_unique:
        _fail("benchmark_action_provenance_invalid", "entitlement source_record_id 必須非空及唯一")
    action_map = actions.set_index("event_id").to_dict(orient="index")
    session_set = set(sessions)
    for row in entitlements.to_dict(orient="records"):
        action = action_map[str(row["event_id"])]
        if row["security_id"] != action["security_id"] or row["announced_at"] != action["announced_at"]:
            _fail("benchmark_action_entitlement_mismatch", f"{row['event_id']} identity 不對數")
        ex_date = _date(row["ex_date"], f"{row['event_id']} entitlement ex_date")
        pay_date = _date(row["pay_date"], f"{row['event_id']} pay_date")
        available = _date(row["cash_available_date"], f"{row['event_id']} cash_available_date")
        if ex_date not in session_set or pay_date not in session_set or available not in session_set:
            _fail("benchmark_action_calendar_invalid", f"{row['event_id']} entitlement 日期不在 XNYS")
        if pay_date < ex_date or available != pay_date or row["ex_date"] != action["ex_date"]:
            _fail("benchmark_action_entitlement_mismatch", f"{row['event_id']} pay／ex-date policy 不符")
        cash = _number(row["cash_per_share"], f"{row['event_id']} cash_per_share")
        action_cash = _number(action["cash_amount"], f"{row['event_id']} cash_amount")
        if cash is None or cash <= 0 or action_cash is None or not math.isclose(cash, action_cash):
            _fail("benchmark_action_entitlement_mismatch", f"{row['event_id']} cash 金額不對數")
        if row["source_record_id"] != action["source_record_id"]:
            _fail("benchmark_action_entitlement_mismatch", f"{row['event_id']} source record 不對數")


def _validate_outcomes(
    actions: pd.DataFrame,
    outcomes: pd.DataFrame,
    sessions: pd.DatetimeIndex,
) -> None:
    exit_actions = actions.loc[actions["event_type"].isin(EXIT_ACTIONS)]
    action_by_key = {
        (str(row.security_id), str(row.effective_date)): row
        for row in exit_actions.itertuples(index=False)
    }
    if len(action_by_key) != len(exit_actions):
        _fail("benchmark_action_schema_invalid", "同一 QQQ／SPY exit 日期不可有多個 action")
    if outcomes["source_record_id"].eq("").any() or not outcomes["source_record_id"].is_unique:
        _fail("benchmark_action_provenance_invalid", "outcome source_record_id 必須非空及唯一")
    session_set = set(sessions)
    keys: set[tuple[str, str]] = set()
    for row in outcomes.to_dict(orient="records"):
        security_id = str(row["security_id"])
        if security_id not in BENCHMARK_ASSETS:
            _fail("benchmark_action_outcome_invalid", f"只接受 QQQ／SPY outcome：{security_id}")
        outcome_type = str(row["outcome_type"])
        if outcome_type not in OUTCOME_TYPES:
            _fail("benchmark_action_outcome_invalid", f"不支援 outcome：{outcome_type}")
        effective = _date(row["exit_effective_date"], "outcome exit_effective_date")
        last_trade = _date(row["last_trade_date"], "outcome last_trade_date")
        if effective not in session_set or last_trade not in session_set or last_trade > effective:
            _fail("benchmark_action_outcome_invalid", f"{security_id} outcome 日期無效")
        _timestamp(row["known_at"], f"{security_id} known_at")
        key = (security_id, str(effective.date()))
        if key in keys:
            _fail("benchmark_action_outcome_invalid", f"outcome 重複：{key}")
        keys.add(key)
        action = action_by_key.get(key)
        if action is None:
            _fail("benchmark_action_outcome_invalid", f"{key} 沒有對應 exit action")
        expected_outcome = {
            "merger_cash": "acquired_cash",
            "merger_stock": "acquired_stock",
            "bankruptcy": "bankrupt",
            "delisting": "delisted",
        }[str(action.event_type)]
        if outcome_type != expected_outcome:
            _fail("benchmark_action_outcome_invalid", f"{key} action／outcome type 不對數")
        delisting = _number(row["delisting_return"], "delisting_return", allow_blank=True)
        cash = _number(row["cash_consideration"], "cash_consideration", allow_blank=True)
        successor = str(row["successor_security_id"]).strip()
        routes = int(delisting is not None) + int(cash is not None) + int(bool(successor))
        if routes != 1:
            _fail("benchmark_action_outcome_invalid", f"{key} exit route 不唯一")
        if outcome_type == "acquired_cash" and cash is None:
            _fail("benchmark_action_outcome_invalid", f"{key} acquired_cash 缺現金代價")
        if outcome_type == "acquired_stock" and successor not in BENCHMARK_ASSETS:
            _fail("benchmark_action_outcome_invalid", f"{key} successor 不在 QQQ／SPY")
        if outcome_type == "acquired_stock" and successor != str(action.successor_security_id):
            _fail("benchmark_action_outcome_invalid", f"{key} successor 不對數")
        if outcome_type in {"bankrupt", "delisted"} and delisting is None:
            _fail("benchmark_action_outcome_invalid", f"{key} 缺 delisting return")
    expected_keys = {
        (str(row.security_id), str(row.effective_date))
        for row in exit_actions.itertuples(index=False)
    }
    if keys != expected_keys:
        _fail("benchmark_action_outcome_invalid", "exit action 與 outcome 未一對一綁定")


@dataclass(frozen=True)
class BenchmarkActionBridge:
    """Validated provider rows ready to append to the raw accounting tables."""

    manifest: dict[str, Any]
    actions: pd.DataFrame
    entitlements: pd.DataFrame
    outcomes: pd.DataFrame


def load_benchmark_action_bridge(
    bundle: str | Path,
    *,
    root: str | Path,
    execution_manifest_path: str | Path,
    formal_run_id: str,
    study_start: str,
    study_end: str,
    sessions: pd.DatetimeIndex,
) -> BenchmarkActionBridge:
    """Load and audit an external QQQ/SPY action bridge exactly once."""
    root_path = Path(root).resolve()
    package = _resolve_bundle(bundle, root_path)
    execution_manifest = Path(execution_manifest_path).resolve()
    if not execution_manifest.is_file():
        _fail("benchmark_action_binding_mismatch", "execution manifest 不存在")
    manifest = _validate_manifest(
        package,
        execution_manifest_path=execution_manifest,
        formal_run_id=formal_run_id,
        study_start=study_start,
        study_end=study_end,
    )
    actions = _read_csv(package / "benchmark_actions.csv", ACTION_COLUMNS)
    entitlements = _read_csv(package / "benchmark_entitlements.csv", ENTITLEMENT_COLUMNS)
    outcomes = _read_csv(package / "benchmark_outcomes.csv", OUTCOME_COLUMNS)
    for name, frame in (
        ("benchmark_actions.csv", actions),
        ("benchmark_entitlements.csv", entitlements),
        ("benchmark_outcomes.csv", outcomes),
    ):
        if manifest["files"][name]["rows"] != len(frame):
            _fail("benchmark_action_receipt_invalid", f"{name} rows receipt 不符")
    _validate_actions(actions, sessions)
    _validate_entitlements(actions, entitlements, sessions)
    _validate_outcomes(actions, outcomes, sessions)
    if not all(
        ((actions["security_id"] == asset) & actions["event_type"].eq("dividend")).any()
        for asset in BENCHMARK_ASSETS
    ):
        _fail("benchmark_action_schema_invalid", "QQQ／SPY 均必須有可對數派息事件")
    return BenchmarkActionBridge(
        manifest=manifest,
        actions=actions,
        entitlements=entitlements,
        outcomes=outcomes,
    )
