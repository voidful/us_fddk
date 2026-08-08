# 短線個股第三十五輪：正式回測 release firewall 整合協議 v1.0

凍結時間：2026-08-08T15:15:19Z

狀態：`frozen_before_formal_provider_release_receipt`

## 目的

現有 Round18 formal readiness 在 `source_mode=provider` 且 base ledger 20/20、execution
16/16、RF 及政策均通過時，會把正式回測標成可執行；Round34 的 release／restatement
firewall 目前是獨立收據。若兩者不綁定，未來 provider package 可能繞過
`available_at`／as-known 驗收。本輪把 firewall receipt 變成正式入口的必要輸入。

## 正式 provider receipt 合約

repository 外、owner-only 的 `release_firewall.json` 必須精確包含：

`schema_version`、`source_mode`、`mode`、`as_known_integrity_passed`、
`provider_package_qualified`、`formal_backtest_authorized`、`package_binding_sha256`、
`release_ledger_sha256`、`release_receipt_chain_passed`、`source_record_count`、
`paper_authorized`、`paper_state`、`real_money_action_usd`。

只有以下條件同時成立，正式 18 道 gate 才可進入 provider 一次性回測候選：

1. `source_mode=provider`、`mode=as_known`；
2. as-known 完整、release ledger 與 restatement supersedes chain 已驗收；
3. provider package qualified，且 `package_binding_sha256` 等於 package 的
   `intake_receipt.json`／`execution_manifest.json` canonical binding；
4. release ledger 有非零 row receipt、`release_receipt_chain_passed=true`；
5. receipt 自身不授權 Paper 或實金。

合成控制可以測試欄位形狀，但永遠不能令 `formal_backtest_authorized=true`。

## 不可移動邊界

- 沒有 `--release-firewall` 或 receipt 缺失，provider formal readiness 直接拒收；
- `final_revised`、日後 restatement、錯誤 package binding、空 release ledger 或 Paper
  欄位非全現金均拒收；
- 不把 Round34 synthetic artifact 當 provider receipt，不下載或保存受限原始資料；
- 既有 18 道策略、成本、baseline、DSR／PBO、RF 及 D+1 規則不改；本輪只加必要前置閘門；
- 通過整合 gate 仍只代表可作一次 immutable formal run，並不代表策略勝出、Paper 或實金。

## 固定攻擊

`formal_release_firewall_required`、`formal_release_receipt_schema_invalid`、
`formal_release_mode_invalid`、`formal_release_as_known_invalid`、
`formal_release_package_binding_mismatch`、`formal_release_chain_invalid`、
`formal_release_decision_boundary_violation` 及 `formal_release_synthetic_substitution`
必須逐一拒收。

## 輸出及決策

本輪只輸出整合 validator 及 synthetic controls；正式 provider package、正式回測、短線
Paper 及實金均為 0。沒有新授權輸入時，現行實際 readiness 維持 formal **1/18**、
point-in-time **1/20**、Paper `all_cash`、實金 **US$0**。

本協議只作研究及專業資訊參考，不構成投資建議、回報預測或盈利保證。
