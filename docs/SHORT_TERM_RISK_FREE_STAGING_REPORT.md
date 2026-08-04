# 短線個股第十九輪：官方風險免費日回報暫存報告

證據截至：2026-08-04

## 結論先行

官方 Fama/French 日度 RF 已由過往 2026-05-29 更新至 **2026-06-30**。本輪把固定
2006-08-01 至 2026-07-31 研究期的 RF 覆蓋由「未量化」收窄為：
**5,009/5,031 個 XNYS session**，即
**99.56%**；仍精確欠最後 **22 日**，全部在
2026 年 7 月。

八道真實來源／暫存控制 **8/8**
通過，八項 ZIP、定義、單位、日期、路徑及越權攻擊
**8/8 全部拒收**。
這只證明官方 202606 snapshot 可以安全暫存及精確報缺，不是完整 RF 包，更不是策略成績。

正式狀態沒有虛報提升：正式就緒仍為 **1/18**，逐股 provider package 未收到，完整 RF
包未收到，正式策略運行 **0 次**；短線 Paper 全現金、0 成交、0 持倉，實金動作
**US$0**。

## 新增的真實證據

- 官方 ZIP SHA-256：`39f9ae1d0e9f575024bc23145980ac270cea508fb67e592578b3f4d65f36d006`；
- CRSP data cut：`202606`；
- 官方完整日度檔最後日期：`2026-06-30`；
- 研究期 XNYS session：5,031；
- 已有 RF：5,009；缺失：22；額外：0；
- 單位：原檔百分點只除以 100 一次，輸出 `decimal_simple_daily_return`；
- 缺值政策：不填 0、不複製 6 月、不插值、不以 SHY 或年率直接除 252。

公開下載本身已核實，但本輪沒有捕捉到一份明確的本地研究授權條款；因此授權閘門仍是
false。即使之後官方補齊 7 月，亦須保留來源版本、授權證據、列數與 SHA-256，且與逐股
provider package 的同一 XNYS 日曆逐日對數。

## 精確缺失的 22 個 session

2026-07-01、2026-07-02、2026-07-06、2026-07-07、2026-07-08、2026-07-09、2026-07-10、2026-07-13、2026-07-14、2026-07-15、2026-07-16、2026-07-17、2026-07-20、2026-07-21、2026-07-22、2026-07-23、2026-07-24、2026-07-27、2026-07-28、2026-07-29、2026-07-30、2026-07-31

缺日集中於最後一個月，不能把 99.56% 覆蓋寫成「差不多完整」：超額 Sharpe、PSR／DSR
及每日 active return 必須使用同一完整時間軸，任意補值都會改變固定正式結論。

## 八道 staging 控制

| # | 閘門 | 結果 | 核對內容 |
|---|---|---|---|
| 01 | 協議及第十八輪綁定 | 通過 | Round 19 協議及第十八輪 RF 正式契約 SHA-256 完整 |
| 02 | 官方來源 snapshot | 通過 | 官方 ZIP、唯一 member、202606 data cut 及 SHA-256 一致 |
| 03 | 經濟定義及表頭 | 通過 | simple daily rate 複利至一個月 T-bill；Mkt-RF／SMB／HML／RF |
| 04 | 日期及原始值 | 通過 | 官方日期唯一遞增，四個原始回報有限 |
| 05 | 單位轉換 | 通過 | RF 百分點只除 100 一次；輸出為 decimal simple daily return |
| 06 | XNYS session 對賬 | 通過 | 5009/5031 已覆蓋；精確列出最後 22 個缺失 session |
| 07 | Owner-only 原子暫存 | 通過 | 外部新目錄、5 個固定檔案、0700／0600、無正式 manifest |
| 08 | 決策邊界 | 通過 | 缺 2026 年 7 月及授權證據；正式回測、Paper、實金全部關閉 |

## 八項失敗攻擊

| # | 單一錯誤 | 實際 error code | 結果 |
|---|---|---|---|
| 01 | ZIP 多一個 member | `rf_source_file_set_mismatch` | 拒收 |
| 02 | ZIP member path traversal | `rf_source_archive_unsafe` | 拒收 |
| 03 | 凍結來源 SHA-256 漂移 | `rf_source_hash_mismatch` | 拒收 |
| 04 | 經濟定義或表頭改變 | `rf_source_definition_mismatch` | 拒收 |
| 05 | 日期重複或倒序 | `rf_source_session_invalid` | 拒收 |
| 06 | RF decimal 量級超過 1% | `rf_source_value_invalid` | 拒收 |
| 07 | 輸出位於 repository 內 | `rf_staging_path_invalid` | 拒收 |
| 08 | 缺日仍要求正式 manifest | `rf_decision_boundary_violation` | 拒收 |

## 為何仍不能運行正式回測

暫存目錄故意只輸出 `risk_free_daily_partial.csv` 及 `availability_manifest.json`，不會生成
第十八輪正式驗證器唯一接受的 `risk_free_daily.csv`／`risk_free_manifest.json`。因此
partial 檔不可能被誤當完整輸入。

每日檢查官方下一個 data cut；只有同一經濟定義覆蓋至 2026-07-31、授權證據完成且逐股 provider package 通過後，才可生成正式 RF manifest。 RF 完整只關閉一個資料缺口；逐股 point-in-time、退市、公司行動、
成分公布時間及正式 provider 授權仍須全數通過。全部 18/18 才可只跑一次凍結回測；
經濟與統計門檻再全數通過，才可由下一個真正新增交易日開始不可回填的全現金 Paper。

## 一手來源

- [Kenneth R. French Data Library](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/Data_Library.html)
- [Fama/French factors 及 RF 定義](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/Data_Library/f-f_factors.html)
- [第十九輪暫存協議](SHORT_TERM_RISK_FREE_STAGING_PROTOCOL.md)
- [第十八輪正式事前登記](SHORT_TERM_FORMAL_BACKTEST_PREREGISTRATION.md)

本報告只作研究及專業資訊參考。RF 覆蓋率不是策略勝率、回報或盈利證明；不構成投資
建議、數據授權或盈利保證。
