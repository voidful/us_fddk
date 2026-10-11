from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

import exchange_calendars as xcals
import numpy as np
import pandas as pd
import pytest

from usfddk.data import load_snapshot, save_snapshot
from usfddk.models import MarketPanel
from usfddk.v25_live import (
    V25_LIVE_TICKERS,
    audit_v25_live_reference,
    run_v25_live_update,
    verify_v25_reference_ledger,
)
from usfddk.v25_recovery import prepare_v25_live_segment

ROOT = Path(__file__).resolve().parents[1]
VALIDATION = ROOT / "artifacts/v25_growth_gold_diversification_validation.json"
NOW = datetime(2026, 10, 11, 11, tzinfo=UTC)
STATE_NAMES = ("paper_v25_state.json", "paper_v25_spy_state.json", "paper_v25_matched_state.json")
LEDGER_NAME = "v25_live_evidence_ledger.jsonl"
ARCHIVED_PRIOR = ROOT / "artifacts/v25_live_segments/2026-10-09/prior"


@pytest.fixture
def current_panel() -> MarketPanel:
    """Synthetic OHLCV is confined to offline tests and never enters a LIVE file."""
    dates = xcals.get_calendar("XNYS", start="2026-07-01", end="2026-10-12").sessions
    dates = pd.DatetimeIndex(dates).tz_localize(None)
    dates = dates[dates <= pd.Timestamp("2026-10-09")]
    close = pd.DataFrame(
        100.0 + np.arange(len(dates))[:, None] * np.array([[0.05, 0.01, 0.06, 0.07]]),
        index=dates, columns=V25_LIVE_TICKERS,
    )
    return MarketPanel(
        open=close * 0.999, high=close * 1.001, low=close * 0.998, close=close,
        volume=close * 1000.0, metadata={"provider": "synthetic offline recovery fixture"},
    )


@pytest.fixture
def old_chain(tmp_path: Path) -> dict[str, Path]:
    previous = tmp_path / "previous"
    previous.mkdir()
    for name in (*STATE_NAMES, LEDGER_NAME):
        source = ARCHIVED_PRIOR if ARCHIVED_PRIOR.exists() else ROOT / "artifacts"
        (previous / name).write_bytes((source / name).read_bytes())
    return {
        "candidate_state_path": previous / STATE_NAMES[0],
        "spy_state_path": previous / STATE_NAMES[1],
        "matched_state_path": previous / STATE_NAMES[2],
        "ledger_path": previous / LEDGER_NAME,
    }


def test_new_segment_preserves_old_bytes_and_counts_only_future_sessions(
    tmp_path: Path, old_chain: dict, current_panel: MarketPanel,
) -> None:
    snapshot = tmp_path / "test-current.zip"
    save_snapshot(current_panel, snapshot)
    before = {key: path.read_bytes() for key, path in old_chain.items()}
    segment = tmp_path / "new-segment"
    manifest = prepare_v25_live_segment(
        segment, **old_chain, snapshot=snapshot, observed_at=NOW, eligibility_receipt=VALIDATION,
    )
    assert manifest["new_started_at"] == "2026-10-09"
    assert manifest["prior_data_through"] == "2026-08-28"
    assert manifest["new_forward_sessions"] == manifest["new_filled_rebalances"] == 0
    assert manifest["inherited_forward_sessions"] == manifest["backfilled_forward_sessions"] == 0
    assert manifest["minimum_new_sessions"] == 252
    assert manifest["minimum_completed_rebalances"] == 6
    assert not manifest["activation_applied"] and not manifest["deployment_applied"]
    assert manifest["live_confirmed"] is False
    assert {key: path.read_bytes() for key, path in old_chain.items()} == before
    for key, path in old_chain.items():
        assert (segment / "prior" / path.name).read_bytes() == before[key]
    assert verify_v25_reference_ledger(segment / LEDGER_NAME)["receipts"] == 0
    assert verify_v25_reference_ledger(segment / "prior" / LEDGER_NAME)["receipts"] == 15
    for name in STATE_NAMES:
        state = json.loads((segment / name).read_text())
        assert state["started_at"] == state["as_of"] == "2026-10-09"
        assert len(state["equity_curve"]) == 1
        assert not state["holdings"] and not state["transactions"] and not state["order_history"]
        assert state["initial_cash"] == 100_000.0 and state["cost_bps"] == 10.0
        assert state["pending_order"]["execute_after"] == "2026-10-09"

    fields = {}
    for field, frame in current_panel.field_map().items():
        fields[field.lower()] = frame.copy()
        fields[field.lower()].loc[pd.Timestamp("2026-10-12")] = frame.iloc[-1] * 1.001
    save_snapshot(MarketPanel(**fields), snapshot)
    status = run_v25_live_update(
        snapshot=snapshot, as_of="2026-10-12", output_dir=segment,
        eligibility_receipt=VALIDATION,
        candidate_state_path=segment / STATE_NAMES[0], spy_state_path=segment / STATE_NAMES[1],
        matched_state_path=segment / STATE_NAMES[2], evidence_path=segment / "evidence-next.json",
        status_path=segment / "status-next.json",
    )
    forward = status["forward_evidence"]
    assert forward["forward_sessions"] == 1
    assert forward["initial_allocations"] == 1 and forward["filled_rebalances"] == 0
    assert forward["gates"]["all_accounts_same_order_path"]
    assert forward["live_confirmed"] is False


def test_segment_cannot_reset_a_contiguous_or_unchanged_chain(tmp_path, old_chain) -> None:
    with pytest.raises(ValueError, match="不得任意重置"):
        prepare_v25_live_segment(
            tmp_path / "new", **old_chain, observed_at=datetime(2026, 8, 30, tzinfo=UTC),
        )
    assert not (tmp_path / "new").exists()


def test_segment_rejects_a_backdated_snapshot_without_persisting_it(tmp_path, old_chain) -> None:
    with pytest.raises(ValueError, match="最後 bar"):
        prepare_v25_live_segment(
            tmp_path / "new", **old_chain, observed_at=NOW,
            snapshot=ROOT / "artifacts/snapshot_v25_vanguard_20060701_20260731_6cf44e63.zip",
        )
    assert not (tmp_path / "new").exists()
    assert not list(tmp_path.glob(".v25-segment-*"))


def test_segment_rejects_a_corrupt_old_receipt_chain(tmp_path, old_chain) -> None:
    ledger = old_chain["ledger_path"]
    ledger.write_text(ledger.read_text().replace('"sequence": 1,', '"sequence": 999,', 1))
    with pytest.raises(ValueError, match="雜湊不符"):
        prepare_v25_live_segment(tmp_path / "new", **old_chain, observed_at=NOW)
    assert not (tmp_path / "new").exists()


def test_segment_rejects_an_existing_destination(tmp_path, old_chain) -> None:
    destination = tmp_path / "new"
    destination.mkdir()
    (destination / "keep").write_bytes(b"unchanged")
    with pytest.raises(ValueError, match="拒絕覆寫"):
        prepare_v25_live_segment(destination, **old_chain, observed_at=NOW)
    assert (destination / "keep").read_bytes() == b"unchanged"


def test_activated_segment_keeps_the_original_chain_and_zero_count_initial_state() -> None:
    expected = {
        "paper_v25_state.json": "52e384155fb26eca584b11df1b1e012743c2a013bded0e18a80259ac336a8166",
        "paper_v25_spy_state.json": "6a9e450fe7ea53fa6b74c4f74d58be0cae3a672abfd4d9fd490d1a7654cab795",
        "paper_v25_matched_state.json": "c49870f7e91502feab0990af127876c6eb23e3abaca993ce8b5fee7d8ccbf149",
        LEDGER_NAME: "af35829dedbf0b0d979abd61295cdf37bd841e56ebe0d599754600a720965a7b",
    }
    for name, digest in expected.items():
        assert hashlib.sha256((ARCHIVED_PRIOR / name).read_bytes()).hexdigest() == digest
    assert verify_v25_reference_ledger(ARCHIVED_PRIOR / LEDGER_NAME)["receipts"] == 15
    initial = ARCHIVED_PRIOR.parent
    for name in STATE_NAMES:
        state = json.loads((initial / name).read_text())
        assert state["as_of"] == state["started_at"] == "2026-10-09"
        assert len(state["equity_curve"]) == 1
        assert state["cash"] == state["initial_cash"] == 100_000.0
        assert not state["order_history"] and not state["transactions"] and not state["holdings"]
        assert state["observation_segment"]["inherited_forward_sessions"] == 0
        assert state["observation_segment"]["backfilled_forward_sessions"] == 0
    active = json.loads((ROOT / "artifacts/paper_v25_state.json").read_text())
    assert active["equity_curve"][0]["date"] == "2026-10-09"
    assert active["observation_segment"] == json.loads((ROOT / "artifacts/v25_live_segment.json").read_text())


def test_live_update_rejects_segment_metadata_drift_before_fetch_or_write(tmp_path) -> None:
    copied = {}
    for name in STATE_NAMES:
        copied[name] = tmp_path / name
        copied[name].write_bytes((ROOT / "artifacts" / name).read_bytes())
    spy = json.loads(copied[STATE_NAMES[1]].read_text())
    spy["observation_segment"]["id"] = "another-segment"
    copied[STATE_NAMES[1]].write_text(json.dumps(spy))
    before = {name: path.read_bytes() for name, path in copied.items()}
    with pytest.raises(ValueError, match="觀察段不同步"):
        run_v25_live_update(
            snapshot="must-not-be-read.zip", as_of=NOW, eligibility_receipt=VALIDATION,
            candidate_state_path=copied[STATE_NAMES[0]], spy_state_path=copied[STATE_NAMES[1]],
            matched_state_path=copied[STATE_NAMES[2]],
        )
    assert {name: path.read_bytes() for name, path in copied.items()} == before


def test_live_audit_rejects_a_hidden_segment_restart() -> None:
    site = json.loads((ROOT / "artifacts/site_data.json").read_text())
    states = [json.loads((ROOT / "artifacts" / name).read_text()) for name in STATE_NAMES]
    site["research_pipeline"]["growth_gold_diversification"]["paper"].pop("observation_segment")
    audit = audit_v25_live_reference(site, *states, now=NOW)
    assert not audit["integrity_ok"]
    assert any("觀察段" in error for error in audit["errors"])


@pytest.mark.parametrize("always_missing", [False, True])
def test_live_fetch_retries_real_panels_without_filling_a_historical_vug_hole(
    tmp_path, monkeypatch, current_panel, always_missing,
) -> None:
    import usfddk.v25_live as live

    broken = MarketPanel(**{field.lower(): frame.copy() for field, frame in current_panel.field_map().items()})
    broken.close.loc["2026-08-28", "VUG"] = np.nan
    calls = []

    def fetch(*args, **kwargs):
        calls.append((args, kwargs))
        return broken if always_missing or len(calls) == 1 else current_panel

    monkeypatch.setattr(live, "fetch_yfinance", fetch)
    arguments = dict(
        as_of=NOW, output_dir=tmp_path, eligibility_receipt=VALIDATION,
        candidate_state_path=tmp_path / STATE_NAMES[0], spy_state_path=tmp_path / STATE_NAMES[1],
        matched_state_path=tmp_path / STATE_NAMES[2], evidence_path=tmp_path / "evidence.json",
        status_path=tmp_path / "status.json",
    )
    if always_missing:
        with pytest.raises(ValueError, match="VUG.*2026-08-28.*Close.*拒絕補值"):
            run_v25_live_update(**arguments)
        assert len(calls) == 3
        assert not list(tmp_path.glob("*.zip"))
        assert not list(tmp_path.glob("*state.json"))
    else:
        status = run_v25_live_update(**arguments)
        assert len(calls) == 2
        restored, _ = load_snapshot(status["snapshot"]["path"])
        assert restored.close.loc["2026-08-28", "VUG"] == pytest.approx(
            current_panel.close.loc["2026-08-28", "VUG"]
        )
        assert status["forward_evidence"]["forward_sessions"] == 0
        assert len(list(tmp_path.glob("*.zip"))) == 1
