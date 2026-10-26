# 短線個股第四十一輪：風險免費 rebind 修訂 v1.1

凍結時間：2026-08-09T22:17:30Z

狀態：`frozen_after_ci_rejected_formal_validator_drift_before_rebind_implementation`

## 目的

第三十六輪 rebind 收據把當時的 `usfddk/formal_backtest_readiness.py` 視為「目前正式
入口」，並凍結其 SHA-256。第四十一輪在沒有正式策略運行、Paper 或實金動作的情況下，
為全域試驗下限帳本加入 fail-closed 驗證及 run-ID 綁定，正式入口因而合法演進。GitHub
Actions 正確以 `rf_staging_rebind_integrity_failed` 拒絕舊 SHA；不能為求通過而改寫第三十六
輪歷史收據。

本修訂在該 CI 失敗後、rebind 實作前凍結，只把第三十六輪歷史鏈接到新的正式入口。
它不新增或改動風險免費資料，不增加覆蓋，不運行策略，也不授權 Paper 或實金。

## 固定父鏈及合法演進

有效 rebind 必須逐一驗證：

1. 第三十六輪協議及收據原始 bytes 的 SHA-256；
2. 第三十六輪收據所指的第十九輪 staging 及第三十五輪 release-integration 父鏈；
3. 舊正式 validator SHA-256
   `f1c98d5fee063dac34d73359b2c3c8a08f92eed10a195caeb0302306032ccbf0`
   只作不可改寫的歷史描述，不可再拿來比較第四十一輪現有檔案；
4. 第四十一輪現有 validator SHA-256
   `dd8e4f56a3f8528917a1ac17451040c71d758eb89cd5869d0736d4f22423aa66`；
5. 未變的 `formal_release_integration.py`，以及令 validator 演進的全域試驗帳本協議及
   帳本 snapshot。

第三十六輪協議及收據不得修改。任何歷史父鏈、第四十一輪正式入口、帳本協議或帳本
snapshot 漂移，均須 fail-closed；其後再有合法入口演進，亦必須新增另一條 versioned
rebind，不可覆寫本修訂。

## 不可移動邊界

- 官方 Fama/French 202606 snapshot、5,009/5,031 覆蓋及 22 個缺日完全不變；
- 不生成正式 `risk_free_manifest.json`，不補值、不回填、不重跑或重選策略；
- 正式 provider run 仍為 0，正式回測不獲授權；
- 短線 Paper 維持 `all_cash`、0 成交、0 持倉；實金動作維持 US$0；
- rebind 通過只代表既有八道 staging 控制及八項攻擊可重現，不是回報或盈利證明。

本協議只作研究及專業資訊參考，不構成投資建議、回報預測或盈利保證。
