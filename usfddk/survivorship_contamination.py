from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .metrics import newey_west_mean_test

SCHEMA_VERSION = 1
RESEARCH_ROUND = 22
PROTOCOL_PATH = "docs/SHORT_TERM_SURVIVORSHIP_CONTAMINATION_PROTOCOL.md"
PROTOCOL_SHA256 = "3977eae15de0a46607d7358ddb25d5988dab58d25ceb9f225ae229d986ff3ddd"
PROTOCOL_COMMIT = "6c0c17570cebe408d841f823a819019b11211ffb"
SCHEMA_REPAIR_PROTOCOL_PATH = (
    "docs/SHORT_TERM_SURVIVORSHIP_CONTAMINATION_SCHEMA_REPAIR_PROTOCOL.md"
)
SCHEMA_REPAIR_PROTOCOL_SHA256 = (
    "68522a1f50d24f7d4234052bceb77b140e745dacfd29eb85ced17feaf540e4a5"
)
SCHEMA_REPAIR_PROTOCOL_COMMIT = "ebdd44bb3cec1de5c29e31b7cab626af4b84f5cb"
INPUT_PATH = "artifacts/short_term_high_return_validation.json"
INPUT_SHA256 = "fa2463cc8273a316e4a98428767b695eb85c74e9ac75c47b5ca34592102979e8"
HORIZON = 20
EXPECTED_EVENT_COUNT = 905
TOP_K = 7
EXIT_RETURN_GRID = (-0.25, -0.50, -0.80, -1.00)
CONTAMINATION_RATE_GRID = (0.005, 0.01, 0.02, 0.05, 0.10)
PRIMARY_EXIT_RETURN = -0.50
PRIMARY_CONTAMINATION_RATE = 0.02
SIMULATION_COUNT = 2_000
SIMULATION_SEED = 20_260_804
NEWEY_WEST_LAG = 4
PERIODS_PER_YEAR = 52
FIRST_HALF_END = pd.Timestamp("2016-07-29")
SECOND_HALF_START = pd.Timestamp("2016-08-01")


class SurvivorshipStressError(ValueError):
    """Fail-closed stress-test error with a stable semantic code."""

    def __init__(self, code: str, detail: str):
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}")


def _fail(code: str, detail: str) -> None:
    raise SurvivorshipStressError(code, detail)


@dataclass(frozen=True)
class FrozenStressContract:
    input_sha256: str = INPUT_SHA256
    horizon: int = HORIZON
    expected_event_count: int = EXPECTED_EVENT_COUNT
    top_k: int = TOP_K
    exit_return_grid: tuple[float, ...] = EXIT_RETURN_GRID
    contamination_rate_grid: tuple[float, ...] = CONTAMINATION_RATE_GRID
    primary_cell: tuple[float, float] = (
        PRIMARY_EXIT_RETURN,
        PRIMARY_CONTAMINATION_RATE,
    )
    simulation_count: int = SIMULATION_COUNT
    simulation_seed: int = SIMULATION_SEED
    common_random_numbers: bool = True
    adjust_eligible_baseline: bool = True
    newey_west_lag: int = NEWEY_WEST_LAG


FROZEN_CONTRACT = FrozenStressContract()


def validate_stress_contract(contract: FrozenStressContract) -> None:
    checks: tuple[tuple[bool, str, str], ...] = (
        (
            contract.input_sha256 == INPUT_SHA256,
            "stress_input_hash_mismatch",
            "輸入 SHA-256 並非凍結版本",
        ),
        (
            contract.horizon == HORIZON,
            "stress_horizon_not_frozen",
            "主要持有期必須維持 20 日",
        ),
        (
            contract.expected_event_count == EXPECTED_EVENT_COUNT,
            "stress_event_count_mismatch",
            "事件數契約必須維持 905",
        ),
        (
            contract.top_k == TOP_K,
            "stress_top_k_not_frozen",
            "Top-K 必須維持 7",
        ),
        (
            contract.exit_return_grid == EXIT_RETURN_GRID,
            "stress_exit_grid_not_frozen",
            "退出回報壓力格漂移",
        ),
        (
            contract.contamination_rate_grid == CONTAMINATION_RATE_GRID,
            "stress_frequency_grid_not_frozen",
            "污染率壓力格漂移",
        ),
        (
            contract.primary_cell
            == (PRIMARY_EXIT_RETURN, PRIMARY_CONTAMINATION_RATE),
            "stress_primary_cell_not_frozen",
            "主要壓力格漂移",
        ),
        (
            contract.simulation_count == SIMULATION_COUNT,
            "stress_simulation_count_not_frozen",
            "Monte Carlo 路徑數漂移",
        ),
        (
            contract.simulation_seed == SIMULATION_SEED,
            "stress_seed_not_frozen",
            "Monte Carlo 種子漂移",
        ),
        (
            contract.common_random_numbers,
            "stress_common_random_numbers_disabled",
            "所有壓力格必須共用亂數",
        ),
        (
            contract.adjust_eligible_baseline,
            "stress_baseline_not_adjusted",
            "公平基準必須加入同一缺失股份",
        ),
        (
            contract.newey_west_lag == NEWEY_WEST_LAG,
            "stress_newey_west_lag_not_frozen",
            "Newey-West lag 必須維持 4",
        ),
    )
    for passed, code, detail in checks:
        if not passed:
            _fail(code, detail)


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_frozen_events(
    root: Path, contract: FrozenStressContract
) -> tuple[pd.DataFrame, dict[str, str]]:
    protocol_path = root / PROTOCOL_PATH
    if _sha256_file(protocol_path) != PROTOCOL_SHA256:
        _fail("stress_protocol_mismatch", "第 22 輪協議 SHA-256 漂移")
    repair_path = root / SCHEMA_REPAIR_PROTOCOL_PATH
    if _sha256_file(repair_path) != SCHEMA_REPAIR_PROTOCOL_SHA256:
        _fail("stress_protocol_mismatch", "第 22 輪 schema repair 協議 SHA-256 漂移")

    input_path = root / INPUT_PATH
    input_sha256 = _sha256_file(input_path)
    if input_sha256 != contract.input_sha256:
        _fail("stress_input_hash_mismatch", "短線訊號輸入 SHA-256 漂移")

    payload = json.loads(input_path.read_text(encoding="utf-8"))
    try:
        events = payload["taiwan_reference_signal_layer_diagnostic"]["horizons"][
            str(contract.horizon)
        ]["event_series"]
    except (KeyError, TypeError) as exc:
        _fail("stress_horizon_not_frozen", f"找不到固定 20 日事件：{exc}")

    frame = pd.DataFrame(events)[
        ["signal_date", "eligible_count", "top7_return", "eligible_equal_return"]
    ].copy()
    frame["signal_date"] = pd.to_datetime(frame["signal_date"], errors="raise")
    for column in ("eligible_count", "top7_return", "eligible_equal_return"):
        frame[column] = pd.to_numeric(frame[column], errors="raise")

    if len(frame) != contract.expected_event_count:
        _fail("stress_event_count_mismatch", "輸入事件數與凍結契約不同")
    if (
        not frame["signal_date"].is_monotonic_increasing
        or frame["signal_date"].duplicated().any()
    ):
        _fail("stress_event_order_mismatch", "訊號日期排序或唯一性漂移")
    numeric = frame[["eligible_count", "top7_return", "eligible_equal_return"]]
    if not np.isfinite(numeric.to_numpy(dtype=float)).all():
        _fail("stress_event_values_invalid", "事件含非有限數值")
    if (frame["eligible_count"] < contract.top_k).any():
        _fail("stress_event_values_invalid", "合資格股份少於固定 Top-7")

    event_payload = frame.assign(
        signal_date=frame["signal_date"].dt.strftime("%Y-%m-%d")
    ).to_dict(orient="records")
    event_sha256 = hashlib.sha256(
        json.dumps(event_payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return frame, {
        "input_sha256": input_sha256,
        "protocol_sha256": _sha256_file(protocol_path),
        "schema_repair_protocol_sha256": _sha256_file(repair_path),
        "event_series_sha256": event_sha256,
    }


def _nw(series: np.ndarray) -> dict[str, float]:
    result = newey_west_mean_test(
        pd.Series(series),
        max_lag=NEWEY_WEST_LAG,
        periods_per_year=PERIODS_PER_YEAR,
    )
    return {
        "mean_difference": float(result["mean_daily"]),
        "annualized_event_difference": float(result["annualized"]),
        "t_stat": float(result["t_stat"]),
        "lag": int(result["lag"]),
    }


def contamination_delta(
    selected: np.ndarray,
    baseline: np.ndarray,
    eligible_count: np.ndarray,
    *,
    exit_return: float,
    top_k: int = TOP_K,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    selected_adjustment = (exit_return - selected) / top_k
    baseline_adjustment = (exit_return - baseline) / (eligible_count + 1.0)
    return (
        selected_adjustment,
        baseline_adjustment,
        selected_adjustment - baseline_adjustment,
    )


def _nw_break_even_rate(active: np.ndarray, delta: np.ndarray) -> float | None:
    for step in range(10_001):
        rate = step / 10_000.0
        if _nw(active + rate * delta)["t_stat"] < 1.96:
            return rate
    return None


def _mean_break_even_rate(active: np.ndarray, delta: np.ndarray) -> float | None:
    mean_delta = float(delta.mean())
    if mean_delta >= 0.0:
        return None
    return float(active.mean() / -mean_delta)


def _monte_carlo_summary(
    active: np.ndarray,
    delta: np.ndarray,
    mask: np.ndarray,
    first_mask: np.ndarray,
    second_mask: np.ndarray,
) -> dict[str, Any]:
    path_means = float(active.mean()) + mask @ delta / len(active)
    first_means = (
        float(active[first_mask].mean())
        + mask[:, first_mask] @ delta[first_mask] / int(first_mask.sum())
    )
    second_means = (
        float(active[second_mask].mean())
        + mask[:, second_mask] @ delta[second_mask] / int(second_mask.sum())
    )
    low, median, high = np.quantile(path_means, [0.025, 0.5, 0.975])
    return {
        "paths": int(mask.shape[0]),
        "mean_difference_quantiles": {
            "p025": float(low),
            "p500": float(median),
            "p975": float(high),
        },
        "positive_mean_fraction": float((path_means > 0.0).mean()),
        "both_halves_positive_fraction": float(
            ((first_means > 0.0) & (second_means > 0.0)).mean()
        ),
    }


def _contract_attacks() -> list[tuple[str, str, str, Callable[[FrozenStressContract], FrozenStressContract]]]:
    return [
        (
            "01",
            "輸入 SHA 漂移",
            "stress_input_hash_mismatch",
            lambda c: replace(c, input_sha256="0" * 64),
        ),
        (
            "02",
            "改用 10 日持有期",
            "stress_horizon_not_frozen",
            lambda c: replace(c, horizon=10),
        ),
        (
            "03",
            "事件數漂移",
            "stress_event_count_mismatch",
            lambda c: replace(c, expected_event_count=904),
        ),
        (
            "04",
            "Top-K 改為 10",
            "stress_top_k_not_frozen",
            lambda c: replace(c, top_k=10),
        ),
        (
            "05",
            "刪除 -100% 退出格",
            "stress_exit_grid_not_frozen",
            lambda c: replace(c, exit_return_grid=(-0.25, -0.50, -0.80)),
        ),
        (
            "06",
            "刪除 10% 污染格",
            "stress_frequency_grid_not_frozen",
            lambda c: replace(c, contamination_rate_grid=(0.005, 0.01, 0.02, 0.05)),
        ),
        (
            "07",
            "主要格改為較輕衝擊",
            "stress_primary_cell_not_frozen",
            lambda c: replace(c, primary_cell=(-0.25, 0.01)),
        ),
        (
            "08",
            "減少 Monte Carlo 路徑",
            "stress_simulation_count_not_frozen",
            lambda c: replace(c, simulation_count=1_000),
        ),
        (
            "09",
            "隨機種子漂移",
            "stress_seed_not_frozen",
            lambda c: replace(c, simulation_seed=1),
        ),
        (
            "10",
            "每格獨立重抽亂數",
            "stress_common_random_numbers_disabled",
            lambda c: replace(c, common_random_numbers=False),
        ),
        (
            "11",
            "只打擊候選不修正 baseline",
            "stress_baseline_not_adjusted",
            lambda c: replace(c, adjust_eligible_baseline=False),
        ),
        (
            "12",
            "Newey-West lag 漂移",
            "stress_newey_west_lag_not_frozen",
            lambda c: replace(c, newey_west_lag=1),
        ),
    ]


def run_attack_harness() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for attack_id, label, expected_code, mutate in _contract_attacks():
        observed_code: str | None = None
        try:
            validate_stress_contract(mutate(FROZEN_CONTRACT))
        except SurvivorshipStressError as exc:
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


def run_survivorship_contamination_stress(root: str | Path) -> dict[str, Any]:
    root_path = Path(root).resolve()
    contract = FROZEN_CONTRACT
    validate_stress_contract(contract)
    frame, integrity = _load_frozen_events(root_path, contract)

    selected = frame["top7_return"].to_numpy(dtype=float)
    baseline = frame["eligible_equal_return"].to_numpy(dtype=float)
    eligible_count = frame["eligible_count"].to_numpy(dtype=float)
    active = selected - baseline
    dates = frame["signal_date"]
    first_mask = (dates <= FIRST_HALF_END).to_numpy(dtype=bool)
    second_mask = (dates >= SECOND_HALF_START).to_numpy(dtype=bool)

    rng = np.random.default_rng(contract.simulation_seed)
    uniforms = rng.random((contract.simulation_count, len(frame)))
    uniform_sha256 = hashlib.sha256(uniforms.tobytes()).hexdigest()
    masks = {
        rate: uniforms < rate for rate in contract.contamination_rate_grid
    }

    observed = {
        "events": int(len(frame)),
        "first_signal_date": dates.iloc[0].strftime("%Y-%m-%d"),
        "last_signal_date": dates.iloc[-1].strftime("%Y-%m-%d"),
        "mean_selected_return": float(selected.mean()),
        "mean_eligible_equal_return": float(baseline.mean()),
        "mean_active_difference": float(active.mean()),
        "median_active_difference": float(np.median(active)),
        "active_win_fraction": float((active > 0.0).mean()),
        "newey_west": _nw(active),
        "fixed_halves": {
            "first_mean_difference": float(active[first_mask].mean()),
            "second_mean_difference": float(active[second_mask].mean()),
        },
    }

    results: list[dict[str, Any]] = []
    break_even: list[dict[str, Any]] = []
    first_adjustments: tuple[np.ndarray, np.ndarray] | None = None
    for exit_return in contract.exit_return_grid:
        selected_adjustment, baseline_adjustment, delta = contamination_delta(
            selected,
            baseline,
            eligible_count,
            exit_return=exit_return,
            top_k=contract.top_k,
        )
        if first_adjustments is None:
            first_adjustments = (selected_adjustment, baseline_adjustment)
        mean_break_even = _mean_break_even_rate(active, delta)
        nw_break_even = _nw_break_even_rate(active, delta)
        break_even.append(
            {
                "exit_return": float(exit_return),
                "mean_zero_contamination_rate": mean_break_even,
                "mean_zero_within_zero_to_one": bool(
                    mean_break_even is not None and 0.0 <= mean_break_even <= 1.0
                ),
                "newey_west_below_1_96_contamination_rate": nw_break_even,
            }
        )
        for rate in contract.contamination_rate_grid:
            expected = active + rate * delta
            nw = _nw(expected)
            monte_carlo = _monte_carlo_summary(
                active,
                delta,
                masks[rate],
                first_mask,
                second_mask,
            )
            results.append(
                {
                    "exit_return": float(exit_return),
                    "contamination_rate": float(rate),
                    "expected": {
                        "mean_difference": float(expected.mean()),
                        "median_difference": float(np.median(expected)),
                        "win_fraction": float((expected > 0.0).mean()),
                        "newey_west": nw,
                        "fixed_halves": {
                            "first_mean_difference": float(expected[first_mask].mean()),
                            "second_mean_difference": float(expected[second_mask].mean()),
                        },
                    },
                    "monte_carlo": monte_carlo,
                }
            )

    primary = next(
        row
        for row in results
        if row["exit_return"] == PRIMARY_EXIT_RETURN
        and row["contamination_rate"] == PRIMARY_CONTAMINATION_RATE
    )
    primary_gates = [
        {
            "id": "expected_mean_positive",
            "label": "期望平均配對差為正",
            "passed": primary["expected"]["mean_difference"] > 0.0,
        },
        {
            "id": "expected_newey_west",
            "label": "期望序列 NW t 不低於 1.96",
            "passed": primary["expected"]["newey_west"]["t_stat"] >= 1.96,
        },
        {
            "id": "monte_carlo_positive",
            "label": "Monte Carlo 正平均路徑不少於 95%",
            "passed": primary["monte_carlo"]["positive_mean_fraction"] >= 0.95,
        },
        {
            "id": "monte_carlo_halves",
            "label": "Monte Carlo 前後十年同正不少於 90%",
            "passed": primary["monte_carlo"]["both_halves_positive_fraction"] >= 0.90,
        },
        {
            "id": "expected_halves",
            "label": "期望前後十年平均配對差均為正",
            "passed": (
                primary["expected"]["fixed_halves"]["first_mean_difference"] > 0.0
                and primary["expected"]["fixed_halves"]["second_mean_difference"] > 0.0
            ),
        },
    ]
    primary_gate_summary = {
        "passed": sum(int(row["passed"]) for row in primary_gates),
        "total": len(primary_gates),
        "all_passed": all(row["passed"] for row in primary_gates),
    }

    assert first_adjustments is not None
    selected_adjustment, baseline_adjustment = first_adjustments
    controls = [
        {"id": "01", "label": "輸入 SHA", "passed": integrity["input_sha256"] == INPUT_SHA256},
        {"id": "02", "label": "固定 20 日期限", "passed": contract.horizon == HORIZON},
        {"id": "03", "label": "905 個事件", "passed": len(frame) == EXPECTED_EVENT_COUNT},
        {"id": "04", "label": "固定 Top-7", "passed": contract.top_k == TOP_K},
        {"id": "05", "label": "四個退出回報", "passed": contract.exit_return_grid == EXIT_RETURN_GRID},
        {"id": "06", "label": "五個污染率", "passed": contract.contamination_rate_grid == CONTAMINATION_RATE_GRID},
        {"id": "07", "label": "固定主要格", "passed": contract.primary_cell == (PRIMARY_EXIT_RETURN, PRIMARY_CONTAMINATION_RATE)},
        {"id": "08", "label": "2,000 條路徑", "passed": uniforms.shape == (SIMULATION_COUNT, EXPECTED_EVENT_COUNT)},
        {"id": "09", "label": "固定隨機種子", "passed": contract.simulation_seed == SIMULATION_SEED},
        {"id": "10", "label": "共用亂數", "passed": bool(contract.common_random_numbers and uniform_sha256)},
        {
            "id": "11",
            "label": "候選與基準同步調整",
            "passed": bool(
                contract.adjust_eligible_baseline
                and np.any(selected_adjustment != 0.0)
                and np.any(baseline_adjustment != 0.0)
            ),
        },
        {"id": "12", "label": "固定 NW lag 4", "passed": contract.newey_west_lag == NEWEY_WEST_LAG},
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

    if not control_summary["all_passed"] or not attack_summary["all_rejected"]:
        _fail("stress_validation_incomplete", "控制或替代攻擊未完整通過")

    return {
        "schema_version": SCHEMA_VERSION,
        "research_round": RESEARCH_ROUND,
        "status": (
            "synthetic_primary_stress_survived_not_investable"
            if primary_gate_summary["all_passed"]
            else "synthetic_primary_stress_failed_not_investable"
        ),
        "research_role": "survivorship_bias_sensitivity_only",
        "protocol": {
            "path": PROTOCOL_PATH,
            "sha256": PROTOCOL_SHA256,
            "commit": PROTOCOL_COMMIT,
            "frozen_before_first_stress_calculation": True,
        },
        "schema_repair_protocol": {
            "path": SCHEMA_REPAIR_PROTOCOL_PATH,
            "sha256": SCHEMA_REPAIR_PROTOCOL_SHA256,
            "commit": SCHEMA_REPAIR_PROTOCOL_COMMIT,
            "repair_scope": "derive_signal_date_boundaries_from_hash_bound_event_series",
            "stress_results_present_at_freeze": False,
        },
        "input": {
            "path": INPUT_PATH,
            **integrity,
            "horizon": HORIZON,
            "event_count": int(len(frame)),
        },
        "frozen_contract": {
            "top_k": TOP_K,
            "exit_return_grid": list(EXIT_RETURN_GRID),
            "contamination_rate_grid": list(CONTAMINATION_RATE_GRID),
            "primary_cell": {
                "exit_return": PRIMARY_EXIT_RETURN,
                "contamination_rate": PRIMARY_CONTAMINATION_RATE,
            },
            "simulation_count": SIMULATION_COUNT,
            "simulation_seed": SIMULATION_SEED,
            "common_random_numbers_sha256": uniform_sha256,
            "newey_west_lag": NEWEY_WEST_LAG,
            "candidate_and_baseline_both_adjusted": True,
        },
        "observed_signal": observed,
        "break_even_by_exit_return": break_even,
        "stress_grid": results,
        "primary_cell": primary,
        "primary_gates": primary_gates,
        "primary_gate_summary": primary_gate_summary,
        "controls": controls,
        "control_summary": control_summary,
        "attacks": attacks,
        "attack_summary": attack_summary,
        "formal_readiness": {"passed": 1, "total": 18},
        "formal_stock_backtest_completed": False,
        "strategy_run_count": 0,
        "paper": {
            "authorized": False,
            "state": "all_cash",
            "positions": 0,
            "allocation_usd": 0,
        },
        "reader_capital_example_usd": 1_000,
        "real_money_action_usd": 0,
        "decision": (
            "合成缺失退出壓力只量化現時正面訊號的脆弱度；無論通過或失敗，"
            "均不修復 point-in-time／退市數據缺口，不建立 Paper 或實金持倉。"
        ),
    }
