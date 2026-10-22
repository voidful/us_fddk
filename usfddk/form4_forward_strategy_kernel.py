from __future__ import annotations

import hashlib
import json
import re
from collections import defaultdict
from collections.abc import Mapping, Sequence
from copy import deepcopy
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal, InvalidOperation
from fractions import Fraction
from pathlib import Path
from typing import Any

import exchange_calendars as xcals
import pandas as pd

PROTOCOL_PATH = "docs/SHORT_TERM_FORM4_FORWARD_STRATEGY_EVIDENCE_PROTOCOL.md"
AUTHORIZATION_RECEIPT_PATH = (
    "artifacts/short_term_form4_forward_strategy_evidence_protocol_receipt.json"
)
WORKFLOW_PATH = ".github/workflows/form4-round46-forward-strategy-ci.yml"
GLOBAL_TRIALS_BEFORE = 6_287
TRIAL_INCREMENT = 8
GLOBAL_TRIALS_AFTER = 6_295

KERNEL_SCHEMA = "us_fddk.short_term_form4_forward_strategy_kernel.v1"
DECISION_LEDGER_SCHEMA = "us_fddk.short_term_form4_forward_decision_entry.v1"
CONTROL_LEDGER_SCHEMA = "us_fddk.short_term_form4_forward_control_entry.v1"
AGGREGATE_SCHEMA = "us_fddk.short_term_form4_forward_aggregate_progress.v1"
PUBLIC_STATUS_SCHEMA = "us_fddk.short_term_form4_forward_public_status.v1"
PUBLIC_STATUS_VALUES = frozenset(
    {
        "collecting_no_readout",
        "stopped_no_readout",
        "insufficient_power_no_performance_readout",
        "eligible_pending_fixed_maturation_embargo",
        "eligible_for_pre_frozen_readout_engine",
    }
)
PRIOR_STATE_SCHEMA = "us_fddk.short_term_form4_forward_prior_state.v1"
KNOWN_AT_BASIS = "prospective_first_observed_externally_anchored"
SOURCE_SCOPE = ["sec_form_4"]
COMPARISON_FAMILY = (
    "qqq_buy_hold",
    "spy_buy_hold",
    "pit_eligible_equal_weight_monthly",
    "form4_cluster_unconfirmed",
    "price_volume_only_matched",
    "single_actor_purchase_confirmed",
    "non_signal_code_confirmed",
    "issuer_month_actor_permutation",
)
PERMUTATION_SEED = 41_202_608
SLOT_COUNT = 10
HOLDING_SESSIONS = 10
COOLDOWN_SESSIONS = 20
MAX_PLANNED_SESSIONS = COOLDOWN_SESSIONS
CLUSTER_CALENDAR_DAYS = 20
MIN_CAPITAL_GROUPS = 2
MIN_ACCESSIONS = 2
MIN_ACCESSION_DOLLARS = Decimal("10000")
MIN_CLUSTER_DOLLARS = Decimal("100000")
MIN_PRICE = Decimal("5")
MIN_MEDIAN_ADV = Decimal("20000000")
MIN_TOTAL_RETURN_SESSIONS = 252
SIGNAL_SESSION_LIMIT = 504
MATURITY_SESSION = 514
MIN_COMPLETED_POSITIONS = 100
MIN_DISTINCT_COMPLETED_ISSUERS = 50
FRACTIONAL_SHARES = True
GENESIS_SHA256 = "0" * 64

FORM4_FORWARD_STRATEGY_ERROR_CODES = (
    "form4_strategy_schema_invalid",
    "form4_strategy_token_invalid",
    "form4_strategy_token_collision",
    "form4_strategy_congress_forbidden",
    "form4_strategy_raw_identifier_forbidden",
    "form4_strategy_timestamp_invalid",
    "form4_strategy_prospective_evidence_invalid",
    "form4_strategy_source_receipt_invalid",
    "form4_strategy_event_semantics_invalid",
    "form4_strategy_amendment_invalid",
    "form4_strategy_capital_independence_invalid",
    "form4_strategy_calendar_invalid",
    "form4_strategy_pit_invalid",
    "form4_strategy_price_history_invalid",
    "form4_strategy_execution_clock_invalid",
    "form4_strategy_execution_outcome_invalid",
    "form4_strategy_slot_invalid",
    "form4_strategy_hold_period_invalid",
    "form4_strategy_cooldown_invalid",
    "form4_strategy_comparison_family_invalid",
    "form4_strategy_trial_ledger_invalid",
    "form4_strategy_ledger_invalid",
    "form4_strategy_create_once_violation",
    "form4_strategy_public_boundary_invalid",
    "form4_strategy_performance_forbidden",
    "form4_strategy_paper_forbidden",
    "form4_strategy_real_money_forbidden",
)

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_DECIMAL = re.compile(r"^(?:0|[1-9]\d*)(?:\.\d+)?$")
_RAW_ACCESSION = re.compile(r"(?<!\d)\d{10}-\d{2}-\d{6}(?!\d)")
_TOKEN_DOMAINS = {
    "issuer_token": "issuer",
    "security_token": "security",
    "accession_token": "accession",
    "economic_event_id": "economic-event",
    "corrects_economic_event_id": "economic-event",
    "row_lineage_token": "row-lineage",
    "effective_version_id": "effective-version",
    "capital_group_token": "capital-group",
    "gics_token": "gics",
    "share_class_token": "share-class",
}
_ALLOWED_ROLES = frozenset({"director", "officer", "ten_percent_owner"})
_FORCED_STATUSES = frozenset({"delisted", "cash_acquisition", "stock_acquisition"})
_STATUS_VALUES = frozenset({"observed", "suspended", *_FORCED_STATUSES})

_EVENT_KEYS = frozenset(
    {
        "source_scope",
        "source_type",
        "form_type",
        "first_observed_basis",
        "first_observed_at",
        "external_anchor_verified",
        "external_anchor_at",
        "external_anchor_sha256",
        "known_at",
        "source_receipt_sha256",
        "tokenization_receipt_sha256",
        "issuer_token",
        "security_token",
        "accession_token",
        "economic_event_id",
        "row_lineage_token",
        "effective_version_id",
        "effective_version_known_at",
        "effective_version_evidence_sha256",
        "capital_group_token",
        "capital_group_known_at",
        "capital_group_evidence_sha256",
        "independence_status",
        "pit_mapping_known_at",
        "pit_mapping_evidence_sha256",
        "pit_eligibility_known_at",
        "pit_eligibility_evidence_sha256",
        "role_set",
        "direct_or_indirect",
        "table",
        "security_type",
        "transaction_code",
        "acquired_disposed",
        "economic_semantics",
        "shares",
        "filed_price",
        "transaction_date",
        "equity_swap",
        "correction_action",
        "corrects_economic_event_id",
    }
)
_CALENDAR_KEYS = frozenset(
    {
        "session",
        "exchange",
        "open_at",
        "close_at",
        "session_complete",
        "source_receipt_sha256",
        "daily_completeness_receipt_sha256",
        "pit_receipt_sha256",
        "integrity_outage",
    }
)
_PIT_KEYS = frozenset(
    {
        "security_token",
        "issuer_token",
        "session",
        "mapping_known_at",
        "mapping_evidence_sha256",
        "eligibility_known_at",
        "eligibility_evidence_sha256",
        "market_data_known_at",
        "source_receipt_sha256",
        "point_in_time_verified",
        "sp500_eligible",
        "gics_token",
        "share_class_token",
        "most_liquid_eligible_share_class",
        "fractional_shares_supported",
        "open_raw",
        "close_raw",
        "volume",
        "split_factor",
        "cash_distribution",
        "future_adjusted",
        "source_status",
        "total_return_session_count",
        "market_cap_decile",
        "adv_decile",
        "settlement_verified",
        "settlement_terms_sha256",
    }
)
_PUBLIC_STATUS_KEYS = frozenset(
    {
        "schema_version",
        "status",
        "today_action",
        "performance_present",
        "paper_authorized",
        "paper_positions",
        "real_money_action_usd",
        "manifest_sha256",
    }
)
_LEDGER_KEYS = frozenset(
    {
        "schema_version",
        "ledger",
        "ordinal",
        "record_type",
        "payload",
        "parent_input_sha256",
        "previous_entry_sha256",
        "entry_sha256",
    }
)
_PRIOR_STATE_KEYS = frozenset(
    {
        "schema_version",
        "namespace_genesis_sha256",
        "decision_record_count",
        "decision_chain_head_sha256",
        "control_record_count",
        "control_chain_head_sha256",
        "state_sha256",
    }
)


class Form4ForwardStrategyError(RuntimeError):
    """Fail-closed Round46 strategy-kernel error with a stable code."""

    def __init__(self, code: str, detail: str):
        if code not in FORM4_FORWARD_STRATEGY_ERROR_CODES:
            raise ValueError("unknown Form 4 forward-strategy error code")
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}")


def _fail(code: str, detail: str) -> None:
    raise Form4ForwardStrategyError(code, detail)


def _canonical_sha256(value: object, *, omit: str | None = None) -> str:
    if isinstance(value, Mapping) and omit is not None:
        value = {key: item for key, item in value.items() if key != omit}
    try:
        raw = json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError):
        _fail("form4_strategy_schema_invalid", "value is not canonical JSON")
    return hashlib.sha256(raw).hexdigest()


def _ledger_genesis(namespace_genesis_sha256: str, ledger: str) -> str:
    return _canonical_sha256(
        {
            "namespace_genesis_sha256": namespace_genesis_sha256,
            "ledger": ledger,
            "schema_version": KERNEL_SCHEMA,
        }
    )


def _same_typed(left: object, right: object) -> bool:
    if type(left) is not type(right):
        return False
    if isinstance(right, Mapping):
        return set(left) == set(right) and all(_same_typed(left[key], right[key]) for key in right)
    if isinstance(right, list):
        return len(left) == len(right) and all(
            _same_typed(a, b) for a, b in zip(left, right, strict=True)
        )
    return left == right


def _exact(value: object, keys: frozenset[str], *, code: str, label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping) or not all(isinstance(key, str) for key in value):
        _fail(code, f"{label} must be an object with string keys")
    if set(value) != keys:
        _fail(code, f"{label} schema is not exact")
    return dict(value)


def _sha256(value: object, *, code: str = "form4_strategy_source_receipt_invalid") -> str:
    if not isinstance(value, str) or _SHA256.fullmatch(value) is None:
        _fail(code, "expected a lowercase SHA-256")
    return value


def _utc(value: object) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        _fail("form4_strategy_timestamp_invalid", "timestamp must be canonical whole-second UTC")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        _fail("form4_strategy_timestamp_invalid", "timestamp is not ISO-8601")
    if parsed.tzinfo is None or parsed.microsecond != 0:
        _fail("form4_strategy_timestamp_invalid", "timestamp is not whole-second UTC")
    normalized = parsed.astimezone(UTC)
    if normalized.isoformat().replace("+00:00", "Z") != value:
        _fail("form4_strategy_timestamp_invalid", "timestamp is not canonical UTC")
    return normalized


def _session_date(value: object) -> date:
    if not isinstance(value, str) or _DATE.fullmatch(value) is None:
        _fail("form4_strategy_calendar_invalid", "session/date must be canonical YYYY-MM-DD")
    try:
        parsed = date.fromisoformat(value)
    except ValueError:
        _fail("form4_strategy_calendar_invalid", "session/date is invalid")
    if parsed.isoformat() != value:
        _fail("form4_strategy_calendar_invalid", "session/date is not canonical")
    return parsed


def _decimal(value: object, *, positive: bool, code: str) -> Decimal:
    if not isinstance(value, str) or _DECIMAL.fullmatch(value) is None:
        _fail(code, "numeric values must be canonical decimal strings")
    try:
        parsed = Decimal(value)
    except InvalidOperation:
        _fail(code, "decimal value is invalid")
    if not parsed.is_finite() or (positive and parsed <= 0) or (not positive and parsed < 0):
        _fail(code, "decimal value is outside its closed range")
    return parsed


def _integer(value: object, *, minimum: int, code: str) -> int:
    if type(value) is not int or value < minimum:
        _fail(code, "integer value is outside its closed range")
    return value


def _token(value: object, field: str) -> str:
    domain = _TOKEN_DOMAINS[field]
    pattern = re.compile(rf"^hmac-sha256:v1:{re.escape(domain)}:[0-9a-f]{{64}}$")
    if not isinstance(value, str) or pattern.fullmatch(value) is None:
        _fail(
            "form4_strategy_token_invalid",
            f"{field} must be an upstream domain-separated HMAC-SHA256 token",
        )
    return value


def _walk(value: object) -> list[tuple[str | None, object]]:
    found: list[tuple[str | None, object]] = []
    if isinstance(value, Mapping):
        for key, item in value.items():
            found.append((str(key), item))
            found.extend(_walk(item))
    elif isinstance(value, list | tuple):
        for item in value:
            found.extend(_walk(item))
    return found


def _reject_forbidden_input(value: object) -> None:
    congress = ("congress", "legislator", "house_ptr", "senate_ptr", "politician")
    raw_keys = {
        "ticker",
        "symbol",
        "cik",
        "cusip",
        "isin",
        "accession",
        "accession_number",
        "issuer_name",
        "owner_name",
        "person_name",
        "address",
        "raw_path",
        "document_content",
    }
    performance = {
        "return",
        "returns",
        "nav",
        "sharpe",
        "sortino",
        "cagr",
        "drawdown",
        "alpha",
        "p_value",
        "performance_result",
    }
    for key, item in _walk(value):
        folded = "" if key is None else re.sub(r"[^a-z0-9]+", "_", key.casefold()).strip("_")
        if any(marker in folded for marker in congress):
            _fail("form4_strategy_congress_forbidden", "Congress/PTR fields are forbidden")
        if folded in raw_keys:
            _fail("form4_strategy_raw_identifier_forbidden", "raw identifier field is forbidden")
        if folded in performance or any(folded.endswith(f"_{marker}") for marker in performance):
            _fail("form4_strategy_performance_forbidden", "performance fields are forbidden")
        if isinstance(item, str):
            lowered = item.casefold()
            if any(marker in lowered for marker in congress):
                _fail("form4_strategy_congress_forbidden", "Congress/PTR values are forbidden")
            if _RAW_ACCESSION.search(item):
                _fail("form4_strategy_raw_identifier_forbidden", "raw accession is forbidden")


def _format_decimal(value: Decimal) -> str:
    rendered = format(value, "f")
    if "." in rendered:
        rendered = rendered.rstrip("0").rstrip(".")
    return rendered or "0"


@dataclass(frozen=True)
class _Session:
    value: dict[str, Any]
    day: date
    open_at: datetime
    close_at: datetime

    @property
    def complete(self) -> bool:
        return self.value["session_complete"] is True

    @property
    def integrity_ok(self) -> bool:
        return bool(
            self.complete
            and isinstance(self.value["daily_completeness_receipt_sha256"], str)
            and isinstance(self.value["pit_receipt_sha256"], str)
            and self.value["integrity_outage"] is False
        )


@dataclass(frozen=True)
class _Event:
    value: dict[str, Any]
    activation_index: int
    base_known_at: datetime
    transaction_day: date
    dollars: Decimal


@dataclass(frozen=True)
class _Pit:
    value: dict[str, Any]
    open_raw: Decimal
    close_raw: Decimal
    volume: int
    split_factor: Decimal
    cash_distribution: Decimal


def _validate_calendar(rows: Sequence[Mapping[str, Any]]) -> list[_Session]:
    if isinstance(rows, str | bytes) or not isinstance(rows, Sequence) or not rows:
        _fail("form4_strategy_calendar_invalid", "XNYS sessions must be a non-empty sequence")
    parsed: list[_Session] = []
    calendar = xcals.get_calendar("XNYS")
    for item in rows:
        row = _exact(item, _CALENDAR_KEYS, code="form4_strategy_calendar_invalid", label="session")
        if row["exchange"] != "XNYS" or type(row["session_complete"]) is not bool:
            _fail("form4_strategy_calendar_invalid", "session must be an exact XNYS clock row")
        day = _session_date(row["session"])
        opened = _utc(row["open_at"])
        closed = _utc(row["close_at"])
        _sha256(row["source_receipt_sha256"])
        if type(row["integrity_outage"]) is not bool:
            _fail("form4_strategy_calendar_invalid", "integrity_outage must be boolean")
        completeness_receipt = row["daily_completeness_receipt_sha256"]
        pit_receipt = row["pit_receipt_sha256"]
        if row["session_complete"]:
            for receipt in (completeness_receipt, pit_receipt):
                if receipt is not None:
                    _sha256(receipt)
        elif (
            completeness_receipt is not None
            or pit_receipt is not None
            or row["integrity_outage"] is not False
        ):
            _fail(
                "form4_strategy_calendar_invalid",
                "planned session cannot claim completeness, PIT receipt or outage",
            )
        stamp = pd.Timestamp(day.isoformat())
        if not calendar.is_session(stamp):
            _fail("form4_strategy_calendar_invalid", "non-XNYS session was supplied")
        expected_open = calendar.session_open(stamp).to_pydatetime().astimezone(UTC)
        expected_close = calendar.session_close(stamp).to_pydatetime().astimezone(UTC)
        if opened != expected_open or closed != expected_close or opened >= closed:
            _fail("form4_strategy_calendar_invalid", "XNYS open/close timestamp drifted")
        parsed.append(_Session(row, day, opened, closed))
    if [item.day for item in parsed] != sorted({item.day for item in parsed}):
        _fail("form4_strategy_calendar_invalid", "sessions are duplicate or non-increasing")
    expected = [
        stamp.date()
        for stamp in calendar.sessions_in_range(parsed[0].day.isoformat(), parsed[-1].day.isoformat())
    ]
    if [item.day for item in parsed] != expected:
        _fail("form4_strategy_calendar_invalid", "XNYS session sequence has a gap")
    flags = [item.complete for item in parsed]
    first_planned = next((index for index, complete in enumerate(flags) if not complete), len(parsed))
    if any(flags[first_planned:]) or len(parsed) - first_planned > MAX_PLANNED_SESSIONS:
        _fail(
            "form4_strategy_calendar_invalid",
            "calendar must be a complete prefix plus at most twenty official planned sessions",
        )
    return parsed


def _validate_pit_rows(
    rows: Sequence[Mapping[str, Any]],
    *,
    sessions: list[_Session],
) -> dict[tuple[str, str], _Pit]:
    if isinstance(rows, str | bytes) or not isinstance(rows, Sequence):
        _fail("form4_strategy_pit_invalid", "PIT rows must be a sequence")
    session_by_day = {item.day.isoformat(): item for item in sessions}
    calendar = xcals.get_calendar("XNYS")
    parsed: dict[tuple[str, str], _Pit] = {}
    token_domains: dict[str, str] = {}
    for item in rows:
        _reject_forbidden_input(item)
        row = _exact(item, _PIT_KEYS, code="form4_strategy_pit_invalid", label="PIT row")
        security = _token(row["security_token"], "security_token")
        issuer = _token(row["issuer_token"], "issuer_token")
        gics = _token(row["gics_token"], "gics_token")
        share_class = _token(row["share_class_token"], "share_class_token")
        for field, token in (
            ("security_token", security),
            ("issuer_token", issuer),
            ("gics_token", gics),
            ("share_class_token", share_class),
        ):
            prior = token_domains.setdefault(token, field)
            if prior != field:
                _fail("form4_strategy_token_collision", "token crossed semantic domains")
        day = _session_date(row["session"]).isoformat()
        if day not in session_by_day:
            _fail("form4_strategy_pit_invalid", "PIT row references an unknown session")
        session = session_by_day[day]
        mapping_known = _utc(row["mapping_known_at"])
        eligibility_known = _utc(row["eligibility_known_at"])
        market_known = _utc(row["market_data_known_at"])
        next_stamp = calendar.next_session(pd.Timestamp(day))
        next_open = calendar.session_open(next_stamp).to_pydatetime().astimezone(UTC)
        if not session.complete:
            _fail("form4_strategy_pit_invalid", "planned future sessions cannot contain PIT market rows")
        if (
            mapping_known > session.close_at
            or eligibility_known > session.close_at
            or not (session.close_at <= market_known < next_open)
        ):
            _fail("form4_strategy_pit_invalid", "PIT availability clock is not tradable at next open")
        for evidence in (
            "source_receipt_sha256",
            "mapping_evidence_sha256",
            "eligibility_evidence_sha256",
        ):
            _sha256(row[evidence])
        if (
            type(row["point_in_time_verified"]) is not bool
            or row["point_in_time_verified"] is not True
            or type(row["future_adjusted"]) is not bool
            or row["future_adjusted"] is not False
        ):
            _fail("form4_strategy_pit_invalid", "PIT/future-adjustment attestation failed")
        for key in (
            "sp500_eligible",
            "most_liquid_eligible_share_class",
            "fractional_shares_supported",
            "settlement_verified",
        ):
            if type(row[key]) is not bool:
                _fail("form4_strategy_pit_invalid", f"{key} must be boolean")
        status = row["source_status"]
        if not isinstance(status, str) or status not in _STATUS_VALUES:
            _fail("form4_strategy_pit_invalid", "source status is outside the closed set")
        opened = _decimal(row["open_raw"], positive=status == "observed", code="form4_strategy_pit_invalid")
        closed = _decimal(row["close_raw"], positive=status == "observed", code="form4_strategy_pit_invalid")
        volume = _integer(row["volume"], minimum=1 if status == "observed" else 0, code="form4_strategy_pit_invalid")
        split = _decimal(row["split_factor"], positive=True, code="form4_strategy_pit_invalid")
        distribution = _decimal(row["cash_distribution"], positive=False, code="form4_strategy_pit_invalid")
        total_sessions = _integer(row["total_return_session_count"], minimum=0, code="form4_strategy_pit_invalid")
        for decile in ("market_cap_decile", "adv_decile"):
            value = _integer(row[decile], minimum=1, code="form4_strategy_pit_invalid")
            if value > 10:
                _fail("form4_strategy_pit_invalid", f"{decile} is outside 1..10")
        terms = row["settlement_terms_sha256"]
        if status in _FORCED_STATUSES:
            if row["settlement_verified"] is not True:
                _fail("form4_strategy_execution_outcome_invalid", "forced settlement is unverified")
            _sha256(terms, code="form4_strategy_execution_outcome_invalid")
        elif row["settlement_verified"] is not False or terms is not None:
            _fail("form4_strategy_pit_invalid", "ordinary/suspended row invented settlement evidence")
        if total_sessions > sessions.index(session) + 1:
            _fail("form4_strategy_pit_invalid", "total-return history count exceeds available sessions")
        key = (security, day)
        if key in parsed:
            _fail("form4_strategy_pit_invalid", "duplicate security/session PIT row")
        parsed[key] = _Pit(row, opened, closed, volume, split, distribution)
    return parsed


def _first_close_after(sessions: list[_Session], instant: datetime) -> int:
    for index, session in enumerate(sessions):
        if session.close_at > instant:
            return index
    _fail("form4_strategy_execution_clock_invalid", "no complete XNYS close follows known-at")


def _validate_events(
    rows: Sequence[Mapping[str, Any]],
    *,
    sessions: list[_Session],
    monitor_started_at: datetime,
) -> list[_Event]:
    if isinstance(rows, str | bytes) or not isinstance(rows, Sequence):
        _fail("form4_strategy_schema_invalid", "normalized rows must be a sequence")
    parsed: list[_Event] = []
    lineage: set[str] = set()
    versions: set[str] = set()
    token_domains: dict[str, str] = {}
    for item in rows:
        _reject_forbidden_input(item)
        row = _exact(item, _EVENT_KEYS, code="form4_strategy_schema_invalid", label="normalized row")
        if row["source_scope"] != SOURCE_SCOPE or row["source_type"] != "sec_form_4":
            _fail("form4_strategy_schema_invalid", "source scope must be exactly SEC Form 4")
        form = row["form_type"]
        if form not in {"4", "4/A"}:
            _fail("form4_strategy_event_semantics_invalid", "form must be 4 or 4/A")
        tokens: dict[str, str] = {}
        for field in (
            "issuer_token",
            "security_token",
            "accession_token",
            "economic_event_id",
            "row_lineage_token",
            "effective_version_id",
            "capital_group_token",
        ):
            tokens[field] = _token(row[field], field)
            prior = token_domains.setdefault(tokens[field], field)
            if prior != field:
                _fail("form4_strategy_token_collision", "token crossed semantic domains")
        corrects = row["corrects_economic_event_id"]
        if corrects is not None:
            _token(corrects, "corrects_economic_event_id")
        if tokens["row_lineage_token"] in lineage or tokens["effective_version_id"] in versions:
            _fail("form4_strategy_token_collision", "row lineage/version token was reused")
        lineage.add(tokens["row_lineage_token"])
        versions.add(tokens["effective_version_id"])
        for key in (
            "external_anchor_sha256",
            "source_receipt_sha256",
            "tokenization_receipt_sha256",
            "capital_group_evidence_sha256",
            "effective_version_evidence_sha256",
            "pit_mapping_evidence_sha256",
            "pit_eligibility_evidence_sha256",
        ):
            _sha256(row[key])
        first_seen = _utc(row["first_observed_at"])
        anchored = _utc(row["external_anchor_at"])
        known = _utc(row["known_at"])
        version_known = _utc(row["effective_version_known_at"])
        capital_known = _utc(row["capital_group_known_at"])
        mapping_known = _utc(row["pit_mapping_known_at"])
        eligibility_known = _utc(row["pit_eligibility_known_at"])
        if (
            row["first_observed_basis"] != KNOWN_AT_BASIS
            or row["external_anchor_verified"] is not True
            or first_seen <= monitor_started_at
            or anchored < first_seen
            or known != anchored
            or version_known < known
        ):
            _fail(
                "form4_strategy_prospective_evidence_invalid",
                "row is not prospective first-observed evidence with a durable external anchor",
            )
        if row["independence_status"] != "verified_independent":
            _fail(
                "form4_strategy_capital_independence_invalid",
                "shared or unresolved capital cannot enter this strategy kernel",
            )
        roles = row["role_set"]
        if (
            type(roles) is not list
            or not roles
            or roles != sorted(set(roles))
            or not set(roles) <= _ALLOWED_ROLES
        ):
            _fail("form4_strategy_event_semantics_invalid", "role_set is not exact and eligible")
        if (
            row["table"] != "I"
            or row["security_type"] != "non_derivative_common_stock"
            or row["transaction_code"] != "P"
            or row["acquired_disposed"] != "A"
            or row["economic_semantics"] != "open_or_private_purchase"
            or row["equity_swap"] is not False
            or row["direct_or_indirect"] not in {"D", "I"}
        ):
            _fail("form4_strategy_event_semantics_invalid", "Form 4 purchase semantics drifted")
        shares = _decimal(row["shares"], positive=True, code="form4_strategy_event_semantics_invalid")
        price = _decimal(row["filed_price"], positive=True, code="form4_strategy_event_semantics_invalid")
        action = row["correction_action"]
        if action not in {"original", "replace", "cancel", "add"}:
            _fail("form4_strategy_amendment_invalid", "correction action is outside the closed set")
        if (
            (action == "original" and (form != "4" or corrects is not None))
            or (action == "add" and (form != "4/A" or corrects is not None))
            or (
                action in {"replace", "cancel"}
                and (form != "4/A" or corrects != tokens["economic_event_id"])
            )
        ):
            _fail("form4_strategy_amendment_invalid", "4/A correction mapping is not exact")
        transaction_day = _session_date(row["transaction_date"])
        base = max(known, capital_known, version_known, mapping_known, eligibility_known)
        activation = _first_close_after(sessions, base)
        parsed.append(_Event(row, activation, base, transaction_day, shares * price))
    parsed.sort(
        key=lambda event: (
            event.activation_index,
            event.base_known_at,
            event.value["row_lineage_token"],
        )
    )
    return parsed


def _append_record(
    records: list[dict[str, Any]],
    *,
    ledger: str,
    record_type: str,
    payload: Mapping[str, Any],
    parent_input: object,
    namespace_genesis_sha256: str,
) -> dict[str, Any]:
    previous = (
        records[-1]["entry_sha256"]
        if records
        else _ledger_genesis(namespace_genesis_sha256, ledger)
    )
    entry = {
        "schema_version": DECISION_LEDGER_SCHEMA if ledger == "decision" else CONTROL_LEDGER_SCHEMA,
        "ledger": ledger,
        "ordinal": len(records),
        "record_type": record_type,
        "payload": deepcopy(dict(payload)),
        "parent_input_sha256": _canonical_sha256(parent_input),
        "previous_entry_sha256": previous,
        "entry_sha256": "",
    }
    entry["entry_sha256"] = _canonical_sha256(entry, omit="entry_sha256")
    records.append(entry)
    return entry


def _validate_ledger(
    records: object,
    *,
    ledger: str,
    namespace_genesis_sha256: str,
) -> list[dict[str, Any]]:
    if isinstance(records, str | bytes) or not isinstance(records, Sequence):
        _fail("form4_strategy_ledger_invalid", "ledger must be a sequence")
    expected_schema = DECISION_LEDGER_SCHEMA if ledger == "decision" else CONTROL_LEDGER_SCHEMA
    result: list[dict[str, Any]] = []
    previous = _ledger_genesis(namespace_genesis_sha256, ledger)
    for ordinal, item in enumerate(records):
        row = _exact(item, _LEDGER_KEYS, code="form4_strategy_ledger_invalid", label="ledger entry")
        if (
            row["schema_version"] != expected_schema
            or row["ledger"] != ledger
            or type(row["ordinal"]) is not int
            or row["ordinal"] != ordinal
            or not isinstance(row["record_type"], str)
            or not isinstance(row["payload"], Mapping)
            or row["previous_entry_sha256"] != previous
        ):
            _fail("form4_strategy_ledger_invalid", "ledger schema/order/chain drifted")
        _sha256(row["parent_input_sha256"], code="form4_strategy_ledger_invalid")
        supplied = _sha256(row["entry_sha256"], code="form4_strategy_ledger_invalid")
        if supplied != _canonical_sha256(row, omit="entry_sha256"):
            _fail("form4_strategy_ledger_invalid", "ledger entry hash drifted")
        if row["payload"].get("performance_present") is not False:
            _fail("form4_strategy_performance_forbidden", "ledger cannot contain performance")
        previous = supplied
        result.append(deepcopy(row))
    return result


def make_genesis_prior_state(namespace_genesis_sha256: str) -> dict[str, Any]:
    namespace = _sha256(namespace_genesis_sha256, code="form4_strategy_ledger_invalid")
    state = {
        "schema_version": PRIOR_STATE_SCHEMA,
        "namespace_genesis_sha256": namespace,
        "decision_record_count": 0,
        "decision_chain_head_sha256": _ledger_genesis(namespace, "decision"),
        "control_record_count": 0,
        "control_chain_head_sha256": _ledger_genesis(namespace, "control"),
        "state_sha256": "",
    }
    state["state_sha256"] = _canonical_sha256(state, omit="state_sha256")
    return state


def _read_prior_state(value: Mapping[str, Any]) -> dict[str, Any]:
    state = _exact(value, _PRIOR_STATE_KEYS, code="form4_strategy_ledger_invalid", label="prior state")
    if state["schema_version"] != PRIOR_STATE_SCHEMA:
        _fail("form4_strategy_ledger_invalid", "prior state schema drifted")
    _sha256(state["namespace_genesis_sha256"], code="form4_strategy_ledger_invalid")
    supplied = _sha256(state["state_sha256"], code="form4_strategy_ledger_invalid")
    if supplied != _canonical_sha256(state, omit="state_sha256"):
        _fail("form4_strategy_ledger_invalid", "prior state hash drifted")
    return state


def _validate_prior_state(
    value: Mapping[str, Any],
    *,
    decisions: list[dict[str, Any]],
    controls: list[dict[str, Any]],
) -> dict[str, Any]:
    state = _read_prior_state(value)
    namespace = state["namespace_genesis_sha256"]
    expected = {
        "decision_record_count": len(decisions),
        "decision_chain_head_sha256": (
            decisions[-1]["entry_sha256"]
            if decisions
            else _ledger_genesis(namespace, "decision")
        ),
        "control_record_count": len(controls),
        "control_chain_head_sha256": (
            controls[-1]["entry_sha256"]
            if controls
            else _ledger_genesis(namespace, "control")
        ),
    }
    for key, item in expected.items():
        if not _same_typed(state[key], item):
            _fail("form4_strategy_create_once_violation", "trusted prior ledger head/count drifted")
    return state


def _median(values: Sequence[Decimal]) -> Decimal:
    ordered = sorted(values)
    size = len(ordered)
    if size == 0:
        _fail("form4_strategy_price_history_invalid", "median input is empty")
    middle = size // 2
    return ordered[middle] if size % 2 else (ordered[middle - 1] + ordered[middle]) / 2


def _daily_integrity_ok(
    session: _Session,
    *,
    pits: dict[tuple[str, str], _Pit],
) -> tuple[bool, list[dict[str, Any]]]:
    session_rows = [
        pit.value
        for (security, day), pit in sorted(pits.items())
        if day == session.day.isoformat()
    ]
    expected_pit = _canonical_sha256(session_rows)
    expected_completeness = _canonical_sha256(
        {
            "session": session.day.isoformat(),
            "open_at": session.value["open_at"],
            "close_at": session.value["close_at"],
            "pit_receipt_sha256": expected_pit,
            "pit_row_count": len(session_rows),
            "integrity_outage": session.value["integrity_outage"],
        }
    )
    return (
        session.integrity_ok
        and session.value["pit_receipt_sha256"] == expected_pit
        and session.value["daily_completeness_receipt_sha256"] == expected_completeness,
        session_rows,
    )


def _market_gate(
    security: str,
    issuer: str,
    index: int,
    *,
    sessions: list[_Session],
    pits: dict[tuple[str, str], _Pit],
) -> tuple[bool, dict[str, Any], Decimal]:
    if index < 20:
        _fail("form4_strategy_price_history_invalid", "D has fewer than 20 prior sessions")
    required = range(index - 20, index + 1)
    rows: list[_Pit] = []
    for position in required:
        key = (security, sessions[position].day.isoformat())
        if key not in pits:
            _fail("form4_strategy_price_history_invalid", "D/prior20 PIT row is missing")
        row = pits[key]
        if row.value["issuer_token"] != issuer or row.value["source_status"] != "observed":
            _fail("form4_strategy_price_history_invalid", "PIT identity/status drifted")
        rows.append(row)
    current = rows[-1]
    previous = rows[-2]
    if max(
        _utc(current.value["mapping_known_at"]),
        _utc(current.value["eligibility_known_at"]),
    ) >= sessions[index].close_at:
        _fail("form4_strategy_execution_clock_invalid", "D is not strictly after PIT known-at")
    prior_adv = [row.close_raw * row.volume for row in rows[:-1]]
    median_adv = _median(prior_adv)
    current_adv = current.close_raw * current.volume
    one_day_positive = (
        current.close_raw * current.split_factor + current.cash_distribution > previous.close_raw
    )
    pool = (
        current.value["sp500_eligible"] is True
        and current.value["most_liquid_eligible_share_class"] is True
        and current.value["fractional_shares_supported"] is True
        and current.close_raw > MIN_PRICE
        and median_adv >= MIN_MEDIAN_ADV
        and current.value["total_return_session_count"] >= MIN_TOTAL_RETURN_SESSIONS
    )
    confirmed = one_day_positive and current_adv > median_adv and pool
    evidence = {
        "one_day_total_return_positive": one_day_positive,
        "d_adv_above_prior20_median": current_adv > median_adv,
        "pit_pool_eligible": pool,
        "prior20_median_adv": _format_decimal(median_adv),
        "d_adv": _format_decimal(current_adv),
    }
    return confirmed, evidence, median_adv


def _comparison_hash() -> str:
    return _canonical_sha256(
        {
            "comparison_family": list(COMPARISON_FAMILY),
            "global_trials_before": GLOBAL_TRIALS_BEFORE,
            "trial_increment": TRIAL_INCREMENT,
            "global_trials_after": GLOBAL_TRIALS_AFTER,
        }
    )


def _aggregate_manifest(payload: Mapping[str, Any]) -> str:
    return _canonical_sha256({key: value for key, value in payload.items() if key != "manifest_sha256"})


def validate_public_aggregate_progress(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Validate the pre-readout redacted public status boundary."""

    public = _exact(
        payload,
        _PUBLIC_STATUS_KEYS,
        code="form4_strategy_public_boundary_invalid",
        label="public status",
    )
    for key, item in _walk(payload):
        if isinstance(item, list | tuple):
            _fail("form4_strategy_public_boundary_invalid", "public aggregate cannot contain lists")
        folded = "" if key is None else key.casefold()
        if (
            folded in {"ticker", "symbol", "cik", "cusip", "isin", "accession", "name", "date"}
            or folded.endswith(("_token", "_ticker", "_cik", "_accession", "_name", "_date", "_at"))
        ):
            _fail("form4_strategy_public_boundary_invalid", "public aggregate leaked identity/date fields")
        if isinstance(item, str):
            if _RAW_ACCESSION.search(item) or _DATE.fullmatch(item) or item.startswith("hmac-sha256:"):
                _fail("form4_strategy_public_boundary_invalid", "public aggregate leaked a value")
            if _SHA256.fullmatch(item) and (key is None or not key.endswith("sha256")):
                _fail("form4_strategy_public_boundary_invalid", "unlabelled hash in public aggregate")
    if public["schema_version"] != PUBLIC_STATUS_SCHEMA:
        _fail("form4_strategy_public_boundary_invalid", "public status schema drifted")
    if public["performance_present"] is not False:
        _fail("form4_strategy_performance_forbidden", "aggregate cannot contain performance")
    if (
        public["paper_authorized"] is not False
        or type(public["paper_positions"]) is not int
        or public["paper_positions"] != 0
    ):
        _fail("form4_strategy_paper_forbidden", "Paper state must remain exact zero")
    if type(public["real_money_action_usd"]) is not int or public["real_money_action_usd"] != 0:
        _fail("form4_strategy_real_money_forbidden", "real-money state must remain exact zero")
    if public["today_action"] != "今天不下單" or public["status"] not in PUBLIC_STATUS_VALUES:
        _fail("form4_strategy_public_boundary_invalid", "public status/action drifted")
    if public["manifest_sha256"] != _aggregate_manifest(public):
        _fail("form4_strategy_public_boundary_invalid", "aggregate manifest hash drifted")
    return deepcopy(public)


def run_form4_forward_strategy(
    *,
    normalized_rows: Sequence[Mapping[str, Any]],
    xnys_sessions: Sequence[Mapping[str, Any]],
    pit_daily_rows: Sequence[Mapping[str, Any]],
    monitor_started_at: str,
    prior_decision_records: Sequence[Mapping[str, Any]],
    prior_control_records: Sequence[Mapping[str, Any]],
    prior_ledger_state: Mapping[str, Any],
) -> dict[str, Any]:
    """Replay the frozen forward-only decision kernel without returns or orders."""

    monitor_start = _utc(monitor_started_at)
    unbound_prior_state = _read_prior_state(prior_ledger_state)
    namespace = unbound_prior_state["namespace_genesis_sha256"]
    prior_decisions = _validate_ledger(
        prior_decision_records,
        ledger="decision",
        namespace_genesis_sha256=namespace,
    )
    prior_controls = _validate_ledger(
        prior_control_records,
        ledger="control",
        namespace_genesis_sha256=namespace,
    )
    prior_state = _validate_prior_state(
        prior_ledger_state, decisions=prior_decisions, controls=prior_controls
    )
    sessions = _validate_calendar(xnys_sessions)
    pits = _validate_pit_rows(pit_daily_rows, sessions=sessions)
    events = _validate_events(
        normalized_rows,
        sessions=sessions,
        monitor_started_at=monitor_start,
    )
    first_prospective = _first_close_after(sessions, monitor_start)
    complete_count = next(
        (index for index, session in enumerate(sessions) if not session.complete), len(sessions)
    )
    prospective_count = max(complete_count - first_prospective, 0)

    decisions: list[dict[str, Any]] = []
    controls: list[dict[str, Any]] = []
    for trial_ordinal, comparison in enumerate(COMPARISON_FAMILY, start=1):
        _append_record(
            controls,
            ledger="control",
            record_type="comparison_family_reserved",
            payload={
                "comparison_id": comparison,
                "trial_ordinal": trial_ordinal,
                "assignment_status": "deferred_to_pre_frozen_control_assignment_engine",
                "permutation_seed": PERMUTATION_SEED if comparison == "issuer_month_actor_permutation" else None,
                "performance_present": False,
            },
            parent_input={"comparison_id": comparison, "comparison_family_sha256": _comparison_hash()},
            namespace_genesis_sha256=namespace,
        )
    warmup_rows = [
        pit.value
        for (security, day), pit in sorted(pits.items())
        if sessions[[item.day.isoformat() for item in sessions].index(day)].close_at <= monitor_start
    ]
    _append_record(
        controls,
        ledger="control",
        record_type="warmup_committed",
        payload={
            "calendar_session_count": first_prospective,
            "pit_row_count": len(warmup_rows),
            "warmup_manifest_sha256": _canonical_sha256(warmup_rows),
            "performance_present": False,
        },
        parent_input=warmup_rows,
        namespace_genesis_sha256=namespace,
    )

    arrivals: dict[int, list[_Event]] = defaultdict(list)
    for event in events:
        arrivals[event.activation_index].append(event)
    current: dict[str, _Event] = {}
    consumed: set[str] = set()
    issuer_cooldown: dict[str, int] = {}
    open_positions: list[dict[str, Any]] = []
    completed_issuers: set[str] = set()
    completed_round_trips = 0
    forced_settlements = 0
    unconfirmed = 0
    capacity_rejected = 0
    d504_completed_positions: int | None = None
    d504_completed_issuers: int | None = None
    d504_integrity_ok: bool | None = None
    integrity_breached = False
    integrity_failure_sessions = 0

    for index, session in enumerate(sessions):
        if not session.complete:
            break
        prospective_ordinal = index - first_prospective + 1
        if prospective_ordinal > MATURITY_SESSION:
            _fail(
                "form4_strategy_create_once_violation",
                "the fixed cohort is sealed at prospective session 514",
            )
        if prospective_ordinal > SIGNAL_SESSION_LIMIT and (
            d504_integrity_ok is not True
            or d504_completed_positions is None
            or d504_completed_positions < MIN_COMPLETED_POSITIONS
            or d504_completed_issuers is None
            or d504_completed_issuers < MIN_DISTINCT_COMPLETED_ISSUERS
        ):
            _fail(
                "form4_strategy_create_once_violation",
                "the terminal D504 stop/insufficient state cannot be extended",
            )
        session_integrity_ok, session_pits = _daily_integrity_ok(session, pits=pits)
        if prospective_ordinal >= 1 and not session_integrity_ok:
            integrity_breached = True
            integrity_failure_sessions += 1
        decisions_before_session = len(decisions)
        for event in arrivals.get(index, []):
            row = event.value
            event_id = row["economic_event_id"]
            action = row["correction_action"]
            existing = current.get(event_id)
            if action in {"original", "add"}:
                if existing is not None:
                    _fail("form4_strategy_amendment_invalid", "economic event was introduced twice")
                current[event_id] = event
            else:
                if existing is None:
                    _fail("form4_strategy_amendment_invalid", "4/A target does not exist")
                stable = (
                    "issuer_token",
                    "security_token",
                    "capital_group_token",
                    "transaction_date",
                )
                if any(existing.value[key] != row[key] for key in stable) or event.base_known_at <= existing.base_known_at:
                    _fail("form4_strategy_amendment_invalid", "4/A rewrote identity/time backwards")
                if event_id not in consumed:
                    if action == "replace":
                        current[event_id] = event
                    else:
                        del current[event_id]
            _append_record(
                controls,
                ledger="control",
                record_type="normalized_row_activated",
                payload={
                    "row_lineage_token": row["row_lineage_token"],
                    "economic_event_id": event_id,
                    "issuer_token": row["issuer_token"],
                    "activation_session": session.day.isoformat(),
                    "correction_action": action,
                    "consumed_event_immutable": event_id in consumed,
                    "performance_present": False,
                },
                parent_input=row,
                namespace_genesis_sha256=namespace,
            )

        still_open: list[dict[str, Any]] = []
        for position in open_positions:
            if index < position["trade_index"]:
                still_open.append(position)
                continue
            pit = pits.get((position["security_token"], session.day.isoformat()))
            if pit is None:
                if index <= position["exit_index"]:
                    _fail("form4_strategy_execution_outcome_invalid", "scheduled position PIT row is missing")
                still_open.append(position)
                continue
            status = pit.value["source_status"]
            if index == position["trade_index"] and status != "observed":
                _fail("form4_strategy_execution_outcome_invalid", "scheduled raw-open entry is unavailable")
            if status == "suspended":
                _fail("form4_strategy_execution_outcome_invalid", "suspension lacks an explicit settlement schedule")
            complete_type: str | None = None
            if status in _FORCED_STATUSES:
                complete_type = "forced_settlement_completed"
                forced_settlements += 1
            elif index == position["exit_index"]:
                complete_type = "round_trip_completed"
                completed_round_trips += 1
            if complete_type is None:
                still_open.append(position)
                continue
            completed_issuers.add(position["issuer_token"])
            _append_record(
                controls,
                ledger="control",
                record_type="position_completed",
                payload={
                    "decision_entry_sha256": position["decision_entry_sha256"],
                    "issuer_token": position["issuer_token"],
                    "security_token": position["security_token"],
                    "completion_session": session.day.isoformat(),
                    "scheduled_exit_session": sessions[position["exit_index"]].day.isoformat(),
                    "completion_type": complete_type,
                    "settlement_terms_sha256": pit.value["settlement_terms_sha256"],
                    "performance_present": False,
                },
                parent_input={"decision": position["decision_entry_sha256"], "pit": pit.value},
                namespace_genesis_sha256=namespace,
            )
        open_positions = still_open

        provisional: list[dict[str, Any]] = []
        if (
            1 <= prospective_ordinal <= SIGNAL_SESSION_LIMIT
            and not integrity_breached
            and session_integrity_ok
        ):
            issuer_events: dict[str, list[_Event]] = defaultdict(list)
            for event_id, event in current.items():
                if event_id in consumed:
                    continue
                if (session.day - event.transaction_day).days not in range(CLUSTER_CALENDAR_DAYS):
                    continue
                issuer_events[event.value["issuer_token"]].append(event)
            for issuer in sorted(issuer_events):
                if index <= issuer_cooldown.get(issuer, -1):
                    continue
                by_accession: dict[str, list[_Event]] = defaultdict(list)
                for event in issuer_events[issuer]:
                    by_accession[event.value["accession_token"]].append(event)
                qualified_accessions = {
                    accession: members
                    for accession, members in by_accession.items()
                    if sum((member.dollars for member in members), Decimal(0))
                    >= MIN_ACCESSION_DOLLARS
                }
                members = [member for group in qualified_accessions.values() for member in group]
                groups = {member.value["capital_group_token"] for member in members}
                dollars = sum((member.dollars for member in members), Decimal(0))
                if (
                    len(qualified_accessions) < MIN_ACCESSIONS
                    or len(groups) < MIN_CAPITAL_GROUPS
                    or dollars < MIN_CLUSTER_DOLLARS
                ):
                    continue
                securities = {member.value["security_token"] for member in members}
                if len(securities) != 1:
                    _fail("form4_strategy_pit_invalid", "issuer cluster maps to multiple securities")
                security = next(iter(securities))
                current_pit = pits.get((security, session.day.isoformat()))
                if current_pit is None:
                    _fail("form4_strategy_price_history_invalid", "D PIT row is missing")
                pit_clock = max(
                    _utc(current_pit.value["mapping_known_at"]),
                    _utc(current_pit.value["eligibility_known_at"]),
                )
                if session.close_at <= pit_clock:
                    continue
                if any(
                    member.value["pit_mapping_evidence_sha256"]
                    != current_pit.value["mapping_evidence_sha256"]
                    or member.value["pit_eligibility_evidence_sha256"]
                    != current_pit.value["eligibility_evidence_sha256"]
                    for member in members
                ):
                    _fail("form4_strategy_pit_invalid", "event/PIT evidence commitment drifted")
                confirmed, market, median_adv = _market_gate(
                    security, issuer, index, sessions=sessions, pits=pits
                )
                member_commitment = _canonical_sha256(
                    sorted(
                        (
                            member.value["economic_event_id"],
                            member.value["effective_version_id"],
                            member.value["accession_token"],
                            member.value["capital_group_token"],
                        )
                        for member in members
                    )
                )
                cluster_id = _canonical_sha256(
                    {
                        "issuer_token": issuer,
                        "decision_session": session.day.isoformat(),
                        "member_commitment_sha256": member_commitment,
                    }
                )
                provisional.append(
                    {
                        "issuer_token": issuer,
                        "security_token": security,
                        "members": members,
                        "breadth": len(groups),
                        "dollars": dollars,
                        "intensity": Fraction(dollars) / Fraction(median_adv),
                        "median_adv": median_adv,
                        "market": market,
                        "confirmed": confirmed,
                        "member_commitment_sha256": member_commitment,
                        "cluster_id_sha256": cluster_id,
                    }
                )
            provisional.sort(
                key=lambda item: (
                    -item["breadth"],
                    -item["intensity"],
                    -item["dollars"],
                    item["security_token"],
                )
            )
            available = SLOT_COUNT - len(open_positions)
            if available < 0:
                _fail("form4_strategy_slot_invalid", "active positions exceed ten slots")
            confirmed_seen = 0
            for cluster in provisional:
                if not cluster["confirmed"]:
                    status = "closed_unconfirmed"
                    unconfirmed += 1
                elif confirmed_seen < available:
                    status = "closed_allocated"
                    confirmed_seen += 1
                else:
                    status = "closed_capacity_rejected"
                    capacity_rejected += 1
                members = cluster["members"]
                for member in members:
                    consumed.add(member.value["economic_event_id"])
                issuer_cooldown[cluster["issuer_token"]] = index + COOLDOWN_SESSIONS
                cooldown_index = index + COOLDOWN_SESSIONS
                if cooldown_index >= len(sessions):
                    _fail(
                        "form4_strategy_cooldown_invalid",
                        "D+20 official planned session is absent",
                    )
                _append_record(
                    controls,
                    ledger="control",
                    record_type="cluster_closed",
                    payload={
                        "cluster_id_sha256": cluster["cluster_id_sha256"],
                        "issuer_token": cluster["issuer_token"],
                        "security_token": cluster["security_token"],
                        "decision_session": session.day.isoformat(),
                        "status": status,
                        "distinct_capital_groups": cluster["breadth"],
                        "distinct_accessions": len({m.value["accession_token"] for m in members}),
                        "purchase_dollars": _format_decimal(cluster["dollars"]),
                        "member_commitment_sha256": cluster["member_commitment_sha256"],
                        **cluster["market"],
                        "cooldown_through_session": sessions[cooldown_index].day.isoformat(),
                        "member_events_consumed": True,
                        "performance_present": False,
                    },
                    parent_input={
                        "members": [member.value for member in members],
                        "market": cluster["market"],
                    },
                    namespace_genesis_sha256=namespace,
                )
                if status != "closed_allocated":
                    continue
                trade_index = index + 1
                exit_index = trade_index + HOLDING_SESSIONS - 1
                if exit_index >= len(sessions):
                    # A decision may be scheduled before future sessions have arrived; XNYS dates
                    # are deterministic, but this replay returns only decisions whose full clock
                    # exists in the supplied contiguous calendar.
                    _fail("form4_strategy_hold_period_invalid", "D+10 session is absent")
                slot = next(
                    value
                    for value in range(SLOT_COUNT)
                    if value not in {position["slot_index"] for position in open_positions}
                )
                intensity = cluster["intensity"]
                decision = _append_record(
                    decisions,
                    ledger="decision",
                    record_type="position_scheduled",
                    payload={
                        "cluster_id_sha256": cluster["cluster_id_sha256"],
                        "issuer_token": cluster["issuer_token"],
                        "security_token": cluster["security_token"],
                        "member_commitment_sha256": cluster["member_commitment_sha256"],
                        "decision_session": session.day.isoformat(),
                        "trade_session": sessions[trade_index].day.isoformat(),
                        "exit_session": sessions[exit_index].day.isoformat(),
                        "slot_index": slot,
                        "breadth": cluster["breadth"],
                        "intensity_numerator": str(intensity.numerator),
                        "intensity_denominator": str(intensity.denominator),
                        "purchase_dollars": _format_decimal(cluster["dollars"]),
                        "fractional_shares": FRACTIONAL_SHARES,
                        "holding_sessions": HOLDING_SESSIONS,
                        "entry_price_basis": "next_session_raw_open",
                        "exit_price_basis": "tenth_session_raw_close_or_verified_forced_settlement",
                        "cost_contract": (
                            "four_real_asset_legs_10bps_primary_25_50bps_stress_"
                            "child_order_fixed_fee_usd_0.01_0.05"
                        ),
                        "performance_present": False,
                        "paper_authorized": False,
                        "real_money_action_usd": 0,
                    },
                    parent_input={"cluster": cluster["cluster_id_sha256"], "active_slots": len(open_positions)},
                    namespace_genesis_sha256=namespace,
                )
                open_positions.append(
                    {
                        "decision_entry_sha256": decision["entry_sha256"],
                        "issuer_token": cluster["issuer_token"],
                        "security_token": cluster["security_token"],
                        "slot_index": slot,
                        "trade_index": trade_index,
                        "exit_index": exit_index,
                    }
                )

        if prospective_ordinal >= 1:
            _append_record(
                controls,
                ledger="control",
                record_type="session_closed",
                payload={
                    "prospective_ordinal": prospective_ordinal,
                    "calendar_session": session.day.isoformat(),
                    "pit_row_count": len(session_pits),
                    "daily_completeness_verified": session_integrity_ok,
                    "pit_receipt_verified": session_integrity_ok,
                    "integrity_outage": session.value["integrity_outage"],
                    "candidate_cluster_count": len(provisional),
                    "new_decision_count": len(decisions) - decisions_before_session,
                    "zero_signal_session": (
                        not integrity_breached
                        and session_integrity_ok
                        and len(provisional) == 0
                    ),
                    "active_position_count": len(open_positions),
                    "new_signals_allowed": (
                        prospective_ordinal <= SIGNAL_SESSION_LIMIT
                        and not integrity_breached
                        and session_integrity_ok
                    ),
                    "performance_present": False,
                },
                parent_input={"session": session.value, "pit": session_pits},
                namespace_genesis_sha256=namespace,
            )
            if prospective_ordinal == SIGNAL_SESSION_LIMIT:
                d504_completed_positions = completed_round_trips + forced_settlements
                d504_completed_issuers = len(completed_issuers)
                d504_integrity_ok = not integrity_breached

    if not all(_same_typed(a, b) for a, b in zip(prior_decisions, decisions, strict=False)) or len(
        prior_decisions
    ) > len(decisions):
        _fail("form4_strategy_create_once_violation", "decision ledger is not an exact immutable prefix")
    if not all(_same_typed(a, b) for a, b in zip(prior_controls, controls, strict=False)) or len(
        prior_controls
    ) > len(controls):
        _fail("form4_strategy_create_once_violation", "control ledger is not an exact immutable prefix")

    decisions_at_limit = [
        item
        for item in decisions
        if item["payload"]["decision_session"]
        <= sessions[min(first_prospective + SIGNAL_SESSION_LIMIT - 1, len(sessions) - 1)].day.isoformat()
    ]
    sample_sufficient_at_504 = bool(
        d504_completed_positions is not None
        and d504_completed_positions >= MIN_COMPLETED_POSITIONS
        and d504_completed_issuers is not None
        and d504_completed_issuers >= MIN_DISTINCT_COMPLETED_ISSUERS
    )
    if integrity_breached:
        readout_status = "stopped_no_readout"
        eligibility_checked = prospective_count >= SIGNAL_SESSION_LIMIT
        eligible = False
    elif prospective_count < SIGNAL_SESSION_LIMIT:
        readout_status = "collecting_no_readout"
        eligibility_checked = False
        eligible = False
    elif not sample_sufficient_at_504:
        readout_status = "insufficient_power_no_performance_readout"
        eligibility_checked = True
        eligible = False
    elif prospective_count < MATURITY_SESSION:
        readout_status = "eligible_pending_fixed_maturation_embargo"
        eligibility_checked = True
        eligible = False
    else:
        if open_positions:
            _fail(
                "form4_strategy_execution_outcome_invalid",
                "all D504 positions must be terminal by fixed session 514",
            )
        eligibility_checked = True
        eligible = True
        readout_status = "eligible_for_pre_frozen_readout_engine"
    aggregate: dict[str, Any] = {
        "schema_version": AGGREGATE_SCHEMA,
        "status": "forward_only_strategy_evidence_no_performance",
        "prospective_sessions": prospective_count,
        "signal_sessions_closed": min(prospective_count, SIGNAL_SESSION_LIMIT),
        "candidate_allocations": len(decisions_at_limit),
        "completed_round_trips": completed_round_trips,
        "forced_settlements": forced_settlements,
        "distinct_issuers_completed": len(completed_issuers),
        "completed_positions_at_session_504": d504_completed_positions or 0,
        "distinct_issuers_completed_at_session_504": d504_completed_issuers or 0,
        "integrity_failure_sessions": integrity_failure_sessions,
        "integrity_complete_through_session_504": d504_integrity_ok is True,
        "active_positions": len(open_positions),
        "unconfirmed_clusters": unconfirmed,
        "capacity_rejected_clusters": capacity_rejected,
        "decision_record_count": len(decisions),
        "control_record_count": len(controls),
        "decision_chain_head_sha256": (
            decisions[-1]["entry_sha256"]
            if decisions
            else _ledger_genesis(namespace, "decision")
        ),
        "control_chain_head_sha256": (
            controls[-1]["entry_sha256"]
            if controls
            else _ledger_genesis(namespace, "control")
        ),
        "comparison_family_count": len(COMPARISON_FAMILY),
        "comparison_family_sha256": _comparison_hash(),
        "control_assignments_complete": False,
        "global_trials_before": GLOBAL_TRIALS_BEFORE,
        "trial_increment": TRIAL_INCREMENT,
        "global_trials_after": GLOBAL_TRIALS_AFTER,
        "readout_eligibility_checked": eligibility_checked,
        "separate_readout_eligible": eligible,
        "readout_status": readout_status,
        "performance_present": False,
        "performance_readout_generated": False,
        "paper_authorized": False,
        "paper_funding_usd": 0,
        "paper_positions": 0,
        "paper_orders": 0,
        "paper_fills": 0,
        "paper_backfill": 0,
        "real_money_action_usd": 0,
        "congress_requests": 0,
        "congress_rows": 0,
        "real_identifier_count": 0,
        "today_action": "今天不下單",
        "manifest_sha256": "",
    }
    aggregate["manifest_sha256"] = _aggregate_manifest(aggregate)
    public_status: dict[str, Any] = {
        "schema_version": PUBLIC_STATUS_SCHEMA,
        "status": readout_status,
        "today_action": "今天不下單",
        "performance_present": False,
        "paper_authorized": False,
        "paper_positions": 0,
        "real_money_action_usd": 0,
        "manifest_sha256": "",
    }
    public_status["manifest_sha256"] = _aggregate_manifest(public_status)
    validate_public_aggregate_progress(public_status)
    next_state = {
        "schema_version": PRIOR_STATE_SCHEMA,
        "namespace_genesis_sha256": prior_state["namespace_genesis_sha256"],
        "decision_record_count": len(decisions),
        "decision_chain_head_sha256": aggregate["decision_chain_head_sha256"],
        "control_record_count": len(controls),
        "control_chain_head_sha256": aggregate["control_chain_head_sha256"],
        "state_sha256": "",
    }
    next_state["state_sha256"] = _canonical_sha256(next_state, omit="state_sha256")
    return {
        "decision_records": deepcopy(decisions),
        "control_records": deepcopy(controls),
        "aggregate_progress": aggregate,
        "public_status": public_status,
        "next_ledger_state": next_state,
    }


def audit_round46_kernel_contract(*, root: str | Path | None = None) -> dict[str, Any]:
    """Return result-blind JSON-safe controls for a Round46 validation artifact."""

    paths: dict[str, object] = {
        "protocol_path": PROTOCOL_PATH,
        "authorization_receipt_path": AUTHORIZATION_RECEIPT_PATH,
        "workflow_path": WORKFLOW_PATH,
    }
    if root is not None:
        root_path = Path(root)
        paths["tracked_files_present"] = all((root_path / path).is_file() for path in paths.values())
    return {
        "schema_version": KERNEL_SCHEMA,
        "paths": paths,
        "fixed_controls": {
            "source_scope": SOURCE_SCOPE,
            "comparison_family": list(COMPARISON_FAMILY),
            "global_trials_before": GLOBAL_TRIALS_BEFORE,
            "trial_increment": TRIAL_INCREMENT,
            "global_trials_after": GLOBAL_TRIALS_AFTER,
            "cluster_calendar_days": CLUSTER_CALENDAR_DAYS,
            "minimum_capital_groups": MIN_CAPITAL_GROUPS,
            "minimum_accessions": MIN_ACCESSIONS,
            "minimum_accession_dollars": _format_decimal(MIN_ACCESSION_DOLLARS),
            "minimum_cluster_dollars": _format_decimal(MIN_CLUSTER_DOLLARS),
            "slot_count": SLOT_COUNT,
            "fractional_shares": FRACTIONAL_SHARES,
            "holding_sessions": HOLDING_SESSIONS,
            "cooldown_sessions": COOLDOWN_SESSIONS,
            "maximum_official_planned_sessions": MAX_PLANNED_SESSIONS,
            "signal_session_limit": SIGNAL_SESSION_LIMIT,
            "fixed_maturity_session": MATURITY_SESSION,
            "minimum_completed_positions": MIN_COMPLETED_POSITIONS,
            "minimum_distinct_completed_issuers": MIN_DISTINCT_COMPLETED_ISSUERS,
            "returns_calculated": False,
            "control_assignments_complete": False,
            "durable_private_writer_implemented": False,
            "readout_implementation_present": False,
        },
        "mutation_attacks": list(FORM4_FORWARD_STRATEGY_ERROR_CODES),
        "state_at_freeze": {
            "tsa_request_count": 0,
            "sec_request_count": 0,
            "real_identifier_count": 0,
            "real_filing_count": 0,
            "real_row_count": 0,
            "candidate_selection_count": 0,
            "candidate_allocation_count": 0,
            "strategy_run_count": 0,
            "performance_present": False,
            "paper_funding_usd": 0,
            "paper_positions": 0,
            "paper_orders": 0,
            "paper_fills": 0,
            "paper_backfill": 0,
            "real_money_action_usd": 0,
            "congress_request_count": 0,
            "congress_row_count": 0,
        },
        "permission": {
            "synthetic_kernel": True,
            "monitor_start": False,
            "sec_collection": False,
            "candidate_publication": False,
            "performance": False,
            "paper": False,
            "real_money": False,
        },
        "today_action": "今天不下單",
    }


__all__ = [
    "AGGREGATE_SCHEMA",
    "AUTHORIZATION_RECEIPT_PATH",
    "COMPARISON_FAMILY",
    "FORM4_FORWARD_STRATEGY_ERROR_CODES",
    "GLOBAL_TRIALS_AFTER",
    "GLOBAL_TRIALS_BEFORE",
    "KERNEL_SCHEMA",
    "PROTOCOL_PATH",
    "TRIAL_INCREMENT",
    "WORKFLOW_PATH",
    "Form4ForwardStrategyError",
    "audit_round46_kernel_contract",
    "make_genesis_prior_state",
    "run_form4_forward_strategy",
    "validate_public_aggregate_progress",
]
