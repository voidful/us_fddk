from __future__ import annotations

import csv
import hashlib
import io
import json
import math
import os
import re
import shutil
import stat
import tempfile
import zipfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Any

import exchange_calendars as xcals
import pandas as pd

STAGING_VERSION = "round19-official-risk-free-staging-v1"
PROTOCOL_PATH = "docs/SHORT_TERM_RISK_FREE_STAGING_PROTOCOL.md"
PROTOCOL_RECEIPT_PATH = (
    "artifacts/short_term_risk_free_staging_protocol_receipt.json"
)
PROTOCOL_SHA256 = "d0ccaa65694ba7b41aa1726a7a475c05ea988f03091246ce2173cc9681176439"
PARENT_PROTOCOL_PATH = "docs/SHORT_TERM_FORMAL_BACKTEST_PREREGISTRATION.md"
PARENT_PROTOCOL_SHA256 = (
    "4534130e245c97b6718e21a658708bd763c7046317a2b355c09b2589a8a3e083"
)
SOURCE_URL = (
    "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/"
    "F-F_Research_Data_Factors_daily_CSV.zip"
)
SOURCE_PAGE_URL = (
    "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/Data_Library.html"
)
SOURCE_DETAILS_URL = (
    "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/Data_Library/"
    "f-f_factors.html"
)
EXPECTED_SOURCE_SHA256 = (
    "39f9ae1d0e9f575024bc23145980ac270cea508fb67e592578b3f4d65f36d006"
)
EXPECTED_MEMBER = "F-F_Research_Data_Factors_daily.csv"
EXPECTED_DATA_CUT = "202606"
EXPECTED_SOURCE_LAST_SESSION = "2026-06-30"
STUDY_START = "2006-08-01"
STUDY_END = "2026-07-31"
EXPECTED_STUDY_SESSION_COUNT = 5_031
EXPECTED_MISSING_SESSION_COUNT = 22
RF_UNIT = "decimal_simple_daily_return"
RF_SERIES = "US_1M_TBILL_DAILY_RETURN"
MAX_ARCHIVE_MEMBER_BYTES = 10_000_000
DATA_ROW_PATTERN = re.compile(r"^\d{8}$")
DATA_CUT_PATTERN = re.compile(r"using the (\d{6}) CRSP database", re.IGNORECASE)


class RiskFreeStagingError(ValueError):
    """Fail-closed official risk-free staging error with a stable code."""

    def __init__(self, code: str, detail: str):
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}")


def _fail(code: str, detail: str) -> None:
    raise RiskFreeStagingError(code, detail)


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


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


def _protocol_integrity(root: str | Path) -> dict[str, Any]:
    root_path = Path(root).resolve()
    receipt_path = root_path / PROTOCOL_RECEIPT_PATH
    try:
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        checks = {
            PROTOCOL_PATH: _sha256_file(root_path / PROTOCOL_PATH)
            == PROTOCOL_SHA256,
            PARENT_PROTOCOL_PATH: _sha256_file(root_path / PARENT_PROTOCOL_PATH)
            == PARENT_PROTOCOL_SHA256,
            receipt["parent_formal_protocol_receipt"]["path"]: _sha256_file(
                root_path / receipt["parent_formal_protocol_receipt"]["path"]
            )
            == receipt["parent_formal_protocol_receipt"]["sha256"],
            receipt["parent_formal_validator"]["path"]: _sha256_file(
                root_path / receipt["parent_formal_validator"]["path"]
            )
            == receipt["parent_formal_validator"]["sha256"],
        }
        passed = bool(
            receipt["schema_version"] == 1
            and receipt["research_round"] == 19
            and receipt["status"]
            == "frozen_after_official_202606_source_inspection_before_staging_implementation"
            and receipt["protocol"]
            == {"path": PROTOCOL_PATH, "sha256": PROTOCOL_SHA256}
            and receipt["parent_formal_protocol"]
            == {
                "path": PARENT_PROTOCOL_PATH,
                "sha256": PARENT_PROTOCOL_SHA256,
            }
            and receipt["official_source_inspected_at_freeze"] is True
            and receipt["independent_first_seen_evidence"] is False
            and receipt["official_source_sha256_seen_at_freeze"]
            == EXPECTED_SOURCE_SHA256
            and receipt["official_data_cut_seen_at_freeze"] == EXPECTED_DATA_CUT
            and receipt["official_last_session_seen_at_freeze"]
            == EXPECTED_SOURCE_LAST_SESSION
            and receipt["known_missing_xnys_session_count_at_freeze"]
            == EXPECTED_MISSING_SESSION_COUNT
            and receipt["staging_implementation_present_at_freeze"] is False
            and receipt["staging_output_present_at_freeze"] is False
            and receipt["strategy_result_present_at_freeze"] is False
            and receipt["strategy_run_count"] == 0
            and receipt["paper_authorized"] is False
            and receipt["paper_state"] == "all_cash"
            and receipt["real_money_action_usd"] == 0
            and receipt["frozen_control_count"] == 8
            and receipt["frozen_attack_count"] == 8
            and all(checks.values())
        )
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError):
        receipt = {}
        checks = {}
        passed = False
    if not passed:
        _fail(
            "rf_staging_protocol_integrity_failed",
            "Round 19 協議、事前收據或第十八輪綁定不完整",
        )
    return {
        "passed": True,
        "frozen_at": receipt["frozen_at"],
        "git_head_at_freeze": receipt["git_head_at_freeze"],
        "independent_first_seen_evidence": False,
        "hash_checks": checks,
    }


@dataclass(frozen=True)
class ParsedRiskFreeSource:
    source_sha256: str
    data_cut: str
    first_session: str
    last_session: str
    full_row_count: int
    source_member_size: int
    frame: pd.DataFrame


def _safe_archive_member(info: zipfile.ZipInfo) -> None:
    member = PurePosixPath(info.filename)
    unix_mode = info.external_attr >> 16
    if (
        info.is_dir()
        or member.is_absolute()
        or ".." in member.parts
        or "\\" in info.filename
        or (unix_mode and stat.S_ISLNK(unix_mode))
        or info.flag_bits & 0x1
        or info.file_size > MAX_ARCHIVE_MEMBER_BYTES
    ):
        _fail("rf_source_archive_unsafe", "ZIP member 不安全")


def _parse_source_text(payload: bytes, *, source_sha256: str) -> ParsedRiskFreeSource:
    try:
        text = payload.decode("utf-8-sig")
    except UnicodeDecodeError:
        _fail("rf_source_definition_mismatch", "官方 CSV 不是 UTF-8／ASCII 文字")
    lines = text.splitlines()
    header_index = next(
        (
            index
            for index, line in enumerate(lines)
            if line.replace(" ", "") == ",Mkt-RF,SMB,HML,RF"
        ),
        None,
    )
    preamble = "\n".join(lines[: header_index if header_index is not None else 0])
    data_cut_match = DATA_CUT_PATTERN.search(preamble)
    if (
        header_index is None
        or data_cut_match is None
        or "simple daily rate" not in preamble
        or "1-month TBill rate" not in preamble
    ):
        _fail(
            "rf_source_definition_mismatch",
            "官方 data cut、simple daily rate 或一個月 T-bill 定義不符",
        )

    records: list[dict[str, Any]] = []
    prior_session: datetime | None = None
    for raw in lines[header_index + 1 :]:
        if not raw.strip():
            continue
        row = next(csv.reader(io.StringIO(raw)))
        if not row or DATA_ROW_PATTERN.fullmatch(row[0].strip()) is None:
            continue
        if len(row) != 5:
            _fail("rf_source_definition_mismatch", "資料列欄數不符")
        try:
            session = datetime.strptime(row[0].strip(), "%Y%m%d")
            returns = [float(value.strip()) for value in row[1:]]
        except ValueError:
            _fail("rf_source_value_invalid", "日期或回報不是有效數值")
        if prior_session is not None and session <= prior_session:
            _fail("rf_source_session_invalid", "官方日期不是唯一且嚴格遞增")
        if not all(math.isfinite(value) for value in returns):
            _fail("rf_source_value_invalid", "官方回報包含非有限值")
        rf_decimal = returns[3] / 100.0
        if rf_decimal <= -1 or abs(rf_decimal) > 0.01:
            _fail("rf_source_value_invalid", "RF percent-to-decimal 後量級不合理")
        session_text = session.strftime("%Y-%m-%d")
        records.append(
            {
                "session": session_text,
                "risk_free_return": rf_decimal,
                "unit": RF_UNIT,
                "source_series": RF_SERIES,
                "source_record_id": (
                    f"KEN_FRENCH_FF3_DAILY_RF:{session.strftime('%Y%m%d')}:"
                    f"{source_sha256[:16]}"
                ),
            }
        )
        prior_session = session
    if not records:
        _fail("rf_source_definition_mismatch", "官方 CSV 沒有日度資料列")
    frame = pd.DataFrame.from_records(records)
    return ParsedRiskFreeSource(
        source_sha256=source_sha256,
        data_cut=data_cut_match.group(1),
        first_session=records[0]["session"],
        last_session=records[-1]["session"],
        full_row_count=len(records),
        source_member_size=len(payload),
        frame=frame,
    )


def _inspect_unfrozen_source_zip(source_zip: str | Path) -> ParsedRiskFreeSource:
    path = Path(source_zip)
    try:
        source_bytes = path.read_bytes()
    except OSError:
        _fail("rf_source_hash_mismatch", "無法讀取官方 ZIP")
    source_sha256 = _sha256_bytes(source_bytes)
    try:
        with zipfile.ZipFile(io.BytesIO(source_bytes)) as archive:
            infos = archive.infolist()
            for info in infos:
                _safe_archive_member(info)
            if len(infos) != 1 or infos[0].filename != EXPECTED_MEMBER:
                _fail(
                    "rf_source_file_set_mismatch",
                    "ZIP 必須只含固定 Fama/French daily CSV",
                )
            payload = archive.read(infos[0])
    except zipfile.BadZipFile:
        _fail("rf_source_archive_unsafe", "來源不是有效 ZIP")
    return _parse_source_text(payload, source_sha256=source_sha256)


def _inspect_source_zip(
    source_zip: str | Path,
    *,
    expected_sha256: str,
) -> ParsedRiskFreeSource:
    parsed = _inspect_unfrozen_source_zip(source_zip)
    if parsed.source_sha256 != expected_sha256:
        _fail("rf_source_hash_mismatch", "官方 ZIP SHA-256 與凍結 snapshot 不符")
    if (
        parsed.data_cut != EXPECTED_DATA_CUT
        or parsed.last_session != EXPECTED_SOURCE_LAST_SESSION
    ):
        _fail("rf_source_definition_mismatch", "data cut 或最後日期與凍結來源不符")
    return parsed


def probe_official_rf_zip(
    source_zip: str | Path,
    *,
    root: str | Path,
) -> dict[str, Any]:
    """Inspect the current official URL without qualifying a new source snapshot."""

    protocol = _protocol_integrity(root)
    parsed = _inspect_unfrozen_source_zip(source_zip)
    required_sessions = list(
        pd.DatetimeIndex(
            xcals.get_calendar("XNYS", start=STUDY_START, end=STUDY_END)
            .sessions_in_range(STUDY_START, STUDY_END)
            .tz_localize(None)
        ).strftime("%Y-%m-%d")
    )
    if len(required_sessions) != EXPECTED_STUDY_SESSION_COUNT:
        _fail("rf_source_session_invalid", "XNYS 固定研究 session 數漂移")
    required_set = set(required_sessions)
    source_sessions = set(parsed.frame["session"])
    available = [session for session in required_sessions if session in source_sessions]
    missing = [session for session in required_sessions if session not in source_sessions]
    extra = sorted(
        session
        for session in source_sessions
        if STUDY_START <= session <= STUDY_END and session not in required_set
    )
    matches_frozen = bool(
        parsed.source_sha256 == EXPECTED_SOURCE_SHA256
        and parsed.data_cut == EXPECTED_DATA_CUT
        and parsed.last_session == EXPECTED_SOURCE_LAST_SESSION
    )
    if matches_frozen:
        status = "matches_frozen_source"
    elif parsed.last_session <= EXPECTED_SOURCE_LAST_SESSION:
        status = "source_changed_without_new_coverage_manual_review_required"
    elif parsed.last_session < STUDY_END or missing:
        status = "newer_source_detected_still_incomplete_manual_freeze_required"
    else:
        status = "candidate_full_coverage_detected_manual_freeze_and_license_review_required"
    return {
        "schema_version": 1,
        "research_round": 19,
        "probe_version": "round19-official-risk-free-source-probe-v1",
        "status": status,
        "protocol_sha256": PROTOCOL_SHA256,
        "protocol_integrity_passed": protocol["passed"],
        "source_url": SOURCE_URL,
        "source_sha256": parsed.source_sha256,
        "data_cut": parsed.data_cut,
        "last_session": parsed.last_session,
        "matches_frozen_source": matches_frozen,
        "frozen_source_sha256": EXPECTED_SOURCE_SHA256,
        "frozen_data_cut": EXPECTED_DATA_CUT,
        "frozen_last_session": EXPECTED_SOURCE_LAST_SESSION,
        "study": {
            "calendar": "XNYS",
            "start": STUDY_START,
            "end": STUDY_END,
            "required_sessions": len(required_sessions),
            "available_sessions": len(available),
            "missing_session_count": len(missing),
            "first_missing_session": missing[0] if missing else None,
            "last_missing_session": missing[-1] if missing else None,
            "extra_session_count": len(extra),
        },
        "new_source_qualified": False,
        "formal_rf_input_ready": False,
        "formal_backtest_authorized": False,
        "strategy_run_count": 0,
        "paper_authorized": False,
        "paper_state": "all_cash",
        "real_money_action_usd": 0,
        "next_action": (
            "來源 hash 或覆蓋變更時另行凍結並人工核對定義、授權、session 與收據；"
            "每日 probe 不會自行升級正式 RF。"
        ),
    }


def inspect_official_rf_zip(
    source_zip: str | Path,
    *,
    root: str | Path,
) -> dict[str, Any]:
    protocol = _protocol_integrity(root)
    parsed = _inspect_source_zip(
        source_zip,
        expected_sha256=EXPECTED_SOURCE_SHA256,
    )
    required = pd.DatetimeIndex(
        xcals.get_calendar("XNYS", start=STUDY_START, end=STUDY_END)
        .sessions_in_range(STUDY_START, STUDY_END)
        .tz_localize(None)
    ).strftime("%Y-%m-%d")
    required_sessions = list(required)
    if len(required_sessions) != EXPECTED_STUDY_SESSION_COUNT:
        _fail("rf_source_session_invalid", "XNYS 固定研究 session 數漂移")
    source_sessions = set(parsed.frame["session"])
    required_set = set(required_sessions)
    available = [session for session in required_sessions if session in source_sessions]
    missing = [session for session in required_sessions if session not in source_sessions]
    extra = sorted(
        session
        for session in source_sessions
        if STUDY_START <= session <= STUDY_END and session not in required_set
    )
    if len(missing) != EXPECTED_MISSING_SESSION_COUNT or extra:
        _fail("rf_source_session_invalid", "官方來源與凍結的 22-session 缺口不符")
    selected = parsed.frame.loc[
        parsed.frame["session"].isin(required_set),
        [
            "session",
            "risk_free_return",
            "unit",
            "source_series",
            "source_record_id",
        ],
    ].copy()
    selected = selected.set_index("session").loc[available].reset_index()
    if selected["source_record_id"].duplicated().any():
        _fail("rf_source_session_invalid", "來源 record ID 不唯一")
    return {
        "protocol": protocol,
        "source": {
            "url": SOURCE_URL,
            "page_url": SOURCE_PAGE_URL,
            "details_url": SOURCE_DETAILS_URL,
            "sha256": parsed.source_sha256,
            "member": EXPECTED_MEMBER,
            "member_bytes": parsed.source_member_size,
            "data_cut": parsed.data_cut,
            "full_first_session": parsed.first_session,
            "full_last_session": parsed.last_session,
            "full_row_count": parsed.full_row_count,
            "economic_definition": (
                "simple daily rate compounded over trading days to the one-month "
                "Treasury bill return"
            ),
            "source_access": "public_download",
            "explicit_local_research_license_evidence_captured": False,
        },
        "study": {
            "calendar": "XNYS",
            "start": STUDY_START,
            "end": STUDY_END,
            "required_sessions": len(required_sessions),
            "available_sessions": len(available),
            "missing_sessions": missing,
            "missing_session_count": len(missing),
            "extra_sessions": extra,
            "extra_session_count": len(extra),
            "coverage_fraction": len(available) / len(required_sessions),
            "first_available_session": available[0],
            "last_available_session": available[-1],
        },
        "frame": selected,
    }


def _validate_staging_path(output_dir: str | Path, *, root: str | Path) -> Path:
    path = Path(output_dir)
    root_path = Path(root).resolve()
    if not path.is_absolute() or path.exists() or path.is_symlink():
        _fail("rf_staging_path_invalid", "暫存輸出須是未存在的絕對路徑")
    resolved = path.resolve(strict=False)
    if resolved == root_path or root_path in resolved.parents:
        _fail("rf_staging_path_invalid", "暫存輸出不可位於 repository 內")
    parent = resolved.parent
    parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    parent.chmod(0o700)
    if parent.is_symlink() or stat.S_IMODE(parent.stat().st_mode) & 0o077:
        _fail("rf_staging_path_invalid", "暫存 parent 必須 owner-only 且不是 symlink")
    return resolved


def _enforce_decision_boundary(
    *,
    missing_sessions: list[str],
    request_formal_manifest: bool,
) -> None:
    if missing_sessions and request_formal_manifest:
        _fail(
            "rf_decision_boundary_violation",
            "RF 尚缺 session，不得生成正式 manifest 或授權回測",
        )


def stage_official_rf_snapshot(
    source_zip: str | Path,
    output_dir: str | Path,
    *,
    root: str | Path,
    request_formal_manifest: bool = False,
) -> dict[str, Any]:
    root_path = Path(root).resolve()
    output = _validate_staging_path(output_dir, root=root_path)
    audit = inspect_official_rf_zip(source_zip, root=root_path)
    missing = audit["study"]["missing_sessions"]
    _enforce_decision_boundary(
        missing_sessions=missing,
        request_formal_manifest=request_formal_manifest,
    )
    temporary = Path(
        tempfile.mkdtemp(prefix=f".{output.name}.tmp-", dir=str(output.parent))
    )
    temporary.chmod(0o700)
    try:
        source_destination = temporary / "source_snapshot.zip"
        shutil.copyfile(source_zip, source_destination)
        source_destination.chmod(0o600)

        partial_path = temporary / "risk_free_daily_partial.csv"
        audit["frame"].to_csv(
            partial_path,
            index=False,
            lineterminator="\n",
            float_format="%.8f",
        )
        partial_path.chmod(0o600)

        missing_path = temporary / "missing_sessions.csv"
        pd.DataFrame({"session": missing}).to_csv(
            missing_path,
            index=False,
            lineterminator="\n",
        )
        missing_path.chmod(0o600)

        manifest = {
            "schema_version": 1,
            "staging_version": STAGING_VERSION,
            "status": "incomplete_missing_formal_tail",
            "protocol_sha256": PROTOCOL_SHA256,
            "parent_formal_protocol_sha256": PARENT_PROTOCOL_SHA256,
            "source": audit["source"],
            "study": audit["study"],
            "conversion": {
                "source_unit": "percent_simple_daily_return",
                "operation": "divide_by_100_exactly_once",
                "output_unit": RF_UNIT,
                "source_series": RF_SERIES,
                "missing_value_policy": "reject_no_fill_no_interpolation",
            },
            "license_evidence": {
                "public_download": True,
                "explicit_local_research_license_evidence_captured": False,
                "formal_license_gate_passed": False,
            },
            "formal_manifest_generated": False,
            "formal_rf_input_ready": False,
            "formal_backtest_authorized": False,
            "paper_authorized": False,
            "paper_state": "all_cash",
            "real_money_action_usd": 0,
        }
        manifest_path = temporary / "availability_manifest.json"
        _write_json(manifest_path, manifest)
        manifest_path.chmod(0o600)

        file_receipts = {
            path.name: {
                "sha256": _sha256_file(path),
                "bytes": path.stat().st_size,
            }
            for path in (
                source_destination,
                partial_path,
                missing_path,
                manifest_path,
            )
        }
        receipt = {
            "schema_version": 1,
            "staging_version": STAGING_VERSION,
            "status": "owner_only_partial_staging_complete_formal_input_blocked",
            "protocol_sha256": PROTOCOL_SHA256,
            "source_sha256": EXPECTED_SOURCE_SHA256,
            "files": file_receipts,
            "owner_only_required": True,
            "symlinks_allowed": False,
            "formal_manifest_generated": False,
            "formal_backtest_authorized": False,
            "strategy_run_count": 0,
            "paper_authorized": False,
            "paper_state": "all_cash",
            "real_money_action_usd": 0,
        }
        receipt_path = temporary / "staging_receipt.json"
        _write_json(receipt_path, receipt)
        receipt_path.chmod(0o600)
        os.replace(temporary, output)
        output.chmod(0o700)
    except BaseException:
        if temporary.exists():
            shutil.rmtree(temporary)
        raise

    expected_files = {
        "source_snapshot.zip",
        "risk_free_daily_partial.csv",
        "missing_sessions.csv",
        "availability_manifest.json",
        "staging_receipt.json",
    }
    actual_files = {path.name for path in output.iterdir()}
    owner_only = bool(
        stat.S_IMODE(output.stat().st_mode) == 0o700
        and all(
            path.is_file()
            and not path.is_symlink()
            and stat.S_IMODE(path.stat().st_mode) == 0o600
            for path in output.iterdir()
        )
    )
    if actual_files != expected_files or not owner_only:
        _fail("rf_staging_path_invalid", "暫存檔案集合或權限不符")
    return {
        "staging_version": STAGING_VERSION,
        "status": "owner_only_partial_staging_complete_formal_input_blocked",
        "file_set": sorted(actual_files),
        "owner_only": True,
        "source_sha256": audit["source"]["sha256"],
        "data_cut": audit["source"]["data_cut"],
        "study": audit["study"],
        "formal_manifest_generated": False,
        "formal_rf_input_ready": False,
        "formal_backtest_authorized": False,
        "strategy_run_count": 0,
        "paper": {
            "authorized": False,
            "state": "all_cash",
            "backfilled_trades": 0,
            "positions": [],
        },
        "real_money_action_usd": 0,
    }
