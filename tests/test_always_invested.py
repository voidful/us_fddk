from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from usfddk.always_invested import (
    V8_PROTOCOL_SHA256,
    evaluate_always_invested_research,
)
from usfddk.data import load_snapshot, panel_fingerprint

ROOT = Path(__file__).resolve().parents[1]
MAIN = ROOT / "artifacts/snapshot_20260731_6a7ca6b8.zip"
NDX = ROOT / "artifacts/snapshot_ndx_proxy_19851001_20060728_4814654a.zip"
GSPC = ROOT / "artifacts/cross_market_gspc_19870101_20060728_fbe6b740.zip"


def _load(path: Path):
    panel, _ = load_snapshot(path)
    return panel, {
        "path": str(path),
        "panel_sha256": panel_fingerprint(panel),
        "archive_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    }


def _inputs():
    main, main_receipt = _load(MAIN)
    ndx, ndx_receipt = _load(NDX)
    gspc, gspc_receipt = _load(GSPC)
    return main, ndx, gspc, main_receipt, ndx_receipt, gspc_receipt


def test_v8_protocol_is_frozen_before_first_calculation():
    assert hashlib.sha256(
        (ROOT / "docs/V8_ALWAYS_INVESTED_PROTOCOL.md").read_bytes()
    ).hexdigest() == V8_PROTOCOL_SHA256


def test_v8_passes_most_economic_checks_but_does_not_open_paper():
    main, ndx, gspc, main_receipt, ndx_receipt, gspc_receipt = _inputs()
    _, _, audit = evaluate_always_invested_research(
        main,
        ndx,
        gspc,
        main_receipt=main_receipt,
        ndx_receipt=ndx_receipt,
        gspc_receipt=gspc_receipt,
        protocol_sha256=V8_PROTOCOL_SHA256,
    )
    assert audit["paper_entry_passed_gate_count"] == 14
    assert audit["paper_entry_required_gate_count"] == 16
    assert audit["passed_gate_count"] == 14
    assert audit["required_gate_count"] == 20
    assert not audit["paper_eligible"]
    assert not audit["historically_confirmed"]
    assert audit["promotion_effect"] == "none"
    assert audit["main"]["strategy_metrics"]["cagr"] == pytest.approx(
        0.12322453275598866
    )
    assert audit["main"]["benchmark_metrics"]["market"]["cagr"] == pytest.approx(
        0.11269644523266886
    )
    assert audit["proxy"]["strategy_metrics"]["cagr"] == pytest.approx(
        0.10984782377530355
    )
    assert not audit["gates"]["05_main_50bps_cagr_beats_spy_10bp"]
    assert not audit["gates"]["13_proxy_drawdown_not_worse_than_gspc_5pp"]
    assert not audit["global_dsr_promotion_sensitivity"]["passed"]


def test_v8_fails_closed_on_protocol_drift():
    main, ndx, gspc, main_receipt, ndx_receipt, gspc_receipt = _inputs()
    with pytest.raises(ValueError, match="協議雜湊"):
        evaluate_always_invested_research(
            main,
            ndx,
            gspc,
            main_receipt=main_receipt,
            ndx_receipt=ndx_receipt,
            gspc_receipt=gspc_receipt,
            protocol_sha256="0" * 64,
        )
