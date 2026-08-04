from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from usfddk.correlation_crowding import run_correlation_crowding

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "artifacts/short_term_correlation_crowding_validation.json"
SITE_DATA = ROOT / "site/data/short-term-correlation-crowding.json"
REPORT = ROOT / "docs/SHORT_TERM_CORRELATION_CROWDING_RESEARCH_REPORT.md"
RECEIPT_FLOAT_DECIMAL_PLACES = 12


def _canonicalize_floats(value: Any) -> Any:
    if isinstance(value, float):
        return round(value, RECEIPT_FLOAT_DECIMAL_PLACES)
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
        "| 固定壓力路徑 | 平均配對差 | NW t | 普通 p | Holm p | 共同 max-t p |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for row in result["family"]["comparisons"]:
        lines.append(
            f"| {row['label']} | {_pp(row['mean_difference'])} | "
            f"{row['newey_west']['t_stat']:.2f} | {row['raw_normal_p']:.4f} | "
            f"{row['holm_adjusted_p']:.4f} | {row['bootstrap_max_t_p']:.4f} |"
        )
    return "\n".join(lines)


def _contributor_table(result: dict[str, Any]) -> str:
    lines = [
        "| 淨貢獻排名 | 2026 現時代號 | 選中次數 | Slot share | 對平均主動差貢獻 | 淨差 share |",
        "|---:|---|---:|---:|---:|---:|",
    ]
    for row in result["current_symbol_contributors"]:
        lines.append(
            f"| {row['net_contribution_rank']} | {row['symbol']} | "
            f"{row['selection_count']} | {_pct(row['selection_slot_share'])} | "
            f"{_pp(row['active_contribution_to_mean'])} | "
            f"{_pct(row['share_of_net_active_sum'])} |"
        )
    return "\n".join(lines)


def _selection_table(result: dict[str, Any]) -> str:
    lines = [
        "| 選中次數排名 | 2026 現時代號 | 選中次數 | Slot share |",
        "|---:|---|---:|---:|",
    ]
    for index, row in enumerate(
        result["symbol_selection_concentration"]["slot_share_ranked"], start=1
    ):
        lines.append(
            f"| {index} | {row['symbol']} | {row['selection_count']} | "
            f"{_pct(row['selection_slot_share'])} |"
        )
    return "\n".join(lines)


def _leave_one_table(result: dict[str, Any]) -> str:
    lines = [
        "| 由弱至強 | 移除的 2026 現時代號 | 平均配對差 | NW t | 最低持倉 | 完整 Top-7 事件 |",
        "|---:|---|---:|---:|---:|---:|",
    ]
    for index, row in enumerate(
        result["leave_one_symbol_out"]["rows_sorted_weakest_first"], start=1
    ):
        exposure = row["matched_cash_exposure"]
        lines.append(
            f"| {index} | {row['symbol']} | {_pp(row['mean_difference'])} | "
            f"{row['newey_west']['t_stat']:.2f} | "
            f"{_pct(exposure['minimum_equity_exposure'])} | "
            f"{_pct(exposure['full_top7_fraction'])} |"
        )
    return "\n".join(lines)


def _report(result: dict[str, Any]) -> str:
    crowding = result["original_crowding"]
    effective = crowding["effective_bets"]
    high_pairs = crowding["high_correlation_pairs"]
    max_corr = crowding["maximum_pairwise_correlation"]
    concentration = result["symbol_selection_concentration"]
    family = {row["id"]: row for row in result["family"]["comparisons"]}
    remove_one = family["remove_top1_contributor"]
    remove_three = family["remove_top3_contributors"]
    cap_family = family["correlation_cap2_stress"]
    cap = result["correlation_cap2_stress"]
    cap_count = cap["accepted_count"]
    cap_change = cap["crowding_change"]
    contributors = result["top_contributor_symbols_ex_post_not_a_buy_list"]
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
    return f"""# 美股短線第 25 輪：相關性擁擠與現時代號依賴報告

研究日期：2026-08-04

狀態：survivor cohort 非獨立反證；不可投資；短線 Paper 全現金；實金動作 US$0

## 一頁結論

名義 Top-7 的中位有效獨立注數只有 **{effective["median"]:.2f}**，平均
**{effective["mean"]:.2f}**；**{_pct(effective["fraction_below_3"])}** 的 905 個事件低於
3 注。**{_pct(high_pairs["events_with_any_fraction"])}** 事件至少有一對 60 日相關高於
0.70；每事件最高 pairwise correlation 的中位數為 **{max_corr["median"]:.3f}**。

選中次數本身沒有被單一代號壟斷：最高單一 slot share **{_pct(concentration["maximum_single_symbol_slot_share"])}**，
最高三個合計 **{_pct(concentration["top3_symbol_slot_share"])}**，均通過事前門檻。但按對
`Top-7 - eligible equal` 的事後淨貢獻排序，最高三個 2026 現時代號為
**{", ".join(contributors)}**。這只是歷史歸因，不是買入名單。

刪除最高一個淨貢獻代號後，平均配對差仍為 **{_pp(remove_one["mean_difference"])}**、
NW t **{remove_one["newey_west"]["t_stat"]:.2f}**；刪除最高三個後只餘
**{_pp(remove_three["mean_difference"])}**、NW t **{remove_three["newey_west"]["t_stat"]:.2f}**，
Holm p **{remove_three["holm_adjusted_p"]:.4f}**、共同 max-t p
**{remove_three["bootstrap_max_t_p"]:.4f}**，統計門檻失敗。

固定相關 cap-2／不回補壓力保留 **{_pct(cap_count["mean_equity_exposure"])}** 平均股票持倉，
相對 matched eligible 仍有 **{_pp(cap_family["mean_difference"])}**、NW t
**{cap_family["newey_west"]["t_stat"]:.2f}**。但平均相關只降低
**{cap_change["mean_pairwise_correlation_reduction"]:.3f}**，遠低於事前 0.05；它沒有充分
解決擁擠，也不會因回報差仍為正而變成新策略。

十二項反證只通過 **{result["gate_summary"]["passed"]}/{result["gate_summary"]["total"]}**。
正式就緒仍為 **1/18**、正式策略運行 **0 次**、Paper 持倉 **0**、實金動作 **US$0**。

## 首次停止與非獨立 schema repair

父協議先以 commit `00faaa5ed04bccb8b0d147fb47a9ef3c706f3d44` 凍結；首次運行在
刪除主要現時代號後遇到合資格股份不足 7 隻，以
`crowding_baseline_fairness_breached` 停止，沒有寫出結果。

其後以 commit `c48de060cbc501f04e73fa9977d040eff8fc097d` 先凍結唯一修補：不足
7 隻時，每隻仍佔 1/7，餘額留零回報現金，candidate 與 eligible baseline 使用完全相同
股票持倉比例及成本。其他 12 項門檻沒有改動。本報告因此不是獨立首次未見證據。

## 原 Top-7 擁擠度

| 指標 | 結果 | 事前判讀 |
|---|---:|---|
| 平均 pairwise correlation | {crowding["mean_pairwise_correlation"]["mean"]:.3f} | 60 個事前日回報 |
| 中位 pairwise correlation | {crowding["mean_pairwise_correlation"]["median"]:.3f} | 每事件 21 pairs |
| 最高 pair correlation 中位 | {max_corr["median"]:.3f} | 聚落內可接近同一注 |
| 高相關 pair 平均數 | {high_pairs["mean"]:.2f} | 嚴格 `corr > 0.70` |
| 中位有效獨立注數 | {effective["median"]:.2f} / 7 | 未過 3.5 門檻 |
| `N_eff < 3` 事件 | {_pct(effective["fraction_below_3"])} | 未過不多於 25% |

`N_eff` 使用事前固定的 `clip(N/(1+(N-1)×平均相關), 1, N)`。這是風險集中度近似，
不是實際獨立交易數或盈利預測。

## 四假說 family

{_family_table(result)}

四列共用 52-event circular block、20,000 路徑及 seed 25202608。Holm／max-t 只防止在
這四條壓力中挑最好一條，不取代正式 6,208-trial DSR。

## 相關性 cap-2 壓力

- 平均保留 **{cap_count["mean"]:.2f}/7** 隻；最低 {cap_count["minimum"]} 隻；完整 Top-7
  事件 **{_pct(cap_count["full_top7_fraction"])}**；共 {cap_count["rejected_slots"]} 個 slot
  留現金。
- 平均 pairwise correlation：{cap_change["mean_pairwise_correlation_before"]:.3f} →
  {cap_change["mean_pairwise_correlation_after"]:.3f}；只降低
  {cap_change["mean_pairwise_correlation_reduction"]:.3f}。
- 中位有效注數：{cap_change["median_effective_bets_before"]:.2f} →
  {cap_change["median_effective_bets_after"]:.2f}。名義持股減少後，風險獨立性沒有實質改善。
- 對 matched QQQ 的平均配對差為
  **{_pp(cap["vs_matched_qqq"]["mean_difference"])}**、NW t
  **{cap["vs_matched_qqq"]["newey_west"]["t_stat"]:.2f}**；仍屬有偏差事件診斷。

## 2026 現時代號事後貢獻

{_contributor_table(result)}

淨貢獻可以為負，share 亦可低於 0 或高於 100%；所有列合計恰等於原平均配對差。Ticker
不是永久證券／公司 ID，不能據此推斷改名、收購或退市 lineage。

### 選中頻率

{_selection_table(result)}

### 25 條 leave-one-symbol-out

{_leave_one_table(result)}

25 條平均差全部為正，最低 NW t 為
**{result["leave_one_symbol_out"]["minimum_newey_west_t"]:.2f}**；這只表示沒有任何單一現時
代號能獨自推翻訊號。最高三個淨貢獻代號合併移除後失敗，顯示組合依賴而非單一股依賴。

## 十二項事前反證門檻

{gates}

十二項全過也只可寫作「現時 survivor cohort 未被本輪推翻」；本輪實際 7/12。

## 十九道控制

{controls}

## 十九項突變攻擊

{attacks}

## 決策

本輪沒有新增可採用策略、股票名單或落盤指令。結果反對把 Top-7 當成七個獨立押注，
亦顯示 cap-2 這個台股風險規則不能直接移植成有效的美股去擁擠方法。不得事後改用 cap 1、
其他相關門檻、40／80 日窗口、回補、重新配重或刪除其他股份救援。

下一個具升級價值的證據仍是獲授權 point-in-time 成分、永久 ID、歷史行業、公司行動、
退市／收購實收及同步 RF。數據齊全後只准依既有 18/18 事前登記運行一次，再通過 50 bps、
QQQ／SPY／逐期股池／同股漂移、NW／PSR／6,208-trial DSR／PBO，以及 252 個真正新增
交易日／12 次完成月度輪選，才可由全現金開始 Paper。

- [第 25 輪父協議](SHORT_TERM_CORRELATION_CROWDING_PROTOCOL.md)
- [matched-cash schema repair](SHORT_TERM_CORRELATION_CROWDING_SCHEMA_REPAIR_PROTOCOL.md)
- [第 24 輪公平 baseline／多重檢驗](SHORT_TERM_BASELINE_MULTIPLICITY_RESEARCH_REPORT.md)
- [台股 tst_wocker 固定參考 commit](https://github.com/appr1ciat1/tst_wocker/tree/3372aa088328700feafeeb07c72ab832ea2d3ecb)
- [台股 tw-block-warrant 固定參考 commit](https://github.com/appr1ciat1/tw-block-warrant/tree/37463c54796ba36f4aac262519ea7fc2ef797de6)
- [台股 filter lab 固定參考 commit](https://github.com/appr1ciat1/tst_wocker_filter_lab/tree/06c87b7a1735877c9ccbab3a339c1742814a5058)

US$1,000 只作讀者比例示例。歷史及合成結果不保證未來回報；本報告不構成投資建議、
Paper 成交或實金落盤指令。
"""


def main() -> None:
    result = run_correlation_crowding(ROOT)
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
