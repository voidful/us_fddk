# 短線個股第三十四輪：release／restatement as-known firewall 協議 v1.0

凍結時間：2026-08-08T15:00:35Z

狀態：`frozen_before_release_ledger_fixture`

## 目的

現有 point-in-time ledger 已要求 `announced_at`、`known_at`、有效區間、退市結果及逐檔
SHA-256，但仍需要一條獨立的 **release availability** 鏈。CRSP 官方資料說明可能提供
每日期的最新或 restated 檔；如果回測直接讀最後一版，便會把日後修訂倒灌到當時不可知的
訊號日。本輪補一個只驗證「哪一版在當時已可取得」的 firewall，不引入任何市場數值。

## 不可移動邊界

- 只接受明確 UTC offset 的 `available_at`；不能以 `data_cutoff`、檔名日期、下載日或
  effective date 冒充可知時間。
- `as_known` 回測只可使用 `available_at <= requested_as_of` 的 release；任何日後才發布的
  restatement 都必須拒收，不能以「最終正確」合理化。
- `supersedes_release_id` 必須指向同一 source、較早 availability 的 release；不可把
  restatement 蓋掉原始版本而不保留鏈。
- 每一筆 data row 必須連到 release_id、source_record_id 及檔案 SHA／列數收據；缺列、
  重複 row 或 release／source 不匹配即停止。
- `final_revised` 只可作描述性資料稽核，不能授權正式策略回測；正式 20 年策略必須
  使用 `as_known`。
- 本輪只使用 synthetic fixture 驗證 validator；不登入、不下載、不保存 CRSP／LSEG 原始
  檔，不產生選股名單或交易。

## 固定 schema

每個 release record 必須包含：

`provider`、`source_id`、`release_id`、`available_at`、`data_cutoff`、`is_restatement`、
`supersedes_release_id`、`content_sha256`、`row_count`。

每個 provenance row 必須包含：

`source_id`、`release_id`、`source_record_id`、`observation_date`、`effective_at`。

請求 envelope 必須固定：`mode`（只接受 `as_known` 或描述性 `final_revised`）、
`requested_as_of`、`selected_release_ids`、`rows` 及 `release_ledger`。所有日期／時間均須
ISO-8601；時間必須含 `Z` 或明確 `+/-HH:MM`。

## 固定控制及攻擊

1. 本協議、Round33 provider evidence protocol、既有 point-in-time contract 及父收據 SHA
   必須吻合；
2. release／row schema、欄位集合及 timestamp offset 必須完整；
3. release id 不可重複，row 必須逐筆連到已存在 release；
4. `available_at <= requested_as_of` 才可入選 `as_known`；
5. 日後 available 的 restatement 不可回看污染歷史；
6. supersedes chain 必須同 source、向後且無循環；
7. content SHA、row count 及 row source_record_id 必須與收據一致；
8. `final_revised` 不可冒充正式 strategy input；
9. firewall 通過不提高 provider readiness、不得啟動回測、Paper 或實金。

指定攻擊代碼：`release_protocol_mismatch`、`release_schema_mismatch`、
`release_id_duplicate`、`future_release_leakage`、`restatement_substitution`、
`supersedes_chain_invalid`、`release_receipt_mismatch`、
`final_revised_strategy_substitution`、`release_decision_boundary_violation`。

## 固定決策

本輪只可輸出 validator 控制結果。正式 provider package 仍為 `false`，formal readiness
仍為 `1/18`，point-in-time readiness 仍為 `1/20`；strategy run `0`、短線 Paper
`all_cash`、實金動作 `US$0`。即使 synthetic fixture 9/9 通過，也不能代表任何供應商已
交付可用資料。

## 輸出

- `artifacts/short_term_restatement_firewall_protocol_receipt.json`；
- `artifacts/short_term_restatement_firewall_validation.json`；
- `site/data/short-term-restatement-firewall.json`；
- `docs/SHORT_TERM_RESTATEMENT_FIREWALL_REPORT.md`。

本協議只作研究及專業資訊參考，不構成數據供應商背書、投資建議、回報預測或盈利保證。
