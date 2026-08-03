# 短線個股第十五輪：CIZ 執行延伸資料協議 v1.0

凍結時間：2026-08-03T22:21:13Z

狀態：`frozen_before_execution_extension_bridge_implementation`

## 研究問題

第十四輪確認第十三輪的八份 point-in-time 賬本只足以通過資料完整性合約，正式執行
仍缺四項輸入：派息付款日、訊號前 252 日歷史、成分移除後至下一次重新平衡開市的
價格，以及同步 QQQ／SPY 行情。本輪只建立一個獨立 execution extension；不修改
第十三輪 adapter、不改八份既有賬本 schema，亦不改短線 v1 訊號、持股數、成本、
baseline、統計或 Paper 門檻。

本輪只准使用合成列驗證 bridge。沒有合法供應商包時，真實 point-in-time readiness
維持 1/20、正式 20 年逐股回測維持 0、短線 Paper 全現金、實金動作 US$0。

## 官方欄位語義

- CRSP CIZ `StkDistributions` 分別提供 `DisExDt` 及 `DisPayDt`；前者是除息／除權日，
  後者是付款日（如有）。現金在付款日前只可列作應收，不可用於下一開市成交。
- WRDS 的 CIZ event-study 範例明示 `DlyRet` 已包括退市回報；本輪不得重新引入
  `DelDlyDt` storage row 或第二次套用 `DelRet`。
- QQQ、SPY 及不足十股時的 QQQ 補位必須使用同一交易日序列、raw open、總回報因子
  與凍結成本政策；不得以不同供應商日曆或調整開市價製造公平比較。

主要來源：

- [CRSP SIZ-to-CIZ cross-reference guide](https://www.crsp.org/crsp_pdf/crsp-us-stock-indexes-databases-siz-to-ciz-cross-reference-guide/)
- [CRSP US Stock Databases Guide for Flat File Format 2.0](https://www.crsp.org/crsp_pdf/crsp-us-stock-indexes-databases-guide-flat-file-format-2-0/)
- [WRDS Run an Event Study (CIZ Format)](https://wrds-www.wharton.upenn.edu/pages/wrds-research/macros/run-an-event-study-ciz-format-macro/)

## 固定輸入與輸出

輸入 A 是完全不變的第十三輪 CIZ bundle；輸入 B 是獨立 overlay：

- `execution_overlay_manifest.json`：授權聲明、固定研究期、第一個訊號日、基準價格政策、
  QQQ 補位綁定、成本政策，以及所有 overlay 檔案的列數與 SHA-256；
- `benchmark_daily.csv`：`asset_id`、`session`、raw OHLC、`volume`、
  `total_return_factor`、`source_status`、`source_record_id`。只接受 QQQ 及 SPY。

輸出根目錄分成 `ledger/` 與 `execution/`。`ledger/` 是第十三輪 adapter 的原樣輸出；
`execution/` 只接受以下檔案：

1. `cash_entitlements.csv`：事件、永久證券 ID、公告時間、ex-date、pay-date、每股現金及
   source record；
2. `signal_eligibility.csv`：每個月末訊號的在籍證券、訊號前回報及流動性 session 數、
   是否合資格及 source record；
3. `removal_execution_windows.csv`：`removed_continues` 的移除日、下一月末訊號、下一
   交易日開市、應有／實有 session 數及 raw open；
4. `benchmark_daily.csv`：經驗證的 QQQ／SPY 同步行情；
5. `execution_manifest.json`：綁定 base ledger manifest、overlay manifest、本協議、短線
   v1 規則及四份輸出收據。

不得把這四份延伸表塞回原八份賬本或改寫第十三輪 manifest；兩層以 SHA-256 對數。

## 固定十六道合成控制閘門

| # | 閘門 | 通過條件 |
|---|---|---|
| 01 | 事前凍結完整性 | 本協議及收據早於 bridge、結果及報告 |
| 02 | 第十三／十四輪不變 | 舊 adapter 雜湊不變；Round 14 仍為 8/12、攻擊 10/10 |
| 03 | 精確輸入檔案集合 | overlay 只含 manifest 及 benchmark；列數與雜湊一致 |
| 04 | Base ledger 仍為 20/20 | 原 adapter 產物按原 point-in-time auditor 全部通過 |
| 05 | Base／extension 綁定 | execution manifest 記錄實際 base manifest SHA-256 |
| 06 | 派息事件一對一 | 每個 dividend action 恰有一行 entitlement，金額及 ID 對數 |
| 07 | Ex-date／pay-date 分離 | pay-date 存在且不早於 ex-date；兩欄不可互換 |
| 08 | 現金只在付款日可用 | ex-date 只建立應收，pay-date 才可進可交易現金 |
| 09 | 月末訊號日曆固定 | 訊號只取研究期內每個完整月份最後正式交易日 |
| 10 | 訊號前回報歷史 | 每個在籍候選在每次訊號前至少有 252 個有效回報 session |
| 11 | 訊號前流動性歷史 | 每個在籍候選在每次訊號前至少有 20 個正成交量 session |
| 12 | 移除後完整價格路徑 | `removed_continues` 由移除日至下一重新平衡開市逐日可定價 |
| 13 | 移除後真實開市價 | 退出成交日有正 raw open；停牌、缺值及補值均不得通過 |
| 14 | 公平基準同步 | QQQ／SPY 覆蓋研究期及必要下一開市，session 完全一致 |
| 15 | QQQ 補位與 D+1 時鐘 | 補位綁定同一 QQQ 表；t 收市訊號只可在 t+1 open 成交 |
| 16 | 規則及成本不變 | primary 10 bps、25／50 bps 壓力及短線 v1 雜湊全部吻合 |

十六道只證明合成 execution extension 可重現；不得將 16/16 解讀成真實數據、策略、
Paper 或盈利通過。

## 固定十六項單一錯誤攻擊

| # | 單一攻擊 | 必須結果 |
|---|---|---|
| 01 | overlay 多／少檔案 | 拒收 `execution_source_file_set_mismatch` |
| 02 | base manifest 雜湊與 extension 不符 | 拒收 `base_ledger_binding_mismatch` |
| 03 | dividend 缺 pay-date | 拒收 `dividend_pay_date_missing` |
| 04 | pay-date 早於 ex-date | 拒收 `dividend_date_order_invalid` |
| 05 | entitlement 金額或 action ID 不對數 | 拒收 `dividend_entitlement_mismatch` |
| 06 | 候選只有 251 個訊號前回報 session | 拒收 `pre_signal_return_history_missing` |
| 07 | 候選只有 19 個正成交量 session | 拒收 `pre_signal_liquidity_history_missing` |
| 08 | 移除後路徑中間缺一日 | 拒收 `post_removal_path_missing` |
| 09 | 下一重新平衡開市價缺失 | 拒收 `post_removal_execution_open_missing` |
| 10 | SPY 缺一個必要 session | 拒收 `benchmark_session_missing` |
| 11 | QQQ 同日重複 | 拒收 `benchmark_duplicate` |
| 12 | 基準 open／close 非正或標示 adjusted | 拒收 `benchmark_price_policy_invalid` |
| 13 | QQQ 補位綁定另一 ticker／序列 | 拒收 `qqq_fallback_binding_invalid` |
| 14 | 月末訊號以同日 open 成交 | 拒收 `execution_clock_violation` |
| 15 | primary 或壓力成本被改 | 拒收 `strategy_cost_policy_mismatch` |
| 16 | 插入非月末訊號日 | 拒收 `signal_calendar_invalid` |

每次攻擊只改一個語義條件，並同步重算其上游 manifest 收據；不得用 generic hash 失敗
掩蓋真正錯誤。指定 error code 不符亦視為失敗。

## 固定研究日曆與策略界線

- 正式研究期維持 2006-08-01 至 2026-07-31；第一個可用月末訊號由 XNYS 日曆決定。
- 12–1／6–1／3–1／1 個月訊號權重 45/25/20/10、Top-10、30% 行業上限、US$5、
  US$20m、月末收市訊號／下一開市成交全部不變。
- Baseline 維持 QQQ 買入持有、SPY 買入持有、同池等權、漂移版本及相同執行時鐘。
- 成本維持單邊 10 bps primary 與 25／50 bps 壓力；不得因 extension 結果改門檻。
- 真實 point-in-time 20/20、execution extension 16/16 及正式策略經濟／統計門檻全數
  通過後，才可由全現金開始前瞻 Paper；任何歷史成交不得回填。

## 停止規則

- 任一控制或攻擊失敗，bridge 及正式引擎維持未授權。
- 若 CIZ `DisPayDt`、基準 raw open 或合法來源缺失，只記錄缺口，不推算、不前向填補。
- 合成控制通過不會提高真實 1/20 readiness，不會執行正式回測，不會建立選股名單。
- 本輪不構成投資建議、供應商背書、盈利保證或實金落盤指令。
