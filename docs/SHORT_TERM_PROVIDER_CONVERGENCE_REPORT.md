# 短線個股第二十輪：CRSP／WRDS 供應商收斂報告

證據截至：2026-08-04

## 結論先行

最新官方 CRSP Stock CIZ 指南可把十份固定交接輸入收窄成兩組：
**5/10 份有直接資料字典能力**，
另 **5/10 份仍須供應商或獨立
evidence overlay**。這不是「數據已齊」：公開指南沒有逐列 `KnownAt`、成分公布時間、完整
XNYS 開收市日曆，也不能替缺失退市回報補 0。

CRSP Treasury 是同一供應商授權下值得核對的映射候選，但最新版指南的日度 RF 是
4／13／26 週；精確 1 個月系列只在月度表，與第十八輪凍結的「1 個月國庫券日度簡單
回報」並不相同。因此狀態固定為
`same_provider_mapping_candidate_not_formal_rf`，不生成正式 RF manifest。

十二道指南、欄位、年期、單位及決策控制
**12/12 通過**；十二項單一
錯誤攻擊 **12/12 全部拒收**。
它們只證明 validator 會 fail closed，不是策略回測。真實正式就緒仍為 **1/18**，provider
package 0、完整 RF 0、正式策略運行 **0 次**；短線 Paper 全現金、0 成交、0 持倉，實金
動作 **US$0**。

## 最新一手指南身份

| 指南 | Effective date | 頁數 | PDF SHA-256 |
|---|---:|---:|---|
| CRSP US Stock CIZ | 2026-07-27 | 97 | `e42f452207d4a30ef05de542a2dac9522f240100cec99a0309b1b3ab20699ec6` |
| CRSP US Treasury | 2026-06-30 | 46 | `d256ae7633049eca9d4c9385913f599c7bece7c3c508c39bf3b8afa18c479781` |

網站每日只探測標題、生效日、PDF URL、頁數及 SHA-256。任何漂移只標記
`unqualified_new_guide`，不會自動改能力矩陣、readiness、回測或 Paper 狀態。

## Stock CIZ：直接支持的五份能力

| 固定輸入 | 狀態 | 專業判讀 |
|---|---|---|
| `stk_security_info_hist.csv` | `direct_documented` | 官方指南直接支持資料字典能力；不等於已訂閱或已交付 |
| `stk_ind_membership.csv` | `direct_effective_interval_only` | 官方指南直接支持資料字典能力；不等於已訂閱或已交付 |
| `stk_dly_security_data.csv` | `direct_documented` | 官方指南直接支持資料字典能力；不等於已訂閱或已交付 |
| `stk_distributions.csv` | `direct_documented` | 官方指南直接支持資料字典能力；不等於已訂閱或已交付 |
| `stk_delists.csv` | `direct_documented` | 官方指南直接支持資料字典能力；不等於已訂閱或已交付 |

其中 `StkSecurityInfoHist` 有 PERMNO／PERMCO 及歷史有效區間；`StkIndMembership` 有
PERMNO／INDNO／MbrStartDt／MbrEndDt／MbrFlg；日線表保留 raw 價量、回報及交易狀態；
distributions 有 ex／declare／record／pay date、現金或比率及 successor；delists 有 DelRet、
missing type、successor PERMNO／PERMCO 及 storage date。這些都是 schema 能力，不是完整
2006–2026 真實列的驗收結果。

## 仍須證據層的五份輸入

| 固定輸入 | 狀態 | 不可替代規則 |
|---|---|---|
| `trading_calendar.csv` | `provider_or_evidence_overlay_required` | 不以生效日、下載日或缺值推算 |
| `security_info_availability.csv` | `evidence_overlay_required` | 不以生效日、下載日或缺值推算 |
| `membership_announcements.csv` | `evidence_overlay_required` | 不以生效日、下載日或缺值推算 |
| `corporate_action_overlay.csv` | `provider_or_evidence_overlay_required` | 不以生效日、下載日或缺值推算 |
| `exit_terms.csv` | `provider_or_evidence_overlay_required` | 不以生效日、下載日或缺值推算 |

最重要的拒絕替代是：`MbrStartDt` 只代表成分生效區間，不是 `AnnouncedAt`；
`SecInfoStartDt` 只代表證券資料有效區間，不是 `KnownAt`。檔案建立、下載或資料 cut 時間
亦不能回填逐列可知時間。`DelRetMissType` 標明缺失原因，但缺失退出經濟代價仍不可填 0。

## Treasury：同供應商不等於同經濟定義

- 個別 Treasury issue 有 `TDRETNUA` 日度未調整回報；
- `TFZ_DLY_RF2` 有 4／13／26 週日度 RF；4 週 `TREASNOX=2000061`；
- 精確 1 個月 `TREASNOX=2000001` 在 `TFZ_MTH_RF`，是月度連續複利收益率；
- 不接受 4 週冒充 1 個月、年率直接除 252、事後逐日挑最接近 30 日票據，或以 DGS1MO、
  SHY、SOFR、零回報拼接。

只有供應商提供相同經濟定義的日度簡單回報，或在看任何輸出前另立可重播映射協議並
完成獨立驗證，才可關閉正式 RF 缺口。本輪沒有建立或試跑該映射。

## 十二道固定控制

| # | 閘門 | 結果 | 核對內容 |
|---|---|---|---|
| 01 | 協議及上游綁定 | 通過 | Round 20 協議、事前收據及第十八／十九輪契約 SHA-256 完整 |
| 02 | 台股參考版本 | 通過 | 三個參考 repository 精確綁定，只轉移研究紀律而不搬參數 |
| 03 | 指南版本身份 | 通過 | 兩個官方標題及 effective date 精確固定 |
| 04 | PDF 身份 | 通過 | 兩份官方 PDF URL、頁數及 SHA-256 與凍結收據一致 |
| 05 | 證券身份歷史 | 通過 | 永久 ID、歷史有效區間及歷史分類能力有官方欄位支持 |
| 06 | 成分只限生效區間 | 通過 | MbrStartDt／EndDt 不被寫成成分公布時間 |
| 07 | Raw 日線及交易狀態 | 通過 | 日價、成交量、回報、停牌及交易狀態能力有指南支持 |
| 08 | 公司行動日期與條款 | 通過 | 除權息、宣派、記錄、派付日、現金／比率及 successor 齊備 |
| 09 | 退市經濟條款 | 通過 | DelRet、缺失類型、successor 及 storage date 齊備；缺值不填 0 |
| 10 | 五份 evidence overlay | 通過 | 日曆、KnownAt、公布時間、公司行動及退出條款缺口全數保留 |
| 11 | Treasury 年期與單位 | 通過 | 4 週日序列與精確 1 個月月序列分開；不冒充正式 RF |
| 12 | 決策邊界 | 通過 | 正式 1/18、provider 0、策略 run 0、Paper 全現金、實金 US$0 |

## 十二項失敗攻擊

| # | 單一錯誤 | 實際 error code | 結果 |
|---|---|---|---|
| 01 | 協議 SHA 漂移 | `convergence_protocol_mismatch` | 拒收 |
| 02 | 參考 commit 漂移 | `reference_commit_mismatch` | 拒收 |
| 03 | 指南 effective date 漂移 | `guide_version_mismatch` | 拒收 |
| 04 | PDF hash 漂移 | `guide_hash_mismatch` | 拒收 |
| 05 | PDF 頁數漂移 | `guide_identity_mismatch` | 拒收 |
| 06 | 少一個 CIZ 直接表 | `stock_capability_set_mismatch` | 拒收 |
| 07 | MbrStartDt 冒充 AnnouncedAt | `membership_announcement_substitution` | 拒收 |
| 08 | SecInfoStartDt 冒充 KnownAt | `security_known_at_substitution` | 拒收 |
| 09 | 缺失 DelRet 填 0 | `delist_economics_imputation` | 拒收 |
| 10 | 4 週日序列冒充 1 個月日序列 | `risk_free_tenor_substitution` | 拒收 |
| 11 | 1 個月年率直接除以 252 | `risk_free_unit_substitution` | 拒收 |
| 12 | 文件通過後啟動 Paper | `convergence_decision_boundary_violation` | 拒收 |

## 下一個有效研究動作

向已授權 CRSP／WRDS 帳戶核對 Stock CIZ 五份直接表、S&P 500 INDNO、五份 evidence overlay，以及與凍結經濟定義完全相同的 1 個月日度簡單 RF；只在真實 18/18 後運行一次正式回測。 在此之前不產生最新選股名單，不把歷史合成控制當真實數據，不為
追求 headline CAGR 改持股數、窗口、退出規則或成本。真實 18/18 後只准運行一次凍結
20 年回測；再通過 QQQ／SPY／同池等權／首輪 Top-10 漂移、10／25／50 bps、DSR／PBO
與危機分段門檻，才可由下一個新增交易日的全現金開始不可回填 Paper。

## 一手來源

- [CRSP US Stock Databases](https://indexes.morningstar.com/research-data-products/crsp-us-stock-databases)
- [CRSP Stock CIZ 最新指南](https://indexes.morningstar.com/docs/guide/crsp-us-stock-databases-guide-for-flat-file-format-2-0?isRdp=true)
- [CRSP US Treasury Database](https://indexes.morningstar.com/research-data-products/crsp-us-treasury-database)
- [CRSP Treasury 最新指南](https://indexes.morningstar.com/docs/guide/crsp-us-treasury-database-guide?isRdp=true)
- [第二十輪事前協議](SHORT_TERM_PROVIDER_CONVERGENCE_PROTOCOL.md)
- [第十八輪正式事前登記](SHORT_TERM_FORMAL_BACKTEST_PREREGISTRATION.md)

本報告只作研究及專業資訊參考，不構成數據供應商背書、投資建議、回報預測或盈利保證。
