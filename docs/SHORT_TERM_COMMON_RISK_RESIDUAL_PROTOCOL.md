# 短線第 26 輪共同風險殘差反證協議

狀態：**首次計算前凍結**
研究角色：只可反證第 24／25 輪的 905 個固定 20 日 Top-7 事件；不得建立新策略、
改變正式 v1、啟動 Paper 或落實實金買賣。

## 問題與停止邊界

第 25 輪顯示名義七股的中位有效獨立注數只有 2.21。第 26 輪只回答：Top-7 對公平
baseline 的正面差額，在以訊號前資料估算並扣除 QQQ、SPY 或完整現時股池共同 beta
後是否仍存在？

本輪不是搜尋較佳 beta 窗、factor、Top-K、持有期、成本或權重。任何結果均不可：

1. 稱為 point-in-time／退市修正後 alpha；
2. 把 2026 現時代號或行業標籤冒充歷史永久身份；
3. 產生最新買入名單；
4. 增加短線 Paper 持倉；
5. 把通過控制、統計或網站部署當成盈利保證。

## 固定輸入

| 輸入 | 固定值 |
|---|---|
| 第 25 輪來源 commit | `ebcbc30ad98d719dad0c098a68211fd611001914` |
| 第 25 輪機器收據 | `artifacts/short_term_correlation_crowding_validation.json` |
| 第 25 輪收據 SHA-256 | `11155736a8449e6c4f50c0de0d285df9598d76de3752733f5bd140d8a2c8d0f5` |
| 第 24 輪機器收據 | `artifacts/short_term_baseline_multiplicity_validation.json` |
| 第 24 輪收據 SHA-256 | `4dc15a520606a03c85279bfaaca88367015bb651d0b6fbd77dffc9023cdbe282` |
| 行情快照 | `artifacts/snapshot_20260731_6a7ca6b8.zip` |
| 行情 archive SHA-256 | `d480fb82e712f06aabe0a98461e222344656b87022b8bda2cd7ccaa4c29ae88b` |
| 行情 panel fingerprint | `6a7ca6b83b1570007424daa46b0ff4e8fb4a655d39298a0f4f6d74c3b7ea3a66` |
| 現時觀察名單 | `usfddk/resources/us_large_cap_watchlist_v1.csv` |
| 觀察名單 SHA-256 | `b6002e4e151bd298884f8cdd6272b5cbfde8aedca47cb58b92830d4d92028014` |
| 原始事件收據 | `artifacts/short_term_high_return_validation.json` |
| 原始事件收據 SHA-256 | `fa2463cc8273a316e4a98428767b695eb85c74e9ac75c47b5ca34592102979e8` |
| 事件 | 905 個；2006-08-04 至 2026-07-02 訊號日 |
| 現時完整 cohort | 25 隻；與第 25 輪逐字一致 |
| 訊號／成交 | 20 日動量、60 日趨勢、Top-7；D+1 調整開市，持有 20 個 session |
| 成本 | candidate、eligible、complete cohort 各自相同 20 bps round trip |

現時完整 cohort 固定為：
`AAPL, AMAT, AMD, AMZN, BAC, BRK-B, CAT, COST, CSCO, CVX, GE, GOOG, GOOGL,
INTC, JNJ, JPM, LLY, LRCX, MA, MSFT, MU, NVDA, UNH, WMT, XOM`。

台股方法參考仍固定為：

- `tst_wocker`：`3372aa088328700feafeeb07c72ab832ea2d3ecb`
- `tw-block-warrant`：`37463c54796ba36f4aac262519ea7fc2ef797de6`
- `tst_wocker_filter_lab`：`06c87b7a1735877c9ccbab3a339c1742814a5058`

## 固定 beta 與殘差定義

1. beta 只用訊號日收市已知的調整收市簡單日回報；訊號日回報可用，之後任何回報不可用。
2. 只准以下三個 factor、四個模型：
   - `QQQ_60`：QQQ，最後 60 個完整日回報；
   - `QQQ_252`：QQQ，最後 252 個完整日回報；
   - `SPY_252`：SPY，最後 252 個完整日回報；
   - `COHORT_252`：固定 25 隻現時 cohort 的每日簡單回報等權平均，最後 252 日。
3. 每隻股票的 beta 固定為
   `sum((f-fbar)*(r-rbar)) / sum((f-fbar)^2)`；不 clipping、不 winsor、不 shrink、
   不把缺值補零。factor variance 非正或窗口不完整即 fail closed。
4. factor 的未來事件回報與個股使用相同 D+1 調整開市至退出日調整收市；
   `COHORT_252` 的事件 factor 回報是固定 25 股同口徑 gross return 等權平均。
5. 每股殘差回報固定為 `stock_event_gross - beta_at_signal * factor_event_gross`。
6. candidate 是固定 Top-7 殘差等權；baseline 只准：
   - 同日全部合資格股份殘差等權；
   - 固定 25 股完整現時 cohort 殘差等權。
7. candidate 與 baseline 都是滿倉、都扣同一 20 bps；故配對差中的成本逐事件恰好抵銷。
   收據仍須保存原 net return 及殘差恆等式，不得把成本省略冒充零成本策略。
8. 每個模型都須滿足逐事件分解：
   `raw_active = residual_active + (candidate_mean_beta - baseline_mean_beta) * factor_event_gross`，
   最大絕對殘差不得高於 `1e-12`。

## 十假說共同 family

兩個 baseline × 五個模型固定成十列：

1. `RAW × eligible`
2. `RAW × complete cohort`
3. `QQQ_60 × eligible`
4. `QQQ_60 × complete cohort`
5. `QQQ_252 × eligible`
6. `QQQ_252 × complete cohort`
7. `SPY_252 × eligible`
8. `SPY_252 × complete cohort`
9. `COHORT_252 × eligible`
10. `COHORT_252 × complete cohort`

每列完整呈列平均／中位配對差、正值比例、Newey–West lag 4、普通兩尾常態 p、Holm p、
固定前後半及共同 max-t p。共同 bootstrap 固定為 52-event circular block、20,000 路徑、
seed `26202608`、十列同一組 indices、各列先在零假設下去中心化。不得逐格改 seed 或 block。

正式全專案 6,208 次搜尋壓力不重設；本輪無論結果如何均不得升格，因此不把診斷 family
冒充新候選或獨立正式 DSR。

## 只可否決的附加壓力

- **主要模型**固定為 `QQQ_252 × eligible`。
- beta gap 呈列 candidate mean beta 減 eligible／complete mean beta 的分布、絕對中位及
  95th percentile，以及 beta contribution 佔 raw active 平均的比例。
- 以未來 QQQ 事件 gross return 分成 `>= 0` 與 `< 0` 兩組，只作事後反證；不得變成交易
  regime。
- 固定移除 `abs(beta_gap * QQQ_event_gross)` 最大的 46 個事件（905 的向上取整 5%），
  再計主要殘差。不得改成較有利的 10／20／45／50 列。
- 2026 現時行業標籤只呈列每事件唯一行業數、行業 HHI、有效行業數及最大行業股數；
  只能增加存活者／身份警告，不能作通過證據或買入名單。

## 十四項事前反證門檻

所有門檻必須同時通過才可寫「第 26 輪沒有額外推翻共同風險殘差線索」；即使 14/14，
亦不得建立策略或 Paper：

1. 四條原始事件回報逐列重建最大誤差不高於 `1e-12`；
2. 905 事件的所有 selected、eligible、complete cohort beta 窗完整且 factor variance 正；
3. 所有 factor／baseline 分解最大誤差不高於 `1e-12`；
4. `QQQ_252` 對 eligible 的絕對 beta gap 中位不高於 `0.10`；
5. 同一絕對 beta gap 95th percentile 不高於 `0.25`；
6. `QQQ_252 × eligible` 平均為正、NW t 不低於 `1.96`、前後半均正；
7. `QQQ_252 × complete` 同上；
8. `SPY_252 × eligible` 同上；
9. `SPY_252 × complete` 同上；
10. `COHORT_252 × eligible` 同上；
11. `COHORT_252 × complete` 同上；
12. 上述六個 252 日殘差列的十假說 Holm p 及共同 max-t p 均不高於 `0.05`；
13. 未來 QQQ 上升／下跌兩組的主要殘差均為正且 NW t 不低於 `1.96`；
14. 移除最大 46 個絕對 beta contribution 事件後，主要殘差仍為正且 NW t 不低於 `1.96`。

## Fail-closed 控制與變異攻擊

實作至少須逐項驗證以下 20 道控制，並以每次只改一欄的 20 項攻擊命中穩定 error code：

1. 協議 SHA；
2. 第 25 輪來源 commit／收據 SHA；
3. 第 24 輪收據 SHA；
4. 行情 archive SHA；
5. panel fingerprint；
6. watchlist SHA；
7. 原始事件收據 SHA；
8. 三個台股參考 commit；
9. 25 股 cohort 逐字一致；
10. 905 事件及日期次序；
11. 20／60／Top-7 訊號；
12. D+1／20 session／20 bps；
13. QQQ／SPY／cohort factor identity；
14. 60／252 beta window；
15. OLS beta 公式及禁止 clipping／winsor／shrink；
16. eligible／complete 兩個 baseline；
17. 十假說 family、Holm 及 NW lag 4；
18. 52-event／20,000／seed 26202608 共同 bootstrap；
19. 46-event 壓力及現時行業標籤不可升格；
20. `paper_authorized=false`、`real_money_authorized=false`、正式策略 run 0。

任何輸入、窗口、factor、baseline、family、seed、壓力列數或決策邊界不符，必須在輸出
結果前 fail closed。輸出若產生，必須保存 14 個 gate、20 個 control、20 個 attack、
全部十列、beta 分解、regime、tail stress、行業警告及機器可重播收據。

## 升格邊界

本輪最高只可保留一條 survivor-contaminated 的共同風險殘差研究線索。正式就緒維持
`1/18`、point-in-time 維持 `1/20`、合格 provider package `0`、正式策略 run `0`、
Paper 全現金、持倉 `0`、實金動作 `US$0`。只有合法授權的 point-in-time 成分、永久
證券 ID、歷史行業、公司行動、退市／退出經濟、同步 QQQ／SPY 及精確 RF 全部通過既有
閘門，才可原樣運行一次正式 20 年回測；通過後仍須由下一個新增交易日全現金開始 Paper。
