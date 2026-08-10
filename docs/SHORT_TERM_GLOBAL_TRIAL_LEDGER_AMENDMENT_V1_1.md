# 全域試驗帳本 v1.1：Round51 breakout family extension

凍結用途：只延伸 `docs/SHORT_TERM_GLOBAL_TRIAL_LEDGER_PROTOCOL.md` 的 lower-bound 收據，
不修改 v1.0 檔案、歷史 entry 或正式 readiness 入口。

## 固定 predecessor

- v1.0 ledger：`artifacts/short_term_global_trial_ledger.json`
- v1.0 ledger SHA-256：`0240f3c36edca35a86c077a94116067a7d1560e4329968df33abbdcaffbb4b49`
- v1.0 protocol SHA-256：`8c9fb4d515741283143192612d8017a86333086ed641ea0e45c2eb5c492c4451`
- predecessor lower bound：`6,287`
- predecessor chain head：`c0e754cee5603c5eb9d2d142db1af6ec21b465d3492097b02112b94a18574085`

## 唯一新增 family

| sequence | family | state | minimum increment | new lower bound |
|---:|---|---|---:|---:|
| 12 | `round51_current_cohort_breakout_three_horizons` | result seen | 3 | 6,290 |

`+3` 對應事前固定的 5／10／20 日 horizon paths。這是保守最低增量，不聲稱已精確枚舉
其他手動查看；`exact_increment_claimed` 必須為 `false`。

## 驗證要求

extension receipt 必須：

1. 先通過 v1.0 ledger audit，並核對 predecessor bytes、protocol hash、lower bound 及 chain head；
2. 綁定 Round51 protocol、protocol receipt、validation result 及本報告的 repository-relative SHA-256；
3. 以 canonical JSON 計算新 entry hash 及 extension receipt self-hash；
4. 保持 `paper.authorized=false`、`paper.state=all_cash`、`backfilled_trades=0`、`positions=[]` 及
   `real_money_action_usd=0`；
5. 禁止刪列、倒退 lower bound、把 `result_seen` 改回 `preregistered_unrun` 或以 extension
   直接開啟正式回測／Paper。

這份 amendment 只為治理收據服務；Round51 本身因 survivorship-biased adjusted OHLCV 及
主要 gate 4/5，仍是負面診斷，公開頁面不顯示策略。
