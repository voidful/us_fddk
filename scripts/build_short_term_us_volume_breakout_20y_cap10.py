from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path
from textwrap import dedent
from typing import Any

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.build_short_term_us_volume_breakout_20y import (  # noqa: E402
    BREAKOUT_LOOKBACK,
    MOMENTUM_SESSIONS,
    TOP_K,
    TREND_SESSIONS,
    VOLUME_LOOKBACK,
    VOLUME_MULTIPLE,
    _load_checked_snapshot,
    _panel_arrays,
    _prepare,
    _scenario,
)
from usfddk.sec_insider import sha256_file  # noqa: E402
from usfddk.sec_insider_portfolio import (  # noqa: E402
    PORTFOLIO_BASELINE_SYMBOLS,
    PORTFOLIO_COST_SCENARIOS,
    PORTFOLIO_HOLDING_SESSIONS,
    PORTFOLIO_MIN_MEDIAN_DOLLAR_VOLUME_USD,
    PORTFOLIO_MIN_PRICE_USD,
)
from usfddk.short_term_high_return import _completed_period_mask  # noqa: E402

PROTOCOL = ROOT / "docs/SHORT_TERM_US_VOLUME_BREAKOUT_20Y_CAP10_PROTOCOL.md"
OUTPUT_DEFAULT = ROOT / "artifacts/short_term_us_volume_breakout_20y_cap10_diagnostic.json"
REPORT_DEFAULT = ROOT / "docs/SHORT_TERM_US_VOLUME_BREAKOUT_20Y_CAP10_REPORT.md"
SNAPSHOT_FILENAME = "snapshot_20260731_6a7ca6b8.zip"
SNAPSHOT_ARCHIVE_SHA256 = "d480fb82e712f06aabe0a98461e222344656b87022b8bda2cd7ccaa4c29ae88b"
SNAPSHOT_PANEL_SHA256 = "6a7ca6b83b1570007424daa46b0ff4e8fb4a655d39298a0f4f6d74c3b7ea3a66"
MIN_ACCEPTED_EVENTS = 30


def _pct(value: float) -> str:
    return f"{value:.2%}"


def _build_candidates(
    arrays: dict[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    sessions = pd.DatetimeIndex(pd.to_datetime(arrays["dates"])).normalize()
    close: np.ndarray = arrays["close"]
    open_: np.ndarray = arrays["open"]
    volume: np.ndarray = arrays["volume"]
    dollar_volume: np.ndarray = arrays["dollar_volume"]
    symbols: list[str] = arrays["symbols"]
    spy_index = arrays["baseline_indices"]["SPY"]
    weekly_mask = _completed_period_mask(sessions, "weekly").to_numpy(dtype=bool)
    candidates: list[dict[str, Any]] = []
    audit = {
        "weekly_signal_sessions": 0,
        "insufficient_history": 0,
        "spy_regime_off": 0,
        "insufficient_base_pool": 0,
        "no_breakout_pool": 0,
        "incomplete_forward_window": 0,
        "candidate_events": 0,
        "candidate_signals": 0,
    }
    stock_count = len(symbols)
    stock_close = close[:, :stock_count]
    stock_volume = volume[:, :stock_count]
    for index in np.flatnonzero(weekly_mask):
        if index + PORTFOLIO_HOLDING_SESSIONS >= len(sessions):
            continue
        audit["weekly_signal_sessions"] += 1
        if index < max(BREAKOUT_LOOKBACK, TREND_SESSIONS, MOMENTUM_SESSIONS):
            audit["insufficient_history"] += 1
            continue
        spy_history = close[index - TREND_SESSIONS + 1 : index + 1, spy_index]
        if not np.all(np.isfinite(spy_history)) or spy_history[-1] <= spy_history.mean():
            audit["spy_regime_off"] += 1
            continue
        history_close = stock_close[index - TREND_SESSIONS + 1 : index + 1]
        liquidity_history = dollar_volume[
            index - VOLUME_LOOKBACK + 1 : index + 1, :stock_count
        ]
        volume_history = stock_volume[index - VOLUME_LOOKBACK + 1 : index + 1]
        prior_close = stock_close[index - MOMENTUM_SESSIONS]
        prior_high_window = stock_close[index - BREAKOUT_LOOKBACK : index]
        finite = (
            np.all(np.isfinite(history_close), axis=0)
            & np.all(np.isfinite(liquidity_history), axis=0)
            & np.all(np.isfinite(volume_history), axis=0)
            & np.isfinite(prior_close)
            & np.all(np.isfinite(prior_high_window), axis=0)
        )
        close_today = stock_close[index]
        momentum = close_today / prior_close - 1.0
        trend = close_today / history_close.mean(axis=0) - 1.0
        median_dollar_volume = np.median(liquidity_history, axis=0)
        median_volume = np.median(volume_history, axis=0)
        base = (
            finite
            & (close_today >= PORTFOLIO_MIN_PRICE_USD)
            & (median_dollar_volume >= PORTFOLIO_MIN_MEDIAN_DOLLAR_VOLUME_USD)
            & (trend > 0.0)
            & (momentum > 0.0)
        )
        if int(np.sum(base)) < TOP_K:
            audit["insufficient_base_pool"] += 1
            continue
        breakout = base & (
            close_today >= np.max(prior_high_window, axis=0)
        ) & (stock_volume[index] >= VOLUME_MULTIPLE * median_volume)
        selected_indices = np.where(breakout)[0]
        if len(selected_indices) == 0:
            audit["no_breakout_pool"] += 1
            continue
        selected_indices = np.asarray(
            sorted(
                selected_indices.tolist(),
                key=lambda item: (-float(momentum[item]), symbols[item]),
            )[:TOP_K],
            dtype=int,
        )
        entry_index = index + 1
        forward = slice(entry_index, entry_index + PORTFOLIO_HOLDING_SESSIONS)
        forward_complete = (
            np.all(np.isfinite(open_[forward, selected_indices]), axis=0)
            & np.all(np.isfinite(close[forward, selected_indices]), axis=0)
        )
        if not np.all(forward_complete):
            audit["incomplete_forward_window"] += 1
            continue
        signal_day = sessions[index].date().isoformat()
        entry_day = sessions[entry_index].date().isoformat()
        for symbol_index in selected_indices:
            candidates.append(
                {
                    "ticker": symbols[symbol_index],
                    "available_session": entry_day,
                    "signal_day": signal_day,
                    "score": float(momentum[symbol_index]),
                    "volume_multiple": float(
                        stock_volume[index, symbol_index] / median_volume[symbol_index]
                    ),
                }
            )
        audit["candidate_events"] += 1
        audit["candidate_signals"] += len(selected_indices)
    return candidates, audit


def _accept_nonoverlap(
    signals: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    by_entry: dict[date, list[dict[str, Any]]] = defaultdict(list)
    for signal in signals:
        by_entry[signal["entry_date"]].append(signal)
    accepted: list[dict[str, Any]] = []
    skipped_events = 0
    skipped_signals = 0
    last_exit: date | None = None
    for entry_day in sorted(by_entry):
        group = by_entry[entry_day]
        if not group:
            continue
        exit_day = max(signal["exit_date"] for signal in group)
        if last_exit is not None and entry_day <= last_exit:
            skipped_events += 1
            skipped_signals += len(group)
            continue
        accepted.extend(group)
        last_exit = exit_day
    return accepted, {
        "accepted_events": len({signal["entry_date"] for signal in accepted}),
        "accepted_signals": len(accepted),
        "overlapping_events_skipped": skipped_events,
        "overlapping_signals_skipped": skipped_signals,
    }


def _build_report(payload: dict[str, Any]) -> str:
    ten = payload["cost_scenarios"]["10"]["all_period"]
    twenty_five = payload["cost_scenarios"]["25"]["all_period"]
    fifty = payload["cost_scenarios"]["50"]["all_period"]
    first = payload["cost_scenarios"]["50"]["fixed_halves"]["2004-01-01_2014-12-31"]
    second = payload["cost_scenarios"]["50"]["fixed_halves"]["2015-01-01_2026-06-30"]
    gates = payload["decision"]["gates"]
    return dedent(
        f"""\
        # 美股短線 20 年成交量突破最多 Top-10 研究報告

        版本：v1｜狀態：`{payload['decision']['strategy_status']}`｜用途：source-aligned 機制診斷，並非買入名單、Paper 指令或投資建議。

        ## 結論先行

        本輪允許 1–10 隻突破股，但要求至少 10 隻合資格基礎股票；沿用 60 日突破、1.5×20 日
        成交量、SPY 60 日 regime、D+1 開市、20 日持有及 first-event-wins。這與上一輪
        exact-Top10 變體分開記錄，不能合併解讀。

        - 候選事件 {payload['schedule']['candidate_events']} 宗；非重疊後接受 {payload['schedule']['accepted_events']} 宗，{payload['schedule']['accepted_signals']} 個股票訊號。
        - 10／25／50 bps 策略 CAGR 為 {_pct(ten['portfolio']['cagr'])}／{_pct(twenty_five['portfolio']['cagr'])}／{_pct(fifty['portfolio']['cagr'])}；QQQ 為 {_pct(ten['QQQ']['cagr'])}／{_pct(twenty_five['QQQ']['cagr'])}／{_pct(fifty['QQQ']['cagr'])}。
        - 50 bps 前段策略／QQQ CAGR 為 {_pct(first['portfolio']['cagr'])}／{_pct(first['QQQ']['cagr'])}；後段為 {_pct(second['portfolio']['cagr'])}／{_pct(second['QQQ']['cagr'])}。

        ## 結果

        | 成本 | 股票訊號 | 策略 CAGR | QQQ CAGR | SPY CAGR | IWM CAGR | 策略最大跌幅 | QQQ 最大跌幅 | Sharpe |
        |---:|---:|---:|---:|---:|---:|---:|---:|---:|
        | 10 bps | {ten['signal_count']} | {_pct(ten['portfolio']['cagr'])} | {_pct(ten['QQQ']['cagr'])} | {_pct(ten['baselines']['SPY']['cagr'])} | {_pct(ten['baselines']['IWM']['cagr'])} | {_pct(ten['portfolio']['max_drawdown'])} | {_pct(ten['QQQ']['max_drawdown'])} | {ten['portfolio']['sharpe']:.2f} |
        | 25 bps | {twenty_five['signal_count']} | {_pct(twenty_five['portfolio']['cagr'])} | {_pct(twenty_five['QQQ']['cagr'])} | {_pct(twenty_five['baselines']['SPY']['cagr'])} | {_pct(twenty_five['baselines']['IWM']['cagr'])} | {_pct(twenty_five['portfolio']['max_drawdown'])} | {_pct(twenty_five['QQQ']['max_drawdown'])} | {twenty_five['portfolio']['sharpe']:.2f} |
        | 50 bps | {fifty['signal_count']} | {_pct(fifty['portfolio']['cagr'])} | {_pct(fifty['QQQ']['cagr'])} | {_pct(fifty['baselines']['SPY']['cagr'])} | {_pct(fifty['baselines']['IWM']['cagr'])} | {_pct(fifty['portfolio']['max_drawdown'])} | {_pct(fifty['QQQ']['max_drawdown'])} | {fifty['portfolio']['sharpe']:.2f} |

        ## 決策閘門

        - 通過：{sum(gates.values())}/{len(gates)}。
        - 未通過：{', '.join(key for key, value in gates.items() if not value) or '無'}。
        - 年率化換手（25 bps）：{twenty_five['annualized_turnover']:.2f}x。

        所有結果只寫入研究 log；`Paper=false`、`public_strategy_allowed=false`、實金 US$0。
        success-only 網頁維持「今天不下單」，不呈現本輪結果或歷史最後權重。

        機器收據：`artifacts/short_term_us_volume_breakout_20y_cap10_diagnostic.json`；協議：
        `docs/SHORT_TERM_US_VOLUME_BREAKOUT_20Y_CAP10_PROTOCOL.md`。
        """
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="建立最多 Top-10 成交量突破診斷；不產生交易指令"
    )
    parser.add_argument("--snapshot", type=Path, default=ROOT / "artifacts" / SNAPSHOT_FILENAME)
    parser.add_argument("--output", type=Path, default=OUTPUT_DEFAULT)
    parser.add_argument("--report", type=Path, default=REPORT_DEFAULT)
    args = parser.parse_args()

    panel, manifest, archive_sha256 = _load_checked_snapshot(args.snapshot)
    arrays = _panel_arrays(panel)
    candidates, candidate_audit = _build_candidates(arrays)
    signals, prepare_skipped = _prepare(candidates, arrays)
    signal_day_map = {
        (row["ticker"], row["available_session"]): row["signal_day"]
        for row in candidates
    }
    for signal in signals:
        signal["signal_day"] = signal_day_map[
            (signal["ticker"], signal["entry_date"].isoformat())
        ]
    accepted_signals, nonoverlap = _accept_nonoverlap(signals)
    cost_scenarios = {
        str(int(cost)): _scenario(accepted_signals, arrays["prices"], cost)
        for cost in PORTFOLIO_COST_SCENARIOS
    }
    ten = cost_scenarios["10"]["all_period"]
    twenty_five = cost_scenarios["25"]["all_period"]
    fifty = cost_scenarios["50"]["all_period"]
    first_fifty = cost_scenarios["50"]["fixed_halves"]["2004-01-01_2014-12-31"]
    second_fifty = cost_scenarios["50"]["fixed_halves"]["2015-01-01_2026-06-30"]
    gates = {
        "minimum_30_accepted_events": nonoverlap["accepted_events"] >= MIN_ACCEPTED_EVENTS,
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
        "status": "post_hoc_us_volume_breakout_20y_cap10_diagnostic",
        "protocol": {
            "path": str(PROTOCOL.relative_to(ROOT)),
            "sha256": sha256_file(PROTOCOL),
            "frequency": "weekly_completed_xnys",
            "breakout_lookback_sessions": BREAKOUT_LOOKBACK,
            "trend_sessions": TREND_SESSIONS,
            "momentum_sessions": MOMENTUM_SESSIONS,
            "volume_lookback": VOLUME_LOOKBACK,
            "volume_multiple": VOLUME_MULTIPLE,
            "top_k_cap": TOP_K,
            "min_breakout_candidates": 1,
            "min_base_eligible": TOP_K,
            "holding_sessions": PORTFOLIO_HOLDING_SESSIONS,
            "baseline_symbols": list(PORTFOLIO_BASELINE_SYMBOLS),
            "cost_scenarios_bps": list(PORTFOLIO_COST_SCENARIOS),
            "min_price_usd": PORTFOLIO_MIN_PRICE_USD,
            "min_median_dollar_volume_usd": PORTFOLIO_MIN_MEDIAN_DOLLAR_VOLUME_USD,
            "market_regime": "SPY_close_above_60_session_SMA",
            "overlap_policy": "first_event_wins",
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
        },
        "schedule": {
            **candidate_audit,
            **nonoverlap,
            "prepare_skipped": prepare_skipped,
            "candidate_events": candidate_audit["candidate_events"],
            "accepted_events": nonoverlap["accepted_events"],
            "accepted_signals": nonoverlap["accepted_signals"],
        },
        "cost_scenarios": cost_scenarios,
        "decision": {
            "strategy_status": "research_candidate_only",
            "diagnostic_status": "volume_breakout_cap10_cost_and_survivorship_diagnostic",
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
            "reason": "Source-aligned cap-10 semantics still use a current-watchlist survivor snapshot and are not a promotion authorization.",
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
                "candidate_events": candidate_audit["candidate_events"],
                "accepted_events": nonoverlap["accepted_events"],
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
