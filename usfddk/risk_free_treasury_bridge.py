from __future__ import annotations

import hashlib
import math
import re
import statistics
import zipfile
from collections.abc import Mapping
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from xml.etree import ElementTree

SCHEMA_VERSION = 1
RESEARCH_ROUND = 37
PROTOCOL_PATH = "docs/SHORT_TERM_RF_TREASURY_BRIDGE_PROTOCOL.md"
PROTOCOL_RECEIPT_PATH = (
    "artifacts/short_term_rf_treasury_bridge_protocol_receipt.json"
)
PROTOCOL_SHA256 = (
    "08d3163799cb1999666c55ef980f480fa5e50a1f11a46c5147aa7e5c3fd8ca1d"
)
PROTOCOL_RECEIPT_SHA256 = (
    "8f9f60eb5b0db6ff1be545a263b98aaed9c41b0d13f32177dbc4d33bdf6d6824"
)
PARENT_STAGING_PROTOCOL_PATH = "docs/SHORT_TERM_RISK_FREE_STAGING_PROTOCOL.md"
PARENT_STAGING_PROTOCOL_SHA256 = (
    "d0ccaa65694ba7b41aa1726a7a475c05ea988f03091246ce2173cc9681176439"
)
PARENT_STAGING_RECEIPT_PATH = (
    "artifacts/short_term_risk_free_staging_protocol_receipt.json"
)
PARENT_STAGING_RECEIPT_SHA256 = (
    "bbcde7cea30c21169ba5e09f851b5a71e873856aef7f366fa810cd5628714e82"
)
PARENT_REBIND_PROTOCOL_PATH = "docs/SHORT_TERM_RISK_FREE_REBIND_PROTOCOL.md"
PARENT_REBIND_PROTOCOL_SHA256 = (
    "807919e88a60c364cbcf48f0bd3eb06bf006d9956b1a121ef2cf2b8b58b05b9b"
)
PARENT_REBIND_RECEIPT_PATH = "artifacts/short_term_risk_free_rebind_receipt.json"
PARENT_REBIND_RECEIPT_SHA256 = (
    "f208061b579951ad514366af277e5349428e0dc45d84b58da4f5a5b7d3b18adb"
)
TREASURY_URL = (
    "https://home.treasury.gov/resource-center/data-chart-center/interest-rates/"
    "pages/xml?data=daily_treasury_bill_rates&field_tdr_date_value=2026"
)
TREASURY_HOST = "home.treasury.gov"
TREASURY_FIELD = "ROUND_B1_YIELD_4WK_2"
FRENCH_RF_PATH = "artifacts/french_ff_factors_daily_39f9ae1d.zip"
FRENCH_RF_SHA256 = (
    "39f9ae1d0e9f575024bc23145980ac270cea508fb67e592578b3f4d65f36d006"
)
TARGET_START = "2026-07-01"
TARGET_END = "2026-07-31"
EXPECTED_MISSING_SESSIONS = (
    "2026-07-01",
    "2026-07-02",
    "2026-07-06",
    "2026-07-07",
    "2026-07-08",
    "2026-07-09",
    "2026-07-10",
    "2026-07-13",
    "2026-07-14",
    "2026-07-15",
    "2026-07-16",
    "2026-07-17",
    "2026-07-20",
    "2026-07-21",
    "2026-07-22",
    "2026-07-23",
    "2026-07-24",
    "2026-07-27",
    "2026-07-28",
    "2026-07-29",
    "2026-07-30",
    "2026-07-31",
)
MAX_BODY_BYTES = 5 * 1024 * 1024


class TreasuryBridgeError(ValueError):
    """Fail-closed error with a stable semantic code."""

    def __init__(self, code: str, detail: str):
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}")


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _sha256_bytes(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest()


def _load_json(path: Path) -> dict[str, Any]:
    import json

    return json.loads(path.read_text(encoding="utf-8"))


def _fail(code: str, detail: str) -> None:
    raise TreasuryBridgeError(code, detail)


def protocol_integrity(root: str | Path) -> dict[str, Any]:
    root_path = Path(root).resolve()
    receipt_path = root_path / PROTOCOL_RECEIPT_PATH
    try:
        receipt = _load_json(receipt_path)
        expected_files = {
            PROTOCOL_PATH: PROTOCOL_SHA256,
            PROTOCOL_RECEIPT_PATH: PROTOCOL_RECEIPT_SHA256,
            PARENT_STAGING_PROTOCOL_PATH: PARENT_STAGING_PROTOCOL_SHA256,
            PARENT_STAGING_RECEIPT_PATH: PARENT_STAGING_RECEIPT_SHA256,
            PARENT_REBIND_PROTOCOL_PATH: PARENT_REBIND_PROTOCOL_SHA256,
            PARENT_REBIND_RECEIPT_PATH: PARENT_REBIND_RECEIPT_SHA256,
            FRENCH_RF_PATH: FRENCH_RF_SHA256,
        }
        hash_checks = {
            path: _sha256_file(root_path / path) == expected
            for path, expected in expected_files.items()
        }
        frozen = (
            receipt["schema_version"] == SCHEMA_VERSION
            and receipt["research_round"] == RESEARCH_ROUND
            and receipt["status"] == "frozen_before_treasury_bridge_observation"
            and receipt["protocol"]
            == {"path": PROTOCOL_PATH, "sha256": PROTOCOL_SHA256}
            and receipt["parent_risk_free_staging_protocol"]
            == {
                "path": PARENT_STAGING_PROTOCOL_PATH,
                "sha256": PARENT_STAGING_PROTOCOL_SHA256,
            }
            and receipt["parent_risk_free_staging_receipt"]
            == {
                "path": PARENT_STAGING_RECEIPT_PATH,
                "sha256": PARENT_STAGING_RECEIPT_SHA256,
            }
            and receipt["parent_risk_free_rebind_protocol"]
            == {
                "path": PARENT_REBIND_PROTOCOL_PATH,
                "sha256": PARENT_REBIND_PROTOCOL_SHA256,
            }
            and receipt["parent_risk_free_rebind_receipt"]
            == {
                "path": PARENT_REBIND_RECEIPT_PATH,
                "sha256": PARENT_REBIND_RECEIPT_SHA256,
            }
            and receipt["treasury_source"]["url"] == TREASURY_URL
            and receipt["treasury_source"]["host"] == TREASURY_HOST
            and receipt["treasury_source"]["field"] == TREASURY_FIELD
            and receipt["treasury_source"]["target_start"] == TARGET_START
            and receipt["treasury_source"]["target_end"] == TARGET_END
            and receipt["frozen_french_rf"]
            == {"path": FRENCH_RF_PATH, "sha256": FRENCH_RF_SHA256}
            and receipt["expected_missing_session_count"]
            == len(EXPECTED_MISSING_SESSIONS)
            and receipt["source_observed_before_freeze"] is False
            and receipt["raw_source_persisted_at_freeze"] is False
            and receipt["formal_rf_substitute_at_freeze"] is False
            and receipt["formal_backtest_authorized"] is False
            and receipt["strategy_run_count"] == 0
            and receipt["paper_authorized"] is False
            and receipt["paper_state"] == "all_cash"
            and receipt["real_money_action_usd"] == 0
            and receipt["frozen_control_count"] == 10
            and receipt["frozen_attack_count"] == 10
            and all(hash_checks.values())
        )
    except (OSError, KeyError, TypeError, ValueError, UnicodeError) as exc:
        _fail("protocol_mismatch", f"Round37 protocol or receipt invalid: {exc}")
    if not frozen:
        _fail("protocol_mismatch", "Round37 protocol／receipt parent chain invalid")
    return {"passed": True, "hash_checks": hash_checks}


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _parse_float(value: str | None, field: str) -> float:
    if value is None or not value.strip() or value.strip().upper() == "N/A":
        _fail("treasury_field_missing", f"{field} is missing")
    try:
        parsed = float(value)
    except ValueError:
        _fail("treasury_field_invalid", f"{field} is not numeric")
    if not math.isfinite(parsed):
        _fail("treasury_field_invalid", f"{field} is not finite")
    return parsed


def parse_treasury_xml(body: bytes) -> dict[str, dict[str, float | str]]:
    if not body or len(body) > MAX_BODY_BYTES:
        _fail("body_size_invalid", "Treasury XML body is empty or too large")
    try:
        root = ElementTree.fromstring(body)
    except ElementTree.ParseError as exc:
        _fail("xml_invalid", f"Treasury XML cannot be parsed: {exc}")
    rows: dict[str, dict[str, float | str]] = {}
    for properties in root.iter():
        if _local_name(properties.tag) != "properties":
            continue
        values = {
            _local_name(child.tag): (child.text or "").strip()
            for child in properties
        }
        raw_date = values.get("INDEX_DATE", "")[:10]
        if not re.fullmatch(r"2026-\d{2}-\d{2}", raw_date):
            continue
        if raw_date in rows:
            _fail("duplicate_session", f"duplicate Treasury session {raw_date}")
        annual_percent = _parse_float(values.get(TREASURY_FIELD), TREASURY_FIELD)
        if annual_percent < -1 or annual_percent > 100:
            _fail("treasury_field_invalid", f"yield out of range on {raw_date}")
        rows[raw_date] = {
            "date": raw_date,
            "annual_yield_percent": annual_percent,
            "proxy_daily_simple": (1 + annual_percent / 100) ** (1 / 365) - 1,
        }
    if not rows:
        _fail("treasury_rows_missing", "no 2026 Treasury bill rows found")
    return dict(sorted(rows.items()))


def _load_french_rf(root: Path) -> dict[str, float]:
    path = root / FRENCH_RF_PATH
    if _sha256_file(path) != FRENCH_RF_SHA256:
        _fail("french_rf_hash_mismatch", "frozen French RF ZIP hash drifted")
    values: dict[str, float] = {}
    try:
        with zipfile.ZipFile(path) as archive:
            names = archive.namelist()
            if names != ["F-F_Research_Data_Factors_daily.csv"]:
                _fail("french_rf_member_mismatch", "French RF member set drifted")
            text = archive.read(names[0]).decode("latin1")
    except (OSError, zipfile.BadZipFile, UnicodeError) as exc:
        _fail("french_rf_read_failed", str(exc))
    for line in text.splitlines():
        if not re.fullmatch(r"20\d{6},.*", line):
            continue
        fields = [part.strip() for part in line.split(",")]
        if len(fields) != 5:
            _fail("french_rf_schema_mismatch", "French RF row has unexpected columns")
        raw_date = fields[0]
        values[f"{raw_date[:4]}-{raw_date[4:6]}-{raw_date[6:8]}"] = float(fields[4]) / 100
    if not values:
        _fail("french_rf_rows_missing", "French RF has no dated rows")
    return values


def _correlation(left: list[float], right: list[float]) -> float | None:
    if len(left) < 2:
        return None
    left_mean = statistics.mean(left)
    right_mean = statistics.mean(right)
    left_dev = [value - left_mean for value in left]
    right_dev = [value - right_mean for value in right]
    denominator = math.sqrt(
        sum(value * value for value in left_dev)
        * sum(value * value for value in right_dev)
    )
    return None if denominator == 0 else sum(
        a * b for a, b in zip(left_dev, right_dev, strict=True)
    ) / denominator


def _validate_response(response: Mapping[str, Any]) -> tuple[bytes, dict[str, Any]]:
    final_url = response.get("final_url")
    if not isinstance(final_url, str):
        _fail("source_url_invalid", "Treasury final URL is missing")
    parsed = urlparse(final_url)
    if parsed.scheme != "https" or parsed.hostname != TREASURY_HOST:
        _fail("source_host_drift", "Treasury final URL host or scheme drifted")
    if response.get("status") != 200:
        _fail("source_http_status", f"Treasury HTTP status {response.get('status')!r}")
    content_type = str(response.get("content_type") or "").casefold()
    if "xml" not in content_type:
        _fail("source_content_type", "Treasury response is not XML")
    body = response.get("body")
    if not isinstance(body, bytes):
        _fail("source_body_type", "Treasury body must be bytes")
    if len(body) > MAX_BODY_BYTES:
        _fail("body_size_invalid", "Treasury XML body is too large")
    return body, {
        "final_url": final_url,
        "http_status": response.get("status"),
        "content_type": content_type,
        "body_size_bytes": len(body),
        "body_sha256": _sha256_bytes(body),
        "raw_source_persisted": False,
    }


def make_bridge_result(
    response: Mapping[str, Any], *, root: str | Path
) -> dict[str, Any]:
    root_path = Path(root).resolve()
    protocol = protocol_integrity(root_path)
    body, source = _validate_response(response)
    rows = parse_treasury_xml(body)
    target = [rows[session] for session in EXPECTED_MISSING_SESSIONS if session in rows]
    missing = [session for session in EXPECTED_MISSING_SESSIONS if session not in rows]
    if missing:
        _fail("target_session_missing", f"Treasury missing target sessions: {missing}")
    french = _load_french_rf(root_path)
    overlap_dates = sorted(set(rows) & set(french))
    treasury_values = [float(rows[session]["proxy_daily_simple"]) for session in overlap_dates]
    french_values = [french[session] for session in overlap_dates]
    differences = [a - b for a, b in zip(treasury_values, french_values, strict=True)]
    comparison = {
        "status": "definition_mismatch_diagnostic",
        "proxy_formula": "(1 + annual_percent / 100) ** (1 / 365) - 1",
        "overlap_sessions": len(overlap_dates),
        "overlap_start": overlap_dates[0] if overlap_dates else None,
        "overlap_end": overlap_dates[-1] if overlap_dates else None,
        "mean_diff": statistics.mean(differences) if differences else None,
        "mean_abs_diff": statistics.mean(abs(value) for value in differences)
        if differences
        else None,
        "max_abs_diff": max(abs(value) for value in differences) if differences else None,
        "correlation": _correlation(treasury_values, french_values),
        "formal_equivalence": False,
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "research_round": RESEARCH_ROUND,
        "status": "official_treasury_bridge_observed_formal_rf_still_blocked",
        "protocol_sha256": PROTOCOL_SHA256,
        "protocol_integrity": protocol,
        "source": {
            **source,
            "url": TREASURY_URL,
            "host": TREASURY_HOST,
            "field": TREASURY_FIELD,
        },
        "coverage": {
            "target_start": TARGET_START,
            "target_end": TARGET_END,
            "target_sessions": len(EXPECTED_MISSING_SESSIONS),
            "observed_target_sessions": len(target),
            "missing_target_sessions": missing,
            "all_target_sessions_observed": not missing,
            "all_source_sessions": len(rows),
            "source_first_session": next(iter(rows)),
            "source_last_session": next(reversed(rows)),
        },
        "target_rows": target,
        "comparison": comparison,
        "formal_rf_substitute": False,
        "complete_risk_free_package": False,
        "formal_backtest_authorized": False,
        "strategy_run_count": 0,
        "paper_authorized": False,
        "paper_state": "all_cash",
        "real_money_action_usd": 0,
        "next_action": (
            "取得與正式 French／ICE BofA 定義一致且獲授權的完整 RF manifest；"
            "Treasury bridge 只作差異診斷，不能回填正式 RF。"
        ),
    }


def validate_result(payload: Mapping[str, Any], *, root: str | Path) -> dict[str, Any]:
    protocol_integrity(root)
    if payload.get("research_round") != RESEARCH_ROUND:
        _fail("protocol_mismatch", "research round mismatch")
    if payload.get("protocol_sha256") != PROTOCOL_SHA256:
        _fail("protocol_mismatch", "protocol SHA-256 mismatch")
    source = payload.get("source", {})
    if source.get("host") != TREASURY_HOST or source.get("field") != TREASURY_FIELD:
        _fail("source_identity_mismatch", "Treasury source identity drifted")
    if source.get("raw_source_persisted") is not False:
        _fail("raw_source_persisted", "Treasury raw XML may not be persisted")
    coverage = payload.get("coverage", {})
    if coverage.get("target_sessions") != len(EXPECTED_MISSING_SESSIONS):
        _fail("coverage_contract_violation", "target session count drifted")
    if coverage.get("observed_target_sessions") != len(EXPECTED_MISSING_SESSIONS):
        _fail("target_session_missing", "not all target sessions were observed")
    if coverage.get("missing_target_sessions") != []:
        _fail("target_session_missing", "result claims missing target sessions")
    if payload.get("comparison", {}).get("formal_equivalence") is not False:
        _fail("definition_substitution", "Treasury proxy cannot claim formal equivalence")
    if payload.get("formal_rf_substitute") is not False:
        _fail("definition_substitution", "Treasury proxy cannot replace frozen RF")
    if payload.get("formal_backtest_authorized") is not False:
        _fail("decision_boundary_violation", "bridge cannot authorize formal backtest")
    if payload.get("paper_authorized") is not False or payload.get("paper_state") != "all_cash":
        _fail("decision_boundary_violation", "bridge cannot authorize or populate Paper")
    if payload.get("real_money_action_usd") != 0:
        _fail("decision_boundary_violation", "bridge cannot create real-money action")
    rows = payload.get("target_rows")
    if not isinstance(rows, list) or [row.get("date") for row in rows] != list(EXPECTED_MISSING_SESSIONS):
        _fail("target_rows_invalid", "target rows are not the fixed ordered 22 sessions")
    return {"passed": True, "status": payload.get("status")}
