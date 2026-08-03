# French prior-return schema-informed 解析映射 v1

凍結日期：2026-08-04

## 來源界線

只讀取 2026-08-03 已封存的五個 ZIP；不下載、不更新、不呼叫外部 API。所有檔案 SHA-256
必須與 `SHORT_TERM_FRENCH_PRIOR_RETURN_SCHEMA_REPAIR_PROTOCOL.md` 完全相同。

## 十分位月表

| 檔案角色 | value-weighted 精確 marker | equal-weighted 精確 marker |
|---|---|---|
| short-term prior 1–1 | `Aerage Value Weighted Returns -- Monthly` | `Average Equal Weighted Returns -- Monthly` |
| long-term prior 12–2 | `Value Weight Returns -- Monthly` | `Average Equal Weighted Returns -- Monthly` |

每個 marker 後第一個非空 CSV 列必須是以下十欄，順序不得改動：

`Lo PRIOR, PRIOR 2, PRIOR 3, PRIOR 4, PRIOR 5, PRIOR 6, PRIOR 7, PRIOR 8, PRIOR 9, Hi PRIOR`

其後只接受六位 `YYYYMM`；第一個非六位日期列即結束該月表。年度表、firm count、market
cap 及其他段落全部不進策略計算。

## 因素月表

- Fama/French factors：首個 header 必須包含 `Mkt-RF, SMB, HML, RF`。
- Momentum：首個 header 必須包含 `Mom`。
- Short-Term Reversal：首個 header 必須包含 `ST_Rev`。
- 同樣只接受六位 `YYYYMM`，遇到非六位列即停止。

## 日期、缺值及單位

- 所有月份轉成月末 `PeriodIndex[M]`，嚴格遞增且不得重複。
- 原始百分比除以 100；`-99.99`、`-999` 轉為缺值，只用來觸發停止，不得補值。
- 五檔共同正式期固定從 1963-01 開始，終點取共同最後月份；首次封存預期為 2026-05。
- 正式期所有主要／baseline／因素欄必須零缺值。
- `Mkt-RF + RF` 是市場總回報；RF 只作超額 Sharpe 及回歸。

## 成本及組合映射

- `Hi PRIOR`／`Lo PRIOR` 直接取相應官方欄；Top-2／Top-3 以當月欄位回報等權。
- 線性全池固定權重為 1 至 10 後正規化；平方全池為 1² 至 10² 後正規化。
- 十分位組合按月重組，第一月淨回報為 `(1-c)×(1+r)-1`；其後為
  `(1-c)²×(1+r)-1`。市場只在第一月使用一次 `(1-c)`。
- 不從月度組合假造逐股換手或個股名單。

## 獨立性標記

這份映射在原 ZIP schema 已被看見後才制定。parser 即使全數通過，結果仍固定
`independent_first_seen_evidence=false`，且不能覆蓋 2026-08-03 的 6/8 原失敗收據。
