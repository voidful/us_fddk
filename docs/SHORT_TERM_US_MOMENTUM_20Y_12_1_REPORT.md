# 美股短線 20 年 12–1 月動量研究報告

版本：v1｜狀態：`research_candidate_only`｜用途：單一回顧期診斷，並非買入名單、Paper 指令或投資建議。

## 結論先行

本輪固定排除最近 21 個 session，以 D-252 至 D-21 的回報作橫斷面排名，沿用 60 日
趨勢、QQQ regime、Top-7、D+1 open、20 日持有、gap audit 及成本。結果沒有因為
低換手假說而改寫門檻。

- regime 版本接受 1190 宗股票訊號；10／25／50 bps CAGR 為 9.05%／6.42%／2.16%。
- QQQ 對應 CAGR 為 15.65%／15.63%／15.60%；25 bps 年化換手 16.24x。
- 50 bps 前段策略／QQQ CAGR 為 1.65%／11.54%；後段為 2.60%／18.98%。

## 結果

| 成本 | 訊號 | 策略 CAGR | QQQ CAGR | SPY CAGR | IWM CAGR | 策略最大跌幅 | QQQ 最大跌幅 | Sharpe |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 10 bps | 1190 | 9.05% | 15.65% | 11.04% | 9.14% | -47.45% | -53.40% | 0.53 |
| 25 bps | 1190 | 6.42% | 15.63% | 11.03% | 9.12% | -47.61% | -53.40% | 0.41 |
| 50 bps | 1190 | 2.16% | 15.60% | 11.00% | 9.10% | -52.91% | -53.40% | 0.21 |

## 決策閘門

- 通過：2/6。
- 未通過：cagr_beats_qqq_at_10bps, cagr_beats_qqq_at_25bps, cagr_beats_qqq_at_50bps, both_fixed_halves_beat_qqq_at_50bps。

所有結果只寫入研究 log；`Paper=false`、`public_strategy_allowed=false`、實金 US$0。
success-only 網頁維持「今天不下單」，不呈現本輪結果或歷史最後權重。

機器收據：`artifacts/short_term_us_momentum_20y_12_1_diagnostic.json`；協議：
`docs/SHORT_TERM_US_MOMENTUM_20Y_12_1_PROTOCOL.md`。
