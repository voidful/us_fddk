from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd
import pytest

from usfddk.formal_benchmark_actions import (
    ACTION_COLUMNS,
    BENCHMARK_ACTION_MANIFEST,
    ENTITLEMENT_COLUMNS,
    OUTCOME_COLUMNS,
    BenchmarkActionBridgeError,
    load_benchmark_action_bridge,
)

ROOT = Path(__file__).resolve().parents[1]
SESSIONS = pd.DatetimeIndex(["2026-01-02", "2026-01-05"])
RUN_ID = "a" * 64


def _write_private(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")
    path.chmod(0o600)


def _write_bridge(tmp_path: Path) -> tuple[Path, Path]:
    bundle = tmp_path / "benchmark-actions"
    bundle.mkdir(mode=0o700)
    execution_manifest = tmp_path / "execution_manifest.json"
    _write_private(execution_manifest, '{"study_start":"2026-01-01","study_end":"2026-01-05"}\n')

    actions = pd.DataFrame(
        [
            {
                "event_id": "BRIDGE-QQQ-DIV-1",
                "security_id": "QQQ",
                "event_type": "dividend",
                "announced_at": "2025-12-01T00:00:00Z",
                "ex_date": "2026-01-02",
                "effective_date": "2026-01-02",
                "cash_amount": "1.0",
                "share_ratio": "0",
                "successor_security_id": "",
                "source_record_id": "PROVIDER-QQQ-DIV-1",
            },
            {
                "event_id": "BRIDGE-SPY-DIV-1",
                "security_id": "SPY",
                "event_type": "dividend",
                "announced_at": "2025-12-01T00:00:00Z",
                "ex_date": "2026-01-05",
                "effective_date": "2026-01-05",
                "cash_amount": "1.0",
                "share_ratio": "0",
                "successor_security_id": "",
                "source_record_id": "PROVIDER-SPY-DIV-1",
            },
        ],
        columns=ACTION_COLUMNS,
    )
    entitlements = pd.DataFrame(
        [
            {
                "event_id": "BRIDGE-QQQ-DIV-1",
                "security_id": "QQQ",
                "announced_at": "2025-12-01T00:00:00Z",
                "ex_date": "2026-01-02",
                "pay_date": "2026-01-05",
                "cash_available_date": "2026-01-05",
                "cash_per_share": "1.0",
                "source_record_id": "PROVIDER-QQQ-DIV-1",
            },
            {
                "event_id": "BRIDGE-SPY-DIV-1",
                "security_id": "SPY",
                "announced_at": "2025-12-01T00:00:00Z",
                "ex_date": "2026-01-05",
                "pay_date": "2026-01-05",
                "cash_available_date": "2026-01-05",
                "cash_per_share": "1.0",
                "source_record_id": "PROVIDER-SPY-DIV-1",
            },
        ],
        columns=ENTITLEMENT_COLUMNS,
    )
    outcomes = pd.DataFrame(columns=OUTCOME_COLUMNS)
    for name, frame in (
        ("benchmark_actions.csv", actions),
        ("benchmark_entitlements.csv", entitlements),
        ("benchmark_outcomes.csv", outcomes),
    ):
        frame.to_csv(bundle / name, index=False, lineterminator="\n")
        (bundle / name).chmod(0o600)
    files = {
        name: {
            "sha256": hashlib.sha256((bundle / name).read_bytes()).hexdigest(),
            "rows": len(frame),
        }
        for name, frame in (
            ("benchmark_actions.csv", actions),
            ("benchmark_entitlements.csv", entitlements),
            ("benchmark_outcomes.csv", outcomes),
        )
    }
    manifest = {
        "schema_version": 1,
        "status": "provider_benchmark_action_bridge",
        "bridge_version": "round23-formal-benchmark-action-bridge-v1",
        "provider": "controlled-provider",
        "provider_product": "benchmark-actions",
        "license_attestation": {
            "authorized_for_local_research": True,
            "raw_redistribution_allowed": False,
            "attested_at": "2025-12-01T00:00:00Z",
            "reference": "provider-attestation-1",
        },
        "exported_at": "2026-01-01T00:00:00Z",
        "first_imported_at": "2026-01-01T01:00:00Z",
        "study_start": "2026-01-01",
        "study_end": "2026-01-05",
        "formal_run_id": RUN_ID,
        "execution_manifest_sha256": hashlib.sha256(execution_manifest.read_bytes()).hexdigest(),
        "benchmark_assets": ["QQQ", "SPY"],
        "files": files,
    }
    _write_private(
        bundle / BENCHMARK_ACTION_MANIFEST,
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
    )
    return bundle, execution_manifest


def _load(bundle: Path, execution_manifest: Path):
    return load_benchmark_action_bridge(
        bundle,
        root=ROOT,
        execution_manifest_path=execution_manifest,
        formal_run_id=RUN_ID,
        study_start="2026-01-01",
        study_end="2026-01-05",
        sessions=SESSIONS,
    )


def test_provider_benchmark_action_bridge_accepts_bound_owner_only_bundle(tmp_path: Path) -> None:
    bundle, execution_manifest = _write_bridge(tmp_path)
    bridge = _load(bundle, execution_manifest)
    assert set(bridge.actions["security_id"]) == {"QQQ", "SPY"}
    assert len(bridge.actions) == len(bridge.entitlements) == 2
    assert bridge.outcomes.empty


def test_bridge_rejects_relative_path(tmp_path: Path) -> None:
    bundle, execution_manifest = _write_bridge(tmp_path)
    with pytest.raises(BenchmarkActionBridgeError) as error:
        _load(Path(bundle.name), execution_manifest)
    assert error.value.code == "benchmark_action_path_boundary_invalid"


def test_bridge_rejects_manifest_hash_or_run_binding_drift(tmp_path: Path) -> None:
    bundle, execution_manifest = _write_bridge(tmp_path)
    manifest_path = bundle / BENCHMARK_ACTION_MANIFEST
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["formal_run_id"] = "b" * 64
    _write_private(manifest_path, json.dumps(manifest, sort_keys=True) + "\n")
    with pytest.raises(BenchmarkActionBridgeError) as error:
        _load(bundle, execution_manifest)
    assert error.value.code == "benchmark_action_binding_mismatch"


def test_bridge_rejects_missing_dividend_entitlement(tmp_path: Path) -> None:
    bundle, execution_manifest = _write_bridge(tmp_path)
    entitlement_path = bundle / "benchmark_entitlements.csv"
    frame = pd.read_csv(entitlement_path, dtype=str, keep_default_na=False)
    frame = frame.iloc[:1]
    frame.to_csv(entitlement_path, index=False, lineterminator="\n")
    entitlement_path.chmod(0o600)
    manifest_path = bundle / BENCHMARK_ACTION_MANIFEST
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["files"]["benchmark_entitlements.csv"] = {
        "sha256": hashlib.sha256(entitlement_path.read_bytes()).hexdigest(),
        "rows": len(frame),
    }
    _write_private(manifest_path, json.dumps(manifest, sort_keys=True) + "\n")
    with pytest.raises(BenchmarkActionBridgeError) as error:
        _load(bundle, execution_manifest)
    assert error.value.code == "benchmark_action_entitlement_mismatch"
