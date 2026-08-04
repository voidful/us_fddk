from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np

from usfddk.qqq_replacement_overlay import run_qqq_replacement_overlay

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "artifacts/short_term_qqq_replacement_overlay_validation.json"
SITE_DATA = ROOT / "site/data/short-term-qqq-replacement-overlay.json"
REPORT = ROOT / "docs/SHORT_TERM_QQQ_REPLACEMENT_OVERLAY_RESEARCH_REPORT.md"
RECEIPT_FLOAT_DECIMAL_PLACES = 12


def _canonicalize_floats(value: Any) -> Any:
    if isinstance(value, np.generic):
        return _canonicalize_floats(value.item())
    if isinstance(value, float):
        rounded = round(value, RECEIPT_FLOAT_DECIMAL_PLACES)
        return 0.0 if rounded == 0.0 else rounded
    if isinstance(value, dict):
        return {key: _canonicalize_floats(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_canonicalize_floats(item) for item in value]
    return value


def _pct(value: float, digits: int = 2) -> str:
    return f"{value * 100:.{digits}f}%"


def _signed_pct(value: float, digits: int = 2) -> str:
    return f"{value * 100:+.{digits}f}%"


def _money(value: float) -> str:
    return f"US${value:,.0f}"


def _path_table(result: dict[str, Any]) -> str:
    lines = [
        "| 固定路徑 | CAGR | US$1,000 終值 | SHY 超額 Sharpe | 最大跌幅 | 年率化換手 | 平均股票持倉 |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in result["paths"].values():
        lines.append(
            f"| {row['label']} | {_pct(row['cagr'])} | {_money(row['terminal_usd'])} | "
            f"{row['shy_excess_sharpe']:.2f} | {_pct(row['max_drawdown'])} | "
            f"{row['annual_turnover']:.1f}x | {_pct(row['average_exposure'], 1)} |"
        )
    return "\n".join(lines)


def _family_table(result: dict[str, Any]) -> str:
    lines = [
        "| 候選相對基準 | 年率化算術差 | NW t | Holm p | 共同 max-t p | 全專案 p | 前半／後半日均 |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in result["family"]["comparisons"]:
        first = row["fixed_halves"]["first"]["mean_daily_difference"] * 10_000
        second = row["fixed_halves"]["second"]["mean_daily_difference"] * 10_000
        lines.append(
            f"| {row['baseline_label']} | {_signed_pct(row['newey_west']['annualized_arithmetic_difference'])} | "
            f"{row['newey_west']['t_stat']:.2f} | {row['holm_adjusted_p']:.4f} | "
            f"{row['bootstrap_max_t_p']:.4f} | {row['global_bonferroni_p']:.4f} | "
            f"{first:+.2f}／{second:+.2f} bp |"
        )
    return "\n".join(lines)


def _cost_table(result: dict[str, Any]) -> str:
    lines = [
        "| 每資產來回成本 | 正常事件名義總成本 | 候選 CAGR | QQQ CAGR | eligible overlay | complete overlay | 候選減 QQQ |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    primary = result["paths"]
    lines.append(
        f"| 20 bp | 40 bp | {_pct(primary['top7_qqq_overlay']['cagr'])} | "
        f"{_pct(primary['qqq_buy_hold']['cagr'])} | {_pct(primary['eligible_qqq_overlay']['cagr'])} | "
        f"{_pct(primary['complete_qqq_overlay']['cagr'])} | "
        f"{_signed_pct(primary['top7_qqq_overlay']['cagr'] - primary['qqq_buy_hold']['cagr'])} |"
    )
    for key in ("50", "100"):
        row = result["stresses"]["costs"][key]
        paths = row["paths"]
        lines.append(
            f"| {key} bp | {row['normal_overlay_event_total_nominal_bps']} bp | "
            f"{_pct(paths['top7_qqq_overlay']['cagr'])} | {_pct(paths['qqq_buy_hold']['cagr'])} | "
            f"{_pct(paths['eligible_qqq_overlay']['cagr'])} | {_pct(paths['complete_qqq_overlay']['cagr'])} | "
            f"{_signed_pct(row['candidate_cagr_differences']['qqq_buy_hold'])} |"
        )
    return "\n".join(lines)


def _crisis_table(result: dict[str, Any]) -> str:
    lines = [
        "| 年份 | 候選回報／最大跌幅 | QQQ 回報／最大跌幅 | 候選減 QQQ 回報 |",
        "|---|---:|---:|---:|",
    ]
    for year, paths in result["stresses"]["crisis_years"].items():
        candidate = paths["top7_qqq_overlay"]
        qqq = paths["qqq_buy_hold"]
        lines.append(
            f"| {year} | {_signed_pct(candidate['return'])}／{_pct(candidate['max_drawdown'])} | "
            f"{_signed_pct(qqq['return'])}／{_pct(qqq['max_drawdown'])} | "
            f"{_signed_pct(candidate['return'] - qqq['return'])} |"
        )
    return "\n".join(lines)


def _gate_list(result: dict[str, Any]) -> str:
    return "\n".join(
        f"- {row['label']}：**{'通過' if row['passed'] else '未通過'}**"
        for row in result["gates"]
    )


def _control_list(result: dict[str, Any]) -> str:
    return "\n".join(
        f"- {row['id']} · {row['label']}：{'通過' if row['passed'] else '未通過'}"
        for row in result["controls"]
    )


def _attack_table(result: dict[str, Any]) -> str:
    lines = ["| 攻擊 | 單欄變異 | 預期錯誤碼 | 結果 |", "|---|---|---|---|"]
    for row in result["attacks"]:
        lines.append(
            f"| {row['id']} | {row['label']} | `{row['expected_error_code']}` | "
            f"{'拒收' if row['rejected'] else '誤收'} |"
        )
    return "\n".join(lines)


def _report(result: dict[str, Any]) -> str:
    candidate = result["paths"]["top7_qqq_overlay"]
    qqq = result["paths"]["qqq_buy_hold"]
    qqq_comparison = next(
        row
        for row in result["family"]["comparisons"]
        if row["baseline_id"] == "qqq_buy_hold"
    )
    complete_comparison = next(
        row
        for row in result["family"]["comparisons"]
        if row["baseline_id"] == "complete_qqq_overlay"
    )
    years = result["stresses"]["best_three_years_removed"]
    event_tail = result["stresses"]["favorable_46_events_removed"]
    failed_gates = [row["label"] for row in result["gates"] if not row["passed"]]
    return f"""# 美股短線第 30 輪：QQQ 全投資替換式疊加研究報告

生成日期：{result["generated_on"]}

資料期：{result["input"]["first_signal_date"]} 至 {result["input"]["last_exit_date"]}

研究角色：同一已見 survivor cohort 的全投資反證；不是正式 point-in-time 回測、買入名單、
Paper 或實金指令。

## 結論一覽

第 29 輪候選平均只有 72% 股票持倉。本輪依事前協議把每個閒置槽放入 QQQ，只在原事件
窗口把該 20% 槽位替換成 Top-7；沒有改 Top-K、持有期、訊號、事件或五槽 assignment。
主要成本為每資產 20 bp round trip，即正常替換事件四腿合計名義 40 bp。

20 bp 下，候選由 **US$1,000** 增至 **{_money(candidate['terminal_usd'])}**，CAGR
**{_pct(candidate['cagr'])}**；QQQ 買入並持有為 **{_money(qqq['terminal_usd'])}**、
**{_pct(qqq['cagr'])}**。這是第一個在相同已見日曆內，headline 終值高於 QQQ 的完整資金
路徑，但仍然 **不升格**：

- 候選相對 QQQ 的 NW t 只有 **{qqq_comparison['newey_west']['t_stat']:.2f}**，Holm／共同
  max-t p 為 **{qqq_comparison['holm_adjusted_p']:.4f}／{qqq_comparison['bootstrap_max_t_p']:.4f}**；
- 6,221 次全專案 Bonferroni p 為 **{qqq_comparison['global_bonferroni_p']:.4f}**；
- 相對 complete overlay 的 NW t 只有 **{complete_comparison['newey_west']['t_stat']:.2f}**；
- 移除相對 QQQ 最佳三年 {', '.join(map(str, years['removed_years']))} 後，平均差轉負，NW t
  **{years['newey_west']['t_stat']:.2f}**；
- 每資產 50／100 bp 時，候選 CAGR 分別落後 QQQ
  **{_pct(abs(result['stresses']['costs']['50']['candidate_cagr_differences']['qqq_buy_hold']))}／
  {_pct(abs(result['stresses']['costs']['100']['candidate_cagr_differences']['qqq_buy_hold']))}**；
- 移除最有利 46 宗事件後，候選 CAGR 落後 QQQ
  **{_pct(abs(event_tail['candidate_cagr_differences']['qqq_buy_hold']))}**，並落後 complete overlay
  **{_pct(abs(event_tail['candidate_cagr_differences']['complete_qqq_overlay']))}**；
- 二十項事前門檻只過 **{result['gate_summary']['passed']}/{result['gate_summary']['total']}**；
  未通過：{'、'.join(failed_gates)}。

因此 `not_rejected_by_round30=false`、`new_strategy_created=false`。正式就緒仍為
**{result['decision']['formal_readiness']}**、point-in-time **{result['decision']['point_in_time_readiness']}**、
合資格資料包 **0**、正式策略 run **0**。短線 Paper 維持全現金、持倉 **0**；US$1,000
只是歷史尺度示例，實金動作 **US$0**。

## 八條固定資金路徑

{_path_table(result)}

候選由首次可成交日起維持 100% long、零現金及無槓桿；共核算
**{result['calendar_integrity']['candidate_total_transaction_legs']:,}** 個交易腿。QQQ placebo
逐日價值與「相同 QQQ 價格路徑 × 累積成本」的最大誤差只有
`{result['calendar_integrity']['maximum_qqq_placebo_residual']:.3g}`。

headline 高於 QQQ 的幅度只有 **{_signed_pct(candidate['cagr'] - qqq['cagr'])}／年**，而候選
年率化換手為 **{candidate['annual_turnover']:.1f} 倍**；成本與年份集中足以改變結論。

## 七基準共同統計 family

{_family_table(result)}

七項比較共用 Newey–West lag 20、63-session circular blocks、20,000 條共同 bootstrap
路徑及 seed 30,202,608。候選對 eligible overlay 的局部結果較強，但完整股池、QQQ、固定
半期及全研究多重搜尋沒有同時通過；不得只選局部顯著列。

## 成本壓力

{_cost_table(result)}

每資產成本由 20 bp 增至 50 bp 時，headline 已由領先 QQQ轉為落後。這不是微小敏感度：
每個正常事件同時交易 QQQ 與股票籃子，故 50 bp 資產 round trip 代表名義 100 bp 事件
切換成本，100 bp 代表名義 200 bp。回測未另計個人稅項、買賣差價、市場衝擊及碎股限制。

## 時間、事件尾部與危機期

- 移除最佳三年後剩 {years['remaining_sessions']:,} 個 session，候選相對 QQQ 年率化算術差
  {_signed_pct(years['newey_west']['annualized_arithmetic_difference'])}，NW t
  {years['newey_west']['t_stat']:.2f}。
- 移除的 46 宗事件由 {event_tail['first_removed_signal_date']} 至
  {event_tail['last_removed_signal_date']}；規則在結果前固定以 Top-7 相對 QQQ event gross
  difference 排序，三個 overlay 同時移除，沒有只打擊候選。

{_crisis_table(result)}

三個危機期沒有全部同時跑贏 QQQ及守住最大跌幅上限，因此危機門檻未通過。候選是高股票比重
替換策略，不是現金、短債或低風險替代品。

## 二十項事前門檻

{_gate_list(result)}

## 二十九道資料、換倉、統計及決策控制

{_control_list(result)}

29/29 只證明程式遵守已推送協議；不證明未來會盈利。

## 二十九項單欄變異攻擊

{_attack_table(result)}

所有變異均命中指定錯誤碼。任何 protocol、父收據、QQQ 底倉、四腿成本、路徑、統計
family、尾部或 Paper 權限漂移，都會在輸出結果前 fail closed。

## 市場與數據邊界

本資料最後退出日為 **{result['input']['last_exit_date']}**，不是 {result['generated_on']} 即市
行情。股票仍是 2026 現時 survivor cohort，沒有可靠逐期成分、永久 ID、歷史行業、公司
行動、退市及實際退出經濟；候選 headline 的相對優勢不能修復這個主要偏差。

下一個可升級步驟仍是合格 point-in-time／退市數據 20/20，按既有正式預先登記運行一次，
再累積至少 252 個新增 session 及 12 次換倉的前瞻 Paper 門檻。取得前不會依本輪結果調整
Top-K、事件期、QQQ 底倉或成本門檻。

## 可重播檔案

- [第 30 輪事前協議](SHORT_TERM_QQQ_REPLACEMENT_OVERLAY_PROTOCOL.md)
- `artifacts/short_term_qqq_replacement_overlay_validation.json`
- `site/data/short-term-qqq-replacement-overlay.json`
"""


def main() -> None:
    result = run_qqq_replacement_overlay(ROOT)
    result["receipt_float_decimal_places"] = RECEIPT_FLOAT_DECIMAL_PLACES
    result = _canonicalize_floats(result)
    payload = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ARTIFACT.parent.mkdir(parents=True, exist_ok=True)
    SITE_DATA.parent.mkdir(parents=True, exist_ok=True)
    ARTIFACT.write_text(payload, encoding="utf-8")
    SITE_DATA.write_text(payload, encoding="utf-8")
    REPORT.write_text(_report(result), encoding="utf-8")
    print(
        f"wrote {ARTIFACT.relative_to(ROOT)}, {SITE_DATA.relative_to(ROOT)}, "
        f"{REPORT.relative_to(ROOT)}"
    )


if __name__ == "__main__":
    main()
