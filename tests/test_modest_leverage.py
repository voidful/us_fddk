from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from usfddk.cli import main as cli_main
from usfddk.data import load_snapshot, panel_fingerprint
from usfddk.modest_leverage import (
    V14_PROTOCOL_SHA256,
    V14_VALIDATION_ARCHIVE_SHA256,
    V14_VALIDATION_PANEL_SHA256,
    evaluate_modest_leverage_research,
)
from usfddk.strategies import (
    confirmed_market_trend_states,
    modest_leverage_trend_targets,
)

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = ROOT / "artifacts/snapshot_v14_leveraged_20040102_20260731_d7dc527a.zip"
PROTOCOL = ROOT / "docs/V14_MODEST_LEVERAGE_TREND_PROTOCOL.md"
PROTOCOL_RECEIPT = ROOT / "artifacts/v14_protocol_receipt.json"
DATA_RECEIPT = ROOT / "artifacts/v14_data_receipt.json"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture(scope="module")
def v14_audit() -> dict:
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
    return evaluate_modest_leverage_research(
        panel,
        validation_receipt=validation_receipt,
        protocol_receipt=json.loads(PROTOCOL_RECEIPT.read_text(encoding="utf-8")),
        data_receipt=json.loads(DATA_RECEIPT.read_text(encoding="utf-8")),
        protocol_sha256=_sha256(PROTOCOL),
    )


def test_two_month_trend_confirmation_and_monthly_targets() -> None:
    index = pd.date_range("2020-01-02", periods=520, freq="B")
    core = np.linspace(100.0, 180.0, len(index))
    close = pd.DataFrame(
        {
            "SPY": core,
            "SSO": core * 1.8,
            "SHY": np.linspace(80.0, 82.0, len(index)),
        },
        index=index,
    )
    states = confirmed_market_trend_states(close, core="SPY")
    assert not states.empty
    assert states.iloc[0] == "risk_on"
    targets = modest_leverage_trend_targets(close, core="SPY", leveraged="SSO")
    signals = targets.dropna(how="all")
    assert len(signals) == len(states)
    assert np.allclose(signals.sum(axis=1), 1.0)
    assert np.allclose(signals["SSO"], 0.60)
    assert np.allclose(signals["SHY"], 0.40)


def test_v14_protocol_was_frozen_before_new_snapshot() -> None:
    protocol_receipt = json.loads(PROTOCOL_RECEIPT.read_text(encoding="utf-8"))
    data_receipt = json.loads(DATA_RECEIPT.read_text(encoding="utf-8"))
    assert _sha256(PROTOCOL) == V14_PROTOCOL_SHA256
    assert protocol_receipt["protocol_sha256"] == V14_PROTOCOL_SHA256
    assert protocol_receipt["protocol_mtime_epoch"] < data_receipt["download"][
        "snapshot_mtime_epoch"
    ]
    assert data_receipt["pre_registration_order_proved"] is True
    assert _sha256(SNAPSHOT) == V14_VALIDATION_ARCHIVE_SHA256
    panel, manifest = load_snapshot(SNAPSHOT)
    assert panel_fingerprint(panel) == V14_VALIDATION_PANEL_SHA256
    assert manifest["contract"]["ok"] is True


def test_v14_real_leveraged_etfs_reject_cross_market_claim(v14_audit: dict) -> None:
    assert v14_audit["status"] == "new_leveraged_etf_validation_failed"
    assert v14_audit["paper_eligible"] is False
    assert v14_audit["reference_trade_candidate"] is False
    assert v14_audit["economic_passed_gate_count"] == 13
    assert v14_audit["economic_required_gate_count"] == 36
    assert v14_audit["data_passed_gate_count"] == 4
    assert v14_audit["data_required_gate_count"] == 4
    assert v14_audit["paper_entry_passed_gate_count"] == 17
    assert v14_audit["paper_entry_required_gate_count"] == 40
    assert v14_audit["statistical_passed_gate_count"] == 0
    assert v14_audit["statistical_required_gate_count"] == 18

    sp500 = v14_audit["datasets"]["sp500"]
    nasdaq = v14_audit["datasets"]["nasdaq100"]
    dow = v14_audit["datasets"]["dow30"]
    assert sp500["strategy_metrics"]["cagr"] == pytest.approx(0.09206844108216194)
    assert sp500["benchmark_metrics"]["core"]["cagr"] == pytest.approx(
        0.11252967297909855
    )
    assert nasdaq["strategy_metrics"]["cagr"] == pytest.approx(0.17013764305797885)
    assert nasdaq["benchmark_metrics"]["core"]["cagr"] == pytest.approx(
        0.16629755154594794
    )
    assert nasdaq["benchmark_metrics"]["fixed_60_40"]["cagr"] == pytest.approx(
        0.17693615025246578
    )
    assert dow["strategy_metrics"]["cagr"] == pytest.approx(0.07284693305934842)
    assert dow["benchmark_metrics"]["core"]["cagr"] == pytest.approx(
        0.10439053835672318
    )
    assert all(data["data_gate_passed"] for data in v14_audit["datasets"].values())


def test_v14_fails_closed_on_changed_protocol_receipt(v14_audit: dict) -> None:
    del v14_audit
    panel, manifest = load_snapshot(SNAPSHOT)
    validation_receipt = {
        "panel_sha256": panel_fingerprint(panel),
        "archive_sha256": _sha256(SNAPSHOT),
        "contract": manifest["contract"],
    }
    protocol_receipt = json.loads(PROTOCOL_RECEIPT.read_text(encoding="utf-8"))
    protocol_receipt["protocol_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="協議凍結收據雜湊不符"):
        evaluate_modest_leverage_research(
            panel,
            validation_receipt=validation_receipt,
            protocol_receipt=protocol_receipt,
            data_receipt=json.loads(DATA_RECEIPT.read_text(encoding="utf-8")),
            protocol_sha256=V14_PROTOCOL_SHA256,
        )


def test_v14_cli_writes_audit_and_beginner_report(tmp_path: Path) -> None:
    output = tmp_path / "v14.json"
    report = tmp_path / "v14.html"
    code = cli_main(
        [
            "v14-modest-leverage",
            "--output",
            str(output),
            "--report",
            str(report),
        ]
    )
    assert code == 0
    audit = json.loads(output.read_text(encoding="utf-8"))
    html = report.read_text(encoding="utf-8")
    assert audit["economic_passed_gate_count"] == 13
    assert audit["paper_eligible"] is False
    assert "槓桿不是免費報酬" in html
    assert "不能進 Paper" in html
    assert "13 / 36" in html


def test_v14_paper_guard_refuses_failed_candidate(tmp_path: Path) -> None:
    state = tmp_path / "paper_v14_state.json"
    code = cli_main(
        [
            "paper",
            "update",
            "--snapshot",
            "artifacts/snapshot_v14_leveraged_20040102_20260731_d7dc527a.zip",
            "--strategy",
            "v14",
            "--state",
            str(state),
        ]
    )
    assert code == 2
    assert not state.exists()
