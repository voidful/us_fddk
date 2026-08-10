# 短線成交量突破 Top-10 × SPY 60 日趨勢 robustness 診斷協議（Round 64）

版本：1.0（post-hoc cost/time robustness diagnostic）  
固定日期：2026-08-11

## 研究角色

Round 63 在現時 survivor cohort 的 20 bps 完整期通過 7/7 capital gate。本輪不改其訊號、
Top-10、SPY 60 日 regime、accepted event schedule、持有期或快照，只重播同一 schedule，
加入固定 50 bps round-trip 成本及前／後固定十年分段，檢查結果是否依賴低成本或單一時段。
這是 post-hoc robustness 診斷，不是獨立首次 alpha 證據；結果不建立策略、Paper 或實金
行動。

## 不可變輸入與重播規則

- 來源固定綁定 Round 63 protocol、protocol receipt、validation receipt、snapshot archive、
  panel fingerprint 及 30 檔 watchlist；任何 predecessor hash 漂移即拒收。
- accepted event schedule 必須由 Round 63 的固定 Top-10、`SPY close > 60-session SMA`、
  20-session holding 及 non-overlap 規則重新產生；不得因成本或分段重新選事件。
- 主要完整期固定為 2006-08-01 至 2026-07-31；分段固定為 2006-08-01 至 2016-07-31
  及 2016-08-01 至 2026-07-31。每段只計 entry／exit 完整落在該段的 accepted event。
- 成交時鐘仍為下一個 XNYS session adjusted open 入場、第 20 個 session adjusted close
  離場；US$1,000 起始資金及單一持倉 non-overlap 不變。
- 成本情景固定為 20 bps（Round 63 primary）及 50 bps；每條路徑同樣在入場／離場各扣
  一半成本，不能只向候選加成本。

## 固定 robustness gate

六項 gate 為：

1. 完整期 20 bps 候選維持 Round 63 的 7/7 capital gate；
2. 完整期 50 bps CAGR 高於同期 passive QQQ；
3. 前十年 20 bps CAGR 高於同期 passive QQQ；
4. 後十年 20 bps CAGR 高於同期 passive QQQ；
5. 前十年 50 bps CAGR 高於同期 passive QQQ；
6. 後十年 50 bps CAGR 高於同期 passive QQQ。

任何 robustness gate 失敗都不得稱為穩健策略；即使全部通過，現時 survivor cohort、
adjusted OHLCV、退市／收購及 point-in-time 缺口仍阻止升格。

本輪只寫 aggregate research log 及 append-only trial ledger。`paper_authorized=false`、
`real_money_authorized=false`、`real_money_action_usd=0`，首頁行動維持「今天不下單」。

## 多重比較

本輪是單一固定 robustness family，global trial lower bound 由 6315 增加至少 1 至 6316；
不聲稱精確增量。研究角色固定為 `robustness_stress_diagnostic`。
