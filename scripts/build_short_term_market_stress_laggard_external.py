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
from usfddk.metrics import newey_west_mean_test
from usfddk.short_term_high_return import _moving_block_bootstrap_mean
from usfddk.short_term_sector_etf import (
    REQUIRED_TICKERS,
    SECTOR_ARCHIVE_SHA256,
    SECTOR_ETFS,
    SECTOR_FORMAL_END,
    SECTOR_FORMAL_START,
    SECTOR_PANEL_SHA256,
)

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "docs/SHORT_TERM_MARKET_STRESS_LAGGARD_EXTERNAL_PROTOCOL.md"
DEFAULT_SNAPSHOT = (
    ROOT / "artifacts/snapshot_short_term_sector_vanguard_20040923_20260731_7a13b864.zip"
)
DEFAULT_RECEIPT = ROOT / "artifacts/short_term_sector_etf_data_receipt.json"
DEFAULT_OUTPUT = ROOT / "artifacts/short_term_market_stress_laggard_external.json"
DEFAULT_REPORT = ROOT / "docs/SHORT_TERM_MARKET_STRESS_LAGGARD_EXTERNAL_REPORT.md"

HORIZONS = (5, 10, 20)
COST_SCENARIOS_BPS = (10.0, 20.0, 50.0)
PRIMARY_HORIZON = 20
PRIMARY_COST_BPS = 20.0
MARKET_DROP_THRESHOLD = -0.015
LAGGARD_THRESHOLD = -0.05
MIN_PRICE = 5.0
MIN_MEDIAN_DOLLAR_VOLUME = 20_000_000.0
TOP_K = 5
BOOTSTRAP_SAMPLES = 2_000
BOOTSTRAP_BLOCK = 8
BOOTSTRAP_SEED = 20_260_803
FIRST_HALF_END = "2016-07-29"
SECOND_HALF_START = "2016-08-01"
BASELINES = ("SPY", "QQQ", "VTI")


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _finite(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return number if np.isfinite(number) else None


def _mean(values: pd.Series) -> float | None:
    clean = pd.to_numeric(values, errors="coerce").dropna()
    return float(clean.mean()) if not clean.empty else None


def _median(values: pd.Series) -> float | None:
    clean = pd.to_numeric(values, errors="coerce").dropna()
    return float(clean.median()) if not clean.empty else None


def _validate_inputs(snapshot: Path, receipt_path: Path) -> tuple[Any, dict[str, Any], str, dict[str, Any]]:
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
    if receipt.get("status") != "short_term_sector_etf_first_external_download_contract_passed":
        raise ValueError("Vanguard 首次外部資料收據狀態不符")
    if receipt.get("pre_registration_order_proved") is not True:
        raise ValueError("Vanguard 收據沒有證明先固定協議後下載")
    if receipt.get("calculation_started") is not False:
        raise ValueError("Vanguard 收據已標記計算開始，拒絕重用")
    if not all(receipt.get("checks", {}).values()):
        raise ValueError("Vanguard 收據完整性閘門未全數通過")
    snapshot_receipt = receipt.get("snapshot", {})
    if snapshot_receipt.get("archive_sha256") != archive_sha:
        raise ValueError("Vanguard 收據 archive hash 不符")
    if snapshot_receipt.get("panel_sha256") != SECTOR_PANEL_SHA256:
        raise ValueError("Vanguard 收據 panel hash 不符")
    if tuple(sorted(snapshot_receipt.get("tickers", []))) != REQUIRED_TICKERS:
        raise ValueError("Vanguard 收據代號集合不符")
    return panel, manifest, archive_sha, receipt


def _basket_return(
    panel: Any,
    tickers: list[str],
    *,
    entry_date: pd.Timestamp,
    exit_date: pd.Timestamp,
    cost_bps: float,
) -> float:
    entry = panel.open.loc[entry_date, tickers].astype(float)
    exit_price = panel.close.loc[exit_date, tickers].astype(float)
    gross = exit_price.div(entry).sub(1.0)
    if not np.isfinite(gross.to_numpy(dtype=float)).all():
        raise ValueError("固定持有期遇到缺失或非有限入場／離場價格")
    return float(gross.mean() - cost_bps / 10_000.0)


def _event_rows(panel: Any) -> list[dict[str, Any]]:
    close = panel.close
    sector_close = close[list(SECTOR_ETFS)]
    sector_volume = panel.volume[list(SECTOR_ETFS)]
    five_session_return = sector_close.pct_change(5, fill_method=None)
    median_dollar_volume = (
        sector_close.mul(sector_volume).rolling(20, min_periods=20).median()
    )
    market_return = close["SPY"].pct_change(fill_method=None)
    rows: list[dict[str, Any]] = []

    for signal_position, signal_date in enumerate(close.index):
        if signal_date < pd.Timestamp(SECTOR_FORMAL_START):
            continue
        if signal_date > pd.Timestamp(SECTOR_FORMAL_END):
            break
        if signal_position < 5 or signal_position + 1 >= len(close.index):
            continue
        market_move = _finite(market_return.loc[signal_date])
        if market_move is None or market_move > MARKET_DROP_THRESHOLD:
            continue

        eligible_mask = (
            five_session_return.loc[signal_date].notna()
            & (five_session_return.loc[signal_date] <= LAGGARD_THRESHOLD)
            & (sector_close.loc[signal_date] > MIN_PRICE)
            & (median_dollar_volume.loc[signal_date] >= MIN_MEDIAN_DOLLAR_VOLUME)
        )
        eligible = list(eligible_mask.index[eligible_mask])
        if len(eligible) < TOP_K:
            continue
        selected = sorted(
            eligible,
            key=lambda ticker: (float(five_session_return.loc[signal_date, ticker]), ticker),
        )[:TOP_K]
        entry_position = signal_position + 1
        entry_date = close.index[entry_position]
        for horizon in HORIZONS:
            exit_position = entry_position + horizon - 1
            if exit_position >= len(close.index):
                continue
            exit_date = close.index[exit_position]
            cost_returns: dict[str, dict[str, float]] = {}
            for cost_bps in COST_SCENARIOS_BPS:
                key = str(int(cost_bps))
                cost_returns[key] = {
                    "candidate_top5": _basket_return(
                        panel,
                        selected,
                        entry_date=entry_date,
                        exit_date=exit_date,
                        cost_bps=cost_bps,
                    ),
                    "eligible_equal": _basket_return(
                        panel,
                        eligible,
                        entry_date=entry_date,
                        exit_date=exit_date,
                        cost_bps=cost_bps,
                    ),
                    "all_sector_equal": _basket_return(
                        panel,
                        list(SECTOR_ETFS),
                        entry_date=entry_date,
                        exit_date=exit_date,
                        cost_bps=cost_bps,
                    ),
                    **{
                        ticker: _basket_return(
                            panel,
                            [ticker],
                            entry_date=entry_date,
                            exit_date=exit_date,
                            cost_bps=cost_bps,
                        )
                        for ticker in BASELINES
                    },
                }
            rows.append(
                {
                    "signal_date": pd.Timestamp(signal_date).strftime("%Y-%m-%d"),
                    "entry_date": pd.Timestamp(entry_date).strftime("%Y-%m-%d"),
                    "exit_date": pd.Timestamp(exit_date).strftime("%Y-%m-%d"),
                    "holding_sessions": horizon,
                    "market_return": market_move,
                    "eligible_count": len(eligible),
                    "selected": selected,
                    "eligible": eligible,
                    "cost_scenarios": cost_returns,
                }
            )
    return rows


def _summary(rows: list[dict[str, Any]], *, horizon: int, cost_bps: float) -> dict[str, Any]:
    horizon_rows = [row for row in rows if row["holding_sessions"] == horizon]
    cost_key = str(int(cost_bps))
    if not horizon_rows:
        raise ValueError(f"{horizon} session 沒有完整事件")
    frame = pd.DataFrame(
        [
            {
                "signal_date": row["signal_date"],
                "market_return": row["market_return"],
                "eligible_count": row["eligible_count"],
                **row["cost_scenarios"][cost_key],
            }
            for row in horizon_rows
        ]
    )
    difference = frame["candidate_top5"] - frame["eligible_equal"]
    comparisons: dict[str, dict[str, Any]] = {}
    for baseline in ("eligible_equal", "all_sector_equal", *BASELINES):
        baseline_difference = frame["candidate_top5"] - frame[baseline]
        comparisons[baseline] = {
            "mean_difference": float(baseline_difference.mean()),
            "median_difference": float(baseline_difference.median()),
            "win_fraction": float((baseline_difference > 0.0).mean()),
            "newey_west": newey_west_mean_test(
                baseline_difference,
                max_lag=5,
                periods_per_year=1,
            ),
        }

    signal_dates = pd.to_datetime(frame["signal_date"])
    halves: dict[str, dict[str, Any]] = {}
    for label, mask in (
        ("first", signal_dates <= pd.Timestamp(FIRST_HALF_END)),
        ("second", signal_dates >= pd.Timestamp(SECOND_HALF_START)),
    ):
        sample = difference.loc[mask.to_numpy()]
        halves[label] = {
            "events": int(len(sample)),
            "mean_difference": _mean(sample),
            "median_difference": _median(sample),
            "win_fraction": float((sample > 0.0).mean()) if len(sample) else None,
        }

    bootstrap = _moving_block_bootstrap_mean(
        difference,
        samples=BOOTSTRAP_SAMPLES,
        block_size=BOOTSTRAP_BLOCK,
        seed=BOOTSTRAP_SEED,
    )
    return {
        "holding_sessions": horizon,
        "cost_bps": cost_bps,
        "events": int(len(frame)),
        "first_signal_date": str(frame["signal_date"].iloc[0]),
        "last_signal_date": str(frame["signal_date"].iloc[-1]),
        "mean_market_drop": float(frame["market_return"].mean()),
        "mean_eligible_count": float(frame["eligible_count"].mean()),
        "net_return_summary": {
            "candidate_top5_mean": float(frame["candidate_top5"].mean()),
            "eligible_equal_mean": float(frame["eligible_equal"].mean()),
            "all_sector_equal_mean": float(frame["all_sector_equal"].mean()),
            **{f"{ticker}_mean": float(frame[ticker].mean()) for ticker in BASELINES},
        },
        "comparisons": comparisons,
        "fixed_halves_vs_eligible_equal": halves,
        "moving_block_bootstrap_mean_difference_vs_eligible_equal": bootstrap,
        "event_series": [
            {
                "signal_date": row["signal_date"],
                "entry_date": row["entry_date"],
                "exit_date": row["exit_date"],
                "selected": row["selected"],
                "eligible_count": row["eligible_count"],
                "market_return": row["market_return"],
                "returns": row["cost_scenarios"][cost_key],
            }
            for row in horizon_rows
        ],
    }


def _primary_gates(summary: dict[str, Any]) -> dict[str, bool]:
    comparison = summary["comparisons"]["eligible_equal"]
    bootstrap = summary["moving_block_bootstrap_mean_difference_vs_eligible_equal"]
    halves = summary["fixed_halves_vs_eligible_equal"]
    return {
        "at_least_30_complete_events": summary["events"] >= 30,
        "mean_difference_positive": comparison["mean_difference"] > 0.0,
        "newey_west_t_at_least_1_96": comparison["newey_west"]["t_stat"] >= 1.96,
        "bootstrap_95pct_low_positive": bootstrap["low"] > 0.0,
        "paired_win_fraction_above_50pct": comparison["win_fraction"] > 0.50,
        "both_fixed_halves_positive": all(
            (value["mean_difference"] is not None and value["mean_difference"] > 0.0)
            for value in halves.values()
        ),
    }


def _pct(value: Any, digits: int = 2) -> str:
    number = _finite(value)
    return "—" if number is None else f"{number:.{digits}%}"


def _num(value: Any, digits: int = 3) -> str:
    number = _finite(value)
    return "—" if number is None else f"{number:.{digits}f}"


def _build_report(payload: dict[str, Any]) -> str:
    primary = payload["horizons"][str(PRIMARY_HORIZON)][str(int(PRIMARY_COST_BPS))]
    gates = payload["decision"]["gates"]
    rows = []
    for horizon in HORIZONS:
        for cost in COST_SCENARIOS_BPS:
            summary = payload["horizons"][str(horizon)][str(int(cost))]
            rows.append(
                f"| {horizon} | {int(cost)} | {summary['events']} | "
                f"{_pct(summary['net_return_summary']['candidate_top5_mean'])} | "
                f"{_pct(summary['net_return_summary']['eligible_equal_mean'])} | "
                f"{_pct(summary['comparisons']['eligible_equal']['mean_difference'])} | "
                f"{_num(summary['comparisons']['eligible_equal']['newey_west']['t_stat'], 2)} |"
            )
    gate_rows = "\n".join(
        f"| {name} | {'通過' if passed else '未通過'} |" for name, passed in gates.items()
    )
    return dedent(
        f"""\
        # 市場急跌落後反轉：獨立 Vanguard 行業 ETF 外部驗證報告

        狀態：`{payload['status']}`。本報告是機制診斷，不是個股名單、Paper 指令或投資建議。

        ## 結論先行

        固定規則在獨立 Vanguard 行業 ETF 面板只產生 **{primary['events']} 宗** 20-session 完整事件，低於事前要求的 30 宗；主要 6 項 gate 通過 **{sum(gates.values())}/{len(gates)}**。因此不能聲稱短線個股策略已獲外部確認，結果只留在研究 log。

        - 20-session、20 bps 候選 Top-5 平均淨回報：`{_pct(primary['net_return_summary']['candidate_top5_mean'])}`；合資格池：`{_pct(primary['net_return_summary']['eligible_equal_mean'])}`。
        - 配對平均差：`{_pct(primary['comparisons']['eligible_equal']['mean_difference'])}`；NW t：`{_num(primary['comparisons']['eligible_equal']['newey_west']['t_stat'], 2)}`；配對勝率：`{_pct(primary['comparisons']['eligible_equal']['win_fraction'])}`。
        - ETF 代理不能取代個股 point-in-time 成分、退市回報、公司行動及真實成交時間。

        ## 固定口徑

        | 項目 | 規則 |
        |---|---|
        | 訊號 | SPY 單日跌至少 1.5%；標的五日跌至少 5% |
        | 篩選 | 價格 > US$5；20-session median dollar volume ≥ US$20m |
        | 選擇 | 最弱 Top-5 Vanguard 行業 ETF |
        | 執行 | 下一 session open 進場；5／10／20 session close 離場 |
        | 成本 | 10／20／50 bps 敏感度；20 bps 為主要口徑 |
        | 基準 | 合資格池、全行業等權、SPY、QQQ、VTI |

        ## 事件結果

        | Horizon | 成本 | 事件 | 候選平均 | 合資格池平均 | 配對差 | NW t |
        |---:|---:|---:|---:|---:|---:|---:|
        {chr(10).join(rows)}

        ## 主要 20-session／20 bps gates

        | Gate | 結果 |
        |---|---|
        {gate_rows}

        前段配對差：`{_pct(primary['fixed_halves_vs_eligible_equal']['first']['mean_difference'])}`；後段：`{_pct(primary['fixed_halves_vs_eligible_equal']['second']['mean_difference'])}`；bootstrap 95% 下界：`{_pct(primary['moving_block_bootstrap_mean_difference_vs_eligible_equal']['low'])}`。

        ## 邊界

        `paper_authorized=false`、`public_strategy_allowed=false`、實金 US$0。沒有建立 strategy run、Paper 帳戶或個股公開名單；success-only 首頁不會讀取本收據，仍顯示「今天不下單」。

        協議：`docs/SHORT_TERM_MARKET_STRESS_LAGGARD_EXTERNAL_PROTOCOL.md`
        收據：`artifacts/short_term_market_stress_laggard_external.json`
        """
    )


def build_payload(snapshot: Path, receipt_path: Path) -> dict[str, Any]:
    panel, manifest, archive_sha, receipt = _validate_inputs(snapshot, receipt_path)
    rows = _event_rows(panel)
    horizons: dict[str, dict[str, dict[str, Any]]] = {}
    for horizon in HORIZONS:
        horizon_rows = [row for row in rows if row["holding_sessions"] == horizon]
        if not horizon_rows:
            raise ValueError(f"{horizon} session 沒有完整事件")
        horizons[str(horizon)] = {
            str(int(cost)): _summary(rows, horizon=horizon, cost_bps=cost)
            for cost in COST_SCENARIOS_BPS
        }
    primary = horizons[str(PRIMARY_HORIZON)][str(int(PRIMARY_COST_BPS))]
    gates = _primary_gates(primary)
    return {
        "schema_version": 1,
        "status": (
            "external_market_stress_laggard_validation_passed"
            if all(gates.values())
            else "external_market_stress_laggard_validation_failed"
        ),
        "research_role": "fixed_external_market_stress_mechanism_diagnostic",
        "calculation_performed": True,
        "paper_eligible": False,
        "trade_ready": False,
        "paper_authorized": False,
        "public_strategy_allowed": False,
        "real_money_action_usd": 0,
        "protocol": {
            "path": str(PROTOCOL.relative_to(ROOT)),
            "sha256": _sha256_file(PROTOCOL),
            "market_drop_threshold": MARKET_DROP_THRESHOLD,
            "laggard_threshold": LAGGARD_THRESHOLD,
            "min_price": MIN_PRICE,
            "min_median_dollar_volume": MIN_MEDIAN_DOLLAR_VOLUME,
            "top_k": TOP_K,
            "horizons": list(HORIZONS),
            "cost_scenarios_bps": list(COST_SCENARIOS_BPS),
            "primary_horizon": PRIMARY_HORIZON,
            "primary_cost_bps": PRIMARY_COST_BPS,
            "bootstrap_samples": BOOTSTRAP_SAMPLES,
            "bootstrap_block": BOOTSTRAP_BLOCK,
            "bootstrap_seed": BOOTSTRAP_SEED,
        },
        "source": {
            "snapshot_filename": snapshot.name,
            "archive_sha256": archive_sha,
            "panel_sha256": manifest["panel_sha256"],
            "manifest_start": manifest["start"],
            "manifest_end": manifest["end"],
            "formal_period": {"start": SECTOR_FORMAL_START, "end": SECTOR_FORMAL_END},
            "tickers": list(SECTOR_ETFS),
            "baseline_tickers": list(BASELINES),
            "data_receipt_status": receipt["status"],
            "data_checks": receipt["checks"],
            "point_in_time_stock_membership": False,
            "delisted_returns_complete": False,
            "corporate_actions_complete": False,
        },
        "schedule": {
            "raw_event_rows": len(rows),
            "complete_events_by_horizon": {
                str(horizon): sum(row["holding_sessions"] == horizon for row in rows)
                for horizon in HORIZONS
            },
            "first_signal_date": rows[0]["signal_date"] if rows else None,
            "last_signal_date": rows[-1]["signal_date"] if rows else None,
        },
        "horizons": horizons,
        "decision": {
            "strategy_status": "research_candidate_only",
            "diagnostic_status": "positive_or_negative_external_replication_only",
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
            "reason": "ETF 外部面板只作機制驗證；不能替代個股 point-in-time 研究，因此不升格網站或 Paper。",
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="建立市場急跌落後反轉的獨立 ETF 外部驗證收據")
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
                "events": payload["schedule"]["complete_events_by_horizon"],
                "gate_summary": payload["decision"]["gate_summary"],
                "output": str(args.output),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
