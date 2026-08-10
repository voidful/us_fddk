# 美股短線超賣反轉診斷報告（Round 55）

版本：1.0
研究快照截至：2026-07-31
狀態：**診斷負面；不建立策略、不建立 Paper；實金動作 US$0；今天不下單。**

## 結論

事前固定的每週超賣反轉訊號，在現時 30 檔大型股倒推池中產生 233 宗完整的 20-session
事件。候選組合的平均回報高於合資格池，但統計強度及 bootstrap 下界未達全部事前 gate，
因此不能升格為短線交易策略或行動建議：

| 指標 | 20-session 結果 |
| --- | ---: |
| 候選 Top-5 平均回報（扣 20 bps） | 3.043% |
| 合資格池等權平均回報 | 1.958% |
| 配對差 | +1.086 個百分點 |
| 完整現時股池等權平均回報 | 2.160% |
| SPY／QQQ 平均回報 | 1.105%／1.605% |
| Newey–West t | 1.54 |
| moving-block bootstrap 95% 下界 | -0.094 個百分點 |
| 配對勝率 | 50.2% |
| 前／後固定段配對差 | +0.267／+1.793 個百分點 |

六項主要 gate 通過 **4/6**；Newey–West t 未達 1.96，bootstrap 下界仍低於零。5-session
結果相對合資格池為 -0.088 個百分點，10-session 為 +0.155 個百分點；兩個較短持有期的
統計量同樣未達門檻，不能只挑 20-session headline 當成證明。

## 基準、成本與覆蓋

- 使用同一份 2006-08-01 至 2026-07-31、42 欄 OHLCV 快照；訊號於完成星期收市後計算，
  下一個交易日 adjusted open 進場，5／10／20 個交易日 adjusted close 離場。
- 超賣條件為固定 5-session 跌幅不低於 8% 且收市價觸及前 20-session 低位；基礎合資格
  池只套用價格及流動性條件，另列完整現時股池、SPY、QQQ。
- 每宗事件扣固定 round-trip 20 bps；沒有停損、停利、槓桿、盤中 timestamp 或事後調參。
- 5-session 234 宗、10／20-session 各 233 宗完整事件；這是事件診斷，不是資金曲線或已
  可執行的投資組合。

## 為何不開 Paper

1. 現時 30 檔名單倒推 20 年，存在 survivorship bias，不能代表當時可選股票。
2. 只有 adjusted OHLCV，沒有 raw execution、公司行動完整賬本、退市／收購回報或盤中
   成交量公開時間。
3. 統計門檻未全部通過；樣本可重疊，不能宣稱已穩健跑贏 ETF 或保證盈利。
4. 本輪沒有建立正式 strategy run、Paper account、個別標的公開名單或實金動作。

結果只寫入研究 log 和機器收據；公開頁面繼續只呈現已驗證可行策略，目前顯示「今天不下單」。

機器收據：

- protocol：`artifacts/short_term_oversold_reversal_diagnostic_protocol_receipt.json`；
- validation：`artifacts/short_term_oversold_reversal_diagnostic_validation.json`；
- multiplicity：Round55 family `round55_oversold_reversal_three_horizons`，全域下限 6299。

本報告只作研究及教育用途，不構成投資建議、Paper 成交或實金落盤指令。
