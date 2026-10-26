from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from usfddk.formal_backtest_readiness_validation import (
    run_formal_backtest_readiness_validation,
)

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "artifacts/short_term_formal_backtest_readiness_validation.json"
SITE_DATA = ROOT / "site/data/short-term-formal-backtest-readiness.json"
REPORT = ROOT / "docs/SHORT_TERM_FORMAL_BACKTEST_READINESS_REPORT.md"


def _site_summary(result: dict[str, Any]) -> dict[str, Any]:
    control = result["synthetic_control"]
    trial_ledger = result["protocol_integrity"]["global_trial_ledger"]
    return {
        "schema_version": 1,
        "research_round": 18,
        "evidence_as_of": result["evidence_as_of"],
        "governance_as_of": result["governance_as_of"],
        "status": result["status"],
        "gap_closed": result["gap_closed"],
        "synthetic_control": {
            "gate_summary": control["gate_summary"],
            "gates": control["gates"],
            "risk_free_sessions": control["risk_free_sessions"],
            "global_search_trials": control["policy"]["statistics"]["global_search_trials"],
            "global_trial_ledger": {
                "original_preregistration_trials": trial_ledger["original_preregistration_trials"],
                "current_lower_bound": trial_ledger["current_lower_bound"],
                "exact_global_count_claimed": trial_ledger["exact_global_count_claimed"],
                "entry_count": trial_ledger["entry_count"],
                "reserved_unrun_family_count": trial_ledger["reserved_unrun_family_count"],
            },
            "pbo_paths": len(control["policy"]["statistics"]["pbo_paths"]),
            "baselines": control["policy"]["baselines"],
            "formal_stock_backtest_authorized": control["formal_stock_backtest_authorized"],
        },
        "attacks": result["attacks"],
        "attack_summary": result["attack_summary"],
        "actual_formal_readiness": result["actual_formal_readiness"],
        "actual_point_in_time_readiness": result["actual_point_in_time_readiness"],
        "actual_local_intake": result["actual_local_intake"],
        "authorized_provider_package_received": result["authorized_provider_package_received"],
        "risk_free_provider_input_received": result["risk_free_provider_input_received"],
        "formal_stock_backtest_completed": result["formal_stock_backtest_completed"],
        "strategy_run_count": result["strategy_run_count"],
        "paper": result["paper"],
        "real_money_action_usd": result["real_money_action_usd"],
        "next_action": result["next_action"],
        "disclaimer": result["disclaimer"],
    }


def _report(result: dict[str, Any]) -> str:
    control = result["synthetic_control"]
    trial_ledger = result["protocol_integrity"]["global_trial_ledger"]
    attacks = result["attack_summary"]
    policy = control["policy"]
    gates = "\n".join(
        f"| {row['id']} | {row['label']} | 通過 | {row['detail']} |" for row in control["gates"]
    )
    attack_rows = "\n".join(
        f"| {row['id']} | {row['label']} | `{row['observed_error_code']}` | "
        f"{'拒收' if row['rejected'] else '失敗'} |"
        for row in result["attacks"]
    )
    baselines = "、".join(f"`{value}`" for value in policy["baselines"])
    return f"""# 短線個股第十八輪：正式回測就緒報告

原始正式輸入證據截至：{result["evidence_as_of"]}

試驗帳本治理截至：{result["governance_as_of"]}

## 結論先行

本輪把一次性正式 20 年回測的資料與統計缺口在結果出現前鎖定，合成就緒控制
**{control["gate_summary"]["passed"]}/{control["gate_summary"]["total"]}**，單一錯誤攻擊
**{attacks["rejected"]}/{attacks["total"]}** 全數按指定 error code 拒收。這只證明管線會
失敗關閉，不是回測成績。

真實狀態仍是：正式就緒 **1/18**、point-in-time **1/20**、本地 provider intake
**1/16**；合法 provider package 及同步 US 1M T-bill RF 包均未收到，正式策略運行
**0 次**，短線 Paper **全現金**，持倉 0，歷史成交 0，實金動作 **US$0**。

## 為何不能現在直接報高回報

既有第十五／十七輪 package 只有 QQQ／SPY，沒有超額 Sharpe、PSR 及 DSR 所需的真正
風險免費日回報。用 0 或 SHY 偷代會改變統計結論。本輪因此新增與 XNYS session 一對一
的 `US_1M_TBILL_DAILY_RETURN`，固定 decimal simple daily return、來源版本、授權、列數及
SHA-256；合成控制共有 {control["risk_free_sessions"]} 個短樣本 session，沒有供應商列。

另一個舊歧義是「同股漂移」曾在有偏差沙盒被實作成整個今日完整股池起點等權。本輪在
正式結果前修正定義：只用第一個正式訊號的 Top-10 各 10% 買入一次，其後只處理公司
行動及退出、不主動再平衡。這才真正分開每月輪選與首輪選股後單純持有。

## 凍結比較與統計

- Baseline：{baselines}。
- 成本：單邊 {policy["execution"]["costs_bps"][0]}／{policy["execution"]["costs_bps"][1]}／{policy["execution"]["costs_bps"][2]} bps，全部用下一正式交易日 raw open 真實重跑。
- 顯示資金：US${policy["execution"]["starting_capital_usd"]:,}，容許 fractional shares；
  現金回報固定 0%，QQQ 補位不是現金。
- Newey–West lag 沿用既有公式；DSR 固定懲罰
  {policy["statistics"]["global_search_trials"]:,} 次全專案路徑，不重設為 1。
- 第十八輪原始收據仍保留 {trial_ledger["original_preregistration_trials"]:,}；第 24–28 輪
  已查看的 39 個共同假說、第 29／30／38／39 輪、本地未發佈負結果的最低三路徑，以及
  第 41 輪八個事前預留比較均只可追加，令目前保守下限為
  {trial_ledger["current_lower_bound"]:,}。帳本明示這是下限、不是虛構的精確總數。
- PBO 固定 {len(policy["statistics"]["pbo_paths"])} 條既有路徑、
  {policy["statistics"]["pbo_slices"]} 段 CSCV；不以 PBO 勝出版本替換正式候選。

## 十八道合成控制

| # | 閘門 | 結果 | 核對內容 |
|---|---|---|---|
{gates}

## 十八項失敗攻擊

| # | 單一錯誤 | 實際 error code | 結果 |
|---|---|---|---|
{attack_rows}

## 下一步與決策邊界

{result["next_action"]}
正式 package 必須 owner-only 且在 repository 外；就緒 18/18 只授權
immutable run ID 的一次固定回測。回測仍須逐項通過 QQQ +2 個百分點、50 bps、前後十年、
滾動三年、逐期等權、首輪同十股漂移、NW／PSR／DSR／PBO 及最大跌幅門檻。

任一項失敗就封存為 `formal_backtest_failed_no_rescue`，不在同一資料上改權重、窗口、持股
數或成本救援。全部通過才可由下一個真正新增交易日開始前瞻 Paper，仍須 252 個新增
session 及 12 次完成輪選；不回填歷史，也不代表實金授權或保證盈利。

## 參考來源

- [Kenneth R. French Data Library](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/Data_Library.html)
- [Fama/French factors 及一個月國庫券 RF 說明](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library/f-f_factors.html)
- [第十八輪事前登記](SHORT_TERM_FORMAL_BACKTEST_PREREGISTRATION.md)
- [全域試驗次數不可回減帳本](SHORT_TERM_GLOBAL_TRIAL_LEDGER_PROTOCOL.md)
- [第 41 輪 Form 4 v1.0 歷史草稿](SHORT_TERM_FORM4_CLUSTER_PROTOCOL.md)
- [第 41 輪 Form 4 v1.1 有效事前修訂](SHORT_TERM_FORM4_CLUSTER_PROTOCOL_AMENDMENT_V1_1.md)
- [短線 v1.1 協議](SHORT_TERM_HIGH_RETURN_PROTOCOL.md)
- [第十七輪本地隔離入口報告](SHORT_TERM_LOCAL_QUARANTINE_INTAKE_REPORT.md)

本報告只作研究及專業資訊參考。合成控制不是真實數據、正式回測、Paper 或盈利證明。
"""


def main() -> int:
    result = run_formal_backtest_readiness_validation(ROOT)
    ARTIFACT.parent.mkdir(parents=True, exist_ok=True)
    SITE_DATA.parent.mkdir(parents=True, exist_ok=True)
    ARTIFACT.write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    SITE_DATA.write_text(
        json.dumps(_site_summary(result), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    REPORT.write_text(_report(result), encoding="utf-8")
    print(
        json.dumps(
            {
                "status": result["status"],
                "synthetic_gate_summary": result["synthetic_control"]["gate_summary"],
                "attack_summary": result["attack_summary"],
                "actual_formal_readiness": result["actual_formal_readiness"],
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
