# 短線個股第三十三輪：官方 provider 證據刷新報告

研究輪次：33
協議 SHA-256：`42c55adf76bba072b50618800890e5e34f07aae3d0b68be7ec1b46f5dcdaea9d`
結果：**manual_review_required**
觀察時間（UTC）：`2026-08-08T20:59:50.806841Z`

## 結論

本次唯讀探針觀察到 **3/4**
個凍結來源身份，`all_frozen_identity_checks_pass=False`。
這不是資料包，也不是授權證明；它只顯示官方文件身份或內容有漂移時，入口會停在人工覆核。

- 遠端下載層：`remote_download_failed`：crsp_ciz_migration_notice: HTTPError: HTTP Error 404: Not Found
- observation-level error：
- `crsp_ciz_guide`：`marker_missing` — crsp_ciz_guide marker check failed
- `crsp_index_history_feed`：`marker_missing` — crsp_index_history_feed marker check failed
- formal readiness：1/18；
  point-in-time readiness：1/20。
- provider package qualified：`False`；
  formal backtest authorized：`False`。
- Paper：`all_cash`；strategy runs：`0`；
  實金動作：**US$0**。

## 遠端 observation 收據

原始 HTML／PDF bytes 沒有保存到 repository；只保留 URL、HTTP、content type、大小、
SHA-256 及 marker 布林值，並繼續拒絕將文件身份升格為供應商 package。

| source | HTTP／content type | bytes | SHA-256 | marker checks |
|---|---:|---:|---|---|
| crsp_ciz_guide | 200／text/html; charset=utf-8 | 548,103 | `d8a6f17f45e833bd9b060f92a96020c1a1d6fb474d8dfc2b4f9a6b20fabdfeb6` | `CIZ` ✗, `CRSP US Stock Databases Guide` ✓ |
| crsp_index_history_feed | 200／application/pdf | 145,917 | `b1cf470b98741add92c9ed16eb5698eb90674180cf01afd083670fb50c073eb9` | `%PDF-` ✓, `INDEX LEVEL AND CONSTITUENT HISTORY` ✗ |
| lseg_historical_constituents | 200／text/html;charset=utf-8 | 296,726 | `2252be7ad1b5fe6b639fb4db111cea178fc5481ac239bd966e9f281cb23bb222` | `Building historical index constituents` ✓, `Joiner` ✓, `Leaver` ✓ |

## 能力與決策邊界

既有 capability matrix 不因公開文件或 URL 變動而升級：逐期成分公布時間、security
metadata KnownAt、完整 DelRet／缺失原因／successor、row-level provenance 仍須授權樣本
和完整 manifest 才能驗證。不得以 effective date 冒充 announced-at，不得以現時／restated
history 冒充 as-known snapshot，不得把缺失退市回報補成零。

本輪固定維持：

- `new_source_qualified=false`
- `provider_package_qualified=false`
- `formal_backtest_authorized=false`
- `paper_state=all_cash`
- `real_money_action_usd=0`

下一個有效動作：取得使用者已授權的完整 provider package，按既有 Round21 的 18/18、
point-in-time 20/20、execution 16/16、完整 RF 及 row-level provenance 驗收；在此之前
不得重選參數、回填交易、開 Paper 或部署新網站版本。

一手入口：

- [CRSP／Morningstar levels and constituents](https://www.crsp.org/indexes/levels-constituents/)
- [CRSP Historical Indexes Guide](https://www.crsp.org/crsp_pdf/crsp-historical-indexes-guide/)
- [LSEG Building historical index constituents](https://developers.lseg.com/en/article-catalog/article/building-historical-index-constituents)

本報告只作研究及專業資訊參考，不構成供應商背書、投資建議、回報預測或盈利保證。
