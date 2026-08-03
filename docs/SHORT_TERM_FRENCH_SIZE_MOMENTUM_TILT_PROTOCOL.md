# 全池動量傾斜：French 25 Size × Momentum 外部協議 v1

凍結日期：2026-08-04

狀態：本協議須在首次下載 `25_Portfolios_ME_Prior_12_2_CSV.zip`、查看其數值列及
計算任何本輪策略指標前提交。本輪是逐股 point-in-time／退市資料仍未取得時的
合格聚合機制測試，不是可落盤組合；Paper、實金及今日選股固定關閉。

## 台股參考與研究問題

以下三份參考專案在凍結時以固定 commit 閱讀，不把其台股回測數字當成美股證據：

- `appr1ciat1/tst_wocker@3372aa088328700feafeeb07c72ab832ea2d3ecb`：20 日橫斷面
  動量 ×3、60MA 趨勢 ×1、流動性池、前日訊號／翌日成交、Top-K 及市場狀態。
- `appr1ciat1/tw-block-warrant@37463c54796ba36f4aac262519ea7fc2ef797de6`：多窗共振
  可作篩選，但 naive 長倉輸給 0050；必須另比市場 beta、橫斷面價差及成本。
- `appr1ciat1/tst_wocker_filter_lab@06c87b7a1735877c9ccbab3a339c1742814a5058`：排名
  有訊號，但集中少數持倉會放大路徑雜訊；留下「保留全池、按排名傾斜」為未測假說，
  並明列 purged walk-forward 及 point-in-time／退市資料仍欠缺。

本輪只問：在包含 NYSE、AMEX、NASDAQ 及歷史退市影響的 CRSP 聚合分組內，保留全部
size／momentum cells、只按排名溫和傾斜，能否比全池等權及市場提供穩健淨回報，同時
比集中 Top-1／Top-2 保留更好的跌幅與風險調整後回報。

## 唯一候選與固定權重

唯一候選為 French **value-weighted 25 Size × Prior 12–2 cells 的全池線性傾斜**，
報表名稱固定為 `All-25 linear momentum tilt`。

- 五個 size quintiles 各佔組合 20%，不以結果改押大型股或細價股。
- 每個 size 內 PRIOR 1–5 的相對權重固定為 `1:2:3:4:5`；因此每個 cell 的全組合
  權重依 PRIOR rank 分別為 `1/75、2/75、3/75、4/75、5/75`。
- 所有 25 cells 權重均大於零；不得按結果改 softmax 溫度、剔除 Lo PRIOR、改成
  Top-1／Top-2、value-weight size row 或 equal-weighted cell table。
- month t 直接使用官方在 t−1 月末按當時 size 及 prior 2–12 回報形成的 month t 回報，
  不再 shift。這是月度換倉策略；長窗是排名訊號，不代表長期持有。

## 固定成本與 US$1,000 口徑

- 候選、全池等權、Top-1、Top-2、Big Hi、短窗傾斜及其他每月 cell 組合均視作每月
  完整回復目標權重：主要單邊成本 10 bps；壓力 25／50 bps。
- French 市場、QQQ 及 SPY 買入持有只在首月扣一次買入成本。
- 不因聚合 cells 缺少實際逐股換手而降低成本；另列相對 baseline 的成本 break-even。
- US$1,000 只顯示理論終值，不產生碎股、委託、持倉或資金指令。

## 固定 baseline、集中度階梯與負控制

主要／近期共同比較：

1. French 美國市場總回報 `Mkt-RF + RF`。
2. 25 cells 全池等權，每月回復 4%／cell。
3. Top-2：每個 size 的 PRIOR 4／5 各佔 10%，其餘為零。
4. Top-1：每個 size 的 Hi PRIOR 各佔 20%，其餘為零。
5. `Big Hi PRIOR 12–2` 單一大型股贏家 cell。
6. 10 組 Prior 12–2 的 value-weighted `Hi PRIOR`，作未分 size 控制。
7. French Momentum factor，作經典多空因素控制，不與長倉 CAGR 作同口徑升格。
8. 已封存 25 Size × Prior 1–1 的相同 `1:2:3:4:5` 線性傾斜，作短窗負控制。
9. 2006-01 後 QQQ 及 SPY 買入持有，作實際產品機會成本。

25 個新 value-weighted cells、全池等權、線性傾斜、平方傾斜、Top-2 及 Top-1 組成
事前 PBO family；平方傾斜的 PRIOR 權重固定為 `1:4:9:16:25`，只作敏感度，不得升格。
全專案搜尋次數由 6,175 加上本輪 25 cells 與 4 個非重複聚合配置，固定為 **6,204**。

## 固定期間與壓力段

- 正式共同期：1963-01 至 2026-05，或新 ZIP 與既有因素的共同最後完整月，以較早者為準。
- 主要外部期：1963-01–2005-12。
- 近期確認期：2006-01–共同終點。
- 固定分段：1963–1984、1985–2005、2006–2015、2016–共同終點。
- 另列 60 月滾動窗、各完整十年、2020–終點，以及 1973–1974、1987-10、
  2000–2002、2008–2009、2020、2022 壓力期。

## 固定指標與統計

- CAGR、總回報、RF 超額 Sharpe、波幅、Sortino、最大跌幅、Calmar、最差月、
  US$1,000 理論終值及固定年換手口徑。
- 候選相對市場、全池等權、Top-1、Top-2、Big Hi、短窗傾斜、QQQ／SPY 的 CAGR
  差、固定分段、60 月滾動勝率及成本 break-even。
- 月度主動回報 Newey–West lag 3；PSR／DSR 年化期數 12，DSR trials 6,204。
- 上述 29-path 事前 family 做 10-slice CSCV PBO；共同月數或 slice 不足即失敗。
- 用 Mkt-RF、SMB、HML、Mom、ST_Rev 作完整共同期因素回歸；alpha 不取代經濟門檻。

## 數據門檻（10 道）

URL／schema 先凍結、首次下載、ZIP/member/SHA、兩個 25 欄月表、語義排序、日期範圍、
1963 後完整、缺值及極端值稽核、既有封存輸入雜湊、t−1 形成／t 回報時序，全部通過。

## 主要期及近期各 19 道經濟門檻

1. 10 bps CAGR 高於 French 市場至少 1.0 個百分點。
2. 10 bps CAGR 高於 25-cell 等權至少 1.0 個百分點。
3. 10 bps CAGR 高於短窗線性傾斜至少 1.0 個百分點。
4. 10 bps CAGR 至少保留 Top-1 及 Top-2 中較高者的 80%。
5. RF 超額 Sharpe 同時高於市場及全池等權。
6. RF 超額 Sharpe 同時高於 Top-1 及 Top-2。
7. 最大跌幅不比市場及全池等權中較深者再深超過 5 個百分點。
8. 最大跌幅不深於 Top-1 或 Top-2 任一者。
9. 50 bps CAGR 仍高於市場至少 0.5 個百分點。
10. 50 bps CAGR 仍高於全池等權至少 0.5 個百分點。
11. 兩個固定分段 CAGR 均高於市場至少 0.5 個百分點。
12. 兩個固定分段 CAGR 均高於全池等權至少 0.5 個百分點。
13. 相對市場 60 月窗勝率至少 60%，中位 CAGR 差大於零。
14. 相對全池等權 60 月窗勝率至少 60%，中位 CAGR 差大於零。
15. 相對市場及全池等權的 Newey–West t 值均至少 1.96。
16. 上述兩組主動 PSR 均至少 95%。
17. 上述兩組主動 DSR 經 6,204 trials 後均至少 95%。
18. CSCV PBO 不高於 20%。
19. 候選成本 break-even 相對市場及全池等權均至少 50 bps 單邊。

總門檻為 10 + 19 + 19 = **48 道**。只有 48/48 才可說聚合層「全池動量傾斜」
通過；任一失敗即封存，不更換 lookback、權重、成本、期間、size 或 baseline。

## Paper 與真正個股邊界

即使 48/48，本輪仍固定 `paper_eligible=false`、`paper_state_created=false`、
`trade_ready=false`、`real_money_action_usd=0`。French cells 不是可買入證券，也沒有逐股
point-in-time 成分、退市／收購、公司行動、成交量、買賣差價及精確換手。只有另獲授權
的合格逐股資料，以前日訊號／翌日成交、流動性及退市回報首次跑完並通過，才可從全現金
建立獨立前瞻 Paper。
