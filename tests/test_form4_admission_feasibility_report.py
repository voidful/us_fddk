from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from scripts.build_short_term_form4_admission_feasibility_report import (
    ARTIFACT,
    REPORT,
    SITE_DATA,
    canonical_sha256,
    load_public_payload,
    render_report,
    validate_public_payload,
)

ROOT = Path(__file__).resolve().parents[1]


def test_round42_public_result_is_exactly_redacted_two_of_sixteen() -> None:
    payload, _ = load_public_payload()
    validate_public_payload(payload)
    assert payload["status"] == "stopped_no_admission_claim"
    assert payload["fixed_quarters"] == ["2006Q1", "2016Q3", "2026Q2"]
    assert payload["sample_count"] == 12
    assert payload["private_manifest_sha256"] == (
        "3919e075c9c1deffd2ceabee641c4520d69b50c298dcf2f68ae918e5de1fa053"
    )
    assert payload["admission_controls"]["passed"] == 2
    assert payload["admission_controls"]["total"] == 16
    assert payload["stop_reasons"] == [
        "form4_feasibility_daily_index_missing_or_ambiguous"
    ]
    assert [
        gate["id"] for gate in payload["admission_controls"]["gates"] if gate["passed"]
    ] == ["01", "04"]
    assert payload["attack_results"]["collection_stop_receipt"] == {
        "admission_core_sha256": (
            "75350c3e047cd78b46595d70b7c571651ff779baa562acb7f8c8d41d83e620f4"
        ),
        "canonicalization": "json_utf8_sort_keys_compact_no_nan_v1",
        "cold_replay_completed": False,
        "complete_submission_requests": 0,
        "completed_http_requests": 5,
        "failure_phase": "post_fetch_validation_failed",
        "post_fetch_local_validation_failures": 1,
        "private_manifest_sha256": (
            "3919e075c9c1deffd2ceabee641c4520d69b50c298dcf2f68ae918e5de1fa053"
        ),
        "receipt_sha256": (
            "614950cd00151095bbcc28e5eb87b3b5bdb8ac13f089f791300bfd499d72a1f0"
        ),
        "schema_version": "us_fddk.short_term_form4_collection_stop.v1",
        "stop_reason": "form4_feasibility_daily_index_missing_or_ambiguous",
    }
    state = payload["state_boundary"]
    assert state["candidate_selection_count"] == 0
    assert state["strategy_run_count"] == 0
    assert state["performance_present"] is False
    assert state["paper"] == {
        "authorized": False,
        "state": "all_cash",
        "backfilled_trades": 0,
        "positions": [],
    }
    assert state["real_money_action_usd"] == 0
    assert state["today_action"] == "今天不下單"


def test_round42_artifact_site_data_and_report_are_deterministic() -> None:
    payload = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    assert SITE_DATA.read_bytes() == ARTIFACT.read_bytes()
    assert REPORT.read_text(encoding="utf-8") == render_report(payload)


def test_round42_public_outputs_contain_no_identifiers_urls_or_performance() -> None:
    artifact = ARTIFACT.read_text(encoding="utf-8")
    report = REPORT.read_text(encoding="utf-8")
    assert re.search(r"(?<!\d)\d{10}-\d{2}-\d{6}(?!\d)", artifact + report) is None
    assert re.search(r"[\w.+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", artifact + report) is None
    assert "http://" not in report and "https://" not in report
    for token in ("AAPL", "MSFT", "NVDA", "AMD", "META", "CAGR", "Sharpe", "最大跌幅", "期末值"):
        assert token not in report
    assert "公開市場或私人購買" in report
    assert "「企業家」" in report and "不是 SEC 法定申報身份" in report
    assert "Paper Trading（模擬交易）未授權" in report
    assert "5 個已完成 HTTP request" in report
    assert "1 次 post-fetch 本地驗證失敗" in report
    assert "complete-submission\nrequest 為 **0**" in report
    assert "cold replay **未完成**" in report
    assert "不能寫成\n真實細樣本已成功重播" in report
    assert "實金動作 **US$0**" in report
    assert "**今天不下單。**" in report


def _load_mutable_payload() -> dict[str, object]:
    return json.loads(ARTIFACT.read_text(encoding="utf-8"))


def _rehash_collection_stop_receipt(payload: dict[str, object]) -> None:
    attacks = payload["attack_results"]
    assert isinstance(attacks, dict)
    receipt = attacks["collection_stop_receipt"]
    assert isinstance(receipt, dict)
    body = dict(receipt)
    body.pop("receipt_sha256")
    receipt["receipt_sha256"] = canonical_sha256(body)


@pytest.mark.parametrize(
    "mutator",
    [
        lambda payload: payload["attack_results"].__setitem__(
            "detail", "1234567890 Example Person Example Corp"
        ),
        lambda payload: payload["state_boundary"].__setitem__("detail", "unexpected"),
        lambda payload: payload.__setitem__(
            "status", "authorized_real_sample_replayed_form4_admission_3_of_16"
        ),
        lambda payload: payload.__setitem__("frozen_at", "2026-08-09 23:39:35"),
    ],
    ids=["extra-detail-with-cik", "state-extra-key", "status-mismatch", "bad-timestamp"],
)
def test_round42_public_schema_rejects_identity_and_nested_drift(mutator) -> None:
    payload = _load_mutable_payload()
    mutator(payload)
    with pytest.raises((TypeError, ValueError)):
        validate_public_payload(payload)


def test_round42_public_schema_rejects_true_gate_identity_drift() -> None:
    payload = _load_mutable_payload()
    gates = payload["admission_controls"]["gates"]
    gates[0]["passed"] = False
    gates[1]["passed"] = True
    with pytest.raises(ValueError, match="gate identity or state drifted"):
        validate_public_payload(payload)


def test_round42_collection_stop_receipt_rejects_hash_and_count_drift() -> None:
    payload = _load_mutable_payload()
    receipt = payload["attack_results"]["collection_stop_receipt"]
    receipt["receipt_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="self-hash drifted"):
        validate_public_payload(payload)

    payload = _load_mutable_payload()
    receipt = payload["attack_results"]["collection_stop_receipt"]
    receipt["completed_http_requests"] = 6
    _rehash_collection_stop_receipt(payload)
    with pytest.raises(ValueError, match="facts drifted"):
        validate_public_payload(payload)


def test_round42_collection_stop_receipt_rejects_binding_drift() -> None:
    payload = _load_mutable_payload()
    receipt = payload["attack_results"]["collection_stop_receipt"]
    receipt["admission_core_sha256"] = "0" * 64
    _rehash_collection_stop_receipt(payload)
    with pytest.raises(ValueError, match="admission core binding drifted"):
        validate_public_payload(payload)

    payload = _load_mutable_payload()
    receipt = payload["attack_results"]["collection_stop_receipt"]
    receipt["private_manifest_sha256"] = "a" * 64
    _rehash_collection_stop_receipt(payload)
    with pytest.raises(ValueError, match="facts drifted"):
        validate_public_payload(payload)
