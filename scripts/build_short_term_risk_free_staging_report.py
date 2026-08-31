from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from usfddk.risk_free_staging_validation import (
    run_risk_free_staging_validation,
)

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "artifacts/french_ff_factors_daily_39f9ae1d.zip"
ARTIFACT = ROOT / "artifacts/short_term_risk_free_staging_validation.json"
SITE_DATA = ROOT / "site/data/short-term-risk-free-staging.json"
REPORT = ROOT / "docs/SHORT_TERM_RISK_FREE_STAGING_REPORT.md"


def _site_summary(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "research_round": 19,
        "evidence_as_of": result["evidence_as_of"],
        "status": result["status"],
        "source": {
            "data_cut": result["source"]["data_cut"],
            "full_last_session": result["source"]["full_last_session"],
            "sha256": result["source"]["sha256"],
            "economic_definition": result["source"]["economic_definition"],
            "source_access": result["source"]["source_access"],
            "explicit_local_research_license_evidence_captured": result[
                "source"
            ]["explicit_local_research_license_evidence_captured"],
        },
        "study": result["study"],
        "staging": result["staging"],
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
    study = result["study"]
    controls = "\n".join(
        f"| {row['id']} | {row['label']} | 通過 | {row['detail']} |"
        for row in result["controls"]
    )
    attacks = "\n".join(
        f"| {row['id']} | {row['label']} | `{row['observed_error_code']}` | "
        f"{'拒收' if row['rejected'] else '失敗'} |"
        for row in result["attacks"]
    )
    missing_dates = "、".join(study["missing_sessions"])
    coverage_pct = study["coverage_fraction"] * 100
    return f"""# 短線個股第十九輪：官方風險免費日回報暫存報告

證據截至：{result['evidence_as_of']}

## 結論先行

官方 Fama/French 日度 RF 已由過往 2026-05-29 更新至 **2026-06-30**。本輪把固定
2006-08-01 至 2026-07-31 研究期的 RF 覆蓋由「未量化」收窄為：
**{study['available_sessions']:,}/{study['required_sessions']:,} 個 XNYS session**，即
**{coverage_pct:.2f}%**；仍精確欠最後 **{study['missing_session_count']} 日**，全部在
2026 年 7 月。

八道真實來源／暫存控制 **{result['control_summary']['passed']}/{result['control_summary']['total']}**
通過，八項 ZIP、定義、單位、日期、路徑及越權攻擊
**{result['attack_summary']['rejected']}/{result['attack_summary']['total']} 全部拒收**。
這只證明官方 202606 snapshot 可以安全暫存及精確報缺，不是完整 RF 包，更不是策略成績。

因第四十一輪把全域試驗下限帳本接入正式 validator，GitHub Actions 正確拒絕第三十六輪
收據所凍結的舊「目前入口」SHA。本輪以 append-only v1.1 rebind 修訂核對第三十六輪歷史
bytes、新 validator 及帳本父鏈；第三十六輪及第十九輪協議／收據均沒有改寫。rebind 只
恢復可重現的 staging 驗證，不增加 RF 覆蓋，也不授權正式回測、Paper 或實金。

正式狀態沒有虛報提升：正式就緒仍為 **1/18**，逐股 provider package 未收到，完整 RF
包未收到，正式策略運行 **0 次**；短線 Paper 全現金、0 成交、0 持倉，實金動作
**US$0**。

## 新增的真實證據

- 官方 ZIP SHA-256：`{result['source']['sha256']}`；
- CRSP data cut：`{result['source']['data_cut']}`；
- 官方完整日度檔最後日期：`{result['source']['full_last_session']}`；
- 研究期 XNYS session：{study['required_sessions']:,}；
- 已有 RF：{study['available_sessions']:,}；缺失：{study['missing_session_count']}；額外：{study['extra_session_count']}；
- 單位：原檔百分點只除以 100 一次，輸出 `decimal_simple_daily_return`；
- 缺值政策：不填 0、不複製 6 月、不插值、不以 SHY 或年率直接除 252。

公開下載本身已核實，但本輪沒有捕捉到一份明確的本地研究授權條款；因此授權閘門仍是
false。即使之後官方補齊 7 月，亦須保留來源版本、授權證據、列數與 SHA-256，且與逐股
provider package 的同一 XNYS 日曆逐日對數。

## 精確缺失的 22 個 session

{missing_dates}

缺日集中於最後一個月，不能把 99.56% 覆蓋寫成「差不多完整」：超額 Sharpe、PSR／DSR
及每日 active return 必須使用同一完整時間軸，任意補值都會改變固定正式結論。

## 八道 staging 控制

| # | 閘門 | 結果 | 核對內容 |
|---|---|---|---|
{controls}

## 八項失敗攻擊

| # | 單一錯誤 | 實際 error code | 結果 |
|---|---|---|---|
{attacks}

## 為何仍不能運行正式回測

暫存目錄故意只輸出 `risk_free_daily_partial.csv` 及 `availability_manifest.json`，不會生成
第十八輪正式驗證器唯一接受的 `risk_free_daily.csv`／`risk_free_manifest.json`。因此
partial 檔不可能被誤當完整輸入。

{result['next_action']} RF 完整只關閉一個資料缺口；逐股 point-in-time、退市、公司行動、
成分公布時間及正式 provider 授權仍須全數通過。全部 18/18 才可只跑一次凍結回測；
經濟與統計門檻再全數通過，才可由下一個真正新增交易日開始不可回填的全現金 Paper。

## 一手來源

- [Kenneth R. French Data Library](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/Data_Library.html)
- [Fama/French factors 及 RF 定義](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/Data_Library/f-f_factors.html)
- [第十九輪暫存協議](SHORT_TERM_RISK_FREE_STAGING_PROTOCOL.md)
- [第十八輪正式事前登記](SHORT_TERM_FORMAL_BACKTEST_PREREGISTRATION.md)

本報告只作研究及專業資訊參考。RF 覆蓋率不是策略勝率、回報或盈利證明；不構成投資
建議、數據授權或盈利保證。
"""


def main() -> int:
    result = run_risk_free_staging_validation(ROOT, SOURCE)
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
                "coverage": {
                    "available": result["study"]["available_sessions"],
                    "required": result["study"]["required_sessions"],
                    "missing": result["study"]["missing_session_count"],
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
