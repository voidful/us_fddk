from __future__ import annotations

import argparse
import json
from pathlib import Path

from usfddk.short_term_current_cohort_breakout import (
    VALIDATION_PATH,
    audit_current_cohort_breakout,
    write_validation_receipt,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run the frozen current-cohort breakout event diagnostic."
    )
    parser.add_argument("--repository-root", type=Path, default=Path.cwd())
    parser.add_argument("--snapshot", type=Path, required=True)
    args = parser.parse_args()
    result = audit_current_cohort_breakout(
        repository_root=args.repository_root,
        snapshot_path=args.snapshot,
    )
    write_validation_receipt(result, repository_root=args.repository_root)
    primary = result["horizons"][str(result["primary_horizon"])]
    comparison = primary["comparison_vs_eligible_equal"]
    print(
        json.dumps(
            {
                "status": result["status"],
                "primary_events": primary["events"],
                "primary_mean_difference": comparison["mean_difference"],
                "primary_newey_west_t": comparison["newey_west"]["t_stat"],
                "passed_primary_gate_count": result["passed_primary_gate_count"],
                "required_primary_gate_count": result["required_primary_gate_count"],
                "paper_authorized": result["data_boundary"]["paper_authorized"],
                "real_money_action_usd": result["real_money_action_usd"],
                "today_action": result["today_action"],
                "output": str(VALIDATION_PATH),
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
