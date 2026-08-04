from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Callable
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .data import load_snapshot, panel_fingerprint
from .metrics import max_drawdown, newey_west_mean_test
from .short_term_high_return import SHORT_TERM_END, SHORT_TERM_START, _completed_period_mask
from .universe import load_stock_watchlist

SCHEMA_VERSION = 1
RESEARCH_ROUND = 29
PROTOCOL_PATH = "docs/SHORT_TERM_CALENDAR_CAPITAL_ACCOUNTING_PROTOCOL.md"
PROTOCOL_SHA256 = "020f99c561994cf59b5d196b17c20aaa3c2fc2bd925ac1711384fcbcfd378b25"
PROTOCOL_COMMIT = "65b3789fa7698ddd06639c334339a5c604c3a745"

ROUND28_RECEIPT_PATH = "artifacts/short_term_reversal_volatility_attribution_validation.json"
ROUND28_RECEIPT_SHA256 = "970801377fd981eebffa3aa970c2cc3c2ce958b453db678a068b953f363daef1"
ROUND27_RECEIPT_PATH = "artifacts/short_term_rank_monotonicity_placebo_validation.json"
ROUND27_RECEIPT_SHA256 = "3d362ed82ab8ed732d53344a1a8d787fe48374e042bdf8f13c54a0f0cea96448"
ROUND24_RECEIPT_PATH = "artifacts/short_term_baseline_multiplicity_validation.json"
ROUND24_RECEIPT_SHA256 = "4dc15a520606a03c85279bfaaca88367015bb651d0b6fbd77dffc9023cdbe282"
EVENT_RECEIPT_PATH = "artifacts/short_term_high_return_validation.json"
EVENT_RECEIPT_SHA256 = "fa2463cc8273a316e4a98428767b695eb85c74e9ac75c47b5ca34592102979e8"
SNAPSHOT_PATH = "artifacts/snapshot_20260731_6a7ca6b8.zip"
SNAPSHOT_SHA256 = "d480fb82e712f06aabe0a98461e222344656b87022b8bda2cd7ccaa4c29ae88b"
PANEL_SHA256 = "6a7ca6b83b1570007424daa46b0ff4e8fb4a655d39298a0f4f6d74c3b7ea3a66"
WATCHLIST_PATH = "usfddk/resources/us_large_cap_watchlist_v1.csv"
WATCHLIST_SHA256 = "b6002e4e151bd298884f8cdd6272b5cbfde8aedca47cb58b92830d4d92028014"

REFERENCE_COMMITS = (
    ("tst_wocker", "3372aa088328700feafeeb07c72ab832ea2d3ecb"),
    ("tw-block-warrant", "37463c54796ba36f4aac262519ea7fc2ef797de6"),
    ("tst_wocker_filter_lab", "06c87b7a1735877c9ccbab3a339c1742814a5058"),
)

EXPECTED_EVENTS = 905
EXPECTED_COHORT = 25
FIRST_SIGNAL_DATE = "2006-08-04"
FIRST_ENTRY_DATE = "2006-08-07"
LAST_SIGNAL_DATE = "2026-07-02"
LAST_EXIT_DATE = "2026-07-31"
MOMENTUM_SESSIONS = 20
TREND_SESSIONS = 60
TOP_K = 7
ENTRY_DELAY = 1
HOLDING_SESSIONS = 20
SLOT_COUNT = 5
EVENTS_PER_SLOT = 181
INITIAL_CAPITAL_USD = 1_000.0
PRIMARY_ROUND_TRIP_COST_BPS = 20
COST_STRESS_BPS = (50, 100)
ASSIGNMENT_SHA256 = "3be9948565e7c58e951a50110e6063185c8c93a12b1cf97c2014b981b25c5547"
RECONSTRUCTION_TOLERANCE = 1e-12

EVENT_PATH_IDS = (
    "top7_five_slot",
    "eligible_equal_five_slot",
    "complete_equal_five_slot",
    "qqq_event_five_slot",
)
BUY_HOLD_IDS = ("qqq_buy_hold", "spy_buy_hold", "shy_buy_hold")
PATH_IDS = (*EVENT_PATH_IDS, *BUY_HOLD_IDS)
FAMILY_BASELINE_IDS = (
    "eligible_equal_five_slot",
    "complete_equal_five_slot",
    "qqq_event_five_slot",
    "qqq_buy_hold",
    "spy_buy_hold",
    "shy_buy_hold",
)
PATH_LABELS = {
    "top7_five_slot": "Top-7 五槽",
    "eligible_equal_five_slot": "合資格池等權五槽",
    "complete_equal_five_slot": "完整現時股池等權五槽",
    "qqq_event_five_slot": "QQQ 事件配對五槽",
    "qqq_buy_hold": "QQQ 買入並持有",
    "spy_buy_hold": "SPY 買入並持有",
    "shy_buy_hold": "SHY 買入並持有",
}

HAC_LAG = 20
FAMILY_ALPHA = 0.05
BOOTSTRAP_BLOCK_SESSIONS = 63
BOOTSTRAP_PATHS = 20_000
BOOTSTRAP_SEED = 29_202_608
GLOBAL_SEARCH_TRIALS = 6_214
FIRST_HALF_END = pd.Timestamp("2016-07-29")
SECOND_HALF_START = pd.Timestamp("2016-08-01")
CRISIS_YEARS = (2008, 2020, 2022)
BEST_YEAR_REMOVAL_COUNT = 3


class CalendarCapitalAccountingError(ValueError):
    """Fail-closed Round 29 error with a stable semantic code."""

    def __init__(self, code: str, detail: str):
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}")


def _fail(code: str, detail: str) -> None:
    raise CalendarCapitalAccountingError(code, detail)


@dataclass(frozen=True)
class FrozenCalendarCapitalContract:
    protocol_sha256: str = PROTOCOL_SHA256
    protocol_commit: str = PROTOCOL_COMMIT
    round28_receipt_sha256: str = ROUND28_RECEIPT_SHA256
    round27_receipt_sha256: str = ROUND27_RECEIPT_SHA256
    round24_receipt_sha256: str = ROUND24_RECEIPT_SHA256
    event_receipt_sha256: str = EVENT_RECEIPT_SHA256
    snapshot_sha256: str = SNAPSHOT_SHA256
    panel_sha256: str = PANEL_SHA256
    watchlist_sha256: str = WATCHLIST_SHA256
    reference_commits: tuple[tuple[str, str], ...] = REFERENCE_COMMITS
    expected_events: int = EXPECTED_EVENTS
    expected_cohort: int = EXPECTED_COHORT
    momentum_sessions: int = MOMENTUM_SESSIONS
    trend_sessions: int = TREND_SESSIONS
    top_k: int = TOP_K
    entry_delay: int = ENTRY_DELAY
    holding_sessions: int = HOLDING_SESSIONS
    slot_count: int = SLOT_COUNT
    events_per_slot: int = EVENTS_PER_SLOT
    assignment_sha256: str = ASSIGNMENT_SHA256
    initial_capital_usd: float = INITIAL_CAPITAL_USD
    primary_round_trip_cost_bps: int = PRIMARY_ROUND_TRIP_COST_BPS
    cost_stress_bps: tuple[int, ...] = COST_STRESS_BPS
    path_ids: tuple[str, ...] = PATH_IDS
    family_baseline_ids: tuple[str, ...] = FAMILY_BASELINE_IDS
    shy_excess_proxy: bool = True
    hac_lag: int = HAC_LAG
    family_alpha: float = FAMILY_ALPHA
    bootstrap_block_sessions: int = BOOTSTRAP_BLOCK_SESSIONS
    bootstrap_paths: int = BOOTSTRAP_PATHS
    bootstrap_seed: int = BOOTSTRAP_SEED
    common_bootstrap_indices: bool = True
    centered_under_null: bool = True
    global_search_trials: int = GLOBAL_SEARCH_TRIALS
    first_half_end: str = FIRST_HALF_END.strftime("%Y-%m-%d")
    second_half_start: str = SECOND_HALF_START.strftime("%Y-%m-%d")
    crisis_years: tuple[int, ...] = CRISIS_YEARS
    best_year_removal_count: int = BEST_YEAR_REMOVAL_COUNT
    current_identifiers_only: bool = True
    paper_authorized: bool = False
    real_money_authorized: bool = False


FROZEN_CONTRACT = FrozenCalendarCapitalContract()


def validate_calendar_capital_contract(contract: FrozenCalendarCapitalContract) -> None:
    checks: tuple[tuple[bool, str, str], ...] = (
        (contract.protocol_sha256 == PROTOCOL_SHA256, "calendar_capital_protocol_hash_mismatch", "協議 SHA 漂移"),
        (contract.protocol_commit == PROTOCOL_COMMIT, "calendar_capital_protocol_commit_mismatch", "協議 commit 漂移"),
        (contract.round28_receipt_sha256 == ROUND28_RECEIPT_SHA256, "calendar_capital_round28_receipt_mismatch", "第 28 輪收據漂移"),
        (contract.round27_receipt_sha256 == ROUND27_RECEIPT_SHA256, "calendar_capital_round27_receipt_mismatch", "第 27 輪收據漂移"),
        (contract.round24_receipt_sha256 == ROUND24_RECEIPT_SHA256, "calendar_capital_round24_receipt_mismatch", "第 24 輪收據漂移"),
        (contract.event_receipt_sha256 == EVENT_RECEIPT_SHA256, "calendar_capital_event_receipt_mismatch", "原始事件收據漂移"),
        (contract.snapshot_sha256 == SNAPSHOT_SHA256 and contract.panel_sha256 == PANEL_SHA256, "calendar_capital_market_data_mismatch", "行情 archive 或 panel 漂移"),
        (contract.watchlist_sha256 == WATCHLIST_SHA256, "calendar_capital_watchlist_mismatch", "watchlist 漂移"),
        (contract.reference_commits == REFERENCE_COMMITS, "calendar_capital_reference_mismatch", "台股參考 commit 漂移"),
        (contract.expected_events == EXPECTED_EVENTS, "calendar_capital_event_count_mismatch", "事件數漂移"),
        (contract.expected_cohort == EXPECTED_COHORT, "calendar_capital_cohort_mismatch", "完整 cohort 漂移"),
        (contract.momentum_sessions == MOMENTUM_SESSIONS and contract.trend_sessions == TREND_SESSIONS and contract.top_k == TOP_K, "calendar_capital_signal_rule_mismatch", "訊號或 Top-K 漂移"),
        (contract.entry_delay == ENTRY_DELAY and contract.holding_sessions == HOLDING_SESSIONS, "calendar_capital_execution_clock_mismatch", "成交時鐘漂移"),
        (contract.slot_count == SLOT_COUNT and contract.events_per_slot == EVENTS_PER_SLOT, "calendar_capital_slot_contract_mismatch", "槽位數或事件數漂移"),
        (contract.assignment_sha256 == ASSIGNMENT_SHA256, "calendar_capital_assignment_mismatch", "槽位 assignment 漂移"),
        (contract.initial_capital_usd == INITIAL_CAPITAL_USD, "calendar_capital_initial_capital_mismatch", "初始資本漂移"),
        (contract.primary_round_trip_cost_bps == PRIMARY_ROUND_TRIP_COST_BPS and contract.cost_stress_bps == COST_STRESS_BPS, "calendar_capital_cost_contract_mismatch", "主要成本或成本壓力漂移"),
        (contract.path_ids == PATH_IDS and contract.family_baseline_ids == FAMILY_BASELINE_IDS, "calendar_capital_baseline_family_mismatch", "固定路徑或 family 漂移"),
        (contract.shy_excess_proxy, "calendar_capital_excess_proxy_mismatch", "SHY excess proxy 被取消"),
        (contract.hac_lag == HAC_LAG and contract.family_alpha == FAMILY_ALPHA, "calendar_capital_statistical_contract_mismatch", "NW lag 或 alpha 漂移"),
        (contract.bootstrap_block_sessions == BOOTSTRAP_BLOCK_SESSIONS and contract.bootstrap_paths == BOOTSTRAP_PATHS and contract.bootstrap_seed == BOOTSTRAP_SEED and contract.common_bootstrap_indices and contract.centered_under_null, "calendar_capital_bootstrap_contract_mismatch", "bootstrap 契約漂移"),
        (contract.global_search_trials == GLOBAL_SEARCH_TRIALS, "calendar_capital_global_trials_mismatch", "全專案 trials 漂移"),
        (contract.first_half_end == FIRST_HALF_END.strftime("%Y-%m-%d") and contract.second_half_start == SECOND_HALF_START.strftime("%Y-%m-%d"), "calendar_capital_half_clock_mismatch", "固定半期漂移"),
        (contract.crisis_years == CRISIS_YEARS and contract.best_year_removal_count == BEST_YEAR_REMOVAL_COUNT, "calendar_capital_stress_contract_mismatch", "危機或最佳年份壓力漂移"),
        (contract.current_identifiers_only and not contract.paper_authorized and not contract.real_money_authorized, "calendar_capital_decision_boundary_breached", "身份警告或 Paper／實金邊界被突破"),
    )
    for passed, code, detail in checks:
        if not passed:
            _fail(code, detail)


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _complete_current_cohort(panel: Any) -> list[str]:
    records = load_stock_watchlist()
    symbols = [record.symbol for record in records if record.symbol in panel.close.columns]
    return [
        ticker
        for ticker in symbols
        if panel.close.loc[:SHORT_TERM_START, ticker].notna().any()
        and bool(panel.close.loc[SHORT_TERM_START:SHORT_TERM_END, ticker].notna().all())
    ]


def _load_inputs(
    root: Path, contract: FrozenCalendarCapitalContract
) -> tuple[Any, list[str], list[dict[str, Any]], dict[str, Any]]:
    paths = {
        "protocol": root / PROTOCOL_PATH,
        "round28": root / ROUND28_RECEIPT_PATH,
        "round27": root / ROUND27_RECEIPT_PATH,
        "round24": root / ROUND24_RECEIPT_PATH,
        "event_receipt": root / EVENT_RECEIPT_PATH,
        "snapshot": root / SNAPSHOT_PATH,
        "watchlist": root / WATCHLIST_PATH,
    }
    observed = {key: _sha256_file(path) for key, path in paths.items()}
    expected = {
        "protocol": contract.protocol_sha256,
        "round28": contract.round28_receipt_sha256,
        "round27": contract.round27_receipt_sha256,
        "round24": contract.round24_receipt_sha256,
        "event_receipt": contract.event_receipt_sha256,
        "snapshot": contract.snapshot_sha256,
        "watchlist": contract.watchlist_sha256,
    }
    error_codes = {
        "protocol": "calendar_capital_protocol_hash_mismatch",
        "round28": "calendar_capital_round28_receipt_mismatch",
        "round27": "calendar_capital_round27_receipt_mismatch",
        "round24": "calendar_capital_round24_receipt_mismatch",
        "event_receipt": "calendar_capital_event_receipt_mismatch",
        "snapshot": "calendar_capital_market_data_mismatch",
        "watchlist": "calendar_capital_watchlist_mismatch",
    }
    for key, expected_hash in expected.items():
        if observed[key] != expected_hash:
            _fail(error_codes[key], f"{key} SHA-256 漂移")

    panel, _ = load_snapshot(paths["snapshot"])
    observed_panel = panel_fingerprint(panel)
    if observed_panel != contract.panel_sha256:
        _fail("calendar_capital_market_data_mismatch", "panel fingerprint 漂移")
    cohort = _complete_current_cohort(panel)
    if len(cohort) != contract.expected_cohort:
        _fail("calendar_capital_cohort_mismatch", "完整現時 cohort 不是 25 隻")
    required_benchmarks = {"QQQ", "SPY", "SHY"}
    if not required_benchmarks.issubset(panel.close.columns):
        _fail("calendar_capital_baseline_family_mismatch", "QQQ／SPY／SHY 行情不完整")

    source = json.loads(paths["event_receipt"].read_text(encoding="utf-8"))
    try:
        frozen_events = source["taiwan_reference_signal_layer_diagnostic"]["horizons"]["20"][
            "event_series"
        ]
    except (KeyError, TypeError) as exc:
        _fail("calendar_capital_event_receipt_mismatch", f"20 日事件路徑缺失：{exc}")
    parents = {
        key: json.loads(paths[key].read_text(encoding="utf-8"))
        for key in ("round28", "round27", "round24")
    }
    if (
        parents["round28"].get("research_round") != 28
        or parents["round27"].get("research_round") != 27
        or parents["round24"].get("research_round") != 24
    ):
        _fail("calendar_capital_parent_round_mismatch", "父收據 research round 漂移")
    return panel, cohort, frozen_events, {
        "paths": {key: str(path.relative_to(root)) for key, path in paths.items()},
        "hashes": {**observed, "panel": observed_panel},
    }


def _symbols_hash(symbols: list[str]) -> str:
    return hashlib.sha256(
        json.dumps(symbols, separators=(",", ":")).encode()
    ).hexdigest()


def _reconstruct_events(
    panel: Any, cohort: list[str], frozen_events: list[dict[str, Any]]
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    close = panel.close[cohort]
    momentum = close.pct_change(MOMENTUM_SESSIONS, fill_method=None)
    trend = close > close.rolling(TREND_SESSIONS, min_periods=TREND_SESSIONS).mean()
    dollar_volume = (close * panel.volume[cohort]).rolling(20).median()
    weekly = _completed_period_mask(close.index, "weekly")
    signal_dates = close.index[
        weekly.to_numpy()
        & (close.index >= pd.Timestamp(SHORT_TERM_START))
        & (close.index <= pd.Timestamp(SHORT_TERM_END))
    ]
    primary_cost = PRIMARY_ROUND_TRIP_COST_BPS / 10_000.0
    rows: list[dict[str, Any]] = []
    assignment_rows: list[dict[str, Any]] = []
    active_counts = pd.Series(0, index=close.index, dtype=int)

    for signal_date in signal_dates:
        position = close.index.get_loc(signal_date)
        if not isinstance(position, int):
            _fail("calendar_capital_event_order_mismatch", "訊號日位置不唯一")
        entry_position = position + ENTRY_DELAY
        exit_position = entry_position + HOLDING_SESSIONS - 1
        if exit_position >= len(close.index):
            continue
        eligible_mask = (
            momentum.loc[signal_date].notna()
            & trend.loc[signal_date]
            & (close.loc[signal_date] > 5.0)
            & (dollar_volume.loc[signal_date] >= 20_000_000.0)
        )
        eligible = list(eligible_mask.index[eligible_mask])
        if len(eligible) < TOP_K:
            continue
        ranked = sorted(
            eligible,
            key=lambda ticker: (-float(momentum.loc[signal_date, ticker]), ticker),
        )
        selected = ranked[:TOP_K]
        entry_date = close.index[entry_position]
        exit_date = close.index[exit_position]
        gross = panel.close.loc[exit_date, cohort].div(panel.open.loc[entry_date, cohort]).sub(1.0)
        if not np.isfinite(gross.to_numpy(dtype=float)).all():
            _fail("calendar_capital_event_return_mismatch", "個股事件回報非有限")
        qqq_gross = float(
            panel.close.loc[exit_date, "QQQ"] / panel.open.loc[entry_date, "QQQ"] - 1.0
        )
        event_index = len(rows)
        slot = event_index % SLOT_COUNT
        event_returns = {
            "top7_five_slot": float(gross.loc[selected].mean() - primary_cost),
            "eligible_equal_five_slot": float(gross.loc[eligible].mean() - primary_cost),
            "complete_equal_five_slot": float(gross.mean() - primary_cost),
            "qqq_event_five_slot": float(qqq_gross - primary_cost),
        }
        rows.append(
            {
                "event_index": event_index,
                "slot": slot,
                "signal_date": pd.Timestamp(signal_date),
                "entry_date": pd.Timestamp(entry_date),
                "exit_date": pd.Timestamp(exit_date),
                "eligible": eligible,
                "ranked": ranked,
                "selected": selected,
                "gross": gross,
                "qqq_gross": qqq_gross,
                "event_returns": event_returns,
            }
        )
        assignment_rows.append(
            {
                "event_index": event_index,
                "entry_date": pd.Timestamp(entry_date).strftime("%Y-%m-%d"),
                "exit_date": pd.Timestamp(exit_date).strftime("%Y-%m-%d"),
                "slot": slot,
            }
        )
        active_counts.loc[entry_date:exit_date] += 1

    if len(rows) != EXPECTED_EVENTS or len(frozen_events) != EXPECTED_EVENTS:
        _fail("calendar_capital_event_count_mismatch", "重建或凍結事件不是 905 列")
    dates = [row["signal_date"].strftime("%Y-%m-%d") for row in rows]
    frozen_dates = [str(row["signal_date"]) for row in frozen_events]
    if (
        dates != frozen_dates
        or dates[0] != FIRST_SIGNAL_DATE
        or dates[-1] != LAST_SIGNAL_DATE
        or rows[0]["entry_date"].strftime("%Y-%m-%d") != FIRST_ENTRY_DATE
        or rows[-1]["exit_date"].strftime("%Y-%m-%d") != LAST_EXIT_DATE
    ):
        _fail("calendar_capital_event_order_mismatch", "事件日期或邊界漂移")

    frozen_columns = {
        "top7_five_slot": "top7_return",
        "eligible_equal_five_slot": "eligible_equal_return",
        "complete_equal_five_slot": "complete_cohort_equal_return",
        "qqq_event_five_slot": "qqq_return",
    }
    reconstruction = {
        path_id: max(
            abs(row["event_returns"][path_id] - float(frozen[column]))
            for row, frozen in zip(rows, frozen_events, strict=True)
        )
        for path_id, column in frozen_columns.items()
    }
    if max(reconstruction.values()) > RECONSTRUCTION_TOLERANCE:
        _fail("calendar_capital_event_return_mismatch", "事件淨回報未逐列重播")

    assignment_hash = hashlib.sha256(
        json.dumps(assignment_rows, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    slot_counts = [sum(row["slot"] == slot for row in rows) for slot in range(SLOT_COUNT)]
    for slot in range(SLOT_COUNT):
        slot_events = [row for row in rows if row["slot"] == slot]
        if any(
            left["exit_date"] >= right["entry_date"]
            for left, right in zip(slot_events[:-1], slot_events[1:], strict=True)
        ):
            _fail("calendar_capital_slot_overlap_mismatch", "同槽事件重疊")
    if (
        assignment_hash != ASSIGNMENT_SHA256
        or slot_counts != [EVENTS_PER_SLOT] * SLOT_COUNT
        or int(active_counts.max()) != SLOT_COUNT
    ):
        _fail("calendar_capital_assignment_mismatch", "五槽 assignment 或 concurrency 漂移")

    receipts = [
        {
            "event_index": row["event_index"],
            "slot": row["slot"],
            "signal_date": row["signal_date"].strftime("%Y-%m-%d"),
            "entry_date": row["entry_date"].strftime("%Y-%m-%d"),
            "exit_date": row["exit_date"].strftime("%Y-%m-%d"),
            "eligible_count": len(row["eligible"]),
            "eligible_sha256": _symbols_hash(row["eligible"]),
            "selected": row["selected"],
            "selected_sha256": _symbols_hash(row["selected"]),
            "event_returns": row["event_returns"],
        }
        for row in rows
    ]
    return rows, {
        "maximum_event_return_residuals": reconstruction,
        "maximum_event_return_residual": max(reconstruction.values()),
        "assignment_sha256": assignment_hash,
        "slot_event_counts": slot_counts,
        "maximum_concurrent_intervals": int(active_counts.max()),
        "event_receipts": receipts,
    }


def _event_symbols(event: dict[str, Any], path_id: str, cohort: list[str]) -> list[str]:
    if path_id == "top7_five_slot":
        return event["selected"]
    if path_id == "eligible_equal_five_slot":
        return event["eligible"]
    if path_id == "complete_equal_five_slot":
        return cohort
    if path_id == "qqq_event_five_slot":
        return ["QQQ"]
    _fail("calendar_capital_baseline_family_mismatch", f"未知事件路徑 {path_id}")


def _build_five_slot_path(
    panel: Any,
    cohort: list[str],
    events: list[dict[str, Any]],
    path_id: str,
    round_trip_cost_bps: int,
) -> dict[str, Any]:
    index = panel.close.loc[FIRST_SIGNAL_DATE:LAST_EXIT_DATE].index
    slot_initial = 1.0 / SLOT_COUNT
    side_cost = round_trip_cost_bps / 20_000.0
    slot_values: list[pd.Series] = []
    slot_active: list[pd.Series] = []
    traded_notional = pd.Series(0.0, index=index)
    terminal_residual = 0.0

    for slot in range(SLOT_COUNT):
        values = pd.Series(np.nan, index=index, dtype=float)
        active = pd.Series(False, index=index, dtype=bool)
        principal = slot_initial
        cursor = 0
        slot_events = [event for event in events if event["slot"] == slot]
        for event in slot_events:
            entry_position = int(index.get_loc(event["entry_date"]))
            exit_position = int(index.get_loc(event["exit_date"]))
            if cursor < entry_position:
                values.iloc[cursor:entry_position] = principal
            symbols = _event_symbols(event, path_id, cohort)
            active_index = index[entry_position : exit_position + 1]
            gross = (
                panel.close.loc[active_index, symbols]
                .div(panel.open.loc[event["entry_date"], symbols])
                .sub(1.0)
                .mean(axis=1)
            )
            relative = 1.0 + gross - side_cost
            relative.iloc[-1] -= side_cost
            if not np.isfinite(relative.to_numpy(dtype=float)).all() or (relative <= 0.0).any():
                _fail("calendar_capital_daily_path_mismatch", "槽位日線估值非正或非有限")
            values.loc[active_index] = principal * relative
            active.loc[active_index] = True
            traded_notional.loc[event["entry_date"]] += principal
            gross_exit_value = principal * (1.0 + float(gross.iloc[-1]) - side_cost)
            traded_notional.loc[event["exit_date"]] += gross_exit_value
            observed_event_return = float(values.loc[event["exit_date"]] / principal - 1.0)
            expected_event_return = float(
                event["gross"].loc[symbols].mean()
                - round_trip_cost_bps / 10_000.0
            ) if path_id != "qqq_event_five_slot" else float(
                event["qqq_gross"] - round_trip_cost_bps / 10_000.0
            )
            terminal_residual = max(
                terminal_residual, abs(observed_event_return - expected_event_return)
            )
            principal = float(values.loc[event["exit_date"]])
            cursor = exit_position + 1
        if cursor < len(index):
            values.iloc[cursor:] = principal
        if values.isna().any():
            _fail("calendar_capital_daily_path_mismatch", "槽位日線有缺值")
        slot_values.append(values)
        slot_active.append(active)

    slot_frame = pd.concat(slot_values, axis=1)
    slot_frame.columns = [f"slot_{slot}" for slot in range(SLOT_COUNT)]
    active_frame = pd.concat(slot_active, axis=1)
    active_frame.columns = slot_frame.columns
    equity = slot_frame.sum(axis=1)
    active_value = slot_frame.where(active_frame, 0.0).sum(axis=1)
    cash_value = equity - active_value
    exposure = active_value.div(equity)
    returns = equity.pct_change(fill_method=None).fillna(0.0)
    turnover = traded_notional.div(equity.shift(1).fillna(1.0))
    maximum_identity = float((equity - slot_frame.sum(axis=1)).abs().max())
    if (
        terminal_residual > RECONSTRUCTION_TOLERANCE
        or maximum_identity > RECONSTRUCTION_TOLERANCE
        or float(cash_value.min()) < -RECONSTRUCTION_TOLERANCE
        or float(exposure.max()) > 1.0 + RECONSTRUCTION_TOLERANCE
        or float(equity.min()) <= 0.0
    ):
        _fail("calendar_capital_daily_identity_mismatch", "槽位、成本、現金或無槓桿 identity 失敗")
    return {
        "equity": equity,
        "returns": returns,
        "turnover": turnover,
        "exposure": exposure,
        "cash_value": cash_value,
        "slot_values": slot_frame,
        "maximum_event_terminal_residual": terminal_residual,
        "maximum_daily_identity_residual": maximum_identity,
    }


def _build_buy_hold_path(panel: Any, ticker: str, round_trip_cost_bps: int) -> dict[str, Any]:
    index = panel.close.loc[FIRST_SIGNAL_DATE:LAST_EXIT_DATE].index
    side_cost = round_trip_cost_bps / 20_000.0
    entry_date = pd.Timestamp(FIRST_ENTRY_DATE)
    exit_date = pd.Timestamp(LAST_EXIT_DATE)
    gross = panel.close.loc[entry_date:exit_date, ticker].div(panel.open.loc[entry_date, ticker]).sub(1.0)
    relative = 1.0 + gross - side_cost
    relative.loc[exit_date] -= side_cost
    equity = pd.Series(1.0, index=index, dtype=float)
    equity.loc[entry_date:exit_date] = relative
    returns = equity.pct_change(fill_method=None).fillna(0.0)
    exposure = pd.Series(0.0, index=index)
    exposure.loc[entry_date:exit_date] = 1.0
    turnover = pd.Series(0.0, index=index)
    turnover.loc[entry_date] = 1.0
    turnover.loc[exit_date] += float(1.0 + gross.loc[exit_date] - side_cost)
    return {
        "equity": equity,
        "returns": returns,
        "turnover": turnover,
        "exposure": exposure,
        "cash_value": equity.where(~exposure.astype(bool), 0.0),
        "slot_values": None,
        "maximum_event_terminal_residual": 0.0,
        "maximum_daily_identity_residual": 0.0,
    }


def _path_metrics(path: dict[str, Any], shy_proxy: pd.Series) -> dict[str, float]:
    equity = path["equity"]
    returns = path["returns"]
    years = (equity.index[-1] - equity.index[0]).days / 365.2425
    total_return = float(equity.iloc[-1] / equity.iloc[0] - 1.0)
    cagr = float((equity.iloc[-1] / equity.iloc[0]) ** (1.0 / years) - 1.0)
    volatility = float(returns.std(ddof=1) * math.sqrt(252.0))
    excess = returns - shy_proxy.reindex(returns.index).fillna(0.0)
    excess_std = float(excess.std(ddof=1))
    excess_sharpe = (
        float(excess.mean() / excess_std * math.sqrt(252.0)) if excess_std > 0.0 else 0.0
    )
    downside = excess[excess < 0.0]
    downside_std = float(downside.std(ddof=1)) if len(downside) > 1 else 0.0
    excess_sortino = (
        float(excess.mean() / downside_std * math.sqrt(252.0))
        if downside_std > 0.0
        else 0.0
    )
    drawdown = max_drawdown(equity)
    return {
        "total_return": total_return,
        "cagr": cagr,
        "volatility": volatility,
        "shy_excess_sharpe": excess_sharpe,
        "shy_excess_sortino": excess_sortino,
        "max_drawdown": drawdown,
        "calmar": float(cagr / abs(drawdown)) if drawdown < 0.0 else 0.0,
        "terminal_usd": float(INITIAL_CAPITAL_USD * equity.iloc[-1]),
        "annual_turnover": float(path["turnover"].sum() / years),
        "average_exposure": float(path["exposure"].mean()),
        "maximum_exposure": float(path["exposure"].max()),
        "minimum_cash_value": float(path["cash_value"].min()),
    }


def _nw(values: np.ndarray) -> dict[str, float | int]:
    result = newey_west_mean_test(pd.Series(values), max_lag=HAC_LAG, periods_per_year=252)
    mean = float(result["mean_daily"])
    t_stat = float(result["t_stat"])
    standard_error = abs(mean / t_stat) if t_stat != 0.0 else 0.0
    return {
        "mean_daily_difference": mean,
        "annualized_arithmetic_difference": float(result["annualized"]),
        "standard_error": standard_error,
        "t_stat": t_stat,
        "lag": int(result["lag"]),
    }


def _normal_two_sided_p(t_stat: float) -> float:
    return float(math.erfc(abs(t_stat) / math.sqrt(2.0)))


def _fixed_halves(values: np.ndarray, dates: pd.DatetimeIndex) -> dict[str, Any]:
    first = np.asarray(dates <= FIRST_HALF_END)
    second = np.asarray(dates >= SECOND_HALF_START)
    return {
        "first": {
            "sessions": int(first.sum()),
            "mean_daily_difference": float(values[first].mean()),
            "compounded_active_return": float(np.prod(1.0 + values[first]) - 1.0),
        },
        "second": {
            "sessions": int(second.sum()),
            "mean_daily_difference": float(values[second].mean()),
            "compounded_active_return": float(np.prod(1.0 + values[second]) - 1.0),
        },
    }


def _annual_active(values: np.ndarray, dates: pd.DatetimeIndex) -> list[dict[str, Any]]:
    series = pd.Series(values, index=dates)
    rows = []
    for year, group in series.groupby(series.index.year):
        rows.append(
            {
                "year": int(year),
                "sessions": len(group),
                "mean_daily_difference": float(group.mean()),
                "compounded_active_return": float((1.0 + group).prod() - 1.0),
            }
        )
    return rows


def _holm_adjust(rows: list[dict[str, Any]]) -> dict[str, float]:
    ordered = sorted(rows, key=lambda row: (row["raw_normal_p"], row["baseline_id"]))
    adjusted: dict[str, float] = {}
    running = 0.0
    total = len(ordered)
    for rank, row in enumerate(ordered):
        running = max(running, min(1.0, (total - rank) * row["raw_normal_p"]))
        adjusted[row["baseline_id"]] = running
    return adjusted


def _common_bootstrap(
    matrix: np.ndarray, observed_t: np.ndarray, standard_errors: np.ndarray
) -> dict[str, Any]:
    centered = matrix - matrix.mean(axis=0, keepdims=True)
    if not np.allclose(centered.mean(axis=0), 0.0, atol=1e-15):
        _fail("calendar_capital_bootstrap_contract_mismatch", "bootstrap 去中心化失敗")
    if (standard_errors <= 0.0).any():
        _fail("calendar_capital_bootstrap_contract_mismatch", "NW 標準誤非正")
    rows = len(matrix)
    blocks_per_path = math.ceil(rows / BOOTSTRAP_BLOCK_SESSIONS)
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    starts = rng.integers(0, rows, size=(BOOTSTRAP_PATHS, blocks_per_path), dtype=np.int64)
    offsets = np.arange(BOOTSTRAP_BLOCK_SESSIONS, dtype=np.int64)
    max_abs = np.empty(BOOTSTRAP_PATHS, dtype=float)
    for start in range(0, BOOTSTRAP_PATHS, 100):
        stop = min(BOOTSTRAP_PATHS, start + 100)
        indices = (starts[start:stop, :, None] + offsets[None, None, :]) % rows
        indices = indices.reshape(stop - start, -1)[:, :rows]
        means = centered[indices].mean(axis=1)
        max_abs[start:stop] = np.abs(means / standard_errors).max(axis=1)
    p_values = (
        1.0 + (max_abs[:, None] >= np.abs(observed_t)[None, :]).sum(axis=0).astype(float)
    ) / (BOOTSTRAP_PATHS + 1.0)
    return {
        "block_sessions": BOOTSTRAP_BLOCK_SESSIONS,
        "paths": BOOTSTRAP_PATHS,
        "seed": BOOTSTRAP_SEED,
        "circular": True,
        "common_indices": True,
        "centered_under_null": True,
        "blocks_per_path": blocks_per_path,
        "start_index_sha256": hashlib.sha256(starts.tobytes()).hexdigest(),
        "single_step_max_t_p": p_values.tolist(),
    }


def _crisis_metrics(path: dict[str, Any], year: int) -> dict[str, Any]:
    returns = path["returns"].loc[str(year)]
    if returns.empty:
        _fail("calendar_capital_stress_contract_mismatch", f"{year} 沒有日線")
    equity = (1.0 + returns).cumprod()
    return {
        "sessions": len(returns),
        "return": float(equity.iloc[-1] - 1.0),
        "max_drawdown": max_drawdown(equity),
    }


def _contract_attacks() -> list[
    tuple[
        str,
        str,
        str,
        Callable[[FrozenCalendarCapitalContract], FrozenCalendarCapitalContract],
    ]
]:
    return [
        ("01", "協議 SHA 漂移", "calendar_capital_protocol_hash_mismatch", lambda c: replace(c, protocol_sha256="0" * 64)),
        ("02", "協議 commit 漂移", "calendar_capital_protocol_commit_mismatch", lambda c: replace(c, protocol_commit="0" * 40)),
        ("03", "第 28 輪收據漂移", "calendar_capital_round28_receipt_mismatch", lambda c: replace(c, round28_receipt_sha256="0" * 64)),
        ("04", "第 27 輪收據漂移", "calendar_capital_round27_receipt_mismatch", lambda c: replace(c, round27_receipt_sha256="0" * 64)),
        ("05", "第 24 輪收據漂移", "calendar_capital_round24_receipt_mismatch", lambda c: replace(c, round24_receipt_sha256="0" * 64)),
        ("06", "原始事件收據漂移", "calendar_capital_event_receipt_mismatch", lambda c: replace(c, event_receipt_sha256="0" * 64)),
        ("07", "行情 archive 漂移", "calendar_capital_market_data_mismatch", lambda c: replace(c, snapshot_sha256="0" * 64)),
        ("08", "watchlist 漂移", "calendar_capital_watchlist_mismatch", lambda c: replace(c, watchlist_sha256="0" * 64)),
        ("09", "台股參考 commit 漂移", "calendar_capital_reference_mismatch", lambda c: replace(c, reference_commits=())),
        ("10", "事件改 904", "calendar_capital_event_count_mismatch", lambda c: replace(c, expected_events=904)),
        ("11", "完整 cohort 改 24", "calendar_capital_cohort_mismatch", lambda c: replace(c, expected_cohort=24)),
        ("12", "Top-K 改 10", "calendar_capital_signal_rule_mismatch", lambda c: replace(c, top_k=10)),
        ("13", "持有期改 10 日", "calendar_capital_execution_clock_mismatch", lambda c: replace(c, holding_sessions=10)),
        ("14", "槽位改四個", "calendar_capital_slot_contract_mismatch", lambda c: replace(c, slot_count=4)),
        ("15", "assignment SHA 漂移", "calendar_capital_assignment_mismatch", lambda c: replace(c, assignment_sha256="0" * 64)),
        ("16", "初始資本改 US$10,000", "calendar_capital_initial_capital_mismatch", lambda c: replace(c, initial_capital_usd=10_000.0)),
        ("17", "主要成本改 10 bps", "calendar_capital_cost_contract_mismatch", lambda c: replace(c, primary_round_trip_cost_bps=10)),
        ("18", "刪除 QQQ buy-hold", "calendar_capital_baseline_family_mismatch", lambda c: replace(c, path_ids=PATH_IDS[:-3] + PATH_IDS[-2:])),
        ("19", "取消 SHY excess", "calendar_capital_excess_proxy_mismatch", lambda c: replace(c, shy_excess_proxy=False)),
        ("20", "NW lag 改 4", "calendar_capital_statistical_contract_mismatch", lambda c: replace(c, hac_lag=4)),
        ("21", "bootstrap block 改 20", "calendar_capital_bootstrap_contract_mismatch", lambda c: replace(c, bootstrap_block_sessions=20)),
        ("22", "全專案 trials 重設", "calendar_capital_global_trials_mismatch", lambda c: replace(c, global_search_trials=6)),
        ("23", "半期起點漂移", "calendar_capital_half_clock_mismatch", lambda c: replace(c, second_half_start="2017-01-01")),
        ("24", "刪除 2022 危機", "calendar_capital_stress_contract_mismatch", lambda c: replace(c, crisis_years=(2008, 2020))),
        ("25", "越權啟動 Paper", "calendar_capital_decision_boundary_breached", lambda c: replace(c, paper_authorized=True)),
    ]


def run_contract_attacks() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for attack_id, label, expected_code, mutate in _contract_attacks():
        observed_code: str | None = None
        try:
            validate_calendar_capital_contract(mutate(FROZEN_CONTRACT))
        except CalendarCapitalAccountingError as exc:
            observed_code = exc.code
        rows.append(
            {
                "id": attack_id,
                "label": label,
                "expected_error_code": expected_code,
                "observed_error_code": observed_code,
                "rejected": observed_code == expected_code,
            }
        )
    return rows


def run_calendar_capital_accounting(root: str | Path) -> dict[str, Any]:
    root_path = Path(root).resolve()
    contract = FROZEN_CONTRACT
    validate_calendar_capital_contract(contract)
    panel, cohort, frozen_events, input_meta = _load_inputs(root_path, contract)
    events, reconstruction = _reconstruct_events(panel, cohort, frozen_events)

    index = panel.close.loc[FIRST_SIGNAL_DATE:LAST_EXIT_DATE].index
    shy_proxy = panel.close.loc[index, "SHY"].pct_change(fill_method=None).fillna(0.0)
    primary_paths = {
        path_id: _build_five_slot_path(
            panel, cohort, events, path_id, PRIMARY_ROUND_TRIP_COST_BPS
        )
        for path_id in EVENT_PATH_IDS
    }
    primary_paths.update(
        {
            "qqq_buy_hold": _build_buy_hold_path(panel, "QQQ", PRIMARY_ROUND_TRIP_COST_BPS),
            "spy_buy_hold": _build_buy_hold_path(panel, "SPY", PRIMARY_ROUND_TRIP_COST_BPS),
            "shy_buy_hold": _build_buy_hold_path(panel, "SHY", PRIMARY_ROUND_TRIP_COST_BPS),
        }
    )
    zero_cost_paths = {
        path_id: _build_five_slot_path(panel, cohort, events, path_id, 0)
        for path_id in EVENT_PATH_IDS
    }
    zero_cost_paths.update(
        {
            "qqq_buy_hold": _build_buy_hold_path(panel, "QQQ", 0),
            "spy_buy_hold": _build_buy_hold_path(panel, "SPY", 0),
            "shy_buy_hold": _build_buy_hold_path(panel, "SHY", 0),
        }
    )

    metrics: dict[str, Any] = {}
    for path_id in PATH_IDS:
        primary = _path_metrics(primary_paths[path_id], shy_proxy)
        zero = _path_metrics(zero_cost_paths[path_id], shy_proxy)
        primary["path_id"] = path_id
        primary["label"] = PATH_LABELS[path_id]
        primary["round_trip_cost_bps"] = PRIMARY_ROUND_TRIP_COST_BPS
        primary["cost_drag_cagr"] = zero["cagr"] - primary["cagr"]
        primary["cost_drag_terminal_usd"] = zero["terminal_usd"] - primary["terminal_usd"]
        metrics[path_id] = primary

    candidate_returns = primary_paths["top7_five_slot"]["returns"]
    comparisons: list[dict[str, Any]] = []
    matrix_columns: list[np.ndarray] = []
    active_by_baseline: dict[str, np.ndarray] = {}
    for baseline_id in FAMILY_BASELINE_IDS:
        values = (
            candidate_returns - primary_paths[baseline_id]["returns"]
        ).to_numpy(dtype=float)
        active_by_baseline[baseline_id] = values
        nw = _nw(values)
        comparisons.append(
            {
                "baseline_id": baseline_id,
                "baseline_label": PATH_LABELS[baseline_id],
                "sessions": len(values),
                "mean_daily_difference": float(values.mean()),
                "median_daily_difference": float(np.median(values)),
                "positive_fraction": float((values > 0.0).mean()),
                "newey_west": nw,
                "raw_normal_p": _normal_two_sided_p(float(nw["t_stat"])),
                "fixed_halves": _fixed_halves(values, index),
                "annual_active_returns": _annual_active(values, index),
            }
        )
        matrix_columns.append(values)
    holm = _holm_adjust(comparisons)
    matrix = np.column_stack(matrix_columns)
    observed_t = np.asarray([row["newey_west"]["t_stat"] for row in comparisons])
    standard_errors = np.asarray(
        [row["newey_west"]["standard_error"] for row in comparisons]
    )
    bootstrap = _common_bootstrap(matrix, observed_t, standard_errors)
    for idx, row in enumerate(comparisons):
        row["holm_adjusted_p"] = holm[row["baseline_id"]]
        row["bootstrap_max_t_p"] = bootstrap["single_step_max_t_p"][idx]
        row["family_bonferroni_p"] = min(1.0, row["raw_normal_p"] * len(comparisons))
        row["global_bonferroni_p"] = min(1.0, row["raw_normal_p"] * GLOBAL_SEARCH_TRIALS)
    comparison_by_id = {row["baseline_id"]: row for row in comparisons}

    eligible_annual = comparison_by_id["eligible_equal_five_slot"]["annual_active_returns"]
    removed_years = [
        row["year"]
        for row in sorted(
            eligible_annual,
            key=lambda row: (-row["compounded_active_return"], row["year"]),
        )[:BEST_YEAR_REMOVAL_COUNT]
    ]
    eligible_values = active_by_baseline["eligible_equal_five_slot"]
    tail_mask = ~np.isin(index.year, removed_years)
    tail_values = eligible_values[tail_mask]
    tail_stress = {
        "selection_basis": "highest_candidate_minus_eligible_compounded_active_year",
        "removed_years": removed_years,
        "remaining_sessions": int(tail_mask.sum()),
        "mean_daily_difference": float(tail_values.mean()),
        "newey_west": _nw(tail_values),
    }

    crisis = {
        str(year): {
            path_id: _crisis_metrics(primary_paths[path_id], year) for path_id in PATH_IDS
        }
        for year in CRISIS_YEARS
    }
    cost_stresses: dict[str, Any] = {}
    for cost_bps in COST_STRESS_BPS:
        paths = {
            path_id: _build_five_slot_path(panel, cohort, events, path_id, cost_bps)
            for path_id in EVENT_PATH_IDS
        }
        cost_metrics = {
            path_id: _path_metrics(path, shy_proxy) for path_id, path in paths.items()
        }
        candidate = cost_metrics["top7_five_slot"]
        cost_stresses[str(cost_bps)] = {
            "round_trip_cost_bps": cost_bps,
            "paths": cost_metrics,
            "candidate_cagr_differences": {
                baseline_id: candidate["cagr"] - cost_metrics[baseline_id]["cagr"]
                for baseline_id in EVENT_PATH_IDS[1:]
            },
            "candidate_terminal_usd_differences": {
                baseline_id: candidate["terminal_usd"] - cost_metrics[baseline_id]["terminal_usd"]
                for baseline_id in EVENT_PATH_IDS[1:]
            },
        }

    candidate_metrics = metrics["top7_five_slot"]
    eligible_comparison = comparison_by_id["eligible_equal_five_slot"]
    complete_comparison = comparison_by_id["complete_equal_five_slot"]
    qqq_event_comparison = comparison_by_id["qqq_event_five_slot"]
    gates = [
        {"id": "exact_input_receipts", "label": "所有固定輸入、父收據、行情、watchlist 與參考 commit 精確", "passed": True},
        {"id": "event_return_reconstruction", "label": "905 個四路事件淨回報逐列重建", "passed": reconstruction["maximum_event_return_residual"] <= RECONSTRUCTION_TOLERANCE},
        {"id": "five_slot_assignment", "label": "assignment SHA、五槽、每槽 181 事件及最大 concurrency 精確", "passed": reconstruction["assignment_sha256"] == ASSIGNMENT_SHA256 and reconstruction["slot_event_counts"] == [EVENTS_PER_SLOT] * SLOT_COUNT and reconstruction["maximum_concurrent_intervals"] == SLOT_COUNT},
        {"id": "daily_capital_identities", "label": "日線槽位、現金、無槓桿、成本及總資產 identity 全通過", "passed": all(primary_paths[path_id]["maximum_event_terminal_residual"] <= RECONSTRUCTION_TOLERANCE and primary_paths[path_id]["maximum_daily_identity_residual"] <= RECONSTRUCTION_TOLERANCE and metrics[path_id]["minimum_cash_value"] >= -RECONSTRUCTION_TOLERANCE and metrics[path_id]["maximum_exposure"] <= 1.0 + RECONSTRUCTION_TOLERANCE for path_id in EVENT_PATH_IDS)},
        {"id": "candidate_cagr_vs_eligible", "label": "候選 CAGR 高於合資格池五槽", "passed": candidate_metrics["cagr"] > metrics["eligible_equal_five_slot"]["cagr"]},
        {"id": "candidate_cagr_vs_complete", "label": "候選 CAGR 高於完整現時股池五槽", "passed": candidate_metrics["cagr"] > metrics["complete_equal_five_slot"]["cagr"]},
        {"id": "candidate_cagr_vs_qqq_event", "label": "候選 CAGR 高於 QQQ event 五槽", "passed": candidate_metrics["cagr"] > metrics["qqq_event_five_slot"]["cagr"]},
        {"id": "candidate_cagr_vs_qqq_buy_hold", "label": "候選 CAGR 高於 QQQ 買入並持有", "passed": candidate_metrics["cagr"] > metrics["qqq_buy_hold"]["cagr"]},
        {"id": "candidate_cagr_vs_spy_buy_hold", "label": "候選 CAGR 高於 SPY 買入並持有", "passed": candidate_metrics["cagr"] > metrics["spy_buy_hold"]["cagr"]},
        {"id": "candidate_excess_sharpe", "label": "候選 SHY-excess Sharpe 為正且高於三個事件五槽基準", "passed": candidate_metrics["shy_excess_sharpe"] > 0.0 and all(candidate_metrics["shy_excess_sharpe"] > metrics[path_id]["shy_excess_sharpe"] for path_id in EVENT_PATH_IDS[1:])},
        {"id": "candidate_drawdown", "label": "候選最大跌幅不比 QQQ buy-hold 深超過十個百分點", "passed": candidate_metrics["max_drawdown"] >= metrics["qqq_buy_hold"]["max_drawdown"] - 0.10},
        {"id": "nw_vs_eligible", "label": "候選對 eligible 平均日差為正且 NW t 不低於 1.96", "passed": eligible_comparison["mean_daily_difference"] > 0.0 and eligible_comparison["newey_west"]["t_stat"] >= 1.96},
        {"id": "nw_vs_complete", "label": "候選對 complete 平均日差為正且 NW t 不低於 1.96", "passed": complete_comparison["mean_daily_difference"] > 0.0 and complete_comparison["newey_west"]["t_stat"] >= 1.96},
        {"id": "nw_vs_qqq_event", "label": "候選對 QQQ event 平均日差為正且 NW t 不低於 1.96", "passed": qqq_event_comparison["mean_daily_difference"] > 0.0 and qqq_event_comparison["newey_west"]["t_stat"] >= 1.96},
        {"id": "fixed_halves", "label": "候選對 eligible／complete／QQQ buy-hold／SPY 的前後半平均日差全正", "passed": all(comparison_by_id[path_id]["fixed_halves"][half]["mean_daily_difference"] > 0.0 for path_id in ("eligible_equal_five_slot", "complete_equal_five_slot", "qqq_buy_hold", "spy_buy_hold") for half in ("first", "second"))},
        {"id": "holm_and_max_t", "label": "候選對 eligible 的 Holm 與共同 max-t p 均不高於 0.05", "passed": eligible_comparison["holm_adjusted_p"] <= FAMILY_ALPHA and eligible_comparison["bootstrap_max_t_p"] <= FAMILY_ALPHA},
        {"id": "best_three_years_removed", "label": "移除最佳三年後候選對 eligible 仍為正且 NW t 不低於 1.96", "passed": tail_stress["mean_daily_difference"] > 0.0 and tail_stress["newey_west"]["t_stat"] >= 1.96},
        {"id": "global_and_cost_stress", "label": "6,214 次 Bonferroni 通過且 50／100 bps 仍勝三個事件基準", "passed": eligible_comparison["global_bonferroni_p"] <= FAMILY_ALPHA and all(all(value > 0.0 for value in row["candidate_cagr_differences"].values()) for row in cost_stresses.values())},
    ]
    gate_summary = {
        "passed": sum(int(row["passed"]) for row in gates),
        "total": len(gates),
        "all_passed": all(row["passed"] for row in gates),
    }

    controls = [
        {"id": "01", "label": "protocol SHA 與 commit", "passed": input_meta["hashes"]["protocol"] == PROTOCOL_SHA256 and PROTOCOL_COMMIT == contract.protocol_commit},
        {"id": "02", "label": "第 28 輪收據", "passed": input_meta["hashes"]["round28"] == ROUND28_RECEIPT_SHA256},
        {"id": "03", "label": "第 27 輪收據", "passed": input_meta["hashes"]["round27"] == ROUND27_RECEIPT_SHA256},
        {"id": "04", "label": "第 24 輪收據", "passed": input_meta["hashes"]["round24"] == ROUND24_RECEIPT_SHA256},
        {"id": "05", "label": "原始事件收據", "passed": input_meta["hashes"]["event_receipt"] == EVENT_RECEIPT_SHA256},
        {"id": "06", "label": "行情 archive 與 panel", "passed": input_meta["hashes"]["snapshot"] == SNAPSHOT_SHA256 and input_meta["hashes"]["panel"] == PANEL_SHA256},
        {"id": "07", "label": "watchlist", "passed": input_meta["hashes"]["watchlist"] == WATCHLIST_SHA256},
        {"id": "08", "label": "三個台股參考 commit", "passed": contract.reference_commits == REFERENCE_COMMITS},
        {"id": "09", "label": "905 事件次序與邊界", "passed": len(events) == EXPECTED_EVENTS and events[0]["signal_date"].strftime("%Y-%m-%d") == FIRST_SIGNAL_DATE and events[-1]["exit_date"].strftime("%Y-%m-%d") == LAST_EXIT_DATE},
        {"id": "10", "label": "完整現時 cohort 25 隻", "passed": len(cohort) == EXPECTED_COHORT},
        {"id": "11", "label": "20／60 日訊號與 Top-7", "passed": contract.momentum_sessions == 20 and contract.trend_sessions == 60 and contract.top_k == 7},
        {"id": "12", "label": "D+1 open 至第 20 session close", "passed": contract.entry_delay == 1 and contract.holding_sessions == 20},
        {"id": "13", "label": "五槽 assignment", "passed": reconstruction["assignment_sha256"] == ASSIGNMENT_SHA256},
        {"id": "14", "label": "每槽 20% 及 181 事件", "passed": reconstruction["slot_event_counts"] == [181] * 5},
        {"id": "15", "label": "20／50／100 bps 成本", "passed": contract.primary_round_trip_cost_bps == 20 and contract.cost_stress_bps == (50, 100)},
        {"id": "16", "label": "七條固定日曆路徑", "passed": tuple(primary_paths) == PATH_IDS},
        {"id": "17", "label": "SHY excess 定義", "passed": contract.shy_excess_proxy and shy_proxy.notna().all()},
        {"id": "18", "label": "日線資產與現金 identity", "passed": all(primary_paths[path_id]["maximum_daily_identity_residual"] <= 1e-12 for path_id in EVENT_PATH_IDS)},
        {"id": "19", "label": "路徑同起訖日", "passed": all(path["equity"].index.equals(index) for path in primary_paths.values())},
        {"id": "20", "label": "六假說 family", "passed": tuple(row["baseline_id"] for row in comparisons) == FAMILY_BASELINE_IDS},
        {"id": "21", "label": "NW lag 20", "passed": all(row["newey_west"]["lag"] == 20 for row in comparisons)},
        {"id": "22", "label": "63-session／20,000 路徑共同 bootstrap", "passed": bootstrap["block_sessions"] == 63 and bootstrap["paths"] == 20_000 and bootstrap["common_indices"]},
        {"id": "23", "label": "固定半期與危機／尾部", "passed": contract.first_half_end == "2016-07-29" and contract.crisis_years == (2008, 2020, 2022) and len(removed_years) == 3},
        {"id": "24", "label": "全專案 6,214 trials", "passed": contract.global_search_trials == 6_214},
        {"id": "25", "label": "現時身份及 Paper／實金邊界", "passed": contract.current_identifiers_only and not contract.paper_authorized and not contract.real_money_authorized},
    ]
    control_summary = {
        "passed": sum(int(row["passed"]) for row in controls),
        "total": len(controls),
        "all_passed": all(row["passed"] for row in controls),
    }
    attacks = run_contract_attacks()
    attack_summary = {
        "rejected": sum(int(row["rejected"]) for row in attacks),
        "total": len(attacks),
        "all_rejected": all(row["rejected"] for row in attacks),
    }

    calendar_rows = []
    for date in index:
        calendar_rows.append(
            {
                "date": date.strftime("%Y-%m-%d"),
                "equity": {path_id: float(primary_paths[path_id]["equity"].loc[date]) for path_id in PATH_IDS},
                "daily_return": {path_id: float(primary_paths[path_id]["returns"].loc[date]) for path_id in PATH_IDS},
                "top7_exposure": float(primary_paths["top7_five_slot"]["exposure"].loc[date]),
                "top7_cash_value": float(primary_paths["top7_five_slot"]["cash_value"].loc[date]),
            }
        )

    return {
        "schema_version": SCHEMA_VERSION,
        "research_round": RESEARCH_ROUND,
        "research_role": "same_seen_survivor_calendar_capital_falsification_not_formal_backtest",
        "generated_on": "2026-08-04",
        "protocol": {
            "path": PROTOCOL_PATH,
            "sha256": PROTOCOL_SHA256,
            "commit": PROTOCOL_COMMIT,
            "calculated_after_protocol_commit": True,
            "independent_first_unseen_evidence": False,
            "same_seen_905_event_family": True,
        },
        "references": [
            {"repository": repository, "commit": commit}
            for repository, commit in REFERENCE_COMMITS
        ],
        "input": {
            "events": len(events),
            "first_signal_date": FIRST_SIGNAL_DATE,
            "first_entry_date": FIRST_ENTRY_DATE,
            "last_signal_date": LAST_SIGNAL_DATE,
            "last_exit_date": LAST_EXIT_DATE,
            "current_cohort": cohort,
            "current_cohort_count": len(cohort),
            "identifier_scope": "2026_current_symbols_not_permanent_ids",
            "survivorship_bias_warning": True,
            "initial_capital_usd": INITIAL_CAPITAL_USD,
        },
        "input_receipts": input_meta["hashes"],
        "method": {
            "momentum_sessions": MOMENTUM_SESSIONS,
            "trend_sessions": TREND_SESSIONS,
            "top_k": TOP_K,
            "entry_delay_sessions": ENTRY_DELAY,
            "holding_sessions": HOLDING_SESSIONS,
            "slot_count": SLOT_COUNT,
            "events_per_slot": EVENTS_PER_SLOT,
            "slot_initial_weight": 1.0 / SLOT_COUNT,
            "assignment_rule": "event_index_mod_5",
            "primary_round_trip_cost_bps": PRIMARY_ROUND_TRIP_COST_BPS,
            "cost_stress_bps": list(COST_STRESS_BPS),
            "event_path_ids": list(EVENT_PATH_IDS),
            "buy_hold_ids": list(BUY_HOLD_IDS),
            "shy_daily_return_as_excess_proxy": True,
            "fractional_shares_research_only": True,
            "leverage_allowed": False,
        },
        "reconstruction": reconstruction,
        "calendar_integrity": {
            "sessions": len(index),
            "first_date": index[0].strftime("%Y-%m-%d"),
            "last_date": index[-1].strftime("%Y-%m-%d"),
            "maximum_event_terminal_residual": max(primary_paths[path_id]["maximum_event_terminal_residual"] for path_id in EVENT_PATH_IDS),
            "maximum_daily_identity_residual": max(primary_paths[path_id]["maximum_daily_identity_residual"] for path_id in EVENT_PATH_IDS),
            "minimum_cash_value": min(metrics[path_id]["minimum_cash_value"] for path_id in EVENT_PATH_IDS),
            "maximum_exposure": max(metrics[path_id]["maximum_exposure"] for path_id in EVENT_PATH_IDS),
        },
        "paths": metrics,
        "family": {
            "size": len(comparisons),
            "candidate_id": "top7_five_slot",
            "comparisons": comparisons,
            "common_bootstrap": bootstrap,
            "global_search_trials": GLOBAL_SEARCH_TRIALS,
        },
        "stresses": {
            "best_three_years_removed": tail_stress,
            "crisis_years": crisis,
            "costs": cost_stresses,
        },
        "gates": gates,
        "gate_summary": gate_summary,
        "controls": controls,
        "control_summary": control_summary,
        "attacks": attacks,
        "attack_summary": attack_summary,
        "calendar_rows": calendar_rows,
        "decision": {
            "can_promote_from_this_round": False,
            "not_rejected_by_round29": gate_summary["all_passed"],
            "new_strategy_created": False,
            "formal_readiness": "1/18",
            "point_in_time_readiness": "1/20",
            "qualified_provider_packages": 0,
            "formal_strategy_runs": 0,
            "paper_status": "all_cash_not_started",
            "paper_positions": 0,
            "real_money_action_usd": 0,
            "us1000_is_reader_example_only": True,
            "formal_global_search_trials": GLOBAL_SEARCH_TRIALS,
        },
    }
