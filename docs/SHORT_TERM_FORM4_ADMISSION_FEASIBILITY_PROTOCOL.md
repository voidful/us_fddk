# 美股短線第 42 輪：Form 4 admission feasibility 事前協議 v1.0

FrozenAt：`2026-08-09T23:30:18Z`

狀態：**result-blind protocol freeze；SEC 擷取 0、真實樣本選擇 0、候選選擇 0、策略運行 0、
績效結果 0。** 本輪只驗證小樣本 admission 證據能否完整重播，不產生公司、人物、股票代號、
持倉、回報或交易訊號。第 41 輪 Form 4 v1.1 的 16 項 admission gate 原樣保留。freeze 時為
`0/16`；未來真實 feasibility run 可按每項精確證據公開 `passed/16`，但只有 `16/16` 才是
admission。任何低於 `16/16` 仍須維持 candidate selection 0、strategy run 0、Paper false。

## 1. 固定來源與 9–12 份樣本

唯一季度依序為 `2006Q1`、`2016Q3`、`2026Q2`。每季 ZIP 必須有且只有一個可解析的 W3C
Table Group metadata JSON；以內容及 schema 辨識，不猜測或固定 metadata filename／extension。
其 `tables[].url` 必須全是沒有 directory、percent-encoding 或 traversal 的純 basename，且精確
一對一指向以下八個 required TSV role；不得把 ZIP 誤稱為精確只有八個 member。每個 TSV 的
header 名稱及次序必須精確等於對應 `tables[].tableSchema.columns[].name`，並至少包含下列
必要 anchor。role、metadata、member 或 header 缺失、重複、大小寫漂移即停止：

- `SUBMISSION.tsv`（`ACCESSION_NUMBER`, `FILING_DATE`, `DATE_OF_ORIG_SUB`,
  `DOCUMENT_TYPE`, `ISSUERCIK`）
- `REPORTINGOWNER.tsv`（`ACCESSION_NUMBER`, `RPTOWNERCIK`, `RPTOWNERNAME`）
- `NONDERIV_TRANS.tsv`（`ACCESSION_NUMBER`, `NONDERIV_TRANS_SK`, `TRANS_FORM_TYPE`,
  `TRANS_CODE`, `TRANS_ACQUIRED_DISP_CD`）
- `NONDERIV_HOLDING.tsv`（`ACCESSION_NUMBER`, `NONDERIV_HOLDING_SK`）
- `DERIV_TRANS.tsv`（`ACCESSION_NUMBER`, `DERIV_TRANS_SK`, `TRANS_FORM_TYPE`, `TRANS_CODE`,
  `TRANS_ACQUIRED_DISP_CD`）
- `DERIV_HOLDING.tsv`（`ACCESSION_NUMBER`, `DERIV_HOLDING_SK`）
- `FOOTNOTES.tsv`（`ACCESSION_NUMBER`, `FOOTNOTE_ID`, `FOOTNOTE_TXT`）
- `OWNER_SIGNATURE.tsv`（`ACCESSION_NUMBER`, `OWNERSIGNATURENAME`,
  `OWNERSIGNATUREDATE`）

每季只在 `SUBMISSION.tsv` 保留 `DOCUMENT_TYPE` 精確為 `4` 或 `4/A` 的列；
`ACCESSION_NUMBER` 必須唯一且符合 `##########-##-######`；raw `FILING_DATE` 必須嚴格符合
`DD-MON-YYYY` 的 English uppercase month token，解析成真實曆日後 normalize 為 ISO date，且
日期必須落在該季度。按 `(normalized FILING_DATE, ACCESSION_NUMBER)` 升冪排序；若共有 `n`
列，固定取：

1. first：zero-based index `0`；
2. median：`floor((n-1)/2)`，偶數明確取 lower median；
3. last：`n-1`。

每季 `n>=3` 且三個 base accession 必須不同。再在同一排序中由前至後取第一個未出現在 base
三筆的 `4/A` 作 amendment specimen；如有就追加為第四筆。如該季所有 `4/A` 已落在 base，
不重複 accession，標為 `amendment_covered_by_base`；如整季沒有 `4/A`，sample gate 必須失敗。
因此每季 3–4、合計 9–12 個 unique accession，且每季至少覆蓋一個 `4/A`。輸入列次序、ZIP
member 次序、TSV 換行或 locale 不得改變選樣。不得以 issuer、人物、交易 code、金額、價格、
後來是否有完整檔案或任何結果重抽樣。若樣本是 `4/A`，只保存 `DATE_OF_ORIG_SUB` 及 as-filed
明示的 lineage 證據；找不到明確 target 時標為 `amendment_target_unresolved`，不得用相近日期、
人物、股數或 issuer 猜配，也不得宣稱 gate 10 通過。

## 2. archive known-at 證據

每個選定 accession 必須在 owner-only、repository 外的 quarantine 保存並雜湊：

- 該 `index_date` 的完整 SEC daily form index 原始 bytes、SHA-256、byte count，以及唯一匹配
  accession／form type／archive path 的 index row；
- 完整 as-filed submission `.txt` 原始 bytes、SHA-256、byte count，且其 accession、CIK 與
  daily index archive path 一致；只雜湊 primary XML 或季度 flat file 不合格；
- request／source receipt、HTTP attempt ledger 與 object receipt 的 SHA-256；本地
  `first_observed_at` 不冒充歷史公開時間。

SEC daily form index 是 `index_date` 當晚約美東 10 時更新的 archive evidence；它不是精確到秒
的 filing public-time，`accepted_at` 亦不得替代 known-at。本輪不映射交易時鐘。若未來另經授權
使用，保守時鐘固定為：在該 nightly index boundary **之後的下一個完整 XNYS session close**
才可作 `decision_session`，交易只可在其後一個 XNYS session open；不得同晚、翌日開市或挑選
較有利的 decision／entry。

## 3. 精確輸出

本次 freeze 只可提交：

1. `docs/SHORT_TERM_FORM4_ADMISSION_FEASIBILITY_PROTOCOL.md`；
2. `artifacts/short_term_form4_admission_feasibility_protocol_receipt.json`；
3. 對上述 bytes、父鏈、零績效邊界及 deterministic selector 的測試。

未來獲明確授權的 feasibility run 才可在 private quarantine 產生
`form4_admission_feasibility_private_manifest.json`（9–12 個 accession、八 member、raw/index/
submission hashes）；Git 內只可寫
`artifacts/short_term_form4_admission_feasibility_validation.json`，其 exact top-level keys 為
`schema_version`, `protocol_sha256`, `protocol_receipt_sha256`, `frozen_at`, `status`,
`fixed_quarters`, `sample_count`, `admission_controls`, `attack_results`, `stop_reasons`,
`state_boundary`, `private_manifest_sha256`。公開 validation 不得包含 accession、CIK、姓名、
issuer、ticker、raw text 或可逆 token；`private_manifest_sha256` 只能是不可逆整體承諾。

本輪 receipt 必須綁定本協議、父 Form 4 v1.1 協議與收據、global trial ledger 協議與目前
artifact、SEC client implementation 與其隔離測試的精確 SHA-256，以及本協議 `FrozenAt`。

## 4. 固定攻擊與停止規則

驗證必須逐一拒收並回傳以下 stable code：

- `form4_feasibility_quarter_set_mismatch`
- `form4_feasibility_zip_member_mismatch`
- `form4_feasibility_header_mismatch`
- `form4_feasibility_form_type_invalid`
- `form4_feasibility_accession_invalid`
- `form4_feasibility_accession_duplicate`
- `form4_feasibility_filing_date_invalid`
- `form4_feasibility_sample_too_small`
- `form4_feasibility_amendment_sample_missing`
- `form4_feasibility_sample_not_deterministic`
- `form4_feasibility_daily_index_missing_or_ambiguous`
- `form4_feasibility_complete_submission_mismatch`
- `form4_feasibility_content_hash_mismatch`
- `form4_feasibility_historical_time_invented`
- `form4_feasibility_amendment_target_unresolved`
- `form4_feasibility_private_boundary_breached`
- `form4_feasibility_result_boundary_breached`
- `form4_feasibility_parent_hash_mismatch`
- `form4_feasibility_global_trial_drift`

任一來源／member／header／accession／日期／index row／完整 submission／hash／receipt／父鏈不符，
任一 4/A target 含糊，任一真實 identifier 外洩，或出現候選、股票代號、績效、Paper、實金
欄位，即整輪 `stopped_no_admission_claim`。停止後不得換季度、換 median、刪除 4/A、補抓較
好樣本、放寬規則或產生 observed-only 結果。

## 5. 不可越界狀態

全域試驗保守下限維持 `6,287`，本輪 trial increment 精確為 `0`；global ledger 不追加亦不
改寫。Form 4 admission 維持 `0/16`，authorized real rows、sample selection、candidate
selection、strategy run、performance result 全為 0／false。Paper 未授權且全現金、不得回填、
持倉 0；real money 未授權、動作 US$0。**今天不下單。**
