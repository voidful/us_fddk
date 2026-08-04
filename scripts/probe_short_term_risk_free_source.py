from __future__ import annotations

import argparse
import json
from pathlib import Path

from usfddk.risk_free_staging import probe_official_rf_zip

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = ROOT / "artifacts/french_ff_factors_daily_39f9ae1d.zip"
ARTIFACT = ROOT / "artifacts/short_term_risk_free_source_probe.json"
SITE_DATA = ROOT / "site/data/short-term-risk-free-source-probe.json"


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Probe the current official Fama/French daily factors ZIP without "
            "qualifying or staging a changed source."
        )
    )
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    args = parser.parse_args()
    result = probe_official_rf_zip(args.source, root=ROOT)
    payload = json.dumps(
        result,
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
        allow_nan=False,
    ) + "\n"
    ARTIFACT.parent.mkdir(parents=True, exist_ok=True)
    SITE_DATA.parent.mkdir(parents=True, exist_ok=True)
    ARTIFACT.write_text(payload, encoding="utf-8")
    SITE_DATA.write_text(payload, encoding="utf-8")
    print(
        json.dumps(
            {
                "status": result["status"],
                "data_cut": result["data_cut"],
                "last_session": result["last_session"],
                "matches_frozen_source": result["matches_frozen_source"],
                "available_sessions": result["study"]["available_sessions"],
                "missing_sessions": result["study"]["missing_session_count"],
                "new_source_qualified": False,
                "formal_backtest_authorized": False,
                "paper_authorized": False,
                "real_money_action_usd": 0,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
