from __future__ import annotations

from pathlib import Path
from typing import Any

from .provider_gap_closure import (
    CANDIDATE_ROUTE_IDS,
    CAPABILITY_IDS,
    EVIDENCE_AS_OF,
    PRIMARY_SOURCES,
    PROCUREMENT_QUESTIONS,
    frozen_gap_closure_record,
    validate_provider_gap_closure,
)

ATTACKS = [
    ("01", "協議 SHA 漂移", "gap_protocol_mismatch"),
    ("02", "台股參考 commit 漂移", "gap_reference_mismatch"),
    ("03", "候選路徑次序漂移", "candidate_set_mismatch"),
    ("04", "少一項正式能力", "capability_set_mismatch"),
    ("05", "第三方文章冒充一手證據", "non_primary_evidence"),
    ("06", "由品牌宣傳推算產品", "product_identity_inference"),
    ("07", "公開下載冒充研究授權", "license_inference"),
    ("08", "歷史宣傳冒充 20 年覆蓋", "coverage_inference"),
    ("09", "生效時間冒充公布時間", "membership_time_substitution"),
    ("10", "有效區間冒充 KnownAt", "known_at_substitution"),
    ("11", "調整價冒充 raw open", "adjusted_price_substitution"),
    ("12", "缺失退出代價填 0", "delist_imputation"),
    ("13", "省略日曆或同步基準", "calendar_benchmark_omission"),
    ("14", "相近年期冒充精確 RF", "risk_free_substitution"),
    ("15", "文件分數啟動 Paper", "gap_decision_boundary_violation"),
]


def _error_code(exc: BaseException) -> str | None:
    return getattr(exc, "code", None)


def _attacked_record(attack_id: str) -> dict[str, Any]:
    record = frozen_gap_closure_record()
    methodology = record["methodology"]
    if attack_id == "01":
        record["protocol_sha256"] = "0" * 64
    elif attack_id == "02":
        record["reference_commits"]["tst_wocker"] = "0" * 40
    elif attack_id == "03":
        record["candidate_route_ids"][0], record["candidate_route_ids"][1] = (
            record["candidate_route_ids"][1],
            record["candidate_route_ids"][0],
        )
    elif attack_id == "04":
        del record["routes"][0]["capabilities"][CAPABILITY_IDS[-1]]
    elif attack_id == "05":
        record["primary_sources"]["sp_dji_api"]["is_primary_owner_document"] = False
    elif attack_id == "06":
        methodology["product_identity_inferred"] = True
    elif attack_id == "07":
        methodology["license_inferred_from_public_access"] = True
    elif attack_id == "08":
        methodology["twenty_year_coverage_inferred_from_history_claim"] = True
    elif attack_id == "09":
        methodology["membership_announced_at_substituted_with_effective_at"] = True
    elif attack_id == "10":
        methodology["metadata_known_at_substituted_with_effective_range"] = True
    elif attack_id == "11":
        methodology["raw_open_substituted_with_adjusted_price"] = True
    elif attack_id == "12":
        methodology["missing_delist_economics_imputed_zero"] = True
    elif attack_id == "13":
        methodology["calendar_or_benchmark_execution_omitted"] = True
    elif attack_id == "14":
        methodology["risk_free_tenor_or_unit_substituted"] = True
    elif attack_id == "15":
        record["decision"]["paper_authorized"] = True
    else:  # pragma: no cover - fixed attack IDs only.
        raise ValueError(f"unknown attack: {attack_id}")
    return record


def _run_attack(attack_id: str, *, root: Path) -> str | None:
    try:
        validate_provider_gap_closure(_attacked_record(attack_id), root=root)
    except Exception as exc:  # noqa: BLE001 - fixed semantic attack harness.
        return _error_code(exc)
    return None


def run_provider_gap_closure_validation(root: str | Path) -> dict[str, Any]:
    root_path = Path(root).resolve()
    record = frozen_gap_closure_record()
    validation = validate_provider_gap_closure(record, root=root_path)
    routes = record["routes"]
    decision = record["decision"]

    controls = [
        {
            "id": "01",
            "label": "協議與父契約",
            "passed": validation["protocol_integrity"]["passed"],
            "detail": "第 21 輪協議、收據及第 18／20 輪 SHA-256 完整。",
        },
        {
            "id": "02",
            "label": "台股參考版本",
            "passed": record["reference_commits"]
            == frozen_gap_closure_record()["reference_commits"],
            "detail": "三個參考 repository 精確綁定，只轉移研究紀律。",
        },
        {
            "id": "03",
            "label": "五條候選路徑",
            "passed": [row["id"] for row in routes] == CANDIDATE_ROUTE_IDS,
            "detail": "沒有看過結果後加第六條路徑或調換次序。",
        },
        {
            "id": "04",
            "label": "十四項能力",
            "passed": all(list(row["capabilities"]) == CAPABILITY_IDS for row in routes),
            "detail": "每條路徑逐項回答同一正式合約。",
        },
        {
            "id": "05",
            "label": "一手文件",
            "passed": all(row["is_primary_owner_document"] for row in PRIMARY_SOURCES.values()),
            "detail": "只使用供應商／數據擁有者的官方頁面、指南及 API 文件。",
        },
        {
            "id": "06",
            "label": "產品身份",
            "passed": record["methodology"]["product_identity_inferred"] is False,
            "detail": "品牌宣傳沒有被推算成已存在的固定產品代碼。",
        },
        {
            "id": "07",
            "label": "研究授權",
            "passed": record["methodology"]["license_inferred_from_public_access"] is False,
            "detail": "公開可讀與使用者帳戶授權分開。",
        },
        {
            "id": "08",
            "label": "固定 20 年覆蓋",
            "passed": record["methodology"]["twenty_year_coverage_inferred_from_history_claim"]
            is False,
            "detail": "歷史年數宣傳不代替 2005-08-01 起逐列 manifest。",
        },
        {
            "id": "09",
            "label": "成分雙時鐘",
            "passed": record["methodology"]["membership_announced_at_substituted_with_effective_at"]
            is False,
            "detail": "AnnouncedAt 與 EffectiveAt 分開。",
        },
        {
            "id": "10",
            "label": "Metadata KnownAt",
            "passed": record["methodology"]["metadata_known_at_substituted_with_effective_range"]
            is False,
            "detail": "有效區間不冒充當時可知時間。",
        },
        {
            "id": "11",
            "label": "Raw 開市價",
            "passed": record["methodology"]["raw_open_substituted_with_adjusted_price"] is False,
            "detail": "調整價不冒充 t+1 raw open。",
        },
        {
            "id": "12",
            "label": "退出經濟",
            "passed": record["methodology"]["missing_delist_economics_imputed_zero"] is False,
            "detail": "缺失 DelRet／條款保留缺口，不補零。",
        },
        {
            "id": "13",
            "label": "日曆與同步基準",
            "passed": record["methodology"]["calendar_or_benchmark_execution_omitted"] is False,
            "detail": "XNYS、QQQ、SPY 與個股執行時鐘均保留。",
        },
        {
            "id": "14",
            "label": "精確 RF",
            "passed": record["methodology"]["risk_free_tenor_or_unit_substituted"] is False,
            "detail": "4 週、年率／252 或代理 ETF 均不替代正式 RF。",
        },
        {
            "id": "15",
            "label": "決策邊界",
            "passed": decision == frozen_gap_closure_record()["decision"],
            "detail": "正式 1/18、run 0、Paper 全現金、實金 US$0。",
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
    best = next(row for row in routes if row["id"] == decision["best_documented_route_id"])
    return {
        "schema_version": 1,
        "research_round": 21,
        "gap_version": record["gap_version"],
        "evidence_as_of": EVIDENCE_AS_OF,
        "status": "procurement_gap_matrix_complete_no_route_qualified",
        "protocol_integrity": validation["protocol_integrity"],
        "primary_sources": record["primary_sources"],
        "routes": routes,
        "route_summary": [
            {
                "id": row["id"],
                "name": row["name"],
                "role": row["role"],
                "status_counts": row["status_counts"],
                "documented_or_partial_count": row["documented_or_partial_count"],
                "qualified": False,
                "hard_gap_capabilities": row["hard_gap_capabilities"],
            }
            for row in routes
        ],
        "best_documented_route": {
            "id": best["id"],
            "name": best["name"],
            "explicit_count": best["status_counts"]["explicit_primary_documentation"],
            "partial_count": best["status_counts"]["partial_primary_documentation"],
            "hard_gap_count": len(best["hard_gap_capabilities"]),
        },
        "strongest_standalone_brand_candidate_id": decision[
            "strongest_standalone_brand_candidate_id"
        ],
        "required_capability_ids": CAPABILITY_IDS,
        "procurement_questions": PROCUREMENT_QUESTIONS,
        "controls": controls,
        "control_summary": control_summary,
        "attacks": attacks,
        "attack_summary": attack_summary,
        "qualified_route_count": 0,
        "actual_formal_readiness": decision["actual_formal_readiness"],
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
            "先以九條固定問題向 CRSP＋S&P DJI 複合路徑及 LSEG 單一品牌路徑"
            "索取授權 data dictionary 與細樣本；未過真實 20/20、extension 16/16、"
            "RF 完整及正式 18/18 前保持全現金。"
        ),
    }
