from __future__ import annotations

import argparse
import csv
import json
from datetime import date
from pathlib import Path

from usfddk.sec_insider import build_insider_receipt

ROOT = Path(__file__).resolve().parents[1]


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def _load_universe(path: Path | None) -> tuple[set[str] | None, str]:
    if path is None:
        return None, "all_valid_tickers"
    with path.open("r", encoding="utf-8", newline="") as handle:
        rows = csv.DictReader(handle)
        symbols = {
            str(row.get("symbol", "")).strip().upper()
            for row in rows
            if str(row.get("symbol", "")).strip()
        }
    if not symbols:
        raise SystemExit(f"universe CSV 沒有有效 symbol：{path}")
    return symbols, f"external_csv:{path}"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="建立 SEC Form 4 insider cluster 研究收據；不產生交易指令"
    )
    parser.add_argument("--zip", type=Path, required=True, help="SEC 345 quarterly ZIP")
    parser.add_argument("--as-of", type=date.fromisoformat, required=True)
    parser.add_argument("--universe-file", type=Path, help="可選 CSV；只作當期候選篩選，不作歷史成分")
    parser.add_argument("--source-url", help="官方資料下載 URL，供收據 provenance 使用")
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "artifacts/short_term_sec_insider_signal.json",
    )
    args = parser.parse_args()
    if not args.zip.is_file():
        raise SystemExit(f"SEC insider ZIP 不存在：{args.zip}")
    universe_symbols, universe_label = _load_universe(args.universe_file)
    receipt = build_insider_receipt(
        args.zip,
        as_of=args.as_of,
        universe_symbols=universe_symbols,
        universe_label=universe_label,
        source_url=args.source_url,
    )
    _write_json(args.output, receipt)
    print(
        json.dumps(
            {
                "status": receipt["decision"]["strategy_status"],
                "event_count": receipt["event_count"],
                "candidate_count": receipt["candidate_count"],
                "output": str(args.output),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
