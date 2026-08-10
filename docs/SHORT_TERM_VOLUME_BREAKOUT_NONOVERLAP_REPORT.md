# 美股短線成交量突破單一帳戶資金會計報告（Round 61）

版本：1.0  
研究快照截至：2026-07-31  
狀態：**負面資金會計診斷（5/7 gate）；只寫研究 log；不建立策略、不建立 Paper；實金動作 US$0；今天不下單。**

## 結論

Round 54 的成交量確認突破在事件層面接近門檻。本輪不改訊號或參數，將相同規則放進
US$1,000 單一帳戶：每次只持有一宗、持倉 20 個交易日、重疊訊號跳過、round-trip 成本
20 bps。403 宗候選事件中，146 宗可按固定規則接受，257 宗因持倉重疊跳過。

Top-5 資金曲線 final equity 為 **US$16,489.57**、CAGR **15.07%**、零利率 Sharpe
**0.70**，最大回撤 **−54.99%**，持倉比例 **60.94%**。結果優於同一 accepted schedule
的 eligible pool 及 passive SPY，但仍落後 passive QQQ，且最大回撤比 QQQ 更深；七項
capital gate 只通過 **5/7**，所以不稱為可行策略。

| 資金曲線 | Final equity | CAGR | 最大回撤 | 零利率 Sharpe | 事件／持倉比例 |
| --- | ---: | ---: | ---: | ---: | ---: |
| Top-5 selected | US$16,490 | **15.07%** | −54.99% | 0.70 | 146 / 60.94% |
| eligible pool（同期 schedule） | US$4,855 | 8.24% | −50.73% | 0.61 | 146 / 60.94% |
| complete cohort（同期 schedule） | US$5,992 | 9.38% | −49.08% | 0.67 | 146 / 60.94% |
| SPY（同期 schedule） | US$1,314 | 1.38% | −53.56% | 0.17 | 146 / 60.94% |
| QQQ（同期 schedule） | US$2,768 | 5.23% | −48.25% | 0.41 | 146 / 60.94% |
| SPY（全期 buy-and-hold） | US$8,455 | 11.29% | −55.19% | 0.65 | 1 / 100% |
| QQQ（全期 buy-and-hold） | US$21,839 | **16.70%** | −53.40% | 0.81 | 1 / 100% |

所有曲線使用 2006-08-01 至 2026-07-31 的固定快照、已完成 XNYS session、下一交易日
adjusted open、20 個交易日後 adjusted close，以及 20 bps round-trip 成本。這是
adjusted OHLCV 的研究資金會計，不是券商可執行成交賬本。

## Gate 解讀

通過：至少 30 宗 accepted events、final equity 高於起始、CAGR 高於同期 eligible pool、
CAGR 高於 passive SPY、最大回撤不深於 passive SPY。  
失敗：CAGR 不高於 passive QQQ、最大回撤不及 passive QQQ。

因此它是目前最接近的個股候選之一，但尚未證明能以可接受風險跑贏 QQQ；Round 54 的
事件平均回報不能替代單一帳戶資金曲線。

## 研究邊界及公開面

- 現時 30 檔 watchlist 是 survivor cohort，沒有 point-in-time 成分、退市／收購經濟及
  歷史 ticker mapping。
- adjusted OHLCV 不等於 raw execution；成交量沒有盤中公開時間戳；fractional equal-weight
  只是研究約定。
- 本輪是 post-hoc 資金會計，並非獨立首次證據；沒有 strategy run、Paper account、
  個別標的名單或實金落盤。

失敗 gate、限制及負面結果只保留在研究 log／機器收據；公開網站只呈現已通過全部必要
驗證且可執行的策略與行動建議。本輪不更新網站，首頁維持「今天不下單」，不顯示實金比例
或金額試算。

機器收據：

- protocol：`artifacts/short_term_volume_breakout_nonoverlap_protocol_receipt.json`；
- validation：`artifacts/short_term_volume_breakout_nonoverlap_validation.json`；
- multiplicity：Round61 family，全域下限至少 6313。

本報告只作研究及教育用途，不構成投資建議、Paper 成交或實金落盤指令。
