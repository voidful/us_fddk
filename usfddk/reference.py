from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from usfddk.paper import PASSIVE_BENCHMARK_KEY, forward_paper_evidence, paper_metrics


def _weights_close(left: dict[str, Any], right: dict[str, Any], tolerance: float = 1e-8) -> bool:
    keys = set(left) | set(right)
    return all(abs(float(left.get(key, 0.0)) - float(right.get(key, 0.0))) <= tolerance for key in keys)


READINESS_GATE_LABELS = {
    "fresh_integrity": "資料新鮮，網站、快照與 Paper 狀態一致",
    "historical_gate_passed": "20 年歷史門檻通過",
    "exposure_control_passed": "公平曝險基準門檻通過",
    "statistically_confirmed": "多重搜尋後的統計證據通過",
    "at_least_252_forward_sessions": "至少累積 252 個前瞻交易日",
    "at_least_6_filled_rebalances": "至少完成 6 次前瞻換倉",
    "positive_return_after_costs": "前瞻扣成本報酬為正",
    "beats_spy_total_return": "前瞻總報酬勝過 SPY",
    "beats_passive_90_10_total_return": "前瞻總報酬勝過被動 90/10",
    "max_drawdown_no_worse_than_spy": "前瞻最大回撤不深於 SPY",
    "max_drawdown_no_worse_than_passive_90_10": "前瞻最大回撤不深於被動 90/10",
}
READINESS_CONTRACT_VERSION = 3


def _session_date(value: Any, *, label: str) -> datetime:
    text = str(value or "")
    try:
        return datetime.strptime(text, "%Y-%m-%d")
    except ValueError as exc:
        raise ValueError(f"{label}不是有效交易日 YYYY-MM-DD：{text or '空值'}") from exc


def build_live_refresh_status(
    *,
    previous_data_through: str | None,
    audit: dict[str, Any],
    account_states: dict[str, dict[str, Any]],
    generated_at: datetime | None = None,
) -> dict[str, Any]:
    """Create the deploy/no-deploy receipt for one automated LIVE refresh."""
    current_text = str(audit.get("data_through") or "")
    current = _session_date(current_text, label="本次資料截止日")
    previous_text = str(previous_data_through or "")
    previous = (
        _session_date(previous_text, label="前次資料截止日")
        if previous_text
        else None
    )
    if previous is not None and current < previous:
        raise ValueError(
            f"LIVE 更新資料日期倒退：{current_text} < {previous_text}"
        )
    if not bool(audit.get("integrity_ok")):
        raise ValueError("LIVE reference 完整性未通過，不得產生可部署收據")

    required = ("v2", "v3", "SPY", "QQQ", PASSIVE_BENCHMARK_KEY)
    missing = [name for name in required if name not in account_states]
    if missing:
        raise ValueError("LIVE 更新缺少同起點帳戶：" + "、".join(missing))
    account_as_of: dict[str, str] = {}
    for name in required:
        state = account_states[name]
        if state.get("mode") != "live":
            raise ValueError(f"{name} 不是 LIVE Paper 帳戶")
        as_of = str(state.get("as_of") or "")
        _session_date(as_of, label=f"{name} 帳戶日期")
        if as_of != current_text:
            raise ValueError(
                f"{name} 帳戶日期 {as_of} 與資料截止日 {current_text} 不同"
            )
        account_as_of[name] = as_of

    data_advanced = previous is None or current > previous
    readiness = audit.get("readiness", {})
    created = generated_at or datetime.now(UTC)
    if created.tzinfo is None:
        created = created.replace(tzinfo=UTC)
    return {
        "schema_version": 1,
        "generated_at_utc": created.astimezone(UTC).isoformat().replace(
            "+00:00", "Z"
        ),
        "previous_data_through": previous_text or None,
        "data_through": current_text,
        "data_advanced": data_advanced,
        "idempotent_no_new_session": not data_advanced,
        "private_deploy_allowed": data_advanced,
        "reference_trade_allowed": bool(audit.get("trade_ready")),
        "decision": audit.get("decision"),
        "integrity_ok": True,
        "readiness": {
            "passed_gate_count": int(readiness.get("passed_gate_count", 0)),
            "required_gate_count": int(readiness.get("required_gate_count", 0)),
        },
        "account_as_of": account_as_of,
    }


def write_live_refresh_status(
    path: str | Path, payload: dict[str, Any]
) -> Path:
    """Atomically persist the latest refresh receipt for automation decisions."""
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(f".{destination.name}.tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False),
        encoding="utf-8",
    )
    temporary.replace(destination)
    return destination


def evaluate_trade_readiness(
    site_payload: dict[str, Any], *, integrity_ok: bool
) -> dict[str, Any]:
    """Separate deployable evidence integrity from real-money trade readiness."""
    evidence = site_payload.get("evidence", {})
    forward_gates = (
        site_payload.get("paper", {}).get("forward_evidence", {}).get("gates", {})
    )
    gates = {
        "fresh_integrity": bool(integrity_ok),
        "historical_gate_passed": bool(evidence.get("historical_gate_passed")),
        "exposure_control_passed": bool(evidence.get("exposure_control_passed")),
        "statistically_confirmed": bool(evidence.get("statistically_confirmed")),
        **{
            key: bool(forward_gates.get(key))
            for key in (
                "at_least_252_forward_sessions",
                "at_least_6_filled_rebalances",
                "positive_return_after_costs",
                "beats_spy_total_return",
                "beats_passive_90_10_total_return",
                "max_drawdown_no_worse_than_spy",
                "max_drawdown_no_worse_than_passive_90_10",
            )
        },
    }
    trade_ready = all(gates.values())
    decision = (
        "reference_trade"
        if trade_ready
        else "paper_only"
        if integrity_ok
        else "stop"
    )
    failed = [
        {"gate": key, "label": READINESS_GATE_LABELS[key]}
        for key, passed in gates.items()
        if not passed
    ]
    return {
        "contract_version": READINESS_CONTRACT_VERSION,
        "trade_ready": trade_ready,
        "decision": decision,
        "ui_mode": "reference_trade" if trade_ready else "paper_only",
        "allocation_visible": trade_ready,
        "passed_gate_count": sum(gates.values()),
        "required_gate_count": len(gates),
        "gates": gates,
        "failed": failed,
    }


def _canonical_sha256(value: Any) -> str:
    encoded = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _paper_evidence_state(state: dict[str, Any]) -> dict[str, Any]:
    """Exclude wall-clock metadata while retaining every performance-bearing field."""
    return {
        key: state.get(key)
        for key in (
            "schema_version",
            "mode",
            "strategy",
            "started_at",
            "as_of",
            "snapshot_sha256",
            "initial_cash",
            "cash",
            "cost_bps",
            "holdings",
            "pending_order",
            "order_history",
            "transactions",
            "equity_curve",
            "adjustment_rebases",
            "total_costs",
        )
    }


def verify_reference_receipt_ledger(path: str | Path) -> dict[str, Any]:
    ledger = Path(path)
    if not ledger.exists():
        return {"ok": True, "receipts": 0, "head_sha256": None}
    previous: str | None = None
    receipts = 0
    last_date: str | None = None
    for line_number, raw in enumerate(
        ledger.read_text(encoding="utf-8").splitlines(), start=1
    ):
        if not raw.strip():
            continue
        try:
            receipt = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError(f"前瞻收據第 {line_number} 行不是有效 JSON") from exc
        claimed = str(receipt.get("receipt_sha256", ""))
        body = {key: value for key, value in receipt.items() if key != "receipt_sha256"}
        if claimed != _canonical_sha256(body):
            raise ValueError(f"前瞻收據第 {line_number} 行雜湊不符")
        if body.get("previous_receipt_sha256") != previous:
            raise ValueError(f"前瞻收據第 {line_number} 行鏈結不符")
        if int(body.get("sequence", -1)) != receipts + 1:
            raise ValueError(f"前瞻收據第 {line_number} 行序號不連續")
        current_date = str(body.get("data_through", ""))
        if last_date is not None and current_date < last_date:
            raise ValueError(f"前瞻收據第 {line_number} 行日期倒退")
        previous = claimed
        last_date = current_date
        receipts += 1
    return {"ok": True, "receipts": receipts, "head_sha256": previous}


def append_reference_receipt(
    path: str | Path,
    *,
    site_payload: dict[str, Any],
    paper_state: dict[str, Any],
    paper_benchmark_states: dict[str, dict[str, Any]],
    audit: dict[str, Any],
    challenger_paper_state: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Append an idempotent hash-chained receipt for forward-only evidence."""
    if not audit.get("integrity_ok"):
        raise ValueError("資料完整性未通過，不得寫入前瞻收據")
    ledger = Path(path)
    verified = verify_reference_receipt_ledger(ledger)
    existing = [
        json.loads(line)
        for line in ledger.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ] if ledger.exists() else []
    forward = site_payload.get("paper", {}).get("forward_evidence", {})
    evidence_state = {
        "site": {
            "schema_version": site_payload.get("schema_version"),
            "data_through": site_payload.get("data_through"),
            "snapshot_sha256": site_payload.get("snapshot_sha256"),
            "strategy": site_payload.get("strategy"),
            "evidence": site_payload.get("evidence"),
            "paper": site_payload.get("paper"),
        },
        "primary": _paper_evidence_state(paper_state),
        "benchmarks": {
            ticker: _paper_evidence_state(state)
            for ticker, state in sorted(paper_benchmark_states.items())
        },
        "challenger": (
            _paper_evidence_state(challenger_paper_state)
            if challenger_paper_state is not None
            else None
        ),
    }
    digest = _canonical_sha256(evidence_state)
    identity = {
        "data_through": str(site_payload.get("data_through")),
        "snapshot_sha256": str(site_payload.get("snapshot_sha256")),
        "contract_version": int(
            audit.get("readiness", {}).get(
                "contract_version", READINESS_CONTRACT_VERSION
            )
        ),
    }
    if existing:
        last = existing[-1]
        same_identity = all(
            last.get(key, 1 if key == "contract_version" else None) == value
            for key, value in identity.items()
        )
        if same_identity and last.get("evidence_digest") == digest:
            return {**last, "appended": False}
        if same_identity:
            raise ValueError("同一日期與快照的前瞻證據已改變，拒絕靜默回填")
        if identity["data_through"] < str(last.get("data_through", "")):
            raise ValueError("前瞻收據日期倒退")
    body = {
        "schema_version": 1,
        "sequence": len(existing) + 1,
        **identity,
        "paper_as_of": str(paper_state.get("as_of")),
        "forward_sessions": int(forward.get("forward_sessions", 0)),
        "filled_rebalances": int(forward.get("filled_rebalances", 0)),
        "integrity_ok": True,
        "trade_ready": bool(audit.get("trade_ready")),
        "decision": audit.get("decision"),
        "readiness_gates": audit.get("readiness", {}).get("gates", {}),
        "evidence_digest": digest,
        "previous_receipt_sha256": verified["head_sha256"],
    }
    receipt = {**body, "receipt_sha256": _canonical_sha256(body)}
    ledger.parent.mkdir(parents=True, exist_ok=True)
    with ledger.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(receipt, ensure_ascii=False, separators=(",", ":")))
        handle.write("\n")
    verify_reference_receipt_ledger(ledger)
    return {**receipt, "appended": True}


def audit_live_reference(
    site_payload: dict[str, Any],
    paper_state: dict[str, Any],
    paper_benchmark_states: dict[str, dict[str, Any]],
    *,
    challenger_paper_state: dict[str, Any] | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Cross-check the deployable site payload against the authoritative LIVE state."""
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
    if site_payload.get("schema_version") != 1:
        errors.append("網站資料 schema 不支援")
    if paper_state.get("mode") != "live" or site_payload.get("paper", {}).get("mode") != "live":
        errors.append("參考交易只能使用 LIVE paper，不能使用 replay")
    site_paper = site_payload.get("paper", {})
    if str(site_payload.get("data_through")) != str(paper_state.get("as_of")):
        errors.append("網站資料截止日與 paper 進度不同")
    if str(site_payload.get("snapshot_sha256")) != str(paper_state.get("snapshot_sha256")):
        errors.append("網站與 paper 使用的快照雜湊不同")
    pending = paper_state.get("pending_order")
    site_pending = site_payload.get("paper", {}).get("pending_order")
    if bool(pending) != bool(site_pending):
        errors.append("網站與 paper 的待成交狀態不同")
    if pending and site_pending and not _weights_close(
        pending.get("target_weights", {}), site_pending.get("target_weights", {})
    ):
        errors.append("網站與 paper 的待成交權重不同")
    if pending and not _weights_close(
        pending.get("target_weights", {}), site_payload.get("strategy", {}).get("current_target", {})
    ):
        errors.append("網站策略配置與 paper 待成交權重不同")
    paper = paper_metrics(paper_state)
    marked_equity = float(paper_state.get("cash", 0.0)) + sum(
        float(position.get("market_value", 0.0))
        for position in paper_state.get("holdings", {}).values()
    )
    if abs(marked_equity - float(paper["equity"])) > 1e-8 * max(
        abs(float(paper["equity"])), 1.0
    ):
        errors.append("paper 持倉加現金與已記錄權益不同")
    forward_sessions = max(len(paper_state.get("equity_curve", [])) - 1, 0)
    if int(site_paper.get("forward_sessions", -1)) != forward_sessions:
        errors.append("網站前瞻日數與 paper 不同")
    if int(site_paper.get("transactions", -1)) != len(paper_state.get("transactions", [])):
        errors.append("網站成交筆數與 paper 不同")
    for field in ("equity", "return", "cash"):
        expected = float(paper_state["cash"]) if field == "cash" else float(paper[field])
        try:
            actual = float(site_paper[field])
        except (KeyError, TypeError, ValueError):
            errors.append(f"網站 paper 缺少有效的 {field}")
            continue
        if abs(actual - expected) > 1e-8 * max(abs(expected), 1.0):
            errors.append(f"網站 paper {field} 與 LIVE state 不同")
    if int(site_paper.get("adjustment_rebases", -1)) != len(
        paper_state.get("adjustment_rebases", [])
    ):
        errors.append("網站價格重基準筆數與 paper 不同")
    expected_holdings = {
        ticker: float(position["market_value"]) / max(float(paper["equity"]), 1e-12)
        for ticker, position in paper_state.get("holdings", {}).items()
    }
    site_holdings = {
        ticker: float(position.get("weight", 0.0))
        for ticker, position in site_paper.get("holdings", {}).items()
    }
    if not _weights_close(expected_holdings, site_holdings):
        errors.append("網站持倉權重與 paper 市值不同")

    try:
        forward = forward_paper_evidence(paper_state, paper_benchmark_states)
    except (KeyError, TypeError, ValueError) as exc:
        forward = None
        errors.append(f"LIVE benchmark 無效：{exc}")
    if forward is not None:
        site_forward = site_paper.get("forward_evidence", {})
        if int(site_forward.get("forward_sessions", -1)) != int(
            forward["forward_sessions"]
        ):
            errors.append("網站 LIVE 證據日數與 benchmark 稽核不同")
        if int(site_forward.get("filled_rebalances", -1)) != int(
            forward["filled_rebalances"]
        ):
            errors.append("網站 LIVE 換倉次數與 benchmark 稽核不同")
        if site_forward.get("gates") != forward["gates"]:
            errors.append("網站 LIVE 門檻與 benchmark 稽核不同")
        for ticker in ("SPY", "QQQ", PASSIVE_BENCHMARK_KEY):
            expected = float(forward["benchmarks"][ticker]["return"])
            try:
                actual = float(site_forward["benchmarks"][ticker]["return"])
            except (KeyError, TypeError, ValueError):
                errors.append(f"網站缺少 {ticker} LIVE benchmark")
                continue
            if abs(actual - expected) > 1e-12:
                errors.append(f"網站 {ticker} LIVE benchmark 與 state 不同")
        if bool(site_payload.get("evidence", {}).get("live_confirmed")) != bool(
            forward["live_confirmed"]
        ):
            errors.append("網站 LIVE 確認狀態與前瞻門檻不同")
    expected_candidate = bool(
        site_payload.get("evidence", {}).get("historical_gate_passed")
    ) and bool(site_payload.get("evidence", {}).get("exposure_control_passed"))
    if bool(
        site_payload.get("evidence", {}).get("reference_trade_candidate")
    ) != expected_candidate:
        errors.append("網站實金候選狀態與歷史／公平基準門檻不同")
    declared_readiness = site_payload.get("readiness")
    expected_readiness = evaluate_trade_readiness(site_payload, integrity_ok=True)
    if not isinstance(declared_readiness, dict):
        errors.append("網站缺少實金 readiness 合約")
    else:
        for field in (
            "contract_version",
            "trade_ready",
            "decision",
            "passed_gate_count",
            "required_gate_count",
            "gates",
            "failed",
        ):
            if declared_readiness.get(field) != expected_readiness.get(field):
                errors.append(f"網站 readiness {field} 與證據不同")
    if not bool(site_payload.get("evidence", {}).get("historical_gate_passed")):
        errors.append("歷史上線門檻未通過")
    challenger_errors: list[str] = []
    if challenger_paper_state is not None:
        challenger = (
            site_payload.get("research_pipeline", {})
            .get("challengers", {})
            .get("v3", {})
        )
        challenger_site_paper = challenger.get("paper")
        if not isinstance(challenger_site_paper, dict):
            challenger_errors.append("網站缺少 v3 獨立 Paper 狀態")
        else:
            if challenger_paper_state.get("mode") != "live" or challenger_site_paper.get(
                "mode"
            ) != "live":
                challenger_errors.append("v3 只能使用 LIVE paper，不能使用 replay")
            if str(challenger.get("name")) != str(
                challenger_paper_state.get("strategy")
            ):
                challenger_errors.append("網站 v3 名稱與獨立 Paper 策略不同")
            if str(challenger_site_paper.get("as_of")) != str(
                challenger_paper_state.get("as_of")
            ) or str(site_payload.get("data_through")) != str(
                challenger_paper_state.get("as_of")
            ):
                challenger_errors.append("網站資料截止日與 v3 Paper 進度不同")
            if str(challenger_site_paper.get("snapshot_sha256")) != str(
                challenger_paper_state.get("snapshot_sha256")
            ) or str(site_payload.get("snapshot_sha256")) != str(
                challenger_paper_state.get("snapshot_sha256")
            ):
                challenger_errors.append("網站與 v3 Paper 使用的快照雜湊不同")
            challenger_pending = challenger_paper_state.get("pending_order")
            challenger_site_pending = challenger_site_paper.get("pending_order")
            if bool(challenger_pending) != bool(challenger_site_pending):
                challenger_errors.append("網站與 v3 Paper 的待成交狀態不同")
            if (
                challenger_pending
                and challenger_site_pending
                and not _weights_close(
                    challenger_pending.get("target_weights", {}),
                    challenger_site_pending.get("target_weights", {}),
                )
            ):
                challenger_errors.append("網站與 v3 Paper 的待成交權重不同")
            if challenger_pending and not _weights_close(
                challenger_pending.get("target_weights", {}),
                challenger.get("current_target", {}),
            ):
                challenger_errors.append("網站 v3 配置與獨立 Paper 待成交權重不同")

            challenger_metrics = paper_metrics(challenger_paper_state)
            for field in ("equity", "return", "cash"):
                expected = (
                    float(challenger_paper_state["cash"])
                    if field == "cash"
                    else float(challenger_metrics[field])
                )
                try:
                    actual = float(challenger_site_paper[field])
                except (KeyError, TypeError, ValueError):
                    challenger_errors.append(f"網站 v3 Paper 缺少有效的 {field}")
                    continue
                if abs(actual - expected) > 1e-8 * max(abs(expected), 1.0):
                    challenger_errors.append(f"網站 v3 Paper {field} 與 LIVE state 不同")
            challenger_sessions = max(
                len(challenger_paper_state.get("equity_curve", [])) - 1, 0
            )
            if int(challenger_site_paper.get("forward_sessions", -1)) != int(
                challenger_sessions
            ):
                challenger_errors.append("網站 v3 前瞻日數與獨立 Paper 不同")
            if int(challenger_site_paper.get("transactions", -1)) != len(
                challenger_paper_state.get("transactions", [])
            ):
                challenger_errors.append("網站 v3 成交筆數與獨立 Paper 不同")
            challenger_equity = max(float(challenger_metrics["equity"]), 1e-12)
            expected_challenger_holdings = {
                ticker: float(position["market_value"]) / challenger_equity
                for ticker, position in challenger_paper_state.get("holdings", {}).items()
            }
            site_challenger_holdings = {
                ticker: float(position.get("weight", 0.0))
                for ticker, position in challenger_site_paper.get("holdings", {}).items()
            }
            if not _weights_close(
                expected_challenger_holdings, site_challenger_holdings
            ):
                challenger_errors.append("網站 v3 持倉權重與獨立 Paper 市值不同")
        errors.extend(challenger_errors)
    stale = checked_at > due
    integrity_ok = not errors and not stale
    readiness = evaluate_trade_readiness(
        site_payload,
        integrity_ok=integrity_ok,
    )
    return {
        "ok": integrity_ok,
        "integrity_ok": integrity_ok,
        "safe_to_publish_paper_status": integrity_ok,
        "status": "invalid" if errors else "stale" if stale else "fresh",
        "checked_at_utc": checked_at.astimezone(UTC).isoformat().replace("+00:00", "Z"),
        "refresh_due_at_utc": due_text,
        "data_through": site_payload.get("data_through"),
        "paper_as_of": paper_state.get("as_of"),
        "snapshot_sha256": site_payload.get("snapshot_sha256"),
        "historical_gate_passed": bool(
            site_payload.get("evidence", {}).get("historical_gate_passed")
        ),
        "exposure_control_passed": bool(
            site_payload.get("evidence", {}).get("exposure_control_passed")
        ),
        "reference_trade_candidate": bool(
            site_payload.get("evidence", {}).get("reference_trade_candidate")
        ),
        "statistically_confirmed": bool(
            site_payload.get("evidence", {}).get("statistically_confirmed")
        ),
        "live_confirmed": bool(site_payload.get("evidence", {}).get("live_confirmed")),
        "trade_ready": bool(readiness["trade_ready"]),
        "decision": readiness["decision"],
        "readiness": readiness,
        "challenger_paper_consistent": (
            None if challenger_paper_state is None else not challenger_errors
        ),
        "errors": errors,
    }


def audit_live_reference_files(
    site_data_path: str | Path,
    paper_state_path: str | Path,
    spy_paper_state_path: str | Path,
    qqq_paper_state_path: str | Path,
    passive90_paper_state_path: str | Path,
    challenger_paper_state_path: str | Path | None = None,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    site_payload = json.loads(Path(site_data_path).read_text(encoding="utf-8"))
    paper_state = json.loads(Path(paper_state_path).read_text(encoding="utf-8"))
    benchmark_states = {
        "SPY": json.loads(Path(spy_paper_state_path).read_text(encoding="utf-8")),
        "QQQ": json.loads(Path(qqq_paper_state_path).read_text(encoding="utf-8")),
        PASSIVE_BENCHMARK_KEY: json.loads(
            Path(passive90_paper_state_path).read_text(encoding="utf-8")
        ),
    }
    challenger_paper_state = (
        json.loads(Path(challenger_paper_state_path).read_text(encoding="utf-8"))
        if challenger_paper_state_path is not None
        else None
    )
    return audit_live_reference(
        site_payload,
        paper_state,
        benchmark_states,
        challenger_paper_state=challenger_paper_state,
        now=now,
    )


def append_reference_receipt_files(
    ledger_path: str | Path,
    site_data_path: str | Path,
    paper_state_path: str | Path,
    spy_paper_state_path: str | Path,
    qqq_paper_state_path: str | Path,
    passive90_paper_state_path: str | Path,
    challenger_paper_state_path: str | Path | None,
    *,
    audit: dict[str, Any],
) -> dict[str, Any]:
    site_payload = json.loads(Path(site_data_path).read_text(encoding="utf-8"))
    paper_state = json.loads(Path(paper_state_path).read_text(encoding="utf-8"))
    benchmark_states = {
        "SPY": json.loads(Path(spy_paper_state_path).read_text(encoding="utf-8")),
        "QQQ": json.loads(Path(qqq_paper_state_path).read_text(encoding="utf-8")),
        PASSIVE_BENCHMARK_KEY: json.loads(
            Path(passive90_paper_state_path).read_text(encoding="utf-8")
        ),
    }
    challenger = (
        json.loads(Path(challenger_paper_state_path).read_text(encoding="utf-8"))
        if challenger_paper_state_path is not None
        else None
    )
    return append_reference_receipt(
        ledger_path,
        site_payload=site_payload,
        paper_state=paper_state,
        paper_benchmark_states=benchmark_states,
        audit=audit,
        challenger_paper_state=challenger,
    )
