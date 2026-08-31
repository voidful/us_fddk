# SEC insider 多季事件診斷協議

版本：v1；用途：研究穩健性，不建立投資組合。

## 事前固定範圍

- SEC 345 quarterly packages 固定為 2024 Q1、Q2、Q3、Q4、2025 Q1、Q2、Q3、Q4、
  2026 Q1、Q2；不可因結果刪除季度或改起訖日期。
- 每季使用該季末前已知的累積事件，候選規則仍固定為 20 個 XNYS sessions、至少兩名
  不同 owner、合計名義金額至少 US$250,000。
- 事件可用時間仍是申報日後下一個 XNYS session；候選只按 filing signal date 歸入
  所在季度，20-session cluster 可跨季。
- Universe 為 SEC package 內所有有效 ticker，不使用今日大型股清單作歷史成分。

## 事前固定表現時計

- 使用同一份外部價格 snapshot，涵蓋 2024-01-01 至 2026-07-31；adjusted open 進場、
  第 5／10／20 個 XNYS session adjusted close 離場，扣 20 bps round-trip。
- QQQ 於同一日期、同一持有期及同一成本作 baseline。
- 主要期限固定為 20 sessions；5／10 只作固定次要診斷。
- 報告全期、固定前半（2024Q1–2025Q1）、固定後半（2025Q2–2026Q2）及每季結果；
  不用任何分段結果重新選參數。

## 完整性及 promotion 邊界

- 每份 SEC package 的 URL、檔名、SHA-256、as-of 及解析數量寫入收據；重複事件 key
  若內容衝突即 fail closed，完全相同才只保留一列。
- 價格缺口只報 coverage，不填值、不以仍存公司替代退市樣本。
- SEC as-filed 事件加 Yahoo exploratory 價格不能通過正式 point-in-time／退市／公司
  行動閘門；即使跨季超額為正，也不進 Paper、網站或實金。

本協議只回答「是否值得用合格資料重測」，不構成買入建議或盈利保證。
