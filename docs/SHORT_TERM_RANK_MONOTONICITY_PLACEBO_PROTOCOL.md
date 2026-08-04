# 短線第 27 輪排序單調性與隨機 placebo 反證協議

狀態：**首次計算前凍結**  
研究角色：只可反證第 24–26 輪固定的 905 個 20 日事件；不得調校新策略、改變正式 v1、
啟動短線 Paper 或落實實金買賣。

## 問題與停止邊界

第 26 輪顯示原始 Top-7 對合資格池的平均差不是全部由 QQQ beta 解釋，但完整現時股池、
共同多重校正及 QQQ 下跌組均未通過。第 27 輪只回答：固定 20 日動量排序的未來 20 日回報，
在合資格池及完整現時 25 股股池內是否呈現由高至低的單調結構，而且能否勝過事前固定的
隨機排序 placebo？

本輪不是搜尋較佳 bucket 數、Top-K、持有期、成本、趨勢門檻、placebo 數量、seed 或
市場 regime。任何結果均不可：

1. 稱為 point-in-time／退市修正後 alpha；
2. 把 2026 現時代號或行業標籤冒充歷史永久身份；
3. 把三分組診斷變成可落盤 long-short 策略；
4. 產生最新買入名單；
5. 增加短線 Paper 持倉或實金動作；
6. 把通過控制、網站部署或 placebo 當成盈利保證。

若 905 個事件任何一個不能為完整 25 股計算訊號日前 20 日動量及同時鐘未來回報，父協議
必須以 `rank_monotonicity_coverage_mismatch` 在結果前停止；不得事後靜默刪除事件或股票。

## 固定輸入

| 輸入 | 固定值 |
|---|---|
| 第 26 輪來源 commit | `178a71f508b0e5bbd82287b65f1776e506947d3b` |
| 第 26 輪機器收據 | `artifacts/short_term_common_risk_residual_validation.json` |
| 第 26 輪收據 SHA-256 | `14727306343fbcf45eb82045363898e07bb6ff0487f0b3d580dec0a9f129637b` |
| 第 25 輪機器收據 SHA-256 | `11155736a8449e6c4f50c0de0d285df9598d76de3752733f5bd140d8a2c8d0f5` |
| 第 24 輪機器收據 SHA-256 | `4dc15a520606a03c85279bfaaca88367015bb651d0b6fbd77dffc9023cdbe282` |
| 原始事件收據 SHA-256 | `fa2463cc8273a316e4a98428767b695eb85c74e9ac75c47b5ca34592102979e8` |
| 行情快照 | `artifacts/snapshot_20260731_6a7ca6b8.zip` |
| 行情 archive SHA-256 | `d480fb82e712f06aabe0a98461e222344656b87022b8bda2cd7ccaa4c29ae88b` |
| 行情 panel fingerprint | `6a7ca6b83b1570007424daa46b0ff4e8fb4a655d39298a0f4f6d74c3b7ea3a66` |
| 現時觀察名單 SHA-256 | `b6002e4e151bd298884f8cdd6272b5cbfde8aedca47cb58b92830d4d92028014` |
| 事件 | 905 個；2006-08-04 至 2026-07-02 訊號日 |
| 現時完整 cohort | 與第 26 輪逐字一致的 25 隻股票 |
| 訊號／成交 | 訊號日 20 日動量；D+1 調整開市進場；持有 20 個 session 至調整收市 |
| 成本 | 每個全額投資 sleeve 各扣相同 20 bps round trip；配對差成本抵銷 |

現時完整 cohort 固定為：
`AAPL, AMAT, AMD, AMZN, BAC, BRK-B, CAT, COST, CSCO, CVX, GE, GOOG, GOOGL,
INTC, JNJ, JPM, LLY, LRCX, MA, MSFT, MU, NVDA, UNH, WMT, XOM`。

台股方法參考固定為：

- `tst_wocker`：`3372aa088328700feafeeb07c72ab832ea2d3ecb`
- `tw-block-warrant`：`37463c54796ba36f4aac262519ea7fc2ef797de6`
- `tst_wocker_filter_lab`：`06c87b7a1735877c9ccbab3a339c1742814a5058`

## 固定排序、三分組及回報

每個事件必須重建第 25 輪同一 `eligible` 清單及固定 25 股 `complete_cohort`。兩個 universe
分開進行以下程序：

1. 20 日動量固定為訊號日調整收市除以 20 個完整 session 前的調整收市減一；不得使用訊號
   日後價格。
2. 依動量由高至低排序；完全相同時以 ticker 字典序由小至大打破平手。
3. 使用等同 NumPy `array_split(sorted_symbols, 3)` 的固定連續切割：前段為 `top`、中段為
   `middle`、末段為 `bottom`。每股只可出現一次，三段聯集必須等於該 universe，段大小
   相差不得超過一；若有餘數，依序分配給 top、middle。
4. complete cohort 每個事件固定 25 股，故大小固定為 9／8／8。eligible 至少須有 7 股；
   三段均須非空。
5. 每段未來 gross return 為段內股票 D+1 調整開市至第 20 個持有 session 調整收市的簡單
   回報等權平均；net return 固定再扣 20 bps。
6. 固定比較為 `top-middle`、`middle-bottom`、`top-bottom`。兩邊都是全額投資及相同成本，
   配對差內成本恰好抵銷，但 gross、net 及成本仍須保存。
7. 正值比例把絕對值不高於 `1e-12` 的浮點殘差視為零；JSON 四捨五入後的負零須正規化。

## 固定 rank IC

每事件、每 universe 另計一個 Spearman rank information coefficient：

1. 訊號 rank 以 20 日動量由低至高的平均 rank 計算；相同動量使用平均 rank，不用 ticker
   人工製造差異。
2. 未來 rank 以同一股票未來 20 日 gross return 由低至高的平均 rank 計算。
3. IC 是兩組 rank 的 Pearson correlation；非有限或零變異即 fail closed。
4. IC 只作排序診斷，不是可交易回報，不扣成本，也不得與 sleeve 回報串接。

## 八假說共同 family

固定八列，不得刪除不利列：

1. `eligible_top_middle`
2. `eligible_middle_bottom`
3. `eligible_top_bottom`
4. `complete_top_middle`
5. `complete_middle_bottom`
6. `complete_top_bottom`
7. `eligible_rank_ic`
8. `complete_rank_ic`

每列呈列事件數、平均／中位、正值比例、Newey–West lag 4、普通兩尾常態 p、固定前後半、
Holm p 及共同 single-step max-t p。共同 bootstrap 固定為 52-event circular blocks、
20,000 路徑、seed `27202609`、八列使用同一組 indices並在零假設下去中心化。

正式全專案 6,208 次搜尋壓力不重設；本輪屬不得升格的診斷 family，不能把八列縮成一列
後聲稱是新的獨立 DSR。

## 二十組隨機排序 placebo

每個 universe 固定 20 組 placebo，ID 為 `P01`–`P20`：

1. 每事件先把 universe ticker 字典序排序。
2. 每個 permutation 使用 NumPy `default_rng(SeedSequence([27202608, universe_code,
   event_index, placebo_id]))`；`universe_code` 固定 eligible=1、complete=2，event_index 依
   訊號日由 0 起，placebo_id 為 1–20。
3. permutation 後以真實分組相同大小切成 placebo top／middle／bottom，只計 top-bottom。
4. 每組保存 905-event 平均、NW t 及前後半；不得挑掉跑贏真實排序的 placebo。
5. 真實 top-bottom 的平均及 NW t 必須分別嚴格高於同 universe 20 組 placebo 的最大值，
   才可通過 placebo dominance。20 是事前固定診斷數，不冒充精確 20,000-path p 值。

## 只可否決的附加壓力

- **市場方向**：使用同時鐘未來 QQQ gross return 把事件固定分成 `>=0` 與 `<0`；只對
  eligible／complete 真實 top-bottom 計 NW t，只作事後反證，不可變成 regime 訊號。
- **尾部**：各 universe 分別移除絕對 top-bottom 差最大的 46 個事件，再計 859 個事件的
  平均及 NW t；46 固定為 905 的向上取整 5%，不得改列數。
- **時段**：前半固定至 2016-07-29，後半固定由 2016-08-01；不得按結果改切點。
- **現時身份警告**：所有股票均是 2026 現時代號；本輪不得把結果用作歷史成分或退市修正
  證據。

## 十四項事前反證門檻

即使 14/14，最高亦只可寫「survivor-contaminated 排序線索未被本輪額外推翻」；不得建立
策略或 Paper：

1. 第 25 輪 Top-7／eligible／complete 回報逐列重建最大誤差不高於 `1e-12`；
2. 905 個事件兩個 universe 訊號及未來回報覆蓋完整；
3. 每事件三段無重疊、聯集完整、段大小相差不超過一；
4. eligible top-middle 平均為正、NW t 不低於 1.96、前後半均正；
5. eligible middle-bottom 同上；
6. eligible top-bottom 同上；
7. complete top-middle 同上；
8. complete middle-bottom 同上；
9. complete top-bottom 同上；
10. eligible／complete rank IC 均為正、NW t 不低於 1.96、前後半均正；
11. 八列 Holm p 及共同 max-t p 全部不高於 0.05；
12. eligible／complete 真實 top-bottom 的平均及 NW t 均嚴格高於各自 20 組 placebo 最大值；
13. 未來 QQQ 非負／負兩組的兩個真實 top-bottom 均為正且 NW t 不低於 1.96；
14. 各自移除最大 46 個絕對差事件後，eligible／complete top-bottom 仍為正且 NW t 不低於
    1.96。

## Fail-closed 控制與變異攻擊

實作至少須逐項驗證以下 23 道控制，並以每次只改一欄的 23 項攻擊命中穩定 error code：

1. 協議 SHA；
2. 第 26 輪來源 commit／收據 SHA；
3. 第 25／24 輪收據 SHA；
4. 原始事件收據 SHA；
5. 行情 archive SHA／panel fingerprint；
6. watchlist SHA；
7. 三個台股參考 commit；
8. 25 股 cohort 逐字一致；
9. 905 事件及嚴格日期次序；
10. 20／60／Top-7 原事件規則；
11. D+1／20 session／20 bps；
12. eligible／complete universe identity；
13. 20 日動量及訊號 known-at；
14. 動量降序／ticker 升序 tie-break；
15. 三段 `array_split`、聯集及互斥；
16. sleeve 等權及成本對稱；
17. Spearman 平均 rank 定義；
18. 八假說 family、Holm 及 NW lag 4；
19. 52-event／20,000／seed 27202609 共同 bootstrap；
20. 20 組 placebo、SeedSequence 欄序及 seed 27202608；
21. QQQ 市場方向、46-event 尾部及固定前後半；
22. 現時代號只可作警告、不得產生買入名單；
23. `paper_authorized=false`、`real_money_authorized=false`、正式策略 run 0。

任何輸入、排序、bucket、IC、family、seed、placebo、壓力或決策邊界不符，必須在輸出結果
前 fail closed。輸出若產生，必須保存全部事件級 bucket receipt、八列、40 組 placebo
結果、14 個 gate、至少 23 個 control／attack、壓力及機器可重播收據。

## 升格邊界

正式就緒維持 `1/18`、point-in-time 維持 `1/20`、合格 provider package `0`、正式策略
run `0`、短線 Paper 全現金、持倉 `0`、實金動作 `US$0`。只有合法授權的 point-in-time
成分、永久證券 ID、歷史行業、公司行動、退市／退出經濟、同步 QQQ／SPY 及精確 RF 全部
通過既有閘門，才可原樣運行一次正式 20 年回測；通過後仍須由下一個新增交易日全現金開始
Paper。
