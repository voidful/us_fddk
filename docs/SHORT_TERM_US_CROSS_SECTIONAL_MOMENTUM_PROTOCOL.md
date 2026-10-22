# 美股短線 20／60 橫斷面動量研究協議

版本：v1；用途：短線個股研究診斷，不授權 Paper、公開策略或實金交易。本輪在先行 smoke
重播後才封存協議，故標記為 post-hoc extension，不是獨立首次發現。

## 研究問題

把參考台股研究中的「20 日動量 × 3＋60 日趨勢 × 1、流動性池、Top-7、20 個交易日
持有」固定翻譯到美股現時大型股觀察池，並測試 QQQ 20／60 日 regime gate 是否只
改善回撤，還是只在最近市場片段有效。這是機制診斷，不是把台股回測當成美股證據。

## 凍結規則與可知時鐘

- 股票池只用輸入價格／流動性 CSV 中的 29 檔個股；排除 QQQ、SPY、IWM 基準。
- 每個完整 XNYS session 收市後計算個股：20-session adjusted-close momentum，及
  `close / 60-session SMA - 1` 趨勢距離。兩者在當日股票池內做 percentile rank：
  `score = 3 × rank(momentum) + rank(trend)`。
- 只保留 `score >= 2.0`、momentum > 0、trend > 0 的候選；每個 signal close 後，
  下一個 XNYS session adjusted open 入場；等權、最多七個同時持倉；每檔持有 20 sessions。
- 每個新入場日先移除已到期部位；容量不足才按 score 由高至低填入。訊號日資料不得
  使用下一日 open／close。
- 固定 QQQ regime gate：signal close 必須高於 QQQ 的 20-session 及 60-session
  adjusted-close SMA；另保留完全相同規則但不加 gate 的 control。
- 每檔入場前價格至少 US$5，前 20 sessions 中位數 dollar volume 至少 US$20m；
  缺價／缺流動性／持有期不足即拒收，不補值。

## 成本、基準及分段

- 單邊成本固定 10／25／50 bps；QQQ、SPY、IWM 以同一 signal schedule 的評估窗
  做買入並持有基準。
- 報告全期及事前固定兩段：2023-01-01..2024-12-31、2025-01-01..2026-06-30。
- 指標包括接受訊號數、CAGR、總回報、Sharpe、最大跌幅、年化換手、平均持倉數及
  regime control 差異。

## 資料限制與升格邊界

輸入是現時大型股觀察池及 exploratory adjusted OHLCV，不是 point-in-time 成分池；
沒有退市／收購回報、完整公司行動、逐股 sector 歷史、high／low ATR 或正式 risk-free
package。因此即使描述性結果跑贏 ETF，本輪仍固定 `research_candidate_only`、
`paper_authorized=false`、`public_strategy_allowed=false`、實金 US$0；所有失敗與
skip reason 只寫入研究 log／機器收據，success-only 網頁不接收輸出。
