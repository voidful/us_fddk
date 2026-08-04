from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from usfddk.provider_convergence_validation import (
    run_provider_convergence_validation,
)

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "artifacts/short_term_provider_convergence_validation.json"
SITE_DATA = ROOT / "site/data/short-term-provider-convergence.json"
REPORT = ROOT / "docs/SHORT_TERM_PROVIDER_CONVERGENCE_REPORT.md"


def _site_summary(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "research_round": 20,
        "evidence_as_of": result["evidence_as_of"],
        "status": result["status"],
        "guides": result["guides"],
        "capability_matrix": result["capability_matrix"],
        "treasury": result["treasury"],
        "control_summary": result["control_summary"],
        "controls": result["controls"],
        "attack_summary": result["attack_summary"],
        "attacks": result["attacks"],
        "actual_formal_readiness": result["actual_formal_readiness"],
        "authorized_provider_package_received": result[
            "authorized_provider_package_received"
        ],
        "complete_risk_free_package_received": result[
            "complete_risk_free_package_received"
        ],
        "formal_stock_backtest_completed": result[
            "formal_stock_backtest_completed"
        ],
        "strategy_run_count": result["strategy_run_count"],
        "paper": result["paper"],
        "real_money_action_usd": result["real_money_action_usd"],
        "next_action": result["next_action"],
        "disclaimer": result["disclaimer"],
    }


def _report(result: dict[str, Any]) -> str:
    matrix = result["capability_matrix"]
    direct = "\n".join(
        f"| `{name}` | `{status}` | 官方指南直接支持資料字典能力；不等於已訂閱或已交付 |"
        for name, status in matrix["direct"].items()
    )
    overlay = "\n".join(
        f"| `{name}` | `{status}` | 不以生效日、下載日或缺值推算 |"
        for name, status in matrix["overlay_required"].items()
    )
    controls = "\n".join(
        f"| {row['id']} | {row['label']} | 通過 | {row['detail']} |"
        for row in result["controls"]
    )
    attacks = "\n".join(
        f"| {row['id']} | {row['label']} | `{row['observed_error_code']}` | "
        f"{'拒收' if row['rejected'] else '失敗'} |"
        for row in result["attacks"]
    )
    stock = result["guides"]["stock_ciz"]
    treasury = result["guides"]["treasury"]
    return f"""# 短線個股第二十輪：CRSP／WRDS 供應商收斂報告

證據截至：{result['evidence_as_of']}

## 結論先行

最新官方 CRSP Stock CIZ 指南可把十份固定交接輸入收窄成兩組：
**{matrix['direct_documented_count']}/{matrix['requested_input_count']} 份有直接資料字典能力**，
另 **{matrix['overlay_required_count']}/{matrix['requested_input_count']} 份仍須供應商或獨立
evidence overlay**。這不是「數據已齊」：公開指南沒有逐列 `KnownAt`、成分公布時間、完整
XNYS 開收市日曆，也不能替缺失退市回報補 0。

CRSP Treasury 是同一供應商授權下值得核對的映射候選，但最新版指南的日度 RF 是
4／13／26 週；精確 1 個月系列只在月度表，與第十八輪凍結的「1 個月國庫券日度簡單
回報」並不相同。因此狀態固定為
`{result['treasury']['same_provider_mapping_status']}`，不生成正式 RF manifest。

十二道指南、欄位、年期、單位及決策控制
**{result['control_summary']['passed']}/{result['control_summary']['total']} 通過**；十二項單一
錯誤攻擊 **{result['attack_summary']['rejected']}/{result['attack_summary']['total']} 全部拒收**。
它們只證明 validator 會 fail closed，不是策略回測。真實正式就緒仍為 **1/18**，provider
package 0、完整 RF 0、正式策略運行 **0 次**；短線 Paper 全現金、0 成交、0 持倉，實金
動作 **US$0**。

## 最新一手指南身份

| 指南 | Effective date | 頁數 | PDF SHA-256 |
|---|---:|---:|---|
| CRSP US Stock CIZ | {stock['effective_date']} | {stock['page_count']} | `{stock['pdf_sha256']}` |
| CRSP US Treasury | {treasury['effective_date']} | {treasury['page_count']} | `{treasury['pdf_sha256']}` |

網站每日只探測標題、生效日、PDF URL、頁數及 SHA-256。任何漂移只標記
`unqualified_new_guide`，不會自動改能力矩陣、readiness、回測或 Paper 狀態。

## Stock CIZ：直接支持的五份能力

| 固定輸入 | 狀態 | 專業判讀 |
|---|---|---|
{direct}

其中 `StkSecurityInfoHist` 有 PERMNO／PERMCO 及歷史有效區間；`StkIndMembership` 有
PERMNO／INDNO／MbrStartDt／MbrEndDt／MbrFlg；日線表保留 raw 價量、回報及交易狀態；
distributions 有 ex／declare／record／pay date、現金或比率及 successor；delists 有 DelRet、
missing type、successor PERMNO／PERMCO 及 storage date。這些都是 schema 能力，不是完整
2006–2026 真實列的驗收結果。

## 仍須證據層的五份輸入

| 固定輸入 | 狀態 | 不可替代規則 |
|---|---|---|
{overlay}

最重要的拒絕替代是：`MbrStartDt` 只代表成分生效區間，不是 `AnnouncedAt`；
`SecInfoStartDt` 只代表證券資料有效區間，不是 `KnownAt`。檔案建立、下載或資料 cut 時間
亦不能回填逐列可知時間。`DelRetMissType` 標明缺失原因，但缺失退出經濟代價仍不可填 0。

## Treasury：同供應商不等於同經濟定義

- 個別 Treasury issue 有 `TDRETNUA` 日度未調整回報；
- `TFZ_DLY_RF2` 有 4／13／26 週日度 RF；4 週 `TREASNOX=2000061`；
- 精確 1 個月 `TREASNOX=2000001` 在 `TFZ_MTH_RF`，是月度連續複利收益率；
- 不接受 4 週冒充 1 個月、年率直接除 252、事後逐日挑最接近 30 日票據，或以 DGS1MO、
  SHY、SOFR、零回報拼接。

只有供應商提供相同經濟定義的日度簡單回報，或在看任何輸出前另立可重播映射協議並
完成獨立驗證，才可關閉正式 RF 缺口。本輪沒有建立或試跑該映射。

## 十二道固定控制

| # | 閘門 | 結果 | 核對內容 |
|---|---|---|---|
{controls}

## 十二項失敗攻擊

| # | 單一錯誤 | 實際 error code | 結果 |
|---|---|---|---|
{attacks}

## 下一個有效研究動作

{result['next_action']} 在此之前不產生最新選股名單，不把歷史合成控制當真實數據，不為
追求 headline CAGR 改持股數、窗口、退出規則或成本。真實 18/18 後只准運行一次凍結
20 年回測；再通過 QQQ／SPY／同池等權／首輪 Top-10 漂移、10／25／50 bps、DSR／PBO
與危機分段門檻，才可由下一個新增交易日的全現金開始不可回填 Paper。

## 一手來源

- [CRSP US Stock Databases](https://indexes.morningstar.com/research-data-products/crsp-us-stock-databases)
- [CRSP Stock CIZ 最新指南]({stock['landing_url']})
- [CRSP US Treasury Database](https://indexes.morningstar.com/research-data-products/crsp-us-treasury-database)
- [CRSP Treasury 最新指南]({treasury['landing_url']})
- [第二十輪事前協議](SHORT_TERM_PROVIDER_CONVERGENCE_PROTOCOL.md)
- [第十八輪正式事前登記](SHORT_TERM_FORMAL_BACKTEST_PREREGISTRATION.md)

本報告只作研究及專業資訊參考，不構成數據供應商背書、投資建議、回報預測或盈利保證。
"""


def main() -> int:
    result = run_provider_convergence_validation(ROOT)
    ARTIFACT.parent.mkdir(parents=True, exist_ok=True)
    SITE_DATA.parent.mkdir(parents=True, exist_ok=True)
    ARTIFACT.write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    SITE_DATA.write_text(
        json.dumps(_site_summary(result), ensure_ascii=False, indent=2, sort_keys=True)
        + "\n",
        encoding="utf-8",
    )
    REPORT.write_text(_report(result), encoding="utf-8")
    print(
        json.dumps(
            {
                "status": result["status"],
                "capability_matrix": {
                    "direct": result["capability_matrix"][
                        "direct_documented_count"
                    ],
                    "overlay": result["capability_matrix"][
                        "overlay_required_count"
                    ],
                },
                "control_summary": result["control_summary"],
                "attack_summary": result["attack_summary"],
                "formal_stock_backtest_completed": False,
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
