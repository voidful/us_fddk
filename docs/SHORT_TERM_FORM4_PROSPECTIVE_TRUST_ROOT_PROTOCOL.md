# 美股短線第 44 輪：Form 4 前瞻信任根 Phase A 協議

FrozenAt：`2026-08-10T05:14:47Z`

狀態：**result-blind pre-data protocol freeze。** 本輪只凍結真實 SEC 前瞻監察在任何網絡
request 前必須通過的信任根、remote exact-head gate、時間及隔離邊界。凍結時新增 SEC request、
真實 filing、真實識別資料、候選、配置、策略運行及績效全部為 0；Paper Trading（模擬交易）
維持全現金、持倉 0、不可回填，實金動作 US$0。**今天不下單。**

本文件不是 collection authorization、monitor-start receipt、real evidence admission、回測、
Paper 或交易指令。Phase A 永遠不能自行啟動 SEC 網絡；只有本協議的 exact commit 推送後，
read-only Form 4 Round44 pre-data CI 在該 exact head 成功，才可由下一個獨立、result-blind
phase 建立 repository 外的 create-once monitor start。該下一階段仍須先補 official manifest collector、
durable hash chain、外部時間錨、實際戶口零狀態及 production-only transport，才可考慮第一個 request。

## 1. 為何先做 Phase A

Round42 的一次性 admission collection 已永久停在 `2/16`、
`stopped_no_admission_claim`；不得重啟、續跑、補抓、replay、換 path 或沿用其 private cache。
Round43 v1.1 又證明目前 executable contract 只可處理 synthetic fixture，caller 提供的 hash、body
及時間不是外部信任根。因此，直接下載新 filing 會令「事前凍結」變成看過資料後才補寫。

Phase A 只解決以下問題：

1. 精確綁定 Round41–43、全域 trial ledger、legacy SEC client、`pyproject.toml`、`uv.lock`、
   協議、tests、舊 frozen workflow 及全新 read-only Round44 workflow bytes；
2. 把 GitHub Actions 由 synthetic merge ref 改成明確 checkout PR head SHA，並在 runner 內逐字比對；
3. 保留舊 `SecEdgarClient` 的 frozen bytes，但把它明確隔離為 engineering prototype，Round44
   不可 import、包裝或呼叫其 default opener；Phase A 本身沒有任何可到達 socket 的 transport；
4. 固定官方來源、現行 Ownership XML 版本、request policy、可信時間及公開輸出邊界；
5. 明確列出仍然未完成、不能被單元測試或 CI 冒充的真實信任證據。

## 2. 官方來源與不可過度解讀的欄位

只接受 SEC 官方一般技術文件作 Phase A 規格來源：

- `https://www.sec.gov/search-filings/edgar-search-assistance/accessing-edgar-data`
- `https://www.sec.gov/about/developer-resources`
- `https://www.sec.gov/submit-filings/technical-specifications`
- `https://www.sec.gov/about/webmaster-frequently-asked-questions`
- `https://www.sec.gov/about/privacy-information`

截至本協議凍結日，Ownership Forms 3／4／5 的現行 technical specification 是 Version 5.5，
日期 2026-03-18。日後版本改變必須另作事前 migration，不能靜默接受新 schema。

SEC 公開規格可證 daily／full index、complete disseminated filing content、alternative symbolic
archive path、PAC／刪除及最大 10 requests/second 公平存取上限；但不提供 public archive 內容的
官方 SHA-256／簽章，亦沒有 filing content 首次可在 sec.gov 取得的官方 timestamp。因此：

- accession 只是一個 EDGAR submission identifier，本身不證已接受或已公開；
- `ACCEPTANCE-DATETIME` 是 EDGAR 接受時間，不是網站首次完整可得時間；
- filing date、交易日期、index filename 日期及 nightly build 時間都不是本系統 `known_at`；
- HTTP `Date`、`ETag`、`Last-Modified`、`Age`、`Content-Length` 或 status 200 不能單獨成為信任根；
- 本地 SHA-256 只證保存後 bytes 沒變，不證資料何時首次被看見；
- March 2025 PDS 文件標示 DRAFT，只可作欄位語意佐證，不是 final public archive contract；
- ticker／CIK mapping 的準確度及範圍沒有 SEC 保證，不能直接變成 PIT 證券身份。

10 requests/second 是 SEC 公開上限，不是本專案操作目標。未來本專案仍只准一台指定 collector、
全專案不高於 1 request/second、自動 retry 精確為 0；403、429、transport、TLS、HTTP、內容、
EOF、hash 或 schema 失敗一律永久停止當次 authorization，不 backoff 重試、不 fallback、不把
省下的 request 移作另一來源。

## 3. 精確來源及時鐘契約

Round43 的 prospective denominator 只可從 SEC daily Form index 的完整 bytes 建立。未來 collector
必須先從官方 quarterly daily-index directory 的 `index.json`／等價 manifest 讀出 SEC 當下列出的
精確 filename，再讀完整 Form index；不得由 caller 傳入 published-date list 或猜一個較有利日期。

每個 accession 的 canonical complete submission URL 只可由已封存的 exact index row 導出：

```text
https://www.sec.gov/Archives/edgar/data/{normalized_archive_cik}/
{accession_without_dashes}/{accession_with_dashes}.txt
```

archive path 的 CIK 可以是提交者或 filing agent，不是 reporting person 或 issuer identity。完整
submission 仍須以 SGML header、`DOCUMENT/TYPE/FILENAME` 及 Ownership XML 的 `documentType`、
issuer、reporting owner 逐層交叉核對；不得猜 primary XML filename。1–10 個 path 是 Round43
project safety cap，不是 SEC 官方 filing 或人物上限。

未來 local operational receipt 必須分開保存：

```text
local_request_started_at
local_full_body_completed_at
independent_anchor_received_at
trusted_data_known_at = independent_anchor_received_at
```

`independent_anchor_received_at` 必須是第一個在完整 body、object、authorization、monitor start、
attempt chain 及 first-seen registry chain heads 全部封存後，從固定外部機制取得並密碼學綁定該
組合 hash 的時間；所以它必然不早於完整 body。普通 `_utc_now()`、caller dict、Git commit author
date 或本地檔案 mtime 均不是獨立時間根。這是 Round44 canary 的保守時鐘，不回寫 Round43 歷史。

`d0`／`d1` reconciliation、later index、PAC 或重抓只能追加 audit event，永遠不能把
`trusted_data_known_at` 改早或改晚。未完成外部錨定的 body 只能是隔離的 transport object，不能
成為 admission row。

## 4. Remote exact-head gate

Phase A machine receipt 因自我參照不可能內含自己的 commit SHA；它只綁定上一個已驗證 parent
commit `d42b444651a3ccde0f26882c803b58f0daf386a2` 及本次所有有效 bytes。下一階段 launch
verifier 必須從 committed blob 推導 `authorization_commit = HEAD`，並同時證明：

1. 本地 receipt 及每個 binding 是該 HEAD 的 exact Git blob，不是 untracked／modified bytes；
2. repository worktree 乾淨，`pyproject.toml` 及 `uv.lock` 精確綁定；workflow 固定
   `ubuntu-24.04`、Python 3.12.12、禁止 uv 下載另一個 Python，所有 actions 使用完整 commit SHA；
3. 同一 repository 的 remote branch head 精確等於 authorization commit，不接受 ancestor；
4. `Form 4 Round44 pre-data CI`／`.github/workflows/form4-round44-predata-ci.yml` 的
   `predata` job 由 GitHub Actions app 執行，check 的 head SHA 精確相同、completed 且
   conclusion 為 success；
5. 只接受同一 repository 的 PR event；workflow 必須 checkout
   `github.event.pull_request.head.sha` 並在 runner 內驗 HEAD，不能用 `refs/pull/.../merge`；
   Phase A 不接受 workflow_dispatch，日後若需要 manual launch 必須另建新協議及 exact-ref verifier；
6. Pages 及 Daily workflow 因具部署／寫入權限，永遠不能作 collection authorization proof。

PR check 完成後，下一階段 launch verifier 仍須重新查 remote branch 的**當前** head；舊的成功 run
在 force-push 後立即失效。checkout 設 `persist-credentials=false`，CI 只可做 protocol/test replay；
它不獲准執行 SEC collector、monitor start、真實 identifier input 或任何部署。套件安裝需要一般
依賴網絡不等於 SEC collection，亦不能被記作本輪 SEC request。machine receipt 因此只記錄
`ci_sec_collection_authorized=false` 及 `current_exact_suite_sec_request_count=0`；它不宣稱 hosted
runner 在技術上完全沒有一般網絡能力。

本 receipt 內 `remote_gate_passed_in_this_receipt=false`。CI 成功只表示 Phase A bytes 可重播，
不會在 Actions、Pages 或網站建立 monitor start、發 SEC request、讀真實 identifier 或 mint capability。

## 5. 下一階段 create-once start 的最低條件

下一階段必須另寫全新協議、schema、implementation、mutation tests 及 machine receipt，且在首個
SEC request 前完成以下全部條件：

- repository 外絕對實體路徑，exact encrypted volume UUID／encryption state，owner-only `0700`；
- start、ledger、object、receipt、registry 全為 owner-only `0600` regular file、link count 1；
- `O_EXCL|O_NOFOLLOW` create-once，fsync file 及 parent directory；並發只有一個 winner；
- 同一 authorization 重入只可驗證並原樣返回 byte-identical existing start，不更新 timestamp；
- fresh Round44 namespace 必須為空；拒絕 Round42 quarantine、cache、receipt、selection 或 manifest；
- 固定 production transport，不准 injected opener／now／clock／sleeper、proxy、第二 collector 或第二主機；
- declared User-Agent contact 的 digest、全域 exclusive lock、最大 1 rps、retry／fallback 0；
- attempt chain 在 socket 前先 append URL commitment、ordinal、時間、prev hash，並 durable fsync；
- content-addressed raw entity-body object、完整 EOF、byte count、raw headers、redirect chain 及 receipt；
- fresh content-hash first-seen registry、previous chain head、外部時間錨及 cold replay；
- official published-date manifest parser，不能接受 caller supplied date list；
- 實際短線 Paper、broker／real ledger 及 account 全零的 repository-external receipt；
- Congress request／row／field 精確 0，任何 nested/null/alias 注入在 socket 前停止。

舊 `SecEdgarClient` 的 receipt 明示 `known_at=null`、external anchor／attempt ledger／加密／
admission 均為 false；它只作歷史 engineering evidence，不能翻 boolean、包裝成 capability 或
成為 Round44 production transport。在 official manifest collector、durable chain、全新 production
transport、外部錨及 account receipt 尚未
實作及驗證前，`prospective_collector_implemented=false`、
`real_evidence_admission_authorized=false`，不得建立 live capability。

## 6. Phase A stable codes

Phase A 及下一階段保留單一語義 error codes：

- `form4_round44_authorization_invalid`
- `form4_round44_remote_gate_invalid`
- `form4_round44_start_receipt_invalid`
- `form4_round44_private_boundary_invalid`
- `form4_round44_request_plan_drifted`
- `form4_round44_already_started`
- `form4_round44_attempt_ledger_invalid`
- `form4_round44_external_anchor_invalid`
- `form4_round44_response_incomplete`
- `form4_round44_cold_replay_required`
- `form4_round44_public_boundary_breached`
- `sec_live_network_authorization_missing`

Round43 同義邊界維持：Congress injection 只能回
`form4_forward_congress_field_injection`；candidate、allocation、performance、Paper 或實金越界
只能回 `form4_forward_non_engineering_action_forbidden`。不得因 wording 不同發出第二個 code。

## 7. Mutation closure

Phase A tests 必須至少證明：

1. receipt extra／missing key、bool 冒充 0、NaN、自身 hash、binding path／hash、parent drift 全失敗；
2. 真實 accession-like value 或公開 identifier field 無法進 machine receipt；
3. 任一 SEC／filing／candidate／allocation／strategy／performance／Paper／real／Congress 非零失敗；
4. Round44 Phase A 唯一入口在 capability 缺失時 socket attempt 為 0，且 module 不 import／呼叫
   舊 `SecEdgarClient`；舊 default opener 明確不屬 Round44 authorization surface；
5. 舊 custom synthetic opener 只可保留既有 offline fixture tests，不構成 production capability；
6. CI workflow 明確 checkout 及 assert exact PR head，且只具 `contents: read`；
7. Pages／Daily 不可成為 Phase A remote proof；
8. Round42 authorization／private state 不可被 Phase A validator 或 network lock 復活。

下一階段還必須補 remote/check mutation、private path／mode／link／race、transport、redirect、
403／429、premature EOF、crash points、ledger truncation／reorder、manifest／d0／d1、SGML／XML、
external anchor、cold replay 及公開 sanitizer attacks。沒有這些 tests，不得降低 receipt 的 false 狀態。

## 8. 現時決策邊界

| 狀態 | 現值 |
|---|---:|
| Phase A protocol freeze | 已建立；待 exact-head remote gate |
| Monitor-start receipt | 0／未建立 |
| Live SEC capability | 0／未發出 |
| 本輪新增 SEC request | 0 |
| 真實 filing／identifier | 0／0 |
| Official manifest／real admission | 未實作／未授權 |
| Congress PTR | 停用；request／row／field 皆 0 |
| 候選／配置／策略／績效 | 0／0／0／0 |
| Paper Trading（模擬交易） | 全現金；持倉 0；不可回填 |
| 實金動作 | US$0 |
| 今日動作 | **今天不下單** |

本協議只建立日後誠實收集的前置閘門。它不提供人物榜、股票代號、持倉比例、US$1,000 金額
試算、回報保證或落盤指示，亦不構成投資或法律建議。
