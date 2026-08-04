# 美股短線第 23 輪：時間聚類與極端贏家脆弱度事前協議 v1.0

凍結日期：2026-08-04（首次計算本輪年度、區塊及尾部結果之前）

狀態：只可否決，不可升格；不建立 Paper；實金動作 US$0

## 研究問題

第 22 輪只量化缺失退出污染，未回答現有 905 個 20 日 Top-7 事件的正平均配對差，
是否其實由少數極端正回報事件或少數年份撐起。事件每週出現、持有期 20 個交易日，
相鄰觀察重疊；只看普通平均及 Newey–West lag 4 仍可能低估較長市場階段的相關性。

本輪不得改訊號、Top-K、持有期、成本、股池、出入時鐘或 baseline，只對已凍結配對差
做時間聚類與尾部影響反證。即使全部門檻通過，也不能修復存活者偏差、不能增加正式
就緒分數，亦不能啟動 Paper 或實金交易。

## 凍結輸入及配對量

- 唯一輸入：`artifacts/short_term_high_return_validation.json`
- 輸入 SHA-256：`fa2463cc8273a316e4a98428767b695eb85c74e9ac75c47b5ca34592102979e8`
- 固定路徑：`taiwan_reference_signal_layer_diagnostic.horizons["20"].event_series`
- 固定事件數：905；實際日期由 SHA 綁定列讀取，為 2006-08-04 至 2026-07-02。
- 每列只讀取 `signal_date`、`eligible_count`、`top7_return`、
  `eligible_equal_return`。
- 固定配對差 `D_i = top7_return_i - eligible_equal_return_i`。
- 兩邊已使用同一下一開市進場／固定 20 日退出時鐘，並各扣來回 20 bps；不得重複扣費。
- 事件日期必須嚴格遞增、不得重排或補列；回報必須有限，`eligible_count >= 7`。

5 日、10 日、QQQ、SPY 及完整組合結果只保留於原報告。本輪不能用它們替換固定 20 日
配對量，也不能把事件平均當成可複利 CAGR。

## 固定時間依賴診斷

### HAC lag 前沿

原始配對差須完整輸出 Newey–West `max_lag = 4, 13, 26, 52` 的平均值、標準誤及 t 值。
lag 4 是原研究口徑；13、26、52 只測較長季度、半年及年度依賴。不得按結果選最好 lag。

### 曆年聚類

以 `signal_date` 的曆年作 21 個固定 cluster（2006 至 2026）。對截距模型使用有限樣本
修正的 cluster-robust 標準誤：

```text
u_i = D_i - mean(D)
S_g = sum_{i in year g}(u_i)
Var(mean) = [G/(G-1)] * [N/(N-1)] * sum_g(S_g^2) / N^2
```

固定 `G = 21`，雙尾 5% 臨界值使用 `t(20) = 2.085963`，不可改用常態 1.96。
輸出每年事件數、平均差、中位差、正配對比例及對總配對差和的貢獻。

另固定五個市場時段，完整呈現而不合併：

1. 2006-08-04 至 2009-12-31；
2. 2010-01-01 至 2013-12-31；
3. 2014-01-01 至 2017-12-31；
4. 2018-01-01 至 2021-12-31；
5. 2022-01-01 至 2026-07-02。

### 年度刪除影響

- 逐一刪除 21 個曆年，輸出剩餘事件的平均差及 NW lag 4 t 值。
- 「最佳年份」事前定義為該年 `sum(D_i)` 最大，而不是平均最大。
- 固定刪除最佳 1 年及最佳 3 年，重新計算平均差、NW lag 4 t 值及前後固定半期平均。
- 年份只可按未刪除原始 `sum(D_i)` 排序一次；不得在每次刪除後重新揀選。

這是集中度壓力，不是估計「真實應刪年份」；負結果不得用其他年份組合救援。

## 固定尾部影響診斷

### 對稱 winsorize

固定以全 905 列配對差的線性分位數，分別在 1%／99% 及 5%／95% 對稱截尾。每個版本
輸出平均、中位、正配對比例及 NW lag 4／13／26／52 t 值。不得改成單尾、trimmed mean、
Huber 或按結果另選百分位。

### 刪除極端正事件

固定按 `(D_i, signal_date)` 由大至小排序，日期只作 deterministic tie-break：

- 刪除最大的 `ceil(1% × 905) = 10` 列；
- 刪除最大的 `ceil(5% × 905) = 46` 列。

兩個版本均輸出平均差、NW lag 4 t 值、曆年 cluster t 值及五時段平均。這是「少數贏家
是否足以支配結論」的反證，不是建議把真實正回報排除在正式策略外。

另輸出最大 1%／5% 事件對全部正配對差總和及淨配對差總和的貢獻比例；分母為零時
必須 fail closed，不得填 0。

### 配對方向

輸出正、負、零配對數及精確雙尾 binomial sign-test p 值；零值剔除於 sign test，
但保留於其他統計。sign test 只作分布診斷，不單獨作主要通過門檻。

## 固定 circular moving-block bootstrap

- 固定 block 長度：52 個相鄰事件；不得按自相關結果選 block。
- 固定路徑：5,000；固定 seed：`20260804`。
- 每條路徑從 `0..904` 均勻抽取 circular block 起點，依原順序連取 52 列，循環越界後
  從第 0 列續取，直至至少 905 列，再截成 905 列。
- 每條路徑的 block 起點數固定 `ceil(905/52) = 18`。
- 輸出路徑平均差的 2.5%、50%、97.5% 分位數、正平均比例，以及五個原時段樣本數。

bootstrap 只量化原 survivor cohort 內的時間抽樣不確定性；不得稱為 point-in-time 或
退市修正後的信賴區間。

## 八項固定反證門檻

本輪只在以下八項同時通過時，標示「未被本輪時間／尾部反證推翻」：

1. 曆年 cluster t 不低於 `2.085963`；
2. 52-event block bootstrap 平均差 2.5% 分位數大於 0；
3. 21 個曆年中至少 14 年平均配對差大於 0；
4. 五個固定市場時段的平均配對差全部大於 0；
5. 刪除最佳 1 年後，平均差大於 0 且 NW lag 4 t 不低於 1.96；
6. 刪除最佳 3 年後，平均差大於 0 且 NW lag 4 t 不低於 1.96；
7. 1%／99% winsorized 平均差大於 0 且 NW lag 4 t 不低於 1.96；
8. 5%／95% winsorized 平均差大於 0 且 NW lag 4 t 不低於 1.96。

任一失敗即保留負結果，不可改 cluster、時段、block、seed、lag、百分位、刪除規則或
臨界值救援。八項全過亦只代表這個 survivor cohort 的正平均不集中於已測時間／尾部，
不代表可投資、正式數據合格或能勝過 QQQ。

## 十五道控制及十五項突變攻擊

正式輸出必須通過：輸入 SHA、固定 JSON 路徑、20 日期限、905 事件、嚴格日期、固定配對
baseline、成本不重扣、四個 HAC lag、21 個曆年 cluster、五時段、年度刪除規則、兩個
winsor grid、兩個極端刪除數、52／5,000／seed bootstrap，以及決策邊界共 15 道控制。

另固定證明以下 15 個錯誤會被拒收：

1. `robustness_input_hash_mismatch`
2. `robustness_path_not_frozen`
3. `robustness_horizon_not_frozen`
4. `robustness_event_count_mismatch`
5. `robustness_event_order_invalid`
6. `robustness_baseline_not_paired`
7. `robustness_cost_double_counted`
8. `robustness_hac_lags_not_frozen`
9. `robustness_calendar_clusters_not_frozen`
10. `robustness_epochs_not_frozen`
11. `robustness_year_removal_not_frozen`
12. `robustness_winsor_grid_not_frozen`
13. `robustness_tail_removal_not_frozen`
14. `robustness_bootstrap_not_frozen`
15. `robustness_decision_boundary_breached`

所有攻擊須 15/15 拒收；控制通過只證明程式依本協議運行，不代表策略合格。

## 狀態邊界

- 正式 point-in-time／退市逐股回測次數維持 0。
- 真實正式就緒維持 1/18；provider package 0；完整 RF package 0。
- 本輪不得輸出股票名單、持倉、Paper 成交、參考配置或實金指令。
- 正式 50 bps 成本、QQQ／SPY／逐期股池 baseline、NW、DSR、PBO 及新增 252 個交易日／
  12 次月度輪選的前瞻門檻全部不變。
- US$1,000 只作讀者本金比例示例；短線配置、Paper 持倉及實金動作固定 US$0。

歷史及合成結果不保證未來回報。本協議不構成投資建議或落盤授權。
