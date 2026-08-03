from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from usfddk.cli import main as cli_main
from usfddk.confirmed_relative_growth import (
    V13_PROTOCOL_SHA256,
    evaluate_confirmed_relative_growth_research,
)
from usfddk.data import load_snapshot, panel_fingerprint

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = ROOT / "artifacts/snapshot_v13_validation_20040102_20260731_1301e2e1.zip"


def _receipt(path: Path, manifest: dict) -> dict:
    panel, _ = load_snapshot(path)
    return {
        "path": str(path),
        "rows": int(manifest["rows"]),
        "start": str(manifest["start"]),
        "end": str(manifest["end"]),
        "tickers": list(manifest["tickers"]),
        "panel_sha256": panel_fingerprint(panel),
        "archive_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "contract": manifest.get("contract"),
    }


@pytest.fixture(scope="module")
def v13_audit():
    panel, manifest = load_snapshot(SNAPSHOT)
    return evaluate_confirmed_relative_growth_research(
        panel,
        validation_receipt=_receipt(SNAPSHOT, manifest),
        protocol_sha256=V13_PROTOCOL_SHA256,
    )


def test_v13_protocol_was_frozen_before_validation_snapshot():
    protocol = ROOT / "docs/V13_CONFIRMED_RELATIVE_GROWTH_PROTOCOL.md"
    assert hashlib.sha256(protocol.read_bytes()).hexdigest() == V13_PROTOCOL_SHA256
    assert protocol.stat().st_mtime_ns <= SNAPSHOT.stat().st_mtime_ns


def test_v13_new_etf_validation_rejects_candidate(v13_audit):
    assert v13_audit["status"] == "new_etf_validation_failed"
    assert v13_audit["economic_passed_gate_count"] == 9
    assert v13_audit["economic_required_gate_count"] == 30
    assert v13_audit["data_passed_gate_count"] == 3
    assert v13_audit["data_required_gate_count"] == 4
    assert not v13_audit["paper_eligible"]
    assert not v13_audit["historically_confirmed"]
    assert v13_audit["promotion_effect"] == "none"


def test_v13_russell_pairs_fail_return_consistency(v13_audit):
    r1000 = v13_audit["datasets"]["russell_1000"]
    r2000 = v13_audit["datasets"]["russell_2000"]
    assert r1000["status"] == "completed"
    assert r2000["status"] == "completed"
    assert r1000["strategy_metrics"]["cagr"] == pytest.approx(0.1094129217445372)
    assert r1000["benchmark_metrics"]["market"]["cagr"] == pytest.approx(
        0.11165210331657338
    )
    assert r2000["strategy_metrics"]["cagr"] == pytest.approx(0.07299395911490714)
    assert r2000["benchmark_metrics"]["market"]["cagr"] == pytest.approx(
        0.0885691382300855
    )
    for row in (r1000, r2000):
        assert not row["economic_gates"]["cagr_beats_market_10bp"]
        assert not row["economic_gates"]["50bps_cagr_beats_market_10bp"]
        assert not row["economic_gates"]["both_halves_cagr_beat_market_10bp"]
        assert not row["economic_gates"]["rolling_wins_60pct_and_positive_median"]


def test_v13_eafe_fails_closed_instead_of_moving_fixed_start(v13_audit):
    eafe = v13_audit["datasets"]["eafe"]
    assert eafe["status"] == "insufficient_warmup"
    assert eafe["warmup_common_sessions"] == 247
    assert not eafe["data_gate_passed"]
    assert not any(eafe["economic_gates"].values())
    assert eafe["diagnostic"]["gate_eligible"] is False


def test_v13_fails_closed_on_protocol_or_snapshot_drift():
    panel, manifest = load_snapshot(SNAPSHOT)
    receipt = _receipt(SNAPSHOT, manifest)
    with pytest.raises(ValueError, match="協議雜湊"):
        evaluate_confirmed_relative_growth_research(
            panel,
            validation_receipt=receipt,
            protocol_sha256="0" * 64,
        )
    bad = {**receipt, "archive_sha256": "0" * 64}
    with pytest.raises(ValueError, match="ZIP 雜湊"):
        evaluate_confirmed_relative_growth_research(
            panel,
            validation_receipt=bad,
            protocol_sha256=V13_PROTOCOL_SHA256,
        )


def test_v13_cli_writes_audit_and_beginner_report(tmp_path):
    output = tmp_path / "v13.json"
    report = tmp_path / "v13.html"
    assert cli_main(
        [
            "v13-confirmed-growth",
            "--validation-snapshot",
            str(SNAPSHOT),
            "--output",
            str(output),
            "--report",
            str(report),
        ]
    ) == 0
    assert output.exists()
    assert report.exists()
    rendered = report.read_text(encoding="utf-8")
    assert "新 ETF 已給答案" in rendered
    assert "不能進 Paper" in rendered
    assert "9 / 30" in rendered


def test_v13_paper_command_refuses_failed_new_etf_receipt(tmp_path):
    state = tmp_path / "paper_v13_state.json"
    assert cli_main(
        [
            "paper",
            "update",
            "--snapshot",
            str(ROOT / "artifacts/snapshot_20260731_6a7ca6b8.zip"),
            "--strategy",
            "v13",
            "--state",
            str(state),
            "--eligibility-receipt",
            str(ROOT / "artifacts/v13_confirmed_growth_validation.json"),
        ]
    ) == 2
    assert not state.exists()
