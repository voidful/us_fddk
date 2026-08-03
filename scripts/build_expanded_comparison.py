from __future__ import annotations

import argparse
import json
from pathlib import Path

from usfddk.comparison_lab import build_v25_expanded_comparison
from usfddk.data import load_snapshot

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_V25_SNAPSHOT = ROOT / "artifacts/snapshot_v25_vanguard_20060701_20260731_6cf44e63.zip"
DEFAULT_STOCK_SNAPSHOT = ROOT / "artifacts/snapshot_20260731_6a7ca6b8.zip"
DEFAULT_RECEIPT = ROOT / "artifacts/v25_expanded_comparison.json"
DEFAULT_SITE_DATA = (
    ROOT / "artifacts/site_data.json",
    ROOT / "site/data/trading-data.json",
)


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
        description="建立 v25 通過後的擴充 baseline、個股及市場狀況比較"
    )
    parser.add_argument("--v25-snapshot", type=Path, default=DEFAULT_V25_SNAPSHOT)
    parser.add_argument("--stock-snapshot", type=Path, default=DEFAULT_STOCK_SNAPSHOT)
    parser.add_argument("--receipt", type=Path, default=DEFAULT_RECEIPT)
    parser.add_argument("--site-data", type=Path, nargs="*", default=list(DEFAULT_SITE_DATA))
    args = parser.parse_args()

    v25_panel, _ = load_snapshot(args.v25_snapshot)
    stock_panel, _ = load_snapshot(args.stock_snapshot)
    comparison = build_v25_expanded_comparison(
        v25_panel,
        stock_panel,
        v25_snapshot_path=args.v25_snapshot,
        stock_snapshot_path=args.stock_snapshot,
    )
    _write_json(args.receipt, comparison)
    for destination in args.site_data:
        payload = json.loads(destination.read_text(encoding="utf-8"))
        v25 = payload["research_pipeline"]["growth_gold_diversification"]
        v25["expanded_comparison_not_used_for_frozen_gate"] = comparison
        _write_json(destination, payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
