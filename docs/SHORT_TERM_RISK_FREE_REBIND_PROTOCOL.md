# 短線個股第三十六輪：風險免費資料與正式入口 rebind 協議 v1.0

凍結時間：2026-08-08T15:40:00Z

狀態：`frozen_after_formal_release_integration_before_risk_free_rebind`

## 目的

第十九輪的暫存協議刻意綁定第十八輪 formal readiness validator 的 frozen SHA-256。
第三十五輪把 release／restatement firewall 接入正式 provider entrypoint，故該
validator 的程式碼有合法演進；第十九輪舊收據仍須保留，不能事後改寫成新版本。這份
rebind 收據只證明「舊資料暫存契約在新正式入口下重新驗證」，不把任何 provider data、
RF 缺日或策略結果變成完整證據。

## 固定父鏈

rebind 必須逐一驗證：

1. 第十九輪協議、事前收據、官方 202606 source 約束及第十八輪 formal preregistration；
2. 第三十五輪 release integration 協議、收據及其 restatement firewall 父鏈；
3. 當前 `usfddk/formal_backtest_readiness.py` 與 `usfddk/formal_release_integration.py`
   的 SHA-256，避免把未核對的入口改動當成已驗證；
4. provider release receipt、Paper、實金仍為未提供、`all_cash`、US$0。

舊第十九輪協議／收據不得修改；本輪只新增一條明確的版本化父鏈。

## 不可移動邊界

- rebind 不是新的 RF snapshot，也不補 2026 年 7 月 22 個 XNYS session；
- rebind 不生成 `risk_free_manifest.json`、不運行策略、不建立 Paper；
- 沒有完整 RF、逐股 point-in-time provider package 及合格 release firewall，正式回測
  仍然拒收；
- 任何父檔案、source SHA、Paper 或實金欄位不符，均 fail-closed。

## 驗證及輸出

程式只在 repository 內讀取父協議及程式 SHA，並以 owner-only 的 frozen receipt 作
完整性收據。成功只代表第十九輪 staging 的既有八道控制及八項攻擊可在新的正式入口
版本下重跑；不代表策略通過、Paper 可啟動或真倉可交易。

本協議只作研究及專業資訊參考，不構成投資建議、回報預測或盈利保證。
