# 第 25 輪相關性擁擠：小股池 matched-cash schema repair v1.0

凍結日期：2026-08-04（首次成功輸出第 25 輪相關性、貢獻及壓力結果之前）

狀態：父協議首次運行已 fail closed；本修補非獨立證據；不可升格；Paper／實金均為 0

## 原始停止紀錄

父協議 `SHORT_TERM_CORRELATION_CROWDING_PROTOCOL.md` 已先以 commit
`00faaa5ed04bccb8b0d147fb47a9ef3c706f3d44` 凍結。首次運行成功通過輸入 hash、25 隻
現時 cohort、905 日期及既有四條事件回報重建，但在刪除壓力遇到合資格股份不足 7 隻，
以 `crowding_baseline_fairness_breached` 停止。沒有寫出 JSON、網站數據、報告或任何可採用
策略結果。

父協議要求「刪除後仍至少 7 隻，否則 fail closed」，卻沒有定義某些事件只有 7–9 隻
合資格股份時，如何在不補回被刪代號、不偷換日期及不只降低候選持倉的情況下完成壓力。
這是 schema 支持不足，不是調整 20／60 日、Top-7、相關門檻或結果救援。

## 唯一修補

所有 leave-one／刪除最高一個／刪除最高三個現時代號壓力改用以下固定 matched-cash
會計；其餘規則不變：

1. 被刪代號同時由候選可選池與合資格 baseline 移除；不得補回。
2. 仍按原 20 日動量排名，最多取 7 隻。若只餘 `K < 7` 隻合資格股份，全部保留；每隻
   固定權重仍為 `1/7`，其餘 `(7-K)/7` 留作零回報現金。
3. 候選回報：`sum(accepted gross returns)/7 - 20bps * K/7`。
4. matched eligible 回報：`K/7 * mean(remaining eligible gross returns) - 20bps * K/7`。
5. 每事件兩邊股票持倉比例、現金比例、時鐘及成本完全一致。不得把較低股票持倉比例的
   絕對風險改善寫成 alpha。
6. 若移除後 `K=0`、回報非有限、candidate／baseline 股票持倉比例不同，仍以
   `crowding_baseline_fairness_breached` 停止。
7. 每條刪除壓力新增輸出平均／最低股票持倉比例、完整 7 隻事件比例及現金 slot 數。

## 完全不變項目

- 三個台股參考 commit、行情／watchlist／事件收據 hash、25 隻現時 survivor cohort。
- 905 個星期事件、20 日動量、60 日趨勢、Top-7、D+1 開市、20 日持有及來回 20 bps。
- 60 日 Pearson 相關、`corr > 0.70`、cap 2、原 Top-7 內不回補及有效注數公式。
- 事後最高一個／三個淨貢獻代號及 25 條 leave-one-symbol-out 的定義。
- 四假說 Holm、52-event／20,000 路徑共同 max-t、seed `25202608`。
- 父協議十二項反證門檻及所有數值界線；不得因修補改用較寬門檻。
- 正式 v1、6,208-trial DSR、point-in-time／退市數據門檻及 Paper 邊界。

## 新增控制及攻擊

父協議 18 道控制／18 項攻擊全部保留，另增加：

- 控制 19：本修補 SHA、matched-cash 公式、同步持倉比例及不足 7 隻時不補回全部固定。
- 攻擊 19：修補 SHA、現金處理或 matched exposure 漂移時，必須以
  `crowding_repair_protocol_mismatch` 拒收。

最終報告必須同時呈列父協議首次停止及本修補的非獨立性，不得把修補後結果稱為未見
首次驗證。歷史及合成結果不保證未來回報；本修補不構成投資建議或落盤授權。
