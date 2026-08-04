# 短線第 26 輪 beta 覆蓋修復協議

狀態：**父協議首次 fail closed 後、任何回報統計成功輸出前凍結**

## 父協議停止證據

已提交的父協議 commit `6616064` 固定要求 905 個事件的 selected、eligible 及完整 25 股
cohort 全部具有 60／252 個訊號前日回報。首次執行在第一個 beta cell 即以
`common_risk_beta_window_mismatch` 停止，沒有產生 family、gate、報告或機器收據。

只作覆蓋盤點後確認：

- 252 日窗口有 39 個早期事件不完整，全部只欠 MA；
- 缺口由 2006-08-04 至 2007-05-25；
- 第一個 25 股 252 日窗口全部有限的固定訊號日是 2007-06-01；
- 2007-06-01 至 2026-07-02 共 866 個既有事件；
- 60 日窗口只在最早 3 個事件欠 MA，但為免模型之間偷換樣本，不能讓 QQQ_60 使用較長
  樣本。

盤點沒有計算、列印或選擇任何 candidate、baseline、beta、殘差或未來回報統計。

## 唯一修復

1. 原始 905 個事件仍須全部重建，四條回報逐列最大誤差仍不得高於 `1e-12`；不得刪除
   或改寫原始研究歷史。
2. 十假說 family、全部 beta gap、共同 bootstrap、QQQ 上／下組及 beta-contribution
   壓力統一使用 **866 個共同事件**，固定訊號日 2007-06-01 至 2026-07-02。
3. 866 個事件必須同時滿足所有 25 股、QQQ、SPY 的 252 日簡單回報完整且有限；
   `COHORT_252` 亦只由同一 25 股構成。
4. `QQQ_60` 不可使用早期多出的 36 個可計事件；五個模型、兩個 baseline 必須逐列同日。
5. 前後半分界仍為 2016-07-29／2016-08-01；不得因樣本修復重選分界。
6. 父協議固定移除 46 個最大絕對 beta contribution 事件；修復後仍保留 **46**，不改成
   44、45 或事後較有利數目。報告須明示它由原 905 個事件的 5% 向上取整而來，對 866
   個共同事件約為 5.31%。
7. 原 14 個 gate 門檻、十假說 family、Holm、NW lag 4、52-event／20,000 路徑／seed
   26202608、factor、beta 公式、baseline、成本及決策邊界全部不變。

## 新增 fail-closed 邊界

- 新增 `common_risk_coverage_repair_mismatch`：修復協議 SHA、共同事件數 866、首末訊號日、
  39 個排除事件、唯一缺口代號 MA 或「所有模型共用 indices」任何一項漂移即停止。
- 輸出須同時呈列 `reconstructed_events=905`、`family_common_events=866`、
  `coverage_excluded_events=39` 及缺口日期／代號；不得只展示 866 而隱藏原樣本。
- 控制及單欄變異攻擊由至少 20 項增加一項 repair 控制；通過只證明修復按協議執行，
  不是獨立首次證據。

## 解讀邊界

本修復是同一 Round 26 family 的非獨立 schema repair。它不能把 Yahoo 現時 survivor
cohort 變成 point-in-time 數據，也不能把通過結果升格。正式就緒仍為 1/18、正式策略
run 0、Paper 全現金、持倉 0、實金動作 US$0。
