from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import pandas as pd

from usfddk.always_invested import (
    V8_PROTOCOL_SHA256,
    evaluate_always_invested_research,
)
from usfddk.capital_efficient import (
    V17_PROTOCOL_SHA256,
    evaluate_capital_efficient_research,
)
from usfddk.confirmed_relative_growth import (
    V13_PROTOCOL_SHA256,
    evaluate_confirmed_relative_growth_research,
)
from usfddk.data import (
    default_snapshot_path,
    fetch_yfinance,
    load_snapshot,
    most_recent_us_session,
    panel_fingerprint,
    save_snapshot,
    validate_panel,
)
from usfddk.diversifier_strength import (
    V20_PROTOCOL_SHA256,
    evaluate_diversifier_strength_research,
)
from usfddk.engine import run_backtest
from usfddk.equal_diversifier import (
    V18_PROTOCOL_SHA256,
    evaluate_equal_diversifier_research,
)
from usfddk.growth_gold_diversification import (
    V25_PRODUCT_MAPPING_SHA256,
    V25_PROTOCOL_SHA256,
    evaluate_growth_gold_diversification,
    v25_forward_paper_evidence,
)
from usfddk.hierarchical_defense import (
    V10_DATA_CONTRACT_SHA256,
    V10_PROTOCOL_SHA256,
    V12_PROTOCOL_SHA256,
    evaluate_v12_hierarchical_research,
    fetch_and_freeze_v10_dji,
)
from usfddk.hybrid_leverage_core import (
    V21_PRODUCT_MAPPING_SHA256,
    V21_PROTOCOL_SHA256,
    evaluate_hybrid_leverage_core_research,
)
from usfddk.industry import (
    V6_PROTOCOL_SHA256,
    evaluate_industry_tilt_research,
    load_french_industry_proxy,
)
from usfddk.low_turnover import (
    V9_DATA_CONTRACT_SHA256,
    V9_PROTOCOL_SHA256,
    evaluate_low_turnover_research,
    fetch_and_freeze_v9_external,
)
from usfddk.managed_futures_capital_efficiency import (
    V23_PRODUCT_MAPPING_SHA256,
    V23_PROTOCOL_SHA256,
    evaluate_managed_futures_capital_efficiency,
)
from usfddk.modest_leverage import (
    V14_PROTOCOL_SHA256,
    evaluate_modest_leverage_research,
)
from usfddk.modest_leverage_overlay import (
    V15_PROTOCOL_SHA256,
    evaluate_modest_leverage_overlay_research,
)
from usfddk.paper import (
    PASSIVE_BENCHMARK_KEY,
    build_paper_report,
    load_paper_state,
    paper_metrics,
    update_paper_state,
    write_paper_state,
)
from usfddk.quality_momentum_factor import (
    V24_PRODUCT_MAPPING_SHA256,
    V24_PROTOCOL_SHA256,
    evaluate_quality_momentum_factor,
)
from usfddk.reference import (
    append_reference_receipt_files,
    audit_live_reference_files,
    build_live_refresh_status,
    write_live_refresh_status,
)
from usfddk.relative_growth import (
    V7_PROTOCOL_SHA256,
    evaluate_relative_growth_research,
)
from usfddk.report import (
    build_always_invested_report,
    build_capital_efficient_report,
    build_confirmed_relative_growth_report,
    build_cross_market_report,
    build_diversifier_strength_report,
    build_equal_diversifier_report,
    build_growth_gold_diversification_report,
    build_hierarchical_defense_report,
    build_hybrid_leverage_core_report,
    build_industry_tilt_report,
    build_low_turnover_report,
    build_managed_futures_capital_efficiency_report,
    build_modest_leverage_overlay_report,
    build_modest_leverage_report,
    build_quality_momentum_factor_report,
    build_relative_growth_report,
    build_report,
    build_sector_capital_efficiency_report,
    build_style_rotation_report,
    build_three_clock_report,
    build_trend_volatility_brake_report,
    write_signals_json,
)
from usfddk.research import (
    CANDIDATE_NAME,
    GROWTH_GUARD_NAME,
    PASSIVE_90_10_NAME,
    PASSIVE_90_10_WEIGHTS,
    TREND_CONFIRMED_GUARD_NAME,
    V3_CROSS_MARKETS,
    V4_STYLE_PROTOCOL_SHA256,
    V5_THREE_CLOCK_PROTOCOL_SHA256,
    VOLATILITY_GUARD_NAME,
    evaluate_candidate_research,
    evaluate_growth_guard_research,
    evaluate_style_rotation_research,
    evaluate_three_clock_ensemble_research,
    evaluate_trend_confirmed_guard_research,
    evaluate_v3_cross_market_research,
    evaluate_volatility_guard_research,
)
from usfddk.sector_capital_efficiency import (
    V22_DESIGN_SOURCE_SHA256,
    V22_PRODUCT_MAPPING_SHA256,
    V22_PROTOCOL_SHA256,
    evaluate_sector_capital_efficiency_research,
)
from usfddk.site_export import refresh_v25_site_data, write_site_data
from usfddk.strategies import (
    balanced_trend_satellite_targets,
    buy_and_hold_targets,
    confirmed_relative_growth_targets,
    diversifier_relative_strength_targets,
    dual_momentum_targets,
    equal_weight_targets,
    fixed_weight_targets,
    growth_guard_targets,
    hierarchical_relative_growth_targets,
    hybrid_leverage_core_targets,
    low_turnover_relative_growth_targets,
    modest_leverage_overlay_targets,
    modest_leverage_trend_targets,
    momentum_tilt_targets,
    stock_screen,
    trend_confirmed_volatility_guard_targets,
    trend_volatility_brake_targets,
    volatility_guard_targets,
)
from usfddk.trend_volatility_brake import (
    V16_PROTOCOL_SHA256,
    evaluate_trend_volatility_brake_research,
)
from usfddk.universe import (
    DEFENSIVE_ASSET,
    ETF_TREND_UNIVERSE,
    all_default_tickers,
    load_stock_watchlist,
)
from usfddk.v11_official_data import (
    V11_DATA_CONTRACT_SHA256,
    V11_PROTOCOL_SHA256,
    fetch_and_freeze_v11_official_djia,
)
from usfddk.v25_live import (
    append_v25_reference_receipt,
    audit_v25_live_reference_files,
    finalize_v25_refresh_status,
    run_v25_live_update,
    write_json_atomic,
)
from usfddk.validation import (
    block_bootstrap_cagr,
    compare_to_benchmark,
    rolling_metrics,
    stress_period_metrics,
    subperiod_metrics,
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _resolve_backtest_start(panel, explicit: str | None, years: int) -> str:
    if explicit:
        return pd.Timestamp(explicit).strftime("%Y-%m-%d")
    if years <= 0:
        raise ValueError("回測年數必須大於零")
    target = panel.end - pd.DateOffset(years=years)
    spy = panel.close["SPY"].dropna()
    if len(spy) == 0 or spy.index[0] > target:
        raise ValueError(
            f"快照不足 {years} 年：需要涵蓋 {target.date()}，實際從 "
            f"{spy.index[0].date() if len(spy) else '—'} 開始"
        )
    return target.strftime("%Y-%m-%d")


PAPER_BENCHMARK_NAMES = {
    "spy": "SPY 買進持有（LIVE 基準）",
    "qqq": "QQQ 買進持有（LIVE 基準）",
}


def _paper_strategy(
    close: pd.DataFrame, key: str, *, signal_on: str | None = None
) -> tuple[str, pd.DataFrame]:
    if key == "volatility":
        return VOLATILITY_GUARD_NAME, volatility_guard_targets(close)
    if key == "v3":
        return TREND_CONFIRMED_GUARD_NAME, trend_confirmed_volatility_guard_targets(close)
    if key == "growth":
        return GROWTH_GUARD_NAME, growth_guard_targets(close)
    if key == "candidate":
        return CANDIDATE_NAME, balanced_trend_satellite_targets(close)
    if key == "dual":
        return "ETF 雙動量", dual_momentum_targets(close)
    if key == "passive90":
        return PASSIVE_90_10_NAME + "（LIVE 基準）", fixed_weight_targets(
            close, PASSIVE_90_10_WEIGHTS, signal_on=signal_on
        )
    if key == "v9":
        return "v9 低換手相對成長傾斜（隔離 Paper）", (low_turnover_relative_growth_targets(close))
    if key == "v12":
        return "v12 階層式成長／核心／防守三態（隔離 Paper）", (
            hierarchical_relative_growth_targets(close)
        )
    if key == "v13":
        return "v13 兩月確認相對成長三態（隔離 Paper）", (confirmed_relative_growth_targets(close))
    if key == "v14":
        return "v14 小幅槓桿兩月確認趨勢（隔離 Paper）", (modest_leverage_trend_targets(close))
    if key == "v15":
        return "v15 小幅槓桿疊加兩月確認趨勢（隔離 Paper）", (
            modest_leverage_overlay_targets(close)
        )
    if key == "v16":
        return "v16 週度趨勢與波動煞車（隔離 Paper）", (trend_volatility_brake_targets(close))
    if key == "v17":
        return "v17 60% SSO／40% IEF 資本效率組合（隔離 Paper）", (
            fixed_weight_targets(
                close,
                {"SSO": 0.60, "IEF": 0.40},
                signal_on=signal_on,
            )
        )
    if key == "v18":
        return "v18 50% SSO／25% IEF／25% GLD（隔離 Paper）", (
            fixed_weight_targets(
                close,
                {"SSO": 0.50, "IEF": 0.25, "GLD": 0.25},
                signal_on=signal_on,
            )
        )
    if key == "v20":
        return "v20 50% SSO＋分散器相對強弱（隔離 Paper）", (
            diversifier_relative_strength_targets(
                close,
                equity="SSO",
                equity_weight=0.50,
                selected_count=2,
                selected_weight=0.25,
                signal_on=signal_on,
            )
        )
    if key == "v21":
        return "v21 常駐核心＋受控槓桿（隔離 Paper）", (
            hybrid_leverage_core_targets(
                close,
                core="SPY",
                leveraged="SSO",
                defensive="SHY",
                daily_target_multiplier=2,
            )
        )
    if key == "v22":
        return "v22 50% SSO／25% IEF／25% GLD（隔離候選 Paper）", (
            fixed_weight_targets(
                close,
                {"SSO": 0.50, "IEF": 0.25, "GLD": 0.25},
                signal_on=signal_on,
            )
        )
    if key == "v23":
        return "v23 50% SSO／50% KMLM（隔離候選 Paper）", (
            fixed_weight_targets(
                close,
                {"SSO": 0.50, "KMLM": 0.50},
                signal_on=signal_on,
            )
        )
    if key == "v24":
        return "v24 50% QUAL／50% MTUM（隔離候選 Paper）", (
            fixed_weight_targets(
                close,
                {"QUAL": 0.50, "MTUM": 0.50},
                signal_on=signal_on,
            )
        )
    if key == "v25":
        return "v25 80% VUG／20% GLD（隔離候選 Paper）", (
            fixed_weight_targets(
                close,
                {"VUG": 0.80, "GLD": 0.20},
                signal_on=signal_on,
            )
        )
    if key == "v25_matched":
        return "v25 公平基準 80% VUG／20% SHY（隔離 Paper）", (
            fixed_weight_targets(
                close,
                {"VUG": 0.80, "SHY": 0.20},
                signal_on=signal_on,
            )
        )
    if key == "v25_spy":
        return "v25 SPY 基準（隔離 Paper）", buy_and_hold_targets(
            close,
            "SPY",
            signal_on=signal_on or close.index[-1].strftime("%Y-%m-%d"),
        )
    if key in PAPER_BENCHMARK_NAMES:
        ticker = key.upper()
        return PAPER_BENCHMARK_NAMES[key], buy_and_hold_targets(
            close,
            ticker,
            signal_on=signal_on or close.index[-1].strftime("%Y-%m-%d"),
        )
    raise ValueError(f"不支援的 paper 策略：{key}")


def _build(args: argparse.Namespace) -> int:
    output = Path(args.output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    as_of = pd.Timestamp(args.end) if args.end else pd.Timestamp.now(tz="UTC")

    if args.snapshot:
        snapshot_path = Path(args.snapshot).resolve()
        panel, manifest = load_snapshot(snapshot_path)
        manifest["archive_sha256"] = _sha256(snapshot_path)
        print(f"使用凍結快照：{snapshot_path}")
    else:
        print(f"下載 {len(all_default_tickers())} 個行情序列…")
        panel = fetch_yfinance(all_default_tickers(), args.fetch_start, args.end)
        pre_contract = validate_panel(
            panel,
            as_of=as_of,
            required=("SPY", DEFENSIVE_ASSET, "^VIX"),
            min_history_coverage=0.70,
            require_fresh=not bool(args.end),
        )
        pre_contract.require()
        session = most_recent_us_session(as_of) if not args.end else panel.end
        snapshot_path = default_snapshot_path(output, session, panel_fingerprint(panel))
        manifest = save_snapshot(panel, snapshot_path, contract=pre_contract)
        print(f"凍結快照：{snapshot_path.name}")

    contract = validate_panel(
        panel,
        as_of=as_of,
        required=("SPY", DEFENSIVE_ASSET, "^VIX"),
        min_history_coverage=0.70,
        require_fresh=not bool(args.end or args.snapshot),
    )
    contract.require()

    start = _resolve_backtest_start(panel, args.backtest_start, args.years)
    stock_records = load_stock_watchlist()
    stock_symbols = [record.symbol for record in stock_records]

    spy = run_backtest(
        panel,
        buy_and_hold_targets(panel.close, "SPY", signal_on=start),
        name="SPY 買進持有",
        cost_bps=args.cost_bps,
        start=start,
    )
    qqq = run_backtest(
        panel,
        buy_and_hold_targets(panel.close, "QQQ", signal_on=start),
        name="QQQ 買進持有",
        cost_bps=args.cost_bps,
        start=start,
    )
    passive_90_10 = run_backtest(
        panel,
        fixed_weight_targets(panel.close, PASSIVE_90_10_WEIGHTS),
        name=PASSIVE_90_10_NAME,
        cost_bps=args.cost_bps,
        start=start,
    )
    etf_equal = run_backtest(
        panel,
        equal_weight_targets(panel.close, ETF_TREND_UNIVERSE),
        name="ETF 等權",
        cost_bps=args.cost_bps,
        start=start,
    )
    dual = run_backtest(
        panel,
        dual_momentum_targets(panel.close),
        name="ETF 雙動量",
        cost_bps=args.cost_bps,
        start=start,
    )
    candidate, candidate_target, candidate_audit = evaluate_candidate_research(
        panel,
        start=start,
        cost_bps=args.cost_bps,
    )
    growth, growth_target, growth_audit = evaluate_growth_guard_research(
        panel,
        start=start,
        cost_bps=args.cost_bps,
    )
    volatility, volatility_target, volatility_audit = evaluate_volatility_guard_research(
        panel,
        start=start,
        cost_bps=args.cost_bps,
    )
    proxy_panel = None
    proxy_manifest: dict[str, object] | None = None
    proxy_path = Path(args.proxy_snapshot).resolve() if args.proxy_snapshot else None
    if proxy_path is not None and proxy_path.exists():
        proxy_panel, proxy_manifest = load_snapshot(proxy_path)
        proxy_contract = validate_panel(
            proxy_panel,
            required=("^NDX",),
            min_history_coverage=1.0,
            require_fresh=False,
        )
        proxy_contract.require()
        proxy_manifest["archive_sha256"] = _sha256(proxy_path)
    trend_v3, trend_v3_target, trend_v3_audit = evaluate_trend_confirmed_guard_research(
        panel,
        start=start,
        cost_bps=args.cost_bps,
        proxy_panel=proxy_panel,
    )
    if proxy_manifest is not None:
        trend_v3_audit["proxy_validation"]["snapshot"] = {
            "path": str(proxy_path),
            "archive_sha256": proxy_manifest["archive_sha256"],
            "panel_sha256": proxy_manifest.get("panel_sha256"),
        }
    stock_equal = run_backtest(
        panel,
        equal_weight_targets(panel.close, stock_symbols),
        name="大型股等權（當期池）",
        cost_bps=args.cost_bps,
        start=start,
    )
    stock_tilt = run_backtest(
        panel,
        momentum_tilt_targets(panel.close, stock_symbols),
        name="大型股動量傾斜（當期池）",
        cost_bps=args.cost_bps,
        start=start,
    )
    screen = stock_screen(panel.close, panel.volume, stock_records)

    midpoint = pd.Timestamp(start) + pd.DateOffset(years=10)
    headline = [
        trend_v3,
        volatility,
        passive_90_10,
        growth,
        spy,
        qqq,
        etf_equal,
        dual,
        candidate,
    ]
    validations: dict[str, object] = {
        "research_window": {
            "requested_years": int(args.years),
            "start": start,
            "end": panel.end.strftime("%Y-%m-%d"),
            "sessions": int(len(dual.equity)),
        },
        "comparisons": {
            f"{VOLATILITY_GUARD_NAME} vs SPY": compare_to_benchmark(volatility, spy),
            f"{VOLATILITY_GUARD_NAME} vs QQQ": compare_to_benchmark(volatility, qqq),
            f"{VOLATILITY_GUARD_NAME} vs {PASSIVE_90_10_NAME}": compare_to_benchmark(
                volatility, passive_90_10
            ),
            f"{VOLATILITY_GUARD_NAME} vs v1": compare_to_benchmark(volatility, growth),
            f"{GROWTH_GUARD_NAME} vs SPY": compare_to_benchmark(growth, spy),
            f"{GROWTH_GUARD_NAME} vs QQQ": compare_to_benchmark(growth, qqq),
            f"{CANDIDATE_NAME} vs SPY": compare_to_benchmark(candidate, spy),
            f"{CANDIDATE_NAME} vs ETF 等權": compare_to_benchmark(candidate, etf_equal),
            "ETF 雙動量 vs SPY": compare_to_benchmark(dual, spy),
            "ETF 雙動量 vs ETF 等權": compare_to_benchmark(dual, etf_equal),
            "大型股動量傾斜 vs 當期池等權（偏誤診斷）": compare_to_benchmark(
                stock_tilt, stock_equal
            ),
        },
        "bootstrap": {
            result.name: block_bootstrap_cagr(
                result.returns,
                samples=args.bootstrap_samples,
                seed=args.seed + idx,
            )
            for idx, result in enumerate(headline)
        },
        "subperiods": {
            result.name: subperiod_metrics(
                result,
                [
                    (
                        "前十年",
                        start,
                        (midpoint - pd.Timedelta(days=1)).strftime("%Y-%m-%d"),
                    ),
                    ("後十年", midpoint.strftime("%Y-%m-%d"), "2099-12-31"),
                ],
            )
            for result in headline
        },
        "stress_periods": stress_period_metrics(
            headline,
            [
                ("全球金融危機｜2007-10-09–2009-03-09", "2007-10-09", "2009-03-09"),
                ("COVID 急跌｜2020-02-19–2020-03-23", "2020-02-19", "2020-03-23"),
                ("2022 熊市｜2022-01-03–2022-10-12", "2022-01-03", "2022-10-12"),
            ],
        ),
        "rolling_3y": {result.name: rolling_metrics(result) for result in headline},
        "research_candidate": candidate_audit,
        "growth_guard": growth_audit,
        "volatility_guard": volatility_audit,
        "trend_confirmed_guard_v3": trend_v3_audit,
    }

    sensitivity: list[dict[str, float | int]] = []
    configs = [(lookback, top_k, 10.0) for lookback in (189, 252, 315) for top_k in (2, 3, 4)]
    configs.extend([(252, 4, 5.0), (252, 4, 25.0)])
    for lookback, top_k, cost in configs:
        target = dual_momentum_targets(
            panel.close,
            long_lookback=lookback,
            top_k=top_k,
        )
        result = run_backtest(
            panel,
            target,
            name=f"sensitivity-{lookback}-{top_k}-{cost:g}",
            cost_bps=cost,
            start=start,
        )
        sensitivity.append(
            {
                "lookback": lookback,
                "top_k": top_k,
                "cost_bps": cost,
                "cagr": result.metrics["cagr"],
                "sharpe": result.metrics["sharpe"],
                "max_drawdown": result.metrics["max_drawdown"],
            }
        )
    validations["sensitivity"] = sensitivity

    report_path = build_report(
        output / "report.html",
        panel=panel,
        contract=contract,
        manifest=manifest,
        headline_results=headline,
        stock_results=[stock_equal, stock_tilt],
        stock_screen=screen,
        validations=validations,
    )
    signals_path = write_signals_json(
        output / "signals.json",
        panel=panel,
        results=[trend_v3, volatility, growth, candidate, dual, stock_tilt],
        stock_screen=screen,
        snapshot_sha256=str(manifest.get("archive_sha256", "")),
    )
    (output / "validation.json").write_text(
        json.dumps(validations, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    paper_state_path = output / "paper_state.json"
    existing_state = load_paper_state(paper_state_path) if paper_state_path.exists() else None
    paper_state = update_paper_state(
        panel,
        dual_momentum_targets(panel.close),
        state=existing_state,
        initial_cash=args.paper_cash,
        cost_bps=args.cost_bps,
        snapshot_sha256=str(manifest.get("archive_sha256", "")),
    )
    write_paper_state(paper_state_path, paper_state)
    paper_report_path = build_paper_report(output / "paper.html", state=paper_state, panel=panel)
    candidate_state_path = output / "paper_candidate_state.json"
    existing_candidate_state = (
        load_paper_state(candidate_state_path) if candidate_state_path.exists() else None
    )
    candidate_state = update_paper_state(
        panel,
        candidate_target,
        state=existing_candidate_state,
        initial_cash=args.paper_cash,
        cost_bps=args.cost_bps,
        snapshot_sha256=str(manifest.get("archive_sha256", "")),
        strategy_name=CANDIDATE_NAME,
    )
    write_paper_state(candidate_state_path, candidate_state)
    candidate_paper_path = build_paper_report(
        output / "paper_candidate.html", state=candidate_state, panel=panel
    )
    growth_state_path = output / "paper_growth_state.json"
    existing_growth_state = (
        load_paper_state(growth_state_path) if growth_state_path.exists() else None
    )
    growth_state = update_paper_state(
        panel,
        growth_target,
        state=existing_growth_state,
        initial_cash=args.paper_cash,
        cost_bps=args.cost_bps,
        snapshot_sha256=str(manifest.get("archive_sha256", "")),
        strategy_name=GROWTH_GUARD_NAME,
    )
    write_paper_state(growth_state_path, growth_state)
    growth_paper_path = build_paper_report(
        output / "paper_growth.html", state=growth_state, panel=panel
    )
    volatility_state_path = output / "paper_volatility_state.json"
    existing_volatility_state = (
        load_paper_state(volatility_state_path) if volatility_state_path.exists() else None
    )
    volatility_state = update_paper_state(
        panel,
        volatility_target,
        state=existing_volatility_state,
        initial_cash=args.paper_cash,
        cost_bps=args.cost_bps,
        snapshot_sha256=str(manifest.get("archive_sha256", "")),
        strategy_name=VOLATILITY_GUARD_NAME,
    )
    write_paper_state(volatility_state_path, volatility_state)
    volatility_paper_path = build_paper_report(
        output / "paper_volatility.html", state=volatility_state, panel=panel
    )
    trend_v3_state_path = output / "paper_v3_state.json"
    existing_trend_v3_state = (
        load_paper_state(trend_v3_state_path) if trend_v3_state_path.exists() else None
    )
    trend_v3_state = update_paper_state(
        panel,
        trend_v3_target,
        state=existing_trend_v3_state,
        initial_cash=args.paper_cash,
        cost_bps=args.cost_bps,
        snapshot_sha256=str(manifest.get("archive_sha256", "")),
        strategy_name=TREND_CONFIRMED_GUARD_NAME,
    )
    write_paper_state(trend_v3_state_path, trend_v3_state)
    trend_v3_paper_path = build_paper_report(
        output / "paper_v3.html", state=trend_v3_state, panel=panel
    )
    benchmark_states: dict[str, dict] = {}
    benchmark_reports: dict[str, Path] = {}
    for key, ticker in (
        ("spy", "SPY"),
        ("qqq", "QQQ"),
        ("passive90", PASSIVE_BENCHMARK_KEY),
    ):
        benchmark_state_path = output / f"paper_{key}_state.json"
        existing_benchmark_state = (
            load_paper_state(benchmark_state_path) if benchmark_state_path.exists() else None
        )
        signal_on = (
            str(existing_benchmark_state["started_at"])
            if existing_benchmark_state is not None
            else panel.end.strftime("%Y-%m-%d")
        )
        benchmark_name, benchmark_target = _paper_strategy(panel.close, key, signal_on=signal_on)
        benchmark_state = update_paper_state(
            panel,
            benchmark_target,
            state=existing_benchmark_state,
            initial_cash=args.paper_cash,
            cost_bps=args.cost_bps,
            snapshot_sha256=str(manifest.get("archive_sha256", "")),
            strategy_name=benchmark_name,
        )
        write_paper_state(benchmark_state_path, benchmark_state)
        benchmark_states[ticker] = benchmark_state
        benchmark_reports[ticker] = build_paper_report(
            output / f"paper_{key}.html", state=benchmark_state, panel=panel
        )
    cross_market_path = Path(args.cross_market_validation)
    cross_market_audit = (
        json.loads(cross_market_path.read_text(encoding="utf-8"))
        if cross_market_path.exists()
        else None
    )
    style_rotation_path = Path(args.style_rotation_validation)
    style_rotation_audit = (
        json.loads(style_rotation_path.read_text(encoding="utf-8"))
        if style_rotation_path.exists()
        else None
    )
    three_clock_path = Path(args.three_clock_validation)
    three_clock_audit = (
        json.loads(three_clock_path.read_text(encoding="utf-8"))
        if three_clock_path.exists()
        else None
    )
    industry_tilt_path = Path(args.industry_tilt_validation)
    industry_tilt_audit = (
        json.loads(industry_tilt_path.read_text(encoding="utf-8"))
        if industry_tilt_path.exists()
        else None
    )
    relative_growth_path = Path(args.relative_growth_validation)
    relative_growth_audit = (
        json.loads(relative_growth_path.read_text(encoding="utf-8"))
        if relative_growth_path.exists()
        else None
    )
    always_invested_path = Path(args.always_invested_validation)
    always_invested_audit = (
        json.loads(always_invested_path.read_text(encoding="utf-8"))
        if always_invested_path.exists()
        else None
    )
    low_turnover_path = Path(args.low_turnover_validation)
    low_turnover_audit = (
        json.loads(low_turnover_path.read_text(encoding="utf-8"))
        if low_turnover_path.exists()
        else None
    )
    hierarchical_defense_path = Path(args.hierarchical_defense_validation)
    hierarchical_defense_audit = (
        json.loads(hierarchical_defense_path.read_text(encoding="utf-8"))
        if hierarchical_defense_path.exists()
        else None
    )
    confirmed_relative_growth_path = Path(args.confirmed_relative_growth_validation)
    confirmed_relative_growth_audit = (
        json.loads(confirmed_relative_growth_path.read_text(encoding="utf-8"))
        if confirmed_relative_growth_path.exists()
        else None
    )
    modest_leverage_path = Path(args.modest_leverage_validation)
    modest_leverage_audit = (
        json.loads(modest_leverage_path.read_text(encoding="utf-8"))
        if modest_leverage_path.exists()
        else None
    )
    modest_leverage_overlay_path = Path(args.modest_leverage_overlay_validation)
    modest_leverage_overlay_audit = (
        json.loads(modest_leverage_overlay_path.read_text(encoding="utf-8"))
        if modest_leverage_overlay_path.exists()
        else None
    )
    trend_volatility_brake_path = Path(args.trend_volatility_brake_validation)
    trend_volatility_brake_audit = (
        json.loads(trend_volatility_brake_path.read_text(encoding="utf-8"))
        if trend_volatility_brake_path.exists()
        else None
    )
    capital_efficient_path = Path(args.capital_efficient_validation)
    capital_efficient_audit = (
        json.loads(capital_efficient_path.read_text(encoding="utf-8"))
        if capital_efficient_path.exists()
        else None
    )
    equal_diversifier_path = Path(args.equal_diversifier_validation)
    equal_diversifier_audit = (
        json.loads(equal_diversifier_path.read_text(encoding="utf-8"))
        if equal_diversifier_path.exists()
        else None
    )
    diversifier_strength_path = Path(args.diversifier_strength_validation)
    diversifier_strength_audit = (
        json.loads(diversifier_strength_path.read_text(encoding="utf-8"))
        if diversifier_strength_path.exists()
        else None
    )
    hybrid_leverage_core_path = Path(args.hybrid_leverage_core_validation)
    hybrid_leverage_core_audit = (
        json.loads(hybrid_leverage_core_path.read_text(encoding="utf-8"))
        if hybrid_leverage_core_path.exists()
        else None
    )
    sector_capital_efficiency_path = Path(args.sector_capital_efficiency_validation)
    sector_capital_efficiency_audit = (
        json.loads(sector_capital_efficiency_path.read_text(encoding="utf-8"))
        if sector_capital_efficiency_path.exists()
        else None
    )
    managed_futures_capital_efficiency_path = Path(
        args.managed_futures_capital_efficiency_validation
    )
    managed_futures_capital_efficiency_audit = (
        json.loads(managed_futures_capital_efficiency_path.read_text(encoding="utf-8"))
        if managed_futures_capital_efficiency_path.exists()
        else None
    )
    quality_momentum_factor_path = Path(args.quality_momentum_factor_validation)
    quality_momentum_factor_audit = (
        json.loads(quality_momentum_factor_path.read_text(encoding="utf-8"))
        if quality_momentum_factor_path.exists()
        else None
    )
    growth_gold_diversification_path = Path(args.growth_gold_diversification_validation)
    growth_gold_diversification_audit = (
        json.loads(growth_gold_diversification_path.read_text(encoding="utf-8"))
        if growth_gold_diversification_path.exists()
        else None
    )

    def optional_paper_state(raw_path: str) -> dict[str, Any] | None:
        path = Path(raw_path)
        return load_paper_state(path) if path.exists() else None

    growth_gold_paper_state = optional_paper_state(args.growth_gold_paper_state)
    growth_gold_spy_paper_state = optional_paper_state(args.growth_gold_spy_paper_state)
    growth_gold_matched_paper_state = optional_paper_state(args.growth_gold_matched_paper_state)
    site_paths = write_site_data(
        [output / "site_data.json", Path("site/data/trading-data.json")],
        panel=panel,
        manifest=manifest,
        start=start,
        reference_audit=volatility_audit,
        challenger_audit=trend_v3_audit,
        challenger_paper_state=trend_v3_state,
        paper_state=volatility_state,
        paper_benchmark_states=benchmark_states,
        cross_market_audit=cross_market_audit,
        style_rotation_audit=style_rotation_audit,
        three_clock_audit=three_clock_audit,
        industry_tilt_audit=industry_tilt_audit,
        relative_growth_audit=relative_growth_audit,
        always_invested_audit=always_invested_audit,
        low_turnover_audit=low_turnover_audit,
        hierarchical_defense_audit=hierarchical_defense_audit,
        confirmed_relative_growth_audit=confirmed_relative_growth_audit,
        modest_leverage_audit=modest_leverage_audit,
        modest_leverage_overlay_audit=modest_leverage_overlay_audit,
        trend_volatility_brake_audit=trend_volatility_brake_audit,
        capital_efficient_audit=capital_efficient_audit,
        equal_diversifier_audit=equal_diversifier_audit,
        diversifier_strength_audit=diversifier_strength_audit,
        hybrid_leverage_core_audit=hybrid_leverage_core_audit,
        sector_capital_efficiency_audit=sector_capital_efficiency_audit,
        managed_futures_capital_efficiency_audit=(managed_futures_capital_efficiency_audit),
        quality_momentum_factor_audit=quality_momentum_factor_audit,
        growth_gold_diversification_audit=growth_gold_diversification_audit,
        growth_gold_paper_state=growth_gold_paper_state,
        growth_gold_spy_paper_state=growth_gold_spy_paper_state,
        growth_gold_matched_paper_state=growth_gold_matched_paper_state,
    )
    print(f"報表：{report_path}")
    print(f"成長守門員 v2 LIVE Paper trade：{volatility_paper_path}")
    print(f"成長守門員 v3 研究 Paper trade：{trend_v3_paper_path}")
    print(f"成長守門員 LIVE Paper trade：{growth_paper_path}")
    print(f"候選策略 Paper trade：{candidate_paper_path}")
    print(f"雙動量 Paper trade：{paper_report_path}")
    print(f"SPY LIVE 基準：{benchmark_reports['SPY']}")
    print(f"QQQ LIVE 基準：{benchmark_reports['QQQ']}")
    print(f"被動 90/10 LIVE 基準：{benchmark_reports[PASSIVE_BENCHMARK_KEY]}")
    print(f"訊號：{signals_path}")
    print(f"網站資料：{site_paths[0]}")
    print(
        f"{TREND_CONFIRMED_GUARD_NAME} CAGR {trend_v3.metrics['cagr']:.1%} / "
        f"QQQ 超額 {trend_v3_audit['cagr_difference_vs_qqq']:.1%} / "
        f"Sharpe {trend_v3.metrics['sharpe']:.2f} / "
        f"MDD {trend_v3.metrics['max_drawdown']:.1%} / "
        f"代理期 {'通過' if trend_v3_audit['proxy_validation_passed'] else '未通過'} / "
        f"研究門檻 {'通過' if trend_v3_audit['historical_gate_passed'] else '未通過'} / "
        f"可升級 {'是' if trend_v3_audit['reference_trade_candidate'] else '否'}"
    )
    print(
        f"{VOLATILITY_GUARD_NAME} CAGR {volatility.metrics['cagr']:.1%} / "
        f"SPY 超額 {volatility_audit['cagr_difference_vs_spy']:.1%} / "
        f"Sharpe {volatility.metrics['sharpe']:.2f} / "
        f"MDD {volatility.metrics['max_drawdown']:.1%} / "
        f"NW t {volatility_audit['active_return_newey_west']['t_stat']:.2f} / "
        f"歷史門檻 {'通過' if volatility_audit['historical_gate_passed'] else '未通過'} / "
        f"曝險控制 {'通過' if volatility_audit['exposure_control_passed'] else '未通過'} / "
        f"統計確認 {'通過' if volatility_audit['statistically_confirmed'] else '未通過'}"
    )
    print(
        f"{GROWTH_GUARD_NAME} CAGR {growth.metrics['cagr']:.1%} / "
        f"SPY 超額 {growth_audit['cagr_difference_vs_spy']:.1%} / "
        f"Sharpe {growth.metrics['sharpe']:.2f} / "
        f"MDD {growth.metrics['max_drawdown']:.1%} / "
        f"NW t {growth_audit['active_return_newey_west']['t_stat']:.2f} / "
        f"歷史門檻 {'通過' if growth_audit['historical_gate_passed'] else '未通過'} / "
        f"統計確認 {'通過' if growth_audit['statistically_confirmed'] else '未通過'}"
    )
    print(
        f"ETF 雙動量 CAGR {dual.metrics['cagr']:.1%} / Sharpe {dual.metrics['sharpe']:.2f} / "
        f"MDD {dual.metrics['max_drawdown']:.1%}"
    )
    print(
        f"{CANDIDATE_NAME} CAGR {candidate.metrics['cagr']:.1%} / "
        f"零利率 Sharpe {candidate.metrics['sharpe']:.2f} / "
        f"SHY 超額 Sharpe "
        f"{candidate_audit['excess_return_metrics']['excess_sharpe_vs_shy']:.2f} / "
        f"MDD {candidate.metrics['max_drawdown']:.1%} / "
        f"超額 DSR {candidate_audit['deflated_sharpe']['probability']:.1%}"
    )
    return 0


def _verify(args: argparse.Namespace) -> int:
    path = Path(args.snapshot).resolve()
    panel, manifest = load_snapshot(path)
    contract = validate_panel(
        panel,
        required=("SPY", DEFENSIVE_ASSET, "^VIX"),
        min_history_coverage=0.70,
        require_fresh=False,
    )
    print(
        json.dumps(
            {
                "archive_sha256": _sha256(path),
                "manifest": manifest,
                "contract": {
                    "ok": contract.ok,
                    "errors": contract.errors,
                    "warnings": contract.warnings,
                    "stats": contract.stats,
                },
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if contract.ok else 2


def _paper_update(args: argparse.Namespace) -> int:
    snapshot = Path(args.snapshot).resolve()
    panel, _ = load_snapshot(snapshot)
    required = (
        ("SPY", "SSO", DEFENSIVE_ASSET)
        if args.strategy == "v14"
        else ("SPY", "UPRO")
        if args.strategy == "v15"
        else ("IJH", "MVV", "SHY")
        if args.strategy == "v16"
        else ("SPY", "SSO", "IEF")
        if args.strategy == "v17"
        else ("SPY", "SSO", "IEF", "GLD")
        if args.strategy in {"v18", "v20", "v22"}
        else ("SPY", "SSO", "KMLM")
        if args.strategy == "v23"
        else ("SPY", "QUAL", "MTUM")
        if args.strategy == "v24"
        else ("SPY", "VUG", "GLD")
        if args.strategy == "v25"
        else ("SPY", "VUG", "SHY")
        if args.strategy == "v25_matched"
        else ("SPY",)
        if args.strategy == "v25_spy"
        else ("SPY", "SSO", "SHY")
        if args.strategy == "v21"
        else ("SPY", DEFENSIVE_ASSET, "^VIX")
    )
    contract = validate_panel(
        panel,
        required=required,
        min_history_coverage=0.70,
        require_fresh=False,
    )
    contract.require()
    if args.strategy in {
        "v9",
        "v12",
        "v13",
        "v14",
        "v15",
        "v16",
        "v17",
        "v18",
        "v20",
        "v21",
        "v22",
        "v23",
        "v24",
        "v25",
    }:
        eligibility_contracts = {
            "v9": ("artifacts/v9_low_turnover_validation.json", V9_PROTOCOL_SHA256),
            "v12": ("artifacts/v12_hierarchical_validation.json", V12_PROTOCOL_SHA256),
            "v13": (
                "artifacts/v13_confirmed_growth_validation.json",
                V13_PROTOCOL_SHA256,
            ),
            "v14": (
                "artifacts/v14_modest_leverage_validation.json",
                V14_PROTOCOL_SHA256,
            ),
            "v15": (
                "artifacts/v15_modest_leverage_overlay_validation.json",
                V15_PROTOCOL_SHA256,
            ),
            "v16": (
                "artifacts/v16_trend_volatility_brake_validation.json",
                V16_PROTOCOL_SHA256,
            ),
            "v17": (
                "artifacts/v17_capital_efficient_validation.json",
                V17_PROTOCOL_SHA256,
            ),
            "v18": (
                "artifacts/v18_equal_diversifier_validation.json",
                V18_PROTOCOL_SHA256,
            ),
            "v20": (
                "artifacts/v20_diversifier_strength_validation.json",
                V20_PROTOCOL_SHA256,
            ),
            "v21": (
                "artifacts/v21_hybrid_leverage_core_validation.json",
                V21_PROTOCOL_SHA256,
            ),
            "v22": (
                "artifacts/v22_us_sector_capital_efficiency_validation.json",
                V22_PROTOCOL_SHA256,
            ),
            "v23": (
                "artifacts/v23_managed_futures_capital_efficiency_validation.json",
                V23_PROTOCOL_SHA256,
            ),
            "v24": (
                "artifacts/v24_quality_momentum_factor_validation.json",
                V24_PROTOCOL_SHA256,
            ),
            "v25": (
                "artifacts/v25_growth_gold_diversification_validation.json",
                V25_PROTOCOL_SHA256,
            ),
        }
        default_eligibility, expected_protocol = eligibility_contracts[args.strategy]
        eligibility_path = Path(args.eligibility_receipt or default_eligibility).resolve()
        eligibility = json.loads(eligibility_path.read_text(encoding="utf-8"))
        passed = int(eligibility.get("paper_entry_passed_gate_count", 0))
        required = int(eligibility.get("paper_entry_required_gate_count", 0))
        if eligibility.get("protocol", {}).get("sha256") != expected_protocol:
            raise ValueError(f"{args.strategy} Paper 守門收據的協議雜湊不符")
        if not bool(eligibility.get("paper_eligible")):
            raise ValueError(
                f"{args.strategy} Paper 入口只通過 {passed}/{required}；"
                f"拒絕建立或推進 {args.strategy} Paper 帳戶"
            )
    default_state = {
        "v3": "artifacts/paper_v3_state.json",
        "volatility": "artifacts/paper_volatility_state.json",
        "growth": "artifacts/paper_growth_state.json",
        "candidate": "artifacts/paper_candidate_state.json",
        "dual": "artifacts/paper_state.json",
        "spy": "artifacts/paper_spy_state.json",
        "qqq": "artifacts/paper_qqq_state.json",
        "passive90": "artifacts/paper_passive90_state.json",
        "v9": "artifacts/paper_v9_state.json",
        "v12": "artifacts/paper_v12_state.json",
        "v13": "artifacts/paper_v13_state.json",
        "v14": "artifacts/paper_v14_state.json",
        "v15": "artifacts/paper_v15_state.json",
        "v16": "artifacts/paper_v16_state.json",
        "v17": "artifacts/paper_v17_state.json",
        "v18": "artifacts/paper_v18_state.json",
        "v20": "artifacts/paper_v20_state.json",
        "v21": "artifacts/paper_v21_state.json",
        "v22": "artifacts/paper_v22_state.json",
        "v23": "artifacts/paper_v23_state.json",
        "v24": "artifacts/paper_v24_state.json",
        "v25": "artifacts/paper_v25_state.json",
        "v25_matched": "artifacts/paper_v25_matched_state.json",
        "v25_spy": "artifacts/paper_v25_spy_state.json",
    }[args.strategy]
    state_path = Path(args.state or default_state).resolve()
    existing = load_paper_state(state_path) if state_path.exists() else None
    if existing is not None and args.replay_from:
        raise ValueError("既有帳戶不能改成 replay；請指定新的 state 路徑")
    strategy_name, target_signals = _paper_strategy(
        panel.close,
        args.strategy,
        signal_on=str(existing["started_at"]) if existing is not None else None,
    )
    state = update_paper_state(
        panel,
        target_signals,
        state=existing,
        replay_from=args.replay_from,
        initial_cash=args.initial_cash,
        cost_bps=args.cost_bps,
        snapshot_sha256=_sha256(snapshot),
        strategy_name=strategy_name,
    )
    write_paper_state(state_path, state)
    if args.report:
        report_path = Path(args.report).resolve()
    else:
        filename = {
            "v3": "paper_v3.html",
            "volatility": "paper_volatility.html",
            "growth": "paper_growth.html",
            "candidate": "paper_candidate.html",
            "dual": "paper.html",
            "spy": "paper_spy.html",
            "qqq": "paper_qqq.html",
            "passive90": "paper_passive90.html",
            "v9": "paper_v9.html",
            "v12": "paper_v12.html",
            "v13": "paper_v13.html",
            "v14": "paper_v14.html",
            "v15": "paper_v15.html",
            "v16": "paper_v16.html",
            "v17": "paper_v17.html",
            "v18": "paper_v18.html",
            "v20": "paper_v20.html",
            "v21": "paper_v21.html",
            "v22": "paper_v22.html",
            "v23": "paper_v23.html",
            "v24": "paper_v24.html",
            "v25": "paper_v25.html",
            "v25_matched": "paper_v25_matched.html",
            "v25_spy": "paper_v25_spy.html",
        }[args.strategy]
        report_path = state_path.with_name(filename)
    build_paper_report(report_path, state=state, panel=panel)
    metrics = paper_metrics(state)
    print(
        f"{state['mode'].upper()}｜截至 {state['as_of']}｜權益 ${metrics['equity']:,.2f}｜"
        f"報酬 {metrics['return']:.1%}｜成交 {len(state['transactions'])} 筆"
    )
    print(f"狀態：{state_path}")
    print(f"報表：{report_path}")
    return 0


def _paper_status(args: argparse.Namespace) -> int:
    state = load_paper_state(Path(args.state).resolve())
    metrics = paper_metrics(state)
    payload = {
        "strategy": state.get("strategy"),
        "mode": state["mode"],
        "as_of": state["as_of"],
        "equity": metrics["equity"],
        "pnl": metrics["pnl"],
        "return": metrics["return"],
        "max_drawdown": metrics["max_drawdown"],
        "cash": state["cash"],
        "holdings": state["holdings"],
        "pending_order": state["pending_order"],
        "transactions": len(state["transactions"]),
        "total_costs": state["total_costs"],
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def _v25_paper_bundle(args: argparse.Namespace) -> int:
    """Advance candidate and both preregistered controls from one frozen snapshot."""
    snapshot = Path(args.snapshot).resolve()
    panel, manifest = load_snapshot(snapshot)
    contract = validate_panel(
        panel,
        required=("GLD", "SHY", "SPY", "VUG"),
        min_history_coverage=0.999,
        require_fresh=False,
    )
    contract.require()
    eligibility_path = Path(args.eligibility_receipt).resolve()
    eligibility = json.loads(eligibility_path.read_text(encoding="utf-8"))
    if eligibility.get("protocol", {}).get("sha256") != V25_PROTOCOL_SHA256:
        raise ValueError("v25 Paper bundle 的協議雜湊不符")
    if not bool(eligibility.get("paper_eligible")):
        raise ValueError("v25 歷史產品入口未通過，拒絕推進 Paper bundle")
    archive_sha256 = _sha256(snapshot)
    configurations = {
        "candidate": ("v25", Path(args.candidate_state).resolve()),
        "SPY": ("v25_spy", Path(args.spy_state).resolve()),
        "matched": ("v25_matched", Path(args.matched_state).resolve()),
    }
    staged: dict[str, tuple[dict[str, Any], Path, str]] = {}
    for label, (strategy_key, state_path) in configurations.items():
        existing = load_paper_state(state_path) if state_path.exists() else None
        strategy_name, targets = _paper_strategy(
            panel.close,
            strategy_key,
            signal_on=str(existing["started_at"]) if existing is not None else None,
        )
        state = update_paper_state(
            panel,
            targets,
            state=existing,
            initial_cash=args.initial_cash,
            cost_bps=args.cost_bps,
            snapshot_sha256=archive_sha256,
            strategy_name=strategy_name,
        )
        staged[label] = (state, state_path, strategy_key)
    starts = {str(item[0].get("started_at")) for item in staged.values()}
    as_of_dates = {str(item[0].get("as_of")) for item in staged.values()}
    if len(starts) != 1 or len(as_of_dates) != 1:
        raise RuntimeError("v25 Paper bundle 三帳戶起點或進度不一致，拒絕寫入")
    evidence = v25_forward_paper_evidence(
        staged["candidate"][0],
        staged["SPY"][0],
        staged["matched"][0],
    )
    identity_gates = (
        "all_accounts_live_and_same_start",
        "all_accounts_same_as_of",
        "all_accounts_same_snapshot",
        "all_accounts_same_cost_and_cash",
        "all_accounts_same_session_path",
        "all_accounts_same_execution_clock",
        "all_accounts_same_order_path",
        "all_accounts_same_fill_counts",
        "zero_integrity_violations",
    )
    if not all(evidence["gates"][gate] for gate in identity_gates):
        raise RuntimeError("v25 Paper bundle 同步完整性門檻未通過，拒絕寫入")
    for state, state_path, strategy_key in staged.values():
        write_paper_state(state_path, state)
        build_paper_report(
            state_path.with_name(f"paper_{strategy_key}.html"),
            state=state,
            panel=panel,
        )
    evidence_path = Path(args.evidence).resolve()
    write_json_atomic(evidence_path, evidence)
    print(
        f"v25 PAPER｜截至 {evidence['as_of']}｜新增交易日 "
        f"{evidence['forward_sessions']}/{evidence['minimum_sessions']}｜"
        f"完成再平衡 {evidence['filled_rebalances']}/"
        f"{evidence['minimum_filled_rebalances']}｜"
        f"實金確認 {'是' if evidence['live_confirmed'] else '否'}"
    )
    print(f"前瞻收據：{evidence_path}")
    return 0


def _v25_live_update(args: argparse.Namespace) -> int:
    status = run_v25_live_update(
        snapshot=args.snapshot,
        fetch_start=args.fetch_start,
        end=args.end,
        as_of=args.as_of,
        output_dir=args.output_dir,
        eligibility_receipt=args.eligibility_receipt,
        candidate_state_path=args.candidate_state,
        spy_state_path=args.spy_state,
        matched_state_path=args.matched_state,
        evidence_path=args.evidence,
        status_path=args.status,
        initial_cash=args.initial_cash,
        cost_bps=args.cost_bps,
    )
    print(json.dumps(status, ensure_ascii=False, indent=2))
    print(
        f"v25 LIVE 更新｜{status['data_through']}｜"
        f"新增交易日 {'是' if status['data_advanced'] else '否'}｜"
        f"決策 {status['decision']}"
    )
    return 0


def _v25_site_export(args: argparse.Namespace) -> int:
    candidate_state = load_paper_state(args.candidate_state)
    spy_state = load_paper_state(args.spy_state)
    matched_state = load_paper_state(args.matched_state)
    paths = refresh_v25_site_data(
        [args.site_data, args.artifact_site_data],
        template=args.template,
        candidate_state=candidate_state,
        spy_state=spy_state,
        matched_state=matched_state,
    )
    print("v25 網站資料：" + "、".join(str(path) for path in paths))
    return 0


def _v25_reference_check(args: argparse.Namespace) -> int:
    result = audit_v25_live_reference_files(
        args.site_data,
        args.candidate_state,
        args.spy_state,
        args.matched_state,
    )
    if result["integrity_ok"] and args.receipt_ledger:
        site_payload = json.loads(Path(args.site_data).read_text(encoding="utf-8"))
        candidate_state = load_paper_state(args.candidate_state)
        spy_state = load_paper_state(args.spy_state)
        matched_state = load_paper_state(args.matched_state)
        receipt = append_v25_reference_receipt(
            args.receipt_ledger,
            site_payload=site_payload,
            candidate_state=candidate_state,
            spy_state=spy_state,
            matched_state=matched_state,
            audit=result,
        )
        result["receipt"] = {
            "ledger": str(args.receipt_ledger),
            "sequence": int(receipt["sequence"]),
            "receipt_sha256": receipt["receipt_sha256"],
            "appended": bool(receipt["appended"]),
        }
    write_json_atomic(args.output, result)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if not result["integrity_ok"]:
        return 3 if result["status"] == "stale" else 2
    if args.require_trade_ready and not result["reference_trade_allowed"]:
        return 4
    return 0


def _v25_refresh_status(args: argparse.Namespace) -> int:
    update_status = json.loads(Path(args.update_status).read_text(encoding="utf-8"))
    audit = json.loads(Path(args.audit).read_text(encoding="utf-8"))
    payload = finalize_v25_refresh_status(update_status, audit)
    write_json_atomic(args.output, payload)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload["integrity_ok"] else 2


def _reference_check(args: argparse.Namespace) -> int:
    result = audit_live_reference_files(
        args.site_data,
        args.paper_state,
        args.spy_paper_state,
        args.qqq_paper_state,
        args.passive90_paper_state,
        args.challenger_paper_state,
    )
    if result["integrity_ok"] and args.receipt_ledger:
        receipt = append_reference_receipt_files(
            args.receipt_ledger,
            args.site_data,
            args.paper_state,
            args.spy_paper_state,
            args.qqq_paper_state,
            args.passive90_paper_state,
            args.challenger_paper_state,
            audit=result,
        )
        result["receipt"] = {
            "ledger": str(args.receipt_ledger),
            "sequence": int(receipt["sequence"]),
            "receipt_sha256": receipt["receipt_sha256"],
            "appended": bool(receipt["appended"]),
        }
    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False),
            encoding="utf-8",
        )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if not result["integrity_ok"]:
        return 3 if result["status"] == "stale" else 2
    if args.require_trade_ready and not result["trade_ready"]:
        return 4
    return 0


def _refresh_status(args: argparse.Namespace) -> int:
    audit = json.loads(Path(args.audit).read_text(encoding="utf-8"))
    account_states = {
        "v2": load_paper_state(Path(args.paper_state)),
        "v3": load_paper_state(Path(args.challenger_paper_state)),
        "SPY": load_paper_state(Path(args.spy_paper_state)),
        "QQQ": load_paper_state(Path(args.qqq_paper_state)),
        PASSIVE_BENCHMARK_KEY: load_paper_state(Path(args.passive90_paper_state)),
    }
    payload = build_live_refresh_status(
        previous_data_through=args.previous_data_through or None,
        audit=audit,
        account_states=account_states,
    )
    output = write_live_refresh_status(args.output, payload)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    print(f"更新狀態：{output}")
    return 0


def _cross_market(args: argparse.Namespace) -> int:
    protocol_path = Path(args.protocol)
    protocol_sha256 = _sha256(protocol_path)
    snapshot_paths = {
        "^GSPC": Path(args.gspc_snapshot),
        "^FTSE": Path(args.ftse_snapshot),
        "^GDAXI": Path(args.gdaxi_snapshot),
        "^N225": Path(args.n225_snapshot),
        "^HSI": Path(args.hsi_snapshot),
    }
    panels = {}
    receipts = {}
    for ticker in V3_CROSS_MARKETS:
        path = snapshot_paths[ticker]
        panel, manifest = load_snapshot(path)
        actual_panel_sha256 = panel_fingerprint(panel)
        if actual_panel_sha256 != manifest.get("panel_sha256"):
            raise ValueError(f"{ticker} 面板內容與 manifest 雜湊不同")
        panels[ticker] = panel
        receipts[ticker] = {
            "path": str(path),
            "rows": int(manifest["rows"]),
            "start": str(manifest["start"]),
            "end": str(manifest["end"]),
            "panel_sha256": str(manifest["panel_sha256"]),
            "archive_sha256": _sha256(path),
            "protocol_sha256": str(
                manifest.get("provider_metadata", {}).get("protocol_sha256", "")
            ),
            "created_at": str(manifest.get("created_at", "")),
        }
    audit = evaluate_v3_cross_market_research(
        panels,
        snapshot_receipts=receipts,
        protocol_sha256=protocol_sha256,
    )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(audit, ensure_ascii=False, indent=2, allow_nan=False),
        encoding="utf-8",
    )
    report = build_cross_market_report(args.report, audit)
    counts = audit["counts"]
    pooled_t = audit["pooled_active_return"]["newey_west"]["t_stat"]
    print(f"機器可讀收據：{output}")
    print(f"研究報表：{report}")
    print(
        f"跨市場結論：{'通過' if audit['cross_market_passed'] else '未通過'}；"
        f"完整期勝出 {counts['full_cagr']}/5；"
        f"50 bps 勝出 {counts['cost_50bps']}/5；"
        f"等權 NW t {pooled_t:.2f}"
    )
    return 0


def _style_rotation(args: argparse.Namespace) -> int:
    protocol_path = Path(args.protocol)
    protocol_sha256 = _sha256(protocol_path)
    if protocol_sha256 != V4_STYLE_PROTOCOL_SHA256:
        raise ValueError("v4 協議檔已與下載前凍結雜湊不同")
    snapshot_paths = {
        "trade": Path(args.trade_snapshot),
        "proxy": Path(args.proxy_snapshot),
    }
    panels = {}
    receipts = {}
    for key, path in snapshot_paths.items():
        panel, manifest = load_snapshot(path)
        actual_panel_sha256 = panel_fingerprint(panel)
        if actual_panel_sha256 != manifest.get("panel_sha256"):
            raise ValueError(f"v4 {key} 面板內容與 manifest 雜湊不同")
        panels[key] = panel
        receipts[key] = {
            "path": str(path),
            "rows": int(manifest["rows"]),
            "start": str(manifest["start"]),
            "end": str(manifest["end"]),
            "tickers": list(manifest["tickers"]),
            "panel_sha256": str(manifest["panel_sha256"]),
            "archive_sha256": _sha256(path),
            "protocol_sha256": str(
                manifest.get("provider_metadata", {}).get("protocol_sha256", "")
            ),
            "created_at": str(manifest.get("created_at", "")),
        }
    _, _, audit = evaluate_style_rotation_research(
        panels["trade"],
        panels["proxy"],
        trade_receipt=receipts["trade"],
        proxy_receipt=receipts["proxy"],
        protocol_sha256=protocol_sha256,
    )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(audit, ensure_ascii=False, indent=2, allow_nan=False),
        encoding="utf-8",
    )
    report = build_style_rotation_report(args.report, audit)
    comparison = audit["trade"]["comparisons"]["market"]
    print(f"機器可讀收據：{output}")
    print(f"研究報表：{report}")
    print(
        f"v4 結論：{'通過' if audit['historical_gate_passed'] else '未通過'}；"
        f"硬門檻 {audit['passed_gate_count']}/{audit['required_gate_count']}；"
        f"相對 SPY CAGR {comparison['cagr_difference']:.2%}；"
        f"回撤改善 {comparison['drawdown_improvement']:.2%}；"
        f"舊代理資料門檻 {'通過' if audit['data_gate_passed'] else '失敗'}"
    )
    return 0


def _three_clock(args: argparse.Namespace) -> int:
    protocol_path = Path(args.protocol)
    protocol_sha256 = _sha256(protocol_path)
    if protocol_sha256 != V5_THREE_CLOCK_PROTOCOL_SHA256:
        raise ValueError("v5 協議檔已與第一次集成計算前凍結雜湊不同")

    def load_receipt(raw_path: str) -> tuple[Any, dict[str, Any]]:
        path = Path(raw_path)
        panel, manifest = load_snapshot(path)
        actual_panel_sha256 = panel_fingerprint(panel)
        if actual_panel_sha256 != manifest.get("panel_sha256"):
            raise ValueError(f"{path.name} 面板內容與 manifest 雜湊不同")
        receipt = {
            "path": str(path),
            "rows": int(manifest["rows"]),
            "start": str(manifest["start"]),
            "end": str(manifest["end"]),
            "tickers": list(manifest["tickers"]),
            "panel_sha256": str(manifest["panel_sha256"]),
            "archive_sha256": _sha256(path),
            "created_at": str(manifest.get("created_at", "")),
        }
        return panel, receipt

    main_panel, main_receipt = load_receipt(args.main_snapshot)
    proxy_panel, proxy_receipt = load_receipt(args.proxy_snapshot)
    cross_paths = {
        "^GSPC": args.gspc_snapshot,
        "^FTSE": args.ftse_snapshot,
        "^GDAXI": args.gdaxi_snapshot,
        "^N225": args.n225_snapshot,
        "^HSI": args.hsi_snapshot,
    }
    loaded_cross = {ticker: load_receipt(path) for ticker, path in cross_paths.items()}
    _, _, audit = evaluate_three_clock_ensemble_research(
        main_panel,
        proxy_panel,
        {ticker: value[0] for ticker, value in loaded_cross.items()},
        main_receipt=main_receipt,
        proxy_receipt=proxy_receipt,
        cross_receipts={ticker: value[1] for ticker, value in loaded_cross.items()},
        protocol_sha256=protocol_sha256,
    )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(audit, ensure_ascii=False, indent=2, allow_nan=False),
        encoding="utf-8",
    )
    report = build_three_clock_report(args.report, audit)
    comparison = audit["main"]["comparisons"]["opportunity"]
    counts = audit["cross_market"]["counts"]
    print(f"機器可讀收據：{output}")
    print(f"研究報表：{report}")
    print(
        f"v5 結論：{'通過' if audit['historical_gate_passed'] else '未通過'}；"
        f"硬門檻 {audit['passed_gate_count']}/{audit['required_gate_count']}；"
        f"相對 QQQ CAGR {comparison['cagr_difference']:.3%}；"
        f"回撤改善 {comparison['drawdown_improvement']:.2%}；"
        f"五市場完整期同勝兩基準 {counts['full_cagr_beats_both']}/5"
    )
    return 0


def _industry_tilt(args: argparse.Namespace) -> int:
    protocol_path = Path(args.protocol)
    protocol_sha256 = _sha256(protocol_path)
    if protocol_sha256 != V6_PROTOCOL_SHA256:
        raise ValueError("v6 協議檔已與新資料下載前凍結雜湊不同")

    snapshot = Path(args.etf_snapshot)
    panel, manifest = load_snapshot(snapshot)
    actual_panel_sha256 = panel_fingerprint(panel)
    if actual_panel_sha256 != manifest.get("panel_sha256"):
        raise ValueError("v6 ETF 面板內容與 manifest 雜湊不同")
    etf_receipt = {
        "path": str(snapshot),
        "rows": int(manifest["rows"]),
        "start": str(manifest["start"]),
        "end": str(manifest["end"]),
        "tickers": list(manifest["tickers"]),
        "panel_sha256": actual_panel_sha256,
        "archive_sha256": _sha256(snapshot),
        "created_at": str(manifest.get("created_at", "")),
        "provider_metadata": manifest.get("provider_metadata", {}),
        "contract": manifest.get("contract"),
    }
    industries, factors, french_receipt = load_french_industry_proxy(
        args.industry_zip, args.factors_zip
    )
    data_receipt = {
        "schema_version": 1,
        "protocol": {"path": str(protocol_path), "sha256": protocol_sha256},
        "etf": etf_receipt,
        "french": french_receipt,
    }
    data_receipt_path = Path(args.data_receipt)
    data_receipt_path.parent.mkdir(parents=True, exist_ok=True)
    data_receipt_path.write_text(
        json.dumps(data_receipt, ensure_ascii=False, indent=2, allow_nan=False),
        encoding="utf-8",
    )

    _, _, audit = evaluate_industry_tilt_research(
        panel,
        industries,
        factors,
        etf_receipt=etf_receipt,
        french_receipt=french_receipt,
        protocol_sha256=protocol_sha256,
    )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(audit, ensure_ascii=False, indent=2, allow_nan=False),
        encoding="utf-8",
    )
    report = build_industry_tilt_report(args.report, audit)
    strategy = audit["main"]["strategy_metrics"]
    spy = audit["main"]["benchmark_metrics"]["spy"]
    matched = audit["main"]["benchmark_metrics"]["matched"]
    print(f"資料收據：{data_receipt_path}")
    print(f"機器可讀研究收據：{output}")
    print(f"研究報表：{report}")
    print(
        f"v6 結論：{'通過' if audit['historical_gate_passed'] else '未通過'}；"
        f"硬門檻 {audit['passed_gate_count']}/{audit['required_gate_count']}；"
        f"CAGR 策略 {strategy['cagr']:.2%}／SPY {spy['cagr']:.2%}／"
        f"matched {matched['cagr']:.2%}；"
        f"Paper {'可建立' if audit['paper_eligible'] else '不建立'}"
    )
    return 0


def _relative_growth(args: argparse.Namespace) -> int:
    protocol_path = Path(args.protocol)
    protocol_sha256 = _sha256(protocol_path)
    if protocol_sha256 != V7_PROTOCOL_SHA256:
        raise ValueError("v7 協議檔已與第一次計算前凍結雜湊不同")

    def load_receipt(source: str) -> tuple[Any, dict[str, Any]]:
        path = Path(source)
        panel, manifest = load_snapshot(path)
        actual_panel_sha256 = panel_fingerprint(panel)
        if actual_panel_sha256 != manifest.get("panel_sha256"):
            raise ValueError(f"v7 快照面板內容與 manifest 雜湊不同：{path}")
        return panel, {
            "path": str(path),
            "rows": int(manifest["rows"]),
            "start": str(manifest["start"]),
            "end": str(manifest["end"]),
            "tickers": list(manifest["tickers"]),
            "panel_sha256": actual_panel_sha256,
            "archive_sha256": _sha256(path),
            "created_at": str(manifest.get("created_at", "")),
            "provider_metadata": manifest.get("provider_metadata", {}),
            "contract": manifest.get("contract"),
        }

    main_panel, main_receipt = load_receipt(args.main_snapshot)
    ndx_panel, ndx_receipt = load_receipt(args.ndx_snapshot)
    gspc_panel, gspc_receipt = load_receipt(args.gspc_snapshot)
    data_receipt = {
        "schema_version": 1,
        "protocol": {"path": str(protocol_path), "sha256": protocol_sha256},
        "main": main_receipt,
        "ndx": ndx_receipt,
        "gspc": gspc_receipt,
        "derived_proxy": {
            "common_sessions_only": True,
            "translation": "QQQ->^NDX; SPY->^GSPC; SHY->constant CASH",
        },
    }
    data_receipt_path = Path(args.data_receipt)
    data_receipt_path.parent.mkdir(parents=True, exist_ok=True)
    data_receipt_path.write_text(
        json.dumps(data_receipt, ensure_ascii=False, indent=2, allow_nan=False),
        encoding="utf-8",
    )

    _, _, audit = evaluate_relative_growth_research(
        main_panel,
        ndx_panel,
        gspc_panel,
        main_receipt=main_receipt,
        ndx_receipt=ndx_receipt,
        gspc_receipt=gspc_receipt,
        protocol_sha256=protocol_sha256,
    )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(audit, ensure_ascii=False, indent=2, allow_nan=False),
        encoding="utf-8",
    )
    report = build_relative_growth_report(args.report, audit)
    strategy = audit["main"]["strategy_metrics"]
    market = audit["main"]["benchmark_metrics"]["market"]
    matched = audit["main"]["benchmark_metrics"]["matched"]
    print(f"資料收據：{data_receipt_path}")
    print(f"機器可讀研究收據：{output}")
    print(f"研究報表：{report}")
    print(
        f"v7 結論：{'通過' if audit['historical_gate_passed'] else '未通過'}；"
        f"硬門檻 {audit['passed_gate_count']}/{audit['required_gate_count']}；"
        f"CAGR 策略 {strategy['cagr']:.2%}／SPY {market['cagr']:.2%}／"
        f"matched {matched['cagr']:.2%}；"
        f"Paper {'可建立' if audit['paper_eligible'] else '不建立'}"
    )
    return 0


def _always_invested(args: argparse.Namespace) -> int:
    protocol_path = Path(args.protocol)
    protocol_sha256 = _sha256(protocol_path)
    if protocol_sha256 != V8_PROTOCOL_SHA256:
        raise ValueError("v8 協議檔已與第一次計算前凍結雜湊不同")

    def load_receipt(source: str) -> tuple[Any, dict[str, Any]]:
        path = Path(source)
        panel, manifest = load_snapshot(path)
        actual_panel_sha256 = panel_fingerprint(panel)
        if actual_panel_sha256 != manifest.get("panel_sha256"):
            raise ValueError(f"v8 快照面板內容與 manifest 雜湊不同：{path}")
        return panel, {
            "path": str(path),
            "rows": int(manifest["rows"]),
            "start": str(manifest["start"]),
            "end": str(manifest["end"]),
            "tickers": list(manifest["tickers"]),
            "panel_sha256": actual_panel_sha256,
            "archive_sha256": _sha256(path),
            "created_at": str(manifest.get("created_at", "")),
            "provider_metadata": manifest.get("provider_metadata", {}),
            "contract": manifest.get("contract"),
        }

    main_panel, main_receipt = load_receipt(args.main_snapshot)
    ndx_panel, ndx_receipt = load_receipt(args.ndx_snapshot)
    gspc_panel, gspc_receipt = load_receipt(args.gspc_snapshot)
    data_receipt = {
        "schema_version": 1,
        "protocol": {"path": str(protocol_path), "sha256": protocol_sha256},
        "main": main_receipt,
        "ndx": ndx_receipt,
        "gspc": gspc_receipt,
        "derived_proxy": {
            "common_sessions_only": True,
            "translation": "QQQ->^NDX; SPY->^GSPC",
        },
    }
    data_receipt_path = Path(args.data_receipt)
    data_receipt_path.parent.mkdir(parents=True, exist_ok=True)
    data_receipt_path.write_text(
        json.dumps(data_receipt, ensure_ascii=False, indent=2, allow_nan=False),
        encoding="utf-8",
    )

    _, _, audit = evaluate_always_invested_research(
        main_panel,
        ndx_panel,
        gspc_panel,
        main_receipt=main_receipt,
        ndx_receipt=ndx_receipt,
        gspc_receipt=gspc_receipt,
        protocol_sha256=protocol_sha256,
    )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(audit, ensure_ascii=False, indent=2, allow_nan=False),
        encoding="utf-8",
    )
    report = build_always_invested_report(args.report, audit)
    strategy = audit["main"]["strategy_metrics"]
    spy = audit["main"]["benchmark_metrics"]["market"]
    print(f"資料收據：{data_receipt_path}")
    print(f"機器可讀研究收據：{output}")
    print(f"研究報表：{report}")
    print(
        f"v8 結論：Paper 入口 "
        f"{audit['paper_entry_passed_gate_count']}/{audit['paper_entry_required_gate_count']}；"
        f"全部歷史門檻 {audit['passed_gate_count']}/{audit['required_gate_count']}；"
        f"CAGR 策略 {strategy['cagr']:.2%}／SPY {spy['cagr']:.2%}；"
        f"Paper {'可建立' if audit['paper_eligible'] else '不建立'}"
    )
    return 0


def _v9_fetch_external(args: argparse.Namespace) -> int:
    protocol_path = Path(args.protocol)
    data_contract_path = Path(args.data_contract)
    protocol_sha256 = _sha256(protocol_path)
    data_contract_sha256 = _sha256(data_contract_path)
    if protocol_sha256 != V9_PROTOCOL_SHA256:
        raise ValueError("v9 協議檔已與首次下載前凍結雜湊不同")
    if data_contract_sha256 != V9_DATA_CONTRACT_SHA256:
        raise ValueError("v9 外部資料契約已與首次下載前凍結雜湊不同")

    receipt, all_ok = fetch_and_freeze_v9_external(
        args.output_dir,
        protocol_sha256=protocol_sha256,
        data_contract_sha256=data_contract_sha256,
    )
    receipt_path = Path(args.data_receipt)
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_text(
        json.dumps(receipt, ensure_ascii=False, indent=2, allow_nan=False),
        encoding="utf-8",
    )
    print(f"v9 外部資料收據：{receipt_path}")
    print("v9 外部資料契約：" + ("全部通過" if all_ok else "未通過；第 23 門必須失敗"))
    return 0 if all_ok else 3


def _v9_low_turnover(args: argparse.Namespace) -> int:
    protocol_path = Path(args.protocol)
    data_contract_path = Path(args.data_contract)
    protocol_sha256 = _sha256(protocol_path)
    data_contract_sha256 = _sha256(data_contract_path)
    if protocol_sha256 != V9_PROTOCOL_SHA256:
        raise ValueError("v9 協議檔已與第一次計算前凍結雜湊不同")
    if data_contract_sha256 != V9_DATA_CONTRACT_SHA256:
        raise ValueError("v9 外部資料契約已與首次下載前凍結雜湊不同")

    def load_receipt(source: str) -> tuple[Any, dict[str, Any]]:
        path = Path(source)
        panel, manifest = load_snapshot(path)
        actual_panel_sha256 = panel_fingerprint(panel)
        if actual_panel_sha256 != manifest.get("panel_sha256"):
            raise ValueError(f"v9 快照面板內容與 manifest 雜湊不同：{path}")
        return panel, {
            "path": str(path),
            "rows": int(manifest["rows"]),
            "start": str(manifest["start"]),
            "end": str(manifest["end"]),
            "tickers": list(manifest["tickers"]),
            "panel_sha256": actual_panel_sha256,
            "archive_sha256": _sha256(path),
            "created_at": str(manifest.get("created_at", "")),
            "provider_metadata": manifest.get("provider_metadata", {}),
            "contract": manifest.get("contract"),
        }

    main_panel, main_receipt = load_receipt(args.main_snapshot)
    ndx_panel, ndx_receipt = load_receipt(args.ndx_snapshot)
    old_gspc_panel, old_gspc_receipt = load_receipt(args.old_gspc_snapshot)
    ixic_panel, ixic_receipt = load_receipt(args.ixic_snapshot)
    external_gspc_panel, external_gspc_receipt = load_receipt(args.external_gspc_snapshot)
    external_receipt_path = Path(args.external_data_receipt)
    external_data_receipt = json.loads(external_receipt_path.read_text(encoding="utf-8"))
    external_data_receipt["receipt_file"] = {
        "path": str(external_receipt_path),
        "sha256": _sha256(external_receipt_path),
    }

    _, _, audit = evaluate_low_turnover_research(
        main_panel,
        ndx_panel,
        old_gspc_panel,
        ixic_panel,
        external_gspc_panel,
        main_receipt=main_receipt,
        ndx_receipt=ndx_receipt,
        old_gspc_receipt=old_gspc_receipt,
        ixic_receipt=ixic_receipt,
        external_gspc_receipt=external_gspc_receipt,
        external_data_receipt=external_data_receipt,
        protocol_sha256=protocol_sha256,
        data_contract_sha256=data_contract_sha256,
    )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(audit, ensure_ascii=False, indent=2, allow_nan=False),
        encoding="utf-8",
    )
    report = build_low_turnover_report(args.report, audit)
    strategy = audit["main"]["strategy_metrics"]
    spy = audit["main"]["benchmark_metrics"]["market"]
    print(f"機器可讀研究收據：{output}")
    print(f"研究報表：{report}")
    print(
        f"v9 結論：Paper 入口 "
        f"{audit['paper_entry_passed_gate_count']}/{audit['paper_entry_required_gate_count']}；"
        f"全部歷史門檻 {audit['passed_gate_count']}/{audit['required_gate_count']}；"
        f"CAGR 策略 {strategy['cagr']:.2%}／SPY {spy['cagr']:.2%}；"
        f"Paper {'可建立' if audit['paper_eligible'] else '不建立'}"
    )
    return 0


def _v10_fetch_dji(args: argparse.Namespace) -> int:
    protocol_path = Path(args.protocol)
    data_contract_path = Path(args.data_contract)
    protocol_sha256 = _sha256(protocol_path)
    data_contract_sha256 = _sha256(data_contract_path)
    if protocol_sha256 != V10_PROTOCOL_SHA256:
        raise ValueError("v10 協議檔已與首次下載前凍結雜湊不同")
    if data_contract_sha256 != V10_DATA_CONTRACT_SHA256:
        raise ValueError("v10 DJIA 資料契約已與首次下載前凍結雜湊不同")
    receipt_path = Path(args.data_receipt)
    if receipt_path.exists():
        existing = json.loads(receipt_path.read_text(encoding="utf-8"))
        if existing.get("status") == "fetch_failed":
            raise ValueError(
                "v10 首次 DJIA 下載失敗已封存，拒絕重試或改寫；替代來源必須建立新版本協議"
            )
    receipt, all_ok = fetch_and_freeze_v10_dji(
        args.output_dir,
        ixic_snapshot=args.ixic_snapshot,
        protocol_sha256=protocol_sha256,
        data_contract_sha256=data_contract_sha256,
    )
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_text(
        json.dumps(receipt, ensure_ascii=False, indent=2, allow_nan=False),
        encoding="utf-8",
    )
    print(f"v10 DJIA 資料收據：{receipt_path}")
    print("v10 DJIA 資料契約：" + ("全部通過" if all_ok else "未通過；第 30 門必須失敗"))
    return 0 if all_ok else 3


def _v11_fetch_official_dji(args: argparse.Namespace) -> int:
    protocol_path = Path(args.protocol)
    data_contract_path = Path(args.data_contract)
    protocol_sha256 = _sha256(protocol_path)
    data_contract_sha256 = _sha256(data_contract_path)
    if protocol_sha256 != V11_PROTOCOL_SHA256:
        raise ValueError("v11 協議檔已與首次官方下載前凍結雜湊不同")
    if data_contract_sha256 != V11_DATA_CONTRACT_SHA256:
        raise ValueError("v11 官方 DJIA 資料契約已與首次下載前凍結雜湊不同")
    receipt_path = Path(args.data_receipt)
    if receipt_path.exists():
        raise ValueError("v11 首次官方 DJIA 下載結果已封存，拒絕重試或改寫；失敗時也不得換來源")
    receipt, all_ok = fetch_and_freeze_v11_official_djia(
        args.output_dir,
        ixic_snapshot=args.ixic_snapshot,
        protocol_sha256=protocol_sha256,
        data_contract_sha256=data_contract_sha256,
    )
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_text(
        json.dumps(receipt, ensure_ascii=False, indent=2, allow_nan=False),
        encoding="utf-8",
    )
    print(f"v11 官方 DJIA 資料收據：{receipt_path}")
    print(
        "v11 官方 DJIA 資料契約："
        + ("全部通過，可開始凍結策略計算" if all_ok else "未通過；第 30 門必須失敗")
    )
    return 0 if all_ok else 3


def _v12_hierarchical(args: argparse.Namespace) -> int:
    protocol_path = Path(args.protocol)
    protocol_sha256 = _sha256(protocol_path)
    if protocol_sha256 != V12_PROTOCOL_SHA256:
        raise ValueError("v12 協議檔已與第一次計算前凍結雜湊不同")

    def load_receipt(source: str) -> tuple[Any, dict[str, Any]]:
        path = Path(source)
        panel, manifest = load_snapshot(path)
        actual_panel_sha256 = panel_fingerprint(panel)
        if actual_panel_sha256 != manifest.get("panel_sha256"):
            raise ValueError(f"v12 快照面板內容與 manifest 雜湊不同：{path}")
        return panel, {
            "path": str(path),
            "rows": int(manifest["rows"]),
            "start": str(manifest["start"]),
            "end": str(manifest["end"]),
            "tickers": list(manifest["tickers"]),
            "panel_sha256": actual_panel_sha256,
            "archive_sha256": _sha256(path),
            "created_at": str(manifest.get("created_at", "")),
            "provider_metadata": manifest.get("provider_metadata", {}),
            "contract": manifest.get("contract"),
        }

    main_panel, main_receipt = load_receipt(args.main_snapshot)
    ndx_panel, ndx_receipt = load_receipt(args.ndx_snapshot)
    old_gspc_panel, old_gspc_receipt = load_receipt(args.old_gspc_snapshot)
    ixic_panel, ixic_receipt = load_receipt(args.ixic_snapshot)
    external_gspc_panel, external_gspc_receipt = load_receipt(args.external_gspc_snapshot)

    def load_failure(source: str) -> dict[str, Any]:
        path = Path(source)
        receipt = json.loads(path.read_text(encoding="utf-8"))
        receipt["receipt_file"] = {"path": str(path), "sha256": _sha256(path)}
        return receipt

    v10_failure = load_failure(args.v10_failure_receipt)
    v11_failure = load_failure(args.v11_failure_receipt)
    _, _, audit = evaluate_v12_hierarchical_research(
        main_panel,
        ndx_panel,
        old_gspc_panel,
        ixic_panel,
        external_gspc_panel,
        main_receipt=main_receipt,
        ndx_receipt=ndx_receipt,
        old_gspc_receipt=old_gspc_receipt,
        ixic_receipt=ixic_receipt,
        external_gspc_receipt=external_gspc_receipt,
        v10_failure_receipt=v10_failure,
        v11_failure_receipt=v11_failure,
        protocol_sha256=protocol_sha256,
    )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(audit, ensure_ascii=False, indent=2, allow_nan=False),
        encoding="utf-8",
    )
    report = build_hierarchical_defense_report(args.report, audit)
    strategy = audit["main"]["strategy_metrics"]
    spy = audit["main"]["benchmark_metrics"]["market"]
    print(f"機器可讀研究收據：{output}")
    print(f"研究報表：{report}")
    print(
        f"v12 結論：Paper 入口 "
        f"{audit['paper_entry_passed_gate_count']}/{audit['paper_entry_required_gate_count']}；"
        f"全部歷史門檻 {audit['passed_gate_count']}/{audit['required_gate_count']}；"
        f"CAGR 策略 {strategy['cagr']:.2%}／SPY {spy['cagr']:.2%}；"
        f"Paper {'可建立' if audit['paper_eligible'] else '不建立'}"
    )
    return 0


def _v13_confirmed_relative_growth(args: argparse.Namespace) -> int:
    protocol_path = Path(args.protocol)
    protocol_sha256 = _sha256(protocol_path)
    if protocol_sha256 != V13_PROTOCOL_SHA256:
        raise ValueError("v13 協議檔已與新 ETF 下載前凍結雜湊不同")

    snapshot_path = Path(args.validation_snapshot)
    panel, manifest = load_snapshot(snapshot_path)
    actual_panel_sha256 = panel_fingerprint(panel)
    if actual_panel_sha256 != manifest.get("panel_sha256"):
        raise ValueError("v13 快照面板內容與 manifest 雜湊不同")
    receipt = {
        "path": str(snapshot_path),
        "rows": int(manifest["rows"]),
        "start": str(manifest["start"]),
        "end": str(manifest["end"]),
        "tickers": list(manifest["tickers"]),
        "panel_sha256": actual_panel_sha256,
        "archive_sha256": _sha256(snapshot_path),
        "created_at": str(manifest.get("created_at", "")),
        "provider_metadata": manifest.get("provider_metadata", {}),
        "contract": manifest.get("contract"),
    }
    audit = evaluate_confirmed_relative_growth_research(
        panel,
        validation_receipt=receipt,
        protocol_sha256=protocol_sha256,
    )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(audit, ensure_ascii=False, indent=2, allow_nan=False),
        encoding="utf-8",
    )
    report = build_confirmed_relative_growth_report(args.report, audit)
    r1000 = audit["datasets"]["russell_1000"]
    r2000 = audit["datasets"]["russell_2000"]
    print(f"機器可讀研究收據：{output}")
    print(f"研究報表：{report}")
    print(
        "v13 結論：新資料經濟門檻 "
        f"{audit['economic_passed_gate_count']}/{audit['economic_required_gate_count']}；"
        f"Russell 1000 CAGR {r1000['strategy_metrics']['cagr']:.2%} / "
        f"IWB {r1000['benchmark_metrics']['market']['cagr']:.2%}；"
        f"Russell 2000 CAGR {r2000['strategy_metrics']['cagr']:.2%} / "
        f"IWM {r2000['benchmark_metrics']['market']['cagr']:.2%}；"
        f"Paper {'可建立' if audit['paper_eligible'] else '不建立'}"
    )
    return 0


def _v14_modest_leverage(args: argparse.Namespace) -> int:
    protocol_path = Path(args.protocol)
    protocol_sha256 = _sha256(protocol_path)
    if protocol_sha256 != V14_PROTOCOL_SHA256:
        raise ValueError("v14 協議檔已與首次槓桿 ETF 下載前凍結雜湊不同")

    protocol_receipt = json.loads(Path(args.protocol_receipt).read_text(encoding="utf-8"))
    data_receipt = json.loads(Path(args.data_receipt).read_text(encoding="utf-8"))
    snapshot_path = Path(args.validation_snapshot)
    panel, manifest = load_snapshot(snapshot_path)
    actual_panel_sha256 = panel_fingerprint(panel)
    if actual_panel_sha256 != manifest.get("panel_sha256"):
        raise ValueError("v14 快照面板內容與 manifest 雜湊不同")
    receipt = {
        "path": str(snapshot_path),
        "rows": int(manifest["rows"]),
        "start": str(manifest["start"]),
        "end": str(manifest["end"]),
        "tickers": list(manifest["tickers"]),
        "panel_sha256": actual_panel_sha256,
        "archive_sha256": _sha256(snapshot_path),
        "created_at": str(manifest.get("created_at", "")),
        "provider_metadata": manifest.get("provider_metadata", {}),
        "contract": manifest.get("contract"),
    }
    audit = evaluate_modest_leverage_research(
        panel,
        validation_receipt=receipt,
        protocol_receipt=protocol_receipt,
        data_receipt=data_receipt,
        protocol_sha256=protocol_sha256,
    )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(audit, ensure_ascii=False, indent=2, allow_nan=False),
        encoding="utf-8",
    )
    report = build_modest_leverage_report(args.report, audit)
    sp500 = audit["datasets"]["sp500"]
    nasdaq = audit["datasets"]["nasdaq100"]
    dow = audit["datasets"]["dow30"]
    print(f"機器可讀研究收據：{output}")
    print(f"研究報表：{report}")
    print(
        "v14 結論：經濟門檻 "
        f"{audit['economic_passed_gate_count']}/{audit['economic_required_gate_count']}；"
        f"S&P 500 {sp500['strategy_metrics']['cagr']:.2%} / SPY "
        f"{sp500['benchmark_metrics']['core']['cagr']:.2%}；"
        f"Nasdaq-100 {nasdaq['strategy_metrics']['cagr']:.2%} / QQQ "
        f"{nasdaq['benchmark_metrics']['core']['cagr']:.2%}；"
        f"Dow 30 {dow['strategy_metrics']['cagr']:.2%} / DIA "
        f"{dow['benchmark_metrics']['core']['cagr']:.2%}；"
        f"Paper {'可建立' if audit['paper_eligible'] else '不建立'}"
    )
    return 0


def _v15_modest_leverage_overlay(args: argparse.Namespace) -> int:
    protocol_path = Path(args.protocol)
    protocol_sha256 = _sha256(protocol_path)
    if protocol_sha256 != V15_PROTOCOL_SHA256:
        raise ValueError("v15 協議檔已與首次 3 倍 ETF 下載前凍結雜湊不同")

    protocol_receipt = json.loads(Path(args.protocol_receipt).read_text(encoding="utf-8"))
    data_receipt = json.loads(Path(args.data_receipt).read_text(encoding="utf-8"))
    snapshot_path = Path(args.validation_snapshot)
    panel, manifest = load_snapshot(snapshot_path)
    actual_panel_sha256 = panel_fingerprint(panel)
    if actual_panel_sha256 != manifest.get("panel_sha256"):
        raise ValueError("v15 快照面板內容與 manifest 雜湊不同")
    receipt = {
        "path": str(snapshot_path),
        "rows": int(manifest["rows"]),
        "start": str(manifest["start"]),
        "end": str(manifest["end"]),
        "tickers": list(manifest["tickers"]),
        "panel_sha256": actual_panel_sha256,
        "archive_sha256": _sha256(snapshot_path),
        "created_at": str(manifest.get("created_at", "")),
        "provider_metadata": manifest.get("provider_metadata", {}),
        "contract": manifest.get("contract"),
    }
    audit = evaluate_modest_leverage_overlay_research(
        panel,
        validation_receipt=receipt,
        protocol_receipt=protocol_receipt,
        data_receipt=data_receipt,
        protocol_sha256=protocol_sha256,
    )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(audit, ensure_ascii=False, indent=2, allow_nan=False),
        encoding="utf-8",
    )
    report = build_modest_leverage_overlay_report(args.report, audit)
    sp500 = audit["datasets"]["sp500"]
    nasdaq = audit["datasets"]["nasdaq100"]
    dow = audit["datasets"]["dow30"]
    print(f"機器可讀研究收據：{output}")
    print(f"研究報表：{report}")
    print(
        "v15 結論：經濟門檻 "
        f"{audit['economic_passed_gate_count']}/{audit['economic_required_gate_count']}；"
        f"S&P 500 {sp500['strategy_metrics']['cagr']:.2%} / SPY "
        f"{sp500['benchmark_metrics']['core']['cagr']:.2%}；"
        f"Nasdaq-100 {nasdaq['strategy_metrics']['cagr']:.2%} / QQQ "
        f"{nasdaq['benchmark_metrics']['core']['cagr']:.2%}；"
        f"Dow 30 {dow['strategy_metrics']['cagr']:.2%} / DIA "
        f"{dow['benchmark_metrics']['core']['cagr']:.2%}；"
        f"Paper {'可建立' if audit['paper_eligible'] else '不建立'}"
    )
    return 0


def _frozen_validation_receipt(snapshot_path: Path, manifest: dict[str, Any]) -> dict[str, Any]:
    panel, _ = load_snapshot(snapshot_path)
    return {
        "path": str(snapshot_path),
        "rows": int(manifest["rows"]),
        "start": str(manifest["start"]),
        "end": str(manifest["end"]),
        "tickers": list(manifest["tickers"]),
        "panel_sha256": panel_fingerprint(panel),
        "archive_sha256": _sha256(snapshot_path),
        "created_at": str(manifest.get("created_at", "")),
        "provider_metadata": manifest.get("provider_metadata", {}),
        "contract": manifest.get("contract"),
    }


def _v16_trend_volatility_brake(args: argparse.Namespace) -> int:
    protocol_path = Path(args.protocol)
    protocol_sha256 = _sha256(protocol_path)
    if protocol_sha256 != V16_PROTOCOL_SHA256:
        raise ValueError("v16 協議檔已與首次中小型 2 倍 ETF 下載前凍結雜湊不同")
    protocol_receipt = json.loads(Path(args.protocol_receipt).read_text(encoding="utf-8"))
    data_receipt = json.loads(Path(args.data_receipt).read_text(encoding="utf-8"))
    snapshot_path = Path(args.validation_snapshot)
    panel, manifest = load_snapshot(snapshot_path)
    receipt = _frozen_validation_receipt(snapshot_path, manifest)
    if receipt["panel_sha256"] != manifest.get("panel_sha256"):
        raise ValueError("v16 快照面板內容與 manifest 雜湊不同")
    audit = evaluate_trend_volatility_brake_research(
        panel,
        validation_receipt=receipt,
        protocol_receipt=protocol_receipt,
        data_receipt=data_receipt,
        protocol_sha256=protocol_sha256,
    )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(audit, ensure_ascii=False, indent=2, allow_nan=False),
        encoding="utf-8",
    )
    report = build_trend_volatility_brake_report(args.report, audit)
    print(f"機器可讀研究收據：{output}")
    print(f"研究報表：{report}")
    print(
        "v16 結論：經濟門檻 "
        f"{audit['economic_passed_gate_count']}/{audit['economic_required_gate_count']}；"
        f"統計 {audit['statistical_passed_gate_count']}/"
        f"{audit['statistical_required_gate_count']}；"
        f"Paper {'可建立' if audit['paper_eligible'] else '不建立'}"
    )
    return 0


def _v17_capital_efficient(args: argparse.Namespace) -> int:
    protocol_path = Path(args.protocol)
    protocol_sha256 = _sha256(protocol_path)
    if protocol_sha256 != V17_PROTOCOL_SHA256:
        raise ValueError("v17 協議檔已與首次資本效率組合計算前凍結雜湊不同")
    protocol_receipt = json.loads(Path(args.protocol_receipt).read_text(encoding="utf-8"))
    data_receipt = json.loads(Path(args.data_receipt).read_text(encoding="utf-8"))
    snapshot_path = Path(args.validation_snapshot)
    panel, manifest = load_snapshot(snapshot_path)
    receipt = _frozen_validation_receipt(snapshot_path, manifest)
    if receipt["panel_sha256"] != manifest.get("panel_sha256"):
        raise ValueError("v17 快照面板內容與 manifest 雜湊不同")
    audit = evaluate_capital_efficient_research(
        panel,
        validation_receipt=receipt,
        protocol_receipt=protocol_receipt,
        data_receipt=data_receipt,
        protocol_sha256=protocol_sha256,
    )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(audit, ensure_ascii=False, indent=2, allow_nan=False),
        encoding="utf-8",
    )
    report = build_capital_efficient_report(args.report, audit)
    print(f"機器可讀研究收據：{output}")
    print(f"研究報表：{report}")
    print(
        "v17 結論：經濟門檻 "
        f"{audit['economic_passed_gate_count']}/{audit['economic_required_gate_count']}；"
        f"統計 {audit['statistical_passed_gate_count']}/"
        f"{audit['statistical_required_gate_count']}；"
        f"Paper {'可建立' if audit['paper_eligible'] else '不建立'}"
    )
    return 0


def _v18_equal_diversifier(args: argparse.Namespace) -> int:
    protocol_path = Path(args.protocol)
    protocol_sha256 = _sha256(protocol_path)
    if protocol_sha256 != V18_PROTOCOL_SHA256:
        raise ValueError("v18 協議檔已與首次海外日線下載前凍結雜湊不同")
    protocol_receipt = json.loads(Path(args.protocol_receipt).read_text(encoding="utf-8"))
    data_receipt = json.loads(Path(args.data_receipt).read_text(encoding="utf-8"))
    snapshot_path = Path(args.validation_snapshot)
    panel, manifest = load_snapshot(snapshot_path)
    receipt = _frozen_validation_receipt(snapshot_path, manifest)
    if receipt["panel_sha256"] != manifest.get("panel_sha256"):
        raise ValueError("v18 快照面板內容與 manifest 雜湊不同")
    audit = evaluate_equal_diversifier_research(
        panel,
        validation_receipt=receipt,
        protocol_receipt=protocol_receipt,
        data_receipt=data_receipt,
        protocol_sha256=protocol_sha256,
    )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(audit, ensure_ascii=False, indent=2, allow_nan=False),
        encoding="utf-8",
    )
    report = build_equal_diversifier_report(args.report, audit)
    print(f"機器可讀研究收據：{output}")
    print(f"研究報表：{report}")
    print(
        "v18 結論：海外經濟門檻 "
        f"{audit['economic_passed_gate_count']}/{audit['economic_required_gate_count']}；"
        f"資料 {audit['data_passed_gate_count']}/{audit['data_required_gate_count']}；"
        f"統計 {audit['statistical_passed_gate_count']}/"
        f"{audit['statistical_required_gate_count']}；"
        f"Paper {'可建立' if audit['paper_eligible'] else '不建立'}"
    )
    return 0


def _v20_diversifier_strength(args: argparse.Namespace) -> int:
    protocol_path = Path(args.protocol)
    protocol_sha256 = _sha256(protocol_path)
    if protocol_sha256 != V20_PROTOCOL_SHA256:
        raise ValueError("v20 協議檔已與首次外部日線下載前凍結雜湊不同")
    protocol_receipt = json.loads(Path(args.protocol_receipt).read_text(encoding="utf-8"))
    data_receipt = json.loads(Path(args.data_receipt).read_text(encoding="utf-8"))
    product_mapping_receipt = json.loads(
        Path(args.product_mapping_receipt).read_text(encoding="utf-8")
    )
    sources: dict[str, Any] = {}
    source_receipts: dict[str, dict[str, Any]] = {}
    for key, source in (
        ("capital", args.capital_snapshot),
        ("main", args.main_snapshot),
        ("v18", args.v18_snapshot),
        ("external", args.external_snapshot),
    ):
        path = Path(source)
        panel, manifest = load_snapshot(path)
        receipt = _frozen_validation_receipt(path, manifest)
        if receipt["panel_sha256"] != manifest.get("panel_sha256"):
            raise ValueError(f"v20 {key} 快照面板內容與 manifest 雜湊不同")
        sources[key] = panel
        source_receipts[key] = receipt
    audit = evaluate_diversifier_strength_research(
        sources["capital"],
        sources["main"],
        sources["v18"],
        sources["external"],
        source_receipts=source_receipts,
        protocol_receipt=protocol_receipt,
        data_receipt=data_receipt,
        product_mapping_receipt=product_mapping_receipt,
        protocol_sha256=protocol_sha256,
    )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(audit, ensure_ascii=False, indent=2, allow_nan=False),
        encoding="utf-8",
    )
    report = build_diversifier_strength_report(args.report, audit)
    print(f"機器可讀研究收據：{output}")
    print(f"研究報表：{report}")
    print(
        "v20 結論：已見設計 "
        f"{audit['design_economic_passed_gate_count']}/"
        f"{audit['design_economic_required_gate_count']}；"
        "新外部 "
        f"{audit['external_economic_passed_gate_count']}/"
        f"{audit['external_economic_required_gate_count']}；"
        f"資料 {audit['data_passed_gate_count']}/{audit['data_required_gate_count']}；"
        f"統計 {audit['statistical_passed_gate_count']}/"
        f"{audit['statistical_required_gate_count']}；"
        f"Paper {'可建立' if audit['paper_eligible'] else '不建立'}"
    )
    return 0


def _v21_hybrid_leverage_core(args: argparse.Namespace) -> int:
    protocol_path = Path(args.protocol)
    mapping_path = Path(args.product_mapping)
    protocol_sha256 = _sha256(protocol_path)
    product_mapping_sha256 = _sha256(mapping_path)
    if protocol_sha256 != V21_PROTOCOL_SHA256:
        raise ValueError("v21 協議檔已與首次外部日線下載前凍結雜湊不同")
    if product_mapping_sha256 != V21_PRODUCT_MAPPING_SHA256:
        raise ValueError("v21 產品稽核已與首次外部日線下載前凍結雜湊不同")
    protocol_receipt = json.loads(Path(args.protocol_receipt).read_text(encoding="utf-8"))
    data_receipt = json.loads(Path(args.data_receipt).read_text(encoding="utf-8"))
    product_mapping_receipt = json.loads(
        Path(args.product_mapping_receipt).read_text(encoding="utf-8")
    )
    sources: dict[str, Any] = {}
    source_receipts: dict[str, dict[str, Any]] = {}
    for key, source in (
        ("capital", args.capital_snapshot),
        ("three_x", args.three_x_snapshot),
        ("external", args.external_snapshot),
    ):
        path = Path(source)
        panel, manifest = load_snapshot(path)
        receipt = _frozen_validation_receipt(path, manifest)
        if receipt["panel_sha256"] != manifest.get("panel_sha256"):
            raise ValueError(f"v21 {key} 快照面板內容與 manifest 雜湊不同")
        sources[key] = panel
        source_receipts[key] = receipt
    audit = evaluate_hybrid_leverage_core_research(
        sources["capital"],
        sources["three_x"],
        sources["external"],
        source_receipts=source_receipts,
        protocol_receipt=protocol_receipt,
        data_receipt=data_receipt,
        product_mapping_receipt=product_mapping_receipt,
        protocol_sha256=protocol_sha256,
        product_mapping_sha256=product_mapping_sha256,
    )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(audit, ensure_ascii=False, indent=2, allow_nan=False),
        encoding="utf-8",
    )
    report = build_hybrid_leverage_core_report(args.report, audit)
    print(f"機器可讀研究收據：{output}")
    print(f"研究報表：{report}")
    print(
        "v21 結論：已見設計 "
        f"{audit['design_economic_passed_gate_count']}/"
        f"{audit['design_economic_required_gate_count']}；"
        "新外部 "
        f"{audit['external_economic_passed_gate_count']}/"
        f"{audit['external_economic_required_gate_count']}；"
        f"資料 {audit['data_passed_gate_count']}/{audit['data_required_gate_count']}；"
        f"統計 {audit['statistical_passed_gate_count']}/"
        f"{audit['statistical_required_gate_count']}；"
        f"Paper {'可建立' if audit['paper_eligible'] else '不建立'}"
    )
    return 0


def _v22_sector_capital_efficiency(args: argparse.Namespace) -> int:
    protocol_path = Path(args.protocol)
    mapping_path = Path(args.product_mapping)
    design_path = Path(args.design_source)
    protocol_sha256 = _sha256(protocol_path)
    product_mapping_sha256 = _sha256(mapping_path)
    design_source_sha256 = _sha256(design_path)
    if protocol_sha256 != V22_PROTOCOL_SHA256:
        raise ValueError("v22 協議檔已與首次產業日線下載前凍結雜湊不同")
    if product_mapping_sha256 != V22_PRODUCT_MAPPING_SHA256:
        raise ValueError("v22 產品映射已與首次產業日線下載前凍結雜湊不同")
    if design_source_sha256 != V22_DESIGN_SOURCE_SHA256:
        raise ValueError("v22 引用的 v18 美國設計紀錄已改變")
    protocol_receipt = json.loads(Path(args.protocol_receipt).read_text(encoding="utf-8"))
    product_mapping_receipt = json.loads(
        Path(args.product_mapping_receipt).read_text(encoding="utf-8")
    )
    data_receipt = json.loads(Path(args.data_receipt).read_text(encoding="utf-8"))
    design_source_receipt = json.loads(Path(args.design_source_receipt).read_text(encoding="utf-8"))
    snapshot_path = Path(args.validation_snapshot)
    panel, manifest = load_snapshot(snapshot_path)
    receipt = _frozen_validation_receipt(snapshot_path, manifest)
    if receipt["panel_sha256"] != manifest.get("panel_sha256"):
        raise ValueError("v22 快照面板內容與 manifest 雜湊不同")
    audit = evaluate_sector_capital_efficiency_research(
        panel,
        validation_receipt=receipt,
        protocol_receipt=protocol_receipt,
        product_mapping_receipt=product_mapping_receipt,
        data_receipt=data_receipt,
        design_source_receipt=design_source_receipt,
        protocol_sha256=protocol_sha256,
        product_mapping_sha256=product_mapping_sha256,
        design_source_sha256=design_source_sha256,
    )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(audit, ensure_ascii=False, indent=2, allow_nan=False),
        encoding="utf-8",
    )
    report = build_sector_capital_efficiency_report(args.report, audit)
    print(f"機器可讀研究收據：{output}")
    print(f"研究報表：{report}")
    print(
        "v22 結論：產業個別門檻 "
        f"{audit['individual_passed_gate_count']}/"
        f"{audit['individual_required_gate_count']}；"
        f"整體經濟 {audit['economic_passed_gate_count']}/"
        f"{audit['economic_required_gate_count']}；"
        f"資料 {audit['data_passed_gate_count']}/{audit['data_required_gate_count']}；"
        f"統計 {audit['statistical_passed_gate_count']}/"
        f"{audit['statistical_required_gate_count']}；"
        f"Paper {'可建立' if audit['paper_eligible'] else '不建立'}"
    )
    return 0


def _v23_managed_futures_capital_efficiency(args: argparse.Namespace) -> int:
    protocol_path = Path(args.protocol)
    mapping_path = Path(args.product_mapping)
    protocol_sha256 = _sha256(protocol_path)
    product_mapping_sha256 = _sha256(mapping_path)
    if protocol_sha256 != V23_PROTOCOL_SHA256:
        raise ValueError("v23 協議檔已與首次 KMLM／FMF 下載前凍結雜湊不同")
    if product_mapping_sha256 != V23_PRODUCT_MAPPING_SHA256:
        raise ValueError("v23 產品映射已與首次 KMLM／FMF 下載前凍結雜湊不同")
    protocol_receipt = json.loads(Path(args.protocol_receipt).read_text(encoding="utf-8"))
    data_receipt = json.loads(Path(args.data_receipt).read_text(encoding="utf-8"))

    sources: dict[str, Any] = {}
    receipts: dict[str, dict[str, Any]] = {}
    for key, source in (
        ("design", args.design_snapshot),
        ("kmlm", args.kmlm_snapshot),
        ("fmf", args.fmf_snapshot),
    ):
        snapshot_path = Path(source)
        panel, manifest = load_snapshot(snapshot_path)
        receipt = _frozen_validation_receipt(snapshot_path, manifest)
        if receipt["panel_sha256"] != manifest.get("panel_sha256"):
            raise ValueError(f"v23 {key} 快照面板內容與 manifest 雜湊不同")
        sources[key] = panel
        receipts[key] = receipt

    audit = evaluate_managed_futures_capital_efficiency(
        sources["design"],
        sources["kmlm"],
        sources["fmf"],
        design_receipt=receipts["design"],
        kmlm_receipt=receipts["kmlm"],
        fmf_receipt=receipts["fmf"],
        protocol_receipt=protocol_receipt,
        data_receipt=data_receipt,
        protocol_sha256=protocol_sha256,
        product_mapping_sha256=product_mapping_sha256,
        kfa_pdf_path=args.kfa_pdf,
        kfa_monthly_csv_path=args.kfa_monthly_csv,
    )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(audit, ensure_ascii=False, indent=2, allow_nan=False),
        encoding="utf-8",
    )
    report = build_managed_futures_capital_efficiency_report(args.report, audit)
    print(f"機器可讀研究收據：{output}")
    print(f"研究報表：{report}")
    print(
        "v23 結論：20 年 "
        f"{audit['long_passed_gate_count']}/{audit['long_required_gate_count']}；"
        "KMLM 實際橋接 "
        f"{audit['kmlm_bridge_passed_gate_count']}/"
        f"{audit['kmlm_bridge_required_gate_count']}；"
        "FMF 跨管理人 "
        f"{audit['fmf_passed_gate_count']}/{audit['fmf_required_gate_count']}；"
        f"資料 {audit['data_passed_gate_count']}/{audit['data_required_gate_count']}；"
        f"Paper {'可建立' if audit['paper_eligible'] else '不建立'}"
    )
    return 0


def _v24_quality_momentum_factor(args: argparse.Namespace) -> int:
    protocol_sha256 = _sha256(Path(args.protocol))
    product_mapping_sha256 = _sha256(Path(args.product_mapping))
    if protocol_sha256 != V24_PROTOCOL_SHA256:
        raise ValueError("v24 協議檔已與首次學術／產品下載前凍結雜湊不同")
    if product_mapping_sha256 != V24_PRODUCT_MAPPING_SHA256:
        raise ValueError("v24 產品映射已與首次學術／產品下載前凍結雜湊不同")
    protocol_receipt = json.loads(Path(args.protocol_receipt).read_text(encoding="utf-8"))
    data_receipt = json.loads(Path(args.data_receipt).read_text(encoding="utf-8"))
    ishares_path = Path(args.ishares_snapshot)
    invesco_path = Path(args.invesco_snapshot)
    ishares_panel, ishares_manifest = load_snapshot(ishares_path)
    invesco_panel, invesco_manifest = load_snapshot(invesco_path)
    ishares_receipt = _frozen_validation_receipt(ishares_path, ishares_manifest)
    invesco_receipt = _frozen_validation_receipt(invesco_path, invesco_manifest)
    if ishares_receipt["panel_sha256"] != ishares_manifest.get("panel_sha256"):
        raise ValueError("v24 iShares 快照面板內容與 manifest 雜湊不同")
    if invesco_receipt["panel_sha256"] != invesco_manifest.get("panel_sha256"):
        raise ValueError("v24 Invesco 快照面板內容與 manifest 雜湊不同")
    audit = evaluate_quality_momentum_factor(
        ishares_panel,
        invesco_panel,
        ishares_manifest=ishares_receipt,
        invesco_manifest=invesco_receipt,
        protocol_receipt=protocol_receipt,
        data_receipt=data_receipt,
        protocol_sha256=protocol_sha256,
        product_mapping_sha256=product_mapping_sha256,
        french_paths={
            "market": args.french_market,
            "quality": args.french_quality,
            "momentum": args.french_momentum,
        },
    )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(audit, ensure_ascii=False, indent=2, allow_nan=False),
        encoding="utf-8",
    )
    report = build_quality_momentum_factor_report(args.report, audit)
    print(f"機器可讀研究收據：{output}")
    print(f"研究報表：{report}")
    print(
        "v24 結論：20 年學術 "
        f"{audit['long_passed_gate_count']}/{audit['long_required_gate_count']}；"
        "iShares 實際 "
        f"{audit['ishares_passed_gate_count']}/{audit['ishares_required_gate_count']}；"
        "Invesco 跨管理人 "
        f"{audit['invesco_passed_gate_count']}/{audit['invesco_required_gate_count']}；"
        f"資料 {audit['data_passed_gate_count']}/{audit['data_required_gate_count']}；"
        f"Paper {'可建立' if audit['paper_eligible'] else '不建立'}"
    )
    return 0


def _v25_growth_gold_diversification(args: argparse.Namespace) -> int:
    protocol_sha256 = _sha256(Path(args.protocol))
    product_mapping_sha256 = _sha256(Path(args.product_mapping))
    if protocol_sha256 != V25_PROTOCOL_SHA256:
        raise ValueError("v25 協議檔已與首次聯合產品下載前凍結雜湊不同")
    if product_mapping_sha256 != V25_PRODUCT_MAPPING_SHA256:
        raise ValueError("v25 產品映射已與首次聯合產品下載前凍結雜湊不同")
    protocol_receipt = json.loads(Path(args.protocol_receipt).read_text(encoding="utf-8"))
    data_receipt = json.loads(Path(args.data_receipt).read_text(encoding="utf-8"))
    snapshot_paths = {
        "vanguard": Path(args.vanguard_snapshot),
        "ishares": Path(args.ishares_snapshot),
        "state_street": Path(args.state_street_snapshot),
    }
    panels: dict[str, Any] = {}
    receipts: dict[str, dict[str, Any]] = {}
    for label, path in snapshot_paths.items():
        panel, manifest = load_snapshot(path)
        receipt = _frozen_validation_receipt(path, manifest)
        if receipt["panel_sha256"] != manifest.get("panel_sha256"):
            raise ValueError(f"v25 {label} 快照面板內容與 manifest 雜湊不同")
        panels[label] = panel
        receipts[label] = receipt
    audit = evaluate_growth_gold_diversification(
        panels,
        manifests=receipts,
        protocol_receipt=protocol_receipt,
        data_receipt=data_receipt,
        protocol_sha256=protocol_sha256,
        product_mapping_sha256=product_mapping_sha256,
    )
    audit["paper_state_created"] = Path("artifacts/paper_v25_state.json").exists()
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(audit, ensure_ascii=False, indent=2, allow_nan=False),
        encoding="utf-8",
    )
    report = build_growth_gold_diversification_report(args.report, audit)
    path_summary = "；".join(
        f"{label} {row['passed_gate_count']}/{row['required_gate_count']}"
        for label, row in audit["paths"].items()
    )
    print(f"機器可讀研究收據：{output}")
    print(f"研究報表：{report}")
    print(
        f"v25 結論：{path_summary}；彙總 "
        f"{audit['pooled_passed_gate_count']}/{audit['pooled_required_gate_count']}；"
        f"資料 {audit['data_passed_gate_count']}/{audit['data_required_gate_count']}；"
        f"Paper {'可建立' if audit['paper_eligible'] else '不建立'}；實金仍關閉"
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="us-fddk",
        description="可重現、先驗證後敘事的美股資料與策略研究工具",
    )
    sub = parser.add_subparsers(dest="command")
    build = sub.add_parser("build", help="抓資料、凍結快照、回測並產生報表")
    build.add_argument("--fetch-start", default="2004-01-01", help="下載起始日（含訊號暖機期）")
    build.add_argument("--years", type=int, default=20, help="未指定起算日時，回測最近幾年")
    build.add_argument("--backtest-start", help="固定績效起算日；提供時取代 --years")
    build.add_argument("--end", help="資料截止日（含）；省略代表抓最新交易日")
    build.add_argument("--snapshot", help="改用既有凍結快照，不重新下載")
    build.add_argument("--output", default="artifacts", help="輸出目錄")
    build.add_argument("--cost-bps", type=float, default=10.0, help="每次成交成本 bps")
    build.add_argument("--bootstrap-samples", type=int, default=1000)
    build.add_argument(
        "--proxy-snapshot",
        default="artifacts/snapshot_ndx_proxy_19851001_20060728_4814654a.zip",
        help="v3 的 1985–2006 Nasdaq-100 凍結代理期快照；不存在時代理門檻失敗",
    )
    build.add_argument(
        "--cross-market-validation",
        default="artifacts/cross_market_validation.json",
        help="已凍結的 v3 五市場驗證收據；存在時納入網站資料",
    )
    build.add_argument(
        "--style-rotation-validation",
        default="artifacts/v4_style_validation.json",
        help="已凍結的 v4 風格輪動驗證收據；存在時納入網站資料",
    )
    build.add_argument(
        "--three-clock-validation",
        default="artifacts/v5_three_clock_validation.json",
        help="已凍結的 v5 三時鐘完整驗證收據；存在時納入網站資料",
    )
    build.add_argument(
        "--industry-tilt-validation",
        default="artifacts/v6_industry_validation.json",
        help="下載新資料前已凍結的 v6 產業動能驗證收據；存在時納入網站資料",
    )
    build.add_argument(
        "--relative-growth-validation",
        default="artifacts/v7_relative_growth_validation.json",
        help="第一次計算前已凍結的 v7 相對成長衛星驗證收據；存在時納入網站資料",
    )
    build.add_argument(
        "--always-invested-validation",
        default="artifacts/v8_always_invested_validation.json",
        help="第一次計算前已凍結的 v8 永遠持股相對成長驗證收據；存在時納入網站資料",
    )
    build.add_argument(
        "--low-turnover-validation",
        default="artifacts/v9_low_turnover_validation.json",
        help="含下載前未見外部期的 v9 低換手驗證收據；存在時納入網站資料",
    )
    build.add_argument(
        "--hierarchical-defense-validation",
        default="artifacts/v12_hierarchical_validation.json",
        help="第一次計算前凍結的 v12 階層式三態驗證收據；存在時納入網站資料",
    )
    build.add_argument(
        "--confirmed-relative-growth-validation",
        default="artifacts/v13_confirmed_growth_validation.json",
        help="規則先凍結、再下載三組新 ETF 的 v13 驗證收據；存在時納入網站資料",
    )
    build.add_argument(
        "--modest-leverage-validation",
        default="artifacts/v14_modest_leverage_validation.json",
        help="先凍結、再下載三組實際槓桿 ETF 的 v14 驗證收據；存在時納入網站資料",
    )
    build.add_argument(
        "--modest-leverage-overlay-validation",
        default="artifacts/v15_modest_leverage_overlay_validation.json",
        help="先凍結、再首次查看三組實際 3 倍 ETF 的 v15 驗證收據；存在時納入網站資料",
    )
    build.add_argument(
        "--trend-volatility-brake-validation",
        default="artifacts/v16_trend_volatility_brake_validation.json",
        help="先凍結、再首次查看中小型 2 倍 ETF 的 v16 驗證收據；存在時納入網站資料",
    )
    build.add_argument(
        "--capital-efficient-validation",
        default="artifacts/v17_capital_efficient_validation.json",
        help="先凍結、再計算六市場股債資本效率組合的 v17 驗證收據；存在時納入網站資料",
    )
    build.add_argument(
        "--equal-diversifier-validation",
        default="artifacts/v18_equal_diversifier_validation.json",
        help="先凍結、再下載海外日線的 v18 股債金外部驗證收據；存在時納入網站資料",
    )
    build.add_argument(
        "--diversifier-strength-validation",
        default="artifacts/v20_diversifier_strength_validation.json",
        help="先凍結、再下載三組區域 ETF 日線的 v20 分散器輪替驗證收據；存在時納入網站資料",
    )
    build.add_argument(
        "--hybrid-leverage-core-validation",
        default="artifacts/v21_hybrid_leverage_core_validation.json",
        help="先凍結、再下載中小型股 3 倍 ETF 日線的 v21 常駐核心驗證收據；存在時納入網站資料",
    )
    build.add_argument(
        "--sector-capital-efficiency-validation",
        default="artifacts/v22_us_sector_capital_efficiency_validation.json",
        help="先凍結、再下載九組產業 ETF 日線的 v22 美國股債金驗證收據；存在時納入網站資料",
    )
    build.add_argument(
        "--managed-futures-capital-efficiency-validation",
        default="artifacts/v23_managed_futures_capital_efficiency_validation.json",
        help="先凍結的 v23 美國股票加管理期貨 20 年與兩個實際產品驗證；存在時納入網站資料",
    )
    build.add_argument(
        "--quality-momentum-factor-validation",
        default="artifacts/v24_quality_momentum_factor_validation.json",
        help="先凍結的 v24 品質動能 20 年學術代理與兩組實際產品驗證；存在時納入網站資料",
    )
    build.add_argument(
        "--growth-gold-diversification-validation",
        default="artifacts/v25_growth_gold_diversification_validation.json",
        help="先凍結的 v25 三條大型成長加黃金 20 年產品驗證；存在時納入網站資料",
    )
    build.add_argument(
        "--growth-gold-paper-state",
        default="artifacts/paper_v25_state.json",
        help="v25 隔離 LIVE Paper 狀態；存在時納入網站",
    )
    build.add_argument(
        "--growth-gold-spy-paper-state",
        default="artifacts/paper_v25_spy_state.json",
        help="v25 同起點 SPY Paper 基準",
    )
    build.add_argument(
        "--growth-gold-matched-paper-state",
        default="artifacts/paper_v25_matched_state.json",
        help="v25 同起點 80% VUG／20% SHY Paper 基準",
    )
    build.add_argument("--seed", type=int, default=20260801)
    build.add_argument("--paper-cash", type=float, default=100_000.0, help="paper 帳戶初始資金")
    build.set_defaults(func=_build)

    verify = sub.add_parser("verify", help="驗證快照雜湊與資料契約")
    verify.add_argument("snapshot")
    verify.set_defaults(func=_verify)

    paper = sub.add_parser("paper", help="建立、推進或查看持久化模擬交易帳戶")
    paper_sub = paper.add_subparsers(dest="paper_command", required=True)
    paper_update = paper_sub.add_parser("update", help="用凍結快照建立或推進帳戶")
    paper_update.add_argument("--snapshot", required=True)
    paper_update.add_argument(
        "--strategy",
        choices=(
            "v3",
            "volatility",
            "growth",
            "candidate",
            "dual",
            "spy",
            "qqq",
            "passive90",
            "v9",
            "v12",
            "v13",
            "v14",
            "v15",
            "v16",
            "v17",
            "v18",
            "v20",
            "v21",
            "v22",
            "v23",
            "v24",
            "v25",
            "v25_matched",
            "v25_spy",
        ),
        default="volatility",
    )
    paper_update.add_argument("--state", help="帳戶狀態路徑；省略時依策略選擇")
    paper_update.add_argument("--report", help="HTML 報表路徑；預設與 state 同目錄")
    paper_update.add_argument("--initial-cash", type=float, default=100_000.0)
    paper_update.add_argument("--cost-bps", type=float, default=10.0)
    paper_update.add_argument(
        "--eligibility-receipt",
        help="v9/v12/v13/v14/v15/v16/v17/v18/v20/v21/v22/v23/v24/v25 專用；省略時讀取該版本預設的完整 Paper 入口收據",
    )
    paper_update.add_argument("--replay-from", help="新帳戶才可用；明確標成歷史回放")
    paper_update.set_defaults(func=_paper_update)
    paper_status = paper_sub.add_parser("status", help="查看帳戶摘要")
    paper_status.add_argument("--state", default="artifacts/paper_volatility_state.json")
    paper_status.set_defaults(func=_paper_status)

    v25_bundle = sub.add_parser(
        "v25-paper-bundle", help="從同一快照原子推進 v25 與兩個前瞻對照帳戶"
    )
    v25_bundle.add_argument("--snapshot", required=True)
    v25_bundle.add_argument(
        "--eligibility-receipt",
        default="artifacts/v25_growth_gold_diversification_validation.json",
    )
    v25_bundle.add_argument("--candidate-state", default="artifacts/paper_v25_state.json")
    v25_bundle.add_argument("--spy-state", default="artifacts/paper_v25_spy_state.json")
    v25_bundle.add_argument("--matched-state", default="artifacts/paper_v25_matched_state.json")
    v25_bundle.add_argument("--evidence", default="artifacts/v25_forward_paper_evidence.json")
    v25_bundle.add_argument("--initial-cash", type=float, default=100_000.0)
    v25_bundle.add_argument("--cost-bps", type=float, default=10.0)
    v25_bundle.set_defaults(func=_v25_paper_bundle)

    v25_live = sub.add_parser(
        "v25-live-update",
        help="抓取最新完整交易日並同步推進 v25、SPY 與公平基準 Paper",
    )
    v25_live.add_argument(
        "--snapshot",
        help="使用既有快照；仍會依 --as-of 驗證應有交易日，適合稽核與測試",
    )
    v25_live.add_argument("--fetch-start", default="2026-07-01")
    v25_live.add_argument("--end", help="行情截止日；省略時使用最近已收盤交易日")
    v25_live.add_argument(
        "--as-of",
        help="新鮮度判定時間或日期；正式日更應省略，測試凍結快照時可明確指定",
    )
    v25_live.add_argument("--output-dir", default="artifacts")
    v25_live.add_argument(
        "--eligibility-receipt",
        default="artifacts/v25_growth_gold_diversification_validation.json",
    )
    v25_live.add_argument("--candidate-state", default="artifacts/paper_v25_state.json")
    v25_live.add_argument("--spy-state", default="artifacts/paper_v25_spy_state.json")
    v25_live.add_argument("--matched-state", default="artifacts/paper_v25_matched_state.json")
    v25_live.add_argument("--evidence", default="artifacts/v25_forward_paper_evidence.json")
    v25_live.add_argument("--status", default="artifacts/v25_live_update_status.json")
    v25_live.add_argument("--initial-cash", type=float, default=100_000.0)
    v25_live.add_argument("--cost-bps", type=float, default=10.0)
    v25_live.set_defaults(func=_v25_live_update)

    v25_site = sub.add_parser(
        "v25-site-export",
        help="保留凍結研究結果，只更新 v25 LIVE Paper 網站資料",
    )
    v25_site.add_argument("--template", default="site/data/trading-data.json")
    v25_site.add_argument("--site-data", default="site/data/trading-data.json")
    v25_site.add_argument("--artifact-site-data", default="artifacts/site_data.json")
    v25_site.add_argument("--candidate-state", default="artifacts/paper_v25_state.json")
    v25_site.add_argument("--spy-state", default="artifacts/paper_v25_spy_state.json")
    v25_site.add_argument(
        "--matched-state", default="artifacts/paper_v25_matched_state.json"
    )
    v25_site.set_defaults(func=_v25_site_export)

    v25_reference = sub.add_parser(
        "v25-reference-check",
        help="交叉檢查 v25 網站、候選與兩個 LIVE Paper 基準",
    )
    v25_reference.add_argument("--site-data", default="artifacts/site_data.json")
    v25_reference.add_argument("--candidate-state", default="artifacts/paper_v25_state.json")
    v25_reference.add_argument("--spy-state", default="artifacts/paper_v25_spy_state.json")
    v25_reference.add_argument("--matched-state", default="artifacts/paper_v25_matched_state.json")
    v25_reference.add_argument("--output", default="artifacts/v25_reference_readiness.json")
    v25_reference.add_argument(
        "--receipt-ledger", default="artifacts/v25_live_evidence_ledger.jsonl"
    )
    v25_reference.add_argument("--require-trade-ready", action="store_true")
    v25_reference.set_defaults(func=_v25_reference_check)

    v25_refresh = sub.add_parser(
        "v25-refresh-status",
        help="合併 v25 LIVE 更新與網站稽核，產生部署／不部署決策",
    )
    v25_refresh.add_argument("--update-status", default="artifacts/v25_live_update_status.json")
    v25_refresh.add_argument("--audit", default="artifacts/v25_reference_readiness.json")
    v25_refresh.add_argument("--output", default="artifacts/v25_live_refresh_status.json")
    v25_refresh.set_defaults(func=_v25_refresh_status)

    reference = sub.add_parser("reference-check", help="部署前檢查訊號鮮度與 LIVE paper 一致性")
    reference.add_argument("--site-data", default="artifacts/site_data.json")
    reference.add_argument("--paper-state", default="artifacts/paper_volatility_state.json")
    reference.add_argument("--spy-paper-state", default="artifacts/paper_spy_state.json")
    reference.add_argument("--qqq-paper-state", default="artifacts/paper_qqq_state.json")
    reference.add_argument(
        "--passive90-paper-state", default="artifacts/paper_passive90_state.json"
    )
    reference.add_argument("--challenger-paper-state", default="artifacts/paper_v3_state.json")
    reference.add_argument(
        "--output",
        default="artifacts/reference_readiness.json",
        help="資料完整性與實金 readiness 的機器可讀收據",
    )
    reference.add_argument(
        "--receipt-ledger",
        default="artifacts/live_evidence_ledger.jsonl",
        help="前瞻證據的不可回填雜湊鏈收據",
    )
    reference.add_argument(
        "--require-trade-ready",
        action="store_true",
        help="若尚不可實金參考則以狀態碼 4 拒絕",
    )
    reference.set_defaults(func=_reference_check)

    refresh_status = sub.add_parser("refresh-status", help="產生每日 LIVE 更新是否可部署的機器收據")
    refresh_status.add_argument("--previous-data-through", default="")
    refresh_status.add_argument("--audit", default="artifacts/reference_readiness.json")
    refresh_status.add_argument("--paper-state", default="artifacts/paper_volatility_state.json")
    refresh_status.add_argument("--challenger-paper-state", default="artifacts/paper_v3_state.json")
    refresh_status.add_argument("--spy-paper-state", default="artifacts/paper_spy_state.json")
    refresh_status.add_argument("--qqq-paper-state", default="artifacts/paper_qqq_state.json")
    refresh_status.add_argument(
        "--passive90-paper-state", default="artifacts/paper_passive90_state.json"
    )
    refresh_status.add_argument("--output", default="artifacts/live_refresh_status.json")
    refresh_status.set_defaults(func=_refresh_status)

    cross_market = sub.add_parser("cross-market", help="執行事前凍結的 v3 五市場機制驗證")
    cross_market.add_argument("--protocol", default="docs/V3_CROSS_MARKET_PROTOCOL.md")
    cross_market.add_argument(
        "--gspc-snapshot",
        default="artifacts/cross_market_gspc_19870101_20060728_fbe6b740.zip",
    )
    cross_market.add_argument(
        "--ftse-snapshot",
        default="artifacts/cross_market_ftse_19870101_20060728_e0e17b65.zip",
    )
    cross_market.add_argument(
        "--gdaxi-snapshot",
        default="artifacts/cross_market_gdaxi_19870101_20060728_ecf4465b.zip",
    )
    cross_market.add_argument(
        "--n225-snapshot",
        default="artifacts/cross_market_n225_19870101_20060728_df89bb42.zip",
    )
    cross_market.add_argument(
        "--hsi-snapshot",
        default="artifacts/cross_market_hsi_19870101_20060728_e05499d6.zip",
    )
    cross_market.add_argument("--output", default="artifacts/cross_market_validation.json")
    cross_market.add_argument("--report", default="artifacts/cross_market_report.html")
    cross_market.set_defaults(func=_cross_market)

    style_rotation = sub.add_parser("v4-style", help="執行事前凍結的 v4 股權風格輪動驗證")
    style_rotation.add_argument("--protocol", default="docs/V4_STYLE_ROTATION_PROTOCOL.md")
    style_rotation.add_argument(
        "--trade-snapshot",
        default="artifacts/snapshot_v4_style_trade_20030701_20260731_e879c128.zip",
    )
    style_rotation.add_argument(
        "--proxy-snapshot",
        default="artifacts/snapshot_v4_style_proxy_19930701_20060728_a94ed540.zip",
    )
    style_rotation.add_argument("--output", default="artifacts/v4_style_validation.json")
    style_rotation.add_argument("--report", default="artifacts/v4_style_report.html")
    style_rotation.set_defaults(func=_style_rotation)

    three_clock = sub.add_parser("v5-three-clock", help="執行事前凍結的 v5 三時鐘等權集成驗證")
    three_clock.add_argument("--protocol", default="docs/V5_THREE_CLOCK_PROTOCOL.md")
    three_clock.add_argument("--main-snapshot", default="artifacts/snapshot_20260731_6a7ca6b8.zip")
    three_clock.add_argument(
        "--proxy-snapshot",
        default="artifacts/snapshot_ndx_proxy_19851001_20060728_4814654a.zip",
    )
    three_clock.add_argument(
        "--gspc-snapshot",
        default="artifacts/cross_market_gspc_19870101_20060728_fbe6b740.zip",
    )
    three_clock.add_argument(
        "--ftse-snapshot",
        default="artifacts/cross_market_ftse_19870101_20060728_e0e17b65.zip",
    )
    three_clock.add_argument(
        "--gdaxi-snapshot",
        default="artifacts/cross_market_gdaxi_19870101_20060728_ecf4465b.zip",
    )
    three_clock.add_argument(
        "--n225-snapshot",
        default="artifacts/cross_market_n225_19870101_20060728_df89bb42.zip",
    )
    three_clock.add_argument(
        "--hsi-snapshot",
        default="artifacts/cross_market_hsi_19870101_20060728_e05499d6.zip",
    )
    three_clock.add_argument("--output", default="artifacts/v5_three_clock_validation.json")
    three_clock.add_argument("--report", default="artifacts/v5_three_clock_report.html")
    three_clock.set_defaults(func=_three_clock)

    industry_tilt = sub.add_parser(
        "v6-industry", help="執行資料下載前凍結的 v6 產業動能核心傾斜驗證"
    )
    industry_tilt.add_argument("--protocol", default="docs/V6_INDUSTRY_TILT_PROTOCOL.md")
    industry_tilt.add_argument(
        "--etf-snapshot",
        default="artifacts/snapshot_v6_sector_etf_19981201_20260731_9238e84a.zip",
    )
    industry_tilt.add_argument(
        "--industry-zip", default="artifacts/french_10_industry_245ac83a.zip"
    )
    industry_tilt.add_argument("--factors-zip", default="artifacts/french_ff_factors_80b88699.zip")
    industry_tilt.add_argument("--data-receipt", default="artifacts/v6_data_receipt.json")
    industry_tilt.add_argument("--output", default="artifacts/v6_industry_validation.json")
    industry_tilt.add_argument("--report", default="artifacts/v6_industry_report.html")
    industry_tilt.set_defaults(func=_industry_tilt)

    relative_growth = sub.add_parser(
        "v7-relative-growth", help="執行第一次計算前凍結的 v7 相對成長衛星驗證"
    )
    relative_growth.add_argument("--protocol", default="docs/V7_RELATIVE_GROWTH_PROTOCOL.md")
    relative_growth.add_argument(
        "--main-snapshot", default="artifacts/snapshot_20260731_6a7ca6b8.zip"
    )
    relative_growth.add_argument(
        "--ndx-snapshot",
        default="artifacts/snapshot_ndx_proxy_19851001_20060728_4814654a.zip",
    )
    relative_growth.add_argument(
        "--gspc-snapshot",
        default="artifacts/cross_market_gspc_19870101_20060728_fbe6b740.zip",
    )
    relative_growth.add_argument("--data-receipt", default="artifacts/v7_data_receipt.json")
    relative_growth.add_argument("--output", default="artifacts/v7_relative_growth_validation.json")
    relative_growth.add_argument("--report", default="artifacts/v7_relative_growth_report.html")
    relative_growth.set_defaults(func=_relative_growth)

    always_invested = sub.add_parser(
        "v8-always-invested", help="執行第一次計算前凍結的 v8 永遠持股相對成長驗證"
    )
    always_invested.add_argument("--protocol", default="docs/V8_ALWAYS_INVESTED_PROTOCOL.md")
    always_invested.add_argument(
        "--main-snapshot", default="artifacts/snapshot_20260731_6a7ca6b8.zip"
    )
    always_invested.add_argument(
        "--ndx-snapshot",
        default="artifacts/snapshot_ndx_proxy_19851001_20060728_4814654a.zip",
    )
    always_invested.add_argument(
        "--gspc-snapshot",
        default="artifacts/cross_market_gspc_19870101_20060728_fbe6b740.zip",
    )
    always_invested.add_argument("--data-receipt", default="artifacts/v8_data_receipt.json")
    always_invested.add_argument("--output", default="artifacts/v8_always_invested_validation.json")
    always_invested.add_argument("--report", default="artifacts/v8_always_invested_report.html")
    always_invested.set_defaults(func=_always_invested)
    v9_fetch = sub.add_parser("v9-fetch-external", help="依下載前凍結契約取得 v9 全新外部指數樣本")
    v9_fetch.add_argument("--protocol", default="docs/V9_LOW_TURNOVER_EXTERNAL_PROTOCOL.md")
    v9_fetch.add_argument("--data-contract", default="docs/V9_EXTERNAL_DATA_CONTRACT.md")
    v9_fetch.add_argument("--output-dir", default="artifacts")
    v9_fetch.add_argument("--data-receipt", default="artifacts/v9_external_data_receipt.json")
    v9_fetch.set_defaults(func=_v9_fetch_external)
    v9 = sub.add_parser("v9-low-turnover", help="執行凍結的 v9 低換手三年代外部驗證")
    v9.add_argument("--protocol", default="docs/V9_LOW_TURNOVER_EXTERNAL_PROTOCOL.md")
    v9.add_argument("--data-contract", default="docs/V9_EXTERNAL_DATA_CONTRACT.md")
    v9.add_argument("--main-snapshot", default="artifacts/snapshot_20260731_6a7ca6b8.zip")
    v9.add_argument(
        "--ndx-snapshot",
        default="artifacts/snapshot_ndx_proxy_19851001_20060728_4814654a.zip",
    )
    v9.add_argument(
        "--old-gspc-snapshot",
        default="artifacts/cross_market_gspc_19870101_20060728_fbe6b740.zip",
    )
    v9.add_argument(
        "--ixic-snapshot",
        default="artifacts/snapshot_v9_ixic_19710205_19881230_76bc29b6.zip",
    )
    v9.add_argument(
        "--external-gspc-snapshot",
        default="artifacts/snapshot_v9_gspc_19710205_19881230_414d7879.zip",
    )
    v9.add_argument(
        "--external-data-receipt",
        default="artifacts/v9_external_data_receipt.json",
    )
    v9.add_argument("--output", default="artifacts/v9_low_turnover_validation.json")
    v9.add_argument("--report", default="artifacts/v9_low_turnover_report.html")
    v9.set_defaults(func=_v9_low_turnover)
    v10_fetch = sub.add_parser(
        "v10-fetch-dji", help="依下載前凍結契約取得 v10 尚未檢視的 DJIA 核心"
    )
    v10_fetch.add_argument("--protocol", default="docs/V10_HIERARCHICAL_DEFENSE_PROTOCOL.md")
    v10_fetch.add_argument("--data-contract", default="docs/V10_DJI_DATA_CONTRACT.md")
    v10_fetch.add_argument(
        "--ixic-snapshot",
        default="artifacts/snapshot_v9_ixic_19710205_19881230_76bc29b6.zip",
    )
    v10_fetch.add_argument("--output-dir", default="artifacts")
    v10_fetch.add_argument("--data-receipt", default="artifacts/v10_dji_data_receipt.json")
    v10_fetch.set_defaults(func=_v10_fetch_dji)
    v11_fetch = sub.add_parser(
        "v11-fetch-official-dji",
        help="依下載前凍結契約取得 S&P DJI 官方 DJIA 日收盤",
    )
    v11_fetch.add_argument(
        "--protocol",
        default="docs/V11_HIERARCHICAL_DEFENSE_OFFICIAL_DJI_PROTOCOL.md",
    )
    v11_fetch.add_argument("--data-contract", default="docs/V11_OFFICIAL_DJI_DATA_CONTRACT.md")
    v11_fetch.add_argument(
        "--ixic-snapshot",
        default="artifacts/snapshot_v9_ixic_19710205_19881230_76bc29b6.zip",
    )
    v11_fetch.add_argument("--output-dir", default="artifacts")
    v11_fetch.add_argument("--data-receipt", default="artifacts/v11_official_dji_data_receipt.json")
    v11_fetch.set_defaults(func=_v11_fetch_official_dji)
    v12 = sub.add_parser("v12-hierarchical", help="執行第一次計算前凍結的 v12 三樣本階層式驗證")
    v12.add_argument(
        "--protocol",
        default="docs/V12_HIERARCHICAL_DEFENSE_THREE_SAMPLE_PROTOCOL.md",
    )
    v12.add_argument("--main-snapshot", default="artifacts/snapshot_20260731_6a7ca6b8.zip")
    v12.add_argument(
        "--ndx-snapshot",
        default="artifacts/snapshot_ndx_proxy_19851001_20060728_4814654a.zip",
    )
    v12.add_argument(
        "--old-gspc-snapshot",
        default="artifacts/cross_market_gspc_19870101_20060728_fbe6b740.zip",
    )
    v12.add_argument(
        "--ixic-snapshot",
        default="artifacts/snapshot_v9_ixic_19710205_19881230_76bc29b6.zip",
    )
    v12.add_argument(
        "--external-gspc-snapshot",
        default="artifacts/snapshot_v9_gspc_19710205_19881230_414d7879.zip",
    )
    v12.add_argument("--v10-failure-receipt", default="artifacts/v10_dji_data_receipt.json")
    v12.add_argument(
        "--v11-failure-receipt",
        default="artifacts/v11_official_dji_data_receipt.json",
    )
    v12.add_argument("--output", default="artifacts/v12_hierarchical_validation.json")
    v12.add_argument("--report", default="artifacts/v12_hierarchical_report.html")
    v12.set_defaults(func=_v12_hierarchical)
    v13 = sub.add_parser(
        "v13-confirmed-growth",
        help="執行規則先凍結、再下載三組新 ETF 的 v13 相對成長驗證",
    )
    v13.add_argument(
        "--protocol",
        default="docs/V13_CONFIRMED_RELATIVE_GROWTH_PROTOCOL.md",
    )
    v13.add_argument(
        "--validation-snapshot",
        default="artifacts/snapshot_v13_validation_20040102_20260731_1301e2e1.zip",
    )
    v13.add_argument("--output", default="artifacts/v13_confirmed_growth_validation.json")
    v13.add_argument("--report", default="artifacts/v13_confirmed_growth_report.html")
    v13.set_defaults(func=_v13_confirmed_relative_growth)
    v14 = sub.add_parser(
        "v14-modest-leverage",
        help="執行先凍結、再下載三組實際槓桿 ETF 的 v14 趨勢驗證",
    )
    v14.add_argument("--protocol", default="docs/V14_MODEST_LEVERAGE_TREND_PROTOCOL.md")
    v14.add_argument("--protocol-receipt", default="artifacts/v14_protocol_receipt.json")
    v14.add_argument("--data-receipt", default="artifacts/v14_data_receipt.json")
    v14.add_argument(
        "--validation-snapshot",
        default="artifacts/snapshot_v14_leveraged_20040102_20260731_d7dc527a.zip",
    )
    v14.add_argument("--output", default="artifacts/v14_modest_leverage_validation.json")
    v14.add_argument("--report", default="artifacts/v14_modest_leverage_report.html")
    v14.set_defaults(func=_v14_modest_leverage)
    v15 = sub.add_parser(
        "v15-modest-leverage-overlay",
        help="執行先凍結、再首次查看三組實際 3 倍 ETF 的 v15 驗證",
    )
    v15.add_argument("--protocol", default="docs/V15_MODEST_LEVERAGE_OVERLAY_PROTOCOL.md")
    v15.add_argument("--protocol-receipt", default="artifacts/v15_protocol_receipt.json")
    v15.add_argument("--data-receipt", default="artifacts/v15_data_receipt.json")
    v15.add_argument(
        "--validation-snapshot",
        default="artifacts/snapshot_v15_3x_20080102_20260731_57527472_validated.zip",
    )
    v15.add_argument(
        "--output",
        default="artifacts/v15_modest_leverage_overlay_validation.json",
    )
    v15.add_argument("--report", default="artifacts/v15_modest_leverage_overlay_report.html")
    v15.set_defaults(func=_v15_modest_leverage_overlay)
    v16 = sub.add_parser(
        "v16-trend-volatility-brake",
        help="執行先凍結、再首次查看中小型 2 倍 ETF 的週度煞車驗證",
    )
    v16.add_argument("--protocol", default="docs/V16_TREND_VOLATILITY_BRAKE_PROTOCOL.md")
    v16.add_argument("--protocol-receipt", default="artifacts/v16_protocol_receipt.json")
    v16.add_argument("--data-receipt", default="artifacts/v16_data_receipt.json")
    v16.add_argument(
        "--validation-snapshot",
        default="artifacts/snapshot_v16_trend_vol_20050103_20260731_777302d4.zip",
    )
    v16.add_argument("--output", default="artifacts/v16_trend_volatility_brake_validation.json")
    v16.add_argument("--report", default="artifacts/v16_trend_volatility_brake_report.html")
    v16.set_defaults(func=_v16_trend_volatility_brake)
    v17 = sub.add_parser(
        "v17-capital-efficient",
        help="執行六市場 20／18 年固定股債資本效率驗證",
    )
    v17.add_argument("--protocol", default="docs/V17_CAPITAL_EFFICIENT_EQUITY_BOND_PROTOCOL.md")
    v17.add_argument("--protocol-receipt", default="artifacts/v17_protocol_receipt.json")
    v17.add_argument("--data-receipt", default="artifacts/v17_data_receipt.json")
    v17.add_argument(
        "--validation-snapshot",
        default="artifacts/snapshot_v17_capital_efficient_20040102_20260731_4c948bf6.zip",
    )
    v17.add_argument("--output", default="artifacts/v17_capital_efficient_validation.json")
    v17.add_argument("--report", default="artifacts/v17_capital_efficient_report.html")
    v17.set_defaults(func=_v17_capital_efficient)
    v18 = sub.add_parser(
        "v18-equal-diversifier",
        help="執行先凍結、再下載 EFO/EET 日線的股債金外部驗證",
    )
    v18.add_argument(
        "--protocol",
        default="docs/V18_EQUAL_DIVERSIFIER_CAPITAL_EFFICIENCY_PROTOCOL.md",
    )
    v18.add_argument("--protocol-receipt", default="artifacts/v18_protocol_receipt.json")
    v18.add_argument("--data-receipt", default="artifacts/v18_data_receipt.json")
    v18.add_argument(
        "--validation-snapshot",
        default="artifacts/snapshot_v18_equal_diversifier_20080602_20260731_dd920b90.zip",
    )
    v18.add_argument("--output", default="artifacts/v18_equal_diversifier_validation.json")
    v18.add_argument("--report", default="artifacts/v18_equal_diversifier_report.html")
    v18.set_defaults(func=_v18_equal_diversifier)
    v20 = sub.add_parser(
        "v20-diversifier-strength",
        help="執行先凍結、再下載三組區域 ETF 日線的分散器輪替驗證",
    )
    v20.add_argument(
        "--protocol",
        default="docs/V20_DIVERSIFIER_RELATIVE_STRENGTH_PROTOCOL.md",
    )
    v20.add_argument("--protocol-receipt", default="artifacts/v20_protocol_receipt.json")
    v20.add_argument("--data-receipt", default="artifacts/v20_data_receipt.json")
    v20.add_argument(
        "--product-mapping-receipt",
        default="artifacts/v20_product_mapping_receipt.json",
    )
    v20.add_argument(
        "--capital-snapshot",
        default="artifacts/snapshot_v17_capital_efficient_20040102_20260731_4c948bf6.zip",
    )
    v20.add_argument("--main-snapshot", default="artifacts/snapshot_20260731_6a7ca6b8.zip")
    v20.add_argument(
        "--v18-snapshot",
        default="artifacts/snapshot_v18_equal_diversifier_20080602_20260731_dd920b90.zip",
    )
    v20.add_argument(
        "--external-snapshot",
        default="artifacts/snapshot_v20_diversifier_strength_20060803_20260731_e30b4032.zip",
    )
    v20.add_argument("--output", default="artifacts/v20_diversifier_strength_validation.json")
    v20.add_argument("--report", default="artifacts/v20_diversifier_strength_report.html")
    v20.set_defaults(func=_v20_diversifier_strength)
    v21 = sub.add_parser(
        "v21-hybrid-core",
        help="執行先凍結、再下載中小型股 3 倍 ETF 日線的常駐核心驗證",
    )
    v21.add_argument(
        "--protocol",
        default="docs/V21_HYBRID_LEVERAGE_CORE_PROTOCOL.md",
    )
    v21.add_argument("--product-mapping", default="docs/V21_PRODUCT_MAPPING.md")
    v21.add_argument("--protocol-receipt", default="artifacts/v21_protocol_receipt.json")
    v21.add_argument("--data-receipt", default="artifacts/v21_data_receipt.json")
    v21.add_argument(
        "--product-mapping-receipt",
        default="artifacts/v21_product_mapping_receipt.json",
    )
    v21.add_argument(
        "--capital-snapshot",
        default="artifacts/snapshot_v17_capital_efficient_20040102_20260731_4c948bf6.zip",
    )
    v21.add_argument(
        "--three-x-snapshot",
        default="artifacts/snapshot_v15_3x_20080102_20260731_57527472_validated.zip",
    )
    v21.add_argument(
        "--external-snapshot",
        default="artifacts/snapshot_v21_hybrid_core_20080102_20260731_45f452a2.zip",
    )
    v21.add_argument(
        "--output",
        default="artifacts/v21_hybrid_leverage_core_validation.json",
    )
    v21.add_argument(
        "--report",
        default="artifacts/v21_hybrid_leverage_core_report.html",
    )
    v21.set_defaults(func=_v21_hybrid_leverage_core)
    v22 = sub.add_parser(
        "v22-sector-capital-efficiency",
        help="執行先凍結、再下載九組美國產業實際 2 倍 ETF 的股債金驗證",
    )
    v22.add_argument(
        "--protocol",
        default="docs/V22_US_SECTOR_CAPITAL_EFFICIENCY_PROTOCOL.md",
    )
    v22.add_argument("--product-mapping", default="docs/V22_PRODUCT_MAPPING.md")
    v22.add_argument("--design-source", default="docs/V18_DESIGN_EXPLORATION.md")
    v22.add_argument("--protocol-receipt", default="artifacts/v22_protocol_receipt.json")
    v22.add_argument(
        "--product-mapping-receipt",
        default="artifacts/v22_product_mapping_receipt.json",
    )
    v22.add_argument("--data-receipt", default="artifacts/v22_data_receipt.json")
    v22.add_argument(
        "--design-source-receipt",
        default="artifacts/v22_design_source_receipt.json",
    )
    v22.add_argument(
        "--validation-snapshot",
        default=("artifacts/snapshot_v22_us_sectors_20030102_20190621_52450c12_validated.zip"),
    )
    v22.add_argument(
        "--output",
        default="artifacts/v22_us_sector_capital_efficiency_validation.json",
    )
    v22.add_argument(
        "--report",
        default="artifacts/v22_us_sector_capital_efficiency_report.html",
    )
    v22.set_defaults(func=_v22_sector_capital_efficiency)
    v23 = sub.add_parser(
        "v23-managed-futures-capital-efficiency",
        help="執行先凍結的 20 年 S&P 500＋管理期貨與兩個實際產品驗證",
    )
    v23.add_argument(
        "--protocol",
        default="docs/V23_MANAGED_FUTURES_CAPITAL_EFFICIENCY_PROTOCOL.md",
    )
    v23.add_argument("--product-mapping", default="docs/V23_PRODUCT_MAPPING.md")
    v23.add_argument("--protocol-receipt", default="artifacts/v23_protocol_receipt.json")
    v23.add_argument("--data-receipt", default="artifacts/v23_data_receipt.json")
    v23.add_argument(
        "--design-snapshot",
        default="artifacts/snapshot_v17_capital_efficient_20040102_20260731_4c948bf6.zip",
    )
    v23.add_argument(
        "--kmlm-snapshot",
        default="artifacts/snapshot_v23_kmlm_20201201_20260731_a7826ecd.zip",
    )
    v23.add_argument(
        "--fmf-snapshot",
        default="artifacts/snapshot_v23_fmf_20130801_20260731_42ecc0b8.zip",
    )
    v23.add_argument(
        "--kfa-pdf",
        default="artifacts/v23_kfa_mlm_index_presentation_20260630.pdf",
    )
    v23.add_argument(
        "--kfa-monthly-csv",
        default="artifacts/v23_kfa_mlm_index_monthly_198801_202606.csv",
    )
    v23.add_argument(
        "--output",
        default="artifacts/v23_managed_futures_capital_efficiency_validation.json",
    )
    v23.add_argument(
        "--report",
        default="artifacts/v23_managed_futures_capital_efficiency_report.html",
    )
    v23.set_defaults(func=_v23_managed_futures_capital_efficiency)
    v24 = sub.add_parser(
        "v24-quality-momentum-factor",
        help="執行先凍結的 20 年品質＋動量學術代理與兩組實際 ETF 驗證",
    )
    v24.add_argument(
        "--protocol",
        default="docs/V24_QUALITY_MOMENTUM_FACTOR_PROTOCOL.md",
    )
    v24.add_argument("--product-mapping", default="docs/V24_PRODUCT_MAPPING.md")
    v24.add_argument("--protocol-receipt", default="artifacts/v24_protocol_receipt.json")
    v24.add_argument("--data-receipt", default="artifacts/v24_data_receipt.json")
    v24.add_argument(
        "--ishares-snapshot",
        default=("artifacts/snapshot_v24_ishares_quality_momentum_20130701_20260731_11fc153f.zip"),
    )
    v24.add_argument(
        "--invesco-snapshot",
        default=("artifacts/snapshot_v24_invesco_quality_momentum_20070301_20260731_39817fb7.zip"),
    )
    v24.add_argument(
        "--french-market",
        default="artifacts/v24_french_ff3_monthly.zip",
    )
    v24.add_argument(
        "--french-quality",
        default="artifacts/v24_french_6_me_op_monthly.zip",
    )
    v24.add_argument(
        "--french-momentum",
        default="artifacts/v24_french_6_me_prior_12_2_monthly.zip",
    )
    v24.add_argument(
        "--output",
        default="artifacts/v24_quality_momentum_factor_validation.json",
    )
    v24.add_argument(
        "--report",
        default="artifacts/v24_quality_momentum_factor_report.html",
    )
    v24.set_defaults(func=_v24_quality_momentum_factor)
    v25 = sub.add_parser(
        "v25-growth-gold-diversification",
        help="執行先凍結的三條 20 年大型成長＋黃金實際 ETF 驗證",
    )
    v25.add_argument(
        "--protocol",
        default="docs/V25_GROWTH_GOLD_DIVERSIFICATION_PROTOCOL.md",
    )
    v25.add_argument("--product-mapping", default="docs/V25_PRODUCT_MAPPING.md")
    v25.add_argument("--protocol-receipt", default="artifacts/v25_protocol_receipt.json")
    v25.add_argument("--data-receipt", default="artifacts/v25_data_receipt.json")
    v25.add_argument(
        "--vanguard-snapshot",
        default="artifacts/snapshot_v25_vanguard_20060701_20260731_6cf44e63.zip",
    )
    v25.add_argument(
        "--ishares-snapshot",
        default="artifacts/snapshot_v25_ishares_20060701_20260731_88dc9a27.zip",
    )
    v25.add_argument(
        "--state-street-snapshot",
        default="artifacts/snapshot_v25_state_street_20060701_20260731_7a32250e.zip",
    )
    v25.add_argument(
        "--output",
        default="artifacts/v25_growth_gold_diversification_validation.json",
    )
    v25.add_argument(
        "--report",
        default="artifacts/v25_growth_gold_diversification_report.html",
    )
    v25.set_defaults(func=_v25_growth_gold_diversification)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "command", None):
        args = parser.parse_args(["build", *(argv or [])])
    try:
        return int(args.func(args))
    except KeyboardInterrupt:
        return 130
    except Exception as exc:
        print(f"錯誤：{exc}", file=sys.stderr)
        return 2
