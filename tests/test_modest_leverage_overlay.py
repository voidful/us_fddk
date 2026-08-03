from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from usfddk.cli import main as cli_main
from usfddk.data import load_snapshot, panel_fingerprint
from usfddk.modest_leverage_overlay import (
    V15_PROTOCOL_SHA256,
    V15_VALIDATION_ARCHIVE_SHA256,
    V15_VALIDATION_PANEL_SHA256,
    evaluate_modest_leverage_overlay_research,
)
from usfddk.strategies import modest_leverage_overlay_targets

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = (
    ROOT / "artifacts/snapshot_v15_3x_20080102_20260731_57527472_validated.zip"
)
FAILED_CONTRACT_SNAPSHOT = (
    ROOT / "artifacts/snapshot_v15_3x_20080102_20260731_57527472.zip"
)
PROTOCOL = ROOT / "docs/V15_MODEST_LEVERAGE_OVERLAY_PROTOCOL.md"
PROTOCOL_RECEIPT = ROOT / "artifacts/v15_protocol_receipt.json"
DATA_RECEIPT = ROOT / "artifacts/v15_data_receipt.json"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture(scope="module")
def v15_audit() -> dict:
    panel, manifest = load_snapshot(SNAPSHOT)
    validation_receipt = {
        "path": str(SNAPSHOT),
        "rows": int(manifest["rows"]),
        "start": str(manifest["start"]),
        "end": str(manifest["end"]),
        "tickers": list(manifest["tickers"]),
        "panel_sha256": panel_fingerprint(panel),
        "archive_sha256": _sha256(SNAPSHOT),
        "created_at": str(manifest["created_at"]),
        "provider_metadata": manifest["provider_metadata"],
        "contract": manifest["contract"],
    }
    return evaluate_modest_leverage_overlay_research(
        panel,
        validation_receipt=validation_receipt,
        protocol_receipt=json.loads(PROTOCOL_RECEIPT.read_text(encoding="utf-8")),
        data_receipt=json.loads(DATA_RECEIPT.read_text(encoding="utf-8")),
        protocol_sha256=_sha256(PROTOCOL),
    )


def test_v15_overlay_targets_keep_core_and_sum_to_one() -> None:
    index = pd.date_range("2020-01-02", periods=520, freq="B")
    core = np.linspace(100.0, 180.0, len(index))
    close = pd.DataFrame({"SPY": core, "UPRO": core * 2.6}, index=index)
    targets = modest_leverage_overlay_targets(close)
    signals = targets.dropna(how="all")
    assert len(signals) > 0
    assert np.allclose(signals.sum(axis=1), 1.0)
    assert np.allclose(signals["SPY"], 0.90)
    assert np.allclose(signals["UPRO"], 0.10)


def test_v15_protocol_precedes_first_download_and_contract_correction() -> None:
    protocol_receipt = json.loads(PROTOCOL_RECEIPT.read_text(encoding="utf-8"))
    data_receipt = json.loads(DATA_RECEIPT.read_text(encoding="utf-8"))
    assert _sha256(PROTOCOL) == V15_PROTOCOL_SHA256
    assert protocol_receipt["protocol_sha256"] == V15_PROTOCOL_SHA256
    assert protocol_receipt["protocol_mtime_epoch"] < data_receipt["download"][
        "first_snapshot_mtime_epoch"
    ]
    assert data_receipt["pre_registration_order_proved"] is True
    assert _sha256(FAILED_CONTRACT_SNAPSHOT) == data_receipt["first_contract_attempt"][
        "archive_sha256"
    ]
    assert data_receipt["first_contract_attempt"]["contract_ok"] is False
    failed_panel, failed_manifest = load_snapshot(FAILED_CONTRACT_SNAPSHOT)
    panel, manifest = load_snapshot(SNAPSHOT)
    assert panel_fingerprint(failed_panel) == panel_fingerprint(panel)
    assert failed_manifest["contract"]["ok"] is False
    assert manifest["contract"]["ok"] is True
    assert _sha256(SNAPSHOT) == V15_VALIDATION_ARCHIVE_SHA256
    assert panel_fingerprint(panel) == V15_VALIDATION_PANEL_SHA256


def test_v15_beats_core_cagr_but_rejects_risk_claim(v15_audit: dict) -> None:
    assert v15_audit["status"] == "new_3x_etf_validation_failed"
    assert v15_audit["paper_eligible"] is False
    assert v15_audit["reference_trade_candidate"] is False
    assert v15_audit["economic_passed_gate_count"] == 17
    assert v15_audit["economic_required_gate_count"] == 36
    assert v15_audit["data_passed_gate_count"] == 4
    assert v15_audit["data_required_gate_count"] == 4
    assert v15_audit["paper_entry_passed_gate_count"] == 21
    assert v15_audit["paper_entry_required_gate_count"] == 40
    assert v15_audit["statistical_passed_gate_count"] == 4
    assert v15_audit["statistical_required_gate_count"] == 18
    assert v15_audit["evidence_boundary"]["cannot_claim_independent_twenty_year_v15"]

    expected = {
        "sp500": (0.15494094394606228, 0.1439091106228787),
        "nasdaq100": (0.2147103042854992, 0.1894226822135998),
        "dow30": (0.13272955840821798, 0.12577984525445962),
    }
    for key, (strategy_cagr, core_cagr) in expected.items():
        data = v15_audit["datasets"][key]
        assert data["strategy_metrics"]["cagr"] == pytest.approx(strategy_cagr)
        assert data["benchmark_metrics"]["core"]["cagr"] == pytest.approx(core_cagr)
        assert data["strategy_metrics"]["cagr"] > data["benchmark_metrics"]["core"][
            "cagr"
        ]
        assert data["strategy_metrics"]["sharpe"] < data["benchmark_metrics"]["core"][
            "sharpe"
        ]
        assert data["strategy_metrics"]["max_drawdown"] < data["benchmark_metrics"][
            "core"
        ]["max_drawdown"]


def test_v15_fails_closed_on_changed_data_receipt(v15_audit: dict) -> None:
    del v15_audit
    panel, manifest = load_snapshot(SNAPSHOT)
    validation_receipt = {
        "panel_sha256": panel_fingerprint(panel),
        "archive_sha256": _sha256(SNAPSHOT),
        "contract": manifest["contract"],
    }
    data_receipt = json.loads(DATA_RECEIPT.read_text(encoding="utf-8"))
    data_receipt["snapshot"]["panel_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="驗證面板雜湊不符"):
        evaluate_modest_leverage_overlay_research(
            panel,
            validation_receipt=validation_receipt,
            protocol_receipt=json.loads(
                PROTOCOL_RECEIPT.read_text(encoding="utf-8")
            ),
            data_receipt=data_receipt,
            protocol_sha256=V15_PROTOCOL_SHA256,
        )


def test_v15_cli_writes_audit_and_beginner_report(tmp_path: Path) -> None:
    output = tmp_path / "v15.json"
    report = tmp_path / "v15.html"
    code = cli_main(
        [
            "v15-modest-leverage-overlay",
            "--output",
            str(output),
            "--report",
            str(report),
        ]
    )
    assert code == 0
    audit = json.loads(output.read_text(encoding="utf-8"))
    html = report.read_text(encoding="utf-8")
    assert audit["economic_passed_gate_count"] == 17
    assert audit["paper_eligible"] is False
    assert "回報確實較高" in html
    assert "較高回報不等於穩健跑贏" in html
    assert "17 / 36" in html


def test_v15_paper_guard_refuses_failed_candidate(tmp_path: Path) -> None:
    state = tmp_path / "paper_v15_state.json"
    code = cli_main(
        [
            "paper",
            "update",
            "--snapshot",
            str(SNAPSHOT),
            "--strategy",
            "v15",
            "--state",
            str(state),
        ]
    )
    assert code == 2
    assert not state.exists()
