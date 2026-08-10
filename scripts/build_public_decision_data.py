from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from usfddk.site_export import (  # noqa: E402
    _preserve_idempotent_generation_time,
    build_public_decision_audit_log,
    build_public_decision_payload,
)


def _load(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"公開資料來源必須是 JSON object：{path}")
    return value


def _write(path: Path, payload: dict, *, preserve_from: list[Path]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = _preserve_idempotent_generation_time(payload, [path, *preserve_from])
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="只輸出已驗證策略與今日行動，將研究失敗結果留在日誌"
    )
    parser.add_argument(
        "--source",
        type=Path,
        default=ROOT / "site/data/trading-data.json",
        help="完整研究／Paper 輸出，只作為 allow-list 產生器的輸入",
    )
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
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "site/data/public-decision.json",
    )
    parser.add_argument(
        "--log-output",
        type=Path,
        default=ROOT / "artifacts/public_decision_build_log.json",
        help="內部決策建置日誌；不會被網站載入",
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
    audit_log = build_public_decision_audit_log(
        source,
        formal_readiness=formal,
        short_term_overlay=overlay,
        public_payload=public,
    )
    _write(args.output, public, preserve_from=[args.source])
    _write(args.log_output, audit_log, preserve_from=[args.source, args.output])
    print(
        f"公開決策資料：{args.output}｜"
        f"{len(public['strategies'])} 個已驗證策略｜{public['today_action']}｜"
        f"內部日誌：{args.log_output}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
