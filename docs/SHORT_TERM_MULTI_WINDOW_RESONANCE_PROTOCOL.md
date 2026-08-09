# 美股短線第 38 輪：四窗動量共振替換式疊加事前協議

狀態：**只凍結設計；本文件提交及推送至 GitHub 前，不得計算任何第 38 輪選股分布、回報、
風險、顯著性或門檻結果。**

## 研究問題與停止邊界

第 30 輪把五個資金槽位在非事件期持有 QQQ、事件期全數換成單一 20 日動量 Top-7；20 bps
下歷史 CAGR 高於 QQQ，但 Newey–West、Holm、共同 max-t、最佳三年移除及 50／100 bps
壓力均未過，只有 13/20 門檻。第 27 輪亦顯示單一 20 日排名欠缺完整單調性。

本輪只測試一個由台股參考研究抽出的、事前有界機制：同一股票若同時進入 5、10、15、
20 日動量排名的 Top-7，跨窗一致性會否比單一 20 日排序提供增量選股證據。只有最少三窗
共振的股票才佔用原七個股票分注；未被佔用的分注繼續持有 QQQ。候選須在相同股票比例、
相同五槽時鐘及相同成本下，與單窗、合資格池、完整現時股池、原第 30 輪及 QQQ 公平比較。

這仍使用同一批已見、以 2026 現時代號倒推的 905 個 survivor 事件。本輪不能修補歷史成分、
永久證券 ID、退市／退出經濟回報、公司行動或資料公告時間。真正可升格的下一步仍是取得
獲授權 provider package，原樣執行已凍結的正式 point-in-time 回測；本輪無論結果如何都只
是診斷，不能啟動 Paper、產生最新買入名單或落實實金。

## 禁止事項

結果後不得：

1. 改 5／10／15／20 日窗口、Top-7、最少三窗、最多七股、排名百分位或 tie-break；
2. 搜尋兩窗／四窗、Top-3／5／10、加權窗口、只採近期窗口或只採最強市場；
3. 改原 20／60 日合資格規則、905 個事件、D+1、20-session 持有期、五槽 assignment；
4. 把未佔用分注改為現金、SPY、TQQQ、SHY，或把合資格候選集中成更大權重；
5. 因結果加入 gap、ATR、止蝕、止賺、成交量、期權、行業、基本面或市況濾網；
6. 忽略 QQQ 沽出／買回及股票買入／沽出腿，或只向候選收較低成本；
7. 改成本、半期、危機年、最佳年份、尾部移除、NW lag、bootstrap block／seed 或 family；
8. 把調整價、分數股或現時 ticker 冒充真實成交、永久 ID、歷史成分或稅後經濟；
9. 因任一本輪門檻通過而重設策略、回填 Paper、建立持倉或改動正式協議。

任何輸入、父收據、事件、窗口排名、分注、槽位、交易腿、成本或 baseline 不能精確重建即
fail closed；不得刪除事件、補值、換用另一份行情或用第 38 輪結果改寫規則。

## 固定來源與收據

| 輸入 | 固定值 |
|---|---|
| 第 30 輪結果 commit | `a3602231917253775ab83a19e49ff3b237de1e89` |
| 第 30 輪機器收據 | `artifacts/short_term_qqq_replacement_overlay_validation.json` |
| 第 30 輪收據 SHA-256 | `ed9b733f8926fcd7ed5a9a061c98a2dfcc05d0b1e82a9ef12f25541b758cd8d8` |
| 第 29 輪機器收據 SHA-256 | `a35a3fa21b491250a3cce23e627a26e67a0d3219f796af4e2ec739d9f07e8e36` |
| 原始事件收據 SHA-256 | `fa2463cc8273a316e4a98428767b695eb85c74e9ac75c47b5ca34592102979e8` |
| 行情 archive SHA-256 | `d480fb82e712f06aabe0a98461e222344656b87022b8bda2cd7ccaa4c29ae88b` |
| 行情 panel fingerprint | `6a7ca6b83b1570007424daa46b0ff4e8fb4a655d39298a0f4f6d74c3b7ea3a66` |
| 現時觀察名單 SHA-256 | `b6002e4e151bd298884f8cdd6272b5cbfde8aedca47cb58b92830d4d92028014` |
| 事件 | 905 個；訊號 2006-08-04 至 2026-07-02；最後退出 2026-07-31 |
| 槽位 assignment SHA-256 | `3be9948565e7c58e951a50110e6063185c8c93a12b1cf97c2014b981b25c5547` |

台股研究紀律參考固定為：

- `tst_wocker@1af28a002d6f797399e94fa869808fef006a6ce1`：D+1 事件時鐘、股票池排名及組合層風險；
- `tw-block-warrant@5ba80c7736a69effeabf564225d679ddf75f8ba0`：多窗口共振、獨立證據及中性狀態；
- `tst_wocker_filter_lab@06c87b7a1735877c9ccbab3a339c1742814a5058`：開市前凍結資本、成本、同期 baseline
  及負結果稽核。

只轉移研究紀律。不得把台股 T86、盤後鉅額交易、權證流向、W3、漲跌停、台灣交易成本、
ATR 或原 repo 回報搬到美股日線資料。

## 固定事件、共振排序與分注

- 完全重播第 29／30 輪 905 個事件、同一 `eligible` universe 及五槽 assignment。合資格規則
  仍是訊號日調整收市已知的 20 日動量、60 日趨勢、股價高於 US$5、20 日中位美元成交額
  至少 US$20m；本輪不得改事件日期或合資格名單。
- 對每個事件日 D 及每個固定窗口 `h in (5, 10, 15, 20)`，動量固定為
  `adjusted_close[D] / adjusted_close[D-h sessions] - 1`，只可使用 D 或之前的資料。
- 每個窗口把同一 `eligible` universe 依動量降序、ticker 字典序升序打破完全相同值，取
  Top-7。零基 ordinal rank 的百分位固定為 `(universe_size - rank - 1) /
  (universe_size - 1)`，最佳為 1、最末為 0。
- 每股 `resonance_count` 是其出現在四個 Top-7 的次數。候選只保留 `resonance_count >= 3`，
  再依共振次數降序、四窗零基 ordinal `rank_sum` 升序、ticker 升序排序，最多七股。四窗
  universe size 相同，所以 `rank_sum` 與四窗百分位平均的排序完全等價；實際選擇只用整數
  `rank_sum`，百分位只作展示，避免浮點平台差異。不得用未來回報或窗口間相關性解決平手。
- 若事件有 N 隻候選，每股固定佔該槽位的 `1/7`，股票目標比例合計 `N/7`；餘下
  `1 - N/7` 留在 QQQ。N 可以是 0，不能把少於七股重新等權至 100%。
- 訊號後一個 session 調整開市成交，持有至第 20 個 session 調整收市；不得以訊號日收市
  成交。`slot = event_index mod 5`，五槽各 181 個事件、初始資金各 US$200，禁止跨槽轉資本。
- `complete` 固定為第 30 輪同一 25 隻 2026 現時股票。US$1,000 與分數股只作比例研究，
  不代表券商碎股、稅項、spread 或市場容量可行。

## 固定部分替換會計

共同日曆為 2006-08-04 至 2026-07-31；第一個可成交時點為 2006-08-07 開市：

1. 五槽各 US$200。首次全市場成交日，未啟動事件的槽位買入 QQQ；啟動事件的槽位按固定
   股票比例買入股票，其餘買入 QQQ。只收實際買入腿，不製造先買再沽的虛構成本。
2. 非事件期間每槽全數持有 QQQ。事件 entry open 先把 QQQ 由上一收市標記至 open，只沽出
   固定 `N/7` 比例並買入候選股票；未替換的 QQQ 不交易。
3. 事件期間股票分注及 QQQ 餘額分開按調整價格漂移，不每日再平衡。exit close 先標記至
   收市，只沽出股票並把所得買回 QQQ；未替換的 QQQ 不交易。
4. 主要資產 round trip 成本固定 20 bps，即每個實際買或賣腿 10 bps。正常被替換名義比例
   收取 QQQ sell、stocks buy、stocks sell、QQQ buy 四腿；首次買入及最後平倉只收實際腿。
5. 成本按各腿交易前的實際 notional 扣減；不得把四腿錯算為一個 round trip。另以資產
   round trip 50／100 bps，即每腿 25／50 bps，同步重建所有路徑。
6. 2026-07-31 收市後全部槽位平倉並收實際賣出腿；買入並持有基準亦只在首次買入及最後
   賣出收相同每腿成本。
7. 每日總資產須精確等於股票 driver、QQQ driver 及現金；首次成交後 long exposure 為
   100%、現金為零、leverage 不高於 1。任何 identity、比例、重疊或成本殘差高於 `1e-12`
   即停止。

## 九條固定路徑

1. `resonance3_qqq_overlay`：本輪唯一候選；事件期股票比例 N/7，餘額 QQQ。
2. `matched_20d_qqq_overlay`：每事件取原 20 日排名最高 N 股，每股 1/7，QQQ 餘額相同；
   用以隔離多窗共振相對單窗排序的增量。
3. `matched_eligible_qqq_overlay`：把相同 N/7 股票比例平均分配到該日全部 eligible 股票，
   其餘 QQQ；每股權重為 `N / (7 * eligible_count)`，不隨機抽 N 股。
4. `matched_complete_qqq_overlay`：把相同 N/7 股票比例平均分配到固定 25 股完整現時股池，
   其餘 QQQ；每股權重為 `N / (7 * 25)`。
5. `original_top7_qqq_overlay`：原第 30 輪 20 日 Top-7 全槽替換路徑；20／50／100 bps 結果
   必須與父輪逐日精確一致。
6. `matched_qqq_switch_placebo`：股票比例仍全持有 QQQ，但按候選每事件 N/7 比例及相同實際
   時點收取相同換倉腿成本；用以分開選股差額與部分換手成本。
7. `qqq_buy_hold`：首次 open 買入、最後 close 沽出，只收一次 QQQ round trip。
8. `spy_buy_hold`：同一起訖及成本的 SPY 基準。
9. `shy_buy_hold`：同一起訖及成本的 SHY 基準，亦作 excess return 現金代理。

候選對其餘八條路徑形成固定八假說 family。所有 matched 路徑每事件的目標股票比例、交易
時點及可歸因成本須與候選逐事件相同；`matched_qqq_switch_placebo` 不得因買賣同一 ticker
而省略成本。

## 固定指標與統計

每條路徑呈列：總回報、CAGR、年率化波幅、SHY 日回報超額 Sharpe／Sortino、最大跌幅、
Calmar、US$1,000 期末值、年率化換手、成本拖累、平均股票／QQQ 曝險及最小現金。另呈列
每事件候選數 N、股票目標比例、各共振次數、ticker 選擇收據及各窗口排名。

八個每日差額使用同一 5,028-session 日曆並呈列：

- 平均／中位日差、年率化算術差、正值比例；
- Newey–West lag 20 兩尾 t 與普通常態 p；
- 八假說 Holm p；
- 63-session circular moving-block、20,000 共同路徑、seed `38202608` single-step max-t p；
- 固定前半至 2016-07-29、後半由 2016-08-01；
- 每個曆年 compounded difference。

正式全專案搜尋次數由 6,221 加本輪八假說至 **6,229**；候選對 QQQ buy-and-hold 的普通
p 另呈列 6,229 次 Bonferroni，不得重設搜尋次數。事件級選擇分布及 regime 只作事前固定
壓力描述，不另挑選一條冒充較小 family。

## 固定壓力

- **最佳三年移除**：按候選相對 QQQ buy-and-hold 的曆年 compounded difference 排名，
  移除最高三年，在其餘共同 session 重算 NW lag 20。
- **危機期**：固定 2008、2020、2022，呈列九路徑回報及最大跌幅，並比較候選與 QQQ。
- **事前已知市場方向**：以訊號日已知的 QQQ 20-session 動量分成 `>=0` 與 `<0`，對候選
  每事件「N/7 ×（候選股票籃子 gross return - QQQ gross return）」各自只呈列事件數、
  平均 N、平均股票比例及平均／中位差；不另計 p 值，不得把較好一組變成開關。
- **成本**：資產 round trip 50／100 bps 同步重建九路；不得只提高候選成本。
- **最有利事件移除**：按上述候選相對 QQQ event gross difference 排名，移除最高 46 個
  事件後，用同一剔除清單重建六條 overlay；被移除事件全槽維持 QQQ 且不收虛構換倉成本。
- **身份**：報告及決策須明示 survivor cohort、正式就緒 1/18、point-in-time 1/20、
  合資格 provider package 0、正式策略 run 0、Paper 全現金。

## 二十項事前反證門檻

1. protocol、父收據、行情、panel、watchlist、事件及三個參考 commit 精確；
2. 第 30 輪 905 個事件、日期、原 Top-7／eligible／complete 回報及 assignment 逐列重播；
3. 五槽各 181 事件、同槽不重疊、最大 concurrency 五個；
4. 四窗動量、Top-7、百分位展示、整數 rank-sum、共振次數、排序及最多七股逐列精確且
   無未來資料；
5. 候選與三個 matched 路徑逐事件 N、N/7 股票比例、1-N/7 QQQ 餘額精確；
6. 九路同一日曆，每日資產、driver、交易腿及成本 identity 誤差不高於 `1e-12`，首次成交
   後 100% long、零現金及無槓桿；
7. `original_top7_qqq_overlay` 與第 30 輪逐日一致，`matched_qqq_switch_placebo` 與 QQQ 價格
   及固定部分換手成本逐日一致；
8. 候選 CAGR 高於 QQQ buy-and-hold；
9. 候選 US$1,000 期末值高於 QQQ buy-and-hold；
10. 候選 SHY-excess Sharpe 高於 QQQ buy-and-hold；
11. 候選最大跌幅不得比 QQQ 深超過 5 個百分點；
12. 候選 CAGR 高於原第 30 輪 Top-7 overlay；
13. 候選 CAGR 高於 matched 20 日 overlay；
14. 候選 CAGR 同時高於 matched eligible 及 matched complete overlay；
15. 候選對 QQQ 的平均日差為正、NW t 不低於 1.96、Holm 及共同 max-t p 均不高於 0.05；
16. 候選對 matched 20 日、eligible、complete 的平均日差均正、NW t 均不低於 1.96、
    Holm 及共同 max-t p 均不高於 0.05；
17. 候選對 QQQ、原 Top-7、matched 20 日、eligible、complete 的前後兩半平均日差全正；
18. 移除相對 QQQ 最佳三年後，平均日差仍正且 NW t 不低於 1.96；
19. 2008／2020／2022 每段候選回報均不低於 QQQ、最大跌幅不比 QQQ 深超過 5pp，而且
    QQQ 事前 20 日動量非負／負兩組的平均事件差均正；
20. 6,229 次 Bonferroni p 不高於 0.05；50／100 bps 及移除最有利 46 事件後，候選 CAGR
    仍同時高於 QQQ、原 Top-7、matched 20 日、eligible 及 complete overlay。

任何一項未通過即 `not_rejected_by_round38=false`。即使 20/20，本輪仍因同一已見 survivor
樣本而固定 `can_promote_from_this_round=false`、`new_strategy_created=false`、
`paper_status=all_cash_not_started` 及 `real_money_action_usd=0`。只有合格 point-in-time／
退市／公司行動數據 20/20、按既有正式預先登記運行一次，再完成至少 252 個新增 session
及 12 次換倉，才可另行評估由全現金啟動 Paper。

## Fail-closed 控制與攻擊

實作須保存至少 34 道控制及 34 項單欄變異攻擊，覆蓋：protocol hash／commit、第 30／29
輪及原始事件收據、snapshot、panel、watchlist、三個參考 commit、事件／cohort／訊號、
四個窗口、Top-7、百分位、共振門檻、tie-break、N/7 分注、五槽 assignment、QQQ 底倉、
部分四腿成本、九路徑、原 Top-7 identity、matched placebo identity、SHY excess、100%
曝險、無槓桿、日線 identity、八假說 family、NW lag、bootstrap、固定半期、危機、regime、
尾部、6,229 trials、現時身份、Paper 及實金越權。每項只改一欄並命中穩定錯誤碼。

## 固定輸出與發佈邊界

若首次計算成功，輸出：

- `artifacts/short_term_multi_window_resonance_validation.json`；
- `site/data/short-term-multi-window-resonance.json`；
- `docs/SHORT_TERM_MULTI_WINDOW_RESONANCE_RESEARCH_REPORT.md`。

報告及網站使用香港金融用詞，完整呈列九條路徑、八假說、選擇分布、交易腿、成本、危機、
半期、最佳年份、regime、46-event 壓力、20 道門檻、控制、攻擊及限制；不得只展示最好數字。
短線 Paper 維持全現金、持倉 0；US$1,000 只作讀者歷史尺度示例，實金動作固定 US$0。
