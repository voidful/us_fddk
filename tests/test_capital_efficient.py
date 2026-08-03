from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pytest

from usfddk.capital_efficient import (
    V17_PROTOCOL_SHA256,
    V17_VALIDATION_ARCHIVE_SHA256,
    V17_VALIDATION_PANEL_SHA256,
    evaluate_capital_efficient_research,
)
from usfddk.cli import main as cli_main
from usfddk.data import load_snapshot, panel_fingerprint
from usfddk.report import build_capital_efficient_report
from usfddk.strategies import fixed_weight_targets

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = (
    ROOT
    / "artifacts/snapshot_v17_capital_efficient_20040102_20260731_4c948bf6.zip"
)
PROTOCOL = ROOT / "docs/V17_CAPITAL_EFFICIENT_EQUITY_BOND_PROTOCOL.md"
PROTOCOL_RECEIPT = ROOT / "artifacts/v17_protocol_receipt.json"
DATA_RECEIPT = ROOT / "artifacts/v17_data_receipt.json"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture(scope="module")
def v17_audit() -> dict:
    panel, manifest = load_snapshot(SNAPSHOT)
    receipt = {
        "panel_sha256": panel_fingerprint(panel),
        "archive_sha256": _sha256(SNAPSHOT),
        "contract": manifest["contract"],
    }
    return evaluate_capital_efficient_research(
        panel,
        validation_receipt=receipt,
        protocol_receipt=json.loads(PROTOCOL_RECEIPT.read_text(encoding="utf-8")),
        data_receipt=json.loads(DATA_RECEIPT.read_text(encoding="utf-8")),
        protocol_sha256=_sha256(PROTOCOL),
    )


def test_v17_fixed_targets_keep_physical_weights_and_160pct_notional() -> None:
    panel, _ = load_snapshot(SNAPSHOT)
    targets = fixed_weight_targets(panel.close, {"SSO": 0.60, "IEF": 0.40})
    signals = targets.dropna(how="all")
    assert len(signals) > 0
    assert np.allclose(signals.sum(axis=1), 1.0)
    assert np.allclose(2.0 * signals["SSO"] + signals["IEF"], 1.60)


def test_v17_protocol_precedes_combined_snapshot() -> None:
    protocol_receipt = json.loads(PROTOCOL_RECEIPT.read_text(encoding="utf-8"))
    data_receipt = json.loads(DATA_RECEIPT.read_text(encoding="utf-8"))
    assert _sha256(PROTOCOL) == V17_PROTOCOL_SHA256
    assert protocol_receipt["protocol_sha256"] == V17_PROTOCOL_SHA256
    assert protocol_receipt["protocol_mtime_epoch"] < data_receipt["download"][
        "snapshot_mtime_epoch"
    ]
    assert data_receipt["pre_registration_order_proved"] is True
    panel, manifest = load_snapshot(SNAPSHOT)
    assert panel_fingerprint(panel) == V17_VALIDATION_PANEL_SHA256
    assert _sha256(SNAPSHOT) == V17_VALIDATION_ARCHIVE_SHA256
    assert manifest["contract"]["ok"] is True


def test_v17_has_twenty_year_large_cap_but_rejects_risk_claim(v17_audit: dict) -> None:
    assert v17_audit["status"] == "capital_efficient_equity_bond_validation_failed"
    assert v17_audit["paper_eligible"] is False
    assert v17_audit["economic_passed_gate_count"] == 48
    assert v17_audit["economic_required_gate_count"] == 84
    assert v17_audit["data_passed_gate_count"] == 7
    assert v17_audit["data_required_gate_count"] == 7
    assert v17_audit["statistical_passed_gate_count"] == 9
    assert v17_audit["statistical_required_gate_count"] == 54
    for key in ("sp500", "nasdaq100", "dow30"):
        assert v17_audit["datasets"][key]["period"]["years"] == 20
    for data in v17_audit["datasets"].values():
        strategy = data["strategy_metrics"]
        core = data["benchmark_metrics"]["core"]
        assert strategy["max_drawdown"] < core["max_drawdown"]


def test_v17_report_and_paper_guard(v17_audit: dict, tmp_path: Path) -> None:
    report = build_capital_efficient_report(tmp_path / "v17.html", v17_audit)
    text = report.read_text(encoding="utf-8")
    assert "公債有幫助" in text
    assert "48 / 84" in text
    state = tmp_path / "paper_v17_state.json"
    code = cli_main(
        [
            "paper",
            "update",
            "--snapshot",
            str(SNAPSHOT),
            "--strategy",
            "v17",
            "--state",
            str(state),
        ]
    )
    assert code == 2
    assert not state.exists()
