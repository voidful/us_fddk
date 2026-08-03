from __future__ import annotations

import hashlib
import json
import math
import re
import tempfile
from pathlib import Path
from typing import Any

import pandas as pd

from .crsp_ciz_adapter import transform_crsp_ciz_bundle
from .point_in_time_ledger import (
    REQUIRED_COLUMNS,
    PointInTimeRequirements,
    audit_point_in_time_bundle,
)

EXECUTION_EXTENSION_VERSION = "round15-ciz-execution-extension-v1"
EXECUTION_EXTENSION_PROTOCOL_SHA256 = (
    "49582d2e7fae7e25897b59adb5322b17424865f5f6b34040d8f6392446fe9883"
)
ROUND13_ADAPTER_SHA256_AT_FREEZE = (
    "2ce8c8c6d760153d094c9511c9a1d2aa9a510328c729e289abdb523618d6cbab"
)
ROUND14_AUDITOR_SHA256_AT_FREEZE = (
    "d8dcc3f7727836f133f0f36365bdc6f8bb174fd1323b296c76d50b32e0371f40"
)
STRATEGY_PROTOCOL_SHA256 = (
    "589a799b18412e1fdad569c48e94313689c57b75eae84972a5c20baaa6ede139"
)
OVERLAY_FILES = ("benchmark_daily.csv",)
OVERLAY_MANIFEST_KEYS = {
    "schema_version",
    "status",
    "provider",
    "provider_product",
    "license_attestation",
    "exported_at",
    "first_imported_at",
    "study_start",
    "study_end",
    "price_basis",
    "signal_policy",
    "execution_clock",
    "dividend_cash_policy",
    "qqq_fallback_asset_id",
    "primary_cost_bps",
    "stress_cost_bps",
    "strategy_protocol_sha256",
    "files",
}
LICENSE_KEYS = {
    "authorized_for_local_research",
    "raw_redistribution_allowed",
    "attested_at",
    "reference",
}
BENCHMARK_COLUMNS = (
    "asset_id",
    "session",
    "open_raw",
    "high_raw",
    "low_raw",
    "close_raw",
    "volume",
    "total_return_factor",
    "source_status",
    "source_record_id",
)
CASH_ENTITLEMENT_COLUMNS = (
    "event_id",
    "security_id",
    "announced_at",
    "ex_date",
    "pay_date",
    "cash_available_date",
    "cash_per_share",
    "source_record_id",
)
SIGNAL_ELIGIBILITY_COLUMNS = (
    "signal_session",
    "security_id",
    "return_sessions",
    "positive_volume_sessions",
    "eligible",
    "source_record_id",
)
REMOVAL_WINDOW_COLUMNS = (
    "security_id",
    "membership_effective_to",
    "signal_session",
    "execution_session",
    "required_sessions",
    "observed_sessions",
    "execution_open_raw",
    "source_record_id",
)
EXECUTION_OUTPUT_FILES = (
    "cash_entitlements.csv",
    "signal_eligibility.csv",
    "removal_execution_windows.csv",
    "benchmark_daily.csv",
)
EXECUTION_MANIFEST_KEYS = {
    "schema_version",
    "status",
    "transform_version",
    "generated_at",
    "study_start",
    "study_end",
    "base_ledger_manifest_sha256",
    "source_overlay_manifest_sha256",
    "protocol_sha256",
    "strategy_protocol_sha256",
    "price_basis",
    "signal_policy",
    "execution_clock",
    "dividend_cash_policy",
    "qqq_fallback_asset_id",
    "primary_cost_bps",
    "stress_cost_bps",
    "files",
}
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
FROZEN_PRICE_BASIS = "raw_unadjusted_ohlc_plus_total_return_factor"
FROZEN_SIGNAL_POLICY = "last_official_session_each_complete_month"
FROZEN_EXECUTION_CLOCK = "signal_close_t_trade_open_t_plus_1"
FROZEN_DIVIDEND_POLICY = "receivable_ex_date_cash_available_pay_date"
FROZEN_QQQ_FALLBACK = "QQQ"
FROZEN_PRIMARY_COST_BPS = 10
FROZEN_STRESS_COST_BPS = [25, 50]


class ExecutionExtensionError(ValueError):
    """Fail-closed Round 15 bridge error with a stable semantic code."""

    def __init__(self, code: str, detail: str):
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}")


def _fail(code: str, detail: str) -> None:
    raise ExecutionExtensionError(code, detail)


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _date(value: object, field: str) -> pd.Timestamp:
    parsed = pd.to_datetime(str(value), format="%Y-%m-%d", errors="coerce")
    if pd.isna(parsed):
        _fail("execution_date_invalid", f"{field} 不是 YYYY-MM-DD")
    return pd.Timestamp(parsed).normalize()


def _timestamp(value: object, field: str) -> pd.Timestamp:
    raw = str(value)
    if not re.search(r"(?:Z|[+-]\d{2}:\d{2})$", raw):
        _fail("execution_timestamp_invalid", f"{field} 缺 UTC offset")
    parsed = pd.to_datetime(raw, errors="coerce", utc=True)
    if pd.isna(parsed):
        _fail("execution_timestamp_invalid", f"{field} 無效")
    return pd.Timestamp(parsed)


def _number(value: object, field: str) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        _fail("execution_number_invalid", f"{field} 不是數值")
    if not math.isfinite(parsed):
        _fail("execution_number_invalid", f"{field} 不是有限數值")
    return parsed


def _read_csv(path: Path, columns: tuple[str, ...], code: str) -> pd.DataFrame:
    try:
        frame = pd.read_csv(path, dtype=str, keep_default_na=False, na_filter=False)
    except (OSError, pd.errors.ParserError) as exc:
        _fail(code, f"{path.name}: {type(exc).__name__}")
    if set(frame.columns) != set(columns):
        _fail(code, f"{path.name} 欄位集合不符")
    return frame.loc[:, list(columns)]


def _protocol_integrity(root: Path, first_imported_at: pd.Timestamp) -> dict[str, Any]:
    receipt_path = root / "artifacts/short_term_ciz_execution_extension_protocol_receipt.json"
    try:
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        tracked = (
            receipt["protocol"],
            receipt["round14_protocol"],
            receipt["round14_protocol_receipt"],
            receipt["round14_auditor_at_freeze"],
            receipt["round13_adapter_at_freeze"],
            receipt["point_in_time_contract"],
            receipt["strategy_protocol"],
        )
        hash_checks = {
            item["path"]: _sha256_file(root / item["path"]) == item["sha256"]
            for item in tracked
        }
        frozen_at = _timestamp(receipt["frozen_at"], "Round 15 frozen_at")
        passed = bool(
            receipt["status"]
            == "frozen_before_execution_extension_bridge_implementation"
            and receipt["protocol"]["sha256"]
            == EXECUTION_EXTENSION_PROTOCOL_SHA256
            and receipt["round13_adapter_at_freeze"]["sha256"]
            == ROUND13_ADAPTER_SHA256_AT_FREEZE
            and receipt["round14_auditor_at_freeze"]["sha256"]
            == ROUND14_AUDITOR_SHA256_AT_FREEZE
            and receipt["frozen_control_gate_count"] == 16
            and receipt["frozen_attack_count"] == 16
            and receipt["frozen_extension_output_file_count"] == 5
            and receipt["execution_extension_bridge_implemented_at_freeze"] is False
            and receipt["authorized_provider_sample_present_at_freeze"] is False
            and first_imported_at > frozen_at
            and all(hash_checks.values())
        )
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError):
        passed = False
        hash_checks = {}
        frozen_at = pd.NaT
    if not passed:
        _fail("execution_protocol_integrity_failed", "Round 15 協議或事前雜湊不完整")
    return {
        "passed": True,
        "frozen_at": frozen_at.isoformat().replace("+00:00", "Z"),
        "hash_checks": hash_checks,
    }


def _read_overlay(source: Path, root: Path) -> tuple[dict[str, Any], pd.DataFrame, dict[str, Any]]:
    if not source.is_dir():
        _fail("execution_source_file_set_mismatch", "execution overlay 目錄不存在")
    expected = {"execution_overlay_manifest.json", *OVERLAY_FILES}
    actual = {item.name for item in source.iterdir() if item.is_file()}
    if actual != expected:
        _fail(
            "execution_source_file_set_mismatch",
            f"missing={sorted(expected - actual)}; extra={sorted(actual - expected)}",
        )
    try:
        manifest = json.loads(
            (source / "execution_overlay_manifest.json").read_text(encoding="utf-8")
        )
    except (OSError, json.JSONDecodeError) as exc:
        _fail("execution_source_manifest_invalid", type(exc).__name__)
    if not isinstance(manifest, dict) or set(manifest) != OVERLAY_MANIFEST_KEYS:
        _fail("execution_source_manifest_invalid", "overlay manifest keys 不符")
    if manifest["schema_version"] != 1 or manifest["status"] != "authorized_execution_overlay":
        _fail("execution_source_manifest_invalid", "overlay schema 或狀態不符")
    if not str(manifest["provider"]).strip() or not str(manifest["provider_product"]).strip():
        _fail("execution_source_manifest_invalid", "overlay 供應商及產品不可空白")
    license_data = manifest["license_attestation"]
    if not isinstance(license_data, dict) or set(license_data) != LICENSE_KEYS:
        _fail("execution_source_manifest_invalid", "overlay 授權欄位不完整")
    if (
        license_data["authorized_for_local_research"] is not True
        or not isinstance(license_data["raw_redistribution_allowed"], bool)
        or not str(license_data["reference"]).strip()
    ):
        _fail("execution_source_manifest_invalid", "overlay 未證明本地研究授權")
    attested_at = _timestamp(license_data["attested_at"], "license attested_at")
    exported_at = _timestamp(manifest["exported_at"], "overlay exported_at")
    first_imported_at = _timestamp(manifest["first_imported_at"], "overlay first_imported_at")
    if attested_at > first_imported_at or exported_at > first_imported_at:
        _fail("execution_source_manifest_invalid", "overlay 授權／匯出晚於首次匯入")
    study_start = _date(manifest["study_start"], "study_start")
    study_end = _date(manifest["study_end"], "study_end")
    if study_start > study_end:
        _fail("execution_source_manifest_invalid", "study_start 晚於 study_end")
    policy_ok = bool(
        manifest["price_basis"] == FROZEN_PRICE_BASIS
        and manifest["signal_policy"] == FROZEN_SIGNAL_POLICY
        and manifest["execution_clock"] == FROZEN_EXECUTION_CLOCK
        and manifest["dividend_cash_policy"] == FROZEN_DIVIDEND_POLICY
    )
    if not policy_ok:
        _fail("benchmark_price_policy_invalid", "overlay 價格或執行政策不符")
    if manifest["qqq_fallback_asset_id"] != FROZEN_QQQ_FALLBACK:
        _fail("qqq_fallback_binding_invalid", "QQQ 補位未綁定同一 QQQ 序列")
    if (
        manifest["primary_cost_bps"] != FROZEN_PRIMARY_COST_BPS
        or manifest["stress_cost_bps"] != FROZEN_STRESS_COST_BPS
        or manifest["strategy_protocol_sha256"] != STRATEGY_PROTOCOL_SHA256
    ):
        _fail("strategy_cost_policy_mismatch", "成本或短線策略雜湊不符")
    receipts = manifest["files"]
    if not isinstance(receipts, dict) or set(receipts) != set(OVERLAY_FILES):
        _fail("execution_source_manifest_invalid", "overlay 收據集合不符")
    benchmarks = _read_csv(
        source / "benchmark_daily.csv",
        BENCHMARK_COLUMNS,
        "benchmark_price_policy_invalid",
    )
    receipt = receipts["benchmark_daily.csv"]
    if (
        not isinstance(receipt, dict)
        or set(receipt) != {"sha256", "rows"}
        or not isinstance(receipt.get("sha256"), str)
        or SHA256_PATTERN.fullmatch(receipt["sha256"]) is None
        or not isinstance(receipt.get("rows"), int)
        or isinstance(receipt.get("rows"), bool)
        or receipt["sha256"] != _sha256_file(source / "benchmark_daily.csv")
        or receipt["rows"] != len(benchmarks)
    ):
        _fail("execution_source_manifest_invalid", "benchmark 收據不符")
    protocol = _protocol_integrity(root, first_imported_at)
    return manifest, benchmarks, protocol


def _read_ledger(ledger: Path) -> tuple[dict[str, Any], dict[str, pd.DataFrame]]:
    try:
        manifest = json.loads((ledger / "manifest.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        _fail("base_ledger_binding_mismatch", type(exc).__name__)
    tables = {
        name: _read_csv(ledger / name, REQUIRED_COLUMNS[name], "base_ledger_binding_mismatch")
        for name in REQUIRED_COLUMNS
    }
    return manifest, tables


def _calendar_and_signals(
    calendar: pd.DataFrame, study_start: str, study_end: str
) -> tuple[pd.DatetimeIndex, pd.DatetimeIndex]:
    sessions = pd.DatetimeIndex(pd.to_datetime(calendar["session"], errors="coerce"))
    if sessions.hasnans or not sessions.is_monotonic_increasing or sessions.has_duplicates:
        _fail("signal_calendar_invalid", "交易日曆無效")
    start = _date(study_start, "study_start")
    end = _date(study_end, "study_end")
    study = sessions[(sessions >= start) & (sessions <= end)]
    if not len(study):
        _fail("signal_calendar_invalid", "研究期沒有交易日")
    calendar_month_ends = (
        pd.Series(sessions, index=sessions).groupby(sessions.to_period("M")).max()
    )
    signal_index = pd.DatetimeIndex(
        day for day in calendar_month_ends.tolist() if start <= day <= end
    )
    if not len(signal_index):
        _fail("signal_calendar_invalid", "沒有完整月末訊號")
    return sessions, signal_index


def _next_session(sessions: pd.DatetimeIndex, signal: pd.Timestamp) -> pd.Timestamp:
    later = sessions[sessions > signal]
    if not len(later):
        _fail("execution_clock_violation", "月末訊號後沒有下一正式交易日")
    return pd.Timestamp(later[0])


def _build_cash_entitlements(
    ciz_source: Path, actions: pd.DataFrame
) -> pd.DataFrame:
    distributions = pd.read_csv(
        ciz_source / "stk_distributions.csv",
        dtype=str,
        keep_default_na=False,
        na_filter=False,
    )
    source_rows: dict[str, pd.Series] = {}
    for _, row in distributions.iterrows():
        event_id = f"CIZ-DIST-{row['PERMNO']}-{row['DisExDt']}-{row['DisSeqnbr']}"
        if event_id in source_rows:
            _fail("dividend_entitlement_mismatch", "distribution event ID 重複")
        source_rows[event_id] = row
    dividends = actions.loc[actions["event_type"] == "dividend"]
    rows: list[dict[str, object]] = []
    for action in dividends.itertuples(index=False):
        if action.event_id not in source_rows:
            _fail("dividend_entitlement_mismatch", "dividend action 沒有 CIZ source row")
        source = source_rows[action.event_id]
        pay_raw = str(source["DisPayDt"]).strip()
        if not pay_raw:
            _fail("dividend_pay_date_missing", f"{action.event_id} 缺 DisPayDt")
        ex_date = _date(source["DisExDt"], "DisExDt")
        pay_date = _date(pay_raw, "DisPayDt")
        if pay_date < ex_date:
            _fail("dividend_date_order_invalid", f"{action.event_id} pay-date 早於 ex-date")
        cash = _number(source["DisDivAmt"], "DisDivAmt")
        action_cash = _number(action.cash_amount, "cash_amount")
        if (
            action.ex_date != source["DisExDt"]
            or not math.isclose(cash, action_cash)
            or cash <= 0
        ):
            _fail("dividend_entitlement_mismatch", f"{action.event_id} 金額或 ex-date 不對數")
        rows.append(
            {
                "event_id": action.event_id,
                "security_id": action.security_id,
                "announced_at": action.announced_at,
                "ex_date": source["DisExDt"],
                "pay_date": pay_raw,
                "cash_available_date": pay_raw,
                "cash_per_share": cash,
                "source_record_id": action.source_record_id,
            }
        )
    return pd.DataFrame(rows, columns=CASH_ENTITLEMENT_COLUMNS)


def _members_at_signal(memberships: pd.DataFrame, signal: pd.Timestamp) -> pd.DataFrame:
    starts = pd.to_datetime(memberships["effective_from"], errors="coerce")
    ends = pd.to_datetime(memberships["effective_to"].replace("", pd.NA), errors="coerce")
    return memberships.loc[(starts <= signal) & (ends.isna() | (signal < ends))]


def _build_signal_eligibility(
    memberships: pd.DataFrame,
    prices: pd.DataFrame,
    signals: pd.DatetimeIndex,
) -> pd.DataFrame:
    priced = prices.copy()
    priced["__session"] = pd.to_datetime(priced["session"], errors="coerce")
    priced["__return"] = pd.to_numeric(priced["total_return_factor"], errors="coerce")
    priced["__volume"] = pd.to_numeric(priced["volume"], errors="coerce")
    rows: list[dict[str, object]] = []
    for signal in signals:
        for membership in _members_at_signal(memberships, signal).itertuples(index=False):
            history = priced.loc[
                (priced["security_id"] == membership.security_id)
                & (priced["__session"] < signal)
            ]
            return_sessions = int(
                (history["__return"].notna() & history["__return"].ge(0)).sum()
            )
            positive_volume_sessions = int(history["__volume"].gt(0).sum())
            if return_sessions < 252:
                _fail(
                    "pre_signal_return_history_missing",
                    f"{membership.security_id} 在 {signal.date()} 只有 {return_sessions}/252",
                )
            if positive_volume_sessions < 20:
                _fail(
                    "pre_signal_liquidity_history_missing",
                    f"{membership.security_id} 在 {signal.date()} 只有 "
                    f"{positive_volume_sessions}/20 正成交量日",
                )
            rows.append(
                {
                    "signal_session": str(signal.date()),
                    "security_id": membership.security_id,
                    "return_sessions": return_sessions,
                    "positive_volume_sessions": positive_volume_sessions,
                    "eligible": "true",
                    "source_record_id": membership.source_record_id,
                }
            )
    return pd.DataFrame(rows, columns=SIGNAL_ELIGIBILITY_COLUMNS)


def _build_removal_windows(
    outcomes: pd.DataFrame,
    prices: pd.DataFrame,
    sessions: pd.DatetimeIndex,
    signals: pd.DatetimeIndex,
) -> pd.DataFrame:
    priced = prices.copy()
    priced["__session"] = pd.to_datetime(priced["session"], errors="coerce")
    rows: list[dict[str, object]] = []
    removed = outcomes.loc[outcomes["outcome_type"] == "removed_continues"]
    for outcome in removed.itertuples(index=False):
        removed_at = _date(outcome.membership_effective_to, "membership_effective_to")
        later_signals = signals[signals >= removed_at]
        if not len(later_signals):
            _fail("post_removal_path_missing", "移除後沒有下一個月末訊號")
        signal = pd.Timestamp(later_signals[0])
        execution = _next_session(sessions, signal)
        required = sessions[(sessions >= removed_at) & (sessions <= execution)]
        security_prices = priced.loc[priced["security_id"] == outcome.security_id]
        available = set(security_prices["__session"].dropna())
        if any(day not in available for day in required):
            _fail(
                "post_removal_path_missing",
                f"{outcome.security_id} 移除後價格路徑中斷",
            )
        execution_row = security_prices.loc[security_prices["__session"] == execution]
        open_raw = (
            pd.to_numeric(execution_row["open_raw"], errors="coerce").iloc[0]
            if len(execution_row)
            else math.nan
        )
        if not math.isfinite(float(open_raw)) or float(open_raw) <= 0:
            _fail(
                "post_removal_execution_open_missing",
                f"{outcome.security_id} 下一重新平衡 raw open 缺失",
            )
        rows.append(
            {
                "security_id": outcome.security_id,
                "membership_effective_to": outcome.membership_effective_to,
                "signal_session": str(signal.date()),
                "execution_session": str(execution.date()),
                "required_sessions": len(required),
                "observed_sessions": len(required),
                "execution_open_raw": float(open_raw),
                "source_record_id": outcome.source_record_id,
            }
        )
    return pd.DataFrame(rows, columns=REMOVAL_WINDOW_COLUMNS)


def _validate_benchmarks(
    benchmarks: pd.DataFrame,
    sessions: pd.DatetimeIndex,
    signals: pd.DatetimeIndex,
    study_start: str,
    study_end: str,
) -> pd.DataFrame:
    if benchmarks.duplicated(["asset_id", "session"]).any():
        _fail("benchmark_duplicate", "QQQ／SPY 同日記錄重複")
    if set(benchmarks["asset_id"]) != {"QQQ", "SPY"}:
        _fail("benchmark_session_missing", "基準只可且必須同時包含 QQQ／SPY")
    if benchmarks["source_record_id"].eq("").any() or not benchmarks[
        "source_record_id"
    ].is_unique:
        _fail("benchmark_price_policy_invalid", "基準 source_record_id 缺失或重複")
    start = _date(study_start, "study_start")
    end = _date(study_end, "study_end")
    last_execution = max(_next_session(sessions, signal) for signal in signals)
    required = sessions[(sessions >= start) & (sessions <= max(end, last_execution))]
    required_strings = {str(day.date()) for day in required}
    for asset_id in ("QQQ", "SPY"):
        actual = set(benchmarks.loc[benchmarks["asset_id"] == asset_id, "session"])
        if actual != required_strings:
            _fail(
                "benchmark_session_missing",
                f"{asset_id} sessions missing={len(required_strings - actual)} "
                f"extra={len(actual - required_strings)}",
            )
    numeric = benchmarks.loc[
        :, ["open_raw", "high_raw", "low_raw", "close_raw", "volume", "total_return_factor"]
    ].apply(pd.to_numeric, errors="coerce")
    price_ok = bool(
        numeric.notna().all().all()
        and numeric[["open_raw", "high_raw", "low_raw", "close_raw"]].gt(0).all().all()
        and numeric["volume"].gt(0).all()
        and numeric["total_return_factor"].ge(0).all()
        and (numeric["high_raw"] >= numeric[["open_raw", "close_raw"]].max(axis=1)).all()
        and (numeric["low_raw"] <= numeric[["open_raw", "close_raw"]].min(axis=1)).all()
        and benchmarks["source_status"].eq("observed").all()
    )
    if not price_ok:
        _fail("benchmark_price_policy_invalid", "基準 raw OHLC、成交量或總回報因子無效")
    return benchmarks.sort_values(["asset_id", "session"]).reset_index(drop=True)


def _write_execution_layer(
    execution: Path,
    *,
    manifest: dict[str, Any],
    frames: dict[str, pd.DataFrame],
) -> None:
    execution.mkdir()
    receipts: dict[str, dict[str, object]] = {}
    for name, frame in frames.items():
        path = execution / name
        frame.to_csv(path, index=False, lineterminator="\n")
        receipts[name] = {"sha256": _sha256_file(path), "rows": len(frame)}
    output_manifest = {**manifest, "files": receipts}
    (execution / "execution_manifest.json").write_text(
        json.dumps(output_manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def transform_crsp_ciz_execution_bundle(
    ciz_source_bundle: str | Path,
    execution_overlay_bundle: str | Path,
    output_bundle: str | Path,
    *,
    root: str | Path,
) -> dict[str, Any]:
    """Build an atomic base-ledger plus Round 15 execution-extension package."""

    ciz_source = Path(ciz_source_bundle)
    overlay_source = Path(execution_overlay_bundle)
    destination = Path(output_bundle)
    root_path = Path(root)
    if destination.exists():
        _fail("execution_output_exists", "輸出目錄已存在；拒絕覆寫")
    overlay_manifest, benchmarks, protocol = _read_overlay(overlay_source, root_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
        prefix=f".{destination.name}-", dir=destination.parent
    ) as temporary:
        staging = Path(temporary) / destination.name
        staging.mkdir()
        ledger = staging / "ledger"
        base_result = transform_crsp_ciz_bundle(ciz_source, ledger, root=root_path)
        _, tables = _read_ledger(ledger)
        sessions, signals = _calendar_and_signals(
            tables["trading_calendar.csv"],
            overlay_manifest["study_start"],
            overlay_manifest["study_end"],
        )
        entitlements = _build_cash_entitlements(
            ciz_source, tables["corporate_actions.csv"]
        )
        eligibility = _build_signal_eligibility(
            tables["membership_history.csv"], tables["daily_prices.csv"], signals
        )
        removals = _build_removal_windows(
            tables["security_outcomes.csv"],
            tables["daily_prices.csv"],
            sessions,
            signals,
        )
        normalized_benchmarks = _validate_benchmarks(
            benchmarks,
            sessions,
            signals,
            overlay_manifest["study_start"],
            overlay_manifest["study_end"],
        )
        generated_at = overlay_manifest["first_imported_at"]
        execution_manifest = {
            "schema_version": 1,
            "status": "synthetic_execution_extension_built",
            "transform_version": EXECUTION_EXTENSION_VERSION,
            "generated_at": generated_at,
            "study_start": overlay_manifest["study_start"],
            "study_end": overlay_manifest["study_end"],
            "base_ledger_manifest_sha256": _sha256_file(ledger / "manifest.json"),
            "source_overlay_manifest_sha256": _sha256_file(
                overlay_source / "execution_overlay_manifest.json"
            ),
            "protocol_sha256": EXECUTION_EXTENSION_PROTOCOL_SHA256,
            "strategy_protocol_sha256": STRATEGY_PROTOCOL_SHA256,
            "price_basis": FROZEN_PRICE_BASIS,
            "signal_policy": FROZEN_SIGNAL_POLICY,
            "execution_clock": FROZEN_EXECUTION_CLOCK,
            "dividend_cash_policy": FROZEN_DIVIDEND_POLICY,
            "qqq_fallback_asset_id": FROZEN_QQQ_FALLBACK,
            "primary_cost_bps": FROZEN_PRIMARY_COST_BPS,
            "stress_cost_bps": FROZEN_STRESS_COST_BPS,
        }
        _write_execution_layer(
            staging / "execution",
            manifest=execution_manifest,
            frames={
                "cash_entitlements.csv": entitlements,
                "signal_eligibility.csv": eligibility,
                "removal_execution_windows.csv": removals,
                "benchmark_daily.csv": normalized_benchmarks,
            },
        )
        staging.rename(destination)
    return {
        "status": "ciz_execution_extension_built_audit_required",
        "transform_version": EXECUTION_EXTENSION_VERSION,
        "base_adapter_version": base_result["adapter_version"],
        "protocol_integrity": protocol,
        "signals": len(signals),
        "cash_entitlements": len(entitlements),
        "signal_eligibility_rows": len(eligibility),
        "removal_execution_windows": len(removals),
        "benchmark_rows": len(normalized_benchmarks),
        "strategy_rule_changed": False,
        "wrds_queried": False,
        "provider_rows_published": False,
    }


def _load_execution_layer(bundle: Path) -> tuple[dict[str, Any], dict[str, pd.DataFrame]]:
    if {item.name for item in bundle.iterdir() if item.is_dir()} != {"ledger", "execution"}:
        _fail("execution_source_file_set_mismatch", "輸出根目錄只可含 ledger／execution")
    execution = bundle / "execution"
    expected = {"execution_manifest.json", *EXECUTION_OUTPUT_FILES}
    actual = {item.name for item in execution.iterdir() if item.is_file()}
    if actual != expected:
        _fail("execution_source_file_set_mismatch", "execution 輸出檔案集合不符")
    try:
        manifest = json.loads(
            (execution / "execution_manifest.json").read_text(encoding="utf-8")
        )
    except (OSError, json.JSONDecodeError) as exc:
        _fail("execution_source_manifest_invalid", type(exc).__name__)
    if not isinstance(manifest, dict) or set(manifest) != EXECUTION_MANIFEST_KEYS:
        _fail("execution_source_manifest_invalid", "execution manifest keys 不符")
    frames = {
        "cash_entitlements.csv": _read_csv(
            execution / "cash_entitlements.csv",
            CASH_ENTITLEMENT_COLUMNS,
            "dividend_entitlement_mismatch",
        ),
        "signal_eligibility.csv": _read_csv(
            execution / "signal_eligibility.csv",
            SIGNAL_ELIGIBILITY_COLUMNS,
            "signal_calendar_invalid",
        ),
        "removal_execution_windows.csv": _read_csv(
            execution / "removal_execution_windows.csv",
            REMOVAL_WINDOW_COLUMNS,
            "post_removal_path_missing",
        ),
        "benchmark_daily.csv": _read_csv(
            execution / "benchmark_daily.csv",
            BENCHMARK_COLUMNS,
            "benchmark_price_policy_invalid",
        ),
    }
    receipts = manifest["files"]
    if not isinstance(receipts, dict) or set(receipts) != set(EXECUTION_OUTPUT_FILES):
        _fail("execution_source_manifest_invalid", "execution receipt 集合不符")
    for name, frame in frames.items():
        receipt = receipts[name]
        if (
            not isinstance(receipt, dict)
            or set(receipt) != {"sha256", "rows"}
            or receipt.get("sha256") != _sha256_file(execution / name)
            or receipt.get("rows") != len(frame)
        ):
            _fail("execution_source_manifest_invalid", f"{name} receipt 不符")
    return manifest, frames


def _assert_manifest_policies(manifest: dict[str, Any], ledger: Path) -> None:
    if manifest["base_ledger_manifest_sha256"] != _sha256_file(ledger / "manifest.json"):
        _fail("base_ledger_binding_mismatch", "base ledger manifest SHA-256 不符")
    if (
        manifest["schema_version"] != 1
        or manifest["status"] != "synthetic_execution_extension_built"
        or manifest["transform_version"] != EXECUTION_EXTENSION_VERSION
        or manifest["protocol_sha256"] != EXECUTION_EXTENSION_PROTOCOL_SHA256
    ):
        _fail("execution_source_manifest_invalid", "execution schema／版本／協議不符")
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


def _audit_entitlements(actions: pd.DataFrame, entitlements: pd.DataFrame) -> None:
    dividends = actions.loc[actions["event_type"] == "dividend"]
    if (
        entitlements["event_id"].eq("").any()
        or not entitlements["event_id"].is_unique
        or set(entitlements["event_id"]) != set(dividends["event_id"])
    ):
        _fail("dividend_entitlement_mismatch", "dividend 與 entitlement 不是一對一")
    merged = dividends.merge(entitlements, on="event_id", suffixes=("_action", "_cash"))
    for row in merged.itertuples(index=False):
        if not row.pay_date:
            _fail("dividend_pay_date_missing", f"{row.event_id} 缺 pay-date")
        ex_date = _date(row.ex_date_cash, "entitlement ex_date")
        pay_date = _date(row.pay_date, "entitlement pay_date")
        if pay_date < ex_date:
            _fail("dividend_date_order_invalid", f"{row.event_id} pay-date 早於 ex-date")
        if (
            row.cash_available_date != row.pay_date
            or row.security_id_action != row.security_id_cash
            or row.source_record_id_action != row.source_record_id_cash
            or row.ex_date_action != row.ex_date_cash
            or not math.isclose(
                _number(row.cash_amount, "action cash"),
                _number(row.cash_per_share, "cash_per_share"),
            )
        ):
            _fail("dividend_entitlement_mismatch", f"{row.event_id} entitlement 不對數")


def _audit_signal_rows(
    memberships: pd.DataFrame,
    prices: pd.DataFrame,
    signals: pd.DatetimeIndex,
    eligibility: pd.DataFrame,
) -> None:
    actual_signal_dates = set(eligibility["signal_session"])
    expected_signal_dates = {str(day.date()) for day in signals}
    if not actual_signal_dates.issubset(expected_signal_dates):
        _fail("signal_calendar_invalid", "eligibility 含非月末訊號")
    expected = _build_signal_eligibility(memberships, prices, signals)
    keys = ["signal_session", "security_id"]
    if eligibility.duplicated(keys).any() or set(map(tuple, eligibility[keys].to_numpy())) != set(
        map(tuple, expected[keys].to_numpy())
    ):
        _fail("signal_calendar_invalid", "eligibility 沒有完整覆蓋月末在籍候選")
    joined = expected.merge(eligibility, on=keys, suffixes=("_expected", "_actual"))
    for row in joined.itertuples(index=False):
        actual_returns = int(row.return_sessions_actual)
        actual_volume = int(row.positive_volume_sessions_actual)
        if actual_returns < 252:
            _fail("pre_signal_return_history_missing", "eligibility 記錄少於 252 日")
        if actual_volume < 20:
            _fail("pre_signal_liquidity_history_missing", "eligibility 記錄少於 20 日")
        if (
            actual_returns != int(row.return_sessions_expected)
            or actual_volume != int(row.positive_volume_sessions_expected)
            or row.eligible_actual != "true"
            or row.source_record_id_actual != row.source_record_id_expected
        ):
            _fail("signal_calendar_invalid", "eligibility 計數或來源不對數")


def _audit_removal_rows(
    outcomes: pd.DataFrame,
    prices: pd.DataFrame,
    sessions: pd.DatetimeIndex,
    signals: pd.DatetimeIndex,
    removals: pd.DataFrame,
) -> None:
    expected = _build_removal_windows(outcomes, prices, sessions, signals)
    keys = ["security_id", "membership_effective_to"]
    if removals.duplicated(keys).any() or set(map(tuple, removals[keys].to_numpy())) != set(
        map(tuple, expected[keys].to_numpy())
    ):
        _fail("post_removal_path_missing", "移除窗口不是一對一")
    joined = expected.merge(removals, on=keys, suffixes=("_expected", "_actual"))
    for row in joined.itertuples(index=False):
        signal = _date(row.signal_session_actual, "removal signal")
        execution = _date(row.execution_session_actual, "removal execution")
        if execution != _next_session(sessions, signal):
            _fail("execution_clock_violation", "移除成交不是訊號後下一交易日")
        if (
            row.signal_session_actual != row.signal_session_expected
            or row.execution_session_actual != row.execution_session_expected
            or int(row.required_sessions_actual) != int(row.required_sessions_expected)
            or int(row.observed_sessions_actual) != int(row.observed_sessions_expected)
            or row.source_record_id_actual != row.source_record_id_expected
        ):
            _fail("post_removal_path_missing", "移除路徑或 session 計數不對數")
        try:
            execution_open = float(row.execution_open_raw_actual)
        except (TypeError, ValueError):
            execution_open = math.nan
        if not math.isfinite(execution_open) or execution_open <= 0:
            _fail("post_removal_execution_open_missing", "移除成交 raw open 無效")


def audit_ciz_execution_extension_bundle(
    bundle: str | Path,
    *,
    root: str | Path,
    requirements: PointInTimeRequirements,
) -> dict[str, Any]:
    """Audit one built Round 15 package against all sixteen frozen controls."""

    package = Path(bundle)
    root_path = Path(root)
    manifest, frames = _load_execution_layer(package)
    protocol = _protocol_integrity(root_path, _timestamp(manifest["generated_at"], "generated_at"))
    ledger = package / "ledger"
    _assert_manifest_policies(manifest, ledger)
    ledger_audit = audit_point_in_time_bundle(
        ledger, root=root_path, requirements=requirements
    )
    if not ledger_audit["gate_summary"]["all_passed"]:
        _fail("base_ledger_binding_mismatch", "base ledger 未通過原 20 道閘門")
    _, tables = _read_ledger(ledger)
    sessions, signals = _calendar_and_signals(
        tables["trading_calendar.csv"], manifest["study_start"], manifest["study_end"]
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
    eligibility = frames["signal_eligibility.csv"]
    cash_example = (
        frames["cash_entitlements.csv"].iloc[0].to_dict()
        if len(frames["cash_entitlements.csv"])
        else None
    )
    removal_example = (
        frames["removal_execution_windows.csv"].iloc[0].to_dict()
        if len(frames["removal_execution_windows.csv"])
        else None
    )
    gate_rows = [
        ("01", "事前凍結完整性", protocol["passed"], "協議、收據及前置雜湊完整"),
        ("02", "第十三／十四輪不變", True, "舊 adapter 及 Round 14 auditor 雜湊不變"),
        ("03", "精確輸入檔案集合", True, "overlay 及 execution 檔案集合／收據一致"),
        ("04", "Base ledger 仍為 20/20", True, "原 point-in-time auditor 全數通過"),
        ("05", "Base／extension 綁定", True, "base manifest SHA-256 對數"),
        ("06", "派息事件一對一", True, "dividend action 與 entitlement 一對一"),
        ("07", "Ex-date／pay-date 分離", True, "付款日存在且不早於除息日"),
        ("08", "現金只在付款日可用", True, "cash_available_date 恰等於 pay-date"),
        ("09", "月末訊號日曆固定", True, f"{len(signals)} 個完整月末訊號"),
        ("10", "訊號前回報歷史", True, "所有候選至少 252 個有效回報 session"),
        ("11", "訊號前流動性歷史", True, "所有候選至少 20 個正成交量 session"),
        ("12", "移除後完整價格路徑", True, "移除日至下一重新平衡逐日可定價"),
        ("13", "移除後真實開市價", True, "退出成交日有正 raw open"),
        ("14", "公平基準同步", True, "QQQ／SPY 必要 session 完全一致"),
        ("15", "QQQ 補位與 D+1 時鐘", True, "同一 QQQ 序列及下一交易日 open"),
        ("16", "規則及成本不變", True, "10／25／50 bps 及短線 v1 雜湊吻合"),
    ]
    return {
        "status": "synthetic_execution_extension_control_passed",
        "gate_summary": {"passed": 16, "total": 16, "all_passed": True},
        "gates": [
            {"id": gate_id, "label": label, "passed": bool(passed), "detail": detail}
            for gate_id, label, passed, detail in gate_rows
        ],
        "protocol_integrity": protocol,
        "base_ledger_gate_summary": ledger_audit["gate_summary"],
        "signals": len(signals),
        "cash_entitlements": len(frames["cash_entitlements.csv"]),
        "signal_eligibility_rows": len(frames["signal_eligibility.csv"]),
        "removal_execution_windows": len(frames["removal_execution_windows.csv"]),
        "benchmark_rows": len(frames["benchmark_daily.csv"]),
        "control_examples": {
            "dividend": cash_example,
            "minimum_return_sessions": int(
                pd.to_numeric(eligibility["return_sessions"]).min()
            ),
            "minimum_positive_volume_sessions": int(
                pd.to_numeric(eligibility["positive_volume_sessions"]).min()
            ),
            "removal": removal_example,
            "benchmark_assets": sorted(
                frames["benchmark_daily.csv"]["asset_id"].unique().tolist()
            ),
        },
        "formal_stock_backtest_authorized": False,
        "paper_authorized": False,
        "real_money_action_usd": 0,
    }
