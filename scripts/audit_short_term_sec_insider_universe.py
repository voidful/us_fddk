from __future__ import annotations

import argparse
import csv
import json
from datetime import date
from pathlib import Path

from usfddk.sec_insider import (
    MIN_CLUSTER_NOTIONAL_USD,
    MIN_CLUSTER_OWNERS,
    SIGNAL_WINDOW_SESSIONS,
    UNIVERSE_AUDIT_SCHEMA_VERSION,
    parse_insider_purchases,
    rank_insider_clusters,
    sha256_file,
    summarize_insider_scope,
)

ROOT = Path(__file__).resolve().parents[1]


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False)
        + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def _load_universe(path: Path) -> tuple[set[str], str]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        rows = csv.DictReader(handle)
        symbols = {
            str(row.get("symbol", "")).strip().upper()
            for row in rows
            if str(row.get("symbol", "")).strip()
        }
    if not symbols:
        raise SystemExit(f"universe CSV 沒有有效 symbol：{path}")
    return symbols, f"external_csv:{path.name}"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="稽核 SEC insider cluster 在不同 universe 的候選數差異；不產生交易指令"
    )
    parser.add_argument("--zip", type=Path, required=True, help="SEC 345 quarterly ZIP")
    parser.add_argument("--as-of", type=date.fromisoformat, required=True)
    parser.add_argument("--universe-file", type=Path, required=True)
    parser.add_argument("--source-url", help="官方資料下載 URL，供收據 provenance 使用")
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "artifacts/short_term_sec_insider_universe_audit.json",
    )
    args = parser.parse_args()
    for path, label in ((args.zip, "SEC insider ZIP"), (args.universe_file, "universe CSV")):
        if not path.is_file():
            raise SystemExit(f"{label} 不存在：{path}")

    events = parse_insider_purchases(args.zip)
    universe_symbols, universe_label = _load_universe(args.universe_file)
    scopes = {
        "all_valid_tickers": summarize_insider_scope(
            events,
            rank_insider_clusters(events, as_of=args.as_of),
            universe_label="all_valid_tickers",
        ),
        "current_watchlist": summarize_insider_scope(
            events,
            rank_insider_clusters(
                events, as_of=args.as_of, universe_symbols=universe_symbols
            ),
            universe_label=universe_label,
            universe_symbols=universe_symbols,
        ),
    }
    payload = {
        "schema_version": UNIVERSE_AUDIT_SCHEMA_VERSION,
        "status": "post_hoc_universe_sensitivity_audit",
        "source": {
            "provider": "SEC Insider Transactions Data Sets",
            "filename": args.zip.name,
            "sha256": sha256_file(args.zip),
            "url": args.source_url,
            "as_of": args.as_of.isoformat(),
            "as_filed": True,
            "universe_file": args.universe_file.name,
        },
        "frozen_rule": {
            "window_xnys_sessions": SIGNAL_WINDOW_SESSIONS,
            "minimum_distinct_owners": MIN_CLUSTER_OWNERS,
            "minimum_notional_usd": MIN_CLUSTER_NOTIONAL_USD,
            "availability": "next_XNYS_session_after_filing_date",
        },
        "scopes": scopes,
        "decision": {
            "strategy_status": "research_candidate_only",
            "post_hoc_diagnostic": True,
            "formal_backtest_completed": False,
            "paper_authorized": False,
            "public_strategy_allowed": False,
            "real_money_action_usd": 0,
            "reason": (
                "Universe sensitivity does not establish investable alpha; "
                "the SEC event stream still lacks point-in-time prices, delisting "
                "returns, and the frozen formal backtest package."
            ),
        },
    }
    _write_json(args.output, payload)
    print(
        json.dumps(
            {
                "status": payload["status"],
                "all_valid_tickers_candidates": scopes["all_valid_tickers"]["candidate_count"],
                "current_watchlist_candidates": scopes["current_watchlist"]["candidate_count"],
                "output": str(args.output),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
