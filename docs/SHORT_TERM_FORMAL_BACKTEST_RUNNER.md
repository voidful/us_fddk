# 短線正式回測一次性執行層

`usfddk/formal_backtest_runner.py` 是凍結短線 v1 的內部最後一層。它先執行 18 道正式
資料、RF、release firewall、路徑及一次性閘門；只有 `formal_stock_backtest_authorized=true`
才會建立 owner-only 輸出目錄並計算訊號、四個 baseline、10／25／50 bps 帳本及比較統計。

## 邊界

- 合成控制在策略計算前拒收；不產生正式結果、不開 Paper、不寫公開決策資料。
- provider run 只容許一個全新輸出目錄；已有目錄不能覆寫或重跑。
- 執行開始後的錯誤寫入該目錄的 `run_failure.json`，狀態為
  `formal_backtest_failed_no_promotion`；失敗結果只作研究 log。
- 成功的內部輸出仍標記 `paper_authorized=false`、`real_money_action_usd=0` 及
  `public_promotion_allowed=false`，不會自動成為網站策略。

## 尚未可執行的資料缺口

目前 CIZ execution extension 的 `benchmark_daily.csv` 有 QQQ／SPY raw OHLC 及
`total_return_factor`，但沒有 ETF 公司行動帳本。raw accounting 不能把非 1 factor 當作
派息／拆股處理，因此 runner 會以 `benchmark_action_ledger_missing` fail closed；補齊
授權 provider 的 benchmark action bridge 後，才可在同一 frozen run ID 下進入正式計算。

## QQQ／SPY 公司行動 bridge

正式 provider 執行必須另傳 repository 外、owner-only 的 bridge 目錄，精確包含：

- `benchmark_action_manifest.json`
- `benchmark_actions.csv`
- `benchmark_entitlements.csv`
- `benchmark_outcomes.csv`

manifest 會綁定正式 `run_id`、execution manifest SHA-256、研究期、QQQ／SPY 資產、供應商
授權及每個 CSV 的 SHA-256／列數。三張表沿用 raw accounting 的 action、派息應收及退出
schema；loader 會檢查 XNYS 日期、派息一對一、退出經濟路徑及 owner-only／無 symlink。
`total_return_factor` 只留作訊號資料，永遠不直接當作估值或派息。

可用 `scripts/run_short_term_formal_backtest.py` 傳入 repository 外的 provider package、
risk-free package、benchmark-action bridge、release firewall 及全新輸出目錄；CLI 只輸出
機器收據，失敗回傳非零狀態。沒有 bridge 或任何 receipt／對數失敗，不建立策略結果。

這個 runner 只產生內部研究收據，不代表盈利、Paper 通過或投資建議。
