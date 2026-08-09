from __future__ import annotations

import json
import re
from pathlib import Path

import scripts.build_short_term_leader_pullback_rebound_report as builder


def _fake_receipt() -> dict:
    path = {
        "label": "龍頭回調—回升 10 日／QQQ 疊加",
        "cagr": 0.12,
        "terminal_usd": 2_000.12345678901234,
        "shy_excess_sharpe": 0.5,
        "max_drawdown": -0.3,
        "annual_turnover": 8.0,
        "average_stock_driver_fraction": 0.25,
        "total_child_orders": 456,
        "negative_zero_probe": -0.0,
    }
    comparisons = [
        {
            "baseline_id": f"baseline_{index}",
            "baseline_label": f"公平基準 {index}",
            "annualized_arithmetic_difference": -0.01,
            "newey_west": {"t_stat": -0.5},
            "holm_adjusted_p": 1.0,
            "bootstrap_max_t_p": 1.0,
            "global_bonferroni_p": 1.0,
            "fixed_halves": {
                "first": {"mean_daily_difference": -0.0001},
                "second": {"mean_daily_difference": 0.0001},
            },
        }
        for index in range(8)
    ]
    gates = [
        {
            "id": "exact_inputs" if index == 1 else f"gate_{index:02d}",
            "label": f"固定門檻 {index}",
            "passed": 2 <= index <= 14,
        }
        for index in range(1, 23)
    ]
    controls = [
        {"id": f"{index:02d}", "label": f"control_{index}", "passed": True}
        for index in range(1, 49)
    ]
    attacks = [
        {
            "id": f"{index:02d}",
            "field": f"attack_{index}",
            "expected_error_code": "lpr_contract_mismatch",
            "rejected": True,
        }
        for index in range(1, 49)
    ]
    return {
        "schema_version": 1,
        "research_round": 39,
        "generated_on": "2026-08-09",
        "input": {
            "first_signal_date": "2006-08-04",
            "last_exit_date": "2026-07-31",
        },
        "selection_distribution": {
            "candidate_count_histogram": [
                {"candidate_count": 0, "events": 400},
                {"candidate_count": 1, "events": 505},
            ],
            "mean_candidates": 0.55,
            "mean_pullback": 0.07,
            "feature_distribution": {
                "pullback": {
                    "minimum": 0.0,
                    "median": 0.04,
                    "mean": 0.05,
                    "maximum": 0.2,
                },
                "reward_risk": {
                    "minimum": 0.1,
                    "median": 1.0,
                    "mean": 1.2,
                    "maximum": 8.0,
                },
            },
        },
        "calendar_integrity": {
            "sessions": 5028,
            "pre_trade_cash_sessions": 1,
            "comparison_trade_sessions": 5027,
            "protocol_calendar_internal_consistency": False,
            "maximum_concurrent_ten_day_intervals": 3,
            "terminal_state_all_cash": True,
            "terminal_exposure": {
                path_id: 0.0 for path_id in builder.EXPECTED_PATH_IDS
            },
            "terminal_position_count": {
                path_id: 0 for path_id in builder.EXPECTED_PATH_IDS
            },
            "order_diagnostics": {
                "primary": {
                    path_id: {
                        "expected_total_orders": 10,
                        "actual_total_orders": 10,
                    }
                    for path_id in builder.EXPECTED_PATH_IDS
                },
                "candidate_ledgers": {
                    "primary_10bps_per_leg": [{"sequence": 1}],
                    "fixed_fee_0.01_usd": [{"sequence": 1}],
                    "fixed_fee_0.05_usd": [{"sequence": 1}],
                },
            },
        },
        "paths": {
            "lpr10_qqq_overlay": path,
            "matched_topn_10d_overlay": {**path, "label": "matched Top-N"},
            "matched_eligible_10d_overlay": {**path, "label": "eligible"},
            "matched_complete_10d_overlay": {**path, "label": "complete"},
            "original_top7_10d_overlay": {**path, "label": "原 Top-7"},
            "matched_qqq_switch_placebo": {**path, "label": "QQQ placebo"},
            "qqq_buy_hold": {**path, "label": "QQQ 買入並持有"},
            "spy_buy_hold": {**path, "label": "SPY 買入並持有"},
            "shy_buy_hold": {**path, "label": "SHY 買入並持有"},
        },
        "family": {
            "candidate_id": "lpr10_qqq_overlay",
            "size": 8,
            "comparisons": comparisons,
        },
        "stresses": {
            "best_three_years_removed": {
                "removed_years": [2026, 2025, 2016],
                "mean_daily_difference": -0.0001,
                "newey_west": {"t_stat": -1.0},
            },
            "crisis_years": {},
            "known_at_qqq_regimes": {
                "negative": {"events": 100, "average_event_increment": -0.001}
            },
            "costs": {"50": {"paths": {"lpr10_qqq_overlay": path}}},
            "fixed_child_order_fees": {
                "0.01": {"paths": {"lpr10_qqq_overlay": path}}
            },
            "favorable_46_events_removed": {
                "removed_event_count": 46,
                "candidate_cagr_differences": {"qqq_buy_hold": -0.02},
            },
        },
        "gates": gates,
        "gate_summary": {"passed": 13, "total": 22, "all_passed": False},
        "controls": controls,
        "control_summary": {"passed": 48, "total": 48, "all_passed": True},
        "attacks": attacks,
        "attack_summary": {"rejected": 48, "total": 48, "all_rejected": True},
        "decision": {
            "can_promote_from_this_round": False,
            "new_strategy_created": False,
            "formal_readiness": "1/18",
            "point_in_time_readiness": "1/20",
            "formal_strategy_runs": 0,
            "paper_status": "all_cash_not_started",
            "paper_positions": 0,
            "real_money_action_usd": 0,
        },
    }


def test_builder_writes_canonical_identical_receipts_and_hong_kong_report(
    tmp_path: Path, monkeypatch
) -> None:
    artifact = tmp_path / "artifact.json"
    site_data = tmp_path / "site.json"
    report = tmp_path / "report.md"
    monkeypatch.setattr(builder, "ROOT", tmp_path)
    monkeypatch.setattr(builder, "ARTIFACT", artifact)
    monkeypatch.setattr(builder, "SITE_DATA", site_data)
    monkeypatch.setattr(builder, "REPORT", report)
    monkeypatch.setattr(builder, "run_leader_pullback_rebound", lambda root: _fake_receipt())

    builder.main()

    artifact_bytes = artifact.read_bytes()
    assert site_data.read_bytes() == artifact_bytes
    payload = artifact_bytes.decode("utf-8")
    result = json.loads(payload)
    assert result["receipt_float_decimal_places"] == 12
    assert result == builder._canonicalize_floats(result)
    assert re.search(r"(?<![\d.])-0\.0(?:[,\n])", payload) is None
    assert result["paths"]["lpr10_qqq_overlay"]["terminal_usd"] == 2000.123456789012

    text = report.read_text(encoding="utf-8")
    assert "13/22" in text
    assert "二十二項事前反證門檻" in text
    assert "九條固定完整資金路徑" in text
    assert "八假說共同統計 family" in text
    assert "調整開市買入" in text
    assert "調整收市沽出" in text
    assert "QQQ 買入並持有" in text
    assert "短線 Paper 維持全現金" in text
    assert "持倉 **0**" in text
    assert "實金動作 **US$0**" in text
    assert "不是即市行情" in text
    assert "實際比較交易期只有 **5,027**" in text
    assert "2006-08-04" in text
    assert "`protocol_calendar_internal_consistency=false`" in text
    assert "`exact_inputs` 門檻" in text and "**未通過**" in text
    assert "最大 concurrency 為\n**3**" in text
    assert "全現金、零持倉" in text
    assert "primary_10bps_per_leg" in text
    assert "fixed_fee_0.01_usd" in text
    assert "fixed_fee_0.05_usd" in text
    assert "attack_1" in text
    assert result["decision"]["can_promote_from_this_round"] is False
    assert result["decision"]["paper_status"] == "all_cash_not_started"
    assert result["decision"]["paper_positions"] == 0
    assert result["decision"]["real_money_action_usd"] == 0
