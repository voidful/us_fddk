# 短線個股第十一輪：Point-in-time 數據來源資格研究協議 v1.0

凍結日期：2026-08-04（亞洲／台北）

狀態：`frozen_before_official_provider_document_review`

## 目的與研究邊界

第九輪已把逐股 point-in-time／退市入口固定為 20 道硬閘門，但真實數據包只有 1/20。
第十輪的學術每日動量環境策略亦只過 27/48，不能取代可買賣股份的正式驗證。本輪只回答：
哪一條合法數據取得路徑最接近既有 20 道合約，尚欠哪些欄位、授權或實證抽查。

本輪不是新策略，不計算回報，不更改 12–1／6–1 動量、200 日趨勢、63 日低波幅、
Top-10、行業上限、成本、日期、基準或 Paper 門檻。官方產品文件只能構成採購前證據，
不能把真實數據入口由 1/20 升級。未有本地合法數據包逐列通過前，正式回測仍為 0 次，
短線 Paper 保持全現金，實金動作 US$0。

## 事前固定候選路徑

只研究四條具不同定位的路徑，不因文件結果增刪供應商：

1. **CRSP／WRDS**：CRSP US Stock／Indexes 經合法機構或個人授權取得；
2. **Norgate Data**：美股數據及歷史指數成分產品，須有容許本地研究的有效訂閱；
3. **Nasdaq Data Link Sharadar**：SEP／TICKERS／ACTIONS 等相應授權表；
4. **Polygon.io Stocks**：Stocks flat files／reference／corporate actions 相應方案。

只可閱讀供應商、交易所、指數擁有人或 WRDS 的官方公開文件。搜尋結果摘要、第三方評測、
論壇及生成式摘要不得用作欄位能力證據。若官方文件需登入而未能存取，狀態固定為
`unresolved_login_required`，不得用推測填補。

## 固定評核方法

每條路徑逐項映射既有 20 道入口，單元狀態只接受：

- `documented`：官方文件明確支持該能力，但仍未以本地原始列驗證；
- `partial`：只支持閘門的一部分，或需另一產品／自行計算；
- `not_documented`：在本輪凍結的官方文件範圍沒有找到；
- `unresolved_login_required`：可能存在，但官方細節需要登入或獲授權後才可檢查；
- `not_applicable_until_import`：SHA-256、列數、固定期間、實際覆蓋率等只能在匯入後驗證。

`documented` 絕不等於數據閘門 `passed`。現時 20 道真實入口分數只讀取
`artifacts/short_term_point_in_time_readiness.json`，不可由文件矩陣改寫。

## 事前固定採購前最小條件

一條路徑只有同時符合下列條件，才可列為「可要求樣本／報價」：

1. 官方文件明確包含不活躍／退市證券，而非只列現存 ticker；
2. 有永久證券或公司識別碼及歷史 identifier 能力；
3. 有歷史 S&P 500 成分生效區間，或可合法連接官方 point-in-time 成分產品；
4. 有原始日線 OHLCV、派息／拆細及退出經濟回報，或能由明確事件表完整重建；
5. 授權容許本專案本地研究，且不要求公開再分發受限制原始列；
6. 能提供 2006-08-01 至 2026-07-31 或更長期間；
7. 供應商能回答成分公布時間、停牌、收購／退市、歷史分類及股份類別的樣本問題。

缺任何一項，只可列為補充來源或不合格；不得用多個殘缺免費來源拼接後宣稱無存活者偏差。

## 固定官方文件範圍

本輪先凍結官方 domain 及查核主題，再閱讀內容：

| 路徑 | 官方 domain | 固定查核主題 |
|---|---|---|
| CRSP／WRDS | `crsp.org`、`wrds-www.wharton.upenn.edu` | permanent identifiers、names／exchange history、daily raw prices and returns、distributions、delisting returns、index membership、industry codes |
| Norgate Data | `norgatedata.com` | delisted securities、historical index constituents、price／volume、dividends、capital events、classification、Python／export access |
| Sharadar | `docs.data.nasdaq.com`、`data.nasdaq.com` | active and delisted tickers、SEP prices、ACTIONS、permanent IDs、historical index membership、classification |
| Polygon.io | `polygon.io` | active／inactive tickers、ticker events、daily OHLCV、dividends／splits、acquisitions／delisting、historical index membership／classification |

如官方頁面改址，只可跟隨同一官方 domain 的 redirect 或官方站內連結，並在收據記錄
最終 URL、頁面標題、存取時間及內容 SHA-256。不得在看過內容後擴大主題來提高分數。

## 固定輸出

本輪只產生：

- `artifacts/short_term_provider_qualification.json`：機器可讀矩陣、來源收據及結論；
- `site/data/short-term-provider-qualification.json`：只含可公開摘要，不含登入、價格或憑證；
- `docs/SHORT_TERM_PROVIDER_QUALIFICATION_REPORT.md`：香港金融用詞的一頁式採購前報告；
- 網頁短線分頁的資料取得路線圖。

每個文件結論必須分開：`documented_capability`、`locally_verified`、`contract_passed`。
本輪 `locally_verified=false`、`contract_passed=false`，除非使用者另行提供合法數據包；
即使找到最完整供應商，也不得啟動回測、Paper 或真倉。

## 停止規則

四條固定路徑及 20 道映射完成後停止，不再以增加供應商或更換評分定義尋找較好結果。
若沒有路徑達到採購前最小條件，結論就是「未有合格單一入口」；下一步只可取得正式
樣本／data dictionary／授權後，另立 schema mapping repair 或 import receipt。研究結果
不構成投資建議、盈利承諾或數據採購授權。
