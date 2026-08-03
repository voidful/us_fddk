import json
from pathlib import Path

import pytest

from scripts.build_short_term_authorized_data_handoff_report import _site_summary
from usfddk.authorized_data_handoff import (
    BUFFER_START,
    FORMAL_END,
    FORMAL_START,
    HANDOFF_PROTOCOL_SHA256,
    HANDOFF_REQUEST_ID,
    NEXT_EXECUTION_SESSION,
    run_authorized_data_handoff_validation,
)
from usfddk.ciz_execution_extension import BENCHMARK_COLUMNS
from usfddk.crsp_ciz_adapter import CIZ_REQUIRED_COLUMNS, CIZ_SOURCE_FILES

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def result() -> dict:
    return run_authorized_data_handoff_validation(ROOT)


def test_round16_synthetic_document_control_and_attacks_are_exact(result: dict) -> None:
    assert result["status"] == (
        "handoff_contract_validated_provider_response_and_data_still_missing"
    )
    assert result["synthetic_control"]["gate_summary"] == {
        "passed": 12,
        "total": 12,
        "all_passed": True,
    }
    assert result["attack_summary"] == {
        "rejected": 12,
        "total": 12,
        "all_rejected": True,
    }
    assert [row["id"] for row in result["synthetic_control"]["gates"]] == [
        f"{index:02d}" for index in range(1, 13)
    ]
    assert all(
        row["rejected"]
        and row["observed_error_code"] == row["expected_error_code"]
        and row["response_receipt_recomputed"] is True
        for row in result["attacks"]
    )


def test_request_is_bound_to_freeze_and_exact_ten_inputs(result: dict) -> None:
    request = result["request"]
    assert request["request_id"] == HANDOFF_REQUEST_ID
    assert request["protocol_sha256"] == HANDOFF_PROTOCOL_SHA256
    assert request["status"] == "ready_to_send_not_yet_sent"
    assert request["protocol_integrity"]["passed"] is True
    assert len(request["protocol_integrity"]["hash_checks"]) == 12
    assert all(request["protocol_integrity"]["hash_checks"].values())

    assert [row["name"] for row in request["source_files"]] == list(
        CIZ_SOURCE_FILES
    )
    assert {
        row["name"]: tuple(row["minimum_fields"])
        for row in request["source_files"]
    } == CIZ_REQUIRED_COLUMNS
    assert request["execution_overlay"]["assets"] == ["QQQ", "SPY"]
    assert tuple(request["execution_overlay"]["columns"]) == BENCHMARK_COLUMNS


def test_request_uses_fixed_coverage_and_documented_candidates(result: dict) -> None:
    request = result["request"]
    assert request["coverage"] == {
        "buffer_start": BUFFER_START,
        "formal_start": FORMAL_START,
        "formal_end": FORMAL_END,
        "next_execution_session": NEXT_EXECUTION_SESSION,
        "minimum_pre_signal_sessions": 252,
    }
    assert [
        row["product_code"] for row in request["provider_products_to_confirm"]
    ] == ["crsp_m_stock", "crsp_m_indexes"]
    assert request["wrds_dataset_candidates_to_confirm"] == [
        "crsp.dsf_v2",
        "crsp.msf_v2",
        "crsp.StkSecurityInfoHist",
        "/wrds/crsp/sasdata/a_stock_v2",
        "/wrds/crsp/sasdata/a_indexes_v2",
    ]
    assert all("login_confirmation_required" in row["status"] for row in request["provider_products_to_confirm"])


def test_json_schema_is_closed_and_bound_to_the_request() -> None:
    schema = json.loads(
        (ROOT / "schemas/short_term_authorized_data_response.schema.json").read_text(
            encoding="utf-8"
        )
    )
    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["additionalProperties"] is False
    assert schema["properties"]["request_id"]["const"] == HANDOFF_REQUEST_ID
    assert (
        schema["properties"]["request_protocol_sha256"]["const"]
        == HANDOFF_PROTOCOL_SHA256
    )
    assert schema["properties"]["source_format"]["const"] == "CIZ_FF2"
    assert set(schema["properties"]["file_capabilities"]["required"]) == set(
        CIZ_SOURCE_FILES
    )
    assert schema["properties"]["benchmark_delivery"]["properties"]["assets"] == {
        "type": "array",
        "prefixItems": [{"const": "QQQ"}, {"const": "SPY"}],
        "items": False,
    }


def test_public_status_does_not_promote_a_document_control(result: dict) -> None:
    verification = result["official_verification"]
    assert result["actual_document_handoff"] == {
        "passed": 1,
        "total": 12,
        "all_passed": False,
        "only_passed_gate": "01_preregistration_integrity",
    }
    assert result["actual_point_in_time_readiness"] == {
        "passed": 1,
        "total": 20,
        "all_passed": False,
    }
    assert verification["wrds_credentials_present"] is False
    assert verification["provider_contacted"] is False
    assert verification["authorized_provider_response_received"] is False
    assert verification["authorized_provider_sample_received"] is False
    assert result["formal_stock_backtest_authorized"] is False
    assert result["formal_stock_backtest_completed"] is False
    assert result["strategy_rule_changed"] is False
    assert result["paper"] == {
        "authorized": False,
        "state": "all_cash",
        "backfilled_trades": 0,
        "positions": [],
    }
    assert result["real_money_action_usd"] == 0


def test_committed_machine_and_site_receipts_match_round16(result: dict) -> None:
    machine = json.loads(
        (ROOT / "artifacts/short_term_authorized_data_handoff.json").read_text(
            encoding="utf-8"
        )
    )
    site = json.loads(
        (ROOT / "site/data/short-term-authorized-data-handoff.json").read_text(
            encoding="utf-8"
        )
    )

    assert machine == result
    assert site == _site_summary(result)
