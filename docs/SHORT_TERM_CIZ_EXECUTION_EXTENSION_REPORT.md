# 美股短線高回報研究｜第十五輪 CIZ 執行延伸數據報告

研究日期：2026-08-04　｜　狀態：合成 extension 通過；真實供應商數據仍未到位

## 一頁結論

第十四輪找出的四項正式執行缺口，已轉成獨立、可雜湊、可重建及 fail-closed 的
execution extension。合成控制通過 **16/16**，事前固定的
十六項檔案、派息、歷史、移除、基準、成本及時鐘攻擊
**16/16 全數拒收**。第十三輪 adapter 及原八份賬本
完全不變，base ledger 在合成包仍為 **20/20**。

這不是正式回測結果。控制只含三個合成 PERMNO、一個月末訊號、兩個候選資格、
一個移除窗口及 46 列合成 QQQ／SPY 行情。真實數據入口仍為
**1/20**、合法供應商樣本 0、正式 20 年逐股回測 0；
短線 Paper 維持全現金、0 成交、0 持倉，實金動作 US$0。

## 四項缺口如何被封口

| 缺口 | 合成控制證據 | 正式狀態 |
|---|---|---|
| 派息付款日 | ex-date 2026-07-30；pay-date／可用現金日 2026-08-03 | schema 已備；待真實列 |
| 訊號前歷史 | 最少 272 個回報 session、272 個正成交量 session | 超過 252／20 控制；待真實列 |
| 移除後成交 | 2026-07-16 移除，2026-07-31 訊號，2026-08-03 open；13/13 sessions | 完整合成路徑；待真實列 |
| 公平基準同步 | QQQ／SPY 共 46 列，覆蓋研究月及下一開市 | 合成同步；待合法行情 |

`DisExDt` 只建立應收權利，`DisPayDt` 才把現金變成可交易餘額。CRSP 官方 cross-reference
把兩者分列為 Ex-Distribution Date 與 Payment Date；WRDS CIZ event-study 同時確認
`DlyRet` 已包含退市回報，因此本輪沒有重新引入退市雙計。

官方來源：[CRSP SIZ-to-CIZ cross-reference](https://www.crsp.org/crsp_pdf/crsp-us-stock-indexes-databases-siz-to-ciz-cross-reference-guide/)、
[CRSP CIZ guide](https://www.crsp.org/crsp_pdf/crsp-us-stock-indexes-databases-guide-flat-file-format-2-0/)、
[WRDS CIZ event-study](https://wrds-www.wharton.upenn.edu/pages/wrds-research/macros/run-an-event-study-ciz-format-macro/)。

## 五份固定 extension 輸出

`execution/` 只接受四份 CSV 及一份 manifest：

1. `cash_entitlements.csv`：ex-date、pay-date、現金可用日及每股金額；
2. `signal_eligibility.csv`：逐月、逐永久 ID 的回報／流動性歷史計數；
3. `removal_execution_windows.csv`：移除日至下一重新平衡 open 的完整路徑；
4. `benchmark_daily.csv`：QQQ／SPY 同日 raw open 及總回報因子；
5. `execution_manifest.json`：綁定 base manifest、overlay、協議、策略及所有列數／SHA-256。

原 `ledger/` 八份檔案及第十三輪 adapter 不作任何修改，避免用新結果重寫舊證據。

## 十六道合成控制

| # | 閘門 | 結果 | 證據 |
|---|---|---|---|
| 01 | 事前凍結完整性 | 通過 | 協議、收據及前置雜湊完整 |
| 02 | 第十三／十四輪不變 | 通過 | 舊 adapter 及 Round 14 auditor 雜湊不變 |
| 03 | 精確輸入檔案集合 | 通過 | overlay 及 execution 檔案集合／收據一致 |
| 04 | Base ledger 仍為 20/20 | 通過 | 原 point-in-time auditor 全數通過 |
| 05 | Base／extension 綁定 | 通過 | base manifest SHA-256 對數 |
| 06 | 派息事件一對一 | 通過 | dividend action 與 entitlement 一對一 |
| 07 | Ex-date／pay-date 分離 | 通過 | 付款日存在且不早於除息日 |
| 08 | 現金只在付款日可用 | 通過 | cash_available_date 恰等於 pay-date |
| 09 | 月末訊號日曆固定 | 通過 | 1 個完整月末訊號 |
| 10 | 訊號前回報歷史 | 通過 | 所有候選至少 252 個有效回報 session |
| 11 | 訊號前流動性歷史 | 通過 | 所有候選至少 20 個正成交量 session |
| 12 | 移除後完整價格路徑 | 通過 | 移除日至下一重新平衡逐日可定價 |
| 13 | 移除後真實開市價 | 通過 | 退出成交日有正 raw open |
| 14 | 公平基準同步 | 通過 | QQQ／SPY 必要 session 完全一致 |
| 15 | QQQ 補位與 D+1 時鐘 | 通過 | 同一 QQQ 序列及下一交易日 open |
| 16 | 規則及成本不變 | 通過 | 10／25／50 bps 及短線 v1 雜湊吻合 |

## 十六項固定攻擊

| # | 單一錯誤 | 指定拒收代碼 | 結果 |
|---|---|---|---|
| 01 | overlay 多／少檔案 | `execution_source_file_set_mismatch` | 拒收 |
| 02 | base manifest 雜湊與 extension 不符 | `base_ledger_binding_mismatch` | 拒收 |
| 03 | dividend 缺 pay-date | `dividend_pay_date_missing` | 拒收 |
| 04 | pay-date 早於 ex-date | `dividend_date_order_invalid` | 拒收 |
| 05 | entitlement 金額或 action ID 不對數 | `dividend_entitlement_mismatch` | 拒收 |
| 06 | 候選只有 251 個訊號前回報 session | `pre_signal_return_history_missing` | 拒收 |
| 07 | 候選只有 19 個正成交量 session | `pre_signal_liquidity_history_missing` | 拒收 |
| 08 | 移除後路徑中間缺一日 | `post_removal_path_missing` | 拒收 |
| 09 | 下一重新平衡開市價缺失 | `post_removal_execution_open_missing` | 拒收 |
| 10 | SPY 缺一個必要 session | `benchmark_session_missing` | 拒收 |
| 11 | QQQ 同日重複 | `benchmark_duplicate` | 拒收 |
| 12 | 基準 open 非正或標示 adjusted | `benchmark_price_policy_invalid` | 拒收 |
| 13 | QQQ 補位綁定另一 ticker／序列 | `qqq_fallback_binding_invalid` | 拒收 |
| 14 | 月末訊號以同日 open 成交 | `execution_clock_violation` | 拒收 |
| 15 | primary 或壓力成本被改 | `strategy_cost_policy_mismatch` | 拒收 |
| 16 | 插入非月末訊號日 | `signal_calendar_invalid` | 拒收 |

攻擊測試每次同步重算其上游收據，只讓單一語義錯誤進入 auditor；因此不是用 generic
hash mismatch 掩蓋真正問題。16/16 只證明合成 bridge 會關門，不證明市場數據或策略。

## 與第十四輪的關係

第十四輪的結果仍是 **8/12**、攻擊 **10/10**，因為舊八份賬本本身仍沒有四項輸入。
第十五輪沒有把 8/12 改寫成 12/12，而是建立獨立 extension，再以 16 道更嚴格合約
證明「若合法來源提供這些欄位，bridge 可以決定性輸出」。兩層結論不可互換。

## 決策與下一步

下一個有效行動是向合法數據擁有人索取同一 schema 的細樣本，逐列驗證：

1. CRSP CIZ membership、raw OHLCV、`DisPayDt` 及完整退出經濟；
2. QQQ／SPY 同期 raw open、總回報因子與授權來源；
3. 2006-08-01 前至少 252 個正式交易日的候選歷史；
4. 每個 `removed_continues` 至下一月末訊號後開市的完整行情。

真實數據 20/20 及 execution extension 16/16 未同時通過前，不運行正式策略、不展示
個股名單、不建立短線 Paper。這不構成投資建議、供應商背書或盈利保證。
