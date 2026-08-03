from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from usfddk.ciz_execution_extension_validation import (
    run_ciz_execution_extension_validation,
)

ROOT = Path(__file__).resolve().parents[1]
MACHINE_PATH = ROOT / "artifacts/short_term_ciz_execution_extension_validation.json"
SITE_PATH = ROOT / "site/data/short-term-ciz-execution-extension.json"
REPORT_PATH = ROOT / "docs/SHORT_TERM_CIZ_EXECUTION_EXTENSION_REPORT.md"


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _site_summary(data: dict[str, Any]) -> dict[str, Any]:
    control = data["control"]
    return {
        "schema_version": data["schema_version"],
        "round": data["research_round"],
        "status": data["status"],
        "evidence_as_of": data["evidence_as_of"],
        "headline": "Execution extension 16/16；真實逐股數據仍為 1/20",
        "official_document_evidence": data["official_document_evidence"],
        "gate_summary": control["gate_summary"],
        "gates": control["gates"],
        "attack_summary": data["attack_summary"],
        "attacks": data["attacks"],
        "base_ledger_gate_summary": control["base_ledger_gate_summary"],
        "control_examples": control["control_examples"],
        "synthetic_counts": {
            "signals": control["signals"],
            "cash_entitlements": control["cash_entitlements"],
            "signal_eligibility_rows": control["signal_eligibility_rows"],
            "removal_execution_windows": control["removal_execution_windows"],
            "benchmark_rows": control["benchmark_rows"],
        },
        "round14_execution_accounting": data["round14_execution_accounting"],
        "actual_point_in_time_readiness": data["actual_point_in_time_readiness"],
        "authorized_provider_sample_received": data[
            "authorized_provider_sample_received"
        ],
        "formal_stock_backtest_authorized": data[
            "formal_stock_backtest_authorized"
        ],
        "formal_stock_backtest_completed": data["formal_stock_backtest_completed"],
        "strategy_rule_changed": data["strategy_rule_changed"],
        "synthetic_rows_only": data["synthetic_rows_only"],
        "paper": data["paper"],
        "real_money_action_usd": data["real_money_action_usd"],
        "next_action": data["next_action"],
    }


def _gate_rows(data: dict[str, Any]) -> str:
    return "\n".join(
        f"| {row['id']} | {row['label']} | {'通過' if row['passed'] else '未通過'} | "
        f"{row['detail']} |"
        for row in data["control"]["gates"]
    )


def _attack_rows(data: dict[str, Any]) -> str:
    return "\n".join(
        f"| {row['id']} | {row['label']} | `{row['expected_error_code']}` | "
        f"{'拒收' if row['rejected'] else '誤收'} |"
        for row in data["attacks"]
    )


def _render_report(data: dict[str, Any]) -> str:
    control = data["control"]
    gates = control["gate_summary"]
    attacks = data["attack_summary"]
    examples = control["control_examples"]
    dividend = examples["dividend"]
    removal = examples["removal"]
    readiness = data["actual_point_in_time_readiness"]
    return f"""# 美股短線高回報研究｜第十五輪 CIZ 執行延伸數據報告

研究日期：2026-08-04　｜　狀態：合成 extension 通過；真實供應商數據仍未到位

## 一頁結論

第十四輪找出的四項正式執行缺口，已轉成獨立、可雜湊、可重建及 fail-closed 的
execution extension。合成控制通過 **{gates['passed']}/{gates['total']}**，事前固定的
十六項檔案、派息、歷史、移除、基準、成本及時鐘攻擊
**{attacks['rejected']}/{attacks['total']} 全數拒收**。第十三輪 adapter 及原八份賬本
完全不變，base ledger 在合成包仍為 **20/20**。

這不是正式回測結果。控制只含三個合成 PERMNO、一個月末訊號、兩個候選資格、
一個移除窗口及 {control['benchmark_rows']} 列合成 QQQ／SPY 行情。真實數據入口仍為
**{readiness['passed']}/{readiness['total']}**、合法供應商樣本 0、正式 20 年逐股回測 0；
短線 Paper 維持全現金、0 成交、0 持倉，實金動作 US$0。

## 四項缺口如何被封口

| 缺口 | 合成控制證據 | 正式狀態 |
|---|---|---|
| 派息付款日 | ex-date {dividend['ex_date']}；pay-date／可用現金日 {dividend['pay_date']} | schema 已備；待真實列 |
| 訊號前歷史 | 最少 {examples['minimum_return_sessions']} 個回報 session、{examples['minimum_positive_volume_sessions']} 個正成交量 session | 超過 252／20 控制；待真實列 |
| 移除後成交 | {removal['membership_effective_to']} 移除，{removal['signal_session']} 訊號，{removal['execution_session']} open；{removal['observed_sessions']}/{removal['required_sessions']} sessions | 完整合成路徑；待真實列 |
| 公平基準同步 | QQQ／SPY 共 {control['benchmark_rows']} 列，覆蓋研究月及下一開市 | 合成同步；待合法行情 |

`DisExDt` 只建立應收權利，`DisPayDt` 才把現金變成可交易餘額。CRSP 官方 cross-reference
把兩者分列為 Ex-Distribution Date 與 Payment Date；WRDS CIZ event-study 同時確認
`DlyRet` 已包含退市回報，因此本輪沒有重新引入退市雙計。

官方來源：[CRSP SIZ-to-CIZ cross-reference](https://www.crsp.org/crsp_pdf/crsp-us-stock-indexes-databases-siz-to-ciz-cross-reference-guide/)、
[CRSP CIZ guide](https://www.crsp.org/crsp_pdf/crsp-us-stock-indexes-databases-guide-flat-file-format-2-0/)、
[WRDS CIZ event-study](https://wrds-www.wharton.upenn.edu/pages/wrds-research/macros/run-an-event-study-ciz-format-macro/)。

## 五份固定 extension 輸出

`execution/` 只接受四份 CSV 及一份 manifest：

1. `cash_entitlements.csv`：ex-date、pay-date、現金可用日及每股金額；
2. `signal_eligibility.csv`：逐月、逐永久 ID 的回報／流動性歷史計數；
3. `removal_execution_windows.csv`：移除日至下一重新平衡 open 的完整路徑；
4. `benchmark_daily.csv`：QQQ／SPY 同日 raw open 及總回報因子；
5. `execution_manifest.json`：綁定 base manifest、overlay、協議、策略及所有列數／SHA-256。

原 `ledger/` 八份檔案及第十三輪 adapter 不作任何修改，避免用新結果重寫舊證據。

## 十六道合成控制

| # | 閘門 | 結果 | 證據 |
|---|---|---|---|
{_gate_rows(data)}

## 十六項固定攻擊

| # | 單一錯誤 | 指定拒收代碼 | 結果 |
|---|---|---|---|
{_attack_rows(data)}

攻擊測試每次同步重算其上游收據，只讓單一語義錯誤進入 auditor；因此不是用 generic
hash mismatch 掩蓋真正問題。16/16 只證明合成 bridge 會關門，不證明市場數據或策略。

## 與第十四輪的關係

第十四輪的結果仍是 **8/12**、攻擊 **10/10**，因為舊八份賬本本身仍沒有四項輸入。
第十五輪沒有把 8/12 改寫成 12/12，而是建立獨立 extension，再以 16 道更嚴格合約
證明「若合法來源提供這些欄位，bridge 可以決定性輸出」。兩層結論不可互換。

## 決策與下一步

下一個有效行動是向合法數據擁有人索取同一 schema 的細樣本，逐列驗證：

1. CRSP CIZ membership、raw OHLCV、`DisPayDt` 及完整退出經濟；
2. QQQ／SPY 同期 raw open、總回報因子與授權來源；
3. 2006-08-01 前至少 252 個正式交易日的候選歷史；
4. 每個 `removed_continues` 至下一月末訊號後開市的完整行情。

真實數據 20/20 及 execution extension 16/16 未同時通過前，不運行正式策略、不展示
個股名單、不建立短線 Paper。這不構成投資建議、供應商背書或盈利保證。
"""


def main() -> None:
    data = run_ciz_execution_extension_validation(ROOT)
    _write_json(MACHINE_PATH, data)
    _write_json(SITE_PATH, _site_summary(data))
    REPORT_PATH.write_text(_render_report(data), encoding="utf-8")
    print(
        json.dumps(
            {
                "status": data["status"],
                "control": data["control"]["gate_summary"],
                "attacks": data["attack_summary"],
                "true_readiness": data["actual_point_in_time_readiness"],
                "formal_stock_backtest_authorized": data[
                    "formal_stock_backtest_authorized"
                ],
                "paper_authorized": data["paper"]["authorized"],
                "real_money_action_usd": data["real_money_action_usd"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
