from __future__ import annotations

import hashlib
import json
from pathlib import Path

from usfddk.short_term_current_cohort_breakout import (
    BOOTSTRAP_SEED,
    EXPECTED_PROTOCOL_RECEIPT_SHA256,
    EXPECTED_PROTOCOL_SHA256,
    GLOBAL_TRIAL_INCREMENT,
    GLOBAL_TRIAL_PRIOR_LOWER_BOUND,
    PROTOCOL_PATH,
    PROTOCOL_RECEIPT_PATH,
    _load_protocol,
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
