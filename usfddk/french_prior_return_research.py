from __future__ import annotations

import csv
import hashlib
import io
import json
import math
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from usfddk.metrics import newey_west_mean_test
from usfddk.validation import (
    deflated_sharpe_ratio,
    probabilistic_sharpe_ratio,
    probability_of_backtest_overfitting,
)

SCHEMA_VERSION = 1
REPAIR_PROTOCOL_SHA256 = "93059919e4acf406dc9e46702cd37c477f688da5afb80bed67d86305bd474297"
REPAIR_MAPPING_SHA256 = "484d0385057ffe867645a8498c6f6071a264da2b94dbde5453e3f4e0321dc1b4"
REPAIR_PROTOCOL_COMMIT = "66779aa3800a0abadaed0387a12f70f07d2bd978"
ORIGINAL_PROTOCOL_SHA256 = "f6ff259ee2ad020d618f891097eb3dbf7b76ee3d382b9a31c373ba76641f62da"
ORIGINAL_PROTOCOL_COMMIT = "b3240326cb4ba92e9e6585779a2b6249a9f5c78d"
FORMAL_START = pd.Period("1963-01", freq="M")
FORMAL_END = pd.Period("2026-05", freq="M")
PRIMARY_END = pd.Period("2005-12", freq="M")
RECENT_START = pd.Period("2006-01", freq="M")
PRIMARY_COST_BPS = 10.0
STRESS_COST_BPS = (25.0, 50.0)
GLOBAL_SEARCH_TRIALS = 6_150
MONTHS_PER_YEAR = 12
NEWEY_WEST_LAG_MONTHS = 3
DECILE_COLUMNS = [
    "Lo PRIOR",
    "PRIOR 2",
    "PRIOR 3",
    "PRIOR 4",
    "PRIOR 5",
    "PRIOR 6",
    "PRIOR 7",
    "PRIOR 8",
    "PRIOR 9",
    "Hi PRIOR",
]

ARCHIVE_CONTRACTS = {
    "short_term_prior_1_0": {
        "path": "artifacts/french_10_prior_1_0_monthly_20b186f6.zip",
        "sha256": "20b186f6f7c322098d6d2a6be6183d5944b12c7f6c9e888664ce44ba81064ace",
        "member": "10_Portfolios_Prior_1_0.csv",
    },
    "long_term_prior_12_2": {
        "path": "artifacts/french_10_prior_12_2_monthly_ca0af27f.zip",
        "sha256": "ca0af27fa0829ed6ac38b7b13b20cc11fd12274a8d06dac226998dfc1d0f07f6",
        "member": "10_Portfolios_Prior_12_2.csv",
    },
    "ff_factors": {
        "path": "artifacts/french_ff_factors_80b88699.zip",
        "sha256": "80b88699a18ac408e2456d25b1004e340f3f7f8d41d5b476a0285bc53c6f0436",
        "member": "F-F_Research_Data_Factors.csv",
    },
    "momentum": {
        "path": "artifacts/french_momentum_monthly_37baf72a.zip",
        "sha256": "37baf72ae4eace9715e8746413d0122334c63aa4083fd1c3cf2060fa04e4bd28",
        "member": "F-F_Momentum_Factor.csv",
    },
    "short_term_reversal": {
        "path": "artifacts/french_st_reversal_monthly_e0fc1859.zip",
        "sha256": "e0fc1859c8b7e56ac17d06239de231fb33d28c8537b3f59fa378d4d704110e21",
        "member": "F-F_ST_Reversal_Factor.csv",
    },
}

TABLE_MARKERS = {
    "short_value": "Aerage Value Weighted Returns -- Monthly",
    "short_equal": "Average Equal Weighted Returns -- Monthly",
    "long_value": "Value Weight Returns -- Monthly",
    "long_equal": "Average Equal Weighted Returns -- Monthly",
}


@dataclass(frozen=True)
class ReturnPath:
    returns: pd.Series
    turnover: pd.Series


@dataclass(frozen=True)
class ParsedTable:
    frame: pd.DataFrame
    raw_missing_codes: int
    marker: str


def _sha256(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _extract_single_csv(path: str | Path, expected_member: str) -> str:
    with zipfile.ZipFile(path) as bundle:
        members = [
            name
            for name in bundle.namelist()
            if not name.endswith("/") and name.lower().endswith(".csv")
        ]
        if members != [expected_member]:
            raise ValueError(f"{Path(path).name} ZIP member 不符：{members}")
        raw = bundle.read(expected_member)
    for encoding in ("utf-8-sig", "latin-1"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise ValueError(f"{Path(path).name} CSV 編碼無法辨識")


def _parse_number(cell: str) -> tuple[float, bool]:
    value = float(cell.strip())
    missing = value in (-99.99, -999.0)
    return (float("nan") if missing else value / 100.0), missing


def parse_exact_monthly_table(text: str, marker: str) -> ParsedTable:
    rows = list(csv.reader(io.StringIO(text)))
    matches = [
        index
        for index, row in enumerate(rows)
        if len(row) == 1 and row[0].strip() == marker
    ]
    if len(matches) != 1:
        raise ValueError(f"精確月表 marker 必須只出現一次：{marker!r}，實際 {len(matches)} 次")
    header_index = matches[0] + 1
    while header_index < len(rows) and not any(cell.strip() for cell in rows[header_index]):
        header_index += 1
    if header_index >= len(rows):
        raise ValueError(f"{marker!r} 後沒有欄名")
    columns = [cell.strip() for cell in rows[header_index][1:]]
    if columns != DECILE_COLUMNS:
        raise ValueError(f"{marker!r} 十分位欄名或次序不符：{columns}")

    periods: list[pd.Period] = []
    values: list[list[float]] = []
    missing_codes = 0
    started = False
    for row in rows[header_index + 1 :]:
        first = row[0].strip() if row else ""
        if len(first) != 6 or not first.isdigit():
            if started:
                break
            continue
        started = True
        if len(row) != len(DECILE_COLUMNS) + 1:
            raise ValueError(f"{marker!r} {first} 欄數不符")
        parsed: list[float] = []
        for cell in row[1:]:
            value, missing = _parse_number(cell)
            parsed.append(value)
            missing_codes += int(missing)
        periods.append(pd.Period(first, freq="M"))
        values.append(parsed)
    if not periods:
        raise ValueError(f"{marker!r} 沒有月資料")
    frame = pd.DataFrame(values, index=pd.PeriodIndex(periods), columns=DECILE_COLUMNS)
    if frame.index.has_duplicates or not frame.index.is_monotonic_increasing:
        raise ValueError(f"{marker!r} 月份重複或未遞增")
    return ParsedTable(frame=frame, raw_missing_codes=missing_codes, marker=marker)


def parse_exact_factor_table(text: str, columns: list[str]) -> ParsedTable:
    rows = list(csv.reader(io.StringIO(text)))
    matches = [
        index
        for index, row in enumerate(rows)
        if [cell.strip() for cell in row[1:]] == columns
    ]
    if not matches:
        raise ValueError(f"找不到因素欄名：{columns}")
    header_index = matches[0]
    periods: list[pd.Period] = []
    values: list[list[float]] = []
    missing_codes = 0
    started = False
    for row in rows[header_index + 1 :]:
        first = row[0].strip() if row else ""
        if len(first) != 6 or not first.isdigit():
            if started:
                break
            continue
        started = True
        if len(row) != len(columns) + 1:
            raise ValueError(f"因素 {first} 欄數不符")
        parsed: list[float] = []
        for cell in row[1:]:
            value, missing = _parse_number(cell)
            parsed.append(value)
            missing_codes += int(missing)
        periods.append(pd.Period(first, freq="M"))
        values.append(parsed)
    if not periods:
        raise ValueError(f"因素 {columns} 沒有月資料")
    frame = pd.DataFrame(values, index=pd.PeriodIndex(periods), columns=columns)
    if frame.index.has_duplicates or not frame.index.is_monotonic_increasing:
        raise ValueError(f"因素 {columns} 月份重複或未遞增")
    return ParsedTable(frame=frame, raw_missing_codes=missing_codes, marker=",".join(columns))


def _verify_repair_receipts(root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    repair_receipt = json.loads(
        (root / "artifacts/short_term_french_prior_return_schema_repair_protocol_receipt.json").read_text(
            encoding="utf-8"
        )
    )
    original_receipt = json.loads(
        (root / "artifacts/short_term_french_prior_return_data_receipt.json").read_text(
            encoding="utf-8"
        )
    )
    expected_repair = {
        "status": "french_prior_return_schema_repair_frozen_before_numeric_calculation",
        "aggregate_strategy_metrics_were_calculated_before_this_protocol": False,
        "new_download_allowed": False,
        "numeric_calculation_started": False,
        "economic_design_changed": False,
        "independent_first_seen_evidence": False,
    }
    if any(repair_receipt.get(key) != value for key, value in expected_repair.items()):
        raise ValueError("schema repair 計算前收據界線不符")
    if (
        repair_receipt["protocol"]["sha256"] != REPAIR_PROTOCOL_SHA256
        or repair_receipt["mapping"]["sha256"] != REPAIR_MAPPING_SHA256
        or repair_receipt["original_economic_protocol"]["sha256"]
        != ORIGINAL_PROTOCOL_SHA256
    ):
        raise ValueError("schema repair 收據雜湊不符")
    if (
        original_receipt.get("status")
        != "french_prior_return_first_download_contract_failed_before_strategy_calculation"
        or original_receipt.get("passed_check_count") != 6
        or original_receipt.get("required_check_count") != 8
        or original_receipt.get("numeric_return_rows_parsed") is not False
        or original_receipt.get("strategy_calculation_started") is not False
    ):
        raise ValueError("原 6/8 fail-closed 收據被改動或不完整")
    return repair_receipt, original_receipt


def load_frozen_prior_return_data(root: str | Path) -> dict[str, Any]:
    root_path = Path(root)
    _verify_repair_receipts(root_path)
    if _sha256(root_path / "docs/SHORT_TERM_FRENCH_PRIOR_RETURN_SCHEMA_REPAIR_PROTOCOL.md") != REPAIR_PROTOCOL_SHA256:
        raise ValueError("schema repair 協議雜湊不符")
    if _sha256(root_path / "docs/SHORT_TERM_FRENCH_PRIOR_RETURN_SCHEMA_REPAIR_MAPPING.md") != REPAIR_MAPPING_SHA256:
        raise ValueError("schema repair 映射雜湊不符")
    if _sha256(root_path / "docs/SHORT_TERM_FRENCH_PRIOR_RETURN_PROTOCOL.md") != ORIGINAL_PROTOCOL_SHA256:
        raise ValueError("原經濟協議雜湊不符")

    texts: dict[str, str] = {}
    archives: dict[str, Any] = {}
    for role, contract in ARCHIVE_CONTRACTS.items():
        path = root_path / contract["path"]
        digest = _sha256(path)
        if digest != contract["sha256"]:
            raise ValueError(f"{role} ZIP 雜湊不符")
        texts[role] = _extract_single_csv(path, contract["member"])
        archives[role] = {
            "path": contract["path"],
            "sha256": digest,
            "member": contract["member"],
            "size_bytes": path.stat().st_size,
        }

    short_value = parse_exact_monthly_table(texts["short_term_prior_1_0"], TABLE_MARKERS["short_value"])
    short_equal = parse_exact_monthly_table(texts["short_term_prior_1_0"], TABLE_MARKERS["short_equal"])
    long_value = parse_exact_monthly_table(texts["long_term_prior_12_2"], TABLE_MARKERS["long_value"])
    long_equal = parse_exact_monthly_table(texts["long_term_prior_12_2"], TABLE_MARKERS["long_equal"])
    ff = parse_exact_factor_table(texts["ff_factors"], ["Mkt-RF", "SMB", "HML", "RF"])
    momentum = parse_exact_factor_table(texts["momentum"], ["Mom"])
    reversal = parse_exact_factor_table(texts["short_term_reversal"], ["ST_Rev"])
    parsed = {
        "short_value": short_value,
        "short_equal": short_equal,
        "long_value": long_value,
        "long_equal": long_equal,
        "ff_factors": ff,
        "momentum": momentum,
        "short_term_reversal": reversal,
    }
    common = parsed["short_value"].frame.index
    for table in parsed.values():
        common = common.intersection(table.frame.index)
    common = common[(common >= FORMAL_START) & (common <= FORMAL_END)]
    if len(common) != 761 or common[0] != FORMAL_START or common[-1] != FORMAL_END:
        raise ValueError(f"共同正式期不符：{common[0] if len(common) else None} 至 {common[-1] if len(common) else None}，{len(common)} 月")
    expected = pd.period_range(FORMAL_START, FORMAL_END, freq="M")
    if not common.equals(expected):
        raise ValueError("共同正式期月份不連續")

    frames = {name: table.frame.reindex(common) for name, table in parsed.items()}
    if any(frame.isna().any().any() for frame in frames.values()):
        raise ValueError("正式期含缺值；禁止補值")
    factors = pd.concat(
        [frames["ff_factors"], frames["momentum"], frames["short_term_reversal"]],
        axis=1,
    )
    return {
        "short_value": frames["short_value"],
        "short_equal": frames["short_equal"],
        "long_value": frames["long_value"],
        "long_equal": frames["long_equal"],
        "factors": factors,
        "archives": archives,
        "raw_missing_codes": {name: table.raw_missing_codes for name, table in parsed.items()},
        "markers": {name: table.marker for name, table in parsed.items()},
        "common_index": common,
    }


def apply_full_reconstitution_cost(gross: pd.Series, cost_bps: float) -> ReturnPath:
    values = gross.astype(float).copy()
    if values.empty:
        raise ValueError("成本路徑不可為空")
    rate = float(cost_bps) / 10_000.0
    net = (1.0 - rate) ** 2 * (1.0 + values) - 1.0
    net.iloc[0] = (1.0 - rate) * (1.0 + values.iloc[0]) - 1.0
    turnover = pd.Series(2.0, index=values.index, name="turnover")
    turnover.iloc[0] = 1.0
    return ReturnPath(returns=net.rename(values.name), turnover=turnover)


def apply_buy_and_hold_entry_cost(gross: pd.Series, cost_bps: float) -> ReturnPath:
    values = gross.astype(float).copy()
    if values.empty:
        raise ValueError("市場路徑不可為空")
    rate = float(cost_bps) / 10_000.0
    net = values.copy()
    net.iloc[0] = (1.0 - rate) * (1.0 + values.iloc[0]) - 1.0
    turnover = pd.Series(0.0, index=values.index, name="turnover")
    turnover.iloc[0] = 1.0
    return ReturnPath(returns=net.rename(values.name), turnover=turnover)


def _slice_path(path: ReturnPath, start: pd.Period, end: pd.Period) -> ReturnPath:
    values = path.returns.loc[start:end].copy()
    return ReturnPath(returns=values, turnover=path.turnover.reindex(values.index).fillna(0.0))


def _metrics(path: ReturnPath, risk_free: pd.Series) -> dict[str, float | int]:
    aligned = pd.concat(
        [path.returns.rename("return"), risk_free.rename("rf")], axis=1, join="inner"
    ).dropna()
    values = aligned["return"]
    if len(values) < 2:
        raise ValueError("月回報期不足")
    wealth = (1.0 + values).cumprod()
    anchored = pd.Series(np.r_[1.0, wealth.to_numpy(dtype=float)])
    total_return = float(wealth.iloc[-1] - 1.0)
    cagr = float(wealth.iloc[-1] ** (MONTHS_PER_YEAR / len(values)) - 1.0)
    volatility = float(values.std(ddof=1) * math.sqrt(MONTHS_PER_YEAR))
    excess = aligned["return"] - aligned["rf"]
    excess_std = float(excess.std(ddof=1))
    excess_sharpe = (
        float(excess.mean() / excess_std * math.sqrt(MONTHS_PER_YEAR))
        if excess_std > 0.0
        else 0.0
    )
    downside = values[values < 0.0]
    downside_std = float(downside.std(ddof=1))
    sortino = (
        float(values.mean() / downside_std * math.sqrt(MONTHS_PER_YEAR))
        if downside_std > 0.0
        else 0.0
    )
    max_drawdown = float((anchored / anchored.cummax() - 1.0).min())
    years = len(values) / MONTHS_PER_YEAR
    return {
        "total_return": total_return,
        "cagr": cagr,
        "volatility": volatility,
        "excess_sharpe": excess_sharpe,
        "sortino": sortino,
        "max_drawdown": max_drawdown,
        "calmar": cagr / abs(max_drawdown) if max_drawdown < 0.0 else 0.0,
        "annual_turnover": float(path.turnover.reindex(values.index).sum() / years),
        "months": int(len(values)),
        "hypothetical_1000_usd_end": float(1_000.0 * wealth.iloc[-1]),
    }


def _active_comparison(candidate: ReturnPath, benchmark: ReturnPath) -> dict[str, Any]:
    aligned = pd.concat(
        [candidate.returns.rename("candidate"), benchmark.returns.rename("benchmark")],
        axis=1,
        join="inner",
    ).dropna()
    active = aligned["candidate"] - aligned["benchmark"]
    return {
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


def _rolling_comparison(
    candidate: ReturnPath, benchmark: ReturnPath, *, window: int = 60
) -> dict[str, Any]:
    aligned = pd.concat(
        [candidate.returns.rename("candidate"), benchmark.returns.rename("benchmark")],
        axis=1,
        join="inner",
    ).dropna()
    rows: list[dict[str, Any]] = []
    for position in range(window - 1, len(aligned)):
        sample = aligned.iloc[position - window + 1 : position + 1]
        candidate_cagr = float((1.0 + sample["candidate"]).prod() ** (MONTHS_PER_YEAR / window) - 1.0)
        benchmark_cagr = float((1.0 + sample["benchmark"]).prod() ** (MONTHS_PER_YEAR / window) - 1.0)
        rows.append(
            {
                "end": str(aligned.index[position]),
                "candidate_cagr": candidate_cagr,
                "benchmark_cagr": benchmark_cagr,
                "cagr_difference": candidate_cagr - benchmark_cagr,
            }
        )
    differences = pd.Series([row["cagr_difference"] for row in rows], dtype=float)
    return {
        "window_months": window,
        "observations": int(len(rows)),
        "cagr_win_fraction": float((differences > 0.0).mean()) if len(rows) else 0.0,
        "median_cagr_difference": float(differences.median()) if len(rows) else 0.0,
        "worst_cagr_difference": float(differences.min()) if len(rows) else 0.0,
        "latest_cagr_difference": float(differences.iloc[-1]) if len(rows) else 0.0,
        "series": rows,
    }


def _factor_regression(candidate: ReturnPath, factors: pd.DataFrame) -> dict[str, float]:
    aligned = pd.concat([candidate.returns.rename("candidate"), factors], axis=1, join="inner").dropna()
    names = ["Mkt-RF", "SMB", "HML", "Mom", "ST_Rev"]
    y = (aligned["candidate"] - aligned["RF"]).to_numpy(dtype=float)
    x = np.column_stack([np.ones(len(aligned)), aligned[names].to_numpy(dtype=float)])
    coefficients, _, _, _ = np.linalg.lstsq(x, y, rcond=None)
    fitted = x @ coefficients
    residual = y - fitted
    total_sum = float(np.sum((y - y.mean()) ** 2))
    residual_sum = float(np.sum(residual**2))
    return {
        "annualized_alpha": float(coefficients[0] * MONTHS_PER_YEAR),
        "market_beta": float(coefficients[1]),
        "smb_beta": float(coefficients[2]),
        "hml_beta": float(coefficients[3]),
        "mom_beta": float(coefficients[4]),
        "short_term_reversal_beta": float(coefficients[5]),
        "r_squared": float(1.0 - residual_sum / total_sum) if total_sum > 0.0 else 0.0,
    }


def _stress_summary(paths: dict[str, ReturnPath]) -> dict[str, Any]:
    periods = {
        "1973_1974": ("1973-01", "1974-12"),
        "1987_crash": ("1987-01", "1987-12"),
        "dotcom": ("2000-01", "2002-12"),
        "gfc": ("2008-01", "2009-12"),
        "covid_2020": ("2020-01", "2020-12"),
        "rate_shock_2022": ("2022-01", "2022-12"),
    }
    output: dict[str, Any] = {}
    for label, (start, end) in periods.items():
        rows: dict[str, Any] = {}
        for name, path in paths.items():
            returns = path.returns.loc[start:end]
            wealth = (1.0 + returns).cumprod()
            anchored = pd.Series(np.r_[1.0, wealth.to_numpy(dtype=float)])
            rows[name] = {
                "return": float(wealth.iloc[-1] - 1.0),
                "max_drawdown": float((anchored / anchored.cummax() - 1.0).min()),
                "worst_month": float(returns.min()),
            }
        output[label] = rows
    return output


def _candidate_cost_break_even(
    gross_candidate: pd.Series,
    baseline: ReturnPath,
    *,
    start: pd.Period,
    end: pd.Period,
    max_cost_bps: float = 500.0,
) -> dict[str, Any]:
    baseline_cagr = float(_metrics(baseline, pd.Series(0.0, index=baseline.returns.index))["cagr"])

    def edge(cost: float) -> float:
        path = _slice_path(apply_full_reconstitution_cost(gross_candidate, cost), start, end)
        return float(_metrics(path, pd.Series(0.0, index=path.returns.index))["cagr"]) - baseline_cagr

    zero_edge = edge(0.0)
    high_edge = edge(max_cost_bps)
    if zero_edge <= 0.0:
        return {
            "one_way_bps": 0.0,
            "status": "no_edge_even_before_candidate_cost",
            "edge_at_zero_cost": zero_edge,
            "search_cap_bps": max_cost_bps,
        }
    if high_edge > 0.0:
        return {
            "one_way_bps": max_cost_bps,
            "status": "above_search_cap",
            "edge_at_zero_cost": zero_edge,
            "edge_at_search_cap": high_edge,
            "search_cap_bps": max_cost_bps,
        }
    low, high = 0.0, max_cost_bps
    for _ in range(80):
        midpoint = (low + high) / 2.0
        if edge(midpoint) > 0.0:
            low = midpoint
        else:
            high = midpoint
    return {
        "one_way_bps": float((low + high) / 2.0),
        "status": "root_within_search_range",
        "edge_at_zero_cost": zero_edge,
        "search_cap_bps": max_cost_bps,
    }


def _build_period(
    *,
    name: str,
    start: pd.Period,
    end: pd.Period,
    candidate_by_cost: dict[str, ReturnPath],
    candidate_gross: pd.Series,
    baselines: dict[str, ReturnPath],
    risk_free: pd.Series,
    split_ranges: list[tuple[str, pd.Period, pd.Period]],
    pbo: dict[str, Any],
) -> dict[str, Any]:
    candidate = _slice_path(candidate_by_cost["10"], start, end)
    candidate_50 = _slice_path(candidate_by_cost["50"], start, end)
    period_baselines = {key: _slice_path(value, start, end) for key, value in baselines.items()}
    candidate_metrics = _metrics(candidate, risk_free)
    candidate_50_metrics = _metrics(candidate_50, risk_free)
    baseline_metrics = {key: _metrics(value, risk_free) for key, value in period_baselines.items()}
    comparisons = {key: _active_comparison(candidate, value) for key, value in period_baselines.items()}
    rolling_market = _rolling_comparison(candidate, period_baselines["market"])
    rolling_equal = _rolling_comparison(candidate, period_baselines["decile_equal"])
    fixed_splits: dict[str, Any] = {}
    for label, split_start, split_end in split_ranges:
        split_candidate = _metrics(_slice_path(candidate, split_start, split_end), risk_free)
        split_market = _metrics(_slice_path(period_baselines["market"], split_start, split_end), risk_free)
        split_equal = _metrics(_slice_path(period_baselines["decile_equal"], split_start, split_end), risk_free)
        fixed_splits[label] = {
            "candidate_cagr": split_candidate["cagr"],
            "market_cagr": split_market["cagr"],
            "decile_equal_cagr": split_equal["cagr"],
            "edge_vs_market": float(split_candidate["cagr"] - split_market["cagr"]),
            "edge_vs_decile_equal": float(split_candidate["cagr"] - split_equal["cagr"]),
        }

    gates = {
        "candidate_10bps_cagr_beats_market_by_2pp": candidate_metrics["cagr"] >= baseline_metrics["market"]["cagr"] + 0.02,
        "candidate_10bps_cagr_beats_decile_equal_by_2pp": candidate_metrics["cagr"] >= baseline_metrics["decile_equal"]["cagr"] + 0.02,
        "candidate_10bps_cagr_beats_lo_prior_by_2pp": candidate_metrics["cagr"] >= baseline_metrics["lo_prior_1_0"]["cagr"] + 0.02,
        "candidate_10bps_cagr_beats_long_momentum_hi_by_50bp": candidate_metrics["cagr"] >= baseline_metrics["long_momentum_hi_12_2"]["cagr"] + 0.005,
        "candidate_excess_sharpe_beats_all_four_baselines": all(candidate_metrics["excess_sharpe"] > value["excess_sharpe"] for value in baseline_metrics.values()),
        "candidate_drawdown_not_over_5pp_deeper_than_market_or_equal": candidate_metrics["max_drawdown"] >= min(baseline_metrics["market"]["max_drawdown"], baseline_metrics["decile_equal"]["max_drawdown"]) - 0.05,
        "candidate_50bps_cagr_beats_market_by_50bp": candidate_50_metrics["cagr"] >= baseline_metrics["market"]["cagr"] + 0.005,
        "both_fixed_halves_beat_market_and_equal_by_50bp": all(value["edge_vs_market"] >= 0.005 and value["edge_vs_decile_equal"] >= 0.005 for value in fixed_splits.values()),
        "rolling_60m_vs_market_60pct_and_positive_median": rolling_market["cagr_win_fraction"] >= 0.60 and rolling_market["median_cagr_difference"] > 0.0,
        "rolling_60m_vs_equal_60pct_and_positive_median": rolling_equal["cagr_win_fraction"] >= 0.60 and rolling_equal["median_cagr_difference"] > 0.0,
        "active_newey_west_t_vs_market_at_least_1_96": comparisons["market"]["newey_west"]["t_stat"] >= 1.96,
        "active_newey_west_t_vs_equal_at_least_1_96": comparisons["decile_equal"]["newey_west"]["t_stat"] >= 1.96,
        "active_psr_vs_market_and_equal_at_least_95pct": all(comparisons[key]["active_probabilistic_sharpe"]["probability"] >= 0.95 for key in ("market", "decile_equal")),
        "active_global_dsr_vs_market_and_equal_at_least_95pct": all(comparisons[key]["active_global_deflated_sharpe"]["probability"] >= 0.95 for key in ("market", "decile_equal")),
        "six_path_pbo_not_above_20pct": bool(np.isfinite(pbo["pbo"]) and pbo["pbo"] <= 0.20),
    }
    break_even = {
        key: _candidate_cost_break_even(
            candidate_gross,
            value,
            start=start,
            end=end,
        )
        for key, value in period_baselines.items()
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
        "rolling_60m_vs_decile_equal": rolling_equal,
        "cost_break_even_vs_baselines": break_even,
        "gates": gates,
        "passed_gate_count": int(sum(bool(value) for value in gates.values())),
        "required_gate_count": 15,
        "all_gates_pass": all(gates.values()),
    }


def build_french_prior_return_schema_repair_research(root: str | Path) -> dict[str, Any]:
    root_path = Path(root)
    data = load_frozen_prior_return_data(root_path)
    short_value = data["short_value"]
    short_equal = data["short_equal"]
    long_value = data["long_value"]
    factors = data["factors"]
    market_gross = (factors["Mkt-RF"] + factors["RF"]).rename("market")

    weights_linear = np.arange(1.0, 11.0)
    weights_linear /= weights_linear.sum()
    weights_square = np.arange(1.0, 11.0) ** 2
    weights_square /= weights_square.sum()
    gross_candidates = {
        "vw_hi_prior_1_0": short_value["Hi PRIOR"].rename("vw_hi_prior_1_0"),
        "vw_top_2": short_value[["PRIOR 9", "Hi PRIOR"]].mean(axis=1).rename("vw_top_2"),
        "vw_top_3": short_value[["PRIOR 8", "PRIOR 9", "Hi PRIOR"]].mean(axis=1).rename("vw_top_3"),
        "vw_linear_tilt": short_value.mul(weights_linear, axis=1).sum(axis=1).rename("vw_linear_tilt"),
        "vw_square_tilt": short_value.mul(weights_square, axis=1).sum(axis=1).rename("vw_square_tilt"),
        "ew_hi_prior_1_0": short_equal["Hi PRIOR"].rename("ew_hi_prior_1_0"),
    }
    candidate_paths = {
        name: apply_full_reconstitution_cost(series, PRIMARY_COST_BPS)
        for name, series in gross_candidates.items()
    }
    primary_by_cost = {
        str(int(cost)): apply_full_reconstitution_cost(gross_candidates["vw_hi_prior_1_0"], cost)
        for cost in (PRIMARY_COST_BPS, *STRESS_COST_BPS)
    }
    baselines = {
        "market": apply_buy_and_hold_entry_cost(market_gross, PRIMARY_COST_BPS),
        "decile_equal": apply_full_reconstitution_cost(short_value.mean(axis=1).rename("decile_equal"), PRIMARY_COST_BPS),
        "lo_prior_1_0": apply_full_reconstitution_cost(short_value["Lo PRIOR"].rename("lo_prior_1_0"), PRIMARY_COST_BPS),
        "long_momentum_hi_12_2": apply_full_reconstitution_cost(long_value["Hi PRIOR"].rename("long_momentum_hi_12_2"), PRIMARY_COST_BPS),
    }
    pbo_primary = probability_of_backtest_overfitting(
        pd.concat({name: _slice_path(path, FORMAL_START, PRIMARY_END).returns for name, path in candidate_paths.items()}, axis=1),
        slices=10,
    )
    pbo_recent = probability_of_backtest_overfitting(
        pd.concat({name: _slice_path(path, RECENT_START, FORMAL_END).returns for name, path in candidate_paths.items()}, axis=1),
        slices=10,
    )
    primary = _build_period(
        name="主要外部期",
        start=FORMAL_START,
        end=PRIMARY_END,
        candidate_by_cost=primary_by_cost,
        candidate_gross=gross_candidates["vw_hi_prior_1_0"],
        baselines=baselines,
        risk_free=factors["RF"],
        split_ranges=[
            ("1963_to_1984", FORMAL_START, pd.Period("1984-12", freq="M")),
            ("1985_to_2005", pd.Period("1985-01", freq="M"), PRIMARY_END),
        ],
        pbo=pbo_primary,
    )
    recent = _build_period(
        name="近期確認期",
        start=RECENT_START,
        end=FORMAL_END,
        candidate_by_cost=primary_by_cost,
        candidate_gross=gross_candidates["vw_hi_prior_1_0"],
        baselines=baselines,
        risk_free=factors["RF"],
        split_ranges=[
            ("2006_to_2015", RECENT_START, pd.Period("2015-12", freq="M")),
            ("2016_to_end", pd.Period("2016-01", freq="M"), FORMAL_END),
        ],
        pbo=pbo_recent,
    )

    repair_receipt, original_receipt = _verify_repair_receipts(root_path)
    data_gates = {
        "repair_protocol_and_mapping_frozen_before_numeric_calculation": repair_receipt["protocol"]["sha256"] == REPAIR_PROTOCOL_SHA256 and repair_receipt["mapping"]["sha256"] == REPAIR_MAPPING_SHA256 and repair_receipt["numeric_calculation_started"] is False,
        "all_five_archive_hashes_and_members_match": all(data["archives"][role]["sha256"] == contract["sha256"] and data["archives"][role]["member"] == contract["member"] for role, contract in ARCHIVE_CONTRACTS.items()),
        "four_exact_schema_informed_markers_match": all(data["markers"][key] == TABLE_MARKERS[key] for key in TABLE_MARKERS),
        "value_and_equal_tables_have_exact_ten_columns": all(list(data[key].columns) == DECILE_COLUMNS for key in ("short_value", "short_equal", "long_value", "long_equal")),
        "common_formal_period_is_1963_01_to_2026_05": data["common_index"][0] == FORMAL_START and data["common_index"][-1] == FORMAL_END and len(data["common_index"]) == 761,
        "formal_period_has_zero_missing_without_imputation": all(not data[key].isna().any().any() for key in ("short_value", "short_equal", "long_value", "long_equal", "factors")),
        "factor_headers_and_market_rf_mom_strev_complete": list(factors.columns) == ["Mkt-RF", "SMB", "HML", "RF", "Mom", "ST_Rev"] and not factors.isna().any().any(),
        "original_6_of_8_failure_preserved_and_no_redownload": original_receipt["passed_check_count"] == 6 and original_receipt["strategy_calculation_started"] is False and repair_receipt["new_download_allowed"] is False and repair_receipt["economic_design_changed"] is False,
    }
    economic_diagnostic_passed = all(data_gates.values()) and primary["all_gates_pass"] and recent["all_gates_pass"]
    full_primary = _slice_path(primary_by_cost["10"], FORMAL_START, FORMAL_END)
    full_baselines = {key: _slice_path(path, FORMAL_START, FORMAL_END) for key, path in baselines.items()}
    full_sensitivity = {
        name: _metrics(_slice_path(path, FORMAL_START, FORMAL_END), factors["RF"])
        for name, path in candidate_paths.items()
    }
    passed_gate_count = int(sum(data_gates.values())) + primary["passed_gate_count"] + recent["passed_gate_count"]
    return {
        "schema_version": SCHEMA_VERSION,
        "status": (
            "schema_repair_engineering_passed_and_economic_diagnostic_passed_but_non_independent"
            if economic_diagnostic_passed
            else "schema_repair_engineering_passed_but_economic_diagnostic_failed"
        ),
        "research_role": "schema_informed_engineering_diagnostic_not_first_seen_validation",
        "schema_repair_engineering_passed": all(data_gates.values()),
        "economic_diagnostic_passed": bool(economic_diagnostic_passed),
        "independent_first_seen_evidence": False,
        "paper_eligible": False,
        "paper_state_created": False,
        "trade_ready": False,
        "real_money_action_usd": 0,
        "protocol": {
            "repair_protocol_sha256": REPAIR_PROTOCOL_SHA256,
            "repair_mapping_sha256": REPAIR_MAPPING_SHA256,
            "repair_protocol_commit": REPAIR_PROTOCOL_COMMIT,
            "original_economic_protocol_sha256": ORIGINAL_PROTOCOL_SHA256,
            "original_economic_protocol_commit": ORIGINAL_PROTOCOL_COMMIT,
            "economic_design_changed": False,
            "global_search_trials": GLOBAL_SEARCH_TRIALS,
            "monthly_periods_per_year": MONTHS_PER_YEAR,
            "newey_west_lag_months": NEWEY_WEST_LAG_MONTHS,
        },
        "snapshot": {
            "archives": data["archives"],
            "formal_start": str(FORMAL_START),
            "formal_end": str(FORMAL_END),
            "formal_months": len(data["common_index"]),
            "raw_missing_code_counts_all_source_history": data["raw_missing_codes"],
            "survivorship_reduced_not_raw_point_in_time_stock_ledger": True,
            "new_download_performed_for_repair": False,
        },
        "frozen_candidate": {
            "label": "VW Hi PRIOR 1–1 月度贏家",
            "portfolio_formation": "月 t-1 形成，直接使用月 t 官方組合總回報",
            "cost_model": "首月買入一次；其後每月完整賣出再買入",
            "cost_sensitivity_full_history": {
                f"{cost}_bps": _metrics(_slice_path(path, FORMAL_START, FORMAL_END), factors["RF"])
                for cost, path in primary_by_cost.items()
            },
            "full_history_metrics_10bps": _metrics(full_primary, factors["RF"]),
        },
        "full_history_baseline_metrics": {
            key: _metrics(path, factors["RF"]) for key, path in full_baselines.items()
        },
        "sensitivity_full_history_metrics_10bps": full_sensitivity,
        "primary_external_period": primary,
        "recent_confirmation_period": recent,
        "pbo": {"primary": pbo_primary, "recent": pbo_recent},
        "factor_regression_full_history": _factor_regression(full_primary, factors),
        "stress_periods": _stress_summary({"candidate": full_primary, **full_baselines}),
        "data_gates": data_gates,
        "passed_gate_count": passed_gate_count,
        "required_gate_count": 38,
        "gate_breakdown": {
            "data": f"{sum(data_gates.values())}/8",
            "primary": f"{primary['passed_gate_count']}/15",
            "recent": f"{recent['passed_gate_count']}/15",
        },
        "paper_blockers": {
            "qualified_point_in_time_stock_constituents_and_delisting_ledger": False,
            "exact_stock_turnover_spreads_and_corporate_actions": False,
            "tradeable_stock_mapping_and_d_plus_1_orders": False,
            "authorized_crsp_wrds_norgate_or_equivalent_provider": False,
        },
        "decision": (
            "保留同一已見 schema 快照的完整正負工程診斷；原 6/8 首次下載失敗不被覆蓋。"
            "即使 38/38 亦非獨立首次證據，French 學術組合不能產生個股名單或 Paper。"
            "只有合格逐股 point-in-time、退市／收購、公司行動及精確成交成本另行通過，"
            "才可由全現金建立隔離 Paper；實金動作固定 US$0。"
        ),
    }
