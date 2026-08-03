# French prior-return 月資料映射 v1

凍結日期：2026-08-03

## 官方來源及首次下載網址

根網址：`https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/`

| 角色 | ZIP | 預期月表／欄位 |
|---|---|---|
| short-term prior-return 十分位 | `10_Portfolios_Prior_1_0_CSV.zip` | `Average Value Weighted Returns -- Monthly`、`Average Equal Weighted Returns -- Monthly`；10 欄，由 `Lo PRIOR` 至 `Hi PRIOR` |
| long-term momentum 十分位 | `10_Portfolios_Prior_12_2_CSV.zip` | 同上兩個月表；10 欄，由 `Lo PRIOR` 至 `Hi PRIOR` |
| Fama/French 三因素及 RF | `F-F_Research_Data_Factors_CSV.zip` | 月表含 `Mkt-RF`、`SMB`、`HML`、`RF` |
| Momentum 因子 | `F-F_Momentum_Factor_CSV.zip` | 月表含 `Mom` |
| Short-Term Reversal 因子 | `F-F_ST_Reversal_Factor_CSV.zip` | 月表含 `ST_Rev` |

詳細方法頁：

- `Data_Library/det_10_port_form_pr_1_0.html`
- `Data_Library/det_10_port_form_pr_12_2.html`
- `Data_Library/det_st_rev_factor.html`

## 日期及單位

- 日期鍵必須為六位 `YYYYMM`，嚴格遞增且不得重複。
- short-term prior-return 正式原始範圍預期不晚於 1926-02 開始，首次下載版本最後完整月
  必須位於 2026-05 發布版。
- 五檔共同正式研究範圍固定為 1963-01 至共同最後完整月。
- 原始百分比除以 100 轉成小數回報；不連續複利化因子本身。
- `-99.99`、`-999` 只可轉為缺值作契約檢查，不得補值；正式期任一必需欄缺值即停止。

## 表段解析

- 十分位 ZIP 必須同時解析 value-weighted 及 equal-weighted 月表；年度表及其他統計表不進
  正式計算。
- 欄名會先去除首尾空白，但不得按結果重新排序；順序必須由最低 prior-return 到最高。
- 因素 ZIP 只解析第一個完整月表；遇到年度日期或說明文字即停止。
- 每個 ZIP 必須只含一個 CSV；若成員數或編碼不符即停止。

## 時序與口徑

- 官方 short-term portfolio 的月 t 成分在 t-1 月底以 prior (1–1) return 形成；月 t 回報
  已是下一期結果，程式不得再 shift 或用月 t 排名。
- 官方 long-term momentum 的月 t 成分在 t-1 月底以 prior (2–12) return 形成。
- 市場總回報定義為 `Mkt-RF + RF`。
- value-weighted `Hi PRIOR` 是唯一主要候選；equal-weighted 只作敏感度。

## 能證明及不能證明的事項

這些 CRSP 學術組合每期按當時可用資料重組，較現時成分倒推更適合檢查美股短窗排名
機制；Data Library 亦明示歷史會隨 CRSP 修訂而重建。因此首次 ZIP 必須以 SHA-256
封存，後續更新只可另立版本。

ZIP 不提供逐股名單、退市事件、公司行動或實際換手，所以不能證明既有個股 v1 可落盤，
亦不能建立 Paper。環境內目前沒有 WRDS／CRSP、Norgate、Sharadar、Polygon、Tiingo、
SimFin 或同級授權路徑；這項資格稽核只記錄「不可用」，不要求或暴露任何憑證值。
