# 短線第 28 輪短期反轉與波幅歸因協議

狀態：**首次計算前凍結**
研究角色：只可解釋第 27 輪同一 905 個事件的底段反彈及局部高段優勢；不得調校新策略、
改變正式 v1、啟動短線 Paper 或落實實金買賣。

## 問題與停止邊界

第 27 輪顯示高動量段相對中段有局部正差，但中段對低段為負，完整排序不是單調階梯。
第 28 輪只回答兩個問題：

1. 低動量段反彈是否可由訊號日前 5 日短期反轉與 20 日已實現波幅解釋？
2. 用相同控制殘差化後，高段相對中段是否仍能通過合資格池、完整現時股池、共同多重校正、
   訊號日已知的 QQQ 市況及尾部壓力？

本輪不是搜尋 2／10 日反轉窗、10／60 日波幅、其他控制、winsor、bucket 數、Top-K、持有期、
成本、regime 門檻、bootstrap 或樣本起點。任何結果均不可：

1. 稱為 point-in-time／退市修正後 alpha；
2. 把 2026 現時代號冒充歷史永久身份；
3. 把歸因殘差變成可落盤 long-short 策略；
4. 產生最新買入名單；
5. 增加短線 Paper 持倉或實金動作；
6. 把通過控制、網站部署或殘差統計當成盈利保證。

若任何事件不能為完整 25 股計算訊號日前特徵、未來回報或第 27 輪固定 bucket，必須以
`reversal_volatility_coverage_mismatch` 在結果前停止；不得刪除事件、股票或控制。

## 固定輸入

| 輸入 | 固定值 |
|---|---|
| 第 27 輪來源 commit | `799120497084f59666e22cfcbd709cd8657f3223` |
| 第 27 輪機器收據 | `artifacts/short_term_rank_monotonicity_placebo_validation.json` |
| 第 27 輪收據 SHA-256 | `3d362ed82ab8ed732d53344a1a8d787fe48374e042bdf8f13c54a0f0cea96448` |
| 第 26 輪收據 SHA-256 | `14727306343fbcf45eb82045363898e07bb6ff0487f0b3d580dec0a9f129637b` |
| 第 25 輪收據 SHA-256 | `11155736a8449e6c4f50c0de0d285df9598d76de3752733f5bd140d8a2c8d0f5` |
| 第 24 輪收據 SHA-256 | `4dc15a520606a03c85279bfaaca88367015bb651d0b6fbd77dffc9023cdbe282` |
| 原始事件收據 SHA-256 | `fa2463cc8273a316e4a98428767b695eb85c74e9ac75c47b5ca34592102979e8` |
| 行情 archive SHA-256 | `d480fb82e712f06aabe0a98461e222344656b87022b8bda2cd7ccaa4c29ae88b` |
| 行情 panel fingerprint | `6a7ca6b83b1570007424daa46b0ff4e8fb4a655d39298a0f4f6d74c3b7ea3a66` |
| 現時觀察名單 SHA-256 | `b6002e4e151bd298884f8cdd6272b5cbfde8aedca47cb58b92830d4d92028014` |
| 事件 | 905 個；2006-08-04 至 2026-07-02 訊號日 |
| 第 27 輪 bucket receipt SHA-256 | `0f1512ccc893f554028b77de85af146e53333e1badd528fb00089878d49e8ffd` |
| 訊號／成交 | 訊號日收市已知特徵；D+1 調整開市至第 20 個持有 session 調整收市 |
| 成本 | 每個全額投資 sleeve 各扣相同 20 bps；spread 內成本抵銷 |

現時完整 cohort 與第 27 輪逐字一致：
`AAPL, AMAT, AMD, AMZN, BAC, BRK-B, CAT, COST, CSCO, CVX, GE, GOOG, GOOGL,
INTC, JNJ, JPM, LLY, LRCX, MA, MSFT, MU, NVDA, UNH, WMT, XOM`。

台股方法參考固定為：

- `tst_wocker`：`3372aa088328700feafeeb07c72ab832ea2d3ecb`
- `tw-block-warrant`：`37463c54796ba36f4aac262519ea7fc2ef797de6`
- `tst_wocker_filter_lab`：`06c87b7a1735877c9ccbab3a339c1742814a5058`

## 訊號日前控制特徵

每個事件、每個 universe 分開計算，所有價格均為凍結面板的調整收市：

1. `prior_5d_return = close[t] / close[t-5] - 1`。
2. `realized_volatility_20d` 為截至訊號日、最近 20 個一日簡單回報的樣本標準差
   （`ddof=1`），即需要 `t-20` 至 `t` 的 21 個收市價。
3. 每項特徵在該事件及 universe 內以平均 rank 計算，再固定轉為
   `(rank - 1) / (n - 1) - 0.5`；範圍為 `[-0.5, +0.5]`。完全相同值使用平均 rank，
   不以 ticker 人工製造控制差異。
4. 非有限、零變異或缺少任一股票即 fail closed；不得補值、截尾或改窗。

## 固定橫截面殘差化與精確歸因

每事件、每 universe 對同時鐘股票未來 **gross** return 做一次橫截面 OLS：

`future_gross = intercept + beta_5d * rank_5d + beta_vol * rank_vol20 + residual`

固定使用 NumPy `lstsq(rcond=None)`；設計矩陣必須 rank 3，2-norm condition number 不高於
`1e8`。不得加入動量本身、行業、beta、市值、winsor 或權重。

第 27 輪 `top／middle／bottom` 股票逐字重播，不重新分組。每事件保存：

- 三段 gross／net、control-predicted 及 residual 平均；
- raw、predicted 及 residual 的 `top-middle` 與 `bottom-middle`；
- `raw spread = predicted spread + residual spread` 的最大誤差；
- bottom 相對 middle 的 5 日回報 rank gap、20 日波幅 rank gap與兩項預測貢獻；
- OLS beta、rank、condition number 及 residual 全 universe 平均。

raw spread 必須逐列對齊第 27 輪；歸因 identity 最大誤差不高於 `1e-12`。殘差只作同樣本
解釋，不是可直接交易的收益。

## 八假說共同 family

固定八列，不得刪除不利列：

1. `eligible_raw_top_middle`
2. `eligible_raw_bottom_middle`
3. `complete_raw_top_middle`
4. `complete_raw_bottom_middle`
5. `eligible_residual_top_middle`
6. `eligible_residual_bottom_middle`
7. `complete_residual_top_middle`
8. `complete_residual_bottom_middle`

每列呈列 905 個事件的平均／中位、正值比例、Newey–West lag 4、普通兩尾常態 p、固定前後半、
Holm p 及共同 single-step max-t p。共同 bootstrap 固定 52-event circular blocks、20,000
路徑、seed `28202610`、八列共用 indices 並在零假設下去中心化。

正式全專案 6,208 次搜尋壓力不重設；本輪使用已見的同一 905 個事件，不是獨立未見確認，
不能把 family 縮成單列後另算新的 DSR。

## 只可否決的附加壓力

- **訊號日已知 QQQ 市況**：以 QQQ 訊號日 20 日回報固定分成 `>=0` 與 `<0`；對兩個
  universe 的 residual top-middle 計平均及 NW t。這是已見樣本診斷，即使通過亦不可直接
  建立 regime 策略。
- **尾部**：各 universe 依 raw bottom-middle 絕對值由大至小移除 46 個事件；在餘下 859
  個事件重算 residual top-middle。不得依 residual 結果改移除列。
- **時段**：前半固定至 2016-07-29，後半固定由 2016-08-01。
- **身份警告**：所有股票均是 2026 現時代號；不得把歸因冒充歷史 point-in-time 證據。

## 十四項事前反證門檻

即使 14/14，最高亦只可寫「同一 survivor-contaminated 樣本內，高段相對中段在兩項控制後
未被本輪額外推翻」；不得建立策略或 Paper：

1. 第 24–27 輪、原始事件、行情、panel、watchlist 及 bucket 收據逐字一致；
2. 905 個事件、兩個 universe 的 5 日回報、20 日波幅及未來回報完整；
3. 第 27 輪 bucket、事件次序及 raw spread 逐列重播；
4. OLS rank／condition、residual mean及歸因 identity 全部通過；
5. eligible raw top-middle 平均正、NW t 不低於 1.96、前後半均正；
6. complete raw top-middle 同上；
7. eligible residual top-middle 同上；
8. complete residual top-middle 同上；
9. eligible raw bottom-middle 平均負、NW t 不高於 -1.96、前後半均負；
10. complete raw bottom-middle 同上；
11. eligible residual bottom-middle 同上；
12. complete residual bottom-middle 同上；
13. 兩個 residual top-middle 保留至少 75% raw 平均，且八列 Holm／共同 max-t p 全部不高於
    0.05；
14. 訊號日 QQQ 兩種市況及 46-event 尾部中，兩個 residual top-middle 均為正且 NW t 不低於
    1.96。

## Fail-closed 控制與變異攻擊

實作至少須逐項驗證以下 23 道控制，並以每次只改一欄的 23 項攻擊命中穩定 error code：

1. 協議 SHA；
2. 第 27 輪來源 commit；
3. 第 27 輪收據 SHA；
4. 第 24–26 輪收據 SHA；
5. 原始事件收據 SHA；
6. 行情 archive SHA／panel fingerprint；
7. watchlist SHA；
8. 三個台股參考 commit；
9. 25 股 cohort；
10. 905 事件及嚴格日期次序；
11. 5 日回報窗口；
12. 20 日波幅窗口及 `ddof=1`；
13. 平均 rank 轉換；
14. OLS 欄序、`lstsq` 及 condition 上限；
15. eligible／complete universe；
16. 第 27 輪 bucket assignment SHA；
17. D+1／20 session／20 bps；
18. raw／predicted／residual identity；
19. 八假說 family、Holm 及 NW lag 4；
20. 52-event／20,000／seed 28202610 共同 bootstrap；
21. QQQ 20 日 known-at regime；
22. 46-event 尾部及固定前後半；
23. 現時代號只可警告、`paper_authorized=false`、`real_money_authorized=false`、正式策略 run 0。

任何輸入、控制、bucket、OLS、family、bootstrap、壓力或決策邊界不符，必須在輸出前 fail
closed。輸出若產生，必須保存事件級特徵／歸因 receipt、八列、14 個 gate、至少 23 個
control／attack、壓力及機器可重播收據。

## 升格邊界

正式就緒維持 `1/18`、point-in-time 維持 `1/20`、合格 provider package `0`、正式策略 run
`0`、短線 Paper 全現金、持倉 `0`、實金動作 `US$0`。只有合法授權的 point-in-time 成分、
永久證券 ID、歷史行業、公司行動、退市／退出經濟、同步基準及精確 RF 全部通過既有閘門，
才可按原事前登記運行一次正式 20 年回測；通過後仍須由下一個新增交易日全現金開始 Paper。
