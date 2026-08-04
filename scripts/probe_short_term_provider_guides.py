from __future__ import annotations

import argparse
import json
import urllib.request
from pathlib import Path

from usfddk.provider_convergence import (
    STOCK_GUIDE,
    TREASURY_GUIDE,
    inspect_provider_guides,
)

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "artifacts/short_term_provider_guide_probe.json"
SITE_DATA = ROOT / "site/data/short-term-provider-guide-probe.json"


def _download(url: str) -> bytes:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "us-fddk-research-guide-probe/1.0"},
    )
    with urllib.request.urlopen(request, timeout=45) as response:  # noqa: S310
        return response.read()


def _read_or_download(path: Path | None, url: str) -> bytes:
    return path.read_bytes() if path is not None else _download(url)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Probe current official CRSP Stock CIZ and Treasury guide identities "
            "without qualifying a changed version."
        )
    )
    parser.add_argument("--stock-landing", type=Path)
    parser.add_argument("--stock-pdf", type=Path)
    parser.add_argument("--treasury-landing", type=Path)
    parser.add_argument("--treasury-pdf", type=Path)
    args = parser.parse_args()
    result = inspect_provider_guides(
        stock_landing_html=_read_or_download(
            args.stock_landing, STOCK_GUIDE["landing_url"]
        ).decode("utf-8", errors="replace"),
        stock_pdf_bytes=_read_or_download(args.stock_pdf, STOCK_GUIDE["pdf_url"]),
        treasury_landing_html=_read_or_download(
            args.treasury_landing, TREASURY_GUIDE["landing_url"]
        ).decode("utf-8", errors="replace"),
        treasury_pdf_bytes=_read_or_download(
            args.treasury_pdf, TREASURY_GUIDE["pdf_url"]
        ),
    )
    payload = json.dumps(
        result,
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
        allow_nan=False,
    ) + "\n"
    ARTIFACT.parent.mkdir(parents=True, exist_ok=True)
    SITE_DATA.parent.mkdir(parents=True, exist_ok=True)
    ARTIFACT.write_text(payload, encoding="utf-8")
    SITE_DATA.write_text(payload, encoding="utf-8")
    print(
        json.dumps(
            {
                "status": result["status"],
                "all_match_frozen_guides": result["all_match_frozen_guides"],
                "new_guide_qualified": False,
                "formal_backtest_authorized": False,
                "paper_authorized": False,
                "real_money_action_usd": 0,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
