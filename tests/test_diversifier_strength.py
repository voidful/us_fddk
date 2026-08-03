from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np

from usfddk.cli import main as cli_main
from usfddk.data import load_snapshot, panel_fingerprint
from usfddk.diversifier_strength import (
    V20_EXTERNAL_ARCHIVE_SHA256,
    V20_EXTERNAL_PANEL_SHA256,
    V20_PROTOCOL_SHA256,
)
from usfddk.report import build_diversifier_strength_report
from usfddk.strategies import diversifier_relative_strength_targets

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "docs/V20_DIVERSIFIER_RELATIVE_STRENGTH_PROTOCOL.md"
PROTOCOL_RECEIPT = ROOT / "artifacts/v20_protocol_receipt.json"
DATA_RECEIPT = ROOT / "artifacts/v20_data_receipt.json"
MAPPING_RECEIPT = ROOT / "artifacts/v20_product_mapping_receipt.json"
SNAPSHOT = ROOT / "artifacts/snapshot_v20_diversifier_strength_20060803_20260731_e30b4032.zip"
VALIDATION = ROOT / "artifacts/v20_diversifier_strength_validation.json"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_v20_targets_select_exactly_two_diversifiers_and_150pct_notional() -> None:
    panel, _ = load_snapshot(SNAPSHOT)
    targets = diversifier_relative_strength_targets(
        panel.close,
        equity="EZJ",
        equity_weight=0.50,
        selected_count=2,
        selected_weight=0.25,
    ).dropna(how="all")
    assert len(targets) > 100
    assert np.allclose(targets.sum(axis=1), 1.0)
    assert ((targets[["IEF", "GLD", "SHY"]] > 0.0).sum(axis=1) == 2).all()
    assert np.allclose(
        2.0 * targets["EZJ"] + targets[["IEF", "GLD", "SHY"]].sum(axis=1),
        1.50,
    )
    assert set(targets.iloc[-1][targets.iloc[-1] > 0.0].index) == {
        "EZJ",
        "IEF",
        "GLD",
    }


def test_v20_freeze_precedes_external_snapshot_and_hashes_are_fixed() -> None:
    protocol_receipt = json.loads(PROTOCOL_RECEIPT.read_text(encoding="utf-8"))
    data_receipt = json.loads(DATA_RECEIPT.read_text(encoding="utf-8"))
    mapping = json.loads(MAPPING_RECEIPT.read_text(encoding="utf-8"))
    panel, manifest = load_snapshot(SNAPSHOT)
    assert _sha256(PROTOCOL) == V20_PROTOCOL_SHA256
    assert protocol_receipt["protocol_sha256"] == V20_PROTOCOL_SHA256
    assert (
        protocol_receipt["protocol_mtime_epoch"] < data_receipt["download"]["snapshot_mtime_epoch"]
    )
    assert data_receipt["pre_registration_order_proved"] is True
    assert mapping["status"] == "all_three_pairs_definition_compatible_for_formal_period"
    assert panel_fingerprint(panel) == V20_EXTERNAL_PANEL_SHA256
    assert _sha256(SNAPSHOT) == V20_EXTERNAL_ARCHIVE_SHA256
    assert manifest["contract"]["ok"] is True


def test_v20_frozen_result_rejects_paper_and_records_all_markets() -> None:
    audit = json.loads(VALIDATION.read_text(encoding="utf-8"))
    assert audit["status"] == "diversifier_rotation_validation_failed"
    assert audit["paper_eligible"] is False
    assert audit["design_economic_passed_gate_count"] == 38
    assert audit["design_economic_required_gate_count"] == 112
    assert audit["external_economic_passed_gate_count"] == 7
    assert audit["external_economic_required_gate_count"] == 42
    assert audit["economic_passed_gate_count"] == 45
    assert audit["economic_required_gate_count"] == 154
    assert audit["data_passed_gate_count"] == 13
    assert audit["data_required_gate_count"] == 13
    assert audit["statistical_passed_gate_count"] == 0
    assert audit["statistical_required_gate_count"] == 27
    assert set(audit["datasets"]) == {
        "sp500",
        "nasdaq100",
        "dow30",
        "midcap400",
        "russell2000",
        "smallcap600",
        "developed_ex_us",
        "emerging_markets",
        "japan",
        "china_large_cap",
        "brazil",
    }
    assert sum(audit["datasets"]["china_large_cap"]["economic_gates"].values()) == 0
    for data in audit["datasets"].values():
        assert data["data_gate_passed"] is True
        assert data["strategy_metrics"]["cagr"] < data["benchmark_metrics"]["fixed_v18"]["cagr"]


def test_v20_report_and_paper_guard(tmp_path: Path) -> None:
    audit = json.loads(VALIDATION.read_text(encoding="utf-8"))
    report = build_diversifier_strength_report(tmp_path / "v20.html", audit)
    text = report.read_text(encoding="utf-8")
    assert "輪替沒有改善固定股債金" in text
    assert "45/154" in text
    state = tmp_path / "paper_v20_state.json"
    code = cli_main(
        [
            "paper",
            "update",
            "--snapshot",
            str(SNAPSHOT),
            "--strategy",
            "v20",
            "--state",
            str(state),
        ]
    )
    assert code == 2
    assert not state.exists()
