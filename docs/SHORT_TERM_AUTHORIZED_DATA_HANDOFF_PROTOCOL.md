# 短線個股第十六輪：授權數據交接協議 v1.0

凍結時間：2026-08-03T23:00:59Z

狀態：`frozen_before_new_provider_lookup_or_handoff_implementation`

## 研究問題

第十五輪只以合成列證明 CRSP CIZ execution extension 可以封閉四項 schema 缺口，
沒有取得任何供應商列。真實 point-in-time／退市入口仍為 1/20、正式 20 年逐股回測
仍為 0、短線 Paper 全現金、實金動作 US$0。

本輪只把既有採購要求轉成一份可交給 CRSP／WRDS 的機器可讀請求，以及一個本地、
fail-closed 的文件回覆驗證器。它不得登入供應商、購買數據、下載原始列、猜測 WRDS
library/table 名稱、修改短線 v1 規則，亦不得因供應商品牌或一份肯定回覆提高真實
readiness。只有合法數據包本身通過既有 20 道閘門及第十五輪 extension，才可運行一次
正式凍結回測。

## 固定來源範圍

新文件核對只准使用下列一手來源，不增加供應商：

1. CRSP／Morningstar Indexes 的 US Stock Databases、Historical Indexes、CIZ Flat File
   Format 2.0 guide 及計算方法；
2. WRDS 的 CRSP 產品目錄、CIZ 變更公告及 CIZ 研究宏；
3. 供應商直接提供、帶日期及產品名稱的書面答覆或授權條款。

若公開頁與登入後 catalog 不同，只可標記 `login_required` 或 `provider_mapping_required`；
不得自行把 flat-file 名稱推定為 WRDS table 名稱。

## 固定交接輸出

本輪固定建立四份可公開、但不含供應商原始列的輸出：

1. `schemas/short_term_authorized_data_response.schema.json`：供應商文件回覆 JSON Schema；
2. `artifacts/short_term_authorized_data_handoff.json`：凍結請求、官方核對及合成驗證收據；
3. `docs/SHORT_TERM_AUTHORIZED_DATA_HANDOFF.md`：可直接交給數據擁有人的人類可讀版本；
4. `site/data/short-term-authorized-data-handoff.json`：只含閘門、攻擊及未授權狀態的網站摘要。

真正供應商回覆、憑證、登入資料、合約、報價及原始數據一律只留在使用者授權的本地
隔離位置，不得加入 Git、網站、Action artifact 或測試 fixture。

## 固定數據請求

### 覆蓋期

- 正式策略期：2006-08-01 至 2026-07-31；
- 訊號前緩衝：至少由 2005-07-01 起，並以每股實際 session 計算，不以日曆日替代；
- 成交尾端：至少覆蓋 2026-08-03，或供應商正式日曆所定 2026-07-31 後首個交易日；
- 所有加入、移除、停牌、退市及公司行動須覆蓋正式策略期，不得只交現時成分。

### CRSP CIZ／證據層十份檔案

檔名及欄位集合沿用第十三輪 adapter，不得看到實際 export 後修改：

1. `stk_security_info_hist.csv`；
2. `stk_ind_membership.csv`；
3. `stk_dly_security_data.csv`；
4. `stk_distributions.csv`；
5. `stk_delists.csv`；
6. `trading_calendar.csv`；
7. `security_info_availability.csv`；
8. `membership_announcements.csv`；
9. `corporate_action_overlay.csv`；
10. `exit_terms.csv`。

前五份可由 CRSP CIZ 或供應商決定性映射；後五份是原 CIZ 欄位不足時的證據層。
供應商若不能提供 announced/known-at、現金／換股退出代價或完整日曆，必須明示
`unavailable`，不得把 effective date、下載時間或現時資料冒充。

### Execution overlay

另需 QQQ／SPY 同一來源、同一交易日的 raw OHLCV、總回報因子、來源記錄 ID，以及
授權與 SHA-256／列數收據。價格必須覆蓋正式策略期及每個月末訊號後下一個正式開市；
不足十股時的 QQQ 補位必須使用完全相同的 QQQ 序列。

## 固定十二道文件交接閘門

| # | 閘門 | 通過條件 |
|---|---|---|
| 01 | 事前凍結完整性 | 本協議及所有前置檔案雜湊早於新文件核對、schema、程式及結果 |
| 02 | 回覆 schema 精確 | 只接受固定 JSON keys、版本、request ID 及本輪協議雜湊 |
| 03 | 供應商與產品明確 | `provider`、`provider_product` 及正式產品參考不可空白 |
| 04 | 授權邊界明確 | 本地研究授權為 true；raw redistribution 必須是明確 boolean；UTC 證明及參考齊全 |
| 05 | CIZ 格式明確 | 只接受現行 `CIZ_FF2`；WRDS library/table 名稱未知時不得猜測 |
| 06 | 十份輸入逐份回答 | 每份檔案須標記 provider／evidence／unavailable、欄位覆蓋及證據參考 |
| 07 | 成分時間語義 | S&P 500 index ID、start/end 及 announcement/availability 能力逐項回答 |
| 08 | 固定期間與緩衝 | 2005-07-01 至至少 2026-08-03，正式期固定且包含訊號前 252 sessions |
| 09 | 永久 ID 與歷史 | PERMNO／PERMCO、歷史代號、股份類別、交易所及歷史分類可逐期重建 |
| 10 | Raw 行情與派息 | raw OHLCV、DlyRet／missing flags、停牌、DisExDt／DisPayDt 及因子能力明確 |
| 11 | 退出經濟完整 | DelRet／missing reason、現金／換股代價、successor 及不可重建比例均有回答 |
| 12 | 公平基準與交付 | QQQ／SPY 同步 raw open、總回報、SHA-256／列數及本地隔離交付方式完整 |

通過 12/12 只表示「文件回覆可進入細樣本交付」，不表示供應商、數據或策略通過，
亦不提高真實 1/20 readiness。

## 固定十二項單一錯誤攻擊

| # | 單一攻擊 | 必須結果 |
|---|---|---|
| 01 | 回覆多／少頂層 key | 拒收 `response_schema_mismatch` |
| 02 | request ID 或協議雜湊漂移 | 拒收 `request_binding_mismatch` |
| 03 | 供應商／產品／產品參考空白 | 拒收 `provider_identity_missing` |
| 04 | 本地研究授權不是 true | 拒收 `license_attestation_invalid` |
| 05 | 授權時間沒有 UTC offset | 拒收 `license_timestamp_invalid` |
| 06 | source format 不是 `CIZ_FF2` | 拒收 `source_format_unsupported` |
| 07 | 十份輸入少一份或多一份 | 拒收 `file_capability_set_mismatch` |
| 08 | 公布時間 unavailable 卻聲稱可 point-in-time | 拒收 `membership_availability_unsupported` |
| 09 | 緩衝晚於 2005-07-01 或尾端早於下一開市 | 拒收 `coverage_window_incomplete` |
| 10 | raw OHLCV／DisPayDt 能力缺失 | 拒收 `market_action_capability_missing` |
| 11 | 缺失 DelRet 沒有比例或退出代價能力 | 拒收 `exit_economics_capability_missing` |
| 12 | QQQ／SPY 不同步或價格標示 adjusted | 拒收 `benchmark_delivery_invalid` |

每項攻擊須同步重算其上游 response hash，只留下單一語義錯誤；不能用 generic hash 錯誤
掩蓋指定拒收代碼。攻擊 fixture 只能是合成聲明，不可含或仿造真實供應商列。

## 固定策略與統計界線

- 12–1／6–1／3–1／1 個月訊號權重 45/25/20/10、Top-10、30% 行業上限、US$5、
  US$20m、月末收市訊號／下一開市成交全部不變；
- baseline 維持 QQQ、SPY、逐期成分等權、同股漂移及相同執行時鐘；
- 成本維持單邊 10 bps 及 25／50 bps 壓力；
- 正式一次性回測仍須通過固定期間、前後十年、滾動窗口、危機段、NW、PSR、全專案
  DSR、PBO、成本及最大跌幅門檻；
- 文件 12/12、細樣本驗收、真實 20/20、extension 16/16 及正式策略門檻必須依次通過，
  才可由全現金開始不可回填的短線 Paper。

## 停止規則

- 沒有帶授權的供應商文件回覆：只發布請求包，不聲稱已聯絡或已取得回覆；
- 文件回覆任一閘門失敗：停止在文件層，不索取或匯入原始列；
- 細樣本或全量包任一既有閘門失敗：不修規則、不刪退出樣本、不改 baseline；
- 不論文件或合成控制多完整，真實數據未通過前，正式回測 0、短線 Paper 全現金、
  實金動作 US$0；
- 本輪不構成採購承諾、供應商背書、投資建議或盈利保證。
