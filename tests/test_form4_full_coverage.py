from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "docs/SHORT_TERM_FORM4_FULL_COVERAGE_PROTOCOL.md"
RECEIPT = ROOT / "artifacts/short_term_form4_full_coverage_protocol_receipt.json"
MANIFEST = ROOT / "artifacts/short_term_form4_full_coverage_source_manifest.json"
VALIDATION = ROOT / "artifacts/short_term_form4_full_coverage_validation.json"
EXPECTED_PROTOCOL_SHA256 = (
    "faefdba7bd890e9d47be115f09e8aee7d9b6a956e28a8a44ce7be415d6ea5fd7"
)
EXPECTED_RECEIPT_SHA256 = (
    "32eabfd42688eac10a73447ca53e7e886710cf9757e90fea49be9955926ff553"
)


def _canonical_sha256(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


def test_round52_protocol_is_frozen_before_download_readout() -> None:
    assert hashlib.sha256(PROTOCOL.read_bytes()).hexdigest() == EXPECTED_PROTOCOL_SHA256
    receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
    claimed = receipt["receipt_sha256"]
    unsigned = dict(receipt)
    unsigned.pop("receipt_sha256")
    assert claimed == EXPECTED_RECEIPT_SHA256
    assert _canonical_sha256(unsigned) == claimed
    assert receipt["status"] == "preregistered_full_quarter_form4_coverage_only"
    assert receipt["quarter_count"] == 82
    assert receipt["quarter_start"] == "2006Q1"
    assert receipt["quarter_end"] == "2026Q2"
    assert receipt["performance_authorized"] is False
    assert receipt["paper_authorized"] is False
    assert receipt["real_money_authorized"] is False
    assert receipt["today_action"] == "今天不下單"


def test_round52_quarter_set_is_contiguous() -> None:
    quarters = [
        f"{year}Q{quarter}"
        for year in range(2006, 2027)
        for quarter in range(1, 5)
        if not (year == 2026 and quarter > 2)
    ]
    assert len(quarters) == 82
    assert quarters[0] == "2006Q1"
    assert quarters[-1] == "2026Q2"


def test_round52_source_manifest_is_self_bound_and_anchor_bound() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    claimed = manifest["manifest_sha256"]
    unsigned = dict(manifest)
    unsigned.pop("manifest_sha256")
    assert _canonical_sha256(unsigned) == claimed
    quarters = manifest["quarters"]
    assert len(quarters) == 82
    assert [row["quarter"] for row in quarters] == [
        f"{year}Q{quarter}"
        for year in range(2006, 2027)
        for quarter in range(1, 5)
        if not (year == 2026 and quarter > 2)
    ]
    anchors = {
        row["quarter"]: (row["bytes"], row["sha256"])
        for row in quarters
        if row["quarter"] in {"2006Q1", "2016Q3", "2026Q2"}
    }
    assert anchors == {
        "2006Q1": (
            17306804,
            "62becdadbe5eaff68f03edefe2ba2357c8bb498a1f825b697003e087cf98e6ce",
        ),
        "2016Q3": (
            8704557,
            "5a25d3c6cb874875904b2be0059bb4784e4da28b315af30b15568fd250bd0dde",
        ),
        "2026Q2": (
            11498860,
            "11f1b2bbbdcbe6347a34437c02d04202fda0eca1dbb023726e4b56504b802e27",
        ),
    }


def test_round52_validation_is_aggregate_only_and_not_trade_authorization() -> None:
    validation = json.loads(VALIDATION.read_text(encoding="utf-8"))
    claimed = validation["receipt_sha256"]
    unsigned = dict(validation)
    unsigned.pop("receipt_sha256")
    assert _canonical_sha256(unsigned) == claimed
    assert validation["status"] == "full_quarter_coverage_ready_for_separate_preregistration"
    assert validation["source_manifest"]["quarter_count"] == 82
    assert validation["source_manifest"]["all_bytes_and_hashes_verified"] is True
    assert validation["source_manifest"]["anchors_verified"] is True
    assert validation["state_boundary"] == {
        "performance_present": False,
        "strategy_run_count": 0,
        "paper_authorized": False,
        "real_money_action_usd": 0,
        "today_action": "今天不下單",
    }
    forbidden_keys = {
        "accession",
        "accession_number",
        "cik",
        "issuer_cik",
        "owner",
        "owner_cik",
        "owner_name",
        "issuer_name",
        "filing_date",
        "notional",
        "symbol",
        "ticker",
    }

    def keys(value: object) -> set[str]:
        if isinstance(value, dict):
            return {str(key) for key in value} | {
                nested
                for item in value.values()
                for nested in keys(item)
            }
        if isinstance(value, list):
            return {nested for item in value for nested in keys(item)}
        return set()

    assert forbidden_keys.isdisjoint(keys(validation))
