# 美股短線第 30 輪：QQQ 全投資替換式疊加研究報告

生成日期：2026-08-04

資料期：2006-08-04 至 2026-07-31

研究角色：同一已見 survivor cohort 的全投資反證；不是正式 point-in-time 回測、買入名單、
Paper 或實金指令。

## 結論一覽

第 29 輪候選平均只有 72% 股票持倉。本輪依事前協議把每個閒置槽放入 QQQ，只在原事件
窗口把該 20% 槽位替換成 Top-7；沒有改 Top-K、持有期、訊號、事件或五槽 assignment。
主要成本為每資產 20 bp round trip，即正常替換事件四腿合計名義 40 bp。

20 bp 下，候選由 **US$1,000** 增至 **US$27,067**，CAGR
**17.94%**；QQQ 買入並持有為 **US$21,797**、
**16.67%**。這是第一個在相同已見日曆內，headline 終值高於 QQQ 的完整資金
路徑，但仍然 **不升格**：

- 候選相對 QQQ 的 NW t 只有 **0.66**，Holm／共同
  max-t p 為 **0.5117／0.9368**；
- 6,221 次全專案 Bonferroni p 為 **1.0000**；
- 相對 complete overlay 的 NW t 只有 **1.57**；
- 移除相對 QQQ 最佳三年 2026, 2025, 2016 後，平均差轉負，NW t
  **-0.97**；
- 每資產 50／100 bp 時，候選 CAGR 分別落後 QQQ
  **4.98%／
  14.70%**；
- 移除最有利 46 宗事件後，候選 CAGR 落後 QQQ
  **3.76%**，並落後 complete overlay
  **1.07%**；
- 二十項事前門檻只過 **13/20**；
  未通過：候選對 complete 平均日差正且 NW t 不低於 1.96、候選對 QQQ 平均日差正且 NW t 不低於 1.96、候選對 QQQ 的 Holm 及共同 max-t p 均不高於 0.05、候選對 QQQ／eligible／complete 前後半平均日差全正、移除相對 QQQ 最佳三年後平均差正且 NW t 不低於 1.96、2008／2020／2022 回報不低於 QQQ且最大跌幅不深超過 5pp、6,221 trials、50／100 bps及移除 46 有利事件全部通過。

因此 `not_rejected_by_round30=false`、`new_strategy_created=false`。正式就緒仍為
**1/18**、point-in-time **1/20**、
合資格資料包 **0**、正式策略 run **0**。短線 Paper 維持全現金、持倉 **0**；US$1,000
只是歷史尺度示例，實金動作 **US$0**。

## 八條固定資金路徑

| 固定路徑 | CAGR | US$1,000 終值 | SHY 超額 Sharpe | 最大跌幅 | 年率化換手 | 平均股票持倉 |
|---|---:|---:|---:|---:|---:|---:|
| Top-7／QQQ 替換式疊加 | 17.94% | US$27,067 | 0.74 | -52.48% | 36.3x | 100.0% |
| 合資格池／QQQ 替換式疊加 | 15.13% | US$16,703 | 0.67 | -50.66% | 36.3x | 100.0% |
| 完整現時股池／QQQ 替換式疊加 | 15.82% | US$18,832 | 0.69 | -53.41% | 36.3x | 100.0% |
| QQQ 同時鐘換手 placebo | 12.51% | US$10,552 | 0.55 | -54.65% | 36.3x | 100.0% |
| Top-7 五槽現金路徑 | 12.31% | US$10,189 | 0.67 | -38.74% | 18.1x | 72.0% |
| QQQ 買入並持有 | 16.67% | US$21,797 | 0.71 | -53.44% | 1.1x | 100.0% |
| SPY 買入並持有 | 11.26% | US$8,433 | 0.54 | -55.23% | 0.5x | 100.0% |
| SHY 買入並持有 | 1.94% | US$1,469 | -0.25 | -5.71% | 0.1x | 100.0% |

候選由首次可成交日起維持 100% long、零現金及無槓桿；共核算
**3,626** 個交易腿。QQQ placebo
逐日價值與「相同 QQQ 價格路徑 × 累積成本」的最大誤差只有
`0`。

headline 高於 QQQ 的幅度只有 **+1.27%／年**，而候選
年率化換手為 **36.3 倍**；成本與年份集中足以改變結論。

## 七基準共同統計 family

| 候選相對基準 | 年率化算術差 | NW t | Holm p | 共同 max-t p | 全專案 p | 前半／後半日均 |
|---|---:|---:|---:|---:|---:|---:|
| 合資格池／QQQ 替換式疊加 | +2.82% | 2.77 | 0.0222 | 0.0236 | 1.0000 | +1.16／+1.08 bp |
| 完整現時股池／QQQ 替換式疊加 | +2.16% | 1.57 | 0.2346 | 0.3511 | 1.0000 | +0.97／+0.75 bp |
| QQQ 同時鐘換手 placebo | +4.92% | 2.51 | 0.0358 | 0.0483 | 1.0000 | +1.18／+2.73 bp |
| Top-7 五槽現金路徑 | +6.26% | 3.15 | 0.0097 | 0.0071 | 1.0000 | +2.49／+2.48 bp |
| QQQ 買入並持有 | +1.28% | 0.66 | 0.5117 | 0.9368 | 1.0000 | -0.18／+1.20 bp |
| SPY 買入並持有 | +6.60% | 3.06 | 0.0111 | 0.0099 | 1.0000 | +1.84／+3.39 bp |
| SHY 買入並持有 | +17.24% | 3.78 | 0.0011 | 0.0009 | 0.9950 | +4.74／+8.94 bp |

七項比較共用 Newey–West lag 20、63-session circular blocks、20,000 條共同 bootstrap
路徑及 seed 30,202,608。候選對 eligible overlay 的局部結果較強，但完整股池、QQQ、固定
半期及全研究多重搜尋沒有同時通過；不得只選局部顯著列。

## 成本壓力

| 每資產來回成本 | 正常事件名義總成本 | 候選 CAGR | QQQ CAGR | eligible overlay | complete overlay | 候選減 QQQ |
|---|---:|---:|---:|---:|---:|---:|
| 20 bp | 40 bp | 17.94% | 16.67% | 15.13% | 15.82% | +1.27% |
| 50 bp | 100 bp | 11.68% | 16.67% | 9.02% | 9.67% | -4.98% |
| 100 bp | 200 bp | 1.97% | 16.67% | -0.47% | 0.13% | -14.70% |

每資產成本由 20 bp 增至 50 bp 時，headline 已由領先 QQQ轉為落後。這不是微小敏感度：
每個正常事件同時交易 QQQ 與股票籃子，故 50 bp 資產 round trip 代表名義 100 bp 事件
切換成本，100 bp 代表名義 200 bp。回測未另計個人稅項、買賣差價、市場衝擊及碎股限制。

## 時間、事件尾部與危機期

- 移除最佳三年後剩 4,381 個 session，候選相對 QQQ 年率化算術差
  -1.83%，NW t
  -0.97。
- 移除的 46 宗事件由 2007-10-26 至
  2026-05-29；規則在結果前固定以 Top-7 相對 QQQ event gross
  difference 排序，三個 overlay 同時移除，沒有只打擊候選。

| 年份 | 候選回報／最大跌幅 | QQQ 回報／最大跌幅 | 候選減 QQQ 回報 |
|---|---:|---:|---:|
| 2008 | -42.99%／-50.35% | -41.76%／-49.43% | -1.23% |
| 2020 | +29.81%／-30.35% | +48.41%／-28.56% | -18.60% |
| 2022 | -28.65%／-30.96% | -32.58%／-34.83% | +3.93% |

三個危機期沒有全部同時跑贏 QQQ及守住最大跌幅上限，因此危機門檻未通過。候選是高股票比重
替換策略，不是現金、短債或低風險替代品。

## 二十項事前門檻

- 所有固定輸入、父收據、行情、watchlist 與參考 commit 精確：**通過**
- 905 事件、四路回報及 assignment 逐列重播：**通過**
- 五槽各 181 事件、無重疊及最大五個 concurrent interval：**通過**
- 八路同日曆及 overlay 資產、driver、成本 identity：**通過**
- 首次成交後 100% long、零現金及無槓桿：**通過**
- QQQ placebo 價格路徑及換手成本逐日重建：**通過**
- 候選 CAGR 高於 QQQ 買入並持有：**通過**
- 候選 US$1,000 期末值高於 QQQ：**通過**
- 候選 SHY-excess Sharpe 高於 QQQ：**通過**
- 候選最大跌幅不比 QQQ 深超過 5pp：**通過**
- 候選 CAGR 高於 eligible overlay：**通過**
- 候選 CAGR 高於 complete overlay：**通過**
- 候選對 eligible 平均日差正且 NW t 不低於 1.96：**通過**
- 候選對 complete 平均日差正且 NW t 不低於 1.96：**未通過**
- 候選對 QQQ 平均日差正且 NW t 不低於 1.96：**未通過**
- 候選對 QQQ 的 Holm 及共同 max-t p 均不高於 0.05：**未通過**
- 候選對 QQQ／eligible／complete 前後半平均日差全正：**未通過**
- 移除相對 QQQ 最佳三年後平均差正且 NW t 不低於 1.96：**未通過**
- 2008／2020／2022 回報不低於 QQQ且最大跌幅不深超過 5pp：**未通過**
- 6,221 trials、50／100 bps及移除 46 有利事件全部通過：**未通過**

## 二十九道資料、換倉、統計及決策控制

- 01 · protocol SHA 與 commit：通過
- 02 · 第 29 輪收據：通過
- 03 · 原始事件收據：通過
- 04 · 行情 archive 與 panel：通過
- 05 · watchlist：通過
- 06 · 三個台股參考 commit：通過
- 07 · 905 事件及日期邊界：通過
- 08 · 現時 cohort 25 隻：通過
- 09 · 20／60 日及 Top-7：通過
- 10 · D+1 open 至第 20 session close：通過
- 11 · 五槽 assignment：通過
- 12 · 五槽各 181 事件：通過
- 13 · 非事件底倉 QQQ：通過
- 14 · 20／50／100 bps 資產 round trip：通過
- 15 · 正常事件四腿成本：通過
- 16 · 八條固定路徑：通過
- 17 · 七假說 family：通過
- 18 · SHY excess 定義：通過
- 19 · overlay 100% 股票比重：通過
- 20 · overlay 零現金及無槓桿：通過
- 21 · 日線資產與 driver identity：通過
- 22 · QQQ placebo identity：通過
- 23 · 路徑同起訖日：通過
- 24 · NW lag 20：通過
- 25 · 63-session／20,000 共同 bootstrap：通過
- 26 · 固定半期與三個危機年：通過
- 27 · 最佳三年及 46-event 尾部：通過
- 28 · 全專案 6,221 trials：通過
- 29 · 現時身份及 Paper／實金邊界：通過

29/29 只證明程式遵守已推送協議；不證明未來會盈利。

## 二十九項單欄變異攻擊

| 攻擊 | 單欄變異 | 預期錯誤碼 | 結果 |
|---|---|---|---|
| 01 | 協議 SHA 漂移 | `qqq_overlay_protocol_hash_mismatch` | 拒收 |
| 02 | 協議 commit 漂移 | `qqq_overlay_protocol_commit_mismatch` | 拒收 |
| 03 | 第 29 輪收據漂移 | `qqq_overlay_round29_receipt_mismatch` | 拒收 |
| 04 | 原始事件收據漂移 | `qqq_overlay_event_receipt_mismatch` | 拒收 |
| 05 | 行情 archive 漂移 | `qqq_overlay_market_data_mismatch` | 拒收 |
| 06 | watchlist 漂移 | `qqq_overlay_watchlist_mismatch` | 拒收 |
| 07 | 台股參考 commit 漂移 | `qqq_overlay_reference_mismatch` | 拒收 |
| 08 | 事件改 904 | `qqq_overlay_event_count_mismatch` | 拒收 |
| 09 | 完整 cohort 改 24 | `qqq_overlay_cohort_mismatch` | 拒收 |
| 10 | Top-K 改 10 | `qqq_overlay_signal_rule_mismatch` | 拒收 |
| 11 | 持有期改 10 日 | `qqq_overlay_execution_clock_mismatch` | 拒收 |
| 12 | 槽位改四個 | `qqq_overlay_assignment_mismatch` | 拒收 |
| 13 | 初始資本改 US$10,000 | `qqq_overlay_initial_capital_mismatch` | 拒收 |
| 14 | 非事件底倉改 SPY | `qqq_overlay_inactive_asset_mismatch` | 拒收 |
| 15 | 主要成本改 10 bps | `qqq_overlay_cost_contract_mismatch` | 拒收 |
| 16 | 取消四腿換倉 | `qqq_overlay_leg_contract_mismatch` | 拒收 |
| 17 | 刪除 QQQ buy-hold | `qqq_overlay_baseline_family_mismatch` | 拒收 |
| 18 | 刪除一個 family baseline | `qqq_overlay_baseline_family_mismatch` | 拒收 |
| 19 | 取消 SHY excess | `qqq_overlay_excess_proxy_mismatch` | 拒收 |
| 20 | NW lag 改 4 | `qqq_overlay_statistical_contract_mismatch` | 拒收 |
| 21 | bootstrap block 改 20 | `qqq_overlay_bootstrap_contract_mismatch` | 拒收 |
| 22 | bootstrap seed 漂移 | `qqq_overlay_bootstrap_contract_mismatch` | 拒收 |
| 23 | 全專案 trials 重設 | `qqq_overlay_global_trials_mismatch` | 拒收 |
| 24 | 半期起點漂移 | `qqq_overlay_half_clock_mismatch` | 拒收 |
| 25 | 刪除 2022 危機 | `qqq_overlay_stress_contract_mismatch` | 拒收 |
| 26 | 尾部移除改 20 事件 | `qqq_overlay_stress_contract_mismatch` | 拒收 |
| 27 | 取消現時身份警告 | `qqq_overlay_identifier_scope_mismatch` | 拒收 |
| 28 | 越權啟動 Paper | `qqq_overlay_decision_boundary_breached` | 拒收 |
| 29 | 越權啟動實金 | `qqq_overlay_decision_boundary_breached` | 拒收 |

所有變異均命中指定錯誤碼。任何 protocol、父收據、QQQ 底倉、四腿成本、路徑、統計
family、尾部或 Paper 權限漂移，都會在輸出結果前 fail closed。

## 市場與數據邊界

本資料最後退出日為 **2026-07-31**，不是 2026-08-04 即市
行情。股票仍是 2026 現時 survivor cohort，沒有可靠逐期成分、永久 ID、歷史行業、公司
行動、退市及實際退出經濟；候選 headline 的相對優勢不能修復這個主要偏差。

下一個可升級步驟仍是合格 point-in-time／退市數據 20/20，按既有正式預先登記運行一次，
再累積至少 252 個新增 session 及 12 次換倉的前瞻 Paper 門檻。取得前不會依本輪結果調整
Top-K、事件期、QQQ 底倉或成本門檻。

## 可重播檔案

- [第 30 輪事前協議](SHORT_TERM_QQQ_REPLACEMENT_OVERLAY_PROTOCOL.md)
- `artifacts/short_term_qqq_replacement_overlay_validation.json`
- `site/data/short-term-qqq-replacement-overlay.json`
