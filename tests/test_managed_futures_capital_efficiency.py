from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd
import pytest

from usfddk.cli import main as cli_main
from usfddk.data import load_snapshot, panel_fingerprint
from usfddk.managed_futures_capital_efficiency import (
    V23_DESIGN_ARCHIVE_SHA256,
    V23_DESIGN_PANEL_SHA256,
    V23_FMF_ARCHIVE_SHA256,
    V23_FMF_PANEL_SHA256,
    V23_KFA_CSV_SHA256,
    V23_KFA_PDF_SHA256,
    V23_KMLM_ARCHIVE_SHA256,
    V23_KMLM_PANEL_SHA256,
    V23_PRODUCT_MAPPING_SHA256,
    V23_PROTOCOL_SHA256,
    _load_kfa_monthly,
    _run_monthly_portfolio,
)
from usfddk.report import build_managed_futures_capital_efficiency_report

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "docs/V23_MANAGED_FUTURES_CAPITAL_EFFICIENCY_PROTOCOL.md"
MAPPING = ROOT / "docs/V23_PRODUCT_MAPPING.md"
PROTOCOL_RECEIPT = ROOT / "artifacts/v23_protocol_receipt.json"
DATA_RECEIPT = ROOT / "artifacts/v23_data_receipt.json"
KFA_PDF = ROOT / "artifacts/v23_kfa_mlm_index_presentation_20260630.pdf"
KFA_CSV = ROOT / "artifacts/v23_kfa_mlm_index_monthly_198801_202606.csv"
DESIGN_SNAPSHOT = (
    ROOT / "artifacts/snapshot_v17_capital_efficient_20040102_20260731_4c948bf6.zip"
)
KMLM_SNAPSHOT = ROOT / "artifacts/snapshot_v23_kmlm_20201201_20260731_a7826ecd.zip"
FMF_SNAPSHOT = ROOT / "artifacts/snapshot_v23_fmf_20130801_20260731_42ecc0b8.zip"
VALIDATION = ROOT / "artifacts/v23_managed_futures_capital_efficiency_validation.json"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_v23_frozen_documents_and_post_freeze_sources_are_fixed() -> None:
    protocol = json.loads(PROTOCOL_RECEIPT.read_text(encoding="utf-8"))
    data = json.loads(DATA_RECEIPT.read_text(encoding="utf-8"))
    assert _sha256(PROTOCOL) == V23_PROTOCOL_SHA256
    assert _sha256(MAPPING) == V23_PRODUCT_MAPPING_SHA256
    assert _sha256(KFA_PDF) == V23_KFA_PDF_SHA256
    assert _sha256(KFA_CSV) == V23_KFA_CSV_SHA256
    assert protocol["protocol_sha256"] == V23_PROTOCOL_SHA256
    assert protocol["product_mapping_sha256"] == V23_PRODUCT_MAPPING_SHA256
    assert data["pre_registration_order_proved"] is True
    assert data["kfa_index_source"]["visual_review_passed"] is True
    assert protocol["protocol_mtime_epoch"] < data["kmlm_snapshot"][
        "snapshot_mtime_epoch"
    ]
    assert protocol["protocol_mtime_epoch"] < data["fmf_snapshot"][
        "snapshot_mtime_epoch"
    ]

    for snapshot, panel_sha, archive_sha in (
        (DESIGN_SNAPSHOT, V23_DESIGN_PANEL_SHA256, V23_DESIGN_ARCHIVE_SHA256),
        (KMLM_SNAPSHOT, V23_KMLM_PANEL_SHA256, V23_KMLM_ARCHIVE_SHA256),
        (FMF_SNAPSHOT, V23_FMF_PANEL_SHA256, V23_FMF_ARCHIVE_SHA256),
    ):
        panel, manifest = load_snapshot(snapshot)
        assert panel_fingerprint(panel) == panel_sha
        assert _sha256(snapshot) == archive_sha
        assert manifest["contract"]["ok"] is True


def test_v23_kfa_formal_table_has_exactly_240_compounding_checked_months() -> None:
    monthly, integrity = _load_kfa_monthly(KFA_CSV)
    formal = monthly.loc["2006-07":"2026-06"]
    assert len(monthly) == 462
    assert len(formal) == 240
    assert integrity["formal_rows"] == 240
    assert integrity["annual_compounding_check_passed"] is True
    assert integrity["maximum_absolute_annual_rounding_difference"] < 0.0015


def test_v23_monthly_engine_charges_initial_and_drift_rebalance_turnover() -> None:
    returns = pd.DataFrame(
        {"A": [0.10, 0.00], "B": [0.00, 0.10]},
        index=pd.to_datetime(["2020-02-28", "2020-03-31"]),
    )
    result = _run_monthly_portfolio(
        returns,
        {"A": 0.5, "B": 0.5},
        name="engine check",
        start_equity_date="2020-01-31",
        cost_bps=10.0,
        rebalance_monthly=True,
    )
    assert result.turnover.iloc[1] == pytest.approx(1.0)
    assert result.equity.iloc[1] == pytest.approx((1.0 - 0.001) * 1.05)
    assert result.turnover.iloc[2] == pytest.approx(2 * abs(0.5 - 0.55 / 1.05))
    second_cost = result.equity.iloc[1] * result.turnover.iloc[2] * 0.001
    assert result.equity.iloc[2] == pytest.approx(
        (result.equity.iloc[1] - second_cost) * 1.05
    )


def test_v23_frozen_result_rejects_paper_and_trade_signal() -> None:
    audit = json.loads(VALIDATION.read_text(encoding="utf-8"))
    assert audit["status"] == "managed_futures_capital_efficiency_validation_failed"
    assert audit["paper_eligible"] is False
    assert audit["trade_ready"] is False
    assert audit["candidate"]["signal_display_allowed"] is False
    assert audit["long_passed_gate_count"] == 6
    assert audit["long_required_gate_count"] == 10
    assert audit["kmlm_bridge_passed_gate_count"] == 7
    assert audit["kmlm_bridge_required_gate_count"] == 10
    assert audit["fmf_passed_gate_count"] == 2
    assert audit["fmf_required_pass_count"] == 5
    assert audit["data_passed_gate_count"] == audit["data_required_gate_count"] == 7
    assert audit["long_horizon"]["strategy_metrics"]["cagr"] > audit[
        "long_horizon"
    ]["benchmark_metrics"]["SPY"]["cagr"]
    assert audit["long_horizon"]["economic_gates"]["cagr_beats_SPY_25bp"] is False
    assert audit["long_horizon"]["economic_gates"][
        "both_fixed_decades_cagr_beat_SPY_10bp"
    ] is False
    assert audit["long_horizon"]["fixed_halves_vs_SPY"]["second"][
        "cagr_difference"
    ] < 0
    assert audit["kmlm_actual_bridge"]["tracking"][
        "annualized_geometric_tracking_gap"
    ] > 0.02
    assert sum(audit["fmf_cross_manager"]["entry_gates"].values()) == 2


def test_v23_report_and_paper_guard(tmp_path: Path) -> None:
    audit = json.loads(VALIDATION.read_text(encoding="utf-8"))
    report = build_managed_futures_capital_efficiency_report(tmp_path / "v23.html", audit)
    text = report.read_text(encoding="utf-8")
    assert "風險路徑改善，但沒有穩健跑贏 SPY" in text
    assert "不要照 50／50 落盤" in text
    assert "20 年長期入口" in text

    state = tmp_path / "paper_v23_state.json"
    code = cli_main(
        [
            "paper",
            "update",
            "--snapshot",
            str(KMLM_SNAPSHOT),
            "--strategy",
            "v23",
            "--eligibility-receipt",
            str(VALIDATION),
            "--state",
            str(state),
        ]
    )
    assert code == 2
    assert not state.exists()
