# 短線 SEC insider cluster 研究收據

研究輪次：研究候選 sub-track
資料截至：2026-06-30
狀態：**research_candidate_only；沒有公開策略或 Paper**

## 一頁結論

本輪首次把 SEC 官方 Insider Transactions Data Sets 接入一個獨立、可重播的
Form 4 事件層。資料是 2026 Q2 的 as-filed 345 ZIP，解析出 6,158 筆合資格的
非衍生工具、`P`（open-market/private purchase）及 `A`（acquired）事件，覆蓋
1,064 個有效 ticker 及 2,140 個 reporting owner。

在目前 30 隻大型股 watchlist（只作當期候選篩選，**不是歷史成分股**）內，固定
「20 個 XNYS session 內至少兩名不同 owner、合計名義金額至少 US$250,000」規則
得到 **0 個候選**。這是資料結果，不是理由去降低門檻或改用事後價格挑選。

因此本輪不建立交易策略、不開 Paper、不產生網站行動建議，實金動作維持 US$0。

## Universe 敏感度 audit

同一批資料及同一條固定規則若不限制於大型股 watchlist，而改用所有有有效 ticker 的
事件，會得到 589 個候選列、277 個 issuer，其中 130 個 issuer 在 20-session 窗口內
重複出現訊號；123 列的名義金額至少 US$10m，37 列至少 US$100m。這與大型股清單的
0 個候選形成鮮明對比，證明候選數高度依賴 universe，而不是策略已找到可交易優勢。

這個 audit 是事後資料品質診斷，不是新策略或參數搜尋。所有列仍標記
`research_only=true`；不會從 589 列挑選股票、不會用名義金額門檻救援結果，也不會把
小型股、私募交易或申報分類不明的 `P` 交易當作可執行買入。網站只讀取已通過正式
promotion 閘門的資料，這份 audit 只保留在內部 log。

## 事件後價格診斷（非正式回測）

為了確認這條事件線是否值得以合格資料重測，另凍結 5／10／20 個交易日的事件後
診斷：申報後下一個 XNYS session 開市進場，以 adjusted open 計算，於第 N 個 session
adjusted close 離場，候選及 QQQ 同時計扣 20 bps round-trip。使用 2026-04-01 至
2026-07-31 的 Yahoo exploratory snapshot；274／278 個候選 ticker 有價格，589 個
候選列中 569 列完成 20 日窗口。

| 持有期 | 候選平均淨回報 | QQQ 平均淨回報 | 平均超額 | 勝出比例 | moving-block bootstrap 95% 區間 |
|---|---:|---:|---:|---:|---:|
| 5 日 | 0.86% | 0.80% | +0.06pp | 48.3% | -0.78pp 至 +1.00pp |
| 10 日 | 1.70% | 1.69% | +0.01pp | 44.5% | -1.22pp 至 +1.30pp |
| **20 日（主要）** | **2.58%** | **1.86%** | **+0.71pp** | **50.4%** | **-0.85pp 至 +2.54pp** |

20 日結果的 bootstrap 零點以下比例為 17.85%，區間仍跨零；事件列互相重疊，亦不是
資金等權組合。這是值得用 CRSP／WRDS／Norgate 逐期成分及退市回報重測的線索，並非
可執行 alpha、買入名單或盈利證據。正面數字也不會改變正式 readiness 或 Paper 狀態。

## 十季固定樣本診斷

為避免單季結果主導判讀，另外事前固定 2024 Q1 至 2026 Q2 十個 SEC quarterly
packages，再用同一 20-session cluster 及同一價格時計重算。共解析 65,591 筆事件，
產生 5,798 個候選列；Yahoo exploratory snapshot 覆蓋 1,328／1,465 個候選 ticker，
20 日窗口有 4,915 列完整，缺口全部保留。

| 固定樣本 | 5 日超額 | 10 日超額 | **20 日超額** | 20 日 bootstrap 95% 區間 |
|---|---:|---:|---:|---:|
| 全部十季 | +0.66pp | +0.71pp | **+0.36pp** | -0.28pp 至 +0.99pp |
| 前五季（2024Q1–2025Q1） | +0.48pp | +0.36pp | **-0.59pp** | -1.40pp 至 +0.19pp |
| 後五季（2025Q2–2026Q2） | +0.83pp | +1.03pp | **+1.24pp** | +0.28pp 至 +2.28pp |

全期主要 20 日配對勝率只有 45.0%，bootstrap 平均超額低於或等於零的比例為 14.9%；
前半段落後、後半段領先，顯示結果受市場時段影響，不能稱為跨期穩健。季度結果亦
混合：2024Q2 約 -4.26pp、2025Q2 約 -1.38pp、2026Q1 約 -1.36pp，但 2025Q4
約 +6.09pp。全期平均超額雖為 +0.36pp，但中位超額為 -1.15pp；後半期平均 +1.24pp
時中位數仍為 -0.74pp，顯示正數主要由少量尾部事件拉動。這種 regime sensitivity、
事件重疊及 137 個候選 ticker 缺乏價格，足以阻止任何 Paper 或網站行動建議。

十季結果只是「值得向合格資料申請重測」的研究線索；它不是十季正式回測，也沒有把
候選列轉成資金等權組合。

## 固定 equal-weight portfolio 可實作性檢查

最後把同一批候選套入事前固定的組合時計：每個 issuer 只取第一個未重疊訊號，持有
20 個交易日，所有 active issuer 等權，不設 Top-K；目標權重變動按單邊 10 bps 計成本，
QQQ 使用相同期間及 20 bps round-trip。這只檢查事件平均數字能否落地，不是另一輪參數
搜尋。

| 固定期間 | 組合 CAGR | QQQ CAGR | 組合最大回撤 | QQQ 最大回撤 | Sharpe | 年化 turnover |
|---|---:|---:|---:|---:|---:|---:|
| 全期 | 33.62% | 23.21% | -23.28% | -22.77% | 1.49 | 38.0x |
| 前五季 | 24.64% | 13.95% | -24.16% | -22.77% | 1.09 | 38.9x |
| 後五季 | 46.24% | 32.86% | -11.91% | -12.62% | 1.91 | 41.0x |

這個表面優勢不能升級為可交易策略：5,798 個候選列只有 2,266 列進入組合，2,649
列因 issuer 持倉重疊被跳過，883 列因缺價格或不足 20 日被跳過；平均約 70 個 active
issuer，亦未有逐筆 spread、流動性、退市／收購回報。接受「有完整價格者」本身已形成
可疑的存活／可得性偏差，故這是 **exploratory upper-bound diagnostic**，不是公平的
20 年個股回測。正式 Paper、網站及實金動作維持零。

### 成本壓力

同一批 2,266 個訊號不變，只改事前固定的單邊成本：

| 單邊成本 | 組合 CAGR | QQQ CAGR | CAGR 超額 |
|---:|---:|---:|---:|
| 10 bps | 33.62% | 23.21% | +10.41pp |
| 25 bps | 26.17% | 23.07% | +3.11pp |
| **50 bps** | **14.67%** | **22.83%** | **-8.16pp** |

50 bps 壓力情境下全期及前／後固定分段均落後 QQQ，顯示表面優勢高度依賴低成本及
不完整價格 coverage；不能以 10 bps 結果宣稱短線策略穩健。

## 固定規則

- 只取 Form 4／4-A 的 `NONDERIV_TRANS`，不把 Form 3、Form 5、衍生工具或持倉列
  當成買入。
- 只取交易代碼 `P` 且 `TRANS_ACQUIRED_DISP_CD=A`；缺日期、ticker、owner、股數
  或價格一律拒收。
- `AFF10B5ONE` 為真時拒收，避免把預先安排的 10b5-1 交易當作 discretionary
  insider view。
- 可用時間是**申報日後下一個 XNYS session**，不是交易發生日；任何申報日後於
  data cut 的事件都不能進入候選。
- owner 以 CIK 去重；來源 accessions 保留在收據，未把「企業家」或「創辦人」身份
  從姓名猜出來。

## 資料邊界

SEC 官方文件指出，該資料集自 2006 年起、按季發布，內容是申報人 as-filed 的結構化
資料，並明確提醒它不是原始申報文件的替代品。它可補足「公司內部人士披露事件」這條
訊號線，但不能取代本專案要求的逐期成分、退市／收購回報、公司行動、價格完整性及
risk-free provider package。

目前使用的 30 隻 watchlist 只作當期篩選，不能用來宣稱 20 年無倖存者偏差表現。

## 收據與可重現性

- 機器收據：`artifacts/short_term_sec_insider_signal.json`
- Universe audit：`artifacts/short_term_sec_insider_universe_audit.json`
- 事件後診斷：`artifacts/short_term_sec_insider_forward_diagnostic.json`
- 十季診斷：`artifacts/short_term_sec_insider_multi_quarter_diagnostic.json`
- 組合檢查：`artifacts/short_term_sec_insider_portfolio_diagnostic.json`
- 下載 URL：SEC 2026 Q2 Form 345 ZIP
- SHA-256：`11f1b2bbbdcbe6347a34437c02d04202fda0eca1dbb023726e4b56504b802e27`
- 重建：`python scripts/build_short_term_sec_insider_signal.py --zip <external-zip> --as-of 2026-06-30 --universe-file usfddk/resources/us_large_cap_watchlist_v1.csv`
- Universe audit 重建：`python scripts/audit_short_term_sec_insider_universe.py --zip <external-zip> --as-of 2026-06-30 --universe-file usfddk/resources/us_large_cap_watchlist_v1.csv`
- 事件後診斷重建：`python scripts/build_short_term_sec_insider_forward_diagnostic.py --sec-zip <external-zip> --prices <prepared-long-csv> --as-of 2026-06-30 --price-client <client-version>`
- 十季診斷重建：`python scripts/build_short_term_sec_insider_multi_quarter.py --manifest <quarter-manifest> --prices <prepared-long-csv> --price-client <client-version>`
- 組合檢查重建：`python scripts/build_short_term_sec_insider_portfolio.py --manifest <quarter-manifest> --prices <prepared-long-csv> --price-client <client-version>`
- 單元測試：`tests/test_sec_insider.py`

下一個有效動作是取得覆蓋完整歷史的價格、退市及 point-in-time 成分資料，先把這條
事件線與凍結的動量 baseline 做獨立樣本外事件研究；在那之前不得把 0 候選改寫成交易
訊號。

本報告只作研究及教育參考，不構成投資建議、Paper 成交、真倉指令或盈利保證。
