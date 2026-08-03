import json
import subprocess
import tempfile
from pathlib import Path

import pytest

from scripts.build_short_term_local_quarantine_intake_report import _site_summary
from usfddk.local_quarantine_intake import (
    INTAKE_PROTOCOL_SHA256,
    INTAKE_VERSION,
    LocalQuarantineIntakeError,
    audit_local_quarantine_package,
    run_local_quarantine_intake,
)
from usfddk.local_quarantine_intake_validation import (
    CONTROL_REQUIREMENTS,
    _write_control_set,
    run_local_quarantine_intake_validation,
)

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def result() -> dict:
    return run_local_quarantine_intake_validation(ROOT)


def test_round17_synthetic_intake_and_all_attacks_are_exact(result: dict) -> None:
    assert result["status"] == (
        "synthetic_local_intake_passed_provider_inputs_still_missing"
    )
    assert result["intake_version"] == INTAKE_VERSION
    assert result["synthetic_control"]["gate_summary"] == {
        "passed": 16,
        "total": 16,
        "all_passed": True,
    }
    assert result["attack_summary"] == {
        "rejected": 16,
        "total": 16,
        "all_rejected": True,
    }
    assert [row["id"] for row in result["synthetic_control"]["gates"]] == [
        f"{index:02d}" for index in range(1, 17)
    ]
    assert all(
        row["rejected"]
        and row["observed_error_code"] == row["expected_error_code"]
        for row in result["attacks"]
    )


def test_round17_preserves_round15_and_adds_explicit_source_modes(result: dict) -> None:
    gap = result["gap_closed"]
    assert gap == {
        "finding": "Round 15 manifest status 只接受 synthetic，不能標示真實 provider mode。",
        "old_status": "synthetic_execution_extension_built",
        "new_synthetic_status": "synthetic_local_quarantine_extension_built",
        "new_provider_status": "authorized_provider_local_quarantine_extension_built",
        "round15_files_modified": False,
    }
    assert "synthetic_execution_extension_built" in (
        ROOT / "usfddk/ciz_execution_extension.py"
    ).read_text(encoding="utf-8")
    assert result["protocol_integrity"]["passed"] is True
    assert len(result["protocol_integrity"]["hash_checks"]) == 17
    assert all(result["protocol_integrity"]["hash_checks"].values())
    assert (
        INTAKE_PROTOCOL_SHA256
        == "1167310d566c0208befc09f24d6391fe4dc3efd606a09f8b16e983c2abdf79a8"
    )


def test_synthetic_receipt_never_promotes_formal_backtest(result: dict) -> None:
    control = result["synthetic_control"]
    assert control["point_in_time_gate_summary"] == {
        "passed": 20,
        "total": 20,
        "all_passed": True,
    }
    assert control["extension_gate_summary"] == {
        "passed": 16,
        "total": 16,
        "all_passed": True,
    }
    assert control["private_permissions"] is True
    assert control["formal_stock_backtest_input_ready"] is False
    assert control["contains_provider_rows"] is False


def test_production_entrypoint_rejects_relative_paths_before_reading() -> None:
    with pytest.raises(LocalQuarantineIntakeError) as error:
        run_local_quarantine_intake(
            "response.json",
            "/private/does-not-matter-ciz",
            "/private/does-not-matter-overlay",
            "/private/does-not-matter-output",
            root=ROOT,
            source_mode="provider",
        )
    assert error.value.code == "intake_path_not_absolute"


def test_derived_intake_receipt_tampering_is_rejected() -> None:
    with tempfile.TemporaryDirectory(prefix="usfddk-round17-receipt-") as temporary:
        paths = _write_control_set(Path(temporary))
        run_local_quarantine_intake(
            paths["response"],
            paths["ciz"],
            paths["overlay"],
            paths["output"],
            root=ROOT,
            source_mode="synthetic_control",
            requirements=CONTROL_REQUIREMENTS,
        )
        receipt_path = paths["output"] / "intake_receipt.json"
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        receipt["strategy_run_count"] = 1
        receipt_path.write_text(
            json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

        with pytest.raises(LocalQuarantineIntakeError) as error:
            audit_local_quarantine_package(
                paths["output"],
                root=ROOT,
                source_mode="synthetic_control",
                requirements=CONTROL_REQUIREMENTS,
            )

    assert error.value.code == "intake_receipt_invalid"


def test_cli_exposes_only_provider_mode_and_requires_all_four_paths() -> None:
    completed = subprocess.run(
        [
            str(ROOT / ".venv/bin/python"),
            str(ROOT / "scripts/validate_short_term_local_quarantine_intake.py"),
            "--help",
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    assert "--response" in completed.stdout
    assert "--ciz-bundle" in completed.stdout
    assert "--execution-overlay" in completed.stdout
    assert "--output" in completed.stdout
    assert "--mode" not in completed.stdout


def test_actual_provider_state_remains_unpromoted(result: dict) -> None:
    assert result["actual_local_intake"] == {
        "passed": 1,
        "total": 16,
        "all_passed": False,
        "only_passed_gate": "01_preregistration_integrity",
    }
    assert result["actual_document_handoff"]["passed"] == 1
    assert result["actual_point_in_time_readiness"] == {
        "passed": 1,
        "total": 20,
        "all_passed": False,
    }
    assert result["explicit_external_paths_provided"] is False
    assert result["provider_mode_run_count"] == 0
    assert result["authorized_provider_response_received"] is False
    assert result["authorized_provider_sample_received"] is False
    assert result["formal_stock_backtest_input_ready"] is False
    assert result["formal_stock_backtest_completed"] is False
    assert result["strategy_rule_changed"] is False
    assert result["paper"] == {
        "authorized": False,
        "state": "all_cash",
        "backfilled_trades": 0,
        "positions": [],
    }
    assert result["real_money_action_usd"] == 0


def test_committed_machine_and_site_receipts_match_round17(result: dict) -> None:
    machine = json.loads(
        (
            ROOT / "artifacts/short_term_local_quarantine_intake_validation.json"
        ).read_text(encoding="utf-8")
    )
    site = json.loads(
        (ROOT / "site/data/short-term-local-quarantine-intake.json").read_text(
            encoding="utf-8"
        )
    )
    assert machine == result
    assert site == _site_summary(result)
