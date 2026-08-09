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
RESEARCH_ROUND = 39
PROTOCOL_PATH = "docs/SHORT_TERM_LEADER_PULLBACK_REBOUND_PROTOCOL.md"
PROTOCOL_SHA256 = "c88952e2e992ee16ab66f577a399f6da974c9f779283e54f8412957e7c389320"
PROTOCOL_COMMIT = "5fabed75b8b16dc16f6c84f39a109e968b844bce"
PARENT_MAIN_COMMIT = "1d506c987781e1c692543dba3f6483cfe57c160d"

ROUND38_RECEIPT_PATH = "artifacts/short_term_multi_window_resonance_validation.json"
ROUND38_RECEIPT_SHA256 = "5c066a4275f4ba851d2a18f3b0274c4f86374717a0507c721ebc9c46cd60fea5"
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
EXPECTED_CALENDAR_SESSIONS = 5_028
FIRST_SIGNAL_DATE = round29.FIRST_SIGNAL_DATE
FIRST_ENTRY_DATE = round29.FIRST_ENTRY_DATE
LAST_SIGNAL_DATE = round29.LAST_SIGNAL_DATE
CALENDAR_LAST_DATE = round29.LAST_EXIT_DATE
PARENT_MOMENTUM_SESSIONS = 20
PARENT_TREND_SESSIONS = 60
PARENT_TOP_K = 7
MINIMUM_PRICE_USD = 5.0
DOLLAR_VOLUME_SESSIONS = 20
MINIMUM_MEDIAN_DOLLAR_VOLUME_USD = 20_000_000.0

ATR_SESSIONS = 14
HIGH20_SESSIONS = 20
HIGH60_SESSIONS = 60
LOW10_SESSIONS = 10
PULLBACK_MINIMUM = 0.03
PULLBACK_MAXIMUM = 0.16
REBOUND_LOW_MULTIPLIER = 1.01
TARGET_ATR_MULTIPLIER = 1.5
STOP_ATR_MULTIPLIER = 0.5
UPSIDE_ATR_FLOOR = 0.5
DOWNSIDE_ATR_FLOOR = 1.0
REWARD_RISK_MINIMUM = 1.60
REWARD_RISK_CLIP_MAXIMUM = 8.0

STOCK_SUBSLOTS = 7
ENTRY_DELAY = 1
HOLDING_SESSIONS = 10
SLOT_COUNT = round29.SLOT_COUNT
EVENTS_PER_SLOT = round29.EVENTS_PER_SLOT
PARENT_ASSIGNMENT_SHA256 = round29.ASSIGNMENT_SHA256
INITIAL_CAPITAL_USD = round29.INITIAL_CAPITAL_USD
PRIMARY_ONE_WAY_LEG_BPS = 10
COST_STRESS_ONE_WAY_LEG_BPS = (25, 50)
FIXED_CHILD_ORDER_FEE_STRESS_USD = (0.01, 0.05)
RECONSTRUCTION_TOLERANCE = 1e-12

OVERLAY_PATH_IDS = (
    "lpr10_qqq_overlay",
    "matched_topn_10d_overlay",
    "matched_eligible_10d_overlay",
    "matched_complete_10d_overlay",
    "original_top7_10d_overlay",
    "matched_qqq_switch_placebo",
)
PATH_IDS = (*OVERLAY_PATH_IDS, "qqq_buy_hold", "spy_buy_hold", "shy_buy_hold")
FAMILY_BASELINE_IDS = PATH_IDS[1:]
PATH_LABELS = {
    "lpr10_qqq_overlay": "龍頭回調—回升確認／QQQ 部分替換",
    "matched_topn_10d_overlay": "相同比例原 Top-N／QQQ 部分替換",
    "matched_eligible_10d_overlay": "相同比例合資格池／QQQ 部分替換",
    "matched_complete_10d_overlay": "相同比例完整現時股池／QQQ 部分替換",
    "original_top7_10d_overlay": "原 Top-7 十日／QQQ 全替換",
    "matched_qqq_switch_placebo": "相同比例 QQQ 換手 placebo",
    "qqq_buy_hold": "QQQ 買入並持有",
    "spy_buy_hold": "SPY 買入並持有",
    "shy_buy_hold": "SHY 買入並持有",
}

HAC_LAG = 10
FAMILY_ALPHA = 0.05
BOOTSTRAP_BLOCK_SESSIONS = 63
BOOTSTRAP_PATHS = 20_000
BOOTSTRAP_SEED = 39_202_608
GLOBAL_SEARCH_TRIALS = 6_237
FIRST_HALF_END = round29.FIRST_HALF_END
SECOND_HALF_START = round29.SECOND_HALF_START
CRISIS_YEARS = round29.CRISIS_YEARS
BEST_YEAR_REMOVAL_COUNT = 3
FAVORABLE_EVENT_REMOVAL_COUNT = 46


class LeaderPullbackReboundError(ValueError):
    def __init__(self, code: str, detail: str):
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}")


def _fail(code: str, detail: str) -> None:
    raise LeaderPullbackReboundError(code, detail)


@dataclass(frozen=True)
class FrozenLeaderPullbackReboundContract:
    protocol_sha256: str = PROTOCOL_SHA256
    protocol_commit: str = PROTOCOL_COMMIT
    parent_main_commit: str = PARENT_MAIN_COMMIT
    round38_receipt_sha256: str = ROUND38_RECEIPT_SHA256
    round30_receipt_sha256: str = ROUND30_RECEIPT_SHA256
    round29_receipt_sha256: str = ROUND29_RECEIPT_SHA256
    event_receipt_sha256: str = EVENT_RECEIPT_SHA256
    snapshot_sha256: str = SNAPSHOT_SHA256
    panel_sha256: str = PANEL_SHA256
    watchlist_sha256: str = WATCHLIST_SHA256
    reference_commits: tuple[tuple[str, str], ...] = REFERENCE_COMMITS
    expected_events: int = EXPECTED_EVENTS
    expected_cohort: int = EXPECTED_COHORT
    expected_calendar_sessions: int = EXPECTED_CALENDAR_SESSIONS
    parent_momentum_sessions: int = PARENT_MOMENTUM_SESSIONS
    parent_trend_sessions: int = PARENT_TREND_SESSIONS
    parent_top_k: int = PARENT_TOP_K
    minimum_price_usd: float = MINIMUM_PRICE_USD
    dollar_volume_sessions: int = DOLLAR_VOLUME_SESSIONS
    minimum_median_dollar_volume_usd: float = MINIMUM_MEDIAN_DOLLAR_VOLUME_USD
    atr_sessions: int = ATR_SESSIONS
    high20_sessions: int = HIGH20_SESSIONS
    high60_sessions: int = HIGH60_SESSIONS
    low10_sessions: int = LOW10_SESSIONS
    pullback_minimum: float = PULLBACK_MINIMUM
    pullback_maximum: float = PULLBACK_MAXIMUM
    rebound_low_multiplier: float = REBOUND_LOW_MULTIPLIER
    target_atr_multiplier: float = TARGET_ATR_MULTIPLIER
    stop_atr_multiplier: float = STOP_ATR_MULTIPLIER
    upside_atr_floor: float = UPSIDE_ATR_FLOOR
    downside_atr_floor: float = DOWNSIDE_ATR_FLOOR
    reward_risk_minimum: float = REWARD_RISK_MINIMUM
    reward_risk_clip_maximum: float = REWARD_RISK_CLIP_MAXIMUM
    stock_subslots: int = STOCK_SUBSLOTS
    allocation_rule: str = "confirmed_each_one_seventh_remainder_qqq"
    entry_delay: int = ENTRY_DELAY
    holding_sessions: int = HOLDING_SESSIONS
    slot_count: int = SLOT_COUNT
    events_per_slot: int = EVENTS_PER_SLOT
    initial_capital_usd: float = INITIAL_CAPITAL_USD
    parent_assignment_sha256: str = PARENT_ASSIGNMENT_SHA256
    inactive_asset: str = "QQQ"
    primary_one_way_leg_bps: int = PRIMARY_ONE_WAY_LEG_BPS
    cost_stress_one_way_leg_bps: tuple[int, ...] = COST_STRESS_ONE_WAY_LEG_BPS
    fixed_child_order_fee_stress_usd: tuple[float, ...] = FIXED_CHILD_ORDER_FEE_STRESS_USD
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


FROZEN_CONTRACT = FrozenLeaderPullbackReboundContract()


def validate_leader_pullback_rebound_contract(
    contract: FrozenLeaderPullbackReboundContract,
) -> None:
    checks = (
        (contract.protocol_sha256 == PROTOCOL_SHA256, "lpr_protocol_hash_mismatch"),
        (contract.protocol_commit == PROTOCOL_COMMIT, "lpr_protocol_commit_mismatch"),
        (contract.parent_main_commit == PARENT_MAIN_COMMIT, "lpr_parent_commit_mismatch"),
        (contract.round38_receipt_sha256 == ROUND38_RECEIPT_SHA256, "lpr_round38_receipt_mismatch"),
        (contract.round30_receipt_sha256 == ROUND30_RECEIPT_SHA256, "lpr_round30_receipt_mismatch"),
        (contract.round29_receipt_sha256 == ROUND29_RECEIPT_SHA256, "lpr_round29_receipt_mismatch"),
        (contract.event_receipt_sha256 == EVENT_RECEIPT_SHA256, "lpr_event_receipt_mismatch"),
        (contract.snapshot_sha256 == SNAPSHOT_SHA256, "lpr_snapshot_mismatch"),
        (contract.panel_sha256 == PANEL_SHA256, "lpr_panel_mismatch"),
        (contract.watchlist_sha256 == WATCHLIST_SHA256, "lpr_watchlist_mismatch"),
        (contract.reference_commits == REFERENCE_COMMITS, "lpr_reference_mismatch"),
        (contract.expected_events == 905, "lpr_event_count_mismatch"),
        (contract.expected_cohort == 25, "lpr_cohort_mismatch"),
        (contract.expected_calendar_sessions == 5_028, "lpr_calendar_mismatch"),
        (contract.parent_momentum_sessions == 20, "lpr_parent_momentum_mismatch"),
        (contract.parent_trend_sessions == 60, "lpr_parent_trend_mismatch"),
        (contract.parent_top_k == 7, "lpr_parent_top_k_mismatch"),
        (contract.minimum_price_usd == 5.0, "lpr_price_floor_mismatch"),
        (contract.dollar_volume_sessions == 20, "lpr_liquidity_window_mismatch"),
        (contract.minimum_median_dollar_volume_usd == 20_000_000.0, "lpr_liquidity_floor_mismatch"),
        (contract.atr_sessions == 14, "lpr_atr_window_mismatch"),
        (contract.high20_sessions == 20, "lpr_high20_window_mismatch"),
        (contract.high60_sessions == 60, "lpr_high60_window_mismatch"),
        (contract.low10_sessions == 10, "lpr_low10_window_mismatch"),
        (contract.pullback_minimum == 0.03, "lpr_pullback_minimum_mismatch"),
        (contract.pullback_maximum == 0.16, "lpr_pullback_maximum_mismatch"),
        (contract.rebound_low_multiplier == 1.01, "lpr_rebound_mismatch"),
        (contract.target_atr_multiplier == 1.5, "lpr_target_mismatch"),
        (contract.stop_atr_multiplier == 0.5, "lpr_stop_mismatch"),
        (contract.upside_atr_floor == 0.5, "lpr_upside_floor_mismatch"),
        (contract.downside_atr_floor == 1.0, "lpr_downside_floor_mismatch"),
        (contract.reward_risk_minimum == 1.60, "lpr_reward_risk_minimum_mismatch"),
        (contract.reward_risk_clip_maximum == 8.0, "lpr_reward_risk_clip_mismatch"),
        (contract.stock_subslots == 7, "lpr_subslots_mismatch"),
        (contract.allocation_rule == "confirmed_each_one_seventh_remainder_qqq", "lpr_allocation_mismatch"),
        (contract.entry_delay == 1, "lpr_entry_clock_mismatch"),
        (contract.holding_sessions == 10, "lpr_holding_clock_mismatch"),
        (contract.slot_count == 5, "lpr_slot_count_mismatch"),
        (contract.events_per_slot == 181, "lpr_events_per_slot_mismatch"),
        (contract.initial_capital_usd == 1_000.0, "lpr_initial_capital_mismatch"),
        (contract.parent_assignment_sha256 == PARENT_ASSIGNMENT_SHA256, "lpr_parent_assignment_mismatch"),
        (contract.inactive_asset == "QQQ", "lpr_inactive_asset_mismatch"),
        (contract.primary_one_way_leg_bps == 10, "lpr_primary_cost_mismatch"),
        (contract.cost_stress_one_way_leg_bps == (25, 50), "lpr_cost_stress_mismatch"),
        (contract.fixed_child_order_fee_stress_usd == (0.01, 0.05), "lpr_fixed_fee_mismatch"),
        (contract.four_legs_per_switched_subslot, "lpr_four_leg_mismatch"),
        (contract.path_ids == PATH_IDS, "lpr_path_family_mismatch"),
        (contract.family_baseline_ids == FAMILY_BASELINE_IDS, "lpr_hypothesis_family_mismatch"),
        (contract.shy_excess_proxy, "lpr_shy_proxy_mismatch"),
        (contract.hac_lag == 10, "lpr_hac_mismatch"),
        (contract.family_alpha == 0.05, "lpr_family_alpha_mismatch"),
        (contract.bootstrap_block_sessions == 63, "lpr_bootstrap_block_mismatch"),
        (contract.bootstrap_paths == 20_000, "lpr_bootstrap_paths_mismatch"),
        (contract.bootstrap_seed == BOOTSTRAP_SEED, "lpr_bootstrap_seed_mismatch"),
        (contract.common_bootstrap_indices, "lpr_bootstrap_indices_mismatch"),
        (contract.centered_under_null, "lpr_bootstrap_centering_mismatch"),
        (contract.global_search_trials == 6_237, "lpr_global_trials_mismatch"),
        (contract.first_half_end == "2016-07-29", "lpr_first_half_mismatch"),
        (contract.second_half_start == "2016-08-01", "lpr_second_half_mismatch"),
        (contract.crisis_years == (2008, 2020, 2022), "lpr_crisis_mismatch"),
        (contract.best_year_removal_count == 3, "lpr_best_year_mismatch"),
        (contract.favorable_event_removal_count == 46, "lpr_tail_mismatch"),
        (contract.formal_readiness == "1/18", "lpr_formal_readiness_mismatch"),
        (contract.point_in_time_readiness == "1/20", "lpr_pit_readiness_mismatch"),
        (contract.qualified_provider_packages == 0, "lpr_provider_boundary_mismatch"),
        (contract.formal_strategy_runs == 0, "lpr_formal_run_boundary_mismatch"),
        (contract.current_identifiers_only, "lpr_identifier_scope_mismatch"),
        (not contract.paper_authorized, "lpr_paper_boundary_breached"),
        (not contract.real_money_authorized, "lpr_real_money_boundary_breached"),
    )
    for passed, code in checks:
        if not passed:
            _fail(code, "凍結契約欄位漂移")


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _symbols_hash(symbols: list[str]) -> str:
    return hashlib.sha256(json.dumps(symbols, separators=(",", ":")).encode()).hexdigest()


def _validate_ohlc_window(
    open_: pd.Series,
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
) -> None:
    arrays = [series.to_numpy(dtype=float) for series in (open_, high, low, close)]
    if not all(np.isfinite(values).all() for values in arrays):
        _fail("lpr_ohlc_nonfinite", "結構窗口 OHLC 含缺值或非有限值")
    if not all((values > 0.0).all() for values in arrays):
        _fail("lpr_ohlc_nonpositive", "結構窗口 OHLC 必須為正")
    o, h, lo, c = arrays
    if (h < np.maximum(o, c)).any() or (lo > np.minimum(o, c)).any() or (h < lo).any():
        _fail("lpr_ohlc_geometry_mismatch", "OHLC 高低界限不一致")


def compute_structure_feature(
    open_: pd.Series,
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    signal_date: pd.Timestamp | str,
) -> dict[str, Any]:
    """Compute the frozen D-close structure using no observation after D."""
    date = pd.Timestamp(signal_date)
    indices = (open_.index, high.index, low.index, close.index)
    if (
        not all(index.equals(indices[0]) for index in indices[1:])
        or not all(index.is_unique and index.is_monotonic_increasing for index in indices)
    ):
        _fail("lpr_ohlc_index_mismatch", "OHLC 索引必須逐列相同、唯一且遞增")
    common = indices[0]
    if date not in common:
        _fail("lpr_feature_clock_mismatch", "訊號日不在共同 OHLC 索引")
    position = int(common.get_loc(date))
    start = position - HIGH60_SESSIONS + 1
    tr_start = position - ATR_SESSIONS + 1
    if start < 0 or tr_start - 1 < 0:
        _fail("lpr_feature_warmup_mismatch", "結構窗口暖機不足")
    idx = common[start : position + 1]
    o = open_.reindex(idx).astype(float)
    h = high.reindex(idx).astype(float)
    lo = low.reindex(idx).astype(float)
    c = close.reindex(idx).astype(float)
    _validate_ohlc_window(o, h, lo, c)

    tr_idx = common[tr_start : position + 1]
    prior_idx = common[tr_start - 1 : position]
    tr_high = high.reindex(tr_idx).to_numpy(dtype=float)
    tr_low = low.reindex(tr_idx).to_numpy(dtype=float)
    prior_close = close.reindex(prior_idx).to_numpy(dtype=float)
    if not np.isfinite(prior_close).all() or (prior_close <= 0).any():
        _fail("lpr_atr_prior_close_mismatch", "ATR 前一日收市缺失")
    true_range = np.maximum(
        tr_high - tr_low,
        np.maximum(np.abs(tr_high - prior_close), np.abs(tr_low - prior_close)),
    )
    if len(true_range) != ATR_SESSIONS or not np.isfinite(true_range).all():
        _fail("lpr_atr_window_mismatch", "ATR14 沒有完整 14 個 TR")

    close_d = float(close.loc[date])
    close_previous = float(close.loc[common[position - 1]])
    atr14 = float(np.mean(true_range))
    high20 = float(close.reindex(common[position - 19 : position + 1]).max())
    high60 = float(c.max())
    low10 = float(low.reindex(common[position - 9 : position + 1]).min())
    pullback = max(0.0, 1.0 - close_d / high20)
    rebound = bool(close_d > close_previous and close_d > REBOUND_LOW_MULTIPLIER * low10)
    target = high60 + TARGET_ATR_MULTIPLIER * atr14
    stop_ref = low10 - STOP_ATR_MULTIPLIER * atr14
    upside = max(target - close_d, UPSIDE_ATR_FLOOR * atr14)
    downside = max(close_d - stop_ref, DOWNSIDE_ATR_FLOOR * atr14)
    reward_risk = float(np.clip(upside / downside, 0.0, REWARD_RISK_CLIP_MAXIMUM))
    confirmed = bool(
        PULLBACK_MINIMUM <= pullback <= PULLBACK_MAXIMUM
        and rebound
        and reward_risk >= REWARD_RISK_MINIMUM
    )
    return {
        "signal_date": date.strftime("%Y-%m-%d"),
        "window_first_date": idx[0].strftime("%Y-%m-%d"),
        "window_last_date": idx[-1].strftime("%Y-%m-%d"),
        "close": close_d,
        "previous_close": close_previous,
        "true_ranges": true_range.tolist(),
        "atr14": atr14,
        "high20": high20,
        "high60": high60,
        "low10": low10,
        "pullback": pullback,
        "rebound": rebound,
        "target": target,
        "stop_ref": stop_ref,
        "upside": upside,
        "downside": downside,
        "reward_risk": reward_risk,
        "confirmed": confirmed,
    }


def _validate_parent_event_identity(
    event: dict[str, Any],
    round29_receipt: dict[str, Any],
    round30_receipt: dict[str, Any],
    round38_receipt: dict[str, Any],
) -> None:
    selected = list(event["selected"])
    ranked = list(event["ranked"])
    eligible = list(event["eligible"])
    scalar_checks = (
        int(round29_receipt.get("event_index", -1)) == int(event["event_index"]),
        int(round29_receipt.get("slot", -1)) == int(event["slot"]),
        str(round29_receipt.get("signal_date"))
        == event["signal_date"].strftime("%Y-%m-%d"),
        str(round29_receipt.get("entry_date"))
        == event["entry_date"].strftime("%Y-%m-%d"),
        str(round29_receipt.get("exit_date"))
        == event["exit_date"].strftime("%Y-%m-%d"),
        int(round29_receipt.get("eligible_count", -1)) == len(eligible),
        str(round29_receipt.get("eligible_sha256")) == _symbols_hash(eligible),
        list(round29_receipt.get("selected", [])) == selected,
        str(round29_receipt.get("selected_sha256")) == _symbols_hash(selected),
        selected == ranked[:PARENT_TOP_K],
        list(round38_receipt.get("window_top7", {}).get("20", [])) == selected,
        str(round38_receipt.get("window_ranked_sha256", {}).get("20"))
        == _symbols_hash(ranked),
        int(round38_receipt.get("event_index", -1)) == int(event["event_index"]),
        int(round38_receipt.get("slot", -1)) == int(event["slot"]),
        str(round38_receipt.get("signal_date"))
        == event["signal_date"].strftime("%Y-%m-%d"),
        str(round38_receipt.get("entry_date"))
        == event["entry_date"].strftime("%Y-%m-%d"),
        str(round38_receipt.get("exit_date"))
        == event["exit_date"].strftime("%Y-%m-%d"),
        int(round38_receipt.get("eligible_count", -1)) == len(eligible),
        str(round38_receipt.get("eligible_sha256")) == _symbols_hash(eligible),
    )
    if not all(scalar_checks):
        _fail(
            "lpr_parent_event_identity_mismatch",
            f"父事件 {event.get('event_index')} 的日期、eligible、Top-7 或排名漂移",
        )
    identity_fields = (
        "event_index",
        "slot",
        "signal_date",
        "entry_date",
        "exit_date",
        "eligible_count",
        "eligible_sha256",
        "selected",
        "selected_sha256",
    )
    if any(round30_receipt.get(field) != round29_receipt.get(field) for field in identity_fields):
        _fail(
            "lpr_parent_event_identity_mismatch",
            f"第 29／30 輪父事件 {event.get('event_index')} identity 不一致",
        )


def _build_lpr_events(
    panel: Any,
    cohort: list[str],
    parent_events: list[dict[str, Any]],
    frozen_ten_day_events: list[dict[str, Any]],
    frozen_parent_receipts: list[
        tuple[dict[str, Any], dict[str, Any], dict[str, Any]]
    ],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    if len(frozen_parent_receipts) != len(parent_events):
        _fail("lpr_parent_event_identity_mismatch", "父事件 identity 收據列數漂移")
    frozen_by_date = {str(row["signal_date"]): row for row in frozen_ten_day_events}
    rows: list[dict[str, Any]] = []
    receipts: list[dict[str, Any]] = []
    assignment_rows: list[dict[str, Any]] = []
    active_counts = pd.Series(0, index=panel.close.index, dtype=int)
    ten_day_residuals = {key: 0.0 for key in ("top7", "eligible", "complete", "qqq")}

    for parent, (round29_receipt, round30_receipt, round38_receipt) in zip(
        parent_events, frozen_parent_receipts, strict=True
    ):
        _validate_parent_event_identity(
            parent, round29_receipt, round30_receipt, round38_receipt
        )
        event = dict(parent)
        signal_date = event["signal_date"]
        entry_date = event["entry_date"]
        entry_position = int(panel.close.index.get_loc(entry_date))
        exit_position = entry_position + HOLDING_SESSIONS - 1
        exit_date = pd.Timestamp(panel.close.index[exit_position])
        gross = panel.close.loc[exit_date, cohort].div(panel.open.loc[entry_date, cohort]).sub(1.0)
        qqq_gross = float(panel.close.loc[exit_date, "QQQ"] / panel.open.loc[entry_date, "QQQ"] - 1.0)
        if not np.isfinite(gross.to_numpy(dtype=float)).all() or not np.isfinite(qqq_gross):
            _fail("lpr_ten_day_return_mismatch", "十日事件回報非有限")

        details: list[dict[str, Any]] = []
        selected: list[str] = []
        for ticker in event["selected"]:
            feature = compute_structure_feature(
                panel.open[ticker], panel.high[ticker], panel.low[ticker], panel.close[ticker], signal_date
            )
            detail = {"ticker": ticker, "parent_momentum_rank": event["ranked"].index(ticker), **feature}
            details.append(detail)
            if feature["confirmed"]:
                selected.append(ticker)

        n = len(selected)
        event.update(
            {
                "parent_exit_date_20d": parent["exit_date"],
                "exit_date": exit_date,
                "gross": gross,
                "qqq_gross": qqq_gross,
                "lpr_selected": selected,
                "candidate_count": n,
                "stock_target_fraction": n / STOCK_SUBSLOTS,
                "qqq_target_fraction": 1.0 - n / STOCK_SUBSLOTS,
                "feature_details": details,
            }
        )
        rows.append(event)
        assignment_rows.append(
            {
                "event_index": event["event_index"],
                "entry_date": entry_date.strftime("%Y-%m-%d"),
                "exit_date": exit_date.strftime("%Y-%m-%d"),
                "slot": event["slot"],
            }
        )
        active_counts.loc[entry_date:exit_date] += 1

        frozen = frozen_by_date.get(signal_date.strftime("%Y-%m-%d"))
        if frozen is None:
            _fail("lpr_parent_ten_day_receipt_mismatch", "父十日事件收據缺少訊號日")
        cost = 20.0 / 10_000.0
        observed_returns = {
            "top7": float(gross.loc[event["selected"]].mean() - cost),
            "eligible": float(gross.loc[event["eligible"]].mean() - cost),
            "complete": float(gross.mean() - cost),
            "qqq": float(qqq_gross - cost),
        }
        frozen_columns = {
            "top7": "top7_return",
            "eligible": "eligible_equal_return",
            "complete": "complete_cohort_equal_return",
            "qqq": "qqq_return",
        }
        if (
            frozen["entry_date"] != entry_date.strftime("%Y-%m-%d")
            or frozen["exit_date"] != exit_date.strftime("%Y-%m-%d")
            or int(frozen["eligible_count"]) != len(event["eligible"])
        ):
            _fail("lpr_parent_ten_day_receipt_mismatch", "父十日事件日期或 universe 漂移")
        for key, value in observed_returns.items():
            ten_day_residuals[key] = max(
                ten_day_residuals[key], abs(value - float(frozen[frozen_columns[key]]))
            )

        receipts.append(
            {
                "event_index": event["event_index"],
                "slot": event["slot"],
                "signal_date": signal_date.strftime("%Y-%m-%d"),
                "entry_date": entry_date.strftime("%Y-%m-%d"),
                "exit_date": exit_date.strftime("%Y-%m-%d"),
                "eligible_count": len(event["eligible"]),
                "eligible_sha256": _symbols_hash(event["eligible"]),
                "parent_top7": list(event["selected"]),
                "parent_top7_sha256": _symbols_hash(event["selected"]),
                "confirmed": selected,
                "confirmed_sha256": _symbols_hash(selected),
                "candidate_count": n,
                "stock_target_fraction": n / STOCK_SUBSLOTS,
                "qqq_target_fraction": 1.0 - n / STOCK_SUBSLOTS,
                "features": details,
            }
        )

    if len(rows) != EXPECTED_EVENTS:
        _fail("lpr_event_count_mismatch", "Round 39 不是原 905 宗事件")
    if max(ten_day_residuals.values()) > RECONSTRUCTION_TOLERANCE:
        _fail("lpr_parent_ten_day_receipt_mismatch", "父十日事件未逐列精確重播")
    slot_counts = [sum(row["slot"] == slot for row in rows) for slot in range(SLOT_COUNT)]
    for slot in range(SLOT_COUNT):
        slot_events = [row for row in rows if row["slot"] == slot]
        if any(
            left["exit_date"] >= right["entry_date"]
            for left, right in zip(slot_events[:-1], slot_events[1:], strict=True)
        ):
            _fail("lpr_slot_overlap_mismatch", "十日事件同槽重疊")
    assignment_sha256 = hashlib.sha256(
        json.dumps(assignment_rows, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return rows, receipts, {
        "ten_day_event_return_residuals": ten_day_residuals,
        "maximum_ten_day_event_return_residual": max(ten_day_residuals.values()),
        "assignment_sha256": assignment_sha256,
        "slot_event_counts": slot_counts,
        "maximum_concurrent_intervals": int(active_counts.max()),
        "last_ten_day_exit_date": rows[-1]["exit_date"].strftime("%Y-%m-%d"),
    }


def _weights_for_path(
    event: dict[str, Any], path_id: str, cohort: list[str]
) -> dict[str, float]:
    n = int(event["candidate_count"])
    fraction = n / STOCK_SUBSLOTS
    if n == 0 and path_id != "original_top7_10d_overlay":
        return {}
    if path_id == "lpr10_qqq_overlay":
        return {ticker: 1.0 / STOCK_SUBSLOTS for ticker in event["lpr_selected"]}
    if path_id == "matched_topn_10d_overlay":
        return {ticker: 1.0 / STOCK_SUBSLOTS for ticker in event["selected"][:n]}
    if path_id == "matched_eligible_10d_overlay":
        return {ticker: fraction / len(event["eligible"]) for ticker in event["eligible"]}
    if path_id == "matched_complete_10d_overlay":
        return {ticker: fraction / len(cohort) for ticker in cohort}
    if path_id == "original_top7_10d_overlay":
        return {ticker: 1.0 / STOCK_SUBSLOTS for ticker in event["selected"]}
    if path_id == "matched_qqq_switch_placebo":
        return {"__QQQ_SWITCH__": fraction} if fraction else {}
    _fail("lpr_path_family_mismatch", f"未知路徑 {path_id}")


def _price_ticker(ticker: str) -> str:
    return "QQQ" if ticker == "__QQQ_SWITCH__" else ticker


def _expected_switched_children(
    event: dict[str, Any], path_id: str, cohort_count: int
) -> int:
    n = int(event["candidate_count"])
    if path_id in {"lpr10_qqq_overlay", "matched_topn_10d_overlay"}:
        return n
    if path_id == "matched_eligible_10d_overlay":
        return len(event["eligible"]) if n > 0 else 0
    if path_id == "matched_complete_10d_overlay":
        return cohort_count if n > 0 else 0
    if path_id == "original_top7_10d_overlay":
        return PARENT_TOP_K
    if path_id == "matched_qqq_switch_placebo":
        return int(n > 0)
    _fail("lpr_path_family_mismatch", f"未知 order-count 路徑 {path_id}")


def _expected_overlay_order_receipt(
    events: list[dict[str, Any]], path_id: str, cohort_count: int
) -> dict[str, Any]:
    per_event: dict[int, int] = {}
    for position, event in enumerate(events):
        children = _expected_switched_children(event, path_id, cohort_count)
        per_event[int(event["event_index"])] = (
            0 if children == 0 else 2 * children + (1 if position == 0 else 2)
        )
    first_fraction_full = path_id == "original_top7_10d_overlay" or int(
        events[0]["candidate_count"]
    ) == STOCK_SUBSLOTS
    initial_base_qqq_orders = SLOT_COUNT - 1 + int(not first_fraction_full)
    total = initial_base_qqq_orders + sum(per_event.values()) + SLOT_COUNT
    encoded = json.dumps(
        {key: value for key, value in per_event.items() if value > 0},
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    return {
        "expected_total_orders": total,
        "initial_base_qqq_orders": initial_base_qqq_orders,
        "expected_terminal_liquidation_orders": SLOT_COUNT,
        "event_order_counts_sha256": hashlib.sha256(encoded).hexdigest(),
        "zero_candidate_event_indices": (
            []
            if path_id == "original_top7_10d_overlay"
            else [
                int(event["event_index"])
                for event in events
                if int(event["candidate_count"]) == 0
            ]
        ),
        "per_event": per_event,
    }


def _build_overlay_path(
    panel: Any,
    cohort: list[str],
    events: list[dict[str, Any]],
    path_id: str,
    one_way_leg_bps: int,
    fixed_child_order_fee_usd: float = 0.0,
    excluded_event_indices: frozenset[int] = frozenset(),
) -> dict[str, Any]:
    index = panel.close.loc[FIRST_SIGNAL_DATE:CALENDAR_LAST_DATE].index
    first_entry = pd.Timestamp(FIRST_ENTRY_DATE)
    final_date = pd.Timestamp(CALENDAR_LAST_DATE)
    first_position = int(index.get_loc(first_entry))
    side_cost = one_way_leg_bps / 10_000.0
    fixed_fee = fixed_child_order_fee_usd / INITIAL_CAPITAL_USD
    slot_initial = 1.0 / SLOT_COUNT
    traded_notional = pd.Series(0.0, index=index)
    proportional_cost_paid = pd.Series(0.0, index=index)
    fixed_cost_paid = pd.Series(0.0, index=index)
    child_orders = pd.Series(0, index=index, dtype=int)
    stock_order_notionals: list[float] = []
    order_ledger: list[dict[str, Any]] = []
    slot_values: list[pd.Series] = []
    stock_values: list[pd.Series] = []
    qqq_values: list[pd.Series] = []
    position_values: list[pd.Series] = []

    def execute(
        notional: float,
        date: pd.Timestamp,
        *,
        order_kind: str,
        event_index: int | None = None,
        ticker: str = "QQQ",
        stock_child: bool = False,
    ) -> float:
        if notional <= 0.0:
            return 0.0
        proportional = notional * side_cost
        if notional <= proportional + fixed_fee:
            _fail("lpr_fixed_fee_exhaustion", "固定費耗盡子委託名義金額")
        traded_notional.loc[date] += notional
        proportional_cost_paid.loc[date] += proportional
        fixed_cost_paid.loc[date] += fixed_fee
        child_orders.loc[date] += 1
        if stock_child:
            stock_order_notionals.append(notional * INITIAL_CAPITAL_USD)
        order_ledger.append(
            {
                "sequence": len(order_ledger) + 1,
                "slot": int(slot),
                "date": date.strftime("%Y-%m-%d"),
                "event_index": event_index,
                "ticker": _price_ticker(ticker),
                "order_kind": order_kind,
                "side": "sell" if "sell" in order_kind else "buy",
                "notional_usd": float(notional * INITIAL_CAPITAL_USD),
                "proportional_cost_usd": float(proportional * INITIAL_CAPITAL_USD),
                "fixed_fee_usd": float(fixed_fee * INITIAL_CAPITAL_USD),
            }
        )
        return notional - proportional - fixed_fee

    for slot in range(SLOT_COUNT):
        values = pd.Series(np.nan, index=index)
        stock_driver = pd.Series(0.0, index=index)
        qqq_driver = pd.Series(0.0, index=index)
        position_count = pd.Series(0, index=index, dtype=int)
        values.iloc[:first_position] = slot_initial
        slot_events = [
            event
            for event in events
            if event["slot"] == slot and event["event_index"] not in excluded_event_indices
        ]
        cursor = 0
        current: dict[str, Any] | None = None
        qqq_component = 0.0
        stock_components: dict[str, float] = {}

        for position in range(first_position, len(index)):
            date = pd.Timestamp(index[position])
            previous_date = pd.Timestamp(index[position - 1])
            next_event = slot_events[cursor] if cursor < len(slot_events) else None

            if position == first_position:
                event_now = next_event is not None and next_event["entry_date"] == date
                weights = _weights_for_path(next_event, path_id, cohort) if event_now else {}
                fraction = float(sum(weights.values()))
                if 1.0 - fraction > 0.0:
                    qqq_component = execute(
                        slot_initial * (1.0 - fraction),
                        date,
                        order_kind="qqq_initial_buy",
                    )
                stock_components = {
                    ticker: execute(
                        slot_initial * weight,
                        date,
                        order_kind=(
                            "qqq_switch_buy"
                            if ticker == "__QQQ_SWITCH__"
                            else "stock_buy"
                        ),
                        event_index=(int(next_event["event_index"]) if event_now else None),
                        ticker=ticker,
                        stock_child=ticker != "__QQQ_SWITCH__",
                    )
                    for ticker, weight in weights.items()
                }
                if not event_now and qqq_component == 0.0:
                    qqq_component = execute(
                        slot_initial, date, order_kind="qqq_initial_buy"
                    )
                open_to_close_qqq = float(panel.close.loc[date, "QQQ"] / panel.open.loc[date, "QQQ"])
                qqq_component *= open_to_close_qqq
                stock_components = {
                    ticker: value
                    * float(
                        panel.close.loc[date, _price_ticker(ticker)]
                        / panel.open.loc[date, _price_ticker(ticker)]
                    )
                    for ticker, value in stock_components.items()
                }
                if event_now:
                    current = next_event
            elif current is None:
                event_now = next_event is not None and next_event["entry_date"] == date
                qqq_component *= float(
                    panel.open.loc[date, "QQQ"] / panel.close.loc[previous_date, "QQQ"]
                    if event_now
                    else panel.close.loc[date, "QQQ"] / panel.close.loc[previous_date, "QQQ"]
                )
                if event_now:
                    weights = _weights_for_path(next_event, path_id, cohort)
                    fraction = float(sum(weights.values()))
                    if fraction > 0.0:
                        gross_sale = qqq_component * fraction
                        qqq_component *= 1.0 - fraction
                        sale_proceeds = execute(
                            gross_sale,
                            date,
                            order_kind="qqq_switch_sell",
                            event_index=int(next_event["event_index"]),
                        )
                        stock_components = {
                            ticker: execute(
                                sale_proceeds * weight / fraction,
                                date,
                                order_kind=(
                                    "qqq_switch_buy"
                                    if ticker == "__QQQ_SWITCH__"
                                    else "stock_buy"
                                ),
                                event_index=int(next_event["event_index"]),
                                ticker=ticker,
                                stock_child=ticker != "__QQQ_SWITCH__",
                            )
                            for ticker, weight in weights.items()
                        }
                    qqq_component *= float(
                        panel.close.loc[date, "QQQ"] / panel.open.loc[date, "QQQ"]
                    )
                    stock_components = {
                        ticker: value
                        * float(
                            panel.close.loc[date, _price_ticker(ticker)]
                            / panel.open.loc[date, _price_ticker(ticker)]
                        )
                        for ticker, value in stock_components.items()
                    }
                    current = next_event
            else:
                qqq_component *= float(
                    panel.close.loc[date, "QQQ"] / panel.close.loc[previous_date, "QQQ"]
                )
                stock_components = {
                    ticker: value
                    * float(
                        panel.close.loc[date, _price_ticker(ticker)]
                        / panel.close.loc[previous_date, _price_ticker(ticker)]
                    )
                    for ticker, value in stock_components.items()
                }

            if current is not None and current["exit_date"] == date:
                proceeds = sum(
                    execute(
                        value,
                        date,
                        order_kind=(
                            "qqq_switch_sell"
                            if ticker == "__QQQ_SWITCH__"
                            else "stock_sell"
                        ),
                        event_index=int(current["event_index"]),
                        ticker=ticker,
                        stock_child=ticker != "__QQQ_SWITCH__",
                    )
                    for ticker, value in stock_components.items()
                )
                stock_components = {}
                if proceeds > 0.0:
                    qqq_component += execute(
                        proceeds,
                        date,
                        order_kind="qqq_switch_buy",
                        event_index=int(current["event_index"]),
                    )
                current = None
                cursor += 1

            if date == final_date:
                if current is not None:
                    _fail("lpr_event_clock_mismatch", "最後結算日仍有未退出事件")
                qqq_component = execute(
                    qqq_component, date, order_kind="qqq_terminal_sell"
                )

            switched_value = float(sum(stock_components.values()))
            total = qqq_component + switched_value
            if not np.isfinite(total) or total <= 0.0:
                _fail("lpr_daily_identity_mismatch", "槽位資產非正或非有限")
            values.loc[date] = total
            if date == final_date:
                stock_driver.loc[date] = 0.0
                qqq_driver.loc[date] = 0.0
                position_count.loc[date] = 0
            elif path_id == "matched_qqq_switch_placebo":
                stock_driver.loc[date] = 0.0
                qqq_driver.loc[date] = total
                position_count.loc[date] = int(total > 0.0)
            else:
                stock_driver.loc[date] = switched_value
                qqq_driver.loc[date] = qqq_component
                position_count.loc[date] = int(qqq_component > 0.0) + sum(
                    int(value > 0.0) for value in stock_components.values()
                )

        if current is not None or cursor != len(slot_events) or values.isna().any():
            _fail("lpr_event_clock_mismatch", "事件未完整進出或日線缺值")
        slot_values.append(values)
        stock_values.append(stock_driver)
        qqq_values.append(qqq_driver)
        position_values.append(position_count)

    slot_frame = pd.concat(slot_values, axis=1)
    stock_frame = pd.concat(stock_values, axis=1)
    qqq_frame = pd.concat(qqq_values, axis=1)
    position_frame = pd.concat(position_values, axis=1)
    equity = slot_frame.sum(axis=1)
    stock_driver_value = stock_frame.sum(axis=1)
    qqq_driver_value = qqq_frame.sum(axis=1)
    invested = pd.Series(False, index=index)
    invested.loc[first_entry:] = True
    invested.loc[final_date] = False
    cash_value = equity.where(~invested, 0.0)
    returns = equity.pct_change(fill_method=None).fillna(0.0)
    total_cost_paid = proportional_cost_paid + fixed_cost_paid
    cost_identity = float(
        (
            total_cost_paid
            - traded_notional * side_cost
            - child_orders.astype(float) * fixed_fee
        ).abs().max()
    )
    return {
        "equity": equity,
        "returns": returns,
        "turnover": traded_notional.div(equity.shift(1).fillna(1.0)),
        "exposure": invested.astype(float),
        "cash_value": cash_value,
        "position_count": position_frame.sum(axis=1),
        "slot_values": slot_frame,
        "stock_driver_value": stock_driver_value,
        "qqq_driver_value": qqq_driver_value,
        "stock_driver_fraction": stock_driver_value.div(equity),
        "qqq_driver_fraction": qqq_driver_value.div(equity),
        "traded_notional": traded_notional,
        "proportional_cost_paid": proportional_cost_paid,
        "fixed_cost_paid": fixed_cost_paid,
        "cost_paid": total_cost_paid,
        "child_orders": child_orders,
        "total_child_orders": int(child_orders.sum()),
        "stock_child_order_notionals_usd": stock_order_notionals,
        "order_ledger_sha256": hashlib.sha256(
            json.dumps(order_ledger, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest(),
        "order_ledger": order_ledger,
        "maximum_daily_identity_residual": float((equity - slot_frame.sum(axis=1)).abs().max()),
        "maximum_driver_identity_residual": float(
            (equity - stock_driver_value - qqq_driver_value - cash_value).abs().max()
        ),
        "maximum_cost_identity_residual": cost_identity,
    }


def _build_buy_hold_path(
    panel: Any,
    ticker: str,
    one_way_leg_bps: int,
    fixed_child_order_fee_usd: float = 0.0,
) -> dict[str, Any]:
    index = panel.close.loc[FIRST_SIGNAL_DATE:CALENDAR_LAST_DATE].index
    first_entry = pd.Timestamp(FIRST_ENTRY_DATE)
    final_date = pd.Timestamp(CALENDAR_LAST_DATE)
    side_cost = one_way_leg_bps / 10_000.0
    fixed_fee = fixed_child_order_fee_usd / INITIAL_CAPITAL_USD
    values = pd.Series(1.0, index=index)
    traded = pd.Series(0.0, index=index)
    proportional = pd.Series(0.0, index=index)
    fixed = pd.Series(0.0, index=index)
    orders = pd.Series(0, index=index, dtype=int)
    order_ledger: list[dict[str, Any]] = []

    def execute(notional: float, date: pd.Timestamp, order_kind: str) -> float:
        if notional <= notional * side_cost + fixed_fee:
            _fail("lpr_fixed_fee_exhaustion", "買入並持有固定費耗盡資產")
        traded.loc[date] += notional
        proportional.loc[date] += notional * side_cost
        fixed.loc[date] += fixed_fee
        orders.loc[date] += 1
        order_ledger.append(
            {
                "sequence": len(order_ledger) + 1,
                "slot": None,
                "date": date.strftime("%Y-%m-%d"),
                "event_index": None,
                "ticker": ticker,
                "order_kind": order_kind,
                "side": "sell" if "sell" in order_kind else "buy",
                "notional_usd": float(notional * INITIAL_CAPITAL_USD),
                "proportional_cost_usd": float(notional * side_cost * INITIAL_CAPITAL_USD),
                "fixed_fee_usd": float(fixed_fee * INITIAL_CAPITAL_USD),
            }
        )
        return notional * (1.0 - side_cost) - fixed_fee

    entry_pos = int(index.get_loc(first_entry))
    amount = execute(1.0, first_entry, "buy_hold_entry_buy")
    amount *= float(panel.close.loc[first_entry, ticker] / panel.open.loc[first_entry, ticker])
    values.iloc[entry_pos] = amount
    for position in range(entry_pos + 1, len(index)):
        date = pd.Timestamp(index[position])
        previous = pd.Timestamp(index[position - 1])
        amount *= float(panel.close.loc[date, ticker] / panel.close.loc[previous, ticker])
        if date == final_date:
            amount = execute(amount, date, "buy_hold_terminal_sell")
        values.iloc[position] = amount
    total_cost = proportional + fixed
    exposure = pd.Series(0.0, index=index)
    exposure.loc[first_entry:] = 1.0
    exposure.loc[final_date] = 0.0
    driver = values.mul(exposure)
    cash_value = values.mul(1.0 - exposure)
    stock_driver = driver if ticker != "QQQ" else pd.Series(0.0, index=index)
    qqq_driver = driver if ticker == "QQQ" else pd.Series(0.0, index=index)
    return {
        "equity": values,
        "returns": values.pct_change(fill_method=None).fillna(0.0),
        "turnover": traded.div(values.shift(1).fillna(1.0)),
        "exposure": exposure,
        "cash_value": cash_value,
        "position_count": exposure.astype(int),
        "stock_driver_value": stock_driver,
        "qqq_driver_value": qqq_driver,
        "stock_driver_fraction": stock_driver.div(values),
        "qqq_driver_fraction": qqq_driver.div(values),
        "traded_notional": traded,
        "proportional_cost_paid": proportional,
        "fixed_cost_paid": fixed,
        "cost_paid": total_cost,
        "child_orders": orders,
        "total_child_orders": int(orders.sum()),
        "stock_child_order_notionals_usd": [],
        "order_ledger_sha256": hashlib.sha256(
            json.dumps(order_ledger, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest(),
        "order_ledger": order_ledger,
        "maximum_daily_identity_residual": 0.0,
        "maximum_driver_identity_residual": float(
            (values - stock_driver - qqq_driver - cash_value).abs().max()
        ),
        "maximum_cost_identity_residual": float(
            (total_cost - traded * side_cost - orders.astype(float) * fixed_fee).abs().max()
        ),
    }


def _load_round39_inputs(
    root: Path,
) -> tuple[
    Any,
    list[str],
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[tuple[dict[str, Any], dict[str, Any], dict[str, Any]]],
    dict[str, Any],
]:
    paths = {
        "protocol": root / PROTOCOL_PATH,
        "round38": root / ROUND38_RECEIPT_PATH,
        "round30": root / ROUND30_RECEIPT_PATH,
        "round29": root / ROUND29_RECEIPT_PATH,
        "event_receipt": root / EVENT_RECEIPT_PATH,
        "snapshot": root / SNAPSHOT_PATH,
        "watchlist": root / WATCHLIST_PATH,
    }
    expected = {
        "protocol": PROTOCOL_SHA256,
        "round38": ROUND38_RECEIPT_SHA256,
        "round30": ROUND30_RECEIPT_SHA256,
        "round29": ROUND29_RECEIPT_SHA256,
        "event_receipt": EVENT_RECEIPT_SHA256,
        "snapshot": SNAPSHOT_SHA256,
        "watchlist": WATCHLIST_SHA256,
    }
    codes = {
        "protocol": "lpr_protocol_hash_mismatch",
        "round38": "lpr_round38_receipt_mismatch",
        "round30": "lpr_round30_receipt_mismatch",
        "round29": "lpr_round29_receipt_mismatch",
        "event_receipt": "lpr_event_receipt_mismatch",
        "snapshot": "lpr_snapshot_mismatch",
        "watchlist": "lpr_watchlist_mismatch",
    }
    observed: dict[str, str] = {}
    for key, path in paths.items():
        if not path.is_file():
            _fail("lpr_input_missing", f"缺少固定輸入 {key}")
        observed[key] = _sha256_file(path)
        if observed[key] != expected[key]:
            _fail(codes[key], f"{key} SHA-256 漂移")

    try:
        panel, cohort, frozen_twenty, parent_meta = round29._load_inputs(
            root, round29.FROZEN_CONTRACT
        )
    except round29.CalendarCapitalAccountingError as exc:
        _fail("lpr_parent_input_replay_mismatch", f"{exc.code}: {exc.detail}")
    if parent_meta["hashes"]["panel"] != PANEL_SHA256:
        _fail("lpr_panel_mismatch", "panel fingerprint 漂移")
    source = json.loads(paths["event_receipt"].read_text(encoding="utf-8"))
    try:
        frozen_ten = source["taiwan_reference_signal_layer_diagnostic"]["horizons"]["10"][
            "event_series"
        ]
    except (KeyError, TypeError) as exc:
        _fail("lpr_event_receipt_mismatch", f"十日事件收據缺失：{exc}")
    if len(frozen_ten) != 907:
        _fail("lpr_event_receipt_mismatch", "十日事件母收據不是 907 列")
    parents: dict[str, dict[str, Any]] = {}
    for key, expected_round in (("round38", 38), ("round30", 30), ("round29", 29)):
        parent = json.loads(paths[key].read_text(encoding="utf-8"))
        parents[key] = parent
        if parent.get("research_round") != expected_round:
            _fail("lpr_parent_round_mismatch", f"{key} research_round 漂移")
    round29_events = parents["round29"].get("reconstruction", {}).get("event_receipts", [])
    round30_events = parents["round30"].get("reconstruction", {}).get("event_receipts", [])
    round38_events = parents["round38"].get("selection_receipts", [])
    if (
        len(round29_events) != EXPECTED_EVENTS
        or len(round30_events) != EXPECTED_EVENTS
        or len(round38_events) != EXPECTED_EVENTS
    ):
        _fail("lpr_parent_event_identity_mismatch", "父 event identity 收據不是 905 列")
    frozen_parent_receipts = list(
        zip(round29_events, round30_events, round38_events, strict=True)
    )
    receipts = {
        "paths": {key: str(path.relative_to(root)) for key, path in paths.items()},
        "hashes": {**observed, "panel": parent_meta["hashes"]["panel"]},
    }
    return panel, cohort, frozen_twenty, frozen_ten, frozen_parent_receipts, receipts


def _metric_summary(path: dict[str, Any], shy_proxy: pd.Series) -> dict[str, Any]:
    result: dict[str, Any] = dict(round29._path_metrics(path, shy_proxy))
    ledger = path["order_ledger"]
    ledger_notionals = [float(row["notional_usd"]) for row in ledger]
    event_order_counts = Counter(
        int(row["event_index"])
        for row in ledger
        if row["event_index"] is not None
    )
    result.update(
        {
            "average_stock_driver_fraction": float(path["stock_driver_fraction"].mean()),
            "average_qqq_driver_fraction": float(path["qqq_driver_fraction"].mean()),
            "total_traded_notional_usd": float(path["traded_notional"].sum() * INITIAL_CAPITAL_USD),
            "total_proportional_cost_usd": float(
                path["proportional_cost_paid"].sum() * INITIAL_CAPITAL_USD
            ),
            "total_fixed_cost_usd": float(path["fixed_cost_paid"].sum() * INITIAL_CAPITAL_USD),
            "total_child_orders": int(path["total_child_orders"]),
            "order_ledger_sha256": path["order_ledger_sha256"],
            "minimum_order_notional_usd": float(min(ledger_notionals)),
            "maximum_order_notional_usd": float(max(ledger_notionals)),
            "order_kind_counts": dict(Counter(row["order_kind"] for row in ledger)),
            "order_ticker_counts": dict(Counter(row["ticker"] for row in ledger)),
            "event_order_counts_sha256": hashlib.sha256(
                json.dumps(
                    dict(sorted(event_order_counts.items())),
                    sort_keys=True,
                    separators=(",", ":"),
                ).encode()
            ).hexdigest(),
            "minimum_stock_child_order_notional_usd": (
                float(min(path["stock_child_order_notionals_usd"]))
                if path["stock_child_order_notionals_usd"]
                else None
            ),
        }
    )
    return result


def _build_all_paths(
    panel: Any,
    cohort: list[str],
    events: list[dict[str, Any]],
    one_way_leg_bps: int,
    fixed_child_order_fee_usd: float = 0.0,
    excluded_event_indices: frozenset[int] = frozenset(),
) -> dict[str, dict[str, Any]]:
    paths = {
        path_id: _build_overlay_path(
            panel,
            cohort,
            events,
            path_id,
            one_way_leg_bps,
            fixed_child_order_fee_usd,
            excluded_event_indices,
        )
        for path_id in OVERLAY_PATH_IDS
    }
    paths.update(
        {
            f"{ticker.lower()}_buy_hold": _build_buy_hold_path(
                panel, ticker, one_way_leg_bps, fixed_child_order_fee_usd
            )
            for ticker in ("QQQ", "SPY", "SHY")
        }
    )
    return paths


def _build_analytical_qqq_placebo(
    panel: Any,
    events: list[dict[str, Any]],
    one_way_leg_bps: int,
    fixed_child_order_fee_usd: float = 0.0,
) -> dict[str, Any]:
    """Independent QQQ-only recurrence for the matched switch placebo identity."""
    index = panel.close.loc[FIRST_SIGNAL_DATE:CALENDAR_LAST_DATE].index
    first_entry = pd.Timestamp(FIRST_ENTRY_DATE)
    final_date = pd.Timestamp(CALENDAR_LAST_DATE)
    first_position = int(index.get_loc(first_entry))
    side_cost = one_way_leg_bps / 10_000.0
    fixed_fee = fixed_child_order_fee_usd / INITIAL_CAPITAL_USD
    traded = pd.Series(0.0, index=index)
    proportional = pd.Series(0.0, index=index)
    fixed = pd.Series(0.0, index=index)
    orders = pd.Series(0, index=index, dtype=int)
    slot_values: list[pd.Series] = []

    def execute(notional: float, date: pd.Timestamp) -> float:
        if notional <= 0.0:
            return 0.0
        if notional <= notional * side_cost + fixed_fee:
            _fail("lpr_fixed_fee_exhaustion", "placebo 固定費耗盡子委託")
        traded.loc[date] += notional
        proportional.loc[date] += notional * side_cost
        fixed.loc[date] += fixed_fee
        orders.loc[date] += 1
        return notional * (1.0 - side_cost) - fixed_fee

    for slot in range(SLOT_COUNT):
        values = pd.Series(np.nan, index=index)
        values.iloc[:first_position] = 1.0 / SLOT_COUNT
        qqq_base = 0.0
        qqq_switched = 0.0
        current: dict[str, Any] | None = None
        cursor = 0
        slot_events = [event for event in events if event["slot"] == slot]
        for position in range(first_position, len(index)):
            date = pd.Timestamp(index[position])
            previous = pd.Timestamp(index[position - 1])
            next_event = slot_events[cursor] if cursor < len(slot_events) else None
            event_now = next_event is not None and next_event["entry_date"] == date

            if position == first_position:
                fraction = (
                    float(next_event["stock_target_fraction"]) if event_now else 0.0
                )
                if 1.0 - fraction > 0.0:
                    qqq_base = execute((1.0 / SLOT_COUNT) * (1.0 - fraction), date)
                if fraction > 0.0:
                    qqq_switched = execute((1.0 / SLOT_COUNT) * fraction, date)
                qqq_open_close = float(
                    panel.close.loc[date, "QQQ"] / panel.open.loc[date, "QQQ"]
                )
                qqq_base *= qqq_open_close
                qqq_switched *= qqq_open_close
                if event_now:
                    current = next_event
            elif current is None:
                qqq_base *= float(
                    panel.open.loc[date, "QQQ"] / panel.close.loc[previous, "QQQ"]
                    if event_now
                    else panel.close.loc[date, "QQQ"] / panel.close.loc[previous, "QQQ"]
                )
                if event_now:
                    fraction = float(next_event["stock_target_fraction"])
                    if fraction > 0.0:
                        sale_notional = qqq_base * fraction
                        qqq_base -= sale_notional
                        qqq_switched = execute(execute(sale_notional, date), date)
                    qqq_open_close = float(
                        panel.close.loc[date, "QQQ"] / panel.open.loc[date, "QQQ"]
                    )
                    qqq_base *= qqq_open_close
                    qqq_switched *= qqq_open_close
                    current = next_event
            else:
                qqq_close_close = float(
                    panel.close.loc[date, "QQQ"] / panel.close.loc[previous, "QQQ"]
                )
                qqq_base *= qqq_close_close
                qqq_switched *= qqq_close_close

            if current is not None and current["exit_date"] == date:
                if qqq_switched > 0.0:
                    qqq_base += execute(execute(qqq_switched, date), date)
                    qqq_switched = 0.0
                current = None
                cursor += 1
            if date == final_date:
                if current is not None:
                    _fail("lpr_event_clock_mismatch", "placebo 最後仍有未退出事件")
                qqq_base = execute(qqq_base, date)
            values.loc[date] = qqq_base + qqq_switched
        if current is not None or cursor != len(slot_events) or values.isna().any():
            _fail("lpr_event_clock_mismatch", "placebo 事件時鐘不完整")
        slot_values.append(values)

    equity = pd.concat(slot_values, axis=1).sum(axis=1)
    return {
        "equity": equity,
        "traded_notional": traded,
        "proportional_cost_paid": proportional,
        "fixed_cost_paid": fixed,
        "cost_paid": proportional + fixed,
        "child_orders": orders,
        "total_child_orders": int(orders.sum()),
    }


def _common_bootstrap(
    matrix: np.ndarray, observed_t: np.ndarray, standard_errors: np.ndarray
) -> dict[str, Any]:
    centered = matrix - matrix.mean(axis=0, keepdims=True)
    if not np.allclose(centered.mean(axis=0), 0.0, atol=1e-15):
        _fail("lpr_bootstrap_centering_mismatch", "bootstrap 去中心化失敗")
    if (standard_errors <= 0.0).any() or not np.isfinite(standard_errors).all():
        _fail("lpr_bootstrap_standard_error_mismatch", "NW 標準誤非正或非有限")
    rows, columns = centered.shape
    blocks_per_path = math.ceil(rows / BOOTSTRAP_BLOCK_SESSIONS)
    final_block_sessions = rows - (blocks_per_path - 1) * BOOTSTRAP_BLOCK_SESSIONS
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    starts = rng.integers(
        0, rows, size=(BOOTSTRAP_PATHS, blocks_per_path), dtype=np.int64
    )
    extended = np.concatenate(
        [centered, centered[: BOOTSTRAP_BLOCK_SESSIONS - 1]], axis=0
    )
    cumulative = np.vstack([np.zeros((1, columns)), np.cumsum(extended, axis=0)])
    positions = np.arange(rows, dtype=np.int64)
    full_sums = (
        cumulative[positions + BOOTSTRAP_BLOCK_SESSIONS] - cumulative[positions]
    )
    final_sums = cumulative[positions + final_block_sessions] - cumulative[positions]
    max_abs = np.zeros(BOOTSTRAP_PATHS, dtype=float)
    for column in range(columns):
        sums = full_sums[starts[:, :-1], column].sum(axis=1)
        sums += final_sums[starts[:, -1], column]
        boot_t = sums / rows / standard_errors[column]
        max_abs = np.maximum(max_abs, np.abs(boot_t))
    p_values = (
        1.0
        + (max_abs[:, None] >= np.abs(observed_t)[None, :]).sum(axis=0).astype(float)
    ) / (BOOTSTRAP_PATHS + 1.0)
    return {
        "block_sessions": BOOTSTRAP_BLOCK_SESSIONS,
        "paths": BOOTSTRAP_PATHS,
        "seed": BOOTSTRAP_SEED,
        "circular": True,
        "common_indices": True,
        "centered_under_null": True,
        "blocks_per_path": blocks_per_path,
        "final_block_sessions": final_block_sessions,
        "start_index_sha256": hashlib.sha256(starts.tobytes()).hexdigest(),
        "single_step_max_t_p": p_values.tolist(),
    }


_CONTRACT_ATTACK_CODES = {
    "protocol_sha256": "lpr_protocol_hash_mismatch",
    "protocol_commit": "lpr_protocol_commit_mismatch",
    "parent_main_commit": "lpr_parent_commit_mismatch",
    "round38_receipt_sha256": "lpr_round38_receipt_mismatch",
    "round30_receipt_sha256": "lpr_round30_receipt_mismatch",
    "round29_receipt_sha256": "lpr_round29_receipt_mismatch",
    "event_receipt_sha256": "lpr_event_receipt_mismatch",
    "snapshot_sha256": "lpr_snapshot_mismatch",
    "panel_sha256": "lpr_panel_mismatch",
    "watchlist_sha256": "lpr_watchlist_mismatch",
    "reference_commits": "lpr_reference_mismatch",
    "expected_events": "lpr_event_count_mismatch",
    "expected_cohort": "lpr_cohort_mismatch",
    "expected_calendar_sessions": "lpr_calendar_mismatch",
    "parent_momentum_sessions": "lpr_parent_momentum_mismatch",
    "parent_trend_sessions": "lpr_parent_trend_mismatch",
    "parent_top_k": "lpr_parent_top_k_mismatch",
    "minimum_price_usd": "lpr_price_floor_mismatch",
    "dollar_volume_sessions": "lpr_liquidity_window_mismatch",
    "minimum_median_dollar_volume_usd": "lpr_liquidity_floor_mismatch",
    "atr_sessions": "lpr_atr_window_mismatch",
    "high20_sessions": "lpr_high20_window_mismatch",
    "high60_sessions": "lpr_high60_window_mismatch",
    "low10_sessions": "lpr_low10_window_mismatch",
    "pullback_minimum": "lpr_pullback_minimum_mismatch",
    "pullback_maximum": "lpr_pullback_maximum_mismatch",
    "rebound_low_multiplier": "lpr_rebound_mismatch",
    "target_atr_multiplier": "lpr_target_mismatch",
    "stop_atr_multiplier": "lpr_stop_mismatch",
    "upside_atr_floor": "lpr_upside_floor_mismatch",
    "downside_atr_floor": "lpr_downside_floor_mismatch",
    "reward_risk_minimum": "lpr_reward_risk_minimum_mismatch",
    "reward_risk_clip_maximum": "lpr_reward_risk_clip_mismatch",
    "stock_subslots": "lpr_subslots_mismatch",
    "allocation_rule": "lpr_allocation_mismatch",
    "entry_delay": "lpr_entry_clock_mismatch",
    "holding_sessions": "lpr_holding_clock_mismatch",
    "slot_count": "lpr_slot_count_mismatch",
    "events_per_slot": "lpr_events_per_slot_mismatch",
    "initial_capital_usd": "lpr_initial_capital_mismatch",
    "parent_assignment_sha256": "lpr_parent_assignment_mismatch",
    "inactive_asset": "lpr_inactive_asset_mismatch",
    "primary_one_way_leg_bps": "lpr_primary_cost_mismatch",
    "cost_stress_one_way_leg_bps": "lpr_cost_stress_mismatch",
    "fixed_child_order_fee_stress_usd": "lpr_fixed_fee_mismatch",
    "four_legs_per_switched_subslot": "lpr_four_leg_mismatch",
    "path_ids": "lpr_path_family_mismatch",
    "family_baseline_ids": "lpr_hypothesis_family_mismatch",
    "shy_excess_proxy": "lpr_shy_proxy_mismatch",
    "hac_lag": "lpr_hac_mismatch",
    "family_alpha": "lpr_family_alpha_mismatch",
    "bootstrap_block_sessions": "lpr_bootstrap_block_mismatch",
    "bootstrap_paths": "lpr_bootstrap_paths_mismatch",
    "bootstrap_seed": "lpr_bootstrap_seed_mismatch",
    "common_bootstrap_indices": "lpr_bootstrap_indices_mismatch",
    "centered_under_null": "lpr_bootstrap_centering_mismatch",
    "global_search_trials": "lpr_global_trials_mismatch",
    "first_half_end": "lpr_first_half_mismatch",
    "second_half_start": "lpr_second_half_mismatch",
    "crisis_years": "lpr_crisis_mismatch",
    "best_year_removal_count": "lpr_best_year_mismatch",
    "favorable_event_removal_count": "lpr_tail_mismatch",
    "formal_readiness": "lpr_formal_readiness_mismatch",
    "point_in_time_readiness": "lpr_pit_readiness_mismatch",
    "qualified_provider_packages": "lpr_provider_boundary_mismatch",
    "formal_strategy_runs": "lpr_formal_run_boundary_mismatch",
    "current_identifiers_only": "lpr_identifier_scope_mismatch",
    "paper_authorized": "lpr_paper_boundary_breached",
    "real_money_authorized": "lpr_real_money_boundary_breached",
}


def _mutate_contract_value(value: Any) -> Any:
    mutators: tuple[tuple[Callable[[Any], bool], Callable[[Any], Any]], ...] = (
        (lambda item: isinstance(item, bool), lambda item: not item),
        (lambda item: isinstance(item, int), lambda item: item + 1),
        (lambda item: isinstance(item, float), lambda item: item + 0.12345),
        (lambda item: isinstance(item, str), lambda item: item + "-mutation"),
        (lambda item: isinstance(item, tuple), lambda item: item + (item[-1],)),
    )
    for predicate, mutate in mutators:
        if predicate(value):
            return mutate(value)
    raise TypeError(f"unsupported contract attack value {type(value)!r}")


def run_contract_attacks() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for index, (field, expected_code) in enumerate(_CONTRACT_ATTACK_CODES.items(), 1):
        observed_code: str | None = None
        attacked = replace(
            FROZEN_CONTRACT,
            **{field: _mutate_contract_value(getattr(FROZEN_CONTRACT, field))},
        )
        try:
            validate_leader_pullback_rebound_contract(attacked)
        except LeaderPullbackReboundError as exc:
            observed_code = exc.code
        rows.append(
            {
                "id": f"{index:02d}",
                "field": field,
                "expected_error_code": expected_code,
                "observed_error_code": observed_code,
                "rejected": observed_code == expected_code,
            }
        )
    attack_index = len(rows)

    eligible = list("ABCDEFGHI")
    ranked = list("IHGFEDCBA")
    selected = ranked[:PARENT_TOP_K]
    parent_event = {
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
    parent_event["selected"][0], parent_event["selected"][1] = (
        parent_event["selected"][1],
        parent_event["selected"][0],
    )

    synthetic_index = pd.bdate_range("2025-01-02", periods=80)
    synthetic_close = pd.Series(np.linspace(80.0, 100.0, 80), index=synthetic_index)
    synthetic_open = synthetic_close * 0.999
    synthetic_high = pd.concat([synthetic_open, synthetic_close], axis=1).max(axis=1) + 1.0
    synthetic_low = pd.concat([synthetic_open, synthetic_close], axis=1).min(axis=1) - 1.0

    runtime_attacks: list[tuple[str, str, Callable[[], None]]] = [
        (
            "parent_top7_order",
            "lpr_parent_event_identity_mismatch",
            lambda: _validate_parent_event_identity(
                parent_event, round29_receipt, dict(round29_receipt), round38_receipt
            ),
        ),
        (
            "ohlc_index_drop",
            "lpr_ohlc_index_mismatch",
            lambda: compute_structure_feature(
                synthetic_open,
                synthetic_high.drop(synthetic_high.index[-10]),
                synthetic_low,
                synthetic_close,
                synthetic_index[-1],
            ),
        ),
        (
            "ohlc_geometry",
            "lpr_ohlc_geometry_mismatch",
            lambda: compute_structure_feature(
                synthetic_open,
                synthetic_high.mask(
                    synthetic_high.index == synthetic_index[-1],
                    synthetic_close.iloc[-1] - 1.0,
                ),
                synthetic_low,
                synthetic_close,
                synthetic_index[-1],
            ),
        ),
    ]
    for offset, (attack_id, expected_code, action) in enumerate(runtime_attacks, 1):
        observed_code = None
        try:
            action()
        except LeaderPullbackReboundError as exc:
            observed_code = exc.code
        rows.append(
            {
                "id": f"{attack_index + offset:02d}",
                "field": attack_id,
                "expected_error_code": expected_code,
                "observed_error_code": observed_code,
                "rejected": observed_code == expected_code,
            }
        )
    return rows


def _nw10(values: np.ndarray) -> dict[str, float | int]:
    result = round29.newey_west_mean_test(
        pd.Series(values), max_lag=HAC_LAG, periods_per_year=252
    )
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


def run_leader_pullback_rebound(root: str | Path) -> dict[str, Any]:
    """Run the frozen Round 39 falsification receipt; never authorizes trading."""
    root_path = Path(root).resolve()
    validate_leader_pullback_rebound_contract(FROZEN_CONTRACT)
    (
        panel,
        cohort,
        frozen_twenty,
        frozen_ten,
        frozen_parent_receipts,
        input_receipts,
    ) = _load_round39_inputs(root_path)
    try:
        parent_events, parent_reconstruction = round29._reconstruct_events(
            panel, cohort, frozen_twenty
        )
    except round29.CalendarCapitalAccountingError as exc:
        _fail("lpr_parent_event_replay_mismatch", f"{exc.code}: {exc.detail}")
    events, selection_receipts, ten_day_reconstruction = _build_lpr_events(
        panel, cohort, parent_events, frozen_ten, frozen_parent_receipts
    )
    index = panel.close.loc[FIRST_SIGNAL_DATE:CALENDAR_LAST_DATE].index
    if len(index) != EXPECTED_CALENDAR_SESSIONS:
        _fail("lpr_calendar_mismatch", "共同日線不是固定 5,028 列")
    shy_proxy = panel.close.loc[index, "SHY"].pct_change(fill_method=None).fillna(0.0)
    primary_paths = _build_all_paths(panel, cohort, events, PRIMARY_ONE_WAY_LEG_BPS)
    metrics = {
        path_id: {
            **_metric_summary(primary_paths[path_id], shy_proxy),
            "path_id": path_id,
            "label": PATH_LABELS[path_id],
            "one_way_leg_cost_bps": PRIMARY_ONE_WAY_LEG_BPS,
        }
        for path_id in PATH_IDS
    }

    zero_paths = _build_all_paths(panel, cohort, events, 0)
    zero_metrics = {
        path_id: _metric_summary(zero_paths[path_id], shy_proxy) for path_id in PATH_IDS
    }
    cost_path_sets = {
        str(cost): _build_all_paths(panel, cohort, events, cost)
        for cost in COST_STRESS_ONE_WAY_LEG_BPS
    }
    fixed_path_sets = {
        f"{fee:.2f}": _build_all_paths(
            panel, cohort, events, PRIMARY_ONE_WAY_LEG_BPS, fee
        )
        for fee in FIXED_CHILD_ORDER_FEE_STRESS_USD
    }
    fixed_metrics = {
        fee: {
            path_id: _metric_summary(paths[path_id], shy_proxy)
            for path_id in PATH_IDS
        }
        for fee, paths in fixed_path_sets.items()
    }
    for path_id in PATH_IDS:
        metrics[path_id]["proportional_cost_drag_cagr"] = (
            zero_metrics[path_id]["cagr"] - metrics[path_id]["cagr"]
        )
        metrics[path_id]["proportional_cost_drag_terminal_usd"] = (
            zero_metrics[path_id]["terminal_usd"] - metrics[path_id]["terminal_usd"]
        )
        metrics[path_id]["fixed_fee_stress"] = {
            fee: {
                "terminal_usd": fixed_metrics[fee][path_id]["terminal_usd"],
                "cagr": fixed_metrics[fee][path_id]["cagr"],
                "terminal_drag_usd_vs_primary": (
                    metrics[path_id]["terminal_usd"]
                    - fixed_metrics[fee][path_id]["terminal_usd"]
                ),
                "fixed_cost_usd": fixed_metrics[fee][path_id]["total_fixed_cost_usd"],
                "actual_child_orders": fixed_metrics[fee][path_id]["total_child_orders"],
            }
            for fee in fixed_metrics
        }

    analytical_placebo = _build_analytical_qqq_placebo(
        panel, events, PRIMARY_ONE_WAY_LEG_BPS
    )
    placebo_path = primary_paths["matched_qqq_switch_placebo"]
    placebo_residuals = {
        "equity": float((placebo_path["equity"] - analytical_placebo["equity"]).abs().max()),
        "traded_notional": float(
            (placebo_path["traded_notional"] - analytical_placebo["traded_notional"])
            .abs()
            .max()
        ),
        "proportional_cost": float(
            (
                placebo_path["proportional_cost_paid"]
                - analytical_placebo["proportional_cost_paid"]
            )
            .abs()
            .max()
        ),
        "fixed_cost": float(
            (placebo_path["fixed_cost_paid"] - analytical_placebo["fixed_cost_paid"])
            .abs()
            .max()
        ),
        "child_orders": int(
            (placebo_path["child_orders"] - analytical_placebo["child_orders"])
            .abs()
            .max()
        ),
    }
    placebo_maximum_residual = max(float(value) for value in placebo_residuals.values())

    order_receipts: dict[str, Any] = {}
    for path_id in OVERLAY_PATH_IDS:
        expected_order = _expected_overlay_order_receipt(events, path_id, len(cohort))
        ledger = primary_paths[path_id]["order_ledger"]
        actual_event_counts = Counter(
            int(row["event_index"])
            for row in ledger
            if row["event_index"] is not None
        )
        zero_event_indices = set(expected_order["zero_candidate_event_indices"])
        zero_event_order_count = sum(
            count for event_index, count in actual_event_counts.items() if event_index in zero_event_indices
        )
        order_receipts[path_id] = {
            key: value for key, value in expected_order.items() if key != "per_event"
        }
        order_receipts[path_id].update(
            {
                "actual_total_orders": int(primary_paths[path_id]["total_child_orders"]),
                "actual_terminal_liquidation_orders": int(
                    sum(
                        row["order_kind"] == "qqq_terminal_sell" for row in ledger
                    )
                ),
                "actual_order_ledger_sha256": primary_paths[path_id]["order_ledger_sha256"],
                "actual_event_order_counts_sha256": metrics[path_id][
                    "event_order_counts_sha256"
                ],
                "event_order_counts_hash_match": expected_order[
                    "event_order_counts_sha256"
                ]
                == metrics[path_id]["event_order_counts_sha256"],
                "maximum_event_order_count_residual": max(
                    abs(
                        expected_order["per_event"].get(event_index, 0)
                        - actual_event_counts.get(event_index, 0)
                    )
                    for event_index in set(expected_order["per_event"])
                    | set(actual_event_counts)
                ),
                "zero_candidate_event_actual_orders": int(zero_event_order_count),
                "minimum_order_notional_usd": metrics[path_id][
                    "minimum_order_notional_usd"
                ],
                "maximum_order_notional_usd": metrics[path_id][
                    "maximum_order_notional_usd"
                ],
            }
        )
        metrics[path_id]["order_receipt"] = order_receipts[path_id]
    for path_id in ("qqq_buy_hold", "spy_buy_hold", "shy_buy_hold"):
        order_receipts[path_id] = {
            "expected_total_orders": 2,
            "actual_total_orders": int(primary_paths[path_id]["total_child_orders"]),
            "expected_terminal_liquidation_orders": 1,
            "actual_terminal_liquidation_orders": int(
                sum(
                    row["order_kind"] == "buy_hold_terminal_sell"
                    for row in primary_paths[path_id]["order_ledger"]
                )
            ),
            "actual_order_ledger_sha256": primary_paths[path_id]["order_ledger_sha256"],
            "minimum_order_notional_usd": metrics[path_id]["minimum_order_notional_usd"],
            "maximum_order_notional_usd": metrics[path_id]["maximum_order_notional_usd"],
        }
        metrics[path_id]["order_receipt"] = order_receipts[path_id]

    candidate_returns = primary_paths["lpr10_qqq_overlay"]["returns"]
    comparisons: list[dict[str, Any]] = []
    family_columns: list[np.ndarray] = []
    family_differences: dict[str, np.ndarray] = {}
    for baseline_id in FAMILY_BASELINE_IDS:
        values = (
            candidate_returns - primary_paths[baseline_id]["returns"]
        ).to_numpy(dtype=float)
        family_differences[baseline_id] = values
        nw = _nw10(values)
        comparisons.append(
            {
                "baseline_id": baseline_id,
                "baseline_label": PATH_LABELS[baseline_id],
                "sessions": len(values),
                "mean_daily_difference": float(values.mean()),
                "median_daily_difference": float(np.median(values)),
                "annualized_arithmetic_difference": float(values.mean() * 252.0),
                "positive_fraction": float((values > 0.0).mean()),
                "newey_west": nw,
                "raw_normal_p": round29._normal_two_sided_p(float(nw["t_stat"])),
                "fixed_halves": round29._fixed_halves(values, index),
                "annual_active_returns": round29._annual_active(values, index),
            }
        )
        family_columns.append(values)
    holm = round29._holm_adjust(comparisons)
    observed_t = np.asarray(
        [float(row["newey_west"]["t_stat"]) for row in comparisons], dtype=float
    )
    standard_errors = np.asarray(
        [float(row["newey_west"]["standard_error"]) for row in comparisons], dtype=float
    )
    bootstrap = _common_bootstrap(
        np.column_stack(family_columns), observed_t, standard_errors
    )
    for position, row in enumerate(comparisons):
        row["holm_adjusted_p"] = holm[row["baseline_id"]]
        row["bootstrap_max_t_p"] = bootstrap["single_step_max_t_p"][position]
        row["family_bonferroni_p"] = min(
            1.0, float(row["raw_normal_p"]) * len(comparisons)
        )
        row["global_bonferroni_p"] = min(
            1.0, float(row["raw_normal_p"]) * GLOBAL_SEARCH_TRIALS
        )
    comparison_by_id = {row["baseline_id"]: row for row in comparisons}

    qqq_annual = comparison_by_id["qqq_buy_hold"]["annual_active_returns"]
    removed_years = [
        int(row["year"])
        for row in sorted(
            qqq_annual,
            key=lambda row: (-float(row["compounded_active_return"]), int(row["year"])),
        )[:BEST_YEAR_REMOVAL_COUNT]
    ]
    best_year_mask = ~np.isin(index.year, removed_years)
    best_year_values = family_differences["qqq_buy_hold"][best_year_mask]
    best_year_stress = {
        "selection_basis": "highest_candidate_minus_qqq_compounded_active_year",
        "removed_years": removed_years,
        "remaining_sessions": int(best_year_mask.sum()),
        "mean_daily_difference": float(best_year_values.mean()),
        "newey_west": _nw10(best_year_values),
    }

    crises = {
        str(year): {
            path_id: round29._crisis_metrics(primary_paths[path_id], year)
            for path_id in PATH_IDS
        }
        for year in CRISIS_YEARS
    }
    qqq_momentum20 = panel.close["QQQ"].pct_change(20, fill_method=None)
    regime_events: dict[str, list[dict[str, Any]]] = {"nonnegative": [], "negative": []}
    event_increments: list[dict[str, Any]] = []
    for event in events:
        candidate_weights = _weights_for_path(event, "lpr10_qqq_overlay", cohort)
        matched_weights = _weights_for_path(event, "matched_topn_10d_overlay", cohort)
        candidate_gross = float(event["qqq_gross"]) + sum(
            weight * (float(event["gross"].loc[ticker]) - float(event["qqq_gross"]))
            for ticker, weight in candidate_weights.items()
        )
        matched_gross = float(event["qqq_gross"]) + sum(
            weight * (float(event["gross"].loc[ticker]) - float(event["qqq_gross"]))
            for ticker, weight in matched_weights.items()
        )
        row = {
            "event_index": int(event["event_index"]),
            "candidate_count": int(event["candidate_count"]),
            "stock_fraction": float(event["stock_target_fraction"]),
            "candidate_gross": candidate_gross,
            "matched_topn_gross": matched_gross,
            "candidate_minus_matched_topn_gross": candidate_gross - matched_gross,
        }
        event_increments.append(row)
        regime = (
            "nonnegative"
            if float(qqq_momentum20.loc[event["signal_date"]]) >= 0.0
            else "negative"
        )
        regime_events[regime].append(row)
    regime_rows = {
        regime: {
            "events": len(rows),
            "average_candidates": float(np.mean([row["candidate_count"] for row in rows])),
            "average_stock_fraction": float(np.mean([row["stock_fraction"] for row in rows])),
            "average_event_increment": float(
                np.mean([row["candidate_minus_matched_topn_gross"] for row in rows])
            ),
            "median_event_increment": float(
                np.median([row["candidate_minus_matched_topn_gross"] for row in rows])
            ),
        }
        for regime, rows in regime_events.items()
    }
    favorable = sorted(
        event_increments,
        key=lambda row: (-row["candidate_minus_matched_topn_gross"], row["event_index"]),
    )[:FAVORABLE_EVENT_REMOVAL_COUNT]
    tail_exclusions = frozenset(int(row["event_index"]) for row in favorable)
    tail_paths = _build_all_paths(
        panel,
        cohort,
        events,
        PRIMARY_ONE_WAY_LEG_BPS,
        excluded_event_indices=tail_exclusions,
    )
    tail_metrics = {
        path_id: _metric_summary(tail_paths[path_id], shy_proxy) for path_id in PATH_IDS
    }
    tail_stress = {
        "selection_basis": "highest_candidate_minus_matched_topn_event_gross_increment",
        "removed_event_count": len(tail_exclusions),
        "removed_event_indices": sorted(tail_exclusions),
        "paths": {path_id: tail_metrics[path_id] for path_id in OVERLAY_PATH_IDS},
        "candidate_cagr_differences": {
            baseline_id: tail_metrics["lpr10_qqq_overlay"]["cagr"]
            - (
                metrics[baseline_id]["cagr"]
                if baseline_id == "qqq_buy_hold"
                else tail_metrics[baseline_id]["cagr"]
            )
            for baseline_id in (
                "qqq_buy_hold",
                "matched_topn_10d_overlay",
                "original_top7_10d_overlay",
                "matched_eligible_10d_overlay",
                "matched_complete_10d_overlay",
            )
        },
    }

    cost_stresses: dict[str, Any] = {}
    for cost, paths in cost_path_sets.items():
        rows = {path_id: _metric_summary(paths[path_id], shy_proxy) for path_id in PATH_IDS}
        cost_stresses[cost] = {
            "one_way_leg_cost_bps": int(cost),
            "paths": rows,
            "candidate_cagr_differences": {
                baseline_id: rows["lpr10_qqq_overlay"]["cagr"] - rows[baseline_id]["cagr"]
                for baseline_id in (
                    "qqq_buy_hold",
                    "matched_topn_10d_overlay",
                    "original_top7_10d_overlay",
                    "matched_eligible_10d_overlay",
                    "matched_complete_10d_overlay",
                )
            },
        }
    fixed_fee_stresses: dict[str, Any] = {}
    for fee, _paths in fixed_path_sets.items():
        rows = fixed_metrics[fee]
        fee_value = float(fee)
        fixed_identity = max(
            abs(
                rows[path_id]["total_fixed_cost_usd"]
                - rows[path_id]["total_child_orders"] * fee_value
            )
            for path_id in PATH_IDS
        )
        fixed_fee_stresses[fee] = {
            "fixed_child_order_fee_usd": fee_value,
            "paths": rows,
            "maximum_fixed_fee_identity_residual_usd": fixed_identity,
            "candidate_cagr_differences": {
                baseline_id: rows["lpr10_qqq_overlay"]["cagr"] - rows[baseline_id]["cagr"]
                for baseline_id in (
                    "qqq_buy_hold",
                    "matched_topn_10d_overlay",
                    "original_top7_10d_overlay",
                    "matched_eligible_10d_overlay",
                    "matched_complete_10d_overlay",
                )
            },
        }
    counts = Counter(int(event["candidate_count"]) for event in events)
    nonempty = [event for event in events if event["candidate_count"] > 0]
    nonempty_first_half = sum(
        event["candidate_count"] > 0 and event["signal_date"] <= FIRST_HALF_END
        for event in events
    )
    nonempty_second_half = sum(
        event["candidate_count"] > 0 and event["signal_date"] >= SECOND_HALF_START
        for event in events
    )
    feature_details = [
        detail for receipt in selection_receipts for detail in receipt["features"]
    ]
    formula_residuals: list[float] = []
    for detail in feature_details:
        formula_residuals.extend(
            [
                abs(float(detail["atr14"]) - float(np.mean(detail["true_ranges"]))),
                abs(
                    float(detail["pullback"])
                    - max(0.0, 1.0 - float(detail["close"]) / float(detail["high20"]))
                ),
                abs(
                    float(detail["target"])
                    - (
                        float(detail["high60"])
                        + TARGET_ATR_MULTIPLIER * float(detail["atr14"])
                    )
                ),
                abs(
                    float(detail["stop_ref"])
                    - (
                        float(detail["low10"])
                        - STOP_ATR_MULTIPLIER * float(detail["atr14"])
                    )
                ),
                abs(
                    float(detail["upside"])
                    - max(
                        float(detail["target"]) - float(detail["close"]),
                        UPSIDE_ATR_FLOOR * float(detail["atr14"]),
                    )
                ),
                abs(
                    float(detail["downside"])
                    - max(
                        float(detail["close"]) - float(detail["stop_ref"]),
                        DOWNSIDE_ATR_FLOOR * float(detail["atr14"]),
                    )
                ),
                abs(
                    float(detail["reward_risk"])
                    - float(
                        np.clip(
                            float(detail["upside"]) / float(detail["downside"]),
                            0.0,
                            REWARD_RISK_CLIP_MAXIMUM,
                        )
                    )
                ),
            ]
        )
    maximum_feature_formula_residual = max(formula_residuals)
    feature_boolean_identities = all(
        bool(detail["rebound"])
        == (
            float(detail["close"]) > float(detail["previous_close"])
            and float(detail["close"])
            > REBOUND_LOW_MULTIPLIER * float(detail["low10"])
        )
        and bool(detail["confirmed"])
        == (
            PULLBACK_MINIMUM
            <= float(detail["pullback"])
            <= PULLBACK_MAXIMUM
            and bool(detail["rebound"])
            and float(detail["reward_risk"]) >= REWARD_RISK_MINIMUM
        )
        for detail in feature_details
    )
    allocation_residual = max(
        abs(
            float(receipt["stock_target_fraction"])
            + float(receipt["qqq_target_fraction"])
            - 1.0
        )
        for receipt in selection_receipts
    )
    feature_summary = {
        "parent_top7_feature_rows": len(feature_details),
        "maximum_formula_residual": maximum_feature_formula_residual,
        "boolean_identities": feature_boolean_identities,
        "all_windows_end_on_signal_date": all(
            detail["window_last_date"] == detail["signal_date"] for detail in feature_details
        ),
        "pullback": {
            "minimum": float(min(detail["pullback"] for detail in feature_details)),
            "median": float(np.median([detail["pullback"] for detail in feature_details])),
            "mean": float(np.mean([detail["pullback"] for detail in feature_details])),
            "maximum": float(max(detail["pullback"] for detail in feature_details)),
        },
        "reward_risk": {
            "minimum": float(min(detail["reward_risk"] for detail in feature_details)),
            "median": float(
                np.median([detail["reward_risk"] for detail in feature_details])
            ),
            "mean": float(np.mean([detail["reward_risk"] for detail in feature_details])),
            "maximum": float(max(detail["reward_risk"] for detail in feature_details)),
        },
    }

    candidate = metrics["lpr10_qqq_overlay"]
    qqq = metrics["qqq_buy_hold"]
    fair_ids = (
        "matched_topn_10d_overlay",
        "original_top7_10d_overlay",
        "matched_eligible_10d_overlay",
        "matched_complete_10d_overlay",
    )
    half_ids = ("qqq_buy_hold", *fair_ids)
    crisis_gate = all(
        crises[str(year)]["lpr10_qqq_overlay"]["return"]
        >= crises[str(year)]["qqq_buy_hold"]["return"]
        and crises[str(year)]["lpr10_qqq_overlay"]["max_drawdown"]
        >= crises[str(year)]["qqq_buy_hold"]["max_drawdown"] - 0.05
        for year in CRISIS_YEARS
    )
    stress_comparison_ids = (
        "qqq_buy_hold",
        "matched_topn_10d_overlay",
        "original_top7_10d_overlay",
        "matched_eligible_10d_overlay",
        "matched_complete_10d_overlay",
    )
    pre_trade_cash_sessions = int((index < pd.Timestamp(FIRST_ENTRY_DATE)).sum())
    comparison_trade_sessions = int((index >= pd.Timestamp(FIRST_ENTRY_DATE)).sum())
    protocol_calendar_internal_consistency = False
    last_invested_date = pd.Timestamp(index[-2])
    terminal_state_ok = all(
        float(path["exposure"].loc[index[-1]]) == 0.0
        and float(path["cash_value"].loc[index[-1]])
        == float(path["equity"].loc[index[-1]])
        and float(path["stock_driver_value"].loc[index[-1]]) == 0.0
        and float(path["qqq_driver_value"].loc[index[-1]]) == 0.0
        and int(path["position_count"].loc[index[-1]]) == 0
        for path in primary_paths.values()
    )
    order_count_identity_ok = all(
        receipt["actual_total_orders"] == receipt["expected_total_orders"]
        and receipt.get("maximum_event_order_count_residual", 0) == 0
        and receipt.get("event_order_counts_hash_match", True)
        and receipt["actual_terminal_liquidation_orders"]
        == receipt.get(
            "expected_terminal_liquidation_orders",
            receipt.get("terminal_liquidation_orders"),
        )
        for receipt in order_receipts.values()
    )
    n_zero_tagged_orders_ok = all(
        order_receipts[path_id]["zero_candidate_event_actual_orders"] == 0
        for path_id in (
            "lpr10_qqq_overlay",
            "matched_topn_10d_overlay",
            "matched_eligible_10d_overlay",
            "matched_complete_10d_overlay",
            "matched_qqq_switch_placebo",
        )
    )
    gate_rows = [
        (
            "exact_inputs",
            "固定輸入精確，但 protocol 的交易日起訖與 5,028 列敘述內部不一致",
            protocol_calendar_internal_consistency,
        ),
        (
            "parent_event_reconstruction",
            "第 29／30 輪 905 事件、排名及五槽逐列重播",
            parent_reconstruction["maximum_event_return_residual"]
            <= RECONSTRUCTION_TOLERANCE
            and parent_reconstruction["assignment_sha256"] == PARENT_ASSIGNMENT_SHA256,
        ),
        (
            "ten_day_slot_clock",
            "五槽各 181 事件、十日持有、無同槽重疊且 concurrency 不高於五",
            ten_day_reconstruction["slot_event_counts"] == [EVENTS_PER_SLOT] * SLOT_COUNT
            and ten_day_reconstruction["maximum_concurrent_intervals"] <= SLOT_COUNT
            and all(
                int(index.get_loc(event["exit_date"]))
                - int(index.get_loc(event["entry_date"]))
                == HOLDING_SESSIONS - 1
                for event in events
            ),
        ),
        (
            "ohlc_structure_no_lookahead",
            "OHLC 結構公式逐列精確且只用訊號日或以前",
            maximum_feature_formula_residual <= RECONSTRUCTION_TOLERANCE
            and feature_summary["all_windows_end_on_signal_date"]
            and feature_boolean_identities,
        ),
        (
            "selection_and_allocation",
            "N、Top-7 子集、N/7、QQQ 餘額及非空事件下限",
            min(counts) >= 0
            and max(counts) <= STOCK_SUBSLOTS
            and all(set(row["confirmed"]).issubset(row["parent_top7"]) for row in selection_receipts)
            and allocation_residual <= RECONSTRUCTION_TOLERANCE
            and len(nonempty) >= 181
            and nonempty_first_half >= 75
            and nonempty_second_half >= 75,
        ),
        (
            "daily_capital_identities",
            "九路每日 driver、資產、成本、曝險、現金及槓桿 identity",
            max(
                max(
                    path["maximum_daily_identity_residual"],
                    path["maximum_driver_identity_residual"],
                    path["maximum_cost_identity_residual"],
                )
                for path in primary_paths.values()
            )
            <= RECONSTRUCTION_TOLERANCE
            and all(row["maximum_exposure"] <= 1.0 + RECONSTRUCTION_TOLERANCE for row in metrics.values())
            and all(row["minimum_cash_value"] >= -RECONSTRUCTION_TOLERANCE for row in metrics.values())
            and all(
                path["exposure"].loc[FIRST_ENTRY_DATE:last_invested_date].eq(1.0).all()
                and float(
                    path["cash_value"].loc[FIRST_ENTRY_DATE:last_invested_date].abs().max()
                )
                <= RECONSTRUCTION_TOLERANCE
                and float(
                    (
                        path["stock_driver_fraction"]
                        + path["qqq_driver_fraction"]
                        - path["exposure"]
                    )
                    .loc[FIRST_ENTRY_DATE:last_invested_date]
                    .abs()
                    .max()
                )
                <= RECONSTRUCTION_TOLERANCE
                for path in primary_paths.values()
            )
            and terminal_state_ok
            and order_count_identity_ok
            and n_zero_tagged_orders_ok,
        ),
        (
            "parent_and_placebo_identities",
            "QQQ switch placebo 與十日父事件 identity 精確",
            placebo_maximum_residual <= RECONSTRUCTION_TOLERANCE
            and ten_day_reconstruction["maximum_ten_day_event_return_residual"]
            <= RECONSTRUCTION_TOLERANCE,
        ),
        ("candidate_cagr_vs_qqq", "候選 CAGR 高於 QQQ", candidate["cagr"] > qqq["cagr"]),
        (
            "candidate_terminal_vs_qqq",
            "候選 US$1,000 期末值高於 QQQ",
            candidate["terminal_usd"] > qqq["terminal_usd"],
        ),
        (
            "candidate_sharpe_vs_qqq",
            "候選 SHY-excess Sharpe 高於 QQQ",
            candidate["shy_excess_sharpe"] > qqq["shy_excess_sharpe"],
        ),
        (
            "candidate_drawdown_vs_qqq",
            "候選最大跌幅不比 QQQ 深超過 5pp",
            candidate["max_drawdown"] >= qqq["max_drawdown"] - 0.05,
        ),
        (
            "candidate_cagr_vs_matched_topn",
            "候選 CAGR 高於 matched Top-N",
            candidate["cagr"] > metrics["matched_topn_10d_overlay"]["cagr"],
        ),
        (
            "candidate_cagr_vs_original_top7",
            "候選 CAGR 高於原 Top-7 十日",
            candidate["cagr"] > metrics["original_top7_10d_overlay"]["cagr"],
        ),
        (
            "candidate_cagr_vs_equal_baselines",
            "候選 CAGR 高於 matched eligible 及 complete",
            candidate["cagr"] > metrics["matched_eligible_10d_overlay"]["cagr"]
            and candidate["cagr"] > metrics["matched_complete_10d_overlay"]["cagr"],
        ),
        (
            "statistical_vs_qqq",
            "候選對 QQQ 日差、NW、Holm 及共同 max-t",
            comparison_by_id["qqq_buy_hold"]["mean_daily_difference"] > 0.0
            and comparison_by_id["qqq_buy_hold"]["newey_west"]["t_stat"] >= 1.96
            and comparison_by_id["qqq_buy_hold"]["holm_adjusted_p"] <= FAMILY_ALPHA
            and comparison_by_id["qqq_buy_hold"]["bootstrap_max_t_p"] <= FAMILY_ALPHA,
        ),
        (
            "statistical_vs_matched_family",
            "候選對四條公平股票基準日差、NW、Holm 及 max-t",
            all(
                comparison_by_id[path_id]["mean_daily_difference"] > 0.0
                and comparison_by_id[path_id]["newey_west"]["t_stat"] >= 1.96
                and comparison_by_id[path_id]["holm_adjusted_p"] <= FAMILY_ALPHA
                and comparison_by_id[path_id]["bootstrap_max_t_p"] <= FAMILY_ALPHA
                for path_id in fair_ids
            ),
        ),
        (
            "fixed_halves",
            "QQQ 與四條公平股票基準前後半日差全正",
            all(
                comparison_by_id[path_id]["fixed_halves"][half][
                    "mean_daily_difference"
                ]
                > 0.0
                for path_id in half_ids
                for half in ("first", "second")
            ),
        ),
        (
            "best_three_years_removed",
            "移除相對 QQQ 最佳三年後日差及 NW",
            best_year_stress["mean_daily_difference"] > 0.0
            and best_year_stress["newey_west"]["t_stat"] >= 1.96,
        ),
        (
            "crisis_periods",
            "2008／2020／2022 回報及跌幅不遜於 QQQ",
            crisis_gate,
        ),
        (
            "known_at_qqq_regimes",
            "QQQ 20 日動量正負兩組事件增量均正",
            all(row["average_event_increment"] > 0.0 for row in regime_rows.values()),
        ),
        (
            "global_multiplicity",
            "候選對 QQQ 的 6,237 次 Bonferroni p 不高於 0.05",
            comparison_by_id["qqq_buy_hold"]["global_bonferroni_p"] <= FAMILY_ALPHA,
        ),
        (
            "cost_fixed_fee_and_tail",
            "25／50bps、US$0.01 子委託費及移除 46 宗後仍勝五基準",
            all(
                all(
                    row["candidate_cagr_differences"][path_id] > 0.0
                    for path_id in stress_comparison_ids
                )
                for row in cost_stresses.values()
            )
            and all(
                fixed_fee_stresses["0.01"]["candidate_cagr_differences"][path_id]
                > 0.0
                for path_id in stress_comparison_ids
            )
            and all(
                tail_stress["candidate_cagr_differences"][path_id] > 0.0
                for path_id in stress_comparison_ids
            ),
        ),
    ]
    gates = [
        {"id": gate_id, "label": label, "passed": bool(passed)}
        for gate_id, label, passed in gate_rows
    ]
    gate_summary = {
        "passed": sum(int(row["passed"]) for row in gates),
        "total": len(gates),
        "all_passed": all(row["passed"] for row in gates),
    }

    controls_source = [
        ("protocol_hash", input_receipts["hashes"]["protocol"] == PROTOCOL_SHA256),
        ("protocol_commit", FROZEN_CONTRACT.protocol_commit == PROTOCOL_COMMIT),
        ("parent_main_commit", FROZEN_CONTRACT.parent_main_commit == PARENT_MAIN_COMMIT),
        ("round38_receipt", input_receipts["hashes"]["round38"] == ROUND38_RECEIPT_SHA256),
        ("round30_receipt", input_receipts["hashes"]["round30"] == ROUND30_RECEIPT_SHA256),
        ("round29_receipt", input_receipts["hashes"]["round29"] == ROUND29_RECEIPT_SHA256),
        ("event_receipt", input_receipts["hashes"]["event_receipt"] == EVENT_RECEIPT_SHA256),
        ("snapshot", input_receipts["hashes"]["snapshot"] == SNAPSHOT_SHA256),
        ("panel", input_receipts["hashes"]["panel"] == PANEL_SHA256),
        ("watchlist", input_receipts["hashes"]["watchlist"] == WATCHLIST_SHA256),
        ("reference_commits", FROZEN_CONTRACT.reference_commits == REFERENCE_COMMITS),
        ("protocol_calendar_internal_consistency", protocol_calendar_internal_consistency),
        ("events_905", len(events) == EXPECTED_EVENTS),
        ("initial_capital_1000", FROZEN_CONTRACT.initial_capital_usd == 1_000.0),
        ("cohort_25", len(cohort) == EXPECTED_COHORT),
        ("signal_boundaries", events[0]["signal_date"].strftime("%Y-%m-%d") == FIRST_SIGNAL_DATE and events[-1]["signal_date"].strftime("%Y-%m-%d") == LAST_SIGNAL_DATE),
        ("eligible_replay", all(len(event["eligible"]) >= PARENT_TOP_K for event in events)),
        ("top7_replay", all(len(event["selected"]) == PARENT_TOP_K for event in events)),
        ("parent_rank_order", all(event["selected"] == event["ranked"][:PARENT_TOP_K] for event in events)),
        ("parent_assignment", parent_reconstruction["assignment_sha256"] == PARENT_ASSIGNMENT_SHA256),
        ("adjusted_ohlc_finite", all(np.isfinite([detail["close"], detail["atr14"], detail["high20"], detail["high60"], detail["low10"]]).all() for detail in feature_details)),
        ("tr14", all(len(detail["true_ranges"]) == ATR_SESSIONS for detail in feature_details)),
        ("atr14_formula", maximum_feature_formula_residual <= RECONSTRUCTION_TOLERANCE),
        ("feature_boolean_identities", feature_boolean_identities),
        ("high20_close", FROZEN_CONTRACT.high20_sessions == 20),
        ("high60_close", FROZEN_CONTRACT.high60_sessions == 60),
        ("low10_low", FROZEN_CONTRACT.low10_sessions == 10),
        ("pullback_bounds", FROZEN_CONTRACT.pullback_minimum == 0.03 and FROZEN_CONTRACT.pullback_maximum == 0.16),
        ("rebound_rule", FROZEN_CONTRACT.rebound_low_multiplier == 1.01),
        ("target_rule", FROZEN_CONTRACT.target_atr_multiplier == 1.5),
        ("stop_rule", FROZEN_CONTRACT.stop_atr_multiplier == 0.5),
        ("reward_risk_floor", FROZEN_CONTRACT.reward_risk_minimum == 1.6),
        ("reward_risk_clip", FROZEN_CONTRACT.reward_risk_clip_maximum == 8.0),
        ("no_lookahead", feature_summary["all_windows_end_on_signal_date"]),
        ("top7_subset", all(set(row["confirmed"]).issubset(row["parent_top7"]) for row in selection_receipts)),
        ("candidate_n_range", min(counts) >= 0 and max(counts) <= STOCK_SUBSLOTS),
        ("n_over_7", all(abs(row["stock_target_fraction"] - row["candidate_count"] / STOCK_SUBSLOTS) <= RECONSTRUCTION_TOLERANCE for row in selection_receipts)),
        ("qqq_remainder", allocation_residual <= RECONSTRUCTION_TOLERANCE),
        ("no_reconcentration", all(row["candidate_count"] == 0 or row["stock_target_fraction"] < 1.0 or row["candidate_count"] == STOCK_SUBSLOTS for row in selection_receipts)),
        ("d_plus_1", all(index.get_loc(event["entry_date"]) - index.get_loc(event["signal_date"]) == 1 for event in events)),
        ("ten_session_hold", all(index.get_loc(event["exit_date"]) - index.get_loc(event["entry_date"]) == 9 for event in events)),
        ("five_slots", ten_day_reconstruction["slot_event_counts"] == [181] * 5),
        ("concurrency_cap", ten_day_reconstruction["maximum_concurrent_intervals"] <= 5),
        ("qqq_base", FROZEN_CONTRACT.inactive_asset == "QQQ"),
        ("four_leg_cost", FROZEN_CONTRACT.four_legs_per_switched_subslot),
        ("primary_10bps", FROZEN_CONTRACT.primary_one_way_leg_bps == 10),
        ("stress_25_50bps", set(cost_stresses) == {"25", "50"}),
        ("fixed_fee_stresses", set(fixed_fee_stresses) == {"0.01", "0.05"}),
        ("fixed_fee_actual_orders", max(row["maximum_fixed_fee_identity_residual_usd"] for row in fixed_fee_stresses.values()) <= RECONSTRUCTION_TOLERANCE),
        ("independent_order_counts", order_count_identity_ok),
        ("n_zero_no_tagged_orders", n_zero_tagged_orders_ok),
        ("nine_paths", tuple(primary_paths) == PATH_IDS),
        ("placebo_identity", placebo_maximum_residual <= RECONSTRUCTION_TOLERANCE),
        ("ten_day_parent_identity", ten_day_reconstruction["maximum_ten_day_event_return_residual"] <= RECONSTRUCTION_TOLERANCE),
        ("shy_excess", FROZEN_CONTRACT.shy_excess_proxy and bool(shy_proxy.notna().all())),
        ("full_long_before_terminal_all_paths", all(path["exposure"].loc[FIRST_ENTRY_DATE:last_invested_date].eq(1.0).all() for path in primary_paths.values())),
        ("zero_cash_before_terminal_all_paths", all(float(path["cash_value"].loc[FIRST_ENTRY_DATE:last_invested_date].abs().max()) <= RECONSTRUCTION_TOLERANCE for path in primary_paths.values())),
        ("driver_fraction_identity_all_paths", all(float((path["stock_driver_fraction"] + path["qqq_driver_fraction"] - path["exposure"]).loc[FIRST_ENTRY_DATE:last_invested_date].abs().max()) <= RECONSTRUCTION_TOLERANCE for path in primary_paths.values())),
        ("terminal_liquidation_all_paths", terminal_state_ok),
        ("no_leverage", all(row["maximum_exposure"] <= 1.0 + RECONSTRUCTION_TOLERANCE for row in metrics.values())),
        ("daily_driver_identity", max(path["maximum_driver_identity_residual"] for path in primary_paths.values()) <= RECONSTRUCTION_TOLERANCE),
        ("actual_notional_cost_identity", max(path["maximum_cost_identity_residual"] for path in primary_paths.values()) <= RECONSTRUCTION_TOLERANCE),
        ("eight_hypotheses", tuple(row["baseline_id"] for row in comparisons) == FAMILY_BASELINE_IDS),
        ("nw_lag10", all(row["newey_west"]["lag"] == HAC_LAG for row in comparisons)),
        ("bootstrap_63_20000", bootstrap["block_sessions"] == 63 and bootstrap["paths"] == 20_000 and bootstrap["seed"] == BOOTSTRAP_SEED and bootstrap["common_indices"]),
        ("fixed_halves", FROZEN_CONTRACT.first_half_end == "2016-07-29" and FROZEN_CONTRACT.second_half_start == "2016-08-01"),
        ("crisis_years", set(crises) == {"2008", "2020", "2022"}),
        ("qqq_known_at_regimes", set(regime_rows) == {"nonnegative", "negative"} and sum(row["events"] for row in regime_rows.values()) == EXPECTED_EVENTS),
        ("best_three_years", len(removed_years) == BEST_YEAR_REMOVAL_COUNT),
        ("favorable_46", len(tail_exclusions) == FAVORABLE_EVENT_REMOVAL_COUNT),
        ("global_6237", FROZEN_CONTRACT.global_search_trials == GLOBAL_SEARCH_TRIALS),
        ("current_identifiers", FROZEN_CONTRACT.current_identifiers_only),
        ("formal_readiness", FROZEN_CONTRACT.formal_readiness == "1/18" and FROZEN_CONTRACT.formal_strategy_runs == 0),
        ("point_in_time_readiness", FROZEN_CONTRACT.point_in_time_readiness == "1/20" and FROZEN_CONTRACT.qualified_provider_packages == 0),
        ("paper_zero", not FROZEN_CONTRACT.paper_authorized),
        ("real_money_zero", not FROZEN_CONTRACT.real_money_authorized),
    ]
    controls = [
        {"id": f"{position:02d}", "label": label, "passed": bool(passed)}
        for position, (label, passed) in enumerate(controls_source, 1)
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
    result = {
        "schema_version": SCHEMA_VERSION,
        "research_round": RESEARCH_ROUND,
        "research_role": "same_seen_survivor_leader_pullback_rebound_falsification_not_formal_backtest",
        "generated_on": "2026-08-09",
        "protocol": {
            "path": PROTOCOL_PATH,
            "sha256": PROTOCOL_SHA256,
            "commit": PROTOCOL_COMMIT,
            "calculated_after_protocol_commit": True,
            "independent_first_unseen_evidence": False,
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
            "calendar_last_date": CALENDAR_LAST_DATE,
            "comparison_trade_start_date": FIRST_ENTRY_DATE,
            "pre_trade_cash_sessions": pre_trade_cash_sessions,
            "comparison_trade_sessions": comparison_trade_sessions,
            "protocol_calendar_internal_consistency": protocol_calendar_internal_consistency,
            "current_cohort": cohort,
            "current_cohort_count": len(cohort),
            "identifier_scope": "2026_current_symbols_not_permanent_ids",
            "survivorship_bias_warning": True,
            "initial_capital_usd": INITIAL_CAPITAL_USD,
        },
        "input_receipts": input_receipts,
        "method": {
            "candidate_id": "lpr10_qqq_overlay",
            "parent_momentum_sessions": PARENT_MOMENTUM_SESSIONS,
            "atr_sessions": ATR_SESSIONS,
            "high20_close_sessions": HIGH20_SESSIONS,
            "high60_close_sessions": HIGH60_SESSIONS,
            "low10_low_sessions": LOW10_SESSIONS,
            "pullback_bounds": [PULLBACK_MINIMUM, PULLBACK_MAXIMUM],
            "rebound_low_multiplier": REBOUND_LOW_MULTIPLIER,
            "target_atr_multiplier": TARGET_ATR_MULTIPLIER,
            "stop_atr_multiplier": STOP_ATR_MULTIPLIER,
            "reward_risk_minimum": REWARD_RISK_MINIMUM,
            "reward_risk_clip_maximum": REWARD_RISK_CLIP_MAXIMUM,
            "stock_subslots": STOCK_SUBSLOTS,
            "stock_target_rule": "N/7",
            "qqq_remainder_rule": "1-N/7",
            "entry_delay_sessions": ENTRY_DELAY,
            "holding_sessions": HOLDING_SESSIONS,
            "slot_count": SLOT_COUNT,
            "events_per_slot": EVENTS_PER_SLOT,
            "inactive_asset": "QQQ",
            "primary_one_way_leg_cost_bps": PRIMARY_ONE_WAY_LEG_BPS,
            "cost_stress_one_way_leg_bps": list(COST_STRESS_ONE_WAY_LEG_BPS),
            "fixed_child_order_fee_stress_usd": list(FIXED_CHILD_ORDER_FEE_STRESS_USD),
            "path_ids": list(PATH_IDS),
            "fractional_shares_research_only": True,
            "leverage_allowed": False,
        },
        "reconstruction": {
            "parent": parent_reconstruction,
            "ten_day": ten_day_reconstruction,
            "feature": feature_summary,
            "placebo_residuals": placebo_residuals,
            "maximum_placebo_residual": placebo_maximum_residual,
            "placebo_identity_method": "independent_qqq_only_price_and_actual_order_cost_recurrence",
        },
        "selection_distribution": {
            "minimum_candidates": min(counts),
            "maximum_candidates": max(counts),
            "mean_candidates": float(np.mean([event["candidate_count"] for event in events])),
            "nonempty_events": len(nonempty),
            "nonempty_first_half_events": nonempty_first_half,
            "nonempty_second_half_events": nonempty_second_half,
            "mean_stock_target_fraction": float(
                np.mean([event["stock_target_fraction"] for event in events])
            ),
            "maximum_allocation_residual": allocation_residual,
            "feature_distribution": feature_summary,
            "candidate_count_histogram": [
                {"candidate_count": value, "events": counts.get(value, 0)}
                for value in range(STOCK_SUBSLOTS + 1)
            ],
        },
        "selection_receipts": selection_receipts,
        "calendar_integrity": {
            "sessions": len(index),
            "first_date": index[0].strftime("%Y-%m-%d"),
            "first_trade_date": FIRST_ENTRY_DATE,
            "last_date": index[-1].strftime("%Y-%m-%d"),
            "pre_trade_cash_sessions": pre_trade_cash_sessions,
            "comparison_trade_sessions": comparison_trade_sessions,
            "protocol_calendar_internal_consistency": protocol_calendar_internal_consistency,
            "maximum_concurrent_ten_day_intervals": ten_day_reconstruction[
                "maximum_concurrent_intervals"
            ],
            "terminal_liquidation_date": index[-1].strftime("%Y-%m-%d"),
            "terminal_exposure": {
                path_id: float(primary_paths[path_id]["exposure"].iloc[-1])
                for path_id in PATH_IDS
            },
            "terminal_position_count": {
                path_id: int(primary_paths[path_id]["position_count"].iloc[-1])
                for path_id in PATH_IDS
            },
            "terminal_state_all_cash": terminal_state_ok,
            "order_diagnostics": {
                "primary": {
                    path_id: {
                        **order_receipts[path_id],
                        "order_kind_counts": metrics[path_id]["order_kind_counts"],
                        "order_ticker_counts": metrics[path_id]["order_ticker_counts"],
                    }
                    for path_id in PATH_IDS
                },
                "candidate_ledgers": {
                    "primary_10bps_per_leg": primary_paths["lpr10_qqq_overlay"][
                        "order_ledger"
                    ],
                    "fixed_fee_0.01_usd": fixed_path_sets["0.01"][
                        "lpr10_qqq_overlay"
                    ]["order_ledger"],
                    "fixed_fee_0.05_usd": fixed_path_sets["0.05"][
                        "lpr10_qqq_overlay"
                    ]["order_ledger"],
                },
            },
            "maximum_daily_identity_residual": max(
                path["maximum_daily_identity_residual"] for path in primary_paths.values()
            ),
            "maximum_driver_identity_residual": max(
                path["maximum_driver_identity_residual"] for path in primary_paths.values()
            ),
            "maximum_cost_identity_residual": max(
                path["maximum_cost_identity_residual"] for path in primary_paths.values()
            ),
        },
        "paths": metrics,
        "family": {
            "size": 8,
            "candidate_id": "lpr10_qqq_overlay",
            "comparisons": comparisons,
            "common_bootstrap": bootstrap,
            "global_search_trials": GLOBAL_SEARCH_TRIALS,
        },
        "stresses": {
            "best_three_years_removed": best_year_stress,
            "crisis_years": crises,
            "known_at_qqq_regimes": regime_rows,
            "costs": cost_stresses,
            "fixed_child_order_fees": fixed_fee_stresses,
            "favorable_46_events_removed": tail_stress,
        },
        "gates": gates,
        "gate_summary": gate_summary,
        "controls": controls,
        "control_summary": control_summary,
        "attacks": attacks,
        "attack_summary": attack_summary,
        "calendar_rows": [
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
                "candidate_stock_driver_fraction": float(
                    primary_paths["lpr10_qqq_overlay"]["stock_driver_fraction"].loc[date]
                ),
                "candidate_qqq_driver_fraction": float(
                    primary_paths["lpr10_qqq_overlay"]["qqq_driver_fraction"].loc[date]
                ),
                "candidate_cost_paid_usd": float(
                    primary_paths["lpr10_qqq_overlay"]["cost_paid"].loc[date]
                    * INITIAL_CAPITAL_USD
                ),
                "candidate_position_count": int(
                    primary_paths["lpr10_qqq_overlay"]["position_count"].loc[date]
                ),
            }
            for date in index
        ],
        "decision": {
            "can_promote_from_this_round": False,
            "not_rejected_by_round39": gate_summary["all_passed"],
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
    return result
