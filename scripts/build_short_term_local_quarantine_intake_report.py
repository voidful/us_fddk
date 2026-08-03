from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from usfddk.local_quarantine_intake_validation import (
    run_local_quarantine_intake_validation,
)

ROOT = Path(__file__).resolve().parents[1]
MACHINE_PATH = ROOT / "artifacts/short_term_local_quarantine_intake_validation.json"
SITE_PATH = ROOT / "site/data/short-term-local-quarantine-intake.json"
REPORT_PATH = ROOT / "docs/SHORT_TERM_LOCAL_QUARANTINE_INTAKE_REPORT.md"


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _site_summary(data: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": data["schema_version"],
        "round": data["research_round"],
        "intake_version": data["intake_version"],
        "status": data["status"],
        "evidence_as_of": data["evidence_as_of"],
        "headline": "本地隔離匯入合成 16/16；真實匯入仍為 1/16",
        "gap_closed": data["gap_closed"],
        "synthetic_gate_summary": data["synthetic_control"]["gate_summary"],
        "synthetic_gates": data["synthetic_control"]["gates"],
        "synthetic_point_in_time_gate_summary": data["synthetic_control"][
            "point_in_time_gate_summary"
        ],
        "synthetic_extension_gate_summary": data["synthetic_control"][
            "extension_gate_summary"
        ],
        "synthetic_counts": data["synthetic_control"]["counts"],
        "synthetic_private_permissions": data["synthetic_control"][
            "private_permissions"
        ],
        "attack_summary": data["attack_summary"],
        "attacks": data["attacks"],
        "actual_local_intake": data["actual_local_intake"],
        "actual_document_handoff": data["actual_document_handoff"],
        "actual_point_in_time_readiness": data[
            "actual_point_in_time_readiness"
        ],
        "explicit_external_paths_provided": data[
            "explicit_external_paths_provided"
        ],
        "provider_mode_run_count": data["provider_mode_run_count"],
        "authorized_provider_response_received": data[
            "authorized_provider_response_received"
        ],
        "authorized_provider_sample_received": data[
            "authorized_provider_sample_received"
        ],
        "formal_stock_backtest_input_ready": data[
            "formal_stock_backtest_input_ready"
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


def _render_report(data: dict[str, Any]) -> str:
    control = data["synthetic_control"]
    gates = control["gate_summary"]
    attacks = data["attack_summary"]
    actual = data["actual_local_intake"]
    document = data["actual_document_handoff"]
    readiness = data["actual_point_in_time_readiness"]
    counts = control["counts"]
    return f"""# 美股短線高回報研究｜第十七輪本地隔離匯入報告

研究日期：2026-08-04　｜　狀態：provider-mode bridge 已備；真實輸入尚未提供

## 一頁結論

第十五輪 execution extension 的輸出 status 固定為
`synthetic_execution_extension_built`，不能誠實標示未來的授權供應商包。本輪沒有改寫
第十五輪 bridge 或其 16/16 收據，而是另立 provider-mode bridge：

- 合成控制：`synthetic_local_quarantine_extension_built`；
- 正式授權模式：`authorized_provider_local_quarantine_extension_built`。

新的本地隔離匯入合成控制通過 **{gates['passed']}/{gates['total']}**，事前固定的路徑、
symlink、文件 hash、模式、身份、授權、時間、CIZ 收據、前視成分、QQQ 缺日、status
冒充及檔案權限攻擊 **{attacks['rejected']}/{attacks['total']} 全數拒收**。

這不是真實數據通過。現時沒有四個明確外部路徑，provider-mode 運行 0 次；真實匯入只過
事前凍結 **{actual['passed']}/{actual['total']}**，文件仍是
**{document['passed']}/{document['total']}**，逐股數據仍是
**{readiness['passed']}/{readiness['total']}**。正式 20 年逐股回測 0 次，短線 Paper
維持全現金、0 成交、0 持倉，實金動作 US$0。

## 為何不能直接沿用第十五輪

第十五輪的任務是證明合成 CIZ bridge 能否封閉派息 pay-date、252 日歷史、移除後成交及
QQQ／SPY 同步四項缺口，因此 synthetic status 是正確的測試標示。真實 provider package
若沿用同一 status，網站及下游程式便無法分辨「合成控制」與「授權市場列」。

本輪以新 manifest status 分開兩者，同時鎖定第十五輪 bridge 的 SHA-256；舊檔案、舊
manifest、舊報告及舊攻擊結果完全不改。

## 正式 CLI 邊界

只有使用者明確提供 repository 外四個絕對路徑時，才可運行：

```bash
python scripts/validate_short_term_local_quarantine_intake.py \\
  --response /private/input/provider-response-envelope.json \\
  --ciz-bundle /private/input/crsp-ciz-bundle \\
  --execution-overlay /private/input/qqq-spy-overlay \\
  --output /private/output/validated-local-package
```

CLI 不接受 synthetic mode，不掃描磁碟，不登入或下載，不覆寫目的地。輸出在同一父目錄
完成 staging 後才原子 rename；目錄權限為 0700、檔案為 0600。公開收據只含匯總，真正
response、合約、報價、原始列及衍生 package 不得加入 Git、網站或 Action artifact。

## 十六道合成匯入控制

| # | 閘門 | 結果 | 證據 |
|---|---|---|---|
{_gate_rows(data)}

合成 fixture 只有 {counts['signals']} 個完整月末訊號、
{counts['signal_eligibility_rows']} 個候選資格、
{counts['removal_execution_windows']} 個移除窗口及 {counts['benchmark_rows']} 列
QQQ／SPY 行情。這些數字只驗證工程，不會加入策略回報或 Paper 樣本。

## 十六項固定攻擊

| # | 單一錯誤 | 指定拒收代碼 | 結果 |
|---|---|---|---|
{_attack_rows(data)}

第 12–14 項在任何實作前核對既有 bridge 後，以勘誤固定為程式實際錯誤代碼；攻擊內容、
門檻及停止規則沒有改變。每項攻擊只保留一個語義錯誤，不以 generic hash 失敗遮蓋。

## 通過後仍不可自動交易

真實 provider-mode 16/16 只會產生
`formal_stock_backtest_input_ready=true`，允許另一步運行一次凍結 v1 正式回測。它不會：

1. 自動運行或調整 12–1／6–1／3–1／1 個月訊號；
2. 改動 Top-10、30% 行業上限、US$5、US$20m 或 10／25／50 bps；
3. 刪除退市、收購、停牌或失敗公司；
4. 改用較弱 QQQ／SPY／等權／漂移 baseline；
5. 建立或回填 Paper；
6. 作任何實金動作。

正式策略仍須通過固定 20 年、前後十年、滾動窗、危機段、NW、PSR、全專案 DSR、PBO、
成本及最大跌幅。全部通過後，短線 Paper 仍須由全現金開始累積 252 個新增交易日及
12 次完成重新平衡，不能回填漂亮歷史。

## 決策

下一個有效行動仍是由使用者明確提供四個 repository 外路徑。沒有這些輸入時，不掃描、
不猜測、不運行 provider mode。合成 16/16 不構成供應商背書、投資建議或盈利保證。
"""


def main() -> None:
    data = run_local_quarantine_intake_validation(ROOT)
    _write_json(MACHINE_PATH, data)
    _write_json(SITE_PATH, _site_summary(data))
    REPORT_PATH.write_text(_render_report(data), encoding="utf-8")
    print(
        json.dumps(
            {
                "status": data["status"],
                "synthetic_control": data["synthetic_control"]["gate_summary"],
                "attacks": data["attack_summary"],
                "actual_local_intake": data["actual_local_intake"],
                "actual_document_handoff": data["actual_document_handoff"],
                "true_readiness": data["actual_point_in_time_readiness"],
                "provider_mode_run_count": data["provider_mode_run_count"],
                "formal_stock_backtest_input_ready": data[
                    "formal_stock_backtest_input_ready"
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
