from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "artifacts/short_term_leader_pullback_rebound_validation.json"
SITE_DATA = ROOT / "site/data/short-term-leader-pullback-rebound.json"
REPORT = ROOT / "docs/SHORT_TERM_LEADER_PULLBACK_REBOUND_RESEARCH_REPORT.md"
RECEIPT_FLOAT_DECIMAL_PLACES = 12
EXPECTED_PATH_IDS = {
    "lpr10_qqq_overlay",
    "matched_topn_10d_overlay",
    "matched_eligible_10d_overlay",
    "matched_complete_10d_overlay",
    "original_top7_10d_overlay",
    "matched_qqq_switch_placebo",
    "qqq_buy_hold",
    "spy_buy_hold",
    "shy_buy_hold",
}


def run_leader_pullback_rebound(root: str | Path) -> dict[str, Any]:
    from usfddk.leader_pullback_rebound import (
        run_leader_pullback_rebound as run_core,
    )

    return run_core(root)


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


def _number(value: Any, default: float = 0.0) -> float:
    return float(value) if isinstance(value, (int, float)) else default


def _receipt_complete(result: dict[str, Any]) -> bool:
    stresses = result.get("stresses", {})
    has_costs = bool(stresses.get("costs", stresses.get("proportional_costs", {})))
    has_fixed_fees = bool(
        stresses.get("fixed_fees", stresses.get("fixed_child_order_fees", {}))
    )
    return (
        EXPECTED_PATH_IDS.issubset(result.get("paths", {}))
        and len(result.get("family", {}).get("comparisons", [])) == 8
        and len(result.get("gates", [])) == 22
        and result.get("gate_summary", {}).get("total") == 22
        and result.get("control_summary", {}).get("total", 0) >= 48
        and result.get("attack_summary", {}).get("total", 0) >= 48
        and has_costs
        and has_fixed_fees
        and bool(stresses.get("best_three_years_removed"))
        and bool(stresses.get("known_at_qqq_regimes"))
        and bool(stresses.get("favorable_46_events_removed"))
    )


def _path_table(result: dict[str, Any]) -> str:
    lines = [
        "| 固定路徑 | CAGR | US$1,000 期末值 | SHY 超額 Sharpe | 最大跌幅 | 年率化換手 | 平均股票比例 | 子委託數 |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for path_id, row in result.get("paths", {}).items():
        lines.append(
            f"| {row.get('label', path_id)} | {_pct(_number(row.get('cagr')))} | "
            f"{_money(_number(row.get('terminal_usd')))} | "
            f"{_number(row.get('shy_excess_sharpe')):.2f} | "
            f"{_pct(_number(row.get('max_drawdown')))} | "
            f"{_number(row.get('annual_turnover')):.1f}x | "
            f"{_pct(_number(row.get('average_stock_driver_fraction')), 1)} | "
            f"{int(_number(row.get('total_child_orders'))):,} |"
        )
    return "\n".join(lines)


def _family_table(result: dict[str, Any]) -> str:
    lines = [
        "| 候選相對基準 | 年率化算術差 | NW t | Holm p | 共同 max-t p | 全專案 p | 前半／後半日均 |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in result.get("family", {}).get("comparisons", []):
        nw = row.get("newey_west", {})
        halves = row.get("fixed_halves", {})
        first = _number(halves.get("first", {}).get("mean_daily_difference")) * 10_000
        second = _number(halves.get("second", {}).get("mean_daily_difference")) * 10_000
        annualized = _number(
            row.get("annualized_arithmetic_difference", nw.get("annualized_arithmetic_difference"))
        )
        lines.append(
            f"| {row.get('baseline_label', row.get('baseline_id', '基準'))} | "
            f"{_signed_pct(annualized)} | {_number(nw.get('t_stat')):.2f} | "
            f"{_number(row.get('holm_adjusted_p')):.4f} | "
            f"{_number(row.get('bootstrap_max_t_p')):.4f} | "
            f"{_number(row.get('global_bonferroni_p')):.4f} | "
            f"{first:+.2f}／{second:+.2f} bp |"
        )
    return "\n".join(lines)


def _selection_table(result: dict[str, Any]) -> str:
    distribution = result.get("selection_distribution", {})
    histogram = distribution.get("candidate_count_histogram", [])
    lines = ["| 每宗確認股票數 N | 事件數 | 股票目標比例 |", "|---:|---:|---:|"]
    for row in histogram:
        count = int(_number(row.get("candidate_count", row.get("count"))))
        lines.append(
            f"| {count} | {int(_number(row.get('events')))} | {_pct(count / 7, 1)} |"
        )
    if not histogram:
        lines.append("| 收據未提供 | 0 | 0.0% |")
    return "\n".join(lines)


def _distribution_details(result: dict[str, Any]) -> str:
    distribution = result.get("selection_distribution", {})
    lines = []
    for key, value in distribution.items():
        if key == "candidate_count_histogram":
            continue
        if isinstance(value, (str, int, float, bool)):
            lines.append(f"- `{key}`：{value}")
        elif isinstance(value, dict) and all(
            isinstance(item, (str, int, float, bool)) for item in value.values()
        ):
            rendered = "、".join(f"{name}={item}" for name, item in value.items())
            lines.append(f"- `{key}`：{rendered}")
    return "\n".join(lines) or "- 機器收據沒有額外分布摘要。"


def _feature_table(result: dict[str, Any]) -> str:
    feature = result.get("selection_distribution", {}).get("feature_distribution", {})
    lines = [
        "| 結構特徵 | 最小值 | 中位數 | 平均值 | 最大值 |",
        "|---|---:|---:|---:|---:|",
    ]
    for key, label in (("pullback", "回調"), ("reward_risk", "Reward/risk")):
        row = feature.get(key, {})
        lines.append(
            f"| {label} | {_number(row.get('minimum')):.4f} | "
            f"{_number(row.get('median')):.4f} | {_number(row.get('mean')):.4f} | "
            f"{_number(row.get('maximum')):.4f} |"
        )
    return "\n".join(lines)


def _calendar_order_summary(result: dict[str, Any]) -> str:
    integrity = result.get("calendar_integrity", {})
    order_diagnostics = integrity.get("order_diagnostics", {})
    primary = order_diagnostics.get("primary", {})
    paths = result.get("paths", {})
    consistency = bool(integrity.get("protocol_calendar_internal_consistency"))
    exact_inputs_failed = any(
        row.get("id") == "exact_inputs" and not row.get("passed")
        for row in result.get("gates", [])
    )
    lines = [
        "| 路徑 | 預期子委託 | 實際子委託 | 差額 |",
        "|---|---:|---:|---:|",
    ]
    for path_id, row in primary.items():
        expected = int(_number(row.get("expected_total_orders")))
        actual = int(_number(row.get("actual_total_orders")))
        lines.append(
            f"| {paths.get(path_id, {}).get('label', path_id)} | {expected:,} | "
            f"{actual:,} | {actual - expected:+,} |"
        )
    ledgers = order_diagnostics.get("candidate_ledgers", {})
    ledger_lines = "\n".join(
        f"- `{name}`：{len(rows):,} 列已保存於機器收據。"
        for name, rows in ledgers.items()
    ) or "- 候選 ledger 尚未提供。"
    terminal_exposure = integrity.get("terminal_exposure", {})
    terminal_positions = integrity.get("terminal_position_count", {})
    terminal_zero = (
        bool(integrity.get("terminal_state_all_cash"))
        and all(_number(value) == 0.0 for value in terminal_exposure.values())
        and all(int(_number(value)) == 0 for value in terminal_positions.values())
    )
    order_table = "\n".join(lines)
    return f"""凍結協議的日曆敘述有不可回改的內部矛盾：表列由 2006-08-07 至 2026-07-31
共有 5,028 列，但實際比較交易期只有 **{int(_number(integrity.get('comparison_trade_sessions'))):,}**
列。為保留父收據，第 39 輪仍保存 2006-08-04 的 **{int(_number(integrity.get('pre_trade_cash_sessions'))):,}**
列成交前現金，總日曆才是 **{int(_number(integrity.get('sessions'))):,}** 列。系統沒有改寫協議；
`protocol_calendar_internal_consistency={str(consistency).lower()}`，因此 `exact_inputs` 門檻
**{'未通過' if exact_inputs_failed else '狀態異常，須人工覆核'}**。

十日事件實際最大 concurrency 為
**{int(_number(integrity.get('maximum_concurrent_ten_day_intervals')))}**，事前上限為 5；通過上限
不會抵銷上述日曆矛盾。

{order_table}

九路預期與實際子委託須完全相同。最終狀態
**{'全現金、零持倉' if terminal_zero else '未能證明全現金，禁止升格'}**；候選的 primary、
US$0.01 及 US$0.05 固定費 ledger 均只保存在機器收據，不在報告列出最新逐股名單：

{ledger_lines}"""


def _crisis_table(stresses: dict[str, Any], candidate_id: str) -> str:
    lines = [
        "| 年份 | 候選回報／最大跌幅 | QQQ 回報／最大跌幅 | 回報差 |",
        "|---|---:|---:|---:|",
    ]
    for year, paths in stresses.get("crisis_years", {}).items():
        candidate = paths.get(candidate_id, {})
        qqq = paths.get("qqq_buy_hold", {})
        candidate_return = _number(candidate.get("return"))
        qqq_return = _number(qqq.get("return"))
        lines.append(
            f"| {year} | {_signed_pct(candidate_return)}／"
            f"{_pct(_number(candidate.get('max_drawdown')))} | "
            f"{_signed_pct(qqq_return)}／{_pct(_number(qqq.get('max_drawdown')))} | "
            f"{_signed_pct(candidate_return - qqq_return)} |"
        )
    if len(lines) == 2:
        lines.append("| 收據未提供 | 0.00%／0.00% | 0.00%／0.00% | 0.00% |")
    return "\n".join(lines)


def _stress_summary(result: dict[str, Any], candidate_id: str) -> str:
    stresses = result.get("stresses", {})
    lines = []
    best = stresses.get("best_three_years_removed", {})
    if best:
        years = "、".join(map(str, best.get("removed_years", []))) or "未提供"
        lines.append(
            f"- 移除相對 QQQ 最佳三年 {years} 後，日均差 "
            f"{_number(best.get('mean_daily_difference')) * 10_000:+.2f} bp，NW t "
            f"{_number(best.get('newey_west', {}).get('t_stat')):.2f}。"
        )
    tail = stresses.get("favorable_46_events_removed", {})
    if tail:
        differences = tail.get("candidate_cagr_differences", {})
        rendered = "、".join(
            f"{baseline} {_signed_pct(_number(value))}"
            for baseline, value in differences.items()
        )
        lines.append(
            f"- 移除最有利 {tail.get('removed_event_count', 46)} 宗事件後："
            f"{rendered or '收據未提供 CAGR 差'}。"
        )
    proportional = stresses.get("costs", stresses.get("proportional_costs", {}))
    for cost, row in proportional.items():
        paths = row.get("paths", {})
        candidate = paths.get(candidate_id, {})
        lines.append(
            f"- 比例成本壓力 {cost}：候選 CAGR "
            f"{_pct(_number(candidate.get('cagr')))}。"
        )
    fixed = stresses.get("fixed_fees", stresses.get("fixed_child_order_fees", {}))
    for fee, row in fixed.items():
        paths = row.get("paths", {})
        candidate = paths.get(candidate_id, {})
        lines.append(
            f"- 每子委託固定費 {fee}：候選 CAGR "
            f"{_pct(_number(candidate.get('cagr')))}。"
        )
    regimes = stresses.get("known_at_qqq_regimes", {})
    for regime, row in regimes.items():
        mean = row.get(
            "average_event_increment",
            row.get("average_event_difference", row.get("mean_event_difference", 0.0)),
        )
        lines.append(
            f"- 訊號日已知 QQQ 組 `{regime}`：{int(_number(row.get('events')))} 宗，"
            f"平均事件增量 {_number(mean) * 10_000:+.2f} bp；只作診斷，不作市況開關。"
        )
    return "\n".join(lines) or "- 收據沒有固定壓力結果；不得據此宣稱通過。"


def _gate_list(result: dict[str, Any]) -> str:
    rendered = "\n".join(
        f"- {row.get('label', row.get('id', 'gate'))}："
        f"**{'通過' if row.get('passed') else '未通過'}**"
        for row in result.get("gates", [])
    )
    return rendered or "- 機器收據尚未提供完整門檻列；不得視為通過。"


def _control_list(result: dict[str, Any]) -> str:
    return "\n".join(
        f"- {row.get('id', '')} · `{row.get('label', '')}`："
        f"{'通過' if row.get('passed') else '未通過'}"
        for row in result.get("controls", [])
    )


def _attack_table(result: dict[str, Any]) -> str:
    lines = ["| 攻擊 | 單欄變異 | 預期錯誤碼 | 結果 |", "|---|---|---|---|"]
    for row in result.get("attacks", []):
        lines.append(
            f"| {row.get('id', '')} | {row.get('label', row.get('field', ''))} | "
            f"`{row.get('expected_error_code', '')}` | "
            f"{'拒收' if row.get('rejected') else '誤收'} |"
        )
    return "\n".join(lines)


def _report(result: dict[str, Any]) -> str:
    family = result.get("family", {})
    candidate_id = family.get("candidate_id", "lpr10_qqq_overlay")
    paths = result.get("paths", {})
    candidate = paths.get(candidate_id, {})
    qqq = paths.get("qqq_buy_hold", {})
    gate_summary = result.get("gate_summary", {})
    passed = int(_number(gate_summary.get("passed")))
    total = int(_number(gate_summary.get("total"), 22.0))
    failed = [
        row.get("label", row.get("id", "gate"))
        for row in result.get("gates", [])
        if not row.get("passed")
    ]
    input_row = result.get("input", {})
    decision = result.get("decision", {})
    controls = result.get("control_summary", {})
    attacks = result.get("attack_summary", {})
    receipt_complete = _receipt_complete(result)
    if receipt_complete:
        verdict = "全部通過但仍不得升格" if not failed else "未通過，不建立新策略"
        completion_notice = "機器收據的固定 family、壓力、門檻、控制及攻擊列完整。"
    else:
        verdict = "機器收據未完成，不可評價門檻"
        completion_notice = (
            "**完整性警告：固定九路、八比較、成本／固定費壓力、22 道門檻、"
            "48 道控制或攻擊仍有缺項；以下暫存欄位不得當作研究結果。**"
        )
    return f"""# 美股短線第 39 輪：龍頭回調—回升 10 日確認研究報告

生成日期：{result.get("generated_on", "未提供")}

資料期：{input_row.get("first_signal_date", "未提供")} 至
{input_row.get("last_exit_date", input_row.get("calendar_last_date", "未提供"))}

研究角色：同一批已見 survivor 股票的只讀反證；不是 point-in-time 回測、最新買入名單、
Paper 或實金指令。

{completion_notice}

## 結論一覽

本輪只測試事前固定的龍頭回調—回升結構：原 20 日 Top-7 中，訊號日同時符合 3%–16%
回調、收市回升及 reward/risk 不低於 1.60 的股票，每隻只佔事件槽位 1/7；其餘持有 QQQ。
訊號後下一個 session 調整開市買入，第 10 個 session 調整收市沽出。target 及 stop 只用作
訊號日結構計算，持有期不執行止賺或止蝕。

主要成本下，US$1,000 候選期末值為 **{_money(_number(candidate.get('terminal_usd')))}**、
CAGR **{_pct(_number(candidate.get('cagr')))}**、SHY 超額 Sharpe
**{_number(candidate.get('shy_excess_sharpe')):.2f}**、最大跌幅
**{_pct(_number(candidate.get('max_drawdown')))}**。QQQ 買入並持有期末值為
**{_money(_number(qqq.get('terminal_usd')))}**、CAGR **{_pct(_number(qqq.get('cagr')))}**。

二十二項事前門檻通過 **{passed}/{total}**，結論為 **{verdict}**。
{('未通過項目：' + '、'.join(failed) + '。') if failed else ''}

無論本輪數字如何，固定 `can_promote_from_this_round=false`、
`new_strategy_created=false`、`paper_status=all_cash_not_started`。短線 Paper 維持全現金、
持倉 **{int(_number(decision.get('paper_positions')))}**，實金動作 **US$0**。

## 選擇與特徵分布

{_selection_table(result)}

{_distribution_details(result)}

{_feature_table(result)}

逐事件收據須保留 ATR14、20／60 日收市高位、10 日低位、pullback、rebound、target、stop、
reward/risk、確認股票及 N/7 分配；報告不呈列最新逐股名單。

## 日曆、自洽性、concurrency 與委託帳

{_calendar_order_summary(result)}

## 九條固定完整資金路徑

{_path_table(result)}

候選與 matched 路徑使用相同 N、股票比例、D+1 開市、10-session 收市時鐘及比例成本。
正常替換完整計入 QQQ 沽出、股票買入、股票沽出及 QQQ 買回；固定費按真實子委託數收取，
不可為候選省略或向基準加入 ghost order。

## 八假說共同統計 family

{_family_table(result)}

八項比較共用 Newey–West lag 10、63-session circular blocks、20,000 條共同 bootstrap 路徑、
seed 39,202,608。全專案搜尋帳由 6,229 增至 6,237，沒有因結果重設。

## 比例成本、固定費及反集中壓力

{_stress_summary(result, candidate_id)}

比例成本與每子委託固定費是不同壓力，不得混算。US$0.01／US$0.05 只是 US$1,000 操作
診斷，不代表任何券商實際收費；模型亦未完整計入買賣差價、市場衝擊或稅項。

## 固定危機年份

{_crisis_table(result.get('stresses', {}), candidate_id)}

## 二十二項事前反證門檻

{_gate_list(result)}

任何一項未通過即 `not_rejected_by_round39=false`。即使 22/22，本輪仍是同一已見 survivor
樣本，不得建立 Paper 或實金策略。

## {int(_number(controls.get('total')))} 道固定控制

{_control_list(result)}

控制全部通過只證明程式遵守已推送協議，不證明未來盈利。

## {int(_number(attacks.get('total')))} 項單欄變異攻擊

{_attack_table(result)}

任何 OHLC、ATR、pullback、reward/risk、N/7、持有期、成本、固定費、family、統計、Paper
或實金權限漂移都須命中穩定錯誤碼並 fail closed。

## 市場與數據邊界

資料最後日期不是即市行情。股票仍是 2026 現時 survivor cohort，欠缺逐期成分、永久證券
ID、可靠退市／退出經濟、歷史公司行動及公告時間。調整 OHLC、分數股與 US$1,000 只供
比例研究，不能冒充真實券商成交或稅後結果。

正式就緒仍為 **{decision.get('formal_readiness', '1/18')}**，point-in-time
**{decision.get('point_in_time_readiness', '1/20')}**，合資格 provider package 0，正式策略
run 0。下一個可升格步驟仍是獲授權逐期成分、永久 ID、公司行動及退市資料，原樣執行既有
正式預先登記；不得用本輪結果重選參數。

## 可重播檔案

- [第 39 輪事前協議](SHORT_TERM_LEADER_PULLBACK_REBOUND_PROTOCOL.md)
- `artifacts/short_term_leader_pullback_rebound_validation.json`
- `site/data/short-term-leader-pullback-rebound.json`
"""


def main() -> None:
    result = run_leader_pullback_rebound(ROOT)
    result["receipt_float_decimal_places"] = RECEIPT_FLOAT_DECIMAL_PLACES
    canonical = _canonicalize_floats(result)
    payload = json.dumps(canonical, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ARTIFACT.parent.mkdir(parents=True, exist_ok=True)
    SITE_DATA.parent.mkdir(parents=True, exist_ok=True)
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    ARTIFACT.write_text(payload, encoding="utf-8")
    SITE_DATA.write_text(payload, encoding="utf-8")
    REPORT.write_text(_report(canonical), encoding="utf-8")
    print(
        f"wrote {ARTIFACT.relative_to(ROOT)}, {SITE_DATA.relative_to(ROOT)}, "
        f"{REPORT.relative_to(ROOT)}"
    )


if __name__ == "__main__":
    main()
