# 月度動量固定排名加權外部驗證協議

版本：v1；凍結於首次計算前。用途：把已封存的 `rank_weighted_top3` 送到獨立 Vanguard
行業 ETF 面板作機制驗證；不授權 Paper、公開策略或實金交易。

## 研究問題

現時大型股 12–1 月動量家族稽核中，固定 50%／30%／20% 排名權重版本通過經濟閘門，
但該結果使用現時股票池倒推歷史。本輪不再改個股參數，而將同一規則原樣套用到首次
共同下載的 Vanguard 十行業 ETF 面板；若不能重現，則把正面個股結果視為未獲外部支持。

## 固定資料及時鐘

- 只接受 `artifacts/snapshot_short_term_sector_vanguard_20040923_20260731_7a13b864.zip`。
- 正式期固定為 2006-08-01 至 2026-07-31；訊號在完整月末收市形成，下一個 XNYS
  session adjusted open 執行，持有至下次月末訊號。
- 行業池固定為 VAW、VCR、VDC、VDE、VFH、VGT、VHT、VIS、VOX、VPU；QQQ、SPY、VTI、SHY
  只作基準或現金代理。
- 使用同一份已先凍結、後下載的 Vanguard 資料收據；任何 hash、完整性或日期漂移即停止。

## 固定訊號及權重

- 月末計算 20-session 總回報及 60-session 簡單均線；只保留回報可計算且收市價高於
  60-session 均線的行業。
- 按 20-session 回報排序取前三名；固定目標權重依排名為 0.50、0.30、0.20。
- 不足三名時，未用比例持有 SHY；不把剩餘比例重新放大，不使用事後結果挑選 Top-K、
  門檻、持有期、VIX、ATR、止蝕、止賺或槓桿。
- 全期一次輸出，不從本面板挑選最佳鄰近版本。

## 成本、基準及閘門

- 單邊成本固定 10／25／50 bps。
- 同時列 QQQ、SPY、VTI、十行業月度等權、十行業起點等權後漂移及相同股票曝險
  matched control。
- 報告全期、固定前後十年、滾動三年／五年及 2008、2020、2022 壓力期。
- 固定升格閘門：10 bps CAGR 高於 QQQ 2 個百分點、50 bps 仍高於 QQQ 0.5 個百分點、
  前後十年均高於 QQQ 0.5 個百分點、滾動三年勝率至少 60% 且中位差為正、最大回撤
  不深於 QQQ 5 個百分點、勝過 matched control，以及相對 QQQ 的 NW t、PSR、DSR 均通過。

任何閘門失敗，結果只保留在機器收據及研究報告；`paper_authorized=false`、
`public_strategy_allowed=false`、實金 US$0，success-only 網頁維持「今天不下單」。
