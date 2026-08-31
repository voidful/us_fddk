from __future__ import annotations

import argparse
import json
from pathlib import Path

from usfddk.form4_historical_feasibility import (
    FIXED_QUARTERS,
    Form4HistoricalFeasibilityError,
    audit_historical_feasibility,
    write_validation_receipt,
)


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Offline-only SEC Form 4 historical event-rate audit. "
            "It never downloads data or emits row-level identifiers."
        )
    )
    parser.add_argument(
        "--archive-dir",
        type=Path,
        required=True,
        help="Owner-controlled directory containing the three frozen ZIP files.",
    )
    parser.add_argument(
        "--repository-root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("artifacts/short_term_form4_historical_feasibility_validation.json"),
    )
    return parser.parse_args()


def main() -> int:
    args = _arguments()
    root = args.repository_root.resolve()
    archive_dir = args.archive_dir.resolve()
    paths = {
        quarter: archive_dir / f"{quarter.lower()}_form345.zip"
        for quarter in FIXED_QUARTERS
    }
    output = args.output if args.output.is_absolute() else root / args.output
    try:
        receipt = audit_historical_feasibility(paths, repository_root=root)
        write_validation_receipt(
            receipt,
            output_path=output,
            repository_root=root,
        )
    except Form4HistoricalFeasibilityError as exc:
        print(json.dumps({"status": "stopped", "error_code": exc.code}))
        return 2
    gate = receipt["aggregate_event_gate"]
    print(
        json.dumps(
            {
                "status": receipt["status"],
                "fixed_quarters": receipt["fixed_quarters"],
                "primary_clusters": gate["observed_primary_clusters"],
                "minimum_clusters": gate["minimum_primary_clusters"],
                "event_rate_passed": gate["passed"],
                "performance_present": False,
                "paper_authorized": False,
                "today_action": "今天不下單",
                "output": str(output.relative_to(root)),
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
