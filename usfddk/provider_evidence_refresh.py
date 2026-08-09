from __future__ import annotations

import copy
import hashlib
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

RESEARCH_ROUND = 33
PROTOCOL_PATH = "docs/SHORT_TERM_PROVIDER_EVIDENCE_REFRESH_PROTOCOL.md"
PROTOCOL_RECEIPT_PATH = (
    "artifacts/short_term_provider_evidence_refresh_protocol_receipt.json"
)
PROTOCOL_SHA256 = (
    "42c55adf76bba072b50618800890e5e34f07aae3d0b68be7ec1b46f5dcdaea9d"
)
PROTOCOL_RECEIPT_SHA256 = (
    "099c5fecc5d604582921cbc4b932c81226492b7bbff632f388f1003c8b25f961"
)
MAX_BODY_BYTES = 32 * 1024 * 1024

REFERENCE_COMMITS = {
    "tst_wocker": "3372aa088328700feafeeb07c72ab832ea2d3ecb",
    "tw_block_warrant": "37463c54796ba36f4aac262519ea7fc2ef797de6",
    "tst_wocker_filter_lab": "06c87b7a1735877c9ccbab3a339c1742814a5058",
}

SOURCES: dict[str, dict[str, Any]] = {
    "crsp_ciz_guide": {
        "owner": "Morningstar Indexes / CRSP",
        "title": "CRSP US Stock Databases Guide for Flat File Format 2.0",
        "url": (
            "https://indexes.morningstar.com/docs/guide/"
            "crsp-us-stock-databases-guide-for-flat-file-format-2-0?isRdp=true"
        ),
        "allowed_hosts": ["indexes.morningstar.com"],
        "content_kind": "html",
        "markers": ["CRSP US Stock Databases Guide", "CIZ"],
    },
    "crsp_index_history_feed": {
        "owner": "Center for Research in Security Prices",
        "title": "Index File Description Direct Client Feed",
        "url": (
            "https://www.crsp.org/wp-content/uploads/2023/10/"
            "Index_File_Description-Direct_Client_Feed.pdf"
        ),
        "allowed_hosts": ["www.crsp.org", "crsp.org"],
        "content_kind": "pdf",
        "markers": ["%PDF-", "INDEX LEVEL AND CONSTITUENT HISTORY"],
    },
    "crsp_ciz_migration_notice": {
        "owner": "Center for Research in Security Prices",
        "title": "Important Notice CRSP US Stock and Indexes CIZ",
        "url": (
            "https://www.crsp.org/important-notice-crsp-us-stock-amp-indexes-"
            "databases-flat-file-format-2-0-ciz/"
        ),
        "allowed_hosts": ["www.crsp.org", "crsp.org"],
        "content_kind": "html",
        "markers": ["Beginning July 28, 2026", "December 2024"],
    },
    "lseg_historical_constituents": {
        "owner": "LSEG Developer Community",
        "title": "Building historical index constituents",
        "url": (
            "https://developers.lseg.com/en/article-catalog/article/"
            "building-historical-index-constituents"
        ),
        "allowed_hosts": ["developers.lseg.com"],
        "content_kind": "html",
        "markers": ["Building historical index constituents", "Joiner", "Leaver"],
    },
}
SOURCE_IDS = tuple(SOURCES)

CAPABILITY_MATRIX: dict[str, dict[str, Any]] = {
    "point_in_time_sp500_membership": {
        "status": "partial_primary_documentation",
        "finding": (
            "CRSP 可提供歷史／最新 restated 檔；LSEG 示範以 Joiner／Leaver 重建，"
            "但兩者均未交付本研究的 as-known export 收據。"
        ),
        "source_ids": ["crsp_index_history_feed", "lseg_historical_constituents"],
    },
    "membership_announced_at": {
        "status": "unresolved_primary_documentation",
        "finding": "生效日、change date 或 release time 不是逐列公布 timestamp／event ID。",
        "source_ids": ["crsp_index_history_feed", "lseg_historical_constituents"],
    },
    "membership_effective_at": {
        "status": "partial_primary_documentation",
        "finding": "有 open-date／change-date 線索，仍須授權樣本確認 session、時區及欄位。",
        "source_ids": ["crsp_index_history_feed", "lseg_historical_constituents"],
    },
    "security_metadata_known_at": {
        "status": "unresolved_primary_documentation",
        "finding": "有效區間或目前 metadata 不等於逐列 KnownAt。",
        "source_ids": ["crsp_ciz_guide"],
    },
    "delist_exit_economics": {
        "status": "unresolved_primary_documentation",
        "finding": "文件身份刷新沒有交付 DelRet、缺失原因、現金／換股條款或 successor rows。",
        "source_ids": [],
    },
    "row_level_provenance_replay": {
        "status": "partial_primary_documentation",
        "finding": "文件、release 或 restatement 說明不等於本地 export ID、逐列 source ID、列數及 SHA。",
        "source_ids": ["crsp_index_history_feed", "lseg_historical_constituents"],
    },
}


class ProviderEvidenceRefreshError(ValueError):
    """Fail-closed error with a stable semantic code."""

    def __init__(self, code: str, detail: str):
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}")


def _sha256_bytes(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest()


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _fail(code: str, detail: str) -> None:
    raise ProviderEvidenceRefreshError(code, detail)


def protocol_integrity(root: str | Path) -> dict[str, Any]:
    root_path = Path(root).resolve()
    receipt_path = root_path / PROTOCOL_RECEIPT_PATH
    try:
        receipt = _load_json(receipt_path)
        checks = {
            PROTOCOL_PATH: _sha256_file(root_path / PROTOCOL_PATH) == PROTOCOL_SHA256,
            PROTOCOL_RECEIPT_PATH: _sha256_file(receipt_path)
            == PROTOCOL_RECEIPT_SHA256,
            receipt["parent_provider_gap_closure_protocol"]["path"]: _sha256_file(
                root_path / receipt["parent_provider_gap_closure_protocol"]["path"]
            )
            == receipt["parent_provider_gap_closure_protocol"]["sha256"],
            receipt["parent_provider_gap_closure_receipt"]["path"]: _sha256_file(
                root_path / receipt["parent_provider_gap_closure_receipt"]["path"]
            )
            == receipt["parent_provider_gap_closure_receipt"]["sha256"],
        }
        frozen = (
            receipt["schema_version"] == 1
            and receipt["research_round"] == RESEARCH_ROUND
            and receipt["status"] == "frozen_before_first_remote_observation"
            and receipt["protocol"]
            == {"path": PROTOCOL_PATH, "sha256": PROTOCOL_SHA256}
            and receipt["reference_commits"] == REFERENCE_COMMITS
            and tuple(receipt["source_ids"]) == SOURCE_IDS
            and receipt["first_remote_observation_before_freeze"] is False
            and receipt["raw_sources_persisted"] is False
            and receipt["authorized_provider_package_present_at_freeze"] is False
            and receipt["complete_risk_free_package_present_at_freeze"] is False
            and receipt["formal_backtest_authorized"] is False
            and receipt["strategy_run_count"] == 0
            and receipt["paper_authorized"] is False
            and receipt["paper_state"] == "all_cash"
            and receipt["real_money_action_usd"] == 0
            and receipt["frozen_control_count"] == 12
            and receipt["frozen_attack_count"] == 12
            and all(checks.values())
        )
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        _fail("protocol_mismatch", f"Round33 protocol or receipt is invalid: {exc}")
    if not frozen:
        _fail("protocol_mismatch", "Round33 protocol／receipt or parent hash is invalid")
    return {
        "passed": True,
        "frozen_at": receipt["frozen_at"],
        "git_head_at_freeze": receipt["git_head_at_freeze"],
        "hash_checks": checks,
    }


def _host_allowed(final_url: str, allowed_hosts: list[str]) -> bool:
    parsed = urlparse(final_url)
    if parsed.scheme != "https" or not parsed.hostname:
        return False
    return any(
        parsed.hostname == host or parsed.hostname.endswith("." + host)
        for host in allowed_hosts
    )


def _marker_present(body: bytes, marker: str) -> bool:
    return marker.encode("utf-8").lower() in body.lower()


def _validate_response(source_id: str, response: Mapping[str, Any]) -> dict[str, Any]:
    if source_id not in SOURCES:
        _fail("source_set_mismatch", f"unknown source id: {source_id}")
    spec = SOURCES[source_id]
    final_url = response.get("final_url")
    status = response.get("status")
    content_type = str(response.get("content_type") or "").casefold()
    body = response.get("body")
    if not isinstance(final_url, str) or not _host_allowed(final_url, spec["allowed_hosts"]):
        _fail("non_https_or_host_drift", f"{source_id} final URL is outside the frozen host")
    if status != 200:
        _fail("http_status_mismatch", f"{source_id} returned HTTP {status!r}")
    if not isinstance(body, bytes):
        _fail("body_type_mismatch", f"{source_id} body must remain bytes")
    if len(body) > MAX_BODY_BYTES:
        _fail("body_size_exceeded", f"{source_id} exceeds {MAX_BODY_BYTES} bytes")
    expected_type = "application/pdf" if spec["content_kind"] == "pdf" else "text/html"
    if expected_type not in content_type:
        _fail("content_type_mismatch", f"{source_id} expected {expected_type}")
    marker_checks = {marker: _marker_present(body, marker) for marker in spec["markers"]}
    if not all(marker_checks.values()):
        _fail("marker_missing", f"{source_id} marker check failed")
    return {
        "source_id": source_id,
        "owner": spec["owner"],
        "title": spec["title"],
        "url": spec["url"],
        "final_url": final_url,
        "host": urlparse(final_url).hostname,
        "http_status": status,
        "content_type": content_type,
        "content_kind": spec["content_kind"],
        "body_size_bytes": len(body),
        "body_sha256": _sha256_bytes(body),
        "marker_checks": marker_checks,
        "raw_source_persisted": False,
        "matches_frozen_identity": True,
    }


def _safe_observation_metadata(source_id: str, response: Mapping[str, Any]) -> dict[str, Any]:
    """Record non-content metadata even when identity validation fails."""

    spec = SOURCES[source_id]
    body = response.get("body")
    body_bytes = body if isinstance(body, bytes) else b""
    final_url = response.get("final_url")
    return {
        "source_id": source_id,
        "owner": spec["owner"],
        "title": spec["title"],
        "url": spec["url"],
        "final_url": final_url,
        "host": urlparse(final_url).hostname if isinstance(final_url, str) else None,
        "http_status": response.get("status"),
        "content_type": str(response.get("content_type") or "").casefold(),
        "content_kind": spec["content_kind"],
        "body_size_bytes": len(body_bytes),
        "body_sha256": _sha256_bytes(body_bytes) if isinstance(body, bytes) else None,
        "marker_checks": {
            marker: _marker_present(body_bytes, marker) if isinstance(body, bytes) else False
            for marker in spec["markers"]
        },
        "raw_source_persisted": False,
        "matches_frozen_identity": False,
    }


def inspect_current_sources(
    downloaded: Mapping[str, Mapping[str, Any]],
    *,
    root: str | Path,
    previous_observations: Mapping[str, Mapping[str, Any]] | None = None,
) -> dict[str, dict[str, Any]]:
    """Validate an in-memory observation without writing any source bytes."""

    protocol_integrity(root)
    if set(downloaded) != set(SOURCE_IDS):
        _fail("source_set_mismatch", "source id set differs from the frozen four-source set")
    observations = {
        source_id: _validate_response(source_id, downloaded[source_id])
        for source_id in SOURCE_IDS
    }
    for source_id, previous in (previous_observations or {}).items():
        if source_id not in observations:
            _fail("source_set_mismatch", f"previous observation has unknown source {source_id}")
        if previous.get("body_sha256") != observations[source_id]["body_sha256"]:
            _fail("source_hash_drift", f"{source_id} hash differs from previous observation")
        if previous.get("final_url") != observations[source_id]["final_url"]:
            _fail("source_hash_drift", f"{source_id} final URL differs from previous observation")
    return observations


def _frozen_decision() -> dict[str, Any]:
    return {
        "authorized_provider_package": False,
        "complete_risk_free_package": False,
        "formal_readiness": {"passed": 1, "total": 18, "all_passed": False},
        "point_in_time_readiness": {"passed": 1, "total": 20, "all_passed": False},
        "formal_backtest_authorized": False,
        "strategy_run_count": 0,
        "paper_authorized": False,
        "paper_state": "all_cash",
        "real_money_action_usd": 0,
    }


def make_refresh_result(
    downloaded: Mapping[str, Mapping[str, Any]],
    *,
    root: str | Path,
    previous_observations: Mapping[str, Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Create a metadata-only result; every invalid observation stays fail-closed."""

    protocol = None
    observations: dict[str, dict[str, Any]] = {}
    error: dict[str, str] | None = None
    observation_errors: dict[str, dict[str, str]] = {}
    try:
        protocol = protocol_integrity(root)
        # Validate each available response independently so a single migrated or
        # unavailable page cannot erase the useful metadata for other sources.
        for source_id, response in downloaded.items():
            try:
                observations[source_id] = _validate_response(source_id, response)
            except ProviderEvidenceRefreshError as exc:
                observations[source_id] = _safe_observation_metadata(source_id, response)
                observation_errors[source_id] = {"code": exc.code, "detail": exc.detail}
        for source_id, previous in (previous_observations or {}).items():
            if source_id in observations:
                if previous.get("body_sha256") != observations[source_id]["body_sha256"]:
                    observation_errors[source_id] = {
                        "code": "source_hash_drift",
                        "detail": f"{source_id} hash differs from previous observation",
                        "previous_body_sha256": previous.get("body_sha256"),
                        "current_body_sha256": observations[source_id].get("body_sha256"),
                        "previous_final_url": previous.get("final_url"),
                        "current_final_url": observations[source_id].get("final_url"),
                    }
                elif previous.get("final_url") != observations[source_id]["final_url"]:
                    observation_errors[source_id] = {
                        "code": "source_hash_drift",
                        "detail": f"{source_id} final URL differs from previous observation",
                        "previous_body_sha256": previous.get("body_sha256"),
                        "current_body_sha256": observations[source_id].get("body_sha256"),
                        "previous_final_url": previous.get("final_url"),
                        "current_final_url": observations[source_id].get("final_url"),
                    }
        missing = sorted(set(SOURCE_IDS) - set(downloaded))
        if missing:
            _fail("source_set_mismatch", f"missing frozen source ids: {missing}")
        if observation_errors:
            first = next(iter(observation_errors.items()))
            _fail(first[1]["code"], f"{first[0]}: {first[1]['detail']}")
        status = "observed_official_sources"
    except ProviderEvidenceRefreshError as exc:
        error = {"code": exc.code, "detail": exc.detail}
        status = "manual_review_required"
    decision = _frozen_decision()
    return {
        "schema_version": 1,
        "research_round": RESEARCH_ROUND,
        "status": status,
        "protocol_sha256": PROTOCOL_SHA256,
        "protocol_integrity": protocol or {"passed": False},
        "observations": observations,
        "source_identity_count": len(observations),
        "expected_source_identity_count": len(SOURCE_IDS),
        "all_frozen_identity_checks_pass": status == "observed_official_sources",
        "manual_review_required": status != "observed_official_sources",
        "error": error,
        "observation_errors": observation_errors,
        "capability_matrix": copy.deepcopy(CAPABILITY_MATRIX),
        "new_source_qualified": False,
        "provider_package_qualified": False,
        **decision,
        "raw_source_persisted": False,
        "next_action": (
            "若需正式回測，須取得使用者授權 package 並按 Round21 驗收 18/18、"
            "point-in-time 20/20、execution 16/16 及完整 RF；本探針不會自動升級。"
        ),
    }


def validate_result(payload: Mapping[str, Any], *, root: str | Path) -> dict[str, Any]:
    """Validate the saved result and reject optimistic capability substitutions."""

    protocol_integrity(root)
    if payload.get("research_round") != RESEARCH_ROUND:
        _fail("protocol_mismatch", "research round mismatch")
    if payload.get("protocol_sha256") != PROTOCOL_SHA256:
        _fail("protocol_mismatch", "protocol SHA-256 mismatch")
    if payload.get("raw_source_persisted") is not False:
        _fail("raw_source_persisted", "raw provider bytes may not be persisted")
    if payload.get("provider_package_qualified") is not False:
        _fail("decision_boundary_violation", "provider package cannot be qualified by a probe")
    if payload.get("formal_backtest_authorized") is not False:
        _fail("decision_boundary_violation", "formal backtest cannot be authorized by a probe")
    if payload.get("paper_authorized") is not False or payload.get("paper_state") != "all_cash":
        _fail("decision_boundary_violation", "probe cannot authorize or populate Paper")
    if payload.get("real_money_action_usd") != 0:
        _fail("decision_boundary_violation", "probe cannot create real-money action")
    for capability, expected in CAPABILITY_MATRIX.items():
        actual = payload.get("capability_matrix", {}).get(capability, {})
        if actual.get("status") != expected["status"]:
            code = (
                "announcement_time_substitution"
                if capability == "membership_announced_at"
                else "known_at_substitution"
                if capability == "security_metadata_known_at"
                else "decision_boundary_violation"
            )
            _fail(code, f"capability status drift: {capability}")
    return {"passed": True, "status": payload.get("status")}


def load_previous_observations(path: str | Path) -> dict[str, dict[str, Any]] | None:
    path_obj = Path(path)
    if not path_obj.exists():
        return None
    payload = _load_json(path_obj)
    observations = payload.get("observations")
    return observations if isinstance(observations, dict) else None
