from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .data import load_snapshot, panel_fingerprint
from .metrics import newey_west_mean_test
from .short_term_high_return import _completed_period_mask
from .universe import load_stock_watchlist

SCHEMA_VERSION = "usfddk.short_term_current_cohort_breakout.v1"
PROTOCOL_PATH = Path("docs/SHORT_TERM_CURRENT_COHORT_BREAKOUT_DIAGNOSTIC_PROTOCOL.md")
PROTOCOL_RECEIPT_PATH = Path(
    "artifacts/short_term_current_cohort_breakout_protocol_receipt.json"
)
VALIDATION_PATH = Path(
    "artifacts/short_term_current_cohort_breakout_validation.json"
)
EXPECTED_PROTOCOL_SHA256 = (
    "71eb8586b682e6add9d992d1c52e84c17a4265b6ab3c584f5be9c5b708559390"
)
EXPECTED_PROTOCOL_RECEIPT_SHA256 = (
    "83a3caede74cc73c551ccecb4bbe96538203d865df3871441f2b272e7f2e599f"
)

SNAPSHOT_FILENAME = "snapshot_20260731_6a7ca6b8.zip"
SNAPSHOT_ARCHIVE_SHA256 = (
    "d480fb82e712f06aabe0a98461e222344656b87022b8bda2cd7ccaa4c29ae88b"
)
SNAPSHOT_PANEL_SHA256 = (
    "6a7ca6b83b1570007424daa46b0ff4e8fb4a655d39298a0f4f6d74c3b7ea3a66"
)
WATCHLIST_PATH = Path("usfddk/resources/us_large_cap_watchlist_v1.csv")
WATCHLIST_SHA256 = (
    "b6002e4e151bd298884f8cdd6272b5cbfde8aedca47cb58b92830d4d92028014"
)
WATCHLIST_COUNT = 30
START = "2006-08-01"
END = "2026-07-31"
HORIZONS = (5, 10, 20)
PRIMARY_HORIZON = 10
ROUND_TRIP_COST_BPS = 20.0
BREAKOUT_SESSIONS = 60
MOMENTUM_SESSIONS = 20
TREND_SMA_SESSIONS = 50
VOLUME_MULTIPLE = 1.5
MARKET_VIX_CAP = 30.0
PRICE_THRESHOLD_USD = 5.0
DOLLAR_VOLUME_THRESHOLD_USD = 20_000_000.0
SELECTION_COUNT = 5
BOOTSTRAP_SAMPLES = 2_000
BOOTSTRAP_BLOCK_EVENTS = 8
BOOTSTRAP_SEED = 20_260_810
GLOBAL_TRIAL_PRIOR_LOWER_BOUND = 6_287
GLOBAL_TRIAL_INCREMENT = 3
GLOBAL_TRIAL_POST_RESULT_LOWER_BOUND = 6_290
GLOBAL_TRIAL_FAMILY_ID = "round51_current_cohort_breakout_three_horizons"


class CurrentCohortBreakoutError(RuntimeError):
    """Fail-closed current-cohort breakout diagnostic error."""

    def __init__(self, code: str, detail: str):
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}")


def _fail(code: str, detail: str) -> None:
    raise CurrentCohortBreakoutError(code, detail)


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_file(path: Path) -> str:
    try:
        return _sha256_bytes(path.read_bytes())
    except OSError as exc:
        _fail("breakout_source_missing", f"{path}: {type(exc).__name__}")


def _canonical_sha256(value: object) -> str:
    rendered = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return _sha256_bytes(rendered)


def _load_protocol(repository_root: Path) -> dict[str, Any]:
    root = repository_root.resolve()
    protocol_path = root / PROTOCOL_PATH
    receipt_path = root / PROTOCOL_RECEIPT_PATH
    if _sha256_file(protocol_path) != EXPECTED_PROTOCOL_SHA256:
        _fail("breakout_protocol_drift", "protocol bytes drifted")
    try:
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        _fail("breakout_protocol_drift", type(exc).__name__)
    if not isinstance(receipt, dict):
        _fail("breakout_protocol_drift", "protocol receipt is not an object")
    claimed = receipt.get("receipt_sha256")
    canonical = dict(receipt)
    canonical.pop("receipt_sha256", None)
    if claimed != EXPECTED_PROTOCOL_RECEIPT_SHA256 or _canonical_sha256(canonical) != claimed:
        _fail("breakout_protocol_drift", "protocol receipt self-hash drifted")
    expected = {
        "schema_version": 1,
        "status": "preregistered_unrun_current_cohort_breakout_diagnostic",
        "research_round": 51,
        "snapshot_filename": SNAPSHOT_FILENAME,
        "snapshot_archive_sha256": SNAPSHOT_ARCHIVE_SHA256,
        "snapshot_panel_sha256": SNAPSHOT_PANEL_SHA256,
        "watchlist_count": WATCHLIST_COUNT,
        "watchlist_sha256": WATCHLIST_SHA256,
        "period": {"start": START, "end": END},
        "horizons": list(HORIZONS),
        "cost_round_trip_bps": ROUND_TRIP_COST_BPS,
        "formal_backtest_authorized": False,
        "paper_authorized": False,
        "real_money_authorized": False,
        "today_action": "今天不下單",
        "signal": {
            "breakout_sessions": BREAKOUT_SESSIONS,
            "dollar_volume_threshold_usd": DOLLAR_VOLUME_THRESHOLD_USD,
            "market_vix_cap": MARKET_VIX_CAP,
            "momentum_sessions": MOMENTUM_SESSIONS,
            "price_threshold_usd": PRICE_THRESHOLD_USD,
            "selection_count": SELECTION_COUNT,
            "trend_sma_sessions": TREND_SMA_SESSIONS,
            "volume_multiple": VOLUME_MULTIPLE,
        },
    }
    if any(receipt.get(key) != value for key, value in expected.items()):
        _fail("breakout_protocol_drift", "fixed protocol fields drifted")
    ledger = receipt.get("global_trial_ledger")
    if not isinstance(ledger, dict) or ledger.get("current_lower_bound") != GLOBAL_TRIAL_PRIOR_LOWER_BOUND:
        _fail("breakout_multiplicity_binding_mismatch", "prior global lower bound drifted")
    if ledger.get("minimum_increment") != GLOBAL_TRIAL_INCREMENT or ledger.get("new_family_id") != GLOBAL_TRIAL_FAMILY_ID:
        _fail("breakout_multiplicity_binding_mismatch", "family reservation drifted")
    return receipt


def _moving_block_bootstrap_mean(
    series: pd.Series,
    *,
    samples: int = BOOTSTRAP_SAMPLES,
    block_size: int = BOOTSTRAP_BLOCK_EVENTS,
    seed: int = BOOTSTRAP_SEED,
) -> dict[str, float]:
    values = series.dropna().to_numpy(dtype=float)
    n = len(values)
    if n < block_size * 2:
        return {
            "low": float("nan"),
            "median": float("nan"),
            "high": float("nan"),
            "p_below_or_equal_zero": float("nan"),
        }
    rng = np.random.default_rng(seed)
    starts_max = n - block_size + 1
    blocks_needed = int(math.ceil(n / block_size))
    means = np.empty(samples, dtype=float)
    for index in range(samples):
        starts = rng.integers(0, starts_max, size=blocks_needed)
        resampled = np.concatenate(
            [values[start : start + block_size] for start in starts]
        )[:n]
        means[index] = float(resampled.mean())
    low, median, high = np.quantile(means, [0.025, 0.5, 0.975])
    return {
        "low": float(low),
        "median": float(median),
        "high": float(high),
        "p_below_or_equal_zero": float((means <= 0.0).mean()),
    }


def _fixed_horizon_return(
    panel: Any,
    tickers: list[str],
    *,
    entry_date: pd.Timestamp,
    exit_date: pd.Timestamp,
    cost: float,
) -> float:
    if not tickers:
        raise CurrentCohortBreakoutError(
            "breakout_event_empty", "event has no tradable tickers"
        )
    gross = panel.close.loc[exit_date, tickers].div(
        panel.open.loc[entry_date, tickers]
    ) - 1.0
    if gross.isna().any() or not np.isfinite(gross.to_numpy(dtype=float)).all():
        raise CurrentCohortBreakoutError(
            "breakout_execution_missing", "event has missing adjusted execution prices"
        )
    return float(gross.mean() - cost)


def _summary(events: pd.DataFrame, horizon: int) -> dict[str, Any]:
    if events.empty:
        _fail("breakout_no_events", f"horizon {horizon} produced no complete events")
    selected = events["top5_return"]
    eligible = events["eligible_equal_return"]
    differences = selected - eligible
    lag = int(math.ceil(horizon / 5))
    comparison = {
        "mean_difference": float(differences.mean()),
        "median_difference": float(differences.median()),
        "win_fraction": float((differences > 0.0).mean()),
        "newey_west": newey_west_mean_test(
            differences,
            max_lag=lag,
            periods_per_year=52,
        ),
    }
    signal_dates = pd.to_datetime(events["signal_date"])
    halves: dict[str, Any] = {}
    for label, mask in (
        ("first", signal_dates <= pd.Timestamp("2016-07-29")),
        ("second", signal_dates >= pd.Timestamp("2016-08-01")),
    ):
        sample = differences.loc[mask.to_numpy()]
        halves[label] = {
            "events": int(len(sample)),
            "mean_difference": float(sample.mean()) if len(sample) else float("nan"),
            "median_difference": float(sample.median()) if len(sample) else float("nan"),
            "win_fraction": float((sample > 0.0).mean()) if len(sample) else 0.0,
        }
    bootstrap = _moving_block_bootstrap_mean(differences)
    return {
        "holding_sessions": horizon,
        "events": int(len(events)),
        "first_signal_date": str(events.iloc[0]["signal_date"]),
        "last_signal_date": str(events.iloc[-1]["signal_date"]),
        "mean_eligible_count": float(events["eligible_count"].mean()),
        "mean_selected_return": float(selected.mean()),
        "mean_eligible_equal_return": float(eligible.mean()),
        "mean_complete_cohort_equal_return": float(
            events["complete_cohort_equal_return"].mean()
        ),
        "mean_qqq_return": float(events["qqq_return"].mean()),
        "mean_spy_return": float(events["spy_return"].mean()),
        "comparison_vs_eligible_equal": comparison,
        "fixed_halves_vs_eligible_equal": halves,
        "moving_block_bootstrap_mean_difference_vs_eligible_equal": bootstrap,
        "event_series": events.to_dict(orient="records"),
    }


def _audit_sources(
    *,
    repository_root: Path,
    snapshot_path: Path,
) -> tuple[Any, dict[str, Any], list[str], list[str]]:
    _load_protocol(repository_root)
    root = repository_root.resolve()
    snapshot = snapshot_path.resolve()
    if snapshot.name != SNAPSHOT_FILENAME or not snapshot.is_file() or snapshot.is_symlink():
        _fail("breakout_source_mismatch", "snapshot path is not fixed")
    if _sha256_file(snapshot) != SNAPSHOT_ARCHIVE_SHA256:
        _fail("breakout_source_mismatch", "snapshot archive hash drifted")
    panel, manifest = load_snapshot(snapshot)
    if panel_fingerprint(panel) != SNAPSHOT_PANEL_SHA256 or manifest.get("panel_sha256") != SNAPSHOT_PANEL_SHA256:
        _fail("breakout_source_mismatch", "snapshot panel hash drifted")
    if manifest.get("provider_metadata", {}).get("adjustment") != (
        "adjusted_ohlc = raw_ohlc * (adj_close / raw_close)"
    ):
        _fail("breakout_execution_boundary", "raw OHLCV contract is absent")
    if panel.end.strftime("%Y-%m-%d") != END:
        _fail("breakout_source_mismatch", "snapshot end drifted")
    watchlist_path = root / WATCHLIST_PATH
    if _sha256_file(watchlist_path) != WATCHLIST_SHA256:
        _fail("breakout_source_mismatch", "watchlist hash drifted")
    records = load_stock_watchlist()
    symbols = [record.symbol for record in records]
    if len(symbols) != WATCHLIST_COUNT or len(set(symbols)) != WATCHLIST_COUNT:
        _fail("breakout_universe_mismatch", "watchlist count or uniqueness drifted")
    missing = sorted(set(symbols) - set(panel.close.columns))
    if missing:
        _fail("breakout_universe_mismatch", "watchlist symbol is absent from snapshot")
    for required in ("QQQ", "SPY", "^VIX"):
        if required not in panel.close.columns:
            _fail("breakout_source_mismatch", f"required benchmark missing: {required}")
    complete_symbols = [
        symbol
        for symbol in symbols
        if panel.close.loc[:START, symbol].notna().any()
        and bool(panel.close.loc[START:END, symbol].notna().all())
    ]
    if len(complete_symbols) < 20:
        _fail("breakout_universe_mismatch", "complete current cohort is below 20")
    return panel, manifest, symbols, complete_symbols


def run_breakout_diagnostic(
    panel: Any,
    *,
    complete_symbols: list[str],
) -> dict[str, Any]:
    """Run the frozen breakout event diagnostic; never produces a trade target."""
    close = panel.close[complete_symbols]
    volume = panel.volume[complete_symbols]
    breakout_high = close.shift(1).rolling(BREAKOUT_SESSIONS, min_periods=BREAKOUT_SESSIONS).max()
    momentum = close.pct_change(MOMENTUM_SESSIONS, fill_method=None)
    trend = close > close.rolling(TREND_SMA_SESSIONS, min_periods=TREND_SMA_SESSIONS).mean()
    prior_volume_median = volume.shift(1).rolling(20, min_periods=20).median()
    prior_dollar_volume_median = (
        (close * volume).shift(1).rolling(20, min_periods=20).median()
    )
    spy = panel.close["SPY"]
    spy_trend = spy > spy.rolling(200, min_periods=200).mean()
    vix = panel.close["^VIX"]
    weekly = _completed_period_mask(close.index, "weekly")
    signal_dates = close.index[
        weekly.to_numpy()
        & (close.index >= pd.Timestamp(START))
        & (close.index <= pd.Timestamp(END))
    ]
    rows: dict[int, list[dict[str, Any]]] = {horizon: [] for horizon in HORIZONS}
    skipped = {"no_signal": 0, "missing_execution": {str(h): 0 for h in HORIZONS}}
    cost = ROUND_TRIP_COST_BPS / 10_000.0
    for signal_date in signal_dates:
        position = close.index.get_loc(signal_date)
        if not isinstance(position, int) or position + 1 >= len(close.index):
            continue
        eligible_mask = (
            breakout_high.loc[signal_date].notna()
            & (close.loc[signal_date] > breakout_high.loc[signal_date])
            & (momentum.loc[signal_date] > 0.0)
            & trend.loc[signal_date]
            & (volume.loc[signal_date] >= prior_volume_median.loc[signal_date] * VOLUME_MULTIPLE)
            & (close.loc[signal_date] > PRICE_THRESHOLD_USD)
            & (prior_dollar_volume_median.loc[signal_date] >= DOLLAR_VOLUME_THRESHOLD_USD)
        )
        market_ok = bool(
            pd.notna(spy_trend.loc[signal_date])
            and bool(spy_trend.loc[signal_date])
            and pd.notna(vix.loc[signal_date])
            and float(vix.loc[signal_date]) < MARKET_VIX_CAP
        )
        eligible = list(eligible_mask.index[eligible_mask]) if market_ok else []
        if len(eligible) < SELECTION_COUNT:
            skipped["no_signal"] += 1
            continue
        selected = sorted(
            eligible,
            key=lambda ticker: (-float(momentum.loc[signal_date, ticker]), ticker),
        )[:SELECTION_COUNT]
        entry_position = position + 1
        entry_date = close.index[entry_position]
        for horizon in HORIZONS:
            exit_position = entry_position + horizon - 1
            if exit_position >= len(close.index):
                skipped["missing_execution"][str(horizon)] += 1
                continue
            exit_date = close.index[exit_position]
            try:
                row = {
                    "signal_date": pd.Timestamp(signal_date).strftime("%Y-%m-%d"),
                    "entry_date": pd.Timestamp(entry_date).strftime("%Y-%m-%d"),
                    "exit_date": pd.Timestamp(exit_date).strftime("%Y-%m-%d"),
                    "eligible_count": int(len(eligible)),
                    "selected_count": SELECTION_COUNT,
                    "top5_return": _fixed_horizon_return(
                        panel,
                        selected,
                        entry_date=entry_date,
                        exit_date=exit_date,
                        cost=cost,
                    ),
                    "eligible_equal_return": _fixed_horizon_return(
                        panel,
                        eligible,
                        entry_date=entry_date,
                        exit_date=exit_date,
                        cost=cost,
                    ),
                    "complete_cohort_equal_return": _fixed_horizon_return(
                        panel,
                        complete_symbols,
                        entry_date=entry_date,
                        exit_date=exit_date,
                        cost=cost,
                    ),
                    "qqq_return": _fixed_horizon_return(
                        panel,
                        ["QQQ"],
                        entry_date=entry_date,
                        exit_date=exit_date,
                        cost=cost,
                    ),
                    "spy_return": _fixed_horizon_return(
                        panel,
                        ["SPY"],
                        entry_date=entry_date,
                        exit_date=exit_date,
                        cost=cost,
                    ),
                }
            except CurrentCohortBreakoutError:
                skipped["missing_execution"][str(horizon)] += 1
                continue
            rows[horizon].append(row)
    horizons = {
        str(horizon): _summary(pd.DataFrame(rows[horizon]), horizon)
        for horizon in HORIZONS
    }
    primary = horizons[str(PRIMARY_HORIZON)]
    comparison = primary["comparison_vs_eligible_equal"]
    bootstrap = primary["moving_block_bootstrap_mean_difference_vs_eligible_equal"]
    halves = primary["fixed_halves_vs_eligible_equal"]
    gates = {
        "mean_difference_positive": comparison["mean_difference"] > 0.0,
        "newey_west_t_at_least_1_96": comparison["newey_west"]["t_stat"] >= 1.96,
        "bootstrap_95pct_low_positive": bootstrap["low"] > 0.0,
        "both_fixed_halves_positive": all(
            value["mean_difference"] > 0.0 for value in halves.values()
        ),
        "paired_win_fraction_above_50pct": comparison["win_fraction"] > 0.50,
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "status": (
            "current_cohort_breakout_diagnostic_positive_survivorship_biased"
            if all(gates.values())
            else "current_cohort_breakout_diagnostic_negative_survivorship_biased"
        ),
        "valid_for_investment_decision": False,
        "survivorship_bias_warning": True,
        "adjusted_ohlcv_only": True,
        "period": {"start": START, "end": END},
        "complete_current_cohort_count": len(complete_symbols),
        "horizons": horizons,
        "skipped": skipped,
        "primary_horizon": PRIMARY_HORIZON,
        "primary_gates": gates,
        "passed_primary_gate_count": int(sum(bool(value) for value in gates.values())),
        "required_primary_gate_count": len(gates),
        "has_follow_up_research_value": all(gates.values()),
        "paper_effect": "none_current_cohort_diagnostic_only",
        "real_money_action_usd": 0,
        "today_action": "今天不下單",
    }


def audit_current_cohort_breakout(
    *,
    repository_root: Path,
    snapshot_path: Path,
) -> dict[str, Any]:
    panel, manifest, symbols, complete_symbols = _audit_sources(
        repository_root=repository_root,
        snapshot_path=snapshot_path,
    )
    diagnostic = run_breakout_diagnostic(panel, complete_symbols=complete_symbols)
    result: dict[str, Any] = {
        **diagnostic,
        "research_round": 51,
        "snapshot": {
            "filename": SNAPSHOT_FILENAME,
            "archive_sha256": SNAPSHOT_ARCHIVE_SHA256,
            "panel_sha256": SNAPSHOT_PANEL_SHA256,
            "archive_bytes": int(snapshot_path.stat().st_size),
            "rows": int(manifest.get("rows", 0)),
            "watchlist_count": WATCHLIST_COUNT,
            "watchlist_mapped_count": len(symbols),
            "complete_current_cohort_count": len(complete_symbols),
        },
        "data_boundary": {
            "point_in_time_membership": False,
            "delisted_and_acquired_returns": False,
            "historical_sector_classification": False,
            "raw_execution_ohlcv": False,
            "corporate_action_ledger": False,
            "formal_backtest_authorized": False,
            "paper_authorized": False,
            "real_money_action_usd": 0,
        },
        "global_trial_ledger_extension": {
            "base_ledger_path": "artifacts/short_term_global_trial_ledger.json",
            "base_ledger_sha256": "0240f3c36edca35a86c077a94116067a7d1560e4329968df33abbdcaffbb4b49",
            "prior_lower_bound": GLOBAL_TRIAL_PRIOR_LOWER_BOUND,
            "family_id": GLOBAL_TRIAL_FAMILY_ID,
            "minimum_increment": GLOBAL_TRIAL_INCREMENT,
            "post_result_lower_bound": GLOBAL_TRIAL_POST_RESULT_LOWER_BOUND,
            "result_seen": True,
            "result_state": "result_seen",
        },
    }
    result["receipt_sha256"] = _canonical_sha256(result)
    return result


def write_validation_receipt(
    result: dict[str, Any],
    *,
    repository_root: Path,
) -> Path:
    path = repository_root / VALIDATION_PATH
    path.write_text(
        json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    return path
