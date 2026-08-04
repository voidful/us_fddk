# 美股短線第 27 輪：排序單調性與隨機 placebo 反證報告

生成日期：2026-08-04
研究角色：現時 survivor cohort 的排序結構反證；不是最新買入名單、Paper 或實金指令。

## 執行摘要

本輪在任何新排序回報前先以 commit `b0c7978` 凍結兩個 universe、
三分組、八假說 family、20 組隨機 placebo、兩個 seed、QQQ 升跌市及 46-event 尾部壓力。
原 905 個事件全部覆蓋，父協議沒有縮樣本或 repair。
這些仍是第 24–26 輪已見的同一批事件，不是獨立未見確認。

結果不是由高至低的單調階梯：

- eligible 的 top-middle 為 **+0.516 個百分點**、NW t
  **2.57**，但 middle-bottom 反為
  **-0.145 個百分點**、t **-0.83**；
- complete 的 top-middle 為 **+0.400 個百分點**、t
  **2.30**，middle-bottom 同樣反為
  **-0.149 個百分點**、t **-0.87**；
- eligible／complete top-bottom 的 NW t 只有
  **1.46／1.09**；
- rank IC 的 NW t 只有 **1.01／
  1.46**；
- 完整股池真實 top-bottom t **1.09**，低於最強 placebo
  **P14 的
  1.22**；
- 未來 QQQ 下跌時，eligible／complete top-bottom 平均為
  **-0.647 個百分點／
  -0.183 個百分點**，兩者均為負。

十四項事前門檻只過 **5/14**。
高段相對中段有局部線索，但底段反彈、完整股池、rank IC、多重校正、placebo、下跌市及
尾部均不支持把它寫成穩健排序 alpha。正式就緒仍為 **1/18**、point-in-time **1/20**、
正式策略運行 **0 次**、短線 Paper 全現金、持倉 **0**、實金動作 **US$0**。

## 凍結輸入與可重播性

| 項目 | 結果 |
|---|---:|
| 原始／本輪共同事件 | 905 / 905 |
| 訊號日期 | 2006-08-04 至 2026-07-02 |
| eligible 數目最少／中位／最多 | 7 / 17 / 25 |
| complete 三分組大小 | 9 / 8 / 8 |
| 最大回報重建誤差 | 0.000e+00 |
| bucket assignment SHA-256 | `0f1512ccc893f554028b77de85af146e53333e1badd528fb00089878d49e8ffd` |
| 控制／攻擊 | 23/23 / 23/23 拒收 |

所有股票仍是 2026 現時代號，沒有修復歷史成分、永久 ID、退市／收購或退出經濟。

## 三分組回報水平

| Universe | 三分組 | 平均 20 日 net return | 中位 20 日 net return |
|---|---|---:|---:|
| eligible | top | 1.42% | 1.92% |
| eligible | middle | 0.91% | 1.31% |
| eligible | bottom | 1.05% | 1.56% |
| complete | top | 1.42% | 2.03% |
| complete | middle | 1.02% | 1.48% |
| complete | bottom | 1.17% | 1.53% |

每段都是全額投資、等權及 20 bps round trip；表格只展示固定事件 sleeve 的平均／中位
20 日 net return，不可把 top-bottom 診斷當成實際可沽空策略。

## 八假說共同 family

| 固定比較 | 平均值 | NW t | 普通 p | Holm p | 共同 max-t p | 前半 | 後半 |
|---|---:|---:|---:|---:|---:|---:|---:|
| eligible_top_middle | +0.516 個百分點 | 2.57 | 0.0103 | 0.0825 | 0.0809 | +0.284 個百分點 | +0.726 個百分點 |
| eligible_middle_bottom | -0.145 個百分點 | -0.83 | 0.4085 | 1.0000 | 0.8862 | +0.165 個百分點 | -0.425 個百分點 |
| eligible_top_bottom | +0.371 個百分點 | 1.46 | 0.1441 | 0.8647 | 0.5100 | +0.449 個百分點 | +0.301 個百分點 |
| complete_top_middle | +0.400 個百分點 | 2.30 | 0.0212 | 0.1485 | 0.1337 | +0.498 個百分點 | +0.312 個百分點 |
| complete_middle_bottom | -0.149 個百分點 | -0.87 | 0.3824 | 1.0000 | 0.8657 | -0.017 個百分點 | -0.268 個百分點 |
| complete_top_bottom | +0.252 個百分點 | 1.09 | 0.2746 | 1.0000 | 0.7409 | +0.481 個百分點 | +0.045 個百分點 |
| eligible_rank_ic | +0.0146 | 1.01 | 0.3118 | 1.0000 | 0.7897 | +0.0209 | +0.0089 |
| complete_rank_ic | +0.0191 | 1.46 | 0.1444 | 0.8647 | 0.5104 | +0.0337 | +0.0059 |

八列共用 52-event circular blocks、20,000 路徑及 seed 27202609。最有利的兩列
top-middle 普通 t 值雖高於 1.96，但 Holm／共同 max-t 仍未過 0.05；middle-bottom 為負，
所以不能刪除底段反彈後只展示高段。

## 二十組隨機排序 placebo

| Universe | 真實平均 | 真實 NW t | placebo 最大平均 | ID | placebo 最大 t | ID | 平均／t 同時勝出 |
|---|---:|---:|---:|---|---:|---|---|
| eligible | +0.371 個百分點 | 1.46 | +0.155 個百分點 | P06 | 1.07 | P06 | 是 |
| complete | +0.252 個百分點 | 1.09 | +0.150 個百分點 | P14 | 1.22 | P14 | 否 |

eligible 真實 top-bottom 的平均及 t 都高於 20 組 placebo 最大值；complete 的真實平均
較高，但 t 值低於最強 placebo，因此兩個 universe 同時勝出的固定門檻失敗。20 組只作
事前固定的 selector 對照，不冒充精確 p 值。

| Universe | Placebo | 平均 top-bottom | NW t | 前半 | 後半 |
|---|---|---:|---:|---:|---:|
| eligible | P01 | +0.150 個百分點 | 0.96 | -0.005 個百分點 | +0.290 個百分點 |
| eligible | P02 | +0.061 個百分點 | 0.41 | -0.019 個百分點 | +0.132 個百分點 |
| eligible | P03 | +0.021 個百分點 | 0.12 | -0.258 個百分點 | +0.273 個百分點 |
| eligible | P04 | -0.098 個百分點 | -0.72 | -0.232 個百分點 | +0.023 個百分點 |
| eligible | P05 | +0.077 個百分點 | 0.53 | +0.395 個百分點 | -0.210 個百分點 |
| eligible | P06 | +0.155 個百分點 | 1.07 | +0.108 個百分點 | +0.196 個百分點 |
| eligible | P07 | -0.214 個百分點 | -1.53 | -0.335 個百分點 | -0.105 個百分點 |
| eligible | P08 | +0.143 個百分點 | 0.90 | +0.261 個百分點 | +0.037 個百分點 |
| eligible | P09 | -0.048 個百分點 | -0.33 | -0.130 個百分點 | +0.025 個百分點 |
| eligible | P10 | -0.162 個百分點 | -1.16 | -0.259 個百分點 | -0.075 個百分點 |
| eligible | P11 | -0.049 個百分點 | -0.33 | +0.169 個百分點 | -0.246 個百分點 |
| eligible | P12 | +0.127 個百分點 | 0.88 | +0.282 個百分點 | -0.013 個百分點 |
| eligible | P13 | -0.231 個百分點 | -1.75 | +0.100 個百分點 | -0.530 個百分點 |
| eligible | P14 | +0.086 個百分點 | 0.62 | +0.257 個百分點 | -0.068 個百分點 |
| eligible | P15 | -0.033 個百分點 | -0.19 | -0.079 個百分點 | +0.009 個百分點 |
| eligible | P16 | -0.258 個百分點 | -1.69 | -0.296 個百分點 | -0.224 個百分點 |
| eligible | P17 | -0.042 個百分點 | -0.27 | -0.039 個百分點 | -0.044 個百分點 |
| eligible | P18 | -0.113 個百分點 | -0.85 | -0.112 個百分點 | -0.115 個百分點 |
| eligible | P19 | -0.040 個百分點 | -0.26 | -0.187 個百分點 | +0.092 個百分點 |
| eligible | P20 | -0.048 個百分點 | -0.31 | -0.134 個百分點 | +0.030 個百分點 |
| complete | P01 | +0.074 個百分點 | 0.59 | +0.011 個百分點 | +0.131 個百分點 |
| complete | P02 | +0.145 個百分點 | 1.20 | -0.231 個百分點 | +0.483 個百分點 |
| complete | P03 | -0.247 個百分點 | -1.80 | -0.127 個百分點 | -0.355 個百分點 |
| complete | P04 | -0.144 個百分點 | -1.25 | -0.155 個百分點 | -0.134 個百分點 |
| complete | P05 | -0.067 個百分點 | -0.56 | +0.267 個百分點 | -0.369 個百分點 |
| complete | P06 | -0.087 個百分點 | -0.75 | -0.258 個百分點 | +0.067 個百分點 |
| complete | P07 | +0.006 個百分點 | 0.05 | +0.062 個百分點 | -0.045 個百分點 |
| complete | P08 | +0.013 個百分點 | 0.11 | +0.062 個百分點 | -0.031 個百分點 |
| complete | P09 | +0.115 個百分點 | 1.05 | +0.145 個百分點 | +0.088 個百分點 |
| complete | P10 | -0.080 個百分點 | -0.63 | -0.027 個百分點 | -0.127 個百分點 |
| complete | P11 | -0.005 個百分點 | -0.05 | +0.018 個百分點 | -0.025 個百分點 |
| complete | P12 | +0.095 個百分點 | 0.78 | -0.068 個百分點 | +0.242 個百分點 |
| complete | P13 | -0.080 個百分點 | -0.65 | +0.143 個百分點 | -0.281 個百分點 |
| complete | P14 | +0.150 個百分點 | 1.22 | +0.369 個百分點 | -0.047 個百分點 |
| complete | P15 | -0.292 個百分點 | -2.24 | -0.131 個百分點 | -0.438 個百分點 |
| complete | P16 | -0.013 個百分點 | -0.11 | +0.196 個百分點 | -0.201 個百分點 |
| complete | P17 | +0.130 個百分點 | 1.14 | +0.129 個百分點 | +0.131 個百分點 |
| complete | P18 | +0.129 個百分點 | 1.08 | +0.053 個百分點 | +0.198 個百分點 |
| complete | P19 | -0.141 個百分點 | -1.14 | -0.112 個百分點 | -0.167 個百分點 |
| complete | P20 | -0.105 個百分點 | -0.91 | -0.037 個百分點 | -0.167 個百分點 |

## 升跌市與尾部壓力

| Universe | 固定壓力 | 事件 | 平均 top-bottom | NW t |
|---|---|---:|---:|---:|
| eligible | 未來 QQQ 非負 | 610 | +0.863 個百分點 | 2.86 |
| eligible | 未來 QQQ 負 | 295 | -0.647 個百分點 | -1.61 |
| eligible | 移除最大 46 個絕對差 | 859 | +0.290 個百分點 | 1.46 |
| complete | 未來 QQQ 非負 | 610 | +0.462 個百分點 | 1.70 |
| complete | 未來 QQQ 負 | 295 | -0.183 個百分點 | -0.52 |
| complete | 移除最大 46 個絕對差 | 859 | +0.357 個百分點 | 1.93 |

未來 QQQ 分組是事後反證，不是 regime 訊號。移除最大 46 個絕對差後，eligible／complete
NW t 只餘 **1.46／
1.93**；兩者均未達 1.96。移除事件分別佔全部絕對
spread **19.7%／
17.6%**。

## 十四項事前反證門檻

- Top-7／eligible／complete 回報逐列重建誤差不高於 1e-12：**通過**
- 905 個事件兩個 universe 訊號及未來回報覆蓋完整：**通過**
- 每事件三段互斥、聯集完整且大小相差不超過一：**通過**
- eligible top-middle 通過平均、NW t 及兩半：**通過**
- eligible middle-bottom 通過平均、NW t 及兩半：**未通過**
- eligible top-bottom 通過平均、NW t 及兩半：**未通過**
- complete top-middle 通過平均、NW t 及兩半：**通過**
- complete middle-bottom 通過平均、NW t 及兩半：**未通過**
- complete top-bottom 通過平均、NW t 及兩半：**未通過**
- eligible／complete rank IC 均通過平均、NW t 及兩半：**未通過**
- 八列 Holm 及共同 max-t p 全部不高於 0.05：**未通過**
- 兩個真實 top-bottom 平均及 NW t 均高於 20 組 placebo 最大值：**未通過**
- QQQ 非負／負兩組的兩個 top-bottom 均正且 NW t 不低於 1.96：**未通過**
- 兩個 universe 移除最大 46 個絕對差後仍正且 NW t 不低於 1.96：**未通過**

## 二十三道輸入、排序、family、placebo 及決策控制

- 01 · 協議 SHA：通過
- 02 · 第 26 輪來源 commit／收據 SHA：通過
- 03 · 第 25／24 輪收據 SHA：通過
- 04 · 原始事件收據 SHA：通過
- 05 · 行情 archive SHA／panel fingerprint：通過
- 06 · watchlist SHA：通過
- 07 · 三個台股參考 commit：通過
- 08 · 25 股 cohort 逐字一致：通過
- 09 · 905 事件及嚴格日期次序：通過
- 10 · 20／60／Top-7 原事件規則：通過
- 11 · D+1／20 session／20 bps：通過
- 12 · eligible／complete universe identity：通過
- 13 · 20 日動量及訊號 known-at：通過
- 14 · 動量降序／ticker 升序 tie-break：通過
- 15 · 三段 array_split、聯集及互斥：通過
- 16 · sleeve 等權及成本對稱：通過
- 17 · Spearman 平均 rank 定義：通過
- 18 · 八假說 family、Holm 及 NW lag 4：通過
- 19 · 52-event／20,000／seed 27202609 共同 bootstrap：通過
- 20 · 20 組 placebo、SeedSequence 欄序及 seed 27202608：通過
- 21 · QQQ 市場方向、46-event 尾部及固定前後半：通過
- 22 · 現時代號只可作警告：通過
- 23 · 策略／Paper／實金決策邊界：通過

23/23 只證明程式遵守凍結協議，不是策略盈利通過。

## 二十三項單欄變異攻擊

| 攻擊 | 單欄變異 | 預期錯誤碼 | 結果 |
|---|---|---|---|
| 01 | 協議 SHA 漂移 | `rank_monotonicity_protocol_mismatch` | 拒收 |
| 02 | 第 26 輪來源 commit 漂移 | `rank_monotonicity_round26_source_mismatch` | 拒收 |
| 03 | 第 26 輪收據 SHA 漂移 | `rank_monotonicity_round26_receipt_mismatch` | 拒收 |
| 04 | 第 25 輪收據 SHA 漂移 | `rank_monotonicity_prior_receipts_mismatch` | 拒收 |
| 05 | 原始事件收據 SHA 漂移 | `rank_monotonicity_event_receipt_mismatch` | 拒收 |
| 06 | 行情 archive SHA 漂移 | `rank_monotonicity_snapshot_hash_mismatch` | 拒收 |
| 07 | panel fingerprint 漂移 | `rank_monotonicity_panel_fingerprint_mismatch` | 拒收 |
| 08 | watchlist SHA 漂移 | `rank_monotonicity_watchlist_hash_mismatch` | 拒收 |
| 09 | 台股參考 commit 漂移 | `rank_monotonicity_reference_commits_mismatch` | 拒收 |
| 10 | 25 股 cohort 漂移 | `rank_monotonicity_cohort_mismatch` | 拒收 |
| 11 | 事件數改 904 | `rank_monotonicity_event_order_mismatch` | 拒收 |
| 12 | Top-K 改 10 | `rank_monotonicity_signal_rule_mismatch` | 拒收 |
| 13 | 成本改 10 bps | `rank_monotonicity_execution_rule_mismatch` | 拒收 |
| 14 | 刪除完整股池 universe | `rank_monotonicity_universe_mismatch` | 拒收 |
| 15 | bucket 改四組 | `rank_monotonicity_bucket_contract_mismatch` | 拒收 |
| 16 | tie-break 反向 | `rank_monotonicity_tie_break_mismatch` | 拒收 |
| 17 | IC 改 Pearson raw | `rank_monotonicity_rank_ic_mismatch` | 拒收 |
| 18 | family 刪除 rank IC | `rank_monotonicity_family_contract_mismatch` | 拒收 |
| 19 | bootstrap seed 漂移 | `rank_monotonicity_bootstrap_contract_mismatch` | 拒收 |
| 20 | placebo 改 100 組 | `rank_monotonicity_placebo_contract_mismatch` | 拒收 |
| 21 | 尾部改 45 列 | `rank_monotonicity_stress_contract_mismatch` | 拒收 |
| 22 | 現時代號越權升格 | `rank_monotonicity_identity_scope_breached` | 拒收 |
| 23 | 越權啟動 Paper | `rank_monotonicity_decision_boundary_breached` | 拒收 |

每項均命中事前指定錯誤碼。覆蓋不足不是合約欄位變異；真實覆蓋若不足，主路徑會以
`rank_monotonicity_coverage_mismatch` 在結果前直接 fail closed。

## 決策

第 27 輪保留一條很窄的研究觀察：高動量段相對中段的平均差為正。但這不是完整單調性；
middle-bottom 為負、top-bottom 及 rank IC 不顯著、完整股池未勝最強 placebo、QQQ 下跌組
為負、46-event 尾部亦未過。**不建立新策略、不啟動短線 Paper、不產生持倉或買入名單。**

下一個具升級價值的證據仍是獲授權 point-in-time 成分、永久 ID、歷史行業、公司行動、
退市／退出經濟與同步基準；在此之前，再改 bucket 數或只選 top-middle 都屬事後救援。

## 可重播檔案

- [第 27 輪事前協議](SHORT_TERM_RANK_MONOTONICITY_PLACEBO_PROTOCOL.md)
- `artifacts/short_term_rank_monotonicity_placebo_validation.json`
- `site/data/short-term-rank-monotonicity-placebo.json`
