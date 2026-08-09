from __future__ import annotations

import hashlib
import json
import math
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from . import calendar_capital_accounting as round29

SCHEMA_VERSION = 1
RESEARCH_ROUND = 38
PROTOCOL_PATH = "docs/SHORT_TERM_MULTI_WINDOW_RESONANCE_PROTOCOL.md"
PROTOCOL_SHA256 = "3c24cecf62b2a7faf8cd5d233377673ec4b104dacfdd1b91f4febc0dc1f0d179"
PROTOCOL_COMMIT = "9d937340356c7352f67f61a484827a65506c216b"

ROUND30_RECEIPT_PATH = "artifacts/short_term_qqq_replacement_overlay_validation.json"
ROUND30_RECEIPT_SHA256 = "ed9b733f8926fcd7ed5a9a061c98a2dfcc05d0b1e82a9ef12f25541b758cd8d8"
ROUND29_RECEIPT_PATH = "artifacts/short_term_calendar_capital_accounting_validation.json"
ROUND29_RECEIPT_SHA256 = "a35a3fa21b491250a3cce23e627a26e67a0d3219f796af4e2ec739d9f07e8e36"
EVENT_RECEIPT_PATH = round29.EVENT_RECEIPT_PATH
EVENT_RECEIPT_SHA256 = round29.EVENT_RECEIPT_SHA256
SNAPSHOT_PATH = round29.SNAPSHOT_PATH
SNAPSHOT_SHA256 = round29.SNAPSHOT_SHA256
PANEL_SHA256 = round29.PANEL_SHA256
WATCHLIST_PATH = round29.WATCHLIST_PATH
WATCHLIST_SHA256 = round29.WATCHLIST_SHA256
REFERENCE_COMMITS = (
    ("tst_wocker", "1af28a002d6f797399e94fa869808fef006a6ce1"),
    ("tw-block-warrant", "5ba80c7736a69effeabf564225d679ddf75f8ba0"),
    ("tst_wocker_filter_lab", "06c87b7a1735877c9ccbab3a339c1742814a5058"),
)

EXPECTED_EVENTS = round29.EXPECTED_EVENTS
EXPECTED_COHORT = round29.EXPECTED_COHORT
FIRST_SIGNAL_DATE = round29.FIRST_SIGNAL_DATE
FIRST_ENTRY_DATE = round29.FIRST_ENTRY_DATE
LAST_SIGNAL_DATE = round29.LAST_SIGNAL_DATE
LAST_EXIT_DATE = round29.LAST_EXIT_DATE
MOMENTUM_WINDOWS = (5, 10, 15, 20)
TOP_K = 7
RESONANCE_MINIMUM = 3
STOCK_SUBSLOTS = 7
ENTRY_DELAY = round29.ENTRY_DELAY
HOLDING_SESSIONS = round29.HOLDING_SESSIONS
SLOT_COUNT = round29.SLOT_COUNT
EVENTS_PER_SLOT = round29.EVENTS_PER_SLOT
ASSIGNMENT_SHA256 = round29.ASSIGNMENT_SHA256
INITIAL_CAPITAL_USD = round29.INITIAL_CAPITAL_USD
PRIMARY_ASSET_ROUND_TRIP_BPS = 20
COST_STRESS_BPS = (50, 100)
RECONSTRUCTION_TOLERANCE = 1e-12

OVERLAY_PATH_IDS = (
    "resonance3_qqq_overlay",
    "matched_20d_qqq_overlay",
    "matched_eligible_qqq_overlay",
    "matched_complete_qqq_overlay",
    "original_top7_qqq_overlay",
    "matched_qqq_switch_placebo",
)
PATH_IDS = (*OVERLAY_PATH_IDS, "qqq_buy_hold", "spy_buy_hold", "shy_buy_hold")
FAMILY_BASELINE_IDS = PATH_IDS[1:]
PATH_LABELS = {
    "resonance3_qqq_overlay": "四窗三重共振／QQQ 部分替換",
    "matched_20d_qqq_overlay": "相同比例 20 日排名／QQQ 部分替換",
    "matched_eligible_qqq_overlay": "相同比例合資格池／QQQ 部分替換",
    "matched_complete_qqq_overlay": "相同比例完整現時股池／QQQ 部分替換",
    "original_top7_qqq_overlay": "第 30 輪原 Top-7／QQQ 全替換",
    "matched_qqq_switch_placebo": "相同比例 QQQ 換手 placebo",
    "qqq_buy_hold": "QQQ 買入並持有",
    "spy_buy_hold": "SPY 買入並持有",
    "shy_buy_hold": "SHY 買入並持有",
}

HAC_LAG = 20
FAMILY_ALPHA = 0.05
BOOTSTRAP_BLOCK_SESSIONS = 63
BOOTSTRAP_PATHS = 20_000
BOOTSTRAP_SEED = 38_202_608
GLOBAL_SEARCH_TRIALS = 6_229
FIRST_HALF_END = round29.FIRST_HALF_END
SECOND_HALF_START = round29.SECOND_HALF_START
CRISIS_YEARS = round29.CRISIS_YEARS
BEST_YEAR_REMOVAL_COUNT = 3
FAVORABLE_EVENT_REMOVAL_COUNT = 46


class MultiWindowResonanceError(ValueError):
    def __init__(self, code: str, detail: str):
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}")


def _fail(code: str, detail: str) -> None:
    raise MultiWindowResonanceError(code, detail)


@dataclass(frozen=True)
class FrozenMultiWindowResonanceContract:
    protocol_sha256: str = PROTOCOL_SHA256
    protocol_commit: str = PROTOCOL_COMMIT
    round30_receipt_sha256: str = ROUND30_RECEIPT_SHA256
    round29_receipt_sha256: str = ROUND29_RECEIPT_SHA256
    event_receipt_sha256: str = EVENT_RECEIPT_SHA256
    snapshot_sha256: str = SNAPSHOT_SHA256
    panel_sha256: str = PANEL_SHA256
    watchlist_sha256: str = WATCHLIST_SHA256
    reference_commits: tuple[tuple[str, str], ...] = REFERENCE_COMMITS
    expected_events: int = EXPECTED_EVENTS
    expected_cohort: int = EXPECTED_COHORT
    momentum_windows: tuple[int, ...] = MOMENTUM_WINDOWS
    top_k: int = TOP_K
    resonance_minimum: int = RESONANCE_MINIMUM
    rank_tie_break: str = "resonance_desc_rank_sum_asc_ticker_asc"
    percentile_display_only: bool = True
    stock_subslots: int = STOCK_SUBSLOTS
    partial_allocation_rule: str = "n_over_7_remainder_qqq"
    entry_delay: int = ENTRY_DELAY
    holding_sessions: int = HOLDING_SESSIONS
    slot_count: int = SLOT_COUNT
    events_per_slot: int = EVENTS_PER_SLOT
    assignment_sha256: str = ASSIGNMENT_SHA256
    inactive_asset: str = "QQQ"
    primary_asset_round_trip_bps: int = PRIMARY_ASSET_ROUND_TRIP_BPS
    cost_stress_bps: tuple[int, ...] = COST_STRESS_BPS
    four_legs_per_switched_subslot: bool = True
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
    favorable_event_removal_count: int = FAVORABLE_EVENT_REMOVAL_COUNT
    formal_readiness: str = "1/18"
    point_in_time_readiness: str = "1/20"
    qualified_provider_packages: int = 0
    formal_strategy_runs: int = 0
    current_identifiers_only: bool = True
    paper_authorized: bool = False
    real_money_authorized: bool = False


FROZEN_CONTRACT = FrozenMultiWindowResonanceContract()


def validate_multi_window_resonance_contract(
    contract: FrozenMultiWindowResonanceContract,
) -> None:
    checks = (
        (contract.protocol_sha256 == PROTOCOL_SHA256, "resonance_protocol_hash_mismatch", "協議 SHA 漂移"),
        (contract.protocol_commit == PROTOCOL_COMMIT, "resonance_protocol_commit_mismatch", "協議 commit 漂移"),
        (contract.round30_receipt_sha256 == ROUND30_RECEIPT_SHA256, "resonance_round30_receipt_mismatch", "第 30 輪收據漂移"),
        (contract.round29_receipt_sha256 == ROUND29_RECEIPT_SHA256, "resonance_round29_receipt_mismatch", "第 29 輪收據漂移"),
        (contract.event_receipt_sha256 == EVENT_RECEIPT_SHA256, "resonance_event_receipt_mismatch", "原始事件收據漂移"),
        (contract.snapshot_sha256 == SNAPSHOT_SHA256, "resonance_snapshot_mismatch", "行情 archive 漂移"),
        (contract.panel_sha256 == PANEL_SHA256, "resonance_panel_mismatch", "panel fingerprint 漂移"),
        (contract.watchlist_sha256 == WATCHLIST_SHA256, "resonance_watchlist_mismatch", "watchlist 漂移"),
        (contract.reference_commits == REFERENCE_COMMITS, "resonance_reference_mismatch", "參考 commit 漂移"),
        (contract.expected_events == EXPECTED_EVENTS, "resonance_event_count_mismatch", "事件數漂移"),
        (contract.expected_cohort == EXPECTED_COHORT, "resonance_cohort_mismatch", "cohort 漂移"),
        (contract.momentum_windows == MOMENTUM_WINDOWS, "resonance_windows_mismatch", "動量窗口漂移"),
        (contract.top_k == TOP_K, "resonance_top_k_mismatch", "Top-K 漂移"),
        (contract.resonance_minimum == RESONANCE_MINIMUM, "resonance_threshold_mismatch", "共振門檻漂移"),
        (contract.rank_tie_break == "resonance_desc_rank_sum_asc_ticker_asc", "resonance_rank_rule_mismatch", "rank-sum 或 tie-break 漂移"),
        (contract.percentile_display_only, "resonance_percentile_scope_mismatch", "百分位不再只作展示"),
        (contract.stock_subslots == STOCK_SUBSLOTS, "resonance_subslots_mismatch", "七分注漂移"),
        (contract.partial_allocation_rule == "n_over_7_remainder_qqq", "resonance_allocation_mismatch", "N/7 分注漂移"),
        (contract.entry_delay == ENTRY_DELAY and contract.holding_sessions == HOLDING_SESSIONS, "resonance_execution_clock_mismatch", "成交時鐘漂移"),
        (contract.slot_count == SLOT_COUNT and contract.events_per_slot == EVENTS_PER_SLOT and contract.assignment_sha256 == ASSIGNMENT_SHA256, "resonance_assignment_mismatch", "五槽 assignment 漂移"),
        (contract.inactive_asset == "QQQ", "resonance_inactive_asset_mismatch", "底倉漂移"),
        (contract.primary_asset_round_trip_bps == 20 and contract.cost_stress_bps == (50, 100), "resonance_cost_mismatch", "成本漂移"),
        (contract.four_legs_per_switched_subslot, "resonance_leg_mismatch", "四腿成本取消"),
        (contract.path_ids == PATH_IDS, "resonance_path_family_mismatch", "九路徑漂移"),
        (contract.family_baseline_ids == FAMILY_BASELINE_IDS, "resonance_hypothesis_family_mismatch", "八假說 family 漂移"),
        (contract.shy_excess_proxy, "resonance_shy_proxy_mismatch", "SHY excess 取消"),
        (contract.hac_lag == 20 and contract.family_alpha == 0.05, "resonance_statistical_mismatch", "NW lag 或 alpha 漂移"),
        (contract.bootstrap_block_sessions == 63 and contract.bootstrap_paths == 20_000 and contract.bootstrap_seed == BOOTSTRAP_SEED and contract.common_bootstrap_indices and contract.centered_under_null, "resonance_bootstrap_mismatch", "bootstrap 漂移"),
        (contract.global_search_trials == GLOBAL_SEARCH_TRIALS, "resonance_global_trials_mismatch", "全專案 trials 漂移"),
        (contract.first_half_end == "2016-07-29" and contract.second_half_start == "2016-08-01", "resonance_half_clock_mismatch", "半期漂移"),
        (contract.crisis_years == (2008, 2020, 2022), "resonance_crisis_mismatch", "危機期漂移"),
        (contract.best_year_removal_count == 3, "resonance_best_year_mismatch", "最佳年份壓力漂移"),
        (contract.favorable_event_removal_count == 46, "resonance_tail_mismatch", "尾部移除漂移"),
        (contract.formal_readiness == "1/18" and contract.point_in_time_readiness == "1/20" and contract.qualified_provider_packages == 0 and contract.formal_strategy_runs == 0, "resonance_identity_mismatch", "正式身份漂移"),
        (contract.current_identifiers_only, "resonance_identifier_scope_mismatch", "survivor 警告取消"),
        (not contract.paper_authorized, "resonance_paper_boundary_breached", "越權啟動 Paper"),
        (not contract.real_money_authorized, "resonance_real_money_boundary_breached", "越權啟動實金"),
    )
    for passed, code, detail in checks:
        if not passed:
            _fail(code, detail)


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _symbols_hash(symbols: list[str]) -> str:
    return hashlib.sha256(json.dumps(symbols, separators=(",", ":")).encode()).hexdigest()


def _build_resonance_events(panel: Any, events: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    cohort = list(panel.close.columns.intersection(events[0]["gross"].index))
    momentum = {window: panel.close[cohort].pct_change(window, fill_method=None) for window in MOMENTUM_WINDOWS}
    receipts: list[dict[str, Any]] = []
    for event in events:
        eligible = list(event["eligible"])
        date = event["signal_date"]
        ranked: dict[int, list[str]] = {}
        ranks: dict[int, dict[str, int]] = {}
        for window in MOMENTUM_WINDOWS:
            ranked[window] = sorted(eligible, key=lambda ticker: (-float(momentum[window].loc[date, ticker]), ticker))
            ranks[window] = {ticker: rank for rank, ticker in enumerate(ranked[window])}
        resonance = {ticker: sum(ticker in ranked[window][:TOP_K] for window in MOMENTUM_WINDOWS) for ticker in eligible}
        rank_sum = {ticker: sum(ranks[window][ticker] for window in MOMENTUM_WINDOWS) for ticker in eligible}
        selected = sorted(
            (ticker for ticker in eligible if resonance[ticker] >= RESONANCE_MINIMUM),
            key=lambda ticker: (-resonance[ticker], rank_sum[ticker], ticker),
        )[:TOP_K]
        n = len(selected)
        event["window_ranked"] = ranked
        event["resonance_count"] = resonance
        event["rank_sum"] = rank_sum
        event["resonance_selected"] = selected
        event["candidate_count"] = n
        event["stock_target_fraction"] = n / STOCK_SUBSLOTS
        event["qqq_target_fraction"] = 1.0 - n / STOCK_SUBSLOTS
        details = []
        for ticker in selected:
            denominator = len(eligible) - 1
            percentiles = {
                str(window): ((len(eligible) - ranks[window][ticker] - 1) / denominator if denominator else 1.0)
                for window in MOMENTUM_WINDOWS
            }
            details.append(
                {
                    "ticker": ticker,
                    "resonance_count": resonance[ticker],
                    "rank_sum": rank_sum[ticker],
                    "ranks": {str(window): ranks[window][ticker] for window in MOMENTUM_WINDOWS},
                    "percentiles": percentiles,
                    "mean_percentile": float(np.mean(list(percentiles.values()))),
                }
            )
        receipts.append(
            {
                "event_index": event["event_index"],
                "slot": event["slot"],
                "signal_date": date.strftime("%Y-%m-%d"),
                "entry_date": event["entry_date"].strftime("%Y-%m-%d"),
                "exit_date": event["exit_date"].strftime("%Y-%m-%d"),
                "eligible_count": len(eligible),
                "eligible_sha256": _symbols_hash(eligible),
                "window_top7": {str(window): ranked[window][:TOP_K] for window in MOMENTUM_WINDOWS},
                "window_ranked_sha256": {str(window): _symbols_hash(ranked[window]) for window in MOMENTUM_WINDOWS},
                "candidate_count": n,
                "selected": selected,
                "selected_sha256": _symbols_hash(selected),
                "selected_details": details,
                "stock_target_fraction": n / STOCK_SUBSLOTS,
                "qqq_target_fraction": 1.0 - n / STOCK_SUBSLOTS,
            }
        )
    return events, receipts


def _weights_for_path(event: dict[str, Any], path_id: str, cohort: list[str]) -> dict[str, float]:
    n = int(event["candidate_count"])
    fraction = n / STOCK_SUBSLOTS
    if path_id == "resonance3_qqq_overlay":
        return {ticker: 1.0 / STOCK_SUBSLOTS for ticker in event["resonance_selected"]}
    if path_id == "matched_20d_qqq_overlay":
        return {ticker: 1.0 / STOCK_SUBSLOTS for ticker in event["ranked"][:n]}
    if path_id == "matched_eligible_qqq_overlay":
        return {ticker: fraction / len(event["eligible"]) for ticker in event["eligible"]}
    if path_id == "matched_complete_qqq_overlay":
        return {ticker: fraction / len(cohort) for ticker in cohort}
    if path_id == "original_top7_qqq_overlay":
        return {ticker: 1.0 / STOCK_SUBSLOTS for ticker in event["selected"]}
    if path_id == "matched_qqq_switch_placebo":
        return {"QQQ": fraction} if fraction else {}
    _fail("resonance_path_family_mismatch", f"未知路徑 {path_id}")


def _build_partial_overlay_path(
    panel: Any,
    cohort: list[str],
    events: list[dict[str, Any]],
    path_id: str,
    asset_round_trip_bps: int,
    excluded_event_indices: frozenset[int] = frozenset(),
) -> dict[str, Any]:
    index = panel.close.loc[FIRST_SIGNAL_DATE:LAST_EXIT_DATE].index
    first_entry = pd.Timestamp(FIRST_ENTRY_DATE)
    last_exit = pd.Timestamp(LAST_EXIT_DATE)
    first_position = int(index.get_loc(first_entry))
    side_cost = asset_round_trip_bps / 20_000.0
    slot_initial = 1.0 / SLOT_COUNT
    slot_values: list[pd.Series] = []
    stock_values: list[pd.Series] = []
    qqq_values: list[pd.Series] = []
    traded_notional = pd.Series(0.0, index=index)
    cost_paid = pd.Series(0.0, index=index)
    cumulative_legs = pd.Series(0, index=index, dtype=int)
    legs_so_far = 0

    def charge(value: float, date: pd.Timestamp) -> float:
        nonlocal legs_so_far
        if value <= 0.0:
            return value
        traded_notional.loc[date] += value
        paid = value * side_cost
        cost_paid.loc[date] += paid
        legs_so_far += 1
        return value - paid

    for slot in range(SLOT_COUNT):
        values = pd.Series(np.nan, index=index)
        stock_driver = pd.Series(0.0, index=index)
        qqq_driver = pd.Series(0.0, index=index)
        values.iloc[:first_position] = slot_initial
        slot_events = [event for event in events if event["slot"] == slot and event["event_index"] not in excluded_event_indices]
        cursor = 0
        current: dict[str, Any] | None = None
        qqq_component = 0.0
        stock_components: dict[str, float] = {}
        for position in range(first_position, len(index)):
            date = index[position]
            previous_date = index[position - 1]
            next_event = slot_events[cursor] if cursor < len(slot_events) else None
            if position == first_position:
                weights = _weights_for_path(next_event, path_id, cohort) if next_event is not None and next_event["entry_date"] == date else {}
                fraction = float(sum(weights.values()))
                qqq_component = charge(slot_initial * (1.0 - fraction), date)
                stock_components = {ticker: charge(slot_initial * weight, date) for ticker, weight in weights.items()}
                qqq_component *= float(panel.close.loc[date, "QQQ"] / panel.open.loc[date, "QQQ"])
                stock_components = {ticker: value * float(panel.close.loc[date, ticker] / panel.open.loc[date, ticker]) for ticker, value in stock_components.items()}
                if weights:
                    current = next_event
                elif next_event is not None and next_event["entry_date"] == date:
                    current = next_event
                if current is None and not weights:
                    # The inactive slot bought QQQ with its whole initial capital.
                    if qqq_component == 0.0:
                        qqq_component = charge(slot_initial, date) * float(panel.close.loc[date, "QQQ"] / panel.open.loc[date, "QQQ"])
                elif fraction == 0.0:
                    # A zero-candidate event still leaves the whole slot in QQQ.
                    if qqq_component == 0.0:
                        qqq_component = charge(slot_initial, date) * float(panel.close.loc[date, "QQQ"] / panel.open.loc[date, "QQQ"])
            elif current is None:
                qqq_component *= float(panel.open.loc[date, "QQQ"] / panel.close.loc[previous_date, "QQQ"] if next_event is not None and next_event["entry_date"] == date else panel.close.loc[date, "QQQ"] / panel.close.loc[previous_date, "QQQ"])
                if next_event is not None and next_event["entry_date"] == date:
                    weights = _weights_for_path(next_event, path_id, cohort)
                    fraction = float(sum(weights.values()))
                    sold = charge(qqq_component * fraction, date)
                    qqq_component *= 1.0 - fraction
                    stock_budget = charge(sold, date) if sold > 0.0 else 0.0
                    stock_components = {ticker: stock_budget * weight / fraction for ticker, weight in weights.items()} if fraction else {}
                    stock_components = {ticker: value * float(panel.close.loc[date, ticker] / panel.open.loc[date, ticker]) for ticker, value in stock_components.items()}
                    qqq_component *= float(panel.close.loc[date, "QQQ"] / panel.open.loc[date, "QQQ"])
                    current = next_event
            else:
                qqq_component *= float(panel.close.loc[date, "QQQ"] / panel.close.loc[previous_date, "QQQ"])
                stock_components = {ticker: value * float(panel.close.loc[date, ticker] / panel.close.loc[previous_date, ticker]) for ticker, value in stock_components.items()}

            if current is not None and current["exit_date"] == date:
                proceeds = sum(charge(value, date) for value in stock_components.values())
                stock_components = {}
                if date == last_exit:
                    qqq_component = charge(qqq_component, date)
                    qqq_component += proceeds
                else:
                    qqq_component += charge(proceeds, date) if proceeds > 0.0 else 0.0
                current = None
                cursor += 1
            elif date == last_exit and current is None:
                qqq_component = charge(qqq_component, date)

            total_stock = float(sum(stock_components.values()))
            total = qqq_component + total_stock
            if not np.isfinite(total) or total <= 0.0:
                _fail("resonance_daily_identity_mismatch", "槽位資產非正或非有限")
            values.loc[date] = total
            stock_driver.loc[date] = total_stock
            qqq_driver.loc[date] = qqq_component
            cumulative_legs.loc[date] = legs_so_far
        if current is not None or cursor != len(slot_events) or values.isna().any():
            _fail("resonance_event_clock_mismatch", "事件未完整進出或日線缺值")
        slot_values.append(values)
        stock_values.append(stock_driver)
        qqq_values.append(qqq_driver)

    slot_frame = pd.concat(slot_values, axis=1)
    stock_frame = pd.concat(stock_values, axis=1)
    qqq_frame = pd.concat(qqq_values, axis=1)
    equity = slot_frame.sum(axis=1)
    stock_driver_value = stock_frame.sum(axis=1)
    qqq_driver_value = qqq_frame.sum(axis=1)
    invested = pd.Series(False, index=index)
    invested.loc[first_entry:last_exit] = True
    cash_value = equity.where(~invested, 0.0)
    exposure = invested.astype(float)
    returns = equity.pct_change(fill_method=None).fillna(0.0)
    turnover = traded_notional.div(equity.shift(1).fillna(1.0))
    identity = float((equity - slot_frame.sum(axis=1)).abs().max())
    driver_identity = float((equity - stock_driver_value - qqq_driver_value - cash_value).abs().max())
    cost_identity = float((cost_paid - traded_notional * side_cost).abs().max())
    return {
        "equity": equity,
        "returns": returns,
        "turnover": turnover,
        "exposure": exposure,
        "cash_value": cash_value,
        "slot_values": slot_frame,
        "stock_driver_value": stock_driver_value,
        "qqq_driver_value": qqq_driver_value,
        "stock_driver_fraction": stock_driver_value.div(equity),
        "qqq_driver_fraction": qqq_driver_value.div(equity),
        "traded_notional": traded_notional,
        "cost_paid": cost_paid,
        "total_legs": int(legs_so_far),
        "maximum_daily_identity_residual": identity,
        "maximum_driver_identity_residual": driver_identity,
        "maximum_cost_identity_residual": cost_identity,
    }


def _build_analytical_qqq_placebo(
    panel: Any,
    events: list[dict[str, Any]],
    asset_round_trip_bps: int,
) -> pd.Series:
    """Independently reconstruct QQQ price times the mandated partial-switch costs."""
    index = panel.close.loc[FIRST_SIGNAL_DATE:LAST_EXIT_DATE].index
    first_entry = pd.Timestamp(FIRST_ENTRY_DATE)
    last_exit = pd.Timestamp(LAST_EXIT_DATE)
    first_position = int(index.get_loc(first_entry))
    side_cost = asset_round_trip_bps / 20_000.0
    slot_series: list[pd.Series] = []
    for slot in range(SLOT_COUNT):
        values = pd.Series(np.nan, index=index)
        values.iloc[:first_position] = 1.0 / SLOT_COUNT
        slot_events = [event for event in events if event["slot"] == slot]
        cursor = 0
        current: dict[str, Any] | None = None
        qqq_component = 0.0
        switched_component = 0.0
        for position in range(first_position, len(index)):
            date = index[position]
            previous_date = index[position - 1]
            next_event = slot_events[cursor] if cursor < len(slot_events) else None
            if position == first_position:
                fraction = (
                    float(next_event["stock_target_fraction"])
                    if next_event is not None and next_event["entry_date"] == date
                    else 0.0
                )
                qqq_component = (1.0 / SLOT_COUNT) * (1.0 - fraction) * (1.0 - side_cost)
                switched_component = (1.0 / SLOT_COUNT) * fraction * (1.0 - side_cost)
                gross = float(panel.close.loc[date, "QQQ"] / panel.open.loc[date, "QQQ"])
                qqq_component *= gross
                switched_component *= gross
                if next_event is not None and next_event["entry_date"] == date:
                    current = next_event
            elif current is None:
                if next_event is not None and next_event["entry_date"] == date:
                    open_ratio = float(panel.open.loc[date, "QQQ"] / panel.close.loc[previous_date, "QQQ"])
                    qqq_component *= open_ratio
                    fraction = float(next_event["stock_target_fraction"])
                    sold = qqq_component * fraction
                    qqq_component *= 1.0 - fraction
                    switched_component = sold * (1.0 - side_cost) ** 2
                    close_ratio = float(panel.close.loc[date, "QQQ"] / panel.open.loc[date, "QQQ"])
                    qqq_component *= close_ratio
                    switched_component *= close_ratio
                    current = next_event
                else:
                    qqq_component *= float(panel.close.loc[date, "QQQ"] / panel.close.loc[previous_date, "QQQ"])
            else:
                daily_ratio = float(panel.close.loc[date, "QQQ"] / panel.close.loc[previous_date, "QQQ"])
                qqq_component *= daily_ratio
                switched_component *= daily_ratio

            if current is not None and current["exit_date"] == date:
                switched_component *= 1.0 - side_cost
                if date != last_exit:
                    switched_component *= 1.0 - side_cost
                else:
                    qqq_component *= 1.0 - side_cost
                qqq_component += switched_component
                switched_component = 0.0
                current = None
                cursor += 1
            elif date == last_exit and current is None:
                qqq_component *= 1.0 - side_cost

            values.loc[date] = qqq_component + switched_component
        if current is not None or cursor != len(slot_events) or values.isna().any():
            _fail("resonance_placebo_identity_mismatch", "獨立 placebo 事件時鐘不完整")
        slot_series.append(values)
    return pd.concat(slot_series, axis=1).sum(axis=1)


def _common_bootstrap(matrix: np.ndarray, observed_t: np.ndarray, standard_errors: np.ndarray) -> dict[str, Any]:
    centered = matrix - matrix.mean(axis=0, keepdims=True)
    if not np.allclose(centered.mean(axis=0), 0.0, atol=1e-15) or (standard_errors <= 0.0).any():
        _fail("resonance_bootstrap_mismatch", "bootstrap 去中心或標準誤失敗")
    rows = len(matrix)
    blocks = math.ceil(rows / BOOTSTRAP_BLOCK_SESSIONS)
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    starts = rng.integers(0, rows, size=(BOOTSTRAP_PATHS, blocks), dtype=np.int64)
    offsets = np.arange(BOOTSTRAP_BLOCK_SESSIONS, dtype=np.int64)
    max_abs = np.empty(BOOTSTRAP_PATHS)
    for start in range(0, BOOTSTRAP_PATHS, 100):
        stop = min(BOOTSTRAP_PATHS, start + 100)
        indices = (starts[start:stop, :, None] + offsets[None, None, :]) % rows
        indices = indices.reshape(stop - start, -1)[:, :rows]
        means = centered[indices].mean(axis=1)
        max_abs[start:stop] = np.abs(means / standard_errors).max(axis=1)
    p_values = (1.0 + (max_abs[:, None] >= np.abs(observed_t)[None, :]).sum(axis=0)) / (BOOTSTRAP_PATHS + 1.0)
    return {
        "block_sessions": BOOTSTRAP_BLOCK_SESSIONS,
        "paths": BOOTSTRAP_PATHS,
        "seed": BOOTSTRAP_SEED,
        "circular": True,
        "common_indices": True,
        "centered_under_null": True,
        "blocks_per_path": blocks,
        "start_index_sha256": hashlib.sha256(starts.tobytes()).hexdigest(),
        "single_step_max_t_p": p_values.tolist(),
    }


def _metrics(path: dict[str, Any], shy_proxy: pd.Series, path_id: str, cost_bps: int) -> dict[str, Any]:
    result = round29._path_metrics(path, shy_proxy)
    result.update(
        {
            "path_id": path_id,
            "label": PATH_LABELS[path_id],
            "asset_round_trip_cost_bps": cost_bps,
            "cost_charge_operations": int(path.get("total_legs", 2)),
            "total_cost_usd": float(INITIAL_CAPITAL_USD * path.get("cost_paid", pd.Series([0.0])).sum()),
            "average_stock_driver_fraction": float(path.get("stock_driver_fraction", pd.Series([0.0])).mean()),
            "average_qqq_driver_fraction": float(path.get("qqq_driver_fraction", pd.Series([0.0])).mean()),
        }
    )
    return result


def _contract_attacks() -> list[tuple[str, str, str, Callable[[FrozenMultiWindowResonanceContract], FrozenMultiWindowResonanceContract]]]:
    specs = [
        ("protocol_sha256", "0" * 64, "resonance_protocol_hash_mismatch"), ("protocol_commit", "0" * 40, "resonance_protocol_commit_mismatch"),
        ("round30_receipt_sha256", "0" * 64, "resonance_round30_receipt_mismatch"), ("round29_receipt_sha256", "0" * 64, "resonance_round29_receipt_mismatch"),
        ("event_receipt_sha256", "0" * 64, "resonance_event_receipt_mismatch"), ("snapshot_sha256", "0" * 64, "resonance_snapshot_mismatch"),
        ("panel_sha256", "0" * 64, "resonance_panel_mismatch"), ("watchlist_sha256", "0" * 64, "resonance_watchlist_mismatch"),
        ("reference_commits", (), "resonance_reference_mismatch"), ("expected_events", 904, "resonance_event_count_mismatch"),
        ("expected_cohort", 24, "resonance_cohort_mismatch"), ("momentum_windows", (5, 10, 20), "resonance_windows_mismatch"),
        ("top_k", 5, "resonance_top_k_mismatch"), ("resonance_minimum", 2, "resonance_threshold_mismatch"),
        ("rank_tie_break", "ticker", "resonance_rank_rule_mismatch"), ("percentile_display_only", False, "resonance_percentile_scope_mismatch"),
        ("stock_subslots", 5, "resonance_subslots_mismatch"), ("partial_allocation_rule", "reweight", "resonance_allocation_mismatch"),
        ("holding_sessions", 10, "resonance_execution_clock_mismatch"), ("slot_count", 4, "resonance_assignment_mismatch"),
        ("inactive_asset", "SPY", "resonance_inactive_asset_mismatch"), ("primary_asset_round_trip_bps", 10, "resonance_cost_mismatch"),
        ("four_legs_per_switched_subslot", False, "resonance_leg_mismatch"), ("path_ids", PATH_IDS[:-1], "resonance_path_family_mismatch"),
        ("family_baseline_ids", FAMILY_BASELINE_IDS[:-1], "resonance_hypothesis_family_mismatch"), ("shy_excess_proxy", False, "resonance_shy_proxy_mismatch"),
        ("hac_lag", 4, "resonance_statistical_mismatch"), ("bootstrap_block_sessions", 20, "resonance_bootstrap_mismatch"),
        ("bootstrap_paths", 1_000, "resonance_bootstrap_mismatch"), ("bootstrap_seed", 1, "resonance_bootstrap_mismatch"),
        ("global_search_trials", 8, "resonance_global_trials_mismatch"), ("second_half_start", "2017-01-01", "resonance_half_clock_mismatch"),
        ("crisis_years", (2008, 2020), "resonance_crisis_mismatch"), ("best_year_removal_count", 2, "resonance_best_year_mismatch"),
        ("favorable_event_removal_count", 20, "resonance_tail_mismatch"), ("formal_readiness", "18/18", "resonance_identity_mismatch"),
        ("current_identifiers_only", False, "resonance_identifier_scope_mismatch"), ("paper_authorized", True, "resonance_paper_boundary_breached"),
        ("real_money_authorized", True, "resonance_real_money_boundary_breached"),
    ]
    return [(f"{idx:02d}", field, code, lambda c, f=field, v=value: replace(c, **{f: v})) for idx, (field, value, code) in enumerate(specs, 1)]


def run_contract_attacks() -> list[dict[str, Any]]:
    rows = []
    for attack_id, label, expected, mutate in _contract_attacks():
        observed = None
        try:
            validate_multi_window_resonance_contract(mutate(FROZEN_CONTRACT))
        except MultiWindowResonanceError as exc:
            observed = exc.code
        rows.append({"id": attack_id, "label": label, "expected_error_code": expected, "observed_error_code": observed, "rejected": observed == expected})
    return rows


def run_multi_window_resonance(root: str | Path) -> dict[str, Any]:
    root_path = Path(root).resolve()
    contract = FROZEN_CONTRACT
    validate_multi_window_resonance_contract(contract)
    input_hashes = {
        "protocol": _sha256_file(root_path / PROTOCOL_PATH), "round30": _sha256_file(root_path / ROUND30_RECEIPT_PATH),
        "round29": _sha256_file(root_path / ROUND29_RECEIPT_PATH), "event_receipt": _sha256_file(root_path / EVENT_RECEIPT_PATH),
        "snapshot": _sha256_file(root_path / SNAPSHOT_PATH), "watchlist": _sha256_file(root_path / WATCHLIST_PATH),
    }
    expected_hashes = {"protocol": PROTOCOL_SHA256, "round30": ROUND30_RECEIPT_SHA256, "round29": ROUND29_RECEIPT_SHA256, "event_receipt": EVENT_RECEIPT_SHA256, "snapshot": SNAPSHOT_SHA256, "watchlist": WATCHLIST_SHA256}
    if input_hashes != expected_hashes:
        _fail("resonance_input_receipt_mismatch", "固定輸入 hash 漂移")
    panel, cohort, frozen_events, parent_meta = round29._load_inputs(root_path, round29.FROZEN_CONTRACT)
    events, reconstruction = round29._reconstruct_events(panel, cohort, frozen_events)
    input_hashes["panel"] = parent_meta["hashes"]["panel"]
    if input_hashes["panel"] != PANEL_SHA256:
        _fail("resonance_panel_mismatch", "panel fingerprint 漂移")
    events, selection_receipts = _build_resonance_events(panel, events)
    index = panel.close.loc[FIRST_SIGNAL_DATE:LAST_EXIT_DATE].index
    shy_proxy = panel.close.loc[index, "SHY"].pct_change(fill_method=None).fillna(0.0)

    primary_paths = {path_id: _build_partial_overlay_path(panel, cohort, events, path_id, PRIMARY_ASSET_ROUND_TRIP_BPS) for path_id in OVERLAY_PATH_IDS}
    primary_paths.update({ticker.lower() + "_buy_hold": round29._build_buy_hold_path(panel, ticker, PRIMARY_ASSET_ROUND_TRIP_BPS) for ticker in ("QQQ", "SPY", "SHY")})
    zero_paths = {path_id: _build_partial_overlay_path(panel, cohort, events, path_id, 0) for path_id in OVERLAY_PATH_IDS}
    zero_paths.update({ticker.lower() + "_buy_hold": round29._build_buy_hold_path(panel, ticker, 0) for ticker in ("QQQ", "SPY", "SHY")})
    metrics = {}
    for path_id in PATH_IDS:
        row = _metrics(primary_paths[path_id], shy_proxy, path_id, PRIMARY_ASSET_ROUND_TRIP_BPS)
        zero = round29._path_metrics(zero_paths[path_id], shy_proxy)
        row["cost_drag_cagr"] = zero["cagr"] - row["cagr"]
        row["cost_drag_terminal_usd"] = zero["terminal_usd"] - row["terminal_usd"]
        metrics[path_id] = row

    parent = json.loads((root_path / ROUND30_RECEIPT_PATH).read_text(encoding="utf-8"))
    parent_equity = np.asarray([row["equity"]["top7_qqq_overlay"] for row in parent["calendar_rows"]], dtype=float)
    original_residual = float(np.max(np.abs(primary_paths["original_top7_qqq_overlay"]["equity"].to_numpy() - parent_equity)))
    analytical_placebo = _build_analytical_qqq_placebo(
        panel, events, PRIMARY_ASSET_ROUND_TRIP_BPS
    )
    placebo_residual = float(
        np.max(
            np.abs(
                analytical_placebo.to_numpy()
                - primary_paths["matched_qqq_switch_placebo"]["equity"].to_numpy()
            )
        )
    )

    candidate_returns = primary_paths["resonance3_qqq_overlay"]["returns"]
    comparisons, differences, columns = [], {}, []
    for baseline_id in FAMILY_BASELINE_IDS:
        values = (candidate_returns - primary_paths[baseline_id]["returns"]).to_numpy(dtype=float)
        differences[baseline_id] = values
        nw = round29._nw(values)
        comparisons.append({"baseline_id": baseline_id, "baseline_label": PATH_LABELS[baseline_id], "sessions": len(values), "mean_daily_difference": float(values.mean()), "median_daily_difference": float(np.median(values)), "annualized_arithmetic_difference": float(values.mean() * 252), "positive_fraction": float((values > 0).mean()), "newey_west": nw, "raw_normal_p": round29._normal_two_sided_p(float(nw["t_stat"])), "fixed_halves": round29._fixed_halves(values, index), "annual_active_returns": round29._annual_active(values, index)})
        columns.append(values)
    holm = round29._holm_adjust(comparisons)
    observed_t = np.asarray([row["newey_west"]["t_stat"] for row in comparisons])
    standard_errors = np.asarray([row["newey_west"]["standard_error"] for row in comparisons])
    bootstrap = _common_bootstrap(np.column_stack(columns), observed_t, standard_errors)
    for idx, row in enumerate(comparisons):
        row["holm_adjusted_p"] = holm[row["baseline_id"]]
        row["bootstrap_max_t_p"] = bootstrap["single_step_max_t_p"][idx]
        row["family_bonferroni_p"] = min(1.0, row["raw_normal_p"] * len(comparisons))
        row["global_bonferroni_p"] = min(1.0, row["raw_normal_p"] * GLOBAL_SEARCH_TRIALS)
    comparison_by_id = {row["baseline_id"]: row for row in comparisons}

    qqq_annual = comparison_by_id["qqq_buy_hold"]["annual_active_returns"]
    removed_years = [row["year"] for row in sorted(qqq_annual, key=lambda row: (-row["compounded_active_return"], row["year"]))[:3]]
    year_mask = ~np.isin(index.year, removed_years)
    tail_values = differences["qqq_buy_hold"][year_mask]
    best_year_stress = {"removed_years": removed_years, "remaining_sessions": int(year_mask.sum()), "mean_daily_difference": float(tail_values.mean()), "newey_west": round29._nw(tail_values)}

    event_differences = []
    qqq_momentum20 = panel.close["QQQ"].pct_change(20, fill_method=None)
    regimes: dict[str, list[dict[str, float]]] = {"nonnegative": [], "negative": []}
    for event in events:
        weights = _weights_for_path(event, "resonance3_qqq_overlay", cohort)
        difference = sum(weight * (float(event["gross"].loc[ticker]) - float(event["qqq_gross"])) for ticker, weight in weights.items())
        item = {"event_index": event["event_index"], "difference": difference, "candidate_count": event["candidate_count"], "stock_fraction": event["stock_target_fraction"]}
        event_differences.append(item)
        regimes["nonnegative" if float(qqq_momentum20.loc[event["signal_date"]]) >= 0 else "negative"].append(item)
    regime_rows = {key: {"events": len(rows), "average_candidates": float(np.mean([row["candidate_count"] for row in rows])), "average_stock_fraction": float(np.mean([row["stock_fraction"] for row in rows])), "average_event_difference": float(np.mean([row["difference"] for row in rows])), "median_event_difference": float(np.median([row["difference"] for row in rows]))} for key, rows in regimes.items()}
    favorable = sorted(event_differences, key=lambda row: (-row["difference"], row["event_index"]))[:46]
    exclusions = frozenset(row["event_index"] for row in favorable)
    removed_paths = {path_id: _build_partial_overlay_path(panel, cohort, events, path_id, PRIMARY_ASSET_ROUND_TRIP_BPS, exclusions) for path_id in OVERLAY_PATH_IDS}
    removed_metrics = {path_id: round29._path_metrics(path, shy_proxy) for path_id, path in removed_paths.items()}
    removed_diffs = {baseline_id: removed_metrics["resonance3_qqq_overlay"]["cagr"] - (metrics[baseline_id]["cagr"] if baseline_id == "qqq_buy_hold" else removed_metrics[baseline_id]["cagr"]) for baseline_id in ("qqq_buy_hold", "original_top7_qqq_overlay", "matched_20d_qqq_overlay", "matched_eligible_qqq_overlay", "matched_complete_qqq_overlay")}
    removed_stress = {"selection_basis": "highest_preregistered_resonance_minus_qqq_event_gross_difference", "removed_event_count": len(exclusions), "removed_event_indices": sorted(exclusions), "paths": removed_metrics, "candidate_cagr_differences": removed_diffs}
    crises = {str(year): {path_id: round29._crisis_metrics(primary_paths[path_id], year) for path_id in PATH_IDS} for year in CRISIS_YEARS}
    costs = {}
    for cost_bps in COST_STRESS_BPS:
        paths = {path_id: _build_partial_overlay_path(panel, cohort, events, path_id, cost_bps) for path_id in OVERLAY_PATH_IDS}
        paths.update({ticker.lower() + "_buy_hold": round29._build_buy_hold_path(panel, ticker, cost_bps) for ticker in ("QQQ", "SPY", "SHY")})
        rows = {path_id: round29._path_metrics(path, shy_proxy) for path_id, path in paths.items()}
        costs[str(cost_bps)] = {"asset_round_trip_cost_bps": cost_bps, "paths": rows, "candidate_cagr_differences": {baseline_id: rows["resonance3_qqq_overlay"]["cagr"] - rows[baseline_id]["cagr"] for baseline_id in ("qqq_buy_hold", "original_top7_qqq_overlay", "matched_20d_qqq_overlay", "matched_eligible_qqq_overlay", "matched_complete_qqq_overlay")}}

    parent_metric_fields = (
        "total_return", "cagr", "volatility", "shy_excess_sharpe",
        "shy_excess_sortino", "max_drawdown", "calmar", "terminal_usd",
        "annual_turnover",
    )
    parent_stress_metric_residual = max(
        abs(
            float(costs[str(cost_bps)]["paths"]["original_top7_qqq_overlay"][field])
            - float(parent["stresses"]["costs"][str(cost_bps)]["paths"]["top7_qqq_overlay"][field])
        ) / max(
            1.0,
            abs(float(parent["stresses"]["costs"][str(cost_bps)]["paths"]["top7_qqq_overlay"][field])),
        )
        for cost_bps in COST_STRESS_BPS
        for field in parent_metric_fields
    )

    candidate, qqq = metrics["resonance3_qqq_overlay"], metrics["qqq_buy_hold"]
    fair_ids = ("matched_20d_qqq_overlay", "matched_eligible_qqq_overlay", "matched_complete_qqq_overlay")
    half_ids = ("qqq_buy_hold", "original_top7_qqq_overlay", *fair_ids)
    crisis_gate = all(crises[str(year)]["resonance3_qqq_overlay"]["return"] >= crises[str(year)]["qqq_buy_hold"]["return"] and crises[str(year)]["resonance3_qqq_overlay"]["max_drawdown"] >= crises[str(year)]["qqq_buy_hold"]["max_drawdown"] - 0.05 for year in CRISIS_YEARS)
    gates = [
        {"id": "exact_inputs", "passed": True}, {"id": "parent_event_reconstruction", "passed": reconstruction["maximum_event_return_residual"] <= 1e-12 and reconstruction["assignment_sha256"] == ASSIGNMENT_SHA256},
        {"id": "slot_clock", "passed": reconstruction["slot_event_counts"] == [181] * 5 and reconstruction["maximum_concurrent_intervals"] == 5}, {"id": "resonance_ranking", "passed": all(len(row["selected"]) <= 7 and all(detail["resonance_count"] >= 3 for detail in row["selected_details"]) for row in selection_receipts)},
        {"id": "partial_allocations", "passed": all(abs(row["stock_target_fraction"] + row["qqq_target_fraction"] - 1) <= 1e-12 for row in selection_receipts)}, {"id": "daily_identities", "passed": max(max(primary_paths[path_id]["maximum_driver_identity_residual"], primary_paths[path_id]["maximum_cost_identity_residual"]) for path_id in OVERLAY_PATH_IDS) <= 1e-12},
        {"id": "parent_and_placebo_identities", "passed": original_residual <= 1e-12 and parent_stress_metric_residual <= 1e-12 and placebo_residual <= 1e-12}, {"id": "candidate_cagr_vs_qqq", "passed": candidate["cagr"] > qqq["cagr"]},
        {"id": "candidate_terminal_vs_qqq", "passed": candidate["terminal_usd"] > qqq["terminal_usd"]}, {"id": "candidate_sharpe_vs_qqq", "passed": candidate["shy_excess_sharpe"] > qqq["shy_excess_sharpe"]},
        {"id": "candidate_drawdown_vs_qqq", "passed": candidate["max_drawdown"] >= qqq["max_drawdown"] - 0.05}, {"id": "candidate_cagr_vs_original", "passed": candidate["cagr"] > metrics["original_top7_qqq_overlay"]["cagr"]},
        {"id": "candidate_cagr_vs_matched20", "passed": candidate["cagr"] > metrics["matched_20d_qqq_overlay"]["cagr"]}, {"id": "candidate_cagr_vs_equal_baselines", "passed": candidate["cagr"] > metrics["matched_eligible_qqq_overlay"]["cagr"] and candidate["cagr"] > metrics["matched_complete_qqq_overlay"]["cagr"]},
        {"id": "statistical_vs_qqq", "passed": comparison_by_id["qqq_buy_hold"]["mean_daily_difference"] > 0 and comparison_by_id["qqq_buy_hold"]["newey_west"]["t_stat"] >= 1.96 and comparison_by_id["qqq_buy_hold"]["holm_adjusted_p"] <= 0.05 and comparison_by_id["qqq_buy_hold"]["bootstrap_max_t_p"] <= 0.05},
        {"id": "statistical_vs_matched", "passed": all(comparison_by_id[path_id]["mean_daily_difference"] > 0 and comparison_by_id[path_id]["newey_west"]["t_stat"] >= 1.96 and comparison_by_id[path_id]["holm_adjusted_p"] <= 0.05 and comparison_by_id[path_id]["bootstrap_max_t_p"] <= 0.05 for path_id in fair_ids)},
        {"id": "fixed_halves", "passed": all(comparison_by_id[path_id]["fixed_halves"][half]["mean_daily_difference"] > 0 for path_id in half_ids for half in ("first", "second"))},
        {"id": "best_three_years_removed", "passed": best_year_stress["mean_daily_difference"] > 0 and best_year_stress["newey_west"]["t_stat"] >= 1.96},
        {"id": "crisis_and_regimes", "passed": crisis_gate and all(row["average_event_difference"] > 0 for row in regime_rows.values())},
        {"id": "global_cost_and_tail", "passed": comparison_by_id["qqq_buy_hold"]["global_bonferroni_p"] <= 0.05 and all(all(value > 0 for value in row["candidate_cagr_differences"].values()) for row in costs.values()) and all(value > 0 for value in removed_diffs.values())},
    ]
    for gate in gates:
        gate["label"] = gate["id"]
    gate_summary = {"passed": sum(int(row["passed"]) for row in gates), "total": len(gates), "all_passed": all(row["passed"] for row in gates)}

    selected_details = [detail for receipt in selection_receipts for detail in receipt["selected_details"]]
    control_checks = [
        ("protocol_hash_commit", input_hashes["protocol"] == PROTOCOL_SHA256 and contract.protocol_commit == PROTOCOL_COMMIT),
        ("round30_receipt", input_hashes["round30"] == ROUND30_RECEIPT_SHA256),
        ("round29_receipt", input_hashes["round29"] == ROUND29_RECEIPT_SHA256),
        ("event_receipt", input_hashes["event_receipt"] == EVENT_RECEIPT_SHA256),
        ("snapshot", input_hashes["snapshot"] == SNAPSHOT_SHA256),
        ("panel", input_hashes["panel"] == PANEL_SHA256),
        ("watchlist", input_hashes["watchlist"] == WATCHLIST_SHA256),
        ("reference_commits", contract.reference_commits == REFERENCE_COMMITS),
        ("905_events", len(events) == 905 and len(selection_receipts) == 905),
        ("25_cohort", len(cohort) == 25),
        ("four_windows", contract.momentum_windows == (5, 10, 15, 20) and all(set(row["window_top7"]) == {"5", "10", "15", "20"} for row in selection_receipts)),
        ("top7", contract.top_k == 7 and all(all(len(symbols) == 7 for symbols in row["window_top7"].values()) for row in selection_receipts)),
        ("three_window_threshold", contract.resonance_minimum == 3 and all(detail["resonance_count"] >= 3 for detail in selected_details)),
        ("integer_rank_sum", all(isinstance(detail["rank_sum"], int) for detail in selected_details)),
        ("ticker_tie_break", contract.rank_tie_break == "resonance_desc_rank_sum_asc_ticker_asc"),
        ("percentile_display", contract.percentile_display_only and all(0.0 <= value <= 1.0 for detail in selected_details for value in detail["percentiles"].values())),
        ("n_over_7", all(abs(row["stock_target_fraction"] - row["candidate_count"] / 7) <= 1e-12 for row in selection_receipts)),
        ("qqq_remainder", all(abs(row["qqq_target_fraction"] - (1.0 - row["candidate_count"] / 7)) <= 1e-12 for row in selection_receipts)),
        ("d_plus_1", contract.entry_delay == 1 and events[0]["entry_date"] == index[index.get_loc(events[0]["signal_date"]) + 1]),
        ("20_session_hold", contract.holding_sessions == 20 and all(index.get_loc(event["exit_date"]) - index.get_loc(event["entry_date"]) == 19 for event in events)),
        ("five_slots", reconstruction["slot_event_counts"] == [181] * 5 and reconstruction["maximum_concurrent_intervals"] == 5),
        ("assignment_hash", reconstruction["assignment_sha256"] == ASSIGNMENT_SHA256),
        ("qqq_base", contract.inactive_asset == "QQQ"),
        ("four_leg_cost", contract.four_legs_per_switched_subslot and contract.primary_asset_round_trip_bps == 20),
        ("20_50_100_costs", set(costs) == {"50", "100"}),
        ("nine_paths", tuple(primary_paths) == PATH_IDS),
        ("original_parent_identity", original_residual <= 1e-12 and parent_stress_metric_residual <= 1e-12),
        ("placebo_identity", placebo_residual <= 1e-12),
        ("shy_excess", contract.shy_excess_proxy and bool(shy_proxy.notna().all())),
        ("full_exposure", primary_paths["resonance3_qqq_overlay"]["exposure"].loc[FIRST_ENTRY_DATE:].eq(1.0).all()),
        ("no_leverage", candidate["maximum_exposure"] <= 1.0 + 1e-12),
        ("daily_identity", max(primary_paths[path_id]["maximum_driver_identity_residual"] for path_id in OVERLAY_PATH_IDS) <= 1e-12),
        ("actual_notional_cost_identity", max(primary_paths[path_id]["maximum_cost_identity_residual"] for path_id in OVERLAY_PATH_IDS) <= 1e-12),
        ("eight_hypotheses", tuple(row["baseline_id"] for row in comparisons) == FAMILY_BASELINE_IDS),
        ("nw_lag20", all(row["newey_west"]["lag"] == 20 for row in comparisons)),
        ("bootstrap_63_20000", bootstrap["block_sessions"] == 63 and bootstrap["paths"] == 20_000 and bootstrap["seed"] == BOOTSTRAP_SEED and bootstrap["common_indices"]),
        ("fixed_halves", contract.first_half_end == "2016-07-29" and contract.second_half_start == "2016-08-01"),
        ("crisis_years", set(crises) == {"2008", "2020", "2022"}),
        ("known_at_regimes", set(regime_rows) == {"nonnegative", "negative"} and sum(row["events"] for row in regime_rows.values()) == 905),
        ("best_three_years", len(removed_years) == 3),
        ("tail_46", len(exclusions) == 46 and len(removed_paths) == 6),
        ("global_6229", contract.global_search_trials == 6_229),
        ("survivor_identity", contract.current_identifiers_only and contract.formal_readiness == "1/18" and contract.point_in_time_readiness == "1/20" and contract.qualified_provider_packages == 0 and contract.formal_strategy_runs == 0),
        ("paper_zero", not contract.paper_authorized),
        ("real_money_zero", not contract.real_money_authorized),
    ]
    controls = [{"id": f"{idx:02d}", "label": label, "passed": bool(passed)} for idx, (label, passed) in enumerate(control_checks, 1)]
    attacks = run_contract_attacks()
    control_summary = {"passed": sum(int(row["passed"]) for row in controls), "total": len(controls), "all_passed": all(row["passed"] for row in controls)}
    attack_summary = {"rejected": sum(int(row["rejected"]) for row in attacks), "total": len(attacks), "all_rejected": all(row["rejected"] for row in attacks)}
    counts = Counter(event["candidate_count"] for event in events)
    distribution = {"minimum_candidates": min(counts), "maximum_candidates": max(counts), "mean_candidates": float(np.mean([event["candidate_count"] for event in events])), "mean_stock_target_fraction": float(np.mean([event["stock_target_fraction"] for event in events])), "candidate_count_histogram": [{"candidate_count": count, "events": counts.get(count, 0)} for count in range(8)], "resonance_count_occurrences": {str(value): sum(sum(count == value for count in event["resonance_count"].values()) for event in events) for value in range(5)}, "maximum_allocation_residual": max(abs(event["stock_target_fraction"] + event["qqq_target_fraction"] - 1.0) for event in events)}
    calendar_rows = [{"date": date.strftime("%Y-%m-%d"), "equity": {path_id: float(primary_paths[path_id]["equity"].loc[date]) for path_id in PATH_IDS}, "daily_return": {path_id: float(primary_paths[path_id]["returns"].loc[date]) for path_id in PATH_IDS}, "candidate_stock_driver_fraction": float(primary_paths["resonance3_qqq_overlay"]["stock_driver_fraction"].loc[date]), "candidate_qqq_driver_fraction": float(primary_paths["resonance3_qqq_overlay"]["qqq_driver_fraction"].loc[date]), "candidate_cost_paid": float(primary_paths["resonance3_qqq_overlay"]["cost_paid"].loc[date])} for date in index]
    return {
        "schema_version": SCHEMA_VERSION, "research_round": 38, "research_role": "same_seen_survivor_multi_window_resonance_falsification_not_formal_backtest", "generated_on": "2026-08-09",
        "protocol": {"path": PROTOCOL_PATH, "sha256": PROTOCOL_SHA256, "commit": PROTOCOL_COMMIT, "calculated_after_protocol_commit": True, "same_seen_905_event_family": True, "independent_first_unseen_evidence": False},
        "references": [{"repository": repository, "commit": commit} for repository, commit in REFERENCE_COMMITS],
        "input": {"events": 905, "first_signal_date": FIRST_SIGNAL_DATE, "first_entry_date": FIRST_ENTRY_DATE, "last_signal_date": LAST_SIGNAL_DATE, "last_exit_date": LAST_EXIT_DATE, "current_cohort": cohort, "current_cohort_count": len(cohort), "identifier_scope": "2026_current_symbols_not_permanent_ids", "survivorship_bias_warning": True, "initial_capital_usd": 1000.0},
        "input_receipts": input_hashes,
        "method": {"resonance_windows": list(MOMENTUM_WINDOWS), "window_top_k": 7, "resonance_minimum_windows": 3, "ranking_rule": "resonance_desc_rank_sum_asc_ticker_asc", "percentile_display_only": True, "stock_subslots": 7, "stock_target_rule": "N/7", "qqq_remainder_rule": "1-N/7", "entry_delay_sessions": 1, "holding_sessions": 20, "slot_count": 5, "events_per_slot": 181, "inactive_asset": "QQQ", "primary_asset_round_trip_cost_bps": 20, "primary_one_way_leg_cost_bps": 10, "normal_switched_subslot_transaction_legs": 4, "cost_stress_bps": [50, 100], "path_ids": list(PATH_IDS), "fractional_shares_research_only": True, "leverage_allowed": False},
        "reconstruction": reconstruction, "selection_distribution": distribution, "selection_receipts": selection_receipts,
        "calendar_integrity": {"sessions": len(index), "first_date": index[0].strftime("%Y-%m-%d"), "last_date": index[-1].strftime("%Y-%m-%d"), "maximum_daily_identity_residual": max(path.get("maximum_daily_identity_residual", 0.0) for path in primary_paths.values()), "maximum_driver_identity_residual": max(path.get("maximum_driver_identity_residual", 0.0) for path in primary_paths.values()), "maximum_cost_identity_residual": max(path.get("maximum_cost_identity_residual", 0.0) for path in primary_paths.values()), "maximum_original_top7_parent_residual": original_residual, "maximum_original_top7_parent_stress_normalized_metric_residual": parent_stress_metric_residual, "maximum_qqq_placebo_residual": placebo_residual, "qqq_placebo_identity_method": "independent_analytical_qqq_price_and_partial_cost_reconstruction", "post_entry_maximum_cash_value": float(primary_paths["resonance3_qqq_overlay"]["cash_value"].loc[FIRST_ENTRY_DATE:].abs().max()), "maximum_exposure": candidate["maximum_exposure"], "candidate_cost_charge_operations": primary_paths["resonance3_qqq_overlay"]["total_legs"], "cost_charge_operation_semantics": "accounting_cost_deductions_not_economic_directions_or_broker_orders"},
        "paths": metrics, "family": {"size": 8, "candidate_id": "resonance3_qqq_overlay", "comparisons": comparisons, "common_bootstrap": bootstrap, "global_search_trials": GLOBAL_SEARCH_TRIALS},
        "stresses": {"best_three_years_removed": best_year_stress, "crisis_years": crises, "known_at_qqq_regimes": regime_rows, "costs": costs, "favorable_46_events_removed": removed_stress},
        "gates": gates, "gate_summary": gate_summary, "controls": controls, "control_summary": control_summary, "attacks": attacks, "attack_summary": attack_summary, "calendar_rows": calendar_rows,
        "decision": {"can_promote_from_this_round": False, "not_rejected_by_round38": gate_summary["all_passed"], "new_strategy_created": False, "formal_readiness": "1/18", "point_in_time_readiness": "1/20", "qualified_provider_packages": 0, "formal_strategy_runs": 0, "paper_status": "all_cash_not_started", "paper_positions": 0, "real_money_action_usd": 0, "us1000_is_reader_example_only": True, "formal_global_search_trials": GLOBAL_SEARCH_TRIALS},
    }
