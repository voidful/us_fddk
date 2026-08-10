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
- 下載 URL：SEC 2026 Q2 Form 345 ZIP
- SHA-256：`11f1b2bbbdcbe6347a34437c02d04202fda0eca1dbb023726e4b56504b802e27`
- 重建：`python scripts/build_short_term_sec_insider_signal.py --zip <external-zip> --as-of 2026-06-30 --universe-file usfddk/resources/us_large_cap_watchlist_v1.csv`
- Universe audit 重建：`python scripts/audit_short_term_sec_insider_universe.py --zip <external-zip> --as-of 2026-06-30 --universe-file usfddk/resources/us_large_cap_watchlist_v1.csv`
- 事件後診斷重建：`python scripts/build_short_term_sec_insider_forward_diagnostic.py --sec-zip <external-zip> --prices <prepared-long-csv> --as-of 2026-06-30 --price-client <client-version>`
- 單元測試：`tests/test_sec_insider.py`

下一個有效動作是取得覆蓋完整歷史的價格、退市及 point-in-time 成分資料，先把這條
事件線與凍結的動量 baseline 做獨立樣本外事件研究；在那之前不得把 0 候選改寫成交易
訊號。

本報告只作研究及教育參考，不構成投資建議、Paper 成交、真倉指令或盈利保證。
