# 美股短線第 24 輪：公平基準歸因與多重檢驗事前協議 v1.0

凍結日期：2026-08-04（首次計算本輪調整後 p 值及共同 bootstrap 之前）

狀態：只可否決，不可升格；不建立 Paper；實金動作 US$0

## 研究問題

第 23 輪顯示 20 日 Top-7 訊號在現時 survivor cohort 內具有正平均，但最佳三年移除後
八項反證只過 7/8。原始第 2 輪已公開 5／10／20 日及三個 baseline 的普通平均與
Newey–West 結果，但沒有把九個配對假說放入同一 family-wise 檢驗；網站亦容易只突出
最有利的「Top-7 對合資格池等權」。

本輪不得修改選股、Top-K、持有期、股池、成本、出入時鐘或 baseline。只問：20 日正面
線索能否同時勝過合資格池、完整現時股池及 QQQ，並在九假說 family、共同時間區塊及
全專案 6,208 次搜尋壓力後仍成立？

輸入內的普通結果早已可見；「首次未見」只指本輪 Holm、max-t、Reality Check、
Romano–Wolf 及全專案調整。即使所有門檻通過，也不能修復存活者偏差或啟動 Paper。

## 凍結輸入與共同樣本

- 唯一輸入：`artifacts/short_term_high_return_validation.json`
- 輸入 SHA-256：`fa2463cc8273a316e4a98428767b695eb85c74e9ac75c47b5ca34592102979e8`
- 固定根路徑：`taiwan_reference_signal_layer_diagnostic.horizons`
- 固定持有期：5、10、20 個交易日；主要期限仍為 20 日。
- 固定 baseline：`eligible_equal_return`、`complete_cohort_equal_return`、`qqq_return`。
- 每個 baseline 與 Top-7 都已用同一下一開市進場、固定期限退出及來回 20 bps；本輪不得
  重複扣費或對任一邊另加成本。
- 三個期限只取 signal date 交集，預期 905 列，2006-08-04 至 2026-07-02；日期須嚴格
  遞增且三表逐日一對一。不得用 5／10 日額外尾端事件增加某個假說樣本。
- 固定九個配對序列：每個期限的 `top7_return - baseline_return`。
- 固定 NW lag：5 日用 1、10 日用 2、20 日用 4；年化只作事件尺度展示，不當 CAGR。

完整現時股池同樣有存活者偏差；它只是比「先通過趨勢／流動性濾網的合資格池」更廣的
公平分母，不得稱為 point-in-time 市場。

## 20 日固定基準歸因

對主要 20 日期限固定輸出：

```text
ranking_effect     = top7_return - eligible_equal_return
eligibility_effect = eligible_equal_return - complete_cohort_equal_return
combined_effect    = top7_return - complete_cohort_equal_return
combined_effect    = ranking_effect + eligibility_effect
```

逐列及平均恆等式都須在 1e-12 內成立。三個序列各輸出平均、中位、正配對比例、NW lag 4
及固定前後兩半（至 2016-07-29／由 2016-08-01）。另列 Top-7 對 QQQ 的相同統計。

## 固定普通 p 值與解析校正

- 每個九假說以其固定 NW t 計雙尾常態 p：`p = erfc(abs(t)/sqrt(2))`。
- family alpha 固定 0.05。
- 九假說 Holm step-down：依 `(p, horizon, baseline)` 排序；輸出單調調整 p。
- 九假說 Bonferroni：`min(1, p × 9)`。
- 全專案壓力固定 6,208 次：`min(1, p × 6208)`；不得因本輪只有九列而重設為 9 或 1。
- 同時輸出全專案通過所需未調整 p 界線 `0.05/6208`。

6,208 次 Bonferroni 是保守的搜尋脆弱度界線，不冒充正式策略 DSR；事件配對差不是可複利
每日超額 Sharpe。本輪不得由 Bonferroni 失敗反推任何替代參數。

## 固定共同 circular moving-block bootstrap

- 九序列按各自樣本平均去中心化，保持原日期及同日跨期限／baseline 關係。
- block 長度：52 個共同每週事件；circular 越界後由第 0 列續取。
- 路徑：20,000；每路徑 18 個 block，截成 905 列；seed `20260804`。
- 所有九序列共用完全相同的 resample indices，不得逐假說重抽。
- 每個 bootstrap 平均以原樣本固定 NW 標準誤 studentize。
- 固定輸出：
  1. 兩尾 `max(abs(t*))` single-step 調整 p；
  2. 兩尾 Romano–Wolf step-down 調整 p，按觀察 `abs(t)` 排序並強制單調；
  3. 一尾 White-style Reality Check：觀察九列最大正 t 對 bootstrap `max(t*)` 的 p；
  4. start-index SHA-256、每列未調整 bootstrap p 及共同 index 契約。

這是 survivor cohort 內的 family-wise 時間抽樣反證，不是 White 原論文所有假設的完整
交易策略 universe，也不能替代正式 point-in-time PBO／DSR。

## 九項固定反證門檻

全部九項通過才可標示「未被本輪公平基準／多重檢驗推翻」：

1. 20 日對合資格池平均為正且 NW t 不低於 1.96；
2. 20 日對完整現時股池平均為正且 NW t 不低於 1.96；
3. 20 日對 QQQ 平均為正且 NW t 不低於 1.96；
4. 20 日對三個 baseline 的固定前後兩半平均全部為正；
5. 20 日對合資格池的九假說 Holm 調整 p 不高於 0.05；
6. 20 日對合資格池的共同 max-t 調整 p 不高於 0.05；
7. 九假說 Reality Check p 不高於 0.05；
8. 20 日對合資格池的 6,208 次 Bonferroni p 不高於 0.05；
9. 5／10／20 日對合資格池的共同 max-t 調整 p 全部不高於 0.05。

任一失敗即保留負結果，不得換 baseline、期限、單尾 p、lag、block、路徑、seed、trial
count 或 alpha 救援。通過亦只代表此 survivor cohort 未被本輪推翻，不代表可投資。

## 十六道控制與十六項突變攻擊

正式輸出須通過：輸入 SHA、固定根路徑、三期限、20 日主要期、三 baseline、905 共同日、
嚴格交集順序、逐事件同成本配對、NW lag 1／2／4、九假說 family、alpha 0.05、6,208
trials、52-event block、20,000 路徑、seed／共同 circular indices／去中心化，以及決策
邊界共 16 道控制。

另固定證明以下 16 個錯誤會被拒收：

1. `multiplicity_input_hash_mismatch`
2. `multiplicity_path_not_frozen`
3. `multiplicity_horizons_not_frozen`
4. `multiplicity_primary_horizon_not_frozen`
5. `multiplicity_baselines_not_frozen`
6. `multiplicity_common_sample_mismatch`
7. `multiplicity_event_order_invalid`
8. `multiplicity_pairing_or_cost_mismatch`
9. `multiplicity_hac_lags_not_frozen`
10. `multiplicity_family_not_frozen`
11. `multiplicity_alpha_not_frozen`
12. `multiplicity_global_trials_not_frozen`
13. `multiplicity_block_length_not_frozen`
14. `multiplicity_bootstrap_paths_not_frozen`
15. `multiplicity_bootstrap_contract_not_frozen`
16. `multiplicity_decision_boundary_breached`

所有攻擊須 16/16 拒收；控制通過只證明程式遵守協議。

## 狀態邊界

- 正式 point-in-time／退市逐股回測次數維持 0；真實正式就緒維持 1/18。
- provider package 0；完整 RF package 0；Paper 全現金且未開始；實金動作 US$0。
- 本輪不得輸出股票名單、持倉、Paper 成交、參考配置或真倉指令。
- 正式 50 bps、QQQ／SPY／逐期股池、NW／PSR／DSR／PBO 及 252 個新增交易日／12 次
  月度輪選門檻全部不變。
- US$1,000 只作讀者本金示例，並非投資建議。

歷史及合成結果不保證未來回報。本協議不構成投資建議或落盤授權。
