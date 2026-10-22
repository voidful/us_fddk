# 美股短線 20 年 12–1 月動量研究協議

版本：v1｜凍結於首次計算前

研究角色：單一慢動量機制診斷；不是 point-in-time 回測、買入名單、Paper 或實金指令。

## 研究問題與固定資料

把參考專案的短線執行時鐘保留不變，只將選股回顧改為學術常見的 12–1 月動量（排除最近
一個月），能否減少短窗噪音並改善成本後回報？本輪不搜尋其他回顧期、權重、Top-K、持有
期或市場閘門。

- 快照：`artifacts/snapshot_20260731_6a7ca6b8.zip`；archive SHA-256
  `d480fb82e712f06aabe0a98461e222344656b87022b8bda2cd7ccaa4c29ae88b`。
- panel fingerprint：`6a7ca6b83b1570007424daa46b0ff4e8fb4a655d39298a0f4f6d74c3b7ea3a66`。
- 資料期：2004-01-02 至 2026-07-31；固定同一 30 隻現時股票池。

現時 survivor、退市／收購、公司行動及 point-in-time 成分缺口仍然存在，結果不能冒充
無偏差可交易回測。

## 訊號、執行與成本

每個完成星期最後一個 XNYS session 為 `D`，下一個 session adjusted open 入場，最多七檔
等權，持有 20 sessions 後 adjusted close 離場；同一股票未離場前不重入，容量滿時跳過。

對合資格股票只用 `D` 或以前資料計算：

```text
momentum12_1 = close_{D-21} / close_{D-252} - 1
trend60      = close_D / mean(close_{D-59:D}) - 1
score        = 3 × percentile(momentum12_1) + percentile(trend60)
```

合資格條件沿用母策略：股價至少 US$5、入場前 20 sessions median dollar volume 至少
US$20m、`momentum12_1 > 0`、`trend60 > 0`，並以 QQQ close 高於 20／60-session SMA 作
固定 regime。下一開市 gap 仍須小於 `1.5 × ATR20`，ATR20 只作 gap audit，不觸發出場。

單邊成本固定 10／25／50 bps；同期列出 QQQ、SPY、IWM 及 2004–2014、2015–2026H1 固定
半期。六項閘門與母 20 年診斷相同：至少 500 宗訊號、三個成本情景均勝 QQQ、50 bps 兩段
均勝 QQQ，以及 10 bps 最大回撤不差於 QQQ。

任何閘門失敗即只寫內部 log，`paper_authorized=false`、`public_strategy_allowed=false`、
實金 US$0，公開頁面維持「今天不下單」。
