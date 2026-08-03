from __future__ import annotations

import hashlib
import io
import json
import math
import sys
import urllib.request
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

PROTOCOL = ROOT / "docs/SHORT_TERM_DAILY_MOMENTUM_REGIME_PROTOCOL.md"
MAPPING = ROOT / "docs/SHORT_TERM_DAILY_MOMENTUM_REGIME_DATA_MAPPING.md"
PROTOCOL_RECEIPT = (
    ROOT / "artifacts/short_term_daily_momentum_regime_protocol_receipt.json"
)
DATA_RECEIPT = ROOT / "artifacts/short_term_daily_momentum_regime_data_receipt.json"
ARTIFACTS = ROOT / "artifacts"

PROTOCOL_SHA256 = "aee1d081bcbfbd819d6c6a6a3362e241e0aab8585cb087e45fed2d1f30464cdc"
MAPPING_SHA256 = "7ee12c479383810cae133a39951a4b3b20ddee3dbeb7c1c38ec79e753578baa1"
PROTOCOL_COMMIT = "1c1310fba545c1ac53d7d3419985755ffe8f0bf2"
ARCHIVE_URL = (
    "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/"
    "10_Portfolios_Prior_12_2_Daily_CSV.zip"
)
EXPECTED_MEMBER = "10_Portfolios_Prior_12_2_Daily.csv"
VALUE_WEIGHTED_DAILY_MARKER = "Value Weight Returns -- Daily"
PRIOR_COLUMNS = [
    "Lo PRIOR",
    "PRIOR 2",
    "PRIOR 3",
    "PRIOR 4",
    "PRIOR 5",
    "PRIOR 6",
    "PRIOR 7",
    "PRIOR 8",
    "PRIOR 9",
    "Hi PRIOR",
]
REUSED = {
    "french_daily_market_rf": (
        ROOT / "artifacts/french_ff_factors_daily_af8aec07.zip",
        "af8aec07d55c98caa15045a77b87455be68cb8847b2ee5bd03bf5c2c8a3f96e2",
    ),
    "qqq_spy_snapshot": (
        ROOT / "artifacts/snapshot_20260731_6a7ca6b8.zip",
        "d480fb82e712f06aabe0a98461e222344656b87022b8bda2cd7ccaa4c29ae88b",
    ),
}


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    rendered = json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(rendered, encoding="utf-8")
    temporary.replace(path)


def _download_once(url: str) -> bytes:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "us-fddk-research/1.0 (+frozen-data-contract)"},
    )
    with urllib.request.urlopen(request, timeout=90) as response:
        payload = response.read(25_000_001)
    if not payload or len(payload) > 25_000_000 or not payload.startswith(b"PK"):
        raise RuntimeError("French 每日 Prior 12–2 回應不是合資格非空 ZIP")
    return payload


def parse_daily_prior_archive(payload: bytes) -> tuple[pd.DataFrame, dict[str, Any]]:
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        members = archive.namelist()
        if members != [EXPECTED_MEMBER]:
            raise ValueError(f"French 每日 Prior ZIP member 不符：{members}")
        raw = archive.read(EXPECTED_MEMBER)
    text = raw.decode("utf-8", errors="strict")
    lines = text.splitlines()
    marker_positions = [
        index for index, line in enumerate(lines) if line.strip() == VALUE_WEIGHTED_DAILY_MARKER
    ]
    if len(marker_positions) != 1:
        raise ValueError("French 每日 Prior value-weighted marker 不是唯一精確命中")
    marker_position = marker_positions[0]
    header_position = marker_position + 1
    if header_position >= len(lines):
        raise ValueError("French 每日 Prior marker 後沒有 header")
    header = [part.strip() for part in lines[header_position].split(",")]
    if header[0] != "" or header[1:] != PRIOR_COLUMNS:
        raise ValueError(f"French 每日 Prior 欄序不符：{header}")

    rows: list[str] = []
    for line in lines[header_position + 1 :]:
        first = line.split(",", 1)[0].strip()
        if len(first) == 8 and first.isdigit():
            rows.append(line)
        elif rows:
            break
    if not rows:
        raise ValueError("French 每日 Prior 沒有八位日期數值列")

    frame = pd.read_csv(io.StringIO("\n".join([lines[header_position], *rows])))
    date_column = frame.columns[0]
    raw_dates = frame[date_column].astype(str).str.strip()
    if not raw_dates.str.fullmatch(r"\d{8}").all():
        raise ValueError("French 每日 Prior 日期不是八位 YYYYMMDD")
    frame.index = pd.to_datetime(raw_dates, format="%Y%m%d", errors="raise")
    frame = frame.drop(columns=[date_column])
    frame.columns = [str(column).strip() for column in frame.columns]
    if list(frame.columns) != PRIOR_COLUMNS:
        raise ValueError("French 每日 Prior parsed 欄序不符")
    numeric = frame.apply(pd.to_numeric, errors="raise").astype(float)
    raw_missing_codes = int(numeric.isin([-99.99, -999.0]).sum().sum())
    if raw_missing_codes:
        raise ValueError(f"French 每日 Prior 含 {raw_missing_codes} 個缺值碼")
    if numeric.isna().any().any():
        raise ValueError("French 每日 Prior 含空值")
    finite = numeric.map(math.isfinite)
    if not finite.all().all():
        raise ValueError("French 每日 Prior 含非有限值")
    if numeric.index.has_duplicates or not numeric.index.is_monotonic_increasing:
        raise ValueError("French 每日 Prior 日期重複或未遞增")
    returns = numeric / 100.0
    meta = {
        "marker": VALUE_WEIGHTED_DAILY_MARKER,
        "member": EXPECTED_MEMBER,
        "rows": int(len(returns)),
        "columns": list(returns.columns),
        "first_date": returns.index[0].date().isoformat(),
        "last_date": returns.index[-1].date().isoformat(),
        "raw_missing_codes": raw_missing_codes,
        "missing_values": int(returns.isna().sum().sum()),
        "maximum_absolute_daily_return": float(returns.abs().max().max()),
    }
    return returns, meta


def _verify_preconditions() -> dict[str, dict[str, str]]:
    receipt = json.loads(PROTOCOL_RECEIPT.read_text(encoding="utf-8"))
    if sha256_file(PROTOCOL) != PROTOCOL_SHA256:
        raise RuntimeError("每日動量環境協議已在首次下載前改變")
    if sha256_file(MAPPING) != MAPPING_SHA256:
        raise RuntimeError("每日動量環境映射已在首次下載前改變")
    if receipt.get("protocol_sha256") != PROTOCOL_SHA256:
        raise RuntimeError("每日動量環境協議收據雜湊不符")
    if receipt.get("data_mapping_sha256") != MAPPING_SHA256:
        raise RuntimeError("每日動量環境映射收據雜湊不符")
    if receipt.get("status") != "protocol_frozen_before_first_daily_prior_download":
        raise RuntimeError("每日動量環境協議收據狀態不符")
    for key in (
        "new_data_present_at_freeze",
        "new_data_downloaded_at_freeze",
        "new_data_parsed_at_freeze",
        "strategy_results_computed_at_freeze",
    ):
        if receipt.get(key) is not False:
            raise RuntimeError(f"每日動量環境凍結欄位不符：{key}")
    reused: dict[str, dict[str, str]] = {}
    for role, (path, expected_hash) in REUSED.items():
        actual = sha256_file(path)
        if actual != expected_hash:
            raise RuntimeError(f"既有 {role} 快照雜湊不符")
        reused[role] = {
            "path": str(path.relative_to(ROOT)),
            "sha256": actual,
        }
    return reused


def main() -> int:
    reused = _verify_preconditions()
    existing = list(ARTIFACTS.glob("french_10_prior_12_2_daily_*.zip"))
    if existing or DATA_RECEIPT.exists():
        raise RuntimeError(f"拒絕重複下載 French 每日 Prior 12–2：{existing}")

    downloaded_at = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    payload = _download_once(ARCHIVE_URL)
    digest = sha256_bytes(payload)
    archive_path = ARTIFACTS / f"french_10_prior_12_2_daily_{digest[:8]}.zip"
    archive_path.write_bytes(payload)

    schema_error: str | None = None
    table_meta: dict[str, Any] = {}
    try:
        returns, table_meta = parse_daily_prior_archive(payload)
        checks = {
            "protocol_and_mapping_frozen_before_download": True,
            "first_download_performed_once": True,
            "url_and_single_member_exact": True,
            "value_weighted_marker_and_columns_exact": True,
            "dates_unique_monotonic_and_values_complete": True,
            "raw_start_no_later_than_1926_11_03": bool(
                returns.index[0] <= pd.Timestamp("1926-11-03")
            ),
            "raw_end_at_least_2026_05_29": bool(
                returns.index[-1] >= pd.Timestamp("2026-05-29")
            ),
            "reused_market_and_price_snapshots_match_hashes": True,
            "strategy_calculation_not_started": True,
        }
    except Exception as exc:
        schema_error = f"{type(exc).__name__}: {exc}"
        checks = {
            "protocol_and_mapping_frozen_before_download": True,
            "first_download_performed_once": True,
            "url_and_single_member_exact": False,
            "value_weighted_marker_and_columns_exact": False,
            "dates_unique_monotonic_and_values_complete": False,
            "raw_start_no_later_than_1926_11_03": False,
            "raw_end_at_least_2026_05_29": False,
            "reused_market_and_price_snapshots_match_hashes": True,
            "strategy_calculation_not_started": True,
        }

    passed = int(sum(checks.values()))
    receipt = {
        "schema_version": "1.0",
        "round": 10,
        "status": (
            "daily_momentum_regime_first_download_contract_passed"
            if all(checks.values())
            else "daily_momentum_regime_first_download_contract_failed_before_strategy"
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
        "archive": {
            "url": ARCHIVE_URL,
            "path": str(archive_path.relative_to(ROOT)),
            "sha256": digest,
            "size_bytes": len(payload),
            "member": EXPECTED_MEMBER,
            "downloaded_in_this_run": True,
        },
        "reused_archives": reused,
        "table": table_meta,
        "schema_error": schema_error,
        "checks": checks,
        "passed_check_count": passed,
        "required_check_count": len(checks),
        "numeric_return_rows_parsed": all(checks.values()),
        "strategy_calculation_started": False,
        "decision_boundary": {
            "paper_eligible": False,
            "paper_state_created": False,
            "trade_ready": False,
            "real_money_action_usd": 0,
        },
    }
    _write_json(DATA_RECEIPT, receipt)
    print(json.dumps(receipt, ensure_ascii=False, indent=2, allow_nan=False))
    return 0 if all(checks.values()) else 2


if __name__ == "__main__":
    raise SystemExit(main())
