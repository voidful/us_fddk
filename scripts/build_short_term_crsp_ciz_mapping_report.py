from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from usfddk.crsp_ciz_mapping_validation import (  # noqa: E402
    run_crsp_ciz_mapping_validation,
)

VALIDATION = ROOT / "artifacts/short_term_crsp_ciz_mapping_validation.json"
SITE_DATA = ROOT / "site/data/short-term-crsp-ciz-mapping.json"
REPORT = ROOT / "docs/SHORT_TERM_CRSP_CIZ_MAPPING_REPORT.md"


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rendered = json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(rendered, encoding="utf-8")
    temporary.replace(path)


def _site_summary(data: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "round": 13,
        "status": data["status"],
        "headline": "CIZ 映射控制包 20/20、十二項攻擊全拒收；真實數據仍為 1/20",
        "evidence_as_of": data["evidence_as_of"],
        "protocol_integrity": data["protocol_integrity"]["passed"],
        "official_document_evidence": data["official_document_evidence"],
        "mapping_policy": data["mapping_policy"],
        "synthetic_control": {
            "mapping_completed": data["control"]["mapping_completed"],
            "gates_passed": data["control"]["ledger_gate_summary"]["passed"],
            "gates_total": data["control"]["ledger_gate_summary"]["total"],
            "provider_rows": False,
            "paper_authorized": False,
        },
        "attack_summary": data["attack_summary"],
        "attacks": [
            {
                "id": attack["id"],
                "label": attack["label"],
                "expected_error_code": attack["expected_error_code"],
                "observed_error_code": attack["observed_error_code"],
                "rejected": attack["rejected"],
            }
            for attack in data["attacks"]
        ],
        "actual_point_in_time_readiness": data["actual_point_in_time_readiness"],
        "authorized_provider_sample_received": False,
        "provider_qualified": False,
        "formal_stock_backtest_authorized": False,
        "formal_stock_backtest_completed": False,
        "strategy_rule_changed": False,
        "paper": data["paper"],
        "real_money_action_usd": 0,
        "next_action": data["next_action"],
    }


def _render_report(data: dict[str, Any]) -> str:
    attacks = "\n".join(
        "| {id} | {label} | `{expected}` | {status} |".format(
            id=attack["id"],
            label=attack["label"],
            expected=attack["expected_error_code"],
            status="拒收" if attack["rejected"] else "誤收",
        )
        for attack in data["attacks"]
    )
    direct = "、".join(data["mapping_policy"]["direct"])
    derived = "、".join(data["mapping_policy"]["deterministic_derived"])
    external = "、".join(data["mapping_policy"]["external_evidence_required"])
    prohibited = "、".join(data["mapping_policy"]["prohibited_inference"])
    missing = "、".join(
        data["official_document_evidence"]["not_verified_in_public_table_definition"]
    )
    return f"""# 美股短線高回報研究｜第十三輪 CRSP CIZ 映射報告

研究日期：2026-08-04　｜　狀態：**映射橋通過；供應商數據及策略仍未通過**

## 一頁結論

本輪沒有調整短線策略參數，亦沒有查詢 WRDS、下載付費數據或運行正式回測。研究先按
CRSP 現行 Flat File Format 2.0（CIZ）公開定義，凍結一個 fail-closed 轉換橋。合成
CIZ 控制包成功轉成既有八份 point-in-time 賬本並通過 **20/20**；十二項事前固定的
schema、公布時間、raw 價、歷史倒填及退市語義攻擊亦 **{data['attack_summary']['rejected']}/{data['attack_summary']['total']} 全數拒收**。

正確解讀是「轉換器能拒絕這十二類錯誤」，不是 CRSP／WRDS 已合格。真實數據仍為
**{data['actual_point_in_time_readiness']['passed']}/{data['actual_point_in_time_readiness']['total']}**，合法供應商樣本 0，正式 20 年逐股回測 0；短線 Paper 保持
全現金、0 成交、0 持倉，實金動作 **US$0**。

| 驗證層 | 結果 | 可以說甚麼 |
|---|---:|---|
| CIZ 合成映射 | 20/20 | 固定欄位可機械轉成八份賬本 |
| 映射攻擊 | {data['attack_summary']['rejected']}/{data['attack_summary']['total']} 拒收 | 十二類已知錯誤會 fail closed |
| 真實 CRSP／WRDS 包 | 1/20 | 只有事前凍結通過，尚未取得合法列 |
| 正式短線回測 | 0 | 不可由合成控制推升 |
| 短線 Paper／實金 | 全現金／US$0 | 繼續鎖定 |

## 今輪最重要發現

[WRDS 的現行格式公告](https://wrds-www.wharton.upenn.edu/pages/data-announcements/changes-to-crsp-data/)
說明 CIZ 已取代 legacy SIZ；因此轉換橋只接受 `CIZ_FF2`。WRDS 的
[2026 CIZ-to-SIZ macro](https://wrds-www.wharton.upenn.edu/pages/wrds-research/macros/crsp-ciztosiz-macro/)
公開展示 `crsp.dsf_v2`、`PERMNO`、`DlyCalDt`、`DlyRet`、`DlyPrc`、`DlyVol`，以及
按 `SecInfoStartDt/EndDt` 連接歷史 security information 的方式。

2026 年 [CRSP US Stock Databases Guide](https://index-website-frontend-prd.mif0286.eas.morningstar.com/docs/guide/crsp-us-stock-databases-guide-for-flat-file-format-2-0?isRdp=true)
列出：

- `StkIndMembership` 的 `MbrStartDt`／`MbrEndDt` 只描述在籍起訖，公開表格未列逐次
  announcement timestamp；所以生效日不能冒充公布時間。
- `DelistingDt` 是最後價格日期；`DelDlyDt` 是退市回報存入日線表的日期，慣例為
  退市後下一交易日。轉換器保留兩者角色，不把儲存日當退出日。
- `DelRetMissType` 明示退市回報可能缺失；缺 `DelRet` 時只能接受可追溯現金或換股
  代價，不能自動補 0。
- `DlyOpen/High/Low/Close/Vol` 是原始日線欄位；轉換器拒絕 adjusted OHLC，避免
  事後調整價污染 US$5 及流動性篩選。

## 固定欄位政策

| 類別 | 今輪固定內容 |
|---|---|
| 官方直接欄位 | {direct} |
| 決定性派生 | {derived} |
| 必須另有證據 | {external} |
| 禁止推算 | {prohibited} |

公開文件仍未驗證：{missing}。這些缺口不會因品牌、登入頁存在或合成測試而視為通過。

## 十二項事前攻擊

| # | 單一錯誤 | 指定拒收代碼 | 結果 |
|---|---|---|---:|
{attacks}

每次攻擊都重算被改 CSV 的列數及 SHA-256；因此結果不是由「檔案被改過」一個泛化錯誤
掩蓋。十二項均在 adapter 語義層按指定代碼停止，未流入八份正式賬本。

## 為何仍不能回測或買入

今輪控制包不含任何供應商列，不能回答 2006-08-01 至 2026-07-31 的 S&P 500 每日
成分、真正 announcement timestamp、退市回報缺失比例、收購付款完整度、停牌覆蓋及
授權邊界。`MbrStartDt`、`SecInfoStartDt` 或 `DelDlyDt` 都不能替代缺失證據。

取得合法小樣本後，仍須逐欄通過同一 adapter 及 20 道賬本閘門；正式包再須覆蓋固定
20 年、每日 495–510 隻成分及至少 99.5% 在籍價格／停牌。只有 20/20 才可按已凍結 v1
運行一次回測，並對照 QQQ、SPY、逐期成分等權及同股漂移，扣 10／25／50 bps，完成
分段、危機、Newey-West、PSR、全專案 DSR 及 PBO。

即使歷史經濟及統計門檻全數通過，短線 Paper 亦只可由全現金開始、不回填歷史成交，
並至少累積 252 個新增交易日及 12 次完整輪選再審。這不構成投資建議、供應商背書或
盈利保證。
"""


def main() -> int:
    data = run_crsp_ciz_mapping_validation(ROOT)
    _write_json(VALIDATION, data)
    _write_json(SITE_DATA, _site_summary(data))
    REPORT.write_text(_render_report(data), encoding="utf-8")
    print(
        json.dumps(
            {
                "status": data["status"],
                "control": data["control"]["ledger_gate_summary"],
                "attacks": data["attack_summary"],
                "actual_point_in_time_readiness": data[
                    "actual_point_in_time_readiness"
                ],
                "authorized_provider_sample_received": False,
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
