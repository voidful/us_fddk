from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pytest

from usfddk.cli import main as cli_main
from usfddk.data import load_snapshot, panel_fingerprint
from usfddk.equal_diversifier import (
    V18_PROTOCOL_SHA256,
    V18_VALIDATION_ARCHIVE_SHA256,
    V18_VALIDATION_PANEL_SHA256,
    evaluate_equal_diversifier_research,
)
from usfddk.report import build_equal_diversifier_report
from usfddk.strategies import fixed_weight_targets

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = (
    ROOT
    / "artifacts/snapshot_v18_equal_diversifier_20080602_20260731_dd920b90.zip"
)
PROTOCOL = ROOT / "docs/V18_EQUAL_DIVERSIFIER_CAPITAL_EFFICIENCY_PROTOCOL.md"
PROTOCOL_RECEIPT = ROOT / "artifacts/v18_protocol_receipt.json"
DATA_RECEIPT = ROOT / "artifacts/v18_data_receipt.json"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture(scope="module")
def v18_audit() -> dict:
    panel, manifest = load_snapshot(SNAPSHOT)
    receipt = {
        "panel_sha256": panel_fingerprint(panel),
        "archive_sha256": _sha256(SNAPSHOT),
        "contract": manifest["contract"],
    }
    return evaluate_equal_diversifier_research(
        panel,
        validation_receipt=receipt,
        protocol_receipt=json.loads(PROTOCOL_RECEIPT.read_text(encoding="utf-8")),
        data_receipt=json.loads(DATA_RECEIPT.read_text(encoding="utf-8")),
        protocol_sha256=_sha256(PROTOCOL),
    )


def test_v18_fixed_targets_keep_physical_weights_and_150pct_notional() -> None:
    panel, _ = load_snapshot(SNAPSHOT)
    targets = fixed_weight_targets(
        panel.close, {"EFO": 0.50, "IEF": 0.25, "GLD": 0.25}
    )
    signals = targets.dropna(how="all")
    assert len(signals) > 0
    assert np.allclose(signals.sum(axis=1), 1.0)
    assert np.allclose(
        2.0 * signals["EFO"] + signals["IEF"] + signals["GLD"], 1.50
    )


def test_v18_protocol_precedes_external_snapshot() -> None:
    protocol_receipt = json.loads(PROTOCOL_RECEIPT.read_text(encoding="utf-8"))
    data_receipt = json.loads(DATA_RECEIPT.read_text(encoding="utf-8"))
    assert _sha256(PROTOCOL) == V18_PROTOCOL_SHA256
    assert protocol_receipt["protocol_sha256"] == V18_PROTOCOL_SHA256
    assert protocol_receipt["protocol_mtime_epoch"] < data_receipt["download"][
        "snapshot_mtime_epoch"
    ]
    assert data_receipt["pre_registration_order_proved"] is True
    panel, manifest = load_snapshot(SNAPSHOT)
    assert panel_fingerprint(panel) == V18_VALIDATION_PANEL_SHA256
    assert _sha256(SNAPSHOT) == V18_VALIDATION_ARCHIVE_SHA256
    assert manifest["contract"]["ok"] is True


def test_v18_external_paths_reject_us_design_claim(v18_audit: dict) -> None:
    assert v18_audit["status"] == "equal_diversifier_external_validation_failed"
    assert v18_audit["paper_eligible"] is False
    assert v18_audit["economic_passed_gate_count"] == 5
    assert v18_audit["economic_required_gate_count"] == 18
    assert v18_audit["data_passed_gate_count"] == 3
    assert v18_audit["data_required_gate_count"] == 3
    assert v18_audit["statistical_passed_gate_count"] == 0
    assert v18_audit["statistical_required_gate_count"] == 12
    assert (
        v18_audit["evidence_boundary"]["classification"]
        == "semi_independent_external_validation_not_fully_blind"
    )
    for data in v18_audit["datasets"].values():
        strategy = data["strategy_metrics"]
        core = data["benchmark_metrics"]["core"]
        assert strategy["max_drawdown"] < core["max_drawdown"]
        assert data["weight_integrity"]["passed"] is True
        assert data["weight_integrity"][
            "signals_pending_execution_after_data_cutoff"
        ] == ["2026-07-31"]


def test_v18_report_and_paper_guard(v18_audit: dict, tmp_path: Path) -> None:
    report = build_equal_diversifier_report(tmp_path / "v18.html", v18_audit)
    text = report.read_text(encoding="utf-8")
    assert "海外驗證沒有重現" in text
    assert "5 / 18" in text
    state = tmp_path / "paper_v18_state.json"
    code = cli_main(
        [
            "paper",
            "update",
            "--snapshot",
            str(SNAPSHOT),
            "--strategy",
            "v18",
            "--state",
            str(state),
        ]
    )
    assert code == 2
    assert not state.exists()
