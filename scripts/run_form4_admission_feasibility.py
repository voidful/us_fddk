from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from usfddk.form4_admission_collection import (  # noqa: E402
    collect_authorized_form4_sample,
    replay_authorized_form4_sample,
    write_public_validation,
)

DEFAULT_OUTPUT = ROOT / "artifacts/short_term_form4_admission_feasibility_validation.json"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="收集或離線重播固定的 SEC Form 4 admission feasibility 細樣本"
    )
    parser.add_argument("mode", choices=("collect", "replay"))
    parser.add_argument("--quarantine", type=Path, required=True)
    parser.add_argument("--authorization", type=Path, required=True)
    parser.add_argument("--private-manifest", type=Path)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    user_agent = os.environ.get("USFDDK_SEC_USER_AGENT")

    if args.mode == "collect":
        if args.private_manifest is not None:
            parser.error("collect 模式不可指定 --private-manifest")
        manifest = collect_authorized_form4_sample(
            repository_root=ROOT,
            quarantine=args.quarantine,
            authorization_path=args.authorization,
            user_agent=user_agent,
        )
        print(
            json.dumps(
                {
                    "status": "private_collection_complete_cold_replay_required",
                    "private_manifest_sha256": hashlib.sha256(manifest.read_bytes()).hexdigest(),
                    "candidate_selection_count": 0,
                    "strategy_run_count": 0,
                    "today_action": "今天不下單",
                },
                ensure_ascii=False,
                sort_keys=True,
            )
        )
        return 0

    if args.private_manifest is None:
        parser.error("replay 模式必須指定 --private-manifest")
    result = replay_authorized_form4_sample(
        repository_root=ROOT,
        quarantine=args.quarantine,
        authorization_path=args.authorization,
        private_manifest_path=args.private_manifest,
        user_agent=user_agent,
    )
    write_public_validation(args.output, result)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False))
    return 0 if result["status"] != "stopped_no_admission_claim" else 2


if __name__ == "__main__":
    raise SystemExit(main())
