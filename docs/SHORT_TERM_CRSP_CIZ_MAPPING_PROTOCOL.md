# 短線個股第十三輪：CRSP CIZ 欄位映射與拒絕推算協議 v1.0

凍結時間：2026-08-03T21:21:26Z

狀態：`frozen_before_ciz_adapter_implementation`

## 研究問題

在沒有 WRDS 登入、沒有取得任何受限制原始列、沒有改動既有短線 v1 選股規則的前提
下，能否把 CRSP Flat File Format 2.0（CIZ）的公開欄位語義，轉成第九輪已凍結的八份
point-in-time／退市賬本，同時拒絕以生效日冒充公布時間、用現時代號倒填歷史、把調整
價當原始價，或把退市回報在日檔的儲存日期當成退出事件日期？

本輪只研究轉換層，不是正式供應商驗收或策略回測。無論合成控制結果如何，真實數據
就緒度仍以實際數據包稽核為準；沒有合法樣本時固定為 1/20，正式逐股回測為 0，短線
Paper 維持全現金，實金動作為 US$0。

## 官方文件基礎與可證明邊界

- WRDS 已說明 CIZ（Flat File Format 2.0）取代 SIZ；legacy SIZ 最後一批為 2024 年
  12 月數據。因此新轉換器只接受 `CIZ_FF2`，不把舊 `dsf`／`msenames` schema 當現行
  輸入。
- WRDS 2026 年 CIZ-to-SIZ 公開 macro 使用 `crsp.dsf_v2`，以 `PERMNO` 及
  `SecInfoStartDt <= DlyCalDt <= SecInfoEndDt` 連接 `StkSecurityInfoHist`，並列出
  `DlyCalDt`、`DlyRet`、`DlyPrc`、`DlyVol`、`CUSIP`、`PrimaryExch` 及證券類型欄位。
- 2026 年 CIZ guide 列出 `StkSecurityInfoHist`、`StkDlySecurityData`、
  `StkDistributions`、`StkDelists` 及 `StkIndMembership`。`MbrStartDt`／`MbrEndDt`
  是成分在籍日期，公開表格沒有逐次 announcement timestamp。
- `DelistingDt` 是最後價格日期；`DelDlyDt` 是退市回報在日檔的儲存日期，慣例為
  退市後下一交易日。兩者不可互換。`DelRetMissType` 明確容許退市回報缺失，因此缺失
  `DelRet` 不得自動填 0。
- 公開指南只證明欄位存在及定義，不證明使用者有授權、WRDS catalog 可查、S&P 500
  精確 `INDNO`、20 年覆蓋或缺值比例。所有需登入頁面維持 `unverified_login_required`。

主要來源：

- [WRDS：Changes to CRSP Data](https://wrds-www.wharton.upenn.edu/pages/data-announcements/changes-to-crsp-data/)
- [WRDS：CRSP CIZtoSIZ macro](https://wrds-www.wharton.upenn.edu/pages/wrds-research/macros/crsp-ciztosiz-macro/)
- [CRSP US Stock Databases Guide for Flat File Format 2.0](https://index-website-frontend-prd.mif0286.eas.morningstar.com/docs/guide/crsp-us-stock-databases-guide-for-flat-file-format-2-0?isRdp=true)

## 固定 CIZ 匯出包

轉換器只讀使用者合法提供的本地目錄。目錄必須只有 `ciz_manifest.json` 及以下十個
UTF-8 CSV；每個檔案的列數及 SHA-256 必須在 manifest 對數。額外或缺少檔案均拒收。

1. `stk_security_info_hist.csv`
2. `stk_ind_membership.csv`
3. `stk_dly_security_data.csv`
4. `stk_distributions.csv`
5. `stk_delists.csv`
6. `trading_calendar.csv`
7. `security_info_availability.csv`
8. `membership_announcements.csv`
9. `corporate_action_overlay.csv`
10. `exit_terms.csv`

`ciz_manifest.json` 固定要求：

- `schema_version=1`、`source_format=CIZ_FF2`、`provider`、`provider_product`；
- 巢狀 `license_attestation` 明示本地研究授權、原始列能否再分發、帶 UTC offset 的
  `attested_at` 及可追溯 `reference`；
- 帶 offset 的 `exported_at`、`first_imported_at`，前者不得較遲；
- `as_of_date`、`sp500_indno`、`price_basis=raw_unadjusted_ohlc`；
- `membership_date_semantics=inclusive_source_to_half_open_ledger`；
- `delist_storage_semantics=DelistingDt_last_price_DelDlyDt_storage_only`；
- 精確十檔收據及 `adapter_version=round13-crsp-ciz-v1`。

## 直接、派生、外加及禁止欄位

| 目標賬本 | CIZ／外加來源 | 分類 | 固定處理 |
|---|---|---|---|
| `security_id` | `PERMNO` | 直接 | 前綴 `CRSP-PERMNO-`；不得用 ticker |
| `company_id` | `PERMCO` | 直接 | 前綴 `CRSP-PERMCO-` |
| 歷史代號／上市地 | `Ticker`、`PrimaryExch`、`CUSIP`、`SecInfoStartDt/EndDt` | 直接＋區間派生 | CIZ inclusive end 轉 ledger half-open end |
| identifier／分類 `known_at` | `security_info_availability.csv` | 外加必需 | 不得用 `SecInfoStartDt`、匯出日或今日倒填 |
| 成分區間 | `PERMNO`、`INDNO`、`MbrStartDt/EndDt` | 直接＋區間派生 | 只接受 manifest 固定 `sp500_indno` |
| 成分 `announced_at` | `membership_announcements.csv` | 外加必需 | 必須有獨立證據，且嚴格早於生效日紐約午夜 |
| raw OHLCV | `DlyOpen/High/Low/Close/Vol` | 直接 | `price_basis` 非 raw 即整包拒收；不可套 `DlyCumFacPr` |
| 總回報因子 | `1 + DlyRet` | 決定性派生 | 缺失旗標非 NA 或非有限值即拒收；不可把缺值填 1 |
| 派息／拆細 | `StkDistributions`＋`corporate_action_overlay.csv` | 直接＋外加正規化 | 公布時間、事件類型及條款須有證據並與 CIZ 金額／因子對數 |
| 最後交易日 | `DelistingDt` | 直接 | 只作最後價格日期；不得使用 `DelDlyDt` |
| 退市儲存日 | `DelDlyDt` | 直接但非事件 | 必須晚於 `DelistingDt`；只作 provenance 檢查 |
| 退市回報 | `DelRet` | 直接 | 有值必須有限且不低於 -1；沒有值不得補 0 |
| 缺失退出代價 | `exit_terms.csv` | 外加必需 | 只接受可追溯正現金代價或已存在 master 的 successor＋正換股比率 |

`PrimaryExch` 只按固定表轉為 `XNYS`／`XNAS`；未知或不合資格上市地拒收。
`USIncFlg=Y`、`SecurityType=EQTY`、`SecuritySubType=COM` 及普通股 share type 才可進
master。歷史分類固定使用 CIZ ICB；若 ICB 欄位空白，不以今日 GICS／SIC 補洞。

## 固定轉換後驗證

轉換成功後必須立即以第九輪同一 `audit_point_in_time_bundle` 驗證八份輸出；adapter
成功不等於 20/20，20/20 亦只授權運行一次凍結 v1 正式回測，不授權 Paper。

合成控制使用 2026-07-29 至 2026-07-31、每日兩隻成分，只證明映射及 validator 的
機械行為。它不得寫入真實 readiness，也不得保存或公開任何供應商列。

## 事前凍結十二項攻擊

| # | 單一攻擊 | 必須拒收原因 |
|---|---|---|
| 1 | 缺少 `membership_announcements.csv` | 不可證明成分公布時間 |
| 2 | `AnnouncedAt` 等於 `MbrStartDt` 午夜 | 疑似用生效日冒充公布時間 |
| 3 | 缺少 security-info availability 對數 | identifier／分類 `known_at` 不可推算 |
| 4 | 把現時整列 security info 倒填前一期 | 連續完全相同歷史列／provenance 漂移 |
| 5 | `price_basis=adjusted_ohlc` | 不能用調整價作 US$5 及流動性篩選 |
| 6 | `DelDlyDt` 等於或早於 `DelistingDt` | 儲存日／最後價格日時序矛盾 |
| 7 | `DelRet` 缺失且 `exit_terms` 無經濟條款 | 永久退出代價缺失 |
| 8 | successor PERMNO 不在永久主檔 | 換股代價不可對數 |
| 9 | 授權聲明缺必要欄位 | 未證明合法本地研究用途 |
| 10 | `source_format` 或 schema 版本漂移 | 未經凍結的產品／欄位集合 |
| 11 | distribution 缺 corporate-action overlay | 公布時間／事件類型不可推算 |
| 12 | security info `KnownAt` 晚於生效日 | identifier／分類含前視資訊 |

控制包必須轉換並通過 20/20，十二項攻擊必須 12/12 在 adapter 或下游 ledger gate
被拒收；任何誤收即判本輪失敗。

## 停止與升格規則

- adapter 只讀本地匯出，不連線登入 WRDS、不下載付費數據、不公開原始列。
- 沒有合法 CIZ 樣本時，正式 readiness 保持 1/20；合成 20/20 不得加分。
- 樣本即使通過，也只可驗證 mapping；正式包仍須覆蓋 2006-08-01 至 2026-07-31、
  每日 495–510 隻、價格／停牌至少 99.5%，並通過完整 20/20。
- 正式數據 20/20 後，才可按原封不動 v1 運行一次回測，並對照 QQQ、SPY、逐期成分
  等權、同股漂移，扣 10／25／50 bps，完成分段、危機、Newey-West、PSR、全專案
  DSR 及 PBO。
- 只有經濟、統計、數據全部通過，才可由全現金建立不回填的短線 Paper；Paper 仍須
  累積 252 個新增交易日及 12 次完整輪選，才可再審，不等於實金授權或盈利保證。
