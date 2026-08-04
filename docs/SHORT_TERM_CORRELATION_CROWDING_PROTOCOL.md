# 美股短線第 25 輪：相關性擁擠與現時代號依賴事前協議 v1.0

凍結日期：2026-08-04（首次重建逐股 Top-7、相關系數及貢獻結果之前）

狀態：只可否決，不可升格；不是新策略；不建立 Paper；實金動作 US$0

## 研究問題

第 24 輪把 5／10／20 日及三個公平 baseline 放入同一九假說 family，結果只過 6/9：
20 日排名相對合資格池仍有訊號，但相對完整現時股池及全專案搜尋壓力失敗。第 23 輪亦
顯示刪除最佳三年後 NW t 跌穿 1.96。尚未回答的是：名義上等權持有 7 隻股份，是否因
動量股高度相關、反覆選中少數 2026 年仍存在的贏家，而實際只剩很少獨立注數。

本輪不得修改 20 日動量、60 日趨勢、Top-7、每週訊號、下一開市成交、20 日持有或來回
20 bps。只重建原 905 個事件，量度事前 60 日相關性、現時代號選中／淨貢獻集中度，並
以刪除主要現時代號及固定相關性上限做壓力測試。全部通過亦不能修復存活者偏差、成為
新候選，或改寫已凍結的正式 v1／6,208-trial DSR。

## 台股參考版本與可移植邊界

固定只參考以下 `main` commit；後續更新不得靜默改變本輪定義：

- `appr1ciat1/tst_wocker`：`3372aa088328700feafeeb07c72ab832ea2d3ecb`。只抽取
  GUARD 的風險端診斷：60 日相關、`corr > 0.70`、候選與已選股份有兩個高相關連結便
  跳過，以及有效獨立注數 `N/(1+(N-1)×平均相關)`。不採用台股回報、ATR、VIX、加碼、
  止賺、止蝕或 Paper 決策。
- `appr1ciat1/tw-block-warrant`：`37463c54796ba36f4aac262519ea7fc2ef797de6`。只保留
  研究層／每日訊號層分開及 D+1 時序；不建立美股鉅額／權證替代因子。
- `appr1ciat1/tst_wocker_filter_lab`：`06c87b7a1735877c9ccbab3a339c1742814a5058`。只保留
  同次運行 baseline、資料修訂防護、負結果及失敗規則不刪除。

相關性只管理風險，不重新估計動量分數；本輪壓力路徑不是可採用策略。

## 凍結輸入與逐股重建

- 行情快照：`artifacts/snapshot_20260731_6a7ca6b8.zip`；archive SHA-256
  `d480fb82e712f06aabe0a98461e222344656b87022b8bda2cd7ccaa4c29ae88b`；panel fingerprint
  `6a7ca6b83b1570007424daa46b0ff4e8fb4a655d39298a0f4f6d74c3b7ea3a66`。
- 現時觀察名單：`usfddk/resources/us_large_cap_watchlist_v1.csv`；SHA-256
  `b6002e4e151bd298884f8cdd6272b5cbfde8aedca47cb58b92830d4d92028014`；as-of 2026-07-30。
- 既有事件收據：`artifacts/short_term_high_return_validation.json`；SHA-256
  `fa2463cc8273a316e4a98428767b695eb85c74e9ac75c47b5ca34592102979e8`。
- 完整現時 cohort 固定為既有 25 隻：2006-08-01 前已有價格，且 2006-08-01 至
  2026-07-31 收市價無缺值。這是 2026 名單倒推，不是 point-in-time 成分。
- 每個完整星期最後一個 XNYS session 收市後，以 20 日動量排名；合資格條件仍為站上
  60 日平均線、股價高於 US$5、20 日中位成交金額不少於 US$20m。
- 取首 7 名，下一 session 未調整開市價進場，在第 20 個持有 session 收市離場；每個
  組合扣來回 20 bps。共同樣本固定為 905 個訊號日，2006-08-04 至 2026-07-02。
- 重建的 Top-7、合資格池等權、完整 cohort 等權及 QQQ 四條回報，須逐列與既有 20 日
  event series 在 `1e-12` 內一致；否則在任何新統計前停止。

本輪可列出歷史研究貢獻者，但必須標示「2026 現時代號、事後歸因、不是買入名單」。
不得把 ticker 當永久證券／公司 ID，也不得合併、修補或猜測改名與收購 lineage。

## 60 日相關性與有效獨立注數

每個訊號日只用截至當日的 61 個完整收市價，計算 60 個簡單日回報及 Pearson 相關矩陣。
原 Top-7 固定輸出 21 個 pair 的平均、中位、最大相關，以及 `corr > 0.70` 的 pair 數。

有效獨立注數固定為：

```text
N_eff = clip(N / (1 + (N - 1) * mean_pairwise_corr), 1, N)
```

原組合 `N=7`；只報告每事件數值、分位數及 `N_eff < 3` 的事件比例。負相關令公式超過
名義 N 時上限為 N；分母非正、缺 60 個完整回報或非有限相關均 fail closed。

## 現時代號選中與淨貢獻歸因

- 905×7 共 6,335 個選中 slot；逐現時代號輸出次數及 slot share。
- 對每個被選股份 `i`，固定主動貢獻為
  `(個股 20 日淨回報 - 同事件合資格池等權淨回報) / 7`。所有代號貢獻總和須與 905 列
  `Top-7 - eligible_equal` 淨差總和在 `1e-12` 內一致。
- 依全期淨貢獻由高至低、再以 ticker 排序；最重要一個／三個現時代號只作事後刪除壓力，
  不能稱為未來贏家或推薦股份。
- 對 25 個現時代號逐一做 leave-one-symbol-out：該代號同時由可選池與合資格 baseline
  移除，再按原動量規則取下一名以保持 7 隻；不得只打擊候選、不改 baseline。
- 另刪除事後淨貢獻最高的一個及三個現時代號；仍須每事件至少 7 隻合資格股份，否則
  fail closed。每條壓力輸出平均／中位配對差、勝率、NW lag 4 及固定前後十年。

## 固定相關性上限壓力

這不是新策略，只問原 Top-7 的正面差是否依賴高度相關的名義持倉：

1. 只在原 Top-7 內依動量排名處理，不查看第 8 名以後股份；
2. 首名必然保留；其後候選若與已保留股份中有至少兩個 `corr > 0.70` 便剔除；
3. 不回補，剔除的每個 1/7 權重保留為零回報現金；每隻保留股份仍是原始 1/7 權重；
4. 成交成本按實際股票持倉比例扣除：`20 bps × accepted_count/7`；
5. 公平 baseline 以完全相同持倉比例投資當日已合資格池等權，其餘為現金；另列相同比例
   QQQ。不得以較低股票持倉比例的回撤改善冒充選股 alpha；
6. 輸出平均保留數／股票持倉比例、滿 7 隻事件比例、剔除數、過濾前後平均相關及 N_eff，
   以及相對 matched eligible／QQQ 的配對統計。

## 統計 family

- 固定四條 905 列序列：原 Top-7、刪除最高一個貢獻代號、刪除最高三個貢獻代號、
  相關性上限壓力；各自比較同口徑合資格 baseline。
- 每條使用 NW lag 4、雙尾常態 p、固定前後十年。
- 四假說 family 使用 Holm；另以 52-event circular moving-block、20,000 路徑、seed
  `25202608`、四列共同 indices 及各列零假設去中心化，輸出兩尾 single-step max-t。
- family 只作本輪擁擠反證；不重設或取代正式 6,208-trial DSR，不從四條中挑最好一條。

## 十二項固定反證門檻

全部通過才可標示「未被本輪相關性／現時代號擁擠反證推翻」：

1. 四條原始事件回報逐列重建誤差不高於 `1e-12`；
2. 原 Top-7 的中位 `N_eff` 不低於 3.5；
3. 原 Top-7 中 `N_eff < 3` 的事件不多於 25%；
4. 單一現時代號 slot share 不高於 10%；
5. slot share 最高三個現時代號合計不高於 25%；
6. 刪除淨貢獻最高一個代號後，平均配對差為正且 NW t 不低於 1.96；
7. 刪除淨貢獻最高三個代號後，平均配對差為正且 NW t 不低於 1.96；
8. 25 條 leave-one-symbol-out 的平均配對差全部為正，且最低 NW t 不低於 1.96；
9. 相關性上限壓力令事件平均 pairwise correlation 至少降低 0.05；
10. 相關性上限壓力的平均股票持倉比例不低於 6/7，且至少一半事件保留完整 7 隻；
11. 相關性上限壓力相對 matched eligible 平均差為正、NW t 不低於 1.96，且前後十年
    平均差同為正；
12. 刪除最高三個代號及相關性上限兩條壓力的 Holm 與共同 max-t p 均不高於 0.05。

任一失敗即完整保留，不得改 0.70、60 日、cap 2、Top-7、刪除數、現金處理、門檻或
family 救援。十二項全過也只代表現時 survivor cohort 未被這輪推翻。

## 十八道控制與十八項突變攻擊

正式輸出須通過：協議 SHA、行情 archive／panel、watchlist、事件收據、三個參考 commit、
25 隻 cohort、905 日期、Top-7／20／60、D+1／20 日／20 bps、60 日相關、0.70／cap 2／
不回補、N_eff 公式、現時代號警告、貢獻恆等式、公平刪除 baseline、四假說共同 bootstrap，
以及決策邊界共 18 道控制。

另固定證明下列錯誤會逐一 fail closed：

1. `crowding_protocol_mismatch`
2. `crowding_snapshot_hash_mismatch`
3. `crowding_panel_fingerprint_mismatch`
4. `crowding_watchlist_hash_mismatch`
5. `crowding_event_receipt_hash_mismatch`
6. `crowding_reference_commits_mismatch`
7. `crowding_cohort_mismatch`
8. `crowding_event_order_mismatch`
9. `crowding_signal_rule_mismatch`
10. `crowding_execution_rule_mismatch`
11. `crowding_correlation_window_mismatch`
12. `crowding_cap_rule_mismatch`
13. `crowding_effective_bets_formula_mismatch`
14. `crowding_identifier_claim_breached`
15. `crowding_contribution_identity_failed`
16. `crowding_baseline_fairness_breached`
17. `crowding_bootstrap_contract_mismatch`
18. `crowding_decision_boundary_breached`

控制通過只證明程式遵守協議，不代表策略盈利或數據合格。

## 狀態邊界

- 正式 point-in-time／退市逐股回測次數維持 0；真實正式就緒維持 1/18。
- provider package 0；完整 RF package 0；Paper 全現金且未開始；實金動作 US$0。
- 本輪不得輸出未來選股、持倉、Paper 成交、參考配置或真倉指令。
- 已凍結正式 v1、QQQ／SPY／逐期股池／同股漂移 baseline、50 bps、NW／PSR／
  6,208-trial DSR／PBO 及 252 個新增交易日／12 次月度輪選門檻全部不變。
- US$1,000 只作讀者本金示例，並非投資建議。

歷史及合成結果不保證未來回報。本協議不構成投資建議或落盤授權。
