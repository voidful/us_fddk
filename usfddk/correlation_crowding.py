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
from .metrics import newey_west_mean_test
from .short_term_high_return import (
    SHORT_TERM_END,
    SHORT_TERM_START,
    _completed_period_mask,
)
from .universe import load_stock_watchlist

SCHEMA_VERSION = 1
RESEARCH_ROUND = 25
PROTOCOL_PATH = "docs/SHORT_TERM_CORRELATION_CROWDING_PROTOCOL.md"
PROTOCOL_SHA256 = "f4510c4a3166a8c7f742224a17785e505f2c9214a13977ea426b6c4fecb54db7"
PROTOCOL_COMMIT = "00faaa5ed04bccb8b0d147fb47a9ef3c706f3d44"
REPAIR_PROTOCOL_PATH = "docs/SHORT_TERM_CORRELATION_CROWDING_SCHEMA_REPAIR_PROTOCOL.md"
REPAIR_PROTOCOL_SHA256 = "8f7c3428cb3fb9b7c4ba95bf579f82b712e7a5865474a8b7991c013d6f949590"
REPAIR_PROTOCOL_COMMIT = "c48de060cbc501f04e73fa9977d040eff8fc097d"

SNAPSHOT_PATH = "artifacts/snapshot_20260731_6a7ca6b8.zip"
SNAPSHOT_SHA256 = "d480fb82e712f06aabe0a98461e222344656b87022b8bda2cd7ccaa4c29ae88b"
PANEL_SHA256 = "6a7ca6b83b1570007424daa46b0ff4e8fb4a655d39298a0f4f6d74c3b7ea3a66"
WATCHLIST_PATH = "usfddk/resources/us_large_cap_watchlist_v1.csv"
WATCHLIST_SHA256 = "b6002e4e151bd298884f8cdd6272b5cbfde8aedca47cb58b92830d4d92028014"
EVENT_RECEIPT_PATH = "artifacts/short_term_high_return_validation.json"
EVENT_RECEIPT_SHA256 = "fa2463cc8273a316e4a98428767b695eb85c74e9ac75c47b5ca34592102979e8"

REFERENCE_COMMITS = (
    ("tst_wocker", "3372aa088328700feafeeb07c72ab832ea2d3ecb"),
    ("tw-block-warrant", "37463c54796ba36f4aac262519ea7fc2ef797de6"),
    ("tst_wocker_filter_lab", "06c87b7a1735877c9ccbab3a339c1742814a5058"),
)

EXPECTED_COHORT = 25
EXPECTED_EVENTS = 905
FIRST_SIGNAL_DATE = "2006-08-04"
LAST_SIGNAL_DATE = "2026-07-02"
MOMENTUM_SESSIONS = 20
TREND_SESSIONS = 60
TOP_K = 7
ENTRY_DELAY = 1
HOLDING_SESSIONS = 20
ROUND_TRIP_COST_BPS = 20
CORRELATION_RETURN_WINDOW = 60
CORRELATION_THRESHOLD = 0.70
CORRELATION_CAP = 2
FAMILY_SIZE = 4
FAMILY_ALPHA = 0.05
HAC_LAG = 4
BOOTSTRAP_BLOCK_LENGTH = 52
BOOTSTRAP_PATHS = 20_000
BOOTSTRAP_SEED = 25_202_608
FIRST_HALF_END = pd.Timestamp("2016-07-29")
SECOND_HALF_START = pd.Timestamp("2016-08-01")
RECONSTRUCTION_TOLERANCE = 1e-12

EFFECTIVE_BETS_FORMULA = "clip(n/(1+(n-1)*mean_pairwise_corr),1,n)"


class CorrelationCrowdingError(ValueError):
    """Fail-closed Round 25 error with a stable semantic code."""

    def __init__(self, code: str, detail: str):
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}")


def _fail(code: str, detail: str) -> None:
    raise CorrelationCrowdingError(code, detail)


@dataclass(frozen=True)
class FrozenCrowdingContract:
    protocol_sha256: str = PROTOCOL_SHA256
    repair_protocol_sha256: str = REPAIR_PROTOCOL_SHA256
    snapshot_sha256: str = SNAPSHOT_SHA256
    panel_sha256: str = PANEL_SHA256
    watchlist_sha256: str = WATCHLIST_SHA256
    event_receipt_sha256: str = EVENT_RECEIPT_SHA256
    reference_commits: tuple[tuple[str, str], ...] = REFERENCE_COMMITS
    expected_cohort: int = EXPECTED_COHORT
    expected_events: int = EXPECTED_EVENTS
    first_signal_date: str = FIRST_SIGNAL_DATE
    last_signal_date: str = LAST_SIGNAL_DATE
    momentum_sessions: int = MOMENTUM_SESSIONS
    trend_sessions: int = TREND_SESSIONS
    top_k: int = TOP_K
    entry_delay: int = ENTRY_DELAY
    holding_sessions: int = HOLDING_SESSIONS
    round_trip_cost_bps: int = ROUND_TRIP_COST_BPS
    correlation_return_window: int = CORRELATION_RETURN_WINDOW
    correlation_threshold: float = CORRELATION_THRESHOLD
    correlation_cap: int = CORRELATION_CAP
    no_backfill: bool = True
    effective_bets_formula: str = EFFECTIVE_BETS_FORMULA
    current_identifiers_only: bool = True
    permanent_identifier_claimed: bool = False
    contribution_identity_required: bool = True
    fair_exclusion_baseline: bool = True
    matched_cash_on_insufficient_breadth: bool = True
    family_size: int = FAMILY_SIZE
    bootstrap_block_length: int = BOOTSTRAP_BLOCK_LENGTH
    bootstrap_paths: int = BOOTSTRAP_PATHS
    bootstrap_seed: int = BOOTSTRAP_SEED
    common_bootstrap_indices: bool = True
    centered_under_null: bool = True
    paper_authorized: bool = False
    real_money_authorized: bool = False


FROZEN_CONTRACT = FrozenCrowdingContract()


def validate_crowding_contract(contract: FrozenCrowdingContract) -> None:
    checks: tuple[tuple[bool, str, str], ...] = (
        (
            contract.protocol_sha256 == PROTOCOL_SHA256,
            "crowding_protocol_mismatch",
            "第 25 輪協議 SHA 漂移",
        ),
        (
            contract.snapshot_sha256 == SNAPSHOT_SHA256,
            "crowding_snapshot_hash_mismatch",
            "行情 archive SHA 漂移",
        ),
        (
            contract.panel_sha256 == PANEL_SHA256,
            "crowding_panel_fingerprint_mismatch",
            "行情 panel fingerprint 漂移",
        ),
        (
            contract.watchlist_sha256 == WATCHLIST_SHA256,
            "crowding_watchlist_hash_mismatch",
            "現時觀察名單 SHA 漂移",
        ),
        (
            contract.event_receipt_sha256 == EVENT_RECEIPT_SHA256,
            "crowding_event_receipt_hash_mismatch",
            "既有事件收據 SHA 漂移",
        ),
        (
            contract.reference_commits == REFERENCE_COMMITS,
            "crowding_reference_commits_mismatch",
            "台股參考 commit 漂移",
        ),
        (
            contract.expected_cohort == EXPECTED_COHORT,
            "crowding_cohort_mismatch",
            "完整現時 cohort 數目漂移",
        ),
        (
            contract.expected_events == EXPECTED_EVENTS
            and contract.first_signal_date == FIRST_SIGNAL_DATE
            and contract.last_signal_date == LAST_SIGNAL_DATE,
            "crowding_event_order_mismatch",
            "固定事件數或日期邊界漂移",
        ),
        (
            contract.momentum_sessions == MOMENTUM_SESSIONS
            and contract.trend_sessions == TREND_SESSIONS
            and contract.top_k == TOP_K,
            "crowding_signal_rule_mismatch",
            "20／60／Top-7 訊號漂移",
        ),
        (
            contract.entry_delay == ENTRY_DELAY
            and contract.holding_sessions == HOLDING_SESSIONS
            and contract.round_trip_cost_bps == ROUND_TRIP_COST_BPS,
            "crowding_execution_rule_mismatch",
            "D+1／20 日／20 bps 執行漂移",
        ),
        (
            contract.correlation_return_window == CORRELATION_RETURN_WINDOW,
            "crowding_correlation_window_mismatch",
            "相關回報窗漂移",
        ),
        (
            contract.correlation_threshold == CORRELATION_THRESHOLD
            and contract.correlation_cap == CORRELATION_CAP
            and contract.no_backfill,
            "crowding_cap_rule_mismatch",
            "0.70／cap 2／不回補規則漂移",
        ),
        (
            contract.effective_bets_formula == EFFECTIVE_BETS_FORMULA,
            "crowding_effective_bets_formula_mismatch",
            "有效獨立注數公式漂移",
        ),
        (
            contract.current_identifiers_only and not contract.permanent_identifier_claimed,
            "crowding_identifier_claim_breached",
            "現時 ticker 被冒充永久證券 ID",
        ),
        (
            contract.contribution_identity_required,
            "crowding_contribution_identity_failed",
            "逐股淨貢獻恆等式被取消",
        ),
        (
            contract.fair_exclusion_baseline,
            "crowding_baseline_fairness_breached",
            "刪除壓力沒有同步修改 baseline",
        ),
        (
            contract.family_size == FAMILY_SIZE
            and contract.bootstrap_block_length == BOOTSTRAP_BLOCK_LENGTH
            and contract.bootstrap_paths == BOOTSTRAP_PATHS
            and contract.bootstrap_seed == BOOTSTRAP_SEED
            and contract.common_bootstrap_indices
            and contract.centered_under_null,
            "crowding_bootstrap_contract_mismatch",
            "四假說共同 bootstrap 漂移",
        ),
        (
            not contract.paper_authorized and not contract.real_money_authorized,
            "crowding_decision_boundary_breached",
            "本輪不得授權 Paper 或實金",
        ),
        (
            contract.repair_protocol_sha256 == REPAIR_PROTOCOL_SHA256
            and contract.matched_cash_on_insufficient_breadth,
            "crowding_repair_protocol_mismatch",
            "matched-cash repair SHA 或會計規則漂移",
        ),
    )
    for passed, code, detail in checks:
        if not passed:
            _fail(code, detail)


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _normal_two_sided_p(t_stat: float) -> float:
    return float(math.erfc(abs(t_stat) / math.sqrt(2.0)))


def _newey_west(values: np.ndarray) -> dict[str, float | int]:
    result = newey_west_mean_test(pd.Series(values), max_lag=HAC_LAG, periods_per_year=52)
    mean = float(result["mean_daily"])
    t_stat = float(result["t_stat"])
    standard_error = abs(mean / t_stat) if t_stat != 0.0 else 0.0
    return {
        "mean_difference": mean,
        "annualized_event_difference": float(result["annualized"]),
        "standard_error": float(standard_error),
        "t_stat": t_stat,
        "lag": int(result["lag"]),
    }


def _fixed_halves(values: np.ndarray, dates: pd.Series) -> dict[str, Any]:
    first = (dates <= FIRST_HALF_END).to_numpy(dtype=bool)
    second = (dates >= SECOND_HALF_START).to_numpy(dtype=bool)
    return {
        "first": {
            "events": int(first.sum()),
            "mean_difference": float(values[first].mean()),
            "median_difference": float(np.median(values[first])),
        },
        "second": {
            "events": int(second.sum()),
            "mean_difference": float(values[second].mean()),
            "median_difference": float(np.median(values[second])),
        },
    }


def _comparison(values: np.ndarray, dates: pd.Series) -> dict[str, Any]:
    nw = _newey_west(values)
    return {
        "events": len(values),
        "mean_difference": float(values.mean()),
        "median_difference": float(np.median(values)),
        "positive_fraction": float((values > 0.0).mean()),
        "newey_west": nw,
        "raw_normal_p": _normal_two_sided_p(float(nw["t_stat"])),
        "fixed_halves": _fixed_halves(values, dates),
    }


def _effective_bets(mean_pairwise_correlation: float, count: int) -> float:
    if count <= 1:
        return float(count)
    denominator = 1.0 + (count - 1) * mean_pairwise_correlation
    if not math.isfinite(denominator) or denominator <= 0.0:
        _fail(
            "crowding_effective_bets_formula_mismatch",
            "有效獨立注數分母非正或非有限",
        )
    return float(np.clip(count / denominator, 1.0, float(count)))


def _pairwise_summary(correlation: pd.DataFrame, symbols: list[str]) -> dict[str, Any]:
    if len(symbols) <= 1:
        return {
            "pair_count": 0,
            "mean_pairwise_correlation": 0.0,
            "median_pairwise_correlation": 0.0,
            "maximum_pairwise_correlation": 0.0,
            "high_correlation_pair_count": 0,
            "effective_bets": float(len(symbols)),
        }
    values = correlation.loc[symbols, symbols].to_numpy(dtype=float)
    upper = values[np.triu_indices(len(symbols), k=1)]
    if len(upper) != len(symbols) * (len(symbols) - 1) // 2 or not np.isfinite(upper).all():
        _fail("crowding_correlation_window_mismatch", "pairwise 相關矩陣不完整")
    mean_correlation = float(upper.mean())
    return {
        "pair_count": len(upper),
        "mean_pairwise_correlation": mean_correlation,
        "median_pairwise_correlation": float(np.median(upper)),
        "maximum_pairwise_correlation": float(upper.max()),
        "high_correlation_pair_count": int((upper > CORRELATION_THRESHOLD).sum()),
        "effective_bets": _effective_bets(mean_correlation, len(symbols)),
    }


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
    root: Path, contract: FrozenCrowdingContract
) -> tuple[Any, list[str], list[dict[str, Any]], dict[str, str]]:
    paths = {
        "protocol": root / PROTOCOL_PATH,
        "repair_protocol": root / REPAIR_PROTOCOL_PATH,
        "snapshot": root / SNAPSHOT_PATH,
        "watchlist": root / WATCHLIST_PATH,
        "event_receipt": root / EVENT_RECEIPT_PATH,
    }
    observed_hashes = {key: _sha256_file(path) for key, path in paths.items()}
    expected = {
        "protocol": contract.protocol_sha256,
        "repair_protocol": contract.repair_protocol_sha256,
        "snapshot": contract.snapshot_sha256,
        "watchlist": contract.watchlist_sha256,
        "event_receipt": contract.event_receipt_sha256,
    }
    error_codes = {
        "protocol": "crowding_protocol_mismatch",
        "repair_protocol": "crowding_repair_protocol_mismatch",
        "snapshot": "crowding_snapshot_hash_mismatch",
        "watchlist": "crowding_watchlist_hash_mismatch",
        "event_receipt": "crowding_event_receipt_hash_mismatch",
    }
    for key, expected_hash in expected.items():
        if observed_hashes[key] != expected_hash:
            _fail(error_codes[key], f"{key} SHA-256 漂移")

    panel, _ = load_snapshot(paths["snapshot"])
    observed_panel_hash = panel_fingerprint(panel)
    if observed_panel_hash != contract.panel_sha256:
        _fail("crowding_panel_fingerprint_mismatch", "panel fingerprint 漂移")
    cohort = _complete_current_cohort(panel)
    if len(cohort) != contract.expected_cohort:
        _fail("crowding_cohort_mismatch", "完整現時 cohort 不是 25 隻")

    receipt = json.loads(paths["event_receipt"].read_text(encoding="utf-8"))
    try:
        frozen_events = receipt["taiwan_reference_signal_layer_diagnostic"]["horizons"]["20"][
            "event_series"
        ]
    except (KeyError, TypeError) as exc:
        _fail("crowding_event_order_mismatch", f"20 日事件路徑缺失：{exc}")
    return (
        panel,
        cohort,
        frozen_events,
        {
            **{f"{key}_sha256": value for key, value in observed_hashes.items()},
            "panel_sha256": observed_panel_hash,
        },
    )


def _reconstruct_events(
    panel: Any,
    cohort: list[str],
    frozen_events: list[dict[str, Any]],
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
    cost = ROUND_TRIP_COST_BPS / 10_000.0
    rows: list[dict[str, Any]] = []

    for signal_date in signal_dates:
        position = close.index.get_loc(signal_date)
        if not isinstance(position, int):
            _fail("crowding_event_order_mismatch", "訊號日位置不唯一")
        entry_position = position + ENTRY_DELAY
        exit_position = entry_position + HOLDING_SESSIONS - 1
        if exit_position >= len(close.index) or position < CORRELATION_RETURN_WINDOW:
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
            _fail("crowding_execution_rule_mismatch", "個股持有期回報非有限")
        qqq_gross = float(
            panel.close.loc[exit_date, "QQQ"] / panel.open.loc[entry_date, "QQQ"] - 1.0
        )
        correlation_returns = (
            close.iloc[position - CORRELATION_RETURN_WINDOW : position + 1]
            .pct_change(fill_method=None)
            .iloc[1:]
        )
        if len(correlation_returns) != CORRELATION_RETURN_WINDOW:
            _fail("crowding_correlation_window_mismatch", "不是 60 個相關回報")
        correlation = correlation_returns.corr()
        pairwise = _pairwise_summary(correlation, selected)
        eligible_mean_gross = float(gross.loc[eligible].mean())
        top7_net = float(gross.loc[selected].mean() - cost)
        eligible_net = eligible_mean_gross - cost
        complete_net = float(gross.mean() - cost)
        qqq_net = qqq_gross - cost
        contributions = {
            ticker: float((gross.loc[ticker] - eligible_mean_gross) / TOP_K) for ticker in selected
        }
        rows.append(
            {
                "signal_date": pd.Timestamp(signal_date),
                "entry_date": pd.Timestamp(entry_date),
                "exit_date": pd.Timestamp(exit_date),
                "eligible": eligible,
                "ranked": ranked,
                "selected": selected,
                "gross": gross,
                "qqq_gross": qqq_gross,
                "correlation": correlation,
                "pairwise": pairwise,
                "top7_return": top7_net,
                "eligible_equal_return": eligible_net,
                "complete_cohort_equal_return": complete_net,
                "qqq_return": qqq_net,
                "active_difference": top7_net - eligible_net,
                "contributions": contributions,
            }
        )

    if len(rows) != EXPECTED_EVENTS or len(frozen_events) != EXPECTED_EVENTS:
        _fail("crowding_event_order_mismatch", "重建或凍結事件不是 905 列")
    date_strings = [row["signal_date"].strftime("%Y-%m-%d") for row in rows]
    frozen_dates = [str(row["signal_date"]) for row in frozen_events]
    if (
        date_strings != frozen_dates
        or date_strings[0] != FIRST_SIGNAL_DATE
        or date_strings[-1] != LAST_SIGNAL_DATE
    ):
        _fail("crowding_event_order_mismatch", "重建日期未逐列對齊")

    return_columns = (
        "top7_return",
        "eligible_equal_return",
        "complete_cohort_equal_return",
        "qqq_return",
    )
    residuals = {
        key: max(
            abs(float(row[key]) - float(frozen[key]))
            for row, frozen in zip(rows, frozen_events, strict=True)
        )
        for key in return_columns
    }
    maximum_residual = max(residuals.values())
    if maximum_residual > RECONSTRUCTION_TOLERANCE:
        _fail(
            "crowding_execution_rule_mismatch",
            f"逐列回報重建最大誤差 {maximum_residual:.3e}",
        )

    contribution_residuals = [
        abs(sum(row["contributions"].values()) - row["active_difference"]) for row in rows
    ]
    maximum_contribution_residual = max(contribution_residuals)
    if maximum_contribution_residual > RECONSTRUCTION_TOLERANCE:
        _fail(
            "crowding_contribution_identity_failed",
            f"逐股貢獻最大殘差 {maximum_contribution_residual:.3e}",
        )

    event_hash_payload = [
        {
            "signal_date": row["signal_date"].strftime("%Y-%m-%d"),
            "selected": row["selected"],
            **{key: row[key] for key in return_columns},
        }
        for row in rows
    ]
    return rows, {
        "return_residuals": residuals,
        "maximum_return_residual": maximum_residual,
        "maximum_contribution_identity_residual": maximum_contribution_residual,
        "event_selection_sha256": hashlib.sha256(
            json.dumps(
                event_hash_payload,
                sort_keys=True,
                separators=(",", ":"),
            ).encode()
        ).hexdigest(),
    }


def _exclusion_active_values(
    events: list[dict[str, Any]], excluded: set[str]
) -> tuple[np.ndarray, dict[str, Any]]:
    values = np.empty(len(events), dtype=float)
    accepted_counts = np.empty(len(events), dtype=int)
    cost = ROUND_TRIP_COST_BPS / 10_000.0
    for index, event in enumerate(events):
        eligible = [ticker for ticker in event["eligible"] if ticker not in excluded]
        selected = [ticker for ticker in event["ranked"] if ticker not in excluded][:TOP_K]
        if not eligible or not selected or len(selected) != min(TOP_K, len(eligible)):
            _fail(
                "crowding_baseline_fairness_breached",
                "matched-cash 刪除壓力沒有可用股份或排序不完整",
            )
        accepted_count = len(selected)
        exposure = accepted_count / TOP_K
        gross = event["gross"]
        candidate = float(gross.loc[selected].sum() / TOP_K - cost * exposure)
        matched_eligible = float(exposure * gross.loc[eligible].mean() - cost * exposure)
        values[index] = candidate - matched_eligible
        accepted_counts[index] = accepted_count
    exposures = accepted_counts / TOP_K
    return values, {
        "matched_cash": True,
        "mean_accepted_count": float(accepted_counts.mean()),
        "minimum_accepted_count": int(accepted_counts.min()),
        "mean_equity_exposure": float(exposures.mean()),
        "minimum_equity_exposure": float(exposures.min()),
        "full_top7_fraction": float((accepted_counts == TOP_K).mean()),
        "cash_slots": int((TOP_K - accepted_counts).sum()),
    }


def _correlation_cap_values(
    events: list[dict[str, Any]], dates: pd.Series
) -> tuple[np.ndarray, dict[str, Any]]:
    cost = ROUND_TRIP_COST_BPS / 10_000.0
    active = np.empty(len(events), dtype=float)
    qqq_active = np.empty(len(events), dtype=float)
    candidate_returns = np.empty(len(events), dtype=float)
    matched_eligible_returns = np.empty(len(events), dtype=float)
    accepted_counts: list[int] = []
    before_correlations: list[float] = []
    after_correlations: list[float] = []
    before_effective: list[float] = []
    after_effective: list[float] = []
    rejected_slots = 0

    for index, event in enumerate(events):
        accepted: list[str] = []
        correlation = event["correlation"]
        for ticker in event["selected"]:
            high_links = sum(
                float(correlation.loc[ticker, other]) > CORRELATION_THRESHOLD for other in accepted
            )
            if high_links >= CORRELATION_CAP:
                rejected_slots += 1
                continue
            accepted.append(ticker)
        accepted_count = len(accepted)
        exposure = accepted_count / TOP_K
        gross = event["gross"]
        eligible_mean = float(gross.loc[event["eligible"]].mean())
        candidate = float(gross.loc[accepted].sum() / TOP_K - cost * exposure)
        matched_eligible = float(exposure * eligible_mean - cost * exposure)
        matched_qqq = float(exposure * event["qqq_gross"] - cost * exposure)
        candidate_returns[index] = candidate
        matched_eligible_returns[index] = matched_eligible
        active[index] = candidate - matched_eligible
        qqq_active[index] = candidate - matched_qqq
        accepted_counts.append(accepted_count)
        before = event["pairwise"]
        after = _pairwise_summary(correlation, accepted)
        before_correlations.append(before["mean_pairwise_correlation"])
        after_correlations.append(after["mean_pairwise_correlation"])
        before_effective.append(before["effective_bets"])
        after_effective.append(after["effective_bets"])

    counts = np.asarray(accepted_counts, dtype=float)
    before_corr = np.asarray(before_correlations, dtype=float)
    after_corr = np.asarray(after_correlations, dtype=float)
    return active, {
        "rule": {
            "source_rank_scope": "original_top7_only",
            "correlation_return_window": CORRELATION_RETURN_WINDOW,
            "correlation_threshold_strictly_above": CORRELATION_THRESHOLD,
            "high_link_cap": CORRELATION_CAP,
            "backfill": False,
            "rejected_weight_destination": "zero_return_cash",
            "per_accepted_stock_weight": 1.0 / TOP_K,
            "matched_baseline_exposure": True,
        },
        "accepted_count": {
            "mean": float(counts.mean()),
            "median": float(np.median(counts)),
            "minimum": int(counts.min()),
            "maximum": int(counts.max()),
            "full_top7_fraction": float((counts == TOP_K).mean()),
            "mean_equity_exposure": float((counts / TOP_K).mean()),
            "rejected_slots": rejected_slots,
        },
        "crowding_change": {
            "mean_pairwise_correlation_before": float(before_corr.mean()),
            "mean_pairwise_correlation_after": float(after_corr.mean()),
            "mean_pairwise_correlation_reduction": float(before_corr.mean() - after_corr.mean()),
            "median_effective_bets_before": float(np.median(before_effective)),
            "median_effective_bets_after": float(np.median(after_effective)),
        },
        "candidate_return": {
            "mean": float(candidate_returns.mean()),
            "median": float(np.median(candidate_returns)),
        },
        "matched_eligible_return": {
            "mean": float(matched_eligible_returns.mean()),
            "median": float(np.median(matched_eligible_returns)),
        },
        "vs_matched_eligible": _comparison(active, dates),
        "vs_matched_qqq": _comparison(qqq_active, dates),
    }


def _holm_adjust(rows: list[dict[str, Any]]) -> dict[str, float]:
    ordered = sorted(rows, key=lambda row: (row["raw_normal_p"], row["id"]))
    adjusted: dict[str, float] = {}
    running = 0.0
    total = len(ordered)
    for rank, row in enumerate(ordered):
        candidate = min(1.0, (total - rank) * row["raw_normal_p"])
        running = max(running, candidate)
        adjusted[row["id"]] = running
    return adjusted


def _common_bootstrap(
    matrix: np.ndarray, observed_t: np.ndarray, standard_errors: np.ndarray
) -> dict[str, Any]:
    centered = matrix - matrix.mean(axis=0, keepdims=True)
    if not np.allclose(centered.mean(axis=0), 0.0, atol=1e-15):
        _fail("crowding_bootstrap_contract_mismatch", "bootstrap 去中心化失敗")
    if (standard_errors <= 0.0).any():
        _fail("crowding_bootstrap_contract_mismatch", "NW 標準誤非正")
    rows = len(matrix)
    blocks_per_path = math.ceil(rows / BOOTSTRAP_BLOCK_LENGTH)
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    starts = rng.integers(0, rows, size=(BOOTSTRAP_PATHS, blocks_per_path), dtype=np.int64)
    offsets = np.arange(BOOTSTRAP_BLOCK_LENGTH, dtype=np.int64)
    max_abs = np.empty(BOOTSTRAP_PATHS, dtype=float)
    batch_size = 250
    for start in range(0, BOOTSTRAP_PATHS, batch_size):
        stop = min(BOOTSTRAP_PATHS, start + batch_size)
        indices = (starts[start:stop, :, None] + offsets[None, None, :]) % rows
        indices = indices.reshape(stop - start, -1)[:, :rows]
        means = centered[indices].mean(axis=1)
        t_star = means / standard_errors
        max_abs[start:stop] = np.abs(t_star).max(axis=1)
    denominator = BOOTSTRAP_PATHS + 1.0
    p_values = (
        1.0 + (max_abs[:, None] >= np.abs(observed_t)[None, :]).sum(axis=0).astype(float)
    ) / denominator
    return {
        "block_length_events": BOOTSTRAP_BLOCK_LENGTH,
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
        Callable[[FrozenCrowdingContract], FrozenCrowdingContract],
    ]
]:
    return [
        (
            "01",
            "協議 SHA 漂移",
            "crowding_protocol_mismatch",
            lambda c: replace(c, protocol_sha256="0" * 64),
        ),
        (
            "02",
            "行情 archive SHA 漂移",
            "crowding_snapshot_hash_mismatch",
            lambda c: replace(c, snapshot_sha256="0" * 64),
        ),
        (
            "03",
            "panel fingerprint 漂移",
            "crowding_panel_fingerprint_mismatch",
            lambda c: replace(c, panel_sha256="0" * 64),
        ),
        (
            "04",
            "watchlist SHA 漂移",
            "crowding_watchlist_hash_mismatch",
            lambda c: replace(c, watchlist_sha256="0" * 64),
        ),
        (
            "05",
            "事件收據 SHA 漂移",
            "crowding_event_receipt_hash_mismatch",
            lambda c: replace(c, event_receipt_sha256="0" * 64),
        ),
        (
            "06",
            "台股參考 commit 漂移",
            "crowding_reference_commits_mismatch",
            lambda c: replace(c, reference_commits=REFERENCE_COMMITS[:2]),
        ),
        (
            "07",
            "cohort 改 30 隻",
            "crowding_cohort_mismatch",
            lambda c: replace(c, expected_cohort=30),
        ),
        (
            "08",
            "事件改 907 列",
            "crowding_event_order_mismatch",
            lambda c: replace(c, expected_events=907),
        ),
        ("09", "Top-K 改 10", "crowding_signal_rule_mismatch", lambda c: replace(c, top_k=10)),
        (
            "10",
            "持有期改 25 日",
            "crowding_execution_rule_mismatch",
            lambda c: replace(c, holding_sessions=25),
        ),
        (
            "11",
            "相關窗改 40 日",
            "crowding_correlation_window_mismatch",
            lambda c: replace(c, correlation_return_window=40),
        ),
        ("12", "cap 改 1", "crowding_cap_rule_mismatch", lambda c: replace(c, correlation_cap=1)),
        (
            "13",
            "N_eff 公式改寫",
            "crowding_effective_bets_formula_mismatch",
            lambda c: replace(c, effective_bets_formula="n"),
        ),
        (
            "14",
            "ticker 冒充永久 ID",
            "crowding_identifier_claim_breached",
            lambda c: replace(c, permanent_identifier_claimed=True),
        ),
        (
            "15",
            "取消貢獻恆等式",
            "crowding_contribution_identity_failed",
            lambda c: replace(c, contribution_identity_required=False),
        ),
        (
            "16",
            "刪除時不改 baseline",
            "crowding_baseline_fairness_breached",
            lambda c: replace(c, fair_exclusion_baseline=False),
        ),
        (
            "17",
            "bootstrap 各列獨立",
            "crowding_bootstrap_contract_mismatch",
            lambda c: replace(c, common_bootstrap_indices=False),
        ),
        (
            "18",
            "提前授權 Paper",
            "crowding_decision_boundary_breached",
            lambda c: replace(c, paper_authorized=True),
        ),
        (
            "19",
            "matched-cash repair 漂移",
            "crowding_repair_protocol_mismatch",
            lambda c: replace(c, matched_cash_on_insufficient_breadth=False),
        ),
    ]


def run_attack_harness() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for attack_id, label, expected_code, mutate in _contract_attacks():
        observed_code: str | None = None
        try:
            validate_crowding_contract(mutate(FROZEN_CONTRACT))
        except CorrelationCrowdingError as exc:
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


def run_correlation_crowding(root: str | Path) -> dict[str, Any]:
    root_path = Path(root).resolve()
    contract = FROZEN_CONTRACT
    validate_crowding_contract(contract)
    panel, cohort, frozen_events, integrity = _load_inputs(root_path, contract)
    events, reconstruction = _reconstruct_events(panel, cohort, frozen_events)
    dates = pd.Series([row["signal_date"] for row in events], name="signal_date")
    original_values = np.asarray([row["active_difference"] for row in events], dtype=float)

    selection_counts = {ticker: 0 for ticker in cohort}
    contribution_sums = {ticker: 0.0 for ticker in cohort}
    for event in events:
        for ticker in event["selected"]:
            selection_counts[ticker] += 1
            contribution_sums[ticker] += event["contributions"][ticker]
    total_slots = EXPECTED_EVENTS * TOP_K
    total_active_sum = float(original_values.sum())
    contributors = sorted(
        (
            {
                "symbol": ticker,
                "selection_count": selection_counts[ticker],
                "selection_slot_share": selection_counts[ticker] / total_slots,
                "active_contribution_sum": contribution_sums[ticker],
                "active_contribution_to_mean": contribution_sums[ticker] / EXPECTED_EVENTS,
                "share_of_net_active_sum": contribution_sums[ticker] / total_active_sum,
                "identifier_scope": "2026_current_symbol_not_permanent_id",
                "investment_role": "ex_post_attribution_not_a_buy_list",
            }
            for ticker in cohort
        ),
        key=lambda row: (-row["active_contribution_sum"], row["symbol"]),
    )
    for rank, row in enumerate(contributors, start=1):
        row["net_contribution_rank"] = rank

    top_contributor_symbols = [row["symbol"] for row in contributors[:3]]
    top1_values, top1_exposure = _exclusion_active_values(events, {top_contributor_symbols[0]})
    top3_values, top3_exposure = _exclusion_active_values(events, set(top_contributor_symbols))
    leave_one_rows: list[dict[str, Any]] = []
    for ticker in cohort:
        values, exposure = _exclusion_active_values(events, {ticker})
        row = _comparison(values, dates)
        row["symbol"] = ticker
        row["identifier_scope"] = "2026_current_symbol_not_permanent_id"
        row["matched_cash_exposure"] = exposure
        leave_one_rows.append(row)
    leave_one_rows.sort(key=lambda row: (row["newey_west"]["t_stat"], row["symbol"]))

    cap_values, cap_result = _correlation_cap_values(events, dates)
    family_value_rows = [
        ("original_top7", "原 Top-7", original_values),
        ("remove_top1_contributor", "刪除最高一個淨貢獻代號", top1_values),
        ("remove_top3_contributors", "刪除最高三個淨貢獻代號", top3_values),
        ("correlation_cap2_stress", "60 日相關 cap 2 不回補壓力", cap_values),
    ]
    family_rows: list[dict[str, Any]] = []
    matrix_columns: list[np.ndarray] = []
    for row_id, label, values in family_value_rows:
        comparison = _comparison(values, dates)
        family_rows.append({"id": row_id, "label": label, **comparison})
        matrix_columns.append(values)
    holm = _holm_adjust(family_rows)
    matrix = np.column_stack(matrix_columns)
    observed_t = np.asarray([row["newey_west"]["t_stat"] for row in family_rows], dtype=float)
    standard_errors = np.asarray(
        [row["newey_west"]["standard_error"] for row in family_rows],
        dtype=float,
    )
    bootstrap = _common_bootstrap(matrix, observed_t, standard_errors)
    for index, row in enumerate(family_rows):
        row["holm_adjusted_p"] = holm[row["id"]]
        row["bootstrap_max_t_p"] = bootstrap["single_step_max_t_p"][index]
        if row["id"] == "remove_top1_contributor":
            row["matched_cash_exposure"] = top1_exposure
        elif row["id"] == "remove_top3_contributors":
            row["matched_cash_exposure"] = top3_exposure

    pairwise_means = np.asarray(
        [row["pairwise"]["mean_pairwise_correlation"] for row in events],
        dtype=float,
    )
    pairwise_maxima = np.asarray(
        [row["pairwise"]["maximum_pairwise_correlation"] for row in events],
        dtype=float,
    )
    high_pair_counts = np.asarray(
        [row["pairwise"]["high_correlation_pair_count"] for row in events],
        dtype=float,
    )
    effective_bets = np.asarray([row["pairwise"]["effective_bets"] for row in events], dtype=float)
    crowding_summary = {
        "nominal_stocks": TOP_K,
        "pairs_per_event": TOP_K * (TOP_K - 1) // 2,
        "mean_pairwise_correlation": {
            "mean": float(pairwise_means.mean()),
            "p25": float(np.quantile(pairwise_means, 0.25)),
            "median": float(np.median(pairwise_means)),
            "p75": float(np.quantile(pairwise_means, 0.75)),
            "p95": float(np.quantile(pairwise_means, 0.95)),
        },
        "maximum_pairwise_correlation": {
            "median": float(np.median(pairwise_maxima)),
            "p75": float(np.quantile(pairwise_maxima, 0.75)),
            "p95": float(np.quantile(pairwise_maxima, 0.95)),
        },
        "high_correlation_pairs": {
            "mean": float(high_pair_counts.mean()),
            "median": float(np.median(high_pair_counts)),
            "events_with_any_fraction": float((high_pair_counts > 0).mean()),
        },
        "effective_bets": {
            "formula": EFFECTIVE_BETS_FORMULA,
            "mean": float(effective_bets.mean()),
            "p05": float(np.quantile(effective_bets, 0.05)),
            "p25": float(np.quantile(effective_bets, 0.25)),
            "median": float(np.median(effective_bets)),
            "p75": float(np.quantile(effective_bets, 0.75)),
            "fraction_below_3": float((effective_bets < 3.0).mean()),
        },
    }

    selection_rows = sorted(
        contributors,
        key=lambda row: (-row["selection_count"], row["symbol"]),
    )
    maximum_slot_share = selection_rows[0]["selection_slot_share"]
    top3_slot_share = sum(row["selection_slot_share"] for row in selection_rows[:3])
    family_by_id = {row["id"]: row for row in family_rows}
    top1_stress = family_by_id["remove_top1_contributor"]
    top3_stress = family_by_id["remove_top3_contributors"]
    cap_stress = family_by_id["correlation_cap2_stress"]
    minimum_leave_one_t = min(row["newey_west"]["t_stat"] for row in leave_one_rows)
    all_leave_one_positive = all(row["mean_difference"] > 0.0 for row in leave_one_rows)
    gates = [
        {
            "id": "exact_event_reconstruction",
            "label": "四條原始事件回報逐列重建誤差不高於 1e-12",
            "passed": reconstruction["maximum_return_residual"] <= RECONSTRUCTION_TOLERANCE,
        },
        {
            "id": "median_effective_bets",
            "label": "原 Top-7 中位有效獨立注數不低於 3.5",
            "passed": crowding_summary["effective_bets"]["median"] >= 3.5,
        },
        {
            "id": "low_effective_bet_fraction",
            "label": "有效獨立注數低於 3 的事件不多於 25%",
            "passed": crowding_summary["effective_bets"]["fraction_below_3"] <= 0.25,
        },
        {
            "id": "single_symbol_slot_share",
            "label": "單一現時代號選中 slot share 不高於 10%",
            "passed": maximum_slot_share <= 0.10,
        },
        {
            "id": "top3_symbol_slot_share",
            "label": "slot share 最高三個現時代號合計不高於 25%",
            "passed": top3_slot_share <= 0.25,
        },
        {
            "id": "remove_top1_contributor",
            "label": "刪除最高一個淨貢獻代號後平均為正且 NW t 不低於 1.96",
            "passed": top1_stress["mean_difference"] > 0.0
            and top1_stress["newey_west"]["t_stat"] >= 1.96,
        },
        {
            "id": "remove_top3_contributors",
            "label": "刪除最高三個淨貢獻代號後平均為正且 NW t 不低於 1.96",
            "passed": top3_stress["mean_difference"] > 0.0
            and top3_stress["newey_west"]["t_stat"] >= 1.96,
        },
        {
            "id": "all_leave_one_symbol_out",
            "label": "25 條 leave-one-symbol-out 全正且最低 NW t 不低於 1.96",
            "passed": all_leave_one_positive and minimum_leave_one_t >= 1.96,
        },
        {
            "id": "correlation_reduction",
            "label": "相關性上限令事件平均 pairwise correlation 至少降低 0.05",
            "passed": cap_result["crowding_change"]["mean_pairwise_correlation_reduction"] >= 0.05,
        },
        {
            "id": "correlation_cap_exposure",
            "label": "平均股票持倉不少於 6/7 且最少一半事件保留完整 7 隻",
            "passed": cap_result["accepted_count"]["mean_equity_exposure"] >= 6 / 7
            and cap_result["accepted_count"]["full_top7_fraction"] >= 0.50,
        },
        {
            "id": "correlation_cap_active_effect",
            "label": "相關性上限對 matched eligible 為正、NW t 過 1.96、兩半同正",
            "passed": cap_stress["mean_difference"] > 0.0
            and cap_stress["newey_west"]["t_stat"] >= 1.96
            and all(
                cap_stress["fixed_halves"][half]["mean_difference"] > 0.0
                for half in ("first", "second")
            ),
        },
        {
            "id": "stress_family_correction",
            "label": "刪除最高三個及相關 cap 壓力的 Holm／max-t p 均不高於 0.05",
            "passed": all(
                family_by_id[row_id]["holm_adjusted_p"] <= FAMILY_ALPHA
                and family_by_id[row_id]["bootstrap_max_t_p"] <= FAMILY_ALPHA
                for row_id in (
                    "remove_top3_contributors",
                    "correlation_cap2_stress",
                )
            ),
        },
    ]
    gate_summary = {
        "passed": sum(int(row["passed"]) for row in gates),
        "total": len(gates),
        "all_passed": all(row["passed"] for row in gates),
    }

    controls = [
        {
            "id": "01",
            "label": "協議 SHA",
            "passed": integrity["protocol_sha256"] == PROTOCOL_SHA256,
        },
        {
            "id": "02",
            "label": "行情 archive SHA",
            "passed": integrity["snapshot_sha256"] == SNAPSHOT_SHA256,
        },
        {
            "id": "03",
            "label": "panel fingerprint",
            "passed": integrity["panel_sha256"] == PANEL_SHA256,
        },
        {
            "id": "04",
            "label": "watchlist SHA",
            "passed": integrity["watchlist_sha256"] == WATCHLIST_SHA256,
        },
        {
            "id": "05",
            "label": "事件收據 SHA",
            "passed": integrity["event_receipt_sha256"] == EVENT_RECEIPT_SHA256,
        },
        {
            "id": "06",
            "label": "三個台股參考 commit",
            "passed": contract.reference_commits == REFERENCE_COMMITS,
        },
        {"id": "07", "label": "25 隻完整現時 cohort", "passed": len(cohort) == EXPECTED_COHORT},
        {
            "id": "08",
            "label": "905 個固定訊號日",
            "passed": len(events) == EXPECTED_EVENTS and dates.is_monotonic_increasing,
        },
        {
            "id": "09",
            "label": "20 日動量／60 日趨勢／Top-7",
            "passed": contract.momentum_sessions == 20
            and contract.trend_sessions == 60
            and contract.top_k == 7,
        },
        {
            "id": "10",
            "label": "D+1／20 日／來回 20 bps",
            "passed": contract.entry_delay == 1
            and contract.holding_sessions == 20
            and contract.round_trip_cost_bps == 20,
        },
        {
            "id": "11",
            "label": "60 個事前日回報相關",
            "passed": contract.correlation_return_window == 60,
        },
        {
            "id": "12",
            "label": "corr >0.70／cap 2／不回補",
            "passed": contract.correlation_threshold == 0.70
            and contract.correlation_cap == 2
            and contract.no_backfill,
        },
        {
            "id": "13",
            "label": "有效獨立注數固定公式",
            "passed": contract.effective_bets_formula == EFFECTIVE_BETS_FORMULA,
        },
        {
            "id": "14",
            "label": "現時代號不冒充永久 ID",
            "passed": contract.current_identifiers_only
            and not contract.permanent_identifier_claimed,
        },
        {
            "id": "15",
            "label": "逐股淨貢獻恆等式",
            "passed": reconstruction["maximum_contribution_identity_residual"]
            <= RECONSTRUCTION_TOLERANCE,
        },
        {
            "id": "16",
            "label": "刪除同步修改合資格 baseline",
            "passed": contract.fair_exclusion_baseline
            and contract.matched_cash_on_insufficient_breadth,
        },
        {
            "id": "17",
            "label": "四假說共同 52-event／20,000 路徑 bootstrap",
            "passed": bootstrap["block_length_events"] == 52
            and bootstrap["paths"] == 20_000
            and bootstrap["common_indices"]
            and bootstrap["centered_under_null"],
        },
        {
            "id": "18",
            "label": "Paper／實金決策邊界",
            "passed": not contract.paper_authorized and not contract.real_money_authorized,
        },
        {
            "id": "19",
            "label": "小股池 matched-cash schema repair",
            "passed": integrity["repair_protocol_sha256"] == REPAIR_PROTOCOL_SHA256
            and contract.matched_cash_on_insufficient_breadth,
        },
    ]
    control_summary = {
        "passed": sum(int(row["passed"]) for row in controls),
        "total": len(controls),
        "all_passed": all(row["passed"] for row in controls),
    }
    attacks = run_attack_harness()
    attack_summary = {
        "rejected": sum(int(row["rejected"]) for row in attacks),
        "total": len(attacks),
        "all_rejected": all(row["rejected"] for row in attacks),
    }

    return {
        "schema_version": SCHEMA_VERSION,
        "research_round": RESEARCH_ROUND,
        "generated_on": "2026-08-04",
        "protocol": {
            "path": PROTOCOL_PATH,
            "sha256": integrity["protocol_sha256"],
            "commit": PROTOCOL_COMMIT,
            "calculated_after_protocol_commit": True,
            "initial_parent_protocol_run": {
                "status": "failed_closed_before_output",
                "error_code": "crowding_baseline_fairness_breached",
            },
            "schema_repair": {
                "path": REPAIR_PROTOCOL_PATH,
                "sha256": integrity["repair_protocol_sha256"],
                "commit": REPAIR_PROTOCOL_COMMIT,
                "calculated_after_repair_commit": True,
                "independent_first_unseen_evidence": False,
            },
        },
        "references": [
            {"repository": name, "commit": commit} for name, commit in REFERENCE_COMMITS
        ],
        "input": {
            "snapshot_path": SNAPSHOT_PATH,
            "snapshot_sha256": integrity["snapshot_sha256"],
            "panel_sha256": integrity["panel_sha256"],
            "watchlist_path": WATCHLIST_PATH,
            "watchlist_sha256": integrity["watchlist_sha256"],
            "event_receipt_path": EVENT_RECEIPT_PATH,
            "event_receipt_sha256": integrity["event_receipt_sha256"],
            "current_cohort_count": len(cohort),
            "events": len(events),
            "first_signal_date": dates.iloc[0].strftime("%Y-%m-%d"),
            "last_signal_date": dates.iloc[-1].strftime("%Y-%m-%d"),
            "event_selection_sha256": reconstruction["event_selection_sha256"],
            "survivorship_bias_warning": True,
            "identifier_scope": "2026_current_symbols_not_permanent_ids",
        },
        "reconstruction": reconstruction,
        "original_crowding": crowding_summary,
        "symbol_selection_concentration": {
            "total_slots": total_slots,
            "maximum_single_symbol_slot_share": maximum_slot_share,
            "top3_symbol_slot_share": top3_slot_share,
            "slot_share_ranked": [
                {
                    "symbol": row["symbol"],
                    "selection_count": row["selection_count"],
                    "selection_slot_share": row["selection_slot_share"],
                    "identifier_scope": row["identifier_scope"],
                }
                for row in selection_rows
            ],
        },
        "current_symbol_contributors": contributors,
        "top_contributor_symbols_ex_post_not_a_buy_list": top_contributor_symbols,
        "leave_one_symbol_out": {
            "all_mean_positive": all_leave_one_positive,
            "minimum_newey_west_t": minimum_leave_one_t,
            "rows_sorted_weakest_first": leave_one_rows,
        },
        "correlation_cap2_stress": cap_result,
        "family": {
            "size": FAMILY_SIZE,
            "alpha": FAMILY_ALPHA,
            "comparisons": family_rows,
            "bootstrap": bootstrap,
        },
        "gates": gates,
        "gate_summary": gate_summary,
        "controls": controls,
        "control_summary": control_summary,
        "attacks": attacks,
        "attack_summary": attack_summary,
        "research_role": "current_survivor_cohort_correlation_and_identifier_falsification_only",
        "decision": {
            "not_rejected_by_round25": gate_summary["all_passed"],
            "new_strategy_created": False,
            "formal_global_search_trials_unchanged": 6_208,
            "formal_readiness": "1/18",
            "point_in_time_readiness": "1/20",
            "qualified_provider_packages": 0,
            "complete_risk_free_packages": 0,
            "formal_strategy_runs": 0,
            "paper_status": "all_cash_not_started",
            "paper_positions": 0,
            "real_money_action_usd": 0,
            "us1000_is_reader_example_only": True,
            "can_promote_from_this_round": False,
        },
    }
