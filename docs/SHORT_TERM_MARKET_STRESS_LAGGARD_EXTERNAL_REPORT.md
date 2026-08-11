        # 市場急跌落後反轉：獨立 Vanguard 行業 ETF 外部驗證報告

        狀態：`external_market_stress_laggard_validation_failed`。本報告是機制診斷，不是個股名單、Paper 指令或投資建議。

        ## 結論先行

        固定規則在獨立 Vanguard 行業 ETF 面板只產生 **18 宗** 20-session 完整事件，低於事前要求的 30 宗；主要 6 項 gate 通過 **1/6**。因此不能聲稱短線個股策略已獲外部確認，結果只留在研究 log。

        - 20-session、20 bps 候選 Top-5 平均淨回報：`8.79%`；合資格池：`8.56%`。
        - 配對平均差：`0.23%`；NW t：`0.99`；配對勝率：`38.89%`。
        - ETF 代理不能取代個股 point-in-time 成分、退市回報、公司行動及真實成交時間。

        ## 固定口徑

        | 項目 | 規則 |
        |---|---|
        | 訊號 | SPY 單日跌至少 1.5%；標的五日跌至少 5% |
        | 篩選 | 價格 > US$5；20-session median dollar volume ≥ US$20m |
        | 選擇 | 最弱 Top-5 Vanguard 行業 ETF |
        | 執行 | 下一 session open 進場；5／10／20 session close 離場 |
        | 成本 | 10／20／50 bps 敏感度；20 bps 為主要口徑 |
        | 基準 | 合資格池、全行業等權、SPY、QQQ、VTI |

        ## 事件結果

        | Horizon | 成本 | 事件 | 候選平均 | 合資格池平均 | 配對差 | NW t |
        |---:|---:|---:|---:|---:|---:|---:|
        | 5 | 10 | 18 | 1.50% | 1.48% | 0.02% | 0.07 |
| 5 | 20 | 18 | 1.40% | 1.38% | 0.02% | 0.07 |
| 5 | 50 | 18 | 1.10% | 1.08% | 0.02% | 0.07 |
| 10 | 10 | 18 | 3.14% | 2.98% | 0.17% | 1.64 |
| 10 | 20 | 18 | 3.04% | 2.88% | 0.17% | 1.64 |
| 10 | 50 | 18 | 2.74% | 2.58% | 0.17% | 1.64 |
| 20 | 10 | 18 | 8.89% | 8.66% | 0.23% | 0.99 |
| 20 | 20 | 18 | 8.79% | 8.56% | 0.23% | 0.99 |
| 20 | 50 | 18 | 8.49% | 8.26% | 0.23% | 0.99 |

        ## 主要 20-session／20 bps gates

        | Gate | 結果 |
        |---|---|
        | at_least_30_complete_events | 未通過 |
| mean_difference_positive | 通過 |
| newey_west_t_at_least_1_96 | 未通過 |
| bootstrap_95pct_low_positive | 未通過 |
| paired_win_fraction_above_50pct | 未通過 |
| both_fixed_halves_positive | 未通過 |

        前段配對差：`—`；後段：`0.23%`；bootstrap 95% 下界：`-0.22%`。

        ## 邊界

        `paper_authorized=false`、`public_strategy_allowed=false`、實金 US$0。沒有建立 strategy run、Paper 帳戶或個股公開名單；success-only 首頁不會讀取本收據，仍顯示「今天不下單」。

        協議：`docs/SHORT_TERM_MARKET_STRESS_LAGGARD_EXTERNAL_PROTOCOL.md`
        收據：`artifacts/short_term_market_stress_laggard_external.json`
