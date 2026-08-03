from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path

from usfddk.paper import load_paper_state
from usfddk.site_export import (
    _localize_hk_finance_copy,
    _preserve_idempotent_generation_time,
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
    template = ROOT / "site/data/trading-data.json"
    before = json.loads(template.read_text(encoding="utf-8"))
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

    assert after["research_snapshot_data_through"] == before["data_through"]
    assert after["research_snapshot_sha256"] == before["snapshot_sha256"]
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
