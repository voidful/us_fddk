# 美股短線第 29 輪：日曆時間資金佔用與五槽組合回測

生成日期：2026-08-04

資料期：2006-08-04 至 2026-07-31

研究角色：同一已見 survivor cohort 的資金層反證；不是正式 point-in-time 回測、買入名單或實金指令。

## 結論一覽

把 905 個重疊事件放回同一條日曆時間線，並以五個互不重疊資金槽、每槽 20%、不借貸方式
核算後，Top-7 候選在 20 bp 來回成本下由 **US$1,000** 累積至
**US$10,189**，CAGR **12.3%**、SHY 超額 Sharpe
**0.67**、最大跌幅 **-38.7%**。

但這不是升格結果：

- QQQ 買入並持有同期 CAGR **16.7%**、終值 **US$21,797**，
  明顯高於 Top-7；SPY CAGR **11.3%**，亦接近 Top-7；
- Top-7 對完整現時股池的 NW t 只有 **1.51**；
- 前後半一致性未通過；移除最佳三年 2026, 2009, 2025 後，
  對合資格池 NW t 只餘 **1.55**；
- 對合資格池的局部 Holm／共同 max-t p 為 **0.0343／
  0.0301**，但 6,214 次全專案 Bonferroni p 為
  **1.0000**，未能排除多重搜尋；
- 十八項事前門檻只過 **13/18**。

因此正式就緒仍是 **1/18**、point-in-time
**1/20**、合資格資料包 **0**、正式策略 run **0**。
短線 Paper 維持全現金、持倉 **0**；US$1,000 只是讀者換算例子，實金動作 **US$0**。

## 七條固定基準與資金結果

| 固定日曆路徑 | CAGR | 終值（US$1,000） | SHY 超額 Sharpe | 最大跌幅 | 年率化換手 | 平均持倉比重 |
|---|---:|---:|---:|---:|---:|---:|
| Top-7 五槽 | 12.3% | US$10,189 | 0.67 | -38.7% | 18.1x | 72.0% |
| 合資格池等權五槽 | 9.6% | US$6,249 | 0.59 | -37.0% | 18.1x | 72.0% |
| 完整現時股池等權五槽 | 10.3% | US$7,138 | 0.63 | -39.4% | 18.1x | 72.0% |
| QQQ 事件配對五槽 | 7.6% | US$4,333 | 0.44 | -40.6% | 18.1x | 72.0% |
| QQQ 買入並持有 | 16.7% | US$21,797 | 0.71 | -53.4% | 1.1x | 100.0% |
| SPY 買入並持有 | 11.3% | US$8,433 | 0.54 | -55.2% | 0.5x | 100.0% |
| SHY 買入並持有 | 1.9% | US$1,469 | -0.25 | -5.7% | 0.1x | 100.0% |

所有路徑由同一 5,028 個美股交易日計算。Top-7 年率化換手
**18.1 倍**、平均持倉比重 **72.0%**；
20 bp 成本令 CAGR 減少 **2.0%**，終值少
**US$4,381**。因此不能以「每宗交易平均回報」直接當成
可投資組合回報。

## 六基準共同統計 family

| Top-7 相對固定基準 | 年率化算術差 | NW t | Holm p | 共同 max-t p | 前半日均差 | 後半日均差 |
|---|---:|---:|---:|---:|---:|---:|
| 合資格池等權五槽 | +2.82% | 2.70 | 0.0343 | 0.0301 | +1.13 bp | +1.11 bp |
| 完整現時股池等權五槽 | +2.14% | 1.51 | 0.2719 | 0.3797 | +0.89 bp | +0.81 bp |
| QQQ 事件配對五槽 | +4.57% | 2.29 | 0.0886 | 0.0832 | +1.17 bp | +2.45 bp |
| QQQ 買入並持有 | -4.97% | -1.69 | 0.2719 | 0.2797 | -2.67 bp | -1.28 bp |
| SPY 買入並持有 | +0.34% | 0.13 | 0.8977 | 1.0000 | -0.65 bp | +0.92 bp |
| SHY 買入並持有 | +10.98% | 3.08 | 0.0123 | 0.0092 | +2.25 bp | +6.46 bp |

六項比較共用 NW lag 20、63-session circular block、20,000 條 bootstrap 路徑及 seed
29,202,608。Top-7 對 QQQ 買入並持有的日均差為負；對 SPY 的 NW t 接近零。局部對
合資格池可見差異，不足以跨越完整基準、時間切割及全專案多重搜尋。

## 交易成本壓力

| 來回交易成本 | Top-7 CAGR | 終值 | 合資格池 CAGR | 完整現時股池 CAGR | QQQ event CAGR |
|---|---:|---:|---:|---:|---:|
| 20 bp | 12.3% | US$10,189 | 9.6% | 10.3% | 7.6% |
| 50 bp | 9.3% | US$5,951 | 6.7% | 7.4% | 4.7% |
| 100 bp | 4.5% | US$2,420 | 2.0% | 2.7% | 0.1% |

100 bp 下 Top-7 CAGR 降至
**4.5%**。候選仍高於三個
事件式基準，只說明相對排名未反轉；不等於已補回 survivor、退市、滑價容量、稅項及零碎股
成交等正式缺口。

## 危機年份

| 年份 | Top-7 回報 / 最大跌幅 | QQQ 買入並持有 | SPY 買入並持有 | SHY 買入並持有 |
|---|---:|---:|---:|---:|
| 2008 | -33.29% / -33.4% | -41.76% | -36.83% | +6.63% |
| 2020 | +7.60% / -23.2% | +48.41% | +18.34% | +3.04% |
| 2022 | -25.72% / -27.6% | -32.58% | -18.18% | -3.88% |

2008 及 2022 均錄得明顯虧損；2020 的正回報亦落後 QQQ。策略不是低風險現金替代品，亦未
建立對不同市場狀況都穩定的高回報證據。

## 十八項事前門檻

- 所有固定輸入、父收據、行情、watchlist 與參考 commit 精確：**通過**
- 905 個四路事件淨回報逐列重建：**通過**
- assignment SHA、五槽、每槽 181 事件及最大 concurrency 精確：**通過**
- 日線槽位、現金、無槓桿、成本及總資產 identity 全通過：**通過**
- 候選 CAGR 高於合資格池五槽：**通過**
- 候選 CAGR 高於完整現時股池五槽：**通過**
- 候選 CAGR 高於 QQQ event 五槽：**通過**
- 候選 CAGR 高於 QQQ 買入並持有：**未通過**
- 候選 CAGR 高於 SPY 買入並持有：**通過**
- 候選 SHY-excess Sharpe 為正且高於三個事件五槽基準：**通過**
- 候選最大跌幅不比 QQQ buy-hold 深超過十個百分點：**通過**
- 候選對 eligible 平均日差為正且 NW t 不低於 1.96：**通過**
- 候選對 complete 平均日差為正且 NW t 不低於 1.96：**未通過**
- 候選對 QQQ event 平均日差為正且 NW t 不低於 1.96：**通過**
- 候選對 eligible／complete／QQQ buy-hold／SPY 的前後半平均日差全正：**未通過**
- 候選對 eligible 的 Holm 與共同 max-t p 均不高於 0.05：**通過**
- 移除最佳三年後候選對 eligible 仍為正且 NW t 不低於 1.96：**未通過**
- 6,214 次 Bonferroni 通過且 50／100 bps 仍勝三個事件基準：**未通過**

## 二十五道資料、資金、統計及決策控制

- 01 · protocol SHA 與 commit：通過
- 02 · 第 28 輪收據：通過
- 03 · 第 27 輪收據：通過
- 04 · 第 24 輪收據：通過
- 05 · 原始事件收據：通過
- 06 · 行情 archive 與 panel：通過
- 07 · watchlist：通過
- 08 · 三個台股參考 commit：通過
- 09 · 905 事件次序與邊界：通過
- 10 · 完整現時 cohort 25 隻：通過
- 11 · 20／60 日訊號與 Top-7：通過
- 12 · D+1 open 至第 20 session close：通過
- 13 · 五槽 assignment：通過
- 14 · 每槽 20% 及 181 事件：通過
- 15 · 20／50／100 bps 成本：通過
- 16 · 七條固定日曆路徑：通過
- 17 · SHY excess 定義：通過
- 18 · 日線資產與現金 identity：通過
- 19 · 路徑同起訖日：通過
- 20 · 六假說 family：通過
- 21 · NW lag 20：通過
- 22 · 63-session／20,000 路徑共同 bootstrap：通過
- 23 · 固定半期與危機／尾部：通過
- 24 · 全專案 6,214 trials：通過
- 25 · 現時身份及 Paper／實金邊界：通過

25/25 只證明程式按凍結協議重播，並不證明策略將來會盈利。

## 二十五項單欄變異攻擊

| 攻擊 | 單欄變異 | 預期錯誤碼 | 結果 |
|---|---|---|---|
| 01 | 協議 SHA 漂移 | `calendar_capital_protocol_hash_mismatch` | 拒收 |
| 02 | 協議 commit 漂移 | `calendar_capital_protocol_commit_mismatch` | 拒收 |
| 03 | 第 28 輪收據漂移 | `calendar_capital_round28_receipt_mismatch` | 拒收 |
| 04 | 第 27 輪收據漂移 | `calendar_capital_round27_receipt_mismatch` | 拒收 |
| 05 | 第 24 輪收據漂移 | `calendar_capital_round24_receipt_mismatch` | 拒收 |
| 06 | 原始事件收據漂移 | `calendar_capital_event_receipt_mismatch` | 拒收 |
| 07 | 行情 archive 漂移 | `calendar_capital_market_data_mismatch` | 拒收 |
| 08 | watchlist 漂移 | `calendar_capital_watchlist_mismatch` | 拒收 |
| 09 | 台股參考 commit 漂移 | `calendar_capital_reference_mismatch` | 拒收 |
| 10 | 事件改 904 | `calendar_capital_event_count_mismatch` | 拒收 |
| 11 | 完整 cohort 改 24 | `calendar_capital_cohort_mismatch` | 拒收 |
| 12 | Top-K 改 10 | `calendar_capital_signal_rule_mismatch` | 拒收 |
| 13 | 持有期改 10 日 | `calendar_capital_execution_clock_mismatch` | 拒收 |
| 14 | 槽位改四個 | `calendar_capital_slot_contract_mismatch` | 拒收 |
| 15 | assignment SHA 漂移 | `calendar_capital_assignment_mismatch` | 拒收 |
| 16 | 初始資本改 US$10,000 | `calendar_capital_initial_capital_mismatch` | 拒收 |
| 17 | 主要成本改 10 bps | `calendar_capital_cost_contract_mismatch` | 拒收 |
| 18 | 刪除 QQQ buy-hold | `calendar_capital_baseline_family_mismatch` | 拒收 |
| 19 | 取消 SHY excess | `calendar_capital_excess_proxy_mismatch` | 拒收 |
| 20 | NW lag 改 4 | `calendar_capital_statistical_contract_mismatch` | 拒收 |
| 21 | bootstrap block 改 20 | `calendar_capital_bootstrap_contract_mismatch` | 拒收 |
| 22 | 全專案 trials 重設 | `calendar_capital_global_trials_mismatch` | 拒收 |
| 23 | 半期起點漂移 | `calendar_capital_half_clock_mismatch` | 拒收 |
| 24 | 刪除 2022 危機 | `calendar_capital_stress_contract_mismatch` | 拒收 |
| 25 | 越權啟動 Paper | `calendar_capital_decision_boundary_breached` | 拒收 |

所有突變均命中事前指定錯誤碼。任何輸入收據、成本、槽位、統計 family 或 Paper 權限漂移，
主路徑都會在產生結果前 fail closed。

## 市場狀況與下一道證據

本資料截至 **2026-07-31**，不是 2026-08-04 即市行情。最新可計算的
2026 年段落對多數基準較強，亦正是移除最佳三年壓力首先剔除的年份；不可把這段短樣本當成
已確認的新市況優勢。

下一道可升格證據仍是合法授權的 point-in-time 成分、永久識別碼、歷史行業、公司行動及
退市／退出經濟，再以凍結規則建立第一段真正未見樣本。取得前不再用同一 survivor 樣本調整
Top-K、持有期或市況篩選作事後救援。

## 可重播檔案

- [第 29 輪事前協議](SHORT_TERM_CALENDAR_CAPITAL_ACCOUNTING_PROTOCOL.md)
- `artifacts/short_term_calendar_capital_accounting_validation.json`
- `site/data/short-term-calendar-capital-accounting.json`
