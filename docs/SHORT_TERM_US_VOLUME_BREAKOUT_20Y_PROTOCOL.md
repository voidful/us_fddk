# 美股短線 20 年成交量突破研究協議

版本：v1｜凍結於首次計算前

研究角色：參考台股專案的單一突破機制診斷；資料為現時 survivor cohort，並非 point-in-time
回測、買入名單、Paper 或實金指令。

## 研究問題

在固定每週成交時鐘下，60 日收市突破配合成交量確認及 SPY 60 日市場 regime，Top-10
個股能否在 10／25／50 bps 成本及兩段固定期間中跑贏 QQQ？除以下條件外不加入任何
止蝕、止賺、VIX、回調、參數網格或結果後市場開關。

## 固定資料

- 快照：`artifacts/snapshot_20260731_6a7ca6b8.zip`，SHA-256
  `d480fb82e712f06aabe0a98461e222344656b87022b8bda2cd7ccaa4c29ae88b`。
- panel fingerprint：`6a7ca6b83b1570007424daa46b0ff4e8fb4a655d39298a0f4f6d74c3b7ea3a66`。
- 資料期：2004-01-02 至 2026-07-31；股票池為同一 30 隻現時股票，排除 QQQ、SPY、IWM
  及其他 ETF／宏觀工具，不按結果改變。

調整 OHLCV 沒有逐期成分、退市／收購回報或完整公司行動，因此任何正面數字仍只能是
研究線索，不能宣稱可交易盈利。

## 固定訊號與交易時鐘

每個完成星期最後一個 XNYS session 為訊號日 `D`，只使用 `D` 或以前資料；下一個 XNYS
session 開市入場，持有 20 個 session，於第 20 個 session 收市離場。事件採 first-event-
wins：上一事件離場前，後續訊號整宗跳過，避免資金重疊。

股票必須同時符合：

```text
price_D > US$5
median(close × volume)_{D-19:D} >= US$20m
close_D > SMA60_D
momentum20_D = close_D / close_{D-20} - 1 > 0
close_D >= max(close_{D-60:D-1})
volume_D >= 1.5 × median(volume)_{D-19:D}
SPY_close_D > SPY_SMA60_D
```

按 20 日動量降序、ticker 升序打破同值，最多選 10 隻；不足 10 隻或選股在未來 20 個
session 缺少完整 adjusted open／close 即跳過整宗事件。訊號期間不使用盤中成交量、
槓桿、停損或停利。

## 成本、基準與閘門

候選資金曲線使用單邊 10／25／50 bps；每個成本情景同步列出同一入場／離場期間的 QQQ、
SPY、IWM 基準及年化換手、Sharpe、最大回撤。另列 2004–2014 與 2015–2026H1 固定半期。

六項固定閘門：至少 30 宗接受事件、10／25／50 bps CAGR 均高於 QQQ、50 bps 兩段均高於
QQQ，以及 10 bps 最大回撤不差於 QQQ。任何一項失敗即只寫內部 log；無論閘門結果，
`paper_authorized=false`、`public_strategy_allowed=false`、實金 US$0，公開頁面維持
「今天不下單」。
