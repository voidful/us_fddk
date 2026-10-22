# SEC XBRL 盈利事件＋60／20 趨勢確認研究協議

版本：v1；用途：短線個股研究診斷，不授權 Paper 或公開策略。

## 研究問題

在已凍結的 SEC XBRL 正 EPS／營收同比事件上，加入一條公開可觀察的價格趨勢確認，是否
能減少事件後的弱勢交易，並在相同持有期、成本及 ETF 基準下改善結果。這是參考台股
研究中「事件／動能／趨勢共振」的美股假說；台股回報不被當作美股證據。

本輪是既有 XBRL v1 diagnostic 的事後固定 extension，不是獨立首次發現，也不得以結果
改動 XBRL 事件、持有期、成本、watchlist 或趨勢窗口。

## 凍結輸入與可知時鐘

- 事件串流只讀取 `artifacts/short_term_sec_xbrl_earnings_diagnostic.json` 的 `events`；
  parent artifact 的 SHA-256 及事件數必須核對。parent 必須仍是
  `post_hoc_sec_xbrl_earnings_event_diagnostic` 且未准許公開策略。
- 價格及流動性 CSV 的 SHA-256 必須與 parent 收據相同；任何來源漂移即停止，不補值。
- 事件的可用日是 filing date 後第一個 XNYS session；趨勢只使用該入場日前的 60 個
  XNYS sessions，入場日價格不得參與篩選。
- 60-session adjusted-close simple moving average：入場前一日收市價必須嚴格高於均線。
- 20-session momentum：入場前一日收市價相對 20 sessions 前收市價必須嚴格為正。
- 缺少完整 60-session 價格歷史即拒收；不使用 filing 後任何價格形成訊號。

## 組合、成本及比較

- 延用 parent：每個 ticker 第一個未重疊事件、持有 20 個 XNYS sessions、active ticker
  等權、入場 adjusted open，之後 close-to-close，到期日收市後離場。
- 單邊成本固定為 10／25／50 bps；QQQ、SPY、IWM 使用相同評估時段及同一成本口徑。
- 報告全期，以及事前固定的 filing date 前半段 `2023-01-01..2024-12-31`、後半段
  `2025-01-01..2026-06-30`；不因結果更換分段或窗口。
- 指標包括接受事件數、CAGR、總回報、Sharpe、最大跌幅、年化換手及成本壓力；結果是
  adjusted-price 研究會計，不是券商可執行帳本。

## 升格邊界

即使結果為正，parent 仍使用現時大型股觀察池及 exploratory adjusted OHLCV，缺少
point-in-time 成分、退市／收購回報、完整公司行動及正式 risk-free package。因此本輪
固定 `research_candidate_only`；失敗與 skip reason 只寫入研究 log／機器收據，不建立
Paper、不產生個股買入名單、不改寫 success-only 網頁。
