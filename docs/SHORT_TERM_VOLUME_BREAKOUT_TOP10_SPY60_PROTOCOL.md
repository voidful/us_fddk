# 短線成交量突破 Top-10 × SPY 60 日趨勢 regime 診斷協議（Round 63）

版本：1.0（post-hoc market-regime overlay diagnostic）  
固定日期：2026-08-11

## 研究角色

Round 62 的 Top-10 分散度曲線改善了回撤，但 CAGR 仍略低於 QQQ。本輪固定加入既有台股
規則直譯中已出現的 `SPY close > 60-session SMA` 市場趨勢閘門，檢查市場 regime 是否帶來
增量。除該閘門外，不改成交量突破訊號、Top-10、快照、成本或 non-overlap 會計。這是看到
前述結果後新增的 post-hoc overlay 診斷，不是獨立首次 alpha 證據；結果不建立策略、Paper
或實金行動。

## 不可變訊號及交易規則

- 資料：`snapshot_20260731_6a7ca6b8.zip`，只接受 archive SHA、panel fingerprint 及
  watchlist SHA 全部吻合。
- 期間：2006-08-01 至 2026-07-31；只使用已完成 XNYS session。
- 個股訊號只在每個完成 XNYS 星期最後一個交易日收市後計算。股票必須收市價 > US$5、
  20 日 median dollar volume >= US$20m、收市價高於 60 日 SMA、20 日回報 > 0、收市價
  突破前一個完整 60 日最高收市價，並且成交量 >= 20 日 median volume 的 1.5 倍。
- 同一訊號日另須 `SPY close > SPY 60-session SMA`；不使用 VIX 或其他市場閘門。
- 按 20 日回報由高至低取 **Top-10**；不足 1 檔即跳過。
- US$1,000 起始資金；一次只可有一宗持倉。下一交易日 adjusted open 等權買入已入選股票，
  持有 20 個交易日於 adjusted close 離場；持倉期間忽略訊號，離場後才接受日後訊號。
- 每宗 round-trip 20 bps，在入場／離場各扣 10 bps；不使用槓桿、停損、停利、盤中
  timestamp 或事後調參。

## 基準及資金曲線

同一 accepted entry／exit schedule 另計 eligible pool、complete cohort、SPY 及 QQQ 的
等權／單一資產曲線；另列全期一次買入並持有 SPY／QQQ（同樣扣一次 20 bps round-trip）。
每條曲線報告 final equity、CAGR、最大回撤、事件勝率及持倉 session 比例；事件平均回報
不得取代資金曲線。

## 固定 gate 及邊界

七項 capital gate 為：至少 30 宗 accepted events、final equity 高於起始、CAGR 高於同期
eligible pool、CAGR 高於 passive SPY、CAGR 高於 passive QQQ、最大回撤不深於 passive SPY、
最大回撤不深於 passive QQQ。任何一項失敗都不得稱為可行策略；即使全部通過，現時
survivorship cohort、adjusted OHLCV、退市／收購及 point-in-time 缺口仍阻止升格。

本輪只寫 aggregate research log 及 append-only trial ledger。`paper_authorized=false`、
`real_money_authorized=false`、`real_money_action_usd=0`，首頁行動維持「今天不下單」。

## 多重比較

本輪是單一固定 market-regime overlay family，global trial lower bound 由 6314 增加至少
1 至 6315；不聲稱精確增量。研究角色固定為 `market_regime_overlay_diagnostic`。
