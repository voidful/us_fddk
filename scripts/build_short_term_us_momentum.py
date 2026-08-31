from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path
from textwrap import dedent
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from usfddk.sec_insider import sha256_file  # noqa: E402
from usfddk.sec_insider_forward import load_long_total_return_prices  # noqa: E402
from usfddk.sec_insider_portfolio import (  # noqa: E402
    PORTFOLIO_BASELINE_SYMBOLS,
    PORTFOLIO_COST_SCENARIOS,
    PORTFOLIO_HOLDING_SESSIONS,
    PORTFOLIO_MIN_MEDIAN_DOLLAR_VOLUME_USD,
    PORTFOLIO_MIN_PRICE_USD,
    load_long_liquidity,
    prepare_portfolio_signals,
    simulate_event_portfolio,
)

PROTOCOL = ROOT / "docs/SHORT_TERM_US_CROSS_SECTIONAL_MOMENTUM_PROTOCOL.md"
OUTPUT_DEFAULT = ROOT / "artifacts/short_term_us_cross_sectional_momentum_diagnostic.json"
REPORT_DEFAULT = ROOT / "docs/SHORT_TERM_US_CROSS_SECTIONAL_MOMENTUM_REPORT.md"
BASELINE_EXCLUDED = set(PORTFOLIO_BASELINE_SYMBOLS)
TOP_K = 7
MOMENTUM_SESSIONS = 20
TREND_SESSIONS = 60
SCORE_THRESHOLD = 2.0
MIN_ACCEPTED_SIGNALS = 200
FIRST_HALF = (date(2023, 1, 1), date(2024, 12, 31))
SECOND_HALF = (date(2025, 1, 1), date(2026, 6, 30))


def _pct(value: float) -> str:
    return f"{value:.2%}"


def _load_inputs(prices_path: Path, liquidity_path: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    prices = load_long_total_return_prices(prices_path)
    liquidity = load_long_liquidity(liquidity_path)
    if prices.empty or liquidity.empty:
        raise ValueError("價格或流動性資料不可為空")
    price_symbols = set(prices["symbol"].unique())
    liquidity_symbols = set(liquidity["symbol"].unique())
    if price_symbols != liquidity_symbols:
        raise ValueError("價格與流動性 symbol 集合不一致")
    if not BASELINE_EXCLUDED.issubset(price_symbols):
        raise ValueError("缺少 QQQ／SPY／IWM 基準資料")
    return prices, liquidity


def _build_schedule(
    prices: pd.DataFrame,
    liquidity: pd.DataFrame,
    *,
    regime_gate: bool,
) -> tuple[list[dict[str, Any]], dict[str, int], list[str]]:
    qqq = prices[prices["symbol"].eq("QQQ")].sort_values("date")
    sessions = qqq["date"].tolist()
    positions = {day: index for index, day in enumerate(sessions)}
    universe = sorted(set(prices["symbol"].unique()) - BASELINE_EXCLUDED)
    prices_by_symbol = {
        symbol: frame.set_index("date").sort_index()
        for symbol, frame in prices.groupby("symbol")
    }
    liquidity_by_symbol = {
        symbol: frame.set_index("date").sort_index()
        for symbol, frame in liquidity.groupby("symbol")
    }
    qqq_frame = prices_by_symbol["QQQ"]
    active: dict[str, date] = {}
    candidates: list[dict[str, Any]] = []
    audit = {
        "signal_sessions": 0,
        "regime_off_sessions": 0,
        "no_eligible_candidates": 0,
        "missing_history_rows": 0,
        "liquidity_rejected_rows": 0,
        "score_rejected_sessions": 0,
        "capacity_rejected_candidates": 0,
        "selected_candidates": 0,
    }

    for index in range(TREND_SESSIONS, len(sessions) - 1):
        signal_day = sessions[index]
        entry_day = sessions[index + 1]
        audit["signal_sessions"] += 1
        for ticker, exit_day in list(active.items()):
            if entry_day > exit_day:
                del active[ticker]

        qqq_history = sessions[index - TREND_SESSIONS + 1 : index + 1]
        if any(day not in qqq_frame.index for day in qqq_history):
            raise ValueError("QQQ 趨勢歷史不完整")
        qqq_closes = qqq_frame.loc[qqq_history, "adj_close"].to_numpy(dtype=float)
        qqq_sma_20 = float(qqq_closes[-MOMENTUM_SESSIONS:].mean())
        qqq_sma_60 = float(qqq_closes.mean())
        if regime_gate and not (
            qqq_closes[-1] > qqq_sma_20 and qqq_closes[-1] > qqq_sma_60
        ):
            audit["regime_off_sessions"] += 1
            continue

        rows: list[dict[str, Any]] = []
        history = sessions[index - TREND_SESSIONS : index + 1]
        liquidity_history = sessions[index - MOMENTUM_SESSIONS : index]
        for ticker in universe:
            price_frame = prices_by_symbol[ticker]
            liquidity_frame = liquidity_by_symbol[ticker]
            if any(day not in price_frame.index or day not in liquidity_frame.index for day in history):
                audit["missing_history_rows"] += 1
                continue
            if any(day not in liquidity_frame.index for day in liquidity_history):
                audit["missing_history_rows"] += 1
                continue
            close = float(liquidity_frame.loc[signal_day, "close"])
            median_dollar_volume = float(
                liquidity_frame.loc[liquidity_history, "dollar_volume"].median()
            )
            if (
                close < PORTFOLIO_MIN_PRICE_USD
                or median_dollar_volume < PORTFOLIO_MIN_MEDIAN_DOLLAR_VOLUME_USD
            ):
                audit["liquidity_rejected_rows"] += 1
                continue
            closes = price_frame.loc[history, "adj_close"].to_numpy(dtype=float)
            momentum = closes[-1] / closes[-1 - MOMENTUM_SESSIONS] - 1.0
            trend = closes[-1] / closes[-TREND_SESSIONS:].mean() - 1.0
            rows.append({"ticker": ticker, "momentum": momentum, "trend": trend})

        if not rows:
            audit["no_eligible_candidates"] += 1
            continue
        ranked = pd.DataFrame(rows)
        ranked["score"] = (
            ranked["momentum"].rank(pct=True) * 3.0
            + ranked["trend"].rank(pct=True)
        )
        eligible = ranked[
            (ranked["score"] >= SCORE_THRESHOLD)
            & (ranked["momentum"] > 0.0)
            & (ranked["trend"] > 0.0)
        ].sort_values(["score", "ticker"], ascending=[False, True])
        if eligible.empty:
            audit["score_rejected_sessions"] += 1
            continue
        room = TOP_K - len(active)
        if room <= 0:
            audit["capacity_rejected_candidates"] += len(eligible)
            continue
        entry_position = positions[entry_day]
        exit_position = entry_position + PORTFOLIO_HOLDING_SESSIONS - 1
        if exit_position >= len(sessions):
            continue
        exit_day = sessions[exit_position]
        for row in eligible.itertuples(index=False):
            if room <= 0:
                break
            if row.ticker in active:
                audit["capacity_rejected_candidates"] += 1
                continue
            active[row.ticker] = exit_day
            candidates.append(
                {
                    "ticker": row.ticker,
                    "available_session": entry_day.isoformat(),
                    "score": float(row.score),
                    "signal_day": signal_day.isoformat(),
                }
            )
            audit["selected_candidates"] += 1
            room -= 1
    return candidates, audit, universe


def _prepare(
    candidates: list[dict[str, Any]],
    prices: pd.DataFrame,
    liquidity: pd.DataFrame,
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    signal_days = {
        (row["ticker"], row["available_session"]): row["signal_day"]
        for row in candidates
    }
    accepted, skipped = prepare_portfolio_signals(
        candidates,
        prices,
        holding_sessions=PORTFOLIO_HOLDING_SESSIONS,
        liquidity=liquidity,
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


def _simulation(signals: list[dict[str, Any]], prices: pd.DataFrame, cost_bps: float) -> dict[str, Any]:
    return simulate_event_portfolio(
        signals,
        prices,
        one_way_cost_bps=cost_bps,
        baseline_symbols=PORTFOLIO_BASELINE_SYMBOLS,
    )


def _scenario(
    signals: list[dict[str, Any]],
    prices: pd.DataFrame,
    cost_bps: float,
) -> dict[str, Any]:
    return {
        "all_period": _simulation(signals, prices, cost_bps),
        "fixed_halves": {
            "2023-01-01_2024-12-31": _simulation(
                _slice(signals, FIRST_HALF), prices, cost_bps
            ),
            "2025-01-01_2026-06-30": _simulation(
                _slice(signals, SECOND_HALF), prices, cost_bps
            ),
        },
    }


def _build_report(payload: dict[str, Any]) -> str:
    ten = payload["cost_scenarios"]["10"]["all_period"]
    twenty_five = payload["cost_scenarios"]["25"]["all_period"]
    fifty = payload["cost_scenarios"]["50"]["all_period"]
    first = payload["cost_scenarios"]["50"]["fixed_halves"]["2023-01-01_2024-12-31"]
    second = payload["cost_scenarios"]["50"]["fixed_halves"]["2025-01-01_2026-06-30"]
    control = payload["control_cost_scenarios"]["25"]["all_period"]
    gates = payload["decision"]["gates"]
    return dedent(
        f"""\
        # 美股短線 20／60 橫斷面動量研究報告

        版本：v1｜狀態：`{payload['decision']['strategy_status']}`｜用途：研究診斷，並非買入名單、Paper 指令或投資建議。

        ## 結論先行

        20 日動量 ×3、60 日趨勢 ×1、Top-7、20 sessions，加上 QQQ 20／60 regime gate，
        全期描述性 CAGR 高於同期 QQQ；但 50 bps 成本下前半段明顯落後，且輸入是現時大型股池，
        不能稱為已驗證可盈利策略。本輪是 post-hoc extension，不是獨立首次發現，故不升格。

        - regime 版本接受 {ten['signal_count']} 宗訊號；全期 10／25／50 bps 策略 CAGR 為 {_pct(ten['portfolio']['cagr'])}／{_pct(twenty_five['portfolio']['cagr'])}／{_pct(fifty['portfolio']['cagr'])}。
        - 50 bps 前半段策略／QQQ CAGR 為 {_pct(first['portfolio']['cagr'])}／{_pct(first['QQQ']['cagr'])}；後半段為 {_pct(second['portfolio']['cagr'])}／{_pct(second['QQQ']['cagr'])}。
        - 同規則不加 regime 的 25 bps control CAGR 為 {_pct(control['portfolio']['cagr'])}，最大跌幅 {_pct(control['portfolio']['max_drawdown'])}；regime 版為 {_pct(twenty_five['portfolio']['cagr'])}／{_pct(twenty_five['portfolio']['max_drawdown'])}。
        - regime 版 25 bps 年化換手 {twenty_five['annualized_turnover']:.2f}x，平均持倉 {twenty_five['average_active_positions']:.2f} 檔；成本與集中度不可忽略。

        ## 固定規則

        | 項目 | 凍結內容 |
        |---|---|
        | 評分 | `3 × percentile(20-session momentum) + percentile(close / 60-session SMA - 1)` |
        | 篩選 | score ≥ 2.0、兩項原始值均為正、流動性 ≥ US$20m 中位成交額、股價 ≥ US$5 |
        | 交易 | 收市產生訊號；下一 XNYS open 入場；等權 Top-7；20 sessions 強制離場 |
        | regime | QQQ 收市同時高於 20／60-session SMA；control 不使用此 gate |
        | 成本／基準 | 單邊 10／25／50 bps；QQQ、SPY、IWM |
        | 分段 | 2023–2024；2025–2026H1 |

        ## Regime 版本全期結果

        | 成本 | 訊號 | 策略 CAGR | QQQ CAGR | SPY CAGR | IWM CAGR | 策略最大跌幅 | QQQ 最大跌幅 | 策略 Sharpe |
        |---:|---:|---:|---:|---:|---:|---:|---:|---:|
        | 10 bps | {ten['signal_count']} | {_pct(ten['portfolio']['cagr'])} | {_pct(ten['QQQ']['cagr'])} | {_pct(ten['baselines']['SPY']['cagr'])} | {_pct(ten['baselines']['IWM']['cagr'])} | {_pct(ten['portfolio']['max_drawdown'])} | {_pct(ten['QQQ']['max_drawdown'])} | {ten['portfolio']['sharpe']:.2f} |
        | 25 bps | {twenty_five['signal_count']} | {_pct(twenty_five['portfolio']['cagr'])} | {_pct(twenty_five['QQQ']['cagr'])} | {_pct(twenty_five['baselines']['SPY']['cagr'])} | {_pct(twenty_five['baselines']['IWM']['cagr'])} | {_pct(twenty_five['portfolio']['max_drawdown'])} | {_pct(twenty_five['QQQ']['max_drawdown'])} | {twenty_five['portfolio']['sharpe']:.2f} |
        | 50 bps | {fifty['signal_count']} | {_pct(fifty['portfolio']['cagr'])} | {_pct(fifty['QQQ']['cagr'])} | {_pct(fifty['baselines']['SPY']['cagr'])} | {_pct(fifty['baselines']['IWM']['cagr'])} | {_pct(fifty['portfolio']['max_drawdown'])} | {_pct(fifty['QQQ']['max_drawdown'])} | {fifty['portfolio']['sharpe']:.2f} |

        ## 決策閘門

        - 通過：{sum(gates.values())}/{len(gates)}。
        - `{', '.join(key for key, value in gates.items() if not value)}` 未通過。
        - 現時 watchlist 只有 29 檔個股，沒有 point-in-time 成分、退市／收購回報、完整公司行動、sector 歷史或 high／low ATR。

        所有結果只寫入研究 log 與機器收據；`Paper=false`、`public_strategy_allowed=false`、實金 US$0。success-only 網頁維持「今天不下單」。

        機器收據：`artifacts/short_term_us_cross_sectional_momentum_diagnostic.json`；協議：`docs/SHORT_TERM_US_CROSS_SECTIONAL_MOMENTUM_PROTOCOL.md`。
        """
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="建立美股 20/60 橫斷面動量＋QQQ regime 診斷；不產生交易指令"
    )
    parser.add_argument("--prices", type=Path, required=True)
    parser.add_argument("--liquidity", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=OUTPUT_DEFAULT)
    parser.add_argument("--report", type=Path, default=REPORT_DEFAULT)
    parser.add_argument("--price-client", default="external_prepared_csv")
    parser.add_argument("--price-source-url", default="https://finance.yahoo.com/")
    args = parser.parse_args()

    prices, liquidity = _load_inputs(args.prices, args.liquidity)
    price_hash = sha256_file(args.prices)
    liquidity_hash = sha256_file(args.liquidity)
    regime_candidates, regime_audit, universe = _build_schedule(
        prices, liquidity, regime_gate=True
    )
    control_candidates, control_audit, control_universe = _build_schedule(
        prices, liquidity, regime_gate=False
    )
    if universe != control_universe:
        raise ValueError("regime 與 control universe 不一致")
    regime_signals, regime_skipped = _prepare(regime_candidates, prices, liquidity)
    control_signals, control_skipped = _prepare(control_candidates, prices, liquidity)
    cost_scenarios = {
        str(int(cost)): _scenario(regime_signals, prices, cost)
        for cost in PORTFOLIO_COST_SCENARIOS
    }
    control_cost_scenarios = {
        str(int(cost)): _scenario(control_signals, prices, cost)
        for cost in PORTFOLIO_COST_SCENARIOS
    }
    ten = cost_scenarios["10"]["all_period"]
    twenty_five = cost_scenarios["25"]["all_period"]
    fifty = cost_scenarios["50"]["all_period"]
    first_fifty = cost_scenarios["50"]["fixed_halves"]["2023-01-01_2024-12-31"]
    second_fifty = cost_scenarios["50"]["fixed_halves"]["2025-01-01_2026-06-30"]
    gates = {
        "minimum_200_accepted_signals": ten["signal_count"] >= MIN_ACCEPTED_SIGNALS,
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
        "status": "post_hoc_us_cross_sectional_momentum_diagnostic",
        "protocol": {
            "path": str(PROTOCOL.relative_to(ROOT)),
            "sha256": sha256_file(PROTOCOL),
            "momentum_sessions": MOMENTUM_SESSIONS,
            "trend_sessions": TREND_SESSIONS,
            "score_threshold": SCORE_THRESHOLD,
            "top_k": TOP_K,
            "holding_sessions": PORTFOLIO_HOLDING_SESSIONS,
            "baseline_symbols": list(PORTFOLIO_BASELINE_SYMBOLS),
            "cost_scenarios_bps": list(PORTFOLIO_COST_SCENARIOS),
            "min_price_usd": PORTFOLIO_MIN_PRICE_USD,
            "min_median_dollar_volume_usd": PORTFOLIO_MIN_MEDIAN_DOLLAR_VOLUME_USD,
        },
        "price_source": {
            "filename": args.prices.name,
            "sha256": price_hash,
            "url": args.price_source_url,
            "client": args.price_client,
            "row_count": int(len(prices)),
            "symbol_count": int(prices["symbol"].nunique()),
            "session_start": min(prices["date"]).isoformat(),
            "session_end": max(prices["date"]).isoformat(),
        },
        "liquidity_source": {
            "filename": args.liquidity.name,
            "sha256": liquidity_hash,
            "row_count": int(len(liquidity)),
            "symbol_count": int(liquidity["symbol"].nunique()),
        },
        "universe": {
            "stock_symbols": universe,
            "stock_symbol_count": len(universe),
            "excluded_baselines": sorted(BASELINE_EXCLUDED),
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
            "diagnostic_status": "negative_persistence_and_data_boundary",
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
            "reason": "The regime result is concentrated in the later half and uses a current-watchlist universe without point-in-time membership or delisting data; it is not an investable proof.",
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
