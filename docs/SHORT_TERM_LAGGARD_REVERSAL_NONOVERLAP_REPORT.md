# 美股短線落後反轉單一帳戶 non-overlap 資金會計報告（Round 60）

版本：1.0
研究快照截至：2026-07-31
狀態：**負面資金會計診斷（3/7 gate）；不建立策略、不建立 Paper；實金動作 US$0；今天不下單。**

## 結論

Round 59 的事件平均結果不能直接當作可交易回報。本輪把同一個「無市場濾網、五日落後、
最弱 Top-5、20-session」訊號放進 US$1,000 單一帳戶；一次只持有一宗，持倉期間忽略所有
重疊訊號，離場後才重新掃描。747 個候選事件最後只有 **123 宗 accepted trades**，624 宗
因重疊被跳過。

Top-5 資金曲線 final equity 為 **US$5,734.25**、CAGR **9.14%**，但最大回撤 **−62.61%**。
它雖然略勝同一 accepted schedule 的 eligible pool（CAGR 8.94%），卻同時落後 passive SPY
（11.29%）及 QQQ（16.70%），而且回撤比兩者更深；七項 capital gate 只通過 **3/7**。

| 資金曲線 | Final equity | CAGR | 最大回撤 | 零利率 Sharpe | 持倉比例 |
| --- | ---: | ---: | ---: | ---: | ---: |
| Top-5 selected | US$5,734 | 9.14% | **−62.61%** | 0.46 | 51.3% |
| eligible pool（同期 schedule） | US$5,523 | 8.94% | −34.23% | 0.55 | 51.3% |
| complete cohort（同期 schedule） | US$6,284 | 9.64% | −37.94% | 0.57 | 51.3% |
| SPY（同期 schedule） | US$2,372 | 4.42% | −39.89% | 0.34 | 51.3% |
| QQQ（同期 schedule） | US$3,584 | 6.60% | −36.86% | 0.43 | 51.3% |
| SPY（全期 buy-and-hold） | US$8,455 | **11.29%** | −55.19% | 0.65 | 100% |
| QQQ（全期 buy-and-hold） | US$21,839 | **16.70%** | −53.40% | 0.81 | 100% |

所有曲線使用相同 2006-08-01 至 2026-07-31 快照、下一開盤成交、20-session 離場及 20 bps
round-trip 成本；passive 基準也扣一次 round-trip 成本。這是 adjusted OHLCV 的研究會計，
不是 broker 可執行的成交賬本。

## Gate 及解讀

通過項目只有：至少 30 宗 accepted events、final equity 高於起始、CAGR 高於同期 eligible
pool。失敗項目為：CAGR 不高於 SPY、CAGR 不高於 QQQ、最大回撤不及 SPY、最大回撤不及 QQQ。

這個結果比重疊事件的正平均更接近真正資金風險：集中 Top-5 令回撤比 eligible pool 深約
28 個百分點，且長期機會成本輸給 QQQ。它不支持把 Round 57–59 的落後反轉診斷升格為短線
交易策略。

## 研究邊界

- 目前 30 檔 watchlist 是現時 survivor cohort，沒有 point-in-time 成分、退市／收購經濟及
  歷史 ticker mapping。
- adjusted OHLCV 不等於 raw execution；fractional equal-weight 只是研究約定。
- post-hoc 資金會計不是獨立首次證據；沒有建立 strategy run、Paper account、個別標的名單
  或實金落盤。

結果只寫入研究 log 和機器收據；公開頁面只接受已驗證可行策略，目前仍顯示「今天不下單」。

機器收據：

- protocol：`artifacts/short_term_laggard_reversal_nonoverlap_protocol_receipt.json`；
- validation：`artifacts/short_term_laggard_reversal_nonoverlap_validation.json`；
- multiplicity：Round60 family，全域下限 6312。

本報告只作研究及教育用途，不構成投資建議、Paper 成交或實金落盤指令。
