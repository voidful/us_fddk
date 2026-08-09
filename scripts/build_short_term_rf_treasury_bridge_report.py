from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "artifacts/short_term_rf_treasury_bridge.json"
REPORT = ROOT / "docs/SHORT_TERM_RF_TREASURY_BRIDGE_REPORT.md"


def _fmt(value: Any, digits: int = 8) -> str:
    if value is None:
        return "—"
    if isinstance(value, float):
        return f"{value:.{digits}f}"
    return str(value)


def render_report(payload: dict[str, Any]) -> str:
    source = payload.get("source", {})
    coverage = payload.get("coverage", {})
    comparison = payload.get("comparison", {})
    error = payload.get("error")
    rows = payload.get("target_rows", [])
    row_lines = "\n".join(
        "| {date} | {yield_value} | {proxy} |".format(
            date=row.get("date", "—"),
            yield_value=_fmt(row.get("annual_yield_percent"), 2),
            proxy=_fmt(row.get("proxy_daily_simple"), 10),
        )
        for row in rows
    )
    error_line = f"`{error}`" if error else "沒有 probe error。"
    return f"""# 短線個股第三十七輪：Treasury RF bridge 診斷報告

結果：**{payload.get('status')}**
觀測時間（UTC）：`{payload.get('observed_at_utc', '未記錄')}`

## 結論

官方 Treasury Daily Treasury Bill Rates 的 4-week coupon-equivalent 可觀察到
**{coverage.get('observed_target_sessions', 0)}/{coverage.get('target_sessions', 22)}** 個
2026-07 XNYS 缺日；這只證明官方來源有 rows，**不代表它等同 frozen French／ICE BofA
1-month RF**。本輪因此只作 proxy 差異診斷，不把 Treasury rows 寫入正式 RF manifest。

- source：`{source.get('url', '—')}`
- field：`{source.get('field', '—')}`；HTTP：`{source.get('http_status', '—')}`；bytes：`{source.get('body_size_bytes', '—')}`
- source SHA-256：`{source.get('body_sha256', '—')}`；原始 XML 保存：**否**
- missing target sessions：`{coverage.get('missing_target_sessions', [])}`
- error：{error_line}

## 定義差異診斷

proxy daily simple 只按 `(1 + annual_percent / 100) ** (1 / 365) - 1` 轉換，不能取代
French data file 中「compounds to 1-month TBill return」且自 202406 使用 ICE BofA
US 1-Month Treasury Bill Index 的 RF。與 frozen RF 的重疊期只供量化差異：

| 指標 | 結果 |
|---|---:|
| overlap sessions | {comparison.get('overlap_sessions', '—')} |
| overlap range | {comparison.get('overlap_start', '—')} → {comparison.get('overlap_end', '—')} |
| mean diff | `{_fmt(comparison.get('mean_diff'))}` |
| mean absolute diff | `{_fmt(comparison.get('mean_abs_diff'))}` |
| max absolute diff | `{_fmt(comparison.get('max_abs_diff'))}` |
| correlation | `{_fmt(comparison.get('correlation'))}` |
| formal equivalence | **{comparison.get('formal_equivalence', False)}** |

## 22 日 derived rows

| date | annual 4-week CE % | proxy daily simple |
|---|---:|---:|
{row_lines or '| （沒有合法 rows） | — | — |'}

## 決策邊界

`formal_rf_substitute=false`、formal backtest 未授權、Paper `all_cash`、策略 run 0、
實金 US$0。不得以 Treasury proxy 回填 frozen French RF、改寫正式 readiness、重選參數
或建立交易建議。下一步仍是取得與正式定義一致、具授權及 row-level provenance 的完整 RF
manifest，並另外通過既有 18/18 formal、20/20 point-in-time 及 execution 閘門。

本報告只作研究及專業資訊參考，不構成投資建議、盈利證明或盈利保證。
"""


def main() -> int:
    payload = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(render_report(payload), encoding="utf-8")
    print(
        json.dumps(
            {
                "status": payload.get("status"),
                "observed_target_sessions": payload.get("coverage", {}).get(
                    "observed_target_sessions"
                ),
                "formal_rf_substitute": False,
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
