# v25 LIVE Paper 日更與發布操作規範

## 目的

把 v25 的歷史合格候選轉成不可回填、可稽核的前瞻觀察紀錄。這份流程只更新
Paper 與公開的教育用途狀態頁；在 252 個新增交易日、6 次完成再平衡及兩個前瞻基準全部通過
以前，不得把任何成功執行訊息解讀成實金授權。

## 每日唯一入口

美股完整收盤且資料供應商緩衝時間結束後，在專案虛擬環境中執行：

```bash
scripts/refresh_live_reference.sh
```

夏令時間通常在次日 02:00 UTC 後、冬令時間通常在次日 03:00 UTC 後才算資料應
更新。程式實際採 XNYS 交易所日曆與官方收盤時間判斷，所以週末、休市與提早收盤
不靠人工猜日期。

## 執行順序

1. 取得同一份 VUG、GLD、SPY、SHY 調整後 OHLCV，驗證最近已完成交易日、四檔
   末日價格、OHLC、成交量、歷史覆蓋率與內容雜湊。
2. 在記憶體中同時計算 v25、SPY、80% VUG／20% SHY 三帳戶；只有起點、日期、
   快照、成本、初始資金與完整交易日路徑全一致才寫入。
3. 更新 42 檔主研究面板與舊 Paper 鏈，重建網站資料。
4. 分別執行舊主鏈與 v25 的網站／帳戶交叉稽核，再執行網站 lint、production build、
   畫面資料契約測試與高風險套件稽核。
5. 只有 refresh status 顯示 `public_paper_status_deploy_allowed=true`，才可保存新的
   GitHub Pages 狀態。同日冪等重跑不建立版本；公開頁仍是研究教育用途，不是實金授權。

GitHub Actions 每天 04:30 UTC（台北 12:30）執行；週末與休市日由 XNYS 日曆判定
為沒有新 session，成功結束但不改寫網站。歷史研究結果保持凍結，日更只推進 v25
候選、SPY 與 80% VUG／20% SHY 三個同起點 Paper 帳戶。

## Fail-closed 情況

- 行情截止日不是最近已完成的 XNYS session。
- 任一 ETF 缺少末日 Open、High、Low、Close 或成交量。
- 帳戶日期倒退，或三帳戶日期、快照、成本、初始資金、成交時鐘、交易日序列、
  月末訊號／成交日期路徑不同。
- 同一資料日的經濟狀態發生修訂；必須人工檢查調整價重基準收據，不自動部署。
- 網站顯示的日期、待成交權重、持倉、權益、成交筆數或前瞻門檻與 state 不同。
- 網站三帳戶對照表的權益、報酬、回撤、現金、成本、成交／再平衡次數或完整權益
  序列，與 v25、SPY、80% VUG／20% SHY 任一權威 state 不同。
- 網站最近成交或已完成再平衡紀錄與候選 state 不同；待成交不可算成成交。
- 網站超過 `refresh_due_at_utc`；前端會自動隱藏訊號。
- 舊主鏈或 v25 任一發布收據失敗。

## 權威輸出

- `artifacts/v25_live_update_status.json`：行情與三帳戶同步更新結果。
- `artifacts/v25_forward_promotion_contract.json`：第一筆成交前凍結的實金參考升級合約。
- `artifacts/v25_forward_paper_evidence.json`：候選相對 SPY 與公平基準的即時門檻。
- `artifacts/v25_reference_readiness.json`：網站與三帳戶交叉稽核。
- `artifacts/v25_live_refresh_status.json`：本次是否可建立私人部署版本。
- `artifacts/v25_live_evidence_ledger.jsonl`：逐交易日 SHA-256 鏈；同日不同證據會拒絕
  靜默覆寫。

## 實金升級

網站只有在以下條件同時成立且資料仍新鮮時，才把 v25
`real_money_signal_display_allowed` 轉為 true：

- 三個帳戶始終同起點、同日、同快照、同成本、同交易日序列且零完整性違規。
- 至少 252 個真正新增交易日。
- 至少 6 次候選帳戶完成「初始建倉後」的月度再平衡；首次配置不計入。
- 候選扣成本累積報酬同時高於 SPY 與 80% VUG／20% SHY，年化優勢各至少
  0.10 個百分點。
- 固定前後兩半都分別勝過兩個基準至少 0.10 個百分點／年。
- 候選最大回撤同時不深於 SPY 與公平基準。
- 相對兩個基準的每日主動報酬 Newey–West t 值都至少 1.96。

完整且在第一筆模擬成交前凍結的定義見
`docs/V25_FORWARD_PROMOTION_CONTRACT.md`。

即使升級，80/20 仍是研究型參考配置，不是保證獲利，也不處理個人稅務、匯率、
券商滑價與適合度。
