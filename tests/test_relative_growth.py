from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from usfddk.data import load_snapshot, panel_fingerprint
from usfddk.relative_growth import (
    V7_PROTOCOL_SHA256,
    build_v7_proxy_panel,
    evaluate_relative_growth_research,
)

ROOT = Path(__file__).resolve().parents[1]
MAIN = ROOT / "artifacts/snapshot_20260731_6a7ca6b8.zip"
NDX = ROOT / "artifacts/snapshot_ndx_proxy_19851001_20060728_4814654a.zip"
GSPC = ROOT / "artifacts/cross_market_gspc_19870101_20060728_fbe6b740.zip"


def _load(path: Path):
    panel, manifest = load_snapshot(path)
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


def test_v7_protocol_and_proxy_translation_are_frozen():
    assert hashlib.sha256(
        (ROOT / "docs/V7_RELATIVE_GROWTH_PROTOCOL.md").read_bytes()
    ).hexdigest() == V7_PROTOCOL_SHA256
    _, ndx, gspc, *_ = _inputs()
    proxy = build_v7_proxy_panel(ndx, gspc)
    assert proxy.start.strftime("%Y-%m-%d") == "1987-01-02"
    assert proxy.end.strftime("%Y-%m-%d") == "2006-07-28"
    assert proxy.tickers == ["^GSPC", "^NDX", "CASH"]
    assert (proxy.close["CASH"] == 1.0).all()
    assert (proxy.volume["CASH"] == 0.0).all()


def test_v7_frozen_rule_is_rejected_and_does_not_open_paper():
    main, ndx, gspc, main_receipt, ndx_receipt, gspc_receipt = _inputs()
    _, _, audit = evaluate_relative_growth_research(
        main,
        ndx,
        gspc,
        main_receipt=main_receipt,
        ndx_receipt=ndx_receipt,
        gspc_receipt=gspc_receipt,
        protocol_sha256=V7_PROTOCOL_SHA256,
    )
    assert audit["passed_gate_count"] == 6
    assert audit["required_gate_count"] == 19
    assert not audit["historical_gate_passed"]
    assert not audit["paper_eligible"]
    assert audit["promotion_effect"] == "none"
    assert audit["main"]["strategy_metrics"]["cagr"] == pytest.approx(
        0.10594602921695562
    )
    assert audit["main"]["benchmark_metrics"]["market"]["cagr"] == pytest.approx(
        0.11269644523266886
    )
    assert audit["main"]["benchmark_metrics"]["matched"]["cagr"] == pytest.approx(
        0.0930423184336151
    )
    assert audit["proxy"]["strategy_metrics"]["cagr"] == pytest.approx(
        0.09395518711141215
    )
    assert not audit["gates"]["01_main_cagr_beats_market_and_matched_10bp"]
    assert audit["gates"]["11_proxy_cagr_beats_market_and_matched_10bp"]


def test_v7_fails_closed_on_protocol_drift():
    main, ndx, gspc, main_receipt, ndx_receipt, gspc_receipt = _inputs()
    with pytest.raises(ValueError, match="協議雜湊"):
        evaluate_relative_growth_research(
            main,
            ndx,
            gspc,
            main_receipt=main_receipt,
            ndx_receipt=ndx_receipt,
            gspc_receipt=gspc_receipt,
            protocol_sha256="0" * 64,
        )
