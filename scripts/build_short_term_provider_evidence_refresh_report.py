from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "artifacts/short_term_provider_evidence_refresh.json"
REPORT = ROOT / "docs/SHORT_TERM_PROVIDER_EVIDENCE_REFRESH_REPORT.md"


def _check_markers(observation: dict[str, Any]) -> str:
    checks = observation.get("marker_checks", {})
    if not checks:
        return "—"
    return ", ".join(f"`{marker}` {'✓' if passed else '✗'}" for marker, passed in checks.items())


def render_report(payload: dict[str, Any]) -> str:
    rows: list[str] = []
    for source_id, observation in payload.get("observations", {}).items():
        rows.append(
            "| {source} | {status}／{content_type} | {bytes:,} | `{sha}` | {markers} |".format(
                source=source_id,
                status=observation.get("http_status", "—"),
                content_type=observation.get("content_type", "—"),
                bytes=int(observation.get("body_size_bytes") or 0),
                sha=observation.get("body_sha256") or "—",
                markers=_check_markers(observation),
            )
        )
    error = payload.get("error") or {}
    error_text = (
        f"`{error.get('code')}`：{error.get('detail')}"
        if error
        else "沒有遠端下載錯誤。"
    )
    observation_errors = payload.get("observation_errors", {})
    error_lines = []
    for source_id, detail in observation_errors.items():
        line = f"- `{source_id}`：`{detail.get('code')}` — {detail.get('detail')}"
        if detail.get("code") == "source_hash_drift":
            line += (
                f"（previous SHA `{detail.get('previous_body_sha256')}` → "
                f"current `{detail.get('current_body_sha256')}`；"
                f"previous URL `{detail.get('previous_final_url')}` → "
                f"current `{detail.get('current_final_url')}`）"
            )
        error_lines.append(line)
    error_text_lines = "\n".join(error_lines) or "- 沒有 observation-level error。"
    formal = payload.get("formal_readiness", {})
    pit = payload.get("point_in_time_readiness", {})
    return f"""# 短線個股第三十三輪：官方 provider 證據刷新報告

研究輪次：{payload.get('research_round')}
協議 SHA-256：`{payload.get('protocol_sha256')}`
結果：**{payload.get('status')}**
觀察時間（UTC）：`{payload.get('observed_at_utc', '未記錄')}`

## 結論

本次唯讀探針觀察到 **{payload.get('source_identity_count')}/{payload.get('expected_source_identity_count')}**
個凍結來源身份，`all_frozen_identity_checks_pass={payload.get('all_frozen_identity_checks_pass')}`。
這不是資料包，也不是授權證明；它只顯示官方文件身份或內容有漂移時，入口會停在人工覆核。

- 遠端下載層：{error_text}
- observation-level error：
{error_text_lines}
- formal readiness：{formal.get('passed', 1)}/{formal.get('total', 18)}；
  point-in-time readiness：{pit.get('passed', 1)}/{pit.get('total', 20)}。
- provider package qualified：`{payload.get('provider_package_qualified')}`；
  formal backtest authorized：`{payload.get('formal_backtest_authorized')}`。
- Paper：`{payload.get('paper_state')}`；strategy runs：`{payload.get('strategy_run_count')}`；
  實金動作：**US${payload.get('real_money_action_usd'):,.0f}**。

## 遠端 observation 收據

原始 HTML／PDF bytes 沒有保存到 repository；只保留 URL、HTTP、content type、大小、
SHA-256 及 marker 布林值，並繼續拒絕將文件身份升格為供應商 package。

| source | HTTP／content type | bytes | SHA-256 | marker checks |
|---|---:|---:|---|---|
{chr(10).join(rows) or '| （沒有有效 observation） | — | — | — | — |'}

## 能力與決策邊界

既有 capability matrix 不因公開文件或 URL 變動而升級：逐期成分公布時間、security
metadata KnownAt、完整 DelRet／缺失原因／successor、row-level provenance 仍須授權樣本
和完整 manifest 才能驗證。不得以 effective date 冒充 announced-at，不得以現時／restated
history 冒充 as-known snapshot，不得把缺失退市回報補成零。

本輪固定維持：

- `new_source_qualified=false`
- `provider_package_qualified=false`
- `formal_backtest_authorized=false`
- `paper_state=all_cash`
- `real_money_action_usd=0`

下一個有效動作：取得使用者已授權的完整 provider package，按既有 Round21 的 18/18、
point-in-time 20/20、execution 16/16、完整 RF 及 row-level provenance 驗收；在此之前
不得重選參數、回填交易、開 Paper 或部署新網站版本。

一手入口：

- [CRSP／Morningstar levels and constituents](https://www.crsp.org/indexes/levels-constituents/)
- [CRSP Historical Indexes Guide](https://www.crsp.org/crsp_pdf/crsp-historical-indexes-guide/)
- [LSEG Building historical index constituents](https://developers.lseg.com/en/article-catalog/article/building-historical-index-constituents)

本報告只作研究及專業資訊參考，不構成供應商背書、投資建議、回報預測或盈利保證。
"""


def main() -> int:
    payload = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(render_report(payload), encoding="utf-8")
    print(
        json.dumps(
            {
                "status": payload.get("status"),
                "source_identity_count": payload.get("source_identity_count"),
                "expected_source_identity_count": payload.get(
                    "expected_source_identity_count"
                ),
                "provider_package_qualified": payload.get(
                    "provider_package_qualified"
                ),
                "formal_backtest_authorized": payload.get(
                    "formal_backtest_authorized"
                ),
                "paper_state": payload.get("paper_state"),
                "real_money_action_usd": payload.get("real_money_action_usd"),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
