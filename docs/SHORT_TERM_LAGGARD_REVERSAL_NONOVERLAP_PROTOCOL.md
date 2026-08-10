# 短線落後反轉單一帳戶 non-overlap 資金會計協議（Round 60）

版本：1.0（post-hoc capital-accounting diagnostic）
固定日期：2026-08-10

## 研究角色

本輪不再增加訊號、股票池或持有期；只把 Round 59 的固定「無市場濾網、五日落後、最弱
Top-5」訊號放入一個真正單一資金帳戶，檢查重疊事件及閒置現金後是否仍有可投資的資金曲線。
它是 post-hoc 的資金會計診斷，不是獨立首次 alpha 證據；結果無論正負均不建立 Paper 或
實金行動。

## 不可變資料及交易規則

- 資料：`snapshot_20260731_6a7ca6b8.zip`，只接受 archive SHA、panel fingerprint 及
  watchlist SHA 全部吻合。
- 期間：2006-08-01 至 2026-07-31；只使用已完成 XNYS session。
- 觀察池：Round 57–59 相同的固定 30 檔大型股名單，存在 survivorship bias。
- 訊號：價格高於 US$5、20-session median dollar volume 至少 US$20m，五日回報不高於
  -5%，按五日回報由低至高取最弱 Top-5；不套用市場方向濾網。
- 執行：US$1,000 起始資金；每次只可有一宗持倉。收到訊號後於下一交易日 adjusted open
  等權買入 Top-5，持有 20 個交易日並於 adjusted close 離場；持倉期間所有訊號忽略，
  離場後才接受下一個日後訊號。
- 成本：每宗 round-trip 20 bps，固定在入場／離場各扣 10 bps；不使用槓桿、停損、停利、
  盤中 timestamp 或事後調參。

## 基準及資金曲線

同一 accepted entry／exit schedule 另計 eligible pool、complete cohort、SPY 及 QQQ 的
等權／單一資產曲線；另列全期一次買入並持有 SPY／QQQ（同樣扣一次 20 bps round-trip）。
每條曲線均報告 final equity、CAGR、最大回撤、事件勝率及持倉 session 比例；事件平均回報
不得取代資金曲線。

## 固定 gate 及邊界

資金會計診斷只檢查：至少 30 宗 accepted events、final equity 高於起始、CAGR 高於同排程
eligible pool、CAGR 高於 passive SPY、CAGR 高於 passive QQQ、最大回撤不深於 passive SPY、
最大回撤不深於 passive QQQ，共七項。任何一項失敗均不得稱為可行策略；即使全部通過，
survivorship、adjusted OHLCV、退市／收購及 point-in-time 缺口仍阻止升格。

本輪只寫 aggregate research log 及 append-only trial ledger。`paper_authorized=false`、
`real_money_authorized=false`、`real_money_action_usd=0`，首頁行動維持「今天不下單」。

## 多重比較

本輪是單一固定資金會計 family，global trial lower bound 由 6311 增加至少 1 至 6312；
不聲稱精確增量。研究角色固定為 `capital_accounting_diagnostic`。
