from __future__ import annotations

import json
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from scripts.build_short_term_rf_treasury_bridge_report import render_report
from usfddk.risk_free_treasury_bridge import (
    MAX_BODY_BYTES,
    TREASURY_URL,
    TreasuryBridgeError,
    make_bridge_result,
    validate_result,
)

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "artifacts/short_term_rf_treasury_bridge.json"
SITE_DATA = ROOT / "site/data/short-term-rf-treasury-bridge.json"
REPORT = ROOT / "docs/SHORT_TERM_RF_TREASURY_BRIDGE_REPORT.md"


def _download() -> dict[str, Any]:
    request = urllib.request.Request(
        TREASURY_URL,
        headers={
            "User-Agent": "us-fddk-rf-treasury-bridge/1.0",
            "Accept": "application/xml,text/xml",
        },
    )
    with urllib.request.urlopen(request, timeout=60) as response:  # noqa: S310
        body = response.read(MAX_BODY_BYTES + 1)
        return {
            "final_url": response.geturl(),
            "status": response.status,
            "content_type": response.headers.get("Content-Type", ""),
            "body": body,
        }


def _write_payload(payload: dict[str, Any]) -> None:
    serialized = json.dumps(
        payload,
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
        allow_nan=False,
    ) + "\n"
    ARTIFACT.parent.mkdir(parents=True, exist_ok=True)
    SITE_DATA.parent.mkdir(parents=True, exist_ok=True)
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    ARTIFACT.write_text(serialized, encoding="utf-8")
    SITE_DATA.write_text(serialized, encoding="utf-8")
    REPORT.write_text(render_report(json.loads(serialized)), encoding="utf-8")


def main() -> int:
    observed_at_utc = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    try:
        payload = make_bridge_result(_download(), root=ROOT)
    except Exception as exc:
        payload = {
            "schema_version": 1,
            "research_round": 37,
            "status": "manual_review_required",
            "protocol_sha256": "08d3163799cb1999666c55ef980f480fa5e50a1f11a46c5147aa7e5c3fd8ca1d",
            "error": {"code": getattr(exc, "code", type(exc).__name__), "detail": str(exc)},
            "formal_rf_substitute": False,
            "formal_backtest_authorized": False,
            "paper_authorized": False,
            "paper_state": "all_cash",
            "real_money_action_usd": 0,
        }
        _write_payload(payload)
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 2
    payload["observed_at_utc"] = observed_at_utc
    _write_payload(payload)
    try:
        validate_result(payload, root=ROOT)
    except TreasuryBridgeError as exc:
        print(json.dumps({"status": "manual_review_required", "error": str(exc)}, ensure_ascii=False, indent=2))
        return 2
    print(
        json.dumps(
            {
                "status": payload["status"],
                "observed_at_utc": observed_at_utc,
                "target_sessions": payload["coverage"]["observed_target_sessions"],
                "formal_rf_substitute": False,
                "formal_backtest_authorized": False,
                "paper_state": "all_cash",
                "real_money_action_usd": 0,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
