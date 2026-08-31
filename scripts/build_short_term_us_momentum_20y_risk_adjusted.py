from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path
from textwrap import dedent
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.build_short_term_us_momentum_20y import (  # noqa: E402
    ATR_SESSIONS,
    EXCLUDED_SYMBOLS,
    FIRST_HALF,
    GAP_ATR_MULTIPLIER,
    MIN_ACCEPTED_SIGNALS,
    MOMENTUM_SESSIONS,
    SECOND_HALF,
    TOP_K,
    TREND_SESSIONS,
    _load_checked_snapshot,
    _panel_arrays,
    _prepare,
)
from scripts.build_short_term_us_momentum_20y import PROTOCOL as PARENT_PROTOCOL  # noqa: E402
from scripts.build_short_term_us_momentum_20y import (  # noqa: E402
    _build_schedule as _build_parent_schedule,
)
from usfddk.sec_insider import sha256_file  # noqa: E402
from usfddk.sec_insider_portfolio import (  # noqa: E402
    PORTFOLIO_BASELINE_SYMBOLS,
    PORTFOLIO_COST_SCENARIOS,
    PORTFOLIO_HOLDING_SESSIONS,
    PORTFOLIO_MIN_MEDIAN_DOLLAR_VOLUME_USD,
    PORTFOLIO_MIN_PRICE_USD,
    simulate_event_portfolio,
)

PROTOCOL = ROOT / "docs/SHORT_TERM_US_MOMENTUM_20Y_RISK_ADJUSTED_PROTOCOL.md"
PARENT_DEFAULT = ROOT / "artifacts/short_term_us_momentum_20y_diagnostic.json"
PARENT_ARTIFACT_SHA256 = "9abd15960162e18419654e9ff0aadd31c075defe38e7ea23709419b0044b26fa"
OUTPUT_DEFAULT = ROOT / "artifacts/short_term_us_momentum_20y_risk_adjusted_diagnostic.json"
REPORT_DEFAULT = ROOT / "docs/SHORT_TERM_US_MOMENTUM_20Y_RISK_ADJUSTED_REPORT.md"
SNAPSHOT_FILENAME = "snapshot_20260731_6a7ca6b8.zip"
SNAPSHOT_ARCHIVE_SHA256 = "d480fb82e712f06aabe0a98461e222344656b87022b8bda2cd7ccaa4c29ae88b"
SNAPSHOT_PANEL_SHA256 = "6a7ca6b83b1570007424daa46b0ff4e8fb4a655d39298a0f4f6d74c3b7ea3a66"
RISK_ADJUSTED_FORMULA = "3 * percentile(momentum20 / (ATR20 / close)) + percentile(trend60)"
SCORE_THRESHOLD = 2.0


def _pct(value: float) -> str:
    return f"{value:.2%}"


def _percentile_rank(values: np.ndarray) -> np.ndarray:
    order = np.argsort(values, kind="mergesort")
    ranked = np.empty(len(values), dtype=float)
    ranked[order] = (np.arange(len(values), dtype=float) + 1.0) / len(values)
    return ranked


def _load_parent(path: Path) -> dict[str, Any]:
    digest = sha256_file(path)
    if digest != PARENT_ARTIFACT_SHA256:
        raise ValueError(f"parent 20 年收據 SHA-256 漂移：{digest}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("status") != "post_hoc_us_momentum_20y_diagnostic":
        raise ValueError("parent 20 年 momentum diagnostic status 不符")
    decision = payload.get("decision")
    if (
        not isinstance(decision, dict)
        or decision.get("paper_authorized") is not False
        or decision.get("public_strategy_allowed") is not False
        or payload.get("regime_schedule", {}).get("accepted_count") != 1531
    ):
        raise ValueError("parent 未維持 research-only 或 accepted schedule 漂移")
    return payload


def _build_schedule(
    arrays: dict[str, Any],
    *,
    regime_gate: bool,
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    sessions: list[date] = arrays["dates"]
    symbols: list[str] = arrays["symbols"]
    close: np.ndarray = arrays["close"]
    open_: np.ndarray = arrays["open"]
    high: np.ndarray = arrays["high"]
    low: np.ndarray = arrays["low"]
    dollar_volume: np.ndarray = arrays["dollar_volume"]
    qqq_index = arrays["baseline_indices"]["QQQ"]
    positions = {day: index for index, day in enumerate(sessions)}
    active: dict[str, date] = {}
    candidates: list[dict[str, Any]] = []
    audit = {
        "signal_sessions": 0,
        "regime_off_sessions": 0,
        "missing_history_symbols": 0,
        "liquidity_rejected_symbols": 0,
        "nonfinite_risk_adjusted_symbols": 0,
        "no_eligible_candidates": 0,
        "capacity_rejected_candidates": 0,
        "gap_rejected_candidates": 0,
        "selected_candidates": 0,
    }
    stock_count = len(symbols)
    for index in range(TREND_SESSIONS, len(sessions) - 1):
        signal_day = sessions[index]
        entry_day = sessions[index + 1]
        audit["signal_sessions"] += 1
        for ticker, exit_day in list(active.items()):
            if entry_day > exit_day:
                del active[ticker]

        qqq_history = close[index - TREND_SESSIONS + 1 : index + 1, qqq_index]
        if not np.all(np.isfinite(qqq_history)):
            audit["regime_off_sessions"] += 1
            continue
        if regime_gate and not (
            qqq_history[-1] > qqq_history[-MOMENTUM_SESSIONS:].mean()
            and qqq_history[-1] > qqq_history.mean()
        ):
            audit["regime_off_sessions"] += 1
            continue

        history = close[index - TREND_SESSIONS : index + 1, :stock_count]
        liquidity_history = dollar_volume[index - MOMENTUM_SESSIONS : index, :stock_count]
        high_history = high[index - ATR_SESSIONS + 1 : index + 1, :stock_count]
        low_history = low[index - ATR_SESSIONS + 1 : index + 1, :stock_count]
        previous_closes = close[index - ATR_SESSIONS : index, :stock_count]
        valid = (
            np.all(np.isfinite(history), axis=0)
            & np.all(np.isfinite(liquidity_history), axis=0)
            & np.all(np.isfinite(high_history), axis=0)
            & np.all(np.isfinite(low_history), axis=0)
            & np.all(np.isfinite(previous_closes), axis=0)
            & np.isfinite(open_[index + 1, :stock_count])
        )
        median_volume = np.zeros(stock_count, dtype=float)
        valid_liquidity = np.all(np.isfinite(liquidity_history), axis=0)
        median_volume[valid_liquidity] = np.median(
            liquidity_history[:, valid_liquidity], axis=0
        )
        liquid = (
            valid
            & (close[index, :stock_count] >= PORTFOLIO_MIN_PRICE_USD)
            & (median_volume >= PORTFOLIO_MIN_MEDIAN_DOLLAR_VOLUME_USD)
        )
        audit["missing_history_symbols"] += int(np.sum(~valid))
        audit["liquidity_rejected_symbols"] += int(np.sum(valid & ~liquid))
        if not np.any(liquid):
            audit["no_eligible_candidates"] += 1
            continue

        momentum = close[index, :stock_count] / close[index - MOMENTUM_SESSIONS, :stock_count] - 1.0
        trend = close[index, :stock_count] / close[
            index - TREND_SESSIONS + 1 : index + 1, :stock_count
        ].mean(axis=0) - 1.0
        true_range = np.maximum.reduce(
            [
                high_history - low_history,
                np.abs(high_history - previous_closes),
                np.abs(low_history - previous_closes),
            ]
        )
        atr = true_range.mean(axis=0)
        volatility = atr / close[index, :stock_count]
        risk_adjusted = np.full(stock_count, np.nan, dtype=float)
        finite_volatility = np.isfinite(volatility) & (volatility > 0.0)
        risk_adjusted[finite_volatility] = momentum[finite_volatility] / volatility[
            finite_volatility
        ]
        gap = np.abs(open_[index + 1, :stock_count] / close[index, :stock_count] - 1.0)
        valid_ids = np.where(liquid & np.isfinite(risk_adjusted) & np.isfinite(trend))[0]
        audit["nonfinite_risk_adjusted_symbols"] += int(np.sum(liquid) - len(valid_ids))
        if len(valid_ids) == 0:
            audit["no_eligible_candidates"] += 1
            continue
        score = np.zeros(stock_count, dtype=float)
        score[valid_ids] = 3.0 * _percentile_rank(risk_adjusted[valid_ids]) + _percentile_rank(
            trend[valid_ids]
        )
        eligible = valid_ids[
            (score[valid_ids] >= SCORE_THRESHOLD)
            & (momentum[valid_ids] > 0.0)
            & (trend[valid_ids] > 0.0)
        ]
        eligible = eligible[np.argsort(-score[eligible], kind="mergesort")]
        if len(eligible) == 0:
            audit["no_eligible_candidates"] += 1
            continue
        room = TOP_K - len(active)
        if room <= 0:
            audit["capacity_rejected_candidates"] += len(eligible)
            continue
        exit_position = positions[entry_day] + PORTFOLIO_HOLDING_SESSIONS - 1
        if exit_position >= len(sessions):
            continue
        exit_day = sessions[exit_position]
        for symbol_index in eligible:
            if room <= 0:
                break
            ticker = symbols[symbol_index]
            if ticker in active:
                audit["capacity_rejected_candidates"] += 1
                continue
            if (
                not np.isfinite(atr[symbol_index])
                or atr[symbol_index] <= 0.0
                or gap[symbol_index]
                >= GAP_ATR_MULTIPLIER * atr[symbol_index] / close[index, symbol_index]
            ):
                audit["gap_rejected_candidates"] += 1
                continue
            active[ticker] = exit_day
            candidates.append(
                {
                    "ticker": ticker,
                    "available_session": entry_day.isoformat(),
                    "score": float(score[symbol_index]),
                    "signal_day": signal_day.isoformat(),
                    "atr": float(atr[symbol_index]),
                    "risk_adjusted_momentum": float(risk_adjusted[symbol_index]),
                }
            )
            audit["selected_candidates"] += 1
            room -= 1
    return candidates, audit


def _slice(signals: list[dict[str, Any]], window: tuple[date, date]) -> list[dict[str, Any]]:
    start, end = window
    return [
        signal
        for signal in signals
        if start <= date.fromisoformat(str(signal["signal_day"])) <= end
    ]


def _scenario(
    signals: list[dict[str, Any]],
    prices,
    cost_bps: float,
) -> dict[str, Any]:
    return {
        "all_period": simulate_event_portfolio(
            signals,
            prices,
            one_way_cost_bps=cost_bps,
            baseline_symbols=PORTFOLIO_BASELINE_SYMBOLS,
        ),
        "fixed_halves": {
            "2004-01-01_2014-12-31": simulate_event_portfolio(
                _slice(signals, FIRST_HALF),
                prices,
                one_way_cost_bps=cost_bps,
                baseline_symbols=PORTFOLIO_BASELINE_SYMBOLS,
            ),
            "2015-01-01_2026-06-30": simulate_event_portfolio(
                _slice(signals, SECOND_HALF),
                prices,
                one_way_cost_bps=cost_bps,
                baseline_symbols=PORTFOLIO_BASELINE_SYMBOLS,
            ),
        },
    }


def _build_report(payload: dict[str, Any]) -> str:
    ten = payload["cost_scenarios"]["10"]["all_period"]
    twenty_five = payload["cost_scenarios"]["25"]["all_period"]
    fifty = payload["cost_scenarios"]["50"]["all_period"]
    first = payload["cost_scenarios"]["50"]["fixed_halves"]["2004-01-01_2014-12-31"]
    second = payload["cost_scenarios"]["50"]["fixed_halves"]["2015-01-01_2026-06-30"]
    parent = payload["parent_reference"]["cost_25bps"]
    gates = payload["decision"]["gates"]
    return dedent(
        f"""\
        # 美股短線 20 年風險調整動量研究報告

        版本：v1｜狀態：`{payload['decision']['strategy_status']}`｜用途：單一機制診斷，並非買入名單、Paper 指令或投資建議。

        ## 結論先行

        本輪只把 20 日回報除以當日 ATR20 作排名，其他訊號、QQQ regime、Top-7、D+1 開市、
        20 日到期、gap filter、成本及 ETF 基準完全沿用母策略。結果不會改寫母策略或流入公開頁面。

        - 風險調整版本接受 {ten['signal_count']} 宗訊號；10／25／50 bps CAGR 為 {_pct(ten['portfolio']['cagr'])}／{_pct(twenty_five['portfolio']['cagr'])}／{_pct(fifty['portfolio']['cagr'])}。
        - 25 bps 母策略 CAGR 為 {_pct(parent['strategy_cagr'])}，QQQ 為 {_pct(parent['qqq_cagr'])}；本輪只作事後比較，不作參數選擇。
        - 50 bps 前段策略／QQQ CAGR 為 {_pct(first['portfolio']['cagr'])}／{_pct(first['QQQ']['cagr'])}；後段為 {_pct(second['portfolio']['cagr'])}／{_pct(second['QQQ']['cagr'])}。

        ## 結果

        | 成本 | 訊號 | 策略 CAGR | QQQ CAGR | SPY CAGR | IWM CAGR | 策略最大跌幅 | QQQ 最大跌幅 | Sharpe |
        |---:|---:|---:|---:|---:|---:|---:|---:|---:|
        | 10 bps | {ten['signal_count']} | {_pct(ten['portfolio']['cagr'])} | {_pct(ten['QQQ']['cagr'])} | {_pct(ten['baselines']['SPY']['cagr'])} | {_pct(ten['baselines']['IWM']['cagr'])} | {_pct(ten['portfolio']['max_drawdown'])} | {_pct(ten['QQQ']['max_drawdown'])} | {ten['portfolio']['sharpe']:.2f} |
        | 25 bps | {twenty_five['signal_count']} | {_pct(twenty_five['portfolio']['cagr'])} | {_pct(twenty_five['QQQ']['cagr'])} | {_pct(twenty_five['baselines']['SPY']['cagr'])} | {_pct(twenty_five['baselines']['IWM']['cagr'])} | {_pct(twenty_five['portfolio']['max_drawdown'])} | {_pct(twenty_five['QQQ']['max_drawdown'])} | {twenty_five['portfolio']['sharpe']:.2f} |
        | 50 bps | {fifty['signal_count']} | {_pct(fifty['portfolio']['cagr'])} | {_pct(fifty['QQQ']['cagr'])} | {_pct(fifty['baselines']['SPY']['cagr'])} | {_pct(fifty['baselines']['IWM']['cagr'])} | {_pct(fifty['portfolio']['max_drawdown'])} | {_pct(fifty['QQQ']['max_drawdown'])} | {fifty['portfolio']['sharpe']:.2f} |

        ## 決策閘門

        - 通過：{sum(gates.values())}/{len(gates)}。
        - 未通過：{', '.join(key for key, value in gates.items() if not value) or '無'}。
        - 年率化換手（25 bps）：{twenty_five['annualized_turnover']:.2f}x。

        所有結果只寫入研究 log；`Paper=false`、`public_strategy_allowed=false`、實金 US$0。
        success-only 網頁維持「今天不下單」，不呈現本輪失敗結果或任何歷史最後權重。

        機器收據：`artifacts/short_term_us_momentum_20y_risk_adjusted_diagnostic.json`；協議：
        `docs/SHORT_TERM_US_MOMENTUM_20Y_RISK_ADJUSTED_PROTOCOL.md`。
        """
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="建立 20 年風險調整動量診斷；不產生交易指令"
    )
    parser.add_argument("--snapshot", type=Path, default=ROOT / "artifacts" / SNAPSHOT_FILENAME)
    parser.add_argument("--parent", type=Path, default=PARENT_DEFAULT)
    parser.add_argument("--output", type=Path, default=OUTPUT_DEFAULT)
    parser.add_argument("--report", type=Path, default=REPORT_DEFAULT)
    args = parser.parse_args()

    parent = _load_parent(args.parent)
    panel, manifest, archive_sha256 = _load_checked_snapshot(args.snapshot)
    arrays = _panel_arrays(panel)
    parent_candidates, _ = _build_parent_schedule(arrays, regime_gate=True)
    regime_candidates, regime_audit = _build_schedule(arrays, regime_gate=True)
    control_candidates, control_audit = _build_schedule(arrays, regime_gate=False)
    regime_signals, regime_skipped = _prepare(regime_candidates, arrays)
    control_signals, control_skipped = _prepare(control_candidates, arrays)
    parent_pairs = {
        (row["ticker"], row["available_session"]) for row in parent_candidates
    }
    risk_adjusted_pairs = {
        (row["ticker"], row["available_session"]) for row in regime_candidates
    }
    cost_scenarios = {
        str(int(cost)): _scenario(regime_signals, arrays["prices"], cost)
        for cost in PORTFOLIO_COST_SCENARIOS
    }
    control_cost_scenarios = {
        str(int(cost)): _scenario(control_signals, arrays["prices"], cost)
        for cost in PORTFOLIO_COST_SCENARIOS
    }
    ten = cost_scenarios["10"]["all_period"]
    twenty_five = cost_scenarios["25"]["all_period"]
    fifty = cost_scenarios["50"]["all_period"]
    first_fifty = cost_scenarios["50"]["fixed_halves"]["2004-01-01_2014-12-31"]
    second_fifty = cost_scenarios["50"]["fixed_halves"]["2015-01-01_2026-06-30"]
    parent_25 = parent["cost_scenarios"]["25"]["all_period"]
    gates = {
        "minimum_500_accepted_signals": ten["signal_count"] >= MIN_ACCEPTED_SIGNALS,
        "cagr_beats_qqq_at_10bps": ten["portfolio"]["cagr"] > ten["QQQ"]["cagr"],
        "cagr_beats_qqq_at_25bps": twenty_five["portfolio"]["cagr"]
        > twenty_five["QQQ"]["cagr"],
        "cagr_beats_qqq_at_50bps": fifty["portfolio"]["cagr"] > fifty["QQQ"]["cagr"],
        "both_fixed_halves_beat_qqq_at_50bps": (
            first_fifty["portfolio"]["cagr"] > first_fifty["QQQ"]["cagr"]
            and second_fifty["portfolio"]["cagr"] > second_fifty["QQQ"]["cagr"]
        ),
        "max_drawdown_no_worse_than_qqq_at_10bps": ten["portfolio"]["max_drawdown"]
        >= ten["QQQ"]["max_drawdown"],
    }
    payload: dict[str, Any] = {
        "schema_version": 1,
        "status": "post_hoc_us_momentum_20y_risk_adjusted_diagnostic",
        "protocol": {
            "path": str(PROTOCOL.relative_to(ROOT)),
            "sha256": sha256_file(PROTOCOL),
            "parent_protocol_path": str(PARENT_PROTOCOL.relative_to(ROOT)),
            "parent_protocol_sha256": sha256_file(PARENT_PROTOCOL),
            "risk_adjusted_formula": RISK_ADJUSTED_FORMULA,
            "momentum_sessions": MOMENTUM_SESSIONS,
            "trend_sessions": TREND_SESSIONS,
            "atr_sessions": ATR_SESSIONS,
            "score_threshold": SCORE_THRESHOLD,
            "top_k": TOP_K,
            "gap_atr_multiplier": GAP_ATR_MULTIPLIER,
            "holding_sessions": PORTFOLIO_HOLDING_SESSIONS,
            "baseline_symbols": list(PORTFOLIO_BASELINE_SYMBOLS),
            "cost_scenarios_bps": list(PORTFOLIO_COST_SCENARIOS),
            "min_price_usd": PORTFOLIO_MIN_PRICE_USD,
            "min_median_dollar_volume_usd": PORTFOLIO_MIN_MEDIAN_DOLLAR_VOLUME_USD,
        },
        "source": {
            "snapshot_filename": args.snapshot.name,
            "archive_sha256": archive_sha256,
            "panel_sha256": manifest["panel_sha256"],
            "manifest_start": manifest["start"],
            "manifest_end": manifest["end"],
            "rows": manifest["rows"],
            "tickers": list(manifest["tickers"]),
            "contract": manifest.get("contract"),
        },
        "universe": {
            "stock_symbols": arrays["symbols"],
            "stock_symbol_count": len(arrays["symbols"]),
            "excluded_symbols": sorted(EXCLUDED_SYMBOLS),
        },
        "parent_reference": {
            "artifact_sha256": PARENT_ARTIFACT_SHA256,
            "status": parent["status"],
            "accepted_count": parent["regime_schedule"]["accepted_count"],
            "parent_schedule_candidate_count": len(parent_candidates),
            "risk_adjusted_schedule_candidate_count": len(regime_candidates),
            "schedule_pair_overlap_count": len(parent_pairs & risk_adjusted_pairs),
            "schedule_pairs_only_parent": len(parent_pairs - risk_adjusted_pairs),
            "schedule_pairs_only_risk_adjusted": len(risk_adjusted_pairs - parent_pairs),
            "cost_25bps": {
                "strategy_cagr": parent_25["portfolio"]["cagr"],
                "qqq_cagr": parent_25["QQQ"]["cagr"],
                "max_drawdown": parent_25["portfolio"]["max_drawdown"],
            },
        },
        "regime_schedule": {
            "candidate_count": len(regime_candidates),
            "accepted_count": len(regime_signals),
            "audit": regime_audit,
            "prepare_skipped": regime_skipped,
        },
        "control_schedule": {
            "candidate_count": len(control_candidates),
            "accepted_count": len(control_signals),
            "audit": control_audit,
            "prepare_skipped": control_skipped,
        },
        "cost_scenarios": cost_scenarios,
        "control_cost_scenarios": control_cost_scenarios,
        "decision": {
            "strategy_status": "research_candidate_only",
            "diagnostic_status": "risk_adjusted_momentum_only_internal_log",
            "gate_summary": {
                "passed": sum(gates.values()),
                "total": len(gates),
                "all_passed": all(gates.values()),
            },
            "gates": gates,
            "formal_stock_backtest_completed": False,
            "paper_authorized": False,
            "public_strategy_allowed": False,
            "real_money_action_usd": 0,
            "reason": "This is a single post-hoc score isolation on a current-watchlist survivor snapshot; no result can authorize Paper or public action.",
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(_build_report(payload), encoding="utf-8")
    print(
        json.dumps(
            {
                "status": payload["status"],
                "accepted_count": len(regime_signals),
                "portfolio_cagr_10bps": ten["portfolio"]["cagr"],
                "qqq_cagr_10bps": ten["QQQ"]["cagr"],
                "gates": payload["decision"]["gate_summary"],
                "output": str(args.output),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
