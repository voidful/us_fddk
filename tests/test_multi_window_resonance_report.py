from __future__ import annotations

import json
import re
from pathlib import Path

from scripts.build_short_term_multi_window_resonance_report import (
    RECEIPT_FLOAT_DECIMAL_PLACES,
    _canonicalize_floats,
)

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "artifacts/short_term_multi_window_resonance_validation.json"
SITE_DATA = ROOT / "site/data/short-term-multi-window-resonance.json"
REPORT = ROOT / "docs/SHORT_TERM_MULTI_WINDOW_RESONANCE_RESEARCH_REPORT.md"


def test_round38_receipts_are_canonical_and_byte_identical() -> None:
    artifact_bytes = ARTIFACT.read_bytes()
    assert SITE_DATA.read_bytes() == artifact_bytes
    payload = artifact_bytes.decode("utf-8")
    result = json.loads(payload)
    assert result["receipt_float_decimal_places"] == RECEIPT_FLOAT_DECIMAL_PLACES == 12
    assert result == _canonicalize_floats(result)
    assert re.search(r"(?<![\d.])-0\.0(?:[,\n])", payload) is None


def test_round38_report_preserves_the_rejection_and_trading_boundary() -> None:
    result = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    report = REPORT.read_text(encoding="utf-8")
    assert (
        f"{result['gate_summary']['passed']}/{result['gate_summary']['total']}" in report
    )
    assert "九條固定完整資金路徑" in report
    assert "八假說共同統計 family" in report
    assert f"{result['control_summary']['total']} 道固定控制" in report
    assert f"{result['attack_summary']['total']} 項單欄變異攻擊" in report
    assert "短線 Paper 維持全現金" in report
    assert "實金動作 **US$0**" in report
    assert "不是即市行情" in report
    assert result["decision"]["can_promote_from_this_round"] is False
    assert result["decision"]["paper_status"] == "all_cash_not_started"
    assert result["decision"]["real_money_action_usd"] == 0
