from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "docs/SHORT_TERM_FORM4_MULTIPATH_FORWARD_PROTOCOL.md"
DESIGN = ROOT / "docs/SHORT_TERM_ACTOR_DISCLOSURE_DYNAMIC_SELECTION_DESIGN.md"
RECEIPT = ROOT / "artifacts/short_term_form4_multipath_forward_protocol_receipt.json"


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


def test_round43_receipt_binds_all_frozen_bytes_and_parent_commit() -> None:
    receipt = _receipt()
    assert receipt["schema_version"] == 1
    assert receipt["research_round"] == 43
    assert receipt["status"] == (
        "result_blind_forward_protocol_frozen_before_new_sec_request_"
        "candidate_or_performance"
    )
    assert receipt["receipt_sha256"] == _canonical_hash(receipt)

    bindings = [
        receipt["protocol"],
        receipt["dynamic_selection_design"],
        receipt["parent_round42_stop"]["validation"],
        receipt["parent_round42_stop"]["report"],
        receipt["parent_round41_candidate"]["protocol_v1_1"],
        receipt["parent_round41_candidate"]["receipt_v1_1"],
        receipt["global_trial_ledger"]["protocol"],
        receipt["global_trial_ledger"]["artifact"],
        receipt["offline_implementation"]["multipath_resolver"],
        receipt["offline_implementation"]["multipath_tests"],
        receipt["offline_implementation"]["forward_contract"],
        receipt["offline_implementation"]["forward_contract_tests"],
        receipt["offline_implementation"]["protocol_tests"],
    ]
    for binding in bindings:
        assert _sha256(ROOT / binding["path"]) == binding["sha256"]

    parent = receipt["parent_code_commit"]["sha"]
    assert re.fullmatch(r"[0-9a-f]{40}", parent)
    completed = subprocess.run(
        ["git", "merge-base", "--is-ancestor", parent, "HEAD"],
        cwd=ROOT,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 0
    protocol_text = PROTOCOL.read_text(encoding="utf-8")
    assert f"FrozenAt：`{receipt['frozen_at']}`" in protocol_text


def test_round42_failure_is_immutable_and_cannot_authorize_round43() -> None:
    receipt = _receipt()
    parent = receipt["parent_round42_stop"]
    payload = json.loads((ROOT / parent["validation"]["path"]).read_text(encoding="utf-8"))
    assert payload["status"] == parent["status"] == "stopped_no_admission_claim"
    assert payload["stop_reasons"] == [parent["stop_code"]]
    assert payload["admission_controls"]["passed"] == parent["admission_passed"] == 2
    assert payload["admission_controls"]["total"] == parent["admission_total"] == 16
    assert parent["reuse_or_restart_allowed"] is False
    assert payload["state_boundary"]["candidate_selection_count"] == 0
    assert payload["state_boundary"]["strategy_run_count"] == 0
    assert payload["state_boundary"]["performance_present"] is False


def test_multipath_and_forward_readout_contract_are_exactly_frozen() -> None:
    receipt = _receipt()
    assert receipt["multipath_contract"] == {
        "minimum_paths": 1,
        "maximum_paths": 10,
        "identity": ["normalized_cik", "exact_archive_path"],
        "canonical_sort": ["cik_zero_padded_to_10", "exact_path_bytes"],
        "carrier_rule": "d0_xor_d1",
        "d1_max_calendar_days_after_d0": 4,
        "row_filing_date_remains_bulk_filing_date": True,
        "path_count_is_actor_count": False,
        "fallback_path_allowed": False,
    }
    assert receipt["prospective_clock"] == {
        "known_at_basis": "prospective_first_observed",
        "known_at_formula": (
            "max(index_pair_first_observed_at,canonical_submission_first_observed_at)"
        ),
        "historical_backfill_allowed": False,
        "accepted_at_allowed_as_known_at": False,
        "decision_session": "first_full_XNYS_close_strictly_after_known_at",
        "trade_session": "next_XNYS_raw_open_after_decision_session",
    }
    assert receipt["readout_contract"] == {
        "fixed_session": 504,
        "minimum_candidate_allocations": 100,
        "minimum_distinct_issuers": 50,
        "interim_performance_allowed": False,
        "extend_if_underpowered": False,
        "underpowered_status": "insufficient_power_no_performance_readout",
        "comparison_family_reused_from_round41": True,
    }
    text = PROTOCOL.read_text(encoding="utf-8")
    for phrase in (
        "只在 `d0` 或 `d1` 其中一個 index 出現",
        "prospective_first_observed",
        "insufficient_power_no_performance_readout",
        "不延長",
        "今天不下單",
    ):
        assert phrase in text


def test_trial_ledger_and_zero_action_boundaries_do_not_move() -> None:
    receipt = _receipt()
    ledger_binding = receipt["global_trial_ledger"]
    ledger = json.loads(
        (ROOT / ledger_binding["artifact"]["path"]).read_text(encoding="utf-8")
    )
    assert len(ledger["entries"]) == ledger_binding["entry_count"] == 12
    assert ledger["chain_head_sha256"] == ledger_binding["chain_head_sha256"]
    assert ledger["current_lower_bound"] == ledger_binding["lower_bound_before"] == 6287
    assert ledger_binding["round43_increment"] == 0
    assert ledger_binding["lower_bound_after"] == 6287
    assert ledger_binding["ledger_append_authorized"] is False

    assert receipt["state_at_freeze"] == {
        "round43_sec_requests": 0,
        "prospective_accessions": 0,
        "candidate_allocations": 0,
        "strategy_run_count": 0,
        "performance_present": False,
        "form4_admission_passed": 2,
        "form4_admission_total": 16,
    }
    assert receipt["permission"] == {
        "protocol_freeze": True,
        "network_collection": False,
        "historical_backfill": False,
        "candidate_selection": False,
        "performance_readout": False,
        "paper": False,
        "real_money": False,
    }
    assert receipt["paper"] == {
        "authorized": False,
        "state": "all_cash",
        "backfilled_trades": 0,
        "positions": [],
    }
    assert receipt["real_money_action_usd"] == 0
    assert receipt["today_action"] == "今天不下單"


def test_dynamic_design_keeps_congress_and_fame_out_of_the_sec_signal() -> None:
    receipt = _receipt()
    assert receipt["source_boundary"] == {
        "allowed": ["sec_form_4", "sec_form_4_a"],
        "congress_ptr_collection_allowed": False,
        "congress_ptr_strategy_allowed": False,
        "celebrity_or_name_weight_allowed": False,
        "entrepreneur_is_sec_role": False,
    }
    text = DESIGN.read_text(encoding="utf-8")
    for phrase in (
        "Congress PTR：法律未清，不得收集",
        "都不是 SEC 法定角色",
        "單一股票單一狀態",
        "pit_pool_equal_weight_monthly",
        "minimal_execution_clock_control",
        "今天不下單",
    ):
        assert phrase in text
    rendered = json.dumps(receipt, ensure_ascii=False, sort_keys=True).casefold()
    for forbidden in ("cagr", "sharpe", "drawdown", "pnl", "latest_pick"):
        assert forbidden not in rendered
