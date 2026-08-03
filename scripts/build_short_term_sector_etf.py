from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path

from usfddk.data import load_snapshot
from usfddk.short_term_sector_etf import build_short_term_sector_etf_research

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SNAPSHOT = (
    ROOT
    / "artifacts/snapshot_short_term_sector_vanguard_20040923_20260731_7a13b864.zip"
)
DEFAULT_DATA_RECEIPT = ROOT / "artifacts/short_term_sector_etf_data_receipt.json"
DEFAULT_RESULT = ROOT / "artifacts/short_term_sector_etf_validation.json"
DEFAULT_SITE_DATA = ROOT / "site/data/short-term-sector-etf.json"


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
        description="執行事前凍結的 Vanguard 行業 ETF 20 日訊號外部驗證"
    )
    parser.add_argument("--snapshot", type=Path, default=DEFAULT_SNAPSHOT)
    parser.add_argument("--data-receipt", type=Path, default=DEFAULT_DATA_RECEIPT)
    parser.add_argument("--result", type=Path, default=DEFAULT_RESULT)
    parser.add_argument("--site-data", type=Path, default=DEFAULT_SITE_DATA)
    args = parser.parse_args()

    panel, _ = load_snapshot(args.snapshot)
    data_receipt = json.loads(args.data_receipt.read_text(encoding="utf-8"))
    payload = build_short_term_sector_etf_research(
        panel,
        snapshot_path=args.snapshot,
        data_receipt=data_receipt,
    )
    _write_json(args.result, payload)
    site_payload = copy.deepcopy(payload)
    site_payload["fixed_20_day_signal_external_diagnostic"].pop(
        "event_series",
        None,
    )
    _write_json(args.site_data, site_payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
