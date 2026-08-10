from __future__ import annotations

import argparse
import json
from pathlib import Path

from usfddk.short_term_volume_breakout_top10_spy60_robustness import (
    VALIDATION_PATH,
    audit_volume_breakout_robustness,
    write_validation_receipt,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Audit the frozen Round64 volume-breakout robustness diagnostic."
    )
    parser.add_argument("--repository-root", type=Path, default=Path.cwd())
    parser.add_argument("--snapshot", type=Path, required=True)
    args = parser.parse_args()
    result = audit_volume_breakout_robustness(
        repository_root=args.repository_root,
        snapshot_path=args.snapshot,
    )
    write_validation_receipt(result, repository_root=args.repository_root)
    selected20 = result["full_period"]["20_bps"]["selected"]
    print(
        json.dumps(
            {
                "status": result["status"],
                "candidate_events": result["fixed_schedule"]["candidate_events"],
                "accepted_events": result["fixed_schedule"]["accepted_events"],
                "selected_20bps_cagr": selected20["cagr"],
                "selected_20bps_max_drawdown": selected20["max_drawdown"],
                "robustness_gates_passed": result["robustness_gate_summary"]["passed"],
                "robustness_gates_required": result["robustness_gate_summary"]["required"],
                "paper_authorized": result["state_boundary"]["paper_authorized"],
                "real_money_action_usd": result["state_boundary"]["real_money_action_usd"],
                "today_action": result["state_boundary"]["today_action"],
                "output": str(VALIDATION_PATH),
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
