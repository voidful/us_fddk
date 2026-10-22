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

from usfddk.data import load_snapshot  # noqa: E402
from usfddk.sec_insider import sha256_file  # noqa: E402
from usfddk.sec_insider_portfolio import (  # noqa: E402
    PORTFOLIO_BASELINE_SYMBOLS,
    PORTFOLIO_COST_SCENARIOS,
    PORTFOLIO_HOLDING_SESSIONS,
    PORTFOLIO_MIN_MEDIAN_DOLLAR_VOLUME_USD,
    PORTFOLIO_MIN_PRICE_USD,
    prepare_portfolio_signals,
    simulate_event_portfolio,
)

PROTOCOL = ROOT / "docs/SHORT_TERM_US_MOMENTUM_20Y_PROTOCOL.md"
OUTPUT_DEFAULT = ROOT / "artifacts/short_term_us_momentum_20y_diagnostic.json"
REPORT_DEFAULT = ROOT / "docs/SHORT_TERM_US_MOMENTUM_20Y_REPORT.md"
SNAPSHOT_FILENAME = "snapshot_20260731_6a7ca6b8.zip"
SNAPSHOT_ARCHIVE_SHA256 = "d480fb82e712f06aabe0a98461e222344656b87022b8bda2cd7ccaa4c29ae88b"
SNAPSHOT_PANEL_SHA256 = "6a7ca6b83b1570007424daa46b0ff4e8fb4a655d39298a0f4f6d74c3b7ea3a66"
EXCLUDED_SYMBOLS = {
    "QQQ",
    "SPY",
    "IWM",
    "DBC",
    "EEM",
    "EFA",
    "GLD",
    "IEF",
    "SHY",
    "TLT",
    "VNQ",
    "^VIX",
}
TOP_K = 7
MOMENTUM_SESSIONS = 20
TREND_SESSIONS = 60
ATR_SESSIONS = 20
SCORE_THRESHOLD = 2.0
GAP_ATR_MULTIPLIER = 1.5
MIN_ACCEPTED_SIGNALS = 500
FIRST_HALF = (date(2004, 1, 1), date(2014, 12, 31))
SECOND_HALF = (date(2015, 1, 1), date(2026, 6, 30))


def _pct(value: float) -> str:
    return f"{value:.2%}"


def _percentile_rank(values: np.ndarray) -> np.ndarray:
    order = np.argsort(values, kind="mergesort")
    ranked = np.empty(len(values), dtype=float)
    ranked[order] = (np.arange(len(values), dtype=float) + 1.0) / len(values)
    return ranked


def _load_checked_snapshot(path: Path):
    if path.name != SNAPSHOT_FILENAME:
        raise ValueError(f"只接受凍結快照：{SNAPSHOT_FILENAME}")
    archive_sha256 = sha256_file(path)
    if archive_sha256 != SNAPSHOT_ARCHIVE_SHA256:
        raise ValueError(f"snapshot archive SHA-256 漂移：{archive_sha256}")
    panel, manifest = load_snapshot(path)
    if manifest.get("panel_sha256") != SNAPSHOT_PANEL_SHA256:
        raise ValueError("snapshot panel SHA-256 漂移")
    if manifest.get("start") != "2004-01-02" or manifest.get("end") != "2026-07-31":
        raise ValueError("snapshot 日期範圍漂移")
    if manifest.get("rows") != 5680:
        raise ValueError("snapshot rows 漂移")
    return panel, manifest, archive_sha256


def _panel_arrays(panel) -> dict[str, Any]:
    dates = panel.close.index[panel.close["QQQ"].notna() & panel.open["QQQ"].notna()]
    symbols = sorted(set(panel.tickers) - EXCLUDED_SYMBOLS)
    if len(symbols) != 30:
        raise ValueError(f"股票池數目漂移：{len(symbols)}")
    ordered = symbols + list(PORTFOLIO_BASELINE_SYMBOLS)
    close = panel.close.loc[dates, ordered].to_numpy(dtype=float)
    open_ = panel.open.loc[dates, ordered].to_numpy(dtype=float)
    high = panel.high.loc[dates, ordered].to_numpy(dtype=float)
    low = panel.low.loc[dates, ordered].to_numpy(dtype=float)
    volume = panel.volume.loc[dates, ordered].to_numpy(dtype=float)
    dollar_volume = close * volume
    session_dates = [stamp.date() for stamp in dates]
    rows: list[tuple[str, date, float, float]] = []
    liquidity_rows: list[tuple[str, date, float, float]] = []
    for symbol_index, symbol in enumerate(ordered):
        for index, session in enumerate(session_dates):
            if np.isfinite(open_[index, symbol_index]) and np.isfinite(close[index, symbol_index]):
                rows.append(
                    (
                        symbol,
                        session,
                        float(open_[index, symbol_index]),
                        float(close[index, symbol_index]),
                    )
                )
            if np.isfinite(close[index, symbol_index]) and np.isfinite(volume[index, symbol_index]):
                liquidity_rows.append(
                    (
                        symbol,
                        session,
                        float(close[index, symbol_index]),
                        float(dollar_volume[index, symbol_index]),
                    )
                )
    prices = pd.DataFrame(rows, columns=["symbol", "date", "adj_open", "adj_close"])
    liquidity = pd.DataFrame(
        liquidity_rows, columns=["symbol", "date", "close", "dollar_volume"]
    )
    return {
        "dates": session_dates,
        "symbols": symbols,
        "close": close,
        "open": open_,
        "high": high,
        "low": low,
        "volume": volume,
        "dollar_volume": dollar_volume,
        "prices": prices,
        "liquidity": liquidity,
        "baseline_indices": {
            symbol: len(symbols) + index for index, symbol in enumerate(PORTFOLIO_BASELINE_SYMBOLS)
        },
    }


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
        trend = close[index, :stock_count] / close[index - TREND_SESSIONS + 1 : index + 1, :stock_count].mean(axis=0) - 1.0
        true_range = np.maximum.reduce(
            [
                high_history - low_history,
                np.abs(high_history - previous_closes),
                np.abs(low_history - previous_closes),
            ]
        )
        atr = true_range.mean(axis=0)
        gap = np.abs(open_[index + 1, :stock_count] / close[index, :stock_count] - 1.0)
        valid_ids = np.where(liquid)[0]
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
                }
            )
            audit["selected_candidates"] += 1
            room -= 1
    return candidates, audit


def _prepare(
    candidates: list[dict[str, Any]],
    arrays: dict[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    signal_days = {
        (row["ticker"], row["available_session"]): row["signal_day"]
        for row in candidates
    }
    accepted, skipped = prepare_portfolio_signals(
        candidates,
        arrays["prices"],
        holding_sessions=PORTFOLIO_HOLDING_SESSIONS,
        liquidity=arrays["liquidity"],
        min_price_usd=PORTFOLIO_MIN_PRICE_USD,
        min_median_dollar_volume_usd=PORTFOLIO_MIN_MEDIAN_DOLLAR_VOLUME_USD,
    )
    for signal in accepted:
        key = (signal["ticker"], signal["entry_date"].isoformat())
        signal["signal_day"] = signal_days[key]
    return accepted, skipped


def _slice(signals: list[dict[str, Any]], window: tuple[date, date]) -> list[dict[str, Any]]:
    start, end = window
    return [
        signal
        for signal in signals
        if start <= date.fromisoformat(str(signal["signal_day"])) <= end
    ]


def _scenario(
    signals: list[dict[str, Any]],
    prices: pd.DataFrame,
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
    control = payload["control_cost_scenarios"]["25"]["all_period"]
    gates = payload["decision"]["gates"]
    return dedent(
        f"""\
        # 美股短線 20 年 20／60 動量研究報告

        版本：v1｜狀態：`{payload['decision']['strategy_status']}`｜用途：長樣本研究診斷，並非買入名單、Paper 指令或投資建議。

        ## 結論先行

        在 2004–2026 凍結快照上，20 日動量 ×3、60 日趨勢 ×1、Top-7、20 sessions 及 QQQ
        regime 的描述性結果在低成本下略勝 QQQ，但 25／50 bps 成本後反轉落後；前段及後段
        亦沒有同時勝出。本輪保留負面成本／持續性結果，不升格。

        - regime 版本接受 {ten['signal_count']} 宗訊號；全期 10／25／50 bps 策略 CAGR 為 {_pct(ten['portfolio']['cagr'])}／{_pct(twenty_five['portfolio']['cagr'])}／{_pct(fifty['portfolio']['cagr'])}。
        - 50 bps 前段策略／QQQ CAGR 為 {_pct(first['portfolio']['cagr'])}／{_pct(first['QQQ']['cagr'])}；後段為 {_pct(second['portfolio']['cagr'])}／{_pct(second['QQQ']['cagr'])}。
        - 不加 regime 的 25 bps control CAGR 為 {_pct(control['portfolio']['cagr'])}，最大跌幅 {_pct(control['portfolio']['max_drawdown'])}；regime 版為 {_pct(twenty_five['portfolio']['cagr'])}／{_pct(twenty_five['portfolio']['max_drawdown'])}。

        ## 固定規則

        | 項目 | 凍結內容 |
        |---|---|
        | 評分 | `3 × percentile(20-session momentum) + percentile(close / 60-session SMA - 1)` |
        | 執行 | 下一 XNYS open 入場；最多七檔等權；20 sessions 強制離場 |
        | regime | QQQ 收市高於 20／60-session SMA；另列 no-regime control |
        | gap | `abs(next open / signal close - 1) < 1.5 × ATR20`，在 open 決定是否跳過 |
        | 成本／基準 | 單邊 10／25／50 bps；QQQ、SPY、IWM |
        | 分段 | 2004–2014；2015–2026H1 |

        ## Regime 版本全期結果

        | 成本 | 訊號 | 策略 CAGR | QQQ CAGR | SPY CAGR | IWM CAGR | 策略最大跌幅 | QQQ 最大跌幅 | 策略 Sharpe |
        |---:|---:|---:|---:|---:|---:|---:|---:|---:|
        | 10 bps | {ten['signal_count']} | {_pct(ten['portfolio']['cagr'])} | {_pct(ten['QQQ']['cagr'])} | {_pct(ten['baselines']['SPY']['cagr'])} | {_pct(ten['baselines']['IWM']['cagr'])} | {_pct(ten['portfolio']['max_drawdown'])} | {_pct(ten['QQQ']['max_drawdown'])} | {ten['portfolio']['sharpe']:.2f} |
        | 25 bps | {twenty_five['signal_count']} | {_pct(twenty_five['portfolio']['cagr'])} | {_pct(twenty_five['QQQ']['cagr'])} | {_pct(twenty_five['baselines']['SPY']['cagr'])} | {_pct(twenty_five['baselines']['IWM']['cagr'])} | {_pct(twenty_five['portfolio']['max_drawdown'])} | {_pct(twenty_five['QQQ']['max_drawdown'])} | {twenty_five['portfolio']['sharpe']:.2f} |
        | 50 bps | {fifty['signal_count']} | {_pct(fifty['portfolio']['cagr'])} | {_pct(fifty['QQQ']['cagr'])} | {_pct(fifty['baselines']['SPY']['cagr'])} | {_pct(fifty['baselines']['IWM']['cagr'])} | {_pct(fifty['portfolio']['max_drawdown'])} | {_pct(fifty['QQQ']['max_drawdown'])} | {fifty['portfolio']['sharpe']:.2f} |

        ## 決策閘門

        - 通過：{sum(gates.values())}/{len(gates)}。
        - `{', '.join(key for key, value in gates.items() if not value)}` 未通過。
        - 快照是現時大型股池，且 manifest 已記錄 ABBV／META 歷史覆蓋不足；沒有 point-in-time 成分、退市／收購回報、完整公司行動、sector 歷史及正式 risk-free package。

        所有結果只寫入研究 log 與機器收據；`Paper=false`、`public_strategy_allowed=false`、實金 US$0。success-only 網頁維持「今天不下單」。

        機器收據：`artifacts/short_term_us_momentum_20y_diagnostic.json`；協議：`docs/SHORT_TERM_US_MOMENTUM_20Y_PROTOCOL.md`。
        """
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="建立 20 年美股 20/60 動量＋ATR gap＋QQQ regime 診斷；不產生交易指令"
    )
    parser.add_argument("--snapshot", type=Path, default=ROOT / "artifacts" / SNAPSHOT_FILENAME)
    parser.add_argument("--output", type=Path, default=OUTPUT_DEFAULT)
    parser.add_argument("--report", type=Path, default=REPORT_DEFAULT)
    args = parser.parse_args()

    panel, manifest, archive_sha256 = _load_checked_snapshot(args.snapshot)
    arrays = _panel_arrays(panel)
    regime_candidates, regime_audit = _build_schedule(arrays, regime_gate=True)
    control_candidates, control_audit = _build_schedule(arrays, regime_gate=False)
    regime_signals, regime_skipped = _prepare(regime_candidates, arrays)
    control_signals, control_skipped = _prepare(control_candidates, arrays)
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
        "status": "post_hoc_us_momentum_20y_diagnostic",
        "protocol": {
            "path": str(PROTOCOL.relative_to(ROOT)),
            "sha256": sha256_file(PROTOCOL),
            "momentum_sessions": MOMENTUM_SESSIONS,
            "trend_sessions": TREND_SESSIONS,
            "atr_sessions": ATR_SESSIONS,
            "gap_atr_multiplier": GAP_ATR_MULTIPLIER,
            "score_threshold": SCORE_THRESHOLD,
            "top_k": TOP_K,
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
            "diagnostic_status": "negative_cost_persistence_and_data_boundary",
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
            "reason": "Low-cost full-period outperformance does not survive 25/50 bps and the fixed halves; the current-watchlist snapshot is not point-in-time investable data.",
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
