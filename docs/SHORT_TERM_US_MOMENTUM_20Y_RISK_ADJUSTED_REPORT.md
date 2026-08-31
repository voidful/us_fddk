# 美股短線 20 年風險調整動量研究報告

版本：v1｜狀態：`research_candidate_only`｜用途：單一機制診斷，並非買入名單、Paper 指令或投資建議。

## 結論先行

本輪只把 20 日回報除以當日 ATR20 作排名，其他訊號、QQQ regime、Top-7、D+1 開市、
20 日到期、gap filter、成本及 ETF 基準完全沿用母策略。結果不會改寫母策略或流入公開頁面。

- 風險調整版本接受 1531 宗訊號；10／25／50 bps CAGR 為 17.33%／14.34%／9.51%。
- 25 bps 母策略 CAGR 為 14.88%，QQQ 為 15.14%；本輪只作事後比較，不作參數選擇。
- 50 bps 前段策略／QQQ CAGR 為 4.68%／10.64%；後段為 14.28%／19.23%。

## 結果

| 成本 | 訊號 | 策略 CAGR | QQQ CAGR | SPY CAGR | IWM CAGR | 策略最大跌幅 | QQQ 最大跌幅 | Sharpe |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 10 bps | 1531 | 17.33% | 15.16% | 10.83% | 8.88% | -37.34% | -53.40% | 0.95 |
| 25 bps | 1531 | 14.34% | 15.14% | 10.82% | 8.86% | -40.97% | -53.40% | 0.81 |
| 50 bps | 1531 | 9.51% | 15.12% | 10.79% | 8.84% | -46.57% | -53.40% | 0.58 |

## 決策閘門

- 通過：3/6。
- 未通過：cagr_beats_qqq_at_25bps, cagr_beats_qqq_at_50bps, both_fixed_halves_beat_qqq_at_50bps。
- 年率化換手（25 bps）：17.17x。

所有結果只寫入研究 log；`Paper=false`、`public_strategy_allowed=false`、實金 US$0。
success-only 網頁維持「今天不下單」，不呈現本輪失敗結果或任何歷史最後權重。

機器收據：`artifacts/short_term_us_momentum_20y_risk_adjusted_diagnostic.json`；協議：
`docs/SHORT_TERM_US_MOMENTUM_20Y_RISK_ADJUSTED_PROTOCOL.md`。
