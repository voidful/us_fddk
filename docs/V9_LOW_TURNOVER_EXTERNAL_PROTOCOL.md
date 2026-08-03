# v9 低換手成長傾斜與全新外部樣本：第一次計算前凍結協議

凍結時間：2026-08-01T17:42:27Z

狀態：v9 是看到 v8 負面結果後提出的結構性修正。v8 的月月回到固定比例造成
成本壓力失敗，舊代理期的 50% 成長槽位也讓回撤超出凍結上限；v9 不回改 v8，
而是事前固定較小的 40% 成長槽位，且只在風險狀態改變時交易。

主 ETF 與舊 Nasdaq-100 代理資料都已看過，因此不是 data-independent
preregistration，必須計入全專案第 6,106 次研究搜尋。第三段 Nasdaq Composite
外部樣本在本文件凍結時尚未下載、檢視或計算。第一次 v9 權重或績效出現後，
不得更換比例、回顧窗、均線、交易觸發、期間、成本、基準或門檻。

## 研究依據與適用邊界

- Jegadeesh and Titman (1993) 記錄股票橫斷面的中期動量，也記錄其後部分反轉：
  https://onlinelibrary.wiley.com/doi/10.1111/j.1540-6261.1993.tb04702.x
- Moskowitz and Grinblatt (1999) 記錄產業動量：
  https://onlinelibrary.wiley.com/doi/10.1111/0022-1082.00146
- Hurst, Ooi and Pedersen 的長期多市場研究支持趨勢機制可能跨資產與年代出現：
  https://www.aqr.com/insights/research/journal-article/a-century-of-evidence-on-trend-following-investing
- Nasdaq 官方資料說明 Nasdaq Composite 於 1971-02-05 啟動，涵蓋 Nasdaq 上市
  公司並採市值加權；官方指數版本文件區分價格報酬 `COMP` 與總報酬 `XCMP`：
  https://www.nasdaq.com/articles/nasdaq-composite-indextm%3A-50th-anniversary-brings-new-records-and-further-optimism
  https://www.nasdaq.com/solutions/global-indexes/nasdaq-composite
  https://indexes.nasdaq.com/docs/Index_Versions_COMP.pdf

這些來源只支持一般研究假說與指數身分，不直接證明本規則有 alpha。外部樣本的
`^IXIC` 是比 Nasdaq-100 更廣的 Nasdaq Composite 價格指數；它只作較嚴格的
跨年代機制檢驗，不能冒充 QQQ、Nasdaq-100 或含股息 ETF 的可交易報酬。

## 唯一可交易規則

每個完整月末 `t`，用當日可得的調整後收盤資料：

1. 核心標的是 `SPY`，成長標的是 `QQQ`；代理樣本只作下列唯一對應。
2. 分別計算核心與成長從 `t-252` 到 `t-21` 的報酬：
   `close(t-21) / close(t-252) - 1`。
3. 成長風險開啟，若且唯若成長報酬嚴格高於核心，且成長在 `t` 的收盤價嚴格
   高於截至 `t` 的 200 個交易日簡單移動平均。相等、缺值或暖機不足一律關閉。
4. 風險開啟的目標是 60% 核心、40% 成長；風險關閉的目標是 100% 核心。
5. 正式期開始前最後一個完整月末產生初始訊號，下一個共同交易日成交。此後只
   在風險開啟布林值改變時產生新訊號，並於下一個共同交易日成交。
6. 兩次狀態切換之間讓持倉自然漂移，不為回到 60/40 而月月再平衡。每月仍計算
   狀態，但狀態不變就不交易。
7. 永遠 100% 股票曝險；不使用 SHY、現金擇時、槓桿、放空、停損、波動縮放、
   確認月數、月中切換或任何 v9 結果出現後的參數修正。
8. 基準成交成本 10 bps，壓力成本 50 bps，均乘以單邊換手；市場基準也用相同
   引擎與成本定義。

### 公平基準與機會成本

- 每段的 hard benchmark 都是 100% 核心市場：主期 `SPY`，兩段代理期 `^GSPC`。
- 固定 60% 核心／40% 成長與 100% 成長只作機會成本背景，不替代 hard gate，
  也不要求 v9 勝過成長指數才可進入 Paper。
- 網站只能把 v9 稱為低換手成長傾斜研究；除非所有歷史與前瞻門檻通過，不得
  稱為已證實 alpha、穩健實金策略或今天可照單的配置。

## 凍結資料、翻譯與期間

### A. 可交易 ETF 主期（已看過）

- 快照：`artifacts/snapshot_20260731_6a7ca6b8.zip`
- panel SHA-256：
  `6a7ca6b83b1570007424daa46b0ff4e8fb4a655d39298a0f4f6d74c3b7ea3a66`
- archive SHA-256：
  `d480fb82e712f06aabe0a98461e222344656b87022b8bda2cd7ccaa4c29ae88b`
- 唯一對應：核心 `SPY`、成長 `QQQ`。
- 正式期：2006-07-31–2026-07-31。
- 固定兩半：2006-07-31–2016-07-29、2016-08-01–2026-07-31。

### B. 不重疊舊 Nasdaq-100 代理期（已看過）

- Nasdaq-100：`artifacts/snapshot_ndx_proxy_19851001_20060728_4814654a.zip`，
  panel `4814654a4abb4ea5ef0eb52763e233e13bc7088d51ca506eb94c7e335f5f4faa`，
  archive `ede88d5906411182e454d2e43442e7b5af61c392eab75e4235d5f22d3112f78d`。
- S&P 500：`artifacts/cross_market_gspc_19870101_20060728_fbe6b740.zip`，
  panel `fbe6b7403574d3296f371ed77c9831cca605b45a5dc5d2a0becfc02ec22f9e2f`，
  archive `2406c622d7b4c85666512ef84b3853b8729c5fe6b4e50256270f60a6273ecacd`。
- 只取共同交易日；唯一對應：核心 `^GSPC`、成長 `^NDX`。不得串接 ETF 報酬。
- 正式期：1989-01-03–2006-07-28。
- 固定兩半：1989-01-03–1997-09-30、1997-10-01–2006-07-28。

### C. 全新 Nasdaq Composite 外部期（凍結時尚未下載）

- 指定供應商與代號：Yahoo Finance via yfinance，成長 `^IXIC`、核心 `^GSPC`。
- 指定下載範圍：1971-02-05–1988-12-30；正式期前資料只作 252／200 日暖機。
- 只取兩個指數都有 OHLCV 的共同交易日；不得補值、串接其他代號、替換供應商
  或在下載失敗後換代理。快照檔名與 panel／archive 雜湊只能在下載後寫入獨立
  data receipt addendum，不得回寫本凍結文件。
- 正式期：1973-01-03–1988-12-30。
- 固定兩半：1973-01-03–1980-12-31、1981-01-02–1988-12-30。
- 唯一對應：核心 `^GSPC`、成長 `^IXIC`。

B、C 都是價格指數、不含股息，僅檢驗規則機制，不能宣稱 ETF 可交易績效。
三段皆年化 252；Newey–West lag 9；五年滾動 1,260 個共同 sessions，於每個
完整月末取樣。日期邊界若非共同交易日，只能在凍結區間內取實際存在日期；不得
移動區間以改善結果。

## 經濟、統計與搜尋偏誤定義

- 經濟勝出必須 CAGR 至少高 hard benchmark 10 bps／年；浮點數微差不算。
- 每一段各自計算每日主動報酬，使用固定 lag 9 Newey–West 平均檢定。
- 每一段各自以 PSR 檢驗母體主動 Sharpe 高於 0 的機率是否至少 95%。
- 另揭露全專案 6,106 次搜尋懲罰的 DSR。三段任一 DSR 未達 95%，都必須明示
  選擇偏誤未排除；DSR 是 promotion sensitivity，不得刪除或調低試驗數。
- Paper 只取得新證據，不會把三段既有回測轉成獨立樣本。

## 29 道凍結歷史門檻

以下 1–7 分別在 A、B、C 三段各檢查一次，共 21 道經濟／時間穩定門檻：

1. 基準成本下 CAGR 勝 hard benchmark 至少 10 bps／年。
2. Sharpe 高於 hard benchmark。
3. 最大回撤不得比 hard benchmark 深超過 5 個百分點。
4. Calmar 高於 hard benchmark。
5. 50 bps 壓力成本下 CAGR 仍勝 hard benchmark 至少 10 bps／年。
6. 固定前後兩半 CAGR 都各勝 hard benchmark 至少 10 bps／年。
7. 五年滾動 CAGR 勝 10 bps 的有效勝率至少 60%，且 CAGR 差中位數為正；沒有
   有效視窗即失敗。

跨資料完整性門檻：

22. 三段至少 95% 正式交易日權重總和為 1，所有權重非負且不得槓桿。
23. 三段快照雜湊、共同日期、暖機、唯一翻譯、無缺值與資料契約全部通過。

以下統計門檻分別在 A、B、C 三段各檢查，共 6 道：

24–26. 每段主動報酬 Newey–West t 至少 1.96。
27–29. 每段主動報酬 PSR 至少 95%。

## Paper 與上線決策

- `Paper-entry gates` 固定為 1–23。23/23 才可從主資料最後日之後建立全新、
  隔離的 v9 Paper；不得回填歷史成交，也不得沿用 v2 或 v3 Paper 成績。
- 29/29 才可標記 `historically_confirmed=true`，但仍不代表可實金參考。
- 三段 6,106 次 DSR 都列為 promotion sensitivity。任一低於 95% 時，網站必須
  明示選擇偏誤未排除；缺口只能由新前瞻資料補強，不可改參數救援。
- v9 Paper 必須累積至少 252 個新增交易日與 6 次已完成的狀態切換成交；扣成本
  後報酬為正、勝同起點 SPY、最大回撤不深於 SPY，且前瞻每日主動報酬 NW t
  至少 1.96、PSR 至少 95%，才可進入實金參考評估。若第 6 次狀態切換晚於第
  252 日，就繼續等待，不以月度計算次數代替實際成交。
- 任一 Paper-entry gate 失敗：封存負結果、不建立 v9 Paper。
- 通過 Paper-entry 但未通過歷史統計：只允許隔離 Paper，網站不可顯示為今天
  可照單的配置。
