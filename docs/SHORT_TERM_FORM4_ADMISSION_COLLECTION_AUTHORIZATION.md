# 美股短線第 42 輪：Form 4 admission 一次性 collection authorization v1.0

FrozenAt：`2026-08-10T00:07:33Z`

狀態：**在 remote commit `0145969e19f2524d3eddc77702865425767aefac` 已推送，且本次
root collection、真實選樣、candidate、策略、績效、Paper 與實金動作仍全為 0 時凍結。**
本授權只准一次固定 SEC admission-feasibility collection 及其後的無網路 cold replay；不准
研究者在看見任何真實樣本後修改季度、選樣、schema、閘門、策略或門檻。

## 1. 精確程式與父協議綁定

machine receipt 必須綁定以下九個 repository bytes：Form 4 feasibility v1.0 協議與收據、
schema amendment v1.1 與收據、SEC client、feasibility verifier、collection implementation、
runner 及 collection tests。父 code commit 固定為完整 SHA
`0145969e19f2524d3eddc77702865425767aefac`，remote ref 固定為
`origin/codex/round42-form4-admission`；任一 hash 漂移、父 commit 不是目前 HEAD ancestor 或
authorization canonical receipt hash 不符，必須在任何網路前停止。

## 2. 唯一獲准的 request plan

只准 authorization ID `round42-form4-admission-one-shot-v1` 執行一次：

- catalog 精確 1 request；固定季度 `2006Q1`、`2016Q3`、`2026Q2` 各 1，共 3；
- 依 frozen first／lower-median／last 加最早未重複 4/A selector，總樣本只可 9–12；不得
  resample、跳過 amendment、換季度或按人物、issuer、金額、交易內容、可用性或結果重選；
- daily form index 只可取每筆 `FILING_DATE` 的同日 index，按 unique date 最多 12 request；
  next-day、later-day、accepted-time 或其他 fallback 全部禁止；
- 每個 selected accession 的完整 as-filed submission 最多 12 request；
- 總 request 數上限 `1 + 3 + 12 + 12 = 28`；automatic retry 精確為 0。任何 HTTP／內容／
  schema／hash 失敗均停止，不得重試、補抽、換日或續跑下一個 authorization。

`collection_started.json` 是 create-once checkpoint；其後只可 append private
`attempt_ledger.jsonl`。只要上述任一 checkpoint、`selection_plan.json` 或
`private_manifest.json` 已存在，同一 authorization 永久不得再啟動。

## 3. 私隱、selection seal 與 cold replay

quarantine 必須是 repository 外的絕對實體路徑，FileVault 已開啟；所有目錄 owner-only
`0700`，所有 raw objects、receipts、attempt ledger、selection seal 及 manifest 都必須是
link count 1 的 owner-only `0600` regular file。真實 accession、CIK、issuer、人物、ticker、
URL、raw text 及 contact data 不可進 Git、CI、網站或公開 validation。

三季 ZIP 驗收後必須先 create-once 寫入 private `selection_plan.json`，封存 9–12 個固定樣本
與 SHA；完成同日 index 及完整 submission collection 後，再 create-once 寫入
`private_manifest.json`，綁 authorization receipt、FileVault attestation、selection seal、三季
receipts、每筆 filing evidence、request count 及 attempt-ledger SHA。公開端只可見整份 private
manifest 的不可逆 SHA-256，不可見逐筆 token。

collection 成功只代表 private bytes 齊備，必須停止於
`private_collection_complete_cold_replay_required`。其後另一次 `replay` 必須從上述 seal 與
manifest cold replay，網路 opener 強制失敗；replay 不得抓取、補檔或更新任何 evidence。

## 4. 停止碼與不可越界狀態

collector stable failures 固定包括：

- `form4_collection_authorization_invalid`
- `form4_collection_private_boundary_invalid`
- `form4_collection_filevault_not_verified`
- `form4_collection_already_started`
- `form4_collection_append_only_collision`
- `form4_collection_attempt_ledger_invalid`
- `form4_collection_request_plan_drifted`
- `form4_collection_selection_plan_invalid`
- `form4_collection_request_limit_exceeded`
- `form4_collection_private_manifest_invalid`
- `form4_collection_replay_network_forbidden`
- `form4_collection_public_boundary_breached`

SEC client 或 feasibility verifier 的既有 stable failure 同樣立即停止並寫入 private attempt
ledger，不轉成 retry。cold replay 即使真實小樣本證明部分 controls，低於完整 admission
`16/16` 時公開 stop reason 必須新增且精確為 `form4_admission_below_16_of_16`。

本授權不准 candidate selection、strategy run、performance result、Paper 或 real money；machine
receipt 的相應狀態固定為 0／false／US$0。低於 `16/16` 必須維持「今天不下單」，不得把真實
樣本、歷史最後權重或 Paper 狀態描述成交易建議。全域 trial 下限仍為 6,287，本次 collection
不新增績效 trial。
