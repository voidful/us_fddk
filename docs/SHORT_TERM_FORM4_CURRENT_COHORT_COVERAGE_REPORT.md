# 美股短線 Form 4 current-cohort 覆蓋診斷報表（Round 50）

稽核日：`2026-08-10`　｜　狀態：**覆蓋不足；不進行正式回測**

## 結論

把已封存 20 年 adjusted OHLCV 快照的 30 檔現時大型股 watchlist，與 SEC 現時
`company_tickers.json` CIK 對照及 Round49 三季 Form 4 aggregate clusters 交叉核對後，只有
**2 個 mapped primary clusters、1 個 mapped issuer，且 2016Q3／2026Q2 兩個 recent anchor
quarter 都是 0**。事前固定的覆蓋門檻為 30 clusters、10 issuers、兩個 recent quarters
均有事件；三項均未通過。

因此本輪固定為 `current_cohort_coverage_failed_no_formal_backtest`，沒有把現時股票名單
包裝成短線策略，沒有計 CAGR／Sharpe／回撤，沒有 QQQ／SPY 比較，亦沒有 Paper 或實金動作。
網站仍只顯示成功可行策略；目前沒有新的可公開行動，維持「今天不下單」。

## Aggregate 結果

| 季度 | 全部 primary clusters | mapped primary clusters | mapped issuers |
|---|---:|---:|---:|
| 2006Q1 | 267 | 2 | 1 |
| 2016Q3 | 239 | 0 | 0 |
| 2026Q2 | 299 | 0 | 0 |
| **合計** | **805** | **2** | **1** |

快照包含 5,680 個交易日及 30 檔 watchlist 股票；現時 CIK 對照可對上 30 個 watchlist ticker，
但兩個 ticker 可能屬同一 issuer，故 unique issuer 仍只有 1。這個 mapping 是現時對照，
不是歷史 ticker、上市地、成分公布時間或 known-at 證據。

## 為何不能以這個結果回測

- watchlist 是現時 survivor cohort，不是 point-in-time 成分分母；
- snapshot metadata 明確是 adjusted OHLCV，不是可核對的 raw open／close execution data；
- 沒有退市、收購、公司行動及歷史 security-master outcome ledger；
- Form 4 的 `P` 仍可能是公開市場或私人購買，不能直接當成純公開市場買入；
- SEC Insider Transactions 資料是 quarterly、as-filed 的 Forms 3／4／5 flattened data，SEC
  亦提醒資料可能有申報或抽取錯誤，不能替代完整 EDGAR filing。[SEC 資料集](https://www.sec.gov/data-research/sec-markets-data/insider-transactions-data-sets)、[SEC 資料字典](https://www.sec.gov/files/insider_transactions_readme.pdf)

## 下一個真正可行的研究步驟

只有取得合法、owner-only 的 point-in-time security master、歷史 ticker／CIK mapping、raw
OHLCV、退市及公司行動賬本後，才另立新協議重跑；本輪不以 CIK 現時對照補洞，也不修改
Round46 forward-only 或 Round49 事件率結果。

機器收據：[short_term_form4_current_cohort_coverage_validation.json](../artifacts/short_term_form4_current_cohort_coverage_validation.json)
