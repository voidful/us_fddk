# 市場急跌落後反轉：獨立 ETF 面板外部驗證協議

版本：1.0（事前固定、只作外部機制診斷）
固定日期：2026-08-11

## 研究問題

把「SPY 單日急跌時，過去五個交易日跌幅最深的標的短線反彈」這條固定規則，原樣套用到獨立的 Vanguard 行業 ETF 面板，檢查訊號是否只是現時個股觀察池的偶然結果。這是 ETF 代理的機制外部驗證，不是個股選股、Paper 或買入名單。

## 凍結資料

- 快照：`artifacts/snapshot_short_term_sector_vanguard_20040923_20260731_7a13b864.zip`。
- archive SHA-256：`5f9a020e33399705ac52b9bdd2f5cda1d569909cd3577f80de4bf3f92a935105`。
- panel fingerprint：`7a13b864f5e4aeaec08c1c78e2ed3f5fd64a7586acf7818e16c0ca945870d392`。
- 期間：2006-08-01 至 2026-07-31；只使用已完成 XNYS session。
- 合資格 ETF：固定十個 Vanguard 行業 ETF（VAW、VCR、VDC、VDE、VFH、VGT、VHT、VIS、VOX、VPU）。QQQ、SPY、VTI 只作基準，SHY 不作候選。
- 資料收據必須證明先固定協議、再首次下載、且所有正式 OHLCV 欄位完整；任何 hash、代號或終點漂移即停止。

## 固定訊號及執行

訊號在完成交易日 `t` 收市後計算，不能使用 `t+1` 或之後資料：

1. SPY 當日 close-to-close 回報 `SPY_t / SPY_{t-1} - 1 <= -1.5%`。
2. ETF 在 `t` 的價格高於 US$5，且截至 `t` 的 20-session median dollar volume（close × volume）至少 US$20m。
3. ETF 五個 session close-to-close 回報不高於 -5%。
4. 按五日回報由低至高排序，取最弱 Top-5；合資格標的少於 5 個則跳過該事件。
5. 下一個 XNYS session open 進場；於入場後第 5、10、20 個 session close 離場。
6. 主要結果每宗事件扣固定 round-trip 20 bps；另事前固定列出 10／50 bps 敏感度，兩者都不作最佳版本選擇。
7. 不使用停損、槓桿、盤中時間、重疊處理或事後調參。

## 基準、統計及 gates

每個 horizon 同時計算：候選 Top-5 等權、當日合資格池等權、十個行業 ETF 等權，以及 SPY／QQQ／VTI 的相同 open-to-close 事件回報。主要 horizon 是 20 sessions；5／10 sessions 只作方向檢查。所有 horizon 一併列出 10／20／50 bps 敏感度，但只用 20-session、20 bps 判定主要 gates。

20-session 主要 gate 固定為：

- 完整事件至少 30 宗；
- 候選相對合資格池平均差額為正；
- Newey–West t 統計量至少 1.96（lag 5）；
- moving-block bootstrap 平均差額 95% 下界為正（2,000 次、block 8、seed 20,260,803）；
- 配對勝率嚴格高於 50%；
- 2006-08-01 至 2016-07-29 及 2016-08-01 至 2026-07-31 兩段平均差額均為正。

任一 gate 失敗即標記 `external_validation_failed`。即使全部通過，ETF 代理也不能修復個股 point-in-time 成分、退市回報、公司行動或真實成交時間，因此仍不得自動建立 Paper 或公開個股建議。

## 邊界

本協議只產生 aggregate research log、固定報告及機器收據：`paper_authorized=false`、`public_strategy_allowed=false`、`real_money_action_usd=0`。不建立策略 run、不重選參數、不把結果寫入 `site/data/public-decision.json`；首頁仍按 success-only 契約顯示「今天不下單」。
