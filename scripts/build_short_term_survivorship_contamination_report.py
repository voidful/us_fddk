from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from usfddk.survivorship_contamination import (
    PRIMARY_CONTAMINATION_RATE,
    PRIMARY_EXIT_RETURN,
    run_survivorship_contamination_stress,
)

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "artifacts/short_term_survivorship_contamination_validation.json"
SITE_DATA = ROOT / "site/data/short-term-survivorship-contamination.json"
REPORT = ROOT / "docs/SHORT_TERM_SURVIVORSHIP_CONTAMINATION_RESEARCH_REPORT.md"


def _pct(value: float, digits: int = 2) -> str:
    return f"{value * 100:.{digits}f}%"


def _pp(value: float, digits: int = 3) -> str:
    sign = "+" if value >= 0 else ""
    return f"{sign}{value * 100:.{digits}f} 個百分點"


def _grid_table(result: dict[str, Any]) -> str:
    lines = [
        "| 退出回報 | 污染率 | 期望配對差 | NW t | MC 95% 區間 | 正平均路徑 | 前後十年同正 |",
        "|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in result["stress_grid"]:
        expected = row["expected"]
        monte_carlo = row["monte_carlo"]
        quantiles = monte_carlo["mean_difference_quantiles"]
        lines.append(
            "| {exit_return} | {rate} | {mean} | {t:.2f} | {low} 至 {high} | "
            "{positive} | {halves} |".format(
                exit_return=_pct(row["exit_return"], 0),
                rate=_pct(row["contamination_rate"], 1),
                mean=_pp(expected["mean_difference"]),
                t=expected["newey_west"]["t_stat"],
                low=_pp(quantiles["p025"]),
                high=_pp(quantiles["p975"]),
                positive=_pct(monte_carlo["positive_mean_fraction"], 1),
                halves=_pct(monte_carlo["both_halves_positive_fraction"], 1),
            )
        )
    return "\n".join(lines)


def _break_even_table(result: dict[str, Any]) -> str:
    lines = [
        "| 退出回報 | 平均差降至零 | NW t 跌穿 1.96 |",
        "|---:|---:|---:|",
    ]
    for row in result["break_even_by_exit_return"]:
        mean_rate = row["mean_zero_contamination_rate"]
        nw_rate = row["newey_west_below_1_96_contamination_rate"]
        lines.append(
            f"| {_pct(row['exit_return'], 0)} | "
            f"{_pct(mean_rate, 2) if mean_rate is not None else '未於 0–100% 出現'} | "
            f"{_pct(nw_rate, 2) if nw_rate is not None else '未於 0–100% 出現'} |"
        )
    return "\n".join(lines)


def _report(result: dict[str, Any]) -> str:
    observed = result["observed_signal"]
    primary = result["primary_cell"]
    expected = primary["expected"]
    monte_carlo = primary["monte_carlo"]
    primary_gates = "\n".join(
        f"- {row['label']}：**{'通過' if row['passed'] else '未通過'}**"
        for row in result["primary_gates"]
    )
    controls = "\n".join(
        f"- {row['id']}｜{row['label']}：**{'通過' if row['passed'] else '未通過'}**"
        for row in result["controls"]
    )
    attacks = "\n".join(
        f"- {row['id']}｜{row['label']}：**{'拒收' if row['rejected'] else '誤收'}** "
        f"`{row['expected_error_code']}`"
        for row in result["attacks"]
    )
    grid_table = _grid_table(result)
    break_even_table = _break_even_table(result)
    severe_80 = next(
        row
        for row in result["stress_grid"]
        if row["exit_return"] == -0.80
        and row["contamination_rate"] == PRIMARY_CONTAMINATION_RATE
    )
    severe_100 = next(
        row
        for row in result["stress_grid"]
        if row["exit_return"] == -1.00
        and row["contamination_rate"] == PRIMARY_CONTAMINATION_RATE
    )
    return f"""# 美股短線第 22 輪：存活者偏差／缺失退出污染壓力報告

研究日期：2026-08-04

狀態：合成壓力測試；不可投資；短線 Paper 全現金；實金動作 US$0

## 一頁結論

固定主要格（每個 20 日事件有 **{_pct(PRIMARY_CONTAMINATION_RATE, 0)}** 機會漏掉一隻
本來會入選 Top-7、該股份退出回報 **{_pct(PRIMARY_EXIT_RETURN, 0)}**）在五項事前門檻
**{result['primary_gate_summary']['passed']}/{result['primary_gate_summary']['total']} 通過**。
觀察配對差由 **{_pp(observed['mean_active_difference'])}** 降至
**{_pp(expected['mean_difference'])}**，Newey–West t 由
**{observed['newey_west']['t_stat']:.2f}** 降至 **{expected['newey_west']['t_stat']:.2f}**；
2,000 條固定亂數路徑的平均差 95% 區間為
**{_pp(monte_carlo['mean_difference_quantiles']['p025'])} 至
{_pp(monte_carlo['mean_difference_quantiles']['p975'])}**。

這不是正式成功。相同 2% 污染率下，退出回報 -80% 時 NW t 只有
**{severe_80['expected']['newey_west']['t_stat']:.2f}**，-100% 時只有
**{severe_100['expected']['newey_west']['t_stat']:.2f}**，均跌穿 1.96。換言之，訊號並非被
輕微壓力立即推翻，但對少量嚴重退出事件仍敏感；真實污染率與退出分布未知，不能由這個
合成結果推算盈利能力。

十二道協議控制 **{result['control_summary']['passed']}/{result['control_summary']['total']}**
通過、十二項突變攻擊 **{result['attack_summary']['rejected']}/{result['attack_summary']['total']}**
全部拒收。正式就緒仍為 **1/18**、正式逐股策略運行 **0 次**、Paper 持倉 **0**、
實金動作 **US$0**。

## 為何做這個測試

現有 905 個 20 日事件只包含 2026 年仍存在的現時大型股，觀察 Top-7 平均淨回報
{_pct(observed['mean_selected_return'])}，同日合資格池等權 {_pct(observed['mean_eligible_equal_return'])}，
配對差 {_pp(observed['mean_active_difference'])}。這條線索在原診斷表面通過，但完整每週
組合低於 QQQ、行業 ETF 外部產品驗證失敗，同股池漂移亦勝過月度綜合輪選。

本輪沒有再搜尋 Top-K、持有期、止賺、止蝕或市場環境，只量化「被漏掉的失敗股份若
集中進入選股籃子」會怎樣。候選以 1/7 承受同一缺失股份，公平基準亦以
`1/(N+1)` 納入，避免只打擊候選而不修正 baseline。

## 固定主要格

- 退出回報：{_pct(PRIMARY_EXIT_RETURN, 0)}；污染率：{_pct(PRIMARY_CONTAMINATION_RATE, 0)}。
- 期望配對差：{_pp(expected['mean_difference'])}；中位差：{_pp(expected['median_difference'])}。
- NW t：{expected['newey_west']['t_stat']:.2f}；配對勝率：{_pct(expected['win_fraction'], 1)}。
- 前／後十年期望差：{_pp(expected['fixed_halves']['first_mean_difference'])}／
  {_pp(expected['fixed_halves']['second_mean_difference'])}。
- Monte Carlo 正平均路徑：{_pct(monte_carlo['positive_mean_fraction'], 1)}；前後十年同正：
  {_pct(monte_carlo['both_halves_positive_fraction'], 1)}。

### 五項事前門檻

{primary_gates}

「5/5」只可讀作這個合成主要格未推翻訊號；它不能把存活者偏差標成已修復。

## 完整 20 格

{grid_table}

MC 區間是污染位置的模型不確定性，不是市場回報信賴區間；重疊 20 日事件亦不能把
每格的事件差直接當作可複利 CAGR。

## Break-even 脆弱度

{break_even_table}

以 -50% 退出回報計，平均差約在污染率 **7.70%** 才降至零，但 NW t 約在
**2.76%** 已跌穿 1.96；若退出回報是 -100%，兩個界線降至約 **3.92%** 及 **1.40%**。
統計證據會先於平均值消失，因此不能只看配對差仍為正。

## Schema repair 完整披露

父協議在首次運行時把最後訊號日手寫錯誤；程式於載入階段以
`stress_event_order_mismatch` 停止，未產生任何壓力結果。其後先提交
[日期邊界 repair 附錄](SHORT_TERM_SURVIVORSHIP_CONTAMINATION_SCHEMA_REPAIR_PROTOCOL.md)，
只准首末日期由已綁定 SHA 的 905 列直接讀取。實際固定事件為
{observed['first_signal_date']} 至 {observed['last_signal_date']}；所有壓力格、統計及門檻不變。

## 十二道控制

{controls}

## 十二項突變攻擊

{attacks}

## 決策

這輪保留 20 日橫斷面排序作為「值得在合格數據原樣重測」的研究線索，但沒有改善正式
資料就緒分數。下一個可升級證據仍只能是獲授權的 point-in-time 成分、永久 ID、歷史
行業、公司行動、退市／收購實收、移除後價格路徑及同步 QQQ／SPY／XNYS／精確 RF。

收到完整 package 後仍須依 18/18 正式閘門只運行一次凍結回測，再通過成本、QQQ／SPY／
逐期股池 baseline、NW、DSR、PBO 及真正新增 252 個交易日／12 次月度輪選，才可由全現金
開始 Paper。US$1,000 只是讀者比例示例，不是持倉建議。

- [事前壓力協議](SHORT_TERM_SURVIVORSHIP_CONTAMINATION_PROTOCOL.md)
- [日期邊界 repair 協議](SHORT_TERM_SURVIVORSHIP_CONTAMINATION_SCHEMA_REPAIR_PROTOCOL.md)
- [原 20 日訊號研究](SHORT_TERM_HIGH_RETURN_RESEARCH_REPORT.md)

歷史及合成結果不保證未來回報；本報告不構成投資建議、Paper 成交或實金落盤指令。
"""


def main() -> None:
    result = run_survivorship_contamination_stress(ROOT)
    rendered = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ARTIFACT.write_text(rendered, encoding="utf-8")
    SITE_DATA.write_text(rendered, encoding="utf-8")
    REPORT.write_text(_report(result), encoding="utf-8")
    print(
        f"wrote {ARTIFACT.relative_to(ROOT)}, {SITE_DATA.relative_to(ROOT)}, "
        f"{REPORT.relative_to(ROOT)}"
    )


if __name__ == "__main__":
    main()
