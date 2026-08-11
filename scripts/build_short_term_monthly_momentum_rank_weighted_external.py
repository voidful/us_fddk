from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from textwrap import dedent
from typing import Any

import numpy as np
import pandas as pd

from usfddk.data import load_snapshot, panel_fingerprint
from usfddk.engine import run_backtest
from usfddk.short_term_high_return import (
    _fixed_halves,
    _rolling_comparison,
    _stress_periods,
)
from usfddk.short_term_sector_etf import (
    REQUIRED_TICKERS,
    SECTOR_ARCHIVE_SHA256,
    SECTOR_ETFS,
    SECTOR_FORMAL_END,
    SECTOR_FORMAL_START,
    SECTOR_PANEL_SHA256,
    _active_comparison,
)
from usfddk.strategies import buy_and_hold_targets, fixed_weight_targets

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "docs/SHORT_TERM_MONTHLY_MOMENTUM_RANK_WEIGHTED_EXTERNAL_PROTOCOL.md"
DEFAULT_SNAPSHOT = (
    ROOT / "artifacts/snapshot_short_term_sector_vanguard_20040923_20260731_7a13b864.zip"
)
DEFAULT_RECEIPT = ROOT / "artifacts/short_term_sector_etf_data_receipt.json"
DEFAULT_OUTPUT = ROOT / "artifacts/short_term_monthly_momentum_rank_weighted_external.json"
DEFAULT_REPORT = ROOT / "docs/SHORT_TERM_MONTHLY_MOMENTUM_RANK_WEIGHTED_EXTERNAL_REPORT.md"
RANK_WEIGHTS = np.array([0.50, 0.30, 0.20], dtype=float)
COST_SCENARIOS = (10.0, 25.0, 50.0)
BASELINES = ("QQQ", "SPY", "VTI")
FIRST_HALF = ("2006-08-01", "2016-07-29")
SECOND_HALF = ("2016-08-01", "2026-07-31")


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _metrics(result: Any) -> dict[str, float]:
    return {key: float(value) for key, value in result.metrics.items()}


def _validate_inputs(snapshot: Path, receipt_path: Path):
    if snapshot.name != DEFAULT_SNAPSHOT.name:
        raise ValueError(f"只接受凍結 Vanguard 快照：{DEFAULT_SNAPSHOT.name}")
    archive_sha = _sha256_file(snapshot)
    if archive_sha != SECTOR_ARCHIVE_SHA256:
        raise ValueError(f"Vanguard 快照 hash 漂移：{archive_sha}")
    panel, manifest = load_snapshot(snapshot)
    if panel_fingerprint(panel) != SECTOR_PANEL_SHA256:
        raise ValueError("Vanguard panel fingerprint 漂移")
    if tuple(sorted(panel.close.columns)) != REQUIRED_TICKERS:
        raise ValueError("Vanguard 代號集合漂移")
    if manifest.get("end") != SECTOR_FORMAL_END:
        raise ValueError("Vanguard 資料終點漂移")
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    required_checks = {
        "status": "short_term_sector_etf_first_external_download_contract_passed",
        "pre_registration_order_proved": True,
        "calculation_started": False,
    }
    for key, expected in required_checks.items():
        if receipt.get(key) != expected:
            raise ValueError(f"Vanguard 收據 {key} 不符：{receipt.get(key)!r}")
    if not all(receipt.get("checks", {}).values()):
        raise ValueError("Vanguard 收據完整性閘門未全數通過")
    if receipt.get("snapshot", {}).get("panel_sha256") != SECTOR_PANEL_SHA256:
        raise ValueError("Vanguard 收據 panel hash 不符")
    return panel, manifest, archive_sha, receipt


def _rank_weighted_targets(panel) -> tuple[pd.DataFrame, list[dict[str, Any]]]:
    close = panel.close[list(SECTOR_ETFS)]
    momentum = close.pct_change(20, fill_method=None)
    trend = close > close.rolling(60, min_periods=60).mean()
    columns = [*SECTOR_ETFS, "SHY"]
    targets = pd.DataFrame(np.nan, index=close.index, columns=columns, dtype=float)
    schedule: list[dict[str, Any]] = []
    month_end = close.index.to_series().dt.to_period("M").ne(
        close.index.to_series().shift(-1).dt.to_period("M")
    )
    signal_dates = close.index[
        month_end.to_numpy()
        & (close.index >= pd.Timestamp(SECTOR_FORMAL_START))
        & (close.index <= pd.Timestamp(SECTOR_FORMAL_END))
    ]
    for day in signal_dates:
        eligible = list(
            close.columns[(momentum.loc[day].notna() & trend.loc[day]).to_numpy()]
        )
        selected = sorted(
            eligible,
            key=lambda ticker: (-float(momentum.loc[day, ticker]), ticker),
        )[:3]
        row = pd.Series(0.0, index=columns, dtype=float)
        used_weights = RANK_WEIGHTS[: len(selected)]
        if selected:
            row.loc[selected] = used_weights
        row.loc["SHY"] = float(1.0 - used_weights.sum())
        targets.loc[day] = row
        position = close.index.get_loc(day)
        next_session = (
            close.index[position + 1].strftime("%Y-%m-%d")
            if isinstance(position, int) and position + 1 < len(close.index)
            else None
        )
        schedule.append(
            {
                "signal_date": day.strftime("%Y-%m-%d"),
                "available_next_session": next_session,
                "eligible": eligible,
                "selected": selected,
                "weights": [float(value) for value in used_weights],
                "cash_weight": float(1.0 - used_weights.sum()),
            }
        )
    return targets, schedule


def _matched_control(targets: pd.DataFrame) -> pd.DataFrame:
    control = pd.DataFrame(np.nan, index=targets.index, columns=list(SECTOR_ETFS) + ["SHY"])
    for day in targets.index[targets["SHY"].notna()]:
        equity = float(targets.loc[day, list(SECTOR_ETFS)].sum())
        row = pd.Series(0.0, index=control.columns)
        row.loc[list(SECTOR_ETFS)] = equity / len(SECTOR_ETFS)
        row.loc["SHY"] = 1.0 - equity
        control.loc[day] = row
    return control


def _baseline_targets(panel) -> dict[str, pd.DataFrame]:
    equal = {ticker: 1.0 / len(SECTOR_ETFS) for ticker in SECTOR_ETFS}
    drift = pd.DataFrame(np.nan, index=panel.close.index, columns=list(SECTOR_ETFS) + ["SHY"])
    first = panel.close.index[panel.close.index >= pd.Timestamp(SECTOR_FORMAL_START)][0]
    drift.loc[first, list(SECTOR_ETFS)] = pd.Series(equal)
    return {
        "QQQ": buy_and_hold_targets(panel.close, "QQQ", signal_on=SECTOR_FORMAL_START),
        "SPY": buy_and_hold_targets(panel.close, "SPY", signal_on=SECTOR_FORMAL_START),
        "VTI": buy_and_hold_targets(panel.close, "VTI", signal_on=SECTOR_FORMAL_START),
        "sector_monthly_equal": fixed_weight_targets(
            panel.close,
            equal,
            signal_on=SECTOR_FORMAL_START,
        ),
        "sector_start_equal_then_drift": drift,
    }


def _run_scenario(panel, targets: pd.DataFrame, baselines: dict[str, pd.DataFrame], cost: float):
    candidate = run_backtest(
        panel,
        targets,
        name=f"rank_weighted_sector_top3_{int(cost)}bps",
        cost_bps=cost,
        start=SECTOR_FORMAL_START,
    )
    results = {
        name: run_backtest(
            panel,
            target,
            name=f"{name}_{int(cost)}bps",
            cost_bps=cost,
            start=SECTOR_FORMAL_START,
        )
        for name, target in baselines.items()
    }
    risk_free = panel.close["SHY"].pct_change(fill_method=None).reindex(candidate.returns.index)
    return {
        "strategy": _metrics(candidate),
        "baselines": {name: _metrics(result) for name, result in results.items()},
        "comparison_vs_qqq": _active_comparison(candidate, results["QQQ"], risk_free),
        "comparison_vs_matched_control": _active_comparison(
            candidate,
            results["matched_control"],
            risk_free,
        ),
        "fixed_halves_vs_qqq": _fixed_halves(candidate, results["QQQ"]),
        "rolling_three_year_vs_qqq": _rolling_comparison(
            candidate,
            results["QQQ"],
            window=756,
        ),
        "rolling_five_year_vs_qqq": _rolling_comparison(
            candidate,
            results["QQQ"],
            window=1260,
        ),
        "stress_periods": _stress_periods(
            {
                "strategy": candidate,
                "QQQ": results["QQQ"],
                "SPY": results["SPY"],
                "sector_monthly_equal": results["sector_monthly_equal"],
            }
        ),
    }


def _gates(scenarios: dict[str, Any]) -> dict[str, bool]:
    ten = scenarios["10"]
    twenty_five = scenarios["25"]
    fifty = scenarios["50"]
    first = fifty["fixed_halves_vs_qqq"]["first"]["cagr_difference"]
    second = fifty["fixed_halves_vs_qqq"]["second"]["cagr_difference"]
    comparison = ten["comparison_vs_qqq"]
    rolling = twenty_five["rolling_three_year_vs_qqq"]
    return {
        "cagr_beats_qqq_by_2pp_at_10bps": ten["strategy"]["cagr"]
        >= ten["baselines"]["QQQ"]["cagr"] + 0.02,
        "cost_50bps_beats_qqq_by_50bp": fifty["strategy"]["cagr"]
        >= fifty["baselines"]["QQQ"]["cagr"] + 0.005,
        "both_fixed_halves_beat_qqq_by_50bp": first >= 0.005 and second >= 0.005,
        "max_drawdown_not_more_than_5pp_deeper_than_qqq": ten["strategy"]["max_drawdown"]
        >= ten["baselines"]["QQQ"]["max_drawdown"] - 0.05,
        "rolling_three_year_win_fraction_at_least_60pct": rolling["cagr_win_fraction"] >= 0.60,
        "rolling_three_year_median_edge_positive": rolling["median_cagr_difference"] > 0.0,
        "beats_matched_control_cagr": ten["strategy"]["cagr"]
        > ten["baselines"]["matched_control"]["cagr"],
        "active_newey_west_t_at_least_1_96": comparison["active_newey_west"]["t_stat"] >= 1.96,
        "active_psr_at_least_95pct": comparison["active_probabilistic_sharpe"]["probability"]
        >= 0.95,
        "active_dsr_at_least_95pct": comparison["active_global_deflated_sharpe"]["probability"]
        >= 0.95,
    }


def _pct(value: float) -> str:
    return f"{value:.2%}"


def _build_report(payload: dict[str, Any]) -> str:
    ten = payload["cost_scenarios"]["10"]
    twenty_five = payload["cost_scenarios"]["25"]
    fifty = payload["cost_scenarios"]["50"]
    gates = payload["decision"]["gates"]
    first = fifty["fixed_halves_vs_qqq"]["first"]["cagr_difference"]
    second = fifty["fixed_halves_vs_qqq"]["second"]["cagr_difference"]
    return dedent(
        f"""\
        # 月度動量排名加權外部驗證報告

        版本：v1｜狀態：`{payload['status']}`｜用途：外部機制診斷，不是買入名單、Paper 指令或投資建議。

        ## 結論先行

        將現時大型股稽核中預先固定的 `rank_weighted_top3`（50%／30%／20%）原樣套用到十隻
        Vanguard 行業 ETF 後，結果未能重現；本輪不升格。

        - 10／25／50 bps 策略 CAGR 為 {_pct(ten['strategy']['cagr'])}／{_pct(twenty_five['strategy']['cagr'])}／{_pct(fifty['strategy']['cagr'])}，相應 QQQ 為 {_pct(ten['baselines']['QQQ']['cagr'])}／{_pct(twenty_five['baselines']['QQQ']['cagr'])}／{_pct(fifty['baselines']['QQQ']['cagr'])}。
        - 50 bps 前／後半段相對 QQQ CAGR 差為 {_pct(first)}／{_pct(second)}。
        - 經濟及統計閘門通過 {sum(gates.values())}/{len(gates)}；失敗結果只保留在收據與本報告。

        ## 固定規則

        | 項目 | 內容 |
        |---|---|
        | 訊號 | 月末 20-session momentum＋60-session SMA；Top-3 |
        | 權重 | 排名 50%／30%／20%；不足名額餘額持有 SHY |
        | 執行 | 下一 XNYS open；下次月末再平衡 |
        | 成本 | 單邊 10／25／50 bps |
        | 基準 | QQQ、SPY、VTI、行業等權、起點漂移及 matched control |
        | 資料 | Vanguard 2006-08-01 至 2026-07-31 凍結面板 |

        ## 全期結果

        | 成本 | 策略 CAGR | QQQ CAGR | SPY CAGR | VTI CAGR | 策略最大跌幅 | QQQ 最大跌幅 | Sharpe |
        |---:|---:|---:|---:|---:|---:|---:|---:|
        | 10 bps | {_pct(ten['strategy']['cagr'])} | {_pct(ten['baselines']['QQQ']['cagr'])} | {_pct(ten['baselines']['SPY']['cagr'])} | {_pct(ten['baselines']['VTI']['cagr'])} | {_pct(ten['strategy']['max_drawdown'])} | {_pct(ten['baselines']['QQQ']['max_drawdown'])} | {ten['strategy']['sharpe']:.2f} |
        | 25 bps | {_pct(twenty_five['strategy']['cagr'])} | {_pct(twenty_five['baselines']['QQQ']['cagr'])} | {_pct(twenty_five['baselines']['SPY']['cagr'])} | {_pct(twenty_five['baselines']['VTI']['cagr'])} | {_pct(twenty_five['strategy']['max_drawdown'])} | {_pct(twenty_five['baselines']['QQQ']['max_drawdown'])} | {twenty_five['strategy']['sharpe']:.2f} |
        | 50 bps | {_pct(fifty['strategy']['cagr'])} | {_pct(fifty['baselines']['QQQ']['cagr'])} | {_pct(fifty['baselines']['SPY']['cagr'])} | {_pct(fifty['baselines']['VTI']['cagr'])} | {_pct(fifty['strategy']['max_drawdown'])} | {_pct(fifty['baselines']['QQQ']['max_drawdown'])} | {fifty['strategy']['sharpe']:.2f} |

        ## 決策

        - `{', '.join(key for key, value in gates.items() if not value)}` 未通過。
        - 即使本輪外部 ETF 資料完整，ETF 產品驗證也不能取代個股逐期成分、退市回報及公司行動資料。
        - `paper_authorized=false`、`public_strategy_allowed=false`、實金 US$0；success-only 網頁維持「今天不下單」。

        機器收據：`artifacts/short_term_monthly_momentum_rank_weighted_external.json`；協議：`docs/SHORT_TERM_MONTHLY_MOMENTUM_RANK_WEIGHTED_EXTERNAL_PROTOCOL.md`。
        """
    )


def build_payload(snapshot: Path, receipt_path: Path) -> dict[str, Any]:
    panel, manifest, archive_sha, receipt = _validate_inputs(snapshot, receipt_path)
    targets, schedule = _rank_weighted_targets(panel)
    matched = _matched_control(targets)
    baselines = _baseline_targets(panel)
    baselines["matched_control"] = matched
    scenarios = {
        str(int(cost)): _run_scenario(panel, targets, baselines, cost)
        for cost in COST_SCENARIOS
    }
    gates = _gates(scenarios)
    return {
        "schema_version": 1,
        "status": "external_rank_weighted_momentum_validation_failed",
        "research_role": "fixed_external_mechanism_diagnostic",
        "paper_eligible": False,
        "trade_ready": False,
        "paper_authorized": False,
        "public_strategy_allowed": False,
        "real_money_action_usd": 0,
        "protocol": {
            "path": str(PROTOCOL.relative_to(ROOT)),
            "sha256": _sha256_file(PROTOCOL),
            "rank_weights": [float(value) for value in RANK_WEIGHTS],
            "cost_scenarios_bps": list(COST_SCENARIOS),
            "holding_clock": "monthly signal close; next XNYS open; next month-end rebalance",
            "baseline_symbols": list(BASELINES),
        },
        "source": {
            "snapshot_filename": snapshot.name,
            "archive_sha256": archive_sha,
            "panel_sha256": manifest["panel_sha256"],
            "manifest_start": manifest["start"],
            "manifest_end": manifest["end"],
            "formal_period": {"start": SECTOR_FORMAL_START, "end": SECTOR_FORMAL_END},
            "data_receipt_status": receipt["status"],
            "data_checks": receipt["checks"],
            "point_in_time_stock_membership": False,
            "delisted_returns_complete": False,
            "corporate_actions_complete": False,
        },
        "schedule": {
            "signals": len(schedule),
            "first_signal_date": schedule[0]["signal_date"] if schedule else None,
            "last_signal_date": schedule[-1]["signal_date"] if schedule else None,
            "selected_symbol_count": len({ticker for row in schedule for ticker in row["selected"]}),
            "rows": schedule,
        },
        "cost_scenarios": scenarios,
        "decision": {
            "strategy_status": "research_candidate_only",
            "diagnostic_status": "negative_external_replication",
            "gates": gates,
            "gate_summary": {
                "passed": sum(gates.values()),
                "total": len(gates),
                "all_passed": all(gates.values()),
            },
            "best_variant_selection_allowed": False,
            "formal_backtest_completed": False,
            "paper_authorized": False,
            "public_strategy_allowed": False,
            "real_money_action_usd": 0,
            "reason": "固定排名加權版本未能在獨立 Vanguard 行業產品面板重現；不把失敗結果帶入網站。",
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="建立月度動量排名加權外部驗證收據")
    parser.add_argument("--snapshot", type=Path, default=DEFAULT_SNAPSHOT)
    parser.add_argument("--data-receipt", type=Path, default=DEFAULT_RECEIPT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()
    payload = build_payload(args.snapshot, args.data_receipt)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(_build_report(payload), encoding="utf-8")
    print(
        json.dumps(
            {
                "status": payload["status"],
                "signals": payload["schedule"]["signals"],
                "gate_summary": payload["decision"]["gate_summary"],
                "output": str(args.output),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
