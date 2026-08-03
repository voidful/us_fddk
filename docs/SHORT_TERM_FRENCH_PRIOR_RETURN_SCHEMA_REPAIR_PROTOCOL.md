# French prior-return schema-informed 工程修復協議 v1

凍結日期：2026-08-04

## 身分與不可逾越的界線

這不是新的 first-seen 經濟驗證。2026-08-03 的第六輪已在首次下載後因兩個
value-weighted 月表標記不符，以 6/8 在策略計算前停止；當時終端稽核亦曾顯示原檔前段
數值列。因此本輪必須標示為 **schema-informed engineering diagnostic**，不得計入獨立
樣本外證據、不得覆蓋原失敗收據、不得建立 Paper。

本輪唯一允許的改動是把 parser 的月表標記改成已封存 ZIP 內的兩個精確字串。經濟研究
問題、主要候選、六路敏感度、成本、四個 baseline、期間、15+15 道門檻及 6,150 次搜尋
校正，全部沿用首次下載前已提交的原協議，不能因結果改動。

原經濟協議：

- 檔案：`docs/SHORT_TERM_FRENCH_PRIOR_RETURN_PROTOCOL.md`
- SHA-256：`f6ff259ee2ad020d618f891097eb3dbf7b76ee3d382b9a31c373ba76641f62da`
- 凍結提交：`b3240326cb4ba92e9e6585779a2b6249a9f5c78d`

原 6/8 失敗收據及報告保持原樣，不得改寫成「其實通過」。

## 凍結輸入

本輪不得連線下載或更新任何行情檔，只可讀取下列五份既有快照：

| 角色 | 檔案 | SHA-256 |
|---|---|---|
| short-term prior 1–1 | `french_10_prior_1_0_monthly_20b186f6.zip` | `20b186f6f7c322098d6d2a6be6183d5944b12c7f6c9e888664ce44ba81064ace` |
| long-term prior 12–2 | `french_10_prior_12_2_monthly_ca0af27f.zip` | `ca0af27fa0829ed6ac38b7b13b20cc11fd12274a8d06dac226998dfc1d0f07f6` |
| Fama/French factors | `french_ff_factors_80b88699.zip` | `80b88699a18ac408e2456d25b1004e340f3f7f8d41d5b476a0285bc53c6f0436` |
| Momentum factor | `french_momentum_monthly_37baf72a.zip` | `37baf72ae4eace9715e8746413d0122334c63aa4083fd1c3cf2060fa04e4bd28` |
| Short-Term Reversal factor | `french_st_reversal_monthly_e0fc1859.zip` | `e0fc1859c8b7e56ac17d06239de231fb33d28c8537b3f59fa378d4d704110e21` |

任何 SHA、ZIP member、日期、欄名、缺值或共同正式期不符即停止；不得重下載、補值或改用
每日檔。

## 唯一工程修復

parser 只接受以下精確表段：

- short-term value-weighted：`Aerage Value Weighted Returns -- Monthly`
- short-term equal-weighted：`Average Equal Weighted Returns -- Monthly`
- long-term value-weighted：`Value Weight Returns -- Monthly`
- long-term equal-weighted：`Average Equal Weighted Returns -- Monthly`

不得使用包含搜尋、拼字相似度、正則模糊匹配或「找到第一個十欄表」等寬鬆規則。

## 完全沿用的經濟設計

- 主要候選：value-weighted `Hi PRIOR` 1–1。
- 敏感度：VW Top-2、VW Top-3、VW 線性全池傾斜、VW 平方全池傾斜、EW Hi PRIOR。
- baseline：French market、VW 十分位等權、VW Lo PRIOR 1–1、VW Hi PRIOR 12–2。
- 正式期：1963-01 至共同最後完整月；主要期 1963-01–2005-12，近期 2006-01–終點。
- 固定分段：1963–1984、1985–2005、2006–2015、2016–終點。
- 成本：主要單邊 10 bps，壓力 25／50 bps；第一個月只收買入成本，之後每月完整賣出
  再買入，兩邊均收成本。市場只在第一個月收買入成本。
- 指標：CAGR、總回報、RF 超額 Sharpe、波幅、Sortino、最大跌幅、Calmar、US$1,000
  理論終值、60 月滾動、固定分段、壓力期、因素回歸、成本 break-even。
- 統計：月度 Newey–West、PSR、6,150 trials DSR、六路 10-slice CSCV PBO。
- 每個主要／近期期間仍使用原協議十五道硬門檻；不得減少或更換。

## 結果標籤

機器結果必須同時分開：

1. `schema_repair_engineering_passed`：精確 schema parser 及數據完整性是否通過；
2. `economic_diagnostic_passed`：原 38 道學術數據／經濟門檻是否通過；
3. `independent_first_seen_evidence=false`：固定為 false；
4. `paper_eligible=false`、`paper_state_created=false`、`trade_ready=false`、
   `real_money_action_usd=0`：固定關閉。

即使經濟診斷 38/38，也只能說「同一已見 schema 快照的工程計算結果」，不能說已獲獨立
驗證，更不能產生股票名單。真正 Paper 仍須合格逐股 point-in-time 成分、退市／收購回報、
公司行動、精確換手及已授權供應商，按既有個股 v1 從全現金另行通過。
