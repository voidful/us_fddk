from __future__ import annotations

import csv
import hashlib
import io
import json
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

PROTOCOL_SHA256 = "f6ff259ee2ad020d618f891097eb3dbf7b76ee3d382b9a31c373ba76641f62da"
MAPPING_SHA256 = "8b7606385e4234dfeb7de878466543c92a8085f2c7f76240415e353b342b7931"
PROTOCOL_COMMIT = "b3240326cb4ba92e9e6585779a2b6249a9f5c78d"
EXPECTED_VALUE_MARKER = "Average Value Weighted Returns -- Monthly"
EXPECTED_EQUAL_MARKER = "Average Equal Weighted Returns -- Monthly"

ARCHIVE_CONTRACTS = {
    "short_term_prior_1_0": {
        "path": "artifacts/french_10_prior_1_0_monthly_20b186f6.zip",
        "sha256": "20b186f6f7c322098d6d2a6be6183d5944b12c7f6c9e888664ce44ba81064ace",
        "member": "10_Portfolios_Prior_1_0.csv",
    },
    "long_term_prior_12_2": {
        "path": "artifacts/french_10_prior_12_2_monthly_ca0af27f.zip",
        "sha256": "ca0af27fa0829ed6ac38b7b13b20cc11fd12274a8d06dac226998dfc1d0f07f6",
        "member": "10_Portfolios_Prior_12_2.csv",
    },
    "ff_factors": {
        "path": "artifacts/french_ff_factors_80b88699.zip",
        "sha256": "80b88699a18ac408e2456d25b1004e340f3f7f8d41d5b476a0285bc53c6f0436",
        "member": "F-F_Research_Data_Factors.csv",
    },
    "momentum": {
        "path": "artifacts/french_momentum_monthly_37baf72a.zip",
        "sha256": "37baf72ae4eace9715e8746413d0122334c63aa4083fd1c3cf2060fa04e4bd28",
        "member": "F-F_Momentum_Factor.csv",
    },
    "short_term_reversal": {
        "path": "artifacts/french_st_reversal_monthly_e0fc1859.zip",
        "sha256": "e0fc1859c8b7e56ac17d06239de231fb33d28c8537b3f59fa378d4d704110e21",
        "member": "F-F_ST_Reversal_Factor.csv",
    },
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _extract_single_csv(path: Path) -> tuple[str, str]:
    with zipfile.ZipFile(path) as bundle:
        members = [
            name
            for name in bundle.namelist()
            if not name.endswith("/") and name.lower().endswith(".csv")
        ]
        if len(members) != 1:
            raise ValueError(f"{path.name} 必須只有一個 CSV member：{members}")
        member = members[0]
        raw = bundle.read(member)
    for encoding in ("utf-8-sig", "latin-1"):
        try:
            return member, raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise ValueError(f"{path.name} CSV 編碼無法辨識")


def _monthly_markers(text: str) -> list[str]:
    return [
        line.strip()
        for line in text.splitlines()
        if line.strip().endswith("Returns -- Monthly")
    ]


def _has_header(text: str, required: set[str]) -> bool:
    for row in csv.reader(io.StringIO(text)):
        names = {cell.strip() for cell in row[1:] if cell.strip()}
        if required.issubset(names):
            return True
    return False


def audit_frozen_prior_return_archives(root: str | Path) -> dict[str, Any]:
    root_path = Path(root)
    protocol_path = root_path / "docs/SHORT_TERM_FRENCH_PRIOR_RETURN_PROTOCOL.md"
    mapping_path = root_path / "docs/SHORT_TERM_FRENCH_PRIOR_RETURN_DATA_MAPPING.md"
    protocol_receipt_path = (
        root_path / "artifacts/short_term_french_prior_return_protocol_receipt.json"
    )
    protocol_receipt = json.loads(protocol_receipt_path.read_text(encoding="utf-8"))

    archives: dict[str, Any] = {}
    texts: dict[str, str] = {}
    newest_mtime = 0.0
    archive_hashes_match = True
    zip_members_match = True
    for role, contract in ARCHIVE_CONTRACTS.items():
        archive_path = root_path / contract["path"]
        digest = _sha256(archive_path)
        member, text = _extract_single_csv(archive_path)
        texts[role] = text
        newest_mtime = max(newest_mtime, archive_path.stat().st_mtime)
        hash_match = digest == contract["sha256"]
        member_match = member == contract["member"]
        archive_hashes_match &= hash_match
        zip_members_match &= member_match
        archives[role] = {
            "path": contract["path"],
            "sha256": digest,
            "size_bytes": archive_path.stat().st_size,
            "member": member,
            "hash_match": hash_match,
            "member_match": member_match,
        }

    short_markers = _monthly_markers(texts["short_term_prior_1_0"])
    long_markers = _monthly_markers(texts["long_term_prior_12_2"])
    checks = {
        "protocol_and_mapping_hashes_match_frozen_receipt": (
            _sha256(protocol_path) == PROTOCOL_SHA256
            and _sha256(mapping_path) == MAPPING_SHA256
            and protocol_receipt["protocol"]["sha256"] == PROTOCOL_SHA256
            and protocol_receipt["mapping"]["sha256"] == MAPPING_SHA256
        ),
        "all_five_archive_hashes_match": archive_hashes_match,
        "all_five_zip_members_match": zip_members_match,
        "short_term_exact_value_weighted_monthly_marker": (
            EXPECTED_VALUE_MARKER in short_markers
        ),
        "long_term_exact_value_weighted_monthly_marker": (
            EXPECTED_VALUE_MARKER in long_markers
        ),
        "both_equal_weighted_monthly_markers_match": (
            EXPECTED_EQUAL_MARKER in short_markers
            and EXPECTED_EQUAL_MARKER in long_markers
        ),
        "ff_factor_header_matches": _has_header(
            texts["ff_factors"], {"Mkt-RF", "SMB", "HML", "RF"}
        ),
        "momentum_and_reversal_headers_match": (
            _has_header(texts["momentum"], {"Mom"})
            and _has_header(texts["short_term_reversal"], {"ST_Rev"})
        ),
    }
    contract_passed = all(checks.values())
    audited_at = datetime.fromtimestamp(newest_mtime, tz=UTC).isoformat().replace(
        "+00:00", "Z"
    )
    return {
        "schema_version": 1,
        "status": (
            "french_prior_return_first_download_contract_passed"
            if contract_passed
            else "french_prior_return_first_download_contract_failed_before_strategy_calculation"
        ),
        "audit_timestamp_from_frozen_archive_mtime_utc": audited_at,
        "protocol": {
            "path": str(protocol_path.relative_to(root_path)),
            "sha256": PROTOCOL_SHA256,
            "commit": PROTOCOL_COMMIT,
        },
        "mapping": {
            "path": str(mapping_path.relative_to(root_path)),
            "sha256": MAPPING_SHA256,
        },
        "archives": archives,
        "observed_monthly_markers": {
            "short_term_prior_1_0": short_markers,
            "long_term_prior_12_2": long_markers,
        },
        "expected_value_weighted_monthly_marker": EXPECTED_VALUE_MARKER,
        "checks": checks,
        "passed_check_count": sum(bool(value) for value in checks.values()),
        "required_check_count": len(checks),
        "new_download_performed_once": True,
        "numeric_return_rows_parsed": False,
        "strategy_calculation_started": False,
        "redownload_permitted": False,
        "failure_reason": (
            None
            if contract_passed
            else "兩個 prior-return ZIP 的 value-weighted 月表標記均與下載前凍結字串不符"
        ),
        "decision_boundary": {
            "academic_result_available": False,
            "paper_eligible": False,
            "paper_state_created": False,
            "trade_ready": False,
            "real_money_action_usd": 0,
        },
    }
