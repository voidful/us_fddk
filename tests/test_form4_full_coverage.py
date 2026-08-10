from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "docs/SHORT_TERM_FORM4_FULL_COVERAGE_PROTOCOL.md"
RECEIPT = ROOT / "artifacts/short_term_form4_full_coverage_protocol_receipt.json"
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
