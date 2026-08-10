from __future__ import annotations

import argparse
import json
from pathlib import Path

from usfddk.form4_full_coverage import (
    VALIDATION_PATH,
    audit_full_coverage,
    write_validation_receipt,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Audit all frozen SEC Form 4 quarters as aggregate coverage only."
    )
    parser.add_argument("--repository-root", type=Path, default=Path.cwd())
    parser.add_argument("--staging-dir", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--sec-mapping", type=Path, required=True)
    args = parser.parse_args()
    result = audit_full_coverage(
        repository_root=args.repository_root,
        staging_dir=args.staging_dir,
        manifest_path=args.manifest,
        sec_mapping_path=args.sec_mapping,
    )
    write_validation_receipt(result, repository_root=args.repository_root)
    print(
        json.dumps(
            {
                "status": result["status"],
                "quarter_count": result["source_manifest"]["quarter_count"],
                "eligible_purchase_accessions": result["aggregate_counts"][
                    "eligible_purchase_accession_count"
                ],
                "current_cik_mapped": result["aggregate_counts"][
                    "current_cik_exact_purchase_accession_count"
                ],
                "as_filed_symbol_mapped": result["aggregate_counts"][
                    "as_filed_symbol_exact_purchase_accession_count"
                ],
                "performance_present": result["state_boundary"]["performance_present"],
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
