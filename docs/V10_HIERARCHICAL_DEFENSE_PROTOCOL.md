# v10 階層式成長／核心／防守三態：第一次計算前凍結協議

凍結時間：2026-08-01T18:13:09Z

狀態：v10 是看到 v9 負面結果後提出的結構性修正，不回改 v9。v9 顯示只把
成長槽位降到 40%、只在狀態改變時交易，仍無法同時通過 50 bps 成本、舊期
回撤與外部期後半。v10 保留相同 60/40 上限與低頻交易，但把風險關閉拆成兩層：
核心市場仍在長期趨勢上時，40% 槽位回核心；核心市場也跌破趨勢時，才移到防守。

主 ETF、舊 Nasdaq-100 代理與 v9 的 Nasdaq Composite 外部結果都已看過，
因此不是 data-independent preregistration，必須計入全專案第 6,107 次研究
搜尋。第四段會使用已看過的 `^IXIC` 與尚未下載、檢視或計算的 `^DJI`；它只對
核心指數選擇提供部分新證據，不是完全未見樣本。第一次 v10 權重或績效出現後，
不得更換比例、狀態順序、回顧窗、均線、期間、成本、基準或門檻。

## 研究依據與適用邊界

- Jegadeesh and Titman (1993) 記錄股票橫斷面的中期動量，也記錄其後反轉：
  https://onlinelibrary.wiley.com/doi/10.1111/j.1540-6261.1993.tb04702.x
- Moskowitz and Grinblatt (1999) 記錄產業動量：
  https://onlinelibrary.wiley.com/doi/10.1111/0022-1082.00146
- Hurst, Ooi and Pedersen 的長期多市場研究支持趨勢機制可能跨資產與年代出現：
  https://www.aqr.com/insights/research/journal-article/a-century-of-evidence-on-trend-following-investing
- S&P Dow Jones Indices 官方頁面說明 DJIA 於 1896-05-26 啟動，是 30 檔美國
  藍籌公司的價格加權指數，價格報酬 ticker 為 `INDU`：
  https://www.spglobal.com/spdji/en/indices/equity/dow-jones-industrial-average/
- Nasdaq 官方資料說明 Nasdaq Composite 於 1971-02-05 啟動並採市值加權：
  https://www.nasdaq.com/articles/nasdaq-composite-indextm%3A-50th-anniversary-brings-new-records-and-further-optimism

這些來源只支持研究假說與指數身分，不直接證明本規則有 alpha。DJIA 與
Nasdaq Composite 都是價格指數；它們只作機制和核心定義敏感度，不能冒充 ETF
含股息報酬。DJIA 只有 30 檔且價格加權，也不能取代 SPY 作正式可交易主基準。

## 唯一可交易規則

每個完整月末 `t`，只使用當日已知的調整後收盤資料：

1. 永久配置 60% 核心市場。
2. 分別計算核心與成長從 `t-252` 到 `t-21` 的報酬：
   `close(t-21) / close(t-252) - 1`。
3. 按固定優先順序決定其餘 40% 槽位：
   - `growth`：成長 12–1 報酬嚴格高於核心，且成長在 `t` 的收盤價嚴格高於
     自己截至 `t` 的 200 日簡單移動平均；槽位持有成長。
   - `core`：前項不成立，但核心收盤價嚴格高於自己的 200 日簡單移動平均；
     槽位也持有核心，總配置成為 100% 核心。
   - `defense`：前兩項都不成立；槽位持有防守資產。
4. 任一必要數值缺失、暖機不足或剛好相等，都不得進入較積極狀態：成長條件
   缺失時繼續檢查核心；核心趨勢也缺失時使用 defense。
5. 正式期開始前最後一個有效完整月末產生初始訊號，下一個共同交易日成交。
   此後每月重算狀態，但只在 `growth`／`core`／`defense` 三態改變時產生新訊號，
   下一個共同交易日成交。
6. 兩次狀態切換之間讓持倉自然漂移，不為回到 60/40 而月月再平衡。
7. 主 ETF 期防守資產固定為 `SHY`。三個價格指數代理組合固定用常數
   `CASH=1.0`、零報酬、零利息，不串接債券 ETF，也不讓防守利息美化代理結果。
8. 不使用槓桿、放空、停損、波動縮放、確認月數、月中切換或 v10 結果出現後
   的任何參數修正。
9. 基準成交成本 10 bps，壓力成本 50 bps，乘以單邊換手；市場基準也使用相同
   引擎與成本定義。

### 公平基準與機會成本

- 每段 hard benchmark 都是 100% 當段核心市場：A=`SPY`，B/C=`^GSPC`，
  D=`^DJI`。
- 100% 成長、一次性 60% 核心／40% 成長與 100% 核心只作機會成本背景；
  Paper 入口不要求勝過成長指數，但必須跨過 hard benchmark 的所有門檻。
- 網站只能把 v10 稱為階層式風險政策研究。除非全部歷史與前瞻門檻通過，
  不得稱為已證實 alpha、穩健實金策略或今天可照單的配置。

## 凍結資料、翻譯與期間

### A. 可交易 ETF 主期（已看過）

- 快照：`artifacts/snapshot_20260731_6a7ca6b8.zip`；panel
  `6a7ca6b83b1570007424daa46b0ff4e8fb4a655d39298a0f4f6d74c3b7ea3a66`；
  archive `d480fb82e712f06aabe0a98461e222344656b87022b8bda2cd7ccaa4c29ae88b`。
- 唯一對應：核心 `SPY`、成長 `QQQ`、防守 `SHY`。
- 正式期：2006-07-31–2026-07-31。
- 固定兩半：2006-07-31–2016-07-29、2016-08-01–2026-07-31。

### B. 不重疊舊 Nasdaq-100 代理期（已看過）

- Nasdaq-100：`artifacts/snapshot_ndx_proxy_19851001_20060728_4814654a.zip`，
  panel `4814654a4abb4ea5ef0eb52763e233e13bc7088d51ca506eb94c7e335f5f4faa`，
  archive `ede88d5906411182e454d2e43442e7b5af61c392eab75e4235d5f22d3112f78d`。
- S&P 500：`artifacts/cross_market_gspc_19870101_20060728_fbe6b740.zip`，
  panel `fbe6b7403574d3296f371ed77c9831cca605b45a5dc5d2a0becfc02ec22f9e2f`，
  archive `2406c622d7b4c85666512ef84b3853b8729c5fe6b4e50256270f60a6273ecacd`。
- 共同交易日唯一對應：核心 `^GSPC`、成長 `^NDX`、防守常數 `CASH`。
- 正式期：1989-01-03–2006-07-28。
- 固定兩半：1989-01-03–1997-09-30、1997-10-01–2006-07-28。

### C. Nasdaq Composite 外部期（v9 已看過）

- Nasdaq Composite：`artifacts/snapshot_v9_ixic_19710205_19881230_76bc29b6.zip`，
  panel `76bc29b61c480e8c44032e4aeaea801e9ea97a1aebceb758bda84df8a8b7d2c9`，
  archive `b845aecd3175584f8dc40e0db8e93ec9427e2a9f491f0824ec7264f6cda9eb22`。
- S&P 500：`artifacts/snapshot_v9_gspc_19710205_19881230_414d7879.zip`，
  panel `414d787995baeceb921bb088d5b54d08612e8b60d7a8443785c9603335ffc5ca`，
  archive `b5bcc28cf4fdddc83e60bf08601c83cd67eff44132c92a4980d6d37a20a2d471`。
- 共同交易日唯一對應：核心 `^GSPC`、成長 `^IXIC`、防守常數 `CASH`。
- 正式期：1973-01-03–1988-12-30。
- 固定兩半：1973-01-03–1980-12-31、1981-01-02–1988-12-30。

### D. DJIA 核心敏感度（凍結時 `^DJI` 尚未下載）

- 已凍結成長快照仍是 C 的 `^IXIC`，不得重新下載或替換。
- 新核心指定 Yahoo Finance via yfinance `^DJI`，下載範圍固定為
  1971-02-05–1988-12-30；首尾皆含。快照檔名、panel／archive 雜湊只能在
  下載後寫入獨立 data receipt，不得回寫本協議。
- 只取 `^DJI` 與既有 `^IXIC` 都有 OHLCV 的共同交易日；不得補值、插值、
  串接別的代號或在下載失敗後換供應商。
- 唯一對應：核心 `^DJI`、成長 `^IXIC`、防守常數 `CASH`。
- 正式期與固定兩半完全同 C，不得因結果移動日期。

B/C/D 都是價格指數，不含股息，只能檢驗機制。四段皆年化 252；Newey–West
lag 9；五年滾動 1,260 個共同 sessions，於每個完整月末取樣。日期邊界若非
共同交易日，只能在凍結區間內取實際存在日期，不得延長樣本。

## 經濟、統計與搜尋偏誤定義

- 經濟勝出必須 CAGR 至少高 hard benchmark 10 bps／年；浮點數微差不算。
- 每段各自用每日主動報酬與固定 lag 9 Newey–West 平均檢定。
- 每段各自以 PSR 檢驗母體主動 Sharpe 高於 0 的機率是否至少 95%。
- 另揭露全專案 6,107 次搜尋懲罰的 DSR。四段任一 DSR 未達 95% 時，都必須
  明示選擇偏誤未排除；DSR 是 promotion sensitivity，不得刪除或調低試驗數。
- D 與 C 共用已看過的成長路徑，只能稱 partial holdout；Paper 只取得新證據，
  不會把任何歷史回測轉成獨立樣本。

## 38 道凍結歷史門檻

以下 1–7 分別在 A、B、C、D 四段各檢查一次，共 28 道：

1. 10 bps 下 CAGR 勝 hard benchmark 至少 10 bps／年。
2. Sharpe 高於 hard benchmark。
3. 最大回撤不得比 hard benchmark 深超過 5 個百分點。
4. Calmar 高於 hard benchmark。
5. 50 bps 下 CAGR 仍勝 hard benchmark 至少 10 bps／年。
6. 固定前後兩半 CAGR 都各勝 hard benchmark 至少 10 bps／年。
7. 五年滾動 CAGR 勝 10 bps 的有效勝率至少 60%，且 CAGR 差中位數為正；
   沒有有效視窗即失敗。

跨資料完整性門檻：

29. 四段至少 95% 正式交易日權重總和為 1，所有權重非負且不得槓桿。
30. 四段快照雜湊、共同日期、暖機、防守翻譯、無缺值與資料契約全部通過。

以下統計門檻分別在 A、B、C、D 四段各檢查，共 8 道：

31–34. 每段主動報酬 Newey–West t 至少 1.96。
35–38. 每段主動報酬 PSR 至少 95%。

## Paper 與上線決策

- `Paper-entry gates` 固定為 1–30。30/30 才可從主資料最後日之後建立全新、
  隔離的 v10 Paper；不得回填歷史成交，也不得沿用任何舊 Paper 成績。
- 38/38 才可標記 `historically_confirmed=true`，但仍不代表可實金參考。
- 四段 6,107 次 DSR 都列為 promotion sensitivity；任一低於 95% 必須明示
  選擇偏誤未排除，缺口只能由新增前瞻資料補強，不可改參數救援。
- v10 Paper 必須累積至少 252 個新增交易日與 6 次已完成的三態切換成交；扣
  成本後報酬為正、勝同起點 SPY、最大回撤不深於 SPY，且前瞻主動報酬 NW t
  至少 1.96、PSR 至少 95%，才可進入實金參考評估。
- 任一 Paper-entry gate 失敗：封存負結果、不建立 v10 Paper。
- 通過 Paper-entry 但未通過歷史統計：只允許隔離 Paper；網站不可顯示為今天
  可照單的配置。
