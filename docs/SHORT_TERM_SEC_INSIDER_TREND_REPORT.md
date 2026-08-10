# SEC insider cluster + trend 共振研究報告

研究快照：2026-07-31；研究時計：2024-04-12 至 2026-07-23

狀態：**research_candidate_only；不開 Paper；實金動作 US$0**

## 一頁結論

本輪在已固定的 SEC insider cluster 及 US$20m／US$5 可交易性 filter 之上，事前固定
加入「入場前 60 個 XNYS sessions 收市價高於 60 日平均線，且 20-session 動量為正」的
單一 trend gate。沒有按結果搜尋其他回顧期、門檻、Top-K 或持有期。

5,798 個候選列中，只有 **142 列**同時通過流動性、趨勢及完整 20-session 價格窗口；
1,235 列成交額不足、2,750 列趨勢不合格、1,576 列缺少完整 60-session 趨勢歷史，
95 列因 issuer 持倉重疊跳過。所有拒收原因保留在機器收據，不轉成網站候選名單。

10／25 bps 的全期 CAGR 表面高於 QQQ，但 50 bps 反轉，而且前五季大幅落後 QQQ；
最大回撤亦比 QQQ 深超過 11 個百分點。這不是跨期、成本穩健的可交易策略。

## 固定時計及規則

- SEC 來源固定為 2024Q1 至 2026Q2 十個 as-filed quarterly packages；cluster 規則
  沿用 20-session、兩名 owner、US$250,000。
- 只用入場前資料計算 20-session median dollar volume、前一日收市價、60-session
  simple moving average 及 20-session momentum。
- 每個 issuer 第一個未重疊訊號持有 20 個 XNYS sessions，active issuer 等權；入場日
  adjusted open，之後 close-to-close；不止蝕、不止賺、不槓桿。
- 成本固定為單邊 10／25／50 bps；QQQ、SPY、IWM 使用相同 evaluation period 及同一
  成本情境（20／50／100 bps round-trip baseline）。
- 完整協議：[SHORT_TERM_SEC_INSIDER_TREND_PROTOCOL.md](SHORT_TERM_SEC_INSIDER_TREND_PROTOCOL.md)。

## 成本及 baseline

| 單邊成本 | 組合 CAGR | QQQ CAGR | SPY CAGR | IWM CAGR | 對 QQQ 超額 | 最大回撤 | Sharpe | 年化 turnover |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 10 bps | 35.47% | 22.39% | 18.46% | 18.94% | +13.08pp | -34.10% | 1.00 | 44.7x |
| 25 bps | 26.63% | 22.23% | 18.30% | 18.78% | +4.40pp | -35.42% | 0.82 | 44.7x |
| **50 bps** | **13.15%** | **21.96%** | **18.04%** | **18.52%** | **-8.81pp** | **-37.58%** | **0.52** | **44.7x** |

10 bps 的回撤比 QQQ 深 11.33pp，50 bps 深 14.81pp；策略 Sharpe 在三個成本情境均
低於 QQQ。表面 CAGR 優勢不能抵銷成本及下行風險。

## 固定前後半段

| 時段 | 10 bps 組合／QQQ CAGR | 25 bps 組合／QQQ CAGR | 50 bps 組合／QQQ CAGR |
|---|---:|---:|---:|
| 2024Q1–2025Q1 | -11.00%／7.21% | -16.62%／6.91% | -25.21%／6.39% |
| 2025Q2–2026Q2 | 96.24%／38.03% | 82.94%／37.71% | 62.72%／37.18% |

前半段三個成本都跑輸 QQQ，後半段的極高回報不能被當作跨期證據；中間存在明顯
regime sensitivity。研究樣本只有約兩年三個月，亦遠非正式 20 年個股回測。

## 決策

此 extension 沒有通過「固定前後段 + 50 bps + 回撤」的基本可交易性審查，且仍使用
exploratory Yahoo 價格，沒有 point-in-time 成分、退市／收購回報、公司行動賬本或正式
risk-free package。因此：

- 不建立 Paper，不產生即日選股名單或落盤指令。
- 不把 2025Q2–2026Q2 的表面高回報放進 success-only 網頁。
- 失敗、skip reason、完整 baseline 及成本表只留在
  `artifacts/short_term_sec_insider_trend_diagnostic.json` 與研究 log。
- 下一個有效升格動作仍是取得合資格 point-in-time 個股資料後，按同一協議只重跑一次。

本報告是研究紀錄，不構成投資建議、Paper 成交、真倉指令或盈利保證。
