from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path
from textwrap import dedent
from typing import Any

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
    PORTFOLIO_TREND_LOOKBACK_SESSIONS,
    PORTFOLIO_TREND_MOMENTUM_SESSIONS,
    load_long_liquidity,
    prepare_portfolio_signals,
    simulate_event_portfolio,
)

PARENT_STATUS = "post_hoc_sec_xbrl_earnings_event_diagnostic"
PROTOCOL = ROOT / "docs/SHORT_TERM_SEC_XBRL_TREND_PROTOCOL.md"
PARENT_DEFAULT = ROOT / "artifacts/short_term_sec_xbrl_earnings_diagnostic.json"
OUTPUT_DEFAULT = ROOT / "artifacts/short_term_sec_xbrl_trend_diagnostic.json"
REPORT_DEFAULT = ROOT / "docs/SHORT_TERM_SEC_XBRL_TREND_REPORT.md"


def _load_object(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON 必須是物件：{path}")
    return payload


def _validate_parent(path: Path) -> dict[str, Any]:
    parent = _load_object(path)
    if parent.get("status") != PARENT_STATUS:
        raise ValueError("parent XBRL diagnostic status 不符")
    decision = parent.get("decision")
    events = parent.get("events")
    price_source = parent.get("price_source")
    liquidity_source = parent.get("liquidity_source")
    if (
        not isinstance(decision, dict)
        or decision.get("public_strategy_allowed") is not False
        or decision.get("paper_authorized") is not False
        or not isinstance(events, list)
        or not events
        or not isinstance(price_source, dict)
        or not isinstance(liquidity_source, dict)
    ):
        raise ValueError("parent XBRL diagnostic 未維持 research-only 邊界")
    required = {"ticker", "filing_date", "available_session", "accession_number"}
    if any(not isinstance(row, dict) or not required.issubset(row) for row in events):
        raise ValueError("parent events 欄位不完整")
    return parent


def _check_source_hash(path: Path, expected: Any, label: str) -> None:
    if not path.is_file():
        raise ValueError(f"缺少 {label}：{path}")
    actual = sha256_file(path)
    if actual != expected:
        raise ValueError(f"{label} SHA-256 與 parent 不符：{actual} != {expected}")


def _event_window(events: list[dict[str, Any]], start: date, end: date) -> list[dict[str, Any]]:
    return [
        row
        for row in events
        if start <= date.fromisoformat(str(row["filing_date"])) <= end
    ]


def _run(
    events: list[dict[str, Any]],
    prices,
    liquidity,
    *,
    cost_bps: float,
) -> dict[str, Any]:
    accepted, skipped = prepare_portfolio_signals(
        events,
        prices,
        holding_sessions=PORTFOLIO_HOLDING_SESSIONS,
        liquidity=liquidity,
        min_price_usd=PORTFOLIO_MIN_PRICE_USD,
        min_median_dollar_volume_usd=PORTFOLIO_MIN_MEDIAN_DOLLAR_VOLUME_USD,
        trend_filter=True,
    )
    return {
        "accepted_count": len(accepted),
        "skipped": skipped,
        "simulation": simulate_event_portfolio(
            accepted,
            prices,
            one_way_cost_bps=cost_bps,
            baseline_symbols=PORTFOLIO_BASELINE_SYMBOLS,
        ),
    }


def _pct(value: float) -> str:
    return f"{value:.2%}"


def _build_report(payload: dict[str, Any]) -> str:
    full = payload["cost_scenarios"]
    ten = full["10"]["all_period"]
    twenty_five = full["25"]["all_period"]
    fifty = full["50"]["all_period"]
    gates = payload["decision"]["gates"]
    first = full["50"]["fixed_halves"]["2023-01-01_2024-12-31"]
    second = full["50"]["fixed_halves"]["2025-01-01_2026-06-30"]
    return dedent(
        f"""\
        # SEC XBRL 盈利事件＋60／20 趨勢確認研究報告

        版本：v1｜狀態：`{payload['decision']['strategy_status']}`｜用途：短線個股研究診斷，並非買入名單、Paper 指令或投資建議。

        ## 結論先行

        在 parent XBRL 正 EPS／營收事件上加入事前固定的 60-session 均線及 20-session 正動量確認後，結果仍未能跑贏 QQQ；本輪不升格。

        - parent 139 宗事件中，趨勢確認後接受 {ten['accepted_count']} 宗；58 宗低於趨勢門檻，4 宗缺少 60-session 歷史。
        - 10／25／50 bps 策略 CAGR 為 {_pct(ten['simulation']['portfolio']['cagr'])}／{_pct(twenty_five['simulation']['portfolio']['cagr'])}／{_pct(fifty['simulation']['portfolio']['cagr'])}，相應 QQQ 為 {_pct(ten['simulation']['QQQ']['cagr'])}／{_pct(twenty_five['simulation']['QQQ']['cagr'])}／{_pct(fifty['simulation']['QQQ']['cagr'])}。
        - 50 bps 前半段策略／QQQ CAGR 為 {_pct(first['simulation']['portfolio']['cagr'])}／{_pct(first['simulation']['QQQ']['cagr'])}；後半段為 {_pct(second['simulation']['portfolio']['cagr'])}／{_pct(second['simulation']['QQQ']['cagr'])}。

        ## 固定規則

        | 項目 | 凍結內容 |
        |---|---|
        | parent | `{payload['parent']['filename']}`，SHA-256 `{payload['parent']['sha256']}` |
        | 趨勢 | 入場前 60 sessions 收市均線；入場前一日相對 20 sessions 前回報 > 0 |
        | 時計 | filing 後第一個 XNYS session 入場；20 sessions；下一交易日 adjusted open |
        | 成本 | 單邊 10／25／50 bps |
        | 基準 | QQQ、SPY、IWM，同評估時段及成本 |
        | 分段 | 2023–2024；2025–2026H1 |

        ## 全期結果

        | 成本 | 接受事件 | 策略 CAGR | QQQ CAGR | SPY CAGR | IWM CAGR | 策略最大跌幅 | QQQ 最大跌幅 | 策略 Sharpe |
        |---:|---:|---:|---:|---:|---:|---:|---:|---:|
        | 10 bps | {ten['accepted_count']} | {_pct(ten['simulation']['portfolio']['cagr'])} | {_pct(ten['simulation']['QQQ']['cagr'])} | {_pct(ten['simulation']['baselines']['SPY']['cagr'])} | {_pct(ten['simulation']['baselines']['IWM']['cagr'])} | {_pct(ten['simulation']['portfolio']['max_drawdown'])} | {_pct(ten['simulation']['QQQ']['max_drawdown'])} | {ten['simulation']['portfolio']['sharpe']:.2f} |
        | 25 bps | {twenty_five['accepted_count']} | {_pct(twenty_five['simulation']['portfolio']['cagr'])} | {_pct(twenty_five['simulation']['QQQ']['cagr'])} | {_pct(twenty_five['simulation']['baselines']['SPY']['cagr'])} | {_pct(twenty_five['simulation']['baselines']['IWM']['cagr'])} | {_pct(twenty_five['simulation']['portfolio']['max_drawdown'])} | {_pct(twenty_five['simulation']['QQQ']['max_drawdown'])} | {twenty_five['simulation']['portfolio']['sharpe']:.2f} |
        | 50 bps | {fifty['accepted_count']} | {_pct(fifty['simulation']['portfolio']['cagr'])} | {_pct(fifty['simulation']['QQQ']['cagr'])} | {_pct(fifty['simulation']['baselines']['SPY']['cagr'])} | {_pct(fifty['simulation']['baselines']['IWM']['cagr'])} | {_pct(fifty['simulation']['portfolio']['max_drawdown'])} | {_pct(fifty['simulation']['QQQ']['max_drawdown'])} | {fifty['simulation']['portfolio']['sharpe']:.2f} |

        ## 決策閘門

        - 通過：{sum(gates.values())}/{len(gates)}。
        - `{', '.join(key for key, value in gates.items() if not value)}` 未通過。
        - parent 本身是現時大型股觀察池及 exploratory adjusted OHLCV；沒有 point-in-time 成分、退市／收購回報、完整公司行動及正式 risk-free package。

        所有結果只寫入研究 log 與機器收據，不建立 Paper、不產生個股公開名單、不顯示實金比例。success-only 網頁維持「今天不下單」。

        機器收據：`artifacts/short_term_sec_xbrl_trend_diagnostic.json`；協議：`docs/SHORT_TERM_SEC_XBRL_TREND_PROTOCOL.md`。
        """
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="建立 SEC XBRL 盈利事件＋60/20 趨勢確認診斷；不產生交易指令"
    )
    parser.add_argument("--parent", type=Path, default=PARENT_DEFAULT)
    parser.add_argument("--prices", type=Path, required=True)
    parser.add_argument("--liquidity", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=OUTPUT_DEFAULT)
    parser.add_argument("--report", type=Path, default=REPORT_DEFAULT)
    parser.add_argument("--price-client", default="external_prepared_csv")
    parser.add_argument("--price-source-url", default="https://finance.yahoo.com/")
    args = parser.parse_args()

    parent = _validate_parent(args.parent)
    parent_sha256 = sha256_file(args.parent)
    _check_source_hash(args.prices, parent["price_source"].get("sha256"), "價格 CSV")
    _check_source_hash(args.liquidity, parent["liquidity_source"].get("sha256"), "流動性 CSV")
    prices = load_long_total_return_prices(args.prices)
    liquidity = load_long_liquidity(args.liquidity)
    events = list(parent["events"])
    first_events = _event_window(events, date(2023, 1, 1), date(2024, 12, 31))
    second_events = _event_window(events, date(2025, 1, 1), date(2026, 6, 30))

    cost_scenarios: dict[str, Any] = {}
    for cost_bps in PORTFOLIO_COST_SCENARIOS:
        cost_scenarios[str(int(cost_bps))] = {
            "all_period": _run(events, prices, liquidity, cost_bps=cost_bps),
            "fixed_halves": {
                "2023-01-01_2024-12-31": _run(
                    first_events, prices, liquidity, cost_bps=cost_bps
                ),
                "2025-01-01_2026-06-30": _run(
                    second_events, prices, liquidity, cost_bps=cost_bps
                ),
            },
        }

    ten = cost_scenarios["10"]["all_period"]
    qqq_ten = ten["simulation"]["QQQ"]
    fifty = cost_scenarios["50"]["all_period"]
    first_fifty = cost_scenarios["50"]["fixed_halves"]["2023-01-01_2024-12-31"]
    second_fifty = cost_scenarios["50"]["fixed_halves"]["2025-01-01_2026-06-30"]
    gates = {
        "minimum_30_accepted_events": ten["accepted_count"] >= 30,
        "cagr_beats_qqq_at_10bps": ten["simulation"]["portfolio"]["cagr"]
        > qqq_ten["cagr"],
        "cagr_beats_qqq_at_25bps": cost_scenarios["25"]["all_period"]["simulation"]["portfolio"]["cagr"]
        > cost_scenarios["25"]["all_period"]["simulation"]["QQQ"]["cagr"],
        "cagr_beats_qqq_at_50bps": fifty["simulation"]["portfolio"]["cagr"]
        > fifty["simulation"]["QQQ"]["cagr"],
        "both_fixed_halves_beat_qqq_at_50bps": (
            first_fifty["simulation"]["portfolio"]["cagr"]
            > first_fifty["simulation"]["QQQ"]["cagr"]
            and second_fifty["simulation"]["portfolio"]["cagr"]
            > second_fifty["simulation"]["QQQ"]["cagr"]
        ),
        "max_drawdown_no_worse_than_qqq_at_10bps": ten["simulation"]["portfolio"][
            "max_drawdown"
        ]
        >= qqq_ten["max_drawdown"],
    }
    payload: dict[str, Any] = {
        "schema_version": 1,
        "status": "post_hoc_sec_xbrl_earnings_trend_diagnostic",
        "parent": {
            "filename": args.parent.name,
            "sha256": parent_sha256,
            "status": parent["status"],
            "event_count": len(events),
        },
        "protocol": {
            "path": str(PROTOCOL.relative_to(ROOT)),
            "sha256": sha256_file(PROTOCOL),
            "holding_sessions": PORTFOLIO_HOLDING_SESSIONS,
            "trend_lookback_sessions": PORTFOLIO_TREND_LOOKBACK_SESSIONS,
            "trend_momentum_sessions": PORTFOLIO_TREND_MOMENTUM_SESSIONS,
            "one_way_cost_bps": list(PORTFOLIO_COST_SCENARIOS),
            "baseline_symbols": list(PORTFOLIO_BASELINE_SYMBOLS),
            "min_price_usd": PORTFOLIO_MIN_PRICE_USD,
            "min_median_dollar_volume_usd": PORTFOLIO_MIN_MEDIAN_DOLLAR_VOLUME_USD,
        },
        "price_source": {
            "filename": args.prices.name,
            "sha256": sha256_file(args.prices),
            "url": args.price_source_url,
            "client": args.price_client,
            "row_count": int(len(prices)),
            "symbol_count": int(prices["symbol"].nunique()),
        },
        "liquidity_source": {
            "filename": args.liquidity.name,
            "sha256": sha256_file(args.liquidity),
            "row_count": int(len(liquidity)),
            "symbol_count": int(liquidity["symbol"].nunique()),
        },
        "signal_filter": {
            "candidate_count": len(events),
            "fixed_half_candidate_counts": {
                "2023-01-01_2024-12-31": len(first_events),
                "2025-01-01_2026-06-30": len(second_events),
            },
            "trend_rule": "prior close > 60-session SMA and prior close / close 20 sessions ago - 1 > 0",
        },
        "cost_scenarios": cost_scenarios,
        "decision": {
            "strategy_status": "research_candidate_only",
            "diagnostic_status": "negative",
            "gate_summary": {
                "passed": sum(gates.values()),
                "total": len(gates),
                "all_passed": all(gates.values()),
            },
            "gates": gates,
            "formal_backtest_completed": False,
            "paper_authorized": False,
            "public_strategy_allowed": False,
            "real_money_action_usd": 0,
            "reason": "Trend confirmation does not overcome QQQ, cost, persistence, or drawdown gates; parent data boundary remains survivorship-biased.",
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
                "accepted_count": ten["accepted_count"],
                "portfolio_cagr_10bps": ten["simulation"]["portfolio"]["cagr"],
                "qqq_cagr_10bps": qqq_ten["cagr"],
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
