# 美股短線 20／60 橫斷面動量研究報告

版本：v1｜狀態：`research_candidate_only`｜用途：研究診斷，並非買入名單、Paper 指令或投資建議。

## 結論先行

20 日動量 ×3、60 日趨勢 ×1、Top-7、20 sessions，加上 QQQ 20／60 regime gate，
全期描述性 CAGR 高於同期 QQQ；但 50 bps 成本下前半段明顯落後，且輸入是現時大型股池，
不能稱為已驗證可盈利策略。本輪是 post-hoc extension，不是獨立首次發現，故不升格。

- regime 版本接受 252 宗訊號；全期 10／25／50 bps 策略 CAGR 為 48.02%／44.39%／38.51%。
- 50 bps 前半段策略／QQQ CAGR 為 10.29%／31.79%；後半段為 84.46%／24.46%。
- 同規則不加 regime 的 25 bps control CAGR 為 24.24%，最大跌幅 -40.26%；regime 版為 44.39%／-25.00%。
- regime 版 25 bps 年化換手 16.35x，平均持倉 6.17 檔；成本與集中度不可忽略。

## 固定規則

| 項目 | 凍結內容 |
|---|---|
| 評分 | `3 × percentile(20-session momentum) + percentile(close / 60-session SMA - 1)` |
| 篩選 | score ≥ 2.0、兩項原始值均為正、流動性 ≥ US$20m 中位成交額、股價 ≥ US$5 |
| 交易 | 收市產生訊號；下一 XNYS open 入場；等權 Top-7；20 sessions 強制離場 |
| regime | QQQ 收市同時高於 20／60-session SMA；control 不使用此 gate |
| 成本／基準 | 單邊 10／25／50 bps；QQQ、SPY、IWM |
| 分段 | 2023–2024；2025–2026H1 |

## Regime 版本全期結果

| 成本 | 訊號 | 策略 CAGR | QQQ CAGR | SPY CAGR | IWM CAGR | 策略最大跌幅 | QQQ 最大跌幅 | 策略 Sharpe |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 10 bps | 252 | 48.02% | 29.50% | 22.31% | 18.83% | -23.47% | -22.77% | 1.72 |
| 25 bps | 252 | 44.39% | 29.38% | 22.20% | 18.72% | -25.00% | -22.77% | 1.61 |
| 50 bps | 252 | 38.51% | 29.18% | 22.01% | 18.54% | -27.49% | -22.77% | 1.44 |

## 決策閘門

- 通過：4/6。
- `both_fixed_halves_beat_qqq_at_50bps, max_drawdown_no_worse_than_qqq_at_10bps` 未通過。
- 現時 watchlist 只有 29 檔個股，沒有 point-in-time 成分、退市／收購回報、完整公司行動、sector 歷史或 high／low ATR。

所有結果只寫入研究 log 與機器收據；`Paper=false`、`public_strategy_allowed=false`、實金 US$0。success-only 網頁維持「今天不下單」。

機器收據：`artifacts/short_term_us_cross_sectional_momentum_diagnostic.json`；協議：`docs/SHORT_TERM_US_CROSS_SECTIONAL_MOMENTUM_PROTOCOL.md`。
