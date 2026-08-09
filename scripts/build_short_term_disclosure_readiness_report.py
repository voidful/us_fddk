from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from usfddk.disclosure_known_at import audit_disclosure_known_at_bundle

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "artifacts/short_term_disclosure_readiness.json"
SITE_DATA = ROOT / "site/data/short-term-disclosure-readiness.json"
REPORT = ROOT / "docs/SHORT_TERM_DISCLOSURE_READINESS_REPORT.md"


SOURCE_CATALOG: tuple[dict[str, str], ...] = (
    {
        "source_type": "congress_house_ptr",
        "label": "美國眾議院 PTR",
        "economic_semantics": "延遲申報的金額區間，可屬本人、配偶或受養人",
        "cannot_infer": "即時成交、精確數量、價格、當刻持倉或由議員親自落盤",
        "phase1_status": "blocked_by_written_exact_use_legal_clearance",
    },
    {
        "source_type": "congress_senate_ptr",
        "label": "美國參議院 PTR",
        "economic_semantics": "延遲申報的金額區間，可屬本人、配偶或受養人",
        "cannot_infer": "法定最後期限不是實際公開時間，亦不是無延遲交易訊號",
        "phase1_status": "blocked_by_written_exact_use_legal_clearance",
    },
    {
        "source_type": "sec_form_4",
        "label": "SEC Form 4",
        "economic_semantics": "Section 16 董事、高級人員及逾 10% 股東的持股變動",
        "cannot_infer": "未分辨交易 code、註腳、修訂及直接／間接持有前，不得當成公開市場買沽",
        "phase1_status": "input_not_observed",
    },
    {
        "source_type": "sec_schedule_13d",
        "label": "SEC Schedule 13D",
        "economic_semantics": "逾 5% 實益擁有權及控制意圖的披露快照",
        "cannot_infer": "逐筆成交、精確建倉日或建倉成本",
        "phase1_status": "input_not_observed",
    },
    {
        "source_type": "sec_schedule_13g",
        "label": "SEC Schedule 13G",
        "economic_semantics": "依申報人類型及門檻呈列的實益擁有權快照",
        "cannot_infer": "單一延遲、看好方向，或由 amendment 差額直接推導買沽",
        "phase1_status": "input_not_observed",
    },
    {
        "source_type": "sec_form_13f",
        "label": "SEC Form 13F",
        "economic_semantics": "機構投資經理的季度末持倉快照，通常可延遲約 45 日申報",
        "cannot_infer": "交易日、成交價、企業家個人交易，或由兩季差額直接推導買沽",
        "phase1_status": "input_not_observed",
    },
)


GATE_LABELS = {
    "01_protocol_schema_receipt_integrity": "協議、schema 與凍結收據一致",
    "02_official_source_semantics_pinned": "六類官方來源及不可推論事項已固定",
    "03_congress_exact_use_legal_clearance": "Congress 精確用途有有效書面法律准許",
    "04_source_terms_and_automation_clearance": "來源條款、自動存取、保存及再發布已批准",
    "05_sec_fair_access_client_verified": "SEC Fair Access 客戶端與停止控制已驗證",
    "06_private_quarantine_verified": "原始文件與人物資料私有隔離已實測",
    "07_closed_manifest_admitted": "真實 manifest 通過封閉 schema 及語意檢查",
    "08_source_request_receipts_complete": "來源 request 收據可完整對數",
    "09_stable_document_version_ids": "文件與修訂版本 ID 穩定可追溯",
    "10_eight_timestamps_complete_or_reasoned": "八個時間 key 齊全或保留缺失原因",
    "11_public_at_evidence_verified": "public_at 有官方或獨立不可回填證據",
    "12_known_at_derivation_verified": "known_at 與 basis 符合三層固定規則",
    "13_append_only_revision_chain_verified": "原版、修訂與刪除雜湊鏈不可回填",
    "14_point_in_time_security_mapping_verified": "當時證券映射可重播且歧義失敗關閉",
    "15_source_specific_semantics_verified": "六類來源的經濟語意逐列保留",
    "16_xnys_decision_entry_clock_verified": "known 後首個收市及再下一開市時鐘已驗證",
    "17_coverage_lag_missingness_audited": "逐來源及年份覆蓋、延遲與缺失已對數",
    "18_public_sanitizer_verified": "公開 sanitizer、最小組別及人工複核已通過",
    "19_independent_synthetic_attacks_passed": "獨立單一錯誤攻擊命中精確拒收碼",
    "20_authorized_real_sample_accepted": "合法真實小樣本逐列重播並獨立接受",
}


def _public_summary(result: dict[str, Any]) -> dict[str, Any]:
    source_counts = result["sources"]
    document_count = sum(source_counts["document_type_counts"].values())
    event_count = sum(source_counts["event_type_counts"].values())
    legal_gate = result["gates"]["03_congress_exact_use_legal_clearance"]
    return {
        "schema_version": 1,
        "research_round": result["research_round"],
        "phase": result["phase"],
        "status": result["status"],
        "input": {
            "configured": result["bundle"]["configured"],
            "repository_external_required": True,
            "raw_rows_published": 0,
            "failure_code": result["bundle"]["failure_code"],
        },
        "source_catalog": list(SOURCE_CATALOG),
        "coverage": {
            "source_types_required": len(SOURCE_CATALOG),
            "source_types_observed": len(source_counts["present"]),
            "documents_observed": document_count,
            "events_observed": event_count,
            "twenty_year_coverage_claimed": False,
            "twenty_year_coverage_validated": False,
            "per_source_year_denominators_audited": result["gates"][
                "17_coverage_lag_missingness_audited"
            ]["passed"],
        },
        "known_at": {
            "basis_order": [
                "official_public_timestamp",
                "independent_archived_first_seen",
                "local_first_observed_fallback",
            ],
            "prohibited_proxies": [
                "event_at",
                "legal_due_date",
                "filed_at",
                "accepted_at",
                "nightly_index_date",
            ],
            "documents_validated": result["known_at"]["documents_validated"],
            "events_validated": result["known_at"]["events_validated"],
            "historical_backfill_allowed": False,
            "final_revision_substitution_allowed": False,
        },
        "lag": {
            "definition": "known_at_minus_event_at",
            "events_measured": result["lag"].get("events_with_valid_lag", 0),
            "source_year_missingness_audited": result["gates"][
                "17_coverage_lag_missingness_audited"
            ]["passed"],
            "decision_at_rule": "first_official_xnys_close_strictly_after_known_at",
            "trade_at_rule": "next_official_xnys_open_after_decision_at",
            "events_with_valid_trade_clock": result["lag"].get(
                "events_with_valid_next_session", 0
            ),
            "same_or_prior_session_execution_allowed": False,
        },
        "legal": {
            "congress_exact_use_written_clearance": legal_gate["passed"],
            "authorized_for_local_research": result["legal"][
                "authorized_for_local_research"
            ],
            "raw_redistribution_allowed": result["legal"][
                "raw_redistribution_allowed"
            ],
            "official_public_sources_only": result["legal"][
                "official_public_sources_only"
            ],
            "legal_advice_provided": False,
        },
        "readiness": result["readiness"],
        "gates": result["gates"],
        "controls": {
            "raw_rows_generated": result["controls"]["synthetic_raw_rows_generated"],
            "raw_rows_published": result["controls"]["raw_rows_published"],
            "actor_names_published": result["controls"]["actor_names_published"],
            "security_identifiers_published": 0,
        },
        "attacks": result["attacks"],
        "selection": {
            "strategy_defined": False,
            "dynamic_selection_enabled": False,
            "published_selection_count": 0,
        },
        "decision": {
            "can_promote": False,
            "formal_backtest_authorized": False,
            "strategy_runs": 0,
            "today": "今天不下單",
        },
        "paper": result["paper"],
        "real_money_usd": result["real_money_usd"],
        "next_action": result["next_action"],
        "disclaimer": result["disclaimer"],
    }


def _gate_table(summary: dict[str, Any]) -> str:
    rows = [
        "| # | 數據就緒門檻 | 結果 |",
        "|---|---|---|",
    ]
    for gate_id, gate in summary["gates"].items():
        rows.append(
            f"| {gate_id[:2]} | {GATE_LABELS[gate_id]} | "
            f"{'**通過**' if gate['passed'] else '未通過'} |"
        )
    return "\n".join(rows)


def _source_table(summary: dict[str, Any]) -> str:
    rows = [
        "| 官方來源類型 | 可知經濟語意 | 不可推論 | Phase 1 |",
        "|---|---|---|---|",
    ]
    for source in summary["source_catalog"]:
        status = (
            "法律／授權門檻未通過"
            if source["phase1_status"].startswith("blocked_by")
            else "未收到合法真實輸入"
        )
        rows.append(
            f"| `{source['source_type']}`（{source['label']}） | "
            f"{source['economic_semantics']} | {source['cannot_infer']} | {status} |"
        )
    return "\n".join(rows)


def _report(summary: dict[str, Any]) -> str:
    readiness = summary["readiness"]
    coverage = summary["coverage"]
    return f"""# 美股短線公開披露 Phase 1：known-at 數據就緒報告

## 結論先行

Phase 1 只把美國議員與企業持股披露的官方來源、經濟語意、公開可得時間及
合規邊界在任何數據擷取或策略設計前固定。實際 readiness 只通過
**{readiness['passed']}/{readiness['total']}**：協議／schema／收據完整性，以及六類官方來源語意已固定；
其餘門檻全部失敗關閉。

目前沒有配置外部原始包，觀察來源 **{coverage['source_types_observed']}/{coverage['source_types_required']}**、
文件 0、事件 0，不聲稱擁有 20 年完整 point-in-time 覆蓋。Congress 披露的精確用途
尚未獲書面法律／授權判定，因此不擷取、不選股、不回測。策略未定義，
正式策略運行 **0 次**，動態選擇停用；Paper Trading（模擬交易）維持**全現金**、持倉 0、不可
回填，實金動作 **US$0**。**今天不下單。**

## 六類來源：可看見不等於可跟單

{_source_table(summary)}

「企業家」不是 SEC 申報身分。只能按法規中可驗證的董事、高級人員、逾 10% 股東、
實益擁有人及機構投資經理角色處理；不會根據知名度、創辦人故事或媒體稱呼自行建立
「高勝率人物」權重。

## known-at、延遲與成交時鐘

`known_at` 只可依次使用：可綁定內容雜湊的官方 `public_at`、獨立且不可回填的
archived first-seen，或本系統第一次觀察到同一內容的 `first_observed_at`。
`event_at`、法定最後期限、`filed_at`、SEC `accepted_at` 及 nightly index 均不能單獨
冒充當時已知。

研究延遲固定為 `known_at - event_at`；兩個時間沒有可靠精度時只能標記未解，不以 0、
中位數或法定期限補值。策略日後若存在，`decision_at` 必須是嚴格晚於 `known_at`
的第一個官方 XNYS 收市；`trade_at` 再取其後下一個官方 XNYS 開市。休市、提早收市、
收市同一 timestamp 才公開、修訂版及過期申報都必須逐版重播，不得回填。

Phase 1 觀察的延遲事件是 **{summary['lag']['events_measured']}**，通過正式成交時鐘的事件是
**{summary['lag']['events_with_valid_trade_clock']}**。這些零值代表尚無真實輸入，不是零延遲或完整覆蓋。

## Congress 法律／授權硬門檻

5 U.S.C. § 13107 及 House／Senate 指引對使用財務披露報告作商業用途等情況有禁止或限制。
公開可看不等於可作任何投資、網站、Paper 或未來收費用途。在合資格法律顧問或有權
機構就本專案精確用途出具有效書面准許，並固定存取、保存、再發布及複核到期日前，
兩個 Congress 來源都不收集任何一列。本報告不提供法律意見。

## 二十項數據就緒門檻

{_gate_table(summary)}

2/20 只表示協議與來源語意事前凍結，不是數據完整性、策略質素或預測能力證明。
機器對數中的失敗攻擊是測試契約，不是真實數據證據；本次 runtime 沒有生成合成原始列，亦沒有
將測試 fixture 冒充市場樣本。

## 公開輸出邊界與下一步

這份公開收據只有來源家族的就緒、known-at／延遲規則、合規狀態及對數摘要；不列人物、
股票代號、CUSIP、CIK、accession、文件 URL、原始列、精確小組別、最新標的或逐文件買沽賬本。

下一步只能是先取得書面法律／授權判定、合規自動存取客戶端、私有隔離與真實細樣本，再原樣
重跑 20 道門檻。20/20 也只准日後另行凍結策略、baseline、成本、統計 family 及停止規則，
不自動產生選股、回測、Paper 或實金授權。

## 參考

- [known-at 數據準備度協議](SHORT_TERM_DISCLOSURE_KNOWN_AT_PROTOCOL.md)
- [美國官方法典 5 U.S.C. § 13107](https://uscode.house.gov/view.xhtml?edition=prelim&num=0&req=granuleid%3AUSC-prelim-title5-section13107)
- [SEC Accessing EDGAR Data](https://www.sec.gov/search-filings/edgar-search-assistance/accessing-edgar-data)
- [SEC Form 13F FAQ](https://www.sec.gov/rules-regulations/staff-guidance/division-investment-management-frequently-asked-questions/frequently-asked-questions-about-form-13f)

本報告只作研究及專業資訊參考，不構成投資或法律建議，不保證盈利。
"""


def main() -> int:
    result = audit_disclosure_known_at_bundle(None, root=ROOT)
    summary = _public_summary(result)
    payload = json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ARTIFACT.parent.mkdir(parents=True, exist_ok=True)
    SITE_DATA.parent.mkdir(parents=True, exist_ok=True)
    ARTIFACT.write_text(payload, encoding="utf-8")
    SITE_DATA.write_text(payload, encoding="utf-8")
    REPORT.write_text(_report(summary), encoding="utf-8")
    print(
        json.dumps(
            {
                "status": summary["status"],
                "readiness": summary["readiness"],
                "dynamic_selection_enabled": False,
                "strategy_runs": 0,
                "paper": summary["paper"]["status"],
                "real_money_usd": 0,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
