# 美股短線 20 年成交量突破最多 Top-10 診斷協議

版本：v1｜凍結於首次計算前

研究角色：參考專案語義對齊的只讀診斷；不是 point-in-time 回測、買入名單、Paper 或
實金指令。上一個「必須完整 10 檔」稀疏變體保留在另一份收據，兩者不可混合。

## 固定資料與研究問題

使用 `artifacts/snapshot_20260731_6a7ca6b8.zip`（archive SHA-256
`d480fb82e712f06aabe0a98461e222344656b87022b8bda2cd7ccaa4c29ae88b`，panel fingerprint
`6a7ca6b83b1570007424daa46b0ff4e8fb4a655d39298a0f4f6d74c3b7ea3a66`），資料期
2004-01-02 至 2026-07-31，固定同一 30 隻現時股票池。

研究問題是：在最多 10 隻突破股而非強制湊滿 10 隻的語義下，60 日收市突破、1.5×20 日
成交量及 SPY 60 日 regime，能否在成本與固定半期中跑贏 QQQ？不得新增止蝕、止賺、VIX、
回調或結果後門檻。

## 訊號及成交

每個完成星期最後一個 XNYS session 為 `D`，下一 session adjusted open 入場，持有 20
sessions，於第 20 個 session adjusted close 離場。上一宗事件未離場前，後續整宗訊號跳過。

合資格基礎股票必須：收市價 > US$5、20-session median dollar volume >= US$20m、收市價
高於 60-session SMA、20-session 回報為正。其後只有同時 `close_D >= max(close_{D-60:D-1})`
及 `volume_D >= 1.5 × median(volume)_{D-19:D}` 的股票進入突破池。SPY 必須高於其 60-session
SMA。按 20-session 回報降序、ticker 升序打破同值，取突破池最多 10 隻；突破池至少 1 隻，
基礎合資格池至少 10 隻，否則跳過整宗事件。

所有選股在未來 20 sessions 必須有完整 adjusted open／close；否則跳過整宗事件。訊號只
使用 `D` 或以前資料，不使用盤中量、槓桿、停損或停利。

## 成本、基準及 fail-closed 閘門

單邊成本固定 10／25／50 bps；同步列出同一候選期間的 QQQ、SPY、IWM 及年化換手、Sharpe、
最大回撤，並列 2004–2014、2015–2026H1 固定半期。六項閘門為：至少 30 宗接受事件、三個
成本情景均勝 QQQ、50 bps 兩段均勝 QQQ，以及 10 bps 最大回撤不差於 QQQ。

目前快照仍有 survivor、退市／收購、公司行動及 point-in-time 成分缺口；無論數字如何，
`paper_authorized=false`、`public_strategy_allowed=false`、實金 US$0。失敗結果只寫入
內部 log，公開頁面維持「今天不下單」。
