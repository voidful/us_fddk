from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from usfddk.common_risk_residual import run_common_risk_residual

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "artifacts/short_term_common_risk_residual_validation.json"
SITE_DATA = ROOT / "site/data/short-term-common-risk-residual.json"
REPORT = ROOT / "docs/SHORT_TERM_COMMON_RISK_RESIDUAL_RESEARCH_REPORT.md"
RECEIPT_FLOAT_DECIMAL_PLACES = 12


def _canonicalize_floats(value: Any) -> Any:
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


def _pp(value: float, digits: int = 3) -> str:
    sign = "+" if value >= 0 else ""
    return f"{sign}{value * 100:.{digits}f} 個百分點"


def _family_table(result: dict[str, Any]) -> str:
    lines = [
        "| 固定模型／baseline | 事件 | 平均配對差 | NW t | 普通 p | Holm p | 共同 max-t p | 前半 | 後半 |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in result["family"]["comparisons"]:
        lines.append(
            f"| {row['label']} | {row['events']} | {_pp(row['mean_difference'])} | "
            f"{row['newey_west']['t_stat']:.2f} | {row['raw_normal_p']:.4f} | "
            f"{row['holm_adjusted_p']:.4f} | {row['bootstrap_max_t_p']:.4f} | "
            f"{_pp(row['fixed_halves']['first']['mean_difference'])} | "
            f"{_pp(row['fixed_halves']['second']['mean_difference'])} |"
        )
    return "\n".join(lines)


def _beta_gap_table(result: dict[str, Any]) -> str:
    lines = [
        "| 模型／baseline | 平均 beta gap | 絕對 gap 中位 | 絕對 gap 95th | beta gap 為正 | beta 貢獻平均 | 佔 raw 平均 |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in result["beta_gap_summaries"]:
        share = row["beta_contribution_share_of_raw_mean"]
        lines.append(
            f"| {row['id']} | {row['mean_beta_gap']:.3f} | "
            f"{row['median_absolute_beta_gap']:.3f} | {row['p95_absolute_beta_gap']:.3f} | "
            f"{_pct(row['positive_beta_gap_fraction'])} | "
            f"{_pp(row['mean_beta_contribution'])} | "
            f"{_pct(share) if share is not None else '不適用'} |"
        )
    return "\n".join(lines)


def _sector_table(result: dict[str, Any]) -> str:
    counts = result["current_sector_label_diagnostic"]["selection_slots_by_current_sector"]
    total = sum(counts.values())
    lines = [
        "| 2026 現時行業標籤 | 選中 slots | Slot share |",
        "|---|---:|---:|",
    ]
    for sector, count in sorted(counts.items(), key=lambda item: (-item[1], item[0])):
        lines.append(f"| {sector} | {count} | {_pct(count / total)} |")
    return "\n".join(lines)


def _report(result: dict[str, Any]) -> str:
    family = {row["id"]: row for row in result["family"]["comparisons"]}
    raw_eligible = family["RAW__eligible"]
    raw_complete = family["RAW__complete_cohort"]
    qqq_eligible = family["QQQ_252__eligible"]
    qqq_complete = family["QQQ_252__complete_cohort"]
    spy_eligible = family["SPY_252__eligible"]
    spy_complete = family["SPY_252__complete_cohort"]
    cohort_eligible = family["COHORT_252__eligible"]
    cohort_complete = family["COHORT_252__complete_cohort"]
    qqq_gap = next(row for row in result["beta_gap_summaries"] if row["id"] == "QQQ_252__eligible")
    regimes = result["primary_stresses"]["qqq_forward_regimes_ex_post_not_a_signal"]
    qqq_up = regimes["qqq_nonnegative"]
    qqq_down = regimes["qqq_negative"]
    tail = result["primary_stresses"]["remove_largest_absolute_beta_contribution"]
    sector = result["current_sector_label_diagnostic"]["summary"]
    gates = "\n".join(
        f"- {row['label']}：**{'通過' if row['passed'] else '未通過'}**" for row in result["gates"]
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
    return f"""# 美股短線第 26 輪：共同市場風險殘差反證報告

研究日期：2026-08-04

狀態：survivor cohort 非獨立反證；不可投資；短線 Paper 全現金；實金動作 US$0

## 一頁結論

第 26 輪沒有調校新策略，只把固定 Top-7 對公平 baseline 的差額分解成訊號日前估算的
共同 beta 貢獻及殘差。原始 905 個事件全部重建無誤；因 MA 在最早 39 個事件前不足
252 個完整日回報，十假說 family 事前 repair 後統一使用 2007-06-01 至 2026-07-02 的
**866 個共同事件**，沒有讓 60 日模型使用較長樣本。

在共同 866 事件中，raw Top-7 對 eligible 等權平均差為
**{_pp(raw_eligible["mean_difference"])}**、NW t **{raw_eligible["newey_west"]["t_stat"]:.2f}**；
但對完整現時股池只餘 **{_pp(raw_complete["mean_difference"])}**、NW t
**{raw_complete["newey_west"]["t_stat"]:.2f}**。以訊號前 252 日 QQQ beta 扣除共同風險後：

- 對 eligible 仍為 **{_pp(qqq_eligible["mean_difference"])}**、NW t
  **{qqq_eligible["newey_west"]["t_stat"]:.2f}**，但十假說 Holm／max-t p 為
  **{qqq_eligible["holm_adjusted_p"]:.4f}／{qqq_eligible["bootstrap_max_t_p"]:.4f}**，均未通過
  固定 0.05；
- 對完整現時股池只有 **{_pp(qqq_complete["mean_difference"])}**、NW t
  **{qqq_complete["newey_west"]["t_stat"]:.2f}**；
- QQQ beta 貢獻平均佔 raw eligible 差額 **{_pct(qqq_gap["beta_contribution_share_of_raw_mean"])}**；
  絕對 beta gap 中位 **{qqq_gap["median_absolute_beta_gap"]:.3f}**、95th
  **{qqq_gap["p95_absolute_beta_gap"]:.3f}**，兩道風險曝險門檻均失敗。

SPY 252 日殘差對 eligible／complete 的 NW t 為
**{spy_eligible["newey_west"]["t_stat"]:.2f}／{spy_complete["newey_west"]["t_stat"]:.2f}**；固定
25 股共同因子殘差只有 **{cohort_eligible["newey_west"]["t_stat"]:.2f}／
{cohort_complete["newey_west"]["t_stat"]:.2f}**。未來 QQQ 上升事件主要殘差 NW t
**{qqq_up["newey_west"]["t_stat"]:.2f}**，下跌事件只有
**{qqq_down["newey_west"]["t_stat"]:.2f}**。十四項事前門檻只過
**{result["gate_summary"]["passed"]}/{result["gate_summary"]["total"]}**，不能把原始正面差額寫成
已通過共同市場風險、公平完整股池及 family-wise 校正的可投資 alpha。

正式就緒仍為 **1/18**、point-in-time **1/20**、正式策略運行 **0 次**、Paper 持倉
**0**、實金動作 **US$0**。

## 首次停止與非獨立 coverage repair

父協議先以 commit `6616064` 凍結。首次執行在第一個缺失 beta cell 以
`common_risk_beta_window_mismatch` 停止，沒有寫出 family、gate、報告或收據。

覆蓋盤點只發現 MA：2006-08-04 至 2007-05-25 共 39 個事件不足 252 日；第一個完整
訊號日為 2007-06-01。其後先以 commit `b781601` 凍結唯一修復：原 905 事件仍完整重建，
但全部十列統一使用 866 個共同事件；父協議其他 14 項 gate、factor、beta 公式、兩個
baseline、成本、前後半、Holm、NW lag 4、共同 bootstrap 及 46-event 壓力全部不改。
本報告因此不是獨立首次未見證據。

| 覆蓋項目 | 固定結果 |
|---|---:|
| 原始重建事件 | {result["input"]["events"]} |
| 十假說共同事件 | {result["input"]["family_common_events"]} |
| 覆蓋排除事件 | {result["input"]["coverage_excluded_events"]} |
| 共同 beta cells | {result["beta_coverage"]["beta_cells"]:,} / {result["beta_coverage"]["expected_beta_cells"]:,} |
| 最大回報重建誤差 | {result["reconstruction"]["maximum_return_residual"]:.3e} |
| 最大 beta 分解誤差 | {result["maximum_decomposition_residual"]:.3e} |

## 十假說共同 family

{_family_table(result)}

十列共用 52-event circular block、20,000 路徑及 seed 26202608。RAW 兩列亦放進同一
family，不能先看 residual 較漂亮才把原始比較刪除。正式 6,208-trial 搜尋壓力沒有重設。

## beta gap 與共同風險貢獻

{_beta_gap_table(result)}

每列逐事件嚴格滿足 `raw active = residual active + beta gap × factor event return`。
beta 只用訊號日或之前的調整收市日回報，不 clipping、不 winsor、不 shrink；未來 factor
回報只用於事後分解，不是訊號。正值比例把絕對值不高於 `1e-12` 的浮點殘差視為零，
並在 JSON 收據把四捨五入後的負零正規化為 `0.0`；這只消除跨平台數值庫差異，不改平均、
t 值、p 值、門檻或決策。

## QQQ 上／下及 beta-contribution 尾部壓力

| 固定反證 | 事件 | 平均主要殘差 | NW t | 判讀 |
|---|---:|---:|---:|---|
| 未來 QQQ 回報非負 | {qqq_up["events"]} | {_pp(qqq_up["mean_difference"])} | {qqq_up["newey_west"]["t_stat"]:.2f} | 事後 regime，不可交易 |
| 未來 QQQ 回報為負 | {qqq_down["events"]} | {_pp(qqq_down["mean_difference"])} | {qqq_down["newey_west"]["t_stat"]:.2f} | 未過 1.96 |
| 移除絕對 beta 貢獻最大 46 列 | {tail["events"]} | {_pp(tail["mean_difference"])} | {tail["newey_west"]["t_stat"]:.2f} | 保留父協議固定 46 列 |

被移除 46 列佔全部絕對 beta contribution **{_pct(tail["removed_absolute_beta_contribution_share"])}**。
尾部壓力通過不能抵銷 QQQ 下跌組、完整股池及十假說 family 的失敗。

## 2026 現時行業標籤診斷

中位唯一行業數 **{sector["median_unique_current_sectors"]:.0f}**，中位有效行業數
**{sector["median_effective_current_sectors"]:.2f}**；**{_pct(sector["events_with_current_sector_majority_fraction"])}**
事件有至少四股被現時標成同一行業，單次最多六股。

{_sector_table(result)}

這些是把 2026 現時行業標籤回填到歷史事件的單向警告，不是 point-in-time 身份、通過
證據或買入名單。

## 十四項事前反證門檻

{gates}

十四項全過亦只可寫作 survivor cohort 未被本輪額外推翻；本輪實際 6/14。

## 二十一道控制

{controls}

## 二十一項突變攻擊

{attacks}

## 決策

本輪保留一個窄結論：對 eligible 的 raw 排名差並非全部由 QQQ beta 解釋；但它的共同
校正 p、完整現時股池、cohort factor 及 QQQ 下跌組均未通過。不得事後改 beta window、
clipping、factor、baseline、樣本起點或壓力列數救援，也不會建立新策略。

下一個具升級價值的證據仍是獲授權 point-in-time 成分、永久 ID、歷史行業、公司行動、
退市／收購實收及同步 RF。數據齊全後只准依既有事前登記原樣運行一次，再通過成本、
QQQ／SPY／逐期股池／同股漂移、NW／PSR／6,208-trial DSR／PBO 及前瞻 Paper 門檻。

- [第 26 輪父協議](SHORT_TERM_COMMON_RISK_RESIDUAL_PROTOCOL.md)
- [beta 覆蓋修復協議](SHORT_TERM_COMMON_RISK_RESIDUAL_COVERAGE_REPAIR_PROTOCOL.md)
- [第 25 輪相關性擁擠報告](SHORT_TERM_CORRELATION_CROWDING_RESEARCH_REPORT.md)
- [台股 tst_wocker 固定參考 commit](https://github.com/appr1ciat1/tst_wocker/tree/3372aa088328700feafeeb07c72ab832ea2d3ecb)
- [台股 tw-block-warrant 固定參考 commit](https://github.com/appr1ciat1/tw-block-warrant/tree/37463c54796ba36f4aac262519ea7fc2ef797de6)
- [台股 filter lab 固定參考 commit](https://github.com/appr1ciat1/tst_wocker_filter_lab/tree/06c87b7a1735877c9ccbab3a339c1742814a5058)

US$1,000 只作讀者比例示例。歷史及合成結果不保證未來回報；本報告不構成投資建議、
Paper 成交或實金落盤指令。
"""


def main() -> None:
    result = run_common_risk_residual(ROOT)
    result["receipt_float_decimal_places"] = RECEIPT_FLOAT_DECIMAL_PLACES
    result = _canonicalize_floats(result)
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
