from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

from usfddk.sec_insider import parse_insider_purchases, sha256_file
from usfddk.sec_insider_forward import load_long_total_return_prices
from usfddk.sec_insider_multi import (
    EXPECTED_QUARTERS,
    build_multi_quarter_diagnostic,
    deduplicate_events,
)

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "docs/SHORT_TERM_SEC_INSIDER_MULTI_QUARTER_PROTOCOL.md"


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
    if not isinstance(rows, list):
        raise ValueError("manifest 缺少 quarters list")
    expected = [label for label, _ in EXPECTED_QUARTERS]
    if [row.get("label") for row in rows] != expected:
        raise ValueError("manifest 必須依序包含 2024Q1 至 2026Q2")
    for row, (label, expected_end) in zip(rows, EXPECTED_QUARTERS, strict=True):
        if row.get("as_of") != expected_end.isoformat():
            raise ValueError(f"{label} as_of 不符固定季度結束日")
        source = Path(str(row.get("path", "")))
        if not source.is_file():
            raise ValueError(f"{label} SEC ZIP 不存在：{source}")
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(
        description="建立 SEC insider 多季後瞻診斷收據；不產生交易指令"
    )
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--prices", type=Path, required=True)
    parser.add_argument("--price-client", default="external_prepared_csv")
    parser.add_argument("--price-source-url", default="https://finance.yahoo.com/")
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "artifacts/short_term_sec_insider_multi_quarter_diagnostic.json",
    )
    args = parser.parse_args()
    if not args.manifest.is_file() or not args.prices.is_file():
        raise SystemExit("manifest 或 prices 不存在")
    manifest = _load_manifest(args.manifest)
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
    diagnostic = build_multi_quarter_diagnostic(quarter_events, prices)
    all_events = [event for _, _, events in quarter_events for event in events]
    # The diagnostic already reports issuer count; use the actual candidate
    # rows from the fixed quarter builder to measure price coverage below.
    candidate_symbols = set(diagnostic.pop("candidate_symbols"))
    covered_candidate_symbols = candidate_symbols & set(prices["symbol"])
    payload = {
        "schema_version": 1,
        "status": "post_hoc_multi_quarter_forward_diagnostic",
        "protocol": {
            "path": "docs/SHORT_TERM_SEC_INSIDER_MULTI_QUARTER_PROTOCOL.md",
            "sha256": sha256_file(PROTOCOL),
            "quarters": [label for label, _ in EXPECTED_QUARTERS],
            "price_first_date": prices["date"].min().isoformat(),
            "price_last_date": prices["date"].max().isoformat(),
            "price_client": args.price_client,
        },
        "sec_sources": sec_sources,
        "sec_input_counts": {
            "package_count": len(sec_sources),
            "raw_event_count": total_events,
            "deduplicated_event_count": len(deduplicate_events(all_events)),
        },
        "price_source": {
            "filename": args.prices.name,
            "sha256": sha256_file(args.prices),
            "url": args.price_source_url,
            "symbol_count": int(prices["symbol"].nunique()),
            "row_count": int(len(prices)),
            "adjusted_total_return_columns": ["adj_open", "adj_close"],
            "candidate_symbol_count": len(candidate_symbols),
            "covered_candidate_symbol_count": len(covered_candidate_symbols),
            "missing_candidate_symbol_count": len(
                candidate_symbols - covered_candidate_symbols
            ),
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
                "SEC as-filed events and exploratory prices do not repair point-in-time "
                "universe, delisting returns, corporate actions, or formal backtest gates."
            ),
        },
    }
    _write_json(args.output, payload)
    primary = diagnostic["all_period"]["horizons"]["20"]
    print(
        json.dumps(
            {
                "status": payload["status"],
                "candidate_count": diagnostic["candidate_count"],
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
