from __future__ import annotations

from copy import deepcopy

import pytest

from usfddk.provider_evidence_refresh import (
    MAX_BODY_BYTES,
    SOURCE_IDS,
    SOURCES,
    ProviderEvidenceRefreshError,
    inspect_current_sources,
    make_refresh_result,
    protocol_integrity,
    validate_result,
)


def _responses() -> dict[str, dict[str, object]]:
    bodies = {
        "crsp_ciz_guide": b"<title>CRSP US Stock Databases Guide CIZ</title>",
        "crsp_index_history_feed": b"%PDF-1.7 INDEX LEVEL AND CONSTITUENT HISTORY",
        "crsp_ciz_migration_notice": b"Beginning July 28, 2026; December 2024",
        "lseg_historical_constituents": b"Building historical index constituents Joiner Leaver",
    }
    content_types = {
        source_id: "application/pdf"
        if SOURCES[source_id]["content_kind"] == "pdf"
        else "text/html; charset=utf-8"
        for source_id in SOURCE_IDS
    }
    return {
        source_id: {
            "final_url": SOURCES[source_id]["url"],
            "status": 200,
            "content_type": content_types[source_id],
            "body": bodies[source_id],
        }
        for source_id in SOURCE_IDS
    }


def test_round33_protocol_is_frozen_and_valid() -> None:
    result = protocol_integrity(".")
    assert result["passed"] is True
    assert len(result["hash_checks"]) == 4


def test_valid_observation_is_metadata_only_and_never_qualifies() -> None:
    responses = _responses()
    observations = inspect_current_sources(responses, root=".")
    assert set(observations) == set(SOURCE_IDS)
    assert all(row["raw_source_persisted"] is False for row in observations.values())
    result = make_refresh_result(responses, root=".")
    assert result["status"] == "observed_official_sources"
    assert result["provider_package_qualified"] is False
    assert result["formal_backtest_authorized"] is False
    assert result["paper_state"] == "all_cash"
    assert result["real_money_action_usd"] == 0
    assert validate_result(result, root=".")["passed"] is True


@pytest.mark.parametrize(
    ("attack", "code"),
    [
        ("missing", "source_set_mismatch"),
        ("host", "non_https_or_host_drift"),
        ("status", "http_status_mismatch"),
        ("marker", "marker_missing"),
    ],
)
def test_source_identity_attacks_fail_closed(attack: str, code: str) -> None:
    responses = _responses()
    if attack == "missing":
        responses.pop("lseg_historical_constituents")
    elif attack == "host":
        responses["lseg_historical_constituents"]["final_url"] = (
            "https://evil.example/lseg"
        )
    elif attack == "status":
        responses["lseg_historical_constituents"]["status"] = 302
    elif attack == "marker":
        responses["lseg_historical_constituents"]["body"] = b"unrelated"
    with pytest.raises(ProviderEvidenceRefreshError) as exc_info:
        inspect_current_sources(responses, root=".")
    assert exc_info.value.code == code


def test_body_cap_and_hash_drift_fail_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    responses = _responses()
    monkeypatch.setattr(
        "usfddk.provider_evidence_refresh.MAX_BODY_BYTES", 8
    )
    responses["lseg_historical_constituents"]["body"] = b"123456789"
    with pytest.raises(ProviderEvidenceRefreshError) as exc_info:
        inspect_current_sources(responses, root=".")
    assert exc_info.value.code == "body_size_exceeded"

    monkeypatch.setattr(
        "usfddk.provider_evidence_refresh.MAX_BODY_BYTES", MAX_BODY_BYTES
    )
    good = inspect_current_sources(_responses(), root=".")
    previous = deepcopy(good)
    previous["lseg_historical_constituents"]["body_sha256"] = "0" * 64
    with pytest.raises(ProviderEvidenceRefreshError) as exc_info:
        inspect_current_sources(
            _responses(), root=".", previous_observations=previous
        )
    assert exc_info.value.code == "source_hash_drift"

    changed = _responses()
    changed["lseg_historical_constituents"]["body"] = (
        b"Building historical index constituents Joiner Leaver revised"
    )
    result = make_refresh_result(
        changed, root=".", previous_observations=good
    )
    drift = result["observation_errors"]["lseg_historical_constituents"]
    assert drift["code"] == "source_hash_drift"
    assert drift["previous_body_sha256"] == good["lseg_historical_constituents"]["body_sha256"]
    assert drift["current_body_sha256"] == result["observations"]["lseg_historical_constituents"]["body_sha256"]
    assert drift["previous_final_url"] == drift["current_final_url"]


def test_result_claim_attacks_cannot_promote_missing_clocks_or_paper() -> None:
    result = make_refresh_result(_responses(), root=".")
    optimistic = deepcopy(result)
    optimistic["capability_matrix"]["membership_announced_at"]["status"] = (
        "explicit_primary_documentation"
    )
    with pytest.raises(ProviderEvidenceRefreshError) as exc_info:
        validate_result(optimistic, root=".")
    assert exc_info.value.code == "announcement_time_substitution"

    optimistic = deepcopy(result)
    optimistic["raw_source_persisted"] = True
    with pytest.raises(ProviderEvidenceRefreshError) as exc_info:
        validate_result(optimistic, root=".")
    assert exc_info.value.code == "raw_source_persisted"

    optimistic = deepcopy(result)
    optimistic["paper_authorized"] = True
    with pytest.raises(ProviderEvidenceRefreshError) as exc_info:
        validate_result(optimistic, root=".")
    assert exc_info.value.code == "decision_boundary_violation"


def test_partial_remote_result_preserves_safe_observations_and_stops() -> None:
    responses = _responses()
    responses.pop("crsp_ciz_migration_notice")
    result = make_refresh_result(responses, root=".")
    assert result["status"] == "manual_review_required"
    assert result["all_frozen_identity_checks_pass"] is False
    assert result["source_identity_count"] == 3
    assert result["provider_package_qualified"] is False
    assert result["paper_state"] == "all_cash"
