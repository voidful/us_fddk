# 短線個股第十九輪：官方風險免費日回報暫存協議 v1.0

凍結時間：2026-08-04T00:57:44Z

狀態：`frozen_after_official_202606_source_inspection_before_staging_implementation`

## 目的與證據邊界

第十八輪已在任何正式策略結果出現前固定：2006-08-01 至 2026-07-31 的每個 XNYS
session 必須有美元一個月國庫券簡單日回報，超額 Sharpe／PSR／DSR 不得用 0、SHY、
年率直接除 252 或事後挑選的替代序列。本輪不更改該規則，只把 Kenneth R. French
Data Library 的官方日度 `RF` 下載檔轉成可重現、fail-closed 的暫存入口。

本協議在查看官方 202606 ZIP 及其最後日期後才凍結，因此不是獨立 first-seen 數據
證據；官方來源 SHA-256、最後日期及已知 2026 年 7 月缺口均如實預先寫入。它仍早於
任何暫存程式、輸出、網站摘要或測試。本輪不計算策略回報，不改第十八輪 baseline、
成本、統計、一次性 run ID 或 Paper 門檻。

## 固定官方來源

- 下載頁：`https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/Data_Library.html`；
- 說明頁：`https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/Data_Library/f-f_factors.html`；
- ZIP：`https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/F-F_Research_Data_Factors_daily_CSV.zip`；
- 本輪已見 ZIP SHA-256：`39f9ae1d0e9f575024bc23145980ac270cea508fb67e592578b3f4d65f36d006`；
- 唯一 member：`F-F_Research_Data_Factors_daily.csv`；
- CRSP data cut：`202606`；
- 官方日度覆蓋最後日期：`2026-06-30`；
- 固定研究終點：`2026-07-31`。

官方檔案文字將 T-bill return 定義為一個簡單日率，在該月交易日複利至一個月 T-bill
回報；截至 2024-05 的一個月 T-bill 來自 Ibbotson Associates，由 2024-06 起來自
ICE BofA US 1-Month Treasury Bill Index。下載頁目前公開顯示日度數據截至 2026-06-30。

## 固定轉換與 session 對賬

1. ZIP 必須只有上述單一普通檔案；拒收 path traversal、symlink、encrypted member、
   多檔或非 UTF-8／ASCII 文字；
2. 前言必須同時包含 `202606 CRSP database`、simple daily rate 及 one-month T-bill
   經濟定義；欄位必須精確為空白日期欄、`Mkt-RF,SMB,HML,RF`；
3. 只讀取八位數日期資料列；日期必須嚴格遞增、唯一，四個回報必須有限；
4. `RF` 原檔為百分點，只可除以 100 一次轉成
   `decimal_simple_daily_return`；轉換後必須 `>-1` 且絕對值不大於 1%；
5. 研究 session 固定由 `exchange_calendars` 的 XNYS 產生，範圍
   2006-08-01 至 2026-07-31，預期 5,031 個 session；
6. 輸出逐一列明 available、missing 及 extra session；不得前向填補、以 0 補值、
   複製 6 月 RF、插值或用另一來源只補有利日期；
7. 本輪已知 2026 年 7 月共有 22 個 XNYS session 尚未在 202606 ZIP 出現；正式
   `risk_free_manifest.json` 因此不得生成。

## 固定暫存輸出

程式只可建立新的 repository 外 owner-only 目錄，且不得覆寫現有目錄。未完整時只含：

- `source_snapshot.zip`：原始官方 bytes；
- `risk_free_daily_partial.csv`：已覆蓋 session 的 decimal 日回報及可追溯 record ID；
- `missing_sessions.csv`：精確缺失 XNYS 日期；
- `availability_manifest.json`：來源 URL／SHA、data cut、轉換、行數、覆蓋及狀態；
- `staging_receipt.json`：上述檔案 SHA-256、權限、協議及第十八輪協議綁定。

只在下列條件同時成立時，未來版本才可另行原子生成第十八輪所需的
`risk_free_manifest.json` 及 `risk_free_daily.csv`：來源經濟定義不變、5,031/5,031
session 一對一、沒有 extra、單位／值／record ID 全通過、使用者提供可稽核的本地研究
授權聲明，而且正式 provider package 亦使用同一研究日曆。完整前的 partial 檔名不能被
正式驗證器接受。

## 固定八道 staging 控制

1. 本協議及第十八輪事前登記雜湊完整；
2. 官方 URL、ZIP SHA-256、唯一 member 及 data cut 一致；
3. 經濟定義及表頭一致；
4. 日期唯一、嚴格遞增且原始值有限；
5. percent-to-decimal 只轉一次且數值合理；
6. 5,031 個 XNYS session 的 available／missing／extra 集合精確；
7. 外部輸出 owner-only、無 symlink、收據與檔案 SHA-256 對數；
8. incomplete 狀態不能授權正式回測、Paper 或實金，亦不能生成正式 RF manifest。

## 固定八項失敗攻擊

| # | 單一攻擊 | 必須拒收的 error code |
|---|---|---|
| 01 | ZIP 多一個 member | `rf_source_file_set_mismatch` |
| 02 | ZIP member path traversal | `rf_source_archive_unsafe` |
| 03 | 官方 ZIP SHA-256 漂移而未另存新 snapshot | `rf_source_hash_mismatch` |
| 04 | 前言或表頭改變 | `rf_source_definition_mismatch` |
| 05 | 日期重複或倒序 | `rf_source_session_invalid` |
| 06 | RF 非有限或 decimal 轉換後超過 1% | `rf_source_value_invalid` |
| 07 | 輸出已存在、在 repository 內或不是 owner-only | `rf_staging_path_invalid` |
| 08 | 缺 2026 年 7 月仍要求正式 manifest／Paper 授權 | `rf_decision_boundary_violation` |

## 停止規則

本輪在真實 202606 source staging、八道控制、八項攻擊、缺日報告及公開摘要完成後停止。
若官方日度檔仍未覆蓋 2026-07-31，只可每日檢查新 data cut 或由同一合格 provider 在看
策略結果前交付同一經濟定義的完整序列；不得拼接結果導向替代。RF 完整亦不代表逐股
provider package 通過。正式回測維持 0 次，短線 Paper 全現金，實金動作 US$0。

本協議只作研究及專業資訊參考，不構成投資建議、數據授權、盈利證明或盈利保證。
