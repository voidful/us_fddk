# v12 階層式三態：三段既有資料第一次計算前凍結協議

凍結時間：2026-08-01T18:29:58Z

狀態：v10 在任何權重或績效計算前因 Yahoo 未提供 1971–1988 `^DJI` 而封存；
v11 改用事前指定的 S&P DJI 官方 Excel，但唯一一次 GET 收到 HTTP 403，因此
資料第 30 門失敗，也沒有計算任何策略權重或績效。v12 不回改 v10/v11、不重試
官方檔、不加入替代資料。它保留 v10/v11 尚未計算的同一套 60/40 階層式三態
規則，只在三段已凍結、可驗證的 A/B/C 資料上第一次計算。

三段資料及過去 v9 結果都已看過，所以這不是 data-independent preregistration。
本規則雖在 v10 取數前已完整指定，但仍按全專案第 6,109 次搜尋揭露 DSR。第一次
v12 權重或績效出現後，不得更換比例、狀態順序、日期、成本、時鐘、基準或門檻。

## 研究依據與限制

- Jegadeesh and Titman (1993) 記錄中期動量與其後反轉：
  https://onlinelibrary.wiley.com/doi/10.1111/j.1540-6261.1993.tb04702.x
- Moskowitz and Grinblatt (1999) 記錄產業動量：
  https://onlinelibrary.wiley.com/doi/10.1111/0022-1082.00146
- Hurst, Ooi and Pedersen 的長期多市場研究支持趨勢機制可能跨年代出現：
  https://www.aqr.com/insights/research/journal-article/a-century-of-evidence-on-trend-following-investing

這些來源只支持一般假說，不證明本規則有 alpha。B/C 使用價格指數且防守是
零利息 CASH，只能視為機制敏感度，不能冒充 ETF 總報酬或真實可成交歷史。

## 唯一策略規則

每個完整月末 `t`，只用當日已知收盤資料：

1. 永久配置 60% 核心市場。
2. 核心與成長的 12–1 報酬固定為 `close(t-21) / close(t-252) - 1`。
3. 固定依序決定其餘 40%：
   - `growth`：成長 12–1 嚴格高於核心，且成長收盤嚴格高於自己的 200 日 SMA；
     槽位持有成長。
   - `core`：growth 不成立，但核心收盤嚴格高於自己的 200 日 SMA；槽位回核心，
     總配置 100% 核心。
   - `defense`：前兩項皆不成立；槽位持有防守資產。
4. 成長條件缺失、暖機不足或相等時繼續檢查核心；核心趨勢也缺失或相等時使用
   defense，不得把缺值當成積極訊號。
5. 正式期前最後一個有效完整月末產生初始訊號。之後每月重算，但只在
   `growth`／`core`／`defense` 三態改變時產生新訊號；狀態不變不交易，持倉
   自然漂移，不為回到 60/40 而月月再平衡。
6. 訊號在收盤 `t` 形成，三個資產都在下一共同交易日的調整後開盤成交。
7. A 防守固定 `SHY`；B/C 固定常數 `CASH=1.0`、零報酬、零利息。
8. 不槓桿、放空、停損、波動縮放、確認月數、月中切換或依結果改參數。
9. 基準成本 10 bps、壓力成本 50 bps，乘以單邊換手；hard benchmark 使用完全
   相同執行時鐘與成本定義。

## 凍結資料與期間

### A. 可交易 ETF 主期

- `artifacts/snapshot_20260731_6a7ca6b8.zip`；panel
  `6a7ca6b83b1570007424daa46b0ff4e8fb4a655d39298a0f4f6d74c3b7ea3a66`；archive
  `d480fb82e712f06aabe0a98461e222344656b87022b8bda2cd7ccaa4c29ae88b`。
- 核心 `SPY`、成長 `QQQ`、防守 `SHY`。
- 正式期 2006-07-31–2026-07-31；兩半 2006-07-31–2016-07-29、
  2016-08-01–2026-07-31。

### B. 舊 Nasdaq-100 代理期

- `artifacts/snapshot_ndx_proxy_19851001_20060728_4814654a.zip`；panel
  `4814654a4abb4ea5ef0eb52763e233e13bc7088d51ca506eb94c7e335f5f4faa`；archive
  `ede88d5906411182e454d2e43442e7b5af61c392eab75e4235d5f22d3112f78d`。
- `artifacts/cross_market_gspc_19870101_20060728_fbe6b740.zip`；panel
  `fbe6b7403574d3296f371ed77c9831cca605b45a5dc5d2a0becfc02ec22f9e2f`；archive
  `2406c622d7b4c85666512ef84b3853b8729c5fe6b4e50256270f60a6273ecacd`。
- 共同日核心 `^GSPC`、成長 `^NDX`、防守 `CASH`。
- 正式期 1989-01-03–2006-07-28；兩半 1989-01-03–1997-09-30、
  1997-10-01–2006-07-28。

### C. Nasdaq Composite 外部期

- `artifacts/snapshot_v9_ixic_19710205_19881230_76bc29b6.zip`；panel
  `76bc29b61c480e8c44032e4aeaea801e9ea97a1aebceb758bda84df8a8b7d2c9`；archive
  `b845aecd3175584f8dc40e0db8e93ec9427e2a9f491f0824ec7264f6cda9eb22`。
- `artifacts/snapshot_v9_gspc_19710205_19881230_414d7879.zip`；panel
  `414d787995baeceb921bb088d5b54d08612e8b60d7a8443785c9603335ffc5ca`；archive
  `b5bcc28cf4fdddc83e60bf08601c83cd67eff44132c92a4980d6d37a20a2d471`。
- 共同日核心 `^GSPC`、成長 `^IXIC`、防守 `CASH`。
- 正式期 1973-01-03–1988-12-30；兩半 1973-01-03–1980-12-31、
  1981-01-02–1988-12-30。

三段年化 252；NW lag 9；五年滾動 1,260 個共同 sessions，於完整月末取樣。

## 29 道凍結門檻

每段 hard benchmark：A=`SPY`、B/C=`^GSPC`。以下七道分別在 A/B/C 檢查，
共 21 道：

1. 10 bps 下 CAGR 勝 hard benchmark 至少 10 bps／年。
2. Sharpe 高於 hard benchmark。
3. 最大回撤不得比 hard benchmark 深超過 5 個百分點。
4. Calmar 高於 hard benchmark。
5. 50 bps 下 CAGR 仍勝 hard benchmark至少 10 bps／年。
6. 固定前後兩半 CAGR 都各勝 hard benchmark 至少 10 bps／年。
7. 五年滾動 CAGR 勝 10 bps 的勝率至少 60%，且差中位數為正；無視窗即失敗。

跨資料門檻：

22. 三段至少 95% 正式交易日權重和為 1，所有權重非負、不得槓桿。
23. 三段快照雜湊、共同日期、暖機、防守翻譯、無缺值、來源與 next-open 時鐘
    契約全部通過；v10/v11 失敗收據仍保留且沒有被改寫。

統計門檻：

24–26. A/B/C 每段主動報酬 NW t 至少 1.96。
27–29. A/B/C 每段主動報酬 PSR 至少 95%。

- 另揭露三段各自按 6,109 次搜尋計算的 DSR；任一低於 95% 都明示選擇偏誤
  未排除。DSR 是 promotion sensitivity，不刪除、不調低試驗數。
- 100% 成長與一次性 60/40 只作機會成本背景，不替代 hard benchmark。

## Paper 與實金決策

- `Paper-entry gates` 固定為 1–23；23/23 才能從主資料最後日之後建立全新、
  隔離的 v12 Paper，禁止歷史回填或沿用舊帳戶。
- 29/29 才可標記 `historically_confirmed=true`，仍不等於實金授權。
- v12 Paper 至少累積 252 個新增交易日與 6 次完成三態切換；扣成本報酬為正、
  勝同起點 SPY、回撤不深於 SPY，且前瞻主動 NW t≥1.96、PSR≥95%，才進入
  實金參考評估。
- 任一 Paper-entry gate 失敗：封存負結果、不建立 v12 Paper、不調參救援。
