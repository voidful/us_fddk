from __future__ import annotations

import argparse
import json
from pathlib import Path

from usfddk.local_quarantine_intake import run_local_quarantine_intake

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "在 repository 外以 provider mode 驗證授權回覆、CIZ、QQQ／SPY overlay，"
            "並原子建立 owner-only 衍生 package；不運行策略或 Paper"
        )
    )
    parser.add_argument("--response", type=Path, required=True)
    parser.add_argument("--ciz-bundle", type=Path, required=True)
    parser.add_argument("--execution-overlay", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    try:
        receipt = run_local_quarantine_intake(
            args.response,
            args.ciz_bundle,
            args.execution_overlay,
            args.output,
            root=ROOT,
            source_mode="provider",
        )
    except Exception as exc:  # noqa: BLE001 - return stable upstream semantic codes.
        code = getattr(exc, "code", "local_intake_unexpected_error")
        detail = getattr(exc, "detail", type(exc).__name__)
        print(
            json.dumps(
                {
                    "status": "rejected",
                    "error_code": code,
                    "detail": detail,
                    "formal_stock_backtest_input_ready": False,
                    "formal_stock_backtest_completed": False,
                    "paper_authorized": False,
                    "real_money_action_usd": 0,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 2

    print(json.dumps(receipt, ensure_ascii=False, indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
