# 美股短線 20 年 20／60 動量研究報告

版本：v1｜狀態：`research_candidate_only`｜用途：長樣本研究診斷，並非買入名單、Paper 指令或投資建議。

## 結論先行

在 2004–2026 凍結快照上，20 日動量 ×3、60 日趨勢 ×1、Top-7、20 sessions 及 QQQ
regime 的描述性結果在低成本下略勝 QQQ，但 25／50 bps 成本後反轉落後；前段及後段
亦沒有同時勝出。本輪保留負面成本／持續性結果，不升格。

- regime 版本接受 1531 宗訊號；全期 10／25／50 bps 策略 CAGR 為 17.82%／14.88%／10.14%。
- 50 bps 前段策略／QQQ CAGR 為 4.88%／10.64%；後段為 15.34%／19.23%。
- 不加 regime 的 25 bps control CAGR 為 15.03%，最大跌幅 -45.51%；regime 版為 14.88%／-41.02%。

## 固定規則

| 項目 | 凍結內容 |
|---|---|
| 評分 | `3 × percentile(20-session momentum) + percentile(close / 60-session SMA - 1)` |
| 執行 | 下一 XNYS open 入場；最多七檔等權；20 sessions 強制離場 |
| regime | QQQ 收市高於 20／60-session SMA；另列 no-regime control |
| gap | `abs(next open / signal close - 1) < 1.5 × ATR20`，在 open 決定是否跳過 |
| 成本／基準 | 單邊 10／25／50 bps；QQQ、SPY、IWM |
| 分段 | 2004–2014；2015–2026H1 |

## Regime 版本全期結果

| 成本 | 訊號 | 策略 CAGR | QQQ CAGR | SPY CAGR | IWM CAGR | 策略最大跌幅 | QQQ 最大跌幅 | 策略 Sharpe |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 10 bps | 1531 | 17.82% | 15.16% | 10.83% | 8.88% | -37.40% | -53.40% | 0.92 |
| 25 bps | 1531 | 14.88% | 15.14% | 10.82% | 8.86% | -41.02% | -53.40% | 0.79 |
| 50 bps | 1531 | 10.14% | 15.12% | 10.79% | 8.84% | -46.62% | -53.40% | 0.58 |

## 決策閘門

- 通過：3/6。
- `cagr_beats_qqq_at_25bps, cagr_beats_qqq_at_50bps, both_fixed_halves_beat_qqq_at_50bps` 未通過。
- 快照是現時大型股池，且 manifest 已記錄 ABBV／META 歷史覆蓋不足；沒有 point-in-time 成分、退市／收購回報、完整公司行動、sector 歷史及正式 risk-free package。

所有結果只寫入研究 log 與機器收據；`Paper=false`、`public_strategy_allowed=false`、實金 US$0。success-only 網頁維持「今天不下單」。

機器收據：`artifacts/short_term_us_momentum_20y_diagnostic.json`；協議：`docs/SHORT_TERM_US_MOMENTUM_20Y_PROTOCOL.md`。
