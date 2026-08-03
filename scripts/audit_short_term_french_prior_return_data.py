from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from usfddk.french_prior_return_contract import (  # noqa: E402
    audit_frozen_prior_return_archives,
)

OUTPUT = ROOT / "artifacts/short_term_french_prior_return_data_receipt.json"
SITE_OUTPUT = ROOT / "site/data/short-term-french-prior-return-contract.json"


def main() -> int:
    payload = audit_frozen_prior_return_archives(ROOT)
    rendered = json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    for destination in (OUTPUT, SITE_OUTPUT):
        if destination.exists():
            if destination.read_text(encoding="utf-8") != rendered:
                raise RuntimeError(f"既有 French prior-return 收據不一致：{destination}")
        else:
            temporary = destination.with_name(f".{destination.name}.tmp")
            temporary.write_text(rendered, encoding="utf-8")
            temporary.replace(destination)
    print(rendered, end="")
    return 0 if payload["status"].endswith("contract_passed") else 2


if __name__ == "__main__":
    raise SystemExit(main())
