from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

from usfddk.sec_insider import (
    MIN_CLUSTER_NOTIONAL_USD,
    MIN_CLUSTER_OWNERS,
    SIGNAL_WINDOW_SESSIONS,
    parse_insider_purchases,
    rank_insider_clusters,
    sha256_file,
)
from usfddk.sec_insider_forward import (
    FORWARD_DIAGNOSTIC_SCHEMA_VERSION,
    FORWARD_HORIZONS,
    FORWARD_PRIMARY_HORIZON,
    FORWARD_ROUND_TRIP_COST_BPS,
    compute_forward_event_diagnostic,
    load_long_total_return_prices,
)

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "docs/SHORT_TERM_SEC_INSIDER_FORWARD_DIAGNOSTIC_PROTOCOL.md"


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False)
        + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="建立 SEC insider 事件後瞻研究收據；不產生交易指令"
    )
    parser.add_argument("--sec-zip", type=Path, required=True)
    parser.add_argument("--prices", type=Path, required=True)
    parser.add_argument("--as-of", type=date.fromisoformat, required=True)
    parser.add_argument("--source-url", help="SEC 官方下載 URL")
    parser.add_argument("--price-source-url", help="價格來源說明 URL")
    parser.add_argument(
        "--price-client",
        default="external_prepared_csv",
        help="產生價格 CSV 的客戶端版本，供 provenance 使用",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "artifacts/short_term_sec_insider_forward_diagnostic.json",
    )
    args = parser.parse_args()
    for path, label in ((args.sec_zip, "SEC ZIP"), (args.prices, "price CSV")):
        if not path.is_file():
            raise SystemExit(f"{label} 不存在：{path}")

    events = parse_insider_purchases(args.sec_zip)
    candidates = rank_insider_clusters(events, as_of=args.as_of)
    prices = load_long_total_return_prices(args.prices)
    diagnostic = compute_forward_event_diagnostic(
        candidates,
        prices,
        as_of=args.as_of,
    )
    payload = {
        "schema_version": FORWARD_DIAGNOSTIC_SCHEMA_VERSION,
        "status": "post_hoc_forward_event_diagnostic",
        "protocol": {
            "path": "docs/SHORT_TERM_SEC_INSIDER_FORWARD_DIAGNOSTIC_PROTOCOL.md",
            "sha256": sha256_file(PROTOCOL),
            "horizons_sessions": list(FORWARD_HORIZONS),
            "primary_horizon_sessions": FORWARD_PRIMARY_HORIZON,
            "round_trip_cost_bps": FORWARD_ROUND_TRIP_COST_BPS,
            "cluster_window_xnys_sessions": SIGNAL_WINDOW_SESSIONS,
            "minimum_distinct_owners": MIN_CLUSTER_OWNERS,
            "minimum_notional_usd": MIN_CLUSTER_NOTIONAL_USD,
        },
        "sec_source": {
            "provider": "SEC Insider Transactions Data Sets",
            "filename": args.sec_zip.name,
            "sha256": sha256_file(args.sec_zip),
            "url": args.source_url,
            "as_of": args.as_of.isoformat(),
            "as_filed": True,
        },
        "price_source": {
            "provider": "Yahoo Finance exploratory snapshot",
            "filename": args.prices.name,
            "sha256": sha256_file(args.prices),
            "url": args.price_source_url,
            "download_client": args.price_client,
            "first_date": prices["date"].min().isoformat(),
            "last_date": prices["date"].max().isoformat(),
            "symbol_count": int(prices["symbol"].nunique()),
            "row_count": int(len(prices)),
            "adjusted_total_return_columns": ["adj_open", "adj_close"],
        },
        "input_counts": {
            "event_count": len(events),
            "candidate_count": len(candidates),
            "candidate_issuer_count": len({row["ticker"] for row in candidates}),
        },
        "diagnostic": diagnostic,
        "decision": {
            "strategy_status": "research_candidate_only",
            "post_hoc_diagnostic": True,
            "formal_backtest_completed": False,
            "paper_authorized": False,
            "public_strategy_allowed": False,
            "real_money_action_usd": 0,
            "reason": (
                "Public exploratory prices do not repair point-in-time universe, "
                "delisting returns, corporate actions, or formal backtest gates."
            ),
        },
    }
    _write_json(args.output, payload)
    primary = diagnostic["horizons"][str(FORWARD_PRIMARY_HORIZON)]
    print(
        json.dumps(
            {
                "status": payload["status"],
                "candidate_count": len(candidates),
                "primary_complete_rows": primary["complete_rows"],
                "primary_mean_excess": primary["mean_excess_vs_baseline"],
                "output": str(args.output),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
