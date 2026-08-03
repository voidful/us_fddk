from __future__ import annotations

import hashlib
import json
from pathlib import Path

from usfddk.cli import main as cli_main
from usfddk.data import load_snapshot, panel_fingerprint
from usfddk.quality_momentum_factor import (
    V24_FRENCH_HASHES,
    V24_GLOBAL_SEARCH_TRIALS,
    V24_INVESCO_ARCHIVE_SHA256,
    V24_INVESCO_PANEL_SHA256,
    V24_ISHARES_ARCHIVE_SHA256,
    V24_ISHARES_PANEL_SHA256,
    V24_PRODUCT_MAPPING_SHA256,
    V24_PROTOCOL_SHA256,
    _load_academic_returns,
)
from usfddk.report import build_quality_momentum_factor_report

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "docs/V24_QUALITY_MOMENTUM_FACTOR_PROTOCOL.md"
MAPPING = ROOT / "docs/V24_PRODUCT_MAPPING.md"
PROTOCOL_RECEIPT = ROOT / "artifacts/v24_protocol_receipt.json"
DATA_RECEIPT = ROOT / "artifacts/v24_data_receipt.json"
FRENCH = {
    "market": ROOT / "artifacts/v24_french_ff3_monthly.zip",
    "quality": ROOT / "artifacts/v24_french_6_me_op_monthly.zip",
    "momentum": ROOT / "artifacts/v24_french_6_me_prior_12_2_monthly.zip",
}
ISHARES = (
    ROOT
    / "artifacts/snapshot_v24_ishares_quality_momentum_20130701_20260731_11fc153f.zip"
)
INVESCO = (
    ROOT
    / "artifacts/snapshot_v24_invesco_quality_momentum_20070301_20260731_39817fb7.zip"
)
VALIDATION = ROOT / "artifacts/v24_quality_momentum_factor_validation.json"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_v24_frozen_protocol_precedes_all_first_downloads() -> None:
    protocol = json.loads(PROTOCOL_RECEIPT.read_text(encoding="utf-8"))
    data = json.loads(DATA_RECEIPT.read_text(encoding="utf-8"))
    assert _sha256(PROTOCOL) == V24_PROTOCOL_SHA256
    assert _sha256(MAPPING) == V24_PRODUCT_MAPPING_SHA256
    assert protocol["global_trial_count"] == V24_GLOBAL_SEARCH_TRIALS
    frozen = max(protocol["protocol_mtime_epoch"], protocol["product_mapping_mtime_epoch"])
    for key, path in FRENCH.items():
        assert _sha256(path) == V24_FRENCH_HASHES[key]
        assert data["academic_sources"][key]["mtime_epoch"] > frozen
        assert data["academic_sources"][key]["download_performed_once"] is True

    for path, panel_hash, archive_hash, receipt_key in (
        (ISHARES, V24_ISHARES_PANEL_SHA256, V24_ISHARES_ARCHIVE_SHA256, "ishares_snapshot"),
        (INVESCO, V24_INVESCO_PANEL_SHA256, V24_INVESCO_ARCHIVE_SHA256, "invesco_snapshot"),
    ):
        panel, manifest = load_snapshot(path)
        assert panel_fingerprint(panel) == panel_hash
        assert _sha256(path) == archive_hash
        assert manifest["contract"]["ok"] is True
        assert data[receipt_key]["snapshot_mtime_epoch"] > frozen
        assert data[receipt_key]["performed_once"] is True


def test_v24_academic_parser_preserves_exact_frozen_periods() -> None:
    returns, integrity = _load_academic_returns(
        FRENCH["market"], FRENCH["quality"], FRENCH["momentum"]
    )
    formal = returns.loc["2006-05-01":"2026-04-30"]
    older = returns.loc["1964-07-01":"2006-04-30"]
    assert len(formal) == integrity["formal_months"] == 240
    assert len(older) == integrity["older_months"] == 502
    assert not returns.isna().any(axis=None)
    assert integrity["columns"] == {
        "market": "Mkt-RF + RF",
        "quality": "BIG HiOP",
        "momentum": "BIG HiPRIOR",
    }


def test_v24_frozen_result_separates_academic_success_from_product_failure() -> None:
    audit = json.loads(VALIDATION.read_text(encoding="utf-8"))
    assert audit["status"] == "quality_momentum_factor_validation_failed"
    assert audit["paper_eligible"] is False
    assert audit["trade_ready"] is False
    assert audit["candidate"]["signal_display_allowed"] is False
    assert audit["long_passed_gate_count"] == audit["long_required_gate_count"] == 10
    assert audit["ishares_passed_gate_count"] == 5
    assert audit["ishares_required_gate_count"] == 10
    assert audit["invesco_passed_gate_count"] == 0
    assert audit["invesco_required_gate_count"] == 7
    assert audit["data_passed_gate_count"] == audit["data_required_gate_count"] == 8
    academic = audit["academic_formal_20y"]
    assert academic["strategy_metrics"]["cagr"] > academic["benchmark_metrics"]["MARKET"][
        "cagr"
    ]
    assert all(academic["economic_gates"].values())
    ishares = audit["ishares_actual"]
    assert ishares["strategy_metrics"]["cagr"] > ishares["benchmark_metrics"]["SPY"][
        "cagr"
    ]
    assert ishares["strategy_metrics"]["max_drawdown"] < ishares[
        "benchmark_metrics"
    ]["SPY"]["max_drawdown"]
    assert ishares["fixed_halves_vs_market"]["second"]["cagr_difference"] < 0
    assert ishares["rolling_five_year_vs_market"]["summary"]["cagr_win_fraction"] < 0.60
    invesco = audit["invesco_cross_manager"]
    assert not any(invesco["entry_gates"].values())
    assert invesco["strategy_metrics"]["cagr"] < invesco["benchmark_metrics"]["SPY"][
        "cagr"
    ]
    assert audit["statistical_confirmation"]["academic_formal_vs_market"][
        "active_global_deflated_sharpe"
    ]["trials"] == V24_GLOBAL_SEARCH_TRIALS


def test_v24_report_and_paper_guard(tmp_path: Path) -> None:
    audit = json.loads(VALIDATION.read_text(encoding="utf-8"))
    report = build_quality_momentum_factor_report(tmp_path / "v24.html", audit)
    text = report.read_text(encoding="utf-8")
    assert "教科書因子成立，但可買 ETF 沒有穩健複製" in text
    assert "不要照 QUAL／MTUM 50/50 落盤" in text
    assert "20 年學術代理" in text

    state = tmp_path / "paper_v24_state.json"
    code = cli_main(
        [
            "paper",
            "update",
            "--snapshot",
            str(ISHARES),
            "--strategy",
            "v24",
            "--eligibility-receipt",
            str(VALIDATION),
            "--state",
            str(state),
        ]
    )
    assert code == 2
    assert not state.exists()
