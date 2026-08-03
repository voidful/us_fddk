from __future__ import annotations

import csv
import hashlib
import io
import json
import re
import shutil
import tempfile
import urllib.request
import zipfile
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / "artifacts"
PROTOCOL = ROOT / "docs/SHORT_TERM_FRENCH_INDUSTRY_MOMENTUM_PROTOCOL.md"
MAPPING = ROOT / "docs/SHORT_TERM_FRENCH_INDUSTRY_DATA_MAPPING.md"
PROTOCOL_RECEIPT = ARTIFACTS / "short_term_french_industry_protocol_receipt.json"
DATA_RECEIPT = ARTIFACTS / "short_term_french_industry_data_receipt.json"

PROTOCOL_SHA256 = "538df4e867dd807db55a7076cdba5015191f1f60e3cc63a7b25de5a393175510"
MAPPING_SHA256 = "abad4423b0463a7f88174359ba868e6eea17a119e62cce5913502d1e535f73e8"
PROTOCOL_COMMIT = "8d0979c392e86100eaa95f3212a0c74db77b24b4"
FORMAL_START_FLOOR = pd.Timestamp("1963-01-01")
FORMAL_START_CEILING = pd.Timestamp("1970-12-31")
LOOKBACK_SESSIONS = 126
MISSING_CODES = {-99.99, -999.0}
DATE_PATTERN = re.compile(r"^\d{8}$")

SOURCES = {
    "industry_49": (
        "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/"
        "49_Industry_Portfolios_Daily_CSV.zip"
    ),
    "ff_factors": (
        "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/"
        "F-F_Research_Data_Factors_daily_CSV.zip"
    ),
    "momentum": (
        "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/"
        "F-F_Momentum_Factor_daily_CSV.zip"
    ),
}


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _write_json(path: Path, payload: dict) -> None:
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def _download_once(url: str) -> bytes:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "us-fddk-research-snapshot/1.0"},
    )
    with urllib.request.urlopen(request, timeout=120) as response:
        if response.status != 200:
            raise RuntimeError(f"官方下載失敗：HTTP {response.status} {url}")
        payload = response.read()
    if not payload:
        raise RuntimeError(f"官方下載為空：{url}")
    return payload


def _extract_single_csv(archive: bytes) -> tuple[str, str]:
    with zipfile.ZipFile(io.BytesIO(archive)) as bundle:
        members = [
            name
            for name in bundle.namelist()
            if not name.endswith("/") and name.lower().endswith(".csv")
        ]
        if len(members) != 1:
            raise RuntimeError(f"ZIP 必須只有一個 CSV member，實際為 {members}")
        member = members[0]
        raw = bundle.read(member)
    for encoding in ("utf-8-sig", "latin-1"):
        try:
            return member, raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise RuntimeError(f"CSV 編碼無法辨識：{member}")


def _locate_header(
    rows: list[list[str]],
    required: set[str] | None,
    expected_columns: int | None,
    marker: str | None,
) -> int:
    start = 0
    if marker is not None:
        marker_rows = [
            index
            for index, row in enumerate(rows)
            if marker in " ".join(cell.strip() for cell in row)
        ]
        if not marker_rows:
            raise RuntimeError(f"找不到 French 表格標記：{marker}")
        start = marker_rows[0] + 1
    for index in range(start, len(rows)):
        values = [cell.strip() for cell in rows[index]]
        names = [value for value in values[1:] if value]
        if required is not None and required.issubset(set(names)):
            return index
        if expected_columns is not None and len(names) == expected_columns:
            return index
    raise RuntimeError("找不到 French 日資料欄名")


def _parse_table(
    text: str,
    *,
    required: set[str] | None = None,
    expected_columns: int | None = None,
    marker: str | None = None,
) -> tuple[pd.DataFrame, dict]:
    rows = list(csv.reader(io.StringIO(text)))
    header_index = _locate_header(rows, required, expected_columns, marker)
    columns = [value.strip() for value in rows[header_index][1:] if value.strip()]
    if expected_columns is not None and len(columns) != expected_columns:
        raise RuntimeError(f"French 欄數錯誤：{len(columns)} != {expected_columns}")
    if len(set(columns)) != len(columns):
        raise RuntimeError("French 欄名重複")

    dates: list[pd.Timestamp] = []
    values: list[list[float]] = []
    missing_by_column = {column: 0 for column in columns}
    missing_first: str | None = None
    missing_last: str | None = None
    started = False
    for row in rows[header_index + 1 :]:
        date_value = row[0].strip() if row else ""
        if not DATE_PATTERN.fullmatch(date_value):
            if started:
                break
            continue
        started = True
        cells = [cell.strip() for cell in row[1 : len(columns) + 1]]
        if len(cells) != len(columns):
            raise RuntimeError(f"{date_value} 欄數不足")
        parsed: list[float] = []
        for column, cell in zip(columns, cells, strict=True):
            try:
                raw_value = float(cell)
            except ValueError:
                raw_value = np.nan
            if not np.isfinite(raw_value) or raw_value in MISSING_CODES:
                parsed.append(np.nan)
                missing_by_column[column] += 1
                missing_first = missing_first or date_value
                missing_last = date_value
            else:
                parsed.append(raw_value / 100.0)
        dates.append(pd.to_datetime(date_value, format="%Y%m%d"))
        values.append(parsed)
    if not dates:
        raise RuntimeError("French 日資料沒有日期列")

    frame = pd.DataFrame(values, index=pd.DatetimeIndex(dates), columns=columns)
    if frame.index.has_duplicates:
        raise RuntimeError("French 日資料有重複日期")
    if not frame.index.is_monotonic_increasing:
        raise RuntimeError("French 日資料日期並非嚴格遞增")
    meta = {
        "columns": columns,
        "rows": int(len(frame)),
        "start": frame.index[0].date().isoformat(),
        "end": frame.index[-1].date().isoformat(),
        "missing_cells": int(frame.isna().sum().sum()),
        "missing_by_column": missing_by_column,
        "missing_first": missing_first,
        "missing_last": missing_last,
        "maximum_absolute_daily_return": float(frame.abs().max().max()),
    }
    return frame, meta


def _formal_start(industry: pd.DataFrame, common_index: pd.DatetimeIndex) -> pd.Timestamp | None:
    aligned = industry.reindex(common_index)
    rolling_complete = aligned.notna().rolling(LOOKBACK_SESSIONS).sum().eq(
        LOOKBACK_SESSIONS
    )
    candidates = common_index[
        (common_index >= FORMAL_START_FLOOR) & rolling_complete.all(axis=1).to_numpy()
    ]
    return candidates[0] if len(candidates) else None


def _safe_date(value: pd.Timestamp | None) -> str | None:
    return value.date().isoformat() if value is not None else None


def main() -> int:
    receipt = json.loads(PROTOCOL_RECEIPT.read_text(encoding="utf-8"))
    if _sha256(PROTOCOL) != PROTOCOL_SHA256:
        raise RuntimeError("French 49 行業協議已在首次下載前改變")
    if _sha256(MAPPING) != MAPPING_SHA256:
        raise RuntimeError("French 49 行業數據映射已在首次下載前改變")
    if receipt.get("downloads_started") is not False:
        raise RuntimeError("French 49 協議收據不是未下載狀態")
    if receipt.get("calculation_started") is not False:
        raise RuntimeError("French 49 協議收據不是未計算狀態")
    if receipt.get("protocol_sha256") != PROTOCOL_SHA256:
        raise RuntimeError("French 49 協議收據雜湊不符")
    if receipt.get("mapping_sha256") != MAPPING_SHA256:
        raise RuntimeError("French 49 映射收據雜湊不符")

    existing = list(ARTIFACTS.glob("french_49_industry_daily_*.zip"))
    existing += list(ARTIFACTS.glob("french_ff_factors_daily_*.zip"))
    existing += list(ARTIFACTS.glob("french_momentum_daily_*.zip"))
    if existing or DATA_RECEIPT.exists():
        raise RuntimeError(f"拒絕重複下載 French 日資料：{existing}")

    downloaded_at = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    with tempfile.TemporaryDirectory(prefix="usfddk-french-daily-") as temporary_name:
        temporary = Path(temporary_name)
        archives: dict[str, bytes] = {}
        for role, url in SOURCES.items():
            archives[role] = _download_once(url)
            (temporary / f"{role}.zip").write_bytes(archives[role])

        extracted = {role: _extract_single_csv(value) for role, value in archives.items()}
        industry, industry_meta = _parse_table(
            extracted["industry_49"][1],
            expected_columns=49,
            marker="Average Value Weighted Returns -- Daily",
        )
        factors, factors_meta = _parse_table(
            extracted["ff_factors"][1],
            required={"Mkt-RF", "RF"},
        )
        momentum, momentum_meta = _parse_table(
            extracted["momentum"][1],
            required={"Mom"},
        )

        common_index = industry.index.intersection(factors.index).intersection(momentum.index)
        common_index = common_index.sort_values()
        start = _formal_start(industry, common_index)
        formal_industry = industry.reindex(common_index).loc[start:] if start is not None else industry.iloc[:0]
        formal_factors = factors.reindex(common_index).loc[start:] if start is not None else factors.iloc[:0]
        formal_momentum = momentum.reindex(common_index).loc[start:] if start is not None else momentum.iloc[:0]
        raw_start = common_index[0] if len(common_index) else None
        raw_end = common_index[-1] if len(common_index) else None

        checks = {
            "three_urls_frozen_before_first_download": True,
            "three_archives_nonempty_and_hashed": all(bool(value) for value in archives.values()),
            "raw_common_start_no_later_than_1927_01_31": bool(
                raw_start is not None and raw_start <= pd.Timestamp("1927-01-31")
            ),
            "raw_common_end_is_in_2026_05_release": bool(
                raw_end is not None and raw_end.year == 2026 and raw_end.month == 5
            ),
            "industry_columns_exactly_49": industry.shape[1] == 49,
            "formal_start_found_no_later_than_1970_12_31": bool(
                start is not None and start <= FORMAL_START_CEILING
            ),
            "formal_period_all_three_files_complete": bool(
                start is not None
                and not formal_industry.isna().any().any()
                and not formal_factors[["Mkt-RF", "RF"]].isna().any().any()
                and not formal_momentum[["Mom"]].isna().any().any()
            ),
            "missing_codes_audited_without_imputation": True,
            "all_dates_unique_and_strictly_increasing": all(
                not frame.index.has_duplicates and frame.index.is_monotonic_increasing
                for frame in (industry, factors, momentum)
            ),
            "signal_t_return_t_plus_1_rule_frozen": True,
        }

        final_names = {
            "industry_49": f"french_49_industry_daily_{_sha256_bytes(archives['industry_49'])[:8]}.zip",
            "ff_factors": f"french_ff_factors_daily_{_sha256_bytes(archives['ff_factors'])[:8]}.zip",
            "momentum": f"french_momentum_daily_{_sha256_bytes(archives['momentum'])[:8]}.zip",
        }
        for role, name in final_names.items():
            shutil.copyfile(temporary / f"{role}.zip", ARTIFACTS / name)

    archive_receipts = {
        role: {
            "url": SOURCES[role],
            "path": f"artifacts/{final_names[role]}",
            "sha256": _sha256_bytes(archives[role]),
            "size_bytes": len(archives[role]),
            "member": extracted[role][0],
        }
        for role in SOURCES
    }
    payload = {
        "status": (
            "french_industry_daily_first_download_contract_passed"
            if all(checks.values())
            else "french_industry_daily_first_download_contract_failed"
        ),
        "downloaded_at_utc": downloaded_at,
        "protocol": {
            "path": str(PROTOCOL.relative_to(ROOT)),
            "sha256": PROTOCOL_SHA256,
            "commit": PROTOCOL_COMMIT,
        },
        "mapping": {
            "path": str(MAPPING.relative_to(ROOT)),
            "sha256": MAPPING_SHA256,
        },
        "archives": archive_receipts,
        "tables": {
            "industry_49_value_weighted": industry_meta,
            "ff_factors": factors_meta,
            "momentum": momentum_meta,
        },
        "common_period": {
            "raw_start": _safe_date(raw_start),
            "raw_end": _safe_date(raw_end),
            "raw_sessions": int(len(common_index)),
            "formal_start": _safe_date(start),
            "formal_end": _safe_date(raw_end),
            "formal_sessions": int(len(formal_industry)),
        },
        "checks": checks,
        "download_performed_once": True,
        "calculation_started": False,
        "decision_boundary": {
            "paper_eligible": False,
            "paper_state_created": False,
            "trade_ready": False,
            "real_money_action_usd": 0,
        },
    }
    _write_json(DATA_RECEIPT, payload)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    if not all(checks.values()):
        raise RuntimeError("French 49 首次下載契約失敗；已保存原始 ZIP 及失敗收據，禁止重下載")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
