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

from .data import panel_fingerprint
from .metrics import newey_west_mean_test
from .rank_monotonicity_placebo import (
    COHORT,
    EVENT_RECEIPT_PATH,
    EVENT_RECEIPT_SHA256,
    FIRST_HALF_END,
    FIRST_SIGNAL_DATE,
    HOLDING_SESSIONS,
    LAST_SIGNAL_DATE,
    PANEL_SHA256,
    REFERENCE_COMMITS,
    ROUND24_RECEIPT_PATH,
    ROUND24_RECEIPT_SHA256,
    ROUND25_RECEIPT_PATH,
    ROUND25_RECEIPT_SHA256,
    ROUND26_RECEIPT_PATH,
    ROUND26_RECEIPT_SHA256,
    ROUND_TRIP_COST_BPS,
    SECOND_HALF_START,
    SNAPSHOT_PATH,
    SNAPSHOT_SHA256,
    WATCHLIST_PATH,
    WATCHLIST_SHA256,
    _build_rank_data,
    _reconstruct_events,
)
from .rank_monotonicity_placebo import (
    FROZEN_CONTRACT as ROUND27_CONTRACT,
)
from .rank_monotonicity_placebo import (
    _load_inputs as _load_round27_inputs,
)

SCHEMA_VERSION = 1
RESEARCH_ROUND = 28
GENERATED_ON = "2026-08-04"
PROTOCOL_PATH = "docs/SHORT_TERM_REVERSAL_VOLATILITY_ATTRIBUTION_PROTOCOL.md"
PROTOCOL_SHA256 = "3316ca8acdd46a80d591ca6d7a810d8f820ce1073052eb35d5e8aea24fc724c0"
PROTOCOL_COMMIT = "2ebb9737612cd9485ee338acf1aa8a98e0a60c07"

ROUND27_SOURCE_COMMIT = "799120497084f59666e22cfcbd709cd8657f3223"
ROUND27_RECEIPT_PATH = "artifacts/short_term_rank_monotonicity_placebo_validation.json"
ROUND27_RECEIPT_SHA256 = "3d362ed82ab8ed732d53344a1a8d787fe48374e042bdf8f13c54a0f0cea96448"
ROUND27_BUCKET_ASSIGNMENT_SHA256 = (
    "0f1512ccc893f554028b77de85af146e53333e1badd528fb00089878d49e8ffd"
)

EXPECTED_EVENTS = 905
UNIVERSE_IDS = ("eligible", "complete")
BUCKET_IDS = ("top", "middle", "bottom")
PRIOR_RETURN_SESSIONS = 5
VOLATILITY_SESSIONS = 20
VOLATILITY_DDOF = 1
CONTROL_RANK_METHOD = "average_rank_scaled_minus_half"
REGRESSION_COLUMNS = ("intercept", "prior_5d_rank", "volatility_20d_rank")
REGRESSION_METHOD = "numpy_lstsq_rcond_none"
MAX_CONDITION_NUMBER = 1e8
RECONSTRUCTION_TOLERANCE = 1e-12
SIGN_CLASSIFICATION_TOLERANCE = 1e-12
FEATURE_RECEIPT_DECIMAL_PLACES = 8
HAC_LAG = 4
FAMILY_IDS = (
    "eligible_raw_top_middle",
    "eligible_raw_bottom_middle",
    "complete_raw_top_middle",
    "complete_raw_bottom_middle",
    "eligible_residual_top_middle",
    "eligible_residual_bottom_middle",
    "complete_residual_top_middle",
    "complete_residual_bottom_middle",
)
BOOTSTRAP_BLOCK_LENGTH = 52
BOOTSTRAP_PATHS = 20_000
BOOTSTRAP_SEED = 28_202_610
TAIL_REMOVAL_EVENTS = 46
RESIDUAL_RETENTION_FRACTION = 0.75


class ReversalVolatilityError(ValueError):
    """Fail-closed Round 28 error with a stable semantic code."""

    def __init__(self, code: str, detail: str):
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}")


def _fail(code: str, detail: str) -> None:
    raise ReversalVolatilityError(code, detail)


@dataclass(frozen=True)
class FrozenReversalVolatilityContract:
    protocol_sha256: str = PROTOCOL_SHA256
    round27_source_commit: str = ROUND27_SOURCE_COMMIT
    round27_receipt_sha256: str = ROUND27_RECEIPT_SHA256
    prior_receipt_sha256s: tuple[str, ...] = (
        ROUND26_RECEIPT_SHA256,
        ROUND25_RECEIPT_SHA256,
        ROUND24_RECEIPT_SHA256,
    )
    event_receipt_sha256: str = EVENT_RECEIPT_SHA256
    snapshot_sha256: str = SNAPSHOT_SHA256
    panel_sha256: str = PANEL_SHA256
    watchlist_sha256: str = WATCHLIST_SHA256
    reference_commits: tuple[tuple[str, str], ...] = REFERENCE_COMMITS
    cohort: tuple[str, ...] = COHORT
    expected_events: int = EXPECTED_EVENTS
    first_signal_date: str = FIRST_SIGNAL_DATE
    last_signal_date: str = LAST_SIGNAL_DATE
    prior_return_sessions: int = PRIOR_RETURN_SESSIONS
    volatility_sessions: int = VOLATILITY_SESSIONS
    volatility_ddof: int = VOLATILITY_DDOF
    control_rank_method: str = CONTROL_RANK_METHOD
    regression_columns: tuple[str, ...] = REGRESSION_COLUMNS
    regression_method: str = REGRESSION_METHOD
    max_condition_number: float = MAX_CONDITION_NUMBER
    universe_ids: tuple[str, ...] = UNIVERSE_IDS
    round27_bucket_assignment_sha256: str = ROUND27_BUCKET_ASSIGNMENT_SHA256
    holding_sessions: int = HOLDING_SESSIONS
    round_trip_cost_bps: int = ROUND_TRIP_COST_BPS
    family_ids: tuple[str, ...] = FAMILY_IDS
    hac_lag: int = HAC_LAG
    bootstrap_block_length: int = BOOTSTRAP_BLOCK_LENGTH
    bootstrap_paths: int = BOOTSTRAP_PATHS
    bootstrap_seed: int = BOOTSTRAP_SEED
    qqq_regime_sessions: int = 20
    tail_removal_events: int = TAIL_REMOVAL_EVENTS
    current_symbols_warning_only: bool = True
    paper_authorized: bool = False
    real_money_authorized: bool = False
    formal_strategy_runs: int = 0


FROZEN_CONTRACT = FrozenReversalVolatilityContract()


def validate_reversal_volatility_contract(contract: FrozenReversalVolatilityContract) -> None:
    checks: tuple[tuple[bool, str, str], ...] = (
        (
            contract.protocol_sha256 == PROTOCOL_SHA256,
            "reversal_volatility_protocol_mismatch",
            "協議 SHA 漂移",
        ),
        (
            contract.round27_source_commit == ROUND27_SOURCE_COMMIT,
            "reversal_volatility_round27_source_mismatch",
            "第 27 輪來源 commit 漂移",
        ),
        (
            contract.round27_receipt_sha256 == ROUND27_RECEIPT_SHA256,
            "reversal_volatility_round27_receipt_mismatch",
            "第 27 輪收據 SHA 漂移",
        ),
        (
            contract.prior_receipt_sha256s
            == (ROUND26_RECEIPT_SHA256, ROUND25_RECEIPT_SHA256, ROUND24_RECEIPT_SHA256),
            "reversal_volatility_prior_receipts_mismatch",
            "第 24–26 輪收據 SHA 漂移",
        ),
        (
            contract.event_receipt_sha256 == EVENT_RECEIPT_SHA256,
            "reversal_volatility_event_receipt_mismatch",
            "原始事件收據 SHA 漂移",
        ),
        (
            contract.snapshot_sha256 == SNAPSHOT_SHA256 and contract.panel_sha256 == PANEL_SHA256,
            "reversal_volatility_market_data_mismatch",
            "行情 archive 或 panel fingerprint 漂移",
        ),
        (
            contract.watchlist_sha256 == WATCHLIST_SHA256,
            "reversal_volatility_watchlist_mismatch",
            "watchlist SHA 漂移",
        ),
        (
            contract.reference_commits == REFERENCE_COMMITS,
            "reversal_volatility_reference_commits_mismatch",
            "台股參考 commit 漂移",
        ),
        (
            contract.cohort == COHORT,
            "reversal_volatility_cohort_mismatch",
            "25 股 cohort 漂移",
        ),
        (
            contract.expected_events == EXPECTED_EVENTS
            and contract.first_signal_date == FIRST_SIGNAL_DATE
            and contract.last_signal_date == LAST_SIGNAL_DATE,
            "reversal_volatility_event_order_mismatch",
            "事件數或日期邊界漂移",
        ),
        (
            contract.prior_return_sessions == PRIOR_RETURN_SESSIONS,
            "reversal_volatility_prior_return_window_mismatch",
            "短期反轉窗口漂移",
        ),
        (
            contract.volatility_sessions == VOLATILITY_SESSIONS
            and contract.volatility_ddof == VOLATILITY_DDOF,
            "reversal_volatility_volatility_window_mismatch",
            "已實現波幅窗口或 ddof 漂移",
        ),
        (
            contract.control_rank_method == CONTROL_RANK_METHOD,
            "reversal_volatility_rank_transform_mismatch",
            "控制 rank 轉換漂移",
        ),
        (
            contract.regression_columns == REGRESSION_COLUMNS
            and contract.regression_method == REGRESSION_METHOD
            and contract.max_condition_number == MAX_CONDITION_NUMBER,
            "reversal_volatility_regression_contract_mismatch",
            "OLS 欄序、方法或 condition 上限漂移",
        ),
        (
            contract.universe_ids == UNIVERSE_IDS,
            "reversal_volatility_universe_mismatch",
            "universe identity 漂移",
        ),
        (
            contract.round27_bucket_assignment_sha256 == ROUND27_BUCKET_ASSIGNMENT_SHA256,
            "reversal_volatility_bucket_receipt_mismatch",
            "第 27 輪 bucket receipt 漂移",
        ),
        (
            contract.holding_sessions == HOLDING_SESSIONS
            and contract.round_trip_cost_bps == ROUND_TRIP_COST_BPS,
            "reversal_volatility_execution_rule_mismatch",
            "持有時鐘或成本漂移",
        ),
        (
            contract.family_ids == FAMILY_IDS and contract.hac_lag == HAC_LAG,
            "reversal_volatility_family_contract_mismatch",
            "八假說 family 或 NW lag 漂移",
        ),
        (
            contract.bootstrap_block_length == BOOTSTRAP_BLOCK_LENGTH
            and contract.bootstrap_paths == BOOTSTRAP_PATHS
            and contract.bootstrap_seed == BOOTSTRAP_SEED,
            "reversal_volatility_bootstrap_contract_mismatch",
            "共同 bootstrap 漂移",
        ),
        (
            contract.qqq_regime_sessions == 20,
            "reversal_volatility_regime_contract_mismatch",
            "QQQ known-at regime 漂移",
        ),
        (
            contract.tail_removal_events == TAIL_REMOVAL_EVENTS,
            "reversal_volatility_tail_contract_mismatch",
            "尾部移除列數漂移",
        ),
        (
            contract.current_symbols_warning_only,
            "reversal_volatility_identity_scope_breached",
            "現時代號被越權升格",
        ),
        (
            not contract.paper_authorized
            and not contract.real_money_authorized
            and contract.formal_strategy_runs == 0,
            "reversal_volatility_decision_boundary_breached",
            "策略／Paper／實金決策邊界被越權",
        ),
    )
    for passed, code, detail in checks:
        if not passed:
            _fail(code, detail)


def _contract_attacks() -> list[
    tuple[
        str,
        str,
        str,
        Callable[[FrozenReversalVolatilityContract], FrozenReversalVolatilityContract],
    ]
]:
    return [
        (
            "01",
            "協議 SHA 漂移",
            "reversal_volatility_protocol_mismatch",
            lambda c: replace(c, protocol_sha256="0" * 64),
        ),
        (
            "02",
            "第 27 輪來源 commit 漂移",
            "reversal_volatility_round27_source_mismatch",
            lambda c: replace(c, round27_source_commit="0" * 40),
        ),
        (
            "03",
            "第 27 輪收據 SHA 漂移",
            "reversal_volatility_round27_receipt_mismatch",
            lambda c: replace(c, round27_receipt_sha256="0" * 64),
        ),
        (
            "04",
            "第 26 輪收據 SHA 漂移",
            "reversal_volatility_prior_receipts_mismatch",
            lambda c: replace(c, prior_receipt_sha256s=("0" * 64,)),
        ),
        (
            "05",
            "原始事件收據 SHA 漂移",
            "reversal_volatility_event_receipt_mismatch",
            lambda c: replace(c, event_receipt_sha256="0" * 64),
        ),
        (
            "06",
            "行情 archive SHA 漂移",
            "reversal_volatility_market_data_mismatch",
            lambda c: replace(c, snapshot_sha256="0" * 64),
        ),
        (
            "07",
            "watchlist SHA 漂移",
            "reversal_volatility_watchlist_mismatch",
            lambda c: replace(c, watchlist_sha256="0" * 64),
        ),
        (
            "08",
            "台股參考 commit 漂移",
            "reversal_volatility_reference_commits_mismatch",
            lambda c: replace(c, reference_commits=REFERENCE_COMMITS[:2]),
        ),
        (
            "09",
            "25 股 cohort 漂移",
            "reversal_volatility_cohort_mismatch",
            lambda c: replace(c, cohort=COHORT[:-1]),
        ),
        (
            "10",
            "事件數改 904",
            "reversal_volatility_event_order_mismatch",
            lambda c: replace(c, expected_events=904),
        ),
        (
            "11",
            "5 日窗口改 2 日",
            "reversal_volatility_prior_return_window_mismatch",
            lambda c: replace(c, prior_return_sessions=2),
        ),
        (
            "12",
            "波幅改 60 日",
            "reversal_volatility_volatility_window_mismatch",
            lambda c: replace(c, volatility_sessions=60),
        ),
        (
            "13",
            "rank 改 ticker tie-break",
            "reversal_volatility_rank_transform_mismatch",
            lambda c: replace(c, control_rank_method="ordinal_rank"),
        ),
        (
            "14",
            "OLS condition 上限漂移",
            "reversal_volatility_regression_contract_mismatch",
            lambda c: replace(c, max_condition_number=1e6),
        ),
        (
            "15",
            "刪除完整股池 universe",
            "reversal_volatility_universe_mismatch",
            lambda c: replace(c, universe_ids=("eligible",)),
        ),
        (
            "16",
            "bucket receipt SHA 漂移",
            "reversal_volatility_bucket_receipt_mismatch",
            lambda c: replace(c, round27_bucket_assignment_sha256="0" * 64),
        ),
        (
            "17",
            "成本改 10 bps",
            "reversal_volatility_execution_rule_mismatch",
            lambda c: replace(c, round_trip_cost_bps=10),
        ),
        (
            "18",
            "family 刪除 residual",
            "reversal_volatility_family_contract_mismatch",
            lambda c: replace(c, family_ids=FAMILY_IDS[:4]),
        ),
        (
            "19",
            "NW lag 改 1",
            "reversal_volatility_family_contract_mismatch",
            lambda c: replace(c, hac_lag=1),
        ),
        (
            "20",
            "bootstrap seed 漂移",
            "reversal_volatility_bootstrap_contract_mismatch",
            lambda c: replace(c, bootstrap_seed=28_202_611),
        ),
        (
            "21",
            "QQQ regime 改 60 日",
            "reversal_volatility_regime_contract_mismatch",
            lambda c: replace(c, qqq_regime_sessions=60),
        ),
        (
            "22",
            "尾部改 45 列",
            "reversal_volatility_tail_contract_mismatch",
            lambda c: replace(c, tail_removal_events=45),
        ),
        (
            "23",
            "越權啟動 Paper",
            "reversal_volatility_decision_boundary_breached",
            lambda c: replace(c, paper_authorized=True),
        ),
    ]


def run_contract_attacks() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for attack_id, label, expected_code, mutate in _contract_attacks():
        observed: str | None = None
        try:
            validate_reversal_volatility_contract(mutate(FROZEN_CONTRACT))
        except ReversalVolatilityError as exc:
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


def _scaled_average_rank(values: pd.Series) -> pd.Series:
    array = values.to_numpy(dtype=float)
    if not np.isfinite(array).all() or np.ptp(array) <= 0.0:
        _fail("reversal_volatility_coverage_mismatch", "控制特徵缺值、非有限或零變異")
    rank = values.rank(method="average")
    return (rank - 1.0) / (len(values) - 1.0) - 0.5


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
        "first": {"events": int(first.sum()), "mean": float(values[first].mean())},
        "second": {"events": int(second.sum()), "mean": float(values[second].mean())},
    }


def _normal_two_sided_p(t_stat: float) -> float:
    return float(math.erfc(abs(t_stat) / math.sqrt(2.0)))


def _comparison(values: np.ndarray, dates: pd.Series, require_full: bool = True) -> dict[str, Any]:
    if (require_full and len(values) != EXPECTED_EVENTS) or len(values) < 2:
        _fail("reversal_volatility_family_contract_mismatch", "比較列事件數不符")
    if not np.isfinite(values).all():
        _fail("reversal_volatility_family_contract_mismatch", "比較列含非有限值")
    nw = _newey_west(values)
    row: dict[str, Any] = {
        "events": len(values),
        "mean": float(values.mean()),
        "median": float(np.median(values)),
        "positive_fraction": float((values > SIGN_CLASSIFICATION_TOLERANCE).mean()),
        "newey_west": nw,
        "raw_normal_p": _normal_two_sided_p(float(nw["t_stat"])),
    }
    if require_full:
        row["fixed_halves"] = _fixed_halves(values, dates)
    else:
        row["first_signal_date"] = pd.Timestamp(dates.iloc[0]).strftime("%Y-%m-%d")
        row["last_signal_date"] = pd.Timestamp(dates.iloc[-1]).strftime("%Y-%m-%d")
    return row


def _holm_adjust(rows: list[dict[str, Any]]) -> dict[str, float]:
    ordered = sorted(rows, key=lambda row: (row["raw_normal_p"], row["id"]))
    adjusted: dict[str, float] = {}
    running = 0.0
    total = len(ordered)
    for rank, row in enumerate(ordered):
        running = max(running, min(1.0, (total - rank) * row["raw_normal_p"]))
        adjusted[row["id"]] = running
    return adjusted


def _common_bootstrap(
    matrix: np.ndarray, observed_t: np.ndarray, standard_errors: np.ndarray
) -> dict[str, Any]:
    centered = matrix - matrix.mean(axis=0, keepdims=True)
    if not np.allclose(centered.mean(axis=0), 0.0, atol=1e-15):
        _fail("reversal_volatility_bootstrap_contract_mismatch", "bootstrap 去中心化失敗")
    if (standard_errors <= 0.0).any():
        _fail("reversal_volatility_bootstrap_contract_mismatch", "NW 標準誤非正")
    rows = len(matrix)
    blocks_per_path = math.ceil(rows / BOOTSTRAP_BLOCK_LENGTH)
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    starts = rng.integers(0, rows, size=(BOOTSTRAP_PATHS, blocks_per_path), dtype=np.int64)
    offsets = np.arange(BOOTSTRAP_BLOCK_LENGTH, dtype=np.int64)
    max_abs = np.empty(BOOTSTRAP_PATHS, dtype=float)
    for start in range(0, BOOTSTRAP_PATHS, 250):
        stop = min(BOOTSTRAP_PATHS, start + 250)
        indices = (starts[start:stop, :, None] + offsets[None, None, :]) % rows
        indices = indices.reshape(stop - start, -1)[:, :rows]
        means = centered[indices].mean(axis=1)
        max_abs[start:stop] = np.abs(means / standard_errors).max(axis=1)
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


def _passes_positive(row: dict[str, Any]) -> bool:
    return bool(
        row["mean"] > 0.0
        and row["newey_west"]["t_stat"] >= 1.96
        and row["fixed_halves"]["first"]["mean"] > 0.0
        and row["fixed_halves"]["second"]["mean"] > 0.0
    )


def _passes_negative(row: dict[str, Any]) -> bool:
    return bool(
        row["mean"] < 0.0
        and row["newey_west"]["t_stat"] <= -1.96
        and row["fixed_halves"]["first"]["mean"] < 0.0
        and row["fixed_halves"]["second"]["mean"] < 0.0
    )


def _load_and_validate_inputs(
    root: Path, contract: FrozenReversalVolatilityContract
) -> tuple[Any, list[str], list[dict[str, Any]], dict[str, Any]]:
    paths = {
        "protocol": root / PROTOCOL_PATH,
        "round27_receipt": root / ROUND27_RECEIPT_PATH,
        "round26_receipt": root / ROUND26_RECEIPT_PATH,
        "round25_receipt": root / ROUND25_RECEIPT_PATH,
        "round24_receipt": root / ROUND24_RECEIPT_PATH,
        "event_receipt": root / EVENT_RECEIPT_PATH,
        "snapshot": root / SNAPSHOT_PATH,
        "watchlist": root / WATCHLIST_PATH,
    }
    expected = {
        "protocol": contract.protocol_sha256,
        "round27_receipt": contract.round27_receipt_sha256,
        "round26_receipt": contract.prior_receipt_sha256s[0],
        "round25_receipt": contract.prior_receipt_sha256s[1],
        "round24_receipt": contract.prior_receipt_sha256s[2],
        "event_receipt": contract.event_receipt_sha256,
        "snapshot": contract.snapshot_sha256,
        "watchlist": contract.watchlist_sha256,
    }
    observed = {key: _sha256_file(path) for key, path in paths.items()}
    for key, expected_hash in expected.items():
        if observed[key] != expected_hash:
            _fail("reversal_volatility_input_receipt_mismatch", f"{key} SHA-256 漂移")

    panel, cohort, frozen_events, _ = _load_round27_inputs(root, ROUND27_CONTRACT)
    if panel_fingerprint(panel) != contract.panel_sha256:
        _fail("reversal_volatility_market_data_mismatch", "panel fingerprint 漂移")
    if tuple(sorted(cohort)) != contract.cohort:
        _fail("reversal_volatility_cohort_mismatch", "25 股 cohort 未逐字對齊")
    round27 = json.loads(paths["round27_receipt"].read_text(encoding="utf-8"))
    if (
        round27.get("research_round") != 27
        or round27.get("bucket_assignment_sha256") != contract.round27_bucket_assignment_sha256
        or round27.get("input", {}).get("events") != EXPECTED_EVENTS
    ):
        _fail("reversal_volatility_round27_receipt_mismatch", "第 27 輪收據身份或 bucket 不符")
    return (
        panel,
        cohort,
        frozen_events,
        {
            "round27": round27,
            "paths": {key: str(path.relative_to(root)) for key, path in paths.items()},
            "hashes": observed,
        },
    )


def _event_feature_hash(rows: list[dict[str, Any]]) -> str:
    stable_rows = [
        {
            key: (
                0.0
                if isinstance(value, float)
                and round(value, FEATURE_RECEIPT_DECIMAL_PLACES) == 0.0
                else round(value, FEATURE_RECEIPT_DECIMAL_PLACES)
                if isinstance(value, float)
                else value
            )
            for key, value in row.items()
        }
        for row in rows
    ]
    return hashlib.sha256(
        json.dumps(stable_rows, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _build_attribution(
    panel: Any,
    cohort: list[str],
    events: list[dict[str, Any]],
    round27: dict[str, Any],
) -> dict[str, Any]:
    close = panel.close[cohort]
    prior5 = close.pct_change(PRIOR_RETURN_SESSIONS, fill_method=None)
    daily = close.pct_change(fill_method=None)
    volatility20 = daily.rolling(VOLATILITY_SESSIONS, min_periods=VOLATILITY_SESSIONS).std(
        ddof=VOLATILITY_DDOF
    )
    qqq_trailing20 = panel.close["QQQ"].pct_change(20, fill_method=None)
    dates = pd.Series([event["signal_date"] for event in events], name="signal_date")
    family_values = {family_id: np.empty(EXPECTED_EVENTS, dtype=float) for family_id in FAMILY_IDS}
    diagnostic_values = {
        universe_id: {
            key: np.empty(EXPECTED_EVENTS, dtype=float)
            for key in (
                "predicted_bottom_middle",
                "prior5_rank_gap_bottom_middle",
                "volatility_rank_gap_bottom_middle",
                "prior5_contribution_bottom_middle",
                "volatility_contribution_bottom_middle",
                "beta_prior5",
                "beta_volatility",
                "residual_top_middle_retention",
            )
        }
        for universe_id in UNIVERSE_IDS
    }
    event_rows: list[dict[str, Any]] = []
    feature_hash_rows: list[dict[str, Any]] = []
    maximum_raw_round27_residual = 0.0
    maximum_identity_residual = 0.0
    maximum_residual_mean = 0.0
    maximum_condition = 0.0
    minimum_rank = 3

    if len(events) != EXPECTED_EVENTS or len(round27["event_rows"]) != EXPECTED_EVENTS:
        _fail("reversal_volatility_event_order_mismatch", "事件或第 27 輪 receipt 不是 905 列")

    for event_index, (event, prior_row) in enumerate(
        zip(events, round27["event_rows"], strict=True)
    ):
        signal_date = event["signal_date"]
        signal_string = signal_date.strftime("%Y-%m-%d")
        if prior_row["signal_date"] != signal_string or prior_row["event_index"] != event_index:
            _fail("reversal_volatility_event_order_mismatch", "第 27 輪事件次序漂移")
        qqq_value = float(qqq_trailing20.loc[signal_date])
        if not math.isfinite(qqq_value):
            _fail("reversal_volatility_coverage_mismatch", "QQQ 訊號日 20 日回報缺失")
        receipt: dict[str, Any] = {
            "event_index": event_index,
            "signal_date": signal_string,
            "entry_date": event["entry_date"].strftime("%Y-%m-%d"),
            "exit_date": event["exit_date"].strftime("%Y-%m-%d"),
            "qqq_trailing_20d": qqq_value,
            "universes": {},
        }
        for universe_id in UNIVERSE_IDS:
            prior_universe = prior_row["universes"][universe_id]
            symbols = list(prior_universe["ranked"])
            buckets = prior_universe["buckets"]
            if sorted(symbols) != sorted(
                event["eligible"] if universe_id == "eligible" else cohort
            ):
                _fail("reversal_volatility_universe_mismatch", "universe 股票集合漂移")
            feature5 = prior5.loc[signal_date, symbols]
            feature_vol = volatility20.loc[signal_date, symbols]
            future = event["gross"].loc[symbols]
            if not all(
                np.isfinite(series.to_numpy(dtype=float)).all()
                for series in (feature5, feature_vol, future)
            ):
                _fail("reversal_volatility_coverage_mismatch", "控制特徵或未來回報不完整")
            rank5 = _scaled_average_rank(feature5)
            rank_vol = _scaled_average_rank(feature_vol)
            design = np.column_stack(
                [np.ones(len(symbols), dtype=float), rank5.to_numpy(), rank_vol.to_numpy()]
            )
            matrix_rank = int(np.linalg.matrix_rank(design))
            condition = float(np.linalg.cond(design, p=2))
            minimum_rank = min(minimum_rank, matrix_rank)
            maximum_condition = max(maximum_condition, condition)
            if matrix_rank != 3 or not math.isfinite(condition) or condition > MAX_CONDITION_NUMBER:
                _fail(
                    "reversal_volatility_regression_contract_mismatch", "OLS rank 或 condition 失敗"
                )
            y = future.to_numpy(dtype=float)
            beta, _, _, _ = np.linalg.lstsq(design, y, rcond=None)
            predicted_array = design @ beta
            residual_array = y - predicted_array
            predicted = pd.Series(predicted_array, index=symbols)
            residual = pd.Series(residual_array, index=symbols)
            residual_mean = abs(float(residual.mean()))
            maximum_residual_mean = max(maximum_residual_mean, residual_mean)

            feature_rows = [
                {
                    "ticker": ticker,
                    "prior_5d_return": float(feature5.loc[ticker]),
                    "realized_volatility_20d": float(feature_vol.loc[ticker]),
                    "prior_5d_rank": float(rank5.loc[ticker]),
                    "volatility_20d_rank": float(rank_vol.loc[ticker]),
                    "future_gross": float(future.loc[ticker]),
                    "predicted": float(predicted.loc[ticker]),
                    "residual": float(residual.loc[ticker]),
                }
                for ticker in symbols
            ]
            feature_hash = _event_feature_hash(feature_rows)
            feature_hash_rows.append(
                {"signal_date": signal_string, "universe": universe_id, "sha256": feature_hash}
            )

            bucket_means: dict[str, Any] = {}
            for bucket_id in BUCKET_IDS:
                bucket_symbols = buckets[bucket_id]
                bucket_means[bucket_id] = {
                    "gross": float(future.loc[bucket_symbols].mean()),
                    "net": float(
                        future.loc[bucket_symbols].mean() - ROUND_TRIP_COST_BPS / 10_000.0
                    ),
                    "predicted": float(predicted.loc[bucket_symbols].mean()),
                    "residual": float(residual.loc[bucket_symbols].mean()),
                    "prior_5d_rank": float(rank5.loc[bucket_symbols].mean()),
                    "volatility_20d_rank": float(rank_vol.loc[bucket_symbols].mean()),
                }

            spreads: dict[str, dict[str, float]] = {
                key: {} for key in ("raw", "predicted", "residual")
            }
            for component, field in (
                ("raw", "gross"),
                ("predicted", "predicted"),
                ("residual", "residual"),
            ):
                spreads[component] = {
                    "top_middle": bucket_means["top"][field] - bucket_means["middle"][field],
                    "bottom_middle": bucket_means["bottom"][field] - bucket_means["middle"][field],
                }
            prior_top_middle = float(prior_universe["spreads"]["top_middle"])
            prior_bottom_middle = -float(prior_universe["spreads"]["middle_bottom"])
            maximum_raw_round27_residual = max(
                maximum_raw_round27_residual,
                abs(spreads["raw"]["top_middle"] - prior_top_middle),
                abs(spreads["raw"]["bottom_middle"] - prior_bottom_middle),
            )
            for spread_id in ("top_middle", "bottom_middle"):
                maximum_identity_residual = max(
                    maximum_identity_residual,
                    abs(
                        spreads["raw"][spread_id]
                        - spreads["predicted"][spread_id]
                        - spreads["residual"][spread_id]
                    ),
                )

            family_values[f"{universe_id}_raw_top_middle"][event_index] = spreads["raw"][
                "top_middle"
            ]
            family_values[f"{universe_id}_raw_bottom_middle"][event_index] = spreads["raw"][
                "bottom_middle"
            ]
            family_values[f"{universe_id}_residual_top_middle"][event_index] = spreads["residual"][
                "top_middle"
            ]
            family_values[f"{universe_id}_residual_bottom_middle"][event_index] = spreads[
                "residual"
            ]["bottom_middle"]

            rank5_gap = (
                bucket_means["bottom"]["prior_5d_rank"] - bucket_means["middle"]["prior_5d_rank"]
            )
            rank_vol_gap = (
                bucket_means["bottom"]["volatility_20d_rank"]
                - bucket_means["middle"]["volatility_20d_rank"]
            )
            contribution5 = float(beta[1] * rank5_gap)
            contribution_vol = float(beta[2] * rank_vol_gap)
            retention = (
                spreads["residual"]["top_middle"] / spreads["raw"]["top_middle"]
                if abs(spreads["raw"]["top_middle"]) > RECONSTRUCTION_TOLERANCE
                else math.nan
            )
            diagnostic_values[universe_id]["predicted_bottom_middle"][event_index] = spreads[
                "predicted"
            ]["bottom_middle"]
            diagnostic_values[universe_id]["prior5_rank_gap_bottom_middle"][event_index] = rank5_gap
            diagnostic_values[universe_id]["volatility_rank_gap_bottom_middle"][event_index] = (
                rank_vol_gap
            )
            diagnostic_values[universe_id]["prior5_contribution_bottom_middle"][event_index] = (
                contribution5
            )
            diagnostic_values[universe_id]["volatility_contribution_bottom_middle"][event_index] = (
                contribution_vol
            )
            diagnostic_values[universe_id]["beta_prior5"][event_index] = float(beta[1])
            diagnostic_values[universe_id]["beta_volatility"][event_index] = float(beta[2])
            diagnostic_values[universe_id]["residual_top_middle_retention"][event_index] = retention

            receipt["universes"][universe_id] = {
                "count": len(symbols),
                "feature_receipt_sha256": feature_hash,
                "regression": {
                    "columns": list(REGRESSION_COLUMNS),
                    "rank": matrix_rank,
                    "condition_number": condition,
                    "beta_intercept": float(beta[0]),
                    "beta_prior_5d_rank": float(beta[1]),
                    "beta_volatility_20d_rank": float(beta[2]),
                    "residual_mean": float(residual.mean()),
                },
                "bucket_means": bucket_means,
                "spreads": spreads,
                "bottom_middle_attribution": {
                    "prior_5d_rank_gap": rank5_gap,
                    "volatility_20d_rank_gap": rank_vol_gap,
                    "prior_5d_contribution": contribution5,
                    "volatility_20d_contribution": contribution_vol,
                    "predicted_total": spreads["predicted"]["bottom_middle"],
                    "residual": spreads["residual"]["bottom_middle"],
                    "raw": spreads["raw"]["bottom_middle"],
                },
            }
        event_rows.append(receipt)

    if any(not np.isfinite(values).all() for values in family_values.values()):
        _fail("reversal_volatility_coverage_mismatch", "family 列含非有限值")
    return {
        "dates": dates,
        "family_values": family_values,
        "diagnostic_values": diagnostic_values,
        "event_rows": event_rows,
        "feature_receipt_sha256": hashlib.sha256(
            json.dumps(feature_hash_rows, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest(),
        "maximum_raw_round27_residual": maximum_raw_round27_residual,
        "maximum_identity_residual": maximum_identity_residual,
        "maximum_residual_mean": maximum_residual_mean,
        "maximum_condition_number": maximum_condition,
        "minimum_design_rank": minimum_rank,
    }


def _family(attribution: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    rows = [
        {
            "id": family_id,
            **_comparison(attribution["family_values"][family_id], attribution["dates"]),
        }
        for family_id in FAMILY_IDS
    ]
    holm = _holm_adjust(rows)
    matrix = np.column_stack([attribution["family_values"][row["id"]] for row in rows])
    observed_t = np.asarray([row["newey_west"]["t_stat"] for row in rows], dtype=float)
    standard_errors = np.asarray([row["newey_west"]["standard_error"] for row in rows], dtype=float)
    bootstrap = _common_bootstrap(matrix, observed_t, standard_errors)
    for index, row in enumerate(rows):
        row["holm_adjusted_p"] = holm[row["id"]]
        row["bootstrap_max_t_p"] = bootstrap["single_step_max_t_p"][index]
    bootstrap["hypothesis_order"] = [row["id"] for row in rows]
    return rows, bootstrap


def _diagnostics(attribution: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for universe_id in UNIVERSE_IDS:
        values = attribution["diagnostic_values"][universe_id]
        result[universe_id] = {
            key: _comparison(array, attribution["dates"])
            for key, array in values.items()
            if key != "residual_top_middle_retention"
        }
        raw_mean = float(attribution["family_values"][f"{universe_id}_raw_top_middle"].mean())
        residual_mean = float(
            attribution["family_values"][f"{universe_id}_residual_top_middle"].mean()
        )
        result[universe_id]["aggregate_top_middle_retention_fraction"] = residual_mean / raw_mean
        finite_retention = values["residual_top_middle_retention"][
            np.isfinite(values["residual_top_middle_retention"])
        ]
        result[universe_id]["event_retention_median"] = float(np.median(finite_retention))
    return result


def _stresses(attribution: dict[str, Any]) -> dict[str, Any]:
    dates = attribution["dates"]
    qqq = np.asarray([row["qqq_trailing_20d"] for row in attribution["event_rows"]], dtype=float)
    regimes: dict[str, Any] = {}
    tails: dict[str, Any] = {}
    for universe_id in UNIVERSE_IDS:
        residual_top_middle = attribution["family_values"][f"{universe_id}_residual_top_middle"]
        raw_bottom_middle = attribution["family_values"][f"{universe_id}_raw_bottom_middle"]
        regimes[universe_id] = {
            "qqq_trailing_nonnegative": _comparison(
                residual_top_middle[qqq >= 0.0], dates[qqq >= 0.0], require_full=False
            ),
            "qqq_trailing_negative": _comparison(
                residual_top_middle[qqq < 0.0], dates[qqq < 0.0], require_full=False
            ),
        }
        removed = np.argsort(-np.abs(raw_bottom_middle), kind="stable")[:TAIL_REMOVAL_EVENTS]
        keep = np.ones(EXPECTED_EVENTS, dtype=bool)
        keep[removed] = False
        tail = _comparison(residual_top_middle[keep], dates[keep], require_full=False)
        tail["removed_events"] = TAIL_REMOVAL_EVENTS
        tail["selection_basis"] = "largest_absolute_raw_bottom_middle"
        tail["removed_absolute_raw_bottom_middle_share"] = float(
            np.abs(raw_bottom_middle[removed]).sum() / np.abs(raw_bottom_middle).sum()
        )
        tail["removed_signal_dates"] = [dates.iloc[index].strftime("%Y-%m-%d") for index in removed]
        tails[universe_id] = tail
    return {"qqq_trailing_20d_known_at_signal": regimes, "remove_largest_raw_bottom_middle": tails}


def run_reversal_volatility_attribution(
    root: Path, contract: FrozenReversalVolatilityContract = FROZEN_CONTRACT
) -> dict[str, Any]:
    validate_reversal_volatility_contract(contract)
    panel, cohort, frozen_events, input_meta = _load_and_validate_inputs(root, contract)
    events, reconstruction = _reconstruct_events(panel, cohort, frozen_events)
    round27_rank_data = _build_rank_data(panel, cohort, events)
    if round27_rank_data["bucket_assignment_sha256"] != ROUND27_BUCKET_ASSIGNMENT_SHA256:
        _fail("reversal_volatility_bucket_receipt_mismatch", "重建 bucket SHA 漂移")
    attribution = _build_attribution(panel, cohort, events, input_meta["round27"])
    family_rows, bootstrap = _family(attribution)
    family_by_id = {row["id"]: row for row in family_rows}
    diagnostics = _diagnostics(attribution)
    stresses = _stresses(attribution)

    exact_inputs = (
        reconstruction["maximum_return_residual"] <= RECONSTRUCTION_TOLERANCE
        and attribution["maximum_raw_round27_residual"] <= RECONSTRUCTION_TOLERANCE
    )
    feature_coverage = len(attribution["event_rows"]) == EXPECTED_EVENTS and all(
        len(row["universes"]) == 2 for row in attribution["event_rows"]
    )
    bucket_replay = (
        round27_rank_data["bucket_assignment_sha256"] == ROUND27_BUCKET_ASSIGNMENT_SHA256
        and attribution["maximum_raw_round27_residual"] <= RECONSTRUCTION_TOLERANCE
    )
    regression_integrity = (
        attribution["minimum_design_rank"] == 3
        and attribution["maximum_condition_number"] <= MAX_CONDITION_NUMBER
        and attribution["maximum_identity_residual"] <= RECONSTRUCTION_TOLERANCE
        and attribution["maximum_residual_mean"] <= RECONSTRUCTION_TOLERANCE
    )
    residual_retention = all(
        diagnostics[universe_id]["aggregate_top_middle_retention_fraction"]
        >= RESIDUAL_RETENTION_FRACTION
        for universe_id in UNIVERSE_IDS
    )
    family_adjusted = all(
        row["holm_adjusted_p"] <= 0.05 and row["bootstrap_max_t_p"] <= 0.05 for row in family_rows
    )
    regimes = stresses["qqq_trailing_20d_known_at_signal"]
    tails = stresses["remove_largest_raw_bottom_middle"]
    regime_tail_pass = all(
        regimes[universe_id][regime]["mean"] > 0.0
        and regimes[universe_id][regime]["newey_west"]["t_stat"] >= 1.96
        for universe_id in UNIVERSE_IDS
        for regime in ("qqq_trailing_nonnegative", "qqq_trailing_negative")
    ) and all(
        tails[universe_id]["mean"] > 0.0 and tails[universe_id]["newey_west"]["t_stat"] >= 1.96
        for universe_id in UNIVERSE_IDS
    )
    gates = [
        {
            "id": "exact_input_receipts",
            "label": "第 24–27 輪、行情、panel、watchlist 及 bucket 收據一致",
            "passed": exact_inputs,
        },
        {
            "id": "complete_feature_coverage",
            "label": "905 事件兩個 universe 的 5 日回報、20 日波幅及未來回報完整",
            "passed": feature_coverage,
        },
        {
            "id": "round27_bucket_replay",
            "label": "第 27 輪 bucket、事件次序及 raw spread 逐列重播",
            "passed": bucket_replay,
        },
        {
            "id": "regression_attribution_identity",
            "label": "OLS rank／condition、residual mean 及歸因 identity 通過",
            "passed": regression_integrity,
        },
        {
            "id": "eligible_raw_top_middle",
            "label": "eligible raw top-middle 通過平均、NW t 及兩半",
            "passed": _passes_positive(family_by_id["eligible_raw_top_middle"]),
        },
        {
            "id": "complete_raw_top_middle",
            "label": "complete raw top-middle 通過平均、NW t 及兩半",
            "passed": _passes_positive(family_by_id["complete_raw_top_middle"]),
        },
        {
            "id": "eligible_residual_top_middle",
            "label": "eligible residual top-middle 通過平均、NW t 及兩半",
            "passed": _passes_positive(family_by_id["eligible_residual_top_middle"]),
        },
        {
            "id": "complete_residual_top_middle",
            "label": "complete residual top-middle 通過平均、NW t 及兩半",
            "passed": _passes_positive(family_by_id["complete_residual_top_middle"]),
        },
        {
            "id": "eligible_raw_bottom_middle",
            "label": "eligible raw bottom-middle 為負、NW t 不高於 -1.96 且兩半為負",
            "passed": _passes_negative(family_by_id["eligible_raw_bottom_middle"]),
        },
        {
            "id": "complete_raw_bottom_middle",
            "label": "complete raw bottom-middle 為負、NW t 不高於 -1.96 且兩半為負",
            "passed": _passes_negative(family_by_id["complete_raw_bottom_middle"]),
        },
        {
            "id": "eligible_residual_bottom_middle",
            "label": "eligible residual bottom-middle 為負、NW t 不高於 -1.96 且兩半為負",
            "passed": _passes_negative(family_by_id["eligible_residual_bottom_middle"]),
        },
        {
            "id": "complete_residual_bottom_middle",
            "label": "complete residual bottom-middle 為負、NW t 不高於 -1.96 且兩半為負",
            "passed": _passes_negative(family_by_id["complete_residual_bottom_middle"]),
        },
        {
            "id": "retention_and_adjusted_family",
            "label": "兩個 residual top-middle 保留至少 75% raw 平均且八列共同校正通過",
            "passed": residual_retention and family_adjusted,
        },
        {
            "id": "known_at_regime_and_tail",
            "label": "QQQ 兩種 known-at 市況及 46-event 尾部的兩個 residual top-middle 均通過",
            "passed": regime_tail_pass,
        },
    ]
    if len(gates) != 14:
        _fail("reversal_volatility_family_contract_mismatch", "事前 gate 不是 14 項")
    passed = sum(bool(row["passed"]) for row in gates)

    control_labels = (
        "協議 SHA",
        "第 27 輪來源 commit",
        "第 27 輪收據 SHA",
        "第 24–26 輪收據 SHA",
        "原始事件收據 SHA",
        "行情 archive SHA／panel fingerprint",
        "watchlist SHA",
        "三個台股參考 commit",
        "25 股 cohort",
        "905 事件及嚴格日期次序",
        "5 日回報窗口",
        "20 日波幅窗口及 ddof=1",
        "平均 rank 轉換",
        "OLS 欄序、lstsq 及 condition 上限",
        "eligible／complete universe",
        "第 27 輪 bucket assignment SHA",
        "D+1／20 session／20 bps",
        "raw／predicted／residual identity",
        "八假說 family、Holm 及 NW lag 4",
        "52-event／20,000／seed 28202610 共同 bootstrap",
        "QQQ 20 日 known-at regime",
        "46-event 尾部及固定前後半",
        "現時代號／策略／Paper／實金決策邊界",
    )
    controls = [
        {"id": f"{index:02d}", "label": label, "passed": True}
        for index, label in enumerate(control_labels, start=1)
    ]
    attacks = run_contract_attacks()
    if len(controls) != 23 or len(attacks) != 23 or not all(row["rejected"] for row in attacks):
        _fail("reversal_volatility_decision_boundary_breached", "控制或攻擊矩陣不完整")

    return {
        "schema_version": SCHEMA_VERSION,
        "research_round": RESEARCH_ROUND,
        "generated_on": GENERATED_ON,
        "research_role": "same_seen_survivor_cohort_reversal_volatility_attribution_only",
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
            "round27_source_commit": ROUND27_SOURCE_COMMIT,
            "round27_receipt_path": ROUND27_RECEIPT_PATH,
            "round27_receipt_sha256": ROUND27_RECEIPT_SHA256,
            "round27_bucket_assignment_sha256": ROUND27_BUCKET_ASSIGNMENT_SHA256,
            "events": len(events),
            "first_signal_date": events[0]["signal_date"].strftime("%Y-%m-%d"),
            "last_signal_date": events[-1]["signal_date"].strftime("%Y-%m-%d"),
            "current_cohort": list(COHORT),
            "current_cohort_count": len(COHORT),
            "identifier_scope": "2026_current_symbols_not_permanent_ids",
            "survivorship_bias_warning": True,
        },
        "input_receipts": input_meta["hashes"],
        "reconstruction": reconstruction,
        "method": {
            "prior_return_sessions": PRIOR_RETURN_SESSIONS,
            "volatility_sessions": VOLATILITY_SESSIONS,
            "volatility_ddof": VOLATILITY_DDOF,
            "control_rank_method": CONTROL_RANK_METHOD,
            "regression_columns": list(REGRESSION_COLUMNS),
            "regression_method": REGRESSION_METHOD,
            "maximum_condition_number_allowed": MAX_CONDITION_NUMBER,
            "universe_ids": list(UNIVERSE_IDS),
            "bucket_ids": list(BUCKET_IDS),
            "holding_sessions": HOLDING_SESSIONS,
            "round_trip_cost_bps": ROUND_TRIP_COST_BPS,
            "feature_receipt_decimal_places": FEATURE_RECEIPT_DECIMAL_PLACES,
        },
        "attribution_integrity": {
            "feature_receipt_sha256": attribution["feature_receipt_sha256"],
            "feature_receipt_decimal_places": FEATURE_RECEIPT_DECIMAL_PLACES,
            "maximum_raw_round27_residual": attribution["maximum_raw_round27_residual"],
            "maximum_identity_residual": attribution["maximum_identity_residual"],
            "maximum_residual_mean": attribution["maximum_residual_mean"],
            "maximum_condition_number": attribution["maximum_condition_number"],
            "minimum_design_rank": attribution["minimum_design_rank"],
        },
        "event_rows": attribution["event_rows"],
        "family": {
            "size": len(FAMILY_IDS),
            "alpha": 0.05,
            "comparisons": family_rows,
            "common_bootstrap": bootstrap,
        },
        "attribution_summary": diagnostics,
        "primary_stresses": stresses,
        "gates": gates,
        "gate_summary": {"passed": passed, "total": len(gates), "all_passed": passed == 14},
        "controls": controls,
        "control_summary": {"passed": len(controls), "total": len(controls), "all_passed": True},
        "attacks": attacks,
        "attack_summary": {"rejected": len(attacks), "total": len(attacks), "all_rejected": True},
        "decision": {
            "not_rejected_by_round28": passed == 14,
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
    }
