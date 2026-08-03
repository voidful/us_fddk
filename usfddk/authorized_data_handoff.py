from __future__ import annotations

import copy
import hashlib
import json
import math
import re
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any

from .ciz_execution_extension import BENCHMARK_COLUMNS
from .crsp_ciz_adapter import CIZ_ADAPTER_VERSION, CIZ_REQUIRED_COLUMNS, CIZ_SOURCE_FILES

HANDOFF_VERSION = "round16-authorized-data-handoff-v1"
HANDOFF_REQUEST_ID = "usfddk-round16-crsp-wrds-ciz-v1"
HANDOFF_PROTOCOL_SHA256 = (
    "4cd6da3541243573ab3a0113eebd26b581831ad31765b4fdc0a82c998703e754"
)
HANDOFF_SCHEMA_PATH = "schemas/short_term_authorized_data_response.schema.json"
HANDOFF_RECEIPT_PATH = (
    "artifacts/short_term_authorized_data_handoff_protocol_receipt.json"
)
EXPECTED_TRUE_READINESS = {"passed": 1, "total": 20, "all_passed": False}
EXPLICIT_OFFSET_PATTERN = re.compile(r"(?:Z|[+-]\d{2}:\d{2})$")
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
FORMAL_START = "2006-08-01"
FORMAL_END = "2026-07-31"
BUFFER_START = "2005-07-01"
NEXT_EXECUTION_SESSION = "2026-08-03"

RESPONSE_KEYS = {
    "schema_version",
    "status",
    "request_id",
    "request_protocol_sha256",
    "provider",
    "provider_product",
    "product_reference",
    "responded_at",
    "source_format",
    "wrds_mapping",
    "license_attestation",
    "coverage",
    "file_capabilities",
    "membership_semantics",
    "security_history",
    "market_actions",
    "exit_economics",
    "benchmark_delivery",
    "delivery",
    "declaration",
}
NESTED_KEYS = {
    "wrds_mapping": {"status", "schema_candidates", "reference"},
    "license_attestation": {
        "authorized_for_local_research",
        "raw_redistribution_allowed",
        "attested_at",
        "reference",
    },
    "coverage": {
        "buffer_start",
        "formal_start",
        "formal_end",
        "next_execution_session",
        "minimum_pre_signal_sessions",
    },
    "membership_semantics": {
        "sp500_index_identifier",
        "effective_dates_available",
        "announcement_status",
        "point_in_time_supported",
        "reference",
    },
    "security_history": {
        "permno",
        "permco",
        "historical_ticker",
        "share_class",
        "primary_exchange",
        "historical_classification",
        "known_at_status",
        "reference",
    },
    "market_actions": {
        "raw_ohlcv",
        "daily_return",
        "return_missing_flags",
        "trading_status",
        "distribution_ex_date",
        "distribution_pay_date",
        "price_share_factors",
        "reference",
    },
    "exit_economics": {
        "delisting_return",
        "missing_reason",
        "missing_delret_count",
        "missing_delret_fraction",
        "cash_consideration_status",
        "stock_consideration_status",
        "successor_identifiers",
        "reference",
    },
    "benchmark_delivery": {
        "assets",
        "same_calendar",
        "price_basis",
        "raw_ohlcv",
        "total_return_factor",
        "source_record_ids",
        "reference",
    },
    "delivery": {
        "local_only",
        "sha256_receipts",
        "row_counts",
        "credentials_excluded",
        "raw_rows_publication_forbidden",
        "reference",
    },
    "declaration": {
        "capabilities_only",
        "contains_provider_rows",
        "synthetic_control",
        "does_not_qualify_data",
        "does_not_authorize_backtest",
        "does_not_authorize_paper",
    },
}
FILE_CAPABILITY_KEYS = {"status", "fields_covered", "reference"}


class AuthorizedDataHandoffError(ValueError):
    """Fail-closed document-handoff error with a stable semantic code."""

    def __init__(self, code: str, detail: str):
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}")


def _fail(code: str, detail: str) -> None:
    raise AuthorizedDataHandoffError(code, detail)


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _canonical_sha256(value: object) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _date(value: object, field: str) -> datetime:
    try:
        parsed = datetime.strptime(str(value), "%Y-%m-%d")
    except ValueError:
        _fail("coverage_window_incomplete", f"{field} 不是 YYYY-MM-DD")
    return parsed


def _timestamp(value: object, code: str, field: str) -> datetime:
    raw = str(value)
    if EXPLICIT_OFFSET_PATTERN.search(raw) is None:
        _fail(code, f"{field} 缺 UTC offset")
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        _fail(code, f"{field} 不是有效 timestamp")


def _nonempty(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _exact_dict(value: object, keys: set[str], code: str, label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != keys:
        _fail(code, f"{label} keys 不符")
    return value


def _protocol_integrity(root: Path) -> dict[str, Any]:
    receipt_path = root / HANDOFF_RECEIPT_PATH
    try:
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        tracked = [
            item
            for item in receipt.values()
            if isinstance(item, dict) and set(item) == {"path", "sha256"}
        ]
        hash_checks = {
            item["path"]: _sha256_file(root / item["path"]) == item["sha256"]
            for item in tracked
        }
        passed = bool(
            receipt["status"]
            == "frozen_before_new_provider_lookup_or_handoff_implementation"
            and receipt["protocol"]["sha256"] == HANDOFF_PROTOCOL_SHA256
            and receipt["frozen_control_gate_count"] == 12
            and receipt["frozen_attack_count"] == 12
            and receipt["frozen_public_output_file_count"] == 4
            and receipt["handoff_schema_implemented_at_freeze"] is False
            and receipt["handoff_validator_implemented_at_freeze"] is False
            and receipt["new_provider_lookup_performed_at_freeze"] is False
            and receipt["authorized_provider_response_present_at_freeze"] is False
            and receipt["authorized_provider_sample_present_at_freeze"] is False
            and receipt["strategy_rule_changed"] is False
            and receipt["real_money_action_usd"] == 0
            and len(tracked) == 12
            and all(hash_checks.values())
        )
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError):
        passed = False
        hash_checks = {}
        receipt = {}
    if not passed:
        _fail("handoff_protocol_integrity_failed", "Round 16 協議或事前雜湊不完整")
    return {
        "passed": True,
        "frozen_at": receipt["frozen_at"],
        "git_head_at_freeze": receipt["git_head_at_freeze"],
        "hash_checks": hash_checks,
    }


def build_authorized_data_request(root: str | Path) -> dict[str, Any]:
    root_path = Path(root)
    protocol = _protocol_integrity(root_path)
    source_files = []
    for name in CIZ_SOURCE_FILES:
        if name in {
            "stk_security_info_hist.csv",
            "stk_ind_membership.csv",
            "stk_dly_security_data.csv",
            "stk_distributions.csv",
            "stk_delists.csv",
        }:
            source_role = "provider_ciz"
        else:
            source_role = "provider_or_evidence_overlay"
        source_files.append(
            {
                "name": name,
                "source_role": source_role,
                "minimum_fields": list(CIZ_REQUIRED_COLUMNS[name]),
            }
        )
    return {
        "schema_version": 1,
        "research_round": 16,
        "request_id": HANDOFF_REQUEST_ID,
        "status": "ready_to_send_not_yet_sent",
        "purpose": "文件能力確認及合法細樣本交接；不購買、不回測、不公開原始列",
        "protocol_sha256": HANDOFF_PROTOCOL_SHA256,
        "protocol_integrity": protocol,
        "frozen_adapter": {
            "version": CIZ_ADAPTER_VERSION,
            "path": "usfddk/crsp_ciz_adapter.py",
            "sha256": _sha256_file(root_path / "usfddk/crsp_ciz_adapter.py"),
        },
        "response_schema": {
            "path": HANDOFF_SCHEMA_PATH,
            "sha256": _sha256_file(root_path / HANDOFF_SCHEMA_PATH),
        },
        "coverage": {
            "buffer_start": BUFFER_START,
            "formal_start": FORMAL_START,
            "formal_end": FORMAL_END,
            "next_execution_session": NEXT_EXECUTION_SESSION,
            "minimum_pre_signal_sessions": 252,
        },
        "provider_products_to_confirm": [
            {
                "product_code": "crsp_m_stock",
                "label": "CRSP Stock (Monthly update package)",
                "status": "public_catalog_candidate_login_confirmation_required",
            },
            {
                "product_code": "crsp_m_indexes",
                "label": "CRSP Indexes (Monthly update package)",
                "status": "public_catalog_candidate_login_confirmation_required",
            },
        ],
        "wrds_dataset_candidates_to_confirm": [
            "crsp.dsf_v2",
            "crsp.msf_v2",
            "crsp.StkSecurityInfoHist",
            "/wrds/crsp/sasdata/a_stock_v2",
            "/wrds/crsp/sasdata/a_indexes_v2",
        ],
        "source_format": "CIZ_FF2",
        "source_files": source_files,
        "execution_overlay": {
            "file": "benchmark_daily.csv",
            "assets": ["QQQ", "SPY"],
            "columns": list(BENCHMARK_COLUMNS),
            "price_basis": "raw_unadjusted_ohlc_plus_total_return_factor",
            "same_calendar_required": True,
        },
        "provider_questions": [
            "S&P 500 成分 start/end 及 announcement/availability timestamp 可否逐次提供？",
            "2006–2026 DelRet 缺失數量、比例及 missing reason 是多少？",
            "缺失 DelRet 能否以現金／換股代價及 successor PERMNO/PERMCO 重建？",
            "raw OHLCV、停牌、DisExDt、DisPayDt 及下一開市覆蓋是否完整？",
            "本地研究、衍生匯總、SHA-256 收據及禁止原始列再分發的授權邊界是甚麼？",
        ],
        "delivery_policy": {
            "local_only": True,
            "credentials_excluded": True,
            "raw_rows_publication_forbidden": True,
            "sha256_and_row_receipts_required": True,
            "git_path_allowed": False,
        },
    }


def _validate_response_shape(response: object) -> dict[str, Any]:
    response_dict = _exact_dict(response, RESPONSE_KEYS, "response_schema_mismatch", "response")
    for key, keys in NESTED_KEYS.items():
        _exact_dict(response_dict[key], keys, "response_schema_mismatch", key)
    return response_dict


def validate_authorized_data_response(
    envelope: object,
    *,
    root: str | Path,
    allow_synthetic_control: bool = False,
) -> dict[str, Any]:
    """Validate one capability response without reading or qualifying provider rows."""

    root_path = Path(root)
    protocol = _protocol_integrity(root_path)
    envelope_dict = _exact_dict(
        envelope,
        {"response", "response_sha256"},
        "response_schema_mismatch",
        "response envelope",
    )
    response = _validate_response_shape(envelope_dict["response"])
    receipt_hash = envelope_dict["response_sha256"]
    if (
        not isinstance(receipt_hash, str)
        or SHA256_PATTERN.fullmatch(receipt_hash) is None
        or receipt_hash != _canonical_sha256(response)
    ):
        _fail("response_receipt_mismatch", "response SHA-256 不符")

    is_synthetic = response["status"] == "synthetic_document_response_control"
    if response["status"] not in {
        "provider_document_response",
        "synthetic_document_response_control",
    } or (is_synthetic and not allow_synthetic_control):
        _fail("response_schema_mismatch", "response status 不允許")
    if (
        response["schema_version"] != 1
        or response["request_id"] != HANDOFF_REQUEST_ID
        or response["request_protocol_sha256"] != HANDOFF_PROTOCOL_SHA256
    ):
        _fail("request_binding_mismatch", "request ID、版本或協議雜湊漂移")

    if not all(
        _nonempty(response[key])
        for key in ("provider", "provider_product", "product_reference")
    ):
        _fail("provider_identity_missing", "供應商、產品或產品參考空白")
    _timestamp(response["responded_at"], "response_schema_mismatch", "responded_at")

    license_data = response["license_attestation"]
    if (
        license_data["authorized_for_local_research"] is not True
        or not isinstance(license_data["raw_redistribution_allowed"], bool)
        or not _nonempty(license_data["reference"])
    ):
        _fail("license_attestation_invalid", "本地研究授權或再分發邊界不完整")
    _timestamp(
        license_data["attested_at"],
        "license_timestamp_invalid",
        "license attested_at",
    )

    if response["source_format"] != "CIZ_FF2":
        _fail("source_format_unsupported", "只接受 CIZ_FF2")
    wrds_mapping = response["wrds_mapping"]
    if (
        wrds_mapping["status"]
        not in {"provider_confirmed", "login_required", "not_applicable"}
        or not isinstance(wrds_mapping["schema_candidates"], list)
        or any(not _nonempty(item) for item in wrds_mapping["schema_candidates"])
        or len(set(wrds_mapping["schema_candidates"]))
        != len(wrds_mapping["schema_candidates"])
        or not _nonempty(wrds_mapping["reference"])
    ):
        _fail("source_format_unsupported", "WRDS mapping 回覆不完整")

    capabilities = response["file_capabilities"]
    if not isinstance(capabilities, dict) or set(capabilities) != set(CIZ_SOURCE_FILES):
        _fail("file_capability_set_mismatch", "十份輸入能力集合不符")
    for name in CIZ_SOURCE_FILES:
        capability = _exact_dict(
            capabilities[name],
            FILE_CAPABILITY_KEYS,
            "response_schema_mismatch",
            name,
        )
        if capability["status"] not in {"provider", "evidence", "unavailable"}:
            _fail("response_schema_mismatch", f"{name} status 無效")
        if not isinstance(capability["fields_covered"], bool) or not isinstance(
            capability["reference"], str
        ):
            _fail("response_schema_mismatch", f"{name} capability 型別無效")
        if capability["status"] == "unavailable" or capability["fields_covered"] is not True:
            _fail("file_capability_unavailable", f"{name} 未能完整交付")
        if not _nonempty(capability["reference"]):
            _fail("file_capability_unavailable", f"{name} 缺證據參考")

    membership = response["membership_semantics"]
    if (
        not _nonempty(membership["sp500_index_identifier"])
        or membership["effective_dates_available"] is not True
        or membership["announcement_status"] not in {"provider", "evidence"}
        or membership["point_in_time_supported"] is not True
        or not _nonempty(membership["reference"])
    ):
        _fail(
            "membership_availability_unsupported",
            "S&P 500 公布／可知時間不足以 point-in-time 重建",
        )

    coverage = response["coverage"]
    if (
        _date(coverage["buffer_start"], "buffer_start") > _date(BUFFER_START, "buffer")
        or coverage["formal_start"] != FORMAL_START
        or coverage["formal_end"] != FORMAL_END
        or _date(coverage["next_execution_session"], "next_execution_session")
        < _date(NEXT_EXECUTION_SESSION, "required next execution")
        or not isinstance(coverage["minimum_pre_signal_sessions"], int)
        or isinstance(coverage["minimum_pre_signal_sessions"], bool)
        or coverage["minimum_pre_signal_sessions"] < 252
    ):
        _fail("coverage_window_incomplete", "固定 20 年、前置緩衝或下一開市不完整")

    history = response["security_history"]
    history_flags = (
        "permno",
        "permco",
        "historical_ticker",
        "share_class",
        "primary_exchange",
        "historical_classification",
    )
    if (
        any(history[key] is not True for key in history_flags)
        or history["known_at_status"] not in {"provider", "evidence"}
        or not _nonempty(history["reference"])
    ):
        _fail("security_history_capability_missing", "永久 ID 或歷史證券欄位不完整")

    market = response["market_actions"]
    market_flags = (
        "raw_ohlcv",
        "daily_return",
        "return_missing_flags",
        "trading_status",
        "distribution_ex_date",
        "distribution_pay_date",
        "price_share_factors",
    )
    if any(market[key] is not True for key in market_flags) or not _nonempty(
        market["reference"]
    ):
        _fail("market_action_capability_missing", "raw 行情、停牌或派息能力缺失")

    exits = response["exit_economics"]
    missing_count = exits["missing_delret_count"]
    missing_fraction = exits["missing_delret_fraction"]
    if (
        exits["delisting_return"] is not True
        or exits["missing_reason"] is not True
        or not isinstance(missing_count, int)
        or isinstance(missing_count, bool)
        or missing_count < 0
        or not isinstance(missing_fraction, (int, float))
        or isinstance(missing_fraction, bool)
        or not math.isfinite(float(missing_fraction))
        or not 0 <= float(missing_fraction) <= 1
        or exits["cash_consideration_status"] not in {"provider", "evidence"}
        or exits["stock_consideration_status"] not in {"provider", "evidence"}
        or exits["successor_identifiers"] is not True
        or not _nonempty(exits["reference"])
    ):
        _fail("exit_economics_capability_missing", "缺失 DelRet 或退出代價能力不完整")

    benchmark = response["benchmark_delivery"]
    if (
        benchmark["assets"] != ["QQQ", "SPY"]
        or benchmark["same_calendar"] is not True
        or benchmark["price_basis"]
        != "raw_unadjusted_ohlc_plus_total_return_factor"
        or benchmark["raw_ohlcv"] is not True
        or benchmark["total_return_factor"] is not True
        or benchmark["source_record_ids"] is not True
        or not _nonempty(benchmark["reference"])
    ):
        _fail("benchmark_delivery_invalid", "QQQ／SPY 同步或 raw 價格政策不符")

    delivery = response["delivery"]
    if (
        any(
            delivery[key] is not True
            for key in (
                "local_only",
                "sha256_receipts",
                "row_counts",
                "credentials_excluded",
                "raw_rows_publication_forbidden",
            )
        )
        or not _nonempty(delivery["reference"])
    ):
        _fail("delivery_policy_invalid", "本地隔離、收據或禁止公開政策不完整")

    declaration = response["declaration"]
    if (
        declaration["capabilities_only"] is not True
        or declaration["contains_provider_rows"] is not False
        or declaration["synthetic_control"] is not is_synthetic
        or declaration["does_not_qualify_data"] is not True
        or declaration["does_not_authorize_backtest"] is not True
        or declaration["does_not_authorize_paper"] is not True
    ):
        _fail("response_schema_mismatch", "文件回覆邊界聲明不符")

    gate_rows = [
        ("01", "事前凍結完整性", "本協議及十二份前置雜湊完整"),
        ("02", "回覆 schema 精確", "版本、keys、request ID 及收據一致"),
        ("03", "供應商與產品明確", "供應商、產品及正式參考非空白"),
        ("04", "授權邊界明確", "本地研究授權、UTC 證明及再分發政策完整"),
        ("05", "CIZ 格式明確", "CIZ_FF2；WRDS mapping 狀態明示"),
        ("06", "十份輸入逐份回答", "固定十份能力及證據參考完整"),
        ("07", "成分時間語義", "S&P 500 生效及公布／可知時間可重建"),
        ("08", "固定期間與緩衝", "2005-07-01 至 2026-08-03；至少 252 sessions"),
        ("09", "永久 ID 與歷史", "PERMNO／PERMCO 及逐期證券歷史完整"),
        ("10", "Raw 行情與派息", "raw OHLCV、停牌、ex/pay-date 及因子完整"),
        ("11", "退出經濟完整", "DelRet 缺失分布、退出代價及 successor 完整"),
        ("12", "公平基準與交付", "QQQ／SPY 同步、本地隔離及收據完整"),
    ]
    return {
        "status": (
            "synthetic_document_response_control_passed"
            if is_synthetic
            else "provider_document_response_ready_for_sample_delivery"
        ),
        "gate_summary": {"passed": 12, "total": 12, "all_passed": True},
        "gates": [
            {"id": gate_id, "label": label, "passed": True, "detail": detail}
            for gate_id, label, detail in gate_rows
        ],
        "protocol_integrity": protocol,
        "response_sha256": receipt_hash,
        "synthetic_control": is_synthetic,
        "contains_provider_rows": False,
        "sample_delivery_ready": not is_synthetic,
        "data_qualified": False,
        "formal_stock_backtest_authorized": False,
        "paper_authorized": False,
        "real_money_action_usd": 0,
    }


def _synthetic_response() -> dict[str, Any]:
    capabilities = {
        name: {
            "status": "provider" if index < 5 else "evidence",
            "fields_covered": True,
            "reference": f"synthetic-capability-{name}",
        }
        for index, name in enumerate(CIZ_SOURCE_FILES)
    }
    return {
        "schema_version": 1,
        "status": "synthetic_document_response_control",
        "request_id": HANDOFF_REQUEST_ID,
        "request_protocol_sha256": HANDOFF_PROTOCOL_SHA256,
        "provider": "authorized-synthetic-control-only",
        "provider_product": "round16-document-shape-control",
        "product_reference": "synthetic-no-provider-contact",
        "responded_at": "2026-08-04T00:30:00Z",
        "source_format": "CIZ_FF2",
        "wrds_mapping": {
            "status": "provider_confirmed",
            "schema_candidates": [
                "crsp_m_stock",
                "crsp_m_indexes",
                "crsp.dsf_v2",
                "crsp.msf_v2",
            ],
            "reference": "synthetic-mapping-control",
        },
        "license_attestation": {
            "authorized_for_local_research": True,
            "raw_redistribution_allowed": False,
            "attested_at": "2026-08-04T00:00:00Z",
            "reference": "synthetic-license-control",
        },
        "coverage": {
            "buffer_start": BUFFER_START,
            "formal_start": FORMAL_START,
            "formal_end": FORMAL_END,
            "next_execution_session": NEXT_EXECUTION_SESSION,
            "minimum_pre_signal_sessions": 252,
        },
        "file_capabilities": capabilities,
        "membership_semantics": {
            "sp500_index_identifier": "synthetic-sp500-index-id",
            "effective_dates_available": True,
            "announcement_status": "evidence",
            "point_in_time_supported": True,
            "reference": "synthetic-membership-control",
        },
        "security_history": {
            "permno": True,
            "permco": True,
            "historical_ticker": True,
            "share_class": True,
            "primary_exchange": True,
            "historical_classification": True,
            "known_at_status": "evidence",
            "reference": "synthetic-security-history-control",
        },
        "market_actions": {
            "raw_ohlcv": True,
            "daily_return": True,
            "return_missing_flags": True,
            "trading_status": True,
            "distribution_ex_date": True,
            "distribution_pay_date": True,
            "price_share_factors": True,
            "reference": "synthetic-market-action-control",
        },
        "exit_economics": {
            "delisting_return": True,
            "missing_reason": True,
            "missing_delret_count": 2,
            "missing_delret_fraction": 0.02,
            "cash_consideration_status": "evidence",
            "stock_consideration_status": "evidence",
            "successor_identifiers": True,
            "reference": "synthetic-exit-control",
        },
        "benchmark_delivery": {
            "assets": ["QQQ", "SPY"],
            "same_calendar": True,
            "price_basis": "raw_unadjusted_ohlc_plus_total_return_factor",
            "raw_ohlcv": True,
            "total_return_factor": True,
            "source_record_ids": True,
            "reference": "synthetic-benchmark-control",
        },
        "delivery": {
            "local_only": True,
            "sha256_receipts": True,
            "row_counts": True,
            "credentials_excluded": True,
            "raw_rows_publication_forbidden": True,
            "reference": "synthetic-delivery-control",
        },
        "declaration": {
            "capabilities_only": True,
            "contains_provider_rows": False,
            "synthetic_control": True,
            "does_not_qualify_data": True,
            "does_not_authorize_backtest": True,
            "does_not_authorize_paper": True,
        },
    }


def _envelope(response: dict[str, Any]) -> dict[str, Any]:
    return {"response": response, "response_sha256": _canonical_sha256(response)}


AttackMutation = Callable[[dict[str, Any]], None]


def _attacks() -> list[tuple[str, str, str, AttackMutation]]:
    return [
        (
            "01",
            "回覆多一個頂層 key",
            "response_schema_mismatch",
            lambda response: response.__setitem__("unexpected", True),
        ),
        (
            "02",
            "request ID 漂移",
            "request_binding_mismatch",
            lambda response: response.__setitem__("request_id", "wrong-request"),
        ),
        (
            "03",
            "供應商產品空白",
            "provider_identity_missing",
            lambda response: response.__setitem__("provider_product", ""),
        ),
        (
            "04",
            "本地研究授權不是 true",
            "license_attestation_invalid",
            lambda response: response["license_attestation"].__setitem__(
                "authorized_for_local_research", False
            ),
        ),
        (
            "05",
            "授權時間沒有 UTC offset",
            "license_timestamp_invalid",
            lambda response: response["license_attestation"].__setitem__(
                "attested_at", "2026-08-04T00:00:00"
            ),
        ),
        (
            "06",
            "source format 退回 SIZ",
            "source_format_unsupported",
            lambda response: response.__setitem__("source_format", "SIZ_FF1"),
        ),
        (
            "07",
            "十份輸入少一份",
            "file_capability_set_mismatch",
            lambda response: response["file_capabilities"].pop("exit_terms.csv"),
        ),
        (
            "08",
            "公布時間 unavailable 卻聲稱 point-in-time",
            "membership_availability_unsupported",
            lambda response: response["membership_semantics"].__setitem__(
                "announcement_status", "unavailable"
            ),
        ),
        (
            "09",
            "訊號前緩衝縮短一天",
            "coverage_window_incomplete",
            lambda response: response["coverage"].__setitem__(
                "buffer_start", "2005-07-02"
            ),
        ),
        (
            "10",
            "派息 pay-date 能力缺失",
            "market_action_capability_missing",
            lambda response: response["market_actions"].__setitem__(
                "distribution_pay_date", False
            ),
        ),
        (
            "11",
            "缺失 DelRet 沒有有效比例",
            "exit_economics_capability_missing",
            lambda response: response["exit_economics"].__setitem__(
                "missing_delret_fraction", -0.01
            ),
        ),
        (
            "12",
            "基準價格標示 adjusted",
            "benchmark_delivery_invalid",
            lambda response: response["benchmark_delivery"].__setitem__(
                "price_basis", "adjusted_close"
            ),
        ),
    ]


def run_authorized_data_handoff_validation(root: str | Path) -> dict[str, Any]:
    root_path = Path(root)
    request = build_authorized_data_request(root_path)
    control_response = _synthetic_response()
    control = validate_authorized_data_response(
        _envelope(control_response),
        root=root_path,
        allow_synthetic_control=True,
    )
    attack_results: list[dict[str, Any]] = []
    for attack_id, label, expected_code, mutate in _attacks():
        attacked = copy.deepcopy(control_response)
        mutate(attacked)
        observed_code = None
        try:
            validate_authorized_data_response(
                _envelope(attacked),
                root=root_path,
                allow_synthetic_control=True,
            )
        except AuthorizedDataHandoffError as exc:
            observed_code = exc.code
        attack_results.append(
            {
                "id": attack_id,
                "label": label,
                "expected_error_code": expected_code,
                "observed_error_code": observed_code,
                "rejected": observed_code == expected_code,
                "response_receipt_recomputed": True,
            }
        )

    rejected = sum(int(item["rejected"]) for item in attack_results)
    readiness = json.loads(
        (root_path / "artifacts/short_term_point_in_time_readiness.json").read_text(
            encoding="utf-8"
        )
    )
    if readiness["gate_summary"] != EXPECTED_TRUE_READINESS:
        raise ValueError("真實 point-in-time readiness 已漂移；不得沿用 Round 16 結論")
    synthetic_ok = control["gate_summary"] == {
        "passed": 12,
        "total": 12,
        "all_passed": True,
    }
    attacks_ok = rejected == len(attack_results) == 12
    return {
        "schema_version": 1,
        "research_round": 16,
        "status": (
            "handoff_contract_validated_provider_response_and_data_still_missing"
            if synthetic_ok and attacks_ok
            else "handoff_contract_incomplete_or_failed"
        ),
        "evidence_as_of": "2026-08-04",
        "request": request,
        "official_verification": {
            "new_provider_lookup_performed_after_freeze": True,
            "provider_set_changed": False,
            "findings": [
                {
                    "id": "ciz_current",
                    "status": "documented",
                    "detail": "WRDS 已公告 CIZ Flat File Format 2.0 取代 SIZ。",
                    "url": "https://wrds-www.wharton.upenn.edu/pages/data-announcements/changes-to-crsp-data/",
                },
                {
                    "id": "wrds_dataset_candidates",
                    "status": "documented_candidate",
                    "detail": "WRDS 官方 CIZ macro 使用 crsp.dsf_v2／msf_v2 及 StkSecurityInfoHist。",
                    "url": "https://wrds-www.wharton.upenn.edu/pages/wrds-research/macros/crsp-ciztosiz-macro/",
                },
                {
                    "id": "wrds_library_candidates",
                    "status": "documented_candidate",
                    "detail": "WRDS 官方 size macro 使用 a_stock_v2／a_indexes_v2 library。",
                    "url": "https://wrds-www.wharton.upenn.edu/pages/wrds-research/macros/macros-portfolios-size-ciz/",
                },
                {
                    "id": "catalog_products",
                    "status": "public_catalog_login_confirmation_required",
                    "detail": "公開 catalog 列出 crsp_m_stock／crsp_m_indexes；完整 data dictionary 要登入。",
                    "url": "https://wrds-www.wharton.upenn.edu/pages/about/data-vendors/center-for-research-in-security-prices-crsp/",
                },
            ],
            "data_dictionary_login_required": True,
            "wrds_credentials_present": False,
            "provider_contacted": False,
            "authorized_provider_response_received": False,
            "authorized_provider_sample_received": False,
        },
        "synthetic_control": control,
        "attack_summary": {
            "rejected": rejected,
            "total": len(attack_results),
            "all_rejected": attacks_ok,
        },
        "attacks": attack_results,
        "actual_document_handoff": {
            "passed": 1,
            "total": 12,
            "all_passed": False,
            "only_passed_gate": "01_preregistration_integrity",
        },
        "actual_point_in_time_readiness": readiness["gate_summary"],
        "formal_stock_backtest_authorized": False,
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
            "在使用者授權對外聯絡後，把固定請求交給 CRSP／WRDS；取得帶產品及授權的"
            "文件回覆並通過 12/12，才接受本地隔離細樣本。"
        ),
        "disclaimer": (
            "合成 12/12 及攻擊全拒收只證明交接驗證器會關門；不證明供應商、數據、"
            "策略、Paper 或盈利通過。"
        ),
    }
