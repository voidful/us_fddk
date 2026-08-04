# 短線個股第 21 輪：多供應商正式數據補缺報告

證據截至：2026-08-04

## 一頁結論

**五條固定路徑沒有一條合格。** 公開一手文件最多只把
`crsp_spdj_composite` 收窄至 **5/14 明確、
5/14 部分**；它仍有 **9/14**
不是明確能力。LSEG 是最完整的單一品牌採購候選，但同樣未公開證明 S&P 500 逐列公布
時間、退市實收回報、精確一個月日度簡單 RF 及使用者授權。

這輪找到的是**可判定的詢價次序**，不是可跑回測的市場列。十五道證據控制
**15/15 通過**，十五項單一
替代攻擊 **15/15 全部拒收**；
它只證明 validator fail closed。真實正式就緒仍為
**1/18**，授權
provider package **0**、完整 RF **0**、正式策略運行 **0 次**、短線 Paper **全現金**、持倉
**0**、實金動作 **US$0**。

## 五條固定路徑

「明確」只代表官方文件明示產品／欄位能力；「部分」仍是缺口。公開頁最高只可成為採購
候選，不能當作已訂閱、已授權、已交付或 20 年覆蓋通過。

| 路徑 | 明確 | 部分 | 不符 | 未解 | 真實樣本 | 完整合格 | 判斷 |
|---|---:|---:|---:|---:|---:|---:|---|
| CRSP Stock CIZ＋S&P DJI 事件＋CRSP Treasury | 5/14 | 5/14 | 1/14 | 3/14 | 0/14 | 0/14 | 採購候選；未合格 |
| S&P Global Market Intelligence | 2/14 | 4/14 | 1/14 | 7/14 | 0/14 | 0/14 | 採購候選；未合格 |
| LSEG Data & Analytics／Workspace／Datastream | 3/14 | 7/14 | 0/14 | 4/14 | 0/14 | 0/14 | 採購候選；未合格 |
| FactSet | 2/14 | 7/14 | 0/14 | 5/14 | 0/14 | 0/14 | 採購候選；未合格 |
| Bloomberg Enterprise／Data License | 3/14 | 5/14 | 0/14 | 6/14 | 0/14 | 0/14 | 採購候選；未合格 |

### 重要反證

- S&P Global Market Intelligence 的公開 Index Data 及 Market Data 規格均標示
  `Point In Time: No`；歷史很長也不能補成逐期可知資料。
- S&P DJI 政策把公布及生效分開，並描述日常 corporate-event／pro-forma 文件；公開頁仍
  未提供本帳戶可下載的逐列 event ID、完整舊檔及授權條款。
- LSEG 可用 as-of 成分加 Joiner／Leaver 重建歷史，且 Quantitative Analytics 說明
  point-in-time、已退市公司、永久 ID 及歷史成分；但「涵蓋已退市公司」不等於提供每次
  退出的實際現金／換股收益。
- FactSet Benchmarks API 可按指定日期取得成分；as-of date 不等於 announcement time。
- Bloomberg Data License 有 20 年以上 Bulk 歷史、公司行動、歷史價格及 source-file
  tracing；其 company／pricing PIT 產品公開覆蓋為 17 年，亦未證明 S&P 500 membership
  事件能按本合約逐列交付。

## 十四項能力矩陣

| 正式能力 | CRSP Stock CIZ＋S&P DJI 事件＋CRSP Treasury | S&P Global Market Intelligence | LSEG Data & Analytics | FactSet | Bloomberg Enterprise |
|---|---|---|---|---|---|
| 研究授權 | 未解 | 未解 | 未解 | 未解 | 未解 |
| 逐期 S&P 500 成分 | 明確 | 不符 | 明確 | 部分 | 部分 |
| 成分公布時間 | 部分 | 未解 | 未解 | 未解 | 未解 |
| 成分生效時間 | 明確 | 部分 | 部分 | 部分 | 未解 |
| 永久證券／公司 ID | 明確 | 明確 | 明確 | 明確 | 明確 |
| Metadata KnownAt | 未解 | 未解 | 部分 | 未解 | 部分 |
| Raw 日線及狀態 | 明確 | 明確 | 明確 | 明確 | 明確 |
| 分派事件時鐘及條款 | 明確 | 部分 | 部分 | 部分 | 明確 |
| 退市／退出經濟 | 部分 | 未解 | 部分 | 部分 | 部分 |
| 移除後價格路徑 | 未解 | 未解 | 未解 | 未解 | 未解 |
| XNYS 日曆 | 部分 | 未解 | 部分 | 部分 | 未解 |
| 同步 QQQ／SPY | 部分 | 部分 | 部分 | 部分 | 部分 |
| 精確一個月日度 RF | 不符 | 未解 | 未解 | 未解 | 未解 |
| 逐列來源重播 | 部分 | 部分 | 部分 | 部分 | 部分 |

## 第一封詢價只問九個可驗收問題

先向 CRSP＋S&P DJI 複合路徑及 LSEG 單一品牌路徑索取相同細樣本。任何回答只有
「可以」「有歷史」「可經 API 取得」而沒有產品代碼、欄位、timestamp、覆蓋率及樣本，
一律保持未解。

1. **研究授權**：請提供允許本地研究、20 年回測、保存驗收收據及發布彙總衍生結果的合約條款。
2. **成分公布時間**：每次 S&P 500 加入／移除可否交付公布 timestamp、時區、event ID 及原始來源？
3. **Metadata KnownAt**：歷史 ticker、交易所、股份類別及行業可否逐列交付 KnownAt，而非只給 effective range？
4. **退市／退出經濟**：缺失 DelRet 時可否交付原因、現金／換股條款、successor 及實際退出收益？
5. **移除後價格路徑**：可否保證每次成分移除日至下一月度重新平衡 open 的 raw 可交易價格及狀態完整？
6. **XNYS 日曆**：可否同 cut 交付 2005-08-01 至 2026-07-31 的 XNYS session、開收市及早收市時間？
7. **同步 QQQ／SPY**：QQQ／SPY 可否與個股同 session、同 cut 交付 raw open、總回報因子及交易狀態？
8. **精確一個月日度 RF**：可否交付 US_1M_TBILL_DAILY_RETURN 同經濟定義的日度 simple return，而非 4 週或年率換算？
9. **逐列來源重播**：每次 export 可否固定產品版本、cutoff、export ID、逐列 source ID、列數及 SHA-256？

## 收到真實樣本後的固定順序

1. 供應商文件 12/12：產品、授權、覆蓋、時間及退出條款逐項入 manifest；
2. 本地隔離匯入 16/16：原始 package 不修改、逐檔列數與 SHA-256 齊備；
3. point-in-time 20/20：成分、身份、公司行動、退市及幽靈價格全部 fail closed；
4. execution extension 16/16：252 個 prior sessions、移除後路徑及同步 QQQ／SPY；
5. 精確 RF 完整：不以 4 週、年率／252、DGS1MO、SHY、SOFR 或零回報代替；
6. 正式就緒 18/18 後，才准使用一次性 run ID 原樣運行凍結的 20 年回測；
7. 只有正式回測及前瞻 Paper 推廣閘門都通過，才可討論下一階段，並仍不等於保證盈利。

## 十五道證據控制

- 01｜協議與父契約：**通過**。第 21 輪協議、收據及第 18／20 輪 SHA-256 完整。
- 02｜台股參考版本：**通過**。三個參考 repository 精確綁定，只轉移研究紀律。
- 03｜五條候選路徑：**通過**。沒有看過結果後加第六條路徑或調換次序。
- 04｜十四項能力：**通過**。每條路徑逐項回答同一正式合約。
- 05｜一手文件：**通過**。只使用供應商／數據擁有者的官方頁面、指南及 API 文件。
- 06｜產品身份：**通過**。品牌宣傳沒有被推算成已存在的固定產品代碼。
- 07｜研究授權：**通過**。公開可讀與使用者帳戶授權分開。
- 08｜固定 20 年覆蓋：**通過**。歷史年數宣傳不代替 2005-08-01 起逐列 manifest。
- 09｜成分雙時鐘：**通過**。AnnouncedAt 與 EffectiveAt 分開。
- 10｜Metadata KnownAt：**通過**。有效區間不冒充當時可知時間。
- 11｜Raw 開市價：**通過**。調整價不冒充 t+1 raw open。
- 12｜退出經濟：**通過**。缺失 DelRet／條款保留缺口，不補零。
- 13｜日曆與同步基準：**通過**。XNYS、QQQ、SPY 與個股執行時鐘均保留。
- 14｜精確 RF：**通過**。4 週、年率／252 或代理 ETF 均不替代正式 RF。
- 15｜決策邊界：**通過**。正式 1/18、run 0、Paper 全現金、實金 US$0。

## 十五項單一錯誤攻擊

- 01｜協議 SHA 漂移：**拒收** `gap_protocol_mismatch`
- 02｜台股參考 commit 漂移：**拒收** `gap_reference_mismatch`
- 03｜候選路徑次序漂移：**拒收** `candidate_set_mismatch`
- 04｜少一項正式能力：**拒收** `capability_set_mismatch`
- 05｜第三方文章冒充一手證據：**拒收** `non_primary_evidence`
- 06｜由品牌宣傳推算產品：**拒收** `product_identity_inference`
- 07｜公開下載冒充研究授權：**拒收** `license_inference`
- 08｜歷史宣傳冒充 20 年覆蓋：**拒收** `coverage_inference`
- 09｜生效時間冒充公布時間：**拒收** `membership_time_substitution`
- 10｜有效區間冒充 KnownAt：**拒收** `known_at_substitution`
- 11｜調整價冒充 raw open：**拒收** `adjusted_price_substitution`
- 12｜缺失退出代價填 0：**拒收** `delist_imputation`
- 13｜省略日曆或同步基準：**拒收** `calendar_benchmark_omission`
- 14｜相近年期冒充精確 RF：**拒收** `risk_free_substitution`
- 15｜文件分數啟動 Paper：**拒收** `gap_decision_boundary_violation`

## 官方一手來源

- [Morningstar Indexes / CRSP｜CRSP US Stock Databases Guide for Flat File Format 2.0](https://indexes.morningstar.com/docs/guide/crsp-us-stock-databases-guide-for-flat-file-format-2-0?isRdp=true)
- [Morningstar Indexes / CRSP｜CRSP US Treasury Database Guide](https://indexes.morningstar.com/docs/guide/crsp-us-treasury-database-guide?isRdp=true)
- [S&P Dow Jones Indices｜S&P DJI API Data Solutions](https://www.spglobal.com/spdji/en/landing/topic/api-data-solutions/)
- [S&P Dow Jones Indices｜Equity Indices Policies & Practices](https://www.spglobal.com/spdji/en/documents/methodologies/methodology-sp-equity-indices-policies-practices.pdf?force_download=true)
- [S&P Dow Jones Indices｜S&P U.S. Indices Methodology](https://www.spglobal.com/spdji/en/documents/methodologies/methodology-sp-us-indices.pdf?os=TMB)
- [S&P Global Market Intelligence｜Market Data](https://www.marketplace.spglobal.com/en/datasets/market-data-%2817%29)
- [S&P Global Market Intelligence｜Index Data](https://www.marketplace.spglobal.com/en/datasets/index-data-%28100%29)
- [S&P Global Market Intelligence｜Corporate Actions](https://www.spglobal.com/market-intelligence/en/solutions/corporate-actions)
- [S&P Global Market Intelligence｜Index Management](https://www.spglobal.com/market-intelligence/en/solutions/products/index-management)
- [LSEG Developer Community｜Building Historical Index Constituents](https://developers.lseg.com/en/article-catalog/article/building-historical-index-constituents)
- [LSEG｜Quantitative Analytics Cloud Fact Sheet](https://www.lseg.com/content/dam/data-analytics/en_us/documents/fact-sheets/quantitative-analytics-cloud-fact-sheet.pdf)
- [LSEG｜Corporate Actions Data](https://www.lseg.com/en/data-analytics/market-data/data-analytics-pricing/reference-data/corporate-actions)
- [FactSet｜FactSet Pricing and Reference Data](https://www.factset.com/marketplace/catalog/product/factset-pricing-and-reference-data)
- [FactSet｜FactSet Prices and Returns API](https://www.factset.com/marketplace/catalog/product/factset-prices-and-returns-api)
- [FactSet｜FactSet Benchmarks API](https://developer.factset.com/api-catalog/factset-benchmarks-api)
- [FactSet｜FactSet Global Prices API](https://developer.factset.com/api-catalog/factset-global-prices-api)
- [Bloomberg｜Data License](https://professional.bloomberg.com/products/data/data-management/data-license/)
- [Bloomberg｜Reference Data](https://professional.bloomberg.com/products/data/enterprise-catalog/reference/)
- [Bloomberg｜Investment Research Data](https://professional.bloomberg.com/products/data/enterprise-catalog/investment-research-data/)
- [Bloomberg｜Company Financials, Estimates and Pricing Point-in-Time](https://professional.bloomberg.com/products/data/enterprise-catalog/cofi/)
- [Bloomberg｜Event-Driven Feeds](https://professional.bloomberg.com/products/data/enterprise-catalog/event-driven-feeds/)

- [第 21 輪事前協議](SHORT_TERM_PROVIDER_GAP_CLOSURE_PROTOCOL.md)
- [第 20 輪供應商收斂報告](SHORT_TERM_PROVIDER_CONVERGENCE_REPORT.md)
- [第 18 輪正式回測事前登記](SHORT_TERM_FORMAL_BACKTEST_PREREGISTRATION.md)

本報告只作研究及專業資訊參考，不構成供應商背書、採購建議、投資建議、回報預測或
盈利保證。
