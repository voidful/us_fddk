from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from usfddk.form4_admission_collection import _sanitize_public_receipt
from usfddk.form4_admission_feasibility import (
    EXPECTED_SCHEMA_AMENDMENT_RECEIPT_SHA256,
    EXPECTED_SCHEMA_AMENDMENT_SHA256,
    FIXED_QUARTERS,
    FORM4_ADMISSION_GATES,
    SCHEMA_AMENDMENT_FROZEN_AT,
    SCHEMA_VERSION,
)

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "artifacts/short_term_form4_admission_feasibility_validation.json"
SITE_DATA = ROOT / "site/data/short-term-form4-admission-feasibility.json"
REPORT = ROOT / "docs/SHORT_TERM_FORM4_ADMISSION_FEASIBILITY_REPORT.md"

EXPECTED_TOP_LEVEL_KEYS = {
    "schema_version",
    "protocol_sha256",
    "protocol_receipt_sha256",
    "frozen_at",
    "status",
    "fixed_quarters",
    "sample_count",
    "admission_controls",
    "attack_results",
    "stop_reasons",
    "state_boundary",
    "private_manifest_sha256",
}
EXPECTED_CONTROL_KEYS = {
    "all_passed",
    "candidate_selection_authorized",
    "gates",
    "passed",
    "strategy_run_authorized",
    "total",
}
EXPECTED_ATTACK_KEYS = {
    "collection_stop_receipt",
    "error_code",
    "identifier_detail_included",
}
EXPECTED_STATE_KEYS = {
    "authorized_real_form4_rows",
    "candidate_selection_count",
    "evidence_mode",
    "form4_specific_admission",
    "paper",
    "performance_present",
    "real_money_action_usd",
    "strategy_run_count",
    "today_action",
}
COLLECTION_STOP_RECEIPT_KEYS = {
    "admission_core_sha256",
    "canonicalization",
    "cold_replay_completed",
    "complete_submission_requests",
    "completed_http_requests",
    "failure_phase",
    "post_fetch_local_validation_failures",
    "private_manifest_sha256",
    "receipt_sha256",
    "schema_version",
    "stop_reason",
}
EXPECTED_STATUS = "stopped_no_admission_claim"
EXPECTED_STOP_REASON = "form4_feasibility_daily_index_missing_or_ambiguous"
EXPECTED_TRUE_GATE_IDS = {"01", "04"}
COLLECTION_STOP_SCHEMA_VERSION = "us_fddk.short_term_form4_collection_stop.v1"
SHA256 = re.compile(r"^[0-9a-f]{64}$")

GATE_LABELS = {
    "versioned_parent_lineage_verified": "父協議、修訂及收據雜湊鏈一致",
    "sec_exact_use_terms_verified": "SEC 精確用途、存取及完整嘗試紀錄已驗證",
    "encrypted_private_quarantine_verified": "加密私有隔離及獨立證據已驗證",
    "source_scope_exact": "來源只限 SEC Form 4／4-A",
    "filing_denominator_complete": "完整申報分母已重播",
    "as_filed_content_complete": "全部 as-filed 內容及收據齊全",
    "fixed_period_coverage_verified": "2005Q4 暖機至 2026Q2 固定期間完整",
    "known_at_evidence_complete": "歷史 known-at 證據完整",
    "known_at_clock_verified": "收市決策及下一開市時鐘已驗證",
    "version_amendment_chain_verified": "4/A 修訂鏈唯一且不可回填",
    "form4_semantics_verified": "Form 4 交易語意及註腳完整",
    "economic_event_dedupe_verified": "共同持有及同一經濟交易已去重",
    "pit_security_universe_verified": "當時可知證券與股份池已驗證",
    "pit_market_execution_verified": "當時可知行情及公司行動已驗證",
    "independent_mutation_attacks_passed": "獨立單欄變異攻擊全部拒收",
    "authorized_real_sample_independently_replayed": "獲授權真實細樣本已獨立重播",
}
REASON_LABELS = {
    "frozen_parent_lineage_hashes_verified": "凍結父鏈雜湊一致",
    "project_wide_exact_use_and_complete_attempt_ledger_not_established": "尚未建立全專案精確用途及完整嘗試紀錄",
    "independent_encrypted_quarantine_evidence_not_established": "尚未建立獨立加密隔離證據",
    "source_scope_sec_form_4_and_exact_form_types_verified": "來源及表格類型精確",
    "full_filing_denominator_not_replayed": "未重播完整申報分母",
    "full_denominator_as_filed_content_not_replayed": "未重播完整分母的 as-filed 內容",
    "fixed_2005q4_through_2026q2_coverage_not_replayed": "未重播完整固定期間",
    "external_historical_known_at_evidence_absent": "欠缺外部歷史 known-at 證據",
    "decision_and_trade_clock_mapping_not_executed": "沒有執行決策及落盤時鐘映射",
    "full_denominator_version_chain_not_replayed": "未重播完整版本及修訂鏈",
    "full_denominator_semantics_not_replayed": "未重播完整分母的交易語意",
    "economic_event_deduplication_not_replayed": "未重播經濟事件去重",
    "pit_security_universe_not_replayed": "未重播當時可知證券與股份池",
    "pit_market_execution_inputs_not_replayed": "未重播當時可知行情及執行輸入",
    "local_fixture_attacks_are_not_full_independent_admission_attacks": "本地 fixture 攻擊不是完整獨立准入攻擊",
    "real_sample_not_authorized_or_replayed": "真實細樣本未獲准入接受",
    "authorized_real_sample_independently_replayed": "獲授權真實細樣本已獨立重播",
}
EXPECTED_GATE_REASONS = {
    "01": "frozen_parent_lineage_hashes_verified",
    "02": "project_wide_exact_use_and_complete_attempt_ledger_not_established",
    "03": "independent_encrypted_quarantine_evidence_not_established",
    "04": "source_scope_sec_form_4_and_exact_form_types_verified",
    "05": "full_filing_denominator_not_replayed",
    "06": "full_denominator_as_filed_content_not_replayed",
    "07": "fixed_2005q4_through_2026q2_coverage_not_replayed",
    "08": "external_historical_known_at_evidence_absent",
    "09": "decision_and_trade_clock_mapping_not_executed",
    "10": "full_denominator_version_chain_not_replayed",
    "11": "full_denominator_semantics_not_replayed",
    "12": "economic_event_deduplication_not_replayed",
    "13": "pit_security_universe_not_replayed",
    "14": "pit_market_execution_inputs_not_replayed",
    "15": "local_fixture_attacks_are_not_full_independent_admission_attacks",
    "16": "real_sample_not_authorized_or_replayed",
}
STOP_REASON_LABELS = {
    "form4_feasibility_daily_index_missing_or_ambiguous": (
        "SEC 每日 Form index 未能為全部固定樣本提供唯一、可重播的匹配列"
    ),
    "form4_admission_below_16_of_16": "准入門檻低於 16/16",
}


def _canonical_bytes(payload: dict[str, Any]) -> bytes:
    return (
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def canonical_sha256(payload: dict[str, Any]) -> str:
    rendered = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(rendered).hexdigest()


def admission_core_payload(payload: dict[str, Any]) -> dict[str, Any]:
    core = dict(payload)
    attacks = dict(payload.get("attack_results", {}))
    attacks.pop("collection_stop_receipt", None)
    core["attack_results"] = attacks
    return core


def _validate_collection_stop_receipt(payload: dict[str, Any]) -> None:
    attacks = payload.get("attack_results")
    if not isinstance(attacks, dict) or set(attacks) != EXPECTED_ATTACK_KEYS:
        raise ValueError("Round 42 attack result schema drifted")
    if (
        attacks.get("error_code") != EXPECTED_STOP_REASON
        or attacks.get("identifier_detail_included") is not False
    ):
        raise ValueError("Round 42 attack result state drifted")
    receipt = attacks.get("collection_stop_receipt")
    if not isinstance(receipt, dict) or set(receipt) != COLLECTION_STOP_RECEIPT_KEYS:
        raise ValueError("Round 42 collection-stop receipt schema drifted")
    if any(
        not isinstance(receipt.get(key), str) or SHA256.fullmatch(receipt[key]) is None
        for key in (
            "admission_core_sha256",
            "private_manifest_sha256",
            "receipt_sha256",
        )
    ):
        raise ValueError("Round 42 collection-stop receipt hash drifted")
    if (
        receipt.get("schema_version") != COLLECTION_STOP_SCHEMA_VERSION
        or receipt.get("canonicalization")
        != "json_utf8_sort_keys_compact_no_nan_v1"
        or receipt.get("completed_http_requests") != 5
        or receipt.get("post_fetch_local_validation_failures") != 1
        or receipt.get("complete_submission_requests") != 0
        or receipt.get("cold_replay_completed") is not False
        or receipt.get("failure_phase") != "post_fetch_validation_failed"
        or receipt.get("stop_reason") != EXPECTED_STOP_REASON
        or receipt.get("private_manifest_sha256")
        != payload.get("private_manifest_sha256")
    ):
        raise ValueError("Round 42 collection-stop receipt facts drifted")
    expected_core_hash = canonical_sha256(admission_core_payload(payload))
    if receipt["admission_core_sha256"] != expected_core_hash:
        raise ValueError("Round 42 admission core binding drifted")
    receipt_body = dict(receipt)
    observed_receipt_hash = receipt_body.pop("receipt_sha256")
    if observed_receipt_hash != canonical_sha256(receipt_body):
        raise ValueError("Round 42 collection-stop receipt self-hash drifted")


def validate_public_payload(payload: dict[str, Any]) -> None:
    _sanitize_public_receipt(payload)
    if set(payload) != EXPECTED_TOP_LEVEL_KEYS:
        raise ValueError("Round 42 public receipt top-level schema drifted")
    if (
        payload.get("schema_version") != SCHEMA_VERSION
        or payload.get("protocol_sha256") != EXPECTED_SCHEMA_AMENDMENT_SHA256
        or payload.get("protocol_receipt_sha256")
        != EXPECTED_SCHEMA_AMENDMENT_RECEIPT_SHA256
        or payload.get("frozen_at") != SCHEMA_AMENDMENT_FROZEN_AT
        or payload.get("status") != EXPECTED_STATUS
        or payload.get("fixed_quarters") != list(FIXED_QUARTERS)
        or payload.get("sample_count") != 12
        or payload.get("stop_reasons") != [EXPECTED_STOP_REASON]
    ):
        raise ValueError("Round 42 frozen public identity drifted")
    private_manifest_sha256 = payload.get("private_manifest_sha256")
    if (
        not isinstance(private_manifest_sha256, str)
        or SHA256.fullmatch(private_manifest_sha256) is None
    ):
        raise ValueError("Round 42 private manifest commitment drifted")

    controls = payload.get("admission_controls")
    if not isinstance(controls, dict) or set(controls) != EXPECTED_CONTROL_KEYS:
        raise ValueError("Round 42 admission control schema drifted")
    gates = controls.get("gates")
    if not isinstance(gates, list) or len(gates) != 16:
        raise ValueError("Round 42 admission must retain all 16 gates")
    for gate, (expected_id, expected_name) in zip(
        gates, FORM4_ADMISSION_GATES, strict=True
    ):
        if not isinstance(gate, dict) or gate != {
            "id": expected_id,
            "name": expected_name,
            "passed": expected_id in EXPECTED_TRUE_GATE_IDS,
            "reason": EXPECTED_GATE_REASONS[expected_id],
        }:
            raise ValueError("Round 42 admission gate identity or state drifted")
    if (
        controls.get("passed") != 2
        or controls.get("total") != 16
        or controls.get("all_passed") is not False
        or controls.get("candidate_selection_authorized") is not False
        or controls.get("strategy_run_authorized") is not False
    ):
        raise ValueError("Round 42 admission summary drifted")

    state = payload.get("state_boundary")
    if not isinstance(state, dict) or set(state) != EXPECTED_STATE_KEYS:
        raise ValueError("Round 42 state boundary schema drifted")
    if state != {
        "evidence_mode": "authorized_real_sample",
        "authorized_real_form4_rows": 0,
        "form4_specific_admission": {
            "passed": 2,
            "total": 16,
            "all_passed": False,
        },
        "candidate_selection_count": 0,
        "strategy_run_count": 0,
        "performance_present": False,
        "paper": {
            "authorized": False,
            "state": "all_cash",
            "backfilled_trades": 0,
            "positions": [],
        },
        "real_money_action_usd": 0,
        "today_action": "今天不下單",
    }:
        raise ValueError("Round 42 strategy, Paper, or real-money boundary drifted")
    _validate_collection_stop_receipt(payload)


def load_public_payload() -> tuple[dict[str, Any], bytes]:
    source_bytes = ARTIFACT.read_bytes()
    payload = json.loads(source_bytes)
    if not isinstance(payload, dict):
        raise ValueError("Round 42 public receipt must be an object")
    validate_public_payload(payload)
    if source_bytes != _canonical_bytes(payload):
        raise ValueError("Round 42 public receipt is not canonical JSON")
    return payload, source_bytes


def _gate_table(payload: dict[str, Any]) -> str:
    rows = [
        "| # | Form 4 准入門檻 | 結果 | 公開判讀 |",
        "|---:|---|---|---|",
    ]
    for gate in payload["admission_controls"]["gates"]:
        rows.append(
            f"| {gate['id']} | {GATE_LABELS[gate['name']]} | "
            f"{'**通過**' if gate['passed'] else '未通過'} | "
            f"{REASON_LABELS[gate['reason']]} |"
        )
    return "\n".join(rows)


def _stop_reason_list(payload: dict[str, Any]) -> str:
    return "\n".join(
        f"- `{code}`：{STOP_REASON_LABELS.get(code, '固定停止碼已封存')}。"
        for code in payload["stop_reasons"]
    )


def render_report(payload: dict[str, Any]) -> str:
    validate_public_payload(payload)
    controls = payload["admission_controls"]
    state = payload["state_boundary"]
    collection = payload["attack_results"]["collection_stop_receipt"]
    cold_replay_state = "已完成" if collection["cold_replay_completed"] else "未完成"
    quarters = "／".join(payload["fixed_quarters"])
    return f"""# 美股短線第 42 輪：SEC Form 4 准入可行性報告

## 結論先行

第 42 輪按事前凍結規則，在 **{quarters}** 三個固定季度取得
**{payload['sample_count']} 份** Form 4／4-A 細樣本。Form 4 專屬准入只通過
**{controls['passed']}/{controls['total']}**，結果為 **停止且不作准入聲稱**；不會因部分工程證據
改寫門檻、改抽樣本或產生選股。

收集程序精確停在 **{collection['completed_http_requests']} 個已完成 HTTP request** 之後的
**{collection['post_fetch_local_validation_failures']} 次 post-fetch 本地驗證失敗**；complete-submission
request 為 **{collection['complete_submission_requests']}**，cold replay **{cold_replay_state}**。因此不能寫成
真實細樣本已成功重播。

停止原因是：

{_stop_reason_list(payload)}

這 {payload['sample_count']} 份固定細樣本不是 {payload['sample_count']} 隻股票，也不是可交易事件或推薦名單。
本輪沒有建立 20 年 filing／known-at 完整分母，沒有計算任何回報、風險或基準比較數值。
候選選擇 **{state['candidate_selection_count']}**、策略運行 **{state['strategy_run_count']}**、
回報結果 **0**。Paper Trading（模擬交易）未授權並維持**全現金**、持倉 0、不可回填，
實金動作 **US$0**。**今天不下單。**

## 一目了然

| 項目 | 已驗證狀態 | 不可推論 |
|---|---|---|
| 固定季度 | {quarters} | 不代表 2006–2026 完整覆蓋 |
| 固定細樣本 | {payload['sample_count']} 份 | 不代表股票名單、事件分母或選股勝率 |
| Form 4 准入 | {controls['passed']}/{controls['total']} | 低於 16/16 不准建立候選或策略 |
| 收集／重播 | {collection['completed_http_requests']} 個 HTTP request 完成；{collection['post_fetch_local_validation_failures']} 次本地驗證失敗；cold replay {cold_replay_state} | 不代表真實細樣本已成功重播 |
| complete submission | {collection['complete_submission_requests']} 次 request | 沒有 as-filed complete-submission 重播證據 |
| 20 年 known-at | 未驗證 | SEC accepted time 或 nightly index 日期不能冒充歷史已知時間 |
| 動態選擇 | 停用 | 不產生買入、沽出、持倉或落盤指示 |
| Paper／實金 | 全現金／US$0 | 沒有 Paper 成交或實金授權 |

## 十六項 Form 4 准入門檻

{_gate_table(payload)}

兩項通過只表示父協議雜湊鏈及 SEC Form 4／4-A 來源範圍精確。其餘十四項沒有以缺失
資料、推測時間或較寬規則補值；任何一項未通過，准入都必須停止。

## 停止原因與 known-at 邊界

本次固定樣本未能在 SEC 每日 Form index 中全部得到唯一匹配，因此不能把後來下載到的
季度資料或 complete submission 倒填成當時已知。nightly index 只屬日級 archive evidence，
不是精確公開時間；SEC accepted time 也不能單獨充當 known-at。本輪因此沒有映射收市決策
或下一開市落盤時鐘。

程序在第 {collection['completed_http_requests']} 個已完成 HTTP request 後才於本地驗證停止；這是一項 post-fetch validation
failure，不是網路 request 失敗。停止後 complete-submission request 為
{collection['complete_submission_requests']}，cold replay {cold_replay_state}；所有後續階段均維持 0。

`P` 在 SEC Form 4 的語意是「公開市場或私人購買」，並不等於已證實的公開市場買入。
「企業家」也不是 SEC 法定申報身份；只能按 Section 16 董事、高級人員及逾 10% 股東等
可驗證角色處理，不能按知名度、姓名或事後結果建立人物權重。

## 私隱、研究與交易邊界

公開收據只保留三個固定季度、總樣本數、十六項門檻、停止碼、狀態邊界及私有 manifest
的整體 SHA-256 承諾。它不包含人物、CIK、accession、公司、股票代號、文件位置、原文或
逐筆交易資料。私有樣本不會流入 Git、CI 或網站內容。

Congress PTR 仍是分離來源，未獲本專案精確用途書面准許前不收集、不選股。公開披露
Phase 1 仍為 2/20；Round 42 細樣本不能替它補成 20/20，也不授權策略、Paper 或實金。

本報告只作研究及專業資訊參考，不構成投資或法律建議，不保證盈利。

## 可重播公開檔案

- `artifacts/short_term_form4_admission_feasibility_validation.json`
- `site/data/short-term-form4-admission-feasibility.json`
- `docs/SHORT_TERM_FORM4_ADMISSION_FEASIBILITY_PROTOCOL.md`
- `docs/SHORT_TERM_FORM4_ADMISSION_FEASIBILITY_SCHEMA_AMENDMENT_V1_1.md`
"""


def main() -> int:
    payload, source_bytes = load_public_payload()
    SITE_DATA.parent.mkdir(parents=True, exist_ok=True)
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    SITE_DATA.write_bytes(source_bytes)
    REPORT.write_text(render_report(payload), encoding="utf-8")
    print(
        json.dumps(
            {
                "status": payload["status"],
                "sample_count": payload["sample_count"],
                "admission": (
                    f"{payload['admission_controls']['passed']}/"
                    f"{payload['admission_controls']['total']}"
                ),
                "stop_reasons": payload["stop_reasons"],
                "candidate_selection_count": 0,
                "strategy_run_count": 0,
                "paper_state": "all_cash",
                "real_money_action_usd": 0,
                "today_action": "今天不下單",
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
