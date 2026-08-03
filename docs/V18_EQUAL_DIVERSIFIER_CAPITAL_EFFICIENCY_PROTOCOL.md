# v18 凍結協議：等權股／債／金資本效率

凍結狀態：本檔完成後先記錄 SHA-256 與檔案時間；在此之前不得下載 EFO/EET 日線資料、不得計算任何海外組合結果、不得修改成功門檻。

## 研究問題

一個不擇時、每月固定再平衡的 50% 實際每日 2 倍股票 ETF／25% IEF／25% GLD 組合，是否能在美國以外的已開發市場與新興市場，同時提高相對核心 ETF 的長期報酬、Sharpe、Calmar，且不加深最大回撤？

## 已鎖定規則

- 已開發市場：50% EFO、25% IEF、25% GLD；核心 ETF 為 EFA。
- 新興市場：50% EET、25% IEF、25% GLD；核心 ETF 為 EEM。
- 每個已完成月末產生固定目標；下一交易日調整後開盤執行。
- 每次換手主要成本 10 bps；壓力成本 50 bps。
- 不使用趨勢、波動、估值、停損、槓桿切換或資料後調參。
- 實體權重合計 100%；組合帳戶不借款、不放空。每日槓桿由 ETF 產品內部提供。
- 約 100% 股票、25% 中期美債、25% 黃金，總名目曝險約 150%。
- 全域搜尋試驗數固定為 6,121。

若海外關卡全過，獲准建立的美股 Paper 候選固定為 50% SSO、25% IEF、25% GLD。歷史配置不得回填成真實 Paper 績效。

## 首次日線下載契約

- 來源：Yahoo Finance 經 `yfinance`，調整後 OHLCV。
- 唯一代號集合：`EFA,EFO,EEM,EET,GLD,IEF,SHY`。
- 請求起日：2008-06-02。
- 唯一資料截止日：2026-07-31；下載 API 的 exclusive end 為 2026-08-01。
- 必須保存不可變 ZIP、manifest、panel SHA-256、archive SHA-256、下載時間、協議 SHA-256 與協議 mtime。
- 面板日期必須嚴格遞增、唯一，第一列 2008-06-02、最後一列 2026-07-31、至少 4,500 列。
- 代號集合必須完全相等；不可在看見結果後新增、移除或替換 ETF。
- 所有非空價量必須通過既有 OHLCV 契約；正式期每個月末訊號與下一個執行日，策略及比較組合需要的標的都必須有完整 OHLCV。
- 協議檔 mtime 與凍結收據時間必須早於第一次 EFO/EET 日線快照 mtime。

EFO 與 EET 官方資料顯示成立日皆為 2009-06-02。正式期延後至 2010-07-30，以要求每個核心、2 倍股票、IEF、GLD、SHY 都至少有 252 個正式期前有效交易日。

## 固定驗證區間

兩個海外資料集都使用：

- 正式完整期：2010-07-30 至 2026-07-31，共約 16 年。
- 第一固定半期：2010-07-30 至 2018-07-30。
- 第二固定半期：2018-07-31 至 2026-07-31。
- 滾動期：1,260 個交易日，僅在已完成月末評估。

這不是 20 年海外驗證，因為 EFO/EET 直到 2009 年才成立。20 年證據只存在於已見的美國大型股設計樣本，不得混稱海外 20 年。

## 比較組合

每個海外資料集固定計算：

1. 核心 ETF 買進持有：EFA 或 EEM。
2. 同資產不槓桿：2/3 核心 ETF、1/6 IEF、1/6 GLD，每月再平衡。
3. 純債分散診斷：50% 實際 2 倍股票 ETF、50% IEF。
4. 純金分散診斷：50% 實際 2 倍股票 ETF、50% GLD。
5. 短債槓桿控制：50% 實際 2 倍股票 ETF、50% SHY。
6. 實際 2 倍股票 ETF 單獨持有，只作風險揭露。

第 3 至第 6 項只作機制診斷，不得覆蓋核心或同資產不槓桿關卡的失敗。

## Paper Entry 經濟關卡

每個海外資料集都必須通過以下九項；兩個資料集合計 18/18 才通過經濟關卡：

1. 10 bps CAGR 高於核心至少 25 bps。
2. 10 bps Sharpe 高於核心。
3. 10 bps 最大回撤不差於核心。
4. 10 bps Calmar 高於核心。
5. 50 bps CAGR 高於核心至少 10 bps。
6. 兩個固定半期的 CAGR 都高於核心至少 10 bps。
7. 滾動五年 CAGR 高於核心 10 bps 的勝率至少 60%，且 CAGR 差中位數大於零。
8. 10 bps CAGR 高於同資產不槓桿組合至少 10 bps。
9. 50 bps CAGR 高於同資產不槓桿組合至少 10 bps。

Paper Entry 還必須通過所有資料、順序、完整月末、下一日執行、權重與名目曝險完整性關卡。任何一項失敗都不得建立 v18 Paper。

## 統計確認關卡

對每個海外資料集，分別以核心 ETF 與同資產不槓桿組合作為基準，計算：

- Newey-West active-return t 值至少 1.96。
- Probabilistic Sharpe Ratio 至少 95%。
- 以 6,121 次全域試驗計算的 Deflated Sharpe Ratio 至少 95%。

共 12 項。統計關卡不降低 Paper Entry 門檻；它決定能否使用「歷史統計確認」字樣。即使全過，也不能直接成為參考交易。

## 前瞻與上線邊界

- 經濟與資料關卡 100% 通過時，只能建立隔離的 v18 Paper 狀態。
- Paper 必須從建立後的新交易日開始；不得把歷史交易回填為前瞻證據。
- 至少累積 252 個新交易日與 6 次已完成月末再平衡。
- 10 bps 後報酬必須為正，且同起點擊敗 SPY、未槓桿同資產配置與短債槓桿控制。
- Paper 最大回撤不得差於上述三個比較組合；active Newey-West t 值至少 1.96，PSR 至少 95%。
- 歷史統計與完整前瞻關卡全過前，`trade_ready=false`、隱藏配置、不得稱穩健、不得稱能跑贏 ETF。

## 預先揭露的偏誤與風險

- v18 規則由六個已見美國市場與七個候選中選出；這些結果只是設計資料。
- 凍結前已查看 EFO/EET 官方頁面的每日 2 倍目標、成立日與公開摘要績效；尚未下載或計算每日 OHLCV 組合路徑。因此海外資料是半獨立、不是完全盲測。
- EFO/EET 追求每日 2 倍，不保證長期 2 倍；波動耗損、費用、衍生品與追蹤誤差已反映在實際 ETF 價格中。
- IEF 有利率風險，GLD 無收益且可能長期落後，股票、債券與黃金仍可能同跌。
- 名目曝險約 150%，虧損可能快速且巨大；Paper 通過也不是個人化投資建議。

## 事前研究來源

- ProShares EFO：<https://www.proshares.com/our-etfs/leveraged-and-inverse/efo>
- ProShares EET：<https://www.proshares.com/our-etfs/leveraged-and-inverse/eet>
- WisdomTree 90/60 資本效率說明：<https://www.wisdomtree.com/us/insights/blog/boosting-portfolio-efficiency-via-our-90-60-approach>
- WisdomTree GDE 股金資本效率產品：<https://www.wisdomtree.com/us/products/capital-efficient/gde>
- Moreira 與 Muir，Volatility Managed Portfolios：<https://www.nber.org/papers/w22208>
