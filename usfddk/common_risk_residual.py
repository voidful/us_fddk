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

from .correlation_crowding import (
    FROZEN_CONTRACT as CROWDING_CONTRACT,
)
from .correlation_crowding import (
    _load_inputs as _load_crowding_inputs,
)
from .correlation_crowding import (
    _reconstruct_events,
)
from .data import panel_fingerprint
from .metrics import newey_west_mean_test
from .universe import load_stock_watchlist

SCHEMA_VERSION = 1
RESEARCH_ROUND = 26
GENERATED_ON = "2026-08-04"
PROTOCOL_PATH = "docs/SHORT_TERM_COMMON_RISK_RESIDUAL_PROTOCOL.md"
PROTOCOL_SHA256 = "efa5d2f6bcf6489d9f2f15d982b54f760e581e1bd27642890b53fbb297f5b38c"
PROTOCOL_COMMIT = "6616064"
REPAIR_PROTOCOL_PATH = "docs/SHORT_TERM_COMMON_RISK_RESIDUAL_COVERAGE_REPAIR_PROTOCOL.md"
REPAIR_PROTOCOL_SHA256 = "a4c92a7145924b670e853d978f260adaa6a5794ce9be078ae9eb9810496341ea"
REPAIR_PROTOCOL_COMMIT = "b781601"

ROUND25_SOURCE_COMMIT = "ebcbc30ad98d719dad0c098a68211fd611001914"
ROUND25_RECEIPT_PATH = "artifacts/short_term_correlation_crowding_validation.json"
ROUND25_RECEIPT_SHA256 = "11155736a8449e6c4f50c0de0d285df9598d76de3752733f5bd140d8a2c8d0f5"
ROUND24_RECEIPT_PATH = "artifacts/short_term_baseline_multiplicity_validation.json"
ROUND24_RECEIPT_SHA256 = "4dc15a520606a03c85279bfaaca88367015bb651d0b6fbd77dffc9023cdbe282"
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
FAMILY_COMMON_EVENTS = 866
FAMILY_FIRST_SIGNAL_DATE = "2007-06-01"
FAMILY_LAST_SIGNAL_DATE = LAST_SIGNAL_DATE
COVERAGE_EXCLUDED_EVENTS = 39
COVERAGE_MISSING_SYMBOLS = ("MA",)
MOMENTUM_SESSIONS = 20
TREND_SESSIONS = 60
TOP_K = 7
ENTRY_DELAY = 1
HOLDING_SESSIONS = 20
ROUND_TRIP_COST_BPS = 20
FACTOR_IDENTITIES = ("QQQ", "SPY", "CURRENT_COHORT_EQUAL")
BETA_WINDOWS = (60, 252)
BETA_FORMULA = "sum((f-fbar)*(r-rbar))/sum((f-fbar)^2)"
MODEL_IDS = ("RAW", "QQQ_60", "QQQ_252", "SPY_252", "COHORT_252")
BASELINE_IDS = ("eligible", "complete_cohort")
FAMILY_SIZE = 10
FAMILY_ALPHA = 0.05
HAC_LAG = 4
FIRST_HALF_END = pd.Timestamp("2016-07-29")
SECOND_HALF_START = pd.Timestamp("2016-08-01")
BOOTSTRAP_BLOCK_LENGTH = 52
BOOTSTRAP_PATHS = 20_000
BOOTSTRAP_SEED = 26_202_608
TAIL_REMOVAL_EVENTS = 46
RECONSTRUCTION_TOLERANCE = 1e-12
SIGN_CLASSIFICATION_TOLERANCE = RECONSTRUCTION_TOLERANCE


class CommonRiskResidualError(ValueError):
    """Fail-closed Round 26 error with a stable semantic code."""

    def __init__(self, code: str, detail: str):
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}")


def _fail(code: str, detail: str) -> None:
    raise CommonRiskResidualError(code, detail)


@dataclass(frozen=True)
class FrozenCommonRiskContract:
    protocol_sha256: str = PROTOCOL_SHA256
    repair_protocol_sha256: str = REPAIR_PROTOCOL_SHA256
    round25_source_commit: str = ROUND25_SOURCE_COMMIT
    round25_receipt_sha256: str = ROUND25_RECEIPT_SHA256
    round24_receipt_sha256: str = ROUND24_RECEIPT_SHA256
    snapshot_sha256: str = SNAPSHOT_SHA256
    panel_sha256: str = PANEL_SHA256
    watchlist_sha256: str = WATCHLIST_SHA256
    event_receipt_sha256: str = EVENT_RECEIPT_SHA256
    reference_commits: tuple[tuple[str, str], ...] = REFERENCE_COMMITS
    cohort: tuple[str, ...] = COHORT
    expected_events: int = EXPECTED_EVENTS
    first_signal_date: str = FIRST_SIGNAL_DATE
    last_signal_date: str = LAST_SIGNAL_DATE
    family_common_events: int = FAMILY_COMMON_EVENTS
    family_first_signal_date: str = FAMILY_FIRST_SIGNAL_DATE
    family_last_signal_date: str = FAMILY_LAST_SIGNAL_DATE
    coverage_excluded_events: int = COVERAGE_EXCLUDED_EVENTS
    coverage_missing_symbols: tuple[str, ...] = COVERAGE_MISSING_SYMBOLS
    common_model_event_indices: bool = True
    momentum_sessions: int = MOMENTUM_SESSIONS
    trend_sessions: int = TREND_SESSIONS
    top_k: int = TOP_K
    entry_delay: int = ENTRY_DELAY
    holding_sessions: int = HOLDING_SESSIONS
    round_trip_cost_bps: int = ROUND_TRIP_COST_BPS
    factor_identities: tuple[str, ...] = FACTOR_IDENTITIES
    beta_windows: tuple[int, ...] = BETA_WINDOWS
    beta_formula: str = BETA_FORMULA
    beta_clipping: bool = False
    beta_winsorization: bool = False
    beta_shrinkage: bool = False
    baseline_ids: tuple[str, ...] = BASELINE_IDS
    model_ids: tuple[str, ...] = MODEL_IDS
    family_size: int = FAMILY_SIZE
    family_alpha: float = FAMILY_ALPHA
    hac_lag: int = HAC_LAG
    bootstrap_block_length: int = BOOTSTRAP_BLOCK_LENGTH
    bootstrap_paths: int = BOOTSTRAP_PATHS
    bootstrap_seed: int = BOOTSTRAP_SEED
    common_bootstrap_indices: bool = True
    centered_under_null: bool = True
    tail_removal_events: int = TAIL_REMOVAL_EVENTS
    current_sector_labels_only: bool = True
    permanent_identifier_claimed: bool = False
    formal_strategy_runs: int = 0
    paper_authorized: bool = False
    real_money_authorized: bool = False


FROZEN_CONTRACT = FrozenCommonRiskContract()


def validate_common_risk_contract(contract: FrozenCommonRiskContract) -> None:
    checks: tuple[tuple[bool, str, str], ...] = (
        (
            contract.protocol_sha256 == PROTOCOL_SHA256,
            "common_risk_protocol_mismatch",
            "第 26 輪協議 SHA 漂移",
        ),
        (
            contract.round25_source_commit == ROUND25_SOURCE_COMMIT,
            "common_risk_round25_source_mismatch",
            "第 25 輪來源 commit 漂移",
        ),
        (
            contract.round25_receipt_sha256 == ROUND25_RECEIPT_SHA256,
            "common_risk_round25_receipt_mismatch",
            "第 25 輪收據 SHA 漂移",
        ),
        (
            contract.round24_receipt_sha256 == ROUND24_RECEIPT_SHA256,
            "common_risk_round24_receipt_mismatch",
            "第 24 輪收據 SHA 漂移",
        ),
        (
            contract.snapshot_sha256 == SNAPSHOT_SHA256,
            "common_risk_snapshot_hash_mismatch",
            "行情 archive SHA 漂移",
        ),
        (
            contract.panel_sha256 == PANEL_SHA256,
            "common_risk_panel_fingerprint_mismatch",
            "行情 panel fingerprint 漂移",
        ),
        (
            contract.watchlist_sha256 == WATCHLIST_SHA256,
            "common_risk_watchlist_hash_mismatch",
            "現時觀察名單 SHA 漂移",
        ),
        (
            contract.event_receipt_sha256 == EVENT_RECEIPT_SHA256,
            "common_risk_event_receipt_hash_mismatch",
            "原始事件收據 SHA 漂移",
        ),
        (
            contract.reference_commits == REFERENCE_COMMITS,
            "common_risk_reference_commits_mismatch",
            "台股參考 commit 漂移",
        ),
        (
            contract.cohort == COHORT,
            "common_risk_cohort_mismatch",
            "25 股完整現時 cohort 漂移",
        ),
        (
            contract.expected_events == EXPECTED_EVENTS
            and contract.first_signal_date == FIRST_SIGNAL_DATE
            and contract.last_signal_date == LAST_SIGNAL_DATE,
            "common_risk_event_order_mismatch",
            "事件數或日期次序漂移",
        ),
        (
            contract.momentum_sessions == MOMENTUM_SESSIONS
            and contract.trend_sessions == TREND_SESSIONS
            and contract.top_k == TOP_K,
            "common_risk_signal_rule_mismatch",
            "20／60／Top-7 訊號漂移",
        ),
        (
            contract.entry_delay == ENTRY_DELAY
            and contract.holding_sessions == HOLDING_SESSIONS
            and contract.round_trip_cost_bps == ROUND_TRIP_COST_BPS,
            "common_risk_execution_rule_mismatch",
            "D+1／20 session／20 bps 執行漂移",
        ),
        (
            contract.factor_identities == FACTOR_IDENTITIES,
            "common_risk_factor_identity_mismatch",
            "QQQ／SPY／cohort factor identity 漂移",
        ),
        (
            contract.beta_windows == BETA_WINDOWS,
            "common_risk_beta_window_mismatch",
            "60／252 beta window 漂移",
        ),
        (
            contract.beta_formula == BETA_FORMULA
            and not contract.beta_clipping
            and not contract.beta_winsorization
            and not contract.beta_shrinkage,
            "common_risk_beta_formula_mismatch",
            "OLS beta 公式或禁止調整規則漂移",
        ),
        (
            contract.baseline_ids == BASELINE_IDS,
            "common_risk_baseline_mismatch",
            "eligible／complete baseline 漂移",
        ),
        (
            contract.model_ids == MODEL_IDS
            and contract.family_size == FAMILY_SIZE
            and contract.family_alpha == FAMILY_ALPHA
            and contract.hac_lag == HAC_LAG,
            "common_risk_family_contract_mismatch",
            "十假說 family、alpha 或 NW lag 漂移",
        ),
        (
            contract.bootstrap_block_length == BOOTSTRAP_BLOCK_LENGTH
            and contract.bootstrap_paths == BOOTSTRAP_PATHS
            and contract.bootstrap_seed == BOOTSTRAP_SEED
            and contract.common_bootstrap_indices
            and contract.centered_under_null
            and contract.tail_removal_events == TAIL_REMOVAL_EVENTS
            and contract.current_sector_labels_only
            and not contract.permanent_identifier_claimed,
            "common_risk_stress_contract_mismatch",
            "bootstrap、46-event 或現時行業標籤邊界漂移",
        ),
        (
            contract.formal_strategy_runs == 0
            and not contract.paper_authorized
            and not contract.real_money_authorized,
            "common_risk_decision_boundary_breached",
            "本輪不得授權策略、Paper 或實金",
        ),
        (
            contract.repair_protocol_sha256 == REPAIR_PROTOCOL_SHA256
            and contract.family_common_events == FAMILY_COMMON_EVENTS
            and contract.family_first_signal_date == FAMILY_FIRST_SIGNAL_DATE
            and contract.family_last_signal_date == FAMILY_LAST_SIGNAL_DATE
            and contract.coverage_excluded_events == COVERAGE_EXCLUDED_EVENTS
            and contract.coverage_missing_symbols == COVERAGE_MISSING_SYMBOLS
            and contract.common_model_event_indices,
            "common_risk_coverage_repair_mismatch",
            "beta 覆蓋 repair SHA、共同樣本或缺口身份漂移",
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


def _comparison(
    values: np.ndarray, dates: pd.Series, *, include_halves: bool = True
) -> dict[str, Any]:
    nw = _newey_west(values)
    result: dict[str, Any] = {
        "events": len(values),
        "mean_difference": float(values.mean()),
        "median_difference": float(np.median(values)),
        "positive_fraction": float((values > SIGN_CLASSIFICATION_TOLERANCE).mean()),
        "newey_west": nw,
        "raw_normal_p": _normal_two_sided_p(float(nw["t_stat"])),
    }
    if include_halves:
        result["fixed_halves"] = _fixed_halves(values, dates)
    return result


def _load_inputs(
    root: Path, contract: FrozenCommonRiskContract
) -> tuple[Any, list[str], list[dict[str, Any]], dict[str, Any]]:
    paths = {
        "protocol": root / PROTOCOL_PATH,
        "repair_protocol": root / REPAIR_PROTOCOL_PATH,
        "round25_receipt": root / ROUND25_RECEIPT_PATH,
        "round24_receipt": root / ROUND24_RECEIPT_PATH,
        "snapshot": root / SNAPSHOT_PATH,
        "watchlist": root / WATCHLIST_PATH,
        "event_receipt": root / EVENT_RECEIPT_PATH,
    }
    expected_hashes = {
        "protocol": contract.protocol_sha256,
        "repair_protocol": contract.repair_protocol_sha256,
        "round25_receipt": contract.round25_receipt_sha256,
        "round24_receipt": contract.round24_receipt_sha256,
        "snapshot": contract.snapshot_sha256,
        "watchlist": contract.watchlist_sha256,
        "event_receipt": contract.event_receipt_sha256,
    }
    error_codes = {
        "protocol": "common_risk_protocol_mismatch",
        "repair_protocol": "common_risk_coverage_repair_mismatch",
        "round25_receipt": "common_risk_round25_receipt_mismatch",
        "round24_receipt": "common_risk_round24_receipt_mismatch",
        "snapshot": "common_risk_snapshot_hash_mismatch",
        "watchlist": "common_risk_watchlist_hash_mismatch",
        "event_receipt": "common_risk_event_receipt_hash_mismatch",
    }
    observed_hashes = {key: _sha256_file(path) for key, path in paths.items()}
    for key, expected in expected_hashes.items():
        if observed_hashes[key] != expected:
            _fail(error_codes[key], f"{key} SHA-256 漂移")

    panel, cohort, frozen_events, _ = _load_crowding_inputs(root, CROWDING_CONTRACT)
    if panel_fingerprint(panel) != contract.panel_sha256:
        _fail("common_risk_panel_fingerprint_mismatch", "panel fingerprint 漂移")
    if tuple(sorted(cohort)) != contract.cohort:
        _fail("common_risk_cohort_mismatch", "完整現時 cohort 未逐字對齊")

    round25 = json.loads(paths["round25_receipt"].read_text(encoding="utf-8"))
    round24 = json.loads(paths["round24_receipt"].read_text(encoding="utf-8"))
    if round25.get("research_round") != 25 or round25.get("input", {}).get("events") != 905:
        _fail("common_risk_round25_receipt_mismatch", "第 25 輪收據身份不符")
    if round24.get("research_round") != 24 or round24.get("input", {}).get("common_events") != 905:
        _fail("common_risk_round24_receipt_mismatch", "第 24 輪收據身份不符")
    return (
        panel,
        cohort,
        frozen_events,
        {
            "paths": {key: str(path.relative_to(root)) for key, path in paths.items()},
            "hashes": observed_hashes,
            "round25_event_selection_sha256": round25["input"]["event_selection_sha256"],
        },
    )


def _ols_beta(stock_returns: np.ndarray, factor_returns: np.ndarray) -> float:
    if len(stock_returns) != len(factor_returns) or len(stock_returns) not in BETA_WINDOWS:
        _fail("common_risk_beta_window_mismatch", "beta window 長度不符")
    if not np.isfinite(stock_returns).all() or not np.isfinite(factor_returns).all():
        _fail("common_risk_beta_window_mismatch", "beta window 包含缺失或非有限回報")
    centered_factor = factor_returns - factor_returns.mean()
    denominator = float(np.dot(centered_factor, centered_factor))
    if denominator <= 0.0 or not math.isfinite(denominator):
        _fail("common_risk_beta_formula_mismatch", "factor variance 非正或非有限")
    centered_stock = stock_returns - stock_returns.mean()
    beta = float(np.dot(centered_factor, centered_stock) / denominator)
    if not math.isfinite(beta):
        _fail("common_risk_beta_formula_mismatch", "OLS beta 非有限")
    return beta


def _model_spec(model_id: str) -> tuple[str, int] | None:
    mapping = {
        "QQQ_60": ("QQQ", 60),
        "QQQ_252": ("QQQ", 252),
        "SPY_252": ("SPY", 252),
        "COHORT_252": ("CURRENT_COHORT_EQUAL", 252),
    }
    if model_id == "RAW":
        return None
    try:
        return mapping[model_id]
    except KeyError as exc:
        _fail("common_risk_factor_identity_mismatch", f"未知模型 {model_id}")
        raise AssertionError from exc


def _build_event_residuals(
    panel: Any,
    cohort: list[str],
    events: list[dict[str, Any]],
) -> dict[str, Any]:
    close_returns = panel.close[[*cohort, "QQQ", "SPY"]].pct_change(fill_method=None)
    cohort_factor = close_returns[cohort].mean(axis=1)
    dates = pd.Series([event["signal_date"] for event in events], name="signal_date")
    values = {
        f"{model_id}__{baseline_id}": np.empty(len(events), dtype=float)
        for model_id in MODEL_IDS
        for baseline_id in BASELINE_IDS
    }
    beta_gaps = {
        f"{model_id}__{baseline_id}": np.empty(len(events), dtype=float)
        for model_id in MODEL_IDS
        if model_id != "RAW"
        for baseline_id in BASELINE_IDS
    }
    beta_contributions = {key: np.empty(len(events), dtype=float) for key in beta_gaps}
    decomposition_residuals = {key: np.empty(len(events), dtype=float) for key in beta_gaps}
    factor_event_returns = {
        model_id: np.empty(len(events), dtype=float) for model_id in MODEL_IDS if model_id != "RAW"
    }
    beta_minimum = math.inf
    beta_maximum = -math.inf
    beta_cells = 0

    for event_index, event in enumerate(events):
        signal_position = close_returns.index.get_loc(event["signal_date"])
        if not isinstance(signal_position, int):
            _fail("common_risk_event_order_mismatch", "訊號日位置不唯一")
        gross = event["gross"].loc[cohort]
        baselines = {
            "eligible": event["eligible"],
            "complete_cohort": cohort,
        }
        raw_candidate = float(gross.loc[event["selected"]].mean())
        for baseline_id, symbols in baselines.items():
            values[f"RAW__{baseline_id}"][event_index] = raw_candidate - float(
                gross.loc[symbols].mean()
            )

        for model_id in MODEL_IDS:
            spec = _model_spec(model_id)
            if spec is None:
                continue
            factor_id, window = spec
            start = signal_position - window + 1
            if start < 1:
                _fail("common_risk_beta_window_mismatch", "beta window 早於行情起點")
            if factor_id == "CURRENT_COHORT_EQUAL":
                factor_window = cohort_factor.iloc[start : signal_position + 1]
                factor_event_gross = float(gross.mean())
            else:
                factor_window = close_returns[factor_id].iloc[start : signal_position + 1]
                factor_event_gross = float(
                    panel.close.loc[event["exit_date"], factor_id]
                    / panel.open.loc[event["entry_date"], factor_id]
                    - 1.0
                )
            if (
                len(factor_window) != window
                or not np.isfinite(factor_window.to_numpy(dtype=float)).all()
            ):
                _fail("common_risk_beta_window_mismatch", f"{model_id} factor window 不完整")
            factor_values = factor_window.to_numpy(dtype=float)
            betas: dict[str, float] = {}
            for symbol in cohort:
                stock_window = close_returns[symbol].iloc[start : signal_position + 1]
                beta = _ols_beta(stock_window.to_numpy(dtype=float), factor_values)
                betas[symbol] = beta
                beta_minimum = min(beta_minimum, beta)
                beta_maximum = max(beta_maximum, beta)
                beta_cells += 1
            residual = pd.Series(
                {
                    symbol: float(gross.loc[symbol] - betas[symbol] * factor_event_gross)
                    for symbol in cohort
                }
            )
            candidate_residual = float(residual.loc[event["selected"]].mean())
            candidate_beta = float(np.mean([betas[symbol] for symbol in event["selected"]]))
            factor_event_returns[model_id][event_index] = factor_event_gross
            for baseline_id, symbols in baselines.items():
                key = f"{model_id}__{baseline_id}"
                baseline_residual = float(residual.loc[symbols].mean())
                baseline_beta = float(np.mean([betas[symbol] for symbol in symbols]))
                residual_active = candidate_residual - baseline_residual
                beta_gap = candidate_beta - baseline_beta
                beta_contribution = beta_gap * factor_event_gross
                raw_active = values[f"RAW__{baseline_id}"][event_index]
                values[key][event_index] = residual_active
                beta_gaps[key][event_index] = beta_gap
                beta_contributions[key][event_index] = beta_contribution
                decomposition_residuals[key][event_index] = abs(
                    raw_active - residual_active - beta_contribution
                )

    expected_beta_cells = len(events) * (len(MODEL_IDS) - 1) * len(cohort)
    if beta_cells != expected_beta_cells:
        _fail("common_risk_beta_window_mismatch", "beta cell 覆蓋不完整")
    maximum_decomposition_residual = max(
        float(series.max()) for series in decomposition_residuals.values()
    )
    if maximum_decomposition_residual > RECONSTRUCTION_TOLERANCE:
        _fail(
            "common_risk_decomposition_failed",
            f"共同風險分解最大殘差 {maximum_decomposition_residual:.3e}",
        )
    return {
        "dates": dates,
        "values": values,
        "beta_gaps": beta_gaps,
        "beta_contributions": beta_contributions,
        "decomposition_residuals": decomposition_residuals,
        "factor_event_returns": factor_event_returns,
        "coverage": {
            "events": len(events),
            "models_with_beta": len(MODEL_IDS) - 1,
            "cohort_stocks_per_model": len(cohort),
            "beta_cells": beta_cells,
            "expected_beta_cells": expected_beta_cells,
            "all_complete": beta_cells == expected_beta_cells,
            "minimum_beta": float(beta_minimum),
            "maximum_beta": float(beta_maximum),
        },
        "maximum_decomposition_residual": maximum_decomposition_residual,
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
        _fail("common_risk_family_contract_mismatch", "bootstrap 去中心化失敗")
    if (standard_errors <= 0.0).any():
        _fail("common_risk_family_contract_mismatch", "NW 標準誤非正")
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


def _family(residuals: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for model_id in MODEL_IDS:
        for baseline_id in BASELINE_IDS:
            key = f"{model_id}__{baseline_id}"
            row = {
                "id": key,
                "model_id": model_id,
                "baseline_id": baseline_id,
                "label": f"{model_id} × {baseline_id}",
                **_comparison(residuals["values"][key], residuals["dates"]),
            }
            rows.append(row)
    if len(rows) != FAMILY_SIZE:
        _fail("common_risk_family_contract_mismatch", "family 不是十列")
    holm = _holm_adjust(rows)
    matrix = np.column_stack([residuals["values"][row["id"]] for row in rows])
    observed_t = np.asarray([row["newey_west"]["t_stat"] for row in rows], dtype=float)
    standard_errors = np.asarray([row["newey_west"]["standard_error"] for row in rows], dtype=float)
    bootstrap = _common_bootstrap(matrix, observed_t, standard_errors)
    for index, row in enumerate(rows):
        row["holm_adjusted_p"] = holm[row["id"]]
        row["bootstrap_max_t_p"] = bootstrap["single_step_max_t_p"][index]
    bootstrap["hypothesis_order"] = [row["id"] for row in rows]
    return rows, bootstrap


def _beta_gap_summaries(residuals: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for model_id in MODEL_IDS:
        if model_id == "RAW":
            continue
        for baseline_id in BASELINE_IDS:
            key = f"{model_id}__{baseline_id}"
            gaps = residuals["beta_gaps"][key]
            contribution = residuals["beta_contributions"][key]
            raw = residuals["values"][f"RAW__{baseline_id}"]
            rows.append(
                {
                    "id": key,
                    "model_id": model_id,
                    "baseline_id": baseline_id,
                    "mean_beta_gap": float(gaps.mean()),
                    "median_beta_gap": float(np.median(gaps)),
                    "median_absolute_beta_gap": float(np.median(np.abs(gaps))),
                    "p95_absolute_beta_gap": float(np.quantile(np.abs(gaps), 0.95)),
                    "positive_beta_gap_fraction": float(
                        (gaps > SIGN_CLASSIFICATION_TOLERANCE).mean()
                    ),
                    "mean_beta_contribution": float(contribution.mean()),
                    "mean_raw_active": float(raw.mean()),
                    "beta_contribution_share_of_raw_mean": (
                        float(contribution.mean() / raw.mean()) if raw.mean() != 0.0 else None
                    ),
                    "maximum_decomposition_residual": float(
                        residuals["decomposition_residuals"][key].max()
                    ),
                }
            )
    return rows


def _primary_stresses(residuals: dict[str, Any]) -> dict[str, Any]:
    primary_key = "QQQ_252__eligible"
    values = residuals["values"][primary_key]
    dates = residuals["dates"]
    qqq_forward = residuals["factor_event_returns"]["QQQ_252"]
    up = qqq_forward >= 0.0
    down = qqq_forward < 0.0
    if not up.any() or not down.any():
        _fail("common_risk_stress_contract_mismatch", "QQQ 上升／下跌 regime 有空組")
    regimes = {
        "qqq_nonnegative": _comparison(
            values[up], dates[up].reset_index(drop=True), include_halves=False
        ),
        "qqq_negative": _comparison(
            values[down], dates[down].reset_index(drop=True), include_halves=False
        ),
    }
    contribution = residuals["beta_contributions"][primary_key]
    order = sorted(
        range(len(values)),
        key=lambda index: (
            -abs(float(contribution[index])),
            dates.iloc[index].strftime("%Y-%m-%d"),
        ),
    )
    removed = order[:TAIL_REMOVAL_EVENTS]
    keep = np.ones(len(values), dtype=bool)
    keep[removed] = False
    tail = _comparison(values[keep], dates[keep].reset_index(drop=True), include_halves=False)
    tail.update(
        {
            "removed_events": TAIL_REMOVAL_EVENTS,
            "removed_signal_dates": [dates.iloc[index].strftime("%Y-%m-%d") for index in removed],
            "removed_absolute_beta_contribution_sum": float(np.abs(contribution[removed]).sum()),
            "total_absolute_beta_contribution_sum": float(np.abs(contribution).sum()),
            "removed_absolute_beta_contribution_share": float(
                np.abs(contribution[removed]).sum() / np.abs(contribution).sum()
            ),
        }
    )
    return {
        "primary_id": primary_key,
        "qqq_forward_regimes_ex_post_not_a_signal": regimes,
        "remove_largest_absolute_beta_contribution": tail,
    }


def _sector_diagnostic(events: list[dict[str, Any]]) -> dict[str, Any]:
    sector_by_symbol = {record.symbol: record.sector for record in load_stock_watchlist()}
    rows: list[dict[str, Any]] = []
    slot_counts: Counter[str] = Counter()
    for event in events:
        sectors = [sector_by_symbol[symbol] for symbol in event["selected"]]
        counts = Counter(sectors)
        weights = np.asarray(list(counts.values()), dtype=float) / TOP_K
        hhi = float(np.square(weights).sum())
        slot_counts.update(sectors)
        rows.append(
            {
                "signal_date": event["signal_date"].strftime("%Y-%m-%d"),
                "unique_current_sectors": len(counts),
                "current_sector_hhi": hhi,
                "effective_current_sectors": float(1.0 / hhi),
                "maximum_current_sector_stocks": max(counts.values()),
                "selected_current_sectors": dict(sorted(counts.items())),
            }
        )
    unique = np.asarray([row["unique_current_sectors"] for row in rows], dtype=float)
    hhi = np.asarray([row["current_sector_hhi"] for row in rows], dtype=float)
    effective = np.asarray([row["effective_current_sectors"] for row in rows], dtype=float)
    maximum = np.asarray([row["maximum_current_sector_stocks"] for row in rows], dtype=float)
    return {
        "identifier_scope": "2026_current_sector_labels_not_point_in_time",
        "investment_role": "one_way_caution_not_promotion_evidence",
        "survivorship_bias_warning": True,
        "summary": {
            "median_unique_current_sectors": float(np.median(unique)),
            "median_current_sector_hhi": float(np.median(hhi)),
            "median_effective_current_sectors": float(np.median(effective)),
            "events_with_current_sector_majority_fraction": float((maximum >= 4).mean()),
            "maximum_current_sector_stocks": int(maximum.max()),
        },
        "selection_slots_by_current_sector": dict(sorted(slot_counts.items())),
        "event_rows": rows,
    }


def _contract_attacks() -> list[
    tuple[
        str,
        str,
        str,
        Callable[[FrozenCommonRiskContract], FrozenCommonRiskContract],
    ]
]:
    return [
        (
            "01",
            "協議 SHA 漂移",
            "common_risk_protocol_mismatch",
            lambda c: replace(c, protocol_sha256="0" * 64),
        ),
        (
            "02",
            "第 25 輪來源 commit 漂移",
            "common_risk_round25_source_mismatch",
            lambda c: replace(c, round25_source_commit="0" * 40),
        ),
        (
            "03",
            "第 25 輪收據 SHA 漂移",
            "common_risk_round25_receipt_mismatch",
            lambda c: replace(c, round25_receipt_sha256="0" * 64),
        ),
        (
            "04",
            "第 24 輪收據 SHA 漂移",
            "common_risk_round24_receipt_mismatch",
            lambda c: replace(c, round24_receipt_sha256="0" * 64),
        ),
        (
            "05",
            "行情 archive SHA 漂移",
            "common_risk_snapshot_hash_mismatch",
            lambda c: replace(c, snapshot_sha256="0" * 64),
        ),
        (
            "06",
            "panel fingerprint 漂移",
            "common_risk_panel_fingerprint_mismatch",
            lambda c: replace(c, panel_sha256="0" * 64),
        ),
        (
            "07",
            "watchlist SHA 漂移",
            "common_risk_watchlist_hash_mismatch",
            lambda c: replace(c, watchlist_sha256="0" * 64),
        ),
        (
            "08",
            "原始事件收據 SHA 漂移",
            "common_risk_event_receipt_hash_mismatch",
            lambda c: replace(c, event_receipt_sha256="0" * 64),
        ),
        (
            "09",
            "台股參考 commit 漂移",
            "common_risk_reference_commits_mismatch",
            lambda c: replace(
                c, reference_commits=(("tst_wocker", "0" * 40), *c.reference_commits[1:])
            ),
        ),
        (
            "10",
            "25 股 cohort 漂移",
            "common_risk_cohort_mismatch",
            lambda c: replace(c, cohort=c.cohort[:-1]),
        ),
        (
            "11",
            "事件數改 904",
            "common_risk_event_order_mismatch",
            lambda c: replace(c, expected_events=904),
        ),
        ("12", "Top-K 改 10", "common_risk_signal_rule_mismatch", lambda c: replace(c, top_k=10)),
        (
            "13",
            "成本改 10 bps",
            "common_risk_execution_rule_mismatch",
            lambda c: replace(c, round_trip_cost_bps=10),
        ),
        (
            "14",
            "刪除 SPY factor",
            "common_risk_factor_identity_mismatch",
            lambda c: replace(c, factor_identities=("QQQ", "CURRENT_COHORT_EQUAL")),
        ),
        (
            "15",
            "beta window 改 126",
            "common_risk_beta_window_mismatch",
            lambda c: replace(c, beta_windows=(60, 126, 252)),
        ),
        (
            "16",
            "啟用 beta clipping",
            "common_risk_beta_formula_mismatch",
            lambda c: replace(c, beta_clipping=True),
        ),
        (
            "17",
            "刪除 complete baseline",
            "common_risk_baseline_mismatch",
            lambda c: replace(c, baseline_ids=("eligible",)),
        ),
        (
            "18",
            "family 改 8 列",
            "common_risk_family_contract_mismatch",
            lambda c: replace(c, family_size=8),
        ),
        (
            "19",
            "tail 改 45 列",
            "common_risk_stress_contract_mismatch",
            lambda c: replace(c, tail_removal_events=45),
        ),
        (
            "20",
            "越權啟動 Paper",
            "common_risk_decision_boundary_breached",
            lambda c: replace(c, paper_authorized=True),
        ),
        (
            "21",
            "共同 beta 樣本改 865",
            "common_risk_coverage_repair_mismatch",
            lambda c: replace(c, family_common_events=865),
        ),
    ]


def run_contract_attacks() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for attack_id, label, expected_code, mutate in _contract_attacks():
        observed_code: str | None = None
        try:
            validate_common_risk_contract(mutate(FROZEN_CONTRACT))
        except CommonRiskResidualError as exc:
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


def _gate_row(row: dict[str, Any]) -> bool:
    return (
        row["mean_difference"] > 0.0
        and row["newey_west"]["t_stat"] >= 1.96
        and row["fixed_halves"]["first"]["mean_difference"] > 0.0
        and row["fixed_halves"]["second"]["mean_difference"] > 0.0
    )


def run_common_risk_residual(
    root: str | Path,
    contract: FrozenCommonRiskContract = FROZEN_CONTRACT,
) -> dict[str, Any]:
    root_path = Path(root).resolve()
    validate_common_risk_contract(contract)
    panel, cohort, frozen_events, input_receipt = _load_inputs(root_path, contract)
    events, reconstruction = _reconstruct_events(panel, cohort, frozen_events)
    if reconstruction["event_selection_sha256"] != input_receipt["round25_event_selection_sha256"]:
        _fail("common_risk_event_order_mismatch", "第 25 輪事件選擇 hash 未逐字對齊")
    common_events = [
        event for event in events if event["signal_date"] >= pd.Timestamp(FAMILY_FIRST_SIGNAL_DATE)
    ]
    if (
        len(common_events) != FAMILY_COMMON_EVENTS
        or len(events) - len(common_events) != COVERAGE_EXCLUDED_EVENTS
        or common_events[0]["signal_date"].strftime("%Y-%m-%d") != FAMILY_FIRST_SIGNAL_DATE
        or common_events[-1]["signal_date"].strftime("%Y-%m-%d") != FAMILY_LAST_SIGNAL_DATE
    ):
        _fail("common_risk_coverage_repair_mismatch", "866 個共同事件或日期邊界不符")
    residuals = _build_event_residuals(panel, cohort, common_events)
    family_rows, bootstrap = _family(residuals)
    family_by_id = {row["id"]: row for row in family_rows}
    beta_gap_rows = _beta_gap_summaries(residuals)
    beta_gap_by_id = {row["id"]: row for row in beta_gap_rows}
    stresses = _primary_stresses(residuals)
    sector = _sector_diagnostic(common_events)

    qqq_gap = beta_gap_by_id["QQQ_252__eligible"]
    adjusted_ids = [
        f"{model_id}__{baseline_id}"
        for model_id in ("QQQ_252", "SPY_252", "COHORT_252")
        for baseline_id in BASELINE_IDS
    ]
    regimes = stresses["qqq_forward_regimes_ex_post_not_a_signal"]
    tail = stresses["remove_largest_absolute_beta_contribution"]
    gates = [
        {
            "id": "exact_event_reconstruction",
            "label": "四條原始事件回報逐列重建誤差不高於 1e-12",
            "passed": reconstruction["maximum_return_residual"] <= RECONSTRUCTION_TOLERANCE,
        },
        {
            "id": "complete_beta_coverage",
            "label": "866 個共同事件所有股票及模型 beta window 完整",
            "passed": residuals["coverage"]["all_complete"],
        },
        {
            "id": "exact_beta_decomposition",
            "label": "所有共同風險分解最大誤差不高於 1e-12",
            "passed": residuals["maximum_decomposition_residual"] <= RECONSTRUCTION_TOLERANCE,
        },
        {
            "id": "median_absolute_qqq_beta_gap",
            "label": "QQQ 252 日絕對 beta gap 中位不高於 0.10",
            "passed": qqq_gap["median_absolute_beta_gap"] <= 0.10,
        },
        {
            "id": "p95_absolute_qqq_beta_gap",
            "label": "QQQ 252 日絕對 beta gap 95th 不高於 0.25",
            "passed": qqq_gap["p95_absolute_beta_gap"] <= 0.25,
        },
        {
            "id": "qqq252_eligible",
            "label": "QQQ 252 殘差對 eligible 為正、NW t 過 1.96、兩半同正",
            "passed": _gate_row(family_by_id["QQQ_252__eligible"]),
        },
        {
            "id": "qqq252_complete",
            "label": "QQQ 252 殘差對 complete 為正、NW t 過 1.96、兩半同正",
            "passed": _gate_row(family_by_id["QQQ_252__complete_cohort"]),
        },
        {
            "id": "spy252_eligible",
            "label": "SPY 252 殘差對 eligible 為正、NW t 過 1.96、兩半同正",
            "passed": _gate_row(family_by_id["SPY_252__eligible"]),
        },
        {
            "id": "spy252_complete",
            "label": "SPY 252 殘差對 complete 為正、NW t 過 1.96、兩半同正",
            "passed": _gate_row(family_by_id["SPY_252__complete_cohort"]),
        },
        {
            "id": "cohort252_eligible",
            "label": "cohort 252 殘差對 eligible 為正、NW t 過 1.96、兩半同正",
            "passed": _gate_row(family_by_id["COHORT_252__eligible"]),
        },
        {
            "id": "cohort252_complete",
            "label": "cohort 252 殘差對 complete 為正、NW t 過 1.96、兩半同正",
            "passed": _gate_row(family_by_id["COHORT_252__complete_cohort"]),
        },
        {
            "id": "adjusted_family_correction",
            "label": "六個 252 日殘差列 Holm／共同 max-t p 均不高於 0.05",
            "passed": all(
                family_by_id[row_id]["holm_adjusted_p"] <= FAMILY_ALPHA
                and family_by_id[row_id]["bootstrap_max_t_p"] <= FAMILY_ALPHA
                for row_id in adjusted_ids
            ),
        },
        {
            "id": "qqq_up_down_regimes",
            "label": "未來 QQQ 上升／下跌兩組主要殘差均正且 NW t 不低於 1.96",
            "passed": all(
                row["mean_difference"] > 0.0 and row["newey_west"]["t_stat"] >= 1.96
                for row in regimes.values()
            ),
        },
        {
            "id": "remove_top_beta_contribution",
            "label": "移除最大 46 個絕對 beta contribution 後主要殘差仍正且 NW t 不低於 1.96",
            "passed": tail["mean_difference"] > 0.0 and tail["newey_west"]["t_stat"] >= 1.96,
        },
    ]
    if len(gates) != 14:
        _fail("common_risk_family_contract_mismatch", "事前 gate 不是 14 項")
    passed = sum(bool(row["passed"]) for row in gates)

    controls = [
        {"id": f"{index:02d}", "label": label, "passed": True}
        for index, label in enumerate(
            (
                "協議 SHA",
                "第 25 輪來源 commit／收據 SHA",
                "第 24 輪收據 SHA",
                "行情 archive SHA",
                "panel fingerprint",
                "watchlist SHA",
                "原始事件收據 SHA",
                "三個台股參考 commit",
                "25 股 cohort 逐字一致",
                "905 事件及日期次序",
                "20／60／Top-7 訊號",
                "D+1／20 session／20 bps",
                "QQQ／SPY／cohort factor identity",
                "60／252 beta window",
                "OLS beta 公式及禁止 clipping／winsor／shrink",
                "eligible／complete 兩個 baseline",
                "十假說 family、Holm 及 NW lag 4",
                "52-event／20,000／seed 26202608 共同 bootstrap",
                "46-event 壓力及現時行業標籤不可升格",
                "策略／Paper／實金決策邊界",
                "beta 覆蓋 repair SHA、866 個共同事件及 MA 缺口",
            ),
            start=1,
        )
    ]
    attacks = run_contract_attacks()
    if len(controls) != 21 or len(attacks) != 21 or not all(row["rejected"] for row in attacks):
        _fail("common_risk_decision_boundary_breached", "控制或攻擊矩陣不完整")

    return {
        "schema_version": SCHEMA_VERSION,
        "research_round": RESEARCH_ROUND,
        "generated_on": GENERATED_ON,
        "research_role": "survivor_contaminated_common_risk_falsification_only",
        "protocol": {
            "path": PROTOCOL_PATH,
            "sha256": PROTOCOL_SHA256,
            "commit": PROTOCOL_COMMIT,
            "calculated_after_protocol_commit": True,
            "initial_parent_protocol_run": {
                "status": "failed_closed_before_output",
                "error_code": "common_risk_beta_window_mismatch",
            },
            "coverage_repair": {
                "path": REPAIR_PROTOCOL_PATH,
                "sha256": REPAIR_PROTOCOL_SHA256,
                "commit": REPAIR_PROTOCOL_COMMIT,
                "calculated_after_repair_commit": True,
                "independent_first_unseen_evidence": False,
            },
        },
        "references": [
            {"repository": repository, "commit": commit} for repository, commit in REFERENCE_COMMITS
        ],
        "input": {
            "round25_source_commit": ROUND25_SOURCE_COMMIT,
            "round25_receipt_path": ROUND25_RECEIPT_PATH,
            "round25_receipt_sha256": ROUND25_RECEIPT_SHA256,
            "round24_receipt_path": ROUND24_RECEIPT_PATH,
            "round24_receipt_sha256": ROUND24_RECEIPT_SHA256,
            "snapshot_path": SNAPSHOT_PATH,
            "snapshot_sha256": SNAPSHOT_SHA256,
            "panel_sha256": PANEL_SHA256,
            "watchlist_path": WATCHLIST_PATH,
            "watchlist_sha256": WATCHLIST_SHA256,
            "event_receipt_path": EVENT_RECEIPT_PATH,
            "event_receipt_sha256": EVENT_RECEIPT_SHA256,
            "event_selection_sha256": reconstruction["event_selection_sha256"],
            "events": len(events),
            "first_signal_date": events[0]["signal_date"].strftime("%Y-%m-%d"),
            "last_signal_date": events[-1]["signal_date"].strftime("%Y-%m-%d"),
            "current_cohort": list(COHORT),
            "current_cohort_count": len(COHORT),
            "identifier_scope": "2026_current_symbols_not_permanent_ids",
            "survivorship_bias_warning": True,
            "family_common_events": len(common_events),
            "family_first_signal_date": common_events[0]["signal_date"].strftime("%Y-%m-%d"),
            "family_last_signal_date": common_events[-1]["signal_date"].strftime("%Y-%m-%d"),
            "coverage_excluded_events": len(events) - len(common_events),
            "coverage_excluded_first_signal_date": events[0]["signal_date"].strftime("%Y-%m-%d"),
            "coverage_excluded_last_signal_date": events[len(events) - len(common_events) - 1][
                "signal_date"
            ].strftime("%Y-%m-%d"),
            "coverage_missing_symbols": list(COVERAGE_MISSING_SYMBOLS),
            "common_model_event_indices": True,
        },
        "reconstruction": reconstruction,
        "method": {
            "beta_formula": BETA_FORMULA,
            "models": list(MODEL_IDS),
            "baselines": list(BASELINE_IDS),
            "cost_bps_each_full_exposure_path": ROUND_TRIP_COST_BPS,
            "active_cost_cancels_exactly": True,
            "no_beta_clipping_winsorization_or_shrinkage": True,
        },
        "beta_coverage": residuals["coverage"],
        "maximum_decomposition_residual": residuals["maximum_decomposition_residual"],
        "beta_gap_summaries": beta_gap_rows,
        "family": {
            "size": FAMILY_SIZE,
            "alpha": FAMILY_ALPHA,
            "comparisons": family_rows,
            "common_bootstrap": bootstrap,
        },
        "primary_stresses": stresses,
        "current_sector_label_diagnostic": sector,
        "gates": gates,
        "gate_summary": {"passed": passed, "total": len(gates), "all_passed": passed == len(gates)},
        "controls": controls,
        "control_summary": {"passed": len(controls), "total": len(controls), "all_passed": True},
        "attacks": attacks,
        "attack_summary": {"rejected": len(attacks), "total": len(attacks), "all_rejected": True},
        "decision": {
            "not_rejected_by_round26": passed == len(gates),
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
