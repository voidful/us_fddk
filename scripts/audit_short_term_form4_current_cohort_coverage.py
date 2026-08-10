from __future__ import annotations

import argparse
import json
from pathlib import Path

from usfddk.form4_current_cohort_coverage import (
    FIXED_QUARTERS,
    VALIDATION_PATH,
    audit_current_cohort_coverage,
    write_validation_receipt,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Audit fixed current-watchlist Form 4 coverage without returns."
    )
    parser.add_argument("--repository-root", type=Path, default=Path.cwd())
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument(
        "--sec-mapping",
        type=Path,
        required=True,
        help="Owner-only SEC company_tickers.json kept outside the repository.",
    )
    parser.add_argument("--archive-dir", type=Path, required=True)
    args = parser.parse_args()
    archive_dir = args.archive_dir.resolve()
    archive_paths = {
        quarter: archive_dir / filename
        for quarter, filename in zip(
            FIXED_QUARTERS,
            ("2006q1_form345.zip", "2016q3_form345.zip", "2026q2_form345.zip"),
            strict=True,
        )
    }
    receipt = audit_current_cohort_coverage(
        repository_root=args.repository_root,
        snapshot_path=args.snapshot,
        sec_mapping_path=args.sec_mapping,
        archive_paths=archive_paths,
    )
    write_validation_receipt(receipt, repository_root=args.repository_root)
    print(json.dumps(
        {
            "status": receipt["status"],
            "coverage_gate_passed": receipt["coverage_gate"]["passed"],
            "mapped_primary_clusters": receipt["coverage_gate"]["observed_mapped_primary_clusters"],
            "mapped_issuers": receipt["coverage_gate"]["observed_mapped_issuers"],
            "performance_present": receipt["state_boundary"]["performance_present"],
            "today_action": receipt["state_boundary"]["today_action"],
            "output": str(VALIDATION_PATH),
        }, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
