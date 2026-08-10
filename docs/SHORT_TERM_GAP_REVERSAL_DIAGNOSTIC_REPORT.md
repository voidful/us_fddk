# 美股短線 Gap-down 反轉診斷報告（Round 56）

版本：1.0
研究快照截至：2026-07-31
狀態：**診斷負面；不建立策略、不建立 Paper；實金動作 US$0；今天不下單。**

## 結論

事前固定的每日 gap-down 反轉訊號，在現時 30 檔大型股倒推池中產生 48 宗完整事件。候選
Top-5 的 20-session 平均回報高於合資格池，但統計 gate 只有 **3/6** 通過，不能升格為
短線交易策略：

| 指標 | 20-session 結果 |
| --- | ---: |
| 候選 Top-5 平均回報（扣 20 bps） | 4.132% |
| 合資格池等權平均回報 | 1.901% |
| 配對差 | +2.231 個百分點 |
| 完整現時股池等權平均回報 | 1.888% |
| SPY／QQQ 平均回報 | 0.678%／1.629% |
| Newey–West t | 1.73 |
| moving-block bootstrap 95% 下界 | -0.745 個百分點 |
| 配對勝率 | 60.4% |
| 前／後固定段配對差 | -0.921／+3.528 個百分點 |

事件數 gate、平均差額及配對勝率通過；Newey–West t 未達 1.96、bootstrap 下界低於零，
而且前段固定期間為負，顯示結果受後段市場狀況影響，未能證明穩健性。5-session 及
10-session 的配對差為 +0.736／+1.221 個百分點，但 t 值只有 1.56／1.51，bootstrap
下界同樣低於零，不能只挑長持有期 headline。

## 基準、成本與覆蓋

- 使用 2006-08-01 至 2026-07-31、42 欄 OHLCV 快照；完成交易日收市後計算，下一個交易日
  adjusted open 進場，5／10／20 個交易日 adjusted close 離場。
- Gap-down 定義為當日 adjusted open 相對前一個 session adjusted close 跌至少 2%；收市
  相對開市升至少 0.5%，並位於當日 high-low range 上四分位；合資格池只套用價格及流動性。
- 每宗事件扣固定 round-trip 20 bps；沒有停損、停利、槓桿、盤中 timestamp 或事後調參。
- 5／10／20-session 均為 48 宗完整事件；事件可重疊，這不是資金曲線或已可執行的投資
  組合。

## 為何不開 Paper

1. 現時 30 檔名單倒推 20 年，存在 survivorship bias，不能代表歷史可選股票全集。
2. 只有 adjusted OHLCV，沒有 raw execution、完整公司行動賬本、退市／收購回報或盤中
   timestamp。
3. 主要統計 gate 未全部通過，前段固定期間為負，不能宣稱穩健跑贏 SPY／QQQ 或保證盈利。
4. 本輪沒有建立正式 strategy run、Paper account、個別標的公開名單或實金動作。

結果只寫入研究 log 和機器收據；公開頁面繼續只呈現已驗證可行策略，目前顯示「今天不下單」。

機器收據：

- protocol：`artifacts/short_term_gap_reversal_diagnostic_protocol_receipt.json`；
- validation：`artifacts/short_term_gap_reversal_diagnostic_validation.json`；
- multiplicity：Round56 family `round56_gap_reversal_three_horizons`，全域下限 6302。

本報告只作研究及教育用途，不構成投資建議、Paper 成交或實金落盤指令。
