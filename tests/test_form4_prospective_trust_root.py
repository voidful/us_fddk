from __future__ import annotations

import copy
import hashlib
import json
import re
import socket
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

import pytest

from usfddk.form4_prospective_trust_root import (
    EVIDENCE_BOUNDARY,
    LINEAGE_STATE,
    MONITOR_START_BOUNDARY,
    OFFICIAL_SOURCE_CONTRACT,
    PERMISSION,
    PRE_DATA_BINDING_KEYS,
    PRE_DATA_BINDING_PATHS,
    PRE_DATA_FROZEN_AT,
    PRE_DATA_RECEIPT_KEYS,
    PRE_DATA_SCHEMA,
    PRE_DATA_STATUS,
    REMOTE_GATE,
    REQUEST_POLICY,
    ROUND43_PARENT_COMMIT,
    ROUND43_PARENT_REMOTE_REF,
    STABLE_CODES,
    STATE_BOUNDARY,
    Form4ProspectiveTrustRootError,
    _assert_identifier_free,
    _load_exact_json,
    _validate_bindings,
    _validate_static_content,
    assert_predata_network_locked,
    canonical_sha256,
    validate_predata_authorization,
)

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "docs/SHORT_TERM_FORM4_PROSPECTIVE_TRUST_ROOT_PROTOCOL.md"
RECEIPT = (
    ROOT / "artifacts/short_term_form4_prospective_trust_root_protocol_receipt.json"
)
WORKFLOW = ROOT / ".github/workflows/form4-round44-predata-ci.yml"
ACCESSION_PATTERN = re.compile(r"(?<!\d)\d{10}-\d{2}-\d{6}(?!\d)")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _receipt() -> dict[str, object]:
    return json.loads(RECEIPT.read_text(encoding="utf-8"))


def _error_code(action: Callable[[], object]) -> str:
    with pytest.raises(Form4ProspectiveTrustRootError) as caught:
        action()
    return caught.value.code


def test_phase_a_receipt_is_exact_canonical_and_locally_replayable() -> None:
    receipt = _receipt()
    assert set(receipt) == PRE_DATA_RECEIPT_KEYS
    assert receipt["schema_version"] == PRE_DATA_SCHEMA
    assert receipt["research_round"] == 44
    assert receipt["phase"] == "predata_protocol_freeze"
    assert receipt["status"] == PRE_DATA_STATUS
    assert receipt["frozen_at"] == PRE_DATA_FROZEN_AT
    frozen_at = datetime.fromisoformat(PRE_DATA_FROZEN_AT.replace("Z", "+00:00"))
    assert frozen_at <= datetime.now(UTC)
    assert receipt["parent_code_commit"] == ROUND43_PARENT_COMMIT
    assert receipt["parent_remote_ref"] == ROUND43_PARENT_REMOTE_REF
    assert receipt["receipt_sha256"] == canonical_sha256(
        receipt, omit="receipt_sha256"
    )
    assert validate_predata_authorization(RECEIPT, repository_root=ROOT) == receipt


def test_phase_a_binds_every_parent_and_effective_execution_byte() -> None:
    receipt = _receipt()
    bindings = receipt["bindings"]
    assert isinstance(bindings, dict)
    assert set(bindings) == PRE_DATA_BINDING_KEYS
    for name, binding in bindings.items():
        assert isinstance(binding, dict)
        assert set(binding) == {"path", "sha256"}
        relative = binding["path"]
        digest = binding["sha256"]
        assert isinstance(relative, str)
        assert isinstance(digest, str)
        assert relative == PRE_DATA_BINDING_PATHS[name]
        assert _sha256(ROOT / relative) == digest


def test_official_source_contract_never_promotes_sec_metadata_to_known_at() -> None:
    receipt = _receipt()
    assert receipt["official_source_contract"] == OFFICIAL_SOURCE_CONTRACT
    assert OFFICIAL_SOURCE_CONTRACT["ownership_xml_version"] == "5.5"
    assert OFFICIAL_SOURCE_CONTRACT["ownership_xml_effective_date"] == "2026-03-18"
    assert OFFICIAL_SOURCE_CONTRACT["allowed_hosts_after_future_authorization"] == [
        "www.sec.gov"
    ]
    assert OFFICIAL_SOURCE_CONTRACT["sec_policy_requests_per_second_ceiling"] == 10
    for false_claim in (
        "sec_public_first_available_timestamp_exists",
        "sec_public_content_signature_exists",
        "acceptance_time_is_known_at",
        "filing_date_is_known_at",
        "index_filename_date_is_known_at",
        "http_headers_are_known_at",
    ):
        assert OFFICIAL_SOURCE_CONTRACT[false_claim] is False

    assert EVIDENCE_BOUNDARY["known_at_basis_after_future_start"] == (
        "max(local_full_body_completed_at, independent_anchor_received_at)"
    )
    assert EVIDENCE_BOUNDARY["local_sha256_alone_is_external_trust_root"] is False
    assert EVIDENCE_BOUNDARY["sec_http_200_alone_is_external_trust_root"] is False
    assert EVIDENCE_BOUNDARY["etag_or_last_modified_is_external_trust_root"] is False
    assert EVIDENCE_BOUNDARY["legacy_sec_client_is_round44_production_transport"] is False
    assert EVIDENCE_BOUNDARY["legacy_sec_client_receipt_is_round44_admission"] is False


def test_lineage_is_frozen_without_rescuing_round42_or_round43() -> None:
    receipt = _receipt()
    assert receipt["lineage_state"] == LINEAGE_STATE
    assert LINEAGE_STATE == {
        "round41_historical_admission_required": 16,
        "round42_observed_admission_passed": 2,
        "round42_observed_admission_total": 16,
        "round42_status": "stopped_no_admission_claim",
        "round42_restart_or_reuse_allowed": False,
        "round43_evidence_mode": "synthetic_fixture_only",
        "round43_real_evidence_admission_authorized": False,
        "round43_performance_readout_authorized": False,
        "global_trial_lower_bound": 6287,
        "round44_trial_increment": 0,
    }


def test_remote_gate_is_exact_head_read_only_and_still_pending() -> None:
    receipt = _receipt()
    assert receipt["remote_gate"] == REMOTE_GATE
    assert REMOTE_GATE["authorization_commit_self_embedded"] is False
    assert REMOTE_GATE["authorization_commit_must_be_derived_from_repository_head"] is True
    assert REMOTE_GATE["same_repository_remote_head_must_equal_authorization_commit"] is True
    assert REMOTE_GATE["pull_request_checkout_must_use_exact_head_sha"] is True
    assert REMOTE_GATE["pages_or_daily_workflow_can_authorize"] is False
    assert REMOTE_GATE["remote_gate_passed_in_this_receipt"] is False

    workflow = WORKFLOW.read_text(encoding="utf-8")
    exact_head = "${{ github.event.pull_request.head.sha }}"
    assert f"ref: {exact_head}" in workflow
    assert f"EXPECTED_HEAD_SHA: {exact_head}" in workflow
    assert "workflow_dispatch:" not in workflow
    assert "if: github.event.pull_request.head.repo.full_name == github.repository" in workflow
    assert "persist-credentials: false" in workflow
    assert 'test "$(git rev-parse HEAD)" = "$EXPECTED_HEAD_SHA"' in workflow
    assert REMOTE_GATE["required_workflow_name"] == "Form 4 Round44 pre-data CI"
    assert REMOTE_GATE["required_job_name"] == "predata"
    assert REMOTE_GATE["accepted_events_after_exact_checkout"] == ["pull_request"]
    assert REMOTE_GATE["same_repository_pull_request_required"] is True
    assert REMOTE_GATE["launch_remote_branch_current_head_recheck_required"] is True
    assert REMOTE_GATE["ci_sec_collection_authorized"] is False
    assert REMOTE_GATE["current_exact_suite_sec_request_count"] == 0
    assert REMOTE_GATE["required_runner"] == "ubuntu-24.04"
    assert REMOTE_GATE["required_python_version"] == "3.12.12"
    assert "permissions:\n  contents: read\n" in workflow
    assert "write" not in workflow
    assert "secrets." not in workflow
    assert "runs-on: ubuntu-24.04" in workflow
    assert "actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1" in workflow
    assert "actions/setup-python@5fda3b95a4ea91299a34e894583c3862153e4b97" in workflow
    assert "astral-sh/setup-uv@c771a70e6277c0a99b617c7a806ffedaca235ff9" in workflow
    assert 'python-version: "3.12.12"' in workflow
    assert 'UV_PYTHON: "3.12.12"' in workflow
    assert 'UV_PYTHON_DOWNLOADS: "never"' in workflow
    assert "uv sync --locked --extra dev --python 3.12.12" in workflow
    assert workflow.count("actions/checkout@") == 1
    assert workflow.index("Verify exact authorization head checkout") < workflow.index(
        "./.venv/bin/pytest"
    )
    for forbidden in (
        "environment:",
        "deploy:",
        "deploy-pages",
        "pages: write",
        "id-token:",
        "github.token",
        "sec.gov",
    ):
        assert forbidden not in workflow


def test_phase_a_is_strict_zero_state_and_cannot_start_monitoring() -> None:
    receipt = _receipt()
    assert receipt["monitor_start_boundary"] == MONITOR_START_BOUNDARY
    assert receipt["request_policy"] == REQUEST_POLICY
    assert receipt["evidence_boundary"] == EVIDENCE_BOUNDARY
    assert receipt["state_boundary"] == STATE_BOUNDARY
    assert receipt["permission"] == PERMISSION
    assert receipt["stable_codes"] == STABLE_CODES
    assert receipt["today_action"] == "今天不下單"

    assert REQUEST_POLICY["predata_sec_request_limit"] == 0
    assert REQUEST_POLICY["future_project_requests_per_second_max"] == 1
    assert REQUEST_POLICY["future_automatic_retries"] == 0
    assert REQUEST_POLICY["future_fallback_path_allowed"] is False
    assert MONITOR_START_BOUNDARY["monitor_start_receipt_created"] is False
    assert MONITOR_START_BOUNDARY["sec_collection_capability_issued"] is False
    assert MONITOR_START_BOUNDARY["sec_collection_enabled"] is False
    assert EVIDENCE_BOUNDARY["prospective_collector_implemented"] is False
    assert EVIDENCE_BOUNDARY["real_evidence_admission_authorized"] is False
    assert EVIDENCE_BOUNDARY["prospective_real_row_admitted"] is False

    for key in (
        "new_sec_request_count",
        "real_identifier_count",
        "real_filing_count",
        "candidate_selection_count",
        "candidate_allocation_count",
        "strategy_run_count",
        "paper_backfilled_trades",
        "real_money_action_usd",
        "congress_request_count",
        "congress_row_count",
        "congress_field_count",
    ):
        assert type(STATE_BOUNDARY[key]) is int
        assert STATE_BOUNDARY[key] == 0
    assert STATE_BOUNDARY["performance_result_present"] is False
    assert STATE_BOUNDARY["paper_authorized"] is False
    assert STATE_BOUNDARY["paper_state"] == "all_cash"
    assert STATE_BOUNDARY["paper_positions"] == []
    assert PERMISSION["monitor_start_creation"] is False
    assert PERMISSION["sec_network_collection"] is False
    assert PERMISSION["congress_collection"] is False


@pytest.mark.parametrize(
    ("section", "key", "value"),
    (
        ("state_boundary", "new_sec_request_count", 1),
        ("state_boundary", "new_sec_request_count", False),
        ("state_boundary", "candidate_selection_count", 1),
        ("state_boundary", "candidate_allocation_count", 1),
        ("state_boundary", "strategy_run_count", 1),
        ("state_boundary", "performance_result_present", True),
        ("state_boundary", "paper_authorized", True),
        ("state_boundary", "real_money_action_usd", False),
        ("state_boundary", "real_money_action_usd", 1),
        ("state_boundary", "congress_request_count", 1),
        ("permission", "sec_network_collection", True),
        ("permission", "candidate_selection", True),
        ("permission", "performance_readout", True),
        ("permission", "paper", True),
        ("permission", "real_money", True),
        ("permission", "congress_collection", True),
        ("remote_gate", "remote_gate_passed_in_this_receipt", True),
        ("monitor_start_boundary", "monitor_start_receipt_created", True),
        ("monitor_start_boundary", "sec_collection_capability_issued", True),
        ("evidence_boundary", "prospective_collector_implemented", True),
        ("evidence_boundary", "real_evidence_admission_authorized", True),
    ),
)
def test_result_or_authority_mutations_fail_with_one_stable_code(
    section: str,
    key: str,
    value: object,
) -> None:
    mutated = copy.deepcopy(_receipt())
    nested = mutated[section]
    assert isinstance(nested, dict)
    nested[key] = value
    mutated["receipt_sha256"] = canonical_sha256(mutated, omit="receipt_sha256")
    assert _error_code(lambda: _validate_static_content(mutated)) == STABLE_CODES[
        "authorization"
    ]


def test_schema_hash_identifier_and_binding_mutations_fail_closed() -> None:
    receipt = _receipt()

    extra = copy.deepcopy(receipt)
    extra["unexpected"] = None
    extra["receipt_sha256"] = canonical_sha256(extra, omit="receipt_sha256")
    assert _error_code(lambda: _validate_static_content(extra)) == STABLE_CODES[
        "authorization"
    ]

    missing = copy.deepcopy(receipt)
    missing.pop("today_action")
    missing["receipt_sha256"] = canonical_sha256(missing, omit="receipt_sha256")
    assert _error_code(lambda: _validate_static_content(missing)) == STABLE_CODES[
        "authorization"
    ]

    hash_drift = copy.deepcopy(receipt)
    hash_drift["receipt_sha256"] = "0" * 64
    assert _error_code(lambda: _validate_static_content(hash_drift)) == STABLE_CODES[
        "authorization"
    ]

    assert _error_code(
        lambda: _assert_identifier_free(
            {"nested": [{"accession": "synthetic"}]}
        )
    ) == STABLE_CODES["authorization"]
    _assert_identifier_free(
        {"repository_external_owner_only_start_receipt_required": True}
    )

    future = copy.deepcopy(receipt)
    future["frozen_at"] = "2099-01-01T00:00:00Z"
    future["receipt_sha256"] = canonical_sha256(future, omit="receipt_sha256")
    assert _error_code(lambda: _validate_static_content(future)) == STABLE_CODES[
        "authorization"
    ]
    assert _error_code(
        lambda: _assert_identifier_free(
            {"nested": ["0000123456-26-000001"]}
        )
    ) == STABLE_CODES["authorization"]
    assert _error_code(
        lambda: _load_exact_json('{"state": 0, "state": 1}')
    ) == STABLE_CODES["authorization"]

    binding_drift = copy.deepcopy(receipt)
    bindings = binding_drift["bindings"]
    assert isinstance(bindings, dict)
    protocol_binding = bindings["predata_protocol"]
    assert isinstance(protocol_binding, dict)
    protocol_binding["sha256"] = "0" * 64
    assert _error_code(lambda: _validate_bindings(binding_drift, ROOT)) == STABLE_CODES[
        "authorization"
    ]

    swapped = copy.deepcopy(receipt)
    swapped_bindings = swapped["bindings"]
    assert isinstance(swapped_bindings, dict)
    left = swapped_bindings["predata_protocol"]
    right = swapped_bindings["predata_tests"]
    assert isinstance(left, dict) and isinstance(right, dict)
    left["path"], right["path"] = right["path"], left["path"]
    left["sha256"], right["sha256"] = right["sha256"], left["sha256"]
    assert _error_code(lambda: _validate_bindings(swapped, ROOT)) == STABLE_CODES[
        "authorization"
    ]

    absolute = copy.deepcopy(receipt)
    absolute_bindings = absolute["bindings"]
    assert isinstance(absolute_bindings, dict)
    absolute_protocol = absolute_bindings["predata_protocol"]
    assert isinstance(absolute_protocol, dict)
    absolute_protocol["path"] = str((ROOT / PRE_DATA_BINDING_PATHS["predata_protocol"]).resolve())
    assert _error_code(lambda: _validate_bindings(absolute, ROOT)) == STABLE_CODES[
        "authorization"
    ]

    traversal = copy.deepcopy(receipt)
    traversal_bindings = traversal["bindings"]
    assert isinstance(traversal_bindings, dict)
    traversal_protocol = traversal_bindings["predata_protocol"]
    assert isinstance(traversal_protocol, dict)
    traversal_protocol["path"] = (
        "docs/0000123456-26-000001/../SHORT_TERM_FORM4_PROSPECTIVE_TRUST_ROOT_PROTOCOL.md"
    )
    assert _error_code(lambda: _validate_bindings(traversal, ROOT)) == STABLE_CODES[
        "authorization"
    ]


def test_public_receipt_contains_no_real_identifier_or_filing_path() -> None:
    rendered = RECEIPT.read_text(encoding="utf-8")
    assert ACCESSION_PATTERN.search(rendered) is None
    for forbidden_key in (
        '"accession"',
        '"cik"',
        '"issuer"',
        '"owner"',
        '"person"',
        '"ticker"',
        '"symbol"',
        '"raw_path"',
    ):
        assert forbidden_key not in rendered.lower()


def test_round44_entrypoint_is_locked_and_legacy_transport_is_rejected() -> None:
    with patch.object(socket, "create_connection") as create_connection:
        assert _error_code(assert_predata_network_locked) == STABLE_CODES["live_network"]
        create_connection.assert_not_called()

    phase_a_source = (
        ROOT / "usfddk/form4_prospective_trust_root.py"
    ).read_text(encoding="utf-8")
    assert "from .sec_edgar_client" not in phase_a_source
    assert "import SecEdgarClient" not in phase_a_source
    assert "build_opener(" not in phase_a_source
    assert "urlopen(" not in phase_a_source

    legacy_source = (ROOT / "usfddk/sec_edgar_client.py").read_text(encoding="utf-8")
    for frozen_false in (
        '"engineering_fetch_not_contemporaneous_evidence"',
        '"first_observed_external_anchor_present": False',
        '"receipt_externally_anchored": False',
        '"known_at": None',
        '"http_attempt_ledger_complete": False',
        '"encrypted_quarantine_verified": False',
        '"form4_admission_gate_passed": False',
    ):
        assert frozen_false in legacy_source


def test_phase_a_module_has_no_capability_mint_or_start_escape_hatch() -> None:
    assert _error_code(assert_predata_network_locked) == STABLE_CODES["live_network"]
    source = (ROOT / "usfddk/form4_prospective_trust_root.py").read_text(
        encoding="utf-8"
    )
    assert "def authorize_monitor_start" not in source
    assert "def mint" not in source
    assert "sec_collection_enabled\": True" not in source


def test_protocol_names_every_material_false_boundary_and_future_preflight() -> None:
    text = PROTOCOL.read_text(encoding="utf-8")
    for phrase in (
        "result-blind pre-data protocol freeze",
        "今天不下單",
        "Round42 的一次性 admission collection 已永久停在 `2/16`",
        "Version 5.5",
        "自動 retry 精確為 0",
        "不是本系統 `known_at`",
        "trusted_data_known_at = independent_anchor_received_at",
        "refs/pull/.../merge",
        "Pages 及 Daily workflow",
        "O_EXCL|O_NOFOLLOW",
        "fsync file 及 parent directory",
        "prospective_collector_implemented=false",
        "real_evidence_admission_authorized=false",
        "Congress PTR",
        "實金動作 US$0",
    ):
        assert phrase in text

    for code in STABLE_CODES.values():
        assert f"`{code}`" in text
