from __future__ import annotations

import json
import stat
import tempfile
from pathlib import Path
from unittest.mock import patch

import pandas as pd
import pytest

import usfddk.risk_free_staging as risk_free_staging
from scripts.build_short_term_risk_free_staging_report import _site_summary
from usfddk.risk_free_staging import (
    EXPECTED_MISSING_SESSION_COUNT,
    EXPECTED_SOURCE_SHA256,
    EXPECTED_STUDY_SESSION_COUNT,
    PROTOCOL_SHA256,
    inspect_official_rf_zip,
    probe_official_rf_zip,
    stage_official_rf_snapshot,
)
from usfddk.risk_free_staging_validation import (
    run_risk_free_staging_validation,
)

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "artifacts/french_ff_factors_daily_39f9ae1d.zip"


def test_official_202606_snapshot_has_exact_frozen_tail_gap() -> None:
    audit = inspect_official_rf_zip(SOURCE, root=ROOT)

    assert audit["protocol"]["passed"] is True
    assert audit["source"]["sha256"] == EXPECTED_SOURCE_SHA256
    assert audit["source"]["data_cut"] == "202606"
    assert audit["source"]["full_last_session"] == "2026-06-30"
    assert audit["study"]["required_sessions"] == EXPECTED_STUDY_SESSION_COUNT
    assert audit["study"]["available_sessions"] == 5_009
    assert audit["study"]["missing_session_count"] == EXPECTED_MISSING_SESSION_COUNT
    assert audit["study"]["missing_sessions"][0] == "2026-07-01"
    assert audit["study"]["missing_sessions"][-1] == "2026-07-31"
    assert audit["study"]["extra_session_count"] == 0


def test_owner_only_staging_is_partial_and_cannot_look_formal() -> None:
    with tempfile.TemporaryDirectory(prefix="usfddk-rf-test-") as temporary:
        output = Path(temporary) / "staging"
        result = stage_official_rf_snapshot(SOURCE, output, root=ROOT)

        assert result["owner_only"] is True
        assert result["formal_manifest_generated"] is False
        assert result["formal_rf_input_ready"] is False
        assert result["formal_backtest_authorized"] is False
        assert result["strategy_run_count"] == 0
        assert result["paper"]["state"] == "all_cash"
        assert result["real_money_action_usd"] == 0
        assert stat.S_IMODE(output.stat().st_mode) == 0o700
        assert all(stat.S_IMODE(path.stat().st_mode) == 0o600 for path in output.iterdir())
        assert not (output / "risk_free_manifest.json").exists()
        assert not (output / "risk_free_daily.csv").exists()

        partial = pd.read_csv(output / "risk_free_daily_partial.csv")
        missing = pd.read_csv(output / "missing_sessions.csv")
        assert len(partial) == 5_009
        assert len(missing) == 22
        assert partial["source_record_id"].is_unique
        assert set(partial["unit"]) == {"decimal_simple_daily_return"}
        assert partial["risk_free_return"].abs().max() <= 0.01


def test_all_eight_controls_pass_and_all_attacks_hit_exact_codes() -> None:
    result = run_risk_free_staging_validation(ROOT, SOURCE)

    assert result["protocol_integrity"]["passed"] is True
    assert result["protocol_integrity"]["independent_first_seen_evidence"] is False
    assert result["control_summary"] == {
        "passed": 8,
        "total": 8,
        "all_passed": True,
    }
    assert result["attack_summary"] == {
        "rejected": 8,
        "total": 8,
        "all_rejected": True,
    }
    assert all(
        row["observed_error_code"] == row["expected_error_code"]
        for row in result["attacks"]
    )
    assert result["protocol_integrity"]["rebind"]["passed"] is True
    assert result["protocol_integrity"]["rebind"]["hash_checks"][
        "usfddk/formal_backtest_readiness.py"
    ] is True


def test_round41_rebind_preserves_round36_bytes_and_binds_effective_entry() -> None:
    result = run_risk_free_staging_validation(ROOT, SOURCE)
    rebind = result["protocol_integrity"]["rebind"]
    amendment = json.loads(
        (ROOT / risk_free_staging.REBIND_AMENDMENT_RECEIPT_PATH).read_text(
            encoding="utf-8"
        )
    )

    assert rebind["effective_version"] == "round41-v1.1"
    assert rebind["historical_round36"]["passed"] is True
    assert rebind["historical_round36"]["frozen_formal_validator_sha256"] == (
        risk_free_staging.HISTORICAL_FORMAL_VALIDATOR_SHA256
    )
    assert risk_free_staging._sha256_file(
        ROOT / risk_free_staging.REBIND_PROTOCOL_RECEIPT_PATH
    ) == risk_free_staging.REBIND_PROTOCOL_RECEIPT_SHA256
    assert risk_free_staging._sha256_file(
        ROOT / risk_free_staging.REBIND_AMENDMENT_RECEIPT_PATH
    ) == risk_free_staging.REBIND_AMENDMENT_RECEIPT_SHA256
    assert amendment["historical_formal_validator"]["sha256"] == (
        risk_free_staging.HISTORICAL_FORMAL_VALIDATOR_SHA256
    )
    assert amendment["current_formal_validator"]["sha256"] == (
        risk_free_staging.CURRENT_FORMAL_VALIDATOR_SHA256
    )
    assert rebind["hash_checks"][risk_free_staging.GLOBAL_TRIAL_LEDGER_PATH] is True


def test_round41_rebind_rejects_current_formal_entry_drift() -> None:
    original = risk_free_staging._sha256_file

    def drifted_hash(path: Path) -> str:
        if path.resolve() == (ROOT / "usfddk/formal_backtest_readiness.py").resolve():
            return "0" * 64
        return original(path)

    with patch.object(risk_free_staging, "_sha256_file", drifted_hash):
        with pytest.raises(risk_free_staging.RiskFreeStagingError) as error:
            risk_free_staging._protocol_integrity(ROOT)
    assert error.value.code == "rf_staging_rebind_integrity_failed"


def test_round41_rebind_rejects_rollback_to_round19_formal_entry() -> None:
    original = risk_free_staging._sha256_file
    round19_validator_sha256 = json.loads(
        (ROOT / risk_free_staging.PROTOCOL_RECEIPT_PATH).read_text(encoding="utf-8")
    )["parent_formal_validator"]["sha256"]

    def rolled_back_hash(path: Path) -> str:
        if path.resolve() == (ROOT / "usfddk/formal_backtest_readiness.py").resolve():
            return round19_validator_sha256
        return original(path)

    with patch.object(risk_free_staging, "_sha256_file", rolled_back_hash):
        with pytest.raises(risk_free_staging.RiskFreeStagingError) as error:
            risk_free_staging._protocol_integrity(ROOT)
    assert error.value.code == "rf_staging_rebind_integrity_failed"


def test_round41_rebind_rejects_historical_round36_receipt_drift() -> None:
    original = risk_free_staging._sha256_file

    def drifted_hash(path: Path) -> str:
        if path.resolve() == (
            ROOT / risk_free_staging.REBIND_PROTOCOL_RECEIPT_PATH
        ).resolve():
            return "0" * 64
        return original(path)

    with patch.object(risk_free_staging, "_sha256_file", drifted_hash):
        with pytest.raises(risk_free_staging.RiskFreeStagingError) as error:
            risk_free_staging._protocol_integrity(ROOT)
    assert error.value.code == "rf_staging_rebind_integrity_failed"


def test_formal_paper_and_real_money_boundaries_remain_closed() -> None:
    result = run_risk_free_staging_validation(ROOT, SOURCE)

    assert result["status"] == "official_rf_staged_incomplete_22_sessions_missing"
    assert result["actual_formal_readiness"] == {
        "passed": 1,
        "total": 18,
        "all_passed": False,
        "only_passed_gate": "01_preregistration_integrity",
    }
    assert result["complete_risk_free_package_received"] is False
    assert result["authorized_provider_package_received"] is False
    assert result["formal_stock_backtest_input_ready"] is False
    assert result["formal_stock_backtest_completed"] is False
    assert result["strategy_run_count"] == 0
    assert result["paper"] == {
        "authorized": False,
        "state": "all_cash",
        "backfilled_trades": 0,
        "positions": [],
    }
    assert result["real_money_action_usd"] == 0


def test_daily_source_probe_is_deterministic_and_never_self_qualifies() -> None:
    expected = probe_official_rf_zip(SOURCE, root=ROOT)
    artifact = json.loads(
        (ROOT / "artifacts/short_term_risk_free_source_probe.json").read_text(
            encoding="utf-8"
        )
    )
    site_data = json.loads(
        (ROOT / "site/data/short-term-risk-free-source-probe.json").read_text(
            encoding="utf-8"
        )
    )

    assert artifact == expected
    assert site_data == expected
    assert expected["status"] == "matches_frozen_source"
    assert expected["matches_frozen_source"] is True
    assert expected["new_source_qualified"] is False
    assert expected["formal_rf_input_ready"] is False
    assert expected["formal_backtest_authorized"] is False
    assert expected["strategy_run_count"] == 0
    assert expected["paper_authorized"] is False
    assert expected["paper_state"] == "all_cash"
    assert expected["real_money_action_usd"] == 0


def test_published_outputs_match_reproducible_builder() -> None:
    result = run_risk_free_staging_validation(ROOT, SOURCE)
    artifact = json.loads(
        (ROOT / "artifacts/short_term_risk_free_staging_validation.json").read_text(
            encoding="utf-8"
        )
    )
    site_data = json.loads(
        (ROOT / "site/data/short-term-risk-free-staging.json").read_text(
            encoding="utf-8"
        )
    )

    assert artifact == result
    assert site_data == _site_summary(result)


def test_report_discloses_partial_coverage_without_promotion() -> None:
    report = (ROOT / "docs/SHORT_TERM_RISK_FREE_STAGING_REPORT.md").read_text(
        encoding="utf-8"
    )

    assert "5,009/5,031 個 XNYS session" in report
    assert "精確欠最後 **22 日**" in report
    assert "正式就緒仍為 **1/18**" in report
    assert "正式策略運行 **0 次**" in report
    assert "短線 Paper 全現金" in report
    assert "實金動作\n**US$0**" in report
    assert "不會生成" in report
    assert PROTOCOL_SHA256 == json.loads(
        (
            ROOT / "artifacts/short_term_risk_free_staging_protocol_receipt.json"
        ).read_text(encoding="utf-8")
    )["protocol"]["sha256"]
