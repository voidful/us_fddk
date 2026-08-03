from __future__ import annotations

import hashlib
import json
import math
import re
import tempfile
from pathlib import Path
from typing import Any

import pandas as pd

from .point_in_time_ledger import MANIFEST_POLICY_VALUES, REQUIRED_COLUMNS

CIZ_ADAPTER_VERSION = "round13-crsp-ciz-v1"
CIZ_PROTOCOL_SHA256 = "0b0f9d97f18427a21df7def9002993464fcfde86856068e654e1e066ffdaac87"
CIZ_SOURCE_FILES = (
    "stk_security_info_hist.csv",
    "stk_ind_membership.csv",
    "stk_dly_security_data.csv",
    "stk_distributions.csv",
    "stk_delists.csv",
    "trading_calendar.csv",
    "security_info_availability.csv",
    "membership_announcements.csv",
    "corporate_action_overlay.csv",
    "exit_terms.csv",
)
CIZ_REQUIRED_COLUMNS: dict[str, tuple[str, ...]] = {
    "stk_security_info_hist.csv": (
        "PERMNO",
        "PERMCO",
        "SecInfoStartDt",
        "SecInfoEndDt",
        "Ticker",
        "PrimaryExch",
        "CUSIP",
        "ShareClass",
        "USIncFlg",
        "IssuerType",
        "SecurityType",
        "SecuritySubType",
        "ShareType",
        "SecurityActiveFlg",
        "SICCD",
        "NAICS",
        "ICBIndustry",
        "TradingStatusFlg",
    ),
    "stk_ind_membership.csv": (
        "PERMNO",
        "INDNO",
        "MbrStartDt",
        "MbrEndDt",
        "MbrFlg",
    ),
    "stk_dly_security_data.csv": (
        "PERMNO",
        "DlyCalDt",
        "DlyOpen",
        "DlyHigh",
        "DlyLow",
        "DlyClose",
        "DlyVol",
        "DlyRet",
        "DlyRetMissFlg",
        "DlyOrdDivAmt",
        "DlynonOrdDivAmt",
        "DlyFacPrc",
        "DlyDelFlg",
        "TradingStatusFlg",
    ),
    "stk_distributions.csv": (
        "PERMNO",
        "DisExDt",
        "DisSeqnbr",
        "DisType",
        "DisOrdinaryFlg",
        "DisDeclareDt",
        "DisPayDt",
        "DisDivAmt",
        "DisFacPr",
        "DisFacShr",
        "DisPERMNO",
    ),
    "stk_delists.csv": (
        "PERMNO",
        "DelistingDt",
        "DelDlyDt",
        "DelActionType",
        "DelStatusType",
        "DelReasonType",
        "DelPaymentType",
        "DelPERMNO",
        "DelPERMCO",
        "DelRet",
        "DelRetMissType",
        "DelDivAmt",
    ),
    "trading_calendar.csv": ("session", "exchange", "open_at", "close_at"),
    "security_info_availability.csv": (
        "PERMNO",
        "SecInfoStartDt",
        "SecInfoEndDt",
        "KnownAt",
        "EvidenceReference",
    ),
    "membership_announcements.csv": (
        "PERMNO",
        "INDNO",
        "MbrStartDt",
        "MbrEndDt",
        "AnnouncedAt",
        "EvidenceReference",
    ),
    "corporate_action_overlay.csv": (
        "SourceTable",
        "PERMNO",
        "EventDate",
        "Sequence",
        "EventType",
        "AnnouncedAt",
        "CashAmount",
        "ShareRatio",
        "SuccessorPERMNO",
        "EvidenceReference",
    ),
    "exit_terms.csv": (
        "PERMNO",
        "DelistingDt",
        "OutcomeType",
        "CashConsideration",
        "ShareRatio",
        "SuccessorPERMNO",
        "KnownAt",
        "EvidenceReference",
    ),
}

CIZ_MANIFEST_KEYS = {
    "schema_version",
    "source_format",
    "provider",
    "provider_product",
    "license_attestation",
    "exported_at",
    "first_imported_at",
    "as_of_date",
    "sp500_indno",
    "price_basis",
    "membership_date_semantics",
    "delist_storage_semantics",
    "adapter_version",
    "files",
}
LICENSE_KEYS = {
    "authorized_for_local_research",
    "raw_redistribution_allowed",
    "attested_at",
    "reference",
}
EXPLICIT_OFFSET_PATTERN = re.compile(r"(?:Z|[+-]\d{2}:\d{2})$")
ISO_DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
EXCHANGE_MAP = {"N": "XNYS", "Q": "XNAS"}
PERMANENT_OUTCOMES = {"delisted", "acquired_cash", "acquired_stock", "bankrupt"}
DISTRIBUTION_EVENT_TYPES = {"dividend", "split", "spinoff", "rights"}
DELIST_EVENT_TYPES = {"delisting", "merger_cash", "merger_stock", "bankruptcy"}


class CizMappingError(ValueError):
    """Fail-closed mapping error with a stable machine-readable code."""

    def __init__(self, code: str, detail: str):
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}")


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _fail(code: str, detail: str) -> None:
    raise CizMappingError(code, detail)


def _timestamp(value: object, field: str) -> pd.Timestamp:
    raw = str(value)
    if not EXPLICIT_OFFSET_PATTERN.search(raw):
        _fail("timestamp_without_offset", f"{field} 必須帶 UTC offset")
    parsed = pd.to_datetime(raw, utc=True, errors="coerce")
    if pd.isna(parsed):
        _fail("invalid_timestamp", f"{field} 不是有效時間")
    return parsed


def _date(value: object, field: str, *, allow_blank: bool = False) -> pd.Timestamp | None:
    raw = str(value).strip()
    if raw == "" and allow_blank:
        return None
    if ISO_DATE_PATTERN.fullmatch(raw) is None:
        _fail("invalid_date", f"{field} 必須是 YYYY-MM-DD")
    parsed = pd.to_datetime(raw, errors="coerce")
    if pd.isna(parsed):
        _fail("invalid_date", f"{field} 不是有效日期")
    return pd.Timestamp(parsed).normalize()


def _number(
    value: object,
    field: str,
    *,
    allow_blank: bool = False,
) -> float | None:
    raw = str(value).strip()
    if raw == "" and allow_blank:
        return None
    try:
        result = float(raw)
    except ValueError:
        _fail("invalid_number", f"{field} 不是數值")
    if not math.isfinite(result):
        _fail("invalid_number", f"{field} 必須是有限數值")
    return result


def _integer(value: object, field: str) -> int:
    parsed = _number(value, field)
    assert parsed is not None
    if parsed < 0 or not float(parsed).is_integer():
        _fail("invalid_integer", f"{field} 必須是非負整數")
    return int(parsed)


def _security_id(permno: object) -> str:
    raw = str(permno).strip()
    if not raw:
        _fail("missing_permno", "PERMNO 不可空白")
    return f"CRSP-PERMNO-{raw}"


def _company_id(permco: object) -> str:
    raw = str(permco).strip()
    if not raw:
        _fail("missing_permco", "PERMCO 不可空白")
    return f"CRSP-PERMCO-{raw}"


def _half_open_end(value: object, as_of: pd.Timestamp) -> str:
    parsed = _date(value, "inclusive end", allow_blank=True)
    if parsed is None or parsed >= as_of:
        return ""
    return str((parsed + pd.Timedelta(days=1)).date())


def _midnight_new_york_utc(day: pd.Timestamp) -> pd.Timestamp:
    return day.tz_localize("America/New_York").tz_convert("UTC")


def _read_csv(path: Path, name: str) -> pd.DataFrame:
    try:
        frame = pd.read_csv(path, dtype=str, keep_default_na=False, na_filter=False)
    except (OSError, pd.errors.ParserError) as exc:
        _fail("unreadable_source_file", f"{name}: {type(exc).__name__}")
    expected = set(CIZ_REQUIRED_COLUMNS[name])
    if set(frame.columns) != expected:
        _fail("source_schema_drift", f"{name} 欄位集合不符凍結 schema")
    return frame.loc[:, list(CIZ_REQUIRED_COLUMNS[name])]


def _manifest_and_tables(bundle: Path) -> tuple[dict[str, Any], dict[str, pd.DataFrame]]:
    expected_names = {"ciz_manifest.json", *CIZ_SOURCE_FILES}
    actual_names = {item.name for item in bundle.iterdir() if item.is_file()}
    if actual_names != expected_names:
        missing = sorted(expected_names - actual_names)
        extra = sorted(actual_names - expected_names)
        _fail("source_file_set_mismatch", f"missing={missing}; extra={extra}")
    try:
        manifest = json.loads((bundle / "ciz_manifest.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        _fail("invalid_source_manifest", type(exc).__name__)
    if not isinstance(manifest, dict) or set(manifest) != CIZ_MANIFEST_KEYS:
        _fail("source_schema_drift", "ciz_manifest keys 不符凍結 schema")
    tables = {name: _read_csv(bundle / name, name) for name in CIZ_SOURCE_FILES}
    return manifest, tables


def _validate_manifest(
    bundle: Path,
    manifest: dict[str, Any],
    tables: dict[str, pd.DataFrame],
) -> tuple[pd.Timestamp, pd.Timestamp, pd.Timestamp]:
    if manifest.get("schema_version") != 1 or manifest.get("source_format") != "CIZ_FF2":
        _fail("source_schema_drift", "只接受 schema 1 的 CIZ_FF2")
    if manifest.get("adapter_version") != CIZ_ADAPTER_VERSION:
        _fail("source_schema_drift", "adapter_version 不符凍結版本")
    if manifest.get("price_basis") != "raw_unadjusted_ohlc":
        _fail("adjusted_price_prohibited", "CIZ 輸入未證明為 raw unadjusted OHLC")
    if manifest.get("membership_date_semantics") != "inclusive_source_to_half_open_ledger":
        _fail("source_schema_drift", "membership date semantics 不符")
    if (
        manifest.get("delist_storage_semantics")
        != "DelistingDt_last_price_DelDlyDt_storage_only"
    ):
        _fail("source_schema_drift", "delist storage semantics 不符")
    if not str(manifest.get("provider", "")).strip() or not str(
        manifest.get("provider_product", "")
    ).strip():
        _fail("license_attestation_invalid", "供應商及產品不可空白")
    if not str(manifest.get("sp500_indno", "")).strip():
        _fail("source_schema_drift", "sp500_indno 不可空白")

    license_data = manifest.get("license_attestation")
    if not isinstance(license_data, dict) or set(license_data) != LICENSE_KEYS:
        _fail("license_attestation_invalid", "license_attestation 欄位不完整")
    if license_data.get("authorized_for_local_research") is not True:
        _fail("license_attestation_invalid", "未授權本地研究")
    if not isinstance(license_data.get("raw_redistribution_allowed"), bool):
        _fail("license_attestation_invalid", "再分發聲明必須是 boolean")
    if not str(license_data.get("reference", "")).strip():
        _fail("license_attestation_invalid", "授權 reference 不可空白")

    attested_at = _timestamp(license_data["attested_at"], "license attested_at")
    exported_at = _timestamp(manifest["exported_at"], "exported_at")
    first_imported_at = _timestamp(manifest["first_imported_at"], "first_imported_at")
    if exported_at > first_imported_at or attested_at > first_imported_at:
        _fail("timestamp_order_invalid", "匯出／授權時間不得晚於首次匯入")
    as_of = _date(manifest["as_of_date"], "as_of_date")
    assert as_of is not None

    receipts = manifest.get("files")
    if not isinstance(receipts, dict) or set(receipts) != set(CIZ_SOURCE_FILES):
        _fail("source_schema_drift", "manifest 檔案收據集合不符")
    for name in CIZ_SOURCE_FILES:
        receipt = receipts[name]
        if (
            not isinstance(receipt, dict)
            or set(receipt) != {"sha256", "rows"}
            or not isinstance(receipt.get("sha256"), str)
            or SHA256_PATTERN.fullmatch(receipt["sha256"]) is None
            or not isinstance(receipt.get("rows"), int)
            or isinstance(receipt.get("rows"), bool)
            or receipt["rows"] < 0
        ):
            _fail("source_receipt_invalid", f"{name} 收據格式錯誤")
        if receipt["sha256"] != _sha256_file(bundle / name) or receipt["rows"] != len(
            tables[name]
        ):
            _fail("source_receipt_invalid", f"{name} SHA-256 或列數不符")
    return as_of, exported_at, first_imported_at


def _protocol_integrity(root: Path, first_imported_at: pd.Timestamp) -> None:
    receipt_path = root / "artifacts/short_term_crsp_ciz_mapping_protocol_receipt.json"
    try:
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        tracked = (
            receipt["protocol"],
            receipt["point_in_time_contract"],
            receipt["manifest_schema"],
            receipt["strategy_protocol"],
            receipt["sample_acceptance_protocol"],
        )
        hashes_ok = all(_sha256_file(root / item["path"]) == item["sha256"] for item in tracked)
        frozen_at = _timestamp(receipt["frozen_at"], "round13 frozen_at")
        passed = bool(
            receipt["status"] == "frozen_before_ciz_adapter_implementation"
            and receipt["protocol"]["sha256"] == CIZ_PROTOCOL_SHA256
            and receipt["frozen_attack_count"] == 12
            and receipt["ciz_adapter_implemented_at_freeze"] is False
            and receipt["authorized_provider_sample_present_at_freeze"] is False
            and hashes_ok
            and first_imported_at > frozen_at
        )
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError):
        passed = False
    if not passed:
        _fail("protocol_integrity_failed", "Round 13 凍結收據、雜湊或首次匯入次序不符")


def _validate_security_history(
    security: pd.DataFrame,
    availability: pd.DataFrame,
    as_of: pd.Timestamp,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, set[str]]:
    keys = ["PERMNO", "SecInfoStartDt", "SecInfoEndDt"]
    if security.empty or security.duplicated(keys).any():
        _fail("security_history_invalid", "security info history 空白或 natural key 重複")
    if availability.duplicated(keys).any():
        _fail("security_info_availability_invalid", "availability natural key 重複")
    joined = security.merge(availability, on=keys, how="outer", indicator=True)
    if len(joined) != len(security) or not joined["_merge"].eq("both").all():
        _fail("security_info_availability_missing", "每段 security info 必須一對一提供 KnownAt")
    if joined["EvidenceReference"].eq("").any():
        _fail("security_info_availability_invalid", "security info evidence reference 不可空白")

    starts: list[pd.Timestamp] = []
    ends: list[pd.Timestamp | None] = []
    known: list[pd.Timestamp] = []
    for index, row in joined.iterrows():
        start = _date(row["SecInfoStartDt"], f"security[{index}] start")
        end = _date(row["SecInfoEndDt"], f"security[{index}] end", allow_blank=True)
        assert start is not None
        if end is not None and end < start:
            _fail("security_history_invalid", "SecInfoEndDt 早於 SecInfoStartDt")
        known_at = _timestamp(row["KnownAt"], f"security[{index}] KnownAt")
        if known_at > _midnight_new_york_utc(start):
            _fail("security_info_known_late", "security info 在生效後才可知")
        starts.append(start)
        ends.append(end)
        known.append(known_at)
    joined["__start"] = starts
    joined["__end"] = ends
    joined["__known"] = known

    eligible = (
        joined["USIncFlg"].eq("Y")
        & joined["SecurityType"].eq("EQTY")
        & joined["SecuritySubType"].eq("COM")
        & joined["ShareType"].eq("NS")
    )
    if not eligible.all():
        _fail("security_universe_invalid", "只接受美國註冊普通股 CIZ history")
    if not joined["PrimaryExch"].isin(EXCHANGE_MAP).all():
        _fail("security_universe_invalid", "PrimaryExch 不是固定 XNYS／XNAS 映射")
    if joined[["PERMNO", "PERMCO", "Ticker", "CUSIP", "ICBIndustry"]].eq("").any().any():
        _fail("security_history_invalid", "永久 ID、歷史代號、CUSIP 或 ICB 不可空白")

    signature_columns = [
        "PERMCO",
        "Ticker",
        "PrimaryExch",
        "CUSIP",
        "ShareClass",
        "USIncFlg",
        "IssuerType",
        "SecurityType",
        "SecuritySubType",
        "ShareType",
        "SICCD",
        "NAICS",
        "ICBIndustry",
    ]
    for _, rows in joined.sort_values(["PERMNO", "__start"]).groupby("PERMNO"):
        if len(rows) > 1 and rows[signature_columns].duplicated().any():
            _fail(
                "current_security_info_backfill",
                "同一 PERMNO 出現完全相同的連續歷史列，拒絕 current-row backfill",
            )
        previous_end: pd.Timestamp | None = None
        company_ids = set(rows["PERMCO"])
        if len(company_ids) != 1:
            _fail("security_history_invalid", "同一 PERMNO 的 PERMCO 漂移")
        for _, row in rows.iterrows():
            start = row["__start"]
            end = row["__end"]
            if previous_end is not None and start <= previous_end:
                _fail("security_history_invalid", "同一 PERMNO 的 inclusive history 重疊")
            previous_end = end

    identifiers: list[dict[str, object]] = []
    classifications: list[dict[str, object]] = []
    for row in joined.itertuples(index=False):
        effective_to = _half_open_end(row.SecInfoEndDt, as_of)
        source_id = f"CIZ-SECINFO-{row.PERMNO}-{row.SecInfoStartDt}-{row.SecInfoEndDt or 'OPEN'}"
        identifiers.append(
            {
                "security_id": _security_id(row.PERMNO),
                "ticker": row.Ticker,
                "exchange": EXCHANGE_MAP[row.PrimaryExch],
                "cusip": row.CUSIP,
                "isin": "",
                "effective_from": row.SecInfoStartDt,
                "effective_to": effective_to,
                "known_at": str(row.KnownAt),
            }
        )
        classifications.append(
            {
                "security_id": _security_id(row.PERMNO),
                "scheme": "ICB",
                "sector_code": str(row.ICBIndustry)[:2],
                "industry_code": row.ICBIndustry,
                "effective_from": row.SecInfoStartDt,
                "effective_to": effective_to,
                "known_at": str(row.KnownAt),
                "source_record_id": source_id,
            }
        )

    masters: list[dict[str, object]] = []
    for permno, rows in joined.sort_values("__start").groupby("PERMNO"):
        latest = rows.iloc[-1]
        share_class = str(latest["ShareClass"]).strip()
        if share_class in {"", "NONE"}:
            share_class = "single"
        masters.append(
            {
                "security_id": _security_id(permno),
                "company_id": _company_id(latest["PERMCO"]),
                "security_type": "common_stock",
                "share_class": share_class,
                "country_of_incorporation": "US",
                "currency": "USD",
            }
        )
    master = pd.DataFrame(masters, columns=REQUIRED_COLUMNS["security_master.csv"])
    identifiers_frame = pd.DataFrame(
        identifiers, columns=REQUIRED_COLUMNS["identifier_history.csv"]
    )
    classifications_frame = pd.DataFrame(
        classifications, columns=REQUIRED_COLUMNS["classification_history.csv"]
    )
    return master, identifiers_frame, classifications_frame, set(joined["PERMNO"])


def _validate_memberships(
    membership: pd.DataFrame,
    announcements: pd.DataFrame,
    *,
    sp500_indno: str,
    as_of: pd.Timestamp,
    permnos: set[str],
) -> pd.DataFrame:
    keys = ["PERMNO", "INDNO", "MbrStartDt", "MbrEndDt"]
    if membership.empty or membership.duplicated(keys).any():
        _fail("membership_history_invalid", "membership 空白或 natural key 重複")
    if announcements.duplicated(keys).any():
        _fail("membership_announcement_invalid", "announcement natural key 重複")
    joined = membership.merge(announcements, on=keys, how="outer", indicator=True)
    if len(joined) != len(membership) or not joined["_merge"].eq("both").all():
        _fail("membership_announcement_missing", "每段 membership 必須一對一提供 announced_at")
    if not joined["INDNO"].eq(sp500_indno).all():
        _fail("membership_history_invalid", "INDNO 不等於 manifest 的 S&P 500 index")
    if not joined["PERMNO"].isin(permnos).all():
        _fail("membership_history_invalid", "membership PERMNO 不在普通股 master")
    if joined["EvidenceReference"].eq("").any():
        _fail("membership_announcement_invalid", "membership evidence reference 不可空白")

    output: list[dict[str, object]] = []
    for index, row in joined.iterrows():
        start = _date(row["MbrStartDt"], f"membership[{index}] start")
        end = _date(row["MbrEndDt"], f"membership[{index}] end", allow_blank=True)
        assert start is not None
        if end is not None and end < start:
            _fail("membership_history_invalid", "MbrEndDt 早於 MbrStartDt")
        announced_at = _timestamp(row["AnnouncedAt"], f"membership[{index}] AnnouncedAt")
        if announced_at >= _midnight_new_york_utc(start):
            _fail(
                "membership_effective_date_substitution",
                "AnnouncedAt 必須有證據且嚴格早於 MbrStartDt 紐約午夜",
            )
        source_id = (
            f"CIZ-MBR-{row['PERMNO']}-{row['INDNO']}-{row['MbrStartDt']}-"
            f"{row['MbrEndDt'] or 'OPEN'}"
        )
        output.append(
            {
                "index_id": "SP500",
                "security_id": _security_id(row["PERMNO"]),
                "effective_from": row["MbrStartDt"],
                "effective_to": _half_open_end(row["MbrEndDt"], as_of),
                "announced_at": row["AnnouncedAt"],
                "source_record_id": source_id,
            }
        )
    return pd.DataFrame(output, columns=REQUIRED_COLUMNS["membership_history.csv"])


def _overlay_key(source_table: str, permno: str, event_date: str, sequence: str) -> tuple[str, str, str, str]:
    return source_table, permno, event_date, sequence


def _validate_action_overlay(
    overlay: pd.DataFrame,
) -> dict[tuple[str, str, str, str], pd.Series]:
    keys = ["SourceTable", "PERMNO", "EventDate", "Sequence"]
    if overlay.duplicated(keys).any():
        _fail("corporate_action_overlay_invalid", "corporate action overlay natural key 重複")
    result: dict[tuple[str, str, str, str], pd.Series] = {}
    for index, row in overlay.iterrows():
        source_table = str(row["SourceTable"])
        if source_table not in {"StkDistributions", "StkDelists"}:
            _fail("corporate_action_overlay_invalid", "SourceTable 不合資格")
        event_date = _date(row["EventDate"], f"overlay[{index}] EventDate")
        assert event_date is not None
        announced = _timestamp(row["AnnouncedAt"], f"overlay[{index}] AnnouncedAt")
        if announced > _midnight_new_york_utc(event_date):
            _fail("corporate_action_overlay_invalid", "公司行動在事件生效後才可知")
        if not str(row["EvidenceReference"]).strip():
            _fail("corporate_action_overlay_invalid", "公司行動 evidence reference 不可空白")
        key = _overlay_key(source_table, row["PERMNO"], row["EventDate"], row["Sequence"])
        result[key] = row
    return result


def _transform_distributions(
    distributions: pd.DataFrame,
    overlay_map: dict[tuple[str, str, str, str], pd.Series],
    permnos: set[str],
) -> tuple[list[dict[str, object]], dict[tuple[str, str], float], dict[tuple[str, str], float]]:
    events: list[dict[str, object]] = []
    cash_by_day: dict[tuple[str, str], float] = {}
    split_by_day: dict[tuple[str, str], float] = {}
    expected_keys: set[tuple[str, str, str, str]] = set()
    for index, row in distributions.iterrows():
        if row["PERMNO"] not in permnos:
            _fail("distribution_invalid", "distribution PERMNO 不在 master")
        ex_date = _date(row["DisExDt"], f"distribution[{index}] DisExDt")
        declare_date = _date(
            row["DisDeclareDt"], f"distribution[{index}] DisDeclareDt", allow_blank=True
        )
        assert ex_date is not None
        if declare_date is not None and declare_date > ex_date:
            _fail("distribution_invalid", "DisDeclareDt 晚於 DisExDt")
        key = _overlay_key(
            "StkDistributions", row["PERMNO"], row["DisExDt"], row["DisSeqnbr"]
        )
        expected_keys.add(key)
        if key not in overlay_map:
            _fail(
                "distribution_overlay_missing",
                "distribution 缺少公告時間及正規化事件 overlay",
            )
        overlay = overlay_map[key]
        event_type = str(overlay["EventType"])
        if event_type not in DISTRIBUTION_EVENT_TYPES:
            _fail("distribution_invalid", "distribution EventType 不合資格")
        cash = _number(overlay["CashAmount"], "distribution CashAmount", allow_blank=True) or 0.0
        ratio = _number(overlay["ShareRatio"], "distribution ShareRatio", allow_blank=True) or 0.0
        successor = str(overlay["SuccessorPERMNO"]).strip()
        source_cash = _number(row["DisDivAmt"], "DisDivAmt", allow_blank=True) or 0.0
        if event_type == "dividend" and (cash <= 0 or not math.isclose(cash, source_cash)):
            _fail("distribution_terms_mismatch", "dividend 金額未與 CIZ DisDivAmt 對數")
        if event_type == "split" and ratio <= 0:
            _fail("distribution_terms_mismatch", "split 缺少正股比率")
        if event_type == "spinoff" and (ratio <= 0 or successor not in permnos):
            _fail("distribution_terms_mismatch", "spinoff successor 或比率不完整")
        if successor and successor not in permnos:
            _fail("unknown_successor_permno", "distribution successor 不在 master")
        day_key = (row["PERMNO"], row["DisExDt"])
        if event_type == "dividend":
            cash_by_day[day_key] = cash_by_day.get(day_key, 0.0) + cash
        if event_type == "split":
            split_by_day[day_key] = split_by_day.get(day_key, 1.0) * ratio
        source_id = f"CIZ-DIST-{row['PERMNO']}-{row['DisExDt']}-{row['DisSeqnbr']}"
        events.append(
            {
                "event_id": source_id,
                "security_id": _security_id(row["PERMNO"]),
                "event_type": event_type,
                "announced_at": overlay["AnnouncedAt"],
                "ex_date": row["DisExDt"],
                "effective_date": row["DisExDt"],
                "cash_amount": cash,
                "share_ratio": ratio,
                "successor_security_id": _security_id(successor) if successor else "",
                "source_record_id": source_id,
            }
        )
    overlay_distribution_keys = {key for key in overlay_map if key[0] == "StkDistributions"}
    if overlay_distribution_keys != expected_keys:
        _fail("corporate_action_overlay_invalid", "distribution overlay 含孤立或缺失記錄")
    return events, cash_by_day, split_by_day


def _validate_delists(
    delists: pd.DataFrame,
    exit_terms: pd.DataFrame,
    overlay_map: dict[tuple[str, str, str, str], pd.Series],
    *,
    permnos: set[str],
    calendar_sessions: list[pd.Timestamp],
) -> tuple[list[dict[str, object]], dict[tuple[str, str], dict[str, object]]]:
    keys = ["PERMNO", "DelistingDt"]
    if delists.duplicated(keys).any() or exit_terms.duplicated(keys).any():
        _fail("delist_invalid", "delist／exit terms natural key 重複")
    joined = delists.merge(exit_terms, on=keys, how="outer", indicator=True)
    if len(joined) != len(delists) or not joined["_merge"].eq("both").all():
        _fail("exit_terms_missing", "每個 delist 必須一對一提供 exit terms")
    if joined["EvidenceReference"].eq("").any():
        _fail("exit_terms_missing", "exit terms evidence reference 不可空白")

    events: list[dict[str, object]] = []
    records: dict[tuple[str, str], dict[str, object]] = {}
    expected_overlay_keys: set[tuple[str, str, str, str]] = set()
    calendar_index = pd.DatetimeIndex(calendar_sessions)
    for index, row in joined.iterrows():
        if row["PERMNO"] not in permnos:
            _fail("delist_invalid", "delist PERMNO 不在 master")
        last_trade = _date(row["DelistingDt"], f"delist[{index}] DelistingDt")
        storage_day = _date(row["DelDlyDt"], f"delist[{index}] DelDlyDt")
        assert last_trade is not None and storage_day is not None
        later_sessions = calendar_index[calendar_index > last_trade]
        if storage_day <= last_trade or not len(later_sessions) or storage_day != later_sessions[0]:
            _fail(
                "delist_storage_date_invalid",
                "DelDlyDt 必須是 DelistingDt 後的下一正式交易日且只作儲存日",
            )
        key = _overlay_key("StkDelists", row["PERMNO"], row["DelistingDt"], "0")
        expected_overlay_keys.add(key)
        if key not in overlay_map:
            _fail("delist_overlay_missing", "delist 缺少公司行動 announcement overlay")
        overlay = overlay_map[key]
        event_type = str(overlay["EventType"])
        if event_type not in DELIST_EVENT_TYPES:
            _fail("delist_invalid", "delist EventType 不合資格")

        outcome_type = str(row["OutcomeType"])
        if outcome_type not in PERMANENT_OUTCOMES:
            _fail("delist_invalid", "OutcomeType 不合資格")
        expected_event = {
            "delisted": {"delisting"},
            "acquired_cash": {"merger_cash", "delisting"},
            "acquired_stock": {"merger_stock", "delisting"},
            "bankrupt": {"bankruptcy", "delisting"},
        }[outcome_type]
        if event_type not in expected_event:
            _fail("delist_invalid", "OutcomeType 與 EventType 不一致")

        delisting_return = _number(row["DelRet"], "DelRet", allow_blank=True)
        if delisting_return is not None and delisting_return < -1:
            _fail("delist_invalid", "DelRet 不可低於 -1")
        cash = _number(row["CashConsideration"], "CashConsideration", allow_blank=True)
        share_ratio = _number(row["ShareRatio"], "exit ShareRatio", allow_blank=True)
        successor = str(row["SuccessorPERMNO"]).strip()
        if successor and successor not in permnos:
            _fail("unknown_successor_permno", "exit successor PERMNO 不在 master")
        if delisting_return is None:
            cash_ok = cash is not None and cash > 0
            stock_ok = (
                outcome_type == "acquired_stock"
                and successor in permnos
                and share_ratio is not None
                and share_ratio > 0
            )
            if not (cash_ok or stock_ok):
                _fail(
                    "missing_exit_economics",
                    "DelRet 缺失時必須有可追溯現金或換股代價，不得填 0",
                )
        known_at = _timestamp(row["KnownAt"], f"delist[{index}] KnownAt")
        effective = str((last_trade + pd.Timedelta(days=1)).date())
        source_id = f"CIZ-DELIST-{row['PERMNO']}-{row['DelistingDt']}"
        events.append(
            {
                "event_id": source_id,
                "security_id": _security_id(row["PERMNO"]),
                "event_type": event_type,
                "announced_at": overlay["AnnouncedAt"],
                "ex_date": effective,
                "effective_date": effective,
                "cash_amount": cash or 0.0,
                "share_ratio": share_ratio or 0.0,
                "successor_security_id": _security_id(successor) if successor else "",
                "source_record_id": source_id,
            }
        )
        records[(row["PERMNO"], row["DelistingDt"])] = {
            "outcome_type": outcome_type,
            "last_trade_date": row["DelistingDt"],
            "exit_effective_date": effective,
            "delisting_return": "" if delisting_return is None else delisting_return,
            "cash_consideration": "" if cash is None else cash,
            "successor_security_id": _security_id(successor) if successor else "",
            "reason_code": row["DelReasonType"] or row["DelActionType"] or "CIZ_DELIST",
            "known_at": str(row["KnownAt"]),
            "storage_date": str(storage_day.date()),
            "known_at_utc": known_at,
        }
    overlay_delist_keys = {key for key in overlay_map if key[0] == "StkDelists"}
    if overlay_delist_keys != expected_overlay_keys:
        _fail("corporate_action_overlay_invalid", "delist overlay 含孤立或缺失記錄")
    return events, records


def _transform_daily_prices(
    daily: pd.DataFrame,
    *,
    permnos: set[str],
    calendar_days: set[str],
    cash_by_day: dict[tuple[str, str], float],
    split_by_day: dict[tuple[str, str], float],
    delist_records: dict[tuple[str, str], dict[str, object]],
) -> pd.DataFrame:
    if daily.empty or daily.duplicated(["PERMNO", "DlyCalDt"]).any():
        _fail("daily_data_invalid", "daily data 空白或 natural key 重複")
    rows: list[dict[str, object]] = []
    seen_storage: set[tuple[str, str]] = set()
    delist_by_storage = {
        (permno, str(record["storage_date"])): (last_trade, record)
        for (permno, last_trade), record in delist_records.items()
    }
    for index, row in daily.iterrows():
        permno = row["PERMNO"]
        day = row["DlyCalDt"]
        if permno not in permnos or day not in calendar_days:
            _fail("daily_data_invalid", "daily PERMNO 或交易日不在固定 master／calendar")
        _date(day, f"daily[{index}] DlyCalDt")
        if row["DlyDelFlg"] == "Y":
            storage_key = (permno, day)
            if storage_key not in delist_by_storage:
                _fail("delist_storage_date_invalid", "DlyDelFlg 沒有對應 DelDlyDt")
            last_trade, record = delist_by_storage[storage_key]
            source_delret = record["delisting_return"]
            daily_return = _number(row["DlyRet"], "DlyRet", allow_blank=True)
            if source_delret == "":
                if daily_return is not None or row["DlyRetMissFlg"] in {"NA", "N"}:
                    _fail("delist_return_mismatch", "缺失 DelRet 的 storage row 旗標不一致")
            elif (
                daily_return is None
                or row["DlyRetMissFlg"] not in {"NA", "N"}
                or not math.isclose(float(source_delret), daily_return)
            ):
                _fail("delist_return_mismatch", "DlyRet 與 StkDelists DelRet 不一致")
            if any(str(row[column]).strip() for column in ("DlyOpen", "DlyHigh", "DlyLow", "DlyClose")):
                _fail("delist_storage_date_invalid", "DelDlyDt return-only row 不可冒充交易價格")
            seen_storage.add((permno, last_trade))
            continue
        if row["DlyDelFlg"] not in {"N", ""}:
            _fail("daily_data_invalid", "DlyDelFlg 不合資格")
        daily_return = _number(row["DlyRet"], "DlyRet", allow_blank=True)
        if daily_return is None or row["DlyRetMissFlg"] not in {"NA", "N"}:
            _fail("daily_return_missing", "DlyRet 缺失或 missing flag 非 NA；不得填 0／1")
        if daily_return < -1:
            _fail("daily_data_invalid", "DlyRet 不可低於 -1")

        status = row["TradingStatusFlg"]
        if status in {"S", "H"}:
            source_status = "suspended"
            if any(str(row[column]).strip() for column in ("DlyOpen", "DlyHigh", "DlyLow", "DlyClose")):
                _fail("daily_data_invalid", "停牌列不可含 OHLC")
            volume = _integer(row["DlyVol"], "DlyVol")
            if volume != 0:
                _fail("daily_data_invalid", "停牌列成交量必須為 0")
            open_raw = high_raw = low_raw = close_raw = ""
        elif status == "A":
            source_status = "observed"
            values = [
                _number(row[column], column)
                for column in ("DlyOpen", "DlyHigh", "DlyLow", "DlyClose")
            ]
            if any(value is None or value <= 0 for value in values):
                _fail("daily_data_invalid", "active row 必須有正 raw OHLC")
            open_raw, high_raw, low_raw, close_raw = values
            volume = _integer(row["DlyVol"], "DlyVol")
        else:
            _fail("daily_data_invalid", "TradingStatusFlg 只接受 A／S／H")

        cash = cash_by_day.get((permno, day), 0.0)
        source_cash = _number(row["DlyOrdDivAmt"], "DlyOrdDivAmt", allow_blank=True) or 0.0
        if not math.isclose(cash, source_cash):
            _fail("distribution_terms_mismatch", "日線 ordinary dividend 未與 distribution overlay 對數")
        nonordinary = _number(
            row["DlynonOrdDivAmt"], "DlynonOrdDivAmt", allow_blank=True
        ) or 0.0
        if nonordinary and (permno, day) not in cash_by_day and (permno, day) not in split_by_day:
            _fail("distribution_overlay_missing", "non-ordinary distribution 缺正規化 overlay")
        rows.append(
            {
                "security_id": _security_id(permno),
                "session": day,
                "open_raw": open_raw,
                "high_raw": high_raw,
                "low_raw": low_raw,
                "close_raw": close_raw,
                "volume": volume,
                "cash_distribution": cash,
                "split_factor": split_by_day.get((permno, day), 1.0),
                "total_return_factor": 1.0 + daily_return,
                "source_status": source_status,
            }
        )
    if seen_storage != set(delist_records):
        _fail("delist_storage_date_invalid", "每個 StkDelists 必須有一個 DlyDelFlg storage row")
    return pd.DataFrame(rows, columns=REQUIRED_COLUMNS["daily_prices.csv"])


def _build_outcomes(
    memberships: pd.DataFrame,
    prices: pd.DataFrame,
    delist_records: dict[tuple[str, str], dict[str, object]],
    exported_at: pd.Timestamp,
) -> pd.DataFrame:
    delist_security_ids = [_security_id(permno) for permno, _ in delist_records]
    if len(delist_security_ids) != len(set(delist_security_ids)):
        _fail(
            "multiple_delists_unsupported",
            "同一 PERMNO 多次退市／重返交易尚未有凍結映射；拒絕靜默覆寫",
        )
    delist_by_security = {
        _security_id(permno): record for (permno, _), record in delist_records.items()
    }
    max_price = prices.groupby("security_id")["session"].max().to_dict()
    rows: list[dict[str, object]] = []
    used_delists: set[str] = set()
    for row in memberships.itertuples(index=False):
        record = delist_by_security.get(row.security_id)
        if record is not None and row.effective_to == record["exit_effective_date"]:
            used_delists.add(row.security_id)
            rows.append(
                {
                    "source_record_id": row.source_record_id,
                    "security_id": row.security_id,
                    "membership_effective_to": row.effective_to,
                    "outcome_type": record["outcome_type"],
                    "last_trade_date": record["last_trade_date"],
                    "exit_effective_date": record["exit_effective_date"],
                    "delisting_return": record["delisting_return"],
                    "cash_consideration": record["cash_consideration"],
                    "successor_security_id": record["successor_security_id"],
                    "reason_code": record["reason_code"],
                    "known_at": record["known_at"],
                }
            )
        elif row.effective_to == "":
            rows.append(
                {
                    "source_record_id": row.source_record_id,
                    "security_id": row.security_id,
                    "membership_effective_to": "",
                    "outcome_type": "still_member",
                    "last_trade_date": "",
                    "exit_effective_date": "",
                    "delisting_return": "",
                    "cash_consideration": "",
                    "successor_security_id": "",
                    "reason_code": "",
                    "known_at": exported_at.isoformat().replace("+00:00", "Z"),
                }
            )
        else:
            if max_price.get(row.security_id, "") < row.effective_to:
                _fail("removed_continuation_unproven", "移除後沒有後續行情證明仍交易")
            rows.append(
                {
                    "source_record_id": row.source_record_id,
                    "security_id": row.security_id,
                    "membership_effective_to": row.effective_to,
                    "outcome_type": "removed_continues",
                    "last_trade_date": "",
                    "exit_effective_date": "",
                    "delisting_return": "",
                    "cash_consideration": "",
                    "successor_security_id": "",
                    "reason_code": "",
                    "known_at": exported_at.isoformat().replace("+00:00", "Z"),
                }
            )
    if used_delists != set(delist_by_security):
        _fail("delist_membership_mismatch", "delist 未與唯一 membership half-open end 對數")
    return pd.DataFrame(rows, columns=REQUIRED_COLUMNS["security_outcomes.csv"])


def _write_ledger_bundle(
    output_bundle: Path,
    *,
    manifest: dict[str, Any],
    tables: dict[str, pd.DataFrame],
    exported_at: pd.Timestamp,
    first_imported_at: pd.Timestamp,
) -> None:
    output_bundle.parent.mkdir(parents=True, exist_ok=True)
    if output_bundle.exists():
        _fail("output_exists", "輸出目錄已存在；拒絕覆寫")
    with tempfile.TemporaryDirectory(
        prefix=f".{output_bundle.name}-", dir=output_bundle.parent
    ) as temporary:
        staging = Path(temporary) / output_bundle.name
        staging.mkdir()
        receipts: dict[str, dict[str, object]] = {}
        for name, frame in tables.items():
            path = staging / name
            frame.to_csv(path, index=False, lineterminator="\n")
            receipts[name] = {"sha256": _sha256_file(path), "rows": len(frame)}
        ledger_manifest = {
            "schema_version": 1,
            "provider": manifest["provider"],
            "provider_product": manifest["provider_product"],
            "license_attestation": manifest["license_attestation"],
            "exported_at": exported_at.isoformat().replace("+00:00", "Z"),
            "first_imported_at": first_imported_at.isoformat().replace("+00:00", "Z"),
            "as_of_date": manifest["as_of_date"],
            "currency": "USD",
            "timezone": "America/New_York",
            **MANIFEST_POLICY_VALUES,
            "transform_version": CIZ_ADAPTER_VERSION,
            "files": receipts,
        }
        (staging / "manifest.json").write_text(
            json.dumps(ledger_manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        staging.rename(output_bundle)


def transform_crsp_ciz_bundle(
    input_bundle: str | Path,
    output_bundle: str | Path,
    *,
    root: str | Path,
) -> dict[str, Any]:
    """Map one authorized local CRSP CIZ export into the frozen eight-ledger bundle.

    The adapter deliberately requires evidence overlays for timestamps and exit terms
    that are not documented in the public CIZ table definitions. It never queries WRDS.
    """

    source = Path(input_bundle)
    destination = Path(output_bundle)
    if not source.is_dir():
        _fail("source_bundle_missing", "CIZ 本地輸入目錄不存在")
    manifest, source_tables = _manifest_and_tables(source)
    as_of, exported_at, first_imported_at = _validate_manifest(
        source, manifest, source_tables
    )
    _protocol_integrity(Path(root), first_imported_at)

    calendar = source_tables["trading_calendar.csv"].copy()
    if calendar.empty or calendar.duplicated(["session"]).any():
        _fail("calendar_invalid", "交易日曆空白或 session 重複")
    calendar_dates = [_date(day, "calendar session") for day in calendar["session"]]
    if any(day is None for day in calendar_dates):
        _fail("calendar_invalid", "交易日曆日期無效")
    parsed_calendar = [day for day in calendar_dates if day is not None]
    if parsed_calendar != sorted(parsed_calendar):
        _fail("calendar_invalid", "交易日曆必須嚴格遞增")
    if parsed_calendar[-1] != as_of:
        _fail("calendar_invalid", "as_of_date 必須等於交易日曆最後一日")
    if not calendar["exchange"].isin({"XNYS", "XNAS"}).all():
        _fail("calendar_invalid", "交易日曆只接受 XNYS／XNAS")
    for index, row in calendar.iterrows():
        if _timestamp(row["open_at"], f"calendar[{index}] open") >= _timestamp(
            row["close_at"], f"calendar[{index}] close"
        ):
            _fail("calendar_invalid", "開市時間必須早於收市")

    master, identifiers, classifications, permnos = _validate_security_history(
        source_tables["stk_security_info_hist.csv"],
        source_tables["security_info_availability.csv"],
        as_of,
    )
    memberships = _validate_memberships(
        source_tables["stk_ind_membership.csv"],
        source_tables["membership_announcements.csv"],
        sp500_indno=str(manifest["sp500_indno"]),
        as_of=as_of,
        permnos=permnos,
    )
    overlay_map = _validate_action_overlay(source_tables["corporate_action_overlay.csv"])
    distribution_events, cash_by_day, split_by_day = _transform_distributions(
        source_tables["stk_distributions.csv"], overlay_map, permnos
    )
    delist_events, delist_records = _validate_delists(
        source_tables["stk_delists.csv"],
        source_tables["exit_terms.csv"],
        overlay_map,
        permnos=permnos,
        calendar_sessions=parsed_calendar,
    )
    prices = _transform_daily_prices(
        source_tables["stk_dly_security_data.csv"],
        permnos=permnos,
        calendar_days=set(calendar["session"]),
        cash_by_day=cash_by_day,
        split_by_day=split_by_day,
        delist_records=delist_records,
    )
    outcomes = _build_outcomes(memberships, prices, delist_records, exported_at)
    actions = pd.DataFrame(
        [*distribution_events, *delist_events],
        columns=REQUIRED_COLUMNS["corporate_actions.csv"],
    )
    ledger_tables = {
        "security_master.csv": master,
        "identifier_history.csv": identifiers,
        "membership_history.csv": memberships,
        "trading_calendar.csv": calendar.loc[
            :, list(REQUIRED_COLUMNS["trading_calendar.csv"])
        ],
        "daily_prices.csv": prices,
        "corporate_actions.csv": actions,
        "classification_history.csv": classifications,
        "security_outcomes.csv": outcomes,
    }
    _write_ledger_bundle(
        destination,
        manifest=manifest,
        tables=ledger_tables,
        exported_at=exported_at,
        first_imported_at=first_imported_at,
    )
    return {
        "status": "ciz_mapping_completed_ledger_audit_required",
        "source_format": "CIZ_FF2",
        "adapter_version": CIZ_ADAPTER_VERSION,
        "source_rows": {name: len(frame) for name, frame in source_tables.items()},
        "ledger_rows": {name: len(frame) for name, frame in ledger_tables.items()},
        "announcement_timestamps_inferred": False,
        "effective_dates_used_as_announcements": False,
        "adjusted_prices_used_as_raw": False,
        "missing_delisting_returns_imputed": False,
        "delisting_storage_dates_used_as_exit_dates": False,
        "wrds_queried": False,
        "provider_rows_published": False,
    }
