# 短線個股第三十四輪：release／restatement as-known firewall 報告

測試時間：2026-08-08
結果：synthetic fixture 控制 **9/9**、攻擊 **9/9**；正式 provider package **0**

## 結論先行

現有 point-in-time ledger 已有 `announced_at`／`known_at` 及退市欄位；本輪再補上
release availability 鏈，防止把日後才發布的 CRSP restatement 倒灌到較早訊號日。
測試 fixture 固定一個 2026-07-01 data cut：v1 在 2026-07-02 可取得，v2 restatement
在 2026-07-15 才可取得。對 2026-07-05 的 `as_known` 請求只接受 v1，並保留 v2 的
supersedes 關係。

這是資料防漏 validator 的工程證據，不是實際供應商資料或策略結果；不提高 readiness，
不產生選股名單、不運行回測、不啟動 Paper。

## 已驗證的邏輯

| 控制 | 結果 | 專業含義 |
|---|---:|---|
| protocol／父收據 SHA | 通過 | release firewall 不能脫離既有 point-in-time contract |
| exact release／row schema | 通過 | 不接受沒有 UTC offset 或缺少 source row link 的資料 |
| availability cutoff | 通過 | 只有 `available_at <= requested_as_of` 才能進入 as-known |
| restatement chain | 通過 | v2 必須指向同 source、較早 availability 的 v1 |
| row count／content receipt | 通過 | release receipt、選入 row 數及 source_record_id 對得上 |
| final revised isolation | 通過 | 可作描述性稽核，但不得變成正式 strategy input |
| decision boundary | 通過 | package、正式回測、Paper 及實金欄位維持關閉 |

## 9/9 攻擊拒收

`release_protocol_mismatch`、`release_schema_mismatch`、`release_id_duplicate`、
`future_release_leakage`、`restatement_substitution`、`supersedes_chain_invalid`、
`release_receipt_mismatch`、`final_revised_strategy_substitution` 及
`release_decision_boundary_violation` 全部按指定語義拒收。

特別重要的是：

- 選入 2026-07-15 才出現的 v2 restatement，對 2026-07-05 as-known 請求直接拒收；
- 把 `final_revised` 結果標記成 strategy input，直接拒收；
- 改 Paper 狀態、protocol hash 或 release receipt，不能繞過決策邊界。

## 現行 readiness 與下一步

- 正式 readiness：**1/18**；point-in-time：**1/20**；
- provider package：`false`；正式 strategy run：`0`；
- short-term Paper：`all_cash`；實金動作：**US$0**。

取得授權 provider package 後，必須把每一份實際 export、release availability、row-level
SHA／列數及 restatement supersedes 鏈接入本 firewall，再按原定 20/20、execution 16/16、
RF 完整及正式 18/18 門檻驗收。synthetic 9/9 不能代替任何一項真實資料證據。

本報告只作研究及專業資訊參考，不構成投資建議、回報預測或盈利保證。
