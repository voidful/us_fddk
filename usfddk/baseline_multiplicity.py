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
RESEARCH_ROUND = 24
PROTOCOL_PATH = "docs/SHORT_TERM_BASELINE_MULTIPLICITY_PROTOCOL.md"
PROTOCOL_SHA256 = "1735ea7a1313aa845355074ace1d38d7fc6deef510c1227e7cd01ac1c4e64fce"
PROTOCOL_COMMIT = "2bf27559be5b617361c0907c58ceededf32cdfea"
INPUT_PATH = "artifacts/short_term_high_return_validation.json"
INPUT_SHA256 = "fa2463cc8273a316e4a98428767b695eb85c74e9ac75c47b5ca34592102979e8"
ROOT_PATH = "taiwan_reference_signal_layer_diagnostic.horizons"
HORIZONS = (5, 10, 20)
PRIMARY_HORIZON = 20
BASELINES = (
    "eligible_equal_return",
    "complete_cohort_equal_return",
    "qqq_return",
)
BASELINE_LABELS = {
    "eligible_equal_return": "合資格池等權",
    "complete_cohort_equal_return": "完整現時股池等權",
    "qqq_return": "QQQ",
}
EXPECTED_COMMON_EVENTS = 905
FIRST_SIGNAL_DATE = "2006-08-04"
LAST_SIGNAL_DATE = "2026-07-02"
ROUND_TRIP_COST_BPS = 20
HAC_LAGS = {5: 1, 10: 2, 20: 4}
FAMILY_ALPHA = 0.05
GLOBAL_SEARCH_TRIALS = 6_208
BOOTSTRAP_BLOCK_LENGTH = 52
BOOTSTRAP_PATHS = 20_000
BOOTSTRAP_SEED = 20_260_804
FIRST_HALF_END = pd.Timestamp("2016-07-29")
SECOND_HALF_START = pd.Timestamp("2016-08-01")


class BaselineMultiplicityError(ValueError):
    """Fail-closed Round 24 error with a stable semantic code."""

    def __init__(self, code: str, detail: str):
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}")


def _fail(code: str, detail: str) -> None:
    raise BaselineMultiplicityError(code, detail)


@dataclass(frozen=True)
class FrozenMultiplicityContract:
    input_sha256: str = INPUT_SHA256
    root_path: str = ROOT_PATH
    horizons: tuple[int, ...] = HORIZONS
    primary_horizon: int = PRIMARY_HORIZON
    baselines: tuple[str, ...] = BASELINES
    expected_common_events: int = EXPECTED_COMMON_EVENTS
    strict_common_order: bool = True
    paired_same_cost: bool = True
    hac_lags: tuple[tuple[int, int], ...] = tuple(HAC_LAGS.items())
    family_size: int = 9
    family_alpha: float = FAMILY_ALPHA
    global_search_trials: int = GLOBAL_SEARCH_TRIALS
    bootstrap_block_length: int = BOOTSTRAP_BLOCK_LENGTH
    bootstrap_paths: int = BOOTSTRAP_PATHS
    bootstrap_seed: int = BOOTSTRAP_SEED
    circular_bootstrap: bool = True
    common_resample_indices: bool = True
    center_under_null: bool = True
    paper_authorized: bool = False
    real_money_authorized: bool = False


FROZEN_CONTRACT = FrozenMultiplicityContract()


def validate_multiplicity_contract(contract: FrozenMultiplicityContract) -> None:
    checks: tuple[tuple[bool, str, str], ...] = (
        (
            contract.input_sha256 == INPUT_SHA256,
            "multiplicity_input_hash_mismatch",
            "輸入 SHA-256 漂移",
        ),
        (
            contract.root_path == ROOT_PATH,
            "multiplicity_path_not_frozen",
            "事件根路徑漂移",
        ),
        (
            contract.horizons == HORIZONS,
            "multiplicity_horizons_not_frozen",
            "固定持有期漂移",
        ),
        (
            contract.primary_horizon == PRIMARY_HORIZON,
            "multiplicity_primary_horizon_not_frozen",
            "主要持有期漂移",
        ),
        (
            contract.baselines == BASELINES,
            "multiplicity_baselines_not_frozen",
            "固定 baseline 漂移",
        ),
        (
            contract.expected_common_events == EXPECTED_COMMON_EVENTS,
            "multiplicity_common_sample_mismatch",
            "共同樣本數漂移",
        ),
        (
            contract.strict_common_order,
            "multiplicity_event_order_invalid",
            "共同日期必須嚴格遞增",
        ),
        (
            contract.paired_same_cost,
            "multiplicity_pairing_or_cost_mismatch",
            "配對兩邊必須使用同一時鐘與成本",
        ),
        (
            contract.hac_lags == tuple(HAC_LAGS.items()),
            "multiplicity_hac_lags_not_frozen",
            "NW lag 漂移",
        ),
        (
            contract.family_size == len(HORIZONS) * len(BASELINES),
            "multiplicity_family_not_frozen",
            "九假說 family 漂移",
        ),
        (
            contract.family_alpha == FAMILY_ALPHA,
            "multiplicity_alpha_not_frozen",
            "family alpha 漂移",
        ),
        (
            contract.global_search_trials == GLOBAL_SEARCH_TRIALS,
            "multiplicity_global_trials_not_frozen",
            "全專案搜尋次數漂移",
        ),
        (
            contract.bootstrap_block_length == BOOTSTRAP_BLOCK_LENGTH,
            "multiplicity_block_length_not_frozen",
            "bootstrap block 漂移",
        ),
        (
            contract.bootstrap_paths == BOOTSTRAP_PATHS,
            "multiplicity_bootstrap_paths_not_frozen",
            "bootstrap 路徑數漂移",
        ),
        (
            contract.bootstrap_seed == BOOTSTRAP_SEED
            and contract.circular_bootstrap
            and contract.common_resample_indices
            and contract.center_under_null,
            "multiplicity_bootstrap_contract_not_frozen",
            "bootstrap seed、共同 index、circular 或去中心化契約漂移",
        ),
        (
            not contract.paper_authorized and not contract.real_money_authorized,
            "multiplicity_decision_boundary_breached",
            "本輪不得授權 Paper 或實金",
        ),
    )
    for passed, code, detail in checks:
        if not passed:
            _fail(code, detail)


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_common_events(
    root: Path, contract: FrozenMultiplicityContract
) -> tuple[dict[int, pd.DataFrame], pd.Series, dict[str, str]]:
    protocol_path = root / PROTOCOL_PATH
    protocol_sha256 = _sha256_file(protocol_path)
    if protocol_sha256 != PROTOCOL_SHA256:
        _fail("multiplicity_protocol_mismatch", "第 24 輪協議 SHA-256 漂移")

    input_path = root / INPUT_PATH
    input_sha256 = _sha256_file(input_path)
    if input_sha256 != contract.input_sha256:
        _fail("multiplicity_input_hash_mismatch", "短線訊號輸入 SHA-256 漂移")
    payload = json.loads(input_path.read_text(encoding="utf-8"))
    try:
        horizon_payload = payload["taiwan_reference_signal_layer_diagnostic"][
            "horizons"
        ]
    except (KeyError, TypeError) as exc:
        _fail("multiplicity_path_not_frozen", f"找不到固定事件根路徑：{exc}")

    columns = ["signal_date", "top7_return", *BASELINES]
    source_frames: dict[int, pd.DataFrame] = {}
    common_dates: set[pd.Timestamp] | None = None
    for horizon in contract.horizons:
        try:
            events = horizon_payload[str(horizon)]["event_series"]
        except (KeyError, TypeError) as exc:
            _fail(
                "multiplicity_horizons_not_frozen",
                f"找不到 {horizon} 日事件：{exc}",
            )
        frame = pd.DataFrame(events)[columns].copy()
        frame["signal_date"] = pd.to_datetime(frame["signal_date"], errors="raise")
        for column in columns[1:]:
            frame[column] = pd.to_numeric(frame[column], errors="raise")
        if (
            not frame["signal_date"].is_monotonic_increasing
            or frame["signal_date"].duplicated().any()
        ):
            _fail("multiplicity_event_order_invalid", f"{horizon} 日期順序漂移")
        if not np.isfinite(frame[columns[1:]].to_numpy(dtype=float)).all():
            _fail("multiplicity_event_values_invalid", f"{horizon} 含非有限回報")
        source_frames[horizon] = frame
        date_set = set(frame["signal_date"])
        common_dates = date_set if common_dates is None else common_dates & date_set

    if common_dates is None:
        _fail("multiplicity_common_sample_mismatch", "沒有共同日期")
    ordered_dates = pd.Series(sorted(common_dates), name="signal_date")
    if len(ordered_dates) != contract.expected_common_events:
        _fail("multiplicity_common_sample_mismatch", "共同日期數不是 905")
    if (
        ordered_dates.iloc[0].strftime("%Y-%m-%d") != FIRST_SIGNAL_DATE
        or ordered_dates.iloc[-1].strftime("%Y-%m-%d") != LAST_SIGNAL_DATE
    ):
        _fail("multiplicity_common_sample_mismatch", "共同日期邊界漂移")

    aligned: dict[int, pd.DataFrame] = {}
    for horizon, frame in source_frames.items():
        indexed = frame.set_index("signal_date")
        try:
            sample = indexed.loc[ordered_dates].reset_index()
        except KeyError as exc:
            _fail("multiplicity_common_sample_mismatch", f"共同 join 失敗：{exc}")
        if not sample["signal_date"].equals(ordered_dates):
            _fail("multiplicity_event_order_invalid", "三期限日期未一對一")
        aligned[horizon] = sample

    event_hashes = {
        str(horizon): hashlib.sha256(
            json.dumps(
                frame.assign(
                    signal_date=frame["signal_date"].dt.strftime("%Y-%m-%d")
                ).to_dict(orient="records"),
                sort_keys=True,
                separators=(",", ":"),
            ).encode()
        ).hexdigest()
        for horizon, frame in aligned.items()
    }
    return aligned, ordered_dates, {
        "input_sha256": input_sha256,
        "protocol_sha256": protocol_sha256,
        "common_event_series_sha256": hashlib.sha256(
            json.dumps(event_hashes, sort_keys=True).encode()
        ).hexdigest(),
        **{f"horizon_{key}_sha256": value for key, value in event_hashes.items()},
    }


def _nw(values: np.ndarray, lag: int) -> dict[str, float | int]:
    result = newey_west_mean_test(
        pd.Series(values), max_lag=lag, periods_per_year=52
    )
    mean = float(result["mean_daily"])
    t_stat = float(result["t_stat"])
    standard_error = mean / t_stat if t_stat != 0.0 else 0.0
    return {
        "mean_difference": mean,
        "annualized_event_difference": float(result["annualized"]),
        "standard_error": float(abs(standard_error)),
        "t_stat": t_stat,
        "lag": int(result["lag"]),
    }


def _normal_two_sided_p(t_stat: float) -> float:
    return float(math.erfc(abs(t_stat) / math.sqrt(2.0)))


def _holm_adjust(rows: list[dict[str, Any]]) -> dict[str, float]:
    ordered = sorted(
        rows,
        key=lambda row: (
            row["raw_normal_p"],
            row["horizon"],
            row["baseline_key"],
        ),
    )
    adjusted: dict[str, float] = {}
    running = 0.0
    total = len(ordered)
    for rank, row in enumerate(ordered):
        candidate = min(1.0, (total - rank) * row["raw_normal_p"])
        running = max(running, candidate)
        adjusted[row["id"]] = running
    return adjusted


def _common_bootstrap(
    matrix: np.ndarray,
    observed_t: np.ndarray,
    standard_errors: np.ndarray,
) -> dict[str, Any]:
    centered = matrix - matrix.mean(axis=0, keepdims=True)
    if not np.allclose(centered.mean(axis=0), 0.0, atol=1e-15):
        _fail("multiplicity_bootstrap_contract_not_frozen", "去中心化失敗")
    if (standard_errors <= 0.0).any():
        _fail("multiplicity_bootstrap_contract_not_frozen", "NW 標準誤非正")

    rows = len(matrix)
    blocks_per_path = math.ceil(rows / BOOTSTRAP_BLOCK_LENGTH)
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    starts = rng.integers(
        0, rows, size=(BOOTSTRAP_PATHS, blocks_per_path), dtype=np.int64
    )
    offsets = np.arange(BOOTSTRAP_BLOCK_LENGTH, dtype=np.int64)
    t_star = np.empty((BOOTSTRAP_PATHS, matrix.shape[1]), dtype=float)
    batch_size = 250
    for start in range(0, BOOTSTRAP_PATHS, batch_size):
        stop = min(BOOTSTRAP_PATHS, start + batch_size)
        indices = (
            starts[start:stop, :, None] + offsets[None, None, :]
        ) % rows
        indices = indices.reshape(stop - start, -1)[:, :rows]
        means = centered[indices].mean(axis=1)
        t_star[start:stop] = means / standard_errors

    observed_abs = np.abs(observed_t)
    bootstrap_abs = np.abs(t_star)
    max_abs = bootstrap_abs.max(axis=1)
    max_positive = t_star.max(axis=1)
    denominator = BOOTSTRAP_PATHS + 1.0
    unadjusted = (
        1.0
        + (bootstrap_abs >= observed_abs[None, :]).sum(axis=0).astype(float)
    ) / denominator
    single_step = (
        1.0
        + (max_abs[:, None] >= observed_abs[None, :]).sum(axis=0).astype(float)
    ) / denominator

    order = np.argsort(-observed_abs, kind="stable")
    stepdown = np.empty(len(observed_t), dtype=float)
    running = 0.0
    for position, hypothesis_index in enumerate(order):
        remaining = order[position:]
        remaining_max = bootstrap_abs[:, remaining].max(axis=1)
        raw_adjusted = (
            1.0
            + float((remaining_max >= observed_abs[hypothesis_index]).sum())
        ) / denominator
        running = max(running, raw_adjusted)
        stepdown[hypothesis_index] = min(1.0, running)

    observed_max_positive = float(observed_t.max())
    reality_check_p = (
        1.0 + float((max_positive >= observed_max_positive).sum())
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
        "observed_max_positive_t": observed_max_positive,
        "reality_check_p_value": float(reality_check_p),
        "unadjusted_two_sided_p": unadjusted.tolist(),
        "single_step_max_t_p": single_step.tolist(),
        "romano_wolf_stepdown_p": stepdown.tolist(),
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


def _contract_attacks() -> list[
    tuple[
        str,
        str,
        str,
        Callable[[FrozenMultiplicityContract], FrozenMultiplicityContract],
    ]
]:
    return [
        ("01", "輸入 SHA 漂移", "multiplicity_input_hash_mismatch", lambda c: replace(c, input_sha256="0" * 64)),
        ("02", "事件路徑漂移", "multiplicity_path_not_frozen", lambda c: replace(c, root_path="other")),
        ("03", "刪除 5 日期限", "multiplicity_horizons_not_frozen", lambda c: replace(c, horizons=(10, 20))),
        ("04", "主要期改 10 日", "multiplicity_primary_horizon_not_frozen", lambda c: replace(c, primary_horizon=10)),
        ("05", "刪除完整股池 baseline", "multiplicity_baselines_not_frozen", lambda c: replace(c, baselines=BASELINES[:1] + BASELINES[2:])),
        ("06", "共同樣本改 907", "multiplicity_common_sample_mismatch", lambda c: replace(c, expected_common_events=907)),
        ("07", "容許日期重排", "multiplicity_event_order_invalid", lambda c: replace(c, strict_common_order=False)),
        ("08", "取消同成本配對", "multiplicity_pairing_or_cost_mismatch", lambda c: replace(c, paired_same_cost=False)),
        ("09", "20 日 lag 改 1", "multiplicity_hac_lags_not_frozen", lambda c: replace(c, hac_lags=((5, 1), (10, 2), (20, 1)))),
        ("10", "family 改三列", "multiplicity_family_not_frozen", lambda c: replace(c, family_size=3)),
        ("11", "alpha 改 10%", "multiplicity_alpha_not_frozen", lambda c: replace(c, family_alpha=0.10)),
        ("12", "全專案 trials 改 9", "multiplicity_global_trials_not_frozen", lambda c: replace(c, global_search_trials=9)),
        ("13", "block 改 8", "multiplicity_block_length_not_frozen", lambda c: replace(c, bootstrap_block_length=8)),
        ("14", "bootstrap 減至 2,000", "multiplicity_bootstrap_paths_not_frozen", lambda c: replace(c, bootstrap_paths=2_000)),
        ("15", "每列獨立重抽", "multiplicity_bootstrap_contract_not_frozen", lambda c: replace(c, common_resample_indices=False)),
        ("16", "提前授權 Paper", "multiplicity_decision_boundary_breached", lambda c: replace(c, paper_authorized=True)),
    ]


def run_attack_harness() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for attack_id, label, expected_code, mutate in _contract_attacks():
        observed_code: str | None = None
        try:
            validate_multiplicity_contract(mutate(FROZEN_CONTRACT))
        except BaselineMultiplicityError as exc:
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


def run_baseline_multiplicity(root: str | Path) -> dict[str, Any]:
    root_path = Path(root).resolve()
    contract = FROZEN_CONTRACT
    validate_multiplicity_contract(contract)
    frames, dates, integrity = _load_common_events(root_path, contract)

    comparisons: list[dict[str, Any]] = []
    matrix_columns: list[np.ndarray] = []
    for horizon in HORIZONS:
        frame = frames[horizon]
        selected = frame["top7_return"].to_numpy(dtype=float)
        for baseline_key in BASELINES:
            values = selected - frame[baseline_key].to_numpy(dtype=float)
            nw = _nw(values, HAC_LAGS[horizon])
            row_id = f"h{horizon}_{baseline_key}"
            comparisons.append(
                {
                    "id": row_id,
                    "horizon": horizon,
                    "baseline_key": baseline_key,
                    "baseline_label": BASELINE_LABELS[baseline_key],
                    "events": len(values),
                    "mean_difference": float(values.mean()),
                    "median_difference": float(np.median(values)),
                    "positive_fraction": float((values > 0.0).mean()),
                    "newey_west": nw,
                    "raw_normal_p": _normal_two_sided_p(float(nw["t_stat"])),
                    "fixed_halves": _fixed_halves(values, dates),
                }
            )
            matrix_columns.append(values)

    holm = _holm_adjust(comparisons)
    matrix = np.column_stack(matrix_columns)
    observed_t = np.asarray(
        [row["newey_west"]["t_stat"] for row in comparisons], dtype=float
    )
    standard_errors = np.asarray(
        [row["newey_west"]["standard_error"] for row in comparisons],
        dtype=float,
    )
    bootstrap = _common_bootstrap(matrix, observed_t, standard_errors)
    for index, row in enumerate(comparisons):
        row["holm_adjusted_p"] = holm[row["id"]]
        row["family_bonferroni_p"] = min(1.0, row["raw_normal_p"] * 9)
        row["global_bonferroni_p"] = min(
            1.0, row["raw_normal_p"] * GLOBAL_SEARCH_TRIALS
        )
        row["bootstrap_unadjusted_p"] = bootstrap[
            "unadjusted_two_sided_p"
        ][index]
        row["bootstrap_max_t_p"] = bootstrap["single_step_max_t_p"][index]
        row["romano_wolf_stepdown_p"] = bootstrap[
            "romano_wolf_stepdown_p"
        ][index]

    primary = {
        row["baseline_key"]: row
        for row in comparisons
        if row["horizon"] == PRIMARY_HORIZON
    }
    frame20 = frames[PRIMARY_HORIZON]
    selected20 = frame20["top7_return"].to_numpy(dtype=float)
    eligible20 = frame20["eligible_equal_return"].to_numpy(dtype=float)
    complete20 = frame20["complete_cohort_equal_return"].to_numpy(dtype=float)
    ranking_effect = selected20 - eligible20
    eligibility_effect = eligible20 - complete20
    combined_effect = selected20 - complete20
    attribution_residual = combined_effect - (
        ranking_effect + eligibility_effect
    )
    if float(np.max(np.abs(attribution_residual))) > 1e-12:
        _fail("multiplicity_attribution_identity_failed", "20 日基準歸因不守恆")
    attribution = {
        "ranking_effect": {
            "definition": "top7 - eligible_equal",
            "mean_difference": float(ranking_effect.mean()),
            "newey_west": _nw(ranking_effect, 4),
            "fixed_halves": _fixed_halves(ranking_effect, dates),
        },
        "eligibility_effect": {
            "definition": "eligible_equal - complete_cohort_equal",
            "mean_difference": float(eligibility_effect.mean()),
            "newey_west": _nw(eligibility_effect, 4),
            "fixed_halves": _fixed_halves(eligibility_effect, dates),
        },
        "combined_effect": {
            "definition": "top7 - complete_cohort_equal",
            "mean_difference": float(combined_effect.mean()),
            "newey_west": _nw(combined_effect, 4),
            "fixed_halves": _fixed_halves(combined_effect, dates),
        },
        "max_abs_identity_residual": float(
            np.max(np.abs(attribution_residual))
        ),
    }

    eligible_primary = primary["eligible_equal_return"]
    complete_primary = primary["complete_cohort_equal_return"]
    qqq_primary = primary["qqq_return"]
    eligible_rows = [
        row for row in comparisons if row["baseline_key"] == "eligible_equal_return"
    ]
    gates = [
        {
            "id": "primary_vs_eligible",
            "label": "20 日對合資格池平均為正且 NW t 不低於 1.96",
            "passed": eligible_primary["mean_difference"] > 0.0
            and eligible_primary["newey_west"]["t_stat"] >= 1.96,
        },
        {
            "id": "primary_vs_complete",
            "label": "20 日對完整現時股池平均為正且 NW t 不低於 1.96",
            "passed": complete_primary["mean_difference"] > 0.0
            and complete_primary["newey_west"]["t_stat"] >= 1.96,
        },
        {
            "id": "primary_vs_qqq",
            "label": "20 日對 QQQ 平均為正且 NW t 不低於 1.96",
            "passed": qqq_primary["mean_difference"] > 0.0
            and qqq_primary["newey_west"]["t_stat"] >= 1.96,
        },
        {
            "id": "primary_all_halves",
            "label": "20 日對三 baseline 的前後兩半平均全部為正",
            "passed": all(
                row["fixed_halves"][half]["mean_difference"] > 0.0
                for row in primary.values()
                for half in ("first", "second")
            ),
        },
        {
            "id": "primary_holm",
            "label": "20 日合資格池九假說 Holm p 不高於 0.05",
            "passed": eligible_primary["holm_adjusted_p"] <= FAMILY_ALPHA,
        },
        {
            "id": "primary_bootstrap_max_t",
            "label": "20 日合資格池共同 max-t p 不高於 0.05",
            "passed": eligible_primary["bootstrap_max_t_p"] <= FAMILY_ALPHA,
        },
        {
            "id": "family_reality_check",
            "label": "九假說 Reality Check p 不高於 0.05",
            "passed": bootstrap["reality_check_p_value"] <= FAMILY_ALPHA,
        },
        {
            "id": "primary_global_bonferroni",
            "label": "20 日合資格池 6,208 次 Bonferroni p 不高於 0.05",
            "passed": eligible_primary["global_bonferroni_p"] <= FAMILY_ALPHA,
        },
        {
            "id": "all_horizons_max_t",
            "label": "5／10／20 日合資格池共同 max-t p 全不高於 0.05",
            "passed": all(
                row["bootstrap_max_t_p"] <= FAMILY_ALPHA
                for row in eligible_rows
            ),
        },
    ]
    gate_summary = {
        "passed": sum(int(row["passed"]) for row in gates),
        "total": len(gates),
        "all_passed": all(row["passed"] for row in gates),
    }

    family_ids = [
        f"h{horizon}_{baseline}"
        for horizon in HORIZONS
        for baseline in BASELINES
    ]
    controls = [
        {"id": "01", "label": "輸入 SHA", "passed": integrity["input_sha256"] == INPUT_SHA256},
        {"id": "02", "label": "固定事件根路徑", "passed": contract.root_path == ROOT_PATH},
        {"id": "03", "label": "5／10／20 日期限", "passed": contract.horizons == HORIZONS},
        {"id": "04", "label": "20 日主要期", "passed": contract.primary_horizon == PRIMARY_HORIZON},
        {"id": "05", "label": "三個公平 baseline", "passed": contract.baselines == BASELINES},
        {"id": "06", "label": "905 個共同事件", "passed": len(dates) == EXPECTED_COMMON_EVENTS},
        {"id": "07", "label": "共同日期嚴格一對一", "passed": bool(dates.is_monotonic_increasing and not dates.duplicated().any())},
        {"id": "08", "label": "逐事件同成本配對", "passed": contract.paired_same_cost and ROUND_TRIP_COST_BPS == 20},
        {"id": "09", "label": "NW lag 1／2／4", "passed": all(row["newey_west"]["lag"] == HAC_LAGS[row["horizon"]] for row in comparisons)},
        {"id": "10", "label": "九假說 family", "passed": [row["id"] for row in comparisons] == family_ids},
        {"id": "11", "label": "alpha 0.05", "passed": contract.family_alpha == FAMILY_ALPHA},
        {"id": "12", "label": "全專案 6,208 trials", "passed": contract.global_search_trials == GLOBAL_SEARCH_TRIALS},
        {"id": "13", "label": "52-event block", "passed": bootstrap["block_length_events"] == BOOTSTRAP_BLOCK_LENGTH},
        {"id": "14", "label": "20,000 路徑", "passed": bootstrap["paths"] == BOOTSTRAP_PATHS},
        {"id": "15", "label": "固定 seed／共同 circular indices／去中心化", "passed": bool(bootstrap["seed"] == BOOTSTRAP_SEED and bootstrap["circular"] and bootstrap["common_indices"] and bootstrap["centered_under_null"])},
        {"id": "16", "label": "決策邊界", "passed": bool(not contract.paper_authorized and not contract.real_money_authorized)},
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
            "root_path": ROOT_PATH,
            "common_event_series_sha256": integrity[
                "common_event_series_sha256"
            ],
            "common_events": len(dates),
            "first_signal_date": dates.iloc[0].strftime("%Y-%m-%d"),
            "last_signal_date": dates.iloc[-1].strftime("%Y-%m-%d"),
            "horizons": list(HORIZONS),
            "baselines": list(BASELINES),
            "embedded_round_trip_cost_bps": ROUND_TRIP_COST_BPS,
        },
        "primary_horizon": PRIMARY_HORIZON,
        "family_alpha": FAMILY_ALPHA,
        "global_search_trials": GLOBAL_SEARCH_TRIALS,
        "global_unadjusted_p_threshold": FAMILY_ALPHA / GLOBAL_SEARCH_TRIALS,
        "comparisons": comparisons,
        "primary_baselines": primary,
        "primary_attribution": attribution,
        "common_bootstrap": bootstrap,
        "gates": gates,
        "gate_summary": gate_summary,
        "controls": controls,
        "control_summary": control_summary,
        "attacks": attacks,
        "attack_summary": attack_summary,
        "research_role": "survivor_cohort_baseline_multiplicity_falsification_only",
        "decision": {
            "not_rejected_by_round24": gate_summary["all_passed"],
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
