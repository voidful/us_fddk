from __future__ import annotations

import hashlib
import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

PROTOCOL_SHA256 = "215f826a2488afe7931662c25c5ba407ebfc0a7813e3ddc749b46b98c98eb3db"
DOMAIN_REPAIR_PROTOCOL_SHA256 = (
    "65ef305af5facc2733731ed028fd3bddfcfb50d3019a0ce2bccf0b3d053c06f1"
)
EXPECTED_PROVIDER_IDS = (
    "crsp_wrds",
    "norgate_data",
    "nasdaq_data_link_sharadar",
    "polygon_io_stocks",
)
STATUS_VALUES = {
    "documented",
    "partial",
    "not_documented",
    "unresolved_login_required",
    "not_applicable_until_import",
}
GATE_KEYS = (
    "01_authorized_provider",
    "02_manifest_and_file_set",
    "03_hash_and_row_receipts",
    "04_preregistration_order",
    "05_security_master",
    "06_identifier_history",
    "07_membership_availability",
    "08_membership_intervals",
    "09_fixed_20_year_calendar",
    "10_daily_member_count",
    "11_member_price_coverage",
    "12_market_data_validity",
    "13_raw_price_policy",
    "14_corporate_actions",
    "15_outcome_coverage",
    "16_permanent_exit_economics",
    "17_no_post_exit_prices",
    "18_point_in_time_classifications",
    "19_share_class_dedup_capability",
    "20_execution_clock",
)

IMPORT_ONLY_DETAIL = {
    "01_authorized_provider": "須由使用者以實際合約證明本地研究授權；公開產品頁不能代替。",
    "02_manifest_and_file_set": "只有本地轉換包才能核對 manifest 及八份固定檔案。",
    "03_hash_and_row_receipts": "只有下載後才能計算原始檔 SHA-256 及列數。",
    "04_preregistration_order": "專案凍結順序已通過 1/1；供應商首次匯入時間仍待真實包。",
    "10_daily_member_count": "須以完整 membership intervals 逐日重建後核對 495–510 隻。",
    "11_member_price_coverage": "須以完整在籍日面板核對至少 99.5% 價格／停牌覆蓋。",
    "17_no_post_exit_prices": "須逐證券核對退出日後是否仍有幽靈價格。",
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _parse_timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _gate(status: str, detail: str, evidence: tuple[str, ...] = ()) -> dict[str, Any]:
    if status not in STATUS_VALUES:
        raise ValueError(f"不支援的來源狀態：{status}")
    return {"status": status, "detail": detail, "evidence_ids": list(evidence)}


def _base_gate_map() -> dict[str, dict[str, Any]]:
    return {
        key: (
            _gate("not_applicable_until_import", IMPORT_ONLY_DETAIL[key])
            if key in IMPORT_ONLY_DETAIL
            else _gate("not_documented", "待按凍結官方文件逐項映射。")
        )
        for key in GATE_KEYS
    }


def _crsp_gates() -> dict[str, dict[str, Any]]:
    stock = "crsp_stock_guide_202607"
    indexes = "crsp_historical_indexes_guide_202607"
    permno = "crsp_permno_page"
    gates = _base_gate_map()
    gates.update(
        {
            "05_security_master": _gate(
                "documented",
                "PERMNO／PERMCO 是證券及公司永久 ID；security/issuer history 另有日期區間。",
                (stock, permno),
            ),
            "06_identifier_history": _gate(
                "documented",
                "SecurityInfoHist 明列 ticker、trading symbol、CUSIP、primary exchange 及生效區間。",
                (stock,),
            ),
            "07_membership_availability": _gate(
                "not_documented",
                "官方 guide 有 membership 起訖日，但本輪沒有找到 S&P 500 成分公布時間欄位。",
                (stock, indexes),
            ),
            "08_membership_intervals": _gate(
                "documented",
                "StkIndMembership 提供 PERMNO、INDNO、MbrStartDt 及 MbrEndDt。",
                (stock, indexes),
            ),
            "09_fixed_20_year_calendar": _gate(
                "documented",
                "日線與 S&P 500 系列覆蓋遠早於 2006；DlyOpen 自 1992 年後可用。",
                (stock, indexes),
            ),
            "12_market_data_validity": _gate(
                "documented",
                "StkDlySecurityData 明列 raw open/high/low/close、volume、total return 及缺值旗號。",
                (stock,),
            ),
            "13_raw_price_policy": _gate(
                "documented",
                "raw 日價、分派及 cumulative adjustment factors 分表提供，可分開過濾與回報用途。",
                (stock,),
            ),
            "14_corporate_actions": _gate(
                "documented",
                "StkDistributions 有除淨、公布、登記、派付、金額、價格／股份因子及接收證券 ID。",
                (stock,),
            ),
            "15_outcome_coverage": _gate(
                "partial",
                "membership、active status、delisting 及後續價格可重建多數結果，但未有一張逐段 outcome 表。",
                (stock,),
            ),
            "16_permanent_exit_economics": _gate(
                "partial",
                "DelRet、delisting amount／dividend／successor ID 存在；DelRetMissType 亦明示部分退出可能無法估值。",
                (stock,),
            ),
            "18_point_in_time_classifications": _gate(
                "documented",
                "歷史 security/issuer information 區間含 SIC、NAICS、ICB 及 UES industry。",
                (stock,),
            ),
            "19_share_class_dedup_capability": _gate(
                "documented",
                "PERMCO 可聚合同公司證券，另有 ShareClass、ShareType、shares 及日成交量。",
                (stock,),
            ),
            "20_execution_clock": _gate(
                "documented",
                "DlyCalDt、DlyOpen 及日收市／回報欄位足以實作 t 收市訊號、t+1 開市成交。",
                (stock,),
            ),
        }
    )
    return gates


def _norgate_gates() -> dict[str, dict[str, Any]]:
    content = "norgate_content_tables"
    faq = "norgate_data_faq"
    gates = _base_gate_map()
    gates.update(
        {
            "05_security_master": _gate(
                "documented",
                "assetid 在證券整個生命週期保持不變，另有證券類型、所在地及貨幣 metadata。",
                (faq, content),
            ),
            "06_identifier_history": _gate(
                "partial",
                "assetid 可保持連續，但官方明示只提供現時／最後 ticker，亦沒有精確歷史主上市地。",
                (faq,),
            ),
            "07_membership_availability": _gate(
                "not_documented",
                "官方 FAQ 明示不提供歷史指數成分公布日期。",
                (faq,),
            ),
            "08_membership_intervals": _gate(
                "documented",
                "Platinum／Diamond 可逐證券逐日查 S&P 500 membership，歷史由 1957 年開始。",
                (content, faq),
            ),
            "09_fixed_20_year_calendar": _gate(
                "documented",
                "產品提供 20 年歷史方案，S&P 500 成分及主要交易所標記覆蓋更長。",
                (content, faq),
            ),
            "12_market_data_validity": _gate(
                "documented",
                "官方定義日線 open／close，Python 路徑提供 OHLC、volume、turnover 及無 padding 選項。",
                (content, faq),
            ),
            "13_raw_price_policy": _gate(
                "documented",
                "價格調整可選 none／capital／total return，並另有 unadjusted close。",
                (content, faq),
            ),
            "14_corporate_actions": _gate(
                "partial",
                "可取得股息及 capital-event 指示，但 FAQ 明示不直接提供拆股及公司行動事件明細。",
                (content, faq),
            ),
            "15_outcome_coverage": _gate(
                "partial",
                "有 delisted pool、last quoted date 及 membership，但沒有逐 membership outcome 賬本。",
                (content, faq),
            ),
            "16_permanent_exit_economics": _gate(
                "not_documented",
                "官方 FAQ 明示不提供 delisting return 或收購／合併代價，只建議最後交易 bar 近似。",
                (faq,),
            ),
            "18_point_in_time_classifications": _gate(
                "not_documented",
                "頁面列出 classification metadata，但沒有證明歷史逐期 classification 區間。",
                (content, faq),
            ),
            "19_share_class_dedup_capability": _gate(
                "partial",
                "assetid 及 security subtype 可分辨證券，但未見永久 company ID／同公司股份類別關聯表。",
                (content, faq),
            ),
            "20_execution_clock": _gate(
                "documented",
                "未填補日線 OHLC 及逐日 membership 足以實作 D+1 開市成交；仍須本地樣本驗證。",
                (content, faq),
            ),
        }
    )
    return gates


def _sharadar_gates() -> dict[str, dict[str, Any]]:
    sep = "sharadar_sep_metadata"
    tickers = "sharadar_tickers_metadata"
    actions = "sharadar_actions_metadata"
    shell = "sharadar_product_documentation"
    gates = _base_gate_map()
    gates.update(
        {
            "05_security_master": _gate(
                "partial",
                "TICKERS metadata 顯示 permaticker 主鍵／filter，但公開 metadata 隱藏完整欄位及公司層 ID。",
                (tickers,),
            ),
            "06_identifier_history": _gate(
                "unresolved_login_required",
                "TICKERS 原始列及完整欄位需有效 API key，未能核對 ticker 生效區間。",
                (tickers, shell),
            ),
            "07_membership_availability": _gate(
                "not_documented",
                "本輪官方公開文件未找到 S&P 500 成分公布時間。",
                (shell,),
            ),
            "08_membership_intervals": _gate(
                "not_documented",
                "SEP／TICKERS／ACTIONS 公開 metadata 未列歷史 S&P 500 membership 表。",
                (sep, tickers, actions),
            ),
            "09_fixed_20_year_calendar": _gate(
                "unresolved_login_required",
                "SEP table 存在，但公開 metadata 沒有可驗證的完整日線起訖與 calendar 欄位。",
                (sep, shell),
            ),
            "12_market_data_validity": _gate(
                "unresolved_login_required",
                "SEP 只公開 ticker/date 主鍵；OHLCV、缺值及狀態欄位需登入後核對。",
                (sep,),
            ),
            "13_raw_price_policy": _gate(
                "unresolved_login_required",
                "未登入官方頁未揭示 raw 與調整欄位的精確用途。",
                (sep, shell),
            ),
            "14_corporate_actions": _gate(
                "unresolved_login_required",
                "ACTIONS table 名稱及 filters 可見，但事件欄位與金額／比率仍隱藏。",
                (actions,),
            ),
            "15_outcome_coverage": _gate(
                "unresolved_login_required",
                "公開 metadata 未證明每段 membership 有持續、移除、收購或退市結果。",
                (tickers, actions),
            ),
            "16_permanent_exit_economics": _gate(
                "unresolved_login_required",
                "公開欄位未證明有 delisting return 或現金／換股代價。",
                (actions, shell),
            ),
            "18_point_in_time_classifications": _gate(
                "unresolved_login_required",
                "公開欄位未證明 classification 的生效及可知時間。",
                (tickers, shell),
            ),
            "19_share_class_dedup_capability": _gate(
                "unresolved_login_required",
                "permaticker 可見，但公司／股份類別關係需完整 TICKERS schema。",
                (tickers,),
            ),
            "20_execution_clock": _gate(
                "unresolved_login_required",
                "SEP 的開市價及正式 trading calendar 欄位未由公開 metadata 證實。",
                (sep,),
            ),
        }
    )
    return gates


def _polygon_gates() -> dict[str, dict[str, Any]]:
    day = "polygon_day_aggregates_redirect"
    tickers = "polygon_tickers_redirect"
    splits = "polygon_splits_redirect"
    dividends = "massive_dividends_after_repair"
    events = "massive_ticker_events_after_repair"
    overview = "massive_ticker_overview_after_repair"
    gates = _base_gate_map()
    gates.update(
        {
            "05_security_master": _gate(
                "partial",
                "Composite／Share Class FIGI、CIK、類型及 active 狀態存在，但未證明全期永久 company/security master。",
                (tickers, overview),
            ),
            "06_identifier_history": _gate(
                "partial",
                "實驗性 ticker-events 只支持 ticker_change；可用 FIGI 連接，但完整 exchange/CUSIP 區間未證實。",
                (events, overview),
            ),
            "07_membership_availability": _gate(
                "not_documented",
                "官方 Stocks 文件未找到 S&P 500 成分公布時間。",
                (tickers, overview),
            ),
            "08_membership_intervals": _gate(
                "not_documented",
                "官方 Stocks 文件未找到歷史 S&P 500 membership intervals。",
                (tickers, overview),
            ),
            "09_fixed_20_year_calendar": _gate(
                "documented",
                "Day Aggregates 官方歷史由 2003-09-10 起，覆蓋固定 2006–2026 主期。",
                (day,),
            ),
            "12_market_data_validity": _gate(
                "documented",
                "日檔提供全美股每日 OHLCV；完整性及停牌仍須匯入抽查。",
                (day,),
            ),
            "13_raw_price_policy": _gate(
                "documented",
                "官方說明 Aggregates 可取 adjusted／unadjusted views，股息及拆股有獨立因子。",
                (day, splits, dividends),
            ),
            "14_corporate_actions": _gate(
                "partial",
                "股息及拆股有事件、日期、金額／比率；ticker-events 只含改名，未見完整 merger/spinoff ledger。",
                (splits, dividends, events),
            ),
            "15_outcome_coverage": _gate(
                "partial",
                "active=false、delisted_utc 及日價可辨認部分退出，但沒有逐 membership outcome 表。",
                (tickers, overview),
            ),
            "16_permanent_exit_economics": _gate(
                "not_documented",
                "官方文件只有退市日期，未找到 delisting return、現金收購或換股代價。",
                (tickers, overview),
            ),
            "18_point_in_time_classifications": _gate(
                "partial",
                "Ticker Overview 可帶 date 並返回 SIC，但申報期／提交時間語義仍須逐列驗證。",
                (overview,),
            ),
            "19_share_class_dedup_capability": _gate(
                "partial",
                "Share Class FIGI、ticker root/suffix 及 weighted shares 可用，但公司層永久關聯未完整證實。",
                (overview,),
            ),
            "20_execution_clock": _gate(
                "documented",
                "每日 raw open 與日期面板可實作 t 收市／t+1 開市；仍須另建正式交易日表。",
                (day,),
            ),
        }
    )
    return gates


def _provider_specs() -> list[dict[str, Any]]:
    return [
        {
            "id": "crsp_wrds",
            "name": "CRSP／WRDS",
            "role": "最接近完整賬本的首個正式查詢對象",
            "gates": _crsp_gates(),
            "hard_blockers": [
                "本地授權及實際 data cut 未提供",
                "S&P 500 成分公布時間欄位未見官方文件",
                "DelRetMissType 代表部分退市回報可能仍缺失",
                "完整 20 年樣本尚未跑 20 道逐列稽核",
            ],
            "next_action": "先要求 data dictionary、20 年細樣本及授權條款；特別書面確認 announcement timestamp 與缺失 delisting return 處理。",
            "first_enquiry": True,
        },
        {
            "id": "norgate_data",
            "name": "Norgate Data",
            "role": "歷史成分／日價補充來源，不能單獨通過",
            "gates": _norgate_gates(),
            "hard_blockers": [
                "官方明示沒有成分公布日期",
                "官方明示沒有舊 ticker 及精確歷史主上市地",
                "公司行動只有調整／指示，沒有完整事件明細",
                "官方明示沒有 delisting return 或收購代價",
            ],
            "next_action": "除非另有合法退出經濟賬本及公布時間來源，否則不作正式主入口。",
            "first_enquiry": False,
        },
        {
            "id": "nasdaq_data_link_sharadar",
            "name": "Nasdaq Data Link Sharadar",
            "role": "公開 schema 不足，需授權後再判斷",
            "gates": _sharadar_gates(),
            "hard_blockers": [
                "SEP／TICKERS／ACTIONS 完整欄位需有效 API key",
                "歷史 S&P 500 membership 未在公開文件證實",
                "成分公布時間、退出經濟回報及歷史分類未證實",
                "本地授權樣本不存在",
            ],
            "next_action": "只有已持有合法訂閱時才取 schema／小樣本；不為提高分數而先購買。",
            "first_enquiry": False,
        },
        {
            "id": "polygon_io_stocks",
            "name": "Polygon.io／Massive Stocks",
            "role": "日價、reference 及成本補充來源，不能單獨通過",
            "gates": _polygon_gates(),
            "hard_blockers": [
                "官方 Stocks 文件未見歷史 S&P 500 membership",
                "未見成分公布時間",
                "未見完整 merger／spinoff／security outcome 賬本",
                "只有退市日期，未見退出經濟回報",
            ],
            "next_action": "可在將來用於 OHLCV／買賣差價核對，但不得取代歷史成分及退出賬本。",
            "first_enquiry": False,
        },
    ]


def _validate_receipts(root: Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    protocol_receipt = _load_json(
        root / "artifacts/short_term_provider_qualification_protocol_receipt.json"
    )
    document_receipt = _load_json(
        root / "artifacts/short_term_provider_document_receipt.json"
    )
    repair_receipt = _load_json(
        root / "artifacts/short_term_provider_source_domain_repair_receipt.json"
    )
    if _sha256(root / protocol_receipt["protocol"]["path"]) != PROTOCOL_SHA256:
        raise ValueError("第十一輪原始協議雜湊不符")
    if protocol_receipt["protocol"]["sha256"] != PROTOCOL_SHA256:
        raise ValueError("第十一輪凍結收據協議雜湊不符")
    if (
        _sha256(root / repair_receipt["repair_protocol"]["path"])
        != DOMAIN_REPAIR_PROTOCOL_SHA256
    ):
        raise ValueError("來源 domain repair 協議雜湊不符")
    if repair_receipt["repair_protocol"]["sha256"] != DOMAIN_REPAIR_PROTOCOL_SHA256:
        raise ValueError("來源 domain repair 收據雜湊不符")
    frozen_at = _parse_timestamp(protocol_receipt["frozen_at"])
    reviewed_at = _parse_timestamp(document_receipt["first_retrieved_at"])
    repaired_at = _parse_timestamp(repair_receipt["frozen_at"])
    if not frozen_at < reviewed_at < repaired_at:
        raise ValueError("原始凍結、首次文件閱讀及 domain repair 時序不符")
    if repair_receipt["independent_first_seen_evidence"] is not False:
        raise ValueError("domain repair 不得標成獨立首次證據")
    if repair_receipt["provider_set_changed"] is not False:
        raise ValueError("domain repair 不得改變供應商集合")
    if repair_receipt["twenty_gate_mapping_changed"] is not False:
        raise ValueError("domain repair 不得改變 20 道映射")

    source_ids: set[str] = set()
    for source in document_receipt["sources"]:
        source_id = source["id"]
        if source_id in source_ids:
            raise ValueError(f"重複來源 ID：{source_id}")
        source_ids.add(source_id)
        if source["http_status"] != 200:
            raise ValueError(f"官方來源未成功取得：{source_id}")
        if len(source["sha256"]) != 64 or source["bytes"] <= 0:
            raise ValueError(f"官方來源收據不完整：{source_id}")
        if not source["accepted_under_domain_repair"]:
            raise ValueError(f"來源不在 repair 範圍：{source_id}")
        final_domain = urlparse(source["final_url"]).hostname
        allowed_domains = {
            "indexes.morningstar.com",
            "norgatedata.com",
            "data.nasdaq.com",
            "massive.com",
        }
        if final_domain not in allowed_domains:
            raise ValueError(f"來源 final domain 不在固定清單：{source_id}")
    return protocol_receipt, document_receipt, repair_receipt


def build_provider_qualification(root: str | Path) -> dict[str, Any]:
    root_path = Path(root)
    protocol_receipt, document_receipt, repair_receipt = _validate_receipts(root_path)
    readiness = _load_json(root_path / "artifacts/short_term_point_in_time_readiness.json")
    if tuple(readiness["gates"]) != GATE_KEYS:
        raise ValueError("真實 point-in-time 閘門集合已漂移")
    if readiness["gate_summary"] != {"passed": 1, "total": 20, "all_passed": False}:
        raise ValueError("第十一輪不得改寫真實 point-in-time 1/20 狀態")

    source_ids = {item["id"] for item in document_receipt["sources"]}
    providers: list[dict[str, Any]] = []
    for spec in _provider_specs():
        if tuple(spec["gates"]) != GATE_KEYS:
            raise ValueError(f"{spec['id']} 的 20 道映射不完整或次序漂移")
        evidence_ids = {
            evidence_id
            for gate in spec["gates"].values()
            for evidence_id in gate["evidence_ids"]
        }
        missing_evidence = evidence_ids - source_ids
        if missing_evidence:
            raise ValueError(f"{spec['id']} 引用未知來源：{sorted(missing_evidence)}")
        counts = Counter(gate["status"] for gate in spec["gates"].values())
        providers.append(
            {
                **spec,
                "status_counts": {
                    status: counts.get(status, 0)
                    for status in (
                        "documented",
                        "partial",
                        "not_documented",
                        "unresolved_login_required",
                        "not_applicable_until_import",
                    )
                },
                "document_supported_count": counts.get("documented", 0),
                "partial_count": counts.get("partial", 0),
                "locally_verified": False,
                "contract_passed": False,
                "procurement_minimum_passed": False,
                "formal_backtest_authorized": False,
                "paper_authorized": False,
            }
        )

    if tuple(provider["id"] for provider in providers) != EXPECTED_PROVIDER_IDS:
        raise ValueError("供應商集合與事前凍結不符")

    return {
        "schema_version": 1,
        "research_round": 11,
        "status": "no_single_provider_preflight_qualified",
        "headline": "四條來源均未能單獨通過；CRSP／WRDS 只適合先索取正式樣本",
        "evidence_as_of": document_receipt["evidence_as_of"],
        "preregistration": {
            "original_protocol_frozen_before_document_review": True,
            "original_protocol_commit": document_receipt["protocol_commit"],
            "original_protocol_sha256": PROTOCOL_SHA256,
            "original_domain_scope_failed": True,
            "domain_repair_frozen_after_redirect_inspection": True,
            "domain_repair_sha256": DOMAIN_REPAIR_PROTOCOL_SHA256,
            "independent_first_seen_evidence": False,
            "provider_set_changed": False,
            "twenty_gate_mapping_changed": False,
            "strategy_rule_changed": False,
        },
        "actual_point_in_time_readiness": {
            "passed": readiness["gate_summary"]["passed"],
            "total": readiness["gate_summary"]["total"],
            "all_passed": readiness["gate_summary"]["all_passed"],
            "status": readiness["status"],
        },
        "providers": providers,
        "first_enquiry": {
            "provider_id": "crsp_wrds",
            "qualified": False,
            "purpose": "只要求 data dictionary、細樣本及授權條款，不購買、不回測",
            "must_resolve": [
                "S&P 500 成分 announcement timestamp",
                "缺失 delisting return 的比例及可對數代價",
                "2006–2026 raw open／OHLCV／停牌完整度",
                "歷史分類及股份類別在當時可知時間",
                "本地研究授權與禁止原始列公開再分發",
            ],
        },
        "hard_findings": [
            "CRSP／WRDS 文件覆蓋最完整，但公告時間未見欄位，退市回報亦可能缺失。",
            "Norgate 官方明示沒有公布日、舊代號、公司行動明細及退市回報，不能單獨通過。",
            "Sharadar 公開 metadata 隱藏完整欄位，亦未證明歷史 S&P 500 membership。",
            "Polygon.io 已遷移至 Massive；日價及 reference 可補充，但沒有歷史成分或退出經濟賬本。",
        ],
        "formal_stock_backtest_authorized": False,
        "formal_stock_backtest_completed": False,
        "paper": {
            "authorized": False,
            "state": "all_cash",
            "backfilled_trades": 0,
            "positions": [],
        },
        "real_money_action_usd": 0,
        "next_action": "向 CRSP／WRDS 索取不含敏感原始列的 schema、20 年細樣本及授權條款；五個缺口全部解決後才匯入 20 道稽核。",
        "disclaimer": "文件能力不等於本地數據通過，不構成供應商背書、投資建議或盈利保證。",
        "receipt_integrity": {
            "protocol_status": protocol_receipt["status"],
            "document_source_count": len(document_receipt["sources"]),
            "domain_repair_status": repair_receipt["status"],
        },
    }
