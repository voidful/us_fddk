"""Build the deliberately tiny data contract consumed by the public site.

The research payloads contain diagnostics, failed candidates, Paper state and
other internal evidence.  They are inputs to this allow-list only; the browser
must never import them directly.  A candidate is copied into the public
contract only after its explicit promotion gates are true.
"""

from __future__ import annotations

import math
from datetime import UTC, datetime
from typing import Any

_ACCOUNT_INTEGRITY_GATES = (
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


def _all_true(values: Any) -> bool:
    return isinstance(values, dict) and bool(values) and all(value is True for value in values.values())


def _percent(value: Any, digits: int = 1) -> str:
    return f"{float(value):.{digits}%}"


def _money(value: Any) -> str:
    return f"US${float(value):,.0f}"


def _finite_number(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return number if math.isfinite(number) else None


def _non_negative_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    try:
        number = int(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return number if number >= 0 else None


def _allocation(weights: Any) -> tuple[str, str] | None:
    if not isinstance(weights, dict):
        return None
    clean: dict[str, float] = {}
    for ticker, weight in weights.items():
        if not isinstance(ticker, str):
            continue
        try:
            amount = float(weight)
        except (TypeError, ValueError, OverflowError):
            continue
        if math.isfinite(amount) and amount > 0.0:
            clean[ticker] = amount
    if not clean:
        return None
    ordered = sorted(clean.items(), key=lambda item: (-item[1], item[0]))
    allocation = "／".join(f"{ticker} {weight:.0%}" for ticker, weight in ordered)
    example = "／".join(_money(1_000.0 * weight) for _, weight in ordered)
    return allocation, example


def _long_term_strategy(payload: dict[str, Any]) -> dict[str, Any] | None:
    readiness = payload.get("readiness")
    pipeline = payload.get("research_pipeline")
    if not isinstance(readiness, dict) or not isinstance(pipeline, dict):
        return None
    gates = readiness.get("gates")
    required = readiness.get("required_gate_count")
    passed = readiness.get("passed_gate_count")
    if not (
        isinstance(required, int)
        and isinstance(passed, int)
        and required == 11
        and passed == required
        and isinstance(gates, dict)
        and len(gates) == required
        and _all_true(gates)
        and readiness.get("trade_ready") is True
        and readiness.get("allocation_visible") is True
        and readiness.get("selected_strategy_key") == "growth_gold_diversification"
    ):
        return None
    latest = pipeline.get("growth_gold_diversification")
    if not isinstance(latest, dict):
        return None
    paper = latest.get("paper")
    forward = paper.get("forward_evidence") if isinstance(paper, dict) else None
    data_through = payload.get("data_through")
    if not (
        isinstance(paper, dict)
        and isinstance(forward, dict)
        and forward.get("as_of") == data_through
        and forward.get("integrity_violations") == 0
        and isinstance(forward.get("gates"), dict)
        and all(forward["gates"].get(name) is True for name in _ACCOUNT_INTEGRITY_GATES)
        and latest.get("trade_ready") is True
        and latest.get("real_money_signal_display_allowed") is True
        and forward.get("live_confirmed") is True
    ):
        return None
    pooled = latest.get("pooled")
    if not isinstance(pooled, dict):
        return None
    strategy_metrics = pooled.get("strategy_metrics")
    spy_metrics = pooled.get("spy_metrics")
    if not isinstance(strategy_metrics, dict) or not isinstance(spy_metrics, dict):
        return None
    strategy_cagr = _finite_number(strategy_metrics.get("cagr"))
    strategy_drawdown = _finite_number(strategy_metrics.get("max_drawdown"))
    spy_cagr = _finite_number(spy_metrics.get("cagr"))
    spy_drawdown = _finite_number(spy_metrics.get("max_drawdown"))
    forward_sessions = _non_negative_int(forward.get("forward_sessions"))
    filled_rebalances = _non_negative_int(forward.get("filled_rebalances"))
    if any(
        value is None
        for value in (
            strategy_cagr,
            strategy_drawdown,
            spy_cagr,
            spy_drawdown,
            forward_sessions,
            filled_rebalances,
        )
    ):
        return None
    pending = paper.get("pending_order")
    weights = pending.get("target_weights") if isinstance(pending, dict) else None
    if weights is None and isinstance(paper.get("holdings"), dict):
        weights = {
            ticker: position.get("weight")
            for ticker, position in paper["holdings"].items()
            if isinstance(position, dict)
        }
    allocation = _allocation(weights)
    if allocation is None:
        return None
    return {
        "verified": True,
        "key": "long-term",
        "horizon": "長線穩定",
        "name": str(latest.get("name", "已驗證長線策略")),
        "description": "固定規則、每月檢查；只在歷史、成本、風險及前瞻門檻全部通過後公開。",
        "action": (
            "下一個完成交易日按已凍結指令調整持倉"
            if pending
            else "今天不下單；維持現有持倉，等待下一個月末檢查"
        ),
        "allocation": allocation[0],
        "amount_example": allocation[1],
        "metrics": [
            {
                "label": "20 年年率化回報",
                "value": _percent(strategy_cagr, 2),
                "comparison": f"SPY {_percent(spy_cagr, 2)}",
            },
            {
                "label": "最大跌幅",
                "value": _percent(strategy_drawdown),
                "comparison": f"SPY {_percent(spy_drawdown)}",
            },
            {
                "label": "前瞻交易日",
                "value": str(forward_sessions),
                "comparison": f"{filled_rebalances} 次完成換倉",
            },
        ],
    }


def _short_term_strategy(
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
    symbols = decision.get("public_symbols")
    action = decision.get("public_action")
    formal_runs = _non_negative_int(decision.get("formal_strategy_runs"))
    if not (
        actual.get("all_passed") is True
        and isinstance(actual.get("passed"), int)
        and isinstance(actual.get("total"), int)
        and actual["passed"] == actual["total"]
        and summary.get("all_passed") is True
        and isinstance(summary.get("passed"), int)
        and isinstance(summary.get("total"), int)
        and summary["passed"] == summary["total"]
        and decision.get("trade_ready") is True
        and decision.get("can_promote_from_this_round") is True
        and decision.get("new_strategy_created") is True
        and formal_runs is not None
        and formal_runs > 0
        and isinstance(action, str)
        and bool(action.strip())
        and isinstance(symbols, list)
        and bool(symbols)
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
                "value": f"{actual['passed']}/{actual['total']}",
                "comparison": "全部事前門檻通過",
            },
            {
                "label": "策略運行",
                "value": str(formal_runs),
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
    """Copy only promoted strategies into the browser-facing contract."""

    strategies: list[dict[str, Any]] = []
    long_term = _long_term_strategy(payload)
    if long_term is not None:
        strategies.append(long_term)
    short_term = _short_term_strategy(formal_readiness, short_term_overlay)
    if short_term is not None:
        strategies.append(short_term)
    freshness = payload.get("freshness")
    freshness = freshness if isinstance(freshness, dict) else {}
    data_through = str(payload.get("data_through", ""))
    today_action = (
        "今天不下單"
        if not strategies or all(item["action"].startswith("今天不下單") for item in strategies)
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
            "；".join(item["action"] for item in strategies)
            if strategies
            else "不建立新倉，保留現金並等待下一個完成交易日的正式驗證。"
        ),
        "strategies": strategies,
        "policy": "首頁只顯示已驗證、可執行的策略；完整研究記錄與機器收據另存於 GitHub。",
        "disclaimer": "研究與教育用途，不構成投資建議；不保證未來跑贏 SPY 或任何 ETF。",
    }


def build_public_decision_audit_log(
    payload: dict[str, Any],
    *,
    formal_readiness: dict[str, Any] | None = None,
    short_term_overlay: dict[str, Any] | None = None,
    public_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Record promotion decisions without copying diagnostics to the public JSON."""

    readiness = payload.get("readiness")
    actual_formal = (
        formal_readiness.get("actual_formal_readiness")
        if isinstance(formal_readiness, dict)
        else None
    )
    long_term_promoted = bool(public_payload and any(
        item.get("key") == "long-term" for item in public_payload.get("strategies", [])
    ))
    short_term_promoted = bool(public_payload and any(
        item.get("key") == "short-term" for item in public_payload.get("strategies", [])
    ))
    return {
        "schema_version": 1,
        "visibility": "internal-research-log",
        "not_for_public_decision_page": True,
        "data_through": payload.get("data_through"),
        "candidate_audit": [
            {
                "key": "long-term",
                "status": "promoted" if long_term_promoted else "not_promoted",
                "reason_codes": [] if long_term_promoted else [
                    "long_term_readiness_incomplete"
                    if not isinstance(readiness, dict) or readiness.get("trade_ready") is not True
                    else "long_term_forward_integrity_incomplete"
                ],
            },
            {
                "key": "short-term",
                "status": "promoted" if short_term_promoted else "not_promoted",
                "reason_codes": [] if short_term_promoted else [
                    "formal_readiness_incomplete"
                    if not isinstance(actual_formal, dict)
                    or actual_formal.get("all_passed") is not True
                    else "short_term_overlay_incomplete"
                ],
            },
        ],
        "public_strategy_count": len(public_payload.get("strategies", [])) if public_payload else 0,
        "paper_authorized": False,
        "real_money_action_usd": 0,
    }
