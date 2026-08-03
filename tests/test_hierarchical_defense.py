from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from usfddk.cli import main as cli_main
from usfddk.data import load_snapshot, panel_fingerprint
from usfddk.hierarchical_defense import (
    V12_PROTOCOL_SHA256,
    evaluate_v12_hierarchical_research,
)

ROOT = Path(__file__).resolve().parents[1]
MAIN = ROOT / "artifacts/snapshot_20260731_6a7ca6b8.zip"
NDX = ROOT / "artifacts/snapshot_ndx_proxy_19851001_20060728_4814654a.zip"
OLD_GSPC = ROOT / "artifacts/cross_market_gspc_19870101_20060728_fbe6b740.zip"
IXIC = ROOT / "artifacts/snapshot_v9_ixic_19710205_19881230_76bc29b6.zip"
EXTERNAL_GSPC = ROOT / "artifacts/snapshot_v9_gspc_19710205_19881230_414d7879.zip"
V10_FAILURE = ROOT / "artifacts/v10_dji_data_receipt.json"
V11_FAILURE = ROOT / "artifacts/v11_official_dji_data_receipt.json"
V12_AUDIT = ROOT / "artifacts/v12_hierarchical_validation.json"


def _load(path: Path):
    panel, manifest = load_snapshot(path)
    return panel, {
        "path": str(path),
        "panel_sha256": panel_fingerprint(panel),
        "archive_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "contract": manifest.get("contract"),
    }


def _failure(path: Path):
    receipt = json.loads(path.read_text(encoding="utf-8"))
    receipt["receipt_file"] = {
        "path": str(path),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    }
    return receipt


@pytest.fixture(scope="module")
def v12_inputs():
    loaded = [_load(path) for path in (MAIN, NDX, OLD_GSPC, IXIC, EXTERNAL_GSPC)]
    panels = [item[0] for item in loaded]
    receipts = [item[1] for item in loaded]
    return (*panels, *receipts, _failure(V10_FAILURE), _failure(V11_FAILURE))


@pytest.fixture(scope="module")
def v12_audit(v12_inputs):
    _, _, audit = evaluate_v12_hierarchical_research(
        *v12_inputs[:5],
        main_receipt=v12_inputs[5],
        ndx_receipt=v12_inputs[6],
        old_gspc_receipt=v12_inputs[7],
        ixic_receipt=v12_inputs[8],
        external_gspc_receipt=v12_inputs[9],
        v10_failure_receipt=v12_inputs[10],
        v11_failure_receipt=v12_inputs[11],
        protocol_sha256=V12_PROTOCOL_SHA256,
    )
    return audit


def test_v12_protocol_is_frozen_before_first_calculation():
    assert hashlib.sha256(
        (ROOT / "docs/V12_HIERARCHICAL_DEFENSE_THREE_SAMPLE_PROTOCOL.md").read_bytes()
    ).hexdigest() == V12_PROTOCOL_SHA256
    assert _failure(V10_FAILURE)["status"] == "fetch_failed"
    assert _failure(V11_FAILURE)["result"]["error"] == "HTTP Error 403: Forbidden"


def test_v12_reduces_drawdown_but_fails_paper_entry(v12_audit):
    assert v12_audit["paper_entry_passed_gate_count"] == 16
    assert v12_audit["paper_entry_required_gate_count"] == 23
    assert v12_audit["passed_gate_count"] == 16
    assert v12_audit["required_gate_count"] == 29
    assert not v12_audit["paper_eligible"]
    assert not v12_audit["historically_confirmed"]
    assert v12_audit["main"]["strategy_metrics"]["cagr"] == pytest.approx(
        0.1109898281914119
    )
    assert v12_audit["main"]["benchmark_metrics"]["market"]["cagr"] == pytest.approx(
        0.11252967777323386
    )
    assert v12_audit["main"]["comparison"]["drawdown_improvement"] == pytest.approx(
        0.13963686520685026
    )
    assert not v12_audit["gates"]["01_main_cagr_beats_market_10bp"]
    assert not v12_audit["gates"]["05_main_50bps_cagr_beats_market_10bp"]
    assert not v12_audit["gates"]["20_external_both_halves_cagr_beat_market_10bp"]
    assert not any(ROOT.glob("artifacts/*v12*paper*"))


def test_v12_trades_only_state_changes_and_fails_statistics(v12_audit):
    for key in ("main", "old_proxy", "external"):
        signals = v12_audit[key]["signals"]
        assert (
            signals["completed_executions_in_formal_period"]
            < signals["completed_month_ends_in_formal_period"]
        )
        assert sum(signals["state_month_counts"].values()) == signals[
            "completed_month_ends_in_formal_period"
        ]
    assert v12_audit["main"]["signals"]["completed_executions_in_formal_period"] == 58
    assert not any(v12_audit["statistical_gates"].values())
    assert not v12_audit["global_dsr_promotion_sensitivity"]["passed"]


def test_v12_fails_closed_on_protocol_drift(v12_inputs):
    with pytest.raises(ValueError, match="協議雜湊"):
        evaluate_v12_hierarchical_research(
            *v12_inputs[:5],
            main_receipt=v12_inputs[5],
            ndx_receipt=v12_inputs[6],
            old_gspc_receipt=v12_inputs[7],
            ixic_receipt=v12_inputs[8],
            external_gspc_receipt=v12_inputs[9],
            v10_failure_receipt=v12_inputs[10],
            v11_failure_receipt=v12_inputs[11],
            protocol_sha256="0" * 64,
        )


def test_v12_paper_command_refuses_failed_entry_receipt(tmp_path: Path):
    state = tmp_path / "paper_v12_state.json"
    assert cli_main(
        [
            "paper",
            "update",
            "--snapshot",
            str(MAIN),
            "--strategy",
            "v12",
            "--state",
            str(state),
            "--eligibility-receipt",
            str(V12_AUDIT),
        ]
    ) == 2
    assert not state.exists()


def test_v11_cli_refuses_second_official_get():
    assert cli_main(["v11-fetch-official-dji"]) == 2
