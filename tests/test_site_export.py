from __future__ import annotations

import json
from copy import deepcopy
from datetime import datetime, timedelta
from pathlib import Path

from usfddk.paper import load_paper_state
from usfddk.site_export import (
    _localize_hk_finance_copy,
    _preserve_idempotent_generation_time,
    build_public_decision_payload,
    refresh_v25_site_data,
)
from usfddk.v25_live import audit_v25_live_reference

ROOT = Path(__file__).resolve().parents[1]


def test_hong_kong_finance_copy_is_recursive_idempotent_and_keeps_keys() -> None:
    payload = {
        "max_drawdown_no_worse_than_spy": "前瞻最大回撤不深於 SPY",
        "broker": "券商帳戶採調整後收盤價",
        "nested": ["年化報酬與波動率", "重新平衡", "證券商"],
    }
    localized = _localize_hk_finance_copy(payload)
    assert set(localized) == set(payload)
    assert localized["max_drawdown_no_worse_than_spy"] == "前瞻最大跌幅不深於 SPY"
    assert localized["broker"] == "證券商模擬組合採經調整收市價"
    assert localized["nested"] == ["年率化回報與波幅", "重新平衡", "證券商"]
    assert _localize_hk_finance_copy(localized) == localized


def test_site_payload_preserves_timestamp_only_when_content_is_idempotent(
    tmp_path,
) -> None:
    path = tmp_path / "site.json"
    existing = {
        "schema_version": 1,
        "generated_at_utc": "2026-08-01T00:00:00Z",
        "data_through": "2026-07-31",
        "paper": {"equity": 100_000.0},
    }
    path.write_text(json.dumps(existing), encoding="utf-8")
    rerun = {
        **existing,
        "generated_at_utc": "2026-08-02T00:00:00Z",
    }
    preserved = _preserve_idempotent_generation_time(rerun, [path])
    assert preserved["generated_at_utc"] == existing["generated_at_utc"]

    advanced = {
        **rerun,
        "data_through": "2026-08-03",
    }
    refreshed = _preserve_idempotent_generation_time(advanced, [path])
    assert refreshed["generated_at_utc"] == "2026-08-02T00:00:00Z"


def test_daily_v25_export_preserves_research_and_passes_live_audit(tmp_path) -> None:
    source_template = ROOT / "site/data/trading-data.json"
    before = json.loads(source_template.read_text(encoding="utf-8"))
    # Simulate a site whose LIVE date has advanced beyond the frozen research snapshot.
    before["data_through"] = "2026-08-03"
    template = tmp_path / "advanced-template.json"
    template.write_text(json.dumps(before), encoding="utf-8")
    destination = tmp_path / "site.json"
    candidate = load_paper_state(ROOT / "artifacts/paper_v25_state.json")
    spy = load_paper_state(ROOT / "artifacts/paper_v25_spy_state.json")
    matched = load_paper_state(ROOT / "artifacts/paper_v25_matched_state.json")

    refresh_v25_site_data(
        destination,
        template=template,
        candidate_state=candidate,
        spy_state=spy,
        matched_state=matched,
    )
    after = json.loads(destination.read_text(encoding="utf-8"))

    expected_research_date = before.get(
        "research_snapshot_data_through", before["data_through"]
    )
    expected_research_sha = before.get(
        "research_snapshot_sha256", before["snapshot_sha256"]
    )
    assert after["research_snapshot_data_through"] == expected_research_date
    assert after["research_snapshot_sha256"] == expected_research_sha
    assert after["research_pipeline"]["growth_gold_diversification"]["pooled"] == (
        before["research_pipeline"]["growth_gold_diversification"]["pooled"]
    )
    assert after["research_pipeline"]["growth_gold_diversification"][
        "expanded_comparison_not_used_for_frozen_gate"
    ] == before["research_pipeline"]["growth_gold_diversification"][
        "expanded_comparison_not_used_for_frozen_gate"
    ]
    assert after["data_through"] == candidate["as_of"]
    assert after["live_snapshot_sha256"] == candidate["snapshot_sha256"]

    due = datetime.fromisoformat(after["freshness"]["refresh_due_at_utc"].replace("Z", "+00:00"))
    audit = audit_v25_live_reference(
        after,
        candidate,
        spy,
        matched,
        now=due - timedelta(hours=1),
    )
    assert audit["integrity_ok"] is True
    assert audit["decision"] == "paper_only"


def test_public_decision_payload_is_success_only_and_fail_closed() -> None:
    source = json.loads((ROOT / "site/data/trading-data.json").read_text(encoding="utf-8"))
    formal = json.loads(
        (ROOT / "site/data/short-term-formal-backtest-readiness.json").read_text(
            encoding="utf-8"
        )
    )
    overlay = json.loads(
        (ROOT / "site/data/short-term-qqq-replacement-overlay.json").read_text(
            encoding="utf-8"
        )
    )

    public = build_public_decision_payload(
        source,
        formal_readiness=formal,
        short_term_overlay=overlay,
    )
    rendered = json.dumps(public, ensure_ascii=False)
    assert public["surface"] == "hold-cash"
    assert public["today_action"] == "今天不下單"
    assert public["strategies"] == []
    assert "limitations" not in public
    assert "failed" not in rendered.lower()
    for forbidden in ("失敗", "淘汰", "攻擊測試", "負結果", "未通過項目"):
        assert forbidden not in rendered


def test_round64_negative_research_log_cannot_leak_into_public_surface() -> None:
    source = deepcopy(
        json.loads((ROOT / "site/data/trading-data.json").read_text(encoding="utf-8"))
    )
    round64 = json.loads(
        (
            ROOT
            / "artifacts/short_term_volume_breakout_top10_spy60_robustness_validation.json"
        ).read_text(encoding="utf-8")
    )
    assert round64["status"] == (
        "volume_breakout_top10_spy60_robustness_negative_survivorship_biased"
    )
    source.setdefault("research_pipeline", {})["round64_robustness_diagnostic"] = round64

    formal = json.loads(
        (ROOT / "site/data/short-term-formal-backtest-readiness.json").read_text(
            encoding="utf-8"
        )
    )
    overlay = json.loads(
        (ROOT / "site/data/short-term-qqq-replacement-overlay.json").read_text(
            encoding="utf-8"
        )
    )
    public = build_public_decision_payload(
        source,
        formal_readiness=formal,
        short_term_overlay=overlay,
    )
    rendered = json.dumps(public, ensure_ascii=False)
    assert public["surface"] == "hold-cash"
    assert public["today_action"] == "今天不下單"
    assert public["strategies"] == []
    assert "round64_robustness_diagnostic" not in rendered
    assert "robustness_negative" not in rendered


def test_public_decision_payload_can_publish_only_a_fully_verified_strategy() -> None:
    source = json.loads((ROOT / "site/data/trading-data.json").read_text(encoding="utf-8"))
    source = deepcopy(source)
    source["readiness"]["selected_strategy_key"] = "growth_gold_diversification"
    source["readiness"]["trade_ready"] = True
    source["readiness"]["allocation_visible"] = True
    source["readiness"]["passed_gate_count"] = 11
    source["readiness"]["required_gate_count"] = 11
    source["readiness"]["gates"] = {
        key: True for key in source["readiness"]["gates"]
    }
    latest = source["research_pipeline"]["growth_gold_diversification"]
    latest["trade_ready"] = True
    latest["real_money_signal_display_allowed"] = True
    forward = latest["paper"]["forward_evidence"]
    forward["live_confirmed"] = True
    forward["integrity_violations"] = 0
    forward["gates"] = {
        key: True for key in forward["gates"]
    }

    public = build_public_decision_payload(source)
    assert public["surface"] == "verified-strategy"
    assert public["today_action"] == "今天不下單"
    assert len(public["strategies"]) == 1
    strategy = public["strategies"][0]
    assert strategy["verified"] is True
    assert strategy["key"] == "long-term"
    assert strategy["allocation"] == "VUG 80%／GLD 20%"
    assert strategy["amount_example"] == "US$800／US$200"
