# 美股短線第 45 輪：Form 4 前瞻監察起點協議

FrozenAt：`2026-08-10T08:14:58Z`

狀態：**result-blind monitor-start authorization freeze。** 本輪只授權在所有 GitHub exact-head、
私有儲存、零戶口及 RFC 3161 外部時間錨均通過後，建立一次不可回填的 Form 4 監察起點。
它不授權 SEC request、真實申報收集、候選、配置、績效、Paper Trading（模擬交易）或實金落盤。
本輪凍結時以上計數全部為 0；專用 Paper／real namespace 未注資、無持倉、無指令、無成交，
Congress request／row／field 亦全為 0。**今天不下單。**

## 1. 目的及父證據

Round44 commit `f599816da099dff75a8a4a60ad21d07ecacb0359` 已推送至同名 remote branch；
PR #8 的 `Form 4 Round44 pre-data CI` run `31358886821`／job `93363646562` 在該 exact SHA
由 GitHub Actions app `15368`（slug `github-actions`）完成且成功。Round45 必須在此父證據之上
新增自己的 protocol、authorization receipt、module、tests、TSA CA、workflow、`pyproject.toml`
及 `uv.lock` exact-byte bindings。authorization receipt本身及每個 binding亦必須是 current `HEAD`
內 mode `100644` 的 regular Git blob；只存在本機、被 `.gitignore` 隱藏或只驗 working-tree hash均無效。
start intent同時綁定 authorization receipt 的 canonical hash及 exact raw-file SHA-256，空白改動亦失敗。

Round44 check 只覆蓋 Round44 bytes，不能批准新程式。Round45 必須另有同 repository 的 draft PR，
由 `pull_request` event 執行 `Form 4 Round45 monitor-start CI`，checkout
`github.event.pull_request.head.sha`，其 `monitor-start` job 在 current authorization commit 上成功。
launch 當刻必須重新讀取 remote current branch head；ancestor、merge ref、舊 run、Pages、Daily、
workflow dispatch、fork PR、非 GitHub Actions check 或 caller 自報 JSON 一律不接受。
branch ref 只可由固定 `github.com` 的 GitHub API 讀取，不可信任 local Git URL rewrite 作 remote
證據；`gh` subprocess只保留 OS account HOME、locale及 GitHub token白名單，caller proxy、custom CA、
GH host／repo／config override一律不繼承。
current run候選全集只能來自固定 Round45 workflow identity endpoint 的**全部連續分頁**；query只可有
`per_page=100`及`page=N`，不得加入 branch／event／status／conclusion／name／path篩選。client收齊並
核對穩定 `total_count` 後，才按 exact head篩選並選最高 `(run id, run_attempt)`；其後先 GET該 exact
run，再驗 name／path／event／head branch／status／conclusion及list與exact response逐欄一致。
較新的metadata drift／queued／in-progress／cancelled／failed重跑一律阻擋，不能退回沿用較舊
success；其他同SHA workflow不屬固定Round45 workflow endpoint，亦不能擴張或縮窄此候選全集。
proof須同時保存current／parent normalized ref、SHA、object type及依頁有序的exact raw-response hash，
不能只保存caller branch字串。

## 2. 權限邊界

Round45 authorization 只可把 `monitor_start_creation` 設為 true；即使私有 start receipt 完成，
狀態仍固定為 `monitor_started_collection_locked`：

```text
sec_network_collection = false
prospective_collector_implemented = false
sec_collection_capability_issued = false
candidate_selection = false
candidate_allocation = false
strategy_run = false
performance_readout = false
paper = false
real_money = false
congress_collection = false
```

任何 SEC socket、官方 manifest 下載或 filing request 仍以
`sec_live_network_authorization_missing` 在 socket 前停止。Round42／43 client、cache、quarantine、
receipt、selection、opener、clock 或 caller-supplied body 不得 import、包裝、續跑或作輸入。

## 3. Create-once 私有儲存

start 只可建立於 repository 外、全新的 direct child namespace。direct parent、root、authorization
namespace 及 objects directory 必須是實際 directory、非 symlink、current uid 擁有、mode `0700`；
所有檔案必須是 current uid、mode `0600`、link count 1 的 regular file。root 的 canonical path、
device、inode、volume UUID 及完整 path 只可留在私有收據；Git、CI及網站只可出不可逆 hash。

private writer 必須使用 parent dir fd、`O_EXCL|O_NOFOLLOW`，完整 write loop 後依序
`fchmod(0600)`、`fstat`、`fsync(file)`、close、`fsync(parent directory)`。不得先 exists 再普通寫，
不得以 tempfile overwrite，亦不得在錯誤時 unlink。global owner-only lock 使用 `fcntl.LOCK_EX`；
同 authorization 的完整重入只可逐 byte 驗證並返回既有 receipt，不能更新 mtime、時間或 chain；
任何 partial state 永久 `STOPPED_PARTIAL`，不得刪除、修補、retry 或改 authorization 救援。

現機器資料卷必須由 `df` 找到 exact backing device，再用 `/usr/sbin/diskutil info -plist` 驗證
`FileVault=true`、`Encryption=true`、`EncryptionThisVolumeProper=true`、未 locked、可寫及 exact
VolumeUUID；另以 `/usr/bin/fdesetup status` 交叉核對 `FileVault is On.`。只驗全機 FileVault、
只 chmod、只用 `Path.resolve()` 或 caller 宣稱均不足。任一 symlink ancestor、ACL、immutable flag、
wrong uid／mode／device、volume swap 或 UUID drift 都在建立第一個檔案前停止。
取得 global lock 後、建立 authorization namespace前，以及唯一 TSA POST緊接之前，必須再讀取並
typed-compare同一份 volume／FileVault attestation；namespace及 response path亦須在 POST前後與持有的
directory／file descriptor核對。

本 authorization 另以 SHA-256 預先固定唯一 direct parent及唯一 private root；caller不能換另一個
owner-only路徑重用同一 authorization。固定值分別為
`98cd2c917f668882aaca3bbab9186a804fdbf90386e232bcd0abb26755d479bf`及
`60ce955e35899ab1851b4c8864f06c9bbcde5952a422276b39575f1d8685aa3e`；公開資料不保存原始路徑。

主 Data volume 凍結時已使用 99%，約只餘 16 GiB；因此本輪不得建立長期 collector。下輪必須先
事前固定 retention、容量上限及 low-space stop-before-socket，不能因 start 已完成而忽略容量風險。

## 4. Genesis chains

私有 namespace 必須在外部時間錨前 durable 建立以下六條獨立 genesis：

1. SEC request-attempt ledger；
2. response receipt ledger；
3. content-addressed object ledger；
4. official manifest ledger；
5. first-seen registry；
6. audit ledger。

每條 genesis 固定 `ordinal=0`、`event=genesis`、`prev_sha256=00…00`、實際事件 count 0，並以
canonical entry hash 作 chain head；objects directory 必須為空。start intent 同時綁定六個文件
SHA、chain head、authorization commit、remote proof、volume attestation及 account-zero receipt。
任何額外 line、歷史 object、identifier、截斷、重排、duplicate ordinal 或 hash drift 均令 start 無效。

合法 final cardinality 固定：前五條 ledger 各只有一行 genesis；audit ledger 精確三行，依次為
genesis、socket前 durable 的 `tsa_request_started`、驗證後的 `tsa_response_verified`。Round45 namespace
於 final receipt 後在協議層永久凍結及接受逐 byte／hash／metadata重驗；這不是 OS immutable 或
read-only 宣稱。current uid 視為受信任管理邊界，同 uid 的惡意程序不在本輪 threat model。未來
collector若另獲授權，只可在新 successor namespace引用這六個 chain head，不得直接 append 或改寫
本 start receipt 綁定的檔案；任何修改只會令重驗失敗，不能被當成有效歷史。

## 5. 專用戶口零狀態

零狀態只證明新的 `round45_form4_runtime_namespace`，不宣稱使用者其他模擬或券商戶口為零：

- Paper：funding、cash、NAV points、positions、open orders、trades、backfill 全為 0；
- broker binding：`unbound`，account identifier、credential handle、transport count 全為 0；
- real ledger：positions、orders、fills、transfers、entries 及 real-money action USD 全為 0；
- 不可 import v25／其他 Paper state，不可建立 shadow portfolio。

若日後綁定真實券商戶口，必須另有 provider-authenticated read-only snapshot；absence of integration
不能冒充該券商戶口餘額證據。本輪不需要亦不接受券商憑證。

## 6. RFC 3161 外部時間錨

唯一獲准 TSA 是 DigiCert 官方 RFC 3161 endpoint：
`http://timestamp.digicert.com`。官方說明及 CA chain來源：
`https://knowledge.digicert.com/general-information/rfc3161-compliant-time-stamp-authority-server`。

固定契約：

- message imprint：SHA-256 of exact `start_intent.json` bytes；
- policy OID：`2.16.840.1.114412.7.1`；
- query：`certReq=true`，OpenSSL 產生 CSPRNG nonce；exact TSQ 必須 create-once／fsync 保存，
  不能重新產生 nonce；本 authorization **不准 cold replay**，任何沒有 final receipt 的 namespace均永久
  `STOPPED_PARTIAL`。若將來另立 recovery authorization，亦只能零網絡驗證既有完整 TSR，絕不可再 POST；
- nonce強度由固定 OpenSSL generator及exact DER query結構約束；DER integer須positive、nonzero及minimal，
  query／signed token的數值相同。human text可因leading zero省略而少於16 hex，不能因此在建立私有狀態後
  誤判失敗；
- TSA request 精確 1、automatic retry 0、redirect 0、proxy 0、fallback 0；
- response 必須為完整 RFC 3161 token，imprint、policy、algorithm及 signature 全通過；
- outer `TimeStampResp` 只以最小 DER parser接受無附加statusString／failInfo的 exact
  `PKIStatus=granted(0)`；policy、imprint、serial、GenTime、Accuracy、ordering及nonce全部只可從
  `token_out`後以 `/dev/stdin` 輸入的 signed TSTInfo解析，不能從未簽署outer status文字取得；
  query與token nonce必須相同；OpenSSL reply mode的 `-in -` 不是stdin，明確禁用；
- responder SHA-256 fingerprint：
  `4aa03fa22cd75c84c55c938f828e676b9caecab33fe36d269aa334f146110a33`；
- intermediate SHA-256 certificate fingerprint：
  `ca0b1554ecd901ea19dcad8749e9f2648c8d6dfcea1add9d2c2109415bb82ccd`；
- responder／intermediate／self-signed root repository PEM bytes SHA-256 分別為：
  `f8ecbaae3ef6421377063a31d238b1cee48060528791854d3d3fcda965d565e6`、
  `5e13de210e735b614d6ec948361aadef9dd6c0ef575382a75f57fd59e183b90e`、
  `ce7d6b44f5d510391be98c8d76b18709400a30cd87659bfebe1c6f97ff5181ee`；
- OpenSSL 必須只用上述 single root／intermediate／responder。asset chain預檢使用
  `-no-CApath -no-CAstore`；`ts -verify` 的固定 OpenSSL不支援這兩個否定選項，因此只傳 exact
  `-CAfile root`及`-untrusted intermediate`，完全不傳 CApath／CAstore，再配合
  `-purpose timestampsign`、`-x509_strict`、`-verify_depth 2`、`-check_ss_sig`。不得把整包系統或
  certifi CA 當 TSA trust store；
- `monitor_started_at = token GenTime + token Accuracy upper bound`；Accuracy為必填，
  **缺失或unspecified即fail closed**。更嚴格的先後條件為
  `GenTime - Accuracy >= current Round45 check completed-at`；只驗 `GenTime + Accuracy` 不足。
  OpenSSL輸出必須有精確一行 `Accuracy:`；沒有RFC欄位時須呈現 `Accuracy: unspecified`，整行缺失或
  無法解析均失敗。固定chain及signed-time verification不包含CRL／OCSP；所有anchor receipt必須明載
  `revocation_checked=false`、`long_term_validation=false`，不得包裝成法律級長期驗證。

OpenSSL subprocess固定 `OPENSSL_CONF=/dev/null`、`LC_ALL=C`，不得繼承 caller 的 config／provider
環境；curl第一個選項固定 `--disable`，只帶最小 locale環境，不能讀 `.curlrc`。

repository另綁定一組無私鑰、非production trust root的離線自簽 RFC3161 query／response／certificate
fixture；本機固定 OpenSSL須實際完成token extraction、TSTInfo parsing、exact-query signature及chain
驗證。fixture只驗命令與parser相容性，不能替代DigiCert signer／chain檢查，亦不能授權production start。

TSA attempt chain 必須在 socket 前 durable 記下 query SHA、endpoint commitment、ordinal及 prev hash。
HTTP transport 不被當作信任根；即使遭 DNS／proxy／plain-HTTP 改寫，token signature、imprint、policy
及固定 certificate chain 必須令錯誤資料失敗。TSA failure、timeout、錯 content type、truncated token、
wrong signer／policy／imprint 或 verify failure 都永久停止本 authorization，不 retry、不 fallback。
本地時鐘、Git commit time、Actions time、HTTP Date 及 file mtime 都不能取代 token GenTime。

## 7. 固定狀態機

```text
UNSEEN
  -> CLAIMED              fresh owner-only namespace及global lock
  -> GENESIS_DURABLE      六條chain、zero-state、remote proof及start intent已fsync
  -> EXTERNAL_ANCHORED    單次RFC3161 token已驗證
  -> MONITOR_STARTED_COLLECTION_LOCKED
```

authorization namespace建立前失敗仍為 UNSEEN（空 root及owner-only operational lock不算監察狀態）；
一旦authorization namespace建立即為 CLAIMED，即使它仍為空；其後任何 crash、缺檔、模式或 hash
不符且尚未有完整 final receipt，均永久 STOPPED_PARTIAL。只有 final receipt 及全部 bound bytes完整時
可 idempotent re-entry。不同
authorization 遇既有 namespace、同一 authorization 的 partial state或第二個 token均失敗。
完整重入只做本機 raw-byte、chain、volume及TSQ／TSR驗證，不再查 GitHub、不再呼叫TSA，故PR日後關閉
或 branch force-push不會改寫已建立的歷史 start。

## 8. Remote proof 必需欄位

私有 `remote_gate_proof.json` 至少保存 normalized repository／branch／PR、local HEAD、remote ref、
Round44 parent run／job／check及 current Round45 run／job／check：run id、attempt、event、workflow
name／path、head SHA、job name／id、check name／id、app id／slug、status、conclusion、completed-at，
以及每個 raw GitHub API response的 SHA-256；workflow-run全集的分頁 hash須依 page順序保存。所有
current SHA 精確等於 launch HEAD；所有 parent
SHA精確等於 `f599816…`；launch 後 force-push 不能改寫已建立 start，但會令未來 collector 的
current-head preflight 失敗，直至另行事前協議處理。

## 9. Stable codes及 mutation closure

沿用 Round44 canonical codes，不新增同義字：authorization／Git blob drift 用
`form4_round44_authorization_invalid`；remote／PR／run／check 用
`form4_round44_remote_gate_invalid`；path／volume／mode／ACL 用
`form4_round44_private_boundary_invalid`；partial／receipt 用
`form4_round44_start_receipt_invalid`；重入衝突用 `form4_round44_already_started`；request plan／
tool／TSA endpoint drift 用 `form4_round44_request_plan_drifted`；genesis／chain 用
`form4_round44_attempt_ledger_invalid`；TSA 用 `form4_round44_external_anchor_invalid`；公開泄漏用
`form4_round44_public_boundary_breached`。Congress injection及非資料工程越界仍分別只用
`form4_forward_congress_field_injection`、`form4_forward_non_engineering_action_forbidden`。

Tests 必須拒絕 duplicate JSON、NaN、bool-as-int、extra／missing key、binding swap／absolute／`..`、
dirty／untracked worktree、wrong remote head／PR／workflow／job／app／status、Pages／Daily冒充、
relative／repo內／symlink／hardlink／wrong mode／uid／volume／encryption、Round42 contamination、
每個 partial state、兩個 concurrent creator、genesis截斷／重排、非零 account、anchor wrong
imprint／policy／signer／time及任何 SEC socket。合法fixture須證 full receipt byte-idempotent且mtime不變。

## 10. 現時決策邊界

| 狀態 | 凍結值 |
|---|---:|
| Round45 SEC／TSA request | 0／0 |
| 真實 filing／identifier | 0／0 |
| Monitor-start receipt | 未建立；需 exact-head remote CI後才可執行 |
| SEC collector／capability | 未實作／未發出 |
| Congress request／row／field | 0／0／0；停用 |
| 候選／配置／策略／績效 | 0／0／0／0 |
| 專用 Paper | 未注資、全現金語義；持倉／指令／成交／回填均 0 |
| 實金動作 | US$0 |
| 今日動作 | **今天不下單** |

本輪只把真正前瞻資料的起點做成可驗證外部事件。它沒有股票名單、人物排行榜、回報、勝率、
US$1,000 金額試算或落盤指示，亦不構成投資、法律或稅務建議。
