# 美股短線 20 年成交量突破研究報告

版本：v1｜狀態：`research_candidate_only`｜用途：固定突破機制診斷，並非買入名單、Paper 指令或投資建議。

## 結論先行

本輪固定測試 60 日收市突破、1.5×20 日成交量、SPY 60 日 regime 及 Top-10；每週
下一個開市入場、20 日後離場，上一宗未完成前跳過新訊號。沒有加入止蝕、止賺或事後調參。

- 候選事件 1 宗，非重疊後接受 1 宗（10 個股票訊號）。
- 10／25／50 bps 策略 CAGR 為 199.50%／188.74%／171.63%；QQQ 對應 89.44%／82.64%／71.81%。
- 50 bps 前段策略／QQQ CAGR 為 0.00%／0.00%；後段為 171.63%／71.81%。

## 結果

| 成本 | 股票訊號 | 策略 CAGR | QQQ CAGR | SPY CAGR | IWM CAGR | 策略最大跌幅 | QQQ 最大跌幅 | Sharpe |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 10 bps | 10 | 199.50% | 89.44% | 40.39% | 7.46% | -1.63% | -0.92% | 7.94 |
| 25 bps | 10 | 188.74% | 82.64% | 35.35% | 3.60% | -1.63% | -0.92% | 7.64 |
| 50 bps | 10 | 171.63% | 71.81% | 27.33% | -2.54% | -1.63% | -0.92% | 7.11 |

## 決策閘門

- 通過：3/6。
- 未通過：minimum_30_accepted_events, both_fixed_halves_beat_qqq_at_50bps, max_drawdown_no_worse_than_qqq_at_10bps。
- 年率化換手（25 bps）：12.60x。

所有結果只寫入研究 log；`Paper=false`、`public_strategy_allowed=false`、實金 US$0。
success-only 網頁維持「今天不下單」，不呈現本輪失敗結果或歷史最後權重。

機器收據：`artifacts/short_term_us_volume_breakout_20y_diagnostic.json`；協議：
`docs/SHORT_TERM_US_VOLUME_BREAKOUT_20Y_PROTOCOL.md`。
