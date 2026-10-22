# SEC XBRL 盈利事件＋60／20 趨勢確認研究報告

版本：v1｜狀態：`research_candidate_only`｜用途：短線個股研究診斷，並非買入名單、Paper 指令或投資建議。

## 結論先行

在 parent XBRL 正 EPS／營收事件上加入事前固定的 60-session 均線及 20-session 正動量確認後，結果仍未能跑贏 QQQ；本輪不升格。

- parent 139 宗事件中，趨勢確認後接受 77 宗；58 宗低於趨勢門檻，4 宗缺少 60-session 歷史。
- 10／25／50 bps 策略 CAGR 為 12.97%／7.94%／0.04%，相應 QQQ 為 24.06%／23.94%／23.74%。
- 50 bps 前半段策略／QQQ CAGR 為 4.87%／28.29%；後半段為 -5.10%／19.61%。

## 固定規則

| 項目 | 凍結內容 |
|---|---|
| parent | `short_term_sec_xbrl_earnings_diagnostic.json`，SHA-256 `823c46ac34633c847f915647127e2d18f1956563a36f4148f24b3b738fe90c57` |
| 趨勢 | 入場前 60 sessions 收市均線；入場前一日相對 20 sessions 前回報 > 0 |
| 時計 | filing 後第一個 XNYS session 入場；20 sessions；下一交易日 adjusted open |
| 成本 | 單邊 10／25／50 bps |
| 基準 | QQQ、SPY、IWM，同評估時段及成本 |
| 分段 | 2023–2024；2025–2026H1 |

## 全期結果

| 成本 | 接受事件 | 策略 CAGR | QQQ CAGR | SPY CAGR | IWM CAGR | 策略最大跌幅 | QQQ 最大跌幅 | 策略 Sharpe |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 10 bps | 77 | 12.97% | 24.06% | 20.94% | 18.52% | -26.44% | -22.77% | 0.59 |
| 25 bps | 77 | 7.94% | 23.94% | 20.82% | 18.41% | -26.44% | -22.77% | 0.42 |
| 50 bps | 77 | 0.04% | 23.74% | 20.63% | 18.22% | -26.44% | -22.77% | 0.14 |

## 決策閘門

- 通過：1/6。
- `cagr_beats_qqq_at_10bps, cagr_beats_qqq_at_25bps, cagr_beats_qqq_at_50bps, both_fixed_halves_beat_qqq_at_50bps, max_drawdown_no_worse_than_qqq_at_10bps` 未通過。
- parent 本身是現時大型股觀察池及 exploratory adjusted OHLCV；沒有 point-in-time 成分、退市／收購回報、完整公司行動及正式 risk-free package。

所有結果只寫入研究 log 與機器收據，不建立 Paper、不產生個股公開名單、不顯示實金比例。success-only 網頁維持「今天不下單」。

機器收據：`artifacts/short_term_sec_xbrl_trend_diagnostic.json`；協議：`docs/SHORT_TERM_SEC_XBRL_TREND_PROTOCOL.md`。
