from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from usfddk.data import load_snapshot
from usfddk.french_prior_return_research import (
    ReturnPath,
    _candidate_cost_break_even,
    _factor_regression,
    _metrics,
    _rolling_comparison,
    _slice_path,
    _stress_summary,
    apply_buy_and_hold_entry_cost,
    apply_full_reconstitution_cost,
    load_frozen_prior_return_data,
)
from usfddk.french_size_prior import (
    EQUAL_WEIGHTED_MONTHLY_MARKER,
    SIZE_PRIOR_COLUMNS,
    VALUE_WEIGHTED_MONTHLY_MARKER,
    extract_single_csv,
    parse_size_prior_monthly_table,
    sha256_file,
)
from usfddk.metrics import newey_west_mean_test
from usfddk.validation import (
    deflated_sharpe_ratio,
    probabilistic_sharpe_ratio,
    probability_of_backtest_overfitting,
)

SCHEMA_VERSION = 1
PROTOCOL_SHA256 = "f2c7907a3630437f9b3dc9df4c0d367ecd4909dbc1d4d5d621b9f8da90d782b4"
MAPPING_SHA256 = "ad859502f111731f1a92ad987386ed7d28eade4e579362f92bf804e0f5e07127"
PROTOCOL_COMMIT = "a75018e6698f3276c03670aef393b0cd9d8738c6"
DATA_ARCHIVE_SHA256 = "35f3c3ae57f65a6ad50148a9c38ad44a75eda1e8b54cea628069b17154c6da33"
PRODUCT_SNAPSHOT_SHA256 = "d480fb82e712f06aabe0a98461e222344656b87022b8bda2cd7ccaa4c29ae88b"
DATA_ARCHIVE_PATH = "artifacts/french_25_size_prior_1_0_monthly_35f3c3ae.zip"
PRODUCT_SNAPSHOT_PATH = "artifacts/snapshot_20260731_6a7ca6b8.zip"
EXPECTED_MEMBER = "25_Portfolios_ME_Prior_1_0.csv"
FORMAL_START = pd.Period("1963-01", freq="M")
FORMAL_END = pd.Period("2026-05", freq="M")
PRIMARY_END = pd.Period("2005-12", freq="M")
RECENT_START = pd.Period("2006-01", freq="M")
PRIMARY_COST_BPS = 10.0
STRESS_COST_BPS = (25.0, 50.0)
GLOBAL_SEARCH_TRIALS = 6_175
MONTHS_PER_YEAR = 12
NEWEY_WEST_LAG_MONTHS = 3
BIG_ROW_COLUMNS = SIZE_PRIOR_COLUMNS[-5:]


def _load_product_monthly_returns(root: Path) -> dict[str, pd.Series]:
    snapshot_path = root / PRODUCT_SNAPSHOT_PATH
    if sha256_file(snapshot_path) != PRODUCT_SNAPSHOT_SHA256:
        raise ValueError("QQQ／SPY 產品快照雜湊不符")
    panel, manifest = load_snapshot(snapshot_path)
    if manifest.get("panel_sha256") != "6a7ca6b83b1570007424daa46b0ff4e8fb4a655d39298a0f4f6d74c3b7ea3a66":
        raise ValueError("QQQ／SPY 產品 panel fingerprint 不符")

    output: dict[str, pd.Series] = {}
    for ticker in ("QQQ", "SPY"):
        prices = panel.close[ticker].dropna().astype(float)
        month_end = prices.groupby(prices.index.to_period("M")).last()
        returns = month_end.pct_change(fill_method=None).dropna()
        output[ticker] = returns.rename(ticker)
    return output


def load_frozen_size_prior_data(root: str | Path) -> dict[str, Any]:
    root_path = Path(root)
    if sha256_file(root_path / "docs/SHORT_TERM_FRENCH_SIZE_PRIOR_PROTOCOL.md") != PROTOCOL_SHA256:
        raise ValueError("French size-prior 協議雜湊不符")
    if sha256_file(root_path / "docs/SHORT_TERM_FRENCH_SIZE_PRIOR_DATA_MAPPING.md") != MAPPING_SHA256:
        raise ValueError("French size-prior 映射雜湊不符")

    protocol_receipt = json.loads(
        (root_path / "artifacts/short_term_french_size_prior_protocol_receipt.json").read_text(
            encoding="utf-8"
        )
    )
    data_receipt = json.loads(
        (root_path / "artifacts/short_term_french_size_prior_data_receipt.json").read_text(
            encoding="utf-8"
        )
    )
    if (
        protocol_receipt.get("status")
        != "french_size_prior_frozen_before_first_download_and_numeric_rows"
        or protocol_receipt.get("new_archive_numeric_rows_seen") is not False
        or protocol_receipt.get("strategy_calculation_started") is not False
        or protocol_receipt["protocol"]["sha256"] != PROTOCOL_SHA256
        or protocol_receipt["mapping"]["sha256"] != MAPPING_SHA256
    ):
        raise ValueError("French size-prior 計算前凍結收據不符")
    if (
        data_receipt.get("status") != "french_size_prior_first_download_contract_passed"
        or data_receipt.get("passed_check_count") != 10
        or data_receipt.get("required_check_count") != 10
        or data_receipt.get("numeric_return_rows_parsed") is not True
        or data_receipt.get("strategy_calculation_started") is not False
        or not all(data_receipt.get("checks", {}).values())
    ):
        raise ValueError("French size-prior 首次下載收據不符")

    archive_path = root_path / DATA_ARCHIVE_PATH
    if sha256_file(archive_path) != DATA_ARCHIVE_SHA256:
        raise ValueError("French size-prior ZIP 雜湊不符")
    text = extract_single_csv(archive_path.read_bytes(), EXPECTED_MEMBER)
    value = parse_size_prior_monthly_table(text, VALUE_WEIGHTED_MONTHLY_MARKER)
    equal = parse_size_prior_monthly_table(text, EQUAL_WEIGHTED_MONTHLY_MARKER)

    prior = load_frozen_prior_return_data(root_path)
    common = value.frame.index.intersection(equal.frame.index).intersection(prior["common_index"])
    common = common[(common >= FORMAL_START) & (common <= FORMAL_END)]
    expected = pd.period_range(FORMAL_START, FORMAL_END, freq="M")
    if not common.equals(expected):
        raise ValueError("French size-prior 共同正式期不連續或邊界不符")

    frames = {
        "size_value": value.frame.reindex(common),
        "size_equal": equal.frame.reindex(common),
        "short_value": prior["short_value"].reindex(common),
        "long_value": prior["long_value"].reindex(common),
        "factors": prior["factors"].reindex(common),
    }
    if any(frame.isna().any().any() for frame in frames.values()):
        raise ValueError("French size-prior 正式共同期含缺值；禁止補值")
    return {
        **frames,
        "products": _load_product_monthly_returns(root_path),
        "common_index": common,
        "protocol_receipt": protocol_receipt,
        "data_receipt": data_receipt,
        "raw_missing_codes": {
            "value_weighted": value.raw_missing_codes,
            "equal_weighted": equal.raw_missing_codes,
        },
        "markers": {
            "value_weighted": value.marker,
            "equal_weighted": equal.marker,
        },
    }


def _metrics_extended(path: ReturnPath, risk_free: pd.Series) -> dict[str, float | int]:
    output = _metrics(path, risk_free)
    output["worst_month"] = float(path.returns.min())
    return output


def _active_comparison(
    candidate: ReturnPath,
    benchmark: ReturnPath,
) -> dict[str, Any]:
    aligned = pd.concat(
        [candidate.returns.rename("candidate"), benchmark.returns.rename("benchmark")],
        axis=1,
        join="inner",
    ).dropna()
    active = aligned["candidate"] - aligned["benchmark"]
    return {
        "months": int(len(active)),
        "mean_monthly": float(active.mean()),
        "annualized_arithmetic": float(active.mean() * MONTHS_PER_YEAR),
        "newey_west": newey_west_mean_test(
            active,
            max_lag=NEWEY_WEST_LAG_MONTHS,
            periods_per_year=MONTHS_PER_YEAR,
        ),
        "active_probabilistic_sharpe": probabilistic_sharpe_ratio(
            active,
            periods_per_year=MONTHS_PER_YEAR,
        ),
        "active_global_deflated_sharpe": deflated_sharpe_ratio(
            active,
            trials=GLOBAL_SEARCH_TRIALS,
            periods_per_year=MONTHS_PER_YEAR,
        ),
    }


def _build_candidate_family(
    size_value: pd.DataFrame,
    size_equal: pd.DataFrame,
) -> dict[str, pd.Series]:
    family = {
        f"cell_{index + 1:02d}_{column}": size_value[column].rename(column)
        for index, column in enumerate(SIZE_PRIOR_COLUMNS)
    }
    linear = np.arange(1.0, 6.0)
    linear /= linear.sum()
    square = np.arange(1.0, 6.0) ** 2
    square /= square.sum()
    family.update(
        {
            "big_row_linear_tilt": size_value[BIG_ROW_COLUMNS].mul(linear, axis=1).sum(axis=1),
            "big_row_square_tilt": size_value[BIG_ROW_COLUMNS].mul(square, axis=1).sum(axis=1),
            "big_equal_weighted_hi": size_equal["BIG HiPRIOR"],
            "big_row_equal": size_value[BIG_ROW_COLUMNS].mean(axis=1),
        }
    )
    return family


def _fixed_split_summary(
    candidate: ReturnPath,
    market: ReturnPath,
    big_equal: ReturnPath,
    risk_free: pd.Series,
    splits: list[tuple[str, pd.Period, pd.Period]],
) -> dict[str, Any]:
    output: dict[str, Any] = {}
    for label, start, end in splits:
        candidate_metrics = _metrics_extended(_slice_path(candidate, start, end), risk_free)
        market_metrics = _metrics_extended(_slice_path(market, start, end), risk_free)
        big_equal_metrics = _metrics_extended(_slice_path(big_equal, start, end), risk_free)
        output[label] = {
            "candidate_cagr": candidate_metrics["cagr"],
            "market_cagr": market_metrics["cagr"],
            "big_row_equal_cagr": big_equal_metrics["cagr"],
            "edge_vs_market": float(candidate_metrics["cagr"] - market_metrics["cagr"]),
            "edge_vs_big_row_equal": float(
                candidate_metrics["cagr"] - big_equal_metrics["cagr"]
            ),
        }
    return output


def _build_period(
    *,
    name: str,
    start: pd.Period,
    end: pd.Period,
    candidate_by_cost: dict[str, ReturnPath],
    candidate_gross: pd.Series,
    baselines: dict[str, ReturnPath],
    risk_free: pd.Series,
    splits: list[tuple[str, pd.Period, pd.Period]],
    pbo: dict[str, Any],
) -> dict[str, Any]:
    candidate = _slice_path(candidate_by_cost["10"], start, end)
    candidate_50 = _slice_path(candidate_by_cost["50"], start, end)
    period_baselines: dict[str, ReturnPath] = {}
    for key, path in baselines.items():
        sliced = _slice_path(path, start, end)
        if len(sliced.returns.dropna()) >= 24:
            period_baselines[key] = sliced

    candidate_metrics = _metrics_extended(candidate, risk_free)
    candidate_50_metrics = _metrics_extended(candidate_50, risk_free)
    baseline_metrics = {
        key: _metrics_extended(path, risk_free) for key, path in period_baselines.items()
    }
    comparisons = {
        key: _active_comparison(candidate, path) for key, path in period_baselines.items()
    }
    fixed_splits = _fixed_split_summary(
        candidate,
        period_baselines["market"],
        period_baselines["big_row_equal"],
        risk_free,
        splits,
    )
    rolling_market = _rolling_comparison(candidate, period_baselines["market"])
    rolling_big_equal = _rolling_comparison(candidate, period_baselines["big_row_equal"])
    break_even = {
        key: _candidate_cost_break_even(
            candidate_gross,
            path,
            start=start,
            end=end,
        )
        for key, path in period_baselines.items()
    }

    market_metrics = baseline_metrics["market"]
    big_equal_metrics = baseline_metrics["big_row_equal"]
    all_equal_metrics = baseline_metrics["all_25_equal"]
    big_lo_metrics = baseline_metrics["big_lo_prior"]
    gates = {
        "candidate_10bps_cagr_beats_market_by_2pp": candidate_metrics["cagr"] >= market_metrics["cagr"] + 0.02,
        "candidate_10bps_cagr_beats_big_row_equal_by_2pp": candidate_metrics["cagr"] >= big_equal_metrics["cagr"] + 0.02,
        "candidate_10bps_cagr_beats_all_25_equal_by_2pp": candidate_metrics["cagr"] >= all_equal_metrics["cagr"] + 0.02,
        "candidate_10bps_cagr_beats_big_lo_by_2pp": candidate_metrics["cagr"] >= big_lo_metrics["cagr"] + 0.02,
        "candidate_excess_sharpe_beats_market_and_big_equal": candidate_metrics["excess_sharpe"] > market_metrics["excess_sharpe"] and candidate_metrics["excess_sharpe"] > big_equal_metrics["excess_sharpe"],
        "candidate_drawdown_not_over_5pp_deeper_than_market_or_big_equal": candidate_metrics["max_drawdown"] >= min(market_metrics["max_drawdown"], big_equal_metrics["max_drawdown"]) - 0.05,
        "candidate_50bps_cagr_beats_market_by_50bp": candidate_50_metrics["cagr"] >= market_metrics["cagr"] + 0.005,
        "candidate_50bps_cagr_beats_big_equal_by_50bp": candidate_50_metrics["cagr"] >= big_equal_metrics["cagr"] + 0.005,
        "both_fixed_halves_beat_market_by_50bp": all(row["edge_vs_market"] >= 0.005 for row in fixed_splits.values()),
        "both_fixed_halves_beat_big_equal_by_50bp": all(row["edge_vs_big_row_equal"] >= 0.005 for row in fixed_splits.values()),
        "rolling_60m_vs_market_60pct_and_positive_median": rolling_market["cagr_win_fraction"] >= 0.60 and rolling_market["median_cagr_difference"] > 0.0,
        "rolling_60m_vs_big_equal_60pct_and_positive_median": rolling_big_equal["cagr_win_fraction"] >= 0.60 and rolling_big_equal["median_cagr_difference"] > 0.0,
        "active_newey_west_t_vs_market_and_big_equal_at_least_1_96": comparisons["market"]["newey_west"]["t_stat"] >= 1.96 and comparisons["big_row_equal"]["newey_west"]["t_stat"] >= 1.96,
        "active_psr_vs_market_and_big_equal_at_least_95pct": comparisons["market"]["active_probabilistic_sharpe"]["probability"] >= 0.95 and comparisons["big_row_equal"]["active_probabilistic_sharpe"]["probability"] >= 0.95,
        "active_global_dsr_vs_market_and_big_equal_at_least_95pct": comparisons["market"]["active_global_deflated_sharpe"]["probability"] >= 0.95 and comparisons["big_row_equal"]["active_global_deflated_sharpe"]["probability"] >= 0.95,
        "candidate_family_pbo_not_above_20pct": bool(np.isfinite(pbo["pbo"]) and pbo["pbo"] <= 0.20),
        "cost_break_even_vs_market_and_big_equal_at_least_50bps": break_even["market"]["one_way_bps"] >= 50.0 and break_even["big_row_equal"]["one_way_bps"] >= 50.0,
    }
    return {
        "name": name,
        "start": str(start),
        "end": str(end),
        "candidate_metrics": candidate_metrics,
        "candidate_50bps_metrics": candidate_50_metrics,
        "baseline_metrics": baseline_metrics,
        "comparisons": comparisons,
        "fixed_splits": fixed_splits,
        "rolling_60m_vs_market": rolling_market,
        "rolling_60m_vs_big_row_equal": rolling_big_equal,
        "cost_break_even_vs_baselines": break_even,
        "gates": gates,
        "passed_gate_count": int(sum(bool(value) for value in gates.values())),
        "required_gate_count": 17,
        "all_gates_pass": all(gates.values()),
    }


def _size_direction_diagnostic(
    size_value: pd.DataFrame,
    factors: pd.DataFrame,
    *,
    start: pd.Period,
    end: pd.Period,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for size in range(1, 6):
        low_column = SIZE_PRIOR_COLUMNS[(size - 1) * 5]
        high_column = SIZE_PRIOR_COLUMNS[(size - 1) * 5 + 4]
        low = _slice_path(
            apply_full_reconstitution_cost(size_value[low_column], PRIMARY_COST_BPS),
            start,
            end,
        )
        high = _slice_path(
            apply_full_reconstitution_cost(size_value[high_column], PRIMARY_COST_BPS),
            start,
            end,
        )
        low_metrics = _metrics_extended(low, factors["RF"])
        high_metrics = _metrics_extended(high, factors["RF"])
        rows.append(
            {
                "size_quintile": size,
                "low_prior_column": low_column,
                "high_prior_column": high_column,
                "low_prior_cagr": low_metrics["cagr"],
                "high_prior_cagr": high_metrics["cagr"],
                "high_minus_low_cagr": float(high_metrics["cagr"] - low_metrics["cagr"]),
                "low_prior_excess_sharpe": low_metrics["excess_sharpe"],
                "high_prior_excess_sharpe": high_metrics["excess_sharpe"],
                "high_prior_max_drawdown": high_metrics["max_drawdown"],
            }
        )
    return rows


def build_french_size_prior_research(root: str | Path) -> dict[str, Any]:
    root_path = Path(root)
    data = load_frozen_size_prior_data(root_path)
    size_value = data["size_value"]
    size_equal = data["size_equal"]
    factors = data["factors"]
    market_gross = (factors["Mkt-RF"] + factors["RF"]).rename("market")
    candidate_gross = size_value["BIG HiPRIOR"].rename("big_hi_prior_1_1")
    candidate_by_cost = {
        str(int(cost)): apply_full_reconstitution_cost(candidate_gross, cost)
        for cost in (PRIMARY_COST_BPS, *STRESS_COST_BPS)
    }

    baselines = {
        "market": apply_buy_and_hold_entry_cost(market_gross, PRIMARY_COST_BPS),
        "big_row_equal": apply_full_reconstitution_cost(
            size_value[BIG_ROW_COLUMNS].mean(axis=1).rename("big_row_equal"),
            PRIMARY_COST_BPS,
        ),
        "all_25_equal": apply_full_reconstitution_cost(
            size_value.mean(axis=1).rename("all_25_equal"),
            PRIMARY_COST_BPS,
        ),
        "big_lo_prior": apply_full_reconstitution_cost(
            size_value["BIG LoPRIOR"].rename("big_lo_prior"),
            PRIMARY_COST_BPS,
        ),
        "unconditional_hi_prior_1_1": apply_full_reconstitution_cost(
            data["short_value"]["Hi PRIOR"].rename("unconditional_hi_prior_1_1"),
            PRIMARY_COST_BPS,
        ),
        "long_momentum_hi_12_2": apply_full_reconstitution_cost(
            data["long_value"]["Hi PRIOR"].rename("long_momentum_hi_12_2"),
            PRIMARY_COST_BPS,
        ),
        "QQQ": apply_buy_and_hold_entry_cost(data["products"]["QQQ"], PRIMARY_COST_BPS),
        "SPY": apply_buy_and_hold_entry_cost(data["products"]["SPY"], PRIMARY_COST_BPS),
    }

    family_gross = _build_candidate_family(size_value, size_equal)
    family_paths = {
        name: apply_full_reconstitution_cost(series, PRIMARY_COST_BPS)
        for name, series in family_gross.items()
    }
    pbo_primary = probability_of_backtest_overfitting(
        pd.concat(
            {
                name: _slice_path(path, FORMAL_START, PRIMARY_END).returns
                for name, path in family_paths.items()
            },
            axis=1,
        ),
        slices=10,
    )
    pbo_recent = probability_of_backtest_overfitting(
        pd.concat(
            {
                name: _slice_path(path, RECENT_START, FORMAL_END).returns
                for name, path in family_paths.items()
            },
            axis=1,
        ),
        slices=10,
    )

    primary = _build_period(
        name="主要外部期",
        start=FORMAL_START,
        end=PRIMARY_END,
        candidate_by_cost=candidate_by_cost,
        candidate_gross=candidate_gross,
        baselines=baselines,
        risk_free=factors["RF"],
        splits=[
            ("1963_to_1984", FORMAL_START, pd.Period("1984-12", freq="M")),
            ("1985_to_2005", pd.Period("1985-01", freq="M"), PRIMARY_END),
        ],
        pbo=pbo_primary,
    )
    recent = _build_period(
        name="近期確認期",
        start=RECENT_START,
        end=FORMAL_END,
        candidate_by_cost=candidate_by_cost,
        candidate_gross=candidate_gross,
        baselines=baselines,
        risk_free=factors["RF"],
        splits=[
            ("2006_to_2015", RECENT_START, pd.Period("2015-12", freq="M")),
            ("2016_to_end", pd.Period("2016-01", freq="M"), FORMAL_END),
        ],
        pbo=pbo_recent,
    )

    receipt = data["data_receipt"]
    data_gates = {
        "protocol_and_mapping_frozen_before_first_download": data["protocol_receipt"]["new_archive_download_started"] is False and data["protocol_receipt"]["new_archive_numeric_rows_seen"] is False and data["protocol_receipt"]["protocol"]["sha256"] == PROTOCOL_SHA256 and data["protocol_receipt"]["mapping"]["sha256"] == MAPPING_SHA256,
        "first_download_performed_once": receipt["archive"]["downloaded_in_this_run"] is True and receipt["strategy_calculation_started"] is False,
        "zip_member_and_sha256_preserved": receipt["archive"]["sha256"] == DATA_ARCHIVE_SHA256 and receipt["archive"]["member"] == EXPECTED_MEMBER and sha256_file(root_path / DATA_ARCHIVE_PATH) == DATA_ARCHIVE_SHA256,
        "two_monthly_tables_have_exactly_25_columns": size_value.shape[1] == 25 and size_equal.shape[1] == 25,
        "semantic_column_order_matches_frozen_grid": list(size_value.columns) == SIZE_PRIOR_COLUMNS and list(size_equal.columns) == SIZE_PRIOR_COLUMNS,
        "raw_dates_cover_1927_01_through_2026_05": receipt["tables"]["value_weighted_monthly"]["first_month"] == "1926-02" and receipt["tables"]["value_weighted_monthly"]["last_month"] == "2026-05",
        "formal_1963_01_to_2026_05_is_complete": data["common_index"].equals(pd.period_range(FORMAL_START, FORMAL_END, freq="M")) and not size_value.isna().any().any() and not size_equal.isna().any().any(),
        "missing_and_extreme_values_audited_without_imputation": receipt["checks"]["missing_and_extreme_values_audited_without_imputation"] is True and all(value == 0 for value in data["raw_missing_codes"].values()),
        "reused_archives_match_frozen_hashes": receipt["checks"]["reused_archives_match_frozen_hashes"] is True and sha256_file(root_path / PRODUCT_SNAPSHOT_PATH) == PRODUCT_SNAPSHOT_SHA256,
        "formation_t_minus_1_return_t_rule_frozen": receipt["checks"]["formation_t_minus_1_return_t_rule_frozen"] is True,
    }

    full_candidate = _slice_path(candidate_by_cost["10"], FORMAL_START, FORMAL_END)
    full_baselines = {
        key: _slice_path(path, FORMAL_START, FORMAL_END)
        for key, path in baselines.items()
        if key not in {"QQQ", "SPY"}
    }
    cell_metrics = {
        name: {
            "column": SIZE_PRIOR_COLUMNS[index],
            "size_quintile": index // 5 + 1,
            "prior_quintile": index % 5 + 1,
            "primary": _metrics_extended(
                _slice_path(family_paths[name], FORMAL_START, PRIMARY_END), factors["RF"]
            ),
            "recent": _metrics_extended(
                _slice_path(family_paths[name], RECENT_START, FORMAL_END), factors["RF"]
            ),
        }
        for index, name in enumerate(list(family_paths)[:25])
    }
    passed_gate_count = int(sum(data_gates.values())) + primary["passed_gate_count"] + recent["passed_gate_count"]
    mechanism_passed = all(data_gates.values()) and primary["all_gates_pass"] and recent["all_gates_pass"]
    return {
        "schema_version": SCHEMA_VERSION,
        "status": (
            "french_size_prior_mechanism_passed_but_non_tradeable"
            if mechanism_passed
            else "french_size_prior_data_passed_but_economic_validation_failed"
        ),
        "research_role": "independent_first_seen_size_conditioned_mechanism_validation",
        "data_contract_passed": all(data_gates.values()),
        "economic_validation_passed": bool(mechanism_passed),
        "independent_first_seen_evidence": True,
        "paper_eligible": False,
        "paper_state_created": False,
        "trade_ready": False,
        "real_money_action_usd": 0,
        "protocol": {
            "protocol_sha256": PROTOCOL_SHA256,
            "mapping_sha256": MAPPING_SHA256,
            "protocol_commit": PROTOCOL_COMMIT,
            "global_search_trials": GLOBAL_SEARCH_TRIALS,
            "candidate_family_paths": len(family_paths),
            "monthly_periods_per_year": MONTHS_PER_YEAR,
            "newey_west_lag_months": NEWEY_WEST_LAG_MONTHS,
            "economic_design_changed_after_results": False,
        },
        "snapshot": {
            "archive_path": DATA_ARCHIVE_PATH,
            "archive_sha256": DATA_ARCHIVE_SHA256,
            "formal_start": str(FORMAL_START),
            "formal_end": str(FORMAL_END),
            "formal_months": int(len(data["common_index"])),
            "value_weighted_marker": data["markers"]["value_weighted"],
            "equal_weighted_marker": data["markers"]["equal_weighted"],
            "survivorship_reduced_not_raw_point_in_time_stock_ledger": True,
        },
        "frozen_candidate": {
            "label": "Big Hi PRIOR 1–1",
            "formation": "month t-1 size/prior sort, month t official value-weighted return",
            "cost_model": "first buy once; complete sell and buy at every later month",
            "full_history_metrics_10bps": _metrics_extended(full_candidate, factors["RF"]),
            "cost_sensitivity_full_history": {
                f"{cost}_bps": _metrics_extended(
                    _slice_path(path, FORMAL_START, FORMAL_END), factors["RF"]
                )
                for cost, path in candidate_by_cost.items()
            },
        },
        "full_history_baseline_metrics": {
            key: _metrics_extended(path, factors["RF"])
            for key, path in full_baselines.items()
        },
        "primary_external_period": primary,
        "recent_confirmation_period": recent,
        "cell_metrics_10bps": cell_metrics,
        "size_direction_diagnostic": {
            "primary": _size_direction_diagnostic(
                size_value, factors, start=FORMAL_START, end=PRIMARY_END
            ),
            "recent": _size_direction_diagnostic(
                size_value, factors, start=RECENT_START, end=FORMAL_END
            ),
        },
        "pbo": {"primary": pbo_primary, "recent": pbo_recent},
        "factor_regression_full_history": _factor_regression(full_candidate, factors),
        "stress_periods": _stress_summary({"candidate": full_candidate, **full_baselines}),
        "data_gates": data_gates,
        "passed_gate_count": passed_gate_count,
        "required_gate_count": 44,
        "gate_breakdown": {
            "data": f"{sum(data_gates.values())}/10",
            "primary": f"{primary['passed_gate_count']}/17",
            "recent": f"{recent['passed_gate_count']}/17",
        },
        "paper_blockers": {
            "cells_are_tradeable_securities": False,
            "qualified_point_in_time_stock_constituents_and_delisting_ledger": False,
            "exact_stock_turnover_spreads_and_corporate_actions": False,
            "authorized_crsp_wrds_norgate_or_equivalent_provider": False,
        },
        "decision": (
            "保留首次未見的 size-conditioned 正負結果；25 個 French cells 只驗證機制，"
            "不能產生個股名單。即使 44/44 亦須取得合格逐股 point-in-time、退市／收購、"
            "公司行動及精確成交成本，另按個股 v1 從全現金建立不可回填 Paper。"
            "本輪 Paper、實金及今日買賣動作固定為 US$0。"
        ),
    }
