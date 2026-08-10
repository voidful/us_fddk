from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

READOUT_SESSION = 504
MIN_CANDIDATE_ALLOCATIONS = 100
MIN_DISTINCT_ISSUERS = 50
MAX_NEW_ALLOCATIONS_PER_SESSION = 10

FORM4_FORWARD_CONTRACT_ERROR_CODES = (
    "form4_forward_timestamp_invalid",
    "form4_forward_canonical_before_index_pair",
    "form4_forward_progress_invalid",
    "form4_forward_horizon_exceeded",
    "form4_forward_readout_too_early",
    "form4_forward_insufficient_power",
)


class Form4ForwardContractError(RuntimeError):
    """Fail-closed Round 43 clock or readout error with a stable code."""

    def __init__(self, code: str, detail: str):
        if code not in FORM4_FORWARD_CONTRACT_ERROR_CODES:
            raise ValueError("unknown Form 4 forward-contract error code")
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}")


def _fail(code: str, detail: str) -> None:
    raise Form4ForwardContractError(code, detail)


def _canonical_utc(value: object) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        _fail("form4_forward_timestamp_invalid", "timestamp must be canonical UTC")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        _fail("form4_forward_timestamp_invalid", "timestamp is not ISO-8601")
    if parsed.tzinfo is None:
        _fail("form4_forward_timestamp_invalid", "timestamp has no UTC offset")
    normalized = parsed.astimezone(UTC).replace(microsecond=0)
    canonical = normalized.isoformat().replace("+00:00", "Z")
    if parsed.microsecond != 0 or value != canonical:
        _fail("form4_forward_timestamp_invalid", "timestamp is not canonical whole-second UTC")
    return normalized


def derive_prospective_known_at(
    *,
    index_pair_first_observed_at: str,
    canonical_submission_first_observed_at: str,
) -> dict[str, str]:
    """Derive the only Round 43 disclosure clock from completed-body receipts."""

    index_pair = _canonical_utc(index_pair_first_observed_at)
    submission = _canonical_utc(canonical_submission_first_observed_at)
    if submission < index_pair:
        _fail(
            "form4_forward_canonical_before_index_pair",
            "canonical submission cannot precede its sealed d0/d1 index pair",
        )
    return {
        "index_pair_first_observed_at": index_pair_first_observed_at,
        "canonical_submission_first_observed_at": canonical_submission_first_observed_at,
        "known_at": max(index_pair, submission).isoformat().replace("+00:00", "Z"),
        "known_at_basis": "prospective_first_observed",
    }


def _count(value: object, *, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        _fail("form4_forward_progress_invalid", f"{label} must be a non-negative integer")
    return value


def evaluate_readout_gate(
    *,
    prospective_sessions: int,
    candidate_allocations: int,
    distinct_issuers_allocated: int,
    performance_readout_requested: bool = False,
) -> dict[str, Any]:
    """Evaluate the fixed-horizon gate without computing or accepting performance."""

    sessions = _count(prospective_sessions, label="prospective_sessions")
    allocations = _count(candidate_allocations, label="candidate_allocations")
    issuers = _count(distinct_issuers_allocated, label="distinct_issuers_allocated")
    if not isinstance(performance_readout_requested, bool):
        _fail("form4_forward_progress_invalid", "performance request flag must be boolean")
    if issuers > allocations or allocations > sessions * MAX_NEW_ALLOCATIONS_PER_SESSION:
        _fail("form4_forward_progress_invalid", "aggregate counts are internally inconsistent")
    if sessions > READOUT_SESSION:
        _fail(
            "form4_forward_horizon_exceeded",
            "the prospective cohort cannot continue beyond session 504",
        )

    sample_power_passed = (
        allocations >= MIN_CANDIDATE_ALLOCATIONS and issuers >= MIN_DISTINCT_ISSUERS
    )
    if sessions < READOUT_SESSION:
        if performance_readout_requested:
            _fail(
                "form4_forward_readout_too_early",
                "performance remains blind before session 504",
            )
        status = "blind_accumulating_no_performance"
        terminal = False
        authorized = False
        stop_code = None
    elif not sample_power_passed:
        if performance_readout_requested:
            _fail(
                "form4_forward_insufficient_power",
                "session 504 sample-count thresholds were not met",
            )
        status = "insufficient_power_no_performance_readout"
        terminal = True
        authorized = False
        stop_code = "form4_forward_insufficient_power"
    else:
        status = "eligible_for_single_performance_readout"
        terminal = True
        authorized = True
        stop_code = None

    return {
        "prospective_sessions": sessions,
        "candidate_allocations": allocations,
        "distinct_issuers_allocated": issuers,
        "fixed_readout_session": READOUT_SESSION,
        "minimum_candidate_allocations": MIN_CANDIDATE_ALLOCATIONS,
        "minimum_distinct_issuers": MIN_DISTINCT_ISSUERS,
        "sample_power_passed": sample_power_passed,
        "performance_readout_authorized": authorized,
        "terminal": terminal,
        "status": status,
        "stop_code": stop_code,
    }


__all__ = [
    "FORM4_FORWARD_CONTRACT_ERROR_CODES",
    "MIN_CANDIDATE_ALLOCATIONS",
    "MIN_DISTINCT_ISSUERS",
    "READOUT_SESSION",
    "Form4ForwardContractError",
    "derive_prospective_known_at",
    "evaluate_readout_gate",
]
