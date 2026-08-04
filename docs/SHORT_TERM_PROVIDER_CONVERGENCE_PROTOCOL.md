# 短線個股第 20 輪：CRSP／WRDS 供應商收斂與拒絕替代協議 v1.0

凍結時間：2026-08-04T01:39:29Z

狀態：`frozen_after_official_guide_inspection_before_convergence_implementation`

## 目的與研究邊界

第 19 輪已把官方 Fama／French 日度 RF 收窄至 5,009／5,031 個 XNYS session，
但逐股 point-in-time／退市供應商包仍為 0。本輪不搜尋新策略、不改短線 v1、
不運行回測，也不把相近的風險免費序列冒充凍結輸入。本輪只回答：

1. 最新 CRSP Stock CIZ 指南可直接證明十份交接輸入中的哪些能力；
2. 同一 CRSP／WRDS 授權若另含 US Treasury Database，可否同時關閉正式 RF 缺口；
3. 哪些欄位仍須供應商回覆或獨立 evidence overlay，不能由生效日或相近年期推算；
4. 如何每日偵測官方指南換版，而不因文件更新自動提高真實 readiness。

本協議保留第 18 輪一次性正式回測事前登記、US$1,000、四個 baseline、
10／25／50 bps、公司行動單次入賬、6,208 trials DSR、四路十段 PBO、
全現金 Paper 及實金 US$0。任何本輪結果均不得修改上述規則。

## 凍結的參考專案版本

- `appr1ciat1/tst_wocker@3372aa088328700feafeeb07c72ab832ea2d3ecb`；
- `appr1ciat1/tw-block-warrant@37463c54796ba36f4aac262519ea7fc2ef797de6`；
- `appr1ciat1/tst_wocker_filter_lab@06c87b7a1735877c9ccbab3a339c1742814a5058`。

只保留其研究紀律：訊號／研究／Paper 分層、D+1、同次 baseline、
同池配對、凍結快照、數據修訂失效、雜訊帶及負結果。不得複製台股參數、
權證／鉅額交易 proxy、headline 回報或未標示可重用授權的程式碼。

## 凍結的一手指南收據

### CRSP US Stock CIZ

- 官方落地頁：`https://indexes.morningstar.com/docs/guide/crsp-us-stock-databases-guide-for-flat-file-format-2-0?isRdp=true`；
- 官方 PDF：`https://indexes.morningstar.com/api/docs/6a70fc12f1246457e16fbfad`；
- 生效日：`2026-07-27`；
- PDF SHA-256：`e42f452207d4a30ef05de542a2dac9522f240100cec99a0309b1b3ab20699ec6`；
- 頁數：97；
- 同一 URL 連續下載兩次位元完全相同。

### CRSP US Treasury

- 官方落地頁：`https://indexes.morningstar.com/docs/guide/crsp-us-treasury-database-guide?isRdp=true`；
- 官方 PDF：`https://indexes.morningstar.com/api/docs/6a454eb24453862570c90c07`；
- 生效日：`2026-06-30`；
- PDF SHA-256：`d256ae7633049eca9d4c9385913f599c7bece7c3c508c39bf3b8afa18c479781`；
- 頁數：46；
- 同一 URL 連續下載兩次位元完全相同。

PDF 只在本地暫存作一手文件核對，不加入 repository、網站或 Action artifact；
公開證據只保留 URL、版本、頁數、SHA-256、欄位摘要及拒絕推算結論。

## 事前固定的能力判讀

### Stock CIZ 可由指南直接證明

| 交接輸入 | 官方表／欄位 | 判讀 |
|---|---|---|
| `stk_security_info_hist.csv` | `StkSecurityInfoHist`；`PERMNO`、`PERMCO`、`SecInfoStartDt`／`EndDt`、歷史 ticker／交易所／股份類別／行業 | `direct_documented` |
| `stk_ind_membership.csv` | `StkIndMembership`；`PERMNO`、`INDNO`、`MbrStartDt`／`EndDt`、`MbrFlg` | `direct_effective_interval_only` |
| `stk_dly_security_data.csv` | `StkDlySecurityData`／`dsf_v2`；raw 日價、成交量、回報、停牌／交易狀態 | `direct_documented` |
| `stk_distributions.csv` | `StkDistributions`；除權息、宣派、記錄、派付日、現金／股份比率及 successor ID | `direct_documented` |
| `stk_delists.csv` | `StkDelists`；退出日、價格／金額、`DelRet`、missing type、successor PERMNO／PERMCO、`DelDlyDt` | `direct_documented` |

上述只證明資料字典存在，不證明使用者已有訂閱、實際交付完整、S&P 500 的 `INDNO`
已確認，或 2006–2026 每一列通過驗證。

### 仍不可由 CIZ 指南推算

| 交接輸入 | 固定狀態 | 不可替代原因 |
|---|---|---|
| `trading_calendar.csv` | `provider_or_evidence_overlay_required` | 指南不是本研究 XNYS 開收市時間及 session 交付 |
| `security_info_availability.csv` | `evidence_overlay_required` | `SecInfoStartDt` 是有效區間，不是 `KnownAt`／資料可知時間 |
| `membership_announcements.csv` | `evidence_overlay_required` | `MbrStartDt`／`MbrEndDt` 是成分生效區間；指南沒有公布時間 |
| `corporate_action_overlay.csv` | `provider_or_evidence_overlay_required` | CIZ 有事件日期／條款，但正式合約仍須完整 `AnnouncedAt` 及證據 reference |
| `exit_terms.csv` | `provider_or_evidence_overlay_required` | `DelRetMissType` 只標記缺失；缺失退出代價不得填 0 或事後猜測 |

`MbrStartDt` 不得填入 `AnnouncedAt`；`SecInfoStartDt` 不得填入 `KnownAt`；
資料 cut、檔案建立時間或下載時間亦不得冒充逐列可知時間。

## Treasury 與正式 RF 的拒絕替代規則

最新版 Treasury 指南證明：

- 個別 Treasury bill 有 `TDRETNUA` 日度未調整回報；
- `TFZ_DLY_RF2` 是 4／13／26 週風險免費日序列，4 週 `TREASNOX=2000061`；
- 精確 1 個月／3 個月風險免費系列 `TREASNOX=2000001／2000002` 在
  `TFZ_MTH_RF`，是月度連續複利收益率，不是本協議要求的日度簡單回報。

因此固定判斷為 `same_provider_mapping_candidate_not_formal_rf`。以下均不得自動生成
`risk_free_daily.csv`／`risk_free_manifest.json`：

1. 以 4 週日序列冒充 1 個月日序列；
2. 把 1 個月年率直接除以 252；
3. 事後選每日最接近 30 日到期的票據而沒有事前、可重播的選券規則；
4. 把 FRED `DGS1MO`、SHY、SOFR 或零回報拼接到 2026 年 7 月；
5. 混合來源卻沒有逐列來源 ID、授權及同日曆對數。

只有供應商提供與第 18 輪 `US_1M_TBILL_DAILY_RETURN` 相同經濟定義的日度簡單回報，
或另立於任何供應商列之前、且不改正式經濟定義的可重播映射並通過獨立驗證，
才可進入正式 RF 驗收。本輪不建立該映射。

## 十二道固定控制

1. 本協議 SHA-256 及凍結收據完整；
2. 三個台股參考 commit 精確綁定；
3. 兩個官方落地頁標題及 effective date 精確；
4. 兩份 PDF URL、SHA-256、頁數及重下載穩定；
5. `StkSecurityInfoHist` 永久 ID／歷史區間欄位完整；
6. `StkIndMembership` 只有生效區間，不宣稱公布時間；
7. raw 日線／交易狀態能力存在；
8. distributions 的 declare／record／pay-date 及 successor 能力存在；
9. delists 的 `DelRet`、missing type、successor 及 storage date 能力存在；
10. 五份 evidence overlay 缺口逐份保留，不由指南推算；
11. Treasury 4 週日序列與 1 個月月序列語義分開，正式 RF 保持未通過；
12. 真實 provider 0、正式回測 0、Paper 全現金、實金 US$0。

## 十二項固定攻擊

| # | 單一錯誤 | 指定拒收代碼 |
|---|---|---|
| 01 | 協議 SHA 漂移 | `convergence_protocol_mismatch` |
| 02 | 參考 commit 漂移 | `reference_commit_mismatch` |
| 03 | 指南 effective date 漂移 | `guide_version_mismatch` |
| 04 | PDF hash 漂移 | `guide_hash_mismatch` |
| 05 | PDF 頁數或 URL 漂移 | `guide_identity_mismatch` |
| 06 | 少一個 CIZ 直接表 | `stock_capability_set_mismatch` |
| 07 | `MbrStartDt` 冒充 `AnnouncedAt` | `membership_announcement_substitution` |
| 08 | `SecInfoStartDt` 冒充 `KnownAt` | `security_known_at_substitution` |
| 09 | 缺失 `DelRet` 填 0 | `delist_economics_imputation` |
| 10 | 4 週日序列冒充 1 個月日序列 | `risk_free_tenor_substitution` |
| 11 | 1 個月年率直接除以 252 | `risk_free_unit_substitution` |
| 12 | 文件通過後提升真實 readiness／啟動 Paper | `convergence_decision_boundary_violation` |

每項攻擊只保留一個語義錯誤，不能以 generic hash 失敗遮蓋。本輪合成 12/12 只可證明
指南證據驗證器 fail closed；不代表供應商包、RF、策略或 Paper 通過。

## 預定輸出與停止規則

- `artifacts/short_term_provider_convergence_protocol_receipt.json`；
- `artifacts/short_term_provider_convergence_validation.json`；
- `artifacts/short_term_provider_guide_probe.json`；
- `site/data/short-term-provider-convergence.json`；
- `site/data/short-term-provider-guide-probe.json`；
- `docs/SHORT_TERM_PROVIDER_CONVERGENCE_REPORT.md`。

每日只探測官方落地頁與 PDF 身份；新版本只標記 `unqualified_new_guide`，不得自行改協議、
能力矩陣或 readiness。正式回測仍須 provider-mode 16/16、point-in-time 20/20、
execution extension 16/16、正式 RF 完整及第 18 輪 18/18 全數通過，才可只運行一次。
其後經濟／統計門檻再全過，短線 Paper 才由下一個新增交易日的全現金開始，不能回填。

本協議只作研究及專業資訊參考，不構成供應商背書、投資建議或盈利保證。
