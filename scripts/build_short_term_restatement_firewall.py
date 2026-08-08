from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

from usfddk.restatement_firewall import (
    PROTOCOL_SHA256,
    RestatementFirewallError,
    frozen_decision_summary,
    synthetic_as_known_envelope,
    validate_envelope,
    validate_result,
)

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "artifacts/short_term_restatement_firewall_validation.json"
SITE_DATA = ROOT / "site/data/short-term-restatement-firewall.json"


def _expect_code(envelope: dict[str, Any], code: str) -> bool:
    try:
        validate_envelope(envelope, root=ROOT)
    except RestatementFirewallError as exc:
        return exc.code == code
    return False


def _attack_cases() -> dict[str, tuple[dict[str, Any], str]]:
    base = synthetic_as_known_envelope()
    cases: dict[str, tuple[dict[str, Any], str]] = {}

    future_restatement = copy.deepcopy(base)
    future_restatement["selected_release_ids"] = ["R-20260701-v2"]
    future_restatement["rows"] = [
        {
            **row,
            "release_id": "R-20260701-v2",
            "source_record_id": f"{row['source_record_id']}-V2",
        }
        for row in base["rows"]
    ]
    cases["future_restatement"] = (future_restatement, "restatement_substitution")

    future_plain = copy.deepcopy(base)
    future_plain["release_ledger"].append(
        {
            "provider": "synthetic-provider",
            "source_id": "CRSP_STK_DLY",
            "release_id": "R-20260720-v1",
            "available_at": "2026-07-20T12:00:00Z",
            "data_cutoff": "2026-07-20",
            "is_restatement": False,
            "supersedes_release_id": None,
            "content_sha256": "a" * 64,
            "row_count": 1,
        }
    )
    future_plain["release_receipts"]["R-20260720-v1"] = {
        "content_sha256": "a" * 64,
        "row_count": 1,
    }
    future_plain["selected_release_ids"] = ["R-20260720-v1"]
    future_plain["rows"] = [
        {
            "source_id": "CRSP_STK_DLY",
            "release_id": "R-20260720-v1",
            "source_record_id": "ROW-FUTURE",
            "observation_date": "2026-07-20",
            "effective_at": "2026-07-20T20:00:00Z",
        }
    ]
    cases["future_release"] = (future_plain, "future_release_leakage")

    duplicate = copy.deepcopy(base)
    duplicate["release_ledger"].append(copy.deepcopy(duplicate["release_ledger"][0]))
    cases["duplicate_release"] = (duplicate, "release_id_duplicate")

    schema = copy.deepcopy(base)
    schema["rows"][0].pop("effective_at")
    cases["row_schema"] = (schema, "release_schema_mismatch")

    chain = copy.deepcopy(base)
    chain["release_ledger"][1]["supersedes_release_id"] = "R-20260701-v2"
    cases["chain_cycle"] = (chain, "supersedes_chain_invalid")

    receipt = copy.deepcopy(base)
    receipt["release_receipts"]["R-20260701-v1"]["row_count"] = 99
    cases["receipt_tamper"] = (receipt, "release_receipt_mismatch")
    return cases


def _write(payload: dict[str, Any]) -> None:
    serialized = json.dumps(
        payload, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False
    ) + "\n"
    ARTIFACT.parent.mkdir(parents=True, exist_ok=True)
    SITE_DATA.parent.mkdir(parents=True, exist_ok=True)
    ARTIFACT.write_text(serialized, encoding="utf-8")
    SITE_DATA.write_text(serialized, encoding="utf-8")


def main() -> int:
    good = synthetic_as_known_envelope()
    good_summary = validate_envelope(good, root=ROOT)
    controls: dict[str, bool] = {
        "protocol_integrity": bool(good_summary["protocol_integrity"]["passed"]),
        "as_known_mode": good_summary["mode"] == "as_known",
        "only_eligible_release_selected": good_summary["future_selected_release_ids"] == [],
        "row_receipts_match": good_summary["row_count_by_release"] == {"R-20260701-v1": 2},
        "supersedes_chain_retained": "R-20260701-v2" in [
            r["release_id"] for r in good["release_ledger"]
        ],
        "restatement_not_used_as_known": good_summary["restatement_release_ids"] == [],
        "strategy_input_locked": good_summary["strategy_input_allowed"] is False,
        "formal_backtest_locked": good_summary["formal_backtest_authorized"] is False,
        "paper_and_cash_locked": good_summary["paper_state"] == "all_cash"
        and good_summary["real_money_action_usd"] == 0,
    }
    attacks: dict[str, bool] = {}
    attack_codes: dict[str, str] = {}
    for name, (envelope, expected) in _attack_cases().items():
        attacks[name] = _expect_code(envelope, expected)
        attack_codes[name] = expected

    final_revised = copy.deepcopy(good)
    final_revised["mode"] = "final_revised"
    final_revised["selected_release_ids"] = ["R-20260701-v2"]
    final_revised["rows"] = [
        {
            **row,
            "release_id": "R-20260701-v2",
            "source_record_id": f"{row['source_record_id']}-V2",
        }
        for row in good["rows"]
    ]
    final_summary = validate_envelope(final_revised, root=ROOT)
    final_attack = copy.deepcopy(final_summary)
    final_attack["strategy_input_allowed"] = True
    final_attack["research_round"] = 34
    final_attack["protocol_sha256"] = PROTOCOL_SHA256
    final_attack.update(frozen_decision_summary())
    final_revised_rejected = False
    try:
        validate_result(final_attack, root=ROOT)
    except RestatementFirewallError as exc:
        final_revised_rejected = exc.code == "final_revised_strategy_substitution"
        attack_codes["final_revised_strategy"] = exc.code
    attacks["final_revised_strategy"] = final_revised_rejected

    result_probe = {
        "research_round": 34,
        "protocol_sha256": PROTOCOL_SHA256,
        **good_summary,
        **frozen_decision_summary(),
    }
    protocol_attack = copy.deepcopy(result_probe)
    protocol_attack["protocol_sha256"] = "0" * 64
    try:
        validate_result(protocol_attack, root=ROOT)
        protocol_rejected = False
        protocol_code = "not_rejected"
    except RestatementFirewallError as exc:
        protocol_rejected = exc.code == "release_protocol_mismatch"
        protocol_code = exc.code
    attacks["protocol_hash"] = protocol_rejected
    attack_codes["protocol_hash"] = protocol_code

    decision_attack = copy.deepcopy(result_probe)
    decision_attack["paper_state"] = "positions"
    try:
        validate_result(decision_attack, root=ROOT)
        decision_rejected = False
        decision_code = "not_rejected"
    except RestatementFirewallError as exc:
        decision_rejected = exc.code == "release_decision_boundary_violation"
        decision_code = exc.code
    attacks["decision_boundary"] = decision_rejected
    attack_codes["decision_boundary"] = decision_code

    result: dict[str, Any] = {
        "schema_version": 1,
        "research_round": 34,
        "status": "synthetic_firewall_controls_passed",
        "protocol_sha256": PROTOCOL_SHA256,
        "mode": good_summary["mode"],
        "requested_as_of": good_summary["requested_as_of"],
        "as_known_integrity_passed": good_summary["as_known_integrity_passed"],
        "strategy_input_allowed": good_summary["strategy_input_allowed"],
        "fixture": {
            "provider": "synthetic-only",
            "mode": good_summary["mode"],
            "requested_as_of": good_summary["requested_as_of"],
            "selected_release_ids": good_summary["selected_release_ids"],
            "restatement_release_ids_in_ledger": [
                r["release_id"]
                for r in good["release_ledger"]
                if r["is_restatement"]
            ],
        },
        "control_summary": {
            "passed": sum(controls.values()),
            "total": len(controls),
            "all_passed": all(controls.values()),
        },
        "controls": controls,
        "attack_summary": {
            "passed": sum(attacks.values()),
            "total": len(attacks),
            "all_passed": all(attacks.values()),
        },
        "attacks": attacks,
        "attack_codes": attack_codes,
        "as_known_summary": good_summary,
        "final_revised_summary": final_summary,
        "raw_provider_bytes_persisted": False,
        **frozen_decision_summary(),
        "next_action": (
            "取得授權 provider package 後，將每一份 release ledger 綁定實際 export／"
            "row receipt，再按 as-known 模式驗收；synthetic 9/9 不等於正式數據通過。"
        ),
    }
    validate_result(result, root=ROOT)
    _write(result)
    print(
        json.dumps(
            {
                "status": result["status"],
                "control_summary": result["control_summary"],
                "attack_summary": result["attack_summary"],
                "formal_backtest_authorized": False,
                "paper_state": "all_cash",
                "real_money_action_usd": 0,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if result["control_summary"]["all_passed"] and result["attack_summary"]["all_passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
