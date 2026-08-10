from __future__ import annotations

import json
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from usfddk.data import market_data_freshness_schedule
from usfddk.growth_gold_diversification import (
    v25_forward_paper_evidence,
    v25_paper_fill_counts,
)
from usfddk.models import MarketPanel
from usfddk.paper import PASSIVE_BENCHMARK_KEY, forward_paper_evidence, paper_metrics
from usfddk.reference import evaluate_trade_readiness


def _clean_metric_set(metrics: dict[str, Any]) -> dict[str, float]:
    return {
        key: float(metrics[key])
        for key in ("cagr", "sharpe", "max_drawdown", "volatility", "turnover")
    }


_HK_FINANCE_REPLACEMENTS = (
    ("買進並持有", "買入並持有"),
    ("買進持有", "買入並持有"),
    ("總報酬", "總回報"),
    ("超額報酬", "超額回報"),
    ("主動報酬", "主動回報"),
    ("最大回撤", "最大跌幅"),
    ("波動率", "波幅"),
    ("行情快照", "市場快照"),
    ("極端行情", "極端市況"),
    ("總權益曝險", "總股票持倉比率"),
    ("三帳戶", "三個模擬組合"),
    ("Paper 帳戶", "Paper 模擬組合"),
    ("報酬", "回報"),
    ("績效", "表現"),
    ("回撤", "最大跌幅"),
    ("年化", "年率化"),
    ("波動", "波幅"),
    ("買進", "買入"),
    ("賣出", "沽出"),
    ("下單", "落盤"),
    ("資料", "數據"),
    ("新手", "初學投資者"),
    ("部位", "持倉"),
    ("曝險", "持倉比率"),
    ("再平衡", "重新平衡"),
    ("帳戶", "模擬組合"),
    ("標的", "相關資產"),
    ("收盤", "收市"),
    ("開盤", "開市"),
    ("盤中", "即市"),
    ("停損", "止蝕"),
    ("損益", "盈虧"),
    ("獲利", "盈利"),
    ("券商", "證券商"),
    ("行情", "市場數據"),
    ("調整後", "經調整"),
    ("滿倉", "全數持股"),
)


def _localize_hk_finance_copy(value: Any) -> Any:
    """Localize display strings without renaming machine-contract keys."""
    if isinstance(value, dict):
        return {key: _localize_hk_finance_copy(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_localize_hk_finance_copy(item) for item in value]
    if not isinstance(value, str):
        return value
    localized = value.replace("證券商", "\u0000BROKER\u0000")
    for source, target in _HK_FINANCE_REPLACEMENTS:
        localized = localized.replace(source, target)
    return localized.replace("\u0000BROKER\u0000", "證券商")


def _preserve_idempotent_generation_time(
    payload: dict[str, Any], paths: Iterable[str | Path]
) -> dict[str, Any]:
    """Keep byte-stable output when only the wall-clock generation time changed."""
    candidate = dict(payload)
    comparable = {key: value for key, value in candidate.items() if key != "generated_at_utc"}
    for raw in paths:
        path = Path(raw)
        if not path.exists():
            continue
        try:
            existing = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        existing_comparable = {
            key: value for key, value in existing.items() if key != "generated_at_utc"
        }
        if existing_comparable == comparable and isinstance(existing.get("generated_at_utc"), str):
            candidate["generated_at_utc"] = existing["generated_at_utc"]
            break
    return candidate


_PUBLIC_ACCOUNT_INTEGRITY_GATES = (
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


def _public_all_true(values: Any) -> bool:
    return isinstance(values, dict) and bool(values) and all(value is True for value in values.values())


def _public_percent(value: Any, digits: int = 1) -> str:
    return f"{float(value):.{digits}%}"


def _public_money(value: Any) -> str:
    return f"US${float(value):,.0f}"


def _public_allocation(weights: dict[str, Any]) -> tuple[str, str] | None:
    clean = {
        str(ticker): float(weight)
        for ticker, weight in weights.items()
        if isinstance(ticker, str) and float(weight) > 0.0
    }
    if not clean:
        return None
    ordered = sorted(clean.items(), key=lambda item: (-item[1], item[0]))
    allocation = "／".join(f"{ticker} {weight:.0%}" for ticker, weight in ordered)
    rounded_weights = [float(f"{weight:.0%}".rstrip("%")) / 100.0 for _, weight in ordered]
    amount_example = "／".join(
        _public_money(1_000.0 * weight) for weight in rounded_weights
    )
    return allocation, amount_example


def _public_long_term_strategy(payload: dict[str, Any]) -> dict[str, Any] | None:
    """Return only a fully promoted long-term strategy view model.

    The full research payload remains an audit/log input.  This function deliberately
    copies a small allow-list and never copies failed gates, limitations, or Paper
    diagnostics into the public decision contract.
    """
    readiness = payload.get("readiness")
    pipeline = payload.get("research_pipeline")
    if not isinstance(readiness, dict) or not isinstance(pipeline, dict):
        return None
    gates = readiness.get("gates")
    required = readiness.get("required_gate_count")
    passed = readiness.get("passed_gate_count")
    root_ready = (
        isinstance(required, int)
        and isinstance(passed, int)
        and required == 11
        and passed == required
        and isinstance(gates, dict)
        and len(gates) == required
        and _public_all_true(gates)
        and readiness.get("trade_ready") is True
        and readiness.get("allocation_visible") is True
        and readiness.get("selected_strategy_key") == "growth_gold_diversification"
    )
    latest = pipeline.get("growth_gold_diversification")
    if not isinstance(latest, dict):
        return None
    paper = latest.get("paper")
    forward = paper.get("forward_evidence") if isinstance(paper, dict) else None
    data_through = payload.get("data_through")
    integrity_ready = (
        isinstance(paper, dict)
        and isinstance(forward, dict)
        and forward.get("as_of") == data_through
        and forward.get("integrity_violations") == 0
        and isinstance(forward.get("gates"), dict)
        and all(forward["gates"].get(name) is True for name in _PUBLIC_ACCOUNT_INTEGRITY_GATES)
    )
    if not (
        root_ready
        and latest.get("trade_ready") is True
        and latest.get("real_money_signal_display_allowed") is True
        and forward.get("live_confirmed") is True
        and integrity_ready
    ):
        return None

    pooled = latest.get("pooled")
    if not isinstance(pooled, dict):
        return None
    strategy_metrics = pooled.get("strategy_metrics")
    spy_metrics = pooled.get("spy_metrics")
    if not isinstance(strategy_metrics, dict) or not isinstance(spy_metrics, dict):
        return None
    weights: dict[str, Any] = {}
    pending = paper.get("pending_order")
    if isinstance(pending, dict) and isinstance(pending.get("target_weights"), dict):
        weights = pending["target_weights"]
    elif isinstance(paper.get("holdings"), dict):
        weights = {
            ticker: position.get("weight")
            for ticker, position in paper["holdings"].items()
            if isinstance(position, dict) and "weight" in position
        }
    allocation = _public_allocation(weights)
    if allocation is None:
        return None
    forward_sessions = int(forward.get("forward_sessions", 0))
    filled_rebalances = int(forward.get("filled_rebalances", 0))
    action = (
        "下一個完成交易日按已凍結指令調整持倉"
        if pending
        else "今天不下單；維持現有持倉，等待下一個月末檢查"
    )
    return {
        "verified": True,
        "key": "long-term",
        "horizon": "長線穩定",
        "name": str(latest.get("name", "已驗證長線策略")),
        "description": "固定規則、每月檢查；只在歷史、成本、風險及前瞻門檻全部通過後公開。",
        "action": action,
        "allocation": allocation[0],
        "amount_example": allocation[1],
        "metrics": [
            {
                "label": "20 年年率化回報",
                "value": _public_percent(strategy_metrics.get("cagr", 0.0), 2),
                "comparison": f"SPY {_public_percent(spy_metrics.get('cagr', 0.0), 2)}",
            },
            {
                "label": "最大跌幅",
                "value": _public_percent(strategy_metrics.get("max_drawdown", 0.0), 1),
                "comparison": f"SPY {_public_percent(spy_metrics.get('max_drawdown', 0.0), 1)}",
            },
            {
                "label": "前瞻交易日",
                "value": str(forward_sessions),
                "comparison": f"{filled_rebalances} 次完成換倉",
            },
        ],
    }


def _public_short_term_strategy(
    formal_readiness: dict[str, Any] | None,
    overlay: dict[str, Any] | None,
) -> dict[str, Any] | None:
    if not isinstance(formal_readiness, dict) or not isinstance(overlay, dict):
        return None
    actual = formal_readiness.get("actual_formal_readiness")
    summary = overlay.get("gate_summary")
    decision = overlay.get("decision")
    if not isinstance(actual, dict) or not isinstance(summary, dict) or not isinstance(decision, dict):
        return None
    total = actual.get("total")
    passed = actual.get("passed")
    summary_total = summary.get("total")
    summary_passed = summary.get("passed")
    symbols = decision.get("public_symbols")
    action = decision.get("public_action")
    if not (
        actual.get("all_passed") is True
        and isinstance(total, int)
        and isinstance(passed, int)
        and passed == total
        and summary.get("all_passed") is True
        and isinstance(summary_total, int)
        and isinstance(summary_passed, int)
        and summary_passed == summary_total
        and decision.get("trade_ready") is True
        and decision.get("can_promote_from_this_round") is True
        and decision.get("new_strategy_created") is True
        and int(decision.get("formal_strategy_runs", 0)) > 0
        and isinstance(action, str)
        and action.strip()
        and isinstance(symbols, list)
        and symbols
        and all(isinstance(symbol, str) and symbol.strip() for symbol in symbols)
    ):
        return None
    return {
        "verified": True,
        "key": "short-term",
        "horizon": "短線高回報",
        "name": "已驗證個股策略",
        "description": "正式個股策略已通過凍結資料、成本、統計、壓力及前瞻門檻。",
        "action": action.strip(),
        "allocation": "／".join(symbols),
        "metrics": [
            {
                "label": "正式就緒",
                "value": f"{passed}/{total}",
                "comparison": "全部事前門檻通過",
            },
            {
                "label": "策略運行",
                "value": str(int(decision["formal_strategy_runs"])),
                "comparison": "正式、不可回填",
            },
        ],
    }


def build_public_decision_payload(
    payload: dict[str, Any],
    *,
    formal_readiness: dict[str, Any] | None = None,
    short_term_overlay: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the success-only, beginner-facing website contract.

    Research results that are not promoted remain in the source payload and logs;
    this allow-list is the only data imported by the public decision page.
    """
    strategies = []
    long_term = _public_long_term_strategy(payload)
    if long_term is not None:
        strategies.append(long_term)
    short_term = _public_short_term_strategy(formal_readiness, short_term_overlay)
    if short_term is not None:
        strategies.append(short_term)
    data_through = str(payload.get("data_through", ""))
    freshness = payload.get("freshness")
    freshness = freshness if isinstance(freshness, dict) else {}
    today_action = (
        "今天不下單"
        if not strategies or all(strategy["action"].startswith("今天不下單") for strategy in strategies)
        else "按已驗證策略執行"
    )
    return {
        "schema_version": 1,
        "generated_at_utc": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "data_through": data_through,
        "next_expected_session": str(freshness.get("next_expected_session", "")),
        "refresh_due_at_utc": str(freshness.get("refresh_due_at_utc", "")),
        "surface": "verified-strategy" if strategies else "hold-cash",
        "today_action": today_action,
        "lead": (
            "以下只列出已完整通過驗證、並有明確執行規則的策略。"
            if strategies
            else "目前沒有可公開的已驗證策略；今日維持現金，等待下一個檢查日。"
        ),
        "action_detail": (
            "；".join(strategy["action"] for strategy in strategies)
            if strategies
            else "不建立新倉，保留現金並等待下一個完成交易日的正式驗證。"
        ),
        "strategies": strategies,
        "policy": "首頁只顯示已驗證、可執行的策略；完整研究記錄與機器收據另存於 GitHub。",
        "disclaimer": "研究與教育用途，不構成投資建議；不保證未來跑贏 SPY 或任何 ETF。",
    }


def _clean_v25_forward_account(state: dict[str, Any]) -> dict[str, Any]:
    summary = paper_metrics(state)
    return {
        "as_of": state["as_of"],
        "equity": float(summary["equity"]),
        "return": float(summary["return"]),
        "max_drawdown": float(summary["max_drawdown"]),
        "cash": float(state["cash"]),
        "total_costs": float(state.get("total_costs", 0.0)),
        "transactions": len(state.get("transactions", [])),
        "filled_rebalances": v25_paper_fill_counts(state)["completed_rebalances"],
        "equity_curve": [
            {
                "date": str(item["date"]),
                "equity": float(item["equity"]),
                "drawdown": float(item["drawdown"]),
            }
            for item in state.get("equity_curve", [])
        ],
    }


def build_v25_paper_bundle(
    candidate_state: dict[str, Any],
    spy_state: dict[str, Any],
    matched_state: dict[str, Any],
) -> dict[str, Any]:
    """Build the single v25 website contract used by full and daily exports."""
    forward = v25_forward_paper_evidence(candidate_state, spy_state, matched_state)
    paper_summary = paper_metrics(candidate_state)
    paper_holdings = {
        ticker: {
            "market_value": float(position["market_value"]),
            "weight": float(position["market_value"]) / float(paper_summary["equity"]),
        }
        for ticker, position in candidate_state.get("holdings", {}).items()
    }
    pending_order = candidate_state.get("pending_order")
    return {
        "mode": candidate_state["mode"],
        "as_of": candidate_state["as_of"],
        "started_at": candidate_state.get("started_at"),
        "snapshot_sha256": candidate_state.get("snapshot_sha256"),
        "initial_cash": float(candidate_state["initial_cash"]),
        "cost_bps": float(candidate_state["cost_bps"]),
        "total_costs": float(candidate_state.get("total_costs", 0.0)),
        "execution_clock": candidate_state.get("execution_clock"),
        "equity": float(paper_summary["equity"]),
        "return": float(paper_summary["return"]),
        "cash": float(candidate_state["cash"]),
        "transactions": len(candidate_state.get("transactions", [])),
        "status": (
            "awaiting_fill" if pending_order else "invested" if paper_holdings else "cash"
        ),
        "holdings": paper_holdings,
        "pending_order": pending_order,
        "recent_transactions": candidate_state.get("transactions", [])[-20:],
        "recent_filled_orders": candidate_state.get("order_history", [])[-12:],
        "accounts": {
            "candidate": _clean_v25_forward_account(candidate_state),
            "SPY": _clean_v25_forward_account(spy_state),
            "matched_80_VUG_20_SHY": _clean_v25_forward_account(matched_state),
        },
        "forward_evidence": forward,
    }


def refresh_v25_site_data(
    destinations: str | Path | Iterable[str | Path],
    *,
    template: str | Path,
    candidate_state: dict[str, Any],
    spy_state: dict[str, Any],
    matched_state: dict[str, Any],
) -> list[Path]:
    """Advance only the pre-registered v25 LIVE section of a frozen research site."""
    paths = [destinations] if isinstance(destinations, (str, Path)) else list(destinations)
    template_path = Path(template)
    payload = json.loads(template_path.read_text(encoding="utf-8"))
    try:
        v25 = payload["research_pipeline"]["growth_gold_diversification"]
    except (KeyError, TypeError) as exc:
        raise ValueError("網站範本缺少凍結的 v25 研究結果") from exc
    if not bool(v25.get("paper_eligible")) or not bool(v25.get("all_paths_passed")):
        raise ValueError("凍結的 v25 歷史入口未通過，不得建立 LIVE Paper 網站數據")

    paper_bundle = build_v25_paper_bundle(candidate_state, spy_state, matched_state)
    forward_trade_ready = bool(paper_bundle["forward_evidence"]["live_confirmed"])
    v25["paper"] = paper_bundle
    v25["paper_signal_display_allowed"] = True
    v25["trade_ready"] = forward_trade_ready
    v25["real_money_signal_display_allowed"] = forward_trade_ready

    payload.setdefault("research_snapshot_data_through", payload.get("data_through"))
    payload.setdefault("research_snapshot_sha256", payload.get("snapshot_sha256"))
    payload["data_through"] = str(candidate_state["as_of"])
    payload["live_snapshot_sha256"] = str(candidate_state.get("snapshot_sha256", ""))
    payload["freshness"] = market_data_freshness_schedule(candidate_state["as_of"])
    payload["generated_at_utc"] = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    payload = _localize_hk_finance_copy(payload)
    payload = _preserve_idempotent_generation_time(payload, [template_path, *paths])

    written: list[Path] = []
    for raw in paths:
        path = Path(raw)
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_name(f".{path.name}.tmp")
        temporary.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False),
            encoding="utf-8",
        )
        temporary.replace(path)
        written.append(path)
    return written


def write_site_data(
    destinations: str | Path | Iterable[str | Path],
    *,
    panel: MarketPanel,
    manifest: dict[str, Any],
    start: str,
    reference_audit: dict[str, Any],
    challenger_audit: dict[str, Any] | None = None,
    challenger_paper_state: dict[str, Any] | None = None,
    paper_state: dict[str, Any],
    paper_benchmark_states: dict[str, dict[str, Any]],
    cross_market_audit: dict[str, Any] | None = None,
    style_rotation_audit: dict[str, Any] | None = None,
    three_clock_audit: dict[str, Any] | None = None,
    industry_tilt_audit: dict[str, Any] | None = None,
    relative_growth_audit: dict[str, Any] | None = None,
    always_invested_audit: dict[str, Any] | None = None,
    low_turnover_audit: dict[str, Any] | None = None,
    hierarchical_defense_audit: dict[str, Any] | None = None,
    confirmed_relative_growth_audit: dict[str, Any] | None = None,
    modest_leverage_audit: dict[str, Any] | None = None,
    modest_leverage_overlay_audit: dict[str, Any] | None = None,
    trend_volatility_brake_audit: dict[str, Any] | None = None,
    capital_efficient_audit: dict[str, Any] | None = None,
    equal_diversifier_audit: dict[str, Any] | None = None,
    diversifier_strength_audit: dict[str, Any] | None = None,
    hybrid_leverage_core_audit: dict[str, Any] | None = None,
    sector_capital_efficiency_audit: dict[str, Any] | None = None,
    managed_futures_capital_efficiency_audit: dict[str, Any] | None = None,
    quality_momentum_factor_audit: dict[str, Any] | None = None,
    growth_gold_diversification_audit: dict[str, Any] | None = None,
    growth_gold_paper_state: dict[str, Any] | None = None,
    growth_gold_spy_paper_state: dict[str, Any] | None = None,
    growth_gold_matched_paper_state: dict[str, Any] | None = None,
) -> list[Path]:
    """Write the small, curated data contract consumed by the beginner website."""
    paths = [destinations] if isinstance(destinations, (str, Path)) else list(destinations)
    rolling = reference_audit["rolling_five_year"]["summary"]
    fixed = reference_audit["fixed_policy_2012"]
    nw = reference_audit["active_return_newey_west"]
    dsr = reference_audit["active_deflated_sharpe"]
    exposure_rolling = reference_audit["rolling_five_year_vs_passive_90_10"]["summary"]
    exposure_nw = reference_audit["exposure_control_newey_west"]
    paper = paper_metrics(paper_state)
    forward = forward_paper_evidence(paper_state, paper_benchmark_states)
    pending = paper_state.get("pending_order")
    holdings = {
        ticker: {
            "market_value": float(position["market_value"]),
            "weight": float(position["market_value"]) / float(paper["equity"]),
        }
        for ticker, position in paper_state.get("holdings", {}).items()
    }
    paper_status = "awaiting_fill" if pending else "invested" if holdings else "cash"
    target = reference_audit["current_target"]
    freshness = market_data_freshness_schedule(panel.end)
    payload = {
        "schema_version": 1,
        "generated_at_utc": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "data_through": panel.end.strftime("%Y-%m-%d"),
        "freshness": freshness,
        "research_start": start,
        "snapshot_sha256": str(manifest.get("archive_sha256", "")),
        "strategy": {
            "name": reference_audit["strategy_name"],
            "version": int(reference_audit.get("strategy_version", 1)),
            "status": reference_audit["status"],
            "execution_clock": "月末收市產生訊號；下一個新增交易日用經調整開市價模擬成交",
            "parameters": reference_audit["frozen_parameters"],
            "current_target": target,
            "metrics": _clean_metric_set(reference_audit["strategy_metrics"]),
        },
        "benchmarks": {
            "SPY": _clean_metric_set(reference_audit["spy_metrics"]),
            "QQQ": _clean_metric_set(reference_audit["qqq_metrics"]),
            PASSIVE_BENCHMARK_KEY: _clean_metric_set(reference_audit["passive_90_10_metrics"]),
        },
        "evidence": {
            "historical_gate_passed": bool(reference_audit["historical_gate_passed"]),
            "exposure_control_passed": bool(reference_audit["exposure_control_passed"]),
            "reference_trade_candidate": bool(reference_audit["reference_trade_candidate"]),
            "statistically_confirmed": bool(reference_audit["statistically_confirmed"]),
            "live_confirmed": bool(forward["live_confirmed"]),
            "cagr_difference_vs_spy": float(reference_audit["cagr_difference_vs_spy"]),
            "drawdown_improvement_vs_spy": float(reference_audit["drawdown_improvement_vs_spy"]),
            "cagr_difference_vs_passive_90_10": float(
                reference_audit["cagr_difference_vs_passive_90_10"]
            ),
            "drawdown_improvement_vs_passive_90_10": float(
                reference_audit["drawdown_improvement_vs_passive_90_10"]
            ),
            "active_return_vs_passive_90_10": {
                "annualized_mean": float(exposure_nw["annualized"]),
                "newey_west_t": float(exposure_nw["t_stat"]),
            },
            "rolling_five_year_vs_passive_90_10": {
                "windows": int(exposure_rolling["windows"]),
                "win_fraction": float(exposure_rolling["cagr_win_fraction"]),
                "latest_cagr_difference": float(exposure_rolling["latest_cagr_difference"]),
                "worst_cagr_difference": float(exposure_rolling["worst_cagr_difference"]),
            },
            "second_ten_year_cagr_difference_vs_passive_90_10": float(
                reference_audit["ten_year_halves"]["second"]["cagr_difference_vs_passive_90_10"]
            ),
            "cost_25bps_cagr_difference_vs_passive_90_10": float(
                next(
                    row["cagr_difference_vs_passive_90_10"]
                    for row in reference_audit["cost_sensitivity"]
                    if row["cost_bps"] == 25.0
                )
            ),
            "newey_west_t": float(nw["t_stat"]),
            "deflated_sharpe_probability": float(dsr["probability"]),
            "rolling_five_year": {
                "windows": int(rolling["windows"]),
                "win_fraction_vs_spy": float(rolling["cagr_win_fraction"]),
                "median_cagr_difference_vs_spy": float(rolling["median_cagr_difference"]),
                "worst_cagr_difference_vs_spy": float(rolling["worst_cagr_difference"]),
                "latest_cagr_difference_vs_spy": float(rolling["latest_cagr_difference"]),
            },
            "fixed_post_2012": {
                "cagr": float(fixed["strategy_metrics"]["cagr"]),
                "spy_cagr": float(fixed["spy_metrics"]["cagr"]),
                "cagr_difference_vs_spy": float(fixed["cagr_difference_vs_spy"]),
                "newey_west_t": float(fixed["active_return_newey_west"]["t_stat"]),
                "caveat": fixed["caveat"],
            },
            "historical_gates": reference_audit["historical_gates"],
            "exposure_control_gates": reference_audit["exposure_control_gates"],
        },
        "paper": {
            "mode": paper_state["mode"],
            "as_of": paper_state["as_of"],
            "started_at": paper_state.get("started_at"),
            "equity": float(paper["equity"]),
            "return": float(paper["return"]),
            "cash": float(paper_state["cash"]),
            "forward_sessions": max(len(paper_state.get("equity_curve", [])) - 1, 0),
            "transactions": len(paper_state.get("transactions", [])),
            "filled_rebalances": int(forward["filled_rebalances"]),
            "adjustment_rebases": len(paper_state.get("adjustment_rebases", [])),
            "latest_adjustment_rebase": (
                {
                    key: paper_state["adjustment_rebases"][-1][key]
                    for key in ("as_of", "ticker", "unit_factor", "reason")
                }
                if paper_state.get("adjustment_rebases")
                else None
            ),
            "status": paper_status,
            "holdings": holdings,
            "pending_order": pending,
            "forward_evidence": forward,
        },
        "beginner": {
            "action": (
                "只做 Paper：等待下一個新增交易日開市模擬成交"
                if pending
                else "照規則持有，等待下一次月末訊號"
                if holdings
                else "目前維持現金，等待有效訊號"
            ),
            "why": (
                "月末訊號已排隊；為避免偷看同一天開市價，只會在未來新增的交易日執行。"
                if pending
                else "目前沒有待成交委託；系統會在下一個完整月末重新計算配置。"
            ),
            "next_check": "市場快照新增交易日後，再執行 paper update 並核對成交明細。",
            "allocation_hint": (
                f"目前 QQQ 約 {float(target.get('QQQ', 0.0)):.0%}；"
                f"SHY 防守準備金約 {float(target.get('SHY', 0.0)):.0%}。"
            ),
        },
        "limitations": [
            "這是依凍結歷史數據選出的研究候選，不是獨立於搜尋之外的全新樣本。",
            "超額回報尚未達統計確認，LIVE Paper 也還沒有足夠前瞻交易紀錄。",
            "相對被動 90% QQQ／10% SHY，後十年、5 年滾動一致性與 25 bps 成本檢查未通過；目前只能視為收窄最大跌幅研究，不是已證實 alpha。",
            "QQQ 仍是主要風險來源；回測最深跌幅約三成六，未來可能更深。",
            "回測含設定的換手成本，但不含稅、買賣價差變動、市場衝擊與匯率。",
            "免費經調整市場數據可能被供應商回溯修訂；每次更新都要留下快照雜湊。",
            "Paper 持倉採總回報調整單位，不是證券商股數；除息、拆股或價格修訂時只重基準單位，不回寫既有盈虧。",
        ],
        "disclaimer": "研究與教育用途，不構成投資建議；不保證未來跑贏 SPY 或任何 ETF。",
    }
    if challenger_audit is not None:
        proxy = challenger_audit.get("proxy_validation", {})
        proxy_rolling = proxy.get("rolling_five_year", {}).get("summary", {})
        challenger_paper = (
            paper_metrics(challenger_paper_state) if challenger_paper_state is not None else None
        )
        challenger_holdings = (
            {
                ticker: {
                    "market_value": float(position["market_value"]),
                    "weight": float(position["market_value"]) / float(challenger_paper["equity"]),
                }
                for ticker, position in challenger_paper_state.get("holdings", {}).items()
            }
            if challenger_paper_state is not None and challenger_paper is not None
            else {}
        )
        payload["research_pipeline"] = {
            "primary_strategy": reference_audit["strategy_name"],
            "challengers": {
                "v3": {
                    "name": challenger_audit["strategy_name"],
                    "status": challenger_audit["status"],
                    "reference_trade_candidate": bool(
                        challenger_audit["reference_trade_candidate"]
                    ),
                    "historical_gate_passed": bool(challenger_audit["historical_gate_passed"]),
                    "matched_control_passed": bool(challenger_audit["exposure_control_passed"]),
                    "statistically_confirmed": bool(challenger_audit["statistically_confirmed"]),
                    "metrics": _clean_metric_set(challenger_audit["strategy_metrics"]),
                    "qqq_metrics": _clean_metric_set(challenger_audit["qqq_metrics"]),
                    "matched_96_4_metrics": _clean_metric_set(
                        challenger_audit["matched_96_4_metrics"]
                    ),
                    "current_target": challenger_audit["current_target"],
                    "cagr_difference_vs_qqq": float(challenger_audit["cagr_difference_vs_qqq"]),
                    "drawdown_improvement_vs_qqq": float(
                        challenger_audit["drawdown_improvement_vs_qqq"]
                    ),
                    "active_return_newey_west": {
                        "annualized": float(
                            challenger_audit["active_return_newey_west"]["annualized"]
                        ),
                        "t_stat": float(challenger_audit["active_return_newey_west"]["t_stat"]),
                    },
                    "deflated_sharpe_probability": float(
                        challenger_audit["active_deflated_sharpe"]["probability"]
                    ),
                    "paper": (
                        {
                            "mode": challenger_paper_state["mode"],
                            "as_of": challenger_paper_state["as_of"],
                            "started_at": challenger_paper_state.get("started_at"),
                            "equity": float(challenger_paper["equity"]),
                            "return": float(challenger_paper["return"]),
                            "cash": float(challenger_paper_state["cash"]),
                            "snapshot_sha256": str(
                                challenger_paper_state.get("snapshot_sha256", "")
                            ),
                            "forward_sessions": max(
                                len(challenger_paper_state.get("equity_curve", [])) - 1,
                                0,
                            ),
                            "transactions": len(challenger_paper_state.get("transactions", [])),
                            "pending_order": challenger_paper_state.get("pending_order"),
                            "holdings": challenger_holdings,
                        }
                        if challenger_paper_state is not None and challenger_paper is not None
                        else None
                    ),
                    "proxy_validation": {
                        "passed": bool(proxy.get("passed", False)),
                        "period": proxy.get("period", {}),
                        "strategy_metrics": (
                            _clean_metric_set(proxy["strategy_metrics"])
                            if proxy.get("strategy_metrics")
                            else None
                        ),
                        "benchmark_metrics": (
                            _clean_metric_set(proxy["benchmark_metrics"])
                            if proxy.get("benchmark_metrics")
                            else None
                        ),
                        "cagr_difference_vs_ndx": float(proxy.get("cagr_difference_vs_ndx", 0.0)),
                        "rolling_five_year_win_fraction": float(
                            proxy_rolling.get("cagr_win_fraction", 0.0)
                        ),
                        "rolling_five_year_noninferior_fraction": float(
                            proxy_rolling.get("cagr_noninferior_fraction", 0.0)
                        ),
                        "ten_year_cagr_differences": proxy.get("ten_year_cagr_differences", {}),
                        "gates": proxy.get("gates", {}),
                        "caveat": proxy.get("caveat", ""),
                    },
                }
            },
        }
    if cross_market_audit is not None:
        markets = cross_market_audit["markets"]
        payload.setdefault(
            "research_pipeline", {"primary_strategy": reference_audit["strategy_name"]}
        )["cross_market"] = {
            "status": cross_market_audit["status"],
            "passed": bool(cross_market_audit["cross_market_passed"]),
            "period": cross_market_audit["period"],
            "protocol_sha256": cross_market_audit["protocol"]["sha256"],
            "counts": cross_market_audit["counts"],
            "aggregate_gates": cross_market_audit["aggregate_gates"],
            "rolling_five_year_win_rate_median": float(
                cross_market_audit["rolling_five_year_win_rate_median"]
            ),
            "pooled_active_return": {
                "annualized": float(
                    cross_market_audit["pooled_active_return"]["newey_west"]["annualized"]
                ),
                "newey_west_t": float(
                    cross_market_audit["pooled_active_return"]["newey_west"]["t_stat"]
                ),
                "deflated_sharpe_probability": float(
                    cross_market_audit["pooled_active_return"]["deflated_sharpe"]["probability"]
                ),
            },
            "markets": {
                ticker: {
                    "market": item["market"],
                    "index": item["index"],
                    "strategy_cagr": float(item["strategy_metrics"]["cagr"]),
                    "benchmark_cagr": float(item["benchmark_metrics"]["cagr"]),
                    "cagr_difference": float(item["cagr_difference"]),
                    "sharpe_difference": float(item["sharpe_difference"]),
                    "drawdown_improvement": float(item["drawdown_improvement"]),
                    "cost_50bps_cagr_difference": float(item["cost_50bps"]["cagr_difference"]),
                    "rolling_five_year_win_fraction": float(
                        item["rolling_five_year"]["summary"]["cagr_win_fraction"]
                    ),
                    "first_half_cagr_difference": float(item["halves"]["first"]["cagr_difference"]),
                    "second_half_cagr_difference": float(
                        item["halves"]["second"]["cagr_difference"]
                    ),
                }
                for ticker, item in markets.items()
            },
        }
        if not cross_market_audit["cross_market_passed"]:
            payload["limitations"].insert(
                0,
                "v3 在下載前凍結的五市場測試僅 1/5 完整期勝出，跨市場機制未能泛化；不得用單一市場成功作為實金依據。",
            )
    if style_rotation_audit is not None:
        trade = style_rotation_audit["trade"]
        payload.setdefault(
            "research_pipeline", {"primary_strategy": reference_audit["strategy_name"]}
        )["style_rotation"] = {
            "status": style_rotation_audit["status"],
            "historical_gate_passed": bool(style_rotation_audit["historical_gate_passed"]),
            "paper_eligible": bool(style_rotation_audit["paper_eligible"]),
            "data_gate_passed": bool(style_rotation_audit["data_gate_passed"]),
            "passed_gate_count": int(style_rotation_audit["passed_gate_count"]),
            "required_gate_count": int(style_rotation_audit["required_gate_count"]),
            "protocol_sha256": style_rotation_audit["protocol"]["sha256"],
            "period": trade["period"],
            "strategy_metrics": _clean_metric_set(trade["strategy_metrics"]),
            "benchmark_metrics": {
                key: _clean_metric_set(metrics)
                for key, metrics in trade["benchmark_metrics"].items()
            },
            "comparisons": {
                key: {
                    "cagr_difference": float(item["cagr_difference"]),
                    "sharpe_difference": float(item["sharpe_difference"]),
                    "drawdown_improvement": float(item["drawdown_improvement"]),
                    "newey_west_t": float(item["active_return_newey_west"]["t_stat"]),
                    "deflated_sharpe_probability": float(
                        item["active_deflated_sharpe"]["probability"]
                    ),
                }
                for key, item in trade["comparisons"].items()
            },
            "cost_50bps": trade["cost_50bps"],
            "rolling_five_year": {
                key: {
                    "win_fraction": float(item["summary"]["cagr_win_fraction"]),
                    "median_cagr_difference": float(item["summary"]["median_cagr_difference"]),
                    "worst_cagr_difference": float(item["summary"]["worst_cagr_difference"]),
                }
                for key, item in trade["rolling_five_year"].items()
            },
            "fixed_halves": trade["fixed_halves"],
            "current_target": trade["current_target"],
            "gates": style_rotation_audit["gates"],
            "proxy": style_rotation_audit["proxy"],
        }
        if not style_rotation_audit["historical_gate_passed"]:
            payload["limitations"].insert(
                0,
                "v4 股權風格輪動雖改善 SPY 最大跌幅，但 14 道事前門檻只通過 2 道；CAGR、成本、後十年、滾動與統計均不足，且舊代理數據門檻失敗，因此不建立 Paper。",
            )
    if three_clock_audit is not None:
        main = three_clock_audit["main"]
        proxy = three_clock_audit["proxy"]
        cross = three_clock_audit["cross_market"]
        payload.setdefault(
            "research_pipeline", {"primary_strategy": reference_audit["strategy_name"]}
        )["three_clock"] = {
            "name": three_clock_audit["strategy_name"],
            "status": three_clock_audit["status"],
            "historical_gate_passed": bool(three_clock_audit["historical_gate_passed"]),
            "paper_eligible": bool(three_clock_audit["paper_eligible"]),
            "passed_gate_count": int(three_clock_audit["passed_gate_count"]),
            "required_gate_count": int(three_clock_audit["required_gate_count"]),
            "protocol_sha256": three_clock_audit["protocol"]["sha256"],
            "main": {
                "period": main["period"],
                "strategy_metrics": _clean_metric_set(main["strategy_metrics"]),
                "benchmark_metrics": {
                    key: _clean_metric_set(metrics)
                    for key, metrics in main["benchmark_metrics"].items()
                },
                "comparisons": {
                    key: {
                        "cagr_difference": float(item["cagr_difference"]),
                        "sharpe_difference": float(item["sharpe_difference"]),
                        "drawdown_improvement": float(item["drawdown_improvement"]),
                        "newey_west_t": float(item["active_return_newey_west"]["t_stat"]),
                        "deflated_sharpe_probability": float(
                            item["active_deflated_sharpe"]["probability"]
                        ),
                    }
                    for key, item in main["comparisons"].items()
                },
                "rolling_five_year": {
                    key: {
                        "win_fraction": float(item["summary"]["cagr_win_fraction"]),
                        "median_cagr_difference": float(item["summary"]["median_cagr_difference"]),
                        "worst_cagr_difference": float(item["summary"]["worst_cagr_difference"]),
                    }
                    for key, item in main["rolling_five_year"].items()
                },
                "cost_50bps": main["cost_50bps"],
                "current_target": main["current_target"],
            },
            "proxy": {
                "period": proxy["period"],
                "strategy_metrics": _clean_metric_set(proxy["strategy_metrics"]),
                "benchmark_metrics": {
                    key: _clean_metric_set(metrics)
                    for key, metrics in proxy["benchmark_metrics"].items()
                },
                "comparisons": {
                    key: {
                        "cagr_difference": float(item["cagr_difference"]),
                        "drawdown_improvement": float(item["drawdown_improvement"]),
                        "newey_west_t": float(item["active_return_newey_west"]["t_stat"]),
                    }
                    for key, item in proxy["comparisons"].items()
                },
                "rolling_five_year": {
                    key: {
                        "win_fraction": float(item["summary"]["cagr_win_fraction"]),
                        "median_cagr_difference": float(item["summary"]["median_cagr_difference"]),
                    }
                    for key, item in proxy["rolling_five_year"].items()
                },
            },
            "cross_market": {
                "counts": cross["counts"],
                "rolling_five_year_win_rate_medians": cross["rolling_five_year_win_rate_medians"],
                "pooled_active_return": {
                    key: {
                        "annualized": float(item["newey_west"]["annualized"]),
                        "newey_west_t": float(item["newey_west"]["t_stat"]),
                    }
                    for key, item in cross["pooled_active_return"].items()
                },
            },
            "gates": three_clock_audit["gates"],
        }
        if not three_clock_audit["historical_gate_passed"]:
            payload["limitations"].insert(
                0,
                "v5 三時鐘集成在近期 20 年幾乎追平 QQQ 且最大跌幅較小，但舊年代 5 年滾動勝率僅約 37%、五市場完整期僅 1/5 同勝兩基準，22 道門檻只過 10 道；研究配置不是交易訊號，不建立 Paper。",
            )
    if industry_tilt_audit is not None:
        main = industry_tilt_audit["main"]
        early = industry_tilt_audit["early_etf"]
        proxy = industry_tilt_audit["proxy"]
        payload.setdefault(
            "research_pipeline", {"primary_strategy": reference_audit["strategy_name"]}
        )["industry_tilt"] = {
            "name": industry_tilt_audit["strategy_name"],
            "status": industry_tilt_audit["status"],
            "historical_gate_passed": bool(industry_tilt_audit["historical_gate_passed"]),
            "paper_eligible": bool(industry_tilt_audit["paper_eligible"]),
            "passed_gate_count": int(industry_tilt_audit["passed_gate_count"]),
            "required_gate_count": int(industry_tilt_audit["required_gate_count"]),
            "protocol_sha256": industry_tilt_audit["protocol"]["sha256"],
            "main": {
                "period": main["period"],
                "strategy_metrics": _clean_metric_set(main["strategy_metrics"]),
                "benchmark_metrics": {
                    key: _clean_metric_set(metrics)
                    for key, metrics in main["benchmark_metrics"].items()
                },
                "comparisons": {
                    key: {
                        "cagr_difference": float(item["cagr_difference"]),
                        "sharpe_difference": float(item["sharpe_difference"]),
                        "drawdown_improvement": float(item["drawdown_improvement"]),
                        "newey_west_t": float(item["active_return_newey_west"]["t_stat"]),
                        "deflated_sharpe_probability": float(
                            item["active_deflated_sharpe"]["probability"]
                        ),
                    }
                    for key, item in main["comparisons"].items()
                },
                "rolling_five_year": {
                    key: {
                        "win_fraction": float(item["summary"]["cagr_win_fraction"]),
                        "median_cagr_difference": float(item["summary"]["median_cagr_difference"]),
                    }
                    for key, item in main["rolling_five_year"].items()
                },
                "current_target": main["current_target"],
            },
            "early_etf": {
                "period": early["period"],
                "strategy_metrics": _clean_metric_set(early["strategy_metrics"]),
                "benchmark_metrics": {
                    key: _clean_metric_set(metrics)
                    for key, metrics in early["benchmark_metrics"].items()
                },
            },
            "proxy": {
                "period": proxy["period"],
                "strategy_metrics": _clean_metric_set(proxy["strategy_metrics"]),
                "benchmark_metrics": {
                    key: _clean_metric_set(metrics)
                    for key, metrics in proxy["benchmark_metrics"].items()
                },
                "comparisons": {
                    key: {
                        "cagr_difference": float(item["cagr_difference"]),
                        "drawdown_improvement": float(item["drawdown_improvement"]),
                        "newey_west_t": float(item["active_return_newey_west"]["t_stat"]),
                        "deflated_sharpe_probability": float(
                            item["active_deflated_sharpe"]["probability"]
                        ),
                    }
                    for key, item in proxy["comparisons"].items()
                },
                "decade_wins": int(proxy["decade_wins"]),
            },
            "gates": industry_tilt_audit["gates"],
        }
        if not industry_tilt_audit["historical_gate_passed"]:
            payload["limitations"].insert(
                0,
                "v6 產業動能在 1927–2005 代理期有效，但 2006–2026 可交易 ETF 主期 CAGR 10.00%，低於 SPY 11.27% 與相同持倉比率對照 10.20%；22 道只過 11 道，研究配置不可照單、不建立 Paper。",
            )
    if relative_growth_audit is not None:
        main = relative_growth_audit["main"]
        proxy = relative_growth_audit["proxy"]
        payload.setdefault(
            "research_pipeline", {"primary_strategy": reference_audit["strategy_name"]}
        )["relative_growth"] = {
            "name": relative_growth_audit["strategy_name"],
            "status": relative_growth_audit["status"],
            "historical_gate_passed": bool(relative_growth_audit["historical_gate_passed"]),
            "paper_eligible": bool(relative_growth_audit["paper_eligible"]),
            "passed_gate_count": int(relative_growth_audit["passed_gate_count"]),
            "required_gate_count": int(relative_growth_audit["required_gate_count"]),
            "protocol_sha256": relative_growth_audit["protocol"]["sha256"],
            "main": {
                "period": main["period"],
                "strategy_metrics": _clean_metric_set(main["strategy_metrics"]),
                "benchmark_metrics": {
                    key: _clean_metric_set(metrics)
                    for key, metrics in main["benchmark_metrics"].items()
                },
                "comparisons": {
                    key: {
                        "cagr_difference": float(item["cagr_difference"]),
                        "sharpe_difference": float(item["sharpe_difference"]),
                        "drawdown_improvement": float(item["drawdown_improvement"]),
                        "newey_west_t": float(item["active_return_newey_west"]["t_stat"]),
                        "probabilistic_sharpe_probability": float(
                            item["active_probabilistic_sharpe"]["probability"]
                        ),
                        "global_deflated_sharpe_probability": float(
                            item["active_global_deflated_sharpe_disclosure"]["probability"]
                        ),
                    }
                    for key, item in main["comparisons"].items()
                },
                "rolling_five_year": {
                    key: {
                        "win_fraction": float(item["summary"]["cagr_win_fraction"]),
                        "median_cagr_difference": float(item["summary"]["median_cagr_difference"]),
                    }
                    for key, item in main["rolling_five_year"].items()
                },
                "signals": main["signals"],
                "current_target": main["current_target"],
            },
            "proxy": {
                "period": proxy["period"],
                "strategy_metrics": _clean_metric_set(proxy["strategy_metrics"]),
                "benchmark_metrics": {
                    key: _clean_metric_set(metrics)
                    for key, metrics in proxy["benchmark_metrics"].items()
                },
                "comparisons": {
                    key: {
                        "cagr_difference": float(item["cagr_difference"]),
                        "drawdown_improvement": float(item["drawdown_improvement"]),
                        "newey_west_t": float(item["active_return_newey_west"]["t_stat"]),
                        "probabilistic_sharpe_probability": float(
                            item["active_probabilistic_sharpe"]["probability"]
                        ),
                    }
                    for key, item in proxy["comparisons"].items()
                },
                "rolling_five_year": {
                    key: {
                        "win_fraction": float(item["summary"]["cagr_win_fraction"]),
                        "median_cagr_difference": float(item["summary"]["median_cagr_difference"]),
                    }
                    for key, item in proxy["rolling_five_year"].items()
                },
                "signals": proxy["signals"],
                "current_target": proxy["current_target"],
            },
            "gates": relative_growth_audit["gates"],
        }
        if not relative_growth_audit["historical_gate_passed"]:
            payload["limitations"].insert(
                0,
                "v7 永久 50% SPY 核心加相對成長開關，在 2006–2026 的 CAGR 10.59% 低於 SPY 11.27%，最大跌幅雖較 SPY 小，卻比相同月度股票持倉比率對照更深；19 道只過 6 道，不建立 Paper。",
            )
    if always_invested_audit is not None:
        main = always_invested_audit["main"]
        proxy = always_invested_audit["proxy"]
        payload.setdefault(
            "research_pipeline", {"primary_strategy": reference_audit["strategy_name"]}
        )["always_invested"] = {
            "name": always_invested_audit["strategy_name"],
            "status": always_invested_audit["status"],
            "paper_eligible": bool(always_invested_audit["paper_eligible"]),
            "historically_confirmed": bool(always_invested_audit["historically_confirmed"]),
            "passed_gate_count": int(always_invested_audit["passed_gate_count"]),
            "required_gate_count": int(always_invested_audit["required_gate_count"]),
            "paper_entry_passed_gate_count": int(
                always_invested_audit["paper_entry_passed_gate_count"]
            ),
            "paper_entry_required_gate_count": int(
                always_invested_audit["paper_entry_required_gate_count"]
            ),
            "protocol_sha256": always_invested_audit["protocol"]["sha256"],
            "main": {
                "period": main["period"],
                "strategy_metrics": _clean_metric_set(main["strategy_metrics"]),
                "benchmark_metrics": {
                    key: _clean_metric_set(metrics)
                    for key, metrics in main["benchmark_metrics"].items()
                },
                "comparison": {
                    "cagr_difference": float(main["comparison"]["cagr_difference"]),
                    "drawdown_difference": float(main["comparison"]["drawdown_difference"]),
                    "newey_west_t": float(main["comparison"]["active_return_newey_west"]["t_stat"]),
                    "probabilistic_sharpe_probability": float(
                        main["comparison"]["active_probabilistic_sharpe"]["probability"]
                    ),
                    "global_deflated_sharpe_probability": float(
                        main["comparison"]["active_global_deflated_sharpe"]["probability"]
                    ),
                },
                "cost_50bps_cagr_difference": float(main["cost_50bps"]["cagr_difference"]),
                "rolling_five_year": {
                    "win_fraction": float(
                        main["rolling_five_year"]["summary"]["cagr_win_fraction"]
                    ),
                    "median_cagr_difference": float(
                        main["rolling_five_year"]["summary"]["median_cagr_difference"]
                    ),
                },
                "signals": main["signals"],
                "current_target": main["current_target"],
            },
            "proxy": {
                "period": proxy["period"],
                "strategy_metrics": _clean_metric_set(proxy["strategy_metrics"]),
                "benchmark_metrics": {
                    key: _clean_metric_set(metrics)
                    for key, metrics in proxy["benchmark_metrics"].items()
                },
                "comparison": {
                    "cagr_difference": float(proxy["comparison"]["cagr_difference"]),
                    "drawdown_difference": float(proxy["comparison"]["drawdown_difference"]),
                    "newey_west_t": float(
                        proxy["comparison"]["active_return_newey_west"]["t_stat"]
                    ),
                    "probabilistic_sharpe_probability": float(
                        proxy["comparison"]["active_probabilistic_sharpe"]["probability"]
                    ),
                },
                "cost_50bps_cagr_difference": float(proxy["cost_50bps"]["cagr_difference"]),
                "rolling_five_year": {
                    "win_fraction": float(
                        proxy["rolling_five_year"]["summary"]["cagr_win_fraction"]
                    ),
                    "median_cagr_difference": float(
                        proxy["rolling_five_year"]["summary"]["median_cagr_difference"]
                    ),
                },
                "signals": proxy["signals"],
                "current_target": proxy["current_target"],
            },
            "paper_entry_gates": always_invested_audit["paper_entry_gates"],
            "statistical_gates": always_invested_audit["statistical_gates"],
            "global_dsr_promotion_sensitivity": {
                "passed": bool(always_invested_audit["global_dsr_promotion_sensitivity"]["passed"]),
                "main_probability": float(
                    always_invested_audit["global_dsr_promotion_sensitivity"]["main"]["probability"]
                ),
                "proxy_probability": float(
                    always_invested_audit["global_dsr_promotion_sensitivity"]["proxy"][
                        "probability"
                    ]
                ),
            },
        }
        if not always_invested_audit["paper_eligible"]:
            payload["limitations"].insert(
                0,
                "v8 永遠維持 100% 股票持倉比率，2006–2026 CAGR 12.32% 勝 SPY 11.27%，但 50 bps 成本後略輸 SPY；1989–2006 代理最大跌幅又比 S&P 500 深 6.97pp。Paper 入口 14/16，依凍結規格不建立 Paper 模擬組合。",
            )
    if low_turnover_audit is not None:
        datasets = {
            "main": low_turnover_audit["main"],
            "old_proxy": low_turnover_audit["old_proxy"],
            "external": low_turnover_audit["external"],
        }

        def clean_v9_period(data: dict[str, Any]) -> dict[str, Any]:
            return {
                "period": data["period"],
                "strategy_metrics": _clean_metric_set(data["strategy_metrics"]),
                "benchmark_metrics": {
                    key: _clean_metric_set(metrics)
                    for key, metrics in data["benchmark_metrics"].items()
                },
                "comparison": {
                    "cagr_difference": float(data["comparison"]["cagr_difference"]),
                    "drawdown_difference": float(data["comparison"]["drawdown_difference"]),
                    "newey_west_t": float(data["comparison"]["active_return_newey_west"]["t_stat"]),
                    "probabilistic_sharpe_probability": float(
                        data["comparison"]["active_probabilistic_sharpe"]["probability"]
                    ),
                    "global_deflated_sharpe_probability": float(
                        data["comparison"]["active_global_deflated_sharpe"]["probability"]
                    ),
                },
                "cost_50bps_cagr_difference": float(data["cost_50bps"]["cagr_difference"]),
                "fixed_halves": {
                    key: {"cagr_difference": float(item["cagr_difference"])}
                    for key, item in data["fixed_halves"].items()
                },
                "rolling_five_year": {
                    "win_fraction": float(
                        data["rolling_five_year"]["summary"]["cagr_win_fraction"]
                    ),
                    "median_cagr_difference": float(
                        data["rolling_five_year"]["summary"]["median_cagr_difference"]
                    ),
                },
                "signals": data["signals"],
                "current_policy_allocation": data["current_policy_allocation"],
                "historical_final_drifted_weights": data["historical_final_drifted_weights"],
            }

        payload.setdefault(
            "research_pipeline", {"primary_strategy": reference_audit["strategy_name"]}
        )["low_turnover"] = {
            "name": low_turnover_audit["strategy_name"],
            "status": low_turnover_audit["status"],
            "paper_eligible": bool(low_turnover_audit["paper_eligible"]),
            "historically_confirmed": bool(low_turnover_audit["historically_confirmed"]),
            "passed_gate_count": int(low_turnover_audit["passed_gate_count"]),
            "required_gate_count": int(low_turnover_audit["required_gate_count"]),
            "paper_entry_passed_gate_count": int(
                low_turnover_audit["paper_entry_passed_gate_count"]
            ),
            "paper_entry_required_gate_count": int(
                low_turnover_audit["paper_entry_required_gate_count"]
            ),
            "protocol_sha256": low_turnover_audit["protocol"]["sha256"],
            **{key: clean_v9_period(data) for key, data in datasets.items()},
            "paper_entry_gates": low_turnover_audit["paper_entry_gates"],
            "statistical_gates": low_turnover_audit["statistical_gates"],
            "global_dsr_promotion_sensitivity": {
                "passed": bool(low_turnover_audit["global_dsr_promotion_sensitivity"]["passed"]),
                **{
                    f"{key}_probability": float(item["probability"])
                    for key, item in low_turnover_audit["global_dsr_promotion_sensitivity"].items()
                    if key != "passed"
                },
            },
        }
        if not low_turnover_audit["paper_eligible"]:
            main = low_turnover_audit["main"]
            old = low_turnover_audit["old_proxy"]
            payload["limitations"].insert(
                0,
                "v9 改為只在狀態切換時交易、成長槽位降至 40%；2006–2026 CAGR "
                f"{main['strategy_metrics']['cagr']:.2%} 勝 SPY "
                f"{main['benchmark_metrics']['market']['cagr']:.2%}，但 50 bps 後僅領先 "
                f"{main['cost_50bps']['cagr_difference']:.3%}；舊代理最大跌幅惡化 "
                f"{abs(old['comparison']['drawdown_difference']):.2%}，1973–1988 外部期後半也落後。"
                f"Paper 入口 {low_turnover_audit['paper_entry_passed_gate_count']}/"
                f"{low_turnover_audit['paper_entry_required_gate_count']}，不建立 Paper 模擬組合。",
            )
    if hierarchical_defense_audit is not None:
        datasets = {
            "main": hierarchical_defense_audit["main"],
            "old_proxy": hierarchical_defense_audit["old_proxy"],
            "external": hierarchical_defense_audit["external"],
        }

        def clean_v12_period(data: dict[str, Any]) -> dict[str, Any]:
            return {
                "period": data["period"],
                "strategy_metrics": _clean_metric_set(data["strategy_metrics"]),
                "benchmark_metrics": {
                    key: _clean_metric_set(metrics)
                    for key, metrics in data["benchmark_metrics"].items()
                },
                "comparison": {
                    "cagr_difference": float(data["comparison"]["cagr_difference"]),
                    "drawdown_improvement": float(data["comparison"]["drawdown_improvement"]),
                    "newey_west_t": float(data["comparison"]["active_return_newey_west"]["t_stat"]),
                    "probabilistic_sharpe_probability": float(
                        data["comparison"]["active_probabilistic_sharpe"]["probability"]
                    ),
                    "global_deflated_sharpe_probability": float(
                        data["comparison"]["active_global_deflated_sharpe"]["probability"]
                    ),
                },
                "cost_50bps_cagr_difference": float(data["cost_50bps"]["cagr_difference"]),
                "fixed_halves": {
                    key: {"cagr_difference": float(item["cagr_difference"])}
                    for key, item in data["fixed_halves"].items()
                },
                "rolling_five_year": {
                    "win_fraction": float(
                        data["rolling_five_year"]["summary"]["cagr_win_fraction"]
                    ),
                    "median_cagr_difference": float(
                        data["rolling_five_year"]["summary"]["median_cagr_difference"]
                    ),
                    "latest_cagr_difference": float(
                        data["rolling_five_year"]["summary"]["latest_cagr_difference"]
                    ),
                },
                "signals": data["signals"],
                "current_policy_allocation": data["current_policy_allocation"],
                "historical_final_drifted_weights": data["historical_final_drifted_weights"],
            }

        payload.setdefault(
            "research_pipeline", {"primary_strategy": reference_audit["strategy_name"]}
        )["hierarchical_defense"] = {
            "name": hierarchical_defense_audit["strategy_name"],
            "status": hierarchical_defense_audit["status"],
            "paper_eligible": bool(hierarchical_defense_audit["paper_eligible"]),
            "historically_confirmed": bool(hierarchical_defense_audit["historically_confirmed"]),
            "passed_gate_count": int(hierarchical_defense_audit["passed_gate_count"]),
            "required_gate_count": int(hierarchical_defense_audit["required_gate_count"]),
            "paper_entry_passed_gate_count": int(
                hierarchical_defense_audit["paper_entry_passed_gate_count"]
            ),
            "paper_entry_required_gate_count": int(
                hierarchical_defense_audit["paper_entry_required_gate_count"]
            ),
            "protocol_sha256": hierarchical_defense_audit["protocol"]["sha256"],
            **{key: clean_v12_period(data) for key, data in datasets.items()},
            "prior_data_failures": {
                "v10": {
                    "status": hierarchical_defense_audit["data_receipts"]["v10_failure"]["status"],
                    "receipt_sha256": hierarchical_defense_audit["data_receipts"]["v10_failure"][
                        "receipt_file"
                    ]["sha256"],
                },
                "v11": {
                    "status": hierarchical_defense_audit["data_receipts"]["v11_failure"]["status"],
                    "failure_stage": hierarchical_defense_audit["data_receipts"]["v11_failure"][
                        "result"
                    ]["failure_stage"],
                    "error": hierarchical_defense_audit["data_receipts"]["v11_failure"]["result"][
                        "error"
                    ],
                    "receipt_sha256": hierarchical_defense_audit["data_receipts"]["v11_failure"][
                        "receipt_file"
                    ]["sha256"],
                },
            },
            "paper_entry_gates": hierarchical_defense_audit["paper_entry_gates"],
            "statistical_gates": hierarchical_defense_audit["statistical_gates"],
            "global_dsr_promotion_sensitivity": {
                "passed": bool(
                    hierarchical_defense_audit["global_dsr_promotion_sensitivity"]["passed"]
                ),
                **{
                    f"{key}_probability": float(item["probability"])
                    for key, item in hierarchical_defense_audit[
                        "global_dsr_promotion_sensitivity"
                    ].items()
                    if key != "passed"
                },
            },
        }
        if not hierarchical_defense_audit["paper_eligible"]:
            main = hierarchical_defense_audit["main"]
            payload["limitations"].insert(
                0,
                "v12 保留 60% 核心，剩餘 40% 依序切到成長、核心或防守；"
                f"2006–2026 CAGR {main['strategy_metrics']['cagr']:.2%} 低於 SPY "
                f"{main['benchmark_metrics']['market']['cagr']:.2%}，雖把最大跌幅改善 "
                f"{main['comparison']['drawdown_improvement']:.2%}，50 bps 後年率化落後 "
                f"{abs(main['cost_50bps']['cagr_difference']):.2%}。1973–1988 後半也落後，"
                f"Paper 入口 {hierarchical_defense_audit['paper_entry_passed_gate_count']}/"
                f"{hierarchical_defense_audit['paper_entry_required_gate_count']}，不建立 Paper 模擬組合。",
            )
    if confirmed_relative_growth_audit is not None:

        def clean_v13_dataset(data: dict[str, Any]) -> dict[str, Any]:
            base = {
                "label": data["label"],
                "assets": data["assets"],
                "status": data["status"],
                "data_gate_passed": bool(data["data_gate_passed"]),
                "warmup_common_sessions": int(data["warmup_common_sessions"]),
                "required_warmup_sessions": int(data["required_warmup_sessions"]),
                "economic_gates": data["economic_gates"],
                "passed_gate_count": int(sum(data["economic_gates"].values())),
                "required_gate_count": int(len(data["economic_gates"])),
            }
            if data["status"] != "completed":
                diagnostic = data.get("diagnostic")
                return {
                    **base,
                    "failure": data["failure"],
                    "diagnostic": None
                    if not diagnostic
                    else {
                        "gate_eligible": False,
                        "start": diagnostic["start"],
                        "strategy_metrics": _clean_metric_set(diagnostic["strategy_metrics"]),
                        "market_metrics": _clean_metric_set(diagnostic["market_metrics"]),
                    },
                }
            return {
                **base,
                "strategy_metrics": _clean_metric_set(data["strategy_metrics"]),
                "benchmark_metrics": {
                    "market": _clean_metric_set(data["benchmark_metrics"]["market"]),
                    "matched": _clean_metric_set(data["benchmark_metrics"]["matched"]),
                },
                "comparison": {
                    "cagr_difference": float(data["comparison"]["cagr_difference"]),
                    "drawdown_improvement": float(data["comparison"]["drawdown_improvement"]),
                    "newey_west_t": float(data["comparison"]["active_return_newey_west"]["t_stat"]),
                },
                "cost_50bps_cagr_difference": float(data["cost_50bps"]["cagr_difference"]),
                "fixed_halves": {
                    key: {"cagr_difference": float(item["cagr_difference"])}
                    for key, item in data["fixed_halves"].items()
                },
                "rolling_five_year": {
                    "win_fraction": float(
                        data["rolling_five_year"]["summary"]["cagr_win_fraction"]
                    ),
                    "median_cagr_difference": float(
                        data["rolling_five_year"]["summary"]["median_cagr_difference"]
                    ),
                },
                "signals": data["signals"],
            }

        v13_datasets = {
            key: clean_v13_dataset(data)
            for key, data in confirmed_relative_growth_audit["datasets"].items()
        }
        payload.setdefault(
            "research_pipeline", {"primary_strategy": reference_audit["strategy_name"]}
        )["confirmed_relative_growth"] = {
            "name": confirmed_relative_growth_audit["strategy_name"],
            "status": confirmed_relative_growth_audit["status"],
            "paper_eligible": bool(confirmed_relative_growth_audit["paper_eligible"]),
            "historically_confirmed": bool(
                confirmed_relative_growth_audit["historically_confirmed"]
            ),
            "economic_passed_gate_count": int(
                confirmed_relative_growth_audit["economic_passed_gate_count"]
            ),
            "economic_required_gate_count": int(
                confirmed_relative_growth_audit["economic_required_gate_count"]
            ),
            "data_passed_gate_count": int(
                confirmed_relative_growth_audit["data_passed_gate_count"]
            ),
            "data_required_gate_count": int(
                confirmed_relative_growth_audit["data_required_gate_count"]
            ),
            "statistical_passed_gate_count": int(
                confirmed_relative_growth_audit["statistical_passed_gate_count"]
            ),
            "statistical_required_gate_count": int(
                confirmed_relative_growth_audit["statistical_required_gate_count"]
            ),
            "protocol_sha256": confirmed_relative_growth_audit["protocol"]["sha256"],
            "datasets": v13_datasets,
            "paper_entry_decision": "do_not_create",
        }
        if not confirmed_relative_growth_audit["paper_eligible"]:
            r1000 = confirmed_relative_growth_audit["datasets"]["russell_1000"]
            r2000 = confirmed_relative_growth_audit["datasets"]["russell_2000"]
            eafe = confirmed_relative_growth_audit["datasets"]["eafe"]
            payload["limitations"].insert(
                0,
                "v13 先凍結兩月確認與部分防守規則，再下載三組新 ETF；"
                f"Russell 1000 CAGR {r1000['strategy_metrics']['cagr']:.2%} 低於 IWB "
                f"{r1000['benchmark_metrics']['market']['cagr']:.2%}，Russell 2000 CAGR "
                f"{r2000['strategy_metrics']['cagr']:.2%} 低於 IWM "
                f"{r2000['benchmark_metrics']['market']['cagr']:.2%}，EAFE 固定起點前只有 "
                f"{eafe['warmup_common_sessions']}/252 個暖機日。新數據經濟門檻 "
                f"{confirmed_relative_growth_audit['economic_passed_gate_count']}/"
                f"{confirmed_relative_growth_audit['economic_required_gate_count']}，不建 Paper。",
            )
    if modest_leverage_audit is not None:

        def clean_v14_dataset(data: dict[str, Any]) -> dict[str, Any]:
            base = {
                "label": data["label"],
                "assets": data["assets"],
                "status": data["status"],
                "data_gate_passed": bool(data["data_gate_passed"]),
                "signal_warmup_sessions": int(data["signal_warmup_sessions"]),
                "leveraged_prestart_sessions": int(data["leveraged_prestart_sessions"]),
                "economic_gates": data["economic_gates"],
                "passed_gate_count": int(sum(data["economic_gates"].values())),
                "required_gate_count": int(len(data["economic_gates"])),
            }
            if data["status"] != "completed":
                return {**base, "failure": data["failure"]}
            return {
                **base,
                "strategy_metrics": _clean_metric_set(data["strategy_metrics"]),
                "benchmark_metrics": {
                    "core": _clean_metric_set(data["benchmark_metrics"]["core"]),
                    "fixed_60_40": _clean_metric_set(data["benchmark_metrics"]["fixed_60_40"]),
                },
                "comparison_vs_core": {
                    "cagr_difference": float(data["comparison_vs_core"]["cagr_difference"]),
                    "drawdown_improvement": float(
                        data["comparison_vs_core"]["drawdown_improvement"]
                    ),
                    "newey_west_t": float(
                        data["comparison_vs_core"]["active_return_newey_west"]["t_stat"]
                    ),
                },
                "comparison_vs_fixed_60_40": {
                    "cagr_difference": float(data["comparison_vs_fixed_60_40"]["cagr_difference"]),
                    "drawdown_improvement": float(
                        data["comparison_vs_fixed_60_40"]["drawdown_improvement"]
                    ),
                    "newey_west_t": float(
                        data["comparison_vs_fixed_60_40"]["active_return_newey_west"]["t_stat"]
                    ),
                },
                "cost_50bps": {
                    "vs_core_cagr_difference": float(data["cost_50bps"]["vs_core_cagr_difference"]),
                    "vs_fixed_60_40_cagr_difference": float(
                        data["cost_50bps"]["vs_fixed_60_40_cagr_difference"]
                    ),
                },
                "rolling_five_year_vs_core": {
                    "win_fraction": float(
                        data["rolling_five_year_vs_core"]["summary"]["cagr_win_fraction"]
                    ),
                    "median_cagr_difference": float(
                        data["rolling_five_year_vs_core"]["summary"]["median_cagr_difference"]
                    ),
                },
                "signals": data["signals"],
            }

        v14_datasets = {
            key: clean_v14_dataset(data) for key, data in modest_leverage_audit["datasets"].items()
        }
        payload.setdefault(
            "research_pipeline", {"primary_strategy": reference_audit["strategy_name"]}
        )["modest_leverage"] = {
            "name": modest_leverage_audit["strategy_name"],
            "status": modest_leverage_audit["status"],
            "paper_eligible": bool(modest_leverage_audit["paper_eligible"]),
            "statistically_confirmed": bool(modest_leverage_audit["statistically_confirmed"]),
            "economic_passed_gate_count": int(modest_leverage_audit["economic_passed_gate_count"]),
            "economic_required_gate_count": int(
                modest_leverage_audit["economic_required_gate_count"]
            ),
            "data_passed_gate_count": int(modest_leverage_audit["data_passed_gate_count"]),
            "data_required_gate_count": int(modest_leverage_audit["data_required_gate_count"]),
            "statistical_passed_gate_count": int(
                modest_leverage_audit["statistical_passed_gate_count"]
            ),
            "statistical_required_gate_count": int(
                modest_leverage_audit["statistical_required_gate_count"]
            ),
            "protocol_sha256": modest_leverage_audit["protocol"]["sha256"],
            "maximum_equity_notional": float(
                modest_leverage_audit["parameters"]["approximate_maximum_equity_notional"]
            ),
            "datasets": v14_datasets,
            "paper_entry_decision": (
                "create_isolated_only"
                if modest_leverage_audit["paper_eligible"]
                else "do_not_create"
            ),
        }
        if not modest_leverage_audit["paper_eligible"]:
            sp500 = modest_leverage_audit["datasets"]["sp500"]
            nasdaq = modest_leverage_audit["datasets"]["nasdaq100"]
            dow = modest_leverage_audit["datasets"]["dow30"]
            payload["limitations"].insert(
                0,
                "v14 先凍結 60% 實際 2 倍 ETF／40% SHY 與兩月趨勢規則，再下載 "
                "SSO、QLD、DDM；S&P 500 CAGR "
                f"{sp500['strategy_metrics']['cagr']:.2%} 低於 SPY "
                f"{sp500['benchmark_metrics']['core']['cagr']:.2%}，Dow 30 CAGR "
                f"{dow['strategy_metrics']['cagr']:.2%} 低於 DIA "
                f"{dow['benchmark_metrics']['core']['cagr']:.2%}。Nasdaq-100 雖略勝 QQQ，"
                f"仍低於固定 60/40 的 {nasdaq['benchmark_metrics']['fixed_60_40']['cagr']:.2%}。"
                f"經濟門檻 {modest_leverage_audit['economic_passed_gate_count']}/"
                f"{modest_leverage_audit['economic_required_gate_count']}，不建 Paper。",
            )
    if modest_leverage_overlay_audit is not None:

        def clean_v15_dataset(data: dict[str, Any]) -> dict[str, Any]:
            base = {
                "label": data["label"],
                "assets": data["assets"],
                "status": data["status"],
                "data_gate_passed": bool(data["data_gate_passed"]),
                "core_prestart_sessions": int(data["core_prestart_sessions"]),
                "leveraged_prestart_sessions": int(data["leveraged_prestart_sessions"]),
                "economic_gates": data["economic_gates"],
                "passed_gate_count": int(sum(data["economic_gates"].values())),
                "required_gate_count": int(len(data["economic_gates"])),
            }
            if data["status"] != "completed":
                return {**base, "failure": data["failure"]}
            return {
                **base,
                "strategy_metrics": _clean_metric_set(data["strategy_metrics"]),
                "benchmark_metrics": {
                    "core": _clean_metric_set(data["benchmark_metrics"]["core"]),
                    "fixed_90_10": _clean_metric_set(data["benchmark_metrics"]["fixed_90_10"]),
                },
                "comparison_vs_core": {
                    "cagr_difference": float(data["comparison_vs_core"]["cagr_difference"]),
                    "sharpe_difference": float(data["comparison_vs_core"]["sharpe_difference"]),
                    "drawdown_improvement": float(
                        data["comparison_vs_core"]["drawdown_improvement"]
                    ),
                    "newey_west_t": float(
                        data["comparison_vs_core"]["active_return_newey_west"]["t_stat"]
                    ),
                },
                "comparison_vs_fixed_90_10": {
                    "cagr_difference": float(data["comparison_vs_fixed_90_10"]["cagr_difference"]),
                    "sharpe_difference": float(
                        data["comparison_vs_fixed_90_10"]["sharpe_difference"]
                    ),
                    "drawdown_improvement": float(
                        data["comparison_vs_fixed_90_10"]["drawdown_improvement"]
                    ),
                    "newey_west_t": float(
                        data["comparison_vs_fixed_90_10"]["active_return_newey_west"]["t_stat"]
                    ),
                },
                "cost_50bps": {
                    "vs_core_cagr_difference": float(data["cost_50bps"]["vs_core_cagr_difference"]),
                    "vs_fixed_90_10_cagr_difference": float(
                        data["cost_50bps"]["vs_fixed_90_10_cagr_difference"]
                    ),
                },
                "rolling_five_year_vs_core": {
                    "win_fraction": float(
                        data["rolling_five_year_vs_core"]["summary"]["cagr_win_fraction"]
                    ),
                    "median_cagr_difference": float(
                        data["rolling_five_year_vs_core"]["summary"]["median_cagr_difference"]
                    ),
                },
                "signals": data["signals"],
            }

        v15_datasets = {
            key: clean_v15_dataset(data)
            for key, data in modest_leverage_overlay_audit["datasets"].items()
        }
        payload.setdefault(
            "research_pipeline", {"primary_strategy": reference_audit["strategy_name"]}
        )["modest_leverage_overlay"] = {
            "name": modest_leverage_overlay_audit["strategy_name"],
            "status": modest_leverage_overlay_audit["status"],
            "paper_eligible": bool(modest_leverage_overlay_audit["paper_eligible"]),
            "statistically_confirmed": bool(
                modest_leverage_overlay_audit["statistically_confirmed"]
            ),
            "economic_passed_gate_count": int(
                modest_leverage_overlay_audit["economic_passed_gate_count"]
            ),
            "economic_required_gate_count": int(
                modest_leverage_overlay_audit["economic_required_gate_count"]
            ),
            "data_passed_gate_count": int(modest_leverage_overlay_audit["data_passed_gate_count"]),
            "data_required_gate_count": int(
                modest_leverage_overlay_audit["data_required_gate_count"]
            ),
            "statistical_passed_gate_count": int(
                modest_leverage_overlay_audit["statistical_passed_gate_count"]
            ),
            "statistical_required_gate_count": int(
                modest_leverage_overlay_audit["statistical_required_gate_count"]
            ),
            "protocol_sha256": modest_leverage_overlay_audit["protocol"]["sha256"],
            "risk_on_equity_notional": float(
                modest_leverage_overlay_audit["parameters"]["risk_on_approximate_equity_notional"]
            ),
            "independent_confirmation_years": int(
                modest_leverage_overlay_audit["evidence_boundary"]["independent_confirmation_years"]
            ),
            "cannot_claim_independent_twenty_year_v15": bool(
                modest_leverage_overlay_audit["evidence_boundary"][
                    "cannot_claim_independent_twenty_year_v15"
                ]
            ),
            "datasets": v15_datasets,
            "paper_entry_decision": (
                "create_isolated_only"
                if modest_leverage_overlay_audit["paper_eligible"]
                else "do_not_create"
            ),
        }
        if not modest_leverage_overlay_audit["paper_eligible"]:
            sp500 = modest_leverage_overlay_audit["datasets"]["sp500"]
            nasdaq = modest_leverage_overlay_audit["datasets"]["nasdaq100"]
            dow = modest_leverage_overlay_audit["datasets"]["dow30"]
            payload["limitations"].insert(
                0,
                "v15 先凍結約 120%／100% 股票持倉比率與兩月趨勢規則，再首次查看 UPRO、"
                "TQQQ、UDOW。三市場 CAGR 都高於原始 ETF：S&P 500 "
                f"{sp500['strategy_metrics']['cagr']:.2%} / SPY "
                f"{sp500['benchmark_metrics']['core']['cagr']:.2%}，Nasdaq-100 "
                f"{nasdaq['strategy_metrics']['cagr']:.2%} / QQQ "
                f"{nasdaq['benchmark_metrics']['core']['cagr']:.2%}，Dow 30 "
                f"{dow['strategy_metrics']['cagr']:.2%} / DIA "
                f"{dow['benchmark_metrics']['core']['cagr']:.2%}；但三組最大跌幅都更深、"
                f"Sharpe 都未嚴格勝過原始 ETF。經濟門檻 "
                f"{modest_leverage_overlay_audit['economic_passed_gate_count']}/"
                f"{modest_leverage_overlay_audit['economic_required_gate_count']}，不建 Paper。",
            )
    if trend_volatility_brake_audit is not None:

        def clean_v16_dataset(data: dict[str, Any]) -> dict[str, Any]:
            base = {
                "label": data["label"],
                "assets": data["assets"],
                "status": data["status"],
                "data_gate_passed": bool(data["data_gate_passed"]),
                "economic_gates": data["economic_gates"],
                "passed_gate_count": int(sum(data["economic_gates"].values())),
                "required_gate_count": int(len(data["economic_gates"])),
            }
            if data["status"] != "completed":
                return {**base, "failure": data["failure"]}
            return {
                **base,
                "period": data["period"],
                "strategy_metrics": _clean_metric_set(data["strategy_metrics"]),
                "benchmark_metrics": {
                    "core": _clean_metric_set(data["benchmark_metrics"]["core"]),
                    "unlevered_trend": _clean_metric_set(
                        data["benchmark_metrics"]["unlevered_trend"]
                    ),
                    "fixed_150": _clean_metric_set(data["benchmark_metrics"]["fixed_150"]),
                },
                "comparison_vs_core": {
                    "cagr_difference": float(data["comparison_vs_core"]["cagr_difference"]),
                    "drawdown_improvement": float(
                        data["comparison_vs_core"]["drawdown_improvement"]
                    ),
                    "newey_west_t": float(
                        data["comparison_vs_core"]["active_return_newey_west"]["t_stat"]
                    ),
                },
                "signals": data["signals"],
            }

        payload.setdefault(
            "research_pipeline", {"primary_strategy": reference_audit["strategy_name"]}
        )["trend_volatility_brake"] = {
            "name": trend_volatility_brake_audit["strategy_name"],
            "status": trend_volatility_brake_audit["status"],
            "paper_eligible": bool(trend_volatility_brake_audit["paper_eligible"]),
            "statistically_confirmed": bool(
                trend_volatility_brake_audit["statistically_confirmed"]
            ),
            "economic_passed_gate_count": int(
                trend_volatility_brake_audit["economic_passed_gate_count"]
            ),
            "economic_required_gate_count": int(
                trend_volatility_brake_audit["economic_required_gate_count"]
            ),
            "data_passed_gate_count": int(trend_volatility_brake_audit["data_passed_gate_count"]),
            "data_required_gate_count": int(
                trend_volatility_brake_audit["data_required_gate_count"]
            ),
            "statistical_passed_gate_count": int(
                trend_volatility_brake_audit["statistical_passed_gate_count"]
            ),
            "statistical_required_gate_count": int(
                trend_volatility_brake_audit["statistical_required_gate_count"]
            ),
            "independent_confirmation_years": int(
                trend_volatility_brake_audit["evidence_boundary"]["independent_confirmation_years"]
            ),
            "datasets": {
                key: clean_v16_dataset(data)
                for key, data in trend_volatility_brake_audit["datasets"].items()
            },
            "paper_entry_decision": (
                "create_isolated_only"
                if trend_volatility_brake_audit["paper_eligible"]
                else "do_not_create"
            ),
        }
        if not trend_volatility_brake_audit["paper_eligible"]:
            mid = trend_volatility_brake_audit["datasets"]["midcap400"]
            r2000 = trend_volatility_brake_audit["datasets"]["russell2000"]
            small = trend_volatility_brake_audit["datasets"]["smallcap600"]
            payload["limitations"].insert(
                0,
                "v16 先凍結 200 日趨勢、21 日波幅與每週 100%–150% 股票持倉比率，"
                "再首次查看 MVV、UWM、SAA。三組策略 CAGR 分別為 "
                f"{mid['strategy_metrics']['cagr']:.2%}、"
                f"{r2000['strategy_metrics']['cagr']:.2%}、"
                f"{small['strategy_metrics']['cagr']:.2%}，都低於原始 ETF；經濟門檻 "
                f"{trend_volatility_brake_audit['economic_passed_gate_count']}/"
                f"{trend_volatility_brake_audit['economic_required_gate_count']}，不建 Paper。",
            )
    if capital_efficient_audit is not None:

        def clean_v17_dataset(data: dict[str, Any]) -> dict[str, Any]:
            base = {
                "label": data["label"],
                "assets": data["assets"],
                "status": data["status"],
                "data_gate_passed": bool(data["data_gate_passed"]),
                "economic_gates": data["economic_gates"],
                "passed_gate_count": int(sum(data["economic_gates"].values())),
                "required_gate_count": int(len(data["economic_gates"])),
            }
            if data["status"] != "completed":
                return {**base, "failure": data["failure"]}
            return {
                **base,
                "period": data["period"],
                "strategy_metrics": _clean_metric_set(data["strategy_metrics"]),
                "benchmark_metrics": {
                    "core": _clean_metric_set(data["benchmark_metrics"]["core"]),
                    "unlevered_75_25": _clean_metric_set(
                        data["benchmark_metrics"]["unlevered_75_25"]
                    ),
                    "leveraged_60_40_shy": _clean_metric_set(
                        data["benchmark_metrics"]["leveraged_60_40_shy"]
                    ),
                },
                "comparison_vs_core": {
                    "cagr_difference": float(data["comparison_vs_core"]["cagr_difference"]),
                    "drawdown_improvement": float(
                        data["comparison_vs_core"]["drawdown_improvement"]
                    ),
                    "newey_west_t": float(
                        data["comparison_vs_core"]["active_return_newey_west"]["t_stat"]
                    ),
                },
                "signals": data["signals"],
            }

        payload.setdefault(
            "research_pipeline", {"primary_strategy": reference_audit["strategy_name"]}
        )["capital_efficient"] = {
            "name": capital_efficient_audit["strategy_name"],
            "status": capital_efficient_audit["status"],
            "paper_eligible": bool(capital_efficient_audit["paper_eligible"]),
            "statistically_confirmed": bool(capital_efficient_audit["statistically_confirmed"]),
            "economic_passed_gate_count": int(
                capital_efficient_audit["economic_passed_gate_count"]
            ),
            "economic_required_gate_count": int(
                capital_efficient_audit["economic_required_gate_count"]
            ),
            "data_passed_gate_count": int(capital_efficient_audit["data_passed_gate_count"]),
            "data_required_gate_count": int(capital_efficient_audit["data_required_gate_count"]),
            "statistical_passed_gate_count": int(
                capital_efficient_audit["statistical_passed_gate_count"]
            ),
            "statistical_required_gate_count": int(
                capital_efficient_audit["statistical_required_gate_count"]
            ),
            "large_cap_years": int(capital_efficient_audit["evidence_boundary"]["large_cap_years"]),
            "mid_small_cap_years": int(
                capital_efficient_audit["evidence_boundary"]["mid_small_cap_years"]
            ),
            "datasets": {
                key: clean_v17_dataset(data)
                for key, data in capital_efficient_audit["datasets"].items()
            },
            "paper_entry_decision": (
                "create_isolated_only"
                if capital_efficient_audit["paper_eligible"]
                else "do_not_create"
            ),
        }
        if not capital_efficient_audit["paper_eligible"]:
            sp500 = capital_efficient_audit["datasets"]["sp500"]
            nasdaq = capital_efficient_audit["datasets"]["nasdaq100"]
            payload["limitations"].insert(
                0,
                "v17 每月固定 60% 實際 2 倍股票 ETF／40% IEF；大型股 20 年、"
                "中小型股 18 年。S&P 500 CAGR "
                f"{sp500['strategy_metrics']['cagr']:.2%} / SPY "
                f"{sp500['benchmark_metrics']['core']['cagr']:.2%}，Nasdaq-100 "
                f"{nasdaq['strategy_metrics']['cagr']:.2%} / QQQ "
                f"{nasdaq['benchmark_metrics']['core']['cagr']:.2%}；但六組最大跌幅都更深。"
                f"經濟門檻 {capital_efficient_audit['economic_passed_gate_count']}/"
                f"{capital_efficient_audit['economic_required_gate_count']}，不建 Paper。",
            )
    if equal_diversifier_audit is not None:

        def clean_v18_dataset(data: dict[str, Any]) -> dict[str, Any]:
            base = {
                "label": data["label"],
                "assets": data["assets"],
                "status": data["status"],
                "data_gate_passed": bool(data["data_gate_passed"]),
                "economic_gates": data["economic_gates"],
                "passed_gate_count": int(sum(data["economic_gates"].values())),
                "required_gate_count": int(len(data["economic_gates"])),
            }
            if data["status"] != "completed":
                return {**base, "failure": data["failure"]}
            return {
                **base,
                "period": data["period"],
                "strategy_metrics": _clean_metric_set(data["strategy_metrics"]),
                "benchmark_metrics": {
                    "core": _clean_metric_set(data["benchmark_metrics"]["core"]),
                    "unlevered_same_assets": _clean_metric_set(
                        data["benchmark_metrics"]["unlevered_same_assets"]
                    ),
                    "leveraged_50_50_ief": _clean_metric_set(
                        data["benchmark_metrics"]["leveraged_50_50_ief"]
                    ),
                    "leveraged_50_50_gld": _clean_metric_set(
                        data["benchmark_metrics"]["leveraged_50_50_gld"]
                    ),
                },
                "comparison_vs_core": {
                    "cagr_difference": float(data["comparisons"]["core"]["cagr_difference"]),
                    "drawdown_improvement": float(
                        data["comparisons"]["core"]["drawdown_improvement"]
                    ),
                    "newey_west_t": float(
                        data["comparisons"]["core"]["active_return_newey_west"]["t_stat"]
                    ),
                },
                "fixed_halves_vs_core": {
                    key: {
                        "start": item["start"],
                        "end": item["end"],
                        "cagr_difference": float(item["cagr_difference"]),
                    }
                    for key, item in data["fixed_halves_vs_core"].items()
                },
                "rolling_five_year_vs_core": {
                    key: float(value) if isinstance(value, (int, float)) else value
                    for key, value in data["rolling_five_year_vs_core"]["summary"].items()
                },
                "signals": data["signals"],
            }

        payload.setdefault(
            "research_pipeline", {"primary_strategy": reference_audit["strategy_name"]}
        )["equal_diversifier"] = {
            "name": equal_diversifier_audit["strategy_name"],
            "status": equal_diversifier_audit["status"],
            "paper_eligible": bool(equal_diversifier_audit["paper_eligible"]),
            "statistically_confirmed": bool(equal_diversifier_audit["statistically_confirmed"]),
            "economic_passed_gate_count": int(
                equal_diversifier_audit["economic_passed_gate_count"]
            ),
            "economic_required_gate_count": int(
                equal_diversifier_audit["economic_required_gate_count"]
            ),
            "data_passed_gate_count": int(equal_diversifier_audit["data_passed_gate_count"]),
            "data_required_gate_count": int(equal_diversifier_audit["data_required_gate_count"]),
            "statistical_passed_gate_count": int(
                equal_diversifier_audit["statistical_passed_gate_count"]
            ),
            "statistical_required_gate_count": int(
                equal_diversifier_audit["statistical_required_gate_count"]
            ),
            "external_years": int(equal_diversifier_audit["evidence_boundary"]["external_years"]),
            "evidence_classification": equal_diversifier_audit["evidence_boundary"][
                "classification"
            ],
            "datasets": {
                key: clean_v18_dataset(data)
                for key, data in equal_diversifier_audit["datasets"].items()
            },
            "paper_entry_decision": (
                "create_isolated_only"
                if equal_diversifier_audit["paper_eligible"]
                else "do_not_create"
            ),
        }
        if not equal_diversifier_audit["paper_eligible"]:
            developed = equal_diversifier_audit["datasets"]["developed_ex_us"]
            emerging = equal_diversifier_audit["datasets"]["emerging_markets"]
            payload["limitations"].insert(
                0,
                "v18 在六個已見美國市場選定 50% 實際 2 倍股票 ETF／25% IEF／"
                "25% GLD，再以凍結後的海外日線驗證。已開發市場 CAGR "
                f"{developed['strategy_metrics']['cagr']:.2%} / EFA "
                f"{developed['benchmark_metrics']['core']['cagr']:.2%}，新興市場 "
                f"{emerging['strategy_metrics']['cagr']:.2%} / EEM "
                f"{emerging['benchmark_metrics']['core']['cagr']:.2%}；兩組最大跌幅都更深，"
                f"外部經濟門檻 {equal_diversifier_audit['economic_passed_gate_count']}/"
                f"{equal_diversifier_audit['economic_required_gate_count']}，不建 Paper。",
            )
    if diversifier_strength_audit is not None:

        def clean_v20_dataset(data: dict[str, Any]) -> dict[str, Any]:
            return {
                "label": data["label"],
                "assets": data["assets"],
                "evidence_role": data["evidence_role"],
                "status": data["status"],
                "data_gate_passed": bool(data["data_gate_passed"]),
                "economic_gates": data["economic_gates"],
                "passed_gate_count": int(sum(data["economic_gates"].values())),
                "required_gate_count": int(len(data["economic_gates"])),
                "period": data["period"],
                "strategy_metrics": _clean_metric_set(data["strategy_metrics"]),
                "benchmark_metrics": {
                    "core": _clean_metric_set(data["benchmark_metrics"]["core"]),
                    "fixed_v18": _clean_metric_set(data["benchmark_metrics"]["fixed_v18"]),
                    "unlevered_same_policy": _clean_metric_set(
                        data["benchmark_metrics"]["unlevered_same_policy"]
                    ),
                },
                "comparison_vs_core": {
                    "cagr_difference": float(data["comparisons"]["core"]["cagr_difference"]),
                    "drawdown_improvement": float(
                        data["comparisons"]["core"]["drawdown_improvement"]
                    ),
                    "newey_west_t": float(
                        data["comparisons"]["core"]["active_return_newey_west"]["t_stat"]
                    ),
                },
                "fixed_halves_vs_core": {
                    key: {
                        "start": item["start"],
                        "end": item["end"],
                        "cagr_difference": float(item["cagr_difference"]),
                    }
                    for key, item in data["fixed_halves_vs_core"].items()
                },
                "rolling_five_year_vs_core": {
                    key: float(value) if isinstance(value, (int, float)) else value
                    for key, value in data["rolling_five_year_vs_core"]["summary"].items()
                },
                "signals": data["signals"],
            }

        payload.setdefault(
            "research_pipeline", {"primary_strategy": reference_audit["strategy_name"]}
        )["diversifier_strength"] = {
            "name": diversifier_strength_audit["strategy_name"],
            "status": diversifier_strength_audit["status"],
            "paper_eligible": bool(diversifier_strength_audit["paper_eligible"]),
            "statistically_confirmed": bool(diversifier_strength_audit["statistically_confirmed"]),
            "design_economic_passed_gate_count": int(
                diversifier_strength_audit["design_economic_passed_gate_count"]
            ),
            "design_economic_required_gate_count": int(
                diversifier_strength_audit["design_economic_required_gate_count"]
            ),
            "external_economic_passed_gate_count": int(
                diversifier_strength_audit["external_economic_passed_gate_count"]
            ),
            "external_economic_required_gate_count": int(
                diversifier_strength_audit["external_economic_required_gate_count"]
            ),
            "economic_passed_gate_count": int(
                diversifier_strength_audit["economic_passed_gate_count"]
            ),
            "economic_required_gate_count": int(
                diversifier_strength_audit["economic_required_gate_count"]
            ),
            "data_passed_gate_count": int(diversifier_strength_audit["data_passed_gate_count"]),
            "data_required_gate_count": int(diversifier_strength_audit["data_required_gate_count"]),
            "statistical_passed_gate_count": int(
                diversifier_strength_audit["statistical_passed_gate_count"]
            ),
            "statistical_required_gate_count": int(
                diversifier_strength_audit["statistical_required_gate_count"]
            ),
            "external_years": int(
                diversifier_strength_audit["evidence_boundary"]["external_years"]
            ),
            "evidence_classification": diversifier_strength_audit["evidence_boundary"][
                "classification"
            ],
            "datasets": {
                key: clean_v20_dataset(data)
                for key, data in diversifier_strength_audit["datasets"].items()
            },
            "paper_entry_decision": (
                "create_isolated_only"
                if diversifier_strength_audit["paper_eligible"]
                else "do_not_create"
            ),
        }
        if not diversifier_strength_audit["paper_eligible"]:
            japan = diversifier_strength_audit["datasets"]["japan"]
            china = diversifier_strength_audit["datasets"]["china_large_cap"]
            brazil = diversifier_strength_audit["datasets"]["brazil"]
            payload["limitations"].insert(
                0,
                "v20 固定 50% 實際 2 倍股票 ETF，再從 IEF／GLD／SHY 依 12–1 月"
                "相對強度選兩檔。數據與時序完整，但 11 市場經濟門檻 "
                f"{diversifier_strength_audit['economic_passed_gate_count']}/"
                f"{diversifier_strength_audit['economic_required_gate_count']}，新外部 "
                f"{diversifier_strength_audit['external_economic_passed_gate_count']}/"
                f"{diversifier_strength_audit['external_economic_required_gate_count']}；"
                f"日本 CAGR {japan['strategy_metrics']['cagr']:.2%} / EWJ "
                f"{japan['benchmark_metrics']['core']['cagr']:.2%}，中國大型股 "
                f"{china['strategy_metrics']['cagr']:.2%} / FXI "
                f"{china['benchmark_metrics']['core']['cagr']:.2%}，巴西 "
                f"{brazil['strategy_metrics']['cagr']:.2%} / EWZ "
                f"{brazil['benchmark_metrics']['core']['cagr']:.2%}。輪替未勝固定 v18，"
                "不建 Paper。",
            )
    if hybrid_leverage_core_audit is not None:

        def clean_v21_dataset(data: dict[str, Any]) -> dict[str, Any]:
            return {
                "label": data["label"],
                "assets": data["assets"],
                "evidence_role": data["evidence_role"],
                "status": data["status"],
                "data_gate_passed": bool(data["data_gate_passed"]),
                "economic_gates": data["economic_gates"],
                "passed_gate_count": int(sum(data["economic_gates"].values())),
                "required_gate_count": int(len(data["economic_gates"])),
                "period": data["period"],
                "strategy_metrics": _clean_metric_set(data["strategy_metrics"]),
                "benchmark_metrics": {
                    "core": _clean_metric_set(data["benchmark_metrics"]["core"]),
                    "fixed_risk_on": _clean_metric_set(data["benchmark_metrics"]["fixed_risk_on"]),
                    "fixed_risk_off": _clean_metric_set(
                        data["benchmark_metrics"]["fixed_risk_off"]
                    ),
                },
                "comparison_vs_core": {
                    "cagr_difference": float(data["comparisons"]["core"]["cagr_difference"]),
                    "drawdown_improvement": float(
                        data["comparisons"]["core"]["drawdown_improvement"]
                    ),
                    "newey_west_t": float(
                        data["comparisons"]["core"]["active_return_newey_west"]["t_stat"]
                    ),
                },
                "fixed_halves_vs_core": {
                    key: {
                        "start": item["start"],
                        "end": item["end"],
                        "cagr_difference": float(item["cagr_difference"]),
                    }
                    for key, item in data["fixed_halves_vs_core"].items()
                },
                "rolling_five_year_vs_core": {
                    key: float(value) if isinstance(value, (int, float)) else value
                    for key, value in data["rolling_five_year_vs_core"]["summary"].items()
                },
                "signals": data["signals"],
            }

        payload.setdefault(
            "research_pipeline", {"primary_strategy": reference_audit["strategy_name"]}
        )["hybrid_leverage_core"] = {
            "name": hybrid_leverage_core_audit["strategy_name"],
            "status": hybrid_leverage_core_audit["status"],
            "paper_eligible": bool(hybrid_leverage_core_audit["paper_eligible"]),
            "trade_ready": bool(hybrid_leverage_core_audit["trade_ready"]),
            "configuration_visible": bool(hybrid_leverage_core_audit["configuration_visible"]),
            "statistically_confirmed": bool(hybrid_leverage_core_audit["statistically_confirmed"]),
            "design_economic_passed_gate_count": int(
                hybrid_leverage_core_audit["design_economic_passed_gate_count"]
            ),
            "design_economic_required_gate_count": int(
                hybrid_leverage_core_audit["design_economic_required_gate_count"]
            ),
            "external_economic_passed_gate_count": int(
                hybrid_leverage_core_audit["external_economic_passed_gate_count"]
            ),
            "external_economic_required_gate_count": int(
                hybrid_leverage_core_audit["external_economic_required_gate_count"]
            ),
            "economic_passed_gate_count": int(
                hybrid_leverage_core_audit["economic_passed_gate_count"]
            ),
            "economic_required_gate_count": int(
                hybrid_leverage_core_audit["economic_required_gate_count"]
            ),
            "data_passed_gate_count": int(hybrid_leverage_core_audit["data_passed_gate_count"]),
            "data_required_gate_count": int(hybrid_leverage_core_audit["data_required_gate_count"]),
            "statistical_passed_gate_count": int(
                hybrid_leverage_core_audit["statistical_passed_gate_count"]
            ),
            "statistical_required_gate_count": int(
                hybrid_leverage_core_audit["statistical_required_gate_count"]
            ),
            "design_20_year_markets": 3,
            "external_years": 15,
            "evidence_classification": hybrid_leverage_core_audit["evidence_boundary"][
                "external_classification"
            ],
            "datasets": {
                key: clean_v21_dataset(data)
                for key, data in hybrid_leverage_core_audit["datasets"].items()
            },
            "paper_entry_decision": (
                "create_isolated_only"
                if hybrid_leverage_core_audit["paper_eligible"]
                else "do_not_create"
            ),
        }
        if not hybrid_leverage_core_audit["paper_eligible"]:
            midcap = hybrid_leverage_core_audit["datasets"]["midcap400_3x"]
            russell = hybrid_leverage_core_audit["datasets"]["russell2000_3x"]
            payload["limitations"].insert(
                0,
                "v21 永久保留 60% 核心，確認上升時約 120% 股票名目持倉比率、"
                "確認轉弱時約 60%。三組大型股 2 倍實作有 20 年已見診斷，"
                "新中小型股 3 倍外部期為 15 年；完整經濟門檻 "
                f"{hybrid_leverage_core_audit['economic_passed_gate_count']}/"
                f"{hybrid_leverage_core_audit['economic_required_gate_count']}，新外部 "
                f"{hybrid_leverage_core_audit['external_economic_passed_gate_count']}/"
                f"{hybrid_leverage_core_audit['external_economic_required_gate_count']}。"
                f"MidCap CAGR {midcap['strategy_metrics']['cagr']:.2%} / IJH "
                f"{midcap['benchmark_metrics']['core']['cagr']:.2%}，Russell 2000 "
                f"{russell['strategy_metrics']['cagr']:.2%} / IWM "
                f"{russell['benchmark_metrics']['core']['cagr']:.2%}；不建 Paper。",
            )
    if sector_capital_efficiency_audit is not None:
        audit = sector_capital_efficiency_audit

        def clean_v22_dataset(data: dict[str, Any]) -> dict[str, Any]:
            rolling = data["rolling_five_year_vs_core"]["summary"]
            return {
                "label": data["label"],
                "assets": data["assets"],
                "period": data["period"],
                "passed_gate_count": int(sum(data["economic_gates"].values())),
                "required_gate_count": len(data["economic_gates"]),
                "economic_gates": data["economic_gates"],
                "data_gate_passed": bool(data["data_gate_passed"]),
                "strategy_metrics": _clean_metric_set(data["strategy_metrics"]),
                "benchmark_metrics": {
                    "core": _clean_metric_set(data["benchmark_metrics"]["core"]),
                    "unlevered_same_assets": _clean_metric_set(
                        data["benchmark_metrics"]["unlevered_same_assets"]
                    ),
                },
                "rolling_five_year_vs_core": {
                    "windows": int(rolling["windows"]),
                    "cagr_win_fraction": float(rolling["cagr_win_fraction"]),
                    "median_cagr_difference": float(rolling["median_cagr_difference"]),
                    "worst_cagr_difference": float(rolling["worst_cagr_difference"]),
                },
                "fixed_halves_vs_core": {
                    key: {"cagr_difference": float(item["cagr_difference"])}
                    for key, item in data["fixed_halves_vs_core"].items()
                },
            }

        pooled = audit["pooled"]
        pooled_rolling = pooled["rolling_five_year_vs_core"]["summary"]
        payload.setdefault(
            "research_pipeline", {"primary_strategy": reference_audit["strategy_name"]}
        )["sector_capital_efficiency"] = {
            "name": audit["strategy_name"],
            "status": audit["status"],
            "paper_eligible": bool(audit["paper_eligible"]),
            "trade_ready": bool(audit["trade_ready"]),
            "configuration_visible": bool(audit["configuration_visible"]),
            "statistically_confirmed": bool(audit["statistically_confirmed"]),
            "individual_passed_gate_count": int(audit["individual_passed_gate_count"]),
            "individual_required_gate_count": int(audit["individual_required_gate_count"]),
            "individual_pass_count_by_gate": audit["individual_pass_count_by_gate"],
            "individual_pass_count_by_dataset": audit["individual_pass_count_by_dataset"],
            "consistency_gates": audit["consistency_gates"],
            "economic_passed_gate_count": int(audit["economic_passed_gate_count"]),
            "economic_required_gate_count": int(audit["economic_required_gate_count"]),
            "data_passed_gate_count": int(audit["data_passed_gate_count"]),
            "data_required_gate_count": int(audit["data_required_gate_count"]),
            "statistical_passed_gate_count": int(audit["statistical_passed_gate_count"]),
            "statistical_required_gate_count": int(audit["statistical_required_gate_count"]),
            "external_years": float(audit["evidence_boundary"]["external_years"]),
            "evidence_classification": audit["evidence_boundary"]["classification"],
            "protocol_sha256": audit["protocol"]["sha256"],
            "datasets": {key: clean_v22_dataset(data) for key, data in audit["datasets"].items()},
            "pooled": {
                "strategy_metrics": _clean_metric_set(pooled["strategy_metrics"]),
                "core_metrics": _clean_metric_set(pooled["core_metrics"]),
                "unlevered_same_assets_metrics": _clean_metric_set(
                    pooled["unlevered_same_assets_metrics"]
                ),
                "passed_gate_count": int(sum(pooled["economic_gates"].values())),
                "required_gate_count": len(pooled["economic_gates"]),
                "economic_gates": pooled["economic_gates"],
                "rolling_five_year_vs_core": {
                    "windows": int(pooled_rolling["windows"]),
                    "cagr_win_fraction": float(pooled_rolling["cagr_win_fraction"]),
                    "median_cagr_difference": float(pooled_rolling["median_cagr_difference"]),
                    "worst_cagr_difference": float(pooled_rolling["worst_cagr_difference"]),
                },
            },
            "statistics": {
                "newey_west_t": float(audit["statistical_details"]["newey_west"]["t_stat"]),
                "probabilistic_sharpe_probability": float(
                    audit["statistical_details"]["probabilistic_sharpe"]["probability"]
                ),
                "global_deflated_sharpe_probability": float(
                    audit["statistical_details"]["global_deflated_sharpe"]["probability"]
                ),
                "global_search_trials": int(audit["protocol"]["global_search_trials"]),
            },
        }
        if not audit["paper_eligible"]:
            payload["limitations"].insert(
                0,
                "v22 九產業完整期 CAGR 全數勝普通 ETF，但五年滾動有效勝率沒有一組達 60%，等權也只有 "
                f"{pooled_rolling['cagr_win_fraction']:.1%}；經濟入口 "
                f"{audit['economic_passed_gate_count']}/{audit['economic_required_gate_count']}、"
                f"統計 {audit['statistical_passed_gate_count']}/"
                f"{audit['statistical_required_gate_count']}，不建 Paper、不顯示 50/25/25。",
            )
    if managed_futures_capital_efficiency_audit is not None:
        audit = managed_futures_capital_efficiency_audit
        long_data = audit["long_horizon"]
        kmlm = audit["kmlm_actual_bridge"]
        fmf = audit["fmf_cross_manager"]

        def clean_v23_period(data: dict[str, Any]) -> dict[str, Any]:
            rolling = data["rolling_five_year_vs_SPY"]["summary"]
            return {
                "period": data["period"],
                "strategy_metrics": _clean_metric_set(data["strategy_metrics"]),
                "spy_metrics": _clean_metric_set(data["benchmark_metrics"]["SPY"]),
                "fixed_halves_vs_spy": {
                    key: {"cagr_difference": float(item["cagr_difference"])}
                    for key, item in data["fixed_halves_vs_SPY"].items()
                },
                "rolling_five_year_vs_spy": {
                    "windows": int(rolling["windows"]),
                    "cagr_win_fraction": float(rolling["cagr_win_fraction"]),
                    "median_cagr_difference": float(rolling["median_cagr_difference"]),
                    "worst_cagr_difference": float(rolling["worst_cagr_difference"]),
                },
            }

        long_stats = audit["statistical_confirmation"]["long_vs_SPY"]
        payload.setdefault(
            "research_pipeline", {"primary_strategy": reference_audit["strategy_name"]}
        )["managed_futures_capital_efficiency"] = {
            "name": "v23 50% SSO／50% KMLM",
            "status": audit["status"],
            "paper_eligible": bool(audit["paper_eligible"]),
            "trade_ready": bool(audit["trade_ready"]),
            "signal_display_allowed": bool(audit["candidate"]["signal_display_allowed"]),
            "long_passed_gate_count": int(audit["long_passed_gate_count"]),
            "long_required_gate_count": int(audit["long_required_gate_count"]),
            "kmlm_bridge_passed_gate_count": int(audit["kmlm_bridge_passed_gate_count"]),
            "kmlm_bridge_required_gate_count": int(audit["kmlm_bridge_required_gate_count"]),
            "fmf_passed_gate_count": int(audit["fmf_passed_gate_count"]),
            "fmf_required_gate_count": int(audit["fmf_required_gate_count"]),
            "fmf_required_pass_count": int(audit["fmf_required_pass_count"]),
            "data_passed_gate_count": int(audit["data_passed_gate_count"]),
            "data_required_gate_count": int(audit["data_required_gate_count"]),
            "global_search_trials": int(audit["global_search_trials"]),
            "protocol_sha256": audit["protocol"]["sha256"],
            "evidence_classification": audit["evidence_boundary"]["classification"],
            "long_horizon": {
                **clean_v23_period(long_data),
                "economic_gates": long_data["economic_gates"],
                "cost_50bps_cagr_difference": float(long_data["cost_50bps"]["cagr_difference"]),
            },
            "kmlm_actual_bridge": {
                **clean_v23_period(kmlm),
                "entry_gates": kmlm["entry_gates"],
                "tracking": {
                    "monthly_return_correlation": float(
                        kmlm["tracking"]["monthly_return_correlation"]
                    ),
                    "annualized_geometric_tracking_gap": float(
                        kmlm["tracking"]["annualized_geometric_tracking_gap"]
                    ),
                },
            },
            "fmf_cross_manager": {
                **clean_v23_period(fmf),
                "entry_gates": fmf["entry_gates"],
            },
            "statistics": {
                "newey_west_t": float(long_stats["active_return_newey_west"]["t_stat"]),
                "probabilistic_sharpe_probability": float(
                    long_stats["active_probabilistic_sharpe"]["probability"]
                ),
                "global_deflated_sharpe_probability": float(
                    long_stats["active_global_deflated_sharpe"]["probability"]
                ),
            },
        }
        if not audit["paper_eligible"]:
            payload["limitations"].insert(
                0,
                "v23 50% SSO／50% KMLM 的 20 年代理把最大跌幅由 "
                f"{long_data['benchmark_metrics']['SPY']['max_drawdown']:.1%} 改善到 "
                f"{long_data['strategy_metrics']['max_drawdown']:.1%}，但 CAGR 只領先 "
                f"{long_data['strategy_metrics']['cagr'] - long_data['benchmark_metrics']['SPY']['cagr']:.2%}；"
                f"長期 {audit['long_passed_gate_count']}/{audit['long_required_gate_count']}、"
                f"KMLM {audit['kmlm_bridge_passed_gate_count']}/{audit['kmlm_bridge_required_gate_count']}、"
                f"FMF {audit['fmf_passed_gate_count']}/{audit['fmf_required_gate_count']}，不建 Paper、不顯示 50/50。",
            )
    if quality_momentum_factor_audit is not None:
        audit = quality_momentum_factor_audit
        academic = audit["academic_formal_20y"]
        ishares = audit["ishares_actual"]
        invesco = audit["invesco_cross_manager"]

        def clean_v24_period(data: dict[str, Any], benchmark_key: str) -> dict[str, Any]:
            rolling = data["rolling_five_year_vs_market"]["summary"]
            return {
                "period": data["period"],
                "strategy_metrics": _clean_metric_set(data["strategy_metrics"]),
                "market_metrics": _clean_metric_set(data["benchmark_metrics"][benchmark_key]),
                "fixed_halves_vs_market": {
                    key: {"cagr_difference": float(item["cagr_difference"])}
                    for key, item in data["fixed_halves_vs_market"].items()
                },
                "rolling_five_year_vs_market": {
                    "windows": int(rolling["windows"]),
                    "cagr_win_fraction": float(rolling["cagr_win_fraction"]),
                    "median_cagr_difference": float(rolling["median_cagr_difference"]),
                    "worst_cagr_difference": float(rolling["worst_cagr_difference"]),
                },
                "cost_50bps_cagr_difference": float(data["cost_50bps"]["cagr_difference"]),
            }

        academic_stats = audit["statistical_confirmation"]["academic_formal_vs_market"]
        ishares_stats = audit["statistical_confirmation"]["ishares_actual_vs_SPY"]
        pipeline = payload.setdefault(
            "research_pipeline", {"primary_strategy": reference_audit["strategy_name"]}
        )
        pipeline["quality_momentum_factor"] = {
            "name": "v24 50% QUAL／50% MTUM",
            "status": audit["status"],
            "paper_eligible": bool(audit["paper_eligible"]),
            "trade_ready": bool(audit["trade_ready"]),
            "signal_display_allowed": bool(audit["candidate"]["signal_display_allowed"]),
            "academic_passed_gate_count": int(audit["long_passed_gate_count"]),
            "academic_required_gate_count": int(audit["long_required_gate_count"]),
            "ishares_passed_gate_count": int(audit["ishares_passed_gate_count"]),
            "ishares_required_gate_count": int(audit["ishares_required_gate_count"]),
            "invesco_passed_gate_count": int(audit["invesco_passed_gate_count"]),
            "invesco_required_gate_count": int(audit["invesco_required_gate_count"]),
            "invesco_required_pass_count": int(audit["invesco_required_pass_count"]),
            "data_passed_gate_count": int(audit["data_passed_gate_count"]),
            "data_required_gate_count": int(audit["data_required_gate_count"]),
            "global_search_trials": int(audit["global_search_trials"]),
            "protocol_sha256": audit["protocol"]["sha256"],
            "evidence_classification": audit["evidence_boundary"]["classification"],
            "academic_formal_20y": {
                **clean_v24_period(academic, "MARKET"),
                "economic_gates": academic["economic_gates"],
            },
            "ishares_actual": {
                **clean_v24_period(ishares, "SPY"),
                "entry_gates": ishares["entry_gates"],
                "quality_metrics": _clean_metric_set(ishares["benchmark_metrics"]["QUAL"]),
                "momentum_metrics": _clean_metric_set(ishares["benchmark_metrics"]["MTUM"]),
            },
            "invesco_cross_manager": {
                **clean_v24_period(invesco, "SPY"),
                "entry_gates": invesco["entry_gates"],
            },
            "statistics": {
                "academic_newey_west_t": float(
                    academic_stats["active_return_newey_west"]["t_stat"]
                ),
                "academic_global_deflated_sharpe_probability": float(
                    academic_stats["active_global_deflated_sharpe"]["probability"]
                ),
                "ishares_newey_west_t": float(ishares_stats["active_return_newey_west"]["t_stat"]),
                "ishares_global_deflated_sharpe_probability": float(
                    ishares_stats["active_global_deflated_sharpe"]["probability"]
                ),
            },
        }
        if not audit["paper_eligible"]:
            payload["limitations"].insert(
                0,
                "v24 學術品質＋動能 20 年通過 "
                f"{audit['long_passed_gate_count']}/{audit['long_required_gate_count']}，但可買的 QUAL／MTUM 只有 "
                f"{audit['ishares_passed_gate_count']}/{audit['ishares_required_gate_count']}、"
                f"SPHQ／PDP 跨管理人 {audit['invesco_passed_gate_count']}/{audit['invesco_required_gate_count']}；"
                "學術代理不是實際 ETF，不建 Paper、不顯示 50/50。",
            )
    if growth_gold_diversification_audit is not None:
        audit = growth_gold_diversification_audit

        def clean_v25_underwater(data: dict[str, Any]) -> dict[str, Any]:
            return {
                "max_underwater_months": int(data["max_underwater_months"]),
                "current_drawdown": float(data["current_drawdown"]),
                "deepest_episode": data["deepest_episode"],
                "longest_episode": data["longest_episode"],
            }

        def clean_v25_diagnostics(data: dict[str, Any]) -> dict[str, Any]:
            cleaned = {
                "used_for_frozen_entry_gate": bool(data["used_for_frozen_entry_gate"]),
                "portfolio_underwater": clean_v25_underwater(data["portfolio_underwater"]),
                "relative_wealth_underwater": {
                    label: clean_v25_underwater(row)
                    for label, row in data["relative_wealth_underwater"].items()
                },
                "rolling_five_year_entry_timing_risk": data["rolling_five_year_entry_timing_risk"],
            }
            if "paired_moving_block_bootstrap" in data:
                cleaned["paired_moving_block_bootstrap"] = data["paired_moving_block_bootstrap"]
            return cleaned

        def clean_v25_path(data: dict[str, Any]) -> dict[str, Any]:
            rolling = data["rolling_five_year_vs_SPY"]["summary"]
            growth_rolling = data["rolling_five_year_vs_growth"]["summary"]
            matched_rolling = data["rolling_five_year_vs_matched"]["summary"]
            return {
                "period": data["period"],
                "implementation": data["implementation"],
                "strategy_metrics": _clean_metric_set(data["strategy_metrics"]),
                "spy_metrics": _clean_metric_set(data["benchmark_metrics"]["SPY"]),
                "growth_metrics": _clean_metric_set(data["benchmark_metrics"]["growth"]),
                "matched_metrics": _clean_metric_set(
                    data["benchmark_metrics"]["matched_80_growth_20_SHY"]
                ),
                "passed_gate_count": int(data["passed_gate_count"]),
                "required_gate_count": int(data["required_gate_count"]),
                "required_pass_count": int(data["required_pass_count"]),
                "entry_gates": data["entry_gates"],
                "cost_50bps_cagr_difference_vs_spy": float(data["cost_50bps"]["cagr_difference"]),
                "fixed_halves_vs_spy": {
                    key: {"cagr_difference": float(item["cagr_difference"])}
                    for key, item in data["fixed_halves_vs_SPY"].items()
                },
                "fixed_halves_vs_growth": {
                    key: {"cagr_difference": float(item["cagr_difference"])}
                    for key, item in data["fixed_halves_vs_growth"].items()
                },
                "rolling_five_year_vs_spy": {
                    "windows": int(rolling["windows"]),
                    "cagr_win_fraction": float(rolling["cagr_win_fraction"]),
                    "median_cagr_difference": float(rolling["median_cagr_difference"]),
                    "worst_cagr_difference": float(rolling["worst_cagr_difference"]),
                },
                "rolling_five_year_vs_matched": {
                    "windows": int(matched_rolling["windows"]),
                    "cagr_win_fraction": float(matched_rolling["cagr_win_fraction"]),
                    "median_cagr_difference": float(matched_rolling["median_cagr_difference"]),
                    "worst_cagr_difference": float(matched_rolling["worst_cagr_difference"]),
                },
                "rolling_five_year_vs_growth": {
                    "windows": int(growth_rolling["windows"]),
                    "cagr_win_fraction": float(growth_rolling["cagr_win_fraction"]),
                    "median_cagr_difference": float(growth_rolling["median_cagr_difference"]),
                    "worst_cagr_difference": float(growth_rolling["worst_cagr_difference"]),
                },
                "post_entry_diagnostics_not_used_for_frozen_gate": (
                    clean_v25_diagnostics(data["post_entry_diagnostics_not_used_for_frozen_gate"])
                ),
            }

        pooled = audit["pooled"]
        pooled_rolling = pooled["rolling_five_year_vs_SPY"]["summary"]
        pooled_growth_rolling = pooled["rolling_five_year_vs_growth"]["summary"]
        paper_bundle = None
        if (
            growth_gold_paper_state is not None
            and growth_gold_spy_paper_state is not None
            and growth_gold_matched_paper_state is not None
        ):
            paper_bundle = build_v25_paper_bundle(
                growth_gold_paper_state,
                growth_gold_spy_paper_state,
                growth_gold_matched_paper_state,
            )
        pipeline = payload.setdefault(
            "research_pipeline", {"primary_strategy": reference_audit["strategy_name"]}
        )
        forward_trade_ready = bool(
            audit["paper_eligible"]
            and audit["all_paths_passed"]
            and paper_bundle is not None
            and paper_bundle["forward_evidence"]["live_confirmed"]
        )
        pipeline["growth_gold_diversification"] = {
            "name": "v25 80% VUG／20% GLD",
            "status": audit["status"],
            "paper_eligible": bool(audit["paper_eligible"]),
            "paper_state_created": bool(audit["paper_state_created"]),
            "trade_ready": forward_trade_ready,
            "paper_signal_display_allowed": bool(audit["candidate"]["signal_display_allowed"]),
            "real_money_signal_display_allowed": forward_trade_ready,
            "all_paths_passed": bool(audit["all_paths_passed"]),
            "path_pass_rule": audit["path_pass_rule"],
            "paths": {label: clean_v25_path(data) for label, data in audit["paths"].items()},
            "pooled": {
                "period": pooled["period"],
                "strategy_metrics": _clean_metric_set(pooled["strategy_metrics"]),
                "spy_metrics": _clean_metric_set(pooled["spy_metrics"]),
                "growth_metrics": _clean_metric_set(pooled["growth_metrics"]),
                "matched_metrics": _clean_metric_set(pooled["matched_metrics"]),
                "passed_gate_count": int(pooled["passed_gate_count"]),
                "required_gate_count": int(pooled["required_gate_count"]),
                "entry_gates": pooled["entry_gates"],
                "cost_50bps_cagr_difference_vs_spy": float(
                    pooled["cost_50bps_cagr_difference_vs_SPY"]
                ),
                "fixed_halves_vs_spy": {
                    key: {"cagr_difference": float(item["cagr_difference"])}
                    for key, item in pooled["fixed_halves_vs_SPY"].items()
                },
                "fixed_halves_vs_growth": {
                    key: {"cagr_difference": float(item["cagr_difference"])}
                    for key, item in pooled["fixed_halves_vs_growth"].items()
                },
                "rolling_five_year_vs_spy": {
                    "windows": int(pooled_rolling["windows"]),
                    "cagr_win_fraction": float(pooled_rolling["cagr_win_fraction"]),
                    "median_cagr_difference": float(pooled_rolling["median_cagr_difference"]),
                    "worst_cagr_difference": float(pooled_rolling["worst_cagr_difference"]),
                },
                "rolling_five_year_vs_growth": {
                    "windows": int(pooled_growth_rolling["windows"]),
                    "cagr_win_fraction": float(pooled_growth_rolling["cagr_win_fraction"]),
                    "median_cagr_difference": float(
                        pooled_growth_rolling["median_cagr_difference"]
                    ),
                    "worst_cagr_difference": float(pooled_growth_rolling["worst_cagr_difference"]),
                },
                "tradeoff_vs_growth": {
                    "cagr_difference": float(pooled["comparison_vs_growth"]["cagr_difference"]),
                    "sharpe_difference": float(pooled["comparison_vs_growth"]["sharpe_difference"]),
                    "drawdown_improvement": float(
                        pooled["comparison_vs_growth"]["drawdown_improvement"]
                    ),
                },
                "post_entry_diagnostics_not_used_for_frozen_gate": (
                    clean_v25_diagnostics(pooled["post_entry_diagnostics_not_used_for_frozen_gate"])
                ),
                "statistics_vs_spy": {
                    "newey_west_t": float(
                        pooled["comparison_vs_SPY"]["active_return_newey_west"]["t_stat"]
                    ),
                    "probabilistic_sharpe_probability": float(
                        pooled["comparison_vs_SPY"]["active_probabilistic_sharpe"]["probability"]
                    ),
                    "global_deflated_sharpe_probability": float(
                        pooled["comparison_vs_SPY"]["active_global_deflated_sharpe"]["probability"]
                    ),
                },
                "statistics_vs_matched": {
                    "newey_west_t": float(
                        pooled["comparison_vs_matched"]["active_return_newey_west"]["t_stat"]
                    )
                },
            },
            "data_passed_gate_count": int(audit["data_passed_gate_count"]),
            "data_required_gate_count": int(audit["data_required_gate_count"]),
            "global_search_trials": int(audit["global_search_trials"]),
            "protocol_sha256": audit["protocol"]["sha256"],
            "evidence_classification": audit["evidence_boundary"]["classification"],
            "paper": paper_bundle,
        }
        payload["limitations"].insert(
            0,
            "v25 三條實際 20 年大型成長＋黃金路徑與彙總入口已通過，但相對 SPY 的 NW t 只有 "
            f"{pooled['comparison_vs_SPY']['active_return_newey_west']['t_stat']:.2f}；"
            f"年率化仍比三路徑純成長 ETF 彙總少 {abs(pooled['comparison_vs_growth']['cagr_difference']) * 100:.2f} 個百分點；"
            f"LIVE Paper 只有 {paper_bundle['forward_evidence']['forward_sessions'] if paper_bundle else 0} 個新增交易日。"
            "現在只顯示 Paper 80/20，不是實金指令。",
        )
    payload["readiness"] = evaluate_trade_readiness(payload, integrity_ok=True)
    payload = _localize_hk_finance_copy(payload)
    payload = _preserve_idempotent_generation_time(payload, paths)
    written: list[Path] = []
    for raw in paths:
        path = Path(raw)
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_name(f".{path.name}.tmp")
        temporary.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False),
            encoding="utf-8",
        )
        temporary.replace(path)
        written.append(path)
    return written
