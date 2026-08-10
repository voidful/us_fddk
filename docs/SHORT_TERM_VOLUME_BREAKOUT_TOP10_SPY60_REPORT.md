# 美股短線成交量突破 Top-10 × SPY 60 日趨勢資金會計報告（Round 63）

版本：1.0  
研究快照截至：2026-07-31  
狀態：**7/7 capital gate 通過的 post-hoc survivor-cohort 診斷；尚未升格策略；不建立 Paper；實金動作 US$0；今天不下單。**

## 結論

Round 62 的 Top-10 曲線只差 QQQ CAGR gate。本輪加入固定 `SPY close > 60-session SMA`
regime gate 後，356 宗候選中有 132 宗 accepted trades，224 宗因重疊跳過。

Top-10 資金曲線 final equity **US$24,643.33**、CAGR **17.41%**、零利率 Sharpe **0.84**，
最大回撤 **−38.78%**，持倉比例 **55.10%**。在這份現時 survivor cohort 的研究會計中，
七項 capital gate 全部通過，並高於 passive QQQ CAGR **16.70%**；但此閘門是在先前結果
出現後才新增，不能當作獨立首次證據或可直接交易的策略。

| 資金曲線 | Final equity | CAGR | 最大回撤 | 零利率 Sharpe | 勝率／持倉比例 |
| --- | ---: | ---: | ---: | ---: | ---: |
| Top-10 + SPY-60 regime | US$24,643 | **17.41%** | −38.78% | 0.84 | 62.12% / 55.10% |
| eligible pool（同期 schedule） | US$10,428 | 12.46% | **−18.19%** | **1.02** | 71.21% / 55.10% |
| complete cohort（同期 schedule） | US$10,895 | 12.71% | −20.06% | 1.05 | 70.45% / 55.10% |
| SPY（同期 schedule） | US$2,786 | 5.27% | −15.92% | 0.56 | 65.91% / 55.10% |
| QQQ（同期 schedule） | US$5,523 | 8.94% | −18.99% | 0.73 | 67.42% / 55.10% |
| SPY（全期 buy-and-hold） | US$8,455 | 11.29% | −55.19% | 0.65 | — / 100% |
| QQQ（全期 buy-and-hold） | US$21,839 | 16.70% | −53.40% | 0.81 | — / 100% |

相對 Round 62（無 regime、CAGR 16.55%、最大回撤 −40.24%），此 overlay 的研究曲線
CAGR 增加 0.86 個百分點、回撤改善 1.46 個百分點。不過 eligible pool 同期 Sharpe 及
回撤均更好，故不能把全部改善歸因於 Top-10 排名；這是需要正式 point-in-time 數據再驗證
的假說，而不是盈利保證。

所有曲線使用 2006-08-01 至 2026-07-31 固定快照、已完成 XNYS session、下一交易日
adjusted open、20 個交易日後 adjusted close及 20 bps round-trip 成本。這是 adjusted OHLCV
研究會計，不是券商可執行成交賬本。

## Gate 解讀

通過：至少 30 宗 accepted events、final equity 高於起始、CAGR 高於同期 eligible pool、
CAGR 高於 passive SPY、CAGR 高於 passive QQQ、最大回撤不深於 passive SPY、最大回撤不深於
passive QQQ。

「7/7」只代表固定收據下的 survivor-cohort 資金診斷一致，並不代表策略已通過完整准入：
`independent_first_seen_evidence=false`、point-in-time readiness 仍未通過，亦未包括退市／
收購回報、公司行動完整賬本、raw execution、滑價容量及多重檢驗後的獨立統計證據。

## 研究邊界及公開面

- 現時 30 檔 watchlist 是 survivor cohort，沒有 point-in-time 成分、退市／收購經濟及
  歷史 ticker mapping。
- adjusted OHLCV 不等於 raw execution；成交量沒有盤中公開時間戳；fractional equal-weight
  只是研究約定。
- SPY-60 gate 是 post-hoc market-regime overlay；不可再以此結果改動 SMA、Top-N、持有期、
  成本或其他條件救援。
- 沒有 strategy run、Paper account、個別標的名單或實金落盤；Paper 仍全現金。

結果只保留在研究 log／機器收據；公開網站只呈現已通過完整正式驗證且可執行的策略與行動
建議。本輪不更新網站，首頁維持「今天不下單」，不顯示實金比例或金額試算。

機器收據：

- protocol：`artifacts/short_term_volume_breakout_top10_spy60_protocol_receipt.json`；
- validation：`artifacts/short_term_volume_breakout_top10_spy60_validation.json`；
- multiplicity：Round63 family，全域下限至少 6315。

本報告只作研究及教育用途，不構成投資建議、Paper 成交或實金落盤指令。
