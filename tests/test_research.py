from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from usfddk.data import load_snapshot
from usfddk.research import (
    V3_CROSS_MARKET_PROTOCOL_SHA256,
    V3_CROSS_MARKETS,
    V4_STYLE_PROTOCOL_SHA256,
    V5_THREE_CLOCK_PROTOCOL_SHA256,
    evaluate_style_rotation_research,
    evaluate_three_clock_ensemble_research,
    evaluate_trend_confirmed_guard_research,
    evaluate_v3_cross_market_research,
)


def test_v3_research_fails_closed_without_frozen_proxy(synthetic_panel):
    strategy, targets, audit = evaluate_trend_confirmed_guard_research(
        synthetic_panel,
        start="2022-01-03",
        cost_bps=10,
        proxy_panel=None,
    )

    assert strategy.name == audit["strategy_name"]
    assert list(targets.columns) == ["QQQ", "SHY"]
    assert audit["proxy_validation"]["status"] == "missing"
    assert not audit["proxy_validation_passed"]
    assert not audit["reference_trade_candidate"]
    assert not audit["promotion_ready"]


def _cross_market_inputs():
    paths = {
        "^GSPC": "artifacts/cross_market_gspc_19870101_20060728_fbe6b740.zip",
        "^FTSE": "artifacts/cross_market_ftse_19870101_20060728_e0e17b65.zip",
        "^GDAXI": "artifacts/cross_market_gdaxi_19870101_20060728_ecf4465b.zip",
        "^N225": "artifacts/cross_market_n225_19870101_20060728_df89bb42.zip",
        "^HSI": "artifacts/cross_market_hsi_19870101_20060728_e05499d6.zip",
    }
    panels = {}
    receipts = {}
    for ticker, raw_path in paths.items():
        path = Path(raw_path)
        panel, manifest = load_snapshot(path)
        panels[ticker] = panel
        receipts[ticker] = {
            "path": raw_path,
            "panel_sha256": manifest["panel_sha256"],
            "archive_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "protocol_sha256": manifest["provider_metadata"]["protocol_sha256"],
        }
    return panels, receipts


def test_v3_frozen_cross_market_validation_retains_the_negative_result():
    panels, receipts = _cross_market_inputs()
    audit = evaluate_v3_cross_market_research(
        panels,
        snapshot_receipts=receipts,
        protocol_sha256=V3_CROSS_MARKET_PROTOCOL_SHA256,
    )

    assert set(audit["markets"]) == set(V3_CROSS_MARKETS)
    assert audit["status"] == "cross_market_failed"
    assert not audit["cross_market_passed"]
    assert audit["promotion_effect"] == "none"
    assert audit["counts"] == {
        "full_cagr": 1,
        "sharpe": 3,
        "drawdown_10pp": 1,
        "cost_50bps": 1,
        "rolling_60pct": 0,
        "both_halves": 1,
    }
    assert not any(audit["aggregate_gates"].values())
    assert audit["pooled_active_return"]["newey_west"]["t_stat"] < 0
    assert audit["markets"]["^GDAXI"]["cagr_difference"] > 0
    for ticker in ("^GSPC", "^FTSE", "^N225", "^HSI"):
        assert audit["markets"][ticker]["cagr_difference"] < 0


def test_v3_cross_market_validation_fails_closed_on_protocol_drift():
    panels, receipts = _cross_market_inputs()

    with pytest.raises(ValueError, match="協議雜湊"):
        evaluate_v3_cross_market_research(
            panels,
            snapshot_receipts=receipts,
            protocol_sha256="0" * 64,
        )


def _style_rotation_inputs():
    paths = {
        "trade": Path(
            "artifacts/snapshot_v4_style_trade_20030701_20260731_e879c128.zip"
        ),
        "proxy": Path(
            "artifacts/snapshot_v4_style_proxy_19930701_20060728_a94ed540.zip"
        ),
    }
    panels = {}
    receipts = {}
    for key, path in paths.items():
        panel, manifest = load_snapshot(path)
        panels[key] = panel
        receipts[key] = {
            "path": str(path),
            "rows": int(manifest["rows"]),
            "start": str(manifest["start"]),
            "end": str(manifest["end"]),
            "tickers": list(manifest["tickers"]),
            "panel_sha256": str(manifest["panel_sha256"]),
            "archive_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "protocol_sha256": str(
                manifest["provider_metadata"]["protocol_sha256"]
            ),
            "created_at": str(manifest["created_at"]),
        }
    return panels, receipts


def test_v4_style_rotation_retains_data_failure_and_tradeable_negative_result():
    panels, receipts = _style_rotation_inputs()

    strategy, targets, audit = evaluate_style_rotation_research(
        panels["trade"],
        panels["proxy"],
        trade_receipt=receipts["trade"],
        proxy_receipt=receipts["proxy"],
        protocol_sha256=V4_STYLE_PROTOCOL_SHA256,
    )

    assert strategy.metrics == audit["trade"]["strategy_metrics"]
    assert list(targets.columns) == ["IWF", "IWD", "IJR", "SHY"]
    assert audit["status"] == "historical_failed"
    assert audit["passed_gate_count"] == 2
    assert not audit["data_gate_passed"]
    assert audit["proxy"]["status"] == "data_gate_failed"
    assert audit["proxy"]["coverage"]["^RLG"]["first_valid"] == "2002-09-30"
    assert audit["proxy"]["coverage"]["^RLV"][
        "warmup_sessions_before_1996_07_31"
    ] == 0
    assert audit["trade"]["comparisons"]["market"]["cagr_difference"] < 0
    assert audit["trade"]["comparisons"]["market"]["drawdown_improvement"] > 0.20
    assert not audit["paper_eligible"]
    assert not audit["reference_trade_candidate"]


def test_v4_style_rotation_fails_closed_on_protocol_drift():
    panels, receipts = _style_rotation_inputs()

    with pytest.raises(ValueError, match="協議雜湊"):
        evaluate_style_rotation_research(
            panels["trade"],
            panels["proxy"],
            trade_receipt=receipts["trade"],
            proxy_receipt=receipts["proxy"],
            protocol_sha256="0" * 64,
        )


def _v5_main_and_proxy_inputs():
    paths = {
        "main": Path("artifacts/snapshot_20260731_6a7ca6b8.zip"),
        "proxy": Path(
            "artifacts/snapshot_ndx_proxy_19851001_20060728_4814654a.zip"
        ),
    }
    panels = {}
    receipts = {}
    for key, path in paths.items():
        panel, manifest = load_snapshot(path)
        panels[key] = panel
        receipts[key] = {
            "path": str(path),
            "rows": int(manifest["rows"]),
            "start": str(manifest["start"]),
            "end": str(manifest["end"]),
            "tickers": list(manifest["tickers"]),
            "panel_sha256": str(manifest["panel_sha256"]),
            "archive_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "created_at": str(manifest["created_at"]),
        }
    return panels, receipts


def test_v5_three_clock_retains_recent_success_and_external_failure():
    panels, receipts = _v5_main_and_proxy_inputs()
    cross_panels, cross_receipts = _cross_market_inputs()

    strategy, targets, audit = evaluate_three_clock_ensemble_research(
        panels["main"],
        panels["proxy"],
        cross_panels,
        main_receipt=receipts["main"],
        proxy_receipt=receipts["proxy"],
        cross_receipts=cross_receipts,
        protocol_sha256=V5_THREE_CLOCK_PROTOCOL_SHA256,
    )

    assert strategy.metrics == audit["main"]["strategy_metrics"]
    assert list(targets.columns) == ["QQQ", "SHY"]
    assert audit["status"] == "historical_failed"
    assert audit["passed_gate_count"] == 10
    assert audit["required_gate_count"] == 22
    assert audit["gates"]["01_main_cagr_above_spy_and_matched_95_5"]
    assert audit["gates"]["08_main_qqq_return_and_drawdown_opportunity_cost"]
    assert not audit["gates"][
        "09_main_dsr_at_least_95pct_vs_spy_and_matched"
    ]
    assert not audit["gates"]["12_proxy_rolling_wins_and_positive_medians"]
    assert audit["main"]["comparisons"]["opportunity"]["cagr_difference"] > 0
    assert audit["main"]["comparisons"]["opportunity"][
        "drawdown_improvement"
    ] > 0.11
    assert audit["proxy"]["rolling_five_year"]["market"]["summary"][
        "cagr_win_fraction"
    ] < 0.40
    assert audit["cross_market"]["counts"] == {
        "full_cagr_beats_both": 1,
        "sharpe_beats_both": 3,
        "drawdown_improves_buyhold_10pp": 0,
        "cost_50bps_beats_both": 0,
        "rolling_60pct_vs_both": 0,
        "both_halves_beat_both": 0,
    }
    assert not audit["paper_eligible"]
    assert not audit["reference_trade_candidate"]


def test_v5_three_clock_fails_closed_on_protocol_drift():
    panels, receipts = _v5_main_and_proxy_inputs()
    cross_panels, cross_receipts = _cross_market_inputs()

    with pytest.raises(ValueError, match="協議雜湊"):
        evaluate_three_clock_ensemble_research(
            panels["main"],
            panels["proxy"],
            cross_panels,
            main_receipt=receipts["main"],
            proxy_receipt=receipts["proxy"],
            cross_receipts=cross_receipts,
            protocol_sha256="0" * 64,
        )
