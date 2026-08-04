# 美股短線第 24 輪：公平基準歸因與多重檢驗報告

研究日期：2026-08-04

狀態：survivor cohort 反證；不可投資；短線 Paper 全現金；實金動作 US$0

## 一頁結論

20 日 Top-7 對合資格池等權仍有 **+0.319 個百分點**、NW t
**3.03**；但對完整現時股池等權只餘
**+0.238 個百分點**、NW t **1.69**。
對 QQQ 的事件差為 **+0.532 個百分點**、NW t
**2.71**。

九假說 Holm 後，主要合資格池 p 為 **0.0223**；共同 52-event
max-t p 為 **0.0208**，Reality Check p 為
**0.0187**。但全專案 6,208 次 Bonferroni p 為
**1.0000**，而且完整現時股池 NW 門檻失敗；九項事前門檻
只通過 **6/9**。

所以「排名相對已通過濾網的股票有訊號」不能改寫成「Top-7 對完整股池及搜尋偏誤都
穩健」。正式就緒仍為 **1/18**、正式策略運行 **0 次**、Paper 持倉 **0**、實金
動作 **US$0**。

## 20 日公平基準歸因

| 20 日歸因 | 定義 | 平均差 | NW t | 前半 | 後半 |
|---|---|---:|---:|---:|---:|
| Top-7 排名效果 | `top7 - eligible_equal` | +0.319 個百分點 | 3.03 | +0.348 個百分點 | +0.293 個百分點 |
| 合資格濾網效果 | `eligible_equal - complete_cohort_equal` | -0.081 個百分點 | -1.04 | -0.073 個百分點 | -0.088 個百分點 |
| 對完整股池合計 | `top7 - complete_cohort_equal` | +0.238 個百分點 | 1.69 | +0.275 個百分點 | +0.205 個百分點 |

逐列 `排名效果 + 合資格濾網效果 = 對完整股池合計`；最大恆等式殘差
`0.00e+00`。完整現時股池仍有
存活者偏差，這張表只防止挑選最有利分母。

## 九個配對假說

| 期限 | Baseline | 平均差 | NW t | 普通 p | Holm | Max-t | RW step-down | 6,208× |
|---:|---|---:|---:|---:|---:|---:|---:|---:|
| 5 日 | 合資格池等權 | +0.086 個百分點 | 2.18 | 0.0296 | 0.1674 | 0.1272 | 0.0952 | 1.0000 |
| 5 日 | 完整現時股池等權 | +0.074 個百分點 | 1.44 | 0.1488 | 0.2975 | 0.4370 | 0.1627 | 1.0000 |
| 5 日 | QQQ | +0.153 個百分點 | 2.38 | 0.0175 | 0.1224 | 0.0844 | 0.0710 | 1.0000 |
| 10 日 | 合資格池等權 | +0.130 個百分點 | 2.06 | 0.0392 | 0.1674 | 0.1583 | 0.0987 | 1.0000 |
| 10 日 | 完整現時股池等權 | +0.092 個百分點 | 1.11 | 0.2672 | 0.2975 | 0.6646 | 0.2584 | 1.0000 |
| 10 日 | QQQ | +0.241 個百分點 | 2.20 | 0.0279 | 0.1674 | 0.1210 | 0.0952 | 1.0000 |
| 20 日 | 合資格池等權 | +0.319 個百分點 | 3.03 | 0.0025 | 0.0223 | 0.0208 | 0.0208 | 1.0000 |
| 20 日 | 完整現時股池等權 | +0.238 個百分點 | 1.69 | 0.0914 | 0.2742 | 0.3037 | 0.1184 | 1.0000 |
| 20 日 | QQQ | +0.532 個百分點 | 2.71 | 0.0067 | 0.0533 | 0.0410 | 0.0399 | 1.0000 |

普通 p 使用固定 NW t 的雙尾常態近似；Holm、共同 max-t、Romano–Wolf 及 6,208 次
Bonferroni 全部呈列，不以其中最漂亮的一欄取代其他負結果。

## 九項事前反證門檻

- 20 日對合資格池平均為正且 NW t 不低於 1.96：**通過**
- 20 日對完整現時股池平均為正且 NW t 不低於 1.96：**未通過**
- 20 日對 QQQ 平均為正且 NW t 不低於 1.96：**通過**
- 20 日對三 baseline 的前後兩半平均全部為正：**通過**
- 20 日合資格池九假說 Holm p 不高於 0.05：**通過**
- 20 日合資格池共同 max-t p 不高於 0.05：**通過**
- 九假說 Reality Check p 不高於 0.05：**通過**
- 20 日合資格池 6,208 次 Bonferroni p 不高於 0.05：**未通過**
- 5／10／20 日合資格池共同 max-t p 全不高於 0.05：**未通過**

任一失敗即不能升格；全通過亦只代表 survivor cohort 未被本輪推翻。

## 共同區塊 bootstrap

- 共同事件：905；52-event circular block；每路徑 18 blocks。
- 路徑：20,000；seed 20260804；九列共用 indices 並各自去中心化。
- 觀察最大正 t：3.03；Reality Check p：
  0.0187。
- start-index SHA-256：`05e46dacfca9fd1326c6f2d1d4f8784b7fef2646ac25b0016e45cb606c9bc98e`。
- 全專案普通 p 通過界線：`0.00000805`。

共同 bootstrap 保留同日跨期限及 baseline 關係，但沒有修復現時股池選樣偏差。

## 十六道控制

- 01｜輸入 SHA：**通過**
- 02｜固定事件根路徑：**通過**
- 03｜5／10／20 日期限：**通過**
- 04｜20 日主要期：**通過**
- 05｜三個公平 baseline：**通過**
- 06｜905 個共同事件：**通過**
- 07｜共同日期嚴格一對一：**通過**
- 08｜逐事件同成本配對：**通過**
- 09｜NW lag 1／2／4：**通過**
- 10｜九假說 family：**通過**
- 11｜alpha 0.05：**通過**
- 12｜全專案 6,208 trials：**通過**
- 13｜52-event block：**通過**
- 14｜20,000 路徑：**通過**
- 15｜固定 seed／共同 circular indices／去中心化：**通過**
- 16｜決策邊界：**通過**

## 十六項突變攻擊

- 01｜輸入 SHA 漂移：**拒收** `multiplicity_input_hash_mismatch`
- 02｜事件路徑漂移：**拒收** `multiplicity_path_not_frozen`
- 03｜刪除 5 日期限：**拒收** `multiplicity_horizons_not_frozen`
- 04｜主要期改 10 日：**拒收** `multiplicity_primary_horizon_not_frozen`
- 05｜刪除完整股池 baseline：**拒收** `multiplicity_baselines_not_frozen`
- 06｜共同樣本改 907：**拒收** `multiplicity_common_sample_mismatch`
- 07｜容許日期重排：**拒收** `multiplicity_event_order_invalid`
- 08｜取消同成本配對：**拒收** `multiplicity_pairing_or_cost_mismatch`
- 09｜20 日 lag 改 1：**拒收** `multiplicity_hac_lags_not_frozen`
- 10｜family 改三列：**拒收** `multiplicity_family_not_frozen`
- 11｜alpha 改 10%：**拒收** `multiplicity_alpha_not_frozen`
- 12｜全專案 trials 改 9：**拒收** `multiplicity_global_trials_not_frozen`
- 13｜block 改 8：**拒收** `multiplicity_block_length_not_frozen`
- 14｜bootstrap 減至 2,000：**拒收** `multiplicity_bootstrap_paths_not_frozen`
- 15｜每列獨立重抽：**拒收** `multiplicity_bootstrap_contract_not_frozen`
- 16｜提前授權 Paper：**拒收** `multiplicity_decision_boundary_breached`

## 決策

本輪沒有新增策略路徑、股票名單或落盤指令。正面排序效果只保留作取得合法
point-in-time 成分、永久 ID、歷史行業、公司行動、退市／收購實收及同步 RF 後的原樣
重測假說。

輸入齊全後仍只准依既有 18/18 正式事前登記運行一次，再通過 50 bps、QQQ／SPY／逐期
股池 baseline、NW／PSR／6,208-trial DSR／PBO，以及 252 個新增交易日／12 次完成月度
輪選，才可由全現金開始 Paper。US$1,000 只作讀者比例示例。

- [第 24 輪事前協議](SHORT_TERM_BASELINE_MULTIPLICITY_PROTOCOL.md)
- [第 23 輪時間／尾部反證](SHORT_TERM_TEMPORAL_TAIL_ROBUSTNESS_RESEARCH_REPORT.md)
- [原 20 日訊號研究](SHORT_TERM_HIGH_RETURN_RESEARCH_REPORT.md)

歷史及合成結果不保證未來回報；本報告不構成投資建議、Paper 成交或實金落盤指令。
