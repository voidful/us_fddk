from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from usfddk.temporal_tail_robustness import run_temporal_tail_robustness

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "artifacts/short_term_temporal_tail_robustness_validation.json"
SITE_DATA = ROOT / "site/data/short-term-temporal-tail-robustness.json"
REPORT = ROOT / "docs/SHORT_TERM_TEMPORAL_TAIL_ROBUSTNESS_RESEARCH_REPORT.md"
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


def _year_table(result: dict[str, Any]) -> str:
    lines = [
        "| 年份 | 事件 | 平均差 | 中位差 | 正配對 | 淨差貢獻 |",
        "|---:|---:|---:|---:|---:|---:|",
    ]
    for row in result["calendar_years"]:
        lines.append(
            f"| {row['year']} | {row['events']} | {_pp(row['mean_difference'])} | "
            f"{_pp(row['median_difference'])} | {_pct(row['positive_fraction'])} | "
            f"{_pct(row['share_of_net_sum'])} |"
        )
    return "\n".join(lines)


def _epoch_table(result: dict[str, Any]) -> str:
    lines = [
        "| 固定時段 | 事件 | 平均差 | 中位差 | NW t |",
        "|---|---:|---:|---:|---:|",
    ]
    for row in result["epochs"]:
        lines.append(
            f"| {row['label']} | {row['events']} | {_pp(row['mean_difference'])} | "
            f"{_pp(row['median_difference'])} | "
            f"{row['newey_west_lag4']['t_stat']:.2f} |"
        )
    return "\n".join(lines)


def _hac_table(result: dict[str, Any]) -> str:
    lines = ["| NW lag | 平均差 | 標準誤 | t 值 |", "|---:|---:|---:|---:|"]
    for row in result["hac_frontier"]:
        lines.append(
            f"| {row['lag']} | {_pp(row['mean_difference'])} | "
            f"{_pp(row['standard_error'])} | {row['t_stat']:.2f} |"
        )
    return "\n".join(lines)


def _winsor_table(result: dict[str, Any]) -> str:
    lines = [
        "| 對稱 winsor | 平均差 | NW4 | NW13 | NW26 | NW52 |",
        "|---:|---:|---:|---:|---:|---:|",
    ]
    for row in result["winsorized"]:
        t_values = {item["lag"]: item["t_stat"] for item in row["hac_frontier"]}
        lines.append(
            f"| {_pct(row['lower_quantile'], 0)}／{_pct(row['upper_quantile'], 0)} | "
            f"{_pp(row['mean_difference'])} | {t_values[4]:.2f} | "
            f"{t_values[13]:.2f} | {t_values[26]:.2f} | {t_values[52]:.2f} |"
        )
    return "\n".join(lines)


def _removal_table(result: dict[str, Any]) -> str:
    lines = [
        "| 壓力 | 移除 | 剩餘平均差 | NW4 t | 年度 cluster t |",
        "|---|---|---:|---:|---:|",
    ]
    for row in result["best_year_removals"]:
        lines.append(
            f"| 最佳年份 | {', '.join(map(str, row['removed_years']))} | "
            f"{_pp(row['mean_difference'])} | "
            f"{row['newey_west_lag4']['t_stat']:.2f} | "
            f"{row['calendar_cluster']['t_stat']:.2f} |"
        )
    for row in result["tail_event_removals"]:
        lines.append(
            f"| 最大正事件 | {row['removed_count']} 列 | "
            f"{_pp(row['mean_difference'])} | "
            f"{row['newey_west_lag4']['t_stat']:.2f} | "
            f"{row['calendar_cluster']['t_stat']:.2f} |"
        )
    return "\n".join(lines)


def _report(result: dict[str, Any]) -> str:
    observed = result["observed"]
    cluster = result["calendar_cluster"]
    bootstrap = result["moving_block_bootstrap"]
    sign = result["sign_test"]
    remove_one = result["best_year_removals"][0]
    remove_three = result["best_year_removals"][1]
    tail_one = result["tail_event_removals"][0]
    tail_five = result["tail_event_removals"][1]
    gate_rows = "\n".join(
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
    return f"""# 美股短線第 23 輪：時間聚類與極端贏家脆弱度報告

研究日期：2026-08-04

狀態：survivor cohort 反證；不可投資；短線 Paper 全現金；實金動作 US$0

## 一頁結論

現有 905 個 20 日 Top-7 事件的普通平均配對差為
**{_pp(observed['mean_active_difference'])}**，但第 23 輪八項事前反證門檻只通過
**{result['gate_summary']['passed']}/{result['gate_summary']['total']}**。

按 21 個曆年聚類後 t 值為 **{cluster['t_stat']:.2f}**，須比較固定 t(20) 臨界值
2.085963；52-event circular block bootstrap 的 95% 區間為
**{_pp(bootstrap['mean_difference_quantiles']['p025'])} 至
{_pp(bootstrap['mean_difference_quantiles']['p975'])}**。21 年中只有
**{result['positive_calendar_years']} 年**平均差為正。

刪除貢獻最大的 **{remove_one['removed_years'][0]}** 後，平均差為
**{_pp(remove_one['mean_difference'])}**、NW t **{remove_one['newey_west_lag4']['t_stat']:.2f}**；
刪除最佳三年 {', '.join(map(str, remove_three['removed_years']))} 後，平均差為
**{_pp(remove_three['mean_difference'])}**、NW t **{remove_three['newey_west_lag4']['t_stat']:.2f}**。
最大的 10／46 個正事件分別佔全部正配對差
**{_pct(tail_one['share_of_positive_sum'])}／{_pct(tail_five['share_of_positive_sum'])}**；
移除後平均差為 **{_pp(tail_one['mean_difference'])}／{_pp(tail_five['mean_difference'])}**。

這輪結果只可削弱或保留現有線索，不能把 survivor cohort 升格。正式就緒仍為
**1/18**、正式逐股策略運行 **0 次**、Paper 持倉 **0**、實金動作 **US$0**。

## 八項事前反證門檻

{gate_rows}

八項全過也只可寫作「未被本輪推翻」；任何一項失敗便不得把普通平均 t 值當成穩健 alpha。

## 時間依賴

{_hac_table(result)}

原始事件每週重疊，lag 4 只約涵蓋一個持有期；13、26、52 完整呈列，不能按結果挑選。

### 五個固定市場時段

{_epoch_table(result)}

### 21 個曆年

{_year_table(result)}

年度 cluster 使用有限樣本修正及 20 自由度，不用常態 1.96 冒充門檻。

## 尾部及集中度

{_winsor_table(result)}

{_removal_table(result)}

配對方向為正 {sign['positive']}、負 {sign['negative']}、零 {sign['zero']}；精確雙尾
sign-test p 值 **{sign['two_sided_exact_p_value']:.4f}**。它檢查方向，不取代回報幅度分析。

## 52-event moving-block bootstrap

- 路徑：{bootstrap['paths']:,}；每條 18 個 circular blocks；固定 seed {bootstrap['seed']}。
- 平均差中位數：{_pp(bootstrap['mean_difference_quantiles']['p500'])}。
- 正平均路徑：{_pct(bootstrap['positive_mean_fraction'])}。
- start-index SHA-256：`{bootstrap['start_index_sha256']}`。

這個區間只描述現有 survivor cohort 的時間抽樣，不是 point-in-time／退市修正後區間。

## 十五道控制

{controls}

## 十五項突變攻擊

{attacks}

## 決策

本輪不得產生股票名單、持倉或落盤指令。現有正平均只保留為「取得合資格數據後按原樣
重測」的假說；正式入口仍須獲授權 point-in-time 成分、永久 ID、歷史行業、公司行動、
退市／收購實收、移除後價格路徑，以及同步 QQQ／SPY／XNYS／精確 RF。

輸入齊全後仍只准依既有 18/18 事前登記運行一次正式回測，再通過 50 bps、QQQ／SPY／
逐期股池 baseline、NW、DSR、PBO 與真正新增 252 個交易日／12 次月度輪選，才可由全現金
開始 Paper。US$1,000 只作讀者比例示例，不是持倉建議。

- [第 23 輪事前協議](SHORT_TERM_TEMPORAL_TAIL_ROBUSTNESS_PROTOCOL.md)
- [第 22 輪缺失退出壓力](SHORT_TERM_SURVIVORSHIP_CONTAMINATION_RESEARCH_REPORT.md)
- [原 20 日訊號研究](SHORT_TERM_HIGH_RETURN_RESEARCH_REPORT.md)

歷史及合成結果不保證未來回報；本報告不構成投資建議、Paper 成交或實金落盤指令。
"""


def main() -> None:
    result = run_temporal_tail_robustness(ROOT)
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
