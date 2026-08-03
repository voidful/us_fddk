from __future__ import annotations

import hashlib
import json
import math
import re
import shutil
import subprocess
import tempfile
import urllib.request
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from usfddk.data import load_snapshot, panel_fingerprint

V11_PROTOCOL_SHA256 = "8611faeec584a78e096df817eeb7ea9a0ce28c71d4c37c4a00c44637ff6644d5"
V11_DATA_CONTRACT_SHA256 = (
    "fe5d805ad79f71646217319a3c5616d8bedd3422f807ce96883e034824212382"
)
V11_OFFICIAL_URL = (
    "https://www.spglobal.com/spdji/en/web-data-downloads/reports/"
    "dja-performance-report-daily.xls?force_download=true"
)
V11_SOURCE_PAGE = (
    "https://www.spglobal.com/spdji/en/indices/equity/"
    "dow-jones-industrial-average/"
)
V11_START = "1971-02-05"
V11_FORMAL_START = "1973-01-03"
V11_END = "1988-12-30"
V11_IXIC_PANEL_SHA256 = "76bc29b61c480e8c44032e4aeaea801e9ea97a1aebceb758bda84df8a8b7d2c9"
V11_IXIC_ARCHIVE_SHA256 = (
    "b845aecd3175584f8dc40e0db8e93ec9427e2a9f491f0824ec7264f6cda9eb22"
)


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _file_sha256(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace(
        "+00:00", "Z"
    )


def _normalized_header(value: Any) -> str:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return ""
    return re.sub(r"\s+", " ", str(value).strip().lower())


def _calendar_day(value: Any) -> pd.Timestamp | pd.NaT:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return pd.NaT
    if isinstance(value, (pd.Timestamp, datetime, date)):
        stamp = pd.Timestamp(value)
    elif isinstance(value, (int, float, np.integer, np.floating)):
        numeric = float(value)
        if not np.isfinite(numeric) or numeric < 1 or numeric > 100_000:
            return pd.NaT
        stamp = pd.Timestamp("1899-12-30") + pd.to_timedelta(numeric, unit="D")
    else:
        text = str(value).strip()
        if not text:
            return pd.NaT
        stamp = pd.to_datetime(text, errors="coerce")
        if pd.isna(stamp):
            return pd.NaT
    if getattr(stamp, "tzinfo", None) is not None:
        stamp = stamp.tz_localize(None)
    return pd.Timestamp(stamp).normalize()


def _positive_number(value: Any) -> float:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return float("nan")
    if isinstance(value, str):
        value = value.strip().replace(",", "")
    try:
        number = float(value)
    except (TypeError, ValueError):
        return float("nan")
    return number if np.isfinite(number) and number > 0.0 else float("nan")


def _candidate_from_columns(
    frame: pd.DataFrame,
    *,
    sheet: str,
    header_row: int,
    date_col: int,
    value_col: int,
) -> tuple[pd.Series | None, dict[str, Any]]:
    rows: list[tuple[pd.Timestamp, float]] = []
    for date_value, index_value in zip(
        frame.iloc[header_row + 1 :, date_col],
        frame.iloc[header_row + 1 :, value_col],
        strict=False,
    ):
        parsed_date = _calendar_day(date_value)
        parsed_value = _positive_number(index_value)
        if pd.isna(parsed_date) or not np.isfinite(parsed_value):
            continue
        rows.append((pd.Timestamp(parsed_date), float(parsed_value)))

    metadata: dict[str, Any] = {
        "sheet": sheet,
        "header_row_zero_based": int(header_row),
        "header_row_excel": int(header_row + 1),
        "date_column_zero_based": int(date_col),
        "value_column_zero_based": int(value_col),
        "date_header": str(frame.iat[header_row, date_col]),
        "value_header": str(frame.iat[header_row, value_col]),
        "parseable_rows": int(len(rows)),
    }
    if not rows:
        metadata["eligible"] = False
        metadata["reason"] = "no parseable positive date/value rows"
        return None, metadata

    parsed = pd.DataFrame(rows, columns=["Date", "DJIA"])
    conflicting = (
        parsed.groupby("Date", sort=False)["DJIA"].nunique(dropna=True) > 1
    )
    conflict_dates = [
        pd.Timestamp(item).strftime("%Y-%m-%d")
        for item in conflicting.index[conflicting]
    ]
    metadata["conflicting_duplicate_dates"] = conflict_dates[:20]
    if conflict_dates:
        metadata["eligible"] = False
        metadata["reason"] = "same date has conflicting index levels"
        return None, metadata

    series = (
        parsed.drop_duplicates(subset=["Date"], keep="first")
        .set_index("Date")["DJIA"]
        .sort_index()
        .astype(float)
    )
    start = pd.Timestamp(V11_START)
    end = pd.Timestamp(V11_END)
    sliced = series.loc[start:end]
    metadata.update(
        {
            "unique_rows": int(len(series)),
            "parsed_start": series.index[0].strftime("%Y-%m-%d"),
            "parsed_end": series.index[-1].strftime("%Y-%m-%d"),
            "slice_rows": int(len(sliced)),
            "slice_start": (
                sliced.index[0].strftime("%Y-%m-%d") if len(sliced) else None
            ),
            "slice_end": (
                sliced.index[-1].strftime("%Y-%m-%d") if len(sliced) else None
            ),
        }
    )
    eligible = bool(
        len(sliced) >= 4_300
        and len(sliced)
        and sliced.index[0] == start
        and sliced.index[-1] == end
    )
    metadata["eligible"] = eligible
    metadata["reason"] = "eligible" if eligible else "coverage or row threshold failed"
    return (sliced if eligible else None), metadata


def parse_official_djia_workbook(
    workbook_path: str | Path,
) -> tuple[pd.Series, dict[str, Any]]:
    """Scan every worksheet/header pair exactly as the frozen v11 contract states."""
    sheets = pd.read_excel(
        Path(workbook_path), sheet_name=None, header=None, engine="openpyxl"
    )
    eligible: list[tuple[pd.Series, dict[str, Any]]] = []
    scanned: list[dict[str, Any]] = []
    value_terms = ("close", "index level", "djia", "dow jones industrial average")
    for sheet, frame in sheets.items():
        for header_row in range(len(frame)):
            headers = [_normalized_header(value) for value in frame.iloc[header_row]]
            date_columns = [
                index for index, header in enumerate(headers) if "date" in header
            ]
            value_columns = [
                index
                for index, header in enumerate(headers)
                if any(term in header for term in value_terms)
            ]
            for date_col in date_columns:
                for value_col in value_columns:
                    if date_col == value_col:
                        continue
                    candidate, metadata = _candidate_from_columns(
                        frame,
                        sheet=str(sheet),
                        header_row=header_row,
                        date_col=date_col,
                        value_col=value_col,
                    )
                    scanned.append(metadata)
                    if candidate is not None:
                        eligible.append((candidate, metadata))
    if len(eligible) != 1:
        raise ValueError(
            "官方活頁簿符合凍結涵蓋條件的日期／DJIA 欄位候選必須恰為 1 個，"
            f"實際為 {len(eligible)} 個"
        )
    selected, selected_metadata = eligible[0]
    audit = {
        "sheet_names": [str(sheet) for sheet in sheets],
        "worksheet_count": int(len(sheets)),
        "header_candidates_scanned": int(len(scanned)),
        "eligible_candidate_count": int(len(eligible)),
        "selected": selected_metadata,
        "candidates": scanned,
    }
    return selected, audit


def _csv_bytes(series: pd.Series) -> bytes:
    frame = series.rename("DJIA").rename_axis("Date").reset_index()
    text = frame.to_csv(
        index=False,
        date_format="%Y-%m-%d",
        float_format="%.10g",
        lineterminator="\n",
    )
    return text.encode("utf-8")


def _common_close_bytes(common: pd.DataFrame) -> bytes:
    frame = common.rename_axis("Date").reset_index()
    text = frame.to_csv(
        index=False,
        date_format="%Y-%m-%d",
        float_format="%.10g",
        lineterminator="\n",
    )
    return text.encode("utf-8")


def _base_receipt(protocol_sha256: str, data_contract_sha256: str) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "recorded_at": _utc_now(),
        "protocol": {
            "path": "docs/V11_HIERARCHICAL_DEFENSE_OFFICIAL_DJI_PROTOCOL.md",
            "sha256": protocol_sha256,
        },
        "data_contract": {
            "path": "docs/V11_OFFICIAL_DJI_DATA_CONTRACT.md",
            "sha256": data_contract_sha256,
        },
        "request": {
            "source_page": V11_SOURCE_PAGE,
            "url": V11_OFFICIAL_URL,
            "http_method": "GET",
            "application_get_calls": 1,
            "provider": "S&P Dow Jones Indices official web data download",
        },
    }


def _failure_receipt(
    base: dict[str, Any],
    *,
    stage: str,
    error: Exception,
    raw: dict[str, Any] | None = None,
    http: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        **base,
        "status": "data_contract_failed",
        **({"http": http} if http is not None else {}),
        **({"raw_file": raw} if raw is not None else {}),
        "result": {
            "contract_ok": False,
            "failure_stage": stage,
            "error_type": type(error).__name__,
            "error": str(error),
        },
        "decision": {
            "data_gate_30": False,
            "v11_calculation_may_start": False,
            "paper_eligible": False,
            "paper_created": False,
            "fallback_provider_allowed": False,
        },
    }


def fetch_and_freeze_v11_official_djia(
    output_dir: str | Path,
    *,
    ixic_snapshot: str | Path,
    protocol_sha256: str,
    data_contract_sha256: str,
    soffice_path: str | None = None,
) -> tuple[dict[str, Any], bool]:
    """Perform the single official GET, preserve raw bytes, parse, and hard-check."""
    if protocol_sha256 != V11_PROTOCOL_SHA256:
        raise ValueError("v11 協議雜湊與首次官方下載前凍結版本不同")
    if data_contract_sha256 != V11_DATA_CONTRACT_SHA256:
        raise ValueError("v11 官方 DJIA 資料契約雜湊與首次下載前凍結版本不同")

    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    existing = sorted(destination.glob("v11_spdji_djia_daily_*.xls")) + sorted(
        destination.glob("v11_spdji_djia_close_19710205_19881230_*.csv")
    )
    if existing:
        raise ValueError(
            "v11 官方 DJIA 原始或解析檔已存在，已在連網前拒絕重新下載、覆寫或改寫"
        )

    base = _base_receipt(protocol_sha256, data_contract_sha256)
    raw_receipt: dict[str, Any] | None = None
    http_receipt: dict[str, Any] | None = None
    try:
        request = urllib.request.Request(
            V11_OFFICIAL_URL,
            method="GET",
            headers={
                "User-Agent": "Mozilla/5.0 (compatible; USFDDK-Research/0.1)",
                "Accept": "application/vnd.ms-excel,application/octet-stream;q=0.9,*/*;q=0.1",
            },
        )
        downloaded_at = _utc_now()
        with urllib.request.urlopen(request, timeout=120) as response:
            payload = response.read()
            http_receipt = {
                "status": int(getattr(response, "status", response.getcode())),
                "final_url": str(response.geturl()),
                "content_type": str(response.headers.get("Content-Type", "")),
                "downloaded_at": downloaded_at,
                "byte_size": int(len(payload)),
            }
        if http_receipt["status"] < 200 or http_receipt["status"] >= 300:
            raise ValueError(f"官方下載 HTTP 狀態不是成功：{http_receipt['status']}")
        if not payload:
            raise ValueError("官方下載回應為空")
    except Exception as exc:
        return _failure_receipt(
            base, stage="official_http_get", error=exc, http=http_receipt
        ), False

    raw_sha256 = _sha256_bytes(payload)
    raw_path = destination / f"v11_spdji_djia_daily_{raw_sha256[:8]}.xls"
    raw_path.write_bytes(payload)
    raw_receipt = {
        "path": str(raw_path),
        "sha256": raw_sha256,
        "byte_size": int(len(payload)),
    }

    try:
        office = soffice_path or shutil.which("soffice")
        if not office:
            raise RuntimeError("找不到可驗證舊式 .xls 的 LibreOffice reader")
        with tempfile.TemporaryDirectory(prefix="usfddk-v11-xls-") as temporary:
            temporary_path = Path(temporary)
            staged_xls = temporary_path / "official_djia.xls"
            staged_xls.write_bytes(payload)
            converted_dir = temporary_path / "converted"
            converted_dir.mkdir()
            conversion = subprocess.run(
                [
                    office,
                    "--headless",
                    "--convert-to",
                    "xlsx",
                    "--outdir",
                    str(converted_dir),
                    str(staged_xls),
                ],
                check=False,
                capture_output=True,
                text=True,
                timeout=120,
            )
            converted = converted_dir / "official_djia.xlsx"
            if conversion.returncode != 0 or not converted.exists():
                detail = (conversion.stderr or conversion.stdout).strip()
                raise ValueError(f"LibreOffice 無法開啟官方 .xls：{detail}")
            series, parser_audit = parse_official_djia_workbook(converted)
    except Exception as exc:
        return _failure_receipt(
            base,
            stage="excel_open_or_automatic_parse",
            error=exc,
            raw=raw_receipt,
            http=http_receipt,
        ), False

    try:
        checks: dict[str, bool] = {}
        start = pd.Timestamp(V11_START)
        end = pd.Timestamp(V11_END)
        checks["parsed_dates_monotonic_unique"] = bool(
            series.index.is_monotonic_increasing and not series.index.has_duplicates
        )
        checks["parsed_exact_boundaries"] = bool(
            len(series) and series.index[0] == start and series.index[-1] == end
        )
        checks["parsed_rows_at_least_4300"] = bool(len(series) >= 4_300)
        values = series.to_numpy(dtype=float)
        checks["parsed_finite_positive_no_missing"] = bool(
            len(values)
            and np.isfinite(values).all()
            and (values > 0.0).all()
            and not series.isna().any()
        )
        max_move = float(series.pct_change(fill_method=None).abs().max())
        checks["parsed_max_absolute_daily_return_at_most_35pct"] = bool(
            max_move <= 0.35
        )

        ixic_path = Path(ixic_snapshot)
        ixic_panel, ixic_manifest = load_snapshot(ixic_path)
        ixic_panel_sha256 = panel_fingerprint(ixic_panel)
        ixic_archive_sha256 = _file_sha256(ixic_path)
        checks["frozen_ixic_panel_hash_matches"] = bool(
            ixic_panel_sha256 == V11_IXIC_PANEL_SHA256
        )
        checks["frozen_ixic_archive_hash_matches"] = bool(
            ixic_archive_sha256 == V11_IXIC_ARCHIVE_SHA256
        )
        checks["frozen_ixic_has_exact_column"] = bool(
            list(ixic_panel.close.columns) == ["^IXIC"]
        )

        common_index = series.index.intersection(ixic_panel.close.index).sort_values()
        common = pd.concat(
            [
                series.loc[common_index].rename("DJIA"),
                ixic_panel.close.loc[common_index, "^IXIC"].rename("^IXIC"),
            ],
            axis=1,
        )
        checks["common_dates_monotonic_unique"] = bool(
            common.index.is_monotonic_increasing and not common.index.has_duplicates
        )
        checks["common_exact_boundaries"] = bool(
            len(common)
            and common.index[0] == start
            and common.index[-1] == end
        )
        checks["common_rows_at_least_4300"] = bool(len(common) >= 4_300)
        checks["common_no_missing_finite_positive"] = bool(
            not common.isna().any().any()
            and np.isfinite(common.to_numpy(dtype=float)).all()
            and (common.to_numpy(dtype=float) > 0.0).all()
        )
        warmup_sessions = int(
            (common.index < pd.Timestamp(V11_FORMAL_START)).sum()
        )
        checks["common_warmup_at_least_252"] = bool(warmup_sessions >= 252)
        required_boundaries = (
            "1973-01-03",
            "1980-12-31",
            "1981-01-02",
            "1988-12-30",
        )
        checks["common_required_boundaries_present"] = bool(
            all(pd.Timestamp(item) in common.index for item in required_boundaries)
        )
        if not all(checks.values()):
            failed = [name for name, passed in checks.items() if not passed]
            raise ValueError("官方資料硬檢查未通過：" + ", ".join(failed))

        csv_payload = _csv_bytes(series)
        csv_sha256 = _sha256_bytes(csv_payload)
        csv_path = destination / (
            "v11_spdji_djia_close_19710205_19881230_"
            f"{csv_sha256[:8]}.csv"
        )
        csv_path.write_bytes(csv_payload)
        common_payload = _common_close_bytes(common)
        receipt = {
            **base,
            "status": "data_contract_passed",
            "http": http_receipt,
            "raw_file": raw_receipt,
            "excel_reader": {
                "application": "LibreOffice headless",
                "executable": str(office),
                "intermediate_xlsx_persisted": False,
            },
            "automatic_parser": parser_audit,
            "parsed_csv": {
                "path": str(csv_path),
                "sha256": csv_sha256,
                "byte_size": int(len(csv_payload)),
                "columns": ["Date", "DJIA"],
                "rows": int(len(series)),
                "start": series.index[0].strftime("%Y-%m-%d"),
                "end": series.index[-1].strftime("%Y-%m-%d"),
                "max_absolute_daily_return": max_move,
            },
            "frozen_ixic_snapshot": {
                "path": str(ixic_path),
                "panel_sha256": ixic_panel_sha256,
                "archive_sha256": ixic_archive_sha256,
                "rows": int(ixic_manifest["rows"]),
                "start": str(ixic_manifest["start"]),
                "end": str(ixic_manifest["end"]),
            },
            "derived_common_close_panel": {
                "sha256": _sha256_bytes(common_payload),
                "columns": ["DJIA", "^IXIC"],
                "rows": int(len(common)),
                "start": common.index[0].strftime("%Y-%m-%d"),
                "end": common.index[-1].strftime("%Y-%m-%d"),
                "warmup_common_sessions": warmup_sessions,
                "join": "date intersection only; no fill, interpolation, shift, or splice",
            },
            "contract": {"ok": True, "checks": checks},
            "decision": {
                "data_gate_30_component": True,
                "v11_calculation_may_start": True,
                "paper_eligible": False,
                "paper_created": False,
                "fallback_provider_allowed": False,
            },
        }
        json.dumps(receipt, ensure_ascii=False, allow_nan=False)
        return receipt, True
    except Exception as exc:
        return _failure_receipt(
            base,
            stage="price_common_date_or_hash_contract",
            error=exc,
            raw=raw_receipt,
            http=http_receipt,
        ), False
