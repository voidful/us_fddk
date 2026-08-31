from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

from usfddk.sec_insider import parse_insider_purchases, sha256_file
from usfddk.sec_insider_forward import load_long_total_return_prices
from usfddk.sec_insider_multi import EXPECTED_QUARTERS, build_quarter_candidates
from usfddk.sec_insider_portfolio import (
    PORTFOLIO_BASELINE_SYMBOLS,
    PORTFOLIO_COST_SCENARIOS,
    PORTFOLIO_HOLDING_SESSIONS,
    PORTFOLIO_MIN_MEDIAN_DOLLAR_VOLUME_USD,
    PORTFOLIO_MIN_PRICE_USD,
    PORTFOLIO_ONE_WAY_COST_BPS,
    PORTFOLIO_TREND_LOOKBACK_SESSIONS,
    PORTFOLIO_TREND_MOMENTUM_SESSIONS,
    load_long_liquidity,
    prepare_portfolio_signals,
    simulate_event_portfolio,
)

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "docs/SHORT_TERM_SEC_INSIDER_TREND_PROTOCOL.md"


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False)
        + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def _load_manifest(path: Path) -> list[dict]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = payload.get("quarters")
    expected = [label for label, _ in EXPECTED_QUARTERS]
    if not isinstance(rows, list) or [row.get("label") for row in rows] != expected:
        raise ValueError("manifest 必須依序包含 2024Q1 至 2026Q2")
    for row, (label, expected_end) in zip(rows, EXPECTED_QUARTERS, strict=True):
        if row.get("as_of") != expected_end.isoformat() or not Path(row["path"]).is_file():
            raise ValueError(f"{label} manifest 欄位或 SEC ZIP 不符")
    return rows


def _prepare(
    rows: list[dict],
    prices,
    liquidity,
) -> tuple[list[dict], dict[str, int]]:
    return prepare_portfolio_signals(
        rows,
        prices,
        liquidity=liquidity,
        min_price_usd=PORTFOLIO_MIN_PRICE_USD,
        min_median_dollar_volume_usd=PORTFOLIO_MIN_MEDIAN_DOLLAR_VOLUME_USD,
        trend_filter=True,
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="建立 SEC insider + 60/20 trend 共振研究收據；不產生交易指令"
    )
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--prices", type=Path, required=True)
    parser.add_argument("--liquidity", type=Path, required=True)
    parser.add_argument("--price-client", default="external_prepared_csv")
    parser.add_argument("--price-source-url", default="https://finance.yahoo.com/")
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "artifacts/short_term_sec_insider_trend_diagnostic.json",
    )
    args = parser.parse_args()
    manifest = _load_manifest(args.manifest)
    for path, label in ((args.prices, "price CSV"), (args.liquidity, "liquidity CSV")):
        if not path.is_file():
            raise SystemExit(f"{label} 不存在：{path}")

    quarter_events = []
    sec_sources = []
    total_events = 0
    for row in manifest:
        source = Path(row["path"])
        events = parse_insider_purchases(source)
        quarter_events.append((row["label"], date.fromisoformat(row["as_of"]), events))
        total_events += len(events)
        sec_sources.append(
            {
                "label": row["label"],
                "as_of": row["as_of"],
                "filename": source.name,
                "sha256": sha256_file(source),
                "url": row.get("url"),
                "event_count": len(events),
            }
        )

    prices = load_long_total_return_prices(args.prices)
    liquidity = load_long_liquidity(args.liquidity)
    quarter_candidates = build_quarter_candidates(quarter_events)
    flattened = [row for label in quarter_candidates for row in quarter_candidates[label]]
    accepted, skipped = _prepare(flattened, prices, liquidity)
    early_rows = [
        row for label in list(quarter_candidates)[:5] for row in quarter_candidates[label]
    ]
    late_rows = [
        row for label in list(quarter_candidates)[5:] for row in quarter_candidates[label]
    ]
    early_accepted, early_skipped = _prepare(early_rows, prices, liquidity)
    late_accepted, late_skipped = _prepare(late_rows, prices, liquidity)

    diagnostic = {
        "all_period": simulate_event_portfolio(
            accepted, prices, baseline_symbols=PORTFOLIO_BASELINE_SYMBOLS
        ),
        "fixed_halves": {
            "2024Q1_2025Q1": simulate_event_portfolio(
                early_accepted, prices, baseline_symbols=PORTFOLIO_BASELINE_SYMBOLS
            ),
            "2025Q2_2026Q2": simulate_event_portfolio(
                late_accepted, prices, baseline_symbols=PORTFOLIO_BASELINE_SYMBOLS
            ),
        },
    }
    cost_scenarios = {}
    for cost_bps in PORTFOLIO_COST_SCENARIOS:
        cost_scenarios[str(int(cost_bps))] = {
            "all_period": simulate_event_portfolio(
                accepted,
                prices,
                one_way_cost_bps=cost_bps,
                baseline_symbols=PORTFOLIO_BASELINE_SYMBOLS,
            ),
            "fixed_halves": {
                "2024Q1_2025Q1": simulate_event_portfolio(
                    early_accepted,
                    prices,
                    one_way_cost_bps=cost_bps,
                    baseline_symbols=PORTFOLIO_BASELINE_SYMBOLS,
                ),
                "2025Q2_2026Q2": simulate_event_portfolio(
                    late_accepted,
                    prices,
                    one_way_cost_bps=cost_bps,
                    baseline_symbols=PORTFOLIO_BASELINE_SYMBOLS,
                ),
            },
        }

    payload = {
        "schema_version": 1,
        "status": "post_hoc_fixed_event_portfolio_trend_diagnostic",
        "protocol": {
            "path": "docs/SHORT_TERM_SEC_INSIDER_TREND_PROTOCOL.md",
            "sha256": sha256_file(PROTOCOL),
            "holding_sessions": PORTFOLIO_HOLDING_SESSIONS,
            "one_way_cost_bps": PORTFOLIO_ONE_WAY_COST_BPS,
            "baseline_symbols": list(PORTFOLIO_BASELINE_SYMBOLS),
            "min_price_usd": PORTFOLIO_MIN_PRICE_USD,
            "min_median_dollar_volume_usd": PORTFOLIO_MIN_MEDIAN_DOLLAR_VOLUME_USD,
            "trend_lookback_sessions": PORTFOLIO_TREND_LOOKBACK_SESSIONS,
            "trend_momentum_sessions": PORTFOLIO_TREND_MOMENTUM_SESSIONS,
        },
        "sec_sources": sec_sources,
        "sec_input_counts": {
            "package_count": len(sec_sources),
            "raw_event_count": total_events,
            "candidate_count": len(flattened),
            "candidate_issuer_count": len({row["ticker"] for row in flattened}),
        },
        "price_source": {
            "filename": args.prices.name,
            "sha256": sha256_file(args.prices),
            "url": args.price_source_url,
            "client": args.price_client,
            "symbol_count": int(prices["symbol"].nunique()),
            "row_count": int(len(prices)),
        },
        "liquidity_source": {
            "filename": args.liquidity.name,
            "sha256": sha256_file(args.liquidity),
            "row_count": int(len(liquidity)),
            "symbol_count": int(liquidity["symbol"].nunique()),
            "columns": ["close", "dollar_volume"],
        },
        "signal_filter": {
            "candidate_count": len(flattened),
            "accepted_count": len(accepted),
            "skipped": skipped,
            "fixed_half_accepted_counts": {
                "2024Q1_2025Q1": len(early_accepted),
                "2025Q2_2026Q2": len(late_accepted),
            },
            "fixed_half_skipped": {
                "2024Q1_2025Q1": early_skipped,
                "2025Q2_2026Q2": late_skipped,
            },
        },
        "diagnostic": diagnostic,
        "cost_scenarios": cost_scenarios,
        "decision": {
            "strategy_status": "research_candidate_only",
            "formal_backtest_completed": False,
            "paper_authorized": False,
            "public_strategy_allowed": False,
            "real_money_action_usd": 0,
            "reason": (
                "Trend extension uses exploratory prices and no point-in-time universe, "
                "delisting returns, corporate actions, or formal risk-free package."
            ),
        },
    }
    _write_json(args.output, payload)
    all_period = diagnostic["all_period"]
    print(
        json.dumps(
            {
                "status": payload["status"],
                "candidate_count": len(flattened),
                "accepted_count": len(accepted),
                "portfolio_cagr": all_period["portfolio"]["cagr"],
                "qqq_cagr": all_period["QQQ"]["cagr"],
                "output": str(args.output),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
