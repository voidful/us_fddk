from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter
from datetime import date
from pathlib import Path
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
    load_long_liquidity,
    prepare_portfolio_signals,
    simulate_event_portfolio,
)
from usfddk.sec_xbrl_earnings import (  # noqa: E402
    ALLOWED_FISCAL_PERIODS,
    ALLOWED_FORMS,
    EVENT_END,
    EVENT_START,
    FACTS_CUTOFF,
    MAX_DURATION_DAYS,
    MIN_DURATION_DAYS,
    REVENUE_TAGS,
    build_positive_growth_events,
    load_company_facts,
)

PROTOCOL = ROOT / "docs/SHORT_TERM_SEC_XBRL_EARNINGS_PROTOCOL.md"
WATCHLIST_DEFAULT = ROOT / "usfddk/resources/us_large_cap_watchlist_v1.csv"


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def _load_watchlist(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    required = {"symbol", "name", "sector", "source_weight_pct", "as_of"}
    if not rows or not required.issubset(rows[0]):
        raise ValueError("watchlist 欄位不完整")
    normalized: list[dict[str, str]] = []
    seen_symbols: set[str] = set()
    for row in rows:
        symbol = str(row.get("symbol", "")).strip().upper()
        if not symbol or symbol in seen_symbols:
            raise ValueError("watchlist 有空白或重複 symbol")
        seen_symbols.add(symbol)
        normalized.append({key: str(row.get(key, "")).strip() for key in required})
    return normalized


def _load_universe_map(path: Path, watchlist: list[dict[str, str]]) -> list[dict[str, str]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = payload.get("rows") if isinstance(payload, dict) else None
    if not isinstance(rows, list) or not rows:
        raise ValueError("universe map 必須含 rows 陣列")
    watch_by_symbol = {row["symbol"]: row for row in watchlist}
    seen_cik: set[str] = set()
    normalized: list[dict[str, str]] = []
    for raw in rows:
        if not isinstance(raw, dict):
            raise ValueError("universe map row 必須是物件")
        symbol = str(raw.get("symbol", "")).strip().upper()
        cik = str(raw.get("cik", "")).strip()
        if symbol not in watch_by_symbol or len(cik) != 10 or not cik.isdigit():
            raise ValueError(f"universe map symbol/CIK 無效：{symbol}/{cik}")
        if cik in seen_cik:
            raise ValueError(f"universe map 有重複 CIK：{cik}")
        seen_cik.add(cik)
        normalized.append({"symbol": symbol, "cik": cik})
    if len(normalized) != len(watchlist) - 1:
        raise ValueError("universe map 與 frozen watchlist 覆蓋範圍不符")
    # The map is required to preserve watchlist order.  The one omitted row is
    # the duplicate share class resolved by the separately frozen CIK map.
    watch_symbols = [row["symbol"] for row in watchlist]
    map_symbols = [row["symbol"] for row in normalized]
    cursor = iter(watch_symbols)
    if any(not any(candidate == symbol for candidate in cursor) for symbol in map_symbols):
        raise ValueError("universe map symbols 不是 frozen watchlist 的有序代表子序列")
    return normalized


def _event_window(events: list[dict[str, Any]], start: date, end: date) -> list[dict[str, Any]]:
    return [row for row in events if start <= date.fromisoformat(str(row["filing_date"])) <= end]


def _run_scenario(
    events: list[dict[str, Any]],
    prices,
    liquidity,
    *,
    cost_bps: float,
) -> dict[str, Any]:
    accepted, skipped = prepare_portfolio_signals(
        events,
        prices,
        liquidity=liquidity,
        min_price_usd=PORTFOLIO_MIN_PRICE_USD,
        min_median_dollar_volume_usd=PORTFOLIO_MIN_MEDIAN_DOLLAR_VOLUME_USD,
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


def main() -> int:
    parser = argparse.ArgumentParser(
        description="建立 SEC XBRL 正 EPS/營收事件研究收據；不產生 Paper 或交易指令"
    )
    parser.add_argument("--universe", type=Path, default=WATCHLIST_DEFAULT)
    parser.add_argument("--universe-map", type=Path, required=True)
    parser.add_argument("--facts-dir", type=Path, required=True)
    parser.add_argument("--prices", type=Path, required=True)
    parser.add_argument("--liquidity", type=Path, required=True)
    parser.add_argument("--price-client", default="external_prepared_csv")
    parser.add_argument("--price-source-url", default="https://finance.yahoo.com/")
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "artifacts/short_term_sec_xbrl_earnings_diagnostic.json",
    )
    args = parser.parse_args()
    for path, label in (
        (args.universe, "watchlist"),
        (args.universe_map, "universe map"),
        (args.facts_dir, "facts directory"),
        (args.prices, "price CSV"),
        (args.liquidity, "liquidity CSV"),
    ):
        if not path.exists():
            raise SystemExit(f"{label} 不存在：{path}")

    watchlist = _load_watchlist(args.universe)
    universe_map = _load_universe_map(args.universe_map, watchlist)
    prices = load_long_total_return_prices(args.prices)
    liquidity = load_long_liquidity(args.liquidity)
    qqq_sessions = sorted(prices.loc[prices["symbol"].eq("QQQ"), "date"].tolist())
    if not qqq_sessions:
        raise ValueError("price snapshot 缺少 QQQ sessions")

    events: list[dict[str, Any]] = []
    facts_sources: list[dict[str, Any]] = []
    per_symbol_counts: dict[str, dict[str, int]] = {}
    for mapping in universe_map:
        symbol = mapping["symbol"]
        cik = mapping["cik"]
        source = args.facts_dir / f"CIK{cik}.json"
        if not source.is_file():
            raise ValueError(f"缺少固定 CIK facts：{source}")
        payload = load_company_facts(source)
        symbol_events, counts = build_positive_growth_events(
            symbol,
            payload,
            qqq_sessions,
            event_start=EVENT_START,
            event_end=EVENT_END,
            cutoff=FACTS_CUTOFF,
        )
        events.extend(symbol_events)
        per_symbol_counts[symbol] = counts
        facts_sources.append(
            {
                "symbol": symbol,
                "cik": cik,
                "filename": source.name,
                "sha256": sha256_file(source),
                "entity_name": payload.get("entityName"),
                "event_count": len(symbol_events),
                "counts": counts,
            }
        )

    events.sort(key=lambda row: (row["filing_date"], row["ticker"], row["accession_number"]))
    all_events = events
    first_half = _event_window(all_events, date(2023, 1, 1), date(2024, 12, 31))
    second_half = _event_window(all_events, date(2025, 1, 1), date(2026, 6, 30))
    scenarios: dict[str, Any] = {}
    for cost_bps in PORTFOLIO_COST_SCENARIOS:
        scenarios[str(int(cost_bps))] = {
            "all_period": _run_scenario(all_events, prices, liquidity, cost_bps=cost_bps),
            "fixed_halves": {
                "2023-01-01_2024-12-31": _run_scenario(
                    first_half, prices, liquidity, cost_bps=cost_bps
                ),
                "2025-01-01_2026-06-30": _run_scenario(
                    second_half, prices, liquidity, cost_bps=cost_bps
                ),
            },
        }

    aggregate_counts: Counter[str] = Counter()
    for counts in per_symbol_counts.values():
        aggregate_counts.update(counts)
    first_run = scenarios[str(int(PORTFOLIO_COST_SCENARIOS[0]))]["all_period"]
    payload: dict[str, Any] = {
        "schema_version": 1,
        "status": "post_hoc_sec_xbrl_earnings_event_diagnostic",
        "protocol": {
            "path": "docs/SHORT_TERM_SEC_XBRL_EARNINGS_PROTOCOL.md",
            "sha256": sha256_file(PROTOCOL),
            "facts_cutoff": FACTS_CUTOFF.isoformat(),
            "event_window": {
                "start": EVENT_START.isoformat(),
                "end": EVENT_END.isoformat(),
            },
            "forms": list(ALLOWED_FORMS),
            "fiscal_periods": list(ALLOWED_FISCAL_PERIODS),
            "duration_days": {"min": MIN_DURATION_DAYS, "max": MAX_DURATION_DAYS},
            "revenue_tag_priority": list(REVENUE_TAGS),
            "holding_sessions": PORTFOLIO_HOLDING_SESSIONS,
            "one_way_cost_bps": list(PORTFOLIO_COST_SCENARIOS),
            "baseline_symbols": list(PORTFOLIO_BASELINE_SYMBOLS),
            "min_price_usd": PORTFOLIO_MIN_PRICE_USD,
            "min_median_dollar_volume_usd": PORTFOLIO_MIN_MEDIAN_DOLLAR_VOLUME_USD,
        },
        "universe": {
            "watchlist_filename": args.universe.name,
            "watchlist_sha256": sha256_file(args.universe),
            "watchlist_row_count": len(watchlist),
            "representative_count": len(universe_map),
            "map_filename": args.universe_map.name,
            "map_sha256": sha256_file(args.universe_map),
            "symbols": [row["symbol"] for row in universe_map],
            "as_of": sorted({row["as_of"] for row in watchlist}),
        },
        "facts_source": {
            "api": "https://data.sec.gov/api/xbrl/companyfacts/",
            "directory": args.facts_dir.name,
            "file_count": len(facts_sources),
            "files": facts_sources,
        },
        "price_source": {
            "filename": args.prices.name,
            "sha256": sha256_file(args.prices),
            "url": args.price_source_url,
            "client": args.price_client,
            "row_count": int(len(prices)),
            "symbol_count": int(prices["symbol"].nunique()),
            "session_start": min(qqq_sessions).isoformat(),
            "session_end": max(qqq_sessions).isoformat(),
        },
        "liquidity_source": {
            "filename": args.liquidity.name,
            "sha256": sha256_file(args.liquidity),
            "row_count": int(len(liquidity)),
            "symbol_count": int(liquidity["symbol"].nunique()),
            "columns": ["close", "dollar_volume"],
        },
        "event_filter": {
            "raw_event_count": len(events),
            "issuer_count": len({row["ticker"] for row in events}),
            "aggregate_counts": dict(sorted(aggregate_counts.items())),
            "per_symbol": per_symbol_counts,
        },
        "events": events,
        "cost_scenarios": scenarios,
        "decision": {
            "strategy_status": "research_candidate_only",
            "formal_backtest_completed": False,
            "paper_authorized": False,
            "public_strategy_allowed": False,
            "real_money_action_usd": 0,
            "reason": (
                "Current-watchlist SEC XBRL events with exploratory Yahoo prices; no "
                "point-in-time membership, delisting returns, complete corporate-action "
                "ledger, or formal risk-free package."
            ),
        },
    }
    _write_json(args.output, payload)
    print(
        json.dumps(
            {
                "status": payload["status"],
                "event_count": len(events),
                "liquidity_accepted_count": first_run["accepted_count"],
                "ten_bps_portfolio_cagr": first_run["simulation"]["portfolio"]["cagr"],
                "ten_bps_qqq_cagr": first_run["simulation"]["QQQ"]["cagr"],
                "output": str(args.output),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
