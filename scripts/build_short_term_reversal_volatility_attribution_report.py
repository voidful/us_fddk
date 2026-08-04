from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from usfddk.reversal_volatility_attribution import run_reversal_volatility_attribution

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "artifacts/short_term_reversal_volatility_attribution_validation.json"
SITE_DATA = ROOT / "site/data/short-term-reversal-volatility-attribution.json"
REPORT = ROOT / "docs/SHORT_TERM_REVERSAL_VOLATILITY_ATTRIBUTION_RESEARCH_REPORT.md"
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


def _pp(value: float, digits: int = 3) -> str:
    sign = "+" if value >= 0 else ""
    return f"{sign}{value * 100:.{digits}f} 個百分點"


def _rank(value: float, digits: int = 3) -> str:
    sign = "+" if value >= 0 else ""
    return f"{sign}{value:.{digits}f}"


def _family_table(result: dict[str, Any]) -> str:
    lines = [
        "| 固定比較 | 平均 | NW t | 普通 p | Holm p | 共同 max-t p | 前半 | 後半 |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in result["family"]["comparisons"]:
        lines.append(
            f"| {row['id']} | {_pp(row['mean'])} | {row['newey_west']['t_stat']:.2f} | "
            f"{row['raw_normal_p']:.4f} | {row['holm_adjusted_p']:.4f} | "
            f"{row['bootstrap_max_t_p']:.4f} | {_pp(row['fixed_halves']['first']['mean'])} | "
            f"{_pp(row['fixed_halves']['second']['mean'])} |"
        )
    return "\n".join(lines)


def _attribution_table(result: dict[str, Any]) -> str:
    family = {row["id"]: row for row in result["family"]["comparisons"]}
    lines = [
        "| Universe | raw bottom-middle | 控制預測 | residual | 5 日 rank gap | 波幅 rank gap | 5 日貢獻 | 波幅貢獻 |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for universe_id in ("eligible", "complete"):
        summary = result["attribution_summary"][universe_id]
        lines.append(
            f"| {universe_id} | {_pp(family[f'{universe_id}_raw_bottom_middle']['mean'])} | "
            f"{_pp(summary['predicted_bottom_middle']['mean'])} | "
            f"{_pp(family[f'{universe_id}_residual_bottom_middle']['mean'])} | "
            f"{_rank(summary['prior5_rank_gap_bottom_middle']['mean'])} | "
            f"{_rank(summary['volatility_rank_gap_bottom_middle']['mean'])} | "
            f"{_pp(summary['prior5_contribution_bottom_middle']['mean'])} | "
            f"{_pp(summary['volatility_contribution_bottom_middle']['mean'])} |"
        )
    return "\n".join(lines)


def _coefficient_table(result: dict[str, Any]) -> str:
    lines = [
        "| Universe | 5 日 rank beta | NW t | 波幅 rank beta | NW t | residual／raw top-middle |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for universe_id in ("eligible", "complete"):
        row = result["attribution_summary"][universe_id]
        lines.append(
            f"| {universe_id} | {_pp(row['beta_prior5']['mean'])} | "
            f"{row['beta_prior5']['newey_west']['t_stat']:.2f} | "
            f"{_pp(row['beta_volatility']['mean'])} | "
            f"{row['beta_volatility']['newey_west']['t_stat']:.2f} | "
            f"{row['aggregate_top_middle_retention_fraction'] * 100:.1f}% |"
        )
    return "\n".join(lines)


def _stress_table(result: dict[str, Any]) -> str:
    regimes = result["primary_stresses"]["qqq_trailing_20d_known_at_signal"]
    tails = result["primary_stresses"]["remove_largest_raw_bottom_middle"]
    lines = [
        "| Universe | 固定壓力 | 事件 | residual top-middle 平均 | NW t |",
        "|---|---|---:|---:|---:|",
    ]
    for universe_id in ("eligible", "complete"):
        for key, label in (
            ("qqq_trailing_nonnegative", "訊號日 QQQ 20 日非負"),
            ("qqq_trailing_negative", "訊號日 QQQ 20 日負"),
        ):
            row = regimes[universe_id][key]
            lines.append(
                f"| {universe_id} | {label} | {row['events']} | {_pp(row['mean'])} | "
                f"{row['newey_west']['t_stat']:.2f} |"
            )
        row = tails[universe_id]
        lines.append(
            f"| {universe_id} | 移除最大 46 個 raw bottom-middle | {row['events']} | "
            f"{_pp(row['mean'])} | {row['newey_west']['t_stat']:.2f} |"
        )
    return "\n".join(lines)


def _gate_list(result: dict[str, Any]) -> str:
    return "\n".join(
        f"- {row['label']}：**{'通過' if row['passed'] else '未通過'}**" for row in result["gates"]
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
    family = {row["id"]: row for row in result["family"]["comparisons"]}
    eligible_raw = family["eligible_raw_top_middle"]
    complete_raw = family["complete_raw_top_middle"]
    eligible_residual = family["eligible_residual_top_middle"]
    complete_residual = family["complete_residual_top_middle"]
    eligible_bottom = family["eligible_residual_bottom_middle"]
    complete_bottom = family["complete_residual_bottom_middle"]
    regimes = result["primary_stresses"]["qqq_trailing_20d_known_at_signal"]
    tails = result["primary_stresses"]["remove_largest_raw_bottom_middle"]
    return f"""# 美股短線第 28 輪：短期反轉與波幅歸因報告

生成日期：{result["generated_on"]}
研究角色：同一已見 survivor cohort 的機制歸因；不是買入名單、Paper 或實金指令。

## 執行摘要

本輪在任何新歸因統計前，以 commit `{result["protocol"]["commit"][:7]}` 固定第 27 輪全部
905 個事件與 bucket、訊號日前 5 日回報、20 日已實現波幅、兩控制橫截面 OLS、八假說
family、QQQ known-at 市況及 46-event 尾部。這是同一已見樣本，不是獨立未見確認。

控制後，高段對中段明顯縮小：

- eligible 由 **{_pp(eligible_raw["mean"])}、NW t {eligible_raw["newey_west"]["t_stat"]:.2f}**
  降至 **{_pp(eligible_residual["mean"])}、t {eligible_residual["newey_west"]["t_stat"]:.2f}**，
  只保留 {result["attribution_summary"]["eligible"]["aggregate_top_middle_retention_fraction"] * 100:.1f}%；
- complete 由 **{_pp(complete_raw["mean"])}、t {complete_raw["newey_west"]["t_stat"]:.2f}**
  降至 **{_pp(complete_residual["mean"])}、t {complete_residual["newey_west"]["t_stat"]:.2f}**，
  只保留 {result["attribution_summary"]["complete"]["aggregate_top_middle_retention_fraction"] * 100:.1f}%，
  後半平均更轉為 **{_pp(complete_residual["fixed_halves"]["second"]["mean"])}**；
- 控制後 bottom-middle 仍為 **{_pp(eligible_bottom["mean"])}／{_pp(complete_bottom["mean"])}**，
  沒有回復單調排序；
- 訊號日 QQQ 20 日為負時，eligible／complete residual top-middle 平均為
  **{_pp(regimes["eligible"]["qqq_trailing_negative"]["mean"])}／
  {_pp(regimes["complete"]["qqq_trailing_negative"]["mean"])}**；
- 尾部壓力 NW t 為 **{tails["eligible"]["newey_west"]["t_stat"]:.2f}／
  {tails["complete"]["newey_west"]["t_stat"]:.2f}**，eligible 的 1.95 仍嚴格低於 1.96。

十四項事前門檻只過 **{result["gate_summary"]["passed"]}/{result["gate_summary"]["total"]}**。
5 日反轉與波幅共同解釋了大部分 top-middle 平均差，卻沒有完整解釋底段反彈；剩餘差額在
完整股池、共同校正、後半、弱市及尾部均不足。正式就緒維持 **1/18**、point-in-time
**1/20**、策略運行 **0**、短線 Paper 全現金、持倉 **0**、實金動作 **US$0**。

## 輸入與歸因完整性

| 項目 | 結果 |
|---|---:|
| 原始／共同事件 | {result["input"]["events"]} / {result["input"]["events"]} |
| 訊號日期 | {result["input"]["first_signal_date"]} 至 {result["input"]["last_signal_date"]} |
| raw 對第 27 輪最大誤差 | {result["attribution_integrity"]["maximum_raw_round27_residual"]:.3e} |
| raw = predicted + residual 最大誤差 | {result["attribution_integrity"]["maximum_identity_residual"]:.3e} |
| residual universe mean 最大絕對值 | {result["attribution_integrity"]["maximum_residual_mean"]:.3e} |
| OLS 最大 condition number／最低 rank | {result["attribution_integrity"]["maximum_condition_number"]:.2f} / {result["attribution_integrity"]["minimum_design_rank"]} |
| feature receipt SHA-256 | `{result["attribution_integrity"]["feature_receipt_sha256"]}` |
| 控制／攻擊 | {result["control_summary"]["passed"]}/{result["control_summary"]["total"]} / {result["attack_summary"]["rejected"]}/{result["attack_summary"]["total"]} 拒收 |

## 八假說共同 family

{_family_table(result)}

八列共用 52-event circular blocks、20,000 路徑及 seed 28202610。raw eligible top-middle 的
Holm／共同 max-t p 已升至 **{eligible_raw["holm_adjusted_p"]:.4f}／
{eligible_raw["bootstrap_max_t_p"]:.4f}**；控制後兩個 top-middle 普通 NW t 亦低於 1.96。

## 底段反彈歸因

{_attribution_table(result)}

bottom 的訊號日前 5 日 rank 明顯低於 middle，但 5 日 rank beta 本身不穩定；完整股池的
bottom 波幅 rank 較高，波幅 beta 為正，但平均波幅貢獻的 NW t 仍不足 1.96。因此不能把
底段反彈簡化成單一「短期反轉」或「高波幅補償」。

{_coefficient_table(result)}

## 訊號日市況與尾部壓力

{_stress_table(result)}

QQQ 分組只使用訊號日已知 20 日回報，但仍是已見樣本診斷。弱市兩個 residual top-middle
平均皆負；46-event 壓力亦沒有兩個 universe 同時通過。

## 十四項事前反證門檻

{_gate_list(result)}

## 二十三道輸入、控制、OLS、family 及決策控制

{_control_list(result)}

23/23 只證明程式遵守凍結協議，不是策略盈利通過。

## 二十三項單欄變異攻擊

{_attack_table(result)}

每項均命中事前指定錯誤碼；真實特徵覆蓋不足會由主路徑以
`reversal_volatility_coverage_mismatch` 在結果前 fail closed。

## 決策

第 28 輪把局部 top-middle 線索再收窄：大部分平均差與 5 日／波幅控制共變，殘差不再通過；
底段反彈仍存在，亦沒有在完整股池、後半或弱市形成可靠單調結構。**不建立新策略、不啟動
短線 Paper、不產生持倉或買入名單。**

下一個可升級證據仍是合法授權 point-in-time 成分、永久 ID、歷史行業、公司行動、退市／
退出經濟與同步基準；在此之前再改控制窗或只選 QQQ 強市，均屬事後救援。

## 可重播檔案

- [第 28 輪事前協議](SHORT_TERM_REVERSAL_VOLATILITY_ATTRIBUTION_PROTOCOL.md)
- `artifacts/short_term_reversal_volatility_attribution_validation.json`
- `site/data/short-term-reversal-volatility-attribution.json`
"""


def main() -> None:
    result = run_reversal_volatility_attribution(ROOT)
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
