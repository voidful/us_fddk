from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from usfddk.formal_backtest_runner import run_formal_backtest_once  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "只在正式 readiness 全過後執行一次凍結短線回測；"
            "失敗只保存到 repository 外 owner-only log，不建立 Paper 或公開建議"
        )
    )
    parser.add_argument("--package", type=Path, required=True)
    parser.add_argument("--risk-free-bundle", type=Path, required=True)
    parser.add_argument(
        "--benchmark-action-bundle",
        type=Path,
        required=True,
        help="repository 外、owner-only 的 QQQ／SPY 公司行動 provider bridge",
    )
    parser.add_argument("--release-firewall", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    try:
        result = run_formal_backtest_once(
            args.package,
            args.risk_free_bundle,
            args.output,
            root=ROOT,
            source_mode="provider",
            release_firewall=args.release_firewall,
            benchmark_action_bundle=args.benchmark_action_bundle,
        )
    except Exception as exc:  # noqa: BLE001 - stable semantic code is the CLI contract.
        code = getattr(exc, "code", "formal_runner_unexpected_error")
        detail = getattr(exc, "detail", type(exc).__name__)
        print(
            json.dumps(
                {
                    "status": "formal_backtest_failed_no_promotion",
                    "error_code": code,
                    "detail": detail,
                    "formal_stock_backtest_completed": False,
                    "paper_authorized": False,
                    "real_money_action_usd": 0,
                    "public_promotion_allowed": False,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 2

    print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
