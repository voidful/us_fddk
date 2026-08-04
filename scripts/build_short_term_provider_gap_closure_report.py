from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from usfddk.provider_gap_closure import CAPABILITY_IDS
from usfddk.provider_gap_closure_validation import (
    run_provider_gap_closure_validation,
)

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "artifacts/short_term_provider_gap_closure_validation.json"
SITE_DATA = ROOT / "site/data/short-term-provider-gap-closure.json"
REPORT = ROOT / "docs/SHORT_TERM_PROVIDER_GAP_CLOSURE_REPORT.md"

STATUS_LABELS = {
    "explicit_primary_documentation": "明確",
    "partial_primary_documentation": "部分",
    "contradicted_by_primary_documentation": "不符",
    "unresolved_primary_documentation": "未解",
    "validated_authorized_sample": "樣本通過",
    "qualified_provider_package": "完整合格",
}

CAPABILITY_LABELS = {
    "authorized_research_license": "研究授權",
    "point_in_time_sp500_membership": "逐期 S&P 500 成分",
    "membership_announced_at": "成分公布時間",
    "membership_effective_at": "成分生效時間",
    "permanent_security_company_ids": "永久證券／公司 ID",
    "security_metadata_known_at": "Metadata KnownAt",
    "raw_daily_ohlcv_status": "Raw 日線及狀態",
    "distribution_event_clock_terms": "分派事件時鐘及條款",
    "delist_exit_economics": "退市／退出經濟",
    "post_removal_price_path": "移除後價格路徑",
    "xnys_session_open_close": "XNYS 日曆",
    "synchronized_qqq_spy_execution": "同步 QQQ／SPY",
    "exact_one_month_daily_simple_rf": "精確一個月日度 RF",
    "row_level_provenance_replay": "逐列來源重播",
}


def _site_summary(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": result["schema_version"],
        "research_round": result["research_round"],
        "gap_version": result["gap_version"],
        "evidence_as_of": result["evidence_as_of"],
        "status": result["status"],
        "route_summary": result["route_summary"],
        "routes": [
            {
                "id": row["id"],
                "name": row["name"],
                "capabilities": row["capabilities"],
            }
            for row in result["routes"]
        ],
        "best_documented_route": result["best_documented_route"],
        "strongest_standalone_brand_candidate_id": result[
            "strongest_standalone_brand_candidate_id"
        ],
        "required_capability_ids": result["required_capability_ids"],
        "primary_sources": result["primary_sources"],
        "procurement_questions": result["procurement_questions"],
        "controls": result["controls"],
        "control_summary": result["control_summary"],
        "attacks": result["attacks"],
        "attack_summary": result["attack_summary"],
        "qualified_route_count": 0,
        "actual_formal_readiness": result["actual_formal_readiness"],
        "authorized_provider_package_received": False,
        "complete_risk_free_package_received": False,
        "formal_stock_backtest_completed": False,
        "strategy_run_count": 0,
        "paper": result["paper"],
        "real_money_action_usd": 0,
        "next_action": result["next_action"],
    }


def _route_table(result: dict[str, Any]) -> str:
    lines = [
        "| 路徑 | 明確 | 部分 | 不符 | 未解 | 真實樣本 | 完整合格 | 判斷 |",
        "|---|---:|---:|---:|---:|---:|---:|---|",
    ]
    for row in result["route_summary"]:
        counts = row["status_counts"]
        lines.append(
            "| {name} | {explicit}/14 | {partial}/14 | {contradicted}/14 | "
            "{unresolved}/14 | 0/14 | 0/14 | 採購候選；未合格 |".format(
                name=row["name"],
                explicit=counts["explicit_primary_documentation"],
                partial=counts["partial_primary_documentation"],
                contradicted=counts["contradicted_by_primary_documentation"],
                unresolved=counts["unresolved_primary_documentation"],
            )
        )
    return "\n".join(lines)


def _capability_table(result: dict[str, Any]) -> str:
    route_names = [row["name"].split("／")[0] for row in result["routes"]]
    lines = [
        "| 正式能力 | " + " | ".join(route_names) + " |",
        "|---|" + "---|" * len(route_names),
    ]
    for capability_id in CAPABILITY_IDS:
        cells = []
        for route in result["routes"]:
            status = route["capabilities"][capability_id]["status"]
            cells.append(STATUS_LABELS[status])
        lines.append(f"| {CAPABILITY_LABELS[capability_id]} | " + " | ".join(cells) + " |")
    return "\n".join(lines)


def _report(result: dict[str, Any]) -> str:
    best = result["best_documented_route"]
    route_table = _route_table(result)
    capability_table = _capability_table(result)
    questions = "\n".join(
        f"{index}. **{CAPABILITY_LABELS[row['capability']]}**：{row['question']}"
        for index, row in enumerate(result["procurement_questions"], start=1)
    )
    controls = "\n".join(
        f"- {row['id']}｜{row['label']}：**{'通過' if row['passed'] else '未通過'}**。{row['detail']}"
        for row in result["controls"]
    )
    attacks = "\n".join(
        f"- {row['id']}｜{row['label']}：**{'拒收' if row['rejected'] else '誤收'}** "
        f"`{row['expected_error_code']}`"
        for row in result["attacks"]
    )
    source_links = "\n".join(
        f"- [{source['owner']}｜{source['title']}]({source['url']})"
        for source in result["primary_sources"].values()
    )
    return f"""# 短線個股第 21 輪：多供應商正式數據補缺報告

證據截至：{result["evidence_as_of"]}

## 一頁結論

**五條固定路徑沒有一條合格。** 公開一手文件最多只把
`{best["id"]}` 收窄至 **{best["explicit_count"]}/14 明確、
{best["partial_count"]}/14 部分**；它仍有 **{best["hard_gap_count"]}/14**
不是明確能力。LSEG 是最完整的單一品牌採購候選，但同樣未公開證明 S&P 500 逐列公布
時間、退市實收回報、精確一個月日度簡單 RF 及使用者授權。

這輪找到的是**可判定的詢價次序**，不是可跑回測的市場列。十五道證據控制
**{result["control_summary"]["passed"]}/{result["control_summary"]["total"]} 通過**，十五項單一
替代攻擊 **{result["attack_summary"]["rejected"]}/{result["attack_summary"]["total"]} 全部拒收**；
它只證明 validator fail closed。真實正式就緒仍為
**{result["actual_formal_readiness"]["passed"]}/{result["actual_formal_readiness"]["total"]}**，授權
provider package **0**、完整 RF **0**、正式策略運行 **0 次**、短線 Paper **全現金**、持倉
**0**、實金動作 **US$0**。

## 五條固定路徑

「明確」只代表官方文件明示產品／欄位能力；「部分」仍是缺口。公開頁最高只可成為採購
候選，不能當作已訂閱、已授權、已交付或 20 年覆蓋通過。

{route_table}

### 重要反證

- S&P Global Market Intelligence 的公開 Index Data 及 Market Data 規格均標示
  `Point In Time: No`；歷史很長也不能補成逐期可知資料。
- S&P DJI 政策把公布及生效分開，並描述日常 corporate-event／pro-forma 文件；公開頁仍
  未提供本帳戶可下載的逐列 event ID、完整舊檔及授權條款。
- LSEG 可用 as-of 成分加 Joiner／Leaver 重建歷史，且 Quantitative Analytics 說明
  point-in-time、已退市公司、永久 ID 及歷史成分；但「涵蓋已退市公司」不等於提供每次
  退出的實際現金／換股收益。
- FactSet Benchmarks API 可按指定日期取得成分；as-of date 不等於 announcement time。
- Bloomberg Data License 有 20 年以上 Bulk 歷史、公司行動、歷史價格及 source-file
  tracing；其 company／pricing PIT 產品公開覆蓋為 17 年，亦未證明 S&P 500 membership
  事件能按本合約逐列交付。

## 十四項能力矩陣

{capability_table}

## 第一封詢價只問九個可驗收問題

先向 CRSP＋S&P DJI 複合路徑及 LSEG 單一品牌路徑索取相同細樣本。任何回答只有
「可以」「有歷史」「可經 API 取得」而沒有產品代碼、欄位、timestamp、覆蓋率及樣本，
一律保持未解。

{questions}

## 收到真實樣本後的固定順序

1. 供應商文件 12/12：產品、授權、覆蓋、時間及退出條款逐項入 manifest；
2. 本地隔離匯入 16/16：原始 package 不修改、逐檔列數與 SHA-256 齊備；
3. point-in-time 20/20：成分、身份、公司行動、退市及幽靈價格全部 fail closed；
4. execution extension 16/16：252 個 prior sessions、移除後路徑及同步 QQQ／SPY；
5. 精確 RF 完整：不以 4 週、年率／252、DGS1MO、SHY、SOFR 或零回報代替；
6. 正式就緒 18/18 後，才准使用一次性 run ID 原樣運行凍結的 20 年回測；
7. 只有正式回測及前瞻 Paper 推廣閘門都通過，才可討論下一階段，並仍不等於保證盈利。

## 十五道證據控制

{controls}

## 十五項單一錯誤攻擊

{attacks}

## 官方一手來源

{source_links}

- [第 21 輪事前協議](SHORT_TERM_PROVIDER_GAP_CLOSURE_PROTOCOL.md)
- [第 20 輪供應商收斂報告](SHORT_TERM_PROVIDER_CONVERGENCE_REPORT.md)
- [第 18 輪正式回測事前登記](SHORT_TERM_FORMAL_BACKTEST_PREREGISTRATION.md)

本報告只作研究及專業資訊參考，不構成供應商背書、採購建議、投資建議、回報預測或
盈利保證。
"""


def main() -> int:
    result = run_provider_gap_closure_validation(ROOT)
    artifact_payload = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    site_payload = (
        json.dumps(_site_summary(result), ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    )
    ARTIFACT.parent.mkdir(parents=True, exist_ok=True)
    SITE_DATA.parent.mkdir(parents=True, exist_ok=True)
    ARTIFACT.write_text(artifact_payload, encoding="utf-8")
    SITE_DATA.write_text(site_payload, encoding="utf-8")
    REPORT.write_text(_report(result), encoding="utf-8")
    print(
        json.dumps(
            {
                "status": result["status"],
                "best_documented_route": result["best_documented_route"],
                "qualified_route_count": 0,
                "controls": result["control_summary"],
                "attacks": result["attack_summary"],
                "formal_readiness": result["actual_formal_readiness"],
                "strategy_run_count": 0,
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
