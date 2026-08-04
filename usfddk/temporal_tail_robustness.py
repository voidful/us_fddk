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

from .metrics import newey_west_mean_test

SCHEMA_VERSION = 1
RESEARCH_ROUND = 23
PROTOCOL_PATH = "docs/SHORT_TERM_TEMPORAL_TAIL_ROBUSTNESS_PROTOCOL.md"
PROTOCOL_SHA256 = "5119362c145ac7bfd4406973ab5d50ba2ec9d1ffd65c22de41c6cf03138b7273"
PROTOCOL_COMMIT = "77679e3024318b48c6547f0e6b68f98db0aa7171"
INPUT_PATH = "artifacts/short_term_high_return_validation.json"
INPUT_SHA256 = "fa2463cc8273a316e4a98428767b695eb85c74e9ac75c47b5ca34592102979e8"
EVENT_PATH = (
    "taiwan_reference_signal_layer_diagnostic.horizons[\"20\"].event_series"
)
HORIZON = 20
EXPECTED_EVENT_COUNT = 905
TOP_K = 7
EMBEDDED_ROUND_TRIP_COST_BPS = 20
HAC_LAGS = (4, 13, 26, 52)
CALENDAR_YEARS = tuple(range(2006, 2027))
EPOCHS = (
    ("2006_2009", "2006–2009", "2006-08-04", "2009-12-31"),
    ("2010_2013", "2010–2013", "2010-01-01", "2013-12-31"),
    ("2014_2017", "2014–2017", "2014-01-01", "2017-12-31"),
    ("2018_2021", "2018–2021", "2018-01-01", "2021-12-31"),
    ("2022_2026", "2022–2026", "2022-01-01", "2026-07-02"),
)
YEAR_REMOVAL_COUNTS = (1, 3)
WINSOR_GRIDS = ((0.01, 0.99), (0.05, 0.95))
TAIL_REMOVAL_COUNTS = (10, 46)
BOOTSTRAP_BLOCK_LENGTH = 52
BOOTSTRAP_PATHS = 5_000
BOOTSTRAP_SEED = 20_260_804
CLUSTER_T_CRITICAL = 2.085963
FIRST_HALF_END = pd.Timestamp("2016-07-29")
SECOND_HALF_START = pd.Timestamp("2016-08-01")


class TemporalTailRobustnessError(ValueError):
    """Fail-closed Round 23 error with a stable semantic code."""

    def __init__(self, code: str, detail: str):
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}")


def _fail(code: str, detail: str) -> None:
    raise TemporalTailRobustnessError(code, detail)


@dataclass(frozen=True)
class FrozenRobustnessContract:
    input_sha256: str = INPUT_SHA256
    event_path: str = EVENT_PATH
    horizon: int = HORIZON
    expected_event_count: int = EXPECTED_EVENT_COUNT
    strict_event_order: bool = True
    paired_baseline: bool = True
    cost_double_counted: bool = False
    hac_lags: tuple[int, ...] = HAC_LAGS
    calendar_years: tuple[int, ...] = CALENDAR_YEARS
    epochs: tuple[tuple[str, str, str, str], ...] = EPOCHS
    year_removal_counts: tuple[int, ...] = YEAR_REMOVAL_COUNTS
    winsor_grids: tuple[tuple[float, float], ...] = WINSOR_GRIDS
    tail_removal_counts: tuple[int, ...] = TAIL_REMOVAL_COUNTS
    bootstrap_block_length: int = BOOTSTRAP_BLOCK_LENGTH
    bootstrap_paths: int = BOOTSTRAP_PATHS
    bootstrap_seed: int = BOOTSTRAP_SEED
    circular_bootstrap: bool = True
    paper_authorized: bool = False
    real_money_authorized: bool = False


FROZEN_CONTRACT = FrozenRobustnessContract()


def validate_robustness_contract(contract: FrozenRobustnessContract) -> None:
    checks: tuple[tuple[bool, str, str], ...] = (
        (
            contract.input_sha256 == INPUT_SHA256,
            "robustness_input_hash_mismatch",
            "輸入 SHA-256 並非凍結版本",
        ),
        (
            contract.event_path == EVENT_PATH,
            "robustness_path_not_frozen",
            "事件 JSON 路徑漂移",
        ),
        (
            contract.horizon == HORIZON,
            "robustness_horizon_not_frozen",
            "持有期必須維持 20 日",
        ),
        (
            contract.expected_event_count == EXPECTED_EVENT_COUNT,
            "robustness_event_count_mismatch",
            "事件數必須維持 905",
        ),
        (
            contract.strict_event_order,
            "robustness_event_order_invalid",
            "日期必須嚴格遞增",
        ),
        (
            contract.paired_baseline,
            "robustness_baseline_not_paired",
            "候選與合資格池必須逐事件配對",
        ),
        (
            not contract.cost_double_counted,
            "robustness_cost_double_counted",
            "輸入已扣成本，不得再次扣費",
        ),
        (
            contract.hac_lags == HAC_LAGS,
            "robustness_hac_lags_not_frozen",
            "HAC lag 前沿漂移",
        ),
        (
            contract.calendar_years == CALENDAR_YEARS,
            "robustness_calendar_clusters_not_frozen",
            "曆年 cluster 漂移",
        ),
        (
            contract.epochs == EPOCHS,
            "robustness_epochs_not_frozen",
            "固定市場時段漂移",
        ),
        (
            contract.year_removal_counts == YEAR_REMOVAL_COUNTS,
            "robustness_year_removal_not_frozen",
            "最佳年份刪除規則漂移",
        ),
        (
            contract.winsor_grids == WINSOR_GRIDS,
            "robustness_winsor_grid_not_frozen",
            "winsor 百分位漂移",
        ),
        (
            contract.tail_removal_counts == TAIL_REMOVAL_COUNTS,
            "robustness_tail_removal_not_frozen",
            "極端事件刪除數漂移",
        ),
        (
            contract.bootstrap_block_length == BOOTSTRAP_BLOCK_LENGTH
            and contract.bootstrap_paths == BOOTSTRAP_PATHS
            and contract.bootstrap_seed == BOOTSTRAP_SEED
            and contract.circular_bootstrap,
            "robustness_bootstrap_not_frozen",
            "moving-block bootstrap 契約漂移",
        ),
        (
            not contract.paper_authorized and not contract.real_money_authorized,
            "robustness_decision_boundary_breached",
            "本輪不得授權 Paper 或實金",
        ),
    )
    for passed, code, detail in checks:
        if not passed:
            _fail(code, detail)


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_frozen_events(
    root: Path, contract: FrozenRobustnessContract
) -> tuple[pd.DataFrame, dict[str, str]]:
    protocol_path = root / PROTOCOL_PATH
    protocol_sha256 = _sha256_file(protocol_path)
    if protocol_sha256 != PROTOCOL_SHA256:
        _fail("robustness_protocol_mismatch", "第 23 輪協議 SHA-256 漂移")

    input_path = root / INPUT_PATH
    input_sha256 = _sha256_file(input_path)
    if input_sha256 != contract.input_sha256:
        _fail("robustness_input_hash_mismatch", "短線訊號輸入 SHA-256 漂移")

    payload = json.loads(input_path.read_text(encoding="utf-8"))
    try:
        events = payload["taiwan_reference_signal_layer_diagnostic"]["horizons"][
            str(contract.horizon)
        ]["event_series"]
    except (KeyError, TypeError) as exc:
        _fail("robustness_path_not_frozen", f"找不到固定事件：{exc}")

    frame = pd.DataFrame(events)[
        ["signal_date", "eligible_count", "top7_return", "eligible_equal_return"]
    ].copy()
    frame["signal_date"] = pd.to_datetime(frame["signal_date"], errors="raise")
    for column in ("eligible_count", "top7_return", "eligible_equal_return"):
        frame[column] = pd.to_numeric(frame[column], errors="raise")

    if len(frame) != contract.expected_event_count:
        _fail("robustness_event_count_mismatch", "輸入事件數與凍結契約不同")
    if (
        not frame["signal_date"].is_monotonic_increasing
        or frame["signal_date"].duplicated().any()
    ):
        _fail("robustness_event_order_invalid", "訊號日期排序或唯一性漂移")
    numeric = frame[["eligible_count", "top7_return", "eligible_equal_return"]]
    if not np.isfinite(numeric.to_numpy(dtype=float)).all():
        _fail("robustness_event_values_invalid", "事件含非有限數值")
    if (frame["eligible_count"] < TOP_K).any():
        _fail("robustness_event_values_invalid", "合資格股份少於固定 Top-7")

    event_payload = frame.assign(
        signal_date=frame["signal_date"].dt.strftime("%Y-%m-%d")
    ).to_dict(orient="records")
    event_sha256 = hashlib.sha256(
        json.dumps(event_payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return frame, {
        "input_sha256": input_sha256,
        "protocol_sha256": protocol_sha256,
        "event_series_sha256": event_sha256,
    }


def _nw(values: np.ndarray, lag: int) -> dict[str, float | int]:
    result = newey_west_mean_test(
        pd.Series(values), max_lag=lag, periods_per_year=52
    )
    return {
        "mean_difference": float(result["mean_daily"]),
        "annualized_event_difference": float(result["annualized"]),
        "standard_error": (
            float(result["mean_daily"] / result["t_stat"])
            if result["t_stat"] != 0.0
            else 0.0
        ),
        "t_stat": float(result["t_stat"]),
        "lag": int(result["lag"]),
    }


def _hac_frontier(values: np.ndarray) -> list[dict[str, float | int]]:
    return [_nw(values, lag) for lag in HAC_LAGS]


def _cluster_mean_test(values: np.ndarray, years: np.ndarray) -> dict[str, Any]:
    n = len(values)
    unique_years = np.unique(years)
    clusters = len(unique_years)
    if n < 3 or clusters < 2:
        _fail("robustness_cluster_sample_invalid", "cluster 樣本不足")
    mean = float(values.mean())
    residuals = values - mean
    scores = np.asarray(
        [residuals[years == year].sum() for year in unique_years], dtype=float
    )
    variance = (
        (clusters / (clusters - 1.0))
        * (n / (n - 1.0))
        * float(np.dot(scores, scores))
        / (n * n)
    )
    standard_error = math.sqrt(max(variance, 0.0))
    t_stat = mean / standard_error if standard_error > 0.0 else 0.0
    return {
        "mean_difference": mean,
        "standard_error": float(standard_error),
        "t_stat": float(t_stat),
        "clusters": clusters,
        "degrees_of_freedom": clusters - 1,
        "two_sided_5pct_critical": CLUSTER_T_CRITICAL,
    }


def _year_rows(active: np.ndarray, dates: pd.Series) -> list[dict[str, Any]]:
    years = dates.dt.year.to_numpy(dtype=int)
    total_sum = float(active.sum())
    positive_sum = float(active[active > 0.0].sum())
    if math.isclose(total_sum, 0.0, abs_tol=1e-15):
        _fail("robustness_net_contribution_undefined", "淨配對差總和為零")
    if math.isclose(positive_sum, 0.0, abs_tol=1e-15):
        _fail("robustness_positive_contribution_undefined", "正配對差總和為零")
    rows: list[dict[str, Any]] = []
    for year in CALENDAR_YEARS:
        mask = years == year
        if not mask.any():
            _fail("robustness_calendar_clusters_not_frozen", f"{year} 沒有事件")
        values = active[mask]
        year_sum = float(values.sum())
        rows.append(
            {
                "year": year,
                "events": int(mask.sum()),
                "mean_difference": float(values.mean()),
                "median_difference": float(np.median(values)),
                "positive_fraction": float((values > 0.0).mean()),
                "sum_difference": year_sum,
                "share_of_net_sum": year_sum / total_sum,
                "share_of_positive_sum": float(values[values > 0.0].sum())
                / positive_sum,
            }
        )
    return rows


def _epoch_rows(active: np.ndarray, dates: pd.Series) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for epoch_id, label, start, end in EPOCHS:
        mask = ((dates >= pd.Timestamp(start)) & (dates <= pd.Timestamp(end))).to_numpy()
        if not mask.any():
            _fail("robustness_epoch_sample_invalid", f"{label} 沒有事件")
        values = active[mask]
        rows.append(
            {
                "id": epoch_id,
                "label": label,
                "start": start,
                "end": end,
                "events": int(mask.sum()),
                "mean_difference": float(values.mean()),
                "median_difference": float(np.median(values)),
                "positive_fraction": float((values > 0.0).mean()),
                "newey_west_lag4": _nw(values, 4),
            }
        )
    return rows


def _subset_summary(
    active: np.ndarray, dates: pd.Series, keep_mask: np.ndarray
) -> dict[str, Any]:
    values = active[keep_mask]
    subset_dates = dates[keep_mask].reset_index(drop=True)
    years = subset_dates.dt.year.to_numpy(dtype=int)
    first_mask = (subset_dates <= FIRST_HALF_END).to_numpy(dtype=bool)
    second_mask = (subset_dates >= SECOND_HALF_START).to_numpy(dtype=bool)
    return {
        "events": int(len(values)),
        "mean_difference": float(values.mean()),
        "median_difference": float(np.median(values)),
        "positive_fraction": float((values > 0.0).mean()),
        "newey_west_lag4": _nw(values, 4),
        "calendar_cluster": _cluster_mean_test(values, years),
        "fixed_halves": {
            "first_events": int(first_mask.sum()),
            "first_mean_difference": float(values[first_mask].mean()),
            "second_events": int(second_mask.sum()),
            "second_mean_difference": float(values[second_mask].mean()),
        },
        "epochs": _epoch_rows(values, subset_dates),
    }


def _sign_test(active: np.ndarray) -> dict[str, Any]:
    positive = int((active > 0.0).sum())
    negative = int((active < 0.0).sum())
    zero = int((active == 0.0).sum())
    trials = positive + negative
    tail = min(positive, negative)
    tail_probability = sum(math.comb(trials, k) for k in range(tail + 1)) / (
        2**trials
    )
    return {
        "positive": positive,
        "negative": negative,
        "zero": zero,
        "nonzero_trials": trials,
        "two_sided_exact_p_value": float(min(1.0, 2.0 * tail_probability)),
    }


def _moving_block_bootstrap(active: np.ndarray) -> dict[str, Any]:
    n = len(active)
    blocks_per_path = math.ceil(n / BOOTSTRAP_BLOCK_LENGTH)
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    starts = rng.integers(0, n, size=(BOOTSTRAP_PATHS, blocks_per_path))
    offsets = np.arange(BOOTSTRAP_BLOCK_LENGTH, dtype=int)
    indices = (starts[:, :, None] + offsets[None, None, :]) % n
    indices = indices.reshape(BOOTSTRAP_PATHS, -1)[:, :n]
    path_means = active[indices].mean(axis=1)
    low, median, high = np.quantile(path_means, [0.025, 0.5, 0.975])
    return {
        "block_length_events": BOOTSTRAP_BLOCK_LENGTH,
        "paths": BOOTSTRAP_PATHS,
        "seed": BOOTSTRAP_SEED,
        "circular": True,
        "blocks_per_path": blocks_per_path,
        "start_index_sha256": hashlib.sha256(starts.tobytes()).hexdigest(),
        "mean_difference_quantiles": {
            "p025": float(low),
            "p500": float(median),
            "p975": float(high),
        },
        "positive_mean_fraction": float((path_means > 0.0).mean()),
    }


def _contract_attacks() -> list[
    tuple[
        str,
        str,
        str,
        Callable[[FrozenRobustnessContract], FrozenRobustnessContract],
    ]
]:
    return [
        ("01", "輸入 SHA 漂移", "robustness_input_hash_mismatch", lambda c: replace(c, input_sha256="0" * 64)),
        ("02", "事件路徑漂移", "robustness_path_not_frozen", lambda c: replace(c, event_path="other")),
        ("03", "改用 10 日", "robustness_horizon_not_frozen", lambda c: replace(c, horizon=10)),
        ("04", "事件數漂移", "robustness_event_count_mismatch", lambda c: replace(c, expected_event_count=904)),
        ("05", "容許日期重排", "robustness_event_order_invalid", lambda c: replace(c, strict_event_order=False)),
        ("06", "取消配對 baseline", "robustness_baseline_not_paired", lambda c: replace(c, paired_baseline=False)),
        ("07", "重複扣成本", "robustness_cost_double_counted", lambda c: replace(c, cost_double_counted=True)),
        ("08", "刪除 HAC lag 52", "robustness_hac_lags_not_frozen", lambda c: replace(c, hac_lags=(4, 13, 26))),
        ("09", "刪除 2008 cluster", "robustness_calendar_clusters_not_frozen", lambda c: replace(c, calendar_years=tuple(year for year in CALENDAR_YEARS if year != 2008))),
        ("10", "合併市場時段", "robustness_epochs_not_frozen", lambda c: replace(c, epochs=EPOCHS[:-1])),
        ("11", "只刪最佳一年", "robustness_year_removal_not_frozen", lambda c: replace(c, year_removal_counts=(1,))),
        ("12", "刪除 5% winsor", "robustness_winsor_grid_not_frozen", lambda c: replace(c, winsor_grids=((0.01, 0.99),))),
        ("13", "刪除較少極端事件", "robustness_tail_removal_not_frozen", lambda c: replace(c, tail_removal_counts=(9, 45))),
        ("14", "縮短 bootstrap block", "robustness_bootstrap_not_frozen", lambda c: replace(c, bootstrap_block_length=13)),
        ("15", "提前授權 Paper", "robustness_decision_boundary_breached", lambda c: replace(c, paper_authorized=True)),
    ]


def run_attack_harness() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for attack_id, label, expected_code, mutate in _contract_attacks():
        observed_code: str | None = None
        try:
            validate_robustness_contract(mutate(FROZEN_CONTRACT))
        except TemporalTailRobustnessError as exc:
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


def run_temporal_tail_robustness(root: str | Path) -> dict[str, Any]:
    root_path = Path(root).resolve()
    contract = FROZEN_CONTRACT
    validate_robustness_contract(contract)
    frame, integrity = _load_frozen_events(root_path, contract)

    dates = frame["signal_date"]
    selected = frame["top7_return"].to_numpy(dtype=float)
    baseline = frame["eligible_equal_return"].to_numpy(dtype=float)
    active = selected - baseline
    years = dates.dt.year.to_numpy(dtype=int)

    year_rows = _year_rows(active, dates)
    calendar_cluster = _cluster_mean_test(active, years)
    epoch_rows = _epoch_rows(active, dates)
    hac_frontier = _hac_frontier(active)
    bootstrap = _moving_block_bootstrap(active)

    leave_one_year_out: list[dict[str, Any]] = []
    for year in CALENDAR_YEARS:
        keep = years != year
        summary = _subset_summary(active, dates, keep)
        leave_one_year_out.append({"removed_year": year, **summary})

    ranked_years = [
        row["year"]
        for row in sorted(
            year_rows, key=lambda row: (-row["sum_difference"], row["year"])
        )
    ]
    best_year_removals: list[dict[str, Any]] = []
    for count in YEAR_REMOVAL_COUNTS:
        removed = ranked_years[:count]
        keep = ~np.isin(years, removed)
        best_year_removals.append(
            {
                "removed_count": count,
                "removed_years": removed,
                **_subset_summary(active, dates, keep),
            }
        )

    winsorized: list[dict[str, Any]] = []
    for lower_q, upper_q in WINSOR_GRIDS:
        lower, upper = np.quantile(
            active, [lower_q, upper_q], method="linear"
        )
        adjusted = np.clip(active, lower, upper)
        winsorized.append(
            {
                "lower_quantile": lower_q,
                "upper_quantile": upper_q,
                "lower_bound": float(lower),
                "upper_bound": float(upper),
                "mean_difference": float(adjusted.mean()),
                "median_difference": float(np.median(adjusted)),
                "positive_fraction": float((adjusted > 0.0).mean()),
                "hac_frontier": _hac_frontier(adjusted),
            }
        )

    ranked_events = sorted(
        range(len(active)), key=lambda i: (-active[i], dates.iloc[i])
    )
    positive_sum = float(active[active > 0.0].sum())
    net_sum = float(active.sum())
    if math.isclose(positive_sum, 0.0, abs_tol=1e-15):
        _fail("robustness_positive_contribution_undefined", "正配對差總和為零")
    if math.isclose(net_sum, 0.0, abs_tol=1e-15):
        _fail("robustness_net_contribution_undefined", "淨配對差總和為零")
    tail_event_removals: list[dict[str, Any]] = []
    for count in TAIL_REMOVAL_COUNTS:
        removed_indices = ranked_events[:count]
        keep = np.ones(len(active), dtype=bool)
        keep[removed_indices] = False
        removed_values = active[removed_indices]
        tail_event_removals.append(
            {
                "removed_count": count,
                "removed_fraction": count / len(active),
                "removed_first_date": min(dates.iloc[i] for i in removed_indices).strftime("%Y-%m-%d"),
                "removed_last_date": max(dates.iloc[i] for i in removed_indices).strftime("%Y-%m-%d"),
                "removed_sum_difference": float(removed_values.sum()),
                "share_of_positive_sum": float(removed_values.sum()) / positive_sum,
                "share_of_net_sum": float(removed_values.sum()) / net_sum,
                **_subset_summary(active, dates, keep),
            }
        )

    remove_one = next(
        row for row in best_year_removals if row["removed_count"] == 1
    )
    remove_three = next(
        row for row in best_year_removals if row["removed_count"] == 3
    )
    winsor_one = next(
        row for row in winsorized if row["lower_quantile"] == 0.01
    )
    winsor_five = next(
        row for row in winsorized if row["lower_quantile"] == 0.05
    )
    winsor_one_nw4 = next(
        row for row in winsor_one["hac_frontier"] if row["lag"] == 4
    )
    winsor_five_nw4 = next(
        row for row in winsor_five["hac_frontier"] if row["lag"] == 4
    )
    positive_years = sum(row["mean_difference"] > 0.0 for row in year_rows)

    gates = [
        {
            "id": "calendar_cluster_t",
            "label": "曆年 cluster t 不低於 t(20) 5% 臨界值",
            "passed": calendar_cluster["t_stat"] >= CLUSTER_T_CRITICAL,
        },
        {
            "id": "block_bootstrap_lower_bound",
            "label": "52-event block bootstrap 2.5% 分位數大於零",
            "passed": bootstrap["mean_difference_quantiles"]["p025"] > 0.0,
        },
        {
            "id": "positive_calendar_years",
            "label": "至少 14/21 個曆年平均差為正",
            "passed": positive_years >= 14,
        },
        {
            "id": "all_epochs_positive",
            "label": "五個固定市場時段平均差全為正",
            "passed": all(row["mean_difference"] > 0.0 for row in epoch_rows),
        },
        {
            "id": "remove_best_year",
            "label": "刪除最佳一年後平均為正且 NW t 不低於 1.96",
            "passed": (
                remove_one["mean_difference"] > 0.0
                and remove_one["newey_west_lag4"]["t_stat"] >= 1.96
            ),
        },
        {
            "id": "remove_best_three_years",
            "label": "刪除最佳三年後平均為正且 NW t 不低於 1.96",
            "passed": (
                remove_three["mean_difference"] > 0.0
                and remove_three["newey_west_lag4"]["t_stat"] >= 1.96
            ),
        },
        {
            "id": "winsor_one_percent",
            "label": "1% 對稱 winsor 後平均為正且 NW t 不低於 1.96",
            "passed": (
                winsor_one["mean_difference"] > 0.0
                and winsor_one_nw4["t_stat"] >= 1.96
            ),
        },
        {
            "id": "winsor_five_percent",
            "label": "5% 對稱 winsor 後平均為正且 NW t 不低於 1.96",
            "passed": (
                winsor_five["mean_difference"] > 0.0
                and winsor_five_nw4["t_stat"] >= 1.96
            ),
        },
    ]
    gate_summary = {
        "passed": sum(int(row["passed"]) for row in gates),
        "total": len(gates),
        "all_passed": all(row["passed"] for row in gates),
    }

    controls = [
        {"id": "01", "label": "輸入 SHA", "passed": integrity["input_sha256"] == INPUT_SHA256},
        {"id": "02", "label": "固定事件路徑", "passed": contract.event_path == EVENT_PATH},
        {"id": "03", "label": "固定 20 日期限", "passed": contract.horizon == HORIZON},
        {"id": "04", "label": "905 個事件", "passed": len(frame) == EXPECTED_EVENT_COUNT},
        {"id": "05", "label": "嚴格日期順序", "passed": bool(dates.is_monotonic_increasing and not dates.duplicated().any())},
        {"id": "06", "label": "逐事件配對 baseline", "passed": contract.paired_baseline},
        {"id": "07", "label": "成本不重扣", "passed": not contract.cost_double_counted},
        {"id": "08", "label": "四個 HAC lag", "passed": tuple(row["lag"] for row in hac_frontier) == HAC_LAGS},
        {"id": "09", "label": "21 個曆年 cluster", "passed": tuple(row["year"] for row in year_rows) == CALENDAR_YEARS},
        {"id": "10", "label": "五個固定時段", "passed": tuple(row["id"] for row in epoch_rows) == tuple(row[0] for row in EPOCHS)},
        {"id": "11", "label": "最佳 1／3 年刪除", "passed": tuple(row["removed_count"] for row in best_year_removals) == YEAR_REMOVAL_COUNTS},
        {"id": "12", "label": "兩個 winsor grid", "passed": tuple((row["lower_quantile"], row["upper_quantile"]) for row in winsorized) == WINSOR_GRIDS},
        {"id": "13", "label": "10／46 個極端事件刪除", "passed": tuple(row["removed_count"] for row in tail_event_removals) == TAIL_REMOVAL_COUNTS},
        {"id": "14", "label": "52／5,000／seed circular bootstrap", "passed": bool(bootstrap["block_length_events"] == BOOTSTRAP_BLOCK_LENGTH and bootstrap["paths"] == BOOTSTRAP_PATHS and bootstrap["seed"] == BOOTSTRAP_SEED and bootstrap["circular"])},
        {"id": "15", "label": "決策邊界", "passed": bool(not contract.paper_authorized and not contract.real_money_authorized)},
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
        },
        "input": {
            "path": INPUT_PATH,
            "sha256": integrity["input_sha256"],
            "event_path": EVENT_PATH,
            "event_series_sha256": integrity["event_series_sha256"],
            "events": len(frame),
            "first_signal_date": dates.iloc[0].strftime("%Y-%m-%d"),
            "last_signal_date": dates.iloc[-1].strftime("%Y-%m-%d"),
            "top_k": TOP_K,
            "holding_period_sessions": HORIZON,
            "embedded_round_trip_cost_bps_each_side": EMBEDDED_ROUND_TRIP_COST_BPS,
        },
        "observed": {
            "mean_selected_return": float(selected.mean()),
            "mean_eligible_equal_return": float(baseline.mean()),
            "mean_active_difference": float(active.mean()),
            "median_active_difference": float(np.median(active)),
            "positive_fraction": float((active > 0.0).mean()),
        },
        "hac_frontier": hac_frontier,
        "calendar_cluster": calendar_cluster,
        "calendar_years": year_rows,
        "positive_calendar_years": positive_years,
        "epochs": epoch_rows,
        "leave_one_year_out": leave_one_year_out,
        "best_year_ranking": ranked_years,
        "best_year_removals": best_year_removals,
        "winsorized": winsorized,
        "tail_event_removals": tail_event_removals,
        "sign_test": _sign_test(active),
        "moving_block_bootstrap": bootstrap,
        "gates": gates,
        "gate_summary": gate_summary,
        "controls": controls,
        "control_summary": control_summary,
        "attacks": attacks,
        "attack_summary": attack_summary,
        "research_role": "survivor_cohort_temporal_tail_falsification_only",
        "decision": {
            "not_rejected_by_round23": gate_summary["all_passed"],
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
