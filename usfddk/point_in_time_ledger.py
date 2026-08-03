from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import exchange_calendars as xcals
import numpy as np
import pandas as pd

POINT_IN_TIME_SCHEMA_VERSION = 1
POINT_IN_TIME_PROTOCOL_SHA256 = (
    "1e684e0ddbffbd29860a78d01c27b1e42885d53fafd8b1b95ae47b7547396b6c"
)
POINT_IN_TIME_MANIFEST_SCHEMA_SHA256 = (
    "f6fba2f7117381c4bea3bde3db4f730bd282d6cc991d0e7b1df0e4ac1a24f160"
)
EXISTING_SHORT_TERM_PROTOCOL_SHA256 = (
    "589a799b18412e1fdad569c48e94313689c57b75eae84972a5c20baaa6ede139"
)

REQUIRED_FILES = (
    "security_master.csv",
    "identifier_history.csv",
    "membership_history.csv",
    "trading_calendar.csv",
    "daily_prices.csv",
    "corporate_actions.csv",
    "classification_history.csv",
    "security_outcomes.csv",
)

REQUIRED_COLUMNS: dict[str, tuple[str, ...]] = {
    "security_master.csv": (
        "security_id",
        "company_id",
        "security_type",
        "share_class",
        "country_of_incorporation",
        "currency",
    ),
    "identifier_history.csv": (
        "security_id",
        "ticker",
        "exchange",
        "cusip",
        "isin",
        "effective_from",
        "effective_to",
        "known_at",
    ),
    "membership_history.csv": (
        "index_id",
        "security_id",
        "effective_from",
        "effective_to",
        "announced_at",
        "source_record_id",
    ),
    "trading_calendar.csv": ("session", "exchange", "open_at", "close_at"),
    "daily_prices.csv": (
        "security_id",
        "session",
        "open_raw",
        "high_raw",
        "low_raw",
        "close_raw",
        "volume",
        "cash_distribution",
        "split_factor",
        "total_return_factor",
        "source_status",
    ),
    "corporate_actions.csv": (
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
    ),
    "classification_history.csv": (
        "security_id",
        "scheme",
        "sector_code",
        "industry_code",
        "effective_from",
        "effective_to",
        "known_at",
        "source_record_id",
    ),
    "security_outcomes.csv": (
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
    ),
}

MANIFEST_REQUIRED_KEYS = {
    "schema_version",
    "provider",
    "provider_product",
    "license_attestation",
    "exported_at",
    "first_imported_at",
    "as_of_date",
    "currency",
    "timezone",
    "adjustment_policy",
    "membership_timestamp_policy",
    "delisting_policy",
    "execution_clock",
    "transform_version",
    "files",
}
MANIFEST_POLICY_VALUES = {
    "adjustment_policy": "raw_ohlc_plus_event_ledger_no_future_adjusted_filters",
    "membership_timestamp_policy": (
        "announced_and_effective_timestamps_no_current_constituent_backfill"
    ),
    "delisting_policy": (
        "include_delisting_return_or_cash_stock_consideration_no_silent_drop"
    ),
    "execution_clock": "signal_close_t_trade_open_t_plus_1",
}
EXIT_OUTCOMES = {"delisted", "acquired_cash", "acquired_stock", "bankrupt"}
OUTCOME_TYPES = {"still_member", "removed_continues", *EXIT_OUTCOMES}
PRICE_STATUSES = {"observed", "delisted", "cash_acquisition", "suspended"}
EVENT_TYPES = {
    "dividend",
    "split",
    "spinoff",
    "merger_cash",
    "merger_stock",
    "bankruptcy",
    "delisting",
    "rights",
}


@dataclass(frozen=True)
class PointInTimeRequirements:
    start: str = "2006-08-01"
    end: str = "2026-07-31"
    index_id: str = "SP500"
    min_daily_members: int = 495
    max_daily_members: int = 510
    min_member_price_coverage: float = 0.995


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _date_series(frame: pd.DataFrame, column: str) -> pd.Series:
    raw = frame[column].replace("", pd.NA)
    return pd.to_datetime(raw, errors="coerce").dt.normalize()


def _utc_series(frame: pd.DataFrame, column: str) -> pd.Series:
    raw = frame[column].replace("", pd.NA)
    return pd.to_datetime(raw, errors="coerce", utc=True)


def _number_series(frame: pd.DataFrame, column: str) -> pd.Series:
    return pd.to_numeric(frame[column].replace("", pd.NA), errors="coerce")


def _end_dates(frame: pd.DataFrame, column: str) -> pd.Series:
    return _date_series(frame, column).fillna(pd.Timestamp("2262-04-11"))


def _intervals_non_overlapping(
    frame: pd.DataFrame,
    *,
    groups: list[str],
    start: str = "effective_from",
    end: str = "effective_to",
) -> bool:
    if frame.empty:
        return True
    work = frame.copy()
    work["__start"] = _date_series(work, start)
    work["__end"] = _end_dates(work, end)
    if work[["__start", "__end"]].isna().any().any():
        return False
    if not bool((work["__start"] < work["__end"]).all()):
        return False
    grouper: str | list[str] = groups[0] if len(groups) == 1 else groups
    for _, rows in work.sort_values([*groups, "__start", "__end"]).groupby(
        grouper, dropna=False
    ):
        starts = rows["__start"].to_numpy()
        ends = rows["__end"].to_numpy()
        if len(rows) > 1 and bool(np.any(starts[1:] < np.maximum.accumulate(ends[:-1]))):
            return False
    return True


def _gate(passed: bool, detail: str, stats: Mapping[str, Any] | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {"passed": bool(passed), "detail": detail}
    if stats:
        payload["stats"] = dict(stats)
    return payload


def _empty_gates() -> dict[str, dict[str, Any]]:
    labels = {
        "01_authorized_provider": "合法授權及供應商產品",
        "02_manifest_and_file_set": "manifest schema 與檔案集合",
        "03_hash_and_row_receipts": "原始檔 SHA-256 及列數",
        "04_preregistration_order": "協議早於首次供應商匯入",
        "05_security_master": "永久證券主檔",
        "06_identifier_history": "歷史代號無重疊或歧義",
        "07_membership_availability": "成分公布時間無前視",
        "08_membership_intervals": "成分區間完整且不重疊",
        "09_fixed_20_year_calendar": "固定 20 年正式交易日",
        "10_daily_member_count": "每日成分數 495–510",
        "11_member_price_coverage": "在籍股份價格／停牌覆蓋",
        "12_market_data_validity": "OHLCV 及總回報因子",
        "13_raw_price_policy": "原始價與調整用途分離",
        "14_corporate_actions": "公司行動唯一且可對數",
        "15_outcome_coverage": "每段 membership 有結果",
        "16_permanent_exit_economics": "永久退出經濟回報完整",
        "17_no_post_exit_prices": "退出後沒有幽靈價格",
        "18_point_in_time_classifications": "歷史分類當時可知",
        "19_share_class_dedup_capability": "同公司股份類別可去重",
        "20_execution_clock": "t 收市訊號／t+1 開市成交",
    }
    return {key: _gate(False, f"未驗證：{label}") for key, label in labels.items()}


def _protocol_receipt_gate(root: Path, manifest: Mapping[str, Any] | None) -> dict[str, Any]:
    receipt_path = root / "artifacts/short_term_point_in_time_protocol_receipt.json"
    try:
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        current_hashes = {
            "protocol": _sha256_file(root / receipt["protocol"]["path"]),
            "manifest_schema": _sha256_file(root / receipt["manifest_schema"]["path"]),
            "existing_strategy_protocol": _sha256_file(
                root / receipt["existing_strategy_protocol"]["path"]
            ),
        }
        expected_hashes = {
            "protocol": POINT_IN_TIME_PROTOCOL_SHA256,
            "manifest_schema": POINT_IN_TIME_MANIFEST_SCHEMA_SHA256,
            "existing_strategy_protocol": EXISTING_SHORT_TERM_PROTOCOL_SHA256,
        }
        receipt_hashes = {
            "protocol": receipt["protocol"]["sha256"],
            "manifest_schema": receipt["manifest_schema"]["sha256"],
            "existing_strategy_protocol": receipt["existing_strategy_protocol"]["sha256"],
        }
        integrity = (
            receipt.get("status") == "frozen_before_first_authorized_provider_import"
            and receipt.get("provider_bundle_present_at_freeze") is False
            and receipt.get("paper_authorized") is False
            and current_hashes == expected_hashes == receipt_hashes
        )
        ordering = True
        imported_at: str | None = None
        if manifest is not None:
            imported_at = str(manifest.get("first_imported_at", ""))
            frozen = pd.to_datetime(receipt.get("frozen_at"), utc=True, errors="coerce")
            imported = pd.to_datetime(imported_at, utc=True, errors="coerce")
            ordering = bool(pd.notna(frozen) and pd.notna(imported) and imported > frozen)
        passed = integrity and ordering
        detail = (
            "協議、manifest schema 及既有 v1 規則雜湊吻合；首次匯入晚於凍結"
            if passed and manifest is not None
            else "協議已在沒有供應商數據時凍結；等待首次匯入"
            if passed
            else "凍結收據、文件雜湊或首次匯入時序不符"
        )
        return _gate(
            passed,
            detail,
            {
                "frozen_at": receipt.get("frozen_at"),
                "first_imported_at": imported_at,
                "hash_integrity": integrity,
                "ordering_ok": ordering,
            },
        )
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        return _gate(False, f"無法驗證凍結收據：{type(exc).__name__}")


def _result(
    gates: dict[str, dict[str, Any]],
    *,
    bundle_present: bool,
    bundle_name: str | None,
    provider: str | None = None,
    as_of_date: str | None = None,
) -> dict[str, Any]:
    passed = sum(int(item["passed"]) for item in gates.values())
    ready = passed == len(gates)
    status = (
        "point_in_time_data_contract_passed_backtest_not_run"
        if ready
        else "blocked_by_point_in_time_data_contract"
    )
    return {
        "schema_version": POINT_IN_TIME_SCHEMA_VERSION,
        "research_round": 9,
        "status": status,
        "bundle": {
            "configured": bundle_present,
            "name": bundle_name,
            "provider": provider,
            "as_of_date": as_of_date,
            "absolute_path_published": False,
        },
        "gate_summary": {"passed": passed, "total": len(gates), "all_passed": ready},
        "gates": gates,
        "strategy_rule_changed": False,
        "formal_backtest_authorized": ready,
        "formal_backtest_completed": False,
        "paper": {
            "authorized": False,
            "state": "all_cash",
            "backfilled_trades": 0,
            "positions": [],
        },
        "real_money_action_usd": 0,
        "next_action": (
            "按已凍結 v1 規則只運行一次正式 20 年逐股回測"
            if ready
            else "取得合法 point-in-time／退市數據包後重新執行同一稽核；不得用現時成分或刪除退出樣本繞過"
        ),
        "disclaimer": "數據入口通過不代表策略通過，不構成投資建議或盈利保證。",
    }


def _load_bundle(bundle: Path) -> tuple[dict[str, Any], dict[str, pd.DataFrame]]:
    manifest = json.loads((bundle / "manifest.json").read_text(encoding="utf-8"))
    tables = {
        name: pd.read_csv(
            bundle / name,
            dtype=str,
            keep_default_na=False,
            na_filter=False,
        )
        for name in REQUIRED_FILES
    }
    return manifest, tables


def audit_point_in_time_bundle(
    bundle: str | Path | None,
    *,
    root: str | Path,
    requirements: PointInTimeRequirements | None = None,
) -> dict[str, Any]:
    """Audit an authorized provider transform and fail closed on any ambiguity.

    The returned payload is safe for a public readiness page: it never includes an
    absolute provider path or any raw security rows.
    """

    root_path = Path(root)
    requirements = requirements or PointInTimeRequirements()
    gates = _empty_gates()
    bundle_path = None if bundle is None else Path(bundle)
    bundle_present = bool(bundle_path is not None and bundle_path.is_dir())
    gates["04_preregistration_order"] = _protocol_receipt_gate(root_path, None)
    if not bundle_present:
        return _result(
            gates,
            bundle_present=False,
            bundle_name=None if bundle_path is None else bundle_path.name,
        )

    assert bundle_path is not None
    expected_names = {"manifest.json", *REQUIRED_FILES}
    actual_names = {item.name for item in bundle_path.iterdir() if item.is_file()}
    try:
        manifest, tables = _load_bundle(bundle_path)
    except (OSError, ValueError, json.JSONDecodeError, pd.errors.ParserError) as exc:
        gates["02_manifest_and_file_set"] = _gate(
            False, f"數據包無法完整讀取：{type(exc).__name__}"
        )
        return _result(gates, bundle_present=True, bundle_name=bundle_path.name)

    gates["04_preregistration_order"] = _protocol_receipt_gate(root_path, manifest)
    provider = str(manifest.get("provider", "")).strip() or None
    as_of_date = str(manifest.get("as_of_date", "")).strip() or None

    license_data = manifest.get("license_attestation")
    license_ok = (
        isinstance(license_data, dict)
        and license_data.get("authorized_for_local_research") is True
        and bool(str(license_data.get("attested_at", "")).strip())
        and provider is not None
        and bool(str(manifest.get("provider_product", "")).strip())
    )
    gates["01_authorized_provider"] = _gate(
        license_ok,
        "本地研究授權聲明、供應商及產品齊全"
        if license_ok
        else "缺少本地研究授權聲明、供應商或產品",
    )

    manifest_keys_ok = set(manifest) == MANIFEST_REQUIRED_KEYS
    policies_ok = all(manifest.get(key) == value for key, value in MANIFEST_POLICY_VALUES.items())
    scalar_ok = (
        manifest.get("schema_version") == POINT_IN_TIME_SCHEMA_VERSION
        and manifest.get("currency") == "USD"
        and manifest.get("timezone") == "America/New_York"
        and bool(str(manifest.get("transform_version", "")).strip())
        and pd.notna(pd.to_datetime(manifest.get("exported_at"), utc=True, errors="coerce"))
        and pd.notna(pd.to_datetime(manifest.get("first_imported_at"), utc=True, errors="coerce"))
        and pd.notna(pd.to_datetime(manifest.get("as_of_date"), errors="coerce"))
    )
    file_receipts = manifest.get("files")
    receipt_set_ok = isinstance(file_receipts, dict) and set(file_receipts) == set(REQUIRED_FILES)
    file_set_ok = actual_names == expected_names
    columns_ok = all(
        set(table.columns) == set(REQUIRED_COLUMNS[name]) for name, table in tables.items()
    )
    gate_02 = manifest_keys_ok and policies_ok and scalar_ok and receipt_set_ok and file_set_ok
    gates["02_manifest_and_file_set"] = _gate(
        gate_02,
        "manifest、固定政策及精確檔案集合吻合"
        if gate_02
        else "manifest 欄位、固定政策或精確檔案集合不符",
        {
            "manifest_keys_ok": manifest_keys_ok,
            "policies_ok": policies_ok,
            "file_set_ok": file_set_ok,
            "file_receipt_set_ok": receipt_set_ok,
        },
    )

    receipt_checks: dict[str, bool] = {}
    if receipt_set_ok:
        for name in REQUIRED_FILES:
            receipt = file_receipts[name]
            receipt_checks[name] = bool(
                isinstance(receipt, dict)
                and set(receipt) == {"sha256", "rows"}
                and receipt.get("sha256") == _sha256_file(bundle_path / name)
                and receipt.get("rows") == len(tables[name])
            )
    hash_rows_ok = receipt_set_ok and len(receipt_checks) == len(REQUIRED_FILES) and all(
        receipt_checks.values()
    )
    gates["03_hash_and_row_receipts"] = _gate(
        hash_rows_ok,
        "八個 CSV 的 SHA-256 與列數全部吻合"
        if hash_rows_ok
        else "至少一個 CSV 的 SHA-256 或列數不符",
        {"files_passed": sum(receipt_checks.values()), "files_total": len(REQUIRED_FILES)},
    )

    if not columns_ok:
        gates["05_security_master"] = _gate(False, "至少一個 CSV 欄位集合不符固定合約")
        return _result(
            gates,
            bundle_present=True,
            bundle_name=bundle_path.name,
            provider=provider,
            as_of_date=as_of_date,
        )

    master = tables["security_master.csv"]
    identifiers = tables["identifier_history.csv"]
    memberships = tables["membership_history.csv"]
    calendar = tables["trading_calendar.csv"]
    prices = tables["daily_prices.csv"]
    actions = tables["corporate_actions.csv"]
    classifications = tables["classification_history.csv"]
    outcomes = tables["security_outcomes.csv"]

    master_ids = set(master["security_id"])
    master_ok = bool(
        len(master)
        and master["security_id"].ne("").all()
        and master["security_id"].is_unique
        and master["company_id"].ne("").all()
        and master["share_class"].ne("").all()
        and master["security_type"].eq("common_stock").all()
        and master["country_of_incorporation"].eq("US").all()
        and master["currency"].eq("USD").all()
    )
    gates["05_security_master"] = _gate(
        master_ok,
        "永久證券 ID 唯一，普通股、公司及股份類別欄位完整"
        if master_ok
        else "證券主檔有空白、重複 ID 或非本輪合資格普通股",
        {"securities": len(master), "companies": int(master["company_id"].nunique())},
    )

    identifier_dates = pd.DataFrame(
        {
            "start": _date_series(identifiers, "effective_from"),
            "known": _utc_series(identifiers, "known_at").dt.tz_localize(None).dt.normalize(),
        }
    )
    identifier_ok = bool(
        len(identifiers)
        and identifiers["security_id"].isin(master_ids).all()
        and identifiers[["ticker", "exchange"]].ne("").all().all()
        and ((identifiers["cusip"] != "") | (identifiers["isin"] != "")).all()
        and identifier_dates.notna().all().all()
        and (identifier_dates["known"] <= identifier_dates["start"]).all()
        and _intervals_non_overlapping(identifiers, groups=["security_id"])
        and _intervals_non_overlapping(identifiers, groups=["ticker", "exchange"])
    )
    gates["06_identifier_history"] = _gate(
        identifier_ok,
        "歷史代號以永久 ID 連接，區間無重疊或同日歧義"
        if identifier_ok
        else "歷史代號缺失、可用時間過晚、區間重疊或同日指向多證券",
        {"identifier_rows": len(identifiers)},
    )

    membership_start = _date_series(memberships, "effective_from")
    membership_end = _end_dates(memberships, "effective_to")
    announced = _utc_series(memberships, "announced_at").dt.tz_localize(None).dt.normalize()
    membership_availability_ok = bool(
        len(memberships)
        and memberships["index_id"].eq(requirements.index_id).all()
        and memberships["security_id"].isin(master_ids).all()
        and memberships["source_record_id"].ne("").all()
        and memberships["source_record_id"].is_unique
        and membership_start.notna().all()
        and announced.notna().all()
        and (announced <= membership_start).all()
    )
    gates["07_membership_availability"] = _gate(
        membership_availability_ok,
        "所有成分公布時間不晚於實際生效日"
        if membership_availability_ok
        else "成分來源、永久 ID、公布時間或生效時間不合格",
        {"membership_spells": len(memberships)},
    )
    membership_intervals_ok = bool(
        membership_start.notna().all()
        and (membership_start < membership_end).all()
        and _intervals_non_overlapping(
            memberships, groups=["index_id", "security_id"]
        )
    )
    gates["08_membership_intervals"] = _gate(
        membership_intervals_ok,
        "成分半開區間有效且同一證券不重疊"
        if membership_intervals_ok
        else "成分起訖無效或同一證券區間重疊",
    )

    sessions = _date_series(calendar, "session")
    opens = _utc_series(calendar, "open_at")
    closes = _utc_series(calendar, "close_at")
    calendar_valid = bool(
        len(calendar)
        and sessions.notna().all()
        and sessions.is_unique
        and sessions.is_monotonic_increasing
        and calendar["exchange"].isin({"XNYS", "XNAS"}).all()
        and opens.notna().all()
        and closes.notna().all()
        and (opens < closes).all()
    )
    req_start = pd.Timestamp(requirements.start)
    req_end = pd.Timestamp(requirements.end)
    fixed_sessions = sessions[(sessions >= req_start) & (sessions <= req_end)]
    expected_sessions = pd.DatetimeIndex(
        xcals.get_calendar("XNYS").sessions_in_range(req_start, req_end)
    )
    if expected_sessions.tz is not None:
        expected_sessions = expected_sessions.tz_localize(None)
    actual_session_index = pd.DatetimeIndex(fixed_sessions)
    exact_exchange_calendar = bool(actual_session_index.equals(expected_sessions))
    missing_exchange_sessions = expected_sessions.difference(actual_session_index)
    extra_exchange_sessions = actual_session_index.difference(expected_sessions)
    calendar_coverage = bool(
        calendar_valid
        and len(fixed_sessions)
        and sessions.min() <= req_start
        and sessions.max() >= req_end
        and exact_exchange_calendar
    )
    gates["09_fixed_20_year_calendar"] = _gate(
        calendar_coverage,
        "正式交易日完整覆蓋固定主期"
        if calendar_coverage
        else "交易日無效或未覆蓋固定 2006-08-01 至 2026-07-31 主期",
        {
            "first_session": None if sessions.dropna().empty else str(sessions.min().date()),
            "last_session": None if sessions.dropna().empty else str(sessions.max().date()),
            "required_sessions": len(fixed_sessions),
            "expected_xnys_sessions": len(expected_sessions),
            "missing_xnys_sessions": len(missing_exchange_sessions),
            "extra_non_xnys_sessions": len(extra_exchange_sessions),
        },
    )

    member_counts = np.zeros(len(fixed_sessions), dtype=int)
    fixed_session_values = fixed_sessions.to_numpy()
    if membership_intervals_ok and len(fixed_sessions):
        for start, end in zip(membership_start, membership_end, strict=True):
            left = int(np.searchsorted(fixed_session_values, np.datetime64(start), side="left"))
            right = int(np.searchsorted(fixed_session_values, np.datetime64(end), side="left"))
            member_counts[left:right] += 1
    counts_ok = bool(
        len(member_counts)
        and int(member_counts.min()) >= requirements.min_daily_members
        and int(member_counts.max()) <= requirements.max_daily_members
    )
    gates["10_daily_member_count"] = _gate(
        counts_ok,
        "每個固定主期交易日的成分數均在事前範圍"
        if counts_ok
        else "至少一日成分數低於下限或高於上限",
        {
            "minimum": None if not len(member_counts) else int(member_counts.min()),
            "maximum": None if not len(member_counts) else int(member_counts.max()),
            "required_minimum": requirements.min_daily_members,
            "required_maximum": requirements.max_daily_members,
        },
    )

    price_sessions = _date_series(prices, "session")
    price_ids_ok = prices["security_id"].isin(master_ids).all()
    price_keys_unique = not prices.duplicated(["security_id", "session"]).any()
    price_session_sets = {
        security_id: set(rows.dropna().to_numpy())
        for security_id, rows in pd.Series(price_sessions.to_numpy(), index=prices["security_id"]).groupby(
            level=0
        )
    }
    required_observations = 0
    covered_observations = 0
    missing_examples: list[str] = []
    if membership_intervals_ok and len(fixed_sessions):
        for row_index, row in memberships.iterrows():
            active = fixed_sessions[
                (fixed_sessions >= membership_start.loc[row_index])
                & (fixed_sessions < membership_end.loc[row_index])
            ]
            required_observations += len(active)
            available = price_session_sets.get(row["security_id"], set())
            hits = sum(np.datetime64(day) in available for day in active)
            covered_observations += hits
            if hits < len(active) and len(missing_examples) < 5:
                missing_examples.append(str(row["security_id"]))
    price_coverage = (
        covered_observations / required_observations if required_observations else 0.0
    )
    coverage_ok = bool(
        price_ids_ok
        and price_keys_unique
        and price_coverage >= requirements.min_member_price_coverage
    )
    gates["11_member_price_coverage"] = _gate(
        coverage_ok,
        "在籍股份每日均有價格或明確停牌記錄，覆蓋達門檻"
        if coverage_ok
        else "在籍股份價格／停牌覆蓋不足或複合鍵重複",
        {
            "coverage": round(price_coverage, 8),
            "required": requirements.min_member_price_coverage,
            "required_observations": required_observations,
            "covered_observations": covered_observations,
            "missing_security_examples": missing_examples,
        },
    )

    status_ok = prices["source_status"].isin(PRICE_STATUSES)
    suspended = prices["source_status"].eq("suspended")
    observed = ~suspended
    numeric_prices = {
        column: _number_series(prices, column)
        for column in (
            "open_raw",
            "high_raw",
            "low_raw",
            "close_raw",
            "volume",
            "cash_distribution",
            "split_factor",
            "total_return_factor",
        )
    }
    ohlc = pd.DataFrame({key: numeric_prices[key] for key in ("open_raw", "high_raw", "low_raw", "close_raw")})
    observed_ohlc_ok = bool(
        ohlc.loc[observed].notna().all().all()
        and (ohlc.loc[observed] > 0).all().all()
        and (numeric_prices["high_raw"].loc[observed] >= numeric_prices["open_raw"].loc[observed]).all()
        and (numeric_prices["high_raw"].loc[observed] >= numeric_prices["close_raw"].loc[observed]).all()
        and (numeric_prices["low_raw"].loc[observed] <= numeric_prices["open_raw"].loc[observed]).all()
        and (numeric_prices["low_raw"].loc[observed] <= numeric_prices["close_raw"].loc[observed]).all()
    )
    suspended_ok = bool(
        ohlc.loc[suspended].isna().all().all()
        and numeric_prices["volume"].loc[suspended].fillna(-1).eq(0).all()
    )
    volume = numeric_prices["volume"]
    factors = numeric_prices["total_return_factor"]
    zero_factor_ok = (~factors.eq(0)) | prices["source_status"].isin({"delisted"})
    market_data_ok = bool(
        price_ids_ok
        and price_keys_unique
        and price_sessions.notna().all()
        and set(price_sessions).issubset(set(sessions))
        and status_ok.all()
        and observed_ohlc_ok
        and suspended_ok
        and volume.notna().all()
        and (volume >= 0).all()
        and np.isclose(volume, np.round(volume)).all()
        and numeric_prices["cash_distribution"].notna().all()
        and (numeric_prices["cash_distribution"] >= 0).all()
        and numeric_prices["split_factor"].notna().all()
        and (numeric_prices["split_factor"] > 0).all()
        and factors.notna().all()
        and (factors >= 0).all()
        and zero_factor_ok.all()
    )
    gates["12_market_data_validity"] = _gate(
        market_data_ok,
        "OHLCV、停牌、拆細、派息及總回報因子均有效"
        if market_data_ok
        else "市場數據含無效 OHLCV、狀態或回報因子",
        {"price_rows": len(prices), "suspended_rows": int(suspended.sum())},
    )
    raw_policy_ok = bool(
        manifest.get("adjustment_policy")
        == MANIFEST_POLICY_VALUES["adjustment_policy"]
        and {"open_raw", "close_raw", "cash_distribution", "split_factor"}.issubset(prices)
    )
    gates["13_raw_price_policy"] = _gate(
        raw_policy_ok,
        "流動性門檻使用原始價，公司行動由獨立賬本對數"
        if raw_policy_ok
        else "未證明原始價與事後調整用途分離",
    )

    action_dates = pd.DataFrame(
        {
            "announced": _utc_series(actions, "announced_at").dt.tz_localize(None).dt.normalize(),
            "effective": _date_series(actions, "effective_date"),
            "ex": _date_series(actions, "ex_date"),
        }
    )
    action_cash = _number_series(actions, "cash_amount")
    action_ratio = _number_series(actions, "share_ratio")
    action_terms_ok = pd.Series(True, index=actions.index)
    action_terms_ok &= ~actions["event_type"].eq("dividend") | action_cash.gt(0)
    action_terms_ok &= ~actions["event_type"].eq("split") | action_ratio.gt(0)
    action_terms_ok &= ~actions["event_type"].eq("merger_cash") | action_cash.gt(0)
    action_terms_ok &= ~actions["event_type"].eq("merger_stock") | (
        action_ratio.gt(0) & actions["successor_security_id"].ne("")
    )
    action_ex_keys = {
        (str(actions.loc[index, "security_id"]), str(actions.loc[index, "event_type"]), day)
        for index, day in action_dates["ex"].items()
        if pd.notna(day)
    }
    action_effective_keys = {
        (str(actions.loc[index, "security_id"]), str(actions.loc[index, "event_type"]), day)
        for index, day in action_dates["effective"].items()
        if pd.notna(day)
    }
    distribution_rows = numeric_prices["cash_distribution"].gt(0)
    split_rows = ~np.isclose(numeric_prices["split_factor"], 1.0)
    distribution_matches = all(
        (str(prices.loc[index, "security_id"]), "dividend", price_sessions.loc[index])
        in action_ex_keys
        for index in prices.index[distribution_rows]
    )
    split_matches = all(
        (str(prices.loc[index, "security_id"]), "split", price_sessions.loc[index])
        in action_ex_keys
        for index in prices.index[split_rows]
    )
    preliminary_outcome_type = outcomes["outcome_type"]
    preliminary_permanent = preliminary_outcome_type.isin(EXIT_OUTCOMES)
    preliminary_exit_dates = _date_series(outcomes, "exit_effective_date")
    expected_exit_event_types = {
        "delisted": {"delisting"},
        "acquired_cash": {"merger_cash", "delisting"},
        "acquired_stock": {"merger_stock", "delisting"},
        "bankrupt": {"bankruptcy", "delisting"},
    }
    exit_action_matches = all(
        any(
            (str(outcomes.loc[index, "security_id"]), event_type, preliminary_exit_dates.loc[index])
            in action_effective_keys
            for event_type in expected_exit_event_types[str(outcomes.loc[index, "outcome_type"])]
        )
        for index in outcomes.index[preliminary_permanent]
        if pd.notna(preliminary_exit_dates.loc[index])
    ) and preliminary_exit_dates.loc[preliminary_permanent].notna().all()
    actions_ok = bool(
        actions["event_id"].ne("").all()
        and actions["event_id"].is_unique
        and actions["security_id"].isin(master_ids).all()
        and actions["event_type"].isin(EVENT_TYPES).all()
        and actions["source_record_id"].ne("").all()
        and action_dates.notna().all().all()
        and (action_dates["announced"] <= action_dates["effective"]).all()
        and action_terms_ok.all()
        and distribution_matches
        and split_matches
        and exit_action_matches
    )
    gates["14_corporate_actions"] = _gate(
        actions_ok,
        "公司行動事件唯一，時間及現金／換股條款可對數"
        if actions_ok
        else "公司行動 ID、日期、類型或經濟條款不完整",
        {
            "events": len(actions),
            "cash_distribution_rows": int(distribution_rows.sum()),
            "split_rows": int(split_rows.sum()),
            "permanent_exit_rows": int(preliminary_permanent.sum()),
        },
    )

    outcome_match = memberships[["source_record_id", "security_id", "effective_to"]].merge(
        outcomes[["source_record_id", "security_id", "membership_effective_to"]],
        on=["source_record_id", "security_id"],
        how="outer",
        indicator=True,
    )
    membership_to = outcome_match["effective_to"].fillna("")
    outcome_to = outcome_match["membership_effective_to"].fillna("")
    outcome_coverage_ok = bool(
        outcomes["source_record_id"].ne("").all()
        and outcomes["source_record_id"].is_unique
        and outcomes["security_id"].isin(master_ids).all()
        and outcomes["outcome_type"].isin(OUTCOME_TYPES).all()
        and len(outcome_match) == len(memberships) == len(outcomes)
        and outcome_match["_merge"].eq("both").all()
        and membership_to.eq(outcome_to).all()
    )
    gates["15_outcome_coverage"] = _gate(
        outcome_coverage_ok,
        "每段成分資格恰有一個對數結果"
        if outcome_coverage_ok
        else "membership 與 outcome 不是一對一或退出日不吻合",
        {"outcomes": len(outcomes), "membership_spells": len(memberships)},
    )

    outcome_type = outcomes["outcome_type"]
    permanent = outcome_type.isin(EXIT_OUTCOMES)
    still = outcome_type.eq("still_member")
    removed = outcome_type.eq("removed_continues")
    last_trade = _date_series(outcomes, "last_trade_date")
    exit_effective = _date_series(outcomes, "exit_effective_date")
    outcome_known = _utc_series(outcomes, "known_at").dt.tz_localize(None).dt.normalize()
    delisting_return = _number_series(outcomes, "delisting_return")
    cash_consideration = _number_series(outcomes, "cash_consideration")
    outcome_membership_to = _date_series(outcomes, "membership_effective_to")
    max_price_session = prices.assign(__session=price_sessions).groupby("security_id")[
        "__session"
    ].max()
    removed_continuation_ok = all(
        pd.notna(outcome_membership_to.loc[index])
        and pd.notna(max_price_session.get(outcomes.loc[index, "security_id"], pd.NaT))
        and max_price_session.get(outcomes.loc[index, "security_id"], pd.NaT)
        >= outcome_membership_to.loc[index]
        for index in outcomes.index[removed]
    )
    economic_terms = (
        delisting_return.notna()
        | cash_consideration.gt(0)
        | (
            outcome_type.eq("acquired_stock")
            & outcomes["successor_security_id"].ne("")
        )
    )
    permanent_economics_ok = bool(
        last_trade.loc[permanent].notna().all()
        and exit_effective.loc[permanent].notna().all()
        and outcome_known.loc[permanent].notna().all()
        and economic_terms.loc[permanent].all()
        and delisting_return.loc[delisting_return.notna()].ge(-1).all()
        and outcomes.loc[permanent, "reason_code"].ne("").all()
        and outcomes.loc[permanent, "membership_effective_to"].ne("").all()
        and (last_trade.loc[permanent] <= exit_effective.loc[permanent]).all()
        and outcomes.loc[still, "membership_effective_to"].eq("").all()
        and outcomes.loc[removed, "membership_effective_to"].ne("").all()
        and removed_continuation_ok
    )
    gates["16_permanent_exit_economics"] = _gate(
        permanent_economics_ok,
        "永久退出均有最後交易日及退市回報或可對數代價"
        if permanent_economics_ok
        else "至少一個永久退出缺最後交易日、原因或完整經濟回報",
        {"permanent_exits": int(permanent.sum())},
    )

    ghost_ids: list[str] = []
    for row_index, row in outcomes.loc[permanent].iterrows():
        maximum = max_price_session.get(row["security_id"], pd.NaT)
        if pd.notna(maximum) and pd.notna(last_trade.loc[row_index]) and maximum > last_trade.loc[row_index]:
            ghost_ids.append(str(row["security_id"]))
    no_ghosts = not ghost_ids
    gates["17_no_post_exit_prices"] = _gate(
        no_ghosts,
        "永久退出最後交易日後沒有觀察或前向填補價格"
        if no_ghosts
        else "永久退出後仍出現價格：" + ", ".join(ghost_ids[:5]),
        {"ghost_security_count": len(ghost_ids)},
    )

    class_start = _date_series(classifications, "effective_from")
    class_end = _end_dates(classifications, "effective_to")
    class_known = _utc_series(classifications, "known_at").dt.tz_localize(None).dt.normalize()
    class_base_ok = bool(
        len(classifications)
        and classifications["security_id"].isin(master_ids).all()
        and classifications[["scheme", "sector_code", "industry_code", "source_record_id"]]
        .ne("")
        .all()
        .all()
        and classifications["source_record_id"].is_unique
        and class_start.notna().all()
        and class_known.notna().all()
        and (class_known <= class_start).all()
        and (class_start < class_end).all()
        and _intervals_non_overlapping(classifications, groups=["security_id"])
    )
    class_by_security = {
        security_id: rows.index.to_list()
        for security_id, rows in classifications.groupby("security_id")
    }
    class_required = 0
    class_exact = 0
    if class_base_ok and membership_intervals_ok and len(fixed_sessions):
        for row_index, row in memberships.iterrows():
            active = fixed_sessions[
                (fixed_sessions >= membership_start.loc[row_index])
                & (fixed_sessions < membership_end.loc[row_index])
            ]
            class_required += len(active)
            coverage_counts = np.zeros(len(active), dtype=int)
            for class_index in class_by_security.get(row["security_id"], []):
                coverage_counts += (
                    (active >= class_start.loc[class_index])
                    & (active < class_end.loc[class_index])
                ).to_numpy(dtype=int)
            class_exact += int((coverage_counts == 1).sum())
    classification_ok = bool(
        class_base_ok and class_required and class_exact == class_required
    )
    gates["18_point_in_time_classifications"] = _gate(
        classification_ok,
        "每個在籍日恰有一個當時可知歷史分類"
        if classification_ok
        else "歷史分類缺失、重疊、事後才知或未完整覆蓋在籍日",
        {"required_observations": class_required, "exactly_one": class_exact},
    )

    duplicate_companies = set(master.loc[master["company_id"].duplicated(False), "company_id"])
    duplicate_master = master[master["company_id"].isin(duplicate_companies)]
    distinct_classes = not duplicate_master.duplicated(["company_id", "share_class"]).any()
    volume_capable = "volume" in prices and numeric_prices["volume"].notna().all()
    share_class_ok = bool(master["company_id"].ne("").all() and distinct_classes and volume_capable)
    gates["19_share_class_dedup_capability"] = _gate(
        share_class_ok,
        "公司與股份類別可按當時成交金額做唯一化"
        if share_class_ok
        else "同公司股份類別鍵重複或缺少可用成交量",
        {"multi_class_companies": len(duplicate_companies)},
    )

    next_session_available = len(fixed_sessions) >= 2
    execution_ok = bool(
        manifest.get("execution_clock") == MANIFEST_POLICY_VALUES["execution_clock"]
        and calendar_valid
        and next_session_available
        and {"open_raw", "close_raw"}.issubset(prices)
    )
    gates["20_execution_clock"] = _gate(
        execution_ok,
        "交易日及原始開收市價可強制 t 收市訊號、t+1 開市成交"
        if execution_ok
        else "manifest 或行情結構不能證明 D+1 無前視成交",
    )

    return _result(
        gates,
        bundle_present=True,
        bundle_name=bundle_path.name,
        provider=provider,
        as_of_date=as_of_date,
    )
