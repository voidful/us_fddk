from __future__ import annotations

from copy import deepcopy

import pytest

from usfddk.risk_free_treasury_bridge import (
    EXPECTED_MISSING_SESSIONS,
    MAX_BODY_BYTES,
    TREASURY_URL,
    TreasuryBridgeError,
    make_bridge_result,
    parse_treasury_xml,
    protocol_integrity,
    validate_result,
)


def _xml_body(*, include_targets: bool = True) -> bytes:
    dates = ["2026-06-29", "2026-06-30"]
    if include_targets:
        dates.extend(EXPECTED_MISSING_SESSIONS)
    rows = []
    for index, raw_date in enumerate(dates):
        rows.append(
            """<m:properties>
  <d:INDEX_DATE>{date}T00:00:00</d:INDEX_DATE>
  <d:ROUND_B1_YIELD_4WK_2>{yield_value}</d:ROUND_B1_YIELD_4WK_2>
</m:properties>""".format(
                date=raw_date,
                yield_value=f"4.{index % 7:02d}",
            )
        )
    return (
        "<?xml version=\"1.0\" encoding=\"utf-8\"?>"
        "<m:feed xmlns:m=\"urn:feed\" xmlns:d=\"urn:data\"><m:entry>"
        + "".join(rows)
        + "</m:entry></m:feed>"
    ).encode()


def _response(body: bytes | None = None) -> dict[str, object]:
    return {
        "final_url": TREASURY_URL,
        "status": 200,
        "content_type": "application/xml; charset=utf-8",
        "body": _xml_body() if body is None else body,
    }


def test_round37_protocol_is_frozen_and_valid() -> None:
    result = protocol_integrity(".")
    assert result["passed"] is True
    assert all(result["hash_checks"].values())


def test_valid_observation_covers_fixed_target_and_keeps_locks() -> None:
    result = make_bridge_result(_response(), root=".")
    assert result["status"] == "official_treasury_bridge_observed_formal_rf_still_blocked"
    assert result["coverage"]["observed_target_sessions"] == 22
    assert result["coverage"]["missing_target_sessions"] == []
    assert result["comparison"]["formal_equivalence"] is False
    assert result["formal_rf_substitute"] is False
    assert result["formal_backtest_authorized"] is False
    assert result["paper_authorized"] is False
    assert result["paper_state"] == "all_cash"
    assert result["real_money_action_usd"] == 0
    assert validate_result(result, root=".")["passed"] is True


def test_parser_rejects_invalid_xml_and_body_size() -> None:
    with pytest.raises(TreasuryBridgeError) as exc_info:
        parse_treasury_xml(b"not xml")
    assert exc_info.value.code == "xml_invalid"

    with pytest.raises(TreasuryBridgeError) as exc_info:
        parse_treasury_xml(b"x" * (MAX_BODY_BYTES + 1))
    assert exc_info.value.code == "body_size_invalid"


@pytest.mark.parametrize(
    ("attack", "code"),
    [
        ("host", "source_host_drift"),
        ("status", "source_http_status"),
        ("content_type", "source_content_type"),
        ("missing", "target_session_missing"),
    ],
)
def test_source_and_coverage_attacks_fail_closed(attack: str, code: str) -> None:
    response = _response()
    if attack == "host":
        response["final_url"] = "https://evil.example/treasury.xml"
    elif attack == "status":
        response["status"] = 302
    elif attack == "content_type":
        response["content_type"] = "text/plain"
    else:
        response["body"] = _xml_body(include_targets=False)
    with pytest.raises(TreasuryBridgeError) as exc_info:
        make_bridge_result(response, root=".")
    assert exc_info.value.code == code


def test_result_claim_attacks_cannot_promote_proxy_or_paper() -> None:
    result = make_bridge_result(_response(), root=".")
    for field, value, code in (
        ("formal_rf_substitute", True, "definition_substitution"),
        ("formal_backtest_authorized", True, "decision_boundary_violation"),
        ("paper_authorized", True, "decision_boundary_violation"),
        ("real_money_action_usd", 1, "decision_boundary_violation"),
    ):
        optimistic = deepcopy(result)
        optimistic[field] = value
        with pytest.raises(TreasuryBridgeError) as exc_info:
            validate_result(optimistic, root=".")
        assert exc_info.value.code == code

    optimistic = deepcopy(result)
    optimistic["target_rows"] = list(reversed(optimistic["target_rows"]))
    with pytest.raises(TreasuryBridgeError) as exc_info:
        validate_result(optimistic, root=".")
    assert exc_info.value.code == "target_rows_invalid"
