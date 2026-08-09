from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from usfddk.disclosure_known_at import (  # noqa: E402
    DISCLOSURE_BUNDLE_ENV,
    audit_disclosure_known_at_bundle,
)

DEFAULT_OUTPUT = ROOT / "artifacts/short_term_disclosure_private_readiness.json"


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rendered = json.dumps(
        payload,
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
        allow_nan=False,
    ) + "\n"
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(rendered, encoding="utf-8")
    temporary.replace(path)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="稽核 repository-external 的美國公開披露 known-at 數據包"
    )
    parser.add_argument(
        "--bundle",
        type=Path,
        help=f"合法私有數據包的絕對路徑；省略時只讀取 {DISCLOSURE_BUNDLE_ENV}",
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--require-ready",
        action="store_true",
        help="未達 20/20 時以非零狀態結束；預設只寫 fail-closed 收據",
    )
    args = parser.parse_args()

    configured = args.bundle
    if configured is None:
        raw = os.environ.get(DISCLOSURE_BUNDLE_ENV, "").strip()
        configured = Path(raw) if raw else None
    result = audit_disclosure_known_at_bundle(configured, root=ROOT)
    _write_json(args.output, result)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False))
    return 2 if args.require_ready and not result["readiness"]["all_passed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
