# 美股短線 20 年動量 ATR 出場研究報告

版本：v1｜狀態：`research_candidate_only`｜用途：出場機制診斷，並非買入名單、Paper 指令或投資建議。

## 結論先行

在同一 20 年 20／60 動量及 QQQ regime signal schedule 上加入止蝕 3×ATR、止賺 4×ATR
後，結果比原本 20-session time exit 更差：10／25／50 bps CAGR 只有 9.25%／4.06%／-4.07%，
均未跑贏 QQQ。本輪不升格，也不以止蝕／止賺結果改寫選股規則。

- ATR exit 全期訊號 1531 宗；stop／target／time exits 為 412／389／730。
- 50 bps 前段策略／QQQ CAGR 為 -5.98%／10.64%；後段為 -2.23%／19.23%。
- 原本 time exit 的 25 bps CAGR 為 14.88%，ATR exit 降至 4.06%。

## ATR 出場結果

| 成本 | 策略 CAGR | QQQ CAGR | SPY CAGR | IWM CAGR | 策略最大跌幅 | QQQ 最大跌幅 | 策略 Sharpe |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 10 bps | 9.25% | 15.16% | 10.83% | 8.88% | -38.34% | -53.40% | 0.54 |
| 25 bps | 4.06% | 15.14% | 10.82% | 8.86% | -43.88% | -53.40% | 0.30 |
| 50 bps | -4.07% | 15.12% | 10.79% | 8.84% | -74.84% | -53.40% | -0.11 |

## 決策閘門

- 通過：2/6。
- `cagr_beats_qqq_at_10bps, cagr_beats_qqq_at_25bps, cagr_beats_qqq_at_50bps, both_fixed_halves_beat_qqq_at_50bps` 未通過。
- ATR extension 年化換手 32.41x；高換手與 gap／資料邊界仍未納入正式 production accounting。

所有結果只寫入研究 log；`Paper=false`、`public_strategy_allowed=false`、實金 US$0。success-only 網頁維持「今天不下單」。

機器收據：`artifacts/short_term_us_momentum_20y_atr_exit_diagnostic.json`；協議：`docs/SHORT_TERM_US_MOMENTUM_20Y_ATR_EXIT_PROTOCOL.md`。
