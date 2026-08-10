# 短線正式回測：QQQ／SPY 公司行動 bridge v1

## 目的

正式 execution extension 只保存 QQQ／SPY raw OHLC、成交量及總回報因子。這個獨立
provider bridge 補上 raw accounting 必須的公司行動表，避免把總回報因子誤當派息或拆股，
亦避免同一經濟回報雙重入賬。它只供正式回測內部使用，不會寫入 Paper 或公開頁面。

## 固定檔案及欄位

目錄必須是 repository 外的絕對路徑、owner-only（目錄 `0700`、檔案 `0600`）、沒有
symlink／特殊檔，且精確只有：

1. `benchmark_action_manifest.json`
2. `benchmark_actions.csv`
3. `benchmark_entitlements.csv`
4. `benchmark_outcomes.csv`

三張 CSV 分別沿用 `formal_raw_accounting` 的 `corporate_actions`、`cash_entitlements` 及
`security_outcomes` 欄位；`security_id` 只可為 QQQ 或 SPY。每個 dividend action 必須
恰有一個 entitlement，pay-date 不早於 ex-date 且現金只在 pay-date 可用。退出 action
必須恰有一條現金、換股或 delisting-return 路徑。

## manifest 綁定

manifest 必須標記 `provider_benchmark_action_bridge`，聲明本地研究授權，並逐檔記錄
SHA-256／列數。`formal_run_id` 必須等於 readiness 計算的 frozen run ID，
`execution_manifest_sha256` 必須等於同一 provider package 的 execution manifest。研究期、
QQQ／SPY 資產順序及 timestamp 順序均固定；bridge 不得用相對路徑或 repository 內路徑。

任何缺檔、hash／列數不符、run ID 漂移、日期不在 XNYS、action／entitlement／outcome
不對數，都會拒收並保留 `formal_backtest_failed_no_promotion` 收據。沒有合格 bridge 時，
正式回測仍是 0 次，Paper 維持全現金，實金動作為 US$0。
