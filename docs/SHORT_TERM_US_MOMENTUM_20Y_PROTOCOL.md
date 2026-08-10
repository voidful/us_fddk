# 美股短線 20 年 20／60 動量研究協議

版本：v1；用途：長樣本短線個股診斷，不授權 Paper、公開策略或實金交易。

本輪把前一輪 20／60 橫斷面動量規則套用到凍結的 2004-01-02..2026-07-31 調整 OHLCV
快照，並加入參考專案的可執行 gap／ATR 入場檢查。這是對既有結果的延伸，不是重新選參數
或獨立首次發現。

## 凍結輸入及 universe

- 只接受 `artifacts/snapshot_20260731_6a7ca6b8.zip`；archive SHA-256、manifest 檔案雜湊
  及 panel SHA-256 必須核對，資料漂移即停止。
- 股票池是快照中 30 檔個股；排除 QQQ、SPY、IWM、DBC、EEM、EFA、GLD、IEF、SHY、TLT、VNQ
  及 `^VIX`。這是現時 watchlist，不是 point-in-time 成分池。
- 股票的 adjusted OHLC 由同一快照提供；dollar volume 以 adjusted close × volume 作流動性
  proxy，非券商成交帳本。

## 訊號及執行

- 每個完整 XNYS session 收市後計算 20-session momentum 及 `close / 60-session SMA - 1`，
  在股票池內做 percentile rank：`score = 3 × rank(momentum) + rank(trend)`。
- 只保留 score ≥ 2.0、momentum > 0、trend > 0；每個 signal close 後下一 session open
  入場，等權、最多七檔、持有 20 sessions 強制離場。
- QQQ regime gate 固定為 signal close 高於 QQQ 20-session 及 60-session SMA；同時保留不加
  gate 的 control。
- 20-session ATR 用 adjusted high／low 及前一日 adjusted close 計算。下一 open 的絕對 gap
  若 ≥ 1.5 × signal-day ATR，於該 open 放棄入場；這是執行時已知的條件，不是用收市後未來
  close 篩選。未加入停損／停利，避免把資料不足的 ATR 出場假設混入本輪 baseline。
- 入場前 20 sessions 中位數 dollar volume ≥ US$20m、股價 ≥ US$5；缺資料或持有期不足拒收。

## 成本、基準及分段

- 單邊成本固定 10／25／50 bps；QQQ、SPY、IWM 用相同持有期間及成本口徑作 passive baseline。
- 全期及事前固定分段：2004-01-01..2014-12-31、2015-01-01..2026-06-30；分段只作診斷，
  不回頭挑選參數。
- 指標包括 CAGR、總回報、Sharpe、最大跌幅、年化換手、平均持倉、gap skip 及控制組差異。

## 升格邊界

現時大型股池存在 survivor bias；ABBV、META 等歷史覆蓋亦不完整，且沒有逐期成分、退市／收購
回報、完整公司行動、sector 歷史及正式 risk-free package。因此即使 20 年描述性 CAGR 跑贏
ETF，仍固定 `research_candidate_only`、`paper_authorized=false`、`public_strategy_allowed=false`、
實金 US$0。結果只寫入內部研究 log／機器收據，success-only 網頁維持「今天不下單」。
