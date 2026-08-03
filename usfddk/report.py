from __future__ import annotations

import html
import json
import math
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from usfddk.metrics import annual_returns
from usfddk.models import BacktestResult, ContractResult, MarketPanel

COLORS = [
    "#61d3a5",
    "#8fb8ff",
    "#ffbd69",
    "#d39cff",
    "#ff7f7f",
    "#70d6ff",
    "#c9e265",
]

REPORT_REFERENCE_HTML = """
<p class="footer report-reference"><b>報告架構參考：</b>
<a href="https://github.com/appr1ciat1/tst_wocker">tst_wocker</a>、
<a href="https://github.com/appr1ciat1/tw-block-warrant">tw-block-warrant</a>、
<a href="https://github.com/appr1ciat1/tst_wocker_filter_lab">tst_wocker_filter_lab</a>。
只參考報告分層、每日狀態及前瞻稽核方式；美股數據、規則與結果由本專案獨立計算。中文採香港金融市場慣用詞。</p>
"""


def _with_report_references(content: str) -> str:
    """Append source and terminology provenance to every human-readable report."""
    marker = "</main></body></html>"
    if marker not in content or REPORT_REFERENCE_HTML.strip() in content:
        return content
    return content.replace(marker, f"{REPORT_REFERENCE_HTML}{marker}")


def _pct(value: float, digits: int = 1) -> str:
    if value is None or not np.isfinite(value):
        return "—"
    return f"{value * 100:.{digits}f}%"


def _num(value: float, digits: int = 2) -> str:
    if value is None or not np.isfinite(value):
        return "—"
    return f"{value:.{digits}f}"


def _equity_svg(results: list[BacktestResult], width: int = 980, height: int = 390) -> str:
    series: list[tuple[str, pd.Series]] = []
    for result in results:
        clean = result.equity.dropna()
        if len(clean) > 1:
            series.append((result.name, clean / clean.iloc[0]))
    if not series:
        return ""
    all_index = sorted(set().union(*(set(s.index) for _, s in series)))
    x0, x1 = pd.Timestamp(all_index[0]).value, pd.Timestamp(all_index[-1]).value
    positive = np.concatenate([s[s > 0].to_numpy() for _, s in series])
    y0, y1 = float(np.log(positive.min())), float(np.log(positive.max()))
    pad_l, pad_r, pad_t, pad_b = 58, 20, 18, 82
    chart_w, chart_h = width - pad_l - pad_r, height - pad_t - pad_b

    def point(stamp: pd.Timestamp, value: float) -> tuple[float, float]:
        x = pad_l + (stamp.value - x0) / max(x1 - x0, 1) * chart_w
        y = pad_t + (y1 - math.log(max(value, 1e-12))) / max(y1 - y0, 1e-12) * chart_h
        return x, y

    lines = [f'<svg viewBox="0 0 {width} {height}" role="img" aria-label="策略組合價值曲線">']
    for fraction in (0.0, 0.25, 0.5, 0.75, 1.0):
        y = pad_t + fraction * chart_h
        label = math.exp(y1 - fraction * (y1 - y0))
        lines.append(
            f'<line x1="{pad_l}" y1="{y:.1f}" x2="{width - pad_r}" y2="{y:.1f}" class="grid"/>'
        )
        lines.append(
            f'<text x="{pad_l - 8}" y="{y + 4:.1f}" text-anchor="end" class="axis">{label:.1f}×</text>'
        )
    for idx, (name, s) in enumerate(series):
        step = max(1, len(s) // 900)
        sampled = s.iloc[::step]
        if sampled.index[-1] != s.index[-1]:
            sampled = pd.concat([sampled, s.iloc[-1:]])
        coords = [point(pd.Timestamp(day), float(value)) for day, value in sampled.items()]
        path = " ".join(
            ("M" if i == 0 else "L") + f"{x:.1f},{y:.1f}" for i, (x, y) in enumerate(coords)
        )
        color = COLORS[idx % len(COLORS)]
        lines.append(f'<path d="{path}" fill="none" stroke="{color}" stroke-width="2.3"/>')
        legend_x = pad_l + (idx % 4) * 220
        legend_y = height - 38 + (idx // 4) * 21
        lines.append(f'<circle cx="{legend_x}" cy="{legend_y}" r="5" fill="{color}"/>')
        lines.append(
            f'<text x="{legend_x + 10}" y="{legend_y + 4}" class="legend">{html.escape(name)}</text>'
        )
    lines.append(
        f'<text x="{pad_l}" y="{height - pad_b + 18}" class="axis">{pd.Timestamp(all_index[0]).date()}</text>'
    )
    lines.append(
        f'<text x="{width - pad_r}" y="{height - pad_b + 18}" text-anchor="end" class="axis">{pd.Timestamp(all_index[-1]).date()}</text>'
    )
    lines.append("</svg>")
    return "".join(lines)


def _metrics_table(results: list[BacktestResult]) -> str:
    rows = []
    for result in results:
        m = result.metrics
        rows.append(
            "<tr>"
            f"<th>{html.escape(result.name)}</th>"
            f"<td>{_pct(m['total_return'])}</td><td>{_pct(m['cagr'])}</td>"
            f"<td>{_pct(m['volatility'])}</td><td>{_num(m['sharpe'])}</td>"
            f"<td>{_num(m['sortino'])}</td><td>{_pct(m['max_drawdown'])}</td>"
            f"<td>{_num(m['calmar'])}</td>"
            f"<td>{_pct(m['turnover'])}</td><td>{result.diagnostics['rebalance_count']}</td>"
            "</tr>"
        )
    return "".join(rows)


def _allocation_cards(results: list[BacktestResult]) -> str:
    cards = []
    for result in results:
        positions = result.current_target[result.current_target > 0]
        pills = "".join(
            f'<span class="pill"><b>{html.escape(str(ticker))}</b> {_pct(float(weight))}</span>'
            for ticker, weight in positions.items()
        )
        cards.append(
            f'<article class="allocation"><h3>{html.escape(result.name)}</h3>'
            f'<div class="pills">{pills or "尚無有效訊號"}</div>'
            '<p class="fine">這是最近月末收市訊號的目標權重；模型成交時點為下一交易日開市。</p></article>'
        )
    return "".join(cards)


def _screen_rows(screen: pd.DataFrame, limit: int = 15) -> str:
    rows = []
    for ticker, row in screen.head(limit).iterrows():
        trend_class = "good" if float(row["trend_200"]) >= 0 else "bad"
        rows.append(
            "<tr>"
            f"<td><b>{html.escape(str(ticker))}</b><small>{html.escape(str(row['name']))}</small></td>"
            f"<td>{html.escape(str(row['sector']))}</td>"
            f"<td>{_num(float(row['score']), 3)}</td>"
            f"<td>{_pct(float(row['mom_12_1']))}</td>"
            f'<td class="{trend_class}">{_pct(float(row["trend_200"]))}</td>'
            f"<td>{_pct(float(row['ann_vol']))}</td>"
            "</tr>"
        )
    return "".join(rows)


def _validation_rows(validations: dict[str, Any]) -> str:
    rows = []
    for label, item in validations.get("comparisons", {}).items():
        if abs(item["active_return_t"]) < 1.96:
            verdict = "未達統計顯著"
        elif item["active_return_t"] > 0:
            verdict = "顯著領先"
        else:
            verdict = "顯著落後"
        rows.append(
            "<tr>"
            f"<th>{html.escape(label)}</th><td>{_pct(item['cagr_difference'])}</td>"
            f"<td>{_pct(item['active_return_nw'])}</td><td>{_num(item['active_return_t'])}</td>"
            f"<td>{verdict}</td></tr>"
        )
    return "".join(rows)


def _bootstrap_rows(validations: dict[str, Any]) -> str:
    rows = []
    for label, ci in validations.get("bootstrap", {}).items():
        rows.append(
            f"<tr><th>{html.escape(label)}</th><td>{_pct(ci['median'])}</td>"
            f"<td>[{_pct(ci['low'])}, {_pct(ci['high'])}]</td><td>{_pct(ci['p_below_zero'])}</td></tr>"
        )
    return "".join(rows)


def _sensitivity_rows(validations: dict[str, Any]) -> str:
    rows = []
    for item in validations.get("sensitivity", []):
        rows.append(
            f"<tr><td>{item['lookback']}</td><td>{item['top_k']}</td>"
            f"<td>{item['cost_bps']:.0f}</td><td>{_pct(item['cagr'])}</td>"
            f"<td>{_num(item['sharpe'])}</td><td>{_pct(item['max_drawdown'])}</td></tr>"
        )
    return "".join(rows)


def _candidate_neighborhood_rows(validations: dict[str, Any]) -> str:
    rows = []
    candidate = validations.get("research_candidate", {})
    selected = float(candidate.get("frozen_parameters", {}).get("core_share", 0.75))
    for item in candidate.get("neighborhood", []):
        share = float(item["core_share"])
        marker = "正式" if math.isclose(share, selected) else "鄰域"
        rows.append(
            f"<tr><th>{share:.0%}</th><td>{marker}</td><td>{_pct(item['cagr'])}</td>"
            f"<td>{_num(item['sharpe'])}</td><td>{_num(item['excess_sharpe_vs_shy'])}</td>"
            f"<td>{_pct(item['max_drawdown'])}</td>"
            f"<td>{_pct(item['turnover'])}</td></tr>"
        )
    return "".join(rows)


def _candidate_cost_rows(validations: dict[str, Any]) -> str:
    rows = []
    for item in validations.get("research_candidate", {}).get("cost_sensitivity", []):
        rows.append(
            f"<tr><th>{float(item['cost_bps']):g}</th><td>{_pct(item['cagr'])}</td>"
            f"<td>{_num(item['sharpe'])}</td><td>{_num(item['excess_sharpe_vs_shy'])}</td>"
            f"<td>{_pct(item['max_drawdown'])}</td></tr>"
        )
    return "".join(rows)


def _walk_forward_rows(validations: dict[str, Any]) -> str:
    rows = []
    walk = validations.get("research_candidate", {}).get("walk_forward", {})
    for item in walk.get("folds", []):
        metrics = item.get("test_metrics", {})
        rows.append(
            f"<tr><th>{html.escape(item['test_start'])}–{html.escape(item['test_end'])}</th>"
            f"<td>{float(item['selected_core_share']):.0%}</td>"
            f"<td>{_pct(metrics.get('cagr', float('nan')))}</td>"
            f"<td>{_num(metrics.get('sharpe', float('nan')))}</td>"
            f"<td>{_num(metrics.get('excess_sharpe_vs_shy', float('nan')))}</td>"
            f"<td>{_pct(metrics.get('max_drawdown', float('nan')))}</td></tr>"
        )
    return "".join(rows)


def _candidate_evidence(validations: dict[str, Any]) -> str:
    item = validations.get("research_candidate", {})
    metrics = item.get("candidate_metrics", {})
    excess = item.get("excess_return_metrics", {})
    psr = item.get("probabilistic_sharpe_above_1", {})
    dsr = item.get("deflated_sharpe", {})
    pbo = item.get("local_family_pbo", {})
    walk = item.get("walk_forward", {}).get("overall_metrics", {})
    confirmed = bool(item.get("statistically_confirmed", False))
    zero_rate_passed = bool(item.get("zero_rate_point_estimate_gate_passed", False))
    conventional_passed = bool(item.get("conventional_point_estimate_gate_passed", False))
    if confirmed:
        verdict = "統計確認關卡通過"
        explanation = "點估計、搜尋懲罰與走勢外關卡均通過。"
        klass = "ok"
    elif zero_rate_passed and not conventional_passed:
        verdict = "只有零利率口徑 Sharpe > 1；標準超額 Sharpe 未通過"
        explanation = (
            "原始回報除以波幅的數字為 1.07，但扣除 SHY 總回報後只有 0.80。"
            "這能繼續 paper 研究，不能算完成標準 Sharpe > 1 目標。"
        )
        klass = "warn"
    elif conventional_passed:
        verdict = "超額 Sharpe > 1 的研究候選，但尚未統計確認"
        explanation = (
            "20 年點估計與穩健性門檻通過；然而真實 Sharpe 高於 1 與搜尋後 DSR "
            "尚未達 95%，因此不能宣稱已證實。"
        )
        klass = "warn"
    else:
        verdict = "研究候選未通過預設門檻"
        explanation = "保留結果作為負面證據，不升級為 paper 主策略。"
        klass = "warn"
    return f"""
    <div class="{klass}"><b>{html.escape(verdict)}</b><br>{html.escape(explanation)}</div>
    <div class="grid4 evidence-grid">
      <div class="kpi"><span>零利率 Sharpe</span><strong>{_num(metrics.get("sharpe", float("nan")))}</strong></div>
      <div class="kpi"><span>SHY 超額 Sharpe</span><strong>{_num(excess.get("excess_sharpe_vs_shy", float("nan")))}</strong></div>
      <div class="kpi"><span>P（超額 Sharpe &gt; 1）</span><strong>{_pct(psr.get("probability", float("nan")))}</strong></div>
      <div class="kpi"><span>超額 DSR｜6,000 次</span><strong>{_pct(dsr.get("probability", float("nan")))}</strong></div>
    </div>
    <p class="fine">走勢外零利率／SHY 超額 Sharpe：{_num(walk.get("sharpe", float("nan")))}／{_num(walk.get("excess_sharpe_vs_shy", float("nan")))}。局部參數族超額回報 PBO {_pct(pbo.get("pbo", float("nan")))}；越低越好。</p>
    """


def _growth_guard_evidence(validations: dict[str, Any]) -> str:
    item = validations.get("growth_guard", {})
    strategy = item.get("strategy_metrics", {})
    spy = item.get("spy_metrics", {})
    qqq = item.get("qqq_metrics", {})
    rolling = item.get("rolling_five_year", {}).get("summary", {})
    nw = item.get("active_return_newey_west", {})
    dsr = item.get("active_deflated_sharpe", {})
    historical = bool(item.get("historical_gate_passed", False))
    statistical = bool(item.get("statistically_confirmed", False))
    verdict = (
        "歷史門檻與統計確認皆通過"
        if historical and statistical
        else "20 年歷史門檻通過；統計與 LIVE 尚未確認"
        if historical
        else "歷史門檻未通過"
    )
    klass = "ok" if statistical else "warn"
    return f"""
    <div class="{klass}"><b>{html.escape(verdict)}</b><br>
    80% QQQ 成長衛星＋20% 多資產趨勢核心。這個凍結回測可以標成研究候選，不能標成已證實會跑贏 ETF。</div>
    <div class="grid4 evidence-grid">
      <div class="kpi"><span>候選 CAGR</span><strong>{_pct(strategy.get("cagr", float("nan")))}</strong><small>SPY {_pct(spy.get("cagr", float("nan")))}</small></div>
      <div class="kpi"><span>最大跌幅</span><strong>{_pct(strategy.get("max_drawdown", float("nan")))}</strong><small>SPY {_pct(spy.get("max_drawdown", float("nan")))}</small></div>
      <div class="kpi"><span>5 年滾動勝率</span><strong>{_pct(rolling.get("cagr_win_fraction", float("nan")))}</strong><small>相對 SPY</small></div>
      <div class="kpi"><span>超額回報 NW t</span><strong>{_num(nw.get("t_stat", float("nan")))}</strong><small>需達 1.96；DSR {_pct(dsr.get("probability", float("nan")))}</small></div>
    </div>
    <p class="fine">QQQ 買入並持有 CAGR {_pct(qqq.get("cagr", float("nan")))}、MDD {_pct(qqq.get("max_drawdown", float("nan")))}。候選是以降低最大跌幅換取部分 QQQ 回報，不宣稱每個期間都領先。</p>
    """


def _volatility_guard_evidence(validations: dict[str, Any]) -> str:
    item = validations.get("volatility_guard", {})
    strategy = item.get("strategy_metrics", {})
    spy = item.get("spy_metrics", {})
    qqq = item.get("qqq_metrics", {})
    passive = item.get("passive_90_10_metrics", {})
    incumbent = item.get("incumbent_growth_guard_metrics", {})
    rolling = item.get("rolling_five_year", {}).get("summary", {})
    nw = item.get("active_return_newey_west", {})
    dsr = item.get("active_deflated_sharpe", {})
    exposure = item.get("exposure_statistics", {})
    historical = bool(item.get("historical_gate_passed", False))
    exposure_control = bool(item.get("exposure_control_passed", False))
    statistical = bool(item.get("statistically_confirmed", False))
    verdict = (
        "SPY 歷史門檻通過，但 90/10 持倉比率控制未通過：只能 Paper 驗證"
        if historical and not exposure_control
        else "歷史、持倉比率控制與統計確認皆通過"
        if historical and exposure_control and statistical
        else "歷史與持倉比率控制通過；統計與 v2 LIVE 尚未確認"
        if historical and exposure_control
        else "歷史門檻未通過"
    )
    return f"""
    <div class="{"ok" if statistical and exposure_control else "warn"}"><b>{html.escape(verdict)}</b><br>
    每月用 QQQ 最近 21 個交易日波幅決定無槓桿持倉比率，目標年率化波幅 18%；未使用的權重放 SHY。它改善 v1，但仍是新搜尋後選出的候選。</div>
    <div class="grid4 evidence-grid">
      <div class="kpi"><span>v2 CAGR</span><strong>{_pct(strategy.get("cagr", float("nan")))}</strong><small>v1 {_pct(incumbent.get("cagr", float("nan")))}</small></div>
      <div class="kpi"><span>最大跌幅</span><strong>{_pct(strategy.get("max_drawdown", float("nan")))}</strong><small>v1 {_pct(incumbent.get("max_drawdown", float("nan")))}</small></div>
      <div class="kpi"><span>5 年滾動勝率</span><strong>{_pct(rolling.get("cagr_win_fraction", float("nan")))}</strong><small>最近 {_pct(rolling.get("latest_cagr_difference", float("nan")))} vs SPY</small></div>
      <div class="kpi"><span>超額回報 NW t</span><strong>{_num(nw.get("t_stat", float("nan")))}</strong><small>需達 1.96；DSR {_pct(dsr.get("probability", float("nan")))}</small></div>
    </div>
    <p class="fine">SPY CAGR {_pct(spy.get("cagr", float("nan")))}／MDD {_pct(spy.get("max_drawdown", float("nan")))}；QQQ CAGR {_pct(qqq.get("cagr", float("nan")))}／MDD {_pct(qqq.get("max_drawdown", float("nan")))}；被動 90/10 CAGR {_pct(passive.get("cagr", float("nan")))}／MDD {_pct(passive.get("max_drawdown", float("nan")))}。歷史平均 QQQ 權重 {_pct(exposure.get("mean_qqq_weight", float("nan")))}。</p>
    """


def _v3_evidence(validations: dict[str, Any]) -> str:
    item = validations.get("trend_confirmed_guard_v3", {})
    strategy = item.get("strategy_metrics", {})
    qqq = item.get("qqq_metrics", {})
    matched = item.get("matched_96_4_metrics", {})
    proxy = item.get("proxy_validation", {})
    proxy_strategy = proxy.get("strategy_metrics", {})
    proxy_benchmark = proxy.get("benchmark_metrics", {})
    nw = item.get("active_return_newey_west", {})
    dsr = item.get("active_deflated_sharpe", {})
    return f"""
    <div class="warn"><b>主樣本通過，較舊代理期未通過：不升級主訊號</b><br>
    v3 在成長 regime 持有 100% QQQ；只有 12 個月趨勢連續兩個月為負後，才以 18%／21 日波幅政策降風險。代理期的有效滾動勝率失敗，因此只建立隔離 Paper。</div>
    <div class="grid4 evidence-grid">
      <div class="kpi"><span>v3 CAGR</span><strong>{_pct(strategy.get("cagr", float("nan")))}</strong><small>QQQ {_pct(qqq.get("cagr", float("nan")))}</small></div>
      <div class="kpi"><span>v3 最大跌幅</span><strong>{_pct(strategy.get("max_drawdown", float("nan")))}</strong><small>QQQ {_pct(qqq.get("max_drawdown", float("nan")))}</small></div>
      <div class="kpi"><span>96/4 持倉比率基準</span><strong>{_pct(matched.get("cagr", float("nan")))}</strong><small>MDD {_pct(matched.get("max_drawdown", float("nan")))}</small></div>
      <div class="kpi"><span>相對 QQQ NW t</span><strong>{_num(nw.get("t_stat", float("nan")))}</strong><small>DSR {_pct(dsr.get("probability", float("nan")))}</small></div>
    </div>
    <p class="fine">1986–2006 Nasdaq-100 價格指數代理：v3 CAGR {_pct(proxy_strategy.get("cagr", float("nan")))}、buy-and-hold {_pct(proxy_benchmark.get("cagr", float("nan")))}；完整期較佳，但代理期前十年與有效滾動一致性未過。</p>
    """


def _v3_gate_rows(validations: dict[str, Any]) -> str:
    item = validations.get("trend_confirmed_guard_v3", {})
    sections = (
        (
            "QQQ 主門檻",
            item.get("historical_gates", {}),
            {
                "full_cagr_above_qqq": "全期 CAGR 高於 QQQ",
                "sharpe_above_qqq": "Sharpe 高於 QQQ",
                "drawdown_improvement_at_least_15pp_vs_qqq": "最大跌幅至少改善 15pp",
                "both_ten_year_halves_beat_qqq": "前後十年都高於 QQQ",
                "still_beats_qqq_at_25bps": "25 bps 仍高於 QQQ",
                "positive_average_daily_active_return_vs_qqq": "平均每日主動回報為正",
                "confirmation_neighborhood_all_beats_qqq": "1／2／3 月確認全期皆高於 QQQ",
                "confirmation_neighborhood_all_improves_drawdown_10pp": "1／2／3 月確認最大跌幅皆改善 10pp",
                "confirmation_neighborhood_all_beats_qqq_at_25bps": "1／2／3 月確認在 25 bps 皆領先",
            },
        ),
        (
            "96/4 持倉比率控制",
            item.get("exposure_control_gates", {}),
            {
                "full_cagr_above_matched_96_4": "全期 CAGR 高於 96/4",
                "sharpe_above_matched_96_4": "Sharpe 高於 96/4",
                "drawdown_improvement_at_least_10pp_vs_matched_96_4": "最大跌幅至少改善 10pp",
                "both_ten_year_halves_beat_matched_96_4": "前後十年都高於 96/4",
                "rolling_five_year_win_rate_vs_matched_at_least_75pct": "5 年有效勝率至少 75%",
                "still_beats_matched_96_4_at_25bps": "25 bps 仍高於 96/4",
                "positive_average_daily_active_return_vs_matched_96_4": "平均每日主動回報為正",
            },
        ),
        (
            "1986–2006 代理期",
            item.get("proxy_validation", {}).get("gates", {}),
            {
                "full_cagr_above_ndx": "完整期 CAGR 高於 NDX",
                "sharpe_above_ndx": "Sharpe 高於 NDX",
                "drawdown_improvement_at_least_10pp": "最大跌幅至少改善 10pp",
                "rolling_five_year_win_rate_at_least_60pct": "5 年有效勝率至少 60%",
                "still_beats_ndx_at_50bps": "50 bps 仍高於 NDX",
                "positive_average_daily_active_return": "平均每日主動回報為正",
            },
        ),
    )
    rows: list[str] = []
    for section, gates, labels in sections:
        for key, label in labels.items():
            passed = bool(gates.get(key))
            rows.append(
                f"<tr><th>{html.escape(section)}</th><td>{html.escape(label)}</td>"
                f'<td class="{"good" if passed else "bad"}">{"通過" if passed else "未通過"}</td></tr>'
            )
    return "".join(rows)


def _v3_family_rows(validations: dict[str, Any]) -> str:
    rows: list[str] = []
    for item in validations.get("trend_confirmed_guard_v3", {}).get("family", []):
        months = int(item["confirmation_months"])
        rows.append(
            f"<tr><th>{months} 個月</th><td>{'凍結政策' if months == 2 else '鄰域'}</td>"
            f"<td>{_pct(item['cagr'])}</td><td>{_num(item['sharpe'])}</td>"
            f"<td>{_pct(item['max_drawdown'])}</td>"
            f"<td>{_pct(item['cagr_difference_vs_qqq'])}</td>"
            f"<td>{_pct(item['cost_25bps_cagr_difference_vs_qqq'])}</td></tr>"
        )
    return "".join(rows)


def _volatility_gate_rows(validations: dict[str, Any]) -> str:
    labels = {
        "full_cagr_at_least_spy_plus_3pp": "全期 CAGR 至少領先 SPY 3 個百分點",
        "sharpe_above_spy": "Sharpe 高於 SPY",
        "drawdown_improvement_at_least_15pp": "最大跌幅改善至少 15 個百分點",
        "both_ten_year_halves_beat_spy": "前後兩個十年都勝過 SPY",
        "rolling_five_year_win_rate_at_least_90pct": "5 年滾動勝率至少 90%",
        "latest_five_year_window_beats_spy": "最近 5 年視窗仍勝過 SPY",
        "still_beats_spy_at_100bps": "成本提高到 100 bps 仍領先",
        "fixed_policy_2012_beats_spy": "固定政策 2012 至今仍領先",
        "improves_incumbent_cagr_and_drawdown": "同時改善 v1 的 CAGR 與最大跌幅",
        "average_qqq_weight_no_more_than_90pct": "歷史平均 QQQ 權重不超過 90%",
    }
    gates = validations.get("volatility_guard", {}).get("historical_gates", {})
    return "".join(
        f'<tr><th>{html.escape(label)}</th><td class="{"good" if gates.get(key) else "bad"}">{"通過" if gates.get(key) else "未通過"}</td></tr>'
        for key, label in labels.items()
    )


def _volatility_family_rows(validations: dict[str, Any]) -> str:
    item = validations.get("volatility_guard", {})
    frozen = item.get("frozen_parameters", {})
    selected_window = int(frozen.get("realized_volatility_window_sessions", 21))
    selected_target = float(frozen.get("target_annualized_volatility", 0.18))
    rows = []
    for row in item.get("family", []):
        window = int(row["volatility_window"])
        target = float(row["target_volatility"])
        role = (
            "凍結政策"
            if window == selected_window and math.isclose(target, selected_target)
            else "鄰域"
        )
        rows.append(
            f"<tr><th>{window}</th><td>{_pct(target)}</td><td>{role}</td>"
            f"<td>{_pct(row['cagr'])}</td><td>{_num(row['sharpe'])}</td>"
            f"<td>{_pct(row['max_drawdown'])}</td><td>{_pct(row['cagr_difference_vs_spy'])}</td></tr>"
        )
    return "".join(rows)


def _exposure_control_gate_rows(validations: dict[str, Any]) -> str:
    labels = {
        "full_cagr_above_passive_90_10": "全期 CAGR 高於被動 90/10",
        "sharpe_above_passive_90_10": "Sharpe 高於被動 90/10",
        "drawdown_improvement_at_least_10pp_vs_passive_90_10": ("最大跌幅至少改善 10 個百分點"),
        "both_ten_year_halves_beat_passive_90_10": "前後兩個十年都勝過被動 90/10",
        "rolling_five_year_win_rate_vs_passive_at_least_75pct": ("5 年滾動勝率至少 75%"),
        "still_beats_passive_90_10_at_25bps": "成本提高到 25 bps 仍領先",
        "positive_average_daily_active_return_vs_passive_90_10": ("平均每日超額回報為正"),
    }
    gates = validations.get("volatility_guard", {}).get("exposure_control_gates", {})
    return "".join(
        f'<tr><th>{html.escape(label)}</th><td class="{"good" if gates.get(key) else "bad"}">{"通過" if gates.get(key) else "未通過"}</td></tr>'
        for key, label in labels.items()
    )


def _volatility_cost_rows(validations: dict[str, Any]) -> str:
    return "".join(
        f"<tr><th>{float(item['cost_bps']):g}</th><td>{_pct(item['cagr'])}</td>"
        f"<td>{_num(item['sharpe'])}</td><td>{_pct(item['max_drawdown'])}</td>"
        f"<td>{_pct(item['cagr_difference_vs_spy'])}</td>"
        f"<td>{_pct(item['passive_90_10_cagr'])}</td>"
        f"<td>{_pct(item['cagr_difference_vs_passive_90_10'])}</td></tr>"
        for item in validations.get("volatility_guard", {}).get("cost_sensitivity", [])
    )


def _growth_gate_rows(validations: dict[str, Any]) -> str:
    labels = {
        "full_cagr_at_least_spy_plus_3pp": "全期 CAGR 至少領先 SPY 3 個百分點",
        "sharpe_above_spy": "Sharpe 高於 SPY",
        "drawdown_improvement_at_least_10pp": "最大跌幅改善至少 10 個百分點",
        "both_ten_year_halves_beat_spy": "前後兩個十年都勝過 SPY",
        "rolling_five_year_win_rate_at_least_85pct": "5 年滾動勝率至少 85%",
        "still_beats_spy_at_50bps": "成本提高到 50 bps 仍領先",
        "walk_forward_beats_spy": "固定政策 2012 至今仍領先",
    }
    gates = validations.get("growth_guard", {}).get("historical_gates", {})
    return "".join(
        f'<tr><th>{html.escape(label)}</th><td class="{"good" if gates.get(key) else "bad"}">{"通過" if gates.get(key) else "未通過"}</td></tr>'
        for key, label in labels.items()
    )


def _growth_family_rows(validations: dict[str, Any]) -> str:
    item = validations.get("growth_guard", {})
    selected = float(item.get("frozen_parameters", {}).get("core_share", 0.20))
    rows = []
    for row in item.get("family", []):
        core = float(row["core_share"])
        role = "凍結政策" if math.isclose(core, selected) else "鄰域"
        rows.append(
            f"<tr><th>{core:.0%}</th><td>{1 - core:.0%}</td><td>{role}</td>"
            f"<td>{_pct(row['cagr'])}</td><td>{_num(row['sharpe'])}</td>"
            f"<td>{_pct(row['max_drawdown'])}</td><td>{_pct(row['cagr_difference_vs_spy'])}</td></tr>"
        )
    return "".join(rows)


def _growth_cost_rows(validations: dict[str, Any]) -> str:
    rows = []
    for item in validations.get("growth_guard", {}).get("cost_sensitivity", []):
        rows.append(
            f"<tr><th>{float(item['cost_bps']):g}</th><td>{_pct(item['cagr'])}</td>"
            f"<td>{_num(item['sharpe'])}</td><td>{_pct(item['max_drawdown'])}</td>"
            f"<td>{_pct(item['cagr_difference_vs_spy'])}</td></tr>"
        )
    return "".join(rows)


def _growth_walk_rows(validations: dict[str, Any]) -> str:
    rows = []
    walk = validations.get("growth_guard", {}).get("walk_forward", {})
    for item in walk.get("folds", []):
        metrics = item.get("test_metrics", {})
        rows.append(
            f"<tr><th>{html.escape(item['test_start'])}–{html.escape(item['test_end'])}</th>"
            f"<td>{float(item['selected_core_share']):.0%}</td>"
            f"<td>{_pct(metrics.get('cagr', float('nan')))}</td>"
            f"<td>{_num(metrics.get('sharpe', float('nan')))}</td>"
            f"<td>{_pct(metrics.get('max_drawdown', float('nan')))}</td>"
            f"<td>{_pct(item.get('test_cagr_difference_vs_spy', float('nan')))}</td></tr>"
        )
    return "".join(rows)


def _search_audit_rows(validations: dict[str, Any]) -> str:
    rows = []
    audit = validations.get("research_candidate", {}).get("search_audit", {})
    for item in audit.get("exploratory_family_summaries", []):
        note = str(item.get("note", "—"))
        rows.append(
            f"<tr><th>{html.escape(str(item['family']))}</th>"
            f"<td>{int(item['evaluated'])}</td><td>{_num(float(item.get('best_sharpe', float('nan'))))}</td>"
            f"<td>{html.escape(note)}</td></tr>"
        )
    return "".join(rows)


def _annual_rows(results: list[BacktestResult]) -> str:
    columns = {result.name: annual_returns(result.returns) for result in results}
    frame = pd.DataFrame(columns).sort_index(ascending=False)
    rows: list[str] = []
    for year, values in frame.iterrows():
        cells = "".join(f"<td>{_pct(float(values[result.name]))}</td>" for result in results)
        year_label = f"{int(year)} YTD" if year == frame.index.max() else str(int(year))
        rows.append(f"<tr><th>{year_label}</th>{cells}</tr>")
    return "".join(rows)


def _subperiod_rows(validations: dict[str, Any], results: list[BacktestResult]) -> str:
    labels: list[str] = []
    for periods in validations.get("subperiods", {}).values():
        labels.extend(label for label in periods if label not in labels)
    rows = []
    for label in labels:
        cells = []
        for result in results:
            item = validations.get("subperiods", {}).get(result.name, {}).get(label, {})
            cells.append(
                f"<td>{_pct(item.get('cagr', float('nan')))} / "
                f"{_num(item.get('sharpe', float('nan')))} / "
                f"{_pct(item.get('max_drawdown', float('nan')))}</td>"
            )
        rows.append(f"<tr><th>{html.escape(label)}</th>{''.join(cells)}</tr>")
    return "".join(rows)


def _stress_rows(validations: dict[str, Any], results: list[BacktestResult]) -> str:
    rows = []
    for label, period in validations.get("stress_periods", {}).items():
        cells = []
        for result in results:
            item = period.get(result.name, {})
            cells.append(
                f"<td>{_pct(item.get('return', float('nan')))} / "
                f"{_pct(item.get('max_drawdown', float('nan')))}</td>"
            )
        rows.append(f"<tr><th>{html.escape(label)}</th>{''.join(cells)}</tr>")
    return "".join(rows)


def build_cross_market_report(destination: str | Path, audit: dict[str, Any]) -> Path:
    """Write a standalone, human-readable receipt for the frozen v3 market test."""
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    market_rows: list[str] = []
    receipt_rows: list[str] = []
    for item in audit["markets"].values():
        rolling = item["rolling_five_year"]["summary"]
        market_rows.append(
            "<tr>"
            f"<th>{html.escape(item['market'])}<small>{html.escape(item['index'])}</small></th>"
            f"<td>{_pct(item['strategy_metrics']['cagr'], 2)}</td>"
            f"<td>{_pct(item['benchmark_metrics']['cagr'], 2)}</td>"
            f"<td class={'pass' if item['cagr_difference'] > 0 else 'fail'}>"
            f"{_pct(item['cagr_difference'], 2)}</td>"
            f"<td>{_num(item['strategy_metrics']['sharpe'])} / "
            f"{_num(item['benchmark_metrics']['sharpe'])}</td>"
            f"<td>{_pct(item['drawdown_improvement'], 2)}</td>"
            f"<td>{_pct(item['cost_50bps']['cagr_difference'], 2)}</td>"
            f"<td>{_pct(rolling.get('cagr_win_fraction', 0.0), 1)}</td>"
            f"<td>{_pct(item['halves']['first']['cagr_difference'], 2)} / "
            f"{_pct(item['halves']['second']['cagr_difference'], 2)}</td>"
            f"<td>{_num(item['active_return_newey_west']['t_stat'])}</td>"
            "</tr>"
        )
        snapshot = item["snapshot"]
        receipt_rows.append(
            "<tr>"
            f"<th>{html.escape(item['ticker'])}</th>"
            f"<td>{item['period']['warmup_sessions']}</td>"
            f"<td><code>{html.escape(str(snapshot['panel_sha256']))}</code></td>"
            f"<td><code>{html.escape(str(snapshot['archive_sha256']))}</code></td>"
            "</tr>"
        )
    gate_labels = {
        "at_least_four_full_cagr_wins": "至少 4/5 市場完整期勝出",
        "at_least_four_sharpe_wins": "至少 4/5 市場 Sharpe 較高",
        "at_least_four_drawdown_improvements_of_10pp": "至少 4/5 市場最大跌幅改善 10 個百分點",
        "at_least_four_cost_50bps_wins": "至少 4/5 市場在 50 bps 仍勝出",
        "rolling_median_and_three_markets_at_least_60pct": "滾動勝率中位數與至少 3 市場達 60%",
        "pooled_active_newey_west_t_at_least_1_96": "等權主動回報 NW t 至少 1.96",
        "at_least_three_markets_win_both_halves": "至少 3/5 市場前後半期皆勝出",
    }
    gate_rows = "".join(
        "<tr>"
        f"<th>{html.escape(gate_labels.get(key, key))}</th>"
        f"<td class={'pass' if passed else 'fail'}>{'通過' if passed else '失敗'}</td>"
        "</tr>"
        for key, passed in audit["aggregate_gates"].items()
    )
    counts = audit["counts"]
    pooled = audit["pooled_active_return"]
    protocol = audit["protocol"]
    css = """
    :root{--ink:#17241e;--muted:#66736b;--paper:#f5f1e8;--panel:#fffdf8;--line:#d8d1c3;--red:#a83a31;--green:#176846;--gold:#c08a34}
    *{box-sizing:border-box}body{margin:0;background:var(--paper);color:var(--ink);font:15px/1.55 ui-sans-serif,system-ui,-apple-system,"PingFang TC","Noto Sans TC",sans-serif}main{max-width:1160px;margin:auto;padding:42px 22px 80px}header{border-bottom:3px solid var(--ink);padding-bottom:24px}.eyebrow{font-weight:800;letter-spacing:.13em;color:var(--red)}h1{font-size:clamp(36px,7vw,72px);line-height:1;margin:8px 0 16px;letter-spacing:-.05em}h2{margin:0 0 14px;font-size:24px}.lead{max-width:800px;font-size:18px}.verdict{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin:24px 0}.card,.panel{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:20px}.card strong{display:block;font-size:34px}.card span,.note,small{display:block;color:var(--muted)}.fail{color:var(--red);font-weight:750}.pass{color:var(--green);font-weight:750}.panel{margin-top:16px}.warning{border-left:5px solid var(--red);background:#f8e7e2;padding:16px 18px;border-radius:8px;margin-top:16px}.table-wrap{overflow:auto}table{width:100%;border-collapse:collapse;min-width:860px}th,td{text-align:right;border-bottom:1px solid var(--line);padding:11px 9px;white-space:nowrap}th:first-child{text-align:left}thead th{color:var(--muted);font-size:12px}code{font-size:11px;word-break:break-all;white-space:normal}.footer{color:var(--muted);font-size:12px;margin-top:24px}@media(max-width:720px){.verdict{grid-template-columns:1fr}main{padding:24px 12px 56px}.panel{padding:14px}}
    """
    content = f"""<!doctype html><html lang="zh-Hant-HK"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>v3 五市場機制驗證</title><style>{css}</style></head><body><main>
    <header><div class="eyebrow">FROZEN CROSS-MARKET AUDIT</div><h1>只有 1 / 5 市場勝出。<br>v3 未能泛化。</h1><p class="lead">這份結果使用下載前寫定的五個市場、1989–2006 期間與同一套 v3 規則。德國 DAX 的成功不能抵銷另外四個市場落後，因此策略不升級，也不能作實金參考。</p></header>
    <section class="verdict"><article class="card"><span>完整期 CAGR 勝出</span><strong class="fail">{counts["full_cagr"]} / 5</strong><small>硬門檻至少 4 / 5</small></article><article class="card"><span>跨市場等權主動回報 NW t</span><strong class="fail">{_num(pooled["newey_west"]["t_stat"])}</strong><small>硬門檻至少 1.96</small></article><article class="card"><span>五年滾動勝率中位數</span><strong class="fail">{_pct(audit["rolling_five_year_win_rate_median"], 1)}</strong><small>硬門檻至少 60%</small></article><article class="card"><span>6,100 次搜尋後 DSR 機率</span><strong class="fail">{_pct(pooled["deflated_sharpe"]["probability"], 4)}</strong><small>選擇偏誤懲罰</small></article></section>
    <div class="warning"><b>研究決定：保留負結果，不調參救援。</b><br>v3 仍可在隔離 Paper 模擬組合累積前瞻紀錄，但本結果降低而不是提高其可信度；不替換 v2，也不成為參考交易候選。</div>
    <section class="panel"><h2>五市場逐一收據</h2><p class="note">CAGR 差、最大跌幅改善與成本差均為策略減 buy-and-hold；前／後半期顯示兩段固定期間的 CAGR 差。</p><div class="table-wrap"><table><thead><tr><th>市場</th><th>v3 CAGR</th><th>買入並持有</th><th>CAGR 差</th><th>Sharpe v3 / 基準</th><th>最大跌幅改善</th><th>50 bps CAGR 差</th><th>5 年滾動勝率</th><th>前／後半期</th><th>NW t</th></tr></thead><tbody>{"".join(market_rows)}</tbody></table></div></section>
    <section class="panel"><h2>七道事前硬門檻</h2><div class="table-wrap"><table><thead><tr><th>檢查</th><th>結果</th></tr></thead><tbody>{gate_rows}</tbody></table></div></section>
    <section class="panel"><h2>數據與協議收據</h2><p>協議 SHA-256：<code>{html.escape(protocol["sha256"])}</code><br>固定驗證期：{html.escape(audit["period"]["start"])}–{html.escape(audit["period"]["end"])}<br>成本：10 bps；壓力成本：50 bps；防守資產：零回報 CASH。</p><div class="table-wrap"><table><thead><tr><th>代號</th><th>暖機 sessions</th><th>面板 SHA-256</th><th>封存檔 SHA-256</th></tr></thead><tbody>{"".join(receipt_rows)}</tbody></table></div></section>
    <p class="footer">價格指數不是總回報指數；策略與基準採相同價格口徑。研究與教育用途，不構成投資建議。</p>
    </main></body></html>"""
    destination.write_text(_with_report_references(content), encoding="utf-8")
    return destination


def build_style_rotation_report(destination: str | Path, audit: dict[str, Any]) -> Path:
    """Write the standalone receipt for the frozen v4 style-rotation test."""
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    trade = audit["trade"]
    strategy = trade["strategy_metrics"]
    benchmark_names = {
        "market": "SPY 買入並持有",
        "equal_weight": "風格靜態等權",
        "opportunity": "QQQ 機會成本",
    }
    comparison_rows = []
    for key, label in benchmark_names.items():
        metrics = trade["benchmark_metrics"][key]
        comparison = trade["comparisons"][key]
        rolling = trade["rolling_five_year"][key]["summary"]
        comparison_rows.append(
            "<tr>"
            f"<th>{html.escape(label)}</th>"
            f"<td>{_pct(strategy['cagr'], 2)} / {_pct(metrics['cagr'], 2)}</td>"
            f"<td>{_pct(comparison['cagr_difference'], 2)}</td>"
            f"<td>{_num(strategy['sharpe'])} / {_num(metrics['sharpe'])}</td>"
            f"<td>{_pct(strategy['max_drawdown'], 1)} / "
            f"{_pct(metrics['max_drawdown'], 1)}</td>"
            f"<td>{_pct(comparison['drawdown_improvement'], 1)}</td>"
            f"<td>{_pct(trade['cost_50bps'][key]['cagr_difference'], 2)}</td>"
            f"<td>{_pct(rolling.get('cagr_win_fraction', 0.0), 1)}</td>"
            f"<td>{_pct(rolling.get('median_cagr_difference', float('nan')), 2)}</td>"
            f"<td>{_num(comparison['active_return_newey_west']['t_stat'])}</td>"
            "</tr>"
        )
    half_rows = []
    for key, half in trade["fixed_halves"].items():
        half_rows.append(
            "<tr>"
            f"<th>{'前十年' if key == 'first' else '後十年'}"
            f"<small>{half['start']}–{half['end']}</small></th>"
            f"<td>{_pct(half['strategy_metrics']['cagr'], 2)}</td>"
            f"<td>{_pct(half['benchmarks']['market']['metrics']['cagr'], 2)}</td>"
            f"<td>{_pct(half['benchmarks']['market']['cagr_difference'], 2)}</td>"
            f"<td>{_pct(half['benchmarks']['equal_weight']['metrics']['cagr'], 2)}</td>"
            f"<td>{_pct(half['benchmarks']['equal_weight']['cagr_difference'], 2)}</td>"
            "</tr>"
        )
    gate_labels = {
        "01_trade_cagr_above_spy_and_equal_weight": "20 年 CAGR 同時勝過 SPY 與風格等權",
        "02_trade_sharpe_above_spy_and_equal_weight": "20 年 Sharpe 同時勝過 SPY 與風格等權",
        "03_trade_drawdown_improves_spy_by_10pp": "最大跌幅相對 SPY 改善至少 10 個百分點",
        "04_trade_50bps_beats_spy_and_equal_weight": "50 bps 成本仍勝過 SPY 與風格等權",
        "05_trade_both_ten_year_halves_beat_spy_and_equal_weight": "前後十年都勝過 SPY 與風格等權",
        "06_trade_rolling_five_year_wins_70pct_and_positive_median": "五年滾動勝率皆達 70% 且差值中位數為正",
        "07_trade_newey_west_t_at_least_1_96_vs_spy_and_equal_weight": "相對兩個主基準 NW t 都至少 1.96",
        "08_trade_qqq_opportunity_cost_and_drawdown": "QQQ 回報機會成本不超過 1pp 且最大跌幅改善 10pp",
        "09_proxy_cagr_above_gspc_and_equal_weight": "舊代理 CAGR 勝過 S&P 500 與風格等權",
        "10_proxy_sharpe_above_gspc_and_equal_weight": "舊代理 Sharpe 勝過兩個基準",
        "11_proxy_rolling_five_year_wins_60pct": "舊代理五年滾動勝率皆達 60%",
        "12_proxy_both_five_year_halves_beat_gspc_and_equal_weight": "舊代理前後五年皆勝過兩個基準",
        "13_proxy_50bps_beats_gspc_and_equal_weight": "舊代理 50 bps 成本仍勝過兩個基準",
        "14_proxy_newey_west_t_at_least_1_96_vs_gspc_and_equal_weight": "舊代理相對兩基準 NW t 都至少 1.96",
    }
    gate_rows = "".join(
        "<tr>"
        f"<th>{html.escape(gate_labels.get(key, key))}</th>"
        f"<td class={'pass' if passed else 'fail'}>{'通過' if passed else '失敗'}</td>"
        "</tr>"
        for key, passed in audit["gates"].items()
    )
    proxy = audit["proxy"]
    proxy_rows = "".join(
        "<tr>"
        f"<th>{html.escape(ticker)}</th>"
        f"<td>{item['valid_sessions']}</td>"
        f"<td>{html.escape(str(item['first_valid'] or '—'))}</td>"
        f"<td>{html.escape(str(item['last_valid'] or '—'))}</td>"
        f"<td>{html.escape(str(item.get('warmup_sessions_before_1996_07_31') if item.get('warmup_sessions_before_1996_07_31') is not None else '—'))}</td>"
        "</tr>"
        for ticker, item in proxy.get("coverage", {}).items()
    )
    receipts = audit["snapshots"]
    receipt_rows = "".join(
        "<tr>"
        f"<th>{'可交易 ETF' if key == 'trade' else '舊代理指數'}</th>"
        f"<td>{html.escape(str(item['start']))}–{html.escape(str(item['end']))}</td>"
        f"<td>{int(item['rows'])}</td>"
        f"<td><code>{html.escape(str(item['panel_sha256']))}</code></td>"
        f"<td><code>{html.escape(str(item['archive_sha256']))}</code></td>"
        "</tr>"
        for key, item in receipts.items()
    )
    css = """
    :root{--ink:#17241e;--muted:#66736b;--paper:#f5f1e8;--panel:#fffdf8;--line:#d8d1c3;--red:#a83a31;--green:#176846;--blue:#245f73}
    *{box-sizing:border-box}body{margin:0;background:var(--paper);color:var(--ink);font:15px/1.55 ui-sans-serif,system-ui,-apple-system,"PingFang TC","Noto Sans TC",sans-serif}main{max-width:1180px;margin:auto;padding:42px 22px 80px}header{border-bottom:3px solid var(--ink);padding-bottom:24px}.eyebrow{font-weight:800;letter-spacing:.13em;color:var(--red)}h1{font-size:clamp(34px,7vw,68px);line-height:1.03;margin:8px 0 16px;letter-spacing:-.05em}h2{margin:0 0 14px;font-size:24px}.lead{max-width:850px;font-size:18px}.verdict{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin:24px 0}.card,.panel{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:20px}.card strong{display:block;font-size:32px}.card span,.note,small{display:block;color:var(--muted)}.fail{color:var(--red);font-weight:750}.pass{color:var(--green);font-weight:750}.panel{margin-top:16px}.warning{border-left:5px solid var(--red);background:#f8e7e2;padding:16px 18px;border-radius:8px;margin-top:16px}.table-wrap{overflow:auto}table{width:100%;border-collapse:collapse;min-width:800px}th,td{text-align:right;border-bottom:1px solid var(--line);padding:11px 9px;white-space:nowrap}th:first-child{text-align:left}thead th{color:var(--muted);font-size:12px}code{font-size:11px;word-break:break-all;white-space:normal}.footer{color:var(--muted);font-size:12px;margin-top:24px}@media(max-width:900px){.verdict{grid-template-columns:1fr 1fr}}@media(max-width:600px){.verdict{grid-template-columns:1fr}main{padding:24px 12px 56px}.panel{padding:14px}}
    """
    current = "、".join(
        f"{ticker} {weight:.0%}" for ticker, weight in trade["current_target"].items()
    )
    content = f"""<!doctype html><html lang="zh-Hant-HK"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>v4 股權風格輪動研究收據</title><style>{css}</style></head><body><main>
    <header><div class="eyebrow">PREDECLARED STYLE-ROTATION AUDIT</div><h1>最大跌幅較小，<br>但回報門檻失敗。</h1><p class="lead">v4 在可交易 20 年中把 SPY 最大跌幅改善 {_pct(trade["comparisons"]["market"]["drawdown_improvement"], 1)}，Sharpe 也較高；但 CAGR 落後 SPY {_pct(abs(trade["comparisons"]["market"]["cagr_difference"]), 2)}，後十年與五年滾動結果明顯失敗。舊代理又沒有足夠數據，因此不能建立 Paper 模擬組合。</p></header>
    <section class="verdict"><article class="card"><span>14 道硬門檻</span><strong class="fail">{audit["passed_gate_count"]} / {audit["required_gate_count"]}</strong><small>必須全部通過</small></article><article class="card"><span>策略 / SPY CAGR</span><strong>{_pct(strategy["cagr"], 2)} / {_pct(trade["benchmark_metrics"]["market"]["cagr"], 2)}</strong><small>主成本 10 bps</small></article><article class="card"><span>策略最大跌幅</span><strong class="pass">{_pct(strategy["max_drawdown"], 1)}</strong><small>SPY {_pct(trade["benchmark_metrics"]["market"]["max_drawdown"], 1)}</small></article><article class="card"><span>目前研究訊號</span><strong>{html.escape(current or "全數防守")}</strong><small>不是交易建議</small></article></section>
    <div class="warning"><b>研究決定：不啟動 v4 Paper，也不調參救援。</b><br>50 bps 成本、後十年、五年滾動、Newey–West 與 QQQ 機會成本均未過關；`^RLG`／`^RLV` 只有 2002 年後數據，舊代理六道門檻依協議全部失敗。</div>
    <section class="panel"><h2>20 年主樣本：同口徑比較</h2><p class="note">所有數字都用 2006-07-31–2026-07-31、月末訊號、下一交易日開市與相同成本。</p><div class="table-wrap"><table><thead><tr><th>基準</th><th>策略 / 基準 CAGR</th><th>CAGR 差</th><th>策略 / 基準 Sharpe</th><th>策略 / 基準 MDD</th><th>最大跌幅改善</th><th>50 bps CAGR 差</th><th>5 年勝率</th><th>5 年差中位數</th><th>NW t</th></tr></thead><tbody>{"".join(comparison_rows)}</tbody></table></div></section>
    <section class="panel"><h2>固定前後十年</h2><div class="table-wrap"><table><thead><tr><th>期間</th><th>策略 CAGR</th><th>SPY CAGR</th><th>相對 SPY</th><th>風格等權 CAGR</th><th>相對等權</th></tr></thead><tbody>{"".join(half_rows)}</tbody></table></div></section>
    <section class="panel"><h2>舊代理數據門檻</h2><p class="note">協議要求 1996-07-31 前至少 273 個有效 session；不允許事後換代號。</p><div class="table-wrap"><table><thead><tr><th>代號</th><th>有效 sessions</th><th>首筆</th><th>末筆</th><th>起算前暖機</th></tr></thead><tbody>{proxy_rows}</tbody></table></div></section>
    <section class="panel"><h2>十四道事前硬門檻</h2><div class="table-wrap"><table><thead><tr><th>檢查</th><th>結果</th></tr></thead><tbody>{gate_rows}</tbody></table></div></section>
    <section class="panel"><h2>快照與協議收據</h2><p>協議 SHA-256：<code>{html.escape(audit["protocol"]["sha256"])}</code></p><div class="table-wrap"><table><thead><tr><th>數據</th><th>期間</th><th>列數</th><th>面板 SHA-256</th><th>封存檔 SHA-256</th></tr></thead><tbody>{receipt_rows}</tbody></table></div></section>
    <p class="footer">經調整 ETF 價格與價格指數代理不可跨段串接。歷史回測、研究與教育用途，不構成投資建議。</p>
    </main></body></html>"""
    destination.write_text(_with_report_references(content), encoding="utf-8")
    return destination


def build_three_clock_report(destination: str | Path, audit: dict[str, Any]) -> Path:
    """Write a standalone beginner-readable v5 ensemble research receipt."""
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    main = audit["main"]
    proxy = audit["proxy"]
    cross = audit["cross_market"]
    strategy = main["strategy_metrics"]
    benchmark_labels = {
        "market": "SPY",
        "matched_95_5": "固定 95% QQQ／5% SHY",
        "opportunity": "QQQ",
    }
    main_rows = []
    for key, label in benchmark_labels.items():
        benchmark = main["benchmark_metrics"][key]
        comparison = main["comparisons"][key]
        rolling = main["rolling_five_year"][key]["summary"]
        main_rows.append(
            "<tr>"
            f"<th>{html.escape(label)}</th>"
            f"<td>{_pct(strategy['cagr'], 2)} / {_pct(benchmark['cagr'], 2)}</td>"
            f"<td>{_pct(comparison['cagr_difference'], 2)}</td>"
            f"<td>{_num(strategy['sharpe'])} / {_num(benchmark['sharpe'])}</td>"
            f"<td>{_pct(strategy['max_drawdown'], 1)} / "
            f"{_pct(benchmark['max_drawdown'], 1)}</td>"
            f"<td>{_pct(comparison['drawdown_improvement'], 1)}</td>"
            f"<td>{_pct(main['cost_50bps'][key]['cagr_difference'], 2)}</td>"
            f"<td>{_pct(rolling['cagr_win_fraction'], 1)}</td>"
            f"<td>{_num(comparison['active_return_newey_west']['t_stat'])}</td>"
            f"<td>{_pct(comparison['active_deflated_sharpe']['probability'], 3)}</td>"
            "</tr>"
        )
    proxy_rows = []
    for key, label in (("market", "NDX"), ("matched_95_5", "固定 95/5")):
        benchmark = proxy["benchmark_metrics"][key]
        comparison = proxy["comparisons"][key]
        rolling = proxy["rolling_five_year"][key]["summary"]
        proxy_rows.append(
            "<tr>"
            f"<th>{label}</th>"
            f"<td>{_pct(proxy['strategy_metrics']['cagr'], 2)} / "
            f"{_pct(benchmark['cagr'], 2)}</td>"
            f"<td>{_pct(comparison['cagr_difference'], 2)}</td>"
            f"<td>{_pct(proxy['strategy_metrics']['max_drawdown'], 1)} / "
            f"{_pct(benchmark['max_drawdown'], 1)}</td>"
            f"<td>{_pct(rolling['cagr_win_fraction'], 1)}</td>"
            f"<td>{_pct(rolling['median_cagr_difference'], 2)}</td>"
            f"<td>{_num(comparison['active_return_newey_west']['t_stat'])}</td>"
            "</tr>"
        )
    market_rows = []
    for item in cross["markets"].values():
        market_comparison = item["comparisons"]["market"]
        matched_comparison = item["comparisons"]["matched_95_5"]
        rolling_market = item["rolling_five_year"]["market"]["summary"]
        rolling_matched = item["rolling_five_year"]["matched_95_5"]["summary"]
        market_rows.append(
            "<tr>"
            f"<th>{html.escape(item['market'])}<small>{html.escape(item['index'])}</small></th>"
            f"<td>{_pct(item['strategy_metrics']['cagr'], 2)}</td>"
            f"<td>{_pct(item['benchmark_metrics']['market']['cagr'], 2)}</td>"
            f"<td>{_pct(item['benchmark_metrics']['matched_95_5']['cagr'], 2)}</td>"
            f"<td class={'pass' if item['gates']['full_cagr_beats_both'] else 'fail'}>"
            f"{_pct(market_comparison['cagr_difference'], 2)} / "
            f"{_pct(matched_comparison['cagr_difference'], 2)}</td>"
            f"<td>{_pct(market_comparison['drawdown_improvement'], 1)}</td>"
            f"<td>{_pct(rolling_market['cagr_win_fraction'], 1)} / "
            f"{_pct(rolling_matched['cagr_win_fraction'], 1)}</td>"
            "</tr>"
        )
    gate_rows = "".join(
        "<tr>"
        f"<th>{html.escape(key.replace('_', ' '))}</th>"
        f"<td class={'pass' if passed else 'fail'}>{'通過' if passed else '失敗'}</td>"
        "</tr>"
        for key, passed in audit["gates"].items()
    )
    current = "、".join(
        f"{ticker} {weight:.1%}" for ticker, weight in main["current_target"].items()
    )
    matched = main["comparisons"]["matched_95_5"]
    opportunity = main["comparisons"]["opportunity"]
    pooled = cross["pooled_active_return"]
    counts = cross["counts"]
    css = """
    :root{--ink:#17241e;--muted:#66736b;--paper:#f5f1e8;--panel:#fffdf8;--line:#d8d1c3;--red:#a83a31;--green:#176846;--gold:#c08a34}
    *{box-sizing:border-box}body{margin:0;background:var(--paper);color:var(--ink);font:15px/1.55 ui-sans-serif,system-ui,-apple-system,"PingFang TC","Noto Sans TC",sans-serif}main{max-width:1180px;margin:auto;padding:42px 22px 80px}header{border-bottom:3px solid var(--ink);padding-bottom:24px}.eyebrow{font-weight:800;letter-spacing:.13em;color:var(--red)}h1{font-size:clamp(34px,7vw,68px);line-height:1.03;margin:8px 0 16px;letter-spacing:-.05em}h2{margin:0 0 14px;font-size:24px}.lead{max-width:870px;font-size:18px}.verdict{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin:24px 0}.card,.panel{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:20px}.card strong{display:block;font-size:30px}.card span,.note,small{display:block;color:var(--muted)}.fail{color:var(--red);font-weight:750}.pass{color:var(--green);font-weight:750}.panel{margin-top:16px}.warning{border-left:5px solid var(--red);background:#f8e7e2;padding:16px 18px;border-radius:8px;margin-top:16px}.table-wrap{overflow:auto}table{width:100%;border-collapse:collapse;min-width:900px}th,td{text-align:right;border-bottom:1px solid var(--line);padding:11px 9px;white-space:nowrap}th:first-child{text-align:left}thead th{color:var(--muted);font-size:12px}code{font-size:11px;word-break:break-all;white-space:normal}.footer{color:var(--muted);font-size:12px;margin-top:24px}@media(max-width:900px){.verdict{grid-template-columns:1fr 1fr}}@media(max-width:600px){.verdict{grid-template-columns:1fr}main{padding:24px 12px 56px}.panel{padding:14px}}
    """
    content = f"""<!doctype html><html lang="zh-Hant-HK"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>v5 三時鐘集成研究收據</title><style>{css}</style></head><body><main>
    <header><div class="eyebrow">FROZEN THREE-CLOCK ENSEMBLE AUDIT</div><h1>近期幾乎追平 QQQ，<br>外部驗證仍失敗。</h1><p class="lead">三個固定三分之一袖套在 2006–2026 得到 {_pct(strategy["cagr"], 2)} CAGR，QQQ 為 {_pct(main["benchmark_metrics"]["opportunity"]["cagr"], 2)}，最大跌幅改善 {_pct(opportunity["drawdown_improvement"], 1)}。但這不是結論：舊年代滾動一致性與五市場泛化仍失敗，所以不能建立 Paper。</p></header>
    <section class="verdict"><article class="card"><span>22 道硬門檻</span><strong class="fail">{audit["passed_gate_count"]} / {audit["required_gate_count"]}</strong><small>必須全部通過</small></article><article class="card"><span>策略 / QQQ CAGR</span><strong>{_pct(strategy["cagr"], 2)} / {_pct(main["benchmark_metrics"]["opportunity"]["cagr"], 2)}</strong><small>差 {_pct(opportunity["cagr_difference"], 3)}</small></article><article class="card"><span>相對 95/5 NW t</span><strong class="fail">{_num(matched["active_return_newey_west"]["t_stat"])}</strong><small>門檻 1.96</small></article><article class="card"><span>目前研究權重</span><strong>{html.escape(current)}</strong><small>未開 Paper、不可照單</small></article></section>
    <div class="warning"><b>研究決定：不建立 v5 Paper，不改袖套比例救援。</b><br>近期主樣本通過 7/9 道，但 1986–2006 滾動勝率只有約 37%，五市場完整期同時勝兩基準只有 {counts["full_cagr_beats_both"]}/5；五市場等權主動回報相對 buy-and-hold 為 {_pct(pooled["market"]["newey_west"]["annualized"], 2)}，NW t = {_num(pooled["market"]["newey_west"]["t_stat"])}。</div>
    <section class="panel"><h2>近期 20 年：看似接近，但 matched alpha 很弱</h2><div class="table-wrap"><table><thead><tr><th>基準</th><th>策略 / 基準 CAGR</th><th>CAGR 差</th><th>策略 / 基準 Sharpe</th><th>策略 / 基準 MDD</th><th>最大跌幅改善</th><th>50 bps CAGR 差</th><th>5 年勝率</th><th>NW t</th><th>DSR</th></tr></thead><tbody>{"".join(main_rows)}</tbody></table></div></section>
    <section class="panel"><h2>1986–2006：全期勝出，滾動一致性失敗</h2><div class="table-wrap"><table><thead><tr><th>基準</th><th>策略 / 基準 CAGR</th><th>CAGR 差</th><th>策略 / 基準 MDD</th><th>5 年勝率</th><th>5 年差中位數</th><th>NW t</th></tr></thead><tbody>{"".join(proxy_rows)}</tbody></table></div></section>
    <section class="panel"><h2>五市場：只有單一市場完整期同勝兩基準</h2><div class="table-wrap"><table><thead><tr><th>市場</th><th>策略 CAGR</th><th>買入並持有</th><th>固定 95/5</th><th>相對兩基準</th><th>最大跌幅改善</th><th>5 年勝率（買入／95/5）</th></tr></thead><tbody>{"".join(market_rows)}</tbody></table></div></section>
    <section class="panel"><h2>二十二道事前硬門檻</h2><div class="table-wrap"><table><thead><tr><th>固定檢查鍵</th><th>結果</th></tr></thead><tbody>{gate_rows}</tbody></table></div></section>
    <section class="panel"><h2>協議與選擇偏誤收據</h2><p>協議 SHA-256：<code>{html.escape(audit["protocol"]["sha256"])}</code><br>本策略整合的是已研究過的三個時鐘，屬 post-selection；6,102 次搜尋懲罰與完整外部失敗均保留。</p></section>
    <p class="footer">歷史回測、研究與教育用途，不構成投資建議。近期樣本成功不能抵銷舊年代和外部市場失敗。</p>
    </main></body></html>"""
    destination.write_text(_with_report_references(content), encoding="utf-8")
    return destination


def build_industry_tilt_report(destination: str | Path, audit: dict[str, Any]) -> Path:
    """Write the beginner-readable receipt for the frozen v6 industry test."""
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    main = audit["main"]
    early = audit["early_etf"]
    proxy = audit["proxy"]
    strategy = main["strategy_metrics"]
    spy = main["benchmark_metrics"]["spy"]
    matched = main["benchmark_metrics"]["matched"]
    failed = [key for key, value in audit["gates"].items() if not value]
    gate_rows = "".join(
        "<tr>"
        f"<th>{html.escape(key.replace('_', ' '))}</th>"
        f"<td class={'pass' if passed else 'fail'}>{'通過' if passed else '失敗'}</td>"
        "</tr>"
        for key, passed in audit["gates"].items()
    )
    current = "、".join(
        f"{ticker} {weight:.1%}" for ticker, weight in main["current_target"].items()
    )
    period_rows = "".join(
        [
            "<tr><th>可交易 ETF 主期<small>2006-07-31–2026-07-31</small></th>"
            f"<td>{_pct(strategy['cagr'], 2)}</td><td>{_pct(spy['cagr'], 2)}</td>"
            f"<td>{_pct(matched['cagr'], 2)}</td>"
            f"<td>{_num(strategy['sharpe'])} / {_num(spy['sharpe'])} / {_num(matched['sharpe'])}</td>"
            f"<td>{_pct(strategy['max_drawdown'], 1)} / {_pct(spy['max_drawdown'], 1)} / {_pct(matched['max_drawdown'], 1)}</td></tr>",
            "<tr><th>早期 ETF 不重疊期"
            f"<small>{html.escape(early['period']['start'])}–{html.escape(early['period']['end'])}</small></th>"
            f"<td>{_pct(early['strategy_metrics']['cagr'], 2)}</td>"
            f"<td>{_pct(early['benchmark_metrics']['spy']['cagr'], 2)}</td>"
            f"<td>{_pct(early['benchmark_metrics']['matched']['cagr'], 2)}</td>"
            f"<td>{_num(early['strategy_metrics']['sharpe'])} / {_num(early['benchmark_metrics']['spy']['sharpe'])} / {_num(early['benchmark_metrics']['matched']['sharpe'])}</td>"
            f"<td>{_pct(early['strategy_metrics']['max_drawdown'], 1)} / {_pct(early['benchmark_metrics']['spy']['max_drawdown'], 1)} / {_pct(early['benchmark_metrics']['matched']['max_drawdown'], 1)}</td></tr>",
            "<tr><th>French 產業代理<small>1927–2005；月頻、不可交易回填</small></th>"
            f"<td>{_pct(proxy['strategy_metrics']['cagr'], 2)}</td>"
            f"<td>{_pct(proxy['benchmark_metrics']['market']['cagr'], 2)}</td>"
            f"<td>{_pct(proxy['benchmark_metrics']['matched']['cagr'], 2)}</td>"
            f"<td>{_num(proxy['strategy_metrics']['sharpe'])} / {_num(proxy['benchmark_metrics']['market']['sharpe'])} / {_num(proxy['benchmark_metrics']['matched']['sharpe'])}</td>"
            f"<td>{_pct(proxy['strategy_metrics']['max_drawdown'], 1)} / {_pct(proxy['benchmark_metrics']['market']['max_drawdown'], 1)} / {_pct(proxy['benchmark_metrics']['matched']['max_drawdown'], 1)}</td></tr>",
        ]
    )
    protocol = audit["protocol"]
    etf = audit["data_receipts"]["etf"]
    french = audit["data_receipts"]["french"]
    css = """
    :root{--ink:#17241e;--muted:#66736b;--paper:#f5f1e8;--panel:#fffdf8;--line:#d8d1c3;--red:#a83a31;--green:#176846;--gold:#b47b1d}
    *{box-sizing:border-box}body{margin:0;background:var(--paper);color:var(--ink);font:15px/1.55 ui-sans-serif,system-ui,-apple-system,"PingFang TC","Noto Sans TC",sans-serif}main{max-width:1180px;margin:auto;padding:42px 22px 80px}header{border-bottom:3px solid var(--ink);padding-bottom:24px}.eyebrow{font-weight:800;letter-spacing:.13em;color:var(--red)}h1{font-size:clamp(34px,7vw,68px);line-height:1.03;margin:8px 0 16px;letter-spacing:-.05em}h2{margin:0 0 14px;font-size:24px}.lead{max-width:890px;font-size:18px}.verdict{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin:24px 0}.card,.panel{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:20px}.card strong{display:block;font-size:30px}.card span,.note,small{display:block;color:var(--muted)}.fail{color:var(--red);font-weight:750}.pass{color:var(--green);font-weight:750}.panel{margin-top:16px}.warning{border-left:5px solid var(--red);background:#f8e7e2;padding:16px 18px;border-radius:8px;margin-top:16px}.table-wrap{overflow:auto}table{width:100%;border-collapse:collapse;min-width:900px}th,td{text-align:right;border-bottom:1px solid var(--line);padding:11px 9px;white-space:nowrap}th:first-child{text-align:left}thead th{color:var(--muted);font-size:12px}code{font-size:11px;word-break:break-all;white-space:normal}.footer{color:var(--muted);font-size:12px;margin-top:24px}@media(max-width:900px){.verdict{grid-template-columns:1fr 1fr}}@media(max-width:600px){.verdict{grid-template-columns:1fr}main{padding:24px 12px 56px}.panel{padding:14px}}
    """
    content = f"""<!doctype html><html lang="zh-Hant-HK"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>v6 產業動能研究收據</title><style>{css}</style></head><body><main>
    <header><div class="eyebrow">FROZEN INDUSTRY-MOMENTUM AUDIT</div><h1>長期代理有效，<br>可交易主期仍落後。</h1><p class="lead">v6 在新數據下載前已把規則與 22 道門檻鎖定。1927–2005 代理期支持產業動能機制，但真正可交易的 2006–2026 ETF 策略 CAGR 只有 {_pct(strategy["cagr"], 2)}，低於 SPY 的 {_pct(spy["cagr"], 2)}，也低於相同每月股票持倉比率對照的 {_pct(matched["cagr"], 2)}。實務主測試優先，因此本候選淘汰。</p></header>
    <section class="verdict"><article class="card"><span>22 道事前硬門檻</span><strong class="fail">{audit["passed_gate_count"]} / {audit["required_gate_count"]}</strong><small>必須全部通過</small></article><article class="card"><span>ETF 主期策略 / SPY</span><strong>{_pct(strategy["cagr"], 2)} / {_pct(spy["cagr"], 2)}</strong><small>相差 {_pct(strategy["cagr"] - spy["cagr"], 2)}</small></article><article class="card"><span>策略 / matched</span><strong>{_pct(strategy["cagr"], 2)} / {_pct(matched["cagr"], 2)}</strong><small>選產業沒有增加淨回報</small></article><article class="card"><span>研究狀態</span><strong class="fail">不開 Paper</strong><small>不調參救援</small></article></section>
    <div class="warning"><b>研究決定：封存負結果，網站主訊號與 Paper 都不改。</b><br>目前規則算出的最後歷史權重是 {html.escape(current)}，但策略已被 11 道失敗門檻淘汰，這組權重不可照單。主要失敗包括 CAGR、同持倉比率 Sharpe、50 bps 成本、前後半期、滾動一致性與統計門檻。</div>
    <section class="panel"><h2>三段數據，同一個研究問題</h2><p class="note">表內依序為策略／廣泛市場／selection-matched control。代理期只能驗證機制，不能取代 ETF 可交易結果。</p><div class="table-wrap"><table><thead><tr><th>數據段</th><th>策略 CAGR</th><th>市場 CAGR</th><th>matched CAGR</th><th>Sharpe：策略 / 市場 / matched</th><th>最大跌幅：策略 / 市場 / matched</th></tr></thead><tbody>{period_rows}</tbody></table></div></section>
    <section class="panel"><h2>22 道事前硬門檻</h2><p class="note">通過 {audit["passed_gate_count"]} 道，失敗 {len(failed)} 道；任何一項失敗都不能啟動 Paper。</p><div class="table-wrap"><table><thead><tr><th>檢查</th><th>結果</th></tr></thead><tbody>{gate_rows}</tbody></table></div></section>
    <section class="panel"><h2>數據與不可竄改收據</h2><p>協議 SHA-256：<code>{html.escape(protocol["sha256"])}</code><br>ETF panel SHA-256：<code>{html.escape(etf["panel_sha256"])}</code><br>ETF archive SHA-256：<code>{html.escape(etf["archive_sha256"])}</code><br>French 10 Industry ZIP：<code>{html.escape(french["industry"]["sha256"])}</code><br>French Factors ZIP：<code>{html.escape(french["factors"]["sha256"])}</code></p></section>
    <p class="footer">歷史回測、研究與教育用途，不構成投資建議。過去表現不保證未來結果。</p>
    </main></body></html>"""
    destination.write_text(_with_report_references(content), encoding="utf-8")
    return destination


def build_relative_growth_report(destination: str | Path, audit: dict[str, Any]) -> Path:
    """Write the beginner-readable receipt for the frozen v7 hypothesis."""
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    main = audit["main"]
    proxy = audit["proxy"]
    strategy = main["strategy_metrics"]
    market = main["benchmark_metrics"]["market"]
    matched = main["benchmark_metrics"]["matched"]
    passed = bool(audit["historical_gate_passed"])
    failed = [key for key, value in audit["gates"].items() if not value]
    current = "、".join(
        f"{ticker} {weight:.0%}" for ticker, weight in main["current_target"].items()
    )
    gate_rows = "".join(
        "<tr>"
        f"<th>{html.escape(key.replace('_', ' '))}</th>"
        f"<td class={'pass' if value else 'fail'}>{'通過' if value else '失敗'}</td>"
        "</tr>"
        for key, value in audit["gates"].items()
    )

    def period_row(label: str, data: dict[str, Any], note: str) -> str:
        sm = data["strategy_metrics"]
        bm = data["benchmark_metrics"]["market"]
        mm = data["benchmark_metrics"]["matched"]
        market_cmp = data["comparisons"]["market"]
        matched_cmp = data["comparisons"]["matched"]
        return (
            f"<tr><th>{html.escape(label)}<small>{html.escape(note)}</small></th>"
            f"<td>{_pct(sm['cagr'], 2)}</td><td>{_pct(bm['cagr'], 2)}</td>"
            f"<td>{_pct(mm['cagr'], 2)}</td>"
            f"<td>{_pct(sm['max_drawdown'], 1)} / {_pct(bm['max_drawdown'], 1)} / {_pct(mm['max_drawdown'], 1)}</td>"
            f"<td>{_num(market_cmp['active_return_newey_west']['t_stat'])}</td>"
            f"<td>{_num(matched_cmp['active_return_newey_west']['t_stat'])}</td></tr>"
        )

    period_rows = "".join(
        [
            period_row("可交易 ETF 主期", main, "2006-07-31–2026-07-31；總回報 ETF"),
            period_row("不重疊舊代理", proxy, "1989-01-03–2006-07-28；價格指數＋零息現金"),
        ]
    )
    css = """
    :root{--ink:#17241e;--muted:#66736b;--paper:#f5f1e8;--panel:#fffdf8;--line:#d8d1c3;--red:#a83a31;--green:#176846;--gold:#b47b1d}
    *{box-sizing:border-box}body{margin:0;background:var(--paper);color:var(--ink);font:15px/1.55 ui-sans-serif,system-ui,-apple-system,"PingFang TC","Noto Sans TC",sans-serif}main{max-width:1180px;margin:auto;padding:42px 22px 80px}header{border-bottom:3px solid var(--ink);padding-bottom:24px}.eyebrow{font-weight:800;letter-spacing:.13em;color:var(--gold)}h1{font-size:clamp(34px,7vw,68px);line-height:1.03;margin:8px 0 16px;letter-spacing:-.05em}h2{margin:0 0 14px;font-size:24px}.lead{max-width:900px;font-size:18px}.verdict{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin:24px 0}.card,.panel{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:20px}.card strong{display:block;font-size:30px}.card span,.note,small{display:block;color:var(--muted)}.fail{color:var(--red);font-weight:750}.pass{color:var(--green);font-weight:750}.panel{margin-top:16px}.warning{border-left:5px solid var(--red);background:#f8e7e2;padding:16px 18px;border-radius:8px;margin-top:16px}.success{border-left-color:var(--green);background:#e5f2e9}.table-wrap{overflow:auto}table{width:100%;border-collapse:collapse;min-width:920px}th,td{text-align:right;border-bottom:1px solid var(--line);padding:11px 9px;white-space:nowrap}th:first-child{text-align:left}thead th{color:var(--muted);font-size:12px}code{font-size:11px;word-break:break-all;white-space:normal}.footer{color:var(--muted);font-size:12px;margin-top:24px}@media(max-width:900px){.verdict{grid-template-columns:1fr 1fr}}@media(max-width:600px){.verdict{grid-template-columns:1fr}main{padding:24px 12px 56px}.panel{padding:14px}}
    """
    headline = (
        "歷史門檻全過，<br>只准開始前瞻 Paper。"
        if passed
        else "有風險政策價值，<br>但 alpha 尚未被證實。"
    )
    decision = (
        "19 道凍結門檻全部通過，但仍需 252 個新增交易日與 6 次換倉；現在不可視為實金參考。"
        if passed
        else f"有 {len(failed)} 道凍結門檻失敗，因此封存負結果、不調參，也不建立 v7 Paper。"
    )
    content = f"""<!doctype html><html lang="zh-Hant-HK"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>v7 相對成長衛星研究收據</title><style>{css}</style></head><body><main>
    <header><div class="eyebrow">FROZEN RELATIVE-GROWTH AUDIT</div><h1>{headline}</h1><p class="lead">v7 永久保留 50% 廣泛市場核心；只有 QQQ 的 12–1 動能領先 SPY 且仍站在 200 日移動平均線上時，另一半才持有 QQQ，否則轉到 SHY。matched control 每月持有相同股票持倉比率，用來分辨「降低風險的配置政策」和「選 QQQ 真正帶來的超額回報」。</p></header>
    <section class="verdict"><article class="card"><span>19 道事前硬門檻</span><strong class={"pass" if passed else "fail"}>{audit["passed_gate_count"]} / {audit["required_gate_count"]}</strong><small>必須全部通過</small></article><article class="card"><span>主期策略 / SPY CAGR</span><strong>{_pct(strategy["cagr"], 2)} / {_pct(market["cagr"], 2)}</strong><small>差 {_pct(strategy["cagr"] - market["cagr"], 2)}</small></article><article class="card"><span>策略 / matched CAGR</span><strong>{_pct(strategy["cagr"], 2)} / {_pct(matched["cagr"], 2)}</strong><small>隔離 QQQ 選擇效果</small></article><article class="card"><span>目前研究權重</span><strong>{html.escape(current)}</strong><small>{"只供新 Paper 起點" if passed else "淘汰規則，不可照單"}</small></article></section>
    <div class="warning {"success" if passed else ""}"><b>研究決定：{"只建立獨立 v7 Paper，不替換正式訊號。" if passed else "不建立 v7 Paper，不改規則救援。"}</b><br>{decision}</div>
    <section class="panel"><h2>政策效果與選擇 alpha 必須分開</h2><p>SPY 是完全承擔市場風險；matched control 則和策略每月持有相同股票比例，但風險開啟時仍持有 SPY。策略只有在同時勝過 SPY 與 matched 時，才能說 QQQ 選擇本身提供了額外證據。這避免把「少持股所以跌得少」誤寫成選股能力。</p></section>
    <section class="panel"><h2>兩段不重疊數據</h2><div class="table-wrap"><table><thead><tr><th>數據段</th><th>策略 CAGR</th><th>市場 CAGR</th><th>matched CAGR</th><th>最大跌幅：策略 / 市場 / matched</th><th>對市場 NW t</th><th>對 matched NW t</th></tr></thead><tbody>{period_rows}</tbody></table></div></section>
    <section class="panel"><h2>十九道事前硬門檻</h2><p class="note">通過 {audit["passed_gate_count"]} 道，失敗 {len(failed)} 道；任何一項失敗都不能啟動 Paper。</p><div class="table-wrap"><table><thead><tr><th>固定檢查鍵</th><th>結果</th></tr></thead><tbody>{gate_rows}</tbody></table></div></section>
    <section class="panel"><h2>不可竄改數據收據</h2><p>協議 SHA-256：<code>{html.escape(audit["protocol"]["sha256"])}</code><br>主 ETF panel：<code>{html.escape(audit["data_receipts"]["main"]["panel_sha256"])}</code><br>Nasdaq-100 archive：<code>{html.escape(audit["data_receipts"]["ndx"]["archive_sha256"])}</code><br>S&amp;P 500 archive：<code>{html.escape(audit["data_receipts"]["gspc"]["archive_sha256"])}</code></p></section>
    <p class="footer">歷史回測、研究與教育用途，不構成投資建議。價格指數代理不含股息，不能冒充 ETF 可交易表現；過去表現不保證未來結果。</p>
    </main></body></html>"""
    destination.write_text(_with_report_references(content), encoding="utf-8")
    return destination


def build_always_invested_report(destination: str | Path, audit: dict[str, Any]) -> Path:
    """Write the beginner-readable receipt for the frozen v8 policy."""
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    main = audit["main"]
    proxy = audit["proxy"]
    strategy = main["strategy_metrics"]
    spy = main["benchmark_metrics"]["market"]
    paper_ok = bool(audit["paper_eligible"])
    history_ok = bool(audit["historically_confirmed"])
    paper_failed = [key for key, value in audit["paper_entry_gates"].items() if not value]
    stat_failed = [key for key, value in audit["statistical_gates"].items() if not value]
    current = "、".join(
        f"{ticker} {weight:.0%}" for ticker, weight in main["current_target"].items()
    )
    gate_rows = "".join(
        "<tr>"
        f"<th>{html.escape(key.replace('_', ' '))}</th>"
        f"<td class={'pass' if value else 'fail'}>{'通過' if value else '失敗'}</td>"
        "</tr>"
        for key, value in audit["gates"].items()
    )

    def period_row(label: str, data: dict[str, Any], note: str) -> str:
        sm = data["strategy_metrics"]
        bm = data["benchmark_metrics"]["market"]
        cmp = data["comparison"]
        rolling = data["rolling_five_year"]["summary"]
        return (
            f"<tr><th>{html.escape(label)}<small>{html.escape(note)}</small></th>"
            f"<td>{_pct(sm['cagr'], 2)}</td><td>{_pct(bm['cagr'], 2)}</td>"
            f"<td>{_pct(cmp['cagr_difference'], 2)}</td>"
            f"<td>{_pct(sm['max_drawdown'], 1)} / {_pct(bm['max_drawdown'], 1)}</td>"
            f"<td>{_pct(rolling.get('cagr_win_fraction', float('nan')), 1)}</td>"
            f"<td>{_num(cmp['active_return_newey_west']['t_stat'])}</td>"
            f"<td>{_pct(cmp['active_probabilistic_sharpe']['probability'], 1)}</td></tr>"
        )

    period_rows = "".join(
        [
            period_row("可交易 ETF 主期", main, "2006-07-31–2026-07-31；總回報 ETF"),
            period_row("不重疊舊代理", proxy, "1989-01-03–2006-07-28；價格指數"),
        ]
    )
    css = """
    :root{--ink:#17241e;--muted:#66736b;--paper:#f5f1e8;--panel:#fffdf8;--line:#d8d1c3;--red:#a83a31;--green:#176846;--gold:#b47b1d}
    *{box-sizing:border-box}body{margin:0;background:var(--paper);color:var(--ink);font:15px/1.55 ui-sans-serif,system-ui,-apple-system,"PingFang TC","Noto Sans TC",sans-serif}main{max-width:1180px;margin:auto;padding:42px 22px 80px}header{border-bottom:3px solid var(--ink);padding-bottom:24px}.eyebrow{font-weight:800;letter-spacing:.13em;color:var(--gold)}h1{font-size:clamp(34px,7vw,68px);line-height:1.03;margin:8px 0 16px;letter-spacing:-.05em}h2{margin:0 0 14px;font-size:24px}.lead{max-width:900px;font-size:18px}.verdict{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin:24px 0}.card,.panel{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:20px}.card strong{display:block;font-size:30px}.card span,.note,small{display:block;color:var(--muted)}.fail{color:var(--red);font-weight:750}.pass{color:var(--green);font-weight:750}.panel{margin-top:16px}.warning{border-left:5px solid var(--red);background:#f8e7e2;padding:16px 18px;border-radius:8px;margin-top:16px}.success{border-left-color:var(--green);background:#e5f2e9}.table-wrap{overflow:auto}table{width:100%;border-collapse:collapse;min-width:980px}th,td{text-align:right;border-bottom:1px solid var(--line);padding:11px 9px;white-space:nowrap}th:first-child{text-align:left}thead th{color:var(--muted);font-size:12px}code{font-size:11px;word-break:break-all;white-space:normal}.footer{color:var(--muted);font-size:12px;margin-top:24px}@media(max-width:900px){.verdict{grid-template-columns:1fr 1fr}}@media(max-width:600px){.verdict{grid-template-columns:1fr}main{padding:24px 12px 56px}.panel{padding:14px}}
    """
    if paper_ok:
        headline = "經濟門檻全過，<br>只准開始隔離 Paper。"
        decision = "16 道經濟與跨期入口全過；這只授權從零開始收集 Paper 證據。" + (
            "四道歷史統計也通過，但仍須前瞻驗證。"
            if history_ok
            else f"仍有 {len(stat_failed)} 道歷史統計門檻失敗，不能實金參考。"
        )
    else:
        headline = "仍未跨過 Paper，<br>不把成長持倉比率當 alpha。"
        decision = f"16 道 Paper 入口有 {len(paper_failed)} 道失敗；封存結果、不建立組合。"
    content = f"""<!doctype html><html lang="zh-Hant-HK"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>v8 永遠持股相對成長研究收據</title><style>{css}</style></head><body><main>
    <header><div class="eyebrow">FROZEN ALWAYS-INVESTED AUDIT</div><h1>{headline}</h1><p class="lead">v8 永遠持有 100% 股票：50% 固定 SPY，另一半只有在 QQQ 相對強勢且仍在 200 日移動平均線上時才換成 QQQ，否則也持有 SPY。因此和 SPY 基準的差異只來自成長傾斜，不再混入轉債券所降低的市場持倉比率。</p></header>
    <section class="verdict"><article class="card"><span>Paper 經濟入口</span><strong class={"pass" if paper_ok else "fail"}>{audit["paper_entry_passed_gate_count"]} / {audit["paper_entry_required_gate_count"]}</strong><small>全過才准建立新 Paper 模擬組合</small></article><article class="card"><span>全部歷史門檻</span><strong class={"pass" if history_ok else "fail"}>{audit["passed_gate_count"]} / {audit["required_gate_count"]}</strong><small>含 NW 與 PSR</small></article><article class="card"><span>主期策略 / SPY CAGR</span><strong>{_pct(strategy["cagr"], 2)} / {_pct(spy["cagr"], 2)}</strong><small>差 {_pct(strategy["cagr"] - spy["cagr"], 2)}</small></article><article class="card"><span>最後歷史權重</span><strong>{html.escape(current)}</strong><small>{"只供 Paper 起點" if paper_ok else "淘汰研究，不可照單"}</small></article></section>
    <div class="warning {"success" if paper_ok else ""}"><b>研究決定：{"只建立隔離 v8 Paper，不顯示成實金訊號。" if paper_ok else "不建立 v8 Paper，不調參救援。"}</b><br>{decision}</div>
    <section class="panel"><h2>同樣 100% 股票，才是公平問題</h2><p>SPY 與 v8 每一天都維持完整股票持倉比率。v8 若勝出，才可能歸因於 QQQ 相對強勢傾斜；它不再能靠持有 SHY、少承擔市場風險來改善最大跌幅或 Sharpe。固定 50/50 與 QQQ 仍列作機會成本背景，但 Paper 入口的 hard benchmark 是 SPY。</p></section>
    <section class="panel"><h2>近期與舊期分開驗證</h2><div class="table-wrap"><table><thead><tr><th>數據段</th><th>策略 CAGR</th><th>市場 CAGR</th><th>年率化差</th><th>最大跌幅：策略 / 市場</th><th>五年勝率</th><th>NW t</th><th>PSR</th></tr></thead><tbody>{period_rows}</tbody></table></div></section>
    <section class="panel"><h2>二十道凍結歷史門檻</h2><p class="note">經濟／跨期入口通過 {audit["paper_entry_passed_gate_count"]} / {audit["paper_entry_required_gate_count"]}；全部歷史通過 {audit["passed_gate_count"]} / {audit["required_gate_count"]}。Paper 是取得新數據，不是實金授權。</p><div class="table-wrap"><table><thead><tr><th>固定檢查鍵</th><th>結果</th></tr></thead><tbody>{gate_rows}</tbody></table></div></section>
    <section class="panel"><h2>選擇偏誤與不可竄改收據</h2><p>本規則是看過 v7 後派生，已計入 6,105 次搜尋；主期 DSR 為 {_pct(audit["global_dsr_promotion_sensitivity"]["main"]["probability"], 3)}，代理期為 {_pct(audit["global_dsr_promotion_sensitivity"]["proxy"]["probability"], 3)}。協議 SHA-256：<code>{html.escape(audit["protocol"]["sha256"])}</code></p></section>
    <p class="footer">歷史回測、研究與教育用途，不構成投資建議。價格指數代理不含股息；Paper 通過也不等於可實金參考。</p>
    </main></body></html>"""
    destination.write_text(_with_report_references(content), encoding="utf-8")
    return destination


def build_low_turnover_report(destination: str | Path, audit: dict[str, Any]) -> Path:
    """Write the beginner-readable receipt for the frozen v9 external test."""
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    main = audit["main"]
    paper_ok = bool(audit["paper_eligible"])
    history_ok = bool(audit["historically_confirmed"])
    failed_paper = [key for key, value in audit["paper_entry_gates"].items() if not value]
    failed_stats = [key for key, value in audit["statistical_gates"].items() if not value]
    strategy = main["strategy_metrics"]
    spy = main["benchmark_metrics"]["market"]
    policy = "、".join(
        f"{ticker} {weight:.0%}"
        for ticker, weight in main["current_policy_allocation"].items()
        if weight > 0.0
    )
    gate_rows = "".join(
        "<tr>"
        f"<th>{html.escape(key.replace('_', ' '))}</th>"
        f"<td class={'pass' if value else 'fail'}>{'通過' if value else '失敗'}</td>"
        "</tr>"
        for key, value in audit["gates"].items()
    )

    def period_row(label: str, data: dict[str, Any], note: str) -> str:
        sm = data["strategy_metrics"]
        bm = data["benchmark_metrics"]["market"]
        cmp = data["comparison"]
        rolling = data["rolling_five_year"]["summary"]
        signal = data["signals"]
        return (
            f"<tr><th>{html.escape(label)}<small>{html.escape(note)}</small></th>"
            f"<td>{_pct(sm['cagr'], 2)} / {_pct(bm['cagr'], 2)}</td>"
            f"<td>{_pct(cmp['cagr_difference'], 2)}</td>"
            f"<td>{_pct(data['cost_50bps']['cagr_difference'], 2)}</td>"
            f"<td>{_pct(sm['max_drawdown'], 1)} / {_pct(bm['max_drawdown'], 1)}</td>"
            f"<td>{_pct(sm['turnover'], 1)}</td>"
            f"<td>{signal['completed_executions_in_formal_period']}</td>"
            f"<td>{_pct(rolling.get('cagr_win_fraction', float('nan')), 1)}</td>"
            f"<td>{_num(cmp['active_return_newey_west']['t_stat'])}</td>"
            f"<td>{_pct(cmp['active_probabilistic_sharpe']['probability'], 1)}</td></tr>"
        )

    period_rows = "".join(
        [
            period_row(
                "可交易 ETF 主期",
                audit["main"],
                "2006-07-31–2026-07-31；SPY／QQQ 經調整總回報",
            ),
            period_row(
                "已看過的舊代理",
                audit["old_proxy"],
                "1989-01-03–2006-07-28；S&P 500／Nasdaq-100 價格指數",
            ),
            period_row(
                "下載前未見外部期",
                audit["external"],
                "1973-01-03–1988-12-30；S&P 500／Nasdaq Composite 價格指數",
            ),
        ]
    )
    dsr = audit["global_dsr_promotion_sensitivity"]
    css = """
    :root{--ink:#17241e;--muted:#66736b;--paper:#f5f1e8;--panel:#fffdf8;--line:#d8d1c3;--red:#a83a31;--green:#176846;--gold:#b47b1d}
    *{box-sizing:border-box}body{margin:0;background:var(--paper);color:var(--ink);font:15px/1.55 ui-sans-serif,system-ui,-apple-system,"PingFang TC","Noto Sans TC",sans-serif}main{max-width:1220px;margin:auto;padding:42px 22px 80px}header{border-bottom:3px solid var(--ink);padding-bottom:24px}.eyebrow{font-weight:800;letter-spacing:.13em;color:var(--gold)}h1{font-size:clamp(34px,7vw,68px);line-height:1.03;margin:8px 0 16px;letter-spacing:-.05em}h2{margin:0 0 14px;font-size:24px}.lead{max-width:940px;font-size:18px}.verdict{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin:24px 0}.card,.panel{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:20px}.card strong{display:block;font-size:30px}.card span,.note,small{display:block;color:var(--muted)}.fail{color:var(--red);font-weight:750}.pass{color:var(--green);font-weight:750}.panel{margin-top:16px}.warning{border-left:5px solid var(--red);background:#f8e7e2;padding:16px 18px;border-radius:8px;margin-top:16px}.success{border-left-color:var(--green);background:#e5f2e9}.table-wrap{overflow:auto}table{width:100%;border-collapse:collapse;min-width:1120px}th,td{text-align:right;border-bottom:1px solid var(--line);padding:11px 9px;white-space:nowrap}th:first-child{text-align:left}thead th{color:var(--muted);font-size:12px}code{font-size:11px;word-break:break-all;white-space:normal}.footer{color:var(--muted);font-size:12px;margin-top:24px}@media(max-width:900px){.verdict{grid-template-columns:1fr 1fr}}@media(max-width:600px){.verdict{grid-template-columns:1fr}main{padding:24px 12px 56px}.panel{padding:14px}}
    """
    if paper_ok:
        headline = "低換手結構通過入口，<br>也只准從 Paper 開始。"
        decision = "23 道經濟、跨期、持倉比率與數據門檻全過；可以建立全新隔離 Paper。" + (
            "六道歷史統計也全過，但仍不能跳過前瞻期。"
            if history_ok
            else f"仍有 {len(failed_stats)} 道歷史統計門檻失敗，不能稱為已確認 alpha。"
        )
    else:
        headline = "外部年代已驗證，<br>仍未取得 Paper 資格。"
        decision = (
            f"23 道 Paper 入口有 {len(failed_paper)} 道失敗；保留完整負結果，"
            "不建立組合，也不回頭調整 60/40 或門檻。"
        )
    content = f"""<!doctype html><html lang="zh-Hant-HK"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>v9 低換手外部驗證研究收據</title><style>{css}</style></head><body><main>
    <header><div class="eyebrow">FROZEN LOW-TURNOVER EXTERNAL AUDIT</div><h1>{headline}</h1><p class="lead">v9 永遠持有 100% 股票：平時 100% 廣泛市場；只有成長市場的 12–1 相對強度領先、且仍在 200 日移動平均線上時，才改成 60% 核心／40% 成長。每月檢查，但只在狀態改變時成交，兩次切換間讓持倉自然漂移。</p></header>
    <section class="verdict"><article class="card"><span>Paper 入口</span><strong class={"pass" if paper_ok else "fail"}>{audit["paper_entry_passed_gate_count"]} / {audit["paper_entry_required_gate_count"]}</strong><small>三段經濟門檻全過才算</small></article><article class="card"><span>全部歷史門檻</span><strong class={"pass" if history_ok else "fail"}>{audit["passed_gate_count"]} / {audit["required_gate_count"]}</strong><small>另含 NW 與 PSR</small></article><article class="card"><span>主期策略 / SPY CAGR</span><strong>{_pct(strategy["cagr"], 2)} / {_pct(spy["cagr"], 2)}</strong><small>50 bps 差 {_pct(main["cost_50bps"]["cagr_difference"], 2)}</small></article><article class="card"><span>最新研究狀態</span><strong>{html.escape(policy)}</strong><small>{"只供 Paper 新模擬組合" if paper_ok else "淘汰研究，不可照單"}</small></article></section>
    <div class="warning {"success" if paper_ok else ""}"><b>研究決定：{"可建立隔離 v9 Paper，但不顯示成實金訊號。" if paper_ok else "不建立 v9 Paper，不調參救援。"}</b><br>{decision}</div>
    <section class="panel"><h2>「每月判斷」不等於「每月交易」</h2><p>模型每個完整月末都重算狀態，但狀態沒變就不落盤。報表把完成成交數與年換手直接列出；最後的 60/40 或 100/0 是政策狀態，不是要求既有持有人每月把漂移權重拉回目標。</p></section>
    <section class="panel"><h2>三個不重疊年代</h2><p class="note">前兩段曾用於舊研究；第三段在協議與數據契約鎖定後才首次下載。Nasdaq Composite 比 Nasdaq-100 更廣，而且代理期都是不含股息的價格指數，因此只能檢驗機制。</p><div class="table-wrap"><table><thead><tr><th>數據段</th><th>策略 / 市場 CAGR</th><th>年率化差</th><th>50 bps 年率化差</th><th>最大跌幅：策略 / 市場</th><th>年換手</th><th>完成交易</th><th>五年勝率</th><th>NW t</th><th>PSR</th></tr></thead><tbody>{period_rows}</tbody></table></div></section>
    <section class="panel"><h2>二十九道凍結歷史門檻</h2><p class="note">Paper 入口通過 {audit["paper_entry_passed_gate_count"]} / {audit["paper_entry_required_gate_count"]}；全部歷史通過 {audit["passed_gate_count"]} / {audit["required_gate_count"]}。任一入口失敗都不開 Paper。</p><div class="table-wrap"><table><thead><tr><th>固定檢查鍵</th><th>結果</th></tr></thead><tbody>{gate_rows}</tbody></table></div></section>
    <section class="panel"><h2>搜尋偏誤與前瞻缺口</h2><p>v9 是看過 v8 後才提出，已計入 6,106 次搜尋。DSR：主期 {_pct(dsr["main"]["probability"], 3)}、舊代理 {_pct(dsr["old_proxy"]["probability"], 3)}、全新外部 {_pct(dsr["external"]["probability"], 3)}。即使歷史門檻通過，仍須 252 個新增交易日與 6 次實際完成的狀態切換，且前瞻 NW t、PSR、SPY 超額與最大跌幅全部達標。</p></section>
    <section class="panel"><h2>不可回改的數據收據</h2><p>研究協議 SHA-256：<code>{html.escape(audit["protocol"]["sha256"])}</code><br>外部數據契約 SHA-256：<code>{html.escape(audit["protocol"]["external_data_contract_sha256"])}</code><br>Nasdaq Composite panel：<code>{html.escape(audit["data_receipts"]["external_ixic"]["panel_sha256"])}</code><br>外部 S&amp;P 500 panel：<code>{html.escape(audit["data_receipts"]["external_gspc"]["panel_sha256"])}</code></p></section>
    <p class="footer">歷史回測、研究與教育用途，不構成投資建議。代理指數不含股息；Paper 通過也不等於可實金參考。</p>
    </main></body></html>"""
    destination.write_text(_with_report_references(content), encoding="utf-8")
    return destination


def build_hierarchical_defense_report(destination: str | Path, audit: dict[str, Any]) -> Path:
    """Write the beginner-readable v12 three-state research receipt."""
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    main = audit["main"]
    paper_ok = bool(audit["paper_eligible"])
    history_ok = bool(audit["historically_confirmed"])
    strategy = main["strategy_metrics"]
    spy = main["benchmark_metrics"]["market"]
    failed_paper = [key for key, value in audit["paper_entry_gates"].items() if not value]
    failed_stats = [key for key, value in audit["statistical_gates"].items() if not value]
    policy = "、".join(
        f"{ticker} {weight:.0%}"
        for ticker, weight in main["current_policy_allocation"].items()
        if weight > 0.0
    )
    gate_rows = "".join(
        "<tr>"
        f"<th>{html.escape(key.replace('_', ' '))}</th>"
        f"<td class={'pass' if value else 'fail'}>{'通過' if value else '失敗'}</td>"
        "</tr>"
        for key, value in audit["gates"].items()
    )

    def period_row(label: str, data: dict[str, Any], note: str) -> str:
        sm = data["strategy_metrics"]
        bm = data["benchmark_metrics"]["market"]
        cmp = data["comparison"]
        rolling = data["rolling_five_year"]["summary"]
        signal = data["signals"]
        counts = signal["state_month_counts"]
        return (
            f"<tr><th>{html.escape(label)}<small>{html.escape(note)}</small></th>"
            f"<td>{_pct(sm['cagr'], 2)} / {_pct(bm['cagr'], 2)}</td>"
            f"<td>{_pct(cmp['cagr_difference'], 2)}</td>"
            f"<td>{_pct(data['cost_50bps']['cagr_difference'], 2)}</td>"
            f"<td>{_pct(sm['max_drawdown'], 1)} / {_pct(bm['max_drawdown'], 1)}</td>"
            f"<td>{_pct(sm['turnover'], 1)}</td>"
            f"<td>{signal['completed_executions_in_formal_period']}</td>"
            f"<td>{counts['growth']} / {counts['core']} / {counts['defense']}</td>"
            f"<td>{_pct(rolling.get('cagr_win_fraction', float('nan')), 1)}</td>"
            f"<td>{_num(cmp['active_return_newey_west']['t_stat'])}</td>"
            f"<td>{_pct(cmp['active_probabilistic_sharpe']['probability'], 1)}</td></tr>"
        )

    period_rows = "".join(
        [
            period_row(
                "可交易 ETF 主期",
                audit["main"],
                "2006-07-31–2026-07-31；SPY／QQQ／SHY 經調整總回報",
            ),
            period_row(
                "舊 Nasdaq-100 代理",
                audit["old_proxy"],
                "1989-01-03–2006-07-28；價格指數＋零利息 CASH",
            ),
            period_row(
                "Nasdaq Composite 外部期",
                audit["external"],
                "1973-01-03–1988-12-30；價格指數＋零利息 CASH",
            ),
        ]
    )
    dsr = audit["global_dsr_promotion_sensitivity"]
    css = """
    :root{--ink:#17241e;--muted:#66736b;--paper:#f5f1e8;--panel:#fffdf8;--line:#d8d1c3;--red:#a83a31;--green:#176846;--gold:#b47b1d}
    *{box-sizing:border-box}body{margin:0;background:var(--paper);color:var(--ink);font:15px/1.55 ui-sans-serif,system-ui,-apple-system,"PingFang TC","Noto Sans TC",sans-serif}main{max-width:1240px;margin:auto;padding:42px 22px 80px}header{border-bottom:3px solid var(--ink);padding-bottom:24px}.eyebrow{font-weight:800;letter-spacing:.13em;color:var(--gold)}h1{font-size:clamp(34px,7vw,68px);line-height:1.03;margin:8px 0 16px;letter-spacing:-.05em}h2{margin:0 0 14px;font-size:24px}.lead{max-width:940px;font-size:18px}.verdict{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin:24px 0}.card,.panel{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:20px}.card strong{display:block;font-size:30px}.card span,.note,small{display:block;color:var(--muted)}.fail{color:var(--red);font-weight:750}.pass{color:var(--green);font-weight:750}.panel{margin-top:16px}.warning{border-left:5px solid var(--red);background:#f8e7e2;padding:16px 18px;border-radius:8px;margin-top:16px}.success{border-left-color:var(--green);background:#e5f2e9}.table-wrap{overflow:auto}table{width:100%;border-collapse:collapse;min-width:1180px}th,td{text-align:right;border-bottom:1px solid var(--line);padding:11px 9px;white-space:nowrap}th:first-child{text-align:left}thead th{color:var(--muted);font-size:12px}code{font-size:11px;word-break:break-all;white-space:normal}.footer{color:var(--muted);font-size:12px;margin-top:24px}@media(max-width:900px){.verdict{grid-template-columns:1fr 1fr}}@media(max-width:600px){.verdict{grid-template-columns:1fr}main{padding:24px 12px 56px}.panel{padding:14px}}
    """
    if paper_ok:
        headline = "三態風險政策通過入口，<br>仍只准從 Paper 開始。"
        decision = "23 道經濟、跨期、持倉比率與數據門檻全過；可以建立全新隔離 Paper。" + (
            "六道歷史統計也全過，但仍不能跳過前瞻期。"
            if history_ok
            else f"仍有 {len(failed_stats)} 道歷史統計門檻失敗，不能稱為已確認 alpha。"
        )
    else:
        headline = "三段歷史已跑完，<br>仍未取得 Paper 資格。"
        decision = (
            f"23 道 Paper 入口有 {len(failed_paper)} 道失敗；保留完整負結果，"
            "不建立組合，也不回頭調整 60/40、三態順序或門檻。"
        )
    content = f"""<!doctype html><html lang="zh-Hant-HK"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>v12 階層式三態研究收據</title><style>{css}</style></head><body><main>
    <header><div class="eyebrow">FROZEN THREE-STATE RISK AUDIT</div><h1>{headline}</h1><p class="lead">v12 永久保留 60% 核心市場。剩下 40% 先看成長相對強度與 200 日趨勢；不符合時看核心自己的 200 日趨勢；再不符合才轉防守。每月判斷，但只有 growth／core／defense 狀態改變才交易。</p></header>
    <section class="verdict"><article class="card"><span>Paper 入口</span><strong class={"pass" if paper_ok else "fail"}>{audit["paper_entry_passed_gate_count"]} / {audit["paper_entry_required_gate_count"]}</strong><small>三段經濟與數據門檻</small></article><article class="card"><span>全部歷史門檻</span><strong class={"pass" if history_ok else "fail"}>{audit["passed_gate_count"]} / {audit["required_gate_count"]}</strong><small>另含 NW 與 PSR</small></article><article class="card"><span>主期策略 / SPY CAGR</span><strong>{_pct(strategy["cagr"], 2)} / {_pct(spy["cagr"], 2)}</strong><small>50 bps 差 {_pct(main["cost_50bps"]["cagr_difference"], 2)}</small></article><article class="card"><span>最新研究狀態</span><strong>{html.escape(policy)}</strong><small>{"只供新 Paper" if paper_ok else "淘汰研究，不可照單"}</small></article></section>
    <div class="warning {"success" if paper_ok else ""}"><b>研究決定：{"可建立隔離 v12 Paper，但不顯示成實金訊號。" if paper_ok else "不建立 v12 Paper，不調參救援。"}</b><br>{decision}</div>
    <section class="panel"><h2>初學投資者版三態</h2><p><b>growth：</b>60% 核心＋40% 成長；<b>core：</b>100% 核心；<b>defense：</b>60% 核心＋40% 防守。表中的月數只是每月底判斷結果；完成交易數才是真正換倉次數。兩次換倉間持倉會自然漂移，不要求每月拉回 60/40。</p></section>
    <section class="panel"><h2>三個不重疊年代</h2><p class="note">只有主期是可交易 ETF 總回報；B/C 是不含股息的價格指數機制測試，防守又刻意設為零利息 CASH，所以不可把三段串成一條實際投資表現。</p><div class="table-wrap"><table><thead><tr><th>數據段</th><th>策略 / 市場 CAGR</th><th>年率化差</th><th>50 bps 年率化差</th><th>最大跌幅：策略 / 市場</th><th>年換手</th><th>完成交易</th><th>月數 G/C/D</th><th>五年勝率</th><th>NW t</th><th>PSR</th></tr></thead><tbody>{period_rows}</tbody></table></div></section>
    <section class="panel"><h2>二十九道凍結歷史門檻</h2><p class="note">Paper 入口通過 {audit["paper_entry_passed_gate_count"]} / {audit["paper_entry_required_gate_count"]}；全部歷史通過 {audit["passed_gate_count"]} / {audit["required_gate_count"]}。任一入口失敗都不開 Paper。</p><div class="table-wrap"><table><thead><tr><th>固定檢查鍵</th><th>結果</th></tr></thead><tbody>{gate_rows}</tbody></table></div></section>
    <section class="panel"><h2>兩次 DJIA 取數失敗沒有被隱藏</h2><p>v10 的 Yahoo 來源沒有 1971–1988 DJIA；v11 事前指定的 S&amp;P DJI 官方 Excel 唯一一次 GET 回覆 403。兩次都在任何策略計算前封存，v12 沒有重試、補值或替換來源，只用既有三段凍結數據第一次計算同一套規則。</p></section>
    <section class="panel"><h2>搜尋偏誤與前瞻缺口</h2><p>DSR 以 6,109 次搜尋計算：主期 {_pct(dsr["main"]["probability"], 3)}、舊代理 {_pct(dsr["old_proxy"]["probability"], 3)}、外部期 {_pct(dsr["external"]["probability"], 3)}。仍須 252 個新增交易日與 6 次實際完成的狀態切換，且前瞻 NW t、PSR、SPY 超額與最大跌幅全部達標，才可評估實金參考。</p></section>
    <section class="panel"><h2>不可回改收據</h2><p>v12 協議：<code>{html.escape(audit["protocol"]["sha256"])}</code><br>v10 失敗收據：<code>{html.escape(audit["data_receipts"]["v10_failure"]["receipt_file"]["sha256"])}</code><br>v11 失敗收據：<code>{html.escape(audit["data_receipts"]["v11_failure"]["receipt_file"]["sha256"])}</code></p></section>
    <p class="footer">歷史回測、研究與教育用途，不構成投資建議。Paper 通過也不等於可實金參考。</p>
    </main></body></html>"""
    destination.write_text(_with_report_references(content), encoding="utf-8")
    return destination


def _rolling_rows(validations: dict[str, Any], results: list[BacktestResult]) -> str:
    rows = []
    for result in results:
        item = validations.get("rolling_3y", {}).get(result.name, {}).get("summary", {})
        rows.append(
            f"<tr><th>{html.escape(result.name)}</th>"
            f"<td>{_pct(item.get('latest_cagr', float('nan')))}</td>"
            f"<td>{_pct(item.get('median_cagr', float('nan')))}</td>"
            f"<td>{_pct(item.get('worst_cagr', float('nan')))}</td>"
            f"<td>{_pct(item.get('positive_cagr_fraction', float('nan')))}</td>"
            f"<td>{_pct(item.get('worst_max_drawdown', float('nan')))}</td></tr>"
        )
    return "".join(rows)


def build_report(
    destination: str | Path,
    *,
    panel: MarketPanel,
    contract: ContractResult,
    manifest: dict[str, Any],
    headline_results: list[BacktestResult],
    stock_results: list[BacktestResult],
    stock_screen: pd.DataFrame,
    validations: dict[str, Any],
) -> Path:
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    spy = panel.close["SPY"].dropna()
    spy_trend = float(spy.iloc[-1] / spy.rolling(200).mean().iloc[-1] - 1.0)
    vix = panel.close["^VIX"].dropna() if "^VIX" in panel.close else pd.Series(dtype=float)
    vix_last = float(vix.iloc[-1]) if len(vix) else float("nan")
    latest = panel.end.strftime("%Y-%m-%d")
    research_start = min(result.equity.index[0] for result in headline_results)
    research_end = max(result.equity.index[-1] for result in headline_results)
    research_years = (research_end - research_start).days / 365.2425
    archive_hash = manifest.get("archive_sha256", "未提供")
    chart = _equity_svg(headline_results)

    css = """
    :root{--bg:#0b1220;--panel:#121d30;--panel2:#17253a;--text:#ecf2f8;--muted:#9eafc1;--line:#263a54;--green:#61d3a5;--red:#ff7f7f;--gold:#ffbd69}
    *{box-sizing:border-box}body{margin:0;background:linear-gradient(145deg,#07101e,#101b2a 48%,#0a1624);color:var(--text);font:15px/1.55 ui-sans-serif,system-ui,-apple-system,"PingFang TC","Noto Sans TC",sans-serif}
    main{max-width:1180px;margin:auto;padding:36px 24px 80px}header{display:grid;grid-template-columns:1fr auto;gap:24px;align-items:end;margin-bottom:28px}.eyebrow{color:var(--green);font-weight:700;letter-spacing:.12em;text-transform:uppercase}h1{font-size:clamp(32px,6vw,62px);line-height:1.05;margin:8px 0 14px;letter-spacing:-.04em}h2{font-size:24px;margin:0 0 16px}h3{margin:0 0 10px}.lead{max-width:780px;color:#c5d2df;font-size:17px}.stamp{padding:12px 16px;border:1px solid var(--line);border-radius:12px;color:var(--muted);white-space:nowrap}a{color:var(--green)}
    .grid4{display:grid;grid-template-columns:repeat(4,1fr);gap:14px}.kpi,.panel,.allocation{background:rgba(18,29,48,.9);border:1px solid var(--line);border-radius:16px}.kpi{padding:18px}.kpi span{display:block;color:var(--muted);font-size:13px}.kpi strong{font-size:28px}.panel{padding:22px;margin-top:16px;overflow:hidden}.panel-head{display:flex;justify-content:space-between;gap:20px;align-items:baseline}.panel-head p,.fine{color:var(--muted);font-size:13px}.allocations{display:grid;grid-template-columns:repeat(2,1fr);gap:14px}.allocation{padding:18px;background:var(--panel2)}.pills{display:flex;flex-wrap:wrap;gap:8px}.pill{padding:7px 10px;border:1px solid #35506e;border-radius:999px;background:#0e1a2a}
    table{width:100%;border-collapse:collapse;min-width:720px}th,td{text-align:right;padding:11px 10px;border-bottom:1px solid var(--line);white-space:nowrap}th:first-child,td:first-child{text-align:left}thead th{color:var(--muted);font-size:12px;text-transform:uppercase;letter-spacing:.05em}tbody th{font-weight:650}td small{display:block;color:var(--muted)}.table-wrap{overflow:auto}.good{color:var(--green)}.bad{color:var(--red)}.warn{border-left:4px solid var(--gold);padding:14px 16px;background:#261f15;border-radius:8px}.ok{border-left:4px solid var(--green);padding:14px 16px;background:#10251f;border-radius:8px}.grid{stroke:#24364e;stroke-width:1}.axis,.legend{fill:#9eafc1;font-size:11px}svg{width:100%;height:auto}.notes{display:grid;grid-template-columns:1fr 1fr;gap:16px}.notes article{background:#0e1a2a;padding:16px;border-radius:12px}.notes p{color:#b7c5d3}.footer{color:var(--muted);font-size:12px;margin-top:24px}.hash{font-family:ui-monospace,SFMono-Regular,monospace;word-break:break-all}
    @media(max-width:780px){header{grid-template-columns:1fr}.grid4,.allocations,.notes{grid-template-columns:1fr}.stamp{white-space:normal}main{padding:24px 14px 60px}.panel{padding:16px}}
    """
    content = f"""<!doctype html><html lang="zh-Hant-HK"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>US FDDK 美股研究台</title><style>{css}</style></head><body><main>
    <header><div><div class="eyebrow">Evidence-first US market research</div><h1>美股數據與策略研究台</h1><p class="lead">把 20 年市場數據、訊號、成交、基準與驗證放在同一張可重現的收據上。主策略只使用 ETF 避免把今天的成分股名單誤當成歷史；個股區是當期觀察清單，不是買賣指令。</p><p><a href="paper_volatility.html">開啟成長守門員 v2 LIVE Paper →</a>　<a href="paper_growth.html">v1 封存組合</a>　<a href="paper_candidate.html">平衡候選組合</a></p></div><div class="stamp">研究區間<br><strong>{research_start.date()}–{research_end.date()}</strong><br>數據截止 {latest}</div></header>
    <section class="grid4"><div class="kpi"><span>研究期間</span><strong>{research_years:.1f} 年</strong></div><div class="kpi"><span>SPY 相對 200 日線</span><strong class="{"good" if spy_trend >= 0 else "bad"}">{_pct(spy_trend)}</strong></div><div class="kpi"><span>VIX</span><strong>{_num(vix_last, 1)}</strong></div><div class="kpi"><span>數據契約</span><strong class="{"good" if contract.ok else "bad"}">{"通過" if contract.ok else "未通過"}</strong></div></section>
    <section class="panel"><div class="panel-head"><div><h2>ETF 主線：同一時鐘、同一成本</h2><p>月末收市產生訊號，下一交易日開市成交；含雙邊換手成本。表內 Sharpe 是零利率口徑，下一節另列扣除 SHY 後的標準超額口徑。</p></div></div>{chart}<div class="table-wrap"><table><thead><tr><th>策略</th><th>累積回報</th><th>CAGR</th><th>波幅</th><th>Sharpe（0%）</th><th>Sortino</th><th>最大跌幅</th><th>Calmar</th><th>年換手</th><th>換倉次數</th></tr></thead><tbody>{_metrics_table(headline_results)}</tbody></table></div></section>
    <section class="panel"><div class="panel-head"><div><h2>v3 隔離研究：主樣本過關，代理期淘汰</h2><p>完整保留看似漂亮的 QQQ 超額，也把較舊年代的失敗放在同一份報表；主網站不會因單一 20 年結果而換訊號。</p></div></div>{_v3_evidence(validations)}</section>
    <section class="panel"><div class="panel-head"><h2>v3 三層硬門檻</h2><p>QQQ、固定 96/4 持倉比率控制與 1986–2006 代理期分開判讀；代理期任何硬門檻失敗就不升級。</p></div><div class="table-wrap"><table><thead><tr><th>層級</th><th>檢查</th><th>結果</th></tr></thead><tbody>{_v3_gate_rows(validations)}</tbody></table></div></section>
    <section class="panel"><div class="panel-head"><h2>v3 確認期鄰域</h2><p>一、二、三個月全部保留；兩個月是凍結中點，不能刪除較弱的兩側結果。</p></div><div class="table-wrap"><table><thead><tr><th>確認</th><th>角色</th><th>CAGR</th><th>Sharpe</th><th>MDD</th><th>相對 QQQ</th><th>25 bps 相對 QQQ</th></tr></thead><tbody>{_v3_family_rows(validations)}</tbody></table></div></section>
    <section class="panel"><div class="panel-head"><div><h2>Paper-only 風險管理候選：成長守門員 v2</h2><p>以無槓桿波幅管理降低 QQQ 最大跌幅；新增持倉比率匹配基準後，不能再只用勝過 SPY 當作 alpha 證據。</p></div></div>{_volatility_guard_evidence(validations)}</section>
    <section class="panel"><div class="panel-head"><h2>v2 預先定義的歷史門檻</h2><p>十項必須全部通過；統計與 LIVE 另設關卡，不能用歷史門檻取代。</p></div><div class="table-wrap"><table><thead><tr><th>檢查</th><th>結果</th></tr></thead><tbody>{_volatility_gate_rows(validations)}</tbody></table></div></section>
    <section class="panel"><div class="panel-head"><h2>新增的持倉比率控制稽核：被動 90% QQQ／10% SHY</h2><p>這組稽核是在 v2 選定後補上，因此不能冒充預先註冊；它用簡單月末重新平衡組合回答「波幅管理是否真的優於相近 QQQ 持倉比率」。任一一致性門檻失敗，就只保留 Paper，不升級成參考落盤策略。</p></div><div class="table-wrap"><table><thead><tr><th>檢查</th><th>結果</th></tr></thead><tbody>{_exposure_control_gate_rows(validations)}</tbody></table></div></section>
    <section class="panel"><div class="panel-head"><h2>v2 波幅窗／目標波幅鄰域</h2><p>只有 3×3 共九組。18% 是中間風險政策；22% 回報更高、14% 最大跌幅更低，故 18% 不是端點贏家。</p></div><div class="table-wrap"><table><thead><tr><th>波幅窗</th><th>目標波幅</th><th>角色</th><th>CAGR</th><th>Sharpe</th><th>MDD</th><th>相對 SPY CAGR</th></tr></thead><tbody>{_volatility_family_rows(validations)}</tbody></table></div></section>
    <section class="panel"><div class="panel-head"><h2>v2 成本惡化</h2><p>5–100 bps 重新成交；同時比較 SPY 與低換手的被動 90/10，避免動態策略只在低成本假設下看起來領先。</p></div><div class="table-wrap"><table><thead><tr><th>成本 bps</th><th>CAGR</th><th>Sharpe</th><th>MDD</th><th>相對 SPY CAGR</th><th>被動 90/10 CAGR</th><th>相對 90/10 CAGR</th></tr></thead><tbody>{_volatility_cost_rows(validations)}</tbody></table></div></section>
    <section class="panel"><div class="panel-head"><div><h2>v1 封存比較：永久 80% QQQ＋趨勢核心</h2><p>v1 仍完整保留，但因 v2 同時提高 CAGR 並降低最大跌幅，不再作網站主訊號。</p></div></div>{_growth_guard_evidence(validations)}</section>
    <section class="panel"><div class="panel-head"><h2>v1 歷史門檻</h2><p>封存時的所有門檻照原樣保留，避免 v2 出現後重寫舊決策。</p></div><div class="table-wrap"><table><thead><tr><th>檢查</th><th>結果</th></tr></thead><tbody>{_growth_gate_rows(validations)}</tbody></table></div></section>
    <section class="panel"><div class="panel-head"><h2>v1 成長／防守比例鄰域</h2><p>80/20 是當時的風險政策上限，不是鄰域中最高回報的一列。</p></div><div class="table-wrap"><table><thead><tr><th>趨勢核心</th><th>QQQ 衛星</th><th>角色</th><th>CAGR</th><th>Sharpe</th><th>MDD</th><th>相對 SPY CAGR</th></tr></thead><tbody>{_growth_family_rows(validations)}</tbody></table></div></section>
    <section class="panel"><div class="panel-head"><h2>v1 成本惡化</h2><p>5–50 bps 重新成交；比較欄使用同一成本假設下的 SPY。</p></div><div class="table-wrap"><table><thead><tr><th>成本 bps</th><th>CAGR</th><th>Sharpe</th><th>MDD</th><th>相對 SPY CAGR</th></tr></thead><tbody>{_growth_cost_rows(validations)}</tbody></table></div></section>
    <section class="panel"><div class="panel-head"><h2>v1 固定政策 2012 至今</h2><p>每段都固定 80/20，不在折間重選；這仍不是完全獨立的走勢外樣本。</p></div><div class="table-wrap"><table><thead><tr><th>期間</th><th>核心比例</th><th>CAGR</th><th>Sharpe</th><th>MDD</th><th>相對 SPY CAGR</th></tr></thead><tbody>{_growth_walk_rows(validations)}</tbody></table></div></section>
    <section class="panel"><div class="panel-head"><div><h2>較低風險研究線：Sharpe &gt; 1 關卡</h2><p>另一候選是 75% 多資產趨勢／風險核心＋25% QQQ；SHY 是可交易的短債／無風險代理，必須從回報中扣除。</p></div></div>{_candidate_evidence(validations)}</section>
    <section class="panel"><div class="panel-head"><h2>候選的參數鄰域</h2><p>只改核心比例；同時列出零利率與 SHY 超額 Sharpe，避免低波幅短債把結果灌高。</p></div><div class="table-wrap"><table><thead><tr><th>核心比例</th><th>角色</th><th>CAGR</th><th>Sharpe（0%）</th><th>Sharpe（超額）</th><th>MDD</th><th>年換手</th></tr></thead><tbody>{_candidate_neighborhood_rows(validations)}</tbody></table></div></section>
    <section class="panel"><div class="panel-head"><h2>候選的成本惡化</h2><p>5–50 bps 都重新跑完整成交，並以兩種 Sharpe 口徑檢查結論。</p></div><div class="table-wrap"><table><thead><tr><th>成本 bps</th><th>CAGR</th><th>Sharpe（0%）</th><th>Sharpe（超額）</th><th>MDD</th></tr></thead><tbody>{_candidate_cost_rows(validations)}</tbody></table></div></section>
    <section class="panel"><div class="panel-head"><h2>展開式兩年走勢外檢查</h2><p>每一段只用當時以前的數據在 60%–90% 核心比例中選擇；2012 年起串接，含切換成本。這仍是歷史模擬，不是 LIVE 成績。</p></div><div class="table-wrap"><table><thead><tr><th>測試期間</th><th>當時選擇</th><th>CAGR</th><th>Sharpe（0%）</th><th>Sharpe（超額）</th><th>MDD</th></tr></thead><tbody>{_walk_forward_rows(validations)}</tbody></table></div></section>
    <section class="panel"><div class="panel-head"><h2>搜尋帳本與負結果</h2><p>下表涵蓋原始與 33 檔擴充 ETF 凍結快照；DSR 採 6,000 次保守上限，連中止、作廢與已規劃組合都算入，不只計成功列。前七列是零利率 Sharpe；擴充池列已明示為 SHY 超額口徑。</p></div><div class="table-wrap"><table><thead><tr><th>策略家族</th><th>已評估</th><th>最佳 Sharpe</th><th>備註</th></tr></thead><tbody>{_search_audit_rows(validations)}</tbody></table></div></section>
    <section class="panel"><h2>最近目標配置</h2><div class="allocations">{_allocation_cards(headline_results)}</div></section>
    <section class="panel"><div class="panel-head"><h2>與基準的成對檢驗</h2><p>Newey–West 修正自相關；|t| &lt; 1.96 不作「勝過基準」宣稱。</p></div><div class="table-wrap"><table><thead><tr><th>比較</th><th>CAGR 差</th><th>年率化平均主動回報</th><th>NW t</th><th>判讀</th></tr></thead><tbody>{_validation_rows(validations)}</tbody></table></div></section>
    <section class="panel"><div class="panel-head"><h2>雜訊帶，不只單點數字</h2><p>21 日區塊 bootstrap，保留一部分時間叢聚；區間不是未來保證。</p></div><div class="table-wrap"><table><thead><tr><th>策略</th><th>中位 CAGR</th><th>95% 區間</th><th>P(CAGR&lt;0)</th></tr></thead><tbody>{_bootstrap_rows(validations)}</tbody></table></div></section>
    <section class="panel"><div class="panel-head"><h2>前後十年分段</h2><p>每格依序是 CAGR／Sharpe／最大跌幅；檢查結論是否只由單一時代支撐。</p></div><div class="table-wrap"><table><thead><tr><th>期間</th>{"".join(f"<th>{html.escape(result.name)}</th>" for result in headline_results)}</tr></thead><tbody>{_subperiod_rows(validations, headline_results)}</tbody></table></div></section>
    <section class="panel"><div class="panel-head"><h2>三次壓力期</h2><p>每格依序是區間回報／區間內最大跌幅；日期在研究前固定，不按結果挑選。</p></div><div class="table-wrap"><table><thead><tr><th>壓力期</th>{"".join(f"<th>{html.escape(result.name)}</th>" for result in headline_results)}</tr></thead><tbody>{_stress_rows(validations, headline_results)}</tbody></table></div></section>
    <section class="panel"><div class="panel-head"><h2>滾動三年穩定度</h2><p>以每個月末回看 756 個交易日，避免只靠單一 20 年起訖點。</p></div><div class="table-wrap"><table><thead><tr><th>策略</th><th>最近 CAGR</th><th>中位 CAGR</th><th>最差 CAGR</th><th>正 CAGR 比例</th><th>最深 MDD</th></tr></thead><tbody>{_rolling_rows(validations, headline_results)}</tbody></table></div></section>
    <section class="panel"><div class="panel-head"><h2>逐年結果</h2><p>同一年橫向比較，避免全期 CAGR 掩蓋策略在不同市場環境的差異。</p></div><div class="table-wrap"><table><thead><tr><th>年份</th>{"".join(f"<th>{html.escape(result.name)}</th>" for result in headline_results)}</tr></thead><tbody>{_annual_rows(headline_results)}</tbody></table></div></section>
    <section class="panel"><div class="panel-head"><h2>原雙動量參數與成本鄰域</h2><p>完整列出鄰域，不挑事後最高回報；原設定為 252 日、Top 4、10 bps，保留作候選策略以外的基準與負結果。</p></div><div class="table-wrap"><table><thead><tr><th>回顧日</th><th>Top K</th><th>成本 bps</th><th>CAGR</th><th>Sharpe</th><th>MDD</th></tr></thead><tbody>{_sensitivity_rows(validations)}</tbody></table></div></section>
    <section class="panel"><div class="panel-head"><div><h2>大型股當期觀察</h2><p>12–1 月動量 45%＋6–1 月動量 25%＋200 日趨勢 20%＋低波幅 10%。名單是 {html.escape(str(stock_screen["universe_as_of"].iloc[0] if len(stock_screen) else "—"))} 快照，因此不拿它做無偏歷史表現宣稱。</p></div></div><div class="table-wrap"><table><thead><tr><th>代號</th><th>產業</th><th>分數</th><th>12–1 月</th><th>距 200MA</th><th>年率化波幅</th></tr></thead><tbody>{_screen_rows(stock_screen)}</tbody></table></div></section>
    <section class="panel"><h2>個股傾斜診斷（有生存者偏誤）</h2><div class="warn">這一區只回答「在今天這批大型股內，廣泛持有後再做權重傾斜，是否值得繼續研究」。它不能證明歷史可交易，因為缺少逐期成分股與下市股票。</div><div class="table-wrap"><table><thead><tr><th>策略</th><th>累積回報</th><th>CAGR</th><th>波幅</th><th>Sharpe</th><th>Sortino</th><th>最大跌幅</th><th>Calmar</th><th>年換手</th><th>換倉次數</th></tr></thead><tbody>{_metrics_table(stock_results)}</tbody></table></div></section>
    <section class="panel"><h2>設計邊界</h2><div class="notes"><article><h3>我們採用</h3><p>凍結原始快照、經調整 OHLC 一致、前一日訊號、成本敏感度、廣泛持有後傾斜、SPY／等權池雙基準、負結果與不顯著結果照樣呈現。</p></article><article><h3>我們不假裝</h3><p>FINRA 場外數據有彙總與發布延遲，不能反推即時「大戶買入」；SEC 財報是申報日後才可用；今天的 S&amp;P 500 持股不是過去的成分股；免費市場數據可能回溯修訂。</p></article></div></section>
    <section class="panel"><h2>數據收據</h2><p class="{"ok" if contract.ok else "warn"}">{"數據契約通過。" if contract.ok else "數據契約未通過，結果不得發布。"} {html.escape("；".join(contract.warnings))}</p><p>供應商：{html.escape(str(panel.metadata.get("provider", "—")))}<br>還原方式：{html.escape(str(panel.metadata.get("adjustment", "—")))}<br>快照 SHA-256：<span class="hash">{html.escape(str(archive_hash))}</span></p></section>
    <p class="footer">研究與教育用途，不構成投資建議。回測不含稅務、融資、申購限制與市場衝擊；實際成交可能與模型顯著不同。</p>
    </main></body></html>"""
    destination.write_text(_with_report_references(content), encoding="utf-8")
    return destination


def build_confirmed_relative_growth_report(destination: str | Path, audit: dict[str, Any]) -> Path:
    """Write the beginner-readable v13 frozen new-ETF validation receipt."""
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    paper_ok = bool(audit["paper_eligible"])
    datasets = audit["datasets"]

    def dataset_row(key: str, data: dict[str, Any]) -> str:
        assets = data["assets"]
        if data["status"] != "completed":
            diagnostic = data.get("diagnostic") or {}
            diag_text = "—"
            if diagnostic:
                diag_text = (
                    f"診斷期 {_pct(diagnostic['strategy_metrics']['cagr'], 2)} / "
                    f"{_pct(diagnostic['market_metrics']['cagr'], 2)}"
                )
            return (
                f"<tr><th>{html.escape(data['label'])}<small>"
                f"{html.escape(assets['growth'])} / {html.escape(assets['core'])}"
                f"</small></th><td class=fail>暖機失敗</td>"
                f"<td>{data['warmup_common_sessions']} / 252</td>"
                f"<td colspan=6>{html.escape(data['failure'])}</td>"
                f"<td>{html.escape(diag_text)}</td></tr>"
            )
        strategy = data["strategy_metrics"]
        market = data["benchmark_metrics"]["market"]
        matched = data["benchmark_metrics"]["matched"]
        rolling = data["rolling_five_year"]["summary"]
        comparison = data["comparison"]
        passed = int(sum(data["economic_gates"].values()))
        return (
            f"<tr><th>{html.escape(data['label'])}<small>"
            f"{html.escape(assets['growth'])} / {html.escape(assets['core'])}"
            f"</small></th><td class={'pass' if passed == 10 else 'fail'}>{passed} / 10</td>"
            f"<td>{data['warmup_common_sessions']} / 252</td>"
            f"<td>{_pct(strategy['cagr'], 2)} / {_pct(market['cagr'], 2)}</td>"
            f"<td>{_pct(comparison['cagr_difference'], 2)}</td>"
            f"<td>{_pct(data['cost_50bps']['cagr_difference'], 2)}</td>"
            f"<td>{_pct(strategy['max_drawdown'], 1)} / {_pct(market['max_drawdown'], 1)}</td>"
            f"<td>{_pct(strategy['cagr'] - matched['cagr'], 2)}</td>"
            f"<td>{_pct(rolling.get('cagr_win_fraction', float('nan')), 1)}</td>"
            f"<td>{_num(comparison['active_return_newey_west']['t_stat'])}</td></tr>"
        )

    dataset_rows = "".join(dataset_row(key, data) for key, data in datasets.items())
    economic_rows = "".join(
        "<tr>"
        f"<th>{html.escape(key.replace('_', ' '))}</th>"
        f"<td class={'pass' if value else 'fail'}>{'通過' if value else '失敗'}</td>"
        "</tr>"
        for key, value in audit["economic_gates"].items()
    )
    data_rows = "".join(
        "<tr>"
        f"<th>{html.escape(key.replace('_', ' '))}</th>"
        f"<td class={'pass' if value else 'fail'}>{'通過' if value else '失敗'}</td>"
        "</tr>"
        for key, value in audit["data_gates"].items()
    )
    css = """
    :root{--ink:#17241e;--muted:#66736b;--paper:#f5f1e8;--panel:#fffdf8;--line:#d8d1c3;--red:#a83a31;--green:#176846;--gold:#b47b1d}
    *{box-sizing:border-box}body{margin:0;background:var(--paper);color:var(--ink);font:15px/1.55 ui-sans-serif,system-ui,-apple-system,"PingFang TC","Noto Sans TC",sans-serif}main{max-width:1240px;margin:auto;padding:42px 22px 80px}header{border-bottom:3px solid var(--ink);padding-bottom:24px}.eyebrow{font-weight:800;letter-spacing:.13em;color:var(--gold)}h1{font-size:clamp(34px,7vw,68px);line-height:1.03;margin:8px 0 16px;letter-spacing:-.05em}h2{margin:0 0 14px;font-size:24px}.lead{max-width:940px;font-size:18px}.verdict{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin:24px 0}.card,.panel{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:20px}.card strong{display:block;font-size:30px}.card span,.note,small{display:block;color:var(--muted)}.fail{color:var(--red);font-weight:750}.pass{color:var(--green);font-weight:750}.panel{margin-top:16px}.warning{border-left:5px solid var(--red);background:#f8e7e2;padding:16px 18px;border-radius:8px;margin-top:16px}.success{border-left-color:var(--green);background:#e5f2e9}.table-wrap{overflow:auto}table{width:100%;border-collapse:collapse;min-width:1120px}th,td{text-align:right;border-bottom:1px solid var(--line);padding:11px 9px;white-space:nowrap}th:first-child{text-align:left}thead th{color:var(--muted);font-size:12px}code{font-size:11px;word-break:break-all;white-space:normal}a{color:var(--green)}.footer{color:var(--muted);font-size:12px;margin-top:24px}@media(max-width:900px){.verdict{grid-template-columns:1fr 1fr}}@media(max-width:600px){.verdict{grid-template-columns:1fr}main{padding:24px 12px 56px}.panel{padding:14px}}
    """
    headline = (
        "新 ETF 驗證全過，<br>也只准開始隔離 Paper。"
        if paper_ok
        else "新 ETF 已給答案：<br>這版不能進 Paper。"
    )
    decision = (
        "30 道新數據經濟門檻與數據完整性全過；仍須獨立前瞻期。"
        if paper_ok
        else (
            "固定規則在 Russell 1000 與 Russell 2000 都無法穩定跑贏核心 ETF；"
            "EAFE 組在固定起點前又少於 252 日暖機。依下載前協議封存，不換代號、"
            "不延後起點，也不建立 v13 Paper。"
        )
    )
    content = f"""<!doctype html><html lang="zh-Hant-HK"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>v13 兩月確認相對成長新 ETF 驗證</title><style>{css}</style></head><body><main>
    <header><div class="eyebrow">FROZEN NEW-ETF VALIDATION</div><h1>{headline}</h1><p class="lead">v13 先用兩個月確認降低假切換：成長成立時持有 40% 核心／60% 成長；成長關閉但市場仍健康時回到 100% 核心；兩者都弱時才用 30% 短債。規則先寫死，之後才下載三組從未用過的 ETF 配對。</p></header>
    <section class="verdict"><article class="card"><span>新數據經濟門檻</span><strong class={"pass" if audit["economic_passed_gate_count"] == audit["economic_required_gate_count"] else "fail"}>{audit["economic_passed_gate_count"]} / {audit["economic_required_gate_count"]}</strong><small>三組各十道，全過才算</small></article><article class="card"><span>數據與暖機</span><strong class={"pass" if audit["data_passed_gate_count"] == audit["data_required_gate_count"] else "fail"}>{audit["data_passed_gate_count"]} / {audit["data_required_gate_count"]}</strong><small>固定起點不可事後移動</small></article><article class="card"><span>歷史統計門檻</span><strong class={"pass" if audit["statistical_passed_gate_count"] == audit["statistical_required_gate_count"] else "fail"}>{audit["statistical_passed_gate_count"]} / {audit["statistical_required_gate_count"]}</strong><small>NW、PSR、DSR</small></article><article class="card"><span>Paper 決定</span><strong class={"pass" if paper_ok else "fail"}>{"可建立" if paper_ok else "不建立"}</strong><small>不能顯示落盤配置</small></article></section>
    <div class="warning {"success" if paper_ok else ""}"><b>結論：{"只准新建隔離 Paper。" if paper_ok else "新樣本否決候選。"}</b><br>{decision}</div>
    <section class="panel"><h2>初學投資者先看這裡</h2><p>「最大跌幅較小」不等於「策略有超額回報」。Russell 1000 組雖把最大跌幅從 {_pct(datasets["russell_1000"]["benchmark_metrics"]["market"]["max_drawdown"], 1)} 降到 {_pct(datasets["russell_1000"]["strategy_metrics"]["max_drawdown"], 1)}，20 年 CAGR 卻由 {_pct(datasets["russell_1000"]["benchmark_metrics"]["market"]["cagr"], 2)} 降為 {_pct(datasets["russell_1000"]["strategy_metrics"]["cagr"], 2)}；Russell 2000 也落後。若只挑「比較不痛」而忽略「長期少賺」，就會把風險控制誤當成 alpha。</p></section>
    <section class="panel"><h2>三組下載後才第一次計算的 ETF</h2><div class="table-wrap"><table><thead><tr><th>驗證組</th><th>門檻</th><th>暖機</th><th>策略 / 核心 CAGR</th><th>10 bps 年率化差</th><th>50 bps 年率化差</th><th>最大跌幅：策略 / 核心</th><th>相對同狀態對照</th><th>五年勝率</th><th>NW t</th></tr></thead><tbody>{dataset_rows}</tbody></table></div></section>
    <section class="panel"><h2>為什麼這比再調參重要</h2><p>既有三年代讓兩月確認版本看起來有希望；但那些數據已參與提出規則，不能再當獨立證據。新的大中型、小型與海外 ETF 是在協議凍結後才下載，結果直接反駁「能跨股票母體穩健跑贏」的說法。正確動作是保留負結果，而不是把 40/60、70/30 或兩個月改成另一個看起來較漂亮的數字。</p></section>
    <section class="panel"><h2>三十道新數據經濟門檻</h2><div class="table-wrap"><table><thead><tr><th>固定檢查鍵</th><th>結果</th></tr></thead><tbody>{economic_rows}</tbody></table></div></section>
    <section class="panel"><h2>數據與暖機門檻</h2><div class="table-wrap"><table><thead><tr><th>固定檢查鍵</th><th>結果</th></tr></thead><tbody>{data_rows}</tbody></table></div></section>
    <section class="panel"><h2>相關資產與不可回改收據</h2><p><a href="https://www.ishares.com/us/products/239706/">IWF</a> 追蹤 Russell 1000 Growth Index；<a href="https://www.ishares.com/us/products/239707/">IWB</a> 追蹤 Russell 1000 Index。其餘兩組同樣以發行人定義與凍結的經調整市場數據驗證。協議 SHA-256：<code>{html.escape(audit["protocol"]["sha256"])}</code><br>新 ETF 面板 SHA-256：<code>{html.escape(audit["snapshot"]["panel_sha256"])}</code></p></section>
    <p class="footer">歷史回測、研究與教育用途，不構成投資建議。淘汰研究的最後政策狀態不是落盤訊號。</p>
    </main></body></html>"""
    destination.write_text(_with_report_references(content), encoding="utf-8")
    return destination


def build_modest_leverage_report(destination: str | Path, audit: dict[str, Any]) -> Path:
    """Write the beginner-readable v14 pre-registered leveraged-ETF validation."""
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    paper_ok = bool(audit["paper_eligible"])

    rows: list[str] = []
    for data in audit["datasets"].values():
        assets = data["assets"]
        passed = int(sum(data["economic_gates"].values()))
        if data["status"] != "completed":
            rows.append(
                f"<tr><th>{html.escape(data['label'])}<small>"
                f"{html.escape(assets['leveraged'])} / {html.escape(assets['core'])}"
                f"</small></th><td class=fail>{passed} / 12</td>"
                f"<td colspan=8>{html.escape(data['failure'])}</td></tr>"
            )
            continue
        strategy = data["strategy_metrics"]
        core = data["benchmark_metrics"]["core"]
        fixed = data["benchmark_metrics"]["fixed_60_40"]
        core_comparison = data["comparison_vs_core"]
        fixed_comparison = data["comparison_vs_fixed_60_40"]
        rolling = data["rolling_five_year_vs_core"]["summary"]
        rows.append(
            f"<tr><th>{html.escape(data['label'])}<small>"
            f"{html.escape(assets['leveraged'])} / {html.escape(assets['core'])}"
            f"</small></th><td class={'pass' if passed == 12 else 'fail'}>{passed} / 12</td>"
            f"<td>{_pct(strategy['cagr'], 2)}</td><td>{_pct(core['cagr'], 2)}</td>"
            f"<td>{_pct(fixed['cagr'], 2)}</td>"
            f"<td>{_pct(core_comparison['cagr_difference'], 2)}</td>"
            f"<td>{_pct(fixed_comparison['cagr_difference'], 2)}</td>"
            f"<td>{_pct(strategy['max_drawdown'], 1)} / {_pct(core['max_drawdown'], 1)}</td>"
            f"<td>{_pct(rolling.get('cagr_win_fraction', float('nan')), 1)}</td>"
            f"<td>{_num(core_comparison['active_return_newey_west']['t_stat'])}</td></tr>"
        )
    dataset_rows = "".join(rows)
    economic_rows = "".join(
        "<tr>"
        f"<th>{html.escape(key.replace('_', ' '))}</th>"
        f"<td class={'pass' if value else 'fail'}>{'通過' if value else '失敗'}</td>"
        "</tr>"
        for key, value in audit["economic_gates"].items()
    )
    data_rows = "".join(
        "<tr>"
        f"<th>{html.escape(key.replace('_', ' '))}</th>"
        f"<td class={'pass' if value else 'fail'}>{'通過' if value else '失敗'}</td>"
        "</tr>"
        for key, value in audit["data_gates"].items()
    )
    css = """
    :root{--ink:#17241e;--muted:#66736b;--paper:#f5f1e8;--panel:#fffdf8;--line:#d8d1c3;--red:#a83a31;--green:#176846;--gold:#b47b1d}
    *{box-sizing:border-box}body{margin:0;background:var(--paper);color:var(--ink);font:15px/1.55 ui-sans-serif,system-ui,-apple-system,"PingFang TC","Noto Sans TC",sans-serif}main{max-width:1240px;margin:auto;padding:42px 22px 80px}header{border-bottom:3px solid var(--ink);padding-bottom:24px}.eyebrow{font-weight:800;letter-spacing:.13em;color:var(--gold)}h1{font-size:clamp(34px,7vw,68px);line-height:1.03;margin:8px 0 16px;letter-spacing:-.05em}h2{margin:0 0 14px;font-size:24px}.lead{max-width:940px;font-size:18px}.verdict{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin:24px 0}.card,.panel{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:20px}.card strong{display:block;font-size:30px}.card span,.note,small{display:block;color:var(--muted)}.fail{color:var(--red);font-weight:750}.pass{color:var(--green);font-weight:750}.panel{margin-top:16px}.warning{border-left:5px solid var(--red);background:#f8e7e2;padding:16px 18px;border-radius:8px;margin-top:16px}.success{border-left-color:var(--green);background:#e5f2e9}.table-wrap{overflow:auto}table{width:100%;border-collapse:collapse;min-width:1120px}th,td{text-align:right;border-bottom:1px solid var(--line);padding:11px 9px;white-space:nowrap}th:first-child{text-align:left}thead th{color:var(--muted);font-size:12px}code{font-size:11px;word-break:break-all;white-space:normal}a{color:var(--green)}.footer{color:var(--muted);font-size:12px;margin-top:24px}@media(max-width:900px){.verdict{grid-template-columns:1fr 1fr}}@media(max-width:600px){.verdict{grid-template-columns:1fr}main{padding:24px 12px 56px}.panel{padding:14px}}
    """
    sp500 = audit["datasets"]["sp500"]
    nasdaq = audit["datasets"]["nasdaq100"]
    dow = audit["datasets"]["dow30"]
    headline = (
        "三市場全數通過，<br>也只准開始隔離 Paper。"
        if paper_ok
        else "實際槓桿 ETF 已回答：<br>這版不能進 Paper。"
    )
    decision = (
        "36 道經濟門檻與所有數據門檻全過；仍須統計與前瞻期。"
        if paper_ok
        else (
            "S&P 500 與 Dow 30 的長期回報落後原始 ETF；Nasdaq-100 雖略勝 QQQ，"
            "仍落後不擇時的同產品 60/40。依預先協議封存，不調比例、不建立 v14 Paper。"
        )
    )
    content = f"""<!doctype html><html lang="zh-Hant-HK"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>v14 小幅槓桿趨勢驗證</title><style>{css}</style></head><body><main>
    <header><div class="eyebrow">PRE-REGISTERED LEVERAGED-ETF VALIDATION</div><h1>{headline}</h1><p class="lead">v14 只做一件事：市場連續兩個完整月高於 200 日移動平均線時，持有 60% 實際 2 倍每日目標 ETF／40% SHY；確認轉弱時改為 100% SHY。比例、成本、三組代號與 36 道門檻先寫死，之後才下載 SSO、QLD、DDM。</p></header>
    <section class="verdict"><article class="card"><span>經濟門檻</span><strong class={"pass" if audit["economic_passed_gate_count"] == audit["economic_required_gate_count"] else "fail"}>{audit["economic_passed_gate_count"]} / {audit["economic_required_gate_count"]}</strong><small>三組各 12 道，任一失敗即淘汰</small></article><article class="card"><span>數據與時序</span><strong class={"pass" if audit["data_passed_gate_count"] == audit["data_required_gate_count"] else "fail"}>{audit["data_passed_gate_count"]} / {audit["data_required_gate_count"]}</strong><small>先凍結，再下載與計算</small></article><article class="card"><span>統計門檻</span><strong class={"pass" if audit["statistical_passed_gate_count"] == audit["statistical_required_gate_count"] else "fail"}>{audit["statistical_passed_gate_count"]} / {audit["statistical_required_gate_count"]}</strong><small>相對原始 ETF 與固定 60/40</small></article><article class="card"><span>Paper 決定</span><strong class={"pass" if paper_ok else "fail"}>{"可建立" if paper_ok else "不建立"}</strong><small>失敗候選不顯示落盤比例</small></article></section>
    <div class="warning {"success" if paper_ok else ""}"><b>結論：{"只准開始隔離 Paper。" if paper_ok else "新數據否決候選。"}</b><br>{decision}</div>
    <section class="panel"><h2>初學投資者先看：槓桿不是免費回報</h2><p>2 倍 ETF 追求的是「每日」兩倍，不是二十年回報一定兩倍。每日重設、費用、波幅與複利都會改變長期結果。即使只把 60% 放入 2 倍 ETF，風險開啟時仍約有 120% 名目股票持倉比率，可能比普通 ETF 跌得更多；所以本研究直接使用真實基金價格，並要求同時比較原始 ETF 與固定 60/40。</p></section>
    <section class="panel"><h2>20 年三市場結果</h2><div class="table-wrap"><table><thead><tr><th>市場</th><th>門檻</th><th>策略 CAGR</th><th>原始 ETF</th><th>固定 60/40</th><th>相對原始</th><th>相對 60/40</th><th>最大跌幅：策略 / 原始</th><th>五年勝率</th><th>NW t</th></tr></thead><tbody>{dataset_rows}</tbody></table></div></section>
    <section class="panel"><h2>這次真正學到什麼</h2><p>S&P 500 為 {_pct(sp500["strategy_metrics"]["cagr"], 2)}，低於 SPY 的 {_pct(sp500["benchmark_metrics"]["core"]["cagr"], 2)}；Dow 30 為 {_pct(dow["strategy_metrics"]["cagr"], 2)}，低於 DIA 的 {_pct(dow["benchmark_metrics"]["core"]["cagr"], 2)}。Nasdaq-100 的 {_pct(nasdaq["strategy_metrics"]["cagr"], 2)} 雖略高於 QQQ 的 {_pct(nasdaq["benchmark_metrics"]["core"]["cagr"], 2)}，仍低於固定 60/40 的 {_pct(nasdaq["benchmark_metrics"]["fixed_60_40"]["cagr"], 2)}。這表示較好的 Nasdaq 結果主要不能證明趨勢開關創造了穩健 alpha。</p></section>
    <section class="panel"><h2>36 道預先固定的經濟門檻</h2><div class="table-wrap"><table><thead><tr><th>固定檢查鍵</th><th>結果</th></tr></thead><tbody>{economic_rows}</tbody></table></div></section>
    <section class="panel"><h2>數據、時序與權重門檻</h2><div class="table-wrap"><table><thead><tr><th>固定檢查鍵</th><th>結果</th></tr></thead><tbody>{data_rows}</tbody></table></div></section>
    <section class="panel"><h2>官方產品定義與不可回改收據</h2><p><a href="https://www.proshares.com/our-etfs/leveraged-and-inverse/sso">SSO</a>、<a href="https://www.proshares.com/our-etfs/leveraged-and-inverse/qld">QLD</a>、<a href="https://www.proshares.com/our-etfs/leveraged-and-inverse/ddm">DDM</a> 都是每日 2 倍目標產品。協議 SHA-256：<code>{html.escape(audit["protocol"]["sha256"])}</code><br>新 ETF 面板 SHA-256：<code>{html.escape(audit["snapshot"]["panel_sha256"])}</code></p></section>
    <p class="footer">歷史回測、研究與教育用途，不構成投資建議。槓桿 ETF 可能快速且大幅虧損；淘汰研究的最後狀態不是交易訊號。</p>
    </main></body></html>"""
    destination.write_text(_with_report_references(content), encoding="utf-8")
    return destination


def build_modest_leverage_overlay_report(destination: str | Path, audit: dict[str, Any]) -> Path:
    """Write the beginner-readable v15 first-seen 3x ETF validation report."""
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    paper_ok = bool(audit["paper_eligible"])
    dataset_rows: list[str] = []
    for data in audit["datasets"].values():
        passed = int(sum(data["economic_gates"].values()))
        assets = data["assets"]
        if data["status"] != "completed":
            dataset_rows.append(
                f"<tr><th>{html.escape(data['label'])}<small>"
                f"{html.escape(assets['leveraged'])} / {html.escape(assets['core'])}"
                f"</small></th><td class=fail>{passed} / 12</td>"
                f"<td colspan=9>{html.escape(data['failure'])}</td></tr>"
            )
            continue
        strategy = data["strategy_metrics"]
        core = data["benchmark_metrics"]["core"]
        fixed = data["benchmark_metrics"]["fixed_90_10"]
        versus_core = data["comparison_vs_core"]
        versus_fixed = data["comparison_vs_fixed_90_10"]
        rolling = data["rolling_five_year_vs_core"]["summary"]
        dataset_rows.append(
            f"<tr><th>{html.escape(data['label'])}<small>"
            f"{html.escape(assets['leveraged'])} / {html.escape(assets['core'])}"
            f"</small></th><td class={'pass' if passed == 12 else 'fail'}>{passed} / 12</td>"
            f"<td>{_pct(strategy['cagr'], 2)}</td><td>{_pct(core['cagr'], 2)}</td>"
            f"<td>{_pct(fixed['cagr'], 2)}</td>"
            f"<td>{strategy['sharpe']:.2f} / {core['sharpe']:.2f}</td>"
            f"<td>{_pct(strategy['max_drawdown'], 1)} / {_pct(core['max_drawdown'], 1)}</td>"
            f"<td>{_pct(versus_core['cagr_difference'], 2)}</td>"
            f"<td>{_pct(versus_fixed['cagr_difference'], 2)}</td>"
            f"<td>{_pct(rolling.get('cagr_win_fraction', float('nan')), 1)}</td>"
            f"<td>{_num(versus_core['active_return_newey_west']['t_stat'])}</td></tr>"
        )
    economic_rows = "".join(
        "<tr>"
        f"<th>{html.escape(key.replace('_', ' '))}</th>"
        f"<td class={'pass' if value else 'fail'}>{'通過' if value else '失敗'}</td>"
        "</tr>"
        for key, value in audit["economic_gates"].items()
    )
    data_rows = "".join(
        "<tr>"
        f"<th>{html.escape(key.replace('_', ' '))}</th>"
        f"<td class={'pass' if value else 'fail'}>{'通過' if value else '失敗'}</td>"
        "</tr>"
        for key, value in audit["data_gates"].items()
    )
    css = """
    :root{--ink:#17241e;--muted:#66736b;--paper:#f5f1e8;--panel:#fffdf8;--line:#d8d1c3;--red:#a83a31;--green:#176846;--gold:#b47b1d}
    *{box-sizing:border-box}body{margin:0;background:var(--paper);color:var(--ink);font:15px/1.55 ui-sans-serif,system-ui,-apple-system,"PingFang TC","Noto Sans TC",sans-serif}main{max-width:1240px;margin:auto;padding:42px 22px 80px}header{border-bottom:3px solid var(--ink);padding-bottom:24px}.eyebrow{font-weight:800;letter-spacing:.13em;color:var(--gold)}h1{font-size:clamp(34px,7vw,68px);line-height:1.03;margin:8px 0 16px;letter-spacing:-.05em}h2{margin:0 0 14px;font-size:24px}.lead{max-width:940px;font-size:18px}.verdict{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin:24px 0}.card,.panel{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:20px}.card strong{display:block;font-size:30px}.card span,.note,small{display:block;color:var(--muted)}.fail{color:var(--red);font-weight:750}.pass{color:var(--green);font-weight:750}.panel{margin-top:16px}.warning{border-left:5px solid var(--red);background:#f8e7e2;padding:16px 18px;border-radius:8px;margin-top:16px}.success{border-left-color:var(--green);background:#e5f2e9}.table-wrap{overflow:auto}table{width:100%;border-collapse:collapse;min-width:1180px}th,td{text-align:right;border-bottom:1px solid var(--line);padding:11px 9px;white-space:nowrap}th:first-child{text-align:left}thead th{color:var(--muted);font-size:12px}code{font-size:11px;word-break:break-all;white-space:normal}a{color:var(--green)}.footer{color:var(--muted);font-size:12px;margin-top:24px}@media(max-width:900px){.verdict{grid-template-columns:1fr 1fr}}@media(max-width:600px){.verdict{grid-template-columns:1fr}main{padding:24px 12px 56px}.panel{padding:14px}}
    """
    sp500 = audit["datasets"]["sp500"]
    nasdaq = audit["datasets"]["nasdaq100"]
    dow = audit["datasets"]["dow30"]
    headline = (
        "三市場全部通過，<br>也只能開始隔離 Paper。"
        if paper_ok
        else "回報確實較高，<br>但風險證據不合格。"
    )
    decision = (
        "36 道經濟門檻與數據門檻全過；仍不得當成實金訊號。"
        if paper_ok
        else (
            "三組 CAGR 都高於原始 ETF，但 S&P 500、Nasdaq-100、Dow 30 的最大跌幅"
            "也全部更深，三組 Sharpe 都沒有嚴格勝過原始 ETF。依凍結門檻不建 Paper。"
        )
    )
    content = f"""<!doctype html><html lang="zh-Hant-HK"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>v15 小幅槓桿疊加驗證</title><style>{css}</style></head><body><main>
    <header><div class="eyebrow">FIRST-SEEN 3X ETF VALIDATION</div><h1>{headline}</h1><p class="lead">v15 平時持有原始 ETF；只有連續兩個完整月站上 200 日移動平均線時，才改為 90% 原始 ETF／10% 實際每日 3 倍 ETF，把名目股票持倉比率提高到約 120%。規則與 36 道門檻先凍結，之後才首次下載 UPRO、TQQQ、UDOW。</p></header>
    <section class="verdict"><article class="card"><span>經濟門檻</span><strong class={"pass" if audit["economic_passed_gate_count"] == audit["economic_required_gate_count"] else "fail"}>{audit["economic_passed_gate_count"]} / {audit["economic_required_gate_count"]}</strong><small>三市場各 12 道</small></article><article class="card"><span>數據與時序</span><strong class={"pass" if audit["data_passed_gate_count"] == audit["data_required_gate_count"] else "fail"}>{audit["data_passed_gate_count"]} / {audit["data_required_gate_count"]}</strong><small>先凍結，再下載與計算</small></article><article class="card"><span>統計門檻</span><strong class={"pass" if audit["statistical_passed_gate_count"] == audit["statistical_required_gate_count"] else "fail"}>{audit["statistical_passed_gate_count"]} / {audit["statistical_required_gate_count"]}</strong><small>相對原始 ETF 與固定 90/10</small></article><article class="card"><span>Paper 決定</span><strong class={"pass" if paper_ok else "fail"}>{"可建立" if paper_ok else "不建立"}</strong><small>不合格就不顯示比例</small></article></section>
    <div class="warning {"success" if paper_ok else ""}"><b>結論：{"只准開始隔離 Paper。" if paper_ok else "較高回報不等於穩健跑贏。"}</b><br>{decision}</div>
    <section class="panel"><h2>初學投資者先看：為什麼「三組都賺比較多」仍然不合格？</h2><p>加上槓桿本來就可能把多頭市場的回報放大，但使用者同時承受更大的虧損。這次 S&P 500 CAGR {_pct(sp500["strategy_metrics"]["cagr"], 2)} 對 SPY {_pct(sp500["benchmark_metrics"]["core"]["cagr"], 2)}；Nasdaq-100 {_pct(nasdaq["strategy_metrics"]["cagr"], 2)} 對 QQQ {_pct(nasdaq["benchmark_metrics"]["core"]["cagr"], 2)}；Dow 30 {_pct(dow["strategy_metrics"]["cagr"], 2)} 對 DIA {_pct(dow["benchmark_metrics"]["core"]["cagr"], 2)}。但三組最大跌幅全都更深，不能只挑回報欄宣布成功。</p></section>
    <section class="panel"><h2>15 年首次查看的三市場結果</h2><div class="table-wrap"><table><thead><tr><th>市場</th><th>門檻</th><th>策略 CAGR</th><th>原始 ETF</th><th>固定 90/10</th><th>Sharpe：策略 / ETF</th><th>最大跌幅：策略 / ETF</th><th>相對 ETF</th><th>相對固定</th><th>五年勝率</th><th>NW t</th></tr></thead><tbody>{"".join(dataset_rows)}</tbody></table></div></section>
    <section class="panel"><h2>20 年與 15 年不能混寫</h2><p>v14 的 20 年 2 倍 ETF 數據只用來產生這個架構；v15 的確認證據是規則凍結後才看的 3 倍 ETF 實際價格，受產品成立日限制只有 15 年。報告不把兩段拼成「獨立 20 年」。</p></section>
    <section class="panel"><h2>36 道預先固定的經濟門檻</h2><div class="table-wrap"><table><thead><tr><th>固定檢查鍵</th><th>結果</th></tr></thead><tbody>{economic_rows}</tbody></table></div></section>
    <section class="panel"><h2>數據、時序與權重門檻</h2><div class="table-wrap"><table><thead><tr><th>固定檢查鍵</th><th>結果</th></tr></thead><tbody>{data_rows}</tbody></table></div></section>
    <section class="panel"><h2>官方產品定義與不可回改收據</h2><p><a href="https://www.proshares.com/our-etfs/leveraged-and-inverse/upro">UPRO</a>、<a href="https://www.proshares.com/our-etfs/leveraged-and-inverse/tqqq">TQQQ</a>、<a href="https://www.proshares.com/our-etfs/leveraged-and-inverse/udow">UDOW</a> 是每日 3 倍目標產品，不是長期固定三倍。協議 SHA-256：<code>{html.escape(audit["protocol"]["sha256"])}</code><br>新 ETF 面板 SHA-256：<code>{html.escape(audit["snapshot"]["panel_sha256"])}</code></p></section>
    <p class="footer">歷史回測、研究與教育用途，不構成投資建議。槓桿 ETF 可能快速且大幅虧損；淘汰研究不是交易訊號。</p>
    </main></body></html>"""
    destination.write_text(_with_report_references(content), encoding="utf-8")
    return destination


def _research_gate_rows(gates: dict[str, Any]) -> str:
    return "".join(
        "<tr>"
        f"<th>{html.escape(key.replace('_', ' '))}</th>"
        f"<td class={'pass' if value else 'fail'}>{'通過' if value else '失敗'}</td>"
        "</tr>"
        for key, value in gates.items()
    )


def _late_research_css() -> str:
    return """
    :root{--ink:#17241e;--muted:#66736b;--paper:#f5f1e8;--panel:#fffdf8;--line:#d8d1c3;--red:#a83a31;--green:#176846;--gold:#b47b1d}
    *{box-sizing:border-box}body{margin:0;background:var(--paper);color:var(--ink);font:15px/1.55 ui-sans-serif,system-ui,-apple-system,"PingFang TC","Noto Sans TC",sans-serif}main{max-width:1280px;margin:auto;padding:42px 22px 80px}header{border-bottom:3px solid var(--ink);padding-bottom:24px}.eyebrow{font-weight:800;letter-spacing:.13em;color:var(--gold)}h1{font-size:clamp(34px,7vw,68px);line-height:1.03;margin:8px 0 16px;letter-spacing:-.05em}h2{margin:0 0 14px;font-size:24px}.lead{max-width:980px;font-size:18px}.verdict{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin:24px 0}.card,.panel{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:20px}.card strong{display:block;font-size:30px}.card span,.note,small{display:block;color:var(--muted)}.fail{color:var(--red);font-weight:750}.pass{color:var(--green);font-weight:750}.panel{margin-top:16px}.warning{border-left:5px solid var(--red);background:#f8e7e2;padding:16px 18px;border-radius:8px;margin-top:16px}.success{border-left-color:var(--green);background:#e5f2e9}.table-wrap{overflow:auto}table{width:100%;border-collapse:collapse;min-width:1160px}th,td{text-align:right;border-bottom:1px solid var(--line);padding:11px 9px;white-space:nowrap}th:first-child{text-align:left}thead th{color:var(--muted);font-size:12px}code{font-size:11px;word-break:break-all;white-space:normal}a{color:var(--green)}.footer{color:var(--muted);font-size:12px;margin-top:24px}@media(max-width:900px){.verdict{grid-template-columns:1fr 1fr}}@media(max-width:600px){.verdict{grid-template-columns:1fr}main{padding:24px 12px 56px}.panel{padding:14px}}
    """


def build_trend_volatility_brake_report(destination: str | Path, audit: dict[str, Any]) -> Path:
    """Write the beginner-readable v16 weekly trend/volatility validation."""
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    paper_ok = bool(audit["paper_eligible"])
    rows: list[str] = []
    for data in audit["datasets"].values():
        passed = int(sum(data["economic_gates"].values()))
        assets = data["assets"]
        if data["status"] != "completed":
            rows.append(
                f"<tr><th>{html.escape(data['label'])}</th><td class=fail>{passed} / 16</td>"
                f"<td colspan=10>{html.escape(data['failure'])}</td></tr>"
            )
            continue
        strategy = data["strategy_metrics"]
        core = data["benchmark_metrics"]["core"]
        trend = data["benchmark_metrics"]["unlevered_trend"]
        fixed = data["benchmark_metrics"]["fixed_150"]
        rows.append(
            f"<tr><th>{html.escape(data['label'])}<small>"
            f"{html.escape(assets['leveraged'])} / {html.escape(assets['core'])}</small></th>"
            f"<td class={'pass' if passed == 16 else 'fail'}>{passed} / 16</td>"
            f"<td>{_pct(strategy['cagr'], 2)}</td><td>{_pct(core['cagr'], 2)}</td>"
            f"<td>{_pct(trend['cagr'], 2)}</td><td>{_pct(fixed['cagr'], 2)}</td>"
            f"<td>{_num(strategy['sharpe'])} / {_num(core['sharpe'])}</td>"
            f"<td>{_pct(strategy['max_drawdown'], 1)} / {_pct(core['max_drawdown'], 1)}</td>"
            f"<td>{data['signals']['completed_weekly_signals_in_formal_period']}</td>"
            f"<td>{data['signals']['completed_rebalances_in_formal_period']}</td>"
            f"<td>{_num(data['comparison_vs_core']['active_return_newey_west']['t_stat'])}</td></tr>"
        )
    css = _late_research_css()
    headline = "所有門檻全過，仍只准 Paper。" if paper_ok else "煞車太頻繁：這版不能進 Paper。"
    decision = (
        "經濟與數據入口全數通過；仍需統計與 252 個新交易日。"
        if paper_ok
        else "三組都只通過 2/16。退場與週週微調降低了部分最大跌幅，卻大幅犧牲長期回報；依凍結規則封存，不調目標波幅、不建立 v16 Paper。"
    )
    content = f"""<!doctype html><html lang="zh-Hant-HK"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>v16 趨勢與波幅煞車驗證</title><style>{css}</style></head><body><main>
    <header><div class="eyebrow">PRE-REGISTERED WEEKLY RISK BRAKE</div><h1>{headline}</h1><p class="lead">v16 在核心 ETF 高於 200 日移動平均線時，依 21 日實現波幅把股票名目持倉比率固定限制在約 100%–150%；趨勢轉弱時全部進 SHY。訊號只用已完成交易週，下一交易日開市執行。</p></header>
    <section class="verdict"><article class="card"><span>經濟門檻</span><strong class={"pass" if audit["economic_passed_gate_count"] == audit["economic_required_gate_count"] else "fail"}>{audit["economic_passed_gate_count"]} / {audit["economic_required_gate_count"]}</strong><small>三組各 16 道</small></article><article class="card"><span>數據與時序</span><strong class={"pass" if audit["data_passed_gate_count"] == audit["data_required_gate_count"] else "fail"}>{audit["data_passed_gate_count"]} / {audit["data_required_gate_count"]}</strong><small>新 ETF、週末與權重</small></article><article class="card"><span>統計門檻</span><strong class={"pass" if audit["statistical_passed_gate_count"] == audit["statistical_required_gate_count"] else "fail"}>{audit["statistical_passed_gate_count"]} / {audit["statistical_required_gate_count"]}</strong><small>三個公平基準</small></article><article class="card"><span>Paper 決定</span><strong class={"pass" if paper_ok else "fail"}>{"可建立" if paper_ok else "不建立"}</strong><small>淘汰版不顯示配置</small></article></section>
    <div class="warning {"success" if paper_ok else ""}"><b>結論：{"只准隔離 Paper。" if paper_ok else "歷史樣本否決候選。"}</b><br>{decision}</div>
    <section class="panel"><h2>初學投資者先看：少跌一點，可能也少賺很多</h2><p>這個版本不是因為程式壞掉而失敗。它確實在三組市場把最大跌幅壓在約 38%–44%，但年率化回報只剩約 2.8%–5.6%，低於原始 ETF，也低於不加槓桿的相同趨勢控制。週度調整與整體退場造成的踏空，是這次最重要的負面證據。</p></section>
    <section class="panel"><h2>18 年三市場結果</h2><div class="table-wrap"><table><thead><tr><th>市場</th><th>門檻</th><th>策略 CAGR</th><th>原始 ETF</th><th>不槓桿同趨勢</th><th>固定 150%</th><th>Sharpe：策略 / ETF</th><th>最大跌幅：策略 / ETF</th><th>週訊號</th><th>實際換倉</th><th>NW t</th></tr></thead><tbody>{"".join(rows)}</tbody></table></div></section>
    <section class="panel"><h2>為何不是 20 年</h2><p>MVV、UWM、SAA 的實際上市歷史不足完整 20 年，因此本報告保留 2008-07-31 至 2026-07-31 的 18 年正式期；沒有用合成的槓桿回報補齊缺口。</p></section>
    <section class="panel"><h2>48 道固定經濟門檻</h2><div class="table-wrap"><table><thead><tr><th>檢查鍵</th><th>結果</th></tr></thead><tbody>{_research_gate_rows(audit["economic_gates"])}</tbody></table></div></section>
    <section class="panel"><h2>數據與時序門檻</h2><div class="table-wrap"><table><thead><tr><th>檢查鍵</th><th>結果</th></tr></thead><tbody>{_research_gate_rows(audit["data_gates"])}</tbody></table></div></section>
    <section class="panel"><h2>研究依據與收據</h2><p><a href="https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2741701">Leverage for the Long Run</a> 提供長期趨勢槓桿假說；<a href="https://www.nber.org/papers/w22208">Volatility Managed Portfolios</a> 提供反波幅持倉比率的研究動機。它們是待驗證假說，不是本結果保證。協議 SHA-256：<code>{html.escape(audit["protocol"]["sha256"])}</code><br>面板 SHA-256：<code>{html.escape(audit["snapshot"]["panel_sha256"])}</code></p></section>
    <p class="footer">歷史回測、研究與教育用途，不構成投資建議。淘汰研究不是交易訊號。</p>
    </main></body></html>"""
    destination.write_text(_with_report_references(content), encoding="utf-8")
    return destination


def build_capital_efficient_report(destination: str | Path, audit: dict[str, Any]) -> Path:
    """Write the beginner-readable v17 six-market stock/Treasury validation."""
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    paper_ok = bool(audit["paper_eligible"])
    rows: list[str] = []
    for data in audit["datasets"].values():
        passed = int(sum(data["economic_gates"].values()))
        assets = data["assets"]
        if data["status"] != "completed":
            rows.append(
                f"<tr><th>{html.escape(data['label'])}</th><td class=fail>{passed} / 14</td>"
                f"<td colspan=10>{html.escape(data['failure'])}</td></tr>"
            )
            continue
        strategy = data["strategy_metrics"]
        core = data["benchmark_metrics"]["core"]
        unlevered = data["benchmark_metrics"]["unlevered_75_25"]
        shy = data["benchmark_metrics"]["leveraged_60_40_shy"]
        rows.append(
            f"<tr><th>{html.escape(data['label'])}<small>"
            f"{html.escape(assets['leveraged'])} / {html.escape(assets['core'])}</small></th>"
            f"<td>{data['period']['years']} 年</td>"
            f"<td class={'pass' if passed == 14 else 'fail'}>{passed} / 14</td>"
            f"<td>{_pct(strategy['cagr'], 2)}</td><td>{_pct(core['cagr'], 2)}</td>"
            f"<td>{_pct(unlevered['cagr'], 2)}</td><td>{_pct(shy['cagr'], 2)}</td>"
            f"<td>{_num(strategy['sharpe'])} / {_num(core['sharpe'])}</td>"
            f"<td>{_pct(strategy['max_drawdown'], 1)} / {_pct(core['max_drawdown'], 1)}</td>"
            f"<td>{_num(strategy['calmar'])} / {_num(core['calmar'])}</td>"
            f"<td>{_num(data['comparison_vs_core']['active_return_newey_west']['t_stat'])}</td></tr>"
        )
    css = _late_research_css()
    headline = "六市場全部通過，仍只准 Paper。" if paper_ok else "公債有幫助，但仍不夠穩健。"
    decision = (
        "84 道經濟與所有數據入口通過；仍需完整統計與前瞻驗證。"
        if paper_ok
        else "六組大多提高 CAGR，也勝過把 40% 留在 SHY 的對照；但相對原始 ETF 的最大跌幅更深，Sharpe 與 Calmar 多數更差。依凍結協議淘汰，不調股債比例、不建立 v17 Paper。"
    )
    content = f"""<!doctype html><html lang="zh-Hant-HK"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>v17 資本效率股債組合驗證</title><style>{css}</style></head><body><main>
    <header><div class="eyebrow">FROZEN CAPITAL-EFFICIENT TEST</div><h1>{headline}</h1><p class="lead">v17 每月固定持有 60% 實際每日 2 倍股票 ETF 與 40% IEF，約為 120% 股票加 40% 7–10 年美國公債持倉比率。沒有移動平均線、預測、止蝕或事後挑比例。</p></header>
    <section class="verdict"><article class="card"><span>經濟門檻</span><strong class={"pass" if audit["economic_passed_gate_count"] == audit["economic_required_gate_count"] else "fail"}>{audit["economic_passed_gate_count"]} / {audit["economic_required_gate_count"]}</strong><small>六組各 14 道</small></article><article class="card"><span>數據與時序</span><strong class={"pass" if audit["data_passed_gate_count"] == audit["data_required_gate_count"] else "fail"}>{audit["data_passed_gate_count"]} / {audit["data_required_gate_count"]}</strong><small>快照、暖機、月末、權重</small></article><article class="card"><span>統計門檻</span><strong class={"pass" if audit["statistical_passed_gate_count"] == audit["statistical_required_gate_count"] else "fail"}>{audit["statistical_passed_gate_count"]} / {audit["statistical_required_gate_count"]}</strong><small>三基準、NW／PSR／DSR</small></article><article class="card"><span>Paper 決定</span><strong class={"pass" if paper_ok else "fail"}>{"可建立" if paper_ok else "不建立"}</strong><small>失敗即拒絕建立組合</small></article></section>
    <div class="warning {"success" if paper_ok else ""}"><b>結論：{"只准隔離 Paper。" if paper_ok else "不是可參考交易策略。"}</b><br>{decision}</div>
    <section class="panel"><h2>初學投資者先看：回報變高，不代表風險回報變好</h2><p>這個組合的總名目持倉比率約 160%。在六組裡，CAGR 多數比原始 ETF 高約 0.1–1.8 個百分點；可是最大跌幅約為 −58% 至 −63%，比原始 ETF 更深。也就是說，加入 IEF 比留在短債好一些，卻沒有把槓桿股票的尾部風險降到可接受門檻。</p></section>
    <section class="panel"><h2>六市場長期結果</h2><div class="table-wrap"><table><thead><tr><th>市場</th><th>期間</th><th>門檻</th><th>策略 CAGR</th><th>原始 ETF</th><th>未槓桿 75/25</th><th>2x/SHY</th><th>Sharpe：策略 / ETF</th><th>最大跌幅：策略 / ETF</th><th>Calmar：策略 / ETF</th><th>NW t</th></tr></thead><tbody>{"".join(rows)}</tbody></table></div></section>
    <section class="panel"><h2>20 年與 18 年分開標示</h2><p>SPY／SSO、QQQ／QLD、DIA／DDM 有完整 2006-07-31 至 2026-07-31 的 20 年正式期。中小型三組因預先固定的暖機與產品歷史，只能使用 2008-07-31 起的 18 年；報告沒有用合成 ETF 補齊。</p></section>
    <section class="panel"><h2>三個公平基準</h2><p>除了原始 1 倍 ETF，本版同時比較未槓桿的 75% 股票／25% IEF，以及相同約 120% 股票持倉比率但把 40% 放在 SHY 的版本。這能分開回答：超額回報是否只來自加槓桿，以及中期公債是否真的改善結果。</p></section>
    <section class="panel"><h2>84 道固定經濟門檻</h2><div class="table-wrap"><table><thead><tr><th>檢查鍵</th><th>結果</th></tr></thead><tbody>{_research_gate_rows(audit["economic_gates"])}</tbody></table></div></section>
    <section class="panel"><h2>數據與時序門檻</h2><div class="table-wrap"><table><thead><tr><th>檢查鍵</th><th>結果</th></tr></thead><tbody>{_research_gate_rows(audit["data_gates"])}</tbody></table></div></section>
    <section class="panel"><h2>研究概念與不可回改收據</h2><p><a href="https://www.wisdomtree.com/us/products/capital-efficient/ntsx">NTSX 官方產品頁</a>說明股票加美國公債期貨的資本效率概念；本研究直接持有 2 倍 ETF 與 IEF，不是複製 NTSX，也不宣稱相同風險。協議 SHA-256：<code>{html.escape(audit["protocol"]["sha256"])}</code><br>面板 SHA-256：<code>{html.escape(audit["snapshot"]["panel_sha256"])}</code></p></section>
    <p class="footer">歷史回測、研究與教育用途，不構成投資建議。槓桿 ETF 與中期公債都可能虧損，且可能同時下跌。</p>
    </main></body></html>"""
    destination.write_text(_with_report_references(content), encoding="utf-8")
    return destination


def build_equal_diversifier_report(destination: str | Path, audit: dict[str, Any]) -> Path:
    """Write the beginner-readable v18 stock/Treasury/gold external validation."""
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    paper_ok = bool(audit["paper_eligible"])
    rows: list[str] = []
    for data in audit["datasets"].values():
        passed = int(sum(data["economic_gates"].values()))
        assets = data["assets"]
        if data["status"] != "completed":
            rows.append(
                f"<tr><th>{html.escape(data['label'])}</th><td class=fail>{passed} / 9</td>"
                f"<td colspan=10>{html.escape(data['failure'])}</td></tr>"
            )
            continue
        strategy = data["strategy_metrics"]
        core = data["benchmark_metrics"]["core"]
        unlevered = data["benchmark_metrics"]["unlevered_same_assets"]
        rolling = data["rolling_five_year_vs_core"]["summary"]
        first = data["fixed_halves_vs_core"]["first"]["cagr_difference"]
        second = data["fixed_halves_vs_core"]["second"]["cagr_difference"]
        rows.append(
            f"<tr><th>{html.escape(data['label'])}<small>"
            f"{html.escape(assets['leveraged'])} / {html.escape(assets['core'])}</small></th>"
            f"<td class={'pass' if passed == 9 else 'fail'}>{passed} / 9</td>"
            f"<td>{_pct(strategy['cagr'], 2)}</td><td>{_pct(core['cagr'], 2)}</td>"
            f"<td>{_pct(unlevered['cagr'], 2)}</td>"
            f"<td>{_num(strategy['sharpe'])} / {_num(core['sharpe'])}</td>"
            f"<td>{_pct(strategy['max_drawdown'], 1)} / {_pct(core['max_drawdown'], 1)}</td>"
            f"<td>{_num(strategy['calmar'])} / {_num(core['calmar'])}</td>"
            f"<td>{_pct(first, 2)} / {_pct(second, 2)}</td>"
            f"<td>{_pct(rolling.get('cagr_win_fraction', float('nan')), 1)}</td>"
            f"<td>{_num(data['comparisons']['core']['active_return_newey_west']['t_stat'])}</td></tr>"
        )
    css = _late_research_css()
    headline = (
        "海外關卡全過，仍只准隔離 Paper。" if paper_ok else "美國樣本看似可行，海外驗證沒有重現。"
    )
    decision = (
        "18 道外部經濟與所有數據門檻通過；仍需歷史統計與 252 個新交易日。"
        if paper_ok
        else "凍結後的海外日線只通過 5/18 道經濟門檻。已開發市場的 Sharpe、最大跌幅、Calmar、前半期與滾動五年失敗；新興市場更只有 Sharpe 一項通過。依協議不建立 v18 Paper。"
    )
    content = f"""<!doctype html><html lang="zh-Hant-HK"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>v18 等權股債金外部驗證</title><style>{css}</style></head><body><main>
    <header><div class="eyebrow">FROZEN STOCK / BOND / GOLD VALIDATION</div><h1>{headline}</h1><p class="lead">v18 每月固定持有 50% 實際每日 2 倍股票 ETF、25% IEF 與 25% GLD，約為 100% 股票、25% 中期美債、25% 黃金持倉比率。美國六市場只用來選定規則；Paper 決定由凍結後的 EFA/EFO 與 EEM/EET 路徑負責。</p></header>
    <section class="verdict"><article class="card"><span>海外經濟門檻</span><strong class={"pass" if audit["economic_passed_gate_count"] == audit["economic_required_gate_count"] else "fail"}>{audit["economic_passed_gate_count"]} / {audit["economic_required_gate_count"]}</strong><small>兩組各 9 道</small></article><article class="card"><span>數據與時序</span><strong class={"pass" if audit["data_passed_gate_count"] == audit["data_required_gate_count"] else "fail"}>{audit["data_passed_gate_count"]} / {audit["data_required_gate_count"]}</strong><small>先凍結，再下載完整日線</small></article><article class="card"><span>統計門檻</span><strong class={"pass" if audit["statistical_passed_gate_count"] == audit["statistical_required_gate_count"] else "fail"}>{audit["statistical_passed_gate_count"]} / {audit["statistical_required_gate_count"]}</strong><small>核心與同資產不槓桿</small></article><article class="card"><span>Paper 決定</span><strong class={"pass" if paper_ok else "fail"}>{"可建立" if paper_ok else "不建立"}</strong><small>失敗候選不顯示美股配置</small></article></section>
    <div class="warning {"success" if paper_ok else ""}"><b>結論：{"只准隔離 Paper。" if paper_ok else "海外結果否決候選。"}</b><br>{decision}</div>
    <section class="panel"><h2>初學投資者先看：漂亮的 20 年美國回測仍可能過度貼合</h2><p>50/25/25 在六個已見美國市場都提高完整期 CAGR、Sharpe 與 Calmar，也略減最大跌幅；但換到美國以外的 16 年實際 ETF 路徑後，改善沒有穩定重現。這正是外部驗證存在的理由：不是再找一組能過的市場，而是讓先鎖定的規則接受可能被否決的測試。</p></section>
    <section class="panel"><h2>16 年兩組海外結果</h2><div class="table-wrap"><table><thead><tr><th>市場</th><th>門檻</th><th>策略 CAGR</th><th>核心 ETF</th><th>同資產不槓桿</th><th>Sharpe：策略 / 核心</th><th>最大跌幅：策略 / 核心</th><th>Calmar：策略 / 核心</th><th>前 / 後半期 CAGR 差</th><th>五年勝率</th><th>NW t</th></tr></thead><tbody>{"".join(rows)}</tbody></table></div></section>
    <section class="panel"><h2>失敗位置</h2><p>美國以外已開發市場的策略 CAGR 為 8.00%，略高於 EFA 的 7.70%，但 Sharpe 0.490 低於 0.504，最大跌幅 −36.2% 深於 −34.2%，前半期 CAGR 又落後約 0.57 個百分點，滾動五年勝率只有 34.8%。新興市場策略 CAGR 5.12%，僅略高於 EEM 的 4.98%，卻低於同資產不槓桿組合的 5.38%；最大跌幅從 −39.8% 加深至 −46.7%，滾動五年勝率只有 31.1%。</p></section>
    <section class="panel"><h2>為何不是海外 20 年</h2><p>EFO 與 EET 都在 2009 年才成立，所以正式期固定為 2010-07-30 至 2026-07-31。沒有用合成槓桿回報補出不存在的產品歷史。20 年只屬於已見的美國大型股設計樣本，不能與本次外部證據混稱。</p></section>
    <section class="panel"><h2>18 道凍結經濟門檻</h2><div class="table-wrap"><table><thead><tr><th>檢查鍵</th><th>結果</th></tr></thead><tbody>{_research_gate_rows(audit["economic_gates"])}</tbody></table></div></section>
    <section class="panel"><h2>數據、月末與執行門檻</h2><div class="table-wrap"><table><thead><tr><th>檢查鍵</th><th>結果</th></tr></thead><tbody>{_research_gate_rows(audit["data_gates"])}</tbody></table></div></section>
    <section class="panel"><h2>證據邊界與不可回改收據</h2><p>凍結前已看過 EFO/EET 官方成立日與摘要表現，因此這是日線路徑與組合未見的半獨立驗證，不是完全盲測。<a href="https://www.proshares.com/our-etfs/leveraged-and-inverse/efo">EFO</a> 與 <a href="https://www.proshares.com/our-etfs/leveraged-and-inverse/eet">EET</a> 追求每日 2 倍，不保證長期兩倍。協議 SHA-256：<code>{html.escape(audit["protocol"]["sha256"])}</code><br>外部面板 SHA-256：<code>{html.escape(audit["snapshot"]["panel_sha256"])}</code></p></section>
    <p class="footer">歷史回測、研究與教育用途，不構成投資建議。槓桿 ETF、IEF 與 GLD 都可能虧損，也可能同時下跌。</p>
    </main></body></html>"""
    destination.write_text(_with_report_references(content), encoding="utf-8")
    return destination


def build_diversifier_strength_report(destination: str | Path, audit: dict[str, Any]) -> Path:
    """Write the beginner-readable v20 diversifier-rotation validation report."""
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    paper_ok = bool(audit["paper_eligible"])
    rows: list[str] = []
    for data in audit["datasets"].values():
        passed = int(sum(data["economic_gates"].values()))
        strategy = data["strategy_metrics"]
        core = data["benchmark_metrics"]["core"]
        fixed = data["benchmark_metrics"]["fixed_v18"]
        unlevered = data["benchmark_metrics"]["unlevered_same_policy"]
        rolling = data["rolling_five_year_vs_core"]["summary"]
        role = "新外部" if data["evidence_role"] == "new_external_daily_path" else "已見設計"
        rows.append(
            f"<tr><th>{html.escape(data['label'])}<small>{role}｜"
            f"{html.escape(data['assets']['leveraged'])} / "
            f"{html.escape(data['assets']['core'])}</small></th>"
            f"<td class={'pass' if passed == 14 else 'fail'}>{passed} / 14</td>"
            f"<td>{_pct(strategy['cagr'], 2)}</td><td>{_pct(core['cagr'], 2)}</td>"
            f"<td>{_pct(fixed['cagr'], 2)}</td><td>{_pct(unlevered['cagr'], 2)}</td>"
            f"<td>{_num(strategy['sharpe'])} / {_num(core['sharpe'])}</td>"
            f"<td>{_pct(strategy['max_drawdown'], 1)} / {_pct(core['max_drawdown'], 1)}</td>"
            f"<td>{_pct(rolling.get('cagr_win_fraction', float('nan')), 1)}</td></tr>"
        )
    css = _late_research_css()
    decision = (
        "所有設計、外部與數據入口全過；仍只能建立隔離 Paper，不能直接參考交易。"
        if paper_ok
        else "數據與時序 13/13 全過，但經濟門檻只有 45/154、外部只有 7/42、統計 0/27。依凍結協議拒絕建立 v20 Paper，也不顯示可交易配置。"
    )
    external = audit["datasets"]
    content = f"""<!doctype html><html lang="zh-Hant-HK"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>v20 分散器相對強弱驗證</title><style>{css}</style></head><body><main>
    <header><div class="eyebrow">FROZEN DIVERSIFIER ROTATION TEST</div><h1>{"歷史入口全過，仍須前瞻觀察。" if paper_ok else "輪替沒有改善固定股債金，候選淘汰。"}</h1><p class="lead">v20 固定 50% 實際每日 2 倍股票 ETF，另外 50% 每月依 12–1 月相對強度，從 IEF、GLD、SHY 選兩檔各 25%。規則在新區域 ETF 日線下載前凍結，沒有測試替代窗或權重。</p></header>
    <section class="verdict"><article class="card"><span>已見設計門檻</span><strong class={"pass" if audit["design_economic_passed_gate_count"] == audit["design_economic_required_gate_count"] else "fail"}>{audit["design_economic_passed_gate_count"]} / {audit["design_economic_required_gate_count"]}</strong><small>8 市場 × 14 道</small></article><article class="card"><span>新外部門檻</span><strong class={"pass" if audit["external_economic_passed_gate_count"] == audit["external_economic_required_gate_count"] else "fail"}>{audit["external_economic_passed_gate_count"]} / {audit["external_economic_required_gate_count"]}</strong><small>日本、中國大型股、巴西</small></article><article class="card"><span>數據與時序</span><strong class={"pass" if audit["data_passed_gate_count"] == audit["data_required_gate_count"] else "fail"}>{audit["data_passed_gate_count"]} / {audit["data_required_gate_count"]}</strong><small>凍結、產品、日線、成交與權重</small></article><article class="card"><span>統計門檻</span><strong class={"pass" if audit["statistical_passed_gate_count"] == audit["statistical_required_gate_count"] else "fail"}>{audit["statistical_passed_gate_count"]} / {audit["statistical_required_gate_count"]}</strong><small>外部三基準 × NW／PSR／DSR</small></article></section>
    <div class="warning {"success" if paper_ok else ""}"><b>Paper 決定：{"只准建立隔離 Paper。" if paper_ok else "不建立。"}</b><br>{decision}</div>
    <section class="panel"><h2>初學投資者先看：輪替聽起來聰明，但沒有穩定增加價值</h2><p>這次不是只問「有沒有賺錢」，而是同時要求勝過核心 ETF、勝過固定 50/25/25、勝過同規則但不槓桿的組合，還要在最大跌幅、成本、前後半期與滾動五年都站得住腳。結果 11 個市場的 CAGR 全部低於固定 v18 配置；多數市場的最大跌幅也比核心 ETF 深。</p></section>
    <section class="panel"><h2>11 市場完整結果</h2><div class="table-wrap"><table><thead><tr><th>市場</th><th>門檻</th><th>輪替 CAGR</th><th>核心 ETF</th><th>固定 v18</th><th>同政策不槓桿</th><th>Sharpe：輪替 / 核心</th><th>最大跌幅：輪替 / 核心</th><th>五年勝率</th></tr></thead><tbody>{"".join(rows)}</tbody></table></div></section>
    <section class="panel"><h2>三個新外部市場說了什麼</h2><p>日本：輪替 CAGR {_pct(external["japan"]["strategy_metrics"]["cagr"], 2)}，低於 EWJ 的 {_pct(external["japan"]["benchmark_metrics"]["core"]["cagr"], 2)}，最大跌幅也由 {_pct(external["japan"]["benchmark_metrics"]["core"]["max_drawdown"], 1)} 加深到 {_pct(external["japan"]["strategy_metrics"]["max_drawdown"], 1)}。中國大型股 14 道全失敗，輪替 CAGR {_pct(external["china_large_cap"]["strategy_metrics"]["cagr"], 2)}，低於 FXI 的 {_pct(external["china_large_cap"]["benchmark_metrics"]["core"]["cagr"], 2)}。巴西雖減輕部分最大跌幅，但 CAGR 仍低於 EWZ、固定 v18 與同政策不槓桿版本，不能靠單一優點覆蓋其餘失敗。</p></section>
    <section class="panel"><h2>20 年邊界</h2><p>S&P 500、Nasdaq-100 與 Dow 30 的實際 ETF 設計期是 2006-07-31 至 2026-07-31，共 20 年；中小型為 18 年。新區域 2 倍 ETF 成立較晚，外部正式期固定為 2016-09-01 至 2026-07-31，不能誠實宣稱 20 年，也沒有用合成槓桿回報補齊。</p></section>
    <section class="panel"><h2>v19 為何先停止</h2><p>在任何 v19 日線下載與表現計算前，產品稽核發現 VGK 與 UPV 在 2015-10-01 至 2016-08-31 的基準範圍不同。v19 因數據識別失敗直接作廢；v20 只修正外部數據契約，策略規則與成功門檻完全不變。</p></section>
    <section class="panel"><h2>154 道凍結經濟門檻</h2><div class="table-wrap"><table><thead><tr><th>檢查鍵</th><th>結果</th></tr></thead><tbody>{_research_gate_rows(audit["economic_gates"])}</tbody></table></div></section>
    <section class="panel"><h2>數據與執行門檻</h2><div class="table-wrap"><table><thead><tr><th>檢查鍵</th><th>結果</th></tr></thead><tbody>{_research_gate_rows(audit["data_gates"])}</tbody></table></div></section>
    <section class="panel"><h2>研究依據與不可回改收據</h2><p><a href="https://www.aqr.com/Insights/Research/Journal-Article/Time-Series-Momentum">Time Series Momentum</a>、<a href="https://papers.ssrn.com/sol3/papers.cfm?abstract_id=962461">A Quantitative Approach to Tactical Asset Allocation</a> 與 <a href="https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2607730">Two Centuries of Multi-Asset Momentum</a>只提供假說來源，不是成功證據。協議 SHA-256：<code>{html.escape(audit["protocol"]["sha256"])}</code><br>外部面板 SHA-256：<code>{html.escape(audit["integrity"]["sources"]["external"]["panel_sha256"])}</code></p></section>
    <p class="footer">歷史回測、研究與教育用途，不構成投資建議。每日 2 倍 ETF、IEF、GLD 與 SHY 都有風險；失敗候選不得轉成真實交易指示。</p>
    </main></body></html>"""
    destination.write_text(_with_report_references(content), encoding="utf-8")
    return destination


def build_hybrid_leverage_core_report(destination: str | Path, audit: dict[str, Any]) -> Path:
    """Write the beginner-readable frozen v21 validation report."""
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    paper_ok = bool(audit["paper_eligible"])
    rows: list[str] = []
    for data in audit["datasets"].values():
        passed = int(sum(data["economic_gates"].values()))
        strategy = data["strategy_metrics"]
        core = data["benchmark_metrics"]["core"]
        fixed_on = data["benchmark_metrics"]["fixed_risk_on"]
        fixed_off = data["benchmark_metrics"]["fixed_risk_off"]
        rolling = data["rolling_five_year_vs_core"]["summary"]
        role = (
            "新外部日線"
            if data["evidence_role"] == "new_external_daily_path_semi_independent"
            else "已見設計"
        )
        rows.append(
            f"<tr><th>{html.escape(data['label'])}<small>{role}｜"
            f"{html.escape(data['assets']['leveraged'])} / "
            f"{html.escape(data['assets']['core'])}</small></th>"
            f"<td class={'pass' if passed == 16 else 'fail'}>{passed} / 16</td>"
            f"<td>{_pct(strategy['cagr'], 2)}</td><td>{_pct(core['cagr'], 2)}</td>"
            f"<td>{_pct(fixed_on['cagr'], 2)}</td><td>{_pct(fixed_off['cagr'], 2)}</td>"
            f"<td>{_num(strategy['sharpe'])} / {_num(core['sharpe'])}</td>"
            f"<td>{_pct(strategy['max_drawdown'], 1)} / "
            f"{_pct(core['max_drawdown'], 1)}</td>"
            f"<td>{_pct(rolling.get('cagr_win_fraction', float('nan')), 1)}</td></tr>"
        )
    css = _late_research_css()
    datasets = audit["datasets"]
    mid = datasets["midcap400_3x"]
    small = datasets["russell2000_3x"]
    decision = (
        "128 道經濟門檻與十道數據門檻全過；仍只能從零開始隔離 Paper。"
        if paper_ok
        else (
            f"數據與治理 {audit['data_passed_gate_count']}/"
            f"{audit['data_required_gate_count']} 全過，但經濟門檻只有 "
            f"{audit['economic_passed_gate_count']}/"
            f"{audit['economic_required_gate_count']}，外部只有 "
            f"{audit['external_economic_passed_gate_count']}/"
            f"{audit['external_economic_required_gate_count']}，統計 "
            f"{audit['statistical_passed_gate_count']}/"
            f"{audit['statistical_required_gate_count']}。依凍結協議拒絕建立 Paper。"
        )
    )
    content = f"""<!doctype html><html lang="zh-Hant-HK"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>v21 常駐核心＋受控槓桿驗證</title><style>{css}</style></head><body><main>
    <header><div class="eyebrow">FROZEN HYBRID LEVERAGE CORE TEST</div><h1>{"歷史入口全過，仍須前瞻觀察。" if paper_ok else "中小型股外部驗證否決候選，不進 Paper。"}</h1><p class="lead">v21 永久保留 60% 普通核心 ETF；核心連續兩個完整月站上 200 日移動平均線時，把股票名目持倉比率提高到約 120%，否則降到約 60%。規則、日期、產品與 128 道門檻都在 UMDD／URTY 日線下載前凍結。</p></header>
    <section class="verdict"><article class="card"><span>20 年／已見設計</span><strong class={"pass" if audit["design_economic_passed_gate_count"] == audit["design_economic_required_gate_count"] else "fail"}>{audit["design_economic_passed_gate_count"]} / {audit["design_economic_required_gate_count"]}</strong><small>6 組 × 16 道</small></article><article class="card"><span>新外部門檻</span><strong class={"pass" if audit["external_economic_passed_gate_count"] == audit["external_economic_required_gate_count"] else "fail"}>{audit["external_economic_passed_gate_count"]} / {audit["external_economic_required_gate_count"]}</strong><small>中型股、小型股各 16 道</small></article><article class="card"><span>數據與治理</span><strong class={"pass" if audit["data_passed_gate_count"] == audit["data_required_gate_count"] else "fail"}>{audit["data_passed_gate_count"]} / {audit["data_required_gate_count"]}</strong><small>先凍結、產品、日線、成交、權重</small></article><article class="card"><span>Paper 決定</span><strong class={"pass" if paper_ok else "fail"}>{"可建立" if paper_ok else "不建立"}</strong><small>失敗候選不提供可照抄訊號</small></article></section>
    <div class="warning {"success" if paper_ok else ""}"><b>結論：{"只准隔離 Paper。" if paper_ok else "不要照這個候選交易。"}</b><br>{decision}</div>
    <section class="panel"><h2>初學投資者先看：這個開關在做什麼</h2><p>把普通 ETF 的完整股票風險想成 100 格。v21 在市場趨勢確認向上時約開到 120 格；確認轉弱時降到 60 格，但不完全離開市場。這原本想同時避免 v14「退太多、錯過反彈」與 v15「留太多、最大跌幅過深」；真正的測試不是它有沒有賺錢，而是能否同時勝過普通 ETF、永久 120 格與永久 60 格三種公平對照。</p></section>
    <section class="panel"><h2>八組完整結果</h2><div class="table-wrap"><table><thead><tr><th>市場</th><th>門檻</th><th>v21 CAGR</th><th>普通 ETF</th><th>固定 120% 持倉比率</th><th>固定 60% 持倉比率</th><th>Sharpe：v21 / 普通</th><th>最大跌幅：v21 / 普通</th><th>五年勝率</th></tr></thead><tbody>{"".join(rows)}</tbody></table></div></section>
    <section class="panel"><h2>外部路徑為何否決</h2><p>S&P MidCap 400 的 v21 CAGR 為 {_pct(mid["strategy_metrics"]["cagr"], 2)}，低於 IJH 的 {_pct(mid["benchmark_metrics"]["core"]["cagr"], 2)}；最大跌幅 {_pct(mid["strategy_metrics"]["max_drawdown"], 1)}，也深於 IJH 的 {_pct(mid["benchmark_metrics"]["core"]["max_drawdown"], 1)}。Russell 2000 的 v21 CAGR {_pct(small["strategy_metrics"]["cagr"], 2)}，低於 IWM 的 {_pct(small["benchmark_metrics"]["core"]["cagr"], 2)}；最大跌幅 {_pct(small["strategy_metrics"]["max_drawdown"], 1)}，深於 IWM 的 {_pct(small["benchmark_metrics"]["core"]["max_drawdown"], 1)}。兩組各只通過 2/16，不能靠 Nasdaq 成功或 pooled 平均抵銷。</p></section>
    <section class="panel"><h2>20 年證據邊界</h2><p>SPY／SSO、QQQ／QLD、DIA／DDM 的實際 2 倍產品設計診斷固定為 2006-07-31 至 2026-07-31，是真實產品 20 年路徑；3 倍產品成立較晚，正式期只能固定為 2011-07-29 至 2026-07-31，共 15 年。沒有用理論三倍回報補出不存在的 20 年產品史。大型股六組都已在先前研究看過，只能作設計診斷；新中小型股日線在 v21 凍結後才下載，但產品頁摘要表現先前已見，因此屬半獨立日線驗證，不是完全盲測。</p></section>
    <section class="panel"><h2>為何每日 3 倍不是長期三倍</h2><p><a href="https://www.proshares.com/globalassets/proshares/prospectuses/umdd_summary_prospectus.pdf">UMDD</a> 與 <a href="https://www.proshares.com/globalassets/proshares/prospectuses/urty_summary_prospectus.pdf">URTY</a> 的官方文件都把目標限定為單日。每日重設、波幅、複利、費用與追蹤誤差會讓多年結果顯著偏離指數長期回報的三倍。本研究直接使用實際 ETF 經調整 OHLCV，而不是合成三倍價格。</p></section>
    <section class="panel"><h2>128 道凍結經濟門檻</h2><div class="table-wrap"><table><thead><tr><th>檢查鍵</th><th>結果</th></tr></thead><tbody>{_research_gate_rows(audit["economic_gates"])}</tbody></table></div></section>
    <section class="panel"><h2>數據、月末、成交與權重門檻</h2><div class="table-wrap"><table><thead><tr><th>檢查鍵</th><th>結果</th></tr></thead><tbody>{_research_gate_rows(audit["data_gates"])}</tbody></table></div></section>
    <section class="panel"><h2>不可回改收據</h2><p>協議 SHA-256：<code>{html.escape(audit["protocol"]["sha256"])}</code><br>產品稽核 SHA-256：<code>{html.escape(audit["product_mapping"]["sha256"])}</code><br>新外部面板 SHA-256：<code>{html.escape(audit["snapshot"]["panel_sha256"])}</code></p></section>
    <p class="footer">歷史回測、研究與教育用途，不構成投資建議。普通 ETF、SHY 與每日槓桿 ETF 都可能虧損；失敗候選不得轉成真實交易指示。</p>
    </main></body></html>"""
    destination.write_text(_with_report_references(content), encoding="utf-8")
    return destination


def build_sector_capital_efficiency_report(destination: str | Path, audit: dict[str, Any]) -> Path:
    """Write the beginner-readable frozen v22 U.S.-sector validation report."""
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    paper_ok = bool(audit["paper_eligible"])
    rows: list[str] = []
    for data in audit["datasets"].values():
        strategy = data["strategy_metrics"]
        core = data["benchmark_metrics"]["core"]
        passed = int(sum(data["economic_gates"].values()))
        rolling = data["rolling_five_year_vs_core"]["summary"]
        rows.append(
            f"<tr><th>{html.escape(data['label'])}<small>"
            f"{html.escape(data['assets']['leveraged'])} / "
            f"{html.escape(data['assets']['core'])}</small></th>"
            f"<td class={'pass' if passed >= 5 else 'fail'}>{passed} / 7</td>"
            f"<td>{_pct(strategy['cagr'], 2)}</td><td>{_pct(core['cagr'], 2)}</td>"
            f"<td>{_num(strategy['sharpe'])} / {_num(core['sharpe'])}</td>"
            f"<td>{_pct(strategy['max_drawdown'], 1)} / "
            f"{_pct(core['max_drawdown'], 1)}</td>"
            f"<td>{_pct(rolling.get('cagr_win_fraction', float('nan')), 1)}</td></tr>"
        )
    pooled = audit["pooled"]
    strategy = pooled["strategy_metrics"]
    core = pooled["core_metrics"]
    pooled_passed = int(sum(pooled["economic_gates"].values()))
    decision = (
        "所有凍結的多數一致性、合併路徑、數據與治理門檻均通過；仍只准從現金開始候選 Paper。"
        if paper_ok
        else (
            f"產業個別門檻 {audit['individual_passed_gate_count']}/"
            f"{audit['individual_required_gate_count']}；整體經濟門檻 "
            f"{audit['economic_passed_gate_count']}/"
            f"{audit['economic_required_gate_count']}；數據 "
            f"{audit['data_passed_gate_count']}/{audit['data_required_gate_count']}。"
            "任一凍結入口失敗就不建立 Paper。"
        )
    )
    css = _late_research_css()
    content = f"""<!doctype html><html lang="zh-Hant-HK"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>v22 美國產業股債金驗證</title><style>{css}</style></head><body><main>
    <header><div class="eyebrow">FROZEN U.S. SECTOR CAPITAL-EFFICIENCY TEST</div><h1>{"歷史入口通過，仍只准候選 Paper。" if paper_ok else "九產業壓力測試未達入口，不進 Paper。"}</h1><p class="lead">v22 固定每月持有 50% 實際每日 2 倍產業 ETF、25% IEF、25% GLD。九組普通／2 倍產業 ETF 在凍結區間追蹤相同 Dow Jones 產業指數；規則、日期、產品與成功門檻都在首次日線下載前固定。</p></header>
    <section class="verdict"><article class="card"><span>個別產業門檻</span><strong class={"pass" if audit["individual_passed_gate_count"] >= 45 else "fail"}>{audit["individual_passed_gate_count"]} / {audit["individual_required_gate_count"]}</strong><small>需同時滿足各門檻多數與無嚴重失敗</small></article><article class="card"><span>九產業等權</span><strong class={"pass" if pooled_passed == 9 else "fail"}>{pooled_passed} / 9</strong><small>不能由單一科技或防禦產業撐起</small></article><article class="card"><span>數據與治理</span><strong class={"pass" if audit["data_passed_gate_count"] == audit["data_required_gate_count"] else "fail"}>{audit["data_passed_gate_count"]} / {audit["data_required_gate_count"]}</strong><small>先凍結、同指數、單次下載、極端值核對</small></article><article class="card"><span>Paper 決定</span><strong class={"pass" if paper_ok else "fail"}>{"可建立" if paper_ok else "不建立"}</strong><small>trade_ready 永遠仍為 false</small></article></section>
    <div class="warning {"success" if paper_ok else ""}"><b>結論：{"只准候選 Paper。" if paper_ok else "不要把這套比例當成落盤訊號。"}</b><br>{decision}</div>
    <section class="panel"><h2>初學投資者先看：為什麼是 50／25／25</h2><p>2 倍 ETF 的 50% 物理權重約提供 100 格股票持倉比率，再加 25 格中期美債與 25 格黃金。這不是預測漲跌，而是用產品內槓桿騰出資金放入兩種分散器；代價是每日重設、費用與極端市況會放大誤差。每月只做一次回到目標比例的重新平衡。</p></section>
    <section class="panel"><h2>九個尚未看過的產業路徑</h2><div class="table-wrap"><table><thead><tr><th>產業</th><th>門檻</th><th>v22 CAGR</th><th>普通 ETF</th><th>Sharpe：v22 / ETF</th><th>最大跌幅：v22 / ETF</th><th>五年勝率</th></tr></thead><tbody>{"".join(rows)}</tbody></table></div></section>
    <section class="panel"><h2>九產業等權結果</h2><p>v22 CAGR {_pct(strategy["cagr"], 2)}，普通產業 ETF 等權 {_pct(core["cagr"], 2)}；Sharpe {_num(strategy["sharpe"])} 對 {_num(core["sharpe"])}；最大跌幅 {_pct(strategy["max_drawdown"], 1)} 對 {_pct(core["max_drawdown"], 1)}。合併路徑通過 {pooled_passed}/9 道，不能用個別產業的亮點抵銷整體失敗。</p></section>
    <section class="panel"><h2>數據異常如何處理</h2><p>唯一超過 35% 的旗標是 DIG 在 2008-10-13 的市場收市回報 +36.29%。ProShares 官方 NAV 同日為 +37.61%，普通 IYE 同日為 +24.38%，證明是金融危機反彈，不是漏調整拆股。原始值完整保留，原機械失敗 ZIP 也未刪除，沒有重抓或放寬門檻。</p></section>
    <section class="panel"><h2>證據邊界</h2><p>這個規則先前已由六個美國廣泛市場設計，且是在看過 v18 海外失敗後才把研究範圍縮回美國；因此不能稱全新盲測，也不能宣稱全球有效。九產業正式期是 2007-07-31 至 2019-06-21，統一在已知第一個產品定義分歧前截止；2022 型股債同跌風險仍由既有 2006–2026 廣泛市場紀錄揭露。</p></section>
    <section class="panel"><h2>凍結入口門檻</h2><div class="table-wrap"><table><thead><tr><th>檢查鍵</th><th>結果</th></tr></thead><tbody>{_research_gate_rows(audit["economic_gates"])}</tbody></table></div></section>
    <section class="panel"><h2>數據與執行門檻</h2><div class="table-wrap"><table><thead><tr><th>檢查鍵</th><th>結果</th></tr></thead><tbody>{_research_gate_rows(audit["data_gates"])}</tbody></table></div></section>
    <section class="panel"><h2>不可回改收據</h2><p>協議 SHA-256：<code>{html.escape(audit["protocol"]["sha256"])}</code><br>產品映射 SHA-256：<code>{html.escape(audit["protocol"]["product_mapping_sha256"])}</code><br>面板 SHA-256：<code>{html.escape(audit["snapshot"]["panel_sha256"])}</code></p></section>
    <p class="footer">歷史回測、研究與教育用途，不構成投資建議。普通 ETF、每日 2 倍 ETF、IEF 與 GLD 都可能虧損；沒有通過前瞻 Paper 與 readiness，不提供可照抄交易配置。</p>
    </main></body></html>"""
    destination.write_text(_with_report_references(content), encoding="utf-8")
    return destination


def build_managed_futures_capital_efficiency_report(
    destination: str | Path, audit: dict[str, Any]
) -> Path:
    """Write the beginner-readable frozen v23 managed-futures report."""
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    paper_ok = bool(audit["paper_eligible"])
    long_data = audit["long_horizon"]
    kmlm = audit["kmlm_actual_bridge"]
    fmf = audit["fmf_cross_manager"]
    long_strategy = long_data["strategy_metrics"]
    long_spy = long_data["benchmark_metrics"]["SPY"]
    kmlm_strategy = kmlm["strategy_metrics"]
    kmlm_spy = kmlm["benchmark_metrics"]["SPY"]
    fmf_strategy = fmf["strategy_metrics"]
    fmf_spy = fmf["benchmark_metrics"]["SPY"]
    long_halves = long_data["fixed_halves_vs_SPY"]
    kmlm_halves = kmlm["fixed_halves_vs_SPY"]
    long_rolling = long_data["rolling_five_year_vs_SPY"]["summary"]
    kmlm_rolling = kmlm["rolling_five_year_vs_SPY"]["summary"]
    fmf_rolling = fmf["rolling_five_year_vs_SPY"]["summary"]
    tracking = kmlm["tracking"]
    long_stats = audit["statistical_confirmation"]["long_vs_SPY"]
    psr = long_stats["active_probabilistic_sharpe"]
    dsr = long_stats["active_global_deflated_sharpe"]
    css = _late_research_css()

    period_rows = "".join(
        [
            f"<tr><th>20 年官方指數代理<small>2006-07–2026-06</small></th>"
            f"<td>{_pct(long_strategy['cagr'], 2)}</td><td>{_pct(long_spy['cagr'], 2)}</td>"
            f"<td>{_num(long_strategy['sharpe'])} / {_num(long_spy['sharpe'])}</td>"
            f"<td>{_pct(long_strategy['max_drawdown'], 1)} / {_pct(long_spy['max_drawdown'], 1)}</td>"
            f"<td>{_pct(long_rolling['cagr_win_fraction'], 1)}</td></tr>",
            f"<tr><th>KMLM 實際產品橋接<small>2021-01–2026-07</small></th>"
            f"<td>{_pct(kmlm_strategy['cagr'], 2)}</td><td>{_pct(kmlm_spy['cagr'], 2)}</td>"
            f"<td>{_num(kmlm_strategy['sharpe'])} / {_num(kmlm_spy['sharpe'])}</td>"
            f"<td>{_pct(kmlm_strategy['max_drawdown'], 1)} / {_pct(kmlm_spy['max_drawdown'], 1)}</td>"
            f"<td>{_pct(kmlm_rolling['cagr_win_fraction'], 1)}</td></tr>",
            f"<tr><th>FMF 跨管理人<small>2013-09–2026-07</small></th>"
            f"<td>{_pct(fmf_strategy['cagr'], 2)}</td><td>{_pct(fmf_spy['cagr'], 2)}</td>"
            f"<td>{_num(fmf_strategy['sharpe'])} / {_num(fmf_spy['sharpe'])}</td>"
            f"<td>{_pct(fmf_strategy['max_drawdown'], 1)} / {_pct(fmf_spy['max_drawdown'], 1)}</td>"
            f"<td>{_pct(fmf_rolling['cagr_win_fraction'], 1)}</td></tr>",
        ]
    )
    decision = (
        "三層凍結入口都通過；仍只准建立隔離 Paper，trade_ready 仍為 false。"
        if paper_ok
        else (
            "20 年段只有很小的完整期回報優勢，後十年、成本與滾動穩定性失敗；"
            "另一個管理人 FMF 也沒有保留跑贏 SPY 的方向，因此不建立 Paper。"
        )
    )
    content = f"""<!doctype html><html lang="zh-Hant-HK"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>v23 美國股＋管理期貨驗證</title><style>{css}</style></head><body><main>
    <header><div class="eyebrow">FROZEN 20-YEAR CAPITAL-EFFICIENCY TEST</div><h1>{"歷史入口通過，仍只准候選 Paper。" if paper_ok else "風險路徑改善，但沒有穩健跑贏 SPY。"}</h1><p class="lead">v23 唯一候選是每月 50% SSO／50% KMLM：用半數實體資金的每日 2 倍 S&P 500 約保留 100% 股票持倉比率，另一半放進商品、貨幣與全球公債的多空趨勢策略。沒有搜尋其他比例或擇時參數。</p></header>
    <section class="verdict"><article class="card"><span>20 年長期入口</span><strong class={"pass" if audit["long_passed_gate_count"] == audit["long_required_gate_count"] else "fail"}>{audit["long_passed_gate_count"]} / {audit["long_required_gate_count"]}</strong><small>實際 SSO＋官方 KFA 指數代理</small></article><article class="card"><span>KMLM 產品橋接</span><strong class={"pass" if audit["kmlm_bridge_passed_gate_count"] == audit["kmlm_bridge_required_gate_count"] else "fail"}>{audit["kmlm_bridge_passed_gate_count"]} / {audit["kmlm_bridge_required_gate_count"]}</strong><small>實際 ETF、追蹤與路徑</small></article><article class="card"><span>FMF 跨管理人</span><strong class={"pass" if audit["fmf_passed_gate_count"] >= audit["fmf_required_pass_count"] else "fail"}>{audit["fmf_passed_gate_count"]} / {audit["fmf_required_gate_count"]}</strong><small>至少需 {audit["fmf_required_pass_count"]} / {audit["fmf_required_gate_count"]}</small></article><article class="card"><span>Paper 決定</span><strong class={"pass" if paper_ok else "fail"}>{"可建立" if paper_ok else "不建立"}</strong><small>trade_ready 仍為 false</small></article></section>
    <div class="warning {"success" if paper_ok else ""}"><b>結論：{"只准候選 Paper。" if paper_ok else "不要照 50／50 落盤。"}</b><br>{decision}</div>
    <section class="panel"><h2>初學投資者先看：有改善，不等於跑贏</h2><p>20 年候選 CAGR {_pct(long_strategy["cagr"], 2)}，SPY {_pct(long_spy["cagr"], 2)}，只多 {_pct(long_strategy["cagr"] - long_spy["cagr"], 2)}／年，未達事前要求的 0.25%。它把最大跌幅由 {_pct(long_spy["max_drawdown"], 1)} 改善到 {_pct(long_strategy["max_drawdown"], 1)}，Sharpe 也略升；但 50 bps 成本後反而落後 SPY {_pct(abs(long_data["cost_50bps"]["cagr_difference"]), 2)}／年。這是一個較平滑的歷史路徑，不是已證明的超額回報。</p></section>
    <section class="panel"><h2>三段固定驗證</h2><div class="table-wrap"><table><thead><tr><th>證據段</th><th>候選 CAGR</th><th>SPY CAGR</th><th>Sharpe：候選 / SPY</th><th>最大跌幅：候選 / SPY</th><th>五年勝率</th></tr></thead><tbody>{period_rows}</tbody></table></div></section>
    <section class="panel"><h2>時間穩定性在哪裡破裂</h2><p>20 年前十年相對 SPY CAGR 為 {_pct(long_halves["first"]["cagr_difference"], 2)}，後十年轉為 {_pct(long_halves["second"]["cagr_difference"], 2)}；181 個五年窗勝率 {_pct(long_rolling["cagr_win_fraction"], 1)}，低於凍結的 60%。KMLM 上市後完整期看似領先，但機械後半期落後 {_pct(abs(kmlm_halves["second"]["cagr_difference"]), 2)}／年，八個可用五年窗沒有一個以 10 bps 門檻勝出。FMF 前後半都落後，96 個五年窗同樣 0% 通過。</p></section>
    <section class="panel"><h2>產品映射不是免費的</h2><p>KMLM 實際月回報與 KFA 指數相關 {_num(tracking["monthly_return_correlation"], 3)}，方向一致；但 2021-01 至 2026-06 的指數 CAGR {_pct(tracking["index_cagr"], 2)}、ETF {_pct(tracking["fund_cagr"], 2)}，年率化幾何追蹤差 {_pct(tracking["annualized_geometric_tracking_gap"], 2)}，超過凍結的 2.00%。官方 FAQ 說一般拖累約為 0.90% 費用加約 0.15% 交易費，也另揭露 2022 年現金管理造成額外拖累；因此歷史指數代理不能直接當成投資人可得回報。</p></section>
    <section class="panel"><h2>統計確認</h2><p>20 年候選相對 SPY 的主動月回報 Newey-West t = {_num(long_stats["active_return_newey_west"]["t_stat"])}，PSR = {_pct(psr["probability"], 2)}；計入全專案 {audit["global_search_trials"]:,} 次搜尋後 DSR = {_pct(dsr["probability"], 4)}。這些只作診斷，不能抵銷經濟入口失敗。</p></section>
    <section class="panel"><h2>20 年凍結門檻</h2><div class="table-wrap"><table><thead><tr><th>檢查鍵</th><th>結果</th></tr></thead><tbody>{_research_gate_rows(long_data["economic_gates"])}</tbody></table></div></section>
    <section class="panel"><h2>KMLM 實際產品門檻</h2><div class="table-wrap"><table><thead><tr><th>檢查鍵</th><th>結果</th></tr></thead><tbody>{_research_gate_rows(kmlm["entry_gates"])}</tbody></table></div></section>
    <section class="panel"><h2>FMF 跨管理人門檻</h2><div class="table-wrap"><table><thead><tr><th>檢查鍵</th><th>結果</th></tr></thead><tbody>{_research_gate_rows(fmf["entry_gates"])}</tbody></table></div></section>
    <section class="panel"><h2>數據與證據邊界</h2><p>20 年段不是 20 年實際 KMLM：股票袖套是實際 SSO，管理期貨袖套是 KraneShares 官方月表中 2005 起同一 EV 方法的 KFA MLM Index，再扣固定年率化 1.05%。正式期恰為 240 個月；原始 24 頁官方簡報、抽取 CSV、KMLM／FMF 單次下載快照與雜湊均保留。凍結前已看過指數月表與產品摘要，所以整體不能稱完全盲測。</p></section>
    <section class="panel"><h2>不可回改收據</h2><p>協議 SHA-256：<code>{html.escape(audit["protocol_sha256"])}</code><br>產品映射 SHA-256：<code>{html.escape(audit["product_mapping_sha256"])}</code><br>KFA 月表正式期：2006-07 至 2026-06，共 {audit["kfa_index_integrity"]["formal_rows"]} 個月。</p></section>
    <p class="footer">歷史回測、研究與教育用途，不構成投資建議。SSO 是每日槓桿 ETF；KMLM／FMF 使用多空期貨。全部都可能快速虧損，且指數回報不可直接投資。未通過凍結入口、前瞻 Paper 與 readiness 前，不提供可照抄交易配置。</p>
    </main></body></html>"""
    destination.write_text(_with_report_references(content), encoding="utf-8")
    return destination


def build_quality_momentum_factor_report(destination: str | Path, audit: dict[str, Any]) -> Path:
    """Write the beginner-readable frozen v24 quality-momentum report."""
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    paper_ok = bool(audit["paper_eligible"])
    academic = audit["academic_formal_20y"]
    older = audit["academic_older_diagnostic"]
    ishares = audit["ishares_actual"]
    invesco = audit["invesco_cross_manager"]
    academic_strategy = academic["strategy_metrics"]
    academic_market = academic["benchmark_metrics"]["MARKET"]
    ishares_strategy = ishares["strategy_metrics"]
    ishares_spy = ishares["benchmark_metrics"]["SPY"]
    invesco_strategy = invesco["strategy_metrics"]
    invesco_spy = invesco["benchmark_metrics"]["SPY"]
    ishares_rolling = ishares["rolling_five_year_vs_market"]["summary"]
    invesco_rolling = invesco["rolling_five_year_vs_market"]["summary"]
    academic_stats = audit["statistical_confirmation"]["academic_formal_vs_market"]
    ishares_stats = audit["statistical_confirmation"]["ishares_actual_vs_SPY"]
    css = _late_research_css()
    content = f"""<!doctype html><html lang="zh-Hant-HK"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>v24 美國品質＋動量因子驗證</title><style>{css}</style></head><body><main>
    <header><div class="eyebrow">FROZEN QUALITY + MOMENTUM FACTOR TEST</div><h1>{"三層入口通過，仍只准候選 Paper。" if paper_ok else "教科書因子成立，但可買 ETF 沒有穩健複製。"}</h1><p class="lead">v24 只測每月固定 50% QUAL／50% MTUM。沒有挑比例、沒有 VIX、沒有槓桿，也沒有停利止蝕；先把品質與動量袖套本身，和產品包裝、出場規則分開歸因。</p></header>
    <section class="verdict"><article class="card"><span>20 年學術代理</span><strong class={"pass" if audit["long_passed_gate_count"] == audit["long_required_gate_count"] else "fail"}>{audit["long_passed_gate_count"]} / {audit["long_required_gate_count"]}</strong><small>French 品質與動量投組</small></article><article class="card"><span>iShares 實際 ETF</span><strong class={"pass" if audit["ishares_passed_gate_count"] == audit["ishares_required_gate_count"] else "fail"}>{audit["ishares_passed_gate_count"]} / {audit["ishares_required_gate_count"]}</strong><small>QUAL／MTUM 2013–2026</small></article><article class="card"><span>Invesco 跨管理人</span><strong class={"pass" if audit["invesco_passed_gate_count"] >= audit["invesco_required_pass_count"] else "fail"}>{audit["invesco_passed_gate_count"]} / {audit["invesco_required_gate_count"]}</strong><small>至少需 {audit["invesco_required_pass_count"]} / {audit["invesco_required_gate_count"]}</small></article><article class="card"><span>Paper 決定</span><strong class={"pass" if paper_ok else "fail"}>{"可建立" if paper_ok else "不建立"}</strong><small>trade_ready 仍為 false</small></article></section>
    <div class="warning {"success" if paper_ok else ""}"><b>結論：{"只准隔離 Paper。" if paper_ok else "不要照 QUAL／MTUM 50/50 落盤。"}</b><br>{"三層凍結入口已通過，但仍需 252 個新增交易日。" if paper_ok else "20 年學術排序表現漂亮；真正可買的兩組產品卻在風險、時間穩定性或完整期回報失敗。這是因子概念與可投資產品之間的映射失敗。"}</div>
    <section class="panel"><h2>初學投資者先看：論文中的因子，不等於 ETF 投資人拿得到</h2><p>French 20 年代理 CAGR {_pct(academic_strategy["cagr"], 2)}、市場 {_pct(academic_market["cagr"], 2)}，Sharpe {_num(academic_strategy["sharpe"])} 對 {_num(academic_market["sharpe"])}，最大跌幅 {_pct(academic_strategy["max_drawdown"], 1)} 對 {_pct(academic_market["max_drawdown"], 1)}，10/10 全過。更早 1964–2006 也以 {_pct(older["strategy_metrics"]["cagr"], 2)} 對 {_pct(older["benchmark_metrics"]["MARKET"]["cagr"], 2)} 保留方向。但這些是學術排序投組，不是 QUAL／MTUM 的歷史資產淨值。</p></section>
    <section class="panel"><h2>實際 iShares 為什麼只過 5/10</h2><p>2013–2026 候選 CAGR {_pct(ishares_strategy["cagr"], 2)}，高於 SPY {_pct(ishares_spy["cagr"], 2)}；50 bps 成本後仍領先。但 Sharpe {_num(ishares_strategy["sharpe"])} 略低於 SPY {_num(ishares_spy["sharpe"])}，最大跌幅 {_pct(ishares_strategy["max_drawdown"], 1)} 比 SPY {_pct(ishares_spy["max_drawdown"], 1)} 更深。前半領先 {_pct(ishares["fixed_halves_vs_market"]["first"]["cagr_difference"], 2)}，後半轉為落後 {_pct(abs(ishares["fixed_halves_vs_market"]["second"]["cagr_difference"]), 2)}；97 個五年窗勝率 {_pct(ishares_rolling["cagr_win_fraction"], 1)}、中位差 {_pct(ishares_rolling["median_cagr_difference"], 2)}。</p></section>
    <section class="panel"><h2>不同產品沒有保留方向</h2><p>2007–2026 的 50% SPHQ／50% PDP CAGR {_pct(invesco_strategy["cagr"], 2)}，低於 SPY {_pct(invesco_spy["cagr"], 2)}；Sharpe、最大跌幅、Calmar、成本、兩半期與五年滾動七道全部失敗。173 個五年窗勝率只有 {_pct(invesco_rolling["cagr_win_fraction"], 1)}，中位 CAGR 差 {_pct(invesco_rolling["median_cagr_difference"], 2)}。這不是完全相同指數的複製，但足以否決「只要買品質＋動量 ETF 就能跨產品穩健跑贏」的廣泛說法。</p></section>
    <section class="panel"><h2>統計確認</h2><p>學術 20 年相對市場 NW t = {_num(academic_stats["active_return_newey_west"]["t_stat"])}，PSR = {_pct(academic_stats["active_probabilistic_sharpe"]["probability"], 2)}；以全專案 {audit["global_search_trials"]:,} 次搜尋懲罰後 DSR = {_pct(academic_stats["active_global_deflated_sharpe"]["probability"], 3)}。iShares 實際段 NW t = {_num(ishares_stats["active_return_newey_west"]["t_stat"])}、DSR = {_pct(ishares_stats["active_global_deflated_sharpe"]["probability"], 3)}。完整期 CAGR 可略高，仍沒有足夠統計確認。</p></section>
    <section class="panel"><h2>20 年學術門檻</h2><div class="table-wrap"><table><thead><tr><th>檢查鍵</th><th>結果</th></tr></thead><tbody>{_research_gate_rows(academic["economic_gates"])}</tbody></table></div></section>
    <section class="panel"><h2>iShares 實際產品門檻</h2><div class="table-wrap"><table><thead><tr><th>檢查鍵</th><th>結果</th></tr></thead><tbody>{_research_gate_rows(ishares["entry_gates"])}</tbody></table></div></section>
    <section class="panel"><h2>Invesco 跨管理人門檻</h2><div class="table-wrap"><table><thead><tr><th>檢查鍵</th><th>結果</th></tr></thead><tbody>{_research_gate_rows(invesco["entry_gates"])}</tbody></table></div></section>
    <section class="panel"><h2>數據與證據邊界</h2><p>正式 20 年恰為 {audit["academic_integrity"]["formal_months"]} 個月，使用 French `BIG HiOP`、`BIG HiPRIOR` 與 `Mkt-RF + RF`，並扣固定年率化 0.15% 代理費用。MTUM 實際基準為拼接指數且後續方法有變；SPHQ／PDP 又是不同供應商與不同定義。凍結前看過產品摘要，因此不能稱完全盲測；所有聯合路徑都在協議凍結後才計算。</p></section>
    <section class="panel"><h2>不可回改收據</h2><p>協議 SHA-256：<code>{html.escape(audit["protocol"]["sha256"])}</code><br>產品映射 SHA-256：<code>{html.escape(audit["protocol"]["product_mapping_sha256"])}</code><br>Paper 入口：{audit["paper_entry_passed_gate_count"]} / {audit["paper_entry_required_gate_count"]}。</p></section>
    <p class="footer">歷史回測、研究與教育用途，不構成投資建議。因子 ETF 可能長期落後 SPY；動量可能快速反轉，品質定義與指數方法也可能改變。未通過產品入口、前瞻 Paper 與 readiness 前，不提供可照抄交易配置。</p>
    </main></body></html>"""
    destination.write_text(_with_report_references(content), encoding="utf-8")
    return destination


def build_growth_gold_diversification_report(
    destination: str | Path, audit: dict[str, Any]
) -> Path:
    """Write the beginner-readable frozen v25 growth-gold report."""
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    paper_ok = bool(audit["paper_eligible"])
    pooled = audit["pooled"]
    strategy = pooled["strategy_metrics"]
    spy = pooled["spy_metrics"]
    growth = pooled["growth_metrics"]
    matched = pooled["matched_metrics"]
    rolling = pooled["rolling_five_year_vs_SPY"]["summary"]
    rolling_growth = pooled["rolling_five_year_vs_growth"]["summary"]
    stats_spy = pooled["comparison_vs_SPY"]
    stats_growth = pooled["comparison_vs_growth"]
    stats_matched = pooled["comparison_vs_matched"]
    diagnostics = pooled["post_entry_diagnostics_not_used_for_frozen_gate"]
    portfolio_underwater = diagnostics["portfolio_underwater"]
    relative_spy = diagnostics["relative_wealth_underwater"]["SPY"]
    relative_growth = diagnostics["relative_wealth_underwater"]["growth"]
    bootstrap = diagnostics["paired_moving_block_bootstrap"]["benchmarks"]
    bootstrap_spy = bootstrap["SPY"]["12"]
    bootstrap_growth = bootstrap["growth"]["12"]
    bootstrap_matched = bootstrap["matched"]["12"]
    worst_spy_window = diagnostics["rolling_five_year_entry_timing_risk"]["SPY"]["worst_window"]
    path_cards = "".join(
        "<article class='card'><span>"
        + html.escape(label.replace("_", " ").title())
        + "</span><strong class='"
        + ("pass" if row["passed_gate_count"] >= row["required_pass_count"] else "fail")
        + "'>"
        + f"{row['passed_gate_count']} / {row['required_gate_count']}"
        + "</strong><small>"
        + html.escape(
            f"80% {row['implementation']['growth']} / 20% {row['implementation']['gold']}"
        )
        + "</small></article>"
        for label, row in audit["paths"].items()
    )
    path_sections = "".join(
        f"""<section class="panel"><h2>{html.escape(label.replace("_", " ").title())} 實際產品路徑</h2><p>候選 CAGR {_pct(row["strategy_metrics"]["cagr"], 2)}、SPY {_pct(row["benchmark_metrics"]["SPY"]["cagr"], 2)}、100% {html.escape(row["implementation"]["growth"])} {_pct(row["benchmark_metrics"]["growth"]["cagr"], 2)}、相同成長持倉比率加 SHY {_pct(row["benchmark_metrics"]["matched_80_growth_20_SHY"]["cagr"], 2)}。候選 Sharpe {_num(row["strategy_metrics"]["sharpe"])}、最大跌幅 {_pct(row["strategy_metrics"]["max_drawdown"], 1)}；相對 SPY 的 181 個五年窗勝率 {_pct(row["rolling_five_year_vs_SPY"]["summary"]["cagr_win_fraction"], 1)}，相對純成長只有 {_pct(row["rolling_five_year_vs_growth"]["summary"]["cagr_win_fraction"], 1)}。診斷沒有加入凍結門檻或改變通過數。</p><div class="table-wrap"><table><thead><tr><th>檢查鍵</th><th>結果</th></tr></thead><tbody>{_research_gate_rows(row["entry_gates"])}</tbody></table></div></section>"""
        for label, row in audit["paths"].items()
    )
    css = _late_research_css()
    content = f"""<!doctype html><html lang="zh-Hant-HK"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>v25 美國大型成長＋黃金分散驗證</title><style>{css}</style></head><body><main>
    <header><div class="eyebrow">FROZEN 20-YEAR GROWTH + GOLD PRODUCT TEST</div><h1>{"歷史產品入口通過，只啟動隔離 Paper。" if paper_ok else "實際產品入口未通過，不建立 Paper。"}</h1><p class="lead">v25 每月固定 80% 美國大型成長 ETF、20% 實物黃金 ETF。沒有預測、槓桿、止蝕或權重搜尋；Vanguard、iShares、State Street 三條實際產品路徑全部保留。</p></header>
    <section class="verdict">{path_cards}<article class="card"><span>三路徑彙總</span><strong class={"pass" if pooled["passed_gate_count"] == pooled["required_gate_count"] else "fail"}>{pooled["passed_gate_count"]} / {pooled["required_gate_count"]}</strong><small>Paper：{"可建立" if paper_ok else "不建立"}</small></article></section>
    <div class="warning {"success" if paper_ok else ""}"><b>現在怎麼做：{"只建立 Paper，不用實金照抄。" if paper_ok else "保持研究，不落盤。"}</b><br>{"20 年產品入口已通過；但相對 SPY 的統計確認仍弱，且最差五年窗仍會落後。Paper 必須再累積至少 252 個真正新增交易日與 6 次初始建倉後的月度重新平衡。" if paper_ok else "任何一條產品或彙總入口失敗，都不能顯示 80/20 為今天配置。"}</div>
    <section class="panel"><h2>初學投資者先看：這個策略靠什麼</h2><p>80 格大型成長股提供企業成長持倉比率，20 格黃金提供不同回報來源；每月只把漂移比例拉回 80/20。黃金不是現金、沒有利息，也可能和股票同跌。這套規則的 20 年彙總 CAGR {_pct(strategy["cagr"], 2)}，SPY {_pct(spy["cagr"], 2)}；最大跌幅 {_pct(strategy["max_drawdown"], 1)}，SPY {_pct(spy["max_drawdown"], 1)}。這表示歷史上勝過 SPY，不表示勝過所有 ETF。</p></section>
    <section class="panel"><h2>不能省略的比較：它沒有跑贏 100% 大型成長</h2><p>三路徑純成長 ETF 彙總 CAGR {_pct(growth["cagr"], 2)}，高於 v25 的 {_pct(strategy["cagr"], 2)}；v25 每年少 {_pct(abs(stats_growth["cagr_difference"]), 2)}。換到的是 Sharpe 從 {_num(growth["sharpe"])} 提高至 {_num(strategy["sharpe"])}，最大跌幅從 {_pct(growth["max_drawdown"], 1)} 改善至 {_pct(strategy["max_drawdown"], 1)}，約少跌 {_pct(stats_growth["drawdown_improvement"], 1)}。181 個五年窗只有 {_pct(rolling_growth["cagr_win_fraction"], 1)} 勝過純成長，最差落後 {_pct(abs(rolling_growth["worst_cagr_difference"]), 2)}。這是風險取捨，不是免費超額回報。</p></section>
    <section class="panel"><h2>公平比較：不是只靠少持股票</h2><p>相同 80% 成長股、20% SHY 控制 CAGR {_pct(matched["cagr"], 2)}、Sharpe {_num(matched["sharpe"])}、最大跌幅 {_pct(matched["max_drawdown"], 1)}。v25 分別為 {_pct(strategy["cagr"], 2)}、{_num(strategy["sharpe"])}、{_pct(strategy["max_drawdown"], 1)}；相對控制的 NW t = {_num(stats_matched["active_return_newey_west"]["t_stat"])}。這代表歷史差異主要來自黃金袖套，而不只是把 20% 放低波幅資產。</p></section>
    <section class="panel"><h2>時間穩定性與不能隱藏的壞消息</h2><p>前十年相對 SPY CAGR 差 {_pct(pooled["fixed_halves_vs_SPY"]["first"]["cagr_difference"], 2)}，後十年 {_pct(pooled["fixed_halves_vs_SPY"]["second"]["cagr_difference"], 2)}。181 個五年窗勝率 {_pct(rolling["cagr_win_fraction"], 1)}、中位差 {_pct(rolling["median_cagr_difference"], 2)}；最差進場期 {html.escape(worst_spy_window["start"])} 至 {html.escape(worst_spy_window["end"])}，每年落後 SPY {_pct(abs(worst_spy_window["cagr_difference"]), 2)}。最近一段成功不等於每個持有期都會贏。</p></section>
    <section class="panel"><h2>最大跌幅多久才回來，比跌多少同樣重要</h2><p>v25 自己最久曾連續 {portfolio_underwater["max_underwater_months"]} 個月低於先前資產淨值高點：高點 {portfolio_underwater["longest_episode"]["peak"]}、谷底 {portfolio_underwater["longest_episode"]["trough"]}、至 {portfolio_underwater["longest_episode"]["recovery"]} 才復原。相對 SPY 的累積財富曾 {relative_spy["max_underwater_months"]} 個月沒有回到先前相對高點；相對純成長 ETF 的最長相對水下期為 {relative_growth["max_underwater_months"]} 個月，期末仍未復原，離先前相對高點仍低 {_pct(abs(relative_growth["current_drawdown"]), 1)}。這不代表每個月都輸，而是長期持有者可能多年感覺選錯策略。</p></section>
    <section class="panel"><h2>區塊重抽樣：漂亮全期仍可能換個順序就落後</h2><p>將候選與基準的月回報配對，以 12 個月區塊循環重抽 10,000 次後，v25 CAGR 勝 SPY 的比例為 {_pct(bootstrap_spy["probability_cagr_above"], 1)}，回報與最大跌幅同時不差於 SPY 只有 {_pct(bootstrap_spy["probability_cagr_above_and_drawdown_not_worse"], 1)}；CAGR 差的第 5 百分位是 {_pct(bootstrap_spy["cagr_difference_percentiles"]["p05"], 2)}。對純成長的 CAGR 勝出比例只有 {_pct(bootstrap_growth["probability_cagr_above"], 1)}。對相同 80/20 SHY 控制，CAGR 勝出 {_pct(bootstrap_matched["probability_cagr_above"], 1)}，但回報與最大跌幅同時勝出只有 {_pct(bootstrap_matched["probability_cagr_above_and_drawdown_not_worse"], 1)}。6、12、24 個月區塊均有保存；這只是同一歷史樣本的順序敏感度，不處理選擇偏誤、制度改變，也不是未來勝率。</p></section>
    <section class="panel"><h2>統計確認仍不足</h2><p>相對 SPY 的 NW t = {_num(stats_spy["active_return_newey_west"]["t_stat"])}、PSR = {_pct(stats_spy["active_probabilistic_sharpe"]["probability"], 2)}；以全專案 {audit["global_search_trials"]:,} 次研究懲罰後 DSR = {_pct(stats_spy["active_global_deflated_sharpe"]["probability"], 3)}。這是為什麼歷史入口通過只准啟動 Paper，`trade_ready` 仍維持 false。</p></section>
    <section class="panel"><h2>第一筆成交前已凍結的前瞻升級合約</h2><p>首次 80/20 建倉不算完成重新平衡。至少 252 個全新交易日與 6 次後續月度重新平衡後，候選扣成本年率化回報仍須分別勝 SPY 與 80% VUG／20% SHY 至少 0.10 個百分點；固定前後兩半都要達標、最大跌幅不得更深，而且兩組每日主動回報的 Newey–West t 值都須至少 1.96。任一項失敗就維持 Paper-only，不能用一年期末剛好領先升級。</p></section>
    {path_sections}
    <section class="panel"><h2>三路徑彙總門檻</h2><p>以下仍是凍結前定義的 10 道入口；後加的純成長比較、最大跌幅復原與進場時點診斷只增加透明度，不參與通過數。</p><div class="table-wrap"><table><thead><tr><th>檢查鍵</th><th>結果</th></tr></thead><tbody>{_research_gate_rows(pooled["entry_gates"])}</tbody></table></div></section>
    <section class="panel"><h2>數據與不可回改收據</h2><p>三條路徑皆為 2006-08 至 2026-07、恰 240 個月；VUG 2026 年 6:1 拆股的經調整市場數據稽核已通過。協議 SHA-256：<code>{html.escape(audit["protocol"]["sha256"])}</code><br>產品映射 SHA-256：<code>{html.escape(audit["protocol"]["product_mapping_sha256"])}</code><br>數據門檻：{audit["data_passed_gate_count"]} / {audit["data_required_gate_count"]}。</p></section>
    <p class="footer">歷史回測、研究與教育用途，不構成投資建議。大型成長股可能長期估值收縮；黃金不生息、可能多年落後，分散也不保證盈利。Paper 尚未累積前瞻證據，現在不提供實金落盤指令。</p>
    </main></body></html>"""
    destination.write_text(_with_report_references(content), encoding="utf-8")
    return destination


def write_signals_json(
    destination: str | Path,
    *,
    panel: MarketPanel,
    results: list[BacktestResult],
    stock_screen: pd.DataFrame,
    snapshot_sha256: str,
) -> Path:
    payload = {
        "schema_version": 1,
        "data_through": panel.end.strftime("%Y-%m-%d"),
        "snapshot_sha256": snapshot_sha256,
        "execution_clock": "signal at close t; intended rebalance at open t+1",
        "allocations": {
            result.name: {
                str(ticker): round(float(weight), 8)
                for ticker, weight in result.current_target.items()
                if weight > 0
            }
            for result in results
        },
        "stock_watchlist": [
            {
                "rank": int(row["rank"]),
                "symbol": str(ticker),
                "name": str(row["name"]),
                "sector": str(row["sector"]),
                "score": round(float(row["score"]), 6),
                "momentum_12_1": round(float(row["mom_12_1"]), 6),
                "trend_200": round(float(row["trend_200"]), 6),
                "universe_as_of": str(row["universe_as_of"]),
            }
            for ticker, row in stock_screen.iterrows()
        ],
        "disclaimer": "research only; not investment advice",
    }
    path = Path(destination)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path
