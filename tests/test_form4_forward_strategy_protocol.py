from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

from usfddk.form4_forward_strategy_kernel import (
    COMPARISON_FAMILY,
    FORM4_FORWARD_STRATEGY_ERROR_CODES,
    audit_round46_kernel_contract,
    validate_public_aggregate_progress,
)
from usfddk.form4_forward_strategy_trial_ledger import (
    BASE_CHAIN_HEAD_SHA256,
    COMBINED_LOWER_BOUND,
    ROUND46_INCREMENT,
    audit_round46_trial_extension,
)

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "docs/SHORT_TERM_FORM4_FORWARD_STRATEGY_EVIDENCE_PROTOCOL.md"
RECEIPT = ROOT / "artifacts/short_term_form4_forward_strategy_evidence_protocol_receipt.json"
WORKFLOW = ROOT / ".github/workflows/form4-round46-forward-strategy-ci.yml"
ROUND45_COMMIT = "568ccc5c695e3f0546d48617f95a19a59f99c3d9"
ROUND45_RECEIPT_FILE_SHA256 = (
    "bf81e6d6ef96fb83e140823c1fc0a40c6f33fdf191345099bcab6255f2cc7d32"
)
ROUND45_RECEIPT_CANONICAL_SHA256 = (
    "e2e255334660f17d862ce42298b8759e8ba5f9480bc56a338a03f995b21a7947"
)
FROZEN_AT = "2026-08-10T08:42:17Z"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _canonical_sha256(value: dict[str, object]) -> str:
    core = {key: item for key, item in value.items() if key != "receipt_sha256"}
    return hashlib.sha256(
        json.dumps(
            core,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


def _receipt() -> dict[str, object]:
    value = json.loads(RECEIPT.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def _assert_binding(binding: object) -> None:
    assert isinstance(binding, dict)
    assert set(binding) == {"path", "sha256"}
    path = binding["path"]
    digest = binding["sha256"]
    assert isinstance(path, str)
    assert isinstance(digest, str)
    assert not Path(path).is_absolute()
    assert ".." not in Path(path).parts
    assert _sha256(ROOT / path) == digest


def test_round46_receipt_is_canonical_and_binds_every_effective_byte() -> None:
    receipt = _receipt()
    assert receipt["schema_version"] == "us_fddk.short_term_form4_forward_strategy_evidence.v1"
    assert receipt["research_round"] == 46
    assert receipt["status"] == "frozen_result_blind_forward_only_no_real_data"
    assert receipt["frozen_at"] == FROZEN_AT
    assert receipt["receipt_sha256"] == _canonical_sha256(receipt)
    bindings = receipt["bindings"]
    assert isinstance(bindings, dict)
    assert len(bindings) >= 18
    for binding in bindings.values():
        _assert_binding(binding)


def test_round46_commit_is_one_exact_child_of_the_passing_round45_parent() -> None:
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, check=True, text=True
    ).stdout.strip()
    parent = subprocess.run(
        ["git", "rev-parse", "HEAD^"], cwd=ROOT, capture_output=True, check=True, text=True
    ).stdout.strip()
    lineage = subprocess.run(
        ["git", "rev-list", "--parents", "-n", "1", "HEAD"],
        cwd=ROOT,
        capture_output=True,
        check=True,
        text=True,
    ).stdout.split()
    child_commit_count = subprocess.run(
        ["git", "rev-list", "--count", f"{ROUND45_COMMIT}..HEAD"],
        cwd=ROOT,
        capture_output=True,
        check=True,
        text=True,
    ).stdout.strip()
    assert len(head) == 40
    assert parent == ROUND45_COMMIT
    assert lineage == [head, ROUND45_COMMIT]
    assert child_commit_count == "1"
    receipt = _receipt()
    parent_contract = receipt["round45_parent"]
    assert isinstance(parent_contract, dict)
    assert parent_contract["commit"] == ROUND45_COMMIT
    assert parent_contract["branch"] == "codex/round45-form4-monitor-start"


def test_round45_parent_receipt_and_successful_exact_head_ci_are_frozen_as_history() -> None:
    receipt = _receipt()
    parent = receipt["round45_parent"]
    assert isinstance(parent, dict)
    authorization = parent["authorization_receipt"]
    assert isinstance(authorization, dict)
    path = authorization["path"]
    assert isinstance(path, str)
    current_bytes = (ROOT / path).read_bytes()
    historical_bytes = subprocess.run(
        ["git", "show", f"{ROUND45_COMMIT}:{path}"],
        cwd=ROOT,
        capture_output=True,
        check=True,
    ).stdout
    assert current_bytes == historical_bytes
    assert hashlib.sha256(current_bytes).hexdigest() == ROUND45_RECEIPT_FILE_SHA256
    parent_receipt = json.loads(current_bytes.decode("utf-8"))
    assert parent_receipt["receipt_sha256"] == ROUND45_RECEIPT_CANONICAL_SHA256
    assert authorization["file_sha256"] == ROUND45_RECEIPT_FILE_SHA256
    assert authorization["canonical_sha256"] == ROUND45_RECEIPT_CANONICAL_SHA256
    assert parent["ci"] == {
        "workflow_name": "Form 4 Round45 monitor-start CI",
        "workflow_path": ".github/workflows/form4-round45-monitor-start-ci.yml",
        "run_id": 31369588741,
        "job_name": "monitor-start",
        "job_id": 93395360805,
        "head_sha": ROUND45_COMMIT,
        "event": "pull_request",
        "status": "completed",
        "conclusion": "success",
        "completed_at": "2026-08-10T08:20:19Z",
    }


def test_versioned_trial_successor_is_the_only_effective_6295_tip() -> None:
    audit = audit_round46_trial_extension(root=ROOT)
    assert audit["passed"] is True
    assert audit["base_lower_bound"] == 6_287
    assert audit["round46_increment"] == ROUND46_INCREMENT == 8
    assert audit["combined_lower_bound"] == COMBINED_LOWER_BOUND == 6_295
    assert audit["combined_tip_sha256"] != BASE_CHAIN_HEAD_SHA256
    assert audit["seen_result"] is False
    assert audit["paper"]["state"] == "all_cash"
    assert audit["real_money_action_usd"] == 0


def test_kernel_freeze_is_zero_real_data_zero_performance_and_not_production_ready() -> None:
    audit = audit_round46_kernel_contract(root=ROOT)
    assert audit["paths"]["tracked_files_present"] is True
    assert audit["fixed_controls"]["comparison_family"] == list(COMPARISON_FAMILY)
    assert audit["fixed_controls"]["global_trials_after"] == 6_295
    assert audit["fixed_controls"]["control_assignments_complete"] is False
    assert audit["fixed_controls"]["durable_private_writer_implemented"] is False
    assert audit["fixed_controls"]["readout_implementation_present"] is False
    assert audit["mutation_attacks"] == list(FORM4_FORWARD_STRATEGY_ERROR_CODES)
    assert audit["state_at_freeze"] == {
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
    }
    assert audit["permission"] == {
        "synthetic_kernel": True,
        "monitor_start": False,
        "sec_collection": False,
        "candidate_publication": False,
        "performance": False,
        "paper": False,
        "real_money": False,
    }
    assert audit["today_action"] == "今天不下單"


def test_public_status_is_exact_redacted_and_contains_no_progress_counts() -> None:
    public = {
        "schema_version": "us_fddk.short_term_form4_forward_public_status.v1",
        "status": "collecting_no_readout",
        "today_action": "今天不下單",
        "performance_present": False,
        "paper_authorized": False,
        "paper_positions": 0,
        "real_money_action_usd": 0,
        "manifest_sha256": "",
    }
    public["manifest_sha256"] = hashlib.sha256(
        json.dumps(
            {key: value for key, value in public.items() if key != "manifest_sha256"},
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()
    assert validate_public_aggregate_progress(public) == public
    rendered = json.dumps(public, ensure_ascii=False, sort_keys=True)
    for forbidden in (
        "candidate",
        "allocation",
        "issuer",
        "token",
        "ticker",
        "accession",
        "chain_head",
        "prospective_sessions",
    ):
        assert forbidden not in rendered


def test_workflow_is_exact_base_exact_head_read_only_and_has_no_network_or_deploy() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")
    assert "pull_request:" in workflow
    assert "workflow_dispatch:" not in workflow
    assert "schedule:" not in workflow
    assert "permissions:\n  contents: read\n" in workflow
    assert "persist-credentials: false" in workflow
    assert "github.event.pull_request.head.repo.full_name == github.repository" in workflow
    assert "github.event.pull_request.base.repo.full_name == github.repository" in workflow
    assert "github.event.pull_request.base.ref == 'codex/round45-form4-monitor-start'" in workflow
    assert f"github.event.pull_request.base.sha == '{ROUND45_COMMIT}'" in workflow
    assert f"EXPECTED_BASE_SHA: {ROUND45_COMMIT}" in workflow
    assert 'test "$(git rev-parse HEAD^)" = "$EXPECTED_BASE_SHA"' in workflow
    assert 'set -- $(git rev-list --parents -n 1 "$EXPECTED_HEAD_SHA")' in workflow
    assert 'test "$#" -eq 2' in workflow
    assert 'test "$2" = "$EXPECTED_BASE_SHA"' in workflow
    assert (
        'test "$(git rev-list --count "${EXPECTED_BASE_SHA}..${EXPECTED_HEAD_SHA}")" = "1"'
        in workflow
    )
    assert 'ref: ${{ github.event.pull_request.head.sha }}' in workflow
    assert 'test -z "$(git status --porcelain=v1 --untracked-files=all)"' in workflow
    for network_guard in (
        "socket.socket.connect = deny_inet_connect",
        "socket.socket.connect_ex = deny_inet_connect_ex",
        "socket.create_connection = deny_create_connection",
        "socket.getaddrinfo = local_getaddrinfo",
        "Round46 CI forbids network sockets during tests",
        "Round46 CI forbids external DNS during tests",
    ):
        assert network_guard in workflow
    assert workflow.index("uv sync --locked") < workflow.index(
        "socket.socket.connect = deny_inet_connect"
    ) < workflow.index("pytest.main(")
    for required in (
        "tests/test_form4_monitor_start.py",
        "tests/test_form4_forward_strategy_kernel.py",
        "tests/test_form4_forward_strategy_trial_ledger.py",
        "tests/test_form4_forward_strategy_protocol.py",
    ):
        assert required in workflow
    for forbidden in (
        "--deselect=",
        "sec.gov",
        "curl ",
        "wget ",
        "secrets.",
        "deploy-pages",
        "pages: write",
        "id-token: write",
    ):
        assert forbidden not in workflow


def test_protocol_freezes_time_order_maturity_privacy_and_no_trade_boundaries() -> None:
    text = PROTOCOL.read_text(encoding="utf-8")
    for phrase in (
        f"FrozenAt：`{FROZEN_AT}`",
        ROUND45_COMMIT,
        ROUND45_RECEIPT_CANONICAL_SHA256,
        "completed_round_trips_or_forced_settlements >= 100",
        "distinct_issuers_completed >= 50",
        "integrity_outages == 0",
        "eligible_pending_fixed_maturation_embargo",
        "eligible_for_pre_frozen_readout_engine",
        "D514",
        "domain-separated HMAC-SHA-256",
        "combined-tip validator",
        "6,295",
        "daily_completeness_receipt_sha256",
        "pit_receipt_sha256",
        "integrity_outage=false",
        "durable private writer / readout implementation = false / false",
        "Congress requests / rows / fields = 0 / 0 / 0",
        "今天不下單",
    ):
        assert phrase in text
