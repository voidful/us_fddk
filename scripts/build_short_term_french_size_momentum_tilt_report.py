from __future__ import annotations

import copy
import json
import math
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from usfddk.french_size_momentum_tilt_research import (  # noqa: E402
    build_french_size_momentum_tilt_research,
)

ARTIFACT = ROOT / "artifacts/short_term_french_size_momentum_tilt_validation.json"
SITE_DATA = ROOT / "site/data/short-term-french-size-momentum-tilt.json"
REPORT = ROOT / "docs/SHORT_TERM_FRENCH_SIZE_MOMENTUM_TILT_RESEARCH_REPORT.md"


def _canonicalize(value: Any) -> Any:
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("研究輸出包含非有限浮點數")
        digits = 10 if 0 < abs(value) < 1e-5 else 12
        return float(f"{value:.{digits}g}")
    if isinstance(value, dict):
        return {key: _canonicalize(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_canonicalize(item) for item in value]
    return value


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(text, encoding="utf-8")
    temporary.replace(path)


def _pct(value: float, digits: int = 2) -> str:
    return f"{value * 100:.{digits}f}%"


def _pp(value: float, digits: int = 2) -> str:
    return f"{value * 100:+.{digits}f} 個百分點"


def _money(value: float) -> str:
    return f"US${value:,.0f}"


def _metrics_row(label: str, metrics: dict[str, Any]) -> str:
    return (
        f"| {label} | {_pct(metrics['cagr'])} | {metrics['excess_sharpe']:.2f} | "
        f"{_pct(metrics['volatility'], 1)} | {_pct(metrics['max_drawdown'], 1)} | "
        f"{metrics['calmar']:.2f} | {_money(metrics['hypothetical_1000_usd_end'])} |"
    )


def _render_report(result: dict[str, Any]) -> str:
    primary = result["primary_external_period"]
    recent = result["recent_confirmation_period"]
    factor = result["factor_regression_full_history"]
    cost = result["frozen_candidate"]["cost_sensitivity_full_history"]
    frontier = result["concentration_frontier"]

    labels = (
        ("market", "French 美國市場"),
        ("all_25_equal", "全 25 cells 等權"),
        ("top2", "每個 size 的 Prior 4–5"),
        ("top1", "每個 size 的 Prior 5"),
        ("big_hi_prior_12_2", "Big Hi PRIOR 12–2"),
        ("unconditional_hi_prior_12_2", "未分 size 的 Hi PRIOR 12–2"),
        ("short_window_linear_tilt", "Prior 1–1 短窗線性傾斜"),
    )
    primary_rows = [
        _metrics_row("全池線性動量傾斜（候選）", primary["candidate_metrics"]),
        *[_metrics_row(label, primary["baseline_metrics"][key]) for key, label in labels],
    ]
    recent_rows = [
        _metrics_row("全池線性動量傾斜（候選）", recent["candidate_metrics"]),
        *[_metrics_row(label, recent["baseline_metrics"][key]) for key, label in labels],
        _metrics_row("QQQ 買入持有", recent["baseline_metrics"]["QQQ"]),
        _metrics_row("SPY 買入持有", recent["baseline_metrics"]["SPY"]),
    ]
    frontier_rows = [
        "| 集中度 | 1963–2005 CAGR | 超額 Sharpe | 最大跌幅 | 2006–2026 CAGR | 超額 Sharpe | 最大跌幅 |",
        "|---|---:|---:|---:|---:|---:|---:|",
        *[
            "| {label} | {pcagr} | {psharpe:.2f} | {pmdd} | {rcagr} | {rsharpe:.2f} | {rmdd} |".format(
                label=label,
                pcagr=_pct(frontier[kind]["primary"]["cagr"]),
                psharpe=frontier[kind]["primary"]["excess_sharpe"],
                pmdd=_pct(frontier[kind]["primary"]["max_drawdown"], 1),
                rcagr=_pct(frontier[kind]["recent"]["cagr"]),
                rsharpe=frontier[kind]["recent"]["excess_sharpe"],
                rmdd=_pct(frontier[kind]["recent"]["max_drawdown"], 1),
            )
            for kind, label in (
                ("equal", "等權"),
                ("linear", "線性 1:2:3:4:5"),
                ("squared", "平方 1:4:9:16:25"),
                ("top2", "只持 Prior 4–5"),
                ("top1", "只持 Prior 5"),
            )
        ],
    ]
    rank_rows = [
        "| Prior 12–2 五分位 | 1963–2005 CAGR | 最大跌幅 | 2006–2026 CAGR | 最大跌幅 |",
        "|---:|---:|---:|---:|---:|",
        *[
            "| {rank} | {pcagr} | {pmdd} | {rcagr} | {rmdd} |".format(
                rank=p["prior_rank"],
                pcagr=_pct(p["metrics"]["cagr"]),
                pmdd=_pct(p["metrics"]["max_drawdown"], 1),
                rcagr=_pct(r["metrics"]["cagr"]),
                rmdd=_pct(r["metrics"]["max_drawdown"], 1),
            )
            for p, r in zip(
                result["prior_rank_diagnostic"]["primary"],
                result["prior_rank_diagnostic"]["recent"],
                strict=True,
            )
        ],
    ]
    primary_passed = [key for key, value in primary["gates"].items() if value]
    primary_failed = [key for key, value in primary["gates"].items() if not value]
    recent_passed = [key for key, value in recent["gates"].items() if value]
    recent_failed = [key for key, value in recent["gates"].items() if not value]
    p_market = primary["comparisons"]["market"]
    p_equal = primary["comparisons"]["all_25_equal"]
    r_market = recent["comparisons"]["market"]
    r_equal = recent["comparisons"]["all_25_equal"]

    return "\n".join(
        [
            "# 全池動量傾斜：French 25 Size × Prior 12–2 研究報告",
            "",
            "凍結協議：2026-08-04｜正式資料：1963-01 至 2026-05｜狀態：**經濟驗證失敗，不啟動 Paper**",
            "",
            "## 一頁結論",
            "",
            f"- 官方首次下載及數據合約 **{result['gate_breakdown']['data']}**；主要外部期 **{result['gate_breakdown']['primary']}**，近期確認期 **{result['gate_breakdown']['recent']}**，總計 **{result['passed_gate_count']}/{result['required_gate_count']}**。",
            f"- 1963–2005 候選 CAGR {_pct(primary['candidate_metrics']['cagr'])}，勝市場 {_pp(primary['candidate_metrics']['cagr'] - primary['baseline_metrics']['market']['cagr'])}、勝全池等權 {_pp(primary['candidate_metrics']['cagr'] - primary['baseline_metrics']['all_25_equal']['cagr'])}；但只保留 Top 1 CAGR 的 {primary['candidate_metrics']['cagr'] / primary['baseline_metrics']['top1']['cagr'] * 100:.1f}%，未達 80% 門檻。",
            f"- 2006–2026 候選 CAGR {_pct(recent['candidate_metrics']['cagr'])}，市場 {_pct(recent['baseline_metrics']['market']['cagr'])}、SPY {_pct(recent['baseline_metrics']['SPY']['cagr'])}、QQQ {_pct(recent['baseline_metrics']['QQQ']['cagr'])}；不是現代市場的高回報勝出者。",
            f"- 近期 50 bps 成本後 CAGR {_pct(recent['candidate_50bps_metrics']['cagr'])}、US$1,000 只餘 {_money(recent['candidate_50bps_metrics']['hypothetical_1000_usd_end'])}。每月全面重組的成本風險足以推翻策略。",
            "- 分散傾斜可穩定勝全池等權，卻不能勝市場；加強集中度在早期顯著增加回報，近期則趨平，證明不能用早期集中結果推論未來。",
            "- French cells 不是證券，也不提供逐股 point-in-time 名單。Paper、實金、持倉及今日買賣動作全部 **US$0**。",
            "",
            "## 主要外部期：1963–2005",
            "",
            "| 策略／baseline | 年率化回報 | 超額 Sharpe | 波幅 | 最大跌幅 | Calmar | US$1,000 期末值 |",
            "|---|---:|---:|---:|---:|---:|---:|",
            *primary_rows,
            "",
            f"兩個固定分段均勝全池等權：1963–1984 {_pp(primary['fixed_splits']['1963_to_1984']['edge_vs_all_25_equal'])}，1985–2005 {_pp(primary['fixed_splits']['1985_to_2005']['edge_vs_all_25_equal'])}；但後半段較市場只有 {_pp(primary['fixed_splits']['1985_to_2005']['edge_vs_market'])}，未達 0.5 個百分點門檻。",
            "",
            "## 近期確認期：2006–2026",
            "",
            "| 策略／baseline | 年率化回報 | 超額 Sharpe | 波幅 | 最大跌幅 | Calmar | US$1,000 期末值 |",
            "|---|---:|---:|---:|---:|---:|---:|",
            *recent_rows,
            "",
            f"2006–2015 較市場 {_pp(recent['fixed_splits']['2006_to_2015']['edge_vs_market'])}；2016–2026 更落後 {_pp(recent['fixed_splits']['2016_to_end']['edge_vs_market'])}。近期 60 月窗口勝市場只有 {_pct(recent['rolling_60m_vs_market']['cagr_win_fraction'], 1)}，最新窗口落後 {_pp(recent['rolling_60m_vs_market']['latest_cagr_difference'])}。",
            "",
            "## 分散與集中度前沿",
            "",
            *frontier_rows,
            "",
            "早期回報隨集中度單調上升；近期 Top 2、平方及線性只在 8.31%–8.50% 之間，Top 1 反而降至 8.18%。這是『排名訊號仍在、集中紅利已弱化』，不是應該追買最集中組合的證據。",
            "",
            "## Prior 排名診斷",
            "",
            *rank_rows,
            "",
            "主要期五分位呈單調上升；近期由 Prior 3 開始轉平，Prior 5 不再領先。全池線性傾斜仍勝等權，但增量不足以補回市場機會成本。",
            "",
            "## 成本、滾動窗口及統計",
            "",
            f"- 全歷史 10／25／50 bps CAGR：{_pct(cost['10_bps']['cagr'])}／{_pct(cost['25_bps']['cagr'])}／{_pct(cost['50_bps']['cagr'])}；50 bps 的 US$1,000 期末值只有 {_money(cost['50_bps']['hypothetical_1000_usd_end'])}。",
            f"- 主要期 60 月窗勝市場 {_pct(primary['rolling_60m_vs_market']['cagr_win_fraction'], 1)}、勝全池等權 {_pct(primary['rolling_60m_vs_all_25_equal']['cagr_win_fraction'], 1)}；近期分別 {_pct(recent['rolling_60m_vs_market']['cagr_win_fraction'], 1)}／{_pct(recent['rolling_60m_vs_all_25_equal']['cagr_win_fraction'], 1)}。",
            f"- 主要期對市場／全池等權 NW t={p_market['newey_west']['t_stat']:.2f}／{p_equal['newey_west']['t_stat']:.2f}；近期為 {r_market['newey_west']['t_stat']:.2f}／{r_equal['newey_west']['t_stat']:.2f}。",
            f"- 近期對市場／全池等權 PSR={_pct(r_market['active_probabilistic_sharpe']['probability'])}／{_pct(r_equal['active_probabilistic_sharpe']['probability'])}；6,204 trials DSR={_pct(r_market['active_global_deflated_sharpe']['probability'], 6)}／{_pct(r_equal['active_global_deflated_sharpe']['probability'], 4)}。",
            f"- 30 路候選家族 CSCV PBO：主要 {_pct(result['pbo']['primary']['pbo'], 1)}，近期 {_pct(result['pbo']['recent']['pbo'], 1)}；近期超過 20% 上限。",
            f"- 全歷史五因子 alpha {_pct(factor['annualized_alpha'])}、市場 beta {factor['market_beta']:.2f}、SMB beta {factor['smb_beta']:.2f}、MOM beta {factor['mom_beta']:.2f}、R² {_pct(factor['r_squared'], 1)}；大部分波動是市場與小型股暴露，不是獨立 alpha。",
            "",
            "## 48 道閘門",
            "",
            f"主要期通過（9）：`{', '.join(primary_passed)}`。",
            "",
            f"主要期失敗（10）：`{', '.join(primary_failed)}`。",
            "",
            f"近期通過（4）：`{', '.join(recent_passed)}`。",
            "",
            f"近期失敗（15）：`{', '.join(recent_failed)}`。",
            "",
            "所有失敗都保留；沒有事後更換權重、成本、起訖日、集中度或 baseline。",
            "",
            "## 數據與可交易性",
            "",
            "- 新資料來自 Kenneth French 官方 25 Size × Prior 12–2 月度 CSV：每月以 NYSE size 五分位與 prior 2–12 回報五分位交集形成 25 個 value-weighted 組合；t 月組合在 t−1 月形成。",
            "- 學術 cells 涵蓋 NYSE、AMEX 及 NASDAQ，減少用今日成份股倒推的倖存者偏差，但不是逐股 point-in-time／退市賬本，也不可直接落盤。",
            "- QQQ／SPY 只在 2006 後用既有調整價快照作產品機會成本；沒有用現時成份股回填歷史。",
            "- 來源：[Kenneth French Data Library](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/Data_Library.html)及[25 Size × Prior 12–2 方法](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/Data_Library/det_25_port_form_sz_pr_12_2.html)。",
            "",
            "## 決定",
            "",
            "本輪是首次未見的全池動量傾斜驗證：數據 10/10，但經濟只得 13/38，總計 23/48，判定失敗。它支持『中長窗橫截面排名比短窗更穩』，不支持『可交易且能勝市場的短線策略』。下一個升格入口仍須合格逐股 point-in-time 成分、退市／收購回報、公司行動、流動性、bid-ask spread 及精確成交成本；其後按凍結個股協議由全現金開始、不可回填的前瞻 Paper。",
            "",
        ]
    )


def main() -> int:
    result = _canonicalize(build_french_size_momentum_tilt_research(ROOT))
    _write(
        ARTIFACT,
        json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
    )

    site_result = copy.deepcopy(result)
    for key in ("primary_external_period", "recent_confirmation_period"):
        site_result[key]["rolling_60m_vs_market"].pop("series", None)
        site_result[key]["rolling_60m_vs_all_25_equal"].pop("series", None)
    for key in ("primary", "recent"):
        site_result["pbo"][key].pop("logits", None)
    _write(
        SITE_DATA,
        json.dumps(site_result, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
    )
    _write(REPORT, _render_report(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
