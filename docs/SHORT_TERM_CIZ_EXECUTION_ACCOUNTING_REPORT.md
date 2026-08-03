# 美股短線高回報研究｜第十四輪 CIZ 執行與退出會計報告

研究日期：2026-08-04　｜　狀態：會計防線通過；正式引擎輸入未齊

## 一頁結論

第十三輪的八份合成賬本雖通過 20/20，但本輪證明該結果只代表資料合約完整，不能直接
推論策略資產淨值可正確執行。本輪在寫 auditor 前固定十二道執行閘門及十項攻擊，沒有
改動短線 v1 訊號、成本、baseline 或 Paper 門檻。

會計控制通過 **8/12**，十項雙計、提早入賬、缺價及時鐘
攻擊 **10/10 全數拒收**。確認 `DelDlyDt` 的 return-only
列沒有流入普通日回報；最後持倉值 100、`DelRet=-50%` 時，終端值恰為 50，而不是 25。
現金收購、換股、拆細及分拆例子亦各只結算一次。

仍未通過四項：**派息權利與付款分離、訊號前歷史覆蓋、移除後成交覆蓋、公平基準同步**。因此正式 20 年逐股回測仍為 0，真實數據入口仍為
**1/20**；
短線 Paper 維持全現金、0 成交、0 持倉，實金動作 US$0。

## 為何這不是小問題

- WRDS 的 CIZ event-study 範例明示 CIZ 日回報已包含退市回報；若 storage row 與
  outcome 同時計入，100 元在 -50% 退出下會錯算成 25 元。
- `DisExDt` 決定派息權利，`DisPayDt` 決定現金何時收到。現行 adapter 把 dividend
  `effective_date` 寫成 ex-date，沒有保留 pay-date，可能在付款前把應收股息拿去交易。
- 成分股在月中被移除但繼續上市時，原持倉要到下一次月度 open 才沽出。現行 20 道
  audit 只要求移除日後至少一列價格，沒有保證整段可成交。
- 12–1 動量需要 252 日歷史；「在籍期間價格完整」不代表新加入成分已有加入前歷史。
- QQQ、SPY 及不足十股時的 QQQ 補位是凍結規則的一部分，但不在八份逐股賬本內。

官方來源：[WRDS CIZ event-study](https://wrds-www.wharton.upenn.edu/pages/wrds-research/macros/run-an-event-study-ciz-format-macro/)、
[WRDS CIZ-to-SIZ macro](https://wrds-www.wharton.upenn.edu/pages/wrds-research/macros/crsp-ciztosiz-macro/)、
[CRSP CIZ guide](https://www.crsp.org/crsp_pdf/crsp-us-stock-indexes-databases-guide-flat-file-format-2-0/)。

## 五個固定會計例子

| 例子 | 輸入 | 唯一正確結果 |
|---|---|---|
| 有 DelRet 退市 | 100 × (1 − 50%) | 50.00 |
| 缺 DelRet 現金收購 | 2 股 × US$50 | US$100.00 |
| 缺 DelRet 換股 | 4 股 × 0.5 | 2.00 股 successor |
| 2-for-1 拆細 | 1 × 100 → 2 × 50 | 100.00 → 100.00 |
| 分拆權利 | 4 股 × 0.25 | 1.00 股 successor |

## 十二道執行閘門

| # | 閘門 | 結果 | 證據 |
|---|---|---|---|
| 01 | 事前凍結完整性 | 通過 | 協議、收據及前置雜湊對數 |
| 02 | 第十三輪不變 | 通過 | Round 13 控制 20/20、攻擊 12/12 |
| 03 | 退市儲存列隔離 | 通過 | return-only 儲存列不進普通日線 |
| 04 | 退市回報只計一次 | 通過 | 100 × (1 − 50%) = 50 |
| 05 | 缺失 DelRet 現金退出 | 通過 | 2 股 × US$50 = US$100 |
| 06 | 缺失 DelRet 換股退出 | 通過 | 4 股 × 0.5 = 2 股 successor |
| 07 | 派息權利與付款分離 | 未通過 | 現行 adapter 把 effective_date 寫成 ex-date，DisPayDt 未保留 |
| 08 | 拆細／分拆持股會計 | 通過 | 拆細及 successor 權利各只結算一次 |
| 09 | 訊號前歷史覆蓋 | 未通過 | 現行 20 道 audit 未要求每股訊號前 252 日數據 |
| 10 | 移除後成交覆蓋 | 未通過 | 現行 audit 只要求移除日後至少一列，未覆蓋下次月度 open |
| 11 | 公平基準同步 | 未通過 | 八份逐股賬本沒有 QQQ／SPY 及 QQQ 補位行情 |
| 12 | D+1 執行失敗關閉 | 通過 | 下一正式交易日真實 open；同日或補值拒收 |

## 十項固定攻擊

| # | 單一錯誤 | 指定拒收代碼 | 結果 |
|---|---|---|---|
| 01 | 同時計 DelDlyDt DlyRet 及 outcome DelRet | `delisting_return_double_count` | 拒收 |
| 02 | DelRet 缺失時填 0／沒有退出代價 | `missing_exit_economics` | 拒收 |
| 03 | 現金收購同時計現金代價及 DelRet | `cash_exit_double_count` | 拒收 |
| 04 | 換股退出缺 successor／share ratio | `stock_exit_terms_missing` | 拒收 |
| 05 | 付款日前釋放派息現金 | `dividend_cash_available_early` | 拒收 |
| 06 | 拆細同時調股數及當額外回報 | `split_double_count` | 拒收 |
| 07 | 成分移除後價格未覆蓋至下次重新平衡 | `post_removal_execution_price_missing` | 拒收 |
| 08 | 新成分沒有 252 日歷史仍計訊號 | `pre_signal_history_missing` | 拒收 |
| 09 | 缺 QQQ／SPY 仍跑正式比較 | `benchmark_execution_data_missing` | 拒收 |
| 10 | 月末訊號使用同日 open／補值 | `execution_clock_violation` | 拒收 |

攻擊結果只證明 auditor 會拒絕這十類錯誤，不代表供應商數據、正式引擎或策略通過。

## 決策與下一步

Round 13 的 20/20 保留，但解讀收窄為「八份資料賬本通過既有完整性合約」。正式回測
另須本輪 12/12；目前只有 8/12，所以不得啟動引擎。

下一步先凍結 CIZ adapter v2／execution extension，再加入：

1. dividend ex-date 與 pay-date 分欄，付款前只作應收、不可交易；
2. 每股訊號前至少 252 日回報及 20 日成交額覆蓋；
3. `removed_continues` 至下一月度 open 的完整價格；
4. QQQ／SPY／QQQ 補位的同步 raw open、總回報及成本來源。

上述四項未全部通過前，不運行正式策略、不調整凍結規則、不建立短線 Paper。這不構成
投資建議、供應商背書或盈利保證。
