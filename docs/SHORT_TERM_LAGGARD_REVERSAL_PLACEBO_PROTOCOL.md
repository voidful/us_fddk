# 短線落後反轉 placebo robustness 診斷協議（Round 58）

版本：1.0（事前固定、只作 placebo 診斷）  
固定日期：2026-08-10

## 研究角色

本輪是 Round 57「SPY 急跌＋個股落後」結果之後的預先指定控制檢驗，不是新的策略搜尋，亦
不是獨立首次證據。保留同一個現時 30 檔大型股觀察池、價格／流動性門檻、五日落後條件、
Top-5 排序、持有期及交易成本，只把市場條件固定改為 **SPY 單日上升至少 1.5%**。
這個上升市 placebo 用來檢查表面上的落後反轉是否不依賴 Round 57 的市場急跌狀態；不論
結果正負，`strategy_rule_changed=false`、`paper_authorized=false`，不會建立 Paper 或實金
行動。

## 不可變資料及期間

- 資料：`snapshot_20260731_6a7ca6b8.zip`，只接受 archive SHA、panel fingerprint 及
  watchlist SHA 全部吻合。
- 期間：2006-08-01 至 2026-07-31；只使用已完成 XNYS session。
- 觀察池：與 Round 57 相同的固定 30 檔大型股名單。此池有 survivorship bias，不能代表
  歷史可投資全集。
- 本輪是 post-Round57 robustness extension；不得把本輪視為獨立首次發現，也不得因結果
  改變門檻、持有期、股票池或回測期間。

## 固定訊號及執行

1. 每個完成交易日收市計算；個股價格必須高於 US$5，20-session median dollar volume 至少
   US$20m。
2. placebo 市場條件為 SPY 當日 adjusted close 相對前一個 session adjusted close 上升至少
   1.5%（`SPY_t / SPY_{t-1} - 1 >= +1.5%`）。
3. 個股落後條件為五個 session close-to-close 回報不高於 -5%。
4. 在同時符合條件的個股中按五日回報由低至高排序，取最弱 Top-5；不足 5 檔即跳過。
5. 下一個交易日 adjusted open 進場，於第 5、10、20 個交易日 adjusted close 離場；每宗
   事件扣固定 round-trip 20 bps，不使用停損、槓桿、盤中 timestamp 或事後調參。

## 基準、gate 及邊界

- 合資格池只套用價格及流動性條件；另列完整現時股池、SPY 及 QQQ 作同期參考。
- 沿用 Round 57 的六項主要診斷 gate：至少 30 宗完整事件、相對合資格池平均差額為正、
  Newey–West t 至少 1.96、moving-block bootstrap 下界為正、配對勝率嚴格高於 50%、前後
  固定期間平均差額均為正。
- 即使 placebo 通過全部 gate，也只標記為控制檢驗；現時觀察池的 survivorship bias、
  adjusted OHLCV、事件重疊及資料供應缺口均阻止任何 Paper／實金升格。
- 本輪只產生 aggregate research log 及 append-only trial ledger。`paper_authorized=false`、
  `real_money_authorized=false`、`real_money_action_usd=0`，首頁行動維持「今天不下單」。

## 多重比較

本輪預先把 5、10、20-session 三個 horizon 視為一個新 family，global trial lower bound
由 6305 增加至少 3 至 6308；不聲稱精確增量。此 family 的研究角色固定為
`placebo_robustness_diagnostic`，不是可交易策略。
