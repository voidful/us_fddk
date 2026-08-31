# 月度動量排名加權外部驗證報告

版本：v1｜狀態：`external_rank_weighted_momentum_validation_failed`｜用途：外部機制診斷，不是買入名單、Paper 指令或投資建議。

## 結論先行

將現時大型股稽核中預先固定的 `rank_weighted_top3`（50%／30%／20%）原樣套用到十隻
Vanguard 行業 ETF 後，結果未能重現；本輪不升格。

- 10／25／50 bps 策略 CAGR 為 5.45%／2.65%／-1.84%，相應 QQQ 為 16.70%／16.70%／16.68%。
- 50 bps 前／後半段相對 QQQ CAGR 差為 -18.17%／-18.74%。
- 經濟及統計閘門通過 1/10；失敗結果只保留在收據與本報告。

## 固定規則

| 項目 | 內容 |
|---|---|
| 訊號 | 月末 20-session momentum＋60-session SMA；Top-3 |
| 權重 | 排名 50%／30%／20%；不足名額餘額持有 SHY |
| 執行 | 下一 XNYS open；下次月末再平衡 |
| 成本 | 單邊 10／25／50 bps |
| 基準 | QQQ、SPY、VTI、行業等權、起點漂移及 matched control |
| 資料 | Vanguard 2006-08-01 至 2026-07-31 凍結面板 |

## 全期結果

| 成本 | 策略 CAGR | QQQ CAGR | SPY CAGR | VTI CAGR | 策略最大跌幅 | QQQ 最大跌幅 | Sharpe |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 10 bps | 5.45% | 16.70% | 11.26% | 11.21% | -43.13% | -53.40% | 0.41 |
| 25 bps | 2.65% | 16.70% | 11.25% | 11.20% | -45.49% | -53.40% | 0.24 |
| 50 bps | -1.84% | 16.68% | 11.24% | 11.18% | -64.31% | -53.40% | -0.03 |

## 決策

- `cagr_beats_qqq_by_2pp_at_10bps, cost_50bps_beats_qqq_by_50bp, both_fixed_halves_beat_qqq_by_50bp, rolling_three_year_win_fraction_at_least_60pct, rolling_three_year_median_edge_positive, beats_matched_control_cagr, active_newey_west_t_at_least_1_96, active_psr_at_least_95pct, active_dsr_at_least_95pct` 未通過。
- 即使本輪外部 ETF 資料完整，ETF 產品驗證也不能取代個股逐期成分、退市回報及公司行動資料。
- `paper_authorized=false`、`public_strategy_allowed=false`、實金 US$0；success-only 網頁維持「今天不下單」。

機器收據：`artifacts/short_term_monthly_momentum_rank_weighted_external.json`；協議：`docs/SHORT_TERM_MONTHLY_MOMENTUM_RANK_WEIGHTED_EXTERNAL_PROTOCOL.md`。
