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
from usfddk.short_term_high_return import (
    _completed_period_mask,
    _moving_block_bootstrap_mean,
)
from usfddk.short_term_sector_etf import (
    REQUIRED_TICKERS,
    SECTOR_ARCHIVE_SHA256,
    SECTOR_ETFS,
    SECTOR_FORMAL_END,
    SECTOR_FORMAL_START,
    SECTOR_PANEL_SHA256,
)

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "docs/SHORT_TERM_VOLUME_BREAKOUT_EXTERNAL_PROTOCOL.md"
DEFAULT_SNAPSHOT = (
    ROOT / "artifacts/snapshot_short_term_sector_vanguard_20040923_20260731_7a13b864.zip"
)
DEFAULT_RECEIPT = ROOT / "artifacts/short_term_sector_etf_data_receipt.json"
DEFAULT_OUTPUT = ROOT / "artifacts/short_term_volume_breakout_external.json"
DEFAULT_REPORT = ROOT / "docs/SHORT_TERM_VOLUME_BREAKOUT_EXTERNAL_REPORT.md"

HORIZONS = (5, 10, 20)
COST_SCENARIOS_BPS = (10.0, 20.0, 50.0)
PRIMARY_HORIZON = 20
PRIMARY_COST_BPS = 20.0
MIN_PRICE = 5.0
MIN_MEDIAN_DOLLAR_VOLUME = 20_000_000.0
LOOKBACK = 60
MOMENTUM_WINDOW = 20
VOLUME_MULTIPLIER = 1.5
TOP_K = 10
BOOTSTRAP_SAMPLES = 2_000
BOOTSTRAP_BLOCK = 8
BOOTSTRAP_SEED = 20_260_803
FIRST_HALF_END = "2016-07-31"
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


def _validate_inputs(
    snapshot: Path,
    receipt_path: Path,
) -> tuple[Any, dict[str, Any], str, dict[str, Any]]:
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
        raise ValueError("Vanguard 外部資料收據狀態不符")
    if not receipt.get("pre_registration_order_proved"):
        raise ValueError("Vanguard 收據沒有證明資料下載前已有母協議")
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
    values = gross.to_numpy(dtype=float)
    if not np.isfinite(values).all():
        raise ValueError("固定持有期遇到缺失或非有限入場／離場價格")
    return float(gross.mean() - cost_bps / 10_000.0)


def _event_rows(panel: Any) -> list[dict[str, Any]]:
    close = panel.close
    volume = panel.volume
    sector_close = close[list(SECTOR_ETFS)]
    sector_volume = volume[list(SECTOR_ETFS)]
    momentum = sector_close.pct_change(MOMENTUM_WINDOW, fill_method=None)
    trend = sector_close > sector_close.rolling(LOOKBACK, min_periods=LOOKBACK).mean()
    prior_high = sector_close.shift(1).rolling(LOOKBACK, min_periods=LOOKBACK).max()
    median_dollar_volume = (
        sector_close.mul(sector_volume).rolling(20, min_periods=20).median()
    )
    median_volume = sector_volume.rolling(20, min_periods=20).median()
    spy_trend = close["SPY"] > close["SPY"].rolling(LOOKBACK, min_periods=LOOKBACK).mean()
    weekly_mask = _completed_period_mask(close.index, "weekly")
    signal_dates = close.index[
        weekly_mask.to_numpy()
        & (close.index >= pd.Timestamp(SECTOR_FORMAL_START))
        & (close.index <= pd.Timestamp(SECTOR_FORMAL_END))
    ]
    rows: list[dict[str, Any]] = []

    for signal_date in signal_dates:
        position = close.index.get_loc(signal_date)
        if not isinstance(position, int):
            continue
        if position + 1 >= len(close.index):
            continue
        if not bool(spy_trend.loc[signal_date]):
            continue
        base_mask = (
            momentum.loc[signal_date].notna()
            & (sector_close.loc[signal_date] > MIN_PRICE)
            & (median_dollar_volume.loc[signal_date] >= MIN_MEDIAN_DOLLAR_VOLUME)
            & trend.loc[signal_date]
            & (momentum.loc[signal_date] > 0.0)
        )
        breakout_mask = (
            base_mask
            & (sector_close.loc[signal_date] > prior_high.loc[signal_date])
            & (
                sector_volume.loc[signal_date]
                >= VOLUME_MULTIPLIER * median_volume.loc[signal_date]
            )
        )
        eligible = list(base_mask.index[base_mask])
        selected = sorted(
            list(breakout_mask.index[breakout_mask]),
            key=lambda ticker: (-float(momentum.loc[signal_date, ticker]), ticker),
        )[:TOP_K]
        if not selected:
            continue
        entry_date = close.index[position + 1]
        for horizon in HORIZONS:
            exit_position = position + 1 + horizon - 1
            if exit_position >= len(close.index):
                continue
            exit_date = close.index[exit_position]
            cost_returns: dict[str, dict[str, float]] = {}
            for cost_bps in COST_SCENARIOS_BPS:
                key = str(int(cost_bps))
                cost_returns[key] = {
                    "candidate_top10": _basket_return(
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
                    "eligible_count": len(eligible),
                    "candidate_count": len(selected),
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
                "eligible_count": row["eligible_count"],
                "candidate_count": row["candidate_count"],
                **row["cost_scenarios"][cost_key],
            }
            for row in horizon_rows
        ]
    )
    difference = frame["candidate_top10"] - frame["eligible_equal"]
    comparisons: dict[str, dict[str, Any]] = {}
    for baseline in ("eligible_equal", "all_sector_equal", *BASELINES):
        baseline_difference = frame["candidate_top10"] - frame[baseline]
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
        "mean_eligible_count": float(frame["eligible_count"].mean()),
        "mean_candidate_count": float(frame["candidate_count"].mean()),
        "net_return_summary": {
            "candidate_top10_mean": float(frame["candidate_top10"].mean()),
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
                "candidate_count": row["candidate_count"],
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
            value["mean_difference"] is not None and value["mean_difference"] > 0.0
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
                f"{_pct(summary['net_return_summary']['candidate_top10_mean'])} | "
                f"{_pct(summary['net_return_summary']['eligible_equal_mean'])} | "
                f"{_pct(summary['comparisons']['eligible_equal']['mean_difference'])} | "
                f"{_num(summary['comparisons']['eligible_equal']['newey_west']['t_stat'], 2)} |"
            )
    gate_rows = "\n".join(
        f"| {name} | {'通過' if passed else '未通過'} |" for name, passed in gates.items()
    )
    return dedent(
        f"""\
        # 成交量突破 × SPY 60-session regime：獨立 Vanguard ETF 外部診斷報告

        狀態：`{payload['status']}`。本報告是 post-hoc 機制診斷，不是個股名單、Paper 指令或投資建議。

        ## 結論先行

        固定規則在獨立 Vanguard 行業 ETF 面板產生 **{primary['events']} 宗** 20-session 完整事件；
        主要六項 gate 通過 **{sum(gates.values())}/{len(gates)}**。候選相對合資格池的平均差為
        `{_pct(primary['comparisons']['eligible_equal']['mean_difference'])}`，但勝率、統計顯著性、bootstrap
        下界及固定分段未全部通過，因此不能聲稱成交量突破個股策略已獲外部確認。

        - 20-session／20 bps 候選平均淨回報：`{_pct(primary['net_return_summary']['candidate_top10_mean'])}`；
          eligible pool：`{_pct(primary['net_return_summary']['eligible_equal_mean'])}`。
        - NW t：`{_num(primary['comparisons']['eligible_equal']['newey_west']['t_stat'], 2)}`；
          配對勝率：`{_pct(primary['comparisons']['eligible_equal']['win_fraction'])}`；
          bootstrap 95% 下界：`{_pct(primary['moving_block_bootstrap_mean_difference_vs_eligible_equal']['low'])}`。
        - ETF 代理不能替代個股 point-in-time 成分、退市回報、公司行動或 raw execution。

        ## 固定口徑

        | 項目 | 規則 |
        |---|---|
        | 訊號 | 每週最後完成 session；SPY close > 60-session SMA |
        | 篩選 | 價格 > US$5；20-session median dollar volume ≥ US$20m；20-session 回報 > 0；close > SMA60 |
        | 突破 | close > 前 60-session 最高 close；volume ≥ 1.5 × 20-session median volume |
        | 選擇 | 20-session 回報最高 Top-10 Vanguard 行業 ETF |
        | 執行 | 下一 session open；5／10／20 session close |
        | 成本 | 10／20／50 bps 敏感度；20 bps 為主要口徑 |
        | 基準 | eligible pool、全行業等權、SPY、QQQ、VTI |

        ## 事件結果

        | Horizon | 成本 | 事件 | 候選平均 | eligible 平均 | 配對差 | NW t |
        |---:|---:|---:|---:|---:|---:|---:|
        {chr(10).join(rows)}

        ## 主要 20-session／20 bps gates

        | Gate | 結果 |
        |---|---|
        {gate_rows}

        前段配對差：`{_pct(primary['fixed_halves_vs_eligible_equal']['first']['mean_difference'])}`；
        後段：`{_pct(primary['fixed_halves_vs_eligible_equal']['second']['mean_difference'])}`。

        ## 邊界

        `paper_authorized=false`、`public_strategy_allowed=false`、實金 US$0。沒有建立 strategy run、
        Paper 帳戶或個股公開名單；success-only 首頁不會讀取本收據，仍顯示「今天不下單」。本輪
        係 post-hoc external replication，不能升格為獨立首次證據。

        協議：`docs/SHORT_TERM_VOLUME_BREAKOUT_EXTERNAL_PROTOCOL.md`
        收據：`artifacts/short_term_volume_breakout_external.json`
        """
    )


def build_payload(snapshot: Path, receipt_path: Path) -> dict[str, Any]:
    panel, manifest, archive_sha, receipt = _validate_inputs(snapshot, receipt_path)
    rows = _event_rows(panel)
    horizons: dict[str, dict[str, dict[str, Any]]] = {}
    for horizon in HORIZONS:
        if not any(row["holding_sessions"] == horizon for row in rows):
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
            "external_volume_breakout_validation_passed"
            if all(gates.values())
            else "external_volume_breakout_validation_failed"
        ),
        "research_role": "post_hoc_external_volume_breakout_mechanism_diagnostic",
        "calculation_performed": True,
        "previewed_before_protocol_freeze": True,
        "paper_eligible": False,
        "trade_ready": False,
        "paper_authorized": False,
        "public_strategy_allowed": False,
        "real_money_action_usd": 0,
        "protocol": {
            "path": str(PROTOCOL.relative_to(ROOT)),
            "sha256": _sha256_file(PROTOCOL),
            "lookback_sessions": LOOKBACK,
            "momentum_window_sessions": MOMENTUM_WINDOW,
            "volume_multiplier": VOLUME_MULTIPLIER,
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
            "result_blind": False,
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
            "diagnostic_status": "post_hoc_external_replication_only",
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
            "reason": "外部 ETF 只作成交量突破機制診斷，且本輪為 post-hoc；不能替代個股 point-in-time 研究。",
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="建立成交量突破的獨立 ETF 外部診斷收據")
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
