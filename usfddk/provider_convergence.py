from __future__ import annotations

import copy
import hashlib
import json
import re
from pathlib import Path
from typing import Any

CONVERGENCE_VERSION = "round20-provider-convergence-v1"
PROBE_VERSION = "round20-provider-guide-probe-v1"
PROTOCOL_PATH = "docs/SHORT_TERM_PROVIDER_CONVERGENCE_PROTOCOL.md"
PROTOCOL_RECEIPT_PATH = (
    "artifacts/short_term_provider_convergence_protocol_receipt.json"
)
PROTOCOL_SHA256 = "7ef6c405c5aa9a7934e55511cb8962c9c47f007e9dc0a6dccd4be3fd0b836024"
PROTOCOL_RECEIPT_SHA256 = (
    "3913492d6df3418fbf27ffce20e5b7d1c57da7379033af5e569ee9b189955985"
)
EVIDENCE_AS_OF = "2026-08-04"

REFERENCE_COMMITS = {
    "tst_wocker": "3372aa088328700feafeeb07c72ab832ea2d3ecb",
    "tw_block_warrant": "37463c54796ba36f4aac262519ea7fc2ef797de6",
    "tst_wocker_filter_lab": "06c87b7a1735877c9ccbab3a339c1742814a5058",
}

STOCK_GUIDE = {
    "title": "CRSP US Stock Databases Guide for Flat File Format 2 0",
    "landing_url": (
        "https://indexes.morningstar.com/docs/guide/"
        "crsp-us-stock-databases-guide-for-flat-file-format-2-0?isRdp=true"
    ),
    "pdf_url": "https://indexes.morningstar.com/api/docs/6a70fc12f1246457e16fbfad",
    "effective_date": "2026-07-27",
    "page_count": 97,
    "pdf_sha256": "e42f452207d4a30ef05de542a2dac9522f240100cec99a0309b1b3ab20699ec6",
}
TREASURY_GUIDE = {
    "title": "CRSP US Treasury Database Guide",
    "landing_url": (
        "https://indexes.morningstar.com/docs/guide/"
        "crsp-us-treasury-database-guide?isRdp=true"
    ),
    "pdf_url": "https://indexes.morningstar.com/api/docs/6a454eb24453862570c90c07",
    "effective_date": "2026-06-30",
    "page_count": 46,
    "pdf_sha256": "d256ae7633049eca9d4c9385913f599c7bece7c3c508c39bf3b8afa18c479781",
}

DIRECT_STOCK_CAPABILITIES = {
    "stk_security_info_hist.csv": "direct_documented",
    "stk_ind_membership.csv": "direct_effective_interval_only",
    "stk_dly_security_data.csv": "direct_documented",
    "stk_distributions.csv": "direct_documented",
    "stk_delists.csv": "direct_documented",
}
OVERLAY_CAPABILITIES = {
    "trading_calendar.csv": "provider_or_evidence_overlay_required",
    "security_info_availability.csv": "evidence_overlay_required",
    "membership_announcements.csv": "evidence_overlay_required",
    "corporate_action_overlay.csv": "provider_or_evidence_overlay_required",
    "exit_terms.csv": "provider_or_evidence_overlay_required",
}

EXPECTED_ACTUAL_FORMAL_READINESS = {
    "passed": 1,
    "total": 18,
    "all_passed": False,
    "only_passed_gate": "01_preregistration_integrity",
}


class ProviderConvergenceError(ValueError):
    """Fail-closed guide-evidence error with a stable semantic code."""

    def __init__(self, code: str, detail: str):
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}")


def _fail(code: str, detail: str) -> None:
    raise ProviderConvergenceError(code, detail)


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _protocol_integrity(root: str | Path) -> dict[str, Any]:
    root_path = Path(root).resolve()
    receipt_path = root_path / PROTOCOL_RECEIPT_PATH
    try:
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        checks = {
            PROTOCOL_PATH: _sha256_file(root_path / PROTOCOL_PATH)
            == PROTOCOL_SHA256,
            PROTOCOL_RECEIPT_PATH: _sha256_file(receipt_path)
            == PROTOCOL_RECEIPT_SHA256,
            receipt["parent_formal_protocol"]["path"]: _sha256_file(
                root_path / receipt["parent_formal_protocol"]["path"]
            )
            == receipt["parent_formal_protocol"]["sha256"],
            receipt["parent_formal_protocol_receipt"]["path"]: _sha256_file(
                root_path / receipt["parent_formal_protocol_receipt"]["path"]
            )
            == receipt["parent_formal_protocol_receipt"]["sha256"],
            receipt["parent_risk_free_protocol"]["path"]: _sha256_file(
                root_path / receipt["parent_risk_free_protocol"]["path"]
            )
            == receipt["parent_risk_free_protocol"]["sha256"],
            receipt["parent_authorized_handoff_protocol"]["path"]: _sha256_file(
                root_path / receipt["parent_authorized_handoff_protocol"]["path"]
            )
            == receipt["parent_authorized_handoff_protocol"]["sha256"],
        }
        passed = bool(
            receipt["schema_version"] == 1
            and receipt["research_round"] == 20
            and receipt["status"]
            == "frozen_after_official_guide_inspection_before_convergence_implementation"
            and receipt["protocol"]
            == {"path": PROTOCOL_PATH, "sha256": PROTOCOL_SHA256}
            and receipt["reference_commits"] == REFERENCE_COMMITS
            and receipt["official_guides_inspected_at_freeze"] is True
            and receipt["independent_first_seen_evidence"] is False
            and receipt["stock_ciz_guide"]
            == {
                key: STOCK_GUIDE[key]
                for key in ("effective_date", "page_count", "pdf_sha256", "pdf_url")
            }
            and receipt["treasury_guide"]
            == {
                key: TREASURY_GUIDE[key]
                for key in ("effective_date", "page_count", "pdf_sha256", "pdf_url")
            }
            and receipt["convergence_implementation_present_at_freeze"] is False
            and receipt["convergence_output_present_at_freeze"] is False
            and receipt["provider_package_present_at_freeze"] is False
            and receipt["complete_risk_free_bundle_present_at_freeze"] is False
            and receipt["strategy_result_present_at_freeze"] is False
            and receipt["strategy_run_count"] == 0
            and receipt["paper_authorized"] is False
            and receipt["paper_state"] == "all_cash"
            and receipt["real_money_action_usd"] == 0
            and receipt["frozen_control_count"] == 12
            and receipt["frozen_attack_count"] == 12
            and all(checks.values())
        )
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError):
        receipt = {}
        checks = {}
        passed = False
    if not passed:
        _fail(
            "convergence_protocol_mismatch",
            "Round 20 協議、凍結收據或上游正式契約不完整",
        )
    return {
        "passed": True,
        "frozen_at": receipt["frozen_at"],
        "git_head_at_freeze": receipt["git_head_at_freeze"],
        "official_guides_inspected_at_freeze": True,
        "independent_first_seen_evidence": False,
        "hash_checks": checks,
    }


def frozen_convergence_record() -> dict[str, Any]:
    """Return the frozen, guide-backed interpretation before any provider data."""

    return {
        "convergence_version": CONVERGENCE_VERSION,
        "protocol_sha256": PROTOCOL_SHA256,
        "reference_commits": copy.deepcopy(REFERENCE_COMMITS),
        "guides": {
            "stock_ciz": copy.deepcopy(STOCK_GUIDE),
            "treasury": copy.deepcopy(TREASURY_GUIDE),
        },
        "stock": {
            "direct_capabilities": copy.deepcopy(DIRECT_STOCK_CAPABILITIES),
            "overlay_capabilities": copy.deepcopy(OVERLAY_CAPABILITIES),
            "membership_semantics": {
                "fields": ["PERMNO", "INDNO", "MbrStartDt", "MbrEndDt", "MbrFlg"],
                "announcement_time_documented": False,
                "announced_at_source": None,
            },
            "security_history_semantics": {
                "fields": ["PERMNO", "PERMCO", "SecInfoStartDt", "SecInfoEndDt"],
                "known_at_documented": False,
                "known_at_source": None,
            },
            "daily_security_semantics": {
                "raw_price_volume_return": True,
                "trading_status": True,
            },
            "distribution_semantics": {
                "ex_date": True,
                "declare_date": True,
                "record_date": True,
                "pay_date": True,
                "cash_and_factor_terms": True,
                "successor_ids": True,
            },
            "delist_semantics": {
                "delret": True,
                "delret_missing_type": True,
                "successor_permno_permco": True,
                "storage_date": True,
                "missing_delret_imputed_zero": False,
            },
        },
        "treasury": {
            "individual_issue_daily_unadjusted_return_field": "TDRETNUA",
            "daily_rf_tenors": ["4_week", "13_week", "26_week"],
            "daily_4_week_treasnox": 2_000_061,
            "exact_1_month_series": {
                "treasnox": 2_000_001,
                "frequency": "monthly",
                "unit": "continuously_compounded_yield",
            },
            "same_provider_mapping_status": (
                "same_provider_mapping_candidate_not_formal_rf"
            ),
            "four_week_used_as_one_month_daily": False,
            "annual_yield_divided_by_252": False,
            "formal_rf_manifest_generated": False,
        },
        "decision": {
            "actual_formal_readiness": copy.deepcopy(
                EXPECTED_ACTUAL_FORMAL_READINESS
            ),
            "authorized_provider_package_received": False,
            "complete_risk_free_package_received": False,
            "formal_stock_backtest_completed": False,
            "strategy_run_count": 0,
            "paper_authorized": False,
            "paper_state": "all_cash",
            "backfilled_trades": 0,
            "positions": [],
            "real_money_action_usd": 0,
        },
    }


def validate_provider_convergence(
    record: dict[str, Any], *, root: str | Path
) -> dict[str, Any]:
    protocol = _protocol_integrity(root)
    if (
        record.get("convergence_version") != CONVERGENCE_VERSION
        or record.get("protocol_sha256") != PROTOCOL_SHA256
    ):
        _fail("convergence_protocol_mismatch", "協議版本或 SHA-256 漂移")
    if record.get("reference_commits") != REFERENCE_COMMITS:
        _fail("reference_commit_mismatch", "台股參考 commit 與凍結版本不符")

    guides = record.get("guides", {})
    for key, expected in (("stock_ciz", STOCK_GUIDE), ("treasury", TREASURY_GUIDE)):
        actual = guides.get(key, {})
        if actual.get("effective_date") != expected["effective_date"]:
            _fail("guide_version_mismatch", "官方指南 effective date 漂移")
        if actual.get("pdf_sha256") != expected["pdf_sha256"]:
            _fail("guide_hash_mismatch", "官方指南 PDF SHA-256 漂移")
        identity_keys = ("title", "landing_url", "pdf_url", "page_count")
        if any(actual.get(name) != expected[name] for name in identity_keys):
            _fail("guide_identity_mismatch", "官方指南標題、URL 或頁數漂移")

    stock = record.get("stock", {})
    if (
        stock.get("direct_capabilities") != DIRECT_STOCK_CAPABILITIES
        or stock.get("overlay_capabilities") != OVERLAY_CAPABILITIES
        or stock.get("daily_security_semantics")
        != {"raw_price_volume_return": True, "trading_status": True}
        or stock.get("distribution_semantics")
        != {
            "ex_date": True,
            "declare_date": True,
            "record_date": True,
            "pay_date": True,
            "cash_and_factor_terms": True,
            "successor_ids": True,
        }
    ):
        _fail(
            "stock_capability_set_mismatch",
            "Stock CIZ 直接能力或五份 evidence overlay 集合不符",
        )
    membership = stock.get("membership_semantics", {})
    if (
        membership.get("announcement_time_documented") is not False
        or membership.get("announced_at_source") is not None
    ):
        _fail(
            "membership_announcement_substitution",
            "MbrStartDt 不得冒充 AnnouncedAt",
        )
    security = stock.get("security_history_semantics", {})
    if (
        security.get("known_at_documented") is not False
        or security.get("known_at_source") is not None
    ):
        _fail(
            "security_known_at_substitution",
            "SecInfoStartDt 不得冒充 KnownAt",
        )
    delist = stock.get("delist_semantics", {})
    if (
        delist.get("delret") is not True
        or delist.get("delret_missing_type") is not True
        or delist.get("successor_permno_permco") is not True
        or delist.get("storage_date") is not True
        or delist.get("missing_delret_imputed_zero") is not False
    ):
        _fail("delist_economics_imputation", "缺失 DelRet 不得填 0 或事後猜測")

    treasury = record.get("treasury", {})
    if (
        treasury.get("daily_rf_tenors") != ["4_week", "13_week", "26_week"]
        or treasury.get("daily_4_week_treasnox") != 2_000_061
        or treasury.get("exact_1_month_series", {}).get("treasnox") != 2_000_001
        or treasury.get("exact_1_month_series", {}).get("frequency") != "monthly"
        or treasury.get("four_week_used_as_one_month_daily") is not False
    ):
        _fail(
            "risk_free_tenor_substitution",
            "4 週日序列不得冒充精確 1 個月日序列",
        )
    if (
        treasury.get("individual_issue_daily_unadjusted_return_field") != "TDRETNUA"
        or treasury.get("exact_1_month_series", {}).get("unit")
        != "continuously_compounded_yield"
        or treasury.get("annual_yield_divided_by_252") is not False
    ):
        _fail(
            "risk_free_unit_substitution",
            "年率收益率不得直接除以 252 冒充日度簡單回報",
        )

    decision = record.get("decision", {})
    expected_decision = frozen_convergence_record()["decision"]
    if (
        treasury.get("same_provider_mapping_status")
        != "same_provider_mapping_candidate_not_formal_rf"
        or treasury.get("formal_rf_manifest_generated") is not False
        or decision != expected_decision
    ):
        _fail(
            "convergence_decision_boundary_violation",
            "指南證據不得提高 readiness、啟動回測、Paper 或實金",
        )
    return {
        "passed": True,
        "protocol_integrity": protocol,
        "direct_stock_capability_count": len(DIRECT_STOCK_CAPABILITIES),
        "overlay_capability_count": len(OVERLAY_CAPABILITIES),
        "treasury_mapping_status": treasury["same_provider_mapping_status"],
        "formal_readiness": copy.deepcopy(EXPECTED_ACTUAL_FORMAL_READINESS),
    }


def _extract_landing_identity(html: str, expected: dict[str, Any]) -> dict[str, Any]:
    normalized = re.sub(r"[^A-Za-z0-9]+", " ", html)
    title = expected["title"] if expected["title"] in normalized else None
    effective_dates = re.findall(r"20\d{2}-\d{2}-\d{2}", html)
    pdf_ids = re.findall(r"6a[0-9a-f]{22}", html)
    return {
        "title": title,
        "effective_date": expected["effective_date"]
        if expected["effective_date"] in effective_dates
        else (effective_dates[0] if effective_dates else None),
        "pdf_url": f"https://indexes.morningstar.com/api/docs/{pdf_ids[0]}"
        if pdf_ids
        else None,
    }


def inspect_provider_guides(
    *,
    stock_landing_html: str,
    stock_pdf_bytes: bytes,
    treasury_landing_html: str,
    treasury_pdf_bytes: bytes,
) -> dict[str, Any]:
    """Inspect live guide identity without changing the frozen interpretation."""

    observations: dict[str, dict[str, Any]] = {}
    for key, html, pdf_bytes, expected in (
        ("stock_ciz", stock_landing_html, stock_pdf_bytes, STOCK_GUIDE),
        ("treasury", treasury_landing_html, treasury_pdf_bytes, TREASURY_GUIDE),
    ):
        identity = _extract_landing_identity(html, expected)
        observed = {
            "title": identity["title"],
            "landing_url": expected["landing_url"],
            "pdf_url": identity["pdf_url"],
            "effective_date": identity["effective_date"],
            "page_count": pdf_bytes.count(b"/Type/Page>>"),
            "pdf_sha256": hashlib.sha256(pdf_bytes).hexdigest(),
            "size_bytes": len(pdf_bytes),
        }
        observed["matches_frozen_guide"] = all(
            observed[name] == expected[name]
            for name in (
                "title",
                "landing_url",
                "pdf_url",
                "effective_date",
                "page_count",
                "pdf_sha256",
            )
        )
        observations[key] = observed
    matches = all(row["matches_frozen_guide"] for row in observations.values())
    return {
        "schema_version": 1,
        "research_round": 20,
        "probe_version": PROBE_VERSION,
        "status": "matches_frozen_guides" if matches else "unqualified_new_guide",
        "observations": observations,
        "frozen_guides": {
            "stock_ciz": copy.deepcopy(STOCK_GUIDE),
            "treasury": copy.deepcopy(TREASURY_GUIDE),
        },
        "all_match_frozen_guides": matches,
        "new_guide_qualified": False,
        "provider_package_qualified": False,
        "formal_rf_input_ready": False,
        "formal_backtest_authorized": False,
        "strategy_run_count": 0,
        "paper_authorized": False,
        "paper_state": "all_cash",
        "real_money_action_usd": 0,
        "next_action": (
            "任何標題、生效日、PDF URL、頁數或 SHA-256 漂移只標記未合資格新版本；"
            "必須另立人工審閱及新協議，probe 不會自動提高 readiness。"
        ),
    }
