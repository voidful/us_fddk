from __future__ import annotations

import hashlib
import json
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from usfddk.provider_gap_closure import PRIMARY_SOURCES, PROBE_VERSION

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "artifacts/short_term_provider_gap_source_probe.json"
SITE_DATA = ROOT / "site/data/short-term-provider-gap-source-probe.json"

PROBE_IDENTITIES = {
    "crsp_stock_ciz_guide": {
        "marker": "CRSP US Stock Databases Guide for Flat File Format 2 0",
        "allowed_host_suffix": "morningstar.com",
    },
    "spgmi_index_data": {
        "marker": "Index Data",
        "allowed_host_suffix": "spglobal.com",
    },
    "lseg_historical_constituents": {
        "marker": "Historical Index Constituents",
        "allowed_host_suffix": "lseg.com",
    },
    "factset_benchmarks": {
        "marker": "/api-catalog/factset-benchmarks-api",
        "allowed_host_suffix": "factset.com",
    },
    "bloomberg_data_license": {
        "marker": "Data License",
        "allowed_host_suffix": "bloomberg.com",
    },
}


def _identity_sha256(source_id: str, source: dict[str, Any]) -> str:
    payload = {
        "source_id": source_id,
        "owner": source["owner"],
        "title": source["title"],
        "url": source["url"],
        "marker": PROBE_IDENTITIES[source_id]["marker"],
    }
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode()
    return hashlib.sha256(canonical).hexdigest()


def _download(url: str) -> tuple[str, str]:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 us-fddk-research-source-probe/1.0",
            "Accept": "text/html,application/xhtml+xml",
        },
    )
    with urllib.request.urlopen(request, timeout=45) as response:  # noqa: S310
        body = response.read().decode("utf-8", errors="replace")
        return response.geturl(), body


def inspect_current_sources(downloaded: dict[str, tuple[str, str]]) -> dict[str, Any]:
    observations = {}
    for source_id, expected in PROBE_IDENTITIES.items():
        source = PRIMARY_SOURCES[source_id]
        final_url, body = downloaded[source_id]
        host = urllib.parse.urlparse(final_url).hostname or ""
        marker_present = expected["marker"].casefold() in body.casefold()
        host_allowed = host == expected["allowed_host_suffix"] or host.endswith(
            "." + expected["allowed_host_suffix"]
        )
        observations[source_id] = {
            "owner": source["owner"],
            "title": source["title"],
            "url": source["url"],
            "final_url": final_url,
            "identity_sha256": _identity_sha256(source_id, source),
            "marker_present": marker_present,
            "official_host_allowed": host_allowed,
            "matches_frozen_identity": marker_present and host_allowed,
        }
    matches = all(row["matches_frozen_identity"] for row in observations.values())
    return {
        "schema_version": 1,
        "research_round": 21,
        "probe_version": PROBE_VERSION,
        "status": (
            "matches_frozen_primary_source_identities" if matches else "manual_review_required"
        ),
        "observations": observations,
        "all_match_frozen_identities": matches,
        "source_identity_count": len(observations),
        "new_source_qualified": False,
        "provider_package_qualified": False,
        "formal_backtest_authorized": False,
        "strategy_run_count": 0,
        "paper_authorized": False,
        "paper_state": "all_cash",
        "real_money_action_usd": 0,
        "next_action": (
            "URL、官方 host 或 identity marker 漂移只標記人工覆核；probe 永不自行"
            "改寫能力矩陣、提高 readiness 或啟動 Paper。"
        ),
    }


def main() -> int:
    downloaded = {
        source_id: _download(PRIMARY_SOURCES[source_id]["url"]) for source_id in PROBE_IDENTITIES
    }
    result = inspect_current_sources(downloaded)
    payload = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ARTIFACT.parent.mkdir(parents=True, exist_ok=True)
    SITE_DATA.parent.mkdir(parents=True, exist_ok=True)
    ARTIFACT.write_text(payload, encoding="utf-8")
    SITE_DATA.write_text(payload, encoding="utf-8")
    print(
        json.dumps(
            {
                "status": result["status"],
                "all_match_frozen_identities": result["all_match_frozen_identities"],
                "provider_package_qualified": False,
                "formal_backtest_authorized": False,
                "paper_state": "all_cash",
                "real_money_action_usd": 0,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if result["all_match_frozen_identities"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
