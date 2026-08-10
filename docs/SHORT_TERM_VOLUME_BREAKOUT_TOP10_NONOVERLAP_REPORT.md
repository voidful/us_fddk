# 美股短線成交量突破 Top-10 分散度資金會計報告（Round 62）

版本：1.0  
研究快照截至：2026-07-31  
狀態：**負面集中度診斷（6/7 gate）；只寫研究 log；不建立策略、不建立 Paper；實金動作 US$0；今天不下單。**

## 結論

Round 61 的 Top-5 資金曲線回撤較深。本輪固定把同一成交量確認突破訊號改為 Top-10，
只作 post-hoc 分散度壓力測試；其餘快照、成本、成交時鐘及單一帳戶規則完全不變。377 宗
候選中有 138 宗 accepted trades，239 宗因重疊跳過。

Top-10 final equity 為 **US$21,279.74**、CAGR **16.55%**、零利率 Sharpe **0.80**，
最大回撤 **−40.24%**，持倉比例 **57.60%**。它只差 passive QQQ 的 CAGR gate（16.70%），
並且回撤比 QQQ 淺 13.17 個百分點；但這是事後改變選股數的診斷，不能升格為可行策略。

| 資金曲線 | Final equity | CAGR | 最大回撤 | 零利率 Sharpe | 勝率／持倉比例 |
| --- | ---: | ---: | ---: | ---: | ---: |
| Top-10 selected | US$21,280 | **16.55%** | −40.24% | 0.80 | 63.04% / 57.60% |
| eligible pool（同期 schedule） | US$9,303 | 11.82% | **−23.54%** | 0.94 | 73.19% / 57.60% |
| complete cohort（同期 schedule） | US$10,240 | 12.36% | −27.32% | 0.98 | 71.74% / 57.60% |
| SPY（同期 schedule） | US$2,467 | 4.63% | −24.91% | 0.48 | 67.39% / 57.60% |
| QQQ（同期 schedule） | US$5,152 | 8.56% | −26.40% | 0.67 | 67.39% / 57.60% |
| SPY（全期 buy-and-hold） | US$8,455 | 11.29% | −55.19% | 0.65 | — / 100% |
| QQQ（全期 buy-and-hold） | US$21,839 | **16.70%** | −53.40% | 0.81 | — / 100% |

Top-10 相對 Round 61 Top-5 的主要變化是回撤由 −54.99% 降至 −40.24%，但事件數由 146
降至 138，且 CAGR 仍差 QQQ 0.15 個百分點。同期 eligible pool 的回撤更淺、Sharpe 更高，
顯示排名選股仍未證明為必要的超額來源。

所有曲線使用 2006-08-01 至 2026-07-31 固定快照、已完成 XNYS session、下一交易日
adjusted open、20 個交易日後 adjusted close及 20 bps round-trip 成本。這是 adjusted OHLCV
研究會計，不是券商可執行成交賬本。

## Gate 解讀

通過：至少 30 宗 accepted events、final equity 高於起始、CAGR 高於同期 eligible pool、
CAGR 高於 passive SPY、最大回撤不深於 passive SPY、最大回撤不深於 passive QQQ。  
失敗：CAGR 不高於 passive QQQ。

這個結果支持「增加持股數可降低集中回撤」的有限診斷，不支持「Top-10 已能穩健跑贏 ETF」。
它是看到 Round 61 後才加入的 concentration-stress family，`independent_first_seen_evidence`
固定為 false，不能用來挑選新參數或產生買入名單。

## 研究邊界及公開面

- 現時 30 檔 watchlist 是 survivor cohort，沒有 point-in-time 成分、退市／收購經濟及
  歷史 ticker mapping。
- adjusted OHLCV 不等於 raw execution；成交量沒有盤中公開時間戳；fractional equal-weight
  只是研究約定。
- Top-10 是事後集中度壓力診斷，不是獨立首次證據；沒有 strategy run、Paper account、
  個別標的名單或實金落盤。

失敗結果只保留在研究 log／機器收據；公開網站只呈現已通過全部必要驗證且可執行的策略與
行動建議。本輪不更新網站，首頁維持「今天不下單」，不顯示實金比例或金額試算。

機器收據：

- protocol：`artifacts/short_term_volume_breakout_top10_nonoverlap_protocol_receipt.json`；
- validation：`artifacts/short_term_volume_breakout_top10_nonoverlap_validation.json`；
- multiplicity：Round62 family，全域下限至少 6314。

本報告只作研究及教育用途，不構成投資建議、Paper 成交或實金落盤指令。
