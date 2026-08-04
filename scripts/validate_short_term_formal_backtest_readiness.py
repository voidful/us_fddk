from __future__ import annotations

import argparse
import json
from pathlib import Path

from usfddk.formal_backtest_readiness import audit_formal_backtest_readiness

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "只讀稽核 repository 外的 provider package、同步 US 1M T-bill RF 包及"
            "預留新輸出路徑；不運行策略、不建立 Paper、不操作實金"
        )
    )
    parser.add_argument("--package", type=Path, required=True)
    parser.add_argument("--risk-free-bundle", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    try:
        receipt = audit_formal_backtest_readiness(
            args.package,
            args.risk_free_bundle,
            args.output,
            root=ROOT,
            source_mode="provider",
        )
    except Exception as exc:  # noqa: BLE001 - stable semantic code is the CLI contract.
        code = getattr(exc, "code", "formal_readiness_unexpected_error")
        detail = getattr(exc, "detail", type(exc).__name__)
        print(
            json.dumps(
                {
                    "status": "rejected",
                    "error_code": code,
                    "detail": detail,
                    "formal_stock_backtest_authorized": False,
                    "formal_stock_backtest_completed": False,
                    "strategy_run_count": 0,
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
