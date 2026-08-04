from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

from .provider_convergence import (
    DIRECT_STOCK_CAPABILITIES,
    EVIDENCE_AS_OF,
    EXPECTED_ACTUAL_FORMAL_READINESS,
    OVERLAY_CAPABILITIES,
    STOCK_GUIDE,
    TREASURY_GUIDE,
    frozen_convergence_record,
    validate_provider_convergence,
)

ATTACKS = [
    ("01", "協議 SHA 漂移", "convergence_protocol_mismatch"),
    ("02", "參考 commit 漂移", "reference_commit_mismatch"),
    ("03", "指南 effective date 漂移", "guide_version_mismatch"),
    ("04", "PDF hash 漂移", "guide_hash_mismatch"),
    ("05", "PDF 頁數漂移", "guide_identity_mismatch"),
    ("06", "少一個 CIZ 直接表", "stock_capability_set_mismatch"),
    ("07", "MbrStartDt 冒充 AnnouncedAt", "membership_announcement_substitution"),
    ("08", "SecInfoStartDt 冒充 KnownAt", "security_known_at_substitution"),
    ("09", "缺失 DelRet 填 0", "delist_economics_imputation"),
    ("10", "4 週日序列冒充 1 個月日序列", "risk_free_tenor_substitution"),
    ("11", "1 個月年率直接除以 252", "risk_free_unit_substitution"),
    ("12", "文件通過後啟動 Paper", "convergence_decision_boundary_violation"),
]


def _error_code(exc: BaseException) -> str | None:
    return getattr(exc, "code", None)


def _attacked_record(attack_id: str) -> dict[str, Any]:
    record = frozen_convergence_record()
    if attack_id == "01":
        record["protocol_sha256"] = "0" * 64
    elif attack_id == "02":
        record["reference_commits"]["tst_wocker"] = "0" * 40
    elif attack_id == "03":
        record["guides"]["stock_ciz"]["effective_date"] = "2026-07-28"
    elif attack_id == "04":
        record["guides"]["stock_ciz"]["pdf_sha256"] = "0" * 64
    elif attack_id == "05":
        record["guides"]["stock_ciz"]["page_count"] = 98
    elif attack_id == "06":
        del record["stock"]["direct_capabilities"]["stk_delists.csv"]
    elif attack_id == "07":
        record["stock"]["membership_semantics"]["announced_at_source"] = (
            "MbrStartDt"
        )
    elif attack_id == "08":
        record["stock"]["security_history_semantics"]["known_at_source"] = (
            "SecInfoStartDt"
        )
    elif attack_id == "09":
        record["stock"]["delist_semantics"]["missing_delret_imputed_zero"] = True
    elif attack_id == "10":
        record["treasury"]["four_week_used_as_one_month_daily"] = True
    elif attack_id == "11":
        record["treasury"]["annual_yield_divided_by_252"] = True
    elif attack_id == "12":
        record["decision"]["paper_authorized"] = True
    else:  # pragma: no cover - only fixed attack IDs are routed here.
        raise ValueError(f"unknown attack: {attack_id}")
    return record


def _run_attack(attack_id: str, *, root: Path) -> str | None:
    try:
        validate_provider_convergence(_attacked_record(attack_id), root=root)
    except Exception as exc:  # noqa: BLE001 - fixed semantic attack harness.
        return _error_code(exc)
    return None


def run_provider_convergence_validation(root: str | Path) -> dict[str, Any]:
    root_path = Path(root).resolve()
    record = frozen_convergence_record()
    validation = validate_provider_convergence(record, root=root_path)
    stock = record["stock"]
    treasury = record["treasury"]
    decision = record["decision"]

    controls = [
        {
            "id": "01",
            "label": "協議及上游綁定",
            "passed": validation["protocol_integrity"]["passed"],
            "detail": "Round 20 協議、事前收據及第十八／十九輪契約 SHA-256 完整",
        },
        {
            "id": "02",
            "label": "台股參考版本",
            "passed": record["reference_commits"]
            == frozen_convergence_record()["reference_commits"],
            "detail": "三個參考 repository 精確綁定，只轉移研究紀律而不搬參數",
        },
        {
            "id": "03",
            "label": "指南版本身份",
            "passed": all(
                record["guides"][key]["effective_date"] == expected["effective_date"]
                for key, expected in (
                    ("stock_ciz", STOCK_GUIDE),
                    ("treasury", TREASURY_GUIDE),
                )
            ),
            "detail": "兩個官方標題及 effective date 精確固定",
        },
        {
            "id": "04",
            "label": "PDF 身份",
            "passed": all(
                record["guides"][key]["pdf_sha256"] == expected["pdf_sha256"]
                and record["guides"][key]["page_count"] == expected["page_count"]
                for key, expected in (
                    ("stock_ciz", STOCK_GUIDE),
                    ("treasury", TREASURY_GUIDE),
                )
            ),
            "detail": "兩份官方 PDF URL、頁數及 SHA-256 與凍結收據一致",
        },
        {
            "id": "05",
            "label": "證券身份歷史",
            "passed": stock["security_history_semantics"]["fields"]
            == ["PERMNO", "PERMCO", "SecInfoStartDt", "SecInfoEndDt"],
            "detail": "永久 ID、歷史有效區間及歷史分類能力有官方欄位支持",
        },
        {
            "id": "06",
            "label": "成分只限生效區間",
            "passed": bool(
                stock["membership_semantics"]["announcement_time_documented"]
                is False
                and stock["membership_semantics"]["announced_at_source"] is None
            ),
            "detail": "MbrStartDt／EndDt 不被寫成成分公布時間",
        },
        {
            "id": "07",
            "label": "Raw 日線及交易狀態",
            "passed": stock["daily_security_semantics"]
            == {"raw_price_volume_return": True, "trading_status": True},
            "detail": "日價、成交量、回報、停牌及交易狀態能力有指南支持",
        },
        {
            "id": "08",
            "label": "公司行動日期與條款",
            "passed": all(stock["distribution_semantics"].values()),
            "detail": "除權息、宣派、記錄、派付日、現金／比率及 successor 齊備",
        },
        {
            "id": "09",
            "label": "退市經濟條款",
            "passed": bool(
                stock["delist_semantics"]["delret"]
                and stock["delist_semantics"]["delret_missing_type"]
                and stock["delist_semantics"]["successor_permno_permco"]
                and stock["delist_semantics"]["storage_date"]
                and not stock["delist_semantics"]["missing_delret_imputed_zero"]
            ),
            "detail": "DelRet、缺失類型、successor 及 storage date 齊備；缺值不填 0",
        },
        {
            "id": "10",
            "label": "五份 evidence overlay",
            "passed": stock["overlay_capabilities"] == OVERLAY_CAPABILITIES,
            "detail": "日曆、KnownAt、公布時間、公司行動及退出條款缺口全數保留",
        },
        {
            "id": "11",
            "label": "Treasury 年期與單位",
            "passed": bool(
                treasury["daily_rf_tenors"] == ["4_week", "13_week", "26_week"]
                and treasury["exact_1_month_series"]["frequency"] == "monthly"
                and not treasury["four_week_used_as_one_month_daily"]
                and not treasury["annual_yield_divided_by_252"]
                and not treasury["formal_rf_manifest_generated"]
            ),
            "detail": "4 週日序列與精確 1 個月月序列分開；不冒充正式 RF",
        },
        {
            "id": "12",
            "label": "決策邊界",
            "passed": decision == frozen_convergence_record()["decision"],
            "detail": "正式 1/18、provider 0、策略 run 0、Paper 全現金、實金 US$0",
        },
    ]
    attacks = []
    for attack_id, label, expected_code in ATTACKS:
        observed = _run_attack(attack_id, root=root_path)
        attacks.append(
            {
                "id": attack_id,
                "label": label,
                "expected_error_code": expected_code,
                "observed_error_code": observed,
                "rejected": observed == expected_code,
            }
        )
    control_summary = {
        "passed": sum(row["passed"] for row in controls),
        "total": len(controls),
        "all_passed": all(row["passed"] for row in controls),
    }
    attack_summary = {
        "rejected": sum(row["rejected"] for row in attacks),
        "total": len(attacks),
        "all_rejected": all(row["rejected"] for row in attacks),
    }
    return {
        "schema_version": 1,
        "research_round": 20,
        "convergence_version": record["convergence_version"],
        "evidence_as_of": EVIDENCE_AS_OF,
        "status": "guide_evidence_converged_provider_and_rf_still_unqualified",
        "protocol_integrity": validation["protocol_integrity"],
        "reference_commits": record["reference_commits"],
        "guides": record["guides"],
        "capability_matrix": {
            "requested_input_count": 10,
            "direct_documented_count": len(DIRECT_STOCK_CAPABILITIES),
            "overlay_required_count": len(OVERLAY_CAPABILITIES),
            "direct": DIRECT_STOCK_CAPABILITIES,
            "overlay_required": OVERLAY_CAPABILITIES,
        },
        "stock_semantics": copy.deepcopy(record["stock"]),
        "treasury": copy.deepcopy(treasury),
        "control_summary": control_summary,
        "controls": controls,
        "attack_summary": attack_summary,
        "attacks": attacks,
        "actual_formal_readiness": copy.deepcopy(EXPECTED_ACTUAL_FORMAL_READINESS),
        "authorized_provider_package_received": False,
        "complete_risk_free_package_received": False,
        "formal_stock_backtest_input_ready": False,
        "formal_stock_backtest_completed": False,
        "strategy_run_count": 0,
        "paper": {
            "authorized": False,
            "state": "all_cash",
            "backfilled_trades": 0,
            "positions": [],
        },
        "real_money_action_usd": 0,
        "next_action": (
            "向已授權 CRSP／WRDS 帳戶核對 Stock CIZ 五份直接表、S&P 500 INDNO、"
            "五份 evidence overlay，以及與凍結經濟定義完全相同的 1 個月日度簡單 RF；"
            "只在真實 18/18 後運行一次正式回測。"
        ),
        "disclaimer": (
            "12/12 控制及 12/12 攻擊只證明指南證據驗證器 fail closed；"
            "不是供應商包、策略回報、Paper 或盈利通過。"
        ),
    }
