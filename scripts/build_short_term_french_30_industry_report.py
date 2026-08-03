from __future__ import annotations

import json
import sys
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from usfddk.french_industry_momentum import (  # noqa: E402
    build_french_30_industry_research,
)

ARTIFACTS = ROOT / "artifacts"
OUTPUT = ARTIFACTS / "short_term_french_30_industry_validation.json"
SITE_OUTPUT = ROOT / "site/data/short-term-french-30-industry.json"


def _site_payload(result: dict) -> dict:
    payload = deepcopy(result)
    for period_key in ("primary_external_period", "recent_confirmation_period"):
        period = payload[period_key]
        period["rolling_five_year_vs_market"].pop("series", None)
        period["rolling_five_year_vs_industry_monthly_equal"].pop("series", None)
    payload["pbo"]["primary"].pop("logits", None)
    payload["pbo"]["recent"].pop("logits", None)
    return payload


def main() -> int:
    receipt = json.loads(
        (ARTIFACTS / "short_term_french_30_industry_data_receipt.json").read_text(
            encoding="utf-8"
        )
    )
    result = build_french_30_industry_research(
        industry_path=ARTIFACTS / "french_30_industry_daily_7140a2db.zip",
        factors_path=ARTIFACTS / "french_ff_factors_daily_af8aec07.zip",
        momentum_path=ARTIFACTS / "french_momentum_daily_f4237e2e.zip",
        data_receipt=receipt,
    )
    temporary = OUTPUT.with_name(f".{OUTPUT.name}.tmp")
    temporary.write_text(
        json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    temporary.replace(OUTPUT)
    site_temporary = SITE_OUTPUT.with_name(f".{SITE_OUTPUT.name}.tmp")
    site_temporary.write_text(
        json.dumps(_site_payload(result), ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    site_temporary.replace(SITE_OUTPUT)
    summary = {
        "status": result["status"],
        "gate_breakdown": result["gate_breakdown"],
        "primary_candidate_cagr": result["primary_external_period"]["candidate_metrics"][
            "cagr"
        ],
        "recent_candidate_cagr": result["recent_confirmation_period"]["candidate_metrics"][
            "cagr"
        ],
        "paper_eligible": result["paper_eligible"],
        "real_money_action_usd": result["real_money_action_usd"],
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
