from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from usfddk.authorized_data_handoff import run_authorized_data_handoff_validation

ROOT = Path(__file__).resolve().parents[1]
MACHINE_PATH = ROOT / "artifacts/short_term_authorized_data_handoff.json"
SITE_PATH = ROOT / "site/data/short-term-authorized-data-handoff.json"
REPORT_PATH = ROOT / "docs/SHORT_TERM_AUTHORIZED_DATA_HANDOFF.md"


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _site_summary(data: dict[str, Any]) -> dict[str, Any]:
    request = data["request"]
    verification = data["official_verification"]
    return {
        "schema_version": data["schema_version"],
        "round": data["research_round"],
        "status": data["status"],
        "evidence_as_of": data["evidence_as_of"],
        "headline": "文件交接控制 12/12；真實文件 1/12、逐股數據 1/20",
        "request_status": request["status"],
        "request_id": request["request_id"],
        "protocol_sha256": request["protocol_sha256"],
        "coverage": request["coverage"],
        "source_format": request["source_format"],
        "source_file_count": len(request["source_files"]),
        "provider_products_to_confirm": request["provider_products_to_confirm"],
        "wrds_dataset_candidates_to_confirm": request[
            "wrds_dataset_candidates_to_confirm"
        ],
        "official_findings": verification["findings"],
        "data_dictionary_login_required": verification[
            "data_dictionary_login_required"
        ],
        "provider_contacted": verification["provider_contacted"],
        "authorized_provider_response_received": verification[
            "authorized_provider_response_received"
        ],
        "authorized_provider_sample_received": verification[
            "authorized_provider_sample_received"
        ],
        "synthetic_gate_summary": data["synthetic_control"]["gate_summary"],
        "synthetic_gates": data["synthetic_control"]["gates"],
        "attack_summary": data["attack_summary"],
        "attacks": data["attacks"],
        "actual_document_handoff": data["actual_document_handoff"],
        "actual_point_in_time_readiness": data[
            "actual_point_in_time_readiness"
        ],
        "formal_stock_backtest_authorized": data[
            "formal_stock_backtest_authorized"
        ],
        "formal_stock_backtest_completed": data[
            "formal_stock_backtest_completed"
        ],
        "strategy_rule_changed": data["strategy_rule_changed"],
        "paper": data["paper"],
        "real_money_action_usd": data["real_money_action_usd"],
        "next_action": data["next_action"],
    }


def _gate_rows(data: dict[str, Any]) -> str:
    return "\n".join(
        f"| {row['id']} | {row['label']} | {'通過' if row['passed'] else '未通過'} | "
        f"{row['detail']} |"
        for row in data["synthetic_control"]["gates"]
    )


def _attack_rows(data: dict[str, Any]) -> str:
    return "\n".join(
        f"| {row['id']} | {row['label']} | `{row['expected_error_code']}` | "
        f"{'拒收' if row['rejected'] else '誤收'} |"
        for row in data["attacks"]
    )


def _file_rows(data: dict[str, Any]) -> str:
    return "\n".join(
        f"| `{item['name']}` | {item['source_role']} | "
        f"{', '.join(f'`{field}`' for field in item['minimum_fields'])} |"
        for item in data["request"]["source_files"]
    )


def _render_report(data: dict[str, Any]) -> str:
    request = data["request"]
    synthetic = data["synthetic_control"]["gate_summary"]
    attacks = data["attack_summary"]
    actual = data["actual_document_handoff"]
    readiness = data["actual_point_in_time_readiness"]
    coverage = request["coverage"]
    products = "、".join(
        f"`{item['product_code']}`" for item in request["provider_products_to_confirm"]
    )
    mappings = "、".join(
        f"`{item}`" for item in request["wrds_dataset_candidates_to_confirm"]
    )
    return f"""# 美股短線高回報研究｜第十六輪授權數據交接文件

研究日期：2026-08-04　｜　請求狀態：準備好可交付，尚未對外發送

## 一頁結論

本輪把 CRSP／WRDS 文件查詢、授權證明及細樣本交付條件做成一份固定、可雜湊、
fail-closed 的請求。合成文件控制通過 **{synthetic['passed']}/{synthetic['total']}**，
事前固定的十二項 schema、授權、時間、成分、退市及基準攻擊
**{attacks['rejected']}/{attacks['total']} 全數拒收**。

這不代表已聯絡供應商。現時沒有 WRDS 憑證、供應商文件回覆或供應商數據列；真實文件
交接只過 **{actual['passed']}/{actual['total']}**，逐股 point-in-time 數據仍是
**{readiness['passed']}/{readiness['total']}**。正式 20 年逐股回測 0 次，短線 Paper
維持全現金、0 成交、0 持倉，實金動作 US$0。

## 可直接交付的固定請求

- Request ID：`{request['request_id']}`；
- 協議 SHA-256：`{request['protocol_sha256']}`；
- 正式期：{coverage['formal_start']} 至 {coverage['formal_end']}；
- 訊號緩衝：由 {coverage['buffer_start']} 起、每股至少
  {coverage['minimum_pre_signal_sessions']} 個正式 session；
- 成交尾端：至少至 {coverage['next_execution_session']}；
- 現行格式：`{request['source_format']}`；
- 公開目錄候選：{products}。產品名稱中的 Monthly 是更新套裝標示，不推論為只有月線；
- 公開 WRDS 程式所見候選：{mappings}。這些名稱必須由登入後目錄或供應商回覆確認。

請供應商按
[`schemas/short_term_authorized_data_response.schema.json`](../schemas/short_term_authorized_data_response.schema.json)
回覆能力、產品、授權及限制。12/12 只准進入本地隔離細樣本交付，不代表數據或策略通過。

## 十份數據／證據輸入

| 檔案 | 責任層 | 最少欄位 |
|---|---|---|
{_file_rows(data)}

另需 QQQ／SPY 同一來源、同一交易日的 raw OHLCV、總回報因子及來源記錄 ID。所有原始列、
憑證、合約、報價及供應商回覆只可留在使用者授權的本地隔離位置，不可加入 Git 或網站。

## 五個必答問題

1. S&P 500 成分 start／end 及每次 announcement／availability timestamp 可否提供？
2. 2006–2026 的 DelRet 缺失數量、比例及 missing reason 是多少？
3. 缺失 DelRet 能否以現金／換股代價及 successor PERMNO／PERMCO 決定性重建？
4. raw OHLCV、停牌、DisExDt、DisPayDt 及下一開市覆蓋是否完整？
5. 本地研究、衍生匯總、SHA-256 收據及禁止原始列再分發的授權邊界是甚麼？

## 十二道合成文件控制

| # | 閘門 | 結果 | 證據 |
|---|---|---|---|
{_gate_rows(data)}

## 十二項固定攻擊

| # | 單一錯誤 | 指定拒收代碼 | 結果 |
|---|---|---|---|
{_attack_rows(data)}

每次攻擊均重算 response SHA-256，只留下單一語義錯誤。因此 12/12 證明驗證器會按指定
錯誤關門，不是用 generic hash mismatch 遮蓋問題，也不代表有真實市場證據。

## 公開文件核對

- [WRDS CIZ 格式變更](https://wrds-www.wharton.upenn.edu/pages/data-announcements/changes-to-crsp-data/)：CIZ Flat File Format 2.0 已取代 SIZ；
- [WRDS CIZtoSIZ macro](https://wrds-www.wharton.upenn.edu/pages/wrds-research/macros/crsp-ciztosiz-macro/)：公開程式列出 `crsp.dsf_v2`、`crsp.msf_v2` 及 `StkSecurityInfoHist` 候選；
- [WRDS Size CIZ macro](https://wrds-www.wharton.upenn.edu/pages/wrds-research/macros/macros-portfolios-size-ciz/)：公開程式列出 `a_stock_v2`、`a_indexes_v2` library 候選；
- [WRDS CRSP 產品目錄](https://wrds-www.wharton.upenn.edu/pages/about/data-vendors/center-for-research-in-security-prices-crsp/)：公開目錄列出 `crsp_m_stock`、`crsp_m_indexes`；完整 data dictionary 要登入確認。

以上只證明公開文件中的候選名稱，不證明使用者已有訂閱、供應商已回覆，亦不代表十份
輸入可由單一產品完整供應。

## 決策與下一步

需要使用者授權對外聯絡後，才把這份固定請求交給 CRSP／WRDS。帶產品及授權的文件回覆
通過 12/12 後，只接受本地隔離的合法細樣本，再依次運行樣本驗收、真實 20/20、
execution extension 16/16 及一次固定 20 年策略回測。任何一層失敗，都不改規則、不刪
退出樣本、不改基準，亦不建立短線 Paper。

本文件不構成採購承諾、供應商背書、投資建議或盈利保證。
"""


def main() -> None:
    data = run_authorized_data_handoff_validation(ROOT)
    _write_json(MACHINE_PATH, data)
    _write_json(SITE_PATH, _site_summary(data))
    REPORT_PATH.write_text(_render_report(data), encoding="utf-8")
    print(
        json.dumps(
            {
                "status": data["status"],
                "synthetic_control": data["synthetic_control"]["gate_summary"],
                "attacks": data["attack_summary"],
                "actual_document_handoff": data["actual_document_handoff"],
                "true_readiness": data["actual_point_in_time_readiness"],
                "provider_contacted": data["official_verification"][
                    "provider_contacted"
                ],
                "formal_stock_backtest_authorized": data[
                    "formal_stock_backtest_authorized"
                ],
                "paper_authorized": data["paper"]["authorized"],
                "real_money_action_usd": data["real_money_action_usd"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
