# French 25 Size × Prior 1–1 數據映射 v1

凍結日期：2026-08-04

本映射在首次下載 25 Size × Prior 1–1 ZIP 及任何數值列之前提交。只准使用下列官方
來源；不得在看過數字後換鏡像、每日版本、欄位排序或研究期。

## 新增官方檔案

| 角色 | 官方網址 | 預期 ZIP member | 預期範圍 |
|---|---|---|---|
| 25 個 Size × Prior 1–1 月度組合 | `https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/25_Portfolios_ME_Prior_1_0_CSV.zip` | `25_Portfolios_ME_Prior_1_0.csv` | 1926-02 至 2026-05 |

官方說明頁：
`https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/Data_Library/det_25_port_form_sz_pr_1_0.html`。
說明頁在下載前已確認：每月以 NYSE 市值五分位及 prior 1–1 回報五分位交叉形成 25 組，
包含具備所需資料的 NYSE、AMEX 及 NASDAQ 股票，月 t 回報使用 t−1 月末已形成的組合。

## 凍結 schema

- ZIP 只能有一個 CSV member，名稱必須與上表完全相同。
- 只讀兩個精確段落：`Average Value Weighted Returns -- Monthly` 及
  `Average Equal Weighted Returns -- Monthly`。任一 marker 不符即停止；不得模糊搜尋。
- 日期列必須為六位 `YYYYMM`；百分比除以 100；`-99.99`／`-999` 只轉為缺值，不能補值。
- 每個月表必須恰有 25 欄，按官方原始排序保存。語義順序固定為 Size 1 至 Size 5，
  每個 size 內依 Lo PRIOR、PRIOR 2、PRIOR 3、PRIOR 4、Hi PRIOR 排列。
- `Big Hi PRIOR` 定義為 Size 5／Prior 5，`Big Lo PRIOR` 為 Size 5／Prior 1；不得用
  回報反推哪一欄是贏家或輸家。
- 正式共同資料起點不得晚於 1927-01，終點必須為 2026-05；1963-01 後不得有缺月、
  重複月、非有限回報或單月絕對回報超過 100%。
- 原始 ZIP、下載時間、HTTP URL、member、SHA-256、首末日期、兩個月表欄名與缺值稽核
  必須保存。首次準備後若檔案或收據存在，程式須拒絕覆寫或重新下載。

## 只讀既有凍結輸入

| 角色 | 檔案 | SHA-256 |
|---|---|---|
| French 市場及 RF | `artifacts/french_ff_factors_80b88699.zip` | `80b88699a18ac408e2456d25b1004e340f3f7f8d41d5b476a0285bc53c6f0436` |
| 10 組 Prior 1–1 | `artifacts/french_10_prior_1_0_monthly_20b186f6.zip` | `20b186f6f7c322098d6d2a6be6183d5944b12c7f6c9e888664ce44ba81064ace` |
| 10 組 Prior 12–2 | `artifacts/french_10_prior_12_2_monthly_ca0af27f.zip` | `ca0af27fa0829ed6ac38b7b13b20cc11fd12274a8d06dac226998dfc1d0f07f6` |
| Mom 因子 | `artifacts/french_momentum_monthly_37baf72a.zip` | `37baf72ae4eace9715e8746413d0122334c63aa4083fd1c3cf2060fa04e4bd28` |
| ST Rev 因子 | `artifacts/french_st_reversal_monthly_e0fc1859.zip` | `e0fc1859c8b7e56ac17d06239de231fb33d28c8537b3f59fa378d4d704110e21` |
| QQQ／SPY 產品價格快照 | `artifacts/snapshot_20260731_6a7ca6b8.zip` | `d480fb82e712f06aabe0a98461e222344656b87022b8bda2cd7ccaa4c29ae88b` |

QQQ／SPY 只用於 2006-01 後產品機會成本；不把 Yahoo 股票快照用於組成歷史個股池。
所有經濟計算只讀封存檔，不在報表建置時更新行情。
