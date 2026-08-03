from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from usfddk.cli import main as cli_main
from usfddk.data import load_snapshot, panel_fingerprint
from usfddk.report import build_trend_volatility_brake_report
from usfddk.strategies import trend_volatility_brake_targets
from usfddk.trend_volatility_brake import (
    V16_PROTOCOL_SHA256,
    V16_VALIDATION_ARCHIVE_SHA256,
    V16_VALIDATION_PANEL_SHA256,
    evaluate_trend_volatility_brake_research,
)

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = ROOT / "artifacts/snapshot_v16_trend_vol_20050103_20260731_777302d4.zip"
PROTOCOL = ROOT / "docs/V16_TREND_VOLATILITY_BRAKE_PROTOCOL.md"
PROTOCOL_RECEIPT = ROOT / "artifacts/v16_protocol_receipt.json"
DATA_RECEIPT = ROOT / "artifacts/v16_data_receipt.json"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture(scope="module")
def v16_audit() -> dict:
    panel, manifest = load_snapshot(SNAPSHOT)
    receipt = {
        "panel_sha256": panel_fingerprint(panel),
        "archive_sha256": _sha256(SNAPSHOT),
        "contract": manifest["contract"],
    }
    return evaluate_trend_volatility_brake_research(
        panel,
        validation_receipt=receipt,
        protocol_receipt=json.loads(PROTOCOL_RECEIPT.read_text(encoding="utf-8")),
        data_receipt=json.loads(DATA_RECEIPT.read_text(encoding="utf-8")),
        protocol_sha256=_sha256(PROTOCOL),
    )


def test_v16_weekly_targets_are_physical_and_bounded() -> None:
    index = pd.date_range("2018-01-02", periods=520, freq="B")
    core = np.linspace(100.0, 180.0, len(index))
    close = pd.DataFrame(
        {"IJH": core, "MVV": core * 1.8, "SHY": np.linspace(80.0, 82.0, len(index))},
        index=index,
    )
    targets = trend_volatility_brake_targets(close).dropna(how="all")
    assert len(targets) > 0
    assert np.allclose(targets.sum(axis=1), 1.0)
    notional = targets["IJH"] + 2.0 * targets["MVV"]
    assert notional.min() >= 0.0
    assert notional.max() <= 1.50 + 1e-10


def test_v16_protocol_and_snapshot_are_frozen_in_order() -> None:
    protocol_receipt = json.loads(PROTOCOL_RECEIPT.read_text(encoding="utf-8"))
    data_receipt = json.loads(DATA_RECEIPT.read_text(encoding="utf-8"))
    assert _sha256(PROTOCOL) == V16_PROTOCOL_SHA256
    assert protocol_receipt["protocol_sha256"] == V16_PROTOCOL_SHA256
    assert protocol_receipt["protocol_mtime_epoch"] < data_receipt["download"][
        "snapshot_mtime_epoch"
    ]
    assert data_receipt["pre_registration_order_proved"] is True
    panel, manifest = load_snapshot(SNAPSHOT)
    assert panel_fingerprint(panel) == V16_VALIDATION_PANEL_SHA256
    assert _sha256(SNAPSHOT) == V16_VALIDATION_ARCHIVE_SHA256
    assert manifest["contract"]["ok"] is True


def test_v16_rejects_the_weekly_brake(v16_audit: dict) -> None:
    assert v16_audit["status"] == "new_mid_small_cap_leveraged_etf_validation_failed"
    assert v16_audit["paper_eligible"] is False
    assert v16_audit["economic_passed_gate_count"] == 6
    assert v16_audit["economic_required_gate_count"] == 48
    assert v16_audit["data_passed_gate_count"] == 4
    assert v16_audit["data_required_gate_count"] == 4
    assert v16_audit["statistical_passed_gate_count"] == 0
    assert v16_audit["statistical_required_gate_count"] == 27
    for data in v16_audit["datasets"].values():
        assert sum(data["economic_gates"].values()) == 2
        assert data["strategy_metrics"]["cagr"] < data["benchmark_metrics"]["core"][
            "cagr"
        ]


def test_v16_report_and_paper_guard(v16_audit: dict, tmp_path: Path) -> None:
    report = build_trend_volatility_brake_report(tmp_path / "v16.html", v16_audit)
    text = report.read_text(encoding="utf-8")
    assert "煞車太頻繁" in text
    assert "6 / 48" in text
    state = tmp_path / "paper_v16_state.json"
    code = cli_main(
        [
            "paper",
            "update",
            "--snapshot",
            str(SNAPSHOT),
            "--strategy",
            "v16",
            "--state",
            str(state),
        ]
    )
    assert code == 2
    assert not state.exists()
