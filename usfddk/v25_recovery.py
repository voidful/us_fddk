from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

import pandas as pd

from usfddk.data import most_recent_us_session
from usfddk.growth_gold_diversification import (
    V25_FORWARD_PROMOTION_PROTOCOL_SHA256,
    v25_forward_paper_evidence,
)
from usfddk.paper import load_paper_state
from usfddk.v25_live import (
    V25LiveContinuityGapError,
    _require_contiguous_v25_session,
    _sha256_file,
    run_v25_live_update,
    verify_v25_reference_ledger,
    write_json_atomic,
)


def prepare_v25_live_segment(
    directory: str | Path,
    *,
    candidate_state_path: str | Path = "artifacts/paper_v25_state.json",
    spy_state_path: str | Path = "artifacts/paper_v25_spy_state.json",
    matched_state_path: str | Path = "artifacts/paper_v25_matched_state.json",
    ledger_path: str | Path = "artifacts/v25_live_evidence_ledger.jsonl",
    eligibility_receipt: str | Path = "artifacts/v25_growth_gold_diversification_validation.json",
    snapshot: str | Path | None = None,
    observed_at: datetime | None = None,
) -> dict[str, Any]:
    """Prepare a separate zero-count segment, without activating or publishing it.

    A continuity failure is the only permitted restart reason. Old bytes and their
    receipt-chain head are preserved. Missed sessions and old performance never
    enter the new segment's forward gates. The production CLI uses the real clock;
    ``observed_at`` exists solely for deterministic offline tests.
    """
    destination = Path(directory).resolve()
    if destination.exists():
        raise ValueError("新 v25 觀察段目錄已存在，拒絕覆寫")
    paths = {
        "candidate": Path(candidate_state_path).resolve(),
        "SPY": Path(spy_state_path).resolve(),
        "matched": Path(matched_state_path).resolve(),
    }
    source_ledger = Path(ledger_path).resolve()
    sources = {**paths, "ledger": source_ledger}
    if any(destination in path.parents or path in destination.parents for path in sources.values()):
        raise ValueError("新觀察段不可與既有權威檔案路徑重疊")
    original_bytes = {label: path.read_bytes() for label, path in sources.items()}
    states = {label: load_paper_state(path) for label, path in paths.items()}
    evidence = v25_forward_paper_evidence(states["candidate"], states["SPY"], states["matched"])
    identity_gates = [
        key for key in evidence["gates"]
        if key.startswith("all_accounts_") and key != "all_accounts_exactly_one_initial_allocation"
    ]
    if not evidence["gates"]["zero_integrity_violations"] or not all(
        evidence["gates"][key] for key in identity_gates
    ):
        raise ValueError("既有 v25 三帳戶完整性不符，必須先覆核，不能以重開掩蓋")
    verified_ledger = verify_v25_reference_ledger(source_ledger)
    if not verified_ledger["receipts"]:
        raise ValueError("既有 v25 觀察段缺少前瞻收據鏈")
    last_receipt = json.loads(source_ledger.read_text(encoding="utf-8").splitlines()[-1])
    previous_date = str(states["candidate"]["as_of"])
    if last_receipt["data_through"] != previous_date or last_receipt["snapshot_sha256"] != states[
        "candidate"
    ]["snapshot_sha256"]:
        raise ValueError("既有 v25 收據鏈尾端與三帳戶日期／快照不符")
    now = observed_at or datetime.now(UTC)
    if now.tzinfo is None:
        raise ValueError("新 v25 觀察段必須使用有時區的真實觀察時間")
    expected = most_recent_us_session(pd.Timestamp(now))
    try:
        _require_contiguous_v25_session(previous_date, expected)
    except V25LiveContinuityGapError as exc:
        continuity_failure = str(exc)
    else:
        raise ValueError("既有 v25 觀察段沒有跨交易日缺口，不得任意重置前瞻績效")

    destination.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix=".v25-segment-", dir=destination.parent) as temporary:
        staging = Path(temporary) / "segment"
        prior = staging / "prior"
        prior.mkdir(parents=True)
        for label, content in original_bytes.items():
            (prior / sources[label].name).write_bytes(content)
        new_paths = {label: staging / path.name for label, path in paths.items()}
        status = run_v25_live_update(
            snapshot=snapshot,
            as_of=now,
            output_dir=staging,
            eligibility_receipt=eligibility_receipt,
            candidate_state_path=new_paths["candidate"],
            spy_state_path=new_paths["SPY"],
            matched_state_path=new_paths["matched"],
            evidence_path=staging / "v25_forward_paper_evidence.json",
            status_path=staging / "v25_live_update_status.json",
            initial_cash=float(states["candidate"]["initial_cash"]),
            cost_bps=float(states["candidate"]["cost_bps"]),
        )
        forward = status["forward_evidence"]
        if forward["forward_sessions"] != 0 or forward["filled_rebalances"] != 0 or forward[
            "live_confirmed"
        ]:
            raise RuntimeError("新 v25 觀察段不可以繼承或回填前瞻績效")
        (staging / source_ledger.name).write_bytes(b"")
        snapshot_path = Path(status["snapshot"]["path"])
        if snapshot_path.parent == staging:
            status["snapshot"]["path"] = str(destination / snapshot_path.name)
        status.update(
            manual_review_required=True,
            private_deploy_candidate=False,
            site_rebuild_required=False,
            decision="new_segment_prepared_requires_activation_review",
        )
        write_json_atomic(staging / "v25_live_update_status.json", status)
        manifest = {
            "schema_version": 1,
            "reason": "missed_live_sessions",
            "continuity_failure": continuity_failure,
            "observed_at_utc": now.astimezone(UTC).isoformat().replace("+00:00", "Z"),
            "prior_started_at": states["candidate"]["started_at"],
            "prior_data_through": previous_date,
            "prior_forward_sessions": evidence["forward_sessions"],
            "prior_ledger": verified_ledger,
            "prior_files": {
                label: {
                    "original_path": str(path),
                    "preserved_path": f"prior/{path.name}",
                    "sha256": _sha256_file(prior / path.name),
                } for label, path in sources.items()
            },
            "new_started_at": forward["started_at"],
            "new_forward_sessions": 0,
            "new_filled_rebalances": 0,
            "inherited_forward_sessions": 0,
            "backfilled_forward_sessions": 0,
            "promotion_protocol_sha256": V25_FORWARD_PROMOTION_PROTOCOL_SHA256,
            "minimum_new_sessions": forward["minimum_sessions"],
            "minimum_completed_rebalances": forward["minimum_filled_rebalances"],
            "live_confirmed": False,
            "activation_applied": False,
            "deployment_applied": False,
        }
        write_json_atomic(staging / "v25_segment_manifest.json", manifest)
        if any(path.read_bytes() != original_bytes[label] for label, path in sources.items()):
            raise RuntimeError("準備新 v25 觀察段期間，既有權威檔案發生變更")
        staging.rename(destination)
    return manifest
