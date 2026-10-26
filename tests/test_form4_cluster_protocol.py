import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

from usfddk.disclosure_known_at import FORM4_SEMANTICS

ROOT = Path(__file__).resolve().parents[1]
V1_DRAFT_RECEIPT = ROOT / "artifacts/short_term_form4_cluster_protocol_receipt.json"
RECEIPT = ROOT / "artifacts/short_term_form4_cluster_protocol_amendment_v1_1_receipt.json"
SUPERSESSION_SEAL = ROOT / "artifacts/short_term_form4_cluster_v1_draft_supersession_seal.json"
LEDGER_APPEND_SEAL = ROOT / "artifacts/short_term_form4_cluster_ledger_append_seal.json"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _utc_timestamp(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    assert parsed.tzinfo is not None
    assert parsed.utcoffset() is not None
    return parsed.astimezone(UTC)


def test_form4_cluster_protocol_was_frozen_before_data_or_results() -> None:
    receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
    assert receipt["research_round"] == 41
    assert receipt["status"] == (
        "v1_1_frozen_before_authorized_form4_data_candidate_selection_strategy_"
        "run_or_performance_result"
    )
    for key in (
        "historical_v1_protocol",
        "historical_v1_draft_receipt",
        "historical_v1_draft_supersession_seal",
        "disclosure_v1_1_amendment",
        "disclosure_v1_1_amendment_receipt",
        "form4_v1_1_amendment",
        "global_trial_ledger_protocol",
    ):
        binding = receipt[key]
        assert _sha256(ROOT / binding["path"]) == binding["sha256"]
    assert receipt["source_scope"] == ["sec_form_4"]
    assert len(receipt["comparison_family"]) == 8
    assert len(set(receipt["comparison_family"])) == 8
    assert receipt["global_trial_correction"] == {
        "historical_v1_draft_lower_bound_before": 6_240,
        "omitted_seen_round24_to_round28_minimum": 39,
        "corrected_lower_bound_before": 6_279,
        "reserved_trial_increment": 8,
        "current_lower_bound_after": 6_287,
        "exact_global_count_claimed": False,
    }
    assert receipt["data_state_at_freeze"] == {
        "global_disclosure_readiness_passed": 2,
        "global_disclosure_readiness_total": 20,
        "form4_specific_admission_passed": 0,
        "form4_specific_admission_total": 16,
        "authorized_real_form4_rows": 0,
        "candidate_selection_count": 0,
        "strategy_run_count": 0,
        "performance_result_present": False,
        "twenty_year_form4_coverage_validated": False,
    }
    assert receipt["permission"] == {
        "candidate_specification_frozen": True,
        "authorized_data_intake": False,
        "backtest": False,
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

    assert _sha256(V1_DRAFT_RECEIPT) == (
        "077b877f7b04acf5aa9fcbcb2efcd4e99bc894f6a85846a616f549745126b383"
    )
    historical = json.loads(V1_DRAFT_RECEIPT.read_text(encoding="utf-8"))
    disclosure = json.loads(
        (
            ROOT / "artifacts/short_term_disclosure_known_at_protocol_amendment_v1_1_receipt.json"
        ).read_text(encoding="utf-8")
    )
    supersession = json.loads(SUPERSESSION_SEAL.read_text(encoding="utf-8"))
    assert historical["status"].startswith(
        "frozen_after_official_documentation_and_isolated_semantic_review"
    )
    assert supersession["historical_v1_receipt_immutable"]["sha256"] == _sha256(V1_DRAFT_RECEIPT)
    assert (
        _utc_timestamp(historical["frozen_at"])
        < _utc_timestamp(disclosure["effective_at"])
        < _utc_timestamp(supersession["sealed_at"])
        < _utc_timestamp(receipt["frozen_at"])
    )


def test_round41_ledger_append_seal_binds_receipt_prefix_and_final_ledger() -> None:
    receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
    ledger_path = ROOT / "artifacts/short_term_global_trial_ledger.json"
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    seal = json.loads(LEDGER_APPEND_SEAL.read_text(encoding="utf-8"))

    assert seal["preregistration_receipt_v1_1"]["sha256"] == _sha256(RECEIPT)
    assert seal["global_trial_ledger_protocol"] == receipt["global_trial_ledger_protocol"]
    assert seal["ledger_before_round41"] == {
        "entry_count": receipt["ledger_before_round41"]["prefix_entry_count"],
        "current_lower_bound": receipt["ledger_before_round41"]["current_lower_bound"],
        "chain_head_sha256": receipt["ledger_before_round41"]["chain_head_sha256"],
    }
    round41 = ledger["entries"][11]
    assert seal["round41_entry"] == {
        "sequence": round41["sequence"],
        "family_id": round41["family_id"],
        "protocol_v1_1_sha256": round41["source_bindings"][0]["sha256"],
        "preregistration_receipt_v1_1_sha256": round41["source_bindings"][1]["sha256"],
        "entry_sha256": round41["entry_sha256"],
    }
    assert seal["ledger_after_round41"] == {
        "path": "artifacts/short_term_global_trial_ledger.json",
        "sha256": _sha256(ledger_path),
        "entry_count": len(ledger["entries"]),
        "current_lower_bound": ledger["current_lower_bound"],
        "chain_head_sha256": ledger["chain_head_sha256"],
    }
    assert _utc_timestamp(receipt["frozen_at"]) < _utc_timestamp(seal["sealed_at"])
    assert seal["state_at_seal"]["paper_authorized"] is False
    assert seal["state_at_seal"]["real_money_action_usd"] == 0


def test_result_blind_preregistration_amendment_never_authorizes_execution() -> None:
    receipt = json.loads(
        (
            ROOT / "artifacts/short_term_disclosure_known_at_protocol_amendment_v1_1_receipt.json"
        ).read_text(encoding="utf-8")
    )
    assert receipt["state_at_freeze"] == {
        "authorized_real_rows": 0,
        "candidate_selection_count": 0,
        "strategy_run_count": 0,
        "performance_result_present": False,
        "paper_authorized": False,
        "real_money_action_usd": 0,
    }
    assert receipt["permission"] == {
        "result_blind_preregistration": True,
        "data_intake": False,
        "backtest": False,
        "paper": False,
        "real_money": False,
    }


def test_form4_purchase_and_sale_semantics_preserve_private_transactions() -> None:
    assert FORM4_SEMANTICS["P"] == "open_or_private_purchase"
    assert FORM4_SEMANTICS["S"] == "open_or_private_sale"
    assert FORM4_SEMANTICS["A"].endswith("_non_signal")
    assert FORM4_SEMANTICS["F"].endswith("_non_signal")
    assert FORM4_SEMANTICS["M"].endswith("_non_signal")
    assert FORM4_SEMANTICS["G"].endswith("_non_signal")


def test_form4_protocol_keeps_congress_and_paper_out_of_scope() -> None:
    text = (ROOT / "docs/SHORT_TERM_FORM4_CLUSTER_PROTOCOL.md").read_text(encoding="utf-8")
    assert "Congress PTR、13F、13D 及 13G 不混入這個候選" in text
    assert "accepted_at` 不得冒充真正公開時間" in text
    assert "十個固定 10% 槽" in text
    assert "每個真實資產腿 10 bps" in text
    assert "Paper 全現金" in text
    assert "今天不下單" in text


def test_form4_v1_1_closes_coverage_dedupe_and_cluster_retry_gaps() -> None:
    text = (ROOT / "docs/SHORT_TERM_FORM4_CLUSTER_PROTOCOL_AMENDMENT_V1_1.md").read_text(
        encoding="utf-8"
    )
    assert "executable admission 為 **0/16**" in text
    assert "historical_backfill_fallback_count" in text
    assert "form4_twenty_year_admission_failed" in text
    assert "capital_group_token" in text
    assert "amendment_mapping_ambiguous" in text
    assert "closed_unconfirmed" in text
    assert "下一個可成立" in text
    assert "matched_rate=1.0" in text
    assert "delta CAGR≥0.50pp" in text
