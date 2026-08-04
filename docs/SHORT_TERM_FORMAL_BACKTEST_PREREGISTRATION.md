# 短線個股第十八輪：一次性正式回測事前登記 v1.0

凍結時間：2026-08-04T00:23:43Z

狀態：`frozen_before_formal_backtest_bridge_implementation_and_before_provider_result`

## 研究目的與停止規則

本輪不是新增策略，也不是用另一組參數挽救既有負結果。本輪只在任何合格供應商數據及
正式策略結果出現前，把短線 v1 的資料、訊號、會計、baseline、統計、一次性執行及
Paper 邊界寫成可機器稽核的事前登記。

只有下列輸入全部通過，才准運行一次正式回測：

1. 第十七輪 owner-only 本地 package 必須以 `provider` 模式通過 16/16；
2. 其 base ledger 必須通過 point-in-time 20/20，execution extension 必須通過 16/16；
3. 必須另有同步、可追溯的美元一個月國庫券日回報，不能以 0、SHY 或事後最佳替代；
4. 本協議及凍結收據完整，且早於 provider package、風險免費包及正式結果；
5. immutable input run ID 從所有 manifest／receipt SHA-256 及本協議 SHA-256 唯一產生，
   同一 run ID 只可執行一次，新輸出目錄不得已存在。

任一條不通過，只可回報缺口；不得縮短 20 年、換成現時成分股、填補退出回報、改訊號、
改成本或用另一 baseline。正式回測失敗亦須原樣封存，不准在同一資料上調參再跑。Paper
維持全現金，歷史成交不回填，實金動作維持 US$0。

## 固定輸入

### A. 第十七輪本地隔離 package

輸入必須是 repository 外的絕對路徑、owner-only、無 symlink，且精確包含 `ledger/`、
`execution/` 及 `intake_receipt.json`。正式模式只接受：

- `source_mode=provider`；
- `formal_stock_backtest_input_ready=true`；
- `formal_stock_backtest_completed=false`；
- `strategy_run_count=0`；
- point-in-time 20/20、execution extension 16/16；
- QQQ／SPY 使用同步 XNYS sessions、raw open 及總回報定義；
- 第十七輪及其所有上游 manifest／receipt SHA-256 對數。

合成 package 只可驗證程式形狀；即使 20/20、16/16 及本輪控制全通過，也不得設定正式
就緒或產生策略結果。

### B. 風險免費日回報包

風險免費包是另一個 repository 外、owner-only、唯讀目錄，只含
`risk_free_manifest.json` 及 `risk_free_daily.csv`。

`risk_free_daily.csv` 欄位固定為：

| 欄位 | 固定要求 |
|---|---|
| `session` | `YYYY-MM-DD`，與正式研究期 XNYS session 一對一、無缺漏或額外日期 |
| `risk_free_return` | 美元一個月國庫券的簡單日回報，以 decimal 表示；有限、`>-1` 且絕對值不大於 1% |
| `unit` | 固定 `decimal_simple_daily_return`，拒收百分點及年率直接當日回報 |
| `source_series` | 固定 `US_1M_TBILL_DAILY_RETURN` |
| `source_record_id` | 非空且全檔唯一，可追溯至來源日期／版本 |

`risk_free_manifest.json` 必須精確記錄 schema、狀態、來源名稱及 URL、來源版本、下載／
首次匯入時間、研究起訖、日曆、單位、本地研究授權聲明，以及 CSV 的列數與 SHA-256。
來源經濟定義固定為美元一個月國庫券的簡單日回報。首選可重現的 Kenneth R. French
Data Library 美國 Fama/French 日因子 `RF`；官方說明將日 T-bill 回報定義為在該月交易日
複利至一個月國庫券回報的簡單日率。若首選版本尚未覆蓋 2026-07-31，可由同一合格
provider 提供同一經濟定義的完整日序列，但必須在看策略結果前於 manifest 唯一指定，
不能在多個風險免費序列中選結果最好者。

風險免費序列只用於超額 Sharpe、PSR／DSR 及披露；組合中的零碎現金不假設賺取該回報，
以 0% 現金回報作較保守的固定會計。QQQ 補位是風險資產，不是現金或風險免費代理。

## 固定研究期與投資範圍

- 主期：2006-08-01 至 2026-07-31，不因結果移動。
- 訊號：每個完整月最後一個 XNYS session 收市後；首次訊號須已有 252 個前置 session。
- 每個訊號只用當時已生效及已公布的 S&P 500 membership、identifier、分類及公司行動。
- 只接受 `common_stock`、USD、US；同公司多股份類別只保留訊號日前 20 個 session
  中位成交金額最高者，同值時以永久 `security_id` 升序決定。
- 至少 252 個有效總回報 session、訊號日 raw close > US$5、前 20 session 中位
  `raw close × volume` ≥ US$20m；不前向填補。

## 固定訊號計算

訊號特徵用 `total_return_factor` 逐日連乘建立只含當日及之前資料的總回報 wealth index；
raw close 只用於 US$5、成交金額及 raw-open 成交。如此可避免拆股令 200 日趨勢失真，
亦不使用今天的事後調整價。

對每隻合資格股份，在同一訊號日以 pandas `rank(method="average", pct=True)` 計算：

1. 45% 12–1 動量：由 `t-252` 收市至 `t-21` 收市的累積總回報；
2. 25% 6–1 動量：由 `t-126` 收市至 `t-21` 收市的累積總回報；
3. 20% 趨勢：訊號日 wealth index 相對截至當日 200-session 簡單平均線的距離；
4. 10% 低波幅：截至訊號日 63-session 總回報日變動的樣本標準差乘 `sqrt(252)`，
   以負波幅排名。

綜合分數由高至低，同分以永久 `security_id` 升序；逐隻加入直至十隻，同一當時行業
最多三隻。每隻目標固定 10%；不足十隻的剩餘比例給同一 execution table 的 QQQ。
不使用槓桿、沽空、止蝕、止賺、即市資料或事後行業分類。

## 固定成交與公司行動會計

- 月末 `t` 收市產生目標，`t+1` 第一個正式 session 的真實 raw open 以 fractional shares
  成交；不使用同日 open、adjusted open、VWAP 或缺值補價。
- 初始名義資金固定 US$1,000，只令報告容易閱讀；百分比結果不靠資金規模改善。
- 單邊成交成本按 `sum(abs(trade shares × raw open)) × bps / 10,000` 扣除；primary
  10 bps，完整重跑 25 及 50 bps，不能只在 CAGR 上事後近似。
- 拆股只調整股數一次；派息於 ex-date 按當時持股建立應收，pay-date 才變成可交易現金；
  raw price 路徑不再另加同一 `total_return_factor` 派息。
- CRSP CIZ 日回報已含退市回報時，return-only storage row 不當普通交易日；退市回報、
  現金代價或換股條款只能選一條經濟結算路徑，不能雙計。
- 現金收購變現後留在 0% 回報現金；換股及分拆按 action ledger 延續 successor 股數；
  `removed_continues` 即使離開指數仍持有至下一個既定重新平衡 raw open。
- 每日權益等於收市可交易現金、應收現金及全部持股的 raw close 市值；每一行必須通過
  `前日權益 + 市場變動 + 公司行動 - 成本 = 當日權益` 對賬容差。

## 四個事前 baseline

所有 baseline 使用相同 session、US$1,000、raw-open 時鐘、公司行動及 10／25／50 bps：

1. `QQQ_buy_hold`：首次可執行日一次買入後持有；
2. `SPY_buy_hold`：同上；
3. `pit_eligible_equal_weight_monthly`：每個月末對同一合資格逐期成分池等權，下一 open
   月度再平衡；它分開「持有大型股池」與「用綜合分數選十股」；
4. `first_top10_equal_then_drift`：只在第一個正式訊號買入候選當時的十股各 10%，不足
   部分給 QQQ，此後不主動重選或再平衡；拆股／派息／退出／successor 仍依法結算，現金
   退出款留作 0% 現金。它精確實現原協議的「同一十股等權漂移」，不再混用整個今日股池。

候選必須同時跑贏第 3 及第 4 baseline，不能只因 QQQ 較弱就升級。

## 固定統計、窗口與多重測試

- 每條策略報告總回報、CAGR、年率波幅、風險免費超額 Sharpe、Sortino、最大跌幅、
  Calmar、年度單邊換手、交易成本及 US$1,000 期末值。
- 相對 QQQ 的每日 active return 報告 Newey–West；lag 使用既有公式
  `floor(4 × (n/100)^(2/9))`，不得看結果改 lag。
- PSR 與 DSR 都用相對 QQQ 的每日 active return；DSR 全專案 trial count 固定為
  **6,208**，包含至本協議凍結前所有成功、失敗及未升級研究路徑，本輪不因只跑一個
  候選而重設為 1。
- PBO 固定使用十段 CSCV 及四條已於首輪存在的路徑：凍結綜合月度 Top-10、台股直譯
  每週 20 日動量／60 日趨勢 Top-7、加 SPY 60 日趨勢、再加 60 日相關性濾網。四條都
  在同一 point-in-time 池及同一會計上只跑一次；PBO 只作過度擬合診斷，不以勝出版本
  替換正式候選。
- 固定兩半：2006-08-01–2016-07-29、2016-08-01–2026-07-31；另列每個月末取樣的
  252／756／1,260-session 滾動一年／三年／五年窗口。
- 固定危機段：2007-10-09–2009-03-09、2020-02-19–2020-03-23、
  2022-01-03–2022-12-30。

## 經濟／統計及 Paper 門檻

沿用短線 v1，必須全部通過：

1. 正式 provider／point-in-time／退出／行動／RF／會計閘門全通過；
2. primary CAGR ≥ QQQ +2.0 個百分點，風險免費超額 Sharpe高於 QQQ；
3. 最大跌幅不比 QQQ 深超過 5 個百分點；
4. 50 bps 後 CAGR ≥ QQQ +0.5 個百分點；
5. 固定前後十年各 ≥ QQQ +0.5 個百分點；
6. 滾動三年勝 QQQ 比例 ≥60%，中位 CAGR 差 >0；
7. primary CAGR 同時高於逐期等權及首輪同十股漂移；
8. 相對 QQQ Newey–West t ≥1.96、PSR ≥95%、6,208 trials DSR ≥95%；
9. 四路 PBO ≤20%。

正式回測只要一項失敗，狀態固定為 `formal_backtest_failed_no_rescue`；保留負結果，不另開
候選救援。全通過才准另行建立從下一個真正新增交易日開始、不得回填的 Paper；Paper
仍須至少 252 個新增 session 及 12 次完成月度輪選。Paper 不是實金授權，也不保證盈利。

## 固定十八道控制

1. 事前凍結及所有 prerequisite SHA-256 完整；
2. 輸入、RF、輸出均為 repository 外絕對路徑；
3. 輸入樹 owner-only、無 symlink／特殊檔；
4. provider mode、Round 17 receipt 及 0 次策略執行一致；
5. base ledger 20/20；
6. execution extension 16/16；
7. RF 精確檔案、manifest、SHA-256、列數及授權完整；
8. RF session 與研究 XNYS calendar 一對一；
9. RF decimal 簡單日回報單位及數值合理；
10. immutable run ID 綁定所有上游收據及本協議；
11. 特徵窗口、排名、同公司去重及行業 cap 固定；
12. `t` close／`t+1` raw open 及 10／25／50 bps 固定；
13. 派息、拆股、退市、現金及 successor 各只計一次；
14. QQQ、SPY、逐期等權及首輪同十股漂移語義固定；
15. 兩半、滾動窗口、危機段及 US$1,000 口徑固定；
16. NW／PSR／6,208-trial DSR／四路十段 PBO 固定；
17. 新輸出、原子寫入、同 run ID 只可一次；
18. 合成／provider、回測／Paper／實金決策邊界分離。

## 固定十八項單一錯誤攻擊

| # | 單一攻擊 | 必須拒收的 error code |
|---|---|---|
| 01 | 相對路徑或路徑在 repository 內 | `formal_path_boundary_invalid` |
| 02 | package tree 有 symlink／非 owner-only | `formal_private_input_invalid` |
| 03 | synthetic package 冒充 provider | `formal_provider_mode_required` |
| 04 | Round 17 receipt 表示已跑一次 | `formal_prior_run_detected` |
| 05 | 上游 manifest／receipt hash 改動 | `formal_input_binding_mismatch` |
| 06 | RF 多／少檔案 | `risk_free_file_set_mismatch` |
| 07 | RF CSV hash／row count 不符 | `risk_free_receipt_invalid` |
| 08 | RF 缺一個 session | `risk_free_session_mismatch` |
| 09 | RF 多一個非交易日 | `risk_free_session_mismatch` |
| 10 | RF 用 percent 或 annualized 單位 | `risk_free_unit_invalid` |
| 11 | RF 值非有限、≤−100% 或絕對值 >1% | `risk_free_value_invalid` |
| 12 | RF source／record ID 缺失或重複 | `risk_free_provenance_invalid` |
| 13 | run ID 沒綁定一個上游 SHA-256 | `formal_run_id_mismatch` |
| 14 | global trials 由 6,208 改小 | `formal_statistics_policy_mismatch` |
| 15 | baseline 漂移語義或 PBO 路徑改動 | `formal_baseline_policy_mismatch` |
| 16 | 同日 open、adjusted open 或成本改動 | `formal_execution_policy_mismatch` |
| 17 | 輸出已存在或同 run ID 重跑 | `formal_run_already_exists` |
| 18 | 合成控制設定正式／Paper／實金通過 | `formal_decision_boundary_violation` |

每個攻擊只改一個語義條件，必要時同步重算上游普通 receipt，避免 generic hash 錯誤掩蓋
真正失敗。控制或攻擊任一未通過，正式引擎維持未授權。

## 披露

本輪參考台股專案的研究紀律是：凍結快照、D+1、同次 baseline、短窗訊號與組合層分開、
負結果保留；不搬用台股市場微結構、槓桿、權證流向、止賺或加碼參數。協議不是投資建議，
合成控制不是回測成績，US$1,000 例子不是盈利承諾。
