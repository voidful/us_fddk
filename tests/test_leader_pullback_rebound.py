from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from usfddk.leader_pullback_rebound import (
    FROZEN_CONTRACT,
    PATH_IDS,
    PROTOCOL_PATH,
    PROTOCOL_SHA256,
    LeaderPullbackReboundError,
    _symbols_hash,
    _validate_parent_event_identity,
    compute_structure_feature,
    run_leader_pullback_rebound,
    validate_leader_pullback_rebound_contract,
)

ROOT = Path(__file__).resolve().parents[1]
TOP_LEVEL_KEYS = {
    "schema_version",
    "research_round",
    "research_role",
    "generated_on",
    "protocol",
    "references",
    "input",
    "input_receipts",
    "method",
    "reconstruction",
    "selection_distribution",
    "selection_receipts",
    "calendar_integrity",
    "paths",
    "family",
    "stresses",
    "gates",
    "gate_summary",
    "controls",
    "control_summary",
    "attacks",
    "attack_summary",
    "calendar_rows",
    "decision",
}


def _synthetic_ohlc() -> tuple[pd.Series, pd.Series, pd.Series, pd.Series]:
    index = pd.bdate_range("2025-01-02", periods=80)
    close = pd.Series(np.linspace(80.0, 100.0, len(index)), index=index)
    close.iloc[-20:] = np.linspace(106.0, 94.0, 20)
    close.iloc[-1] = 96.0
    open_ = close.mul(0.999)
    high = pd.concat([open_, close], axis=1).max(axis=1).add(1.25)
    low = pd.concat([open_, close], axis=1).min(axis=1).sub(1.25)
    return open_, high, low, close


def test_frozen_contract_and_protocol_hash() -> None:
    validate_leader_pullback_rebound_contract(FROZEN_CONTRACT)
    import hashlib

    assert hashlib.sha256((ROOT / PROTOCOL_PATH).read_bytes()).hexdigest() == PROTOCOL_SHA256
    with pytest.raises(LeaderPullbackReboundError) as error:
        validate_leader_pullback_rebound_contract(
            replace(FROZEN_CONTRACT, initial_capital_usd=999.0)
        )
    assert error.value.code == "lpr_initial_capital_mismatch"


def test_structure_feature_formula_and_no_lookahead() -> None:
    open_, high, low, close = _synthetic_ohlc()
    signal = close.index[-2]
    observed = compute_structure_feature(open_, high, low, close, signal)
    tr_dates = close.index[-15:-1]
    previous = close.reindex(close.index[-16:-2]).to_numpy()
    expected_tr = np.maximum(
        high.reindex(tr_dates).to_numpy() - low.reindex(tr_dates).to_numpy(),
        np.maximum(
            np.abs(high.reindex(tr_dates).to_numpy() - previous),
            np.abs(low.reindex(tr_dates).to_numpy() - previous),
        ),
    )
    assert observed["atr14"] == pytest.approx(float(expected_tr.mean()))
    assert observed["high20"] == pytest.approx(float(close.loc[:signal].iloc[-20:].max()))
    assert observed["high60"] == pytest.approx(float(close.loc[:signal].iloc[-60:].max()))
    assert observed["low10"] == pytest.approx(float(low.loc[:signal].iloc[-10:].min()))

    modified = [series.copy() for series in (open_, high, low, close)]
    for series in modified:
        series.loc[close.index[-1]] *= 20.0
    assert compute_structure_feature(*modified, signal) == observed


def test_structure_feature_rejects_bad_ohlc() -> None:
    open_, high, low, close = _synthetic_ohlc()
    signal = close.index[-1]
    high.loc[signal] = close.loc[signal] - 1.0
    with pytest.raises(LeaderPullbackReboundError) as error:
        compute_structure_feature(open_, high, low, close, signal)
    assert error.value.code == "lpr_ohlc_geometry_mismatch"


def test_structure_feature_rejects_silently_missing_ohlc_session() -> None:
    open_, high, low, close = _synthetic_ohlc()
    high = high.drop(high.index[-10])
    with pytest.raises(LeaderPullbackReboundError) as error:
        compute_structure_feature(open_, high, low, close, close.index[-1])
    assert error.value.code == "lpr_ohlc_index_mismatch"


def test_parent_selected_order_mutation_is_rejected() -> None:
    eligible = list("ABCDEFGHI")
    ranked = list("IHGFEDCBA")
    selected = ranked[:7]
    event = {
        "event_index": 0,
        "slot": 0,
        "signal_date": pd.Timestamp("2025-01-03"),
        "entry_date": pd.Timestamp("2025-01-06"),
        "exit_date": pd.Timestamp("2025-01-31"),
        "eligible": eligible,
        "ranked": ranked,
        "selected": selected.copy(),
    }
    round29_receipt = {
        "event_index": 0,
        "slot": 0,
        "signal_date": "2025-01-03",
        "entry_date": "2025-01-06",
        "exit_date": "2025-01-31",
        "eligible_count": len(eligible),
        "eligible_sha256": _symbols_hash(eligible),
        "selected": selected,
        "selected_sha256": _symbols_hash(selected),
    }
    round38_receipt = {
        "event_index": 0,
        "slot": 0,
        "signal_date": "2025-01-03",
        "entry_date": "2025-01-06",
        "exit_date": "2025-01-31",
        "eligible_count": len(eligible),
        "eligible_sha256": _symbols_hash(eligible),
        "window_top7": {"20": selected},
        "window_ranked_sha256": {"20": _symbols_hash(ranked)},
    }
    _validate_parent_event_identity(
        event, round29_receipt, dict(round29_receipt), round38_receipt
    )
    event["selected"][0], event["selected"][1] = event["selected"][1], event["selected"][0]
    with pytest.raises(LeaderPullbackReboundError) as error:
        _validate_parent_event_identity(
            event, round29_receipt, dict(round29_receipt), round38_receipt
        )
    assert error.value.code == "lpr_parent_event_identity_mismatch"


@pytest.fixture(scope="module")
def receipt() -> dict:
    return run_leader_pullback_rebound(ROOT)


def test_public_runner_schema_and_parent_identities(receipt: dict) -> None:
    assert set(receipt) == TOP_LEVEL_KEYS
    assert receipt["research_round"] == 39
    assert receipt["protocol"]["sha256"] == PROTOCOL_SHA256
    assert receipt["input"]["events"] == 905
    assert receipt["reconstruction"]["parent"]["maximum_event_return_residual"] <= 1e-12
    assert receipt["reconstruction"]["ten_day"]["maximum_ten_day_event_return_residual"] <= 1e-12
    assert tuple(receipt["paths"]) == PATH_IDS
    assert receipt["calendar_integrity"]["sessions"] == 5_028
    assert receipt["calendar_integrity"]["pre_trade_cash_sessions"] == 1
    assert receipt["calendar_integrity"]["comparison_trade_sessions"] == 5_027
    assert receipt["calendar_integrity"]["protocol_calendar_internal_consistency"] is False
    assert receipt["calendar_integrity"]["maximum_concurrent_ten_day_intervals"] <= 5
    assert receipt["calendar_integrity"]["terminal_state_all_cash"] is True
    assert set(receipt["calendar_integrity"]["terminal_exposure"].values()) == {0.0}
    assert set(receipt["calendar_integrity"]["terminal_position_count"].values()) == {0}
    order_diagnostics = receipt["calendar_integrity"]["order_diagnostics"]
    assert all(
        row["actual_total_orders"] == row["expected_total_orders"]
        for row in order_diagnostics["primary"].values()
    )
    assert all(
        row.get("maximum_event_order_count_residual", 0) == 0
        for row in order_diagnostics["primary"].values()
    )
    assert all(
        row.get("event_order_counts_hash_match", True)
        for row in order_diagnostics["primary"].values()
    )
    assert set(order_diagnostics["candidate_ledgers"]) == {
        "primary_10bps_per_leg",
        "fixed_fee_0.01_usd",
        "fixed_fee_0.05_usd",
    }
    assert all(order_diagnostics["candidate_ledgers"].values())
    assert all(
        {"date", "ticker", "side", "notional_usd"}.issubset(row)
        for ledger in order_diagnostics["candidate_ledgers"].values()
        for row in ledger
    )
    assert receipt["family"]["size"] == 8
    assert receipt["family"]["common_bootstrap"]["paths"] == 20_000
    assert receipt["family"]["common_bootstrap"]["seed"] == 39_202_608
    assert len(receipt["gates"]) == 22
    assert receipt["gate_summary"]["all_passed"] is False
    assert receipt["selection_distribution"]["nonempty_events"] == 151
    assert receipt["paths"]["lpr10_qqq_overlay"]["cagr"] < receipt["paths"][
        "qqq_buy_hold"
    ]["cagr"]
    assert receipt["paths"]["lpr10_qqq_overlay"]["cagr"] < receipt["paths"][
        "matched_topn_10d_overlay"
    ]["cagr"]
    assert receipt["control_summary"]["total"] >= 48
    assert receipt["attack_summary"]["total"] >= 48
    assert receipt["attack_summary"]["all_rejected"] is True
    attack_codes = {
        row["field"]: row["observed_error_code"] for row in receipt["attacks"]
    }
    assert attack_codes["parent_top7_order"] == "lpr_parent_event_identity_mismatch"
    assert attack_codes["ohlc_index_drop"] == "lpr_ohlc_index_mismatch"
    assert attack_codes["ohlc_geometry"] == "lpr_ohlc_geometry_mismatch"
    assert all(
        row["maximum_fixed_fee_identity_residual_usd"] <= 1e-12
        for row in receipt["stresses"]["fixed_child_order_fees"].values()
    )
    assert receipt["decision"]["paper_status"] == "all_cash_not_started"
    assert receipt["decision"]["real_money_action_usd"] == 0
