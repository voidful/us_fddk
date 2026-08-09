from __future__ import annotations

import json
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from scripts.build_short_term_provider_evidence_refresh_report import render_report
from usfddk.provider_evidence_refresh import (
    MAX_BODY_BYTES,
    SOURCES,
    load_previous_observations,
    make_refresh_result,
    validate_result,
)

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "artifacts/short_term_provider_evidence_refresh.json"
SITE_DATA = ROOT / "site/data/short-term-provider-evidence-refresh.json"
REPORT = ROOT / "docs/SHORT_TERM_PROVIDER_EVIDENCE_REFRESH_REPORT.md"


def _download(source_id: str, url: str) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "us-fddk-research-evidence-refresh/1.0",
            "Accept": "text/html,application/xhtml+xml,application/pdf",
        },
    )
    with urllib.request.urlopen(request, timeout=45) as response:  # noqa: S310
        body = response.read(MAX_BODY_BYTES + 1)
        return {
            "final_url": response.geturl(),
            "status": response.status,
            "content_type": response.headers.get("Content-Type", ""),
            "body": body,
            "source_id": source_id,
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
    # Render from the exact canonical JSON representation.  ``sort_keys=True``
    # can reorder nested marker maps, and rendering the pre-serialization
    # object would make the Markdown receipt differ despite identical data.
    REPORT.write_text(
        render_report(json.loads(serialized)),
        encoding="utf-8",
    )


def main() -> int:
    observed_at_utc = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    previous = load_previous_observations(ARTIFACT)
    downloaded: dict[str, dict[str, Any]] = {}
    download_errors: dict[str, str] = {}
    for source_id, source in SOURCES.items():
        try:
            downloaded[source_id] = _download(source_id, source["url"])
        except Exception as exc:  # pragma: no cover - network failure is environment-specific
            download_errors[source_id] = f"{type(exc).__name__}: {exc}"

    if download_errors:
        payload = make_refresh_result(
            downloaded, root=ROOT, previous_observations=previous
        )
        payload["error"] = {
            "code": "remote_download_failed",
            "detail": "; ".join(
                f"{source_id}: {detail}" for source_id, detail in download_errors.items()
            ),
        }
        payload["status"] = "manual_review_required"
        payload["manual_review_required"] = True
        payload["all_frozen_identity_checks_pass"] = False
    else:
        payload = make_refresh_result(
            downloaded, root=ROOT, previous_observations=previous
        )
    payload["observed_at_utc"] = observed_at_utc
    _write_payload(payload)
    try:
        validate_result(payload, root=ROOT)
    except Exception as exc:
        print(
            json.dumps(
                {
                    "status": "manual_review_required",
                    "validation_error": str(exc),
                    "provider_package_qualified": False,
                    "formal_backtest_authorized": False,
                    "paper_state": "all_cash",
                    "real_money_action_usd": 0,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 2
    print(
        json.dumps(
            {
                "status": payload["status"],
                "source_identity_count": payload["source_identity_count"],
                "all_frozen_identity_checks_pass": payload[
                    "all_frozen_identity_checks_pass"
                ],
                "provider_package_qualified": False,
                "formal_backtest_authorized": False,
                "paper_state": "all_cash",
                "real_money_action_usd": 0,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if payload["status"] == "observed_official_sources" else 2


if __name__ == "__main__":
    raise SystemExit(main())
