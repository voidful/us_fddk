from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from usfddk.baseline_multiplicity import run_baseline_multiplicity

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "artifacts/short_term_baseline_multiplicity_validation.json"
SITE_DATA = ROOT / "site/data/short-term-baseline-multiplicity.json"
REPORT = ROOT / "docs/SHORT_TERM_BASELINE_MULTIPLICITY_RESEARCH_REPORT.md"
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


def _p(value: float) -> str:
    return f"{value:.4f}" if value >= 0.0001 else f"{value:.2e}"


def _comparison_table(result: dict[str, Any]) -> str:
    lines = [
        "| 期限 | Baseline | 平均差 | NW t | 普通 p | Holm | Max-t | RW step-down | 6,208× |",
        "|---:|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in result["comparisons"]:
        lines.append(
            f"| {row['horizon']} 日 | {row['baseline_label']} | "
            f"{_pp(row['mean_difference'])} | {row['newey_west']['t_stat']:.2f} | "
            f"{_p(row['raw_normal_p'])} | {_p(row['holm_adjusted_p'])} | "
            f"{_p(row['bootstrap_max_t_p'])} | "
            f"{_p(row['romano_wolf_stepdown_p'])} | "
            f"{_p(row['global_bonferroni_p'])} |"
        )
    return "\n".join(lines)


def _attribution_table(result: dict[str, Any]) -> str:
    labels = {
        "ranking_effect": "Top-7 排名效果",
        "eligibility_effect": "合資格濾網效果",
        "combined_effect": "對完整股池合計",
    }
    lines = [
        "| 20 日歸因 | 定義 | 平均差 | NW t | 前半 | 後半 |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for key, row in result["primary_attribution"].items():
        if key == "max_abs_identity_residual":
            continue
        lines.append(
            f"| {labels[key]} | `{row['definition']}` | "
            f"{_pp(row['mean_difference'])} | {row['newey_west']['t_stat']:.2f} | "
            f"{_pp(row['fixed_halves']['first']['mean_difference'])} | "
            f"{_pp(row['fixed_halves']['second']['mean_difference'])} |"
        )
    return "\n".join(lines)


def _report(result: dict[str, Any]) -> str:
    primary = result["primary_baselines"]
    eligible = primary["eligible_equal_return"]
    complete = primary["complete_cohort_equal_return"]
    qqq = primary["qqq_return"]
    bootstrap = result["common_bootstrap"]
    gates = "\n".join(
        f"- {row['label']}：**{'通過' if row['passed'] else '未通過'}**"
        for row in result["gates"]
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
    return f"""# 美股短線第 24 輪：公平基準歸因與多重檢驗報告

研究日期：2026-08-04

狀態：survivor cohort 反證；不可投資；短線 Paper 全現金；實金動作 US$0

## 一頁結論

20 日 Top-7 對合資格池等權仍有 **{_pp(eligible['mean_difference'])}**、NW t
**{eligible['newey_west']['t_stat']:.2f}**；但對完整現時股池等權只餘
**{_pp(complete['mean_difference'])}**、NW t **{complete['newey_west']['t_stat']:.2f}**。
對 QQQ 的事件差為 **{_pp(qqq['mean_difference'])}**、NW t
**{qqq['newey_west']['t_stat']:.2f}**。

九假說 Holm 後，主要合資格池 p 為 **{_p(eligible['holm_adjusted_p'])}**；共同 52-event
max-t p 為 **{_p(eligible['bootstrap_max_t_p'])}**，Reality Check p 為
**{_p(bootstrap['reality_check_p_value'])}**。但全專案 6,208 次 Bonferroni p 為
**{_p(eligible['global_bonferroni_p'])}**，而且完整現時股池 NW 門檻失敗；九項事前門檻
只通過 **{result['gate_summary']['passed']}/{result['gate_summary']['total']}**。

所以「排名相對已通過濾網的股票有訊號」不能改寫成「Top-7 對完整股池及搜尋偏誤都
穩健」。正式就緒仍為 **1/18**、正式策略運行 **0 次**、Paper 持倉 **0**、實金
動作 **US$0**。

## 20 日公平基準歸因

{_attribution_table(result)}

逐列 `排名效果 + 合資格濾網效果 = 對完整股池合計`；最大恆等式殘差
`{result['primary_attribution']['max_abs_identity_residual']:.2e}`。完整現時股池仍有
存活者偏差，這張表只防止挑選最有利分母。

## 九個配對假說

{_comparison_table(result)}

普通 p 使用固定 NW t 的雙尾常態近似；Holm、共同 max-t、Romano–Wolf 及 6,208 次
Bonferroni 全部呈列，不以其中最漂亮的一欄取代其他負結果。

## 九項事前反證門檻

{gates}

任一失敗即不能升格；全通過亦只代表 survivor cohort 未被本輪推翻。

## 共同區塊 bootstrap

- 共同事件：{result['input']['common_events']}；52-event circular block；每路徑 18 blocks。
- 路徑：{bootstrap['paths']:,}；seed {bootstrap['seed']}；九列共用 indices 並各自去中心化。
- 觀察最大正 t：{bootstrap['observed_max_positive_t']:.2f}；Reality Check p：
  {_p(bootstrap['reality_check_p_value'])}。
- start-index SHA-256：`{bootstrap['start_index_sha256']}`。
- 全專案普通 p 通過界線：`{result['global_unadjusted_p_threshold']:.8f}`。

共同 bootstrap 保留同日跨期限及 baseline 關係，但沒有修復現時股池選樣偏差。

## 十六道控制

{controls}

## 十六項突變攻擊

{attacks}

## 決策

本輪沒有新增策略路徑、股票名單或落盤指令。正面排序效果只保留作取得合法
point-in-time 成分、永久 ID、歷史行業、公司行動、退市／收購實收及同步 RF 後的原樣
重測假說。

輸入齊全後仍只准依既有 18/18 正式事前登記運行一次，再通過 50 bps、QQQ／SPY／逐期
股池 baseline、NW／PSR／6,208-trial DSR／PBO，以及 252 個新增交易日／12 次完成月度
輪選，才可由全現金開始 Paper。US$1,000 只作讀者比例示例。

- [第 24 輪事前協議](SHORT_TERM_BASELINE_MULTIPLICITY_PROTOCOL.md)
- [第 23 輪時間／尾部反證](SHORT_TERM_TEMPORAL_TAIL_ROBUSTNESS_RESEARCH_REPORT.md)
- [原 20 日訊號研究](SHORT_TERM_HIGH_RETURN_RESEARCH_REPORT.md)

歷史及合成結果不保證未來回報；本報告不構成投資建議、Paper 成交或實金落盤指令。
"""


def main() -> None:
    result = run_baseline_multiplicity(ROOT)
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
