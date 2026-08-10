from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .data import load_snapshot, panel_fingerprint
from .metrics import newey_west_mean_test
from .short_term_market_stress_laggard_reversal import (
    DOLLAR_VOLUME_THRESHOLD,
    END,
    HORIZONS,
    LOOKBACK_RETURN_SESSIONS,
    PRICE_THRESHOLD,
    PRIMARY_HORIZON,
    SELECTION_COUNT,
    SNAPSHOT_ARCHIVE_SHA256,
    SNAPSHOT_FILENAME,
    SNAPSHOT_PANEL_SHA256,
    START,
    STOCK_RETURN_THRESHOLD,
    WATCHLIST_COUNT,
    WATCHLIST_PATH,
    WATCHLIST_SHA256,
    _canonical_sha256,
    _moving_block_bootstrap,
    _privacy_scan,
    _return_for_tickers,
    _sha256_file,
    _valid_complete_symbols,
)
from .universe import load_stock_watchlist

SCHEMA_VERSION = "usfddk.short_term_laggard_reversal_placebo.v1"
PROTOCOL_PATH = Path("docs/SHORT_TERM_LAGGARD_REVERSAL_PLACEBO_PROTOCOL.md")
PROTOCOL_RECEIPT_PATH = Path(
    "artifacts/short_term_laggard_reversal_placebo_protocol_receipt.json"
)
VALIDATION_PATH = Path(
    "artifacts/short_term_laggard_reversal_placebo_validation.json"
)
EXPECTED_PROTOCOL_SHA256 = (
    "a847183f970c68da6c9263a24ecfca0797650d50422ac921b1598744efa2fa14"
)
EXPECTED_PROTOCOL_RECEIPT_SHA256 = (
    "734b5a04e167de7a21e0790dfecffe3ad9827033b0b5928cc5300dd67e442900"
)
PLACEBO_MARKET_ASSET = "SPY"
PLACEBO_MARKET_THRESHOLD = 0.015
ROUND_TRIP_COST_BPS = 20.0
ROUND_TRIP_COST = ROUND_TRIP_COST_BPS / 10_000
BOOTSTRAP_SEED = 20_260_815
GLOBAL_TRIAL_PRIOR_LOWER_BOUND = 6305
GLOBAL_TRIAL_INCREMENT = 3
GLOBAL_TRIAL_FAMILY_ID = "round58_laggard_reversal_placebo_three_horizons"


class LaggardReversalPlaceboError(RuntimeError):
    def __init__(self, code: str, detail: str):
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}")


def _fail(code: str, detail: str) -> None:
    raise LaggardReversalPlaceboError(code, detail)


def _load_protocol(root: Path) -> dict[str, Any]:
    if _sha256_file(root / PROTOCOL_PATH) != EXPECTED_PROTOCOL_SHA256:
        _fail("laggard_placebo_protocol_drift", "protocol bytes drifted")
    try:
        receipt = json.loads((root / PROTOCOL_RECEIPT_PATH).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        _fail("laggard_placebo_protocol_drift", type(exc).__name__)
    if not isinstance(receipt, dict):
        _fail("laggard_placebo_protocol_drift", "receipt is not an object")
    claimed = receipt.get("receipt_sha256")
    unsigned = dict(receipt)
    unsigned.pop("receipt_sha256", None)
    if claimed != EXPECTED_PROTOCOL_RECEIPT_SHA256 or _canonical_sha256(unsigned) != claimed:
        _fail("laggard_placebo_protocol_drift", "receipt hash drifted")
    expected = {
        "schema_version": 1,
        "research_round": 58,
        "status": "preregistered_laggard_reversal_placebo_diagnostic_only",
        "research_role": "placebo_robustness_diagnostic",
        "independent_first_seen_evidence": False,
        "strategy_rule_changed": False,
        "protocol_sha256": EXPECTED_PROTOCOL_SHA256,
        "snapshot_filename": SNAPSHOT_FILENAME,
        "snapshot_archive_sha256": SNAPSHOT_ARCHIVE_SHA256,
        "snapshot_panel_sha256": SNAPSHOT_PANEL_SHA256,
        "watchlist_count": WATCHLIST_COUNT,
        "watchlist_sha256": WATCHLIST_SHA256,
        "period": {"start": START, "end": END},
        "horizons": list(HORIZONS),
        "primary_horizon_sessions": PRIMARY_HORIZON,
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
        _fail("laggard_placebo_protocol_drift", "fixed receipt field drifted")
    if receipt.get("placebo_control") != {
        "market_asset": PLACEBO_MARKET_ASSET,
        "market_condition": "SPY_daily_return >= +1.5%",
        "market_return_threshold": PLACEBO_MARKET_THRESHOLD,
        "control_for": "round57_market_stress_laggard_reversal",
    }:
        _fail("laggard_placebo_protocol_drift", "placebo control drifted")
    if receipt.get("signal") != {
        "frequency": "daily_completed_xnys",
        "dollar_volume_threshold_usd": DOLLAR_VOLUME_THRESHOLD,
        "lookback_return_sessions": LOOKBACK_RETURN_SESSIONS,
        "price_threshold_usd": PRICE_THRESHOLD,
        "selection_count": SELECTION_COUNT,
        "stock_return_threshold": STOCK_RETURN_THRESHOLD,
    }:
        _fail("laggard_placebo_protocol_drift", "signal contract drifted")
    return receipt


def _event_rows(panel: Any, stocks: list[str], horizon: int) -> list[dict[str, float]]:
    close = panel.close[stocks]
    volume = panel.volume[stocks]
    dollar_volume = (close * volume).rolling(20, min_periods=20).median()
    stock_return = close.pct_change(LOOKBACK_RETURN_SESSIONS, fill_method=None)
    market_return = panel.close[PLACEBO_MARKET_ASSET].pct_change(1, fill_method=None)
    index = pd.DatetimeIndex(panel.close.index).normalize()
    index = index[(index >= pd.Timestamp(START)) & (index <= pd.Timestamp(END))]
    rows: list[dict[str, float]] = []
    for signal_date in index:
        position = index.get_loc(signal_date)
        if not isinstance(position, int) or position + horizon + 1 >= len(index):
            continue
        if float(market_return.loc[signal_date]) < PLACEBO_MARKET_THRESHOLD:
            continue
        entry_date = index[position + 1]
        exit_date = index[position + 1 + horizon]
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
        if len(complete) < SELECTION_COUNT:
            continue
        row = {
            "selected_return": _return_for_tickers(
                panel, selected, entry_date=entry_date, exit_date=exit_date
            ),
            "eligible_pool_return": _return_for_tickers(
                panel, eligible, entry_date=entry_date, exit_date=exit_date
            ),
            "complete_cohort_return": _return_for_tickers(
                panel, complete, entry_date=entry_date, exit_date=exit_date
            ),
            "SPY_return": float(
                panel.close.loc[exit_date, PLACEBO_MARKET_ASSET]
                / panel.open.loc[entry_date, PLACEBO_MARKET_ASSET]
                - 1.0
                - ROUND_TRIP_COST
            ),
            "QQQ_return": float(
                panel.close.loc[exit_date, "QQQ"]
                / panel.open.loc[entry_date, "QQQ"]
                - 1.0
                - ROUND_TRIP_COST
            ),
            "year": int(pd.Timestamp(signal_date).year),
            "selected_count": float(len(selected)),
            "eligible_count": float(len(eligible)),
            "complete_count": float(len(complete)),
        }
        if all(np.isfinite(value) for key, value in row.items() if key != "year"):
            rows.append(row)
    return rows


def _summarize_horizon(rows: list[dict[str, float]], horizon: int) -> dict[str, Any]:
    frame = pd.DataFrame(rows)
    selected = frame["selected_return"]
    eligible = frame["eligible_pool_return"]
    complete = frame["complete_cohort_return"]
    difference = selected - eligible
    halves: dict[str, dict[str, float | int]] = {}
    for label, mask in (("first", frame["year"] <= 2016), ("second", frame["year"] >= 2017)):
        sample = difference.loc[mask]
        halves[label] = {
            "events": int(len(sample)),
            "mean_difference": float(sample.mean()) if len(sample) else float("nan"),
            "win_fraction": float((sample > 0).mean()) if len(sample) else float("nan"),
        }
    return {
        "holding_sessions": horizon,
        "events": int(len(frame)),
        "selected_mean": float(selected.mean()),
        "eligible_pool_mean": float(eligible.mean()),
        "complete_cohort_mean": float(complete.mean()),
        "SPY_mean": float(frame["SPY_return"].mean()),
        "QQQ_mean": float(frame["QQQ_return"].mean()),
        "mean_difference_vs_eligible_pool": float(difference.mean()),
        "mean_difference_vs_complete_cohort": float((selected - complete).mean()),
        "median_difference_vs_eligible_pool": float(difference.median()),
        "win_fraction_vs_eligible_pool": float((difference > 0.0).mean()),
        "newey_west_vs_eligible_pool": newey_west_mean_test(
            difference, max_lag=int(math.ceil(horizon / 5)), periods_per_year=252 / horizon
        ),
        "moving_block_bootstrap_vs_eligible_pool": _moving_block_bootstrap(
            difference, seed=BOOTSTRAP_SEED
        ),
        "fixed_halves_vs_eligible_pool": halves,
        "mean_selected_count": float(frame["selected_count"].mean()),
        "mean_eligible_count": float(frame["eligible_count"].mean()),
        "mean_complete_count": float(frame["complete_count"].mean()),
    }


def audit_laggard_reversal_placebo(
    *, repository_root: Path, snapshot_path: Path
) -> dict[str, Any]:
    root = repository_root.resolve()
    _load_protocol(root)
    snapshot = snapshot_path.resolve()
    if snapshot.name != SNAPSHOT_FILENAME or not snapshot.is_file() or snapshot.is_symlink():
        _fail("laggard_placebo_snapshot_invalid", "snapshot path is not fixed")
    if _sha256_file(snapshot) != SNAPSHOT_ARCHIVE_SHA256:
        _fail("laggard_placebo_snapshot_invalid", "snapshot archive hash drifted")
    panel, manifest = load_snapshot(snapshot)
    if (
        manifest.get("panel_sha256") != SNAPSHOT_PANEL_SHA256
        or panel_fingerprint(panel) != SNAPSHOT_PANEL_SHA256
    ):
        _fail("laggard_placebo_snapshot_invalid", "snapshot panel hash drifted")
    if _sha256_file(root / WATCHLIST_PATH) != WATCHLIST_SHA256:
        _fail("laggard_placebo_source_invalid", "watchlist hash drifted")
    records = load_stock_watchlist()
    stocks = [record.symbol for record in records if record.symbol in panel.close.columns]
    if len(records) != WATCHLIST_COUNT or len(stocks) != WATCHLIST_COUNT:
        _fail("laggard_placebo_source_invalid", "watchlist coverage drifted")
    horizons: dict[str, Any] = {}
    complete_counts: dict[str, int] = {}
    for horizon in HORIZONS:
        rows = _event_rows(panel, stocks, horizon)
        if not rows:
            _fail("laggard_placebo_no_events", f"horizon {horizon} produced no events")
        horizons[str(horizon)] = _summarize_horizon(rows, horizon)
        complete_counts[str(horizon)] = len(rows)
    primary = horizons[str(PRIMARY_HORIZON)]
    halves = primary["fixed_halves_vs_eligible_pool"]
    gates = {
        "at_least_30_complete_events": primary["events"] >= 30,
        "mean_difference_positive": primary["mean_difference_vs_eligible_pool"] > 0.0,
        "newey_west_t_at_least_1_96": primary["newey_west_vs_eligible_pool"].get(
            "t_stat", 0.0
        )
        >= 1.96,
        "bootstrap_low_positive": primary[
            "moving_block_bootstrap_vs_eligible_pool"
        ].get("low", float("nan"))
        > 0.0,
        "win_fraction_over_50_percent": primary["win_fraction_vs_eligible_pool"] > 0.50,
        "both_fixed_halves_positive": (
            halves["first"].get("mean_difference", float("nan")) > 0.0
            and halves["second"].get("mean_difference", float("nan")) > 0.0
        ),
    }
    result: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "research_round": 58,
        "status": (
            "laggard_reversal_placebo_positive_survivorship_biased_control"
            if all(gates.values())
            else "laggard_reversal_placebo_negative_survivorship_biased_control"
        ),
        "research_role": "placebo_robustness_diagnostic",
        "independent_first_seen_evidence": False,
        "strategy_rule_changed": False,
        "placebo_control": {
            "market_asset": PLACEBO_MARKET_ASSET,
            "market_condition": "SPY_daily_return >= +1.5%",
            "market_return_threshold": PLACEBO_MARKET_THRESHOLD,
            "control_for": "round57_market_stress_laggard_reversal",
        },
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
            "market_asset": PLACEBO_MARKET_ASSET,
            "market_return_threshold": PLACEBO_MARKET_THRESHOLD,
            "lookback_return_sessions": LOOKBACK_RETURN_SESSIONS,
            "stock_return_threshold": STOCK_RETURN_THRESHOLD,
            "selection_count": SELECTION_COUNT,
            "round_trip_cost_bps": ROUND_TRIP_COST_BPS,
        },
        "horizons": horizons,
        "complete_event_counts": complete_counts,
        "gate_summary": {
            "primary_horizon_sessions": PRIMARY_HORIZON,
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
            "post_round57_control_is_not_independent_first_seen_evidence",
            "adjusted_ohlcv_is_not_raw_execution_or_complete_total_return_ledger",
            "market_condition_and_return_have_no_intraday_public_timestamp",
            "daily_events_can_overlap",
            "no_strategy_or_paper_authorization",
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
