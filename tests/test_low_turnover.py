from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from usfddk.cli import main as cli_main
from usfddk.data import load_snapshot, panel_fingerprint
from usfddk.low_turnover import (
    V9_DATA_CONTRACT_SHA256,
    V9_EXTERNAL_COMMON_PANEL_SHA256,
    V9_PROTOCOL_SHA256,
    build_v9_external_common_panel,
    evaluate_low_turnover_research,
    fetch_and_freeze_v9_external,
    validate_v9_external_common,
    validate_v9_external_index,
)

ROOT = Path(__file__).resolve().parents[1]
MAIN = ROOT / "artifacts/snapshot_20260731_6a7ca6b8.zip"
NDX = ROOT / "artifacts/snapshot_ndx_proxy_19851001_20060728_4814654a.zip"
OLD_GSPC = ROOT / "artifacts/cross_market_gspc_19870101_20060728_fbe6b740.zip"
IXIC = ROOT / "artifacts/snapshot_v9_ixic_19710205_19881230_76bc29b6.zip"
EXTERNAL_GSPC = ROOT / "artifacts/snapshot_v9_gspc_19710205_19881230_414d7879.zip"
EXTERNAL_RECEIPT = ROOT / "artifacts/v9_external_data_receipt.json"


def _load(path: Path):
    panel, manifest = load_snapshot(path)
    return panel, {
        "path": str(path),
        "panel_sha256": panel_fingerprint(panel),
        "archive_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "contract": manifest.get("contract"),
    }


@pytest.fixture(scope="module")
def v9_inputs():
    main, main_receipt = _load(MAIN)
    ndx, ndx_receipt = _load(NDX)
    old_gspc, old_gspc_receipt = _load(OLD_GSPC)
    ixic, ixic_receipt = _load(IXIC)
    external_gspc, external_gspc_receipt = _load(EXTERNAL_GSPC)
    external_receipt = json.loads(EXTERNAL_RECEIPT.read_text(encoding="utf-8"))
    return (
        main,
        ndx,
        old_gspc,
        ixic,
        external_gspc,
        main_receipt,
        ndx_receipt,
        old_gspc_receipt,
        ixic_receipt,
        external_gspc_receipt,
        external_receipt,
    )


@pytest.fixture(scope="module")
def v9_audit(v9_inputs):
    (
        main,
        ndx,
        old_gspc,
        ixic,
        external_gspc,
        main_receipt,
        ndx_receipt,
        old_gspc_receipt,
        ixic_receipt,
        external_gspc_receipt,
        external_receipt,
    ) = v9_inputs
    _, _, audit = evaluate_low_turnover_research(
        main,
        ndx,
        old_gspc,
        ixic,
        external_gspc,
        main_receipt=main_receipt,
        ndx_receipt=ndx_receipt,
        old_gspc_receipt=old_gspc_receipt,
        ixic_receipt=ixic_receipt,
        external_gspc_receipt=external_gspc_receipt,
        external_data_receipt=external_receipt,
        protocol_sha256=V9_PROTOCOL_SHA256,
        data_contract_sha256=V9_DATA_CONTRACT_SHA256,
    )
    return audit


def test_v9_protocol_and_external_data_contract_are_frozen_before_use(v9_inputs):
    assert hashlib.sha256(
        (ROOT / "docs/V9_LOW_TURNOVER_EXTERNAL_PROTOCOL.md").read_bytes()
    ).hexdigest() == V9_PROTOCOL_SHA256
    assert hashlib.sha256(
        (ROOT / "docs/V9_EXTERNAL_DATA_CONTRACT.md").read_bytes()
    ).hexdigest() == V9_DATA_CONTRACT_SHA256
    ixic = v9_inputs[3]
    gspc = v9_inputs[4]
    assert validate_v9_external_index(
        ixic, ticker="^IXIC", protocol_sha256=V9_PROTOCOL_SHA256
    ).ok
    assert validate_v9_external_index(
        gspc, ticker="^GSPC", protocol_sha256=V9_PROTOCOL_SHA256
    ).ok
    common = build_v9_external_common_panel(ixic, gspc)
    assert validate_v9_external_common(common).ok
    assert panel_fingerprint(common) == V9_EXTERNAL_COMMON_PANEL_SHA256


def test_v9_improves_main_cagr_but_fails_three_paper_entry_gates(v9_audit):
    assert v9_audit["paper_entry_passed_gate_count"] == 20
    assert v9_audit["paper_entry_required_gate_count"] == 23
    assert v9_audit["passed_gate_count"] == 20
    assert v9_audit["required_gate_count"] == 29
    assert not v9_audit["paper_eligible"]
    assert not v9_audit["historically_confirmed"]
    assert v9_audit["promotion_effect"] == "none"
    assert v9_audit["main"]["strategy_metrics"]["cagr"] == pytest.approx(
        0.1210220028033635
    )
    assert v9_audit["main"]["benchmark_metrics"]["market"]["cagr"] == pytest.approx(
        0.11252967777323386
    )
    assert not v9_audit["gates"]["05_main_50bps_cagr_beats_market_10bp"]
    assert not v9_audit["gates"]["10_old_proxy_drawdown_not_worse_than_market_5pp"]
    assert not v9_audit["gates"]["20_external_both_halves_cagr_beat_market_10bp"]
    assert not any(ROOT.glob("artifacts/*v9*paper*"))


def test_v9_only_executes_regime_changes_and_fails_statistical_confirmation(v9_audit):
    for key in ("main", "old_proxy", "external"):
        signals = v9_audit[key]["signals"]
        assert (
            signals["completed_executions_in_formal_period"]
            < signals["completed_month_ends_in_formal_period"]
        )
    assert v9_audit["main"]["signals"]["completed_executions_in_formal_period"] == 47
    assert not all(v9_audit["statistical_gates"].values())
    assert not v9_audit["global_dsr_promotion_sensitivity"]["passed"]


def test_v9_fails_closed_on_protocol_drift(v9_inputs):
    with pytest.raises(ValueError, match="協議雜湊"):
        evaluate_low_turnover_research(
            *v9_inputs[:5],
            main_receipt=v9_inputs[5],
            ndx_receipt=v9_inputs[6],
            old_gspc_receipt=v9_inputs[7],
            ixic_receipt=v9_inputs[8],
            external_gspc_receipt=v9_inputs[9],
            external_data_receipt=v9_inputs[10],
            protocol_sha256="0" * 64,
            data_contract_sha256=V9_DATA_CONTRACT_SHA256,
        )


def test_v9_paper_command_refuses_failed_entry_receipt(tmp_path):
    state = tmp_path / "paper_v9_state.json"
    assert cli_main(
        [
            "paper",
            "update",
            "--snapshot",
            str(MAIN),
            "--strategy",
            "v9",
            "--state",
            str(state),
            "--eligibility-receipt",
            str(ROOT / "artifacts/v9_low_turnover_validation.json"),
        ]
    ) == 2
    assert not state.exists()


def test_v9_external_fetch_refuses_to_overwrite_frozen_snapshot(tmp_path):
    frozen = tmp_path / "snapshot_v9_ixic_19710205_19881230_deadbeef.zip"
    frozen.write_bytes(b"already frozen")
    with pytest.raises(ValueError, match="拒絕重新下載或覆寫"):
        fetch_and_freeze_v9_external(
            tmp_path,
            protocol_sha256=V9_PROTOCOL_SHA256,
            data_contract_sha256=V9_DATA_CONTRACT_SHA256,
        )
