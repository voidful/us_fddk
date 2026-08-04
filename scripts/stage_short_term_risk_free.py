from __future__ import annotations

import argparse
import json
from pathlib import Path

from usfddk.risk_free_staging import stage_official_rf_snapshot

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = ROOT / "artifacts/french_ff_factors_daily_39f9ae1d.zip"


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Stage the frozen official 202606 Fama/French daily RF snapshot in "
            "a new repository-external owner-only directory."
        )
    )
    parser.add_argument("output", type=Path)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    args = parser.parse_args()
    result = stage_official_rf_snapshot(args.source, args.output, root=ROOT)
    print(
        json.dumps(
            {
                "status": result["status"],
                "data_cut": result["data_cut"],
                "available_sessions": result["study"]["available_sessions"],
                "required_sessions": result["study"]["required_sessions"],
                "missing_sessions": result["study"]["missing_session_count"],
                "owner_only": result["owner_only"],
                "formal_manifest_generated": result["formal_manifest_generated"],
                "formal_backtest_authorized": result[
                    "formal_backtest_authorized"
                ],
                "paper_authorized": result["paper"]["authorized"],
                "real_money_action_usd": result["real_money_action_usd"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
