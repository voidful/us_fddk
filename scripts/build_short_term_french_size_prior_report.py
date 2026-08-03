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

from usfddk.french_size_prior_research import (  # noqa: E402
    build_french_size_prior_research,
)

ARTIFACT = ROOT / "artifacts/short_term_french_size_prior_validation.json"
SITE_DATA = ROOT / "site/data/short-term-french-size-prior.json"
REPORT = ROOT / "docs/SHORT_TERM_FRENCH_SIZE_PRIOR_RESEARCH_REPORT.md"


def _canonicalize(value: Any) -> Any:
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("研究輸出包含非有限浮點數")
        # SciPy's extreme normal-CDF tails can differ in the last few ulps
        # across platforms. Narrow only those tiny probabilities so the rest
        # of the committed research precision remains unchanged.
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
    size_primary = result["size_direction_diagnostic"]["primary"]
    size_recent = result["size_direction_diagnostic"]["recent"]
    full_cost = result["frozen_candidate"]["cost_sensitivity_full_history"]

    primary_rows = [
        _metrics_row("Big Hi PRIOR 1–1（唯一候選）", primary["candidate_metrics"]),
        *[
            _metrics_row(label, primary["baseline_metrics"][key])
            for key, label in (
                ("market", "French 美國市場"),
                ("big_row_equal", "大型股五個 prior 組合等權"),
                ("all_25_equal", "全 25 cells 等權"),
                ("big_lo_prior", "Big Lo PRIOR 反方向"),
                ("unconditional_hi_prior_1_1", "未分 size 的 Hi PRIOR 1–1"),
                ("long_momentum_hi_12_2", "Hi PRIOR 12–2 長窗動量"),
            )
        ],
    ]
    recent_rows = [
        _metrics_row("Big Hi PRIOR 1–1（唯一候選）", recent["candidate_metrics"]),
        *[
            _metrics_row(label, recent["baseline_metrics"][key])
            for key, label in (
                ("market", "French 美國市場"),
                ("big_row_equal", "大型股五個 prior 組合等權"),
                ("all_25_equal", "全 25 cells 等權"),
                ("big_lo_prior", "Big Lo PRIOR 反方向"),
                ("unconditional_hi_prior_1_1", "未分 size 的 Hi PRIOR 1–1"),
                ("long_momentum_hi_12_2", "Hi PRIOR 12–2 長窗動量"),
                ("QQQ", "QQQ 買入持有"),
                ("SPY", "SPY 買入持有"),
            )
        ],
    ]
    size_rows = [
        "| Size 五分位 | 1963–2005 Hi−Lo CAGR | 2006–2026 Hi−Lo CAGR | 近期 Hi CAGR | 近期 Hi 最大跌幅 |",
        "|---:|---:|---:|---:|---:|",
        *[
            "| {size} | {primary_edge} | {recent_edge} | {recent_hi} | {recent_mdd} |".format(
                size=row_recent["size_quintile"],
                primary_edge=_pp(row_primary["high_minus_low_cagr"]),
                recent_edge=_pp(row_recent["high_minus_low_cagr"]),
                recent_hi=_pct(row_recent["high_prior_cagr"]),
                recent_mdd=_pct(row_recent["high_prior_max_drawdown"], 1),
            )
            for row_primary, row_recent in zip(size_primary, size_recent, strict=True)
        ],
    ]
    primary_passed = [key for key, value in primary["gates"].items() if value]
    recent_passed = [key for key, value in recent["gates"].items() if value]
    p_market = primary["comparisons"]["market"]
    r_market = recent["comparisons"]["market"]
    r_big = recent["comparisons"]["big_row_equal"]

    return "\n".join(
        [
            "# 大型股短窗贏家：French 25 Size × Prior 1–1 研究報告",
            "",
            "凍結協議：2026-08-04｜正式資料：1963-01 至 2026-05｜狀態：**經濟驗證失敗，不啟動 Paper**",
            "",
            "## 一頁結論",
            "",
            f"- 官方首次下載及數據合約 **{result['gate_breakdown']['data']}**；主要外部期 **{result['gate_breakdown']['primary']}**，近期確認期 **{result['gate_breakdown']['recent']}**，總計 **{result['passed_gate_count']}/{result['required_gate_count']}**。",
            f"- 1963–2005 候選年率化回報 {_pct(primary['candidate_metrics']['cagr'])}，市場 {_pct(primary['baseline_metrics']['market']['cagr'])}，大型股同 size 等權 {_pct(primary['baseline_metrics']['big_row_equal']['cagr'])}；只通過 PBO 一道。",
            f"- 2006–2026 候選 {_pct(recent['candidate_metrics']['cagr'])}，市場 {_pct(recent['baseline_metrics']['market']['cagr'])}，QQQ {_pct(recent['baseline_metrics']['QQQ']['cagr'])}。候選只勝全 25 cells 等權、Big Lo PRIOR及跌幅限制，仍不是高回報勝出者。",
            f"- 近期 50 bps 成本後 CAGR {_pct(recent['candidate_50bps_metrics']['cagr'])}；對市場單邊成本 break-even 只有 {recent['cost_break_even_vs_baselines']['market']['one_way_bps']:.2f} bps，對大型股等權只有 {recent['cost_break_even_vs_baselines']['big_row_equal']['one_way_bps']:.2f} bps。",
            "- 結論不是『改買小型股』：早期五個 size 的 Hi PRIOR 全部落後 Lo PRIOR；近期正方向才出現，屬時期不穩定。沒有合格逐股 point-in-time／退市賬本，不能產生股票名單。",
            "- US$1,000 只作歷史尺度；Paper、實金、持倉及今日買賣動作全部 **US$0**。",
            "",
            "## 主要外部期：1963–2005",
            "",
            "| 策略／baseline | 年率化回報 | 超額 Sharpe | 波幅 | 最大跌幅 | Calmar | US$1,000 期末值 |",
            "|---|---:|---:|---:|---:|---:|---:|",
            *primary_rows,
            "",
            f"兩個固定分段均失敗：1963–1984 較市場 {_pp(primary['fixed_splits']['1963_to_1984']['edge_vs_market'])}，1985–2005 {_pp(primary['fixed_splits']['1985_to_2005']['edge_vs_market'])}。60 月窗勝市場只有 {_pct(primary['rolling_60m_vs_market']['cagr_win_fraction'], 1)}。",
            "",
            "## 近期確認期：2006–2026",
            "",
            "| 策略／baseline | 年率化回報 | 超額 Sharpe | 波幅 | 最大跌幅 | Calmar | US$1,000 期末值 |",
            "|---|---:|---:|---:|---:|---:|---:|",
            *recent_rows,
            "",
            f"2006–2015 候選只得 {_pct(recent['fixed_splits']['2006_to_2015']['candidate_cagr'])}，較市場 {_pp(recent['fixed_splits']['2006_to_2015']['edge_vs_market'])}；2016–2026 才較市場 {_pp(recent['fixed_splits']['2016_to_end']['edge_vs_market'])}。不能用後段反彈覆蓋前段失敗。",
            "",
            "## Size × 正反方向",
            "",
            *size_rows,
            "",
            "近期大型股 Hi−Lo 差為正，主要由 Big Lo PRIOR 近期表現極弱造成；候選本身仍落後市場及 QQQ。這張表只作機制診斷，不選事後最佳 size。",
            "",
            "## 成本、滾動窗口與統計",
            "",
            f"- 全歷史 10／25／50 bps CAGR：{_pct(full_cost['10_bps']['cagr'])}／{_pct(full_cost['25_bps']['cagr'])}／{_pct(full_cost['50_bps']['cagr'])}；假設年換手約 {result['frozen_candidate']['full_history_metrics_10bps']['annual_turnover']:.2f} 倍。",
            f"- 近期 60 月窗勝市場 {_pct(recent['rolling_60m_vs_market']['cagr_win_fraction'], 1)}，勝大型股等權 {_pct(recent['rolling_60m_vs_big_row_equal']['cagr_win_fraction'], 1)}；門檻均為 60%。",
            f"- 主要期對市場 NW t={p_market['newey_west']['t_stat']:.2f}；近期對市場／大型股等權 NW t={r_market['newey_west']['t_stat']:.2f}／{r_big['newey_west']['t_stat']:.2f}。",
            f"- 近期對市場／大型股等權 PSR={_pct(r_market['active_probabilistic_sharpe']['probability'])}／{_pct(r_big['active_probabilistic_sharpe']['probability'])}；6,175 trials DSR={_pct(r_market['active_global_deflated_sharpe']['probability'], 4)}／{_pct(r_big['active_global_deflated_sharpe']['probability'], 4)}。",
            f"- CSCV PBO：主要 {_pct(result['pbo']['primary']['pbo'], 1)}，近期 {_pct(result['pbo']['recent']['pbo'], 1)}；近期高於 20% 上限。",
            f"- 五因子年率化 alpha {_pct(factor['annualized_alpha'])}，市場 beta {factor['market_beta']:.2f}，SMB beta {factor['smb_beta']:.2f}，ST_Rev beta {factor['short_term_reversal_beta']:.2f}，R² {_pct(factor['r_squared'], 1)}。",
            "",
            "## 門檻逐項界線",
            "",
            f"主要期通過：`{', '.join(primary_passed)}`。",
            "",
            f"近期通過：`{', '.join(recent_passed)}`。",
            "",
            "所有未通過項目都保留；不更換 size、prior 方向、權重、成本、起訖日或 baseline。",
            "",
            "## 數據及可交易性",
            "",
            "- 新資料來自 Kenneth French 官方 25 Size × Short-Term Reversal 月度 CSV；組合每月涵蓋具備所需資料的 NYSE、AMEX及 NASDAQ 股票，使用 NYSE 五分位 breakpoints。",
            "- 學術 cells 降低以今日成份股倒推的倖存者偏差，但不是逐股 point-in-time 賬本，也不是可買入證券。",
            "- QQQ／SPY 只在 2006 後用既有調整價快照作產品機會成本；沒有用其現時成份股回推歷史。",
            "- 來源：[Kenneth French Data Library](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/Data_Library.html)及[25 Size × Short-Term Reversal 方法](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/Data_Library/det_25_port_form_sz_pr_1_0.html)。",
            "",
            "## 決定",
            "",
            "本輪是首次未見的 size-conditioned 機制驗證，數據 10/10，但經濟只得 14/44，判定失敗。French cells 不能開 Paper。下一個可升格入口仍須合格逐股 point-in-time 成分、退市／收購回報、公司行動、流動性及精確成交成本，按凍結個股 v1 從全現金開始不可回填的前瞻 Paper。",
            "",
        ]
    )


def main() -> int:
    result = _canonicalize(build_french_size_prior_research(ROOT))
    _write(
        ARTIFACT,
        json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
    )

    site_result = copy.deepcopy(result)
    for key in ("primary_external_period", "recent_confirmation_period"):
        site_result[key]["rolling_60m_vs_market"].pop("series", None)
        site_result[key]["rolling_60m_vs_big_row_equal"].pop("series", None)
    _write(
        SITE_DATA,
        json.dumps(site_result, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
    )
    _write(REPORT, _render_report(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
