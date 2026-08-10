from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import subprocess
from pathlib import Path
from typing import Any

import pytest

from usfddk.form4_admission_collection import (
    Form4CollectionError,
    validate_collection_authorization,
)

ROOT = Path(__file__).resolve().parents[1]
AMENDMENT = ROOT / "docs/SHORT_TERM_FORM4_MULTIPATH_FORWARD_PROTOCOL_AMENDMENT_V1_1.md"
RECEIPT = (
    ROOT
    / "artifacts/short_term_form4_multipath_forward_protocol_amendment_v1_1_receipt.json"
)
HISTORICAL_COMMIT = "0e326d75e87d0ca8ee3e2260ad3c4a3c4f6c1a02"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _canonical_hash(payload: dict[str, Any]) -> str:
    core = {key: value for key, value in payload.items() if key != "receipt_sha256"}
    rendered = json.dumps(
        core,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(rendered).hexdigest()


def _receipt() -> dict[str, Any]:
    return json.loads(RECEIPT.read_text(encoding="utf-8"))


def _assert_binding(binding: dict[str, str]) -> None:
    assert set(binding) == {"path", "sha256"}
    assert _sha256(ROOT / binding["path"]) == binding["sha256"]


def test_v1_1_receipt_is_canonical_and_binds_every_effective_byte() -> None:
    receipt = _receipt()
    assert receipt["schema_version"] == 1
    assert receipt["research_round"] == 43
    assert receipt["status"] == (
        "v1_1_append_only_supersession_result_blind_data_engineering_only"
    )
    assert receipt["frozen_at"] == "2026-08-10T02:34:43Z"
    assert receipt["receipt_sha256"] == _canonical_hash(receipt)

    bindings = [
        receipt["historical_v1"]["protocol"],
        receipt["historical_v1"]["receipt"],
        receipt["amendment"],
        *receipt["parent_lineage"]["disclosure_known_at"],
        *receipt["parent_lineage"]["round41_form4"],
        *receipt["parent_lineage"]["round42_feasibility"],
        *receipt["parent_lineage"]["global_trial_ledger"],
        *receipt["effective_offline_implementation"],
        *receipt["integration_bindings"],
    ]
    for binding in bindings:
        _assert_binding(binding)


def test_historical_v1_bytes_are_preserved_but_never_effective() -> None:
    receipt = _receipt()
    historical = receipt["historical_v1"]
    assert historical["commit"] == HISTORICAL_COMMIT
    assert historical["protocol"]["sha256"] == (
        "845b13b1c01a0edef887ac490764ef8359cb382184430f483ab7093ca2b013eb"
    )
    assert historical["receipt"]["sha256"] == (
        "f4c413217145fc2fff422a8291957565e690a1f4a734dab1b75482a9e1be4e85"
    )
    assert historical["receipt_canonical_sha256"] == (
        "7cf6131367baa8c8cda2a4e2a9ba32c6e8582866efc5c5bf809cbcbc2335b707"
    )
    assert historical["bytes_preserved"] is True
    assert historical["executable"] is False
    assert historical["performance_authorization_effective"] is False
    assert historical["active_import_paths_removed"] is True
    assert historical["active_positive_tests_removed"] is True
    assert historical["historical_commit_only"] is True

    for binding in (historical["protocol"], historical["receipt"]):
        historical_bytes = subprocess.run(
            ["git", "show", f"{HISTORICAL_COMMIT}:{binding['path']}"],
            cwd=ROOT,
            capture_output=True,
            check=True,
        ).stdout
        assert hashlib.sha256(historical_bytes).hexdigest() == binding["sha256"]
        assert historical_bytes == (ROOT / binding["path"]).read_bytes()

    active = (ROOT / "usfddk/form4_forward_admission_contract.py").read_text(
        encoding="utf-8"
    )
    assert "from usfddk.form4_forward_contract" not in active
    assert "Round43 v1.1 is permanently data-engineering-only" in active

    historical_receipt = json.loads(
        (ROOT / historical["receipt"]["path"]).read_text(encoding="utf-8")
    )
    for key in (
        "multipath_resolver",
        "multipath_tests",
        "forward_contract",
        "forward_contract_tests",
        "protocol_tests",
    ):
        binding = historical_receipt["offline_implementation"][key]
        historical_bytes = subprocess.run(
            ["git", "show", f"{HISTORICAL_COMMIT}:{binding['path']}"],
            cwd=ROOT,
            capture_output=True,
            check=True,
        ).stdout
        assert hashlib.sha256(historical_bytes).hexdigest() == binding["sha256"]
        assert not (ROOT / binding["path"]).exists()

    assert importlib.util.find_spec("usfddk.form4_forward_contract") is None
    assert importlib.util.find_spec("usfddk.form4_multipath_index") is None


def test_parent_admission_and_trial_ledger_cannot_be_promoted() -> None:
    receipt = _receipt()
    parent = receipt["parent_state"]
    assert parent == {
        "round41_required_admission_passed": 16,
        "round41_required_admission_total": 16,
        "round42_observed_admission_passed": 2,
        "round42_observed_admission_total": 16,
        "round42_stop_status": "stopped_no_admission_claim",
        "round42_restart_or_reuse_allowed": False,
        "historical_gate_07_passed": False,
        "historical_gate_08_passed": False,
        "prospective_evidence_can_promote_historical_admission": False,
        "global_trial_lower_bound": 6287,
        "round43_trial_increment": 0,
        "global_trial_ledger_append_authorized": False,
    }
    validation = json.loads(
        (ROOT / "artifacts/short_term_form4_admission_feasibility_validation.json").read_text(
            encoding="utf-8"
        )
    )
    assert validation["status"] == parent["round42_stop_status"]
    assert validation["admission_controls"]["passed"] == 2
    assert validation["admission_controls"]["total"] == 16
    assert validation["admission_controls"]["gates"][6]["passed"] is False
    assert validation["admission_controls"]["gates"][7]["passed"] is False


def test_round42_authorization_drift_guard_replays_outside_repository(
    tmp_path: Path,
) -> None:
    source = ROOT / "artifacts/short_term_form4_admission_collection_authorization_receipt.json"
    drifted = copy.deepcopy(json.loads(source.read_text(encoding="utf-8")))
    drifted["fixed_collection"]["total_requests_max"] = 29
    drifted["receipt_sha256"] = _canonical_hash(drifted)
    outside_repository = tmp_path / "authorization-drift.json"
    outside_repository.write_text(json.dumps(drifted), encoding="utf-8")
    with pytest.raises(Form4CollectionError) as caught:
        validate_collection_authorization(outside_repository, repository_root=ROOT)
    assert caught.value.code == "form4_collection_authorization_invalid"


def test_effective_round43_contract_is_exact_zero_and_has_no_readout() -> None:
    receipt = _receipt()
    assert receipt["effective_contract"] == {
        "scope": "data_engineering_only",
        "evidence_mode": "synthetic_fixture_only",
        "structural_fixture_only": True,
        "real_evidence_admission_authorized": False,
        "external_trust_root_complete": False,
        "official_response_trust_root_complete": False,
        "published_date_manifest_trust_root_complete": False,
        "zero_state_is_external_account_proof": False,
        "source_scope": ["sec_form_4"],
        "form_types": ["4", "4/A"],
        "round43_sec_requests": 0,
        "prospective_accessions": 0,
        "candidate_selection_count": 0,
        "candidate_allocation_count": 0,
        "strategy_run_count": 0,
        "performance_result_present": False,
        "prospective_session_endpoint_enabled": False,
        "minimum_candidate_allocations_enabled": False,
        "minimum_distinct_issuers_enabled": False,
        "readout_receipt_enabled": False,
        "paper_authorized": False,
        "paper_state": "all_cash",
        "paper_positions": [],
        "paper_backfilled_trades": 0,
        "real_money_action_usd": 0,
    }
    assert receipt["future_strategy_boundary"] == {
        "new_round_required": True,
        "new_authorization_required": True,
        "new_global_trial_entry_required": True,
        "new_unseen_prospective_cohort_required": True,
        "round41_historical_comparisons_reusable_as_paid_trials": False,
    }


def test_known_at_multipath_and_congress_boundaries_are_unambiguous() -> None:
    receipt = _receipt()
    assert receipt["known_at_contract"] == {
        "field": "content_full_body_first_observed_at",
        "basis": "prospective_local_full_body_first_observed",
        "strictly_after_monitor_start": True,
        "full_body_read_to_eof_required": True,
        "content_hash_required": True,
        "trusted_create_once_registry_required_for_future_real_admission": True,
        "trusted_create_once_registry_complete": False,
        "reconciliation_can_change_known_at": False,
        "historical_backfill_allowed": False,
    }
    assert receipt["multipath_contract"] == {
        "minimum_paths": 1,
        "project_path_cap": 10,
        "project_cap_is_sec_official_limit": False,
        "path_count_is_actor_count": False,
        "d0_and_d1_bodies_required": True,
        "d1_is_first_published_date_strictly_after_d0": True,
        "carrier_rule": "d0_xor_d1",
        "exact_raw_archive_path_required": True,
        "fresh_offline_replay_hash_required": True,
    }
    assert receipt["congress_boundary"] == {
        "collection_allowed": False,
        "request_count": 0,
        "row_count": 0,
        "field_count": 0,
        "strategy_allowed": False,
        "mixed_source_allowed": False,
        "stable_code": "form4_forward_congress_field_injection",
    }


def test_amendment_and_ci_keep_canonical_stops_and_effective_tests() -> None:
    receipt = _receipt()
    text = AMENDMENT.read_text(encoding="utf-8")
    for phrase in (
        "Round43 永久只准資料工程",
        "504／100／50 全部不可執行",
        "prospective_local_full_body_first_observed",
        'source_scope = ["sec_form_4"]',
        "form4_forward_non_engineering_action_forbidden",
        "form4_forward_congress_field_injection",
        "form4_forward_project_path_cap_exceeded",
        "form4_forward_known_at_invented",
        "今天不下單",
    ):
        assert phrase in text

    assert receipt["stable_codes"] == {
        "non_engineering": "form4_forward_non_engineering_action_forbidden",
        "congress_injection": "form4_forward_congress_field_injection",
        "project_path_cap": "form4_forward_project_path_cap_exceeded",
        "known_at": "form4_forward_known_at_invented",
        "cross_day": "form4_forward_cross_day_missing_or_ambiguous",
    }
    for workflow_name in ("pages.yml", "daily-paper-update.yml"):
        workflow = (ROOT / ".github/workflows" / workflow_name).read_text(encoding="utf-8")
        v2 = workflow.index("tests/test_form4_multipath_reconciliation_v2.py")
        admission = workflow.index("tests/test_form4_forward_admission_contract.py")
        amendment = workflow.index(
            "tests/test_form4_multipath_forward_protocol_amendment_v1_1.py"
        )
        assert v2 < admission < amendment
        assert "tests/test_form4_forward_contract.py" not in workflow


def test_zero_action_and_no_network_receipt_are_explicit() -> None:
    receipt = _receipt()
    assert receipt["execution_evidence"] == {
        "network_used": False,
        "new_sec_request_count": 0,
        "real_identifier_fixture_used": False,
        "candidate_or_performance_engine_invoked": False,
        "historical_v1_protocol_or_receipt_modified": False,
        "historical_v1_executable_paths_removed": True,
        "historical_v1_exact_bytes_retained_in_commit": True,
    }
    assert receipt["permission"] == {
        "protocol_amendment": True,
        "network_collection": False,
        "historical_backfill": False,
        "candidate_selection": False,
        "candidate_allocation": False,
        "performance_readout": False,
        "paper": False,
        "real_money": False,
    }
    assert receipt["today_action"] == "今天不下單"

    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "append-only v1.1 修訂" in readme
    assert "撤銷 504／100／50及所有績效解封" in readme
