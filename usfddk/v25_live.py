from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

from usfddk.data import (
    fetch_yfinance,
    load_snapshot,
    most_recent_us_session,
    panel_fingerprint,
    save_snapshot,
    validate_panel,
)
from usfddk.growth_gold_diversification import (
    V25_PRODUCT_MAPPING_SHA256,
    V25_PROTOCOL_SHA256,
    v25_forward_paper_evidence,
    v25_paper_fill_counts,
)
from usfddk.models import MarketPanel
from usfddk.paper import (
    build_paper_report,
    load_paper_state,
    paper_metrics,
    update_paper_state,
    write_paper_state,
)
from usfddk.strategies import buy_and_hold_targets, fixed_weight_targets

V25_LIVE_TICKERS = ("GLD", "SHY", "SPY", "VUG")
V25_LIVE_FETCH_START = "2026-07-01"
V25_LIVE_STATUS_SCHEMA_VERSION = 1
V25_LIVE_AUDIT_SCHEMA_VERSION = 1
V25_LIVE_LEDGER_SCHEMA_VERSION = 1


def _sha256_file(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _canonical_sha256(value: Any) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def write_json_atomic(path: str | Path, payload: dict[str, Any]) -> Path:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(f".{destination.name}.tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False),
        encoding="utf-8",
    )
    temporary.replace(destination)
    return destination


def _paper_performance_state(state: dict[str, Any]) -> dict[str, Any]:
    """Retain every economic field while excluding wall-clock-only metadata."""
    return {
        key: state.get(key)
        for key in (
            "schema_version",
            "mode",
            "strategy",
            "execution_clock",
            "initial_cash",
            "cash",
            "cost_bps",
            "started_at",
            "as_of",
            "holdings",
            "pending_order",
            "order_history",
            "transactions",
            "equity_curve",
            "adjustment_rebases",
            "total_costs",
        )
    }


def _strategy_targets(
    close: pd.DataFrame,
    strategy_key: str,
    *,
    signal_on: str | None,
) -> tuple[str, pd.DataFrame]:
    if strategy_key == "v25":
        return "v25 80% VUG／20% GLD（隔離候選 Paper）", fixed_weight_targets(
            close,
            {"VUG": 0.80, "GLD": 0.20},
            signal_on=signal_on,
        )
    if strategy_key == "v25_spy":
        return "v25 SPY 基準（隔離 Paper）", buy_and_hold_targets(
            close,
            "SPY",
            signal_on=signal_on or close.index[-1].strftime("%Y-%m-%d"),
        )
    if strategy_key == "v25_matched":
        return "v25 公平基準 80% VUG／20% SHY（隔離 Paper）", fixed_weight_targets(
            close,
            {"VUG": 0.80, "SHY": 0.20},
            signal_on=signal_on,
        )
    raise ValueError(f"不支援的 v25 LIVE 策略：{strategy_key}")


def _load_or_fetch_live_panel(
    *,
    snapshot: str | Path | None,
    fetch_start: str,
    end: str | None,
    as_of: str | datetime | pd.Timestamp | None,
    output_dir: str | Path,
) -> tuple[MarketPanel, dict[str, Any], Path, pd.Timestamp]:
    observation_time = pd.Timestamp(as_of) if as_of is not None else pd.Timestamp.now(tz="UTC")
    expected_session = most_recent_us_session(observation_time)
    if snapshot is not None:
        snapshot_path = Path(snapshot).resolve()
        panel, manifest = load_snapshot(snapshot_path)
    else:
        requested_end = end or expected_session.strftime("%Y-%m-%d")
        panel = fetch_yfinance(
            V25_LIVE_TICKERS,
            fetch_start,
            requested_end,
            threads=False,
        )
        fingerprint = panel_fingerprint(panel)
        snapshot_path = (
            Path(output_dir).resolve()
            / f"snapshot_v25_live_{panel.end.strftime('%Y%m%d')}_{fingerprint[:8]}.zip"
        )
        if snapshot_path.exists():
            frozen, manifest = load_snapshot(snapshot_path)
            if panel_fingerprint(frozen) != fingerprint:
                raise RuntimeError("v25 LIVE 快照短雜湊碰撞，拒絕覆寫既有檔案")
            panel = frozen
        else:
            manifest = {}

    contract = validate_panel(
        panel,
        as_of=observation_time,
        required=V25_LIVE_TICKERS,
        min_last_coverage=1.0,
        min_history_coverage=0.999,
        require_fresh=True,
    )
    contract.require()
    if not manifest:
        manifest = save_snapshot(panel, snapshot_path, contract=contract)
    actual_fingerprint = panel_fingerprint(panel)
    if manifest.get("panel_sha256") != actual_fingerprint:
        raise ValueError("v25 LIVE 快照面板與 manifest 雜湊不同")
    return panel, manifest, snapshot_path, expected_session


def run_v25_live_update(
    *,
    snapshot: str | Path | None = None,
    fetch_start: str = V25_LIVE_FETCH_START,
    end: str | None = None,
    as_of: str | datetime | pd.Timestamp | None = None,
    output_dir: str | Path = "artifacts",
    eligibility_receipt: str | Path = ("artifacts/v25_growth_gold_diversification_validation.json"),
    candidate_state_path: str | Path = "artifacts/paper_v25_state.json",
    spy_state_path: str | Path = "artifacts/paper_v25_spy_state.json",
    matched_state_path: str | Path = "artifacts/paper_v25_matched_state.json",
    evidence_path: str | Path = "artifacts/v25_forward_paper_evidence.json",
    status_path: str | Path = "artifacts/v25_live_update_status.json",
    initial_cash: float = 100_000.0,
    cost_bps: float = 10.0,
) -> dict[str, Any]:
    """Fetch one completed session and advance all v25 accounts in lockstep."""
    panel, manifest, resolved_snapshot, expected_session = _load_or_fetch_live_panel(
        snapshot=snapshot,
        fetch_start=fetch_start,
        end=end,
        as_of=as_of,
        output_dir=output_dir,
    )
    eligibility = json.loads(Path(eligibility_receipt).read_text(encoding="utf-8"))
    if eligibility.get("protocol", {}).get("sha256") != V25_PROTOCOL_SHA256:
        raise ValueError("v25 LIVE 更新的歷史入口協議雜湊不符")
    if eligibility.get("protocol", {}).get("product_mapping_sha256") != V25_PRODUCT_MAPPING_SHA256:
        raise ValueError("v25 LIVE 更新的產品映射雜湊不符")
    if not bool(
        eligibility.get("paper_eligible")
        and eligibility.get("all_paths_passed")
        and eligibility.get("data_passed_gate_count") == eligibility.get("data_required_gate_count")
    ):
        raise ValueError("v25 歷史產品入口未通過，拒絕推進 LIVE Paper")

    archive_sha256 = _sha256_file(resolved_snapshot)
    configurations = {
        "candidate": ("v25", Path(candidate_state_path).resolve()),
        "SPY": ("v25_spy", Path(spy_state_path).resolve()),
        "matched": ("v25_matched", Path(matched_state_path).resolve()),
    }
    existing_states = {
        label: load_paper_state(path) if path.exists() else None
        for label, (_, path) in configurations.items()
    }
    existing_presence = [state is not None for state in existing_states.values()]
    if any(existing_presence) and not all(existing_presence):
        raise ValueError("v25 LIVE 三帳戶只有部分存在，拒絕自動補建")
    existing_dates = {
        str(state.get("as_of")) for state in existing_states.values() if state is not None
    }
    if len(existing_dates) > 1:
        raise ValueError("v25 LIVE 三帳戶更新前日期已不同步，拒絕繼續")
    previous_data_through = next(iter(existing_dates), None)
    before_hashes = {
        label: _canonical_sha256(_paper_performance_state(state))
        for label, state in existing_states.items()
        if state is not None
    }

    staged: dict[str, tuple[dict[str, Any], Path, str]] = {}
    for label, (strategy_key, state_path) in configurations.items():
        existing = deepcopy(existing_states[label])
        strategy_name, targets = _strategy_targets(
            panel.close,
            strategy_key,
            signal_on=str(existing["started_at"]) if existing is not None else None,
        )
        state = update_paper_state(
            panel,
            targets,
            state=existing,
            initial_cash=initial_cash,
            cost_bps=cost_bps,
            snapshot_sha256=archive_sha256,
            strategy_name=strategy_name,
        )
        staged[label] = (state, state_path, strategy_key)

    starts = {str(item[0].get("started_at")) for item in staged.values()}
    as_of_dates = {str(item[0].get("as_of")) for item in staged.values()}
    snapshot_hashes = {str(item[0].get("snapshot_sha256")) for item in staged.values()}
    if len(starts) != 1 or len(as_of_dates) != 1 or len(snapshot_hashes) != 1:
        raise RuntimeError("v25 LIVE 三帳戶起點、進度或快照不同步，拒絕寫入")
    data_through = next(iter(as_of_dates))
    if data_through != panel.end.strftime("%Y-%m-%d"):
        raise RuntimeError("v25 LIVE 帳戶沒有完整推進到行情截止日")

    proposed_evidence = v25_forward_paper_evidence(
        staged["candidate"][0],
        staged["SPY"][0],
        staged["matched"][0],
    )
    if not all(
        proposed_evidence["gates"][key]
        for key in (
            "all_accounts_live_and_same_start",
            "all_accounts_same_as_of",
            "all_accounts_same_snapshot",
            "all_accounts_same_cost_and_cash",
            "all_accounts_same_session_path",
            "all_accounts_same_execution_clock",
            "all_accounts_same_order_path",
            "all_accounts_same_fill_counts",
            "zero_integrity_violations",
        )
    ):
        raise RuntimeError("v25 LIVE 同步完整性門檻未通過")

    after_hashes = {
        label: _canonical_sha256(_paper_performance_state(item[0]))
        for label, item in staged.items()
    }
    data_advanced = previous_data_through is None or data_through > previous_data_through
    changed_without_new_session = bool(
        previous_data_through is not None and not data_advanced and before_hashes != after_hashes
    )
    state_write_applied = data_advanced
    if state_write_applied:
        authoritative = staged
        evidence = proposed_evidence
        for state, state_path, _ in authoritative.values():
            write_paper_state(state_path, state)
        for state, state_path, strategy_key in authoritative.values():
            build_paper_report(
                state_path.with_name(f"paper_{strategy_key}.html"),
                state=state,
                panel=panel,
            )
        write_json_atomic(evidence_path, evidence)
    else:
        authoritative = {
            label: (existing_states[label], state_path, strategy_key)
            for label, (strategy_key, state_path) in configurations.items()
        }
        if any(item[0] is None for item in authoritative.values()):
            raise RuntimeError("v25 LIVE 冪等更新缺少既有帳戶")
        evidence = v25_forward_paper_evidence(
            authoritative["candidate"][0],
            authoritative["SPY"][0],
            authoritative["matched"][0],
        )
    authoritative_hashes = {
        label: _canonical_sha256(_paper_performance_state(item[0]))
        for label, item in authoritative.items()
    }
    status = {
        "schema_version": V25_LIVE_STATUS_SCHEMA_VERSION,
        "generated_at_utc": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "previous_data_through": previous_data_through,
        "data_through": data_through,
        "expected_session": expected_session.strftime("%Y-%m-%d"),
        "data_advanced": data_advanced,
        "idempotent_no_new_session": not data_advanced and not changed_without_new_session,
        "state_changed_without_new_session": changed_without_new_session,
        "manual_review_required": changed_without_new_session,
        "state_write_applied": state_write_applied,
        "site_rebuild_required": data_advanced,
        "private_deploy_candidate": data_advanced and not changed_without_new_session,
        "reference_trade_allowed": bool(evidence["live_confirmed"]),
        "snapshot": {
            "path": str(resolved_snapshot),
            "panel_sha256": str(manifest["panel_sha256"]),
            "archive_sha256": archive_sha256,
            "rows": int(manifest["rows"]),
            "start": str(manifest["start"]),
            "end": str(manifest["end"]),
            "tickers": list(manifest["tickers"]),
            "contract": manifest.get("contract"),
        },
        "accounts": {
            label: {
                "as_of": state["as_of"],
                "started_at": state["started_at"],
                "mode": state["mode"],
                "transactions": len(state.get("transactions", [])),
                "snapshot_sha256": state.get("snapshot_sha256"),
                "performance_state_sha256": authoritative_hashes[label],
                "proposed_performance_state_sha256": after_hashes[label],
            }
            for label, (state, _, _) in authoritative.items()
        },
        "forward_evidence": evidence,
        "decision": (
            "manual_review"
            if changed_without_new_session
            else "rebuild_and_audit"
            if data_advanced
            else "no_new_session_no_deploy"
        ),
    }
    write_json_atomic(status_path, status)
    return status


def _weights_close(
    left: dict[str, Any],
    right: dict[str, Any],
    *,
    tolerance: float = 1e-8,
) -> bool:
    keys = set(left) | set(right)
    return all(
        abs(float(left.get(key, 0.0)) - float(right.get(key, 0.0))) <= tolerance for key in keys
    )


def _numbers_close(left: Any, right: Any, *, tolerance: float = 1e-8) -> bool:
    try:
        left_value = float(left)
        right_value = float(right)
    except (TypeError, ValueError):
        return False
    return abs(left_value - right_value) <= tolerance * max(abs(right_value), 1.0)


def audit_v25_live_reference(
    site_payload: dict[str, Any],
    candidate_state: dict[str, Any],
    spy_state: dict[str, Any],
    matched_state: dict[str, Any],
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Cross-check the deployed v25 Paper view against all authoritative states."""
    checked_at = now or datetime.now(UTC)
    if checked_at.tzinfo is None:
        checked_at = checked_at.replace(tzinfo=UTC)
    errors: list[str] = []
    due_text = str(site_payload.get("freshness", {}).get("refresh_due_at_utc", ""))
    try:
        due = datetime.fromisoformat(due_text.replace("Z", "+00:00"))
        if due.tzinfo is None:
            raise ValueError
    except ValueError:
        due = checked_at
        errors.append("網站資料缺少有效的更新截止時間")

    v25 = site_payload.get("research_pipeline", {}).get("growth_gold_diversification", {})
    site_paper = v25.get("paper")
    if site_payload.get("schema_version") != 1:
        errors.append("網站資料 schema 不支援")
    if not isinstance(site_paper, dict):
        errors.append("網站缺少 v25 Paper 狀態")
        site_paper = {}
    states = {
        "candidate": candidate_state,
        "SPY": spy_state,
        "matched": matched_state,
    }
    for label, state in states.items():
        if state.get("mode") != "live":
            errors.append(f"v25 {label} 不是 LIVE Paper")
    try:
        forward = v25_forward_paper_evidence(
            candidate_state,
            spy_state,
            matched_state,
        )
    except (KeyError, TypeError, ValueError) as exc:
        forward = None
        errors.append(f"v25 三帳戶證據無效：{exc}")

    if str(site_payload.get("data_through")) != str(candidate_state.get("as_of")):
        errors.append("網站資料截止日與 v25 Paper 進度不同")
    for label, state in states.items():
        if str(state.get("as_of")) != str(candidate_state.get("as_of")):
            errors.append(f"v25 {label} 與候選帳戶日期不同")
    if str(site_paper.get("as_of")) != str(candidate_state.get("as_of")):
        errors.append("網站 v25 Paper 日期與候選帳戶不同")
    if str(site_paper.get("started_at")) != str(candidate_state.get("started_at")):
        errors.append("網站 v25 Paper 起點與候選帳戶不同")
    if str(site_paper.get("snapshot_sha256")) != str(candidate_state.get("snapshot_sha256")):
        errors.append("網站 v25 Paper 與候選帳戶快照不同")
    for field in ("initial_cash", "cost_bps", "total_costs"):
        if not _numbers_close(site_paper.get(field), candidate_state.get(field, 0.0)):
            errors.append(f"網站 v25 Paper {field} 與候選帳戶不同")
    if str(site_paper.get("execution_clock")) != str(candidate_state.get("execution_clock")):
        errors.append("網站 v25 Paper 成交時鐘與候選帳戶不同")

    candidate_metrics = paper_metrics(candidate_state)
    for field in ("equity", "return"):
        try:
            actual = float(site_paper[field])
        except (KeyError, TypeError, ValueError):
            errors.append(f"網站 v25 Paper 缺少有效的 {field}")
            continue
        expected = float(candidate_metrics[field])
        if abs(actual - expected) > 1e-8 * max(abs(expected), 1.0):
            errors.append(f"網站 v25 Paper {field} 與候選帳戶不同")
    try:
        site_cash = float(site_paper["cash"])
    except (KeyError, TypeError, ValueError):
        errors.append("網站 v25 Paper 缺少有效的 cash")
    else:
        if abs(site_cash - float(candidate_state["cash"])) > 1e-8 * max(
            abs(float(candidate_state["cash"])), 1.0
        ):
            errors.append("網站 v25 Paper cash 與候選帳戶不同")
    if int(site_paper.get("transactions", -1)) != len(candidate_state.get("transactions", [])):
        errors.append("網站 v25 Paper 成交筆數與候選帳戶不同")

    pending = candidate_state.get("pending_order")
    site_pending = site_paper.get("pending_order")
    if bool(pending) != bool(site_pending):
        errors.append("網站 v25 待成交狀態與候選帳戶不同")
    if (
        pending
        and site_pending
        and not _weights_close(
            pending.get("target_weights", {}),
            site_pending.get("target_weights", {}),
        )
    ):
        errors.append("網站 v25 待成交權重與候選帳戶不同")
    if pending and site_pending:
        for field in ("signal_date", "execute_after", "status"):
            if str(site_pending.get(field)) != str(pending.get(field)):
                errors.append(f"網站 v25 待成交 {field} 與候選帳戶不同")
    expected_holdings = {
        ticker: float(position["market_value"]) / max(float(candidate_metrics["equity"]), 1e-12)
        for ticker, position in candidate_state.get("holdings", {}).items()
    }
    site_holdings = {
        ticker: float(position.get("weight", 0.0))
        for ticker, position in site_paper.get("holdings", {}).items()
    }
    if not _weights_close(expected_holdings, site_holdings):
        errors.append("網站 v25 持倉權重與候選帳戶不同")
    if site_paper.get("recent_transactions") != candidate_state.get("transactions", [])[-20:]:
        errors.append("網站 v25 最近成交紀錄與候選帳戶不同")
    if site_paper.get("recent_filled_orders") != candidate_state.get("order_history", [])[-12:]:
        errors.append("網站 v25 最近再平衡紀錄與候選帳戶不同")

    site_accounts = site_paper.get("accounts", {})
    account_states = {
        "candidate": candidate_state,
        "SPY": spy_state,
        "matched_80_VUG_20_SHY": matched_state,
    }
    if not isinstance(site_accounts, dict):
        errors.append("網站缺少 v25 三帳戶比較資料")
        site_accounts = {}
    for label, state in account_states.items():
        site_account = site_accounts.get(label)
        if not isinstance(site_account, dict):
            errors.append(f"網站缺少 v25 {label} 比較帳戶")
            continue
        metrics = paper_metrics(state)
        if str(site_account.get("as_of")) != str(state.get("as_of")):
            errors.append(f"網站 v25 {label} 比較帳戶日期不同")
        for field, expected in (
            ("equity", metrics["equity"]),
            ("return", metrics["return"]),
            ("max_drawdown", metrics["max_drawdown"]),
            ("cash", state.get("cash")),
            ("total_costs", state.get("total_costs", 0.0)),
        ):
            if not _numbers_close(site_account.get(field), expected):
                errors.append(f"網站 v25 {label} 比較帳戶 {field} 不同")
        expected_fills = v25_paper_fill_counts(state)["completed_rebalances"]
        if int(site_account.get("transactions", -1)) != len(state.get("transactions", [])):
            errors.append(f"網站 v25 {label} 比較帳戶成交筆數不同")
        if int(site_account.get("filled_rebalances", -1)) != int(expected_fills):
            errors.append(f"網站 v25 {label} 比較帳戶再平衡次數不同")
        site_curve = site_account.get("equity_curve")
        expected_curve = state.get("equity_curve", [])
        if not isinstance(site_curve, list) or len(site_curve) != len(expected_curve):
            errors.append(f"網站 v25 {label} 比較帳戶權益序列長度不同")
            continue
        for position, (site_point, expected_point) in enumerate(
            zip(site_curve, expected_curve, strict=True)
        ):
            if str(site_point.get("date")) != str(expected_point.get("date")):
                errors.append(f"網站 v25 {label} 比較帳戶第 {position + 1} 筆日期不同")
                break
            if not _numbers_close(
                site_point.get("equity"), expected_point.get("equity")
            ) or not _numbers_close(site_point.get("drawdown"), expected_point.get("drawdown")):
                errors.append(f"網站 v25 {label} 比較帳戶第 {position + 1} 筆權益不同")
                break

    expected_trade_ready = False
    if forward is not None:
        site_forward = site_paper.get("forward_evidence", {})
        for field in (
            "forward_sessions",
            "filled_rebalances",
            "remaining_sessions",
            "remaining_filled_rebalances",
            "integrity_violations",
            "promotion_protocol",
            "promotion_protocol_sha256",
            "filled_orders_including_initial_allocation",
            "initial_allocations",
            "account_fill_counts",
            "forward_diagnostics",
            "live_confirmed",
            "gates",
        ):
            if site_forward.get(field) != forward.get(field):
                errors.append(f"網站 v25 前瞻證據 {field} 與三帳戶不同")
        identity_gates = (
            "all_accounts_live_and_same_start",
            "all_accounts_same_as_of",
            "all_accounts_same_snapshot",
            "all_accounts_same_cost_and_cash",
            "all_accounts_same_session_path",
            "all_accounts_same_execution_clock",
            "all_accounts_same_order_path",
            "all_accounts_same_fill_counts",
            "zero_integrity_violations",
        )
        for gate in identity_gates:
            if not bool(forward["gates"].get(gate)):
                errors.append(f"v25 LIVE 同步門檻失敗：{gate}")
        expected_trade_ready = bool(
            v25.get("paper_eligible") and v25.get("all_paths_passed") and forward["live_confirmed"]
        )
    if bool(v25.get("trade_ready")) != expected_trade_ready:
        errors.append("網站 v25 trade_ready 與前瞻門檻不同")
    if bool(v25.get("real_money_signal_display_allowed")) != expected_trade_ready:
        errors.append("網站 v25 實金訊號顯示權限與前瞻門檻不同")
    expected_paper_display = bool(v25.get("paper_eligible") and site_paper)
    if bool(v25.get("paper_signal_display_allowed")) != expected_paper_display:
        errors.append("網站 v25 Paper 訊號顯示權限與歷史入口不同")

    stale = checked_at > due
    integrity_ok = not errors and not stale
    reference_trade_allowed = bool(integrity_ok and expected_trade_ready)
    return {
        "schema_version": V25_LIVE_AUDIT_SCHEMA_VERSION,
        "ok": integrity_ok,
        "integrity_ok": integrity_ok,
        "safe_to_publish_paper_status": integrity_ok,
        "status": "invalid" if errors else "stale" if stale else "fresh",
        "checked_at_utc": checked_at.astimezone(UTC).isoformat().replace("+00:00", "Z"),
        "refresh_due_at_utc": due_text,
        "data_through": site_payload.get("data_through"),
        "paper_as_of": candidate_state.get("as_of"),
        "snapshot_sha256": candidate_state.get("snapshot_sha256"),
        "paper_eligible": bool(v25.get("paper_eligible")),
        "all_paths_passed": bool(v25.get("all_paths_passed")),
        "forward_sessions": (int(forward["forward_sessions"]) if forward is not None else None),
        "filled_rebalances": (int(forward["filled_rebalances"]) if forward is not None else None),
        "live_confirmed": bool(forward and forward["live_confirmed"]),
        "reference_trade_allowed": reference_trade_allowed,
        "decision": (
            "stop"
            if not integrity_ok
            else "reference_trade"
            if reference_trade_allowed
            else "paper_only"
        ),
        "errors": errors,
    }


def audit_v25_live_reference_files(
    site_data_path: str | Path,
    candidate_state_path: str | Path,
    spy_state_path: str | Path,
    matched_state_path: str | Path,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    return audit_v25_live_reference(
        json.loads(Path(site_data_path).read_text(encoding="utf-8")),
        load_paper_state(candidate_state_path),
        load_paper_state(spy_state_path),
        load_paper_state(matched_state_path),
        now=now,
    )


def verify_v25_reference_ledger(path: str | Path) -> dict[str, Any]:
    ledger = Path(path)
    if not ledger.exists():
        return {"ok": True, "receipts": 0, "head_sha256": None}
    previous: str | None = None
    last_date: str | None = None
    receipts = 0
    for line_number, raw in enumerate(ledger.read_text(encoding="utf-8").splitlines(), start=1):
        if not raw.strip():
            continue
        try:
            receipt = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError(f"v25 前瞻收據第 {line_number} 行不是有效 JSON") from exc
        claimed = str(receipt.get("receipt_sha256", ""))
        body = {key: value for key, value in receipt.items() if key != "receipt_sha256"}
        if claimed != _canonical_sha256(body):
            raise ValueError(f"v25 前瞻收據第 {line_number} 行雜湊不符")
        if body.get("previous_receipt_sha256") != previous:
            raise ValueError(f"v25 前瞻收據第 {line_number} 行鏈結不符")
        if int(body.get("sequence", -1)) != receipts + 1:
            raise ValueError(f"v25 前瞻收據第 {line_number} 行序號不連續")
        current_date = str(body.get("data_through", ""))
        if last_date is not None and current_date < last_date:
            raise ValueError(f"v25 前瞻收據第 {line_number} 行日期倒退")
        previous = claimed
        last_date = current_date
        receipts += 1
    return {"ok": True, "receipts": receipts, "head_sha256": previous}


def append_v25_reference_receipt(
    path: str | Path,
    *,
    site_payload: dict[str, Any],
    candidate_state: dict[str, Any],
    spy_state: dict[str, Any],
    matched_state: dict[str, Any],
    audit: dict[str, Any],
) -> dict[str, Any]:
    if not audit.get("integrity_ok"):
        raise ValueError("v25 完整性未通過，不得寫入前瞻證據鏈")
    ledger = Path(path)
    verified = verify_v25_reference_ledger(ledger)
    existing = (
        [
            json.loads(line)
            for line in ledger.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        if ledger.exists()
        else []
    )
    forward = v25_forward_paper_evidence(
        candidate_state,
        spy_state,
        matched_state,
    )
    evidence = {
        "site": {
            "data_through": site_payload.get("data_through"),
            "v25": site_payload.get("research_pipeline", {}).get("growth_gold_diversification", {}),
        },
        "accounts": {
            "candidate": _paper_performance_state(candidate_state),
            "SPY": _paper_performance_state(spy_state),
            "matched": _paper_performance_state(matched_state),
        },
        "forward": forward,
    }
    evidence_sha256 = _canonical_sha256(evidence)
    data_through = str(site_payload.get("data_through"))
    if existing and str(existing[-1].get("data_through")) == data_through:
        if str(existing[-1].get("evidence_sha256")) != evidence_sha256:
            raise ValueError("v25 同一資料日證據已改寫，拒絕靜默回填")
        return {**existing[-1], "appended": False}
    body = {
        "schema_version": V25_LIVE_LEDGER_SCHEMA_VERSION,
        "sequence": len(existing) + 1,
        "previous_receipt_sha256": verified["head_sha256"],
        "recorded_at_utc": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "data_through": data_through,
        "snapshot_sha256": candidate_state.get("snapshot_sha256"),
        "evidence_sha256": evidence_sha256,
        "forward_sessions": int(forward["forward_sessions"]),
        "filled_rebalances": int(forward["filled_rebalances"]),
        "live_confirmed": bool(forward["live_confirmed"]),
        "reference_trade_allowed": bool(audit["reference_trade_allowed"]),
    }
    receipt = {**body, "receipt_sha256": _canonical_sha256(body)}
    lines = [json.dumps(item, ensure_ascii=False, sort_keys=True) for item in existing]
    lines.append(json.dumps(receipt, ensure_ascii=False, sort_keys=True))
    ledger.parent.mkdir(parents=True, exist_ok=True)
    temporary = ledger.with_name(f".{ledger.name}.tmp")
    temporary.write_text("\n".join(lines) + "\n", encoding="utf-8")
    temporary.replace(ledger)
    verify_v25_reference_ledger(ledger)
    return {**receipt, "appended": True}


def finalize_v25_refresh_status(
    update_status: dict[str, Any],
    audit: dict[str, Any],
) -> dict[str, Any]:
    if str(update_status.get("data_through")) != str(audit.get("data_through")):
        raise ValueError("v25 更新收據與網站稽核日期不同")
    data_advanced = bool(update_status.get("data_advanced"))
    manual_review = bool(update_status.get("manual_review_required"))
    integrity_ok = bool(audit.get("integrity_ok"))
    deploy_allowed = bool(data_advanced and integrity_ok and not manual_review)
    return {
        "schema_version": 1,
        "generated_at_utc": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "data_through": audit.get("data_through"),
        "data_advanced": data_advanced,
        "idempotent_no_new_session": bool(update_status.get("idempotent_no_new_session")),
        "manual_review_required": manual_review,
        "integrity_ok": integrity_ok,
        "private_deploy_allowed": deploy_allowed,
        "public_paper_status_deploy_allowed": deploy_allowed,
        "reference_trade_allowed": bool(audit.get("reference_trade_allowed")),
        "decision": (
            "deploy_private"
            if deploy_allowed
            else "stop"
            if not integrity_ok or manual_review
            else "no_new_session_no_deploy"
        ),
        "update_status_sha256": _canonical_sha256(update_status),
        "audit_sha256": _canonical_sha256(audit),
    }
