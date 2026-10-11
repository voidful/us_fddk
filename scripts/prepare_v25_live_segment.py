"""Prepare a reviewable, separate v25 forward segment; never activate or deploy."""
from __future__ import annotations

import argparse
import json

from usfddk.v25_recovery import prepare_v25_live_segment


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", required=True, help="不存在的新目錄；舊三帳戶不會改寫")
    parser.add_argument("--snapshot", help="選用快照，仍必須是現在最近已收盤的交易日")
    args = parser.parse_args()
    manifest = prepare_v25_live_segment(args.directory, snapshot=args.snapshot)
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
