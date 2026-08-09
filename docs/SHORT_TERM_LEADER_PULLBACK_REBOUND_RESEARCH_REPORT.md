# 美股短線第 39 輪：龍頭回調—回升 10 日確認研究報告

生成日期：2026-08-09

資料期：2006-08-04 至
2026-07-31

研究角色：同一批已見 survivor 股票的只讀反證；不是 point-in-time 回測、最新買入名單、
Paper 或實金指令。

機器收據的固定 family、壓力、門檻、控制及攻擊列完整。

## 結論一覽

本輪只測試事前固定的龍頭回調—回升結構：原 20 日 Top-7 中，訊號日同時符合 3%–16%
回調、收市回升及 reward/risk 不低於 1.60 的股票，每隻只佔事件槽位 1/7；其餘持有 QQQ。
訊號後下一個 session 調整開市買入，第 10 個 session 調整收市沽出。target 及 stop 只用作
訊號日結構計算，持有期不執行止賺或止蝕。

主要成本下，US$1,000 候選期末值為 **US$21,479**、
CAGR **16.58%**、SHY 超額 Sharpe
**0.71**、最大跌幅
**-53.33%**。QQQ 買入並持有期末值為
**US$21,756**、CAGR **16.66%**。

二十二項事前門檻通過 **8/22**，結論為 **未通過，不建立新策略**。
未通過項目：固定輸入精確，但 protocol 的交易日起訖與 5,028 列敘述內部不一致、N、Top-7 子集、N/7、QQQ 餘額及非空事件下限、候選 CAGR 高於 QQQ、候選 US$1,000 期末值高於 QQQ、候選 SHY-excess Sharpe 高於 QQQ、候選 CAGR 高於 matched Top-N、候選對 QQQ 日差、NW、Holm 及共同 max-t、候選對四條公平股票基準日差、NW、Holm 及 max-t、QQQ 與四條公平股票基準前後半日差全正、移除相對 QQQ 最佳三年後日差及 NW、2008／2020／2022 回報及跌幅不遜於 QQQ、QQQ 20 日動量正負兩組事件增量均正、候選對 QQQ 的 6,237 次 Bonferroni p 不高於 0.05、25／50bps、US$0.01 子委託費及移除 46 宗後仍勝五基準。

無論本輪數字如何，固定 `can_promote_from_this_round=false`、
`new_strategy_created=false`、`paper_status=all_cash_not_started`。短線 Paper 維持全現金、
持倉 **0**，實金動作 **US$0**。

## 選擇與特徵分布

| 每宗確認股票數 N | 事件數 | 股票目標比例 |
|---:|---:|---:|
| 0 | 754 | 0.0% |
| 1 | 110 | 14.3% |
| 2 | 27 | 28.6% |
| 3 | 7 | 42.9% |
| 4 | 3 | 57.1% |
| 5 | 3 | 71.4% |
| 6 | 1 | 85.7% |
| 7 | 0 | 100.0% |

- `minimum_candidates`：0
- `maximum_candidates`：6
- `mean_candidates`：0.240883977901
- `nonempty_events`：151
- `nonempty_first_half_events`：68
- `nonempty_second_half_events`：83
- `mean_stock_target_fraction`：0.034411996843
- `maximum_allocation_residual`：0.0

| 結構特徵 | 最小值 | 中位數 | 平均值 | 最大值 |
|---|---:|---:|---:|---:|
| 回調 | 0.0000 | 0.0062 | 0.0151 | 0.2188 |
| Reward/risk | 0.1509 | 0.6648 | 1.0641 | 6.6490 |

逐事件收據須保留 ATR14、20／60 日收市高位、10 日低位、pullback、rebound、target、stop、
reward/risk、確認股票及 N/7 分配；報告不呈列最新逐股名單。

## 日曆、自洽性、concurrency 與委託帳

凍結協議的日曆敘述有不可回改的內部矛盾：表列由 2006-08-07 至 2026-07-31
共有 5,028 列，但實際比較交易期只有 **5,027**
列。為保留父收據，第 39 輪仍保存 2006-08-04 的 **1**
列成交前現金，總日曆才是 **5,028** 列。系統沒有改寫協議；
`protocol_calendar_internal_consistency=false`，因此 `exact_inputs` 門檻
**未通過**。

十日事件實際最大 concurrency 為
**3**，事前上限為 5；通過上限
不會抵銷上述日曆矛盾。

| 路徑 | 預期子委託 | 實際子委託 | 差額 |
|---|---:|---:|---:|
| 龍頭回調—回升確認／QQQ 部分替換 | 747 | 747 | +0 |
| 相同比例原 Top-N／QQQ 部分替換 | 747 | 747 | +0 |
| 相同比例合資格池／QQQ 部分替換 | 4,605 | 4,605 | +0 |
| 相同比例完整現時股池／QQQ 部分替換 | 7,861 | 7,861 | +0 |
| 原 Top-7 十日／QQQ 全替換 | 14,488 | 14,488 | +0 |
| 相同比例 QQQ 換手 placebo | 613 | 613 | +0 |
| QQQ 買入並持有 | 2 | 2 | +0 |
| SPY 買入並持有 | 2 | 2 | +0 |
| SHY 買入並持有 | 2 | 2 | +0 |

九路預期與實際子委託須完全相同。最終狀態
**全現金、零持倉**；候選的 primary、
US$0.01 及 US$0.05 固定費 ledger 均只保存在機器收據，不在報告列出最新逐股名單：

- `primary_10bps_per_leg`：747 列已保存於機器收據。
- `fixed_fee_0.01_usd`：747 列已保存於機器收據。
- `fixed_fee_0.05_usd`：747 列已保存於機器收據。

## 九條固定完整資金路徑

| 固定路徑 | CAGR | US$1,000 期末值 | SHY 超額 Sharpe | 最大跌幅 | 年率化換手 | 平均股票比例 | 子委託數 |
|---|---:|---:|---:|---:|---:|---:|---:|
| 龍頭回調—回升確認／QQQ 部分替換 | 16.58% | US$21,479 | 0.71 | -53.33% | 1.3x | 1.1% | 747 |
| 相同比例原 Top-N／QQQ 部分替換 | 16.64% | US$21,674 | 0.71 | -52.44% | 1.3x | 1.1% | 747 |
| 相同比例合資格池／QQQ 部分替換 | 16.56% | US$21,407 | 0.71 | -53.05% | 1.3x | 1.1% | 4,605 |
| 相同比例完整現時股池／QQQ 部分替換 | 16.58% | US$21,471 | 0.71 | -53.28% | 1.3x | 1.1% | 7,861 |
| 原 Top-7 十日／QQQ 全替換 | 14.99% | US$16,312 | 0.65 | -52.20% | 36.3x | 32.4% | 14,488 |
| 相同比例 QQQ 換手 placebo | 16.51% | US$21,222 | 0.70 | -53.48% | 1.3x | 0.0% | 613 |
| QQQ 買入並持有 | 16.66% | US$21,756 | 0.71 | -53.40% | 0.1x | 0.0% | 2 |
| SPY 買入並持有 | 11.25% | US$8,418 | 0.54 | -55.19% | 0.1x | 100.0% | 2 |
| SHY 買入並持有 | 1.94% | US$1,468 | -0.32 | -5.71% | 0.1x | 100.0% | 2 |

候選與 matched 路徑使用相同 N、股票比例、D+1 開市、10-session 收市時鐘及比例成本。
正常替換完整計入 QQQ 沽出、股票買入、股票沽出及 QQQ 買回；固定費按真實子委託數收取，
不可為候選省略或向基準加入 ghost order。

## 八假說共同統計 family

| 候選相對基準 | 年率化算術差 | NW t | Holm p | 共同 max-t p | 全專案 p | 前半／後半日均 |
|---|---:|---:|---:|---:|---:|---:|
| 相同比例原 Top-N／QQQ 部分替換 | -0.05% | -0.31 | 1.0000 | 0.9994 | 1.0000 | +0.00／-0.04 bp |
| 相同比例合資格池／QQQ 部分替換 | +0.03% | 0.22 | 1.0000 | 0.9999 | 1.0000 | +0.00／+0.02 bp |
| 相同比例完整現時股池／QQQ 部分替換 | +0.01% | 0.07 | 1.0000 | 1.0000 | 1.0000 | +0.02／-0.01 bp |
| 原 Top-7 十日／QQQ 全替換 | +1.38% | 1.31 | 1.0000 | 0.6268 | 1.0000 | +0.57／+0.53 bp |
| 相同比例 QQQ 換手 placebo | +0.06% | 0.41 | 1.0000 | 0.9970 | 1.0000 | +0.00／+0.05 bp |
| QQQ 買入並持有 | -0.06% | -0.41 | 1.0000 | 0.9970 | 1.0000 | -0.04／-0.01 bp |
| SPY 買入並持有 | +5.25% | 3.06 | 0.0153 | 0.0134 | 1.0000 | +1.98／+2.19 bp |
| SHY 買入並持有 | +15.89% | 3.59 | 0.0026 | 0.0024 | 1.0000 | +4.88／+7.73 bp |

八項比較共用 Newey–West lag 10、63-session circular blocks、20,000 條共同 bootstrap 路徑、
seed 39,202,608。全專案搜尋帳由 6,229 增至 6,237，沒有因結果重設。

## 比例成本、固定費及反集中壓力

- 移除相對 QQQ 最佳三年 2021、2016、2025 後，日均差 -0.10 bp，NW t -1.62。
- 移除最有利 46 宗事件後：qqq_buy_hold -0.33%、matched_topn_10d_overlay -0.74%、original_top7_10d_overlay +1.26%、matched_eligible_10d_overlay -0.26%、matched_complete_10d_overlay -0.25%。
- 比例成本壓力 25：候選 CAGR 16.35%。
- 比例成本壓力 50：候選 CAGR 15.96%。
- 每子委託固定費 0.01：候選 CAGR 16.57%。
- 每子委託固定費 0.05：候選 CAGR 16.51%。
- 訊號日已知 QQQ 組 `nonnegative`：677 宗，平均事件增量 -0.02 bp；只作診斷，不作市況開關。
- 訊號日已知 QQQ 組 `negative`：228 宗，平均事件增量 -2.30 bp；只作診斷，不作市況開關。

比例成本與每子委託固定費是不同壓力，不得混算。US$0.01／US$0.05 只是 US$1,000 操作
診斷，不代表任何券商實際收費；模型亦未完整計入買賣差價、市場衝擊或稅項。

## 固定危機年份

| 年份 | 候選回報／最大跌幅 | QQQ 回報／最大跌幅 | 回報差 |
|---|---:|---:|---:|
| 2008 | -41.80%／-49.46% | -41.73%／-49.40% | -0.07% |
| 2020 | +47.06%／-28.56% | +48.41%／-28.56% | -1.34% |
| 2022 | -32.81%／-35.01% | -32.58%／-34.83% | -0.23% |

## 二十二項事前反證門檻

- 固定輸入精確，但 protocol 的交易日起訖與 5,028 列敘述內部不一致：**未通過**
- 第 29／30 輪 905 事件、排名及五槽逐列重播：**通過**
- 五槽各 181 事件、十日持有、無同槽重疊且 concurrency 不高於五：**通過**
- OHLC 結構公式逐列精確且只用訊號日或以前：**通過**
- N、Top-7 子集、N/7、QQQ 餘額及非空事件下限：**未通過**
- 九路每日 driver、資產、成本、曝險、現金及槓桿 identity：**通過**
- QQQ switch placebo 與十日父事件 identity 精確：**通過**
- 候選 CAGR 高於 QQQ：**未通過**
- 候選 US$1,000 期末值高於 QQQ：**未通過**
- 候選 SHY-excess Sharpe 高於 QQQ：**未通過**
- 候選最大跌幅不比 QQQ 深超過 5pp：**通過**
- 候選 CAGR 高於 matched Top-N：**未通過**
- 候選 CAGR 高於原 Top-7 十日：**通過**
- 候選 CAGR 高於 matched eligible 及 complete：**通過**
- 候選對 QQQ 日差、NW、Holm 及共同 max-t：**未通過**
- 候選對四條公平股票基準日差、NW、Holm 及 max-t：**未通過**
- QQQ 與四條公平股票基準前後半日差全正：**未通過**
- 移除相對 QQQ 最佳三年後日差及 NW：**未通過**
- 2008／2020／2022 回報及跌幅不遜於 QQQ：**未通過**
- QQQ 20 日動量正負兩組事件增量均正：**未通過**
- 候選對 QQQ 的 6,237 次 Bonferroni p 不高於 0.05：**未通過**
- 25／50bps、US$0.01 子委託費及移除 46 宗後仍勝五基準：**未通過**

任何一項未通過即 `not_rejected_by_round39=false`。即使 22/22，本輪仍是同一已見 survivor
樣本，不得建立 Paper 或實金策略。

## 76 道固定控制

- 01 · `protocol_hash`：通過
- 02 · `protocol_commit`：通過
- 03 · `parent_main_commit`：通過
- 04 · `round38_receipt`：通過
- 05 · `round30_receipt`：通過
- 06 · `round29_receipt`：通過
- 07 · `event_receipt`：通過
- 08 · `snapshot`：通過
- 09 · `panel`：通過
- 10 · `watchlist`：通過
- 11 · `reference_commits`：通過
- 12 · `protocol_calendar_internal_consistency`：未通過
- 13 · `events_905`：通過
- 14 · `initial_capital_1000`：通過
- 15 · `cohort_25`：通過
- 16 · `signal_boundaries`：通過
- 17 · `eligible_replay`：通過
- 18 · `top7_replay`：通過
- 19 · `parent_rank_order`：通過
- 20 · `parent_assignment`：通過
- 21 · `adjusted_ohlc_finite`：通過
- 22 · `tr14`：通過
- 23 · `atr14_formula`：通過
- 24 · `feature_boolean_identities`：通過
- 25 · `high20_close`：通過
- 26 · `high60_close`：通過
- 27 · `low10_low`：通過
- 28 · `pullback_bounds`：通過
- 29 · `rebound_rule`：通過
- 30 · `target_rule`：通過
- 31 · `stop_rule`：通過
- 32 · `reward_risk_floor`：通過
- 33 · `reward_risk_clip`：通過
- 34 · `no_lookahead`：通過
- 35 · `top7_subset`：通過
- 36 · `candidate_n_range`：通過
- 37 · `n_over_7`：通過
- 38 · `qqq_remainder`：通過
- 39 · `no_reconcentration`：通過
- 40 · `d_plus_1`：通過
- 41 · `ten_session_hold`：通過
- 42 · `five_slots`：通過
- 43 · `concurrency_cap`：通過
- 44 · `qqq_base`：通過
- 45 · `four_leg_cost`：通過
- 46 · `primary_10bps`：通過
- 47 · `stress_25_50bps`：通過
- 48 · `fixed_fee_stresses`：通過
- 49 · `fixed_fee_actual_orders`：通過
- 50 · `independent_order_counts`：通過
- 51 · `n_zero_no_tagged_orders`：通過
- 52 · `nine_paths`：通過
- 53 · `placebo_identity`：通過
- 54 · `ten_day_parent_identity`：通過
- 55 · `shy_excess`：通過
- 56 · `full_long_before_terminal_all_paths`：通過
- 57 · `zero_cash_before_terminal_all_paths`：通過
- 58 · `driver_fraction_identity_all_paths`：通過
- 59 · `terminal_liquidation_all_paths`：通過
- 60 · `no_leverage`：通過
- 61 · `daily_driver_identity`：通過
- 62 · `actual_notional_cost_identity`：通過
- 63 · `eight_hypotheses`：通過
- 64 · `nw_lag10`：通過
- 65 · `bootstrap_63_20000`：通過
- 66 · `fixed_halves`：通過
- 67 · `crisis_years`：通過
- 68 · `qqq_known_at_regimes`：通過
- 69 · `best_three_years`：通過
- 70 · `favorable_46`：通過
- 71 · `global_6237`：通過
- 72 · `current_identifiers`：通過
- 73 · `formal_readiness`：通過
- 74 · `point_in_time_readiness`：通過
- 75 · `paper_zero`：通過
- 76 · `real_money_zero`：通過

控制全部通過只證明程式遵守已推送協議，不證明未來盈利。

## 72 項單欄變異攻擊

| 攻擊 | 單欄變異 | 預期錯誤碼 | 結果 |
|---|---|---|---|
| 01 | protocol_sha256 | `lpr_protocol_hash_mismatch` | 拒收 |
| 02 | protocol_commit | `lpr_protocol_commit_mismatch` | 拒收 |
| 03 | parent_main_commit | `lpr_parent_commit_mismatch` | 拒收 |
| 04 | round38_receipt_sha256 | `lpr_round38_receipt_mismatch` | 拒收 |
| 05 | round30_receipt_sha256 | `lpr_round30_receipt_mismatch` | 拒收 |
| 06 | round29_receipt_sha256 | `lpr_round29_receipt_mismatch` | 拒收 |
| 07 | event_receipt_sha256 | `lpr_event_receipt_mismatch` | 拒收 |
| 08 | snapshot_sha256 | `lpr_snapshot_mismatch` | 拒收 |
| 09 | panel_sha256 | `lpr_panel_mismatch` | 拒收 |
| 10 | watchlist_sha256 | `lpr_watchlist_mismatch` | 拒收 |
| 11 | reference_commits | `lpr_reference_mismatch` | 拒收 |
| 12 | expected_events | `lpr_event_count_mismatch` | 拒收 |
| 13 | expected_cohort | `lpr_cohort_mismatch` | 拒收 |
| 14 | expected_calendar_sessions | `lpr_calendar_mismatch` | 拒收 |
| 15 | parent_momentum_sessions | `lpr_parent_momentum_mismatch` | 拒收 |
| 16 | parent_trend_sessions | `lpr_parent_trend_mismatch` | 拒收 |
| 17 | parent_top_k | `lpr_parent_top_k_mismatch` | 拒收 |
| 18 | minimum_price_usd | `lpr_price_floor_mismatch` | 拒收 |
| 19 | dollar_volume_sessions | `lpr_liquidity_window_mismatch` | 拒收 |
| 20 | minimum_median_dollar_volume_usd | `lpr_liquidity_floor_mismatch` | 拒收 |
| 21 | atr_sessions | `lpr_atr_window_mismatch` | 拒收 |
| 22 | high20_sessions | `lpr_high20_window_mismatch` | 拒收 |
| 23 | high60_sessions | `lpr_high60_window_mismatch` | 拒收 |
| 24 | low10_sessions | `lpr_low10_window_mismatch` | 拒收 |
| 25 | pullback_minimum | `lpr_pullback_minimum_mismatch` | 拒收 |
| 26 | pullback_maximum | `lpr_pullback_maximum_mismatch` | 拒收 |
| 27 | rebound_low_multiplier | `lpr_rebound_mismatch` | 拒收 |
| 28 | target_atr_multiplier | `lpr_target_mismatch` | 拒收 |
| 29 | stop_atr_multiplier | `lpr_stop_mismatch` | 拒收 |
| 30 | upside_atr_floor | `lpr_upside_floor_mismatch` | 拒收 |
| 31 | downside_atr_floor | `lpr_downside_floor_mismatch` | 拒收 |
| 32 | reward_risk_minimum | `lpr_reward_risk_minimum_mismatch` | 拒收 |
| 33 | reward_risk_clip_maximum | `lpr_reward_risk_clip_mismatch` | 拒收 |
| 34 | stock_subslots | `lpr_subslots_mismatch` | 拒收 |
| 35 | allocation_rule | `lpr_allocation_mismatch` | 拒收 |
| 36 | entry_delay | `lpr_entry_clock_mismatch` | 拒收 |
| 37 | holding_sessions | `lpr_holding_clock_mismatch` | 拒收 |
| 38 | slot_count | `lpr_slot_count_mismatch` | 拒收 |
| 39 | events_per_slot | `lpr_events_per_slot_mismatch` | 拒收 |
| 40 | initial_capital_usd | `lpr_initial_capital_mismatch` | 拒收 |
| 41 | parent_assignment_sha256 | `lpr_parent_assignment_mismatch` | 拒收 |
| 42 | inactive_asset | `lpr_inactive_asset_mismatch` | 拒收 |
| 43 | primary_one_way_leg_bps | `lpr_primary_cost_mismatch` | 拒收 |
| 44 | cost_stress_one_way_leg_bps | `lpr_cost_stress_mismatch` | 拒收 |
| 45 | fixed_child_order_fee_stress_usd | `lpr_fixed_fee_mismatch` | 拒收 |
| 46 | four_legs_per_switched_subslot | `lpr_four_leg_mismatch` | 拒收 |
| 47 | path_ids | `lpr_path_family_mismatch` | 拒收 |
| 48 | family_baseline_ids | `lpr_hypothesis_family_mismatch` | 拒收 |
| 49 | shy_excess_proxy | `lpr_shy_proxy_mismatch` | 拒收 |
| 50 | hac_lag | `lpr_hac_mismatch` | 拒收 |
| 51 | family_alpha | `lpr_family_alpha_mismatch` | 拒收 |
| 52 | bootstrap_block_sessions | `lpr_bootstrap_block_mismatch` | 拒收 |
| 53 | bootstrap_paths | `lpr_bootstrap_paths_mismatch` | 拒收 |
| 54 | bootstrap_seed | `lpr_bootstrap_seed_mismatch` | 拒收 |
| 55 | common_bootstrap_indices | `lpr_bootstrap_indices_mismatch` | 拒收 |
| 56 | centered_under_null | `lpr_bootstrap_centering_mismatch` | 拒收 |
| 57 | global_search_trials | `lpr_global_trials_mismatch` | 拒收 |
| 58 | first_half_end | `lpr_first_half_mismatch` | 拒收 |
| 59 | second_half_start | `lpr_second_half_mismatch` | 拒收 |
| 60 | crisis_years | `lpr_crisis_mismatch` | 拒收 |
| 61 | best_year_removal_count | `lpr_best_year_mismatch` | 拒收 |
| 62 | favorable_event_removal_count | `lpr_tail_mismatch` | 拒收 |
| 63 | formal_readiness | `lpr_formal_readiness_mismatch` | 拒收 |
| 64 | point_in_time_readiness | `lpr_pit_readiness_mismatch` | 拒收 |
| 65 | qualified_provider_packages | `lpr_provider_boundary_mismatch` | 拒收 |
| 66 | formal_strategy_runs | `lpr_formal_run_boundary_mismatch` | 拒收 |
| 67 | current_identifiers_only | `lpr_identifier_scope_mismatch` | 拒收 |
| 68 | paper_authorized | `lpr_paper_boundary_breached` | 拒收 |
| 69 | real_money_authorized | `lpr_real_money_boundary_breached` | 拒收 |
| 70 | parent_top7_order | `lpr_parent_event_identity_mismatch` | 拒收 |
| 71 | ohlc_index_drop | `lpr_ohlc_index_mismatch` | 拒收 |
| 72 | ohlc_geometry | `lpr_ohlc_geometry_mismatch` | 拒收 |

任何 OHLC、ATR、pullback、reward/risk、N/7、持有期、成本、固定費、family、統計、Paper
或實金權限漂移都須命中穩定錯誤碼並 fail closed。

## 市場與數據邊界

資料最後日期不是即市行情。股票仍是 2026 現時 survivor cohort，欠缺逐期成分、永久證券
ID、可靠退市／退出經濟、歷史公司行動及公告時間。調整 OHLC、分數股與 US$1,000 只供
比例研究，不能冒充真實券商成交或稅後結果。

正式就緒仍為 **1/18**，point-in-time
**1/20**，合資格 provider package 0，正式策略
run 0。下一個可升格步驟仍是獲授權逐期成分、永久 ID、公司行動及退市資料，原樣執行既有
正式預先登記；不得用本輪結果重選參數。

## 可重播檔案

- [第 39 輪事前協議](SHORT_TERM_LEADER_PULLBACK_REBOUND_PROTOCOL.md)
- `artifacts/short_term_leader_pullback_rebound_validation.json`
- `site/data/short-term-leader-pullback-rebound.json`
