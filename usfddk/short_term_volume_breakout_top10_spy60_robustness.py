from __future__ import annotations

import json
import math
from collections.abc import Callable
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .data import load_snapshot, panel_fingerprint
from .short_term_laggard_reversal_nonoverlap import (
    _canonical_sha256,
    _privacy_scan,
    _sha256_file,
)
from .short_term_volume_breakout_diagnostic import (
    END,
    SNAPSHOT_ARCHIVE_SHA256,
    SNAPSHOT_FILENAME,
    SNAPSHOT_PANEL_SHA256,
    START,
    WATCHLIST_COUNT,
    WATCHLIST_PATH,
    WATCHLIST_SHA256,
)
from .short_term_volume_breakout_top10_spy60 import (
    _accepted_events,
    _regime_filtered_events,
)
from .universe import load_stock_watchlist

SCHEMA_VERSION = "usfddk.short_term_volume_breakout_top10_spy60_robustness.v1"
PROTOCOL_PATH = Path(
    "docs/SHORT_TERM_VOLUME_BREAKOUT_TOP10_SPY60_ROBUSTNESS_PROTOCOL.md"
)
PROTOCOL_RECEIPT_PATH = Path(
    "artifacts/short_term_volume_breakout_top10_spy60_robustness_protocol_receipt.json"
)
VALIDATION_PATH = Path(
    "artifacts/short_term_volume_breakout_top10_spy60_robustness_validation.json"
)
EXPECTED_PROTOCOL_SHA256 = (
    "4822b3ebfaf5eeea899cc482938c00e8f15caee07a8c0861feb5a10928013ed4"
)
EXPECTED_PROTOCOL_RECEIPT_SHA256 = (
    "0c1a88110519fcbbb5ce71feb9ce66a15818be1dfb280fa5b9558034fbb85ead"
)
PREDECESSOR_PROTOCOL_SHA256 = (
    "dc5ef0d794677a0845250fc2c74001f975f5ba493dca170a4cd872127350de5f"
)
PREDECESSOR_PROTOCOL_RECEIPT_SHA256 = (
    "acae6bfa93dacb38734a04a2010c0053e28e6924cb9b5f81d3819953b53e7f95"
)
PREDECESSOR_VALIDATION_SHA256 = (
    "3e6f71ecb3b2deddc4309fd0621900f6da837e327852960c1a5e94ee63111588"
)
STARTING_CAPITAL_USD = 1_000.0
HORIZON = 20
COSTS_BPS = (20.0, 50.0)
HALF_PERIODS = {
    "first_half": {"start": "2006-08-01", "end": "2016-07-31"},
    "second_half": {"start": "2016-08-01", "end": "2026-07-31"},
}
GLOBAL_TRIAL_PRIOR_LOWER_BOUND = 6315
GLOBAL_TRIAL_INCREMENT = 1
GLOBAL_TRIAL_FAMILY_ID = "round64_volume_breakout_top10_spy60_robustness"


class VolumeBreakoutRobustnessError(RuntimeError):
    def __init__(self, code: str, detail: str):
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}")


def _fail(code: str, detail: str) -> None:
    raise VolumeBreakoutRobustnessError(code, detail)


def _load_protocol(root: Path) -> dict[str, Any]:
    if _sha256_file(root / PROTOCOL_PATH) != EXPECTED_PROTOCOL_SHA256:
        _fail("volume_robustness_protocol_drift", "protocol bytes drifted")
    try:
        receipt = json.loads((root / PROTOCOL_RECEIPT_PATH).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        _fail("volume_robustness_protocol_drift", type(exc).__name__)
    if not isinstance(receipt, dict):
        _fail("volume_robustness_protocol_drift", "receipt is not an object")
    claimed = receipt.get("receipt_sha256")
    unsigned = dict(receipt)
    unsigned.pop("receipt_sha256", None)
    if claimed != EXPECTED_PROTOCOL_RECEIPT_SHA256 or _canonical_sha256(unsigned) != claimed:
        _fail("volume_robustness_protocol_drift", "receipt hash drifted")
    expected = {
        "schema_version": 1,
        "research_round": 64,
        "status": "posthoc_volume_breakout_top10_spy60_robustness_diagnostic_only",
        "research_role": "robustness_stress_diagnostic",
        "independent_first_seen_evidence": False,
        "strategy_rule_changed": False,
        "protocol_sha256": EXPECTED_PROTOCOL_SHA256,
        "predecessor_protocol_sha256": PREDECESSOR_PROTOCOL_SHA256,
        "predecessor_protocol_receipt_sha256": PREDECESSOR_PROTOCOL_RECEIPT_SHA256,
        "predecessor_validation_sha256": PREDECESSOR_VALIDATION_SHA256,
        "snapshot_filename": SNAPSHOT_FILENAME,
        "snapshot_archive_sha256": SNAPSHOT_ARCHIVE_SHA256,
        "snapshot_panel_sha256": SNAPSHOT_PANEL_SHA256,
        "watchlist_count": WATCHLIST_COUNT,
        "watchlist_sha256": WATCHLIST_SHA256,
        "period": {"start": START, "end": END},
        "frequency": "weekly_completed_xnys",
        "holding_sessions": HORIZON,
        "selection_count": 10,
        "market_filter": "SPY_close_above_60_session_SMA",
        "costs_round_trip_bps": list(COSTS_BPS),
        "half_periods": HALF_PERIODS,
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
        _fail("volume_robustness_protocol_drift", "fixed receipt field drifted")
    if receipt.get("gate_names") != [
        "full_period_20bps_capital_gates_preserved",
        "full_period_50bps_cagr_above_passive_QQQ",
        "first_half_20bps_cagr_above_passive_QQQ",
        "second_half_20bps_cagr_above_passive_QQQ",
        "first_half_50bps_cagr_above_passive_QQQ",
        "second_half_50bps_cagr_above_passive_QQQ",
    ]:
        _fail("volume_robustness_protocol_drift", "gate contract drifted")
    return receipt


def _metrics(
    series: pd.Series,
    *,
    final_equity: float,
    events: int,
    event_returns: list[float] | None = None,
    utilization: float | None = None,
) -> dict[str, Any]:
    daily = series.pct_change().replace([np.inf, -np.inf], np.nan).dropna()
    drawdown = series / series.cummax() - 1.0
    cagr = (final_equity / STARTING_CAPITAL_USD) ** (252 / len(series)) - 1.0
    return {
        "final_equity_usd": float(final_equity),
        "total_return": float(final_equity / STARTING_CAPITAL_USD - 1.0),
        "cagr": float(cagr),
        "max_drawdown": float(drawdown.min()),
        "daily_sharpe_zero_rate": float(
            daily.mean() / daily.std(ddof=1) * math.sqrt(252)
        )
        if len(daily) > 1 and daily.std(ddof=1) > 0
        else float("nan"),
        "events": int(events),
        "mean_event_return": float(np.mean(event_returns)) if event_returns else None,
        "win_fraction": (
            float(np.mean(np.asarray(event_returns) > 0.0)) if event_returns else None
        ),
        "utilization_fraction": utilization,
    }


def _simulate_schedule_cost(
    panel: Any,
    index: pd.DatetimeIndex,
    events: list[dict[str, Any]],
    selector: Callable[[dict[str, Any]], list[str]],
    cost_bps: float,
) -> dict[str, Any]:
    equity = STARTING_CAPITAL_USD
    series = pd.Series(np.nan, index=index, dtype=float)
    series.iloc[0] = equity
    event_returns: list[float] = []
    busy_sessions = 0
    leg_cost = cost_bps / 10_000.0 / 2.0
    for event in events:
        tickers = selector(event)
        entry_position = index.get_loc(event["entry_date"])
        exit_position = index.get_loc(event["exit_date"])
        before = equity
        equity *= 1.0 - leg_cost
        equity *= float(
            (panel.close.loc[event["entry_date"], tickers] / panel.open.loc[event["entry_date"], tickers]).mean()
        )
        series.iloc[entry_position] = equity
        for position in range(entry_position + 1, exit_position + 1):
            equity *= float(
                (
                    panel.close.loc[index[position], tickers]
                    / panel.close.loc[index[position - 1], tickers]
                ).mean()
            )
            series.iloc[position] = equity
        equity *= 1.0 - leg_cost
        series.iloc[exit_position] = equity
        event_returns.append(equity / before - 1.0)
        busy_sessions += exit_position - entry_position + 1
    series = series.ffill().fillna(STARTING_CAPITAL_USD)
    return _metrics(
        series,
        final_equity=equity,
        events=len(events),
        event_returns=event_returns,
        utilization=float(busy_sessions / len(index)),
    )


def _simulate_passive_cost(
    panel: Any, index: pd.DatetimeIndex, symbol: str, cost_bps: float
) -> dict[str, Any]:
    leg_cost = cost_bps / 10_000.0 / 2.0
    equity = STARTING_CAPITAL_USD * (1.0 - leg_cost)
    series = pd.Series(np.nan, index=index, dtype=float)
    series.iloc[0] = equity
    equity *= float(panel.close.loc[index[0], symbol] / panel.open.loc[index[0], symbol])
    series.iloc[0] = equity
    for position in range(1, len(index)):
        equity *= float(
            panel.close.loc[index[position], symbol] / panel.close.loc[index[position - 1], symbol]
        )
        series.iloc[position] = equity
    equity *= 1.0 - leg_cost
    series.iloc[-1] = equity
    return _metrics(series, final_equity=equity, events=1, utilization=1.0)


def _period_metrics(
    panel: Any,
    index: pd.DatetimeIndex,
    events: list[dict[str, Any]],
    *,
    start: str,
    end: str,
) -> dict[str, Any]:
    period_index = index[(index >= pd.Timestamp(start)) & (index <= pd.Timestamp(end))]
    period_events = [
        event
        for event in events
        if event["entry_date"] >= period_index[0] and event["exit_date"] <= period_index[-1]
    ]
    result: dict[str, Any] = {
        "period": {"start": start, "end": end},
        "sessions": len(period_index),
        "accepted_events": len(period_events),
    }
    for bps in COSTS_BPS:
        label = f"{int(bps)}_bps"
        result[label] = {
            "selected": _simulate_schedule_cost(
                panel, period_index, period_events, lambda event: event["selected"], bps
            ),
            "passive_QQQ": _simulate_passive_cost(panel, period_index, "QQQ", bps),
            "passive_SPY": _simulate_passive_cost(panel, period_index, "SPY", bps),
        }
    return result


def audit_volume_breakout_robustness(
    *, repository_root: Path, snapshot_path: Path
) -> dict[str, Any]:
    root = repository_root.resolve()
    _load_protocol(root)
    snapshot = snapshot_path.resolve()
    if snapshot.name != SNAPSHOT_FILENAME or not snapshot.is_file() or snapshot.is_symlink():
        _fail("volume_robustness_snapshot_invalid", "snapshot path is not fixed")
    if _sha256_file(snapshot) != SNAPSHOT_ARCHIVE_SHA256:
        _fail("volume_robustness_snapshot_invalid", "snapshot archive hash drifted")
    panel, manifest = load_snapshot(snapshot)
    if (
        manifest.get("panel_sha256") != SNAPSHOT_PANEL_SHA256
        or panel_fingerprint(panel) != SNAPSHOT_PANEL_SHA256
    ):
        _fail("volume_robustness_snapshot_invalid", "snapshot panel hash drifted")
    if _sha256_file(root / WATCHLIST_PATH) != WATCHLIST_SHA256:
        _fail("volume_robustness_source_invalid", "watchlist hash drifted")
    records = load_stock_watchlist()
    stocks = [record.symbol for record in records if record.symbol in panel.close.columns]
    if len(records) != WATCHLIST_COUNT or len(stocks) != WATCHLIST_COUNT:
        _fail("volume_robustness_source_invalid", "watchlist coverage drifted")
    index = pd.DatetimeIndex(panel.close.index).normalize()
    index = index[(index >= pd.Timestamp(START)) & (index <= pd.Timestamp(END))]
    candidates = _regime_filtered_events(panel, stocks)
    accepted = _accepted_events(candidates)
    if len(accepted) != 132:
        _fail("volume_robustness_schedule_drift", "accepted event schedule drifted")
    full: dict[str, Any] = {
        "sessions": len(index),
        "candidate_events": len(candidates),
        "accepted_events": len(accepted),
    }
    for bps in COSTS_BPS:
        label = f"{int(bps)}_bps"
        full[label] = {
            "selected": _simulate_schedule_cost(
                panel, index, accepted, lambda event: event["selected"], bps
            ),
            "eligible_pool": _simulate_schedule_cost(
                panel, index, accepted, lambda event: event["eligible"], bps
            ),
            "complete_cohort": _simulate_schedule_cost(
                panel, index, accepted, lambda event: event["complete"], bps
            ),
            "SPY": _simulate_schedule_cost(
                panel, index, accepted, lambda event: ["SPY"], bps
            ),
            "QQQ": _simulate_schedule_cost(
                panel, index, accepted, lambda event: ["QQQ"], bps
            ),
            "passive_SPY": _simulate_passive_cost(panel, index, "SPY", bps),
            "passive_QQQ": _simulate_passive_cost(panel, index, "QQQ", bps),
        }
    halves = {
        name: _period_metrics(panel, index, accepted, **period)
        for name, period in HALF_PERIODS.items()
    }
    full20 = full["20_bps"]
    selected = full20["selected"]
    capital_gates = {
        "at_least_30_accepted_events": selected["events"] >= 30,
        "final_equity_above_start": selected["final_equity_usd"] > STARTING_CAPITAL_USD,
        "cagr_above_event_schedule_eligible_pool": selected["cagr"]
        > full20["eligible_pool"]["cagr"],
        "cagr_above_passive_SPY": selected["cagr"] > full20["passive_SPY"]["cagr"],
        "cagr_above_passive_QQQ": selected["cagr"] > full20["passive_QQQ"]["cagr"],
        "max_drawdown_not_deeper_than_passive_SPY": selected["max_drawdown"]
        >= full20["passive_SPY"]["max_drawdown"],
        "max_drawdown_not_deeper_than_passive_QQQ": selected["max_drawdown"]
        >= full20["passive_QQQ"]["max_drawdown"],
    }
    robustness_gates = {
        "full_period_20bps_capital_gates_preserved": all(capital_gates.values()),
        "full_period_50bps_cagr_above_passive_QQQ": full["50_bps"]["selected"]["cagr"]
        > full["50_bps"]["passive_QQQ"]["cagr"],
        "first_half_20bps_cagr_above_passive_QQQ": halves["first_half"]["20_bps"][
            "selected"
        ]["cagr"]
        > halves["first_half"]["20_bps"]["passive_QQQ"]["cagr"],
        "second_half_20bps_cagr_above_passive_QQQ": halves["second_half"]["20_bps"][
            "selected"
        ]["cagr"]
        > halves["second_half"]["20_bps"]["passive_QQQ"]["cagr"],
        "first_half_50bps_cagr_above_passive_QQQ": halves["first_half"]["50_bps"][
            "selected"
        ]["cagr"]
        > halves["first_half"]["50_bps"]["passive_QQQ"]["cagr"],
        "second_half_50bps_cagr_above_passive_QQQ": halves["second_half"]["50_bps"][
            "selected"
        ]["cagr"]
        > halves["second_half"]["50_bps"]["passive_QQQ"]["cagr"],
    }
    result: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "research_round": 64,
        "status": (
            "volume_breakout_top10_spy60_robustness_positive_survivorship_biased"
            if all(robustness_gates.values())
            else "volume_breakout_top10_spy60_robustness_negative_survivorship_biased"
        ),
        "research_role": "robustness_stress_diagnostic",
        "independent_first_seen_evidence": False,
        "strategy_rule_changed": False,
        "source": {
            "protocol_sha256": EXPECTED_PROTOCOL_SHA256,
            "predecessor_protocol_sha256": PREDECESSOR_PROTOCOL_SHA256,
            "predecessor_protocol_receipt_sha256": PREDECESSOR_PROTOCOL_RECEIPT_SHA256,
            "predecessor_validation_sha256": PREDECESSOR_VALIDATION_SHA256,
            "snapshot_filename": SNAPSHOT_FILENAME,
            "snapshot_archive_sha256": SNAPSHOT_ARCHIVE_SHA256,
            "snapshot_panel_sha256": SNAPSHOT_PANEL_SHA256,
            "watchlist_count": WATCHLIST_COUNT,
            "watchlist_sha256": WATCHLIST_SHA256,
            "period": {"start": START, "end": END},
        },
        "fixed_schedule": {
            "frequency": "weekly_completed_xnys",
            "market_filter": "SPY_close_above_60_session_SMA",
            "selection_count": 10,
            "holding_sessions": HORIZON,
            "overlap_policy": "ignore_signals_until_exit_then_resume",
            "candidate_events": len(candidates),
            "accepted_events": len(accepted),
            "ignored_overlapping_events": len(candidates) - len(accepted),
        },
        "full_period": full,
        "half_periods": halves,
        "capital_gate_summary": {
            "gates": capital_gates,
            "passed": int(sum(bool(value) for value in capital_gates.values())),
            "required": len(capital_gates),
        },
        "robustness_gate_summary": {
            "gates": robustness_gates,
            "passed": int(sum(bool(value) for value in robustness_gates.values())),
            "required": len(robustness_gates),
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
            "posthoc_robustness_diagnostic_is_not_independent_first_seen_evidence",
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
