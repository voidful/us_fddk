# 大型股短窗贏家：French 25 Size × Prior 1–1 外部協議 v1

凍結日期：2026-08-04

狀態：本協議須在首次下載 `25_Portfolios_ME_Prior_1_0_CSV.zip`、查看其數值列及計算
任何本輪策略指標前提交。本輪是個股層級正式資料尚未取得時的合格交叉分組機制檢驗，
不是可買賣組合；Paper、實金及今日選股固定關閉。

## 研究問題與唯一候選

台股參考專案的 20 日動量在現時美股倖存者股池曾出現正訊號，但完整輪選輸給 QQQ。
本輪只問：正方向是否能在 CRSP 全市場分組中、尤其較可交易的大型股內持續存在，而
不是由細價股、退市缺口或今日成份股倒推造成。

唯一候選為 French **value-weighted Size 5／Hi PRIOR 1–1** 月度組合，報表名稱固定為
`Big Hi PRIOR 1–1`。它直接使用 month t 的官方組合回報；該組合已在 t−1 月末按當時
市值及 prior 1–1 排名形成，不能再向前或向後移位。不得按結果把小型股、Lo PRIOR、
equal-weighted 或混合傾斜升格為候選。

## 固定成本與 US$1,000 口徑

- 月度 cohort 視作完整換倉：首月買入一次，其後每月完整賣出再買入。
- 主要單邊成本 10 bps；壓力測試 25／50 bps。這是沒有逐股換手時的保守固定口徑，
  不可因結果改成較低估計。
- French 市場、QQQ 及 SPY 買入持有只在首月扣買入成本。
- Big size row 等權、25-cell 等權、Big Lo PRIOR 及其他每月重組基準使用同一完整換倉
  成本，避免把候選與無成本 baseline 混比。
- US$1,000 只顯示理論終值；不產生碎股、落盤或資金指令。

## 固定 baseline 與敏感度

主要／近期期均比較：

1. French 美國市場總回報 `Mkt-RF + RF`。
2. Size 5 row 五個 prior 組合等權、每月回復等權。
3. 全 25 cells 等權、每月回復等權。
4. `Big Lo PRIOR 1–1`，作正反方向控制。
5. 10 組 Prior 1–1 的 value-weighted `Hi PRIOR`，作未分 size 的既有控制。
6. 10 組 Prior 12–2 的 value-weighted `Hi PRIOR`，作長窗動量控制。
7. 2006-01 後另列 QQQ 及 SPY 買入持有，作實際產品機會成本；兩者不取代 French 市場
   作長歷史統計 baseline。

25 個 value-weighted cells 全部列出；Size 1–5 的 Hi／Lo PRIOR、Big row 線性及平方
傾斜、Big equal-weighted Hi PRIOR只作事前敏感度及 PBO，不得替代唯一候選。全專案
搜尋次數由 6,150 加上本輪 25 cells，固定為 **6,175**。

## 固定期間與壓力段

- 正式共同期：1963-01 至 2026-05 或新 ZIP 與既有因素的共同最後完整月，以較早者為準。
- 主要外部期：1963-01–2005-12。
- 近期確認期：2006-01–共同終點。
- 固定分段：1963–1984、1985–2005、2006–2015、2016–共同終點。
- 另列 60 月滾動窗、1960s 部分期、1970s 至 2010s 完整十年、2020–終點，以及
  1973–1974、1987-10、2000–2002、2008–2009、2020、2022 壓力期。

## 固定指標與統計

- CAGR、總回報、RF 超額 Sharpe、波幅、Sortino、最大跌幅、Calmar、最差月、
  US$1,000 理論終值及年換手。
- 候選相對市場、Big row 等權、25-cell 等權、Big Lo、QQQ、SPY及 12–2 贏家的
  CAGR 差、成本 break-even、固定分段及 60 月滾動勝率。
- 月度主動回報 Newey–West lag 3；PSR／DSR 年化期數 12，DSR trials 6,175。
- 以 25 cells、Big row 線性／平方、Big EW Hi 及 Big row 等權組成的事前 family 做
  10-slice CSCV PBO；若共同月數不足或 slice 不完整即失敗，不改 slice。
- 用 Mkt-RF、SMB、HML、Mom、ST_Rev 作完整共同期因素回歸；不得把 alpha 當成替代
  經濟門檻。

## 硬門檻

數據及時序 10 道門檻：URL／schema 先凍結、首次下載、ZIP/member/SHA、兩個 25 欄
月表、語義排序、日期範圍、1963 後完整、缺值與極端值稽核、既有五 ZIP 及產品快照
雜湊、t−1 形成／t 回報時序，全部必須通過。

主要外部期及近期確認期各用相同 17 道門檻：

1. 10 bps CAGR 高於 French 市場至少 2.0 個百分點。
2. 10 bps CAGR 高於 Big row 等權至少 2.0 個百分點。
3. 10 bps CAGR 高於 25-cell 等權至少 2.0 個百分點。
4. 10 bps CAGR 高於 Big Lo PRIOR 至少 2.0 個百分點。
5. RF 超額 Sharpe高於市場及 Big row 等權。
6. 最大跌幅不比市場及 Big row 等權中較深者再深超過 5 個百分點。
7. 50 bps CAGR 仍高於市場至少 0.5 個百分點。
8. 50 bps CAGR 仍高於 Big row 等權至少 0.5 個百分點。
9. 兩個固定分段 CAGR 均高於市場至少 0.5 個百分點。
10. 兩個固定分段 CAGR 均高於 Big row 等權至少 0.5 個百分點。
11. 相對市場 60 月窗勝率至少 60%，中位 CAGR 差大於零。
12. 相對 Big row 等權 60 月窗勝率至少 60%，中位 CAGR 差大於零。
13. 相對市場及 Big row 等權的 Newey–West t 值均至少 1.96。
14. 上述兩組主動 PSR 均至少 95%。
15. 上述兩組主動 DSR 經 6,175 trials 後均至少 95%。
16. CSCV PBO 不高於 20%。
17. 候選成本 break-even 相對市場及 Big row 等權均至少 50 bps 單邊。

總門檻為 10 + 17 + 17 = **44 道**。只有 44/44 才可說大型股短窗贏家機制通過；
任一失敗即封存，不更換 size、prior 方向、權重、成本、期間或 baseline。

## Paper 與真正個股邊界

即使 44/44，本輪仍固定 `paper_eligible=false`、`paper_state_created=false`、
`trade_ready=false`、`real_money_action_usd=0`。French cells 不是可買入證券，也沒有逐股
成交量、買賣差價、公司行動及每月精確成分賬本。只有另獲授權的 point-in-time／退市
逐股資料，按既有個股 v1 規則首次跑完且通過，才可從全現金建立前瞻 Paper。
