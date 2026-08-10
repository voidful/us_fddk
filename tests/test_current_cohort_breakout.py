from __future__ import annotations

import hashlib
import json
from pathlib import Path

from usfddk.global_trial_ledger_round51_extension import audit_round51_extension
from usfddk.short_term_current_cohort_breakout import (
    BOOTSTRAP_SEED,
    EXPECTED_PROTOCOL_RECEIPT_SHA256,
    EXPECTED_PROTOCOL_SHA256,
    GLOBAL_TRIAL_INCREMENT,
    GLOBAL_TRIAL_PRIOR_LOWER_BOUND,
    PROTOCOL_PATH,
    PROTOCOL_RECEIPT_PATH,
    VALIDATION_PATH,
    _load_protocol,
    audit_current_cohort_breakout,
)

ROOT = Path(__file__).resolve().parents[1]


def _canonical_sha256(value: object) -> str:
    rendered = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(rendered).hexdigest()


def test_protocol_is_frozen_and_self_bound() -> None:
    protocol = ROOT / PROTOCOL_PATH
    receipt_path = ROOT / PROTOCOL_RECEIPT_PATH
    assert hashlib.sha256(protocol.read_bytes()).hexdigest() == EXPECTED_PROTOCOL_SHA256
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    claimed = receipt["receipt_sha256"]
    unsigned = dict(receipt)
    unsigned.pop("receipt_sha256")
    assert claimed == EXPECTED_PROTOCOL_RECEIPT_SHA256
    assert _canonical_sha256(unsigned) == claimed
    assert _load_protocol(ROOT)["status"] == (
        "preregistered_unrun_current_cohort_breakout_diagnostic"
    )


def test_protocol_reserves_multiplicity_without_authorizing_trading() -> None:
    receipt = _load_protocol(ROOT)
    ledger = receipt["global_trial_ledger"]
    assert ledger["current_lower_bound"] == GLOBAL_TRIAL_PRIOR_LOWER_BOUND
    assert ledger["minimum_increment"] == GLOBAL_TRIAL_INCREMENT
    assert receipt["formal_backtest_authorized"] is False
    assert receipt["paper_authorized"] is False
    assert receipt["real_money_authorized"] is False
    assert receipt["today_action"] == "今天不下單"
    assert receipt["bootstrap"]["seed"] == BOOTSTRAP_SEED


def test_breakout_result_is_reproducible_and_stays_out_of_trading() -> None:
    snapshot = ROOT / "artifacts/snapshot_20260731_6a7ca6b8.zip"
    generated = audit_current_cohort_breakout(
        repository_root=ROOT,
        snapshot_path=snapshot,
    )
    saved = json.loads((ROOT / VALIDATION_PATH).read_text(encoding="utf-8"))
    assert generated == saved
    assert generated["status"] == (
        "current_cohort_breakout_diagnostic_negative_survivorship_biased"
    )
    assert generated["passed_primary_gate_count"] == 4
    assert generated["required_primary_gate_count"] == 5
    assert generated["valid_for_investment_decision"] is False
    assert generated["data_boundary"]["paper_authorized"] is False
    assert generated["data_boundary"]["formal_backtest_authorized"] is False
    assert generated["real_money_action_usd"] == 0
    assert generated["today_action"] == "今天不下單"
    rendered = json.dumps(generated, ensure_ascii=False)
    assert "ticker" not in rendered
    assert "symbol" not in rendered
    assert "accession" not in rendered


def test_round51_global_trial_extension_is_append_only_and_closed() -> None:
    result = audit_round51_extension(root=ROOT)
    assert result["passed"] is True
    assert result["base_lower_bound"] == 6287
    assert result["increment"] == 3
    assert result["current_lower_bound"] == 6290
    assert result["source_binding_count"] == 4
    assert result["paper"]["authorized"] is False
    assert result["real_money_action_usd"] == 0
