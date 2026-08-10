from __future__ import annotations

import argparse
import json
from pathlib import Path

from usfddk.short_term_volume_breakout_top10_spy60 import (
    VALIDATION_PATH,
    audit_volume_breakout_top10_spy60,
    write_validation_receipt,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Audit the frozen Round63 SPY-60 regime overlay diagnostic."
    )
    parser.add_argument("--repository-root", type=Path, default=Path.cwd())
    parser.add_argument("--snapshot", type=Path, required=True)
    args = parser.parse_args()
    result = audit_volume_breakout_top10_spy60(
        repository_root=args.repository_root,
        snapshot_path=args.snapshot,
    )
    write_validation_receipt(result, repository_root=args.repository_root)
    selected = result["scheduled_baselines"]["selected"]
    print(
        json.dumps(
            {
                "status": result["status"],
                "candidate_events": result["capital_policy"]["candidate_events"],
                "accepted_events": result["capital_policy"]["accepted_events"],
                "selected_cagr": selected["cagr"],
                "selected_max_drawdown": selected["max_drawdown"],
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
