# 美股短線第 26 輪：共同市場風險殘差反證報告

研究日期：2026-08-04

狀態：survivor cohort 非獨立反證；不可投資；短線 Paper 全現金；實金動作 US$0

## 一頁結論

第 26 輪沒有調校新策略，只把固定 Top-7 對公平 baseline 的差額分解成訊號日前估算的
共同 beta 貢獻及殘差。原始 905 個事件全部重建無誤；因 MA 在最早 39 個事件前不足
252 個完整日回報，十假說 family 事前 repair 後統一使用 2007-06-01 至 2026-07-02 的
**866 個共同事件**，沒有讓 60 日模型使用較長樣本。

在共同 866 事件中，raw Top-7 對 eligible 等權平均差為
**+0.313 個百分點**、NW t **2.88**；
但對完整現時股池只餘 **+0.261 個百分點**、NW t
**1.78**。以訊號前 252 日 QQQ beta 扣除共同風險後：

- 對 eligible 仍為 **+0.228 個百分點**、NW t
  **2.45**，但十假說 Holm／max-t p 為
  **0.1302／0.0524**，均未通過
  固定 0.05；
- 對完整現時股池只有 **+0.180 個百分點**、NW t
  **1.36**；
- QQQ beta 貢獻平均佔 raw eligible 差額 **27.0%**；
  絕對 beta gap 中位 **0.108**、95th
  **0.404**，兩道風險曝險門檻均失敗。

SPY 252 日殘差對 eligible／complete 的 NW t 為
**2.21／1.11**；固定
25 股共同因子殘差只有 **1.51／
0.66**。未來 QQQ 上升事件主要殘差 NW t
**2.59**，下跌事件只有
**0.70**。十四項事前門檻只過
**6/14**，不能把原始正面差額寫成
已通過共同市場風險、公平完整股池及 family-wise 校正的可投資 alpha。

正式就緒仍為 **1/18**、point-in-time **1/20**、正式策略運行 **0 次**、Paper 持倉
**0**、實金動作 **US$0**。

## 首次停止與非獨立 coverage repair

父協議先以 commit `6616064` 凍結。首次執行在第一個缺失 beta cell 以
`common_risk_beta_window_mismatch` 停止，沒有寫出 family、gate、報告或收據。

覆蓋盤點只發現 MA：2006-08-04 至 2007-05-25 共 39 個事件不足 252 日；第一個完整
訊號日為 2007-06-01。其後先以 commit `b781601` 凍結唯一修復：原 905 事件仍完整重建，
但全部十列統一使用 866 個共同事件；父協議其他 14 項 gate、factor、beta 公式、兩個
baseline、成本、前後半、Holm、NW lag 4、共同 bootstrap 及 46-event 壓力全部不改。
本報告因此不是獨立首次未見證據。

| 覆蓋項目 | 固定結果 |
|---|---:|
| 原始重建事件 | 905 |
| 十假說共同事件 | 866 |
| 覆蓋排除事件 | 39 |
| 共同 beta cells | 86,600 / 86,600 |
| 最大回報重建誤差 | 0.000e+00 |
| 最大 beta 分解誤差 | 0.000e+00 |

## 十假說共同 family

| 固定模型／baseline | 事件 | 平均配對差 | NW t | 普通 p | Holm p | 共同 max-t p | 前半 | 後半 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| RAW × eligible | 866 | +0.313 個百分點 | 2.88 | 0.0040 | 0.0400 | 0.0177 | +0.337 個百分點 | +0.293 個百分點 |
| RAW × complete_cohort | 866 | +0.261 個百分點 | 1.78 | 0.0749 | 0.4494 | 0.2024 | +0.329 個百分點 | +0.205 個百分點 |
| QQQ_60 × eligible | 866 | +0.215 個百分點 | 2.28 | 0.0229 | 0.1831 | 0.0748 | +0.251 個百分點 | +0.185 個百分點 |
| QQQ_60 × complete_cohort | 866 | +0.198 個百分點 | 1.48 | 0.1388 | 0.6544 | 0.3408 | +0.363 個百分點 | +0.063 個百分點 |
| QQQ_252 × eligible | 866 | +0.228 個百分點 | 2.45 | 0.0145 | 0.1302 | 0.0524 | +0.280 個百分點 | +0.186 個百分點 |
| QQQ_252 × complete_cohort | 866 | +0.180 個百分點 | 1.36 | 0.1749 | 0.6544 | 0.4098 | +0.321 個百分點 | +0.064 個百分點 |
| SPY_252 × eligible | 866 | +0.220 個百分點 | 2.21 | 0.0272 | 0.1901 | 0.0870 | +0.290 個百分點 | +0.162 個百分點 |
| SPY_252 × complete_cohort | 866 | +0.156 個百分點 | 1.11 | 0.2659 | 0.6544 | 0.5746 | +0.312 個百分點 | +0.028 個百分點 |
| COHORT_252 × eligible | 866 | +0.135 個百分點 | 1.51 | 0.1309 | 0.6544 | 0.3239 | +0.260 個百分點 | +0.032 個百分點 |
| COHORT_252 × complete_cohort | 866 | +0.085 個百分點 | 0.66 | 0.5105 | 0.6544 | 0.8840 | +0.305 個百分點 | -0.096 個百分點 |

十列共用 52-event circular block、20,000 路徑及 seed 26202608。RAW 兩列亦放進同一
family，不能先看 residual 較漂亮才把原始比較刪除。正式 6,208-trial 搜尋壓力沒有重設。

## beta gap 與共同風險貢獻

| 模型／baseline | 平均 beta gap | 絕對 gap 中位 | 絕對 gap 95th | beta gap 為正 | beta 貢獻平均 | 佔 raw 平均 |
|---|---:|---:|---:|---:|---:|---:|
| QQQ_60__eligible | 0.099 | 0.134 | 0.494 | 66.7% | +0.098 個百分點 | 31.4% |
| QQQ_60__complete_cohort | 0.069 | 0.173 | 0.574 | 58.4% | +0.063 個百分點 | 24.2% |
| QQQ_252__eligible | 0.091 | 0.108 | 0.404 | 71.5% | +0.085 個百分點 | 27.0% |
| QQQ_252__complete_cohort | 0.062 | 0.141 | 0.479 | 61.2% | +0.081 個百分點 | 31.1% |
| SPY_252__eligible | 0.092 | 0.098 | 0.417 | 69.4% | +0.093 個百分點 | 29.9% |
| SPY_252__complete_cohort | 0.065 | 0.136 | 0.499 | 61.5% | +0.105 個百分點 | 40.3% |
| COHORT_252__eligible | 0.107 | 0.112 | 0.463 | 70.7% | +0.178 個百分點 | 56.9% |
| COHORT_252__complete_cohort | 0.069 | 0.145 | 0.528 | 58.9% | +0.176 個百分點 | 67.5% |

每列逐事件嚴格滿足 `raw active = residual active + beta gap × factor event return`。
beta 只用訊號日或之前的調整收市日回報，不 clipping、不 winsor、不 shrink；未來 factor
回報只用於事後分解，不是訊號。正值比例把絕對值不高於 `1e-12` 的浮點殘差視為零，
並在 JSON 收據把四捨五入後的負零正規化為 `0.0`；這只消除跨平台數值庫差異，不改平均、
t 值、p 值、門檻或決策。

## QQQ 上／下及 beta-contribution 尾部壓力

| 固定反證 | 事件 | 平均主要殘差 | NW t | 判讀 |
|---|---:|---:|---:|---|
| 未來 QQQ 回報非負 | 581 | +0.290 個百分點 | 2.59 | 事後 regime，不可交易 |
| 未來 QQQ 回報為負 | 285 | +0.102 個百分點 | 0.70 | 未過 1.96 |
| 移除絕對 beta 貢獻最大 46 列 | 820 | +0.205 個百分點 | 2.20 | 保留父協議固定 46 列 |

被移除 46 列佔全部絕對 beta contribution **27.3%**。
尾部壓力通過不能抵銷 QQQ 下跌組、完整股池及十假說 family 的失敗。

## 2026 現時行業標籤診斷

中位唯一行業數 **4**，中位有效行業數
**3.27**；**30.1%**
事件有至少四股被現時標成同一行業，單次最多六股。

| 2026 現時行業標籤 | 選中 slots | Slot share |
|---|---:|---:|
| Information Technology | 2326 | 38.4% |
| Financials | 922 | 15.2% |
| Health Care | 694 | 11.4% |
| Industrials | 549 | 9.1% |
| Communication | 518 | 8.5% |
| Consumer Staples | 430 | 7.1% |
| Energy | 362 | 6.0% |
| Consumer Discretionary | 261 | 4.3% |

這些是把 2026 現時行業標籤回填到歷史事件的單向警告，不是 point-in-time 身份、通過
證據或買入名單。

## 十四項事前反證門檻

- 四條原始事件回報逐列重建誤差不高於 1e-12：**通過**
- 866 個共同事件所有股票及模型 beta window 完整：**通過**
- 所有共同風險分解最大誤差不高於 1e-12：**通過**
- QQQ 252 日絕對 beta gap 中位不高於 0.10：**未通過**
- QQQ 252 日絕對 beta gap 95th 不高於 0.25：**未通過**
- QQQ 252 殘差對 eligible 為正、NW t 過 1.96、兩半同正：**通過**
- QQQ 252 殘差對 complete 為正、NW t 過 1.96、兩半同正：**未通過**
- SPY 252 殘差對 eligible 為正、NW t 過 1.96、兩半同正：**通過**
- SPY 252 殘差對 complete 為正、NW t 過 1.96、兩半同正：**未通過**
- cohort 252 殘差對 eligible 為正、NW t 過 1.96、兩半同正：**未通過**
- cohort 252 殘差對 complete 為正、NW t 過 1.96、兩半同正：**未通過**
- 六個 252 日殘差列 Holm／共同 max-t p 均不高於 0.05：**未通過**
- 未來 QQQ 上升／下跌兩組主要殘差均正且 NW t 不低於 1.96：**未通過**
- 移除最大 46 個絕對 beta contribution 後主要殘差仍正且 NW t 不低於 1.96：**通過**

十四項全過亦只可寫作 survivor cohort 未被本輪額外推翻；本輪實際 6/14。

## 二十一道控制

- 01｜協議 SHA：**通過**
- 02｜第 25 輪來源 commit／收據 SHA：**通過**
- 03｜第 24 輪收據 SHA：**通過**
- 04｜行情 archive SHA：**通過**
- 05｜panel fingerprint：**通過**
- 06｜watchlist SHA：**通過**
- 07｜原始事件收據 SHA：**通過**
- 08｜三個台股參考 commit：**通過**
- 09｜25 股 cohort 逐字一致：**通過**
- 10｜905 事件及日期次序：**通過**
- 11｜20／60／Top-7 訊號：**通過**
- 12｜D+1／20 session／20 bps：**通過**
- 13｜QQQ／SPY／cohort factor identity：**通過**
- 14｜60／252 beta window：**通過**
- 15｜OLS beta 公式及禁止 clipping／winsor／shrink：**通過**
- 16｜eligible／complete 兩個 baseline：**通過**
- 17｜十假說 family、Holm 及 NW lag 4：**通過**
- 18｜52-event／20,000／seed 26202608 共同 bootstrap：**通過**
- 19｜46-event 壓力及現時行業標籤不可升格：**通過**
- 20｜策略／Paper／實金決策邊界：**通過**
- 21｜beta 覆蓋 repair SHA、866 個共同事件及 MA 缺口：**通過**

## 二十一項突變攻擊

- 01｜協議 SHA 漂移：**拒收** `common_risk_protocol_mismatch`
- 02｜第 25 輪來源 commit 漂移：**拒收** `common_risk_round25_source_mismatch`
- 03｜第 25 輪收據 SHA 漂移：**拒收** `common_risk_round25_receipt_mismatch`
- 04｜第 24 輪收據 SHA 漂移：**拒收** `common_risk_round24_receipt_mismatch`
- 05｜行情 archive SHA 漂移：**拒收** `common_risk_snapshot_hash_mismatch`
- 06｜panel fingerprint 漂移：**拒收** `common_risk_panel_fingerprint_mismatch`
- 07｜watchlist SHA 漂移：**拒收** `common_risk_watchlist_hash_mismatch`
- 08｜原始事件收據 SHA 漂移：**拒收** `common_risk_event_receipt_hash_mismatch`
- 09｜台股參考 commit 漂移：**拒收** `common_risk_reference_commits_mismatch`
- 10｜25 股 cohort 漂移：**拒收** `common_risk_cohort_mismatch`
- 11｜事件數改 904：**拒收** `common_risk_event_order_mismatch`
- 12｜Top-K 改 10：**拒收** `common_risk_signal_rule_mismatch`
- 13｜成本改 10 bps：**拒收** `common_risk_execution_rule_mismatch`
- 14｜刪除 SPY factor：**拒收** `common_risk_factor_identity_mismatch`
- 15｜beta window 改 126：**拒收** `common_risk_beta_window_mismatch`
- 16｜啟用 beta clipping：**拒收** `common_risk_beta_formula_mismatch`
- 17｜刪除 complete baseline：**拒收** `common_risk_baseline_mismatch`
- 18｜family 改 8 列：**拒收** `common_risk_family_contract_mismatch`
- 19｜tail 改 45 列：**拒收** `common_risk_stress_contract_mismatch`
- 20｜越權啟動 Paper：**拒收** `common_risk_decision_boundary_breached`
- 21｜共同 beta 樣本改 865：**拒收** `common_risk_coverage_repair_mismatch`

## 決策

本輪保留一個窄結論：對 eligible 的 raw 排名差並非全部由 QQQ beta 解釋；但它的共同
校正 p、完整現時股池、cohort factor 及 QQQ 下跌組均未通過。不得事後改 beta window、
clipping、factor、baseline、樣本起點或壓力列數救援，也不會建立新策略。

下一個具升級價值的證據仍是獲授權 point-in-time 成分、永久 ID、歷史行業、公司行動、
退市／收購實收及同步 RF。數據齊全後只准依既有事前登記原樣運行一次，再通過成本、
QQQ／SPY／逐期股池／同股漂移、NW／PSR／6,208-trial DSR／PBO 及前瞻 Paper 門檻。

- [第 26 輪父協議](SHORT_TERM_COMMON_RISK_RESIDUAL_PROTOCOL.md)
- [beta 覆蓋修復協議](SHORT_TERM_COMMON_RISK_RESIDUAL_COVERAGE_REPAIR_PROTOCOL.md)
- [第 25 輪相關性擁擠報告](SHORT_TERM_CORRELATION_CROWDING_RESEARCH_REPORT.md)
- [台股 tst_wocker 固定參考 commit](https://github.com/appr1ciat1/tst_wocker/tree/3372aa088328700feafeeb07c72ab832ea2d3ecb)
- [台股 tw-block-warrant 固定參考 commit](https://github.com/appr1ciat1/tw-block-warrant/tree/37463c54796ba36f4aac262519ea7fc2ef797de6)
- [台股 filter lab 固定參考 commit](https://github.com/appr1ciat1/tst_wocker_filter_lab/tree/06c87b7a1735877c9ccbab3a339c1742814a5058)

US$1,000 只作讀者比例示例。歷史及合成結果不保證未來回報；本報告不構成投資建議、
Paper 成交或實金落盤指令。
