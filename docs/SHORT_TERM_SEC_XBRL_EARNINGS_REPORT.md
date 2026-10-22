# SEC XBRL 正 EPS／營收事件研究報告

版本：v1｜狀態：`research_candidate_only`｜用途：短線個股研究診斷，並非買入名單、Paper 指令或投資建議。

## 結論先行

這個固定規則事件層未能跑贏 QQQ，不能升格為可行策略，也不會出現在 success-only 網頁。

- 2023-01-01 至 2026-06-30 的 29 個唯一 CIK 觀察池產生 139 個正 diluted EPS／營收同比事件，涵蓋 23 家公司。
- 以前 20 個交易日 median dollar volume 至少 US$20m、前一日收市價至少 US$5 的固定流動性門檻後，138 個事件可模擬；唯一跳過原因是入場前不足 20 個流動性觀察日。
- 單邊成本由 10 bps 提高至 50 bps，策略 CAGR 由 13.40% 降至 -3.34%；同期 QQQ CAGR 為 29.07% 至 28.77%。三個成本情境均落後 QQQ，後半段亦沒有反轉。
- 研究收據將失敗、缺少 prior、非正值、未同時增長及流動性跳過原因全部留在 [診斷收據](../artifacts/short_term_sec_xbrl_earnings_diagnostic.json)；公開資料契約不會讀取這些結果。

## 研究邊界

| 項目 | 凍結規則 |
|---|---|
| 基本面來源 | [SEC EDGAR Company Facts API](https://www.sec.gov/search-filings/edgar-application-programming-interfaces)，每個 CIK 一份 JSON；`filed <= 2026-06-30` |
| 觀察池 | `us_large_cap_watchlist_v1.csv` 的 2026-07-30 快照；同一 CIK 只保留檔案順序第一個代表股份類別 |
| 表格 | 僅原始 `10-Q`、`fp=Q1/Q2/Q3`、期間 70–120 日；拒收 10-K、10-Q/A、8-K 及自訂 taxonomy |
| 指標 | `EarningsPerShareDiluted`（`USD/shares`）；營收優先 `Revenues`，缺合資格觀察才用 `RevenueFromContractWithCustomerExcludingAssessedTax`（`USD`） |
| 事件 | 當季及同一 `fp` 上年同期的 EPS、營收均為正，且兩者均同比上升；只取最早原始 filing，下一個 XNYS session 才可用 |
| 持有及基準 | 下一個 XNYS session 入場，持有 20 sessions；active ticker 等權；QQQ、SPY、IWM 同一時鐘、同一期間 |
| 成本 | 策略單邊 10／25／50 bps；基準相應 20／50／100 bps round-trip |
| 分段 | 前半段 filing date 2023-01-01–2024-12-31；後半段 2025-01-01–2026-06-30 |

這是現時觀察池的 post-hoc diagnostic，不是 20 年 point-in-time 成分股回測；沒有把退市／收購回報、完整 corporate-action ledger 或正式 risk-free package 假裝補齊。

## 全期結果

| 策略成本 | 接受事件 | 策略 CAGR | QQQ CAGR | 相對 QQQ | 策略最大跌幅 | QQQ 最大跌幅 | 策略 Sharpe | QQQ Sharpe |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 10 bps | 138 | 13.40% | 29.07% | -15.67 個百分點 | -22.94% | -22.77% | 0.63 | 1.38 |
| 25 bps | 138 | 6.82% | 28.96% | -22.14 個百分點 | -26.18% | -22.77% | 0.39 | 1.38 |
| 50 bps | 138 | -3.34% | 28.77% | -32.11 個百分點 | -34.85% | -22.77% | -0.01 | 1.37 |

同一 10 bps 情境下，SPY CAGR 為 21.63%、IWM CAGR 為 15.26%，兩者亦高於策略 13.40%。策略年化 turnover 約 39.70 倍，平均 active positions 約 3.22 個。

## 固定前後半段壓力

下表仍使用同一事件規則及同一流動性門檻，沒有按結果重選期間或參數。

| 成本 | 2023–2024 策略／QQQ CAGR | 2025–2026H1 策略／QQQ CAGR |
|---:|---:|---:|
| 10 bps | 17.84% ／ 37.65% | 8.12% ／ 20.26% |
| 25 bps | 11.35% ／ 37.43% | 1.33% ／ 20.02% |
| 50 bps | 1.31% ／ 37.07% | -9.08% ／ 19.61% |

前後兩段、全部成本情境都落後 QQQ，沒有足夠證據支持穩健性或可交易性。

## 升格決定

| 閘門 | 結果 |
|---|---|
| 正式 point-in-time universe | 未完成 |
| 20 年可比歷史 | 未完成 |
| 成本壓力全部勝出 | 否 |
| 前後固定半段勝出 | 否 |
| Paper 授權 | 否 |
| success-only 網頁公開 | 否 |
| real-money action | US$0 |

因此網站只會顯示已通過全部公開門檻的策略與行動；本輪只更新研究報告及機器 log，失敗結果不轉成交易建議。
