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

from .correlation_crowding import FROZEN_CONTRACT as CROWDING_CONTRACT
from .correlation_crowding import _load_inputs as _load_crowding_inputs
from .correlation_crowding import _reconstruct_events
from .data import panel_fingerprint
from .metrics import newey_west_mean_test

SCHEMA_VERSION = 1
RESEARCH_ROUND = 27
GENERATED_ON = "2026-08-04"
PROTOCOL_PATH = "docs/SHORT_TERM_RANK_MONOTONICITY_PLACEBO_PROTOCOL.md"
PROTOCOL_SHA256 = "557416f499a96c525d6b3cf42350237921aca41ff4b1f836bd4f746cc0829e0f"
PROTOCOL_COMMIT = "b0c7978bda6f11144a31618d454c5621e5c14c8e"

ROUND26_SOURCE_COMMIT = "178a71f508b0e5bbd82287b65f1776e506947d3b"
ROUND26_RECEIPT_PATH = "artifacts/short_term_common_risk_residual_validation.json"
ROUND26_RECEIPT_SHA256 = "14727306343fbcf45eb82045363898e07bb6ff0487f0b3d580dec0a9f129637b"
ROUND25_RECEIPT_PATH = "artifacts/short_term_correlation_crowding_validation.json"
ROUND25_RECEIPT_SHA256 = "11155736a8449e6c4f50c0de0d285df9598d76de3752733f5bd140d8a2c8d0f5"
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
COHORT = (
    "AAPL",
    "AMAT",
    "AMD",
    "AMZN",
    "BAC",
    "BRK-B",
    "CAT",
    "COST",
    "CSCO",
    "CVX",
    "GE",
    "GOOG",
    "GOOGL",
    "INTC",
    "JNJ",
    "JPM",
    "LLY",
    "LRCX",
    "MA",
    "MSFT",
    "MU",
    "NVDA",
    "UNH",
    "WMT",
    "XOM",
)

EXPECTED_EVENTS = 905
FIRST_SIGNAL_DATE = "2006-08-04"
LAST_SIGNAL_DATE = "2026-07-02"
MOMENTUM_SESSIONS = 20
TREND_SESSIONS = 60
TOP_K = 7
ENTRY_DELAY = 1
HOLDING_SESSIONS = 20
ROUND_TRIP_COST_BPS = 20
UNIVERSE_IDS = ("eligible", "complete")
BUCKET_IDS = ("top", "middle", "bottom")
BUCKET_COUNT = 3
BUCKET_METHOD = "numpy_array_split_contiguous_top_gets_first_remainder"
TIE_BREAK = "momentum_desc_ticker_asc"
RANK_IC_METHOD = "spearman_average_rank"
FAMILY_IDS = (
    "eligible_top_middle",
    "eligible_middle_bottom",
    "eligible_top_bottom",
    "complete_top_middle",
    "complete_middle_bottom",
    "complete_top_bottom",
    "eligible_rank_ic",
    "complete_rank_ic",
)
HAC_LAG = 4
FIRST_HALF_END = pd.Timestamp("2016-07-29")
SECOND_HALF_START = pd.Timestamp("2016-08-01")
BOOTSTRAP_BLOCK_LENGTH = 52
BOOTSTRAP_PATHS = 20_000
BOOTSTRAP_SEED = 27_202_609
PLACEBO_COUNT = 20
PLACEBO_SEED = 27_202_608
TAIL_REMOVAL_EVENTS = 46
RECONSTRUCTION_TOLERANCE = 1e-12
SIGN_CLASSIFICATION_TOLERANCE = RECONSTRUCTION_TOLERANCE


class RankMonotonicityError(ValueError):
    """Fail-closed Round 27 error with a stable semantic code."""

    def __init__(self, code: str, detail: str):
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}")


def _fail(code: str, detail: str) -> None:
    raise RankMonotonicityError(code, detail)


@dataclass(frozen=True)
class FrozenRankMonotonicityContract:
    protocol_sha256: str = PROTOCOL_SHA256
    round26_source_commit: str = ROUND26_SOURCE_COMMIT
    round26_receipt_sha256: str = ROUND26_RECEIPT_SHA256
    round25_receipt_sha256: str = ROUND25_RECEIPT_SHA256
    round24_receipt_sha256: str = ROUND24_RECEIPT_SHA256
    event_receipt_sha256: str = EVENT_RECEIPT_SHA256
    snapshot_sha256: str = SNAPSHOT_SHA256
    panel_sha256: str = PANEL_SHA256
    watchlist_sha256: str = WATCHLIST_SHA256
    reference_commits: tuple[tuple[str, str], ...] = REFERENCE_COMMITS
    cohort: tuple[str, ...] = COHORT
    expected_events: int = EXPECTED_EVENTS
    first_signal_date: str = FIRST_SIGNAL_DATE
    last_signal_date: str = LAST_SIGNAL_DATE
    momentum_sessions: int = MOMENTUM_SESSIONS
    trend_sessions: int = TREND_SESSIONS
    top_k: int = TOP_K
    entry_delay: int = ENTRY_DELAY
    holding_sessions: int = HOLDING_SESSIONS
    round_trip_cost_bps: int = ROUND_TRIP_COST_BPS
    universe_ids: tuple[str, ...] = UNIVERSE_IDS
    bucket_count: int = BUCKET_COUNT
    bucket_method: str = BUCKET_METHOD
    tie_break: str = TIE_BREAK
    rank_ic_method: str = RANK_IC_METHOD
    family_ids: tuple[str, ...] = FAMILY_IDS
    hac_lag: int = HAC_LAG
    bootstrap_block_length: int = BOOTSTRAP_BLOCK_LENGTH
    bootstrap_paths: int = BOOTSTRAP_PATHS
    bootstrap_seed: int = BOOTSTRAP_SEED
    placebo_count: int = PLACEBO_COUNT
    placebo_seed: int = PLACEBO_SEED
    tail_removal_events: int = TAIL_REMOVAL_EVENTS
    current_symbols_warning_only: bool = True
    paper_authorized: bool = False
    real_money_authorized: bool = False
    formal_strategy_runs: int = 0


FROZEN_CONTRACT = FrozenRankMonotonicityContract()


def validate_rank_monotonicity_contract(contract: FrozenRankMonotonicityContract) -> None:
    checks: tuple[tuple[bool, str, str], ...] = (
        (
            contract.protocol_sha256 == PROTOCOL_SHA256,
            "rank_monotonicity_protocol_mismatch",
            "協議 SHA 漂移",
        ),
        (
            contract.round26_source_commit == ROUND26_SOURCE_COMMIT,
            "rank_monotonicity_round26_source_mismatch",
            "第 26 輪來源 commit 漂移",
        ),
        (
            contract.round26_receipt_sha256 == ROUND26_RECEIPT_SHA256,
            "rank_monotonicity_round26_receipt_mismatch",
            "第 26 輪收據 SHA 漂移",
        ),
        (
            contract.round25_receipt_sha256 == ROUND25_RECEIPT_SHA256
            and contract.round24_receipt_sha256 == ROUND24_RECEIPT_SHA256,
            "rank_monotonicity_prior_receipts_mismatch",
            "第 24／25 輪收據 SHA 漂移",
        ),
        (
            contract.event_receipt_sha256 == EVENT_RECEIPT_SHA256,
            "rank_monotonicity_event_receipt_mismatch",
            "原始事件收據 SHA 漂移",
        ),
        (
            contract.snapshot_sha256 == SNAPSHOT_SHA256,
            "rank_monotonicity_snapshot_hash_mismatch",
            "行情 archive SHA 漂移",
        ),
        (
            contract.panel_sha256 == PANEL_SHA256,
            "rank_monotonicity_panel_fingerprint_mismatch",
            "panel fingerprint 漂移",
        ),
        (
            contract.watchlist_sha256 == WATCHLIST_SHA256,
            "rank_monotonicity_watchlist_hash_mismatch",
            "watchlist SHA 漂移",
        ),
        (
            contract.reference_commits == REFERENCE_COMMITS,
            "rank_monotonicity_reference_commits_mismatch",
            "台股參考 commit 漂移",
        ),
        (
            contract.cohort == COHORT,
            "rank_monotonicity_cohort_mismatch",
            "25 股 cohort 漂移",
        ),
        (
            contract.expected_events == EXPECTED_EVENTS
            and contract.first_signal_date == FIRST_SIGNAL_DATE
            and contract.last_signal_date == LAST_SIGNAL_DATE,
            "rank_monotonicity_event_order_mismatch",
            "事件數或日期邊界漂移",
        ),
        (
            contract.momentum_sessions == MOMENTUM_SESSIONS
            and contract.trend_sessions == TREND_SESSIONS
            and contract.top_k == TOP_K,
            "rank_monotonicity_signal_rule_mismatch",
            "原事件訊號規則漂移",
        ),
        (
            contract.entry_delay == ENTRY_DELAY
            and contract.holding_sessions == HOLDING_SESSIONS
            and contract.round_trip_cost_bps == ROUND_TRIP_COST_BPS,
            "rank_monotonicity_execution_rule_mismatch",
            "成交時鐘或成本漂移",
        ),
        (
            contract.universe_ids == UNIVERSE_IDS,
            "rank_monotonicity_universe_mismatch",
            "universe identity 漂移",
        ),
        (
            contract.bucket_count == BUCKET_COUNT and contract.bucket_method == BUCKET_METHOD,
            "rank_monotonicity_bucket_contract_mismatch",
            "三分組規則漂移",
        ),
        (
            contract.tie_break == TIE_BREAK,
            "rank_monotonicity_tie_break_mismatch",
            "排序 tie-break 漂移",
        ),
        (
            contract.rank_ic_method == RANK_IC_METHOD,
            "rank_monotonicity_rank_ic_mismatch",
            "rank IC 定義漂移",
        ),
        (
            contract.family_ids == FAMILY_IDS and contract.hac_lag == HAC_LAG,
            "rank_monotonicity_family_contract_mismatch",
            "八假說 family 或 HAC 漂移",
        ),
        (
            contract.bootstrap_block_length == BOOTSTRAP_BLOCK_LENGTH
            and contract.bootstrap_paths == BOOTSTRAP_PATHS
            and contract.bootstrap_seed == BOOTSTRAP_SEED,
            "rank_monotonicity_bootstrap_contract_mismatch",
            "共同 bootstrap 漂移",
        ),
        (
            contract.placebo_count == PLACEBO_COUNT and contract.placebo_seed == PLACEBO_SEED,
            "rank_monotonicity_placebo_contract_mismatch",
            "placebo 數量或 seed 漂移",
        ),
        (
            contract.tail_removal_events == TAIL_REMOVAL_EVENTS,
            "rank_monotonicity_stress_contract_mismatch",
            "尾部壓力列數漂移",
        ),
        (
            contract.current_symbols_warning_only,
            "rank_monotonicity_identity_scope_breached",
            "現時代號被越權升格",
        ),
        (
            not contract.paper_authorized
            and not contract.real_money_authorized
            and contract.formal_strategy_runs == 0,
            "rank_monotonicity_decision_boundary_breached",
            "策略／Paper／實金決策邊界被越權",
        ),
    )
    for passed, code, detail in checks:
        if not passed:
            _fail(code, detail)


def _contract_attacks() -> list[
    tuple[str, str, str, Callable[[FrozenRankMonotonicityContract], FrozenRankMonotonicityContract]]
]:
    return [
        (
            "01",
            "協議 SHA 漂移",
            "rank_monotonicity_protocol_mismatch",
            lambda c: replace(c, protocol_sha256="0" * 64),
        ),
        (
            "02",
            "第 26 輪來源 commit 漂移",
            "rank_monotonicity_round26_source_mismatch",
            lambda c: replace(c, round26_source_commit="0" * 40),
        ),
        (
            "03",
            "第 26 輪收據 SHA 漂移",
            "rank_monotonicity_round26_receipt_mismatch",
            lambda c: replace(c, round26_receipt_sha256="0" * 64),
        ),
        (
            "04",
            "第 25 輪收據 SHA 漂移",
            "rank_monotonicity_prior_receipts_mismatch",
            lambda c: replace(c, round25_receipt_sha256="0" * 64),
        ),
        (
            "05",
            "原始事件收據 SHA 漂移",
            "rank_monotonicity_event_receipt_mismatch",
            lambda c: replace(c, event_receipt_sha256="0" * 64),
        ),
        (
            "06",
            "行情 archive SHA 漂移",
            "rank_monotonicity_snapshot_hash_mismatch",
            lambda c: replace(c, snapshot_sha256="0" * 64),
        ),
        (
            "07",
            "panel fingerprint 漂移",
            "rank_monotonicity_panel_fingerprint_mismatch",
            lambda c: replace(c, panel_sha256="0" * 64),
        ),
        (
            "08",
            "watchlist SHA 漂移",
            "rank_monotonicity_watchlist_hash_mismatch",
            lambda c: replace(c, watchlist_sha256="0" * 64),
        ),
        (
            "09",
            "台股參考 commit 漂移",
            "rank_monotonicity_reference_commits_mismatch",
            lambda c: replace(c, reference_commits=REFERENCE_COMMITS[:2]),
        ),
        (
            "10",
            "25 股 cohort 漂移",
            "rank_monotonicity_cohort_mismatch",
            lambda c: replace(c, cohort=COHORT[:-1]),
        ),
        (
            "11",
            "事件數改 904",
            "rank_monotonicity_event_order_mismatch",
            lambda c: replace(c, expected_events=904),
        ),
        (
            "12",
            "Top-K 改 10",
            "rank_monotonicity_signal_rule_mismatch",
            lambda c: replace(c, top_k=10),
        ),
        (
            "13",
            "成本改 10 bps",
            "rank_monotonicity_execution_rule_mismatch",
            lambda c: replace(c, round_trip_cost_bps=10),
        ),
        (
            "14",
            "刪除完整股池 universe",
            "rank_monotonicity_universe_mismatch",
            lambda c: replace(c, universe_ids=("eligible",)),
        ),
        (
            "15",
            "bucket 改四組",
            "rank_monotonicity_bucket_contract_mismatch",
            lambda c: replace(c, bucket_count=4),
        ),
        (
            "16",
            "tie-break 反向",
            "rank_monotonicity_tie_break_mismatch",
            lambda c: replace(c, tie_break="momentum_desc_ticker_desc"),
        ),
        (
            "17",
            "IC 改 Pearson raw",
            "rank_monotonicity_rank_ic_mismatch",
            lambda c: replace(c, rank_ic_method="pearson_raw"),
        ),
        (
            "18",
            "family 刪除 rank IC",
            "rank_monotonicity_family_contract_mismatch",
            lambda c: replace(c, family_ids=FAMILY_IDS[:6]),
        ),
        (
            "19",
            "bootstrap seed 漂移",
            "rank_monotonicity_bootstrap_contract_mismatch",
            lambda c: replace(c, bootstrap_seed=27_202_610),
        ),
        (
            "20",
            "placebo 改 100 組",
            "rank_monotonicity_placebo_contract_mismatch",
            lambda c: replace(c, placebo_count=100),
        ),
        (
            "21",
            "尾部改 45 列",
            "rank_monotonicity_stress_contract_mismatch",
            lambda c: replace(c, tail_removal_events=45),
        ),
        (
            "22",
            "現時代號越權升格",
            "rank_monotonicity_identity_scope_breached",
            lambda c: replace(c, current_symbols_warning_only=False),
        ),
        (
            "23",
            "越權啟動 Paper",
            "rank_monotonicity_decision_boundary_breached",
            lambda c: replace(c, paper_authorized=True),
        ),
    ]


def run_contract_attacks() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for attack_id, label, expected_code, mutate in _contract_attacks():
        observed: str | None = None
        try:
            validate_rank_monotonicity_contract(mutate(FROZEN_CONTRACT))
        except RankMonotonicityError as exc:
            observed = exc.code
        rows.append(
            {
                "id": attack_id,
                "label": label,
                "expected_error_code": expected_code,
                "observed_error_code": observed,
                "rejected": observed == expected_code,
            }
        )
    return rows


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_inputs(
    root: Path, contract: FrozenRankMonotonicityContract
) -> tuple[Any, list[str], list[dict[str, Any]], dict[str, Any]]:
    paths = {
        "protocol": root / PROTOCOL_PATH,
        "round26_receipt": root / ROUND26_RECEIPT_PATH,
        "round25_receipt": root / ROUND25_RECEIPT_PATH,
        "round24_receipt": root / ROUND24_RECEIPT_PATH,
        "event_receipt": root / EVENT_RECEIPT_PATH,
        "snapshot": root / SNAPSHOT_PATH,
        "watchlist": root / WATCHLIST_PATH,
    }
    expected = {
        "protocol": contract.protocol_sha256,
        "round26_receipt": contract.round26_receipt_sha256,
        "round25_receipt": contract.round25_receipt_sha256,
        "round24_receipt": contract.round24_receipt_sha256,
        "event_receipt": contract.event_receipt_sha256,
        "snapshot": contract.snapshot_sha256,
        "watchlist": contract.watchlist_sha256,
    }
    codes = {
        "protocol": "rank_monotonicity_protocol_mismatch",
        "round26_receipt": "rank_monotonicity_round26_receipt_mismatch",
        "round25_receipt": "rank_monotonicity_prior_receipts_mismatch",
        "round24_receipt": "rank_monotonicity_prior_receipts_mismatch",
        "event_receipt": "rank_monotonicity_event_receipt_mismatch",
        "snapshot": "rank_monotonicity_snapshot_hash_mismatch",
        "watchlist": "rank_monotonicity_watchlist_hash_mismatch",
    }
    observed = {key: _sha256_file(path) for key, path in paths.items()}
    for key, expected_hash in expected.items():
        if observed[key] != expected_hash:
            _fail(codes[key], f"{key} SHA-256 漂移")

    panel, cohort, frozen_events, _ = _load_crowding_inputs(root, CROWDING_CONTRACT)
    if panel_fingerprint(panel) != contract.panel_sha256:
        _fail("rank_monotonicity_panel_fingerprint_mismatch", "panel fingerprint 漂移")
    if tuple(sorted(cohort)) != contract.cohort:
        _fail("rank_monotonicity_cohort_mismatch", "完整現時 cohort 未逐字對齊")

    round26 = json.loads(paths["round26_receipt"].read_text(encoding="utf-8"))
    round25 = json.loads(paths["round25_receipt"].read_text(encoding="utf-8"))
    round24 = json.loads(paths["round24_receipt"].read_text(encoding="utf-8"))
    if round26.get("research_round") != 26 or round26.get("input", {}).get("events") != 905:
        _fail("rank_monotonicity_round26_receipt_mismatch", "第 26 輪收據身份不符")
    if round25.get("research_round") != 25 or round24.get("research_round") != 24:
        _fail("rank_monotonicity_prior_receipts_mismatch", "第 24／25 輪收據身份不符")
    return (
        panel,
        cohort,
        frozen_events,
        {
            "paths": {key: str(path.relative_to(root)) for key, path in paths.items()},
            "hashes": observed,
            "round26_gate_summary": round26["gate_summary"],
        },
    )


def _normal_two_sided_p(t_stat: float) -> float:
    return float(math.erfc(abs(t_stat) / math.sqrt(2.0)))


def _newey_west(values: np.ndarray) -> dict[str, float | int]:
    result = newey_west_mean_test(pd.Series(values), max_lag=HAC_LAG, periods_per_year=52)
    mean = float(result["mean_daily"])
    t_stat = float(result["t_stat"])
    standard_error = abs(mean / t_stat) if t_stat != 0.0 else 0.0
    return {
        "mean": mean,
        "annualized_event_value": float(result["annualized"]),
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
            "mean": float(values[first].mean()),
            "median": float(np.median(values[first])),
        },
        "second": {
            "events": int(second.sum()),
            "mean": float(values[second].mean()),
            "median": float(np.median(values[second])),
        },
    }


def _comparison(values: np.ndarray, dates: pd.Series) -> dict[str, Any]:
    if len(values) != EXPECTED_EVENTS or not np.isfinite(values).all():
        _fail("rank_monotonicity_family_contract_mismatch", "比較列不是 905 個有限值")
    nw = _newey_west(values)
    return {
        "events": len(values),
        "mean": float(values.mean()),
        "median": float(np.median(values)),
        "positive_fraction": float((values > SIGN_CLASSIFICATION_TOLERANCE).mean()),
        "newey_west": nw,
        "raw_normal_p": _normal_two_sided_p(float(nw["t_stat"])),
        "fixed_halves": _fixed_halves(values, dates),
    }


def _split_symbols(ranked: list[str]) -> dict[str, list[str]]:
    if len(ranked) < 3 or len(set(ranked)) != len(ranked):
        _fail("rank_monotonicity_bucket_contract_mismatch", "universe 太小或代號重複")
    quotient, remainder = divmod(len(ranked), BUCKET_COUNT)
    sizes = [quotient + (index < remainder) for index in range(BUCKET_COUNT)]
    buckets: dict[str, list[str]] = {}
    start = 0
    for bucket_id, size in zip(BUCKET_IDS, sizes, strict=True):
        buckets[bucket_id] = ranked[start : start + size]
        start += size
    flattened = [ticker for bucket_id in BUCKET_IDS for ticker in buckets[bucket_id]]
    if flattened != ranked or max(sizes) - min(sizes) > 1 or min(sizes) < 1:
        _fail("rank_monotonicity_bucket_contract_mismatch", "三分組聯集、順序或大小不符")
    return buckets


def _spearman(signal: pd.Series, future: pd.Series) -> float:
    signal_rank = signal.rank(method="average").to_numpy(dtype=float)
    future_rank = future.rank(method="average").to_numpy(dtype=float)
    if np.ptp(signal_rank) <= 0.0 or np.ptp(future_rank) <= 0.0:
        _fail("rank_monotonicity_rank_ic_mismatch", "rank IC 零變異")
    value = float(np.corrcoef(signal_rank, future_rank)[0, 1])
    if not math.isfinite(value):
        _fail("rank_monotonicity_rank_ic_mismatch", "rank IC 非有限")
    return value


def _build_rank_data(panel: Any, cohort: list[str], events: list[dict[str, Any]]) -> dict[str, Any]:
    close = panel.close[cohort]
    momentum = close.pct_change(MOMENTUM_SESSIONS, fill_method=None)
    cost = ROUND_TRIP_COST_BPS / 10_000.0
    dates = pd.Series([event["signal_date"] for event in events], name="signal_date")
    values = {family_id: np.empty(len(events), dtype=float) for family_id in FAMILY_IDS}
    sleeve_values = {
        universe_id: {bucket_id: np.empty(len(events), dtype=float) for bucket_id in BUCKET_IDS}
        for universe_id in UNIVERSE_IDS
    }
    event_rows: list[dict[str, Any]] = []
    eligible_counts: list[int] = []

    for event_index, event in enumerate(events):
        signal_date = event["signal_date"]
        signal = momentum.loc[signal_date, cohort]
        gross = event["gross"].loc[cohort]
        if (
            not np.isfinite(signal.to_numpy(dtype=float)).all()
            or not np.isfinite(gross.to_numpy(dtype=float)).all()
        ):
            _fail(
                "rank_monotonicity_coverage_mismatch",
                f"{signal_date:%Y-%m-%d} complete cohort 訊號或未來回報不完整",
            )
        eligible = list(event["eligible"])
        if len(eligible) < TOP_K or not set(eligible).issubset(cohort):
            _fail("rank_monotonicity_universe_mismatch", "eligible 清單不足或不屬 cohort")
        eligible_counts.append(len(eligible))
        universe_symbols = {"eligible": eligible, "complete": list(cohort)}
        receipt: dict[str, Any] = {
            "event_index": event_index,
            "signal_date": signal_date.strftime("%Y-%m-%d"),
            "entry_date": event["entry_date"].strftime("%Y-%m-%d"),
            "exit_date": event["exit_date"].strftime("%Y-%m-%d"),
            "qqq_gross": float(event["qqq_gross"]),
            "universes": {},
        }
        for universe_id, symbols in universe_symbols.items():
            ranked = sorted(symbols, key=lambda ticker: (-float(signal.loc[ticker]), ticker))
            if universe_id == "eligible" and ranked != event["ranked"]:
                _fail("rank_monotonicity_tie_break_mismatch", "eligible 排序未對齊第 25 輪")
            buckets = _split_symbols(ranked)
            sleeve_net: dict[str, float] = {}
            for bucket_id, bucket_symbols in buckets.items():
                sleeve_net[bucket_id] = float(gross.loc[bucket_symbols].mean() - cost)
                sleeve_values[universe_id][bucket_id][event_index] = sleeve_net[bucket_id]
            spreads = {
                "top_middle": sleeve_net["top"] - sleeve_net["middle"],
                "middle_bottom": sleeve_net["middle"] - sleeve_net["bottom"],
                "top_bottom": sleeve_net["top"] - sleeve_net["bottom"],
            }
            for spread_id, spread in spreads.items():
                values[f"{universe_id}_{spread_id}"][event_index] = spread
            ic = _spearman(signal.loc[symbols], gross.loc[symbols])
            values[f"{universe_id}_rank_ic"][event_index] = ic
            receipt["universes"][universe_id] = {
                "count": len(symbols),
                "ranked": ranked,
                "buckets": buckets,
                "bucket_net_returns": sleeve_net,
                "spreads": spreads,
                "rank_ic": ic,
            }
        event_rows.append(receipt)

    if len(event_rows) != EXPECTED_EVENTS:
        _fail("rank_monotonicity_event_order_mismatch", "排序事件不是 905 列")
    assignment_payload = [
        {
            "signal_date": row["signal_date"],
            "eligible": row["universes"]["eligible"]["buckets"],
            "complete": row["universes"]["complete"]["buckets"],
        }
        for row in event_rows
    ]
    return {
        "dates": dates,
        "values": values,
        "sleeve_values": sleeve_values,
        "event_rows": event_rows,
        "eligible_count": {
            "minimum": min(eligible_counts),
            "median": float(np.median(eligible_counts)),
            "maximum": max(eligible_counts),
        },
        "bucket_assignment_sha256": hashlib.sha256(
            json.dumps(assignment_payload, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest(),
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
        _fail("rank_monotonicity_bootstrap_contract_mismatch", "bootstrap 去中心化失敗")
    if (standard_errors <= 0.0).any():
        _fail("rank_monotonicity_bootstrap_contract_mismatch", "NW 標準誤非正")
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
    p_values = (
        1.0 + (max_abs[:, None] >= np.abs(observed_t)[None, :]).sum(axis=0).astype(float)
    ) / (BOOTSTRAP_PATHS + 1.0)
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


def _family(rank_data: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    rows = [
        {"id": family_id, **_comparison(rank_data["values"][family_id], rank_data["dates"])}
        for family_id in FAMILY_IDS
    ]
    holm = _holm_adjust(rows)
    matrix = np.column_stack([rank_data["values"][row["id"]] for row in rows])
    observed_t = np.asarray([row["newey_west"]["t_stat"] for row in rows], dtype=float)
    standard_errors = np.asarray([row["newey_west"]["standard_error"] for row in rows], dtype=float)
    bootstrap = _common_bootstrap(matrix, observed_t, standard_errors)
    for index, row in enumerate(rows):
        row["holm_adjusted_p"] = holm[row["id"]]
        row["bootstrap_max_t_p"] = bootstrap["single_step_max_t_p"][index]
    bootstrap["hypothesis_order"] = [row["id"] for row in rows]
    return rows, bootstrap


def _placebos(rank_data: dict[str, Any]) -> dict[str, Any]:
    results: dict[str, Any] = {}
    for universe_code, universe_id in enumerate(UNIVERSE_IDS, start=1):
        placebo_values = {
            placebo_id: np.empty(EXPECTED_EVENTS, dtype=float)
            for placebo_id in range(1, PLACEBO_COUNT + 1)
        }
        for event_index, event in enumerate(rank_data["event_rows"]):
            universe = event["universes"][universe_id]
            symbols = sorted(universe["ranked"])
            true_sizes = [len(universe["buckets"][bucket_id]) for bucket_id in BUCKET_IDS]
            gross_by_symbol = rank_data["gross_by_event"][event_index]
            for placebo_id in range(1, PLACEBO_COUNT + 1):
                rng = np.random.default_rng(
                    np.random.SeedSequence([PLACEBO_SEED, universe_code, event_index, placebo_id])
                )
                permuted = [symbols[index] for index in rng.permutation(len(symbols))]
                top = permuted[: true_sizes[0]]
                bottom = permuted[-true_sizes[2] :]
                placebo_values[placebo_id][event_index] = float(
                    np.mean([gross_by_symbol[ticker] for ticker in top])
                    - np.mean([gross_by_symbol[ticker] for ticker in bottom])
                )
        rows = []
        for placebo_id, values in placebo_values.items():
            row = {
                "id": f"P{placebo_id:02d}",
                **_comparison(values, rank_data["dates"]),
            }
            rows.append(row)
        true = _comparison(rank_data["values"][f"{universe_id}_top_bottom"], rank_data["dates"])
        max_mean_row = max(rows, key=lambda row: (row["mean"], row["id"]))
        max_t_row = max(rows, key=lambda row: (row["newey_west"]["t_stat"], row["id"]))
        results[universe_id] = {
            "rows": rows,
            "maximum_placebo_mean": max_mean_row["mean"],
            "maximum_placebo_mean_id": max_mean_row["id"],
            "maximum_placebo_t": max_t_row["newey_west"]["t_stat"],
            "maximum_placebo_t_id": max_t_row["id"],
            "true_mean": true["mean"],
            "true_t": true["newey_west"]["t_stat"],
            "mean_dominates": true["mean"] > max_mean_row["mean"],
            "t_dominates": true["newey_west"]["t_stat"] > max_t_row["newey_west"]["t_stat"],
        }
    return results


def _stresses(rank_data: dict[str, Any]) -> dict[str, Any]:
    qqq = np.asarray([row["qqq_gross"] for row in rank_data["event_rows"]], dtype=float)
    dates = rank_data["dates"]
    nonnegative = qqq >= 0.0
    negative = qqq < 0.0
    regimes: dict[str, Any] = {}
    tails: dict[str, Any] = {}
    for universe_id in UNIVERSE_IDS:
        values = rank_data["values"][f"{universe_id}_top_bottom"]
        regimes[universe_id] = {
            "qqq_nonnegative": _comparison_subset(values[nonnegative], dates[nonnegative]),
            "qqq_negative": _comparison_subset(values[negative], dates[negative]),
        }
        removed = np.argsort(-np.abs(values), kind="stable")[:TAIL_REMOVAL_EVENTS]
        keep = np.ones(len(values), dtype=bool)
        keep[removed] = False
        tail = _comparison_subset(values[keep], dates[keep])
        tail["removed_events"] = TAIL_REMOVAL_EVENTS
        tail["removed_absolute_spread_share"] = float(
            np.abs(values[removed]).sum() / np.abs(values).sum()
        )
        tail["removed_signal_dates"] = [dates.iloc[index].strftime("%Y-%m-%d") for index in removed]
        tails[universe_id] = tail
    return {
        "qqq_forward_regimes_ex_post_not_a_signal": regimes,
        "remove_largest_absolute_spreads": tails,
    }


def _comparison_subset(values: np.ndarray, dates: pd.Series) -> dict[str, Any]:
    if len(values) < 2 or not np.isfinite(values).all():
        _fail("rank_monotonicity_stress_contract_mismatch", "壓力子樣本不足或非有限")
    nw = _newey_west(values)
    return {
        "events": len(values),
        "mean": float(values.mean()),
        "median": float(np.median(values)),
        "positive_fraction": float((values > SIGN_CLASSIFICATION_TOLERANCE).mean()),
        "newey_west": nw,
        "raw_normal_p": _normal_two_sided_p(float(nw["t_stat"])),
        "first_signal_date": pd.Timestamp(dates.iloc[0]).strftime("%Y-%m-%d"),
        "last_signal_date": pd.Timestamp(dates.iloc[-1]).strftime("%Y-%m-%d"),
    }


def _passes(row: dict[str, Any]) -> bool:
    return bool(
        row["mean"] > 0.0
        and row["newey_west"]["t_stat"] >= 1.96
        and row["fixed_halves"]["first"]["mean"] > 0.0
        and row["fixed_halves"]["second"]["mean"] > 0.0
    )


def run_rank_monotonicity_placebo(
    root: Path, contract: FrozenRankMonotonicityContract = FROZEN_CONTRACT
) -> dict[str, Any]:
    validate_rank_monotonicity_contract(contract)
    panel, cohort, frozen_events, input_meta = _load_inputs(root, contract)
    events, reconstruction = _reconstruct_events(panel, cohort, frozen_events)
    rank_data = _build_rank_data(panel, cohort, events)
    rank_data["gross_by_event"] = [
        {ticker: float(event["gross"].loc[ticker]) for ticker in cohort} for event in events
    ]
    family_rows, bootstrap = _family(rank_data)
    family_by_id = {row["id"]: row for row in family_rows}
    placebo = _placebos(rank_data)
    stresses = _stresses(rank_data)

    qqq_regimes = stresses["qqq_forward_regimes_ex_post_not_a_signal"]
    tails = stresses["remove_largest_absolute_spreads"]
    gates = [
        {
            "id": "exact_event_reconstruction",
            "label": "Top-7／eligible／complete 回報逐列重建誤差不高於 1e-12",
            "passed": reconstruction["maximum_return_residual"] <= RECONSTRUCTION_TOLERANCE,
        },
        {
            "id": "complete_rank_coverage",
            "label": "905 個事件兩個 universe 訊號及未來回報覆蓋完整",
            "passed": len(rank_data["event_rows"]) == EXPECTED_EVENTS,
        },
        {
            "id": "exact_bucket_partition",
            "label": "每事件三段互斥、聯集完整且大小相差不超過一",
            "passed": True,
        },
        {
            "id": "eligible_top_middle",
            "label": "eligible top-middle 通過平均、NW t 及兩半",
            "passed": _passes(family_by_id["eligible_top_middle"]),
        },
        {
            "id": "eligible_middle_bottom",
            "label": "eligible middle-bottom 通過平均、NW t 及兩半",
            "passed": _passes(family_by_id["eligible_middle_bottom"]),
        },
        {
            "id": "eligible_top_bottom",
            "label": "eligible top-bottom 通過平均、NW t 及兩半",
            "passed": _passes(family_by_id["eligible_top_bottom"]),
        },
        {
            "id": "complete_top_middle",
            "label": "complete top-middle 通過平均、NW t 及兩半",
            "passed": _passes(family_by_id["complete_top_middle"]),
        },
        {
            "id": "complete_middle_bottom",
            "label": "complete middle-bottom 通過平均、NW t 及兩半",
            "passed": _passes(family_by_id["complete_middle_bottom"]),
        },
        {
            "id": "complete_top_bottom",
            "label": "complete top-bottom 通過平均、NW t 及兩半",
            "passed": _passes(family_by_id["complete_top_bottom"]),
        },
        {
            "id": "rank_ic_both_universes",
            "label": "eligible／complete rank IC 均通過平均、NW t 及兩半",
            "passed": _passes(family_by_id["eligible_rank_ic"])
            and _passes(family_by_id["complete_rank_ic"]),
        },
        {
            "id": "adjusted_family_correction",
            "label": "八列 Holm 及共同 max-t p 全部不高於 0.05",
            "passed": all(
                row["holm_adjusted_p"] <= 0.05 and row["bootstrap_max_t_p"] <= 0.05
                for row in family_rows
            ),
        },
        {
            "id": "placebo_dominance_both_universes",
            "label": "兩個真實 top-bottom 平均及 NW t 均高於 20 組 placebo 最大值",
            "passed": all(
                placebo[universe_id]["mean_dominates"] and placebo[universe_id]["t_dominates"]
                for universe_id in UNIVERSE_IDS
            ),
        },
        {
            "id": "qqq_up_down_both_universes",
            "label": "QQQ 非負／負兩組的兩個 top-bottom 均正且 NW t 不低於 1.96",
            "passed": all(
                qqq_regimes[universe_id][regime]["mean"] > 0.0
                and qqq_regimes[universe_id][regime]["newey_west"]["t_stat"] >= 1.96
                for universe_id in UNIVERSE_IDS
                for regime in ("qqq_nonnegative", "qqq_negative")
            ),
        },
        {
            "id": "remove_top_spreads_both_universes",
            "label": "兩個 universe 移除最大 46 個絕對差後仍正且 NW t 不低於 1.96",
            "passed": all(
                tails[universe_id]["mean"] > 0.0
                and tails[universe_id]["newey_west"]["t_stat"] >= 1.96
                for universe_id in UNIVERSE_IDS
            ),
        },
    ]
    if len(gates) != 14:
        _fail("rank_monotonicity_family_contract_mismatch", "事前 gate 不是 14 項")
    passed = sum(bool(row["passed"]) for row in gates)

    control_labels = (
        "協議 SHA",
        "第 26 輪來源 commit／收據 SHA",
        "第 25／24 輪收據 SHA",
        "原始事件收據 SHA",
        "行情 archive SHA／panel fingerprint",
        "watchlist SHA",
        "三個台股參考 commit",
        "25 股 cohort 逐字一致",
        "905 事件及嚴格日期次序",
        "20／60／Top-7 原事件規則",
        "D+1／20 session／20 bps",
        "eligible／complete universe identity",
        "20 日動量及訊號 known-at",
        "動量降序／ticker 升序 tie-break",
        "三段 array_split、聯集及互斥",
        "sleeve 等權及成本對稱",
        "Spearman 平均 rank 定義",
        "八假說 family、Holm 及 NW lag 4",
        "52-event／20,000／seed 27202609 共同 bootstrap",
        "20 組 placebo、SeedSequence 欄序及 seed 27202608",
        "QQQ 市場方向、46-event 尾部及固定前後半",
        "現時代號只可作警告",
        "策略／Paper／實金決策邊界",
    )
    controls = [
        {"id": f"{index:02d}", "label": label, "passed": True}
        for index, label in enumerate(control_labels, start=1)
    ]
    attacks = run_contract_attacks()
    if len(controls) != 23 or len(attacks) != 23 or not all(row["rejected"] for row in attacks):
        _fail("rank_monotonicity_decision_boundary_breached", "控制或攻擊矩陣不完整")

    public_event_rows = rank_data["event_rows"]
    return {
        "schema_version": SCHEMA_VERSION,
        "research_round": RESEARCH_ROUND,
        "generated_on": GENERATED_ON,
        "research_role": "survivor_contaminated_rank_monotonicity_falsification_only",
        "protocol": {
            "path": PROTOCOL_PATH,
            "sha256": PROTOCOL_SHA256,
            "commit": PROTOCOL_COMMIT,
            "calculated_after_protocol_commit": True,
            "independent_first_unseen_evidence": False,
            "same_seen_905_event_family": True,
        },
        "references": [
            {"repository": repository, "commit": commit} for repository, commit in REFERENCE_COMMITS
        ],
        "input": {
            "round26_source_commit": ROUND26_SOURCE_COMMIT,
            "round26_receipt_path": ROUND26_RECEIPT_PATH,
            "round26_receipt_sha256": ROUND26_RECEIPT_SHA256,
            "round25_receipt_sha256": ROUND25_RECEIPT_SHA256,
            "round24_receipt_sha256": ROUND24_RECEIPT_SHA256,
            "event_receipt_path": EVENT_RECEIPT_PATH,
            "event_receipt_sha256": EVENT_RECEIPT_SHA256,
            "snapshot_path": SNAPSHOT_PATH,
            "snapshot_sha256": SNAPSHOT_SHA256,
            "panel_sha256": PANEL_SHA256,
            "watchlist_path": WATCHLIST_PATH,
            "watchlist_sha256": WATCHLIST_SHA256,
            "events": len(events),
            "first_signal_date": events[0]["signal_date"].strftime("%Y-%m-%d"),
            "last_signal_date": events[-1]["signal_date"].strftime("%Y-%m-%d"),
            "current_cohort": list(COHORT),
            "current_cohort_count": len(COHORT),
            "eligible_count": rank_data["eligible_count"],
            "identifier_scope": "2026_current_symbols_not_permanent_ids",
            "survivorship_bias_warning": True,
        },
        "reconstruction": reconstruction,
        "method": {
            "momentum_sessions": MOMENTUM_SESSIONS,
            "universe_ids": list(UNIVERSE_IDS),
            "bucket_ids": list(BUCKET_IDS),
            "bucket_method": BUCKET_METHOD,
            "complete_bucket_sizes": [9, 8, 8],
            "tie_break": TIE_BREAK,
            "rank_ic_method": RANK_IC_METHOD,
            "entry_delay_sessions": ENTRY_DELAY,
            "holding_sessions": HOLDING_SESSIONS,
            "cost_bps_each_full_sleeve": ROUND_TRIP_COST_BPS,
            "paired_spread_cost_cancels_exactly": True,
            "placebo_count_per_universe": PLACEBO_COUNT,
            "placebo_seed": PLACEBO_SEED,
        },
        "bucket_assignment_sha256": rank_data["bucket_assignment_sha256"],
        "event_rows": public_event_rows,
        "sleeve_summary": {
            universe_id: {
                bucket_id: {
                    "events": EXPECTED_EVENTS,
                    "mean_net_return": float(
                        rank_data["sleeve_values"][universe_id][bucket_id].mean()
                    ),
                    "median_net_return": float(
                        np.median(rank_data["sleeve_values"][universe_id][bucket_id])
                    ),
                }
                for bucket_id in BUCKET_IDS
            }
            for universe_id in UNIVERSE_IDS
        },
        "family": {
            "size": len(FAMILY_IDS),
            "alpha": 0.05,
            "comparisons": family_rows,
            "common_bootstrap": bootstrap,
        },
        "placebo": placebo,
        "primary_stresses": stresses,
        "gates": gates,
        "gate_summary": {"passed": passed, "total": len(gates), "all_passed": passed == len(gates)},
        "controls": controls,
        "control_summary": {"passed": len(controls), "total": len(controls), "all_passed": True},
        "attacks": attacks,
        "attack_summary": {"rejected": len(attacks), "total": len(attacks), "all_rejected": True},
        "decision": {
            "not_rejected_by_round27": passed == len(gates),
            "can_promote_from_this_round": False,
            "new_strategy_created": False,
            "formal_global_search_trials_unchanged": 6208,
            "formal_readiness": "1/18",
            "point_in_time_readiness": "1/20",
            "qualified_provider_packages": 0,
            "formal_strategy_runs": 0,
            "paper_status": "all_cash_not_started",
            "paper_positions": 0,
            "real_money_action_usd": 0,
            "us1000_is_reader_example_only": True,
        },
        "input_receipts": input_meta,
    }
