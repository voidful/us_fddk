# 短線正式研究報表

`usfddk.formal_report` 是正式回測收據的內部顯示層，並非網站資料來源。

## 顯示規則

- `run_summary.json` 只按凍結的 10／25／50 bps 成本，以及候選策略、QQQ、SPY、PIT
  合資格等權（月度）、首輪 Top-10 等權後漂移四條路徑列出描述性指標。
- `run_failure.json` 只渲染成內部 failure log；不會建立策略表格，不會建立 Paper，亦不會
  產生實金動作。
- 成功摘要仍必須是 `paper_authorized=false`、`real_money_action_usd=0`、
  `public_promotion_allowed=false`。這份報表不代表可盈利或可落盤。
- 報表輸出不可寫入 `site/`；公開頁只讀 `site_export` 的成功白名單。未通過正式 release 閘門
  時，網站維持「今天不下單」。

## 產生報表

```bash
uv run python scripts/build_short_term_formal_backtest_report.py \
  --run-dir /path/to/owner-only/formal-run \
  --output /path/to/owner-only/formal-run/formal_research_report.md
```

`run-dir` 必須恰好包含一份 `run_summary.json` 或 `run_failure.json`。輸出檔會設成
owner-only `0600`；失敗收據只應留在正式 run 的內部目錄，不能複製到公開網站或當作行動建議。
