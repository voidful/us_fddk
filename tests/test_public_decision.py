from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

from usfddk.public_decision import (
    build_public_decision_audit_log,
    build_public_decision_payload,
)

ROOT = Path(__file__).resolve().parents[1]


def _read(relative: str) -> dict:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def test_public_contract_is_success_only_and_currently_holds_cash() -> None:
    source = _read("site/data/trading-data.json")
    formal = _read("site/data/short-term-formal-backtest-readiness.json")
    overlay = _read("site/data/short-term-qqq-replacement-overlay.json")

    public = build_public_decision_payload(
        source,
        formal_readiness=formal,
        short_term_overlay=overlay,
    )
    rendered = json.dumps(public, ensure_ascii=False)

    assert public["surface"] == "hold-cash"
    assert public["today_action"] == "今天不下單"
    assert public["strategies"] == []
    assert "research_pipeline" not in public
    assert "formal_readiness_incomplete" not in rendered
    assert "失敗" not in rendered
    assert "淘汰" not in rendered

    audit = build_public_decision_audit_log(
        source,
        formal_readiness=formal,
        short_term_overlay=overlay,
        public_payload=public,
    )
    assert audit["visibility"] == "internal-research-log"
    assert audit["not_for_public_decision_page"] is True
    assert all(row["status"] == "not_promoted" for row in audit["candidate_audit"])
    assert "formal_readiness_incomplete" in audit["candidate_audit"][1]["reason_codes"]


def test_public_contract_copies_only_a_fully_promoted_strategy() -> None:
    source = deepcopy(_read("site/data/trading-data.json"))
    source["readiness"]["trade_ready"] = True
    source["readiness"]["allocation_visible"] = True
    source["readiness"]["passed_gate_count"] = source["readiness"]["required_gate_count"]
    source["readiness"]["gates"] = {
        key: True for key in source["readiness"]["gates"]
    }
    source["readiness"]["selected_strategy_key"] = "growth_gold_diversification"
    latest = source["research_pipeline"]["growth_gold_diversification"]
    latest["trade_ready"] = True
    latest["real_money_signal_display_allowed"] = True
    paper = latest["paper"]
    paper["pending_order"] = {"target_weights": {"VUG": 0.8, "GLD": 0.2}}
    forward = paper["forward_evidence"]
    forward["as_of"] = source["data_through"]
    forward["integrity_violations"] = 0
    forward["live_confirmed"] = True
    forward["gates"] = {name: True for name in forward["gates"]}

    public = build_public_decision_payload(source)

    assert len(public["strategies"]) == 1
    strategy = public["strategies"][0]
    assert strategy["verified"] is True
    assert strategy["key"] == "long-term"
    assert strategy["allocation"] == "VUG 80%／GLD 20%"
    assert strategy["action"] == "下一個完成交易日按已凍結指令調整持倉"
    assert "readiness" not in json.dumps(public, ensure_ascii=False)


def test_malformed_promotion_inputs_fail_closed_and_stay_out_of_public_json() -> None:
    source = deepcopy(_read("site/data/trading-data.json"))
    source["readiness"] = "corrupt"
    formal = {"actual_formal_readiness": ["corrupt"]}
    overlay = {"decision": {"formal_strategy_runs": "not-a-number"}}

    public = build_public_decision_payload(
        source,
        formal_readiness=formal,
        short_term_overlay=overlay,
    )
    audit = build_public_decision_audit_log(
        source,
        formal_readiness=formal,
        short_term_overlay=overlay,
        public_payload=public,
    )

    assert public["surface"] == "hold-cash"
    assert public["strategies"] == []
    assert audit["candidate_audit"][1]["reason_codes"] == [
        "formal_readiness_incomplete"
    ]
