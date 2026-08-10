# 美股短線 Form 4 同期買入事件診斷報告（Round 53）

版本：1.0
研究快照截至：2026-07-31
狀態：**負面診斷；不建立 Paper；實金動作 US$0；今天不下單。**

## 結論

事前凍結的「同一 issuer、同一披露日最少 2 個合資格 Form 4 purchase accession，合計
reported notional 至少 US$100,000」事件，在 82 季 SEC Form 4 aggregate coverage 中得到
45 宗完整事件。主要 10-session 結果沒有跑贏同日 eligible current-cohort 等權池：

| 指標 | 10-session 結果 |
| --- | ---: |
| 事件回報（扣來回 20 bps） | 0.862% |
| eligible-pool 等權回報 | 0.982% |
| 配對差 | -0.119 個百分點 |
| Newey–West t | -0.09 |
| moving-block bootstrap 95% 下界 | -2.210 個百分點 |
| 配對勝率 | 46.7% |
| 前／後固定段配對差 | +0.467 / -0.789 個百分點 |

事前 6 項 gate 只通過 **1/6**（事件數量門檻）。5-session 的平均差雖為正，20-session
則進一步落後；兩者都不能補救主要 horizon 的統計及前後段失敗。結果固定為
`form4_event_diagnostic_negative_survivorship_biased`，不調整 cluster 門檻、持有期、成本或
mapping 來救援。

## 覆蓋與 baseline

- 82/82 個 SEC 季度檔案、Round52 source manifest 及固定 anchor bytes 全部通過。
- Round52 的 current-watchlist mapping union 有 664 個 purchase accessions；按本輪
  deterministic mapping 聚合成 45 宗事件。
- 事件與 current complete cohort、同日 eligible pool、SPY、QQQ 使用同一 entry／exit
  session 及成本口徑。10-session 的事件平均回報為 0.862%，QQQ 為 0.195%，SPY 為 -0.047%；
  但這些是 event-level adjusted-price 統計，不是資金曲線或可落盤回報。

## 不能升格為交易策略的原因

1. watchlist 是現時 30 檔大型股倒推，帶 survivorship bias；current CIK 不是歷史 security
   master。
2. Form 4 filing date 沒有可稽核的盤中公開 timestamp；本輪採一個完整 XNYS session lag，
   仍不能證明當時可成交。
3. 行情為 adjusted OHLCV，沒有 raw execution、退市／收購回報及完整公司行動賬本。
4. 事件研究保留重疊事件，沒有建立投資組合、換手資金曲線或真實成交紀錄。

## 決策

本輪結果只寫入研究 log 和機器收據，不進入網站首頁、不產生個股名單、不顯示持倉比例、
不建立 Paper，實金 action 保持 US$0。網站繼續只展示已驗證、可執行的成功策略；目前仍為
「今天不下單」。下一個可接受步驟仍是取得具發布日的 point-in-time 成分、退市回報、raw
execution 及公司行動資料，再按本協議原樣重測。

機器收據：

- protocol：`artifacts/short_term_form4_event_diagnostic_protocol_receipt.json`；
- validation：`artifacts/short_term_form4_event_diagnostic_validation.json`；
- report：本文件。

本報告只作研究及教育用途，不構成投資建議、Paper 成交或實金落盤指令。
