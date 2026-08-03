from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pytest

from usfddk.cli import main as cli_main
from usfddk.data import load_snapshot, panel_fingerprint
from usfddk.hybrid_leverage_core import (
    V21_EXTERNAL_ARCHIVE_SHA256,
    V21_EXTERNAL_PANEL_SHA256,
    V21_PRODUCT_MAPPING_SHA256,
    V21_PROTOCOL_SHA256,
)
from usfddk.report import build_hybrid_leverage_core_report
from usfddk.strategies import hybrid_leverage_core_targets

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "docs/V21_HYBRID_LEVERAGE_CORE_PROTOCOL.md"
MAPPING = ROOT / "docs/V21_PRODUCT_MAPPING.md"
PROTOCOL_RECEIPT = ROOT / "artifacts/v21_protocol_receipt.json"
DATA_RECEIPT = ROOT / "artifacts/v21_data_receipt.json"
MAPPING_RECEIPT = ROOT / "artifacts/v21_product_mapping_receipt.json"
EXTERNAL_SNAPSHOT = (
    ROOT / "artifacts/snapshot_v21_hybrid_core_20080102_20260731_45f452a2.zip"
)
CAPITAL_SNAPSHOT = (
    ROOT / "artifacts/snapshot_v17_capital_efficient_20040102_20260731_4c948bf6.zip"
)
VALIDATION = ROOT / "artifacts/v21_hybrid_leverage_core_validation.json"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_v21_targets_hold_exact_frozen_physical_and_notional_weights() -> None:
    capital, _ = load_snapshot(CAPITAL_SNAPSHOT)
    two_x = hybrid_leverage_core_targets(
        capital.close,
        core="SPY",
        leveraged="SSO",
        defensive="SHY",
        daily_target_multiplier=2,
    ).dropna(how="all")
    assert len(two_x) > 200
    assert np.allclose(two_x.sum(axis=1), 1.0)
    assert np.allclose(two_x["SPY"], 0.60)
    assert set(np.round(two_x["SSO"].unique(), 8)) == {0.0, 0.30}
    assert set(np.round(two_x["SHY"].unique(), 8)) == {0.10, 0.40}
    assert set(np.round((two_x["SPY"] + 2 * two_x["SSO"]).unique(), 8)) == {
        0.60,
        1.20,
    }

    external, _ = load_snapshot(EXTERNAL_SNAPSHOT)
    three_x = hybrid_leverage_core_targets(
        external.close,
        core="IJH",
        leveraged="UMDD",
        defensive="SHY",
        daily_target_multiplier=3,
    ).dropna(how="all")
    assert np.allclose(three_x.sum(axis=1), 1.0)
    assert np.allclose(three_x["IJH"], 0.60)
    assert set(np.round(three_x["UMDD"].unique(), 8)) == {0.0, 0.20}
    assert set(np.round(three_x["SHY"].unique(), 8)) == {0.20, 0.40}
    assert set(np.round((three_x["IJH"] + 3 * three_x["UMDD"]).unique(), 8)) == {
        0.60,
        1.20,
    }
    with pytest.raises(ValueError, match="每日 2 倍或 3 倍"):
        hybrid_leverage_core_targets(
            external.close,
            core="IJH",
            leveraged="UMDD",
            defensive="SHY",
            daily_target_multiplier=4,
        )


def test_v21_freeze_mapping_and_external_snapshot_are_fixed() -> None:
    protocol = json.loads(PROTOCOL_RECEIPT.read_text(encoding="utf-8"))
    data = json.loads(DATA_RECEIPT.read_text(encoding="utf-8"))
    mapping = json.loads(MAPPING_RECEIPT.read_text(encoding="utf-8"))
    panel, manifest = load_snapshot(EXTERNAL_SNAPSHOT)
    assert _sha256(PROTOCOL) == V21_PROTOCOL_SHA256
    assert _sha256(MAPPING) == V21_PRODUCT_MAPPING_SHA256
    assert protocol["protocol_sha256"] == V21_PROTOCOL_SHA256
    assert protocol["product_mapping_sha256"] == V21_PRODUCT_MAPPING_SHA256
    assert mapping["gate_passed"] is True
    assert protocol["protocol_mtime_epoch"] < data["download"]["snapshot_mtime_epoch"]
    assert protocol["product_mapping_mtime_epoch"] < data["download"]["snapshot_mtime_epoch"]
    assert data["pre_registration_order_proved"] is True
    assert panel_fingerprint(panel) == V21_EXTERNAL_PANEL_SHA256
    assert _sha256(EXTERNAL_SNAPSHOT) == V21_EXTERNAL_ARCHIVE_SHA256
    assert manifest["contract"]["ok"] is True
    assert manifest["tickers"] == ["IJH", "IWM", "SHY", "UMDD", "URTY"]


def test_v21_frozen_result_rejects_paper_and_records_all_datasets() -> None:
    audit = json.loads(VALIDATION.read_text(encoding="utf-8"))
    assert audit["status"] == "hybrid_leverage_core_validation_failed"
    assert audit["paper_eligible"] is False
    assert audit["trade_ready"] is False
    assert audit["configuration_visible"] is False
    assert audit["design_economic_passed_gate_count"] == 49
    assert audit["design_economic_required_gate_count"] == 96
    assert audit["external_economic_passed_gate_count"] == 4
    assert audit["external_economic_required_gate_count"] == 32
    assert audit["economic_passed_gate_count"] == 53
    assert audit["economic_required_gate_count"] == 128
    assert audit["data_passed_gate_count"] == 10
    assert audit["data_required_gate_count"] == 10
    assert audit["statistical_passed_gate_count"] == 0
    assert audit["statistical_required_gate_count"] == 18
    assert set(audit["datasets"]) == {
        "sp500_2x",
        "nasdaq100_2x",
        "dow30_2x",
        "sp500_3x",
        "nasdaq100_3x",
        "dow30_3x",
        "midcap400_3x",
        "russell2000_3x",
    }
    for key in ("midcap400_3x", "russell2000_3x"):
        data = audit["datasets"][key]
        assert sum(data["economic_gates"].values()) == 2
        assert data["data_gate_passed"] is True
        assert data["strategy_metrics"]["cagr"] < data["benchmark_metrics"]["core"]["cagr"]
        assert (
            data["strategy_metrics"]["max_drawdown"]
            < data["benchmark_metrics"]["core"]["max_drawdown"]
        )


def test_v21_report_and_paper_guard(tmp_path: Path) -> None:
    audit = json.loads(VALIDATION.read_text(encoding="utf-8"))
    report = build_hybrid_leverage_core_report(tmp_path / "v21.html", audit)
    text = report.read_text(encoding="utf-8")
    assert "中小型股外部驗證否決候選" in text
    assert "53/128" in text
    state = tmp_path / "paper_v21_state.json"
    code = cli_main(
        [
            "paper",
            "update",
            "--snapshot",
            str(CAPITAL_SNAPSHOT),
            "--strategy",
            "v21",
            "--state",
            str(state),
        ]
    )
    assert code == 2
    assert not state.exists()
