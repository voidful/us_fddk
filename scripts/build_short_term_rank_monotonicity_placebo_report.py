from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from usfddk.rank_monotonicity_placebo import run_rank_monotonicity_placebo

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "artifacts/short_term_rank_monotonicity_placebo_validation.json"
SITE_DATA = ROOT / "site/data/short-term-rank-monotonicity-placebo.json"
REPORT = ROOT / "docs/SHORT_TERM_RANK_MONOTONICITY_PLACEBO_RESEARCH_REPORT.md"
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


def _value(value: float, digits: int = 4) -> str:
    sign = "+" if value >= 0 else ""
    return f"{sign}{value:.{digits}f}"


def _family_table(result: dict[str, Any]) -> str:
    lines = [
        "| 固定比較 | 平均值 | NW t | 普通 p | Holm p | 共同 max-t p | 前半 | 後半 |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in result["family"]["comparisons"]:
        is_ic = row["id"].endswith("rank_ic")
        render = _value if is_ic else _pp
        lines.append(
            f"| {row['id']} | {render(row['mean'])} | {row['newey_west']['t_stat']:.2f} | "
            f"{row['raw_normal_p']:.4f} | {row['holm_adjusted_p']:.4f} | "
            f"{row['bootstrap_max_t_p']:.4f} | "
            f"{render(row['fixed_halves']['first']['mean'])} | "
            f"{render(row['fixed_halves']['second']['mean'])} |"
        )
    return "\n".join(lines)


def _sleeve_table(result: dict[str, Any]) -> str:
    lines = [
        "| Universe | 三分組 | 平均 20 日 net return | 中位 20 日 net return |",
        "|---|---|---:|---:|",
    ]
    for universe_id in ("eligible", "complete"):
        for bucket_id in ("top", "middle", "bottom"):
            row = result["sleeve_summary"][universe_id][bucket_id]
            lines.append(
                f"| {universe_id} | {bucket_id} | {_pct(row['mean_net_return'], 2)} | "
                f"{_pct(row['median_net_return'], 2)} |"
            )
    return "\n".join(lines)


def _placebo_table(result: dict[str, Any]) -> str:
    lines = [
        "| Universe | 真實平均 | 真實 NW t | placebo 最大平均 | ID | placebo 最大 t | ID | 平均／t 同時勝出 |",
        "|---|---:|---:|---:|---|---:|---|---|",
    ]
    for universe_id in ("eligible", "complete"):
        row = result["placebo"][universe_id]
        lines.append(
            f"| {universe_id} | {_pp(row['true_mean'])} | {row['true_t']:.2f} | "
            f"{_pp(row['maximum_placebo_mean'])} | {row['maximum_placebo_mean_id']} | "
            f"{row['maximum_placebo_t']:.2f} | {row['maximum_placebo_t_id']} | "
            f"{'是' if row['mean_dominates'] and row['t_dominates'] else '否'} |"
        )
    return "\n".join(lines)


def _all_placebos(result: dict[str, Any]) -> str:
    lines = [
        "| Universe | Placebo | 平均 top-bottom | NW t | 前半 | 後半 |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for universe_id in ("eligible", "complete"):
        for row in result["placebo"][universe_id]["rows"]:
            lines.append(
                f"| {universe_id} | {row['id']} | {_pp(row['mean'])} | "
                f"{row['newey_west']['t_stat']:.2f} | "
                f"{_pp(row['fixed_halves']['first']['mean'])} | "
                f"{_pp(row['fixed_halves']['second']['mean'])} |"
            )
    return "\n".join(lines)


def _stress_table(result: dict[str, Any]) -> str:
    regimes = result["primary_stresses"]["qqq_forward_regimes_ex_post_not_a_signal"]
    tails = result["primary_stresses"]["remove_largest_absolute_spreads"]
    lines = [
        "| Universe | 固定壓力 | 事件 | 平均 top-bottom | NW t |",
        "|---|---|---:|---:|---:|",
    ]
    for universe_id in ("eligible", "complete"):
        for regime, label in (
            ("qqq_nonnegative", "未來 QQQ 非負"),
            ("qqq_negative", "未來 QQQ 負"),
        ):
            row = regimes[universe_id][regime]
            lines.append(
                f"| {universe_id} | {label} | {row['events']} | {_pp(row['mean'])} | "
                f"{row['newey_west']['t_stat']:.2f} |"
            )
        row = tails[universe_id]
        lines.append(
            f"| {universe_id} | 移除最大 46 個絕對差 | {row['events']} | "
            f"{_pp(row['mean'])} | {row['newey_west']['t_stat']:.2f} |"
        )
    return "\n".join(lines)


def _gate_list(result: dict[str, Any]) -> str:
    return "\n".join(
        f"- {row['label']}：**{'通過' if row['passed'] else '未通過'}**" for row in result["gates"]
    )


def _control_table(result: dict[str, Any]) -> str:
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
    family = {row["id"]: row for row in result["family"]["comparisons"]}
    eligible_tm = family["eligible_top_middle"]
    eligible_mb = family["eligible_middle_bottom"]
    eligible_tb = family["eligible_top_bottom"]
    complete_tm = family["complete_top_middle"]
    complete_mb = family["complete_middle_bottom"]
    complete_tb = family["complete_top_bottom"]
    eligible_ic = family["eligible_rank_ic"]
    complete_ic = family["complete_rank_ic"]
    regimes = result["primary_stresses"]["qqq_forward_regimes_ex_post_not_a_signal"]
    tails = result["primary_stresses"]["remove_largest_absolute_spreads"]
    return f"""# 美股短線第 27 輪：排序單調性與隨機 placebo 反證報告

生成日期：{result["generated_on"]}
研究角色：現時 survivor cohort 的排序結構反證；不是最新買入名單、Paper 或實金指令。

## 執行摘要

本輪在任何新排序回報前先以 commit `{result["protocol"]["commit"][:7]}` 凍結兩個 universe、
三分組、八假說 family、20 組隨機 placebo、兩個 seed、QQQ 升跌市及 46-event 尾部壓力。
原 905 個事件全部覆蓋，父協議沒有縮樣本或 repair。
這些仍是第 24–26 輪已見的同一批事件，不是獨立未見確認。

結果不是由高至低的單調階梯：

- eligible 的 top-middle 為 **{_pp(eligible_tm["mean"])}**、NW t
  **{eligible_tm["newey_west"]["t_stat"]:.2f}**，但 middle-bottom 反為
  **{_pp(eligible_mb["mean"])}**、t **{eligible_mb["newey_west"]["t_stat"]:.2f}**；
- complete 的 top-middle 為 **{_pp(complete_tm["mean"])}**、t
  **{complete_tm["newey_west"]["t_stat"]:.2f}**，middle-bottom 同樣反為
  **{_pp(complete_mb["mean"])}**、t **{complete_mb["newey_west"]["t_stat"]:.2f}**；
- eligible／complete top-bottom 的 NW t 只有
  **{eligible_tb["newey_west"]["t_stat"]:.2f}／{complete_tb["newey_west"]["t_stat"]:.2f}**；
- rank IC 的 NW t 只有 **{eligible_ic["newey_west"]["t_stat"]:.2f}／
  {complete_ic["newey_west"]["t_stat"]:.2f}**；
- 完整股池真實 top-bottom t **{complete_tb["newey_west"]["t_stat"]:.2f}**，低於最強 placebo
  **{result["placebo"]["complete"]["maximum_placebo_t_id"]} 的
  {result["placebo"]["complete"]["maximum_placebo_t"]:.2f}**；
- 未來 QQQ 下跌時，eligible／complete top-bottom 平均為
  **{_pp(regimes["eligible"]["qqq_negative"]["mean"])}／
  {_pp(regimes["complete"]["qqq_negative"]["mean"])}**，兩者均為負。

十四項事前門檻只過 **{result["gate_summary"]["passed"]}/{result["gate_summary"]["total"]}**。
高段相對中段有局部線索，但底段反彈、完整股池、rank IC、多重校正、placebo、下跌市及
尾部均不支持把它寫成穩健排序 alpha。正式就緒仍為 **1/18**、point-in-time **1/20**、
正式策略運行 **0 次**、短線 Paper 全現金、持倉 **0**、實金動作 **US$0**。

## 凍結輸入與可重播性

| 項目 | 結果 |
|---|---:|
| 原始／本輪共同事件 | {result["input"]["events"]} / {result["input"]["events"]} |
| 訊號日期 | {result["input"]["first_signal_date"]} 至 {result["input"]["last_signal_date"]} |
| eligible 數目最少／中位／最多 | {result["input"]["eligible_count"]["minimum"]} / {result["input"]["eligible_count"]["median"]:.0f} / {result["input"]["eligible_count"]["maximum"]} |
| complete 三分組大小 | 9 / 8 / 8 |
| 最大回報重建誤差 | {result["reconstruction"]["maximum_return_residual"]:.3e} |
| bucket assignment SHA-256 | `{result["bucket_assignment_sha256"]}` |
| 控制／攻擊 | {result["control_summary"]["passed"]}/{result["control_summary"]["total"]} / {result["attack_summary"]["rejected"]}/{result["attack_summary"]["total"]} 拒收 |

所有股票仍是 2026 現時代號，沒有修復歷史成分、永久 ID、退市／收購或退出經濟。

## 三分組回報水平

{_sleeve_table(result)}

每段都是全額投資、等權及 20 bps round trip；表格只展示固定事件 sleeve 的平均／中位
20 日 net return，不可把 top-bottom 診斷當成實際可沽空策略。

## 八假說共同 family

{_family_table(result)}

八列共用 52-event circular blocks、20,000 路徑及 seed 27202609。最有利的兩列
top-middle 普通 t 值雖高於 1.96，但 Holm／共同 max-t 仍未過 0.05；middle-bottom 為負，
所以不能刪除底段反彈後只展示高段。

## 二十組隨機排序 placebo

{_placebo_table(result)}

eligible 真實 top-bottom 的平均及 t 都高於 20 組 placebo 最大值；complete 的真實平均
較高，但 t 值低於最強 placebo，因此兩個 universe 同時勝出的固定門檻失敗。20 組只作
事前固定的 selector 對照，不冒充精確 p 值。

{_all_placebos(result)}

## 升跌市與尾部壓力

{_stress_table(result)}

未來 QQQ 分組是事後反證，不是 regime 訊號。移除最大 46 個絕對差後，eligible／complete
NW t 只餘 **{tails["eligible"]["newey_west"]["t_stat"]:.2f}／
{tails["complete"]["newey_west"]["t_stat"]:.2f}**；兩者均未達 1.96。移除事件分別佔全部絕對
spread **{_pct(tails["eligible"]["removed_absolute_spread_share"])}／
{_pct(tails["complete"]["removed_absolute_spread_share"])}**。

## 十四項事前反證門檻

{_gate_list(result)}

## 二十三道輸入、排序、family、placebo 及決策控制

{_control_table(result)}

23/23 只證明程式遵守凍結協議，不是策略盈利通過。

## 二十三項單欄變異攻擊

{_attack_table(result)}

每項均命中事前指定錯誤碼。覆蓋不足不是合約欄位變異；真實覆蓋若不足，主路徑會以
`rank_monotonicity_coverage_mismatch` 在結果前直接 fail closed。

## 決策

第 27 輪保留一條很窄的研究觀察：高動量段相對中段的平均差為正。但這不是完整單調性；
middle-bottom 為負、top-bottom 及 rank IC 不顯著、完整股池未勝最強 placebo、QQQ 下跌組
為負、46-event 尾部亦未過。**不建立新策略、不啟動短線 Paper、不產生持倉或買入名單。**

下一個具升級價值的證據仍是獲授權 point-in-time 成分、永久 ID、歷史行業、公司行動、
退市／退出經濟與同步基準；在此之前，再改 bucket 數或只選 top-middle 都屬事後救援。

## 可重播檔案

- [第 27 輪事前協議](SHORT_TERM_RANK_MONOTONICITY_PLACEBO_PROTOCOL.md)
- `artifacts/short_term_rank_monotonicity_placebo_validation.json`
- `site/data/short-term-rank-monotonicity-placebo.json`
"""


def main() -> None:
    result = run_rank_monotonicity_placebo(ROOT)
    result["receipt_float_decimal_places"] = RECEIPT_FLOAT_DECIMAL_PLACES
    result = _canonicalize_floats(result)
    payload = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ARTIFACT.parent.mkdir(parents=True, exist_ok=True)
    SITE_DATA.parent.mkdir(parents=True, exist_ok=True)
    ARTIFACT.write_text(payload, encoding="utf-8")
    SITE_DATA.write_text(payload, encoding="utf-8")
    REPORT.write_text(_report(result), encoding="utf-8")
    print(
        f"wrote {ARTIFACT.relative_to(ROOT)}, {SITE_DATA.relative_to(ROOT)}, {REPORT.relative_to(ROOT)}"
    )


if __name__ == "__main__":
    main()
