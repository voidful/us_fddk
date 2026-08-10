# SEC insider equal-weight event portfolio 協議

版本：v1；用途：研究可實作性，不授權 Paper。

## 固定規則

- 候選沿用十季研究的 20-XNYS-session、兩名 owner、US$250,000 cluster 規則。
- 每個 issuer 只接受第一個未重疊訊號；持倉固定 20 個 XNYS sessions，期間不加碼、不
  止蝕、不止賺、不槓桿。
- 每個交易日開市後，所有 active issuer 等權；新訊號及到期訊號按目標權重調整。沒有
  active issuer 時持有現金。這不是 Top-K 搜尋，亦不按回報排序救援。
- 只納入有完整 20-session adjusted open／close 價格的訊號；缺價、缺 session 或不足
  20 日的訊號只計入 skip log，不補值、不以前後 ticker 代替。
- 入場日 adjusted open；入場日用 open-to-close，之後用 close-to-close；到期日收市後
  離場。成本情境事前固定為單邊 10 bps（主要）、25 bps 及 50 bps（壓力測試）；同一
  批訊號、持倉及期間全部重用，不按成本結果重新選擇。
- QQQ、SPY、IWM 在相同 portfolio evaluation period 以 adjusted open 進場、末日收市
  離場，同樣扣 20 bps；三者均事前固定，QQQ 仍是主要高回報 baseline。

## 評估

- 報告 total return、CAGR、Sharpe、最大回撤、平均 active positions 及年化 turnover。
- 全期及事前固定前五季／後五季分段各自由現金起步；分段邊界不由結果修改。
- 任何缺少 point-in-time 成分、退市／收購回報、公司行動或正式 risk-free package 的
  結果，均維持 `research_candidate_only`，不得建立 Paper、網站策略或實金指令。

這個協議用來檢查事件平均超額能否落地成組合，不是盈利承諾或投資建議。
