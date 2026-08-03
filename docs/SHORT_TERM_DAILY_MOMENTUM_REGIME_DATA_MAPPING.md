# French 每日動量環境共振：凍結數據映射 v1

狀態：2026-08-04 在首次下載新日檔前凍結。

## 首次未見資料

| 用途 | 精確來源 | 預期 ZIP member | 凍結狀態 |
|---|---|---|---|
| 10 組 Prior 12–2 每日 value-weighted 報酬 | `https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/10_Portfolios_Prior_12_2_Daily_CSV.zip` | `10_Portfolios_Prior_12_2_Daily.csv` | 未下載、未解析、未計算 |

下載後只准以原始 ZIP SHA-256 前八碼命名：
`artifacts/french_10_prior_12_2_daily_<sha8>.zip`。若 URL、member、marker 或欄序與上表
不符，整輪在策略計算前停止；不得模糊找 marker、重抓另一份、換 TXT 或改檔名救援。

## 既有、已見且只准重用的資料

| 用途 | 檔案 | SHA-256／panel SHA-256 | 邊界 |
|---|---|---|---|
| French daily 市場及 RF | `artifacts/french_ff_factors_daily_af8aec07.zip` | archive `af8aec07d55c98caa15045a77b87455be68cb8847b2ee5bd03bf5c2c8a3f96e2` | 只讀，不重抓 |
| QQQ／SPY 價格 | `artifacts/snapshot_20260731_6a7ca6b8.zip` | archive `d480fb82e712f06aabe0a98461e222344656b87022b8bda2cd7ccaa4c29ae88b`; panel `6a7ca6b83b1570007424daa46b0ff4e8fb4a655d39298a0f4f6d74c3b7ea3a66` | 只取 QQQ、SPY；不得用現時個股池 |

既有資料曾被其他研究查看，只作市場／現金／機會成本 baseline，不能把它稱為第十輪
獨立首次證據。第十輪的 `independent_first_seen_evidence` 僅適用於新的每日 Prior 十分位
ZIP 及在協議凍結後第一次計算的四證據曝險結果。

## 固定 parser 契約

- ZIP 必須只有一個 member，名稱完全等於上表。
- 文字必須包含精確 marker `Value Weight Returns -- Daily`；其下一列為固定十欄 header。
- 日期欄必須為八位 `YYYYMMDD`；由首個數值列讀至第一個非八位日期列即停止。
- 只解析 value-weighted daily table，不讀 equal-weighted table或任何年／月表。
- `-99.99`、`-999`、空白、重複日期、逆序或非有限值一律失敗。
- 原始 ZIP 永久保留，不格式化、不覆寫；機器收據記錄 URL、下載時間、member、bytes、
  SHA-256、首末日、列數、欄序及本映射／協議 SHA-256。

