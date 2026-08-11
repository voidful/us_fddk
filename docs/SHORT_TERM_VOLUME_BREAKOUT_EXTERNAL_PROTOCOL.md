# 成交量突破 × SPY 60-session regime：獨立 Vanguard 行業 ETF 外部診斷協議

版本：1.0（post-hoc external mechanism diagnostic）
固定日期：2026-08-11

## 研究角色

Round 63 已在現時 survivor cohort 的 30 檔大型股快照中觀察到成交量突破加 `SPY close >
60-session SMA` 的正面診斷，但 Round 64 的成本及前後十年 robustness 已否決該結果。本輪
把同一規則原樣套用到獨立 Vanguard 行業 ETF 面板，作為機制反證／外部重播，不是新的
首次 alpha 證據。計算預覽已在本協議文字建立前完成，因此不得聲稱 result-blind 或獨立
預註冊；任何結果只寫研究 log，不建立 Paper、網站策略或實金行動。

## 凍結輸入

- 快照：`artifacts/snapshot_short_term_sector_vanguard_20040923_20260731_7a13b864.zip`。
- archive SHA-256：`5f9a020e33399705ac52b9bdd2f5cda1d569909cd3577f80de4bf3f92a935105`。
- panel fingerprint：`7a13b864f5e4aeaec08c1c78e2ed3f5fd64a7586acf7818e16c0ca945870d392`。
- 期間：2006-08-01 至 2026-07-31；只使用已完成 XNYS sessions。
- 候選：固定十個 Vanguard 行業 ETF（VAW、VCR、VDC、VDE、VFH、VGT、VHT、VIS、VOX、VPU）。
- 基準：合資格池、十個行業 ETF 等權、SPY、QQQ、VTI；SHY 只保留作資料完整性對照，
  不作候選。
- SEC／ETF 收據只證明資料 bytes、OHLCV 完整度及 hash；ETF 代理不修復個股 point-in-time
  成分、退市／收購回報或公司行動缺口。

## 固定訊號及執行

訊號只在每個已完成 XNYS 週期最後一個交易日 `t` 收市後計算：

1. `SPY_t > SMA60(SPY)`。
2. 行業 ETF 收市價 > US$5、20-session median dollar volume ≥ US$20m、收市價 > 自身
   60-session SMA、20-session 回報 > 0。
3. 收市價嚴格高於 `t` 之前完整 60-session 的最高收市價，且成交量 ≥ 20-session median
   volume × 1.5。
4. 以 20-session 回報由高至低排序，取最多 Top-10；沒有合資格突破標的即跳過事件。
5. 下一個 XNYS session open 進場，於入場後第 5、10、20 個 session close 離場。
6. 每宗事件扣固定 round-trip 20 bps；另固定列出 10／50 bps 成本敏感度，不使用停損、槓桿、
   盤中 timestamp、重疊處理或事後重選參數。

`eligible_equal` 只套用價格、流動性、60-session 趨勢及正 20-session 回報，不套用突破及
成交量確認；這是配對公平基準。事件結果是 aggregate mechanism diagnostic，不建立資金
曲線或個股交易名單。

## 統計及主要 gates

所有 horizon 同時計算候選、eligible pool、全行業等權及 SPY／QQQ／VTI 的平均淨回報、
配對差、Newey–West（lag 5）、moving-block bootstrap（2,000 次、block 8、seed
20,260,803）、配對勝率及固定前後段結果。主要口徑固定為 20-session／20 bps，六項 gate
如下：

- 完整事件至少 30 宗；
- 候選相對 eligible pool 平均差 > 0；
- Newey–West t ≥ 1.96；
- bootstrap 95% 下界 > 0；
- 配對勝率 > 50%；
- 2006-08-01 至 2016-07-31 及 2016-08-01 至 2026-07-31 兩段平均差均 > 0。

任一 gate 失敗即 `external_validation_failed`。即使全部通過，因本輪是 post-hoc ETF 代理
重播，仍不得自動進入個股正式回測、Paper 或公開頁面。

## 輸出邊界

只產生 aggregate report 及 machine receipt：`paper_authorized=false`、
`public_strategy_allowed=false`、`real_money_action_usd=0`。不修改
`site/data/public-decision.json`；success-only 首頁維持「今天不下單」。
