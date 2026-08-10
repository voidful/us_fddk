"""One-shot internal runner for the frozen short-term formal study.

The runner is deliberately downstream of ``audit_formal_backtest_readiness``.
It never turns a synthetic control into a result, never writes a Paper account,
and never touches the public decision contract.  A provider run gets one
owner-only output directory; any post-start failure is preserved as an internal
failure receipt so the same input cannot be silently retried or tuned.

The current CIZ execution extension supplies benchmark raw prices and a total
return factor, but not an explicit QQQ/SPY action ledger.  Raw accounting cannot
pretend that factor is a corporate-action ledger, so a provider benchmark-action
bridge is required before a non-unit factor can be used.  This is intentional:
no attractive but economically incomplete backtest is produced.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .formal_backtest_readiness import (
    FORMAL_BASELINES,
    FORMAL_COSTS_BPS,
    FormalBacktestReadinessError,
    audit_formal_backtest_readiness,
)
from .formal_baseline_schedule import build_formal_baseline_targets
from .formal_benchmark_actions import BenchmarkActionBridge, load_benchmark_action_bridge
from .formal_execution_schedule import build_next_open_schedule, execution_schedule_frame
from .formal_performance import compare_formal_paths
from .formal_raw_accounting import run_raw_accounting
from .formal_signal_engine import build_monthly_target_weights, load_signal_inputs_from_ledger

FORMAL_BACKTEST_RUNNER_VERSION = "round23-formal-backtest-runner-v1"
_BENCHMARK_COLUMNS = (
    "asset_id",
    "session",
    "open_raw",
    "high_raw",
    "low_raw",
    "close_raw",
    "volume",
    "total_return_factor",
    "source_status",
    "source_record_id",
)
_RAW_PRICE_COLUMNS = ("security_id", "session", "open_raw", "close_raw", "source_status")
_SUPPORTED_ACTIONS = {"dividend", "split", "spinoff", "merger_cash", "merger_stock", "bankruptcy", "delisting"}
_EXIT_OUTCOMES = {"acquired_cash", "acquired_stock", "bankrupt", "delisted"}


class FormalBacktestRunnerError(ValueError):
    """Fail-closed one-shot runner error with a stable semantic code."""

    def __init__(self, code: str, detail: str):
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}")


def _fail(code: str, detail: str) -> None:
    raise FormalBacktestRunnerError(code, detail)


def _json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    path.chmod(0o600)


def _read_json(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        _fail("formal_runner_input_invalid", f"{label}: {type(exc).__name__}")
    if not isinstance(value, dict):
        _fail("formal_runner_input_invalid", f"{label} 必須是 JSON object")
    return value


def _csv(path: Path, columns: tuple[str, ...], label: str) -> pd.DataFrame:
    try:
        frame = pd.read_csv(path, dtype=str, keep_default_na=False, na_filter=False)
    except (OSError, pd.errors.ParserError) as exc:
        _fail("formal_runner_input_invalid", f"{label}: {type(exc).__name__}")
    if set(frame.columns) != set(columns):
        _fail("formal_runner_input_invalid", f"{label} 欄位集合不符")
    return frame.loc[:, list(columns)]


def _study_calendar(
    calendar: pd.DataFrame, manifest: dict[str, Any]
) -> tuple[pd.DatetimeIndex, str, str]:
    sessions = pd.to_datetime(calendar["session"], format="%Y-%m-%d", errors="coerce")
    if sessions.isna().any() or sessions.duplicated().any() or not sessions.is_monotonic_increasing:
        _fail("formal_runner_calendar_invalid", "trading_calendar 必須唯一遞增")
    if not calendar["exchange"].eq("XNYS").all():
        _fail("formal_runner_calendar_invalid", "正式研究只接受 XNYS")
    start = str(manifest.get("study_start", ""))
    end = str(manifest.get("study_end", ""))
    start_date = pd.to_datetime(start, format="%Y-%m-%d", errors="coerce")
    end_date = pd.to_datetime(end, format="%Y-%m-%d", errors="coerce")
    if pd.isna(start_date) or pd.isna(end_date) or start_date > end_date:
        _fail("formal_runner_calendar_invalid", "study_start／study_end 無效")
    selected = pd.DatetimeIndex(sessions[(sessions >= start_date) & (sessions <= end_date)])
    if len(selected) < 2:
        _fail("formal_runner_calendar_invalid", "正式研究期交易日不足")
    return selected, start, end


def _benchmark_prices(
    benchmark: pd.DataFrame,
    sessions: pd.DatetimeIndex,
    *,
    benchmark_action_ledger_bound: bool = False,
) -> pd.DataFrame:
    parsed = pd.to_datetime(benchmark["session"], format="%Y-%m-%d", errors="coerce")
    if parsed.isna().any() or benchmark[["asset_id", "session"]].duplicated().any():
        _fail("benchmark_execution_data_missing", "QQQ／SPY benchmark 日期不唯一")
    if set(benchmark["asset_id"]) != {"QQQ", "SPY"}:
        _fail("benchmark_execution_data_missing", "benchmark 必須只含 QQQ／SPY")
    expected = set(sessions)
    for asset in ("QQQ", "SPY"):
        actual = set(pd.DatetimeIndex(parsed[benchmark["asset_id"].eq(asset)]))
        if actual != expected:
            _fail("benchmark_execution_data_missing", f"{asset} 沒有完整研究期 session")
    numeric = benchmark.loc[:, ["open_raw", "close_raw", "total_return_factor"]].apply(
        pd.to_numeric, errors="coerce"
    )
    if numeric.isna().any().any() or not np.isfinite(numeric.to_numpy(dtype=float)).all():
        _fail("benchmark_execution_data_missing", "benchmark raw 價格／總回報因子無效")
    if (numeric[["open_raw", "close_raw"]] <= 0).any().any() or (numeric["total_return_factor"] <= 0).any():
        _fail("benchmark_execution_data_missing", "benchmark 價格／總回報因子必須為正")
    # The raw accounting bridge only accepts explicit action rows.  A non-unit
    # factor without such a bridge would either omit distributions or double
    # count them, so stop before a strategy run rather than silently choosing.
    if (
        not benchmark_action_ledger_bound
        and not np.isclose(numeric["total_return_factor"].to_numpy(dtype=float), 1.0).all()
    ):
        _fail(
            "benchmark_action_ledger_missing",
            "QQQ／SPY 有非 1 總回報因子，但 execution package 沒有 ETF 公司行動帳本",
        )
    return pd.DataFrame(
        {
            "security_id": benchmark["asset_id"].astype(str),
            "session": benchmark["session"].astype(str),
            "open_raw": numeric["open_raw"].astype(float),
            "close_raw": numeric["close_raw"].astype(float),
            "source_status": benchmark["source_status"].astype(str),
        }
    )


def _combine_prices(
    daily_prices: pd.DataFrame,
    benchmark: pd.DataFrame,
    sessions: pd.DatetimeIndex,
    *,
    benchmark_action_ledger_bound: bool = False,
) -> pd.DataFrame:
    stock = daily_prices.loc[:, list(_RAW_PRICE_COLUMNS)].copy()
    stock_sessions = pd.to_datetime(stock["session"], format="%Y-%m-%d", errors="coerce")
    if stock_sessions.isna().any():
        _fail("formal_runner_price_invalid", "股票價格含無效 session")
    stock = stock.loc[stock_sessions.isin(sessions)].copy()
    benchmark_raw = _benchmark_prices(
        benchmark,
        sessions,
        benchmark_action_ledger_bound=benchmark_action_ledger_bound,
    )
    frame = pd.concat([stock, benchmark_raw], ignore_index=True)
    parsed = pd.to_datetime(frame["session"], format="%Y-%m-%d", errors="coerce")
    if parsed.isna().any() or not set(parsed).issubset(set(sessions)):
        _fail("formal_runner_price_invalid", "價格含研究期外 session")
    if frame[["security_id", "session"]].duplicated().any():
        _fail("formal_runner_price_invalid", "股票與 QQQ／SPY 價格 key 重複")
    if not frame["source_status"].eq("observed").all():
        _fail("formal_runner_price_invalid", "估值只接受 observed raw price")
    return frame.sort_values(["session", "security_id"]).reset_index(drop=True)


def _event_tables(
    package: Path,
    sessions: pd.DatetimeIndex,
    benchmark_bridge: BenchmarkActionBridge | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    ledger = package / "ledger"
    execution = package / "execution"
    actions = _csv(
        ledger / "corporate_actions.csv",
        ("event_id", "security_id", "event_type", "announced_at", "ex_date", "effective_date", "cash_amount", "share_ratio", "successor_security_id", "source_record_id"),
        "corporate_actions.csv",
    )
    entitlements = _csv(
        execution / "cash_entitlements.csv",
        ("event_id", "security_id", "announced_at", "ex_date", "pay_date", "cash_available_date", "cash_per_share", "source_record_id"),
        "cash_entitlements.csv",
    )
    outcomes = _csv(
        ledger / "security_outcomes.csv",
        ("source_record_id", "security_id", "membership_effective_to", "outcome_type", "last_trade_date", "exit_effective_date", "delisting_return", "cash_consideration", "successor_security_id", "reason_code", "known_at"),
        "security_outcomes.csv",
    )
    if set(actions["event_type"]) - _SUPPORTED_ACTIONS:
        unsupported = sorted(set(actions["event_type"]) - _SUPPORTED_ACTIONS)
        _fail("formal_runner_action_unsupported", f"corporate_actions 含未實作路徑：{unsupported}")
    session_strings = {str(day.date()) for day in sessions}
    action_dates = actions["ex_date"].where(actions["ex_date"].ne(""), actions["effective_date"])
    actions = actions.loc[
        action_dates.isin(session_strings) | actions["effective_date"].isin(session_strings)
    ].copy()
    entitlements = entitlements.loc[entitlements["event_id"].isin(actions["event_id"])].copy()
    outcomes = outcomes.loc[
        outcomes["outcome_type"].isin(_EXIT_OUTCOMES)
        & outcomes["exit_effective_date"].isin(session_strings)
    ].copy()
    if benchmark_bridge is not None:
        actions = pd.concat([actions, benchmark_bridge.actions], ignore_index=True)
        entitlements = pd.concat(
            [entitlements, benchmark_bridge.entitlements], ignore_index=True
        )
        outcomes = pd.concat([outcomes, benchmark_bridge.outcomes], ignore_index=True)
    if actions["event_id"].duplicated().any() or actions["source_record_id"].duplicated().any():
        _fail("formal_runner_action_duplicate", "股票與 QQQ／SPY action ID 重複")
    if entitlements["event_id"].duplicated().any() or entitlements["source_record_id"].duplicated().any():
        _fail("formal_runner_action_duplicate", "股票與 QQQ／SPY entitlement ID 重複")
    if outcomes["source_record_id"].duplicated().any() or outcomes.duplicated(
        ["security_id", "exit_effective_date"]
    ).any():
        _fail("formal_runner_action_duplicate", "股票與 QQQ／SPY outcome ID 重複")
    return actions, entitlements, outcomes


def _write_account_files(
    directory: Path,
    path_key: str,
    account: Any,
) -> dict[str, str]:
    safe = path_key.replace("/", "_")
    files = {
        "equity_curve": f"{safe}.equity.csv",
        "trades": f"{safe}.trades.csv",
        "action_audit": f"{safe}.actions.csv",
    }
    account.equity_curve.to_csv(directory / files["equity_curve"], index=False, lineterminator="\n")
    account.trades.to_csv(directory / files["trades"], index=False, lineterminator="\n")
    account.action_audit.to_csv(directory / files["action_audit"], index=False, lineterminator="\n")
    for name in files.values():
        (directory / name).chmod(0o600)
    return files


def _run_authorized(
    *,
    root: Path,
    package: Path,
    risk_free_bundle: Path,
    readiness: dict[str, Any],
    output: Path,
    benchmark_action_bundle: str | Path | None,
) -> dict[str, Any]:
    execution_manifest = _read_json(
        package / "execution/execution_manifest.json", "execution_manifest.json"
    )
    inputs = load_signal_inputs_from_ledger(package)
    sessions, study_start, study_end = _study_calendar(
        inputs.trading_calendar, execution_manifest
    )
    if benchmark_action_bundle is None:
        _fail(
            "benchmark_action_ledger_missing",
            "provider execution package 必須另附 QQQ／SPY 公司行動 bridge",
        )
    benchmark_bridge = load_benchmark_action_bridge(
        benchmark_action_bundle,
        root=root,
        execution_manifest_path=package / "execution/execution_manifest.json",
        formal_run_id=str(readiness["run_id"]),
        study_start=study_start,
        study_end=study_end,
        sessions=sessions,
    )
    benchmark = _csv(
        package / "execution/benchmark_daily.csv",
        _BENCHMARK_COLUMNS,
        "benchmark_daily.csv",
    )
    prices = _combine_prices(
        inputs.daily_prices,
        benchmark,
        sessions,
        benchmark_action_ledger_bound=True,
    )
    actions, entitlements, outcomes = _event_tables(
        package,
        sessions,
        benchmark_bridge=benchmark_bridge,
    )
    targets, signal_audit = build_monthly_target_weights(
        inputs, start=study_start, end=study_end
    )
    baseline_set = build_formal_baseline_targets(targets, signal_audit)
    target_frames: dict[str, pd.DataFrame] = {
        "candidate": targets,
        **baseline_set.targets,
    }
    accounts_by_cost: dict[str, dict[str, Any]] = {}
    for cost_bps in FORMAL_COSTS_BPS:
        paths: dict[str, Any] = {}
        schedules: dict[str, pd.DataFrame] = {}
        for key, frame in target_frames.items():
            instructions = build_next_open_schedule(sessions, frame)
            schedules[key] = execution_schedule_frame(instructions)
            paths[key] = run_raw_accounting(
                sessions=sessions,
                prices=prices,
                instructions=instructions,
                corporate_actions=actions,
                cash_entitlements=entitlements,
                security_outcomes=outcomes,
                cost_bps=cost_bps,
            )
        rf = _csv(
            risk_free_bundle / "risk_free_daily.csv",
            ("session", "risk_free_return", "unit", "source_series", "source_record_id"),
            "risk_free_daily.csv",
        )
        comparison = compare_formal_paths(
            paths,
            candidate_key="candidate",
            baseline_keys=FORMAL_BASELINES,
            risk_free=rf,
            global_trials=int(readiness["policy"]["statistics"]["global_search_trials"]),
        )
        path_files: dict[str, dict[str, str]] = {}
        for key, account in paths.items():
            path_files[key] = _write_account_files(output, f"cost_{cost_bps}bps.{key}", account)
            schedules[key].to_csv(
                output / f"cost_{cost_bps}bps.{key}.schedule.csv",
                index=False,
                lineterminator="\n",
            )
            (output / f"cost_{cost_bps}bps.{key}.schedule.csv").chmod(0o600)
        accounts_by_cost[str(cost_bps)] = {
            "performance": comparison,
            "files": path_files,
        }
    return {
        "schema_version": 1,
        "runner_version": FORMAL_BACKTEST_RUNNER_VERSION,
        "run_id": readiness["run_id"],
        "study_start": study_start,
        "study_end": study_end,
        "signal_rows": int(len(targets)),
        "baseline_keys": list(FORMAL_BASELINES),
        "costs_bps": list(FORMAL_COSTS_BPS),
        "cost_runs": accounts_by_cost,
        "formal_stock_backtest_completed": True,
        "paper_authorized": False,
        "real_money_action_usd": 0,
        "public_promotion_allowed": False,
    }


def run_formal_backtest_once(
    package: str | Path,
    risk_free_bundle: str | Path,
    output_directory: str | Path,
    *,
    root: str | Path,
    source_mode: str = "provider",
    requirements: Any | None = None,
    expected_run_id: str | None = None,
    release_firewall: str | Path | None = None,
    benchmark_action_bundle: str | Path | None = None,
) -> dict[str, Any]:
    """Run the frozen provider study once, or fail before strategy calculation.

    Synthetic controls are audited but rejected before creating an output.  A
    provider run creates its owner-only output directory before calculating any
    signal; subsequent errors are written there as a durable internal log.
    """

    try:
        readiness = audit_formal_backtest_readiness(
            package,
            risk_free_bundle,
            output_directory,
            root=root,
            source_mode=source_mode,
            requirements=requirements,
            expected_run_id=expected_run_id,
            release_firewall=release_firewall,
        )
    except FormalBacktestReadinessError as exc:
        raise FormalBacktestRunnerError(exc.code, exc.detail) from exc
    if readiness.get("formal_stock_backtest_authorized") is not True:
        _fail(
            "formal_backtest_not_authorized",
            "正式 provider 閘門未全過；不計算訊號、不建立輸出、不建立 Paper",
        )

    output = Path(output_directory).resolve()
    try:
        output.mkdir(mode=0o700)
    except FileExistsError:
        _fail("formal_run_already_exists", "正式輸出目錄已存在；不可重跑或覆寫")
    except OSError as exc:
        _fail("formal_runner_output_invalid", f"正式輸出目錄無法建立：{type(exc).__name__}")
    if output.is_symlink() or os.stat(output).st_mode & 0o777 != 0o700:
        _fail("formal_runner_output_invalid", "正式輸出必須是 owner-only 目錄")
    _json(
        output / "run_started.json",
        {
            "runner_version": FORMAL_BACKTEST_RUNNER_VERSION,
            "run_id": readiness["run_id"],
            "status": "started",
            "formal_stock_backtest_completed": False,
            "paper_authorized": False,
            "real_money_action_usd": 0,
        },
    )
    try:
        result = _run_authorized(
            root=Path(root).resolve(),
            package=Path(package).resolve(),
            risk_free_bundle=Path(risk_free_bundle).resolve(),
            readiness=readiness,
            output=output,
            benchmark_action_bundle=benchmark_action_bundle,
        )
        _json(output / "run_summary.json", result)
        (output / "run_started.json").unlink()
        return result
    except Exception as exc:  # noqa: BLE001 - durable internal failure receipt.
        code = getattr(exc, "code", type(exc).__name__)
        detail = getattr(exc, "detail", str(exc))
        failure = {
            "runner_version": FORMAL_BACKTEST_RUNNER_VERSION,
            "run_id": readiness["run_id"],
            "status": "formal_backtest_failed_no_promotion",
            "failure_code": str(code),
            "failure_detail": str(detail),
            "formal_stock_backtest_completed": False,
            "paper_authorized": False,
            "real_money_action_usd": 0,
            "public_promotion_allowed": False,
        }
        _json(output / "run_failure.json", failure)
        raise FormalBacktestRunnerError(str(code), str(detail)) from exc
