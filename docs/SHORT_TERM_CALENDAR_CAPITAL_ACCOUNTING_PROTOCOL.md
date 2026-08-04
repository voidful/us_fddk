# 美股短線第 29 輪：日曆時間重疊持倉與資金賬本事前協議

狀態：**只凍結設計；本文件提交前不得計算任何第 29 輪回報、風險或門檻結果。**

## 研究問題

第 24–28 輪的主要證據以每週事件的 20 日回報差呈列。事件會互相重疊；事件平均為正，
不等於 US$1,000 在無槓桿、資金已被其他持倉佔用時可以取得同一經濟效果。台股
`tst_wocker_filter_lab` 的既有稽核亦指出，逐筆右尾、事件差額與組合層資金再投資可以得出
不同結論。

本輪只回答：把第 24 輪固定 20 日 Top-7 事件放入一個日曆時間、五個獨立資金槽、每槽
20%、零槓桿的長倉賬本後，能否在同成本下同時勝過合資格池等權、完整現時股池等權、
事件配對 QQQ、買入並持有 QQQ、SPY 及 SHY。

這仍是 2026 現時代號倒推的同一批已見 905 個事件，只可作反證與會計橋接，不是正式
point-in-time 回測、未見驗證、最新買入名單、Paper 或實金策略。

## 禁止事項

結果後不得：

1. 改事件頻率、Top-K、20／60 日訊號、五槽、持有期、成本或基準；
2. 依結果改用四槽、六槽、跨槽借款、再配重或只保留有利事件；
3. 依回報改選 QQQ／SPY／SHY 起點、危機期、NW lag、bootstrap block 或 seed；
4. 把事件配對多空差額冒充可落盤沽空策略；
5. 把調整價及 2026 現時代號冒充永久 ID、歷史成分或退市經濟；
6. 因任一本輪門檻通過而啟動 Paper、持倉或實金。

任何輸入、事件回報、槽位、日線估值、成本、基準或身份不能逐列重建即 fail closed；不得
刪除事件、補值或轉用另一份行情。

## 固定來源與收據

| 輸入 | 固定值 |
|---|---|
| 第 28 輪結果 commit | `0b4630f44ef405e8ff6ca1d992a9e2641473a92f` |
| 第 28 輪機器收據 | `artifacts/short_term_reversal_volatility_attribution_validation.json` |
| 第 28 輪收據 SHA-256 | `970801377fd981eebffa3aa970c2cc3c2ce958b453db678a068b953f363daef1` |
| 第 27 輪收據 SHA-256 | `3d362ed82ab8ed732d53344a1a8d787fe48374e042bdf8f13c54a0f0cea96448` |
| 第 24 輪收據 SHA-256 | `4dc15a520606a03c85279bfaaca88367015bb651d0b6fbd77dffc9023cdbe282` |
| 原始事件收據 SHA-256 | `fa2463cc8273a316e4a98428767b695eb85c74e9ac75c47b5ca34592102979e8` |
| 行情 archive SHA-256 | `d480fb82e712f06aabe0a98461e222344656b87022b8bda2cd7ccaa4c29ae88b` |
| 行情 panel fingerprint | `6a7ca6b83b1570007424daa46b0ff4e8fb4a655d39298a0f4f6d74c3b7ea3a66` |
| 現時觀察名單 SHA-256 | `b6002e4e151bd298884f8cdd6272b5cbfde8aedca47cb58b92830d4d92028014` |
| 事件 | 905 個；訊號 2006-08-04 至 2026-07-02；最後退出 2026-07-31 |
| 槽位 assignment SHA-256 | `3be9948565e7c58e951a50110e6063185c8c93a12b1cf97c2014b981b25c5547` |

台股方法參考固定為：

- `tst_wocker@3372aa088328700feafeeb07c72ab832ea2d3ecb`；
- `tw-block-warrant@37463c54796ba36f4aac262519ea7fc2ef797de6`；
- `tst_wocker_filter_lab@06c87b7a1735877c9ccbab3a339c1742814a5058`。

## 固定訊號、成交與股票集合

- 完全重播原事件：訊號日調整收市已知的 20 日動量、60 日趨勢、訊號價高於 US$5、
  20 日中位美元成交額至少 US$20m，按動量降序及 ticker 升序 tie-break，Top-7。
- 訊號後一個 session 以調整開市進場，持有 20 個 session，在第 20 個 session 調整收市
  退出；不使用同日收市成交。
- `eligible` 為各事件原合資格股票；`complete` 固定為同一 25 隻 2026 現時代號。
- 分數股只為 US$1,000 比例研究；不設最小股數、稅項或融資，亦不表示券商可成交。

## 五槽無槓桿資金賬本

結構在任何回報計算前由 entry／exit 日期唯一決定：

1. 初始資本 US$1,000，五個互不借款的槽各 US$200；槽外沒有額外資本。
2. 事件按既有次序分配至 `slot = event_index mod 5`；每槽恰有 181 個事件。
3. 同槽上一事件必須在下一事件進場日前退出；同日「開市進新、收市退舊」不准共用一槽。
4. 活躍區間包含 entry 與 exit；任一日最多五槽活躍。未活躍槽為零回報現金。
5. 每槽只以自己上一事件退出後的資金複利；禁止跨槽轉移、借款、槓桿及預支未退出資金。
6. 每事件入場成本固定 10 bps、退出成本 10 bps。日內標記相對該事件 entry open 的等權
   gross return；entry 日扣 10 bps、exit 日再扣 10 bps，因此 exit 淨回報必須逐列精確等於
   原事件 `gross mean - 20 bps`。
7. 日曆路徑由 2006-08-04 的 US$1,000 現金起步，2006-08-07 首次進場，至
   2026-07-31 最後退出；所有策略每日使用同一 XNYS session 索引。

日線總資產必須等於五個槽的現金或持倉標記總和；總 long exposure 不高於總資產、cash
不低於零、槽位不重疊。任何 identity 誤差高於 `1e-12` 即停止。

## 七條固定日曆路徑

同一五槽、時鐘及主要 20 bps round trip：

1. `top7_five_slot`：每事件 Top-7 等權；唯一候選。
2. `eligible_equal_five_slot`：同事件合資格池等權。
3. `complete_equal_five_slot`：完整現時 25 股等權。
4. `qqq_event_five_slot`：每個事件槽全數持有 QQQ。
5. `qqq_buy_hold`：首次 entry open 買入，最後 exit close 賣出，只收一次來回成本。
6. `spy_buy_hold`：同上。
7. `shy_buy_hold`：同上；亦作每日 cash／risk-free 可交易代理。

買入並持有基準不得因候選時鐘而每週重買；事件配對 QQQ 與 QQQ buy-and-hold 必須同時
呈列，以分開選股差額與週期性退出／重進成本。另固定把所有五槽路徑的 round trip 同步
改為 50 bps 及 100 bps 作成本壓力；不得只提高候選或只提高基準成本。

## 固定績效與公平比較

每條路徑呈列：總回報、CAGR、年率化波幅、以 SHY 日回報為 cash proxy 的 excess Sharpe、
excess Sortino、最大跌幅、Calmar、US$1,000 期末值、成本拖累及年換手。主結果使用完整
2006-08-04 至 2026-07-31 日線；SHY 只是可交易現金代理，不是無風險保證。

候選對六基準形成固定六假說 family。每日 active return 使用同一 session 相減，呈列：

- 平均日差、年率化算術差、正值比例；
- Newey–West lag 20 兩尾 t 與普通常態 p；
- Holm p；
- 63-session circular moving-block、20,000 共同路徑、seed `29202608` 的 single-step
  max-t p；
- 固定前半至 2016-07-29、後半由 2016-08-01；
- 每個曆年 active compounded return。

正式全專案搜尋次數由 6,208 加本輪六假說至 **6,214**；候選對合資格池的普通 p 另呈列
6,214 次 Bonferroni。不得重設搜尋次數。

## 固定附加壓力

- **最佳年份移除**：按候選相對合資格池的曆年 active compounded return，移除最高三年，
  在其餘共同日重算 NW lag 20；移除規則不得看其他 baseline。
- **危機期**：2008、2020、2022 分別呈列七路徑回報及最大跌幅；不因結果改危機年份。
- **成本**：50／100 bps 同步重建五槽四路徑，另重算候選對 eligible／complete／QQQ event
  的 CAGR 與期末值差。
- **身份**：結果首頁及決策必須明示現時 survivor cohort、正式就緒 1/18、point-in-time
  1/20、供應商包 0、正式 run 0。

## 十八項事前反證門檻

1. 所有輸入、protocol、panel、watchlist、事件及參考 commit 精確；
2. 905 個 Top-7／eligible／complete／QQQ 事件淨回報逐列重建誤差不高於 `1e-12`；
3. assignment SHA、五槽、每槽 181 事件及最大五個 concurrent interval 精確；
4. 每日槽位、現金、無槓桿、成本與總資產 identity 全通過；
5. 主要候選 CAGR 高於 eligible 五槽；
6. 主要候選 CAGR 高於 complete 五槽；
7. 主要候選 CAGR 高於 QQQ event 五槽；
8. 主要候選 CAGR 高於 QQQ buy-and-hold；
9. 主要候選 CAGR 高於 SPY buy-and-hold；
10. 候選 SHY-excess Sharpe 為正且高於 eligible、complete 與 QQQ event；
11. 候選最大跌幅不得比 QQQ buy-and-hold 深超過 10 個百分點；
12. 候選對 eligible 的平均日差為正且 NW t 不低於 1.96；
13. 候選對 complete 的平均日差為正且 NW t 不低於 1.96；
14. 候選對 QQQ event 的平均日差為正且 NW t 不低於 1.96；
15. 候選對 eligible／complete／QQQ buy-and-hold／SPY 的前後兩半平均日差全正；
16. 候選對 eligible 的 Holm p 與共同 max-t p 均不高於 0.05；
17. 移除最佳三年後候選對 eligible 仍為正且 NW t 不低於 1.96；
18. 6,214 次 Bonferroni p 不高於 0.05，且 50／100 bps 時候選 CAGR 仍同時高於
    eligible、complete 與 QQQ event。

任何一項未通過即 `can_promote_from_this_round=false`。即使 18/18，本輪仍因 survivor
cohort 及已見樣本不得啟動 Paper；必須另取得合格 point-in-time／退市數據 20/20，按已
凍結正式規則重跑，並再通過 252 個新增 session／12 次完成重新平衡的前瞻門檻。

## Fail-closed 控制與單欄變異攻擊

實作須保存至少 25 道控制及 25 項攻擊，逐項覆蓋：protocol hash／commit、三個父收據、
snapshot、panel、watchlist、三個參考 commit、事件數／次序、完整 cohort、訊號與成交時鐘、
slot assignment／數目／資本、成本、七路徑、SHY excess 定義、日線 identity、績效定義、
六假說 family、NW lag、bootstrap block／paths／seed、固定半期、危機／尾部、6,214 trials、
現時身份警告及 Paper／實金越權。每項只改一欄並須命中穩定錯誤碼。

## 固定輸出與決策邊界

若計算成功，輸出：

- `artifacts/short_term_calendar_capital_accounting_validation.json`；
- `site/data/short-term-calendar-capital-accounting.json`；
- `docs/SHORT_TERM_CALENDAR_CAPITAL_ACCOUNTING_RESEARCH_REPORT.md`。

報告使用香港金融用詞，完整呈列七條路徑、六假說、成本、危機、最佳年份移除、18 道
門檻、控制、攻擊、限制及負結果；不得只放最好數字。短線 Paper 維持全現金、持倉 0，
US$1,000 只作讀者比例與歷史尺度示例，實金動作固定 US$0。
