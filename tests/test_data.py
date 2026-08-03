from __future__ import annotations

import zipfile

import pandas as pd

from usfddk.data import (
    load_snapshot,
    market_data_freshness_schedule,
    most_recent_us_session,
    save_snapshot,
    validate_panel,
)


def test_contract_and_snapshot_roundtrip(synthetic_panel, tmp_path):
    contract = validate_panel(
        synthetic_panel,
        required=("SPY", "SHY", "^VIX"),
        require_fresh=False,
    )
    assert contract.ok, contract.errors
    path = tmp_path / "snapshot.zip"
    manifest = save_snapshot(synthetic_panel, path, contract=contract)
    restored, loaded_manifest = load_snapshot(path)
    assert restored.close.shape == synthetic_panel.close.shape
    assert restored.close.index.equals(synthetic_panel.close.index)
    assert list(restored.close.columns) == sorted(synthetic_panel.close.columns)
    assert manifest["files"] == loaded_manifest["files"]


def test_snapshot_rejects_unknown_members(synthetic_panel, tmp_path):
    path = tmp_path / "snapshot.zip"
    save_snapshot(synthetic_panel, path)
    with zipfile.ZipFile(path, "a") as archive:
        archive.writestr("unexpected.txt", "x")
    try:
        load_snapshot(path)
    except ValueError as exc:
        assert "快照成員不符" in str(exc)
    else:
        raise AssertionError("corrupt archive was accepted")


def test_contract_catches_ohlc_violation(synthetic_panel):
    broken = synthetic_panel.high.copy()
    broken.iloc[-1, 0] = synthetic_panel.close.iloc[-1, 0] * 0.5
    panel = synthetic_panel.__class__(
        synthetic_panel.open,
        broken,
        synthetic_panel.low,
        synthetic_panel.close,
        synthetic_panel.volume,
    )
    result = validate_panel(panel, require_fresh=False)
    assert not result.ok
    assert any("OHLC" in item for item in result.errors)


def test_freshness_schedule_uses_next_exchange_session_close():
    schedule = market_data_freshness_schedule("2026-07-31", vendor_grace_hours=6)
    assert schedule["next_expected_session"] == "2026-08-03"
    close = pd.Timestamp(schedule["next_session_close_utc"])
    due = pd.Timestamp(schedule["refresh_due_at_utc"])
    assert due - close == pd.Timedelta(hours=6)


def test_most_recent_session_uses_completed_new_york_close_not_taipei_date():
    # 2026-08-04 10:00 in Taipei is after Monday's US close but before Tuesday's.
    assert most_recent_us_session(pd.Timestamp("2026-08-04T02:00:00Z")) == pd.Timestamp(
        "2026-08-03"
    )
    assert most_recent_us_session(pd.Timestamp("2026-08-04T21:00:00Z")) == pd.Timestamp(
        "2026-08-04"
    )


def test_most_recent_session_before_close_stays_on_prior_session():
    assert most_recent_us_session(pd.Timestamp("2026-08-03T19:00:00Z")) == pd.Timestamp(
        "2026-07-31"
    )
