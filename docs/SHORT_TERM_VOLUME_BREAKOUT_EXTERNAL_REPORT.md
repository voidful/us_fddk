        # 成交量突破 × SPY 60-session regime：獨立 Vanguard ETF 外部診斷報告

        狀態：`external_volume_breakout_validation_failed`。本報告是 post-hoc 機制診斷，不是個股名單、Paper 指令或投資建議。

        ## 結論先行

        固定規則在獨立 Vanguard 行業 ETF 面板產生 **45 宗** 20-session 完整事件；
        主要六項 gate 通過 **1/6**。候選相對合資格池的平均差為
        `-0.68%`，但勝率、統計顯著性、bootstrap
        下界及固定分段未全部通過，因此不能聲稱成交量突破個股策略已獲外部確認。

        - 20-session／20 bps 候選平均淨回報：`-0.41%`；
          eligible pool：`0.27%`。
        - NW t：`-1.49`；
          配對勝率：`42.22%`；
          bootstrap 95% 下界：`-1.53%`。
        - ETF 代理不能替代個股 point-in-time 成分、退市回報、公司行動或 raw execution。

        ## 固定口徑

        | 項目 | 規則 |
        |---|---|
        | 訊號 | 每週最後完成 session；SPY close > 60-session SMA |
        | 篩選 | 價格 > US$5；20-session median dollar volume ≥ US$20m；20-session 回報 > 0；close > SMA60 |
        | 突破 | close > 前 60-session 最高 close；volume ≥ 1.5 × 20-session median volume |
        | 選擇 | 20-session 回報最高 Top-10 Vanguard 行業 ETF |
        | 執行 | 下一 session open；5／10／20 session close |
        | 成本 | 10／20／50 bps 敏感度；20 bps 為主要口徑 |
        | 基準 | eligible pool、全行業等權、SPY、QQQ、VTI |

        ## 事件結果

        | Horizon | 成本 | 事件 | 候選平均 | eligible 平均 | 配對差 | NW t |
        |---:|---:|---:|---:|---:|---:|---:|
        | 5 | 10 | 45 | 0.09% | 0.26% | -0.17% | -1.25 |
| 5 | 20 | 45 | -0.01% | 0.16% | -0.17% | -1.25 |
| 5 | 50 | 45 | -0.31% | -0.14% | -0.17% | -1.25 |
| 10 | 10 | 45 | -0.16% | 0.22% | -0.38% | -1.80 |
| 10 | 20 | 45 | -0.26% | 0.12% | -0.38% | -1.80 |
| 10 | 50 | 45 | -0.56% | -0.18% | -0.38% | -1.80 |
| 20 | 10 | 45 | -0.31% | 0.37% | -0.68% | -1.49 |
| 20 | 20 | 45 | -0.41% | 0.27% | -0.68% | -1.49 |
| 20 | 50 | 45 | -0.71% | -0.03% | -0.68% | -1.49 |

        ## 主要 20-session／20 bps gates

        | Gate | 結果 |
        |---|---|
        | at_least_30_complete_events | 通過 |
| mean_difference_positive | 未通過 |
| newey_west_t_at_least_1_96 | 未通過 |
| bootstrap_95pct_low_positive | 未通過 |
| paired_win_fraction_above_50pct | 未通過 |
| both_fixed_halves_positive | 未通過 |

        前段配對差：`-0.85%`；
        後段：`-0.67%`。

        ## 邊界

        `paper_authorized=false`、`public_strategy_allowed=false`、實金 US$0。沒有建立 strategy run、
        Paper 帳戶或個股公開名單；success-only 首頁不會讀取本收據，仍顯示「今天不下單」。本輪
        係 post-hoc external replication，不能升格為獨立首次證據。

        協議：`docs/SHORT_TERM_VOLUME_BREAKOUT_EXTERNAL_PROTOCOL.md`
        收據：`artifacts/short_term_volume_breakout_external.json`
