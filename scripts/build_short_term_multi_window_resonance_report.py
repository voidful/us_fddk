from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np

from usfddk.multi_window_resonance import run_multi_window_resonance

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "artifacts/short_term_multi_window_resonance_validation.json"
SITE_DATA = ROOT / "site/data/short-term-multi-window-resonance.json"
REPORT = ROOT / "docs/SHORT_TERM_MULTI_WINDOW_RESONANCE_RESEARCH_REPORT.md"
RECEIPT_FLOAT_DECIMAL_PLACES = 12


GATE_LABELS = {
    "exact_inputs": "協議、父收據、行情、觀察名單及參考 commit 精確",
    "parent_event_reconstruction": "第 29／30 輪 905 宗事件及 assignment 逐列重播",
    "slot_clock": "五槽各 181 宗事件、無重疊及最大 concurrency 五個",
    "resonance_ranking": "四窗 Top-7、共振次數、rank-sum 及最多七股精確",
    "partial_allocations": "候選與 matched 路徑的 N/7 股票比例及 QQQ 餘額精確",
    "daily_identities": "九路每日資產、driver、成本、現金及無槓桿 identity",
    "parent_and_placebo_identities": "原 Top-7 父路徑及部分 QQQ 換手 placebo 逐日一致",
    "candidate_cagr_vs_qqq": "候選 CAGR 高於 QQQ 買入並持有",
    "candidate_terminal_vs_qqq": "候選 US$1,000 期末值高於 QQQ",
    "candidate_sharpe_vs_qqq": "候選 SHY 超額 Sharpe 高於 QQQ",
    "candidate_drawdown_vs_qqq": "候選最大跌幅不比 QQQ 深超過 5 個百分點",
    "candidate_cagr_vs_original": "候選 CAGR 高於原第 30 輪 Top-7 疊加",
    "candidate_cagr_vs_matched20": "候選 CAGR 高於相同比例 20 日動量路徑",
    "candidate_cagr_vs_equal_baselines": "候選 CAGR 同時高於 eligible 及 complete matched 路徑",
    "statistical_vs_qqq": "相對 QQQ 的日均差、NW、Holm 及共同 max-t 全部通過",
    "statistical_vs_matched": "相對三條 matched 路徑的 NW、Holm 及共同 max-t 全部通過",
    "fixed_halves": "五個核心比較的固定前後半日均差全正",
    "best_three_years_removed": "移除相對 QQQ 最佳三年後仍為正且 NW t 不低於 1.96",
    "crisis_and_regimes": "2008／2020／2022 及兩個事前 QQQ 市況組全部通過",
    "global_cost_and_tail": "6,229 trials、50／100 bp及移除 46 宗事件全部通過",
}


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
        "| 固定路徑 | CAGR | US$1,000 終值 | SHY 超額 Sharpe | 最大跌幅 | 年率化換手 | 平均股票比例 | 成本拖累 |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in result["paths"].values():
        lines.append(
            f"| {row['label']} | {_pct(row['cagr'])} | {_money(row['terminal_usd'])} | "
            f"{row['shy_excess_sharpe']:.2f} | {_pct(row['max_drawdown'])} | "
            f"{row['annual_turnover']:.1f}x | {_pct(row['average_stock_driver_fraction'], 1)} | "
            f"{_signed_pct(-row['cost_drag_cagr'])} |"
        )
    return "\n".join(lines)


def _selection_table(result: dict[str, Any]) -> str:
    lines = ["| 每宗候選數 N | 事件數 | 股票目標比例 |", "|---:|---:|---:|"]
    for row in result["selection_distribution"]["candidate_count_histogram"]:
        lines.append(
            f"| {row['candidate_count']} | {row['events']} | "
            f"{_pct(row['candidate_count'] / 7, 1)} |"
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
            f"| {row['baseline_label']} | {_signed_pct(row['annualized_arithmetic_difference'])} | "
            f"{row['newey_west']['t_stat']:.2f} | {row['holm_adjusted_p']:.4f} | "
            f"{row['bootstrap_max_t_p']:.4f} | {row['global_bonferroni_p']:.4f} | "
            f"{first:+.2f}／{second:+.2f} bp |"
        )
    return "\n".join(lines)


def _cost_table(result: dict[str, Any]) -> str:
    baseline_ids = (
        "qqq_buy_hold",
        "original_top7_qqq_overlay",
        "matched_20d_qqq_overlay",
        "matched_eligible_qqq_overlay",
        "matched_complete_qqq_overlay",
    )
    lines = [
        "| 每資產來回成本 | 候選 CAGR | 候選減 QQQ | 候選減原 Top-7 | 候選減 matched 20 日 | 候選減 eligible | 候選減 complete |",
        "|---:|---:|---:|---:|---:|---:|---:|",
    ]
    primary = result["paths"]
    primary_differences = [
        primary["resonance3_qqq_overlay"]["cagr"] - primary[path_id]["cagr"]
        for path_id in baseline_ids
    ]
    lines.append(
        f"| 20 bp | {_pct(primary['resonance3_qqq_overlay']['cagr'])} | "
        + " | ".join(_signed_pct(value) for value in primary_differences)
        + " |"
    )
    for cost in ("50", "100"):
        row = result["stresses"]["costs"][cost]
        differences = row["candidate_cagr_differences"]
        lines.append(
            f"| {cost} bp | {_pct(row['paths']['resonance3_qqq_overlay']['cagr'])} | "
            + " | ".join(_signed_pct(differences[path_id]) for path_id in baseline_ids)
            + " |"
        )
    return "\n".join(lines)


def _regime_table(result: dict[str, Any]) -> str:
    labels = {"nonnegative": "QQQ 20 日動量非負", "negative": "QQQ 20 日動量負"}
    lines = [
        "| 訊號日已知市況 | 事件數 | 平均候選數 | 平均股票比例 | 平均／中位事件差 |",
        "|---|---:|---:|---:|---:|",
    ]
    for regime_id in ("nonnegative", "negative"):
        row = result["stresses"]["known_at_qqq_regimes"][regime_id]
        lines.append(
            f"| {labels[regime_id]} | {row['events']} | {row['average_candidates']:.2f} | "
            f"{_pct(row['average_stock_fraction'], 1)} | "
            f"{row['average_event_difference'] * 10_000:+.2f}／"
            f"{row['median_event_difference'] * 10_000:+.2f} bp |"
        )
    return "\n".join(lines)


def _crisis_table(result: dict[str, Any]) -> str:
    lines = [
        "| 年份 | 候選回報／最大跌幅 | QQQ 回報／最大跌幅 | 回報差 |",
        "|---|---:|---:|---:|",
    ]
    for year in ("2008", "2020", "2022"):
        paths = result["stresses"]["crisis_years"][year]
        candidate = paths["resonance3_qqq_overlay"]
        qqq = paths["qqq_buy_hold"]
        lines.append(
            f"| {year} | {_signed_pct(candidate['return'])}／{_pct(candidate['max_drawdown'])} | "
            f"{_signed_pct(qqq['return'])}／{_pct(qqq['max_drawdown'])} | "
            f"{_signed_pct(candidate['return'] - qqq['return'])} |"
        )
    return "\n".join(lines)


def _gate_list(result: dict[str, Any]) -> str:
    return "\n".join(
        f"- {GATE_LABELS[row['id']]}：**{'通過' if row['passed'] else '未通過'}**"
        for row in result["gates"]
    )


def _control_list(result: dict[str, Any]) -> str:
    return "\n".join(
        f"- {row['id']} · `{row['label']}`：{'通過' if row['passed'] else '未通過'}"
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
    paths = result["paths"]
    candidate = paths["resonance3_qqq_overlay"]
    qqq = paths["qqq_buy_hold"]
    original = paths["original_top7_qqq_overlay"]
    matched20 = paths["matched_20d_qqq_overlay"]
    comparison_by_id = {
        row["baseline_id"]: row for row in result["family"]["comparisons"]
    }
    qqq_comparison = comparison_by_id["qqq_buy_hold"]
    matched20_comparison = comparison_by_id["matched_20d_qqq_overlay"]
    distribution = result["selection_distribution"]
    years = result["stresses"]["best_three_years_removed"]
    tail = result["stresses"]["favorable_46_events_removed"]
    failed = [GATE_LABELS[row["id"]] for row in result["gates"] if not row["passed"]]
    verdict = "全部通過但仍不得升格" if not failed else "未通過，不建立新策略"
    return f"""# 美股短線第 38 輪：四窗動量共振替換式疊加研究報告

生成日期：{result["generated_on"]}

資料期：{result["input"]["first_signal_date"]} 至 {result["input"]["last_exit_date"]}

研究角色：同一批已見 survivor 事件的有界反證；不是正式 point-in-time 回測、即市買入名單、
Paper 或實金指令。

## 結論一覽

本輪按已推送事前協議，只測試 5／10／15／20 日動量 Top-7 的跨窗一致性。每宗事件只有
最少三窗共振的股票佔用七個固定分注，每隻只佔該 20% 資金槽的 1/7；未佔用分注繼續持有
QQQ。沒有搜尋窗口、門檻、持有期、市況開關或結果後 fallback。

20 bp 每資產來回成本下，US$1,000 候選期末值為 **{_money(candidate['terminal_usd'])}**、
CAGR **{_pct(candidate['cagr'])}**；QQQ 買入並持有為 **{_money(qqq['terminal_usd'])}**、
**{_pct(qqq['cagr'])}**，原第 30 輪 Top-7 為 **{_money(original['terminal_usd'])}**、
**{_pct(original['cagr'])}**，相同比例 20 日動量路徑為 **{_money(matched20['terminal_usd'])}**、
**{_pct(matched20['cagr'])}**。

事前二十項門檻通過 **{result['gate_summary']['passed']}/{result['gate_summary']['total']}**，結論為
**{verdict}**。{('未通過項目：' + '、'.join(failed) + '。') if failed else ''}

- 候選相對 QQQ 的 NW t 為 **{qqq_comparison['newey_west']['t_stat']:.2f}**，Holm／共同
  max-t／6,229 次全專案 p 為 **{qqq_comparison['holm_adjusted_p']:.4f}／
  {qqq_comparison['bootstrap_max_t_p']:.4f}／{qqq_comparison['global_bonferroni_p']:.4f}**；
- 相對 matched 20 日路徑的 NW t 為 **{matched20_comparison['newey_west']['t_stat']:.2f}**，
  直接回答多窗共振有沒有單窗以外的增量；
- 移除相對 QQQ 最佳三年 {', '.join(map(str, years['removed_years']))} 後，NW t 為
  **{years['newey_west']['t_stat']:.2f}**；
- 移除事前定義的最有利 46 宗事件後，候選減 QQQ CAGR 為
  **{_signed_pct(tail['candidate_cagr_differences']['qqq_buy_hold'])}**；
- 無論本輪數字如何，`can_promote_from_this_round=false`、`new_strategy_created=false`。
  短線 Paper 維持全現金、持倉 0，實金動作 **US$0**。

## 共振選擇分布

905 宗事件平均有 **{distribution['mean_candidates']:.2f}** 隻候選，平均股票目標比例
**{_pct(distribution['mean_stock_target_fraction'], 1)}**；候選數範圍
{distribution['minimum_candidates']} 至 {distribution['maximum_candidates']}。候選不足七隻時
不會放大餘下股票；QQQ 承接所有未用分注。

{_selection_table(result)}

排名以整數 rank-sum 作真正 tie-break，百分位只作展示。逐事件收據保留四窗 Top-7、共振次數、
最終選股、N/7 股票比例及 QQQ 餘額；最大分配 identity 誤差為
`{distribution['maximum_allocation_residual']:.3g}`。

## 九條固定完整資金路徑

{_path_table(result)}

所有路徑由首次成交後保持 100% long、零現金及無槓桿。候選只對實際被替換比例收取 QQQ
沽出、股票買入、股票沽出及 QQQ 買回四個經濟腿；未替換的 QQQ 不收虛構成本。原 Top-7
與第 30 輪逐日最大殘差為 `{result['calendar_integrity']['maximum_original_top7_parent_residual']:.3g}`，
部分 QQQ 換手 placebo 最大殘差為 `{result['calendar_integrity']['maximum_qqq_placebo_residual']:.3g}`。

## 八假說共同統計 family

{_family_table(result)}

八項比較共用 Newey–West lag 20、63-session circular blocks、20,000 條共同 bootstrap 路徑、
seed 38,202,608 及相同抽樣 indices。正式搜尋帳由 6,221 增至 6,229，沒有因本輪結果重設。

## 成本壓力

{_cost_table(result)}

50／100 bp 同步重建九路，不會只提高候選成本。模型按成交名義收比例成本，未另計固定每單
佣金、買賣差價、市場衝擊、稅項及碎股限制；eligible／complete 持股數較多，這是重要限制。

## 已知市況、事件尾部與危機期

{_regime_table(result)}

市況只使用訊號日已知的 QQQ 20 日動量，沒有 p 值，亦不會變成開關。最有利 46 宗事件以
事前固定候選減 QQQ gross difference 排序；六條 overlay 同時把相同事件改為全槽 QQQ，
沒有刪除日期或重排五槽。

{_crisis_table(result)}

## 二十項事前反證門檻

{_gate_list(result)}

任何一項未通過即 `not_rejected_by_round38=false`。即使 20/20，本輪仍是同一已見 survivor
樣本，不能建立 Paper 或實金策略。

## {result['control_summary']['total']} 道固定控制

{_control_list(result)}

{result['control_summary']['passed']}/{result['control_summary']['total']} 只證明程式遵守已推送
協議，不證明未來盈利。

## {result['attack_summary']['total']} 項單欄變異攻擊

{_attack_table(result)}

所有變異須命中指定穩定錯誤碼；任何窗口、共振門檻、N/7 分注、QQQ 餘額、成本、父路徑、
family、統計或 Paper／實金權限漂移都會 fail closed。

## 市場與數據邊界

資料最後退出日為 **{result['input']['last_exit_date']}**，不是即市行情。股票仍是 2026 現時
survivor cohort，欠缺逐期成分、永久證券 ID、可靠退市／退出經濟、歷史公司行動及公告時間。
調整 OHLC、分數股與 US$1,000 只供比例研究，不能冒充真實券商成交或稅後結果。

正式就緒仍為 **{result['decision']['formal_readiness']}**，point-in-time
**{result['decision']['point_in_time_readiness']}**，合資格 provider package 0，正式策略 run 0。
下一個可升格步驟仍是獲授權逐期成分、永久 ID、公司行動及退市資料，原樣執行既有正式
預先登記；不得用本輪結果重選參數。

## 可重播檔案

- [第 38 輪事前協議](SHORT_TERM_MULTI_WINDOW_RESONANCE_PROTOCOL.md)
- `artifacts/short_term_multi_window_resonance_validation.json`
- `site/data/short-term-multi-window-resonance.json`
"""


def main() -> None:
    result = run_multi_window_resonance(ROOT)
    result["receipt_float_decimal_places"] = RECEIPT_FLOAT_DECIMAL_PLACES
    canonical = _canonicalize_floats(result)
    payload = json.dumps(canonical, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ARTIFACT.parent.mkdir(parents=True, exist_ok=True)
    SITE_DATA.parent.mkdir(parents=True, exist_ok=True)
    ARTIFACT.write_text(payload, encoding="utf-8")
    SITE_DATA.write_text(payload, encoding="utf-8")
    REPORT.write_text(_report(canonical), encoding="utf-8")
    print(
        f"wrote {ARTIFACT.relative_to(ROOT)}, {SITE_DATA.relative_to(ROOT)}, "
        f"{REPORT.relative_to(ROOT)}"
    )


if __name__ == "__main__":
    main()
