from __future__ import annotations

import hashlib
from pathlib import Path

import pandas as pd
import pytest

from usfddk.data import load_snapshot, panel_fingerprint
from usfddk.industry import (
    FRENCH_INDUSTRIES,
    V6_PROTOCOL_SHA256,
    evaluate_industry_tilt_research,
    load_french_industry_proxy,
)
from usfddk.strategies import (
    industry_momentum_core_tilt_targets,
    industry_selection_matched_targets,
)

ROOT = Path(__file__).resolve().parents[1]
ETF_SNAPSHOT = ROOT / "artifacts/snapshot_v6_sector_etf_19981201_20260731_9238e84a.zip"
INDUSTRY_ZIP = ROOT / "artifacts/french_10_industry_245ac83a.zip"
FACTORS_ZIP = ROOT / "artifacts/french_ff_factors_80b88699.zip"


def _inputs():
    panel, manifest = load_snapshot(ETF_SNAPSHOT)
    etf_receipt = {
        "path": str(ETF_SNAPSHOT),
        "rows": manifest["rows"],
        "start": manifest["start"],
        "end": manifest["end"],
        "tickers": manifest["tickers"],
        "panel_sha256": panel_fingerprint(panel),
        "archive_sha256": hashlib.sha256(ETF_SNAPSHOT.read_bytes()).hexdigest(),
        "created_at": manifest["created_at"],
        "provider_metadata": manifest["provider_metadata"],
        "contract": manifest["contract"],
    }
    industries, factors, french_receipt = load_french_industry_proxy(
        INDUSTRY_ZIP, FACTORS_ZIP
    )
    return panel, etf_receipt, industries, factors, french_receipt


def test_v6_protocol_and_official_proxy_are_frozen_and_complete():
    assert hashlib.sha256(
        (ROOT / "docs/V6_INDUSTRY_TILT_PROTOCOL.md").read_bytes()
    ).hexdigest() == V6_PROTOCOL_SHA256
    _, _, industries, factors, receipt = _inputs()
    assert tuple(industries.columns) == FRENCH_INDUSTRIES
    assert list(factors.columns) == ["Mkt-RF", "RF"]
    assert len(industries) == 948
    assert industries.index[0] == pd.Timestamp("1927-01-31")
    assert industries.index[-1] == pd.Timestamp("2005-12-31")
    assert not industries.isna().any().any()
    assert receipt["missing_value_policy"].startswith("reject")


def test_v6_matched_control_exactly_matches_monthly_equity_exposure():
    panel, *_ = _inputs()
    target = industry_momentum_core_tilt_targets(panel.close)
    matched = industry_selection_matched_targets(target)
    industries = ["XLB", "XLE", "XLF", "XLI", "XLK", "XLP", "XLU", "XLV", "XLY"]
    signal_days = target.dropna(how="all").index
    assert len(signal_days) > 250
    for day in signal_days:
        selected_exposure = float(target.loc[day, industries].sum())
        matched_exposure = float(matched.loc[day, industries].sum())
        assert matched_exposure == pytest.approx(selected_exposure)
        assert float(matched.loc[day].sum()) == pytest.approx(1.0)


def test_v6_frozen_rule_is_rejected_and_does_not_open_paper():
    panel, etf_receipt, industries, factors, french_receipt = _inputs()
    _, _, audit = evaluate_industry_tilt_research(
        panel,
        industries,
        factors,
        etf_receipt=etf_receipt,
        french_receipt=french_receipt,
        protocol_sha256=V6_PROTOCOL_SHA256,
    )
    assert audit["passed_gate_count"] == 11
    assert audit["required_gate_count"] == 22
    assert not audit["historical_gate_passed"]
    assert not audit["paper_eligible"]
    assert audit["promotion_effect"] == "none"
    assert audit["main"]["strategy_metrics"]["cagr"] == pytest.approx(0.10002571899612578)
    assert audit["main"]["benchmark_metrics"]["spy"]["cagr"] == pytest.approx(
        0.11269641150272025
    )
    assert audit["main"]["benchmark_metrics"]["matched"]["cagr"] == pytest.approx(
        0.10196742859865116
    )
    assert not audit["gates"]["01_main_cagr_beats_spy_and_matched_10bp"]
    assert audit["proxy"]["decade_wins"] == 5


def test_v6_fails_closed_on_protocol_drift():
    panel, etf_receipt, industries, factors, french_receipt = _inputs()
    with pytest.raises(ValueError, match="協議雜湊"):
        evaluate_industry_tilt_research(
            panel,
            industries,
            factors,
            etf_receipt=etf_receipt,
            french_receipt=french_receipt,
            protocol_sha256="0" * 64,
        )
