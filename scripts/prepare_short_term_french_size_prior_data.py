from __future__ import annotations

import json
import sys
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from usfddk.french_size_prior import (  # noqa: E402
    EQUAL_WEIGHTED_MONTHLY_MARKER,
    SIZE_PRIOR_COLUMNS,
    VALUE_WEIGHTED_MONTHLY_MARKER,
    extract_single_csv,
    parse_size_prior_monthly_table,
    sha256_bytes,
    sha256_file,
)

ARTIFACTS = ROOT / "artifacts"
PROTOCOL = ROOT / "docs/SHORT_TERM_FRENCH_SIZE_PRIOR_PROTOCOL.md"
MAPPING = ROOT / "docs/SHORT_TERM_FRENCH_SIZE_PRIOR_DATA_MAPPING.md"
PROTOCOL_RECEIPT = ARTIFACTS / "short_term_french_size_prior_protocol_receipt.json"
DATA_RECEIPT = ARTIFACTS / "short_term_french_size_prior_data_receipt.json"

PROTOCOL_SHA256 = "f2c7907a3630437f9b3dc9df4c0d367ecd4909dbc1d4d5d621b9f8da90d782b4"
MAPPING_SHA256 = "ad859502f111731f1a92ad987386ed7d28eade4e579362f92bf804e0f5e07127"
PROTOCOL_COMMIT = "a75018e6698f3276c03670aef393b0cd9d8738c6"
ARCHIVE_URL = (
    "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/"
    "25_Portfolios_ME_Prior_1_0_CSV.zip"
)
EXPECTED_MEMBER = "25_Portfolios_ME_Prior_1_0.csv"
FORMAL_START = pd.Period("1963-01", freq="M")
FORMAL_END = pd.Period("2026-05", freq="M")

REUSED_ARCHIVES = {
    "ff_factors": (
        "artifacts/french_ff_factors_80b88699.zip",
        "80b88699a18ac408e2456d25b1004e340f3f7f8d41d5b476a0285bc53c6f0436",
    ),
    "prior_1_0": (
        "artifacts/french_10_prior_1_0_monthly_20b186f6.zip",
        "20b186f6f7c322098d6d2a6be6183d5944b12c7f6c9e888664ce44ba81064ace",
    ),
    "prior_12_2": (
        "artifacts/french_10_prior_12_2_monthly_ca0af27f.zip",
        "ca0af27fa0829ed6ac38b7b13b20cc11fd12274a8d06dac226998dfc1d0f07f6",
    ),
    "momentum": (
        "artifacts/french_momentum_monthly_37baf72a.zip",
        "37baf72ae4eace9715e8746413d0122334c63aa4083fd1c3cf2060fa04e4bd28",
    ),
    "short_term_reversal": (
        "artifacts/french_st_reversal_monthly_e0fc1859.zip",
        "e0fc1859c8b7e56ac17d06239de231fb33d28c8537b3f59fa378d4d704110e21",
    ),
    "qqq_spy_snapshot": (
        "artifacts/snapshot_20260731_6a7ca6b8.zip",
        "d480fb82e712f06aabe0a98461e222344656b87022b8bda2cd7ccaa4c29ae88b",
    ),
}


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
    with urllib.request.urlopen(request, timeout=60) as response:
        payload = response.read(10_000_001)
    if not payload or len(payload) > 10_000_000 or not payload.startswith(b"PK"):
        raise RuntimeError("French 25 ZIP 回應不是合資格非空 ZIP")
    return payload


def _table_meta(table: Any) -> dict[str, Any]:
    frame = table.frame
    return {
        "marker": table.marker,
        "rows": int(len(frame)),
        "columns": list(frame.columns),
        "first_month": str(frame.index[0]),
        "last_month": str(frame.index[-1]),
        "raw_missing_codes": int(table.raw_missing_codes),
        "missing_values": int(frame.isna().sum().sum()),
        "maximum_absolute_return": float(frame.abs().max().max()),
    }


def _verify_preconditions() -> dict[str, dict[str, str]]:
    receipt = json.loads(PROTOCOL_RECEIPT.read_text(encoding="utf-8"))
    if sha256_file(PROTOCOL) != PROTOCOL_SHA256:
        raise RuntimeError("French size-prior 協議已在首次下載前改變")
    if sha256_file(MAPPING) != MAPPING_SHA256:
        raise RuntimeError("French size-prior 映射已在首次下載前改變")
    if receipt.get("status") != "french_size_prior_frozen_before_first_download_and_numeric_rows":
        raise RuntimeError("French size-prior 協議收據狀態不符")
    if any(
        receipt.get(key) is not False
        for key in (
            "new_archive_download_started",
            "new_archive_schema_seen",
            "new_archive_numeric_rows_seen",
            "strategy_calculation_started",
        )
    ):
        raise RuntimeError("French size-prior 協議收據不是未下載／未計算狀態")
    if receipt["protocol"]["sha256"] != PROTOCOL_SHA256:
        raise RuntimeError("French size-prior 協議收據雜湊不符")
    if receipt["mapping"]["sha256"] != MAPPING_SHA256:
        raise RuntimeError("French size-prior 映射收據雜湊不符")

    reused: dict[str, dict[str, str]] = {}
    for role, (relative_path, expected_sha) in REUSED_ARCHIVES.items():
        path = ROOT / relative_path
        actual = sha256_file(path)
        if actual != expected_sha:
            raise RuntimeError(f"既有 {role} 封存檔雜湊不符")
        reused[role] = {"path": relative_path, "sha256": actual}
    return reused


def main() -> int:
    reused = _verify_preconditions()
    existing = list(ARTIFACTS.glob("french_25_size_prior_1_0_monthly_*.zip"))
    if existing or DATA_RECEIPT.exists():
        raise RuntimeError(f"拒絕重複下載 French 25 size-prior 資料：{existing}")

    downloaded_at = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    payload = _download_once(ARCHIVE_URL)
    digest = sha256_bytes(payload)
    archive_path = ARTIFACTS / f"french_25_size_prior_1_0_monthly_{digest[:8]}.zip"
    archive_path.write_bytes(payload)

    tables: dict[str, Any] = {}
    schema_error: str | None = None
    try:
        text = extract_single_csv(payload, EXPECTED_MEMBER)
        value_table = parse_size_prior_monthly_table(text, VALUE_WEIGHTED_MONTHLY_MARKER)
        equal_table = parse_size_prior_monthly_table(text, EQUAL_WEIGHTED_MONTHLY_MARKER)
        tables = {
            "value_weighted_monthly": _table_meta(value_table),
            "equal_weighted_monthly": _table_meta(equal_table),
        }
        formal = value_table.frame.loc[FORMAL_START:FORMAL_END]
        formal_equal = equal_table.frame.loc[FORMAL_START:FORMAL_END]
        expected = pd.period_range(FORMAL_START, FORMAL_END, freq="M")
        checks = {
            "url_and_schema_frozen_before_first_download": True,
            "first_download_performed_once": True,
            "zip_member_and_sha256_preserved": True,
            "two_monthly_tables_have_exactly_25_columns": bool(
                value_table.frame.shape[1] == 25 and equal_table.frame.shape[1] == 25
            ),
            "semantic_column_order_matches_frozen_grid": bool(
                list(value_table.frame.columns) == SIZE_PRIOR_COLUMNS
                and list(equal_table.frame.columns) == SIZE_PRIOR_COLUMNS
            ),
            "raw_dates_cover_1927_01_through_2026_05": bool(
                value_table.frame.index[0] <= pd.Period("1927-01", freq="M")
                and equal_table.frame.index[0] <= pd.Period("1927-01", freq="M")
                and value_table.frame.index[-1] == FORMAL_END
                and equal_table.frame.index[-1] == FORMAL_END
            ),
            "formal_1963_01_to_2026_05_is_complete": bool(
                formal.index.equals(expected)
                and formal_equal.index.equals(expected)
                and not formal.isna().any().any()
                and not formal_equal.isna().any().any()
            ),
            "missing_and_extreme_values_audited_without_imputation": bool(
                formal.abs().max().max() <= 1.0 and formal_equal.abs().max().max() <= 1.0
            ),
            "reused_archives_match_frozen_hashes": True,
            "formation_t_minus_1_return_t_rule_frozen": True,
        }
    except Exception as exc:  # preserve first-seen schema failure without retrying
        schema_error = f"{type(exc).__name__}: {exc}"
        checks = {
            "url_and_schema_frozen_before_first_download": True,
            "first_download_performed_once": True,
            "zip_member_and_sha256_preserved": True,
            "two_monthly_tables_have_exactly_25_columns": False,
            "semantic_column_order_matches_frozen_grid": False,
            "raw_dates_cover_1927_01_through_2026_05": False,
            "formal_1963_01_to_2026_05_is_complete": False,
            "missing_and_extreme_values_audited_without_imputation": False,
            "reused_archives_match_frozen_hashes": True,
            "formation_t_minus_1_return_t_rule_frozen": True,
        }

    passed = int(sum(checks.values()))
    receipt = {
        "schema_version": 1,
        "status": (
            "french_size_prior_first_download_contract_passed"
            if passed == len(checks)
            else "french_size_prior_first_download_contract_failed_before_strategy_calculation"
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
        "tables": tables,
        "schema_error": schema_error,
        "checks": checks,
        "passed_check_count": passed,
        "required_check_count": len(checks),
        "numeric_return_rows_parsed": passed == len(checks),
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
    return 0 if passed == len(checks) else 2


if __name__ == "__main__":
    raise SystemExit(main())
