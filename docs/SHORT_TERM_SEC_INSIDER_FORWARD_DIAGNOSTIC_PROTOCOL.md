# SEC insider event 後瞻診斷協議

版本：v1

用途：研究候選的事件後表現，不建立投資組合、不授權 Paper。

## 固定輸入

- SEC 2026 Q2 Form 4／4-A as-filed ZIP，資料 cut 為 2026-06-30。
- 候選使用既有凍結規則：20 個 XNYS session、至少兩名不同 owner、合計名義金額
  至少 US$250,000；不因後瞻回報修改。
- Universe 為該 SEC ZIP 內所有有效 ticker；大型股 watchlist 不作候選池。
- 價格只接受外部明確提供的 long CSV，欄位為 ticker、日期、adjusted open、adjusted
  close；本輪 exploratory source 為 Yahoo Finance 下載快照，日期範圍 2026-04-01 至
  2026-07-31。adjusted open 必須在輸入建立時以同一 corporate-action factor 對齊；
  缺價不補值。下載客戶端及 CSV SHA-256 必須寫入收據。

## 固定時計及比較

- 事件可用時間是申報日後下一個 XNYS session。
- 在可用 session 開市以 adjusted open 進場，於第 5、10、20 個 session 的 adjusted
  close 離場。
- 每個事件列扣固定 20 bps round-trip 成本；同一日期、同一時計及同一成本計算 QQQ
  baseline。
- 事件列是 observation，不是資金配置；同一 issuer 的重疊事件不事後合併，也不把
  結果轉成 Top-K 或持倉名單。
- 主要期限事前固定為 20 sessions；5／10 sessions 只作預先指定的次要診斷。

## 統計及失敗處理

- 報告候選回報、QQQ 回報、配對超額、勝率及 moving-block bootstrap 95% 區間；block
  size 固定 8、seed 固定，沒有按結果選期限。
- 缺候選價格或 QQQ 價格的事件只計入 coverage 缺口，不估算、不前填、不回溯搜尋。
- Yahoo exploratory snapshot 不能通過正式 point-in-time／退市／公司行動閘門；所有
  結果標記 `post_hoc_diagnostic`，不進正式 readiness、Paper 或網站。

本協議及收據只回答「現有事件後觀察是否值得以合格資料重測」，不回答可否賺錢或應否
買入任何股票。
