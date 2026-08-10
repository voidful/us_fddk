from __future__ import annotations

import argparse
import json
from pathlib import Path

from usfddk.short_term_form4_event_diagnostic import (
    VALIDATION_PATH,
    audit_form4_event_diagnostic,
    write_validation_receipt,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Audit frozen Form 4 clustered-purchase event returns without trade authorization."
    )
    parser.add_argument("--repository-root", type=Path, default=Path.cwd())
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--staging-dir", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--sec-mapping", type=Path, required=True)
    args = parser.parse_args()
    result = audit_form4_event_diagnostic(
        repository_root=args.repository_root,
        snapshot_path=args.snapshot,
        staging_dir=args.staging_dir,
        manifest_path=args.manifest,
        sec_mapping_path=args.sec_mapping,
    )
    write_validation_receipt(result, repository_root=args.repository_root)
    print(
        json.dumps(
            {
                "status": result["status"],
                "cluster_events": result["event_definition"]["cluster_event_count"],
                "primary_complete_events": result["complete_event_counts"]["10"],
                "primary_gate_passed": result["gate_summary"]["passed"],
                "primary_gate_required": result["gate_summary"]["required"],
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
