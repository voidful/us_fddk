from __future__ import annotations

import json
from copy import deepcopy
from datetime import UTC, datetime

import pytest

from usfddk.paper import PASSIVE_BENCHMARK_KEY, forward_paper_evidence
from usfddk.reference import (
    append_reference_receipt,
    audit_live_reference,
    build_live_refresh_status,
    evaluate_trade_readiness,
    verify_reference_receipt_ledger,
    write_live_refresh_status,
)


def _fixtures():
    weights = {"QQQ": 0.8, "SHY": 0.2}
    paper = {
        "mode": "live",
        "strategy": "test",
        "started_at": "2026-07-31",
        "as_of": "2026-07-31",
        "snapshot_sha256": "abc",
        "initial_cash": 100_000.0,
        "cash": 100_000.0,
        "cost_bps": 10.0,
        "holdings": {},
        "pending_order": {"target_weights": weights},
        "order_history": [],
        "transactions": [],
        "equity_curve": [
            {
                "date": "2026-07-31",
                "equity": 100_000.0,
                "cash": 100_000.0,
                "turnover": 0.0,
                "cost": 0.0,
                "drawdown": 0.0,
            }
        ],
    }
    benchmarks = {
        ticker: {**deepcopy(paper), "strategy": ticker, "pending_order": None}
        for ticker in ("SPY", "QQQ", PASSIVE_BENCHMARK_KEY)
    }
    forward = forward_paper_evidence(paper, benchmarks)
    site = {
        "schema_version": 1,
        "data_through": "2026-07-31",
        "snapshot_sha256": "abc",
        "freshness": {"refresh_due_at_utc": "2026-08-04T02:00:00Z"},
        "strategy": {"current_target": weights},
        "paper": {
            "mode": "live",
            "as_of": "2026-07-31",
            "equity": 100_000.0,
            "return": 0.0,
            "cash": 100_000.0,
            "forward_sessions": 0,
            "transactions": 0,
            "adjustment_rebases": 0,
            "holdings": {},
            "pending_order": {"target_weights": weights},
            "forward_evidence": forward,
        },
        "evidence": {
            "historical_gate_passed": True,
            "statistically_confirmed": False,
            "live_confirmed": False,
        },
    }
    site["readiness"] = evaluate_trade_readiness(site, integrity_ok=True)
    return site, paper, benchmarks


def _add_v3_challenger(site, paper):
    challenger = deepcopy(paper)
    challenger["strategy"] = "v3"
    challenger["pending_order"] = {"target_weights": {"QQQ": 1.0}}
    site["research_pipeline"] = {
        "challengers": {
            "v3": {
                "name": "v3",
                "current_target": {"QQQ": 1.0},
                "paper": {
                    "mode": "live",
                    "as_of": "2026-07-31",
                    "started_at": "2026-07-31",
                    "equity": 100_000.0,
                    "return": 0.0,
                    "cash": 100_000.0,
                    "snapshot_sha256": "abc",
                    "forward_sessions": 0,
                    "transactions": 0,
                    "pending_order": {"target_weights": {"QQQ": 1.0}},
                    "holdings": {},
                },
            }
        }
    }
    return challenger


def test_reference_audit_accepts_fresh_matching_live_state():
    site, paper, benchmarks = _fixtures()
    result = audit_live_reference(
        site, paper, benchmarks, now=datetime(2026, 8, 3, tzinfo=UTC)
    )
    assert result["ok"]
    assert result["integrity_ok"]
    assert result["safe_to_publish_paper_status"]
    assert result["status"] == "fresh"
    assert not result["trade_ready"]
    assert result["decision"] == "paper_only"
    assert result["readiness"]["passed_gate_count"] < result["readiness"][
        "required_gate_count"
    ]


def test_reference_audit_marks_expired_payload_stale():
    site, paper, benchmarks = _fixtures()
    result = audit_live_reference(
        site, paper, benchmarks, now=datetime(2026, 8, 4, 3, tzinfo=UTC)
    )
    assert not result["ok"]
    assert result["status"] == "stale"


def test_reference_audit_rejects_replay_or_weight_drift():
    site, paper, benchmarks = _fixtures()
    broken = deepcopy(paper)
    broken["mode"] = "replay"
    broken["pending_order"]["target_weights"] = {"QQQ": 1.0}
    result = audit_live_reference(
        site, broken, benchmarks, now=datetime(2026, 8, 3, tzinfo=UTC)
    )
    assert result["status"] == "invalid"
    assert any("LIVE paper" in item for item in result["errors"])
    assert any("權重" in item for item in result["errors"])


def test_reference_audit_rejects_benchmark_date_drift():
    site, paper, benchmarks = _fixtures()
    benchmarks["SPY"]["as_of"] = "2026-07-30"
    result = audit_live_reference(
        site, paper, benchmarks, now=datetime(2026, 8, 3, tzinfo=UTC)
    )
    assert result["status"] == "invalid"
    assert any("benchmark" in item for item in result["errors"])


def test_reference_audit_rejects_missing_exposure_control_benchmark():
    site, paper, benchmarks = _fixtures()
    del benchmarks[PASSIVE_BENCHMARK_KEY]
    result = audit_live_reference(
        site, paper, benchmarks, now=datetime(2026, 8, 3, tzinfo=UTC)
    )
    assert result["status"] == "invalid"
    assert any(PASSIVE_BENCHMARK_KEY in item for item in result["errors"])


def test_reference_audit_rejects_accounting_or_rebase_counter_drift():
    site, paper, benchmarks = _fixtures()
    paper["holdings"] = {
        "QQQ": {"shares": 10.0, "last_price": 100.0, "market_value": 1_000.0}
    }
    paper["adjustment_rebases"] = [{"ticker": "QQQ"}]
    result = audit_live_reference(
        site, paper, benchmarks, now=datetime(2026, 8, 3, tzinfo=UTC)
    )
    assert result["status"] == "invalid"
    assert any("權益不同" in item for item in result["errors"])
    assert any("重基準筆數" in item for item in result["errors"])
    assert any("持倉權重" in item for item in result["errors"])


def test_reference_audit_accepts_matching_v3_challenger_paper():
    site, paper, benchmarks = _fixtures()
    challenger = _add_v3_challenger(site, paper)
    result = audit_live_reference(
        site,
        paper,
        benchmarks,
        challenger_paper_state=challenger,
        now=datetime(2026, 8, 3, tzinfo=UTC),
    )
    assert result["ok"]
    assert result["challenger_paper_consistent"] is True


def test_reference_audit_rejects_v3_snapshot_or_order_drift():
    site, paper, benchmarks = _fixtures()
    challenger = _add_v3_challenger(site, paper)
    site_v3 = site["research_pipeline"]["challengers"]["v3"]
    site_v3["paper"]["snapshot_sha256"] = "wrong"
    site_v3["paper"]["pending_order"]["target_weights"] = {"QQQ": 0.5}
    result = audit_live_reference(
        site,
        paper,
        benchmarks,
        challenger_paper_state=challenger,
        now=datetime(2026, 8, 3, tzinfo=UTC),
    )
    assert result["status"] == "invalid"
    assert result["challenger_paper_consistent"] is False
    assert any("v3 Paper 使用的快照" in item for item in result["errors"])
    assert any("v3 Paper 的待成交權重" in item for item in result["errors"])


def test_trade_readiness_requires_every_historical_statistical_and_forward_gate():
    forward_gates = {
        "at_least_252_forward_sessions": True,
        "at_least_6_filled_rebalances": True,
        "positive_return_after_costs": True,
        "beats_spy_total_return": True,
        "beats_passive_90_10_total_return": True,
        "max_drawdown_no_worse_than_spy": True,
        "max_drawdown_no_worse_than_passive_90_10": True,
    }
    site = {
        "evidence": {
            "historical_gate_passed": True,
            "exposure_control_passed": True,
            "statistically_confirmed": True,
        },
        "paper": {"forward_evidence": {"gates": forward_gates}},
    }
    ready = evaluate_trade_readiness(site, integrity_ok=True)
    assert ready["trade_ready"]
    assert ready["decision"] == "reference_trade"
    assert ready["ui_mode"] == "reference_trade"
    assert ready["allocation_visible"] is True
    assert ready["passed_gate_count"] == ready["required_gate_count"] == 11

    site["evidence"]["statistically_confirmed"] = False
    rejected = evaluate_trade_readiness(site, integrity_ok=True)
    assert not rejected["trade_ready"]
    assert rejected["decision"] == "paper_only"
    assert rejected["ui_mode"] == "paper_only"
    assert rejected["allocation_visible"] is False
    assert rejected["failed"] == [
        {
            "gate": "statistically_confirmed",
            "label": "多重搜尋後的統計證據通過",
        }
    ]


def test_reference_receipt_chain_is_idempotent_and_rejects_same_snapshot_rewrite(
    tmp_path,
):
    site, paper, benchmarks = _fixtures()
    audit = audit_live_reference(
        site, paper, benchmarks, now=datetime(2026, 8, 3, tzinfo=UTC)
    )
    ledger = tmp_path / "live-evidence.jsonl"
    first = append_reference_receipt(
        ledger,
        site_payload=site,
        paper_state=paper,
        paper_benchmark_states=benchmarks,
        audit=audit,
    )
    assert first["appended"]
    assert first["sequence"] == 1
    assert verify_reference_receipt_ledger(ledger) == {
        "ok": True,
        "receipts": 1,
        "head_sha256": first["receipt_sha256"],
    }

    duplicate = append_reference_receipt(
        ledger,
        site_payload=site,
        paper_state=paper,
        paper_benchmark_states=benchmarks,
        audit=audit,
    )
    assert not duplicate["appended"]
    assert duplicate["receipt_sha256"] == first["receipt_sha256"]

    rewritten = deepcopy(paper)
    rewritten["cash"] = 99_999.0
    with pytest.raises(ValueError, match="拒絕靜默回填"):
        append_reference_receipt(
            ledger,
            site_payload=site,
            paper_state=rewritten,
            paper_benchmark_states=benchmarks,
            audit=audit,
        )


def test_live_refresh_status_distinguishes_new_session_from_idempotent_rerun(
    tmp_path,
):
    site, paper, benchmarks = _fixtures()
    challenger = _add_v3_challenger(site, paper)
    audit = audit_live_reference(
        site,
        paper,
        benchmarks,
        challenger_paper_state=challenger,
        now=datetime(2026, 8, 3, tzinfo=UTC),
    )
    accounts = {
        "v2": paper,
        "v3": challenger,
        "SPY": benchmarks["SPY"],
        "QQQ": benchmarks["QQQ"],
        PASSIVE_BENCHMARK_KEY: benchmarks[PASSIVE_BENCHMARK_KEY],
    }
    advanced = build_live_refresh_status(
        previous_data_through="2026-07-30",
        audit=audit,
        account_states=accounts,
        generated_at=datetime(2026, 8, 3, 12, tzinfo=UTC),
    )
    assert advanced["data_advanced"]
    assert advanced["private_deploy_allowed"]
    assert not advanced["reference_trade_allowed"]
    assert set(advanced["account_as_of"]) == {
        "v2",
        "v3",
        "SPY",
        "QQQ",
        PASSIVE_BENCHMARK_KEY,
    }
    output = write_live_refresh_status(tmp_path / "refresh.json", advanced)
    assert json.loads(output.read_text(encoding="utf-8")) == advanced
    assert not list(tmp_path.glob(".*.tmp"))

    same_day = build_live_refresh_status(
        previous_data_through="2026-07-31",
        audit=audit,
        account_states=accounts,
        generated_at=datetime(2026, 8, 3, 12, tzinfo=UTC),
    )
    assert not same_day["data_advanced"]
    assert same_day["idempotent_no_new_session"]
    assert not same_day["private_deploy_allowed"]


def test_live_refresh_status_rejects_date_regression_or_account_drift():
    site, paper, benchmarks = _fixtures()
    challenger = _add_v3_challenger(site, paper)
    audit = audit_live_reference(
        site,
        paper,
        benchmarks,
        challenger_paper_state=challenger,
        now=datetime(2026, 8, 3, tzinfo=UTC),
    )
    accounts = {
        "v2": paper,
        "v3": challenger,
        "SPY": benchmarks["SPY"],
        "QQQ": benchmarks["QQQ"],
        PASSIVE_BENCHMARK_KEY: benchmarks[PASSIVE_BENCHMARK_KEY],
    }
    with pytest.raises(ValueError, match="資料日期倒退"):
        build_live_refresh_status(
            previous_data_through="2026-08-01",
            audit=audit,
            account_states=accounts,
        )

    accounts["v3"] = deepcopy(accounts["v3"])
    accounts["v3"]["as_of"] = "2026-07-30"
    with pytest.raises(ValueError, match="v3 帳戶日期"):
        build_live_refresh_status(
            previous_data_through="2026-07-30",
            audit=audit,
            account_states=accounts,
        )
