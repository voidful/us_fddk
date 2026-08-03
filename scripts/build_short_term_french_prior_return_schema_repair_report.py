from __future__ import annotations

import json
import sys
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from usfddk.french_prior_return_research import (  # noqa: E402
    build_french_prior_return_schema_repair_research,
)

ARTIFACT_OUTPUT = (
    ROOT / "artifacts/short_term_french_prior_return_schema_repair_validation.json"
)
SITE_OUTPUT = ROOT / "site/data/short-term-french-prior-return-schema-repair.json"


def _site_payload(result: dict) -> dict:
    payload = deepcopy(result)
    for period_key in ("primary_external_period", "recent_confirmation_period"):
        payload[period_key]["rolling_60m_vs_market"].pop("series", None)
        payload[period_key]["rolling_60m_vs_decile_equal"].pop("series", None)
    payload["pbo"]["primary"].pop("logits", None)
    payload["pbo"]["recent"].pop("logits", None)
    return payload


def _write_json(path: Path, payload: dict) -> None:
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def main() -> int:
    result = build_french_prior_return_schema_repair_research(ROOT)
    _write_json(ARTIFACT_OUTPUT, result)
    _write_json(SITE_OUTPUT, _site_payload(result))
    print(
        json.dumps(
            {
                "status": result["status"],
                "gate_breakdown": result["gate_breakdown"],
                "passed_gate_count": result["passed_gate_count"],
                "required_gate_count": result["required_gate_count"],
                "primary_candidate_cagr": result["primary_external_period"][
                    "candidate_metrics"
                ]["cagr"],
                "recent_candidate_cagr": result["recent_confirmation_period"][
                    "candidate_metrics"
                ]["cagr"],
                "independent_first_seen_evidence": result[
                    "independent_first_seen_evidence"
                ],
                "paper_eligible": result["paper_eligible"],
                "real_money_action_usd": result["real_money_action_usd"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
