from __future__ import annotations

import argparse
import json
from pathlib import Path

from usfddk.short_term_oversold_reversal_diagnostic import (
    VALIDATION_PATH,
    audit_oversold_reversal_diagnostic,
    write_validation_receipt,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Audit a frozen oversold-reversal diagnostic without trade authorization."
    )
    parser.add_argument("--repository-root", type=Path, default=Path.cwd())
    parser.add_argument("--snapshot", type=Path, required=True)
    args = parser.parse_args()
    result = audit_oversold_reversal_diagnostic(
        repository_root=args.repository_root,
        snapshot_path=args.snapshot,
    )
    write_validation_receipt(result, repository_root=args.repository_root)
    primary = result["horizons"]["20"]
    print(
        json.dumps(
            {
                "status": result["status"],
                "complete_events": primary["events"],
                "primary_mean_difference": primary["mean_difference_vs_eligible_pool"],
                "primary_newey_west_t": primary["newey_west_vs_eligible_pool"]["t_stat"],
                "gates_passed": result["gate_summary"]["passed"],
                "gates_required": result["gate_summary"]["required"],
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
