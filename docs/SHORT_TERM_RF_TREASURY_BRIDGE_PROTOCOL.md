# 短線個股第三十七輪：Treasury RF bridge 診斷協議 v1.0

狀態：**協議先於首次 Treasury remote observation 凍結；本輪只作差異診斷，不回填正式 RF。**

## 目的與邊界

第十九輪 frozen French／ICE BofA 日度 RF source 的 data cut 為 202606，XNYS 對賬到
2026-07-31 尚欠 22 個 session。本輪只檢查 U.S. Treasury Daily Treasury Bill Rates
XML 是否能觀察到同一批日期，並量化 4-week coupon-equivalent 轉換成 proxy daily
simple return 後，與 frozen French RF 的定義差異。

Treasury proxy **不是** French／ICE BofA 1-month Treasury Bill Index；因此不會寫入
正式 RF manifest、不會覆蓋 frozen RF、不會增加正式 readiness、回測或 Paper。任何
coverage 22/22 只代表來源有資料，不能代表經濟定義、授權、as-known 或 row-level
provenance 通過。

## 固定輸入

- 官方來源 URL：
  `https://home.treasury.gov/resource-center/data-chart-center/interest-rates/pages/xml?data=daily_treasury_bill_rates&field_tdr_date_value=2026`
- 官方來源 host：`home.treasury.gov`，只接受 HTTPS 且 final URL host 不漂移。
- XML 欄位：`INDEX_DATE` 及 `ROUND_B1_YIELD_4WK_2`（coupon-equivalent，百分點）。
- proxy conversion：`(1 + annual_percent / 100) ** (1 / 365) - 1`；只作可重播比較，
  不宣稱為 French RF 的等價轉換。
- 目標缺日（固定 22 個）：2026-07-01、07-02、07-06、07-07、07-08、07-09、
  07-10、07-13、07-14、07-15、07-16、07-17、07-20、07-21、07-22、07-23、
  07-24、07-27、07-28、07-29、07-30、07-31。
- French RF comparison input：`artifacts/french_ff_factors_daily_39f9ae1d.zip`，
  只讀、只保存其 frozen SHA，不重下載、不修改。

## 輸出與停止規則

Probe 可把 XML 讀入記憶體，但不得把 XML／ZIP 原始 bytes 寫入 repository。只保存：

- final URL、HTTP、content type、body bytes、body SHA-256；
- 22 個目標日期的 derived 4-week yield 及 proxy daily simple；
- 與 frozen French RF 的 overlap count、平均／最大絕對差、相關係數及定義差異標籤。

任何 host、status、content type、XML、日期、數值、重複、缺日、French hash 或協議
漂移均 fail closed。Probe 失敗時保留 `formal_rf_substitute=false`、formal backtest
未授權、Paper `all_cash` 及實金 US$0。

## 固定決策邊界

每次結果必須包含並驗證：

- `treasury_bridge_observed` 只代表官方 rows 可讀；
- `formal_rf_substitute=false`；
- `formal_backtest_authorized=false`；
- `paper_authorized=false`、`paper_state=all_cash`；
- `real_money_action_usd=0`；
- 不產生 strategy run、不重選參數、不改寫 frozen readiness。

只有取得合格 provider package、明確授權及與正式協議一致的完整 RF manifest 後，才可
另行凍結新協議；本輪結果不能用作正式回測或交易建議。
