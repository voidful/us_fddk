from __future__ import annotations

import hashlib
import math
from collections.abc import Callable
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from . import calendar_capital_accounting as round29

SCHEMA_VERSION = 1
RESEARCH_ROUND = 30
PROTOCOL_PATH = "docs/SHORT_TERM_QQQ_REPLACEMENT_OVERLAY_PROTOCOL.md"
PROTOCOL_SHA256 = "d17979ca149c20341cc537290743ee44944ce0a6952ea0409995e77e85fcd601"
PROTOCOL_COMMIT = "bf52098e8ff5919cf5afff262e982be281fc488c"

ROUND29_RECEIPT_PATH = "artifacts/short_term_calendar_capital_accounting_validation.json"
ROUND29_RECEIPT_SHA256 = "a35a3fa21b491250a3cce23e627a26e67a0d3219f796af4e2ec739d9f07e8e36"
EVENT_RECEIPT_PATH = round29.EVENT_RECEIPT_PATH
EVENT_RECEIPT_SHA256 = round29.EVENT_RECEIPT_SHA256
SNAPSHOT_PATH = round29.SNAPSHOT_PATH
SNAPSHOT_SHA256 = round29.SNAPSHOT_SHA256
PANEL_SHA256 = round29.PANEL_SHA256
WATCHLIST_PATH = round29.WATCHLIST_PATH
WATCHLIST_SHA256 = round29.WATCHLIST_SHA256
REFERENCE_COMMITS = round29.REFERENCE_COMMITS

EXPECTED_EVENTS = round29.EXPECTED_EVENTS
EXPECTED_COHORT = round29.EXPECTED_COHORT
FIRST_SIGNAL_DATE = round29.FIRST_SIGNAL_DATE
FIRST_ENTRY_DATE = round29.FIRST_ENTRY_DATE
LAST_SIGNAL_DATE = round29.LAST_SIGNAL_DATE
LAST_EXIT_DATE = round29.LAST_EXIT_DATE
MOMENTUM_SESSIONS = round29.MOMENTUM_SESSIONS
TREND_SESSIONS = round29.TREND_SESSIONS
TOP_K = round29.TOP_K
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
    "top7_qqq_overlay",
    "eligible_qqq_overlay",
    "complete_qqq_overlay",
    "qqq_switch_placebo",
)
PATH_IDS = (
    *OVERLAY_PATH_IDS,
    "top7_cash_five_slot",
    "qqq_buy_hold",
    "spy_buy_hold",
    "shy_buy_hold",
)
FAMILY_BASELINE_IDS = PATH_IDS[1:]
PATH_LABELS = {
    "top7_qqq_overlay": "Top-7／QQQ 替換式疊加",
    "eligible_qqq_overlay": "合資格池／QQQ 替換式疊加",
    "complete_qqq_overlay": "完整現時股池／QQQ 替換式疊加",
    "qqq_switch_placebo": "QQQ 同時鐘換手 placebo",
    "top7_cash_five_slot": "Top-7 五槽現金路徑",
    "qqq_buy_hold": "QQQ 買入並持有",
    "spy_buy_hold": "SPY 買入並持有",
    "shy_buy_hold": "SHY 買入並持有",
}

HAC_LAG = 20
FAMILY_ALPHA = 0.05
BOOTSTRAP_BLOCK_SESSIONS = 63
BOOTSTRAP_PATHS = 20_000
BOOTSTRAP_SEED = 30_202_608
GLOBAL_SEARCH_TRIALS = 6_221
FIRST_HALF_END = round29.FIRST_HALF_END
SECOND_HALF_START = round29.SECOND_HALF_START
CRISIS_YEARS = round29.CRISIS_YEARS
BEST_YEAR_REMOVAL_COUNT = 3
FAVORABLE_EVENT_REMOVAL_COUNT = 46


class QQQReplacementOverlayError(ValueError):
    """Fail-closed Round 30 error with a stable semantic code."""

    def __init__(self, code: str, detail: str):
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}")


def _fail(code: str, detail: str) -> None:
    raise QQQReplacementOverlayError(code, detail)


@dataclass(frozen=True)
class FrozenQQQReplacementOverlayContract:
    protocol_sha256: str = PROTOCOL_SHA256
    protocol_commit: str = PROTOCOL_COMMIT
    round29_receipt_sha256: str = ROUND29_RECEIPT_SHA256
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
    inactive_asset: str = "QQQ"
    primary_asset_round_trip_bps: int = PRIMARY_ASSET_ROUND_TRIP_BPS
    cost_stress_bps: tuple[int, ...] = COST_STRESS_BPS
    four_legs_per_normal_event: bool = True
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
    current_identifiers_only: bool = True
    paper_authorized: bool = False
    real_money_authorized: bool = False


FROZEN_CONTRACT = FrozenQQQReplacementOverlayContract()


def validate_qqq_replacement_overlay_contract(
    contract: FrozenQQQReplacementOverlayContract,
) -> None:
    checks: tuple[tuple[bool, str, str], ...] = (
        (contract.protocol_sha256 == PROTOCOL_SHA256, "qqq_overlay_protocol_hash_mismatch", "協議 SHA 漂移"),
        (contract.protocol_commit == PROTOCOL_COMMIT, "qqq_overlay_protocol_commit_mismatch", "協議 commit 漂移"),
        (contract.round29_receipt_sha256 == ROUND29_RECEIPT_SHA256, "qqq_overlay_round29_receipt_mismatch", "第 29 輪收據漂移"),
        (contract.event_receipt_sha256 == EVENT_RECEIPT_SHA256, "qqq_overlay_event_receipt_mismatch", "原始事件收據漂移"),
        (contract.snapshot_sha256 == SNAPSHOT_SHA256 and contract.panel_sha256 == PANEL_SHA256, "qqq_overlay_market_data_mismatch", "行情 archive 或 panel 漂移"),
        (contract.watchlist_sha256 == WATCHLIST_SHA256, "qqq_overlay_watchlist_mismatch", "watchlist 漂移"),
        (contract.reference_commits == REFERENCE_COMMITS, "qqq_overlay_reference_mismatch", "台股參考 commit 漂移"),
        (contract.expected_events == EXPECTED_EVENTS, "qqq_overlay_event_count_mismatch", "事件數漂移"),
        (contract.expected_cohort == EXPECTED_COHORT, "qqq_overlay_cohort_mismatch", "完整 cohort 漂移"),
        (contract.momentum_sessions == MOMENTUM_SESSIONS and contract.trend_sessions == TREND_SESSIONS and contract.top_k == TOP_K, "qqq_overlay_signal_rule_mismatch", "訊號或 Top-K 漂移"),
        (contract.entry_delay == ENTRY_DELAY and contract.holding_sessions == HOLDING_SESSIONS, "qqq_overlay_execution_clock_mismatch", "成交時鐘漂移"),
        (contract.slot_count == SLOT_COUNT and contract.events_per_slot == EVENTS_PER_SLOT and contract.assignment_sha256 == ASSIGNMENT_SHA256, "qqq_overlay_assignment_mismatch", "五槽 assignment 漂移"),
        (contract.initial_capital_usd == INITIAL_CAPITAL_USD, "qqq_overlay_initial_capital_mismatch", "初始資本漂移"),
        (contract.inactive_asset == "QQQ", "qqq_overlay_inactive_asset_mismatch", "非事件底倉不是 QQQ"),
        (contract.primary_asset_round_trip_bps == PRIMARY_ASSET_ROUND_TRIP_BPS and contract.cost_stress_bps == COST_STRESS_BPS, "qqq_overlay_cost_contract_mismatch", "成本或壓力成本漂移"),
        (contract.four_legs_per_normal_event, "qqq_overlay_leg_contract_mismatch", "正常事件不是四腿換倉"),
        (contract.path_ids == PATH_IDS and contract.family_baseline_ids == FAMILY_BASELINE_IDS, "qqq_overlay_baseline_family_mismatch", "路徑或 family 漂移"),
        (contract.shy_excess_proxy, "qqq_overlay_excess_proxy_mismatch", "SHY excess 定義取消"),
        (contract.hac_lag == HAC_LAG and contract.family_alpha == FAMILY_ALPHA, "qqq_overlay_statistical_contract_mismatch", "NW lag 或 alpha 漂移"),
        (contract.bootstrap_block_sessions == BOOTSTRAP_BLOCK_SESSIONS and contract.bootstrap_paths == BOOTSTRAP_PATHS and contract.bootstrap_seed == BOOTSTRAP_SEED and contract.common_bootstrap_indices and contract.centered_under_null, "qqq_overlay_bootstrap_contract_mismatch", "bootstrap 設定漂移"),
        (contract.global_search_trials == GLOBAL_SEARCH_TRIALS, "qqq_overlay_global_trials_mismatch", "全專案 trials 漂移"),
        (contract.first_half_end == FIRST_HALF_END.strftime("%Y-%m-%d") and contract.second_half_start == SECOND_HALF_START.strftime("%Y-%m-%d"), "qqq_overlay_half_clock_mismatch", "固定半期漂移"),
        (contract.crisis_years == CRISIS_YEARS and contract.best_year_removal_count == BEST_YEAR_REMOVAL_COUNT and contract.favorable_event_removal_count == FAVORABLE_EVENT_REMOVAL_COUNT, "qqq_overlay_stress_contract_mismatch", "危機或尾部壓力漂移"),
        (contract.current_identifiers_only, "qqq_overlay_identifier_scope_mismatch", "現時身份警告取消"),
        (not contract.paper_authorized and not contract.real_money_authorized, "qqq_overlay_decision_boundary_breached", "越權啟動 Paper 或實金"),
    )
    for passed, code, detail in checks:
        if not passed:
            _fail(code, detail)


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _symbols_for_path(event: dict[str, Any], path_id: str, cohort: list[str]) -> list[str]:
    if path_id == "top7_qqq_overlay":
        return list(event["selected"])
    if path_id == "eligible_qqq_overlay":
        return list(event["eligible"])
    if path_id == "complete_qqq_overlay":
        return list(cohort)
    if path_id == "qqq_switch_placebo":
        return ["QQQ"]
    _fail("qqq_overlay_baseline_family_mismatch", f"未知 overlay 路徑 {path_id}")


def _charge_leg(value: float, side_cost: float) -> tuple[float, float]:
    cost = value * side_cost
    return value - cost, cost


def _build_overlay_path(
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
    first_entry_position = int(index.get_loc(first_entry))
    side_cost = asset_round_trip_bps / 20_000.0
    slot_initial = 1.0 / SLOT_COUNT
    slot_values: list[pd.Series] = []
    slot_active: list[pd.Series] = []
    slot_leg_counts: list[pd.Series] = []
    traded_notional = pd.Series(0.0, index=index, dtype=float)
    cost_paid = pd.Series(0.0, index=index, dtype=float)

    for slot in range(SLOT_COUNT):
        values = pd.Series(np.nan, index=index, dtype=float)
        active = pd.Series(False, index=index, dtype=bool)
        cumulative_legs = pd.Series(0, index=index, dtype=int)
        slot_events = [
            event
            for event in events
            if event["slot"] == slot and event["event_index"] not in excluded_event_indices
        ]
        event_cursor = 0
        current_event: dict[str, Any] | None = None
        event_entry_after_cost = 0.0
        previous_value = slot_initial
        legs_so_far = 0

        values.iloc[:first_entry_position] = slot_initial
        for position in range(first_entry_position, len(index)):
            date = index[position]
            previous_date = index[position - 1]
            next_event = slot_events[event_cursor] if event_cursor < len(slot_events) else None

            if position == first_entry_position:
                if next_event is not None and next_event["entry_date"] == date:
                    symbols = _symbols_for_path(next_event, path_id, cohort)
                    traded_notional.loc[date] += previous_value
                    previous_value, paid = _charge_leg(previous_value, side_cost)
                    cost_paid.loc[date] += paid
                    legs_so_far += 1
                    event_entry_after_cost = previous_value
                    gross = float(
                        panel.close.loc[date, symbols]
                        .div(panel.open.loc[date, symbols])
                        .sub(1.0)
                        .mean()
                    )
                    current_event = next_event
                    active.loc[date] = True
                    previous_value = event_entry_after_cost * (1.0 + gross)
                else:
                    traded_notional.loc[date] += previous_value
                    previous_value, paid = _charge_leg(previous_value, side_cost)
                    cost_paid.loc[date] += paid
                    legs_so_far += 1
                    previous_value *= float(
                        panel.close.loc[date, "QQQ"] / panel.open.loc[date, "QQQ"]
                    )
            elif current_event is None:
                if next_event is not None and next_event["entry_date"] == date:
                    qqq_at_open = previous_value * float(
                        panel.open.loc[date, "QQQ"] / panel.close.loc[previous_date, "QQQ"]
                    )
                    traded_notional.loc[date] += qqq_at_open
                    after_sell, paid = _charge_leg(qqq_at_open, side_cost)
                    cost_paid.loc[date] += paid
                    legs_so_far += 1
                    traded_notional.loc[date] += after_sell
                    after_buy, paid = _charge_leg(after_sell, side_cost)
                    cost_paid.loc[date] += paid
                    legs_so_far += 1
                    symbols = _symbols_for_path(next_event, path_id, cohort)
                    event_entry_after_cost = after_buy
                    gross = float(
                        panel.close.loc[date, symbols]
                        .div(panel.open.loc[date, symbols])
                        .sub(1.0)
                        .mean()
                    )
                    current_event = next_event
                    active.loc[date] = True
                    previous_value = event_entry_after_cost * (1.0 + gross)
                else:
                    previous_value *= float(
                        panel.close.loc[date, "QQQ"] / panel.close.loc[previous_date, "QQQ"]
                    )
            else:
                symbols = _symbols_for_path(current_event, path_id, cohort)
                active.loc[date] = True
                gross = float(
                    panel.close.loc[date, symbols]
                    .div(panel.open.loc[current_event["entry_date"], symbols])
                    .sub(1.0)
                    .mean()
                )
                previous_value = event_entry_after_cost * (1.0 + gross)

            if current_event is not None and current_event["exit_date"] == date:
                traded_notional.loc[date] += previous_value
                previous_value, paid = _charge_leg(previous_value, side_cost)
                cost_paid.loc[date] += paid
                legs_so_far += 1
                if date != last_exit:
                    traded_notional.loc[date] += previous_value
                    previous_value, paid = _charge_leg(previous_value, side_cost)
                    cost_paid.loc[date] += paid
                    legs_so_far += 1
                current_event = None
                event_cursor += 1

            if date == last_exit and current_event is None:
                # A final event already paid its sell leg immediately above. Other slots hold QQQ.
                if not active.loc[date]:
                    traded_notional.loc[date] += previous_value
                    previous_value, paid = _charge_leg(previous_value, side_cost)
                    cost_paid.loc[date] += paid
                    legs_so_far += 1

            if not np.isfinite(previous_value) or previous_value <= 0.0:
                _fail("qqq_overlay_daily_path_mismatch", "槽位日線資產非正或非有限")
            values.loc[date] = previous_value
            cumulative_legs.loc[date] = legs_so_far

        if current_event is not None or event_cursor != len(slot_events) or values.isna().any():
            _fail("qqq_overlay_event_clock_mismatch", "事件未完整進出或日線有缺值")
        slot_values.append(values)
        slot_active.append(active)
        slot_leg_counts.append(cumulative_legs)

    slot_frame = pd.concat(slot_values, axis=1)
    slot_frame.columns = [f"slot_{slot}" for slot in range(SLOT_COUNT)]
    active_frame = pd.concat(slot_active, axis=1)
    active_frame.columns = slot_frame.columns
    leg_frame = pd.concat(slot_leg_counts, axis=1)
    leg_frame.columns = slot_frame.columns
    equity = slot_frame.sum(axis=1)
    event_driver_value = slot_frame.where(active_frame, 0.0).sum(axis=1)
    invested = pd.Series(False, index=index)
    invested.loc[first_entry:last_exit] = True
    exposure = invested.astype(float)
    cash_value = equity.where(~invested, 0.0)
    qqq_driver_value = equity - event_driver_value - cash_value
    returns = equity.pct_change(fill_method=None).fillna(0.0)
    turnover = traded_notional.div(equity.shift(1).fillna(1.0))
    maximum_identity_residual = float((equity - slot_frame.sum(axis=1)).abs().max())
    maximum_driver_residual = float(
        (equity - event_driver_value - qqq_driver_value - cash_value).abs().max()
    )
    placebo_residual = 0.0
    if path_id == "qqq_switch_placebo":
        qqq_gross = panel.close.loc[first_entry:last_exit, "QQQ"].div(
            panel.open.loc[first_entry, "QQQ"]
        )
        expected_slots = pd.DataFrame(index=index, columns=slot_frame.columns, dtype=float)
        expected_slots.iloc[:first_entry_position] = slot_initial
        for column in slot_frame.columns:
            expected_slots.loc[first_entry:last_exit, column] = (
                slot_initial
                * qqq_gross
                * np.power(1.0 - side_cost, leg_frame.loc[first_entry:last_exit, column])
            )
        placebo_residual = float((slot_frame - expected_slots).abs().max().max())
    if (
        maximum_identity_residual > RECONSTRUCTION_TOLERANCE
        or maximum_driver_residual > RECONSTRUCTION_TOLERANCE
        or placebo_residual > RECONSTRUCTION_TOLERANCE
        or float(cash_value.min()) < -RECONSTRUCTION_TOLERANCE
        or float(exposure.max()) > 1.0 + RECONSTRUCTION_TOLERANCE
        or float(equity.min()) <= 0.0
    ):
        _fail("qqq_overlay_daily_identity_mismatch", "資產、driver、placebo、現金或無槓桿 identity 失敗")
    post_entry_cash = cash_value.loc[first_entry:last_exit]
    if float(post_entry_cash.abs().max()) > RECONSTRUCTION_TOLERANCE:
        _fail("qqq_overlay_full_investment_mismatch", "首次成交後仍有閒置現金")
    return {
        "equity": equity,
        "returns": returns,
        "turnover": turnover,
        "exposure": exposure,
        "cash_value": cash_value,
        "slot_values": slot_frame,
        "event_driver_value": event_driver_value,
        "qqq_driver_value": qqq_driver_value,
        "event_driver_fraction": event_driver_value.div(equity),
        "qqq_driver_fraction": qqq_driver_value.div(equity),
        "cost_paid": cost_paid,
        "leg_counts": leg_frame,
        "total_legs": int(leg_frame.iloc[-1].sum()),
        "maximum_daily_identity_residual": maximum_identity_residual,
        "maximum_driver_identity_residual": maximum_driver_residual,
        "maximum_qqq_placebo_residual": placebo_residual,
    }


def _common_bootstrap(
    matrix: np.ndarray, observed_t: np.ndarray, standard_errors: np.ndarray
) -> dict[str, Any]:
    centered = matrix - matrix.mean(axis=0, keepdims=True)
    if not np.allclose(centered.mean(axis=0), 0.0, atol=1e-15):
        _fail("qqq_overlay_bootstrap_contract_mismatch", "bootstrap 去中心化失敗")
    if (standard_errors <= 0.0).any():
        _fail("qqq_overlay_bootstrap_contract_mismatch", "NW 標準誤非正")
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


def _contract_attacks() -> list[
    tuple[
        str,
        str,
        str,
        Callable[[FrozenQQQReplacementOverlayContract], FrozenQQQReplacementOverlayContract],
    ]
]:
    return [
        ("01", "協議 SHA 漂移", "qqq_overlay_protocol_hash_mismatch", lambda c: replace(c, protocol_sha256="0" * 64)),
        ("02", "協議 commit 漂移", "qqq_overlay_protocol_commit_mismatch", lambda c: replace(c, protocol_commit="0" * 40)),
        ("03", "第 29 輪收據漂移", "qqq_overlay_round29_receipt_mismatch", lambda c: replace(c, round29_receipt_sha256="0" * 64)),
        ("04", "原始事件收據漂移", "qqq_overlay_event_receipt_mismatch", lambda c: replace(c, event_receipt_sha256="0" * 64)),
        ("05", "行情 archive 漂移", "qqq_overlay_market_data_mismatch", lambda c: replace(c, snapshot_sha256="0" * 64)),
        ("06", "watchlist 漂移", "qqq_overlay_watchlist_mismatch", lambda c: replace(c, watchlist_sha256="0" * 64)),
        ("07", "台股參考 commit 漂移", "qqq_overlay_reference_mismatch", lambda c: replace(c, reference_commits=())),
        ("08", "事件改 904", "qqq_overlay_event_count_mismatch", lambda c: replace(c, expected_events=904)),
        ("09", "完整 cohort 改 24", "qqq_overlay_cohort_mismatch", lambda c: replace(c, expected_cohort=24)),
        ("10", "Top-K 改 10", "qqq_overlay_signal_rule_mismatch", lambda c: replace(c, top_k=10)),
        ("11", "持有期改 10 日", "qqq_overlay_execution_clock_mismatch", lambda c: replace(c, holding_sessions=10)),
        ("12", "槽位改四個", "qqq_overlay_assignment_mismatch", lambda c: replace(c, slot_count=4)),
        ("13", "初始資本改 US$10,000", "qqq_overlay_initial_capital_mismatch", lambda c: replace(c, initial_capital_usd=10_000.0)),
        ("14", "非事件底倉改 SPY", "qqq_overlay_inactive_asset_mismatch", lambda c: replace(c, inactive_asset="SPY")),
        ("15", "主要成本改 10 bps", "qqq_overlay_cost_contract_mismatch", lambda c: replace(c, primary_asset_round_trip_bps=10)),
        ("16", "取消四腿換倉", "qqq_overlay_leg_contract_mismatch", lambda c: replace(c, four_legs_per_normal_event=False)),
        ("17", "刪除 QQQ buy-hold", "qqq_overlay_baseline_family_mismatch", lambda c: replace(c, path_ids=tuple(path for path in PATH_IDS if path != "qqq_buy_hold"))),
        ("18", "刪除一個 family baseline", "qqq_overlay_baseline_family_mismatch", lambda c: replace(c, family_baseline_ids=FAMILY_BASELINE_IDS[:-1])),
        ("19", "取消 SHY excess", "qqq_overlay_excess_proxy_mismatch", lambda c: replace(c, shy_excess_proxy=False)),
        ("20", "NW lag 改 4", "qqq_overlay_statistical_contract_mismatch", lambda c: replace(c, hac_lag=4)),
        ("21", "bootstrap block 改 20", "qqq_overlay_bootstrap_contract_mismatch", lambda c: replace(c, bootstrap_block_sessions=20)),
        ("22", "bootstrap seed 漂移", "qqq_overlay_bootstrap_contract_mismatch", lambda c: replace(c, bootstrap_seed=1)),
        ("23", "全專案 trials 重設", "qqq_overlay_global_trials_mismatch", lambda c: replace(c, global_search_trials=7)),
        ("24", "半期起點漂移", "qqq_overlay_half_clock_mismatch", lambda c: replace(c, second_half_start="2017-01-01")),
        ("25", "刪除 2022 危機", "qqq_overlay_stress_contract_mismatch", lambda c: replace(c, crisis_years=(2008, 2020))),
        ("26", "尾部移除改 20 事件", "qqq_overlay_stress_contract_mismatch", lambda c: replace(c, favorable_event_removal_count=20)),
        ("27", "取消現時身份警告", "qqq_overlay_identifier_scope_mismatch", lambda c: replace(c, current_identifiers_only=False)),
        ("28", "越權啟動 Paper", "qqq_overlay_decision_boundary_breached", lambda c: replace(c, paper_authorized=True)),
        ("29", "越權啟動實金", "qqq_overlay_decision_boundary_breached", lambda c: replace(c, real_money_authorized=True)),
    ]


def run_contract_attacks() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for attack_id, label, expected_code, mutate in _contract_attacks():
        observed_code: str | None = None
        try:
            validate_qqq_replacement_overlay_contract(mutate(FROZEN_CONTRACT))
        except QQQReplacementOverlayError as exc:
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


def _metrics_with_overlay_fields(
    path: dict[str, Any], shy_proxy: pd.Series, path_id: str, cost_bps: int
) -> dict[str, Any]:
    metrics = round29._path_metrics(path, shy_proxy)
    metrics.update(
        {
            "path_id": path_id,
            "label": PATH_LABELS[path_id],
            "asset_round_trip_cost_bps": cost_bps,
            "total_transaction_legs": int(path.get("total_legs", 2)),
            "total_cost_usd": float(INITIAL_CAPITAL_USD * path.get("cost_paid", pd.Series([0.0])).sum()),
            "average_event_driver_fraction": float(path.get("event_driver_fraction", pd.Series([0.0])).mean()),
            "average_qqq_driver_fraction": float(path.get("qqq_driver_fraction", pd.Series([0.0])).mean()),
        }
    )
    return metrics


def run_qqq_replacement_overlay(root: str | Path) -> dict[str, Any]:
    root_path = Path(root).resolve()
    contract = FROZEN_CONTRACT
    validate_qqq_replacement_overlay_contract(contract)
    input_hashes = {
        "protocol": _sha256_file(root_path / PROTOCOL_PATH),
        "round29": _sha256_file(root_path / ROUND29_RECEIPT_PATH),
        "event_receipt": _sha256_file(root_path / EVENT_RECEIPT_PATH),
        "snapshot": _sha256_file(root_path / SNAPSHOT_PATH),
        "watchlist": _sha256_file(root_path / WATCHLIST_PATH),
    }
    if input_hashes != {
        "protocol": PROTOCOL_SHA256,
        "round29": ROUND29_RECEIPT_SHA256,
        "event_receipt": EVENT_RECEIPT_SHA256,
        "snapshot": SNAPSHOT_SHA256,
        "watchlist": WATCHLIST_SHA256,
    }:
        _fail("qqq_overlay_input_receipt_mismatch", "固定輸入檔案 hash 漂移")

    panel, cohort, frozen_events, parent_meta = round29._load_inputs(
        root_path, round29.FROZEN_CONTRACT
    )
    events, reconstruction = round29._reconstruct_events(
        panel, cohort, frozen_events
    )
    input_hashes["panel"] = parent_meta["hashes"]["panel"]
    if input_hashes["panel"] != PANEL_SHA256:
        _fail("qqq_overlay_market_data_mismatch", "panel fingerprint 漂移")

    index = panel.close.loc[FIRST_SIGNAL_DATE:LAST_EXIT_DATE].index
    shy_proxy = panel.close.loc[index, "SHY"].pct_change(fill_method=None).fillna(0.0)
    primary_paths = {
        path_id: _build_overlay_path(
            panel, cohort, events, path_id, PRIMARY_ASSET_ROUND_TRIP_BPS
        )
        for path_id in OVERLAY_PATH_IDS
    }
    primary_paths.update(
        {
            "top7_cash_five_slot": round29._build_five_slot_path(
                panel,
                cohort,
                events,
                "top7_five_slot",
                PRIMARY_ASSET_ROUND_TRIP_BPS,
            ),
            "qqq_buy_hold": round29._build_buy_hold_path(
                panel, "QQQ", PRIMARY_ASSET_ROUND_TRIP_BPS
            ),
            "spy_buy_hold": round29._build_buy_hold_path(
                panel, "SPY", PRIMARY_ASSET_ROUND_TRIP_BPS
            ),
            "shy_buy_hold": round29._build_buy_hold_path(
                panel, "SHY", PRIMARY_ASSET_ROUND_TRIP_BPS
            ),
        }
    )
    zero_paths = {
        path_id: _build_overlay_path(panel, cohort, events, path_id, 0)
        for path_id in OVERLAY_PATH_IDS
    }
    zero_paths.update(
        {
            "top7_cash_five_slot": round29._build_five_slot_path(
                panel, cohort, events, "top7_five_slot", 0
            ),
            "qqq_buy_hold": round29._build_buy_hold_path(panel, "QQQ", 0),
            "spy_buy_hold": round29._build_buy_hold_path(panel, "SPY", 0),
            "shy_buy_hold": round29._build_buy_hold_path(panel, "SHY", 0),
        }
    )
    metrics: dict[str, Any] = {}
    for path_id in PATH_IDS:
        primary = _metrics_with_overlay_fields(
            primary_paths[path_id], shy_proxy, path_id, PRIMARY_ASSET_ROUND_TRIP_BPS
        )
        zero = round29._path_metrics(zero_paths[path_id], shy_proxy)
        primary["cost_drag_cagr"] = zero["cagr"] - primary["cagr"]
        primary["cost_drag_terminal_usd"] = zero["terminal_usd"] - primary["terminal_usd"]
        metrics[path_id] = primary

    candidate_returns = primary_paths["top7_qqq_overlay"]["returns"]
    comparisons: list[dict[str, Any]] = []
    matrix_columns: list[np.ndarray] = []
    differences: dict[str, np.ndarray] = {}
    for baseline_id in FAMILY_BASELINE_IDS:
        values = (
            candidate_returns - primary_paths[baseline_id]["returns"]
        ).to_numpy(dtype=float)
        differences[baseline_id] = values
        nw = round29._nw(values)
        comparisons.append(
            {
                "baseline_id": baseline_id,
                "baseline_label": PATH_LABELS[baseline_id],
                "sessions": len(values),
                "mean_daily_difference": float(values.mean()),
                "median_daily_difference": float(np.median(values)),
                "positive_fraction": float((values > 0.0).mean()),
                "newey_west": nw,
                "raw_normal_p": round29._normal_two_sided_p(float(nw["t_stat"])),
                "fixed_halves": round29._fixed_halves(values, index),
                "annual_active_returns": round29._annual_active(values, index),
            }
        )
        matrix_columns.append(values)
    holm = round29._holm_adjust(comparisons)
    matrix = np.column_stack(matrix_columns)
    observed_t = np.asarray([row["newey_west"]["t_stat"] for row in comparisons])
    standard_errors = np.asarray(
        [row["newey_west"]["standard_error"] for row in comparisons]
    )
    bootstrap = _common_bootstrap(matrix, observed_t, standard_errors)
    for idx, row in enumerate(comparisons):
        row["holm_adjusted_p"] = holm[row["baseline_id"]]
        row["bootstrap_max_t_p"] = bootstrap["single_step_max_t_p"][idx]
        row["family_bonferroni_p"] = min(
            1.0, row["raw_normal_p"] * len(comparisons)
        )
        row["global_bonferroni_p"] = min(
            1.0, row["raw_normal_p"] * GLOBAL_SEARCH_TRIALS
        )
    comparison_by_id = {row["baseline_id"]: row for row in comparisons}

    qqq_annual = comparison_by_id["qqq_buy_hold"]["annual_active_returns"]
    removed_years = [
        row["year"]
        for row in sorted(
            qqq_annual,
            key=lambda row: (-row["compounded_active_return"], row["year"]),
        )[:BEST_YEAR_REMOVAL_COUNT]
    ]
    year_mask = ~np.isin(index.year, removed_years)
    qqq_tail_values = differences["qqq_buy_hold"][year_mask]
    best_year_stress = {
        "selection_basis": "highest_candidate_minus_qqq_compounded_year",
        "removed_years": removed_years,
        "remaining_sessions": int(year_mask.sum()),
        "mean_daily_difference": float(qqq_tail_values.mean()),
        "newey_west": round29._nw(qqq_tail_values),
    }

    favorable_events = sorted(
        events,
        key=lambda event: (
            -(float(event["gross"].loc[event["selected"]].mean()) - float(event["qqq_gross"])),
            event["event_index"],
        ),
    )[:FAVORABLE_EVENT_REMOVAL_COUNT]
    excluded_event_indices = frozenset(
        int(event["event_index"]) for event in favorable_events
    )
    removed_event_paths = {
        path_id: _build_overlay_path(
            panel,
            cohort,
            events,
            path_id,
            PRIMARY_ASSET_ROUND_TRIP_BPS,
            excluded_event_indices,
        )
        for path_id in OVERLAY_PATH_IDS[:3]
    }
    removed_event_metrics = {
        path_id: round29._path_metrics(path, shy_proxy)
        for path_id, path in removed_event_paths.items()
    }
    removed_event_stress = {
        "selection_basis": "highest_frozen_top7_minus_qqq_event_gross_difference",
        "removed_event_count": len(excluded_event_indices),
        "removed_event_indices": sorted(excluded_event_indices),
        "first_removed_signal_date": min(
            event["signal_date"] for event in favorable_events
        ).strftime("%Y-%m-%d"),
        "last_removed_signal_date": max(
            event["signal_date"] for event in favorable_events
        ).strftime("%Y-%m-%d"),
        "paths": removed_event_metrics,
        "candidate_cagr_differences": {
            "qqq_buy_hold": removed_event_metrics["top7_qqq_overlay"]["cagr"]
            - metrics["qqq_buy_hold"]["cagr"],
            "eligible_qqq_overlay": removed_event_metrics["top7_qqq_overlay"]["cagr"]
            - removed_event_metrics["eligible_qqq_overlay"]["cagr"],
            "complete_qqq_overlay": removed_event_metrics["top7_qqq_overlay"]["cagr"]
            - removed_event_metrics["complete_qqq_overlay"]["cagr"],
        },
    }

    crises = {
        str(year): {
            path_id: round29._crisis_metrics(primary_paths[path_id], year)
            for path_id in PATH_IDS
        }
        for year in CRISIS_YEARS
    }
    cost_stresses: dict[str, Any] = {}
    for cost_bps in COST_STRESS_BPS:
        paths = {
            path_id: _build_overlay_path(panel, cohort, events, path_id, cost_bps)
            for path_id in OVERLAY_PATH_IDS
        }
        paths.update(
            {
                "top7_cash_five_slot": round29._build_five_slot_path(
                    panel, cohort, events, "top7_five_slot", cost_bps
                ),
                "qqq_buy_hold": round29._build_buy_hold_path(panel, "QQQ", cost_bps),
                "spy_buy_hold": round29._build_buy_hold_path(panel, "SPY", cost_bps),
                "shy_buy_hold": round29._build_buy_hold_path(panel, "SHY", cost_bps),
            }
        )
        path_metrics = {
            path_id: round29._path_metrics(path, shy_proxy)
            for path_id, path in paths.items()
        }
        candidate = path_metrics["top7_qqq_overlay"]
        cost_stresses[str(cost_bps)] = {
            "asset_round_trip_cost_bps": cost_bps,
            "normal_overlay_event_total_nominal_bps": 2 * cost_bps,
            "paths": path_metrics,
            "candidate_cagr_differences": {
                baseline_id: candidate["cagr"] - path_metrics[baseline_id]["cagr"]
                for baseline_id in (
                    "qqq_buy_hold",
                    "eligible_qqq_overlay",
                    "complete_qqq_overlay",
                )
            },
        }

    candidate = metrics["top7_qqq_overlay"]
    qqq = metrics["qqq_buy_hold"]
    qqq_comparison = comparison_by_id["qqq_buy_hold"]
    eligible_comparison = comparison_by_id["eligible_qqq_overlay"]
    complete_comparison = comparison_by_id["complete_qqq_overlay"]
    crisis_gate = all(
        crises[str(year)]["top7_qqq_overlay"]["return"]
        >= crises[str(year)]["qqq_buy_hold"]["return"]
        and crises[str(year)]["top7_qqq_overlay"]["max_drawdown"]
        >= crises[str(year)]["qqq_buy_hold"]["max_drawdown"] - 0.05
        for year in CRISIS_YEARS
    )
    stress_gate = (
        qqq_comparison["global_bonferroni_p"] <= FAMILY_ALPHA
        and all(
            all(value > 0.0 for value in row["candidate_cagr_differences"].values())
            for row in cost_stresses.values()
        )
        and all(
            value > 0.0
            for value in removed_event_stress["candidate_cagr_differences"].values()
        )
    )
    gates = [
        {"id": "exact_input_receipts", "label": "所有固定輸入、父收據、行情、watchlist 與參考 commit 精確", "passed": True},
        {"id": "event_reconstruction", "label": "905 事件、四路回報及 assignment 逐列重播", "passed": reconstruction["maximum_event_return_residual"] <= RECONSTRUCTION_TOLERANCE and reconstruction["assignment_sha256"] == ASSIGNMENT_SHA256},
        {"id": "slot_clock", "label": "五槽各 181 事件、無重疊及最大五個 concurrent interval", "passed": reconstruction["slot_event_counts"] == [181] * 5 and reconstruction["maximum_concurrent_intervals"] == 5},
        {"id": "daily_overlay_identities", "label": "八路同日曆及 overlay 資產、driver、成本 identity", "passed": all(primary_paths[path_id]["maximum_daily_identity_residual"] <= RECONSTRUCTION_TOLERANCE and primary_paths[path_id]["maximum_driver_identity_residual"] <= RECONSTRUCTION_TOLERANCE for path_id in OVERLAY_PATH_IDS)},
        {"id": "fully_invested_no_leverage", "label": "首次成交後 100% long、零現金及無槓桿", "passed": candidate["average_exposure"] > 0.999 and candidate["maximum_exposure"] <= 1.0 + RECONSTRUCTION_TOLERANCE and primary_paths["top7_qqq_overlay"]["cash_value"].loc[FIRST_ENTRY_DATE:].abs().max() <= RECONSTRUCTION_TOLERANCE},
        {"id": "qqq_placebo_identity", "label": "QQQ placebo 價格路徑及換手成本逐日重建", "passed": primary_paths["qqq_switch_placebo"]["maximum_qqq_placebo_residual"] <= RECONSTRUCTION_TOLERANCE},
        {"id": "candidate_cagr_vs_qqq", "label": "候選 CAGR 高於 QQQ 買入並持有", "passed": candidate["cagr"] > qqq["cagr"]},
        {"id": "candidate_terminal_vs_qqq", "label": "候選 US$1,000 期末值高於 QQQ", "passed": candidate["terminal_usd"] > qqq["terminal_usd"]},
        {"id": "candidate_sharpe_vs_qqq", "label": "候選 SHY-excess Sharpe 高於 QQQ", "passed": candidate["shy_excess_sharpe"] > qqq["shy_excess_sharpe"]},
        {"id": "candidate_drawdown_vs_qqq", "label": "候選最大跌幅不比 QQQ 深超過 5pp", "passed": candidate["max_drawdown"] >= qqq["max_drawdown"] - 0.05},
        {"id": "candidate_cagr_vs_eligible", "label": "候選 CAGR 高於 eligible overlay", "passed": candidate["cagr"] > metrics["eligible_qqq_overlay"]["cagr"]},
        {"id": "candidate_cagr_vs_complete", "label": "候選 CAGR 高於 complete overlay", "passed": candidate["cagr"] > metrics["complete_qqq_overlay"]["cagr"]},
        {"id": "nw_vs_eligible", "label": "候選對 eligible 平均日差正且 NW t 不低於 1.96", "passed": eligible_comparison["mean_daily_difference"] > 0.0 and eligible_comparison["newey_west"]["t_stat"] >= 1.96},
        {"id": "nw_vs_complete", "label": "候選對 complete 平均日差正且 NW t 不低於 1.96", "passed": complete_comparison["mean_daily_difference"] > 0.0 and complete_comparison["newey_west"]["t_stat"] >= 1.96},
        {"id": "nw_vs_qqq", "label": "候選對 QQQ 平均日差正且 NW t 不低於 1.96", "passed": qqq_comparison["mean_daily_difference"] > 0.0 and qqq_comparison["newey_west"]["t_stat"] >= 1.96},
        {"id": "holm_and_max_t_vs_qqq", "label": "候選對 QQQ 的 Holm 及共同 max-t p 均不高於 0.05", "passed": qqq_comparison["holm_adjusted_p"] <= FAMILY_ALPHA and qqq_comparison["bootstrap_max_t_p"] <= FAMILY_ALPHA},
        {"id": "fixed_halves", "label": "候選對 QQQ／eligible／complete 前後半平均日差全正", "passed": all(comparison_by_id[baseline_id]["fixed_halves"][half]["mean_daily_difference"] > 0.0 for baseline_id in ("qqq_buy_hold", "eligible_qqq_overlay", "complete_qqq_overlay") for half in ("first", "second"))},
        {"id": "best_three_years_removed", "label": "移除相對 QQQ 最佳三年後平均差正且 NW t 不低於 1.96", "passed": best_year_stress["mean_daily_difference"] > 0.0 and best_year_stress["newey_west"]["t_stat"] >= 1.96},
        {"id": "crisis_periods", "label": "2008／2020／2022 回報不低於 QQQ且最大跌幅不深超過 5pp", "passed": crisis_gate},
        {"id": "global_cost_and_event_tail", "label": "6,221 trials、50／100 bps及移除 46 有利事件全部通過", "passed": stress_gate},
    ]
    gate_summary = {
        "passed": sum(int(row["passed"]) for row in gates),
        "total": len(gates),
        "all_passed": all(row["passed"] for row in gates),
    }

    controls = [
        {"id": "01", "label": "protocol SHA 與 commit", "passed": input_hashes["protocol"] == PROTOCOL_SHA256 and contract.protocol_commit == PROTOCOL_COMMIT},
        {"id": "02", "label": "第 29 輪收據", "passed": input_hashes["round29"] == ROUND29_RECEIPT_SHA256},
        {"id": "03", "label": "原始事件收據", "passed": input_hashes["event_receipt"] == EVENT_RECEIPT_SHA256},
        {"id": "04", "label": "行情 archive 與 panel", "passed": input_hashes["snapshot"] == SNAPSHOT_SHA256 and input_hashes["panel"] == PANEL_SHA256},
        {"id": "05", "label": "watchlist", "passed": input_hashes["watchlist"] == WATCHLIST_SHA256},
        {"id": "06", "label": "三個台股參考 commit", "passed": contract.reference_commits == REFERENCE_COMMITS},
        {"id": "07", "label": "905 事件及日期邊界", "passed": len(events) == 905 and events[0]["signal_date"].strftime("%Y-%m-%d") == FIRST_SIGNAL_DATE and events[-1]["exit_date"].strftime("%Y-%m-%d") == LAST_EXIT_DATE},
        {"id": "08", "label": "現時 cohort 25 隻", "passed": len(cohort) == 25},
        {"id": "09", "label": "20／60 日及 Top-7", "passed": contract.momentum_sessions == 20 and contract.trend_sessions == 60 and contract.top_k == 7},
        {"id": "10", "label": "D+1 open 至第 20 session close", "passed": contract.entry_delay == 1 and contract.holding_sessions == 20},
        {"id": "11", "label": "五槽 assignment", "passed": reconstruction["assignment_sha256"] == ASSIGNMENT_SHA256},
        {"id": "12", "label": "五槽各 181 事件", "passed": reconstruction["slot_event_counts"] == [181] * 5},
        {"id": "13", "label": "非事件底倉 QQQ", "passed": contract.inactive_asset == "QQQ"},
        {"id": "14", "label": "20／50／100 bps 資產 round trip", "passed": contract.primary_asset_round_trip_bps == 20 and contract.cost_stress_bps == (50, 100)},
        {"id": "15", "label": "正常事件四腿成本", "passed": contract.four_legs_per_normal_event and primary_paths["top7_qqq_overlay"]["total_legs"] == 3626},
        {"id": "16", "label": "八條固定路徑", "passed": tuple(primary_paths) == PATH_IDS},
        {"id": "17", "label": "七假說 family", "passed": tuple(row["baseline_id"] for row in comparisons) == FAMILY_BASELINE_IDS},
        {"id": "18", "label": "SHY excess 定義", "passed": contract.shy_excess_proxy and shy_proxy.notna().all()},
        {"id": "19", "label": "overlay 100% 股票比重", "passed": primary_paths["top7_qqq_overlay"]["exposure"].loc[FIRST_ENTRY_DATE:].eq(1.0).all()},
        {"id": "20", "label": "overlay 零現金及無槓桿", "passed": primary_paths["top7_qqq_overlay"]["cash_value"].loc[FIRST_ENTRY_DATE:].abs().max() <= 1e-12 and candidate["maximum_exposure"] <= 1.0},
        {"id": "21", "label": "日線資產與 driver identity", "passed": all(primary_paths[path_id]["maximum_daily_identity_residual"] <= 1e-12 and primary_paths[path_id]["maximum_driver_identity_residual"] <= 1e-12 for path_id in OVERLAY_PATH_IDS)},
        {"id": "22", "label": "QQQ placebo identity", "passed": primary_paths["qqq_switch_placebo"]["maximum_qqq_placebo_residual"] <= 1e-12},
        {"id": "23", "label": "路徑同起訖日", "passed": all(path["equity"].index.equals(index) for path in primary_paths.values())},
        {"id": "24", "label": "NW lag 20", "passed": all(row["newey_west"]["lag"] == 20 for row in comparisons)},
        {"id": "25", "label": "63-session／20,000 共同 bootstrap", "passed": bootstrap["block_sessions"] == 63 and bootstrap["paths"] == 20_000 and bootstrap["seed"] == 30_202_608 and bootstrap["common_indices"]},
        {"id": "26", "label": "固定半期與三個危機年", "passed": contract.first_half_end == "2016-07-29" and contract.crisis_years == (2008, 2020, 2022)},
        {"id": "27", "label": "最佳三年及 46-event 尾部", "passed": len(removed_years) == 3 and len(excluded_event_indices) == 46},
        {"id": "28", "label": "全專案 6,221 trials", "passed": contract.global_search_trials == 6_221},
        {"id": "29", "label": "現時身份及 Paper／實金邊界", "passed": contract.current_identifiers_only and not contract.paper_authorized and not contract.real_money_authorized},
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

    calendar_rows = [
        {
            "date": date.strftime("%Y-%m-%d"),
            "equity": {
                path_id: float(primary_paths[path_id]["equity"].loc[date])
                for path_id in PATH_IDS
            },
            "daily_return": {
                path_id: float(primary_paths[path_id]["returns"].loc[date])
                for path_id in PATH_IDS
            },
            "candidate_event_driver_fraction": float(
                primary_paths["top7_qqq_overlay"]["event_driver_fraction"].loc[date]
            ),
            "candidate_qqq_driver_fraction": float(
                primary_paths["top7_qqq_overlay"]["qqq_driver_fraction"].loc[date]
            ),
            "candidate_cost_paid": float(
                primary_paths["top7_qqq_overlay"]["cost_paid"].loc[date]
            ),
        }
        for date in index
    ]

    return {
        "schema_version": SCHEMA_VERSION,
        "research_round": RESEARCH_ROUND,
        "research_role": "same_seen_survivor_qqq_replacement_overlay_falsification_not_formal_backtest",
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
        "input_receipts": input_hashes,
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
            "inactive_asset": "QQQ",
            "primary_asset_round_trip_cost_bps": PRIMARY_ASSET_ROUND_TRIP_BPS,
            "primary_one_way_leg_cost_bps": PRIMARY_ASSET_ROUND_TRIP_BPS / 2,
            "normal_event_transaction_legs": 4,
            "normal_event_total_nominal_cost_bps": 2 * PRIMARY_ASSET_ROUND_TRIP_BPS,
            "cost_stress_bps": list(COST_STRESS_BPS),
            "overlay_path_ids": list(OVERLAY_PATH_IDS),
            "path_ids": list(PATH_IDS),
            "shy_daily_return_as_excess_proxy": True,
            "fractional_shares_research_only": True,
            "leverage_allowed": False,
        },
        "reconstruction": reconstruction,
        "calendar_integrity": {
            "sessions": len(index),
            "first_date": index[0].strftime("%Y-%m-%d"),
            "last_date": index[-1].strftime("%Y-%m-%d"),
            "candidate_total_transaction_legs": primary_paths["top7_qqq_overlay"]["total_legs"],
            "maximum_daily_identity_residual": max(primary_paths[path_id]["maximum_daily_identity_residual"] for path_id in OVERLAY_PATH_IDS),
            "maximum_driver_identity_residual": max(primary_paths[path_id]["maximum_driver_identity_residual"] for path_id in OVERLAY_PATH_IDS),
            "maximum_qqq_placebo_residual": primary_paths["qqq_switch_placebo"]["maximum_qqq_placebo_residual"],
            "post_entry_maximum_cash_value": float(primary_paths["top7_qqq_overlay"]["cash_value"].loc[FIRST_ENTRY_DATE:].abs().max()),
            "maximum_exposure": candidate["maximum_exposure"],
        },
        "paths": metrics,
        "family": {
            "size": len(comparisons),
            "candidate_id": "top7_qqq_overlay",
            "comparisons": comparisons,
            "common_bootstrap": bootstrap,
            "global_search_trials": GLOBAL_SEARCH_TRIALS,
        },
        "stresses": {
            "best_three_years_removed": best_year_stress,
            "favorable_46_events_removed": removed_event_stress,
            "crisis_years": crises,
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
            "not_rejected_by_round30": gate_summary["all_passed"],
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
