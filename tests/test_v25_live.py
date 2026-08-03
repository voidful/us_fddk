from __future__ import annotations

import json
import shutil
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
import pytest

from usfddk.data import load_snapshot, save_snapshot, validate_panel
from usfddk.models import MarketPanel
from usfddk.v25_live import (
    append_v25_reference_receipt,
    audit_v25_live_reference,
    finalize_v25_refresh_status,
    run_v25_live_update,
    verify_v25_reference_ledger,
)

ROOT = Path(__file__).resolve().parents[1]
SITE_DATA = ROOT / "artifacts/site_data.json"
VALIDATION = ROOT / "artifacts/v25_growth_gold_diversification_validation.json"
SNAPSHOT = ROOT / "artifacts/snapshot_v25_vanguard_20060701_20260731_6cf44e63.zip"
STATE_PATHS = {
    "candidate": ROOT / "artifacts/paper_v25_state.json",
    "SPY": ROOT / "artifacts/paper_v25_spy_state.json",
    "matched": ROOT / "artifacts/paper_v25_matched_state.json",
}


def _fixtures() -> tuple[dict, dict, dict, dict]:
    site = json.loads(SITE_DATA.read_text(encoding="utf-8"))
    states = {
        key: json.loads(path.read_text(encoding="utf-8")) for key, path in STATE_PATHS.items()
    }
    return site, states["candidate"], states["SPY"], states["matched"]


def test_v25_live_audit_accepts_synchronized_site_and_states() -> None:
    site, candidate, spy, matched = _fixtures()
    audit = audit_v25_live_reference(
        site,
        candidate,
        spy,
        matched,
        now=datetime(2026, 8, 3, tzinfo=UTC),
    )
    assert audit["integrity_ok"] is True
    assert audit["status"] == "fresh"
    assert audit["decision"] == "paper_only"
    assert audit["reference_trade_allowed"] is False
    expected_forward_sessions = site["research_pipeline"][
        "growth_gold_diversification"
    ]["paper"]["forward_evidence"]["forward_sessions"]
    assert audit["forward_sessions"] == expected_forward_sessions
    assert audit["errors"] == []


def test_v25_live_audit_fails_closed_on_account_or_site_drift() -> None:
    site, candidate, spy, matched = _fixtures()
    drifted = deepcopy(matched)
    drifted["as_of"] = "2026-07-30"
    audit = audit_v25_live_reference(
        site,
        candidate,
        spy,
        drifted,
        now=datetime(2026, 8, 3, tzinfo=UTC),
    )
    assert audit["integrity_ok"] is False
    assert audit["status"] == "invalid"
    assert audit["decision"] == "stop"
    assert any("matched" in error or "同步門檻" in error for error in audit["errors"])

    changed_site = deepcopy(site)
    paper = changed_site["research_pipeline"]["growth_gold_diversification"]["paper"]
    if paper.get("pending_order"):
        paper["pending_order"]["target_weights"] = {"GLD": 0.3, "VUG": 0.7}
        expected_pending_error = "網站 v25 待成交權重與候選帳戶不同"
    else:
        paper["pending_order"] = {
            "signal_date": candidate["as_of"],
            "execute_after": candidate["as_of"],
            "status": "pending",
            "target_weights": {"GLD": 0.2, "VUG": 0.8},
        }
        expected_pending_error = "網站 v25 待成交狀態與候選帳戶不同"
    audit = audit_v25_live_reference(
        changed_site,
        candidate,
        spy,
        matched,
        now=datetime(2026, 8, 3, tzinfo=UTC),
    )
    assert audit["integrity_ok"] is False
    assert expected_pending_error in audit["errors"]

    changed_site = deepcopy(site)
    accounts = changed_site["research_pipeline"]["growth_gold_diversification"]["paper"]["accounts"]
    accounts["SPY"]["equity"] = 99_000.0
    accounts["matched_80_VUG_20_SHY"]["equity_curve"][0]["date"] = "2026-07-30"
    audit = audit_v25_live_reference(
        changed_site,
        candidate,
        spy,
        matched,
        now=datetime(2026, 8, 3, tzinfo=UTC),
    )
    assert audit["integrity_ok"] is False
    assert "網站 v25 SPY 比較帳戶 equity 不同" in audit["errors"]
    assert any(
        "matched_80_VUG_20_SHY" in error and "日期不同" in error for error in audit["errors"]
    )


def test_v25_live_update_is_idempotent_without_a_new_session(tmp_path: Path) -> None:
    copied = {}
    for label, source in STATE_PATHS.items():
        destination = tmp_path / source.name
        shutil.copy2(source, destination)
        copied[label] = destination
    before = {label: path.read_bytes() for label, path in copied.items()}
    status = run_v25_live_update(
        snapshot=SNAPSHOT,
        as_of="2026-07-31",
        output_dir=tmp_path,
        eligibility_receipt=VALIDATION,
        candidate_state_path=copied["candidate"],
        spy_state_path=copied["SPY"],
        matched_state_path=copied["matched"],
        evidence_path=tmp_path / "evidence.json",
        status_path=tmp_path / "status.json",
    )
    assert status["data_advanced"] is False
    assert status["idempotent_no_new_session"] is True
    assert status["state_changed_without_new_session"] is False
    assert status["state_write_applied"] is False
    assert status["site_rebuild_required"] is False
    assert status["private_deploy_candidate"] is False
    assert status["decision"] == "no_new_session_no_deploy"
    assert {item["as_of"] for item in status["accounts"].values()} == {"2026-07-31"}
    assert {label: path.read_bytes() for label, path in copied.items()} == before
    assert not list(tmp_path.glob(".*.tmp"))


def test_v25_live_update_executes_all_first_orders_on_same_new_open(
    tmp_path: Path,
) -> None:
    frozen, _ = load_snapshot(SNAPSHOT)
    new_day = pd.Timestamp("2026-08-03")
    open_row = frozen.close.iloc[-1] * 1.002
    close_row = open_row * pd.Series({"GLD": 1.001, "SHY": 1.0001, "SPY": 1.003, "VUG": 1.004})

    def extended(frame: pd.DataFrame, row: pd.Series) -> pd.DataFrame:
        result = frame.copy()
        result.loc[new_day] = row.reindex(result.columns)
        return result

    open_prices = extended(frozen.open, open_row)
    close_prices = extended(frozen.close, close_row)
    high_prices = extended(
        frozen.high,
        pd.concat([open_row, close_row], axis=1).max(axis=1) * 1.001,
    )
    low_prices = extended(
        frozen.low,
        pd.concat([open_row, close_row], axis=1).min(axis=1) * 0.999,
    )
    volume = extended(frozen.volume, frozen.volume.iloc[-1])
    panel = MarketPanel(
        open=open_prices,
        high=high_prices,
        low=low_prices,
        close=close_prices,
        volume=volume,
        metadata={"provider": "test next completed session"},
    )
    contract = validate_panel(
        panel,
        as_of="2026-08-03",
        required=("GLD", "SHY", "SPY", "VUG"),
        min_last_coverage=1.0,
        min_history_coverage=0.999,
        require_fresh=True,
    )
    contract.require()
    snapshot = tmp_path / "next-session.zip"
    save_snapshot(panel, snapshot, contract=contract)

    copied = {}
    for label, source in STATE_PATHS.items():
        destination = tmp_path / source.name
        shutil.copy2(source, destination)
        copied[label] = destination
    status = run_v25_live_update(
        snapshot=snapshot,
        as_of="2026-08-03",
        output_dir=tmp_path,
        eligibility_receipt=VALIDATION,
        candidate_state_path=copied["candidate"],
        spy_state_path=copied["SPY"],
        matched_state_path=copied["matched"],
        evidence_path=tmp_path / "evidence-next.json",
        status_path=tmp_path / "status-next.json",
    )
    assert status["data_advanced"] is True
    assert status["state_write_applied"] is True
    assert status["private_deploy_candidate"] is True
    assert status["decision"] == "rebuild_and_audit"
    assert status["forward_evidence"]["forward_sessions"] == 1
    assert status["forward_evidence"]["filled_orders_including_initial_allocation"] == 1
    assert status["forward_evidence"]["initial_allocations"] == 1
    assert status["forward_evidence"]["filled_rebalances"] == 0
    assert status["forward_evidence"]["live_confirmed"] is False
    assert {item["as_of"] for item in status["accounts"].values()} == {"2026-08-03"}
    assert status["accounts"]["candidate"]["transactions"] == 2
    assert status["accounts"]["SPY"]["transactions"] == 1
    assert status["accounts"]["matched"]["transactions"] == 2
    candidate = json.loads(copied["candidate"].read_text(encoding="utf-8"))
    assert set(candidate["holdings"]) == {"GLD", "VUG"}
    assert candidate["pending_order"] is None


def test_v25_live_update_rejects_drift_before_writing_any_account(
    tmp_path: Path,
) -> None:
    copied = {}
    for label, source in STATE_PATHS.items():
        destination = tmp_path / source.name
        shutil.copy2(source, destination)
        copied[label] = destination
    matched = json.loads(copied["matched"].read_text(encoding="utf-8"))
    matched["initial_cash"] = 90_000.0
    copied["matched"].write_text(
        json.dumps(matched, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    before = {label: path.read_bytes() for label, path in copied.items()}
    with pytest.raises(RuntimeError, match="同步完整性門檻未通過"):
        run_v25_live_update(
            snapshot=SNAPSHOT,
            as_of="2026-07-31",
            output_dir=tmp_path,
            eligibility_receipt=VALIDATION,
            candidate_state_path=copied["candidate"],
            spy_state_path=copied["SPY"],
            matched_state_path=copied["matched"],
            evidence_path=tmp_path / "evidence-drift.json",
            status_path=tmp_path / "status-drift.json",
        )
    assert {label: path.read_bytes() for label, path in copied.items()} == before
    assert not (tmp_path / "evidence-drift.json").exists()
    assert not (tmp_path / "status-drift.json").exists()


def test_v25_live_update_rejects_order_path_drift_before_writing(
    tmp_path: Path,
) -> None:
    copied = {}
    for label, source in STATE_PATHS.items():
        destination = tmp_path / source.name
        shutil.copy2(source, destination)
        copied[label] = destination
    matched = json.loads(copied["matched"].read_text(encoding="utf-8"))
    matched["pending_order"]["execute_after"] = "2026-08-01"
    copied["matched"].write_text(
        json.dumps(matched, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    before = {label: path.read_bytes() for label, path in copied.items()}
    with pytest.raises(RuntimeError, match="同步完整性門檻未通過"):
        run_v25_live_update(
            snapshot=SNAPSHOT,
            as_of="2026-07-31",
            output_dir=tmp_path,
            eligibility_receipt=VALIDATION,
            candidate_state_path=copied["candidate"],
            spy_state_path=copied["SPY"],
            matched_state_path=copied["matched"],
            evidence_path=tmp_path / "evidence-order-drift.json",
            status_path=tmp_path / "status-order-drift.json",
        )
    assert {label: path.read_bytes() for label, path in copied.items()} == before
    assert not (tmp_path / "evidence-order-drift.json").exists()
    assert not (tmp_path / "status-order-drift.json").exists()


def test_v25_ledger_is_idempotent_and_rejects_same_day_rewrite(
    tmp_path: Path,
) -> None:
    site, candidate, spy, matched = _fixtures()
    audit = audit_v25_live_reference(
        site,
        candidate,
        spy,
        matched,
        now=datetime(2026, 8, 3, tzinfo=UTC),
    )
    ledger = tmp_path / "v25.jsonl"
    first = append_v25_reference_receipt(
        ledger,
        site_payload=site,
        candidate_state=candidate,
        spy_state=spy,
        matched_state=matched,
        audit=audit,
    )
    assert first["appended"] is True
    duplicate = append_v25_reference_receipt(
        ledger,
        site_payload=site,
        candidate_state=candidate,
        spy_state=spy,
        matched_state=matched,
        audit=audit,
    )
    assert duplicate["appended"] is False
    assert duplicate["receipt_sha256"] == first["receipt_sha256"]
    assert verify_v25_reference_ledger(ledger)["receipts"] == 1

    rewritten = deepcopy(candidate)
    rewritten["cash"] = float(rewritten["cash"]) - 1.0
    with pytest.raises(ValueError, match="拒絕靜默回填"):
        append_v25_reference_receipt(
            ledger,
            site_payload=site,
            candidate_state=rewritten,
            spy_state=spy,
            matched_state=matched,
            audit=audit,
        )


def test_v25_refresh_status_requires_both_new_data_and_integrity() -> None:
    update = {
        "data_through": "2026-08-03",
        "data_advanced": True,
        "idempotent_no_new_session": False,
        "manual_review_required": False,
    }
    audit = {
        "data_through": "2026-08-03",
        "integrity_ok": True,
        "reference_trade_allowed": False,
    }
    ready = finalize_v25_refresh_status(update, audit)
    assert ready["private_deploy_allowed"] is True
    assert ready["decision"] == "deploy_private"
    assert ready["reference_trade_allowed"] is False

    same_day = finalize_v25_refresh_status(
        {
            **update,
            "data_advanced": False,
            "idempotent_no_new_session": True,
        },
        audit,
    )
    assert same_day["private_deploy_allowed"] is False
    assert same_day["decision"] == "no_new_session_no_deploy"

    failed = finalize_v25_refresh_status(
        update,
        {**audit, "integrity_ok": False},
    )
    assert failed["private_deploy_allowed"] is False
    assert failed["decision"] == "stop"
