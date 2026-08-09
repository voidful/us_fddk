# 美股短線第 38 輪：四窗動量共振替換式疊加研究報告

生成日期：2026-08-09

資料期：2006-08-04 至 2026-07-31

研究角色：同一批已見 survivor 事件的有界反證；不是正式 point-in-time 回測、即市買入名單、
Paper 或實金指令。

## 結論一覽

本輪按已推送事前協議，只測試 5／10／15／20 日動量 Top-7 的跨窗一致性。每宗事件只有
最少三窗共振的股票佔用七個固定分注，每隻只佔該 20% 資金槽的 1/7；未佔用分注繼續持有
QQQ。沒有搜尋窗口、門檻、持有期、市況開關或結果後 fallback。

20 bp 每資產來回成本下，US$1,000 候選期末值為 **US$22,654**、
CAGR **16.89%**；QQQ 買入並持有為 **US$21,797**、
**16.67%**，原第 30 輪 Top-7 為 **US$27,067**、
**17.94%**，相同比例 20 日動量路徑為 **US$26,632**、
**17.84%**。

事前二十項門檻通過 **11/20**，結論為
**未通過，不建立新策略**。未通過項目：候選 SHY 超額 Sharpe 高於 QQQ、候選 CAGR 高於原第 30 輪 Top-7 疊加、候選 CAGR 高於相同比例 20 日動量路徑、相對 QQQ 的日均差、NW、Holm 及共同 max-t 全部通過、相對三條 matched 路徑的 NW、Holm 及共同 max-t 全部通過、五個核心比較的固定前後半日均差全正、移除相對 QQQ 最佳三年後仍為正且 NW t 不低於 1.96、2008／2020／2022 及兩個事前 QQQ 市況組全部通過、6,229 trials、50／100 bp及移除 46 宗事件全部通過。

- 候選相對 QQQ 的 NW t 為 **0.19**，Holm／共同
  max-t／6,229 次全專案 p 為 **0.8519／
  1.0000／1.0000**；
- 相對 matched 20 日路徑的 NW t 為 **-1.56**，
  直接回答多窗共振有沒有單窗以外的增量；
- 移除相對 QQQ 最佳三年 2026, 2025, 2016 後，NW t 為
  **-1.43**；
- 移除事前定義的最有利 46 宗事件後，候選減 QQQ CAGR 為
  **-3.97%**；
- 無論本輪數字如何，`can_promote_from_this_round=false`、`new_strategy_created=false`。
  短線 Paper 維持全現金、持倉 0，實金動作 **US$0**。

## 共振選擇分布

905 宗事件平均有 **5.66** 隻候選，平均股票目標比例
**80.8%**；候選數範圍
2 至 7。候選不足七隻時
不會放大餘下股票；QQQ 承接所有未用分注。

| 每宗候選數 N | 事件數 | 股票目標比例 |
|---:|---:|---:|
| 0 | 0 | 0.0% |
| 1 | 0 | 14.3% |
| 2 | 1 | 28.6% |
| 3 | 26 | 42.9% |
| 4 | 98 | 57.1% |
| 5 | 240 | 71.4% |
| 6 | 333 | 85.7% |
| 7 | 207 | 100.0% |

排名以整數 rank-sum 作真正 tie-break，百分位只作展示。逐事件收據保留四窗 Top-7、共振次數、
最終選股、N/7 股票比例及 QQQ 餘額；最大分配 identity 誤差為
`0`。

## 九條固定完整資金路徑

| 固定路徑 | CAGR | US$1,000 終值 | SHY 超額 Sharpe | 最大跌幅 | 年率化換手 | 平均股票比例 | 成本拖累 |
|---|---:|---:|---:|---:|---:|---:|---:|
| 四窗三重共振／QQQ 部分替換 | 16.89% | US$22,654 | 0.71 | -52.48% | 29.4x | 55.3% | -3.48% |
| 相同比例 20 日排名／QQQ 部分替換 | 17.84% | US$26,632 | 0.73 | -53.51% | 29.3x | 55.2% | -3.51% |
| 相同比例合資格池／QQQ 部分替換 | 15.19% | US$16,883 | 0.67 | -50.77% | 29.3x | 55.3% | -3.43% |
| 相同比例完整現時股池／QQQ 部分替換 | 15.90% | US$19,096 | 0.69 | -53.07% | 29.3x | 55.2% | -3.45% |
| 第 30 輪原 Top-7／QQQ 全替換 | 17.94% | US$27,067 | 0.74 | -52.48% | 36.3x | 68.4% | -4.36% |
| 相同比例 QQQ 換手 placebo | 13.30% | US$12,127 | 0.58 | -54.50% | 29.3x | 55.2% | -3.37% |
| QQQ 買入並持有 | 16.67% | US$21,797 | 0.71 | -53.44% | 1.1x | 0.0% | -0.00% |
| SPY 買入並持有 | 11.26% | US$8,433 | 0.54 | -55.23% | 0.5x | 0.0% | -0.00% |
| SHY 買入並持有 | 1.94% | US$1,469 | -0.25 | -5.71% | 0.1x | 0.0% | -0.01% |

所有路徑由首次成交後保持 100% long、零現金及無槓桿。候選只對實際被替換比例收取 QQQ
沽出、股票買入、股票沽出及 QQQ 買回四個經濟腿；未替換的 QQQ 不收虛構成本。原 Top-7
與第 30 輪逐日最大殘差為 `1e-12`，
部分 QQQ 換手 placebo 最大殘差為 `0`。

## 八假說共同統計 family

| 候選相對基準 | 年率化算術差 | NW t | Holm p | 共同 max-t p | 全專案 p | 前半／後半日均 |
|---|---:|---:|---:|---:|---:|---:|
| 相同比例 20 日排名／QQQ 部分替換 | -0.91% | -1.56 | 0.4750 | 0.4500 | 1.0000 | -0.56／-0.17 bp |
| 相同比例合資格池／QQQ 部分替換 | +1.79% | 1.87 | 0.3056 | 0.2707 | 1.0000 | +0.50／+0.92 bp |
| 相同比例完整現時股池／QQQ 部分替換 | +1.11% | 0.91 | 0.7270 | 0.8799 | 1.0000 | +0.32／+0.57 bp |
| 第 30 輪原 Top-7／QQQ 全替換 | -0.98% | -1.36 | 0.5208 | 0.5883 | 1.0000 | -0.42／-0.35 bp |
| 相同比例 QQQ 換手 placebo | +3.25% | 1.99 | 0.2810 | 0.2185 | 1.0000 | +0.52／+2.06 bp |
| QQQ 買入並持有 | +0.30% | 0.19 | 0.8519 | 1.0000 | 1.0000 | -0.60／+0.84 bp |
| SPY 買入並持有 | +5.62% | 2.74 | 0.0427 | 0.0375 | 1.0000 | +1.42／+3.04 bp |
| SHY 買入並持有 | +16.26% | 3.61 | 0.0024 | 0.0022 | 1.0000 | +4.32／+8.58 bp |

八項比較共用 Newey–West lag 20、63-session circular blocks、20,000 條共同 bootstrap 路徑、
seed 38,202,608 及相同抽樣 indices。正式搜尋帳由 6,221 增至 6,229，沒有因本輪結果重設。

## 成本壓力

| 每資產來回成本 | 候選 CAGR | 候選減 QQQ | 候選減原 Top-7 | 候選減 matched 20 日 | 候選減 eligible | 候選減 complete |
|---:|---:|---:|---:|---:|---:|---:|
| 20 bp | 16.89% | +0.23% | -1.05% | -0.95% | +1.71% | +0.99% |
| 50 bp | 11.86% | -4.81% | +0.18% | -0.91% | +1.63% | +0.95% |
| 100 bp | 3.95% | -12.72% | +1.98% | -0.85% | +1.51% | +0.88% |

50／100 bp 同步重建九路，不會只提高候選成本。模型按成交名義收比例成本，未另計固定每單
佣金、買賣差價、市場衝擊、稅項及碎股限制；eligible／complete 持股數較多，這是重要限制。

## 已知市況、事件尾部與危機期

| 訊號日已知市況 | 事件數 | 平均候選數 | 平均股票比例 | 平均／中位事件差 |
|---|---:|---:|---:|---:|
| QQQ 20 日動量非負 | 677 | 5.54 | 79.2% | +54.85／+12.15 bp |
| QQQ 20 日動量負 | 228 | 5.99 | 85.6% | -19.23／-40.92 bp |

市況只使用訊號日已知的 QQQ 20 日動量，沒有 p 值，亦不會變成開關。最有利 46 宗事件以
事前固定候選減 QQQ gross difference 排序；六條 overlay 同時把相同事件改為全槽 QQQ，
沒有刪除日期或重排五槽。

| 年份 | 候選回報／最大跌幅 | QQQ 回報／最大跌幅 | 回報差 |
|---|---:|---:|---:|
| 2008 | -42.90%／-50.36% | -41.76%／-49.43% | -1.15% |
| 2020 | +36.54%／-29.01% | +48.41%／-28.56% | -11.87% |
| 2022 | -29.76%／-33.39% | -32.58%／-34.83% | +2.82% |

## 二十項事前反證門檻

- 協議、父收據、行情、觀察名單及參考 commit 精確：**通過**
- 第 29／30 輪 905 宗事件及 assignment 逐列重播：**通過**
- 五槽各 181 宗事件、無重疊及最大 concurrency 五個：**通過**
- 四窗 Top-7、共振次數、rank-sum 及最多七股精確：**通過**
- 候選與 matched 路徑的 N/7 股票比例及 QQQ 餘額精確：**通過**
- 九路每日資產、driver、成本、現金及無槓桿 identity：**通過**
- 原 Top-7 父路徑及部分 QQQ 換手 placebo 逐日一致：**通過**
- 候選 CAGR 高於 QQQ 買入並持有：**通過**
- 候選 US$1,000 期末值高於 QQQ：**通過**
- 候選 SHY 超額 Sharpe 高於 QQQ：**未通過**
- 候選最大跌幅不比 QQQ 深超過 5 個百分點：**通過**
- 候選 CAGR 高於原第 30 輪 Top-7 疊加：**未通過**
- 候選 CAGR 高於相同比例 20 日動量路徑：**未通過**
- 候選 CAGR 同時高於 eligible 及 complete matched 路徑：**通過**
- 相對 QQQ 的日均差、NW、Holm 及共同 max-t 全部通過：**未通過**
- 相對三條 matched 路徑的 NW、Holm 及共同 max-t 全部通過：**未通過**
- 五個核心比較的固定前後半日均差全正：**未通過**
- 移除相對 QQQ 最佳三年後仍為正且 NW t 不低於 1.96：**未通過**
- 2008／2020／2022 及兩個事前 QQQ 市況組全部通過：**未通過**
- 6,229 trials、50／100 bp及移除 46 宗事件全部通過：**未通過**

任何一項未通過即 `not_rejected_by_round38=false`。即使 20/20，本輪仍是同一已見 survivor
樣本，不能建立 Paper 或實金策略。

## 45 道固定控制

- 01 · `protocol_hash_commit`：通過
- 02 · `round30_receipt`：通過
- 03 · `round29_receipt`：通過
- 04 · `event_receipt`：通過
- 05 · `snapshot`：通過
- 06 · `panel`：通過
- 07 · `watchlist`：通過
- 08 · `reference_commits`：通過
- 09 · `905_events`：通過
- 10 · `25_cohort`：通過
- 11 · `four_windows`：通過
- 12 · `top7`：通過
- 13 · `three_window_threshold`：通過
- 14 · `integer_rank_sum`：通過
- 15 · `ticker_tie_break`：通過
- 16 · `percentile_display`：通過
- 17 · `n_over_7`：通過
- 18 · `qqq_remainder`：通過
- 19 · `d_plus_1`：通過
- 20 · `20_session_hold`：通過
- 21 · `five_slots`：通過
- 22 · `assignment_hash`：通過
- 23 · `qqq_base`：通過
- 24 · `four_leg_cost`：通過
- 25 · `20_50_100_costs`：通過
- 26 · `nine_paths`：通過
- 27 · `original_parent_identity`：通過
- 28 · `placebo_identity`：通過
- 29 · `shy_excess`：通過
- 30 · `full_exposure`：通過
- 31 · `no_leverage`：通過
- 32 · `daily_identity`：通過
- 33 · `actual_notional_cost_identity`：通過
- 34 · `eight_hypotheses`：通過
- 35 · `nw_lag20`：通過
- 36 · `bootstrap_63_20000`：通過
- 37 · `fixed_halves`：通過
- 38 · `crisis_years`：通過
- 39 · `known_at_regimes`：通過
- 40 · `best_three_years`：通過
- 41 · `tail_46`：通過
- 42 · `global_6229`：通過
- 43 · `survivor_identity`：通過
- 44 · `paper_zero`：通過
- 45 · `real_money_zero`：通過

45/45 只證明程式遵守已推送
協議，不證明未來盈利。

## 39 項單欄變異攻擊

| 攻擊 | 單欄變異 | 預期錯誤碼 | 結果 |
|---|---|---|---|
| 01 | protocol_sha256 | `resonance_protocol_hash_mismatch` | 拒收 |
| 02 | protocol_commit | `resonance_protocol_commit_mismatch` | 拒收 |
| 03 | round30_receipt_sha256 | `resonance_round30_receipt_mismatch` | 拒收 |
| 04 | round29_receipt_sha256 | `resonance_round29_receipt_mismatch` | 拒收 |
| 05 | event_receipt_sha256 | `resonance_event_receipt_mismatch` | 拒收 |
| 06 | snapshot_sha256 | `resonance_snapshot_mismatch` | 拒收 |
| 07 | panel_sha256 | `resonance_panel_mismatch` | 拒收 |
| 08 | watchlist_sha256 | `resonance_watchlist_mismatch` | 拒收 |
| 09 | reference_commits | `resonance_reference_mismatch` | 拒收 |
| 10 | expected_events | `resonance_event_count_mismatch` | 拒收 |
| 11 | expected_cohort | `resonance_cohort_mismatch` | 拒收 |
| 12 | momentum_windows | `resonance_windows_mismatch` | 拒收 |
| 13 | top_k | `resonance_top_k_mismatch` | 拒收 |
| 14 | resonance_minimum | `resonance_threshold_mismatch` | 拒收 |
| 15 | rank_tie_break | `resonance_rank_rule_mismatch` | 拒收 |
| 16 | percentile_display_only | `resonance_percentile_scope_mismatch` | 拒收 |
| 17 | stock_subslots | `resonance_subslots_mismatch` | 拒收 |
| 18 | partial_allocation_rule | `resonance_allocation_mismatch` | 拒收 |
| 19 | holding_sessions | `resonance_execution_clock_mismatch` | 拒收 |
| 20 | slot_count | `resonance_assignment_mismatch` | 拒收 |
| 21 | inactive_asset | `resonance_inactive_asset_mismatch` | 拒收 |
| 22 | primary_asset_round_trip_bps | `resonance_cost_mismatch` | 拒收 |
| 23 | four_legs_per_switched_subslot | `resonance_leg_mismatch` | 拒收 |
| 24 | path_ids | `resonance_path_family_mismatch` | 拒收 |
| 25 | family_baseline_ids | `resonance_hypothesis_family_mismatch` | 拒收 |
| 26 | shy_excess_proxy | `resonance_shy_proxy_mismatch` | 拒收 |
| 27 | hac_lag | `resonance_statistical_mismatch` | 拒收 |
| 28 | bootstrap_block_sessions | `resonance_bootstrap_mismatch` | 拒收 |
| 29 | bootstrap_paths | `resonance_bootstrap_mismatch` | 拒收 |
| 30 | bootstrap_seed | `resonance_bootstrap_mismatch` | 拒收 |
| 31 | global_search_trials | `resonance_global_trials_mismatch` | 拒收 |
| 32 | second_half_start | `resonance_half_clock_mismatch` | 拒收 |
| 33 | crisis_years | `resonance_crisis_mismatch` | 拒收 |
| 34 | best_year_removal_count | `resonance_best_year_mismatch` | 拒收 |
| 35 | favorable_event_removal_count | `resonance_tail_mismatch` | 拒收 |
| 36 | formal_readiness | `resonance_identity_mismatch` | 拒收 |
| 37 | current_identifiers_only | `resonance_identifier_scope_mismatch` | 拒收 |
| 38 | paper_authorized | `resonance_paper_boundary_breached` | 拒收 |
| 39 | real_money_authorized | `resonance_real_money_boundary_breached` | 拒收 |

所有變異須命中指定穩定錯誤碼；任何窗口、共振門檻、N/7 分注、QQQ 餘額、成本、父路徑、
family、統計或 Paper／實金權限漂移都會 fail closed。

## 市場與數據邊界

資料最後退出日為 **2026-07-31**，不是即市行情。股票仍是 2026 現時
survivor cohort，欠缺逐期成分、永久證券 ID、可靠退市／退出經濟、歷史公司行動及公告時間。
調整 OHLC、分數股與 US$1,000 只供比例研究，不能冒充真實券商成交或稅後結果。

正式就緒仍為 **1/18**，point-in-time
**1/20**，合資格 provider package 0，正式策略 run 0。
下一個可升格步驟仍是獲授權逐期成分、永久 ID、公司行動及退市資料，原樣執行既有正式
預先登記；不得用本輪結果重選參數。

## 可重播檔案

- [第 38 輪事前協議](SHORT_TERM_MULTI_WINDOW_RESONANCE_PROTOCOL.md)
- `artifacts/short_term_multi_window_resonance_validation.json`
- `site/data/short-term-multi-window-resonance.json`
