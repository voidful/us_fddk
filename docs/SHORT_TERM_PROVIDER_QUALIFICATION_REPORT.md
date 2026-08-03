# 美股短線高回報研究｜第十一輪數據來源資格報告

研究日期：2026-08-04　｜　官方文件存取：2026-08-03T19:51:29Z

狀態：**沒有單一來源通過採購前最低條件；逐股數據仍為 1/20**

## 一頁結論

本輪沒有再調短線策略參數，也沒有用供應商宣傳頁代替真實數據。四條事前固定來源逐項
對照既有 20 道 point-in-time／退市合約後，結論是：**CRSP／WRDS 最接近正式入口，
但仍只值得先索取 data dictionary、細樣本及授權條款；Norgate、Sharadar 及
Polygon.io／Massive 均不能單獨完成現有合約。**

| 路徑 | 官方文件明確 | 只部分支持 | 未解／待匯入 | 採購前通過 | 正確定位 |
|---|---:|---:|---:|---:|---|
| CRSP／WRDS | 10/20 | 2/20 | 8/20 | 否 | 最接近完整賬本的首個正式查詢對象 |
| Norgate Data | 6/20 | 4/20 | 10/20 | 否 | 歷史成分／日價補充來源，不能單獨通過 |
| Nasdaq Data Link Sharadar | 0/20 | 1/20 | 19/20 | 否 | 公開 schema 不足，需授權後再判斷 |
| Polygon.io／Massive Stocks | 4/20 | 6/20 | 10/20 | 否 | 日價、reference 及成本補充來源，不能單獨通過 |

「官方文件明確」不等於數據閘門通過。真實入口仍只過凍結順序 1/20；四條路徑本地驗證
全部為 false，正式 20 年逐股回測 0 次，短線 Paper 保持全現金、0 成交、0 持倉，
實金動作 US$0。

## 最重要的新發現

### 1. CRSP／WRDS 是首選查詢對象，但不是已通過

[CRSP 股票數據 guide](https://indexes.morningstar.com/docs/guide/crsp-us-stock-databases-guide-for-flat-file-format-2-0?isRdp=true)
明列 PERMNO／PERMCO、歷史 security／issuer information、ticker、CUSIP、primary
exchange、share class、SIC／NAICS／ICB／UES、日線 raw OHLCV、分派、調整因子、
delisting return 及 S&P 500 membership 起訖日。DlyOpen 自 1992 年後可用，覆蓋固定
2006–2026 主期。

但兩個硬缺口不能省略：guide 沒有找到 S&P 500 **成分公布時間**；DelRetMissType 又
明確容許某些退市回報缺失。沒有抽查真實 20 年 data cut 前，不能聲稱退出經濟回報完整，
更不能把 CRSP 品牌名稱直接當成 20/20。

### 2. Norgate 不是現有合約的單一替代品

[Norgate Data Content Tables](https://norgatedata.com/data-content-tables.php) 確認
Platinum／Diamond 有退市股票、1957 年起 S&P 500 歷史成分、日線 OHLCV、股息及
capital-event 指示；assetid 亦在證券生命週期保持不變。

然而 [Norgate 官方 FAQ](https://norgatedata.com/data-package-faq.php) 同時明示：

- 不提供舊 ticker，只把全部歷史接到現時／最後代號；
- 不提供歷史成分公布日期；
- 不直接提供公司行動事件明細或精確歷史主上市地；
- 不提供 delisting return，官方建議以最後交易 bar 近似。

最後交易 bar 不是破產全損、現金收購或換股代價的同義詞，會直接違反第 16 道硬閘門。
因此過往報告把 Norgate 與 CRSP 並列為「可能正式入口」需要收窄：Norgate 可作成分／
價格補充來源，但在現有合約下不能單獨放行。

### 3. Sharadar 公開資料不足以完成資格判定

Nasdaq Data Link 公開 metadata 只確認
[SEP](https://data.nasdaq.com/api/v3/datatables/SHARADAR/SEP/metadata.json)、
[TICKERS](https://data.nasdaq.com/api/v3/datatables/SHARADAR/TICKERS/metadata.json) 及
[ACTIONS](https://data.nasdaq.com/api/v3/datatables/SHARADAR/ACTIONS/metadata.json) 三張表，
亦可看到 permaticker、ticker/date 主鍵及 filters；完整欄位和原始列仍需有效 API key。
官方公開範圍沒有證明歷史 S&P 500 membership、成分公布時間、退出代價或歷史分類，
所以不先購買訂閱來尋找較好答案。

### 4. Polygon.io 已遷移至 Massive，適合補價格，不適合補成分／退出

原始三個 `polygon.io` URL 已 redirect 至 `massive.com`；原協議先按 domain 失敗，之後
另立只修正官方遷移 alias 的 schema-informed repair，固定
`independent_first_seen_evidence=false`。repair 後官方文件支持 2003 年起日線 OHLCV、
active／delisted ticker、Composite／Share Class FIGI、ticker change、股息及拆股；但沒有
找到歷史 S&P 500 membership、公布時間、完整 merger／spinoff outcome 或退出經濟回報。
它可在未來核對日價、成交及買賣差價，不可單獨修復存活者偏差。

## 十一項核心能力對照

| 能力 | CRSP／WRDS | Norgate | Sharadar | Polygon／Massive |
|---|---:|---:|---:|---:|
| 永久證券／公司 ID | 明確 | 明確 | 部分 | 部分 |
| 歷史代號及上市地 | 明確 | 部分 | 需登入 | 部分 |
| 成分公布時間 | 未見 | 未見 | 未見 | 未見 |
| 歷史 S&P 500 成分區間 | 明確 | 明確 | 未見 | 未見 |
| 固定 20 年日線 | 明確 | 明確 | 需登入 | 明確 |
| Raw OHLCV／總回報 | 明確 | 明確 | 需登入 | 明確 |
| 公司行動明細 | 明確 | 部分 | 需登入 | 部分 |
| 退市／收購經濟回報 | 部分 | 未見 | 需登入 | 未見 |
| 歷史分類 | 明確 | 未見 | 需登入 | 部分 |
| 股份類別去重 | 明確 | 部分 | 需登入 | 部分 |
| t 收市／t+1 開市 | 明確 | 明確 | 需登入 | 明確 |

「明確」只代表官方文件有相應欄位；「部分」代表仍欠合約要求的一部分；「需登入」不是
假定存在；「待匯入」只可由真實列的 SHA-256、列數、覆蓋率及正反稽核回答。

## 事前順序與非獨立 repair

原始第十一輪協議先於任何新官方文件提交，供應商集合、20 道映射、狀態詞及停止規則
均已固定。首次文件閱讀才發現 CRSP 已遷移至 Morningstar Indexes、Polygon.io 已遷移至
Massive；由於原 domain 白名單沒有兩個新 domain，原 source-scope 檢查先失敗。

其後 repair 只容許 `crsp.org → indexes.morningstar.com` 及
`polygon.io → massive.com` 兩個精確 alias，不增加供應商、不改 20 道映射或策略規則。
因為已看過 redirect 及部分內容，本輪不是獨立 first-seen 策略證據；它只是一份採購前
工程診斷。

## 下一個唯一有效動作

先向 CRSP／WRDS 索取不含敏感原始列的 schema、20 年細樣本及授權條款，書面回答：

1. S&P 500 成分公告時間能否逐次提供；
2. 2006–2026 有多少退出樣本缺 DelRet，能否取得現金／換股代價；
3. raw open／OHLCV、停牌及退市後價格的完整率；
4. 歷史分類與股份類別何時可知；
5. 本地研究、雜湊收據及禁止公開原始列的授權邊界。

五項都拿到後，才把合法轉換包送入既有 20 道驗證器。20/20 亦只准按已凍結 v1 規則
正式重跑一次，並須勝 QQQ、SPY、逐期成分等權及同股漂移，扣 10／25／50 bps，通過
NW／PSR／全專案 DSR／PBO 及前後十年、滾動窗口、危機段；全部經濟與統計門檻通過後，
才可由全現金建立不能回填的 Paper。歷史及文件研究不構成供應商背書、投資建議或盈利
保證。
