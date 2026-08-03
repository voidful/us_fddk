from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from usfddk.provider_qualification import build_provider_qualification  # noqa: E402

VALIDATION = ROOT / "artifacts/short_term_provider_qualification.json"
SITE_DATA = ROOT / "site/data/short-term-provider-qualification.json"
REPORT = ROOT / "docs/SHORT_TERM_PROVIDER_QUALIFICATION_REPORT.md"


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rendered = json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(rendered, encoding="utf-8")
    temporary.replace(path)


def _site_summary(data: dict[str, Any]) -> dict[str, Any]:
    selected_gates = (
        "05_security_master",
        "06_identifier_history",
        "07_membership_availability",
        "08_membership_intervals",
        "12_market_data_validity",
        "14_corporate_actions",
        "16_permanent_exit_economics",
        "18_point_in_time_classifications",
        "19_share_class_dedup_capability",
        "20_execution_clock",
    )
    return {
        "schema_version": 1,
        "round": 11,
        "status": data["status"],
        "headline": data["headline"],
        "evidence_as_of": data["evidence_as_of"],
        "independent_first_seen_evidence": False,
        "actual_point_in_time_readiness": data["actual_point_in_time_readiness"],
        "provider_preflight_passed": 0,
        "provider_preflight_total": len(data["providers"]),
        "providers": [
            {
                "id": provider["id"],
                "name": provider["name"],
                "role": provider["role"],
                "document_supported_count": provider["document_supported_count"],
                "partial_count": provider["partial_count"],
                "unresolved_count": 20
                - provider["document_supported_count"]
                - provider["partial_count"],
                "status_counts": provider["status_counts"],
                "hard_blockers": provider["hard_blockers"],
                "next_action": provider["next_action"],
                "first_enquiry": provider["first_enquiry"],
                "locally_verified": False,
                "contract_passed": False,
                "selected_gates": {
                    key: provider["gates"][key] for key in selected_gates
                },
            }
            for provider in data["providers"]
        ],
        "first_enquiry": data["first_enquiry"],
        "hard_findings": data["hard_findings"],
        "formal_stock_backtest_authorized": False,
        "formal_stock_backtest_completed": False,
        "paper": data["paper"],
        "real_money_action_usd": 0,
        "next_action": data["next_action"],
        "source_links": [
            {
                "label": "CRSP 股票數據 guide",
                "url": "https://indexes.morningstar.com/docs/guide/crsp-us-stock-databases-guide-for-flat-file-format-2-0?isRdp=true",
            },
            {
                "label": "CRSP Historical Indexes",
                "url": "https://indexes.morningstar.com/research-data-products/crsp-historical-indexes-database",
            },
            {
                "label": "Norgate Data Content",
                "url": "https://norgatedata.com/data-content-tables.php",
            },
            {
                "label": "Norgate Data FAQ",
                "url": "https://norgatedata.com/data-package-faq.php",
            },
            {
                "label": "Sharadar SEP metadata",
                "url": "https://data.nasdaq.com/api/v3/datatables/SHARADAR/SEP/metadata.json",
            },
            {
                "label": "Massive Stocks 文件",
                "url": "https://massive.com/docs/rest/stocks",
            },
        ],
    }


def _cell(provider: dict[str, Any], key: str) -> str:
    labels = {
        "documented": "明確",
        "partial": "部分",
        "not_documented": "未見",
        "unresolved_login_required": "需登入",
        "not_applicable_until_import": "待匯入",
    }
    return labels[provider["gates"][key]["status"]]


def _render_report(data: dict[str, Any]) -> str:
    providers = {provider["id"]: provider for provider in data["providers"]}
    rows = "\n".join(
        "| {name} | {documented}/20 | {partial}/20 | {unresolved}/20 | 否 | {role} |".format(
            name=provider["name"],
            documented=provider["document_supported_count"],
            partial=provider["partial_count"],
            unresolved=20
            - provider["document_supported_count"]
            - provider["partial_count"],
            role=provider["role"],
        )
        for provider in data["providers"]
    )
    capability_rows = "\n".join(
        "| {label} | {crsp} | {norgate} | {sharadar} | {polygon} |".format(
            label=label,
            crsp=_cell(providers["crsp_wrds"], key),
            norgate=_cell(providers["norgate_data"], key),
            sharadar=_cell(providers["nasdaq_data_link_sharadar"], key),
            polygon=_cell(providers["polygon_io_stocks"], key),
        )
        for key, label in (
            ("05_security_master", "永久證券／公司 ID"),
            ("06_identifier_history", "歷史代號及上市地"),
            ("07_membership_availability", "成分公布時間"),
            ("08_membership_intervals", "歷史 S&P 500 成分區間"),
            ("09_fixed_20_year_calendar", "固定 20 年日線"),
            ("12_market_data_validity", "Raw OHLCV／總回報"),
            ("14_corporate_actions", "公司行動明細"),
            ("16_permanent_exit_economics", "退市／收購經濟回報"),
            ("18_point_in_time_classifications", "歷史分類"),
            ("19_share_class_dedup_capability", "股份類別去重"),
            ("20_execution_clock", "t 收市／t+1 開市"),
        )
    )
    return f"""# 美股短線高回報研究｜第十一輪數據來源資格報告

研究日期：2026-08-04　｜　官方文件存取：{data['evidence_as_of']}

狀態：**沒有單一來源通過採購前最低條件；逐股數據仍為 1/20**

## 一頁結論

本輪沒有再調短線策略參數，也沒有用供應商宣傳頁代替真實數據。四條事前固定來源逐項
對照既有 20 道 point-in-time／退市合約後，結論是：**CRSP／WRDS 最接近正式入口，
但仍只值得先索取 data dictionary、細樣本及授權條款；Norgate、Sharadar 及
Polygon.io／Massive 均不能單獨完成現有合約。**

| 路徑 | 官方文件明確 | 只部分支持 | 未解／待匯入 | 採購前通過 | 正確定位 |
|---|---:|---:|---:|---:|---|
{rows}

「官方文件明確」不等於數據閘門通過。真實入口仍只過凍結順序 1/20；四條路徑本地驗證
全部為 false，正式 20 年逐股回測 0 次，短線 Paper 保持全現金、0 成交、0 持倉，
實金動作 US$0。

## 最重要的新發現

### 1. CRSP／WRDS 是首選查詢對象，但不是已通過

[CRSP 股票數據 guide](https://indexes.morningstar.com/docs/guide/crsp-us-stock-databases-guide-for-flat-file-format-2-0?isRdp=true)
明列 PERMNO／PERMCO、歷史 security／issuer information、ticker、CUSIP、primary
exchange、share class、SIC／NAICS／ICB／UES、日線 raw OHLCV、分派、調整因子、
delisting return 及 S&P 500 membership 起訖日。DlyOpen 自 1992 年後可用，覆蓋固定
2006–2026 主期。

但兩個硬缺口不能省略：guide 沒有找到 S&P 500 **成分公布時間**；DelRetMissType 又
明確容許某些退市回報缺失。沒有抽查真實 20 年 data cut 前，不能聲稱退出經濟回報完整，
更不能把 CRSP 品牌名稱直接當成 20/20。

### 2. Norgate 不是現有合約的單一替代品

[Norgate Data Content Tables](https://norgatedata.com/data-content-tables.php) 確認
Platinum／Diamond 有退市股票、1957 年起 S&P 500 歷史成分、日線 OHLCV、股息及
capital-event 指示；assetid 亦在證券生命週期保持不變。

然而 [Norgate 官方 FAQ](https://norgatedata.com/data-package-faq.php) 同時明示：

- 不提供舊 ticker，只把全部歷史接到現時／最後代號；
- 不提供歷史成分公布日期；
- 不直接提供公司行動事件明細或精確歷史主上市地；
- 不提供 delisting return，官方建議以最後交易 bar 近似。

最後交易 bar 不是破產全損、現金收購或換股代價的同義詞，會直接違反第 16 道硬閘門。
因此過往報告把 Norgate 與 CRSP 並列為「可能正式入口」需要收窄：Norgate 可作成分／
價格補充來源，但在現有合約下不能單獨放行。

### 3. Sharadar 公開資料不足以完成資格判定

Nasdaq Data Link 公開 metadata 只確認
[SEP](https://data.nasdaq.com/api/v3/datatables/SHARADAR/SEP/metadata.json)、
[TICKERS](https://data.nasdaq.com/api/v3/datatables/SHARADAR/TICKERS/metadata.json) 及
[ACTIONS](https://data.nasdaq.com/api/v3/datatables/SHARADAR/ACTIONS/metadata.json) 三張表，
亦可看到 permaticker、ticker/date 主鍵及 filters；完整欄位和原始列仍需有效 API key。
官方公開範圍沒有證明歷史 S&P 500 membership、成分公布時間、退出代價或歷史分類，
所以不先購買訂閱來尋找較好答案。

### 4. Polygon.io 已遷移至 Massive，適合補價格，不適合補成分／退出

原始三個 `polygon.io` URL 已 redirect 至 `massive.com`；原協議先按 domain 失敗，之後
另立只修正官方遷移 alias 的 schema-informed repair，固定
`independent_first_seen_evidence=false`。repair 後官方文件支持 2003 年起日線 OHLCV、
active／delisted ticker、Composite／Share Class FIGI、ticker change、股息及拆股；但沒有
找到歷史 S&P 500 membership、公布時間、完整 merger／spinoff outcome 或退出經濟回報。
它可在未來核對日價、成交及買賣差價，不可單獨修復存活者偏差。

## 十一項核心能力對照

| 能力 | CRSP／WRDS | Norgate | Sharadar | Polygon／Massive |
|---|---:|---:|---:|---:|
{capability_rows}

「明確」只代表官方文件有相應欄位；「部分」代表仍欠合約要求的一部分；「需登入」不是
假定存在；「待匯入」只可由真實列的 SHA-256、列數、覆蓋率及正反稽核回答。

## 事前順序與非獨立 repair

原始第十一輪協議先於任何新官方文件提交，供應商集合、20 道映射、狀態詞及停止規則
均已固定。首次文件閱讀才發現 CRSP 已遷移至 Morningstar Indexes、Polygon.io 已遷移至
Massive；由於原 domain 白名單沒有兩個新 domain，原 source-scope 檢查先失敗。

其後 repair 只容許 `crsp.org → indexes.morningstar.com` 及
`polygon.io → massive.com` 兩個精確 alias，不增加供應商、不改 20 道映射或策略規則。
因為已看過 redirect 及部分內容，本輪不是獨立 first-seen 策略證據；它只是一份採購前
工程診斷。

## 下一個唯一有效動作

先向 CRSP／WRDS 索取不含敏感原始列的 schema、20 年細樣本及授權條款，書面回答：

1. S&P 500 成分公告時間能否逐次提供；
2. 2006–2026 有多少退出樣本缺 DelRet，能否取得現金／換股代價；
3. raw open／OHLCV、停牌及退市後價格的完整率；
4. 歷史分類與股份類別何時可知；
5. 本地研究、雜湊收據及禁止公開原始列的授權邊界。

五項都拿到後，才把合法轉換包送入既有 20 道驗證器。20/20 亦只准按已凍結 v1 規則
正式重跑一次，並須勝 QQQ、SPY、逐期成分等權及同股漂移，扣 10／25／50 bps，通過
NW／PSR／全專案 DSR／PBO 及前後十年、滾動窗口、危機段；全部經濟與統計門檻通過後，
才可由全現金建立不能回填的 Paper。歷史及文件研究不構成供應商背書、投資建議或盈利
保證。
"""


def main() -> int:
    data = build_provider_qualification(ROOT)
    _write_json(VALIDATION, data)
    _write_json(SITE_DATA, _site_summary(data))
    REPORT.write_text(_render_report(data), encoding="utf-8")
    print(
        json.dumps(
            {
                "status": data["status"],
                "point_in_time_readiness": data["actual_point_in_time_readiness"],
                "provider_preflight_passed": 0,
                "provider_preflight_total": len(data["providers"]),
                "formal_stock_backtest_authorized": False,
                "paper_authorized": False,
                "real_money_action_usd": 0,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
