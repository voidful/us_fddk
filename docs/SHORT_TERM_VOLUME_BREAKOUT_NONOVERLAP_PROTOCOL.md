# 短線成交量確認突破單一帳戶 non-overlap 資金會計協議（Round 61）

版本：1.0（post-hoc capital-accounting diagnostic）
固定日期：2026-08-10

## 研究角色

Round 54 是目前唯一在事件層面接近主要統計門檻的 volume-confirmed breakout 診斷。本輪
不改動其訊號、週期、持有期、股票池或成本，只把原本可重疊的事件放進單一 US$1,000 資金
帳戶，量度能否轉成可持有資金曲線。這是 post-hoc 資金會計診斷，不是獨立首次 alpha 證據；
結果無論正負均不建立 Paper 或實金行動。

## 不可變訊號及交易規則

- 資料：`snapshot_20260731_6a7ca6b8.zip`，只接受 archive SHA、panel fingerprint 及
  watchlist SHA 全部吻合。
- 期間：2006-08-01 至 2026-07-31；只使用已完成 XNYS session。
- 訊號只在每個完成 XNYS 星期最後一個交易日收市後計算。股票必須收市價 > US$5、20 日
  median dollar volume >= US$20m、收市價高於 60 日 SMA、20 日回報 > 0、收市價突破前一個
  完整 60 日最高收市價，並且成交量 >= 20 日 median volume 的 1.5 倍。
- 按 20 日回報由高至低取 Top-5；不足 1 檔即跳過；不套用市場方向濾網。
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

本輪是單一固定資金會計 family，global trial lower bound 由 6312 增加至少 1 至 6313；
不聲稱精確增量。研究角色固定為 `capital_accounting_diagnostic`。
