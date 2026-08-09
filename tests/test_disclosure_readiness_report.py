from __future__ import annotations

import json
import re
from pathlib import Path

from scripts.build_short_term_disclosure_readiness_report import (
    SOURCE_CATALOG,
    _public_summary,
)
from usfddk.disclosure_known_at import audit_disclosure_known_at_bundle

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "artifacts/short_term_disclosure_readiness.json"
SITE_DATA = ROOT / "site/data/short-term-disclosure-readiness.json"
REPORT = ROOT / "docs/SHORT_TERM_DISCLOSURE_READINESS_REPORT.md"


def test_phase1_public_receipt_is_exactly_two_of_twenty_and_fail_closed() -> None:
    result = audit_disclosure_known_at_bundle(None, root=ROOT)
    summary = _public_summary(result)

    assert summary["status"] == "blocked_by_disclosure_known_at_readiness"
    assert summary["readiness"] == {
        "passed": 2,
        "total": 20,
        "all_passed": False,
    }
    assert [key[:2] for key in summary["gates"]] == [
        f"{index:02d}" for index in range(1, 21)
    ]
    assert summary["gates"]["01_protocol_schema_receipt_integrity"]["passed"] is True
    assert summary["gates"]["02_official_source_semantics_pinned"]["passed"] is True
    assert all(not gate["passed"] for gate in list(summary["gates"].values())[2:])

    assert summary["selection"] == {
        "strategy_defined": False,
        "dynamic_selection_enabled": False,
        "published_selection_count": 0,
    }
    assert summary["decision"] == {
        "can_promote": False,
        "formal_backtest_authorized": False,
        "strategy_runs": 0,
        "today": "今天不下單",
    }
    assert summary["paper"] == {
        "authorized": False,
        "status": "all_cash_not_started",
        "positions": 0,
        "backfilled_trades": 0,
    }
    assert summary["real_money_usd"] == 0


def test_public_receipt_has_six_source_families_but_no_observed_records() -> None:
    result = audit_disclosure_known_at_bundle(None, root=ROOT)
    summary = _public_summary(result)

    assert [row["source_type"] for row in SOURCE_CATALOG] == [
        "congress_house_ptr",
        "congress_senate_ptr",
        "sec_form_4",
        "sec_schedule_13d",
        "sec_schedule_13g",
        "sec_form_13f",
    ]
    assert summary["coverage"] == {
        "source_types_required": 6,
        "source_types_observed": 0,
        "documents_observed": 0,
        "events_observed": 0,
        "twenty_year_coverage_claimed": False,
        "twenty_year_coverage_validated": False,
        "per_source_year_denominators_audited": False,
    }
    assert summary["known_at"]["documents_validated"] == 0
    assert summary["known_at"]["events_validated"] == 0
    assert summary["lag"]["events_measured"] == 0
    assert summary["lag"]["events_with_valid_trade_clock"] == 0
    assert summary["legal"]["congress_exact_use_written_clearance"] is False
    assert summary["legal"]["authorized_for_local_research"] is False


def test_public_receipt_contains_no_private_or_trade_level_material() -> None:
    summary = _public_summary(audit_disclosure_known_at_bundle(None, root=ROOT))
    payload = json.dumps(summary, ensure_ascii=False, sort_keys=True)

    assert re.search(r"/(?:Users|private|tmp)/", payload) is None
    assert "actor_id" not in payload
    assert "actor_token" not in payload
    assert "selected_tickers" not in payload
    assert "ticker" not in payload.lower()
    assert "cusip" not in payload.lower()
    assert "cik" not in payload.lower()
    assert "accession" not in payload.lower()
    assert "document_id" not in payload
    assert "source_document_id" not in payload
    assert "http://" not in payload
    assert "https://" not in payload
    assert summary["controls"] == {
        "raw_rows_generated": 0,
        "raw_rows_published": 0,
        "actor_names_published": 0,
        "security_identifiers_published": 0,
    }


def test_committed_public_receipts_are_reproducible_and_byte_identical() -> None:
    expected = _public_summary(audit_disclosure_known_at_bundle(None, root=ROOT))
    assert json.loads(ARTIFACT.read_text(encoding="utf-8")) == expected
    assert SITE_DATA.read_bytes() == ARTIFACT.read_bytes()


def test_report_is_conclusion_first_and_non_promotional() -> None:
    report = REPORT.read_text(encoding="utf-8")

    assert "**2/20**" in report
    assert "觀察來源 **0/6**" in report
    assert "「企業家」不是 SEC 申報身分" in report
    assert "`known_at - event_at`" in report
    assert "第一個官方 XNYS 收市" in report
    assert "`trade_at` 再取其後下一個官方 XNYS 開市" in report
    assert "Congress 法律／授權硬門檻" in report
    assert "動態選擇停用" in report
    assert "策略運行 **0 次**" in report
    assert "Paper Trading（模擬交易）維持**全現金**" in report
    assert "實金動作 **US$0**" in report
    assert "**今天不下單。**" in report
    assert "不列人物、\n股票代號" in report
    assert "不保證盈利" in report
