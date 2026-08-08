# 短線個股第三十三輪：官方 provider 證據刷新協議 v1.0

凍結時間：2026-08-08T14:44:43Z

狀態：`frozen_before_first_remote_observation`

## 目的

本輪只刷新官方 provider 文件的身份、可見欄位及版本漂移，回答上一輪仍未解決的
point-in-time 成分、公布／生效時鐘、退市經濟及可重播來源問題。它不是新數據包、不是
策略回測，也不是 Paper 升級。第一個遠端 observation 必須在本協議及收據凍結後才可接受。

## 不可移動邊界

- 不登入、不購買、不接受供應商條款，也不假設公開頁等於研究授權。
- 不下載或保存 CRSP／LSEG 的受限原始檔；探針只在記憶體內讀取，輸出 URL、最終 host、
  HTTP／content type、大小、SHA-256 及布林 marker 結果。
- 不把 `MbrStartDt`、`Effective on Open Date` 或 Joiner／Leaver change date 寫成
  `AnnouncedAt` 或逐列 `KnownAt`。
- 不把「latest／restated history」寫成當時可得的 point-in-time snapshot；不把產品頁的
  歷史宣稱寫成已交付 20 年樣本。
- 不把缺失 DelRet、公司行動條款、XNYS session 或一個月日度簡單 RF 補成可用；不得
  因文件刷新改寫能力矩陣、正式回測、Paper 或實金狀態。

## 凍結的台股參考版本

以下 commit 只提供 D+1、研究／訊號／Paper 分層、同池基準、凍結規則及負結果紀律，
不搬用台股參數、權證或收益宣稱：

- `appr1ciat1/tst_wocker@3372aa088328700feafeeb07c72ab832ea2d3ecb`；
- `appr1ciat1/tw-block-warrant@37463c54796ba36f4aac262519ea7fc2ef797de6`；
- `appr1ciat1/tst_wocker_filter_lab@06c87b7a1735877c9ccbab3a339c1742814a5058`。

## 只接受的一手來源

| source id | 官方 owner／文件 | 固定 URL | 只核對的身份 marker |
|---|---|---|---|
| `crsp_ciz_guide` | Morningstar Indexes／CRSP Stock CIZ guide | `https://indexes.morningstar.com/docs/guide/crsp-us-stock-databases-guide-for-flat-file-format-2-0?isRdp=true` | `CRSP US Stock Databases Guide`、`CIZ` |
| `crsp_index_history_feed` | CRSP Index File Description／Direct Client Feed | `https://www.crsp.org/wp-content/uploads/2023/10/Index_File_Description-Direct_Client_Feed.pdf` | `%PDF-`、`INDEX LEVEL AND CONSTITUENT HISTORY` |
| `crsp_ciz_migration_notice` | CRSP CIZ migration notice | `https://www.crsp.org/important-notice-crsp-us-stock-amp-indexes-databases-flat-file-format-2-0-ciz/` | `Beginning July 28, 2026`、`December 2024` |
| `lseg_historical_constituents` | LSEG Developer Community | `https://developers.lseg.com/en/article-catalog/article/building-historical-index-constituents` | `Building historical index constituents`、`Joiner`、`Leaver` |

探針固定只接受上述 host（`indexes.morningstar.com`、`www.crsp.org`／`crsp.org`、
`developers.lseg.com`）及 HTTPS。重導向到其他 host、非 200、超過 32 MiB、marker 缺失或
source id 集合漂移，均為人工覆核；不自動改寫任何既有 provider 決策。

## 事前能力判讀

本輪預先固定下列判讀，遠端 observation 只可驗證身份或標記漂移，不能自行把狀態升級：

| 能力 | 本輪最多可支持的狀態 | 原因 |
|---|---|---|
| `point_in_time_sp500_membership` | `partial_primary_documentation` | CRSP 有歷史／最新 restated 檔；LSEG 以 Joiner／Leaver 重建，均未提供本研究所需的逐事件 as-known export 收據 |
| `membership_announced_at` | `unresolved_primary_documentation` | 生效日、change date 或 release time 不是成分公布 timestamp／event ID |
| `membership_effective_at` | `partial_primary_documentation` | CRSP 的 open-date／LSEG change-date 仍須授權樣本確認 session、時區及欄位 |
| `security_metadata_known_at` | `unresolved_primary_documentation` | 有效區間或目前 metadata 不等於逐列 KnownAt |
| `delist_exit_economics` | `unresolved_primary_documentation` | 文件身份刷新不會交付 DelRet、缺失原因、現金／換股條款及 successor row |
| `row_level_provenance_replay` | `partial_primary_documentation` | 文件／release／restatement 說明不等於本地 export ID、逐列 source ID、列數及 SHA |

其餘 14 項正式能力仍沿用 Round21 閉合矩陣；公開文件最高決策仍為
`procurement_candidate`。`authorized_provider_package=false`、formal readiness `1/18`、
strategy run `0`、短線 Paper `all_cash`、實金動作 `US$0` 必須在 observation 前固定。

## 控制及單一錯誤攻擊

1. 協議、收據及 Round21 父收據 SHA-256 必須完整；
2. 三個台股參考 commit、source id 集合及 URL 不得漂移；
3. 只接受官方 owner，一手頁面或官方 PDF；
4. 重導向 host、HTTP、content type、32 MiB 上限及 HTTPS 均須檢查；
5. HTML marker 不得以標題推算欄位能力；PDF 只核對 magic、marker／身份，不保存內容；
6. 首次 observation 必須在凍結收據後，重跑 hash 漂移必須標記人工覆核；
7. 不把 release／restatement／effective date 冒充 announced／known-at；
8. 不把公開產品頁冒充授權或完整 20 年 sample；
9. 不以文件刷新建立 strategy result、持倉或交易建議；
10. artifact 只保存可重播 metadata，不保存受限原始 bytes；
11. 任何 marker／來源漂移不升級 readiness；
12. 結果必須保留 `provider_package_qualified=false`、`formal_backtest_authorized=false`、
    `paper_state=all_cash` 及 `real_money_action_usd=0`。

測試須對應下列語義錯誤並拒收：`protocol_mismatch`、`source_set_mismatch`、
`non_https_or_host_drift`、`http_status_mismatch`、`body_size_exceeded`、
`marker_missing`、`source_hash_drift`、`announcement_time_substitution`、
`known_at_substitution`、`license_inference`、`raw_source_persisted`、
`decision_boundary_violation`。

## 輸出及停止規則

- `artifacts/short_term_provider_evidence_refresh_protocol_receipt.json`；
- `artifacts/short_term_provider_evidence_refresh.json`；
- `site/data/short-term-provider-evidence-refresh.json`；
- `docs/SHORT_TERM_PROVIDER_EVIDENCE_REFRESH_REPORT.md`。

若所有 source identity marker 都匹配，只能得出 `observed_official_sources`；若任何
身份或 hash 漂移，輸出 `manual_review_required`。兩者都不提高 readiness、不運行 20 年
回測、不啟動 Paper、不建立實金下單名單。只有使用者另行提供完整授權 package，才回到
Round21 的 18/18、point-in-time 20/20、execution 16/16 及 RF 完整驗收。

本協議只作研究及專業資訊參考，不構成供應商背書、採購建議、投資建議或盈利保證。
