# 美股短線第 39 輪：龍頭回調—回升 10 日確認協議

凍結日期：2026-08-09

狀態：**首次候選選擇、回報及資金路徑計算前凍結**

研究角色：現時 25 股 survivor cohort 的只讀反證沙盒；不可建立 Paper、不可產生買入名單、
不可授權實金。

## 研究問題與停止邊界

第 38 輪顯示，把 5／10／15／20 日排名做三窗共振，並沒有勝過原本簡單的 20 日 Top-7。
本輪不得再改動動量窗口、Top-K、合資格濾網或市場曝險來救結果，只回答一個新的問題：

> 原 20 日 Top-7 龍頭中，只有在訊號日同時出現固定的回調、回升及結構性 reward/risk
> 確認時，以十個交易日持有期暫時取代部分 QQQ，能否在相同股票比例、時鐘及成本下，
> 穩健勝過未使用該結構確認的公平基準？

三個台股參考專案的固定來源 commit：

- `tst_wocker@1af28a002d6f797399e94fa869808fef006a6ce1`：20 日動量、60 日趨勢、流動性、
  Top-7 及 D+1 開市成交母訊號；
- `tw-block-warrant@5ba80c7736a69effeabf564225d679ddf75f8ba0`：D 日後成交、重疊持倉、逐腿成本及
  十日持有的外部先驗；
- `tst_wocker_filter_lab@06c87b7a1735877c9ccbab3a339c1742814a5058`：
  `strategies/entry_confirmation.py` 的 ATR、20／60 日高位、10 日低位、3%–16% 回調、回升及
  `reward_risk >= 1.60` 結構分支。

本輪只隔離上述 `setup_recovery` 價格結構，不聲稱複製該專案完整 CONFIRMED 策略；美股
快照沒有台股法人、融資融券、隔夜全球龍頭或逐日 point-in-time 成分資料，所以不得用零值
冒充那些輸入。成交量確認、VIX 開關、ATR 止賺／止蝕、gap filter、sector cap、倉位加碼、
其他 pullback／RR／持有期及任何參數網格全部排除。

即使全部門檻通過，本輪仍是已見現時代號樣本，固定
`can_promote_from_this_round=false`、`new_strategy_created=false`、
`paper_status=all_cash_not_started`、`real_money_action_usd=0`。

## 固定輸入與不可回改收據

| 輸入 | 固定值 |
|---|---|
| 主分支父 commit | `1d506c987781e1c692543dba3f6483cfe57c160d` |
| 第 38 輪收據 | `artifacts/short_term_multi_window_resonance_validation.json` |
| 第 38 輪 SHA-256 | `5c066a4275f4ba851d2a18f3b0274c4f86374717a0507c721ebc9c46cd60fea5` |
| 第 30 輪收據 SHA-256 | `ed9b733f8926fcd7ed5a9a061c98a2dfcc05d0b1e82a9ef12f25541b758cd8d8` |
| 第 29 輪收據 SHA-256 | `a35a3fa21b491250a3cce23e627a26e67a0d3219f796af4e2ec739d9f07e8e36` |
| 原始事件收據 SHA-256 | `fa2463cc8273a316e4a98428767b695eb85c74e9ac75c47b5ca34592102979e8` |
| 行情快照 | `artifacts/snapshot_20260731_6a7ca6b8.zip` |
| 行情 SHA-256 | `d480fb82e712f06aabe0a98461e222344656b87022b8bda2cd7ccaa4c29ae88b` |
| panel fingerprint | `6a7ca6b83b1570007424daa46b0ff4e8fb4a655d39298a0f4f6d74c3b7ea3a66` |
| watchlist SHA-256 | `b6002e4e151bd298884f8cdd6272b5cbfde8aedca47cb58b92830d4d92028014` |
| 原事件 | 905 宗；2006-08-04 至 2026-07-02 訊號日 |
| 完整現時 cohort | 固定 25 股；不得新增、刪除或以結果替換 |
| 共同比較日曆 | 2006-08-07 至 2026-07-31，共 5,028 個 XNYS session |
| 初始歷史尺度 | US$1,000；五個 US$200 資金槽 |
| 正式就緒 | formal 1/18；point-in-time 1/20；合資格 provider package 0 |

行情為同一凍結 Yahoo Finance 快照，`open/high/low/close` 均使用
`raw_ohlc * (adj_close/raw_close)` 的一致調整口徑。這只能防止 OHLC 混用，不會消除日後修訂、
現時 survivor cohort、缺失歷史成分、退市／收購及永久證券 ID 的偏誤。

## 母訊號、結構特徵與唯一候選

### 母訊號逐字不變

每個已完成星期的最後一個 XNYS session 為訊號日 `D`。沿用第 29／30／38 輪：

1. 20 日調整收市回報完整；
2. `close_D > 60-session simple moving average_D`；
3. `close_D > US$5`；
4. 20 日調整收市乘成交量的中位數不少於 US$20,000,000；
5. 至少七股合資格；按 20 日回報降序、ticker 升序打破同值，取原 Top-7。

不得以本輪 OHLC 結構改變 eligible、重排 Top-7 或回補不足七股。

### 訊號日已知的固定結構

只對原 Top-7 計算，所有窗口包括 `D` 並只使用 `D` 或以前資料：

```text
TR_s       = max(high_s-low_s, abs(high_s-close_{s-1}), abs(low_s-close_{s-1}))
ATR14_D    = mean(TR_{D-13:D})
high20_D   = max(close_{D-19:D})
high60_D   = max(close_{D-59:D})
low10_D    = min(low_{D-9:D})

pullback   = max(0, 1 - close_D/high20_D)
rebound    = (close_D > close_{D-1}) and (close_D > 1.01*low10_D)
target     = high60_D + 1.5*ATR14_D
stop_ref   = low10_D - 0.5*ATR14_D
upside     = max(target-close_D, 0.5*ATR14_D)
downside   = max(close_D-stop_ref, 1.0*ATR14_D)
reward_risk = clip(upside/downside, 0, 8)

confirmed  = 0.03 <= pullback <= 0.16 and rebound and reward_risk >= 1.60
```

`ATR14` 必須有完整 14 個 TR 及前一日收市，窗口中任何 OHLC 缺失、非有限、非正、
`high < max(open,close)`、`low > min(open,close)` 或 `high < low` 即在結果前停止。`target` 與
`stop_ref` 只用來形成事前 reward/risk；**不得**在持有期觸發止賺或止蝕。

唯一候選 `lpr10_qqq_overlay`：每個通過結構確認的原 Top-7 股票固定佔該事件槽位 `1/7`；
若通過 `N` 股，股票比例為 `N/7`，餘下 `1-N/7` 留在 QQQ。`N=0` 保留全 QQQ、零虛構
換倉；不得把剩餘股票重新集中至 100%，亦不得用 reward/risk 排名或加權。

## 固定成交時鐘、資金槽與成本

- 訊號：`D` 調整收市後；入場：下一個 XNYS session `D+1` 調整開市；
- 固定持有十個 session，入場日為第 1 日，第 10 個 session 調整收市退出；
- 原 905 事件按 `event_index mod 5` 指派五槽；同槽下一事件前必須已退出，槽位不得借貸；
- 每槽初始 US$200，其他時段持有 QQQ；每日總資產為五槽資產總和；
- 首次成交後 long exposure 必須為 100%、現金為零、leverage 不高於 1；
- primary 每個實際買／賣腿 10 bps。一次正常部分替換完整收取
  `QQQ sell + stock buy + stock sell + QQQ buy` 四腿；
- 壓力每腿 25／50 bps，等同每資產 round trip 50／100 bps；所有公平路徑同步重建；
- US$1,000 操作診斷另列每隻股票名義金額、原始子委託數及每子委託 US$0.01／US$0.05
  固定費壓力；這不是宣稱任何券商實際收費。

每日 driver、資產、成本、股票／QQQ 曝險、現金及子委託 identity 最大容許誤差 `1e-12`。

## 九條固定路徑

1. `lpr10_qqq_overlay`：唯一候選；通過結構確認的原 Top-7 每股一個 `1/7` 子槽。
2. `matched_topn_10d_overlay`：每事件取原 Top-7 中動量最高 `N` 股，每股 `1/7`；隔離
   回調—回升結構相對「只是取前 N 名」的增量。
3. `matched_eligible_10d_overlay`：相同 `N/7` 股票比例平均分配至當日全部 eligible；其餘 QQQ。
4. `matched_complete_10d_overlay`：相同 `N/7` 平均分配至固定 25 股現時 cohort；其餘 QQQ。
5. `original_top7_10d_overlay`：十日內完整以原 Top-7 取代事件槽 QQQ；不使用本輪 N。
6. `matched_qqq_switch_placebo`：相同 N、比例及時點仍持有 QQQ，但照收部分四腿成本。
7. `qqq_buy_hold`：首次開市買入、最後收市沽出，只收一次 QQQ round trip。
8. `spy_buy_hold`：相同起訖及成本的 SPY。
9. `shy_buy_hold`：相同起訖及成本的 SHY，亦作超額回報現金代理。

候選對其餘八條路徑形成固定八假說 family。所有 matched 路徑逐事件 N、股票比例、時鐘及
比例成本必須相同；固定費診斷則按各路徑真實子委託數收取，不得為候選省略成本或令 baseline
承擔不存在的 ghost order。第 30 輪 20 日 Top-7 另作已凍結歷史參考，不放入不同持有期的
共同日差 family。

## 固定統計、切片及壓力

每條路徑呈列總回報、CAGR、年率化波幅、SHY-excess Sharpe／Sortino、最大跌幅、Calmar、
US$1,000 期末值、年率化換手、比例及固定費拖累、平均股票／QQQ 曝險、最小現金、driver
腿及子委託數。

八個每日差額使用同一 5,028-session 日曆：

- 平均／中位日差、年率化算術差、正值比例；
- Newey–West lag 10 兩尾 t 及普通常態 p；
- 八假說 Holm p；
- 63-session circular moving-block、20,000 共同路徑、seed `39202608`、零假設下去中心化的
  single-step max-t p；
- 固定前半至 2016-07-29、後半由 2016-08-01；每個曆年 compounded difference。

全專案搜尋次數由 6,229 加八列至 **6,237**；候選對 QQQ 的普通 p 另列 6,237 次
Bonferroni，不得重設。

固定壓力：

1. 每腿 25／50 bps，同步重建九路；
2. 每子委託 US$0.01／US$0.05，按真實 order count 重建；
3. 按候選相對 QQQ 年度 compounded difference 移除最佳三年，重算 NW lag 10；
4. 固定 2008、2020、2022，呈列回報及最大跌幅；
5. 以訊號日已知 QQQ 20 日回報 `>=0`／`<0` 分組，只診斷候選對 matched Top-N 事件差；
6. 按候選相對 matched Top-N 的事件 gross 增量移除最有利 46 宗事件，用同一清單重建六條
   overlay，不重排或改 N；
7. 固定前後半、非空事件數、N 分布、pullback／reward-risk 分布及票據大小完整呈列。

不得計算 5／15／20 日持有、2%／5%／10% 回調、其他 RR、ATR、target、stop、排序、
market regime 或入場變體。那些只能作單欄 mutation attack，不能成為報告候選。

## 二十二項事前反證門檻

1. protocol、父 commit／收據、行情、panel、watchlist、事件及三個參考 commit 精確；
2. 第 29／30 輪 905 個事件、日期、eligible、原 Top-7、20 日排名及五槽 assignment 逐列重播；
3. 五槽各 181 事件、十日持有、同槽不重疊、最大 concurrency 五；
4. 調整 OHLC 一致，TR／ATR14／high20／high60／low10／pullback／rebound／reward-risk 逐列精確，
   只用 D 或以前資料；
5. N=0–7、原 Top-7 子集、每股 1/7、N/7 股票比例及 QQQ 餘額逐事件精確；非空事件至少
   181 宗，前後半各至少 75 宗；
6. 九路同一日曆，每日 driver、資產、比例成本、股票／QQQ 曝險、現金及槓桿 identity
   誤差不高於 `1e-12`；
7. `matched_qqq_switch_placebo` 與 QQQ 價格及部分換手成本逐日一致；原 Top-7 十日事件回報
   與既有第 1 輪十日事件收據逐列一致；
8. 候選 CAGR 高於 QQQ buy-and-hold；
9. 候選 US$1,000 期末值高於 QQQ buy-and-hold；
10. 候選 SHY-excess Sharpe 高於 QQQ buy-and-hold；
11. 候選最大跌幅不得比 QQQ 深超過 5 個百分點；
12. 候選 CAGR 高於 `matched_topn_10d_overlay`；
13. 候選 CAGR 高於 `original_top7_10d_overlay`；
14. 候選 CAGR 同時高於 matched eligible 及 matched complete；
15. 候選對 QQQ 平均日差為正、NW t 不低於 1.96、Holm 及共同 max-t p 均不高於 0.05；
16. 候選對 matched Top-N、原 Top-7、eligible、complete 的平均日差均正、NW t 均不低於
    1.96、Holm 及共同 max-t p 均不高於 0.05；
17. 候選對 QQQ、matched Top-N、原 Top-7、eligible、complete 的前後兩半平均日差全正；
18. 移除相對 QQQ 最佳三年後，平均日差仍正且 NW t 不低於 1.96；
19. 2008／2020／2022 每段候選回報均不低於 QQQ，最大跌幅不比 QQQ 深超過 5pp；
20. QQQ 事前 20 日動量非負／負兩組，候選相對 matched Top-N 的平均事件增量均正；
21. 6,237 次 Bonferroni p 不高於 0.05；
22. 每腿 25／50 bps、每子委託 US$0.01 及移除最有利 46 宗事件後，候選 CAGR 仍同時高於
    QQQ、matched Top-N、原 Top-7、eligible 及 complete。

任何一項未通過即 `not_rejected_by_round39=false`。22/22 亦只表示同一已見 survivor 樣本
沒有在本輪被推翻，不得升格。只有合法 point-in-time／退市／公司行動數據 20/20、按既有
正式預先登記運行一次，再由下一個新增交易日全現金開始累積至少 252 session 及 12 次完成
換倉，才可另行評估 Paper。

## Fail-closed 控制、攻擊與輸出

實作至少保存 48 道控制及 48 項一次只改一欄的攻擊，覆蓋：protocol hash／commit、父收據、
snapshot／panel／watchlist、三個參考 commit、事件／cohort／signal、adjusted OHLC、TR、ATR
窗口、20／60 日 close high、10 日 low、pullback 上下界、rebound、target／stop、RR floor／
clip、Top-7 子集、N／7、不重新集中、D+1／10 session、五槽 assignment、QQQ 底倉、四腿
比例成本、子委託固定費、九路徑、placebo identity、SHY excess、100% long、零槓桿、日線
identity、八假說 family、NW lag、bootstrap、固定半期、危機、QQQ 分組、最佳年、46-event、
6,237 trials、現時身份、Paper 及實金越權。每項須命中穩定語義錯誤碼。

首次計算成功後才可產生：

- `artifacts/short_term_leader_pullback_rebound_validation.json`；
- `site/data/short-term-leader-pullback-rebound.json`；
- `docs/SHORT_TERM_LEADER_PULLBACK_REBOUND_RESEARCH_REPORT.md`。

報告與網站使用香港金融用詞，完整呈列九路徑、八假說、選擇／特徵分布、比例及固定成本、
危機、半期、最佳年份、QQQ 分組、46-event 壓力、22 道門檻、控制、攻擊及限制；不得只展示
最好數字，不呈列最新逐股名單或配置計算器。US$1,000 只作歷史尺度，短線 Paper 保持全現金、
持倉 0，實金動作固定 US$0。
