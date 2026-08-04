# 第 22 輪存活者偏差壓力測試：日期邊界 schema repair 附錄 v1.0

凍結日期：2026-08-04（任何污染壓力結果產生之前）

父協議：`SHORT_TERM_SURVIVORSHIP_CONTAMINATION_PROTOCOL.md`

父協議提交：`6c0c17570cebe408d841f823a819019b11211ffb`

父協議 SHA-256：`3977eae15de0a46607d7358ddb25d5988dab58d25ceb9f225ae229d986ff3ddd`

## 觸發原因

首次運行在載入階段以 `stress_event_order_mismatch` 停止。當時只完成：

1. 父協議 SHA 核對；
2. `artifacts/short_term_high_return_validation.json` 輸入 SHA 核對；
3. 固定 20 日事件路徑讀取；
4. 905 個事件數核對；
5. 手寫首末日期邊界核對。

程式在第 5 步立即 fail closed，尚未建立亂數矩陣、污染序列、壓力格、break-even、
Monte Carlo、主要格門檻或任何結果檔案。錯誤源於父協議手寫最後訊號日期，而不是
輸入 SHA、事件數、排序規則或策略結果。

## 唯一准許的 repair

- 保留輸入 SHA-256
  `fa2463cc8273a316e4a98428767b695eb85c74e9ac75c47b5ca34592102979e8` 為權威身份。
- 保留固定路徑 `horizons["20"].event_series` 及 905 個事件。
- 首、末訊號日期改由上述已綁定 SHA 的 905 列直接讀取並輸出，不再與手寫日期比較。
- 仍須拒收非遞增日期、重複日期、非有限回報及合資格股份少於 Top-7。
- 機器結果必須同時記錄父協議及本 repair 附錄的路徑、SHA 與提交。

## 明確不准修改

- 20 日主要期限；
- Top-7；
- -25%、-50%、-80%、-100% 四個退出回報；
- 0.5%、1%、2%、5%、10% 五個污染率；
- -50%／2% 主要格；
- 2,000 條 Monte Carlo 路徑及種子 `20260804`；
- 共用亂數、候選與公平基準同步調整；
- Newey–West lag 4、前後十年及五項主要格門檻；
- 正式回測 0、Paper 全現金、持倉 0、實金 US$0。

本附錄只修復輸入日期 metadata 的手寫重複來源，不准用於改良結果。合成壓力仍只可
否決，不能修復 point-in-time／退市數據或升格策略。
