from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from usfddk.cli import main as cli_main
from usfddk.data import load_snapshot, panel_fingerprint
from usfddk.growth_gold_diversification import (
    V25_ARCHIVE_HASHES,
    V25_FORWARD_PROMOTION_PROTOCOL,
    V25_FORWARD_PROMOTION_PROTOCOL_SHA256,
    V25_GLOBAL_SEARCH_TRIALS,
    V25_PANEL_HASHES,
    V25_PRODUCT_MAPPING_SHA256,
    V25_PROTOCOL_SHA256,
    v25_forward_paper_evidence,
)
from usfddk.report import build_growth_gold_diversification_report

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "docs/V25_GROWTH_GOLD_DIVERSIFICATION_PROTOCOL.md"
MAPPING = ROOT / "docs/V25_PRODUCT_MAPPING.md"
PROTOCOL_RECEIPT = ROOT / "artifacts/v25_protocol_receipt.json"
DATA_RECEIPT = ROOT / "artifacts/v25_data_receipt.json"
SNAPSHOTS = {
    "vanguard": ROOT / "artifacts/snapshot_v25_vanguard_20060701_20260731_6cf44e63.zip",
    "ishares": ROOT / "artifacts/snapshot_v25_ishares_20060701_20260731_88dc9a27.zip",
    "state_street": ROOT / "artifacts/snapshot_v25_state_street_20060701_20260731_7a32250e.zip",
}
VALIDATION = ROOT / "artifacts/v25_growth_gold_diversification_validation.json"
FORWARD_PROMOTION_CONTRACT = ROOT / "artifacts/v25_forward_promotion_contract.json"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _v25_forward_state(name: str, daily_returns: np.ndarray) -> dict:
    dates = pd.bdate_range("2026-01-02", periods=len(daily_returns) + 1)
    equity = 100_000.0 * np.cumprod(np.r_[1.0, 1.0 + daily_returns])
    filled_signal_dates = [dates[0], *[dates[position] for position in (20, 40, 60, 80, 100, 120)]]
    return {
        "mode": "live",
        "strategy": name,
        "execution_clock": "signal at close t; rebalance at adjusted open t+1",
        "started_at": dates[0].strftime("%Y-%m-%d"),
        "as_of": dates[-1].strftime("%Y-%m-%d"),
        "snapshot_sha256": "same-forward-snapshot",
        "initial_cash": 100_000.0,
        "cash": 0.0,
        "cost_bps": 10.0,
        "holdings": {},
        "pending_order": None,
        "integrity_violations": [],
        "order_history": [
            {
                "status": "filled",
                "signal_date": day.strftime("%Y-%m-%d"),
                "execute_after": day.strftime("%Y-%m-%d"),
                "filled_at": dates[min(position * 20 + 1, len(dates) - 1)].strftime("%Y-%m-%d"),
            }
            for position, day in enumerate(filled_signal_dates)
        ],
        "transactions": [],
        "equity_curve": [
            {
                "date": day.strftime("%Y-%m-%d"),
                "equity": float(value),
                "cash": 0.0,
                "turnover": 0.0,
                "cost": 0.0,
                "drawdown": float(value / max(equity[: position + 1]) - 1.0),
            }
            for position, (day, value) in enumerate(zip(dates, equity, strict=True))
        ],
    }


def test_v25_frozen_protocol_precedes_all_first_product_downloads() -> None:
    protocol = json.loads(PROTOCOL_RECEIPT.read_text(encoding="utf-8"))
    data = json.loads(DATA_RECEIPT.read_text(encoding="utf-8"))
    assert _sha256(PROTOCOL) == V25_PROTOCOL_SHA256
    assert _sha256(MAPPING) == V25_PRODUCT_MAPPING_SHA256
    assert protocol["global_trial_count"] == V25_GLOBAL_SEARCH_TRIALS
    assert protocol["v25_joint_daily_paths_seen_before_freeze"] is False
    frozen = max(protocol["protocol_mtime_epoch"], protocol["product_mapping_mtime_epoch"])
    for label, path in SNAPSHOTS.items():
        panel, manifest = load_snapshot(path)
        receipt = data["snapshots"][label]
        assert panel_fingerprint(panel) == V25_PANEL_HASHES[label]
        assert _sha256(path) == V25_ARCHIVE_HASHES[label]
        assert manifest["contract"]["ok"] is True
        assert receipt["snapshot_mtime_epoch"] > frozen
        assert receipt["performed_once"] is True
    split = data["vug_split_adjustment_audit"]
    assert split["official_split_ratio"] == "6:1"
    assert split["passed"] is True
    assert split["maximum_absolute_adjusted_daily_move"] < 0.65


def test_v25_forward_promotion_contract_is_machine_frozen_before_first_fill() -> None:
    contract = json.loads(FORWARD_PROMOTION_CONTRACT.read_text(encoding="utf-8"))
    sha256 = contract.pop("sha256")
    assert contract == V25_FORWARD_PROMOTION_PROTOCOL
    assert sha256 == V25_FORWARD_PROMOTION_PROTOCOL_SHA256
    candidate = json.loads((ROOT / "artifacts/paper_v25_state.json").read_text(encoding="utf-8"))
    assert candidate["transactions"] == []
    assert candidate["order_history"] == []


def test_v25_three_product_paths_and_pooled_gate_pass() -> None:
    audit = json.loads(VALIDATION.read_text(encoding="utf-8"))
    assert audit["status"] == "growth_gold_diversification_passed_for_isolated_paper"
    assert audit["paper_eligible"] is True
    assert audit["trade_ready"] is False
    assert audit["candidate"]["signal_display_allowed"] is True
    assert audit["all_paths_passed"] is True
    for path in audit["paths"].values():
        assert path["period"]["months"] == 240
        assert path["passed_gate_count"] == path["required_gate_count"] == 12
        assert all(path["entry_gates"].values())
        assert path["strategy_metrics"]["cagr"] > path["benchmark_metrics"]["SPY"]["cagr"]
        assert (
            path["strategy_metrics"]["max_drawdown"]
            > path["benchmark_metrics"]["SPY"]["max_drawdown"]
        )
    pooled = audit["pooled"]
    assert pooled["passed_gate_count"] == pooled["required_gate_count"] == 10
    assert pooled["strategy_metrics"]["cagr"] > pooled["spy_metrics"]["cagr"]
    assert pooled["strategy_metrics"]["cagr"] > pooled["matched_metrics"]["cagr"]
    assert pooled["strategy_metrics"]["cagr"] < pooled["growth_metrics"]["cagr"]
    assert pooled["strategy_metrics"]["sharpe"] > pooled["growth_metrics"]["sharpe"]
    assert pooled["comparison_vs_growth"]["drawdown_improvement"] > 0.10
    assert pooled["rolling_five_year_vs_SPY"]["summary"]["cagr_win_fraction"] >= 0.60
    assert pooled["rolling_five_year_vs_growth"]["summary"]["cagr_win_fraction"] < 0.20
    diagnostics = pooled["post_entry_diagnostics_not_used_for_frozen_gate"]
    assert diagnostics["used_for_frozen_entry_gate"] is False
    assert diagnostics["portfolio_underwater"]["max_underwater_months"] == 35
    assert diagnostics["relative_wealth_underwater"]["growth"]["max_underwater_months"] == 179
    assert (
        diagnostics["relative_wealth_underwater"]["growth"]["longest_episode"]["recovered"] is False
    )
    bootstrap = diagnostics["paired_moving_block_bootstrap"]
    assert bootstrap["used_for_frozen_entry_gate"] is False
    spy_12 = bootstrap["benchmarks"]["SPY"]["12"]
    growth_12 = bootstrap["benchmarks"]["growth"]["12"]
    matched_12 = bootstrap["benchmarks"]["matched"]["12"]
    assert 0.84 < spy_12["probability_cagr_above"] < 0.86
    assert spy_12["cagr_difference_percentiles"]["p05"] < 0
    assert 0.72 < spy_12["probability_cagr_above_and_drawdown_not_worse"] < 0.75
    assert growth_12["probability_cagr_above"] < 0.40
    assert matched_12["probability_cagr_above"] > 0.98
    assert 0.58 < matched_12["probability_cagr_above_and_drawdown_not_worse"] < 0.62
    assert audit["data_passed_gate_count"] == audit["data_required_gate_count"] == 8


def test_v25_keeps_statistical_weakness_and_trade_gate_visible() -> None:
    audit = json.loads(VALIDATION.read_text(encoding="utf-8"))
    pooled = audit["pooled"]
    assert pooled["comparison_vs_SPY"]["active_return_newey_west"]["t_stat"] < 1.96
    assert (
        pooled["comparison_vs_SPY"]["active_global_deflated_sharpe"]["trials"]
        == V25_GLOBAL_SEARCH_TRIALS
    )
    assert pooled["comparison_vs_SPY"]["active_global_deflated_sharpe"]["probability"] < 0.95
    assert pooled["rolling_five_year_vs_SPY"]["summary"]["worst_cagr_difference"] < 0
    assert audit["reference_trade_candidate"] is True
    assert audit["trade_ready"] is False


def test_v25_report_and_isolated_paper_initialization(tmp_path: Path) -> None:
    audit = json.loads(VALIDATION.read_text(encoding="utf-8"))
    report = build_growth_gold_diversification_report(tmp_path / "v25.html", audit)
    text = report.read_text(encoding="utf-8")
    assert "歷史產品入口通過，只啟動隔離 Paper" in text
    assert "只建立 Paper，不用實金照抄" in text
    assert "統計確認仍不足" in text
    assert "沒有跑贏 100% 大型成長" in text
    assert "最大跌幅多久才回來" in text
    assert "不參與通過數" in text
    assert "區塊重抽樣" in text
    assert "不是未來勝率" in text
    assert 'lang="zh-Hant-HK"' in text
    assert "報告架構參考" in text
    assert "中文採香港金融市場慣用詞" in text
    for discouraged_term in (
        "報酬",
        "績效",
        "回撤",
        "買進",
        "賣出",
        "下單",
        "資料",
        "新手",
        "部位",
        "曝險",
        "再平衡",
        "年化",
        "波動率",
        "收盤",
        "開盤",
        "停損",
    ):
        assert discouraged_term not in text

    state_path = tmp_path / "paper_v25_state.json"
    paper_report = tmp_path / "paper_v25.html"
    code = cli_main(
        [
            "paper",
            "update",
            "--snapshot",
            str(SNAPSHOTS["vanguard"]),
            "--strategy",
            "v25",
            "--eligibility-receipt",
            str(VALIDATION),
            "--state",
            str(state_path),
            "--report",
            str(paper_report),
        ]
    )
    assert code == 0
    state = json.loads(state_path.read_text(encoding="utf-8"))
    assert state["mode"] == "live"
    assert state["as_of"] == "2026-07-31"
    assert len(state["equity_curve"]) == 1
    assert state["transactions"] == []
    assert state["pending_order"]["target_weights"] == {"GLD": 0.2, "VUG": 0.8}
    assert paper_report.exists()


def test_v25_new_paper_bundle_does_not_claim_forward_confirmation() -> None:
    candidate = json.loads((ROOT / "artifacts/paper_v25_state.json").read_text(encoding="utf-8"))
    spy = json.loads((ROOT / "artifacts/paper_v25_spy_state.json").read_text(encoding="utf-8"))
    matched = json.loads(
        (ROOT / "artifacts/paper_v25_matched_state.json").read_text(encoding="utf-8")
    )
    evidence = v25_forward_paper_evidence(candidate, spy, matched)
    assert evidence["forward_sessions"] == 0
    assert evidence["filled_rebalances"] == 0
    assert evidence["candidate"]["equity"] == 100_000.0
    assert evidence["live_confirmed"] is False
    assert evidence["promotion_protocol"]["schema_version"] == 2
    assert evidence["promotion_protocol"]["frozen_before_first_forward_fill"] is True
    assert len(evidence["promotion_protocol_sha256"]) == 64
    assert evidence["filled_orders_including_initial_allocation"] == 0
    assert evidence["initial_allocations"] == 0
    assert evidence["gates"]["all_accounts_live_and_same_start"] is True
    assert evidence["gates"]["at_least_252_new_sessions"] is False
    assert evidence["gates"]["candidate_outperforms_SPY_in_both_halves"] is False
    assert evidence["gates"]["candidate_active_newey_west_t_at_least_1_96_vs_SPY"] is False


def test_v25_forward_promotion_requires_material_persistent_statistical_edge() -> None:
    positions = np.arange(252, dtype=float)
    candidate = _v25_forward_state(
        "candidate",
        0.00075 + 0.00012 * np.sin(positions / 7.0),
    )
    spy_returns = 0.00030 + 0.00015 * np.sin(positions / 11.0)
    spy = _v25_forward_state("SPY", spy_returns)
    matched = _v25_forward_state(
        "matched",
        0.00025 + 0.00012 * np.cos(positions / 13.0),
    )
    evidence = v25_forward_paper_evidence(candidate, spy, matched)
    assert evidence["forward_sessions"] == 252
    assert evidence["filled_orders_including_initial_allocation"] == 7
    assert evidence["initial_allocations"] == 1
    assert evidence["filled_rebalances"] == 6
    assert evidence["gates"]["all_accounts_same_execution_clock"]
    assert evidence["gates"]["all_accounts_same_order_path"]
    assert evidence["gates"]["all_accounts_same_fill_counts"]
    assert evidence["gates"]["all_accounts_exactly_one_initial_allocation"]
    assert evidence["gates"]["candidate_annualized_edge_at_least_10bp_vs_SPY"]
    assert evidence["gates"]["candidate_outperforms_SPY_in_both_halves"]
    assert evidence["gates"]["candidate_active_newey_west_t_at_least_1_96_vs_SPY"]
    assert evidence["live_confirmed"] is True

    tiny_edge = _v25_forward_state(
        "candidate",
        spy_returns + 0.000003 + 0.000001 * np.sin(positions / 5.0),
    )
    weak = v25_forward_paper_evidence(tiny_edge, spy, matched)
    assert weak["candidate"]["return"] > weak["SPY"]["return"]
    assert weak["gates"]["candidate_return_above_SPY"] is True
    assert weak["gates"]["candidate_annualized_edge_at_least_10bp_vs_SPY"] is False
    assert weak["live_confirmed"] is False


def test_v25_atomic_paper_bundle_keeps_all_accounts_aligned(tmp_path: Path) -> None:
    candidate_path = tmp_path / "paper_v25_state.json"
    spy_path = tmp_path / "paper_v25_spy_state.json"
    matched_path = tmp_path / "paper_v25_matched_state.json"
    evidence_path = tmp_path / "v25_forward_paper_evidence.json"
    code = cli_main(
        [
            "v25-paper-bundle",
            "--snapshot",
            str(SNAPSHOTS["vanguard"]),
            "--eligibility-receipt",
            str(VALIDATION),
            "--candidate-state",
            str(candidate_path),
            "--spy-state",
            str(spy_path),
            "--matched-state",
            str(matched_path),
            "--evidence",
            str(evidence_path),
        ]
    )
    assert code == 0
    states = [
        json.loads(path.read_text(encoding="utf-8"))
        for path in (candidate_path, spy_path, matched_path)
    ]
    assert {state["started_at"] for state in states} == {"2026-07-31"}
    assert {state["as_of"] for state in states} == {"2026-07-31"}
    assert all(state["transactions"] == [] for state in states)
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    assert evidence["forward_sessions"] == 0
    assert evidence["filled_rebalances"] == 0
    assert evidence["live_confirmed"] is False
