# 短線個股第十八輪：正式回測就緒報告

證據截至：2026-08-04

## 結論先行

本輪把一次性正式 20 年回測的資料與統計缺口在結果出現前鎖定，合成就緒控制
**18/18**，單一錯誤攻擊
**18/18** 全數按指定 error code 拒收。這只證明管線會
失敗關閉，不是回測成績。

真實狀態仍是：正式就緒 **1/18**、point-in-time **1/20**、本地 provider intake
**1/16**；合法 provider package 及同步 US 1M T-bill RF 包均未收到，正式策略運行
**0 次**，短線 Paper **全現金**，持倉 0，歷史成交 0，實金動作 **US$0**。

## 為何不能現在直接報高回報

既有第十五／十七輪 package 只有 QQQ／SPY，沒有超額 Sharpe、PSR 及 DSR 所需的真正
風險免費日回報。用 0 或 SHY 偷代會改變統計結論。本輪因此新增與 XNYS session 一對一
的 `US_1M_TBILL_DAILY_RETURN`，固定 decimal simple daily return、來源版本、授權、列數及
SHA-256；合成控制共有 22 個短樣本 session，沒有供應商列。

另一個舊歧義是「同股漂移」曾在有偏差沙盒被實作成整個今日完整股池起點等權。本輪在
正式結果前修正定義：只用第一個正式訊號的 Top-10 各 10% 買入一次，其後只處理公司
行動及退出、不主動再平衡。這才真正分開每月輪選與首輪選股後單純持有。

## 凍結比較與統計

- Baseline：`QQQ_buy_hold`、`SPY_buy_hold`、`pit_eligible_equal_weight_monthly`、`first_top10_equal_then_drift`。
- 成本：單邊 10／25／50 bps，全部用下一正式交易日 raw open 真實重跑。
- 顯示資金：US$1,000，容許 fractional shares；
  現金回報固定 0%，QQQ 補位不是現金。
- Newey–West lag 沿用既有公式；DSR 固定懲罰
  6,208 次全專案路徑，不重設為 1。
- PBO 固定 4 條既有路徑、
  10 段 CSCV；不以 PBO 勝出版本替換正式候選。

## 十八道合成控制

| # | 閘門 | 結果 | 核對內容 |
|---|---|---|---|
| 01 | 事前凍結完整性 | 通過 | Round 18 協議、收據及十二份前置雜湊完整 |
| 02 | 外部絕對路徑 | 通過 | 輸入、RF、預留輸出均為 repository 外絕對路徑 |
| 03 | owner-only 輸入 | 通過 | 兩個輸入樹 owner-only 且無 symlink／特殊檔 |
| 04 | provider／合成及零次執行 | 通過 | source_mode=synthetic_control；Round 17 策略執行 0 次 |
| 05 | base ledger 20/20 | 通過 | base ledger point-in-time 20/20 |
| 06 | execution extension 16/16 | 通過 | execution extension 16/16 |
| 07 | RF 收據及授權 | 通過 | RF manifest、CSV、SHA-256、列數及授權完整 |
| 08 | RF 日曆同步 | 通過 | RF 與 22 個 XNYS sessions 一對一 |
| 09 | RF 單位及數值 | 通過 | RF 使用 decimal simple daily return 且量級有效 |
| 10 | immutable run ID | 通過 | run ID 綁定協議、三份上游收據、RF 及政策 |
| 11 | 固定訊號規則 | 通過 | 四因子、排名、同公司去重及三股行業 cap 固定 |
| 12 | 固定成交及成本 | 通過 | t close／t+1 raw open；10／25／50 bps 固定 |
| 13 | 公司行動單次入賬 | 通過 | 派息、拆股、退市、現金及 successor 只計一次 |
| 14 | 四個公平 baseline | 通過 | 四個 baseline 名稱、次序及漂移語義固定 |
| 15 | 固定時段及資金口徑 | 通過 | 固定兩半、滾動窗口、危機段及 US$1,000 |
| 16 | 固定統計及多重測試 | 通過 | NW／PSR／6,208-trial DSR／四路十段 PBO 固定 |
| 17 | 新輸出及一次性 | 通過 | 預留輸出不存在；正式執行須原子建立且只可一次 |
| 18 | 決策邊界分離 | 通過 | 合成只通過形狀控制；正式／Paper／實金均未升級 |

## 十八項失敗攻擊

| # | 單一錯誤 | 實際 error code | 結果 |
|---|---|---|---|
| 01 | 相對路徑 | `formal_path_boundary_invalid` | 拒收 |
| 02 | 非 owner-only 輸入 | `formal_private_input_invalid` | 拒收 |
| 03 | synthetic 冒充 provider | `formal_provider_mode_required` | 拒收 |
| 04 | Round 17 receipt 已跑一次 | `formal_prior_run_detected` | 拒收 |
| 05 | 上游 manifest 漂移 | `formal_input_binding_mismatch` | 拒收 |
| 06 | RF 多一個檔案 | `risk_free_file_set_mismatch` | 拒收 |
| 07 | RF CSV 收據不符 | `risk_free_receipt_invalid` | 拒收 |
| 08 | RF 缺一個 session | `risk_free_session_mismatch` | 拒收 |
| 09 | RF 多一個非交易日 | `risk_free_session_mismatch` | 拒收 |
| 10 | RF 單位改為 percent | `risk_free_unit_invalid` | 拒收 |
| 11 | RF 日回報量級 2% | `risk_free_value_invalid` | 拒收 |
| 12 | RF source record 重複 | `risk_free_provenance_invalid` | 拒收 |
| 13 | run ID 未綁定輸入 | `formal_run_id_mismatch` | 拒收 |
| 14 | DSR trials 改為 6,207 | `formal_statistics_policy_mismatch` | 拒收 |
| 15 | 漂移 baseline 改名／改義 | `formal_baseline_policy_mismatch` | 拒收 |
| 16 | 成本由 50 改 40 bps | `formal_execution_policy_mismatch` | 拒收 |
| 17 | 輸出目錄已存在 | `formal_run_already_exists` | 拒收 |
| 18 | 合成控制升級正式授權 | `formal_decision_boundary_violation` | 拒收 |

## 下一步與決策邊界

取得合法 provider package 與同日 US 1M T-bill RF 包後，先通過 18/18，再以 immutable run ID 只跑一次凍結正式回測。
正式 package 必須 owner-only 且在 repository 外；就緒 18/18 只授權
immutable run ID 的一次固定回測。回測仍須逐項通過 QQQ +2 個百分點、50 bps、前後十年、
滾動三年、逐期等權、首輪同十股漂移、NW／PSR／DSR／PBO 及最大跌幅門檻。

任一項失敗就封存為 `formal_backtest_failed_no_rescue`，不在同一資料上改權重、窗口、持股
數或成本救援。全部通過才可由下一個真正新增交易日開始前瞻 Paper，仍須 252 個新增
session 及 12 次完成輪選；不回填歷史，也不代表實金授權或保證盈利。

## 參考來源

- [Kenneth R. French Data Library](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/Data_Library.html)
- [Fama/French factors 及一個月國庫券 RF 說明](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library/f-f_factors.html)
- [第十八輪事前登記](SHORT_TERM_FORMAL_BACKTEST_PREREGISTRATION.md)
- [短線 v1.1 協議](SHORT_TERM_HIGH_RETURN_PROTOCOL.md)
- [第十七輪本地隔離入口報告](SHORT_TERM_LOCAL_QUARANTINE_INTAKE_REPORT.md)

本報告只作研究及專業資訊參考。合成控制不是真實數據、正式回測、Paper 或盈利證明。
