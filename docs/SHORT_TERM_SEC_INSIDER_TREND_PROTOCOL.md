# SEC insider cluster + trend 共振研究協議

版本：v1；用途：研究假說診斷，不授權 Paper 或公開策略。

## 研究問題

在已固定的 SEC insider cluster 及可交易性規則上，加入一條事前指定的價格趨勢共振
是否能減少弱勢事件、並在同一持有期及成本下改善相對 QQQ 的結果。這是台股參考專案
所用 20／60 日趨勢結構的美股研究假說，不把台股回報當作美股證據。

## 固定輸入與成交時計

- SEC 輸入固定為 2024Q1 至 2026Q2 十個 quarterly packages，以及既有
  20-XNYS-session、至少兩名 owner、名義金額至少 US$250,000 的 cluster 規則。
- 基礎可交易性 filter 不變：入場前 20 個 XNYS sessions 的 median dollar volume
  至少 US$20m，入場前一日收市價至少 US$5；任何缺口只寫入 skip log。
- 候選可用時間是 filing 後下一個 XNYS session；只用該 session 以前的價格。
- 新增 trend gate 只使用入場前 60 個 XNYS sessions：
  1. 入場前一日 adjusted close 高於該 60-session adjusted-close simple moving average；
  2. 入場前一日相對 20 sessions 前 adjusted close 的總回報嚴格為正。
- 缺少完整 60-session 價格歷史即拒收；入場日價格不得參與 gate。
- 每個 issuer 只接受第一個未重疊訊號，持有 20 個 XNYS sessions，active issuers 等權；
  入場日 adjusted open，之後 close-to-close，到期日收市後離場。

## 固定比較與壓力

- 單邊成本固定為 10、25、50 bps；不因結果調整。
- QQQ、SPY、IWM 使用相同 evaluation period、相同 open／close 時計及同一成本情境；
  即單邊 10／25／50 bps 對應 20／50／100 bps round-trip baseline 成本。
- 報告全期及事前固定前五季／後五季、CAGR、total return、Sharpe、最大回撤及年化
  turnover；不以任一結果選擇子時段或股票。

## 升格邊界

這條線使用 exploratory Yahoo 價格，沒有 point-in-time 成分、退市／收購回報、完整
公司行動或正式 risk-free package，因此無論結果正負都維持 `research_candidate_only`。
任何未通過流動性、成本或固定分段比較的結果只保留在機器收據及研究 log；不建立 Paper、
不產生個股名單、不改寫公開 success-only 網頁。
