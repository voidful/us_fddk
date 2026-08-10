from __future__ import annotations

import json

import pytest

from usfddk.formal_report import (
    FORMAL_BASELINES,
    FORMAL_COSTS_BPS,
    FormalReportError,
    load_formal_receipt,
    render_formal_backtest_report,
)


def _success_receipt() -> dict[str, object]:
    metric = {
        "cagr": 0.12,
        "max_drawdown": -0.2,
        "volatility": 0.18,
        "excess_sharpe": 0.7,
        "annual_turnover": 1.4,
        "total_costs": 12.5,
        "transactions": 8,
        "terminal_usd": 1_250.0,
    }
    comparison = {
        "cagr_difference": 0.02,
        "max_drawdown_difference": -0.01,
        "positive_active_fraction": 0.54,
        "active_return_newey_west": {"t_stat": 1.2},
        "active_psr": {"probability": 0.81},
        "active_dsr": {"probability": 0.62, "trials": 6_287},
    }
    performance = {
        "metrics": {
            "candidate": dict(metric),
            **{key: dict(metric) for key in FORMAL_BASELINES},
        },
        "comparisons": {key: dict(comparison) for key in FORMAL_BASELINES},
    }
    return {
        "runner_version": "test",
        "run_id": "formal-test-001",
        "study_start": "2006-01-03",
        "study_end": "2025-12-31",
        "baseline_keys": list(FORMAL_BASELINES),
        "costs_bps": list(FORMAL_COSTS_BPS),
        "cost_runs": {
            str(cost): {"performance": json.loads(json.dumps(performance))}
            for cost in FORMAL_COSTS_BPS
        },
        "formal_stock_backtest_completed": True,
        "paper_authorized": False,
        "real_money_action_usd": 0,
        "public_promotion_allowed": False,
    }


def test_success_report_is_hk_finance_internal_and_has_all_frozen_paths() -> None:
    report = render_formal_backtest_report(_success_receipt())

    assert "短線正式回測內部研究報表" in report
    assert "最大跌幅" in report
    assert "波幅" in report
    assert "成交成本" in report
    assert "單邊 10 bps" in report
    assert "單邊 25 bps" in report
    assert "單邊 50 bps" in report
    for label in ("QQQ 買入並持有", "SPY 買入並持有", "PIT 合資格等權（月度）"):
        assert label in report
    assert "Paper：未授權" in report
    assert "實金動作：US$0" in report
    assert "不得接入公開決策頁" in report


def test_failure_receipt_is_a_log_and_never_a_strategy_report() -> None:
    report = render_formal_backtest_report(
        {
            "run_id": "failed-001",
            "status": "formal_backtest_failed_no_promotion",
            "failure_code": "benchmark_action_ledger_missing",
            "failure_detail": "QQQ／SPY 缺少公司行動 bridge",
            "formal_stock_backtest_completed": False,
            "paper_authorized": False,
            "real_money_action_usd": 0,
            "public_promotion_allowed": False,
        }
    )

    assert "內部研究 log" in report
    assert "benchmark_action_ledger_missing" in report
    assert "未授權；全現金" in report
    assert "單邊 10 bps" not in report
    assert "行動建議" in report


def test_report_rejects_paper_authorization_and_duplicate_receipts(tmp_path) -> None:
    receipt = _success_receipt()
    receipt["paper_authorized"] = True
    with pytest.raises(FormalReportError) as error:
        render_formal_backtest_report(receipt)
    assert error.value.code == "formal_report_promotion_boundary_invalid"

    run_dir = tmp_path / "run"
    run_dir.mkdir()
    (run_dir / "run_summary.json").write_text(
        json.dumps(_success_receipt()), encoding="utf-8"
    )
    (run_dir / "run_failure.json").write_text(
        json.dumps(
            {
                "status": "formal_backtest_failed_no_promotion",
                "failure_code": "x",
                "failure_detail": "y",
                "formal_stock_backtest_completed": False,
                "paper_authorized": False,
                "real_money_action_usd": 0,
                "public_promotion_allowed": False,
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(FormalReportError) as duplicate:
        load_formal_receipt(run_dir)
    assert duplicate.value.code == "formal_report_input_invalid"
