# 美股短線突破／量能訊號診斷協議（Round 51）

凍結時間：`2026-08-10T12:10:01Z`

狀態：**事前凍結、current-cohort 診斷 only。** 本輪只檢驗一個由
`tst_wocker`／`tw-block-warrant`／`tst_wocker_filter_lab` 抽取的訊號機制：突破、量能確認及
市場環境是否在現時大型股 survivor cohort 內帶來短線相對差。它不是 point-in-time 個股回測、
不是 Paper Trading（模擬交易）、不是實金策略，也不會把結果送到公開決策頁。

## 1. 研究邊界與固定輸入

- 研究快照固定為 `artifacts/snapshot_20260731_6a7ca6b8.zip`；archive SHA-256
  `d480fb82e712f06aabe0a98461e222344656b87022b8bda2cd7ccaa4c29ae88b`，panel SHA-256
  `6a7ca6b83b1570007424daa46b0ff4e8fb4a655d39298a0f4f6d74c3b7ea3a66`。
- 個股 universe 固定為既有 `us_large_cap_watchlist_v1.csv`（30 檔，SHA-256
  `b6002e4e151bd298884f8cdd6272b5cbfde8aedca47cb58b92830d4d92028014`）。它是 2026-07-30
  現時名單，明確帶有 survivorship bias；不得用它宣稱歷史成分股策略。
- 快照只提供 `adjusted_ohlcv`（`raw_ohlc * adj_close / raw_close`），因此所有數字只可稱
  adjusted-price 事件診斷，不可冒充 raw execution、股息／退市／收購完整總回報。
- 主研究期固定為 `2006-08-01` 至 `2026-07-31`；訊號只在完整 XNYS 星期收市後計算，成交時鐘
  固定為下一個交易日開市，禁止同日成交及任何回填。

## 2. 唯一固定訊號

在每個完整星期最後一個 XNYS session `t`，對每一檔個股計算：

1. `close[t] > max(close[t-60:t-1])`：前 60 個交易日高位突破，不包括當日以前視資料；
2. `close[t] / close[t-20] - 1 > 0`：20 日動量為正；
3. `close[t] > SMA50[t]`：收市價高於 50 日簡單平均線；
4. `volume[t] / median(volume[t-20:t-1]) >= 1.5`：量能為過去 20 日中位數 1.5 倍；
5. `close[t] > US$5`，且過去 20 日中位成交金額 `close * volume` 至少 US$20m；
6. 市場環境固定為 `SPY close[t] > SMA200[t]` 且 `^VIX[t] < 30`。

合資格股票按 60 日動量由高至低排序，取最多 Top-5 等權；同分以字母順序決定。沒有合資格
股票的星期不產生事件。不得改 60／20／50／1.5／30／5／20m／Top-5，不得加入行業上限、
止賺、止蝕、加碼、槓桿、即市訊號或事後市場判斷。

## 3. 事件回報與比較

每個訊號星期只建立一筆事件。下一交易日開市以 adjusted open 入場，固定持有 **5、10、20**
個 XNYS sessions，分別是三個事前固定 horizon；於最後一日 adjusted close 離場。每個事件
組合扣固定來回 20 bps，不按結果改成本。

每個 horizon 同時計算：

- Top-5 等權淨回報；
- 同一事件日所有合資格股票等權淨回報；
- 25 檔完整現時 cohort 等權淨回報（只作完整度控制）；
- QQQ 與 SPY 下一開市至固定離場的淨回報。

只輸出 aggregate event rows（日期、事件數、合資格數及回報統計），不輸出個股名單、ticker、
持倉比例或交易指令。

## 4. 事前固定判讀

主要 horizon 固定為 10 日；在首次計算前固定五項診斷 gate：

1. Top-5 對合資格池平均差 `> 0`；
2. Newey–West 配對 t 值 `>= 1.96`（lag=`ceil(horizon/5)`、每年 52 個星期）；
3. 8-event moving-block bootstrap 95% 下界 `> 0`（2,000 次，seed `20260810`）；
4. 前／後固定十年平均差均 `> 0`；
5. 配對勝率 `> 50%`。

五項全過也只表示值得向合格 point-in-time 數據重測，不代表策略成功。事件重疊、現時名單、
adjusted OHLCV、缺退市資料及多重搜尋均保留在限制內；不計算 Paper、DSR、PBO 或實金配置。
任何數據不足或合約不符均 fail closed，結果狀態只能是 diagnostic success／diagnostic negative，
公開 action 固定為 `今天不下單`。

## 5. 研究帳本與輸出

本輪先綁定既有全域試驗帳本（v1.0 lower bound 6,287、chain head
`c0e754cee5603c5eb9d2d142db1af6ec21b465d3492097b02112b94a18574085`），並預留一個新 family、
三個固定 horizon path 的最少增量 `+3`。結果收取後只可把下限提高至 6,290；不得回到 6,287、
刪除結果、重選參數或以正面 headline 開 Paper。若只完成 protocol 而未運行，family 必須保持
`preregistered_unrun`。

機器輸出：

- protocol receipt：`artifacts/short_term_current_cohort_breakout_protocol_receipt.json`；
- validation log：`artifacts/short_term_current_cohort_breakout_validation.json`；
- human-readable report：`docs/SHORT_TERM_CURRENT_COHORT_BREAKOUT_DIAGNOSTIC_REPORT.md`。

所有收據必須自我 hash、重跑一致，並明確保存 `performance_present`、`paper_authorized=false`、
`real_money_action_usd=0` 及 `today_action=今天不下單`。本輪只留在研究 log，不修改網站 success-only
投影。
