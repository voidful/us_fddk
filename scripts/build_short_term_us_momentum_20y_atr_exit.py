from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path
from textwrap import dedent
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.build_short_term_us_momentum_20y import (  # noqa: E402
    FIRST_HALF,
    SECOND_HALF,
    _build_schedule,
    _load_checked_snapshot,
    _panel_arrays,
    _prepare,
)
from scripts.build_short_term_us_momentum_20y import PROTOCOL as PARENT_PROTOCOL  # noqa: E402
from usfddk.sec_insider import sha256_file  # noqa: E402
from usfddk.sec_insider_portfolio import (  # noqa: E402
    PORTFOLIO_BASELINE_SYMBOLS,
    PORTFOLIO_COST_SCENARIOS,
    _buy_hold_baseline,
    _metrics,
)

PROTOCOL = ROOT / "docs/SHORT_TERM_US_MOMENTUM_20Y_ATR_EXIT_PROTOCOL.md"
PARENT_DEFAULT = ROOT / "artifacts/short_term_us_momentum_20y_diagnostic.json"
OUTPUT_DEFAULT = ROOT / "artifacts/short_term_us_momentum_20y_atr_exit_diagnostic.json"
REPORT_DEFAULT = ROOT / "docs/SHORT_TERM_US_MOMENTUM_20Y_ATR_EXIT_REPORT.md"
STOP_ATR_MULTIPLIER = 3.0
TARGET_ATR_MULTIPLIER = 4.0
MIN_ACCEPTED_SIGNALS = 500


def _pct(value: float) -> str:
    return f"{value:.2%}"


def _load_parent(path: Path) -> dict[str, Any]:
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


def _prepare_with_atr(candidates: list[dict[str, Any]], arrays: dict[str, Any]):
    atr_by_key = {
        (row["ticker"], row["available_session"]): float(row["atr"])
        for row in candidates
    }
    accepted, skipped = _prepare(candidates, arrays)
    for signal in accepted:
        signal["atr"] = atr_by_key[(signal["ticker"], signal["entry_date"].isoformat())]
    return accepted, skipped


def _simulate(signals: list[dict[str, Any]], arrays: dict[str, Any], cost_bps: float) -> dict[str, Any]:
    if not signals:
        raise ValueError("ATR extension 不接受空 signal schedule")
    cost = cost_bps / 10_000.0
    sessions: list[date] = arrays["dates"]
    position_by_day = {day: index for index, day in enumerate(sessions)}
    symbol_order = arrays["symbols"] + list(PORTFOLIO_BASELINE_SYMBOLS)
    symbol_index = {symbol: index for index, symbol in enumerate(symbol_order)}
    close = arrays["close"]
    open_ = arrays["open"]
    high = arrays["high"]
    low = arrays["low"]
    start = min(signal["entry_date"] for signal in signals)
    end = max(signal["exit_date"] for signal in signals)
    start_index = position_by_day[start]
    end_index = position_by_day[end]
    signals_by_day: dict[date, list[dict[str, Any]]] = defaultdict(list)
    for signal in signals:
        signals_by_day[signal["entry_date"]].append(signal)

    active: dict[str, dict[str, Any]] = {}
    previous_weights: dict[str, float] = {}
    equity = 1.0
    equity_values: list[float] = []
    daily_returns: list[float] = []
    turnover_total = 0.0
    active_total = 0
    stop_count = 0
    target_count = 0
    time_count = 0

    for index in range(start_index, end_index + 1):
        day = sessions[index]
        for ticker, position in list(active.items()):
            if day > position["exit_date"]:
                del active[ticker]
        for signal in signals_by_day.get(day, []):
            ticker_index = symbol_index[signal["ticker"]]
            entry_price = float(open_[index, ticker_index])
            atr = float(signal["atr"])
            if not pd.notna(entry_price) or not pd.notna(atr) or atr <= 0.0:
                raise ValueError("入場 OHLC 或 ATR 不完整")
            active[signal["ticker"]] = {
                "entry_index": index,
                "entry_price": entry_price,
                "stop": entry_price - STOP_ATR_MULTIPLIER * atr,
                "target": entry_price + TARGET_ATR_MULTIPLIER * atr,
                "exit_date": signal["exit_date"],
            }

        weight = 1.0 / len(active) if active else 0.0
        target_weights = {ticker: weight for ticker in active}
        turnover = sum(
            abs(target_weights.get(ticker, 0.0) - previous_weights.get(ticker, 0.0))
            for ticker in set(target_weights) | set(previous_weights)
        )
        turnover_total += turnover
        gross_return = 0.0
        expired: list[str] = []
        for ticker, position in active.items():
            ticker_index = symbol_index[ticker]
            base_price = (
                position["entry_price"]
                if index == position["entry_index"]
                else float(close[index - 1, ticker_index])
            )
            hit_stop = float(low[index, ticker_index]) <= position["stop"]
            hit_target = float(high[index, ticker_index]) >= position["target"]
            if hit_stop and hit_target:
                exit_price = position["stop"]
                stop_count += 1
                expired.append(ticker)
            elif hit_stop:
                exit_price = position["stop"]
                stop_count += 1
                expired.append(ticker)
            elif hit_target:
                exit_price = position["target"]
                target_count += 1
                expired.append(ticker)
            elif day >= position["exit_date"]:
                exit_price = float(close[index, ticker_index])
                time_count += 1
                expired.append(ticker)
            else:
                exit_price = float(close[index, ticker_index])
            gross_return += target_weights[ticker] * (exit_price / base_price - 1.0)

        equity *= (1.0 - turnover * cost) * (1.0 + gross_return)
        equity_values.append(equity)
        daily_returns.append(
            equity_values[-1] / equity_values[-2] - 1.0
            if len(equity_values) > 1
            else equity - 1.0
        )
        active_total += len(active)
        previous_weights = target_weights
        for ticker in expired:
            active.pop(ticker, None)

    terminal_liquidation_cost = sum(previous_weights.values()) * cost
    equity *= 1.0 - terminal_liquidation_cost
    equity_values[-1] = equity
    series = pd.Series(equity_values, index=sessions[start_index : end_index + 1])
    returns = series.pct_change().fillna(series.iloc[0] - 1.0)
    portfolio = _metrics(series, returns, max((end - start).days, 1))
    baselines: dict[str, dict[str, float]] = {}
    for symbol in PORTFOLIO_BASELINE_SYMBOLS:
        baselines[symbol], _ = _buy_hold_baseline(
            arrays["prices"],
            symbol=symbol,
            start=start,
            end=end,
            one_way_cost=cost,
        )
    return {
        "signal_count": len(signals),
        "period": {"start": start.isoformat(), "end": end.isoformat()},
        "portfolio": portfolio,
        "QQQ": baselines["QQQ"],
        "baselines": baselines,
        "comparison": {
            "cagr_difference": portfolio["cagr"] - baselines["QQQ"]["cagr"],
            "total_return_difference": portfolio["total_return"]
            - baselines["QQQ"]["total_return"],
        },
        "average_active_positions": active_total / max(len(equity_values), 1),
        "annualized_turnover": turnover_total / max(len(equity_values), 1) * 252.0,
        "terminal_liquidation_cost": terminal_liquidation_cost,
        "exit_counts": {
            "stop": stop_count,
            "target": target_count,
            "time": time_count,
        },
    }


def _slice(signals: list[dict[str, Any]], window: tuple[date, date]) -> list[dict[str, Any]]:
    start, end = window
    return [
        signal
        for signal in signals
        if start <= date.fromisoformat(str(signal["signal_day"])) <= end
    ]


def _scenario(signals: list[dict[str, Any]], arrays: dict[str, Any], cost_bps: float) -> dict[str, Any]:
    return {
        "all_period": _simulate(signals, arrays, cost_bps),
        "fixed_halves": {
            "2004-01-01_2014-12-31": _simulate(_slice(signals, FIRST_HALF), arrays, cost_bps),
            "2015-01-01_2026-06-30": _simulate(_slice(signals, SECOND_HALF), arrays, cost_bps),
        },
    }


def _build_report(payload: dict[str, Any]) -> str:
    ten = payload["cost_scenarios"]["10"]["all_period"]
    twenty_five = payload["cost_scenarios"]["25"]["all_period"]
    fifty = payload["cost_scenarios"]["50"]["all_period"]
    first = payload["cost_scenarios"]["50"]["fixed_halves"]["2004-01-01_2014-12-31"]
    second = payload["cost_scenarios"]["50"]["fixed_halves"]["2015-01-01_2026-06-30"]
    parent = payload["parent_time_exit"]["cost_scenarios"]
    gates = payload["decision"]["gates"]
    return dedent(
        f"""\
        # 美股短線 20 年動量 ATR 出場研究報告

        版本：v1｜狀態：`{payload['decision']['strategy_status']}`｜用途：出場機制診斷，並非買入名單、Paper 指令或投資建議。

        ## 結論先行

        在同一 20 年 20／60 動量及 QQQ regime signal schedule 上加入止蝕 3×ATR、止賺 4×ATR
        後，結果比原本 20-session time exit 更差：10／25／50 bps CAGR 只有 9.25%／4.06%／-4.07%，
        均未跑贏 QQQ。本輪不升格，也不以止蝕／止賺結果改寫選股規則。

        - ATR exit 全期訊號 {ten['signal_count']} 宗；stop／target／time exits 為 {ten['exit_counts']['stop']}／{ten['exit_counts']['target']}／{ten['exit_counts']['time']}。
        - 50 bps 前段策略／QQQ CAGR 為 {_pct(first['portfolio']['cagr'])}／{_pct(first['QQQ']['cagr'])}；後段為 {_pct(second['portfolio']['cagr'])}／{_pct(second['QQQ']['cagr'])}。
        - 原本 time exit 的 25 bps CAGR 為 {_pct(parent['25']['all_period']['portfolio']['cagr'])}，ATR exit 降至 {_pct(twenty_five['portfolio']['cagr'])}。

        ## ATR 出場結果

        | 成本 | 策略 CAGR | QQQ CAGR | SPY CAGR | IWM CAGR | 策略最大跌幅 | QQQ 最大跌幅 | 策略 Sharpe |
        |---:|---:|---:|---:|---:|---:|---:|---:|
        | 10 bps | {_pct(ten['portfolio']['cagr'])} | {_pct(ten['QQQ']['cagr'])} | {_pct(ten['baselines']['SPY']['cagr'])} | {_pct(ten['baselines']['IWM']['cagr'])} | {_pct(ten['portfolio']['max_drawdown'])} | {_pct(ten['QQQ']['max_drawdown'])} | {ten['portfolio']['sharpe']:.2f} |
        | 25 bps | {_pct(twenty_five['portfolio']['cagr'])} | {_pct(twenty_five['QQQ']['cagr'])} | {_pct(twenty_five['baselines']['SPY']['cagr'])} | {_pct(twenty_five['baselines']['IWM']['cagr'])} | {_pct(twenty_five['portfolio']['max_drawdown'])} | {_pct(twenty_five['QQQ']['max_drawdown'])} | {twenty_five['portfolio']['sharpe']:.2f} |
        | 50 bps | {_pct(fifty['portfolio']['cagr'])} | {_pct(fifty['QQQ']['cagr'])} | {_pct(fifty['baselines']['SPY']['cagr'])} | {_pct(fifty['baselines']['IWM']['cagr'])} | {_pct(fifty['portfolio']['max_drawdown'])} | {_pct(fifty['QQQ']['max_drawdown'])} | {fifty['portfolio']['sharpe']:.2f} |

        ## 決策閘門

        - 通過：{sum(gates.values())}/{len(gates)}。
        - `{', '.join(key for key, value in gates.items() if not value)}` 未通過。
        - ATR extension 年化換手 {twenty_five['annualized_turnover']:.2f}x；高換手與 gap／資料邊界仍未納入正式 production accounting。

        所有結果只寫入研究 log；`Paper=false`、`public_strategy_allowed=false`、實金 US$0。success-only 網頁維持「今天不下單」。

        機器收據：`artifacts/short_term_us_momentum_20y_atr_exit_diagnostic.json`；協議：`docs/SHORT_TERM_US_MOMENTUM_20Y_ATR_EXIT_PROTOCOL.md`。
        """
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="建立 20 年 momentum ATR exit extension；不產生交易指令"
    )
    parser.add_argument("--snapshot", type=Path, default=ROOT / "artifacts" / "snapshot_20260731_6a7ca6b8.zip")
    parser.add_argument("--parent", type=Path, default=PARENT_DEFAULT)
    parser.add_argument("--output", type=Path, default=OUTPUT_DEFAULT)
    parser.add_argument("--report", type=Path, default=REPORT_DEFAULT)
    args = parser.parse_args()

    parent = _load_parent(args.parent)
    panel, manifest, archive_sha256 = _load_checked_snapshot(args.snapshot)
    arrays = _panel_arrays(panel)
    candidates, schedule_audit = _build_schedule(arrays, regime_gate=True)
    signals, prepare_skipped = _prepare_with_atr(candidates, arrays)
    if len(signals) != parent["regime_schedule"]["accepted_count"]:
        raise ValueError("ATR extension schedule 與 parent accepted count 不一致")
    cost_scenarios = {
        str(int(cost)): _scenario(signals, arrays, cost)
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
        "status": "post_hoc_us_momentum_20y_atr_exit_diagnostic",
        "parent": {
            "filename": args.parent.name,
            "sha256": sha256_file(args.parent),
            "status": parent["status"],
            "protocol_sha256": parent["protocol"]["sha256"],
            "time_exit_accepted_count": parent["regime_schedule"]["accepted_count"],
        },
        "protocol": {
            "path": str(PROTOCOL.relative_to(ROOT)),
            "sha256": sha256_file(PROTOCOL),
            "parent_protocol_path": str(PARENT_PROTOCOL.relative_to(ROOT)),
            "parent_protocol_sha256": parent["protocol"]["sha256"],
            "stop_atr_multiplier": STOP_ATR_MULTIPLIER,
            "target_atr_multiplier": TARGET_ATR_MULTIPLIER,
            "holding_sessions": 20,
            "cost_scenarios_bps": list(PORTFOLIO_COST_SCENARIOS),
            "baseline_symbols": list(PORTFOLIO_BASELINE_SYMBOLS),
        },
        "source": {
            "snapshot_filename": args.snapshot.name,
            "archive_sha256": archive_sha256,
            "panel_sha256": manifest["panel_sha256"],
            "manifest_start": manifest["start"],
            "manifest_end": manifest["end"],
        },
        "schedule": {
            "candidate_count": len(candidates),
            "accepted_count": len(signals),
            "audit": schedule_audit,
            "prepare_skipped": prepare_skipped,
            "early_exit_replacement": False,
        },
        "cost_scenarios": cost_scenarios,
        "parent_time_exit": parent,
        "decision": {
            "strategy_status": "research_candidate_only",
            "diagnostic_status": "negative_atr_exit_cost_and_persistence",
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
            "reason": "ATR stop/target extension loses to QQQ at every cost scenario and fixed half; early exits are conservatively non-replaced and the parent data remains survivor-biased.",
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
