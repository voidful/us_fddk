# 內部研究 log

這個目錄和 `artifacts/`、`docs/SHORT_TERM_*` 一起保存研究收據、失敗候選及未升格結果。它們用來追蹤可重現性、成本、基準、資料完整性和 Paper 門檻，不是公開交易頁面的資料來源。

公開頁面只有一條資料邊界：`site/data/public-decision.json`。它由
`scripts/build_public_decision_data.py` 從完整研究資料建立白名單；只有同時滿足所有事前、成本、風險、前瞻和帳戶完整性條件的策略，才會被複製到白名單。其餘候選即使回報為正、Paper 暫時領先或只差一項門檻，也只留下內部狀態。

## 公開規則

- 白名單有策略時，只展示已驗證策略的執行規則、配置和必要比較指標。
- 白名單為空時，首頁固定顯示「今天不下單」，不展示失敗候選、研究中結果、歷史最後權重、Paper 配置或實金金額試算。
- Pages artifact 不會複製 `site/data/` 研究資料；只包含渲染後的 success-only HTML 和必要前端資產。

## log 分層

- `artifacts/public_decision_build_log.json`：每次公開白名單建置的升格／未升格摘要。
- `artifacts/short_term_*`：短線研究、基準比較、壓力測試和資料收據。
- `docs/SHORT_TERM_*`：各輪固定協議與研究報告。
- `docs/research-log/`：需要保留、但不應混入公開決策契約的補充紀錄。

失敗結果不會由 log 反向產生交易建議；只有新的完整驗證收據才能讓白名單出現策略。
