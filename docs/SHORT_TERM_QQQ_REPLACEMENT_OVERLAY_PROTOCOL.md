# 美股短線第 30 輪：QQQ 全投資替換式疊加事前協議

狀態：**只凍結設計；本文件提交及推送前不得計算任何第 30 輪回報、風險或門檻結果。**

## 研究問題

第 29 輪把 US$1,000 分成五個無槓桿槽位，只在事件期間持有股票，其餘時間留作零回報
現金。Top-7 五槽的平均股票持倉只有 72.0%，所以即使事件窗口相對 QQQ 有正差，完整
資金路徑仍可能因閒置資金而落後 QQQ 買入並持有。

本輪只回答一個新的、可否證的資金配置問題：五個各 20% 的槽位在沒有事件時持有 QQQ；
當輪到該槽的原第 29 輪事件時，在 D+1 開市沽出該槽 QQQ、買入凍結 Top-7，於第 20 個
session 收市沽出股票並買回 QQQ。這個 **QQQ replacement overlay** 在零槓桿、完整收取
四個換倉交易腿成本後，能否勝過 QQQ 買入並持有及相同換倉時鐘的公平選股基準。

這仍使用同一批已見、以 2026 現時代號倒推的 905 個 survivor 事件。它只可測試「把現金
拖累改為 QQQ 是否修復經濟結果」，不是正式 point-in-time 回測、未見驗證、最新買入名單、
Paper 或實金策略。

## 禁止事項

結果後不得：

1. 改 Top-7、20／60 日訊號、D+1、20-session 持有期、事件次序或五槽 assignment；
2. 改成只在強市持有 QQQ、只替換正面事件、提高槽位權重、借入 QQQ 或加槓桿；
3. 因結果改用 SPY、TQQQ、現金、短債或另一隻 ETF 作非事件底倉；
4. 忽略 QQQ 沽出／買回兩腿，或把每事件兩個資產 round trip 只收作一個；
5. 依結果改成本、半期、危機年、最佳年份、NW lag、bootstrap block／seed 或 family；
6. 把調整價、分數股或現時 ticker 冒充真實成交、永久 ID、歷史成分、退市或稅後經濟；
7. 因任一本輪門檻通過而啟動 Paper、建立持倉或落實實金。

任何輸入、父收據、事件、槽位、換倉腿、日線資產、成本或 baseline 不能重建即 fail
closed；不得刪除事件、補值或換用另一份行情。

## 固定來源與收據

| 輸入 | 固定值 |
|---|---|
| 第 29 輪結果 commit | `ba7515529959d45dfe6f576ac96d833d7a1e08e1` |
| 第 29 輪機器收據 | `artifacts/short_term_calendar_capital_accounting_validation.json` |
| 第 29 輪收據 SHA-256 | `a35a3fa21b491250a3cce23e627a26e67a0d3219f796af4e2ec739d9f07e8e36` |
| 原始事件收據 SHA-256 | `fa2463cc8273a316e4a98428767b695eb85c74e9ac75c47b5ca34592102979e8` |
| 行情 archive SHA-256 | `d480fb82e712f06aabe0a98461e222344656b87022b8bda2cd7ccaa4c29ae88b` |
| 行情 panel fingerprint | `6a7ca6b83b1570007424daa46b0ff4e8fb4a655d39298a0f4f6d74c3b7ea3a66` |
| 現時觀察名單 SHA-256 | `b6002e4e151bd298884f8cdd6272b5cbfde8aedca47cb58b92830d4d92028014` |
| 事件 | 905 個；訊號 2006-08-04 至 2026-07-02；最後退出 2026-07-31 |
| 槽位 assignment SHA-256 | `3be9948565e7c58e951a50110e6063185c8c93a12b1cf97c2014b981b25c5547` |

台股研究紀律參考固定為：

- `tst_wocker@3372aa088328700feafeeb07c72ab832ea2d3ecb`：橫斷面排名及組合層風險；
- `tw-block-warrant@37463c54796ba36f4aac262519ea7fc2ef797de6`：D 日訊號、D+1 成交及多窗分離；
- `tst_wocker_filter_lab@06c87b7a1735877c9ccbab3a339c1742814a5058`：同次 baseline、凍結快照、
  負結果及資金再投資稽核。

只轉移研究紀律，不搬用台股回報、ATR、權證流向、止賺止蝕、加碼或市場微結構參數。

## 固定訊號與五槽

- 完全重播第 29 輪 905 個事件：訊號日調整收市已知的 20 日動量、60 日趨勢、價格高於
  US$5、20 日中位美元成交額至少 US$20m，按動量降序及 ticker 升序 tie-break 選 Top-7。
- 訊號後一個 session 調整開市進場，持有 20 個 session，在第 20 個 session 調整收市
  退出；不得以訊號日收市成交。
- `slot = event_index mod 5`，五槽各 181 個事件、初始權重各 20%，禁止跨槽轉資本。
- `eligible` 為該事件原合資格股票；`complete` 固定為同一 25 隻 2026 現時代號。
- US$1,000 與分數股只作比例研究；不代表券商碎股、稅項或市場容量可行。

## 固定全投資換倉會計

共同日曆為 2006-08-04 至 2026-07-31；第一個可成交時點為 2006-08-07 開市：

1. 五槽各 US$200；第一事件若在該槽首次可成交時點開始，直接買入事件資產，否則買入
   QQQ。禁止先買再即時沽同一資產以製造無意義成本。
2. 非事件期間，每槽全數持有 QQQ，按調整收市及下一次 entry open 標記；事件期間持有該
   路徑的等權股票籃子，按 entry open 至每日調整 close 標記。
3. 在事件 entry open，先把 QQQ 從上一收市標記至 entry open，再沽 QQQ及買股票；在
   event exit close，先標記股票至 exit close，再沽股票及買回 QQQ。
4. 主要資產 round trip 成本固定 20 bps，即每個買或賣腿 10 bps。正常事件含 QQQ sell、
   basket buy、basket sell、QQQ buy 四腿，名義總成本 40 bps；首個直接買入事件及最後
   全部平倉只收實際發生的腿。
5. 成本按每次交易前該槽資產比例精確扣減；不把兩資產來回錯算成一個 round trip。另以
   資產 round trip 50／100 bps，即每腿 25／50 bps，同步重建全部 overlay 路徑。
6. 2026-07-31 收市後所有槽平倉並收最後賣出腿；買入並持有基準亦只在首次買入及最後
   賣出收相同每腿成本。
7. 每日總資產等於五槽資產；2006-08-07 後 long exposure 必須為 100%，cash 為零，
   leverage 不高於 1。任何 identity、重疊或換倉腿誤差高於 `1e-12` 即停止。

## 八條固定路徑

1. `top7_qqq_overlay`：非事件 QQQ，事件期間 Top-7；唯一候選。
2. `eligible_qqq_overlay`：相同槽位、換倉腿及成本，事件期間持有 eligible 等權。
3. `complete_qqq_overlay`：相同槽位、換倉腿及成本，事件期間持有完整現時 25 股等權。
4. `qqq_switch_placebo`：在相同 905 個事件時點沽出並買回 QQQ，完整收取四腿成本；用以
   分開選股差額與高換手成本，不可取代較強的 QQQ buy-and-hold。
5. `top7_cash_five_slot`：第 29 輪 Top-7 五槽現金路徑，原樣重播 20 bps；量化現金拖累。
6. `qqq_buy_hold`：首次 open 買入、最後 close 賣出，只收一次 QQQ round trip。
7. `spy_buy_hold`：同一起訖及成本的 SPY 基準。
8. `shy_buy_hold`：同一起訖及成本的 SHY 基準，亦作 excess return 現金代理。

候選對其餘七條路徑形成固定七假說 family。`qqq_switch_placebo` 必須精確等於「QQQ 價格
路徑加固定事件換手成本」，不得因買賣同一 ticker 而省略成本。

## 固定指標與統計

每條路徑呈列：總回報、CAGR、年率化波幅、SHY 日回報超額 Sharpe／Sortino、最大跌幅、
Calmar、US$1,000 期末值、年率化換手、成本拖累、平均 QQQ／事件股票曝險及最小現金。

七個每日差額使用同一 5,028-session 日曆並呈列：

- 平均／中位日差、年率化算術差、正值比例；
- Newey–West lag 20 兩尾 t 與普通常態 p；
- 七假說 Holm p；
- 63-session circular moving-block、20,000 共同路徑、seed `30202608` single-step max-t p；
- 固定前半至 2016-07-29、後半由 2016-08-01；
- 每個曆年 compounded difference。

正式全專案搜尋次數由 6,214 加本輪七假說至 **6,221**；候選對 QQQ buy-and-hold 的普通
p 另呈列 6,221 次 Bonferroni，不得重設搜尋次數。

## 固定壓力

- **最佳三年移除**：按候選相對 QQQ buy-and-hold 的曆年 compounded difference 排名，
  移除最高三年，在其餘共同 session 重算 NW lag 20。
- **危機期**：固定 2008、2020、2022，呈列八路徑回報及最大跌幅，並比較候選與 QQQ。
- **成本**：資產 round trip 50／100 bps 同步重建四條 overlay 及三條 buy-and-hold；
  top7 cash 路徑按第 29 輪相同 round-trip 定義重建。不得只提高候選成本。
- **最差事件差額**：按事前固定的候選相對 QQQ event gross difference，移除最有利 46 個
  事件後重建 candidate 與三個 overlay baseline；不改槽位或以其他 baseline 排序。
- **身份**：頁首及決策須明示 survivor cohort、正式就緒 1/18、point-in-time 1/20、
  合資格 provider package 0、正式策略 run 0、Paper 全現金。

## 二十項事前反證門檻

1. protocol、父收據、行情、panel、watchlist、事件及三個參考 commit 精確；
2. 第 29 輪 905 個事件、日期、四路事件回報及 assignment 逐列重播；
3. 五槽各 181 事件、同槽不重疊、最大 concurrency 五個；
4. 八路同一日曆，overlay 每日資產、換倉腿及成本 identity 誤差不高於 `1e-12`；
5. 首次可交易日後候選 long exposure 為 100%、cash 為零、leverage 不高於 1；
6. `qqq_switch_placebo` 價格路徑及事件換手成本逐日重建；
7. 候選 CAGR 高於 QQQ buy-and-hold；
8. 候選 US$1,000 期末值高於 QQQ buy-and-hold；
9. 候選 SHY-excess Sharpe 高於 QQQ buy-and-hold；
10. 候選最大跌幅不得比 QQQ 深超過 5 個百分點；
11. 候選 CAGR 高於 eligible overlay；
12. 候選 CAGR 高於 complete overlay；
13. 候選對 eligible overlay 平均日差為正且 NW t 不低於 1.96；
14. 候選對 complete overlay 平均日差為正且 NW t 不低於 1.96；
15. 候選對 QQQ buy-and-hold 平均日差為正且 NW t 不低於 1.96；
16. 候選對 QQQ 的 Holm 及共同 max-t p 均不高於 0.05；
17. 候選對 QQQ、eligible、complete 的前後兩半平均日差全部為正；
18. 移除相對 QQQ 最佳三年後，平均日差仍正且 NW t 不低於 1.96；
19. 2008／2020／2022 每段候選回報均不低於 QQQ，且最大跌幅不比 QQQ 深超過 5pp；
20. 6,221 次 Bonferroni p 不高於 0.05；50／100 bps 及移除最有利 46 事件後，候選 CAGR
    仍同時高於 QQQ buy-and-hold、eligible overlay 及 complete overlay。

任何一項未通過即 `not_rejected_by_round30=false`。即使 20/20，本輪仍因同一已見 survivor
樣本而固定 `can_promote_from_this_round=false`、`new_strategy_created=false`；不得建立
Paper。只有合格 point-in-time／退市／公司行動數據 20/20、按既有正式預先登記運行一次，
再完成至少 252 個新增 session 及 12 次換倉，才可另行評估由全現金啟動 Paper。

## Fail-closed 控制與攻擊

實作須保存至少 27 道控制及 27 項單欄變異攻擊，覆蓋：protocol hash／commit、第 29 輪
及原始事件收據、snapshot、panel、watchlist、三個台股參考 commit、事件／cohort／訊號、
五槽 assignment、QQQ 底倉、四腿成本、八路徑、SHY excess、100% 曝險、無槓桿、日線
identity、七假說 family、NW lag、bootstrap、固定半期、危機、尾部、6,221 trials、現時
身份、Paper 及實金越權。每項只改一欄並命中穩定錯誤碼。

## 固定輸出與發佈邊界

若首次計算成功，輸出：

- `artifacts/short_term_qqq_replacement_overlay_validation.json`；
- `site/data/short-term-qqq-replacement-overlay.json`；
- `docs/SHORT_TERM_QQQ_REPLACEMENT_OVERLAY_RESEARCH_REPORT.md`。

報告及網站使用香港金融用詞，完整呈列八條路徑、七假說、換倉腿、成本、危機、半期、
最佳年份、46-event 壓力、20 道門檻、控制、攻擊及限制。不得只展示最好數字。短線 Paper
維持全現金、持倉 0；US$1,000 只作讀者歷史尺度示例，實金動作固定 US$0。
