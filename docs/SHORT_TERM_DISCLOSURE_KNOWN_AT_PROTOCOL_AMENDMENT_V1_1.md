# 短線公開披露 known-at 準備度協議 v1.1 修訂

生效日期：2026-08-10

狀態：**在任何獲授權真實披露列、候選選擇或績效結果出現前，對 v1.0 的研究先後次序作
result-blind 修訂。v1.0 原文及原收據保留，不覆寫。**

## 修訂原因

v1.0 寫成「20/20 後才可另開策略協議」，會令研究者只能在看過完整資料後才固定候選，
反而增加事後調參風險。另一方面，v1.0 的 20 項是六個來源的總體 admission；若一個候選
只使用 SEC Form 4，強迫它先取得 Congress、13D、13G 及 13F 的准許與資料，亦不是精確的
來源範圍控制。

本修訂只改這兩個治理次序，不降低任何數據、known-at、私隱、回測或 Paper 門檻。

## v1.0「通過 20/20 後仍不自動成為策略」的版本化取代文字

在 Phase 1 未達 20/20 前，只可凍結 **result-blind candidate specification**；其收據必須
同時證明：

- `authorized_real_rows=0`；
- `candidate_selection_count=0`；
- `strategy_run_count=0`；
- `performance_result_present=false`；
- `paper_authorized=false`；
- `real_money_action_usd=0`。

此行為只令 `candidate_specification_frozen=true`，不得把 Phase 1 的 `strategy_defined`、
`data_admitted`、`backtest_authorized` 或 `paper_authorized` 改為 true。候選執行仍須先通過
與其 `source_scope` **精確相符**的 admission profile 全部閘門；使用多個來源時取各來源
閘門聯集，不能借「未使用」迴避必要審查，也不能要求無關來源的個人資料或法律准許來
冒充更嚴謹。

任何真實資料結果、候選名單或回報存在後，才修改訊號、窗口、成本、比較 family、
樣本期或門檻，一律失敗關閉並新增試驗次數。原 v1.0 的六來源 20/20 仍是多來源總體包的
完整 Phase 1 契約；其 schema、歷史 2/20 狀態及不授權策略的結論不變。

## Source-specific admission 最低契約

每個候選必須另凍結封閉 manifest/schema 及機器 verifier，至少固定：

1. 精確 `source_scope` 與仍有效的 exact-use／automation 條款；
2. request attempt、raw content、版本、修訂及 first-seen 的 append-only 收據；
3. 可驗證加密、owner-only、repository 外 quarantine；
4. 逐期 filing universe 分母、missing／unexpected／duplicate accession；
5. 每列真正的 known-at 證據，歷史 bulk fetch 不得冒充 contemporaneous first-seen；
6. point-in-time 識別碼、成分股、公司行動、市價及 XNYS 成交時鐘；
7. 來源語義、經濟事件去重、amendment 狀態機及獨立 mutation attacks；
8. 獨立覆核的合法真實小樣本，但不得在 admission 階段計算候選或回報。

Source-specific admission 全部通過仍只准執行已凍結研究，不自動准許 Paper。正式回測若
通過，Paper 亦必須由下一個真正新增交易日全現金開始、不可歷史回填；實金永不由本修訂
授權。

## 現時決策邊界

修訂時真實獲授權列 0、候選選擇 0、策略運行 0、績效結果 0。Paper 全現金、持倉 0、
實金動作 US$0，**今天不下單**。
