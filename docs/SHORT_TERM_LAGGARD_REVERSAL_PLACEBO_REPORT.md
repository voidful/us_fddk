# 美股短線落後反轉 placebo robustness 報告（Round 58）

版本：1.0  
研究快照截至：2026-07-31  
狀態：**負面控制診斷（5/6 gate）；不建立策略、不建立 Paper；實金動作 US$0；今天不下單。**

## 結論

本輪是 Round 57 之後的固定 placebo control：保留同一個 30 檔現時大型股觀察池、五日跌幅
不高於 -5%、最弱 Top-5、20 bps 成本及 5／10／20-session 持有期，只將市場條件改為
SPY 單日上升至少 1.5%。結果 20-session 相對價格／流動性合資格池雖為正，但 Newey–West
t=1.74，未達預先固定的 1.96；因此不能說 Round 57 的市場急跌條件帶來獨立可重複優勢，
亦不能把 placebo 的正平均差當作交易訊號。

| 指標 | 5-session | 10-session | 20-session 主要 |
| --- | ---: | ---: | ---: |
| 完整事件數 | 54 | 54 | 54 |
| 落後 Top-5 平均回報（扣 20 bps） | 0.011% | 1.143% | 2.588% |
| 合資格池等權平均回報 | -0.710% | 0.119% | 1.209% |
| 配對差 | +0.721 個百分點 | +1.025 個百分點 | +1.379 個百分點 |
| SPY／QQQ 同期平均回報 | -0.877%／-0.881% | -0.451%／-0.339% | +0.338%／+0.479% |
| Newey–West t | 1.46 | 1.90 | **1.74** |
| bootstrap 95% 下界 | +0.269 個百分點 | +0.320 個百分點 | +0.231 個百分點 |
| 配對勝率 | 59.3% | 66.7% | 57.4% |

主要 20-session gate 為 **5/6**：事件數、平均差、bootstrap 下界、勝率及前後固定段均通過；
只有 Newey–West t 未通過。樣本只有 54 宗，事件可重疊，且 30 檔名單是現時觀察池倒推，
不能視為歷史可投資全集。

## 研究邊界

- 這是 post-Round57 robustness extension，`independent_first_seen_evidence=false`，不是
  獨立首次發現，也沒有改動 Round57 規則。
- adjusted OHLCV 並非 raw execution 或完整 total-return ledger；沒有退市／收購缺口及盤中
  timestamp。平均事件回報不是資金曲線或可實現回報。
- 沒有 point-in-time universe、forward contract 或合資格 Paper admission，因此不建立
  strategy run、Paper account、個別標的名單或實金落盤。

結果只寫入研究 log 和機器收據；公開頁面只接受已驗證可行策略，目前仍顯示「今天不下單」。

機器收據：

- protocol：`artifacts/short_term_laggard_reversal_placebo_protocol_receipt.json`；
- validation：`artifacts/short_term_laggard_reversal_placebo_validation.json`；
- multiplicity：Round58 placebo family，全域下限 6308。

本報告只作研究及教育用途，不構成投資建議、Paper 成交或實金落盤指令。
