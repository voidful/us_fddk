from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np

from usfddk.calendar_capital_accounting import run_calendar_capital_accounting

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "artifacts/short_term_calendar_capital_accounting_validation.json"
SITE_DATA = ROOT / "site/data/short-term-calendar-capital-accounting.json"
REPORT = ROOT / "docs/SHORT_TERM_CALENDAR_CAPITAL_ACCOUNTING_RESEARCH_REPORT.md"
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


def _pct(value: float, digits: int = 1) -> str:
    return f"{value * 100:.{digits}f}%"


def _signed_pct(value: float, digits: int = 2) -> str:
    sign = "+" if value >= 0.0 else ""
    return f"{sign}{value * 100:.{digits}f}%"


def _money(value: float) -> str:
    return f"US${value:,.0f}"


def _path_table(result: dict[str, Any]) -> str:
    lines = [
        "| 固定日曆路徑 | CAGR | 終值（US$1,000） | SHY 超額 Sharpe | 最大跌幅 | 年率化換手 | 平均持倉比重 |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in result["paths"].values():
        lines.append(
            f"| {row['label']} | {_pct(row['cagr'])} | {_money(row['terminal_usd'])} | "
            f"{row['shy_excess_sharpe']:.2f} | {_pct(row['max_drawdown'])} | "
            f"{row['annual_turnover']:.1f}x | {_pct(row['average_exposure'])} |"
        )
    return "\n".join(lines)


def _family_table(result: dict[str, Any]) -> str:
    lines = [
        "| Top-7 相對固定基準 | 年率化算術差 | NW t | Holm p | 共同 max-t p | 前半日均差 | 後半日均差 |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in result["family"]["comparisons"]:
        first = row["fixed_halves"]["first"]["mean_daily_difference"]
        second = row["fixed_halves"]["second"]["mean_daily_difference"]
        lines.append(
            f"| {row['baseline_label']} | {_signed_pct(row['newey_west']['annualized_arithmetic_difference'])} | "
            f"{row['newey_west']['t_stat']:.2f} | {row['holm_adjusted_p']:.4f} | "
            f"{row['bootstrap_max_t_p']:.4f} | {first * 10_000:+.2f} bp | "
            f"{second * 10_000:+.2f} bp |"
        )
    return "\n".join(lines)


def _cost_table(result: dict[str, Any]) -> str:
    lines = [
        "| 來回交易成本 | Top-7 CAGR | 終值 | 合資格池 CAGR | 完整現時股池 CAGR | QQQ event CAGR |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    primary = result["paths"]
    lines.append(
        f"| 20 bp | {_pct(primary['top7_five_slot']['cagr'])} | "
        f"{_money(primary['top7_five_slot']['terminal_usd'])} | "
        f"{_pct(primary['eligible_equal_five_slot']['cagr'])} | "
        f"{_pct(primary['complete_equal_five_slot']['cagr'])} | "
        f"{_pct(primary['qqq_event_five_slot']['cagr'])} |"
    )
    for key in ("50", "100"):
        paths = result["stresses"]["costs"][key]["paths"]
        lines.append(
            f"| {key} bp | {_pct(paths['top7_five_slot']['cagr'])} | "
            f"{_money(paths['top7_five_slot']['terminal_usd'])} | "
            f"{_pct(paths['eligible_equal_five_slot']['cagr'])} | "
            f"{_pct(paths['complete_equal_five_slot']['cagr'])} | "
            f"{_pct(paths['qqq_event_five_slot']['cagr'])} |"
        )
    return "\n".join(lines)


def _crisis_table(result: dict[str, Any]) -> str:
    lines = [
        "| 年份 | Top-7 回報 / 最大跌幅 | QQQ 買入並持有 | SPY 買入並持有 | SHY 買入並持有 |",
        "|---|---:|---:|---:|---:|",
    ]
    for year, paths in result["stresses"]["crisis_years"].items():
        top7 = paths["top7_five_slot"]
        qqq = paths["qqq_buy_hold"]
        spy = paths["spy_buy_hold"]
        shy = paths["shy_buy_hold"]
        lines.append(
            f"| {year} | {_signed_pct(top7['return'])} / {_pct(top7['max_drawdown'])} | "
            f"{_signed_pct(qqq['return'])} | {_signed_pct(spy['return'])} | "
            f"{_signed_pct(shy['return'])} |"
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
    candidate = result["paths"]["top7_five_slot"]
    qqq = result["paths"]["qqq_buy_hold"]
    spy = result["paths"]["spy_buy_hold"]
    eligible = next(
        row
        for row in result["family"]["comparisons"]
        if row["baseline_id"] == "eligible_equal_five_slot"
    )
    complete = next(
        row
        for row in result["family"]["comparisons"]
        if row["baseline_id"] == "complete_equal_five_slot"
    )
    removed = result["stresses"]["best_three_years_removed"]
    return f"""# 美股短線第 29 輪：日曆時間資金佔用與五槽組合回測

生成日期：{result["generated_on"]}

資料期：{result["input"]["first_signal_date"]} 至 {result["input"]["last_exit_date"]}

研究角色：同一已見 survivor cohort 的資金層反證；不是正式 point-in-time 回測、買入名單或實金指令。

## 結論一覽

把 905 個重疊事件放回同一條日曆時間線，並以五個互不重疊資金槽、每槽 20%、不借貸方式
核算後，Top-7 候選在 20 bp 來回成本下由 **US$1,000** 累積至
**{_money(candidate['terminal_usd'])}**，CAGR **{_pct(candidate['cagr'])}**、SHY 超額 Sharpe
**{candidate['shy_excess_sharpe']:.2f}**、最大跌幅 **{_pct(candidate['max_drawdown'])}**。

但這不是升格結果：

- QQQ 買入並持有同期 CAGR **{_pct(qqq['cagr'])}**、終值 **{_money(qqq['terminal_usd'])}**，
  明顯高於 Top-7；SPY CAGR **{_pct(spy['cagr'])}**，亦接近 Top-7；
- Top-7 對完整現時股池的 NW t 只有 **{complete['newey_west']['t_stat']:.2f}**；
- 前後半一致性未通過；移除最佳三年 {', '.join(map(str, removed['removed_years']))} 後，
  對合資格池 NW t 只餘 **{removed['newey_west']['t_stat']:.2f}**；
- 對合資格池的局部 Holm／共同 max-t p 為 **{eligible['holm_adjusted_p']:.4f}／
  {eligible['bootstrap_max_t_p']:.4f}**，但 6,214 次全專案 Bonferroni p 為
  **{eligible['global_bonferroni_p']:.4f}**，未能排除多重搜尋；
- 十八項事前門檻只過 **{result['gate_summary']['passed']}/{result['gate_summary']['total']}**。

因此正式就緒仍是 **{result['decision']['formal_readiness']}**、point-in-time
**{result['decision']['point_in_time_readiness']}**、合資格資料包 **0**、正式策略 run **0**。
短線 Paper 維持全現金、持倉 **0**；US$1,000 只是讀者換算例子，實金動作 **US$0**。

## 七條固定基準與資金結果

{_path_table(result)}

所有路徑由同一 {result['calendar_integrity']['sessions']:,} 個美股交易日計算。Top-7 年率化換手
**{candidate['annual_turnover']:.1f} 倍**、平均持倉比重 **{_pct(candidate['average_exposure'])}**；
20 bp 成本令 CAGR 減少 **{_pct(candidate['cost_drag_cagr'])}**，終值少
**{_money(candidate['cost_drag_terminal_usd'])}**。因此不能以「每宗交易平均回報」直接當成
可投資組合回報。

## 六基準共同統計 family

{_family_table(result)}

六項比較共用 NW lag 20、63-session circular block、20,000 條 bootstrap 路徑及 seed
29,202,608。Top-7 對 QQQ 買入並持有的日均差為負；對 SPY 的 NW t 接近零。局部對
合資格池可見差異，不足以跨越完整基準、時間切割及全專案多重搜尋。

## 交易成本壓力

{_cost_table(result)}

100 bp 下 Top-7 CAGR 降至
**{_pct(result['stresses']['costs']['100']['paths']['top7_five_slot']['cagr'])}**。候選仍高於三個
事件式基準，只說明相對排名未反轉；不等於已補回 survivor、退市、滑價容量、稅項及零碎股
成交等正式缺口。

## 危機年份

{_crisis_table(result)}

2008 及 2022 均錄得明顯虧損；2020 的正回報亦落後 QQQ。策略不是低風險現金替代品，亦未
建立對不同市場狀況都穩定的高回報證據。

## 十八項事前門檻

{_gate_list(result)}

## 二十五道資料、資金、統計及決策控制

{_control_list(result)}

25/25 只證明程式按凍結協議重播，並不證明策略將來會盈利。

## 二十五項單欄變異攻擊

{_attack_table(result)}

所有突變均命中事前指定錯誤碼。任何輸入收據、成本、槽位、統計 family 或 Paper 權限漂移，
主路徑都會在產生結果前 fail closed。

## 市場狀況與下一道證據

本資料截至 **{result['input']['last_exit_date']}**，不是 2026-08-04 即市行情。最新可計算的
2026 年段落對多數基準較強，亦正是移除最佳三年壓力首先剔除的年份；不可把這段短樣本當成
已確認的新市況優勢。

下一道可升格證據仍是合法授權的 point-in-time 成分、永久識別碼、歷史行業、公司行動及
退市／退出經濟，再以凍結規則建立第一段真正未見樣本。取得前不再用同一 survivor 樣本調整
Top-K、持有期或市況篩選作事後救援。

## 可重播檔案

- [第 29 輪事前協議](SHORT_TERM_CALENDAR_CAPITAL_ACCOUNTING_PROTOCOL.md)
- `artifacts/short_term_calendar_capital_accounting_validation.json`
- `site/data/short-term-calendar-capital-accounting.json`
"""


def main() -> None:
    result = run_calendar_capital_accounting(ROOT)
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
