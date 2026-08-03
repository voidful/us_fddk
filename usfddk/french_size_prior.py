from __future__ import annotations

import csv
import hashlib
import io
import zipfile
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

VALUE_WEIGHTED_MONTHLY_MARKER = "Average Value Weighted Returns -- Monthly"
EQUAL_WEIGHTED_MONTHLY_MARKER = "Average Equal Weighted Returns -- Monthly"

SIZE_PRIOR_COLUMNS = [
    "SMALL LoPRIOR",
    "ME1 PRIOR2",
    "ME1 PRIOR3",
    "ME1 PRIOR4",
    "SMALL HiPRIOR",
    "ME2 PRIOR1",
    "ME2 PRIOR2",
    "ME2 PRIOR3",
    "ME2 PRIOR4",
    "ME2 PRIOR5",
    "ME3 PRIOR1",
    "ME3 PRIOR2",
    "ME3 PRIOR3",
    "ME3 PRIOR4",
    "ME3 PRIOR5",
    "ME4 PRIOR1",
    "ME4 PRIOR2",
    "ME4 PRIOR3",
    "ME4 PRIOR4",
    "ME4 PRIOR5",
    "BIG LoPRIOR",
    "ME5 PRIOR2",
    "ME5 PRIOR3",
    "ME5 PRIOR4",
    "BIG HiPRIOR",
]


@dataclass(frozen=True)
class ParsedSizePriorTable:
    frame: pd.DataFrame
    marker: str
    raw_missing_codes: int


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: str | Path) -> str:
    return sha256_bytes(Path(path).read_bytes())


def extract_single_csv(payload: bytes, expected_member: str) -> str:
    with zipfile.ZipFile(io.BytesIO(payload)) as bundle:
        members = [
            name
            for name in bundle.namelist()
            if not name.endswith("/") and name.lower().endswith(".csv")
        ]
        if members != [expected_member]:
            raise ValueError(f"ZIP member 不符：{members}")
        raw = bundle.read(expected_member)
    for encoding in ("utf-8-sig", "latin-1"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise ValueError("CSV 編碼無法辨識")


def parse_size_prior_monthly_table(
    text: str,
    marker: str,
) -> ParsedSizePriorTable:
    rows = list(csv.reader(io.StringIO(text)))
    matches = [
        index
        for index, row in enumerate(rows)
        if len(row) == 1 and row[0].strip() == marker
    ]
    if len(matches) != 1:
        raise ValueError(f"精確月表 marker 必須只出現一次：{marker!r}，實際 {len(matches)} 次")

    header_index = matches[0] + 1
    while header_index < len(rows) and not any(cell.strip() for cell in rows[header_index]):
        header_index += 1
    if header_index >= len(rows):
        raise ValueError(f"{marker!r} 後沒有欄名")
    columns = [cell.strip() for cell in rows[header_index][1:]]
    if columns != SIZE_PRIOR_COLUMNS:
        raise ValueError(f"{marker!r} 25-cell 欄名或次序不符：{columns}")

    periods: list[pd.Period] = []
    values: list[list[float]] = []
    missing_codes = 0
    started = False
    for row in rows[header_index + 1 :]:
        first = row[0].strip() if row else ""
        if len(first) != 6 or not first.isdigit():
            if started:
                break
            continue
        started = True
        if len(row) != len(SIZE_PRIOR_COLUMNS) + 1:
            raise ValueError(f"{marker!r} {first} 欄數不符")
        parsed: list[float] = []
        for cell in row[1:]:
            raw = float(cell.strip())
            missing = raw in (-99.99, -999.0)
            missing_codes += int(missing)
            parsed.append(float("nan") if missing else raw / 100.0)
        periods.append(pd.Period(first, freq="M"))
        values.append(parsed)
    if not periods:
        raise ValueError(f"{marker!r} 沒有月資料")

    frame = pd.DataFrame(
        values,
        index=pd.PeriodIndex(periods, freq="M"),
        columns=SIZE_PRIOR_COLUMNS,
    )
    if frame.index.has_duplicates or not frame.index.is_monotonic_increasing:
        raise ValueError(f"{marker!r} 月份重複或未遞增")
    return ParsedSizePriorTable(
        frame=frame,
        marker=marker,
        raw_missing_codes=missing_codes,
    )
