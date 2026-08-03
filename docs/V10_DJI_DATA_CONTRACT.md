# v10 尚未檢視的 DJIA 核心：下載前資料契約

凍結時間：2026-08-01T18:14:44Z

本契約在首次下載 `^DJI` 前凍結，補充 `V10_HIERARCHICAL_DEFENSE_PROTOCOL.md`
的第 D 段。下載後不得因資料或績效結果放寬；任一條失敗就讓 v10 第 30 門
失敗，不得換代號、供應商、期間或改用別的核心指數。

## 請求

- 供應商：Yahoo Finance via yfinance。
- 代號只能是 `^DJI`；`auto_adjust=False`，必須取得 `Adj Close`，OHLC 全部用
  `Adj Close / Close` 同比例還原。
- 請求日期固定為 1971-02-05–1988-12-30（首尾皆含）。
- 快照 metadata 必須記錄 v10 協議 SHA-256、請求日期與 `core_sensitivity` 角色。
- 任何符合 `snapshot_v10_dji_19710205_19881230_*.zip` 的檔案一旦存在，就在
  連網前拒絕重新下載或覆寫。

## 單一 `^DJI` 快照硬檢查

1. 欄位只能是 `^DJI`；日期嚴格遞增、唯一。
2. 第一筆必須是 1971-02-05，最後一筆必須是 1988-12-30，至少 4,300 筆。
3. Open、High、Low、Close、Volume 的索引與欄位完全一致且無缺值。
4. OHLC 都是有限正數；High 不低於 Open／Close，Low 不高於 Open／Close。
5. Volume 必須是有限非負數；價格指數的 0 成交量不冒充 ETF 流動性問題。
6. 任一日 Close 絕對報酬不得超過 35%；超過即視為疑似資料錯誤並失敗。
7. provider 與還原方法 metadata 必須存在，研究協議 SHA-256 必須等於
   `ec23c0593820529e60087daf866adc66b64eda91922165a614ba225dadbc4484`。

## 與既有 `^IXIC` 的共同研究面板硬檢查

1. 成長資料只能載入既有凍結快照
   `artifacts/snapshot_v9_ixic_19710205_19881230_76bc29b6.zip`；panel 必須等於
   `76bc29b61c480e8c44032e4aeaea801e9ea97a1aebceb758bda84df8a8b7d2c9`，archive
   必須等於 `b845aecd3175584f8dc40e0db8e93ec9427e2a9f491f0824ec7264f6cda9eb22`。
2. 只允許 `^DJI` 與 `^IXIC` 日期交集，不前填、後填或插值；OHLCV 無缺值。
3. 共同日期第一筆必須是 1971-02-05，最後一筆必須是 1988-12-30，至少
   4,300 筆。
4. 1973-01-03 正式期以前，兩個指數都有效的共同暖機日必須至少 252 筆。
5. 必須涵蓋 1973-01-03、1980-12-31、1981-01-02、1988-12-30 四個凍結邊界。
6. 下載後的 data receipt 必須記錄 `^DJI` 快照路徑、panel／archive SHA-256、
   單一與共同契約結果、共同面板雜湊、協議與本契約的 SHA-256。
