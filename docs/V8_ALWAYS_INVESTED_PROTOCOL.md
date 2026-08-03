# v8 永遠持股相對成長傾斜：第一次計算前凍結協議

凍結時間：2026-08-01T17:24:50Z

狀態：此規則在第一次計算 v8 權重或績效前凍結。ETF、指數資料與 v7 結果均已
被看過，因此不是 data-independent preregistration；v8 必須計入全專案第 6,105
次研究搜尋。第一次結果出現後不得更換比例、回顧窗、均線、期間、成本或門檻。

## 研究依據與適用邊界

- Jegadeesh and Titman (1993) 在股票橫斷面記錄 3–12 個月 winner-minus-loser
  動量，但也記錄形成後的部分反轉：
  https://onlinelibrary.wiley.com/doi/10.1111/j.1540-6261.1993.tb04702.x
- Moskowitz and Grinblatt (1999) 記錄產業動量：
  https://onlinelibrary.wiley.com/doi/10.1111/0022-1082.00146
- Hurst, Ooi and Pedersen 的長期多市場研究支持趨勢機制可跨資產出現：
  https://www.aqr.com/insights/research/journal-article/a-century-of-evidence-on-trend-following-investing

這些來源只支持一般研究假說，不直接證明 QQQ 相對 SPY 有 alpha，也不支持任何
保證跑贏。v8 必須由下列凍結資料、同曝險基準、時間切片與前瞻 Paper 自己舉證。

## 唯一可交易規則

標的固定為 `SPY` 與 `QQQ`。每個完整月末：

1. 永久配置 50% `SPY`。
2. 分別計算 `QQQ` 與 `SPY` 從 `t-252` 到 `t-21` 的調整後總報酬。
3. 若 `QQQ` 的 12–1 動量嚴格高於 `SPY`，且 `QQQ` 調整後收盤價嚴格高於
   過去 200 個交易日簡單移動平均，另一個 50% 槽位配置 `QQQ`。
4. 其他情況，另一個 50% 槽位也配置 `SPY`。同分、缺值或剛好等於均線都不
   配置 QQQ。
5. 月末收盤產生訊號，下一個新增交易日用調整後開盤價模擬成交。
6. 永遠 100% 股票曝險；不使用 SHY、現金擇時、槓桿、放空、停損、波動縮放、
   確認月數或月中切換。
7. 基準成交成本 10 bps，壓力成本 50 bps。

### 公平基準與機會成本

- hard benchmark／selection-matched control 都是 100% `SPY`；策略與基準每月
  都是 100% 股票曝險，差異只來自風險開啟月用 50% QQQ 取代 50% SPY。
- 固定 50% SPY／50% QQQ 與 100% QQQ 只作機會成本背景，不替代 SPY hard
  gate，也不要求 v8 勝過 QQQ 才能進入 Paper。
- 網站必須把 v8 稱為成長傾斜政策；除非所有統計與前瞻門檻通過，不得稱為已
  證實 alpha 或可實金參考。

## 凍結資料與期間

### A. 可交易 ETF 主期

- 快照：`artifacts/snapshot_20260731_6a7ca6b8.zip`
- panel SHA-256：
  `6a7ca6b83b1570007424daa46b0ff4e8fb4a655d39298a0f4f6d74c3b7ea3a66`
- archive SHA-256：
  `d480fb82e712f06aabe0a98461e222344656b87022b8bda2cd7ccaa4c29ae88b`
- 正式期：2006-07-31–2026-07-31。
- 固定兩半：2006-07-31–2016-07-29、2016-08-01–2026-07-31。
- 年化 252；Newey–West lag 9；五年滾動 1,260 sessions，每個月末取樣。

### B. 不重疊舊指數代理期

- Nasdaq-100：`artifacts/snapshot_ndx_proxy_19851001_20060728_4814654a.zip`，
  panel `4814654a4abb4ea5ef0eb52763e233e13bc7088d51ca506eb94c7e335f5f4faa`，
  archive `ede88d5906411182e454d2e43442e7b5af61c392eab75e4235d5f22d3112f78d`。
- S&P 500：`artifacts/cross_market_gspc_19870101_20060728_fbe6b740.zip`，
  panel `fbe6b7403574d3296f371ed77c9831cca605b45a5dc5d2a0becfc02ec22f9e2f`，
  archive `2406c622d7b4c85666512ef84b3853b8729c5fe6b4e50256270f60a6273ecacd`。
- 只取共同交易日；唯一翻譯 `QQQ→^NDX`、`SPY→^GSPC`，不得串接 ETF 報酬。
- 正式期：1989-01-03–2006-07-28。
- 固定兩半：1989-01-03–1997-09-30、1997-10-01–2006-07-28。
- 代理是價格指數，不含股息，檢驗機制而不是 ETF 可交易績效。

## 統計與搜尋偏誤

- 經濟勝出必須 CAGR 至少高 10 bps／年；浮點數微差不算勝出。
- 主動報酬使用固定 lag 9 Newey–West 平均檢定。
- PSR 檢驗母體主動 Sharpe 高於 0 的機率是否至少 95%。
- 另揭露全專案 6,105 次搜尋懲罰的 DSR。因 v8 是看過 v7 後的派生規則，DSR
  不得省略；若未達 95%，即使可進 Paper 也不能稱為歷史統計確認。
- Paper 只取得新證據，不會把既有回測轉成獨立樣本。

## 20 道凍結歷史門檻

可交易 ETF 主期：

1. CAGR 勝 SPY 至少 10 bps／年。
2. Sharpe 高於 SPY。
3. 最大回撤不得比 SPY 深超過 5 個百分點。
4. Calmar 高於 SPY。
5. 50 bps 下 CAGR 仍勝 SPY 至少 10 bps／年。
6. 固定前後兩半 CAGR 都勝 SPY 至少 10 bps／年。
7. 五年滾動有效勝率至少 60%，且 CAGR 差中位數為正。
8. 主動報酬 Newey–West t 至少 1.96。
9. 主動報酬 PSR 機率至少 95%。
10. 至少 95% 交易日權重總和為 1，且不得有負權重或槓桿。

舊指數代理期：

11. CAGR 勝 S&P 500 至少 10 bps／年。
12. Sharpe 高於 S&P 500。
13. 最大回撤不得比 S&P 500 深超過 5 個百分點。
14. Calmar 高於 S&P 500。
15. 50 bps 下 CAGR 仍勝 S&P 500 至少 10 bps／年。
16. 固定前後兩半 CAGR 都勝 S&P 500 至少 10 bps／年。
17. 五年滾動有效勝率至少 60%，且 CAGR 差中位數為正。
18. 主動報酬 Newey–West t 至少 1.96。
19. 主動報酬 PSR 機率至少 95%。
20. 代理資料共同日期、唯一翻譯、暖機、無缺值與雜湊全部通過。

## Paper 與上線決策

- `Paper-entry economic gates` 固定為 1–7、10–17、20，共 16 道。16/16 才可
  從 2026-07-31 建立全新 v8 隔離 Paper；不得回填歷史成交。
- 8、9、18、19 是歷史統計確認門檻。20/20 才可標記
  `historically_confirmed=true`，但仍不代表可實金參考。
- 6,105 次 DSR 主期與代理期都列為 promotion sensitivity；任一低於 95% 時，
  網站必須明示選擇偏誤未排除。其缺口只能由新前瞻資料補強，不可改參數救援。
- v8 Paper 必須累積至少 252 個新增交易日與 6 次完成換倉；扣成本後為正、勝
  同起點 SPY、回撤不深於 SPY，且前瞻每日主動報酬 NW t 與 PSR 都達門檻，才
  能進入實金參考評估。
- 任一 Paper-entry gate 失敗：封存負結果、不建立 v8 Paper。
- 通過 Paper-entry 但未通過歷史統計：只允許隔離 Paper，網站不可顯示為今天
  可照單的配置。
