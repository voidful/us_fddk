from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from usfddk.public_decision import (  # noqa: E402
    build_public_decision_audit_log,
    build_public_decision_payload,
)


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON source must be an object: {path}")
    return value


def _write_json(path: Path, payload: dict[str, Any], *, preserve_generated_at: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if preserve_generated_at and path.exists():
        try:
            previous = _load(path)
            if {
                key: value for key, value in payload.items() if key != "generated_at_utc"
            } == {
                key: value for key, value in previous.items() if key != "generated_at_utc"
            } and isinstance(previous.get("generated_at_utc"), str):
                payload = {**payload, "generated_at_utc": previous["generated_at_utc"]}
        except (OSError, json.JSONDecodeError, ValueError):
            pass
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build the success-only public decision contract; keep diagnostics in an internal log"
    )
    parser.add_argument("--source", type=Path, default=ROOT / "site/data/trading-data.json")
    parser.add_argument(
        "--formal-readiness",
        type=Path,
        default=ROOT / "site/data/short-term-formal-backtest-readiness.json",
    )
    parser.add_argument(
        "--short-term-overlay",
        type=Path,
        default=ROOT / "site/data/short-term-qqq-replacement-overlay.json",
    )
    parser.add_argument("--output", type=Path, default=ROOT / "site/data/public-decision.json")
    parser.add_argument(
        "--audit-log",
        type=Path,
        default=ROOT / "artifacts/public_decision_build_log.json",
    )
    args = parser.parse_args()

    source = _load(args.source)
    formal = _load(args.formal_readiness) if args.formal_readiness.exists() else None
    overlay = _load(args.short_term_overlay) if args.short_term_overlay.exists() else None
    public = build_public_decision_payload(
        source,
        formal_readiness=formal,
        short_term_overlay=overlay,
    )
    audit = build_public_decision_audit_log(
        source,
        formal_readiness=formal,
        short_term_overlay=overlay,
        public_payload=public,
    )
    _write_json(args.output, public, preserve_generated_at=True)
    _write_json(args.audit_log, audit)
    print(
        json.dumps(
            {
                "status": "public_decision_contract_built",
                "output": str(args.output),
                "audit_log": str(args.audit_log),
                "surface": public["surface"],
                "today_action": public["today_action"],
                "public_strategy_count": len(public["strategies"]),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
