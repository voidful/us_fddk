# 全池動量傾斜：French 25 Size × Prior 12–2 研究報告

凍結協議：2026-08-04｜正式資料：1963-01 至 2026-05｜狀態：**經濟驗證失敗，不啟動 Paper**

## 一頁結論

- 官方首次下載及數據合約 **10/10**；主要外部期 **9/19**，近期確認期 **4/19**，總計 **23/48**。
- 1963–2005 候選 CAGR 12.36%，勝市場 +1.53 個百分點、勝全池等權 +2.35 個百分點；但只保留 Top 1 CAGR 的 73.5%，未達 80% 門檻。
- 2006–2026 候選 CAGR 8.31%，市場 11.38%、SPY 11.26%、QQQ 16.18%；不是現代市場的高回報勝出者。
- 近期 50 bps 成本後 CAGR -1.63%、US$1,000 只餘 US$715。每月全面重組的成本風險足以推翻策略。
- 分散傾斜可穩定勝全池等權，卻不能勝市場；加強集中度在早期顯著增加回報，近期則趨平，證明不能用早期集中結果推論未來。
- French cells 不是證券，也不提供逐股 point-in-time 名單。Paper、實金、持倉及今日買賣動作全部 **US$0**。

## 主要外部期：1963–2005

| 策略／baseline | 年率化回報 | 超額 Sharpe | 波幅 | 最大跌幅 | Calmar | US$1,000 期末值 |
|---|---:|---:|---:|---:|---:|---:|
| 全池線性動量傾斜（候選） | 12.36% | 0.44 | 17.2% | -52.4% | 0.24 | US$149,956 |
| French 美國市場 | 10.82% | 0.38 | 15.3% | -46.5% | 0.23 | US$83,024 |
| 全 25 cells 等權 | 10.01% | 0.31 | 17.6% | -60.0% | 0.17 | US$60,420 |
| 每個 size 的 Prior 4–5 | 14.80% | 0.55 | 17.8% | -44.9% | 0.33 | US$378,122 |
| 每個 size 的 Prior 5 | 16.82% | 0.60 | 20.3% | -43.8% | 0.38 | US$801,394 |
| Big Hi PRIOR 12–2 | 12.12% | 0.41 | 18.3% | -45.7% | 0.27 | US$137,024 |
| 未分 size 的 Hi PRIOR 12–2 | 16.45% | 0.56 | 21.3% | -51.5% | 0.32 | US$697,525 |
| Prior 1–1 短窗線性傾斜 | 8.43% | 0.23 | 17.2% | -63.5% | 0.13 | US$32,503 |

兩個固定分段均勝全池等權：1963–1984 +2.36 個百分點，1985–2005 +2.34 個百分點；但後半段較市場只有 +0.39 個百分點，未達 0.5 個百分點門檻。

## 近期確認期：2006–2026

| 策略／baseline | 年率化回報 | 超額 Sharpe | 波幅 | 最大跌幅 | Calmar | US$1,000 期末值 |
|---|---:|---:|---:|---:|---:|---:|
| 全池線性動量傾斜（候選） | 8.31% | 0.44 | 18.5% | -54.2% | 0.15 | US$5,105 |
| French 美國市場 | 11.38% | 0.67 | 15.6% | -50.3% | 0.23 | US$9,032 |
| 全 25 cells 等權 | 7.66% | 0.39 | 19.8% | -58.4% | 0.13 | US$4,510 |
| 每個 size 的 Prior 4–5 | 8.50% | 0.46 | 17.9% | -51.6% | 0.16 | US$5,288 |
| 每個 size 的 Prior 5 | 8.18% | 0.42 | 19.5% | -55.6% | 0.15 | US$4,976 |
| Big Hi PRIOR 12–2 | 9.00% | 0.49 | 17.2% | -51.8% | 0.17 | US$5,814 |
| 未分 size 的 Hi PRIOR 12–2 | 10.88% | 0.51 | 21.9% | -52.2% | 0.21 | US$8,237 |
| Prior 1–1 短窗線性傾斜 | 7.34% | 0.39 | 18.5% | -55.3% | 0.13 | US$4,245 |
| QQQ 買入持有 | 16.18% | 0.82 | 18.5% | -49.7% | 0.33 | US$21,374 |
| SPY 買入持有 | 11.26% | 0.67 | 15.1% | -50.8% | 0.22 | US$8,825 |

2006–2015 較市場 -1.43 個百分點；2016–2026 更落後 -4.73 個百分點。近期 60 月窗口勝市場只有 11.3%，最新窗口落後 -6.57 個百分點。

## 分散與集中度前沿

| 集中度 | 1963–2005 CAGR | 超額 Sharpe | 最大跌幅 | 2006–2026 CAGR | 超額 Sharpe | 最大跌幅 |
|---|---:|---:|---:|---:|---:|---:|
| 等權 | 10.01% | 0.31 | -60.0% | 7.66% | 0.39 | -58.4% |
| 線性 1:2:3:4:5 | 12.36% | 0.44 | -52.4% | 8.31% | 0.44 | -54.2% |
| 平方 1:4:9:16:25 | 13.75% | 0.51 | -48.1% | 8.49% | 0.45 | -53.0% |
| 只持 Prior 4–5 | 14.80% | 0.55 | -44.9% | 8.50% | 0.46 | -51.6% |
| 只持 Prior 5 | 16.82% | 0.60 | -43.8% | 8.18% | 0.42 | -55.6% |

早期回報隨集中度單調上升；近期 Top 2、平方及線性只在 8.31%–8.50% 之間，Top 1 反而降至 8.18%。這是『排名訊號仍在、集中紅利已弱化』，不是應該追買最集中組合的證據。

## Prior 排名診斷

| Prior 12–2 五分位 | 1963–2005 CAGR | 最大跌幅 | 2006–2026 CAGR | 最大跌幅 |
|---:|---:|---:|---:|---:|
| 1 | 1.25% | -82.1% | 3.03% | -74.8% |
| 2 | 8.49% | -61.3% | 8.20% | -59.4% |
| 3 | 10.28% | -54.7% | 9.02% | -52.1% |
| 4 | 12.64% | -48.6% | 8.69% | -47.6% |
| 5 | 16.82% | -43.8% | 8.18% | -55.6% |

主要期五分位呈單調上升；近期由 Prior 3 開始轉平，Prior 5 不再領先。全池線性傾斜仍勝等權，但增量不足以補回市場機會成本。

## 成本、滾動窗口及統計

- 全歷史 10／25／50 bps CAGR：11.04%／7.11%／0.85%；50 bps 的 US$1,000 期末值只有 US$1,713。
- 主要期 60 月窗勝市場 53.0%、勝全池等權 100.0%；近期分別 11.3%／80.1%。
- 主要期對市場／全池等權 NW t=1.68／5.67；近期為 -1.71／0.53。
- 近期對市場／全池等權 PSR=4.75%／70.61%；6,204 trials DSR=0.000003%／0.0686%。
- 30 路候選家族 CSCV PBO：主要 1.6%，近期 23.8%；近期超過 20% 上限。
- 全歷史五因子 alpha -1.87%、市場 beta 1.01、SMB beta 0.51、MOM beta 0.05、R² 98.3%；大部分波動是市場與小型股暴露，不是獨立 alpha。

## 48 道閘門

主要期通過（9）：`candidate_10bps_cagr_beats_market_by_1pp, candidate_10bps_cagr_beats_all_25_equal_by_1pp, candidate_10bps_cagr_beats_short_window_tilt_by_1pp, candidate_excess_sharpe_beats_market_and_all_25_equal, candidate_drawdown_not_over_5pp_deeper_than_market_or_equal, both_fixed_halves_beat_all_25_equal_by_50bp, rolling_60m_vs_all_25_equal_60pct_and_positive_median, active_psr_vs_market_and_equal_at_least_95pct, candidate_family_pbo_not_above_20pct`。

主要期失敗（10）：`candidate_retains_80pct_of_better_top1_top2_cagr, candidate_excess_sharpe_beats_top1_and_top2, candidate_drawdown_not_deeper_than_top1_or_top2, candidate_50bps_cagr_beats_market_by_50bp, candidate_50bps_cagr_beats_all_25_equal_by_50bp, both_fixed_halves_beat_market_by_50bp, rolling_60m_vs_market_60pct_and_positive_median, active_newey_west_t_vs_market_and_equal_at_least_1_96, active_global_dsr_vs_market_and_equal_at_least_95pct, cost_break_even_vs_market_and_equal_at_least_50bps`。

近期通過（4）：`candidate_retains_80pct_of_better_top1_top2_cagr, candidate_drawdown_not_over_5pp_deeper_than_market_or_equal, both_fixed_halves_beat_all_25_equal_by_50bp, rolling_60m_vs_all_25_equal_60pct_and_positive_median`。

近期失敗（15）：`candidate_10bps_cagr_beats_market_by_1pp, candidate_10bps_cagr_beats_all_25_equal_by_1pp, candidate_10bps_cagr_beats_short_window_tilt_by_1pp, candidate_excess_sharpe_beats_market_and_all_25_equal, candidate_excess_sharpe_beats_top1_and_top2, candidate_drawdown_not_deeper_than_top1_or_top2, candidate_50bps_cagr_beats_market_by_50bp, candidate_50bps_cagr_beats_all_25_equal_by_50bp, both_fixed_halves_beat_market_by_50bp, rolling_60m_vs_market_60pct_and_positive_median, active_newey_west_t_vs_market_and_equal_at_least_1_96, active_psr_vs_market_and_equal_at_least_95pct, active_global_dsr_vs_market_and_equal_at_least_95pct, candidate_family_pbo_not_above_20pct, cost_break_even_vs_market_and_equal_at_least_50bps`。

所有失敗都保留；沒有事後更換權重、成本、起訖日、集中度或 baseline。

## 數據與可交易性

- 新資料來自 Kenneth French 官方 25 Size × Prior 12–2 月度 CSV：每月以 NYSE size 五分位與 prior 2–12 回報五分位交集形成 25 個 value-weighted 組合；t 月組合在 t−1 月形成。
- 學術 cells 涵蓋 NYSE、AMEX 及 NASDAQ，減少用今日成份股倒推的倖存者偏差，但不是逐股 point-in-time／退市賬本，也不可直接落盤。
- QQQ／SPY 只在 2006 後用既有調整價快照作產品機會成本；沒有用現時成份股回填歷史。
- 來源：[Kenneth French Data Library](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/Data_Library.html)及[25 Size × Prior 12–2 方法](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/Data_Library/det_25_port_form_sz_pr_12_2.html)。

## 決定

本輪是首次未見的全池動量傾斜驗證：數據 10/10，但經濟只得 13/38，總計 23/48，判定失敗。它支持『中長窗橫截面排名比短窗更穩』，不支持『可交易且能勝市場的短線策略』。下一個升格入口仍須合格逐股 point-in-time 成分、退市／收購回報、公司行動、流動性、bid-ask spread 及精確成交成本；其後按凍結個股協議由全現金開始、不可回填的前瞻 Paper。
