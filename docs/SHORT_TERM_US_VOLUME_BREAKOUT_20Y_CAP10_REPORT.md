# 美股短線 20 年成交量突破最多 Top-10 研究報告

版本：v1｜狀態：`research_candidate_only`｜用途：source-aligned 機制診斷，並非買入名單、Paper 指令或投資建議。

## 結論先行

本輪允許 1–10 隻突破股，但要求至少 10 隻合資格基礎股票；沿用 60 日突破、1.5×20 日
成交量、SPY 60 日 regime、D+1 開市、20 日持有及 first-event-wins。這與上一輪
exact-Top10 變體分開記錄，不能合併解讀。

- 候選事件 376 宗；非重疊後接受 146 宗，265 個股票訊號。
- 10／25／50 bps 策略 CAGR 為 16.36%／14.10%／10.43%；QQQ 為 15.38%／15.37%／15.34%。
- 50 bps 前段策略／QQQ CAGR 為 9.03%／10.78%；後段為 11.89%／19.02%。

## 結果

| 成本 | 股票訊號 | 策略 CAGR | QQQ CAGR | SPY CAGR | IWM CAGR | 策略最大跌幅 | QQQ 最大跌幅 | Sharpe |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 10 bps | 265 | 16.36% | 15.38% | 10.90% | 9.29% | -45.25% | -53.40% | 0.80 |
| 25 bps | 265 | 14.10% | 15.37% | 10.89% | 9.27% | -47.63% | -53.40% | 0.71 |
| 50 bps | 265 | 10.43% | 15.34% | 10.86% | 9.25% | -51.38% | -53.40% | 0.56 |

## 決策閘門

- 通過：3/6。
- 未通過：cagr_beats_qqq_at_25bps, cagr_beats_qqq_at_50bps, both_fixed_halves_beat_qqq_at_50bps。
- 年率化換手（25 bps）：13.01x。

所有結果只寫入研究 log；`Paper=false`、`public_strategy_allowed=false`、實金 US$0。
success-only 網頁維持「今天不下單」，不呈現本輪結果或歷史最後權重。

機器收據：`artifacts/short_term_us_volume_breakout_20y_cap10_diagnostic.json`；協議：
`docs/SHORT_TERM_US_VOLUME_BREAKOUT_20Y_CAP10_PROTOCOL.md`。
