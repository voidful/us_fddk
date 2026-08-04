# 美股短線第 28 輪：短期反轉與波幅歸因報告

生成日期：2026-08-04
研究角色：同一已見 survivor cohort 的機制歸因；不是買入名單、Paper 或實金指令。

## 執行摘要

本輪在任何新歸因統計前，以 commit `2ebb973` 固定第 27 輪全部
905 個事件與 bucket、訊號日前 5 日回報、20 日已實現波幅、兩控制橫截面 OLS、八假說
family、QQQ known-at 市況及 46-event 尾部。這是同一已見樣本，不是獨立未見確認。

控制後，高段對中段明顯縮小：

- eligible 由 **+0.516 個百分點、NW t 2.57**
  降至 **+0.216 個百分點、t 1.62**，
  只保留 41.8%；
- complete 由 **+0.400 個百分點、t 2.30**
  降至 **+0.140 個百分點、t 1.10**，
  只保留 34.9%，
  後半平均更轉為 **-0.068 個百分點**；
- 控制後 bottom-middle 仍為 **+0.164 個百分點／+0.053 個百分點**，
  沒有回復單調排序；
- 訊號日 QQQ 20 日為負時，eligible／complete residual top-middle 平均為
  **-0.038 個百分點／
  -0.138 個百分點**；
- 尾部壓力 NW t 為 **1.95／
  1.01**，eligible 的 1.95 仍嚴格低於 1.96。

十四項事前門檻只過 **6/14**。
5 日反轉與波幅共同解釋了大部分 top-middle 平均差，卻沒有完整解釋底段反彈；剩餘差額在
完整股池、共同校正、後半、弱市及尾部均不足。正式就緒維持 **1/18**、point-in-time
**1/20**、策略運行 **0**、短線 Paper 全現金、持倉 **0**、實金動作 **US$0**。

## 輸入與歸因完整性

| 項目 | 結果 |
|---|---:|
| 原始／共同事件 | 905 / 905 |
| 訊號日期 | 2006-08-04 至 2026-07-02 |
| raw 對第 27 輪最大誤差 | 0.000e+00 |
| raw = predicted + residual 最大誤差 | 0.000e+00 |
| residual universe mean 最大絕對值 | 0.000e+00 |
| OLS 最大 condition number／最低 rank | 14.00 / 3 |
| feature receipt SHA-256 | `0cf0edd8e562d64edfa9f50a49f48c266f19909faaf0f4fe75f5222710a4e9a8` |
| 控制／攻擊 | 23/23 / 23/23 拒收 |

## 八假說共同 family

| 固定比較 | 平均 | NW t | 普通 p | Holm p | 共同 max-t p | 前半 | 後半 |
|---|---:|---:|---:|---:|---:|---:|---:|
| eligible_raw_top_middle | +0.516 個百分點 | 2.57 | 0.0103 | 0.0825 | 0.1106 | +0.284 個百分點 | +0.726 個百分點 |
| eligible_raw_bottom_middle | +0.145 個百分點 | 0.83 | 0.4085 | 1.0000 | 0.9488 | -0.165 個百分點 | +0.425 個百分點 |
| complete_raw_top_middle | +0.400 個百分點 | 2.30 | 0.0212 | 0.1485 | 0.1805 | +0.498 個百分點 | +0.312 個百分點 |
| complete_raw_bottom_middle | +0.149 個百分點 | 0.87 | 0.3824 | 1.0000 | 0.9352 | +0.017 個百分點 | +0.268 個百分點 |
| eligible_residual_top_middle | +0.216 個百分點 | 1.62 | 0.1059 | 0.6353 | 0.5237 | +0.094 個百分點 | +0.325 個百分點 |
| eligible_residual_bottom_middle | +0.164 個百分點 | 1.12 | 0.2616 | 1.0000 | 0.8328 | -0.194 個百分點 | +0.487 個百分點 |
| complete_residual_top_middle | +0.140 個百分點 | 1.10 | 0.2722 | 1.0000 | 0.8450 | +0.370 個百分點 | -0.068 個百分點 |
| complete_residual_bottom_middle | +0.053 個百分點 | 0.41 | 0.6811 | 1.0000 | 0.9989 | -0.027 個百分點 | +0.125 個百分點 |

八列共用 52-event circular blocks、20,000 路徑及 seed 28202610。raw eligible top-middle 的
Holm／共同 max-t p 已升至 **0.0825／
0.1106**；控制後兩個 top-middle 普通 NW t 亦低於 1.96。

## 底段反彈歸因

| Universe | raw bottom-middle | 控制預測 | residual | 5 日 rank gap | 波幅 rank gap | 5 日貢獻 | 波幅貢獻 |
|---|---:|---:|---:|---:|---:|---:|---:|
| eligible | +0.145 個百分點 | -0.019 個百分點 | +0.164 個百分點 | -0.113 | +0.015 | +0.007 個百分點 | -0.025 個百分點 |
| complete | +0.149 個百分點 | +0.096 個百分點 | +0.053 個百分點 | -0.150 | +0.114 | +0.002 個百分點 | +0.094 個百分點 |

bottom 的訊號日前 5 日 rank 明顯低於 middle，但 5 日 rank beta 本身不穩定；完整股池的
bottom 波幅 rank 較高，波幅 beta 為正，但平均波幅貢獻的 NW t 仍不足 1.96。因此不能把
底段反彈簡化成單一「短期反轉」或「高波幅補償」。

| Universe | 5 日 rank beta | NW t | 波幅 rank beta | NW t | residual／raw top-middle |
|---|---:|---:|---:|---:|---:|
| eligible | -0.330 個百分點 | -1.41 | +1.088 個百分點 | 2.08 | 41.8% |
| complete | -0.065 個百分點 | -0.28 | +1.469 個百分點 | 2.81 | 34.9% |

## 訊號日市況與尾部壓力

| Universe | 固定壓力 | 事件 | residual top-middle 平均 | NW t |
|---|---|---:|---:|---:|
| eligible | 訊號日 QQQ 20 日非負 | 677 | +0.301 個百分點 | 2.15 |
| eligible | 訊號日 QQQ 20 日負 | 228 | -0.038 個百分點 | -0.13 |
| eligible | 移除最大 46 個 raw bottom-middle | 859 | +0.269 個百分點 | 1.95 |
| complete | 訊號日 QQQ 20 日非負 | 677 | +0.233 個百分點 | 1.63 |
| complete | 訊號日 QQQ 20 日負 | 228 | -0.138 個百分點 | -0.60 |
| complete | 移除最大 46 個 raw bottom-middle | 859 | +0.128 個百分點 | 1.01 |

QQQ 分組只使用訊號日已知 20 日回報，但仍是已見樣本診斷。弱市兩個 residual top-middle
平均皆負；46-event 壓力亦沒有兩個 universe 同時通過。

## 十四項事前反證門檻

- 第 24–27 輪、行情、panel、watchlist 及 bucket 收據一致：**通過**
- 905 事件兩個 universe 的 5 日回報、20 日波幅及未來回報完整：**通過**
- 第 27 輪 bucket、事件次序及 raw spread 逐列重播：**通過**
- OLS rank／condition、residual mean 及歸因 identity 通過：**通過**
- eligible raw top-middle 通過平均、NW t 及兩半：**通過**
- complete raw top-middle 通過平均、NW t 及兩半：**通過**
- eligible residual top-middle 通過平均、NW t 及兩半：**未通過**
- complete residual top-middle 通過平均、NW t 及兩半：**未通過**
- eligible raw bottom-middle 為負、NW t 不高於 -1.96 且兩半為負：**未通過**
- complete raw bottom-middle 為負、NW t 不高於 -1.96 且兩半為負：**未通過**
- eligible residual bottom-middle 為負、NW t 不高於 -1.96 且兩半為負：**未通過**
- complete residual bottom-middle 為負、NW t 不高於 -1.96 且兩半為負：**未通過**
- 兩個 residual top-middle 保留至少 75% raw 平均且八列共同校正通過：**未通過**
- QQQ 兩種 known-at 市況及 46-event 尾部的兩個 residual top-middle 均通過：**未通過**

## 二十三道輸入、控制、OLS、family 及決策控制

- 01 · 協議 SHA：通過
- 02 · 第 27 輪來源 commit：通過
- 03 · 第 27 輪收據 SHA：通過
- 04 · 第 24–26 輪收據 SHA：通過
- 05 · 原始事件收據 SHA：通過
- 06 · 行情 archive SHA／panel fingerprint：通過
- 07 · watchlist SHA：通過
- 08 · 三個台股參考 commit：通過
- 09 · 25 股 cohort：通過
- 10 · 905 事件及嚴格日期次序：通過
- 11 · 5 日回報窗口：通過
- 12 · 20 日波幅窗口及 ddof=1：通過
- 13 · 平均 rank 轉換：通過
- 14 · OLS 欄序、lstsq 及 condition 上限：通過
- 15 · eligible／complete universe：通過
- 16 · 第 27 輪 bucket assignment SHA：通過
- 17 · D+1／20 session／20 bps：通過
- 18 · raw／predicted／residual identity：通過
- 19 · 八假說 family、Holm 及 NW lag 4：通過
- 20 · 52-event／20,000／seed 28202610 共同 bootstrap：通過
- 21 · QQQ 20 日 known-at regime：通過
- 22 · 46-event 尾部及固定前後半：通過
- 23 · 現時代號／策略／Paper／實金決策邊界：通過

23/23 只證明程式遵守凍結協議，不是策略盈利通過。

## 二十三項單欄變異攻擊

| 攻擊 | 單欄變異 | 預期錯誤碼 | 結果 |
|---|---|---|---|
| 01 | 協議 SHA 漂移 | `reversal_volatility_protocol_mismatch` | 拒收 |
| 02 | 第 27 輪來源 commit 漂移 | `reversal_volatility_round27_source_mismatch` | 拒收 |
| 03 | 第 27 輪收據 SHA 漂移 | `reversal_volatility_round27_receipt_mismatch` | 拒收 |
| 04 | 第 26 輪收據 SHA 漂移 | `reversal_volatility_prior_receipts_mismatch` | 拒收 |
| 05 | 原始事件收據 SHA 漂移 | `reversal_volatility_event_receipt_mismatch` | 拒收 |
| 06 | 行情 archive SHA 漂移 | `reversal_volatility_market_data_mismatch` | 拒收 |
| 07 | watchlist SHA 漂移 | `reversal_volatility_watchlist_mismatch` | 拒收 |
| 08 | 台股參考 commit 漂移 | `reversal_volatility_reference_commits_mismatch` | 拒收 |
| 09 | 25 股 cohort 漂移 | `reversal_volatility_cohort_mismatch` | 拒收 |
| 10 | 事件數改 904 | `reversal_volatility_event_order_mismatch` | 拒收 |
| 11 | 5 日窗口改 2 日 | `reversal_volatility_prior_return_window_mismatch` | 拒收 |
| 12 | 波幅改 60 日 | `reversal_volatility_volatility_window_mismatch` | 拒收 |
| 13 | rank 改 ticker tie-break | `reversal_volatility_rank_transform_mismatch` | 拒收 |
| 14 | OLS condition 上限漂移 | `reversal_volatility_regression_contract_mismatch` | 拒收 |
| 15 | 刪除完整股池 universe | `reversal_volatility_universe_mismatch` | 拒收 |
| 16 | bucket receipt SHA 漂移 | `reversal_volatility_bucket_receipt_mismatch` | 拒收 |
| 17 | 成本改 10 bps | `reversal_volatility_execution_rule_mismatch` | 拒收 |
| 18 | family 刪除 residual | `reversal_volatility_family_contract_mismatch` | 拒收 |
| 19 | NW lag 改 1 | `reversal_volatility_family_contract_mismatch` | 拒收 |
| 20 | bootstrap seed 漂移 | `reversal_volatility_bootstrap_contract_mismatch` | 拒收 |
| 21 | QQQ regime 改 60 日 | `reversal_volatility_regime_contract_mismatch` | 拒收 |
| 22 | 尾部改 45 列 | `reversal_volatility_tail_contract_mismatch` | 拒收 |
| 23 | 越權啟動 Paper | `reversal_volatility_decision_boundary_breached` | 拒收 |

每項均命中事前指定錯誤碼；真實特徵覆蓋不足會由主路徑以
`reversal_volatility_coverage_mismatch` 在結果前 fail closed。

## 決策

第 28 輪把局部 top-middle 線索再收窄：大部分平均差與 5 日／波幅控制共變，殘差不再通過；
底段反彈仍存在，亦沒有在完整股池、後半或弱市形成可靠單調結構。**不建立新策略、不啟動
短線 Paper、不產生持倉或買入名單。**

下一個可升級證據仍是合法授權 point-in-time 成分、永久 ID、歷史行業、公司行動、退市／
退出經濟與同步基準；在此之前再改控制窗或只選 QQQ 強市，均屬事後救援。

## 可重播檔案

- [第 28 輪事前協議](SHORT_TERM_REVERSAL_VOLATILITY_ATTRIBUTION_PROTOCOL.md)
- `artifacts/short_term_reversal_volatility_attribution_validation.json`
- `site/data/short-term-reversal-volatility-attribution.json`
