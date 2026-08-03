from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from usfddk.ciz_execution_accounting import run_ciz_execution_accounting_validation

ROOT = Path(__file__).resolve().parents[1]
MACHINE_PATH = ROOT / "artifacts/short_term_ciz_execution_accounting_validation.json"
SITE_PATH = ROOT / "site/data/short-term-ciz-execution-accounting.json"
REPORT_PATH = ROOT / "docs/SHORT_TERM_CIZ_EXECUTION_ACCOUNTING_REPORT.md"


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _site_summary(data: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": data["schema_version"],
        "round": data["research_round"],
        "status": data["status"],
        "evidence_as_of": data["evidence_as_of"],
        "headline": "退出會計 8/12；十項攻擊全拒收，四項正式引擎輸入仍缺",
        "protocol_integrity": data["protocol_integrity"]["passed"],
        "official_document_evidence": data["official_document_evidence"],
        "accounting_controls": data["accounting_controls"],
        "gate_summary": data["gate_summary"],
        "gates": data["gates"],
        "attack_summary": data["attack_summary"],
        "attacks": data["attacks"],
        "unresolved_execution_inputs": data["unresolved_execution_inputs"],
        "round13_control_ledger_gates": data["round13_control_ledger_gates"],
        "actual_point_in_time_readiness": data["actual_point_in_time_readiness"],
        "authorized_provider_sample_received": data["authorized_provider_sample_received"],
        "formal_stock_backtest_authorized": data["formal_stock_backtest_authorized"],
        "formal_stock_backtest_completed": data["formal_stock_backtest_completed"],
        "strategy_rule_changed": data["strategy_rule_changed"],
        "paper": data["paper"],
        "real_money_action_usd": data["real_money_action_usd"],
        "next_action": data["next_action"],
    }


def _gate_rows(data: dict[str, Any]) -> str:
    return "\n".join(
        f"| {row['id']} | {row['label']} | {'通過' if row['passed'] else '未通過'} | {row['detail']} |"
        for row in data["gates"]
    )


def _attack_rows(data: dict[str, Any]) -> str:
    return "\n".join(
        f"| {row['id']} | {row['label']} | `{row['expected_error_code']}` | "
        f"{'拒收' if row['rejected'] else '誤收'} |"
        for row in data["attacks"]
    )


def _render_report(data: dict[str, Any]) -> str:
    gates = data["gate_summary"]
    attacks = data["attack_summary"]
    controls = data["accounting_controls"]
    gaps = "、".join(data["unresolved_execution_inputs"])
    return f"""# 美股短線高回報研究｜第十四輪 CIZ 執行與退出會計報告

研究日期：2026-08-04　｜　狀態：會計防線通過；正式引擎輸入未齊

## 一頁結論

第十三輪的八份合成賬本雖通過 20/20，但本輪證明該結果只代表資料合約完整，不能直接
推論策略資產淨值可正確執行。本輪在寫 auditor 前固定十二道執行閘門及十項攻擊，沒有
改動短線 v1 訊號、成本、baseline 或 Paper 門檻。

會計控制通過 **{gates['passed']}/{gates['total']}**，十項雙計、提早入賬、缺價及時鐘
攻擊 **{attacks['rejected']}/{attacks['total']} 全數拒收**。確認 `DelDlyDt` 的 return-only
列沒有流入普通日回報；最後持倉值 100、`DelRet=-50%` 時，終端值恰為 50，而不是 25。
現金收購、換股、拆細及分拆例子亦各只結算一次。

仍未通過四項：**{gaps}**。因此正式 20 年逐股回測仍為 0，真實數據入口仍為
**{data['actual_point_in_time_readiness']['passed']}/{data['actual_point_in_time_readiness']['total']}**；
短線 Paper 維持全現金、0 成交、0 持倉，實金動作 US$0。

## 為何這不是小問題

- WRDS 的 CIZ event-study 範例明示 CIZ 日回報已包含退市回報；若 storage row 與
  outcome 同時計入，100 元在 -50% 退出下會錯算成 25 元。
- `DisExDt` 決定派息權利，`DisPayDt` 決定現金何時收到。現行 adapter 把 dividend
  `effective_date` 寫成 ex-date，沒有保留 pay-date，可能在付款前把應收股息拿去交易。
- 成分股在月中被移除但繼續上市時，原持倉要到下一次月度 open 才沽出。現行 20 道
  audit 只要求移除日後至少一列價格，沒有保證整段可成交。
- 12–1 動量需要 252 日歷史；「在籍期間價格完整」不代表新加入成分已有加入前歷史。
- QQQ、SPY 及不足十股時的 QQQ 補位是凍結規則的一部分，但不在八份逐股賬本內。

官方來源：[WRDS CIZ event-study](https://wrds-www.wharton.upenn.edu/pages/wrds-research/macros/run-an-event-study-ciz-format-macro/)、
[WRDS CIZ-to-SIZ macro](https://wrds-www.wharton.upenn.edu/pages/wrds-research/macros/crsp-ciztosiz-macro/)、
[CRSP CIZ guide](https://www.crsp.org/crsp_pdf/crsp-us-stock-indexes-databases-guide-flat-file-format-2-0/)。

## 五個固定會計例子

| 例子 | 輸入 | 唯一正確結果 |
|---|---|---|
| 有 DelRet 退市 | 100 × (1 − 50%) | {controls['delisting_terminal_value_once']:.2f} |
| 缺 DelRet 現金收購 | 2 股 × US$50 | US${controls['cash_exit_terminal_value']:.2f} |
| 缺 DelRet 換股 | 4 股 × 0.5 | {controls['stock_exit_successor_shares']:.2f} 股 successor |
| 2-for-1 拆細 | 1 × 100 → 2 × 50 | {controls['split_before_value']:.2f} → {controls['split_after_value']:.2f} |
| 分拆權利 | 4 股 × 0.25 | {controls['spinoff_successor_shares']:.2f} 股 successor |

## 十二道執行閘門

| # | 閘門 | 結果 | 證據 |
|---|---|---|---|
{_gate_rows(data)}

## 十項固定攻擊

| # | 單一錯誤 | 指定拒收代碼 | 結果 |
|---|---|---|---|
{_attack_rows(data)}

攻擊結果只證明 auditor 會拒絕這十類錯誤，不代表供應商數據、正式引擎或策略通過。

## 決策與下一步

Round 13 的 20/20 保留，但解讀收窄為「八份資料賬本通過既有完整性合約」。正式回測
另須本輪 12/12；目前只有 {gates['passed']}/{gates['total']}，所以不得啟動引擎。

下一步先凍結 CIZ adapter v2／execution extension，再加入：

1. dividend ex-date 與 pay-date 分欄，付款前只作應收、不可交易；
2. 每股訊號前至少 252 日回報及 20 日成交額覆蓋；
3. `removed_continues` 至下一月度 open 的完整價格；
4. QQQ／SPY／QQQ 補位的同步 raw open、總回報及成本來源。

上述四項未全部通過前，不運行正式策略、不調整凍結規則、不建立短線 Paper。這不構成
投資建議、供應商背書或盈利保證。
"""


def main() -> None:
    data = run_ciz_execution_accounting_validation(ROOT)
    _write_json(MACHINE_PATH, data)
    _write_json(SITE_PATH, _site_summary(data))
    REPORT_PATH.write_text(_render_report(data), encoding="utf-8")
    print(
        json.dumps(
            {
                "status": data["status"],
                "gates": data["gate_summary"],
                "attacks": data["attack_summary"],
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
