from __future__ import annotations

import hashlib
import io
import zipfile
from pathlib import Path
from typing import Any

import pandas as pd

from usfddk.data import panel_fingerprint
from usfddk.managed_futures_capital_efficiency import (
    _halves,
    _month_end_prices,
    _return_frame_from_prices,
    _rolling_comparison,
    _run_monthly_portfolio,
)
from usfddk.metrics import newey_west_mean_test
from usfddk.models import BacktestResult, MarketPanel
from usfddk.validation import deflated_sharpe_ratio, probabilistic_sharpe_ratio

V24_PROTOCOL_SHA256 = "0d35082a8c7d07a247966a85906158e57f0126c195b355f1d79a2f084e8fb147"
V24_PRODUCT_MAPPING_SHA256 = (
    "70e0f6c6336a56e13e339f7e1726d8c080c285eaa779ffa819f89acb335122a9"
)
V24_GLOBAL_SEARCH_TRIALS = 6_131
V24_FRENCH_HASHES = {
    "market": "80b88699a18ac408e2456d25b1004e340f3f7f8d41d5b476a0285bc53c6f0436",
    "quality": "dabda928b154d115cb3f4701e44fa8cb512511e6dce39fe67ff4271bee6ffc10",
    "momentum": "486c246aef32e8656588092fbb5560406258cb2f2d9d22c5db03708fa93028bf",
}
V24_ISHARES_PANEL_SHA256 = (
    "11fc153fc473b8c21ae5e9b141da403f8c377473f583efafcba74fd346f2bee4"
)
V24_ISHARES_ARCHIVE_SHA256 = (
    "5f5408f14c8ea83533bac923b1bba585e3d689866f572c8e69dd6d0d8030c488"
)
V24_INVESCO_PANEL_SHA256 = (
    "39817fb775916705b17795da92b1fc8436f2abc191e71f35f943c49ec2962007"
)
V24_INVESCO_ARCHIVE_SHA256 = (
    "b3487ca3726b0e115e84cd017e149e920f1c674e8079bf8da6d5d70f28a307d9"
)
V24_ACADEMIC_FORMAL_START = "2006-05"
V24_ACADEMIC_FORMAL_END = "2026-04"
V24_ACADEMIC_OLDER_START = "1964-07"
V24_ACADEMIC_OLDER_END = "2006-04"
V24_ISHARES_START = "2013-07-31"
V24_INVESCO_START = "2007-03-30"
V24_PRODUCT_END = "2026-07-31"
V24_ACADEMIC_ANNUAL_DRAG = 0.0015


def _sha256(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _read_french_monthly_table(
    path: str | Path,
    *,
    marker: str | None = None,
) -> pd.DataFrame:
    with zipfile.ZipFile(path) as archive:
        members = archive.namelist()
        if len(members) != 1:
            raise ValueError(f"French ZIP 成員不是一個：{members}")
        text = archive.read(members[0]).decode("utf-8", errors="strict")
    lines = text.splitlines()
    if marker is None:
        header_position = next(
            index for index, line in enumerate(lines) if line.lstrip().startswith(",Mkt-RF")
        )
    else:
        marker_position = next(index for index, line in enumerate(lines) if marker in line)
        header_position = marker_position + 1
    rows: list[str] = []
    for line in lines[header_position + 1 :]:
        first = line.split(",", 1)[0].strip()
        if len(first) == 6 and first.isdigit():
            rows.append(line)
        elif rows:
            break
    if not rows:
        raise ValueError(f"French 月表沒有資料列：{path}")
    frame = pd.read_csv(io.StringIO("\n".join([lines[header_position], *rows])))
    first_column = frame.columns[0]
    periods = pd.PeriodIndex(frame[first_column].astype(str), freq="M")
    frame = frame.drop(columns=[first_column])
    frame.columns = [str(column).strip() for column in frame.columns]
    frame.index = periods
    frame = frame.apply(pd.to_numeric, errors="raise")
    if frame.index.has_duplicates or not frame.index.is_monotonic_increasing:
        raise ValueError(f"French 月表日期不唯一或未排序：{path}")
    if bool(frame.isin([-99.99, -999.0]).any(axis=None)):
        raise ValueError(f"French 月表含缺值碼：{path}")
    return frame.astype(float) / 100.0


def _load_academic_returns(
    market_path: str | Path,
    quality_path: str | Path,
    momentum_path: str | Path,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    market = _read_french_monthly_table(market_path)
    quality = _read_french_monthly_table(
        quality_path, marker="Average Value Weighted Returns -- Monthly"
    )
    momentum = _read_french_monthly_table(
        momentum_path, marker="Average Value Weighted Returns -- Monthly"
    )
    if "Mkt-RF" not in market or "RF" not in market:
        raise ValueError("French 市場月表缺 Mkt-RF／RF")
    if "BIG HiOP" not in quality or "BIG HiPRIOR" not in momentum:
        raise ValueError("French 品質／動量月表缺凍結欄位")
    common = market.index.intersection(quality.index).intersection(momentum.index)
    if common.empty:
        raise ValueError("French 三份月表沒有共同月份")
    monthly_drag = (1.0 - V24_ACADEMIC_ANNUAL_DRAG) ** (1.0 / 12.0)
    returns = pd.DataFrame(
        {
            "MARKET": (
                market.loc[common, "Mkt-RF"] + market.loc[common, "RF"]
            ).to_numpy(),
            "QUALITY": (
                (1.0 + quality.loc[common, "BIG HiOP"]) * monthly_drag - 1.0
            ).to_numpy(),
            "MOMENTUM": (
                (1.0 + momentum.loc[common, "BIG HiPRIOR"]) * monthly_drag - 1.0
            ).to_numpy(),
        },
        index=common.to_timestamp("M"),
    )
    expected = pd.period_range(common[0], common[-1], freq="M")
    if not common.equals(expected):
        raise ValueError("French 三份月表共同月份不連續")
    formal = returns.loc["2006-05-01":"2026-04-30"]
    older = returns.loc["1964-07-01":"2006-04-30"]
    integrity = {
        "common_start": str(common[0]),
        "common_end": str(common[-1]),
        "common_months": int(len(common)),
        "formal_start": formal.index[0].strftime("%Y-%m"),
        "formal_end": formal.index[-1].strftime("%Y-%m"),
        "formal_months": int(len(formal)),
        "older_start": older.index[0].strftime("%Y-%m"),
        "older_end": older.index[-1].strftime("%Y-%m"),
        "older_months": int(len(older)),
        "columns": {
            "market": "Mkt-RF + RF",
            "quality": "BIG HiOP",
            "momentum": "BIG HiPRIOR",
        },
        "annual_product_drag": V24_ACADEMIC_ANNUAL_DRAG,
    }
    if len(formal) != 240:
        raise ValueError(f"v24 正式學術月份 {len(formal)} != 240")
    return returns, integrity


def _comparison_v24(
    strategy: BacktestResult, benchmark: BacktestResult
) -> dict[str, Any]:
    aligned = pd.concat(
        [strategy.returns.rename("strategy"), benchmark.returns.rename("benchmark")],
        axis=1,
    ).dropna()
    active = (aligned["strategy"] - aligned["benchmark"]).iloc[1:]
    return {
        "cagr_difference": strategy.metrics["cagr"] - benchmark.metrics["cagr"],
        "sharpe_difference": strategy.metrics["sharpe"] - benchmark.metrics["sharpe"],
        "drawdown_improvement": (
            strategy.metrics["max_drawdown"] - benchmark.metrics["max_drawdown"]
        ),
        "calmar_difference": strategy.metrics["calmar"] - benchmark.metrics["calmar"],
        "active_return_newey_west": newey_west_mean_test(
            active, max_lag=6, periods_per_year=12
        ),
        "active_probabilistic_sharpe": probabilistic_sharpe_ratio(
            active, benchmark_sharpe=0.0, periods_per_year=12
        ),
        "active_global_deflated_sharpe": deflated_sharpe_ratio(
            active, trials=V24_GLOBAL_SEARCH_TRIALS, periods_per_year=12
        ),
    }


def _evaluate_period(
    returns: pd.DataFrame,
    *,
    quality: str,
    momentum: str,
    market: str,
    start_equity_date: str,
    primary_cost_bps: float,
    stress_cost_bps: float,
) -> tuple[dict[str, Any], dict[str, BacktestResult]]:
    candidate = _run_monthly_portfolio(
        returns,
        {quality: 0.5, momentum: 0.5},
        name=f"50% {quality} / 50% {momentum}",
        start_equity_date=start_equity_date,
        cost_bps=primary_cost_bps,
        rebalance_monthly=True,
    )
    candidate_stress = _run_monthly_portfolio(
        returns,
        {quality: 0.5, momentum: 0.5},
        name="factor blend stress",
        start_equity_date=start_equity_date,
        cost_bps=stress_cost_bps,
        rebalance_monthly=True,
    )
    benchmark = _run_monthly_portfolio(
        returns,
        {market: 1.0},
        name=market,
        start_equity_date=start_equity_date,
        cost_bps=primary_cost_bps,
        rebalance_monthly=False,
    )
    benchmark_stress = _run_monthly_portfolio(
        returns,
        {market: 1.0},
        name=f"{market} stress",
        start_equity_date=start_equity_date,
        cost_bps=stress_cost_bps,
        rebalance_monthly=False,
    )
    quality_only = _run_monthly_portfolio(
        returns,
        {quality: 1.0},
        name=quality,
        start_equity_date=start_equity_date,
        cost_bps=primary_cost_bps,
        rebalance_monthly=False,
    )
    momentum_only = _run_monthly_portfolio(
        returns,
        {momentum: 1.0},
        name=momentum,
        start_equity_date=start_equity_date,
        cost_bps=primary_cost_bps,
        rebalance_monthly=False,
    )
    drift = _run_monthly_portfolio(
        returns,
        {quality: 0.5, momentum: 0.5},
        name="50/50 start then drift",
        start_equity_date=start_equity_date,
        cost_bps=primary_cost_bps,
        rebalance_monthly=False,
    )
    results = {
        "candidate": candidate,
        "candidate_stress": candidate_stress,
        "market": benchmark,
        "market_stress": benchmark_stress,
        "quality": quality_only,
        "momentum": momentum_only,
        "drift": drift,
    }
    data = {
        "period": {
            "start_equity_date": start_equity_date,
            "first_return_month_end": returns.index[0].strftime("%Y-%m-%d"),
            "end": returns.index[-1].strftime("%Y-%m-%d"),
            "months": int(len(returns)),
        },
        "strategy_metrics": candidate.metrics,
        "benchmark_metrics": {
            market: benchmark.metrics,
            quality: quality_only.metrics,
            momentum: momentum_only.metrics,
            "start_then_drift_50_50": drift.metrics,
        },
        "comparisons": {
            market: _comparison_v24(candidate, benchmark),
            quality: _comparison_v24(candidate, quality_only),
            momentum: _comparison_v24(candidate, momentum_only),
            "start_then_drift_50_50": _comparison_v24(candidate, drift),
        },
        "cost_50bps": {
            "strategy_metrics": candidate_stress.metrics,
            "market_metrics": benchmark_stress.metrics,
            "cagr_difference": (
                candidate_stress.metrics["cagr"] - benchmark_stress.metrics["cagr"]
            ),
        },
        "fixed_halves_vs_market": _halves(candidate, benchmark),
        "rolling_five_year_vs_market": _rolling_comparison(candidate, benchmark),
        "turnover_definition": "sum absolute target-minus-drift weights; initial 100pct",
    }
    return data, results


def _receipt_integrity(
    ishares_panel: MarketPanel,
    invesco_panel: MarketPanel,
    *,
    ishares_manifest: dict[str, Any],
    invesco_manifest: dict[str, Any],
    protocol_receipt: dict[str, Any],
    data_receipt: dict[str, Any],
    protocol_sha256: str,
    product_mapping_sha256: str,
    french_paths: dict[str, str | Path],
) -> dict[str, bool]:
    if protocol_sha256 != V24_PROTOCOL_SHA256:
        raise ValueError("v24 協議雜湊不符")
    if product_mapping_sha256 != V24_PRODUCT_MAPPING_SHA256:
        raise ValueError("v24 產品映射雜湊不符")
    if protocol_receipt.get("protocol_sha256") != V24_PROTOCOL_SHA256:
        raise ValueError("v24 協議收據不符")
    if (
        protocol_receipt.get("status")
        != "frozen_before_first_v24_academic_or_product_download_or_portfolio_calculation"
    ):
        raise ValueError("v24 收據未證明先凍結")
    if data_receipt.get("pre_registration_order_proved") is not True:
        raise ValueError("v24 資料收據未證明先凍結")
    for key, expected_hash in V24_FRENCH_HASHES.items():
        if _sha256(french_paths[key]) != expected_hash:
            raise ValueError(f"v24 French {key} 雜湊不符")
    for panel, manifest, panel_hash, archive_hash in (
        (
            ishares_panel,
            ishares_manifest,
            V24_ISHARES_PANEL_SHA256,
            V24_ISHARES_ARCHIVE_SHA256,
        ),
        (
            invesco_panel,
            invesco_manifest,
            V24_INVESCO_PANEL_SHA256,
            V24_INVESCO_ARCHIVE_SHA256,
        ),
    ):
        if panel_fingerprint(panel) != panel_hash or manifest.get("panel_sha256") != panel_hash:
            raise ValueError("v24 產品面板雜湊不符")
        if manifest.get("archive_sha256") != archive_hash:
            raise ValueError("v24 產品快照 ZIP 雜湊不符")
        if (manifest.get("contract") or {}).get("ok") is not True:
            raise ValueError("v24 產品資料契約未通過")
    frozen = max(
        int(protocol_receipt["protocol_mtime_epoch"]),
        int(protocol_receipt["product_mapping_mtime_epoch"]),
    )
    later_mtimes = [
        int(item["mtime_epoch"])
        for item in data_receipt["academic_sources"].values()
    ] + [
        int(data_receipt["ishares_snapshot"]["snapshot_mtime_epoch"]),
        int(data_receipt["invesco_snapshot"]["snapshot_mtime_epoch"]),
    ]
    if any(mtime <= frozen for mtime in later_mtimes):
        raise ValueError("v24 有資料不是在凍結後取得")
    return {
        "frozen_protocol_and_mapping_hashes_pass": True,
        "protocol_and_mapping_precede_all_first_downloads": True,
        "three_french_archives_hash_and_single_member_pass": True,
        "ishares_snapshot_hash_and_contract_pass": True,
        "invesco_snapshot_hash_and_contract_pass": True,
    }


def evaluate_quality_momentum_factor(
    ishares_panel: MarketPanel,
    invesco_panel: MarketPanel,
    *,
    ishares_manifest: dict[str, Any],
    invesco_manifest: dict[str, Any],
    protocol_receipt: dict[str, Any],
    data_receipt: dict[str, Any],
    protocol_sha256: str,
    product_mapping_sha256: str,
    french_paths: dict[str, str | Path],
    primary_cost_bps: float = 10.0,
    stress_cost_bps: float = 50.0,
) -> dict[str, Any]:
    data_gates = _receipt_integrity(
        ishares_panel,
        invesco_panel,
        ishares_manifest=ishares_manifest,
        invesco_manifest=invesco_manifest,
        protocol_receipt=protocol_receipt,
        data_receipt=data_receipt,
        protocol_sha256=protocol_sha256,
        product_mapping_sha256=product_mapping_sha256,
        french_paths=french_paths,
    )
    academic_returns, academic_integrity = _load_academic_returns(
        french_paths["market"], french_paths["quality"], french_paths["momentum"]
    )
    formal_returns = academic_returns.loc["2006-05-01":"2026-04-30"]
    older_returns = academic_returns.loc["1964-07-01":"2006-04-30"]
    formal, _ = _evaluate_period(
        formal_returns,
        quality="QUALITY",
        momentum="MOMENTUM",
        market="MARKET",
        start_equity_date="2006-04-30",
        primary_cost_bps=primary_cost_bps,
        stress_cost_bps=stress_cost_bps,
    )
    older, _ = _evaluate_period(
        older_returns,
        quality="QUALITY",
        momentum="MOMENTUM",
        market="MARKET",
        start_equity_date="1964-06-30",
        primary_cost_bps=primary_cost_bps,
        stress_cost_bps=stress_cost_bps,
    )
    formal_strategy = formal["strategy_metrics"]
    formal_market = formal["benchmark_metrics"]["MARKET"]
    formal_rolling = formal["rolling_five_year_vs_market"]["summary"]
    formal_halves = formal["fixed_halves_vs_market"]
    older_strategy = older["strategy_metrics"]
    older_market = older["benchmark_metrics"]["MARKET"]
    long_gates = {
        "cagr_beats_market_25bp": bool(formal_strategy["cagr"] >= formal_market["cagr"] + 0.0025),
        "sharpe_beats_market": bool(formal_strategy["sharpe"] > formal_market["sharpe"]),
        "drawdown_not_worse_than_market": bool(
            formal_strategy["max_drawdown"] >= formal_market["max_drawdown"]
        ),
        "calmar_beats_market": bool(formal_strategy["calmar"] > formal_market["calmar"]),
        "50bps_cagr_beats_market_10bp": bool(
            formal["cost_50bps"]["cagr_difference"] >= 0.001
        ),
        "both_fixed_decades_cagr_beat_market_10bp": bool(
            all(item["cagr_difference"] >= 0.001 for item in formal_halves.values())
        ),
        "rolling_5y_wins_60pct_and_median_10bp": bool(
            formal_rolling["cagr_win_fraction"] >= 0.60
            and formal_rolling["median_cagr_difference"] >= 0.001
        ),
        "older_cagr_beats_market": bool(older_strategy["cagr"] > older_market["cagr"]),
        "older_sharpe_and_drawdown_not_worse": bool(
            older_strategy["sharpe"] >= older_market["sharpe"]
            and older_strategy["max_drawdown"] >= older_market["max_drawdown"]
        ),
        "monthly_rebalance_not_below_drift_10bp": bool(
            formal_strategy["cagr"]
            >= formal["benchmark_metrics"]["start_then_drift_50_50"]["cagr"] - 0.001
        ),
    }

    ishares_prices = _month_end_prices(
        ishares_panel,
        ["SPY", "QUAL", "MTUM"],
        start=V24_ISHARES_START,
        end=V24_PRODUCT_END,
    )
    ishares_returns = _return_frame_from_prices(ishares_prices)
    ishares, _ = _evaluate_period(
        ishares_returns,
        quality="QUAL",
        momentum="MTUM",
        market="SPY",
        start_equity_date=V24_ISHARES_START,
        primary_cost_bps=primary_cost_bps,
        stress_cost_bps=stress_cost_bps,
    )
    ishares_strategy = ishares["strategy_metrics"]
    ishares_spy = ishares["benchmark_metrics"]["SPY"]
    ishares_halves = ishares["fixed_halves_vs_market"]
    ishares_rolling = ishares["rolling_five_year_vs_market"]["summary"]
    sleeve_cagrs = [
        ishares["benchmark_metrics"][ticker]["cagr"] for ticker in ("QUAL", "MTUM")
    ]
    sleeve_sharpes = [
        ishares["benchmark_metrics"][ticker]["sharpe"] for ticker in ("QUAL", "MTUM")
    ]
    ishares_gates = {
        "actual_months_ohlc_and_unique_dates_pass": True,
        "cagr_beats_SPY_25bp": bool(ishares_strategy["cagr"] >= ishares_spy["cagr"] + 0.0025),
        "sharpe_beats_SPY": bool(ishares_strategy["sharpe"] > ishares_spy["sharpe"]),
        "drawdown_not_worse_than_SPY": bool(
            ishares_strategy["max_drawdown"] >= ishares_spy["max_drawdown"]
        ),
        "calmar_beats_SPY": bool(ishares_strategy["calmar"] > ishares_spy["calmar"]),
        "50bps_cagr_beats_SPY_10bp": bool(ishares["cost_50bps"]["cagr_difference"] >= 0.001),
        "both_fixed_halves_cagr_beat_SPY_10bp": bool(
            all(item["cagr_difference"] >= 0.001 for item in ishares_halves.values())
        ),
        "rolling_5y_wins_60pct_and_median_10bp": bool(
            ishares_rolling["cagr_win_fraction"] >= 0.60
            and ishares_rolling["median_cagr_difference"] >= 0.001
        ),
        "blend_beats_lower_sleeve_cagr_and_sharpe": bool(
            ishares_strategy["cagr"] > min(sleeve_cagrs)
            and ishares_strategy["sharpe"] > min(sleeve_sharpes)
        ),
        "monthly_rebalance_not_below_drift_10bp": bool(
            ishares_strategy["cagr"]
            >= ishares["benchmark_metrics"]["start_then_drift_50_50"]["cagr"] - 0.001
        ),
    }

    invesco_prices = _month_end_prices(
        invesco_panel,
        ["SPY", "SPHQ", "PDP"],
        start=V24_INVESCO_START,
        end=V24_PRODUCT_END,
    )
    invesco_returns = _return_frame_from_prices(invesco_prices)
    invesco, _ = _evaluate_period(
        invesco_returns,
        quality="SPHQ",
        momentum="PDP",
        market="SPY",
        start_equity_date=V24_INVESCO_START,
        primary_cost_bps=primary_cost_bps,
        stress_cost_bps=stress_cost_bps,
    )
    invesco_strategy = invesco["strategy_metrics"]
    invesco_spy = invesco["benchmark_metrics"]["SPY"]
    invesco_halves = invesco["fixed_halves_vs_market"]
    invesco_rolling = invesco["rolling_five_year_vs_market"]["summary"]
    invesco_gates = {
        "cagr_beats_SPY_10bp": bool(invesco_strategy["cagr"] >= invesco_spy["cagr"] + 0.001),
        "sharpe_beats_SPY": bool(invesco_strategy["sharpe"] > invesco_spy["sharpe"]),
        "drawdown_not_worse_than_SPY": bool(
            invesco_strategy["max_drawdown"] >= invesco_spy["max_drawdown"]
        ),
        "calmar_beats_SPY": bool(invesco_strategy["calmar"] > invesco_spy["calmar"]),
        "50bps_cagr_not_below_SPY": bool(invesco["cost_50bps"]["cagr_difference"] >= 0.0),
        "both_halves_cagr_not_below_SPY": bool(
            all(item["cagr_difference"] >= 0.0 for item in invesco_halves.values())
        ),
        "rolling_5y_wins_60pct_and_positive_median": bool(
            invesco_rolling["cagr_win_fraction"] >= 0.60
            and invesco_rolling["median_cagr_difference"] > 0.0
        ),
    }
    data_gates.update(
        {
            "academic_formal_240_and_older_months_contiguous": bool(
                academic_integrity["formal_months"] == 240
                and academic_integrity["older_months"] > 480
            ),
            "ishares_exact_month_end_range_pass": bool(ishares["period"]["months"] == 156),
            "invesco_exact_month_end_range_pass": bool(invesco["period"]["months"] == 232),
        }
    )
    long_passed = sum(long_gates.values())
    ishares_passed = sum(ishares_gates.values())
    invesco_passed = sum(invesco_gates.values())
    data_passed = sum(data_gates.values())
    paper_eligible = bool(
        long_passed == len(long_gates)
        and ishares_passed == len(ishares_gates)
        and invesco_passed >= 5
        and data_passed == len(data_gates)
    )
    return {
        "schema_version": 1,
        "status": (
            "quality_momentum_factor_passed_for_isolated_paper"
            if paper_eligible
            else "quality_momentum_factor_validation_failed"
        ),
        "paper_eligible": paper_eligible,
        "trade_ready": False,
        "reference_trade_candidate": paper_eligible,
        "global_search_trials": V24_GLOBAL_SEARCH_TRIALS,
        "protocol": {
            "sha256": V24_PROTOCOL_SHA256,
            "product_mapping_sha256": V24_PRODUCT_MAPPING_SHA256,
        },
        "candidate": {
            "physical_weights": {"QUAL": 0.5, "MTUM": 0.5},
            "rebalance": "monthly",
            "timing_or_exit_overlay": False,
            "signal_display_allowed": paper_eligible,
        },
        "academic_integrity": academic_integrity,
        "academic_formal_20y": {**formal, "economic_gates": long_gates},
        "academic_older_diagnostic": older,
        "ishares_actual": {**ishares, "entry_gates": ishares_gates},
        "invesco_cross_manager": {**invesco, "entry_gates": invesco_gates},
        "data_gates": data_gates,
        "long_passed_gate_count": long_passed,
        "long_required_gate_count": len(long_gates),
        "ishares_passed_gate_count": ishares_passed,
        "ishares_required_gate_count": len(ishares_gates),
        "invesco_passed_gate_count": invesco_passed,
        "invesco_required_gate_count": len(invesco_gates),
        "invesco_required_pass_count": 5,
        "data_passed_gate_count": data_passed,
        "data_required_gate_count": len(data_gates),
        "paper_entry_passed_gate_count": (
            long_passed + ishares_passed + min(invesco_passed, 5) + data_passed
        ),
        "paper_entry_required_gate_count": (
            len(long_gates) + len(ishares_gates) + 5 + len(data_gates)
        ),
        "paper_state_created": False,
        "statistical_confirmation": {
            "academic_formal_vs_market": formal["comparisons"]["MARKET"],
            "ishares_actual_vs_SPY": ishares["comparisons"]["SPY"],
            "invesco_cross_manager_vs_SPY": invesco["comparisons"]["SPY"],
        },
        "evidence_boundary": {
            "classification": "seen_product_summary_performance_but_post_freeze_academic_and_daily_joint_paths_not_fully_blind",
            "academic_proxy_is_not_investable_or_exact_MSCI_mapping": True,
            "ishares_underlying_momentum_index_is_spliced_and_methodology_changed": True,
            "invesco_pair_is_directional_cross_manager_not_interchangeable": True,
            "joint_paths_computed_after_freeze": True,
        },
    }
