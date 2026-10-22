from __future__ import annotations

import copy
import hashlib
import json
from datetime import UTC, timedelta
from pathlib import Path

import exchange_calendars as xcals
import pytest

import usfddk.form4_forward_strategy_kernel as kernel
from usfddk.form4_forward_strategy_kernel import (
    COMPARISON_FAMILY,
    GLOBAL_TRIALS_AFTER,
    Form4ForwardStrategyError,
    audit_round46_kernel_contract,
    make_genesis_prior_state,
    run_form4_forward_strategy,
    validate_public_aggregate_progress,
)

ROOT = Path(__file__).resolve().parents[1]
SHA = "a" * 64
NAMESPACE = "f" * 64


def _token(domain: str, label: str) -> str:
    return f"hmac-sha256:v1:{domain}:{hashlib.sha256(label.encode()).hexdigest()}"


def _canonical_sha256(value: object) -> str:
    raw = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode()
    return hashlib.sha256(raw).hexdigest()


def _seal_daily_receipts(sessions: list[dict], pit_rows: list[dict]) -> None:
    by_day: dict[str, list[dict]] = {}
    for row in pit_rows:
        by_day.setdefault(row["session"], []).append(row)
    for session in sessions:
        if not session["session_complete"]:
            session["daily_completeness_receipt_sha256"] = None
            session["pit_receipt_sha256"] = None
            session["integrity_outage"] = False
            continue
        rows = sorted(
            by_day.get(session["session"], []),
            key=lambda row: (row["security_token"], row["session"]),
        )
        pit_receipt = _canonical_sha256(rows)
        session["pit_receipt_sha256"] = pit_receipt
        session["daily_completeness_receipt_sha256"] = _canonical_sha256(
            {
                "session": session["session"],
                "open_at": session["open_at"],
                "close_at": session["close_at"],
                "pit_receipt_sha256": pit_receipt,
                "pit_row_count": len(rows),
                "integrity_outage": session["integrity_outage"],
            }
        )


def _set_planned(sessions: list[dict], count: int) -> None:
    for session in sessions[-count:]:
        session["session_complete"] = False
        session["daily_completeness_receipt_sha256"] = None
        session["pit_receipt_sha256"] = None
        session["integrity_outage"] = False


def _z(value) -> str:
    return value.to_pydatetime().astimezone(UTC).replace(microsecond=0).isoformat().replace(
        "+00:00", "Z"
    )


def _calendar(count: int = 285) -> list[dict]:
    calendar = xcals.get_calendar("XNYS")
    sessions = calendar.sessions_in_range("2025-01-02", "2027-08-10")[:count]
    rows = [
        {
            "session": session.date().isoformat(),
            "exchange": "XNYS",
            "open_at": _z(calendar.session_open(session)),
            "close_at": _z(calendar.session_close(session)),
            "session_complete": True,
            "source_receipt_sha256": SHA,
            "daily_completeness_receipt_sha256": "",
            "pit_receipt_sha256": "",
            "integrity_outage": False,
        }
        for session in sessions
    ]
    _seal_daily_receipts(rows, [])
    return rows


def _pit(
    sessions: list[dict],
    security: str,
    issuer: str,
    *,
    close_bias: int = 0,
) -> list[dict]:
    rows = []
    gics = _token("gics", "technology")
    share_class = _token("share-class", f"class-{security}")
    for index, session in enumerate(sessions):
        if not session["session_complete"]:
            continue
        close = 100 + close_bias + index
        rows.append(
            {
                "security_token": security,
                "issuer_token": issuer,
                "session": session["session"],
                "mapping_known_at": session["open_at"],
                "mapping_evidence_sha256": SHA,
                "eligibility_known_at": session["open_at"],
                "eligibility_evidence_sha256": SHA,
                "market_data_known_at": session["close_at"],
                "source_receipt_sha256": SHA,
                "point_in_time_verified": True,
                "sp500_eligible": True,
                "gics_token": gics,
                "share_class_token": share_class,
                "most_liquid_eligible_share_class": True,
                "fractional_shares_supported": True,
                "open_raw": str(close - 1),
                "close_raw": str(close),
                "volume": 1_000_000,
                "split_factor": "1",
                "cash_distribution": "0",
                "future_adjusted": False,
                "source_status": "observed",
                "total_return_session_count": index + 1,
                "market_cap_decile": 5,
                "adv_decile": 8,
                "settlement_verified": False,
                "settlement_terms_sha256": None,
            }
        )
    _seal_daily_receipts(sessions, rows)
    return rows


def _event(
    sessions: list[dict],
    *,
    label: str,
    issuer: str,
    security: str,
    known_at: str,
    transaction_date: str,
    dollars: int = 60_000,
    form_type: str = "4",
    action: str = "original",
    event_id: str | None = None,
    accession: str | None = None,
    capital: str | None = None,
) -> dict:
    event = event_id or _token("economic-event", f"event-{label}")
    return {
        "source_scope": ["sec_form_4"],
        "source_type": "sec_form_4",
        "form_type": form_type,
        "first_observed_basis": "prospective_first_observed_externally_anchored",
        "first_observed_at": known_at,
        "external_anchor_verified": True,
        "external_anchor_at": known_at,
        "external_anchor_sha256": SHA,
        "known_at": known_at,
        "source_receipt_sha256": SHA,
        "tokenization_receipt_sha256": SHA,
        "issuer_token": issuer,
        "security_token": security,
        "accession_token": accession or _token("accession", f"accession-{label}"),
        "economic_event_id": event,
        "row_lineage_token": _token("row-lineage", f"lineage-{label}-{action}"),
        "effective_version_id": _token("effective-version", f"version-{label}-{action}"),
        "effective_version_known_at": known_at,
        "effective_version_evidence_sha256": SHA,
        "capital_group_token": capital or _token("capital-group", f"capital-{label}"),
        "capital_group_known_at": known_at,
        "capital_group_evidence_sha256": SHA,
        "independence_status": "verified_independent",
        "pit_mapping_known_at": known_at,
        "pit_mapping_evidence_sha256": SHA,
        "pit_eligibility_known_at": known_at,
        "pit_eligibility_evidence_sha256": SHA,
        "role_set": ["director"],
        "direct_or_indirect": "D",
        "table": "I",
        "security_type": "non_derivative_common_stock",
        "transaction_code": "P",
        "acquired_disposed": "A",
        "economic_semantics": "open_or_private_purchase",
        "shares": "1000",
        "filed_price": str(dollars // 1000),
        "transaction_date": transaction_date,
        "equity_swap": False,
        "correction_action": action,
        "corrects_economic_event_id": event if action in {"replace", "cancel"} else None,
    }


def _bundle(*, event_count: int = 2, count: int = 285) -> dict:
    sessions = _calendar(count)
    monitor_index = 251
    monitor = sessions[monitor_index]["close_at"]
    known = (
        __import__("datetime").datetime.fromisoformat(monitor.replace("Z", "+00:00"))
        + timedelta(seconds=1)
    ).isoformat().replace("+00:00", "Z")
    issuer = _token("issuer", "issuer-main")
    security = _token("security", "security-main")
    transaction_date = sessions[monitor_index + 1]["session"]
    events = [
        _event(
            sessions,
            label=str(index),
            issuer=issuer,
            security=security,
            known_at=known,
            transaction_date=transaction_date,
        )
        for index in range(event_count)
    ]
    return {
        "normalized_rows": events,
        "xnys_sessions": sessions,
        "pit_daily_rows": _pit(sessions, security, issuer),
        "monitor_started_at": monitor,
        "prior_decision_records": [],
        "prior_control_records": [],
        "prior_ledger_state": make_genesis_prior_state(NAMESPACE),
    }


def _run(bundle: dict) -> dict:
    return run_form4_forward_strategy(**bundle)


def _zero_signal_bundle(count: int) -> dict:
    sessions = _calendar(count)
    monitor = (
        __import__("datetime").datetime.fromisoformat(
            sessions[0]["open_at"].replace("Z", "+00:00")
        )
        - timedelta(seconds=1)
    ).isoformat().replace("+00:00", "Z")
    return {
        "normalized_rows": [],
        "xnys_sessions": sessions,
        "pit_daily_rows": [],
        "monitor_started_at": monitor,
        "prior_decision_records": [],
        "prior_control_records": [],
        "prior_ledger_state": make_genesis_prior_state(NAMESPACE),
    }


def _error(bundle: dict, code: str) -> None:
    with pytest.raises(Form4ForwardStrategyError) as caught:
        _run(bundle)
    assert caught.value.code == code


def test_two_independent_accessions_close_once_and_schedule_d_plus_one_to_ten() -> None:
    bundle = _bundle()
    result = _run(bundle)
    assert len(result["decision_records"]) == 1
    decision = result["decision_records"][0]["payload"]
    sessions = bundle["xnys_sessions"]
    assert decision["decision_session"] == sessions[252]["session"]
    assert decision["trade_session"] == sessions[253]["session"]
    assert decision["exit_session"] == sessions[262]["session"]
    assert decision["holding_sessions"] == 10
    assert decision["fractional_shares"] is True
    clusters = [
        row for row in result["control_records"] if row["record_type"] == "cluster_closed"
    ]
    assert len(clusters) == 1
    assert clusters[0]["payload"]["status"] == "closed_allocated"
    assert clusters[0]["payload"]["distinct_capital_groups"] == 2
    assert clusters[0]["payload"]["distinct_accessions"] == 2
    completions = [
        row for row in result["control_records"] if row["record_type"] == "position_completed"
    ]
    assert completions[0]["payload"]["completion_type"] == "round_trip_completed"
    assert result["aggregate_progress"]["completed_round_trips"] == 1


def test_singleton_accumulates_until_second_group_first_crosses_gate() -> None:
    bundle = _bundle(event_count=1)
    sessions = bundle["xnys_sessions"]
    second_known = (
        __import__("datetime").datetime.fromisoformat(
            sessions[252]["close_at"].replace("Z", "+00:00")
        )
        + timedelta(seconds=1)
    ).isoformat().replace("+00:00", "Z")
    first = bundle["normalized_rows"][0]
    bundle["normalized_rows"].append(
        _event(
            sessions,
            label="late",
            issuer=first["issuer_token"],
            security=first["security_token"],
            known_at=second_known,
            transaction_date=first["transaction_date"],
        )
    )
    result = _run(bundle)
    assert result["decision_records"][0]["payload"]["decision_session"] == sessions[253]["session"]
    assert len([r for r in result["control_records"] if r["record_type"] == "cluster_closed"]) == 1


def test_latest_evidence_clock_delays_d_and_future_planned_clock_does_not_need_market_data() -> None:
    bundle = _bundle()
    sessions = bundle["xnys_sessions"]
    late_capital = (
        __import__("datetime").datetime.fromisoformat(
            sessions[252]["close_at"].replace("Z", "+00:00")
        )
        + timedelta(seconds=1)
    ).isoformat().replace("+00:00", "Z")
    for row in bundle["normalized_rows"]:
        row["capital_group_known_at"] = late_capital
    _set_planned(sessions, 10)
    bundle["pit_daily_rows"] = bundle["pit_daily_rows"][:-10]

    result = _run(bundle)
    assert result["decision_records"][0]["payload"]["decision_session"] == sessions[253]["session"]
    assert result["decision_records"][0]["payload"]["trade_session"] == sessions[254]["session"]


def test_pit_known_at_equal_to_close_moves_decision_to_the_next_session() -> None:
    bundle = _bundle()
    sessions = bundle["xnys_sessions"]
    for row in bundle["normalized_rows"]:
        row["pit_mapping_known_at"] = sessions[252]["close_at"]
    result = _run(bundle)
    assert result["decision_records"][0]["payload"]["decision_session"] == sessions[253]["session"]


def test_latest_complete_session_can_schedule_exit_and_exact_d_plus_twenty_cooldown() -> None:
    sessions = _calendar(285)
    _set_planned(sessions, 20)
    monitor = sessions[263]["close_at"]
    known = (
        __import__("datetime").datetime.fromisoformat(monitor.replace("Z", "+00:00"))
        + timedelta(seconds=1)
    ).isoformat().replace("+00:00", "Z")
    issuer = _token("issuer", "latest-issuer")
    security = _token("security", "latest-security")
    bundle = {
        "normalized_rows": [
            _event(
                sessions,
                label=str(index),
                issuer=issuer,
                security=security,
                known_at=known,
                transaction_date=sessions[264]["session"],
            )
            for index in range(2)
        ],
        "xnys_sessions": sessions,
        "pit_daily_rows": _pit(sessions[:265], security, issuer),
        "monitor_started_at": monitor,
        "prior_decision_records": [],
        "prior_control_records": [],
        "prior_ledger_state": make_genesis_prior_state(NAMESPACE),
    }
    result = _run(bundle)
    decision = result["decision_records"][0]["payload"]
    assert decision["decision_session"] == sessions[264]["session"]
    assert decision["trade_session"] == sessions[265]["session"]
    assert decision["exit_session"] == sessions[274]["session"]
    cluster = next(
        record for record in result["control_records"] if record["record_type"] == "cluster_closed"
    )
    assert cluster["payload"]["cooldown_through_session"] == sessions[284]["session"]


def test_create_once_ledgers_are_idempotent_and_prefix_tamper_fails() -> None:
    bundle = _bundle()
    first = _run(bundle)
    replay = copy.deepcopy(bundle)
    replay["prior_decision_records"] = first["decision_records"]
    replay["prior_control_records"] = first["control_records"]
    replay["prior_ledger_state"] = first["next_ledger_state"]
    assert _run(replay) == first

    tampered = copy.deepcopy(replay)
    tampered["prior_control_records"][0]["payload"]["comparison_id"] = "spy_buy_hold"
    _error(tampered, "form4_strategy_ledger_invalid")


def test_namespace_swap_cannot_preserve_or_replay_chain_heads() -> None:
    bundle = _bundle()
    first = _run(bundle)
    other_genesis = make_genesis_prior_state("e" * 64)
    assert (
        other_genesis["decision_chain_head_sha256"]
        != make_genesis_prior_state(NAMESPACE)["decision_chain_head_sha256"]
    )

    replay = copy.deepcopy(bundle)
    replay["prior_decision_records"] = first["decision_records"]
    replay["prior_control_records"] = first["control_records"]
    replay["prior_ledger_state"] = copy.deepcopy(first["next_ledger_state"])
    replay["prior_ledger_state"]["namespace_genesis_sha256"] = "e" * 64
    replay["prior_ledger_state"]["state_sha256"] = _canonical_sha256(
        {
            key: value
            for key, value in replay["prior_ledger_state"].items()
            if key != "state_sha256"
        }
    )
    _error(replay, "form4_strategy_ledger_invalid")


def test_4a_replace_accepts_new_accession_cancel_removes_and_consumed_stays_consumed() -> None:
    bundle = _bundle(event_count=1)
    sessions = bundle["xnys_sessions"]
    original = bundle["normalized_rows"][0]
    amendment_known = (
        __import__("datetime").datetime.fromisoformat(
            sessions[252]["close_at"].replace("Z", "+00:00")
        )
        + timedelta(seconds=1)
    ).isoformat().replace("+00:00", "Z")
    replacement = _event(
        sessions,
        label="replacement",
        issuer=original["issuer_token"],
        security=original["security_token"],
        known_at=amendment_known,
        transaction_date=original["transaction_date"],
        dollars=70_000,
        form_type="4/A",
        action="replace",
        event_id=original["economic_event_id"],
        accession=_token("accession", "replacement-accession"),
        capital=original["capital_group_token"],
    )
    second = _event(
        sessions,
        label="replacement-second",
        issuer=original["issuer_token"],
        security=original["security_token"],
        known_at=amendment_known,
        transaction_date=original["transaction_date"],
    )
    bundle["normalized_rows"].extend([replacement, second])
    result = _run(bundle)
    assert result["decision_records"][0]["payload"]["purchase_dollars"] == "130000"
    cluster = next(r for r in result["control_records"] if r["record_type"] == "cluster_closed")
    assert cluster["payload"]["distinct_accessions"] == 2

    cancelled = _bundle(event_count=1)
    original = cancelled["normalized_rows"][0]
    cancel = _event(
        cancelled["xnys_sessions"],
        label="cancel",
        issuer=original["issuer_token"],
        security=original["security_token"],
        known_at=amendment_known,
        transaction_date=original["transaction_date"],
        form_type="4/A",
        action="cancel",
        event_id=original["economic_event_id"],
        accession=_token("accession", "cancel-accession"),
        capital=original["capital_group_token"],
    )
    cancelled["normalized_rows"].extend([cancel, second])
    assert _run(cancelled)["decision_records"] == []

    consumed = _bundle()
    original = consumed["normalized_rows"][0]
    consumed_replace = copy.deepcopy(replacement)
    consumed_replace["issuer_token"] = original["issuer_token"]
    consumed_replace["security_token"] = original["security_token"]
    consumed_replace["economic_event_id"] = original["economic_event_id"]
    consumed_replace["corrects_economic_event_id"] = original["economic_event_id"]
    consumed_replace["capital_group_token"] = original["capital_group_token"]
    consumed["normalized_rows"].append(consumed_replace)
    consumed_result = _run(consumed)
    activated = [
        record
        for record in consumed_result["control_records"]
        if record["record_type"] == "normalized_row_activated"
        and record["payload"]["correction_action"] == "replace"
    ]
    assert activated[0]["payload"]["consumed_event_immutable"] is True
    assert len(consumed_result["decision_records"]) == 1


@pytest.mark.parametrize(
    ("mutate", "code"),
    [
        (
            lambda row: row.update({"congress_member": "x"}),
            "form4_strategy_congress_forbidden",
        ),
        (
            lambda row: row.update({"accession_number": "0000123456-26-000001"}),
            "form4_strategy_raw_identifier_forbidden",
        ),
        (
            lambda row: row.update({"security_token": "a" * 64}),
            "form4_strategy_token_invalid",
        ),
        (
            lambda row: row.update({"external_anchor_verified": False}),
            "form4_strategy_prospective_evidence_invalid",
        ),
        (
            lambda row: row.update({"independence_status": "unresolved"}),
            "form4_strategy_capital_independence_invalid",
        ),
        (
            lambda row: row.update({"economic_semantics": "open_market_purchase"}),
            "form4_strategy_event_semantics_invalid",
        ),
        (
            lambda row: row.update({"filed_price": "NaN"}),
            "form4_strategy_event_semantics_invalid",
        ),
    ],
)
def test_event_mutations_fail_with_stable_codes(mutate, code: str) -> None:
    bundle = _bundle()
    mutate(bundle["normalized_rows"][0])
    _error(bundle, code)


def test_same_accession_or_same_capital_group_cannot_cross_gate() -> None:
    bundle = _bundle()
    bundle["normalized_rows"][1]["accession_token"] = bundle["normalized_rows"][0][
        "accession_token"
    ]
    result = _run(bundle)
    assert result["decision_records"] == []

    bundle = _bundle()
    bundle["normalized_rows"][1]["capital_group_token"] = bundle["normalized_rows"][0][
        "capital_group_token"
    ]
    result = _run(bundle)
    assert result["decision_records"] == []


def test_future_adjusted_price_and_missing_raw_entry_fail_closed() -> None:
    bundle = _bundle()
    bundle["pit_daily_rows"][252]["future_adjusted"] = True
    _error(bundle, "form4_strategy_pit_invalid")

    bundle = _bundle()
    bundle["pit_daily_rows"][253]["source_status"] = "suspended"
    bundle["pit_daily_rows"][253]["open_raw"] = "0"
    bundle["pit_daily_rows"][253]["close_raw"] = "0"
    bundle["pit_daily_rows"][253]["volume"] = 0
    _error(bundle, "form4_strategy_execution_outcome_invalid")


def test_public_aggregate_has_no_tokens_dates_lists_or_performance() -> None:
    public = _run(_bundle())["public_status"]
    assert validate_public_aggregate_progress(public) == public
    rendered = str(public)
    assert "hmac-sha256" not in rendered
    assert "2025-" not in rendered
    assert "performance_present': False" in rendered
    assert public["real_money_action_usd"] == 0
    assert public["paper_positions"] == 0

    leaked = copy.deepcopy(public)
    leaked["candidate_list"] = [_token("security", "leak")]
    with pytest.raises(Form4ForwardStrategyError) as caught:
        validate_public_aggregate_progress(leaked)
    assert caught.value.code == "form4_strategy_public_boundary_invalid"

    for mutation in (
        {"status": "invented_status"},
        {"ticker": "FAKE"},
        {"name": "Raw Person"},
    ):
        invalid = copy.deepcopy(public)
        invalid.update(mutation)
        invalid["manifest_sha256"] = _canonical_sha256(
            {key: value for key, value in invalid.items() if key != "manifest_sha256"}
        )
        with pytest.raises(Form4ForwardStrategyError) as caught:
            validate_public_aggregate_progress(invalid)
        assert caught.value.code == "form4_strategy_public_boundary_invalid"


def test_daily_completeness_proves_zero_signal_and_outage_or_missing_receipt_stops() -> None:
    clean = _run(_zero_signal_bundle(504))
    sessions = [
        record for record in clean["control_records"] if record["record_type"] == "session_closed"
    ]
    assert len(sessions) == 504
    assert all(record["payload"]["daily_completeness_verified"] for record in sessions)
    assert all(record["payload"]["pit_receipt_verified"] for record in sessions)
    assert all(record["payload"]["zero_signal_session"] for record in sessions)
    assert clean["aggregate_progress"]["readout_status"] == (
        "insufficient_power_no_performance_readout"
    )

    outage = _zero_signal_bundle(504)
    outage["xnys_sessions"][100]["integrity_outage"] = True
    _seal_daily_receipts(outage["xnys_sessions"], [])
    outage_result = _run(outage)
    assert outage_result["aggregate_progress"]["readout_status"] == "stopped_no_readout"
    assert outage_result["public_status"]["status"] == "stopped_no_readout"
    assert outage_result["aggregate_progress"]["integrity_failure_sessions"] == 1

    early_outage = _zero_signal_bundle(101)
    early_outage["xnys_sessions"][100]["integrity_outage"] = True
    _seal_daily_receipts(early_outage["xnys_sessions"], [])
    early_result = _run(early_outage)
    assert early_result["aggregate_progress"]["readout_status"] == "stopped_no_readout"
    assert early_result["public_status"]["status"] == "stopped_no_readout"
    early_session = next(
        record
        for record in early_result["control_records"]
        if record["record_type"] == "session_closed"
        and record["payload"]["prospective_ordinal"] == 101
    )
    assert early_session["payload"]["daily_completeness_verified"] is False
    assert early_session["payload"]["integrity_outage"] is True
    assert early_session["payload"]["zero_signal_session"] is False

    for receipt_field in (
        "daily_completeness_receipt_sha256",
        "pit_receipt_sha256",
    ):
        missing = _zero_signal_bundle(504)
        missing["xnys_sessions"][100][receipt_field] = None
        missing_result = _run(missing)
        assert missing_result["aggregate_progress"]["readout_status"] == "stopped_no_readout"
        assert (
            missing_result["aggregate_progress"]["integrity_complete_through_session_504"]
            is False
        )


def test_terminal_cohort_rejects_d515_even_after_sufficient_d504_snapshot(monkeypatch) -> None:
    monkeypatch.setattr(kernel, "MIN_COMPLETED_POSITIONS", 0)
    monkeypatch.setattr(kernel, "MIN_DISTINCT_COMPLETED_ISSUERS", 0)
    at_514 = _run(_zero_signal_bundle(514))
    assert at_514["public_status"]["status"] == "eligible_for_pre_frozen_readout_engine"

    _error(_zero_signal_bundle(515), "form4_strategy_create_once_violation")


def test_comparison_family_trials_and_current_zero_state_are_explicit() -> None:
    audit = audit_round46_kernel_contract(root=ROOT)
    assert audit["fixed_controls"]["comparison_family"] == list(COMPARISON_FAMILY)
    assert audit["fixed_controls"]["global_trials_after"] == GLOBAL_TRIALS_AFTER == 6_295
    assert audit["fixed_controls"]["returns_calculated"] is False
    assert audit["fixed_controls"]["control_assignments_complete"] is False
    assert audit["state_at_freeze"]["real_row_count"] == 0
    assert audit["state_at_freeze"]["performance_present"] is False
    assert audit["state_at_freeze"]["paper_positions"] == 0
    assert audit["state_at_freeze"]["real_money_action_usd"] == 0


def test_504_stops_signals_and_514_only_checks_completed_sample_no_returns() -> None:
    sessions = _calendar(520)
    monitor = (
        __import__("datetime").datetime.fromisoformat(
            sessions[0]["open_at"].replace("Z", "+00:00")
        )
        - timedelta(seconds=1)
    ).isoformat().replace("+00:00", "Z")
    bundle = {
        "normalized_rows": [],
        "xnys_sessions": sessions[:504],
        "pit_daily_rows": [],
        "monitor_started_at": monitor,
        "prior_decision_records": [],
        "prior_control_records": [],
        "prior_ledger_state": make_genesis_prior_state(NAMESPACE),
    }
    at_504 = _run(bundle)["aggregate_progress"]
    assert at_504["readout_status"] == "insufficient_power_no_performance_readout"
    assert at_504["performance_readout_generated"] is False

    bundle["xnys_sessions"] = sessions[:514]
    _error(bundle, "form4_strategy_create_once_violation")
