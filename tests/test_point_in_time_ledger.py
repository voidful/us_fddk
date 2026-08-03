from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd

from usfddk.point_in_time_ledger import (
    MANIFEST_POLICY_VALUES,
    REQUIRED_COLUMNS,
    PointInTimeRequirements,
    audit_point_in_time_bundle,
)

ROOT = Path(__file__).resolve().parents[1]
FIXTURE_REQUIREMENTS = PointInTimeRequirements(
    start="2026-07-29",
    end="2026-07-31",
    min_daily_members=2,
    max_daily_members=2,
    min_member_price_coverage=1.0,
)


def _frame(name: str, rows: list[dict[str, object]]) -> pd.DataFrame:
    return pd.DataFrame(rows, columns=REQUIRED_COLUMNS[name])


def _write_bundle(tmp_path: Path) -> Path:
    bundle = tmp_path / "authorized-pit-fixture"
    bundle.mkdir()
    tables = {
        "security_master.csv": _frame(
            "security_master.csv",
            [
                {
                    "security_id": "SEC1",
                    "company_id": "CO1",
                    "security_type": "common_stock",
                    "share_class": "A",
                    "country_of_incorporation": "US",
                    "currency": "USD",
                },
                {
                    "security_id": "SEC2",
                    "company_id": "CO2",
                    "security_type": "common_stock",
                    "share_class": "single",
                    "country_of_incorporation": "US",
                    "currency": "USD",
                },
            ],
        ),
        "identifier_history.csv": _frame(
            "identifier_history.csv",
            [
                {
                    "security_id": "SEC1",
                    "ticker": "AAA",
                    "exchange": "XNYS",
                    "cusip": "000000001",
                    "isin": "",
                    "effective_from": "2020-01-01",
                    "effective_to": "",
                    "known_at": "2019-12-31T20:00:00Z",
                },
                {
                    "security_id": "SEC2",
                    "ticker": "BBB",
                    "exchange": "XNAS",
                    "cusip": "000000002",
                    "isin": "",
                    "effective_from": "2020-01-01",
                    "effective_to": "",
                    "known_at": "2019-12-31T20:00:00Z",
                },
            ],
        ),
        "membership_history.csv": _frame(
            "membership_history.csv",
            [
                {
                    "index_id": "SP500",
                    "security_id": "SEC1",
                    "effective_from": "2026-07-29",
                    "effective_to": "",
                    "announced_at": "2026-07-28T20:00:00Z",
                    "source_record_id": "MEM1",
                },
                {
                    "index_id": "SP500",
                    "security_id": "SEC2",
                    "effective_from": "2026-07-29",
                    "effective_to": "",
                    "announced_at": "2026-07-28T20:00:00Z",
                    "source_record_id": "MEM2",
                },
            ],
        ),
        "trading_calendar.csv": _frame(
            "trading_calendar.csv",
            [
                {
                    "session": day,
                    "exchange": "XNYS",
                    "open_at": f"{day}T13:30:00Z",
                    "close_at": f"{day}T20:00:00Z",
                }
                for day in ("2026-07-29", "2026-07-30", "2026-07-31")
            ],
        ),
        "daily_prices.csv": _frame(
            "daily_prices.csv",
            [
                {
                    "security_id": security_id,
                    "session": day,
                    "open_raw": price,
                    "high_raw": price + 1,
                    "low_raw": price - 1,
                    "close_raw": price + 0.5,
                    "volume": 1_000_000,
                    "cash_distribution": 0,
                    "split_factor": 1,
                    "total_return_factor": 1.005,
                    "source_status": "observed",
                }
                for security_id, base in (("SEC1", 100), ("SEC2", 200))
                for offset, day in enumerate(("2026-07-29", "2026-07-30", "2026-07-31"))
                for price in (base + offset,)
            ],
        ),
        "corporate_actions.csv": _frame("corporate_actions.csv", []),
        "classification_history.csv": _frame(
            "classification_history.csv",
            [
                {
                    "security_id": security_id,
                    "scheme": "GICS",
                    "sector_code": sector,
                    "industry_code": industry,
                    "effective_from": "2020-01-01",
                    "effective_to": "",
                    "known_at": "2019-12-31T20:00:00Z",
                    "source_record_id": f"CLASS-{security_id}",
                }
                for security_id, sector, industry in (
                    ("SEC1", "45", "4510"),
                    ("SEC2", "40", "4010"),
                )
            ],
        ),
        "security_outcomes.csv": _frame(
            "security_outcomes.csv",
            [
                {
                    "source_record_id": source_record_id,
                    "security_id": security_id,
                    "membership_effective_to": "",
                    "outcome_type": "still_member",
                    "last_trade_date": "",
                    "exit_effective_date": "",
                    "delisting_return": "",
                    "cash_consideration": "",
                    "successor_security_id": "",
                    "reason_code": "",
                    "known_at": "2026-07-31T20:00:00Z",
                }
                for source_record_id, security_id in (("MEM1", "SEC1"), ("MEM2", "SEC2"))
            ],
        ),
    }
    file_receipts: dict[str, dict[str, object]] = {}
    for name, frame in tables.items():
        path = bundle / name
        frame.to_csv(path, index=False, lineterminator="\n")
        file_receipts[name] = {
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "rows": len(frame),
        }
    manifest = {
        "schema_version": 1,
        "provider": "authorized-test-provider",
        "provider_product": "point-in-time-test-product",
        "license_attestation": {
            "authorized_for_local_research": True,
            "raw_redistribution_allowed": False,
            "attested_at": "2026-08-03T18:40:00Z",
            "reference": "test-only",
        },
        "exported_at": "2026-08-03T18:39:00Z",
        "first_imported_at": "2026-08-03T18:40:00Z",
        "as_of_date": "2026-07-31",
        "currency": "USD",
        "timezone": "America/New_York",
        **MANIFEST_POLICY_VALUES,
        "transform_version": "fixture-v1",
        "files": file_receipts,
    }
    (bundle / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return bundle


def _refresh_receipt(bundle: Path, name: str) -> None:
    manifest_path = bundle / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    path = bundle / name
    manifest["files"][name] = {
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "rows": len(pd.read_csv(path)),
    }
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def _audit(bundle: Path) -> dict:
    return audit_point_in_time_bundle(
        bundle,
        root=ROOT,
        requirements=FIXTURE_REQUIREMENTS,
    )


def test_valid_fixture_passes_all_twenty_data_gates(tmp_path: Path) -> None:
    result = _audit(_write_bundle(tmp_path))

    assert result["gate_summary"] == {"passed": 20, "total": 20, "all_passed": True}
    assert result["status"] == "point_in_time_data_contract_passed_backtest_not_run"
    assert result["formal_backtest_authorized"] is True
    assert result["formal_backtest_completed"] is False
    assert result["paper"]["authorized"] is False
    assert result["paper"]["state"] == "all_cash"
    assert result["real_money_action_usd"] == 0


def test_missing_bundle_fails_closed_but_preserves_frozen_protocol() -> None:
    result = audit_point_in_time_bundle(None, root=ROOT)

    assert result["gate_summary"]["passed"] == 1
    assert result["gates"]["04_preregistration_order"]["passed"] is True
    assert result["formal_backtest_authorized"] is False
    assert result["paper"]["positions"] == []


def test_manifest_hash_tampering_is_rejected(tmp_path: Path) -> None:
    bundle = _write_bundle(tmp_path)
    with (bundle / "daily_prices.csv").open("a", encoding="utf-8") as handle:
        handle.write("SEC1,2026-08-01,1,1,1,1,1,0,1,1,observed\n")

    result = _audit(bundle)

    assert result["gates"]["03_hash_and_row_receipts"]["passed"] is False
    assert result["gate_summary"]["all_passed"] is False


def test_current_constituent_backfill_timestamp_is_rejected(tmp_path: Path) -> None:
    bundle = _write_bundle(tmp_path)
    path = bundle / "membership_history.csv"
    frame = pd.read_csv(path, dtype=str, keep_default_na=False)
    frame.loc[0, "announced_at"] = "2026-08-01T20:00:00Z"
    frame.to_csv(path, index=False, lineterminator="\n")
    _refresh_receipt(bundle, path.name)

    result = _audit(bundle)

    assert result["gates"]["07_membership_availability"]["passed"] is False
    assert result["formal_backtest_authorized"] is False


def test_overlapping_ticker_reuse_is_rejected(tmp_path: Path) -> None:
    bundle = _write_bundle(tmp_path)
    path = bundle / "identifier_history.csv"
    frame = pd.read_csv(path, dtype=str, keep_default_na=False)
    frame.loc[1, ["ticker", "exchange"]] = ["AAA", "XNYS"]
    frame.to_csv(path, index=False, lineterminator="\n")
    _refresh_receipt(bundle, path.name)

    result = _audit(bundle)

    assert result["gates"]["06_identifier_history"]["passed"] is False


def test_missing_official_xnys_session_is_rejected(tmp_path: Path) -> None:
    bundle = _write_bundle(tmp_path)
    path = bundle / "trading_calendar.csv"
    frame = pd.read_csv(path, dtype=str, keep_default_na=False)
    frame = frame[frame["session"] != "2026-07-30"]
    frame.to_csv(path, index=False, lineterminator="\n")
    _refresh_receipt(bundle, path.name)

    result = _audit(bundle)

    assert result["gates"]["09_fixed_20_year_calendar"]["passed"] is False
    assert result["formal_backtest_authorized"] is False


def test_distribution_without_corporate_action_is_rejected(tmp_path: Path) -> None:
    bundle = _write_bundle(tmp_path)
    path = bundle / "daily_prices.csv"
    frame = pd.read_csv(path, dtype=str, keep_default_na=False)
    frame.loc[0, "cash_distribution"] = 0.5
    frame.to_csv(path, index=False, lineterminator="\n")
    _refresh_receipt(bundle, path.name)

    result = _audit(bundle)

    assert result["gates"]["14_corporate_actions"]["passed"] is False


def test_removed_security_requires_post_removal_trading_evidence(tmp_path: Path) -> None:
    bundle = _write_bundle(tmp_path)
    membership_path = bundle / "membership_history.csv"
    memberships = pd.read_csv(membership_path, dtype=str, keep_default_na=False)
    memberships.loc[0, "effective_to"] = "2026-08-01"
    memberships.to_csv(membership_path, index=False, lineterminator="\n")
    _refresh_receipt(bundle, membership_path.name)

    outcome_path = bundle / "security_outcomes.csv"
    outcomes = pd.read_csv(outcome_path, dtype=str, keep_default_na=False)
    outcomes.loc[0, "membership_effective_to"] = "2026-08-01"
    outcomes.loc[0, "outcome_type"] = "removed_continues"
    outcomes.to_csv(outcome_path, index=False, lineterminator="\n")
    _refresh_receipt(bundle, outcome_path.name)

    result = _audit(bundle)

    assert result["gates"]["15_outcome_coverage"]["passed"] is True
    assert result["gates"]["16_permanent_exit_economics"]["passed"] is False


def test_permanent_exit_without_economic_return_is_rejected(tmp_path: Path) -> None:
    bundle = _write_bundle(tmp_path)
    path = bundle / "security_outcomes.csv"
    frame = pd.read_csv(path, dtype=str, keep_default_na=False)
    frame.loc[0, "outcome_type"] = "bankrupt"
    frame.loc[0, "last_trade_date"] = "2026-07-31"
    frame.loc[0, "exit_effective_date"] = "2026-07-31"
    frame.loc[0, "reason_code"] = "BANKRUPTCY"
    frame.to_csv(path, index=False, lineterminator="\n")
    _refresh_receipt(bundle, path.name)

    result = _audit(bundle)

    assert result["gates"]["16_permanent_exit_economics"]["passed"] is False
    assert result["paper"]["authorized"] is False


def test_price_after_permanent_exit_is_rejected_as_ghost_data(tmp_path: Path) -> None:
    bundle = _write_bundle(tmp_path)
    membership_path = bundle / "membership_history.csv"
    memberships = pd.read_csv(membership_path, dtype=str, keep_default_na=False)
    memberships.loc[0, "effective_to"] = "2026-07-31"
    memberships.to_csv(membership_path, index=False, lineterminator="\n")
    _refresh_receipt(bundle, membership_path.name)
    path = bundle / "security_outcomes.csv"
    frame = pd.read_csv(path, dtype=str, keep_default_na=False)
    frame.loc[0, "membership_effective_to"] = "2026-07-31"
    frame.loc[0, "outcome_type"] = "delisted"
    frame.loc[0, "last_trade_date"] = "2026-07-30"
    frame.loc[0, "exit_effective_date"] = "2026-07-31"
    frame.loc[0, "delisting_return"] = -0.5
    frame.loc[0, "reason_code"] = "DELIST"
    frame.to_csv(path, index=False, lineterminator="\n")
    _refresh_receipt(bundle, path.name)

    result = _audit(bundle)

    assert result["gates"]["16_permanent_exit_economics"]["passed"] is True
    assert result["gates"]["17_no_post_exit_prices"]["passed"] is False
    assert result["formal_backtest_authorized"] is False
