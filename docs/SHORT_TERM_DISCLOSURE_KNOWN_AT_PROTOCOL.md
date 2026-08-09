# 短線個股公開披露 known-at 準備度協議 v1.0

凍結時間：2026-08-09T16:32:24Z（2026-08-10 亞洲／台北）

狀態：`frozen_after_official_documentation_review_before_any_disclosure_data_fetch_or_strategy_design`

## 結論先行

本輪只建立「某項公開披露在當時是否已真正可知」的數據準備度契約，**不是交易策略、
人物排行榜、選股名單、回測或 Paper 訊號**。在二十項準備度閘門全部通過前：

- 不以美國議員、公司內幕人士、實益擁有人或機構經理的披露動向動態選股；
- 不把 `transaction date`、`filed date` 或 SEC `accepted` 時間冒充公眾已可取得時間；
- 不顯示人物、股份代號、個別文件或「最新買入」；
- 正式回測未獲授權、策略未定義且運行次數為 0；
- 短線 Paper 維持全現金、持倉 0、不可回填；
- 實金動作為 **US$0**，狀態固定為 **今天不下單**。

「企業家」不是 SEC 申報身分。本協議只使用法規所定的 `director`、`officer`、
`10-percent owner`、Schedule 13D／13G 實益擁有人及 Form 13F 機構投資經理等可驗證角色；
不得因知名度、創辦人敘事或媒體稱呼自行加上「企業家高勝率」標籤。

## 固定來源與正確語義

來源類型固定為六個，不得在看到結果後增刪或合併：

| `source_type` | 官方入口／說明 | 可知內容 | 不可推論 |
|---|---|---|---|
| `congress_house_ptr` | [House Clerk Financial Disclosure](https://disclosures-clerk.house.gov/FinancialDisclosure)、[House PTR 到期日說明](https://ethics.house.gov/periodic-transaction-report-calculator/) | House 議員、主管及部分僱員的 Periodic Transaction Report；某些超過 US$1,000 的買入、賣出或交換須在知悉後 30 日內且最遲交易後 45 日申報 | 不是即時成交帶；金額通常是區間；申報可屬配偶或受扶養人；不能推定精確數量、價格、當刻持倉或由議員親自下單 |
| `congress_senate_ptr` | [Senate eFD Search](https://efdsearch.senate.gov/search/home/)、[Senate Financial Disclosure](https://www.ethics.senate.gov/public/index.cfm/financialdisclosure) | Senate PTR 的申報類型、交易日期／範圍及公開文件 | 與 House 相同，法定最遲期限不是實際公開時間，亦不是無延遲交易訊號 |
| `sec_form_4` | [SEC Form 4](https://www.sec.gov/files/form4.pdf)、[SEC Ownership Form Codes](https://www.sec.gov/edgar/searchedgar/ownershipformcodes.html) | Section 16 的董事、高級人員及逾 10% 股東持股變動；一般須在交易後兩個工作日申報 | 只有交易 code、A／D、直接／間接持有及註腳可辨別經濟語義；獎勵、期權行使、稅項扣股、贈與或轉移不可當作公開市場買賣；`P`／`S` 亦須保留註腳及修訂狀態 |
| `sec_schedule_13d` | [SEC 13D／13G filing guide](https://www.sec.gov/submit-filings/filer-support-resources/how-do-i-guides/file-schedule-13d-schedule-13-g-corresponding-amendments)、[SEC 2023 final rule](https://www.sec.gov/files/rules/final/2023/33-11253.pdf) | 一般是超過某類別 5% 的實益擁有權申報，13D 關乎控制意圖；現行初次申報期限一般為觸發後五個工作日，修訂期限另計 | 是披露時點的實益擁有權／意圖快照，不是逐筆成交、精確建倉日期或建倉成本 |
| `sec_schedule_13g` | 同上 | 合資格機構、被動或豁免實益擁有人按其類別及門檻申報；期限因申報人類型及事件而異 | 不得套用單一延遲、假定被動等於看好，或把 amendment 差額直接當買賣 |
| `sec_form_13f` | [SEC Form 13F](https://www.sec.gov/files/form13f.pdf)、[SEC Form 13F FAQ](https://www.sec.gov/rules-regulations/staff-guidance/division-investment-management-frequently-asked-questions/frequently-asked-questions-about-form-13f) | 一般是達 US$100m 門檻的機構投資經理季度末 Section 13(f) 證券持倉；申報一般在季末後 45 日內 | 是滯後季度持倉快照，不是企業家交易、不提供交易日或成交價；兩季差額可來自買賣、公司行動、估值、遺漏或修訂；保密處理可令公開覆蓋不完整 |

SEC EDGAR 的 `acceptance-datetime` 是系統接受申報的時間，不保證文件在同一瞬間已向公眾
發布。[SEC Webmaster FAQ](https://www.sec.gov/about/webmaster-frequently-asked-questions) 指出
公開文件常在接受後一至三分鐘才可用，因此歷史資料若沒有可驗證
的 `public_at` 或獨立 archived first-seen，只能以本系統的 `first_observed_at` 作保守
`known_at`，不得自行加一個固定分鐘數回推。

## 國會披露的法律／商業用途硬閘門

[5 U.S.C. § 13107](https://uscode.house.gov/view.xhtml?edition=prelim&num=0&req=granuleid%3AUSC-prelim-title5-section13107)、
[House Ethics Manual](https://ethics.house.gov/manual/retention-of-and-public-access-to-reports/) 及
[Senate Financial Disclosure guidance](https://www.ethics.senate.gov/public/index.cfm/financialdisclosure)
均列明，取得或使用財務披露報告作商業用途（新聞及通訊媒體向公眾發布除外）等用途受
禁止或限制。本專案不自行判斷「個人投資參考」、「網站」、「Paper」或未來收費功能是否
落入例外。

`congress_house_ptr` 及 `congress_senate_ptr` 只有在以下文件全部存在時才可收集一列：

1. 由合資格法律顧問或有權機構就**本專案精確用途**作出的書面准許判定；
2. House／Senate 當時網站條款、存取聲明及自動化規則的帶時間 SHA-256 快照；
3. 准許的使用、保存、再分發、公開展示及商業用途範圍；
4. 專案擁有人簽署的用途聲明及覆核到期日。

任何文件缺失、過期、範圍模糊或只屬一般網上意見，`legal_use_approved=false`，入口必須
失敗關閉。公開可看不等於可作任何用途。這是合規閘門，不是法律意見。

## SEC 自動存取契約

SEC 來源只可按 [Accessing EDGAR Data](https://www.sec.gov/search-filings/edgar-search-assistance/accessing-edgar-data)
及 [Developer Resources](https://www.sec.gov/about/developer-resources) 存取：

- 每個 HTTP request 必須帶可聯絡的 `User-Agent`（產品／版本及管理員聯絡地址）；
- 所有機器、程序及並行 worker 合計最多 **10 requests/second**；本專案預設上限須更低，
  並使用全域 limiter、快取、指數／feed 優先、429 指數退避及停止開關；
- 不用輪換 IP、代理或多機繞過總上限；不把 `robots`、條款或 403／429 當成可忽略錯誤；
- request URL、UTC 擷取時間、HTTP status、關鍵 response headers、byte count 及 payload
  SHA-256 必須在私有來源收據中保留；
- API 或網站規則日後有變時，舊准許不自動延續，須重新覆核。

## 八個時間欄與 known-at 防火牆

每個正規化事件必須有以下八個 key；源頭沒有精確值時保留 `null` 及原因，禁止推算為午夜、
季末收市或法定到期日：

| 欄位 | 定義 |
|---|---|
| `event_at` | 源頭明示的交易日、觸發日或報告期末；須另有 `event_precision`，不得冒充公開時間 |
| `filed_at` | 申報人提交／申報日期時間；只有官方欄位才可填 |
| `accepted_at` | 接收系統接受時間；SEC 可來自 EDGAR header，Congress 無可靠值時為 `null` |
| `public_at` | 文件確實向一般公眾可取得的最早可驗證時間及證據；due date、filed 或 accepted 不可代替 |
| `first_observed_at` | 本系統第一次成功取得相同 content hash 的 UTC 時間；不可在重跑時改早 |
| `known_at` | 研究可使用時間，由下列固定規則決定 |
| `decision_at` | `known_at` 後第一個合資格 XNYS 正式收市；只作日後重播時鐘，不是本輪訊號 |
| `trade_at` | `decision_at` 後下一個 XNYS 正式開市；本輪不產生訂單 |

`known_at` 固定規則：

1. 有官方可驗證 `public_at` 且內容 hash 可綁定時，`known_at=public_at`；
2. 沒有官方公開時間但有獨立、不可回填的 archived first-seen 證據時，
   `known_at=independent_archived_first_seen_at`；
3. 以上皆沒有時，`known_at=first_observed_at`；
4. `known_at_basis` 只接受 `official_public_timestamp`、
   `independent_archived_first_seen`、`local_first_observed_fallback`；
5. `transaction/event_at`、法定 deadline、`filed_at`、`accepted_at`、EDGAR nightly index 日期、
   搜尋結果排名或第三方「估計公開時間」均不可單獨決定 `known_at`；
6. 任何 amendment／late filing 的新內容只可由其自己的 `known_at` 起使用，不得回寫原版。

研究延遲固定定義為 `known_at - event_at`，只在 `event_at` 及 `known_at` 都有可靠精度時
計算；否則標記 `lag_unresolved`，不以 0 或中位數補值。

## XNYS 訊號／成交時鐘

- 日曆只接受可重播的官方 `XNYS` session，包括假期及提早收市；
- `decision_at` 是 **嚴格晚於** `known_at` 的第一個 XNYS 正式收市；在收市同一 timestamp
  才公開的資料留至下一個 session；
- 截至 `decision_at` 的版本快照在收市後建立並雜湊；日後若另有策略，只可由該快照計算；
- `trade_at` 是 `decision_at` 後下一個 XNYS 正式開市；不得同日收市成交、日曆日加一、
  用調整收市價代替開市價，或把休市日向前填補；
- 今輪 `decision_at`／`trade_at` 只驗證時鐘欄位，`strategy_defined=false`，訂單數固定為 0。

## 版本、修訂及不可回填雜湊鏈

每次第一次見到一份文件或 amendment 都建立獨立 `version_id`，至少保存：
`source_type`、穩定 `source_document_id`、`source_version_id`、`supersedes_version_id`、
`request_receipt_sha256`、`content_sha256`、`first_observed_at`、`public_at` 證據及 record count。

- 原版永不覆寫；修訂只能 append，且 `supersedes_version_id` 必須存在並形成無環鏈；
- 每個 chain row 記錄 `previous_chain_sha256`，genesis 使用 64 個 `0`，chain hash 由 canonical
  UTF-8 JSON 計算；
- 同一來源文件 ID＋版本只能對應一個 content hash；hash 改變但沒有新版本／修訂證據即隔離；
- 每次重跑不得更早設定 `first_observed_at`、`public_at` 或 `known_at`；
- 「final revised」資料只准作事後品質稽核，不得代換 as-known 回測輸入；
- 刪除、無聲改名、缺頁、late filing、confidential treatment release 及取消申報都須成為新鏈項。

## 私隱、隔離及公開清洗

本協議凍結時**沒有擷取或保存任何原始披露、人物資料或個人資料**。日後即使法律閘門
通過，raw response、PDF／HTML／XML、人物姓名、住址、簽名、配偶／受扶養人身分、私人
聯絡資料及逐文件 ledger 只可留在加密、本地、權限最小化的私有 quarantine；不得加入：

- Git commit／Git LFS；
- GitHub Actions cache 或 artifact；
- Sites／GitHub Pages 的 source、bundle 或 source map；
- 測試 fixture、錯誤訊息、截圖、日誌或分析 telemetry。

內部正規化只用帶專案 salt 的不可逆 `actor_token`；salt 不入 Git。公開 sanitizer 只可輸出
來源家族層面的準備度、延遲分布、缺失率、修訂率、合規狀態及聚合統計。Phase 1 禁止輸出
人物、角色可識別組合、股份代號、CUSIP、CIK、accession、文件 URL、原始列、精確小群組、
最新標的或逐文件買賣。低於固定最小群組數的統計須抑制，公開輸出必須通過 forbidden-key
掃描及人工覆核；固定最小群組為 **10 個不同 `actor_token`**，不能以同一人多份文件湊數。

## 覆蓋與「20 年」聲明

六個來源的電子化起點、公開介面、申報人範圍、保留期、修訂、late filing、保密處理及
結構化格式並不相同。SEC EDGAR 很早已有申報，不等於每個來源、每個時間欄、每種角色及
每個證券都有二十年完整 point-in-time 覆蓋；Congress PTR 本身亦由 STOCK Act 後才出現。

任何樣本只能聲明實際觀察到的 `min(event_at)`、`min(known_at)`、`max(known_at)`、來源別
應有／實有文件數、缺失率及可驗證公開時間比例。只有逐來源、逐年份、逐 filing universe
完成分母對數，late／amended／confidential／removed document 亦可重播，才可聲明該固定
區間完整。Phase 1 固定：

- `twenty_year_coverage_claimed=false`；
- `twenty_year_coverage_validated=false`；
- 不把 2006–2026 市價覆蓋轉譯為披露數據覆蓋；
- 不用現存文件倒填「當時已可知」；
- 覆蓋不足時縮短研究期只能在新的事前協議中進行，不能看完績效才改。

## 固定輸入 schema

日後的 Phase 1 admission manifest 必須符合
`schemas/short_term_disclosure_point_in_time_manifest.schema.json`。Schema 是封閉的
Draft 2020-12 契約，要求：六個來源收據、合法用途證明、SEC 存取政策、八個時間欄語義、
XNYS 時鐘、append-only SHA-256 鏈、五個精確檔案收據、覆蓋非宣稱及公開清洗邊界。

Schema 通過只代表「包的聲明格式完整」，不代表聲明真實。檔案 hash／row count、官方
來源身份、法律文件、公開時間證據、時序、鏈及 sanitizer 必須另行對數。Raw 文件不屬於
可提交的五檔集合，只能以私有 request/content receipt 綁定。

## 二十項準備度閘門

固定共 20 項，必須 20/20；Phase 1 凍結時只通過 01–02，即 **2/20**：

| ID | 閘門 | 通過條件 | 凍結時 |
|---|---|---|---|
| 01 | `protocol_schema_receipt_integrity` | 協議、schema、收據路徑及 SHA-256 一致 | 通過 |
| 02 | `official_source_semantics_pinned` | 六類來源、官方 URL 及不可推論事項已固定 | 通過 |
| 03 | `congress_exact_use_legal_clearance` | House／Senate 精確用途有仍有效的書面准許 | 未通過 |
| 04 | `source_terms_and_automation_clearance` | 六來源條款、robots/API、保存及再發布逐一批准 | 未通過 |
| 05 | `sec_fair_access_client_verified` | 可聯絡 User-Agent、全域 ≤10 rps、快取／429／停止控制有測試 | 未通過 |
| 06 | `private_quarantine_verified` | raw 與人物資料不進 Git／CI／網站，權限及刪除流程實測 | 未通過 |
| 07 | `closed_manifest_admitted` | 真實 manifest 經封閉 schema、精確檔案集合及語義檢查 | 未通過 |
| 08 | `source_request_receipts_complete` | 每次 request 的 URL、時間、status、headers、bytes、hash 可對數 | 未通過 |
| 09 | `stable_document_version_ids` | 文件／版本 ID 唯一，amendment／late filing 可追溯 | 未通過 |
| 10 | `eight_timestamps_complete_or_reasoned` | 八 key 齊全；null 均有源頭原因且無人造時間 | 未通過 |
| 11 | `public_at_evidence_verified` | public_at 有官方或獨立不可回填證據，不用 filed/accepted 代替 | 未通過 |
| 12 | `known_at_derivation_verified` | 每列 known_at 及 basis 符合三層固定規則 | 未通過 |
| 13 | `append_only_revision_chain_verified` | 原版、修訂、刪除及 hash chain 完整、無環、不可回填 | 未通過 |
| 14 | `point_in_time_security_mapping_verified` | 當時 ticker／CUSIP／CIK 映射可重播，歧義失敗關閉 | 未通過 |
| 15 | `source_specific_semantics_verified` | PTR 範圍／owner、Form 4 code、13D/G 類型、13F 期末語義全保留 | 未通過 |
| 16 | `xnys_decision_entry_clock_verified` | known 後首個收市／再下一開市、假期／early close 攻擊全拒收 | 未通過 |
| 17 | `coverage_lag_missingness_audited` | 逐來源／年份有分母、延遲、late、amendment、保密及缺失報表 | 未通過 |
| 18 | `public_sanitizer_verified` | forbidden-key、最小群組、bundle/source-map 及人工覆核全通過 | 未通過 |
| 19 | `independent_synthetic_attacks_passed` | 單一錯誤攻擊命中精確拒收碼，沒有 generic hash 掩蓋 | 未通過 |
| 20 | `authorized_real_sample_accepted` | 合法真實小樣本逐列重播並由獨立覆核者接受 | 未通過 |

任一閘門失敗時，狀態固定為 `blocked_by_disclosure_known_at_readiness`。不得以「公開資料」、
網站可下載、第三方 API、較短樣本、人工看過 PDF、accepted 時間或事後修訂資料繞過。

## 通過 20/20 後仍不自動成為策略

20/20 只准另開一份事前凍結的研究協議，定義 actor universe、來源權重、Form 4 code、
PTR amount range、13D/G 意圖、13F lag、聚合、持有期、成本、baseline、negative control、
multiple-testing family 及停止規則。不得用 Phase 1 的資料結果挑規則。

該研究仍須與 QQQ、SPY、同股／同業及延遲匹配 baseline 作公平比較，顯示交易成本、滑價、
擁擠、容量、披露延遲、修訂、缺失、危機段及多重測試懲罰。只有另行正式回測全部通過，
才可由全現金開始不可回填的 Paper；Paper 通過亦不等於實金授權或盈利保證。

## 凍結收據

本協議及封閉 schema 的 SHA-256 固定記錄於
`artifacts/short_term_disclosure_known_at_protocol_receipt.json`。收據明示凍結時沒有擷取
原始披露、沒有個人資料、沒有正規化列、沒有策略、沒有回測、沒有 Paper 成交及沒有實金
動作。任何後續修改須升 schema／協議版本並建立新收據，不得覆寫 v1.0 歷史。
