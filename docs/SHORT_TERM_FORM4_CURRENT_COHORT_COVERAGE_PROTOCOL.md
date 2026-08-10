# 美股短線 Form 4 current-cohort 覆蓋診斷協議（Round 50）

FrozenAt：`2026-08-10T12:10:00Z`

狀態：**post-readout coverage diagnostic only。** Round49 已先證明三個固定 SEC 季度有
805 個 aggregate clusters；本輪只核對現有 30 檔大型股 watchlist 是否有足夠、近期且可對上
現時 SEC CIK 的 Form 4 事件，決定是否值得採購正式 point-in-time 證券主檔。這不是事前
alpha trial、不是正式回測、不是 Paper Trading（模擬交易），亦不授權實金落盤。

Round50 不修改 Round46 forward-only family、Round49 事件門檻或全域試驗帳本；不計任何市場
回報、不建立候選、不產生配置。結果只寫入研究 log；公開決策頁維持「只顯示已驗證成功策略，
否則今天不下單」。

## 1. 固定輸入

| 類別 | 固定來源 | SHA-256／限制 |
|---|---|---|
| 市場快照 | `artifacts/snapshot_20260731_6a7ca6b8.zip` | archive `d480fb82e712f06aabe0a98461e222344656b87022b8bda2cd7ccaa4c29ae88b`；panel `6a7ca6b83b1570007424daa46b0ff4e8fb4a655d39298a0f4f6d74c3b7ea3a66` |
| SEC CIK 對照 | SEC `https://www.sec.gov/files/company_tickers.json` | 2026-08-10 離線收據；只存 bytes／hash／映射數，不存原始列 |
| Form 4 | Round49 固定 `2006Q1`／`2016Q3`／`2026Q2` ZIP | 沿用 Round49 三份 SHA-256；不新增 SEC request |

快照的 30 檔股票 watchlist 由 repository 內事前既有的 `us_large_cap_watchlist_v1.csv` 定義，
不是從回報結果挑選；該 CSV SHA-256 為
`b6002e4e151bd298884f8cdd6272b5cbfde8aedca47cb58b92830d4d92028014`。ETF、VIX 及防守資產不列為個股 universe。SEC CIK 對照只是一個現時
識別診斷，不能代表歷史 ticker、主上市地、退市證券或 point-in-time mapping。

## 2. 固定覆蓋閘門

只計 Round49 parser 已通過的 primary cluster，並以 issuer CIK 對上 SEC 現時 mapping 及
watchlist 股票的集合；不得輸出 issuer、ticker、CIK、accession、日期或金額。診斷 gate 固定為：

1. 30 檔 watchlist 均有快照欄位；
2. 至少 30 個 mapped primary clusters；
3. 至少 10 個不同 mapped issuers；
4. `2016Q3` 及 `2026Q2` 兩個 recent anchor quarter 均至少有一個 mapped primary cluster；
5. CIK mapping 檔案每個 ticker／CIK 格式正確、ticker 唯一，且 mapping hash 與收據一致。

全部通過只代表「現時 watchlist 有足夠事件可作下一輪資料工程測試」，仍不授權回報計算。任一
不通過固定為 `current_cohort_coverage_failed_no_formal_backtest`。

## 3. 明確拒收事項

- 不使用現時 ticker 反推歷史 ticker，不用 today 成分填補歷史分母；
- 不以 adjusted OHLCV 冒充 raw open／close、公司行動或退市經濟；快照 metadata 已標示為
  `adjusted_ohlc`，故本輪即使事件量足夠也不能做正式 execution readout；
- 不因 CIK 對不上而換 ticker、刪除事件、改 watchlist 或重選季度；
- 不將 `P` 改稱純公開市場買入；不從人物知名度、新聞或社交媒體加權；
- 不把 2006Q1 的 survivor-only 對照結果外推至 20 年，亦不因 2016Q3／2026Q2 零事件而回填；
- 不產生 CAGR、Sharpe、最大跌幅、勝率、QQQ／SPY 差額、候選名單、Paper 或實金動作。

## 4. 輸出邊界

validation receipt 只可包含：來源 bytes／hash、watchlist／mapping／cluster aggregate counts、
各季度 aggregate counts、固定 gate pass/fail、limitations、`performance_present=false`、
`strategy_run_count=0`、`paper_authorized=false`、`real_money_action_usd=0` 及
`today_action="今天不下單"`。row-level identifier 只在 process memory 存在，結束後丟棄。

本輪的 current-cohort coverage 是 **survivorship-biased diagnostic**；即使 gate 通過，也必須
取得完整 point-in-time security master、歷史 mapping、退市／公司行動及 raw OHLCV 後，另立
新協議才可做正式個股回測。
