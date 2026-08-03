# French 25 Size × Momentum 全池傾斜數據映射 v1

凍結日期：2026-08-04

本映射在首次下載 25 Size × Prior 12–2 ZIP 及任何數值列之前提交。只准使用下列官方
來源；不得在看過數字後換每日版本、地區版本、鏡像、欄位排序或研究期。

## 新增官方檔案

| 角色 | 官方網址 | 預期 ZIP member | 預期範圍 |
|---|---|---|---|
| 25 個 Size × Prior 12–2 月度組合 | `https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/25_Portfolios_ME_Prior_12_2_CSV.zip` | `25_Portfolios_ME_Prior_12_2.csv` | 1927-01 至 2026-05 |

官方說明頁：
`https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/Data_Library/det_25_port_form_sz_pr_12_2.html`。
下載前只確認方法及非數值 metadata：每月把 NYSE 市值五分位與 prior 2–12 回報五分位
交叉形成 25 組；包含具備所需資料的 NYSE、AMEX 及 NASDAQ 股票；month t 使用 t−1
月末已形成組合；官方頁列示 1927-01 至 2026-05。

## 凍結 schema

- ZIP 只能有一個 CSV member，名稱必須與上表完全相同。
- 只讀兩個精確段落：`Average Value Weighted Returns -- Monthly` 及
  `Average Equal Weighted Returns -- Monthly`。任一 marker 不符即停止。
- 日期必須為六位 `YYYYMM`；百分比除以 100；`-99.99`／`-999` 只轉缺值，不補值。
- 每個月表必須恰有 25 欄，保存官方原始排序。語義固定為 Size 1 至 Size 5，每個 size
  內依 Lo PRIOR、PRIOR 2、PRIOR 3、PRIOR 4、Hi PRIOR 排列。
- 正式共同起點不得晚於 1927-01，終點必須為 2026-05；1963-01 後不得有缺月、重複月、
  非有限回報或單月絕對回報超過 150%。
- 原始 ZIP、下載時間、HTTP URL、member、SHA-256、大小、首末日期、兩個月表欄名及
  缺值稽核必須保存。首次準備後如檔案或收據存在，程式須拒絕覆寫或重新下載。

## 固定權重映射

- 25 欄按 `(size_rank, prior_rank)` 映射，不用回報反推贏家。
- 候選 cell 權重固定為 `prior_rank / 75`，25 個權重合計 1。
- 全池等權為每 cell `1/25`。
- Top-2 只保留 prior 4／5，每個有效 cell `1/10`；Top-1 只保留 prior 5，每個有效
  cell `1/5`。
- 平方傾斜只作敏感度，cell 權重為 `prior_rank² / 275`。
- 候選及所有 cell 聚合月度回報使用同月 cell returns 的固定權重和；不再 shift。

## 只讀既有封存輸入

| 角色 | 檔案 | SHA-256 |
|---|---|---|
| French 市場及 RF | `artifacts/french_ff_factors_80b88699.zip` | `80b88699a18ac408e2456d25b1004e340f3f7f8d41d5b476a0285bc53c6f0436` |
| 10 組 Prior 12–2 | `artifacts/french_10_prior_12_2_monthly_ca0af27f.zip` | `ca0af27fa0829ed6ac38b7b13b20cc11fd12274a8d06dac226998dfc1d0f07f6` |
| Mom 因子 | `artifacts/french_momentum_monthly_37baf72a.zip` | `37baf72ae4eace9715e8746413d0122334c63aa4083fd1c3cf2060fa04e4bd28` |
| ST Rev 因子 | `artifacts/french_st_reversal_monthly_e0fc1859.zip` | `e0fc1859c8b7e56ac17d06239de231fb33d28c8537b3f59fa378d4d704110e21` |
| 25 Size × Prior 1–1 負控制 | `artifacts/french_25_size_prior_1_0_monthly_35f3c3ae.zip` | `35f3c3ae57f65a6ad50148a9c38ad44a75eda1e8b54cea628069b17154c6da33` |
| QQQ／SPY 產品價格快照 | `artifacts/snapshot_20260731_6a7ca6b8.zip` | `d480fb82e712f06aabe0a98461e222344656b87022b8bda2cd7ccaa4c29ae88b` |

QQQ／SPY 只用於 2006-01 後產品機會成本；不以現時股票快照建立歷史成分池。所有經濟
計算只讀封存檔，不在報表建置時更新行情。
