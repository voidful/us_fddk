from __future__ import annotations

import json
import math
from collections.abc import Callable
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .data import load_snapshot, panel_fingerprint
from .short_term_laggard_reversal_unconditional import (
    DOLLAR_VOLUME_THRESHOLD,
    END,
    LOOKBACK_RETURN_SESSIONS,
    PRICE_THRESHOLD,
    START,
    STOCK_RETURN_THRESHOLD,
    WATCHLIST_COUNT,
    WATCHLIST_PATH,
    WATCHLIST_SHA256,
)
from .short_term_market_stress_laggard_reversal import (
    SNAPSHOT_ARCHIVE_SHA256,
    SNAPSHOT_FILENAME,
    SNAPSHOT_PANEL_SHA256,
    _canonical_sha256,
    _privacy_scan,
    _sha256_file,
    _valid_complete_symbols,
)
from .universe import load_stock_watchlist

SCHEMA_VERSION = "usfddk.short_term_laggard_reversal_nonoverlap.v1"
PROTOCOL_PATH = Path("docs/SHORT_TERM_LAGGARD_REVERSAL_NONOVERLAP_PROTOCOL.md")
PROTOCOL_RECEIPT_PATH = Path(
    "artifacts/short_term_laggard_reversal_nonoverlap_protocol_receipt.json"
)
VALIDATION_PATH = Path(
    "artifacts/short_term_laggard_reversal_nonoverlap_validation.json"
)
EXPECTED_PROTOCOL_SHA256 = (
    "02102596400c9be51d76a1b93928a9d4309c02ffe5d2e4f3ff81cfd0bc424cd9"
)
EXPECTED_PROTOCOL_RECEIPT_SHA256 = (
    "0d80d7371ae1ec13614e4c16a36b7fcadd22b0a84e5e578a92536b75ea640c3d"
)
ROUND_TRIP_COST_BPS = 20.0
ROUND_TRIP_COST = ROUND_TRIP_COST_BPS / 10_000
STARTING_CAPITAL_USD = 1_000.0
HORIZON = 20
SELECTION_COUNT = 5
GLOBAL_TRIAL_PRIOR_LOWER_BOUND = 6311
GLOBAL_TRIAL_INCREMENT = 1
GLOBAL_TRIAL_FAMILY_ID = "round60_laggard_reversal_nonoverlap_capital"


class LaggardReversalNonoverlapError(RuntimeError):
    def __init__(self, code: str, detail: str):
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}")


def _fail(code: str, detail: str) -> None:
    raise LaggardReversalNonoverlapError(code, detail)


def _load_protocol(root: Path) -> dict[str, Any]:
    if _sha256_file(root / PROTOCOL_PATH) != EXPECTED_PROTOCOL_SHA256:
        _fail("laggard_nonoverlap_protocol_drift", "protocol bytes drifted")
    try:
        receipt = json.loads((root / PROTOCOL_RECEIPT_PATH).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        _fail("laggard_nonoverlap_protocol_drift", type(exc).__name__)
    if not isinstance(receipt, dict):
        _fail("laggard_nonoverlap_protocol_drift", "receipt is not an object")
    claimed = receipt.get("receipt_sha256")
    unsigned = dict(receipt)
    unsigned.pop("receipt_sha256", None)
    if claimed != EXPECTED_PROTOCOL_RECEIPT_SHA256 or _canonical_sha256(unsigned) != claimed:
        _fail("laggard_nonoverlap_protocol_drift", "receipt hash drifted")
    expected = {
        "schema_version": 1,
        "research_round": 60,
        "status": "posthoc_laggard_reversal_nonoverlap_capital_diagnostic_only",
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
        _fail("laggard_nonoverlap_protocol_drift", "fixed receipt field drifted")
    if receipt.get("signal") != {
        "frequency": "daily_completed_xnys",
        "dollar_volume_threshold_usd": DOLLAR_VOLUME_THRESHOLD,
        "lookback_return_sessions": LOOKBACK_RETURN_SESSIONS,
        "price_threshold_usd": PRICE_THRESHOLD,
        "selection_count": SELECTION_COUNT,
        "stock_return_threshold": STOCK_RETURN_THRESHOLD,
        "market_filter": "none",
    }:
        _fail("laggard_nonoverlap_protocol_drift", "signal contract drifted")
    if receipt.get("execution") != {
        "entry": "next_session_adjusted_open",
        "exit": "session_{holding_sessions}_adjusted_close",
        "overlap_policy": "ignore_signals_until_exit_then_resume",
        "cost_allocation": "10_bps_entry_plus_10_bps_exit",
    }:
        _fail("laggard_nonoverlap_protocol_drift", "execution contract drifted")
    if receipt.get("baselines") != {
        "event_schedule": ["eligible_pool", "complete_cohort", "SPY", "QQQ"],
        "passive": ["SPY", "QQQ"],
    }:
        _fail("laggard_nonoverlap_protocol_drift", "baseline contract drifted")
    if receipt.get("gate_names") != [
        "at_least_30_accepted_events",
        "final_equity_above_start",
        "cagr_above_event_schedule_eligible_pool",
        "cagr_above_passive_SPY",
        "cagr_above_passive_QQQ",
        "max_drawdown_not_deeper_than_passive_SPY",
        "max_drawdown_not_deeper_than_passive_QQQ",
    ]:
        _fail("laggard_nonoverlap_protocol_drift", "gate contract drifted")
    return receipt


def _candidate_events(panel: Any, stocks: list[str]) -> list[dict[str, Any]]:
    close = panel.close[stocks]
    volume = panel.volume[stocks]
    dollar_volume = (close * volume).rolling(20, min_periods=20).median()
    stock_return = close.pct_change(LOOKBACK_RETURN_SESSIONS, fill_method=None)
    index = pd.DatetimeIndex(panel.close.index).normalize()
    index = index[(index >= pd.Timestamp(START)) & (index <= pd.Timestamp(END))]
    candidates: list[dict[str, Any]] = []
    for signal_date in index:
        position = index.get_loc(signal_date)
        if not isinstance(position, int) or position + HORIZON + 1 >= len(index):
            continue
        entry_date = index[position + 1]
        exit_date = index[position + 1 + HORIZON]
        base = (close.loc[signal_date] > PRICE_THRESHOLD) & (
            dollar_volume.loc[signal_date] >= DOLLAR_VOLUME_THRESHOLD
        )
        signal = base & (stock_return.loc[signal_date] <= STOCK_RETURN_THRESHOLD)
        selected = sorted(
            signal.index[signal],
            key=lambda symbol: (float(stock_return.loc[signal_date, symbol]), symbol),
        )[:SELECTION_COUNT]
        eligible = list(base.index[base])
        if len(selected) < SELECTION_COUNT or len(eligible) < SELECTION_COUNT:
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


def _series_metrics(
    series: pd.Series,
    *,
    final_equity: float,
    events: int,
    event_returns: list[float] | None = None,
) -> dict[str, Any]:
    daily_return = series.pct_change().replace([np.inf, -np.inf], np.nan).dropna()
    cagr = (final_equity / STARTING_CAPITAL_USD) ** (252 / len(series)) - 1.0
    drawdown = series / series.cummax() - 1.0
    return {
        "final_equity_usd": float(final_equity),
        "total_return": float(final_equity / STARTING_CAPITAL_USD - 1.0),
        "cagr": float(cagr),
        "max_drawdown": float(drawdown.min()),
        "daily_sharpe_zero_rate": float(
            daily_return.mean() / daily_return.std(ddof=1) * math.sqrt(252)
        )
        if len(daily_return) > 1 and daily_return.std(ddof=1) > 0
        else float("nan"),
        "events": int(events),
        "mean_event_return": (
            float(np.mean(event_returns))
            if event_returns
            else None
        ),
    }


def _simulate_schedule(
    panel: Any,
    index: pd.DatetimeIndex,
    events: list[dict[str, Any]],
    selector: Callable[[dict[str, Any]], list[str]],
) -> dict[str, Any]:
    equity = STARTING_CAPITAL_USD
    series = pd.Series(np.nan, index=index, dtype=float)
    series.iloc[0] = equity
    event_returns: list[float] = []
    busy_sessions = 0
    for event in events:
        tickers = selector(event)
        entry = event["entry_date"]
        exit_date = event["exit_date"]
        entry_position = index.get_loc(entry)
        exit_position = index.get_loc(exit_date)
        before = equity
        equity *= 1.0 - ROUND_TRIP_COST / 2.0
        equity *= float((panel.close.loc[entry, tickers] / panel.open.loc[entry, tickers]).mean())
        series.iloc[entry_position] = equity
        for position in range(entry_position + 1, exit_position + 1):
            day = index[position]
            previous = index[position - 1]
            equity *= float(
                (panel.close.loc[day, tickers] / panel.close.loc[previous, tickers]).mean()
            )
            series.iloc[position] = equity
        equity *= 1.0 - ROUND_TRIP_COST / 2.0
        series.iloc[exit_position] = equity
        event_returns.append(equity / before - 1.0)
        busy_sessions += exit_position - entry_position + 1
    series = series.ffill().fillna(STARTING_CAPITAL_USD)
    metrics = _series_metrics(
        series,
        final_equity=equity,
        events=len(events),
        event_returns=event_returns,
    )
    metrics.update(
        {
            "win_fraction": float(np.mean(np.asarray(event_returns) > 0.0))
            if event_returns
            else float("nan"),
            "utilization_fraction": float(busy_sessions / len(index)),
            "busy_sessions": int(busy_sessions),
        }
    )
    return metrics


def _simulate_passive(panel: Any, index: pd.DatetimeIndex, symbol: str) -> dict[str, Any]:
    equity = STARTING_CAPITAL_USD * (1.0 - ROUND_TRIP_COST / 2.0)
    first = index[0]
    equity *= float(panel.close.loc[first, symbol] / panel.open.loc[first, symbol])
    series = pd.Series(np.nan, index=index, dtype=float)
    series.iloc[0] = equity
    for position in range(1, len(index)):
        day = index[position]
        previous = index[position - 1]
        equity *= float(panel.close.loc[day, symbol] / panel.close.loc[previous, symbol])
        series.iloc[position] = equity
    equity *= 1.0 - ROUND_TRIP_COST / 2.0
    series.iloc[-1] = equity
    metrics = _series_metrics(series, final_equity=equity, events=1)
    metrics.update({"win_fraction": None, "utilization_fraction": 1.0, "busy_sessions": len(index)})
    return metrics


def audit_laggard_reversal_nonoverlap(
    *, repository_root: Path, snapshot_path: Path
) -> dict[str, Any]:
    root = repository_root.resolve()
    _load_protocol(root)
    snapshot = snapshot_path.resolve()
    if snapshot.name != SNAPSHOT_FILENAME or not snapshot.is_file() or snapshot.is_symlink():
        _fail("laggard_nonoverlap_snapshot_invalid", "snapshot path is not fixed")
    if _sha256_file(snapshot) != SNAPSHOT_ARCHIVE_SHA256:
        _fail("laggard_nonoverlap_snapshot_invalid", "snapshot archive hash drifted")
    panel, manifest = load_snapshot(snapshot)
    if (
        manifest.get("panel_sha256") != SNAPSHOT_PANEL_SHA256
        or panel_fingerprint(panel) != SNAPSHOT_PANEL_SHA256
    ):
        _fail("laggard_nonoverlap_snapshot_invalid", "snapshot panel hash drifted")
    if _sha256_file(root / WATCHLIST_PATH) != WATCHLIST_SHA256:
        _fail("laggard_nonoverlap_source_invalid", "watchlist hash drifted")
    records = load_stock_watchlist()
    stocks = [record.symbol for record in records if record.symbol in panel.close.columns]
    if len(records) != WATCHLIST_COUNT or len(stocks) != WATCHLIST_COUNT:
        _fail("laggard_nonoverlap_source_invalid", "watchlist coverage drifted")
    index = pd.DatetimeIndex(panel.close.index).normalize()
    index = index[(index >= pd.Timestamp(START)) & (index <= pd.Timestamp(END))]
    candidates = _candidate_events(panel, stocks)
    accepted = _accepted_events(candidates)
    if not accepted:
        _fail("laggard_nonoverlap_no_events", "no accepted events")
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
        "research_round": 60,
        "status": (
            "laggard_reversal_nonoverlap_capital_positive_survivorship_biased"
            if all(gates.values())
            else "laggard_reversal_nonoverlap_capital_negative_survivorship_biased"
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
            "frequency": "daily_completed_xnys",
            "market_filter": "none",
            "lookback_return_sessions": LOOKBACK_RETURN_SESSIONS,
            "stock_return_threshold": STOCK_RETURN_THRESHOLD,
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
