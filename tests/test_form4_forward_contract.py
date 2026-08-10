from __future__ import annotations

from collections.abc import Callable

import pytest

from usfddk.form4_forward_contract import (
    Form4ForwardContractError,
    derive_prospective_known_at,
    evaluate_readout_gate,
)


def _code(action: Callable[[], object]) -> str:
    with pytest.raises(Form4ForwardContractError) as caught:
        action()
    return caught.value.code


def test_known_at_uses_completed_canonical_submission_observation() -> None:
    result = derive_prospective_known_at(
        index_pair_first_observed_at="2026-08-10T02:00:00Z",
        canonical_submission_first_observed_at="2026-08-10T02:00:09Z",
    )
    assert result == {
        "index_pair_first_observed_at": "2026-08-10T02:00:00Z",
        "canonical_submission_first_observed_at": "2026-08-10T02:00:09Z",
        "known_at": "2026-08-10T02:00:09Z",
        "known_at_basis": "prospective_first_observed",
    }


def test_known_at_rejects_invented_or_out_of_order_timestamps() -> None:
    assert _code(
        lambda: derive_prospective_known_at(
            index_pair_first_observed_at="2026-08-10",
            canonical_submission_first_observed_at="2026-08-10T02:00:09Z",
        )
    ) == "form4_forward_timestamp_invalid"
    assert _code(
        lambda: derive_prospective_known_at(
            index_pair_first_observed_at="2026-08-10T02:00:09Z",
            canonical_submission_first_observed_at="2026-08-10T02:00:08Z",
        )
    ) == "form4_forward_canonical_before_index_pair"


def test_readout_remains_blind_before_fixed_session_504() -> None:
    result = evaluate_readout_gate(
        prospective_sessions=503,
        candidate_allocations=101,
        distinct_issuers_allocated=51,
    )
    assert result["status"] == "blind_accumulating_no_performance"
    assert result["performance_readout_authorized"] is False
    assert result["terminal"] is False
    assert _code(
        lambda: evaluate_readout_gate(
            prospective_sessions=503,
            candidate_allocations=101,
            distinct_issuers_allocated=51,
            performance_readout_requested=True,
        )
    ) == "form4_forward_readout_too_early"


@pytest.mark.parametrize(
    ("allocations", "issuers"),
    [(99, 50), (100, 49), (0, 0)],
)
def test_session_504_stops_without_performance_when_power_is_insufficient(
    allocations: int,
    issuers: int,
) -> None:
    result = evaluate_readout_gate(
        prospective_sessions=504,
        candidate_allocations=allocations,
        distinct_issuers_allocated=issuers,
    )
    assert result["status"] == "insufficient_power_no_performance_readout"
    assert result["stop_code"] == "form4_forward_insufficient_power"
    assert result["terminal"] is True
    assert result["performance_readout_authorized"] is False
    assert _code(
        lambda: evaluate_readout_gate(
            prospective_sessions=504,
            candidate_allocations=allocations,
            distinct_issuers_allocated=issuers,
            performance_readout_requested=True,
        )
    ) == "form4_forward_insufficient_power"


def test_session_504_authorizes_exactly_one_readout_only_when_both_counts_pass() -> None:
    result = evaluate_readout_gate(
        prospective_sessions=504,
        candidate_allocations=100,
        distinct_issuers_allocated=50,
        performance_readout_requested=True,
    )
    assert result["status"] == "eligible_for_single_performance_readout"
    assert result["sample_power_passed"] is True
    assert result["performance_readout_authorized"] is True
    assert result["terminal"] is True


def test_cohort_cannot_be_extended_or_report_impossible_counts() -> None:
    assert _code(
        lambda: evaluate_readout_gate(
            prospective_sessions=505,
            candidate_allocations=100,
            distinct_issuers_allocated=50,
        )
    ) == "form4_forward_horizon_exceeded"
    assert _code(
        lambda: evaluate_readout_gate(
            prospective_sessions=10,
            candidate_allocations=101,
            distinct_issuers_allocated=50,
        )
    ) == "form4_forward_progress_invalid"
    assert _code(
        lambda: evaluate_readout_gate(
            prospective_sessions=504,
            candidate_allocations=49,
            distinct_issuers_allocated=50,
        )
    ) == "form4_forward_progress_invalid"
