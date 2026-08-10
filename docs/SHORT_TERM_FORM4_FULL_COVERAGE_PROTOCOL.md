# 美股短線 Form 4 全季度 coverage-only 協議（Round 52）

凍結時間：`2026-08-10T12:25:47Z`

狀態：**事前凍結、資料覆蓋診斷 only。** 本輪先補足 Round49／50 只有三個季度的
Form 4 coverage，固定下載 2006Q1 至 2026Q2 的全部 82 季度；只計 schema、來源完整性及
現時 watchlist 對照數，不計任何市場回報、baseline、策略勝率、Paper 或實金動作。

## 1. 固定來源與下載邊界

- SEC 官方季度 ZIP URL template 固定為：
  `https://www.sec.gov/files/structureddata/data/insider-transactions-data-sets/{yyyy}q{q}_form345.zip`。
- 季度集合固定為 `2006Q1, 2006Q2, ..., 2025Q4, 2026Q1, 2026Q2`，共 82 季；不得跳季、換季、
  只留有事件的季或用結果重選。
- 每個季度必須以 SEC catalog URL、HTTP status、Content-Length、bytes SHA-256 及檔名寫入
  source manifest；fetch 不解析交易列，manifest 完成前不讀事件數。
- Round49 已有的三個 anchor bytes 必須精確重核：2006Q1、2016Q3、2026Q2 的 SHA-256
  不可漂移。其餘季度的 bytes/hash 由本輪首次完整下載後封存；任何重下載 hash 不一致即停止，
  不覆寫原 manifest。
- 原始 ZIP 只留在 owner-only staging（repository 外）；repository 只提交 URL／bytes／hash
  aggregate manifest，不提交 row-level Form 4、姓名、地址、CIK、accession 或交易金額。

## 2. 固定 watchlist 與兩條識別診斷

個股 watchlist 固定沿用 `usfddk/resources/us_large_cap_watchlist_v1.csv`：30 檔、SHA-256
`b6002e4e151bd298884f8cdd6272b5cbfde8aedca47cb58b92830d4d92028014`。它是現時 2026 名單，
不是歷史 point-in-time 成分；所有結果只能稱 current-cohort coverage。

對每個 SEC purchase accession，保留兩個互斥、aggregate-only 對照：

1. **current CIK exact**：`ISSUERCIK` 精確命中 2026-08-10 SEC `company_tickers.json`；
2. **as-filed trading-symbol exact**：`ISSUERTRADINGSYMBOL` 只做大寫、`.`／`/` → `-` 的
   確定性正規化後精確命中 watchlist。`N/A`、`NONE`、空白及模糊公司名稱一律排除。

兩條路徑分開列出；symbol match 不是歷史 security master、不是 known-at membership，也不能
以名稱相似或人工判斷補票。不得把 symbol match 改寫成 current CIK，亦不得因 coverage 低而
調低 Round49 的 Form 4 cluster 門檻。

## 3. 固定 schema、交易列與輸出

每季先沿用 Round42 physical-header、ZIP safety、CRC、row key、日期及 Decimal 驗證；purchase
列固定為 Round49 的 `Form 4`、`P`、`A`、swap false、正 shares／price 及合資格 owner token。
本輪只計每個 purchase accession 及 issuer aggregate，不建立 20 日 cluster、不用 owner
名單構造策略、不計 cluster 門檻的替代結果。

validation receipt 只能包含：

- 82 季 source manifest hash、schema／row aggregate、Form 4 denominator 及 purchase accession count；
- current CIK exact、as-filed symbol exact、兩者交集的 aggregate issuer／accession count；
- 缺檔、hash drift、schema error、mapping error 的固定代碼；
- `performance_present=false`、`strategy_run_count=0`、`paper_authorized=false`、
  `real_money_action_usd=0` 及 `today_action="今天不下單"`。

不得輸出 ticker、symbol、CIK、accession、filing date、owner、issuer name、notional 或任何
可由 aggregate 反推個別交易者的 row-level 欄位。所有 process-memory identifiers 結束即丟棄。

## 4. 成功門檻與下一步

本輪沒有 alpha／收益 gate。只有在 82/82 季 bytes、schema、manifest、anchor hash 及 deterministic
replay 全部通過，才把 coverage 狀態標為 `full_quarter_coverage_ready_for_separate_preregistration`。
這不等於個股策略可回測，也不授權 Paper；之後如要計算 event returns，必須另立協議、另綁
Round51 後的 global trial lower bound `6,290`，不得把本輪 coverage 當成已看過的回報結果。

若來源下載、歷史 mapping、raw execution 或 point-in-time security master 仍不足，狀態固定為
`coverage_incomplete_no_strategy`，網站維持 success-only；不以免費現時名單加 adjusted OHLCV
包裝成可交易 Form 4 策略。

## 5. 固定輸出

- protocol receipt：`artifacts/short_term_form4_full_coverage_protocol_receipt.json`；
- source manifest：`artifacts/short_term_form4_full_coverage_source_manifest.json`；
- validation log：`artifacts/short_term_form4_full_coverage_validation.json`；
- report：`docs/SHORT_TERM_FORM4_FULL_COVERAGE_REPORT.md`。

本輪是資料工程與研究準入紀錄，不構成投資建議、Paper 成交或實金落盤指令。
