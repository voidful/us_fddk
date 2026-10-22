# 美股短線第 43 輪：Form 4 多路徑前瞻准入協議

FrozenAt：`2026-08-10T02:21:51Z`

狀態：**result-blind prospective protocol freeze。** 凍結時 Round43 SEC request 0、前瞻
Form 4／4-A accession 0、候選配置 0、策略運行 0、績效結果 0。本文只預先定義資料准入、
多路徑對賬、首次觀察時鐘及將來唯一 readout；本文件本身不授權網絡擷取、Paper Trading
（模擬交易）或實金落盤。

## 1. Round42 永久保留，不准救援

Round42 `round42-form4-admission-one-shot-v1` 已永久停止：固定 12 份樣本、完成 5 個 HTTP
request 後發生首次 post-fetch 本地驗證失敗、complete-submission request 0、cold replay 未完成，
Form 4 專屬准入為 2/16。其公開狀態必須一直是
`stopped_no_admission_claim`，停止碼一直是
`form4_feasibility_daily_index_missing_or_ambiguous`；候選選擇 0、策略運行 0、績效 0、
Paper 全現金、實金動作 US$0。

只讀 failure audit 顯示，同一 accession 可在同一 daily Form index 對應多於一個自洽的
CIK／archive path。這只推翻「每個 accession 必須精確只有一條 index row」的工程假設，
不改寫 Round42 結果，也不證明任何人物、發行人、股份或交易訊號有效。

Round43 必須使用全新 authorization ID、全新 create-once start receipt、全新 owner-only
quarantine 及全新 append-only ledger。Round42 的 selection plan、raw objects、source receipts、
ledger、failure manifest／seal 或私有 identifier 均不得成為 Round43 輸入，不得重啟、續跑、
補抓、replay、改標為通過或用另一條 path 完成該輪。Round42 的公開檔案及雜湊承諾不得覆寫。

## 2. 唯一研究目的及來源邊界

Round43 只回答：從一個事前封存的將來起點開始，能否在不歷史回填的情況下，完整接收 SEC
Form 4／4-A 分母，把同一 accession 的 1–10 條 index path 作可重播對賬，並用真正的本系統
`first_observed_at` 建立前瞻 known-at，最終讓 Round41 已凍結的候選及八個比較得到一次盲封
readout。

唯一披露來源仍是 SEC Form 4／4-A。Congress PTR、13F、13D、13G、新聞、社交媒體、人物
知名度及第三方「insider signal」不得混入。季度 Insider Transactions Data Sets 只可在後來作
完整性對賬，不可提供或提前任何前瞻 known-at。`P` 仍表示 open market or private purchase，
不可寫成已證實的公開市場買入；「企業家」不是 SEC 法定身份。

本文不改 Round41 的 20 日 cluster、兩個獨立 capital group、US$10,000／US$100,000、量價
確認、十個 10% 槽、10-session 持有、QQQ 空槽、成本、排序、cooldown、修訂鏈或公司行動
規則。多條 archive path 不等於多名 reporting person、多份獨立文件或多注獨立資本。

## 3. 前瞻起點與完整分母

任何網絡前，另行獲授權的 implementation 及 mutation tests 必須已在 remote commit 推送，並
create-once 產生 `forward_start_receipt`，至少綁定：本協議 bytes／SHA-256、父 Round41 v1.0
及 v1.1 bytes／receipts、Round42 stop receipt、implementation／tests bytes、authorization ID、
UTC `monitor_started_at`、quarantine attestation 及全球 trial ledger chain head。任一 binding
漂移即在網絡前停止。

前瞻 cohort 的第一個 session 固定為：`monitor_started_at` 後第一個完整 XNYS 正式交易時段。
其後按 XNYS session 順序單向前進，不得把 start 前的 filing、index、完整 submission、價格、
訊號或配置加入 cohort。系統離線或遲取資料時，只可記錄實際較遲的首次觀察時間；不得把
之後取得的檔案倒填成較早可知，也不得重設起點刪走事故時段。

每個已觀察 SEC daily Form index 內所有 form type 精確為 `4` 或 `4/A` 的列都屬分母。先按
accession 建組，再做 path 對賬；不得按人物、發行人、交易 code、金額、股份、path 數、
complete-submission 可用性或之後回報選擇性收集。每個 index 原始 bytes、HTTP attempt、
request／object receipt、SHA-256、byte count 及完整 row count 必須在 repository 外 owner-only
加密隔離保存，並加入不可回填雜湊鏈。

本協議仍授權 **0 個 request**。未來 collection authorization 必須另行事前凍結精確用途、
User-Agent、單一 collector、全專案不高於 1 request／second、每個 index 及每個 canonical
submission 的一次 request、retry 精確 0、403／429／HTTP／內容／hash 失敗即停止。節省的
request 不得轉作重試、fallback 或額外來源。

## 4. `d0`／`d1` 固定對賬

對每個 accession：

- `d0` 是 index row 的 `Date Filed`；它必須是有效 SEC filing date；
- `d1` 是 SEC directory manifest 中嚴格晚於 `d0` 的第一個已發布 daily Form index 日期；
- `d1-d0` 最多四個日曆日。manifest、`d0` index 及 `d1` index 的完整 bytes 與 receipt 必須
  全部封存；找不到唯一 `d1`、窗口超過四日或 manifest 漂移即停止；
- 只有 `d0` 及 `d1` 兩個 index 可參與該 accession 的對賬。不得查 `d-1`、`d2` 或任何更有利
  日期，也不得用 accepted timestamp、搜尋頁、公司 submissions JSON 或季度 ZIP fallback；
- accession 必須只在 `d0` 或 `d1` 其中一個 index 出現。兩日皆無是 missing，兩日皆有是
  cross-day ambiguous，兩者均拒收；
- 每條命中 row 的 `Date Filed` 必須精確等於 `d0`。daily index filename 日期只表示承載它的
  index 日，可以是 `d0` 或 `d1`，不可反過來改寫 filing date。

必須等待 `d0`／`d1` 兩個 index 均完成讀取、雜湊及 create-once receipt，才可封存該
accession 的 reconciliation；即使它已在 `d0` 出現，也不得在未見 `d1` 前提前產生候選配置。

## 5. 1–10 路徑 equivalence class

在唯一承載 index 內，同一 accession 的所有命中列構成一個 **index-level path equivalence
class**。准入條件精確為：

1. 有 1–10 條 distinct row；0、超過 10 或完全相同 raw row 重複均拒收；
2. 每列 form type 都精確為同一個 `4` 或 `4/A`，`Date Filed` 都等於 `d0`，accession 完全相同；
3. 每列 CIK 必須是 1–10 位十進制數；去除前置零後，必須等於其 file path 內的 CIK；
4. file path 必須精確為 `edgar/data/{normalized_cik}/{accession}.txt`，不得有 query、fragment、
   percent-encoding、traversal、替代 basename、額外 extension 或大小寫漂移；
5. equivalence class 只表示多條 SEC index reference 指向同一 accession；不得由 path 數推論
   actor 數、joint filer 數、獨立資本組數、購買次數或訊號強度。

在看到任何 path 的 HTTP／內容可用性前，canonical path 固定為按
`(CIK 左補零至 10 位, exact path bytes)` 升冪排序的第一條。輸入 row 次序、名稱、locale 或
index 排序改變不得影響選擇。equivalence-class seal 必須先 create-once 保存所有 row commitment、
排序 key、canonical row commitment 及來源 index hash，才可擷取完整 submission。

只准從 canonical index path 取一次完整 as-filed submission。canonical request 失敗、redirect
漂移、content hash／SGML／XML／accession／form／issuer／版本不符即整個 accession 及 Round43
停止；不得改取第二條 path。非 canonical path 不擷取內容，只保存其不可逆 row commitment。
完整 submission 成功不會把多路徑升格成多份文件；每個 accession 在分母及版本鏈仍只計一次。

## 6. 唯一 prospective `known_at`

每個 accession 必須保存三個不可回填 UTC 時間：

```text
index_pair_first_observed_at = d0 與 d1 index 均完整讀取、驗 hash 並封存後的較遲時間
canonical_submission_first_observed_at = canonical complete submission 完整讀取、驗 hash並封存時間
known_at = max(index_pair_first_observed_at,
               canonical_submission_first_observed_at)
known_at_basis = prospective_first_observed
```

`first_observed_at` 只可在 response body 完整讀取及內容雜湊核對後寫入 create-once receipt；
request start、HTTP `Date`、`Last-Modified`、filing date、transaction date、SEC accepted timestamp、
nightly index 起始時間、季度發布日及今天回看歷史檔案的時間均不得替代或提前它。沒有上述
兩個 receipt 就沒有 known-at；不得以估算、午夜、日期尾或 missing-value default 補值。

決策及入場時鐘沿用 Round41，但以這個 prospective known-at 為唯一披露時鐘：

```text
decision_session = close_at(session) 嚴格晚於 known_at 的第一個完整 XNYS session
trade_session    = decision_session 的緊接下一個 XNYS session raw open
```

若 known-at 等於收市 timestamp，該 session 不合資格。遲取資料只會把 decision 向後移，不會
倒填較早配置。每個 4/A 有自己的 first-observed known-at，只由該時點起 append／replace／cancel；
不得回寫原版決策、釋放已使用事件或重啟 cooldown。

## 7. 前瞻配置 ledger 與唯一 readout

在另行 machine authorization 通過所有資料、私隱、multipath、known-at、修訂、去重、PIT 股份池、
行情、公司行動及成交時鐘閘門前，candidate selection 及配置 ledger 仍為 0。獲准後只可按
Round41 `form4_cluster_confirmed_10d` 的原規則建立 **盲封研究配置 ledger**；它不是 Paper
戶口，不計 NAV、回報、勝率、Sharpe、最大回撤或 US$ 金額，亦不公開人物、公司或股份代號。

計數定義固定為：

- `prospective_sessions`：由 cohort 第一個 XNYS session 起按正式日曆累積，不因沒有訊號、
  系統事故或之後補檔而刪除或重設；
- `candidate_allocations`：候選於 D 完成所有當日 cluster、量價、排序及十槽容量判定後，實際
  取得一個 stock slot 並排定下一 session open 入場才計一次；signal、cluster、被容量拒絕者、
  control 配對、非 canonical path 及同一配置的 child order 均不計；
- `distinct_issuers_allocated`：上述 candidate allocations 內永久 issuer ID 的 distinct count；
  同一發行人再次配置會增加 allocation count，但 issuer count 只計一次。

readout 時點固定為 cohort 的第 **504** 個 XNYS session 收市，不能提早或延後。該時點另須
同時達到兩個樣本量下限：

```text
prospective_sessions = 504
candidate_allocations >= 100
distinct_issuers_allocated >= 50
```

第 504 個 session 收市必須先 create-once 封存 `readout_eligibility_receipt`，綁定起點、完整
session／accession／版本／配置雜湊鏈、配置及發行人計數、八比較輸入及當時程式 bytes。
只有兩個樣本量下限亦通過，才可第一次解鎖績效 engine。若配置少於 100 或發行人少於 50，
唯一結果是 `insufficient_power_no_performance_readout`；該 cohort 永久停止，不計績效、不延長
日數、不等下一個 crossing、不重設起點或刪除失敗配置。這避免按訊號密度事後選擇較有利
觀察期。

任一 hard failure 令本 authorization 成為 `stopped_no_readout`。同一 authorization 不得重新
開始；另開 trial 必須另作 result-blind protocol，並完整保留本輪負結果。

## 8. Round41 八個固定比較，不增加績效試驗

將來唯一 readout 精確沿用 Round41 v1.0／v1.1 已預留的八條比較：

1. `qqq_buy_hold`；
2. `spy_buy_hold`；
3. `pit_eligible_equal_weight_monthly`；
4. `form4_cluster_unconfirmed`；
5. `price_volume_only_matched`；
6. `single_actor_purchase_confirmed`；
7. `non_signal_code_confirmed`；
8. `issuer_month_actor_permutation`。

比較的共同日曆、候選／control 建構、十槽、10-session 持有、QQQ 空槽、成本 10／25／50 bps、
US$0.01／US$0.05 child-order 固定費、seed `41202608`、20,000 permutation／bootstrap、
Newey–West lag 10、Holm／max-t、DSR、固定反證及數值門檻全部不變。不得增加第九條比較、
刪除不利 control、改 matched cohort、成本、持有期、統計量或門檻。

Round41 八次 trial 已事前記入 global lower bound；目前保守下限維持 **6,287**。Round43 只修復
前瞻資料准入及預先封存 readout，不新增比較、trial 或績效結果，因此本次 increment 精確為 0，
global ledger 不追加亦不改寫。只有 readout eligibility receipt 完成後，才可一次過產生八比較
的前瞻結果；不得把它描述成 20 年回測，亦不得與 Round42 的 12 份工程樣本拼接。

## 9. 固定停止碼

implementation 必須 fail closed 並至少保留以下 stable code：

- `form4_forward_parent_round42_reuse_forbidden`
- `form4_forward_start_receipt_invalid`
- `form4_forward_historical_backfill_forbidden`
- `form4_forward_denominator_incomplete`
- `form4_forward_d1_window_invalid`
- `form4_forward_cross_day_missing_or_ambiguous`
- `form4_forward_multipath_cardinality_invalid`
- `form4_forward_multipath_duplicate_row`
- `form4_forward_multipath_identity_mismatch`
- `form4_forward_canonical_path_drift`
- `form4_forward_canonical_submission_failed`
- `form4_forward_known_at_invented`
- `form4_forward_decision_clock_invalid`
- `form4_forward_amendment_or_dedupe_invalid`
- `form4_forward_private_boundary_breached`
- `form4_forward_readout_too_early`
- `form4_forward_insufficient_power`
- `form4_forward_comparison_family_drift`
- `form4_forward_paper_boundary_breached`

任何停止後不得 fallback、retry、換 path、擴大日期窗、刪 row、跳 accession、延遲至較有利 D、
改配置計數、延長 504-session horizon 或降低 100／50 門檻。

## 10. 固定 mutation attacks

獨立測試必須最少覆蓋並拒收：Round42 authorization／quarantine／sample reuse；start 前歷史列；
accepted／filed／nightly time 提前 known-at；只讀 d0 不等 d1；同 accession 在 d0 及 d1；兩日
皆無；d1 超過四日或 manifest 換成較有利日期；0 路徑、11 路徑及 exact duplicate row；混合
form／Date Filed／accession；row CIK 與 path CIK 不符；basename、extension、case、query、
percent-encoding 或 traversal 漂移；輸入 row 洗牌令 canonical 改變；canonical fetch 失敗後取
第二 path；把 path count 當 actor／資本組數；4/A 回填；joint／trust／配偶／entity 重複計算；
同日開市入場；漏失 session 或配置後重設 cohort；在 503 sessions 解鎖；第 504 日只有 99
allocations 或 49 issuers 時仍計績效或延長 cohort；control allocation 冒充 candidate allocation；
八比較少一項／多一項；中途計算回報；
Paper 回填、建立持倉或實金越權。

合法 fixture 亦必須證明：1、2 及 10 路徑均可形成 index-level equivalence class；row 次序洗牌
不改 canonical；accession 只在 d0 或只在 d1 時可分別通過；較遲 first observation 只會把
decision／trade 向後移；只有固定第 504 個 session 且 100／50 同時達標才可產生績效 readout。

## 11. 公開、私隱及狀態邊界

未來公開 machine receipt 只可列協議／程式雜湊、session／accession／equivalence-class path-count
分布、准入 gate、停止碼、504／100／50 aggregate progress、readout eligibility 及私有 manifest
整體 SHA-256。不得包含 accession、CIK、姓名、地址、issuer、ticker、raw path、原文、逐筆
金額、候選名單、可逆 token 或配置日期。

本次 freeze 沒有擷取或處理新 SEC 資料，沒有建立候選或配置，也沒有產生任何新績效。Round42
仍為 2/16 且停止；Round43 尚未獲 collection、selection、readout、Paper 或實金授權。Paper
戶口維持全現金、持倉 0、backfilled trade 0；實金動作 US$0。不展示持倉比例或 US$1,000
金額試算，**今天不下單**。

## 官方參考

- SEC Accessing EDGAR Data：
  https://www.sec.gov/search-filings/edgar-search-assistance/accessing-edgar-data
- SEC Insider Transactions Data Sets：
  https://www.sec.gov/data-research/sec-markets-data/insider-transactions-data-sets
- SEC Determine the Status of My Filing：
  https://www.sec.gov/submit-filings/filer-support-resources/how-do-i-guides/determine-status-my-filing
- SEC Login CIK 說明：
  https://www.sec.gov/submit-filings/filer-support-resources/how-do-i-guides/understand-select-set-default-login-cik
- SEC Form 4 instructions：
  https://www.sec.gov/files/form4data%2C0.pdf
- SEC Form 4 joint／group filing final rule：
  https://www.sec.gov/files/rules/final/33-8230.htm
- SEC Ownership XML Technical Specification：
  https://www.sec.gov/info/edgar/ownershipxmltechspec-v3.pdf
