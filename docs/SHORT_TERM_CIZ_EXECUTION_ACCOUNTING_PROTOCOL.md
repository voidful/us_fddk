# 短線個股第十四輪：CIZ 執行與退出會計協議 v1.0

凍結時間：2026-08-03T21:55:47Z

狀態：`frozen_before_execution_accounting_auditor_implementation`

## 研究問題

第十三輪證明合成 CRSP CIZ 可轉成八份 point-in-time 賬本，但「資料賬本通過」不等於
「可以正確計算策略資產淨值」。本輪在不改動短線 v1 訊號、持股數、成本、baseline 或
Paper 門檻下，檢查八份賬本是否足以按以下唯一時鐘執行：完整月末收市後產生訊號，
下一個交易日開市成交，持有期間逐日入賬派息、拆細、成分移除及永久退出，而且每項
經濟回報只計一次。

本輪不登入 WRDS、不下載付費列、不運行正式 20 年逐股回測。即使合成會計控制通過，
真實 point-in-time readiness 仍以實際數據包為準；未有合法供應商包時維持 1/20，
短線 Paper 全現金，實金動作 US$0。

## 官方語義與優先風險

- WRDS 的 CIZ event-study 範例明示新 CIZ 日回報已包含退市回報。
- CRSP guide 說明 `DelDlyDt` 是 `DelRet` 存入 `StkDlySecurityData` 的日期，通常是
  `DelistingDt` 後下一交易日；它不是交易價格日。
- 因此唯一容許的轉換是：`DlyDelFlg=Y` 的 return-only 儲存列不進普通日回報序列，
  其 `DlyRet` 必須與 `StkDelists.DelRet` 對數，退出時由 `security_outcomes.csv` 計一次。
  若同時保留儲存列回報及再套用 outcome，便屬雙重計算。
- CIZ `StkDistributions` 同時提供 `DisExDt` 與 `DisPayDt`。除息日決定持有人權利，
  付款日決定現金何時可用；正式下一開市成交不能在付款前把未收到現金當成可投資現金。

主要來源：

- [WRDS：Run an Event Study (CIZ Format)](https://wrds-www.wharton.upenn.edu/pages/wrds-research/macros/run-an-event-study-ciz-format-macro/)
- [WRDS：CRSP CIZtoSIZ macro](https://wrds-www.wharton.upenn.edu/pages/wrds-research/macros/crsp-ciztosiz-macro/)
- [CRSP US Stock Databases Guide for Flat File Format 2.0](https://www.crsp.org/crsp_pdf/crsp-us-stock-indexes-databases-guide-flat-file-format-2-0/)

## 固定十二道執行就緒閘門

| # | 閘門 | 通過條件 |
|---|---|---|
| 01 | 事前凍結完整性 | 本協議及收據早於 auditor 程式與任何結果 |
| 02 | 第十三輪不變 | 原 adapter 控制仍為 20/20、攻擊仍為 12/12，策略規則未改 |
| 03 | 退市儲存列隔離 | `DlyDelFlg=Y`／`DelDlyDt` 不輸出成普通價格或普通日回報 |
| 04 | 退市回報只計一次 | `DlyRet` 與 `DelRet` 對數後，只由 outcome 產生一個終端因子 |
| 05 | 缺失 DelRet 現金退出 | 只以持股數乘可追溯正現金代價結算，不再疊加百分比回報 |
| 06 | 缺失 DelRet 換股退出 | successor 永久 ID 及正換股比率可一對一轉成 successor 持股 |
| 07 | 派息權利與付款分離 | 同時保留 ex-date 及 pay-date；付款前現金不可交易 |
| 08 | 拆細／分拆持股會計 | 股數及 successor 權利只調整一次，不能製造假回報或假現金 |
| 09 | 訊號前歷史覆蓋 | 每個候選在訊號日前有 252 個交易日回報及至少 20 日成交額 |
| 10 | 移除後成交覆蓋 | `removed_continues` 由移除日至下一個實際再平衡開市均可定價 |
| 11 | 公平基準同步 | QQQ、SPY 及不足十股時 QQQ 補位有同日 open／總回報／成本資料 |
| 12 | D+1 執行失敗關閉 | t 收市訊號只能在 t+1 open 成交；缺價、停牌或未知退出不得補值 |

十二道全部通過，才代表「引擎輸入及會計可執行」；它仍只可在真實數據 20/20 後授權
運行一次已凍結 v1 正式回測，不授權 Paper。

## 固定十項攻擊

| # | 單一攻擊 | 必須結果 |
|---|---|---|
| 01 | 同時把 DelDlyDt 的 DlyRet 及 outcome DelRet 計入 | 拒收 `delisting_return_double_count` |
| 02 | DelRet 缺失時填 0 | 拒收 `missing_exit_economics` |
| 03 | 現金收購同時計現金代價及 DelRet | 拒收 `cash_exit_double_count` |
| 04 | 換股退出缺 successor 或 share ratio | 拒收 `stock_exit_terms_missing` |
| 05 | DisPayDt 晚於 DisExDt 卻在 ex-date 釋放可用現金 | 拒收 `dividend_cash_available_early` |
| 06 | 拆細同時調整股數及再把比例當回報 | 拒收 `split_double_count` |
| 07 | 成分移除後價格在下次再平衡前中斷 | 拒收 `post_removal_execution_price_missing` |
| 08 | 新成分只有在籍後價格，仍計 12–1／6–1 訊號 | 拒收 `pre_signal_history_missing` |
| 09 | 沒有 QQQ／SPY 或 QQQ 補位行情仍跑正式比較 | 拒收 `benchmark_execution_data_missing` |
| 10 | 月末 t 訊號使用同日 open 或缺價前向填補 | 拒收 `execution_clock_violation` |

每項只改一個條件；不得以 manifest hash 泛化失敗掩蓋語義錯誤。指定 error code 不符亦
視為攻擊測試失敗。

## 固定會計例子

1. **有 DelRet 的退市**：最後交易日收市持倉值 100，`DelRet=-0.50`，下一交易日終端
   現金必須恰為 50；不能再乘第二次 0.50。
2. **缺 DelRet 的現金收購**：持有 2 股、每股現金代價 50，終端現金恰為 100；不得
   另行推算百分比回報。
3. **缺 DelRet 的換股收購**：持有 4 股、每股換 0.5 股 successor，結果恰為 2 股
   successor；不能同時保留舊股。
4. **2-for-1 拆細**：1 股變 2 股，若 raw 價由 100 變 50，持倉價值仍為 100；拆細
   比率不是額外 +100% 回報。
5. **派息**：ex-date 建立應收權利，pay-date 才變成可交易現金；兩日期不得互換。

## 停止及升格規則

- 任一會計控制或十項攻擊失敗，正式引擎維持未授權；不得用現有 20/20 ledger headline
  取代本輪執行閘門。
- 若發現八份賬本缺欄位，只可記錄缺口及提出下一版 schema；不得從未記錄資料推算。
- 不因結果改動 45/25/20/10 權重、Top-10、30% 行業上限、US$5、US$20m、月末訊號、
  下一開市成交、10/25/50 bps、QQQ/SPY/同池/漂移 baseline 或統計門檻。
- 真實數據 20/20 與本輪 12/12 都通過後，才可執行一次 2006-08-01 至 2026-07-31
  正式回測；策略經濟及統計門檻再全部通過，才可由全現金開始前瞻 Paper。
- 合成結果、工程通過或私人部署均不構成投資建議、供應商背書或盈利保證。
