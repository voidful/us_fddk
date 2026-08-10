from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from usfddk.formal_report import (  # noqa: E402
    FormalReportError,
    load_formal_receipt,
    render_formal_backtest_report,
)


def _write_private(path: Path, content: str) -> None:
    path = path.resolve()
    if path.exists() and path.is_symlink():
        raise FormalReportError("formal_report_output_invalid", "輸出檔不可是 symlink")
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    path.write_text(content, encoding="utf-8")
    path.chmod(0o600)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "把一份 immutable formal run summary 或 failure receipt 轉成內部研究報表；"
            "不寫入公開決策頁"
        )
    )
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    try:
        receipt, source = load_formal_receipt(args.run_dir)
        output = args.output.resolve()
        site_root = (ROOT / "site").resolve()
        try:
            output.relative_to(site_root)
        except ValueError:
            pass
        else:
            raise FormalReportError(
                "formal_report_output_invalid", "內部研究報表不可寫入 site 目錄"
            )
        report = render_formal_backtest_report(receipt)
        _write_private(output, report)
    except FormalReportError as exc:
        print(
            json.dumps(
                {
                    "status": "formal_report_failed",
                    "error_code": exc.code,
                    "detail": exc.detail,
                    "public_promotion_allowed": False,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 2

    print(
        json.dumps(
            {
                "status": "formal_report_rendered",
                "source_receipt": str(source),
                "report_path": str(output),
                "public_promotion_allowed": False,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
