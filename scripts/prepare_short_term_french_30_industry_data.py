from __future__ import annotations

import json
import shutil
import tempfile
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
from prepare_short_term_french_industry_data import (
    _download_once,
    _extract_single_csv,
    _parse_table,
    _safe_date,
    _sha256,
    _sha256_bytes,
    _write_json,
)

ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / "artifacts"
PROTOCOL = ROOT / "docs/SHORT_TERM_FRENCH_30_INDUSTRY_MOMENTUM_PROTOCOL.md"
MAPPING = ROOT / "docs/SHORT_TERM_FRENCH_30_INDUSTRY_DATA_MAPPING.md"
PROTOCOL_RECEIPT = ARTIFACTS / "short_term_french_30_industry_protocol_receipt.json"
DATA_RECEIPT = ARTIFACTS / "short_term_french_30_industry_data_receipt.json"
FACTORS_ARCHIVE = ARTIFACTS / "french_ff_factors_daily_af8aec07.zip"
MOMENTUM_ARCHIVE = ARTIFACTS / "french_momentum_daily_f4237e2e.zip"

PROTOCOL_SHA256 = "71c32560fd4234504cf1005686824278173f6034f7cf1a7f9179b8c587613db3"
MAPPING_SHA256 = "ae02ad3e9fa201e036b33319c7398a804e99567b2fc60ef263240f4cf8f1d0df"
PROTOCOL_COMMIT = "2ca60d4187e874b4a208029d8f18a08c21a2227a"
FACTORS_SHA256 = "af8aec07d55c98caa15045a77b87455be68cb8847b2ee5bd03bf5c2c8a3f96e2"
MOMENTUM_SHA256 = "f4237e2e36dffa13fd7823f55376316a94b5ac663af951dd9eaca8ed2c678bcf"
INDUSTRY_URL = (
    "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/"
    "30_Industry_Portfolios_Daily_CSV.zip"
)
FORMAL_START_FLOOR = pd.Timestamp("1963-01-01")
FORMAL_START_CEILING = pd.Timestamp("1970-12-31")
LOOKBACK_SESSIONS = 126


def _formal_start(industry: pd.DataFrame, common_index: pd.DatetimeIndex) -> pd.Timestamp | None:
    aligned = industry.reindex(common_index)
    rolling_complete = aligned.notna().rolling(LOOKBACK_SESSIONS).sum().eq(
        LOOKBACK_SESSIONS
    )
    candidates = common_index[
        (common_index >= FORMAL_START_FLOOR) & rolling_complete.all(axis=1).to_numpy()
    ]
    return candidates[0] if len(candidates) else None


def _missing_locations(frame: pd.DataFrame, start: pd.Timestamp | None) -> list[dict]:
    if start is None:
        return []
    missing = frame.loc[start:].isna().stack()
    return [
        {"date": date.date().isoformat(), "column": str(column)}
        for (date, column), value in missing.items()
        if bool(value)
    ][:100]


def main() -> int:
    receipt = json.loads(PROTOCOL_RECEIPT.read_text(encoding="utf-8"))
    if _sha256(PROTOCOL) != PROTOCOL_SHA256:
        raise RuntimeError("French 30 行業協議已在首次下載前改變")
    if _sha256(MAPPING) != MAPPING_SHA256:
        raise RuntimeError("French 30 行業數據映射已在首次下載前改變")
    if receipt.get("new_industry_download_started") is not False:
        raise RuntimeError("French 30 協議收據不是未下載狀態")
    if receipt.get("calculation_started") is not False:
        raise RuntimeError("French 30 協議收據不是未計算狀態")
    if receipt.get("protocol_sha256") != PROTOCOL_SHA256:
        raise RuntimeError("French 30 協議收據雜湊不符")
    if receipt.get("mapping_sha256") != MAPPING_SHA256:
        raise RuntimeError("French 30 映射收據雜湊不符")
    if _sha256(FACTORS_ARCHIVE) != FACTORS_SHA256:
        raise RuntimeError("既有 French 日因素封存檔改變")
    if _sha256(MOMENTUM_ARCHIVE) != MOMENTUM_SHA256:
        raise RuntimeError("既有 French 日 Mom 封存檔改變")

    existing = list(ARTIFACTS.glob("french_30_industry_daily_*.zip"))
    if existing or DATA_RECEIPT.exists():
        raise RuntimeError(f"拒絕重複下載 French 30 日資料：{existing}")

    downloaded_at = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    with tempfile.TemporaryDirectory(prefix="usfddk-french-30-daily-") as temporary_name:
        temporary = Path(temporary_name)
        industry_archive = _download_once(INDUSTRY_URL)
        temporary_archive = temporary / "industry_30.zip"
        temporary_archive.write_bytes(industry_archive)

        industry_member, industry_text = _extract_single_csv(industry_archive)
        factors_member, factors_text = _extract_single_csv(FACTORS_ARCHIVE.read_bytes())
        momentum_member, momentum_text = _extract_single_csv(MOMENTUM_ARCHIVE.read_bytes())
        industry, industry_meta = _parse_table(
            industry_text,
            expected_columns=30,
            marker="Average Value Weighted Returns -- Daily",
        )
        factors, factors_meta = _parse_table(
            factors_text,
            required={"Mkt-RF", "RF"},
        )
        momentum, momentum_meta = _parse_table(
            momentum_text,
            required={"Mom"},
        )

        common_index = industry.index.intersection(factors.index).intersection(momentum.index)
        common_index = common_index.sort_values()
        start = _formal_start(industry, common_index)
        formal_industry = (
            industry.reindex(common_index).loc[start:] if start is not None else industry.iloc[:0]
        )
        formal_factors = (
            factors.reindex(common_index).loc[start:] if start is not None else factors.iloc[:0]
        )
        formal_momentum = (
            momentum.reindex(common_index).loc[start:] if start is not None else momentum.iloc[:0]
        )
        raw_start = common_index[0] if len(common_index) else None
        raw_end = common_index[-1] if len(common_index) else None
        formal_missing_locations = _missing_locations(industry.reindex(common_index), start)

        checks = {
            "industry_url_frozen_before_first_download": True,
            "new_archive_nonempty_and_hashed": bool(industry_archive),
            "reused_factor_archives_match_frozen_hashes": True,
            "raw_common_start_no_later_than_1927_01_31": bool(
                raw_start is not None and raw_start <= pd.Timestamp("1927-01-31")
            ),
            "raw_common_end_is_in_2026_05_release": bool(
                raw_end is not None and raw_end.year == 2026 and raw_end.month == 5
            ),
            "industry_columns_exactly_30": industry.shape[1] == 30,
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

        final_name = f"french_30_industry_daily_{_sha256_bytes(industry_archive)[:8]}.zip"
        shutil.copyfile(temporary_archive, ARTIFACTS / final_name)

    payload = {
        "status": (
            "french_30_industry_daily_first_download_contract_passed"
            if all(checks.values())
            else "french_30_industry_daily_first_download_contract_failed"
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
        "archives": {
            "industry_30": {
                "url": INDUSTRY_URL,
                "path": f"artifacts/{final_name}",
                "sha256": _sha256_bytes(industry_archive),
                "size_bytes": len(industry_archive),
                "member": industry_member,
                "downloaded_in_this_run": True,
            },
            "ff_factors": {
                "path": str(FACTORS_ARCHIVE.relative_to(ROOT)),
                "sha256": FACTORS_SHA256,
                "member": factors_member,
                "downloaded_in_this_run": False,
            },
            "momentum": {
                "path": str(MOMENTUM_ARCHIVE.relative_to(ROOT)),
                "sha256": MOMENTUM_SHA256,
                "member": momentum_member,
                "downloaded_in_this_run": False,
            },
        },
        "tables": {
            "industry_30_value_weighted": industry_meta,
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
            "formal_missing_locations_first_100": formal_missing_locations,
        },
        "checks": checks,
        "new_download_performed_once": True,
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
        raise RuntimeError("French 30 首次下載契約失敗；已保存原始 ZIP 及失敗收據，禁止重下載")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
