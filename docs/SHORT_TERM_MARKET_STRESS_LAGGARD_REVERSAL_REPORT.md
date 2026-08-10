# 美股短線市場急跌落後股反彈診斷報告（Round 57）

版本：1.0
研究快照截至：2026-07-31
狀態：**診斷正面但受 survivorship bias 限制；不建立策略、不建立 Paper；實金動作 US$0；今天不下單。**

## 結論

事前固定的「SPY 單日急跌＋個股五日落後」訊號，在現時 30 檔大型股倒推池中產生 204 宗
完整事件。20-session 主要結果相對合資格池為正，且六項診斷 gate 全部通過；這是目前
研究鏈中最值得以 point-in-time 數據重測的候選，但不是已獲准的交易策略：

| 指標 | 20-session 結果 |
| --- | ---: |
| 候選最弱 Top-5 平均回報（扣 20 bps） | 3.832% |
| 合資格池等權平均回報 | 2.476% |
| 配對差 | +1.355 個百分點 |
| 完整現時股池等權平均回報 | 2.721% |
| SPY／QQQ 平均回報 | 1.549%／2.049% |
| Newey–West t | 2.53 |
| moving-block bootstrap 95% 下界 | +0.337 個百分點 |
| 配對勝率 | 53.9% |
| 前／後固定段配對差 | +0.660／+2.024 個百分點 |

六項主要 gate 通過 **6/6**。5-session 及 10-session 配對差分別為 +1.030／+1.194 個百分點，
Newey–West t 為 3.34／2.98，bootstrap 下界亦為正；不同持有期方向一致。

## 基準、成本與覆蓋

- 使用 2006-08-01 至 2026-07-31、42 欄 OHLCV 快照；訊號於完成交易日收市後計算，下一個
  交易日 adjusted open 進場，5／10／20 個交易日 adjusted close 離場。
- 市場狀態為 SPY 當日 close-to-close 跌至少 1.5%；個股條件為五日 close-to-close 跌至少
  5%，按五日回報由低至高取最弱 Top-5；合資格池只套用價格及流動性。
- 每宗事件扣固定 round-trip 20 bps；沒有停損、停利、槓桿、盤中 timestamp 或事後調參。
- 5／10／20-session 均為 204 宗完整事件；事件可重疊，這不是正式資金曲線。

## 為何仍不開 Paper

1. 30 檔名單是現時觀察池，倒推 20 年有 survivorship bias；六項 gate 不能修復歷史成分及
   退市缺口。
2. 只有 adjusted OHLCV，沒有 raw execution、完整公司行動賬本、退市／收購回報或盤中
   timestamp。
3. Round57 是全域搜尋下限 6305 前的一個新 family；結果需要獨立 point-in-time universe、
   成本壓力、placebo／分層及前瞻交易日確認，不能把事件平均回報當成可賺錢保證。
4. 本輪沒有建立正式 strategy run、Paper account、個別標的公開名單或實金動作。

結果只寫入研究 log 和機器收據；公開頁面繼續只呈現已驗證可行策略，目前顯示「今天不下單」。

機器收據：

- protocol：`artifacts/short_term_market_stress_laggard_reversal_protocol_receipt.json`；
- validation：`artifacts/short_term_market_stress_laggard_reversal_validation.json`；
- multiplicity：Round57 family `round57_market_stress_laggard_reversal_three_horizons`，
  全域下限 6305。

本報告只作研究及教育用途，不構成投資建議、Paper 成交或實金落盤指令。
