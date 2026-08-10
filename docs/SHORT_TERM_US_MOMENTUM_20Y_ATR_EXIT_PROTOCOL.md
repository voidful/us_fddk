# 美股短線 20 年動量 ATR 出場診斷協議

版本：v1；用途：既有 20 年動量 schedule 的出場機制診斷，不授權 Paper、公開策略或實金交易。

本輪不重選股票、分數、regime、Top-7 或持有窗口；只在
`artifacts/short_term_us_momentum_20y_diagnostic.json` 的同一 accepted signal schedule 上，
固定加入參考專案的 ATR 出場：止蝕 3×ATR、止賺 4×ATR、最長 20 sessions。

## 出場時計及成本

- 入場仍為 signal close 後下一 XNYS open；止蝕／止賺價以入場 adjusted open 加減 signal-day
  ATR20 計算。
- 當日 high／low 同時觸及止蝕及止賺時，採最不利的止蝕先成交；只有 high 或 low 觸價才提早
  離場，否則於原定 20-session 到期日收市離場。
- 既有 20-session schedule 的部位槽位固定至原定到期日；ATR 提前離場後不補開新倉，避免
  以事後 stop 結果改寫選股時鐘。這是保守的機制隔離，不是完整 production execution。
- 單邊成本固定 10／25／50 bps；以每日 target-weight 變動及最後清倉扣除成本；QQQ、SPY、IWM
  仍用同一評估窗及成本。

## 評估及邊界

- 全期及固定 2004–2014、2015–2026H1 兩段均沿用 parent schedule；報告比較 time-exit parent
  與 ATR-exit extension，並列 stop／target／time exit 次數、年化換手、CAGR、Sharpe、最大跌幅。
- 這是 post-hoc mechanism extension；snapshot 是現時大型股池，缺少 point-in-time 成分、
  退市／收購回報、完整公司行動、sector 歷史及正式 risk-free package。
- 即使 ATR 出場改善回撤，也不能升格；本輪固定 `research_candidate_only`、
  `paper_authorized=false`、`public_strategy_allowed=false`、實金 US$0，失敗只寫入內部 log，
  success-only 網頁維持「今天不下單」。
