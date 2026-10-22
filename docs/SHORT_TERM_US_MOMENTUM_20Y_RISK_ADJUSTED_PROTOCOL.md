# 美股短線 20 年風險調整動量診斷協議

版本：v1｜凍結於首次計算前

研究角色：同一現時 survivor cohort 的只讀機制診斷；不是 point-in-time 回測、買入名單、Paper
或實金指令。

## 研究問題

在不改動原有市場環境、持有期、交易成本或容量規則的前提下，將 20 日價格動量按當日
ATR20 波幅調整，能否改善原本 20／60 動量 Top-7 相對 QQQ 的長期成本後表現？本輪只
測試這一個固定分數，不搜尋其他窗口、權重、門檻或出場方法。

## 固定輸入與父收據

- 行情：`artifacts/snapshot_20260731_6a7ca6b8.zip`，SHA-256
  `d480fb82e712f06aabe0a98461e222344656b87022b8bda2cd7ccaa4c29ae88b`，資料期
  2004-01-02 至 2026-07-31。
- panel fingerprint：`6a7ca6b83b1570007424daa46b0ff4e8fb4a655d39298a0f4f6d74c3b7ea3a66`。
- 母診斷：`artifacts/short_term_us_momentum_20y_diagnostic.json`，SHA-256
  `9abd15960162e18419654e9ff0aadd31c075defe38e7ea23709419b0044b26fa`。
- 母協議 SHA-256：`22d93df9c906f9010747797ab8abb194108d7b0760e81e0f80b9a4f12dd857a1`。
- 固定股票池為快照中排除 QQQ、SPY、IWM、DBC、EEM、EFA、GLD、IEF、SHY、TLT、VNQ、VIX
  後的 30 隻現時股票；不得新增、刪除或按結果換股。

資料包含現時 survivor 及調整 OHLCV，沒有逐期成分、退市／收購回報或完整公司行動；此
診斷不能被描述為無偏差可交易回測。

## 訊號與執行（逐項沿用母策略）

每個 session 收市作訊號，下一個 XNYS session 開市成交，最多七檔，20 個 session 後離場。
QQQ regime、股價 US$5、20 日中位成交額至少 US$20m、容量、同一股票不得重疊及
`abs(next open / signal close - 1) < 1.5 × ATR20 / close` 全部沿用母協議。

對合資格股票計算：

```text
momentum20 = close_D / close_{D-20} - 1
trend60    = close_D / mean(close_{D-59:D}) - 1
TR_s       = max(high_s-low_s, abs(high_s-close_{s-1}), abs(low_s-close_{s-1}))
ATR20_D    = mean(TR_{D-19:D})
vol20      = ATR20_D / close_D
risk_adj20 = momentum20 / vol20
score      = 3 × percentile(risk_adj20) + percentile(trend60)
```

只有 `momentum20 > 0`、`trend60 > 0`、完整且正的 ATR20 才可入選；按 score 降序及 ticker
升序打破同值。ATR20 只作排名與既有 gap audit，不觸發止蝕、止賺或提前換倉。

## 成本、基準與門檻

單邊成本固定測試 10／25／50 bps；同期列出 QQQ、SPY、IWM 買入並持有，並列 2004–2014
及 2015–2026H1 固定半期。診斷閘門與母策略相同：至少 500 宗訊號、三個成本情景均勝
QQQ、50 bps 兩段均勝 QQQ，以及 10 bps 最大回撤不差於 QQQ。

任何閘門失敗即 `research_candidate_only`、`paper_authorized=false`、
`public_strategy_allowed=false`、實金 US$0；結果只寫入內部 log。即使全部通過，現時
survivor 資料仍不足以授權 Paper。
