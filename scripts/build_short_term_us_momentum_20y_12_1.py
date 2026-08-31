from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path
from textwrap import dedent
from typing import Any

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.build_short_term_us_momentum_20y import (  # noqa: E402
    EXCLUDED_SYMBOLS,
    _load_checked_snapshot,
    _panel_arrays,
    _prepare,
    _scenario,
)
from scripts.build_short_term_us_momentum_20y import PROTOCOL as PARENT_PROTOCOL  # noqa: E402
from usfddk.sec_insider import sha256_file  # noqa: E402
from usfddk.sec_insider_portfolio import (  # noqa: E402
    PORTFOLIO_BASELINE_SYMBOLS,
    PORTFOLIO_COST_SCENARIOS,
    PORTFOLIO_HOLDING_SESSIONS,
    PORTFOLIO_MIN_MEDIAN_DOLLAR_VOLUME_USD,
    PORTFOLIO_MIN_PRICE_USD,
)
from usfddk.short_term_high_return import _completed_period_mask  # noqa: E402

PROTOCOL = ROOT / "docs/SHORT_TERM_US_MOMENTUM_20Y_12_1_PROTOCOL.md"
PARENT_DEFAULT = ROOT / "artifacts/short_term_us_momentum_20y_diagnostic.json"
PARENT_ARTIFACT_SHA256 = "9abd15960162e18419654e9ff0aadd31c075defe38e7ea23709419b0044b26fa"
OUTPUT_DEFAULT = ROOT / "artifacts/short_term_us_momentum_20y_12_1_diagnostic.json"
REPORT_DEFAULT = ROOT / "docs/SHORT_TERM_US_MOMENTUM_20Y_12_1_REPORT.md"
SNAPSHOT_FILENAME = "snapshot_20260731_6a7ca6b8.zip"
SNAPSHOT_ARCHIVE_SHA256 = "d480fb82e712f06aabe0a98461e222344656b87022b8bda2cd7ccaa4c29ae88b"
SNAPSHOT_PANEL_SHA256 = "6a7ca6b83b1570007424daa46b0ff4e8fb4a655d39298a0f4f6d74c3b7ea3a66"
LOOKBACK_SESSIONS = 252
RECENT_SKIP_SESSIONS = 21
TREND_SESSIONS = 60
MOMENTUM_SESSIONS = 20
ATR_SESSIONS = 20
TOP_K = 7
SCORE_THRESHOLD = 2.0
GAP_ATR_MULTIPLIER = 1.5
MIN_ACCEPTED_SIGNALS = 500


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
        raise ValueError("parent 20 年動量收據 status 不符")
    if payload.get("regime_schedule", {}).get("accepted_count") != 1531:
        raise ValueError("parent accepted schedule 漂移")
    decision = payload.get("decision", {})
    if decision.get("paper_authorized") is not False or decision.get(
        "public_strategy_allowed"
    ) is not False:
        raise ValueError("parent promotion boundary 漂移")
    return payload


def _build_schedule(
    arrays: dict[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    sessions: list[date] = arrays["dates"]
    index = pd.DatetimeIndex(pd.to_datetime(sessions)).normalize()
    weekly_mask = _completed_period_mask(index, "weekly").to_numpy(dtype=bool)
    symbols: list[str] = arrays["symbols"]
    close: np.ndarray = arrays["close"]
    open_: np.ndarray = arrays["open"]
    high: np.ndarray = arrays["high"]
    low: np.ndarray = arrays["low"]
    dollar_volume: np.ndarray = arrays["dollar_volume"]
    qqq_index = arrays["baseline_indices"]["QQQ"]
    positions = {day: position for position, day in enumerate(sessions)}
    active: dict[str, date] = {}
    candidates: list[dict[str, Any]] = []
    audit = {
        "weekly_signal_sessions": 0,
        "regime_off_sessions": 0,
        "insufficient_history_sessions": 0,
        "missing_history_symbols": 0,
        "liquidity_rejected_symbols": 0,
        "no_eligible_candidates": 0,
        "capacity_rejected_candidates": 0,
        "gap_rejected_candidates": 0,
        "selected_candidates": 0,
    }
    stock_count = len(symbols)
    for signal_index in np.flatnonzero(weekly_mask):
        signal_index = int(signal_index)
        if signal_index + PORTFOLIO_HOLDING_SESSIONS >= len(sessions):
            continue
        audit["weekly_signal_sessions"] += 1
        entry_day = sessions[signal_index + 1]
        for ticker, exit_day in list(active.items()):
            if entry_day > exit_day:
                del active[ticker]
        if signal_index < LOOKBACK_SESSIONS:
            audit["insufficient_history_sessions"] += 1
            continue
        qqq_history = close[
            signal_index - TREND_SESSIONS + 1 : signal_index + 1, qqq_index
        ]
        if not np.all(np.isfinite(qqq_history)) or not (
            qqq_history[-1] > qqq_history[-MOMENTUM_SESSIONS:].mean()
            and qqq_history[-1] > qqq_history.mean()
        ):
            audit["regime_off_sessions"] += 1
            continue
        history = close[
            signal_index - TREND_SESSIONS : signal_index + 1, :stock_count
        ]
        liquidity_history = dollar_volume[
            signal_index - MOMENTUM_SESSIONS : signal_index, :stock_count
        ]
        high_history = high[
            signal_index - ATR_SESSIONS + 1 : signal_index + 1, :stock_count
        ]
        low_history = low[
            signal_index - ATR_SESSIONS + 1 : signal_index + 1, :stock_count
        ]
        previous_closes = close[
            signal_index - ATR_SESSIONS : signal_index, :stock_count
        ]
        valid = (
            np.all(np.isfinite(history), axis=0)
            & np.all(np.isfinite(liquidity_history), axis=0)
            & np.all(np.isfinite(high_history), axis=0)
            & np.all(np.isfinite(low_history), axis=0)
            & np.all(np.isfinite(previous_closes), axis=0)
            & np.isfinite(open_[signal_index + 1, :stock_count])
            & np.isfinite(close[signal_index - LOOKBACK_SESSIONS, :stock_count])
        )
        median_volume = np.zeros(stock_count, dtype=float)
        valid_liquidity = np.all(np.isfinite(liquidity_history), axis=0)
        median_volume[valid_liquidity] = np.median(
            liquidity_history[:, valid_liquidity], axis=0
        )
        liquid = (
            valid
            & (close[signal_index, :stock_count] >= PORTFOLIO_MIN_PRICE_USD)
            & (median_volume >= PORTFOLIO_MIN_MEDIAN_DOLLAR_VOLUME_USD)
        )
        audit["missing_history_symbols"] += int(np.sum(~valid))
        audit["liquidity_rejected_symbols"] += int(np.sum(valid & ~liquid))
        if not np.any(liquid):
            audit["no_eligible_candidates"] += 1
            continue
        momentum = (
            close[signal_index - RECENT_SKIP_SESSIONS, :stock_count]
            / close[signal_index - LOOKBACK_SESSIONS, :stock_count]
            - 1.0
        )
        trend = (
            close[signal_index, :stock_count]
            / close[signal_index - TREND_SESSIONS + 1 : signal_index + 1, :stock_count].mean(
                axis=0
            )
            - 1.0
        )
        true_range = np.maximum.reduce(
            [
                high_history - low_history,
                np.abs(high_history - previous_closes),
                np.abs(low_history - previous_closes),
            ]
        )
        atr = true_range.mean(axis=0)
        gap = np.abs(
            open_[signal_index + 1, :stock_count]
            / close[signal_index, :stock_count]
            - 1.0
        )
        valid_ids = np.where(liquid & np.isfinite(momentum) & np.isfinite(trend))[0]
        if len(valid_ids) == 0:
            audit["no_eligible_candidates"] += 1
            continue
        score = np.zeros(stock_count, dtype=float)
        score[valid_ids] = 3.0 * _percentile_rank(momentum[valid_ids]) + _percentile_rank(
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
                >= GAP_ATR_MULTIPLIER * atr[symbol_index] / close[signal_index, symbol_index]
            ):
                audit["gap_rejected_candidates"] += 1
                continue
            active[ticker] = exit_day
            candidates.append(
                {
                    "ticker": ticker,
                    "available_session": entry_day.isoformat(),
                    "signal_day": sessions[signal_index].isoformat(),
                    "score": float(score[symbol_index]),
                    "momentum12_1": float(momentum[symbol_index]),
                    "trend60": float(trend[symbol_index]),
                    "atr": float(atr[symbol_index]),
                }
            )
            audit["selected_candidates"] += 1
            room -= 1
    return candidates, audit


def _build_report(payload: dict[str, Any]) -> str:
    ten = payload["cost_scenarios"]["10"]["all_period"]
    twenty_five = payload["cost_scenarios"]["25"]["all_period"]
    fifty = payload["cost_scenarios"]["50"]["all_period"]
    first = payload["cost_scenarios"]["50"]["fixed_halves"]["2004-01-01_2014-12-31"]
    second = payload["cost_scenarios"]["50"]["fixed_halves"]["2015-01-01_2026-06-30"]
    gates = payload["decision"]["gates"]
    return dedent(
        f"""\
        # 美股短線 20 年 12–1 月動量研究報告

        版本：v1｜狀態：`{payload['decision']['strategy_status']}`｜用途：單一回顧期診斷，並非買入名單、Paper 指令或投資建議。

        ## 結論先行

        本輪固定排除最近 21 個 session，以 D-252 至 D-21 的回報作橫斷面排名，沿用 60 日
        趨勢、QQQ regime、Top-7、D+1 open、20 日持有、gap audit 及成本。結果沒有因為
        低換手假說而改寫門檻。

        - regime 版本接受 {ten['signal_count']} 宗股票訊號；10／25／50 bps CAGR 為 {_pct(ten['portfolio']['cagr'])}／{_pct(twenty_five['portfolio']['cagr'])}／{_pct(fifty['portfolio']['cagr'])}。
        - QQQ 對應 CAGR 為 {_pct(ten['QQQ']['cagr'])}／{_pct(twenty_five['QQQ']['cagr'])}／{_pct(fifty['QQQ']['cagr'])}；25 bps 年化換手 {twenty_five['annualized_turnover']:.2f}x。
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

        所有結果只寫入研究 log；`Paper=false`、`public_strategy_allowed=false`、實金 US$0。
        success-only 網頁維持「今天不下單」，不呈現本輪結果或歷史最後權重。

        機器收據：`artifacts/short_term_us_momentum_20y_12_1_diagnostic.json`；協議：
        `docs/SHORT_TERM_US_MOMENTUM_20Y_12_1_PROTOCOL.md`。
        """
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="建立 20 年 12-1 動量診斷；不產生交易指令"
    )
    parser.add_argument("--snapshot", type=Path, default=ROOT / "artifacts" / SNAPSHOT_FILENAME)
    parser.add_argument("--parent", type=Path, default=PARENT_DEFAULT)
    parser.add_argument("--output", type=Path, default=OUTPUT_DEFAULT)
    parser.add_argument("--report", type=Path, default=REPORT_DEFAULT)
    args = parser.parse_args()

    parent = _load_parent(args.parent)
    panel, manifest, archive_sha256 = _load_checked_snapshot(args.snapshot)
    arrays = _panel_arrays(panel)
    candidates, audit = _build_schedule(arrays)
    signals, skipped = _prepare(candidates, arrays)
    cost_scenarios = {
        str(int(cost)): _scenario(signals, arrays["prices"], cost)
        for cost in PORTFOLIO_COST_SCENARIOS
    }
    ten = cost_scenarios["10"]["all_period"]
    twenty_five = cost_scenarios["25"]["all_period"]
    fifty = cost_scenarios["50"]["all_period"]
    first_fifty = cost_scenarios["50"]["fixed_halves"]["2004-01-01_2014-12-31"]
    second_fifty = cost_scenarios["50"]["fixed_halves"]["2015-01-01_2026-06-30"]
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
        "status": "post_hoc_us_momentum_20y_12_1_diagnostic",
        "protocol": {
            "path": str(PROTOCOL.relative_to(ROOT)),
            "sha256": sha256_file(PROTOCOL),
            "parent_protocol_path": str(PARENT_PROTOCOL.relative_to(ROOT)),
            "parent_protocol_sha256": sha256_file(PARENT_PROTOCOL),
            "lookback_sessions": LOOKBACK_SESSIONS,
            "recent_skip_sessions": RECENT_SKIP_SESSIONS,
            "trend_sessions": TREND_SESSIONS,
            "atr_sessions": ATR_SESSIONS,
            "score": "3 * percentile(momentum12_1) + percentile(trend60)",
            "top_k": TOP_K,
            "score_threshold": SCORE_THRESHOLD,
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
        },
        "schedule": {
            "candidate_count": len(candidates),
            "accepted_count": len(signals),
            "audit": audit,
            "prepare_skipped": skipped,
        },
        "cost_scenarios": cost_scenarios,
        "decision": {
            "strategy_status": "research_candidate_only",
            "diagnostic_status": "negative_slow_momentum_cost_and_persistence",
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
            "reason": "The fixed 12-1 momentum diagnostic does not demonstrate cost-robust outperformance, and the current-watchlist snapshot is survivor-biased.",
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
                "accepted_count": len(signals),
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
