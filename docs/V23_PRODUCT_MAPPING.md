# v23 產品映射：S&P 500 資本效率＋管理期貨

狀態：**在首次下載 KMLM／FMF 完整日線與首次 v23 組合計算前凍結。**

## Paper 候選產品

| 角色 | 產品 | 固定資本權重 | 定義與限制 |
|---|---|---:|---|
| 美國大型股核心 | SSO | 50% | ProShares Ultra S&P500；每日目標為 S&P 500 的 2 倍，不把長期結果當成精確 2 倍。成立日 2006-06-19。 |
| 多市場趨勢分散器 | KMLM | 50% | KraneShares Mount Lucas Managed Futures Index Strategy ETF；追蹤 KFA MLM Index，含 11 種商品、6 種貨幣、5 個全球公債期貨，不含股票期貨。成立日 2020-12-01。 |

實體權重合計 100%，不由 Paper 帳戶借款、不放空 ETF。這不是「低風險」產品：SSO 有每日槓桿複利與波動拖累；KMLM 持有多空期貨，可能出現快速反轉、保證金、流動性、追蹤誤差與較高稅務複雜度。

## 長期歷史映射

KMLM 沒有 20 年 ETF 歷史。正式長期段只能使用官方公布的 KFA MLM Index 月報酬，並明確標為**歷史指數代理**：

- 2006-07 至 2020-11：MLM Index EV 月報酬。
- 2020-12 起：使用同一 EV 方法的 KFA MLM Index 月報酬。
- 只用 2005-01-01 起的 EV／KFA 同方法區間，不使用 1988-2004 舊 MLM 方法。
- 官方月報酬是指數、不可投資，且未扣管理費、交易成本或 ETF 追蹤誤差。
- 每個月先將指數報酬扣除年化 1.05% 拖累的月複利等值；1.05% 來自 KMLM 官方 FAQ 的 0.90% 費用與約 0.15% 交易費用說明。
- 長期回測不可描述為「20 年實際 KMLM 回測」，只能描述為「20 年實際 SSO＋官方 KFA MLM 歷史指數代理」。

## 固定對照

1. `SPY`：投資人最直接可買的 S&P 500 ETF 基準。
2. `50% SSO / 50% SHY`：相同實體資本與約 100% 股票名目曝險、但沒有管理期貨的控制。
3. `2/3 SPY / 1/3 KFA_MLM_NET_PROXY`：把候選約 100 單位股票／50 單位管理期貨曝險按 150 單位正規化的未槓桿同資產控制。
4. KMLM 上市後，以 `50% SSO / 50% KMLM` 與相同期間 SPY、SSO／SHY 控制比較。
5. 跨管理人診斷使用 `50% SSO / 50% FMF`；FMF 是 First Trust 主動管理期貨 ETF，不是 KFA 指數的可互換替代品，也不是 Paper 候選。

## 排除產品

- `WTMF`：成立於 2011 年，但 WisdomTree 官方歸因文件明載 2021-06-04 曾重大改造策略；2025 年招募說明書又允許最多 10% 資產配置比特幣 ETP／期貨。完整價格史不是同一定義，排除於 v23 正式驗證。
- `RSST`：其「股票＋管理期貨堆疊」可作資本效率架構參考，但成立於 2023-09-05，產品史太短，不用於 20 年驗證或候選挑選。
- 不用合成 SSO，不把 KFA 指數接成 KMLM 實際 ETF，也不把 FMF／WTMF／KMLM 宣稱為同一策略。

## 凍結前已見資訊

已看過 SSO、KMLM、FMF、WTMF 與 RSST 官方產品頁的成立日、策略摘要與部分摘要績效；也已看過 KFA MLM 官方月報酬表，但尚未做 v23 聯合組合計算，尚未下載 KMLM／FMF 完整日線。因此 v23 最多只能稱為**半獨立產品路徑驗證**，不能稱完全盲測。

## 官方來源

- ProShares SSO：<https://www.proshares.com/our-etfs/leveraged-and-inverse/sso>
- KraneShares KMLM：<https://kraneshares.com/etf/kmlm/>
- KMLM FAQ 與指數／追蹤說明：<https://kraneshares.com/kmlm-managed-futures-faq/>
- KFA MLM 官方月報酬 deck：<https://engage.kraneshares.com/s/77b9d7d7/?ks_product=kmlm&page=15>
- KMLM SEC 摘要招募說明書：<https://www.sec.gov/Archives/edgar/data/1547576/000182912624005085/kraneshares_497k.htm>
- First Trust FMF：<https://www.ftportfolios.com/retail/etf/etfsummary.aspx?ticker=fmf>
- WTMF 2021 改造揭露：<https://www.wisdomtree.com/us/media/wtmf-attribution-presentation>
- WTMF 2025 SEC 摘要招募說明書：<https://www.sec.gov/Archives/edgar/data/1350487/000121465925009342/wtmf61625497k.htm>
- RSST：<https://www.returnstackedetfs.com/rsst-return-stacked-us-stocks-managed-futures/>
