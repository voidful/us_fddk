from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from .data import load_snapshot, panel_fingerprint
from .short_term_high_return import _completed_period_mask
from .short_term_laggard_reversal_nonoverlap import (
    _canonical_sha256,
    _privacy_scan,
    _sha256_file,
    _simulate_passive,
    _simulate_schedule,
)
from .short_term_market_stress_laggard_reversal import _valid_complete_symbols
from .short_term_volume_breakout_diagnostic import (
    BREAKOUT_LOOKBACK,
    DOLLAR_VOLUME_THRESHOLD,
    END,
    MOMENTUM_SESSIONS,
    PRICE_THRESHOLD,
    SELECTION_COUNT,
    SNAPSHOT_ARCHIVE_SHA256,
    SNAPSHOT_FILENAME,
    SNAPSHOT_PANEL_SHA256,
    START,
    TREND_SMA_SESSIONS,
    VOLUME_MULTIPLE,
    WATCHLIST_COUNT,
    WATCHLIST_PATH,
    WATCHLIST_SHA256,
)
from .universe import load_stock_watchlist

SCHEMA_VERSION = "usfddk.short_term_volume_breakout_nonoverlap.v1"
PROTOCOL_PATH = Path("docs/SHORT_TERM_VOLUME_BREAKOUT_NONOVERLAP_PROTOCOL.md")
PROTOCOL_RECEIPT_PATH = Path(
    "artifacts/short_term_volume_breakout_nonoverlap_protocol_receipt.json"
)
VALIDATION_PATH = Path(
    "artifacts/short_term_volume_breakout_nonoverlap_validation.json"
)
EXPECTED_PROTOCOL_SHA256 = (
    "127d958369d1a277b252a101f00dbf5cc0ffd1d80fc01b4a00baf99cc797f20c"
)
EXPECTED_PROTOCOL_RECEIPT_SHA256 = (
    "ca66206a32870fd670182fe3d418b7adf438282c4164d57d4bf7921a4973c4b3"
)
ROUND_TRIP_COST_BPS = 20.0
STARTING_CAPITAL_USD = 1_000.0
HORIZON = 20
GLOBAL_TRIAL_PRIOR_LOWER_BOUND = 6312
GLOBAL_TRIAL_INCREMENT = 1
GLOBAL_TRIAL_FAMILY_ID = "round61_volume_breakout_nonoverlap_capital"


class VolumeBreakoutNonoverlapError(RuntimeError):
    def __init__(self, code: str, detail: str):
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}")


def _fail(code: str, detail: str) -> None:
    raise VolumeBreakoutNonoverlapError(code, detail)


def _load_protocol(root: Path) -> dict[str, Any]:
    if _sha256_file(root / PROTOCOL_PATH) != EXPECTED_PROTOCOL_SHA256:
        _fail("volume_nonoverlap_protocol_drift", "protocol bytes drifted")
    try:
        receipt = json.loads((root / PROTOCOL_RECEIPT_PATH).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        _fail("volume_nonoverlap_protocol_drift", type(exc).__name__)
    if not isinstance(receipt, dict):
        _fail("volume_nonoverlap_protocol_drift", "receipt is not an object")
    claimed = receipt.get("receipt_sha256")
    unsigned = dict(receipt)
    unsigned.pop("receipt_sha256", None)
    if claimed != EXPECTED_PROTOCOL_RECEIPT_SHA256 or _canonical_sha256(unsigned) != claimed:
        _fail("volume_nonoverlap_protocol_drift", "receipt hash drifted")
    expected = {
        "schema_version": 1,
        "research_round": 61,
        "status": "posthoc_volume_breakout_nonoverlap_capital_diagnostic_only",
        "research_role": "capital_accounting_diagnostic",
        "independent_first_seen_evidence": False,
        "strategy_rule_changed": False,
        "protocol_sha256": EXPECTED_PROTOCOL_SHA256,
        "snapshot_filename": SNAPSHOT_FILENAME,
        "snapshot_archive_sha256": SNAPSHOT_ARCHIVE_SHA256,
        "snapshot_panel_sha256": SNAPSHOT_PANEL_SHA256,
        "watchlist_count": WATCHLIST_COUNT,
        "watchlist_sha256": WATCHLIST_SHA256,
        "period": {"start": START, "end": END},
        "frequency": "weekly_completed_xnys",
        "holding_sessions": HORIZON,
        "selection_count": SELECTION_COUNT,
        "starting_capital_usd": STARTING_CAPITAL_USD,
        "cost_round_trip_bps": ROUND_TRIP_COST_BPS,
        "performance_authorized": False,
        "paper_authorized": False,
        "real_money_authorized": False,
        "today_action": "今天不下單",
        "global_trial_ledger": {
            "prior_lower_bound": GLOBAL_TRIAL_PRIOR_LOWER_BOUND,
            "minimum_increment": GLOBAL_TRIAL_INCREMENT,
            "new_family_id": GLOBAL_TRIAL_FAMILY_ID,
        },
    }
    if any(receipt.get(key) != value for key, value in expected.items()):
        _fail("volume_nonoverlap_protocol_drift", "fixed receipt field drifted")
    if receipt.get("signal") != {
        "breakout_lookback_sessions": BREAKOUT_LOOKBACK,
        "dollar_volume_threshold_usd": DOLLAR_VOLUME_THRESHOLD,
        "momentum_sessions": MOMENTUM_SESSIONS,
        "price_threshold_usd": PRICE_THRESHOLD,
        "selection_count": SELECTION_COUNT,
        "trend_sma_sessions": TREND_SMA_SESSIONS,
        "volume_multiple": VOLUME_MULTIPLE,
        "market_filter": "none",
    }:
        _fail("volume_nonoverlap_protocol_drift", "signal contract drifted")
    if receipt.get("execution") != {
        "entry": "next_session_adjusted_open",
        "exit": "session_{holding_sessions}_adjusted_close",
        "overlap_policy": "ignore_signals_until_exit_then_resume",
        "cost_allocation": "10_bps_entry_plus_10_bps_exit",
    }:
        _fail("volume_nonoverlap_protocol_drift", "execution contract drifted")
    if receipt.get("baselines") != {
        "event_schedule": ["eligible_pool", "complete_cohort", "SPY", "QQQ"],
        "passive": ["SPY", "QQQ"],
    }:
        _fail("volume_nonoverlap_protocol_drift", "baseline contract drifted")
    if receipt.get("gate_names") != [
        "at_least_30_accepted_events",
        "final_equity_above_start",
        "cagr_above_event_schedule_eligible_pool",
        "cagr_above_passive_SPY",
        "cagr_above_passive_QQQ",
        "max_drawdown_not_deeper_than_passive_SPY",
        "max_drawdown_not_deeper_than_passive_QQQ",
    ]:
        _fail("volume_nonoverlap_protocol_drift", "gate contract drifted")
    return receipt


def _candidate_events(panel: Any, stocks: list[str]) -> list[dict[str, Any]]:
    close = panel.close[stocks]
    volume = panel.volume[stocks]
    dollar_volume = (close * volume).rolling(20, min_periods=20).median()
    volume_median = volume.rolling(20, min_periods=20).median()
    trend = close.rolling(TREND_SMA_SESSIONS, min_periods=TREND_SMA_SESSIONS).mean()
    momentum = close.pct_change(MOMENTUM_SESSIONS, fill_method=None)
    prior_high = close.rolling(BREAKOUT_LOOKBACK, min_periods=BREAKOUT_LOOKBACK).max().shift(1)
    index = pd.DatetimeIndex(panel.close.index).normalize()
    index = index[(index >= pd.Timestamp(START)) & (index <= pd.Timestamp(END))]
    weekly = pd.DatetimeIndex(
        panel.close.index[_completed_period_mask(panel.close.index, "weekly")]
    ).normalize()
    weekly = weekly[(weekly >= pd.Timestamp(START)) & (weekly <= pd.Timestamp(END))]
    candidates: list[dict[str, Any]] = []
    for signal_date in weekly:
        if signal_date not in index:
            continue
        position = index.get_loc(signal_date)
        if not isinstance(position, int) or position + HORIZON + 1 >= len(index):
            continue
        entry_date = index[position + 1]
        exit_date = index[position + 1 + HORIZON]
        base = (
            (close.loc[signal_date] > PRICE_THRESHOLD)
            & (dollar_volume.loc[signal_date] >= DOLLAR_VOLUME_THRESHOLD)
            & (close.loc[signal_date] > trend.loc[signal_date])
            & momentum.loc[signal_date].notna()
            & (momentum.loc[signal_date] > 0.0)
        )
        signal = (
            base
            & (close.loc[signal_date] >= prior_high.loc[signal_date])
            & (volume.loc[signal_date] >= VOLUME_MULTIPLE * volume_median.loc[signal_date])
        )
        selected = sorted(
            signal.index[signal],
            key=lambda symbol: (-float(momentum.loc[signal_date, symbol]), symbol),
        )[:SELECTION_COUNT]
        eligible = list(base.index[base])
        if not selected or len(eligible) < SELECTION_COUNT:
            continue
        complete = _valid_complete_symbols(
            panel,
            stocks,
            signal_date=signal_date,
            entry_date=entry_date,
            exit_date=exit_date,
        )
        if len(complete) < SELECTION_COUNT or not set(selected).issubset(complete):
            continue
        candidates.append(
            {
                "signal_date": signal_date,
                "entry_date": entry_date,
                "exit_date": exit_date,
                "selected": selected,
                "eligible": [symbol for symbol in eligible if symbol in complete],
                "complete": complete,
            }
        )
    return candidates


def _accepted_events(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    accepted: list[dict[str, Any]] = []
    last_exit: pd.Timestamp | None = None
    for event in candidates:
        if last_exit is not None and event["signal_date"] <= last_exit:
            continue
        accepted.append(event)
        last_exit = event["exit_date"]
    return accepted


def audit_volume_breakout_nonoverlap(
    *, repository_root: Path, snapshot_path: Path
) -> dict[str, Any]:
    root = repository_root.resolve()
    _load_protocol(root)
    snapshot = snapshot_path.resolve()
    if snapshot.name != SNAPSHOT_FILENAME or not snapshot.is_file() or snapshot.is_symlink():
        _fail("volume_nonoverlap_snapshot_invalid", "snapshot path is not fixed")
    if _sha256_file(snapshot) != SNAPSHOT_ARCHIVE_SHA256:
        _fail("volume_nonoverlap_snapshot_invalid", "snapshot archive hash drifted")
    panel, manifest = load_snapshot(snapshot)
    if (
        manifest.get("panel_sha256") != SNAPSHOT_PANEL_SHA256
        or panel_fingerprint(panel) != SNAPSHOT_PANEL_SHA256
    ):
        _fail("volume_nonoverlap_snapshot_invalid", "snapshot panel hash drifted")
    if _sha256_file(root / WATCHLIST_PATH) != WATCHLIST_SHA256:
        _fail("volume_nonoverlap_source_invalid", "watchlist hash drifted")
    records = load_stock_watchlist()
    stocks = [record.symbol for record in records if record.symbol in panel.close.columns]
    if len(records) != WATCHLIST_COUNT or len(stocks) != WATCHLIST_COUNT:
        _fail("volume_nonoverlap_source_invalid", "watchlist coverage drifted")
    index = pd.DatetimeIndex(panel.close.index).normalize()
    index = index[(index >= pd.Timestamp(START)) & (index <= pd.Timestamp(END))]
    candidates = _candidate_events(panel, stocks)
    accepted = _accepted_events(candidates)
    if not accepted:
        _fail("volume_nonoverlap_no_events", "no accepted events")
    scheduled = {
        "selected": _simulate_schedule(panel, index, accepted, lambda event: event["selected"]),
        "eligible_pool": _simulate_schedule(
            panel, index, accepted, lambda event: event["eligible"]
        ),
        "complete_cohort": _simulate_schedule(
            panel, index, accepted, lambda event: event["complete"]
        ),
        "SPY": _simulate_schedule(panel, index, accepted, lambda event: ["SPY"]),
        "QQQ": _simulate_schedule(panel, index, accepted, lambda event: ["QQQ"]),
    }
    passive = {
        "SPY": _simulate_passive(panel, index, "SPY"),
        "QQQ": _simulate_passive(panel, index, "QQQ"),
    }
    selected = scheduled["selected"]
    gates = {
        "at_least_30_accepted_events": selected["events"] >= 30,
        "final_equity_above_start": selected["final_equity_usd"] > STARTING_CAPITAL_USD,
        "cagr_above_event_schedule_eligible_pool": selected["cagr"]
        > scheduled["eligible_pool"]["cagr"],
        "cagr_above_passive_SPY": selected["cagr"] > passive["SPY"]["cagr"],
        "cagr_above_passive_QQQ": selected["cagr"] > passive["QQQ"]["cagr"],
        "max_drawdown_not_deeper_than_passive_SPY": selected["max_drawdown"]
        >= passive["SPY"]["max_drawdown"],
        "max_drawdown_not_deeper_than_passive_QQQ": selected["max_drawdown"]
        >= passive["QQQ"]["max_drawdown"],
    }
    result: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "research_round": 61,
        "status": (
            "volume_breakout_nonoverlap_capital_positive_survivorship_biased"
            if all(gates.values())
            else "volume_breakout_nonoverlap_capital_negative_survivorship_biased"
        ),
        "research_role": "capital_accounting_diagnostic",
        "independent_first_seen_evidence": False,
        "strategy_rule_changed": False,
        "source": {
            "protocol_sha256": EXPECTED_PROTOCOL_SHA256,
            "snapshot_filename": SNAPSHOT_FILENAME,
            "snapshot_archive_sha256": SNAPSHOT_ARCHIVE_SHA256,
            "snapshot_panel_sha256": SNAPSHOT_PANEL_SHA256,
            "watchlist_count": WATCHLIST_COUNT,
            "watchlist_sha256": WATCHLIST_SHA256,
            "period": {"start": START, "end": END},
        },
        "signal_definition": {
            "frequency": "weekly_completed_xnys",
            "market_filter": "none",
            "breakout_lookback_sessions": BREAKOUT_LOOKBACK,
            "trend_sma_sessions": TREND_SMA_SESSIONS,
            "momentum_sessions": MOMENTUM_SESSIONS,
            "volume_multiple": VOLUME_MULTIPLE,
            "selection_count": SELECTION_COUNT,
            "round_trip_cost_bps": ROUND_TRIP_COST_BPS,
        },
        "capital_policy": {
            "starting_capital_usd": STARTING_CAPITAL_USD,
            "holding_sessions": HORIZON,
            "overlap_policy": "ignore_signals_until_exit_then_resume",
            "candidate_events": len(candidates),
            "accepted_events": len(accepted),
            "ignored_overlapping_events": len(candidates) - len(accepted),
        },
        "scheduled_baselines": scheduled,
        "passive_baselines": passive,
        "gate_summary": {
            "gates": gates,
            "passed": int(sum(bool(value) for value in gates.values())),
            "required": len(gates),
        },
        "multiplicity": {
            "prior_lower_bound": GLOBAL_TRIAL_PRIOR_LOWER_BOUND,
            "increment": GLOBAL_TRIAL_INCREMENT,
            "current_lower_bound": GLOBAL_TRIAL_PRIOR_LOWER_BOUND + GLOBAL_TRIAL_INCREMENT,
            "family_id": GLOBAL_TRIAL_FAMILY_ID,
        },
        "state_boundary": {
            "performance_present": False,
            "strategy_run_count": 0,
            "paper_authorized": False,
            "real_money_authorized": False,
            "real_money_action_usd": 0,
            "today_action": "今天不下單",
        },
        "limitations": [
            "current_watchlist_is_survivorship_biased",
            "posthoc_capital_accounting_is_not_independent_first_seen_evidence",
            "adjusted_ohlcv_is_not_raw_execution_or_complete_total_return_ledger",
            "volume_has_no_intraday_public_timestamp",
            "no_point_in_time_universe_or_delisting_economics",
            "fractional_equal_weight_is_a_research_convention",
        ],
    }
    _privacy_scan(result)
    result["receipt_sha256"] = _canonical_sha256(result)
    return result


def write_validation_receipt(result: dict[str, Any], *, repository_root: Path) -> Path:
    path = repository_root / VALIDATION_PATH
    path.write_text(
        json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False)
        + "\n",
        encoding="utf-8",
    )
    return path
