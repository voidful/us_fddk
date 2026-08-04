from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any

GAP_VERSION = "round21-provider-gap-closure-v1"
PROBE_VERSION = "round21-provider-source-probe-v1"
EVIDENCE_AS_OF = "2026-08-04"
PROTOCOL_PATH = "docs/SHORT_TERM_PROVIDER_GAP_CLOSURE_PROTOCOL.md"
PROTOCOL_RECEIPT_PATH = "artifacts/short_term_provider_gap_closure_protocol_receipt.json"
PROTOCOL_SHA256 = "ec97b748d9abc8f3ef0d707dde923f27c3796e7c1f7bdceae68c3eaaa4339655"
PROTOCOL_RECEIPT_SHA256 = "a931d201d6b996348c85c4360fb172f1bb3b5dfb722e58236fa3e3779c72ccba"

REFERENCE_COMMITS = {
    "tst_wocker": "3372aa088328700feafeeb07c72ab832ea2d3ecb",
    "tw_block_warrant": "37463c54796ba36f4aac262519ea7fc2ef797de6",
    "tst_wocker_filter_lab": "06c87b7a1735877c9ccbab3a339c1742814a5058",
}

CANDIDATE_ROUTE_IDS = [
    "crsp_spdj_composite",
    "sp_global_market_intelligence",
    "lseg_data_analytics",
    "factset",
    "bloomberg_enterprise",
]

CAPABILITY_IDS = [
    "authorized_research_license",
    "point_in_time_sp500_membership",
    "membership_announced_at",
    "membership_effective_at",
    "permanent_security_company_ids",
    "security_metadata_known_at",
    "raw_daily_ohlcv_status",
    "distribution_event_clock_terms",
    "delist_exit_economics",
    "post_removal_price_path",
    "xnys_session_open_close",
    "synchronized_qqq_spy_execution",
    "exact_one_month_daily_simple_rf",
    "row_level_provenance_replay",
]

EVIDENCE_STATUSES = [
    "explicit_primary_documentation",
    "partial_primary_documentation",
    "contradicted_by_primary_documentation",
    "unresolved_primary_documentation",
    "validated_authorized_sample",
    "qualified_provider_package",
]

EXPECTED_ACTUAL_FORMAL_READINESS = {
    "passed": 1,
    "total": 18,
    "all_passed": False,
    "only_passed_gate": "01_preregistration_integrity",
}

PRIMARY_SOURCES: dict[str, dict[str, Any]] = {
    "crsp_stock_ciz_guide": {
        "title": "CRSP US Stock Databases Guide for Flat File Format 2.0",
        "owner": "Morningstar Indexes / CRSP",
        "url": (
            "https://indexes.morningstar.com/docs/guide/"
            "crsp-us-stock-databases-guide-for-flat-file-format-2-0?isRdp=true"
        ),
        "is_primary_owner_document": True,
    },
    "crsp_treasury_guide": {
        "title": "CRSP US Treasury Database Guide",
        "owner": "Morningstar Indexes / CRSP",
        "url": (
            "https://indexes.morningstar.com/docs/guide/crsp-us-treasury-database-guide?isRdp=true"
        ),
        "is_primary_owner_document": True,
    },
    "sp_dji_api": {
        "title": "S&P DJI API Data Solutions",
        "owner": "S&P Dow Jones Indices",
        "url": "https://www.spglobal.com/spdji/en/landing/topic/api-data-solutions/",
        "is_primary_owner_document": True,
    },
    "sp_dji_equity_policy": {
        "title": "Equity Indices Policies & Practices",
        "owner": "S&P Dow Jones Indices",
        "url": (
            "https://www.spglobal.com/spdji/en/documents/methodologies/"
            "methodology-sp-equity-indices-policies-practices.pdf?force_download=true"
        ),
        "is_primary_owner_document": True,
    },
    "sp_dji_us_methodology": {
        "title": "S&P U.S. Indices Methodology",
        "owner": "S&P Dow Jones Indices",
        "url": (
            "https://www.spglobal.com/spdji/en/documents/methodologies/"
            "methodology-sp-us-indices.pdf?os=TMB"
        ),
        "is_primary_owner_document": True,
    },
    "spgmi_market_data": {
        "title": "Market Data",
        "owner": "S&P Global Market Intelligence",
        "url": "https://www.marketplace.spglobal.com/en/datasets/market-data-%2817%29",
        "is_primary_owner_document": True,
    },
    "spgmi_index_data": {
        "title": "Index Data",
        "owner": "S&P Global Market Intelligence",
        "url": "https://www.marketplace.spglobal.com/en/datasets/index-data-%28100%29",
        "is_primary_owner_document": True,
    },
    "spgmi_corporate_actions": {
        "title": "Corporate Actions",
        "owner": "S&P Global Market Intelligence",
        "url": "https://www.spglobal.com/market-intelligence/en/solutions/corporate-actions",
        "is_primary_owner_document": True,
    },
    "spgmi_index_management": {
        "title": "Index Management",
        "owner": "S&P Global Market Intelligence",
        "url": (
            "https://www.spglobal.com/market-intelligence/en/solutions/products/index-management"
        ),
        "is_primary_owner_document": True,
    },
    "lseg_historical_constituents": {
        "title": "Building Historical Index Constituents",
        "owner": "LSEG Developer Community",
        "url": (
            "https://developers.lseg.com/en/article-catalog/article/"
            "building-historical-index-constituents"
        ),
        "is_primary_owner_document": True,
    },
    "lseg_quant_analytics": {
        "title": "Quantitative Analytics Cloud Fact Sheet",
        "owner": "LSEG",
        "url": (
            "https://www.lseg.com/content/dam/data-analytics/en_us/documents/"
            "fact-sheets/quantitative-analytics-cloud-fact-sheet.pdf"
        ),
        "is_primary_owner_document": True,
    },
    "lseg_corporate_actions": {
        "title": "Corporate Actions Data",
        "owner": "LSEG",
        "url": (
            "https://www.lseg.com/en/data-analytics/market-data/"
            "data-analytics-pricing/reference-data/corporate-actions"
        ),
        "is_primary_owner_document": True,
    },
    "factset_pricing_reference": {
        "title": "FactSet Pricing and Reference Data",
        "owner": "FactSet",
        "url": (
            "https://www.factset.com/marketplace/catalog/product/factset-pricing-and-reference-data"
        ),
        "is_primary_owner_document": True,
    },
    "factset_prices_returns": {
        "title": "FactSet Prices and Returns API",
        "owner": "FactSet",
        "url": (
            "https://www.factset.com/marketplace/catalog/product/factset-prices-and-returns-api"
        ),
        "is_primary_owner_document": True,
    },
    "factset_benchmarks": {
        "title": "FactSet Benchmarks API",
        "owner": "FactSet",
        "url": "https://developer.factset.com/api-catalog/factset-benchmarks-api",
        "is_primary_owner_document": True,
    },
    "factset_global_prices": {
        "title": "FactSet Global Prices API",
        "owner": "FactSet",
        "url": "https://developer.factset.com/api-catalog/factset-global-prices-api",
        "is_primary_owner_document": True,
    },
    "bloomberg_data_license": {
        "title": "Data License",
        "owner": "Bloomberg",
        "url": ("https://professional.bloomberg.com/products/data/data-management/data-license/"),
        "is_primary_owner_document": True,
    },
    "bloomberg_reference": {
        "title": "Reference Data",
        "owner": "Bloomberg",
        "url": "https://professional.bloomberg.com/products/data/enterprise-catalog/reference/",
        "is_primary_owner_document": True,
    },
    "bloomberg_research": {
        "title": "Investment Research Data",
        "owner": "Bloomberg",
        "url": (
            "https://professional.bloomberg.com/products/data/"
            "enterprise-catalog/investment-research-data/"
        ),
        "is_primary_owner_document": True,
    },
    "bloomberg_cofi": {
        "title": "Company Financials, Estimates and Pricing Point-in-Time",
        "owner": "Bloomberg",
        "url": "https://professional.bloomberg.com/products/data/enterprise-catalog/cofi/",
        "is_primary_owner_document": True,
    },
    "bloomberg_events": {
        "title": "Event-Driven Feeds",
        "owner": "Bloomberg",
        "url": (
            "https://professional.bloomberg.com/products/data/"
            "enterprise-catalog/event-driven-feeds/"
        ),
        "is_primary_owner_document": True,
    },
}


def _cap(status: str, source_ids: list[str], finding: str) -> dict[str, Any]:
    return {"status": status, "source_ids": source_ids, "finding": finding}


ROUTES: list[dict[str, Any]] = [
    {
        "id": "crsp_spdj_composite",
        "name": "CRSP Stock CIZ＋S&P DJI 事件＋CRSP Treasury",
        "role": "首個複合詢價路徑；公開證據最多，但並非同一授權的已交付 package。",
        "source_ids": [
            "crsp_stock_ciz_guide",
            "crsp_treasury_guide",
            "sp_dji_api",
            "sp_dji_equity_policy",
            "sp_dji_us_methodology",
        ],
        "capabilities": {
            "authorized_research_license": _cap(
                "unresolved_primary_documentation", [], "公開頁面不等於研究授權條款。"
            ),
            "point_in_time_sp500_membership": _cap(
                "explicit_primary_documentation",
                ["sp_dji_api", "crsp_stock_ciz_guide"],
                "官方 API／CIZ 文件支持歷史成分及生效區間。",
            ),
            "membership_announced_at": _cap(
                "partial_primary_documentation",
                ["sp_dji_equity_policy", "sp_dji_us_methodology"],
                "官方政策說明事件預告及 17:15 ET 慣例，未公開逐列 event ID export。",
            ),
            "membership_effective_at": _cap(
                "explicit_primary_documentation",
                ["sp_dji_equity_policy", "crsp_stock_ciz_guide"],
                "pro-forma／SDE 與 CIZ 生效區間把公布與生效分開。",
            ),
            "permanent_security_company_ids": _cap(
                "explicit_primary_documentation",
                ["crsp_stock_ciz_guide"],
                "PERMNO／PERMCO 及 successor 欄位有現行資料字典。",
            ),
            "security_metadata_known_at": _cap(
                "unresolved_primary_documentation",
                ["crsp_stock_ciz_guide"],
                "SecInfo 有效期不是逐列 KnownAt。",
            ),
            "raw_daily_ohlcv_status": _cap(
                "explicit_primary_documentation",
                ["crsp_stock_ciz_guide"],
                "raw 日線、成交量、回報及交易狀態有現行欄位。",
            ),
            "distribution_event_clock_terms": _cap(
                "explicit_primary_documentation",
                ["crsp_stock_ciz_guide"],
                "宣派／除權息／記錄／派付日期及條款有欄位支持。",
            ),
            "delist_exit_economics": _cap(
                "partial_primary_documentation",
                ["crsp_stock_ciz_guide"],
                "DelRet、missing type 及 successor 存在，但缺值不能推算為零。",
            ),
            "post_removal_price_path": _cap(
                "unresolved_primary_documentation",
                ["crsp_stock_ciz_guide"],
                "公開文件未承諾每次移除後至下一 rebalancing open 的完整路徑。",
            ),
            "xnys_session_open_close": _cap(
                "partial_primary_documentation",
                ["sp_dji_us_methodology"],
                "有假期政策，但未證明同一 package 的 20 年開收市及早收市 export。",
            ),
            "synchronized_qqq_spy_execution": _cap(
                "partial_primary_documentation",
                ["crsp_stock_ciz_guide"],
                "日線能力存在，仍須真實樣本證明兩 ETF 同 session raw open／總回報。",
            ),
            "exact_one_month_daily_simple_rf": _cap(
                "contradicted_by_primary_documentation",
                ["crsp_treasury_guide"],
                "日度系列為 4／13／26 週；精確 1 個月系列是月度連續複利收益率。",
            ),
            "row_level_provenance_replay": _cap(
                "partial_primary_documentation",
                ["crsp_stock_ciz_guide", "sp_dji_api"],
                "產品及欄位可固定，仍欠帳戶 export ID、逐列 source ID 與 hash。",
            ),
        },
    },
    {
        "id": "sp_global_market_intelligence",
        "name": "S&P Global Market Intelligence",
        "role": "歷史價格與指數數據廣，但公開 marketplace 明示非 point-in-time。",
        "source_ids": [
            "spgmi_market_data",
            "spgmi_index_data",
            "spgmi_corporate_actions",
            "spgmi_index_management",
        ],
        "capabilities": {
            "authorized_research_license": _cap(
                "unresolved_primary_documentation", [], "公開產品頁不構成訂閱或研究授權。"
            ),
            "point_in_time_sp500_membership": _cap(
                "contradicted_by_primary_documentation",
                ["spgmi_index_data"],
                "Index Data 公開規格明示 Point In Time: No。",
            ),
            "membership_announced_at": _cap(
                "unresolved_primary_documentation", ["spgmi_index_data"], "未見逐列公布 timestamp。"
            ),
            "membership_effective_at": _cap(
                "partial_primary_documentation",
                ["spgmi_index_data", "spgmi_index_management"],
                "有成分及 rebalance event，但公開頁未列固定生效 timestamp schema。",
            ),
            "permanent_security_company_ids": _cap(
                "explicit_primary_documentation",
                ["spgmi_index_data"],
                "指數成分可連接 S&P Global entity IDs。",
            ),
            "security_metadata_known_at": _cap(
                "unresolved_primary_documentation", ["spgmi_market_data"], "未見逐列歷史 KnownAt。"
            ),
            "raw_daily_ohlcv_status": _cap(
                "explicit_primary_documentation",
                ["spgmi_market_data"],
                "EOD as-quoted OHLCV 有公開規格；仍須樣本驗 raw 口徑及狀態。",
            ),
            "distribution_event_clock_terms": _cap(
                "partial_primary_documentation",
                ["spgmi_corporate_actions", "spgmi_market_data"],
                "公司行動及 dividend／split add-on 存在，固定欄位仍未公開齊全。",
            ),
            "delist_exit_economics": _cap(
                "unresolved_primary_documentation",
                ["spgmi_corporate_actions"],
                "未見 DelRet 等價經濟回報。",
            ),
            "post_removal_price_path": _cap(
                "unresolved_primary_documentation",
                ["spgmi_market_data"],
                "未見移除後路徑完整保證。",
            ),
            "xnys_session_open_close": _cap(
                "unresolved_primary_documentation",
                [],
                "未見同一 package 的固定 XNYS session export。",
            ),
            "synchronized_qqq_spy_execution": _cap(
                "partial_primary_documentation",
                ["spgmi_market_data"],
                "EOD 價格可覆蓋 ETF，但同步 raw open／總回報仍須樣本。",
            ),
            "exact_one_month_daily_simple_rf": _cap(
                "unresolved_primary_documentation", [], "未見指定經濟定義的日度簡單 RF。"
            ),
            "row_level_provenance_replay": _cap(
                "partial_primary_documentation",
                ["spgmi_index_management"],
                "平台宣稱可追溯及重現，仍欠本產品逐列 export 證據。",
            ),
        },
    },
    {
        "id": "lseg_data_analytics",
        "name": "LSEG Data & Analytics／Workspace／Datastream",
        "role": "最完整的單一品牌採購候選；仍欠公布時鐘、退市實收及精確 RF。",
        "source_ids": [
            "lseg_historical_constituents",
            "lseg_quant_analytics",
            "lseg_corporate_actions",
        ],
        "capabilities": {
            "authorized_research_license": _cap(
                "unresolved_primary_documentation", [], "須以實際 Workspace／DataScope 合約核對。"
            ),
            "point_in_time_sp500_membership": _cap(
                "explicit_primary_documentation",
                ["lseg_historical_constituents", "lseg_quant_analytics"],
                "官方示例以 as-of 成分加 Joiner／Leaver 重建歷史名單。",
            ),
            "membership_announced_at": _cap(
                "unresolved_primary_documentation",
                ["lseg_historical_constituents"],
                "Joiner／Leaver 能力未公開 S&P 500 公布 timestamp／event ID。",
            ),
            "membership_effective_at": _cap(
                "partial_primary_documentation",
                ["lseg_historical_constituents"],
                "變更日期存在，仍須確認 timestamp、時區及生效 session。",
            ),
            "permanent_security_company_ids": _cap(
                "explicit_primary_documentation",
                ["lseg_quant_analytics"],
                "fact sheet 明示單一不變 unique ID 及 security IDs。",
            ),
            "security_metadata_known_at": _cap(
                "partial_primary_documentation",
                ["lseg_quant_analytics"],
                "point-in-time 值及可靠 timestamp 有描述，未逐欄證明 metadata KnownAt。",
            ),
            "raw_daily_ohlcv_status": _cap(
                "explicit_primary_documentation",
                ["lseg_quant_analytics"],
                "pricing／timeseries 及已退市公司覆蓋有官方產品說明。",
            ),
            "distribution_event_clock_terms": _cap(
                "partial_primary_documentation",
                ["lseg_corporate_actions"],
                "公司行動有 25 年以上歷史及 audit trail，公開欄位未完整列出。",
            ),
            "delist_exit_economics": _cap(
                "partial_primary_documentation",
                ["lseg_quant_analytics", "lseg_corporate_actions"],
                "已退市公司存在，不等於逐次退出實收回報及缺失原因齊備。",
            ),
            "post_removal_price_path": _cap(
                "unresolved_primary_documentation",
                ["lseg_quant_analytics"],
                "未見逐事件完整路徑承諾。",
            ),
            "xnys_session_open_close": _cap(
                "partial_primary_documentation",
                ["lseg_quant_analytics"],
                "有 timeseries，未見固定 XNYS 日曆欄位。",
            ),
            "synchronized_qqq_spy_execution": _cap(
                "partial_primary_documentation",
                ["lseg_quant_analytics"],
                "須以同一 export 細樣本驗證同步。",
            ),
            "exact_one_month_daily_simple_rf": _cap(
                "unresolved_primary_documentation", [], "未見指定日度簡單 RF 經濟定義。"
            ),
            "row_level_provenance_replay": _cap(
                "partial_primary_documentation",
                ["lseg_corporate_actions", "lseg_quant_analytics"],
                "有 audit trail／timestamp，但仍欠帳戶列級 replay receipt。",
            ),
        },
    },
    {
        "id": "factset",
        "name": "FactSet",
        "role": "價格、永久 ID、公司行動與 as-of benchmark 強；公布時間及退出經濟未解。",
        "source_ids": [
            "factset_pricing_reference",
            "factset_prices_returns",
            "factset_benchmarks",
            "factset_global_prices",
        ],
        "capabilities": {
            "authorized_research_license": _cap(
                "unresolved_primary_documentation", [], "API 可見不代表已訂閱或可保存研究輸出。"
            ),
            "point_in_time_sp500_membership": _cap(
                "partial_primary_documentation",
                ["factset_benchmarks"],
                "Benchmarks API 支持指定 as-of date 成分，未證明完整變更事件歷史。",
            ),
            "membership_announced_at": _cap(
                "unresolved_primary_documentation",
                ["factset_benchmarks"],
                "未見公布 timestamp／event ID。",
            ),
            "membership_effective_at": _cap(
                "partial_primary_documentation",
                ["factset_benchmarks"],
                "as-of 成分可定位日期，未分開公布及生效時鐘。",
            ),
            "permanent_security_company_ids": _cap(
                "explicit_primary_documentation",
                ["factset_pricing_reference", "factset_benchmarks"],
                "FactSet permanent identifier／fsymRegionalId 有官方說明。",
            ),
            "security_metadata_known_at": _cap(
                "unresolved_primary_documentation",
                ["factset_pricing_reference"],
                "未見逐列歷史 KnownAt。",
            ),
            "raw_daily_ohlcv_status": _cap(
                "explicit_primary_documentation",
                ["factset_prices_returns"],
                "活躍及非活躍證券的歷史 OHLC、成交量及回報有 API。",
            ),
            "distribution_event_clock_terms": _cap(
                "partial_primary_documentation",
                ["factset_global_prices", "factset_prices_returns"],
                "splits／dividends／pay-date return 有能力，仍須固定完整事件時鐘。",
            ),
            "delist_exit_economics": _cap(
                "partial_primary_documentation",
                ["factset_prices_returns", "factset_pricing_reference"],
                "非活躍證券及 last-trade 可查，不等於 DelRet／現金換股條款完整。",
            ),
            "post_removal_price_path": _cap(
                "unresolved_primary_documentation",
                ["factset_prices_returns"],
                "未見移除後指定窗口完整保證。",
            ),
            "xnys_session_open_close": _cap(
                "partial_primary_documentation",
                ["factset_benchmarks"],
                "API 有 calendar 參數，未證明 XNYS 開收市時間。",
            ),
            "synchronized_qqq_spy_execution": _cap(
                "partial_primary_documentation",
                ["factset_prices_returns"],
                "須以同 cut 原始開市及總回報細樣本驗證。",
            ),
            "exact_one_month_daily_simple_rf": _cap(
                "unresolved_primary_documentation", [], "未見指定 RF 系列及單位。"
            ),
            "row_level_provenance_replay": _cap(
                "partial_primary_documentation",
                ["factset_pricing_reference", "factset_benchmarks"],
                "API 產品及 ID 可固定，仍欠 export/version/source-row receipt。",
            ),
        },
    },
    {
        "id": "bloomberg_enterprise",
        "name": "Bloomberg Enterprise／Data License",
        "role": "企業數據廣且有 point-in-time 產品；公開頁未證明本研究的成分事件全鏈。",
        "source_ids": [
            "bloomberg_data_license",
            "bloomberg_reference",
            "bloomberg_research",
            "bloomberg_cofi",
            "bloomberg_events",
        ],
        "capabilities": {
            "authorized_research_license": _cap(
                "unresolved_primary_documentation", [], "Data License 產品頁不是使用者合約。"
            ),
            "point_in_time_sp500_membership": _cap(
                "partial_primary_documentation",
                ["bloomberg_research", "bloomberg_reference"],
                "官方宣稱長 point-in-time 歷史及 index constituent data，未指定 S&P 500 事件鏈。",
            ),
            "membership_announced_at": _cap(
                "unresolved_primary_documentation",
                ["bloomberg_events"],
                "未見 S&P 500 逐列公布 timestamp／ID。",
            ),
            "membership_effective_at": _cap(
                "unresolved_primary_documentation",
                ["bloomberg_reference"],
                "未見固定 membership effective schema。",
            ),
            "permanent_security_company_ids": _cap(
                "explicit_primary_documentation",
                ["bloomberg_cofi", "bloomberg_reference"],
                "Bloomberg Company ID、FIGI 及 security master 有官方說明。",
            ),
            "security_metadata_known_at": _cap(
                "partial_primary_documentation",
                ["bloomberg_cofi", "bloomberg_research"],
                "PIT pricing/security master 存在，但公開範圍為 17 年且未逐欄列 KnownAt。",
            ),
            "raw_daily_ohlcv_status": _cap(
                "explicit_primary_documentation",
                ["bloomberg_data_license", "bloomberg_reference"],
                "歷史／EOD pricing 及 reference status 有企業數據能力。",
            ),
            "distribution_event_clock_terms": _cap(
                "explicit_primary_documentation",
                ["bloomberg_reference", "bloomberg_events"],
                "公司行動有 50 類事件及結構化 feed。",
            ),
            "delist_exit_economics": _cap(
                "partial_primary_documentation",
                ["bloomberg_events", "bloomberg_research"],
                "涵蓋 bankruptcy／inactive companies，未見逐次退出實收回報及缺失原因。",
            ),
            "post_removal_price_path": _cap(
                "unresolved_primary_documentation",
                ["bloomberg_data_license"],
                "未見移除後指定窗口覆蓋承諾。",
            ),
            "xnys_session_open_close": _cap(
                "unresolved_primary_documentation",
                [],
                "未見同一 package 的 XNYS 開收市／早收市輸出。",
            ),
            "synchronized_qqq_spy_execution": _cap(
                "partial_primary_documentation",
                ["bloomberg_reference"],
                "EOD 價格可覆蓋 ETF，仍須同步 raw 樣本。",
            ),
            "exact_one_month_daily_simple_rf": _cap(
                "unresolved_primary_documentation", [], "未見指定一個月日度簡單回報系列。"
            ),
            "row_level_provenance_replay": _cap(
                "partial_primary_documentation",
                ["bloomberg_data_license"],
                "DL+ 可追溯 source files，仍欠逐列 source ID、cut、列數及 SHA。",
            ),
        },
    },
]

PROCUREMENT_QUESTIONS = [
    {
        "capability": "authorized_research_license",
        "question": "請提供允許本地研究、20 年回測、保存驗收收據及發布彙總衍生結果的合約條款。",
    },
    {
        "capability": "membership_announced_at",
        "question": "每次 S&P 500 加入／移除可否交付公布 timestamp、時區、event ID 及原始來源？",
    },
    {
        "capability": "security_metadata_known_at",
        "question": "歷史 ticker、交易所、股份類別及行業可否逐列交付 KnownAt，而非只給 effective range？",
    },
    {
        "capability": "delist_exit_economics",
        "question": "缺失 DelRet 時可否交付原因、現金／換股條款、successor 及實際退出收益？",
    },
    {
        "capability": "post_removal_price_path",
        "question": "可否保證每次成分移除日至下一月度重新平衡 open 的 raw 可交易價格及狀態完整？",
    },
    {
        "capability": "xnys_session_open_close",
        "question": "可否同 cut 交付 2005-08-01 至 2026-07-31 的 XNYS session、開收市及早收市時間？",
    },
    {
        "capability": "synchronized_qqq_spy_execution",
        "question": "QQQ／SPY 可否與個股同 session、同 cut 交付 raw open、總回報因子及交易狀態？",
    },
    {
        "capability": "exact_one_month_daily_simple_rf",
        "question": "可否交付 US_1M_TBILL_DAILY_RETURN 同經濟定義的日度 simple return，而非 4 週或年率換算？",
    },
    {
        "capability": "row_level_provenance_replay",
        "question": "每次 export 可否固定產品版本、cutoff、export ID、逐列 source ID、列數及 SHA-256？",
    },
]


class ProviderGapClosureError(ValueError):
    """Fail-closed public-evidence error with a stable semantic code."""

    def __init__(self, code: str, detail: str):
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}")


def _fail(code: str, detail: str) -> None:
    raise ProviderGapClosureError(code, detail)


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _protocol_integrity(root: str | Path) -> dict[str, Any]:
    root_path = Path(root).resolve()
    try:
        receipt_path = root_path / PROTOCOL_RECEIPT_PATH
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        parent_keys = [
            "parent_provider_convergence_protocol",
            "parent_provider_convergence_validation",
            "parent_formal_protocol",
            "parent_authorized_handoff_protocol",
        ]
        hash_checks = {
            PROTOCOL_PATH: _sha256_file(root_path / PROTOCOL_PATH) == PROTOCOL_SHA256,
            PROTOCOL_RECEIPT_PATH: _sha256_file(receipt_path) == PROTOCOL_RECEIPT_SHA256,
        }
        for key in parent_keys:
            item = receipt[key]
            hash_checks[item["path"]] = _sha256_file(root_path / item["path"]) == item["sha256"]
        passed = bool(
            receipt["schema_version"] == 1
            and receipt["research_round"] == 21
            and receipt["status"]
            == (
                "frozen_after_local_access_audit_before_new_provider_"
                "evidence_inspection_and_implementation"
            )
            and receipt["protocol"] == {"path": PROTOCOL_PATH, "sha256": PROTOCOL_SHA256}
            and receipt["reference_commits"] == REFERENCE_COMMITS
            and receipt["candidate_route_ids"] == CANDIDATE_ROUTE_IDS
            and receipt["required_capability_ids"] == CAPABILITY_IDS
            and receipt["new_candidate_provider_evidence_inspected_at_freeze"] is False
            and receipt["gap_closure_implementation_present_at_freeze"] is False
            and receipt["gap_closure_output_present_at_freeze"] is False
            and receipt["strategy_run_count"] == 0
            and receipt["paper_authorized"] is False
            and receipt["paper_state"] == "all_cash"
            and receipt["real_money_action_usd"] == 0
            and receipt["frozen_control_count"] == 15
            and receipt["frozen_attack_count"] == 15
            and all(hash_checks.values())
        )
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError):
        receipt = {}
        hash_checks = {}
        passed = False
    if not passed:
        _fail("gap_protocol_mismatch", "第 21 輪協議、收據或父契約 SHA 漂移")
    return {
        "passed": True,
        "frozen_at": receipt["frozen_at"],
        "git_head_at_freeze": receipt["git_head_at_freeze"],
        "hash_checks": hash_checks,
    }


def _route_with_counts(route: dict[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(route)
    counts = {status: 0 for status in EVIDENCE_STATUSES}
    for capability in result["capabilities"].values():
        counts[capability["status"]] += 1
    result["status_counts"] = counts
    result["documented_or_partial_count"] = (
        counts["explicit_primary_documentation"] + counts["partial_primary_documentation"]
    )
    result["public_decision"] = "procurement_candidate"
    result["qualified"] = False
    result["hard_gap_capabilities"] = [
        capability_id
        for capability_id, capability in result["capabilities"].items()
        if capability["status"] != "explicit_primary_documentation"
    ]
    return result


def frozen_gap_closure_record() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "research_round": 21,
        "gap_version": GAP_VERSION,
        "evidence_as_of": EVIDENCE_AS_OF,
        "protocol_sha256": PROTOCOL_SHA256,
        "reference_commits": copy.deepcopy(REFERENCE_COMMITS),
        "candidate_route_ids": copy.deepcopy(CANDIDATE_ROUTE_IDS),
        "required_capability_ids": copy.deepcopy(CAPABILITY_IDS),
        "evidence_statuses": copy.deepcopy(EVIDENCE_STATUSES),
        "primary_sources": copy.deepcopy(PRIMARY_SOURCES),
        "routes": [_route_with_counts(route) for route in ROUTES],
        "methodology": {
            "primary_owner_documents_only": True,
            "product_identity_inferred": False,
            "license_inferred_from_public_access": False,
            "twenty_year_coverage_inferred_from_history_claim": False,
            "membership_announced_at_substituted_with_effective_at": False,
            "metadata_known_at_substituted_with_effective_range": False,
            "raw_open_substituted_with_adjusted_price": False,
            "missing_delist_economics_imputed_zero": False,
            "calendar_or_benchmark_execution_omitted": False,
            "risk_free_tenor_or_unit_substituted": False,
            "public_documentation_maximum_decision": "procurement_candidate",
        },
        "procurement_questions": copy.deepcopy(PROCUREMENT_QUESTIONS),
        "decision": {
            "best_documented_route_id": "crsp_spdj_composite",
            "strongest_standalone_brand_candidate_id": "lseg_data_analytics",
            "qualified_route_count": 0,
            "authorized_provider_package_received": False,
            "complete_risk_free_package_received": False,
            "actual_formal_readiness": copy.deepcopy(EXPECTED_ACTUAL_FORMAL_READINESS),
            "formal_stock_backtest_input_ready": False,
            "formal_stock_backtest_completed": False,
            "strategy_run_count": 0,
            "paper_authorized": False,
            "paper_state": "all_cash",
            "backfilled_trades": 0,
            "positions": [],
            "real_money_action_usd": 0,
        },
    }


def validate_provider_gap_closure(record: dict[str, Any], *, root: str | Path) -> dict[str, Any]:
    protocol = _protocol_integrity(root)
    if record.get("gap_version") != GAP_VERSION or record.get("protocol_sha256") != PROTOCOL_SHA256:
        _fail("gap_protocol_mismatch", "協議版本或 SHA 漂移")
    if record.get("reference_commits") != REFERENCE_COMMITS:
        _fail("gap_reference_mismatch", "台股參考 commit 與凍結版本不符")
    if (
        record.get("candidate_route_ids") != CANDIDATE_ROUTE_IDS
        or [route.get("id") for route in record.get("routes", [])] != CANDIDATE_ROUTE_IDS
    ):
        _fail("candidate_set_mismatch", "候選路徑集合或次序漂移")
    if (
        record.get("required_capability_ids") != CAPABILITY_IDS
        or record.get("evidence_statuses") != EVIDENCE_STATUSES
        or any(
            list(route.get("capabilities", {})) != CAPABILITY_IDS
            for route in record.get("routes", [])
        )
    ):
        _fail("capability_set_mismatch", "十四項能力集合或次序漂移")

    sources = record.get("primary_sources", {})
    if sources != PRIMARY_SOURCES or any(
        source.get("is_primary_owner_document") is not True for source in sources.values()
    ):
        _fail("non_primary_evidence", "只接受供應商或數據擁有者的一手文件")
    for route in record["routes"]:
        if any(source_id not in sources for source_id in route["source_ids"]):
            _fail("non_primary_evidence", "路徑引用了未固定的一手來源")
        for capability in route["capabilities"].values():
            if capability["status"] not in EVIDENCE_STATUSES:
                _fail("capability_set_mismatch", "未知證據等級")
            if any(source_id not in sources for source_id in capability["source_ids"]):
                _fail("non_primary_evidence", "能力引用了未固定的一手來源")

    methodology = record.get("methodology", {})
    if methodology.get("product_identity_inferred") is not False:
        _fail("product_identity_inference", "不得由品牌宣傳推算產品 identity")
    if methodology.get("license_inferred_from_public_access") is not False:
        _fail("license_inference", "公開下載不得冒充研究授權")
    if methodology.get("twenty_year_coverage_inferred_from_history_claim") is not False:
        _fail("coverage_inference", "歷史數據宣傳不得冒充固定 20 年完整覆蓋")
    if methodology.get("membership_announced_at_substituted_with_effective_at") is not False:
        _fail("membership_time_substitution", "effective time 不得冒充 announced time")
    if methodology.get("metadata_known_at_substituted_with_effective_range") is not False:
        _fail("known_at_substitution", "metadata effective range 不得冒充 KnownAt")
    if methodology.get("raw_open_substituted_with_adjusted_price") is not False:
        _fail("adjusted_price_substitution", "adjusted price 不得冒充 raw open")
    if methodology.get("missing_delist_economics_imputed_zero") is not False:
        _fail("delist_imputation", "缺失退出經濟代價不得填 0")
    if methodology.get("calendar_or_benchmark_execution_omitted") is not False:
        _fail("calendar_benchmark_omission", "XNYS 及同步 QQQ／SPY 不得省略")
    if methodology.get("risk_free_tenor_or_unit_substituted") is not False:
        _fail("risk_free_substitution", "相近年期或單位不得冒充精確 RF")

    expected = frozen_gap_closure_record()
    if (
        methodology.get("primary_owner_documents_only") is not True
        or methodology.get("public_documentation_maximum_decision") != "procurement_candidate"
        or record.get("procurement_questions") != PROCUREMENT_QUESTIONS
        or record.get("decision") != expected["decision"]
        or any(route.get("qualified") for route in record["routes"])
        or any(
            route.get("public_decision") != "procurement_candidate" for route in record["routes"]
        )
    ):
        _fail(
            "gap_decision_boundary_violation",
            "公開文件不得提高 readiness、運行策略、啟動 Paper 或實金",
        )

    return {
        "passed": True,
        "protocol_integrity": protocol,
        "candidate_route_count": len(CANDIDATE_ROUTE_IDS),
        "required_capability_count": len(CAPABILITY_IDS),
        "primary_source_count": len(PRIMARY_SOURCES),
        "qualified_route_count": 0,
        "actual_formal_readiness": copy.deepcopy(EXPECTED_ACTUAL_FORMAL_READINESS),
    }
