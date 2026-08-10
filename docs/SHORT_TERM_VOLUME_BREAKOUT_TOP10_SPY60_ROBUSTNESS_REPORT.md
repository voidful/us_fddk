# 美股短線成交量突破 Top-10 × SPY 60 日趨勢 robustness 報告（Round 64）

版本：1.0  
研究快照截至：2026-07-31  
狀態：**robustness 負面診斷（3/6 gate）；不建立策略、不建立 Paper；實金動作 US$0；今天不下單。**

## 結論

本輪重播 Round 63 的同一個 356 宗候選／132 宗 accepted event schedule，只改用固定 20／
50 bps 成本及前後十年分段。完整期 20 bps 仍維持 7/7 capital gate，但 **50 bps CAGR
降至 15.10%，低於 QQQ 的 16.69%**；前十年 20／50 bps 亦分別只有 5.86%／4.06%，
低於 QQQ 的 13.08%／13.04%。

| 範圍 | 成本 | 策略 CAGR | QQQ CAGR | 策略最大回撤 | QQQ 最大回撤 |
| --- | ---: | ---: | ---: | ---: | ---: |
| 完整 2006–2026 | 20 bps | **17.41%** | 16.70% | −38.78% | −53.40% |
| 完整 2006–2026 | 50 bps | 15.10% | **16.69%** | −40.59% | −53.40% |
| 前半 2006–2016 | 20 bps | 5.86% | **13.08%** | −32.99% | −53.40% |
| 前半 2006–2016 | 50 bps | 4.06% | **13.04%** | −35.36% | −53.40% |
| 後半 2016–2026 | 20 bps | **27.10%** | 20.42% | −38.78% | −35.12% |
| 後半 2016–2026 | 50 bps | **24.30%** | 20.38% | −40.59% | −35.12% |

robustness gate 只通過 **3/6**：完整期 20 bps 的 Round 63 gate、後半 20 bps、後半
50 bps。完整期 50 bps 及前半兩個成本情景均失敗；正面結果主要由後十年貢獻，不能稱為
跨市場週期穩健跑贏 QQQ。

## 資金會計

- US$1,000 起始資金；一次只持有一宗；20 個交易日離場；下一交易日 adjusted open 入場。
- 20 bps 完整期 final equity **US$24,643**；50 bps **US$16,574**。
- 20 bps accepted event 勝率 **62.12%**、持倉比例 **55.10%**；事件平均回報不取代資金曲線。
- 成本壓力只改 round-trip 成本，沒有為候選單獨增加成本或改動事件 schedule。

## 研究邊界及公開面

- 現時 30 檔 watchlist 是 survivor cohort，沒有 point-in-time 成分、退市／收購經濟、歷史
  ticker mapping 或完整公司行動賬本。
- adjusted OHLCV 不等於 raw execution；成交量沒有盤中公開時間戳；fractional equal-weight
  只是研究約定。
- 這是 post-hoc robustness 診斷，不是獨立首次證據；不能以後半期結果再改 regime、成本、
  Top-N 或持有期。

失敗結果只保留在研究 log／機器收據；公開網站只呈現已通過完整正式驗證且可執行的策略與
行動建議。本輪不更新網站，首頁維持「今天不下單」，不顯示實金比例或金額試算。

機器收據：

- protocol：`artifacts/short_term_volume_breakout_top10_spy60_robustness_protocol_receipt.json`；
- validation：`artifacts/short_term_volume_breakout_top10_spy60_robustness_validation.json`；
- multiplicity：Round64 family，全域下限至少 6316。

本報告只作研究及教育用途，不構成投資建議、Paper 成交或實金落盤指令。
