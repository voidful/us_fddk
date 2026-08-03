# 美股短線高回報研究｜第十六輪授權數據交接文件

研究日期：2026-08-04　｜　請求狀態：準備好可交付，尚未對外發送

## 一頁結論

本輪把 CRSP／WRDS 文件查詢、授權證明及細樣本交付條件做成一份固定、可雜湊、
fail-closed 的請求。合成文件控制通過 **12/12**，
事前固定的十二項 schema、授權、時間、成分、退市及基準攻擊
**12/12 全數拒收**。

這不代表已聯絡供應商。現時沒有 WRDS 憑證、供應商文件回覆或供應商數據列；真實文件
交接只過 **1/12**，逐股 point-in-time 數據仍是
**1/20**。正式 20 年逐股回測 0 次，短線 Paper
維持全現金、0 成交、0 持倉，實金動作 US$0。

## 可直接交付的固定請求

- Request ID：`usfddk-round16-crsp-wrds-ciz-v1`；
- 協議 SHA-256：`4cd6da3541243573ab3a0113eebd26b581831ad31765b4fdc0a82c998703e754`；
- 正式期：2006-08-01 至 2026-07-31；
- 訊號緩衝：由 2005-07-01 起、每股至少
  252 個正式 session；
- 成交尾端：至少至 2026-08-03；
- 現行格式：`CIZ_FF2`；
- 公開目錄候選：`crsp_m_stock`、`crsp_m_indexes`。產品名稱中的 Monthly 是更新套裝標示，不推論為只有月線；
- 公開 WRDS 程式所見候選：`crsp.dsf_v2`、`crsp.msf_v2`、`crsp.StkSecurityInfoHist`、`/wrds/crsp/sasdata/a_stock_v2`、`/wrds/crsp/sasdata/a_indexes_v2`。這些名稱必須由登入後目錄或供應商回覆確認。

請供應商按
[`schemas/short_term_authorized_data_response.schema.json`](../schemas/short_term_authorized_data_response.schema.json)
回覆能力、產品、授權及限制。12/12 只准進入本地隔離細樣本交付，不代表數據或策略通過。

## 十份數據／證據輸入

| 檔案 | 責任層 | 最少欄位 |
|---|---|---|
| `stk_security_info_hist.csv` | provider_ciz | `PERMNO`, `PERMCO`, `SecInfoStartDt`, `SecInfoEndDt`, `Ticker`, `PrimaryExch`, `CUSIP`, `ShareClass`, `USIncFlg`, `IssuerType`, `SecurityType`, `SecuritySubType`, `ShareType`, `SecurityActiveFlg`, `SICCD`, `NAICS`, `ICBIndustry`, `TradingStatusFlg` |
| `stk_ind_membership.csv` | provider_ciz | `PERMNO`, `INDNO`, `MbrStartDt`, `MbrEndDt`, `MbrFlg` |
| `stk_dly_security_data.csv` | provider_ciz | `PERMNO`, `DlyCalDt`, `DlyOpen`, `DlyHigh`, `DlyLow`, `DlyClose`, `DlyVol`, `DlyRet`, `DlyRetMissFlg`, `DlyOrdDivAmt`, `DlynonOrdDivAmt`, `DlyFacPrc`, `DlyDelFlg`, `TradingStatusFlg` |
| `stk_distributions.csv` | provider_ciz | `PERMNO`, `DisExDt`, `DisSeqnbr`, `DisType`, `DisOrdinaryFlg`, `DisDeclareDt`, `DisPayDt`, `DisDivAmt`, `DisFacPr`, `DisFacShr`, `DisPERMNO` |
| `stk_delists.csv` | provider_ciz | `PERMNO`, `DelistingDt`, `DelDlyDt`, `DelActionType`, `DelStatusType`, `DelReasonType`, `DelPaymentType`, `DelPERMNO`, `DelPERMCO`, `DelRet`, `DelRetMissType`, `DelDivAmt` |
| `trading_calendar.csv` | provider_or_evidence_overlay | `session`, `exchange`, `open_at`, `close_at` |
| `security_info_availability.csv` | provider_or_evidence_overlay | `PERMNO`, `SecInfoStartDt`, `SecInfoEndDt`, `KnownAt`, `EvidenceReference` |
| `membership_announcements.csv` | provider_or_evidence_overlay | `PERMNO`, `INDNO`, `MbrStartDt`, `MbrEndDt`, `AnnouncedAt`, `EvidenceReference` |
| `corporate_action_overlay.csv` | provider_or_evidence_overlay | `SourceTable`, `PERMNO`, `EventDate`, `Sequence`, `EventType`, `AnnouncedAt`, `CashAmount`, `ShareRatio`, `SuccessorPERMNO`, `EvidenceReference` |
| `exit_terms.csv` | provider_or_evidence_overlay | `PERMNO`, `DelistingDt`, `OutcomeType`, `CashConsideration`, `ShareRatio`, `SuccessorPERMNO`, `KnownAt`, `EvidenceReference` |

另需 QQQ／SPY 同一來源、同一交易日的 raw OHLCV、總回報因子及來源記錄 ID。所有原始列、
憑證、合約、報價及供應商回覆只可留在使用者授權的本地隔離位置，不可加入 Git 或網站。

## 五個必答問題

1. S&P 500 成分 start／end 及每次 announcement／availability timestamp 可否提供？
2. 2006–2026 的 DelRet 缺失數量、比例及 missing reason 是多少？
3. 缺失 DelRet 能否以現金／換股代價及 successor PERMNO／PERMCO 決定性重建？
4. raw OHLCV、停牌、DisExDt、DisPayDt 及下一開市覆蓋是否完整？
5. 本地研究、衍生匯總、SHA-256 收據及禁止原始列再分發的授權邊界是甚麼？

## 十二道合成文件控制

| # | 閘門 | 結果 | 證據 |
|---|---|---|---|
| 01 | 事前凍結完整性 | 通過 | 本協議及十二份前置雜湊完整 |
| 02 | 回覆 schema 精確 | 通過 | 版本、keys、request ID 及收據一致 |
| 03 | 供應商與產品明確 | 通過 | 供應商、產品及正式參考非空白 |
| 04 | 授權邊界明確 | 通過 | 本地研究授權、UTC 證明及再分發政策完整 |
| 05 | CIZ 格式明確 | 通過 | CIZ_FF2；WRDS mapping 狀態明示 |
| 06 | 十份輸入逐份回答 | 通過 | 固定十份能力及證據參考完整 |
| 07 | 成分時間語義 | 通過 | S&P 500 生效及公布／可知時間可重建 |
| 08 | 固定期間與緩衝 | 通過 | 2005-07-01 至 2026-08-03；至少 252 sessions |
| 09 | 永久 ID 與歷史 | 通過 | PERMNO／PERMCO 及逐期證券歷史完整 |
| 10 | Raw 行情與派息 | 通過 | raw OHLCV、停牌、ex/pay-date 及因子完整 |
| 11 | 退出經濟完整 | 通過 | DelRet 缺失分布、退出代價及 successor 完整 |
| 12 | 公平基準與交付 | 通過 | QQQ／SPY 同步、本地隔離及收據完整 |

## 十二項固定攻擊

| # | 單一錯誤 | 指定拒收代碼 | 結果 |
|---|---|---|---|
| 01 | 回覆多一個頂層 key | `response_schema_mismatch` | 拒收 |
| 02 | request ID 漂移 | `request_binding_mismatch` | 拒收 |
| 03 | 供應商產品空白 | `provider_identity_missing` | 拒收 |
| 04 | 本地研究授權不是 true | `license_attestation_invalid` | 拒收 |
| 05 | 授權時間沒有 UTC offset | `license_timestamp_invalid` | 拒收 |
| 06 | source format 退回 SIZ | `source_format_unsupported` | 拒收 |
| 07 | 十份輸入少一份 | `file_capability_set_mismatch` | 拒收 |
| 08 | 公布時間 unavailable 卻聲稱 point-in-time | `membership_availability_unsupported` | 拒收 |
| 09 | 訊號前緩衝縮短一天 | `coverage_window_incomplete` | 拒收 |
| 10 | 派息 pay-date 能力缺失 | `market_action_capability_missing` | 拒收 |
| 11 | 缺失 DelRet 沒有有效比例 | `exit_economics_capability_missing` | 拒收 |
| 12 | 基準價格標示 adjusted | `benchmark_delivery_invalid` | 拒收 |

每次攻擊均重算 response SHA-256，只留下單一語義錯誤。因此 12/12 證明驗證器會按指定
錯誤關門，不是用 generic hash mismatch 遮蓋問題，也不代表有真實市場證據。

## 公開文件核對

- [WRDS CIZ 格式變更](https://wrds-www.wharton.upenn.edu/pages/data-announcements/changes-to-crsp-data/)：CIZ Flat File Format 2.0 已取代 SIZ；
- [WRDS CIZtoSIZ macro](https://wrds-www.wharton.upenn.edu/pages/wrds-research/macros/crsp-ciztosiz-macro/)：公開程式列出 `crsp.dsf_v2`、`crsp.msf_v2` 及 `StkSecurityInfoHist` 候選；
- [WRDS Size CIZ macro](https://wrds-www.wharton.upenn.edu/pages/wrds-research/macros/macros-portfolios-size-ciz/)：公開程式列出 `a_stock_v2`、`a_indexes_v2` library 候選；
- [WRDS CRSP 產品目錄](https://wrds-www.wharton.upenn.edu/pages/about/data-vendors/center-for-research-in-security-prices-crsp/)：公開目錄列出 `crsp_m_stock`、`crsp_m_indexes`；完整 data dictionary 要登入確認。

以上只證明公開文件中的候選名稱，不證明使用者已有訂閱、供應商已回覆，亦不代表十份
輸入可由單一產品完整供應。

## 決策與下一步

需要使用者授權對外聯絡後，才把這份固定請求交給 CRSP／WRDS。帶產品及授權的文件回覆
通過 12/12 後，只接受本地隔離的合法細樣本，再依次運行樣本驗收、真實 20/20、
execution extension 16/16 及一次固定 20 年策略回測。任何一層失敗，都不改規則、不刪
退出樣本、不改基準，亦不建立短線 Paper。

本文件不構成採購承諾、供應商背書、投資建議或盈利保證。
