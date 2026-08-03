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

import exchange_calendars as xcals
import numpy as np
import pandas as pd

from usfddk.data import load_snapshot, panel_fingerprint
from usfddk.metrics import newey_west_mean_test
from usfddk.validation import (
    deflated_sharpe_ratio,
    probabilistic_sharpe_ratio,
    probability_of_backtest_overfitting,
)

PROTOCOL_SHA256 = "aee1d081bcbfbd819d6c6a6a3362e241e0aab8585cb087e45fed2d1f30464cdc"
MAPPING_SHA256 = "7ee12c479383810cae133a39951a4b3b20ddee3dbeb7c1c38ec79e753578baa1"
REPAIR_PROTOCOL_SHA256 = "57987c7b49e03bbcb2bf9e159398bc05e37032d5285d74667a41164b7687ffe6"
DATA_ARCHIVE_SHA256 = "a19daa6c84ef6232f3f867159e2752c2a437d5990d6f3bf673fd91317eab6093"
FACTOR_ARCHIVE_SHA256 = "af8aec07d55c98caa15045a77b87455be68cb8847b2ee5bd03bf5c2c8a3f96e2"
PRODUCT_ARCHIVE_SHA256 = "d480fb82e712f06aabe0a98461e222344656b87022b8bda2cd7ccaa4c29ae88b"
PRODUCT_PANEL_SHA256 = "6a7ca6b83b1570007424daa46b0ff4e8fb4a655d39298a0f4f6d74c3b7ea3a66"

DATA_ARCHIVE_PATH = "artifacts/french_10_prior_12_2_daily_a19daa6c.zip"
FACTOR_ARCHIVE_PATH = "artifacts/french_ff_factors_daily_af8aec07.zip"
PRODUCT_ARCHIVE_PATH = "artifacts/snapshot_20260731_6a7ca6b8.zip"
EXPECTED_MEMBER = "10_Portfolios_Prior_12_2_Daily.csv"
REPAIRED_MARKER = "Average Value Weighted Returns -- Daily"
PRIOR_COLUMNS = [
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

EARLY_START = pd.Timestamp("1963-07-01")
EARLY_END = pd.Timestamp("2006-05-31")
RECENT_START = pd.Timestamp("2006-06-01")
RECENT_END = pd.Timestamp("2026-05-29")
PRIMARY_DRAG = 0.05
DRAG_SENSITIVITY = (0.02, 0.05, 0.10)
PRIMARY_COST_BPS = 10.0
COST_SENSITIVITY_BPS = (10.0, 25.0, 50.0)
GLOBAL_SEARCH_TRIALS = 6_208
PERIODS_PER_YEAR = 252
NEWEY_WEST_LAG = 20


@dataclass(frozen=True)
class DailyPath:
    returns: pd.Series
    turnover: pd.Series
    exposure: pd.Series


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _read_single_csv(path: Path, expected_member: str) -> str:
    with zipfile.ZipFile(path) as archive:
        members = archive.namelist()
        if members != [expected_member]:
            raise ValueError(f"{path.name} ZIP member 不符：{members}")
        raw = archive.read(expected_member)
    return raw.decode("utf-8", errors="strict")


def _parse_daily_rows(
    rows: list[list[str]],
    *,
    header_index: int,
    columns: list[str],
) -> tuple[pd.DataFrame, int]:
    dates: list[pd.Timestamp] = []
    values: list[list[float]] = []
    missing_codes = 0
    started = False
    for row in rows[header_index + 1 :]:
        first = row[0].strip() if row else ""
        if len(first) != 8 or not first.isdigit():
            if started:
                break
            continue
        started = True
        if len(row) != len(columns) + 1:
            raise ValueError(f"每日表 {first} 欄數不符")
        parsed: list[float] = []
        for cell in row[1:]:
            raw = float(cell.strip())
            if raw in (-99.99, -999.0):
                missing_codes += 1
                parsed.append(float("nan"))
            else:
                parsed.append(raw / 100.0)
        dates.append(pd.to_datetime(first, format="%Y%m%d", errors="raise"))
        values.append(parsed)
    if not dates:
        raise ValueError("每日表沒有數值列")
    frame = pd.DataFrame(values, index=pd.DatetimeIndex(dates), columns=columns)
    if frame.index.has_duplicates or not frame.index.is_monotonic_increasing:
        raise ValueError("每日表日期重複或未遞增")
    if missing_codes or frame.isna().any().any():
        raise ValueError(f"每日表含 {missing_codes} 個缺值碼或空值")
    if not np.isfinite(frame.to_numpy(dtype=float)).all():
        raise ValueError("每日表含非有限值")
    return frame, missing_codes


def parse_repaired_prior_daily(path: Path) -> tuple[pd.DataFrame, dict[str, Any]]:
    text = _read_single_csv(path, EXPECTED_MEMBER)
    rows = list(csv.reader(io.StringIO(text)))
    markers = [
        index
        for index, row in enumerate(rows)
        if len(row) == 1 and row[0].strip() == REPAIRED_MARKER
    ]
    if len(markers) != 1:
        raise ValueError(f"repair marker 必須精確命中一次，實際 {len(markers)}")
    header_index = markers[0] + 1
    if header_index >= len(rows):
        raise ValueError("repair marker 後沒有 header")
    columns = [cell.strip() for cell in rows[header_index][1:]]
    if columns != PRIOR_COLUMNS:
        raise ValueError(f"每日 Prior 欄序不符：{columns}")
    frame, missing_codes = _parse_daily_rows(
        rows,
        header_index=header_index,
        columns=PRIOR_COLUMNS,
    )
    return frame, {
        "marker": REPAIRED_MARKER,
        "member": EXPECTED_MEMBER,
        "rows": int(len(frame)),
        "columns": list(frame.columns),
        "first_date": frame.index[0].date().isoformat(),
        "last_date": frame.index[-1].date().isoformat(),
        "raw_missing_codes": missing_codes,
        "missing_values": int(frame.isna().sum().sum()),
        "maximum_absolute_daily_return": float(frame.abs().max().max()),
    }


def parse_daily_factors(path: Path) -> pd.DataFrame:
    text = _read_single_csv(path, "F-F_Research_Data_Factors_daily.csv")
    rows = list(csv.reader(io.StringIO(text)))
    columns = ["Mkt-RF", "SMB", "HML", "RF"]
    headers = [
        index for index, row in enumerate(rows) if [cell.strip() for cell in row[1:]] == columns
    ]
    if len(headers) != 1:
        raise ValueError(f"French daily factors header 不是唯一：{headers}")
    frame, _ = _parse_daily_rows(rows, header_index=headers[0], columns=columns)
    return frame


def _verify_frozen_inputs(root: Path) -> dict[str, Any]:
    protocol = root / "docs/SHORT_TERM_DAILY_MOMENTUM_REGIME_PROTOCOL.md"
    mapping = root / "docs/SHORT_TERM_DAILY_MOMENTUM_REGIME_DATA_MAPPING.md"
    repair = root / "docs/SHORT_TERM_DAILY_MOMENTUM_REGIME_SCHEMA_REPAIR_PROTOCOL.md"
    if _sha256(protocol) != PROTOCOL_SHA256 or _sha256(mapping) != MAPPING_SHA256:
        raise ValueError("第十輪原協議或映射雜湊不符")
    if _sha256(repair) != REPAIR_PROTOCOL_SHA256:
        raise ValueError("每日動量 schema repair 協議雜湊不符")

    original = json.loads(
        (root / "artifacts/short_term_daily_momentum_regime_data_receipt.json").read_text(
            encoding="utf-8"
        )
    )
    repaired = json.loads(
        (
            root / "artifacts/short_term_daily_momentum_regime_schema_repair_receipt.json"
        ).read_text(encoding="utf-8")
    )
    preregistration = json.loads(
        (root / "artifacts/short_term_daily_momentum_regime_protocol_receipt.json").read_text(
            encoding="utf-8"
        )
    )
    if (
        original.get("status")
        != "daily_momentum_regime_first_download_contract_failed_before_strategy"
        or original.get("passed_check_count") != 4
        or original.get("required_check_count") != 9
        or original.get("numeric_return_rows_parsed") is not False
        or original.get("strategy_calculation_started") is not False
    ):
        raise ValueError("第十輪 4/9 原始失敗收據被改動")
    expected_repair = {
        "status": "schema_repair_frozen_before_first_aggregate_or_strategy_result",
        "schema_seen_before_repair_freeze": True,
        "initial_numeric_rows_visible_during_schema_inspection": True,
        "numeric_rows_parsed_before_repair_freeze": False,
        "strategy_results_computed_before_repair_freeze": False,
        "independent_first_seen_evidence": False,
        "candidate_or_gate_changed": False,
        "global_search_trials": GLOBAL_SEARCH_TRIALS,
        "required_gate_count": 48,
    }
    if any(repaired.get(key) != value for key, value in expected_repair.items()):
        raise ValueError("每日動量 schema repair 凍結邊界不符")
    if repaired.get("repair_protocol_sha256") != REPAIR_PROTOCOL_SHA256:
        raise ValueError("每日動量 schema repair 收據雜湊不符")
    if (
        preregistration.get("status")
        != "protocol_frozen_before_first_daily_prior_download"
        or preregistration.get("protocol_sha256") != PROTOCOL_SHA256
        or preregistration.get("data_mapping_sha256") != MAPPING_SHA256
        or preregistration.get("new_data_downloaded_at_freeze") is not False
        or preregistration.get("strategy_results_computed_at_freeze") is not False
        or not (
            preregistration["frozen_at_utc"]
            < original["downloaded_at_utc"]
            < repaired["frozen_at_utc"]
        )
    ):
        raise ValueError("每日動量協議／下載／repair 時序或凍結收據不符")

    archive = root / DATA_ARCHIVE_PATH
    factors = root / FACTOR_ARCHIVE_PATH
    products = root / PRODUCT_ARCHIVE_PATH
    if _sha256(archive) != DATA_ARCHIVE_SHA256:
        raise ValueError("French 每日 Prior 原始 ZIP 雜湊不符")
    if _sha256(factors) != FACTOR_ARCHIVE_SHA256:
        raise ValueError("French daily factor ZIP 雜湊不符")
    if _sha256(products) != PRODUCT_ARCHIVE_SHA256:
        raise ValueError("QQQ／SPY 既有快照 archive 雜湊不符")
    return {
        "preregistration_receipt": preregistration,
        "original_receipt": original,
        "repair_receipt": repaired,
    }


def load_frozen_daily_momentum_data(root: str | Path) -> dict[str, Any]:
    root_path = Path(root)
    receipts = _verify_frozen_inputs(root_path)
    prior, prior_meta = parse_repaired_prior_daily(root_path / DATA_ARCHIVE_PATH)
    factors = parse_daily_factors(root_path / FACTOR_ARCHIVE_PATH)
    panel, manifest = load_snapshot(root_path / PRODUCT_ARCHIVE_PATH)
    if panel_fingerprint(panel) != PRODUCT_PANEL_SHA256:
        raise ValueError("QQQ／SPY 既有快照 panel 雜湊不符")
    if not {"QQQ", "SPY"}.issubset(panel.close.columns):
        raise ValueError("既有快照缺 QQQ／SPY")
    product_returns = panel.close[["QQQ", "SPY"]].pct_change(fill_method=None)

    common_academic = prior.index.intersection(factors.index).sort_values()
    if len(common_academic) < 20_000:
        raise ValueError("French 每日 Prior 與市場共同日數不足")
    prior = prior.reindex(common_academic)
    factors = factors.reindex(common_academic)
    if prior.isna().any().any() or factors[["Mkt-RF", "RF"]].isna().any().any():
        raise ValueError("French 共同日含缺值")

    recent_sessions = (
        xcals.get_calendar("XNYS", start=RECENT_START, end=RECENT_END)
        .sessions_in_range(RECENT_START, RECENT_END)
        .tz_localize(None)
    )
    french_recent = common_academic[
        (common_academic >= RECENT_START) & (common_academic <= RECENT_END)
    ]
    coverage = len(french_recent.intersection(recent_sessions)) / len(recent_sessions)
    recent_common = (
        french_recent.intersection(product_returns.dropna(how="any").index).sort_values()
    )
    return {
        **receipts,
        "prior": prior,
        "prior_meta": prior_meta,
        "factors": factors,
        "product_returns": product_returns,
        "product_manifest": manifest,
        "recent_sessions": recent_sessions,
        "recent_french_coverage": float(coverage),
        "recent_common": recent_common,
    }


def _trailing_total_return(returns: pd.Series, window: int) -> pd.Series:
    wealth = (1.0 + returns).cumprod()
    return wealth.div(wealth.shift(window)).sub(1.0)


def build_exposure_signals(
    prior: pd.DataFrame,
    market: pd.Series,
) -> pd.DataFrame:
    prior_wealth = (1.0 + prior).cumprod()
    market_wealth = (1.0 + market).cumprod()
    pool = prior.mean(axis=1)
    market_20 = market_wealth > market_wealth.rolling(20, min_periods=20).mean()
    market_60 = market_wealth > market_wealth.rolling(60, min_periods=60).mean()
    breadth = (
        prior_wealth.gt(prior_wealth.rolling(60, min_periods=60).mean()).mean(axis=1)
        >= 0.60
    )
    resonance_windows = pd.DataFrame(
        {
            str(window): _trailing_total_return(prior["Hi PRIOR"], window)
            > _trailing_total_return(pool, window)
            for window in (5, 10, 15, 20)
        }
    )
    resonance_count = resonance_windows.sum(axis=1)
    resonance = resonance_count >= 2
    score = (
        market_20.astype(int)
        + market_60.astype(int)
        + breadth.astype(int)
        + resonance.astype(int)
    )
    exposure = pd.Series(
        np.select([score <= 1, score == 2, score >= 3], [0.0, 0.5, 1.0], default=np.nan),
        index=score.index,
        name="candidate_exposure",
    ).shift(1)

    no_resonance_score = market_20.astype(int) + market_60.astype(int) + breadth.astype(int)
    no_resonance = pd.Series(
        np.select(
            [no_resonance_score <= 1, no_resonance_score == 2, no_resonance_score == 3],
            [0.0, 0.5, 1.0],
            default=np.nan,
        ),
        index=score.index,
        name="no_resonance_exposure",
    ).shift(1)
    binary_60 = market_60.astype(float).shift(1).rename("binary_60_exposure")
    return pd.DataFrame(
        {
            "market_above_20": market_20.shift(1).astype("boolean"),
            "market_above_60": market_60.shift(1).astype("boolean"),
            "breadth_at_least_60pct": breadth.shift(1).astype("boolean"),
            "resonance_count": resonance_count.shift(1),
            "resonance_at_least_two": resonance.shift(1).astype("boolean"),
            "score": score.shift(1),
            "candidate_exposure": exposure,
            "binary_60_exposure": binary_60,
            "no_resonance_exposure": no_resonance,
        },
        index=prior.index,
    )


def _apply_exposure(
    risk_return: pd.Series,
    risk_free: pd.Series,
    exposure: pd.Series,
    *,
    cost_bps: float,
    annual_drag: float,
) -> DailyPath:
    aligned = pd.concat(
        [
            risk_return.rename("risk"),
            risk_free.rename("rf"),
            exposure.rename("exposure"),
        ],
        axis=1,
        join="inner",
    ).dropna()
    if aligned.empty:
        raise ValueError("曝險路徑沒有共同日")
    if not aligned["exposure"].between(0.0, 1.0).all():
        raise ValueError("曝險超出 0–100%")
    drag_multiplier = (1.0 - float(annual_drag)) ** (1.0 / PERIODS_PER_YEAR)
    adjusted_risk = (1.0 + aligned["risk"]) * drag_multiplier - 1.0
    gross = aligned["exposure"] * adjusted_risk + (1.0 - aligned["exposure"]) * aligned["rf"]
    turnover = aligned["exposure"].diff().abs()
    turnover.iloc[0] = abs(float(aligned["exposure"].iloc[0]))
    costs = turnover * float(cost_bps) / 10_000.0
    returns = ((1.0 + gross) * (1.0 - costs) - 1.0).rename("return")
    return DailyPath(
        returns=returns,
        turnover=turnover.rename("turnover"),
        exposure=aligned["exposure"].rename("exposure"),
    )


def _buy_and_hold(returns: pd.Series, cost_bps: float) -> DailyPath:
    values = returns.dropna().astype(float).copy()
    if values.empty:
        raise ValueError("買入持有路徑沒有回報")
    turnover = pd.Series(0.0, index=values.index, name="turnover")
    turnover.iloc[0] = 1.0
    rate = float(cost_bps) / 10_000.0
    values.iloc[0] = (1.0 + values.iloc[0]) * (1.0 - rate) - 1.0
    return DailyPath(
        returns=values.rename("return"),
        turnover=turnover,
        exposure=pd.Series(1.0, index=values.index, name="exposure"),
    )


def _slice(path: DailyPath, start: pd.Timestamp, end: pd.Timestamp) -> DailyPath:
    index = path.returns.loc[start:end].index
    return DailyPath(
        returns=path.returns.reindex(index),
        turnover=path.turnover.reindex(index).fillna(0.0),
        exposure=path.exposure.reindex(index),
    )


def _metrics(path: DailyPath, risk_free: pd.Series) -> dict[str, float | int]:
    aligned = pd.concat(
        [path.returns.rename("return"), risk_free.rename("rf")],
        axis=1,
        join="inner",
    ).dropna()
    values = aligned["return"]
    if len(values) < 2:
        raise ValueError("日回報期不足")
    wealth = (1.0 + values).cumprod()
    anchored = pd.Series(np.r_[1.0, wealth.to_numpy(dtype=float)])
    years = len(values) / PERIODS_PER_YEAR
    cagr = float(wealth.iloc[-1] ** (1.0 / years) - 1.0)
    volatility = float(values.std(ddof=1) * math.sqrt(PERIODS_PER_YEAR))
    excess = aligned["return"] - aligned["rf"]
    excess_std = float(excess.std(ddof=1))
    excess_sharpe = (
        float(excess.mean() / excess_std * math.sqrt(PERIODS_PER_YEAR))
        if excess_std > 0.0
        else 0.0
    )
    downside = values[values < 0.0]
    downside_std = float(downside.std(ddof=1))
    sortino = (
        float(values.mean() / downside_std * math.sqrt(PERIODS_PER_YEAR))
        if downside_std > 0.0
        else 0.0
    )
    max_drawdown = float((anchored / anchored.cummax() - 1.0).min())
    exposure = path.exposure.reindex(values.index).dropna()
    return {
        "total_return": float(wealth.iloc[-1] - 1.0),
        "cagr": cagr,
        "volatility": volatility,
        "excess_sharpe": excess_sharpe,
        "sortino": sortino,
        "max_drawdown": max_drawdown,
        "calmar": cagr / abs(max_drawdown) if max_drawdown < 0.0 else 0.0,
        "annual_turnover": float(path.turnover.reindex(values.index).sum() / years),
        "average_exposure": float(exposure.mean()),
        "minimum_exposure": float(exposure.min()),
        "maximum_exposure": float(exposure.max()),
        "sessions": int(len(values)),
        "hypothetical_1000_usd_end": float(1_000.0 * wealth.iloc[-1]),
        "worst_day": float(values.min()),
    }


def _comparison(candidate: DailyPath, benchmark: DailyPath) -> dict[str, Any]:
    aligned = pd.concat(
        [candidate.returns.rename("candidate"), benchmark.returns.rename("benchmark")],
        axis=1,
        join="inner",
    ).dropna()
    active = aligned["candidate"] - aligned["benchmark"]
    return {
        "sessions": int(len(active)),
        "annualized_arithmetic": float(active.mean() * PERIODS_PER_YEAR),
        "newey_west": newey_west_mean_test(
            active,
            max_lag=NEWEY_WEST_LAG,
            periods_per_year=PERIODS_PER_YEAR,
        ),
        "active_probabilistic_sharpe": probabilistic_sharpe_ratio(
            active,
            periods_per_year=PERIODS_PER_YEAR,
        ),
        "active_global_deflated_sharpe": deflated_sharpe_ratio(
            active,
            trials=GLOBAL_SEARCH_TRIALS,
            periods_per_year=PERIODS_PER_YEAR,
        ),
    }


def _rolling_three_year(candidate: DailyPath, benchmark: DailyPath) -> dict[str, Any]:
    aligned = pd.concat(
        [candidate.returns.rename("candidate"), benchmark.returns.rename("benchmark")],
        axis=1,
        join="inner",
    ).dropna()
    window = 756
    if len(aligned) < window:
        return {"window_sessions": window, "observations": 0, "series": []}
    month = aligned.index.to_period("M")
    end_positions = np.flatnonzero(np.r_[month[:-1] != month[1:], True])
    rows: list[dict[str, Any]] = []
    for position in end_positions:
        if position < window - 1:
            continue
        sample = aligned.iloc[position - window + 1 : position + 1]
        candidate_cagr = float((1.0 + sample["candidate"]).prod() ** (252.0 / window) - 1.0)
        benchmark_cagr = float((1.0 + sample["benchmark"]).prod() ** (252.0 / window) - 1.0)
        rows.append(
            {
                "end": aligned.index[position].date().isoformat(),
                "candidate_cagr": candidate_cagr,
                "benchmark_cagr": benchmark_cagr,
                "cagr_difference": candidate_cagr - benchmark_cagr,
            }
        )
    differences = pd.Series([row["cagr_difference"] for row in rows], dtype=float)
    return {
        "window_sessions": window,
        "observations": int(len(rows)),
        "cagr_win_fraction": float((differences >= 0.001).mean()) if len(rows) else 0.0,
        "median_cagr_difference": float(differences.median()) if len(rows) else 0.0,
        "worst_cagr_difference": float(differences.min()) if len(rows) else 0.0,
        "latest_cagr_difference": float(differences.iloc[-1]) if len(rows) else 0.0,
        "series": rows,
    }


def _fixed_halves(
    candidate: DailyPath,
    benchmark: DailyPath,
    risk_free: pd.Series,
    splits: list[tuple[str, pd.Timestamp, pd.Timestamp]],
) -> dict[str, Any]:
    output: dict[str, Any] = {}
    for label, start, end in splits:
        candidate_metrics = _metrics(_slice(candidate, start, end), risk_free)
        benchmark_metrics = _metrics(_slice(benchmark, start, end), risk_free)
        output[label] = {
            "start": start.date().isoformat(),
            "end": end.date().isoformat(),
            "candidate_cagr": candidate_metrics["cagr"],
            "benchmark_cagr": benchmark_metrics["cagr"],
            "cagr_difference": float(
                candidate_metrics["cagr"] - benchmark_metrics["cagr"]
            ),
        }
    return output


def _stress(
    paths: dict[str, DailyPath],
    periods: dict[str, tuple[str, str]],
) -> dict[str, Any]:
    output: dict[str, Any] = {}
    for label, (start, end) in periods.items():
        rows: dict[str, Any] = {}
        for name, path in paths.items():
            values = path.returns.loc[start:end].dropna()
            if len(values) < 2:
                continue
            wealth = (1.0 + values).cumprod()
            anchored = pd.Series(np.r_[1.0, wealth.to_numpy(dtype=float)])
            rows[name] = {
                "return": float(wealth.iloc[-1] - 1.0),
                "max_drawdown": float((anchored / anchored.cummax() - 1.0).min()),
                "worst_day": float(values.min()),
            }
        output[label] = rows
    return output


def _factor_regression(path: DailyPath, factors: pd.DataFrame) -> dict[str, float]:
    aligned = pd.concat([path.returns.rename("candidate"), factors], axis=1, join="inner").dropna()
    y = (aligned["candidate"] - aligned["RF"]).to_numpy(dtype=float)
    names = ["Mkt-RF", "SMB", "HML"]
    x = np.column_stack([np.ones(len(aligned)), aligned[names].to_numpy(dtype=float)])
    coefficients, _, _, _ = np.linalg.lstsq(x, y, rcond=None)
    fitted = x @ coefficients
    residual = y - fitted
    total_sum = float(np.sum((y - y.mean()) ** 2))
    residual_sum = float(np.sum(residual**2))
    return {
        "annualized_alpha": float(coefficients[0] * PERIODS_PER_YEAR),
        "market_beta": float(coefficients[1]),
        "smb_beta": float(coefficients[2]),
        "hml_beta": float(coefficients[3]),
        "r_squared": float(1.0 - residual_sum / total_sum) if total_sum > 0.0 else 0.0,
    }


def _pbo_summary(paths: dict[str, DailyPath]) -> dict[str, Any]:
    frame = pd.concat({name: path.returns for name, path in paths.items()}, axis=1).dropna()
    result = probability_of_backtest_overfitting(frame, slices=10)
    return {key: value for key, value in result.items() if key != "logits"}


def _period_result(
    *,
    name: str,
    start: pd.Timestamp,
    end: pd.Timestamp,
    prior: pd.DataFrame,
    factors: pd.DataFrame,
    products: pd.DataFrame,
    signals: pd.DataFrame,
    include_products: bool,
) -> tuple[dict[str, Any], dict[str, DailyPath]]:
    period_index = prior.loc[start:end].index.intersection(factors.loc[start:end].index)
    if include_products:
        period_index = period_index.intersection(
            products.loc[start:end].dropna(how="any").index
        )
    period_index = period_index.sort_values()
    period_prior = prior.reindex(period_index)
    period_factors = factors.reindex(period_index)
    period_signals = signals.reindex(period_index)
    hi = period_prior["Hi PRIOR"]
    pool = period_prior.mean(axis=1).rename("prior_pool_equal")
    market = (period_factors["Mkt-RF"] + period_factors["RF"]).rename("market")
    rf = period_factors["RF"]
    candidate = _apply_exposure(
        hi,
        rf,
        period_signals["candidate_exposure"],
        cost_bps=PRIMARY_COST_BPS,
        annual_drag=PRIMARY_DRAG,
    )
    candidate_50 = _apply_exposure(
        hi,
        rf,
        period_signals["candidate_exposure"],
        cost_bps=50.0,
        annual_drag=PRIMARY_DRAG,
    )
    raw_hi = _apply_exposure(
        hi,
        rf,
        pd.Series(1.0, index=hi.index),
        cost_bps=PRIMARY_COST_BPS,
        annual_drag=PRIMARY_DRAG,
    )
    binary = _apply_exposure(
        hi,
        rf,
        period_signals["binary_60_exposure"],
        cost_bps=PRIMARY_COST_BPS,
        annual_drag=PRIMARY_DRAG,
    )
    no_resonance = _apply_exposure(
        hi,
        rf,
        period_signals["no_resonance_exposure"],
        cost_bps=PRIMARY_COST_BPS,
        annual_drag=PRIMARY_DRAG,
    )
    mean_exposure = float(candidate.exposure.mean())
    fixed_average = _apply_exposure(
        hi,
        rf,
        pd.Series(mean_exposure, index=hi.index),
        cost_bps=PRIMARY_COST_BPS,
        annual_drag=PRIMARY_DRAG,
    )
    matched_market = _apply_exposure(
        market,
        rf,
        period_signals["candidate_exposure"],
        cost_bps=PRIMARY_COST_BPS,
        annual_drag=0.0,
    )
    paths: dict[str, DailyPath] = {
        "candidate": candidate,
        "candidate_50bps": candidate_50,
        "french_market": _buy_and_hold(market, PRIMARY_COST_BPS),
        "prior_pool_equal": _buy_and_hold(pool, PRIMARY_COST_BPS),
        "raw_hi_prior": raw_hi,
        "matched_market_exposure": matched_market,
        "fixed_average_exposure": fixed_average,
        "binary_market_60": binary,
        "no_resonance": no_resonance,
    }
    if include_products:
        for ticker in ("QQQ", "SPY"):
            paths[ticker.lower()] = _slice(
                _buy_and_hold(products.reindex(period_index)[ticker], PRIMARY_COST_BPS),
                start,
                end,
            )

    metrics = {key: _metrics(path, rf) for key, path in paths.items()}
    benchmark_keys = [
        "french_market",
        "prior_pool_equal",
        "raw_hi_prior",
        "matched_market_exposure",
        "fixed_average_exposure",
        "binary_market_60",
        "no_resonance",
    ]
    if include_products:
        benchmark_keys.extend(["qqq", "spy"])
    comparisons = {key: _comparison(candidate, paths[key]) for key in benchmark_keys}
    primary_benchmark = "qqq" if include_products else "french_market"
    split_definitions = (
        [
            ("first_10y", pd.Timestamp("2006-06-01"), pd.Timestamp("2016-05-31")),
            ("second_10y", pd.Timestamp("2016-06-01"), pd.Timestamp("2026-05-29")),
        ]
        if include_products
        else [
            ("first_half", pd.Timestamp("1963-07-01"), pd.Timestamp("1984-12-31")),
            ("second_half", pd.Timestamp("1985-01-01"), pd.Timestamp("2006-05-31")),
        ]
    )
    cost_grid: list[dict[str, Any]] = []
    for drag in DRAG_SENSITIVITY:
        for cost in COST_SENSITIVITY_BPS:
            path = _apply_exposure(
                hi,
                rf,
                period_signals["candidate_exposure"],
                cost_bps=cost,
                annual_drag=drag,
            )
            cost_grid.append(
                {
                    "annual_drag": drag,
                    "overlay_cost_bps": cost,
                    "metrics": _metrics(path, rf),
                }
            )
    pbo = _pbo_summary(
        {
            "candidate": candidate,
            "raw_hi_prior": raw_hi,
            "binary_market_60": binary,
            "no_resonance": no_resonance,
        }
    )
    exposure_counts = candidate.exposure.value_counts().sort_index()
    output = {
        "name": name,
        "start": start.date().isoformat(),
        "end": end.date().isoformat(),
        "candidate_metrics": metrics["candidate"],
        "baseline_metrics": {key: metrics[key] for key in benchmark_keys},
        "candidate_50bps_metrics": metrics["candidate_50bps"],
        "comparisons": comparisons,
        "fixed_halves": _fixed_halves(
            candidate,
            paths[primary_benchmark],
            rf,
            split_definitions,
        ),
        "rolling_three_year": _rolling_three_year(candidate, paths[primary_benchmark]),
        "cost_and_drag_grid": cost_grid,
        "pbo": pbo,
        "exposure_diagnostics": {
            "average": mean_exposure,
            "state_sessions": {str(float(key)): int(value) for key, value in exposure_counts.items()},
            "state_fraction": {
                str(float(key)): float(value / len(candidate.exposure))
                for key, value in exposure_counts.items()
            },
            "annual_transitions": metrics["candidate"]["annual_turnover"],
        },
        "factor_regression": _factor_regression(candidate, period_factors),
    }
    return output, paths


def build_daily_momentum_regime_research(root: str | Path) -> dict[str, Any]:
    root_path = Path(root)
    data = load_frozen_daily_momentum_data(root_path)
    prior = data["prior"]
    factors = data["factors"]
    products = data["product_returns"]
    market = factors["Mkt-RF"] + factors["RF"]
    signals = build_exposure_signals(prior, market)

    early, early_paths = _period_result(
        name="early_confirmation",
        start=EARLY_START,
        end=EARLY_END,
        prior=prior,
        factors=factors,
        products=products,
        signals=signals,
        include_products=False,
    )
    recent, recent_paths = _period_result(
        name="recent_20y",
        start=RECENT_START,
        end=RECENT_END,
        prior=prior,
        factors=factors,
        products=products,
        signals=signals,
        include_products=True,
    )

    early_metrics = early["candidate_metrics"]
    early_baselines = early["baseline_metrics"]
    recent_metrics = recent["candidate_metrics"]
    recent_baselines = recent["baseline_metrics"]
    early_comparison = early["comparisons"]["french_market"]
    recent_comparison = recent["comparisons"]["qqq"]
    early_rolling = early["rolling_three_year"]
    recent_rolling = recent["rolling_three_year"]

    early_gates = {
        "candidate_cagr_beats_market_by_2pp": early_metrics["cagr"]
        >= early_baselines["french_market"]["cagr"] + 0.02,
        "candidate_excess_sharpe_beats_market": early_metrics["excess_sharpe"]
        > early_baselines["french_market"]["excess_sharpe"],
        "candidate_drawdown_not_over_5pp_deeper_than_market": early_metrics["max_drawdown"]
        >= early_baselines["french_market"]["max_drawdown"] - 0.05,
        "candidate_50bps_cagr_beats_market_by_50bp": early["candidate_50bps_metrics"]["cagr"]
        >= early_baselines["french_market"]["cagr"] + 0.005,
        "candidate_cagr_beats_raw_hi_prior": early_metrics["cagr"]
        > early_baselines["raw_hi_prior"]["cagr"],
        "candidate_cagr_beats_fixed_average_exposure": early_metrics["cagr"]
        > early_baselines["fixed_average_exposure"]["cagr"],
        "candidate_cagr_beats_matched_market_exposure": early_metrics["cagr"]
        > early_baselines["matched_market_exposure"]["cagr"],
        "both_fixed_halves_beat_market_by_50bp": all(
            row["cagr_difference"] >= 0.005 for row in early["fixed_halves"].values()
        ),
        "rolling_3y_win_fraction_at_least_60pct": early_rolling["cagr_win_fraction"] >= 0.60,
        "rolling_3y_median_difference_positive": early_rolling["median_cagr_difference"] > 0.0,
        "active_newey_west_t_at_least_1_96": early_comparison["newey_west"]["t_stat"] >= 1.96,
        "active_psr_at_least_95pct": early_comparison["active_probabilistic_sharpe"][
            "probability"
        ]
        >= 0.95,
        "active_global_dsr_at_least_95pct": early_comparison["active_global_deflated_sharpe"][
            "probability"
        ]
        >= 0.95,
        "four_path_pbo_not_above_20pct": early["pbo"]["pbo"] <= 0.20,
        "exposure_and_weights_never_leveraged": bool(
            early_metrics["minimum_exposure"] >= 0.0
            and early_metrics["maximum_exposure"] <= 1.0
        ),
    }
    recent_stress = _stress(
        {"candidate": recent_paths["candidate"], "qqq": recent_paths["qqq"]},
        {
            "global_financial_crisis": ("2007-10-09", "2009-03-09"),
            "covid_crash": ("2020-02-19", "2020-03-23"),
            "rate_shock_2022": ("2022-01-03", "2022-12-30"),
        },
    )
    crisis_drawdown_wins = sum(
        rows["candidate"]["max_drawdown"] >= rows["qqq"]["max_drawdown"]
        for rows in recent_stress.values()
    )
    recent_gates = {
        "candidate_cagr_beats_qqq_by_2pp": recent_metrics["cagr"]
        >= recent_baselines["qqq"]["cagr"] + 0.02,
        "candidate_excess_sharpe_beats_qqq": recent_metrics["excess_sharpe"]
        > recent_baselines["qqq"]["excess_sharpe"],
        "candidate_drawdown_not_over_5pp_deeper_than_qqq": recent_metrics["max_drawdown"]
        >= recent_baselines["qqq"]["max_drawdown"] - 0.05,
        "candidate_50bps_cagr_beats_qqq_by_50bp": recent["candidate_50bps_metrics"]["cagr"]
        >= recent_baselines["qqq"]["cagr"] + 0.005,
        "candidate_cagr_beats_spy_by_2pp": recent_metrics["cagr"]
        >= recent_baselines["spy"]["cagr"] + 0.02,
        "candidate_cagr_beats_raw_hi_prior": recent_metrics["cagr"]
        > recent_baselines["raw_hi_prior"]["cagr"],
        "candidate_cagr_beats_fixed_average_exposure": recent_metrics["cagr"]
        > recent_baselines["fixed_average_exposure"]["cagr"],
        "candidate_cagr_beats_matched_market_exposure": recent_metrics["cagr"]
        > recent_baselines["matched_market_exposure"]["cagr"],
        "first_10y_beats_qqq_by_50bp": recent["fixed_halves"]["first_10y"][
            "cagr_difference"
        ]
        >= 0.005,
        "second_10y_beats_qqq_by_50bp": recent["fixed_halves"]["second_10y"][
            "cagr_difference"
        ]
        >= 0.005,
        "rolling_3y_win_fraction_at_least_60pct": recent_rolling["cagr_win_fraction"] >= 0.60,
        "rolling_3y_median_difference_positive": recent_rolling["median_cagr_difference"] > 0.0,
        "active_newey_west_t_at_least_1_96": recent_comparison["newey_west"]["t_stat"] >= 1.96,
        "active_psr_at_least_95pct": recent_comparison["active_probabilistic_sharpe"][
            "probability"
        ]
        >= 0.95,
        "active_global_dsr_at_least_95pct": recent_comparison["active_global_deflated_sharpe"][
            "probability"
        ]
        >= 0.95,
        "four_path_pbo_not_above_20pct": recent["pbo"]["pbo"] <= 0.20,
        "at_least_two_of_three_crisis_drawdowns_not_deeper_than_qqq": crisis_drawdown_wins >= 2,
        "average_exposure_between_25pct_and_90pct": 0.25
        <= recent_metrics["average_exposure"]
        <= 0.90,
        "exposure_and_weights_never_leveraged": bool(
            recent_metrics["minimum_exposure"] >= 0.0
            and recent_metrics["maximum_exposure"] <= 1.0
        ),
    }
    mechanism_gates = {
        "hi_prior_cagr_beats_prior_pool_in_both_periods": bool(
            early_baselines["raw_hi_prior"]["cagr"]
            > early_baselines["prior_pool_equal"]["cagr"]
            and recent_baselines["raw_hi_prior"]["cagr"]
            > recent_baselines["prior_pool_equal"]["cagr"]
        ),
        "candidate_drawdown_improves_raw_hi_in_both_periods": bool(
            early_metrics["max_drawdown"] > early_baselines["raw_hi_prior"]["max_drawdown"]
            and recent_metrics["max_drawdown"]
            > recent_baselines["raw_hi_prior"]["max_drawdown"]
        ),
        "candidate_recent_sharpe_beats_binary_60": recent_metrics["excess_sharpe"]
        > recent_baselines["binary_market_60"]["excess_sharpe"],
        "candidate_recent_sharpe_beats_no_resonance": recent_metrics["excess_sharpe"]
        > recent_baselines["no_resonance"]["excess_sharpe"],
    }
    if len(early_gates) != 15 or len(recent_gates) != 19 or len(mechanism_gates) != 4:
        raise AssertionError("每日動量環境硬門檻數量不符")

    data_gates = {
        "frozen_protocol_mapping_and_repair_hashes_match": True,
        "first_download_postdates_original_freeze_and_was_once": bool(
            data["original_receipt"]["archive"]["downloaded_in_this_run"] is True
            and data["original_receipt"]["downloaded_at_utc"]
            > data["preregistration_receipt"]["frozen_at_utc"]
        ),
        "url_member_and_archive_hash_exact": bool(
            data["original_receipt"]["archive"]["url"].endswith(
                "10_Portfolios_Prior_12_2_Daily_CSV.zip"
            )
            and data["original_receipt"]["archive"]["member"] == EXPECTED_MEMBER
            and data["original_receipt"]["archive"]["sha256"] == DATA_ARCHIVE_SHA256
        ),
        "repaired_marker_and_ten_columns_exact": bool(
            data["prior_meta"]["marker"] == REPAIRED_MARKER
            and data["prior_meta"]["columns"] == PRIOR_COLUMNS
        ),
        "dates_unique_monotonic_and_values_complete": bool(
            not prior.index.has_duplicates
            and prior.index.is_monotonic_increasing
            and not prior.isna().any().any()
            and np.isfinite(prior.to_numpy(dtype=float)).all()
        ),
        "raw_dates_cover_1926_11_03_through_2026_05_29": bool(
            prior.index[0] <= pd.Timestamp("1926-11-03")
            and prior.index[-1] >= pd.Timestamp("2026-05-29")
        ),
        "recent_french_coverage_at_least_99_5pct": data["recent_french_coverage"] >= 0.995,
        "reused_french_market_rf_hash_matches": True,
        "reused_qqq_spy_archive_and_panel_hashes_match": bool(
            data["product_manifest"]["panel_sha256"] == PRODUCT_PANEL_SHA256
        ),
        "recent_candidate_qqq_spy_common_sessions_at_least_4900": len(data["recent_common"])
        >= 4_900,
    }
    all_gates = {
        **{f"data.{key}": value for key, value in data_gates.items()},
        **{f"early.{key}": value for key, value in early_gates.items()},
        **{f"recent.{key}": value for key, value in recent_gates.items()},
        **{f"mechanism.{key}": value for key, value in mechanism_gates.items()},
    }
    if len(data_gates) != 10 or len(all_gates) != 48:
        raise AssertionError("每日動量環境總門檻不是 48 道")

    passed = int(sum(bool(value) for value in all_gates.values()))
    return {
        "schema_version": "1.0",
        "round": 10,
        "status": "daily_momentum_regime_schema_repair_diagnostic_failed"
        if passed < 48
        else "daily_momentum_regime_schema_repair_diagnostic_passed_mechanism_only",
        "research_role": "schema_informed_engineering_diagnostic",
        "independent_first_seen_evidence": False,
        "original_first_download_status": data["original_receipt"]["status"],
        "original_first_download_passed_gate_count": data["original_receipt"][
            "passed_check_count"
        ],
        "original_first_download_required_gate_count": data["original_receipt"][
            "required_check_count"
        ],
        "protocol": {
            "original_sha256": PROTOCOL_SHA256,
            "mapping_sha256": MAPPING_SHA256,
            "repair_sha256": REPAIR_PROTOCOL_SHA256,
            "global_search_trials": GLOBAL_SEARCH_TRIALS,
            "primary_annual_implementation_drag": PRIMARY_DRAG,
            "primary_overlay_cost_bps": PRIMARY_COST_BPS,
        },
        "data": {
            "archive_path": DATA_ARCHIVE_PATH,
            "archive_sha256": DATA_ARCHIVE_SHA256,
            "prior_meta": data["prior_meta"],
            "recent_xnys_coverage": data["recent_french_coverage"],
            "recent_common_product_sessions": int(len(data["recent_common"])),
        },
        "candidate": {
            "definition": "lagged 20d trend + 60d trend + 60pct breadth + 2-of-4 resonance; 0/50/100pct Hi PRIOR",
            "underlying_is_investable_security": False,
            "signal_display_allowed": False,
            "paper_eligible": False,
            "trade_ready": False,
        },
        "early_confirmation": early,
        "recent_20y": recent,
        "stress_periods_recent": recent_stress,
        "crisis_drawdown_wins_vs_qqq": int(crisis_drawdown_wins),
        "data_gates": data_gates,
        "early_gates": early_gates,
        "recent_gates": recent_gates,
        "mechanism_gates": mechanism_gates,
        "passed_gate_count": passed,
        "required_gate_count": 48,
        "all_gates_pass": passed == 48,
        "paper_eligible": False,
        "trade_ready": False,
        "paper_state_created": False,
        "paper_position_count": 0,
        "real_money_action_usd": 0,
        "point_in_time_stock_ledger_readiness": "1/20",
        "decision": (
            "工程診斷即使全過亦只准保留機制線索；正式逐股賬本未到位，短線 Paper 全現金。"
            if passed == 48
            else "48 道工程／經濟／統計門檻未全過；封存結果，不改參數，短線 Paper 全現金。"
        ),
    }
