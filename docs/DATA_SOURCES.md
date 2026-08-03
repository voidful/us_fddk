# 資料來源與邊界

| 資料 | 本版用途 | 時間／真實性邊界 |
|---|---|---|
| Yahoo Finance via yfinance | 日 OHLCV、調整收盤、ETF、個股、VIX | 便利但非官方；可能回溯修訂，因此每次凍結快照。 |
| [SEC Company Facts API](https://www.sec.gov/search-filings/edgar-application-programming-interfaces) | 下一階段的申報日可用基本面 | 官方、免 API key；必須遵守 SEC fair-access 與 User-Agent，且只能在 filing date 後使用。 |
| [FINRA OTC Transparency](https://www.finra.org/filing-reporting/otc-transparency/finra-developer-api-service-available-otc-transparency-data) | 下一階段的 ATS／Non-ATS 彙總研究 | 週／月彙總且延遲；不是逐筆內外盤，不能宣稱即時買賣方向。 |
| [French Data Library](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library.html) | 因子定義與未來外部基準 | 官方研究資料會因 CRSP 修訂而重建歷史；其頁面也明示歷史報酬可能改變。 |
| [S&P DJI](https://www.spglobal.com/spdji/en/indices/equity/sp-total-market-index-tmi/)／[IVV 持股頁](https://www.ishares.com/us/products/239726/ishares-core-sp-500-etfIVV) | 當期大型股觀察池的來源脈絡 | 當期成分不是逐期成分；不可回填成歷史母體。 |
| [iShares SHY 官方頁](https://www.ishares.com/us/products/239452/ishares-13-year-treasury-bond-etf) | 雙動量未入選槽位的短天期美債防守資產 | 官方成立日 2002-07-22，足以覆蓋完整 20 年；研究行情仍取自同一份 Yahoo 凍結快照。 |
| Yahoo Finance `^NDX` 價格指數 | v3 的 1985-10-01–2006-07-28 隔離代理期 | 不是 QQQ 總報酬、沒有 SHY；只配衍生零報酬 CASH，不能和主樣本串接或冒充可交易績效。凍結檔為 `snapshot_ndx_proxy_19851001_20060728_4814654a.zip`，archive SHA-256 `ede88d5906411182e454d2e43442e7b5af61c392eab75e4235d5f22d3112f78d`。 |
| [S&P DJI 官方 DJIA 日績效檔](https://www.spglobal.com/spdji/en/indices/equity/dow-jones-industrial-average/) | v11 事前指定的 1971–1988 核心指數敏感度 | 下載前已鎖定直接 Excel URL、唯一 GET、自動解析與共同日期契約；唯一一次 GET 收到 HTTP 403，故沒有原始檔、沒有績效，也不改用鏡像。失敗收據為 `v11_official_dji_data_receipt.json`。 |
| [FRED DGS3MO](https://fred.stlouisfed.org/series/DGS3MO)／[DTB3](https://fred.stlouisfed.org/series/DTB3) | `^NDX` 舊代理期的短債現金敏感度測試 | 聯準會 H.15 的官方日利率；只用前一可得值按實際日數累積。兩種口徑都沒有改變 36.9% 五年滾動勝率，因此不取代原凍結零報酬 CASH 代理。 |
| Yahoo Finance `^GSPC`／`^FTSE`／`^GDAXI`／`^N225`／`^HSI` 價格指數 | v3 下載前凍結的五市場機制驗證 | 五個市場各用本地交易日、1989-01-03–2006-07-28、相同 v3 規則與零報酬 CASH；策略和基準都採價格指數，故可比較但不能冒充含股息總報酬。五份 ZIP 各自保存 panel／archive SHA-256，並綁定協議 SHA-256 `8de1eafd…8117`。 |
| Yahoo Finance `IWF`／`IWD`／`IJR`／`SHY`／`SPY`／`QQQ` | v4 可交易股權風格輪動主樣本 | 凍結 2003-07-01–2026-07-31、六檔全數 5,808 sessions；面板 SHA-256 `e879c128…3da7`，封存檔 SHA-256 `8acdf562…e559`。 |
| Yahoo Finance `^RLG`／`^RLV`／`^SP600`／`^GSPC` | v4 不重疊舊代理資料門檻 | 凍結檔雖涵蓋 1993-07-01–2006-07-28，`^RLG`／`^RLV` 實際只有 2002-09-30 後各 965 sessions，無法支援固定 1996 起算與 273-session 暖機；協議禁止換代號，故判定資料門檻失敗。面板 SHA-256 `a94ed540…f2e6`，封存檔 SHA-256 `fb725b9e…cb59`。 |
| 既有 QQQ／SHY／SPY、`^NDX` 與五市場凍結快照 | v5 三時鐘集成的 post-selection 機制整合 | 沒有把舊資料冒充新樣本；協議在第一次「集成」績效計算前凍結，並以精確 panel/archive SHA-256 鎖定既有七份快照。近期、舊年代與外部市場全部保留，搜尋懲罰增至 6,102。 |

## 快照內容

每個 `snapshot_YYYYMMDD_<hash8>.zip` 只允許六個成員；檔名的短雜湊來自面板內容，同一交易日若上游資料被改寫會另存一份：

```text
open.csv
high.csv
low.csv
close.csv
volume.csv
manifest.json
```

`manifest.json` 記錄：schema、建立時間、資料期間、代號、供應商、調整方式、每個 CSV 的 SHA-256 與資料契約結果。載入器拒絕額外檔案、缺檔與雜湊不符。

## 尚未實作成正式因子的資料

- SEC XBRL 品質／價值：必須處理不同公司 tag、財年、重編與 filing-date 可用性。
- 13F：資料落後，且只看到申報機構的季度長倉快照。
- FINRA ATS／Non-ATS：只有延遲彙總，適合慢速因子，不適合每日方向訊號。
- 期權流：免費彙總量不能辨識開倉／平倉、買方／賣方與多腿組合；沒有完整 OPRA 歷史前不做「聰明錢」宣稱。
