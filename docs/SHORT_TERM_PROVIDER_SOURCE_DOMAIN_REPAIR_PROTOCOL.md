# 第十一輪官方來源 domain repair 協議 v1.0

凍結日期：2026-08-04（亞洲／台北）

狀態：`schema_informed_domain_repair_after_redirect_inspection`

## 原始協議失敗

原始 `SHORT_TERM_PROVIDER_QUALIFICATION_PROTOCOL.md` 只容許 `crsp.org`、
`wrds-www.wharton.upenn.edu`、`norgatedata.com`、`docs.data.nasdaq.com`、
`data.nasdaq.com` 及 `polygon.io`。首次按該範圍開啟官方文件時：

- CRSP 官方產品及 guide 頁已遷移到 `indexes.morningstar.com`；
- `polygon.io` 三個凍結文件 URL 已 redirect 到 `massive.com`。

兩組 redirect 都離開原始 domain 白名單，所以原協議的 source-scope 檢查失敗。失敗不得
靜默改寫為通過；原始 requested URL、final URL、HTTP status、bytes 及 SHA-256 全部保留
在 `artifacts/short_term_provider_document_receipt.json`。

## 唯一容許修正

本 repair 只增加兩個精確官方遷移 alias：

1. `crsp.org` → `indexes.morningstar.com`；
2. `polygon.io` → `massive.com`。

只有 requested URL 屬於原始凍結 domain、經 HTTPS redirect 到上述精確 final domain，
而且頁面仍屬同一已凍結供應商產品時才可使用。不得加入其他 domain、第三方文章、搜尋
摘要或未凍結供應商。

## 證據性質

建立本 repair 前已看過 redirect 目標及部分文件內容，因此固定：

- `independent_first_seen_evidence=false`；
- `source_domain_repair_only=true`；
- `provider_set_changed=false`；
- `twenty_gate_mapping_changed=false`；
- `strategy_rule_changed=false`；
- `paper_gate_changed=false`。

修正只讓文件可進入採購前診斷，不把任何供應商數據閘門升級為 passed，也不授權下載
付費原始列、正式逐股回測、Paper 或實金交易。若 repair 後仍欠成分公布時間、退出經濟
回報、歷史分類或本地授權樣本，結論必須保持失敗關閉。
