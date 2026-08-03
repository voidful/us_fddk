from __future__ import annotations

import argparse
import json
from pathlib import Path

from usfddk.data import load_snapshot
from usfddk.short_term_high_return import build_short_term_high_return_research
from usfddk.universe import load_stock_watchlist

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SNAPSHOT = ROOT / "artifacts/snapshot_20260731_6a7ca6b8.zip"
DEFAULT_RECEIPT = ROOT / "artifacts/short_term_high_return_validation.json"
DEFAULT_SITE_DATA = ROOT / "site/data/short-term-research.json"


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="建立短線高回報現時股池沙盒、QQQ 基準及台股規則直譯稽核"
    )
    parser.add_argument("--snapshot", type=Path, default=DEFAULT_SNAPSHOT)
    parser.add_argument("--receipt", type=Path, default=DEFAULT_RECEIPT)
    parser.add_argument("--site-data", type=Path, default=DEFAULT_SITE_DATA)
    args = parser.parse_args()

    panel, _ = load_snapshot(args.snapshot)
    payload = build_short_term_high_return_research(
        panel,
        load_stock_watchlist(),
        snapshot_path=args.snapshot,
    )
    _write_json(args.receipt, payload)
    _write_json(args.site_data, payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
