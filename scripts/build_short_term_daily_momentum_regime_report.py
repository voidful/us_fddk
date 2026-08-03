from __future__ import annotations

import json
import math
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from usfddk.daily_momentum_regime import (  # noqa: E402
    build_daily_momentum_regime_research,
)

VALIDATION = ROOT / "artifacts/short_term_daily_momentum_regime_validation.json"
SITE_DATA = ROOT / "site/data/short-term-daily-momentum-regime.json"
REPORT = ROOT / "docs/SHORT_TERM_DAILY_MOMENTUM_REGIME_RESEARCH_REPORT.md"


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


def _pct(value: float, digits: int = 2) -> str:
    return f"{value * 100:.{digits}f}%"


def _pp(value: float, digits: int = 2) -> str:
    sign = "+" if value >= 0.0 else ""
    return f"{sign}{value * 100:.{digits}f}pp"


def _money(value: float) -> str:
    return f"US${value:,.0f}"


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    rendered = json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(rendered, encoding="utf-8")
    temporary.replace(path)


def _site_summary(data: dict[str, Any]) -> dict[str, Any]:
    early = data["early_confirmation"]
    recent = data["recent_20y"]
    recent_comparison = recent["comparisons"]["qqq"]
    return {
        "schema_version": "1.0",
        "round": 10,
        "status": data["status"],
        "research_role": data["research_role"],
        "independent_first_seen_evidence": False,
        "headline": "每日環境共振近期失效：27/48，不建立 Paper",
        "original_data_contract": {
            "passed": data["original_first_download_passed_gate_count"],
            "required": data["original_first_download_required_gate_count"],
            "status": data["original_first_download_status"],
            "reason": "官方 marker 多一個 Average 前綴；原輪在策略計算前停止",
        },
        "repair_diagnostic": {
            "passed": data["passed_gate_count"],
            "required": data["required_gate_count"],
            "data_passed": int(sum(data["data_gates"].values())),
            "data_required": len(data["data_gates"]),
            "early_passed": int(sum(data["early_gates"].values())),
            "early_required": len(data["early_gates"]),
            "recent_passed": int(sum(data["recent_gates"].values())),
            "recent_required": len(data["recent_gates"]),
            "mechanism_passed": int(sum(data["mechanism_gates"].values())),
            "mechanism_required": len(data["mechanism_gates"]),
        },
        "early": {
            "period": [early["start"], early["end"]],
            "candidate": early["candidate_metrics"],
            "market": early["baseline_metrics"]["french_market"],
            "raw_hi_prior": early["baseline_metrics"]["raw_hi_prior"],
            "second_half_edge_vs_market": early["fixed_halves"]["second_half"][
                "cagr_difference"
            ],
            "pbo": early["pbo"]["pbo"],
        },
        "recent": {
            "period": [recent["start"], recent["end"]],
            "candidate": recent["candidate_metrics"],
            "qqq": recent["baseline_metrics"]["qqq"],
            "spy": recent["baseline_metrics"]["spy"],
            "market": recent["baseline_metrics"]["french_market"],
            "raw_hi_prior": recent["baseline_metrics"]["raw_hi_prior"],
            "matched_market_exposure": recent["baseline_metrics"][
                "matched_market_exposure"
            ],
            "binary_market_60": recent["baseline_metrics"]["binary_market_60"],
            "no_resonance": recent["baseline_metrics"]["no_resonance"],
            "first_half": recent["fixed_halves"]["first_10y"],
            "second_half": recent["fixed_halves"]["second_10y"],
            "rolling_three_year": {
                key: value
                for key, value in recent["rolling_three_year"].items()
                if key != "series"
            },
            "newey_west_vs_qqq": recent_comparison["newey_west"],
            "psr_vs_qqq": recent_comparison["active_probabilistic_sharpe"]["probability"],
            "dsr_vs_qqq": recent_comparison["active_global_deflated_sharpe"]["probability"],
            "pbo": recent["pbo"]["pbo"],
            "exposure": recent["exposure_diagnostics"],
            "cost_and_drag_grid": recent["cost_and_drag_grid"],
            "factor_regression": recent["factor_regression"],
        },
        "stress_periods_recent": data["stress_periods_recent"],
        "crisis_drawdown_wins_vs_qqq": data["crisis_drawdown_wins_vs_qqq"],
        "failed_gates": {
            "early": [key for key, value in data["early_gates"].items() if not value],
            "recent": [key for key, value in data["recent_gates"].items() if not value],
            "mechanism": [
                key for key, value in data["mechanism_gates"].items() if not value
            ],
        },
        "point_in_time_stock_ledger_readiness": "1/20",
        "paper_eligible": False,
        "trade_ready": False,
        "paper_state_created": False,
        "paper_position_count": 0,
        "real_money_action_usd": 0,
        "decision": data["decision"],
    }


def _render_report(data: dict[str, Any]) -> str:
    early = data["early_confirmation"]
    recent = data["recent_20y"]
    em = early["candidate_metrics"]
    rm = recent["candidate_metrics"]
    eb = early["baseline_metrics"]
    rb = recent["baseline_metrics"]
    rc = recent["comparisons"]["qqq"]
    early_passed = int(sum(data["early_gates"].values()))
    recent_passed = int(sum(data["recent_gates"].values()))
    mechanism_passed = int(sum(data["mechanism_gates"].values()))
    recent_grid = {
        (row["annual_drag"], row["overlay_cost_bps"]): row["metrics"]
        for row in recent["cost_and_drag_grid"]
    }
    stress = data["stress_periods_recent"]
    return f"""# 美股短線高回報研究｜第十輪每日動量環境共振報告

研究日期：2026-08-04

正式近期：{recent['start']} 至 {recent['end']}

狀態：**27/48，失敗；短線 Paper 全現金；實金動作 US$0**

## 一頁結論

台股 `tst_wocker` 的 20／60 日環境、`tw-block-warrant` 的多窗共振，以及
`tst_wocker_filter_lab` 的同池 baseline／凍結快照，被翻譯成一個沒有槓桿的每日
0／50／100% `Hi PRIOR` 持倉。它沒有在近期美股成立：

| 近期 20 年路徑 | CAGR | 超額 Sharpe | 最大跌幅 | US$1,000 歷史終值 |
|---|---:|---:|---:|---:|
| 四證據環境共振候選 | **{_pct(rm['cagr'])}** | {rm['excess_sharpe']:.2f} | {_pct(rm['max_drawdown'], 1)} | {_money(rm['hypothetical_1000_usd_end'])} |
| QQQ 買入持有 | {_pct(rb['qqq']['cagr'])} | {rb['qqq']['excess_sharpe']:.2f} | {_pct(rb['qqq']['max_drawdown'], 1)} | {_money(rb['qqq']['hypothetical_1000_usd_end'])} |
| SPY 買入持有 | {_pct(rb['spy']['cagr'])} | {rb['spy']['excess_sharpe']:.2f} | {_pct(rb['spy']['max_drawdown'], 1)} | {_money(rb['spy']['hypothetical_1000_usd_end'])} |
| French 市場 | {_pct(rb['french_market']['cagr'])} | {rb['french_market']['excess_sharpe']:.2f} | {_pct(rb['french_market']['max_drawdown'], 1)} | {_money(rb['french_market']['hypothetical_1000_usd_end'])} |
| 永久 Hi PRIOR（同 5% 拖累） | {_pct(rb['raw_hi_prior']['cagr'])} | {rb['raw_hi_prior']['excess_sharpe']:.2f} | {_pct(rb['raw_hi_prior']['max_drawdown'], 1)} | {_money(rb['raw_hi_prior']['hypothetical_1000_usd_end'])} |
| 相同持倉比率 French 市場 | {_pct(rb['matched_market_exposure']['cagr'])} | {rb['matched_market_exposure']['excess_sharpe']:.2f} | {_pct(rb['matched_market_exposure']['max_drawdown'], 1)} | {_money(rb['matched_market_exposure']['hypothetical_1000_usd_end'])} |

候選較 QQQ 每年落後 {_pp(rm['cagr'] - rb['qqq']['cagr'])}；相對 QQQ 的
Newey–West t = {rc['newey_west']['t_stat']:.2f}、PSR = {_pct(rc['active_probabilistic_sharpe']['probability'])}、
6,208 次搜尋校正 DSR 幾乎為零。這不是「回報稍低但更穩」：最大跌幅仍接近五成，
而回報只略高於現金尺度。

## 凍結順序與 schema 失敗

第十輪在任何新日檔前提交原協議及映射，唯一候選、5% 年度學術實作拖累、
10／25／50 bps、baseline、日期及 48 道門檻全部固定。首次下載的 URL、ZIP 及 member
正確，但官方 marker 是 `Average Value Weighted Returns -- Daily`，原映射少了
`Average `。原輪按設計在策略計算前以 **4/9** 停止；原 ZIP、SHA-256 及失敗收據永久
保留。

其後另立 schema-informed repair，只容許精確增加該前綴，不重新下載、不改候選或門檻。
由於 schema 檢視已看見首批 1926 原始行，本報告固定
`independent_first_seen_evidence=false`，不能冒充完全獨立的首次外部結果。

## 唯一候選

day t 持倉只使用 day t−1 數據。四項證據是 French 市場高於 20 日平均、
高於 60 日平均、十個 Prior 組合至少 60% 高於各自 60 日平均，以及 Hi PRIOR 相對
十組等權池在 5／10／15／20 日至少兩窗領先。0–1 分持 RF、2 分 50% Hi PRIOR、
3–4 分 100% Hi PRIOR；不借款、不沽空、不用 VIX、ATR、止蝕或事後例外。

French 每日十分位是 CRSP-based point-in-time 學術組合，不是 ETF。所有 Hi PRIOR
路徑事前先扣 5% 年度實作拖累，另按每日持倉改變扣成本。這仍不能取代底層逐股換手、
bid-ask spread 或開市成交，因此即使全過亦不准 Paper。

## 早期成立、後期崩解

| 時期 | 候選 CAGR | 市場 CAGR | 永久 Hi CAGR | 最大跌幅 | 門檻 |
|---|---:|---:|---:|---:|---:|
| 1963–2006 | {_pct(em['cagr'])} | {_pct(eb['french_market']['cagr'])} | {_pct(eb['raw_hi_prior']['cagr'])} | {_pct(em['max_drawdown'], 1)} | {early_passed}/15 |
| 2006–2026 | {_pct(rm['cagr'])} | {_pct(rb['french_market']['cagr'])} | {_pct(rb['raw_hi_prior']['cagr'])} | {_pct(rm['max_drawdown'], 1)} | {recent_passed}/19 |

早期前半候選較市場 CAGR 高
{_pp(early['fixed_halves']['first_half']['cagr_difference'])}，但 1985–2006 已反向落後
{_pp(early['fixed_halves']['second_half']['cagr_difference'])}。近期兩個固定十年分別只錄得
{_pct(recent['fixed_halves']['first_10y']['candidate_cagr'])}及
{_pct(recent['fixed_halves']['second_10y']['candidate_cagr'])}，同期落後 QQQ
{_pp(recent['fixed_halves']['first_10y']['cagr_difference'])}及
{_pp(recent['fixed_halves']['second_10y']['cagr_difference'])}。

204 個近期滾動三年窗只有
{_pct(recent['rolling_three_year']['cagr_win_fraction'])}勝 QQQ，中位 CAGR 差
{_pp(recent['rolling_three_year']['median_cagr_difference'])}。這是跨世代失效，不是單一
危機或起點選擇。

## 成本與實作拖累

候選近期平均持倉比率 {_pct(rm['average_exposure'])}，0／50／100% 狀態分別佔
{_pct(recent['exposure_diagnostics']['state_fraction']['0.0'])}、
{_pct(recent['exposure_diagnostics']['state_fraction']['0.5'])}、
{_pct(recent['exposure_diagnostics']['state_fraction']['1.0'])}；每年轉倉約
{rm['annual_turnover']:.1f} 倍。

| 年度學術拖累 | 轉倉成本 | 近期 CAGR | 最大跌幅 | US$1,000 終值 |
|---:|---:|---:|---:|---:|
| 2% | 10 bps | {_pct(recent_grid[(0.02, 10.0)]['cagr'])} | {_pct(recent_grid[(0.02, 10.0)]['max_drawdown'], 1)} | {_money(recent_grid[(0.02, 10.0)]['hypothetical_1000_usd_end'])} |
| 2% | 50 bps | {_pct(recent_grid[(0.02, 50.0)]['cagr'])} | {_pct(recent_grid[(0.02, 50.0)]['max_drawdown'], 1)} | {_money(recent_grid[(0.02, 50.0)]['hypothetical_1000_usd_end'])} |
| **5%** | **10 bps** | **{_pct(recent_grid[(0.05, 10.0)]['cagr'])}** | **{_pct(recent_grid[(0.05, 10.0)]['max_drawdown'], 1)}** | **{_money(recent_grid[(0.05, 10.0)]['hypothetical_1000_usd_end'])}** |
| 5% | 50 bps | {_pct(recent_grid[(0.05, 50.0)]['cagr'])} | {_pct(recent_grid[(0.05, 50.0)]['max_drawdown'], 1)} | {_money(recent_grid[(0.05, 50.0)]['hypothetical_1000_usd_end'])} |
| 10% | 10 bps | {_pct(recent_grid[(0.10, 10.0)]['cagr'])} | {_pct(recent_grid[(0.10, 10.0)]['max_drawdown'], 1)} | {_money(recent_grid[(0.10, 10.0)]['hypothetical_1000_usd_end'])} |
| 10% | 50 bps | {_pct(recent_grid[(0.10, 50.0)]['cagr'])} | {_pct(recent_grid[(0.10, 50.0)]['max_drawdown'], 1)} | {_money(recent_grid[(0.10, 50.0)]['hypothetical_1000_usd_end'])} |

即使把拖累降到 2% 並只扣 10 bps，近期 CAGR 亦只有
{_pct(recent_grid[(0.02, 10.0)]['cagr'])}；不是單靠一個保守成本假設才輸。

## 風險與歸因

環境減倉在三段近期危機都令最大跌幅比 QQQ 淺：金融海嘯
{_pct(stress['global_financial_crisis']['candidate']['max_drawdown'], 1)} 對
{_pct(stress['global_financial_crisis']['qqq']['max_drawdown'], 1)}、新冠急跌
{_pct(stress['covid_crash']['candidate']['max_drawdown'], 1)} 對
{_pct(stress['covid_crash']['qqq']['max_drawdown'], 1)}、2022 年
{_pct(stress['rate_shock_2022']['candidate']['max_drawdown'], 1)} 對
{_pct(stress['rate_shock_2022']['qqq']['max_drawdown'], 1)}。風控腿不是完全無效，但它
犧牲的長期升幅遠高於避開的跌幅。

近期三因子年率化 alpha 為
{_pct(recent['factor_regression']['annualized_alpha'])}，市場 beta
{recent['factor_regression']['market_beta']:.2f}、SMB beta
{recent['factor_regression']['smb_beta']:.2f}、HML beta
{recent['factor_regression']['hml_beta']:.2f}、R²
{_pct(recent['factor_regression']['r_squared'])}。負 alpha 與極低回報反駁「只是低 beta
所以看起來落後」的說法。

四路 PBO 早期 {_pct(early['pbo']['pbo'])}、近期 {_pct(recent['pbo']['pbo'])}。近期低 PBO
不是成功：它只表示四路中永久 Hi PRIOR 經常成為樣本內贏家；事前候選本身仍大幅落後。

## 48 道門檻與決策

| 門檻組 | 通過 | 判讀 |
|---|---:|---|
| repair 後數據完整性 | 10/10 | ZIP、member、精確 marker、日期、XNYS、QQQ／SPY 快照全部吻合 |
| 1963–2006 早期確認 | {early_passed}/15 | 後半、50 bps、NW t、DSR、PBO 失敗 |
| 2006–2026 近期正式 | {recent_passed}/19 | 回報、兩半、滾動窗、成本及統計均失敗 |
| 機制一致性 | {mechanism_passed}/4 | 改善跌幅，但未穩定改善回報／Sharpe |
| **總計** | **{data['passed_gate_count']}/48** | **失敗** |

結果封存，不改 20／60 日、60% 廣度、共振門檻、持倉級別、成本或時段救援。
逐股 point-in-time 數據入口仍是 **1/20**；正式短線回測 0 次、Paper 0 成交、持倉 0，
實金動作 US$0。下一個合理研究方向不是更頻密擇時，而是取得合資格逐股賬本後按凍結
v1 原樣重跑，並把日頻換手的 bid-ask spread／退出樣本真正計入。

## 可重現性與來源

- 原始日檔 SHA-256：`{data['data']['archive_sha256']}`
- 原協議 SHA-256：`{data['protocol']['original_sha256']}`
- schema repair SHA-256：`{data['protocol']['repair_sha256']}`
- 機器結果：`artifacts/short_term_daily_momentum_regime_validation.json`
- 重建：`python scripts/build_short_term_daily_momentum_regime_report.py`
- 官方方法：[French daily momentum deciles](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/Data_Library/det_10_port_form_pr_12_2_daily.html)
- 台股參考：[tst_wocker](https://github.com/appr1ciat1/tst_wocker)、[tw-block-warrant](https://github.com/appr1ciat1/tw-block-warrant)、[filter lab](https://github.com/appr1ciat1/tst_wocker_filter_lab)

歷史表現不保證未來結果；French 組合不是可買入證券，本報告不構成投資建議、Paper
成交或實金落盤指令。
"""


def main() -> int:
    data = _canonicalize(build_daily_momentum_regime_research(ROOT))
    _write_json(VALIDATION, data)
    _write_json(SITE_DATA, _site_summary(data))
    REPORT.write_text(_render_report(data), encoding="utf-8")
    print(
        json.dumps(
            {
                "status": data["status"],
                "passed_gate_count": data["passed_gate_count"],
                "required_gate_count": data["required_gate_count"],
                "report": str(REPORT.relative_to(ROOT)),
                "validation": str(VALIDATION.relative_to(ROOT)),
                "site_data": str(SITE_DATA.relative_to(ROOT)),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
