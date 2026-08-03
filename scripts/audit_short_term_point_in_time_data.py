from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from usfddk.point_in_time_ledger import audit_point_in_time_bundle  # noqa: E402

DEFAULT_OUTPUT = ROOT / "artifacts/short_term_point_in_time_readiness.json"
DEFAULT_SITE_DATA = ROOT / "site/data/short-term-point-in-time-readiness.json"
PROVIDER_BUNDLE_ENV = "USFDDK_PIT_DATA_BUNDLE"


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rendered = json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(rendered, encoding="utf-8")
    temporary.replace(path)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="稽核短線個股 point-in-time 成分、退市及公司行動數據包"
    )
    parser.add_argument(
        "--bundle",
        type=Path,
        help=f"本地授權數據轉換包；未提供時只讀取 {PROVIDER_BUNDLE_ENV}",
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--site-data", type=Path, default=DEFAULT_SITE_DATA)
    parser.add_argument(
        "--require-ready",
        action="store_true",
        help="數據合約未 20/20 時以非零狀態結束；日常就緒度更新預設不報錯",
    )
    args = parser.parse_args()

    configured = args.bundle
    if configured is None:
        environment_path = os.environ.get(PROVIDER_BUNDLE_ENV, "").strip()
        configured = Path(environment_path) if environment_path else None

    payload = audit_point_in_time_bundle(configured, root=ROOT)
    _write_json(args.output, payload)
    _write_json(args.site_data, payload)
    print(json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False))
    if args.require_ready and not payload["gate_summary"]["all_passed"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
