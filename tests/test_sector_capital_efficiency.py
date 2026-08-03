from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np

from usfddk.cli import main as cli_main
from usfddk.data import load_snapshot, panel_fingerprint
from usfddk.engine import run_backtest
from usfddk.hierarchical_defense import _slice_result
from usfddk.report import build_sector_capital_efficiency_report
from usfddk.sector_capital_efficiency import (
    V22_ARCHIVE_SHA256,
    V22_DESIGN_SOURCE_SHA256,
    V22_FORMAL_END,
    V22_FORMAL_START,
    V22_PANEL_SHA256,
    V22_PRODUCT_MAPPING_SHA256,
    V22_PROTOCOL_SHA256,
    V22_TICKERS,
    _run_sparse_backtest,
)
from usfddk.strategies import fixed_weight_targets

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "docs/V22_US_SECTOR_CAPITAL_EFFICIENCY_PROTOCOL.md"
MAPPING = ROOT / "docs/V22_PRODUCT_MAPPING.md"
DESIGN_SOURCE = ROOT / "docs/V18_DESIGN_EXPLORATION.md"
PROTOCOL_RECEIPT = ROOT / "artifacts/v22_protocol_receipt.json"
MAPPING_RECEIPT = ROOT / "artifacts/v22_product_mapping_receipt.json"
DATA_RECEIPT = ROOT / "artifacts/v22_data_receipt.json"
SNAPSHOT = (
    ROOT
    / "artifacts/snapshot_v22_us_sectors_20030102_20190621_52450c12_validated.zip"
)
PAPER_SNAPSHOT = ROOT / "artifacts/snapshot_20260731_6a7ca6b8.zip"
VALIDATION = ROOT / "artifacts/v22_us_sector_capital_efficiency_validation.json"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_v22_frozen_documents_and_single_download_snapshot_are_fixed() -> None:
    protocol = json.loads(PROTOCOL_RECEIPT.read_text(encoding="utf-8"))
    mapping = json.loads(MAPPING_RECEIPT.read_text(encoding="utf-8"))
    data = json.loads(DATA_RECEIPT.read_text(encoding="utf-8"))
    panel, manifest = load_snapshot(SNAPSHOT)
    assert _sha256(PROTOCOL) == V22_PROTOCOL_SHA256
    assert _sha256(MAPPING) == V22_PRODUCT_MAPPING_SHA256
    assert _sha256(DESIGN_SOURCE) == V22_DESIGN_SOURCE_SHA256
    assert protocol["protocol_sha256"] == V22_PROTOCOL_SHA256
    assert protocol["product_mapping_sha256"] == V22_PRODUCT_MAPPING_SHA256
    assert mapping["passed_pair_count"] == 9
    assert data["pre_registration_order_proved"] is True
    assert data["jump_audit"]["audit_passed"] is True
    assert data["jump_audit"]["redownload_performed"] is False
    assert protocol["protocol_mtime_epoch"] < data["download"]["snapshot_mtime_epoch"]
    assert panel_fingerprint(panel) == V22_PANEL_SHA256
    assert _sha256(SNAPSHOT) == V22_ARCHIVE_SHA256
    assert manifest["contract"]["ok"] is True
    assert tuple(manifest["tickers"]) == V22_TICKERS


def test_v22_sparse_monthly_engine_is_exactly_equal_to_daily_engine() -> None:
    panel, _ = load_snapshot(SNAPSHOT)
    targets = fixed_weight_targets(
        panel.close, {"UYM": 0.50, "IEF": 0.25, "GLD": 0.25}
    )
    first_signal = targets.dropna(how="all").index[0]
    start = panel.close.index[panel.close.index.get_loc(first_signal) + 1]
    daily = _slice_result(
        run_backtest(panel, targets, name="daily", cost_bps=10.0, start=start),
        V22_FORMAL_START,
        V22_FORMAL_END,
    )
    sparse = _slice_result(
        _run_sparse_backtest(
            panel, targets, name="sparse", cost_bps=10.0, start=start
        ),
        V22_FORMAL_START,
        V22_FORMAL_END,
    )
    for attribute in ("equity", "returns", "turnover", "costs", "weights"):
        assert np.array_equal(
            getattr(daily, attribute).to_numpy(),
            getattr(sparse, attribute).to_numpy(),
        )
    assert daily.metrics == sparse.metrics


def test_v22_frozen_result_fails_only_the_preregistered_rolling_consistency() -> None:
    audit = json.loads(VALIDATION.read_text(encoding="utf-8"))
    assert audit["status"] == "us_sector_capital_efficiency_validation_failed"
    assert audit["paper_eligible"] is False
    assert audit["trade_ready"] is False
    assert audit["individual_passed_gate_count"] == 51
    assert audit["individual_required_gate_count"] == 63
    assert audit["economic_passed_gate_count"] == 13
    assert audit["economic_required_gate_count"] == 15
    assert audit["data_passed_gate_count"] == 11
    assert audit["data_required_gate_count"] == 11
    assert audit["statistical_passed_gate_count"] == 0
    assert audit["statistical_required_gate_count"] == 3
    assert audit["individual_pass_count_by_gate"][
        "rolling_wins_60pct_and_positive_median"
    ] == 0
    assert audit["consistency_gates"][
        "each_gate_passes_in_at_least_6_of_9_sectors"
    ] is False
    assert audit["pooled"]["economic_gates"][
        "rolling_wins_60pct_and_positive_median"
    ] is False
    assert sum(audit["pooled"]["economic_gates"].values()) == 8
    assert audit["pooled"]["strategy_metrics"]["cagr"] > audit["pooled"][
        "core_metrics"
    ]["cagr"]
    assert audit["pooled"]["strategy_metrics"]["max_drawdown"] < -0.50


def test_v22_report_and_paper_guard(tmp_path: Path) -> None:
    audit = json.loads(VALIDATION.read_text(encoding="utf-8"))
    report = build_sector_capital_efficiency_report(tmp_path / "v22.html", audit)
    text = report.read_text(encoding="utf-8")
    assert "九產業壓力測試未達入口，不進 Paper" in text
    assert "51/63" in text
    state = tmp_path / "paper_v22_state.json"
    code = cli_main(
        [
            "paper",
            "update",
            "--snapshot",
            str(PAPER_SNAPSHOT),
            "--strategy",
            "v22",
            "--state",
            str(state),
        ]
    )
    assert code == 2
    assert not state.exists()
