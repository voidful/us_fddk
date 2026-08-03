# v11 S&P DJI 官方日收盤：下載前資料契約

凍結時間：2026-08-01T18:20:40Z

本契約在首次下載官方 Excel 前凍結。任一條失敗就讓 v11 第 30 門失敗；不得
改用 Yahoo、Stooq、Macrotrends、手工抄值或其他鏡像。

研究協議 SHA-256：
`8611faeec584a78e096df817eeb7ea9a0ce28c71d4c37c4a00c44637ff6644d5`

## 唯一來源與封存

- URL：`https://www.spglobal.com/spdji/en/web-data-downloads/reports/dja-performance-report-daily.xls?force_download=true`
- 來源頁：`https://www.spglobal.com/spdji/en/indices/equity/dow-jones-industrial-average/`
- 只允許一次 HTTP GET；必須是成功回應、非空且能由 Excel reader 開啟。
- 原始檔固定寫入內容定址的
  `artifacts/v11_spdji_djia_daily_<sha8>.xls`，解析結果寫入
  `artifacts/v11_spdji_djia_close_19710205_19881230_<sha8>.csv`。
- 任一符合上述 v11 原始或解析檔樣式的檔案已存在，就在連網前拒絕重新下載、
  覆寫或改寫。
- 收據記錄最終 URL、HTTP content type、下載時間、byte size、原始 SHA-256、
  工作表、解析欄位／列位置、CSV SHA-256 與研究協議雜湊。

## 唯一可接受的自動解析

1. 逐一以 `header=None` 讀取所有工作表，不預先假設表名或標題列。
2. 在每個工作表逐列尋找同一列中的日期標題與 DJIA 價格／收盤／index level
   標題。日期標題經去空白、小寫後必須是 `date` 或含 `date`；數值標題必須含
   `close`、`index level`、`djia` 或 `dow jones industrial average` 之一。
3. 從該標題列下一列開始，只保留日期可唯一轉成日曆日、數值可轉為有限正數的
   兩欄。每個候選先依日期去重；同日若有不同值即失敗，不得任選。
4. 候選必須涵蓋 1971-02-05–1988-12-30 且該區間至少 4,300 筆。若零個或多於
   一個候選符合，即失敗；不得人工指定較好看的工作表或欄位。
5. 解析 CSV 只含 `Date,DJIA`，日期遞增、唯一，UTF-8、LF、日期 `%Y-%m-%d`、
   數值 `%.10g`；只保存 1971-02-05–1988-12-30。

## 價格與共同日期硬檢查

1. 解析後第一筆必須不晚於 1971-02-05、最後一筆不早於 1988-12-30；切片後
   首尾必須正好為這兩日，至少 4,300 筆、無缺值、所有 level 為有限正數。
2. 單日絕對報酬不得超過 35%；1987 崩盤可通過此上限，但更大的跳變視為資料
   或解析錯誤。
3. 成長資料只能載入既有
   `artifacts/snapshot_v9_ixic_19710205_19881230_76bc29b6.zip`；panel
   `76bc29b61c480e8c44032e4aeaea801e9ea97a1aebceb758bda84df8a8b7d2c9`，archive
   `b845aecd3175584f8dc40e0db8e93ec9427e2a9f491f0824ec7264f6cda9eb22`。
4. 只取 DJIA 與 `^IXIC` 日期交集；不補值、插值、挪動日期或串接別的序列。
5. 共同日第一筆必須是 1971-02-05、最後一筆 1988-12-30，至少 4,300 筆；
   1973-01-03 以前共同暖機至少 252 筆。
6. 共同面板必須含 1973-01-03、1980-12-31、1981-01-02、1988-12-30。
7. 下載後 data receipt 必須完整記錄原始、解析、既有 IXIC、共同面板與所有
   契約結果；任何失敗都記錄 `paper_eligible=false` 且不產生 v11 績效。
