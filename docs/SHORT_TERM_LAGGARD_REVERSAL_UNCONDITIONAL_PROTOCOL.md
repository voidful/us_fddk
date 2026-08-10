# 短線落後反轉無市場濾網控制協議（Round 59）

版本：1.0（post-hoc robustness，只作控制診斷）
固定日期：2026-08-10

## 研究角色

本輪是 Round 57「SPY 急跌＋個股落後」及 Round 58 上升市 placebo 之後的控制檢驗。它保留
同一個現時 30 檔大型股觀察池、價格／流動性門檻、五日落後條件、最弱 Top-5 排序、持有期
及交易成本，**只移除市場條件**。因此它不是獨立首次證據，也不是新的策略搜尋；目的只是
量度急跌濾網是否有增量價值。規則、股票池、期間及成本在本輪執行前固定，結果不會改寫
Round 57／58，也不會建立 Paper 或實金行動。

## 不可變資料及期間

- 資料：`snapshot_20260731_6a7ca6b8.zip`，只接受 archive SHA、panel fingerprint 及
  watchlist SHA 全部吻合。
- 期間：2006-08-01 至 2026-07-31；只使用已完成 XNYS session。
- 觀察池：與 Round 57／58 相同的固定 30 檔大型股名單。此池有 survivorship bias，不能
  代表歷史可投資全集。
- 本輪是 `posthoc_robustness_diagnostic`；不得把結果描述成預註冊的獨立策略證據。

## 固定訊號及執行

1. 每個完成交易日收市計算；個股價格必須高於 US$5，20-session median dollar volume 至少
   US$20m。
2. 不套用 SPY、QQQ 或任何市場方向濾網。
3. 個股落後條件為五個 session close-to-close 回報不高於 -5%。
4. 在同時符合條件的個股中按五日回報由低至高排序，取最弱 Top-5；不足 5 檔即跳過。
5. 下一個交易日 adjusted open 進場，於第 5、10、20 個交易日 adjusted close 離場；每宗
   事件扣固定 round-trip 20 bps，不使用停損、槓桿、盤中 timestamp 或事後調參。

## 基準、gate 及邊界

- 合資格池只套用價格及流動性條件；另列完整現時股池、SPY 及 QQQ 作同期參考。
- 沿用六項主要診斷 gate：至少 30 宗完整事件、相對合資格池平均差額為正、Newey–West t
  至少 1.96、moving-block bootstrap 下界為正、配對勝率嚴格高於 50%、前後固定期間平均
  差額均為正。
- 即使無市場濾網控制通過全部 gate，也只代表現時 survivor cohort 內的事後控制結果；
  它不能證明 Round 57 的急跌條件有增量 alpha，更不能修復 survivorship、adjusted OHLCV、
  事件重疊或 point-in-time／退市數據缺口。
- 本輪只產生 aggregate research log 及 append-only trial ledger。`paper_authorized=false`、
  `real_money_authorized=false`、`real_money_action_usd=0`，首頁行動維持「今天不下單」。

## 多重比較

本輪預先把 5、10、20-session 三個 horizon 視為一個新 family，global trial lower bound
由 6308 增加至少 3 至 6311；不聲稱精確增量。family 角色固定為
`posthoc_robustness_diagnostic`，不是可交易策略。
