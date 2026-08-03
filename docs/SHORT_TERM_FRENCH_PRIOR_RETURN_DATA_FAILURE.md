# French prior-return 第六輪：首次下載數據契約失敗

稽核日期：2026-08-03

正式狀態：**6/8 數據檢查；策略計算未開始；Paper 關閉；實金動作 US$0**

## 一眼結論

本輪原定用 Kenneth French 的 short-term prior (1–1) 十分位，直接檢查台股 20 日贏家
延續概念在美股全 CRSP 學術母體是否反而受到短期反轉支配。主要候選、六路敏感度、
四個 baseline、成本、分段、38 道學術門檻及四道逐股 Paper 閘已在首次下載前提交凍結。

五個官方 ZIP 均只下載一次，檔案、SHA-256、CSV member、equal-weighted 表及三個因素
header 均通過；但兩個 prior-return ZIP 的 value-weighted 月表標記與凍結映射不一致：

| ZIP | 凍結預期 | 首次原檔實際值 |
|---|---|---|
| short-term prior 1–1 | `Average Value Weighted Returns -- Monthly` | `Aerage Value Weighted Returns -- Monthly` |
| long-term prior 12–2 | `Average Value Weighted Returns -- Monthly` | `Value Weight Returns -- Monthly` |

第一個是官方原檔的 `Average` 拼字缺字；第二個使用 `Value Weight` 而非
`Average Value Weighted`。這些可能只是標題差異，但凍結契約明訂欄名或表段不符就在
策略計算前停止。因此沒有用模糊搜尋、寬鬆 parser 或改映射跨過失敗，也沒有計算任何
CAGR、Sharpe、PBO、事件回報或 US$1,000 終值。

## 可重現稽核

| 檢查 | 結果 |
|---|---:|
| 協議及映射雜湊 | 通過 |
| 五個官方 ZIP 雜湊 | 通過 |
| 五個 CSV member | 通過 |
| short-term value-weighted 月表標記 | **失敗** |
| long-term value-weighted 月表標記 | **失敗** |
| 兩個 equal-weighted 月表標記 | 通過 |
| Fama/French 因素 header | 通過 |
| Mom／ST_Rev header | 通過 |

機器收據固定記錄 `numeric_return_rows_parsed=false`、
`strategy_calculation_started=false` 及 `redownload_permitted=false`。稽核工具預期以退出碼
2 表示「失敗已正確關閉」，而不是程式故障。

## 五份封存原檔

| 角色 | SHA-256 |
|---|---|
| short-term prior 1–1 | `20b186f6f7c322098d6d2a6be6183d5944b12c7f6c9e888664ce44ba81064ace` |
| long-term prior 12–2 | `ca0af27fa0829ed6ac38b7b13b20cc11fd12274a8d06dac226998dfc1d0f07f6` |
| Fama/French factors | `80b88699a18ac408e2456d25b1004e340f3f7f8d41d5b476a0285bc53c6f0436` |
| Momentum factor | `37baf72ae4eace9715e8746413d0122334c63aa4083fd1c3cf2060fa04e4bd28` |
| Short-Term Reversal factor | `e0fc1859c8b7e56ac17d06239de231fb33d28c8537b3f59fa378d4d704110e21` |

Fama/French factors 的首次取得內容與專案先前封存檔逐 byte 相同，所以只保留既有的一份
正式快照，不複製相同檔案冒充新證據。

## 與三個台股參考專案的關係

- `tst_wocker` 最新底層仍是 20 日橫斷面動量加 60 日趨勢，但其 headline 不可直接搬到
  美國市場。
- `tw-block-warrant` 的 D 日訊號、D+1 時鐘、固定持有期及成本原則已抽取；美股沒有
  同質免費鉅額／權證歷史，沒有偽造 proxy。
- `tst_wocker_filter_lab` 最新稽核顯示同池等權的 Sharpe 可以勝過四個複雜策略，且
  Top-7 集中可能淹沒排名優勢；因此本輪已事前把同母體十分位等權、Lo PRIOR、標準
  12–2 贏家及市場列為硬 baseline。

由於數據契約在計算前失敗，以上假說仍然未被這一輪的回報數字支持或否定。

## 決策

這一輪只證明「凍結映射與官方 CSV 標題不相容」，不證明短窗動量有效或無效。不得：

- 修改 marker 後用同一批已見原檔宣稱 first-seen 驗證；
- 把 Lo PRIOR、Top-2、Top-3、傾斜池或 12–2 改成事後冠軍；
- 重下載同一發布版尋找不同內容；
- 產生股票名單、Paper 或實金配置。

若繼續研究，只可另立一條明示「映射在看過 schema 後制定」的新工程驗證，且不能算
獨立 first-seen 經濟證據；更高價值的路徑仍是取得已授權的 CRSP／WRDS、Norgate 或
同級逐股 point-in-time／退市資料，按既有個股 v1 由全現金重跑。現時短線配置、Paper
持倉及實金動作全部維持 US$0。
