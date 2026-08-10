# 美股短線成交量確認突破診斷報告（Round 54）

版本：1.0  
研究快照截至：2026-07-31  
狀態：**診斷負面；不建立策略、不建立 Paper；實金動作 US$0；今天不下單。**

## 結論

事前固定的每週「60 日收市突破＋成交量至少為 20 日中位數 1.5 倍」訊號，在現時 30 檔
大型股倒推池中產生 403 宗完整事件。主要 20-session 結果的平均差額及統計量為正，
但事件勝率只有 49.9%，未通過全部事前 gate，不能升格為短線交易策略：

| 指標 | 20-session 結果 |
| --- | ---: |
| 候選 Top-5 平均回報（扣 20 bps） | 2.144% |
| 合資格池等權平均回報 | 1.392% |
| 配對差 | +0.753 個百分點 |
| 完整現時股池等權平均回報 | 1.506% |
| SPY／QQQ 平均回報 | 0.538%／1.025% |
| Newey–West t | 2.03 |
| moving-block bootstrap 95% 下界 | +0.092 個百分點 |
| 配對勝率 | 49.9% |
| 前／後固定段配對差 | +0.425／+1.028 個百分點 |

六項主要 gate 通過 **5/6**；唯一失敗是勝率沒有嚴格高於 50%。5-session 及 10-session
的 t 值分別為 0.94 及 1.18，bootstrap 下界仍低於零；不能只挑 20-session 的 headline
當成證明。

## 基準、成本與覆蓋

- 使用同一份 2006-08-01 至 2026-07-31、42 欄 OHLCV 快照；訊號於完成星期收市後計算，
  下一個交易日 adjusted open 進場，5／10／20 個交易日 adjusted close 離場。
- 合資格池只套用價格、流動性、60 日趨勢及正 20 日回報，不套用突破及成交量條件；
  另列完整現時股池、SPY、QQQ。
- 每宗事件扣固定 round-trip 20 bps；沒有停損、停利、槓桿、盤中 timestamp 或事後調參。
- 5／10／20-session 完整事件數均為 403，平均候選數約 1.9 檔；訊號稀疏且不是投資組合
  資金曲線。

## 為何不開 Paper

1. 現時 30 檔名單倒推 20 年，存在 survivorship bias，不能代表當時可選股票。
2. 只有 adjusted OHLCV，沒有 raw execution、公司行動完整賬本、退市／收購回報或盤中
   成交量公開時間。
3. 配對勝率未過 50%，主要統計優勢接近門檻，且事件可重疊；沒有足夠證據宣稱可穩健賺錢。
4. 本輪沒有建立正式 strategy run、Paper account、個股公開名單或實金動作。

結果只寫入研究 log 和機器收據；公開頁面繼續只呈現已驗證可行策略，目前顯示「今天不下單」。

機器收據：

- protocol：`artifacts/short_term_volume_breakout_diagnostic_protocol_receipt.json`；
- validation：`artifacts/short_term_volume_breakout_diagnostic_validation.json`；
- multiplicity：Round54 family `round54_volume_breakout_three_horizons`，全域下限 6296。

本報告只作研究及教育用途，不構成投資建議、Paper 成交或實金落盤指令。
